"""Focused SJ-3C.5 password step-up tests without UI or real product data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
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
from src.application.school_year_transition_step_up import (
    SchoolYearTransitionStepUpError,
    SchoolYearTransitionStepUpService,
)
from src.core.maintenance_gate import (
    MaintenanceGate,
    MaintenancePurpose,
    MaintenanceState,
)
from src.security.application import AuthenticationResult
from src.security.domain import AuthenticationStatus
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v3_database,
)


NOW = datetime(2026, 7, 15, 10, 30, tzinfo=UTC)
AUTHORIZATION_ID = "SYA-fedcba9876543210fedcba9876543210"
PASSWORD = "correct horse battery staple"


class _PasswordService:
    def __init__(self, expected: str = PASSWORD) -> None:
        self.expected = expected
        self.calls: list[str] = []
        self.result_override: AuthenticationResult | None = None

    def authenticate_password(self, password: str) -> AuthenticationResult:
        self.calls.append(password)
        if self.result_override is not None:
            return self.result_override
        status = (
            AuthenticationStatus.AUTHENTICATED
            if password == self.expected
            else AuthenticationStatus.INVALID_CREDENTIALS
        )
        return AuthenticationResult(status)


class _BackupSpy:
    def __init__(self) -> None:
        self.calls = 0

    def create_and_verify(self):
        self.calls += 1
        raise AssertionError("backup must not run")


class _MaintenanceGateSpy(MaintenanceGate):
    def __init__(self) -> None:
        super().__init__()
        self.request_calls = 0

    def request_maintenance(self, **kwargs):
        self.request_calls += 1
        return super().request_maintenance(**kwargs)


def _factory(path: Path):
    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    return connect


@pytest.fixture
def resolved_plan(tmp_path: Path):
    path = create_synthetic_v3_database(tmp_path / "step-up.sqlite")
    plan = SchoolYearTransitionPreviewService(_factory(path)).preview_plan(
        label="2026/27",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 7, 31),
    ).repeat_year_level_three(
        SYNTHETIC_STUDENT_IDS[2],
        "CRS-TEST-3",
    )
    return path, plan


def _service(password_service: _PasswordService, *, now_provider=lambda: NOW):
    return SchoolYearTransitionStepUpService(
        password_service,
        now_provider=now_provider,
        authorization_id_provider=lambda: AUTHORIZATION_ID,
    )


def test_correct_password_issues_short_lived_transition_authorization(
    resolved_plan,
) -> None:
    _path, plan = resolved_plan
    passwords = _PasswordService()

    result = _service(passwords).authenticate(plan=plan, password=PASSWORD)

    assert result.status is AuthenticationStatus.AUTHENTICATED
    assert result.authorization is not None
    assert result.authorization.purpose is MaintenancePurpose.SCHOOL_YEAR_TRANSITION
    assert result.authorization.created_at == NOW
    assert result.authorization.expires_at == NOW + timedelta(minutes=2)
    assert result.authorization.authorization_id == AUTHORIZATION_ID
    assert result.authorization.consumed is False
    assert passwords.calls == [PASSWORD]


@pytest.mark.parametrize("password", ("wrong password", ""))
def test_wrong_or_empty_password_blocks_without_authorization(
    resolved_plan,
    password: str,
) -> None:
    _path, plan = resolved_plan
    passwords = _PasswordService()

    result = _service(passwords).authenticate(plan=plan, password=password)

    assert result.status is AuthenticationStatus.INVALID_CREDENTIALS
    assert result.authorization is None
    assert passwords.calls == [password]


def test_existing_password_throttling_result_is_forwarded(resolved_plan) -> None:
    _path, plan = resolved_plan
    passwords = _PasswordService()
    passwords.result_override = AuthenticationResult(
        AuthenticationStatus.THROTTLED,
        retry_after_seconds=30,
    )

    result = _service(passwords).authenticate(plan=plan, password=PASSWORD)

    assert result.status is AuthenticationStatus.THROTTLED
    assert result.retry_after_seconds == 30
    assert result.authorization is None


def test_invalid_authorization_reaches_neither_maintenance_backup_nor_database(
    resolved_plan,
) -> None:
    path, plan = resolved_plan
    gate = _MaintenanceGateSpy()
    backup = _BackupSpy()
    step_up_service = _service(_PasswordService())
    failed = step_up_service.authenticate(plan=plan, password="wrong password")
    assert failed.authorization is None
    opened = False

    def forbidden_connection():
        nonlocal opened
        opened = True
        raise AssertionError("database must not open")

    with pytest.raises(SchoolYearTransitionExecutionError) as captured:
        ExecuteSchoolYearTransition(
            forbidden_connection,
            maintenance_gate=gate,
            step_up_service=step_up_service,
            backup_service=backup,
            now_provider=lambda: NOW,
        ).execute(
            plan=plan,
            operation_token="step-up-blocked",
            expected_plan_sha256=school_year_transition_plan_sha256(plan),
            step_up_authorization=failed.authorization,  # type: ignore[arg-type]
            maintenance_owner_id="step-up-test",
        )

    assert captured.value.code == "transition_step_up_authorization_invalid"
    assert gate.request_calls == 0
    assert gate.state is MaintenanceState.NORMAL
    assert backup.calls == 0
    assert opened is False
    assert path.exists()


def test_authorization_is_transition_only_and_consumed_on_wrong_purpose(
    resolved_plan,
) -> None:
    _path, plan = resolved_plan
    service = _service(_PasswordService())
    authorization = service.authenticate(
        plan=plan,
        password=PASSWORD,
    ).authorization
    assert authorization is not None

    with pytest.raises(SchoolYearTransitionStepUpError) as captured:
        service.consume(
            authorization,
            plan=plan,
            purpose=MaintenancePurpose.BACKUP_RESTORE,
        )

    assert captured.value.code == "transition_step_up_purpose_mismatch"
    assert authorization.consumed is True


def test_authorization_is_single_use_and_reuse_is_blocked(resolved_plan) -> None:
    _path, plan = resolved_plan
    service = _service(_PasswordService())
    authorization = service.authenticate(
        plan=plan,
        password=PASSWORD,
    ).authorization
    assert authorization is not None

    service.consume(
        authorization,
        plan=plan,
        purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
    )
    with pytest.raises(SchoolYearTransitionStepUpError) as captured:
        service.consume(
            authorization,
            plan=plan,
            purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
        )

    assert captured.value.code == "transition_step_up_authorization_consumed"


def test_expired_authorization_is_discarded_and_blocks(resolved_plan) -> None:
    _path, plan = resolved_plan
    current = [NOW]
    service = _service(_PasswordService(), now_provider=lambda: current[0])
    authorization = service.authenticate(
        plan=plan,
        password=PASSWORD,
    ).authorization
    assert authorization is not None
    current[0] = NOW + timedelta(minutes=2)

    with pytest.raises(SchoolYearTransitionStepUpError) as captured:
        service.consume(
            authorization,
            plan=plan,
            purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
        )

    assert captured.value.code == "transition_step_up_authorization_expired"
    assert authorization.consumed is True


def test_authorization_is_bound_to_exact_resolved_plan(resolved_plan) -> None:
    _path, plan = resolved_plan
    service = _service(_PasswordService())
    authorization = service.authenticate(
        plan=plan,
        password=PASSWORD,
    ).authorization
    assert authorization is not None
    changed = plan.select_other_group(SYNTHETIC_STUDENT_IDS[0], "GRP-TEST-B")

    with pytest.raises(SchoolYearTransitionStepUpError) as captured:
        service.consume(
            authorization,
            plan=changed,
            purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
        )

    assert captured.value.code == "transition_step_up_plan_mismatch"
    assert authorization.consumed is True


def test_abort_discards_authorization_without_side_effect(resolved_plan) -> None:
    path, plan = resolved_plan
    service = _service(_PasswordService())
    authorization = service.authenticate(
        plan=plan,
        password=PASSWORD,
    ).authorization
    assert authorization is not None
    before = path.read_bytes()

    service.discard(authorization)

    assert authorization.consumed is True
    assert path.read_bytes() == before


def test_password_is_absent_from_authorization_result_and_log(
    resolved_plan,
    caplog,
) -> None:
    _path, plan = resolved_plan

    result = _service(_PasswordService()).authenticate(
        plan=plan,
        password=PASSWORD,
    )

    assert PASSWORD not in repr(result)
    assert PASSWORD not in caplog.text
    assert result.authorization is not None
    assert not hasattr(result.authorization, "password")
    assert not hasattr(result.authorization, "password_hash")
    assert not hasattr(result.authorization, "credential")


def test_unresolved_plan_is_rejected_before_password_check(resolved_plan) -> None:
    path, _plan = resolved_plan
    unresolved = SchoolYearTransitionPreviewService(_factory(path)).preview_plan(
        label="2026/27",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 7, 31),
    )
    passwords = _PasswordService()

    with pytest.raises(SchoolYearTransitionStepUpError) as captured:
        _service(passwords).authenticate(plan=unresolved, password=PASSWORD)

    assert captured.value.code == "transition_plan_not_fully_resolved"
    assert passwords.calls == []
