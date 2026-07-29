"""New-student dialog for the PySide6 desktop app."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.application.dispatcher import ErrorResult, SuccessResult
from src.application.school_year_assignment import MembershipChangeStatus
from src.core.school_year import AssignmentResolutionStatus, V3Student
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
        student: V3Student | None = None,
    ) -> None:
        super().__init__()
        self.adapter = adapter
        self.student = student
        self.master_data_adapter = master_data_adapter or MasterDataDesktopAdapter(
            adapter
        )
        master_data = self.master_data_adapter.view_model()
        self.group_items = {
            group.item_id: group for group in master_data.active_groups
        }
        self.course_items = {
            course.item_id: course for course in master_data.active_courses
        }
        self.current_school_year = self.adapter.current_school_year()
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
        self.school_year_label = QLabel(
            (
                self.current_school_year.label
                if self.current_school_year is not None
                else "Kein aktuelles Schuljahr festgelegt"
            )
        )
        self.school_year_label.setAccessibleName("Aktuelles Schuljahr")

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
        if self.student is None:
            form.addRow("Aktuelles Schuljahr", self.school_year_label)
            form.addRow("Stammgruppe", self.group_select)
            form.addRow("Kurs", self.course_select)
        form.addRow("Notiz", self.notes_input)
        form_card_layout.addLayout(form)
        layout.addWidget(form_card, 1)
        if self.student is not None:
            layout.addWidget(self._membership_card())

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

    def _membership_card(self) -> AppCard:
        membership = self.adapter.current_membership_for_student(
            self.student.student_id
        )
        card = AppCard("soft")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 16)
        card_layout.setSpacing(10)
        card_layout.addWidget(
            SectionHeader(
                "Aktuelle Zuordnung",
                "Kurs, Stammgruppe und Austritt werden bewusst getrennt von den Stammdaten geändert.",
            )
        )
        summary = QLabel(
            (
                f"{membership.group_name or 'Ohne Stammgruppe'} · "
                f"{membership.course_name or 'Ohne Kurs'}"
            )
        )
        summary.setAccessibleName("Aktuelle Stammgruppe und aktueller Kurs")
        card_layout.addWidget(summary)
        actions = QHBoxLayout()
        change_button = QPushButton("Zuordnung ändern")
        change_button.clicked.connect(self._open_membership_change)
        exit_button = QPushButton("Austritt erfassen")
        exit_button.clicked.connect(self._open_exit)
        archive_button = QPushButton("Archivieren")
        archive_button.clicked.connect(self._archive_student)
        actions.addWidget(change_button)
        actions.addWidget(exit_button)
        actions.addWidget(archive_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)
        return card

    def _open_membership_change(self) -> None:
        dialog = StudentMembershipChangeDialog(
            self.adapter,
            self.master_data_adapter,
            self.student.student_id,
            self,
        )
        if dialog.exec():
            self.student_updated.emit(self.student.student_id)
            self.accept()

    def _open_exit(self) -> None:
        dialog = StudentExitDialog(
            self.adapter,
            self.student.student_id,
            self,
        )
        if dialog.exec():
            self.student_updated.emit(self.student.student_id)
            self.accept()

    def _archive_student(self) -> None:
        answer = QMessageBox.question(
            self,
            "Kind archivieren",
            "Das Kind archivieren? Eine aktive Einschreibung muss vorher "
            "separat beendet werden; Zuordnungen werden dabei nicht verändert.",
            QMessageBox.StandardButton.Cancel
            | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer is not QMessageBox.StandardButton.Yes:
            return
        result = self.adapter.archive_student_master_data(
            self.student.student_id
        )
        if isinstance(result, SuccessResult):
            self.student_updated.emit(self.student.student_id)
            self.accept()
            return
        if isinstance(result, ErrorResult):
            self.validation_message.set_message(result.message, tone="error")

    def save(self) -> None:
        """Dispatch student create/update and close only on success."""
        validation_message = self._validation_message()
        if validation_message:
            self.validation_message.set_message(validation_message, tone="error")
            return
        self.validation_message.set_message("")

        master_data_payload = {
            "first_name": self.first_name_input.text(),
            "last_name": self.last_name_input.text(),
            "student_notes": self.notes_input.toPlainText(),
        }
        if self.student is None:
            result = self.adapter.save_new_student(
                **master_data_payload,
                group_id=str(self.group_select.currentData()),
                course_id=str(self.course_select.currentData()),
            )
        else:
            result = self.adapter.save_existing_student(
                student_id=self.student.student_id,
                **master_data_payload,
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
        self.notes_input.setPlainText(self.student.notes)

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
        if self.student is not None:
            return ""
        if self.current_school_year is None:
            return "Es ist kein aktuelles Schuljahr festgelegt."

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


class StudentMembershipChangeDialog(MotionDialog):
    """Preview and confirm one dated membership change for one student."""

    def __init__(
        self,
        adapter: StudentDesktopAdapter,
        master_data_adapter: MasterDataDesktopAdapter,
        student_id: str,
        parent: QDialog | None = None,
    ) -> None:
        super().__init__(parent)
        self.adapter = adapter
        self.student_id = student_id
        current = adapter.current_membership_for_student(student_id)
        master_data = master_data_adapter.view_model()
        self.current_group_name = current.group_name or "Ohne Stammgruppe"
        self.current_course_name = current.course_name or "Ohne Kurs"
        operation_date = adapter.operation_date()
        self.effective_on = QDateEdit(
            QDate(
                operation_date.year,
                operation_date.month,
                operation_date.day,
            )
        )
        self.effective_on.setCalendarPopup(True)
        self.effective_on.setAccessibleName("Stichtag des Wechsels")
        self.group_select = QComboBox()
        self.group_select.addItem("Stammgruppe beibehalten", None)
        for group in master_data.active_groups:
            self.group_select.addItem(group.name, group.item_id)
        self.course_select = QComboBox()
        self.course_select.addItem(STUDENT_DIALOG_SELECT_PLACEHOLDER, "")
        for course in master_data.active_courses:
            self.course_select.addItem(course.name, course.item_id)
        self.preview = QLabel()
        self.validation_message = InlineMessage()
        self.setWindowTitle("Zuordnung ändern")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._build()
        self._refresh_preview()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(
            DialogHeader(
                "Zuordnung ändern",
                f"Aktuell: {self.current_group_name} · {self.current_course_name}",
                "Der bisherige Zeitraum endet am Vortag des gewählten Stichtags.",
                icon_name="student-record",
            )
        )
        card = AppCard("default")
        form = QFormLayout(card)
        form.addRow("Stichtag", self.effective_on)
        form.addRow("Zielkurs", self.course_select)
        form.addRow("Neue Stammgruppe (optional)", self.group_select)
        form.addRow("Vorschau", self.preview)
        layout.addWidget(card)
        layout.addWidget(self.validation_message)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Wechsel bestätigen")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)
        self.effective_on.dateChanged.connect(self._refresh_preview)
        self.group_select.currentIndexChanged.connect(self._refresh_preview)
        self.course_select.currentIndexChanged.connect(self._refresh_preview)

    def _refresh_preview(self) -> None:
        selected_date = self.effective_on.date()
        reference_date = date(
            selected_date.year(),
            selected_date.month(),
            selected_date.day(),
        )
        try:
            source = self.adapter.current_membership_for_student(
                self.student_id,
                as_of=reference_date,
            )
        except Exception:
            self.preview.setText(
                "Die Zuordnung am gewählten Stichtag ist nicht verfügbar."
            )
            self.save_button.setEnabled(False)
            return
        if source.resolution_status is not AssignmentResolutionStatus.ENROLLED:
            self.preview.setText(
                "Am gewählten Stichtag besteht keine eindeutige Einschreibung."
            )
            self.save_button.setEnabled(False)
            return
        source_group_name = source.group_name or "Ohne Stammgruppe"
        source_course_name = source.course_name or "Ohne Kurs"
        group_name = (
            self.group_select.currentText()
            if self.group_select.currentData() is not None
            else source_group_name
        )
        course_name = (
            self.course_select.currentText()
            if self.course_select.currentData()
            else "Bitte Zielkurs wählen"
        )
        self.save_button.setEnabled(bool(self.course_select.currentData()))
        self.preview.setText(
            f"Am Stichtag: {source_group_name} · {source_course_name}. "
            f"Ab {selected_date.toString('dd.MM.yyyy')}: "
            f"{group_name} · {course_name}."
        )

    def save(self) -> None:
        course_id = str(self.course_select.currentData() or "")
        if not course_id:
            self.validation_message.set_message(
                STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE,
                tone="error",
            )
            return
        selected = self.effective_on.date()
        result = self.adapter.change_student_membership(
            self.student_id,
            effective_on=date(selected.year(), selected.month(), selected.day()),
            group_id=(
                str(self.group_select.currentData())
                if self.group_select.currentData() is not None
                else None
            ),
            course_id=course_id,
        )
        if isinstance(result, SuccessResult):
            if result.value.status is MembershipChangeStatus.NO_CHANGE:
                self.validation_message.set_message(
                    "Die gewählte Zuordnung entspricht dem aktuellen Stand.",
                    tone="info",
                )
                return
            self.accept()
            return
        self.validation_message.set_message(result.message, tone="error")


class StudentExitDialog(MotionDialog):
    """Confirm a dated exit without archiving the student."""

    def __init__(
        self,
        adapter: StudentDesktopAdapter,
        student_id: str,
        parent: QDialog | None = None,
    ) -> None:
        super().__init__(parent)
        self.adapter = adapter
        self.student_id = student_id
        operation_date = adapter.operation_date()
        self.effective_on = QDateEdit(
            QDate(
                operation_date.year,
                operation_date.month,
                operation_date.day,
            )
        )
        self.effective_on.setCalendarPopup(True)
        self.validation_message = InlineMessage()
        self.setWindowTitle("Austritt erfassen")
        layout = QVBoxLayout(self)
        layout.addWidget(
            DialogHeader(
                "Austritt erfassen",
                "Einschreibung beenden",
                "Der Austritt beendet die Zuordnung, archiviert das Kind aber nicht.",
                icon_name="student-record",
            )
        )
        form_card = AppCard("default")
        form = QFormLayout(form_card)
        form.addRow("Stichtag", self.effective_on)
        layout.addWidget(form_card)
        layout.addWidget(self.validation_message)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Austritt bestätigen"
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)

    def save(self) -> None:
        selected = self.effective_on.date()
        result = self.adapter.exit_student_from_school_year(
            self.student_id,
            effective_on=date(selected.year(), selected.month(), selected.day()),
        )
        if isinstance(result, SuccessResult):
            self.accept()
            return
        self.validation_message.set_message(result.message, tone="error")
