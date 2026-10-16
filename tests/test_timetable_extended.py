"""Normalized timetable CRUD through real SQLCipher and the actual editor."""
import os
import multiprocessing
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from contextlib import closing
from dataclasses import replace
import pytest
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QApplication
from src.application.commands.timetable import SaveTimetableEntryCommand
from src.core.sqlite_store import SQLiteDatabase
from src.core.database_compatibility import DatabaseCompatibilityError
from src.core.timetable import TimetableEntry
from src.core.timetable import TimetableValidationError
from src.core.upgrade_validation import verify_timetable_target_references
from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
from src.desktop_app.view_models.lesson_time_templates_view_model import LessonTimeTemplateOptionViewModel
from src.core.lesson_time_templates import LessonTimeTemplate, LessonTimeTemplateService
from src.security.infrastructure.lesson_time_templates import SQLiteLessonTimeTemplateRepository
from src.security.transactional_timetable_migration import SyntheticTimetableMigration
from tests.test_transactional_schema_migration import _seed_case, _inspection_service


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _migration_worker(path, pipe):
    try:
        runtime, service = _seed_case(path)
        with closing(runtime.final_v4.database.connect()) as connection:
            values = dict(connection.execute("SELECT * FROM competencies LIMIT 1").fetchone())
            values.update(competency_id="CMP-SYNTHETIC-MATH", subject_id="SUB-TEST-MA",
                subject_name="Mathematik", subject_full_name="Mathematik")
            columns = tuple(values)
            connection.execute("INSERT INTO competencies (" + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")", tuple(values.values()))
            connection.commit()
        SyntheticTimetableMigration(service).execute()
        pipe.send(("ok", service.paths, service.loaded, service.installation_id))
    except BaseException as error:
        pipe.send((type(error).__name__, str(error)))
    finally:
        pipe.close()


@pytest.fixture
def extended(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_migration_worker, args=(tmp_path, child))
    process.start()
    child.close()
    try:
        assert parent.poll(45)
        result = parent.recv()
        assert result[0] == "ok", result
        process.join(10)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)
        parent.close()
    _, paths, loaded, installation = result
    service = _inspection_service(paths, loaded, installation)
    class BoundProvider:
        def connect(self, path, *, create=False):
            assert not create
            return service._provider.connect(path, create=False, key_material=service.loaded.database_key.key_material)
    database = SQLiteDatabase(service.paths.final_v4.database, connection_provider=BoundProvider(), create=False, initialize_schema=False)
    return TimetableDesktopAdapter(database), service


def command(adapter, *, kind="subject_lesson", subjects=None, weekday=2):
    week = adapter.week_view_model()
    selected = tuple(item.item_id for item in week.subjects[:2]) if subjects is None else subjects
    return SaveTimetableEntryCommand("", weekday, "08:00", "08:45", "", "group", week.targets_by_type["group"][0].item_id,
        "Atelier", True, entry_kind=kind, subject_ids=selected)


def test_historical_single_subject_opens_and_saves_without_changing_fields(extended, app):
    adapter, _ = extended
    before = adapter.week_view_model().days[0].entries[0]
    dialog = TimetableEntryDialog(adapter.week_view_model(), weekday=1, entry=before)
    saved = adapter.save_entry(dialog.command())
    assert saved == before
    assert saved.subject_ids == ("SUB-TEST-DE",)


@pytest.mark.parametrize("kind", ["subject_lesson", "homeroom_session"])
def test_real_cipher_create_reopen_update_activate_softdelete(extended, app, kind):
    adapter, service = extended
    original_observations = None
    with closing(adapter.database.connect()) as c:
        original_observations = tuple(tuple(row) for row in c.execute("SELECT * FROM observations"))
        competencies = tuple(tuple(row) for row in c.execute("SELECT * FROM competencies"))
        ratings = tuple(tuple(row) for row in c.execute("SELECT * FROM observation_competency_ratings"))
    request = command(adapter, kind=kind, subjects=() if kind == "homeroom_session" else None)
    saved = adapter.save_entry(request)
    assert saved.subject_id == ""
    assert saved.entry_kind == kind
    assert saved.subject_ids == request.subject_ids
    assert saved.subject_label == "Stammgruppenstunde" if kind == "homeroom_session" else len(saved.subject_options) == 2
    reopened = TimetableDesktopAdapter(adapter.database)
    row = reopened.week_view_model().days[1].entries[0]
    dialog = TimetableEntryDialog(reopened.week_view_model(), weekday=2, entry=row)
    assert dialog.command().subject_ids == row.subject_ids
    if kind == "homeroom_session":
        assert not dialog.subject_list.isEnabled()
    dialog.room_input.setText("Raum 2")
    changed = reopened.save_entry(dialog.command())
    assert changed.room == "Raum 2"
    assert reopened.set_entry_active(changed.timetable_entry_id, False).subject_ids == saved.subject_ids
    assert reopened.set_entry_active(changed.timetable_entry_id, True).subject_ids == saved.subject_ids
    reopened.delete_entry(saved.timetable_entry_id)
    assert not reopened.week_view_model().days[1].entries
    with closing(adapter.database.connect()) as c:
        assert c.execute("SELECT COUNT(*) FROM timetable_entries WHERE timetable_entry_id=?", (saved.timetable_entry_id,)).fetchone()[0] == 1
        assert tuple(tuple(row) for row in c.execute("SELECT * FROM observations")) == original_observations
        assert tuple(tuple(row) for row in c.execute("SELECT * FROM competencies")) == competencies
        assert tuple(tuple(row) for row in c.execute("SELECT * FROM observation_competency_ratings")) == ratings
        verify_timetable_target_references(c)
        assert c.execute("PRAGMA cipher_version").fetchone()[0].startswith("4.17")
        assert c.execute("PRAGMA cipher_provider").fetchone()[0] == "commoncrypto"
    assert not service.paths.final_v4.database.read_bytes().startswith(b"SQLite format 3")


