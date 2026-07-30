"""Connection-bound SQLite boundary for school-year transition reads and writes.

The repositories never begin, commit, roll back, or close a transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import sqlite3

from .school_year import (
    SchoolYear,
    StudentAssignmentStatus,
    StudentMembershipAssignment,
)
from .school_year_transition import (
    SchoolYearTransitionCourse,
    SchoolYearTransitionGroup,
    SchoolYearTransitionMembership,
    SchoolYearTransitionPreviewSources,
)
from .sqlite_school_year_assignment import (
    SchoolYearAssignmentRepositoryError,
    StudentSchoolYearAssignmentRepository,
    V3StudentRepository,
)


NO_BACKUP_EVIDENCE_SHA256 = "0" * 64


class SchoolYearTransitionRepositoryError(RuntimeError):
    """Fail closed at the transition persistence boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class StoredSchoolYearTransition:
    transition_id: str
    from_school_year_id: str
    to_school_year_id: str
    operation_token: str
    plan_sha256: str
    result_counts_json: str
    completed_at: datetime


class SchoolYearTransitionPreviewRepository:
    """Read every SJ-3A source from one caller-owned SQLite snapshot."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def read_sources(
        self,
        *,
        school_years: tuple[SchoolYear, ...],
        current_school_year: SchoolYear | None,
    ) -> SchoolYearTransitionPreviewSources:
        students = V3StudentRepository(self.connection).list_all()
        memberships: tuple[SchoolYearTransitionMembership, ...] = ()
        if current_school_year is not None:
            sources = StudentSchoolYearAssignmentRepository(
                self.connection
            ).list_current_memberships(
                current_school_year.school_year_id,
                current_school_year.end_date,
                student_ids=tuple(student.student_id for student in students),
            )
            if any(source.assignment_status is None for source in sources):
                raise SchoolYearAssignmentRepositoryError(
                    "transition_assignment_status_invalid"
                )
            memberships = tuple(
                SchoolYearTransitionMembership(
                    student_id=source.student_id,
                    school_year_id=current_school_year.school_year_id,
                    group_id=source.group_id,
                    group_name=source.group_name,
                    course_id=source.course_id,
                    course_name=source.course_name,
                    assignment_status=source.assignment_status,
                )
                for source in sources
                if source.assignment_id is not None
            )
        return SchoolYearTransitionPreviewSources(
            school_years=school_years,
            students=students,
            memberships=memberships,
            courses=self._list_courses(),
            groups=self._list_groups(),
            source_sha256=school_year_transition_source_sha256(self.connection),
        )

    def _list_courses(self) -> tuple[SchoolYearTransitionCourse, ...]:
        rows = self.connection.execute(
            """
            SELECT course_id, course_name, active, year_level
            FROM courses
            ORDER BY course_id
            """
        ).fetchall()
        return tuple(
            SchoolYearTransitionCourse(
                course_id=str(row["course_id"]),
                course_name=str(row["course_name"]),
                active=bool(row["active"]),
                year_level=row["year_level"],
            )
            for row in rows
        )

    def _list_groups(self) -> tuple[SchoolYearTransitionGroup, ...]:
        rows = self.connection.execute(
            """
            SELECT group_id, group_name, active
            FROM groups
            ORDER BY group_id
            """
        ).fetchall()
        return tuple(
            SchoolYearTransitionGroup(
                group_id=str(row["group_id"]),
                group_name=str(row["group_name"]),
                active=bool(row["active"]),
            )
            for row in rows
        )


class SchoolYearTransitionExecutionRepository:
    """Write one complete transition inside a caller-owned transaction."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def source_sha256(self) -> str:
        return school_year_transition_source_sha256(self.connection)

    def find_by_operation_token(
        self,
        operation_token: str,
    ) -> StoredSchoolYearTransition | None:
        row = self.connection.execute(
            """
            SELECT
                transition_id, from_school_year_id, to_school_year_id,
                operation_token, plan_sha256, result_counts_json, completed_at
            FROM school_year_transitions
            WHERE operation_token = ?
            """,
            (operation_token,),
        ).fetchone()
        return _stored_transition(row) if row is not None else None

    def find_by_target_school_year_id(
        self,
        school_year_id: str,
    ) -> StoredSchoolYearTransition | None:
        row = self.connection.execute(
            """
            SELECT
                transition_id, from_school_year_id, to_school_year_id,
                operation_token, plan_sha256, result_counts_json, completed_at
            FROM school_year_transitions
            WHERE to_school_year_id = ?
            """,
            (school_year_id,),
        ).fetchone()
        return _stored_transition(row) if row is not None else None

    def current_school_year(self) -> SchoolYear | None:
        rows = self.connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years
            WHERE status = 'current'
            ORDER BY school_year_id
            LIMIT 2
            """
        ).fetchall()
        if len(rows) != 1:
            return None
        row = rows[0]
        return SchoolYear(
            school_year_id=str(row["school_year_id"]),
            label=str(row["label"]),
            start_date=date.fromisoformat(str(row["start_date"])),
            end_date=date.fromisoformat(str(row["end_date"])),
            status=str(row["status"]),
        )

    def target_school_year_exists(
        self,
        *,
        school_year_id: str,
        label: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM school_years
            WHERE school_year_id = ?
               OR label = ?
               OR NOT (end_date < ? OR start_date > ?)
            LIMIT 1
            """,
            (
                school_year_id,
                label,
                start_date.isoformat(),
                end_date.isoformat(),
            ),
        ).fetchone()
        return row is not None

    def validate_active_references(
        self,
        *,
        group_ids: tuple[str, ...],
        course_ids: tuple[str, ...],
    ) -> None:
        if group_ids:
            placeholders = ", ".join("?" for _ in group_ids)
            count = self.connection.execute(
                f"""
                SELECT count(*)
                FROM groups
                WHERE active = 1 AND group_id IN ({placeholders})
                """,
                group_ids,
            ).fetchone()[0]
            if int(count) != len(group_ids):
                raise SchoolYearTransitionRepositoryError(
                    "transition_group_invalid"
                )
        if course_ids:
            placeholders = ", ".join("?" for _ in course_ids)
            count = self.connection.execute(
                f"""
                SELECT count(*)
                FROM courses
                WHERE active = 1 AND course_id IN ({placeholders})
                """,
                course_ids,
            ).fetchone()[0]
            if int(count) != len(course_ids):
                raise SchoolYearTransitionRepositoryError(
                    "transition_course_invalid"
                )

    def close_current_school_year(
        self,
        school_year_id: str,
        completed_at: datetime,
    ) -> None:
        cursor = self.connection.execute(
            """
            UPDATE school_years
            SET status = 'closed', closed_at = ?
            WHERE school_year_id = ? AND status = 'current'
            """,
            (completed_at.isoformat(), school_year_id),
        )
        if cursor.rowcount != 1:
            raise SchoolYearTransitionRepositoryError(
                "transition_current_school_year_changed"
            )

    def insert_current_school_year(
        self,
        *,
        school_year_id: str,
        label: str,
        start_date: date,
        end_date: date,
        created_at: datetime,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (?, ?, ?, ?, 'current', ?, NULL)
            """,
            (
                school_year_id,
                label,
                start_date.isoformat(),
                end_date.isoformat(),
                created_at.isoformat(),
            ),
        )

    def insert_assignment(
        self,
        *,
        assignment_id: str,
        assignment: StudentMembershipAssignment,
        created_at: datetime,
    ) -> None:
        StudentSchoolYearAssignmentRepository(self.connection).insert(
            assignment_id,
            assignment,
            created_at,
        )

    def insert_transition(
        self,
        *,
        transition_id: str,
        from_school_year_id: str,
        to_school_year_id: str,
        operation_token: str,
        plan_sha256: str,
        result_counts_json: str,
        completed_at: datetime,
    ) -> StoredSchoolYearTransition:
        self.connection.execute(
            """
            INSERT INTO school_year_transitions(
                transition_id, from_school_year_id, to_school_year_id,
                operation_token, plan_sha256, backup_sha256,
                result_counts_json, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transition_id,
                from_school_year_id,
                to_school_year_id,
                operation_token,
                plan_sha256,
                NO_BACKUP_EVIDENCE_SHA256,
                result_counts_json,
                completed_at.isoformat(),
            ),
        )
        stored = self.find_by_operation_token(operation_token)
        if stored is None:
            raise SchoolYearTransitionRepositoryError(
                "transition_receipt_not_visible"
            )
        return stored

    def verify_written_result(
        self,
        *,
        from_school_year_id: str,
        to_school_year_id: str,
        expected_student_ids: tuple[str, ...],
        expected_enrolled_count: int,
        expected_exited_count: int,
        operation_token: str,
    ) -> None:
        statuses = self.connection.execute(
            """
            SELECT assignment_status, count(*) AS item_count
            FROM student_school_year_assignments
            WHERE school_year_id = ?
            GROUP BY assignment_status
            """,
            (to_school_year_id,),
        ).fetchall()
        counts = {
            str(row["assignment_status"]): int(row["item_count"])
            for row in statuses
        }
        if counts.get(StudentAssignmentStatus.ENROLLED.value, 0) != (
            expected_enrolled_count
        ):
            raise SchoolYearTransitionRepositoryError(
                "transition_enrolled_count_mismatch"
            )
        if counts.get(StudentAssignmentStatus.EXITED.value, 0) != (
            expected_exited_count
        ):
            raise SchoolYearTransitionRepositoryError(
                "transition_exited_count_mismatch"
            )
        rows = self.connection.execute(
            """
            SELECT student_id
            FROM student_school_year_assignments
            WHERE school_year_id = ?
            ORDER BY student_id
            """,
            (to_school_year_id,),
        ).fetchall()
        actual_student_ids = tuple(str(row["student_id"]) for row in rows)
        if actual_student_ids != tuple(sorted(expected_student_ids)):
            raise SchoolYearTransitionRepositoryError(
                "transition_student_count_mismatch"
            )
        state = self.connection.execute(
            """
            SELECT
                sum(status = 'closed' AND school_year_id = ?),
                sum(status = 'current' AND school_year_id = ?),
                sum(status = 'current')
            FROM school_years
            """,
            (from_school_year_id, to_school_year_id),
        ).fetchone()
        if tuple(int(value or 0) for value in state) != (1, 1, 1):
            raise SchoolYearTransitionRepositoryError(
                "transition_school_year_state_mismatch"
            )
        receipt_count = self.connection.execute(
            """
            SELECT count(*)
            FROM school_year_transitions
            WHERE operation_token = ? AND to_school_year_id = ?
            """,
            (operation_token, to_school_year_id),
        ).fetchone()[0]
        if int(receipt_count) != 1:
            raise SchoolYearTransitionRepositoryError(
                "transition_receipt_count_mismatch"
            )
        integrity = self.connection.execute("PRAGMA integrity_check").fetchall()
        if len(integrity) != 1 or str(integrity[0][0]).lower() != "ok":
            raise SchoolYearTransitionRepositoryError(
                "transition_integrity_check_failed"
            )
        if self.connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise SchoolYearTransitionRepositoryError(
                "transition_foreign_key_check_failed"
            )


