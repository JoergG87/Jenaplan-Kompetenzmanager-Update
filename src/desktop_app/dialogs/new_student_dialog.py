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
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.dialog_buttons import configure_save_cancel_buttons
from src.desktop_app.view_models.master_data_view_model import MasterDataItemViewModel
from src.desktop_app.theme import set_label_style


STUDENT_DIALOG_SELECT_PLACEHOLDER = "Bitte auswählen"
STUDENT_DIALOG_EMPTY_NAME_MESSAGE = "Bitte einen Namen eingeben."
STUDENT_DIALOG_GROUP_REQUIRED_MESSAGE = "Bitte eine Stammgruppe auswählen."
STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE = "Bitte einen Kurs auswählen."
STUDENT_DIALOG_DRAFT_GROUP_MESSAGE = (
    "Diese Stammgruppe kann noch nicht für neue Schüler verwendet werden."
)
STUDENT_DIALOG_DRAFT_COURSE_MESSAGE = (
    "Dieser Kurs kann noch nicht für neue Schüler verwendet werden."
)


class NewStudentDialog(QDialog):
    """Collect input and dispatch student.create through the adapter."""

    student_created = Signal(str)

    def __init__(
        self,
        adapter: StudentDesktopAdapter,
        master_data_adapter: MasterDataDesktopAdapter | None = None,
    ) -> None:
        super().__init__()
        self.adapter = adapter
        self.master_data_adapter = master_data_adapter or MasterDataDesktopAdapter(
            adapter
        )
        master_data = self.master_data_adapter.view_model()
        self.group_items = {group.item_id: group for group in master_data.groups}
        self.course_items = {course.item_id: course for course in master_data.courses}
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

        self._populate_master_data_select(
            self.group_select,
            tuple(self.group_items.values()),
            "Keine Stammgruppen vorhanden",
        )
        self._populate_master_data_select(
            self.course_select,
            tuple(self.course_items.values()),
            "Keine Kurse vorhanden",
        )

        form.addRow("Vorname", self.first_name_input)
        form.addRow("Nachname", self.last_name_input)
        form.addRow("Stammgruppe", self.group_select)
        form.addRow("Kurs", self.course_select)
        form.addRow("Notiz", self.notes_input)
        layout.addLayout(form)

        self.error_label = QLabel("")
        set_label_style(self.error_label, "error")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)

    def save(self) -> None:
        """Dispatch student.create and close only on success."""
        validation_message = self._validation_message()
        if validation_message:
            self.error_label.setText(validation_message)
            return

        result = self.adapter.save_new_student(
            first_name=self.first_name_input.text(),
            last_name=self.last_name_input.text(),
            group_id=str(self.group_select.currentData()),
            course_id=str(self.course_select.currentData()),
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

    def _populate_master_data_select(
        self,
        select: QComboBox,
        items: tuple[MasterDataItemViewModel, ...],
        empty_label: str,
    ) -> None:
        select.addItem(STUDENT_DIALOG_SELECT_PLACEHOLDER, "")
        if not items:
            select.addItem(empty_label, "")
            return
        for item in items:
            select.addItem(item.name, item.item_id)

    def _validation_message(self) -> str:
        if not self.first_name_input.text().strip():
            return STUDENT_DIALOG_EMPTY_NAME_MESSAGE
        if not self.last_name_input.text().strip():
            return STUDENT_DIALOG_EMPTY_NAME_MESSAGE

        group = self._selected_item(self.group_select, self.group_items)
        if group is None:
            return STUDENT_DIALOG_GROUP_REQUIRED_MESSAGE
        if not group.is_persistent:
            return STUDENT_DIALOG_DRAFT_GROUP_MESSAGE

        course = self._selected_item(self.course_select, self.course_items)
        if course is None:
            return STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE
        if not course.is_persistent:
            return STUDENT_DIALOG_DRAFT_COURSE_MESSAGE

        return ""

    def _selected_item(
        self,
        select: QComboBox,
        items: dict[str, MasterDataItemViewModel],
    ) -> MasterDataItemViewModel | None:
        item_id = str(select.currentData() or "")
        if not item_id:
            return None
        return items.get(item_id)
