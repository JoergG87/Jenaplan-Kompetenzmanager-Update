"""Atomic SJ-3C.2 execution tests on temporary synthetic Final-V3 only."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import json
import sqlite3

import pytest

from src.application.school_year_transition_execution import (
    ExecuteSchoolYearTransition,
    SchoolYearTransitionExecutionError,
)
from src.application.school_year_transition_plan import (
    school_year_transition_plan_sha256,
)
from src.application.school_year_transition_preview import (
    SchoolYearTransitionPreviewService,
)
from src.core.sqlite_school_year_transition import (
    NO_BACKUP_EVIDENCE_SHA256,
    SchoolYearTransitionExecutionRepository,
)
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v3_database,
)


NOW = datetime(2026, 7, 15, 10, 30, tzinfo=UTC)
TOKEN = "sj-3c2-operation-001"


def _factory(path: Path):
    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    return connect


@pytest.fixture
def v3_database(tmp_path: Path) -> Path:
    return create_synthetic_v3_database(tmp_path / "transition.sqlite")


def _plan(path: Path):
    return SchoolYearTransitionPreviewService(_factory(path)).preview_plan(
        label="2026/27",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 7, 31),
    )


def _resolved_plan(path: Path):
    return _plan(path).repeat_year_level_three(
        SYNTHETIC_STUDENT_IDS[2],
        "CRS-TEST-3",
    )


def _execute(path: Path, plan, token: str = TOKEN):
    return ExecuteSchoolYearTransition(
        _factory(path),
        now_provider=lambda: NOW,
    ).execute(
        plan=plan,
        operation_token=token,
        expected_plan_sha256=school_year_transition_plan_sha256(plan),
    )


def _database_state(path: Path) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            tuple(row)
            for table in (
                "school_years",
                "student_school_year_assignments",
                "school_year_transitions",
            )
            for row in connection.execute(
                f"SELECT '{table}', * FROM {table} ORDER BY 1, 2"
            ).fetchall()
        )


def _historical_assignments(path: Path) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            connection.execute(
                """
                SELECT *
                FROM student_school_year_assignments
                WHERE school_year_id = ?
                ORDER BY assignment_id
                """,
                (SYNTHETIC_SCHOOL_YEAR_ID,),
            ).fetchall()
        )


def _unrelated_records(
    path: Path,
) -> tuple[tuple[str, tuple[tuple[object, ...], ...]], ...]:
    excluded = {
        "school_years",
        "student_school_year_assignments",
        "school_year_transitions",
    }
    with sqlite3.connect(path) as connection:
        tables = tuple(
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
            if str(row[0]) not in excluded
        )
        return tuple(
            (
                table,
                tuple(
                    sorted(
                        (
                            tuple(row)
                            for row in connection.execute(
                                f'SELECT * FROM "{table}"'
                            ).fetchall()
                        ),
                        key=repr,
                    )
                ),
            )
            for table in tables
        )


def test_successful_transition_writes_1_to_2_2_to_3_and_level_3_repeater(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    historical_before = _historical_assignments(v3_database)
    unrelated_before = _unrelated_records(v3_database)

    result = _execute(v3_database, plan)

    assert result.from_school_year_id == SYNTHETIC_SCHOOL_YEAR_ID
    assert result.counts.student_count == 3
    assert result.counts.enrolled_count == 3
    assert result.counts.advance_1_to_2_count == 1
    assert result.counts.advance_2_to_3_count == 1
    assert result.counts.repeat_year_level_three_count == 1
    with sqlite3.connect(v3_database) as connection:
        school_years = connection.execute(
            """
            SELECT school_year_id, status, closed_at
            FROM school_years
            ORDER BY start_date
            """
        ).fetchall()
        assignments = connection.execute(
            """
            SELECT student_id, group_id, course_id, assignment_status
            FROM student_school_year_assignments
            WHERE school_year_id = ?
            ORDER BY student_id
            """,
            (result.to_school_year_id,),
        ).fetchall()
    assert school_years == [
        (SYNTHETIC_SCHOOL_YEAR_ID, "closed", NOW.isoformat()),
        (result.to_school_year_id, "current", None),
    ]
    assert assignments == [
        (SYNTHETIC_STUDENT_IDS[0], "GRP-TEST-A", "CRS-TEST-2", "enrolled"),
        (SYNTHETIC_STUDENT_IDS[1], "GRP-TEST-A", "CRS-TEST-3", "enrolled"),
        (SYNTHETIC_STUDENT_IDS[2], "GRP-TEST-B", "CRS-TEST-3", "enrolled"),
    ]
    assert _historical_assignments(v3_database) == historical_before
    assert _unrelated_records(v3_database) == unrelated_before


def test_exit_and_changed_group_are_written_without_archiving(
    v3_database: Path,
) -> None:
    plan = _plan(v3_database)
    plan = plan.select_other_group(SYNTHETIC_STUDENT_IDS[0], "GRP-TEST-B")
    plan = plan.mark_exited(SYNTHETIC_STUDENT_IDS[2])

    result = _execute(v3_database, plan)

    assert result.counts.exited_count == 1
    assert result.counts.group_change_count == 1
    with sqlite3.connect(v3_database) as connection:
        connection.row_factory = sqlite3.Row
        changed = connection.execute(
            """
            SELECT group_id, course_id, assignment_status
            FROM student_school_year_assignments
            WHERE school_year_id = ? AND student_id = ?
            """,
            (result.to_school_year_id, SYNTHETIC_STUDENT_IDS[0]),
        ).fetchone()
        exited = connection.execute(
            """
            SELECT group_id, course_id, assignment_status
            FROM student_school_year_assignments
            WHERE school_year_id = ? AND student_id = ?
            """,
            (result.to_school_year_id, SYNTHETIC_STUDENT_IDS[2]),
        ).fetchone()
        student = connection.execute(
            "SELECT active, archived_at FROM students WHERE student_id = ?",
            (SYNTHETIC_STUDENT_IDS[2],),
        ).fetchone()
    assert tuple(changed) == ("GRP-TEST-B", "CRS-TEST-2", "enrolled")
    assert tuple(exited) == (None, None, "exited")
    assert tuple(student) == (1, None)


def test_unresolved_plan_is_rejected_before_begin(v3_database: Path) -> None:
    unresolved = _plan(v3_database)
    opened = False

    def forbidden_connection() -> sqlite3.Connection:
        nonlocal opened
        opened = True
        raise AssertionError("connection must not be opened")

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(forbidden_connection).execute(
            plan=unresolved,
            operation_token=TOKEN,
            expected_plan_sha256=school_year_transition_plan_sha256(unresolved),
        )

    assert captured.value.code == "transition_plan_not_fully_resolved"
    assert opened is False


def test_changed_assignment_makes_plan_stale(v3_database: Path) -> None:
    plan = _resolved_plan(v3_database)
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            UPDATE student_school_year_assignments
            SET updated_at = ?
            WHERE assignment_id = 'ASG-TEST-001'
            """,
            ("2026-07-15T09:00:00+00:00",),
        )
    before = _database_state(v3_database)

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        _execute(v3_database, plan)

    assert captured.value.code == "transition_sources_changed"
    assert _database_state(v3_database) == before


