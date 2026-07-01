"""Main window for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from src.core.sqlite_store import SQLITE_SPIKE_PATH
from src.desktop_app.shell import AppShell


class JenaplanDesktopApp(AppShell):
    """PySide6 app shell entry class."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        super().__init__(database_path)
