"""Light student profile screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import (
    PROFILE_ACTION_MESSAGES,
    PROFILE_SECTION_PLACEHOLDERS,
    StudentDetailViewModel,
    StudentReportPreviewViewModel,
)
from src.desktop_app.view_models.observation_view_model import (
    ObservationListItem,
    StudentCompetencySubjectGroup,
    observation_rating_keys,
)
from src.desktop_app.theme import create_card, set_label_style


class StudentProfileScreen(QWidget):
    """Lightweight read-only student profile."""

    DEFAULT_OBSERVATION_LIMIT = 3

    back_requested = Signal()
    observation_requested = Signal(object)
    observation_edit_requested = Signal(str)
    observation_delete_requested = Signal(str)
    competency_confirmation_requested = Signal(str, str, str, str)

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
        self.report_empty_label = QLabel("")
        self.current_observations: tuple[ObservationListItem, ...] = ()
        self.show_all_observations = False
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
        content_layout.addWidget(self._report_preview_card())
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
        self.observation_subject_filter = QComboBox()
        self.observation_rating_filter = QComboBox()
        self.observation_search_input = QLineEdit()
        self.observation_reset_button = QPushButton("Zurücksetzen")
        self.observation_show_all_button = QPushButton("")
        self.observation_show_all_button.setObjectName("ObservationTextActionButton")
        self.observation_show_all_button.clicked.connect(self.toggle_observation_limit)
        self.observations_container = QWidget()
        self.observations_layout = QVBoxLayout(self.observations_container)
        self.observations_layout.setContentsMargins(0, 0, 0, 0)
        self.observations_layout.setSpacing(8)
        set_label_style(self.observation_empty_label, "body")
        layout.addWidget(title_label)
        layout.addWidget(self._observation_filter_card())
        layout.addWidget(self.observations_container)
        layout.addWidget(self.observation_show_all_button)
        return section

    def _observation_filter_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("ObservationFilterBar")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        self.observation_subject_filter.currentIndexChanged.connect(
            lambda _index: self.apply_observation_filters()
        )
        self.observation_rating_filter.addItems(("Alle", "++", "+", "-", "--"))
        self.observation_rating_filter.currentIndexChanged.connect(
            lambda _index: self.apply_observation_filters()
        )
        self.observation_search_input.setPlaceholderText(
            "Kontext, Notiz oder Kompetenz suchen"
        )
        self.observation_search_input.textChanged.connect(
            lambda _text: self.apply_observation_filters()
        )
        self.observation_search_input.setObjectName("ObservationFilterInput")
        self.observation_reset_button.setObjectName("ObservationResetButton")
        self.observation_subject_filter.setMinimumWidth(150)
        self.observation_rating_filter.setMinimumWidth(118)
        self.observation_search_input.setMinimumWidth(190)
        self.observation_search_input.setMaximumWidth(320)
        self.observation_reset_button.clicked.connect(self.reset_observation_filters)
        layout.addWidget(self._filter_label("Fach"))
        layout.addWidget(self.observation_subject_filter, 2)
        layout.addWidget(self._filter_label("Bewertung"))
        layout.addWidget(self.observation_rating_filter, 0)
        layout.addWidget(self.observation_search_input, 1)
        layout.addWidget(self.observation_reset_button, 0)
        return card

    def _filter_label(self, label: str) -> QLabel:
        filter_label = QLabel(label)
        set_label_style(filter_label, "field_label")
        return filter_label

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

    def _report_preview_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_label = QLabel("Berichtsvorschau")
        set_label_style(title_label, "section_title")
        self.report_preview_container = QWidget()
        self.report_preview_layout = QVBoxLayout(self.report_preview_container)
        self.report_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.report_preview_layout.setSpacing(8)
        set_label_style(self.report_empty_label, "body")
        layout.addWidget(title_label)
        layout.addWidget(self.report_preview_container)
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
        report_preview: StudentReportPreviewViewModel | None = None,
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
            self.set_report_preview(None)
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
        self.set_report_preview(report_preview)

    def set_observations(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        """Render persisted observations for the current profile."""
        self.current_observations = observations
        self.show_all_observations = False
        self._populate_observation_subject_filter(observations)
        self.apply_observation_filters()

    def apply_observation_filters(self) -> None:
        """Render observations matching the profile-local filter state."""
        self._clear_observations()
        if not self.current_observations:
            self.observation_show_all_button.setVisible(False)
            self.observations_layout.addWidget(
                self._empty_observations_card()
            )
            return
        filtered_observations = self._filtered_observations()
        if not filtered_observations:
            self.observation_show_all_button.setVisible(False)
            self.observations_layout.addWidget(
                self._empty_observations_card(
                    "Keine passenden Beobachtungen.",
                    "Filter ändern oder zurücksetzen.",
                )
            )
            return
        visible_observations = self._visible_observations(filtered_observations)
        for observation in visible_observations:
            self.observations_layout.addWidget(
                self._observation_card(observation)
            )
        self._update_observation_limit_action(filtered_observations)

    def _empty_observations_card(
        self,
        title: str | None = None,
        hint: str | None = None,
    ) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        self.observation_empty_label.setText(
            title or PROFILE_SECTION_PLACEHOLDERS["observations_title"]
        )
        hint_label = QLabel(hint or PROFILE_SECTION_PLACEHOLDERS["observations_hint"])
        set_label_style(hint_label, "subtle")
        layout.addWidget(self.observation_empty_label)
        layout.addWidget(hint_label)
        return card

    def _populate_observation_subject_filter(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        current_subject = str(self.observation_subject_filter.currentData() or "")
        subjects: dict[str, str] = {}
        for observation in observations:
            subject_label = observation.subject_display_name or "-"
            subjects.setdefault(subject_label, subject_label)
        self.observation_subject_filter.blockSignals(True)
        try:
            self.observation_subject_filter.clear()
            self.observation_subject_filter.addItem("Alle", "")
            for subject_label in subjects:
                self.observation_subject_filter.addItem(subject_label, subject_label)
            subject_index = self.observation_subject_filter.findData(current_subject)
            if subject_index >= 0:
                self.observation_subject_filter.setCurrentIndex(subject_index)
        finally:
            self.observation_subject_filter.blockSignals(False)
        self._set_observation_filters_enabled(bool(observations))

    def _set_observation_filters_enabled(self, enabled: bool) -> None:
        self.observation_subject_filter.setEnabled(enabled)
        self.observation_rating_filter.setEnabled(enabled)
        self.observation_search_input.setEnabled(enabled)
        self.observation_reset_button.setEnabled(enabled)

    def reset_observation_filters(self) -> None:
        """Reset all profile-local observation filters."""
        self.show_all_observations = False
        self.observation_subject_filter.setCurrentIndex(0)
        self.observation_rating_filter.setCurrentIndex(0)
        self.observation_search_input.clear()
        self.apply_observation_filters()

    def toggle_observation_limit(self) -> None:
        """Toggle between the compact observation limit and all observations."""
        self.show_all_observations = not self.show_all_observations
        self.apply_observation_filters()

    def _filtered_observations(self) -> tuple[ObservationListItem, ...]:
        subject_filter = str(self.observation_subject_filter.currentData() or "")
        rating_filter = self.observation_rating_filter.currentText()
        search_text = self.observation_search_input.text().strip().casefold()
        return tuple(
            observation
            for observation in self.current_observations
            if self._matches_observation_filters(
                observation,
                subject_filter,
                rating_filter,
                search_text,
            )
        )

    def _visible_observations(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> tuple[ObservationListItem, ...]:
        if self._observation_filter_is_active() or self.show_all_observations:
            return observations
        return observations[: self.DEFAULT_OBSERVATION_LIMIT]

    def _update_observation_limit_action(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        should_show = (
            not self._observation_filter_is_active()
            and len(observations) > self.DEFAULT_OBSERVATION_LIMIT
        )
        self.observation_show_all_button.setVisible(should_show)
        if not should_show:
            self.observation_show_all_button.setText("")
            return
        if self.show_all_observations:
            self.observation_show_all_button.setText("Weniger anzeigen")
        else:
            self.observation_show_all_button.setText(
                f"Alle Beobachtungen anzeigen ({len(observations)})"
            )

    def _observation_filter_is_active(self) -> bool:
        return any((
            bool(str(self.observation_subject_filter.currentData() or "")),
            self.observation_rating_filter.currentText() != "Alle",
            bool(self.observation_search_input.text().strip()),
        ))

    def _matches_observation_filters(
        self,
        observation: ObservationListItem,
        subject_filter: str,
        rating_filter: str,
        search_text: str,
    ) -> bool:
        if subject_filter and observation.subject_display_name != subject_filter:
            return False
        if rating_filter != "Alle" and not any(
            rating.rating == rating_filter for rating in observation.competency_ratings
        ):
            return False
        if search_text and search_text not in self._observation_search_text(observation):
            return False
        return True

    def _observation_search_text(self, observation: ObservationListItem) -> str:
        search_parts = [
            observation.context,
            observation.note,
            *(
                " ".join((
                    rating.learning_area,
                    rating.competency_group,
                    rating.competency_text,
                    rating.subject_display_name,
                ))
                for rating in observation.competency_ratings
            ),
        ]
        return " ".join(search_parts).casefold()

    def _observation_card(self, observation: ObservationListItem) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        details_widget = QWidget()
        details_widget.setVisible(False)
        details_button = QPushButton("Details anzeigen")
        details_button.setObjectName("ObservationTextActionButton")
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
        edit_button.setObjectName("ObservationTextActionButton")
        delete_button.setObjectName("ObservationTextActionButton")
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
        """Render calculated competency status grouped by subject."""
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

    def set_report_preview(
        self,
        report_preview: StudentReportPreviewViewModel | None,
    ) -> None:
        """Render the derived report preparation for the current profile."""
        self._clear_layout(self.report_preview_layout)
        if report_preview is None or not report_preview.has_content:
            self.report_preview_layout.addWidget(self._empty_report_preview_card())
            return
        for section in report_preview.subject_sections:
            self.report_preview_layout.addWidget(
                self._report_subject_card(section)
            )

    def _empty_report_preview_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        self.report_empty_label.setText("Noch keine Berichtsdaten vorhanden.")
        hint_label = QLabel(
            "Bestätigte Kompetenzstände oder Beobachtungen erscheinen hier."
        )
        set_label_style(hint_label, "subtle")
        layout.addWidget(self.report_empty_label)
        layout.addWidget(hint_label)
        return card

    def _report_subject_card(self, section: object) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title = QLabel(getattr(section, "subject_display_name"))
        set_label_style(title, "card_title")
        layout.addWidget(title)
        layout.addWidget(self._report_bucket(
            "Stärken",
            getattr(section, "strengths"),
        ))
        layout.addWidget(self._report_bucket(
            "Entwicklung",
            getattr(section, "development"),
        ))
        layout.addWidget(self._report_bucket(
            "Unterstützungsbedarf",
            getattr(section, "support_needs"),
        ))
        layout.addWidget(self._report_evidence_block(
            getattr(section, "example_observations")
        ))
        return card

    def _report_bucket(self, title: str, competencies: tuple[object, ...]) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel(title)
        set_label_style(title_label, "field_label")
        layout.addWidget(title_label)
        if not competencies:
            empty_label = QLabel("Keine Einträge.")
            set_label_style(empty_label, "subtle")
            layout.addWidget(empty_label)
            return block
        for competency in competencies:
            line = QLabel(getattr(competency, "display_label"))
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
        return block

    def _report_evidence_block(
        self,
        observations: tuple[object, ...],
    ) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel("Beispielbeobachtungen")
        set_label_style(title_label, "field_label")
        layout.addWidget(title_label)
        if not observations:
            empty_label = QLabel("Keine passenden Beobachtungen.")
            set_label_style(empty_label, "subtle")
            layout.addWidget(empty_label)
            return block
        for observation in observations:
            line = QLabel(getattr(observation, "display_label"))
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
            competencies = QLabel(
                " · ".join(getattr(observation, "competency_labels"))
            )
            competencies.setWordWrap(True)
            set_label_style(competencies, "subtle")
            layout.addWidget(competencies)
        return block

    def _competency_group_card(
        self,
        group: StudentCompetencySubjectGroup,
    ) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        header = QHBoxLayout()
        title = QLabel(group.subject_display_name)
        set_label_style(title, "card_title")
        summary = QLabel(f"{len(group.competencies)} Kompetenzen")
        set_label_style(summary, "subtle")
        details_button = QPushButton("Details ▾")
        details_button.setObjectName("CompetencyGroupDetailsButton")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(summary)
        header.addWidget(details_button)
        layout.addLayout(header)
        details_container = QWidget()
        details_container.setObjectName("CompetencyGroupDetails")
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(4)
        for competency in group.competencies:
            details_layout.addWidget(self._competency_status_row(competency))
        details_container.setVisible(False)
        details_button.clicked.connect(
            lambda _checked=False: self._toggle_competency_group_details(
                details_container,
                details_button,
            )
        )
        layout.addWidget(details_container)
        return card

    def _toggle_competency_group_details(
        self,
        details_container: QWidget,
        details_button: QPushButton,
    ) -> None:
        details_container.setVisible(details_container.isHidden())
        details_button.setText(
            "Details ▾" if details_container.isHidden() else "Details ▴"
        )

    def _competency_status_row(self, competency: object) -> QWidget:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 4)
        layout.setSpacing(2)
        title = QLabel(getattr(competency, "competency_label"))
        title.setWordWrap(True)
        set_label_style(title, "body")
        status = QLabel(getattr(competency, "confirmation_status_label"))
        set_label_style(status, "small")
        history = QLabel(
            f"Verlauf: {getattr(competency, 'rating_history_label')}"
        )
        history.setWordWrap(True)
        set_label_style(history, "small")
        meta = QLabel(
            f"{getattr(competency, 'observation_count_label')} · "
            f"zuletzt beobachtet: {getattr(competency, 'last_observation_date')}"
        )
        set_label_style(meta, "subtle")
        confirmation_meta = QLabel(getattr(competency, "confirmation_meta_label"))
        set_label_style(confirmation_meta, "subtle")
        confirmation_meta.setVisible(bool(confirmation_meta.text()))
        layout.addWidget(title)
        layout.addWidget(status)
        layout.addWidget(history)
        layout.addWidget(meta)
        layout.addWidget(confirmation_meta)
        layout.addLayout(self._competency_confirmation_actions(competency))
        return row

    def _competency_confirmation_actions(self, competency: object) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
        rating_select = QComboBox()
        rating_select.setObjectName("CompetencyConfirmationRatingSelect")
        rating_select.addItems(observation_rating_keys())
        selected_rating = (
            getattr(competency, "confirmed_rating")
            or getattr(competency, "rating")
        )
        selected_index = rating_select.findText(selected_rating)
        if selected_index >= 0:
            rating_select.setCurrentIndex(selected_index)
        adopt_button = QPushButton("Vorschlag übernehmen")
        confirm_button = QPushButton("Bestätigen")
        adopt_button.clicked.connect(
            lambda _checked=False: self._request_competency_confirmation(
                competency,
                getattr(competency, "rating"),
            )
        )
        confirm_button.clicked.connect(
            lambda _checked=False: self._request_competency_confirmation(
                competency,
                rating_select.currentText(),
            )
        )
        actions.addWidget(rating_select)
        actions.addWidget(adopt_button)
        actions.addWidget(confirm_button)
        actions.addStretch(1)
        return actions

    def _request_competency_confirmation(
        self,
        competency: object,
        confirmed_rating: str,
    ) -> None:
        if self.current_student is None:
            return
        self.competency_confirmation_requested.emit(
            self.current_student.student_id,
            getattr(competency, "competency_id"),
            confirmed_rating,
            "",
        )

    def _clear_observations(self) -> None:
        self._clear_layout(self.observations_layout)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            layout_item = layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.setParent(None)
