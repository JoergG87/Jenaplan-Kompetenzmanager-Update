"""New-observation dialog for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.dialogs.dialog_buttons import configure_save_cancel_buttons
from src.desktop_app.theme import create_card, set_label_style
from src.desktop_app.view_models.observation_view_model import (
    DOCUMENT_TYPE_OPTIONS,
    OBSERVATION_ATTACHMENT_EMPTY_STATE,
    OBSERVATION_CONTEXT_OPTIONS,
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_SAVE_VALIDATION_MESSAGE,
    ObservationAttachmentDraft,
    ObservationCompetencyGroupViewModel,
    ObservationCompetencyOptionViewModel,
    ObservationCompetencyRatingDraft,
    ObservationCompetencySubjectGroupViewModel,
    ObservationDraftViewModel,
    ObservationLearningAreaGroupViewModel,
    ObservationSubjectOptionViewModel,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


OBSERVATION_DIALOG_STYLESHEET = """
QFrame#ObservationDialogZone {
    background-color: #FFFFFF;
    border: 1px solid #C9D8E4;
    border-radius: 14px;
}
QFrame#ObservationSelectedCompetencyCard,
QFrame#ObservationCatalogCompetencyTile {
    background-color: #FFFFFF;
    border: 1px solid #D7E4ED;
    border-radius: 9px;
}
QFrame#ObservationSelectedCompetencyCard[historical="true"] {
    background-color: #FFFAF5;
    border-color: #E9E1D6;
}
QFrame#ObservationCatalogCompetencyTile[selected="false"]:hover {
    background-color: #EEF6FB;
    border-color: #AFCADC;
}
QFrame#ObservationCatalogCompetencyTile[selected="false"]:focus {
    border: 2px solid #2563EB;
}
QFrame#ObservationCatalogCompetencyTile[selected="true"] {
    background-color: #F2F7FA;
    border-color: #D9E5EC;
}
QLabel#ObservationHistoricalBadge {
    color: #8B5A2B;
    background-color: #FDF0E3;
    border: 1px solid #F0D9BE;
    border-radius: 7px;
    padding: 2px 6px;
    font-size: 10px;
}
QPushButton#ObservationHierarchyToggle {
    background-color: transparent;
    border: none;
    color: #0B3A63;
    padding: 7px 5px;
    text-align: left;
    font-weight: 600;
}
QPushButton#ObservationHierarchyToggle:hover {
    background-color: #EEF6FB;
}
QPushButton#ObservationRatingChip {
    background-color: #F7FAFC;
    border: 1px solid #D2E0EA;
    border-radius: 7px;
    color: #38546B;
    min-height: 27px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#ObservationRatingChip:checked {
    background-color: #2563EB;
    border-color: #2563EB;
    color: #FFFFFF;
}
QPushButton#ObservationRemoveCompetencyButton {
    background-color: #F7FAFC;
    border: 1px solid #D7E3EC;
    color: #556372;
    min-width: 30px;
    max-width: 30px;
    min-height: 28px;
    padding: 2px;
}
"""


class ObservationRatingSelector(QWidget):
    """Exclusive four-chip selector with the former combo-box data contract."""

    def __init__(self, initial_rating: str = "") -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for rating_option in OBSERVATION_RATING_OPTIONS:
            rating = rating_option.split(" ", 1)[0]
            button = QPushButton(rating_option)
            button.setObjectName("ObservationRatingChip")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("rating", rating)
            self.button_group.addButton(button)
            self.buttons[rating] = button
            layout.addWidget(button)
        self.set_current_data(initial_rating)

    def currentData(self) -> str:  # noqa: N802 - matches QComboBox contract
        checked_button = self.button_group.checkedButton()
        return str(checked_button.property("rating") or "") if checked_button else ""

    def set_current_data(self, rating: str) -> None:
        button = self.buttons.get(rating)
        if button is not None:
            button.setChecked(True)


class ObservationCatalogCompetencyTile(QFrame):
    """Keyboard- and pointer-activatable catalog tile."""

    def __init__(
        self,
        competency_id: str,
        activate: Callable[[], None],
        selected: bool,
    ) -> None:
        super().__init__()
        self.competency_id = competency_id
        self._activate = activate
        self.setObjectName("ObservationCatalogCompetencyTile")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Kompetenz zur Auswahl hinzufügen")
        self.set_selected(selected)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.setCursor(
            Qt.CursorShape.ArrowCursor
            if selected
            else Qt.CursorShape.PointingHandCursor
        )
        self.setAccessibleName(
            "Bereits ausgewählte Kompetenz"
            if selected
            else "Kompetenz zur Auswahl hinzufügen"
        )
        self.style().unpolish(self)
        self.style().polish(self)

    def is_selected(self) -> bool:
        return self.property("selected") == "true"

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.is_selected():
            self._activate()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if not self.is_selected():
                self._activate()
            event.accept()
            return
        super().keyPressEvent(event)


class NewObservationDialog(QDialog):
    """Collect and persist an observation draft through the desktop adapter."""

    def __init__(
        self,
        student: StudentDetailViewModel,
        curriculum_adapter: object | None = None,
        observation_adapter: object | None = None,
        initial_draft: ObservationDraftViewModel | None = None,
        subject_options: tuple[ObservationSubjectOptionViewModel, ...] = (),
        competency_subject_groups: tuple[
            ObservationCompetencySubjectGroupViewModel, ...
        ] = (),
    ) -> None:
        super().__init__()
        self.student = student
        self.curriculum_adapter = curriculum_adapter
        self.observation_adapter = observation_adapter
        self.initial_draft = initial_draft
        self.subject_options = subject_options
        self.competency_subject_groups = competency_subject_groups
        self.attachment_feedback_label = QLabel("")
        self.competency_rating_entries: dict[str, object] = {}
        self.competency_rating_widgets: dict[str, ObservationRatingSelector] = {}
        self.competency_rating_rows: dict[str, QWidget] = {}
        self.competency_catalog_tiles: dict[str, ObservationCatalogCompetencyTile] = {}
        self.competency_area_buttons: dict[str, QPushButton] = {}
        self.competency_area_containers: dict[str, QWidget] = {}
        self.competency_topic_buttons: dict[str, QPushButton] = {}
        self.competency_topic_containers: dict[str, QWidget] = {}
        self._catalog_expansion_snapshot: tuple[dict[str, bool], dict[str, bool]] | None = None
        self._catalog_search_text = ""
        self.attachment_drafts: list[ObservationAttachmentDraft] = []
        self._initial_selected_competency_ids = {
            rating.competency_id
            for rating in (initial_draft.competency_ratings if initial_draft else ())
            if rating.competency_id
        }
        self._historical_competency_ids = {
            competency.competency_id
            for subject_group in competency_subject_groups
            for area_group in subject_group.learning_area_groups
            for topic_group in area_group.competency_groups
            for competency in topic_group.competencies
            if competency.catalog_status != "current" or not competency.is_active
        }
        self.setWindowTitle(
            "Beobachtung bearbeiten" if self.initial_draft else "Neue Beobachtung"
        )
        self.setModal(True)
        self.setMinimumSize(1080, 680)
        self.resize(1320, 820)
        self.setStyleSheet(self.styleSheet() + OBSERVATION_DIALOG_STYLESHEET)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        title = QLabel(
            "Beobachtung bearbeiten"
            if self.initial_draft
            else f"Neue Beobachtung für {self.student.display_name}"
        )
        set_label_style(title, "dialog_title")
        layout.addWidget(title)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        self.date_input.setDate(QDate.currentDate())
        self.subject_select = QComboBox()
        self._populate_subjects()
        self.context_select = QComboBox()
        self.context_select.addItems(OBSERVATION_CONTEXT_OPTIONS)
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Was war konkret zu beobachten?")
        self.note_input.setMinimumHeight(150)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("ObservationThreeZoneWorkspace")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(self._build_context_zone())
        splitter.addWidget(self._build_competency_zone())
        splitter.addWidget(self._build_observation_zone())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([250, 704, 310])
        layout.addWidget(splitter, 1)

        self.subject_select.currentIndexChanged.connect(self._refresh_competencies)
        self._refresh_competencies()
        self._apply_initial_draft()

    def _build_context_zone(self) -> QFrame:
        zone = self._zone("Kind und Kontext")
        zone.setMinimumWidth(225)
        zone.setMaximumWidth(290)
        zone_layout = zone.layout()

        student_card = self._card()
        student_layout = QVBoxLayout(student_card)
        student_layout.setContentsMargins(12, 12, 12, 12)
        student_layout.setSpacing(4)
        student_name = QLabel(self.student.display_name)
        set_label_style(student_name, "card_title")
        student_context = QLabel(
            f"{self.student.group_name}\n{self.student.course_name}"
        )
        student_context.setWordWrap(True)
        set_label_style(student_context, "muted")
        student_layout.addWidget(student_name)
        student_layout.addWidget(student_context)
        zone_layout.addWidget(student_card)
        zone_layout.addWidget(self._field_label("Fach · Katalogfilter"))
        zone_layout.addWidget(self.subject_select)
        zone_layout.addWidget(self._field_label("Beobachtungskontext"))
        zone_layout.addWidget(self.context_select)
        hint = QLabel(
            "Der Fachwechsel filtert nur den Katalog. Bereits ausgewählte "
            "Kompetenzen und Bewertungen bleiben erhalten."
        )
        hint.setWordWrap(True)
        set_label_style(hint, "muted")
        zone_layout.addWidget(hint)
        zone_layout.addStretch(1)
        return zone

    def _build_competency_zone(self) -> QFrame:
        zone = self._zone()
        zone.setMinimumWidth(480)
        zone_layout = zone.layout()

        selected_header = QHBoxLayout()
        selected_title = QLabel("Ausgewählte Kompetenzen")
        set_label_style(selected_title, "section_title")
        selected_header.addWidget(selected_title)
        selected_header.addStretch(1)
        self.selection_count_label = QLabel("0 ausgewählt")
        set_label_style(self.selection_count_label, "muted")
        selected_header.addWidget(self.selection_count_label)
        zone_layout.addLayout(selected_header)

        self.selected_scroll = QScrollArea()
        self.selected_scroll.setObjectName("ObservationSelectedScroll")
        self.selected_scroll.setWidgetResizable(True)
        self.selected_scroll.setMinimumHeight(210)
        self.selected_scroll.setMaximumHeight(310)
        selected_content = QWidget()
        self.competency_ratings_layout = QVBoxLayout(selected_content)
        self.competency_ratings_layout.setContentsMargins(0, 0, 4, 0)
        self.competency_ratings_layout.setSpacing(7)
        self.competency_ratings_empty_state = QLabel(
            "Noch keine Kompetenz ausgewählt."
        )
        set_label_style(self.competency_ratings_empty_state, "subtle")
        self.competency_ratings_layout.addWidget(self.competency_ratings_empty_state)
        self.competency_ratings_layout.addStretch(1)
        self.selected_scroll.setWidget(selected_content)
        zone_layout.addWidget(self.selected_scroll, 0)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        zone_layout.addWidget(divider)
        catalog_title = QLabel("Kompetenzkatalog")
        set_label_style(catalog_title, "section_title")
        zone_layout.addWidget(catalog_title)
        self.catalog_search_input = QLineEdit()
        self.catalog_search_input.setObjectName("ObservationCatalogSearch")
        self.catalog_search_input.setPlaceholderText("Kompetenzen durchsuchen …")
        self.catalog_search_input.setClearButtonEnabled(True)
        self.catalog_search_input.textChanged.connect(self._search_catalog)
        zone_layout.addWidget(self.catalog_search_input)
        self.catalog_search_result_label = QLabel("")
        self.catalog_search_result_label.setObjectName("ObservationCatalogSearchResult")
        set_label_style(self.catalog_search_result_label, "muted")
        zone_layout.addWidget(self.catalog_search_result_label)
        self.catalog_hint = QLabel("Fach → Kompetenzbereich → Thema → Kompetenz")
        set_label_style(self.catalog_hint, "muted")
        zone_layout.addWidget(self.catalog_hint)

        self.catalog_scroll = QScrollArea()
        self.catalog_scroll.setObjectName("ObservationCatalogScroll")
        self.catalog_scroll.setWidgetResizable(True)
        self.catalog_content = QWidget()
        self.competency_tree_layout = QVBoxLayout(self.catalog_content)
        self.competency_tree_layout.setContentsMargins(0, 0, 4, 0)
        self.competency_tree_layout.setSpacing(6)
        self.catalog_scroll.setWidget(self.catalog_content)
        zone_layout.addWidget(self.catalog_scroll, 1)
        return zone

    def _build_observation_zone(self) -> QFrame:
        zone = self._zone("Beobachtung")
        zone.setMinimumWidth(285)
        zone.setMaximumWidth(350)
        zone_layout = zone.layout()
        zone_layout.addWidget(self._field_label("Datum"))
        zone_layout.addWidget(self.date_input)
        zone_layout.addWidget(self._field_label("Notiz"))
        zone_layout.addWidget(self.note_input, 1)
        zone_layout.addWidget(self._attachments_card())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.setObjectName("ObservationPersistentActions")
        configure_save_cancel_buttons(buttons)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setText("Beobachtung speichern")
            save_button.setMinimumHeight(42)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save_draft)
        zone_layout.addWidget(buttons, 0)
        return zone

    def _zone(self, title: str = "") -> QFrame:
        zone = QFrame()
        zone.setObjectName("ObservationDialogZone")
        zone_layout = QVBoxLayout(zone)
        zone_layout.setContentsMargins(14, 14, 14, 14)
        zone_layout.setSpacing(10)
        if title:
            title_label = QLabel(title)
            set_label_style(title_label, "section_title")
            zone_layout.addWidget(title_label)
        return zone

    def _populate_subjects(self) -> None:
        subject_options = self.subject_options or tuple(
            ObservationSubjectOptionViewModel(
                group.subject_key,
                group.subject_display_name,
            )
            for group in self.competency_subject_groups
        )
        for subject in subject_options:
            self.subject_select.addItem(subject.display_name, subject.subject_key)

    def _refresh_competencies(self, _index: int | None = None) -> None:
        if not hasattr(self, "competency_tree_layout"):
            return
        self._clear_layout(self.competency_tree_layout)
        self.competency_catalog_tiles.clear()
        self.competency_area_buttons.clear()
        self.competency_area_containers.clear()
        self.competency_topic_buttons.clear()
        self.competency_topic_containers.clear()
        subject_group = self._current_subject_group()
        if subject_group is None or not subject_group.learning_area_groups:
            self._set_catalog_search_feedback(0)
            empty_label = QLabel("Keine aktuellen Kompetenzen für dieses Fach hinterlegt.")
            set_label_style(empty_label, "subtle")
            self.competency_tree_layout.addWidget(empty_label)
            self.competency_tree_layout.addStretch(1)
            return
        self.catalog_hint.setText(
            f"{subject_group.subject_display_name} · Kompetenzbereich → Thema → Kompetenz"
        )
        matching_competency_count = 0
        for learning_area_group in subject_group.learning_area_groups:
            matching_topics = tuple(
                (competency_group, self._matching_catalog_competencies(competency_group))
                for competency_group in learning_area_group.competency_groups
            )
            matching_topics = tuple(
                (competency_group, competencies)
                for competency_group, competencies in matching_topics
                if competencies
            )
            if not matching_topics:
                continue
            matching_competency_count += sum(
                len(competencies) for _group, competencies in matching_topics
            )
            self.competency_tree_layout.addWidget(
                self._learning_area_widget(learning_area_group, matching_topics)
            )
        self._set_catalog_search_feedback(matching_competency_count)
        if self._catalog_search_text and not matching_competency_count:
            empty_label = QLabel("Keine passenden Kompetenzen gefunden.")
            empty_label.setObjectName("ObservationCatalogSearchEmptyState")
            set_label_style(empty_label, "subtle")
            self.competency_tree_layout.addWidget(empty_label)
        self.competency_tree_layout.addStretch(1)
        self.catalog_scroll.verticalScrollBar().setValue(0)

    def _search_catalog(self, search_text: str) -> None:
        normalized_search_text = search_text.strip().casefold()
        if normalized_search_text and not self._catalog_search_text:
            self._catalog_expansion_snapshot = self._catalog_expansion_state()
        self._catalog_search_text = normalized_search_text
        self._refresh_competencies()
        if not normalized_search_text:
            self._catalog_expansion_snapshot = None

    def _matching_catalog_competencies(
        self,
        competency_group: ObservationCompetencyGroupViewModel,
    ) -> tuple[ObservationCompetencyOptionViewModel, ...]:
        query = self._catalog_search_text
        return tuple(
            competency
            for competency in competency_group.competencies
            if (
                not query
                or (
                    competency.catalog_status == "current"
                    and competency.is_active
                )
            )
            and (
                not query
                or query in " ".join((
                    competency.competency_label,
                    competency.competency_text,
                    competency.competency_group,
                    competency.learning_area,
                )).casefold()
            )
        )

    def _set_catalog_search_feedback(self, competency_count: int) -> None:
        if not self._catalog_search_text:
            self.catalog_search_result_label.setText("")
            return
        self.catalog_search_result_label.setText(
            f"{competency_count} Kompetenz{'en' if competency_count != 1 else ''} gefunden"
        )

    def _catalog_expansion_state(self) -> tuple[dict[str, bool], dict[str, bool]]:
        return (
            {
                area_key: not container.isHidden()
                for area_key, container in self.competency_area_containers.items()
            },
            {
                topic_key: not container.isHidden()
                for topic_key, container in self.competency_topic_containers.items()
            },
        )

    def _current_subject_group(
        self,
    ) -> ObservationCompetencySubjectGroupViewModel | None:
        subject_key = str(self.subject_select.currentData() or "")
        return next(
            (
                subject_group
                for subject_group in self.competency_subject_groups
                if subject_group.subject_key == subject_key
            ),
            None,
        )

    def _learning_area_widget(
        self,
        learning_area_group: ObservationLearningAreaGroupViewModel,
        matching_topics: tuple[
            tuple[
                ObservationCompetencyGroupViewModel,
                tuple[ObservationCompetencyOptionViewModel, ...],
            ],
            ...,
        ],
    ) -> QWidget:
        area_widget = QWidget()
        area_layout = QVBoxLayout(area_widget)
        area_layout.setContentsMargins(0, 0, 0, 3)
        area_layout.setSpacing(4)
        area_key = self._area_key(learning_area_group)
        area_is_open = True if self._catalog_search_text else self._restored_area_state(
            area_key,
            self._learning_area_has_initial_selection(learning_area_group),
        )
        area_button = self._hierarchy_button(area_key, self._toggle_competency_area)
        self.competency_area_buttons[area_key] = area_button
        area_layout.addWidget(area_button)

        topics_container = QWidget()
        topics_layout = QVBoxLayout(topics_container)
        topics_layout.setContentsMargins(12, 0, 0, 0)
        topics_layout.setSpacing(4)
        for competency_group, competencies in matching_topics:
            topics_layout.addWidget(
                self._competency_group_widget(competency_group, competencies)
            )
        topics_container.setVisible(area_is_open)
        self.competency_area_containers[area_key] = topics_container
        area_layout.addWidget(topics_container)
        self._set_area_button_text(area_key, area_is_open)
        return area_widget

    def _competency_group_widget(
        self,
        competency_group: ObservationCompetencyGroupViewModel,
        competencies: tuple[ObservationCompetencyOptionViewModel, ...],
    ) -> QWidget:
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(12, 0, 0, 3)
        group_layout.setSpacing(3)
        topic_key = self._topic_key(competency_group)
        topic_is_open = True if self._catalog_search_text else self._restored_topic_state(
            topic_key,
            self._competency_group_has_initial_selection(competency_group),
        )
        topic_button = self._hierarchy_button(topic_key, self._toggle_competency_topic)
        self.competency_topic_buttons[topic_key] = topic_button
        group_layout.addWidget(topic_button)

        competencies_container = QWidget()
        competencies_layout = QVBoxLayout(competencies_container)
        competencies_layout.setContentsMargins(12, 0, 0, 0)
        competencies_layout.setSpacing(5)
        for competency in competencies:
            competencies_layout.addWidget(self._competency_catalog_tile(competency))
        competencies_container.setVisible(topic_is_open)
        self.competency_topic_containers[topic_key] = competencies_container
        group_layout.addWidget(competencies_container)
        self._set_topic_button_text(topic_key, topic_is_open)
        return group_widget

    def _hierarchy_button(
        self,
        key: str,
        toggle: Callable[[str], None],
    ) -> QPushButton:
        button = QPushButton()
        button.setObjectName("ObservationHierarchyToggle")
        button.setFlat(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda _checked=False: toggle(key))
        return button

    def _competency_catalog_tile(
        self,
        competency: ObservationCompetencyOptionViewModel,
    ) -> ObservationCatalogCompetencyTile:
        competency_key = self._competency_key(competency)
        is_selected = competency_key in self.competency_rating_entries or competency.selected
        tile = ObservationCatalogCompetencyTile(
            competency_key,
            lambda entry=competency: self._select_competency(entry),
            is_selected,
        )
        tile.setProperty("subject_key", competency.subject_key)
        tile.setToolTip(self._competency_detail_text(competency))
        tile_layout = QHBoxLayout(tile)
        tile_layout.setContentsMargins(9, 7, 7, 7)
        tile_layout.setSpacing(8)
        text = QLabel(self._competency_display_text(competency))
        text.setWordWrap(True)
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        tile_layout.addWidget(text, 1)
        signal = QLabel("✓" if is_selected else "+")
        signal.setObjectName("ObservationCatalogSelectionSignal")
        signal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signal.setMinimumWidth(24)
        signal.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        tile_layout.addWidget(signal, 0, Qt.AlignmentFlag.AlignTop)
        tile.selection_signal = signal
        self.competency_catalog_tiles[competency_key] = tile
        return tile

    def _select_competency(self, competency: ObservationCompetencyOptionViewModel) -> None:
        competency_key = self._competency_key(competency)
        if competency_key in self.competency_rating_entries:
            return
        self._add_competency_rating_row(
            competency_key,
            competency,
            initial_rating="+",
            prepend=True,
        )
        self._set_catalog_tile_selected(competency_key, True)
        QTimer.singleShot(0, self._scroll_selected_to_top)

    def _set_catalog_tile_selected(self, competency_key: str, selected: bool) -> None:
        tile = self.competency_catalog_tiles.get(competency_key)
        if tile is None:
            return
        tile.set_selected(selected)
        tile.selection_signal.setText("✓" if selected else "+")

    def _scroll_selected_to_top(self) -> None:
        self.selected_scroll.verticalScrollBar().setValue(
            self.selected_scroll.verticalScrollBar().minimum()
        )

    def _area_key(self, group: ObservationLearningAreaGroupViewModel) -> str:
        first_competency = next(
            (
                competency
                for topic in group.competency_groups
                for competency in topic.competencies
            ),
            None,
        )
        subject_key = getattr(first_competency, "subject_key", "")
        return f"{subject_key}|{self._learning_area_text(group)}"

    def _topic_key(self, group: ObservationCompetencyGroupViewModel) -> str:
        first_competency = group.competencies[0] if group.competencies else None
        return "|".join((
            str(getattr(first_competency, "subject_key", "")),
            str(getattr(first_competency, "learning_area", "")),
            self._competency_group_text(group),
        ))

    def _learning_area_has_initial_selection(
        self,
        group: ObservationLearningAreaGroupViewModel,
    ) -> bool:
        return any(
            self._competency_group_has_initial_selection(topic)
            for topic in group.competency_groups
        )

    def _competency_group_has_initial_selection(
        self,
        group: ObservationCompetencyGroupViewModel,
    ) -> bool:
        return self.initial_draft is not None and any(
            competency.competency_id in self._initial_selected_competency_ids
            for competency in group.competencies
        )

    def _toggle_competency_area(self, area_key: str) -> None:
        if self._catalog_search_text:
            return
        container = self.competency_area_containers.get(area_key)
        if container is None:
            return
        is_open = container.isHidden()
        container.setVisible(is_open)
        self._set_area_button_text(area_key, is_open)

    def _toggle_competency_topic(self, topic_key: str) -> None:
        if self._catalog_search_text:
            return
        container = self.competency_topic_containers.get(topic_key)
        if container is None:
            return
        is_open = container.isHidden()
        container.setVisible(is_open)
        self._set_topic_button_text(topic_key, is_open)

    def _restored_area_state(self, area_key: str, default: bool) -> bool:
        if self._catalog_expansion_snapshot is None:
            return default
        return self._catalog_expansion_snapshot[0].get(area_key, default)

    def _restored_topic_state(self, topic_key: str, default: bool) -> bool:
        if self._catalog_expansion_snapshot is None:
            return default
        return self._catalog_expansion_snapshot[1].get(topic_key, default)

    def _set_area_button_text(self, area_key: str, is_open: bool) -> None:
        button = self.competency_area_buttons.get(area_key)
        if button is not None:
            button.setText(
                f"{'▾' if is_open else '▸'} Kompetenzbereich: "
                f"{area_key.rsplit('|', 1)[-1] or 'Ohne Kompetenzbereich'}"
            )

    def _set_topic_button_text(self, topic_key: str, is_open: bool) -> None:
        button = self.competency_topic_buttons.get(topic_key)
        if button is not None:
            button.setText(
                f"{'▾' if is_open else '▸'} Thema: "
                f"{topic_key.rsplit('|', 1)[-1] or 'Ohne Thema'}"
            )

    def _attachments_card(self) -> QFrame:
        card = self._card()
        card.setMaximumHeight(250)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title = QLabel("Dokumente & Medien")
        set_label_style(title, "card_title")
        self.attachment_type_select = QComboBox()
        self.attachment_type_select.addItems(DOCUMENT_TYPE_OPTIONS)
        default_type_index = self.attachment_type_select.findText("Sonstiges")
        if default_type_index >= 0:
            self.attachment_type_select.setCurrentIndex(default_type_index)
        add_file_button = QPushButton("Datei hinzufügen")
        add_file_button.clicked.connect(self.add_attachment_from_dialog)
        self.attachments_container = QWidget()
        self.attachments_layout = QVBoxLayout(self.attachments_container)
        self.attachments_layout.setContentsMargins(0, 0, 0, 0)
        self.attachments_layout.setSpacing(4)
        attachments_scroll = QScrollArea()
        attachments_scroll.setObjectName("ObservationAttachmentsScroll")
        attachments_scroll.setWidgetResizable(True)
        attachments_scroll.setFrameShape(QFrame.Shape.NoFrame)
        attachments_scroll.setMaximumHeight(105)
        attachments_scroll.setWidget(self.attachments_container)
        self.attachment_empty_state = QLabel(OBSERVATION_ATTACHMENT_EMPTY_STATE)
        set_label_style(self.attachment_empty_state, "subtle")
        set_label_style(self.attachment_feedback_label, "muted")
        layout.addWidget(title)
        layout.addWidget(self.attachment_type_select)
        layout.addWidget(add_file_button)
        layout.addWidget(attachments_scroll)
        layout.addWidget(self.attachment_feedback_label)
        self._render_attachments()
        return card

    def _field_label(self, label: str) -> QLabel:
        field_label = QLabel(label)
        set_label_style(field_label, "field_label")
        return field_label

    def _card(self) -> QFrame:
        return create_card()

    def add_attachment_from_dialog(self) -> None:
        """Ask for files and add them to the observation draft."""
        file_paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Dateien hinzufügen",
            "",
            "Alle Dateien (*)",
        )
        for file_path in file_paths:
            self.add_attachment_path(Path(file_path))

    def add_attachment_path(self, file_path: Path) -> None:
        """Add one local file to the UI draft."""
        source_path = Path(file_path)
        if not source_path.is_file():
            self.attachment_feedback_label.setText("Datei wurde nicht gefunden.")
            return
        self.attachment_drafts.append(
            ObservationAttachmentDraft(
                source_path=str(source_path),
                title=source_path.stem,
                document_type=self.attachment_type_select.currentText() or "Sonstiges",
                original_filename=source_path.name,
            )
        )
        self.attachment_feedback_label.setText("")
        self._render_attachments()

    def create_draft(self) -> ObservationDraftViewModel:
        """Return the UI draft."""
        return ObservationDraftViewModel(
            student_id=self.student.student_id,
            student_name=self.student.display_name,
            date_text=self.date_input.date().toString("yyyy-MM-dd"),
            competency_ratings=self._selected_competency_ratings(),
            context=self.context_select.currentText(),
            note=self.note_input.toPlainText(),
            subject_id=str(self.subject_select.currentData() or ""),
            subject_display_name=self.subject_select.currentText(),
            attachment_names=tuple(
                attachment.original_filename or Path(attachment.source_path).name
                for attachment in self.attachment_drafts
            ),
            attachments=tuple(self.attachment_drafts),
            observation_id=self.initial_draft.observation_id if self.initial_draft else "",
        )

    def _render_attachments(self) -> None:
        self._clear_attachments()
        if not self.attachment_drafts:
            self.attachments_layout.addWidget(self.attachment_empty_state)
            return
        for index, attachment in enumerate(self.attachment_drafts):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            label = QLabel(attachment.display_label)
            label.setWordWrap(True)
            set_label_style(label, "small")
            remove_button = QPushButton("Entfernen")
            remove_button.clicked.connect(
                lambda _checked=False, row_index=index: self._remove_attachment(row_index)
            )
            row.addWidget(label, 1)
            row.addWidget(remove_button, 0)
            self.attachments_layout.addWidget(row_widget)

    def _clear_attachments(self) -> None:
        while self.attachments_layout.count():
            item = self.attachments_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _remove_attachment(self, index: int) -> None:
        if 0 <= index < len(self.attachment_drafts):
            self.attachment_drafts.pop(index)
            self._render_attachments()

    def _selected_competency_ratings(
        self,
    ) -> tuple[ObservationCompetencyRatingDraft, ...]:
        return tuple(
            ObservationCompetencyRatingDraft.from_catalog_entry(
                catalog_entry,
                self.competency_rating_widgets[competency_key].currentData(),
            )
            for competency_key, catalog_entry in self.competency_rating_entries.items()
        )

    def _add_competency_rating_row(
        self,
        competency_key: str,
        catalog_entry: object,
        initial_rating: str = "",
        *,
        prepend: bool = False,
    ) -> None:
        if competency_key in self.competency_rating_entries:
            return
        card = QFrame()
        card.setObjectName("ObservationSelectedCompetencyCard")
        card.setProperty(
            "historical",
            "true" if competency_key in self._historical_competency_ids else "false",
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(9, 6, 8, 6)
        card_layout.setSpacing(4)
        meta_row = QHBoxLayout()
        meta = QLabel(
            f"{getattr(catalog_entry, 'subject_display_name', '')} · "
            f"{self._learning_area_text(catalog_entry)} · "
            f"{self._competency_group_text(catalog_entry)}"
        )
        meta.setWordWrap(True)
        set_label_style(meta, "small")
        meta_row.addWidget(meta, 1)
        if competency_key in self._historical_competency_ids:
            historical = QLabel("Historischer Bestand")
            historical.setObjectName("ObservationHistoricalBadge")
            historical.setToolTip(
                "Diese Kompetenz gehört zu einer bestehenden Beobachtung und "
                "wird im aktuellen Katalog nicht mehr neu angeboten."
            )
            meta_row.addWidget(historical)
        card_layout.addLayout(meta_row)
        text = QLabel(self._competency_display_text(catalog_entry))
        text.setWordWrap(True)
        text.setToolTip(self._competency_detail_text(catalog_entry))
        text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        card_layout.addWidget(text)
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        rating_selector = ObservationRatingSelector(initial_rating)
        rating_selector.setAccessibleName(
            f"Bewertung für {self._competency_display_text(catalog_entry)}"
        )
        remove_button = QPushButton("×")
        remove_button.setObjectName("ObservationRemoveCompetencyButton")
        remove_button.setToolTip("Aus Auswahl entfernen")
        remove_button.clicked.connect(
            lambda _checked=False, key=competency_key: self._remove_competency_rating(key)
        )
        action_row.addWidget(rating_selector, 1)
        action_row.addWidget(remove_button, 0)
        card_layout.addLayout(action_row)

        self.competency_rating_entries[competency_key] = catalog_entry
        self.competency_rating_widgets[competency_key] = rating_selector
        self.competency_rating_rows[competency_key] = card
        card.setProperty("competency_key", competency_key)
        insert_index = 0 if prepend else max(0, self.competency_ratings_layout.count() - 1)
        self.competency_ratings_layout.insertWidget(insert_index, card)
        self._update_selection_summary()

    def _remove_competency_rating(self, competency_key: str) -> None:
        self.competency_rating_entries.pop(competency_key, None)
        self.competency_rating_widgets.pop(competency_key, None)
        row = self.competency_rating_rows.pop(competency_key, None)
        if row is not None:
            self.competency_ratings_layout.removeWidget(row)
            row.deleteLater()
        self._set_catalog_tile_selected(competency_key, False)
        self._update_selection_summary()

    def _update_selection_summary(self) -> None:
        count = len(self.competency_rating_entries)
        self.selection_count_label.setText(f"{count} ausgewählt")
        self.competency_ratings_empty_state.setVisible(count == 0)

    def _competency_key(self, catalog_entry: object) -> str:
        competency_id = str(getattr(catalog_entry, "competency_id", "")).strip()
        if competency_id:
            return competency_id
        return "|".join((
            str(getattr(catalog_entry, "subject_key", "")),
            str(getattr(catalog_entry, "learning_area", "")),
            str(getattr(catalog_entry, "competency_group", "")),
            str(getattr(catalog_entry, "competency_text", "")),
        ))

    def _learning_area_text(self, entry: object) -> str:
        return str(getattr(entry, "learning_area", "") or "").strip() or (
            "Ohne Kompetenzbereich"
        )

    def _competency_group_text(self, entry: object) -> str:
        return str(getattr(entry, "competency_group", "") or "").strip() or "Ohne Thema"

    def _competency_display_text(self, entry: object) -> str:
        return (
            str(getattr(entry, "competency_text", "") or "").strip()
            or str(getattr(entry, "competency_label", "") or "").strip()
            or self._learning_area_text(entry)
        )

    def _competency_detail_text(self, entry: object) -> str:
        return "\n".join((
            f"Kompetenzbereich: {self._learning_area_text(entry)}",
            f"Thema: {self._competency_group_text(entry)}",
            f"Kompetenz: {self._competency_display_text(entry)}",
        ))

    def _apply_initial_draft(self) -> None:
        if self.initial_draft is None:
            return
        date = QDate.fromString(self.initial_draft.date_text, "yyyy-MM-dd")
        if date.isValid():
            self.date_input.setDate(date)
        self.note_input.setPlainText(self.initial_draft.note)
        context_index = self.context_select.findText(self.initial_draft.context)
        if context_index >= 0:
            self.context_select.setCurrentIndex(context_index)
        visible_subject = self._initial_visible_subject()
        subject_index = self.subject_select.findData(visible_subject)
        if subject_index >= 0:
            self.subject_select.setCurrentIndex(subject_index)
        for rating in self.initial_draft.competency_ratings:
            self._add_competency_rating_row(
                self._competency_key(rating),
                rating,
                rating.rating,
            )
            self._set_catalog_tile_selected(self._competency_key(rating), True)
        self.attachment_drafts = list(self.initial_draft.attachments)
        self._render_attachments()

    def _initial_visible_subject(self) -> str:
        if self.initial_draft is None:
            return ""
        if self.initial_draft.competency_ratings:
            return self.initial_draft.competency_ratings[0].subject_key
        return self.initial_draft.subject_id

    def save_draft(self) -> None:
        """Persist the observation draft through the adapter and return on success."""
        draft = self.create_draft()
        if not draft.competency_ratings or any(
            not rating.rating for rating in draft.competency_ratings
        ):
            QMessageBox.warning(self, "Hinweis", OBSERVATION_SAVE_VALIDATION_MESSAGE)
            return
        if self.observation_adapter is None:
            QMessageBox.warning(
                self,
                "Hinweis",
                "Beobachtungen können ohne Adapter nicht gespeichert werden.",
            )
            return
        if draft.observation_id:
            result = self.observation_adapter.update_observation(draft)
        else:
            result = self.observation_adapter.save_observation(draft)
        if not getattr(result, "success", False):
            QMessageBox.warning(
                self,
                "Speichern fehlgeschlagen",
                str(
                    getattr(
                        result,
                        "message",
                        "Beobachtung konnte nicht gespeichert werden.",
                    )
                ),
            )
            return
        self.accept()

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                NewObservationDialog._clear_layout(child_layout)
