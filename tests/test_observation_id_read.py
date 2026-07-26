"""Focused regression tests for observation ID allocation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
import time

import pytest

from src.core.database_engine import SQLiteConnectionProvider
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationService,
    ObservationValidator,
)
from src.core.sqlite_store import SQLiteDatabase, SQLiteObservationRepository


STUDENT_A = "STU-000001"
STUDENT_B = "STU-000002"


class _TracingSQLiteConnectionProvider(SQLiteConnectionProvider):
    def __init__(self) -> None:
        self.enabled = False
        self.statements: list[str] = []

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> sqlite3.Connection:
        connection = super().connect(
            path,
            create=create,
            key_material=key_material,
        )
        connection.set_trace_callback(self._trace)
        return connection

    def _trace(self, statement: str) -> None:
        if self.enabled:
            self.statements.append(statement)


def _database(
    path: Path,
    *,
    provider: SQLiteConnectionProvider | None = None,
) -> SQLiteDatabase:
    database = SQLiteDatabase(path, connection_provider=provider)
    database.initialize_schema()
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO groups (group_id, group_name, sort_order, active)
            VALUES ('GRP-001', 'Gruppe 1', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO courses (
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active
            )
            VALUES ('CRS-001', 'Kurs 1', NULL, '', '', 1, 1)
            """
        )
        connection.executemany(
            """
            INSERT INTO students (
                student_id, first_name, last_name, group_id, course_id,
                student_notes, active, created_at, updated_at, archived_at
            )
            VALUES (?, ?, 'Test', 'GRP-001', 'CRS-001', '', 1, ?, ?, NULL)
            """,
            (
                (STUDENT_A, "Ada", "2026-07-26T08:00:00+00:00", "2026-07-26T08:00:00+00:00"),
                (STUDENT_B, "Berta", "2026-07-26T08:00:00+00:00", "2026-07-26T08:00:00+00:00"),
            ),
        )
    return database


def _rating(
    competency_id: str,
    rating: str,
) -> ObservationCompetencyRatingRecord:
    return ObservationCompetencyRatingRecord(
        competency_id,
        "deutsch",
        "Deutsch",
        "Lesen",
        "Texte",
        f"Kompetenz {competency_id}",
        rating,
    )


def _service(
    database: SQLiteDatabase,
    *,
    student_ids: tuple[str, ...] = (STUDENT_A, STUDENT_B),
) -> ObservationService:
    return ObservationService(
        SQLiteObservationRepository(database),
        ObservationValidator(),
        student_ids,
        now_provider=lambda: datetime(2026, 7, 26, 10, 0, tzinfo=UTC),
    )


def _create(
    service: ObservationService,
    *,
    student_id: str = STUDENT_A,
    ratings: tuple[ObservationCompetencyRatingRecord, ...] | None = None,
):
    return service.create_observation(
        student_id=student_id,
        date="2026-07-26",
        subject_id="deutsch",
        context="Unterricht",
        note="Gezielte Beobachtung.",
        competency_ratings=ratings or (_rating("CMP-000001", "+"),),
    )


def test_create_returns_own_ids_for_consecutive_students_and_multiple_ratings(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "consecutive.sqlite")
    service = _service(database)

    first = _create(
        service,
        ratings=(
            _rating("CMP-000001", "+"),
            _rating("CMP-000002", "++"),
        ),
    )
    second = _create(service, student_id=STUDENT_B)

    assert first.observation_id == "OBS-000001"
    assert second.observation_id == "OBS-000002"
    assert len(first.competency_ratings) == 2
    assert SQLiteObservationRepository(database).get_observation(
        first.observation_id
    ) == first


def test_edit_preserves_observation_id(tmp_path: Path) -> None:
    database = _database(tmp_path / "edit.sqlite")
    service = _service(database)
    created = _create(service)

    updated = service.update_observation(
        observation_id=created.observation_id,
        student_id=STUDENT_A,
        date="2026-07-27",
        subject_id="deutsch",
        context="Lernzeit",
        note="Bearbeitet.",
        competency_ratings=(_rating("CMP-000002", "++"),),
    )

    assert updated.observation_id == created.observation_id
    assert updated.note == "Bearbeitet."


def test_database_failure_does_not_return_or_persist_an_observation(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "failure.sqlite")
    with database.connect() as connection:
        connection.execute("DELETE FROM students WHERE student_id = ?", (STUDENT_A,))

    with pytest.raises(sqlite3.IntegrityError):
        _create(_service(database, student_ids=(STUDENT_A,)))

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM persistence_events").fetchone()[0] == 0


def test_separate_connections_allocate_distinct_ids_under_concurrent_create(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path / "concurrent.sqlite")
    services = (_service(database), _service(database))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(_create, services[0], student_id=STUDENT_A),
            pool.submit(_create, services[1], student_id=STUDENT_B),
        )
        created = tuple(future.result(timeout=5) for future in futures)

    assert {item.observation_id for item in created} == {
        "OBS-000001",
        "OBS-000002",
    }
    assert {item.student_id for item in created} == {STUDENT_A, STUDENT_B}


@pytest.mark.parametrize("existing_count", (18_000, 120_000))
def test_id_read_query_budget_is_constant_without_rating_hydration(
    tmp_path: Path,
    existing_count: int,
) -> None:
    provider = _TracingSQLiteConnectionProvider()
    database = _database(tmp_path / f"budget-{existing_count}.sqlite", provider=provider)
    with database.connect() as connection:
        connection.executemany(
            """
            INSERT INTO observations (
                observation_id, student_id, date, subject_id, context, note,
                active, created_at, updated_at
            )
            VALUES (?, ?, '2026-07-25', 'deutsch', '', '', 1, ?, ?)
            """,
            (
                (
                    f"OBS-{number:06d}",
                    STUDENT_A if number % 2 else STUDENT_B,
                    "2026-07-25T08:00:00+00:00",
                    "2026-07-25T08:00:00+00:00",
                )
                for number in range(1, existing_count + 1)
            ),
        )

    provider.statements.clear()
    provider.enabled = True
    started = time.perf_counter()
    created = _create(_service(database))
    elapsed = time.perf_counter() - started
    provider.enabled = False

    select_statements = tuple(
        statement
        for statement in provider.statements
        if statement.lstrip().upper().startswith("SELECT")
    )
    assert created.observation_id == f"OBS-{existing_count + 1:06d}"
    assert len(select_statements) == 1
    assert "SELECT observation_id" in select_statements[0]
    assert "observation_competency_ratings" not in select_statements[0]
    assert elapsed < 2.0
