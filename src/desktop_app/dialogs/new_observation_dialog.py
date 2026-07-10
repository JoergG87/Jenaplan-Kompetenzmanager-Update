"""New-observation dialog for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QDateEdit,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
)
from src.desktop_app.dialogs.dialog_buttons import configure_save_cancel_buttons
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_ATTACHMENT_EMPTY_STATE,
    OBSERVATION_CONTEXT_OPTIONS,
    DOCUMENT_TYPE_OPTIONS,
    ObservationAttachmentDraft,
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_SAVE_VALIDATION_MESSAGE,
    ObservationCompetencyGroupViewModel,
    ObservationCompetencyOptionViewModel,
    ObservationCompetencyRatingDraft,
    ObservationCompetencySubjectGroupViewModel,
    ObservationDraftViewModel,
    ObservationLearningAreaGroupViewModel,
    ObservationSubjectOptionViewModel,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel
from src.desktop_app.theme import create_card, set_label_style


class NewObservationDialog(QDialog):
    """Collect and persist an observation draft through the desktop adapter."""

    def __init__(
        self,
        student: StudentDetailViewModel,
        curriculum_adapter: CurriculumDesktopAdapter | None = None,
        observation_adapter: object | None = None,
        initial_draft: ObservationDraftViewModel | None = None,
        subject_options: tuple[ObservationSubjectOptionViewModel, ...] = (),
        competency_subject_groups: tuple[
            ObservationCompetencySubjectGroupViewModel, ...
        ] = (),
    ) -> None:
        super().__init__()
        self.student = student
        self.curriculum_adapter = curriculum_adapter or CurriculumDesktopAdapter()
        self.observation_adapter = observation_adapter
        self.initial_draft = initial_draft
        self.subject_options = subject_options
        self.competency_subject_groups = competency_subject_groups
        self.attachment_feedback_label = QLabel("")
        self.competency_rating_entries: dict[str, object] = {}
        self.competency_rating_widgets: dict[str, QComboBox] = {}
        self.competency_rating_rows: dict[str, QWidget] = {}
        self.competency_checkboxes: dict[str, QCheckBox] = {}
        self.competency_area_buttons: dict[str, QPushButton] = {}
        self.competency_area_containers: dict[str, QWidget] = {}
        self.competency_topic_buttons: dict[str, QPushButton] = {}
        self.competency_topic_containers: dict[str, QWidget] = {}
        self.attachment_drafts: list[ObservationAttachmentDraft] = []
        self.setWindowTitle(
            "Beobachtung bearbeiten" if self.initial_draft else "Neue Beobachtung"
        )
        self.setModal(True)
        self.setMinimumSize(700, 560)
        self.resize(760, 640)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)

        title_text = (
            "Beobachtung bearbeiten"
            if self.initial_draft
            else f"Neue Beobachtung für {self.student.display_name}"
        )
        title = QLabel(title_text)
        set_label_style(title, "dialog_title")
        student_context = QLabel(
            f"{self.student.group_name} · {self.student.course_name}"
        )
        set_label_style(student_context, "muted")
        layout.addWidget(title)
        layout.addWidget(student_context)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        form_card = self._card()
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(12, 10, 12, 10)
        form_layout.setSpacing(8)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())

        self.subject_select = QComboBox()
        self._populate_subjects()
        self.subject_select.currentIndexChanged.connect(self._refresh_competencies)

        self.competency_tree_container = QWidget()
        self.competency_tree_layout = QVBoxLayout(self.competency_tree_container)
        self.competency_tree_layout.setContentsMargins(0, 2, 0, 0)
        self.competency_tree_layout.setSpacing(6)
        self._refresh_competencies()

        self.context_select = QComboBox()
        self.context_select.addItems(OBSERVATION_CONTEXT_OPTIONS)

        self.note_input = QTextEdit()
        self.note_input.setMinimumHeight(86)

        form_layout.addLayout(self._field_row("Datum", self.date_input))
        form_layout.addLayout(
            self._field_row("Fach für Kompetenzauswahl", self.subject_select)
        )
        form_layout.addWidget(self._competency_card())
        form_layout.addWidget(self._competency_ratings_card())
        form_layout.addLayout(self._field_row("Kontext", self.context_select))
        form_layout.addWidget(self._field_label("Notiz"))
        form_layout.addWidget(self.note_input)
        scroll_layout.addWidget(form_card)

        scroll_layout.addWidget(self._attachments_card())
        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save_draft)
        layout.addWidget(buttons)
        self._apply_initial_draft()

    def _populate_subjects(self) -> None:
        subject_options = self.subject_options or tuple(
            ObservationSubjectOptionViewModel(
                subject.subject_key,
                subject.display_name,
            )
            for subject in self.curriculum_adapter.list_active_subjects()
        )
        for subject in subject_options:
            self.subject_select.addItem(subject.display_name, subject.subject_key)

    def _refresh_competencies(self) -> None:
        if not hasattr(self, "competency_tree_layout"):
            return
        self._clear_competency_tree()
        self.competency_checkboxes.clear()
        self.competency_area_buttons.clear()
        self.competency_area_containers.clear()
        self.competency_topic_buttons.clear()
        self.competency_topic_containers.clear()
        subject_group = self._current_subject_group()
        if subject_group is None or not subject_group.learning_area_groups:
            empty_label = QLabel("Keine Kompetenzen für dieses Fach hinterlegt.")
            set_label_style(empty_label, "subtle")
            self.competency_tree_layout.addWidget(empty_label)
            return
        for learning_area_group in subject_group.learning_area_groups:
            self.competency_tree_layout.addWidget(
                self._learning_area_widget(learning_area_group)
            )
        self.competency_tree_layout.addStretch(1)

    def _clear_competency_tree(self) -> None:
        while self.competency_tree_layout.count():
            layout_item = self.competency_tree_layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()

    def _current_subject_group(
        self,
    ) -> ObservationCompetencySubjectGroupViewModel | None:
        subject_key = str(self.subject_select.currentData() or "")
        for subject_group in self.competency_subject_groups:
            if subject_group.subject_key == subject_key:
                return subject_group
        return self._fallback_subject_group(subject_key)

    def _fallback_subject_group(
        self,
        subject_key: str,
    ) -> ObservationCompetencySubjectGroupViewModel | None:
        if not subject_key:
            return None
        learning_area_groups: dict[
            str,
            dict[str, list[ObservationCompetencyOptionViewModel]],
        ] = {}
        for competency in self.curriculum_adapter.list_competencies_for_subject(
            subject_key
        ):
            option = ObservationCompetencyOptionViewModel(
                competency_id=getattr(competency, "competency_id", ""),
                subject_key=getattr(competency, "subject_key", subject_key),
                subject_display_name=getattr(
                    competency,
                    "subject_display_name",
                    self.subject_select.currentText(),
                ),
                learning_area=self._learning_area_text(competency),
                competency_group=self._competency_group_text(competency),
                competency_text=getattr(competency, "competency_text", ""),
                competency_label=getattr(
                    competency,
                    "competency_label",
                    getattr(competency, "competency_display_name", ""),
                ),
            )
            learning_area_groups.setdefault(
                option.learning_area,
                {},
            ).setdefault(option.competency_group, []).append(option)
        return ObservationCompetencySubjectGroupViewModel(
            subject_key=subject_key,
            subject_display_name=self.subject_select.currentText(),
            learning_area_groups=tuple(
                ObservationLearningAreaGroupViewModel(
                    learning_area,
                    tuple(
                        ObservationCompetencyGroupViewModel(
                            competency_group,
                            tuple(competencies),
                        )
                        for competency_group, competencies in competency_groups.items()
                    ),
                )
                for learning_area, competency_groups in learning_area_groups.items()
            ),
        )

    def _learning_area_widget(
        self,
        learning_area_group: ObservationLearningAreaGroupViewModel,
    ) -> QWidget:
        area_widget = QWidget()
        area_layout = QVBoxLayout(area_widget)
        area_layout.setContentsMargins(0, 4, 0, 6)
        area_layout.setSpacing(4)

        area_key = self._area_key(learning_area_group)
        area_is_open = self._learning_area_has_selection(learning_area_group)

        area_button = QPushButton()
        area_button.setObjectName("ObservationAreaToggleButton")
        area_button.setFlat(True)
        area_button.setCursor(Qt.CursorShape.PointingHandCursor)
        area_button.clicked.connect(
            lambda _checked=False, key=area_key: self._toggle_competency_area(key)
        )
        area_button.setProperty("area_key", area_key)
        self.competency_area_buttons[area_key] = area_button
        area_layout.addWidget(area_button)

        topics_container = QWidget()
        topics_container.setObjectName("ObservationAreaTopics")
        topics_layout = QVBoxLayout(topics_container)
        topics_layout.setContentsMargins(12, 0, 0, 0)
        topics_layout.setSpacing(4)
        for competency_group in learning_area_group.competency_groups:
            topics_layout.addWidget(self._competency_group_widget(competency_group))
        topics_container.setVisible(area_is_open)
        self.competency_area_containers[area_key] = topics_container
        area_layout.addWidget(topics_container)
        self._set_area_button_text(area_key, area_is_open)
        return area_widget

    def _area_key(self, learning_area_group: ObservationLearningAreaGroupViewModel) -> str:
        first_group = (
            learning_area_group.competency_groups[0]
            if learning_area_group.competency_groups
            else None
        )
        first_competency = (
            first_group.competencies[0]
            if first_group is not None and first_group.competencies
            else None
        )
        subject_key = getattr(first_competency, "subject_key", "")
        return "|".join((
            str(subject_key),
            self._learning_area_text(learning_area_group),
        ))

    def _learning_area_has_selection(
        self,
        learning_area_group: ObservationLearningAreaGroupViewModel,
    ) -> bool:
        return any(
            self._competency_group_has_selection(competency_group)
            for competency_group in learning_area_group.competency_groups
        )

    def _toggle_competency_area(self, area_key: str) -> None:
        container = self.competency_area_containers.get(area_key)
        if container is None:
            return
        is_open = container.isHidden()
        container.setVisible(is_open)
        self._set_area_button_text(area_key, is_open)

    def _set_area_button_text(self, area_key: str, is_open: bool) -> None:
        button = self.competency_area_buttons.get(area_key)
        if button is None:
            return
        area_name = area_key.rsplit("|", 1)[-1] or "Ohne Kompetenzbereich"
        indicator = "▾" if is_open else "▸"
        button.setText(f"{indicator} Kompetenzbereich: {area_name}")

    def _competency_group_widget(
        self,
        competency_group: ObservationCompetencyGroupViewModel,
    ) -> QWidget:
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(12, 0, 0, 4)
        group_layout.setSpacing(3)
        topic_key = self._topic_key(competency_group)
        topic_is_open = self._competency_group_has_selection(competency_group)
        topic_button = QPushButton()
        topic_button.setObjectName("ObservationTopicToggleButton")
        topic_button.setFlat(True)
        topic_button.setCursor(Qt.CursorShape.PointingHandCursor)
        topic_button.clicked.connect(
            lambda _checked=False, key=topic_key: self._toggle_competency_topic(key)
        )
        topic_button.setProperty("topic_key", topic_key)
        self.competency_topic_buttons[topic_key] = topic_button
        group_layout.addWidget(topic_button)
        competencies_container = QWidget()
        competencies_container.setObjectName("ObservationTopicCompetencies")
        competencies_layout = QVBoxLayout(competencies_container)
        competencies_layout.setContentsMargins(12, 0, 0, 0)
        competencies_layout.setSpacing(3)
        for competency in competency_group.competencies:
            competencies_layout.addWidget(
                self._competency_checkbox_row(competency, topic_key)
            )
        competencies_container.setVisible(topic_is_open)
        self.competency_topic_containers[topic_key] = competencies_container
        group_layout.addWidget(competencies_container)
        self._set_topic_button_text(topic_key, topic_is_open)
        return group_widget

    def _topic_key(self, competency_group: ObservationCompetencyGroupViewModel) -> str:
        first_competency = (
            competency_group.competencies[0]
            if competency_group.competencies
            else None
        )
        subject_key = getattr(first_competency, "subject_key", "")
        learning_area = getattr(first_competency, "learning_area", "")
        return "|".join((
            str(subject_key),
            str(learning_area),
            self._competency_group_text(competency_group),
        ))

    def _competency_group_has_selection(
        self,
        competency_group: ObservationCompetencyGroupViewModel,
    ) -> bool:
        return any(
            competency.selected
            or self._competency_key(competency) in self.competency_rating_entries
            for competency in competency_group.competencies
        )

    def _toggle_competency_topic(self, topic_key: str) -> None:
        container = self.competency_topic_containers.get(topic_key)
        if container is None:
            return
        is_open = container.isHidden()
        container.setVisible(is_open)
        self._set_topic_button_text(topic_key, is_open)

    def _set_topic_button_text(self, topic_key: str, is_open: bool) -> None:
        button = self.competency_topic_buttons.get(topic_key)
        if button is None:
            return
        topic_name = topic_key.rsplit("|", 1)[-1] or "Ohne Thema"
        indicator = "▾" if is_open else "▸"
        button.setText(f"{indicator} Thema: {topic_name}")

    def _area_key_from_topic_key(self, topic_key: str) -> str:
        parts = topic_key.split("|", 2)
        if len(parts) < 2:
            return topic_key
        return "|".join(parts[:2])

    def _competency_checkbox_row(
        self,
        competency: ObservationCompetencyOptionViewModel,
        topic_key: str,
    ) -> QWidget:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(12, 0, 0, 0)
        row_layout.setSpacing(6)
        competency_key = self._competency_key(competency)
        checkbox = QCheckBox(self._competency_display_text(competency))
        checkbox.setToolTip(self._competency_detail_text(competency))
        checkbox.setProperty("competency_key", competency_key)
        checkbox.setProperty("subject_key", competency.subject_key)
        checkbox.setProperty("topic_key", topic_key)
        checkbox.setProperty("area_key", self._area_key_from_topic_key(topic_key))
        checkbox.setChecked(
            competency.selected or competency_key in self.competency_rating_entries
        )
        checkbox.stateChanged.connect(
            lambda _state, entry=competency: self._sync_competency_ratings(entry)
        )
        self.competency_checkboxes[competency_key] = checkbox
        row_layout.addWidget(checkbox, 1)
        return row_widget

    def _competency_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        title = QLabel("Kompetenzen")
        set_label_style(title, "card_title")
        hint = QLabel("Mehrfachauswahl möglich")
        set_label_style(hint, "muted")
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.competency_tree_container)
        return card

    def _competency_ratings_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        title = QLabel("Ausgewählte Kompetenzen bewerten")
        set_label_style(title, "card_title")
        hint = QLabel("Jede ausgewählte Kompetenz erhält eine eigene Bewertung.")
        set_label_style(hint, "muted")
        self.competency_ratings_container = QWidget()
        self.competency_ratings_layout = QVBoxLayout(self.competency_ratings_container)
        self.competency_ratings_layout.setContentsMargins(0, 2, 0, 0)
        self.competency_ratings_layout.setSpacing(4)
        self.competency_ratings_empty_state = QLabel(
            "Noch keine Kompetenz ausgewählt."
        )
        set_label_style(self.competency_ratings_empty_state, "subtle")
        self.competency_ratings_layout.addWidget(self.competency_ratings_empty_state)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.competency_ratings_container)
        return card

    def _attachments_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title = QLabel("Dokumente & Medien")
        set_label_style(title, "card_title")
        hint = QLabel("Dateien werden schülerzentriert im App-Datenordner abgelegt.")
        hint.setWordWrap(True)
        set_label_style(hint, "muted")
        self.attachment_type_select = QComboBox()
        self.attachment_type_select.addItems(DOCUMENT_TYPE_OPTIONS)
        default_type_index = self.attachment_type_select.findText("Sonstiges")
        if default_type_index >= 0:
            self.attachment_type_select.setCurrentIndex(default_type_index)
        add_file_button = QPushButton("+ Datei hinzufügen")
        add_file_button.clicked.connect(self.add_attachment_from_dialog)
        self.attachments_container = QWidget()
        self.attachments_layout = QVBoxLayout(self.attachments_container)
        self.attachments_layout.setContentsMargins(0, 0, 0, 0)
        self.attachments_layout.setSpacing(4)
        self.attachment_empty_state = QLabel(OBSERVATION_ATTACHMENT_EMPTY_STATE)
        set_label_style(self.attachment_empty_state, "subtle")
        set_label_style(self.attachment_feedback_label, "muted")

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(self._field_row("Dokumenttyp", self.attachment_type_select))
        layout.addWidget(add_file_button)
        layout.addWidget(self.attachments_container)
        layout.addWidget(self.attachment_feedback_label)
        self._render_attachments()
        return card

    def _field_row(self, label: str, widget: object) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(self._field_label(label), 1)
        row.addWidget(widget, 3)
        return row

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
        selected_competency_ratings = self._selected_competency_ratings()
        return ObservationDraftViewModel(
            student_id=self.student.student_id,
            student_name=self.student.display_name,
            date_text=self.date_input.date().toString("yyyy-MM-dd"),
            competency_ratings=selected_competency_ratings,
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
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            label = QLabel(attachment.display_label)
            label.setWordWrap(True)
            set_label_style(label, "small")
            remove_button = QPushButton("Entfernen")
            remove_button.clicked.connect(
                lambda _checked=False, row_index=index: self._remove_attachment(
                    row_index
                )
            )
            row.addWidget(label, 1)
            row.addWidget(remove_button, 0)
            row_widget = QWidget()
            row_widget.setLayout(row)
            self.attachments_layout.addWidget(row_widget)

    def _clear_attachments(self) -> None:
        while self.attachments_layout.count():
            layout_item = self.attachments_layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.setParent(None)

    def _remove_attachment(self, index: int) -> None:
        if index < 0 or index >= len(self.attachment_drafts):
            return
        self.attachment_drafts.pop(index)
        self._render_attachments()

    def _selected_competency_ratings(self) -> tuple[ObservationCompetencyRatingDraft, ...]:
        selected: list[ObservationCompetencyRatingDraft] = []
        for competency_key, catalog_entry in self.competency_rating_entries.items():
            rating_widget = self.competency_rating_widgets[competency_key]
            selected.append(
                ObservationCompetencyRatingDraft.from_catalog_entry(
                    catalog_entry,
                    str(rating_widget.currentData() or ""),
                )
            )
        return tuple(selected)

    def _sync_competency_ratings(
        self,
        catalog_entry: object | None = None,
    ) -> None:
        if not hasattr(self, "competency_ratings_layout"):
            return
        if catalog_entry is None:
            entries: tuple[object, ...] = tuple(self.competency_rating_entries.values())
        else:
            entries = (catalog_entry,)
        for entry in entries:
            competency_key = self._competency_key(entry)
            checkbox = self.competency_checkboxes.get(competency_key)
            checked = checkbox.isChecked() if checkbox is not None else True
            if checked:
                if competency_key not in self.competency_rating_widgets:
                    self._add_competency_rating_row(competency_key, entry)
            elif competency_key in self.competency_rating_widgets:
                self._remove_competency_rating_row(competency_key)

        self.competency_ratings_empty_state.setVisible(
            not self.competency_rating_widgets
        )

    def _add_competency_rating_row(
        self,
        competency_key: str,
        catalog_entry: object,
        initial_rating: str = "",
    ) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        subject_display_name = getattr(catalog_entry, "subject_display_name")
        competency_display_name = self._competency_display_text(catalog_entry)
        label = QLabel(f"{subject_display_name} · {competency_display_name}")
        label.setToolTip(self._competency_detail_text(catalog_entry))
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        rating_select = QComboBox()
        rating_select.setMinimumWidth(190)
        rating_select.addItem("Bewertung auswählen", "")
        for rating_option in OBSERVATION_RATING_OPTIONS:
            rating_select.addItem(rating_option, rating_option.split(" ", 1)[0])
        if initial_rating:
            rating_index = rating_select.findData(initial_rating)
            if rating_index >= 0:
                rating_select.setCurrentIndex(rating_index)
        remove_button = QPushButton("Entfernen")
        remove_button.clicked.connect(
            lambda _checked=False, key=competency_key: self._remove_competency_rating(
                key
            )
        )
        row.addWidget(label, 1)
        row.addWidget(rating_select, 0)
        row.addWidget(remove_button, 0)

        row_widget = QWidget()
        row_widget.setLayout(row)
        row_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.competency_rating_entries[competency_key] = catalog_entry
        self.competency_rating_widgets[competency_key] = rating_select
        self.competency_rating_rows[competency_key] = row_widget
        row_widget.setProperty("competency_key", competency_key)
        self.competency_ratings_layout.addWidget(row_widget)

    def _remove_competency_rating(self, competency_key: str) -> None:
        self._remove_competency_rating_row(competency_key)
        self._sync_visible_competency_checkbox(
            competency_key,
            Qt.CheckState.Unchecked,
        )

    def _remove_competency_rating_row(self, competency_key: str) -> None:
        self.competency_rating_entries.pop(competency_key, None)
        self.competency_rating_widgets.pop(competency_key, None)
        self.competency_rating_rows.pop(competency_key, None)
        for index in range(self.competency_ratings_layout.count()):
            layout_item = self.competency_ratings_layout.itemAt(index)
            widget = layout_item.widget()
            if widget is None:
                continue
            if widget.property("competency_key") == competency_key:
                removed_item = self.competency_ratings_layout.takeAt(index)
                removed_widget = removed_item.widget()
                if removed_widget is not None:
                    removed_widget.deleteLater()
                break
        self.competency_ratings_empty_state.setVisible(
            not self.competency_rating_widgets
        )

    def _sync_visible_competency_checkbox(
        self,
        competency_key: str,
        check_state: Qt.CheckState,
    ) -> None:
        checkbox = self.competency_checkboxes.get(competency_key)
        if checkbox is None:
            return
        checkbox.blockSignals(True)
        try:
            checkbox.setCheckState(check_state)
        finally:
            checkbox.blockSignals(False)
        if check_state == Qt.CheckState.Checked:
            area_key = str(checkbox.property("area_key") or "")
            if area_key:
                self._set_competency_area_visible(area_key, True)
            topic_key = str(checkbox.property("topic_key") or "")
            if topic_key:
                self._set_competency_topic_visible(topic_key, True)

    def _set_competency_area_visible(self, area_key: str, visible: bool) -> None:
        container = self.competency_area_containers.get(area_key)
        if container is None:
            return
        container.setVisible(visible)
        self._set_area_button_text(area_key, visible)

    def _set_competency_topic_visible(self, topic_key: str, visible: bool) -> None:
        container = self.competency_topic_containers.get(topic_key)
        if container is None:
            return
        container.setVisible(visible)
        self._set_topic_button_text(topic_key, visible)

    def _clear_competency_ratings(self) -> None:
        self.competency_rating_entries.clear()
        self.competency_rating_widgets.clear()
        self.competency_rating_rows.clear()
        if not hasattr(self, "competency_ratings_layout"):
            return
        while self.competency_ratings_layout.count():
            layout_item = self.competency_ratings_layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()
        self.competency_ratings_empty_state = QLabel(
            "Noch keine Kompetenz ausgewählt."
        )
        set_label_style(self.competency_ratings_empty_state, "subtle")
        self.competency_ratings_layout.addWidget(self.competency_ratings_empty_state)

    def _competency_key(self, catalog_entry: object) -> str:
        competency_id = str(getattr(catalog_entry, "competency_id", "")).strip()
        if competency_id:
            return competency_id
        return "|".join((
            getattr(catalog_entry, "subject_key"),
            getattr(catalog_entry, "learning_area"),
            getattr(catalog_entry, "competency_group"),
            getattr(catalog_entry, "competency_text"),
        ))

    def _learning_area_text(self, catalog_entry: object) -> str:
        return str(getattr(catalog_entry, "learning_area", "") or "").strip() or (
            "Ohne Kompetenzbereich"
        )

    def _competency_group_text(self, catalog_entry: object) -> str:
        return str(getattr(catalog_entry, "competency_group", "") or "").strip() or (
            "Ohne Thema"
        )

    def _competency_display_text(self, catalog_entry: object) -> str:
        return (
            str(getattr(catalog_entry, "competency_text", "") or "").strip()
            or str(getattr(catalog_entry, "competency_label", "") or "").strip()
            or str(getattr(catalog_entry, "competency_display_name", "") or "").strip()
            or self._learning_area_text(catalog_entry)
        )

    def _competency_detail_text(self, catalog_entry: object) -> str:
        detail = str(getattr(catalog_entry, "competency_detail_label", "") or "").strip()
        if detail:
            return detail
        return "\n".join((
            f"Kompetenzbereich: {self._learning_area_text(catalog_entry)}",
            f"Thema: {self._competency_group_text(catalog_entry)}",
            f"Kompetenz: {self._competency_display_text(catalog_entry)}",
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
        if visible_subject:
            subject_index = self.subject_select.findData(visible_subject)
            if subject_index >= 0:
                self.subject_select.setCurrentIndex(subject_index)
        for rating in self.initial_draft.competency_ratings:
            competency_key = self._competency_key(rating)
            self._add_competency_rating_row(
                competency_key,
                rating,
                rating.rating,
            )
            self._sync_visible_competency_checkbox(
                competency_key,
                Qt.CheckState.Checked,
            )
        self.competency_ratings_empty_state.setVisible(
            not self.competency_rating_widgets
        )
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
            QMessageBox.warning(
                self,
                "Hinweis",
                OBSERVATION_SAVE_VALIDATION_MESSAGE,
            )
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
                str(getattr(result, "message", "Beobachtung konnte nicht gespeichert werden.")),
            )
            return
        self.accept()
