"""Compact editor for one timetable entry."""

from __future__ import annotations

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTimeEdit,
    QVBoxLayout,
)

from src.desktop_app.dialogs.dialog_buttons import (
    DialogActionBar,
    configure_save_cancel_buttons,
)

from src.application.commands.timetable import SaveTimetableEntryCommand
from src.desktop_app.components import AppCard, DialogHeader, SectionHeader
from src.desktop_app.view_models.timetable_view_model import (
    TARGET_TYPE_LABELS,
    WEEKDAY_LABELS,
    TimetableEntryViewModel,
    TimetableWeekViewModel,
)


class TimetableEntryDialog(QDialog):
    """Collect timetable values without business or persistence logic."""

    def __init__(
        self,
        week: TimetableWeekViewModel,
        *,
        weekday: int,
        entry: TimetableEntryViewModel | None = None,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.week = week
        self.entry = entry
        self.setWindowTitle("Stundenplaneintrag bearbeiten" if entry else "Stunde anlegen")
        self.setMinimumWidth(520)
        self.resize(540, 680)
        self._build(weekday)
        if entry is not None:
            self._set_entry(entry)

    def command(self) -> SaveTimetableEntryCommand:
        """Build the application command from current widget values."""
        return SaveTimetableEntryCommand(
            self.entry.timetable_entry_id if self.entry else "",
            int(self.weekday_combo.currentData()),
            self.start_time.time().toString("HH:mm"),
            self.end_time.time().toString("HH:mm"),
            str(self.subject_combo.currentData()),
            str(self.target_type_combo.currentData()),
            str(self.target_combo.currentData()),
            self.room_input.text(),
            self.active_checkbox.isChecked(),
            self.entry.sort_order if self.entry else 0,
        )

    def _build(self, weekday: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                self.windowTitle(),
                "Wochenstundenplan",
                "Zeit, Fach und Unterrichtsziel für diesen Eintrag festlegen.",
                icon_name="timetable-dialog",
            )
        )
        card = AppCard("default")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        card_layout.setSpacing(10)
        card_layout.addWidget(SectionHeader("Stunde und Zuordnung"))
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setVerticalSpacing(8)

        self.weekday_combo = QComboBox()
        for value, label in WEEKDAY_LABELS.items():
            self.weekday_combo.addItem(label, value)
        self.weekday_combo.setCurrentIndex(max(0, weekday - 1))
        form.addRow("Wochentag", self.weekday_combo)

        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        self.end_time = QTimeEdit(QTime(8, 45))
        self.end_time.setDisplayFormat("HH:mm")
        form.addRow("Beginn", self.start_time)
        form.addRow("Ende", self.end_time)

        self.subject_combo = QComboBox()
        for option in self.week.subjects:
            self.subject_combo.addItem(option.label, option.item_id)
        form.addRow("Fach", self.subject_combo)

        self.target_type_combo = QComboBox()
        for target_type, label in TARGET_TYPE_LABELS.items():
            self.target_type_combo.addItem(label, target_type)
        self.target_type_combo.currentIndexChanged.connect(self._populate_targets)
        form.addRow("Zielart", self.target_type_combo)

        self.target_combo = QComboBox()
        form.addRow("Ziel", self.target_combo)
        self._populate_targets()

        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("optional")
        form.addRow("Raum/Ort", self.room_input)

        self.active_checkbox = QCheckBox("Eintrag aktiv")
        self.active_checkbox.setChecked(True)
        form.addRow("", self.active_checkbox)
        card_layout.addLayout(form)
        layout.addWidget(card, 1)

        buttons = DialogActionBar(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.weekday_combo.setFocus()

    def _populate_targets(self) -> None:
        selected_id = self.target_combo.currentData() if hasattr(self, "target_combo") else None
        if not hasattr(self, "target_combo"):
            return
        self.target_combo.clear()
        target_type = str(self.target_type_combo.currentData())
        for option in self.week.targets_by_type.get(target_type, ()):
            self.target_combo.addItem(option.label, option.item_id)
        index = self.target_combo.findData(selected_id)
        if index >= 0:
            self.target_combo.setCurrentIndex(index)

    def _set_entry(self, entry: TimetableEntryViewModel) -> None:
        self.weekday_combo.setCurrentIndex(self.weekday_combo.findData(entry.weekday))
        self.start_time.setTime(QTime.fromString(entry.start_time, "HH:mm"))
        self.end_time.setTime(QTime.fromString(entry.end_time, "HH:mm"))
        self.subject_combo.setCurrentIndex(self.subject_combo.findData(entry.subject_id))
        self.target_type_combo.setCurrentIndex(
            self.target_type_combo.findData(entry.target_type)
        )
        self._populate_targets()
        self.target_combo.setCurrentIndex(self.target_combo.findData(entry.target_id))
        self.room_input.setText(entry.room)
        self.active_checkbox.setChecked(entry.active)
