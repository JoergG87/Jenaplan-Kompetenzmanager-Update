"""Static asset helpers for the PySide desktop app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel


APP_ICON_RELATIVE_PATH = Path("assets") / "app_icon.png"


def project_root() -> Path:
    """Return the repository root independently from the current working directory."""
    return Path(__file__).resolve().parents[2]


def app_icon_path() -> Path:
    """Return the app icon path."""
    return project_root() / APP_ICON_RELATIVE_PATH


def load_app_icon_pixmap(size: int) -> QPixmap:
    """Load and scale the app icon without raising in the UI."""
    pixmap = QPixmap(str(app_icon_path()))
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def create_app_icon_label(size: int) -> QLabel:
    """Create a centered label with the app icon or a compact fallback."""
    label = QLabel()
    label.setObjectName("AppIconLabel")
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pixmap = load_app_icon_pixmap(size)
    if pixmap.isNull():
        label.setText("JK")
        return label
    label.setPixmap(pixmap)
    return label
