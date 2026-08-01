"""Preview-only integration from settings into the existing transition dialog."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sqlite3
from unittest.mock import patch

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QPushButton

from src.desktop_app.shell import AppShell
from src.security.application import AuthenticationResult
from src.security.domain import AuthenticationStatus
from tests.helpers.synthetic_v3 import create_pre_transition_v3_database


create_synthetic_v3_database = create_pre_transition_v3_database


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

    def inspect_dialog(dialog, owner) -> int:
        assert owner is shell
        opened_plans.append(dialog.plan)
        button_texts = tuple(
            button.text().casefold()
            for button in dialog.findChildren(QPushButton)
        )
        assert any("verbindlich aktivieren" in text for text in button_texts)
        assert not dialog.activate_button.isEnabled()
        dialog.reject()
        return 0

    with (
        patch.object(
            shell.backup_restore_operations,
            "start",
        ) as backup_or_restore_start,
        patch(
            "src.desktop_app.shell.exec_maximized_workspace",
            side_effect=inspect_dialog,
        ) as execute_dialog,
    ):
        shell.open_school_year_transition_preview(
            "2026/27",
            date(2026, 8, 1),
            date(2027, 7, 31),
        )

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

    def activate(dialog, owner) -> int:
        assert owner is shell
        opened.append(dialog)
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
        return 0

    with patch(
        "src.desktop_app.shell.exec_maximized_workspace",
        side_effect=activate,
    ):
        shell.open_school_year_transition_preview(
            "2026/27",
            date(2026, 8, 1),
            date(2027, 7, 31),
        )

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


def test_invalid_year_dates_show_neutral_error_and_do_not_open_dialog(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "settings-transition-invalid.sqlite"
    create_synthetic_v3_database(database_path)
    shell = AppShell(database_path)
    before = _database_snapshot(database_path)

    with patch(
        "src.desktop_app.shell.exec_maximized_workspace"
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
