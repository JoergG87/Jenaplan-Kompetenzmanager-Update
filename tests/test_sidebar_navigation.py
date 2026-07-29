"""Qt signal-path regression tests for the shell sidebar."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.shell import AppShell


class SidebarNavigationSignalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "sidebar.sqlite"
        database = SQLiteDatabase(database_path)
        database.initialize_schema()
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO school_years(
                    school_year_id, label, start_date, end_date,
                    status, created_at, closed_at
                ) VALUES (
                    'SY-TEST-2025-26', '2025/26', '2025-08-01', '2026-07-31',
                    'current', '2025-07-01T08:00:00+00:00', NULL
                )
                """
            )
        self.shell = AppShell(database_path)
        self.shell.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.shell.close()
        self.app.processEvents()
        self.temp_dir.cleanup()

    def _item(self, key: str):
        return next(
            self.shell.navigation.item(row)
            for row in range(self.shell.navigation.count())
            if self.shell.navigation.item(row).data(Qt.ItemDataRole.UserRole) == key
        )

    def _click(self, key: str) -> None:
        item = self._item(key)
        QTest.mouseClick(
            self.shell.navigation.viewport(),
            Qt.MouseButton.LeftButton,
            pos=self.shell.navigation.visualItemRect(item).center(),
        )
        self.app.processEvents()

    def test_mouse_click_to_other_entry_dispatches_students_once(self) -> None:
        signals: list[str] = []
        self.shell.navigation.currentRowChanged.connect(
            lambda _row: signals.append("row_changed")
        )
        self.shell.navigation.itemClicked.connect(lambda _item: signals.append("clicked"))
        with patch.object(
            self.shell, "refresh_students", wraps=self.shell.refresh_students
        ) as refresh_students, patch.object(
            self.shell.students_workspace,
            "show_section",
            wraps=self.shell.students_workspace.show_section,
        ) as show_section:
            self._click("students")
            self.app.processEvents()

        self.assertEqual(signals, ["row_changed", "clicked"])
        self.assertEqual(refresh_students.call_count, 1)
        self.assertEqual(show_section.call_count, 1)
        self.assertIs(self.shell.stack.currentWidget(), self.shell.students_workspace)

    def test_mouse_click_on_active_entry_dispatches_once_per_click(self) -> None:
        self._click("students")
        with patch.object(
            self.shell, "refresh_students", wraps=self.shell.refresh_students
        ) as refresh_students, patch.object(
            self.shell.students_workspace,
            "show_section",
            wraps=self.shell.students_workspace.show_section,
        ) as show_section:
            self._click("students")
            self._click("students")
            self.app.processEvents()

        self.assertEqual(refresh_students.call_count, 2)
        self.assertEqual(show_section.call_count, 2)

    def test_keyboard_change_dispatches_students_once(self) -> None:
        self.shell._show_screen("dashboard")
        self.shell._select_navigation("dashboard")
        self.shell.navigation.setFocus()
        with patch.object(
            self.shell, "refresh_students", wraps=self.shell.refresh_students
        ) as refresh_students, patch.object(
            self.shell.students_workspace,
            "show_section",
            wraps=self.shell.students_workspace.show_section,
        ) as show_section:
            QTest.keyClick(self.shell.navigation, Qt.Key.Key_Down)
            self.app.processEvents()
            self.app.processEvents()

        self.assertEqual(self.shell.navigation.currentItem().data(Qt.ItemDataRole.UserRole), "students")
        self.assertEqual(refresh_students.call_count, 1)
        self.assertEqual(show_section.call_count, 1)

    def test_programmatic_startup_selection_has_no_navigation_dispatch(self) -> None:
        self.assertEqual(
            self.shell.navigation.currentItem().data(Qt.ItemDataRole.UserRole),
            "dashboard",
        )
        with patch.object(
            self.shell, "refresh_students", wraps=self.shell.refresh_students
        ) as refresh_students:
            self.app.processEvents()
            self.app.processEvents()

        self.assertEqual(refresh_students.call_count, 0)

    def test_programmatic_selection_dispatches_once(self) -> None:
        with patch.object(
            self.shell, "refresh_students", wraps=self.shell.refresh_students
        ) as refresh_students:
            self.shell.navigation.setCurrentRow(
                self.shell.navigation.row(self._item("students"))
            )
            self.app.processEvents()
            self.app.processEvents()

        self.assertEqual(refresh_students.call_count, 1)

    def test_fast_switches_between_entries_do_not_duplicate_students_refresh(self) -> None:
        with patch.object(
            self.shell, "refresh_students", wraps=self.shell.refresh_students
        ) as refresh_students:
            self._click("students")
            self._click("dashboard")
            self._click("students")
            self.app.processEvents()

        self.assertEqual(refresh_students.call_count, 2)
