"""SQLite repositories for the isolated final-V3 assignment API.

Repositories in this module never open, commit, or roll back a transaction.
The caller owns the supplied connection and therefore the read snapshot or
write unit of work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import sqlite3
from typing import Iterable, Mapping, Sequence

from .school_year import (
    SchoolYear,
    SchoolYearStatus,
    StudentAssignmentStatus,
    StudentMembershipAssignment,
    V3Student,
)


class SchoolYearAssignmentRepositoryError(RuntimeError):
    """Fail closed when assignment persistence is missing or inconsistent."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class AssignmentSource:
    """Joined, display-independent source row for one assignment candidate."""

    student_id: str
    student_active: bool
    student_archived_at: datetime | None
    assignment_id: str | None
    school_year_id: str | None
    school_year_label: str | None
    assignment_status: StudentAssignmentStatus | None
    valid_from: date | None
    valid_to: date | None
    group_id: str | None
    group_name: str | None
    course_id: str | None
    course_name: str | None
    year_level: int | None


@dataclass(frozen=True, slots=True)
class StoredStudentSchoolYearAssignment:
    """Persisted assignment identity plus its validated domain interval."""

    assignment_id: str
    membership: StudentMembershipAssignment
    created_at: datetime
    updated_at: datetime


class SchoolYearRepository:
    """Read school-year truth through an explicitly supplied connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(self, school_year_id: str) -> SchoolYear | None:
        row = self.connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years
            WHERE school_year_id = ?
            """,
            (school_year_id,),
        ).fetchone()
        return _school_year_from_row(row) if row is not None else None

    def get_current(self) -> SchoolYear | None:
        rows = self.connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years
            WHERE status = 'current'
            ORDER BY school_year_id
            LIMIT 2
            """
        ).fetchall()
        if len(rows) > 1:
            raise SchoolYearAssignmentRepositoryError(
                "current_school_year_ambiguous"
            )
        return _school_year_from_row(rows[0]) if rows else None

    def list_all(self) -> tuple[SchoolYear, ...]:
        rows = self.connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years
            ORDER BY start_date, school_year_id
            """
        ).fetchall()
        return tuple(_school_year_from_row(row) for row in rows)

    def require_current(self) -> SchoolYear:
        current = self.get_current()
        if current is None:
            raise SchoolYearAssignmentRepositoryError(
                "current_school_year_missing"
            )
        return current


