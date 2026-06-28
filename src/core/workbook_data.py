"""Workbook data sources for the Jenaplan UX prototype."""

from __future__ import annotations

from dataclasses import dataclass

from openpyxl.utils import get_column_letter
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from .constants import (
    ACTIVE,
    ARCHIVED_AT,
    COLOR_KEY,
    COURSE_ID,
    COURSE_ID_PREFIX,
    COURSE_NAME,
    CREATED_AT,
    FIRST_NAME,
    GROUP_ID,
    GROUP_ID_PREFIX,
    GROUP_NAME,
    LAST_NAME,
    SHEET_DATA_COURSES,
    SHEET_DATA_GROUPS,
    SHEET_DATA_STUDENTS,
    STUDENT_ID,
    STUDENT_ID_PREFIX,
    STUDENT_NOTES,
    TABLE_COURSES,
    TABLE_GROUPS,
    TABLE_STUDENTS,
    UPDATED_AT,
)


DEFAULT_GROUP_ID = f"{GROUP_ID_PREFIX}-000001"
DEFAULT_STUDENT_ID = f"{STUDENT_ID_PREFIX}-000001"
SCHOOL_YEAR = "2025/26"
SEED_TIMESTAMP = "2026-06-28"


@dataclass(frozen=True)
class StudentRecord:
    """Student entity stored in the workbook data layer."""

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
    """Group entity stored in the workbook data layer."""

    group_id: str
    group_name: str
    active: bool


@dataclass(frozen=True)
class CourseRecord:
    """Course entity stored in the workbook data layer."""

    course_id: str
    course_name: str
    color_key: str
    active: bool


@dataclass(frozen=True)
class WorkbookData:
    """Registered workbook data sources used by UI builders."""

    students: tuple[StudentRecord, ...]
    groups: tuple[GroupRecord, ...]
    courses: tuple[CourseRecord, ...]
    default_group_id: str = DEFAULT_GROUP_ID
    default_student_id: str = DEFAULT_STUDENT_ID
    school_year: str = SCHOOL_YEAR


def seed_workbook_data() -> WorkbookData:
    """Return the seed data for Sprint 4.1 architecture validation."""
    return WorkbookData(
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


class WorkbookDataBuilder:
    """Create hidden workbook data sheets and structured tables."""

    def __init__(self, workbook: Workbook, data: WorkbookData) -> None:
        self.workbook = workbook
        self.data = data

    def build(self) -> None:
        """Create all registered Phase 1 workbook data sources."""
        self._create_table(
            SHEET_DATA_STUDENTS,
            TABLE_STUDENTS,
            (
                STUDENT_ID,
                FIRST_NAME,
                LAST_NAME,
                GROUP_ID,
                COURSE_ID,
                STUDENT_NOTES,
                ACTIVE,
                CREATED_AT,
                UPDATED_AT,
                ARCHIVED_AT,
            ),
            (
                (
                    student.student_id,
                    student.first_name,
                    student.last_name,
                    student.group_id,
                    student.course_id,
                    student.student_notes,
                    student.active,
                    student.created_at,
                    student.updated_at,
                    student.archived_at,
                )
                for student in self.data.students
            ),
        )
        self._create_table(
            SHEET_DATA_GROUPS,
            TABLE_GROUPS,
            (GROUP_ID, GROUP_NAME, ACTIVE),
            (
                (group.group_id, group.group_name, group.active)
                for group in self.data.groups
            ),
        )
        self._create_table(
            SHEET_DATA_COURSES,
            TABLE_COURSES,
            (COURSE_ID, COURSE_NAME, COLOR_KEY, ACTIVE),
            (
                (course.course_id, course.course_name, course.color_key, course.active)
                for course in self.data.courses
            ),
        )

    def _create_table(
        self,
        sheet_name: str,
        table_name: str,
        headers: tuple[str, ...],
        rows: object,
    ) -> None:
        worksheet = self.workbook.create_sheet(sheet_name)
        worksheet.sheet_state = "hidden"
        worksheet.append(headers)
        for row in rows:
            worksheet.append(row)

        table_ref = f"A1:{get_column_letter(len(headers))}{worksheet.max_row}"
        table = Table(displayName=table_name, ref=table_ref)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        worksheet.add_table(table)

        for column_index, header in enumerate(headers, start=1):
            worksheet.column_dimensions[get_column_letter(column_index)].width = max(
                12,
                len(header) + 2,
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
