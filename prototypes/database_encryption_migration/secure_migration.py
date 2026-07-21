"""Sprint-5-only Envelope and Journal integration for the synthetic prototype."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re

from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DatabaseKeyEnvelopeError,
    DatabaseKeyEnvelopeService,
    derive_database_key_registry_auth_key,
    derive_migration_journal_auth_key,
)
from src.security.infrastructure.database_key_envelope_repository import (
    DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.migration_journal_repository import (
    AuthenticatedMigrationJournalRepository,
    MIGRATION_JOURNAL_FILENAME,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from src.security.migration_journal import (
    MigrationPhase,
    MigrationRecoveryEvaluator,
    RecoveryDecision,
    capture_file_evidence,
    new_migration_journal,
    transition_migration_journal,
)

from .migration import (
    FailurePoint,
    MigrationPaths,
    MigrationPrototypeEngine,
    MigrationPrototypeError,
    MigrationReport,
    validate_migration_preflight,
)


class PrototypeInterruptionPoint(str, Enum):
    AFTER_BACKUP = "after_backup"
    DURING_EXPORT = "during_export"
    AFTER_EXPORT = "after_export"
    DURING_VALIDATION = "during_validation"
    AFTER_REOPEN = "after_reopen"


class SimulatedProcessInterruption(BaseException):
    """Test-only abrupt-process signal intentionally outside Exception cleanup."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SecureMigrationPrototypeReport:
    migration: MigrationReport
    migration_id: str
    database_context_id: str
    database_key_id: str
    database_key_generation: int
    envelope_path: Path
    journal_path: Path


