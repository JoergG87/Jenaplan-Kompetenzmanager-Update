"""Final-V3 membership contracts for report and LEG snapshots."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3

import pytest

from src.application.school_year_assignment import ChangeStudentMembership
from src.core.learning_conference import (
    LearningConferenceCompletionError,
    LearningConferenceCompletionErrorCode,
    LearningConferenceCompletionService,
)
from src.core.learning_report import (
    ReportFinalizationError,
    ReportFinalizationService,
)
from src.core.sqlite_store import (
    SQLiteDatabase,
    SQLiteLearningConferenceRepository,
    SQLiteLearningReportRepository,
)
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_LEG_DRAFT_ID,
    SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,
    SYNTHETIC_REPORT_DRAFT_ID,
    SYNTHETIC_STUDENT_IDS,
    create_pre_transition_v3_database,
)


REPORT_DRAFT_ID = SYNTHETIC_REPORT_DRAFT_ID
LEG_DRAFT_ID = SYNTHETIC_LEG_DRAFT_ID
SYNTHETIC_SCHOOL_YEAR_ID = SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID
create_synthetic_v3_database = create_pre_transition_v3_database
STUDENT_ID = SYNTHETIC_STUDENT_IDS[0]
SWITCH_DATE = date(2026, 2, 1)
NOW = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)


def _connection_factory(path: Path):
    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    return connect


@pytest.fixture
def v3_report_leg_database(tmp_path: Path) -> tuple[Path, SQLiteDatabase]:
    path = create_synthetic_v3_database(
        tmp_path / "v3-report-leg-membership.sqlite"
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE report_draft_subjects
            SET strengths_text = ?
            WHERE report_draft_id = ? AND subject_id = 'SUB-TEST-DE'
            """,
            (
                "Synthetischer, bewusst verantworteter Fachtext.",
                REPORT_DRAFT_ID,
            ),
        )
        connection.execute(
            """
            UPDATE learning_conference_drafts
            SET agreed_goals_text = ?
            WHERE learning_conference_draft_id = ?
            """,
            ("Synthetisches gemeinsames Ziel.", LEG_DRAFT_ID),
        )
    return (
        path,
        SQLiteDatabase(
            path,
            create=False,
            initialize_schema=False,
        ),
    )


def _change_membership(path: Path, *, effective_on: date = SWITCH_DATE) -> None:
    ChangeStudentMembership(
        _connection_factory(path),
        assignment_id_factory=lambda: (
            f"ASG-TEST-SWITCH-{effective_on.isoformat()}"
        ),
        now_provider=lambda: NOW,
    ).execute(
        STUDENT_ID,
        effective_on=effective_on,
        group_id="GRP-TEST-B",
        course_id="CRS-TEST-2",
    )


def _report_service(database: SQLiteDatabase) -> ReportFinalizationService:
    return ReportFinalizationService(
        SQLiteLearningReportRepository(database),
        now=lambda: NOW,
    )


def _leg_service(
    database: SQLiteDatabase,
) -> LearningConferenceCompletionService:
    return LearningConferenceCompletionService(
        SQLiteLearningConferenceRepository(database),
        now=lambda: NOW,
    )


def _update_report_period_end(path: Path, period_end: date) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE report_drafts
            SET period_end = ?, updated_at = ?
            WHERE report_draft_id = ?
            """,
            (period_end.isoformat(), NOW.isoformat(), REPORT_DRAFT_ID),
        )


def _update_conference_date(
    path: Path,
    conference_date: date | None,
) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE learning_conference_drafts
            SET conference_date = ?, updated_at = ?
            WHERE learning_conference_draft_id = ?
            """,
            (
                conference_date.isoformat()
                if conference_date is not None
                else "",
                NOW.isoformat(),
                LEG_DRAFT_ID,
            ),
        )


