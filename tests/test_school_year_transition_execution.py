"""Atomic SJ-3C.2 execution tests on temporary synthetic Final-V3 only."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import json
import sqlite3
import threading

import pytest

from src.application.school_year_transition_execution import (
    ExecuteSchoolYearTransition,
    SchoolYearTransitionExecutionError,
)
from src.application.commands.school_year_transition_backup import (
    SchoolYearTransitionBackupEvidence,
    VerifiedSchoolYearTransitionBackupAdapter,
)
from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
)
from src.application.school_year_transition_plan import (
    school_year_transition_plan_sha256,
)
from src.application.school_year_transition_preview import (
    SchoolYearTransitionPreviewService,
)
from src.application.school_year_transition_step_up import (
    SchoolYearTransitionStepUpService,
)
from src.core.database_compatibility import FINAL_SCHEMA_FINGERPRINT
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
    SchoolYearTransitionRepositoryError,
)
from src.core.maintenance_gate import (
    MaintenanceGate,
    MaintenancePurpose,
    MaintenanceState,
    MaintenanceWriterBlockedError,
)
from src.desktop_app.runtime import runtime_paths
from src.security.application import AuthenticationResult
from src.security.domain import AuthenticationStatus
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v3_database,
)


NOW = datetime(2026, 7, 15, 10, 30, tzinfo=UTC)
TOKEN = "sj-3c2-operation-001"
MAINTENANCE_OWNER = "school-year-transition-test"
BACKUP_SHA256 = "b" * 64
BACKUP_ID = "SYB-0123456789abcdef0123456789abcdef"
AUTHORIZATION_ID = "SYA-0123456789abcdef0123456789abcdef"


class _SuccessfulPasswordService:
    def authenticate_password(self, password: str) -> AuthenticationResult:
        return AuthenticationResult(AuthenticationStatus.AUTHENTICATED)


class _VerifiedBackupService:
    def __init__(
        self,
        *,
        evidence: SchoolYearTransitionBackupEvidence | None = None,
        error: Exception | None = None,
        after_backup=None,
        evidence_changes: dict[str, object] | None = None,
        source_state_sha256: str | None = None,
    ) -> None:
        self.evidence = evidence
        self.error = error
        self.after_backup = after_backup
        self.evidence_changes = evidence_changes or {}
        self.source_state_sha256 = source_state_sha256

    def create_and_verify(self):
        if self.error is not None:
            raise self.error
        if self.after_backup is not None:
            self.after_backup()
        if self.evidence is not None:
            return self.evidence
        evidence = SchoolYearTransitionBackupEvidence(
            backup_id=BACKUP_ID,
            backup_sha256=BACKUP_SHA256,
            source_state_sha256=self.source_state_sha256 or "f" * 64,
            source_schema_fingerprint=FINAL_SCHEMA_FINGERPRINT,
            verified_at=NOW,
        )
        return replace(evidence, **self.evidence_changes)


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


def _step_up(plan):
    service = SchoolYearTransitionStepUpService(
        _SuccessfulPasswordService(),
        now_provider=lambda: NOW,
        authorization_id_provider=lambda: AUTHORIZATION_ID,
    )
    result = service.authenticate(plan=plan, password="test-password")
    assert result.authorization is not None
    return service, result.authorization


def _execute(path: Path, plan, token: str = TOKEN):
    gate = MaintenanceGate()
    step_up_service, authorization = _step_up(plan)
    return ExecuteSchoolYearTransition(
        _factory(path),
        maintenance_gate=gate,
        step_up_service=step_up_service,
        backup_service=_VerifiedBackupService(
            source_state_sha256=plan.source_sha256
        ),
        now_provider=lambda: NOW,
    ).execute(
        plan=plan,
        operation_token=token,
        expected_plan_sha256=school_year_transition_plan_sha256(plan),
        step_up_authorization=authorization,
        maintenance_owner_id=MAINTENANCE_OWNER,
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

    assert "test-password" not in repr(result)
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


def test_real_verified_backup_allows_transition_and_binds_receipt(
    tmp_path: Path,
) -> None:
    paths = runtime_paths(tmp_path / "runtime")
    for directory in (paths.root, paths.documents, paths.backups):
        directory.mkdir(parents=True, exist_ok=True)
    create_synthetic_v3_database(paths.database)
    plan = _resolved_plan(paths.database)
    adapter = VerifiedSchoolYearTransitionBackupAdapter(
        service=BackupApplicationService(now=lambda: NOW),
        command=CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version="0.3.0",
            build_commit="0ba4a93d47bc318679496987d445c83816a16b4f",
            source_tree_state="clean",
        ),
        now_provider=lambda: NOW,
        backup_id_provider=lambda: BACKUP_ID,
    )

    class _RecordingBackupService:
        evidence = None

        def create_and_verify(self):
            self.evidence = adapter.create_and_verify()
            return self.evidence

    backup_service = _RecordingBackupService()
    gate, execute = _execute_with_backup_service(
        paths.database,
        plan,
        backup_service,
    )

    result = execute()

    evidence = backup_service.evidence
    assert evidence is not None
    assert evidence.backup_id == BACKUP_ID
    assert evidence.backup_sha256 == result.backup_sha256
    assert evidence.source_state_sha256 == plan.source_sha256
    assert evidence.source_schema_fingerprint == FINAL_SCHEMA_FINGERPRINT
    assert evidence.verified_at == NOW
    assert evidence.backup_sha256 != "0" * 64
    with sqlite3.connect(paths.database) as connection:
        receipt_hash = connection.execute(
            "SELECT backup_sha256 FROM school_year_transitions"
        ).fetchone()[0]
    assert receipt_hash == evidence.backup_sha256
    assert gate.state is MaintenanceState.NORMAL


def test_backup_of_different_database_cannot_authorize_transition(
    tmp_path: Path,
) -> None:
    source_paths = runtime_paths(tmp_path / "source-runtime")
    other_paths = runtime_paths(tmp_path / "other-runtime")
    for paths in (source_paths, other_paths):
        for directory in (paths.root, paths.documents, paths.backups):
            directory.mkdir(parents=True, exist_ok=True)
        create_synthetic_v3_database(paths.database)
    with sqlite3.connect(other_paths.database) as connection:
        connection.execute(
            "UPDATE groups SET active = 0 WHERE group_id = 'GRP-TEST-B'"
        )
    plan = _resolved_plan(source_paths.database)
    before = _database_state(source_paths.database)
    adapter = VerifiedSchoolYearTransitionBackupAdapter(
        service=BackupApplicationService(now=lambda: NOW),
        command=CreateBackupCommand(
            database_path=other_paths.database,
            runtime_paths=other_paths,
            target_path=other_paths.backups,
            app_version="0.3.0",
            build_commit="0ba4a93d47bc318679496987d445c83816a16b4f",
        ),
        now_provider=lambda: NOW,
        backup_id_provider=lambda: BACKUP_ID,
    )
    gate, execute = _execute_with_backup_service(
        source_paths.database,
        plan,
        adapter,
    )

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == "transition_backup_source_state_mismatch"
    assert _database_state(source_paths.database) == before
    assert gate.state is MaintenanceState.NORMAL


def test_pending_observation_recovery_blocks_transition_backup(
    tmp_path: Path,
) -> None:
    paths = runtime_paths(tmp_path / "runtime")
    for directory in (paths.root, paths.documents, paths.backups):
        directory.mkdir(parents=True, exist_ok=True)
    create_synthetic_v3_database(paths.database)
    pending = paths.root / ".observation-staging" / ("a" * 32)
    pending.mkdir(parents=True)
    plan = _resolved_plan(paths.database)
    before = _database_state(paths.database)
    adapter = VerifiedSchoolYearTransitionBackupAdapter(
        service=BackupApplicationService(now=lambda: NOW),
        command=CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version="0.3.0",
            build_commit="0ba4a93d47bc318679496987d445c83816a16b4f",
        ),
        now_provider=lambda: NOW,
        backup_id_provider=lambda: BACKUP_ID,
    )
    gate, execute = _execute_with_backup_service(paths.database, plan, adapter)

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == "transition_backup_failed"
    assert _database_state(paths.database) == before
    assert pending.is_dir()
    assert tuple(paths.backups.iterdir()) == ()
    assert gate.state is MaintenanceState.NORMAL


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

    gate = MaintenanceGate()
    step_up_service, authorization = _step_up(_resolved_plan(v3_database))
    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(
            forbidden_connection,
            maintenance_gate=gate,
            step_up_service=step_up_service,
            backup_service=_VerifiedBackupService(
                source_state_sha256=unresolved.source_sha256
            ),
        ).execute(
            plan=unresolved,
            operation_token=TOKEN,
            expected_plan_sha256=school_year_transition_plan_sha256(unresolved),
            step_up_authorization=authorization,
            maintenance_owner_id=MAINTENANCE_OWNER,
        )

    assert captured.value.code == "transition_plan_not_fully_resolved"
    assert opened is False


def test_transition_requests_maintenance_only_after_step_up(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    gate = MaintenanceGate()
    step_up_service, authorization = _step_up(plan)

    ExecuteSchoolYearTransition(
        _factory(v3_database),
        maintenance_gate=gate,
        step_up_service=step_up_service,
        backup_service=_VerifiedBackupService(
            source_state_sha256=plan.source_sha256
        ),
        now_provider=lambda: NOW,
    ).execute(
        plan=plan,
        operation_token=TOKEN,
        expected_plan_sha256=school_year_transition_plan_sha256(plan),
        step_up_authorization=authorization,
        maintenance_owner_id="different-owner",
    )

    assert authorization.consumed is True
    assert gate.state is MaintenanceState.NORMAL


def _execute_with_backup_service(path: Path, plan, backup_service, *, gate=None):
    if (
        isinstance(backup_service, _VerifiedBackupService)
        and backup_service.source_state_sha256 is None
    ):
        backup_service.source_state_sha256 = plan.source_sha256
    gate = gate or MaintenanceGate()
    step_up_service, authorization = _step_up(plan)
    service = ExecuteSchoolYearTransition(
        _factory(path),
        maintenance_gate=gate,
        step_up_service=step_up_service,
        backup_service=backup_service,
        now_provider=lambda: NOW,
    )
    return gate, lambda: service.execute(
        plan=plan,
        operation_token=TOKEN,
        expected_plan_sha256=school_year_transition_plan_sha256(plan),
        step_up_authorization=authorization,
        maintenance_owner_id=MAINTENANCE_OWNER,
    )


def test_missing_backup_evidence_blocks_and_releases_gate(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    before = _database_state(v3_database)
    gate, execute = _execute_with_backup_service(v3_database, plan, None)

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == "transition_backup_evidence_missing"
    assert _database_state(v3_database) == before
    assert gate.state is MaintenanceState.NORMAL


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    (
        (
            {"backup_sha256": "not-a-sha256"},
            "transition_backup_sha256_invalid",
        ),
        (
            {"backup_sha256": "0" * 64},
            "transition_backup_sha256_invalid",
        ),
        (
            {"source_state_sha256": "a" * 64},
            "transition_backup_source_state_mismatch",
        ),
        (
            {"source_schema_fingerprint": "c" * 64},
            "transition_backup_schema_fingerprint_mismatch",
        ),
        (
            {"verified_at": datetime(2026, 7, 15, 10, 30)},
            "transition_backup_verified_at_invalid",
        ),
    ),
)
def test_invalid_backup_evidence_blocks_without_database_change(
    v3_database: Path,
    changes: dict[str, object],
    expected_code: str,
) -> None:
    plan = _resolved_plan(v3_database)
    before = _database_state(v3_database)
    gate, execute = _execute_with_backup_service(
        v3_database,
        plan,
        _VerifiedBackupService(evidence_changes=changes),
    )

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == expected_code
    assert _database_state(v3_database) == before
    assert gate.state is MaintenanceState.NORMAL


def test_repository_rejects_null_backup_hash(v3_database: Path) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.row_factory = sqlite3.Row
        repository = SchoolYearTransitionExecutionRepository(connection)

        with pytest.raises(SchoolYearTransitionRepositoryError) as captured:
            repository.insert_transition(
                transition_id="SYT-null-backup-test",
                from_school_year_id=SYNTHETIC_SCHOOL_YEAR_ID,
                to_school_year_id="SY-null-backup-target",
                operation_token="null-backup-test",
                plan_sha256="a" * 64,
                backup_sha256="0" * 64,
                result_counts_json="{}",
                completed_at=NOW,
            )

    assert captured.value.code == "transition_backup_sha256_invalid"


def test_backup_service_failure_blocks_without_database_change(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    before = _database_state(v3_database)
    gate, execute = _execute_with_backup_service(
        v3_database,
        plan,
        _VerifiedBackupService(error=RuntimeError("injected backup failure")),
    )

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == "transition_backup_failed"
    assert _database_state(v3_database) == before
    assert gate.state is MaintenanceState.NORMAL


def test_source_change_after_backup_blocks_transition_and_receipt(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)

    def change_source() -> None:
        with sqlite3.connect(v3_database) as connection:
            connection.execute(
                "UPDATE groups SET active = 0 WHERE group_id = 'GRP-TEST-B'"
            )

    gate, execute = _execute_with_backup_service(
        v3_database,
        plan,
        _VerifiedBackupService(after_backup=change_source),
    )

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == "transition_sources_changed"
    with sqlite3.connect(v3_database) as connection:
        assert connection.execute(
            "SELECT count(*) FROM school_year_transitions"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM school_years WHERE status = 'current'"
        ).fetchone()[0] == 1
    assert gate.state is MaintenanceState.NORMAL


def test_new_writer_is_blocked_while_transition_backup_runs(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    gate = MaintenanceGate()
    observed: list[object] = []

    def probe_writer() -> None:
        observed.append(gate.state)
        errors: list[Exception] = []

        def other_thread() -> None:
            try:
                gate.begin_writer()
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=other_thread)
        thread.start()
        thread.join(timeout=1)
        observed.extend(errors)

    gate, execute = _execute_with_backup_service(
        v3_database,
        plan,
        _VerifiedBackupService(after_backup=probe_writer),
        gate=gate,
    )

    execute()

    assert observed[0] is MaintenanceState.MAINTENANCE_ACTIVE
    assert isinstance(observed[1], MaintenanceWriterBlockedError)
    assert gate.state is MaintenanceState.NORMAL


def test_transition_rejects_incomplete_writer_drain_without_write(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    before = _database_state(v3_database)
    gate = MaintenanceGate()
    lease = gate.begin_writer()
    gate, execute = _execute_with_backup_service(
        v3_database,
        plan,
        _VerifiedBackupService(),
        gate=gate,
    )

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        execute()

    assert captured.value.code == "transition_writers_not_drained"
    assert _database_state(v3_database) == before
    assert gate.state is MaintenanceState.NORMAL
    lease.release()


def test_backup_restore_capability_cannot_execute_transition(
    v3_database: Path,
) -> None:
    plan = _resolved_plan(v3_database)
    before = _database_state(v3_database)
    gate = MaintenanceGate()
    step_up_service, authorization = _step_up(plan)
    object.__setattr__(
        authorization,
        "purpose",
        MaintenancePurpose.BACKUP_RESTORE,
    )

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(
            _factory(v3_database),
            maintenance_gate=gate,
            step_up_service=step_up_service,
            backup_service=_VerifiedBackupService(
                source_state_sha256=plan.source_sha256
            ),
        ).execute(
            plan=plan,
            operation_token=TOKEN,
            expected_plan_sha256=school_year_transition_plan_sha256(plan),
            step_up_authorization=authorization,
            maintenance_owner_id=MAINTENANCE_OWNER,
        )

    assert captured.value.code == "transition_step_up_purpose_invalid"
    assert _database_state(v3_database) == before
    assert gate.state is MaintenanceState.NORMAL


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

    gate = MaintenanceGate()
    step_up_service, authorization = _step_up(plan)
    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(
            _factory(v3_database),
            maintenance_gate=gate,
            step_up_service=step_up_service,
            backup_service=_VerifiedBackupService(
                source_state_sha256=plan.source_sha256
            ),
            now_provider=lambda: NOW,
            repository_factory=lambda connection: _FailingRepository(
                connection,
                fail_at=fail_at,
            ),
        ).execute(
            plan=plan,
            operation_token=TOKEN,
            expected_plan_sha256=school_year_transition_plan_sha256(plan),
            step_up_authorization=authorization,
            maintenance_owner_id=MAINTENANCE_OWNER,
        )

    assert captured.value.code == "transition_execution_failed"
    assert _database_state(v3_database) == before
    assert gate.state is MaintenanceState.NORMAL


class _AmbiguousCommitConnection(sqlite3.Connection):
    def commit(self) -> None:
        super().commit()
        raise sqlite3.OperationalError("injected ambiguous commit outcome")


def test_ambiguous_commit_marks_recovery_required(v3_database: Path) -> None:
    plan = _resolved_plan(v3_database)
    gate = MaintenanceGate()
    step_up_service, authorization = _step_up(plan)

    def ambiguous_factory() -> sqlite3.Connection:
        connection = sqlite3.connect(
            v3_database,
            factory=_AmbiguousCommitConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(
            ambiguous_factory,
            maintenance_gate=gate,
            step_up_service=step_up_service,
            backup_service=_VerifiedBackupService(
                source_state_sha256=plan.source_sha256
            ),
            now_provider=lambda: NOW,
        ).execute(
            plan=plan,
            operation_token=TOKEN,
            expected_plan_sha256=school_year_transition_plan_sha256(plan),
            step_up_authorization=authorization,
            maintenance_owner_id=MAINTENANCE_OWNER,
        )

    assert captured.value.code == "transition_recovery_required"
    assert gate.state is MaintenanceState.RECOVERY_REQUIRED
    with pytest.raises(MaintenanceWriterBlockedError):
        gate.begin_writer()


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
    assert receipt[2] == BACKUP_SHA256
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
