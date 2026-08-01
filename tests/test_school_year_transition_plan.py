"""Pure application tests for the transient SJ-3B.2a plan model."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3

import pytest

from src.application.school_year_transition_plan import (
    SchoolYearTransitionCourseDecision,
    SchoolYearTransitionGroupDecision,
    SchoolYearTransitionPlan,
    SchoolYearTransitionPlanError,
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
    SchoolYearTransitionIssueSeverity,
    SchoolYearTransitionMembership,
    SchoolYearTransitionPreviewSources,
    SchoolYearTransitionValidationIssue,
)
from tests.helpers.synthetic_v3 import create_pre_transition_v3_database


create_synthetic_v3_database = create_pre_transition_v3_database


CURRENT = SchoolYear(
    "SY-CURRENT",
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
STAMP = datetime(2025, 7, 1, 8, 0, tzinfo=UTC)
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
    return V3Student(
        student_id=student_id,
        first_name="Test",
        last_name=student_id,
        notes="",
        active=True,
        created_at=STAMP,
        updated_at=STAMP,
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
        course_name=course_id,
        assignment_status=StudentAssignmentStatus.ENROLLED,
    )


def _preview():
    sources = SchoolYearTransitionPreviewSources(
        school_years=(CURRENT,),
        students=(_student("S-1"), _student("S-2"), _student("S-3")),
        memberships=(
            _membership("S-1", "C-1"),
            _membership("S-2", "C-2"),
            _membership("S-3", "C-3"),
        ),
        courses=(
            COURSES[0],
            COURSES[1],
            COURSES[3],
        ),
        groups=GROUPS,
    )
    return SchoolYearTransitionPreviewProjector().project(
        planned_school_year=PLANNED,
        sources=sources,
    )


def _plan() -> SchoolYearTransitionPlan:
    return SchoolYearTransitionPlan.from_preview(
        _preview(),
        courses=COURSES,
        groups=GROUPS,
    )


def _item(plan: SchoolYearTransitionPlan, student_id: str):
    return next(item for item in plan.items if item.student_id == student_id)


def test_initial_plan_copies_preview_without_mutating_or_reordering_it() -> None:
    preview = _preview()
    original = preview

    plan = SchoolYearTransitionPlan.from_preview(
        preview,
        courses=COURSES,
        groups=GROUPS,
    )
    edited = plan.select_other_course("S-1", "C-2-B")

    assert preview == original
    assert tuple(item.student_id for item in plan.items) == tuple(
        item.student_id for item in preview.items
    )
    assert _item(plan, "S-1").edited is False
    assert _item(edited, "S-1").edited is True
    assert _item(plan, "S-1").target_course_id == "C-2"
    assert plan.current_school_year_label == "2025/26"
    assert plan.planned_school_year_label == "2026/27"
    assert plan.planned_school_year_start_date == date(2026, 8, 1)
    assert _item(plan, "S-1").current_group_id == "G-A"
    assert _item(plan, "S-1").current_group_name == "Gruppe A"
    assert _item(plan, "S-1").current_course_id == "C-1"
    assert _item(plan, "S-1").current_course_name == "C-1"
    assert _item(plan, "S-1").current_year_level == 1


def test_plan_preserves_a_caller_supplied_preview_item_order() -> None:
    preview = _preview()
    reordered = replace(
        preview,
        items=(preview.items[2], preview.items[0], preview.items[1]),
    )

    plan = SchoolYearTransitionPlan.from_preview(
        reordered,
        courses=COURSES,
        groups=GROUPS,
    )

    assert tuple(item.student_id for item in plan.items) == (
        "S-3",
        "S-1",
        "S-2",
    )


def test_proposed_course_can_be_consciously_accepted() -> None:
    accepted = _plan().accept_proposed_course("S-1")
    item = _item(accepted, "S-1")

    assert item.student_id == "S-1"
    assert item.target_course_id == "C-2"
    assert item.course_decision is (
        SchoolYearTransitionCourseDecision.ACCEPT_PROPOSAL
    )
    assert item.edited is True
    assert item.resolved is True


def test_other_existing_course_and_group_are_transient_choices() -> None:
    changed = (
        _plan()
        .select_other_course("S-1", "C-2-B")
        .select_other_group("S-1", "G-B")
    )
    item = _item(changed, "S-1")

    assert item.target_course_id == "C-2-B"
    assert item.target_group_id == "G-B"
    assert item.target_status is SchoolYearTransitionPlanTargetStatus.OTHER_COURSE
    assert item.course_decision is (
        SchoolYearTransitionCourseDecision.SELECT_OTHER_COURSE
    )
    assert item.group_decision is (
        SchoolYearTransitionGroupDecision.SELECT_OTHER_GROUP
    )
    assert item.resolved is True


def test_original_issues_remain_auditable_after_conscious_edit() -> None:
    plan = _plan()
    original = _item(plan, "S-3")

    repeated = _item(
        plan.repeat_year_level_three("S-3", "C-3"),
        "S-3",
    )

    assert original.original_warning_codes == ()
    assert original.original_blocker_codes == (
        "YEAR_LEVEL_THREE_SELECTION_REQUIRED",
    )
    assert repeated.original_warning_codes == original.original_warning_codes
    assert repeated.original_blocker_codes == original.original_blocker_codes


def test_proposed_group_can_be_consciously_retained() -> None:
    retained = _item(_plan().keep_proposed_group("S-1"), "S-1")

    assert retained.target_group_id == "G-A"
    assert retained.group_decision is (
        SchoolYearTransitionGroupDecision.KEEP_PROPOSAL
    )
    assert retained.edited is True


def test_current_active_group_can_be_kept_without_a_group_proposal() -> None:
    preview = _preview()
    without_group_proposal = replace(
        preview,
        items=(
            replace(
                preview.items[0],
                proposed_group_id=None,
                proposed_group_name=None,
                resolved=False,
            ),
            *preview.items[1:],
        ),
    )
    plan = SchoolYearTransitionPlan.from_preview(
        without_group_proposal,
        courses=COURSES,
        groups=GROUPS,
    )

    kept = _item(plan.keep_current_group("S-1"), "S-1")

    assert kept.target_group_id == "G-A"
    assert kept.target_group_name == "Gruppe A"
    assert kept.group_decision is (
        SchoolYearTransitionGroupDecision.KEEP_CURRENT_GROUP
    )
    assert kept.edited is True


def test_course_three_remains_unresolved_until_a_conscious_choice() -> None:
    plan = _plan()
    item = _item(plan, "S-3")

    assert item.target_status is SchoolYearTransitionPlanTargetStatus.UNRESOLVED
    assert item.course_decision is SchoolYearTransitionCourseDecision.UNCHANGED
    assert item.edited is False
    assert item.resolved is False

    repeated = _item(
        plan.repeat_year_level_three("S-3", "C-3"),
        "S-3",
    )
    assert repeated.target_status is (
        SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE
    )
    assert repeated.resolved is True
    assert repeated.edited is True


def test_exited_has_no_course_or_group_claim() -> None:
    plan = _plan().mark_exited("S-3")
    exited = _item(plan, "S-3")

    assert exited.target_status is SchoolYearTransitionPlanTargetStatus.EXITED
    assert exited.target_course_id is None
    assert exited.target_course_name is None
    assert exited.target_group_id is None
    assert exited.target_group_name is None
    assert exited.group_decision is (
        SchoolYearTransitionGroupDecision.NOT_APPLICABLE
    )
    assert exited.resolved is True
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="exited_plan_has_no_group_decision",
    ):
        plan.select_other_group("S-3", "G-B")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="exited_plan_has_no_group_decision",
    ):
        plan.keep_proposed_group("S-3")


def test_unresolved_is_a_conscious_but_still_incomplete_decision() -> None:
    unresolved = _item(_plan().leave_unresolved("S-1"), "S-1")

    assert unresolved.edited is True
    assert unresolved.course_decision is (
        SchoolYearTransitionCourseDecision.LEAVE_UNRESOLVED
    )
    assert unresolved.target_status is (
        SchoolYearTransitionPlanTargetStatus.UNRESOLVED
    )
    assert unresolved.target_course_id is None
    assert unresolved.resolved is False


def test_only_existing_active_options_can_be_selected() -> None:
    inactive_course = SchoolYearTransitionCourse(
        "C-INACTIVE",
        "Inaktiv",
        False,
        2,
    )
    plan = SchoolYearTransitionPlan.from_preview(
        _preview(),
        courses=COURSES + (inactive_course,),
        groups=GROUPS,
    )

    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="active_plan_course_not_found",
    ):
        plan.select_other_course("S-1", "C-INACTIVE")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="active_plan_group_not_found",
    ):
        plan.select_other_group("S-1", "G-MISSING")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="repeat_course_must_have_year_level_three",
    ):
        plan.repeat_year_level_three("S-3", "C-2")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="repeat_decision_requires_year_level_three_source",
    ):
        plan.repeat_year_level_three("S-1", "C-3")


def test_bulk_edits_create_one_new_plan_and_preserve_unselected_items() -> None:
    initial = _plan()
    unchanged = _item(initial, "S-2")

    course_plan = initial.set_target_course_for_students(("S-1",), "C-2-B")
    assert course_plan is not initial
    assert _item(course_plan, "S-1").target_course_id == "C-2-B"
    assert _item(course_plan, "S-2") == unchanged

    group_plan = course_plan.set_target_group_for_students(
        ("S-1", "S-2"),
        "G-B",
    )
    assert group_plan is not course_plan
    assert _item(group_plan, "S-1").target_group_id == "G-B"
    assert _item(group_plan, "S-2").target_group_id == "G-B"
    assert _item(group_plan, "S-3").target_group_id == "G-A"

    exited_plan = group_plan.mark_students_exited(("S-1",))
    exited = _item(exited_plan, "S-1")
    assert exited.target_course_id is None
    assert exited.target_group_id is None

    unresolved_plan = exited_plan.leave_students_unresolved(("S-2",))
    unresolved = _item(unresolved_plan, "S-2")
    assert unresolved.target_course_id is None
    assert unresolved.target_group_id == "G-B"
    assert unresolved.target_status is (
        SchoolYearTransitionPlanTargetStatus.UNRESOLVED
    )


def test_bulk_course_three_and_active_option_rules_are_fail_closed() -> None:
    plan = _plan()
    repeated_plan = plan.set_target_course_for_students(("S-3",), "C-3")
    repeated = _item(repeated_plan, "S-3")
    assert repeated.target_status is (
        SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE
    )

    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="repeat_course_must_have_year_level_three",
    ):
        plan.set_target_course_for_students(("S-3",), "C-2")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="active_plan_course_not_found",
    ):
        plan.set_target_course_for_students(("S-1",), "C-INACTIVE")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="active_plan_group_not_found",
    ):
        plan.set_target_group_for_students(("S-1",), "G-MISSING")
    with pytest.raises(
        SchoolYearTransitionPlanError,
        match="plan_student_not_found",
    ):
        plan.mark_students_exited(("S-MISSING",))


def test_global_preview_issues_remain_auditable_and_block_completeness() -> None:
    overlapping = PlannedSchoolYear(
        "2026/27",
        date(2026, 7, 31),
        date(2027, 7, 30),
    )
    sources = SchoolYearTransitionPreviewSources(
        school_years=(CURRENT,),
        students=(_student("S-1"),),
        memberships=(_membership("S-1", "C-1"),),
        courses=(COURSES[0], COURSES[1], COURSES[3]),
        groups=GROUPS,
    )
    preview = SchoolYearTransitionPreviewProjector().project(
        planned_school_year=overlapping,
        sources=sources,
    )
    plan = SchoolYearTransitionPlan.from_preview(
        preview,
        courses=COURSES,
        groups=GROUPS,
    )

    validation = plan.validate()

    assert plan.original_validation_issues == preview.validation_issues
    assert validation.complete is False
    assert (None, "NEW_SCHOOL_YEAR_OVERLAP") in tuple(
        (issue.student_id, issue.code) for issue in validation.issues
    )


def test_global_warning_remains_auditable_without_blocking_completeness() -> None:
    sources = SchoolYearTransitionPreviewSources(
        school_years=(CURRENT,),
        students=(_student("S-1"),),
        memberships=(_membership("S-1", "C-1"),),
        courses=(COURSES[0], COURSES[1], COURSES[3]),
        groups=GROUPS,
    )
    preview = SchoolYearTransitionPreviewProjector().project(
        planned_school_year=PLANNED,
        sources=sources,
    )
    warning = SchoolYearTransitionValidationIssue(
        "GLOBAL_WARNING",
        SchoolYearTransitionIssueSeverity.WARNING,
    )
    preview_with_warning = replace(
        preview,
        validation_issues=(warning,),
        executable=True,
    )
    plan = SchoolYearTransitionPlan.from_preview(
        preview_with_warning,
        courses=COURSES,
        groups=GROUPS,
    )

    validation = plan.validate()

    assert validation.issues[0].code == "GLOBAL_WARNING"
    assert validation.issues[0].severity is (
        SchoolYearTransitionIssueSeverity.WARNING
    )
    assert validation.complete is True


def test_validation_and_counts_are_deterministic() -> None:
    plan = _plan().mark_exited("S-2").repeat_year_level_three("S-3", "C-3")

    first = plan.validate()
    second = plan.validate()

    assert first == second
    assert first.complete is True
    assert first.issues == ()
    assert first.counts.student_count == 3
    assert first.counts.resolved_count == 3
    assert first.counts.advance_1_to_2_count == 1
    assert first.counts.advance_2_to_3_count == 0
    assert first.counts.repeat_year_level_three_count == 1
    assert first.counts.exited_count == 1
    assert first.counts.unresolved_count == 0
    assert first.counts.edited_count == 2


def test_transient_edit_does_not_change_sqlite(tmp_path: Path) -> None:
    path = create_synthetic_v3_database(tmp_path / "plan.sqlite")

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
        courses=(
            SchoolYearTransitionCourse(
                "CRS-TEST-1",
                "Testkurs 1",
                True,
                1,
            ),
            SchoolYearTransitionCourse(
                "CRS-TEST-2",
                "Testkurs 2",
                True,
                2,
            ),
            SchoolYearTransitionCourse(
                "CRS-TEST-3",
                "Testkurs 3",
                True,
                3,
            ),
        ),
        groups=(
            SchoolYearTransitionGroup(
                "GRP-TEST-A",
                "Testgruppe A",
                True,
            ),
        ),
    )
    changed = plan.mark_exited(preview.items[0].student_id)

    assert _item(changed, preview.items[0].student_id).edited is True
    assert snapshot() == before
