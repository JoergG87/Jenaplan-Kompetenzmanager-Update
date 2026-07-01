"""Navigation constants for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationItem:
    """Navigation entry for the app shell."""

    key: str
    label: str


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem("overview", "Übersicht"),
    NavigationItem("students", "Schüler"),
    NavigationItem("observations", "Beobachtungen"),
    NavigationItem("competencies", "Kompetenzen"),
    NavigationItem("reports", "Berichte"),
    NavigationItem("settings", "Einstellungen"),
)
