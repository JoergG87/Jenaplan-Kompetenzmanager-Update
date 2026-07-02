"""Master-data name dialogs for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.desktop_app.view_models.master_data_view_model import (
    MASTER_DATA_EMPTY_NAME_MESSAGE,
    normalize_master_data_name,
)


class MasterDataNameDialog(QDialog):
    """Collect one master-data name with light UI validation."""

    def __init__(self, title: str, initial_name: str = "") -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.name_input = QLineEdit(initial_name)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #B00020;")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Name", self.name_input)
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

    def save(self) -> None:
        """Close only when the name is not empty."""
        try:
            self.name()
        except ValueError:
            self.error_label.setText(MASTER_DATA_EMPTY_NAME_MESSAGE)
            return
        self.accept()
