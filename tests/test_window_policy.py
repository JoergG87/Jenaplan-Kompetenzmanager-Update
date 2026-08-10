"""Focused offscreen checks for large workspace window placement."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from src.desktop_app.shell import AppShell
from src.desktop_app.window_policy import (
    exec_maximized_workspace,
    open_maximized_workspace,
    prepare_maximized_workspace,
    workspace_screen,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_workspace_policy_uses_owner_screen_and_available_geometry() -> None:
    app = _app()
    owner = QWidget()
    owner.resize(700, 500)
    owner.show()
    app.processEvents()
    screen = owner.screen()
    available = screen.availableGeometry()
    dialog = QDialog(owner)
    dialog.setMinimumSize(available.width() + 500, available.height() + 500)

    selected = prepare_maximized_workspace(dialog, owner)

    assert selected is screen
    assert workspace_screen(owner, dialog) is screen
    assert dialog.minimumWidth() == available.width()
    assert dialog.minimumHeight() == available.height()
    assert available.contains(dialog.geometry())
    assert dialog.windowState() & Qt.WindowState.WindowMaximized
    assert not dialog.windowState() & Qt.WindowState.WindowFullScreen
    owner.close()


def test_workspace_policy_executes_repeated_windows_maximized() -> None:
    app = _app()
    owner = QWidget()
    owner.show()
    app.processEvents()

    class RecordingDialog(QDialog):
        def __init__(self, parent: QWidget) -> None:
            super().__init__(parent)
            self.maximized_requested = False

        def showMaximized(self) -> None:  # noqa: N802
            self.maximized_requested = True
            super().showMaximized()

        def exec(self) -> int:
            return int(QDialog.DialogCode.Accepted)

    for _index in range(2):
        dialog = RecordingDialog(owner)
        assert exec_maximized_workspace(dialog, owner) == int(QDialog.DialogCode.Accepted)
        assert dialog.maximized_requested
        assert dialog.windowState() & Qt.WindowState.WindowMaximized
        assert not dialog.windowState() & Qt.WindowState.WindowFullScreen
        dialog.close()
    owner.close()


def test_workspace_policy_opens_report_without_nested_event_loop() -> None:
    app = _app()
    owner = QWidget()
    owner.show()
    app.processEvents()
    dialog = QDialog(owner)

    open_maximized_workspace(dialog, owner)
    app.processEvents()

    assert dialog.isVisible()
    assert dialog.isModal()
    assert dialog.windowModality() == Qt.WindowModality.WindowModal
    assert dialog.windowState() & Qt.WindowState.WindowMaximized
    dialog.close()
    owner.close()


def test_shell_routes_observation_report_and_leg_through_central_policy() -> None:
    report_source = inspect.getsource(AppShell.open_learning_report_dialog)
    leg_source = inspect.getsource(AppShell.open_learning_conference_dialog)
    observation_sources = "\n".join(
        inspect.getsource(method)
        for method in (
            AppShell.open_new_observation_dialog,
            AppShell.open_quick_observation_dialog,
            AppShell.open_edit_observation_dialog,
        )
    )

    assert "open_maximized_workspace(dialog, self)" in report_source
    assert "exec_maximized_workspace(dialog, self)" not in report_source
    assert "open_maximized_workspace(dialog, self)" in leg_source
    assert "exec_maximized_workspace(dialog, self)" not in leg_source
    assert "dialog.finished.connect(finish_learning_conference_workspace)" in leg_source
    assert "dialog.destroyed.connect(clear_active_learning_conference)" in leg_source
    assert observation_sources.count("exec_maximized_workspace(dialog, self)") == 3
    assert observation_sources.count("parent=self") == 3
