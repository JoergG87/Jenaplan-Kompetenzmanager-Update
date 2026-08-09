"""Main window for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from src.core.restore_runtime import RuntimeInstanceLock
from src.desktop_app.shell import AppShell
from src.desktop_app.runtime import RuntimePaths, default_database_path, runtime_paths
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.updater.application import UpdateApplicationService


class JenaplanDesktopApp(AppShell):
    """PySide6 app shell entry class."""

    def __init__(
        self,
        database_path: Path | None = None,
        *,
        paths: RuntimePaths | None = None,
        runtime_lock: RuntimeInstanceLock | None = None,
        update_service: UpdateApplicationService | None = None,
        database_create_allowed: bool = False,
        student_adapter: StudentDesktopAdapter | None = None,
        backup_restore_available: bool = True,
    ) -> None:
        database = database_path or default_database_path()
        super().__init__(
            database,
            paths=paths or runtime_paths(database.parent),
            runtime_lock=runtime_lock,
            update_service=update_service,
            database_create_allowed=database_create_allowed,
            student_adapter=student_adapter,
            backup_restore_available=backup_restore_available,
        )
