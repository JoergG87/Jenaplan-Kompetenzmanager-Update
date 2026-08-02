"""Qt signal-path regression tests for the shell sidebar."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QEvent, QSize, Qt
from PySide6.QtGui import QEnterEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView, QApplication, QListWidgetItem

from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.shell import AppShell, _SidebarNavigationList


class SidebarCursorComponentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.navigation = _SidebarNavigationList()
        self.navigation.setFixedSize(180, 110)
        self.navigation.setSpacing(8)
        self.navigation.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.items: dict[str, QListWidgetItem] = {}
        for key in (
            "padding-1",
            "padding-2",
            "active-1",
            "disabled",
            "active-2",
            "padding-3",
            "padding-4",
        ):
            item = QListWidgetItem(key)
            item.setSizeHint(QSize(150, 30))
            if key.startswith("active"):
                item.setData(Qt.ItemDataRole.UserRole, "dashboard")
            elif key == "disabled":
                item.setData(Qt.ItemDataRole.UserRole, "students")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.navigation.addItem(item)
            self.items[key] = item
        self.navigation.show()
        self.app.processEvents()
        self.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
        self.position = self.navigation.viewport().rect().center()
        QApplication.sendEvent(
            self.navigation.viewport(),
            QEvent(QEvent.Type.Leave),
        )

    def tearDown(self) -> None:
        self.navigation.close()
        self.app.processEvents()
        self.assertIsNone(QApplication.overrideCursor())

    def _align_item(self, key: str) -> None:
        item = self.items[key]
        rect = self.navigation.visualItemRect(item)
        scrollbar = self.navigation.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + rect.center().y() - self.position.y())
        self.app.processEvents()
        self.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
        self.navigation._refresh_cursor()
        self.assertIs(self.navigation.itemAt(self.position), item)

    def _align_empty_gap_after(self, key: str) -> None:
        rect = self.navigation.visualItemRect(self.items[key])
        gap_y = rect.bottom() + 1 + self.navigation.spacing() // 2
        scrollbar = self.navigation.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + gap_y - self.position.y())
        self.app.processEvents()
        self.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
        self.navigation._refresh_cursor()
        self.assertIsNone(self.navigation.itemAt(self.position))

    def _move_pointer_to_position(self) -> None:
        viewport = self.navigation.viewport()
        local_position = QPointF(self.position)
        global_position = QPointF(viewport.mapToGlobal(self.position))
        QApplication.sendEvent(
            viewport,
            QEnterEvent(local_position, local_position, global_position),
        )
        QApplication.sendEvent(
            viewport,
            QMouseEvent(
                QEvent.Type.MouseMove,
                local_position,
                global_position,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )
        self.app.processEvents()
        self.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
        self.navigation._refresh_cursor()
        self.assertEqual(self.navigation._pointer_position, self.position)

    def test_scroll_without_prior_pointer_state_keeps_arrow_cursor(self) -> None:
        self.assertIsNone(self.navigation._pointer_position)
        self._align_item("active-1")
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

    def test_stationary_pointer_scrolls_from_empty_space_to_active_item(self) -> None:
        self._align_empty_gap_after("active-1")
        self._move_pointer_to_position()
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

        self._align_item("active-2")
        self.assertEqual(self.navigation._pointer_position, self.position)
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )

    def test_stationary_pointer_scrolls_from_active_item_to_empty_space(self) -> None:
        self._align_item("active-1")
        self._move_pointer_to_position()
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )

        self._align_empty_gap_after("active-2")
        self.assertEqual(self.navigation._pointer_position, self.position)
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

    def test_stationary_pointer_scrolls_from_active_to_disabled_item(self) -> None:
        self._align_item("active-1")
        self._move_pointer_to_position()
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )

        self._align_item("disabled")
        self.assertEqual(self.navigation._pointer_position, self.position)
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

    def test_leave_and_reenter_follow_the_real_pointer_path(self) -> None:
        self._align_item("active-1")
        self._move_pointer_to_position()
        QApplication.sendEvent(
            self.navigation.viewport(),
            QEvent(QEvent.Type.Leave),
        )
        self.assertIsNone(self.navigation._pointer_position)
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

        self._move_pointer_to_position()
        self.assertEqual(
            self.navigation.viewport().cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )


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
        self.shell.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
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

    def _move_to_item(self, key: str) -> None:
        item = self._item(key)
        self._send_pointer_move(self.shell.navigation.visualItemRect(item).center())

    def _send_pointer_move(self, position: QPoint) -> None:
        viewport = self.shell.navigation.viewport()
        local_position = QPointF(position)
        global_position = QPointF(viewport.mapToGlobal(position))
        QApplication.sendEvent(
            viewport,
            QEnterEvent(local_position, local_position, global_position),
        )
        QApplication.sendEvent(
            viewport,
            QMouseEvent(
                QEvent.Type.MouseMove,
                local_position,
                global_position,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )
        self.app.processEvents()
        self.shell.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
        self.shell.navigation._refresh_cursor()

    def _move_to_empty_space(self) -> QPoint:
        viewport = self.shell.navigation.viewport()
        position = QPoint(viewport.width() - 2, viewport.height() - 2)
        self.assertIsNone(self.shell.navigation.itemAt(position))
        self._send_pointer_move(position)
        return position

    def test_cursor_tracks_only_activatable_navigation_items(self) -> None:
        viewport = self.shell.navigation.viewport()

        self._move_to_item("dashboard")
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.PointingHandCursor)

        self._move_to_empty_space()
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.ArrowCursor)

        self._move_to_item("students")
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.PointingHandCursor)
        self._move_to_item("dashboard")
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.PointingHandCursor)

    def test_cursor_stays_standard_over_disabled_item_and_section(self) -> None:
        viewport = self.shell.navigation.viewport()
        disabled_item = self._item("students")
        disabled_item.setFlags(disabled_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        QTest.mouseMove(viewport, self.shell.navigation.visualItemRect(disabled_item).center())
        self.app.processEvents()
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.ArrowCursor)

        section_item = self.shell.navigation.item(0)
        self.assertEqual(section_item.flags(), Qt.ItemFlag.NoItemFlags)
        QTest.mouseMove(viewport, self.shell.navigation.visualItemRect(section_item).center())
        self.app.processEvents()
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.ArrowCursor)

    def test_cursor_resets_on_leave_scroll_and_navigation_refresh(self) -> None:
        viewport = self.shell.navigation.viewport()
        self._move_to_item("dashboard")
        QApplication.sendEvent(viewport, QEvent(QEvent.Type.Leave))
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.ArrowCursor)

        self._move_to_empty_space()
        self.shell.navigation.model().layoutChanged.emit()
        self.app.processEvents()
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.ArrowCursor)

        self.shell.navigation.setFixedHeight(110)
        self.app.processEvents()
        self.shell.navigation.scrollToItem(self._item("settings"))
        self.app.processEvents()
        self._move_to_item("settings")
        position = self.shell.navigation._pointer_position
        self.assertIsNotNone(position)
        self.assertTrue(viewport.rect().contains(position))
        self.shell.navigation.scrollToItem(self._item("dashboard"))
        self.app.processEvents()
        self.assertEqual(self.shell.navigation._pointer_position, position)
        self.shell.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationActive
        )
        self.shell.navigation._refresh_cursor()
        item = self.shell.navigation.itemAt(position) if position is not None else None
        expected = (
            Qt.CursorShape.PointingHandCursor
            if item is not None and item.data(Qt.ItemDataRole.UserRole)
            else Qt.CursorShape.ArrowCursor
        )
        self.assertEqual(
            viewport.cursor().shape(),
            expected,
            msg=(
                f"position={position}, item_key="
                f"{item.data(Qt.ItemDataRole.UserRole) if item else None}, "
                f"flags={item.flags() if item else None}, "
                f"application_active={self.shell.navigation._application_active}, "
                f"same_viewport={viewport is self.shell.navigation.viewport()}"
            ),
        )

        self._move_to_item("dashboard")
        self.shell.navigation._application_state_changed(
            Qt.ApplicationState.ApplicationInactive
        )
        self.assertEqual(viewport.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertIsNone(QApplication.overrideCursor())

    def test_cursor_change_does_not_alter_navigation_or_accessibility(self) -> None:
        accessible_names = (
            self.shell.navigation.accessibleName(),
            self.shell.navigation.accessibleDescription(),
            tuple(
                self.shell.navigation.item(row).data(Qt.ItemDataRole.AccessibleTextRole)
                for row in range(self.shell.navigation.count())
            ),
        )
        self._move_to_item("students")
        self._click("students")
        self.assertIs(self.shell.stack.currentWidget(), self.shell.students_workspace)
        self.assertEqual(
            accessible_names,
            (
                self.shell.navigation.accessibleName(),
                self.shell.navigation.accessibleDescription(),
                tuple(
                    self.shell.navigation.item(row).data(
                        Qt.ItemDataRole.AccessibleTextRole
                    )
                    for row in range(self.shell.navigation.count())
                ),
            ),
        )

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
