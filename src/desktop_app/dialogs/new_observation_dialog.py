"""New-observation dialog for the PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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
    ObservationCompetencyRatingDraft,
    ObservationDraftViewModel,
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
    ) -> None:
        super().__init__()
        self.student = student
        self.curriculum_adapter = curriculum_adapter or CurriculumDesktopAdapter()
        self.observation_adapter = observation_adapter
        self.initial_draft = initial_draft
        self.attachment_feedback_label = QLabel("")
        self.competency_rating_entries: dict[str, object] = {}
        self.competency_rating_widgets: dict[str, QComboBox] = {}
        self.competency_rating_rows: dict[str, QWidget] = {}
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

        self.competency_list = QListWidget()
        self.competency_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.competency_list.setMinimumHeight(86)
        self.competency_list.setMaximumHeight(138)
        self.competency_list.itemChanged.connect(self._sync_competency_ratings)
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
        for subject in self.curriculum_adapter.list_active_subjects():
            self.subject_select.addItem(subject.display_name, subject.subject_key)

    def _refresh_competencies(self) -> None:
        self.competency_list.blockSignals(True)
        try:
            self.competency_list.clear()
            subject_key = str(self.subject_select.currentData() or "")
            competencies = self.curriculum_adapter.list_competencies_for_subject(
                subject_key
            )
            if not competencies:
                item = QListWidgetItem("Keine Kompetenzen für dieses Fach hinterlegt.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.competency_list.addItem(item)
                return
            for competency in competencies:
                competency_key = self._competency_key(competency)
                item = QListWidgetItem(competency.competency_display_name)
                item.setData(Qt.ItemDataRole.UserRole, competency)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if competency_key in self.competency_rating_entries
                    else Qt.CheckState.Unchecked
                )
                item.setToolTip(competency.competency_detail_label)
                self.competency_list.addItem(item)
        finally:
            self.competency_list.blockSignals(False)

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
        layout.addWidget(self.competency_list)
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
        _changed_item: QListWidgetItem | None = None,
    ) -> None:
        if not hasattr(self, "competency_ratings_layout"):
            return
        for row in range(self.competency_list.count()):
            item = self.competency_list.item(row)
            catalog_entry = item.data(Qt.ItemDataRole.UserRole)
            if catalog_entry is None:
                continue
            competency_key = self._competency_key(catalog_entry)
            if item.checkState() == Qt.CheckState.Checked:
                if competency_key not in self.competency_rating_widgets:
                    self._add_competency_rating_row(competency_key, catalog_entry)
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
        competency_display_name = getattr(
            catalog_entry,
            "competency_display_name",
            getattr(catalog_entry, "learning_area"),
        )
        label = QLabel(f"{subject_display_name} · {competency_display_name}")
        label.setToolTip(
            getattr(
                catalog_entry,
                "competency_detail_label",
                getattr(catalog_entry, "competency_text", ""),
            )
        )
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
        self.competency_list.blockSignals(True)
        try:
            for row in range(self.competency_list.count()):
                item = self.competency_list.item(row)
                catalog_entry = item.data(Qt.ItemDataRole.UserRole)
                if catalog_entry is None:
                    continue
                if self._competency_key(catalog_entry) == competency_key:
                    item.setCheckState(check_state)
                    break
        finally:
            self.competency_list.blockSignals(False)

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
