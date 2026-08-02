"""Focused settings navigation and privacy-safe preview tests."""

from __future__ import annotations

import unittest
from datetime import date

from PySide6.QtCore import QDate, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.view_models.backup_restore_view_model import RestorePreviewViewModel


class SettingsNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_overview_has_six_areas_and_back_returns(self) -> None:
        screen = SettingsScreen()
        self.assertEqual(
            set(screen.settings_cards),
            {
                "timetable",
                "documentation_subjects",
                "backup_restore",
                "security",
                "updates",
                "school_years",
            },
        )
        screen.show_page("school_years")
        self.assertEqual(screen.current_page, "school_years")
        screen.show_overview()
        self.assertEqual(screen.current_page, "overview")

    def test_school_year_navigation_is_keyboard_operable(self) -> None:
        screen = SettingsScreen()
        card = screen.settings_cards["school_years"]

        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            screen.show_overview()
            card.setFocus()
            QTest.keyClick(card, key)
            self.assertEqual(screen.current_page, "school_years")

    def test_cursor_contract_is_reinitialized_on_stationary_detail_navigation(
        self,
    ) -> None:
        screen = SettingsScreen()
        screen.resize(900, 700)
        screen.show()
        self.app.processEvents()
        card = screen.settings_cards["school_years"]
        card_position = card.rect().center()
        global_position = card.mapToGlobal(card_position)

        QTest.mouseMove(card, card_position)
        self.assertEqual(
            card.cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )
        QTest.mouseClick(
            card,
            Qt.MouseButton.LeftButton,
            pos=card_position,
        )
        self.app.processEvents()

        detail_scroll = screen.pages.currentWidget()
        self.assertIsInstance(detail_scroll, QScrollArea)
        detail_content = detail_scroll.widget()
        self.assertEqual(
            detail_content.cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )
        self.assertTrue(
            detail_content.testAttribute(Qt.WidgetAttribute.WA_SetCursor)
        )
        self.assertEqual(
            detail_scroll.viewport().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )
        widget_under_stationary_pointer = QApplication.widgetAt(global_position)
        self.assertIsNotNone(widget_under_stationary_pointer)
        self.assertTrue(
            detail_content is widget_under_stationary_pointer
            or detail_content.isAncestorOf(widget_under_stationary_pointer)
        )
        self.assertEqual(
            widget_under_stationary_pointer.cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

        title = next(
            label
            for label in detail_content.findChildren(QLabel)
            if label.text() == "Schuljahre"
        )
        self.assertEqual(title.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertEqual(
            screen.school_year_transition_button.cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )
        self.assertIsNone(QApplication.overrideCursor())
        screen.close()

    def test_cursor_contract_survives_back_other_detail_and_app_activation(
        self,
    ) -> None:
        screen = SettingsScreen()
        accessible_names = {
            key: card.accessibleName()
            for key, card in screen.settings_cards.items()
        }

        for key in ("school_years", "documentation_subjects"):
            screen.show_page(key)
            detail_scroll = screen.pages.currentWidget()
            self.assertEqual(
                detail_scroll.widget().cursor().shape(),
                Qt.CursorShape.ArrowCursor,
            )
            self.assertEqual(
                screen.detail_back_buttons[key].cursor().shape(),
                Qt.CursorShape.PointingHandCursor,
            )

        QApplication.sendEvent(
            screen,
            QEvent(QEvent.Type.ApplicationDeactivate),
        )
        QApplication.sendEvent(
            screen,
            QEvent(QEvent.Type.ApplicationActivate),
        )
        self.assertEqual(
            screen.pages.currentWidget().widget().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )
        self.assertIsNone(QApplication.overrideCursor())

        screen.show_overview()
        overview_scroll = screen.pages.currentWidget()
        self.assertEqual(
            overview_scroll.widget().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )
        self.assertEqual(
            screen.settings_cards["school_years"].cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )
        self.assertEqual(
            accessible_names,
            {
                key: card.accessibleName()
                for key, card in screen.settings_cards.items()
            },
        )

    def test_school_year_page_shows_current_year_and_emits_accessible_input(
        self,
    ) -> None:
        screen = SettingsScreen()
        screen.set_current_school_year(
            "2025/26",
            date(2025, 8, 1),
            date(2026, 7, 31),
        )
        screen.show_page("school_years")
        screen.new_school_year_label.setText("2026/27")
        screen.new_school_year_start.setDate(QDate(2026, 8, 1))
        screen.new_school_year_end.setDate(QDate(2027, 7, 31))
        requests: list[tuple[str, date, date]] = []
        screen.school_year_transition_preview_requested.connect(
            lambda label, start, end: requests.append((label, start, end))
        )

        QTest.mouseClick(
            screen.school_year_transition_button,
            Qt.MouseButton.LeftButton,
        )

        self.assertIn("2025/26", screen.current_school_year_label.text())
        self.assertEqual(
            requests,
            [("2026/27", date(2026, 8, 1), date(2027, 7, 31))],
        )
        self.assertTrue(screen.new_school_year_label.accessibleName())
        self.assertTrue(screen.new_school_year_start.accessibleName())
        self.assertTrue(screen.new_school_year_end.accessibleName())
        self.assertIn(
            "flüchtige Vorschau",
            screen.school_year_transition_button.accessibleName(),
        )

    def test_target_period_default_is_calendar_based_after_leap_year(
        self,
    ) -> None:
        screen = SettingsScreen()

        screen.set_current_school_year(
            "2023/24",
            date(2023, 8, 1),
            date(2024, 7, 31),
        )

        self.assertEqual(
            screen.new_school_year_start.date().toPython(),
            date(2024, 8, 1),
        )
        self.assertEqual(
            screen.new_school_year_end.date().toPython(),
            date(2025, 7, 31),
        )

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
