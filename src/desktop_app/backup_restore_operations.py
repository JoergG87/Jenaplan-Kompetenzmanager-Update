"""Qt worker boundary for long-running backup and restore operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import logging
from pathlib import Path
from typing import Final

from PySide6.QtCore import QObject, QThread, Signal, Slot

from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
    VerifyBackupQuery,
)
from src.application.commands.restore import (
    CreateRestoreSafetyBackupCommand,
    PrepareRestoreStagingCommand,
    RestoreApplicationService,
    VerifyPreparedRestoreQuery,
    VerifyRestoreBackupQuery,
)


LOGGER = logging.getLogger(__name__)


class BackupRestoreOperationType(StrEnum):
    """The bounded set of technical operations allowed on a Qt worker."""

    CREATE_BACKUP = "create_backup"
    DISCOVER_VERIFIED_BACKUPS = "discover_verified_backups"
    VERIFY_BACKUP = "verify_backup"
    VERIFY_RESTORE_BACKUP = "verify_restore_backup"
    PREPARE_RESTORE_STAGING = "prepare_restore_staging"
    VERIFY_PREPARED_RESTORE = "verify_prepared_restore"
    CREATE_RESTORE_SAFETY_BACKUP = "create_restore_safety_backup"


class BackupRestoreProgressPhase(StrEnum):
    """Non-percentage phases emitted without user-facing exception text."""

    PREPARING_BACKUP = "preparing_backup"
    VERIFYING_BACKUP = "verifying_backup"
    VERIFYING_RESTORE = "verifying_restore"
    PREPARING_RESTORE = "preparing_restore"
    VERIFYING_PREPARED_RESTORE = "verifying_prepared_restore"
    PREPARING_SAFETY_BACKUP = "preparing_safety_backup"


class BackupRestoreOperationsState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHING = "finishing"


@dataclass(frozen=True)
class DiscoverVerifiedBackupsQuery:
    """Immutable candidate set for the existing settings status projection."""

    paths: tuple[Path, ...]

    def __post_init__(self) -> None:
        if any(path.suffix != ".jkmbackup" for path in self.paths):
            raise ValueError("Only .jkmbackup candidates may be discovered.")


_PAYLOAD_TYPES: Final = {
    BackupRestoreOperationType.CREATE_BACKUP: CreateBackupCommand,
    BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS: (
        DiscoverVerifiedBackupsQuery
    ),
    BackupRestoreOperationType.VERIFY_BACKUP: VerifyBackupQuery,
    BackupRestoreOperationType.VERIFY_RESTORE_BACKUP: VerifyRestoreBackupQuery,
    BackupRestoreOperationType.PREPARE_RESTORE_STAGING: PrepareRestoreStagingCommand,
    BackupRestoreOperationType.VERIFY_PREPARED_RESTORE: VerifyPreparedRestoreQuery,
    BackupRestoreOperationType.CREATE_RESTORE_SAFETY_BACKUP: (
        CreateRestoreSafetyBackupCommand
    ),
}

_PROGRESS_PHASES: Final = {
    BackupRestoreOperationType.CREATE_BACKUP: (
        BackupRestoreProgressPhase.PREPARING_BACKUP
    ),
    BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS: (
        BackupRestoreProgressPhase.VERIFYING_BACKUP
    ),
    BackupRestoreOperationType.VERIFY_BACKUP: (
        BackupRestoreProgressPhase.VERIFYING_BACKUP
    ),
    BackupRestoreOperationType.VERIFY_RESTORE_BACKUP: (
        BackupRestoreProgressPhase.VERIFYING_RESTORE
    ),
    BackupRestoreOperationType.PREPARE_RESTORE_STAGING: (
        BackupRestoreProgressPhase.PREPARING_RESTORE
    ),
    BackupRestoreOperationType.VERIFY_PREPARED_RESTORE: (
        BackupRestoreProgressPhase.VERIFYING_PREPARED_RESTORE
    ),
    BackupRestoreOperationType.CREATE_RESTORE_SAFETY_BACKUP: (
        BackupRestoreProgressPhase.PREPARING_SAFETY_BACKUP
    ),
}


@dataclass(frozen=True)
class BackupRestoreOperation:
    """One immutable, type-checked Application-Service invocation."""

    operation_type: BackupRestoreOperationType
    payload: object

    def __post_init__(self) -> None:
        expected_type = _PAYLOAD_TYPES[self.operation_type]
        if not isinstance(self.payload, expected_type):
            raise TypeError(
                f"{self.operation_type.value} requires {expected_type.__name__}."
            )


@dataclass(frozen=True)
class BackupRestoreOperationErrorInfo:
    """Privacy-minimized technical failure data for main-thread mapping."""

    operation_type: BackupRestoreOperationType
    error_class: str


class BackupRestoreOperationWorker(QObject):
    """Execute exactly one existing Application-Service call off the UI thread."""

    started = Signal()
    progress = Signal(object)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(
        self,
        operation: BackupRestoreOperation,
        *,
        backup_service: BackupApplicationService,
        restore_service: RestoreApplicationService,
    ) -> None:
        super().__init__()
        self.operation = operation
        self.backup_service = backup_service
        self.restore_service = restore_service

    @Slot()
    def run(self) -> None:
        """Emit one terminal result and always finish without touching Qt widgets."""
        self.started.emit()
        self.progress.emit(_PROGRESS_PHASES[self.operation.operation_type])
        try:
            result = self._execute()
        except Exception as error:
            self._log_sanitized_traceback(error)
            self.failed.emit(
                BackupRestoreOperationErrorInfo(
                    self.operation.operation_type,
                    type(error).__name__,
                )
            )
        else:
            self.succeeded.emit(result)
        finally:
            self.finished.emit()

    def _execute(self) -> object:
        operation_type = self.operation.operation_type
        payload = self.operation.payload
        if operation_type is BackupRestoreOperationType.CREATE_BACKUP:
            return self.backup_service.create(payload)
        if operation_type is BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS:
            verified = []
            for path in payload.paths:
                try:
                    verified.append(
                        self.backup_service.verify(VerifyBackupQuery(path))
                    )
                except Exception:
                    continue
            return tuple(verified)
        if operation_type is BackupRestoreOperationType.VERIFY_BACKUP:
            return self.backup_service.verify(payload)
        if operation_type is BackupRestoreOperationType.VERIFY_RESTORE_BACKUP:
            return self.restore_service.verify(payload)
        if operation_type is BackupRestoreOperationType.PREPARE_RESTORE_STAGING:
            return self.restore_service.prepare_staging(payload)
        if operation_type is BackupRestoreOperationType.VERIFY_PREPARED_RESTORE:
            return self.restore_service.verify_prepared(payload)
        if operation_type is BackupRestoreOperationType.CREATE_RESTORE_SAFETY_BACKUP:
            return self.restore_service.create_safety_backup(payload)
        raise AssertionError("Unregistered backup/restore operation.")

    def _log_sanitized_traceback(self, error: Exception) -> None:
        sanitized_error = RuntimeError("technical details redacted")
        LOGGER.error(
            "Backup/restore worker failed: operation=%s error_class=%s",
            self.operation.operation_type.value,
            type(error).__name__,
            exc_info=(RuntimeError, sanitized_error, error.__traceback__),
        )


class BackupRestoreOperationsController(QObject):
    """Own one worker thread at a time until its actual termination."""

    started = Signal(object)
    progress = Signal(object, object)
    succeeded = Signal(object, object)
    failed = Signal(object, object)
    finished = Signal(object)
    rejected = Signal(object)
    state_changed = Signal(str)

    def __init__(
        self,
        *,
        backup_service: BackupApplicationService | None = None,
        restore_service: RestoreApplicationService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.backup_service = backup_service or BackupApplicationService()
        self.restore_service = restore_service or RestoreApplicationService()
        self._state = BackupRestoreOperationsState.IDLE
        self._thread: QThread | None = None
        self._worker: BackupRestoreOperationWorker | None = None
        self._operation: BackupRestoreOperation | None = None
        self._terminal_result: object | None = None
        self._terminal_error: BackupRestoreOperationErrorInfo | None = None

    @property
    def state(self) -> BackupRestoreOperationsState:
        return self._state

    @property
    def is_busy(self) -> bool:
        return self._state is not BackupRestoreOperationsState.IDLE

    @property
    def has_running_thread(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(self, operation: BackupRestoreOperation) -> bool:
        """Start one operation, rejecting overlap without queuing or cancellation."""
        if self.is_busy:
            self.rejected.emit(operation.operation_type)
            return False
        self._operation = operation
        self._terminal_result = None
        self._terminal_error = None
        self._set_state(BackupRestoreOperationsState.RUNNING)

        thread = QThread(self)
        worker = BackupRestoreOperationWorker(
            operation,
            backup_service=self.backup_service,
            restore_service=self.restore_service,
        )
        worker.moveToThread(thread)
        self._thread = thread
        self._worker = worker

        thread.started.connect(worker.run)
        worker.started.connect(self._on_worker_started)
        worker.progress.connect(self._on_worker_progress)
        worker.succeeded.connect(self._on_worker_succeeded)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(self._on_worker_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        return True

    @Slot()
    def _on_worker_started(self) -> None:
        if self._operation is not None:
            self.started.emit(self._operation.operation_type)

    @Slot(object)
    def _on_worker_progress(self, phase: BackupRestoreProgressPhase) -> None:
        if self._operation is not None:
            self.progress.emit(self._operation.operation_type, phase)

    @Slot(object)
    def _on_worker_succeeded(self, result: object) -> None:
        if self._terminal_result is None and self._terminal_error is None:
            self._terminal_result = result

    @Slot(object)
    def _on_worker_failed(self, error_info: BackupRestoreOperationErrorInfo) -> None:
        if self._terminal_result is None and self._terminal_error is None:
            self._terminal_error = error_info

    @Slot()
    def _on_worker_finished(self) -> None:
        if self._state is BackupRestoreOperationsState.RUNNING:
            self._set_state(BackupRestoreOperationsState.FINISHING)

    @Slot()
    def _on_thread_finished(self) -> None:
        operation = self._operation
        result = self._terminal_result
        error_info = self._terminal_error
        self._thread = None
        self._worker = None
        self._operation = None
        self._terminal_result = None
        self._terminal_error = None
        self._set_state(BackupRestoreOperationsState.IDLE)
        if operation is None:
            return
        if error_info is not None:
            self.failed.emit(operation.operation_type, error_info)
        elif result is not None:
            self.succeeded.emit(operation.operation_type, result)
        else:
            self.failed.emit(
                operation.operation_type,
                BackupRestoreOperationErrorInfo(
                    operation.operation_type,
                    "WorkerProtocolError",
                ),
            )
        self.finished.emit(operation.operation_type)

    def _set_state(self, state: BackupRestoreOperationsState) -> None:
        if self._state is state:
            return
        self._state = state
        self.state_changed.emit(state.value)