class _FailingRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        fail_at: int,
    ) -> None:
        self._delegate = SchoolYearTransitionExecutionRepository(connection)
        self._fail_at = fail_at
        self._write_index = 0

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    def _write(self, method, *args, **kwargs):
        self._write_index += 1
        if self._write_index == self._fail_at:
            raise sqlite3.OperationalError("injected transition write failure")
        return method(*args, **kwargs)

    def close_current_school_year(self, *args, **kwargs):
        return self._write(
            self._delegate.close_current_school_year,
            *args,
            **kwargs,
        )

    def insert_current_school_year(self, *args, **kwargs):
        return self._write(
            self._delegate.insert_current_school_year,
            *args,
            **kwargs,
        )

    def insert_assignment(self, *args, **kwargs):
        return self._write(
            self._delegate.insert_assignment,
            *args,
            **kwargs,
        )

    def insert_transition(self, *args, **kwargs):
        return self._write(
            self._delegate.insert_transition,
            *args,
            **kwargs,
        )

    def verify_written_result(self, *args, **kwargs):
        return self._write(
            self._delegate.verify_written_result,
            *args,
            **kwargs,
        )


@pytest.mark.parametrize("fail_at", range(1, 8))
def test_failure_at_every_write_step_and_final_check_rolls_back_completely(
    v3_database: Path,
    fail_at: int,
) -> None:
    plan = _resolved_plan(v3_database)
    before = _database_state(v3_database)

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(
            _factory(v3_database),
            now_provider=lambda: NOW,
            repository_factory=lambda connection: _FailingRepository(
                connection,
                fail_at=fail_at,
            ),
        ).execute(
            plan=plan,
            operation_token=TOKEN,
            expected_plan_sha256=school_year_transition_plan_sha256(plan),
        )

    assert captured.value.code == "transition_execution_failed"
    assert _database_state(v3_database) == before


