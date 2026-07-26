"""Desktop projection boundary for backup and restore operations."""

from __future__ import annotations

from pathlib import Path

from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
    VerifyBackupQuery,
)
from src.application.commands.restore import (
    CreateRestoreHandoffCommand,
    CreateRestoreSafetyBackupCommand,
    PrepareRestoreStagingCommand,
    RestoreApplicationService,
    VerifyPreparedRestoreQuery,
    VerifyRestoreBackupQuery,
)
from src.core.restore_runtime import RestoreHandoffResult, RuntimeInstanceLock
from src.desktop_app.backup_restore_operations import (
    BackupRestoreOperation,
    BackupRestoreOperationType,
    DiscoverVerifiedBackupsQuery,
)
from src.desktop_app.restore_worker import (
    RestoreWorkerProcess,
    launch_restore_worker,
)
from src.desktop_app.runtime import RuntimePaths
from src.desktop_app.view_models.backup_restore_view_model import (
    BackupSummaryViewModel,
    RestorePreviewViewModel,
)


class BackupRestoreDesktopAdapter:
    """Build technical commands and privacy-minimized desktop projections."""

    def __init__(
        self,
        runtime_paths: RuntimePaths,
        *,
        app_version: str,
        build_commit: str = "unknown",
        source_tree_state: str | None = None,
        lock: RuntimeInstanceLock | None = None,
        backup_service: BackupApplicationService | None = None,
        restore_service: RestoreApplicationService | None = None,
    ) -> None:
        self.paths = runtime_paths
        self.app_version = app_version
        self.build_commit = build_commit
        self.source_tree_state = source_tree_state
        self.lock = lock
        self.backup_service = backup_service or BackupApplicationService()
        self.restore_service = restore_service or RestoreApplicationService()

    def create_backup_operation(
        self,
        target_directory: Path,
    ) -> BackupRestoreOperation:
        return BackupRestoreOperation(
            BackupRestoreOperationType.CREATE_BACKUP,
            CreateBackupCommand(
                database_path=self.paths.database,
                runtime_paths=self.paths,
                target_path=Path(target_directory),
                app_version=self.app_version,
                build_commit=self.build_commit,
                source_tree_state=self.source_tree_state,
            ),
        )

    def discover_verified_backups_operation(self) -> BackupRestoreOperation:
        candidates = tuple(sorted(self.paths.backups.glob("*.jkmbackup")))
        return BackupRestoreOperation(
            BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS,
            DiscoverVerifiedBackupsQuery(candidates),
        )

    @staticmethod
    def verify_backup_operation(path: Path) -> BackupRestoreOperation:
        return BackupRestoreOperation(
            BackupRestoreOperationType.VERIFY_BACKUP,
            VerifyBackupQuery(Path(path)),
        )

    @staticmethod
    def verify_restore_operation(path: Path) -> BackupRestoreOperation:
        return BackupRestoreOperation(
            BackupRestoreOperationType.VERIFY_RESTORE_BACKUP,
            VerifyRestoreBackupQuery(Path(path)),
        )

    def prepare_restore_operation(self, path: Path) -> BackupRestoreOperation:
        return BackupRestoreOperation(
            BackupRestoreOperationType.PREPARE_RESTORE_STAGING,
            PrepareRestoreStagingCommand(Path(path), self.paths),
        )

    def verify_prepared_restore_operation(
        self,
        restore_id: str,
    ) -> BackupRestoreOperation:
        return BackupRestoreOperation(
            BackupRestoreOperationType.VERIFY_PREPARED_RESTORE,
            VerifyPreparedRestoreQuery(restore_id, self.paths),
        )

    def create_restore_safety_backup_operation(
        self,
        restore_id: str,
    ) -> BackupRestoreOperation:
        """Expose the existing service for flows that explicitly require it."""
        return BackupRestoreOperation(
            BackupRestoreOperationType.CREATE_RESTORE_SAFETY_BACKUP,
            CreateRestoreSafetyBackupCommand(
                restore_id,
                self.paths,
                self.app_version,
                self.build_commit,
                self.source_tree_state,
            ),
        )

    def create_restore_handoff(
        self,
        preview: RestorePreviewViewModel,
    ) -> RestoreHandoffResult:
        if not preview.restore_id:
            raise RuntimeError("Die Wiederherstellung wurde nicht vorbereitet.")
        return self.restore_service.create_handoff(
            CreateRestoreHandoffCommand(
                preview.archive_path,
                preview.restore_id,
                self.paths,
                self.app_version,
                self.build_commit,
                self.source_tree_state,
            )
        )

    def launch_prepared_restore(
        self,
        handoff: RestoreHandoffResult,
    ) -> RestoreWorkerProcess:
        if self.lock is None:
            raise RuntimeError("Der sichere Wiederherstellungsmodus ist nicht verfügbar.")
        return launch_restore_worker(
            handoff=handoff.path,
            nonce=handoff.nonce,
            lock=self.lock,
        )

    @staticmethod
    def backup_summary(verified: object) -> BackupSummaryViewModel:
        manifest = verified.manifest
        return BackupSummaryViewModel(
            created_at=manifest.created_at,
            file_name=verified.path.name,
            size_bytes=verified.archive_size_bytes,
            verified=True,
        )

    @classmethod
    def latest_backup_summary(
        cls,
        verified_backups: tuple[object, ...],
    ) -> BackupSummaryViewModel | None:
        summaries = tuple(cls.backup_summary(item) for item in verified_backups)
        return max(summaries, key=lambda item: item.created_at, default=None)

    @staticmethod
    def restore_preview(result: object) -> RestorePreviewViewModel:
        return RestorePreviewViewModel.from_preview(
            result.preview,
            result.compatibility.status.value,
            result.path,
        )

    @staticmethod
    def staged_restore_preview(
        result: object,
        archive_path: Path,
    ) -> RestorePreviewViewModel:
        return RestorePreviewViewModel.from_preview(
            result.preview,
            result.target_compatibility.status.value,
            archive_path,
            restore_id=result.restore_id,
        )
