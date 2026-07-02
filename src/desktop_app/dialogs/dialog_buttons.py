"""Shared dialog button setup for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox


DIALOG_CANCEL_TEXT = "Abbrechen"
DIALOG_SAVE_TEXT = "Speichern"
DIALOG_PRIMARY_BUTTON_STYLE = """
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1D4ED8;
}
QPushButton:pressed {
    background-color: #1E40AF;
}
QPushButton:disabled {
    background-color: #93C5FD;
    border-color: #93C5FD;
}
"""


def configure_save_cancel_buttons(buttons: QDialogButtonBox) -> None:
    """Apply consistent labels and default behavior to save/cancel dialogs."""
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
    if cancel_button is not None:
        cancel_button.setText(DIALOG_CANCEL_TEXT)
        cancel_button.setAutoDefault(False)
        cancel_button.setShortcut("Esc")
    if save_button is not None:
        save_button.setText(DIALOG_SAVE_TEXT)
        save_button.setStyleSheet(DIALOG_PRIMARY_BUTTON_STYLE)
        save_button.setDefault(True)
        save_button.setAutoDefault(True)
