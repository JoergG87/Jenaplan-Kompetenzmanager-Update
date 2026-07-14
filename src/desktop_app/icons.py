"""Loader for the small, consistent SVG icon set used by the product shell."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon


ICON_NAMES = frozenset({"today", "students", "master-data", "settings", "info"})
ICON_SIZE_SMALL = 16
ICON_SIZE_MEDIUM = 20
ICON_SIZE_LARGE = 24


def icon_path(name: str) -> Path:
    """Return one registered shell icon path."""
    if name not in ICON_NAMES:
        raise ValueError(f"Unbekanntes App-Icon: {name}")
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / f"{name}.svg"


def load_icon(name: str) -> QIcon:
    """Load one registered SVG icon."""
    return QIcon(str(icon_path(name)))
