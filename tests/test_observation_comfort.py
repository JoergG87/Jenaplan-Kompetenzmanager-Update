"""Behavioral checks for the observation keyboard and repeat-entry workflow."""

from dataclasses import replace
from datetime import date, datetime

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.shell import AppShell
from tests.helpers.synthetic_v4 import SYNTHETIC_STUDENT_IDS, create_synthetic_v4_database


@pytest.fixture
def observation_dialog(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = create_synthetic_v4_database(tmp_path / "observations.sqlite")
    adapter = StudentDesktopAdapter(path, today_provider=lambda: date(2026, 9, 7))
    student = adapter.get_student_profile(SYNTHETIC_STUDENT_IDS[0])
    assert student is not None
    dialog = NewObservationDialog(
        student,
        observation_adapter=adapter,
        subject_options=adapter.list_observation_subject_options(student.student_id),
        competency_subject_groups=adapter.list_observation_competency_subject_groups(student.student_id),
    )
    yield app, dialog
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_new_observation_starts_in_catalog_search(observation_dialog):
    app, dialog = observation_dialog
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    assert dialog.catalog_search_input.hasFocus()
    QTest.keyClicks(app.focusWidget(), "Test")
    assert dialog.catalog_search_input.text() == "Test"
    assert dialog.note_input.toPlainText() == ""


def test_edit_starts_in_note_and_preserves_existing_text(observation_dialog):
    app, dialog = observation_dialog
    dialog.initial_draft = replace(dialog.create_draft(), note="Vorhandene Notiz")
    dialog._apply_initial_draft()
    before = dialog.create_draft()
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    assert dialog.note_input.hasFocus()
    assert dialog.create_draft() == before


def test_reactivation_keeps_user_focus_and_quick_mode_focuses_note(observation_dialog):
    app, dialog = observation_dialog
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    dialog.quick_observation_checkbox.setChecked(True)
    assert dialog.note_input.hasFocus()
    dialog.context_select.setFocus(Qt.FocusReason.TabFocusReason)
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    assert dialog.context_select.hasFocus()


@pytest.fixture
def observation_shell(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = create_synthetic_v4_database(tmp_path / "shell.sqlite")
    shell = AppShell(path, now_provider=lambda: datetime(2026, 9, 7, 10, 0))
    shell.show()
    shell.activateWindow()
    app.processEvents()
    yield app, shell
    shell.close()
    shell.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_shortcut_uses_visible_profile_and_fresh_student(observation_shell, monkeypatch):
    app, shell = observation_shell
    shell.show_student_profile(SYNTHETIC_STUDENT_IDS[0])
    opened = []
    monkeypatch.setattr(shell, "open_new_observation_dialog", opened.append)
    shell.new_observation_action.trigger()
    assert [student.student_id for student in opened] == [SYNTHETIC_STUDENT_IDS[0]]
    assert not shell.new_observation_action.autoRepeat()


def test_shortcut_requires_deliberate_visible_list_selection(observation_shell, monkeypatch):
    app, shell = observation_shell
    shell.show_student_profile(SYNTHETIC_STUDENT_IDS[0])
    shell._show_screen("dashboard")
    opened = []
    monkeypatch.setattr(shell, "open_quick_observation_dialog", opened.append)
    shell.new_observation_action.trigger()
    assert not opened
    assert shell.stack.currentWidget() is shell.students_workspace
    assert shell.students_screen.search_input.hasFocus()
    assert shell.students_screen.selected_student_id() is None
    shell.students_screen.table.selectRow(1)
    expected = shell.students_screen.filtered_students[1].student_id
    shell.new_observation_action.trigger()
    assert opened == [expected]
    shell.refresh_students()
    assert shell.students_screen.selected_student_id() is None


def test_shortcut_does_not_open_behind_modal_or_disabled_shell(observation_shell, monkeypatch):
    app, shell = observation_shell
    shell.show_student_profile(SYNTHETIC_STUDENT_IDS[0])
    opened = []
    monkeypatch.setattr(shell, "open_new_observation_dialog", opened.append)
    modal = QDialog(shell)
    modal.setModal(True)
    modal.show()
    app.processEvents()
    shell.new_observation_action.trigger()
    assert not opened
    modal.close()
    shell.setEnabled(False)
    shell.new_observation_action.trigger()
    assert not opened
    shell.setEnabled(True)
