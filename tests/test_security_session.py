"""Central inactivity and sleep/wake session policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.security.session import (
    InMemorySession,
    SecuritySessionController,
    SessionActivityKind,
    SessionLockReason,
    WakeObservation,
)


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
SESSION = InMemorySession("user", "installation", 3)


def _controller(minutes: int = 15) -> SecuritySessionController:
    return SecuritySessionController(
        SESSION,
        inactivity_minutes=minutes,
        monotonic_now=100.0,
        utc_now=NOW,
    )


@pytest.mark.parametrize("minutes", [5, 10, 15, 30, 60])
def test_only_allowed_intervals_lock_at_their_deadline(minutes: int) -> None:
    controller = _controller(minutes)
    seconds = minutes * 60
    assert controller.poll(monotonic_now=100 + seconds - 1, utc_now=NOW + timedelta(seconds=seconds - 1)) is None
    assert controller.poll(monotonic_now=100 + seconds, utc_now=NOW + timedelta(seconds=seconds)) is SessionLockReason.INACTIVITY


@pytest.mark.parametrize("minutes", [0, 1, 14, 61])
def test_never_and_free_intervals_are_rejected(minutes: int) -> None:
    with pytest.raises(ValueError):
        _controller(minutes)


def test_real_activity_resets_deadline_but_background_has_no_controller_api() -> None:
    controller = _controller(5)
    controller.activity(
        SessionActivityKind.KEYBOARD,
        monotonic_now=350.0,
        utc_now=NOW + timedelta(seconds=250),
    )
    assert controller.poll(monotonic_now=649.0, utc_now=NOW + timedelta(seconds=549)) is None
    assert not hasattr(controller, "worker_activity")
    assert not hasattr(controller, "timer_activity")


def test_wake_locks_when_deadline_elapsed_or_time_is_uncertain() -> None:
    elapsed = _controller(5)
    assert elapsed.observe_wake(
        WakeObservation(401.0, NOW + timedelta(seconds=301))
    ) is SessionLockReason.WAKE
    uncertain = _controller(60)
    assert uncertain.observe_wake(
        WakeObservation(None, None, time_uncertain=True)
    ) is SessionLockReason.WAKE


def test_short_known_sleep_does_not_lock_before_deadline() -> None:
    controller = _controller(15)
    assert controller.observe_wake(
        WakeObservation(220.0, NOW + timedelta(seconds=120))
    ) is None


def test_session_is_memory_only_and_epoch_change_invalidates() -> None:
    controller = _controller()
    controller.invalidate()
    assert controller.session is None
    assert controller.lock_reason is SessionLockReason.EPOCH_CHANGED
