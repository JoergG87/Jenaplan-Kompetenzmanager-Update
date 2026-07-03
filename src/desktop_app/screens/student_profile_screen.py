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
from src.desktop_app.view_models.observation_view_model import (
    ObservationListItem,
    StudentCompetencySubjectGroup,
)
from src.desktop_app.theme import create_card, set_label_style


class StudentProfileScreen(QWidget):
    """Lightweight read-only student profile."""

    back_requested = Signal()
    observation_requested = Signal(object)
    observation_edit_requested = Signal(str)
    observation_delete_requested = Signal(str)

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
        self.observation_empty_label = QLabel("")
        self.competency_empty_label = QLabel("")
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

        set_label_style(self.name_label, "screen_title")
        set_label_style(self.meta_label, "muted")
        set_label_style(self.student_id_label, "small")
        content_layout.addWidget(self.name_label)
        content_layout.addWidget(self.meta_label)
        content_layout.addWidget(self.student_id_label)
        content_layout.addWidget(self._actions_card())
        content_layout.addWidget(self._basis_data_card())
        content_layout.addWidget(self._observations_card())
        content_layout.addWidget(self._competencies_card())
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
        set_label_style(title, "card_title")
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
        set_label_style(self.action_feedback_label, "muted")
        layout.addWidget(title)
        layout.addLayout(button_row)
        layout.addWidget(self.action_feedback_label)
        return card

    def _basis_data_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Basisdaten")
        set_label_style(title, "card_title")
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
        set_label_style(field_label, "field_label")
        set_label_style(value_label, "body")
        value_label.setWordWrap(True)
        layout.addWidget(field_label)
        layout.addWidget(value_label)
        layout.addStretch()
        return column

    def _placeholder_card(self, title: str, placeholder: str, hint: str) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        set_label_style(title_label, "card_title")
        placeholder_label = QLabel(placeholder)
        set_label_style(placeholder_label, "body")
        hint_label = QLabel(hint)
        set_label_style(hint_label, "subtle")
        layout.addWidget(title_label)
        layout.addWidget(placeholder_label)
        layout.addWidget(hint_label)
        return card

    def _observations_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_label = QLabel("Beobachtungen")
        set_label_style(title_label, "section_title")
        self.observations_container = QWidget()
        self.observations_layout = QVBoxLayout(self.observations_container)
        self.observations_layout.setContentsMargins(0, 0, 0, 0)
        self.observations_layout.setSpacing(8)
        set_label_style(self.observation_empty_label, "body")
        layout.addWidget(title_label)
        layout.addWidget(self.observations_container)
        return section

    def _competencies_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_label = QLabel("Kompetenzübersicht")
        set_label_style(title_label, "section_title")
        self.competencies_container = QWidget()
        self.competencies_layout = QVBoxLayout(self.competencies_container)
        self.competencies_layout.setContentsMargins(0, 0, 0, 0)
        self.competencies_layout.setSpacing(8)
        set_label_style(self.competency_empty_label, "body")
        layout.addWidget(title_label)
        layout.addWidget(self.competencies_container)
        return section

    def _card(self) -> QFrame:
        return create_card()

    def _show_placeholder_message(self, message: str) -> None:
        self.action_feedback_label.setText(message)

    def _request_new_observation(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["observation"])
            return
        self.observation_requested.emit(self.current_student)

    def set_student(
        self,
        student: StudentDetailViewModel | None,
        observations: tuple[ObservationListItem, ...] = (),
        competency_groups: tuple[StudentCompetencySubjectGroup, ...] = (),
    ) -> None:
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
            self.set_observations(())
            self.set_competency_groups(())
            return
        self.name_label.setText(student.display_name)
        self.meta_label.setText(f"{student.group_name} · {student.course_name}")
        self.student_id_label.setText(student.student_id)
        self.group_value_label.setText(student.group_name)
        self.course_value_label.setText(student.course_name)
        self.notes_value_label.setText(student.student_notes or "Keine Notiz hinterlegt.")
        self.action_feedback_label.setText("")
        self.set_observations(observations)
        self.set_competency_groups(competency_groups)

    def set_observations(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        """Render persisted observations for the current profile."""
        self._clear_observations()
        if not observations:
            self.observations_layout.addWidget(
                self._empty_observations_card()
            )
            return
        for observation in observations:
            self.observations_layout.addWidget(
                self._observation_card(observation)
            )

    def _empty_observations_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        self.observation_empty_label.setText(
            PROFILE_SECTION_PLACEHOLDERS["observations_title"]
        )
        hint_label = QLabel(PROFILE_SECTION_PLACEHOLDERS["observations_hint"])
        set_label_style(hint_label, "subtle")
        layout.addWidget(self.observation_empty_label)
        layout.addWidget(hint_label)
        return card

    def _observation_card(self, observation: ObservationListItem) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        details_widget = QWidget()
        details_widget.setVisible(False)
        details_button = QPushButton("Details anzeigen")
        details_button.clicked.connect(
            lambda _checked=False: self._toggle_observation_details(
                details_widget,
                details_button,
            )
        )
        layout.addLayout(self._observation_header(observation, details_button))
        layout.addWidget(self._observation_summary(observation))
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(5)
        details_layout.addWidget(self._observation_field("Notiz", observation.note or "-"))
        competencies_title = QLabel("Kompetenzen")
        set_label_style(competencies_title, "field_label")
        details_layout.addWidget(competencies_title)
        if not observation.competency_ratings:
            empty_competencies = QLabel("Keine Kompetenzen hinterlegt.")
            set_label_style(empty_competencies, "subtle")
            details_layout.addWidget(empty_competencies)
            details_layout.addLayout(self._observation_actions(observation))
            layout.addWidget(details_widget)
            return card
        for rating in observation.competency_ratings:
            details_layout.addWidget(self._rating_row(rating))
        details_layout.addLayout(self._observation_actions(observation))
        layout.addWidget(details_widget)
        return card

    def _observation_header(
        self,
        observation: ObservationListItem,
        details_button: QPushButton,
    ) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        date_label = QLabel(observation.date_text)
        set_label_style(date_label, "card_title")
        subject_label = QLabel(observation.subject_display_name or "-")
        set_label_style(subject_label, "muted")
        header.addWidget(date_label, 0)
        header.addWidget(subject_label, 1)
        header.addWidget(details_button, 0)
        return header

    def _observation_summary(self, observation: ObservationListItem) -> QLabel:
        preview = self._note_preview(observation.note)
        competency_count = len(observation.competency_ratings)
        competency_label = (
            "1 Kompetenz"
            if competency_count == 1
            else f"{competency_count} Kompetenzen"
        )
        parts = [observation.context or "-", preview, competency_label]
        summary = QLabel(" · ".join(part for part in parts if part))
        summary.setWordWrap(True)
        set_label_style(summary, "body")
        return summary

    def _note_preview(self, note: str, max_length: int = 90) -> str:
        cleaned_note = " ".join(note.split())
        if not cleaned_note:
            return "Keine Notiz"
        if len(cleaned_note) <= max_length:
            return cleaned_note
        return f"{cleaned_note[:max_length].rstrip()}..."

    def _toggle_observation_details(
        self,
        details_widget: QWidget,
        details_button: QPushButton,
    ) -> None:
        details_widget.setVisible(details_widget.isHidden())
        details_button.setText(
            "Details ausblenden"
            if not details_widget.isHidden()
            else "Details anzeigen"
        )

    def _observation_actions(self, observation: ObservationListItem) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 2, 0, 0)
        actions.setSpacing(8)
        edit_button = QPushButton("Bearbeiten")
        delete_button = QPushButton("Löschen")
        edit_button.clicked.connect(
            lambda _checked=False, observation_id=observation.observation_id: (
                self.observation_edit_requested.emit(observation_id)
            )
        )
        delete_button.clicked.connect(
            lambda _checked=False, observation_id=observation.observation_id: (
                self.observation_delete_requested.emit(observation_id)
            )
        )
        actions.addStretch()
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        return actions

    def _observation_field(self, label: str, value: str) -> QLabel:
        field = QLabel(f"{label}: {value}")
        field.setWordWrap(True)
        set_label_style(field, "body")
        return field

    def _rating_row(self, rating: object) -> QLabel:
        rating_label = QLabel(
            f"{getattr(rating, 'rating', '')}  "
            f"{getattr(rating, 'learning_area', '')}"
        )
        rating_label.setWordWrap(True)
        rating_label.setToolTip(getattr(rating, "competency_text", ""))
        detail_parts = (
            getattr(rating, "subject_display_name", ""),
            getattr(rating, "competency_group", ""),
        )
        detail = " · ".join(part for part in detail_parts if part)
        if detail:
            rating_label.setText(f"{rating_label.text()} · {detail}")
        set_label_style(rating_label, "small")
        return rating_label

    def set_competency_groups(
        self,
        competency_groups: tuple[StudentCompetencySubjectGroup, ...],
    ) -> None:
        """Render latest observed competency status grouped by subject."""
        self._clear_layout(self.competencies_layout)
        if not competency_groups:
            self.competencies_layout.addWidget(self._empty_competencies_card())
            return
        for group in competency_groups:
            self.competencies_layout.addWidget(self._competency_group_card(group))

    def _empty_competencies_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        self.competency_empty_label.setText(
            PROFILE_SECTION_PLACEHOLDERS["competencies_title"]
        )
        hint_label = QLabel(PROFILE_SECTION_PLACEHOLDERS["competencies_hint"])
        set_label_style(hint_label, "subtle")
        layout.addWidget(self.competency_empty_label)
        layout.addWidget(hint_label)
        return card

    def _competency_group_card(
        self,
        group: StudentCompetencySubjectGroup,
    ) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        title = QLabel(group.subject_display_name)
        set_label_style(title, "card_title")
        layout.addWidget(title)
        for competency in group.competencies:
            row = QLabel(
                f"{competency.competency_label}: "
                f"{competency.rating_label} · {competency.last_observation_date}"
            )
            row.setWordWrap(True)
            set_label_style(row, "body")
            layout.addWidget(row)
        return card

    def _clear_observations(self) -> None:
        self._clear_layout(self.observations_layout)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            layout_item = layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.setParent(None)
