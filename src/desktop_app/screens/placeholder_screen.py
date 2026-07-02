"""Placeholder screens for deferred MVP areas."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.desktop_app.theme import set_label_style


class PlaceholderScreen(QWidget):
    """Simple placeholder for out-of-scope areas."""

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        set_label_style(title_label, "screen_title")
        message_label = QLabel(message)
        set_label_style(message_label, "muted")
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addStretch()