def school_year_transition_source_sha256(
    connection: sqlite3.Connection,
) -> str:
    """Hash all technical source rows that can affect transition execution."""

    payload = {
        "schema_version": 1,
        "school_years": _rows(
            connection,
            """
            SELECT
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            FROM school_years
            ORDER BY school_year_id
            """,
        ),
        "students": _rows(
            connection,
            """
            SELECT student_id, active, archived_at
            FROM students
            ORDER BY student_id
            """,
        ),
        "assignments": _rows(
            connection,
            """
            SELECT
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            FROM student_school_year_assignments
            ORDER BY assignment_id
            """,
        ),
        "courses": _rows(
            connection,
            """
            SELECT course_id, active, year_level
            FROM courses
            ORDER BY course_id
            """,
        ),
        "groups": _rows(
            connection,
            """
            SELECT group_id, active
            FROM groups
            ORDER BY group_id
            """,
        ),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rows(
    connection: sqlite3.Connection,
    statement: str,
) -> list[list[object]]:
    return [list(row) for row in connection.execute(statement).fetchall()]


def _stored_transition(row: sqlite3.Row) -> StoredSchoolYearTransition:
    return StoredSchoolYearTransition(
        transition_id=str(row["transition_id"]),
        from_school_year_id=str(row["from_school_year_id"]),
        to_school_year_id=str(row["to_school_year_id"]),
        operation_token=str(row["operation_token"]),
        plan_sha256=str(row["plan_sha256"]),
        result_counts_json=str(row["result_counts_json"]),
        completed_at=datetime.fromisoformat(str(row["completed_at"])),
    )
