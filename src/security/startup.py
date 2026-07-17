"""Qt-free startup state and technical security-runtime composition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from src.core.app_preferences import AppPreferencesFile

from .application import SecurityApplicationService, SecurityStateResult
from .domain import SecurityStoreError, SecurityStoreState
from .infrastructure import (
    Argon2idPasswordHasher,
    EnrollmentMarkerFile,
    PlatformFilePermissionManager,
    SQLiteSecurityRepository,
    SystemClock,
    SystemRandomSource,
)


class SecurityRuntimePaths(Protocol):
    database: Path
    documents: Path
    security_database: Path
    enrollment_marker: Path
    app_preferences: Path


class SecurityStartState(StrEnum):
    FIRST_RUN = "first_run"
    LEGACY_ENROLLMENT = "legacy_enrollment"
    LOGIN_REQUIRED = "login_required"
    RECOVERY_AVAILABLE = "recovery_available"
    PASSWORD_RESET_PENDING = "password_reset_pending"
    LOCKED = "locked"
    AUTHENTICATED = "authenticated"
    INCONSISTENT = "inconsistent"
    CORRUPT = "corrupt"
    UNSUPPORTED_VERSION = "unsupported_version"
    FATAL_SECURITY_ERROR = "fatal_security_error"


@dataclass(frozen=True)
class SecurityStartupDecision:
    state: SecurityStartState
    technical_code: str


class SecurityStartupResolver:
    """Map one validated store state to exactly one product startup state."""

    def resolve(
        self,
        security_state: SecurityStateResult,
        *,
        legacy_installation_present: bool,
    ) -> SecurityStartupDecision:
        state = security_state.state
        if state is SecurityStoreState.UNINITIALIZED:
            result = (
                SecurityStartState.LEGACY_ENROLLMENT
                if legacy_installation_present
                else SecurityStartState.FIRST_RUN
            )
        elif state is SecurityStoreState.READY:
            result = SecurityStartState.LOGIN_REQUIRED
        elif state is SecurityStoreState.PASSWORD_RESET_PENDING:
            result = SecurityStartState.PASSWORD_RESET_PENDING
        elif state is SecurityStoreState.INCONSISTENT:
            result = SecurityStartState.INCONSISTENT
        elif state is SecurityStoreState.CORRUPT:
            result = SecurityStartState.CORRUPT
        elif state is SecurityStoreState.UNSUPPORTED_VERSION:
            result = SecurityStartState.UNSUPPORTED_VERSION
        else:  # pragma: no cover - enum exhaustiveness guard
            result = SecurityStartState.FATAL_SECURITY_ERROR
        return SecurityStartupDecision(result, f"SEC-{result.value.upper()}")


@dataclass(frozen=True)
class SecurityRuntime:
    service: SecurityApplicationService
    repository: SQLiteSecurityRepository
    preferences: AppPreferencesFile


def build_security_runtime(paths: SecurityRuntimePaths) -> SecurityRuntime:
    permissions = PlatformFilePermissionManager()
    repository = SQLiteSecurityRepository(paths.security_database, permissions)
    clock = SystemClock()
    service = SecurityApplicationService(
        repository=repository,
        marker=EnrollmentMarkerFile(paths.enrollment_marker, permissions),
        password_hasher=Argon2idPasswordHasher(),
        random_source=SystemRandomSource(),
        utc_clock=clock,
        monotonic_clock=clock,
        permissions=permissions,
    )
    return SecurityRuntime(
        service,
        repository,
        AppPreferencesFile(paths.app_preferences, permissions),
    )


def legacy_installation_present(paths: SecurityRuntimePaths) -> bool:
    """Recognize an existing product runtime without opening its database."""
    return paths.database.is_file() or paths.documents.is_dir()
