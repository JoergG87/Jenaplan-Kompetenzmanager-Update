"""Focused regressions for Qt window ownership and normal application exit."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from shiboken6 import isValid

from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.components import AppCard
from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
from src.desktop_app.runtime import runtime_paths
from src.desktop_app.shell import AppShell


def _shell(root: Path) -> AppShell:
    paths = runtime_paths(root)
    for directory in (
        paths.root,
        paths.documents,
        paths.exports,
        paths.backups,
        paths.logs,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    database = SQLiteDatabase(paths.database)
    database.initialize_schema()
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (
                'SY-CLOSE-TEST', '2025/26', '2025-08-01', '2026-07-31',
                'current', '2025-07-01T08:00:00+00:00', NULL
            )
            """
        )
    return AppShell(paths.database, paths=paths)


def _created_top_levels(
    app: QApplication,
    previous: set[object],
) -> list[object]:
    return [
        widget
        for widget in app.topLevelWidgets()
        if widget not in previous
    ]


def test_shell_owns_every_product_widget_and_normal_close_leaves_no_window(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    previous = set(app.topLevelWidgets())
    shell = _shell(tmp_path / "runtime")
    shell.show()
    app.processEvents()

    created = _created_top_levels(app, previous)
    unowned = [
        widget
        for widget in created
        if widget.parentWidget() is None
    ]
    visible = [widget for widget in created if widget.isVisible()]

    assert unowned == [shell]
    assert visible == [shell]
    assert not any(thread.isRunning() for thread in shell.findChildren(QThread))

    shell.close()
    app.processEvents()

    assert not any(widget.isVisible() for widget in created)
    assert not any(thread.isRunning() for thread in shell.findChildren(QThread))


def _close_probe_main(root: str) -> None:
    """Run one isolated QApplication and expose a stuck event loop as exit 91."""
    app = QApplication(sys.argv)
    shell = _shell(Path(root))
    shell.show()
    QTimer.singleShot(0, shell.close)
    QTimer.singleShot(1_000, lambda: app.exit(91))
    raise SystemExit(app.exec())


def test_normal_close_ends_the_application_process(tmp_path: Path) -> None:
    probe_root = tmp_path / "process-runtime"
    command = (
        "from tests.test_app_close_lifecycle import _close_probe_main; "
        "_close_probe_main(__import__('sys').argv[1])"
    )
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

    completed = subprocess.run(
        [sys.executable, "-c", command, str(probe_root)],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, (
        f"process did not exit after the shell closed: {completed.stderr}"
    )


def test_report_preview_cleanup_keeps_cards_owned_until_deferred_delete() -> None:
    app = QApplication.instance() or QApplication([])
    container = QWidget()
    layout = QVBoxLayout(container)
    card = AppCard()
    layout.addWidget(card)

    LearningReportDialog._clear_layout(layout)

    assert card.parentWidget() is container
    assert card not in app.topLevelWidgets()


def test_profile_list_cleanup_destroys_detached_cards_immediately(
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    shell = _shell(tmp_path / "profile-cleanup-runtime")
    container = QWidget(shell.student_profile_screen)
    layout = QVBoxLayout(container)
    card = AppCard()
    layout.addWidget(card)

    shell.student_profile_screen._clear_layout(layout)

    assert not isValid(card)
    assert card not in app.topLevelWidgets()
    shell.close()
    app.processEvents()
