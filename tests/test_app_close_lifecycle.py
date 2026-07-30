"""Focused regressions for Qt window ownership and normal application exit."""

from __future__ import annotations

import os
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QWidget
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


def _restore_shutdown_probe_main(root: str, lifetime_fd: int) -> None:
    """Exercise restore shutdown from inside a nested workspace event loop."""
    app = QApplication(sys.argv)
    shell = _shell(Path(root))
    shell.show()
    workspace = QDialog(shell)
    events: list[str] = []
    workspace.finished.connect(lambda _result: events.append("workspace_finished"))
    app.lastWindowClosed.connect(lambda: events.append("last_window_closed"))
    app.aboutToQuit.connect(lambda: events.append("about_to_quit"))
    preview = SimpleNamespace(restore_id="RST-NESTED-SHUTDOWN")
    handoff = SimpleNamespace(path=Path("handoff.json"), nonce="nonce")
    started = SimpleNamespace(process=object(), parent_lifetime_fd=lifetime_fd)

    def enter_workspace() -> None:
        QTimer.singleShot(0, lambda: shell._launch_verified_restore(preview))
        workspace.exec()
        events.append("workspace_unwound")
        shell.show()

    with mock.patch.object(
        shell.backup_restore_adapter,
        "create_restore_handoff",
        return_value=handoff,
    ), mock.patch.object(
        shell.backup_restore_adapter,
        "launch_prepared_restore",
        return_value=started,
    ):
        QTimer.singleShot(0, enter_workspace)
        QTimer.singleShot(2_000, lambda: app.exit(91))
        exit_code = app.exec()

    events.append("app_exec_returned")
    visible = [widget for widget in app.topLevelWidgets() if widget.isVisible()]
    running_threads = [
        thread for thread in shell.findChildren(QThread) if thread.isRunning()
    ]
    print(json.dumps(events), flush=True)
    if visible or running_threads:
        raise SystemExit(92)
    raise SystemExit(exit_code)


def test_restore_shutdown_unwinds_nested_workspace_and_closes_parent_lifetime_fd(
    tmp_path: Path,
) -> None:
    probe_root = tmp_path / "restore-process-runtime"
    read_fd, write_fd = os.pipe()
    command = (
        "from tests.test_app_close_lifecycle import _restore_shutdown_probe_main; "
        "_restore_shutdown_probe_main(__import__('sys').argv[1], "
        "int(__import__('sys').argv[2]))"
    )
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    process = subprocess.Popen(
        [sys.executable, "-c", command, str(probe_root), str(write_fd)],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        pass_fds=(write_fd,),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    os.close(write_fd)
    try:
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, (
            f"restore shutdown did not finish cleanly: {stderr}"
        )
        assert os.read(read_fd, 1) == b""
    finally:
        os.close(read_fd)

    events = json.loads(stdout.strip().splitlines()[-1])
    assert events.index("workspace_finished") < events.index("workspace_unwound")
    assert events.index("workspace_unwound") < events.index("about_to_quit")
    assert events.index("about_to_quit") < events.index("app_exec_returned")


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
