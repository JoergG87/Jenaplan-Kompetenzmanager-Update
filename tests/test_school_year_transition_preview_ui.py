"""Focused UI checks for the read-only SJ-3B.1 preview dialog."""

from __future__ import annotations

import os
import sqlite3
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
)

from src.application.school_year_transition_preview import (
    SchoolYearTransitionPreviewProjector,
    SchoolYearTransitionPreviewService,
)
from src.core.school_year import (
    SchoolYear,
    SchoolYearStatus,
    StudentAssignmentStatus,
    V3Student,
)
from src.core.school_year_transition import (
    PlannedSchoolYear,
    SchoolYearTransitionCourse,
    SchoolYearTransitionGroup,
    SchoolYearTransitionMembership,
    SchoolYearTransitionPreviewSources,
)
from src.desktop_app.dialogs.school_year_transition_preview_dialog import (
    SchoolYearTransitionPreviewDialog,
)
from tests.helpers.synthetic_v3 import create_synthetic_v3_database


CURRENT = SchoolYear(
    "SY-2025",
    "2025/26",
    date(2025, 8, 1),
    date(2026, 7, 31),
    SchoolYearStatus.CURRENT,
)
PLANNED = PlannedSchoolYear(
    "2026/27",
    date(2026, 8, 1),
    date(2027, 7, 31),
)


def _student(
    student_id: str,
    *,
    archived: bool = False,
) -> V3Student:
    from datetime import datetime

    timestamp = datetime(2026, 1, 1, 12, 0)
    return V3Student(
        student_id=student_id,
        first_name="Test",
        last_name=student_id,
        notes="",
        active=not archived,
        created_at=timestamp,
        updated_at=timestamp,
        archived_at=timestamp if archived else None,
    )


def _membership(
    student_id: str,
    course_id: str,
    *,
    status: StudentAssignmentStatus = StudentAssignmentStatus.ENROLLED,
) -> SchoolYearTransitionMembership:
    return SchoolYearTransitionMembership(
        student_id=student_id,
        school_year_id=CURRENT.school_year_id,
        group_id="G-A" if status is StudentAssignmentStatus.ENROLLED else None,
        group_name="Gruppe A" if status is StudentAssignmentStatus.ENROLLED else None,
        course_id=course_id if status is StudentAssignmentStatus.ENROLLED else None,
        course_name=(
            f"Kurs {course_id[-1]}"
            if status is StudentAssignmentStatus.ENROLLED
            else None
        ),
        assignment_status=status,
    )


def _sources(
    *,
    students: tuple[V3Student, ...] = (),
    memberships: tuple[SchoolYearTransitionMembership, ...] = (),
    courses: tuple[SchoolYearTransitionCourse, ...] | None = None,
) -> SchoolYearTransitionPreviewSources:
    return SchoolYearTransitionPreviewSources(
        school_years=(CURRENT,),
        students=students,
        memberships=memberships,
        courses=(
            courses
            if courses is not None
            else (
                SchoolYearTransitionCourse("C-1", "Kurs 1", True, 1),
                SchoolYearTransitionCourse("C-2", "Kurs 2", True, 2),
                SchoolYearTransitionCourse("C-3", "Kurs 3", True, 3),
            )
        ),
        groups=(SchoolYearTransitionGroup("G-A", "Gruppe A", True),),
    )


def _preview(
    sources: SchoolYearTransitionPreviewSources,
):
    return SchoolYearTransitionPreviewProjector().project(
        planned_school_year=PLANNED,
        sources=sources,
    )


class SchoolYearTransitionPreviewUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, SchoolYearTransitionPreviewDialog):
                widget.close()

    def test_empty_preview_is_complete_and_has_no_rows(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_preview(_sources()))

        self.assertEqual(dialog.view_model.status_label, "Vorschau vollständig")
        self.assertEqual(dialog.table.rowCount(), 0)
        self.assertEqual(dialog.summary_labels["Kinder gesamt"].text(), "0")

    def test_complete_preview_shows_counts_and_stable_item_order(self) -> None:
        sources = _sources(
            students=(_student("S-2"), _student("S-1")),
            memberships=(
                _membership("S-2", "C-2"),
                _membership("S-1", "C-1"),
            ),
        )
        dialog = SchoolYearTransitionPreviewDialog(_preview(sources))

        self.assertEqual(dialog.view_model.status_label, "Vorschau vollständig")
        self.assertEqual(dialog.table.item(0, 0).text(), "S-1")
        self.assertEqual(dialog.table.item(1, 0).text(), "S-2")
        self.assertEqual(dialog.summary_labels["Wechsel 1 → 2"].text(), "1")
        self.assertEqual(dialog.summary_labels["Wechsel 2 → 3"].text(), "1")

    def test_course_three_is_visibly_unresolved_without_color_dependency(self) -> None:
        sources = _sources(
            students=(_student("S-3"),),
            memberships=(_membership("S-3", "C-3"),),
        )
        dialog = SchoolYearTransitionPreviewDialog(_preview(sources))

        self.assertEqual(dialog.table.item(0, 6).text(), "Ungelöst")
        self.assertIn("Kursstufe 3", dialog.table.item(0, 7).text())
        self.assertEqual(
            dialog.table.item(0, 6).data(Qt.ItemDataRole.UserRole),
            "unresolved",
        )

    def test_multiple_warnings_are_all_visible(self) -> None:
        sources = _sources(
            students=(_student("S-X", archived=True),),
            memberships=(),
        )
        dialog = SchoolYearTransitionPreviewDialog(_preview(sources))

        warnings = dialog.table.item(0, 7).text()
        self.assertIn("archiviert", warnings)
        self.assertIn("Zuordnung fehlt", warnings)

    def test_archived_and_exited_children_remain_visible(self) -> None:
        sources = _sources(
            students=(_student("S-A", archived=True), _student("S-E")),
            memberships=(
                _membership(
                    "S-E",
                    "C-1",
                    status=StudentAssignmentStatus.EXITED,
                ),
            ),
        )
        dialog = SchoolYearTransitionPreviewDialog(_preview(sources))

        self.assertEqual(
            tuple(dialog.table.item(row, 0).text() for row in range(2)),
            ("S-A", "S-E"),
        )
        self.assertIn("archiviert", dialog.table.item(0, 7).text())
        self.assertIn("ausgeschieden", dialog.table.item(1, 7).text())

    def test_every_preview_item_is_shown_exactly_once(self) -> None:
        students = tuple(_student(f"S-{number:02}") for number in range(18, 0, -1))
        memberships = tuple(
            _membership(student.student_id, "C-1")
            for student in students
        )
        preview = _preview(_sources(students=students, memberships=memberships))
        dialog = SchoolYearTransitionPreviewDialog(preview)

        visible_ids = tuple(
            dialog.table.item(row, 0).text()
            for row in range(dialog.table.rowCount())
        )
        self.assertEqual(visible_ids, tuple(item.student_id for item in preview.items))
        self.assertEqual(len(visible_ids), len(set(visible_ids)))

    def test_view_model_preserves_a_caller_supplied_item_order(self) -> None:
        preview = _preview(
            _sources(
                students=(_student("S-1"), _student("S-2"), _student("S-3")),
                memberships=(
                    _membership("S-1", "C-1"),
                    _membership("S-2", "C-1"),
                    _membership("S-3", "C-1"),
                ),
            )
        )
        reordered = replace(
            preview,
            items=(preview.items[2], preview.items[0], preview.items[1]),
        )
        dialog = SchoolYearTransitionPreviewDialog(reordered)

        self.assertEqual(
            tuple(
                dialog.table.item(row, 0).text()
                for row in range(dialog.table.rowCount())
            ),
            ("S-3", "S-1", "S-2"),
        )

    def test_small_window_keeps_horizontal_and_vertical_scrolling(self) -> None:
        students = tuple(_student(f"S-{number:02}") for number in range(20))
        memberships = tuple(
            _membership(student.student_id, "C-1")
            for student in students
        )
        dialog = SchoolYearTransitionPreviewDialog(
            _preview(_sources(students=students, memberships=memberships))
        )
        dialog.resize(520, 360)
        dialog.show()
        self.app.processEvents()

        self.assertGreater(dialog.table.horizontalScrollBar().maximum(), 0)
        self.assertGreater(dialog.table.verticalScrollBar().maximum(), 0)
        self.assertTrue(dialog.table.horizontalScrollBar().isVisible())
        self.assertTrue(dialog.table.verticalScrollBar().isVisible())

    def test_keyboard_and_accessible_names_are_complete(self) -> None:
        sources = _sources(
            students=(_student("S-1"),),
            memberships=(_membership("S-1", "C-1"),),
        )
        dialog = SchoolYearTransitionPreviewDialog(_preview(sources))
        dialog.show()
        self.app.processEvents()

        self.assertEqual(dialog.accessibleName(), "Schuljahreswechsel-Vorschau")
        self.assertEqual(dialog.table.accessibleName(), "Vorschau je Kind")
        self.assertTrue(dialog.status_message.accessibleName())
        self.assertTrue(
            all(label.accessibleName() for label in dialog.summary_labels.values())
        )
        for column in range(dialog.table.columnCount()):
            self.assertTrue(
                dialog.table.horizontalHeaderItem(column).data(
                    Qt.ItemDataRole.AccessibleTextRole
                )
            )
            self.assertTrue(
                dialog.table.item(0, column).data(
                    Qt.ItemDataRole.AccessibleDescriptionRole
                )
            )
        dialog.table.setFocus()
        QTest.keyClick(dialog.table, Qt.Key.Key_Right)
        self.assertEqual(dialog.table.currentColumn(), 1)

        close_button = dialog.findChild(QDialogButtonBox).button(
            QDialogButtonBox.StandardButton.Close
        )
        self.assertIsNotNone(close_button)
        self.assertEqual(close_button.accessibleName(), "Vorschau schließen")
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_widget_has_no_repository_or_write_call(self) -> None:
        sources = _sources(
            students=(_student("S-1"),),
            memberships=(_membership("S-1", "C-1"),),
        )
        with mock.patch(
            "sqlite3.connect",
            side_effect=AssertionError("Widget must not open SQLite"),
        ):
            dialog = SchoolYearTransitionPreviewDialog(_preview(sources))

        self.assertEqual(
            dialog.table.editTriggers(),
            QAbstractItemView.EditTrigger.NoEditTriggers,
        )
        self.assertEqual(
            dialog.findChildren(QDialogButtonBox)[0].standardButtons(),
            QDialogButtonBox.StandardButton.Close,
        )

    def test_opening_widget_does_not_change_database(self) -> None:
        with TemporaryDirectory() as directory:
            path = create_synthetic_v3_database(
                Path(directory) / "preview-ui.sqlite"
            )

            def snapshot() -> tuple[str, ...]:
                with sqlite3.connect(path) as connection:
                    return tuple(connection.iterdump())

            before = snapshot()

            def connect() -> sqlite3.Connection:
                connection = sqlite3.connect(path)
                connection.row_factory = sqlite3.Row
                return connection

            preview = SchoolYearTransitionPreviewService(connect).preview(
                label="2026/27",
                start_date=date(2026, 8, 1),
                end_date=date(2027, 7, 31),
            )
            dialog = SchoolYearTransitionPreviewDialog(preview)
            dialog.show()
            self.app.processEvents()
            dialog.close()

            self.assertEqual(snapshot(), before)

    def test_invalid_preview_period_remains_visible_without_crashing(self) -> None:
        invalid_planned = PlannedSchoolYear(
            "2026/27",
            "kein Datum",  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
        )
        preview = SchoolYearTransitionPreviewProjector().project(
            planned_school_year=invalid_planned,
            sources=_sources(),
        )
        dialog = SchoolYearTransitionPreviewDialog(preview)

        self.assertEqual(dialog.summary_labels["Zeitraum"].text(), "Nicht verfügbar")
        self.assertIn(
            "Zeitraum des neuen Schuljahres ist ungültig",
            dialog.status_message.label.text(),
        )

    def test_mapping_uses_preview_counts_without_recalculation(self) -> None:
        preview = _preview(
            _sources(
                students=(_student("S-1"),),
                memberships=(_membership("S-1", "C-1"),),
            )
        )
        altered_counts = replace(
            preview,
            student_count=91,
            advance_1_to_2_count=81,
            advance_2_to_3_count=71,
            unresolved_count=61,
            executable=False,
        )
        dialog = SchoolYearTransitionPreviewDialog(altered_counts)

        self.assertEqual(dialog.summary_labels["Kinder gesamt"].text(), "91")
        self.assertEqual(dialog.summary_labels["Wechsel 1 → 2"].text(), "81")
        self.assertEqual(dialog.summary_labels["Wechsel 2 → 3"].text(), "71")
        self.assertEqual(dialog.summary_labels["Ungelöst"].text(), "61")
        self.assertEqual(
            dialog.view_model.status_label,
            "Entscheidungen erforderlich",
        )


if __name__ == "__main__":
    unittest.main()
