"""Internal LEG surface gate without importing Qt WebEngine on the Qt path."""

from __future__ import annotations

import os
from typing import Literal


LEG_UI_ENV = "JKM_LEG_UI"
LegUiMode = Literal["qt", "html"]


def leg_ui_mode(environment: dict[str, str] | None = None) -> LegUiMode:
    """Return the explicitly selected LEG surface; Qt is the safe default."""
    values = os.environ if environment is None else environment
    value = values.get(LEG_UI_ENV, "qt").strip().casefold()
    if value not in {"qt", "html"}:
        raise ValueError("leg_ui_mode_invalid")
    return value  # type: ignore[return-value]
