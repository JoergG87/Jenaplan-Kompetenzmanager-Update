"""New-observation UX prototype dialog for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE,
    OBSERVATION_CONTEXT_OPTIONS,
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_SAVE_PLACEHOLDER_MESSAGE,
    ObservationCompetencyRatingDraft,
    ObservationDraftViewModel,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel
from src.desktop_app.theme import create_card, set_label_style


class NewObservationDialog(QDialog):
    """Collect a non-persistent observation draft for UX validation."""

    def __init__(
        self,
        student: StudentDetailViewModel,
        curriculum_adapter: CurriculumDesktopAdapter | None = None,
    ) -> None:
        super().__init__()
        self.student = student
        self.curriculum_adapter = curriculum_adapter or CurriculumDesktopAdapter()
        self.attachment_feedback_label = QLabel("")
        self.competency_rating_entries: dict[str, object] = {}
        self.competency_rating_widgets: dict[str, QComboBox] = {}
        self.competency_rating_rows: dict[str, QWidget] = {}
        self.setWindowTitle("Neue Beobachtung")
        self.setModal(True)
        self.setMinimumSize(700, 560)
        self.resize(760, 640)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)

        title = QLabel(f"Neue Beobachtung für {self.student.display_name}")
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
        hint = QLabel(
            "Fotos, Dateien oder andere Nachweise können später an Beobachtungen "
            "angehängt werden."
        )
        hint.setWordWrap(True)
        set_label_style(hint, "muted")
        add_file_button = QPushButton("Datei hinzufügen")
        add_file_button.clicked.connect(self.show_attachment_placeholder)
        empty_state = QLabel(OBSERVATION_ATTACHMENT_EMPTY_STATE)
        set_label_style(empty_state, "subtle")
        set_label_style(self.attachment_feedback_label, "muted")

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(add_file_button)
        layout.addWidget(empty_state)
        layout.addWidget(self.attachment_feedback_label)
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

    def show_attachment_placeholder(self) -> None:
        """Show a non-persistent attachment message."""
        self.attachment_feedback_label.setText(OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE)

    def create_draft(self) -> ObservationDraftViewModel:
        """Return the non-persistent UI draft."""
        selected_competency_ratings = self._selected_competency_ratings()
        return ObservationDraftViewModel(
            student_id=self.student.student_id,
            student_name=self.student.display_name,
            date_text=self.date_input.date().toString("yyyy-MM-dd"),
            competency_ratings=selected_competency_ratings,
            context=self.context_select.currentText(),
            note=self.note_input.toPlainText(),
        )

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
    ) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        subject_display_name = getattr(catalog_entry, "subject_display_name")
        competency_display_name = getattr(catalog_entry, "competency_display_name")
        label = QLabel(f"{subject_display_name} · {competency_display_name}")
        label.setToolTip(getattr(catalog_entry, "competency_detail_label"))
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        rating_select = QComboBox()
        rating_select.setMinimumWidth(190)
        rating_select.addItem("Bewertung auswählen", "")
        for rating_option in OBSERVATION_RATING_OPTIONS:
            rating_select.addItem(rating_option, rating_option)
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
        return "|".join((
            getattr(catalog_entry, "subject_key"),
            getattr(catalog_entry, "learning_area"),
            getattr(catalog_entry, "competency_group"),
            getattr(catalog_entry, "competency_text"),
        ))

    def save_draft(self) -> None:
        """Close after showing that persistence is intentionally not implemented."""
        self.create_draft()
        QMessageBox.information(
            self,
            "Hinweis",
            OBSERVATION_SAVE_PLACEHOLDER_MESSAGE,
        )
        self.accept()
