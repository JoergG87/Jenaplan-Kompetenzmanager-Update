"""Focused tests for direct creation of the only product schema."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from src.core.database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityStatus,
)
from src.core.final_v3_schema import (
    FinalV3SchemaError,
    FinalV3SchemaInitializer,
)
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_COURSE_GROUP_ID,
    SYNTHETIC_DOCUMENT_IDS,
    SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,
    SYNTHETIC_LEG_DRAFT_ID,
    SYNTHETIC_REPORT_DRAFT_ID,
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v3_database,
)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_direct_initializer_creates_exact_registered_final_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "final-v3.sqlite"

    FinalV3SchemaInitializer().initialize(path)

    result = DatabaseCompatibilityInspector().inspect(path)
    assert result.status is DatabaseCompatibilityStatus.EXACT
    assert result.version.sqlite_user_version == FINAL_SCHEMA_VERSION == 3
    assert result.schema_identity.fingerprint == FINAL_SCHEMA_FINGERPRINT
    assert result.schema_identity.object_count == 95


def test_direct_initializer_rejects_every_existing_target(tmp_path: Path) -> None:
    path = tmp_path / "existing.sqlite"
    path.write_bytes(b"existing")

    with pytest.raises(FinalV3SchemaError, match="final_v3_target_must_not_exist"):
        FinalV3SchemaInitializer().initialize(path)

    assert path.read_bytes() == b"existing"


def test_final_schema_has_v3_student_course_and_membership_shape(
    tmp_path: Path,
) -> None:
    path = tmp_path / "shape.sqlite"
    FinalV3SchemaInitializer().initialize(path)

    with _connect(path) as connection:
        student_columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(students)")
        }
        course_columns = {
            str(row[1]): int(row[3])
            for row in connection.execute("PRAGMA table_info(courses)")
        }
        assignment_columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(student_school_year_assignments)"
            )
        }

    assert "group_id" not in student_columns
    assert "course_id" not in student_columns
    assert course_columns["year_level"] == 1
    assert {
        "assignment_id",
        "student_id",
        "school_year_id",
        "group_id",
        "course_id",
        "assignment_status",
        "valid_from",
        "valid_to",
    }.issubset(assignment_columns)


def test_transition_requires_real_from_school_year(tmp_path: Path) -> None:
    path = create_synthetic_v3_database(tmp_path / "transition.sqlite")

    with _connect(path) as connection:
        from_column = next(
            row
            for row in connection.execute(
                "PRAGMA table_info(school_year_transitions)"
            )
            if row[1] == "from_school_year_id"
        )
        assert int(from_column[3]) == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_year_transitions(
                    transition_id, from_school_year_id, to_school_year_id,
                    operation_token, plan_sha256, backup_sha256,
                    result_counts_json, completed_at
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "TRN-TEST-NULL",
                    SYNTHETIC_SCHOOL_YEAR_ID,
                    "token-null",
                    "a" * 64,
                    "b" * 64,
                    "{}",
                    "2026-07-31T12:00:00+00:00",
                ),
            )


def test_initial_creation_writes_no_transition_receipt(tmp_path: Path) -> None:
    path = create_synthetic_v3_database(tmp_path / "no-transition.sqlite")

    with _connect(path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM school_year_transitions"
        ).fetchone()[0] == 0


def test_school_year_constraints_reject_second_current_and_overlap(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "school-years.sqlite")

    with _connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_years(
                    school_year_id, label, start_date, end_date,
                    status, created_at, closed_at
                ) VALUES (?, ?, ?, ?, 'current', ?, NULL)
                """,
                (
                    "SY-TEST-SECOND-CURRENT",
                    "2026/27",
                    "2026-08-01",
                    "2027-07-31",
                    "2026-06-01T08:00:00+00:00",
                ),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_years(
                    school_year_id, label, start_date, end_date,
                    status, created_at, closed_at
                ) VALUES (?, ?, ?, ?, 'planned', ?, NULL)
                """,
                (
                    "SY-TEST-OVERLAP",
                    "Überlappung",
                    "2026-07-01",
                    "2027-06-30",
                    "2026-06-01T08:00:00+00:00",
                ),
            )


def test_assignment_constraints_reject_outside_and_overlapping_intervals(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "assignments.sqlite")

    with _connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'enrolled', ?, ?, ?, ?)
                """,
                (
                    "ASG-TEST-OUTSIDE",
                    SYNTHETIC_STUDENT_IDS[0],
                    SYNTHETIC_SCHOOL_YEAR_ID,
                    "GRP-TEST-A",
                    "CRS-TEST-1",
                    "2025-07-31",
                    "2025-07-31",
                    "2025-07-01T10:00:00+00:00",
                    "2025-07-01T10:00:00+00:00",
                ),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'enrolled', ?, ?, ?, ?)
                """,
                (
                    "ASG-TEST-OVERLAP",
                    SYNTHETIC_STUDENT_IDS[0],
                    SYNTHETIC_SCHOOL_YEAR_ID,
                    "GRP-TEST-A",
                    "CRS-TEST-1",
                    "2026-01-01",
                    "2026-01-31",
                    "2025-07-01T10:00:00+00:00",
                    "2025-07-01T10:00:00+00:00",
                ),
            )


def test_transition_receipts_are_immutable(tmp_path: Path) -> None:
    path = create_synthetic_v3_database(tmp_path / "immutable.sqlite")

    with _connect(path) as connection:
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (?, ?, ?, ?, 'planned', ?, NULL)
            """,
            (
                    "SY-TEST-2027-28",
                    "2027/28",
                    "2027-08-01",
                    "2028-07-31",
                    "2027-06-01T08:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO school_year_transitions(
                transition_id, from_school_year_id, to_school_year_id,
                operation_token, plan_sha256, backup_sha256,
                result_counts_json, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "TRN-TEST-001",
                SYNTHETIC_SCHOOL_YEAR_ID,
                "SY-TEST-2027-28",
                "token-001",
                "a" * 64,
                "b" * 64,
                "{}",
                "2027-07-31T12:00:00+00:00",
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE school_year_transitions
                SET result_counts_json = '{"changed":1}'
                WHERE transition_id = 'TRN-TEST-001'
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                DELETE FROM school_year_transitions
                WHERE transition_id = 'TRN-TEST-001'
                """
            )


def test_synthetic_seed_is_complete_and_deterministic(tmp_path: Path) -> None:
    first = create_synthetic_v3_database(tmp_path / "first.sqlite")
    second = create_synthetic_v3_database(tmp_path / "second.sqlite")
    queries = (
        "SELECT * FROM school_years ORDER BY school_year_id",
        "SELECT * FROM courses ORDER BY course_id",
        "SELECT * FROM groups ORDER BY group_id",
        "SELECT * FROM students ORDER BY student_id",
        "SELECT * FROM course_groups ORDER BY course_group_id",
        """
        SELECT * FROM course_group_student_groups
        ORDER BY course_group_id, student_group_id
        """,
        """
        SELECT * FROM course_group_courses
        ORDER BY course_group_id, course_id
        """,
        """
        SELECT * FROM student_school_year_assignments
        ORDER BY assignment_id
        """,
        "SELECT * FROM observations ORDER BY observation_id",
        "SELECT * FROM documents ORDER BY document_id",
        """
        SELECT * FROM student_competency_confirmations
        ORDER BY student_id, competency_id
        """,
        "SELECT * FROM report_drafts ORDER BY report_draft_id",
        """
        SELECT * FROM report_draft_subjects
        ORDER BY report_draft_id, subject_id
        """,
        """
        SELECT * FROM report_draft_competencies
        ORDER BY report_draft_id, competency_id
        """,
        """
        SELECT * FROM report_draft_observations
        ORDER BY report_draft_id, observation_id
        """,
        """
        SELECT * FROM report_draft_charts
        ORDER BY report_draft_id, subject_id, chart_type
        """,
        """
        SELECT * FROM learning_conference_drafts
        ORDER BY learning_conference_draft_id
        """,
        """
        SELECT * FROM learning_conference_draft_subjects
        ORDER BY learning_conference_draft_id, subject_id
        """,
        """
        SELECT * FROM learning_conference_draft_cross_topics
        ORDER BY learning_conference_draft_id, cross_topic_key
        """,
        """
        SELECT * FROM learning_conference_draft_competencies
        ORDER BY learning_conference_draft_id, competency_id
        """,
        """
        SELECT * FROM learning_conference_draft_observations
        ORDER BY learning_conference_draft_id, observation_id
        """,
    )

    with _connect(first) as left, _connect(second) as right:
        for query in queries:
            assert left.execute(query).fetchall() == right.execute(query).fetchall()
        assert left.execute(
            """
            SELECT COUNT(*) FROM students AS student
            WHERE NOT EXISTS (
                SELECT 1
                FROM student_school_year_assignments AS assignment
                WHERE assignment.student_id = student.student_id
                  AND assignment.school_year_id = ?
                  AND assignment.assignment_status = 'enrolled'
                  AND assignment.valid_from = '2026-08-01'
                  AND assignment.valid_to = '2027-07-31'
            )
            """,
            (SYNTHETIC_SCHOOL_YEAR_ID,),
        ).fetchone()[0] == 0
        assert left.execute(
            "SELECT year_level FROM courses ORDER BY year_level"
        ).fetchall() == [(1,), (2,), (3,)]


def test_synthetic_seed_has_only_final_v3_membership_shape(tmp_path: Path) -> None:
    path = create_synthetic_v3_database(tmp_path / "shape-seed.sqlite")
    compatibility = DatabaseCompatibilityInspector().inspect(path)

    with _connect(path) as connection:
        student_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(students)")
        }
        current_school_year = connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years
            WHERE status = 'current'
            """
        ).fetchall()

    assert "group_id" not in student_columns
    assert "course_id" not in student_columns
    assert "student_notes" not in student_columns
    assert "notes" in student_columns
    assert compatibility.status is DatabaseCompatibilityStatus.EXACT
    assert compatibility.schema_identity.fingerprint == FINAL_SCHEMA_FINGERPRINT
    assert current_school_year == [
        (
            SYNTHETIC_SCHOOL_YEAR_ID,
            "2026/27",
            "2026-08-01",
            "2027-07-31",
            "current",
        )
    ]
    with _connect(path) as connection:
        assert connection.execute(
            """
            SELECT label, start_date, end_date, status
            FROM school_years
            WHERE school_year_id = ?
            """,
            (SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,),
        ).fetchone() == (
            "2025/26",
            "2025-08-01",
            "2026-07-31",
            "closed",
        )


