"""Focused settings navigation and privacy-safe preview tests."""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.view_models.backup_restore_view_model import RestorePreviewViewModel


class SettingsNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_overview_has_exactly_four_areas_and_back_returns(self) -> None:
        screen = SettingsScreen()
        self.assertEqual(
            set(screen.settings_cards),
            {"timetable", "documentation_subjects", "backup_restore", "security"},
        )
        screen.show_page("backup_restore")
        self.assertEqual(screen.current_page, "backup_restore")
        screen.show_overview()
        self.assertEqual(screen.current_page, "overview")

    def test_restore_preview_has_aggregates_only_and_requires_preparation(self) -> None:
        screen = SettingsScreen()
        preview = RestorePreviewViewModel(
            "2026-07-16T12:00:00Z", "0.1.2", "exact", 3, 8, 2, 1, 4, 5, 1,
            archive_path=__import__("pathlib").Path("/private/hidden.jkmbackup"),
        )
        screen.show_restore_preview(preview)
        text = screen.restore_preview_label.text()
        self.assertIn("Kinder: 3", text)
        self.assertNotIn("hidden.jkmbackup", text)
        self.assertTrue(screen.restore_start_button.isEnabled())

    def test_incompatible_preview_is_not_startable(self) -> None:
        screen = SettingsScreen()
        screen.show_restore_preview(RestorePreviewViewModel(
            "2026-07-16T12:00:00Z", "0.1.2", "incompatible", 0, 0, 0, 0, 0, 0, 0,
            archive_path=__import__("pathlib").Path("/private/hidden.jkmbackup"),
        ))
        self.assertFalse(screen.restore_start_button.isEnabled())
