"""Shared dialog button setup for the PySide6 desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox


DIALOG_CANCEL_TEXT = "Abbrechen"
DIALOG_SAVE_TEXT = "Speichern"


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
        save_button.setDefault(True)
        save_button.setAutoDefault(True)
