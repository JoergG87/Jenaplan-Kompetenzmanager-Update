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
from src.version import APP_BUILD_VERSION, APP_VERSION


APP_INFO_TITLE = "Über Jenaplan-Kompetenzmanager"
APP_INFO_APP_NAME = "Jenaplan-Kompetenzmanager"
APP_INFO_MODE = "Lokale Desktop-App"
APP_INFO_VERSION = f"Version {APP_VERSION} · Build {APP_BUILD_VERSION}"
APP_INFO_DEVELOPER_NAME = "Jörg Gehrke"
APP_INFO_DESCRIPTION = "Kompetenzmanagement und Entwicklungsdokumentation für Jenaplan-Schulen"
APP_INFO_COPYRIGHT = "© 2026 Jörg Gehrke"


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
        version = QLabel(APP_INFO_VERSION)
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(version, "muted")
        layout.addWidget(version)
        developed_by = QLabel("Entwickelt von")
        developed_by.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(developed_by, "muted")
        layout.addWidget(developed_by)
        developer_name = QLabel(APP_INFO_DEVELOPER_NAME)
        developer_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(developer_name, "card_title")
        layout.addWidget(developer_name)
        description = QLabel(APP_INFO_DESCRIPTION)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        set_label_style(description, "muted")
        layout.addWidget(description)
        copyright_notice = QLabel(APP_INFO_COPYRIGHT)
        copyright_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(copyright_notice, "muted")
        layout.addWidget(copyright_notice)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.setObjectName("DialogActionBar")
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Schließen")
            close_button.setDefault(True)
            configure_button(close_button, "secondary", "Informationen schließen")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
