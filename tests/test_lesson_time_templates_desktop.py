"""Teaching time UI contracts, with existing timetable semantics preserved."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication
from src.core.lesson_time_templates import LessonTimeTemplate
from src.desktop_app.dialogs.timetable_entry_dialog import TimetableEntryDialog
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.view_models.lesson_time_templates_view_model import (
    LessonTimeTemplateOptionViewModel, LessonTimeTemplatesViewModel,
)
from src.desktop_app.view_models.timetable_view_model import (
    TimetableEntryViewModel, TimetableWeekViewModel, TimetableOptionViewModel,
)


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def option(start="07:45", end="08:30"):
    return LessonTimeTemplateOptionViewModel(LessonTimeTemplate(1, start, end))


def week():
    return TimetableWeekViewModel((), (TimetableOptionViewModel("de", "Deutsch"),),
                                  {"group": (TimetableOptionViewModel("g", "Eulen"),)})


def entry():
    return TimetableEntryViewModel("e", 2, "09:10", "09:55", "de", "Deutsch",
                                   "group", "g", "Eulen", "", True, 0)


def test_v4_settings_and_dialog_expose_no_template_access(app):
    settings = SettingsScreen()
    assert "lesson_time_templates" not in settings.settings_cards
    settings.show_page("lesson_time_templates")
    assert settings.current_page == "overview"
    assert not hasattr(settings, "lesson_time_templates_editor")
    dialog = TimetableEntryDialog(week(), weekday=1)
    assert not hasattr(dialog, "lesson_template_combo")


def test_synthetic_settings_has_ordered_templates_and_explicit_edit_identity(app):
    settings = SettingsScreen(lesson_time_templates_available=True)
    settings.show_page("lesson_time_templates")
    assert settings.current_page == "lesson_time_templates"
    editor = settings.lesson_time_templates_editor
    model = LessonTimeTemplatesViewModel((option(), option("08:35", "09:20")))
    editor.set_view_model(model)
    assert editor.template_combo.itemText(1) == "1. Stunde: 07:45–08:30"
    editor.template_combo.setCurrentIndex(1)
    assert not editor.lesson_number.isEnabled()
    emitted = []
    editor.save_requested.connect(lambda *values: emitted.append(values))
    editor.start_time.setTime(QTime(7, 50))
    editor.save_button.click()
    assert emitted == [(1, "07:50", "08:30", model.templates[0].template)]
    editor.template_combo.setCurrentIndex(0)
    assert editor.lesson_number.isEnabled()
    assert editor.start_time.time() == QTime(0, 0)


def test_template_selection_requires_explicit_apply_and_allows_individual_times(app):
    dialog = TimetableEntryDialog(week(), weekday=1, templates=(option(),))
    assert dialog.start_time.time() == QTime(8, 0)
    dialog.lesson_template_combo.setCurrentIndex(1)
    assert dialog.start_time.time() == QTime(8, 0)
    dialog.apply_template_button.click()
    assert (dialog.command().start_time, dialog.command().end_time) == ("07:45", "08:30")
    dialog.start_time.setTime(QTime(7, 55))
    dialog.end_time.setTime(QTime(8, 40))
    assert (dialog.command().start_time, dialog.command().end_time) == ("07:55", "08:40")


def test_reopening_existing_entry_never_copies_modified_template(app):
    dialog = TimetableEntryDialog(week(), weekday=2, entry=entry(), templates=(option("07:50", "08:35"),))
    assert dialog.lesson_template_combo.currentData() is None
    assert not dialog.apply_template_button.isEnabled()
    assert (dialog.command().start_time, dialog.command().end_time) == ("09:10", "09:55")
    dialog.lesson_template_combo.setCurrentIndex(1)
    assert (dialog.command().start_time, dialog.command().end_time) == ("09:10", "09:55")


def test_synthetic_editor_scrolls_with_actions_visible_at_680px(app):
    from src.desktop_app.dialogs.dialog_buttons import DialogActionBar
    from PySide6.QtWidgets import QDialogButtonBox
    from src.desktop_app.theme import apply_app_theme
    apply_app_theme(app)
    dialog = TimetableEntryDialog(week(), weekday=1, templates=(option(),))
    dialog.resize(540, 680)
    dialog.show()
    app.processEvents()
    assert dialog.height() == 680
    assert dialog.form_scroll.verticalScrollBar().maximum() > 0
    buttons = dialog.findChild(DialogActionBar)
    save = buttons.button(QDialogButtonBox.StandardButton.Save)
    assert save.isVisibleTo(dialog)
    assert save.mapTo(dialog, save.rect().bottomRight()).y() <= dialog.height()


def test_empty_templates_remain_manual(app):
    dialog = TimetableEntryDialog(week(), weekday=1, templates=())
    assert dialog.lesson_template_combo.count() == 1
    assert not dialog.apply_template_button.isEnabled()


@pytest.fixture
def encrypted_repository(tmp_path):
    from contextlib import closing
    from src.core.final_v4_schema import FinalV4SchemaInitializer
    from src.core.lesson_times_schema import LESSON_TIME_TEMPLATE_STATEMENT
    from src.security.infrastructure.lesson_time_templates import SQLiteLessonTimeTemplateRepository
    from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider
    provider = qualified_sqlcipher_test_provider()
    path = tmp_path / "synthetic-times.sqlcipher"
    key = b"s" * 32
    with closing(provider.connect(path, create=True, key_material=key)) as connection:
        FinalV4SchemaInitializer.initialize_connection(connection)
        connection.execute(LESSON_TIME_TEMPLATE_STATEMENT)
        connection.execute("PRAGMA user_version=5")
        connection.commit()
    return SQLiteLessonTimeTemplateRepository(lambda: provider.connect(path, create=False, key_material=key))


def test_real_cipher_atomic_insert_conflict_and_stale_update(encrypted_repository):
    from src.core.lesson_time_templates import LessonTimeTemplateError, LessonTimeTemplateService
    service = LessonTimeTemplateService(encrypted_repository)
    first = LessonTimeTemplate(1, "07:45", "08:30")
    service.set_times_if_unchanged(1, first.start_time, first.end_time, expected=None)
    with pytest.raises(LessonTimeTemplateError):
        service.set_times_if_unchanged(1, "08:00", "08:45", expected=None)
    service.set_times_if_unchanged(1, "07:50", "08:35", expected=first)
    with pytest.raises(LessonTimeTemplateError):
        service.set_times_if_unchanged(1, "08:00", "08:45", expected=first)
    assert service.suggest(1) == LessonTimeTemplate(1, "07:50", "08:35")
    with pytest.raises(LessonTimeTemplateError):
        service.set_times_if_unchanged(1, "09:00", "08:00", expected=service.suggest(1))
    assert service.suggest(1) == LessonTimeTemplate(1, "07:50", "08:35")


def test_real_cipher_settings_save_and_reopen(encrypted_repository, app):
    from src.core.lesson_time_templates import LessonTimeTemplateService
    service = LessonTimeTemplateService(encrypted_repository)
    settings = SettingsScreen(lesson_time_templates_available=True)
    editor = settings.lesson_time_templates_editor
    editor.save_requested.connect(lambda number, start, end, expected:
                                 service.set_times_if_unchanged(number, start, end, expected=expected))
    editor.start_time.setTime(QTime(7, 45))
    editor.end_time.setTime(QTime(8, 30))
    editor.save_button.click()
    values = tuple(LessonTimeTemplateOptionViewModel(t) for t in encrypted_repository.list_templates())
    editor.set_view_model(LessonTimeTemplatesViewModel(values))
    editor.template_combo.setCurrentIndex(1)
    assert editor.start_time.time() == QTime(7, 45)
    dialog = TimetableEntryDialog(week(), weekday=1, templates=values)
    dialog.lesson_template_combo.setCurrentIndex(1)
    dialog.apply_template_button.click()
    copied = dialog.command()
    service.set_times(1, "08:00", "08:45")
    assert (copied.start_time, copied.end_time) == ("07:45", "08:30")


def _qualified_ui_worker(paths, loaded, installation, channel):
    try:
        from tests.test_transactional_schema_migration import _inspection_service
        from src.security.synthetic_v5_runtime import SyntheticV5Runtime
        from src.desktop_app.adapters.lesson_time_templates_desktop_adapter import LessonTimeTemplatesDesktopAdapter
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        service = _inspection_service(paths, loaded, installation)
        application = QApplication.instance() or QApplication([])
        with SyntheticV5Runtime(service).open_existing() as runtime:
            adapter = LessonTimeTemplatesDesktopAdapter(runtime)
            settings = SettingsScreen(lesson_time_templates_available=True)
            editor = settings.lesson_time_templates_editor
            editor.save_requested.connect(adapter.save_template)
            editor.start_time.setTime(QTime(7, 45))
            editor.end_time.setTime(QTime(8, 30))
            editor.save_button.click()
            model = adapter.view_model()
            assert model.templates[0].start_time == "07:45"
            from types import SimpleNamespace
            from src.desktop_app.shell import AppShell
            shell = SimpleNamespace(lesson_time_templates_adapter=adapter, settings_screen=settings)
            AppShell.save_lesson_time_template(shell, 1, "09:00", "08:00", model.templates[0].template)
            assert editor.message.label.text() == "Beginn muss vor Ende liegen."
            assert adapter.view_model() == model
            AppShell.save_lesson_time_template(shell, 1, "07:50", "08:35", None)
            assert "inzwischen geändert" in editor.message.label.text()
            assert adapter.view_model() == model
            editor.reload_requested.connect(lambda: AppShell.reload_lesson_time_templates(shell))
            editor.start_time.setTime(QTime(12, 0))
            editor.reload_button.click()
            editor.template_combo.setCurrentIndex(1)
            assert editor.start_time.time() == QTime(7, 45)
            timetable = TimetableDesktopAdapter(runtime.database)
            old = timetable.week_view_model().days[0].entries[0]
            dialog = TimetableEntryDialog(timetable.week_view_model(), weekday=1, entry=old, templates=model.templates)
            assert dialog.command().start_time == "09:00"
            dialog.lesson_template_combo.setCurrentIndex(1)
            dialog.apply_template_button.click()
            dialog.start_time.setTime(QTime(7, 55))
            timetable.save_entry(dialog.command())
            adapter.save_template(1, "08:00", "08:45", model.templates[0].template)
            new_week = timetable.week_view_model()
            saved = new_week.days[0].entries[0]
            assert (saved.start_time, saved.end_time) == ("07:55", "08:30")
            reopened = TimetableEntryDialog(new_week, weekday=1, entry=saved, templates=adapter.view_model().templates)
            assert (reopened.command().start_time, reopened.command().end_time) == ("07:55", "08:30")
            settings.close(); dialog.close(); reopened.close()
        with pytest.raises(RuntimeError):
            adapter.view_model()
        with pytest.raises(ValueError, match="synthetic_v5_runtime_required"):
            LessonTimeTemplatesDesktopAdapter(object())
        channel.send(("ok",))
    except BaseException as error:
        channel.send(("error", type(error).__name__, str(error)))
    finally:
        channel.close()


def test_qualified_existing_runtime_widgets_and_saved_timetable_in_real_process(tmp_path):
    import multiprocessing
    from tests.test_transactional_schema_migration import _seed_case
    from src.security.transactional_schema_migration import SyntheticTransactionalMigration
    _, service = _seed_case(tmp_path)
    SyntheticTransactionalMigration(service).execute()
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=_qualified_ui_worker,
                              args=(service.paths, service.loaded, service.installation_id, child))
    process.start(); child.close()
    try:
        assert parent.poll(50), "synthetic UI worker did not report"
        result = parent.recv()
        process.join(10)
        assert process.exitcode == 0 and result == ("ok",), result
    finally:
        if process.is_alive():
            process.kill(); process.join(10)
        parent.close()
