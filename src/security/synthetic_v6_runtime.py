"""Explicit existing-only synthetic V6 runtime; never a product startup path."""
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import threading
import tempfile
import shutil
import os
import weakref

from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.database_engine import (SQLCipherConnectionProvider,
    SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION)
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
from src.core.lesson_time_templates import LessonTimeTemplate, LessonTimeTemplateService
from src.core.runtime_root_protection import require_mutable_test_root, RuntimeRootKind
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.sqlite_store import SQLiteDatabase
from src.core.upgrade_validation import verify_timetable_target_references
from src.security.database_key_runtime import DatabaseKeyRuntimePaths
from src.security.final_v4_sqlcipher_runtime import KeyedFinalV4CompatibilityReport, FinalV4SQLCipherRuntimePaths
from src.security.final_v3_document_runtime import FinalV3DocumentRuntime, FinalV3DocumentRuntimePaths
from src.security.infrastructure.installation_inventory import ReadOnlyInstallationInventory
from src.security.infrastructure.lesson_time_templates import SQLiteLessonTimeTemplateRepository


class SyntheticV6RuntimeError(RuntimeError):
    """Sanitized fail-closed failure; no keys, SQL, or user paths."""


class KeyedSyntheticV6CompatibilityInspector:
    """Validate an already keyed connection, including domain content."""
    def inspect_connection(self, connection):
        try:
            before = connection.total_changes
            expected = {"cipher_version": SQLCIPHER_4_17_ENGINE_VERSION,
                "cipher_status": "1", "cipher_provider": "commoncrypto", "foreign_keys": "1"}
            for name, value in expected.items():
                row = connection.execute(f"PRAGMA {name}").fetchone()
                if row is None or str(row[0]) != value:
                    raise ValueError
            provider_version = connection.execute("PRAGMA cipher_provider_version").fetchone()[0]
            sqlite_version = connection.execute("SELECT sqlite_version()").fetchone()[0]
            if not provider_version or sqlite_version != SQLCIPHER_4_17_SQLITE_VERSION:
                raise ValueError
            if connection.execute("PRAGMA cipher_integrity_check").fetchall():
                raise ValueError
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            if len(integrity) != 1 or integrity[0][0] != "ok":
                raise ValueError
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError
            result = DatabaseCompatibilityInspector().inspect_connection(connection)
            target = SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity
            if (result.version.sqlite_user_version != target.schema_version
                    or result.schema_identity.fingerprint != target.fingerprint):
                raise ValueError
            verify_timetable_target_references(connection)
            for row in connection.execute("SELECT lesson_number,start_time,end_time FROM lesson_time_templates"):
                LessonTimeTemplate(*row)
            if connection.total_changes != before:
                raise ValueError
            return KeyedFinalV4CompatibilityReport(SQLCIPHER_4_17_ENGINE_VERSION,
                "commoncrypto", str(provider_version), sqlite_version, target.schema_version,
                target.fingerprint, result.schema_identity.object_count)
        except Exception:
            raise SyntheticV6RuntimeError("synthetic_v6_full_inspection_failed") from None


@dataclass(frozen=True)
class OpenedSyntheticV6Runtime:
    database: SQLiteDatabase
    lesson_time_templates: LessonTimeTemplateService
    compatibility: KeyedFinalV4CompatibilityReport
    documents: FinalV3DocumentRuntime = field(repr=False)
    database_context_id: str
    installation_id: str
    loaded_keys: object = field(repr=False)
    identity: object = SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity
    first_run: bool = False

    @property
    def final_v4(self):
        # Structural compatibility for existing document/backup composition only.
        # This object is never returned by the Final-V4 runtime coordinator.
        return self


class SyntheticV6ConnectionFactory:
    def __init__(self, runtime):
        self._runtime = runtime

    def connect(self, path, *, create=False, key_material=None):
        runtime = self._runtime
        if create or key_material is not None or Path(path) != runtime.service.paths.final_v4.database:
            raise SyntheticV6RuntimeError("synthetic_v6_existing_path_required")
        return runtime._open_connection(Path(path), read_only=False, inspect_main=True)

    def connect_read_only(self, path):
        runtime = self._runtime
        if Path(path) != runtime.service.paths.final_v4.database:
            raise SyntheticV6RuntimeError("synthetic_v6_existing_path_required")
        return runtime._open_connection(Path(path), read_only=True, inspect_main=True)


class _SessionDocumentFactory:
    def __init__(self, runtime):
        self.runtime = runtime

    def connect(self, *, create=False):
        if create:
            raise SyntheticV6RuntimeError("synthetic_v6_existing_companion_required")
        return self.runtime._open_connection(self.runtime.service.paths.database,
            read_only=False, inspect_main=False)

    def connect_read_only(self):
        return self.runtime._open_connection(self.runtime.service.paths.database,
            read_only=True, inspect_main=False)


