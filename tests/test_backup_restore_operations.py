"""Qt-threading and shell-lifecycle tests for settings backup operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import time
from unittest import mock

from PySide6.QtCore import QEvent, QEventLoop, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QDialog

from src.application.commands.backup import CreateBackupCommand, VerifyBackupQuery
from src.application.commands.restore import (
    CreateRestoreSafetyBackupCommand,
    PrepareRestoreStagingCommand,
    VerifyPreparedRestoreQuery,
    VerifyRestoreBackupQuery,
)
from src.desktop_app.backup_restore_operations import (
    BackupRestoreOperation,
    BackupRestoreOperationWorker,
    BackupRestoreOperationsController,
    BackupRestoreOperationType,
    BackupRestoreOperationErrorInfo,
    BackupRestoreProgressPhase,
)
from src.core.sqlite_store import SQLiteDatabase
from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.desktop_app.runtime import runtime_paths
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.shell import AppShell
from src.desktop_app.view_models.backup_restore_view_model import (
    RestorePreviewViewModel,
)


@dataclass(frozen=True)
class _Paths:
    root: Path = Path("/tmp/runtime")
    database: Path = Path("/tmp/runtime/database.sqlite")
    documents: Path = Path("/tmp/runtime/documents")
    backups: Path = Path("/tmp/runtime/backups")


class _BackupService:
    def __init__(self, *, result: object = None, delay: float = 0, error=None) -> None:
        self.result = object() if result is None else result
        self.delay = delay
        self.error = error
        self.calls: list[str] = []
        self.completed = False

    def _run(self, name: str) -> object:
        self.calls.append(name)
        if self.delay:
            time.sleep(self.delay)
        self.completed = True
        if self.error is not None:
            raise self.error
        return self.result

    def create(self, _command) -> object:
        return self._run("create")

    def verify(self, _query) -> object:
        return self._run("verify")


class _RestoreService:
    def __init__(self, *, result: object = None, error=None) -> None:
        self.result = object() if result is None else result
        self.error = error
        self.calls: list[str] = []

    def _run(self, name: str) -> object:
        self.calls.append(name)
        if self.error is not None:
            raise self.error
        return self.result

    def verify(self, _query) -> object:
        return self._run("verify")

    def prepare_staging(self, _command) -> object:
        return self._run("prepare_staging")

    def verify_prepared(self, _query) -> object:
        return self._run("verify_prepared")

    def create_safety_backup(self, _command) -> object:
        return self._run("create_safety_backup")


class _EventLoopProbeBackupService:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.completed = False

    def create(self, _command) -> object:
        self.entered.set()
        if not self.release.wait(timeout=3):
            raise RuntimeError("event_loop_probe_not_released")
        self.completed = True
        return object()


def _create_operation() -> BackupRestoreOperation:
    paths = _Paths()
    return BackupRestoreOperation(
        BackupRestoreOperationType.CREATE_BACKUP,
        CreateBackupCommand(
            paths.database,
            paths,
            paths.backups,
            "0.1.2",
            "test-build",
        ),
    )


def _wait_for_controller(
    controller: BackupRestoreOperationsController,
    *,
    timeout_ms: int = 3000,
) -> None:
    if not controller.is_busy:
        return
    loop = QEventLoop()
    timed_out: list[bool] = []
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: (timed_out.append(True), loop.quit()))
    controller.finished.connect(lambda _operation: loop.quit())
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    assert not timed_out


class TestBackupRestoreOperationWorker:
    def test_success_and_finished_are_each_emitted_once(self) -> None:
        result = object()
        worker = BackupRestoreOperationWorker(
            _create_operation(),
            backup_service=_BackupService(result=result),
            restore_service=_RestoreService(),
        )
        events: list[str] = []
        results: list[object] = []
        worker.started.connect(lambda: events.append("started"))
        worker.progress.connect(lambda _phase: events.append("progress"))
        worker.succeeded.connect(lambda value: results.append(value))
        worker.failed.connect(lambda _error: events.append("failed"))
        worker.finished.connect(lambda: events.append("finished"))

        worker.run()

        assert events == ["started", "progress", "finished"]
        assert results == [result]

    def test_failure_has_no_result_and_finishes_once(self) -> None:
        worker = BackupRestoreOperationWorker(
            _create_operation(),
            backup_service=_BackupService(
                error=RuntimeError("/private/path and personal content")
            ),
            restore_service=_RestoreService(),
        )
        results: list[object] = []
        failures: list[object] = []
        finished: list[bool] = []
        worker.succeeded.connect(results.append)
        worker.failed.connect(failures.append)
        worker.finished.connect(lambda: finished.append(True))

        with mock.patch(
            "src.desktop_app.backup_restore_operations.LOGGER.error"
        ) as log_error:
            worker.run()

        assert results == []
        assert len(failures) == 1
        assert failures[0].error_class == "RuntimeError"
        assert finished == [True]
        assert "/private/path" not in str(log_error.call_args)

    def test_all_restore_service_operations_use_the_injected_service(self) -> None:
        paths = _Paths()
        cases = (
            (
                BackupRestoreOperationType.VERIFY_RESTORE_BACKUP,
                VerifyRestoreBackupQuery(Path("candidate.jkmbackup")),
                "verify",
            ),
            (
                BackupRestoreOperationType.PREPARE_RESTORE_STAGING,
                PrepareRestoreStagingCommand(Path("candidate.jkmbackup"), paths),
                "prepare_staging",
            ),
            (
                BackupRestoreOperationType.VERIFY_PREPARED_RESTORE,
                VerifyPreparedRestoreQuery("RST-123", paths),
                "verify_prepared",
            ),
            (
                BackupRestoreOperationType.CREATE_RESTORE_SAFETY_BACKUP,
                CreateRestoreSafetyBackupCommand(
                    "RST-123", paths, "0.1.2", "test-build"
                ),
                "create_safety_backup",
            ),
        )
        for operation_type, payload, expected_call in cases:
            service = _RestoreService()
            worker = BackupRestoreOperationWorker(
                BackupRestoreOperation(operation_type, payload),
                backup_service=_BackupService(),
                restore_service=service,
            )
            worker.run()
            assert service.calls == [expected_call]


class TestBackupRestoreOperationsController:
    @classmethod
    def setup_class(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_slow_backup_keeps_main_event_loop_responsive(self) -> None:
        service = _EventLoopProbeBackupService()
        controller = BackupRestoreOperationsController(
            backup_service=service,
            restore_service=_RestoreService(),
        )
        ticks_while_running: list[bool] = []
        timer = QTimer()
        timer.setInterval(5)
        def observe_running_worker() -> None:
            if service.entered.is_set() and not service.completed:
                ticks_while_running.append(True)
                service.release.set()

        timer.timeout.connect(observe_running_worker)
        timer.start()

        assert controller.start(_create_operation())
        _wait_for_controller(controller)
        timer.stop()

        assert ticks_while_running
        assert not controller.has_running_thread

    def test_overlap_is_rejected_and_state_waits_for_thread_end(self) -> None:
        controller = BackupRestoreOperationsController(
            backup_service=_BackupService(delay=0.1),
            restore_service=_RestoreService(),
        )
        states: list[str] = []
        rejected: list[object] = []
        successes: list[object] = []
        failures: list[object] = []
        finished: list[object] = []
        controller.state_changed.connect(states.append)
        controller.rejected.connect(rejected.append)
        controller.succeeded.connect(lambda _kind, value: successes.append(value))
        controller.failed.connect(lambda _kind, value: failures.append(value))
        controller.finished.connect(finished.append)

        assert controller.start(_create_operation())
        assert not controller.start(
            BackupRestoreOperation(
                BackupRestoreOperationType.VERIFY_BACKUP,
                VerifyBackupQuery(Path("candidate.jkmbackup")),
            )
        )
        _wait_for_controller(controller)

        assert states == ["running", "finishing", "idle"]
        assert len(rejected) == 1
        assert len(successes) == 1
        assert failures == []
        assert len(finished) == 1
        assert not controller.is_busy

    def test_page_change_is_blocked_and_actions_recover_after_finish(self) -> None:
        screen = SettingsScreen()
        screen.show_page("backup_restore")
        controller = BackupRestoreOperationsController(
            backup_service=_BackupService(delay=0.1),
            restore_service=_RestoreService(),
        )
        controller.state_changed.connect(
            lambda state: screen.set_operation_active(state != "idle")
        )
        controller.progress.connect(
            lambda _kind, phase: screen.set_operation_active(True, phase.value)
        )

        assert controller.start(_create_operation())
        QApplication.processEvents()
        screen.show_overview()

        assert screen.current_page == "backup_restore"
        assert not screen.backup_create_button.isEnabled()
        assert not screen.operation_progress.isHidden()
        _wait_for_controller(controller)
        assert screen.backup_create_button.isEnabled()
        assert screen.operation_progress.isHidden()
        assert not screen.restore_start_button.isEnabled()


class TestBackupRestoreShellLifecycle:
    @classmethod
    def setup_class(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _window(self, root: Path) -> AppShell:
        prepare_synthetic_test_root(root)
        paths = runtime_paths(root)
        for directory in (
            paths.root,
            paths.documents,
            paths.exports,
            paths.backups,
            paths.logs,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        database = SQLiteDatabase(paths.database)
        database.initialize_schema()
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO school_years(
                    school_year_id, label, start_date, end_date,
                    status, created_at, closed_at
                ) VALUES (
                    'SY-TEST-2025-26', '2025/26', '2025-08-01', '2026-07-31',
                    'current', '2025-07-01T08:00:00+00:00', NULL
                )
                """
            )
        return AppShell(paths.database, paths=paths)

    def test_backup_creation_returns_immediately_and_updates_status_on_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            verification = SimpleNamespace(
                manifest=SimpleNamespace(created_at="2026-07-17T10:00:00Z"),
                path=Path("created.jkmbackup"),
                archive_size_bytes=1024 * 1024,
            )
            window.backup_restore_operations.backup_service = _BackupService(
                result=SimpleNamespace(verification=verification),
                delay=0.15,
            )
            with mock.patch.object(
                window.backup_restore_adapter,
                "create_backup_operation",
                return_value=_create_operation(),
            ), mock.patch(
                "src.desktop_app.shell.QFileDialog.getExistingDirectory",
                return_value=temporary,
            ):
                started_at = time.monotonic()
                window.create_backup()
                elapsed = time.monotonic() - started_at

            assert elapsed < 0.1
            assert window.backup_restore_operations.is_busy
            assert not window.settings_screen.backup_create_button.isEnabled()
            _wait_for_controller(window.backup_restore_operations)
            assert "2026-07-17T10:00:00Z" in window.settings_screen.latest_backup_label.text()
            window.close()

    def test_existing_backup_status_is_discovered_asynchronously(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            candidate = window.runtime_paths.backups / "existing.jkmbackup"
            candidate.write_bytes(b"technical candidate")
            verification = SimpleNamespace(
                manifest=SimpleNamespace(created_at="2026-07-16T08:00:00Z"),
                path=candidate,
                archive_size_bytes=2048,
            )
            window.backup_restore_operations.backup_service = _BackupService(
                result=verification,
                delay=0.12,
            )

            window.settings_screen.show_page("backup_restore")

            assert window.backup_restore_operations.is_busy
            assert not window.settings_screen.backup_verify_button.isEnabled()
            _wait_for_controller(window.backup_restore_operations)
            assert "2026-07-16T08:00:00Z" in window.settings_screen.latest_backup_label.text()
            window.close()

    def test_failed_discovery_remains_unknown_and_can_be_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            operation = BackupRestoreOperationType.DISCOVER_VERIFIED_BACKUPS
            window._handle_backup_restore_failure(
                operation, BackupRestoreOperationErrorInfo(operation, "OSError")
            )
            assert not window._backup_status_loaded
            assert "nicht bestätigt" in window.settings_screen.latest_backup_label.text()
            with mock.patch.object(window.backup_restore_operations, "start") as start:
                window._load_backup_status()
                start.assert_called_once()
            window.close()

    def test_close_is_rejected_until_operation_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            window.backup_restore_operations.backup_service = _BackupService(
                delay=0.12
            )
            assert window.backup_restore_operations.start(_create_operation())
            event = QCloseEvent()
            window.closeEvent(event)
            assert not event.isAccepted()
            assert "sicher abgeschlossen" in window.settings_screen.operation_status_label.text()
            _wait_for_controller(window.backup_restore_operations)
            finished_event = QCloseEvent()
            window.closeEvent(finished_event)
            assert finished_event.isAccepted()

    def test_restore_process_starts_once_and_only_then_closes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            preview = RestorePreviewViewModel(
                "2026-07-17T10:00:00Z",
                "0.1.2",
                "exact",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                Path("candidate.jkmbackup"),
                "RST-123",
            )
            window._prepared_restore_preview = preview
            handoff = SimpleNamespace(path=Path("handoff.json"), nonce="nonce")
            started = SimpleNamespace(process=object(), parent_lifetime_fd=9)
            application = QApplication.instance()
            assert application is not None
            workspace = QDialog(window)
            workspace.show()
            with mock.patch.object(
                window.backup_restore_adapter,
                "create_restore_handoff",
                return_value=handoff,
            ) as create_handoff, mock.patch.object(
                window.backup_restore_adapter,
                "launch_prepared_restore",
                return_value=started,
            ) as launch, mock.patch.object(
                application,
                "quit",
            ) as quit_application, mock.patch.object(window, "close") as close:
                window._handle_backup_restore_success(
                    BackupRestoreOperationType.VERIFY_PREPARED_RESTORE,
                    SimpleNamespace(restore_id="RST-123"),
                )
                assert workspace.result() == QDialog.DialogCode.Rejected
                assert not workspace.isVisible()
                assert not window.isVisible()
                application.processEvents()

            create_handoff.assert_called_once_with(preview)
            launch.assert_called_once_with(handoff)
            assert window._restore_worker_process is started
            quit_application.assert_called_once_with()
            close.assert_called_once_with()

    def test_cipher_restore_confirmation_retains_ready_binding_until_worker_start(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            preview = RestorePreviewViewModel(
                "2026-08-09T12:00:00Z",
                "0.4.0",
                "exact",
                3,
                4,
                1,
                1,
                2,
                0,
                0,
                Path("candidate.jkmebackup"),
                "RST-FINAL-V4",
            )
            window.settings_screen.show_restore_preview(preview)
            confirm = object()
            confirmation = mock.Mock()
            confirmation.clickedButton.return_value = confirm
            operations: list[BackupRestoreOperation] = []

            with mock.patch(
                "src.desktop_app.shell.create_confirmation_message",
                return_value=(confirmation, confirm),
            ), mock.patch.object(
                window.backup_restore_operations,
                "start",
                side_effect=lambda operation: operations.append(operation) or True,
            ):
                window.start_restore()

            assert len(operations) == 1
            assert (
                operations[0].operation_type
                is BackupRestoreOperationType.VERIFY_PREPARED_RESTORE
            )
            assert operations[0].payload.restore_id == "RST-FINAL-V4"
            assert window._prepared_restore_preview is preview

            handoff = SimpleNamespace(
                path=Path("handoff.json"),
                nonce="nonce",
                restore_id="RST-FINAL-V4",
            )
            started = SimpleNamespace(process=object(), parent_lifetime_fd=9)
            with mock.patch.object(
                window.backup_restore_adapter,
                "create_restore_handoff",
                return_value=handoff,
            ) as create_handoff, mock.patch.object(
                window.backup_restore_adapter,
                "launch_prepared_restore",
                return_value=started,
            ) as launch, mock.patch.object(
                window,
                "_close_restore_workspaces",
            ), mock.patch(
                "src.desktop_app.shell.QTimer.singleShot",
            ):
                window._handle_backup_restore_success(
                    BackupRestoreOperationType.VERIFY_PREPARED_RESTORE,
                    SimpleNamespace(restore_id="RST-FINAL-V4"),
                )

            create_handoff.assert_called_once_with(preview)
            launch.assert_called_once_with(handoff)
            assert window._restore_worker_process is started
            window._restore_shutdown_in_progress = False
            window.close()

    def test_restore_worker_start_error_keeps_app_open_and_clears_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            window = self._window(Path(temporary))
            live_before = window.runtime_paths.database.read_bytes()
            preview = RestorePreviewViewModel(
                "2026-07-17T10:00:00Z",
                "0.1.2",
                "exact",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                Path("candidate.jkmbackup"),
                "RST-456",
            )
            window.settings_screen.show_restore_preview(preview)
            handoff = SimpleNamespace(path=Path("handoff.json"), nonce="nonce")
            application = QApplication.instance()
            assert application is not None
            workspace = QDialog(window)
            workspace.show()
            with mock.patch.object(
                window.backup_restore_adapter,
                "create_restore_handoff",
                return_value=handoff,
            ) as create_handoff, mock.patch.object(
                window.backup_restore_adapter,
                "launch_prepared_restore",
                side_effect=OSError("/private/hidden"),
            ) as launch, mock.patch.object(
                application,
                "quit",
            ) as quit_application, mock.patch.object(window, "close") as close:
                window._launch_verified_restore(preview)
                window._launch_verified_restore(preview)

            create_handoff.assert_called_once_with(preview)
            launch.assert_called_once_with(handoff)
            close.assert_not_called()
            quit_application.assert_not_called()
            assert workspace.isVisible()
            assert window.settings_screen.restore_preview is None
            assert "/private" not in window.settings_screen.restore_message.label.text()
            assert window.runtime_paths.database.read_bytes() == live_before
            workspace.done(QDialog.DialogCode.Rejected)
            window.close()