class StudentSchoolYearAssignmentRepository:
    """Read and write V3 assignments without owning transaction boundaries."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(
        self,
        assignment_id: str,
    ) -> StoredStudentSchoolYearAssignment | None:
        row = self.connection.execute(
            """
            SELECT
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            FROM student_school_year_assignments
            WHERE assignment_id = ?
            """,
            (assignment_id,),
        ).fetchone()
        return _stored_assignment_from_row(row) if row is not None else None

    def get_assignment_at_date(
        self,
        student_id: str,
        reference_date: date,
        *,
        school_year_id: str | None = None,
    ) -> tuple[AssignmentSource, ...]:
        return self.list_assignments_at_dates(
            ((student_id, reference_date),),
            school_year_id=school_year_id,
        )[student_id]

    def list_assignments_at_dates(
        self,
        student_dates: Mapping[str, date] | Sequence[tuple[str, date]],
        *,
        school_year_id: str | None = None,
    ) -> dict[str, tuple[AssignmentSource, ...]]:
        pairs = tuple(
            student_dates.items()
            if isinstance(student_dates, Mapping)
            else student_dates
        )
        if not pairs:
            return {}
        if len({student_id for student_id, _ in pairs}) != len(pairs):
            raise SchoolYearAssignmentRepositoryError(
                "assignment_batch_student_duplicate"
            )
        values_sql = ", ".join("(?, ?)" for _ in pairs)
        parameters: list[object] = []
        for student_id, reference_date in pairs:
            parameters.extend((student_id, reference_date.isoformat()))
        school_year_sql = ""
        if school_year_id is not None:
            school_year_sql = "AND assignment.school_year_id = ?"
            parameters.append(school_year_id)
        rows = self.connection.execute(
            f"""
            WITH requested(student_id, reference_date) AS (
                VALUES {values_sql}
            )
            SELECT
                requested.student_id AS requested_student_id,
                student.active AS student_active,
                student.archived_at AS student_archived_at,
                assignment.assignment_id,
                assignment.school_year_id,
                school_year.label AS school_year_label,
                assignment.assignment_status,
                assignment.valid_from,
                assignment.valid_to,
                assignment.group_id,
                student_group.group_name,
                assignment.course_id,
                course.course_name,
                course.year_level
            FROM requested
            LEFT JOIN students AS student
                ON student.student_id = requested.student_id
            LEFT JOIN student_school_year_assignments AS assignment
                ON assignment.student_id = requested.student_id
               AND assignment.valid_from <= requested.reference_date
               AND assignment.valid_to >= requested.reference_date
               {school_year_sql}
            LEFT JOIN school_years AS school_year
                ON school_year.school_year_id = assignment.school_year_id
            LEFT JOIN groups AS student_group
                ON student_group.group_id = assignment.group_id
            LEFT JOIN courses AS course
                ON course.course_id = assignment.course_id
            ORDER BY
                requested.student_id,
                assignment.valid_from,
                assignment.assignment_id
            """,
            tuple(parameters),
        ).fetchall()
        grouped: dict[str, list[AssignmentSource]] = {
            student_id: [] for student_id, _ in pairs
        }
        for row in rows:
            source = _assignment_source_from_row(row)
            if source.assignment_id is not None:
                grouped[source.student_id].append(source)
            elif not grouped[source.student_id]:
                grouped[source.student_id].append(source)
        return {
            student_id: tuple(candidates)
            for student_id, candidates in grouped.items()
        }

    def list_for_student(
        self,
        student_id: str,
    ) -> tuple[StoredStudentSchoolYearAssignment, ...]:
        rows = self.connection.execute(
            """
            SELECT
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            FROM student_school_year_assignments
            WHERE student_id = ?
            ORDER BY valid_from, valid_to, assignment_id
            """,
            (student_id,),
        ).fetchall()
        return tuple(_stored_assignment_from_row(row) for row in rows)

    def list_current_memberships(
        self,
        school_year_id: str,
        as_of: date,
        *,
        student_ids: Sequence[str] | None = None,
        group_id: str | None = None,
        course_id: str | None = None,
        course_group_id: str | None = None,
    ) -> tuple[AssignmentSource, ...]:
        parameters: list[object] = [
            school_year_id,
            as_of.isoformat(),
            as_of.isoformat(),
        ]
        student_filters: list[str] = []
        if student_ids is not None:
            identifiers = tuple(dict.fromkeys(student_ids))
            if not identifiers:
                return ()
            placeholders = ", ".join("?" for _ in identifiers)
            student_filters.append(f"student.student_id IN ({placeholders})")
            parameters.extend(identifiers)
        else:
            student_filters.extend(
                ("student.active = 1", "student.archived_at IS NULL")
            )

        scope_filters = [
            "scoped_assignment.student_id = student.student_id",
            "scoped_assignment.school_year_id = ?",
            "scoped_assignment.assignment_status = 'enrolled'",
            "scoped_assignment.valid_from <= ?",
            "scoped_assignment.valid_to >= ?",
        ]
        scope_parameters: list[object] = [
            school_year_id,
            as_of.isoformat(),
            as_of.isoformat(),
        ]
        if group_id is not None:
            scope_filters.append("scoped_assignment.group_id = ?")
            scope_parameters.append(group_id)
        if course_id is not None:
            scope_filters.append("scoped_assignment.course_id = ?")
            scope_parameters.append(course_id)
        if course_group_id is not None:
            scope_filters.append(
                """
                (
                    EXISTS (
                        SELECT 1
                        FROM course_group_student_groups AS group_link
                        WHERE group_link.course_group_id = ?
                          AND group_link.student_group_id =
                              scoped_assignment.group_id
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM course_group_courses AS course_link
                        WHERE course_link.course_group_id = ?
                          AND course_link.course_id =
                              scoped_assignment.course_id
                    )
                )
                """
            )
            scope_parameters.extend((course_group_id, course_group_id))
        if group_id is not None or course_id is not None or course_group_id is not None:
            student_filters.append(
                "EXISTS ("
                "SELECT 1 FROM student_school_year_assignments "
                "AS scoped_assignment WHERE "
                + " AND ".join(scope_filters)
                + ")"
            )
            parameters.extend(scope_parameters)
        elif student_ids is None:
            student_filters.append("assignment.assignment_id IS NOT NULL")
        student_filter_sql = "WHERE " + " AND ".join(student_filters)

        rows = self.connection.execute(
            f"""
            SELECT
                student.student_id AS requested_student_id,
                student.active AS student_active,
                student.archived_at AS student_archived_at,
                assignment.assignment_id,
                assignment.school_year_id,
                school_year.label AS school_year_label,
                assignment.assignment_status,
                assignment.valid_from,
                assignment.valid_to,
                assignment.group_id,
                student_group.group_name,
                assignment.course_id,
                course.course_name,
                course.year_level
            FROM students AS student
            LEFT JOIN student_school_year_assignments AS assignment
                ON assignment.student_id = student.student_id
               AND assignment.school_year_id = ?
               AND assignment.valid_from <= ?
               AND assignment.valid_to >= ?
            LEFT JOIN school_years AS school_year
                ON school_year.school_year_id = assignment.school_year_id
            LEFT JOIN groups AS student_group
                ON student_group.group_id = assignment.group_id
            LEFT JOIN courses AS course
                ON course.course_id = assignment.course_id
            {student_filter_sql}
            ORDER BY
                lower(student.last_name),
                lower(student.first_name),
                student.student_id,
                assignment.assignment_id
            """,
            tuple(parameters),
        ).fetchall()
        return tuple(_assignment_source_from_row(row) for row in rows)

    def count_current_by_group(
        self,
        school_year_id: str,
        as_of: date,
    ) -> dict[str, int]:
        return self._count_current("group_id", school_year_id, as_of)

    def count_current_by_course(
        self,
        school_year_id: str,
        as_of: date,
    ) -> dict[str, int]:
        return self._count_current("course_id", school_year_id, as_of)

    def get_last_known(
        self,
        student_id: str,
        reference_date: date,
    ) -> tuple[AssignmentSource, ...]:
        rows = self.connection.execute(
            """
            WITH last_date AS (
                SELECT max(valid_to) AS valid_to
                FROM student_school_year_assignments
                WHERE student_id = ?
                  AND valid_from <= ?
            )
            SELECT
                student.student_id AS requested_student_id,
                student.active AS student_active,
                student.archived_at AS student_archived_at,
                assignment.assignment_id,
                assignment.school_year_id,
                school_year.label AS school_year_label,
                assignment.assignment_status,
                assignment.valid_from,
                assignment.valid_to,
                assignment.group_id,
                student_group.group_name,
                assignment.course_id,
                course.course_name,
                course.year_level
            FROM students AS student
            LEFT JOIN student_school_year_assignments AS assignment
                ON assignment.student_id = student.student_id
               AND assignment.valid_to = (SELECT valid_to FROM last_date)
               AND assignment.valid_from <= ?
            LEFT JOIN school_years AS school_year
                ON school_year.school_year_id = assignment.school_year_id
            LEFT JOIN groups AS student_group
                ON student_group.group_id = assignment.group_id
            LEFT JOIN courses AS course
                ON course.course_id = assignment.course_id
            WHERE student.student_id = ?
            ORDER BY assignment.valid_from, assignment.assignment_id
            """,
            (
                student_id,
                reference_date.isoformat(),
                reference_date.isoformat(),
                student_id,
            ),
        ).fetchall()
        return tuple(_assignment_source_from_row(row) for row in rows)

    def insert(
        self,
        assignment_id: str,
        assignment: StudentMembershipAssignment,
        timestamp: datetime,
    ) -> StoredStudentSchoolYearAssignment:
        value = timestamp.isoformat()
        self.connection.execute(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assignment_id,
                assignment.student_id,
                assignment.school_year_id,
                assignment.group_id,
                assignment.course_id,
                assignment.assignment_status.value,
                assignment.valid_from.isoformat(),
                assignment.valid_to.isoformat(),
                value,
                value,
            ),
        )
        stored = self.get_by_id(assignment_id)
        if stored is None:
            raise SchoolYearAssignmentRepositoryError(
                "assignment_insert_not_visible"
            )
        return stored

    def shorten(
        self,
        assignment_id: str,
        valid_to: date,
        timestamp: datetime,
    ) -> None:
        cursor = self.connection.execute(
            """
            UPDATE student_school_year_assignments
            SET valid_to = ?, updated_at = ?
            WHERE assignment_id = ?
            """,
            (valid_to.isoformat(), timestamp.isoformat(), assignment_id),
        )
        if cursor.rowcount != 1:
            raise SchoolYearAssignmentRepositoryError(
                "assignment_update_missing"
            )

    def has_overlap(
        self,
        student_id: str,
        valid_from: date,
        valid_to: date,
    ) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM student_school_year_assignments
            WHERE student_id = ?
              AND NOT (valid_to < ? OR valid_from > ?)
            LIMIT 1
            """,
            (student_id, valid_from.isoformat(), valid_to.isoformat()),
        ).fetchone()
        return row is not None

    def has_active_enrollment(self, student_id: str, as_of: date) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM student_school_year_assignments
            WHERE student_id = ?
              AND assignment_status = 'enrolled'
              AND valid_from <= ?
              AND valid_to >= ?
            LIMIT 1
            """,
            (student_id, as_of.isoformat(), as_of.isoformat()),
        ).fetchone()
        return row is not None

    def _count_current(
        self,
        column: str,
        school_year_id: str,
        as_of: date,
    ) -> dict[str, int]:
        if column not in {"group_id", "course_id"}:
            raise AssertionError("unsupported assignment count column")
        rows = self.connection.execute(
            f"""
            WITH candidates AS (
                SELECT
                    assignment.student_id,
                    assignment.{column} AS membership_id,
                    assignment.assignment_status
                FROM student_school_year_assignments AS assignment
                JOIN students AS student
                    ON student.student_id = assignment.student_id
                WHERE assignment.school_year_id = ?
                  AND assignment.valid_from <= ?
                  AND assignment.valid_to >= ?
                  AND student.active = 1
                  AND student.archived_at IS NULL
            ),
            unique_enrolled AS (
                SELECT student_id, max(membership_id) AS membership_id
                FROM candidates
                GROUP BY student_id
                HAVING count(*) = 1
                   AND max(assignment_status) = 'enrolled'
            )
            SELECT membership_id, count(*) AS member_count
            FROM unique_enrolled
            WHERE membership_id IS NOT NULL
            GROUP BY membership_id
            ORDER BY membership_id
            """,
            (
                school_year_id,
                as_of.isoformat(),
                as_of.isoformat(),
            ),
        ).fetchall()
        return {
            str(row["membership_id"]): int(row["member_count"])
            for row in rows
        }


class V3StudentRepository:
    """Persist only V3 student master data, never membership fields."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(self, student_id: str) -> V3Student | None:
        row = self.connection.execute(
            """
            SELECT
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            FROM students
            WHERE student_id = ?
            """,
            (student_id,),
        ).fetchone()
        return _v3_student_from_row(row) if row is not None else None

    def list_by_ids(
        self,
        student_ids: Sequence[str],
    ) -> dict[str, V3Student]:
        identifiers = tuple(dict.fromkeys(student_ids))
        if not identifiers:
            return {}
        placeholders = ", ".join("?" for _ in identifiers)
        rows = self.connection.execute(
            f"""
            SELECT
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            FROM students
            WHERE student_id IN ({placeholders})
            """,
            identifiers,
        ).fetchall()
        return {
            student.student_id: student
            for student in (_v3_student_from_row(row) for row in rows)
        }

    def create(self, student: V3Student) -> V3Student:
        self.connection.execute(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student.student_id,
                student.first_name,
                student.last_name,
                student.notes,
                int(student.active),
                student.created_at.isoformat(),
                student.updated_at.isoformat(),
                (
                    student.archived_at.isoformat()
                    if student.archived_at is not None
                    else None
                ),
            ),
        )
        return student

    def update_master_data(
        self,
        student_id: str,
        first_name: str,
        last_name: str,
        notes: str,
        updated_at: datetime,
    ) -> V3Student:
        cursor = self.connection.execute(
            """
            UPDATE students
            SET first_name = ?, last_name = ?, notes = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (
                first_name,
                last_name,
                notes,
                updated_at.isoformat(),
                student_id,
            ),
        )
        if cursor.rowcount != 1:
            raise SchoolYearAssignmentRepositoryError("student_missing")
        updated = self.get_by_id(student_id)
        if updated is None:
            raise SchoolYearAssignmentRepositoryError("student_update_not_visible")
        return updated

    def archive(self, student_id: str, archived_at: datetime) -> V3Student:
        cursor = self.connection.execute(
            """
            UPDATE students
            SET active = 0, updated_at = ?, archived_at = ?
            WHERE student_id = ? AND active = 1 AND archived_at IS NULL
            """,
            (
                archived_at.isoformat(),
                archived_at.isoformat(),
                student_id,
            ),
        )
        if cursor.rowcount != 1:
            raise SchoolYearAssignmentRepositoryError(
                "student_missing_or_archived"
            )
        archived = self.get_by_id(student_id)
        if archived is None:
            raise SchoolYearAssignmentRepositoryError("student_archive_not_visible")
        return archived


def _school_year_from_row(row: sqlite3.Row) -> SchoolYear:
    return SchoolYear(
        school_year_id=str(row["school_year_id"]),
        label=str(row["label"]),
        start_date=date.fromisoformat(str(row["start_date"])),
        end_date=date.fromisoformat(str(row["end_date"])),
        status=SchoolYearStatus(str(row["status"])),
    )


def _stored_assignment_from_row(
    row: sqlite3.Row,
) -> StoredStudentSchoolYearAssignment:
    return StoredStudentSchoolYearAssignment(
        assignment_id=str(row["assignment_id"]),
        membership=StudentMembershipAssignment(
            student_id=str(row["student_id"]),
            school_year_id=str(row["school_year_id"]),
            group_id=(
                str(row["group_id"]) if row["group_id"] is not None else None
            ),
            course_id=(
                str(row["course_id"]) if row["course_id"] is not None else None
            ),
            assignment_status=StudentAssignmentStatus(
                str(row["assignment_status"])
            ),
            valid_from=date.fromisoformat(str(row["valid_from"])),
            valid_to=date.fromisoformat(str(row["valid_to"])),
        ),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def _assignment_source_from_row(row: sqlite3.Row) -> AssignmentSource:
    assignment_status = row["assignment_status"]
    return AssignmentSource(
        student_id=str(row["requested_student_id"]),
        student_active=bool(row["student_active"]),
        student_archived_at=(
            datetime.fromisoformat(str(row["student_archived_at"]))
            if row["student_archived_at"] is not None
            else None
        ),
        assignment_id=(
            str(row["assignment_id"])
            if row["assignment_id"] is not None
            else None
        ),
        school_year_id=(
            str(row["school_year_id"])
            if row["school_year_id"] is not None
            else None
        ),
        school_year_label=(
            str(row["school_year_label"])
            if row["school_year_label"] is not None
            else None
        ),
        assignment_status=(
            StudentAssignmentStatus(str(assignment_status))
            if assignment_status is not None
            else None
        ),
        valid_from=(
            date.fromisoformat(str(row["valid_from"]))
            if row["valid_from"] is not None
            else None
        ),
        valid_to=(
            date.fromisoformat(str(row["valid_to"]))
            if row["valid_to"] is not None
            else None
        ),
        group_id=(
            str(row["group_id"]) if row["group_id"] is not None else None
        ),
        group_name=(
            str(row["group_name"]) if row["group_name"] is not None else None
        ),
        course_id=(
            str(row["course_id"]) if row["course_id"] is not None else None
        ),
        course_name=(
            str(row["course_name"]) if row["course_name"] is not None else None
        ),
        year_level=(
            int(row["year_level"]) if row["year_level"] is not None else None
        ),
    )


def _v3_student_from_row(row: sqlite3.Row) -> V3Student:
    archived_at = row["archived_at"]
    return V3Student(
        student_id=str(row["student_id"]),
        first_name=str(row["first_name"]),
        last_name=str(row["last_name"]),
        notes=str(row["notes"] or ""),
        active=bool(row["active"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
        archived_at=(
            datetime.fromisoformat(str(archived_at))
            if archived_at is not None
            else None
        ),
    )
