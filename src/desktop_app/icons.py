"""Loader for the small, consistent SVG icon set used by the product shell."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

from src.desktop_app.runtime import resource_path


ICON_NAMES = frozenset(
    {
        "today",
        "students",
        "master-data",
        "settings",
        "info",
        "search",
        "close",
        "chevron-down",
        "conference",
        "observation",
        "report",
        "student-record",
        "timetable-dialog",
        "master-data-dialog",
    }
)
ICON_SIZE_SMALL = 16
ICON_SIZE_MEDIUM = 20
ICON_SIZE_LARGE = 24


def icon_path(name: str) -> Path:
    """Return one registered shell icon path."""
    if name not in ICON_NAMES:
        raise ValueError(f"Unbekanntes App-Icon: {name}")
    return resource_path("assets", "icons", f"{name}.svg")


def load_icon(name: str) -> QIcon:
    """Load one registered SVG icon."""
    return QIcon(str(icon_path(name)))
