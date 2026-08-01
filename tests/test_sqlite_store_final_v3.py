"""Focused Final-V3 checks for the shared SQLite store facade."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.core.database_compatibility import (
    DatabaseCompatibilityError,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityStatus,
)
from src.core.records import (
    HISTORICAL_SCHOOL_YEAR_END,
    HISTORICAL_SCHOOL_YEAR_START,
    SCHOOL_YEAR_END,
    SCHOOL_YEAR_START,
    seed_reference_data,
)
from src.core.sqlite_store import (
    SQLiteDatabase,
    SQLiteStudentRepository,
    create_sqlite_seed_database,
)


def test_initialize_schema_creates_and_accepts_only_exact_final_v3(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh-final-v3.sqlite"
    database = SQLiteDatabase(database_path)

    database.initialize_schema()
    database.initialize_schema()

    result = DatabaseCompatibilityInspector().inspect(database_path)
    assert result.status is DatabaseCompatibilityStatus.EXACT
    with sqlite3.connect(database_path) as connection:
        student_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(students)")
        }
        course_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(courses)")
        }
    assert "notes" in student_columns
    assert "student_notes" not in student_columns
    assert "group_id" not in student_columns
    assert "course_id" not in student_columns
    assert "year_level" in course_columns


def test_initialize_schema_rejects_existing_legacy_shape_without_mutation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE students(
                student_id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                course_id TEXT NOT NULL
            )
            """
        )
        connection.execute("PRAGMA user_version = 2")

    with pytest.raises(DatabaseCompatibilityError):
        SQLiteDatabase(database_path).initialize_schema()

    with sqlite3.connect(database_path) as connection:
        columns = tuple(
            str(row[1])
            for row in connection.execute("PRAGMA table_info(students)")
        )
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    assert columns == ("student_id", "group_id", "course_id")
    assert version == 2


def test_seed_database_contains_complete_deterministic_final_v3_memberships(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "seed-a.sqlite"
    second_path = tmp_path / "seed-b.sqlite"
    create_sqlite_seed_database(first_path)
    create_sqlite_seed_database(second_path)

    first_snapshot = _membership_snapshot(first_path)
    second_snapshot = _membership_snapshot(second_path)

    assert first_snapshot == second_snapshot
    school_years, courses, students, assignments, transitions = first_snapshot
    assert school_years == (
        (
            "SY-TEST-2025-26",
            "2025/26",
            HISTORICAL_SCHOOL_YEAR_START.isoformat(),
            HISTORICAL_SCHOOL_YEAR_END.isoformat(),
            "closed",
        ),
        (
            "SY-TEST-2026-27",
            "2026/27",
            SCHOOL_YEAR_START.isoformat(),
            SCHOOL_YEAR_END.isoformat(),
            "current",
        ),
    )
    assert tuple(row[-1] for row in courses) == (1, 2, 3)
    assert len(students) == 28
    assert len(assignments) == 2 * len(students)
    assert all(row[5] == "enrolled" for row in assignments)
    assert sum(row[2] == "SY-TEST-2025-26" for row in assignments) == len(students)
    assert sum(row[2] == "SY-TEST-2026-27" for row in assignments) == len(students)
    assert transitions == ()


def test_seed_data_refuses_to_overwrite_existing_final_v3_rows(
    tmp_path: Path,
) -> None:
    database = create_sqlite_seed_database(tmp_path / "seed.sqlite")
    with pytest.raises(RuntimeError, match="vollstaendig leere Datenbank"):
        database.replace_seed_data(seed_reference_data())

    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM students").fetchone()[0] == 28
        assert (
            connection.execute(
                "SELECT count(*) FROM student_school_year_assignments"
            ).fetchone()[0]
            == 56
        )


def test_sqlite_student_repository_exposes_no_legacy_writer_methods() -> None:
    assert not hasattr(SQLiteStudentRepository, "create_student")
    assert not hasattr(SQLiteStudentRepository, "update_student")
    assert not hasattr(SQLiteStudentRepository, "archive_student")


def _membership_snapshot(
    database_path: Path,
) -> tuple[
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
]:
    with sqlite3.connect(database_path) as connection:
        return (
            tuple(
                connection.execute(
                    """
                    SELECT school_year_id, label, start_date, end_date, status
                    FROM school_years
                    ORDER BY school_year_id
                    """
                )
            ),
            tuple(
                connection.execute(
                    """
                    SELECT course_id, course_name, active, year_level
                    FROM courses
                    ORDER BY sort_order, course_id
                    """
                )
            ),
            tuple(
                connection.execute(
                    """
                    SELECT
                        student_id, first_name, last_name, notes, active,
                        created_at, updated_at, archived_at
                    FROM students
                    ORDER BY student_id
                    """
                )
            ),
            tuple(
                connection.execute(
                    """
                    SELECT
                        assignment_id, student_id, school_year_id, group_id,
                        course_id, assignment_status, valid_from, valid_to,
                        created_at, updated_at
                    FROM student_school_year_assignments
                    ORDER BY assignment_id
                    """
                )
            ),
            tuple(
                connection.execute(
                    """
                    SELECT transition_id
                    FROM school_year_transitions
                    ORDER BY transition_id
                    """
                )
            ),
        )
