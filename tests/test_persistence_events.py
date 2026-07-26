"""Focused migration and freshness tests for persistence event ordering."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from unittest import mock

import pytest

from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
    ObservationRepositoryError,
)
from src.core.persistence_events import (
    SQLitePersistenceEventRepository,
)
from src.core.sqlite_store import (
    SQLiteDatabase,
    SQLiteObservationRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    StudentCompetencyConfirmationRecord,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter


STUDENT_ID = "STU-000001"
COMPETENCY_ID = "CMP-000001"


def _database(path: Path) -> SQLiteDatabase:
    database = SQLiteDatabase(path)
    database.initialize_schema()
    with database.connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO groups VALUES ('GRP-001', 'Gruppe', 0, 1)"
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO courses (
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active
            ) VALUES ('CRS-001', 'Kurs', NULL, '', '', 0, 1)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO students (
                student_id, first_name, last_name, group_id, course_id,
                student_notes, active, created_at, updated_at, archived_at
            ) VALUES (?, 'Ada', 'Test', 'GRP-001', 'CRS-001', '', 1, ?, ?, NULL)
            """,
            (STUDENT_ID, "2026-07-01T08:00:00+00:00", "2026-07-01T08:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO competencies (
                competency_id, subject_id, subject_name, subject_full_name,
                official_subject_name, school_context_name, grade_band, label,
                description, learning_stage, learning_area, competency_group,
                source_reference, catalog_status, activation_group_key,
                sort_order, active, catalog_default_active, is_core_subject
            ) VALUES (
                ?, 'deutsch', 'Deutsch', '', '', '', '', 'Lesen', 'Lesen',
                'cross_stage', 'Lesen', 'Text', '', 'current', '', 0, 1, 1, 1
            )
            """,
            (COMPETENCY_ID,),
        )
    return database


def _rating(value: str = "+") -> ObservationCompetencyRatingRecord:
    return ObservationCompetencyRatingRecord(
        COMPETENCY_ID,
        "deutsch",
        "Deutsch",
        "Lesen",
        "Text",
        "Lesen",
        value,
    )


def _observation(
    *,
    observation_id: str = "OBS-000001",
    date: str = "2026-07-01",
    timestamp: str = "2026-07-01T09:00:00+00:00",
    rating: str = "+",
    note: str = "Notiz",
) -> ObservationRecord:
    return ObservationRecord(
        observation_id,
        STUDENT_ID,
        date,
        "deutsch",
        "Unterricht",
        note,
        True,
        timestamp,
        timestamp,
        (_rating(rating),),
    )


def _as_v1(database: SQLiteDatabase) -> None:
    with database.connect() as connection:
        connection.execute("DROP TABLE persistence_events")
        connection.execute("PRAGMA user_version = 1")


def test_empty_v1_migrates_once_to_v2(tmp_path: Path) -> None:
    database = _database(tmp_path / "empty.sqlite")
    _as_v1(database)
    database.initialize_schema()
    database.initialize_schema()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM persistence_events").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("observation_time", "confirmation_time", "expected"),
    (
        ("2026-07-01T08:00:00+00:00", "2026-07-01T09:00:00+00:00", "confirmed"),
        ("2026-07-01T10:00:00+00:00", "2026-07-01T09:00:00+00:00", "newer_observations"),
        ("2026-07-01T09:00:00+00:00", "2026-07-01T09:00:00+00:00", "confirmation_unknown"),
    ),
)
def test_historical_ordering_and_same_second_unknown(
    tmp_path: Path,
    observation_time: str,
    confirmation_time: str,
    expected: str,
) -> None:
    database = _database(tmp_path / f"{expected}.sqlite")
    SQLiteObservationRepository(database).create_observation(
        _observation(timestamp=observation_time)
    )
    SQLiteStudentCompetencyConfirmationRepository(database).upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            confirmation_time,
            "",
        )
    )
    _as_v1(database)
    database.initialize_schema()
    freshness = SQLitePersistenceEventRepository(database).freshness_for_student(
        STUDENT_ID
    )
    assert freshness[COMPETENCY_ID].state == expected


def test_multiple_historical_ties_and_new_confirmation_resolve_unknown(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "ties.sqlite")
    repository = SQLiteObservationRepository(database)
    repository.create_observation(_observation())
    repository.create_observation(
        _observation(observation_id="OBS-000002", rating="-")
    )
    confirmations = SQLiteStudentCompetencyConfirmationRepository(database)
    confirmations.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T09:00:00+00:00",
            "",
        )
    )
    _as_v1(database)
    database.initialize_schema()
    events = SQLitePersistenceEventRepository(database)
    assert events.freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == (
        "confirmation_unknown"
    )
    confirmations.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T09:00:00+00:00",
            "",
        ),
        operation_token="a" * 32,
    )
    assert events.freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == "confirmed"


def test_older_tie_does_not_hide_later_unambiguous_historical_observation(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "older-tie.sqlite")
    observations = SQLiteObservationRepository(database)
    observations.create_observation(
        _observation(timestamp="2026-07-01T09:00:00+00:00")
    )
    observations.create_observation(
        _observation(
            observation_id="OBS-000002",
            timestamp="2026-07-01T10:00:00+00:00",
        )
    )
    SQLiteStudentCompetencyConfirmationRepository(database).upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T09:00:00+00:00",
            "",
        )
    )
    _as_v1(database)
    database.initialize_schema()
    assert SQLitePersistenceEventRepository(
        database
    ).freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == "newer_observations"


def test_invalid_historical_timestamp_is_sticky_until_new_ordered_event(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "invalid-time.sqlite")
    SQLiteObservationRepository(database).create_observation(
        _observation(timestamp="2026-07-01T09:00:00+00:00")
    )
    with database.connect() as connection:
        connection.execute(
            "UPDATE observations SET updated_at = 'kein-zeitpunkt'"
        )
    confirmations = SQLiteStudentCompetencyConfirmationRepository(database)
    confirmations.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T10:00:00+00:00",
            "",
        )
    )
    _as_v1(database)
    database.initialize_schema()
    events = SQLitePersistenceEventRepository(database)
    assert events.freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == (
        "confirmation_unknown"
    )
    confirmations.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T10:00:00+00:00",
            "",
        ),
        operation_token="b" * 32,
    )
    assert events.freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == "confirmed"


@pytest.mark.parametrize("date", ("2020-01-01", "2035-12-31"))
def test_new_observation_sequence_ignores_back_or_future_date(
    tmp_path: Path,
    date: str,
) -> None:
    database = _database(tmp_path / f"{date}.sqlite")
    confirmations = SQLiteStudentCompetencyConfirmationRepository(database)
    confirmations.upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T09:00:00+00:00",
            "",
        )
    )
    SQLiteObservationRepository(database).create_observation(
        _observation(date=date, timestamp="2026-07-01T09:00:00+00:00")
    )
    state = SQLitePersistenceEventRepository(database).freshness_for_student(
        STUDENT_ID
    )[COMPETENCY_ID].state
    assert state == "newer_observations"


def test_confirmation_retry_requires_and_reuses_exact_single_event(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "confirmation-retry.sqlite")
    repository = SQLiteStudentCompetencyConfirmationRepository(database)
    confirmation = StudentCompetencyConfirmationRecord(
        STUDENT_ID,
        COMPETENCY_ID,
        "+",
        "2026-07-01T10:00:00+00:00",
        "",
    )
    token = "c" * 32
    repository.upsert_confirmation(confirmation, operation_token=token)
    repository.upsert_confirmation(confirmation, operation_token=token)
    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM persistence_events WHERE operation_token = ?",
            (token,),
        ).fetchone()[0] == 1


def test_relevant_rating_edit_is_newer_but_note_only_edit_is_not(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "edit.sqlite")
    observations = SQLiteObservationRepository(database)
    original = observations.create_observation(_observation())
    SQLiteStudentCompetencyConfirmationRepository(database).upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T10:00:00+00:00",
            "",
        )
    )
    observations.update_observation(
        replace(
            original,
            note="Korrigierte Notiz",
            updated_at="2026-07-01T11:00:00+00:00",
        )
    )
    events = SQLitePersistenceEventRepository(database)
    assert events.freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == "confirmed"
    observations.update_observation(
        replace(
            original,
            competency_ratings=(_rating("-"),),
            updated_at="2026-07-01T12:00:00+00:00",
        )
    )
    assert events.freshness_for_student(STUDENT_ID)[COMPETENCY_ID].state == (
        "newer_observations"
    )


def test_soft_deactivation_is_a_relevant_ordered_event(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "deactivation.sqlite")
    observations = SQLiteObservationRepository(database)
    observations.create_observation(_observation())
    SQLiteStudentCompetencyConfirmationRepository(database).upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T10:00:00+00:00",
            "",
        )
    )
    observations.deactivate_observation(
        "OBS-000001",
        "2026-07-01T11:00:00+00:00",
    )
    freshness = SQLitePersistenceEventRepository(database).freshness_for_student(
        STUDENT_ID
    )
    assert freshness[COMPETENCY_ID].state == "newer_observations"
    with database.connect() as connection:
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM persistence_events
            WHERE event_kind = 'observation_deactivated'
              AND competency_id = ?
            """,
            (COMPETENCY_ID,),
        ).fetchone()[0] == 1


