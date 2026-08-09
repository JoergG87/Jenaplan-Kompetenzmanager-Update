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
from shiboken6 import isValid

from src.application.school_year_transition_plan import (
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
    KEEP_CURRENT_GROUP,
    REPEAT_YEAR_LEVEL_THREE,
    SELECT_OTHER_COURSE,
    SELECT_OTHER_GROUP,
)
from tests.helpers.synthetic_v4 import create_pre_transition_v4_database


create_synthetic_v4_database = create_pre_transition_v4_database


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
        for index in range(dialog.table.count())
        if dialog.table.item(index).data(Qt.ItemDataRole.UserRole)
        == student_id
    )


def _row_text(
    dialog: SchoolYearTransitionPreviewDialog,
    student_id: str,
) -> str:
    return dialog.table.item(_row(dialog, student_id)).text()


def _show_all(dialog: SchoolYearTransitionPreviewDialog) -> None:
    _set_combo_data(dialog.unresolved_filter, False)


def _combo(
    dialog: SchoolYearTransitionPreviewDialog,
    student_id: str,
    column: int,
) -> QComboBox:
    _set_combo_data(dialog.individual_student_combo, student_id)
    if column == 4:
        return dialog.individual_course_combo
    if column == 5:
        return dialog.individual_group_combo
    raise AssertionError("Expected course or group decision combo")


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
    app = QApplication.instance()
    if app is not None:
        app.processEvents()


