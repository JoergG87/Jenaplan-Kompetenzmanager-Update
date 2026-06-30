"""Student commands for the application layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateStudentCommand:
    """Command DTO for creating a student through the application layer."""

    first_name: str
    last_name: str
    group_id: str
    course_id: str
    student_notes: str = ""

    command_name: str = "student.create"