def test_repeated_soft_deactivation_is_an_exact_noop(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "deactivation-retry.sqlite")
    observations = SQLiteObservationRepository(database)
    observations.create_observation(_observation())
    observations.deactivate_observation(
        "OBS-000001",
        "2026-07-01T11:00:00+00:00",
    )
    with database.connect() as connection:
        before = connection.execute(
            "SELECT COUNT(*) FROM persistence_events"
        ).fetchone()[0]
    observations.deactivate_observation(
        "OBS-000001",
        "2026-07-01T12:00:00+00:00",
    )
    with database.connect() as connection:
        after = connection.execute(
            "SELECT COUNT(*) FROM persistence_events"
        ).fetchone()[0]
    assert after == before


@pytest.mark.parametrize("mode", ("rating_removed", "deactivated", "student_changed"))
def test_relevant_change_without_remaining_old_student_evidence_stays_newer(
    tmp_path: Path,
    mode: str,
) -> None:
    database = _database(tmp_path / f"empty-evidence-{mode}.sqlite")
    observations = SQLiteObservationRepository(database)
    original = observations.create_observation(_observation())
    SQLiteStudentCompetencyConfirmationRepository(database).upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T10:00:00+00:00",
            "",
        )
    )
    if mode == "rating_removed":
        observations.update_observation(
            replace(
                original,
                competency_ratings=(),
                updated_at="2026-07-01T11:00:00+00:00",
            )
        )
    elif mode == "deactivated":
        observations.deactivate_observation(
            original.observation_id,
            "2026-07-01T11:00:00+00:00",
        )
    else:
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO students (
                    student_id, first_name, last_name, group_id, course_id,
                    student_notes, active, created_at, updated_at, archived_at
                ) VALUES (
                    'STU-000002', 'Berta', 'Test', 'GRP-001', 'CRS-001', '',
                    1, '2026-07-01T08:00:00+00:00',
                    '2026-07-01T08:00:00+00:00', NULL
                )
                """
            )
        observations.update_observation(
            replace(
                original,
                student_id="STU-000002",
                updated_at="2026-07-01T11:00:00+00:00",
            )
        )
    adapter = StudentDesktopAdapter(database=database)
    status = next(
        item
        for item in adapter.list_competency_status_projection_for_student(STUDENT_ID)
        if item.competency_id == COMPETENCY_ID
    )
    assert status.documentation_state == "newer_observations"


def test_event_failure_rolls_back_observation_and_event(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "rollback.sqlite")
    original_append = SQLitePersistenceEventRepository.append
    calls = 0

    def fail_after_first(connection: sqlite3.Connection, event: object) -> int:
        nonlocal calls
        sequence = original_append(connection, event)
        calls += 1
        if calls == 1:
            raise RuntimeError("simulierter Abbruch nach Ereignisschreiben")
        return sequence

    with mock.patch.object(
        SQLitePersistenceEventRepository,
        "append",
        side_effect=fail_after_first,
    ):
        with pytest.raises(RuntimeError, match="Abbruch"):
            SQLiteObservationRepository(database).create_observation(_observation())
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM persistence_events").fetchone()[0] == 0


def test_unknown_status_propagates_to_profile_cockpit_report_and_leg(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "projections.sqlite")
    SQLiteObservationRepository(database).create_observation(_observation())
    SQLiteStudentCompetencyConfirmationRepository(database).upsert_confirmation(
        StudentCompetencyConfirmationRecord(
            STUDENT_ID,
            COMPETENCY_ID,
            "+",
            "2026-07-01T09:00:00+00:00",
            "",
        )
    )
    _as_v1(database)
    database.initialize_schema()
    adapter = StudentDesktopAdapter(database=database)
    status = next(
        item
        for item in adapter.list_competency_status_projection_for_student(STUDENT_ID)
        if item.competency_id == COMPETENCY_ID
    )
    assert status.documentation_state == "confirmation_unknown"
    assert status.confirmed_rating == ""
    assert status.documentation_state_label == (
        "Bestätigungsstand unklar – bitte erneut bestätigen"
    )
    cockpit = adapter.competency_cockpit_for_student(STUDENT_ID)
    cockpit_statuses = tuple(
        competency
        for subject in cockpit.subjects
        for area in subject.learning_areas
        for topic in area.topics
        for competency in topic.competencies
    )
    assert any(
        competency.documentation_state == "confirmation_unknown"
        for competency in cockpit_statuses
    )
    report = adapter.learning_report_preparation_for_student(STUDENT_ID)
    assert report is not None
    report_competencies = tuple(
        competency
        for subject in report.subjects
        for competency in subject.competencies
    )
    assert any(
        competency.documentation_state == "confirmation_unknown"
        for competency in report_competencies
    )
    conference = adapter.learning_conference_preparation_for_student(STUDENT_ID)
    assert conference is not None
    conference_competencies = tuple(
        competency
        for subject in conference.subjects
        for competency in subject.competencies
    )
    assert any(
        competency.documentation_state
        == "Bestätigungsstand unklar – bitte erneut bestätigen"
        for competency in conference_competencies
    )