def _select(
    dialog: SchoolYearTransitionPreviewDialog,
    student_id: str,
) -> None:
    try:
        row = _row(dialog, student_id)
    except StopIteration:
        _show_all(dialog)
        row = _row(dialog, student_id)
    item = dialog.table.item(row)
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
        _show_all(dialog)

        first_row = _row(dialog, "S-1")
        self.assertTrue(dialog.table.item(first_row).text().startswith("Test S-1\n"))
        self.assertNotEqual(dialog.table.item(first_row).text(), "S-1")
        self.assertEqual(
            _plan_item(dialog.plan, "S-1").student_id,
            "S-1",
        )

    def test_row_list_exposes_one_complete_read_only_summary_per_child(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        _show_all(dialog)

        self.assertEqual(dialog.table.count(), len(dialog.plan.items))
        row_text = _row_text(dialog, "S-3")
        self.assertIn("Test S-3", row_text)
        self.assertIn("Bisher: Stammgruppe Gruppe A", row_text)
        self.assertIn("Kurs Kurs 3", row_text)
        self.assertIn("Stufe 3", row_text)
        self.assertIn("Ziel: Ungelöst", row_text)
        self.assertIn("Warnungen und Blocker", row_text)
        self.assertFalse(
            bool(
                dialog.table.item(_row(dialog, "S-3")).flags()
                & Qt.ItemFlag.ItemIsEditable
            )
        )

    def test_row_list_starts_without_programmatic_ax_selection(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        self.assertEqual(dialog.table.currentRow(), -1)
        self.assertFalse(dialog.table.selectedItems())
        self.assertEqual(dialog.individual_student_combo.currentData(), "S-3")

    def test_summary_labels_are_owned_and_unused_labels_stay_hidden(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        dialog.show()
        self.app.processEvents()

        all_summary_labels = tuple(dialog.summary_labels.values()) + tuple(
            dialog.activation_summary_labels.values()
        )
        self.assertTrue(
            all(label.parentWidget() is not None for label in all_summary_labels)
        )
        self.assertTrue(
            all(
                label not in QApplication.topLevelWidgets()
                for label in all_summary_labels
            )
        )
        compact_fields = {
            "Wechsel 1 → 2",
            "Wechsel 2 → 3",
            "Ungelöst",
            "Ausgeschieden",
            "Stammgruppenänderungen",
        }
        self.assertTrue(
            all(
                label.isHidden()
                for field_name, label in dialog.summary_labels.items()
                if field_name not in compact_fields
            )
        )

    def test_alternative_course_creates_a_new_plan(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        initial_plan = dialog.plan

        _choose(
            _combo(dialog, "S-1", 4),
            SELECT_OTHER_COURSE,
            "C-2-B",
        )
        changed = _plan_item(dialog.plan, "S-1")
        self.assertIsNot(dialog.plan, initial_plan)
        self.assertEqual(changed.target_course_name, "Kurs 2B")
        self.assertIs(
            changed.target_status,
            SchoolYearTransitionPlanTargetStatus.OTHER_COURSE,
        )
        self.assertEqual(
            dialog.individual_course_combo.currentText(),
            "Kurs 2B",
        )

    def test_target_status_names_the_exact_year_level_change(self) -> None:
        initial_dialog = SchoolYearTransitionPreviewDialog(_plan())
        _show_all(initial_dialog)
        self.assertIn(
            "Wechsel 1 → 2",
            _row_text(initial_dialog, "S-1"),
        )
        self.assertIn(
            "Wechsel 2 → 3",
            _row_text(initial_dialog, "S-2"),
        )

        for student_id, course_id, expected in (
            ("S-1", "C-3", "Wechsel 1 → 3"),
            ("S-2", "C-1", "Wechsel 2 → 1"),
            ("S-3", "C-1", "Wechsel 3 → 1"),
            ("S-3", "C-2", "Wechsel 3 → 2"),
        ):
            with self.subTest(student_id=student_id, course_id=course_id):
                dialog = SchoolYearTransitionPreviewDialog(_plan())
                _choose(
                    _combo(dialog, student_id, 4),
                    SELECT_OTHER_COURSE,
                    course_id,
                )
                _show_all(dialog)
                self.assertIn(expected, _row_text(dialog, student_id))

    def test_same_level_course_result_is_described_without_other_course(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        _choose(
            _combo(dialog, "S-2", 4),
            SELECT_OTHER_COURSE,
            "C-2-B",
        )
        _show_all(dialog)

        self.assertIn(
            "Kurswechsel innerhalb Stufe 2",
            _row_text(dialog, "S-2"),
        )

    def test_course_choices_use_compact_course_and_status_labels(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        course_combo = _combo(dialog, "S-1", 4)
        self.assertEqual(course_combo.currentText(), "Kurs 2")
        self.assertEqual(
            {
                course_combo.itemText(index)
                for index in range(1, course_combo.count())
            },
            {
                "Kurs 1",
                "Kurs 2B",
                "Kurs 3",
            },
        )
        self.assertIn("Zielkurs", course_combo.accessibleName())
        self.assertNotIn(
            course_combo.currentText(),
            {
                course_combo.itemText(index)
                for index in range(1, course_combo.count())
            },
        )
        self.assertEqual(dialog.individual_exited_button.text(), "Ausgeschieden")
        self.assertEqual(dialog.individual_unresolved_button.text(), "Ungelöst")
        course_three_combo = _combo(dialog, "S-3", 4)
        course_three_labels = tuple(
            course_three_combo.itemText(index)
            for index in range(course_three_combo.count())
        )
        self.assertIn("Verbleibt in Kurs 3", course_three_labels)
        self.assertNotIn("Kurs 3", course_three_labels)
        self.assertFalse(
            any(
                course_three_combo.itemData(index)
                == (SELECT_OTHER_COURSE, "C-3")
                for index in range(course_three_combo.count())
            )
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
        _show_all(dialog)
        self.assertIn(
            "Verbleibt in Kurs 3",
            _row_text(dialog, "S-3"),
        )

    def test_course_three_editor_remains_stable_during_refresh(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        old_combo = _combo(dialog, "S-3", 4)

        selection = (REPEAT_YEAR_LEVEL_THREE, "C-3")
        index = next(
            index
            for index in range(old_combo.count())
            if old_combo.itemData(index) == selection
        )
        old_combo.setCurrentIndex(index)
        old_combo.activated.emit(index)

        self.app.processEvents()

        new_combo = _combo(dialog, "S-3", 4)
        self.assertIs(new_combo, old_combo)
        self.assertTrue(new_combo.accessibleName())
        self.assertTrue(new_combo.accessibleDescription())
        self.assertTrue(isValid(old_combo))
        self.assertFalse(dialog._retired_tables)
        self.assertEqual(
            dialog.summary_labels["Kurs 3 wiederholen"].text(),
            "1",
        )

    def test_current_target_group_is_not_repeated_in_group_choices(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())

        group_combo = _combo(dialog, "S-1", 5)
        self.assertEqual(group_combo.currentText(), "Gruppe A")
        self.assertEqual(
            tuple(
                group_combo.itemText(index)
                for index in range(1, group_combo.count())
            ),
            ("Gruppe B",),
        )

        _choose(
            group_combo,
            SELECT_OTHER_GROUP,
            "G-B",
        )
        changed = _plan_item(dialog.plan, "S-1")
        self.assertEqual(changed.target_group_name, "Gruppe B")
        self.assertIs(
            changed.group_decision,
            SchoolYearTransitionGroupDecision.SELECT_OTHER_GROUP,
        )
        self.assertEqual(dialog.individual_group_combo.currentText(), "Gruppe B")
        self.assertNotIn(
            "Gruppe B",
            {
                dialog.individual_group_combo.itemText(index)
                for index in range(1, dialog.individual_group_combo.count())
            },
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
        _show_all(dialog)

        _set_combo_data(dialog.individual_student_combo, "S-2")
        dialog.individual_exited_button.click()
        row = _row(dialog, "S-2")
        exited = _plan_item(dialog.plan, "S-2")

        self.assertIs(
            exited.target_status,
            SchoolYearTransitionPlanTargetStatus.EXITED,
        )
        self.assertIsNone(exited.target_group_id)
        self.assertIsNone(exited.target_course_id)
        self.assertIn(
            "Ziel: Ausgeschieden, Stammgruppe —, Kurs —",
            dialog.table.item(row).text(),
        )
        self.assertFalse(
            bool(dialog.table.item(row).flags() & Qt.ItemFlag.ItemIsEditable)
        )
        self.assertEqual(dialog.summary_labels["Ausgeschieden"].text(), "1")

    def test_consciously_unresolved_remains_textually_blocking(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        _show_all(dialog)

        _set_combo_data(dialog.individual_student_combo, "S-1")
        dialog.individual_unresolved_button.click()
        row = _row(dialog, "S-1")

        self.assertIn("Ziel: Ungelöst", dialog.table.item(row).text())
        self.assertIn(
            "bewusst ungelöst",
            dialog.table.item(row).text(),
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
        self.assertIs(dialog.unresolved_filter.currentData(), True)
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(
            dialog.table.item(0).data(Qt.ItemDataRole.UserRole),
            "S-3",
        )

        _set_combo_data(dialog.unresolved_filter, True)
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(
            dialog.table.item(0).data(Qt.ItemDataRole.UserRole),
            "S-3",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.current_course_filter, "C-1")
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(
            dialog.table.item(0).data(Qt.ItemDataRole.UserRole),
            "S-1",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.target_course_filter, "C-3")
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(
            dialog.table.item(0).data(Qt.ItemDataRole.UserRole),
            "S-2",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.current_group_filter, "G-A")
        self.assertEqual(dialog.table.count(), 3)

        dialog.reset_filters_button.click()
        _choose(
            _combo(dialog, "S-1", 5),
            SELECT_OTHER_GROUP,
            "G-B",
        )
        _set_combo_data(dialog.target_group_filter, "G-B")
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(
            dialog.table.item(0).data(Qt.ItemDataRole.UserRole),
            "S-1",
        )

        dialog.reset_filters_button.click()
        _set_combo_data(dialog.unresolved_filter, True)
        _set_combo_data(dialog.current_course_filter, "C-3")
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(
            dialog.table.item(0).data(Qt.ItemDataRole.UserRole),
            "S-3",
        )
        dialog.reset_filters_button.click()
        self.assertEqual(dialog.table.count(), 3)

    def test_workflow_starts_calm_and_focused_on_open_cases(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        original_plan = dialog.plan

        self.assertEqual(dialog.workflow_tabs.count(), 2)
        self.assertEqual(dialog.workflow_tabs.currentIndex(), 0)
        self.assertIn("Zuordnungen prüfen", dialog.workflow_tabs.tabText(0))
        self.assertIn("noch 1 offen", dialog.workflow_tabs.tabText(1))
        self.assertIs(dialog.unresolved_filter.currentData(), True)
        self.assertEqual(dialog.table.count(), 1)
        self.assertEqual(dialog.individual_student_combo.currentData(), "S-3")
        self.assertFalse(dialog.advanced_filters_widget.isVisible())
        self.assertFalse(dialog.bulk_actions_panel.isVisible())
        self.assertEqual(
            dialog.visible_count_label.text(),
            "1 von 3 Kindern sichtbar · 1 ungelöst",
        )

        dialog.workflow_tabs.setCurrentIndex(1)

        self.assertIs(dialog.plan, original_plan)
        self.assertIs(
            dialog.workflow_tabs.currentWidget(),
            dialog.activation_page,
        )
        self.assertFalse(dialog.confirmation_checkbox.isChecked())
        dialog.workflow_tabs.setCurrentIndex(0)

        _show_all(dialog)

        self.assertEqual(dialog.table.count(), len(dialog.plan.items))
        self.assertEqual(
            {
                dialog.table.item(row).data(Qt.ItemDataRole.UserRole)
                for row in range(dialog.table.count())
            },
            {item.student_id for item in dialog.plan.items},
        )

    def test_bulk_actions_appear_only_for_a_visible_selection(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        self.assertTrue(dialog.bulk_actions_panel.isHidden())

        _select(dialog, "S-1")

        self.assertFalse(dialog.bulk_actions_panel.isHidden())
        self.assertTrue(dialog.bulk_course_button.isEnabled())
        self.assertEqual(dialog.bulk_course_combo.maximumWidth(), 440)
        self.assertEqual(dialog.bulk_group_combo.maximumWidth(), 440)
        self.assertEqual(dialog.bulk_actions_grid.columnStretch(0), 1)
        self.assertEqual(dialog.bulk_actions_grid.columnStretch(3), 1)
        dialog.clear_selection_button.click()
        self.assertTrue(dialog.bulk_actions_panel.isHidden())

    def test_escape_clears_the_active_filter_before_closing(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        dialog.show()
        self.app.processEvents()

        QTest.keyClick(dialog, Qt.Key.Key_Escape)

        self.assertTrue(dialog.isVisible())
        self.assertIs(dialog.unresolved_filter.currentData(), False)
        self.assertEqual(dialog.table.count(), len(dialog.plan.items))

        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        if QApplication.platformName().casefold() not in {
            "offscreen",
            "minimal",
        }:
            for _attempt in range(40):
                if not dialog.isVisible():
                    break
                QTest.qWait(50)
                self.app.processEvents()
        self.assertFalse(dialog.isVisible())

    def test_individual_and_all_visible_selection_are_explicit(self) -> None:
        dialog = SchoolYearTransitionPreviewDialog(_plan())
        self.assertFalse(dialog.bulk_exited_button.isEnabled())

        _select(dialog, "S-1")
        self.assertIn("1 Kind ausgewählt", dialog.selected_count_label.text())
        self.assertEqual(
            dialog.table.item(_row(dialog, "S-1")).checkState(),
            Qt.CheckState.Checked,
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
                if dialog.table.item(_row(dialog, student_id)).checkState()
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
        self.assertEqual(
            dialog.summary_labels["Individuelle Kurswahl"].text(),
            "1",
        )
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
            path = create_synthetic_v4_database(
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
        _show_all(dialog)
        dialog.show()
        self.app.processEvents()

        course_combo = _combo(dialog, "S-1", 4)
        original_plan = dialog.plan
        for combo in (
            dialog.unresolved_filter,
            dialog.bulk_course_combo,
            dialog.bulk_group_combo,
            course_combo,
        ):
            self.assertEqual(
                combo.maxVisibleItems(),
                min(combo.count(), 18),
            )
            self.assertGreaterEqual(
                combo.view().minimumHeight(),
                combo.maxVisibleItems() * 28,
            )
            self.assertGreaterEqual(
                combo.view().minimumWidth(),
                combo.sizeHint().width(),
            )
        course_combo.showPopup()
        self.app.processEvents()
        course_combo.hidePopup()
        self.app.processEvents()
        self.assertIs(dialog.plan, original_plan)
        group_combo = _combo(dialog, "S-1", 5)

        self.assertEqual(
            dialog.accessibleName(),
            "Schuljahreswechsel bearbeiten",
        )
        self.assertEqual(
            dialog.table.accessibleName(),
            "Kindliste für den Schuljahreswechsel",
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
        self.assertEqual(
            dialog.table.accessibleName(),
            "Kindliste für den Schuljahreswechsel",
        )
        for row in range(dialog.table.count()):
            item = dialog.table.item(row)
            self.assertTrue(item.text())
            self.assertIsNone(
                item.data(Qt.ItemDataRole.AccessibleTextRole)
            )
            self.assertIsNone(
                item.data(Qt.ItemDataRole.AccessibleDescriptionRole)
            )

        dialog.activateWindow()
        dialog.table.setFocus(Qt.FocusReason.TabFocusReason)
        self.app.processEvents()
        QTest.keyClick(dialog, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertIs(QApplication.focusWidget(), dialog.table)

        course_combo.setFocus(Qt.FocusReason.TabFocusReason)
        self.app.processEvents()
        self.assertIs(QApplication.focusWidget(), course_combo)
        QTest.keyClick(course_combo, Qt.Key.Key_Tab)
        self.app.processEvents()
        self.assertIs(QApplication.focusWidget(), group_combo)

        row = _row(dialog, "S-1")
        dialog.table.setCurrentRow(row)
        dialog.table.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(dialog.table, Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertIs(QApplication.focusWidget(), course_combo)
        dialog.table.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(dialog.table, Qt.Key.Key_Space)
        self.app.processEvents()
        self.assertEqual(
            dialog.table.item(_row(dialog, "S-1")).checkState(),
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

        self.assertIs(
            dialog.work_splitter.orientation(),
            Qt.Orientation.Vertical,
        )
        self.assertGreater(
            dialog.work_scroll.verticalScrollBar().maximum(),
            0,
        )
        self.assertFalse(dialog.dialog_header.description_label.isVisible())
        self.assertEqual(dialog.table.horizontalScrollBar().maximum(), 0)
        self.assertGreater(dialog.table.verticalScrollBar().maximum(), 0)
        self.assertFalse(dialog.table.horizontalScrollBar().isVisible())
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
