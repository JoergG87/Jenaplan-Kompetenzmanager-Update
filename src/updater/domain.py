"""Qt-free update state projected into the desktop application."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class UpdateChannel(StrEnum):
    """Release channels understood by the product."""

    PILOT = "pilot"
    STABLE = "stable"


class UpdateState(StrEnum):
    """Small user-facing state independent of Sparkle implementation details."""

    READY = "ready"
    CHECKING = "checking"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True)
class UpdateProjection:
    """Read-only update status for the settings page."""

    current_version: str
    build_version: str
    channel: UpdateChannel
    state: UpdateState
    last_checked_at: str | None = None
    message: str = ""

    @property
    def can_check(self) -> bool:
        return self.state is UpdateState.READY
