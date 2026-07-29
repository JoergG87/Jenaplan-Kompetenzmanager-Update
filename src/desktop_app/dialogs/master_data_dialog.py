"""Master-data name dialogs for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.dialogs.dialog_buttons import (
    DialogActionBar,
    configure_save_cancel_buttons,
)
from src.desktop_app.components import AppCard, DialogHeader, InlineMessage, SectionHeader
from src.desktop_app.motion import MotionDialog
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_GROUP_EMPTY_COURSES_MESSAGE,
    COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
    COURSE_COLOR_OPTIONS,
    COURSE_YEAR_LEVEL_REQUIRED_MESSAGE,
    MASTER_DATA_EMPTY_NAME_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    normalize_master_data_name,
    validate_course_year_level,
)


class MasterDataNameDialog(MotionDialog):
    """Collect one master-data name and optional course color."""

    def __init__(
        self,
        title: str,
        initial_name: str = "",
        *,
        include_color: bool = False,
        initial_color_hex: str = "",
        include_year_level: bool = False,
        initial_year_level: int | None = None,
        include_active: bool = False,
        initial_active: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.resize(
            500,
            340
            + (70 if include_color else 0)
            + (70 if include_year_level else 0)
            + (50 if include_active else 0),
        )
        self.name_input = QLineEdit(initial_name)
        self.name_input.setAccessibleName("Bezeichnung")
        self.include_color = include_color
        self.include_year_level = include_year_level
        self.include_active = include_active
        self.color_select = QComboBox()
        self.color_select.setAccessibleName("Kursfarbe")
        self._populate_colors(initial_color_hex)
        self.year_level_select = QComboBox()
        self.year_level_select.setAccessibleName("Kursstufe")
        self.year_level_select.addItem("Bitte auswählen", None)
        for year_level in (1, 2, 3):
            self.year_level_select.addItem(f"Stufe {year_level}", year_level)
        if initial_year_level in (1, 2, 3):
            self.year_level_select.setCurrentIndex(int(initial_year_level))
        self.active_checkbox = QCheckBox("Aktiv")
        self.active_checkbox.setAccessibleName("Stammdatensatz ist aktiv")
        self.active_checkbox.setChecked(initial_active)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                self.windowTitle(),
                "Stammdaten",
                "Die Änderung gilt nach dem Speichern in allen zugehörigen Ansichten.",
                icon_name="master-data-dialog",
            )
        )
        card = AppCard("default")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        card_layout.setSpacing(10)
        card_layout.addWidget(SectionHeader("Bezeichnung"))
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Name", self.name_input)
        if self.include_color:
            form.addRow("Farbe", self.color_select)
        if self.include_year_level:
            form.addRow("Kursstufe", self.year_level_select)
        if self.include_active:
            form.addRow("Status", self.active_checkbox)
        card_layout.addLayout(form)
        layout.addWidget(card, 1)
        self.validation_message = InlineMessage()
        self.validation_message.setAccessibleName("Validierung der Stammdaten")
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
        self.name_input.setFocus()

    def name(self) -> str:
        """Return the validated name."""
        return normalize_master_data_name(self.name_input.text())

    def color_hex(self) -> str:
        """Return the selected course color."""
        return str(self.color_select.currentData() or COURSE_COLOR_OPTIONS[0][1])

    def year_level(self) -> int:
        """Return the consciously selected final-V3 course level."""
        return validate_course_year_level(self.year_level_select.currentData())

    def is_active(self) -> bool:
        """Return the explicit master-data activity choice."""
        return self.active_checkbox.isChecked()

    def save(self) -> None:
        """Close only when the name is not empty."""
        try:
            self.name()
        except ValueError:
            self.validation_message.set_message(
                MASTER_DATA_EMPTY_NAME_MESSAGE,
                tone="error",
            )
            return
        if self.include_year_level:
            try:
                self.year_level()
            except ValueError:
                self.validation_message.set_message(
                    COURSE_YEAR_LEVEL_REQUIRED_MESSAGE,
                    tone="error",
                )
                return
        self.validation_message.set_message("")
        self.accept()

    def _populate_colors(self, initial_color_hex: str) -> None:
        for color_name, color_hex in COURSE_COLOR_OPTIONS:
            self.color_select.addItem(color_name, color_hex)
        for index in range(self.color_select.count()):
            if self.color_select.itemData(index) == initial_color_hex:
                self.color_select.setCurrentIndex(index)
                return


class CourseGroupDialog(MotionDialog):
    """Edit one persisted course-group configuration."""

    def __init__(
        self,
        course_group: CourseGroupViewModel,
        groups: tuple[MasterDataItemViewModel, ...],
        courses: tuple[MasterDataItemViewModel, ...],
        *,
        title: str = "Kursverbund bearbeiten",
    ) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(580, 520)
        self.resize(640, 650)
        self.course_group = course_group
        self.groups = groups
        self.courses = courses
        self.name_input = QLineEdit(course_group.name)
        self.name_input.setAccessibleName("Name des Kursverbunds")
        self.group_checkboxes: dict[str, QCheckBox] = {}
        self.course_checkboxes: dict[str, QCheckBox] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(
            DialogHeader(
                self.windowTitle(),
                "Stammgruppen und Kurse gemeinsam organisieren",
                "Name und Zuordnungen werden zusammen als ein Kursverbund gespeichert.",
                icon_name="master-data-dialog",
            )
        )
        name_card = AppCard("default")
        name_layout = QVBoxLayout(name_card)
        name_layout.setContentsMargins(18, 14, 18, 16)
        name_layout.addWidget(SectionHeader("Bezeichnung"))
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Name", self.name_input)
        name_layout.addLayout(form)
        layout.addWidget(name_card)
        layout.addWidget(self._checkbox_group(
            "Stammgruppen",
            self.groups,
            self.course_group.selected_group_ids,
            self.group_checkboxes,
        ))
        layout.addWidget(self._checkbox_group(
            "Kurse",
            self.courses,
            self.course_group.selected_course_ids,
            self.course_checkboxes,
            include_color=True,
        ))
        self.validation_message = InlineMessage()
        self.validation_message.setAccessibleName("Validierung des Kursverbunds")
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
        self.name_input.setFocus()

    def name(self) -> str:
        """Return the validated course-group name."""
        return normalize_master_data_name(self.name_input.text())

    def selected_group_ids(self) -> tuple[str, ...]:
        """Return selected group ids in visible order."""
        return tuple(
            item_id
            for item_id, checkbox in self.group_checkboxes.items()
            if checkbox.isChecked()
        )

    def selected_course_ids(self) -> tuple[str, ...]:
        """Return selected course ids in visible order."""
        return tuple(
            item_id
            for item_id, checkbox in self.course_checkboxes.items()
            if checkbox.isChecked()
        )

    def save(self) -> None:
        """Accept only when name, groups and courses are valid."""
        try:
            self.name()
        except ValueError:
            self.validation_message.set_message(
                MASTER_DATA_EMPTY_NAME_MESSAGE,
                tone="error",
            )
            return
        if not self.selected_group_ids():
            self.validation_message.set_message(
                COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
                tone="error",
            )
            return
        if not self.selected_course_ids():
            self.validation_message.set_message(
                COURSE_GROUP_EMPTY_COURSES_MESSAGE,
                tone="error",
            )
            return
        self.validation_message.set_message("")
        self.accept()

    def _checkbox_group(
        self,
        title: str,
        items: tuple[MasterDataItemViewModel, ...],
        selected_ids: tuple[str, ...],
        target: dict[str, QCheckBox],
        *,
        include_color: bool = False,
    ) -> AppCard:
        group_box = AppCard("soft")
        layout = QVBoxLayout(group_box)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.addWidget(SectionHeader(title))
        selected_set = set(selected_ids)
        for item in items:
            checkbox = QCheckBox(item.name)
            checkbox.setChecked(item.item_id in selected_set)
            checkbox.setAccessibleName(
                f"{title}: {item.name} dem Kursverbund zuordnen"
            )
            target[item.item_id] = checkbox
            if include_color:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                marker = QLabel("●")
                marker.setStyleSheet(f"color: {item.color_hex or '#6B7280'};")
                row_layout.addWidget(marker)
                row_layout.addWidget(checkbox)
                row_layout.addStretch(1)
                layout.addWidget(row)
            else:
                layout.addWidget(checkbox)
        return group_box
