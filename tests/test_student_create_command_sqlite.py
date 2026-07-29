"""End-to-end tests for student.create through the application stack."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path

from src.application.commands import CreateStudentCommand
from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    ErrorResult,
    SuccessResult,
    student_create_handler,
)
from src.core.constants import COURSE_ID_PREFIX, GROUP_ID_PREFIX, STUDENT_ID_PREFIX
from src.core.sqlite_store import (
    SQLiteCourseRepository,
    SQLiteDatabase,
    SQLiteGroupRepository,
    SQLiteStudentRepository,
    create_sqlite_seed_database,
)
from src.core.student import StudentService, StudentValidator


class FixedClock:
    """Return a deterministic timestamp for command tests."""

    def __call__(self) -> datetime:
        return datetime(2026, 6, 30, 12, 0, tzinfo=UTC)


class DuplicateIdStudentService(StudentService):
    """Force an ID collision through the StudentService path."""

    def _generate_student_id(self) -> str:
        return f"{STUDENT_ID_PREFIX}-000001"


class StudentCreateCommandSQLiteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
        self.database = create_sqlite_seed_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_student_create_command_writes_student_to_sqlite(self) -> None:
        dispatcher = self._dispatcher()

        result = dispatcher.dispatch(
            CreateStudentCommand(
                first_name="Jule",
                last_name="Schneider",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000001",
                student_notes="Liest gern.",
            )
        )

        self.assertIsInstance(result, SuccessResult)
        student = result.value
        self.assertEqual(student.student_id, f"{STUDENT_ID_PREFIX}-000029")
        self.assertEqual(student.created_at, "2026-06-30T12:00:00+00:00")
        self.assertEqual(student.updated_at, "2026-06-30T12:00:00+00:00")
        self.assertTrue(student.active)
        self.assertIsNone(student.archived_at)

        stored_student = SQLiteStudentRepository(
            self.database,
            as_of=date(2026, 7, 13),
        ).get_student_by_id(student.student_id)
        self.assertIsNotNone(stored_student)
        self.assertEqual(stored_student.first_name, "Jule")
        self.assertEqual(stored_student.last_name, "Schneider")
        self.assertEqual(stored_student.student_notes, "Liest gern.")
        self.assertEqual(
            len(
                SQLiteStudentRepository(
                    self.database,
                    as_of=date(2026, 7, 13),
                ).list_students()
            ),
            29,
        )

    def test_missing_first_name_returns_error_result(self) -> None:
        result = self._dispatcher().dispatch(
            CreateStudentCommand(
                first_name="",
                last_name="Schneider",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )
        )

        self.assert_error(result, "StudentValidationError", "first_name")

    def test_missing_group_returns_error_result(self) -> None:
        result = self._dispatcher().dispatch(
            CreateStudentCommand(
                first_name="Jule",
                last_name="Schneider",
                group_id="",
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )
        )

        self.assert_error(result, "StudentValidationError", "group_id")

    def test_missing_course_returns_error_result(self) -> None:
        result = self._dispatcher().dispatch(
            CreateStudentCommand(
                first_name="Jule",
                last_name="Schneider",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id="",
            )
        )

        self.assert_error(result, "StudentValidationError", "course_id")

    def test_duplicate_student_id_returns_error_result(self) -> None:
        result = self._dispatcher(service_type=DuplicateIdStudentService).dispatch(
            CreateStudentCommand(
                first_name="Jule",
                last_name="Schneider",
                group_id=f"{GROUP_ID_PREFIX}-000001",
                course_id=f"{COURSE_ID_PREFIX}-000001",
            )
        )

        self.assert_error(result, "StudentRepositoryError", f"{STUDENT_ID_PREFIX}-000001")

    def _dispatcher(
        self,
        service_type: type[StudentService] = StudentService,
    ) -> ApplicationCommandDispatcher:
        student_repository = SQLiteStudentRepository(
            self.database,
            as_of=date(2026, 7, 13),
        )
        group_ids = tuple(group.group_id for group in SQLiteGroupRepository(self.database).list_groups())
        course_ids = tuple(course.course_id for course in SQLiteCourseRepository(self.database).list_courses())
        service = service_type(
            student_repository,
            StudentValidator(),
            group_ids,
            course_ids,
            now_provider=FixedClock(),
        )
        dispatcher = ApplicationCommandDispatcher()
        dispatcher.register("student.create", student_create_handler(service))
        return dispatcher

    def assert_error(self, result: object, error_type: str, message_part: str) -> None:
        self.assertIsInstance(result, ErrorResult)
        self.assertFalse(result.success)
        self.assertEqual(result.command_name, "student.create")
        self.assertEqual(result.error_type, error_type)
        self.assertIn(message_part, result.message)


if __name__ == "__main__":
    unittest.main()
