"""Main window for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from src.desktop_app.shell import AppShell
from src.desktop_app.runtime import default_database_path


class JenaplanDesktopApp(AppShell):
    """PySide6 app shell entry class."""

    def __init__(self, database_path: Path | None = None) -> None:
        super().__init__(database_path or default_database_path())
