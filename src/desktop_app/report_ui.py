"""Internal report surface gate without importing Qt WebEngine on the Qt path."""

from __future__ import annotations

import os
from typing import Literal


REPORT_UI_ENV = "JKM_REPORT_UI"
ReportUiMode = Literal["qt", "html"]


def report_ui_mode(environment: dict[str, str] | None = None) -> ReportUiMode:
    """Return the explicitly selected report surface; Qt is the safe default."""
    values = os.environ if environment is None else environment
    value = values.get(REPORT_UI_ENV, "qt").strip().casefold()
    if value not in {"qt", "html"}:
        raise ValueError("report_ui_mode_invalid")
    return value  # type: ignore[return-value]
