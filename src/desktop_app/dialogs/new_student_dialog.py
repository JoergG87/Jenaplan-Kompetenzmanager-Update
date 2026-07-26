"""New-student dialog for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from src.application.dispatcher import ErrorResult, SuccessResult
from src.core.records import StudentRecord
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.components import AppCard, DialogHeader, InlineMessage, SectionHeader
from src.desktop_app.dialogs.dialog_buttons import (
    DialogActionBar,
    configure_save_cancel_buttons,
)
from src.desktop_app.motion import MotionDialog
from src.desktop_app.view_models.master_data_view_model import MasterDataItemViewModel


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


class NewStudentDialog(MotionDialog):
    """Collect input and dispatch student create/update through the adapter."""

    student_created = Signal(str)
    student_updated = Signal(str)

    def __init__(
        self,
        adapter: StudentDesktopAdapter,
        master_data_adapter: MasterDataDesktopAdapter | None = None,
        student: StudentRecord | None = None,
    ) -> None:
        super().__init__()
        self.adapter = adapter
        self.student = student
        self.master_data_adapter = master_data_adapter or MasterDataDesktopAdapter(
            adapter
        )
        master_data = self.master_data_adapter.view_model()
        self.group_items = {group.item_id: group for group in master_data.groups}
        self.course_items = {course.item_id: course for course in master_data.courses}
        self.setWindowTitle("Schüler bearbeiten" if self.student else "Neuer Schüler")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.resize(560, 590)
        self._build()
        self._prefill_student()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        dialog_title = "Schüler bearbeiten" if self.student else "Neuer Schüler"
        dialog_context = (
            f"{self.student.first_name} {self.student.last_name}".strip()
            if self.student is not None
            else "Schülerakte anlegen"
        )
        layout.addWidget(
            DialogHeader(
                dialog_title,
                dialog_context,
                "Grunddaten und pädagogische Notiz in einem ruhigen Arbeitsgang erfassen.",
                icon_name="student-record",
            )
        )

        form_card = AppCard("default")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(18, 16, 18, 18)
        form_card_layout.setSpacing(12)
        form_card_layout.addWidget(
            SectionHeader("Stammdaten", "Pflichtangaben stehen jeweils direkt über dem Feld.")
        )
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setVerticalSpacing(9)

        self.first_name_input = QLineEdit()
        self.first_name_input.setAccessibleName("Vorname")
        self.last_name_input = QLineEdit()
        self.last_name_input.setAccessibleName("Nachname")
        self.group_select = QComboBox()
        self.group_select.setAccessibleName("Stammgruppe")
        self.course_select = QComboBox()
        self.course_select.setAccessibleName("Kurs")
        self.notes_input = QTextEdit()
        self.notes_input.setAccessibleName("Pädagogische Notiz")
        self.notes_input.setFixedHeight(90)

        self._populate_master_data_select(
            self.group_select,
            tuple(self.group_items.values()),
            "Keine Stammgruppen – zuerst unter Stammdaten anlegen",
        )
        self._populate_master_data_select(
            self.course_select,
            tuple(self.course_items.values()),
            "Keine Kurse – zuerst unter Stammdaten anlegen",
        )

        form.addRow("Vorname", self.first_name_input)
        form.addRow("Nachname", self.last_name_input)
        form.addRow("Stammgruppe", self.group_select)
        form.addRow("Kurs", self.course_select)
        form.addRow("Notiz", self.notes_input)
        form_card_layout.addLayout(form)
        layout.addWidget(form_card, 1)

        self.validation_message = InlineMessage()
        self.validation_message.setAccessibleName("Validierung der Schülerdaten")
        self.error_label = self.validation_message.label
        layout.addWidget(self.validation_message)

        buttons = DialogActionBar(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)
        self.first_name_input.setFocus()

    def save(self) -> None:
        """Dispatch student create/update and close only on success."""
        validation_message = self._validation_message()
        if validation_message:
            self.validation_message.set_message(validation_message, tone="error")
            return
        self.validation_message.set_message("")

        payload = {
            "first_name": self.first_name_input.text(),
            "last_name": self.last_name_input.text(),
            "group_id": str(self.group_select.currentData()),
            "course_id": str(self.course_select.currentData()),
            "student_notes": self.notes_input.toPlainText(),
        }
        if self.student is None:
            result = self.adapter.save_new_student(**payload)
        else:
            result = self.adapter.save_existing_student(
                student_id=self.student.student_id,
                **payload,
            )

        if isinstance(result, SuccessResult):
            student_id = getattr(result.value, "student_id", "")
            if self.student is None:
                self.student_created.emit(student_id)
            else:
                self.student_updated.emit(student_id)
            self.accept()
            return
        if isinstance(result, ErrorResult):
            self.validation_message.set_message(result.message, tone="error")
            return
        self.validation_message.set_message(
            f"Unerwartetes Ergebnis: {type(result).__name__}",
            tone="error",
        )

    def _prefill_student(self) -> None:
        if self.student is None:
            return
        self.first_name_input.setText(self.student.first_name)
        self.last_name_input.setText(self.student.last_name)
        self._select_combo_data(self.group_select, self.student.group_id)
        self._select_combo_data(self.course_select, self.student.course_id)
        self.notes_input.setPlainText(self.student.student_notes)

    def _select_combo_data(self, select: QComboBox, item_id: str) -> None:
        index = select.findData(item_id)
        if index >= 0:
            select.setCurrentIndex(index)

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
