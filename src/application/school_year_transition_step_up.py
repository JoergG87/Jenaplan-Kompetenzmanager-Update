"""Transient password step-up authority for school-year transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import secrets
from typing import Protocol

from src.application.school_year_transition_plan import (
    SchoolYearTransitionPlan,
    school_year_transition_plan_sha256,
)
from src.core.maintenance_gate import MaintenancePurpose
from src.security.application import AuthenticationResult
from src.security.domain import AuthenticationStatus


_DEFAULT_LIFETIME = timedelta(minutes=2)
_MAXIMUM_LIFETIME = timedelta(minutes=5)


class SchoolYearTransitionStepUpError(RuntimeError):
    """Sanitized fail-closed step-up failure with a stable technical code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _PasswordAuthenticationService(Protocol):
    def authenticate_password(self, password: str) -> AuthenticationResult: ...


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionStepUpAuthorization:
    """One-shot in-memory authority bound to one resolved transition plan."""

    purpose: MaintenancePurpose
    created_at: datetime
    expires_at: datetime
    authorization_id: str
    plan_sha256: str
    _issuer_token: object = field(repr=False)
    _consumed: bool = field(default=False, init=False, repr=False)

    @property
    def consumed(self) -> bool:
        return self._consumed


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionStepUpResult:
    """Password result plus an authority only when authentication succeeded."""

    status: AuthenticationStatus
    retry_after_seconds: int = 0
    authorization: SchoolYearTransitionStepUpAuthorization | None = None


class SchoolYearTransitionStepUpService:
    """Authenticate, issue, consume and discard transition-only authority."""

    def __init__(
        self,
        security_service: _PasswordAuthenticationService,
        *,
        now_provider=None,
        authorization_id_provider=None,
        lifetime: timedelta = _DEFAULT_LIFETIME,
    ) -> None:
        if not isinstance(lifetime, timedelta) or not (
            timedelta(0) < lifetime <= _MAXIMUM_LIFETIME
        ):
            raise ValueError("step_up_lifetime_invalid")
        self._security_service = security_service
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._authorization_id_provider = authorization_id_provider or (
            lambda: f"SYA-{secrets.token_hex(16)}"
        )
        self._lifetime = lifetime
        self._issuer_token = object()

    def authenticate(
        self,
        *,
        plan: SchoolYearTransitionPlan,
        password: str,
    ) -> SchoolYearTransitionStepUpResult:
        plan_hash = _require_resolved_plan(plan)
        result = self._security_service.authenticate_password(password)
        if result.status is not AuthenticationStatus.AUTHENTICATED:
            return SchoolYearTransitionStepUpResult(
                status=result.status,
                retry_after_seconds=result.retry_after_seconds,
            )
        created_at = _require_timestamp(self._now_provider())
        authorization = SchoolYearTransitionStepUpAuthorization(
            purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
            created_at=created_at,
            expires_at=created_at + self._lifetime,
            authorization_id=_require_authorization_id(
                self._authorization_id_provider()
            ),
            plan_sha256=plan_hash,
            _issuer_token=self._issuer_token,
        )
        return SchoolYearTransitionStepUpResult(
            status=AuthenticationStatus.AUTHENTICATED,
            authorization=authorization,
        )

    def consume(
        self,
        authorization: SchoolYearTransitionStepUpAuthorization,
        *,
        plan: SchoolYearTransitionPlan,
        purpose: MaintenancePurpose,
    ) -> None:
        if (
            not isinstance(authorization, SchoolYearTransitionStepUpAuthorization)
            or authorization._issuer_token is not self._issuer_token
        ):
            raise SchoolYearTransitionStepUpError(
                "transition_step_up_authorization_invalid"
            )
        if authorization._consumed:
            raise SchoolYearTransitionStepUpError(
                "transition_step_up_authorization_consumed"
            )
        object.__setattr__(authorization, "_consumed", True)
        now = _require_timestamp(self._now_provider())
        if authorization.purpose is not MaintenancePurpose.SCHOOL_YEAR_TRANSITION:
            raise SchoolYearTransitionStepUpError(
                "transition_step_up_purpose_invalid"
            )
        if purpose is not MaintenancePurpose.SCHOOL_YEAR_TRANSITION:
            raise SchoolYearTransitionStepUpError(
                "transition_step_up_purpose_mismatch"
            )
        if now >= authorization.expires_at:
            raise SchoolYearTransitionStepUpError(
                "transition_step_up_authorization_expired"
            )
        if authorization.plan_sha256 != _require_resolved_plan(plan):
            raise SchoolYearTransitionStepUpError(
                "transition_step_up_plan_mismatch"
            )

    def discard(
        self,
        authorization: SchoolYearTransitionStepUpAuthorization | None,
    ) -> None:
        if (
            isinstance(authorization, SchoolYearTransitionStepUpAuthorization)
            and authorization._issuer_token is self._issuer_token
        ):
            object.__setattr__(authorization, "_consumed", True)


def _require_resolved_plan(plan: SchoolYearTransitionPlan) -> str:
    if not isinstance(plan, SchoolYearTransitionPlan):
        raise SchoolYearTransitionStepUpError("transition_plan_invalid")
    validation = plan.validate()
    if not validation.complete or any(not item.resolved for item in plan.items):
        raise SchoolYearTransitionStepUpError(
            "transition_plan_not_fully_resolved"
        )
    return school_year_transition_plan_sha256(plan)


def _require_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SchoolYearTransitionStepUpError(
            "transition_step_up_timestamp_invalid"
        )
    return value.astimezone(UTC)


def _require_authorization_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("SYA-")
        or len(value) != 36
        or any(character not in "0123456789abcdef" for character in value[4:])
    ):
        raise SchoolYearTransitionStepUpError(
            "transition_step_up_authorization_id_invalid"
        )
    return value
