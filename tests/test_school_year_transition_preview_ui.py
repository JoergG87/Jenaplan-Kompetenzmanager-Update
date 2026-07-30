"""Focused UI checks for the editable SJ-3B.2b transition plan dialog."""

from __future__ import annotations

import os
import sqlite3
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QComboBox,
    QDialog,
    QDialogButtonBox,
)

from src.application.school_year_transition_plan import (
    SchoolYearTransitionCourseDecision,
    SchoolYearTransitionGroupDecision,
    SchoolYearTransitionPlan,
    SchoolYearTransitionPlanTargetStatus,
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
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionPreviewRepository,
)
from src.desktop_app.dialogs.school_year_transition_preview_dialog import (
    SchoolYearTransitionPreviewDialog,
)
from src.desktop_app.view_models.school_year_transition_preview_view_model import (
    ACCEPT_PROPOSAL,
    KEEP_CURRENT_GROUP,
    LEAVE_UNRESOLVED,
    MARK_EXITED,
    REPEAT_YEAR_LEVEL_THREE,
    SELECT_OTHER_COURSE,
    SELECT_OTHER_GROUP,
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
COURSES = (
    SchoolYearTransitionCourse("C-1", "Kurs 1", True, 1),
    SchoolYearTransitionCourse("C-2", "Kurs 2", True, 2),
    SchoolYearTransitionCourse("C-2-B", "Kurs 2B", True, 2),
    SchoolYearTransitionCourse("C-3", "Kurs 3", True, 3),
)
GROUPS = (
    SchoolYearTransitionGroup("G-A", "Gruppe A", True),
    SchoolYearTransitionGroup("G-B", "Gruppe B", True),
)


def _student(student_id: str) -> V3Student:
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return V3Student(
        student_id=student_id,
        first_name="Test",
        last_name=student_id,
        notes="",
        active=True,
        created_at=timestamp,
        updated_at=timestamp,
        archived_at=None,
    )


def _membership(
    student_id: str,
    course_id: str,
) -> SchoolYearTransitionMembership:
    return SchoolYearTransitionMembership(
        student_id=student_id,
        school_year_id=CURRENT.school_year_id,
        group_id="G-A",
        group_name="Gruppe A",
        course_id=course_id,
        course_name=f"Kurs {course_id.removeprefix('C-')}",
        assignment_status=StudentAssignmentStatus.ENROLLED,
    )


def _preview(
    *,
    students: tuple[V3Student, ...] | None = None,
    memberships: tuple[SchoolYearTransitionMembership, ...] | None = None,
    courses: tuple[SchoolYearTransitionCourse, ...] | None = None,
):
    preview_students = students or (
        _student("S-1"),
        _student("S-2"),
        _student("S-3"),
    )
    preview_memberships = memberships or (
        _membership("S-1", "C-1"),
        _membership("S-2", "C-2"),
        _membership("S-3", "C-3"),
    )
    sources = SchoolYearTransitionPreviewSources(
        school_years=(CURRENT,),
        students=preview_students,
        memberships=preview_memberships,
        courses=courses or (COURSES[0], COURSES[1], COURSES[3]),
        groups=GROUPS,
    )
    return SchoolYearTransitionPreviewProjector().project(
        planned_school_year=PLANNED,
        sources=sources,
    )


def _plan(preview=None) -> SchoolYearTransitionPlan:
    return SchoolYearTransitionPlan.from_preview(
        preview or _preview(),
        courses=COURSES,
        groups=GROUPS,
    )


def _plan_item(plan: SchoolYearTransitionPlan, student_id: str):
    return next(item for item in plan.items if item.student_id == student_id)


def _row(dialog: SchoolYearTransitionPreviewDialog, student_id: str) -> int:
    return next(
        index
        for index in range(dialog.table.rowCount())
        if dialog.table.item(index, 0).data(Qt.ItemDataRole.UserRole)
        == student_id
    )


def _combo(
    dialog: SchoolYearTransitionPreviewDialog,
    student_id: str,
    column: int,
) -> QComboBox:
    widget = dialog.table.cellWidget(_row(dialog, student_id), column + 1)
    if not isinstance(widget, QComboBox):
        raise AssertionError("Expected decision combo")
    return widget


def _choose(
    combo: QComboBox,
    action: str,
    option_id: str | None = None,
) -> None:
    selection = (action, option_id)
    index = next(
        index
        for index in range(combo.count())
        if combo.itemData(index) == selection
    )
    combo.setCurrentIndex(index)
    combo.activated.emit(index)


def _select(
    dialog: SchoolYearTransitionPreviewDialog,
    student_id: str,
) -> None:
    item = dialog.table.item(_row(dialog, student_id), 0)
    item.setCheckState(Qt.CheckState.Checked)


def _set_combo_data(combo: QComboBox, value: object) -> None:
    index = combo.findData(value)
    if index < 0:
        raise AssertionError(f"Missing combo value: {value!r}")
    combo.setCurrentIndex(index)


class SchoolYearTransitionPreviewUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, SchoolYearTransitionPreviewDialog):
                widget.close()

    def test_student_name_is_visible_instead_of_student_id(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        first_row = _row(dialog, "S-1")
        self.assertEqual(dialog.table.item(first_row, 1).text(), "Test S-1")
        self.assertNotEqual(dialog.table.item(first_row, 1).text(), "S-1")
        self.assertEqual(
            _plan_item(dialog.plan, "S-1").student_id,
            "S-1",
        )

    def test_proposal_and_alternative_course_create_new_plans(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        initial_plan = dialog.plan

        _choose(_combo(dialog, "S-1", 4), ACCEPT_PROPOSAL)
        accepted_plan = dialog.plan
        accepted = _plan_item(accepted_plan, "S-1")
        self.assertIsNot(accepted_plan, initial_plan)
        self.assertEqual(accepted.target_course_name, "Kurs 2")
        self.assertIs(
            accepted.course_decision,
            SchoolYearTransitionCourseDecision.ACCEPT_PROPOSAL,
        )

        _choose(
            _combo(dialog, "S-1", 4),
            SELECT_OTHER_COURSE,
            "C-2-B",
        )
        changed = _plan_item(dialog.plan, "S-1")
        self.assertIsNot(dialog.plan, accepted_plan)
        self.assertEqual(changed.target_course_name, "Kurs 2B")
        self.assertIs(
            changed.target_status,
            SchoolYearTransitionPlanTargetStatus.OTHER_COURSE,
        )

    def test_course_three_repeat_is_a_conscious_selection(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        self.assertEqual(
            _plan_item(dialog.plan, "S-3").target_status,
            SchoolYearTransitionPlanTargetStatus.UNRESOLVED,
        )
        _choose(
            _combo(dialog, "S-3", 4),
            REPEAT_YEAR_LEVEL_THREE,
            "C-3",
        )

        repeated = _plan_item(dialog.plan, "S-3")
        self.assertIs(
            repeated.target_status,
            SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE,
        )
        self.assertEqual(
            dialog.summary_labels["Kurs 3 wiederholen"].text(),
            "1",
        )

    def test_group_can_be_kept_or_changed_individually(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        _choose(_combo(dialog, "S-1", 5), KEEP_CURRENT_GROUP)
        kept = _plan_item(dialog.plan, "S-1")
        self.assertIs(
            kept.group_decision,
            SchoolYearTransitionGroupDecision.KEEP_CURRENT_GROUP,
        )

        _choose(
            _combo(dialog, "S-1", 5),
            SELECT_OTHER_GROUP,
            "G-B",
        )
        changed = _plan_item(dialog.plan, "S-1")
        self.assertEqual(changed.target_group_name, "Gruppe B")
        self.assertIs(
            changed.group_decision,
            SchoolYearTransitionGroupDecision.SELECT_OTHER_GROUP,
        )

    def test_current_group_can_be_kept_when_current_course_is_invalid(
        self,
    ) -> None:
        preview = _preview(
            students=(_student("S-X"),),
            memberships=(_membership("S-X", "C-1"),),
            courses=(COURSES[1], COURSES[3]),
        )
        self.assertIsNone(preview.items[0].proposed_group_id)
        dialog = SchoolYearTransitionPreviewDialog(_plan(preview))

        group_combo = _combo(dialog, "S-X", 5)
        self.assertTrue(
            any(
                group_combo.itemData(index) == (KEEP_CURRENT_GROUP, None)
                for index in range(group_combo.count())
            )
        )
        self.assertFalse(
            any(
                group_combo.itemData(index)
                == (SELECT_OTHER_GROUP, "G-A")
                for index in range(group_combo.count())
            )
        )
        _choose(group_combo, KEEP_CURRENT_GROUP)

        kept = _plan_item(dialog.plan, "S-X")
        self.assertEqual(kept.target_group_id, "G-A")
        self.assertIs(
            kept.group_decision,
            SchoolYearTransitionGroupDecision.KEEP_CURRENT_GROUP,
        )

    def test_exited_has_no_target_course_or_group(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        _choose(_combo(dialog, "S-2", 4), MARK_EXITED)
        row = _row(dialog, "S-2")
        exited = _plan_item(dialog.plan, "S-2")

        self.assertIs(
            exited.target_status,
            SchoolYearTransitionPlanTargetStatus.EXITED,
        )
        self.assertIsNone(exited.target_group_id)
        self.assertIsNone(exited.target_course_id)
        self.assertEqual(dialog.table.item(row, 6).text(), "—")
        self.assertEqual(dialog.table.item(row, 7).text(), "—")
        self.assertIsNone(dialog.table.cellWidget(row, 6))
        self.assertEqual(dialog.summary_labels["Ausgeschieden"].text(), "1")

    def test_consciously_unresolved_remains_textually_blocking(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        _choose(_combo(dialog, "S-1", 4), LEAVE_UNRESOLVED)
        row = _row(dialog, "S-1")

        self.assertEqual(dialog.table.item(row, 5).text(), "Ungelöst")
        self.assertIn(
            "bewusst ungelöst",
            dialog.table.item(row, 8).text(),
        )
        self.assertIn(
            "Entscheidungen erforderlich",
            dialog.status_message.label.text(),
        )

    def test_counts_and_status_refresh_after_every_change(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        self.assertEqual(dialog.summary_labels["Ungelöst"].text(), "1")
        self.assertEqual(
            dialog.summary_labels["Individuell bearbeitet"].text(),
            "0",
        )

        _choose(
            _combo(dialog, "S-3", 4),
            REPEAT_YEAR_LEVEL_THREE,
            "C-3",
        )

        self.assertEqual(dialog.summary_labels["Ungelöst"].text(), "0")
        self.assertEqual(
            dialog.summary_labels["Individuell bearbeitet"].text(),
            "1",
        )
        self.assertIn(
            "Plan vollständig",
            dialog.status_message.label.text(),
        )

    def test_filters_work_individually_and_in_combination(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        self.assertEqual(dialog.table.rowCount(), 3)

        _set_combo_data(dialog.unresolved_filter, True)
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(
            dialog.table.item(0, 0).data(Qt.ItemDataRole.UserRole),
            "S-3",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.current_course_filter, "C-1")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(
            dialog.table.item(0, 0).data(Qt.ItemDataRole.UserRole),
            "S-1",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.target_course_filter, "C-3")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(
            dialog.table.item(0, 0).data(Qt.ItemDataRole.UserRole),
            "S-2",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.current_group_filter, "G-A")
        self.assertEqual(dialog.table.rowCount(), 3)

        dialog.reset_filters_button.click()
        _choose(
            _combo(dialog, "S-1", 5),
            SELECT_OTHER_GROUP,
            "G-B",
        )
        _set_combo_data(dialog.target_group_filter, "G-B")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(
            dialog.table.item(0, 0).data(Qt.ItemDataRole.UserRole),
            "S-1",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.unresolved_filter, True)
        _set_combo_data(dialog.current_course_filter, "C-3")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(
            dialog.table.item(0, 0).data(Qt.ItemDataRole.UserRole),
            "S-3",
        )
        dialog.reset_filters_button.click()
        self.assertEqual(dialog.table.rowCount(), 3)

    def test_individual_and_all_visible_selection_are_explicit(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        self.assertFalse(dialog.bulk_exited_button.isEnabled())

        _select(dialog, "S-1")
        self.assertIn("1 Kind ausgewählt", dialog.selected_count_label.text())
        self.assertEqual(
            dialog.table.item(_row(dialog, "S-1"), 0).text(),
            "Ausgewählt",
        )
        self.assertTrue(dialog.bulk_exited_button.isEnabled())

        _set_combo_data(dialog.current_course_filter, "C-2")
        dialog.select_visible_button.click()
        self.assertIn("2 Kinder ausgewählt", dialog.selected_count_label.text())
        dialog.reset_filters_button.click()
        self.assertEqual(
            {
                student_id
                for student_id in ("S-1", "S-2", "S-3")
                if dialog.table.item(
                    _row(dialog, student_id),
                    0,
                ).checkState()
                == Qt.CheckState.Checked
            },
            {"S-1", "S-2"},
        )

        dialog.clear_selection_button.click()
        self.assertEqual(dialog.selected_count_label.text(), "0 Kinder ausgewählt")
        self.assertFalse(dialog.bulk_exited_button.isEnabled())

    def test_filter_change_preserves_selection_but_bulk_edits_only_visible(
        self,
    ) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        _select(dialog, "S-1")
        _set_combo_data(dialog.current_course_filter, "C-2")
        _select(dialog, "S-2")
        before = dialog.plan

        dialog.bulk_exited_button.click()

        self.assertIsNot(dialog.plan, before)
        self.assertIs(
            _plan_item(dialog.plan, "S-2").target_status,
            SchoolYearTransitionPlanTargetStatus.EXITED,
        )
        self.assertIs(
            _plan_item(dialog.plan, "S-1").target_status,
            SchoolYearTransitionPlanTargetStatus.ADVANCE_1_TO_2,
        )
        self.assertIn(
            "2 Kinder ausgewählt, davon 1",
            dialog.selected_count_label.text(),
        )

    def test_bulk_target_course_updates_only_selected_and_counts(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        initial_plan = dialog.plan
        unchanged_s2 = _plan_item(initial_plan, "S-2")
        _select(dialog, "S-1")
        _set_combo_data(dialog.bulk_course_combo, "C-2-B")

        dialog.bulk_course_button.click()

        self.assertIsNot(dialog.plan, initial_plan)
        changed = _plan_item(dialog.plan, "S-1")
        self.assertEqual(changed.target_course_id, "C-2-B")
        self.assertIs(
            changed.target_status,
            SchoolYearTransitionPlanTargetStatus.OTHER_COURSE,
        )
        self.assertEqual(_plan_item(dialog.plan, "S-2"), unchanged_s2)
        self.assertEqual(dialog.summary_labels["Anderer Kurs"].text(), "1")
        self.assertEqual(
            dialog.summary_labels["Individuell bearbeitet"].text(),
            "1",
        )

    def test_bulk_target_group_confirms_multiple_children(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        _select(dialog, "S-1")
        _select(dialog, "S-2")
        _set_combo_data(dialog.bulk_group_combo, "G-B")

        with mock.patch.object(
            dialog,
            "_confirm_bulk_change",
            return_value=True,
        ) as confirm:
            dialog.bulk_group_button.click()

        confirm.assert_called_once()
        self.assertEqual(_plan_item(dialog.plan, "S-1").target_group_id, "G-B")
        self.assertEqual(_plan_item(dialog.plan, "S-2").target_group_id, "G-B")
        self.assertEqual(_plan_item(dialog.plan, "S-3").target_group_id, "G-A")

    def test_cancelled_multi_child_confirmation_keeps_plan_unchanged(
        self,
    ) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        _select(dialog, "S-1")
        _select(dialog, "S-2")
        original_plan = dialog.plan

        with mock.patch.object(
            dialog,
            "_confirm_bulk_change",
            return_value=False,
        ):
            dialog.bulk_exited_button.click()

        self.assertIs(dialog.plan, original_plan)

    def test_bulk_exited_and_unresolved_clear_the_required_targets(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        _select(dialog, "S-1")
        dialog.bulk_exited_button.click()
        exited = _plan_item(dialog.plan, "S-1")
        self.assertIsNone(exited.target_course_id)
        self.assertIsNone(exited.target_group_id)
        self.assertEqual(dialog.summary_labels["Ausgeschieden"].text(), "1")

        dialog.clear_selection_button.click()
        _select(dialog, "S-2")
        dialog.bulk_unresolved_button.click()
        unresolved = _plan_item(dialog.plan, "S-2")
        self.assertIs(
            unresolved.target_status,
            SchoolYearTransitionPlanTargetStatus.UNRESOLVED,
        )
        self.assertIsNone(unresolved.target_course_id)
        self.assertEqual(unresolved.target_group_id, "G-A")
        self.assertEqual(dialog.summary_labels["Ungelöst"].text(), "2")

    def test_bulk_course_three_requires_a_conscious_level_three_choice(
        self,
    ) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        initial_plan = dialog.plan
        _select(dialog, "S-3")
        self.assertIs(
            _plan_item(initial_plan, "S-3").target_status,
            SchoolYearTransitionPlanTargetStatus.UNRESOLVED,
        )
        _set_combo_data(dialog.bulk_course_combo, "C-3")

        dialog.bulk_course_button.click()

        repeated = _plan_item(dialog.plan, "S-3")
        self.assertIs(
            repeated.target_status,
            SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE,
        )
        self.assertEqual(dialog.summary_labels["Ungelöst"].text(), "0")
        self.assertEqual(
            dialog.summary_labels["Kurs 3 wiederholen"].text(),
            "1",
        )

    def test_original_preview_and_initial_plan_remain_unchanged(self) -> None:
        preview = _preview()
        original_preview = preview
        initial_plan = _plan(preview)
        dialog = SchoolYearTransitionPreviewDialog(initial_plan)

        _select(dialog, "S-2")
        dialog.bulk_exited_button.click()

        self.assertEqual(preview, original_preview)
        self.assertIs(
            _plan_item(initial_plan, "S-2").target_status,
            SchoolYearTransitionPlanTargetStatus.ADVANCE_2_TO_3,
        )
        self.assertIs(
            _plan_item(dialog.plan, "S-2").target_status,
            SchoolYearTransitionPlanTargetStatus.EXITED,
        )

    def test_widget_edits_do_not_call_sqlite_or_change_database(self) -> None:
        with TemporaryDirectory() as directory:
            path = create_synthetic_v3_database(
                Path(directory) / "preview-ui.sqlite"
            )

            def snapshot() -> tuple[str, ...]:
                with sqlite3.connect(path) as connection:
                    return tuple(connection.iterdump())

            def connect() -> sqlite3.Connection:
                connection = sqlite3.connect(path)
                connection.row_factory = sqlite3.Row
                return connection

            before = snapshot()
            preview = SchoolYearTransitionPreviewService(connect).preview(
                label="2026/27",
                start_date=date(2026, 8, 1),
                end_date=date(2027, 7, 31),
            )
            plan = SchoolYearTransitionPlan.from_preview(
                preview,
                courses=COURSES,
                groups=GROUPS,
            )
            with mock.patch(
                "sqlite3.connect",
                side_effect=AssertionError("Widget must not open SQLite"),
            ), mock.patch.object(
                SchoolYearTransitionPreviewService,
                "preview",
                side_effect=AssertionError(
                    "Widget must not call the preview service"
                ),
            ), mock.patch.object(
                SchoolYearTransitionPreviewRepository,
                "read_sources",
                side_effect=AssertionError(
                    "Widget must not call the preview repository"
                ),
            ):
                dialog = SchoolYearTransitionPreviewDialog(plan)
                student_id = dialog.plan.items[0].student_id
                _select(dialog, student_id)
                dialog.bulk_exited_button.click()
            self.assertEqual(snapshot(), before)

    def test_keyboard_accessibility_and_dropdown_opening_are_safe(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        dialog.show()
        self.app.processEvents()

        course_combo = _combo(dialog, "S-1", 4)
        group_combo = _combo(dialog, "S-1", 5)
        original_plan = dialog.plan
        course_combo.showPopup()
        self.app.processEvents()
        course_combo.hidePopup()
        self.app.processEvents()
        self.assertIs(dialog.plan, original_plan)

        self.assertEqual(
            dialog.accessibleName(),
            "Schuljahreswechsel-Vorschau bearbeiten",
        )
        self.assertEqual(
            dialog.table.accessibleName(),
            "Flüchtiger Plan je Kind",
        )
        self.assertTrue(dialog.status_message.accessibleName())
        self.assertTrue(dialog.selected_count_label.accessibleName())
        self.assertTrue(dialog.unresolved_filter.accessibleName())
        self.assertTrue(dialog.current_course_filter.accessibleName())
        self.assertTrue(dialog.target_course_filter.accessibleName())
        self.assertTrue(dialog.current_group_filter.accessibleName())
        self.assertTrue(dialog.target_group_filter.accessibleName())
        self.assertTrue(dialog.bulk_course_combo.accessibleName())
        self.assertTrue(dialog.bulk_group_combo.accessibleName())
        self.assertTrue(dialog.bulk_exited_button.accessibleName())
        self.assertTrue(dialog.bulk_unresolved_button.accessibleName())
        self.assertIn("Test S-1", course_combo.accessibleName())
        self.assertIn("Test S-1", group_combo.accessibleName())
        self.assertTrue(course_combo.accessibleDescription())
        self.assertTrue(
            all(
                label.accessibleName()
                for label in dialog.summary_labels.values()
            )
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

        dialog.activateWindow()
        course_combo.setFocus(Qt.FocusReason.TabFocusReason)
        self.app.processEvents()
        self.assertIs(QApplication.focusWidget(), course_combo)
        QTest.keyClick(course_combo, Qt.Key.Key_Tab)
        self.app.processEvents()
        self.assertIs(QApplication.focusWidget(), group_combo)

        dialog.table.setCurrentCell(_row(dialog, "S-1"), 0)
        dialog.table.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(dialog.table, Qt.Key.Key_Space)
        self.app.processEvents()
        self.assertEqual(
            dialog.table.item(_row(dialog, "S-1"), 0).checkState(),
            Qt.CheckState.Checked,
        )
        self.assertIn("1 Kind ausgewählt", dialog.selected_count_label.text())

        self.assertIsNotNone(dialog.close_button)
        self.assertEqual(
            dialog.close_button.accessibleName(),
            "Vorschau schließen",
        )
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_long_lists_scroll_and_no_execution_action_exists(self) -> None:
        students = tuple(_student(f"S-{number:02}") for number in range(24))
        memberships = tuple(
            _membership(student.student_id, "C-1")
            for student in students
        )
        dialog = SchoolYearTransitionPreviewDialog(
            _plan(_preview(students=students, memberships=memberships))
        )
        dialog.resize(520, 360)
        dialog.show()
        self.app.processEvents()

        self.assertGreater(dialog.table.horizontalScrollBar().maximum(), 0)
        self.assertGreater(dialog.table.verticalScrollBar().maximum(), 0)
        self.assertTrue(dialog.table.horizontalScrollBar().isVisible())
        self.assertTrue(dialog.table.verticalScrollBar().isVisible())
        self.assertEqual(
            dialog.table.selectionMode(),
            dialog.table.SelectionMode.SingleSelection,
        )
        self.assertEqual(
            dialog.buttons.standardButtons(),
            QDialogButtonBox.StandardButton.Close,
        )
        button_texts = tuple(
            button.text()
            for button in dialog.findChildren(QAbstractButton)
        )
        self.assertNotIn("Ausführen", button_texts)
        self.assertIn("Alle sichtbaren auswählen", button_texts)


if __name__ == "__main__":
    unittest.main()
