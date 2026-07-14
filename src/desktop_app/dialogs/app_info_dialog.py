"""App information dialog for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from src.desktop_app.assets import create_app_icon_label
from src.desktop_app.components import StatusBadge, configure_button
from src.desktop_app.theme import set_label_style


APP_INFO_TITLE = "Über Jenaplan Kompetenzmanager"
APP_INFO_APP_NAME = "Jenaplan Kompetenzmanager"
APP_INFO_MODE = "Lokale Desktop-App"
APP_INFO_VERSION = "v0.4"
APP_INFO_STORAGE_HINT = "Arbeitsdaten werden lokal auf diesem Gerät gespeichert."
APP_INFO_PURPOSE = "Für die tägliche Dokumentation und Lernbegleitung."


class AppInfoDialog(QDialog):
    """Show a compact, non-technical app information dialog."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_INFO_TITLE)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.resize(460, 430)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        icon_label = create_app_icon_label(112)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignHCenter)
        title = QLabel(APP_INFO_APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        set_label_style(title, "dialog_title")
        layout.addWidget(title)
        mode = StatusBadge(APP_INFO_MODE)
        mode.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mode, 0, Qt.AlignmentFlag.AlignHCenter)
        version = QLabel(f"Version: {APP_INFO_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        storage = QLabel(APP_INFO_STORAGE_HINT)
        storage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(storage)
        purpose = QLabel(APP_INFO_PURPOSE)
        purpose.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(purpose, "muted")
        layout.addWidget(purpose)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.setObjectName("DialogActionBar")
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Schließen")
            close_button.setDefault(True)
            configure_button(close_button, "secondary", "Informationen schließen")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
