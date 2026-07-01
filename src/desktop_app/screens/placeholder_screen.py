"""Placeholder screens for deferred MVP areas."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderScreen(QWidget):
    """Simple placeholder for out-of-scope areas."""

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #555;")
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addStretch()
