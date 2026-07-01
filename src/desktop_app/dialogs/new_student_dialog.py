"""New-student dialog for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from src.application.dispatcher import ErrorResult, SuccessResult
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter


class NewStudentDialog(QDialog):
    """Collect input and dispatch student.create through the adapter."""

    student_created = Signal(str)

    def __init__(self, adapter: StudentDesktopAdapter) -> None:
        super().__init__()
        self.adapter = adapter
        self.group_ids = adapter.group_id_by_name()
        self.course_ids = adapter.course_id_by_name()
        self.setWindowTitle("Neuer Schüler")
        self.setModal(True)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.group_select = QComboBox()
        self.course_select = QComboBox()
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(90)

        self.group_select.addItems(tuple(self.group_ids))
        self.course_select.addItems(tuple(self.course_ids))

        form.addRow("Vorname", self.first_name_input)
        form.addRow("Nachname", self.last_name_input)
        form.addRow("Stammgruppe", self.group_select)
        form.addRow("Kurs", self.course_select)
        form.addRow("Notiz", self.notes_input)
        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #B00020;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)

    def save(self) -> None:
        """Dispatch student.create and close only on success."""
        group_name = self.group_select.currentText()
        course_name = self.course_select.currentText()
        result = self.adapter.save_new_student(
            first_name=self.first_name_input.text(),
            last_name=self.last_name_input.text(),
            group_id=self.group_ids.get(group_name, group_name),
            course_id=self.course_ids.get(course_name, course_name),
            student_notes=self.notes_input.toPlainText(),
        )
        if isinstance(result, SuccessResult):
            self.student_created.emit(getattr(result.value, "student_id", ""))
            self.accept()
            return
        if isinstance(result, ErrorResult):
            self.error_label.setText(result.message)
            return
        self.error_label.setText(f"Unerwartetes Ergebnis: {type(result).__name__}")
