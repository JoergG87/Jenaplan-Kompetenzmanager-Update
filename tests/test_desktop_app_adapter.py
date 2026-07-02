"""Tests for the experimental PySide6 desktop adapter."""

from __future__ import annotations

import inspect
import importlib
import os
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

from src.application.commands import CreateStudentCommand
from src.application.dispatcher import SuccessResult
from src.core.constants import COURSE_ID_PREFIX, GROUP_ID_PREFIX, STUDENT_ID_PREFIX
from src.core.sqlite_store import SQLiteStudentRepository, create_sqlite_seed_database
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters import student_desktop_adapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs import app_info_dialog
from src.desktop_app.dialogs import dialog_buttons
from src.desktop_app.dialogs import master_data_dialog
from src.desktop_app.dialogs import new_student_dialog
from src.desktop_app.dialogs import new_observation_dialog
from src.desktop_app.navigation import NAVIGATION_ITEMS, resolve_navigation_target
from src.desktop_app.screens import master_data_screen
from src.desktop_app.screens import overview_screen
from src.desktop_app.screens import students_screen
from src.desktop_app import main
from src.desktop_app import shell
from src.desktop_app import theme
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_GROUP_EMPTY_COURSES_MESSAGE,
    COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
    COURSE_COLOR_OPTIONS,
    MASTER_DATA_EMPTY_NAME_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    MasterDataViewModel,
    course_color_from_key,
    normalize_master_data_name,
)
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_ATTACHMENT_EMPTY_STATE,
    OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE,
    OBSERVATION_CONTEXT_OPTIONS,
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_SAVE_PLACEHOLDER_MESSAGE,
    ObservationCompetencyRatingDraft,
    ObservationDraftViewModel,
    observation_rating_keys,
)
from src.desktop_app.view_models.student_view_model import (
    PROFILE_ACTION_MESSAGES,
    PROFILE_SECTION_PLACEHOLDERS,
    filter_student_list,
)


class DesktopAppAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
        self.database = create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.adapter)
        self.curriculum_adapter = CurriculumDesktopAdapter()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_adapter_creates_create_student_command(self) -> None:
        command = self.adapter.create_student_command(
            first_name="Jule",
            last_name="Schneider",
            group_id=f"{GROUP_ID_PREFIX}-000001",
            course_id=f"{COURSE_ID_PREFIX}-000001",
            student_notes="Liest gern.",
        )

        self.assertIsInstance(command, CreateStudentCommand)
        self.assertEqual(command.command_name, "student.create")
        self.assertEqual(command.first_name, "Jule")
        self.assertEqual(command.last_name, "Schneider")
        self.assertEqual(command.group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(command.course_id, f"{COURSE_ID_PREFIX}-000001")
        self.assertEqual(command.student_notes, "Liest gern.")

    def test_save_new_student_uses_application_stack(self) -> None:
        result = self.adapter.save_new_student(
            first_name="Jule",
            last_name="Schneider",
            group_id=f"{GROUP_ID_PREFIX}-000001",
            course_id=f"{COURSE_ID_PREFIX}-000001",
            student_notes="Liest gern.",
        )

        self.assertIsInstance(result, SuccessResult)
        student = result.value
        self.assertEqual(student.student_id, f"{STUDENT_ID_PREFIX}-000029")

        stored_student = SQLiteStudentRepository(self.database).get_student_by_id(student.student_id)
        self.assertIsNotNone(stored_student)
        self.assertEqual(stored_student.first_name, "Jule")
        self.assertEqual(len(SQLiteStudentRepository(self.database).list_students()), 29)

    def test_group_and_course_name_mapping_uses_ids(self) -> None:
        group_ids = self.adapter.group_id_by_name()
        course_ids = self.adapter.course_id_by_name()

        self.assertEqual(group_ids["Grashüpfer"], f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(course_ids["Kurs 1"], f"{COURSE_ID_PREFIX}-000001")
        self.assertEqual(course_ids["Kurs 2"], f"{COURSE_ID_PREFIX}-000002")
        self.assertEqual(course_ids["Kurs 3"], f"{COURSE_ID_PREFIX}-000003")

    def test_student_list_uses_readable_group_and_course_names(self) -> None:
        students = self.adapter.list_students()

        self.assertEqual(len(students), 28)
        self.assertEqual(students[0].student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(students[0].group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(students[0].group_name, "Grashüpfer")
        self.assertIn(students[0].course_id, {
            f"{COURSE_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000002",
            f"{COURSE_ID_PREFIX}-000003",
        })
        self.assertIn(students[0].course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})

    def test_group_summary_counts_active_students(self) -> None:
        groups = self.adapter.list_group_summaries()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(groups[0].group_name, "Grashüpfer")
        self.assertEqual(groups[0].active_student_count, 28)

    def test_navigation_contains_master_data_screen(self) -> None:
        navigation_labels = tuple(item.label for item in NAVIGATION_ITEMS)
        navigation_keys = tuple(item.key for item in NAVIGATION_ITEMS)

        self.assertIn("Stammdaten", navigation_labels)
        self.assertIn("master_data", navigation_keys)
        self.assertEqual(
            resolve_navigation_target("master_data").screen_key,
            "master_data",
        )

    def test_macos_launcher_exists_and_starts_desktop_app_module(self) -> None:
        launcher_path = Path("launcher/Jenaplan_Kompetenzmanager.command")
        launcher_source = launcher_path.read_text(encoding="utf-8")

        self.assertTrue(launcher_path.exists())
        self.assertTrue(os.access(launcher_path, os.X_OK))
        self.assertIn(".venv/bin/python", launcher_source)
        self.assertIn("python3", launcher_source)
        self.assertIn("-m src.desktop_app.main", launcher_source)

    def test_master_data_view_model_displays_groups_and_courses(self) -> None:
        view_model = self.master_data_adapter.view_model()

        self.assertIsInstance(view_model, MasterDataViewModel)
        self.assertEqual(view_model.groups[0].item_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(view_model.groups[0].name, "Grashüpfer")
        self.assertTrue(view_model.groups[0].is_persistent)
        self.assertEqual(view_model.groups[0].status_label, "Vorhanden")
        self.assertEqual(
            {course.name for course in view_model.courses},
            {"Kurs 1", "Kurs 2", "Kurs 3"},
        )
        self.assertEqual(view_model.courses[0].color_name, "Blau")
        self.assertEqual(view_model.courses[0].color_hex, "#2563EB")
        self.assertTrue(view_model.courses[0].has_color)
        self.assertEqual(len(view_model.course_groups), 1)
        self.assertEqual(
            view_model.course_groups[0].name,
            "Mathe/Deutsch Kursverbund A",
        )
        self.assertEqual(
            view_model.course_groups[0].selected_group_ids,
            (f"{GROUP_ID_PREFIX}-000001",),
        )
        self.assertEqual(
            view_model.course_groups[0].selected_course_ids,
            (
                f"{COURSE_ID_PREFIX}-000001",
                f"{COURSE_ID_PREFIX}-000002",
                f"{COURSE_ID_PREFIX}-000003",
            ),
        )

    def test_course_group_view_model_contains_groups_and_courses(self) -> None:
        course_group = CourseGroupViewModel(
            "course-group-a",
            "Mathe/Deutsch Kursverbund A",
            (f"{GROUP_ID_PREFIX}-000001", f"{GROUP_ID_PREFIX}-000002"),
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )

        self.assertEqual(course_group.course_group_id, "course-group-a")
        self.assertIn(f"{GROUP_ID_PREFIX}-000001", course_group.selected_group_ids)
        self.assertIn(f"{COURSE_ID_PREFIX}-000001", course_group.selected_course_ids)

    def test_master_data_adapter_updates_course_group_session_locally(self) -> None:
        updated_course_group = self.master_data_adapter.update_course_group(
            "course-group-default",
            "Mathe/Deutsch Kursverbund B",
            (f"{GROUP_ID_PREFIX}-000001",),
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )
        view_model = self.master_data_adapter.view_model()

        self.assertEqual(updated_course_group.name, "Mathe/Deutsch Kursverbund B")
        self.assertEqual(
            updated_course_group.selected_group_ids,
            (f"{GROUP_ID_PREFIX}-000001",),
        )
        self.assertEqual(
            updated_course_group.selected_course_ids,
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
        )
        self.assertEqual(view_model.course_groups[0], updated_course_group)

    def test_course_group_update_validation_rejects_empty_values(self) -> None:
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            self.master_data_adapter.update_course_group(
                "course-group-default",
                "",
                (f"{GROUP_ID_PREFIX}-000001",),
                (f"{COURSE_ID_PREFIX}-000001",),
            )
        with self.assertRaisesRegex(ValueError, COURSE_GROUP_EMPTY_GROUPS_MESSAGE):
            self.master_data_adapter.update_course_group(
                "course-group-default",
                "Mathe/Deutsch Kursverbund A",
                (),
                (f"{COURSE_ID_PREFIX}-000001",),
            )
        with self.assertRaisesRegex(ValueError, COURSE_GROUP_EMPTY_COURSES_MESSAGE):
            self.master_data_adapter.update_course_group(
                "course-group-default",
                "Mathe/Deutsch Kursverbund A",
                (f"{GROUP_ID_PREFIX}-000001",),
                (),
            )

    def test_course_color_options_are_registered_for_master_data_light(self) -> None:
        self.assertEqual(
            COURSE_COLOR_OPTIONS,
            (
                ("Blau", "#2563EB"),
                ("Grün", "#16A34A"),
                ("Orange", "#F97316"),
                ("Gelb", "#EAB308"),
                ("Lila", "#9333EA"),
                ("Rot", "#DC2626"),
                ("Grau", "#6B7280"),
            ),
        )
        self.assertEqual(course_color_from_key("", 0), ("Blau", "#2563EB"))
        self.assertEqual(course_color_from_key("", 1), ("Grün", "#16A34A"))
        self.assertEqual(course_color_from_key("#EAB308"), ("Gelb", "#EAB308"))

    def test_master_data_adapter_adds_non_persistent_groups_and_courses(self) -> None:
        group = self.master_data_adapter.add_group("Eulen")
        course = self.master_data_adapter.add_course("Kurs 4", "#9333EA")
        view_model = self.master_data_adapter.view_model()

        self.assertIsInstance(group, MasterDataItemViewModel)
        self.assertEqual(group.name, "Eulen")
        self.assertFalse(group.is_persistent)
        self.assertEqual(group.status_label, "Nur vorgemerkt")
        self.assertEqual(course.name, "Kurs 4")
        self.assertEqual(course.color_name, "Lila")
        self.assertEqual(course.color_hex, "#9333EA")
        self.assertFalse(course.is_persistent)
        self.assertIn("Eulen", {item.name for item in view_model.groups})
        self.assertIn("Kurs 4", {item.name for item in view_model.courses})

    def test_master_data_adapter_renames_non_persistent_state(self) -> None:
        group = self.master_data_adapter.rename_group(
            f"{GROUP_ID_PREFIX}-000001",
            "Grashüpfer A",
        )
        course = self.master_data_adapter.rename_course(
            f"{COURSE_ID_PREFIX}-000001",
            "Kurs 1A",
            "#DC2626",
        )
        view_model = self.master_data_adapter.view_model()

        self.assertEqual(group.name, "Grashüpfer A")
        self.assertEqual(course.name, "Kurs 1A")
        self.assertEqual(course.color_name, "Rot")
        self.assertEqual(course.color_hex, "#DC2626")
        self.assertIn("Grashüpfer A", {item.name for item in view_model.groups})
        self.assertIn("Kurs 1A", {item.name for item in view_model.courses})

    def test_master_data_empty_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            normalize_master_data_name("   ")
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            self.master_data_adapter.add_group("")
        with self.assertRaisesRegex(ValueError, MASTER_DATA_EMPTY_NAME_MESSAGE):
            self.master_data_adapter.add_course("")

    def test_master_data_widgets_do_not_access_sqlite_directly(self) -> None:
        screen_source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)

        self.assertNotIn("sqlite", screen_source.casefold())
        self.assertNotIn("sqlite", dialog_source.casefold())
        self.assertNotIn("INSERT INTO", screen_source)
        self.assertNotIn("UPDATE ", screen_source)
        self.assertNotIn("DELETE FROM", screen_source)

    def test_dialogs_use_consistent_save_cancel_buttons(self) -> None:
        button_source = inspect.getsource(dialog_buttons)

        self.assertIn('DIALOG_CANCEL_TEXT = "Abbrechen"', button_source)
        self.assertIn('DIALOG_SAVE_TEXT = "Speichern"', button_source)
        self.assertIn("configure_save_cancel_buttons(buttons)", inspect.getsource(new_student_dialog))
        self.assertIn("configure_save_cancel_buttons(buttons)", inspect.getsource(new_observation_dialog))
        self.assertIn("configure_save_cancel_buttons(buttons)", inspect.getsource(master_data_dialog))
        self.assertIn("DIALOG_PRIMARY_BUTTON_STYLE", button_source)
        self.assertIn("PRIMARY_BUTTON_STYLESHEET", button_source)
        self.assertIn("background-color: #2563EB", theme.PRIMARY_BUTTON_STYLESHEET)
        self.assertIn("color: #FFFFFF", theme.PRIMARY_BUTTON_STYLESHEET)
        self.assertIn("save_button.setStyleSheet(DIALOG_PRIMARY_BUTTON_STYLE)", button_source)
        self.assertIn("save_button.setDefault(True)", button_source)
        self.assertIn('cancel_button.setShortcut("Esc")', button_source)

    def test_pyside_app_uses_icon_based_visual_theme(self) -> None:
        theme_source = inspect.getsource(theme)
        main_source = inspect.getsource(main)
        shell_source = inspect.getsource(shell)
        screen_source = inspect.getsource(students_screen)

        self.assertIn('COLOR_NAVY = "#0B3A63"', theme_source)
        self.assertIn('COLOR_BLUE = "#2563EB"', theme_source)
        self.assertIn('COLOR_TURQUOISE = "#0EA5A7"', theme_source)
        self.assertIn('COLOR_GREEN = "#16A34A"', theme_source)
        self.assertIn('COLOR_ORANGE = "#F97316"', theme_source)
        self.assertIn("APP_STYLESHEET", theme_source)
        self.assertIn("QListWidget#AppNavigation", theme.APP_STYLESHEET)
        self.assertIn("QFrame#AppCard", theme.APP_STYLESHEET)
        self.assertIn("rgba(255, 255, 255, 238)", theme.APP_STYLESHEET)
        self.assertIn("def apply_app_theme(", theme_source)
        self.assertIn("def create_card(", theme_source)
        self.assertIn("def set_label_style(", theme_source)
        self.assertIn("apply_app_theme(app)", main_source)
        self.assertIn('root.setObjectName("AppRoot")', shell_source)
        self.assertIn('self.navigation.setObjectName("AppNavigation")', shell_source)
        self.assertIn('set_label_style(title, "screen_title")', screen_source)

    def test_app_info_dialog_contains_non_technical_app_information(self) -> None:
        source = inspect.getsource(app_info_dialog)
        shell_source = inspect.getsource(shell)

        self.assertIn('APP_INFO_APP_NAME = "Jenaplan Kompetenzmanager"', source)
        self.assertIn('APP_INFO_MODE = "PySide6 Prototyp"', source)
        self.assertIn(
            'APP_INFO_STORAGE_HINT = "Einige Funktionen sind noch nicht dauerhaft gespeichert."',
            source,
        )
        self.assertIn("AppInfoDialog", shell_source)
        self.assertIn('self.info_button = QPushButton("Info")', shell_source)
        self.assertIn("open_app_info_dialog", shell_source)

    def test_master_data_course_screen_shows_course_color_marker(self) -> None:
        source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_new_course_dialog)

        self.assertIn('("Farbe", "Name", "Status", "Aktion")', source)
        self.assertIn('QTableWidgetItem(f"● {item.color_name}")', source)
        self.assertIn("setForeground(QColor(item.color_hex))", source)
        self.assertIn("COURSE_COLOR_OPTIONS", dialog_source)
        self.assertIn('form.addRow("Farbe", self.color_select)', dialog_source)
        self.assertIn("include_color=True", shell_source)
        self.assertIn("dialog.color_hex()", shell_source)

    def test_student_list_items_include_course_color(self) -> None:
        students = self.adapter.list_students()

        self.assertEqual(students[0].group_name, "Grashüpfer")
        self.assertIn(students[0].course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})
        self.assertIn(students[0].course_color_name, {"Blau", "Grün", "Orange"})
        self.assertIn(
            students[0].course_color_hex,
            {"#2563EB", "#16A34A", "#F97316"},
        )

    def test_students_screen_shows_course_color_marker(self) -> None:
        source = inspect.getsource(importlib.import_module(
            "src.desktop_app.screens.students_screen"
        ))

        self.assertIn('self.table.setHorizontalHeaderLabels(("Name", "Kurs"))', source)
        self.assertIn(
            "self.table.setCellWidget(row_index, 1, self._course_cell(student))",
            source,
        )
        self.assertIn('marker = QLabel("●")', source)
        self.assertIn("student.course_color_hex or '#6B7280'", source)
        self.assertIn('set_label_style(course_label, "body")', source)
        self.assertIn("QHeaderView.ResizeMode.ResizeToContents", source)
        self.assertNotIn('"Stammgruppe", "Kurs"', source)
        self.assertNotIn("self.table.setItem(row_index, 1", source)

    def test_overview_screen_shows_master_data_groups_and_courses(self) -> None:
        source = inspect.getsource(overview_screen)
        shell_source = inspect.getsource(shell.AppShell.refresh_overview)

        self.assertIn("MasterDataViewModel", source)
        self.assertIn("MasterDataItemViewModel", source)
        self.assertIn("CourseGroupViewModel", source)
        self.assertIn("def set_master_data(", source)
        self.assertIn("view_model.groups", source)
        self.assertIn("view_model.course_groups", source)
        self.assertIn("course_group.selected_group_ids", source)
        self.assertIn("course_group.selected_course_ids", source)
        self.assertIn("course_selected = Signal(str, str)", source)
        self.assertIn('QLabel("●")', source)
        self.assertIn("course.color_hex or '#6B7280'", source)
        self.assertIn("self.master_data_adapter.view_model()", shell_source)
        self.assertIn("self.adapter.list_group_summaries()", shell_source)

    def test_master_data_screen_shows_course_groups(self) -> None:
        source = inspect.getsource(master_data_screen)
        dialog_source = inspect.getsource(master_data_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_edit_course_group_dialog)

        self.assertIn('MASTER_DATA_COURSE_GROUP_EMPTY_STATE = "Noch keine Kursverbünde vorhanden."', source)
        self.assertIn('"Kursverbünde"', source)
        self.assertIn("course_group_edit_requested = Signal(str)", source)
        self.assertIn("self.course_group_table = QTableWidget(0, 4)", source)
        self.assertIn(
            'table.setHorizontalHeaderLabels(("Name", "Stammgruppen", "Kurse", "Aktion"))',
            source,
        )
        self.assertIn("item.selected_group_ids", source)
        self.assertIn("item.selected_course_ids", source)
        self.assertIn('edit_button = QPushButton("Bearbeiten")', source)
        self.assertIn("CourseGroupDialog", dialog_source)
        self.assertIn("QCheckBox", dialog_source)
        self.assertIn("COURSE_GROUP_EMPTY_GROUPS_MESSAGE", dialog_source)
        self.assertIn("COURSE_GROUP_EMPTY_COURSES_MESSAGE", dialog_source)
        self.assertIn("configure_save_cancel_buttons(buttons)", dialog_source)
        self.assertIn("update_course_group(", shell_source)
        self.assertIn("_clear_invalid_course_group_filter", shell_source)

    def test_course_group_filter_limits_course_to_selected_groups(self) -> None:
        with self.database.connect() as connection:
            with connection:
                connection.execute(
                    "INSERT INTO groups (group_id, group_name, active) VALUES (?, ?, ?)",
                    (f"{GROUP_ID_PREFIX}-000002", "Füchse", 1),
                )
                connection.execute(
                    """
                    INSERT INTO students (
                        student_id,
                        first_name,
                        last_name,
                        group_id,
                        course_id,
                        student_notes,
                        active,
                        created_at,
                        updated_at,
                        archived_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{STUDENT_ID_PREFIX}-999999",
                        "Test",
                        "Fuchs",
                        f"{GROUP_ID_PREFIX}-000002",
                        f"{COURSE_ID_PREFIX}-000001",
                        "",
                        1,
                        "2026-07-02",
                        "2026-07-02",
                        None,
                    ),
                )

        adapter = StudentDesktopAdapter(self.database_path)
        global_course_students = adapter.list_students(
            course_id=f"{COURSE_ID_PREFIX}-000001",
        )
        course_group_students = adapter.list_students(
            course_id=f"{COURSE_ID_PREFIX}-000001",
            group_ids=(f"{GROUP_ID_PREFIX}-000001",),
        )

        self.assertIn(
            f"{STUDENT_ID_PREFIX}-999999",
            {student.student_id for student in global_course_students},
        )
        self.assertNotIn(
            f"{STUDENT_ID_PREFIX}-999999",
            {student.student_id for student in course_group_students},
        )
        self.assertTrue(all(
            student.group_id == f"{GROUP_ID_PREFIX}-000001"
            for student in course_group_students
        ))

    def test_student_list_search_and_empty_states_are_polished(self) -> None:
        source = inspect.getsource(students_screen)

        self.assertIn('STUDENT_SEARCH_PLACEHOLDER = "Schüler suchen …"', source)
        self.assertIn("Noch keine Schüler vorhanden.", source)
        self.assertIn("Lege über „+ Schüler“ den ersten Schüler an.", source)
        self.assertIn('STUDENT_SEARCH_EMPTY_STATE = "Keine Schüler gefunden."', source)
        self.assertIn('clear_search_button = QPushButton("Zurücksetzen")', source)
        self.assertIn("self.search_input.text().strip()", source)

    def test_master_data_empty_states_are_registered(self) -> None:
        source = inspect.getsource(master_data_screen)

        self.assertIn(
            'MASTER_DATA_GROUP_EMPTY_STATE = "Noch keine Stammgruppen vorhanden."',
            source,
        )
        self.assertIn(
            'MASTER_DATA_COURSE_EMPTY_STATE = "Noch keine Kurse vorhanden."',
            source,
        )
        self.assertIn("self.group_empty_state_label.setVisible(not items)", source)
        self.assertIn("self.course_empty_state_label.setVisible(not items)", source)

    def test_new_student_dialog_uses_master_data_for_group_and_course_options(self) -> None:
        source = inspect.getsource(new_student_dialog)
        shell_source = inspect.getsource(shell.AppShell.open_new_student_dialog)

        self.assertIn("MasterDataDesktopAdapter", source)
        self.assertIn("self.master_data_adapter.view_model()", source)
        self.assertIn("self.group_items = {group.item_id: group", source)
        self.assertIn("self.course_items = {course.item_id: course", source)
        self.assertIn("self._populate_master_data_select(", source)
        self.assertIn("select.addItem(item.name, item.item_id)", source)
        self.assertIn("NewStudentDialog(self.adapter, self.master_data_adapter)", shell_source)

    def test_new_student_dialog_uses_required_dropdown_placeholders(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertIn('STUDENT_DIALOG_SELECT_PLACEHOLDER = "Bitte auswählen"', source)
        self.assertIn('"Keine Stammgruppen vorhanden"', source)
        self.assertIn('"Keine Kurse vorhanden"', source)
        self.assertIn("select.addItem(STUDENT_DIALOG_SELECT_PLACEHOLDER, \"\")", source)

    def test_new_student_dialog_validates_name_group_and_course(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertIn('STUDENT_DIALOG_EMPTY_NAME_MESSAGE = "Bitte einen Namen eingeben."', source)
        self.assertIn(
            'STUDENT_DIALOG_GROUP_REQUIRED_MESSAGE = "Bitte eine Stammgruppe auswählen."',
            source,
        )
        self.assertIn(
            'STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE = "Bitte einen Kurs auswählen."',
            source,
        )
        self.assertIn("if not self.first_name_input.text().strip()", source)
        self.assertIn("if not self.last_name_input.text().strip()", source)
        self.assertIn("if group is None", source)
        self.assertIn("if course is None", source)
        self.assertIn("if not group.is_persistent", source)
        self.assertIn("if not course.is_persistent", source)

    def test_new_student_dialog_widgets_do_not_access_sqlite_directly(self) -> None:
        source = inspect.getsource(new_student_dialog)

        self.assertNotIn("sqlite", source.casefold())
        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)

    def test_selected_student_creates_profile_view_model(self) -> None:
        students = self.adapter.list_students()
        profile = self.adapter.get_student_profile(students[0].student_id)

        self.assertIsNotNone(profile)
        self.assertEqual(profile.student_id, students[0].student_id)
        self.assertEqual(profile.display_name, students[0].display_name)
        self.assertEqual(profile.group_name, "Grashüpfer")
        self.assertIn(profile.course_name, {"Kurs 1", "Kurs 2", "Kurs 3"})
        self.assertIsInstance(profile.student_notes, str)
        self.assertTrue(profile.active)

    def test_student_profile_view_model_contains_header_and_basis_data(self) -> None:
        students = self.adapter.list_students()
        profile = self.adapter.get_student_profile(students[0].student_id)

        self.assertIsNotNone(profile)
        self.assertTrue(profile.student_id.startswith(STUDENT_ID_PREFIX))
        self.assertEqual(profile.display_name, students[0].display_name)
        self.assertEqual(profile.group_name, students[0].group_name)
        self.assertEqual(profile.course_name, students[0].course_name)
        self.assertIsInstance(profile.student_notes, str)

    def test_profile_placeholder_messages_are_registered(self) -> None:
        self.assertEqual(
            PROFILE_ACTION_MESSAGES["observation"],
            "Beobachtungen werden in einem späteren Sprint erfasst.",
        )
        self.assertEqual(
            PROFILE_ACTION_MESSAGES["document"],
            "Dokumente werden in einem späteren Sprint verwaltet.",
        )
        self.assertEqual(
            PROFILE_ACTION_MESSAGES["edit"],
            "Bearbeiten wird in einem späteren Sprint umgesetzt.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["observations_title"],
            "Noch keine Beobachtungen erfasst.",
        )
        self.assertEqual(
            PROFILE_SECTION_PLACEHOLDERS["documents_hint"],
            "Dokumente werden schülerzentriert verwaltet.",
        )

    def test_observation_rating_options_use_required_scale(self) -> None:
        self.assertEqual(observation_rating_keys(), ("++", "+", "-", "--"))
        self.assertEqual(
            OBSERVATION_RATING_OPTIONS,
            (
                "++ sicher erreicht",
                "+ erreicht",
                "- in Entwicklung",
                "-- Unterstützungsbedarf",
            ),
        )

    def test_curriculum_catalog_loads_active_subjects(self) -> None:
        subjects = self.curriculum_adapter.list_active_subjects()

        self.assertEqual(
            tuple(subject.display_name for subject in subjects),
            (
                "Deutsch",
                "Mathematik",
                "EPU",
                "Musik",
                "Kunst",
                "Sport",
                "Sozialkompetenz",
                "Ethik",
                "Religion",
                "Werken",
                "Schulgarten",
            ),
        )

    def test_curriculum_catalog_uses_epu_instead_of_sachunterricht(self) -> None:
        entries = self.curriculum_adapter.list_entries()
        subject_names = {entry.subject_display_name for entry in entries}
        epu_entries = [entry for entry in entries if entry.subject_key == "epu"]

        self.assertIn("EPU", subject_names)
        self.assertNotIn("Sachunterricht", subject_names)
        self.assertTrue(epu_entries)
        self.assertTrue(all(
            entry.official_subject_name == "Heimat- und Sachkunde"
            for entry in epu_entries
        ))
        self.assertTrue(all(
            entry.subject_full_name == "Epochaler Projektunterricht"
            for entry in epu_entries
        ))

    def test_curriculum_catalog_maps_kunst_to_kunsterziehung(self) -> None:
        kunst_entries = [
            entry
            for entry in self.curriculum_adapter.list_entries()
            if entry.subject_key == "kunst"
        ]

        self.assertTrue(kunst_entries)
        self.assertTrue(all(
            entry.subject_display_name == "Kunst"
            for entry in kunst_entries
        ))
        self.assertTrue(all(
            entry.official_subject_name == "Kunsterziehung"
            for entry in kunst_entries
        ))

    def test_curriculum_catalog_contains_extended_subjects(self) -> None:
        subjects = {
            subject.display_name
            for subject in self.curriculum_adapter.list_active_subjects()
            if not subject.is_core_subject
        }

        self.assertEqual(subjects, {"Ethik", "Religion", "Werken", "Schulgarten"})

    def test_curriculum_catalog_filters_competencies_by_subject(self) -> None:
        epu_competencies = self.curriculum_adapter.list_competencies_for_subject("epu")
        math_competencies = self.curriculum_adapter.list_competencies_for_subject("mathematik")

        self.assertGreaterEqual(len(epu_competencies), 6)
        self.assertTrue(all(entry.subject_key == "epu" for entry in epu_competencies))
        self.assertTrue(any(
            entry.learning_area == "Natur und Umwelt"
            for entry in epu_competencies
        ))
        self.assertTrue(all(
            entry.subject_key == "mathematik"
            for entry in math_competencies
        ))

    def test_curriculum_competency_options_have_short_display_labels(self) -> None:
        epu_competency = self.curriculum_adapter.list_competencies_for_subject("epu")[0]

        self.assertEqual(epu_competency.competency_display_name, epu_competency.learning_area)
        self.assertEqual(epu_competency.competency_label, epu_competency.learning_area)
        self.assertNotEqual(epu_competency.competency_display_name, epu_competency.competency_text)
        self.assertIn(epu_competency.competency_text, epu_competency.competency_detail_label)

    def test_observation_dialog_uses_curriculum_catalog_data(self) -> None:
        source = inspect.getsource(new_observation_dialog)
        view_model_source = inspect.getsource(importlib.import_module(
            "src.desktop_app.view_models.observation_view_model"
        ))

        self.assertIn("CurriculumDesktopAdapter", source)
        self.assertIn("list_active_subjects", source)
        self.assertIn("list_competencies_for_subject", source)
        self.assertIn("currentIndexChanged.connect(self._refresh_competencies)", source)
        self.assertIn("self.competency_list.clear()", source)
        self.assertNotIn("OBSERVATION_SUBJECT_OPTIONS", source)
        self.assertNotIn("OBSERVATION_COMPETENCY_OPTIONS", source)
        self.assertNotIn("Sachunterricht", view_model_source)

    def test_observation_dialog_uses_checkbox_list_for_competencies(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertIn("QListWidget.SelectionMode.NoSelection", source)
        self.assertIn("ItemIsUserCheckable", source)
        self.assertIn("Qt.CheckState.Unchecked", source)
        self.assertIn("competency.competency_display_name", source)
        self.assertIn("Mehrfachauswahl möglich", source)
        self.assertIn("_selected_competency_ratings", source)

    def test_observation_dialog_uses_rating_dropdown_per_competency(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertNotIn("self.rating_select", source)
        self.assertNotIn('form_layout.addLayout(self._field_row("Bewertung"', source)
        self.assertIn("Ausgewählte Kompetenzen bewerten", source)
        self.assertIn("Jede ausgewählte Kompetenz erhält eine eigene Bewertung.", source)
        self.assertIn("rating_select.addItem(\"Bewertung auswählen\", \"\")", source)
        self.assertIn("for rating_option in OBSERVATION_RATING_OPTIONS", source)

    def test_observation_dialog_keeps_buttons_outside_scroll_area(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertIn("QScrollArea", source)
        self.assertIn("scroll_area.setWidgetResizable(True)", source)
        self.assertIn("layout.addWidget(scroll_area, 1)", source)
        self.assertIn("layout.addWidget(buttons)", source)

    def test_observation_dialog_uses_compact_competency_layout(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertIn("self.competency_list.setMaximumHeight(138)", source)
        self.assertIn("self.competency_ratings_layout.setSpacing(4)", source)
        self.assertIn("rating_select.setMinimumWidth(190)", source)
        self.assertIn("row.addWidget(label, 1)", source)

    def test_observation_dialog_keeps_cross_subject_competency_ratings(self) -> None:
        source = inspect.getsource(new_observation_dialog)
        refresh_source = inspect.getsource(
            new_observation_dialog.NewObservationDialog._refresh_competencies
        )
        sync_source = inspect.getsource(
            new_observation_dialog.NewObservationDialog._sync_competency_ratings
        )

        self.assertIn("_remove_competency_rating_row", source)
        self.assertIn("_remove_competency_rating", source)
        self.assertIn('QPushButton("Entfernen")', source)
        self.assertIn("self.competency_rating_entries.pop", source)
        self.assertIn("self.competency_rating_widgets.pop", source)
        self.assertIn("self.competency_list.clear()", source)
        self.assertNotIn("_clear_competency_ratings", refresh_source)
        self.assertIn("competency_key in self.competency_rating_entries", refresh_source)
        self.assertIn("Qt.CheckState.Checked", refresh_source)
        self.assertIn("if competency_key not in self.competency_rating_widgets", sync_source)
        self.assertIn("elif competency_key in self.competency_rating_widgets", sync_source)

    def test_observation_context_options_match_prototype_scope(self) -> None:
        self.assertEqual(
            OBSERVATION_CONTEXT_OPTIONS,
            (
                "Lernzielkontrolle",
                "Präsentation",
                "Einzelgespräch",
                "Gruppenarbeit",
                "Leseübung",
            ),
        )

    def test_observation_draft_view_model_keeps_student_context(self) -> None:
        competency = ObservationCompetencyRatingDraft(
            subject_key="deutsch",
            subject_display_name="Deutsch",
            learning_area="Mit Texten und Medien umgehen",
            competency_group="Lesen und Verstehen",
            competency_text="Texte lesen und zentrale Informationen entnehmen",
            rating="+ erreicht",
        )
        draft = ObservationDraftViewModel(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            student_name="Emma Müller",
            date_text="2026-07-01",
            competency_ratings=(competency,),
            context="Leseübung",
            note="Liest einen bekannten Text flüssig.",
        )

        self.assertEqual(draft.student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(draft.student_name, "Emma Müller")
        self.assertEqual(draft.competency_ratings[0].subject_key, "deutsch")
        self.assertEqual(draft.competency_ratings[0].subject_display_name, "Deutsch")
        self.assertEqual(draft.competency_ratings[0].display_label, "Mit Texten und Medien umgehen")
        self.assertEqual(draft.competency_ratings[0].competency_text, "Texte lesen und zentrale Informationen entnehmen")
        self.assertEqual(draft.competency_ratings[0].rating, "+ erreicht")
        self.assertEqual(draft.attachment_names, ())

    def test_observation_draft_has_no_global_rating(self) -> None:
        field_names = {field.name for field in fields(ObservationDraftViewModel)}

        self.assertNotIn("rating", field_names)
        self.assertNotIn("subject_key", field_names)
        self.assertNotIn("subject", field_names)
        self.assertIn("competency_ratings", field_names)

    def test_observation_competency_ratings_can_span_subjects(self) -> None:
        first = ObservationCompetencyRatingDraft(
            subject_key="epu",
            subject_display_name="EPU",
            learning_area="Natur und Umwelt",
            competency_group="Erkunden und beschreiben",
            competency_text="Naturphänomene beobachten und beschreiben",
            rating="++ sicher erreicht",
        )
        second = ObservationCompetencyRatingDraft(
            subject_key="deutsch",
            subject_display_name="Deutsch",
            learning_area="Miteinander sprechen",
            competency_group="Gesprächsbeiträge",
            competency_text="Eigene Beiträge verständlich einbringen",
            rating="- in Entwicklung",
        )
        third = ObservationCompetencyRatingDraft(
            subject_key="sozialkompetenz",
            subject_display_name="Sozialkompetenz",
            learning_area="Verantwortung",
            competency_group="Auftreten",
            competency_text="Verantwortung in der Gruppe übernehmen",
            rating="+ erreicht",
        )

        draft = ObservationDraftViewModel(
            student_id=f"{STUDENT_ID_PREFIX}-000001",
            student_name="Emma Müller",
            date_text="2026-07-01",
            competency_ratings=(first, second, third),
            context="Präsentation",
            note="Präsentiert Arbeitsergebnisse vor der Gruppe.",
        )

        self.assertEqual(draft.competency_ratings[0].rating, "++ sicher erreicht")
        self.assertEqual(draft.competency_ratings[1].rating, "- in Entwicklung")
        self.assertEqual(draft.competency_ratings[2].rating, "+ erreicht")
        self.assertNotEqual(
            draft.competency_ratings[0].rating,
            draft.competency_ratings[1].rating,
        )
        self.assertEqual(
            [rating.subject_key for rating in draft.competency_ratings],
            ["epu", "deutsch", "sozialkompetenz"],
        )
        self.assertEqual(
            [rating.subject_display_name for rating in draft.competency_ratings],
            ["EPU", "Deutsch", "Sozialkompetenz"],
        )
        self.assertEqual(draft.competency_ratings[0].display_label, "Natur und Umwelt")
        self.assertEqual(draft.competency_ratings[1].display_label, "Miteinander sprechen")

    def test_observation_dialog_placeholder_messages_are_non_persistent(self) -> None:
        self.assertEqual(
            OBSERVATION_SAVE_PLACEHOLDER_MESSAGE,
            "Beobachtungen werden in einem späteren Sprint gespeichert.",
        )
        self.assertEqual(
            OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE,
            "Anhänge werden in einem späteren Sprint gespeichert.",
        )
        self.assertEqual(
            OBSERVATION_ATTACHMENT_EMPTY_STATE,
            "Noch keine Anhänge ausgewählt.",
        )

    def test_observation_dialog_has_no_productive_write_logic(self) -> None:
        source = inspect.getsource(new_observation_dialog)

        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)
        self.assertNotIn("sqlite3.connect", source)
        self.assertNotIn("ApplicationCommandDispatcher", source)
        self.assertNotIn("student.create", source)

    def test_sidebar_students_navigation_resets_to_list(self) -> None:
        target = resolve_navigation_target("students")

        self.assertEqual(target.screen_key, "students")
        self.assertTrue(target.reset_group_filter)

    def test_placeholder_navigation_keeps_target_key(self) -> None:
        target = resolve_navigation_target("reports")

        self.assertEqual(target.screen_key, "reports")
        self.assertFalse(target.reset_group_filter)

    def test_student_search_finds_first_name(self) -> None:
        students = self.adapter.list_students()
        result = filter_student_list(students, students[0].first_name)

        self.assertIn(students[0].student_id, {student.student_id for student in result})

    def test_student_search_finds_last_name(self) -> None:
        students = self.adapter.list_students()
        result = filter_student_list(students, students[0].last_name)

        self.assertIn(students[0].student_id, {student.student_id for student in result})

    def test_student_search_is_case_insensitive_and_trims_query(self) -> None:
        students = self.adapter.list_students()
        query = f"  {students[0].display_name.upper()}  "
        result = filter_student_list(students, query)

        self.assertIn(students[0].student_id, {student.student_id for student in result})

    def test_empty_student_search_returns_current_group_filter(self) -> None:
        students = self.adapter.list_students(group_id=f"{GROUP_ID_PREFIX}-000001")
        result = filter_student_list(students, "   ")

        self.assertEqual(result, students)

    def test_student_search_combines_with_group_filter(self) -> None:
        students = self.adapter.list_students(group_id=f"{GROUP_ID_PREFIX}-000001")
        result = filter_student_list(students, students[0].course_name)

        self.assertGreater(len(result), 0)
        self.assertTrue(all(student.group_id == f"{GROUP_ID_PREFIX}-000001" for student in result))

    def test_adapter_has_no_direct_sql_write_logic(self) -> None:
        source = inspect.getsource(student_desktop_adapter)

        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)
        self.assertNotIn("sqlite3.connect", source)

    def test_widgets_have_no_direct_sql_write_logic(self) -> None:
        module_names = (
            "src.desktop_app.adapters.curriculum_desktop_adapter",
            "src.desktop_app.shell",
            "src.desktop_app.dialogs.new_observation_dialog",
            "src.desktop_app.dialogs.new_student_dialog",
            "src.desktop_app.screens.overview_screen",
            "src.desktop_app.screens.students_screen",
            "src.desktop_app.screens.student_profile_screen",
            "src.desktop_app.screens.placeholder_screen",
        )

        for module_name in module_names:
            module = importlib.import_module(module_name)
            source = inspect.getsource(module)
            with self.subTest(module_name=module_name):
                self.assertNotIn("INSERT INTO", source)
                self.assertNotIn("UPDATE ", source)
                self.assertNotIn("DELETE FROM", source)
                self.assertNotIn("sqlite3.connect", source)

    def test_desktop_app_modules_are_importable(self) -> None:
        for module_name in (
            "src.desktop_app.adapters.curriculum_desktop_adapter",
            "src.desktop_app.adapters.student_desktop_adapter",
            "src.desktop_app.app",
            "src.desktop_app.dialogs.new_observation_dialog",
            "src.desktop_app.dialogs.new_student_dialog",
            "src.desktop_app.main",
            "src.desktop_app.new_student_dialog",
            "src.desktop_app.navigation",
            "src.desktop_app.screens.overview_screen",
            "src.desktop_app.screens.placeholder_screen",
            "src.desktop_app.screens.student_profile_screen",
            "src.desktop_app.screens.students_screen",
            "src.desktop_app.shell",
            "src.desktop_app.student_list_view",
            "src.desktop_app.view_models.observation_view_model",
            "src.desktop_app.view_models.student_view_model",
        ):
            with self.subTest(module_name=module_name):
                importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
