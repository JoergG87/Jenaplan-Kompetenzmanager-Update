"""Entry point for the experimental PySide6 desktop app."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.desktop_app.app import JenaplanDesktopApp
from src.desktop_app.theme import apply_app_theme


def _app_icon() -> QIcon:
    """Return the application icon used for windows and the task switcher."""
    project_root = Path(__file__).resolve().parents[2]
    icon_path = project_root / "assets" / "app_icon.png"
    return QIcon(str(icon_path))


def main() -> int:
    """Start the desktop app."""
    app = QApplication(sys.argv)
    app.setApplicationName("Jenaplan Kompetenzmanager")
    app.setWindowIcon(_app_icon())
    apply_app_theme(app)

    window = JenaplanDesktopApp()
    window.setWindowIcon(_app_icon())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
