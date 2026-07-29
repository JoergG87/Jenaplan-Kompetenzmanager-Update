"""Core records used by the PySide and SQLite application path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from .constants import (
    COURSE_ID_PREFIX,
    GROUP_ID_PREFIX,
    STUDENT_ID_PREFIX,
)
from .school_year import (
    SchoolYear,
    SchoolYearStatus,
    StudentAssignmentStatus,
    StudentMembershipAssignment,
    V3Student,
)


DEFAULT_GROUP_ID = f"{GROUP_ID_PREFIX}-000001"
DEFAULT_STUDENT_ID = f"{STUDENT_ID_PREFIX}-000001"
SCHOOL_YEAR_ID = "SY-TEST-2025-26"
SCHOOL_YEAR = "2025/26"
SCHOOL_YEAR_START = date(2025, 8, 1)
SCHOOL_YEAR_END = date(2026, 7, 31)
SEED_TIMESTAMP = "2025-07-01T08:00:00+00:00"


@dataclass(frozen=True)
class StudentRecord:
    """Read projection combining V3 student data and resolved membership."""

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
    year_level: int


@dataclass(frozen=True)
class ReferenceData:
    """Deterministic test/reference records for explicit seed paths."""

    students: tuple[V3Student, ...]
    groups: tuple[GroupRecord, ...]
    courses: tuple[CourseRecord, ...]
    school_year: SchoolYear
    assignments: tuple[tuple[str, StudentMembershipAssignment], ...]
    default_group_id: str = DEFAULT_GROUP_ID
    default_student_id: str = DEFAULT_STUDENT_ID


def seed_reference_data() -> ReferenceData:
    """Return deterministic test/reference data for explicit seed paths."""
    students = _student_records()
    return ReferenceData(
        students=students,
        groups=(
            GroupRecord(DEFAULT_GROUP_ID, "Grashüpfer", True),
        ),
        courses=(
            CourseRecord(
                f"{COURSE_ID_PREFIX}-000001",
                "Kurs 1",
                "DDEDE6",
                True,
                1,
            ),
            CourseRecord(
                f"{COURSE_ID_PREFIX}-000002",
                "Kurs 2",
                "E8F0F8",
                True,
                2,
            ),
            CourseRecord(
                f"{COURSE_ID_PREFIX}-000003",
                "Kurs 3",
                "E9E4F0",
                True,
                3,
            ),
        ),
        school_year=SchoolYear(
            SCHOOL_YEAR_ID,
            SCHOOL_YEAR,
            SCHOOL_YEAR_START,
            SCHOOL_YEAR_END,
            SchoolYearStatus.CURRENT,
        ),
        assignments=_assignment_records(students),
    )


def _student_records() -> tuple[V3Student, ...]:
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
    timestamp = datetime.fromisoformat(SEED_TIMESTAMP).astimezone(UTC)
    records: list[V3Student] = []
    for student_number, (first_name, last_name) in enumerate(raw_students, start=1):
        student_id = f"{STUDENT_ID_PREFIX}-{student_number:06}"
        records.append(
            V3Student(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                notes="",
                active=True,
                created_at=timestamp,
                updated_at=timestamp,
                archived_at=None,
            )
        )
    return tuple(sorted(records, key=lambda student: student.first_name.casefold()))


def _assignment_records(
    students: tuple[V3Student, ...],
) -> tuple[tuple[str, StudentMembershipAssignment], ...]:
    return tuple(
        (
            f"ASG-TEST-{assignment_number:06}",
            StudentMembershipAssignment(
                student_id=student.student_id,
                school_year_id=SCHOOL_YEAR_ID,
                group_id=DEFAULT_GROUP_ID,
                course_id=(
                    f"{COURSE_ID_PREFIX}-"
                    f"{((assignment_number - 1) % 3) + 1:06}"
                ),
                assignment_status=StudentAssignmentStatus.ENROLLED,
                valid_from=SCHOOL_YEAR_START,
                valid_to=SCHOOL_YEAR_END,
            ),
        )
        for assignment_number, student in enumerate(students, start=1)
    )
