"""Master-data name dialogs for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.dialogs.dialog_buttons import configure_save_cancel_buttons
from src.desktop_app.view_models.master_data_view_model import (
    COURSE_GROUP_EMPTY_COURSES_MESSAGE,
    COURSE_GROUP_EMPTY_GROUPS_MESSAGE,
    COURSE_COLOR_OPTIONS,
    MASTER_DATA_EMPTY_NAME_MESSAGE,
    CourseGroupViewModel,
    MasterDataItemViewModel,
    normalize_master_data_name,
)
from src.desktop_app.theme import set_label_style


class MasterDataNameDialog(QDialog):
    """Collect one master-data name and optional course color."""

    def __init__(
        self,
        title: str,
        initial_name: str = "",
        *,
        include_color: bool = False,
        initial_color_hex: str = "",
    ) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.name_input = QLineEdit(initial_name)
        self.include_color = include_color
        self.color_select = QComboBox()
        self._populate_colors(initial_color_hex)
        self.error_label = QLabel("")
        set_label_style(self.error_label, "error")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Name", self.name_input)
        if self.include_color:
            form.addRow("Farbe", self.color_select)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)

    def name(self) -> str:
        """Return the validated name."""
        return normalize_master_data_name(self.name_input.text())

    def color_hex(self) -> str:
        """Return the selected course color."""
        return str(self.color_select.currentData() or COURSE_COLOR_OPTIONS[0][1])

    def save(self) -> None:
        """Close only when the name is not empty."""
        try:
            self.name()
        except ValueError:
            self.error_label.setText(MASTER_DATA_EMPTY_NAME_MESSAGE)
            return
        self.accept()

    def _populate_colors(self, initial_color_hex: str) -> None:
        for color_name, color_hex in COURSE_COLOR_OPTIONS:
            self.color_select.addItem(color_name, color_hex)
        for index in range(self.color_select.count()):
            if self.color_select.itemData(index) == initial_color_hex:
                self.color_select.setCurrentIndex(index)
                return


class CourseGroupDialog(QDialog):
    """Edit one session-local course-group configuration."""

    def __init__(
        self,
        course_group: CourseGroupViewModel,
        groups: tuple[MasterDataItemViewModel, ...],
        courses: tuple[MasterDataItemViewModel, ...],
    ) -> None:
        super().__init__()
        self.setWindowTitle("Kursverbund bearbeiten")
        self.setModal(True)
        self.course_group = course_group
        self.groups = groups
        self.courses = courses
        self.name_input = QLineEdit(course_group.name)
        self.group_checkboxes: dict[str, QCheckBox] = {}
        self.course_checkboxes: dict[str, QCheckBox] = {}
        self.error_label = QLabel("")
        set_label_style(self.error_label, "error")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Name", self.name_input)
        layout.addLayout(form)
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
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.save)
        layout.addWidget(buttons)

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
            self.error_label.setText(MASTER_DATA_EMPTY_NAME_MESSAGE)
            return
        if not self.selected_group_ids():
            self.error_label.setText(COURSE_GROUP_EMPTY_GROUPS_MESSAGE)
            return
        if not self.selected_course_ids():
            self.error_label.setText(COURSE_GROUP_EMPTY_COURSES_MESSAGE)
            return
        self.accept()

    def _checkbox_group(
        self,
        title: str,
        items: tuple[MasterDataItemViewModel, ...],
        selected_ids: tuple[str, ...],
        target: dict[str, QCheckBox],
        *,
        include_color: bool = False,
    ) -> QGroupBox:
        group_box = QGroupBox(title)
        layout = QVBoxLayout(group_box)
        selected_set = set(selected_ids)
        for item in items:
            checkbox = QCheckBox(item.name)
            checkbox.setChecked(item.item_id in selected_set)
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
