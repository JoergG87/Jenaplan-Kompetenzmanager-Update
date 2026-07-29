"""Explicit V2 membership doubles for pre-V3 synthetic regression fixtures.

These readers exist only in the test package. Product code always uses the
central Final-V3 assignment API. Older tests that intentionally exercise the
still-blocked V2 writer/runtime fixture receive equivalent read projections so
unrelated observation, report, PDF and UI regressions remain testable.
"""

from __future__ import annotations

from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping, Sequence
import sqlite3

from src.core.school_year import (
    AssignmentAtDateProjection,
    AssignmentReferenceRequest,
    AssignmentResolutionStatus,
    CurrentMembershipReadSnapshot,
    CurrentStudentMembershipProjection,
    StudentAssignmentStatus,
    V3Student,
)
from src.core.sqlite_school_year_assignment import (
    SchoolYearAssignmentReadSession as FinalV3ReadSession,
    V3StudentRepository as FinalV3StudentRepository,
)


LEGACY_TEST_SCHOOL_YEAR_ID = "SY-LEGACY-TEST"
LEGACY_TEST_SCHOOL_YEAR_LABEL = "Synthetischer V2-Testbestand"


def is_final_v3(connection: sqlite3.Connection) -> bool:
    columns = {
        str(row["name"] if isinstance(row, sqlite3.Row) else row[1])
        for row in connection.execute("PRAGMA table_info(students)").fetchall()
    }
    return "notes" in columns and "student_notes" not in columns


