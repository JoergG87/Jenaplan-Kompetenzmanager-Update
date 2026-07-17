"""Main window for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from src.core.restore_runtime import RuntimeInstanceLock
from src.desktop_app.shell import AppShell
from src.desktop_app.runtime import RuntimePaths, default_database_path, runtime_paths


class JenaplanDesktopApp(AppShell):
    """PySide6 app shell entry class."""

    def __init__(
        self,
        database_path: Path | None = None,
        *,
        paths: RuntimePaths | None = None,
        runtime_lock: RuntimeInstanceLock | None = None,
    ) -> None:
        database = database_path or default_database_path()
        super().__init__(database, paths=paths or runtime_paths(database.parent), runtime_lock=runtime_lock)
