"""Preview-only integration from settings into the existing transition dialog."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sqlite3
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QObject, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton
from shiboken6 import isValid

from src.desktop_app.dialogs.school_year_transition_preview_dialog import (
    SchoolYearTransitionPreviewDialog,
)
from src.desktop_app.school_year_transition_activation import (
    SchoolYearTransitionActivationErrorInfo,
)
from src.application.school_year_transition_preview import (
    SchoolYearTransitionPreviewService,
)
from src.desktop_app.shell import AppShell
from src.desktop_app.theme import MOTION_DIALOG_MS
from src.security.application import AuthenticationResult
from src.security.domain import AuthenticationStatus
from tests.helpers.synthetic_v3 import create_pre_transition_v3_database


create_synthetic_v3_database = create_pre_transition_v3_database


class _LifecycleActivationController(QObject):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.is_busy = False

    def start(self, **_kwargs: object) -> bool:
        if self.is_busy:
            return False
        self.is_busy = True
        return True

    def fail(self, code: str) -> None:
        self.is_busy = False
        self.failed.emit(SchoolYearTransitionActivationErrorInfo(code))
        self.finished.emit()


def _database_snapshot(database_path: Path) -> tuple[str, ...]:
    with sqlite3.connect(database_path) as connection:
        return tuple(connection.iterdump())


def test_valid_settings_input_opens_transient_dialog_without_side_effects(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "settings-transition.sqlite"
    create_synthetic_v3_database(database_path)
    shell = AppShell(database_path)
    before = _database_snapshot(database_path)
    password_requests: list[bool] = []
    recovery_requests: list[bool] = []
    support_reset_requests: list[bool] = []
    shell.password_change_requested.connect(
        lambda: password_requests.append(True)
    )
    shell.recovery_codes_requested.connect(
        lambda: recovery_requests.append(True)
    )
    shell.support_reset_requested.connect(
        lambda: support_reset_requests.append(True)
    )
    opened_plans = []

    def inspect_dialog(dialog, owner) -> None:
        assert owner is shell
        assert dialog.parentWidget() is shell
        opened_plans.append(dialog.plan)
        button_texts = tuple(
            button.text().casefold()
            for button in dialog.findChildren(QPushButton)
        )
        assert any("verbindlich aktivieren" in text for text in button_texts)
        assert not dialog.activate_button.isEnabled()
        QTimer.singleShot(0, dialog.reject)

    with (
        patch.object(
            shell.backup_restore_operations,
            "start",
        ) as backup_or_restore_start,
        patch(
            "src.desktop_app.shell.prepare_maximized_workspace",
            side_effect=inspect_dialog,
        ) as execute_dialog,
    ):
        shell.open_school_year_transition_preview(
            "2026/27",
            date(2026, 8, 1),
            date(2027, 7, 31),
        )
        app.processEvents()

    after = _database_snapshot(database_path)
    assert execute_dialog.call_count == 1
    assert len(opened_plans) == 1
    assert opened_plans[0].planned_school_year_label == "2026/27"
    assert before == after
    backup_or_restore_start.assert_not_called()
    assert password_requests == []
    assert recovery_requests == []
    assert support_reset_requests == []
    shell.close()
    app.processEvents()


class _AcceptingPasswordService:
    def authenticate_password(self, _password: str) -> AuthenticationResult:
        return AuthenticationResult(AuthenticationStatus.AUTHENTICATED)


class _RejectingPasswordService:
    def authenticate_password(self, _password: str) -> AuthenticationResult:
        return AuthenticationResult(AuthenticationStatus.INVALID_CREDENTIALS)


def test_confirmed_settings_activation_changes_only_temporary_database(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "kompetenzmanager.sqlite"
    create_synthetic_v3_database(database_path)
    (tmp_path / "documents").mkdir()
    (tmp_path / "backups").mkdir()
    shell = AppShell(database_path)
    shell.configure_school_year_transition_activation(
        _AcceptingPasswordService()
    )
    before = _database_snapshot(database_path)
    opened = []

    def activate(dialog, owner) -> None:
        assert owner is shell
        assert dialog.parentWidget() is shell
        opened.append(dialog)

        def run_activation() -> None:
            dialog.plan = dialog.plan.repeat_year_level_three(
                "STD-TEST-003",
                "CRS-TEST-3",
            )
            dialog._refresh_from_plan()
            dialog.confirmation_checkbox.setChecked(True)
            dialog.password_field.setText("synthetisches Testpasswort")
            dialog.activate_button.click()
            loop = QEventLoop()
            dialog.activation_controller.finished.connect(loop.quit)
            QTimer.singleShot(60_000, loop.quit)
            if dialog.activation_controller.is_busy:
                loop.exec()
            assert not dialog.activation_controller.is_busy, (
                dialog.execution_status.label.text()
            )
            assert "verbindlich aktiviert" in dialog.execution_status.label.text()
            dialog.close_button.click()

        QTimer.singleShot(0, run_activation)

    with patch(
        "src.desktop_app.shell.prepare_maximized_workspace",
        side_effect=activate,
    ):
        shell.open_school_year_transition_preview(
            "2026/27",
            date(2026, 8, 1),
            date(2027, 7, 31),
        )
        app.processEvents()

    assert len(opened) == 1
    assert "2026/27" in shell.settings_screen.current_school_year_label.text()
    after = _database_snapshot(database_path)
    assert before != after
    with sqlite3.connect(database_path) as connection:
        current = connection.execute(
            "SELECT label FROM school_years WHERE status = 'current'"
        ).fetchone()
        transition_count = connection.execute(
            "SELECT count(*) FROM school_year_transitions"
        ).fetchone()[0]
        assert current == ("2026/27",)
        assert transition_count == 1
        assert connection.execute("PRAGMA integrity_check").fetchone() == (
            "ok",
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert tuple(tmp_path.glob("backups/*.jkmbackup"))
    shell.close()
    app.processEvents()


def test_wrong_password_keeps_database_and_backup_unchanged_and_releases_close(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "kompetenzmanager.sqlite"
    create_synthetic_v3_database(database_path)
    (tmp_path / "documents").mkdir()
    backups = tmp_path / "backups"
    backups.mkdir()
    shell = AppShell(database_path)
    shell.configure_school_year_transition_activation(
        _RejectingPasswordService()
    )
    before = _database_snapshot(database_path)

    def reject_password(dialog, _owner) -> None:
        def run_activation() -> None:
            dialog.plan = dialog.plan.repeat_year_level_three(
                "STD-TEST-003",
                "CRS-TEST-3",
            )
            dialog._refresh_from_plan()
            dialog.confirmation_checkbox.setChecked(True)
            dialog.password_field.setText("falsches Testpasswort")
            dialog.activate_button.click()
            loop = QEventLoop()
            dialog.activation_controller.finished.connect(loop.quit)
            QTimer.singleShot(60_000, loop.quit)
            if dialog.activation_controller.is_busy:
                loop.exec()
            assert "keine Änderungen begonnen" in (
                dialog.execution_status.label.text()
            )
            assert not dialog.close_blocked
            dialog.close_button.click()

        QTimer.singleShot(0, run_activation)

    with patch(
        "src.desktop_app.shell.prepare_maximized_workspace",
        side_effect=reject_password,
    ):
        shell.open_school_year_transition_preview(
            "2026/27",
            date(2026, 8, 1),
            date(2027, 7, 31),
        )
        app.processEvents()

    assert _database_snapshot(database_path) == before
    assert tuple(backups.iterdir()) == ()
    shell.close()
    app.processEvents()


def test_shell_close_uses_dialog_guard_during_step_up_and_recovery(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "shell-close.sqlite"
    create_synthetic_v3_database(database_path)
    shell = AppShell(database_path)
    shell.show()
    plan = SchoolYearTransitionPreviewService(
        shell.adapter.database.connect
    ).preview_plan(
        label="2026/27",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 7, 31),
    ).repeat_year_level_three("STD-TEST-003", "CRS-TEST-3")
    controller = _LifecycleActivationController()
    dialog = SchoolYearTransitionPreviewDialog(
        plan,
        shell,
        activation_controller=controller,
    )
    shell._active_school_year_transition_dialog = dialog
    shell._active_school_year_transition_controller = controller
    dialog.show()
    dialog.confirmation_checkbox.setChecked(True)
    dialog.password_field.setText("synthetisches Testpasswort")
    dialog._start_activation()

    step_up_close = QCloseEvent()
    shell.closeEvent(step_up_close)
    assert not step_up_close.isAccepted()
    assert shell.isVisible()
    assert dialog.isVisible()

    controller.fail("transition_recovery_required")
    recovery_close = QCloseEvent()
    shell.closeEvent(recovery_close)
    assert not recovery_close.isAccepted()
    assert shell.isVisible()
    assert dialog.isVisible()

    shell._active_school_year_transition_dialog = None
    shell._active_school_year_transition_controller = None
    dialog.deleteLater()
    shell.close()
    app.processEvents()


def test_invalid_year_dates_show_neutral_error_and_do_not_open_dialog(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "settings-transition-invalid.sqlite"
    create_synthetic_v3_database(database_path)
    shell = AppShell(database_path)
    before = _database_snapshot(database_path)

    with patch(
        "src.desktop_app.shell.prepare_maximized_workspace",
    ) as execute_dialog:
        shell.open_school_year_transition_preview(
            "2026/27",
            date(2026, 8, 1),
            date(2026, 7, 31),
        )

    message = shell.settings_screen.school_year_transition_message
    assert execute_dialog.call_count == 0
    assert "Bezeichnung, Beginn und Ende prüfen" in message.label.text()
    assert "NEW_SCHOOL_YEAR" not in message.label.text()
    assert message.accessibleName() == message.label.text()
    assert before == _database_snapshot(database_path)
    shell.close()
    app.processEvents()


def test_preview_reopens_five_times_without_nested_exec_or_retained_dialogs(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "settings-transition-reopen.sqlite"
    create_synthetic_v3_database(database_path)
    shell = AppShell(database_path)
    before = _database_snapshot(database_path)
    dialogs: list[SchoolYearTransitionPreviewDialog] = []
    summary_label_groups: list[tuple[QObject, ...]] = []

    with patch.object(
        SchoolYearTransitionPreviewDialog,
        "exec",
        side_effect=AssertionError("Preview must not enter a nested event loop"),
    ):
        for _index in range(5):
            shell.open_school_year_transition_preview(
                "2026/27",
                date(2026, 8, 1),
                date(2027, 7, 31),
            )
            dialog = shell._active_school_year_transition_dialog
            assert isinstance(dialog, SchoolYearTransitionPreviewDialog)
            assert dialog.isModal()
            assert not dialog.activate_button.isEnabled()
            dialogs.append(dialog)
            summary_labels = tuple(dialog.summary_labels.values()) + tuple(
                dialog.activation_summary_labels.values()
            )
            assert all(label.parentWidget() is not None for label in summary_labels)
            assert all(
                label not in QApplication.topLevelWidgets()
                for label in summary_labels
            )
            summary_label_groups.append(summary_labels)
            dialog.reject()
            if QApplication.platformName().casefold() not in {
                "offscreen",
                "minimal",
            }:
                for _attempt in range(40):
                    if not isValid(dialog) or not dialog.isVisible():
                        break
                    QTest.qWait(max(25, MOTION_DIALOG_MS // 4))
                    app.processEvents()
            QCoreApplication.sendPostedEvents(
                None,
                QEvent.Type.DeferredDelete,
            )
            app.processEvents()
            assert shell._active_school_year_transition_dialog is None
            assert shell._active_school_year_transition_controller is None
            assert not isValid(dialog)

    assert _database_snapshot(database_path) == before
    assert not shell.findChildren(SchoolYearTransitionPreviewDialog)
    assert all(not isValid(dialog) for dialog in dialogs)
    assert all(
        not isValid(label)
        for summary_labels in summary_label_groups
        for label in summary_labels
    )
    shell.close()
    app.processEvents()
