"""Restartable end-to-end Security Sprint 11 integration test path."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, replace
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Callable, Mapping

from prototypes.encrypted_backup_container.sprint9_container import (
    SYNTHETIC_BACKUP_TEST_ROOT_MARKER,
    SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES,
    SyntheticEncryptedBackupServiceV1,
)
from prototypes.encrypted_document_container.sprint10_container import (
    SYNTHETIC_DOCUMENT_EXPORT_MARKER,
    SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES,
    SYNTHETIC_DOCUMENT_STORAGE_MARKER,
    SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
    SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
    SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
    SyntheticEncryptedDocumentServiceV1,
)
from src.core.database_engine import (
    SQLCipherConnectionProvider,
    SQLITE_RUNTIME_VERSION,
)
from src.core.database_compatibility import DATABASE_COMPATIBILITY_VERSION
from src.core.sqlite_store import SQLiteDatabase
from src.security.backup_container import BackupContainerContextV1
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DatabaseKey,
    derive_domain_separated_key,
)
from src.security.domain import validate_uuid4
from src.security.migration_lock import (
    ExclusiveMigrationLock,
    MigrationLockError,
    MigrationLockStatus,
)
from src.security.ports import RandomSource, UtcClock

from .document_container import format_utc
from .integration_backup import (
    SecurityEncryptedBackupAdapter,
    SecurityEncryptedRestoreResult,
    integration_backup_sqlcipher_guard,
)
from .integration_database import (
    EncryptedDocumentGenerationRecord,
    SecurityDocumentApplicationAdapter,
    SecurityIntegrationConnectionFactory,
    inspect_plaintext_documents,
    security_integration_database_validator,
    transfer_plaintext_to_sqlcipher,
)
from .integration_gate import (
    SECURITY_INTEGRATION_ROOT_MARKER,
    SECURITY_INTEGRATION_SOURCE_MARKER,
    SecurityIntegrationError,
    SecurityIntegrationGate,
    SecurityIntegrationPaths,
)
from .integration_state import (
    SecurityIntegrationArtifact,
    SecurityIntegrationDocumentPlan,
    SecurityIntegrationJournalRepository,
    SecurityIntegrationJournalV1,
    SecurityIntegrationReplayAnchorRepository,
    SecurityIntegrationReplayAnchorV1,
)


SECURITY_INTEGRATION_JOURNAL_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/security-integration-journal-auth/v1"
)
SECURITY_INTEGRATION_REPLAY_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/security-integration-replay-auth/v1"
)
_SQLITE_HEADER = b"SQLite format 3\x00"
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_ALLOWED_TRANSITIONS = {
    "PREFLIGHT": "BACKUP_VERIFIED",
    "BACKUP_VERIFIED": "DATABASE_MIGRATED",
    "DATABASE_MIGRATED": "DOCUMENTS_PREPARED",
    "DOCUMENTS_PREPARED": "REFERENCES_SWITCHED",
    "REFERENCES_SWITCHED": "ENCRYPTED_BACKUP_VERIFIED",
    "ENCRYPTED_BACKUP_VERIFIED": "REOPEN_VERIFIED",
    "REOPEN_VERIFIED": "COMPLETED",
}


class SecurityIntegrationPhase(StrEnum):
    PREFLIGHT = "PREFLIGHT"
    BACKUP_VERIFIED = "BACKUP_VERIFIED"
    DATABASE_MIGRATED = "DATABASE_MIGRATED"
    DOCUMENTS_PREPARED = "DOCUMENTS_PREPARED"
    REFERENCES_SWITCHED = "REFERENCES_SWITCHED"
    ENCRYPTED_BACKUP_VERIFIED = "ENCRYPTED_BACKUP_VERIFIED"
    REOPEN_VERIFIED = "REOPEN_VERIFIED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True)
class SecurityIntegrationPreflight:
    phase: SecurityIntegrationPhase
    error_code: str | None
    journal_revision: int
    document_count: int


@dataclass(frozen=True)
class SecurityIntegrationReport:
    phase: SecurityIntegrationPhase
    journal_revision: int
    document_count: int
    source_sha256: str
    safety_copy_sha256: str
    encrypted_database_sha256: str
    encrypted_backup_sha256: str
    source_retained: bool
    reopened: bool


@dataclass(frozen=True)
class SecurityIntegrationRuntime:
    """Qt-free application composition against the encrypted test stock."""

    database: SQLiteDatabase
    documents: SecurityDocumentApplicationAdapter
    records: tuple[EncryptedDocumentGenerationRecord, ...]

    def student_count(self) -> int:
        with closing(self.database.connect()) as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            )


class SecurityIntegrationOrchestrator:
    """Smallest complete, gate-bound and restartable integration chain."""

    def __init__(
        self,
        *,
        paths: SecurityIntegrationPaths,
        installation_id: str,
        database_context_id: str,
        migration_id: str,
        migration_generation: int,
        dmk_loader: Callable[[], LoadedDataMasterKey],
        database_key_loader: Callable[[LoadedDataMasterKey], DatabaseKey],
        random_source: RandomSource,
        clock: UtcClock,
        sqlcipher_provider: SQLCipherConnectionProvider,
        app_instance_available: Callable[[], bool],
        source_closed_probe: Callable[[Path], bool],
        app_version: str,
        sqlite_version: str = SQLITE_RUNTIME_VERSION,
        sqlcipher_version: str = "4.12.0 community",
        fault_injector: Callable[[str], None] | None = None,
        fsync: Callable[[int], None] = os.fsync,
    ) -> None:
        for identifier in (
            installation_id,
            database_context_id,
            migration_id,
        ):
            validate_uuid4(identifier)
        if type(migration_generation) is not int or migration_generation < 1:
            raise SecurityIntegrationError(
                "security_integration_generation_invalid"
            )
        self.paths = paths
        self.installation_id = installation_id
        self.database_context_id = database_context_id
        self.migration_id = migration_id
        self.migration_generation = migration_generation
        self._dmk_loader = dmk_loader
        self._database_key_loader = database_key_loader
        self._random = random_source
        self._clock = clock
        self._provider = sqlcipher_provider
        self._app_instance_available = app_instance_available
        self._source_closed_probe = source_closed_probe
        self._app_version = app_version
        self._sqlite_version = sqlite_version
        self._sqlcipher_version = sqlcipher_version
        self._fault = fault_injector or (lambda _point: None)
        self._fsync = fsync
        self._journal = SecurityIntegrationJournalRepository(
            paths.journal,
            fsync=fsync,
        )
        self._anchor = SecurityIntegrationReplayAnchorRepository(
            paths.replay_anchor,
            fsync=fsync,
        )
        self._state: SecurityIntegrationJournalV1 | None = None
        self._journal_digest: str | None = None
        self._anchor_state: SecurityIntegrationReplayAnchorV1 | None = None
        self._document_service = SyntheticEncryptedDocumentServiceV1(
            random_source=random_source,
            clock=clock,
            fault_injector=fault_injector,
            required_source_prefix=None,
        )

    @classmethod
    def from_environment(
        cls,
        *,
        environ: Mapping[str, str],
        **kwargs,
    ) -> "SecurityIntegrationOrchestrator":
        paths = SecurityIntegrationGate().require_active(environ)
        return cls(paths=paths, **kwargs)

    def preflight(self) -> SecurityIntegrationPreflight:
        """Inspect state without creating, replacing, or deleting anything."""
        try:
            self._require_gate_bound_paths()
            dmk, database_key = self._load_keys()
            self._validate_plaintext_source()
            sources = inspect_plaintext_documents(
                factory=self._source_factory(),
                paths=self.paths,
            )
            journal_key, anchor_key = self._state_keys(dmk)
            if not self._journal.exists():
                if self._anchor.exists() or self._has_started_artifacts():
                    return SecurityIntegrationPreflight(
                        SecurityIntegrationPhase.BLOCKED,
                        "security_integration_unjournaled_artifacts",
                        0,
                        len(sources),
                    )
                self._require_storage_inventory(None)
                return SecurityIntegrationPreflight(
                    SecurityIntegrationPhase.PREFLIGHT,
                    None,
                    0,
                    len(sources),
                )
            state, digest = self._journal.load_with_digest(journal_key)
            self._require_state_context(state, dmk, database_key)
            if not self._anchor.exists():
                if (
                    state.revision == 0
                    and state.phase == SecurityIntegrationPhase.PREFLIGHT
                ):
                    return SecurityIntegrationPreflight(
                        SecurityIntegrationPhase.RECOVERY_REQUIRED,
                        "security_integration_initial_anchor_missing",
                        state.revision,
                        len(state.documents),
                    )
                raise SecurityIntegrationError(
                    "security_integration_anchor_missing"
                )
            anchor = self._anchor.read(anchor_key)
            self._require_anchor_context(anchor, state, digest)
            self._require_document_sources_match(state.documents, sources)
            self._require_storage_inventory(state)
            if anchor.pending is not None:
                return SecurityIntegrationPreflight(
                    SecurityIntegrationPhase.RECOVERY_REQUIRED,
                    "security_integration_anchor_pending",
                    state.revision,
                    len(state.documents),
                )
            self._validate_phase_artifacts(state)
            return SecurityIntegrationPreflight(
                SecurityIntegrationPhase(state.phase),
                None,
                state.revision,
                len(state.documents),
            )
        except Exception as error:
            return SecurityIntegrationPreflight(
                SecurityIntegrationPhase.BLOCKED,
                _error_code(error, "security_integration_preflight_failed"),
                0,
                0,
            )

    def run(self) -> SecurityIntegrationReport:
        return self._run(allow_stale_takeover=False)

    def _run(
        self,
        *,
        allow_stale_takeover: bool,
    ) -> SecurityIntegrationReport:
        preflight = self.preflight()
        if preflight.phase is SecurityIntegrationPhase.BLOCKED:
            raise SecurityIntegrationError(
                preflight.error_code or "security_integration_preflight_blocked"
            )
        dmk, database_key = self._load_keys()
        lock = ExclusiveMigrationLock(
            self.paths.root,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            allowed_root=self.paths.root,
        )
        try:
            lock.acquire()
        except MigrationLockError as error:
            if (
                not allow_stale_takeover
                or error.code != "migration_lock_stale_takeover_required"
            ):
                raise
            inspection = lock.inspect()
            if (
                inspection.status is not MigrationLockStatus.STALE
                or inspection.owner is None
                or inspection.device_id is None
                or inspection.file_id is None
            ):
                raise SecurityIntegrationError(
                    "security_integration_stale_lock_evidence_missing"
                ) from None
            lock.take_over_stale(
                expected_owner=inspection.owner,
                expected_device_id=inspection.device_id,
                expected_file_id=inspection.file_id,
                recovery_evidence_validator=(
                    lambda owner, identity: (
                        owner == inspection.owner
                        and identity
                        == (inspection.device_id, inspection.file_id)
                        and self._authenticated_recovery_evidence_valid()
                    )
                ),
            )
        try:
            self._load_or_initialize_state(dmk, database_key)
            self._drive(dmk, database_key)
            return self._report()
        finally:
            try:
                if lock.verify_owner():
                    lock.release()
            except Exception:
                pass

    def recover(self) -> SecurityIntegrationReport:
        """A freshly constructed process revalidates and resumes idempotently."""
        return self._run(allow_stale_takeover=True)

    def _authenticated_recovery_evidence_valid(self) -> bool:
        try:
            dmk, database_key = self._load_keys()
            journal_key, anchor_key = self._state_keys(dmk)
            state, digest = self._journal.load_with_digest(journal_key)
            self._require_state_context(state, dmk, database_key)
            if not self._anchor.exists():
                return (
                    state.revision == 0
                    and state.phase == SecurityIntegrationPhase.PREFLIGHT
                )
            anchor = self._anchor.read(anchor_key)
            self._require_anchor_context(anchor, state, digest)
            return True
        except Exception:
            return False

    def open_runtime(self) -> SecurityIntegrationRuntime:
        preflight = self.preflight()
        if preflight.phase is not SecurityIntegrationPhase.COMPLETED:
            raise SecurityIntegrationError(
                "security_integration_runtime_not_completed"
            )
        dmk, database_key = self._load_keys()
        self._load_authenticated_state(dmk, database_key)
        assert self._state is not None
        factory = self._target_factory(database_key, read_only=True)
        documents = self._document_adapter(factory)
        records = documents.verify_active(self._state.documents)
        database = SQLiteDatabase(
            self.paths.encrypted_database,
            connection_provider=factory,
            create=False,
            initialize_schema=False,
        )
        runtime = SecurityIntegrationRuntime(database, documents, records)
        runtime.student_count()
        return runtime

    def open_document_writer(self) -> SecurityDocumentApplicationAdapter:
        preflight = self.preflight()
        if preflight.phase is not SecurityIntegrationPhase.COMPLETED:
            raise SecurityIntegrationError(
                "security_integration_runtime_not_completed"
            )
        _dmk, database_key = self._load_keys()
        return self._document_adapter(self._target_factory(database_key))

    def restore_verified_backup(
        self,
        restore_name: str,
    ) -> SecurityEncryptedRestoreResult:
        runtime = self.open_runtime()
        _require_safe_restore_name(restore_name)
        dmk, database_key = self._load_keys()
        return self._backup_adapter(
            database_key,
        ).restore_verified(
            records=runtime.records,
            restore_name=restore_name,
        )

    def _drive(
        self,
        dmk: LoadedDataMasterKey,
        database_key: DatabaseKey,
    ) -> None:
        assert self._state is not None
        while self._state.phase != SecurityIntegrationPhase.COMPLETED:
            phase = SecurityIntegrationPhase(self._state.phase)
            if phase is SecurityIntegrationPhase.PREFLIGHT:
                self._create_and_verify_safety_copy()
                self._transition(
                    SecurityIntegrationPhase.BACKUP_VERIFIED,
                    completed_check="plaintext_safety_copy_verified",
                )
            elif phase is SecurityIntegrationPhase.BACKUP_VERIFIED:
                self._ensure_encrypted_database(database_key)
                self._transition(
                    SecurityIntegrationPhase.DATABASE_MIGRATED,
                    completed_check="sqlcipher_database_verified",
                )
            elif phase is SecurityIntegrationPhase.DATABASE_MIGRATED:
                factory = self._target_factory(database_key)
                adapter = self._document_adapter(factory)
                prepared: list[SecurityIntegrationDocumentPlan] = []
                for plan in self._state.documents:
                    record = adapter.prepare_existing(plan)
                    verification = self._document_service.verify(
                        test_root=self.paths.root,
                        container=self.paths.document_storage
                        / record.container_name,
                        dmk=dmk,
                        context=adapter._context(record.document_id, 1),
                        expected_storage_id=record.storage_id,
                    )
                    prepared.append(
                        replace(
                            plan,
                            container_name=record.container_name,
                            container_sha256=verification.container_sha256,
                        )
                    )
                    self._fault("documents_after_prepared_generation")
                self._transition(
                    SecurityIntegrationPhase.DOCUMENTS_PREPARED,
                    completed_check="encrypted_documents_verified",
                    documents=tuple(prepared),
                )
            elif phase is SecurityIntegrationPhase.DOCUMENTS_PREPARED:
                records = self._document_adapter(
                    self._target_factory(database_key)
                ).activate_prepared(self._state.documents)
                if len(records) != len(self._state.documents):
                    raise SecurityIntegrationError(
                        "security_integration_document_activation_incomplete"
                    )
                self._transition(
                    SecurityIntegrationPhase.REFERENCES_SWITCHED,
                    completed_check="document_references_switched",
                )
            elif phase is SecurityIntegrationPhase.REFERENCES_SWITCHED:
                records = self._document_adapter(
                    self._target_factory(database_key)
                ).verify_active(self._state.documents)
                self._backup_adapter(database_key).create_or_verify(records)
                self._transition(
                    SecurityIntegrationPhase.ENCRYPTED_BACKUP_VERIFIED,
                    completed_check="encrypted_backup_verified",
                )
            elif phase is SecurityIntegrationPhase.ENCRYPTED_BACKUP_VERIFIED:
                factory = self._target_factory(database_key)
                with closing(factory.open_existing()):
                    pass
                records = self._document_adapter(factory).verify_active(
                    self._state.documents
                )
                self._backup_adapter(database_key).create_or_verify(records)
                self._transition(
                    SecurityIntegrationPhase.REOPEN_VERIFIED,
                    completed_check="fresh_reopen_verified",
                )
            elif phase is SecurityIntegrationPhase.REOPEN_VERIFIED:
                self._publish_retained_marker()
                self._transition(
                    SecurityIntegrationPhase.COMPLETED,
                    completed_check="plaintext_marked_retained",
                )
            else:
                raise SecurityIntegrationError(
                    "security_integration_phase_blocked"
                )

    def _load_or_initialize_state(
        self,
        dmk: LoadedDataMasterKey,
        database_key: DatabaseKey,
    ) -> None:
        journal_key, anchor_key = self._state_keys(dmk)
        if self._journal.exists():
            if not self._anchor.exists():
                state, digest = self._journal.load_with_digest(journal_key)
                self._require_state_context(state, dmk, database_key)
                if (
                    state.revision != 0
                    or state.phase != SecurityIntegrationPhase.PREFLIGHT
                ):
                    raise SecurityIntegrationError(
                        "security_integration_anchor_missing"
                    )
                anchor = SecurityIntegrationReplayAnchorV1(
                    installation_id=self.installation_id,
                    database_context_id=self.database_context_id,
                    migration_id=self.migration_id,
                    migration_generation=self.migration_generation,
                    revision=0,
                    journal_revision=0,
                    journal_sha256=digest,
                    root_sha256=state.root_sha256,
                )
                self._anchor.initialize(anchor, anchor_key)
            self._load_authenticated_state(dmk, database_key)
            self._resolve_pending_anchor(journal_key, anchor_key)
            assert self._state is not None
            self._validate_phase_artifacts(self._state)
            return
        sources = inspect_plaintext_documents(
            factory=self._source_factory(),
            paths=self.paths,
        )
        plans = tuple(
            SecurityIntegrationDocumentPlan(
                source_document_id=source.source_document_id,
                document_id=self._new_uuid(
                    "security_integration_document_id_invalid"
                ),
                storage_id=self._new_uuid(
                    "security_integration_storage_id_invalid"
                ),
                source_path_sha256=source.source_path_sha256,
                plaintext_size=source.plaintext_size,
                plaintext_sha256=source.plaintext_sha256,
            )
            for source in sources
        )
        state = SecurityIntegrationJournalV1(
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            migration_generation=self.migration_generation,
            dmk_key_id=dmk.key_id,
            dmk_key_generation=dmk.generation,
            database_key_id=database_key.key_id,
            database_key_generation=database_key.generation,
            root_sha256=_path_sha256(self.paths.root),
            revision=0,
            phase=SecurityIntegrationPhase.PREFLIGHT,
            artifacts=self._capture_artifacts(),
            documents=plans,
            completed_checks=("preflight_verified",),
        )
        digest = self._journal.create(state, journal_key)
        self._fault("initial_after_journal_publish")
        anchor = SecurityIntegrationReplayAnchorV1(
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            migration_generation=self.migration_generation,
            revision=0,
            journal_revision=0,
            journal_sha256=digest,
            root_sha256=state.root_sha256,
        )
        self._anchor.initialize(anchor, anchor_key)
        self._fault("initial_after_anchor_publish")
        self._state = state
        self._journal_digest = digest
        self._anchor_state = anchor

    def _load_authenticated_state(
        self,
        dmk: LoadedDataMasterKey,
        database_key: DatabaseKey,
    ) -> None:
        journal_key, anchor_key = self._state_keys(dmk)
        state, digest = self._journal.load_with_digest(journal_key)
        self._require_state_context(state, dmk, database_key)
        anchor = self._anchor.read(anchor_key)
        self._require_anchor_context(anchor, state, digest)
        self._state, self._journal_digest, self._anchor_state = (
            state,
            digest,
            anchor,
        )

    def _resolve_pending_anchor(
        self,
        journal_key: bytes,
        anchor_key: bytes,
    ) -> None:
        assert self._state is not None
        assert self._journal_digest is not None
        assert self._anchor_state is not None
        anchor = self._anchor_state
        if anchor.pending is None:
            return
        pending = anchor.pending
        if (
            pending.journal_revision == self._state.revision
            and pending.journal_sha256 == self._journal_digest
        ):
            anchor = self._anchor.commit(anchor, anchor_key)
        elif (
            anchor.journal_revision == self._state.revision
            and anchor.journal_sha256 == self._journal_digest
        ):
            anchor = self._anchor.abort_pending(anchor, anchor_key)
        else:
            raise SecurityIntegrationError(
                "security_integration_anchor_replay_invalid"
            )
        self._anchor_state = anchor
        self._state, self._journal_digest = self._journal.load_with_digest(
            journal_key
        )

    def _transition(
        self,
        phase: SecurityIntegrationPhase,
        *,
        completed_check: str,
        documents: tuple[SecurityIntegrationDocumentPlan, ...] | None = None,
    ) -> None:
        assert self._state is not None
        assert self._journal_digest is not None
        assert self._anchor_state is not None
        expected = _ALLOWED_TRANSITIONS.get(self._state.phase)
        if expected != phase:
            raise SecurityIntegrationError(
                "security_integration_transition_invalid"
            )
        dmk = self._dmk_loader()
        journal_key, anchor_key = self._state_keys(dmk)
        next_state = replace(
            self._state,
            revision=self._state.revision + 1,
            phase=phase,
            artifacts=self._capture_artifacts(),
            documents=(
                self._state.documents if documents is None else documents
            ),
            completed_checks=(
                *self._state.completed_checks,
                completed_check,
            ),
            error_code=None,
        )
        next_digest = self._journal.preview_digest(next_state, journal_key)
        planned = replace(
            self._anchor_state,
            revision=self._anchor_state.revision + 1,
            journal_revision=next_state.revision,
            journal_sha256=next_digest,
            pending=None,
        )
        prepared = self._anchor.prepare(
            self._anchor_state,
            planned,
            anchor_key,
        )
        self._fault("transition_after_anchor_prepare")
        observed_digest = self._journal.replace(
            self._journal_digest,
            next_state,
            journal_key,
        )
        if observed_digest != next_digest:
            raise SecurityIntegrationError(
                "security_integration_transition_digest_mismatch"
            )
        self._fault("transition_after_journal_publish")
        committed = self._anchor.commit(prepared, anchor_key)
        self._fault(f"phase_{phase.value.lower()}_committed")
        self._state = next_state
        self._journal_digest = observed_digest
        self._anchor_state = committed

    def _create_and_verify_safety_copy(self) -> None:
        source = self.paths.source_database
        target = self.paths.safety_copy
        source_size, source_hash = _hash_file(source)
        if target.exists():
            target_size, target_hash = _hash_file(target)
            if (target_size, target_hash) != (source_size, source_hash):
                raise SecurityIntegrationError(
                    "security_integration_safety_copy_changed"
                )
        else:
            _copy_exclusive(source, target, self._fsync)
        self._fault("safety_copy_after_publish")
        target_size, target_hash = _hash_file(target)
        if (target_size, target_hash) != (source_size, source_hash):
            raise SecurityIntegrationError(
                "security_integration_safety_copy_mismatch"
            )
        with closing(
            SecurityIntegrationConnectionFactory.plaintext_source(
                target
            ).open_existing()
        ) as connection:
            rows = connection.execute("PRAGMA integrity_check").fetchall()
            if len(rows) != 1 or str(rows[0][0]) != "ok":
                raise SecurityIntegrationError(
                    "security_integration_safety_copy_integrity_failed"
                )

    def _publish_retained_marker(self) -> None:
        source_size, source_hash = _hash_file(self.paths.source_database)
        safety_size, safety_hash = _hash_file(self.paths.safety_copy)
        if (source_size, source_hash) != (safety_size, safety_hash):
            raise SecurityIntegrationError(
                "security_integration_retained_source_mismatch"
            )
        payload = _canonical_bytes(
            {
                "database_context_id": self.database_context_id,
                "migration_id": self.migration_id,
                "retained_format_version": 1,
                "safety_copy_sha256": safety_hash,
                "source_sha256": source_hash,
            }
        )
        if self.paths.retained_marker.exists():
            if self.paths.retained_marker.read_bytes() != payload:
                raise SecurityIntegrationError(
                    "security_integration_retained_marker_changed"
                )
            return
        _write_exclusive(
            self.paths.retained_marker,
            payload,
            self._fsync,
        )

    def _report(self) -> SecurityIntegrationReport:
        assert self._state is not None
        source = _artifact(self._state, "source")
        safety = _artifact(self._state, "safety_copy")
        target = _artifact(self._state, "encrypted_database")
        backup = _artifact(self._state, "encrypted_backup")
        if any(
            item.sha256 is None for item in (source, safety, target, backup)
        ):
            raise SecurityIntegrationError(
                "security_integration_report_incomplete"
            )
        return SecurityIntegrationReport(
            phase=SecurityIntegrationPhase(self._state.phase),
            journal_revision=self._state.revision,
            document_count=len(self._state.documents),
            source_sha256=source.sha256 or "",
            safety_copy_sha256=safety.sha256 or "",
            encrypted_database_sha256=target.sha256 or "",
            encrypted_backup_sha256=backup.sha256 or "",
            source_retained=self.paths.retained_marker.is_file(),
            reopened=(
                "fresh_reopen_verified" in self._state.completed_checks
            ),
        )

    def _target_factory(
        self,
        database_key: DatabaseKey,
        *,
        validate_schema: bool = True,
        read_only: bool = False,
    ) -> SecurityIntegrationConnectionFactory:
        return SecurityIntegrationConnectionFactory.sqlcipher(
            path=self.paths.encrypted_database,
            provider=self._provider,
            key_loader=lambda: self._database_key_loader(
                self._dmk_loader()
            ),
            expected_key_id=database_key.key_id,
            expected_key_generation=database_key.generation,
            validator=(
                security_integration_database_validator(
                    installation_id=self.installation_id,
                    database_context_id=self.database_context_id,
                    migration_id=self.migration_id,
                )
                if validate_schema
                else None
            ),
            read_only=read_only,
        )

    def _ensure_encrypted_database(
        self,
        database_key: DatabaseKey,
    ) -> None:
        factory = self._target_factory(database_key)
        if self.paths.encrypted_database.exists():
            raw_factory = self._target_factory(
                database_key,
                validate_schema=False,
            )
            with closing(raw_factory.open_existing()) as connection:
                try:
                    security_integration_database_validator(
                        installation_id=self.installation_id,
                        database_context_id=self.database_context_id,
                        migration_id=self.migration_id,
                    )(connection)
                    return
                except SecurityIntegrationError:
                    pass
            quarantine = self.paths.root / (
                ".incomplete-target-"
                f"{self._new_uuid('security_integration_quarantine_id_invalid')}"
                ".quarantine"
            )
            if quarantine.exists() or quarantine.is_symlink():
                raise SecurityIntegrationError(
                    "security_integration_target_quarantine_exists"
                )
            try:
                os.replace(self.paths.encrypted_database, quarantine)
                _fsync_directory(self.paths.root, self._fsync)
            except OSError:
                raise SecurityIntegrationError(
                    "security_integration_target_quarantine_failed"
                ) from None
        transfer_plaintext_to_sqlcipher(
            source_factory=self._source_factory(),
            target_factory=factory,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            created_at=format_utc(self._clock.utc_now()),
        )

    def _source_factory(self) -> SecurityIntegrationConnectionFactory:
        return SecurityIntegrationConnectionFactory.plaintext_source(
            self.paths.source_database
        )

    def _document_adapter(
        self,
        factory: SecurityIntegrationConnectionFactory,
    ) -> SecurityDocumentApplicationAdapter:
        return SecurityDocumentApplicationAdapter(
            paths=self.paths,
            factory=factory,
            service=self._document_service,
            dmk_loader=self._dmk_loader,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
        )

    def _backup_adapter(
        self,
        database_key: DatabaseKey,
    ) -> SecurityEncryptedBackupAdapter:
        factory = self._target_factory(database_key, read_only=True)
        with closing(factory.open_existing()) as connection:
            sqlite_version = str(
                connection.execute("SELECT sqlite_version()").fetchone()[0]
            )
            sqlcipher_version = str(
                connection.execute("PRAGMA cipher_version").fetchone()[0]
            )
        service = SyntheticEncryptedBackupServiceV1(
            random_source=self._random,
            clock=self._clock,
            sqlcipher_provider=self._provider,
            fault_injector=self._fault,
            sqlcipher_guard_validator=integration_backup_sqlcipher_guard(
                installation_id=self.installation_id,
                database_context_id=self.database_context_id,
                migration_id=self.migration_id,
            ),
        )
        return SecurityEncryptedBackupAdapter(
            paths=self.paths,
            service=service,
            document_service=self._document_service,
            database_factory=factory,
            dmk_loader=self._dmk_loader,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            context=BackupContainerContextV1(
                installation_id=self.installation_id,
                database_context_id=self.database_context_id,
                app_version=self._app_version,
                sqlite_version=sqlite_version,
                sqlcipher_version=sqlcipher_version,
            ),
        )

    def _state_keys(
        self,
        dmk: LoadedDataMasterKey,
    ) -> tuple[bytes, bytes]:
        context = {
            "database_context_id": self.database_context_id,
            "migration_generation": self.migration_generation,
            "migration_id": self.migration_id,
        }
        journal = derive_domain_separated_key(
            dmk,
            purpose=SECURITY_INTEGRATION_JOURNAL_AUTH_PURPOSE,
            derivation_version=1,
            context=context,
        )
        anchor = derive_domain_separated_key(
            dmk,
            purpose=SECURITY_INTEGRATION_REPLAY_AUTH_PURPOSE,
            derivation_version=1,
            context=context,
        )
        return journal.key_material, anchor.key_material

    def _load_keys(self) -> tuple[LoadedDataMasterKey, DatabaseKey]:
        dmk = self._dmk_loader()
        if len(dmk.key_material) != 32:
            raise SecurityIntegrationError(
                "security_integration_dmk_invalid"
            )
        database_key = self._database_key_loader(dmk)
        if len(database_key.key_material) != 32:
            raise SecurityIntegrationError(
                "security_integration_database_key_invalid"
            )
        return dmk, database_key

    def _validate_plaintext_source(self) -> None:
        source = self.paths.source_database
        if (
            source.is_symlink()
            or not source.is_file()
            or not self._source_closed_probe(source)
            or not self._app_instance_available()
        ):
            raise SecurityIntegrationError(
                "security_integration_plaintext_source_unavailable"
            )
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(source) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                raise SecurityIntegrationError(
                    "security_integration_plaintext_source_not_quiet"
                )
        with source.open("rb") as handle:
            if handle.read(len(_SQLITE_HEADER)) != _SQLITE_HEADER:
                raise SecurityIntegrationError(
                    "security_integration_plaintext_header_invalid"
                )
        with closing(self._source_factory().open_existing()) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            if (
                len(integrity) != 1
                or str(integrity[0][0]) != "ok"
                or version != DATABASE_COMPATIBILITY_VERSION
            ):
                raise SecurityIntegrationError(
                    "security_integration_plaintext_schema_invalid"
                )

    def _require_gate_bound_paths(self) -> None:
        resolved = SecurityIntegrationGate()._validate_root(
            str(self.paths.root)
        )
        if resolved != self.paths:
            raise SecurityIntegrationError(
                "security_integration_path_binding_invalid"
            )

    def _require_state_context(
        self,
        state: SecurityIntegrationJournalV1,
        dmk: LoadedDataMasterKey,
        database_key: DatabaseKey,
    ) -> None:
        if (
            state.installation_id != self.installation_id
            or state.database_context_id != self.database_context_id
            or state.migration_id != self.migration_id
            or state.migration_generation != self.migration_generation
            or state.dmk_key_id != dmk.key_id
            or state.dmk_key_generation != dmk.generation
            or state.database_key_id != database_key.key_id
            or state.database_key_generation != database_key.generation
            or state.root_sha256 != _path_sha256(self.paths.root)
        ):
            raise SecurityIntegrationError(
                "security_integration_crossbinding_invalid"
            )

    def _require_anchor_context(
        self,
        anchor: SecurityIntegrationReplayAnchorV1,
        state: SecurityIntegrationJournalV1,
        digest: str,
    ) -> None:
        if (
            anchor.installation_id != self.installation_id
            or anchor.database_context_id != self.database_context_id
            or anchor.migration_id != self.migration_id
            or anchor.migration_generation != self.migration_generation
            or anchor.root_sha256 != state.root_sha256
        ):
            raise SecurityIntegrationError(
                "security_integration_anchor_context_invalid"
            )
        if anchor.pending is None and (
            anchor.journal_revision != state.revision
            or anchor.journal_sha256 != digest
        ):
            raise SecurityIntegrationError(
                "security_integration_anchor_replay_invalid"
            )
        if anchor.pending is not None and not (
            (
                anchor.journal_revision == state.revision
                and anchor.journal_sha256 == digest
            )
            or (
                anchor.pending.journal_revision == state.revision
                and anchor.pending.journal_sha256 == digest
            )
        ):
            raise SecurityIntegrationError(
                "security_integration_anchor_replay_invalid"
            )

    def _require_document_sources_match(
        self,
        plans: tuple[SecurityIntegrationDocumentPlan, ...],
        sources,
    ) -> None:
        by_id = {item.source_document_id: item for item in sources}
        if set(by_id) != {item.source_document_id for item in plans}:
            raise SecurityIntegrationError(
                "security_integration_document_inventory_changed"
            )
        for plan in plans:
            source = by_id[plan.source_document_id]
            if (
                source.plaintext_size != plan.plaintext_size
                or source.plaintext_sha256 != plan.plaintext_sha256
                or source.source_path_sha256 != plan.source_path_sha256
            ):
                raise SecurityIntegrationError(
                    "security_integration_document_source_changed"
                )

    def _validate_phase_artifacts(
        self,
        state: SecurityIntegrationJournalV1,
    ) -> None:
        observed = {
            item.role: item for item in self._capture_artifacts()
        }
        phase = SecurityIntegrationPhase(state.phase)
        required = {
            SecurityIntegrationPhase.PREFLIGHT: {"source"},
            SecurityIntegrationPhase.BACKUP_VERIFIED: {
                "source",
                "safety_copy",
            },
            SecurityIntegrationPhase.DATABASE_MIGRATED: {
                "source",
                "safety_copy",
                "encrypted_database",
            },
            SecurityIntegrationPhase.DOCUMENTS_PREPARED: {
                "source",
                "safety_copy",
                "encrypted_database",
            },
            SecurityIntegrationPhase.REFERENCES_SWITCHED: {
                "source",
                "safety_copy",
                "encrypted_database",
            },
            SecurityIntegrationPhase.ENCRYPTED_BACKUP_VERIFIED: {
                "source",
                "safety_copy",
                "encrypted_database",
                "encrypted_backup",
            },
            SecurityIntegrationPhase.REOPEN_VERIFIED: {
                "source",
                "safety_copy",
                "encrypted_database",
                "encrypted_backup",
            },
            SecurityIntegrationPhase.COMPLETED: {
                "source",
                "safety_copy",
                "encrypted_database",
                "encrypted_backup",
            },
        }.get(phase)
        if required is None:
            raise SecurityIntegrationError(
                "security_integration_phase_invalid"
            )
        persisted = {item.role: item for item in state.artifacts}
        for role in required:
            if (
                role == "encrypted_database"
                and phase
                in {
                    SecurityIntegrationPhase.DATABASE_MIGRATED,
                    SecurityIntegrationPhase.DOCUMENTS_PREPARED,
                }
            ):
                continue
            if (
                observed[role].sha256 is None
                or persisted[role].sha256 != observed[role].sha256
                or persisted[role].size != observed[role].size
            ):
                raise SecurityIntegrationError(
                    f"security_integration_{role}_artifact_changed"
                )
        if "encrypted_database" in required:
            _dmk, database_key = self._load_keys()
            with closing(
                self._target_factory(
                    database_key,
                    read_only=True,
                ).open_existing()
            ):
                pass
        if phase in {
            SecurityIntegrationPhase.DOCUMENTS_PREPARED,
            SecurityIntegrationPhase.REFERENCES_SWITCHED,
            SecurityIntegrationPhase.ENCRYPTED_BACKUP_VERIFIED,
            SecurityIntegrationPhase.REOPEN_VERIFIED,
            SecurityIntegrationPhase.COMPLETED,
        }:
            for plan in state.documents:
                if (
                    plan.container_name is None
                    or plan.container_sha256 is None
                ):
                    raise SecurityIntegrationError(
                        "security_integration_document_evidence_missing"
                    )
                _size, observed_hash = _hash_file(
                    self.paths.document_storage / plan.container_name
                )
                if observed_hash != plan.container_sha256:
                    raise SecurityIntegrationError(
                        "security_integration_document_container_changed"
                    )
        if phase in {
            SecurityIntegrationPhase.REFERENCES_SWITCHED,
            SecurityIntegrationPhase.ENCRYPTED_BACKUP_VERIFIED,
            SecurityIntegrationPhase.REOPEN_VERIFIED,
            SecurityIntegrationPhase.COMPLETED,
        }:
            _dmk, database_key = self._load_keys()
            self._document_adapter(
                self._target_factory(
                    database_key,
                    read_only=True,
                )
            ).verify_active(state.documents)
        if phase is SecurityIntegrationPhase.COMPLETED and (
            not self.paths.retained_marker.is_file()
        ):
            raise SecurityIntegrationError(
                "security_integration_retained_marker_missing"
            )

    def _capture_artifacts(
        self,
    ) -> tuple[SecurityIntegrationArtifact, ...]:
        return tuple(
            _capture_artifact(role, path, self.paths.root)
            for role, path in (
                ("source", self.paths.source_database),
                ("safety_copy", self.paths.safety_copy),
                ("encrypted_database", self.paths.encrypted_database),
                ("encrypted_backup", self.paths.encrypted_backup),
            )
        )

    def _has_started_artifacts(self) -> bool:
        return any(
            path.exists() or path.is_symlink()
            for path in (
                self.paths.safety_copy,
                self.paths.encrypted_database,
                self.paths.encrypted_backup,
                self.paths.retained_marker,
            )
        )

    def _require_storage_inventory(
        self,
        state: SecurityIntegrationJournalV1 | None,
    ) -> None:
        allowed_ids = (
            set()
            if state is None
            else {plan.storage_id for plan in state.documents}
        )
        try:
            entries = tuple(self.paths.document_storage.iterdir())
        except OSError:
            raise SecurityIntegrationError(
                "security_integration_document_storage_invalid"
            ) from None
        for entry in entries:
            if entry.name == SYNTHETIC_DOCUMENT_STORAGE_MARKER:
                continue
            if _is_allowed_document_storage_name(
                entry.name,
                allowed_ids,
            ):
                continue
            raise SecurityIntegrationError(
                "security_integration_document_storage_mixed"
            )

    def _new_uuid(self, code: str) -> str:
        value = self._random.uuid4()
        try:
            validate_uuid4(value)
            return value
        except Exception:
            raise SecurityIntegrationError(code) from None


def prepare_security_integration_test_layout(
    *,
    root: Path,
    environ: Mapping[str, str],
) -> SecurityIntegrationPaths:
    """Create only an explicitly gated empty synthetic integration layout."""
    if (
        environ.get("JKM_SECURITY_INTEGRATION_TEST") != "1"
        or environ.get("JKM_SECURITY_INTEGRATION_ROOT") != str(root)
        or not Path(root).is_absolute()
        or not Path(root).name.startswith("jkm-security-integration-")
    ):
        raise SecurityIntegrationError(
            "security_integration_layout_gate_invalid"
        )
    base = Path(root)
    try:
        base.parent.resolve(strict=True).relative_to(
            Path(tempfile.gettempdir()).resolve(strict=True)
        )
    except (OSError, RuntimeError, ValueError):
        raise SecurityIntegrationError(
            "security_integration_layout_root_invalid"
        ) from None
    if base.exists() or base.is_symlink():
        raise SecurityIntegrationError(
            "security_integration_layout_exists"
        )
    try:
        base.mkdir(mode=0o700)
        os.chmod(base, 0o700)
        sources = base / "sources"
        storage = base / "storage"
        exports = base / "exports"
        for directory in (sources, storage, exports):
            directory.mkdir(mode=0o700)
            os.chmod(directory, 0o700)
        for path, payload in (
            (
                base / SECURITY_INTEGRATION_ROOT_MARKER,
                b"jenaplan-security-integration-test-root-v1\n",
            ),
            (
                base / SECURITY_INTEGRATION_SOURCE_MARKER,
                b"jenaplan-security-integration-plaintext-source-v1\n",
            ),
            (
                base / SYNTHETIC_BACKUP_TEST_ROOT_MARKER,
                SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES,
            ),
            (
                base / SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
                SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
            ),
            (
                storage / SYNTHETIC_DOCUMENT_STORAGE_MARKER,
                SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
            ),
            (
                exports / SYNTHETIC_DOCUMENT_EXPORT_MARKER,
                SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES,
            ),
        ):
            _write_exclusive(path, payload, os.fsync)
    except SecurityIntegrationError:
        raise
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_layout_create_failed"
        ) from None
    return SecurityIntegrationGate().require_active(environ)


def _capture_artifact(
    role: str,
    path: Path,
    root: Path,
) -> SecurityIntegrationArtifact:
    relative = path.relative_to(root).as_posix()
    if not path.exists():
        if path.is_symlink():
            raise SecurityIntegrationError(
                "security_integration_artifact_symlink"
            )
        return SecurityIntegrationArtifact(role, relative, None, None)
    size, digest = _hash_file(path)
    return SecurityIntegrationArtifact(role, relative, size, digest)


def _artifact(
    state: SecurityIntegrationJournalV1,
    role: str,
) -> SecurityIntegrationArtifact:
    return next(item for item in state.artifacts if item.role == role)


def _copy_exclusive(
    source: Path,
    target: Path,
    fsync: Callable[[int], None],
) -> None:
    source_fd: int | None = None
    target_fd: int | None = None
    try:
        source_flags = os.O_RDONLY
        target_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            source_flags |= os.O_NOFOLLOW
            target_flags |= os.O_NOFOLLOW
        source_fd = os.open(source, source_flags)
        target_fd = os.open(target, target_flags, 0o600)
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            _write_all(target_fd, chunk)
        os.fchmod(target_fd, 0o600)
        fsync(target_fd)
        _fsync_directory(target.parent, fsync)
    except FileExistsError:
        raise SecurityIntegrationError(
            "security_integration_safety_copy_exists"
        ) from None
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_safety_copy_failed"
        ) from None
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if target_fd is not None:
            os.close(target_fd)


def _write_exclusive(
    path: Path,
    payload: bytes,
    fsync: Callable[[int], None],
) -> None:
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o600)
        _write_all(descriptor, payload)
        os.fchmod(descriptor, 0o600)
        fsync(descriptor)
        _fsync_directory(path.parent, fsync)
    except FileExistsError:
        raise SecurityIntegrationError(
            "security_integration_target_exists"
        ) from None
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_write_failed"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short write")
        offset += written


def _fsync_directory(
    directory: Path,
    fsync: Callable[[int], None],
) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        fsync(descriptor)
    finally:
        os.close(descriptor)


def _hash_file(path: Path) -> tuple[int, str]:
    try:
        status = os.lstat(path)
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            raise SecurityIntegrationError(
                "security_integration_artifact_invalid"
            )
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
        final = os.lstat(path)
        if (
            (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns)
            != (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
            or size != status.st_size
        ):
            raise SecurityIntegrationError(
                "security_integration_artifact_changed"
            )
        return size, digest.hexdigest()
    except SecurityIntegrationError:
        raise
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_artifact_read_failed"
        ) from None


def _path_sha256(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _is_allowed_document_storage_name(
    name: str,
    storage_ids: set[str],
) -> bool:
    for storage_id in storage_ids:
        published = f"{storage_id}.w1.jkmedoc"
        if name == published:
            return True
        prefix = f".{published}."
        if name.startswith(prefix) and name.endswith(".retained"):
            run_id = name[len(prefix) : -len(".retained")]
            try:
                validate_uuid4(run_id)
                return True
            except Exception:
                continue
    return False


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise SecurityIntegrationError(
            "security_integration_state_format_invalid"
        ) from None


def _require_safe_restore_name(value: str) -> None:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"restore-[A-Za-z0-9._-]{1,80}", value)
        or value in {".", ".."}
    ):
        raise SecurityIntegrationError(
            "security_integration_restore_name_invalid"
        )


def _error_code(error: BaseException, fallback: str) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{0,79}",
        code,
    ):
        return code
    return fallback
