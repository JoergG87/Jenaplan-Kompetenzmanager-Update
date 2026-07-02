"""Master-data name dialogs for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.desktop_app.view_models.master_data_view_model import (
    COURSE_COLOR_OPTIONS,
    MASTER_DATA_EMPTY_NAME_MESSAGE,
    normalize_master_data_name,
)


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
        self.error_label.setStyleSheet("color: #B00020;")
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
