"""One fixed, synthetic-only SQLCipher transaction. No product migration entry.

SQLite owns transaction recovery. The existing instance lock coordinates normal
app processes; it is not claimed as hostile-process continuity authority.
"""
from contextlib import closing
from pathlib import Path
import os
import sys

from src.core.database_engine import (SQLCipherConnectionProvider,
    SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION)
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.database_content_evidence import database_content_evidence, require_same_content, DatabaseContentEvidence
from src.core.lesson_times_schema import (
    LESSON_TIME_TEMPLATE_STATEMENT, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION,
    SYNTHETIC_LESSON_TIMES_REGISTRY,
)
from src.core.maintenance_gate import ConnectionDrain, MaintenancePurpose
from src.core.observation_uow import ObservationWriterLock
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.runtime_root_protection import require_mutable_test_root, RuntimeRootKind
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.schema_upgrade import UpgradeError
from src.core.upgrade_validation import verify_timetable_source_references
from src.security.final_v4_sqlcipher_runtime import KeyedFinalV4CompatibilityInspector
from src.security.final_v3_document_runtime import FinalV3DocumentRuntime
from src.security.upgrade_startup import ProductStartupInventory
from src.security.final_v4_backup_runtime import _fsync_directory


class SyntheticTransactionalMigration:
    """Call once in a dedicated maintenance process, then terminate that process.

    Fixed additive V4 -> synthetic V5 only. The retained backup/evidence vetoes
    regular startup and all repeated execute calls, including after failure.
    """
    def __init__(self, backup_service, *, fault_hook=None):
        self.service = backup_service
        self.root = Path(backup_service.paths.final_v4.root)
        self._require_synthetic()
        self.main = backup_service.paths.final_v4.database
        self.companion = backup_service.paths.database
        self.backup = self.root / "schema-upgrade-source" / "transaction-v1" / "source.jkmebackup"
        self._fault_hook = fault_hook
        self._used = False

    def _require_synthetic(self):
        if not self.root.is_absolute() or self.root.resolve() != self.root:
            raise UpgradeError("transaction_synthetic_root_required")
        protection = require_mutable_test_root(self.root)
        if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
            raise UpgradeError("transaction_synthetic_root_required")
        expected = self.root / "final-v4-sqlcipher-runtime-v1"
        if (self.service.paths.final_v4.database != expected / "final-v4.sqlcipher"
                or self.service.paths.database != expected / "documents-v1.sqlcipher"):
            raise UpgradeError("transaction_paths_invalid")
        provider = self.service._provider
        if (not isinstance(provider, SQLCipherConnectionProvider)
                or provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
                or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION):
            raise UpgradeError("transaction_provider_invalid")

    def _emit(self, boundary):
        if self._fault_hook is not None:
            self._fault_hook(boundary)

    @staticmethod
    def _no_sidecars(path):
        for suffix in ("-wal", "-shm", "-journal"):
            try:
                Path(str(path) + suffix).lstat()
            except FileNotFoundError:
                continue
            raise UpgradeError("transaction_sidecar_requires_separate_recovery")

    def _connect(self, path, *, read_only=False):
        provider = self.service._provider
        key = self.service.loaded.database_key.key_material
        return (provider.connect_read_only(path, key_material=key) if read_only else
                provider.connect(path, create=False, key_material=key))

    def _source(self, path):
        self._no_sidecars(path)
        with closing(self._connect(path, read_only=True)) as connection:
            KeyedFinalV4CompatibilityInspector().inspect_connection(connection)
            verify_timetable_source_references(connection)
            return database_content_evidence(connection)

    def _companion_content(self, path):
        self._no_sidecars(path)
        self.service._inspect_companion(path, self.service.loaded.database_key.key_material)
        with closing(self._connect(path, read_only=True)) as connection:
            return database_content_evidence(connection)

    def _verified_backup_content(self):
        # Reextract, authenticate every entry, open both databases independently,
        # and validate documents/crossbindings through the existing backup service.
        with self.service.verified_snapshot(self.backup) as snapshot:
            return self._source(snapshot.database_path), self._companion_content(snapshot.companion_path)

    def _validate_live_documents(self):
        FinalV3DocumentRuntime(paths=self.service.paths,
            factory=self.service._document_factory, loaded_keys=self.service.loaded,
            installation_id=self.service.installation_id, source_root=None,
            random_source=self.service._random, clock=self.service._clock).validate_restart()

    def _sync_backup_chain(self):
        # The backup service syncs its publication directory. These two new
        # ancestors must also be durable before touching the main database.
        for directory in (self.backup.parent, self.backup.parent.parent, self.root):
            _fsync_directory(directory)
        if sys.platform == "darwin":
            import fcntl
            with self.backup.open("rb") as backup:
                fcntl.fcntl(backup.fileno(), fcntl.F_FULLFSYNC)

    def _target(self, connection, source):
        self.service._provider.verify_integrity(connection)
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        target = SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity
        if (result.version.sqlite_user_version != target.schema_version
                or result.schema_identity.fingerprint != target.fingerprint):
            raise UpgradeError("transaction_target_schema_invalid")
        evidence = database_content_evidence(connection)
        historical = DatabaseContentEvidence(tuple(t for t in evidence.tables if t[0] != "lesson_time_templates"))
        require_same_content(source, historical)
        verify_timetable_source_references(connection)
        return target

    @staticmethod
    def _configure_transaction(connection):
        # EXTRA additionally syncs the directory after deleting the rollback
        # journal. fullfsync requests F_FULLFSYNC on the macOS VFS.
        for sql in ("PRAGMA busy_timeout=0", "PRAGMA synchronous=EXTRA", "PRAGMA fullfsync=ON"):
            connection.execute(sql)
        expected = {"journal_mode": "delete", "synchronous": "3", "foreign_keys": "1",
                    "temp_store": "2", "cipher_status": "1", "busy_timeout": "0"}
        if sys.platform == "darwin":
            expected["fullfsync"] = "1"
        for name, value in expected.items():
            row = connection.execute(f"PRAGMA {name}").fetchone()
            if row is None or str(row[0]).lower() != value:
                raise UpgradeError("transaction_configuration_invalid")

    def _require_source_connection(self, connection):
        KeyedFinalV4CompatibilityInspector().inspect_connection(connection)

    def _apply_schema(self, connection):
        connection.execute(LESSON_TIME_TEMPLATE_STATEMENT)
        self._emit("schema_changed")
        connection.execute("PRAGMA user_version=5")

    def _require_upgrade(self):
        SYNTHETIC_LESSON_TIMES_REGISTRY.require_upgrade(
            FINAL_V4_SCHEMA_REGISTRATION.identity, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity)

    def _require_inventory(self, inventory):
        if inventory.restore_evidence or inventory.upgrade_evidence:
            raise UpgradeError("transaction_existing_evidence")

    def execute(self):
        self._require_synthetic()
        if self.service.opened is None:
            raise UpgradeError("transaction_existing_runtime_required")
        if self._used:
            raise UpgradeError("transaction_restart_required")
        self._used = True
        self._require_upgrade()
        gate = self.service._gate
        owner = "synthetic-transaction-v1"
        with RuntimeInstanceLock(self.root):
            inventory = ProductStartupInventory().inspect(self.root)
            if inventory.status.value in {"unsafe", "changed"}:
                raise UpgradeError("transaction_inventory_unsafe")
            allowed_markers = {".jkm-dmk-database-key-runtime-test-root",
                               ".jkm-final-v4-sqlcipher-runtime-test-root"}
            if set(inventory.unknown) - allowed_markers:
                raise UpgradeError("transaction_inventory_unknown")
            from src.application.retained_operation_startup import inspect_retained_operation_journals
            inspect_retained_operation_journals(self.root)
            self._require_inventory(inventory)
            capability = gate.request_maintenance(owner_id=owner, purpose=MaintenancePurpose.SCHEMA_UPGRADE)
            try:
                if not gate.activate(capability, owner_id=owner):
                    raise UpgradeError("transaction_writers_active")
                with gate.exclusive_writer(capability, owner_id=owner, purpose=MaintenancePurpose.SCHEMA_UPGRADE):
                    with ObservationWriterLock(self.main.parent / ".observation-staging"):
                        self._no_sidecars(self.main)
                        self._no_sidecars(self.companion)
                        source = self._source(self.main)
                        companion = self._companion_content(self.companion)
                        self.service.opened.documents.validate_restart()
                        self.service._validate_crossbindings(self.main, self.companion,
                                                            self.service.loaded.database_key.key_material)
                        self._emit("source_verified")
                        self.backup.parent.mkdir(mode=0o700, parents=True)
                        self.backup.parent.parent.chmod(0o700)
                        self.service.create_during_maintenance(self.backup)
                        backup_source, backup_companion = self._verified_backup_content()
                        require_same_content(source, backup_source)
                        require_same_content(companion, backup_companion)
                        self._sync_backup_chain()
                        self._emit("backup_verified")
                        # No lock monitor: the enclosing cooperative lock scope
                        # and existing maintenance capability are sufficient.
                        drain = ConnectionDrain((self.main, self.companion), gate=gate,
                            capability=capability, owner_id=owner, require_authority=self._require_synthetic)
                        with drain:
                            self._emit("connections_closed")
                            with drain.synthetic_transaction_connection(self.main, lambda: self._connect(self.main)) as connection:
                                self._configure_transaction(connection)
                                try:
                                    connection.execute("BEGIN EXCLUSIVE")
                                    self._require_source_connection(connection)
                                    require_same_content(source, database_content_evidence(connection))
                                    self._emit("transaction_begun")
                                    self._apply_schema(connection)
                                    self._target(connection, source)
                                    self._emit("target_verified")
                                    self._emit("before_commit")
                                    connection.commit()
                                    self._emit("after_commit")
                                except BaseException:
                                    if connection.in_transaction:
                                        connection.rollback()
                                    raise
                            with drain.maintenance_connections():
                                with closing(self._connect(self.main, read_only=True)) as reopened:
                                    self._target(reopened, source)
                                require_same_content(companion, self._companion_content(self.companion))
                        self._emit("connection_closed")
            finally:
                # This maintenance process must exit. Never resume stale V4
                # adapters, even after a successful rollback or commit error.
                gate.mark_recovery_required()
        return self.target_identity

    target_identity = SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity

    def inspect_restart(self):
        """Explicit synthetic inspection, no application/First-Run admission.

        A fresh process/service is required after execute. Reopen uses mode=rw
        only to let SQLite recover its own hot rollback journal, with the same
        existing key. An unknown state is preserved and rejected.
        """
        self._require_synthetic()
        with RuntimeInstanceLock(self.root):
            source, companion = self._verified_backup_content()
            self._no_sidecars(self.companion)
            for suffix in ("-wal", "-shm"):
                if Path(str(self.main) + suffix).exists():
                    raise UpgradeError("transaction_restart_wal_unsupported")
            with closing(self._connect(self.main)) as connection:
                result = DatabaseCompatibilityInspector().inspect_connection(connection)
                if (result.version.sqlite_user_version == 4
                        and result.schema_identity.fingerprint == FINAL_V4_SCHEMA_REGISTRATION.identity.fingerprint):
                    KeyedFinalV4CompatibilityInspector().inspect_connection(connection)
                    require_same_content(source, database_content_evidence(connection))
                    verify_timetable_source_references(connection)
                    identity = FINAL_V4_SCHEMA_REGISTRATION.identity
                else:
                    identity = self._target(connection, source)
            require_same_content(companion, self._companion_content(self.companion))
            self._validate_live_documents()
            self.service._validate_crossbindings(self.main, self.companion,
                                                self.service.loaded.database_key.key_material)
            return identity
