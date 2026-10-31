"""Consent must stay explicit; UI receives no database authority."""
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from src.desktop_app.product_migration_dialog import (
    ProductMigrationDialog, show_product_migration_error,
)


class ProductMigrationDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_start_requires_consent_and_later_is_default(self):
        dialog = ProductMigrationDialog()
        self.assertFalse(dialog.start_button.isEnabled())
        self.assertTrue(dialog.later_button.isDefault())
        dialog._accept_consent()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)
        dialog.consent.setChecked(True)
        self.assertTrue(dialog.start_button.isEnabled())
        dialog._accept_consent()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_recovery_only_offers_existing_completion(self):
        dialog = ProductMigrationDialog(completing=True)
        self.assertEqual(dialog.start_button.text(), "Abschluss prüfen")
        self.assertFalse(dialog.start_button.isEnabled())
        dialog.reject()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_support_details_do_not_echo_arbitrary_output(self):
        details = []
        def capture(box):
            details.append(box.detailedText())
            return 0
        with patch.object(QMessageBox, "exec", capture):
            show_product_migration_error(support_code="secret=/Users/private/key")
        self.assertEqual(details, ["Supporthinweis: product_v7_maintenance_failed"])
