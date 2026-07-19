"""Ports for the supervised native updater."""

from __future__ import annotations

from typing import Protocol


class NativeUpdatePort(Protocol):
    """Minimal native operations needed by the application service."""

    @property
    def available(self) -> bool: ...

    @property
    def can_check(self) -> bool: ...

    def last_check_date(self) -> str | None: ...

    def check_for_updates(self) -> None: ...
