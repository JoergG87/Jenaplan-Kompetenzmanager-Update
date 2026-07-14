"""Navigation constants for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationItem:
    """Navigation entry for the app shell."""

    key: str
    label: str
    section: str
    icon_name: str


@dataclass(frozen=True)
class NavigationTarget:
    """Resolved navigation target for shell actions."""

    screen_key: str
    reset_group_filter: bool = False


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem("dashboard", "Heute", "ARBEIT", "today"),
    NavigationItem("students", "Schüler", "ARBEIT", "students"),
    NavigationItem("master_data", "Stammdaten", "VERWALTUNG", "master-data"),
    NavigationItem("settings", "Einstellungen", "VERWALTUNG", "settings"),
)


def resolve_navigation_target(key: str) -> NavigationTarget:
    """Resolve sidebar navigation to a shell screen target."""
    if key == "students":
        return NavigationTarget("students", reset_group_filter=True)
    if key in {item.key for item in NAVIGATION_ITEMS}:
        return NavigationTarget(key)
    raise ValueError(f"Unbekanntes Navigationsziel: {key}")
