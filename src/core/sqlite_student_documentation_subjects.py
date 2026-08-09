"""Connection-bound persistence for student documentation subjects.

The repository never opens, commits, or rolls back a transaction. Application
callers own the supplied connection and therefore the full read/write snapshot.
"""

from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Iterable

from .student_documentation_subjects import (
    DocumentationSubjectMode,
    StudentDocumentationSubjectConfiguration,
    StudentDocumentationSubjectProfile,
)


class StudentDocumentationSubjectRepositoryError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SQLiteStudentDocumentationSubjectRepository:
    """Read and write profiles and exact selections on one connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def student_state(self, student_id: str) -> tuple[bool, str | None] | None:
        row = self.connection.execute(
            "SELECT active, archived_at FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if row is None:
            return None
        return bool(row["active"]), row["archived_at"]

    def school_year_status(self, school_year_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT status FROM school_years WHERE school_year_id = ?",
            (school_year_id,),
        ).fetchone()
        return None if row is None else str(row["status"])

    def subject_state(self, subject_id: str) -> tuple[bool, int] | None:
        row = self.connection.execute(
            """
            SELECT MAX(active) AS catalog_active, MIN(sort_order) AS sort_order
            FROM competencies
            WHERE subject_id = ?
            GROUP BY subject_id
            """,
            (subject_id,),
        ).fetchone()
        if row is None:
            return None
        return bool(row["catalog_active"]), int(row["sort_order"])

    def get_profile(
        self,
        student_id: str,
        school_year_id: str,
    ) -> StudentDocumentationSubjectProfile | None:
        row = self.connection.execute(
            """
            SELECT student_id, school_year_id, mode, created_at, updated_at
            FROM student_documentation_subject_profiles
            WHERE student_id = ? AND school_year_id = ?
            """,
            (student_id, school_year_id),
        ).fetchone()
        if row is None:
            return None
        return StudentDocumentationSubjectProfile(
            student_id=str(row["student_id"]),
            school_year_id=str(row["school_year_id"]),
            mode=DocumentationSubjectMode(str(row["mode"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def list_selected_subject_ids(
        self,
        student_id: str,
        school_year_id: str,
    ) -> tuple[str, ...]:
        rows = self.connection.execute(
            """
            SELECT subject_id
            FROM student_documentation_subject_selections
            WHERE student_id = ? AND school_year_id = ?
            ORDER BY subject_id
            """,
            (student_id, school_year_id),
        ).fetchall()
        return tuple(str(row["subject_id"]) for row in rows)

    def configuration(
        self,
        student_id: str,
        school_year_id: str,
    ) -> StudentDocumentationSubjectConfiguration:
        profile = self.get_profile(student_id, school_year_id)
        mode = (
            profile.mode
            if profile is not None
            else DocumentationSubjectMode.INHERIT
        )
        selected = (
            self.list_selected_subject_ids(student_id, school_year_id)
            if mode is DocumentationSubjectMode.CUSTOM
            else ()
        )
        return StudentDocumentationSubjectConfiguration(
            student_id=student_id,
            school_year_id=school_year_id,
            mode=mode,
            selected_subject_ids=self.sort_subject_ids(selected),
            profile=profile,
        )

    def global_documentation_subject_ids(self) -> tuple[str, ...]:
        rows = self.connection.execute(
            """
            SELECT subject_id, active
            FROM documentation_subject_settings
            ORDER BY subject_id
            """
        ).fetchall()
        if rows:
            subject_ids = tuple(
                str(row["subject_id"])
                for row in rows
                if bool(row["active"])
            )
        else:
            subject_ids = tuple(
                str(row["subject_id"])
                for row in self.connection.execute(
                    """
                    SELECT subject_id
                    FROM competencies
                    WHERE active = 1
                    GROUP BY subject_id
                    ORDER BY MIN(sort_order), subject_id
                    """
                ).fetchall()
            )
        return self.sort_subject_ids(subject_ids)

    def sort_subject_ids(self, subject_ids: Iterable[str]) -> tuple[str, ...]:
        unique_ids = set(subject_ids)
        if not unique_ids:
            return ()
        rows = self.connection.execute(
            """
            SELECT subject_id, MIN(sort_order) AS subject_sort_order
            FROM competencies
            GROUP BY subject_id
            """
        ).fetchall()
        order = {
            str(row["subject_id"]): int(row["subject_sort_order"])
            for row in rows
        }
        fallback = max(order.values(), default=-1) + 1
        return tuple(
            sorted(
                unique_ids,
                key=lambda subject_id: (order.get(subject_id, fallback), subject_id),
            )
        )

    def insert_profile(
        self,
        student_id: str,
        school_year_id: str,
        mode: DocumentationSubjectMode,
        timestamp: datetime,
    ) -> None:
        value = timestamp.isoformat()
        self.connection.execute(
            """
            INSERT INTO student_documentation_subject_profiles(
                student_id, school_year_id, mode, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, school_year_id, mode.value, value, value),
        )

    def update_profile_mode(
        self,
        student_id: str,
        school_year_id: str,
        mode: DocumentationSubjectMode,
        timestamp: datetime,
    ) -> None:
        cursor = self.connection.execute(
            """
            UPDATE student_documentation_subject_profiles
            SET mode = ?, updated_at = ?
            WHERE student_id = ? AND school_year_id = ?
            """,
            (mode.value, timestamp.isoformat(), student_id, school_year_id),
        )
        if cursor.rowcount != 1:
            raise StudentDocumentationSubjectRepositoryError(
                "documentation_subject_profile_missing"
            )

    def replace_selections(
        self,
        student_id: str,
        school_year_id: str,
        subject_ids: tuple[str, ...],
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM student_documentation_subject_selections
            WHERE student_id = ? AND school_year_id = ?
            """,
            (student_id, school_year_id),
        )
        self.connection.executemany(
            """
            INSERT INTO student_documentation_subject_selections(
                student_id, school_year_id, subject_id
            ) VALUES (?, ?, ?)
            """,
            (
                (student_id, school_year_id, subject_id)
                for subject_id in subject_ids
            ),
        )
