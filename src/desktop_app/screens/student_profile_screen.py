"""Light student profile screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


class StudentProfileScreen(QWidget):
    """Lightweight read-only student profile."""

    back_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.back_button = QPushButton("← Zurück zur Schülerliste")
        self.name_label = QLabel("Kein Schüler ausgewählt")
        self.meta_label = QLabel("")
        self.notes = QTextEdit()
        self.observation_placeholder = QLabel("Beobachtungen folgen später.")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.back_button.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_button)
        header.addStretch()
        layout.addLayout(header)

        self.name_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.meta_label.setStyleSheet("color: #555;")
        self.notes.setReadOnly(True)
        self.notes.setMinimumHeight(110)

        notes_card = QFrame()
        notes_card.setFrameShape(QFrame.Shape.StyledPanel)
        notes_card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        notes_layout = QVBoxLayout(notes_card)
        notes_title = QLabel("Notiz")
        notes_title.setStyleSheet("font-weight: 600;")
        notes_layout.addWidget(notes_title)
        notes_layout.addWidget(self.notes)

        observation_card = QFrame()
        observation_card.setFrameShape(QFrame.Shape.StyledPanel)
        observation_card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        observation_layout = QVBoxLayout(observation_card)
        observation_title = QLabel("Beobachtungen")
        observation_title.setStyleSheet("font-weight: 600;")
        self.observation_placeholder.setStyleSheet("color: #666;")
        observation_layout.addWidget(observation_title)
        observation_layout.addWidget(self.observation_placeholder)

        layout.addWidget(self.name_label)
        layout.addWidget(self.meta_label)
        layout.addWidget(notes_card)
        layout.addWidget(observation_card)
        layout.addStretch()

    def set_student(self, student: StudentDetailViewModel | None) -> None:
        """Render selected student or empty state."""
        if student is None:
            self.name_label.setText("Kein Schüler ausgewählt")
            self.meta_label.setText("")
            self.notes.setPlainText("")
            return
        self.name_label.setText(student.display_name)
        self.meta_label.setText(f"{student.group_name} · {student.course_name}")
        self.notes.setPlainText(student.student_notes or "Keine Notiz vorhanden.")