def test_synthetic_seed_covers_scopes_documents_and_workflows(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "coverage.sqlite")

    with _connect(path) as connection:
        course_group_relations = connection.execute(
            """
            SELECT student_group_id, course_id
            FROM course_group_student_groups
            CROSS JOIN course_group_courses USING (course_group_id)
            WHERE course_group_id = ?
            ORDER BY student_group_id, course_id
            """,
            (SYNTHETIC_COURSE_GROUP_ID,),
        ).fetchall()
        documents = connection.execute(
            """
            SELECT document_id, student_id, observation_id, active
            FROM documents
            ORDER BY document_id
            """
        ).fetchall()
        report_relations = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM report_draft_subjects
                 WHERE report_draft_id = ?),
                (SELECT COUNT(*) FROM report_draft_competencies
                 WHERE report_draft_id = ?),
                (SELECT COUNT(*) FROM report_draft_observations
                 WHERE report_draft_id = ?),
                (SELECT COUNT(*) FROM report_draft_charts
                 WHERE report_draft_id = ?)
            """,
            (SYNTHETIC_REPORT_DRAFT_ID,) * 4,
        ).fetchone()
        leg_relations = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM learning_conference_draft_subjects
                 WHERE learning_conference_draft_id = ?),
                (SELECT COUNT(*) FROM learning_conference_draft_cross_topics
                 WHERE learning_conference_draft_id = ?),
                (SELECT COUNT(*) FROM learning_conference_draft_competencies
                 WHERE learning_conference_draft_id = ?),
                (SELECT COUNT(*) FROM learning_conference_draft_observations
                 WHERE learning_conference_draft_id = ?)
            """,
            (SYNTHETIC_LEG_DRAFT_ID,) * 4,
        ).fetchone()

    assert course_group_relations == [
        ("GRP-TEST-A", "CRS-TEST-1"),
        ("GRP-TEST-A", "CRS-TEST-2"),
        ("GRP-TEST-A", "CRS-TEST-3"),
        ("GRP-TEST-B", "CRS-TEST-1"),
        ("GRP-TEST-B", "CRS-TEST-2"),
        ("GRP-TEST-B", "CRS-TEST-3"),
    ]
    assert documents == [
        (
            SYNTHETIC_DOCUMENT_IDS[0],
            SYNTHETIC_STUDENT_IDS[0],
            "OBS-TEST-001",
            1,
        ),
        (
            SYNTHETIC_DOCUMENT_IDS[1],
            SYNTHETIC_STUDENT_IDS[1],
            None,
            1,
        ),
    ]
    assert report_relations == (1, 1, 1, 1)
    assert leg_relations == (1, 1, 1, 1)
