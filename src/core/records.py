"""Core records used by the PySide and SQLite application path."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    COURSE_ID_PREFIX,
    GROUP_ID_PREFIX,
    STUDENT_ID_PREFIX,
)


DEFAULT_GROUP_ID = f"{GROUP_ID_PREFIX}-000001"
DEFAULT_STUDENT_ID = f"{STUDENT_ID_PREFIX}-000001"
SCHOOL_YEAR = "2025/26"
SEED_TIMESTAMP = "2026-06-28"


@dataclass(frozen=True)
class StudentRecord:
    """Student entity stored in SQLite."""

    student_id: str
    first_name: str
    last_name: str
    group_id: str
    course_id: str
    student_notes: str
    active: bool
    created_at: str
    updated_at: str
    archived_at: str | None


@dataclass(frozen=True)
class GroupRecord:
    """Student group entity stored in SQLite."""

    group_id: str
    group_name: str
    active: bool


@dataclass(frozen=True)
class CourseRecord:
    """Course entity stored in SQLite."""

    course_id: str
    course_name: str
    color_key: str
    active: bool


@dataclass(frozen=True)
class ReferenceData:
    """Deterministic test/reference records for explicit seed paths."""

    students: tuple[StudentRecord, ...]
    groups: tuple[GroupRecord, ...]
    courses: tuple[CourseRecord, ...]
    default_group_id: str = DEFAULT_GROUP_ID
    default_student_id: str = DEFAULT_STUDENT_ID
    school_year: str = SCHOOL_YEAR


def seed_reference_data() -> ReferenceData:
    """Return deterministic test/reference data for explicit seed paths."""
    return ReferenceData(
        students=_student_records(),
        groups=(
            GroupRecord(DEFAULT_GROUP_ID, "Grashüpfer", True),
        ),
        courses=(
            CourseRecord(f"{COURSE_ID_PREFIX}-000001", "Kurs 1", "DDEDE6", True),
            CourseRecord(f"{COURSE_ID_PREFIX}-000002", "Kurs 2", "E8F0F8", True),
            CourseRecord(f"{COURSE_ID_PREFIX}-000003", "Kurs 3", "E9E4F0", True),
        ),
    )


def _student_records() -> tuple[StudentRecord, ...]:
    raw_students = (
        ("Mia", "Becker"),
        ("Emma", "Müller"),
        ("Leon", "Schmidt"),
        ("Paul", "Wagner"),
        ("Anna", "Fischer"),
        ("Ben", "Schneider"),
        ("Lina", "Hoffmann"),
        ("Noah", "Weber"),
        ("Sophia", "Koch"),
        ("Finn", "Bauer"),
        ("Leni", "Richter"),
        ("Jonas", "Klein"),
        ("Clara", "Wolf"),
        ("Luis", "Schröder"),
        ("Marie", "Neumann"),
        ("Ole", "Schwarz"),
        ("Ella", "Braun"),
        ("Tom", "Hartmann"),
        ("Frida", "Krüger"),
        ("Henri", "Lang"),
        ("Mara", "Schmitt"),
        ("Mats", "Werner"),
        ("Lea", "Scholz"),
        ("Theo", "Jung"),
        ("Amelie", "Vogel"),
        ("Anton", "Krause"),
        ("Ida", "Mayer"),
        ("Oskar", "Lehmann"),
    )
    records = []
    for student_number, (first_name, last_name) in enumerate(raw_students, start=1):
        student_id = f"{STUDENT_ID_PREFIX}-{student_number:06}"
        course_id = f"{COURSE_ID_PREFIX}-{((student_number - 1) % 3) + 1:06}"
        records.append(
            StudentRecord(
                student_id,
                first_name,
                last_name,
                DEFAULT_GROUP_ID,
                course_id,
                "",
                True,
                SEED_TIMESTAMP,
                SEED_TIMESTAMP,
                None,
            )
        )
    return tuple(sorted(records, key=lambda student: student.first_name.casefold()))
