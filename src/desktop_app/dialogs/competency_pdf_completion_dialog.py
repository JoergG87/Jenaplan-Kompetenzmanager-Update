"""Collect explicit development levels; validation/persistence stays in application code."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QScrollArea,
    QTabWidget, QVBoxLayout, QWidget,
)
from src.application.competency_pdf_completion import pending_competency_pdf_rows
from src.desktop_app.view_models.observation_view_model import RATING_LABELS_BY_PROFILE


class CompetencyPdfCompletionDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Entwicklungsstände ergänzen")
        self.resize(920, 680)
        layout = QVBoxLayout(self)
        introduction = QLabel(
            "Für das Eltern-PDF braucht jede aktuelle Kompetenz einen Entwicklungsstand. "
            "Bitte wähle die offenen Stände ausdrücklich aus. Mit „Auswahl speichern und weiter“ "
            "werden deine Eingaben im Kinderprofil gespeichert."
        )
        introduction.setWordWrap(True)
        layout.addWidget(introduction)
        self.remaining_label = QLabel()
        layout.addWidget(self.remaining_label)
        tabs = QTabWidget()
        tabs.setUsesScrollButtons(True)
        tabs.setElideMode(Qt.TextElideMode.ElideNone)
        tabs.tabBar().setExpanding(False)
        layout.addWidget(tabs)
        self.rating_inputs = {}
        pending = pending_competency_pdf_rows(model)
        for subject in model.subjects:
            rows = tuple(row for group, row in pending if group is subject)
            if not rows:
                continue
            page = QWidget()
            body = QVBoxLayout(page)
            for row in rows:
                line = QHBoxLayout()
                label = QLabel(row.text + "\n" + row.context)
                label.setWordWrap(True)
                line.addWidget(label, 3)
                choice = QComboBox()
                choice.setAccessibleName("Entwicklungsstand: " + row.text)
                choice.addItem("Bitte auswählen", "")
                for token in ("--", "-", "+", "++"):
                    choice.addItem(RATING_LABELS_BY_PROFILE[subject.rating_profile][token], token)
                choice.setMinimumWidth(220)
                choice.currentIndexChanged.connect(self._update_remaining)
                self.rating_inputs[row.competency_id] = choice
                line.addWidget(choice, 2)
                body.addLayout(line)
            body.addStretch()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            tabs.addTab(scroll, f"{subject.name} ({len(rows)})")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.save_button = buttons.addButton(
            "Auswahl speichern und weiter", QDialogButtonBox.ButtonRole.AcceptRole,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_remaining()

    def _update_remaining(self, *_):
        count = sum(not choice.currentData() for choice in self.rating_inputs.values())
        self.remaining_label.setText(f"Noch {count} Kompetenzen offen")
        self.save_button.setEnabled(count == 0)

    def selections(self):
        return {key: choice.currentData() for key, choice in self.rating_inputs.items()}
