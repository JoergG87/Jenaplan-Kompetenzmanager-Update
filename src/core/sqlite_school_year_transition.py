"""Connection-bound SQLite reads for the school-year transition preview."""

from __future__ import annotations

import sqlite3

from .school_year import SchoolYear
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
