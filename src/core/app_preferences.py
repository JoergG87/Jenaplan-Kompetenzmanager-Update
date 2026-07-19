"""Local, non-domain application preferences stored outside SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
import tempfile
from typing import Protocol


DISPLAY_NAME_MAX_LENGTH = 80
ALLOWED_INACTIVITY_MINUTES = (5, 10, 15, 30, 60)
ONBOARDING_FORMAT_VERSION = 1
ONBOARDING_BASE_STEP_COUNT = 5
ONBOARDING_PILOT_STEP_COUNT = 6
ONBOARDING_STEP_COUNT = ONBOARDING_PILOT_STEP_COUNT


class OnboardingStatus(StrEnum):
    """Persisted local state for the first-steps orientation."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class AppPreferencesError(RuntimeError):
    """Raised when local application preferences cannot be read safely."""


class FilePermissionPort(Protocol):
    def prepare_directory(self, path: Path) -> None: ...

    def secure_file(self, path: Path) -> None: ...


def normalize_display_name(value: str) -> str | None:
    """Trim only outer whitespace and validate the optional plain-text name."""
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > DISPLAY_NAME_MAX_LENGTH:
        raise ValueError("display_name_too_long")
    return normalized


@dataclass(frozen=True)
class AppPreferences:
    inactivity_minutes: int = 15
    display_name: str | None = None
    onboarding_status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    onboarding_current_step: int = 0
    onboarding_format_version: int = ONBOARDING_FORMAT_VERSION
    touch_id_preferred: bool = False

    def __post_init__(self) -> None:
        if self.inactivity_minutes not in ALLOWED_INACTIVITY_MINUTES:
            raise ValueError("inactivity_interval_invalid")
        normalized = normalize_display_name(self.display_name or "")
        if normalized != self.display_name:
            raise ValueError("display_name_not_normalized")
        if self.onboarding_format_version != ONBOARDING_FORMAT_VERSION:
            raise ValueError("onboarding_format_version_unsupported")
        if not isinstance(self.onboarding_status, OnboardingStatus):
            object.__setattr__(
                self,
                "onboarding_status",
                OnboardingStatus(str(self.onboarding_status)),
            )
        if not 0 <= int(self.onboarding_current_step) < ONBOARDING_STEP_COUNT:
            raise ValueError("onboarding_current_step_invalid")
        object.__setattr__(
            self, "onboarding_current_step", int(self.onboarding_current_step)
        )
        if not isinstance(self.touch_id_preferred, bool):
            raise ValueError("touch_id_preferred_invalid")


class AppPreferencesFile:
    """Atomic JSON persistence for general local app preferences."""

    FORMAT_VERSION = 3
    LEGACY_FORMAT_VERSION = 1
    ONBOARDING_FORMAT_FILE_VERSION = 2

    def __init__(self, path: Path, permissions: FilePermissionPort):
        self.path = Path(path)
        self.permissions = permissions

    def load(self) -> AppPreferences:
        if not self.path.exists():
            return AppPreferences()
        if self.path.is_symlink():
            raise AppPreferencesError("app_preferences_symlink_rejected")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
            raw_format_version = int(payload.get("format_version", 0))
            if raw_format_version > self.FORMAT_VERSION:
                return self._newer_preferences(payload)
            if raw_format_version == self.LEGACY_FORMAT_VERSION:
                if set(payload) != {
                    "display_name", "format_version", "inactivity_minutes"
                }:
                    raise ValueError
                return self._legacy_preferences(payload)
            onboarding_fields = {
                "display_name",
                "format_version",
                "inactivity_minutes",
                "onboarding_current_step",
                "onboarding_format_version",
                "onboarding_status",
            }
            if raw_format_version == self.ONBOARDING_FORMAT_FILE_VERSION:
                if set(payload) != onboarding_fields:
                    raise ValueError
                return self._onboarding_preferences(payload)
            if raw_format_version != self.FORMAT_VERSION:
                raise ValueError
            if set(payload) != onboarding_fields | {"touch_id_preferred"}:
                raise ValueError
            raw_name = payload["display_name"]
            if raw_name is not None and not isinstance(raw_name, str):
                raise ValueError
            raw_onboarding_format_version = int(
                payload["onboarding_format_version"]
            )
            if raw_onboarding_format_version > ONBOARDING_FORMAT_VERSION:
                return self._newer_preferences(payload)
            return AppPreferences(
                inactivity_minutes=int(payload["inactivity_minutes"]),
                display_name=raw_name,
                onboarding_status=OnboardingStatus(payload["onboarding_status"]),
                onboarding_current_step=int(payload["onboarding_current_step"]),
                onboarding_format_version=raw_onboarding_format_version,
                touch_id_preferred=payload["touch_id_preferred"],
            )
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise AppPreferencesError("app_preferences_invalid") from error

    def save(self, preferences: AppPreferences) -> None:
        self.permissions.prepare_directory(self.path.parent)
        payload = json.dumps(
            {
                "display_name": preferences.display_name,
                "format_version": self.FORMAT_VERSION,
                "inactivity_minutes": preferences.inactivity_minutes,
                "onboarding_current_step": preferences.onboarding_current_step,
                "onboarding_format_version": preferences.onboarding_format_version,
                "onboarding_status": preferences.onboarding_status.value,
                "touch_id_preferred": preferences.touch_id_preferred,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".app-preferences-", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            if os.name == "posix":
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self.permissions.secure_file(self.path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _legacy_preferences(self, payload: dict[str, object]) -> AppPreferences:
        raw_name = payload["display_name"]
        if raw_name is not None and not isinstance(raw_name, str):
            raise ValueError
        return AppPreferences(
            inactivity_minutes=int(payload["inactivity_minutes"]),
            display_name=raw_name,
        )

    def _onboarding_preferences(self, payload: dict[str, object]) -> AppPreferences:
        raw_name = payload["display_name"]
        if raw_name is not None and not isinstance(raw_name, str):
            raise ValueError
        return AppPreferences(
            inactivity_minutes=int(payload["inactivity_minutes"]),
            display_name=raw_name,
            onboarding_status=OnboardingStatus(payload["onboarding_status"]),
            onboarding_current_step=int(payload["onboarding_current_step"]),
            onboarding_format_version=int(payload["onboarding_format_version"]),
        )

    def _newer_preferences(self, payload: dict[str, object]) -> AppPreferences:
        raw_name = payload.get("display_name")
        if raw_name is not None and not isinstance(raw_name, str):
            raw_name = None
        try:
            inactivity_minutes = int(payload.get("inactivity_minutes", 15))
            if inactivity_minutes not in ALLOWED_INACTIVITY_MINUTES:
                inactivity_minutes = 15
        except (TypeError, ValueError):
            inactivity_minutes = 15
        try:
            display_name = normalize_display_name(raw_name or "")
        except ValueError:
            display_name = None
        return AppPreferences(
            inactivity_minutes=inactivity_minutes,
            display_name=display_name,
            onboarding_status=OnboardingStatus.DISMISSED,
        )
