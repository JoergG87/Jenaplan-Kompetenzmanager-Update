"""Tests for the productive runtime adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import km
from src.core.sqlite_store import SQLiteDatabase, SQLiteStudentRepository


class RuntimeAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.database_path = self.work_dir / "kompetenzmanager.sqlite"
        self.command_path = self.work_dir / "runtime_command.json"
        self.result_path = self.work_dir / "runtime_result.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_student_create_runtime_writes_sqlite_and_result_file(self) -> None:
        self._write_command(
            {
                "first_name": "Jule",
                "last_name": "Schneider",
                "group": "Grashüpfer",
                "course": "Kurs 1",
                "student_notes": "Liest gern.",
            }
        )

        exit_code = km.main(self._runtime_args())

        self.assertEqual(exit_code, 0)
        result = self._read_result()
        self.assertTrue(result["success"])
        self.assertEqual(result["command_name"], "student.create")
        self.assertEqual(result["student_id"], "STU-000029")

        repository = SQLiteStudentRepository(SQLiteDatabase(self.database_path))
        stored_student = repository.get_student_by_id("STU-000029")
        self.assertIsNotNone(stored_student)
        self.assertEqual(stored_student.first_name, "Jule")
        self.assertEqual(stored_student.group_id, "GRP-000001")
        self.assertEqual(stored_student.course_id, "CRS-000001")
        self.assertEqual(len(repository.list_students()), 29)

    def test_student_create_runtime_returns_error_without_partial_write(self) -> None:
        self._write_command(
            {
                "first_name": "",
                "last_name": "Schneider",
                "group": "GRP-000001",
                "course": "CRS-000001",
                "student_notes": "",
            }
        )

        exit_code = km.main(self._runtime_args())

        self.assertEqual(exit_code, 1)
        result = self._read_result()
        self.assertFalse(result["success"])
        self.assertEqual(result["command_name"], "student.create")
        self.assertEqual(result["error_type"], "StudentValidationError")
        self.assertIn("first_name", result["message"])

        repository = SQLiteStudentRepository(SQLiteDatabase(self.database_path))
        self.assertEqual(len(repository.list_students()), 28)

    def test_student_create_runtime_reads_mac_encoded_command_file(self) -> None:
        command = {
            "command": "student.create",
            "data": {
                "first_name": "Jörg",
                "last_name": "Müller",
                "group": "Grashüpfer",
                "course": "Kurs 1",
                "student_notes": "Förderhinweis",
            },
        }
        self.command_path.write_bytes(
            json.dumps(command, ensure_ascii=False).encode("mac_roman")
        )

        exit_code = km.main(self._runtime_args())

        self.assertEqual(exit_code, 0)
        repository = SQLiteStudentRepository(SQLiteDatabase(self.database_path))
        stored_student = repository.get_student_by_id("STU-000029")
        self.assertIsNotNone(stored_student)
        self.assertEqual(stored_student.first_name, "Jörg")
        self.assertEqual(stored_student.last_name, "Müller")

    def _runtime_args(self) -> list[str]:
        return [
            "--database",
            str(self.database_path),
            "--result-file",
            str(self.result_path),
            "student",
            "create",
            "--command-file",
            str(self.command_path),
        ]

    def _write_command(self, data: dict[str, str]) -> None:
        self.command_path.write_text(
            json.dumps(
                {
                    "command": "student.create",
                    "data": data,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _read_result(self) -> dict[str, object]:
        return json.loads(self.result_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
