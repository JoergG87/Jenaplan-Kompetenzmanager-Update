"""Light student profile screen for the PySide6 desktop app."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.view_models.student_view_model import (
    PROFILE_ACTION_MESSAGES,
    PROFILE_SECTION_PLACEHOLDERS,
    REPORT_NO_OBSERVATIONS_MESSAGE,
    StudentDetailViewModel,
    StudentDocumentViewModel,
    StudentReportPreviewViewModel,
    build_student_profile_overview,
    documentation_summary_from_subjects,
    format_student_report_preview_text,
)
from src.desktop_app.view_models.observation_view_model import (
    ObservationListItem,
    StudentCompetencyCockpitLearningAreaViewModel,
    StudentCompetencyCockpitSubjectViewModel,
    StudentCompetencyCockpitTopicViewModel,
    StudentCompetencyCockpitViewModel,
    StudentDocumentationSubjectStatus,
    StudentCompetencySubjectGroup,
)
from src.desktop_app.theme import create_card, set_label_style


class StudentProfileScreen(QWidget):
    student_edit_requested = Signal(str)
    """Lightweight read-only student profile."""

    DEFAULT_OBSERVATION_LIMIT = 3

    back_requested = Signal()
    observation_requested = Signal(object)
    observation_edit_requested = Signal(str)
    observation_delete_requested = Signal(str)
    document_add_requested = Signal(str)
    document_remove_requested = Signal(str, str)
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
        self.overview_summary_layout = QVBoxLayout()
        self.overview_recent_layout = QVBoxLayout()
        self.overview_documentation_layout = QVBoxLayout()
        self.overview_development_layout = QVBoxLayout()
        self.observation_empty_label = QLabel("")
        self.competency_empty_label = QLabel("")
        self.documentation_empty_label = QLabel("")
        self.documents_empty_label = QLabel("")
        self.documents_feedback_label = QLabel("")
        self.report_empty_label = QLabel("")
        self.report_feedback_label = QLabel("")
        self.report_copy_button = QPushButton("Bericht kopieren")
        self.report_export_button = QPushButton("Als Text exportieren")
        self.report_copy_button.setEnabled(False)
        self.report_export_button.setEnabled(False)
        self.current_observations: tuple[ObservationListItem, ...] = ()
        self.current_documents: tuple[StudentDocumentViewModel, ...] = ()
        self.current_report_preview: StudentReportPreviewViewModel | None = None
        self.show_all_observations = False
        self._competency_expanded_keys: set[str] = set()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.back_button.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_button)
        header.addStretch()
        layout.addLayout(header)

        set_label_style(self.name_label, "screen_title")
        set_label_style(self.meta_label, "muted")
        set_label_style(self.student_id_label, "small")
        layout.addWidget(self.name_label)
        layout.addWidget(self.meta_label)

        self.profile_tabs = QTabWidget()
        self.profile_tabs.addTab(self._scrollable_tab(self._overview_tab()), "Überblick")
        self.profile_tabs.addTab(
            self._scrollable_tab(self._observations_card()),
            "Beobachtungen",
        )

        self.profile_tabs.addTab(
            self._scrollable_tab(self._competency_cockpit_tab()),
            "Kompetenzen",
        )

        self.profile_tabs.addTab(
            self._scrollable_tab(self._report_preview_card()),
            "Bericht",
        )
        self.profile_tabs.addTab(
            self._scrollable_tab(self._documents_card()),
            "Dateien",
        )
        layout.addWidget(self.profile_tabs, 1)

    def _scrollable_tab(self, content: QWidget) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 8, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(content)
        wrapper_layout.addStretch(1)

        scroll_area.setWidget(wrapper)
        return scroll_area

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("Überblick")
        set_label_style(title, "section_title")
        header.addWidget(title)
        header.addStretch(1)

        add_observation_button = QPushButton("+ Beobachtung")
        add_observation_button.clicked.connect(self._request_new_observation)
        header.addWidget(add_observation_button)

        add_document_button = QPushButton("+ Datei hinzufügen")
        add_document_button.clicked.connect(self._request_add_document)
        header.addWidget(add_document_button)

        edit_student_button = QPushButton("Schüler bearbeiten")
        edit_student_button.clicked.connect(self._request_edit_student)
        header.addWidget(edit_student_button)

        layout.addLayout(header)
        layout.addWidget(self._basis_data_card())
        layout.addWidget(self._overview_summary_card())
        layout.addWidget(
            self._overview_list_card("Entwicklung", self.overview_development_layout)
        )
        layout.addWidget(
            self._overview_list_card("Letzte Beobachtungen", self.overview_recent_layout)
        )
        layout.addWidget(
            self._overview_list_card(
                "Dokumentationsstand",
                self.overview_documentation_layout,
            )
        )
        layout.addStretch(1)
        return tab

    def _overview_summary_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title = QLabel("Halbjahresblick")
        set_label_style(title, "card_title")
        layout.addWidget(title)
        layout.addLayout(self.overview_summary_layout)
        return card

    def _overview_list_card(self, title: str, content_layout: QVBoxLayout) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        title_label = QLabel(title)
        set_label_style(title_label, "card_title")
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        layout.addWidget(title_label)
        layout.addLayout(content_layout)
        return card

    def _actions_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Schnellaktionen")
        set_label_style(title, "card_title")
        button_row = QHBoxLayout()
        observation_button = QPushButton("+ Beobachtung")
        document_button = QPushButton("+ Datei hinzufügen")
        edit_button = QPushButton("Schüler bearbeiten")
        observation_button.clicked.connect(self._request_new_observation)
        document_button.clicked.connect(self._request_add_document)
        edit_button.clicked.connect(self._request_edit_student)
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

    def _competency_cockpit_tab(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)
        title = QLabel("Kompetenz-Cockpit")
        set_label_style(title, "section_title")
        hint = QLabel(
            "Dokumentationsstand nach Fach, Kompetenzbereich und Thema. "
            "Alle Bereiche starten geschlossen."
        )
        hint.setWordWrap(True)
        set_label_style(hint, "subtle")
        self.competency_cockpit_container = QWidget()
        self.competency_cockpit_layout = QVBoxLayout(
            self.competency_cockpit_container
        )
        self.competency_cockpit_layout.setContentsMargins(0, 0, 0, 0)
        self.competency_cockpit_layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.competency_cockpit_container)
        return section

    def _documents_card(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title_label = QLabel("Dokumente & Medien")
        set_label_style(title_label, "section_title")
        add_button = QPushButton("+ Datei hinzufügen")
        add_button.clicked.connect(self._request_add_document)
        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(add_button)
        self.documents_container = QWidget()
        self.documents_layout = QVBoxLayout(self.documents_container)
        self.documents_layout.setContentsMargins(0, 0, 0, 0)
        self.documents_layout.setSpacing(8)
        set_label_style(self.documents_empty_label, "body")
        set_label_style(self.documents_feedback_label, "subtle")
        layout.addLayout(header)
        layout.addWidget(self.documents_feedback_label)
        layout.addWidget(self.documents_container)
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
        set_label_style(self.report_feedback_label, "subtle")
        self.report_copy_button.clicked.connect(self.copy_report_text_to_clipboard)
        self.report_export_button.clicked.connect(self.export_report_text)
        layout.addWidget(title_label)
        layout.addLayout(self._report_action_row())
        layout.addWidget(self.report_feedback_label)
        layout.addWidget(self.report_preview_container)
        return section

    def _report_action_row(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        actions.addWidget(self.report_copy_button)
        actions.addWidget(self.report_export_button)
        actions.addStretch(1)
        return actions

    def _card(self) -> QFrame:
        return create_card()

    def _make_clickable_card(
        self,
        card: QFrame,
        action: Callable[[], None],
        tooltip: str,
    ) -> None:
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setToolTip(tooltip)

        def handle_mouse_release(event: object) -> None:
            button = getattr(event, "button", lambda: None)()
            if button != Qt.MouseButton.LeftButton:
                getattr(event, "ignore", lambda: None)()
                return
            position = (
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            child = card.childAt(position)
            while child is not None and child is not card:
                if isinstance(child, (QPushButton, QComboBox, QLineEdit)):
                    getattr(event, "ignore", lambda: None)()
                    return
                child = child.parentWidget()
            action()
            getattr(event, "accept", lambda: None)()

        card.mouseReleaseEvent = handle_mouse_release

    def _show_placeholder_message(self, message: str) -> None:
        self.action_feedback_label.setText(message)

    def _request_new_observation(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["observation"])
            return
        self.observation_requested.emit(self.current_student)

    def _request_add_document(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["document"])
            return
        self.document_add_requested.emit(self.current_student.student_id)

    def _request_edit_student(self) -> None:
        if self.current_student is None:
            self._show_placeholder_message(PROFILE_ACTION_MESSAGES["edit"])
            return
        self.student_edit_requested.emit(self.current_student.student_id)

    def _render_profile_overview(
        self,
        student: StudentDetailViewModel | None,
        observations: tuple[ObservationListItem, ...],
        competency_groups: tuple[StudentCompetencySubjectGroup, ...],
        documentation_statuses: tuple[StudentDocumentationSubjectStatus, ...],
    ) -> None:
        self._clear_layout(self.overview_summary_layout)
        self._clear_layout(self.overview_recent_layout)
        self._clear_layout(self.overview_documentation_layout)
        self._clear_layout(self.overview_development_layout)
        if student is None:
            self.overview_summary_layout.addWidget(
                self._overview_text("Kein Schüler ausgewählt.", "body")
            )
            return
        overview = build_student_profile_overview(
            observations,
            competency_groups,
            documentation_statuses,
        )
        self.overview_summary_layout.addWidget(
            self._overview_text(
                f"{overview.observation_count_label} · {overview.documentation_label}",
                "body",
            )
        )
        self.overview_summary_layout.addWidget(
            self._overview_text(overview.latest_observation_label, "small")
        )
        if overview.reliability_hint:
            self.overview_summary_layout.addWidget(
                self._overview_text(overview.reliability_hint, "subtle")
            )
        self.overview_summary_layout.addWidget(
            self._overview_subsection("Stärken", overview.strengths, "✓")
        )
        self.overview_summary_layout.addWidget(
            self._overview_subsection(
                "Im Blick behalten",
                overview.watch_items,
                "!",
                empty_text="Aktuell kein besonderer Beobachtungshinweis aus den vorhandenen Daten.",
            )
        )
        self._render_overview_recent_observations(observations)
        self._render_overview_documentation(documentation_statuses)
        self._render_overview_development(overview.development_items)

    def _overview_text(self, text: str, style: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        set_label_style(label, style)
        return label

    def _overview_subsection(
        self,
        title: str,
        items: tuple[str, ...],
        marker: str,
        *,
        empty_text: str = "Noch zu wenig Beobachtungen für eine verlässliche Einschätzung.",
    ) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(3)
        title_label = QLabel(title)
        set_label_style(title_label, "field_label")
        layout.addWidget(title_label)
        if not items:
            layout.addWidget(self._overview_text(empty_text, "subtle"))
            return section
        for item in items:
            layout.addWidget(self._overview_text(f"{marker} {item}", "small"))
        return section

    def _render_overview_recent_observations(
        self,
        observations: tuple[ObservationListItem, ...],
    ) -> None:
        if not observations:
            self.overview_recent_layout.addWidget(
                self._overview_text("Noch keine Beobachtungen dokumentiert.", "subtle")
            )
            return
        for observation in sorted(
            observations,
            key=lambda item: item.date_text,
            reverse=True,
        )[:3]:
            parts = [
                observation.date_text,
                observation.subject_display_name,
                observation.context,
                self._note_preview(observation.note, 72),
            ]
            self.overview_recent_layout.addWidget(
                self._overview_text(" · ".join(part for part in parts if part), "small")
            )

    def _render_overview_documentation(
        self,
        statuses: tuple[StudentDocumentationSubjectStatus, ...],
    ) -> None:
        if not statuses:
            self.overview_documentation_layout.addWidget(
                self._overview_text("Noch kein Kompetenzkatalog verfügbar.", "subtle")
            )
            return
        summary = documentation_summary_from_subjects(statuses)
        self.overview_documentation_layout.addWidget(
            self._overview_text(summary.profile_summary_label, "body")
        )
        if summary.weak_subjects_label:
            self.overview_documentation_layout.addWidget(
                self._overview_text(summary.weak_subjects_label, "subtle")
            )
        details_button = QPushButton("Details anzeigen")
        details_button.setObjectName("OverviewDocumentationDetailsButton")
        details_container = QWidget()
        details_container.setObjectName("OverviewDocumentationDetails")
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(4)
        for status in statuses:
            details_layout.addWidget(self._documentation_subject_details(status))
        details_container.setVisible(False)
        details_button.clicked.connect(
            lambda _checked=False: self._toggle_documentation_status_details(
                details_container,
                details_button,
            )
        )
        self.overview_documentation_layout.addWidget(details_button)
        self.overview_documentation_layout.addWidget(details_container)

    def _render_overview_development(self, development_items: tuple[str, ...]) -> None:
        if not development_items:
            self.overview_development_layout.addWidget(
                self._overview_text(
                    "Sichtbare Entwicklung erscheint hier nach mehreren Beobachtungen.",
                    "subtle",
                )
            )
            return
        for item in development_items:
            self.overview_development_layout.addWidget(
                self._overview_text(item, "small")
            )

    def set_student(
        self,
        student: StudentDetailViewModel | None,
        observations: tuple[ObservationListItem, ...] = (),
        competency_groups: tuple[StudentCompetencySubjectGroup, ...] = (),
        report_preview: StudentReportPreviewViewModel | None = None,
        documentation_statuses: tuple[StudentDocumentationSubjectStatus, ...] = (),
        documents: tuple[StudentDocumentViewModel, ...] = (),
        competency_cockpit: StudentCompetencyCockpitViewModel | None = None,
    ) -> None:
        """Render selected student or empty state."""
        previous_student_id = (
            self.current_student.student_id
            if self.current_student is not None
            else None
        )
        previous_tab_index = self.profile_tabs.currentIndex()

        self.current_student = student
        should_reset_tab = (
            student is None
            or previous_student_id is None
            or previous_student_id != student.student_id
        )
        if should_reset_tab:
            self.profile_tabs.setCurrentIndex(0)
            self._competency_expanded_keys.clear()

        if student is None:
            self.name_label.setText("Kein Schüler ausgewählt")
            self.meta_label.setText("")
            self.student_id_label.setText("")
            self.group_value_label.setText("")
            self.course_value_label.setText("")
            self.notes_value_label.setText("")
            self.action_feedback_label.setText("")
            self.set_observations(())
            self.set_competency_cockpit(None)
            self.set_report_preview(None)
            self.set_documents(())
            self._render_profile_overview(None, (), (), ())
            return
        self.name_label.setText(student.display_name)
        self.meta_label.setText(f"{student.group_name} · {student.course_name}")
        self.student_id_label.setText("")
        self.group_value_label.setText(student.group_name)
        self.course_value_label.setText(student.course_name)
        self.notes_value_label.setText(student.student_notes or "Keine Notiz hinterlegt.")
        self.action_feedback_label.setText("")
        self._render_profile_overview(
            student,
            observations,
            competency_groups,
            documentation_statuses,
        )
        self.set_observations(observations)
        self.set_competency_cockpit(competency_cockpit)
        self.set_report_preview(report_preview)
        self.set_documents(documents)

        if not should_reset_tab and 0 <= previous_tab_index < self.profile_tabs.count():
            self.profile_tabs.setCurrentIndex(previous_tab_index)

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

        empty_label = QLabel(
            title or PROFILE_SECTION_PLACEHOLDERS["observations_title"]
        )
        empty_label.setWordWrap(True)
        set_label_style(empty_label, "body")

        hint_label = QLabel(hint or PROFILE_SECTION_PLACEHOLDERS["observations_hint"])
        hint_label.setWordWrap(True)
        set_label_style(hint_label, "subtle")

        layout.addWidget(empty_label)
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
        def toggle_details() -> None:
            self._toggle_observation_details(details_widget, details_button)

        details_button.clicked.connect(lambda _checked=False: toggle_details())
        self._make_clickable_card(card, toggle_details, "Details anzeigen")
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
            details_layout.addWidget(self._observation_attachments_block(observation))
            details_layout.addLayout(self._observation_actions(observation))
            layout.addWidget(details_widget)
            return card
        for rating in observation.competency_ratings:
            details_layout.addWidget(self._rating_row(rating))
        details_layout.addWidget(self._observation_attachments_block(observation))
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

        attachment_count = len(observation.attachments)
        attachment_label = ""
        if attachment_count == 1:
            attachment_label = "1 Anhang"
        elif attachment_count > 1:
            attachment_label = f"{attachment_count} Anhänge"

        parts = [
            observation.context or "-",
            preview,
            competency_label,
            attachment_label,
        ]
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

    def _observation_attachments_block(
        self,
        observation: ObservationListItem,
    ) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)
        title = QLabel("Dokumente & Medien")
        set_label_style(title, "field_label")
        layout.addWidget(title)
        if not observation.attachments:
            empty = QLabel("Keine Anhänge hinterlegt.")
            set_label_style(empty, "subtle")
            layout.addWidget(empty)
            return block
        for document in observation.attachments:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            line = QLabel(
                f"{getattr(document, 'document_type', '')} · "
                f"{getattr(document, 'display_title', '')}"
            )
            line.setWordWrap(True)
            set_label_style(line, "small")

            open_button = QPushButton("Öffnen")
            open_button.clicked.connect(
                lambda _checked=False, file_path=document.file_path: (
                    self.open_document_file(file_path)
                )
            )

            row_layout.addWidget(line, 1)
            row_layout.addWidget(open_button, 0)
            layout.addWidget(row)
        return block

    def _documentation_subject_details(
        self,
        status: StudentDocumentationSubjectStatus,
    ) -> QWidget:
        detail = QWidget()
        layout = QVBoxLayout(detail)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)
        subject_label = QLabel(status.subject_display_name)
        set_label_style(subject_label, "field_label")
        count_label = QLabel(
            f"{status.documented_count}/{status.total_count} Lernbereiche"
        )
        set_label_style(count_label, "small")
        progress_label = QLabel(status.progress_label)
        progress_label.setWordWrap(True)
        set_label_style(progress_label, "small")
        layout.addWidget(subject_label)
        layout.addWidget(count_label)
        layout.addWidget(progress_label)
        if status.missing_competencies:
            suitable_labels = ", ".join(
                competency.competency_label
                for competency in status.missing_competencies
            )
            next_observations_label = QLabel(
                f"Für nächste Beobachtungen geeignet: {suitable_labels}"
            )
            next_observations_label.setWordWrap(True)
            set_label_style(next_observations_label, "subtle")
            layout.addWidget(next_observations_label)
        elif status.documented_count < status.total_count:
            open_label = QLabel("Noch offen für Beobachtungen.")
            open_label.setWordWrap(True)
            set_label_style(open_label, "subtle")
            layout.addWidget(open_label)
        return detail

    def _toggle_documentation_status_details(
        self,
        details_container: QWidget,
        details_button: QPushButton,
    ) -> None:
        details_container.setVisible(details_container.isHidden())
        details_button.setText(
            "Details anzeigen"
            if details_container.isHidden()
            else "Details ausblenden"
        )

    def set_competency_cockpit(
        self,
        cockpit: StudentCompetencyCockpitViewModel | None,
    ) -> None:
        """Render the read-only cockpit from the canonical Sprint-6B projection."""
        self._clear_layout(self.competency_cockpit_layout)
        if cockpit is None or (not cockpit.subjects and not cockpit.historical_subjects):
            self.competency_cockpit_layout.addWidget(
                self._empty_competency_cockpit_card()
            )
            return
        for subject in cockpit.subjects:
            self.competency_cockpit_layout.addWidget(
                self._cockpit_subject_card(subject, historical=False)
            )
        if cockpit.historical_subjects:
            self.competency_cockpit_layout.addWidget(
                self._historical_competency_section(cockpit.historical_subjects)
            )

    def _empty_competency_cockpit_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        message = QLabel("Noch keine Kompetenzprojektion vorhanden.")
        set_label_style(message, "body")
        layout.addWidget(message)
        return card

    def _cockpit_subject_card(
        self,
        subject: StudentCompetencyCockpitSubjectViewModel,
        *,
        historical: bool,
    ) -> QFrame:
        key = f"{'historical' if historical else 'current'}:subject:{subject.subject_id}"
        card = self._card()
        card.setObjectName("CompetencyCockpitSubjectCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(7)
        header = QHBoxLayout()
        title = QLabel(subject.subject_display_name)
        set_label_style(title, "card_title")
        count = QLabel(
            f"{subject.documented_count} / {subject.total_count} Kompetenzen dokumentiert"
        )
        set_label_style(count, "small")
        button = QPushButton("Öffnen ▾")
        button.setObjectName("CompetencyCockpitSubjectButton")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        header.addWidget(button)
        layout.addLayout(header)
        layout.addWidget(self._cockpit_progress(subject.progress_percent))
        details = QWidget()
        details.setObjectName("CompetencyCockpitSubjectDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 5, 0, 0)
        details_layout.setSpacing(7)
        for area in subject.learning_areas:
            details_layout.addWidget(
                self._cockpit_learning_area_card(
                    subject.subject_id,
                    area,
                    historical=historical,
                )
            )
        self._configure_cockpit_toggle(key, details, button, "Öffnen ▾", "Schließen ▴")
        layout.addWidget(details)
        self._make_clickable_card(
            card,
            lambda: self._toggle_cockpit_section(
                key, details, button, "Öffnen ▾", "Schließen ▴"
            ),
            "Fach öffnen",
        )
        return card

    def _cockpit_learning_area_card(
        self,
        subject_id: str,
        area: StudentCompetencyCockpitLearningAreaViewModel,
        *,
        historical: bool,
    ) -> QFrame:
        key = (
            f"{'historical' if historical else 'current'}:area:"
            f"{subject_id}:{area.learning_area}"
        )
        card = self._card()
        card.setObjectName("CompetencyCockpitLearningAreaCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel(area.learning_area)
        set_label_style(title, "field_label")
        count = QLabel(f"{area.documented_count} / {area.total_count}")
        set_label_style(count, "small")
        button = QPushButton("Öffnen ▾")
        button.setObjectName("CompetencyCockpitLearningAreaButton")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        header.addWidget(button)
        layout.addLayout(header)
        layout.addWidget(self._cockpit_progress(area.progress_percent))
        details = QWidget()
        details.setObjectName("CompetencyCockpitLearningAreaDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(6)
        for topic in area.topics:
            details_layout.addWidget(
                self._cockpit_topic_card(
                    subject_id,
                    area.learning_area,
                    topic,
                    historical=historical,
                )
            )
        self._configure_cockpit_toggle(key, details, button, "Öffnen ▾", "Schließen ▴")
        layout.addWidget(details)
        return card

    def _cockpit_topic_card(
        self,
        subject_id: str,
        learning_area: str,
        topic: StudentCompetencyCockpitTopicViewModel,
        *,
        historical: bool,
    ) -> QFrame:
        key = (
            f"{'historical' if historical else 'current'}:topic:"
            f"{subject_id}:{learning_area}:{topic.competency_group}"
        )
        card = self._card()
        card.setObjectName("CompetencyCockpitTopicCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        header = QHBoxLayout()
        title = QLabel(topic.competency_group)
        set_label_style(title, "body")
        count = QLabel(f"{topic.documented_count} / {topic.total_count}")
        set_label_style(count, "subtle")
        button = QPushButton("Öffnen ▾")
        button.setObjectName("CompetencyCockpitTopicButton")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        header.addWidget(button)
        layout.addLayout(header)
        details = QWidget()
        details.setObjectName("CompetencyCockpitTopicDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(3)
        for competency in topic.competencies:
            details_layout.addWidget(self._cockpit_competency_row(competency))
        self._configure_cockpit_toggle(key, details, button, "Öffnen ▾", "Schließen ▴")
        layout.addWidget(details)
        return card

    def _cockpit_competency_row(self, competency: object) -> QWidget:
        row = QWidget()
        row.setObjectName("CompetencyCockpitCompetencyRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(3)
        documented = getattr(competency, "documentation_state") != "undocumented"
        button = QPushButton(
            f"{'☑' if documented else '☐'} {getattr(competency, 'competency_label')}"
        )
        button.setObjectName("CompetencyCockpitCompetencyButton")
        details = self._cockpit_competency_details(competency)
        details.setObjectName("CompetencyCockpitCompetencyDetails")
        key = f"competency:{getattr(competency, 'competency_id')}"
        self._configure_cockpit_toggle(key, details, button, button.text(), button.text())
        layout.addWidget(button)
        layout.addWidget(details)
        return row

    def _cockpit_competency_details(self, competency: object) -> QFrame:
        details = self._card()
        layout = QVBoxLayout(details)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        rows = (
            (
                "Kompetenz",
                getattr(competency, "competency_text")
                or getattr(competency, "competency_label"),
            ),
            ("Dokumentationszustand", getattr(competency, "documentation_state_label")),
            ("Bestätigter Stand", getattr(competency, "confirmed_status_label")),
            ("Anzahl Beobachtungen", getattr(competency, "observation_count_label")),
            (
                "Letzte Beobachtung",
                getattr(competency, "last_observation_date")
                or "Keine Beobachtung",
            ),
        )
        for label, value in rows:
            line = QLabel(f"{label}: {value}")
            line.setWordWrap(True)
            set_label_style(line, "small")
            layout.addWidget(line)
        proposal = getattr(competency, "observed_proposal")
        if proposal:
            proposal_label = QLabel(f"Vorschlag aus Beobachtungen: {proposal}")
            set_label_style(proposal_label, "small")
            layout.addWidget(proposal_label)
        observations_button = QPushButton("Beobachtungen anzeigen")
        observations_button.setObjectName("CompetencyCockpitObservationsButton")
        observations_button.clicked.connect(self._show_observations_tab)
        layout.addWidget(observations_button, 0, Qt.AlignmentFlag.AlignLeft)
        return details

    def _historical_competency_section(
        self,
        subjects: tuple[StudentCompetencyCockpitSubjectViewModel, ...],
    ) -> QFrame:
        key = "historical"
        card = self._card()
        card.setObjectName("CompetencyCockpitHistoricalCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        button = QPushButton("Historisch dokumentiert ▾")
        button.setObjectName("CompetencyCockpitHistoricalButton")
        details = QWidget()
        details.setObjectName("CompetencyCockpitHistoricalDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 6, 0, 0)
        details_layout.setSpacing(7)
        for subject in subjects:
            details_layout.addWidget(self._cockpit_subject_card(subject, historical=True))
        self._configure_cockpit_toggle(
            key, details, button, "Historisch dokumentiert ▾", "Historisch dokumentiert ▴"
        )
        layout.addWidget(button)
        layout.addWidget(details)
        return card

    def _cockpit_progress(self, percent: int) -> QProgressBar:
        progress = QProgressBar()
        progress.setObjectName("CompetencyCockpitProgressBar")
        progress.setRange(0, 100)
        progress.setValue(percent)
        progress.setTextVisible(False)
        progress.setAccessibleName(f"Dokumentationsfortschritt {percent} Prozent")
        return progress

    def _configure_cockpit_toggle(
        self,
        key: str,
        details: QWidget,
        button: QPushButton,
        collapsed_text: str,
        expanded_text: str,
    ) -> None:
        expanded = key in self._competency_expanded_keys
        details.setVisible(expanded)
        button.setText(expanded_text if expanded else collapsed_text)
        button.clicked.connect(
            lambda _checked=False: self._toggle_cockpit_section(
                key, details, button, collapsed_text, expanded_text
            )
        )

    def _toggle_cockpit_section(
        self,
        key: str,
        details: QWidget,
        button: QPushButton,
        collapsed_text: str,
        expanded_text: str,
    ) -> None:
        expanded = details.isHidden()
        details.setVisible(expanded)
        if expanded:
            self._competency_expanded_keys.add(key)
        else:
            self._competency_expanded_keys.discard(key)
        button.setText(expanded_text if expanded else collapsed_text)

    def _show_observations_tab(self) -> None:
        self.profile_tabs.setCurrentIndex(1)

    def set_report_preview(
        self,
        report_preview: StudentReportPreviewViewModel | None,
    ) -> None:
        """Render the derived report preparation for the current profile."""
        self.current_report_preview = report_preview
        has_report_text = self.current_student is not None and report_preview is not None
        self.report_copy_button.setEnabled(has_report_text)
        self.report_export_button.setEnabled(has_report_text)
        self.report_feedback_label.setText("")
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

        empty_label = QLabel(REPORT_NO_OBSERVATIONS_MESSAGE)
        empty_label.setWordWrap(True)
        set_label_style(empty_label, "body")

        hint_label = QLabel(
            "Berichtsvorschau erscheint nach aktiven Beobachtungen."
        )
        hint_label.setWordWrap(True)
        set_label_style(hint_label, "subtle")

        layout.addWidget(empty_label)
        layout.addWidget(hint_label)
        return card

    def set_documents(
        self,
        documents: tuple[StudentDocumentViewModel, ...],
    ) -> None:
        """Render student documents and media."""
        self.current_documents = documents
        self.documents_feedback_label.setText("")
        self._clear_layout(self.documents_layout)
        if not documents:
            self.documents_layout.addWidget(self._empty_documents_card())
            return
        for document in documents:
            self.documents_layout.addWidget(self._document_row(document))

    def _empty_documents_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        empty_label = QLabel(PROFILE_SECTION_PLACEHOLDERS["documents_title"])
        empty_label.setWordWrap(True)
        set_label_style(empty_label, "body")

        hint_label = QLabel(PROFILE_SECTION_PLACEHOLDERS["documents_hint"])
        hint_label.setWordWrap(True)
        set_label_style(hint_label, "subtle")

        layout.addWidget(empty_label)
        layout.addWidget(hint_label)
        return card

    def _document_row(self, document: StudentDocumentViewModel) -> QFrame:
        row = self._card()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        text_block = QWidget()
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        title = QLabel(f"{document.document_type} · {document.display_title}")
        title.setWordWrap(True)
        set_label_style(title, "body")
        meta_parts = [document.created_date_label]
        if document.observation_link_label:
            meta_parts.append(document.observation_link_label)
        meta = QLabel(" · ".join(meta_parts))
        set_label_style(meta, "subtle")
        text_layout.addWidget(title)
        text_layout.addWidget(meta)
        open_button = QPushButton("Öffnen")
        open_button.clicked.connect(
            lambda _checked=False, file_path=document.file_path: (
                self.open_document_file(file_path)
            )
        )
        remove_button = QPushButton("Entfernen")
        remove_button.setObjectName("DocumentRemoveButton")
        remove_button.clicked.connect(
            lambda _checked=False, document_id=document.document_id: (
                self._request_document_remove(document_id)
            )
        )
        layout.addWidget(text_block, 1)
        layout.addWidget(open_button, 0)
        layout.addWidget(remove_button, 0)
        self._make_clickable_card(
            row,
            lambda file_path=document.file_path: self.open_document_file(file_path),
            "Datei öffnen",
        )
        return row

    def _request_document_remove(self, document_id: str) -> None:
        if self.current_student is None:
            return
        self.document_remove_requested.emit(
            self.current_student.student_id,
            document_id,
        )

    def open_document_file(self, file_path: str) -> None:
        """Open a document through the operating system if the path exists."""
        path = Path(file_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()

        if not path.exists():
            self.documents_feedback_label.setText(
                f"Datei wurde nicht gefunden: {path}"
            )
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if opened:
            self.documents_feedback_label.setText("Datei wird geöffnet.")
        else:
            self.documents_feedback_label.setText(
                f"Datei konnte nicht geöffnet werden: {path}"
            )

    def _report_subject_card(self, section: object) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title = QLabel(getattr(section, "subject_display_name"))
        set_label_style(title, "card_title")
        layout.addWidget(title)
        layout.addWidget(self._report_bucket(
            "Aktueller Stand",
            getattr(section, "current_statuses"),
        ))
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

    def report_text(self) -> str:
        """Return the current report preparation as plain text."""
        if self.current_student is None:
            return ""
        return format_student_report_preview_text(
            self.current_student,
            self.current_report_preview,
        )

    def copy_report_text_to_clipboard(self) -> None:
        """Copy the current report preparation into the system clipboard."""
        text = self.report_text()
        if not text:
            self.report_feedback_label.setText("Kein Bericht zum Kopieren vorhanden.")
            return
        QApplication.clipboard().setText(text)
        self.report_feedback_label.setText("Bericht wurde kopiert.")

    def export_report_text(self) -> None:
        """Ask for a text path and export the current report preparation."""
        if self.current_student is None:
            self.report_feedback_label.setText("Kein Bericht zum Exportieren vorhanden.")
            return
        target_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Bericht als Text exportieren",
            self._default_report_export_filename(),
            "Markdown-Datei (*.md);;Textdatei (*.txt)",
        )
        if not target_path:
            return
        self.export_report_text_to_path(Path(target_path))

    def export_report_text_to_path(self, target_path: Path) -> None:
        """Write the current report preparation to a text file."""
        text = self.report_text()
        if not text:
            self.report_feedback_label.setText("Kein Bericht zum Exportieren vorhanden.")
            return
        target_path.write_text(text, encoding="utf-8")
        self.report_feedback_label.setText("Bericht wurde exportiert.")

    def _default_report_export_filename(self) -> str:
        if self.current_student is None:
            return "Berichtsvorbereitung.md"
        safe_name = "_".join(self.current_student.display_name.split())
        safe_id = self.current_student.student_id.replace("/", "-")
        return f"Berichtsvorbereitung_{safe_name}_{safe_id}.md"

    def _clear_observations(self) -> None:
        self._clear_layout(self.observations_layout)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            layout_item = layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.setParent(None)
