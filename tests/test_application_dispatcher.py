"""Tests for the application command dispatcher spike."""

from __future__ import annotations

import unittest

from src.application.commands import CreateStudentCommand
from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    ErrorResult,
    SuccessResult,
    student_create_handler,
)


class FakeStudentService:
    """Capture student service calls for dispatcher tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def create_student(
        self,
        first_name: str,
        last_name: str,
        group_id: str,
        course_id: str,
        student_notes: str = "",
    ) -> dict[str, str]:
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "group_id": group_id,
            "course_id": course_id,
            "student_notes": student_notes,
        }
        self.calls.append(payload)
        return payload


class ApplicationCommandDispatcherTest(unittest.TestCase):
    def test_dispatches_student_create_to_registered_service_handler(self) -> None:
        service = FakeStudentService()
        dispatcher = ApplicationCommandDispatcher()
        dispatcher.register("student.create", student_create_handler(service))

        result = dispatcher.dispatch(
            CreateStudentCommand(
                first_name="Jule",
                last_name="Schneider",
                group_id="GRP-000001",
                course_id="CRS-000001",
                student_notes="Liest gern.",
            )
        )

        self.assertIsInstance(result, SuccessResult)
        self.assertEqual(result.value["first_name"], "Jule")
        self.assertEqual(service.calls[0]["last_name"], "Schneider")
        self.assertEqual(dispatcher.registered_commands(), ("student.create",))

    def test_rejects_unknown_command(self) -> None:
        dispatcher = ApplicationCommandDispatcher()

        result = dispatcher.dispatch(
            CreateStudentCommand(
                first_name="Jule",
                last_name="Schneider",
                group_id="GRP-000001",
                course_id="CRS-000001",
            )
        )

        self.assertIsInstance(result, ErrorResult)
        self.assertFalse(result.success)
        self.assertEqual(result.command_name, "student.create")


if __name__ == "__main__":
    unittest.main()
