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
    QTextEdit,
    QDateEdit,
    QVBoxLayout,
)

from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
)
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_ATTACHMENT_EMPTY_STATE,
    OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE,
    OBSERVATION_CONTEXT_OPTIONS,
    OBSERVATION_RATING_OPTIONS,
    OBSERVATION_SAVE_PLACEHOLDER_MESSAGE,
    ObservationCompetencyDraft,
    ObservationDraftViewModel,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


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
        self.setWindowTitle("Neue Beobachtung")
        self.setModal(True)
        self.resize(760, 720)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(f"Neue Beobachtung für {self.student.display_name}")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        student_context = QLabel(
            f"{self.student.group_name} · {self.student.course_name}"
        )
        student_context.setStyleSheet("color: #555;")
        layout.addWidget(title)
        layout.addWidget(student_context)

        form_card = self._card()
        form_layout = QVBoxLayout(form_card)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())

        self.subject_select = QComboBox()
        self._populate_subjects()
        self.subject_select.currentIndexChanged.connect(self._refresh_competencies)

        self.competency_list = QListWidget()
        self.competency_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.competency_list.setMinimumHeight(120)
        self._refresh_competencies()

        self.context_select = QComboBox()
        self.context_select.addItems(OBSERVATION_CONTEXT_OPTIONS)

        self.rating_select = QComboBox()
        self.rating_select.addItems(OBSERVATION_RATING_OPTIONS)

        self.note_input = QTextEdit()
        self.note_input.setMinimumHeight(120)

        form_layout.addLayout(self._field_row("Datum", self.date_input))
        form_layout.addLayout(self._field_row("Fach", self.subject_select))
        form_layout.addWidget(self._competency_card())
        form_layout.addLayout(self._field_row("Kontext", self.context_select))
        form_layout.addLayout(self._field_row("Bewertung", self.rating_select))
        form_layout.addWidget(self._field_label("Notiz"))
        form_layout.addWidget(self.note_input)
        layout.addWidget(form_card)

        layout.addWidget(self._attachments_card())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save_draft)
        layout.addWidget(buttons)

    def _populate_subjects(self) -> None:
        for subject in self.curriculum_adapter.list_active_subjects():
            self.subject_select.addItem(subject.display_name, subject.subject_key)

    def _refresh_competencies(self) -> None:
        self.competency_list.clear()
        subject_key = str(self.subject_select.currentData() or "")
        competencies = self.curriculum_adapter.list_competencies_for_subject(subject_key)
        if not competencies:
            item = QListWidgetItem("Keine Kompetenzen für dieses Fach hinterlegt.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.competency_list.addItem(item)
            return
        for competency in competencies:
            item = QListWidgetItem(competency.competency_display_name)
            item.setData(Qt.ItemDataRole.UserRole, competency)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setToolTip(competency.competency_detail_label)
            self.competency_list.addItem(item)

    def _competency_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Kompetenzen")
        title.setStyleSheet("font-weight: 600;")
        hint = QLabel("Mehrfachauswahl möglich")
        hint.setStyleSheet("color: #555;")
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.competency_list)
        return card

    def _attachments_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        title = QLabel("Dokumente & Medien")
        title.setStyleSheet("font-weight: 600;")
        hint = QLabel(
            "Fotos, Dateien oder andere Nachweise können später an Beobachtungen "
            "angehängt werden."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555;")
        add_file_button = QPushButton("Datei hinzufügen")
        add_file_button.clicked.connect(self.show_attachment_placeholder)
        empty_state = QLabel(OBSERVATION_ATTACHMENT_EMPTY_STATE)
        empty_state.setStyleSheet("color: #666;")
        self.attachment_feedback_label.setStyleSheet("color: #555;")

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
        field_label.setStyleSheet("color: #555;")
        return field_label

    def _card(self) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        return card

    def show_attachment_placeholder(self) -> None:
        """Show a non-persistent attachment message."""
        self.attachment_feedback_label.setText(OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE)

    def create_draft(self) -> ObservationDraftViewModel:
        """Return the non-persistent UI draft."""
        selected_competencies = self._selected_competencies()
        return ObservationDraftViewModel(
            student_id=self.student.student_id,
            student_name=self.student.display_name,
            date_text=self.date_input.date().toString("yyyy-MM-dd"),
            subject_key=str(self.subject_select.currentData() or ""),
            subject=self.subject_select.currentText(),
            competencies=selected_competencies,
            context=self.context_select.currentText(),
            rating=self.rating_select.currentText(),
            note=self.note_input.toPlainText(),
        )

    def _selected_competencies(self) -> tuple[ObservationCompetencyDraft, ...]:
        selected: list[ObservationCompetencyDraft] = []
        for row in range(self.competency_list.count()):
            item = self.competency_list.item(row)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            catalog_entry = item.data(Qt.ItemDataRole.UserRole)
            if catalog_entry is not None:
                selected.append(ObservationCompetencyDraft.from_catalog_entry(catalog_entry))
        return tuple(selected)

    def save_draft(self) -> None:
        """Close after showing that persistence is intentionally not implemented."""
        self.create_draft()
        QMessageBox.information(
            self,
            "Hinweis",
            OBSERVATION_SAVE_PLACEHOLDER_MESSAGE,
        )
        self.accept()
