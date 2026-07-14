"""Focused checks for the shared productive dialog experience."""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QVBoxLayout

from src.desktop_app.components import DialogHeader
from src.desktop_app.dialogs.dialog_buttons import (
    DialogActionBar,
    configure_save_cancel_buttons,
)
from src.desktop_app.dialogs.master_data_dialog import MasterDataNameDialog
from src.desktop_app.theme import apply_app_theme


class DialogExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        apply_app_theme(cls.app)

    def test_dialog_header_exposes_title_context_and_description(self) -> None:
        header = DialogHeader(
            "Neue Beobachtung",
            "Amelie Vogel · Grashüpfer · Kurs 1",
            "Kontext, Kompetenzen und Notiz bearbeiten.",
            icon_name="observation",
        )

        self.assertEqual(header.title_label.text(), "Neue Beobachtung")
        self.assertIn("Amelie Vogel", header.context_label.text())
        self.assertFalse(header.description_label.isHidden())
        self.assertFalse(header.icon_label.pixmap().isNull())

    def test_save_cancel_actions_keep_safe_visual_order(self) -> None:
        dialog = QDialog()
        layout = QVBoxLayout(dialog)
        buttons = DialogActionBar(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        configure_save_cancel_buttons(buttons)
        layout.addWidget(buttons)
        dialog.show()
        self.app.processEvents()
        self.app.processEvents()

        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.assertIsNotNone(cancel)
        self.assertIsNotNone(save)
        self.assertLess(cancel.geometry().x(), save.geometry().x())
        self.assertTrue(save.isDefault())
        self.assertEqual(cancel.shortcut().toString(), "Esc")
        dialog.close()

    def test_small_master_data_dialog_uses_header_inline_error_and_action_bar(self) -> None:
        dialog = MasterDataNameDialog("Neue Stammgruppe")

        self.assertIsNotNone(dialog.findChild(DialogHeader))
        actions = dialog.findChild(QDialogButtonBox, "DialogActionBar")
        self.assertIsNotNone(actions)
        dialog.save()
        self.assertEqual(
            dialog.error_label.text(),
            "Bitte einen Namen eingeben.",
        )
        self.assertFalse(dialog.validation_message.isHidden())


if __name__ == "__main__":
    unittest.main()
