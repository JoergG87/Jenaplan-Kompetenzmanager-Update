"""Student view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudentListItem:
    """Display-ready student row for desktop lists."""

    student_id: str
    first_name: str
    last_name: str
    group_id: str
    group_name: str
    course_id: str
    course_name: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass(frozen=True)
class StudentDetailViewModel:
    """Display model for the light student profile."""

    student_id: str
    display_name: str
    group_name: str
    course_name: str
    student_notes: str
    active: bool


@dataclass(frozen=True)
class GroupSummaryViewModel:
    """Display model for overview group cards."""

    group_id: str
    group_name: str
    active_student_count: int