class SyntheticLegacyStudentRepository:
    """V3 master-data projection over an explicit synthetic legacy fixture."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._delegate = (
            FinalV3StudentRepository(connection)
            if is_final_v3(connection)
            else None
        )

    def __getattr__(self, name: str):
        if self._delegate is not None:
            return getattr(self._delegate, name)
        raise AttributeError(name)

    def list_all(self) -> tuple[V3Student, ...]:
        if self._delegate is not None:
            return self._delegate.list_all()
        rows = self.connection.execute(
            """
            SELECT
                student_id, first_name, last_name, student_notes,
                active, created_at, updated_at, archived_at
            FROM students
            ORDER BY lower(last_name), lower(first_name), student_id
            """
        ).fetchall()
        return tuple(_legacy_student(row) for row in rows)

    def list_by_ids(self, student_ids: Sequence[str]) -> dict[str, V3Student]:
        if self._delegate is not None:
            return self._delegate.list_by_ids(student_ids)
        identifiers = tuple(dict.fromkeys(student_ids))
        if not identifiers:
            return {}
        placeholders = ", ".join("?" for _ in identifiers)
        rows = self.connection.execute(
            f"""
            SELECT
                student_id, first_name, last_name, student_notes,
                active, created_at, updated_at, archived_at
            FROM students
            WHERE student_id IN ({placeholders})
            """,
            identifiers,
        ).fetchall()
        return {
            str(row["student_id"]): _legacy_student(row)
            for row in rows
        }

    def get_by_id(self, student_id: str) -> V3Student | None:
        if self._delegate is not None:
            return self._delegate.get_by_id(student_id)
        row = self.connection.execute(
            """
            SELECT
                student_id, first_name, last_name, student_notes,
                active, created_at, updated_at, archived_at
            FROM students
            WHERE student_id = ?
            """,
            (student_id,),
        ).fetchone()
        return _legacy_student(row) if row is not None else None


class SyntheticLegacyAssignmentReadSession:
    """Assignment projections for explicitly marked synthetic V2 tests only."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._delegate = (
            FinalV3ReadSession(connection)
            if is_final_v3(connection)
            else None
        )

    def __getattr__(self, name: str):
        if self._delegate is not None:
            return getattr(self._delegate, name)
        raise AttributeError(name)

    def assignment_at_date(
        self,
        student_id: str,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        if self._delegate is not None:
            return self._delegate.assignment_at_date(
                student_id,
                reference_date,
            )
        return _legacy_assignment(
            self.connection,
            student_id,
            reference_date,
        )

    def assignments_at_dates(
        self,
        student_dates: Mapping[str, date],
    ) -> tuple[AssignmentAtDateProjection, ...]:
        if self._delegate is not None:
            return self._delegate.assignments_at_dates(student_dates)
        return tuple(
            self.assignment_at_date(student_id, reference_date)
            for student_id, reference_date in student_dates.items()
        )

    def assignments_for_references(
        self,
        references: Sequence[AssignmentReferenceRequest],
    ) -> dict[str, AssignmentAtDateProjection]:
        if self._delegate is not None:
            return self._delegate.assignments_for_references(references)
        return {
            reference.request_key: self.assignment_at_date(
                reference.student_id,
                reference.reference_date,
            )
            for reference in references
        }

    def current_membership(
        self,
        student_id: str,
        *,
        as_of: date,
    ) -> CurrentStudentMembershipProjection:
        if self._delegate is not None:
            return self._delegate.current_membership(
                student_id,
                as_of=as_of,
            )
        return _current_projection(
            _legacy_assignment(self.connection, student_id, as_of),
            as_of,
        )

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
        if self._delegate is not None:
            return self._delegate.current_memberships(
                student_ids,
                as_of=as_of,
                group_id=group_id,
                group_ids=group_ids,
                course_id=course_id,
                course_ids=course_ids,
                course_group_id=course_group_id,
            )
        identifiers = (
            tuple(dict.fromkeys(student_ids))
            if student_ids is not None
            else None
        )
        allowed_groups: set[str] | None = None
        allowed_courses: set[str] | None = None
        if course_group_id is not None:
            allowed_groups = {
                str(row["student_group_id"])
                for row in self.connection.execute(
                    """
                    SELECT student_group_id
                    FROM course_group_student_groups
                    WHERE course_group_id = ?
                    """,
                    (course_group_id,),
                ).fetchall()
            }
            allowed_courses = {
                str(row["course_id"])
                for row in self.connection.execute(
                    """
                    SELECT course_id
                    FROM course_group_courses
                    WHERE course_group_id = ?
                    """,
                    (course_group_id,),
                ).fetchall()
            }
        requested_groups = frozenset(group_ids)
        requested_courses = frozenset(course_ids)
        clauses: list[str] = []
        parameters: list[object] = []
        if identifiers is None:
            clauses.extend(
                ("student.active = 1", "student.archived_at IS NULL")
            )
        elif not identifiers:
            return ()
        else:
            placeholders = ", ".join("?" for _ in identifiers)
            clauses.append(f"student.student_id IN ({placeholders})")
            parameters.extend(identifiers)
        where_sql = " AND ".join(clauses) if clauses else "1 = 1"
        rows = self.connection.execute(
            f"""
            SELECT
                student.student_id,
                student.group_id,
                student.course_id,
                student.active,
                student.archived_at,
                student_group.group_name,
                course.course_name
            FROM students AS student
            LEFT JOIN groups AS student_group
                ON student_group.group_id = student.group_id
            LEFT JOIN courses AS course
                ON course.course_id = student.course_id
            WHERE {where_sql}
            ORDER BY
                lower(student.last_name),
                lower(student.first_name),
                student.student_id
            """,
            tuple(parameters),
        ).fetchall()
        by_student_id = {
            str(row["student_id"]): _current_projection(
                _legacy_assignment_from_row(row, as_of),
                as_of,
            )
            for row in rows
        }
        order = (
            identifiers
            if identifiers is not None
            else tuple(by_student_id)
        )
        projections = tuple(
            by_student_id.get(
                student_id,
                _current_projection(
                    _empty_assignment(
                        student_id,
                        as_of,
                        AssignmentResolutionStatus.NO_ASSIGNMENT,
                        False,
                        False,
                    ),
                    as_of,
                ),
            )
            for student_id in order
        )
        if student_ids is not None and not any(
            (
                group_id,
                requested_groups,
                course_id,
                requested_courses,
                course_group_id,
            )
        ):
            return projections
        return tuple(
            projection
            for projection in projections
            if (
                projection.resolution_status
                is AssignmentResolutionStatus.ENROLLED
                and (group_id is None or projection.group_id == group_id)
                and (
                    not requested_groups
                    or projection.group_id in requested_groups
                )
                and (course_id is None or projection.course_id == course_id)
                and (
                    not requested_courses
                    or projection.course_id in requested_courses
                )
                and (
                    allowed_groups is None
                    or (
                        projection.group_id in allowed_groups
                        and projection.course_id in (allowed_courses or set())
                    )
                )
            )
        )

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
        if self._delegate is not None:
            return self._delegate.current_membership_snapshot(
                as_of=as_of,
                group_id=group_id,
                group_ids=group_ids,
                course_id=course_id,
                course_ids=course_ids,
                course_group_id=course_group_id,
            )
        memberships = self.current_memberships(
            as_of=as_of,
            group_id=group_id,
            group_ids=group_ids,
            course_id=course_id,
            course_ids=course_ids,
            course_group_id=course_group_id,
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
            current_school_year_id=LEGACY_TEST_SCHOOL_YEAR_ID,
            current_school_year_label=LEGACY_TEST_SCHOOL_YEAR_LABEL,
            as_of=as_of,
            memberships=memberships,
            ambiguous_student_ids=(),
            current_school_year_missing=False,
            group_counts=MappingProxyType(group_counts),
            course_counts=MappingProxyType(course_counts),
        )

    def count_current_by_group(self, *, as_of: date) -> dict[str, int]:
        if self._delegate is not None:
            return self._delegate.count_current_by_group(as_of=as_of)
        return dict(
            self.current_membership_snapshot(as_of=as_of).group_counts
        )

    def count_current_by_course(self, *, as_of: date) -> dict[str, int]:
        if self._delegate is not None:
            return self._delegate.count_current_by_course(as_of=as_of)
        return dict(
            self.current_membership_snapshot(as_of=as_of).course_counts
        )


def _legacy_student(row: sqlite3.Row) -> V3Student:
    return V3Student(
        student_id=str(row["student_id"]),
        first_name=str(row["first_name"]),
        last_name=str(row["last_name"]),
        notes=str(row["student_notes"] or ""),
        active=bool(row["active"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
        archived_at=(
            datetime.fromisoformat(str(row["archived_at"]))
            if row["archived_at"]
            else None
        ),
    )


def _legacy_assignment(
    connection: sqlite3.Connection,
    student_id: str,
    reference_date: date,
) -> AssignmentAtDateProjection:
    row = connection.execute(
        """
        SELECT
            student.student_id,
            student.group_id,
            student.course_id,
            student.active,
            student.archived_at,
            student_group.group_name,
            course.course_name
        FROM students AS student
        LEFT JOIN groups AS student_group
            ON student_group.group_id = student.group_id
        LEFT JOIN courses AS course
            ON course.course_id = student.course_id
        WHERE student.student_id = ?
        """,
        (student_id,),
    ).fetchone()
    if row is None:
        return _empty_assignment(
            student_id,
            reference_date,
            AssignmentResolutionStatus.NO_ASSIGNMENT,
            False,
            False,
        )
    return _legacy_assignment_from_row(row, reference_date)


def _legacy_assignment_from_row(
    row: sqlite3.Row,
    reference_date: date,
) -> AssignmentAtDateProjection:
    student_id = str(row["student_id"])
    active = bool(row["active"])
    archived = bool(row["archived_at"]) or not active
    if archived:
        return _empty_assignment(
            student_id,
            reference_date,
            AssignmentResolutionStatus.STUDENT_ARCHIVED,
            active,
            True,
        )
    if not row["group_id"] or not row["course_id"]:
        return _empty_assignment(
            student_id,
            reference_date,
            AssignmentResolutionStatus.NO_ASSIGNMENT,
            active,
            False,
        )
    return AssignmentAtDateProjection(
        student_id=student_id,
        reference_date=reference_date,
        resolution_status=AssignmentResolutionStatus.ENROLLED,
        school_year_id=LEGACY_TEST_SCHOOL_YEAR_ID,
        school_year_label=LEGACY_TEST_SCHOOL_YEAR_LABEL,
        assignment_id=f"ASG-LEGACY-{student_id}",
        assignment_status=StudentAssignmentStatus.ENROLLED,
        valid_from=reference_date,
        valid_to=reference_date,
        group_id=str(row["group_id"]),
        group_name=str(row["group_name"] or ""),
        course_id=str(row["course_id"]),
        course_name=str(row["course_name"] or ""),
        year_level=None,
        student_active=active,
        student_archived=False,
        visible_status_key=AssignmentResolutionStatus.ENROLLED.value,
        accessible_name=(
            f"{LEGACY_TEST_SCHOOL_YEAR_LABEL}, eingeschrieben, "
            f"{row['group_name'] or ''}, {row['course_name'] or ''}"
        ),
    )


def _empty_assignment(
    student_id: str,
    reference_date: date,
    status: AssignmentResolutionStatus,
    active: bool,
    archived: bool,
) -> AssignmentAtDateProjection:
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
        student_active=active,
        student_archived=archived,
        visible_status_key=status.value,
        accessible_name=status.value,
    )


def _current_projection(
    assignment: AssignmentAtDateProjection,
    as_of: date,
) -> CurrentStudentMembershipProjection:
    return CurrentStudentMembershipProjection(
        current_school_year_id=(
            LEGACY_TEST_SCHOOL_YEAR_ID
            if assignment.resolution_status
            is AssignmentResolutionStatus.ENROLLED
            else None
        ),
        current_school_year_label=(
            LEGACY_TEST_SCHOOL_YEAR_LABEL
            if assignment.resolution_status
            is AssignmentResolutionStatus.ENROLLED
            else None
        ),
        as_of=as_of,
        student_id=assignment.student_id,
        student_active=assignment.student_active,
        student_archived=assignment.student_archived,
        resolution_status=assignment.resolution_status,
        group_id=assignment.group_id,
        group_name=assignment.group_name,
        course_id=assignment.course_id,
        course_name=assignment.course_name,
        year_level=assignment.year_level,
    )
