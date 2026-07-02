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
from src.desktop_app.theme import set_label_style


APP_INFO_TITLE = "Über Jenaplan Kompetenzmanager"
APP_INFO_APP_NAME = "Jenaplan Kompetenzmanager"
APP_INFO_MODE = "PySide6 Prototyp"
APP_INFO_VERSION = "Prototyp"
APP_INFO_STORAGE_HINT = "Einige Funktionen sind noch nicht dauerhaft gespeichert."
APP_INFO_EXCEL_HINT = "Excel bleibt aktuell Export/Legacy-Projektion."


class AppInfoDialog(QDialog):
    """Show a compact, non-technical app information dialog."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_INFO_TITLE)
        self.setModal(True)
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
        layout.addWidget(QLabel(APP_INFO_MODE))
        layout.addWidget(QLabel(f"Version: {APP_INFO_VERSION}"))
        layout.addWidget(QLabel(APP_INFO_STORAGE_HINT))
        layout.addWidget(QLabel(APP_INFO_EXCEL_HINT))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Schließen")
            close_button.setDefault(True)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