class _SessionDocuments:
    """Check lifetime before any document method can change files."""
    def __init__(self, runtime, documents):
        self._runtime = runtime
        self._documents = documents

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        value = getattr(self._documents, name)
        if not callable(value):
            self._runtime._require_active()
            return value
        def call(*args, **kwargs):
            self._runtime._require_active()
            return value(*args, **kwargs)
        return call


class SyntheticV6Runtime:
    """Hold the existing instance lock for the entire synthetic session.

    The caller supplies an authenticated existing key context. No account/key
    creation port, repair, source restore, or product admission is available.
    SQLite hot-journal recovery must finish separately before this entry.
    """
    def __init__(self, backup_service):
        self.service = backup_service
        self.root = Path(backup_service.paths.final_v4.root)
        self._active = False
        self._used = False
        self.factory = SyntheticV6ConnectionFactory(self)
        self.document_factory = _SessionDocumentFactory(self)
        self._connections = weakref.WeakSet()
        self._session_lock = None
        self._thread = None

    def _require_scope(self):
        if not self.root.is_absolute() or self.root.resolve(strict=True) != self.root:
            raise SyntheticV6RuntimeError("synthetic_v6_root_required")
        protection = require_mutable_test_root(self.root)
        if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
            raise SyntheticV6RuntimeError("synthetic_v6_root_required")
        service = self.service
        expected_main = FinalV4SQLCipherRuntimePaths.for_key_runtime(DatabaseKeyRuntimePaths.for_root(self.root))
        if service.paths != FinalV3DocumentRuntimePaths.for_final_v4(expected_main):
            raise SyntheticV6RuntimeError("synthetic_v6_paths_invalid")
        provider = service._provider
        if (not isinstance(provider, SQLCipherConnectionProvider)
                or provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
                or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION):
            raise SyntheticV6RuntimeError("synthetic_v6_provider_required")
        keys = service.paths.final_v4.key_runtime
        service._validate_key_metadata(keys.keyset_metadata, keys.envelope_registry, expected=service.loaded)

    def _require_active(self):
        if threading.get_ident() != self._thread:
            raise SyntheticV6RuntimeError("synthetic_v6_session_thread_required")
        if not self._active:
            raise SyntheticV6RuntimeError("synthetic_v6_session_closed")
        self._require_scope()

    def _open_connection(self, path, *, read_only, inspect_main):
        self._require_active()
        provider = self.service._provider
        key = self.service.loaded.database_key.key_material
        connection = (provider.connect_read_only(path, key_material=key) if read_only else
            provider.connect(path, create=False, key_material=key))
        self._connections.add(connection)
        try:
            if inspect_main:
                KeyedSyntheticV6CompatibilityInspector().inspect_connection(connection)
            return connection
        except BaseException:
            connection.close()
            raise

    def _verify_historical_sources(self):
        # These retained encrypted sources are historical evidence, never V6
        # restore authority. Each exact path still needs its own schema-bound
        # independent container verification before runtime admission.
        from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupService
        from src.security.synthetic_v5_backup_runtime import SyntheticV5EncryptedBackupService
        service = self.service
        arguments = dict(opened_runtime=None, paths=service.paths,
            loaded_keys=service.loaded, main_factory=service._main_factory,
            document_factory=service._document_factory, provider=service._provider,
            maintenance_gate=service._gate, random_source=service._random,
            clock=service._clock, installation_id=service.installation_id)
        sources = (
            (self.root / "schema-upgrade-source/transaction-v1/source.jkmebackup",
                (FinalV4EncryptedBackupService,)),
            (self.root / "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup",
                (FinalV4EncryptedBackupService, SyntheticV5EncryptedBackupService)),
        )
        for path, allowed_services in sources:
            if not path.exists():
                if path.parent.exists():
                    raise SyntheticV6RuntimeError("synthetic_v6_historical_source_incomplete")
                continue
            for service_type in allowed_services:
                try:
                    # Existing backup verification extracts temporary encrypted
                    # artifacts beside its input. Keep startup installation
                    # inventory unchanged: authenticate an exclusive encrypted
                    # copy outside the installation instead.
                    with tempfile.TemporaryDirectory(prefix="jkm-v6-history-verify-") as temporary:
                        copied = Path(temporary) / "source.jkmebackup"
                        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                        with os.fdopen(descriptor, "rb") as source:
                            with copied.open("xb") as target:
                                copied.chmod(0o600)
                                shutil.copyfileobj(source, target)
                        with service_type(**arguments).verified_snapshot(copied):
                            pass
                    break
                except Exception:
                    continue
            else:
                raise SyntheticV6RuntimeError("synthetic_v6_historical_source_invalid")

    def _preflight(self):
        self._require_scope()
        inventory = ReadOnlyInstallationInventory().inspect(self.root)
        if inventory.status.value in {"unsafe", "changed", "empty", "main_missing"}:
            raise SyntheticV6RuntimeError("synthetic_v6_inventory_invalid")
        allowed_markers = {".jkm-dmk-database-key-runtime-test-root",
                           ".jkm-final-v4-sqlcipher-runtime-test-root"}
        if set(inventory.unknown) - allowed_markers:
            raise SyntheticV6RuntimeError("synthetic_v6_unknown_evidence")
        terminal_restore = False
        if inventory.restore_evidence:
            from src.security.synthetic_v6_live_restore import classify_terminal_synthetic_v6_restore_artifacts
            terminal_restore = classify_terminal_synthetic_v6_restore_artifacts(self.service)
        for artifact in inventory.artifacts:
            name = artifact.relative_path
            # Retained transactional source backup is historical only. Old
            # journal/anchor and all pending restore evidence still veto runtime.
            if (artifact.role == "restore_evidence" and not terminal_restore) or name.split("/")[0] in {
                    "schema-upgrade-foundation", "schema-upgrade-replay"}:
                raise SyntheticV6RuntimeError("synthetic_v6_recovery_required")
            if artifact.role == "upgrade_evidence" and name not in {
                    "schema-upgrade-source", "schema-upgrade-source/transaction-timetable-v1",
                    "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup",
                    "schema-upgrade-source/transaction-v1",
                    "schema-upgrade-source/transaction-v1/source.jkmebackup"}:
                raise SyntheticV6RuntimeError("synthetic_v6_unknown_upgrade_evidence")
        self._verify_historical_sources()
        for path in (self.service.paths.final_v4.database, self.service.paths.database):
            for suffix in ("-wal", "-shm", "-journal"):
                try:
                    Path(str(path) + suffix).lstat()
                except FileNotFoundError:
                    continue
                raise SyntheticV6RuntimeError("synthetic_v6_separate_recovery_required")

    @contextmanager
    def open_existing(self, *, lock=None):
        self._require_scope()
        if self._used:
            raise SyntheticV6RuntimeError("synthetic_v6_session_used")
        self._used = True
        owns_lock = lock is None
        if lock is None:
            self._session_lock = RuntimeInstanceLock(self.root).acquire()
        else:
            from src.security.upgrade_startup import ProductUpgradeStartupGuard
            if lock.runtime_root != self.root:
                raise SyntheticV6RuntimeError("synthetic_v6_lock_root_mismatch")
            ProductUpgradeStartupGuard(lock)._require_lock()
            self._session_lock = lock
        self._thread = threading.get_ident()
        try:
            self._preflight()
            service = self.service
            with closing(service._provider.connect_read_only(service.paths.final_v4.database,
                    key_material=service.loaded.database_key.key_material)) as connection:
                report = KeyedSyntheticV6CompatibilityInspector().inspect_connection(connection)
            service._inspect_companion(service.paths.database, service.loaded.database_key.key_material)
            documents = FinalV3DocumentRuntime(paths=service.paths, factory=self.document_factory,
                loaded_keys=service.loaded, installation_id=service.installation_id,
                source_root=None, random_source=service._random, clock=service._clock)
            self._active = True
            documents.validate_restart()
            service._validate_crossbindings(service.paths.final_v4.database,
                service.paths.database, service.loaded.database_key.key_material)
            self._active = True
            database = SQLiteDatabase(service.paths.final_v4.database, connection_provider=self.factory,
                create=False, initialize_schema=False, maintenance_gate=service._gate)
            try:
                yield OpenedSyntheticV6Runtime(database,
                    LessonTimeTemplateService(SQLiteLessonTimeTemplateRepository(database.connect)),
                    report, _SessionDocuments(self, documents), service.loaded.database_context_id,
                    service.installation_id, service.loaded)
            finally:
                self._active = False
        finally:
            self._active = False
            # Closing a connection invalidates every escaped cursor and rolls
            # back uncommitted writes. Never release the instance lock first.
            close_errors = []
            for connection in tuple(self._connections):
                try:
                    connection.close()
                except Exception as error:
                    close_errors.append(error)
            self._connections.clear()
            if close_errors:
                raise SyntheticV6RuntimeError("synthetic_v6_connection_close_failed")
            if owns_lock:
                self._session_lock.release()
            self._session_lock = None
