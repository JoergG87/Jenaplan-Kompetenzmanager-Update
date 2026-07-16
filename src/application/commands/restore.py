"""Application boundary for verification and staging-only restore preparation."""

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


class RestoreApplicationService:
    """Expose explicit restore preparation steps, never a live restore command."""

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