class SecureMigrationPrototypeEngine:
    """Use Product-Key and Journal foundations only inside one synthetic root."""

    def __init__(
        self,
        *,
        migration_engine: MigrationPrototypeEngine | None = None,
        random_source=None,
        clock=None,
        permissions=None,
    ) -> None:
        self._migration_engine = migration_engine or MigrationPrototypeEngine()
        self._random = random_source or SystemRandomSource()
        self._clock = clock or SystemClock()
        self._permissions = permissions or PlatformFilePermissionManager()

    def run(
        self,
        paths: MigrationPaths,
        *,
        dmk: LoadedDataMasterKey,
        database_context_id: str | None = None,
        interruption_point: PrototypeInterruptionPoint | None = None,
        failure_point: FailurePoint | None = None,
    ) -> SecureMigrationPrototypeReport:
        envelope_repository = self._envelope_repository(paths)
        journal_repository = self._journal_repository(paths)
        if envelope_repository.exists() or journal_repository.path.exists():
            raise MigrationPrototypeError("secure_migration_run_already_exists")
        validate_migration_preflight(paths)

        context_id = database_context_id or self._random.uuid4()
        migration_id = self._random.uuid4()
        envelope_service = DatabaseKeyEnvelopeService(
            repository=envelope_repository,
            random_source=self._random,
            clock=self._clock,
        )
        envelope_service.create_pending(
            dmk, database_context_id=context_id, generation=1
        )
        envelope_service.activate(dmk, generation=1)
        database_key = envelope_service.load_active(dmk, expected_generation=1)
        auth_key = derive_migration_journal_auth_key(
            dmk, migration_id=migration_id
        )
        state = new_migration_journal(
            migration_id=migration_id,
            data_context_id=context_id,
            database_key_id=database_key.key_id,
            database_key_generation=database_key.generation,
            wrapping_dmk_key_id=dmk.key_id,
            wrapping_dmk_generation=dmk.generation,
            planned_paths={
                "source": paths.source.name,
                "backup": paths.backup.name,
                "target": paths.target.name,
            },
            source_evidence=capture_file_evidence(
                paths.root, role="source", relative_path=paths.source.name
            ),
            now=self._clock.utc_now(),
        )
        journal_repository.create(state, auth_key)
        key_buffer = bytearray(database_key.key_material)

        def persist(
            phase: MigrationPhase,
            *,
            evidence=None,
            checks=None,
            error_class: str | None = None,
        ) -> None:
            nonlocal state
            replacement = transition_migration_journal(
                state,
                phase,
                now=self._clock.utc_now(),
                file_evidence=evidence,
                completed_checks=checks,
                error_class=error_class,
            )
            journal_repository.save(state, replacement, auth_key)
            state = replacement

        def observer(event: str, observed_paths: MigrationPaths) -> None:
            if event == "preflight_started":
                persist(MigrationPhase.PREFLIGHT_STARTED)
            elif event == "source_verified":
                observed = capture_file_evidence(
                    observed_paths.root,
                    role="source",
                    relative_path=observed_paths.source.name,
                )
                if observed != state.file_evidence["source"]:
                    raise MigrationPrototypeError("migration_source_changed")
                persist(
                    MigrationPhase.SOURCE_VERIFIED,
                    checks=("source_identity", "source_integrity"),
                )
            elif event == "backup_started":
                persist(MigrationPhase.BACKUP_STARTED)
            elif event == "backup_created":
                evidence = dict(state.file_evidence)
                evidence["backup"] = capture_file_evidence(
                    observed_paths.root,
                    role="backup",
                    relative_path=observed_paths.backup.name,
                )
                persist(MigrationPhase.BACKUP_CREATED, evidence=evidence)
            elif event == "backup_verified":
                persist(
                    MigrationPhase.BACKUP_VERIFIED,
                    checks=(*state.completed_checks, "backup_integrity"),
                )
                self._interrupt_if(
                    interruption_point, PrototypeInterruptionPoint.AFTER_BACKUP
                )
            elif event == "target_creation_started":
                persist(MigrationPhase.TARGET_CREATION_STARTED)
            elif event == "target_created":
                evidence = dict(state.file_evidence)
                evidence["target"] = capture_file_evidence(
                    observed_paths.root,
                    role="target",
                    relative_path=observed_paths.target.name,
                )
                persist(MigrationPhase.TARGET_CREATED, evidence=evidence)
            elif event == "export_started":
                persist(MigrationPhase.EXPORT_STARTED)
            elif event == "export_in_progress":
                self._interrupt_if(
                    interruption_point, PrototypeInterruptionPoint.DURING_EXPORT
                )
            elif event == "export_completed":
                evidence = dict(state.file_evidence)
                evidence["target"] = capture_file_evidence(
                    observed_paths.root,
                    role="target",
                    relative_path=observed_paths.target.name,
                )
                persist(
                    MigrationPhase.EXPORT_COMPLETED,
                    evidence=evidence,
                    checks=(*state.completed_checks, "export_committed"),
                )
                self._interrupt_if(
                    interruption_point, PrototypeInterruptionPoint.AFTER_EXPORT
                )
            elif event == "validation_started":
                persist(MigrationPhase.VALIDATION_STARTED)
            elif event == "validation_in_progress":
                self._interrupt_if(
                    interruption_point, PrototypeInterruptionPoint.DURING_VALIDATION
                )
            elif event == "validation_completed":
                persist(
                    MigrationPhase.VALIDATION_COMPLETED,
                    checks=(*state.completed_checks, "full_validation"),
                )
            elif event == "reopen_started":
                persist(MigrationPhase.REOPEN_STARTED)
            elif event == "reopen_verified":
                persist(
                    MigrationPhase.REOPEN_VERIFIED,
                    checks=(*state.completed_checks, "reopen_integrity"),
                )
                self._interrupt_if(
                    interruption_point, PrototypeInterruptionPoint.AFTER_REOPEN
                )
            elif event == "rollback_started":
                persist(MigrationPhase.ROLLBACK_STARTED)
            elif event == "rollback_completed":
                persist(MigrationPhase.ROLLBACK_COMPLETED)

        try:
            migration = self._migration_engine.migrate(
                paths,
                key_material=key_buffer,
                failure_point=failure_point,
                phase_observer=observer,
            )
            persist(
                MigrationPhase.COMPLETED,
                checks=(*state.completed_checks, "synthetic_prototype_completed"),
            )
            return SecureMigrationPrototypeReport(
                migration=migration,
                migration_id=migration_id,
                database_context_id=context_id,
                database_key_id=database_key.key_id,
                database_key_generation=database_key.generation,
                envelope_path=envelope_repository.path,
                journal_path=journal_repository.path,
            )
        except Exception as error:
            if state.phase not in {
                MigrationPhase.FAILED,
                MigrationPhase.BLOCKED,
                MigrationPhase.COMPLETED,
            }:
                code = getattr(error, "code", "secure_migration_failed")
                if not isinstance(code, str) or not re.fullmatch(
                    r"[a-z][a-z0-9_]{0,79}", code
                ):
                    code = "secure_migration_failed"
                persist(MigrationPhase.FAILED, error_class=code)
            try:
                envelope_service.fail(dmk, generation=database_key.generation)
            except DatabaseKeyEnvelopeError:
                pass
            raise
        finally:
            for index in range(len(key_buffer)):
                key_buffer[index] = 0

    def recovery_decision(
        self, paths: MigrationPaths, *, dmk: LoadedDataMasterKey
    ) -> RecoveryDecision:
        try:
            envelope_service = DatabaseKeyEnvelopeService(
                repository=self._envelope_repository(paths),
                random_source=self._random,
                clock=self._clock,
            )
            database_key = envelope_service.load_active(
                dmk, expected_generation=1
            )
            journal_repository = self._journal_repository(paths)
            migration_id, key_id, generation, kdf_version = (
                journal_repository.peek_context()
            )
            if (
                key_id != dmk.key_id
                or generation != dmk.generation
                or kdf_version != 1
            ):
                return RecoveryDecision.BLOCK_MANUAL_REVIEW
            auth_key = derive_migration_journal_auth_key(
                dmk, migration_id=migration_id
            )
            state = journal_repository.load(auth_key)
            envelope_repository = self._envelope_repository(paths)
            registry_context = envelope_repository.peek_context()
            registry_auth_key = derive_database_key_registry_auth_key(
                dmk, database_context_id=registry_context
            )
            if (
                state.data_context_id
                != envelope_repository.database_context_id(registry_auth_key)
                or state.database_key_id != database_key.key_id
                or state.database_key_generation != database_key.generation
            ):
                return RecoveryDecision.BLOCK_MANUAL_REVIEW
            return MigrationRecoveryEvaluator().decide(
                state, workspace=paths.root
            )
        except Exception:
            return RecoveryDecision.BLOCK_MANUAL_REVIEW

    def _envelope_repository(
        self, paths: MigrationPaths
    ) -> FileDatabaseKeyEnvelopeRepository:
        return FileDatabaseKeyEnvelopeRepository(
            paths.root / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
            self._permissions,
        )

    def _journal_repository(
        self, paths: MigrationPaths
    ) -> AuthenticatedMigrationJournalRepository:
        return AuthenticatedMigrationJournalRepository(
            paths.root / MIGRATION_JOURNAL_FILENAME,
            self._permissions,
        )

    @staticmethod
    def _interrupt_if(
        actual: PrototypeInterruptionPoint | None,
        expected: PrototypeInterruptionPoint,
    ) -> None:
        if actual is expected:
            raise SimulatedProcessInterruption(
                f"simulated_process_interruption_{expected.value}"
            )