def _point_drafts_to_unassigned_student(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (
                'STD-TEST-NO-ASSIGNMENT', 'Testkind', 'Ohne Zuordnung',
                '', 1, ?, ?, NULL
            )
            """,
            (NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            """
            UPDATE report_drafts
            SET student_id = 'STD-TEST-NO-ASSIGNMENT', updated_at = ?
            WHERE report_draft_id = ?
            """,
            (NOW.isoformat(), REPORT_DRAFT_ID),
        )
        connection.execute(
            """
            UPDATE learning_conference_drafts
            SET student_id = 'STD-TEST-NO-ASSIGNMENT', updated_at = ?
            WHERE learning_conference_draft_id = ?
            """,
            (NOW.isoformat(), LEG_DRAFT_ID),
        )


def _make_assignment_ambiguous(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER trg_assignments_no_overlap_insert")
        connection.execute(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (
                'ASG-TEST-AMBIGUOUS', ?, ?, 'GRP-TEST-B', 'CRS-TEST-2',
                'enrolled', '2026-01-01', '2026-06-30', ?, ?
            )
            """,
            (
                STUDENT_ID,
                SYNTHETIC_SCHOOL_YEAR_ID,
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )


@pytest.mark.parametrize(
    ("period_end", "expected_group", "expected_course"),
    (
        (date(2026, 1, 31), ("GRP-TEST-A", "Testgruppe A"), ("CRS-TEST-1", "Testkurs 1")),
        (date(2026, 2, 10), ("GRP-TEST-B", "Testgruppe B"), ("CRS-TEST-2", "Testkurs 2")),
    ),
)
def test_report_snapshot_uses_assignment_at_period_end(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
    period_end: date,
    expected_group: tuple[str, str],
    expected_course: tuple[str, str],
) -> None:
    path, database = v3_report_leg_database
    _change_membership(path)
    _update_report_period_end(path, period_end)

    result = _report_service(database).finalize(
        report_draft_id=REPORT_DRAFT_ID,
        finalized_by_display_name="Testlehrkraft",
    )
    snapshot = json.loads(result.revision.snapshot_json)

    assert snapshot["student"]["group"] == {
        "group_id": expected_group[0],
        "group_name": expected_group[1],
    }
    assert snapshot["student"]["course"] == {
        "course_id": expected_course[0],
        "course_name": expected_course[1],
    }


@pytest.mark.parametrize(
    ("conference_date", "expected_group", "expected_course"),
    (
        (date(2026, 1, 31), ("GRP-TEST-A", "Testgruppe A"), ("CRS-TEST-1", "Testkurs 1")),
        (date(2026, 2, 10), ("GRP-TEST-B", "Testgruppe B"), ("CRS-TEST-2", "Testkurs 2")),
    ),
)
def test_leg_snapshot_uses_assignment_at_conference_date(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
    conference_date: date,
    expected_group: tuple[str, str],
    expected_course: tuple[str, str],
) -> None:
    path, database = v3_report_leg_database
    _change_membership(path)
    _update_conference_date(path, conference_date)

    result = _leg_service(database).complete(
        learning_conference_draft_id=LEG_DRAFT_ID
    )
    snapshot = json.loads(result.revision.snapshot_json)

    assert snapshot["student"]["group"] == {
        "group_id": expected_group[0],
        "group_name": expected_group[1],
    }
    assert snapshot["student"]["course"] == {
        "course_id": expected_course[0],
        "course_name": expected_course[1],
    }


def test_report_finalization_blocks_no_assignment(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
) -> None:
    path, database = v3_report_leg_database
    _point_drafts_to_unassigned_student(path)

    with pytest.raises(ReportFinalizationError):
        _report_service(database).finalize(
            report_draft_id=REPORT_DRAFT_ID,
            finalized_by_display_name="Testlehrkraft",
        )


def test_report_finalization_blocks_ambiguous_assignment(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
) -> None:
    path, database = v3_report_leg_database
    _make_assignment_ambiguous(path)

    with pytest.raises(ReportFinalizationError, match="nicht eindeutig"):
        _report_service(database).finalize(
            report_draft_id=REPORT_DRAFT_ID,
            finalized_by_display_name="Testlehrkraft",
        )


def test_leg_completion_blocks_no_assignment(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
) -> None:
    path, database = v3_report_leg_database
    _point_drafts_to_unassigned_student(path)

    with pytest.raises(LearningConferenceCompletionError) as captured:
        _leg_service(database).complete(
            learning_conference_draft_id=LEG_DRAFT_ID
        )

    assert (
        captured.value.code
        is LearningConferenceCompletionErrorCode.ASSIGNMENT_MISSING
    )


def test_leg_completion_blocks_ambiguous_assignment(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
) -> None:
    path, database = v3_report_leg_database
    _make_assignment_ambiguous(path)

    with pytest.raises(LearningConferenceCompletionError) as captured:
        _leg_service(database).complete(
            learning_conference_draft_id=LEG_DRAFT_ID
        )

    assert (
        captured.value.code
        is LearningConferenceCompletionErrorCode.ASSIGNMENT_AMBIGUOUS
    )


def test_report_and_leg_snapshots_stay_immutable_after_later_assignment_change(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
) -> None:
    path, database = v3_report_leg_database
    report_repository = SQLiteLearningReportRepository(database)
    leg_repository = SQLiteLearningConferenceRepository(database)
    report_result = ReportFinalizationService(
        report_repository,
        now=lambda: NOW,
    ).finalize(
        report_draft_id=REPORT_DRAFT_ID,
        finalized_by_display_name="Testlehrkraft",
    )
    leg_result = LearningConferenceCompletionService(
        leg_repository,
        now=lambda: NOW,
    ).complete(learning_conference_draft_id=LEG_DRAFT_ID)
    report_bytes = report_result.revision.snapshot_json.encode("utf-8")
    report_hash = report_result.revision.snapshot_sha256
    leg_bytes = leg_result.revision.snapshot_json.encode("utf-8")
    leg_hash = leg_result.revision.snapshot_sha256

    _change_membership(path, effective_on=date(2026, 3, 1))

    reloaded_report = report_repository.get_revision(
        report_result.revision.learning_report_revision_id
    )
    reloaded_leg = leg_repository.get_revision(
        leg_result.revision.learning_conference_revision_id
    )
    assert reloaded_report is not None
    assert reloaded_leg is not None
    assert reloaded_report.snapshot_json.encode("utf-8") == report_bytes
    assert reloaded_report.snapshot_sha256 == report_hash
    assert reloaded_leg.snapshot_json.encode("utf-8") == leg_bytes
    assert reloaded_leg.snapshot_sha256 == leg_hash


def test_leg_completion_requires_conference_date_before_assignment_resolution(
    v3_report_leg_database: tuple[Path, SQLiteDatabase],
) -> None:
    path, database = v3_report_leg_database
    _update_conference_date(path, None)

    with pytest.raises(LearningConferenceCompletionError) as captured:
        _leg_service(database).complete(
            learning_conference_draft_id=LEG_DRAFT_ID
        )

    assert (
        captured.value.code
        is LearningConferenceCompletionErrorCode.CONFERENCE_DATE_MISSING
    )
