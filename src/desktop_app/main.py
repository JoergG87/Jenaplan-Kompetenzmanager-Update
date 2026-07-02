"""Entry point for the experimental PySide6 desktop app."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.desktop_app.app import JenaplanDesktopApp
from src.desktop_app.theme import apply_app_theme


def main() -> int:
    """Start the desktop app."""
    app = QApplication(sys.argv)
    apply_app_theme(app)
    window = JenaplanDesktopApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
