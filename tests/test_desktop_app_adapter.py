"""Tests for the experimental PySide6 desktop adapter."""

from __future__ import annotations

import inspect
import importlib
import tempfile
import unittest
from pathlib import Path

from src.application.commands import CreateStudentCommand
from src.application.dispatcher import SuccessResult
from src.core.constants import COURSE_ID_PREFIX, GROUP_ID_PREFIX, STUDENT_ID_PREFIX
from src.core.sqlite_store import SQLiteStudentRepository, create_sqlite_seed_database
from src.desktop_app.adapters import student_desktop_adapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.navigation import resolve_navigation_target
from src.desktop_app.view_models.student_view_model import filter_student_list


class DesktopAppAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
        self.database = create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)

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
            "src.desktop_app.shell",
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
            "src.desktop_app.adapters.student_desktop_adapter",
            "src.desktop_app.app",
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
            "src.desktop_app.view_models.student_view_model",
        ):
            with self.subTest(module_name=module_name):
                importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
