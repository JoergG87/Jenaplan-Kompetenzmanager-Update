"""Explicit observation subject choice and real encrypted AppShell integration."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from contextlib import closing
from dataclasses import replace
from datetime import datetime
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.view_models.timetable_view_model import TimetableEntryViewModel, TimetableOptionViewModel


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def combined():
    options = (TimetableOptionViewModel("deutsch", "Deutsch"),
               TimetableOptionViewModel("mathematik", "Mathematik"))
    return TimetableEntryViewModel("TTE-1", 1, "08:00", "08:45", "", "Deutsch / Mathematik",
        "group", "G-1", "Eulen", "", True, 1,
        subject_ids=tuple(o.item_id for o in options), subject_options=options)


@pytest.mark.parametrize("label,accepted,expected", [
    ("Bitte Fach wählen", True, []), ("Mathematik", False, []),
    ("Mathematik", True, [("mathematik", "Mathematik", "group", "G-1", "Eulen")]),
])
def test_combined_observation_requires_explicit_choice(app, label, accepted, expected):
    screen = OverviewScreen(); emitted = []
    screen.timetable_observation_requested.connect(lambda *values: emitted.append(values))
    with patch("src.desktop_app.screens.overview_screen.QInputDialog.getItem", return_value=(label, accepted)) as choose:
        screen._emit_observation(combined())
    assert emitted == expected
    assert choose.call_args.args[4] == 0  # Placeholder, never the first real subject.
    assert choose.call_args.args[3] == ["Bitte Fach wählen", "Deutsch", "Mathematik"]
    screen.close()


def test_homeroom_has_no_implicit_competency_subject(app):
    screen = OverviewScreen(); emitted = []
    entry = replace(combined(), subject_ids=(), subject_options=(), entry_kind="homeroom_session",
                    subject_label="Stammgruppenstunde")
    screen._observation_subjects = combined().subject_options
    screen.timetable_observation_requested.connect(lambda *values: emitted.append(values))
    with patch("src.desktop_app.screens.overview_screen.QInputDialog.getItem", return_value=("Bitte Fach wählen", True)):
        screen._emit_observation(entry)
    assert emitted == []
    with patch("src.desktop_app.screens.overview_screen.QInputDialog.getItem", return_value=("Deutsch", True)):
        screen._emit_observation(entry)
    assert emitted == [("deutsch", "Deutsch", "group", "G-1", "Eulen")]
    screen.close()


def _seed_appshell_case(directory, channel):
    try:
        from tests.test_transactional_schema_migration import _seed_case
        from src.security.transactional_timetable_migration import SyntheticTimetableMigration
        _, service = _seed_case(directory)
        with closing(service._provider.connect(service.paths.final_v4.database, create=False,
                key_material=service.loaded.database_key.key_material)) as c:
            c.execute("UPDATE competencies SET subject_name='Deutsch', subject_full_name='Deutsch' WHERE subject_id='SUB-TEST-DE'")
            columns = [row[1] for row in c.execute("PRAGMA table_info(competencies)")]
            values = dict(c.execute("SELECT * FROM competencies LIMIT 1").fetchone())
            values.update(competency_id="CMP-SYN-MATH", subject_id="SUB-SYN-MATH",
                          subject_name="Mathematik", subject_full_name="Mathematik")
            c.execute("INSERT INTO competencies(" + ",".join(columns) + ") VALUES(" + ",".join("?" for _ in columns) + ")",
                      [values[column] for column in columns]); c.commit()
        SyntheticTimetableMigration(service).execute()
        channel.send(("ok", service.paths, service.loaded, service.installation_id))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()


def _run_process(target, args):
    import multiprocessing
    ctx = multiprocessing.get_context("spawn"); parent, child = ctx.Pipe()
    process = ctx.Process(target=target, args=(*args, child))
    process.start(); child.close()
    try:
        assert parent.poll(60), "synthetic worker did not report"
        result = parent.recv(); process.join(10)
        assert process.exitcode == 0 and result[0] == "ok", result
        return result
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()


def test_real_cipher_appshell_all_three_features_and_one_observation(app, tmp_path):
    _, paths, loaded, installation_id = _run_process(_seed_appshell_case, (tmp_path,))
    assert _run_process(_appshell_worker, (paths, loaded, installation_id)) == ("ok",)


def _appshell_worker(paths, loaded, installation_id, channel, capture_dir=None):
    try:
        def reject_modal(*args, **kwargs):
            raise AssertionError(str(args[1:]))
        with patch("src.desktop_app.shell.QMessageBox.warning", side_effect=reject_modal):
            _exercise_appshell(paths, loaded, installation_id, capture_dir=capture_dir)
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()


def _exercise_appshell(paths, loaded, installation_id, capture_dir=None):
    from tests.test_transactional_schema_migration import _inspection_service
    from src.security.synthetic_v6_runtime import SyntheticV6Runtime
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.adapters.lesson_time_templates_desktop_adapter import LessonTimeTemplatesDesktopAdapter
    from src.desktop_app.shell import AppShell
    from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
    from src.desktop_app.runtime import runtime_paths
    service = _inspection_service(paths, loaded, installation_id)
    app = QApplication.instance() or QApplication([])
    from src.desktop_app.theme import apply_app_theme
    apply_app_theme(app)
    instant = datetime(2026, 8, 3, 8, 0)
    with SyntheticV6Runtime(service).open_existing() as opened:
        student_adapter = StudentDesktopAdapter(database=opened.database,
            database_create_allowed=False, today_provider=lambda: instant.date(),
            now_provider=lambda: instant, managed_document_store=opened.documents)
        shell = AppShell(student_adapter=student_adapter, backup_restore_available=False,
            paths=runtime_paths(service.paths.final_v4.root), now_provider=lambda: instant,
            lesson_time_templates_adapter=LessonTimeTemplatesDesktopAdapter(opened))
        shell.resize(1180, 760); shell.show(); app.processEvents()
        with closing(opened.database.connect()) as c:
            observations_before = c.execute("SELECT count(*) FROM observations").fetchone()[0]
            ratings_before = c.execute("SELECT count(*) FROM observation_competency_ratings").fetchone()[0]
            competencies_before = c.execute("SELECT count(*) FROM competencies").fetchone()[0]
        editor = shell.settings_screen.lesson_time_templates_editor
        editor.start_time.setTime(QTime(7,45)); editor.end_time.setTime(QTime(8,30))
        editor.save_button.click(); app.processEvents()
        templates = shell.lesson_time_templates_adapter.view_model().templates
        assert templates[0].start_time == "07:45"
        week = shell.timetable_adapter.week_view_model()
        assert week.supports_extended_entries
        existing = week.days[0].entries[0]
        dialog = TimetableEntryDialog(week, weekday=1, entry=existing, templates=templates)
        saved = shell.timetable_adapter.save_entry(dialog.command())
        assert saved.subject_ids == existing.subject_ids
        created = []
        for weekday, kind in ((1, "subject_lesson"), (2, "homeroom_session")):
            dialog = TimetableEntryDialog(shell.timetable_adapter.week_view_model(), weekday=weekday, templates=templates)
            dialog.entry_kind_combo.setCurrentIndex(dialog.entry_kind_combo.findData(kind))
            if kind == "subject_lesson":
                for i in range(dialog.subject_list.count()):
                    dialog.subject_list.item(i).setCheckState(Qt.CheckState.Checked)
            else:
                assert not dialog.subject_list.isEnabled()
            dialog.lesson_template_combo.setCurrentIndex(1); dialog.apply_template_button.click()
            if capture_dir is not None:
                dialog.show(); app.processEvents()
                dialog.grab().save(str(capture_dir / (kind + "_times.png")))
                dialog.form_scroll.ensureWidgetVisible(dialog.subject_list)
                app.processEvents()
                dialog.grab().save(str(capture_dir / (kind + ".png")))
                dialog.hide()
            assert shell._save_timetable_dialog(dialog)
            entries = shell.timetable_adapter.week_view_model().days[weekday-1].entries
            created.append(next(e for e in entries if e.start_time == "07:45"))
        multi, homeroom = created
        assert len(multi.subject_ids) == 2 and not multi.subject_id
        assert homeroom.subject_ids == () and homeroom.subject_label == "Stammgruppenstunde"
        shell.save_lesson_time_template(1, "08:00", "08:45", templates[0].template)
        assert shell.timetable_adapter.repository.get_entry(multi.timetable_entry_id).start_time == "07:45"
        shell.refresh_dashboard(instant)
        assert shell.dashboard_screen._hero_occurrence.entry.subject_ids == multi.subject_ids
        if capture_dir is not None:
            app.processEvents(); shell.grab().save(str(capture_dir / "appshell.png"))
        selected_in_dialog = []
        def choose_math():
            chooser = next(widget for widget in QApplication.topLevelWidgets()
                           if isinstance(widget, QInputDialog) and widget.isVisible())
            selected_in_dialog.append(chooser.textValue())
            chooser.setTextValue("Mathematik")
            if capture_dir is not None:
                chooser.grab().save(str(capture_dir / "observation_subject.png"))
            chooser.accept()
        QTimer.singleShot(0, choose_math)
        shell.dashboard_screen._emit_observation(multi)
        assert selected_in_dialog == ["Bitte Fach wählen"]
        assert shell.pending_observation_subject_id == "SUB-SYN-MATH"
        student_id = "STD-TEST-001"
        captured = []
        def save_once(dialog):
            assert dialog.prefill_subject_id == "SUB-SYN-MATH"
            assert dialog.subject_select.currentData() == "SUB-SYN-MATH"
            dialog.quick_observation_checkbox.setChecked(True)
            dialog.note_input.setPlainText("Synthetische einzelne Fachbeobachtung")
            dialog.save_draft()
            captured.append(dialog.has_saved_observation)
            return 0
        with patch.object(shell, "_exec_workspace", side_effect=save_once):
            shell.open_quick_observation_dialog(student_id)
        assert captured == [True]
        with closing(opened.database.connect()) as c:
            assert c.execute("SELECT count(*) FROM observations").fetchone()[0] == observations_before + 1
            assert c.execute("SELECT count(*) FROM observation_competency_ratings").fetchone()[0] == ratings_before
            assert c.execute("SELECT count(*) FROM competencies").fetchone()[0] == competencies_before
            row = c.execute("SELECT subject_id FROM observations WHERE note=?", ("Synthetische einzelne Fachbeobachtung",)).fetchone()
            assert row[0] == "SUB-SYN-MATH"
        for entry in created:
            dialog = TimetableEntryDialog(shell.timetable_adapter.week_view_model(), weekday=entry.weekday, entry=entry, templates=templates)
            dialog.room_input.setText("Synthetischer Raum")
            shell._save_timetable_dialog(dialog)
            assert shell.timetable_adapter.repository.get_entry(entry.timetable_entry_id).room == "Synthetischer Raum"
            shell.timetable_adapter.delete_entry(entry.timetable_entry_id)
            assert shell.timetable_adapter.repository.get_entry(entry.timetable_entry_id) is None
        shell.close(); app.processEvents()
