"""Navigation constants for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationItem:
    """Navigation entry for the app shell."""

    key: str
    label: str


@dataclass(frozen=True)
class NavigationTarget:
    """Resolved navigation target for shell actions."""

    screen_key: str
    reset_group_filter: bool = False


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem("overview", "Übersicht"),
    NavigationItem("students", "Schüler"),
    NavigationItem("observations", "Beobachtungen"),
    NavigationItem("competencies", "Kompetenzen"),
    NavigationItem("reports", "Berichte"),
    NavigationItem("master_data", "Stammdaten"),
    NavigationItem("settings", "Einstellungen"),
)


def resolve_navigation_target(key: str) -> NavigationTarget:
    """Resolve sidebar navigation to a shell screen target."""
    if key == "students":
        return NavigationTarget("students", reset_group_filter=True)
    return NavigationTarget(key)
