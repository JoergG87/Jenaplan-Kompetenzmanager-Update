"""SQLite repositories for the isolated final-V3 assignment API.

Repositories in this module never open, commit, or roll back a transaction.
The caller owns the supplied connection and therefore the read snapshot or
write unit of work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import sqlite3
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

from .school_year import (
    AssignmentAtDateProjection,
    AssignmentReferenceRequest,
    AssignmentResolutionStatus,
    CurrentMembershipReadSnapshot,
    CurrentStudentMembershipProjection,
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
        if len({student_id for student_id, _ in pairs}) != len(pairs):
            raise SchoolYearAssignmentRepositoryError(
                "assignment_batch_student_duplicate"
            )
        references = tuple(
            AssignmentReferenceRequest(
                request_key=student_id,
                student_id=student_id,
                reference_date=reference_date,
            )
            for student_id, reference_date in pairs
        )
        resolved = self.list_assignments_for_references(
            references,
            school_year_id=school_year_id,
        )
        return {
            student_id: resolved[student_id]
            for student_id, _reference_date in pairs
        }

    def list_assignments_for_references(
        self,
        references: Sequence[AssignmentReferenceRequest],
        *,
        school_year_id: str | None = None,
    ) -> dict[str, tuple[AssignmentSource, ...]]:
        """Resolve repeated students at caller-keyed dates in one SQL query."""

        requested = tuple(references)
        if not requested:
            return {}
        keys = tuple(reference.request_key for reference in requested)
        if len(set(keys)) != len(keys):
            raise SchoolYearAssignmentRepositoryError(
                "assignment_reference_key_duplicate"
            )
        values_sql = ", ".join("(?, ?, ?, ?)" for _ in requested)
        parameters: list[object] = []
        for ordinal, reference in enumerate(requested):
            parameters.extend(
                (
                    ordinal,
                    reference.request_key,
                    reference.student_id,
                    reference.reference_date.isoformat(),
                )
            )
        school_year_sql = ""
        if school_year_id is not None:
            school_year_sql = "AND assignment.school_year_id = ?"
            parameters.append(school_year_id)
        rows = self.connection.execute(
            f"""
            WITH requested(
                request_ordinal,
                request_key,
                student_id,
                reference_date
            ) AS (
                VALUES {values_sql}
            )
            SELECT
                requested.request_ordinal,
                requested.request_key,
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
                requested.request_ordinal,
                assignment.valid_from,
                assignment.assignment_id
            """,
            tuple(parameters),
        ).fetchall()
        grouped: dict[str, list[AssignmentSource]] = {
            reference.request_key: [] for reference in requested
        }
        for row in rows:
            source = _assignment_source_from_row(row)
            request_key = str(row["request_key"])
            if source.assignment_id is not None:
                grouped[request_key].append(source)
            elif not grouped[request_key]:
                grouped[request_key].append(source)
        return {
            request_key: tuple(candidates)
            for request_key, candidates in grouped.items()
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
        group_ids: Sequence[str] = (),
        course_id: str | None = None,
        course_ids: Sequence[str] = (),
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
        normalized_group_ids = tuple(dict.fromkeys(group_ids))
        if normalized_group_ids:
            placeholders = ", ".join("?" for _ in normalized_group_ids)
            scope_filters.append(
                f"scoped_assignment.group_id IN ({placeholders})"
            )
            scope_parameters.extend(normalized_group_ids)
        if course_id is not None:
            scope_filters.append("scoped_assignment.course_id = ?")
            scope_parameters.append(course_id)
        normalized_course_ids = tuple(dict.fromkeys(course_ids))
        if normalized_course_ids:
            placeholders = ", ".join("?" for _ in normalized_course_ids)
            scope_filters.append(
                f"scoped_assignment.course_id IN ({placeholders})"
            )
            scope_parameters.extend(normalized_course_ids)
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
        if (
            group_id is not None
            or normalized_group_ids
            or course_id is not None
            or normalized_course_ids
            or course_group_id is not None
        ):
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

    def list_all(self) -> tuple[V3Student, ...]:
        rows = self.connection.execute(
            """
            SELECT
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            FROM students
            ORDER BY lower(last_name), lower(first_name), student_id
            """
        ).fetchall()
        return tuple(_v3_student_from_row(row) for row in rows)

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


class SchoolYearAssignmentReadSession:
    """Central assignment API bound to one caller-owned SQLite snapshot."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._school_years = SchoolYearRepository(connection)
        self._assignments = StudentSchoolYearAssignmentRepository(connection)
        self._current_loaded = False
        self._current: SchoolYear | None = None

    def assignment_at_date(
        self,
        student_id: str,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        sources = self._assignments.get_assignment_at_date(
            student_id,
            reference_date,
        )
        return _resolve_projection(student_id, reference_date, sources)

    def assignments_at_dates(
        self,
        student_dates: Mapping[str, date],
    ) -> tuple[AssignmentAtDateProjection, ...]:
        references = tuple(
            AssignmentReferenceRequest(student_id, student_id, reference_date)
            for student_id, reference_date in student_dates.items()
        )
        resolved = self.assignments_for_references(references)
        return tuple(resolved[reference.request_key] for reference in references)

    def assignments_for_references(
        self,
        references: Sequence[AssignmentReferenceRequest],
    ) -> dict[str, AssignmentAtDateProjection]:
        requested = tuple(references)
        sources = self._assignments.list_assignments_for_references(requested)
        return {
            reference.request_key: _resolve_projection(
                reference.student_id,
                reference.reference_date,
                sources.get(reference.request_key, ()),
            )
            for reference in requested
        }

    def current_membership(
        self,
        student_id: str,
        *,
        as_of: date,
    ) -> CurrentStudentMembershipProjection:
        return self.current_memberships((student_id,), as_of=as_of)[0]

    def current_memberships(
        self,
        student_ids: Sequence[str] | None = None,
        *,
        as_of: date,
        group_id: str | None = None,
        group_ids: Sequence[str] = (),
        course_id: str | None = None,
        course_ids: Sequence[str] = (),
        course_group_id: str | None = None,
    ) -> tuple[CurrentStudentMembershipProjection, ...]:
        identifiers = (
            tuple(dict.fromkeys(student_ids))
            if student_ids is not None
            else None
        )
        current = self._get_current()
        if current is None:
            if identifiers is None:
                return ()
            students = V3StudentRepository(self.connection).list_by_ids(
                identifiers
            )
            return tuple(
                _missing_current_membership(
                    student_id,
                    as_of,
                    students.get(student_id),
                )
                for student_id in identifiers
            )
        sources = self._assignments.list_current_memberships(
            current.school_year_id,
            as_of,
            student_ids=identifiers,
            group_id=group_id,
            group_ids=group_ids,
            course_id=course_id,
            course_ids=course_ids,
            course_group_id=course_group_id,
        )
        grouped: dict[str, list[AssignmentSource]] = {}
        for source in sources:
            grouped.setdefault(source.student_id, []).append(source)
        order = identifiers if identifiers is not None else tuple(grouped)
        projections = tuple(
            _current_projection(
                current,
                as_of,
                _resolve_projection(
                    student_id,
                    as_of,
                    grouped.get(student_id, ()),
                ),
            )
            for student_id in order
        )
        if identifiers is None or any(
            (
                group_id is not None,
                bool(group_ids),
                course_id is not None,
                bool(course_ids),
                course_group_id is not None,
            )
        ):
            projections = tuple(
                projection
                for projection in projections
                if (
                    projection.resolution_status
                    is AssignmentResolutionStatus.ENROLLED
                    and not projection.student_archived
                    and projection.student_active
                    and (
                        group_id is None
                        or projection.group_id == group_id
                    )
                    and (
                        not group_ids
                        or projection.group_id in group_ids
                    )
                    and (
                        course_id is None
                        or projection.course_id == course_id
                    )
                    and (
                        not course_ids
                        or projection.course_id in course_ids
                    )
                )
            )
        return projections

    def current_membership_snapshot(
        self,
        *,
        as_of: date,
        group_id: str | None = None,
        group_ids: Sequence[str] = (),
        course_id: str | None = None,
        course_ids: Sequence[str] = (),
        course_group_id: str | None = None,
    ) -> CurrentMembershipReadSnapshot:
        current = self._get_current()
        if current is None:
            return CurrentMembershipReadSnapshot(
                current_school_year_id=None,
                current_school_year_label=None,
                as_of=as_of,
                memberships=(),
                ambiguous_student_ids=(),
                current_school_year_missing=True,
                group_counts=MappingProxyType({}),
                course_counts=MappingProxyType({}),
            )
        sources = self._assignments.list_current_memberships(
            current.school_year_id,
            as_of,
            group_id=group_id,
            group_ids=group_ids,
            course_id=course_id,
            course_ids=course_ids,
            course_group_id=course_group_id,
        )
        grouped: dict[str, list[AssignmentSource]] = {}
        for source in sources:
            grouped.setdefault(source.student_id, []).append(source)
        resolved = tuple(
            _current_projection(
                current,
                as_of,
                _resolve_projection(student_id, as_of, candidates),
            )
            for student_id, candidates in grouped.items()
        )
        ambiguous_student_ids = tuple(
            sorted(
                projection.student_id
                for projection in resolved
                if (
                    projection.resolution_status
                    is AssignmentResolutionStatus.AMBIGUOUS
                )
            )
        )
        memberships = tuple(
            projection
            for projection in resolved
            if (
                projection.resolution_status
                is AssignmentResolutionStatus.ENROLLED
                and projection.student_active
                and not projection.student_archived
            )
        )
        group_counts: dict[str, int] = {}
        course_counts: dict[str, int] = {}
        for membership in memberships:
            if membership.group_id is not None:
                group_counts[membership.group_id] = (
                    group_counts.get(membership.group_id, 0) + 1
                )
            if membership.course_id is not None:
                course_counts[membership.course_id] = (
                    course_counts.get(membership.course_id, 0) + 1
                )
        return CurrentMembershipReadSnapshot(
            current_school_year_id=current.school_year_id,
            current_school_year_label=current.label,
            as_of=as_of,
            memberships=memberships,
            ambiguous_student_ids=ambiguous_student_ids,
            current_school_year_missing=False,
            group_counts=MappingProxyType(group_counts),
            course_counts=MappingProxyType(course_counts),
        )

    def membership_in_school_year(
        self,
        student_id: str,
        school_year_id: str,
        *,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        school_year = self._school_years.get_by_id(school_year_id)
        if school_year is None:
            raise SchoolYearAssignmentRepositoryError("school_year_missing")
        if not school_year.start_date <= reference_date <= school_year.end_date:
            raise SchoolYearAssignmentRepositoryError(
                "reference_date_outside_school_year"
            )
        sources = self._assignments.get_assignment_at_date(
            student_id,
            reference_date,
            school_year_id=school_year_id,
        )
        return _resolve_projection(student_id, reference_date, sources)

    def last_known_membership(
        self,
        student_id: str,
        *,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        sources = self._assignments.get_last_known(student_id, reference_date)
        return _resolve_projection(student_id, reference_date, sources)

    def count_current_by_group(self, *, as_of: date) -> dict[str, int]:
        snapshot = self.current_membership_snapshot(as_of=as_of)
        if snapshot.current_school_year_missing:
            raise SchoolYearAssignmentRepositoryError(
                "current_school_year_missing"
            )
        if snapshot.ambiguous_student_ids:
            raise SchoolYearAssignmentRepositoryError(
                "assignment_ambiguous"
            )
        return dict(snapshot.group_counts)

    def count_current_by_course(self, *, as_of: date) -> dict[str, int]:
        snapshot = self.current_membership_snapshot(as_of=as_of)
        if snapshot.current_school_year_missing:
            raise SchoolYearAssignmentRepositoryError(
                "current_school_year_missing"
            )
        if snapshot.ambiguous_student_ids:
            raise SchoolYearAssignmentRepositoryError(
                "assignment_ambiguous"
            )
        return dict(snapshot.course_counts)

    def _get_current(self) -> SchoolYear | None:
        if not self._current_loaded:
            self._current = self._school_years.get_current()
            self._current_loaded = True
        return self._current


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


def _resolve_projection(
    student_id: str,
    reference_date: date,
    sources: Sequence[AssignmentSource],
) -> AssignmentAtDateProjection:
    matched = tuple(
        source for source in sources if source.assignment_id is not None
    )
    base = sources[0] if sources else None
    student_active = base.student_active if base is not None else False
    archived_at = base.student_archived_at if base is not None else None
    student_archived = archived_at is not None or not student_active
    if (
        archived_at is not None
        and archived_at.date() <= reference_date
    ):
        return _empty_projection(
            student_id,
            reference_date,
            AssignmentResolutionStatus.STUDENT_ARCHIVED,
            student_active,
            True,
        )
    if len(matched) > 1:
        return _empty_projection(
            student_id,
            reference_date,
            AssignmentResolutionStatus.AMBIGUOUS,
            student_active,
            student_archived,
        )
    if len(matched) == 1:
        source = matched[0]
        assert source.assignment_status is not None
        status = (
            AssignmentResolutionStatus.ENROLLED
            if source.assignment_status is StudentAssignmentStatus.ENROLLED
            else AssignmentResolutionStatus.EXITED
        )
        return AssignmentAtDateProjection(
            student_id=student_id,
            reference_date=reference_date,
            resolution_status=status,
            school_year_id=source.school_year_id,
            school_year_label=source.school_year_label,
            assignment_id=source.assignment_id,
            assignment_status=source.assignment_status,
            valid_from=source.valid_from,
            valid_to=source.valid_to,
            group_id=source.group_id,
            group_name=source.group_name,
            course_id=source.course_id,
            course_name=source.course_name,
            year_level=source.year_level,
            student_active=student_active,
            student_archived=student_archived,
            visible_status_key=status.value,
            accessible_name=_accessible_assignment_name(status, source),
        )
    return _empty_projection(
        student_id,
        reference_date,
        AssignmentResolutionStatus.NO_ASSIGNMENT,
        student_active,
        student_archived,
    )


def _empty_projection(
    student_id: str,
    reference_date: date,
    status: AssignmentResolutionStatus,
    student_active: bool,
    student_archived: bool,
) -> AssignmentAtDateProjection:
    accessible_names = {
        AssignmentResolutionStatus.NO_ASSIGNMENT: "Keine Zuordnung vorhanden",
        AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING: (
            "Kein aktuelles Schuljahr festgelegt"
        ),
        AssignmentResolutionStatus.AMBIGUOUS: "Zuordnung nicht eindeutig",
        AssignmentResolutionStatus.STUDENT_ARCHIVED: "Kind ist archiviert",
    }
    return AssignmentAtDateProjection(
        student_id=student_id,
        reference_date=reference_date,
        resolution_status=status,
        school_year_id=None,
        school_year_label=None,
        assignment_id=None,
        assignment_status=None,
        valid_from=None,
        valid_to=None,
        group_id=None,
        group_name=None,
        course_id=None,
        course_name=None,
        year_level=None,
        student_active=student_active,
        student_archived=student_archived,
        visible_status_key=status.value,
        accessible_name=accessible_names[status],
    )


def _accessible_assignment_name(
    status: AssignmentResolutionStatus,
    source: AssignmentSource,
) -> str:
    year = source.school_year_label or "Schuljahr unbekannt"
    if status is AssignmentResolutionStatus.EXITED:
        return f"{year}, ausgeschieden"
    group = source.group_name or "Stammgruppe unbekannt"
    course = source.course_name or "Kurs unbekannt"
    level = (
        f"Stufe {source.year_level}"
        if source.year_level is not None
        else "Stufe unbekannt"
    )
    return f"{year}, eingeschrieben, {group}, {course}, {level}"


def _current_projection(
    current: SchoolYear,
    as_of: date,
    resolved: AssignmentAtDateProjection,
) -> CurrentStudentMembershipProjection:
    return CurrentStudentMembershipProjection(
        current_school_year_id=current.school_year_id,
        current_school_year_label=current.label,
        as_of=as_of,
        student_id=resolved.student_id,
        student_active=resolved.student_active,
        student_archived=resolved.student_archived,
        resolution_status=resolved.resolution_status,
        group_id=resolved.group_id,
        group_name=resolved.group_name,
        course_id=resolved.course_id,
        course_name=resolved.course_name,
        year_level=resolved.year_level,
    )


def _missing_current_membership(
    student_id: str,
    as_of: date,
    student: V3Student | None,
) -> CurrentStudentMembershipProjection:
    return CurrentStudentMembershipProjection(
        current_school_year_id=None,
        current_school_year_label=None,
        as_of=as_of,
        student_id=student_id,
        student_active=student.active if student is not None else False,
        student_archived=(
            student.archived_at is not None if student is not None else False
        ),
        resolution_status=(
            AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING
        ),
        group_id=None,
        group_name=None,
        course_id=None,
        course_name=None,
        year_level=None,
    )
