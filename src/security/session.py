"""Qt-free in-memory session, activity and wake lock policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from src.core.app_preferences import ALLOWED_INACTIVITY_MINUTES


class SessionLockReason(StrEnum):
    MANUAL = "manual"
    INACTIVITY = "inactivity"
    WAKE = "wake"
    EPOCH_CHANGED = "epoch_changed"


class SessionActivityKind(StrEnum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    TOUCH = "touch"
    WINDOW_ACTIVATION = "window_activation"


@dataclass(frozen=True)
class InMemorySession:
    user_id: str
    installation_id: str
    security_epoch: int


@dataclass(frozen=True)
class WakeObservation:
    monotonic_now: float | None
    utc_now: datetime | None
    time_uncertain: bool = False


class SecuritySessionController:
    """Own the only inactivity clock; background work never calls activity()."""

    def __init__(
        self,
        session: InMemorySession,
        *,
        inactivity_minutes: int = 15,
        monotonic_now: float,
        utc_now: datetime,
    ) -> None:
        self._validate_interval(inactivity_minutes)
        self.session: InMemorySession | None = session
        self.inactivity_minutes = inactivity_minutes
        self.lock_reason: SessionLockReason | None = None
        self.last_activity_monotonic = monotonic_now
        self.last_activity_utc = self._utc(utc_now)

    @property
    def locked(self) -> bool:
        return self.lock_reason is not None

    def set_inactivity_minutes(self, minutes: int) -> None:
        self._validate_interval(minutes)
        self.inactivity_minutes = minutes

    def activity(
        self, kind: SessionActivityKind, *, monotonic_now: float, utc_now: datetime
    ) -> None:
        if self.locked or self.session is None:
            return
        SessionActivityKind(kind)
        self.last_activity_monotonic = monotonic_now
        self.last_activity_utc = self._utc(utc_now)

    def poll(self, *, monotonic_now: float, utc_now: datetime) -> SessionLockReason | None:
        if self.locked or self.session is None:
            return self.lock_reason
        limit = self.inactivity_minutes * 60
        utc_elapsed = (self._utc(utc_now) - self.last_activity_utc).total_seconds()
        monotonic_elapsed = monotonic_now - self.last_activity_monotonic
        if utc_elapsed < 0 or monotonic_elapsed < 0:
            return self.lock(SessionLockReason.WAKE)
        if max(utc_elapsed, monotonic_elapsed) >= limit:
            return self.lock(SessionLockReason.INACTIVITY)
        return None

    def observe_wake(self, observation: WakeObservation) -> SessionLockReason | None:
        if self.locked or self.session is None:
            return self.lock_reason
        if (
            observation.time_uncertain
            or observation.monotonic_now is None
            or observation.utc_now is None
        ):
            return self.lock(SessionLockReason.WAKE)
        limit = self.inactivity_minutes * 60
        utc_elapsed = (self._utc(observation.utc_now) - self.last_activity_utc).total_seconds()
        monotonic_elapsed = observation.monotonic_now - self.last_activity_monotonic
        if utc_elapsed < 0 or monotonic_elapsed < 0 or max(utc_elapsed, monotonic_elapsed) >= limit:
            return self.lock(SessionLockReason.WAKE)
        return None

    def lock(self, reason: SessionLockReason) -> SessionLockReason:
        self.lock_reason = SessionLockReason(reason)
        return self.lock_reason

    def unlock(
        self,
        session: InMemorySession,
        *,
        monotonic_now: float,
        utc_now: datetime,
    ) -> None:
        self.session = session
        self.lock_reason = None
        self.last_activity_monotonic = monotonic_now
        self.last_activity_utc = self._utc(utc_now)

    def invalidate(self) -> None:
        self.session = None
        self.lock_reason = SessionLockReason.EPOCH_CHANGED

    @staticmethod
    def _validate_interval(minutes: int) -> None:
        if minutes not in ALLOWED_INACTIVITY_MINUTES:
            raise ValueError("inactivity_interval_invalid")

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("utc_time_required")
        return value.astimezone(timezone.utc)
