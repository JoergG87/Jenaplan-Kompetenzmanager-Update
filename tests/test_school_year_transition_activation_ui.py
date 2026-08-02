"""Focused SJ-3C.6 confirmation, lifecycle and privacy checks."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

from src.application.school_year_transition_execution import (
    SchoolYearTransitionExecutionCounts,
    SchoolYearTransitionExecutionResult,
)
from src.desktop_app.dialogs.school_year_transition_preview_dialog import (
    SchoolYearTransitionPreviewDialog,
)
from src.desktop_app.school_year_transition_activation import (
    SchoolYearTransitionActivationErrorInfo,
    SchoolYearTransitionActivationWorker,
)
from src.desktop_app.theme import MOTION_DIALOG_MS
from src.application.school_year_transition_step_up import (
    SchoolYearTransitionStepUpResult,
)
from src.security.domain import AuthenticationStatus
from tests.test_school_year_transition_preview_ui import _plan


class StubActivationController(QObject):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.start_count = 0
        self.is_busy = False

    def start(self, **_kwargs: object) -> bool:
        if self.is_busy:
            return False
        self.start_count += 1
        self.is_busy = True
        return True

    def complete(self, result: object) -> None:
        self.is_busy = False
        self.succeeded.emit(result)
        self.finished.emit()

    def fail(self, code: str, retry_after_seconds: int = 0) -> None:
        self.is_busy = False
        self.failed.emit(
            SchoolYearTransitionActivationErrorInfo(
                code,
                retry_after_seconds,
            )
        )
        self.finished.emit()


def _resolved_plan():
    return _plan().repeat_year_level_three("S-3", "C-3")


def _result() -> SchoolYearTransitionExecutionResult:
    return SchoolYearTransitionExecutionResult(
        transition_id="hidden-transition-id",
        from_school_year_id="hidden-source-id",
        to_school_year_id="hidden-target-id",
        operation_token="hidden-operation-token",
        plan_sha256="a" * 64,
        backup_sha256="b" * 64,
        counts=SchoolYearTransitionExecutionCounts(
            student_count=3,
            enrolled_count=3,
            exited_count=0,
            advance_1_to_2_count=1,
            advance_2_to_3_count=1,
            other_course_count=0,
            repeat_year_level_three_count=1,
            group_change_count=0,
        ),
        completed_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
    )


def _running_dialog() -> tuple[
    SchoolYearTransitionPreviewDialog,
    StubActivationController,
]:
    controller = StubActivationController()
    dialog = SchoolYearTransitionPreviewDialog(
        _resolved_plan(),
        activation_controller=controller,
    )
    dialog.show()
    dialog.confirmation_checkbox.setChecked(True)
    dialog.password_field.setText("correct horse battery staple")
    dialog._start_activation()
    return dialog, controller


def _finish_native_close(
    app: QApplication,
    dialog: SchoolYearTransitionPreviewDialog,
) -> None:
    if QApplication.platformName().casefold() not in {"offscreen", "minimal"}:
        for _attempt in range(40):
            if not dialog.isVisible():
                break
            QTest.qWait(max(25, MOTION_DIALOG_MS // 4))
            app.processEvents()
    app.processEvents()


def test_unresolved_plan_and_confirmation_inputs_gate_activation() -> None:
    app = QApplication.instance() or QApplication([])
    controller = StubActivationController()
    unresolved = SchoolYearTransitionPreviewDialog(
        _plan(),
        activation_controller=controller,
    )
    unresolved.confirmation_checkbox.setChecked(True)
    unresolved.password_field.setText("correct horse battery staple")
    assert not unresolved.activate_button.isEnabled()

    dialog = SchoolYearTransitionPreviewDialog(
        _resolved_plan().select_other_group("S-1", "G-B"),
        activation_controller=controller,
    )
    assert not dialog.activate_button.isEnabled()
    dialog.confirmation_checkbox.setChecked(True)
    assert not dialog.activate_button.isEnabled()
    dialog.password_field.setText("correct horse battery staple")
    assert dialog.activate_button.isEnabled()
    assert dialog.password_field.echoMode() is QLineEdit.EchoMode.Password
    assert dialog.activate_button.text() == (
        "Schuljahr 2026/27 verbindlich aktivieren"
    )
    assert dialog.summary_labels["Stammgruppenänderungen"].text() == "1"
    app.processEvents()


def test_double_start_close_escape_and_enter_are_guarded() -> None:
    app = QApplication.instance() or QApplication([])
    dialog, controller = _running_dialog()
    dialog._start_activation()
    assert controller.start_count == 1
    assert not dialog.close_button.isEnabled()
    assert dialog.close_blocked
    dialog.reject()
    assert dialog.isVisible()
    dialog.done(QDialog.DialogCode.Accepted)
    assert dialog.isVisible()
    assert not dialog.close()
    assert dialog.isVisible()
    close_event = QCloseEvent()
    dialog.closeEvent(close_event)
    assert not close_event.isAccepted()
    QTest.keyClick(dialog, Qt.Key.Key_Return)
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert dialog.isVisible()
    app.processEvents()


def test_close_paths_are_allowed_before_activation() -> None:
    app = QApplication.instance() or QApplication([])
    for close_path in ("reject", "done", "close", "escape", "native"):
        dialog = SchoolYearTransitionPreviewDialog(_resolved_plan())
        dialog.show()
        assert not dialog.close_blocked
        if close_path == "reject":
            dialog.reject()
        elif close_path == "done":
            dialog.done(QDialog.DialogCode.Rejected)
        elif close_path == "close":
            close_result = dialog.close()
            if QApplication.platformName().casefold() in {
                "offscreen",
                "minimal",
            }:
                assert close_result
        elif close_path == "escape":
            QTest.keyClick(dialog, Qt.Key.Key_Escape)
        else:
            close_event = QCloseEvent()
            dialog.closeEvent(close_event)
            if QApplication.platformName().casefold() in {
                "offscreen",
                "minimal",
            }:
                assert close_event.isAccepted()
            else:
                _finish_native_close(app, dialog)
                assert not dialog.isVisible()
        if close_path != "native":
            _finish_native_close(app, dialog)
            assert not dialog.isVisible()
    app.processEvents()


def test_close_paths_stay_blocked_during_backup_and_transition() -> None:
    app = QApplication.instance() or QApplication([])
    for phase in ("backup_creating", "school_year_activating"):
        dialog, controller = _running_dialog()
        controller.progress.emit(phase)
        assert dialog.close_blocked
        dialog.reject()
        dialog.done(QDialog.DialogCode.Accepted)
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        close_event = QCloseEvent()
        dialog.closeEvent(close_event)
        assert not close_event.isAccepted()
        assert not dialog.close()
        assert dialog.isVisible()
        controller.fail("transition_execution_failed")
        dialog.close()
    app.processEvents()


def test_safe_failure_and_success_release_close_but_recovery_does_not() -> None:
    app = QApplication.instance() or QApplication([])
    safe_failure, safe_controller = _running_dialog()
    safe_controller.progress.emit("backup_creating")
    safe_controller.fail("transition_backup_failed")
    assert not safe_failure.close_blocked
    safe_failure.close()
    _finish_native_close(app, safe_failure)
    assert not safe_failure.isVisible()

    success, success_controller = _running_dialog()
    success_controller.progress.emit("school_year_activating")
    success_controller.complete(_result())
    assert not success.close_blocked
    success.close()
    _finish_native_close(app, success)
    assert not success.isVisible()

    recovery, recovery_controller = _running_dialog()
    recovery_controller.progress.emit("completion_checking")
    recovery_controller.fail("transition_recovery_required")
    assert recovery.close_blocked
    recovery.reject()
    recovery.done(QDialog.DialogCode.Accepted)
    assert not recovery.close()
    QTest.keyClick(recovery, Qt.Key.Key_Escape)
    assert recovery.isVisible()
    app.processEvents()


def test_progress_success_and_accessibility_hide_technical_details() -> None:
    app = QApplication.instance() or QApplication([])
    controller = StubActivationController()
    dialog = SchoolYearTransitionPreviewDialog(
        _resolved_plan(),
        activation_controller=controller,
    )
    dialog.confirmation_checkbox.setChecked(True)
    dialog.password_field.setText("correct horse battery staple")
    dialog._start_activation()
    for phase in (
        "writers_draining",
        "backup_creating",
        "assignments_checking",
        "school_year_activating",
        "completion_checking",
    ):
        controller.progress.emit(phase)
    controller.complete(_result())
    visible = dialog.execution_status.label.text()
    assert "2026/27" in visible
    assert "Sicherheitsbackup" in visible
    assert "vollständig abgeschlossen" in visible
    assert "0 ungelöst" in visible
    assert "hidden-" not in visible
    assert "aaaa" not in visible
    assert "bbbb" not in visible
    assert dialog.close_button.text() == "Fertig"
    assert dialog.confirmation_checkbox.accessibleName()
    assert dialog.password_field.accessibleName()
    assert dialog.activate_button.accessibleName()
    assert dialog.execution_status.accessibleName()
    app.processEvents()


def test_sanitized_failure_projections_cover_required_states() -> None:
    app = QApplication.instance() or QApplication([])
    expected = {
        "password_invalid": "keine Änderungen begonnen",
        "transition_backup_failed": "Daten wurden nicht geändert",
        "transition_sources_changed": "neue Vorschau",
        "transition_execution_failed": "sicher zurückgenommen",
        "transition_recovery_required": "Wiederherstellung geprüft",
    }
    for code, phrase in expected.items():
        controller = StubActivationController()
        dialog = SchoolYearTransitionPreviewDialog(
            _resolved_plan(),
            activation_controller=controller,
        )
        dialog.confirmation_checkbox.setChecked(True)
        dialog.password_field.setText("correct horse battery staple")
        dialog._start_activation()
        controller.fail(code)
        visible = dialog.execution_status.label.text()
        assert phrase in visible
        assert code not in visible
        assert "Traceback" not in visible
        assert "/Users/" not in visible
        if code == "transition_recovery_required":
            assert not dialog.activate_button.isEnabled()
            assert not dialog.close_button.isEnabled()
            assert dialog._terminal_state
    app.processEvents()


class _FakeStepUp:
    def __init__(self, status: AuthenticationStatus) -> None:
        self.status = status
        self.calls: list[str] = []

    def authenticate(self, **_kwargs: object) -> SchoolYearTransitionStepUpResult:
        self.calls.append("step_up")
        return SchoolYearTransitionStepUpResult(
            status=self.status,
            authorization=(object() if self.status is AuthenticationStatus.AUTHENTICATED else None),
        )


class _FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, **kwargs: object) -> SchoolYearTransitionExecutionResult:
        callback = kwargs["progress_callback"]
        for phase in (
            "writers_draining",
            "backup_creating",
            "assignments_checking",
            "school_year_activating",
            "completion_checking",
        ):
            self.calls.append(phase)
            callback(phase)
        return _result()


def test_worker_calls_step_up_before_backend_and_wrong_password_stops() -> None:
    invalid_step_up = _FakeStepUp(AuthenticationStatus.INVALID_CREDENTIALS)
    invalid_executor = _FakeExecutor()
    invalid_worker = SchoolYearTransitionActivationWorker(
        plan=_resolved_plan(),
        password="wrong password",
        step_up_service=invalid_step_up,
        executor=invalid_executor,
    )
    failures: list[SchoolYearTransitionActivationErrorInfo] = []
    invalid_worker.failed.connect(failures.append)
    invalid_worker.run()
    assert invalid_step_up.calls == ["step_up"]
    assert invalid_executor.calls == []
    assert failures[0].code == "password_invalid"

    valid_step_up = _FakeStepUp(AuthenticationStatus.AUTHENTICATED)
    valid_executor = _FakeExecutor()
    valid_worker = SchoolYearTransitionActivationWorker(
        plan=_resolved_plan(),
        password="correct horse battery staple",
        step_up_service=valid_step_up,
        executor=valid_executor,
    )
    phases: list[str] = []
    valid_worker.progress.connect(phases.append)
    valid_worker.run()
    assert valid_step_up.calls == ["step_up"]
    assert phases == valid_executor.calls
