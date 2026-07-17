"""Central screen-aware policy for large desktop workspaces."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QDialog, QWidget


def workspace_screen(owner: QWidget | None, dialog: QWidget | None = None) -> QScreen:
    """Return the owner's screen, with conservative Qt fallbacks."""
    candidates = (
        owner,
        dialog.parentWidget() if dialog is not None else None,
        dialog,
    )
    for candidate in candidates:
        if candidate is None:
            continue
        screen = candidate.window().screen()
        if screen is not None:
            return screen
    primary = QGuiApplication.primaryScreen()
    if primary is None:
        raise RuntimeError("Für das Arbeitsfenster ist kein Bildschirm verfügbar.")
    return primary


def prepare_maximized_workspace(dialog: QDialog, owner: QWidget | None) -> QScreen:
    """Place a normal maximized dialog inside the owner's available screen area."""
    screen = workspace_screen(owner, dialog)
    available = screen.availableGeometry()
    if available.width() <= 0 or available.height() <= 0:
        raise RuntimeError("Die verfügbare Bildschirmfläche ist ungültig.")

    dialog.setMinimumSize(
        min(dialog.minimumWidth(), available.width()),
        min(dialog.minimumHeight(), available.height()),
    )
    dialog.setGeometry(available)
    dialog.winId()
    handle = dialog.windowHandle()
    if handle is not None and handle.screen() is not screen:
        handle.setScreen(screen)
        dialog.setGeometry(available)
    state = dialog.windowState()
    dialog.setWindowState(
        (state | Qt.WindowState.WindowMaximized)
        & ~Qt.WindowState.WindowFullScreen
    )
    return screen


def exec_maximized_workspace(dialog: QDialog, owner: QWidget | None) -> int:
    """Execute a workspace maximized without entering a platform full-screen space."""
    prepare_maximized_workspace(dialog, owner)
    dialog.showMaximized()
    return int(dialog.exec())