def test_cardinality_references_overlap_and_atomic_repository_rejection(extended):
    adapter, _ = extended
    valid = command(adapter)
    for invalid in (replace(valid, subject_ids=()), replace(valid, subject_ids=("missing",)),
            replace(valid, subject_ids=(valid.subject_ids[0],) * 2),
            replace(valid, entry_kind="homeroom_session"),
            replace(valid, entry_kind="homeroom_session", subject_ids=(), target_type="course")):
        with pytest.raises(TimetableValidationError): adapter.save_entry(invalid)
    saved = adapter.save_entry(valid)
    with pytest.raises(TimetableValidationError, match="überschneidet"):
        adapter.save_entry(replace(valid, entry_kind="homeroom_session", subject_ids=()))
    raw = adapter.repository.get_entry(saved.timetable_entry_id)
    with pytest.raises(Exception):
        adapter.repository.update_entry(replace(raw, subject_ids=("missing",), room="must roll back"))
    assert adapter.repository.get_entry(saved.timetable_entry_id) == raw
    with closing(adapter.database.connect()) as c:
        assert c.execute("SELECT COUNT(*) FROM timetable_entries WHERE weekday=2").fetchone()[0] == 1


@pytest.mark.parametrize("kind", ["subject_lesson", "homeroom_session"])
def test_time_template_copy_and_individual_override_for_both_kinds(extended, app, kind):
    adapter, _ = extended
    templates = LessonTimeTemplateService(SQLiteLessonTimeTemplateRepository(adapter.database.connect))
    templates.set_times(1, "07:45", "08:30")
    week = adapter.week_view_model()
    dialog = TimetableEntryDialog(week, weekday=2, templates=(LessonTimeTemplateOptionViewModel(templates.suggest(1)),))
    dialog.entry_kind_combo.setCurrentIndex(dialog.entry_kind_combo.findData(kind))
    if kind == "subject_lesson":
        for index in range(2): dialog.subject_list.item(index).setCheckState(Qt.CheckState.Checked)
    dialog.lesson_template_combo.setCurrentIndex(1)
    assert dialog.command().start_time == "08:00"
    dialog.apply_template_button.click()
    dialog.end_time.setTime(QTime(8, 35))
    saved = adapter.save_entry(dialog.command())
    templates.set_times(1, "10:00", "10:45")
    reread = adapter.repository.get_entry(saved.timetable_entry_id)
    assert (reread.start_time, reread.end_time) == ("07:45", "08:35")
    edited = TimetableEntryDialog(adapter.week_view_model(), weekday=2, entry=saved,
        templates=(LessonTimeTemplateOptionViewModel(templates.suggest(1)),))
    assert (edited.command().start_time, edited.command().end_time) == ("07:45", "08:35")
    assert edited.command().entry_kind == kind


def test_conflicting_scalar_and_subject_set_are_rejected(extended):
    adapter, _ = extended
    request = command(adapter)
    with pytest.raises(TimetableValidationError, match="Widersprüchliche"):
        adapter.save_entry(replace(request, subject_id=request.subject_ids[0]))
    historical = adapter.week_view_model().days[0].entries[0]
    with pytest.raises(ValueError, match="Widersprüchliche"):
        replace(historical, subject_ids=("SUB-TEST-MA",))


def test_unknown_schema_never_falls_back_to_legacy_repository(extended):
    adapter, _ = extended
    saved = adapter.save_entry(command(adapter))
    raw = adapter.repository.get_entry(saved.timetable_entry_id)
    with closing(adapter.database.connect()) as connection:
        before = tuple(tuple(row) for row in connection.execute("SELECT * FROM timetable_entries"))
        connection.execute("CREATE TABLE unknown_synthetic_schema(value TEXT)")
        connection.commit()
    with pytest.raises(DatabaseCompatibilityError, match="Unbekanntes"):
        adapter.repository.update_entry(replace(raw, room="must not save"))
    with pytest.raises(DatabaseCompatibilityError, match="Unbekanntes"):
        adapter.repository.list_entries()
    with closing(adapter.database.connect()) as connection:
        assert tuple(tuple(row) for row in connection.execute("SELECT * FROM timetable_entries")) == before
