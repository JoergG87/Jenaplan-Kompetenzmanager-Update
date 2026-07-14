"""Shared dialog button setup for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QDialogButtonBox, QHBoxLayout

from src.desktop_app.components import configure_button


DIALOG_CANCEL_TEXT = "Abbrechen"
DIALOG_SAVE_TEXT = "Speichern"


class DialogActionBar(QDialogButtonBox):
    """Button box with an explicit safe-left, primary-right visual order."""

    def __init__(self, buttons: QDialogButtonBox.StandardButton) -> None:
        super().__init__(buttons)
        self.setObjectName("DialogActionBar")

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._order_actions()

    def _order_actions(self) -> None:
        cancel_button = self.button(QDialogButtonBox.StandardButton.Cancel)
        save_button = self.button(QDialogButtonBox.StandardButton.Save)
        button_layout = self.layout()
        if (
            cancel_button is None
            or save_button is None
            or not isinstance(button_layout, QHBoxLayout)
        ):
            return
        while button_layout.count():
            button_layout.takeAt(0)
        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)


def configure_save_cancel_buttons(buttons: QDialogButtonBox) -> None:
    """Apply consistent labels and default behavior to save/cancel dialogs."""
    if not buttons.objectName():
        buttons.setObjectName("DialogActionBar")
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
    if cancel_button is not None:
        cancel_button.setText(DIALOG_CANCEL_TEXT)
        configure_button(cancel_button, "secondary", "Dialog abbrechen")
        cancel_button.setAutoDefault(False)
        cancel_button.setShortcut("Esc")
    if save_button is not None:
        save_button.setText(DIALOG_SAVE_TEXT)
        configure_button(save_button, "primary", "Änderungen speichern")
        save_button.setDefault(True)
        save_button.setAutoDefault(True)
    if isinstance(buttons, DialogActionBar):
        buttons._order_actions()
