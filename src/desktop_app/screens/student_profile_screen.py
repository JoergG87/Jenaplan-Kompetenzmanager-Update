"""Light student profile screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


class StudentProfileScreen(QWidget):
    """Lightweight read-only student profile."""

    def __init__(self) -> None:
        super().__init__()
        self.name_label = QLabel("Kein Schüler ausgewählt")
        self.meta_label = QLabel("")
        self.notes = QTextEdit()
        self.observation_placeholder = QLabel("Beobachtungen folgen später.")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        self.name_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.meta_label.setStyleSheet("color: #555;")
        self.notes.setReadOnly(True)
        self.notes.setMinimumHeight(110)
        self.observation_placeholder.setStyleSheet("color: #666;")
        layout.addWidget(self.name_label)
        layout.addWidget(self.meta_label)
        layout.addWidget(QLabel("Notiz"))
        layout.addWidget(self.notes)
        layout.addWidget(self.observation_placeholder)
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
