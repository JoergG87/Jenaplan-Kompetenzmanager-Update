"""Tests for the Student reference entity implementation."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.core.constants import (
    COURSE_ID,
    COURSE_ID_PREFIX,
    FIRST_NAME,
    GROUP_ID,
    GROUP_ID_PREFIX,
    LAST_NAME,
    STUDENT_ID_PREFIX,
    STUDENT_NOTES,
)
from src.core.records import StudentRecord
from src.core.student import StudentRepository, StudentService, StudentValidator


class FixedClock:
    """Return deterministic timestamps for service tests."""

    def __init__(self) -> None:
        self.timestamps = (
            datetime(2026, 6, 28, 10, 0, tzinfo=UTC),
            datetime(2026, 6, 28, 11, 0, tzinfo=UTC),
            datetime(2026, 6, 28, 12, 0, tzinfo=UTC),
        )
        self.index = 0

    def __call__(self) -> datetime:
        timestamp = self.timestamps[self.index]
        self.index = min(self.index + 1, len(self.timestamps) - 1)
        return timestamp


class StudentEntityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = StudentRepository(())
        self.clock = FixedClock()
        self.service = StudentService(
            self.repository,
            StudentValidator(),
            (f"{GROUP_ID_PREFIX}-000001",),
            (f"{COURSE_ID_PREFIX}-000001", f"{COURSE_ID_PREFIX}-000002"),
            now_provider=self.clock,
        )

    def test_create_student_creates_complete_record(self) -> None:
        student = self.service.create_student(
            "Jule",
            "Schneider",
            f"{GROUP_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000001",
            "Liest gern.",
        )

        self.assertEqual(student.student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(student.first_name, "Jule")
        self.assertEqual(student.last_name, "Schneider")
        self.assertEqual(student.student_notes, "Liest gern.")
        self.assertTrue(student.active)
        self.assertEqual(student.created_at, "2026-06-28T10:00:00+00:00")
        self.assertEqual(student.updated_at, "2026-06-28T10:00:00+00:00")
        self.assertIsNone(student.archived_at)
        self.assertEqual(self.repository.get_student_by_id(student.student_id), student)

    def test_id_collision_uses_next_free_student_id(self) -> None:
        self.repository.create_student(
            StudentRecord(
                f"{STUDENT_ID_PREFIX}-000001",
                "Mia",
                "Becker",
                f"{GROUP_ID_PREFIX}-000001",
                f"{COURSE_ID_PREFIX}-000001",
                "",
                True,
                "2026-06-28T09:00:00+00:00",
                "2026-06-28T09:00:00+00:00",
                None,
            )
        )

        student = self.service.create_student(
            "Jule",
            "Schneider",
            f"{GROUP_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000001",
        )

        self.assertEqual(student.student_id, f"{STUDENT_ID_PREFIX}-000002")

    def test_update_student_keeps_id_and_created_at(self) -> None:
        student = self.service.create_student(
            "Jule",
            "Schneider",
            f"{GROUP_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000001",
        )

        updated_student = self.service.update_student(
            student.student_id,
            "Julia",
            "Schneider",
            f"{GROUP_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000002",
            "Neuer Hinweis.",
        )

        self.assertEqual(updated_student.student_id, student.student_id)
        self.assertEqual(updated_student.created_at, student.created_at)
        self.assertEqual(updated_student.first_name, "Julia")
        self.assertEqual(updated_student.course_id, f"{COURSE_ID_PREFIX}-000002")
        self.assertEqual(updated_student.student_notes, "Neuer Hinweis.")
        self.assertEqual(updated_student.updated_at, "2026-06-28T11:00:00+00:00")

    def test_archive_student_keeps_history_and_deactivates_student(self) -> None:
        student = self.service.create_student(
            "Jule",
            "Schneider",
            f"{GROUP_ID_PREFIX}-000001",
            f"{COURSE_ID_PREFIX}-000001",
        )

        archived_student = self.service.archive_student(student.student_id)

        self.assertEqual(archived_student.student_id, student.student_id)
        self.assertEqual(archived_student.created_at, student.created_at)
        self.assertFalse(archived_student.active)
        self.assertEqual(archived_student.archived_at, "2026-06-28T11:00:00+00:00")
        self.assertEqual(self.repository.get_student_by_id(student.student_id), archived_student)

if __name__ == "__main__":
    unittest.main()
