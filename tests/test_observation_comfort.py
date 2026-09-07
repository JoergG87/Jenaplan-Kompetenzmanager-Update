"""Behavioral checks for the observation keyboard and repeat-entry workflow."""

from dataclasses import replace
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.shell import AppShell
from src.desktop_app.view_models.observation_view_model import ObservationAttachmentDraft
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


def test_continue_creates_two_distinct_observations_and_keeps_context(observation_dialog):
    app, dialog = observation_dialog
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    adapter = dialog.observation_adapter
    student_id = dialog.student.student_id
    before = adapter.list_observations_for_student(student_id)
    dialog.quick_observation_checkbox.setChecked(True)
    dialog.context_select.setCurrentText("Partnerarbeit")
    dialog.note_input.setPlainText("Erste neue Testbeobachtung")
    first = dialog.create_draft()
    QTest.mouseClick(dialog.save_and_continue_button, Qt.MouseButton.LeftButton)
    assert dialog.isVisible()
    assert dialog.has_saved_observation
    next_draft = dialog.create_draft()
    assert next_draft.student_id == first.student_id
    assert next_draft.date_text == first.date_text
    assert next_draft.subject_id == first.subject_id
    assert next_draft.context == first.context
    assert next_draft.operation_token != first.operation_token
    assert not next_draft.note and not next_draft.observation_id
    assert dialog.note_input.hasFocus()
    dialog.note_input.setPlainText("Zweite neue Testbeobachtung")
    dialog.save_draft()
    after = adapter.list_observations_for_student(student_id)
    assert len(after) == len(before) + 2
    assert len({item.observation_id for item in after}) == len(after)
    assert {item.note for item in after} >= {
        "Erste neue Testbeobachtung", "Zweite neue Testbeobachtung",
    }


def test_continue_failure_preserves_draft_and_operation_token(observation_dialog, monkeypatch):
    app, dialog = observation_dialog
    dialog.quick_observation_checkbox.setChecked(True)
    dialog.note_input.setPlainText("Nicht verlieren")
    before = dialog.create_draft()
    monkeypatch.setattr(
        dialog.observation_adapter, "save_observation",
        lambda _draft: SimpleNamespace(success=False, message="Testfehler"),
    )
    dialog.save_draft(continue_entry=True)
    assert dialog.create_draft() == before
    assert not dialog.has_saved_observation
    assert dialog.save_and_continue_button.isEnabled()


def test_continue_clears_ratings_attachments_and_blocks_reentrant_save(observation_dialog, monkeypatch):
    app, dialog = observation_dialog
    dialog.show()
    app.processEvents()
    entry = next(
        competency
        for group in dialog.competency_subject_groups
        for area in group.learning_area_groups
        for topic in area.competency_groups
        for competency in topic.competencies
    )
    dialog._add_competency_rating_row(entry.competency_id, entry, "+")
    dialog.attachment_drafts.append(
        ObservationAttachmentDraft(source_path="synthetic.txt", title="Testanhang")
    )
    dialog.note_input.setPlainText("Erste Eingabe")
    calls = []

    def save(draft):
        calls.append(draft)
        dialog.save_draft(continue_entry=True)
        dialog.reject()
        assert dialog.isVisible()
        return SimpleNamespace(success=True)

    monkeypatch.setattr(dialog.observation_adapter, "save_observation", save)
    dialog.save_draft(continue_entry=True)
    assert len(calls) == 1
    assert calls[0].competency_ratings and calls[0].attachments
    assert not dialog.create_draft().competency_ratings
    assert not dialog.create_draft().attachments
    assert not dialog.note_input.toPlainText()
    dialog.reject()
    assert dialog.has_saved_observation
    assert not dialog.isVisible()


def test_edit_cannot_start_repeat_create_path(observation_dialog, monkeypatch):
    app, dialog = observation_dialog
    dialog.initial_draft = replace(dialog.create_draft(), observation_id="OBS-TEST-001")
    calls = []
    monkeypatch.setattr(dialog.observation_adapter, "save_observation", calls.append)
    dialog.save_draft(continue_entry=True)
    assert not calls


@pytest.mark.parametrize("route", ("profile", "list"))
def test_shell_refreshes_after_saved_entry_then_cancel(observation_shell, monkeypatch, route):
    app, shell = observation_shell
    refreshed = []

    def cancel_after_saved(dialog, _owner):
        dialog.has_saved_observation = True
        return 0

    monkeypatch.setattr("src.desktop_app.shell.exec_maximized_workspace", cancel_after_saved)
    monkeypatch.setattr(shell, "show_student_profile", refreshed.append)
    monkeypatch.setattr(shell, "refresh_overview", lambda: refreshed.append("overview"))
    monkeypatch.setattr(shell, "refresh_students", lambda: refreshed.append("students"))
    if route == "profile":
        student = shell.adapter.get_student_profile(SYNTHETIC_STUDENT_IDS[0])
        shell.open_new_observation_dialog(student)
        assert refreshed == [SYNTHETIC_STUDENT_IDS[0]]
    else:
        shell.open_quick_observation_dialog(SYNTHETIC_STUDENT_IDS[0])
        assert refreshed == ["overview", "students"]
