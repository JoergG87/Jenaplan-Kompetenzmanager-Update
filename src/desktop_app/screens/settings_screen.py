"""Settings screen for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.theme import create_card, set_label_style
from src.desktop_app.view_models.settings_view_model import (
    DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE,
    DocumentationSubjectOptionViewModel,
    SettingsViewModel,
)


DOCUMENTATION_SUBJECTS_HELP_TEXT = (
    "Diese Auswahl steuert, welche Fächer im Dokumentationsstand "
    "berücksichtigt werden. Beobachtungen bleiben immer erhalten."
)


class SettingsScreen(QWidget):
    """Show app settings and emit save requests without persistence logic."""

    documentation_subjects_save_requested = Signal(tuple)

    def __init__(self) -> None:
        super().__init__()
        self.documentation_subject_checkboxes: dict[str, QCheckBox] = {}
        self.documentation_subjects_layout = QVBoxLayout()
        self.status_label = QLabel("")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Einstellungen")
        set_label_style(title, "screen_title")
        subtitle = QLabel("Grundlagen für Dokumentation und Auswertung")
        set_label_style(subtitle, "muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._documentation_subjects_card())
        layout.addStretch(1)

    def set_settings(self, view_model: SettingsViewModel) -> None:
        """Replace settings content with the current view model."""
        self.set_documentation_subjects(view_model.documentation_subjects)

    def set_documentation_subjects(
        self,
        subjects: tuple[DocumentationSubjectOptionViewModel, ...],
    ) -> None:
        """Replace the documentation subject checkbox list."""
        self._clear_documentation_subjects()
        self.documentation_subject_checkboxes = {}
        for subject in subjects:
            checkbox = QCheckBox(subject.label)
            checkbox.setObjectName(
                f"DocumentationSubjectCheckbox_{subject.subject_id}"
            )
            checkbox.setChecked(subject.selected)
            self.documentation_subject_checkboxes[subject.subject_id] = checkbox
            self.documentation_subjects_layout.addWidget(checkbox)
        self.documentation_subjects_layout.addStretch(1)

    def show_documentation_subjects_saved(self) -> None:
        """Show the calm save confirmation for documentation subjects."""
        self.status_label.setText(DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE)

    def _documentation_subjects_card(self) -> QFrame:
        card = create_card()
        card.setObjectName("DocumentationSubjectSettingsSection")
        layout = QVBoxLayout(card)
        header = QHBoxLayout()
        title = QLabel("Dokumentationsrelevante Fächer")
        set_label_style(title, "section_title")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        help_label = QLabel(DOCUMENTATION_SUBJECTS_HELP_TEXT)
        help_label.setWordWrap(True)
        set_label_style(help_label, "muted")
        layout.addWidget(help_label)
        layout.addLayout(self.documentation_subjects_layout)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        save_button = QPushButton("Speichern")
        save_button.setObjectName("DocumentationSubjectSaveButton")
        save_button.clicked.connect(self._emit_documentation_subjects_save)
        action_row.addWidget(save_button)
        layout.addLayout(action_row)

        set_label_style(self.status_label, "muted")
        self.status_label.setObjectName("SettingsStatusLabel")
        layout.addWidget(self.status_label)
        return card

    def _emit_documentation_subjects_save(self) -> None:
        selected_subject_ids = tuple(
            subject_id
            for subject_id, checkbox in self.documentation_subject_checkboxes.items()
            if checkbox.isChecked()
        )
        self.documentation_subjects_save_requested.emit(selected_subject_ids)

    def _clear_documentation_subjects(self) -> None:
        while self.documentation_subjects_layout.count():
            item = self.documentation_subjects_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
