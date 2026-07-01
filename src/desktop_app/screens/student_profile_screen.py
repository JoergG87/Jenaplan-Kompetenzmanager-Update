"""Light student profile screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import (
    PROFILE_ACTION_MESSAGES,
    PROFILE_SECTION_PLACEHOLDERS,
    StudentDetailViewModel,
)


class StudentProfileScreen(QWidget):
    """Lightweight read-only student profile."""

    back_requested = Signal()
    observation_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.current_student: StudentDetailViewModel | None = None
        self.back_button = QPushButton("← Zurück zur Schülerliste")
        self.name_label = QLabel("Kein Schüler ausgewählt")
        self.meta_label = QLabel("")
        self.student_id_label = QLabel("")
        self.group_value_label = QLabel("")
        self.course_value_label = QLabel("")
        self.notes_value_label = QLabel("")
        self.action_feedback_label = QLabel("")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.back_button.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_button)
        header.addStretch()
        layout.addLayout(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        self.name_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.meta_label.setStyleSheet("color: #555;")
        self.student_id_label.setStyleSheet("color: #777; font-size: 11px;")
        content_layout.addWidget(self.name_label)
        content_layout.addWidget(self.meta_label)
        content_layout.addWidget(self.student_id_label)
        content_layout.addWidget(self._actions_card())
        content_layout.addWidget(self._basis_data_card())
        content_layout.addWidget(self._placeholder_card(
            "Beobachtungen",
            PROFILE_SECTION_PLACEHOLDERS["observations_title"],
            PROFILE_SECTION_PLACEHOLDERS["observations_hint"],
        ))
        content_layout.addWidget(self._placeholder_card(
            "Kompetenzen",
            PROFILE_SECTION_PLACEHOLDERS["competencies_title"],
            PROFILE_SECTION_PLACEHOLDERS["competencies_hint"],
        ))
        content_layout.addWidget(self._placeholder_card(
            "Dokumente",
            PROFILE_SECTION_PLACEHOLDERS["documents_title"],
            PROFILE_SECTION_PLACEHOLDERS["documents_hint"],
        ))
        content_layout.addStretch()
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

    def _actions_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Schnellaktionen")
        title.setStyleSheet("font-weight: 600;")
        button_row = QHBoxLayout()
        observation_button = QPushButton("+ Beobachtung")
        document_button = QPushButton("Dokument hinzufügen")
        edit_button = QPushButton("Schüler bearbeiten")
        observation_button.clicked.connect(self._request_new_observation)
        document_button.clicked.connect(
            lambda: self._show_placeholder_message(PROFILE_ACTION_MESSAGES["document"])
        )
        edit_button.clicked.connect(
            lambda: self._show_placeholder_message(PROFILE_ACTION_MESSAGES["edit"])
        )
        button_row.addWidget(observation_button)
        button_row.addWidget(document_button)
        button_row.addWidget(edit_button)
        button_row.addStretch()
        self.action_feedback_label.setStyleSheet("color: #555;")
        layout.addWidget(title)
        layout.addLayout(button_row)
        layout.addWidget(self.action_feedback_label)
        return card

    def _basis_data_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Basisdaten")
        title.setStyleSheet("font-weight: 600;")
        field_row = QHBoxLayout()
        field_row.addWidget(self._basis_field_column("Stammgruppe", self.group_value_label), 1)
        field_row.addWidget(self._basis_field_column("Kurs", self.course_value_label), 1)
        field_row.addWidget(self._basis_field_column("Notiz", self.notes_value_label), 2)
        layout.addWidget(title)
        layout.addLayout(field_row)
        return card

    def _basis_field_column(self, label: str, value_label: QLabel) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        field_label = QLabel(label)
        field_label.setStyleSheet("color: #666; font-size: 12px;")
        value_label.setStyleSheet("color: #222; font-size: 14px;")
        value_label.setWordWrap(True)
        layout.addWidget(field_label)
        layout.addWidget(value_label)
        layout.addStretch()
        return column

    def _placeholder_card(self, title: str, placeholder: str, hint: str) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600;")
        placeholder_label = QLabel(placeholder)
        placeholder_label.setStyleSheet("color: #444;")
        hint_label = QLabel(hint)
        hint_label.setStyleSheet("color: #666;")
        layout.addWidget(title_label)
        layout.addWidget(placeholder_label)
        layout.addWidget(hint_label)
        return card

    def _card(self) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        return card

    def _show_placeholder_message(self, message: str) -> None:
        self.action_feedback_label.setText(message)

    def _request_new_observation(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["observation"])
            return
        self.observation_requested.emit(self.current_student)

    def set_student(self, student: StudentDetailViewModel | None) -> None:
        """Render selected student or empty state."""
        self.current_student = student
        if student is None:
            self.name_label.setText("Kein Schüler ausgewählt")
            self.meta_label.setText("")
            self.student_id_label.setText("")
            self.group_value_label.setText("")
            self.course_value_label.setText("")
            self.notes_value_label.setText("")
            self.action_feedback_label.setText("")
            return
        self.name_label.setText(student.display_name)
        self.meta_label.setText(f"{student.group_name} · {student.course_name}")
        self.student_id_label.setText(student.student_id)
        self.group_value_label.setText(student.group_name)
        self.course_value_label.setText(student.course_name)
        self.notes_value_label.setText(student.student_notes or "Keine Notiz hinterlegt.")
        self.action_feedback_label.setText("")