def test_receipt_and_identical_retry_are_idempotent(v3_database: Path) -> None:
    plan = _resolved_plan(v3_database)

    first = _execute(v3_database, plan)
    state_after_first = _database_state(v3_database)
    retry = _execute(v3_database, plan)

    assert retry == first
    assert _database_state(v3_database) == state_after_first
    with sqlite3.connect(v3_database) as connection:
        receipt = connection.execute(
            """
            SELECT
                operation_token, plan_sha256, backup_sha256,
                result_counts_json
            FROM school_year_transitions
            """
        ).fetchone()
        receipt_count = connection.execute(
            "SELECT count(*) FROM school_year_transitions"
        ).fetchone()[0]
    assert receipt[0] == TOKEN
    assert receipt[1] == school_year_transition_plan_sha256(plan)
    assert receipt[2] == NO_BACKUP_EVIDENCE_SHA256
    assert json.loads(receipt[3])["student_count"] == 3
    assert "Testkind" not in receipt[3]
    assert receipt_count == 1


def test_divergent_retry_with_same_token_is_rejected(v3_database: Path) -> None:
    original = _resolved_plan(v3_database)
    _execute(v3_database, original)
    divergent = original.select_other_group(
        SYNTHETIC_STUDENT_IDS[0],
        "GRP-TEST-B",
    )
    state = _database_state(v3_database)

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        _execute(v3_database, divergent)

    assert captured.value.code == "transition_operation_token_conflict"
    assert _database_state(v3_database) == state


def test_divergent_plan_for_same_target_year_is_rejected(
    v3_database: Path,
) -> None:
    original = _resolved_plan(v3_database)
    _execute(v3_database, original)
    divergent = original.select_other_group(
        SYNTHETIC_STUDENT_IDS[0],
        "GRP-TEST-B",
    )
    state = _database_state(v3_database)

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        _execute(v3_database, divergent, token="sj-3c2-operation-002")

    assert captured.value.code == "transition_target_school_year_conflict"
    assert _database_state(v3_database) == state


def test_plan_hash_excludes_display_names_but_covers_technical_decisions(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    renamed = replace(
        plan,
        items=tuple(
            replace(item, student_display_name=f"Anzeige {index}")
            for index, item in enumerate(plan.items)
        ),
    )
    changed = plan.select_other_group(
        SYNTHETIC_STUDENT_IDS[0],
        "GRP-TEST-B",
    )

    assert school_year_transition_plan_sha256(renamed) == (
        school_year_transition_plan_sha256(plan)
    )
    assert school_year_transition_plan_sha256(changed) != (
        school_year_transition_plan_sha256(plan)
    )


def test_integrity_and_foreign_keys_are_clean_after_commit(
    v3_database: Path,
) -> None:
    _execute(v3_database, _resolved_plan(v3_database))

    with sqlite3.connect(v3_database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [
            ("ok",)
        ]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
