"""Application boundary for restore preparation and productive recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

from src.core.backup import BackupVerifier, SQLiteBackupEngine
from src.core.restore import (
    PreparedRestoreVerificationResult,
    RestoreSafetyBackupResult,
    RestoreSafetyBackupService,
    RestoreStagingResult,
    RestoreStagingService,
    RestoreVerificationResult,
    RestoreVerifier,
)
from src.core.restore_runtime import (
    ProductiveRestoreService,
    RestoreExecutionResult,
    RestoreHandoffResult,
    RestoreHandoffService,
    RestoreRecoveryResult,
    RuntimeInstanceLock,
    confirm_restore_startup,
    recover_interrupted_restore,
)


class RuntimeRestorePathSet(Protocol):
    """Minimal injected runtime-path contract for restore preparation."""

    root: Path
    database: Path
    documents: Path
    backups: Path


@dataclass(frozen=True)
class VerifyRestoreBackupQuery:
    """Verify one backup and produce a technical restore preview."""

    path: Path


@dataclass(frozen=True)
class PrepareRestoreStagingCommand:
    """Prepare one new staging without changing any live path."""

    path: Path
    runtime_paths: RuntimeRestorePathSet
    restore_id: str | None = None


@dataclass(frozen=True)
class CreateRestoreSafetyBackupCommand:
    """Create a verified live-data safety backup for one prepared restore."""

    restore_id: str
    runtime_paths: RuntimeRestorePathSet
    app_version: str
    build_commit: str
    source_tree_state: str | None = None


@dataclass(frozen=True)
class VerifyPreparedRestoreQuery:
    """Repeat all prepared-staging checks for one technical restore ID."""

    restore_id: str
    runtime_paths: RuntimeRestorePathSet


@dataclass(frozen=True)
class CleanupRestoreStagingCommand:
    """Remove only one completed or failed, state-bound staging directory."""

    restore_id: str
    runtime_paths: RuntimeRestorePathSet


@dataclass(frozen=True)
class CreateRestoreHandoffCommand:
    """Create one runtime-bound, one-time worker handoff."""

    path: Path
    restore_id: str
    runtime_paths: RuntimeRestorePathSet
    app_version: str
    build_commit: str
    source_tree_state: str | None = None


@dataclass(frozen=True)
class ExecutePreparedRestoreCommand:
    """Execute one consumed handoff while the exclusive lock is held."""

    handoff_path: Path
    nonce: str
    lock: RuntimeInstanceLock


@dataclass(frozen=True)
class RecoverInterruptedRestoreCommand:
    """Recover the only open transaction before normal app startup."""

    runtime_root: Path


@dataclass(frozen=True)
class ConfirmRestoreStartupCommand:
    """Confirm one installed restore with its one-time resume token."""

    runtime_root: Path
    restore_id: str
    token: str


class RestoreApplicationService:
    """Expose explicit preparation, worker execution and startup recovery."""

    def __init__(
        self,
        verifier: RestoreVerifier | None = None,
        *,
        staging_service: RestoreStagingService | None = None,
        safety_backup_service: RestoreSafetyBackupService | None = None,
        backup_verifier: BackupVerifier | None = None,
        sqlite_engine: SQLiteBackupEngine | None = None,
        now: Callable[[], datetime] | None = None,
        restore_id_factory: Callable[[], str] | None = None,
        handoff_service: RestoreHandoffService | None = None,
        productive_restore_service: ProductiveRestoreService | None = None,
    ) -> None:
        backup_verifier = backup_verifier or BackupVerifier()
        self.verifier = verifier or RestoreVerifier(
            backup_verifier=backup_verifier
        )
        self.staging_service = staging_service or RestoreStagingService(
            backup_verifier=backup_verifier,
            restore_verifier=self.verifier,
            now=now,
            restore_id_factory=restore_id_factory,
        )
        self.safety_backup_service = (
            safety_backup_service
            or RestoreSafetyBackupService(
                now=now or (lambda: datetime.now(UTC)),
                sqlite_engine=sqlite_engine,
                verifier=backup_verifier,
            )
        )
        self.handoff_service = handoff_service or RestoreHandoffService(
            staging_service=self.staging_service,
            now=now,
        )
        self.productive_restore_service = (
            productive_restore_service
            or ProductiveRestoreService(
                staging_service=self.staging_service,
                safety_service=self.safety_backup_service,
                handoff_service=self.handoff_service,
                now=now,
            )
        )

    def verify(self, query: VerifyRestoreBackupQuery) -> RestoreVerificationResult:
        return self.verifier.verify(query.path)

    def prepare_staging(
        self,
        command: PrepareRestoreStagingCommand,
    ) -> RestoreStagingResult:
        paths = command.runtime_paths
        return self.staging_service.prepare(
            archive_path=command.path,
            runtime_root=paths.root,
            live_database=paths.database,
            live_documents=paths.documents,
            restore_id=command.restore_id,
        )

    def create_safety_backup(
        self,
        command: CreateRestoreSafetyBackupCommand,
    ) -> RestoreSafetyBackupResult:
        paths = command.runtime_paths
        self.staging_service.verify_prepared(
            runtime_root=paths.root,
            live_documents=paths.documents,
            restore_id=command.restore_id,
        )
        return self.safety_backup_service.create(
            restore_id=command.restore_id,
            runtime_root=paths.root,
            database_path=paths.database,
            documents_root=paths.documents,
            backups_root=paths.backups,
            app_version=command.app_version,
            build_commit=command.build_commit,
            source_tree_state=command.source_tree_state,
        )

    def verify_prepared(
        self,
        query: VerifyPreparedRestoreQuery,
    ) -> PreparedRestoreVerificationResult:
        paths = query.runtime_paths
        return self.staging_service.verify_prepared(
            runtime_root=paths.root,
            live_documents=paths.documents,
            restore_id=query.restore_id,
        )

    def cleanup_staging(self, command: CleanupRestoreStagingCommand) -> bool:
        return self.staging_service.cleanup(
            runtime_root=command.runtime_paths.root,
            restore_id=command.restore_id,
        )

    def create_handoff(
        self,
        command: CreateRestoreHandoffCommand,
    ) -> RestoreHandoffResult:
        return self.handoff_service.create(
            archive_path=command.path,
            runtime_paths=command.runtime_paths,
            restore_id=command.restore_id,
            app_version=command.app_version,
            build_commit=command.build_commit,
            source_tree_state=command.source_tree_state,
        )

    def execute_prepared_restore(
        self,
        command: ExecutePreparedRestoreCommand,
    ) -> RestoreExecutionResult:
        return self.productive_restore_service.execute(
            handoff_path=command.handoff_path,
            nonce=command.nonce,
            lock=command.lock,
        )

    @staticmethod
    def recover_interrupted(
        command: RecoverInterruptedRestoreCommand,
    ) -> RestoreRecoveryResult:
        return recover_interrupted_restore(command.runtime_root)

    @staticmethod
    def confirm_startup(
        command: ConfirmRestoreStartupCommand,
    ) -> RestoreRecoveryResult:
        return confirm_restore_startup(
            command.runtime_root,
            command.restore_id,
            command.token,
        )
