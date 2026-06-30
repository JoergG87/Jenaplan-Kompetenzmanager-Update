"""Tests for the Sprint 5.2a SQLite architecture spike."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from openpyxl import load_workbook

from src.core.constants import (
    ACTIVE,
    COURSE_ID_PREFIX,
    GROUP_ID_PREFIX,
    STUDENT_ID,
    STUDENT_ID_PREFIX,
    TABLE_COURSES,
    TABLE_GROUPS,
    TABLE_STUDENTS,
)
from src.core.sqlite_store import (
    SQLiteCourseRepository,
    SQLiteDatabase,
    SQLiteGroupRepository,
    SQLiteStudentRepository,
    build_workbook_data_from_sqlite,
    create_sqlite_seed_database,
)
from src.core.workbook_data import seed_workbook_data
from src.ui.screens.klassenuebersicht import ClassOverviewV02WorkbookBuilder


class SQLiteSpikeTest(unittest.TestCase):
    def test_seed_data_is_written_to_sqlite_without_id_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            create_sqlite_seed_database(database_path)

            self.assertTrue(database_path.exists())
            with closing(sqlite3.connect(database_path)) as connection:
                with connection:
                    student_count = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                    group_count = connection.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
                    course_count = connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
                    first_student_id = connection.execute(
                        "SELECT student_id FROM students ORDER BY student_id LIMIT 1"
                    ).fetchone()[0]
                    first_group_id = connection.execute(
                        "SELECT group_id FROM groups ORDER BY group_id LIMIT 1"
                    ).fetchone()[0]
                    first_course_id = connection.execute(
                        "SELECT course_id FROM courses ORDER BY course_id LIMIT 1"
                    ).fetchone()[0]

        seed_data = seed_workbook_data()
        self.assertEqual(student_count, len(seed_data.students))
        self.assertEqual(group_count, len(seed_data.groups))
        self.assertEqual(course_count, len(seed_data.courses))
        self.assertEqual(first_student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(first_group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(first_course_id, f"{COURSE_ID_PREFIX}-000001")

    def test_repositories_read_seed_records_from_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            students = SQLiteStudentRepository(database).list_students()
            groups = SQLiteGroupRepository(database).list_groups()
            courses = SQLiteCourseRepository(database).list_courses()

        self.assertEqual(len(students), 28)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(courses), 3)
        self.assertTrue(all(student.student_id.startswith(STUDENT_ID_PREFIX) for student in students))
        self.assertTrue(all(group.active for group in groups))
        self.assertTrue(all(course.active for course in courses))

    def test_existing_projection_can_be_built_from_sqlite_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            workbook_path = Path(temp_dir) / "sqlite_projection.xlsx"
            create_sqlite_seed_database(database_path)
            projection_data = build_workbook_data_from_sqlite(database_path)
            ClassOverviewV02WorkbookBuilder(workbook_path, projection_data).build()
            workbook = load_workbook(workbook_path, data_only=False)

        students_sheet = workbook["data_students"]
        groups_sheet = workbook["data_groups"]
        courses_sheet = workbook["data_courses"]
        overview_sheet = workbook["Stammgruppenübersicht"]

        self.assertIn(TABLE_STUDENTS, students_sheet.tables)
        self.assertIn(TABLE_GROUPS, groups_sheet.tables)
        self.assertIn(TABLE_COURSES, courses_sheet.tables)
        self.assertEqual(students_sheet.max_row, 29)
        self.assertTrue(str(overview_sheet["X2"].value).startswith(STUDENT_ID_PREFIX))
        self.assertIn(TABLE_STUDENTS, overview_sheet["Y2"].value)
        self.assertIn(f"[{ACTIVE}]", overview_sheet["B6"].value)
        self.assertIn("ui_student_slot_id_01", workbook.defined_names)

        headers = [cell.value for cell in students_sheet[1]]
        student_id_column = headers.index(STUDENT_ID) + 1
        stored_ids = [
            students_sheet.cell(row, student_id_column).value
            for row in range(2, students_sheet.max_row + 1)
        ]
        self.assertIn(f"{STUDENT_ID_PREFIX}-000001", stored_ids)


if __name__ == "__main__":
    unittest.main()
