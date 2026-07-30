"""Pure, transient editing model for a later school-year transition UI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from typing import TypeVar

from src.core.school_year_transition import (
    SchoolYearTransitionCourse,
    SchoolYearTransitionGroup,
    SchoolYearTransitionIssueSeverity,
    SchoolYearTransitionPreview,
    SchoolYearTransitionPreviewItem,
    SchoolYearTransitionTargetStatus,
    SchoolYearTransitionValidationIssue,
)


_Option = TypeVar("_Option")


class SchoolYearTransitionPlanError(ValueError):
    """Reject an invalid transient editing request without side effects."""


class SchoolYearTransitionPlanTargetStatus(str, Enum):
    """Current transient target decision for one student."""

    ADVANCE_1_TO_2 = "advance_1_to_2"
    ADVANCE_2_TO_3 = "advance_2_to_3"
    OTHER_COURSE = "other_course"
    REPEAT_YEAR_LEVEL_THREE = "repeat_year_level_three"
    EXITED = "exited"
    UNRESOLVED = "unresolved"


class SchoolYearTransitionCourseDecision(str, Enum):
    """Conscious course decision recorded only in the transient plan."""

    UNCHANGED = "unchanged"
    ACCEPT_PROPOSAL = "accept_proposal"
    SELECT_OTHER_COURSE = "select_other_course"
    REPEAT_YEAR_LEVEL_THREE = "repeat_year_level_three"
    EXITED = "exited"
    LEAVE_UNRESOLVED = "leave_unresolved"


class SchoolYearTransitionGroupDecision(str, Enum):
    """Conscious group decision recorded only in the transient plan."""

    UNCHANGED = "unchanged"
    KEEP_PROPOSAL = "keep_proposal"
    SELECT_OTHER_GROUP = "select_other_group"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPlanItem:
    """One immutable snapshot of a student's transient target decision."""

    student_id: str
    student_display_name: str
    target_group_id: str | None
    target_group_name: str | None
    target_course_id: str | None
    target_course_name: str | None
    target_status: SchoolYearTransitionPlanTargetStatus
    original_warning_codes: tuple[str, ...]
    original_blocker_codes: tuple[str, ...]
    resolved: bool
    edited: bool
    course_decision: SchoolYearTransitionCourseDecision
    group_decision: SchoolYearTransitionGroupDecision
    original_proposed_group_id: str | None
    original_proposed_group_name: str | None
    original_proposed_course_id: str | None
    original_proposed_course_name: str | None
    original_target_status: SchoolYearTransitionTargetStatus
    original_current_year_level: int | None


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPlanValidationIssue:
    """Deterministic global or student-owned transient-plan issue."""

    student_id: str | None
    code: str
    severity: SchoolYearTransitionIssueSeverity


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPlanCounts:
    """Deterministic counts derived only from the current transient items."""

    student_count: int
    resolved_count: int
    advance_1_to_2_count: int
    advance_2_to_3_count: int
    other_course_count: int
    repeat_year_level_three_count: int
    exited_count: int
    unresolved_count: int
    edited_count: int


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPlanValidation:
    """Complete validation result without execution semantics."""

    issues: tuple[SchoolYearTransitionPlanValidationIssue, ...]
    counts: SchoolYearTransitionPlanCounts
    complete: bool


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPlan:
    """Immutable aggregate whose edits never touch repositories or SQLite."""

    items: tuple[SchoolYearTransitionPlanItem, ...]
    available_courses: tuple[SchoolYearTransitionCourse, ...]
    available_groups: tuple[SchoolYearTransitionGroup, ...]
    original_validation_issues: tuple[
        SchoolYearTransitionValidationIssue,
        ...,
    ]

    @classmethod
    def from_preview(
        cls,
        preview: SchoolYearTransitionPreview,
        *,
        courses: tuple[SchoolYearTransitionCourse, ...],
        groups: tuple[SchoolYearTransitionGroup, ...],
    ) -> "SchoolYearTransitionPlan":
        """Copy one preview without mutating or reordering it."""
        available_courses = _active_courses(courses)
        available_groups = _active_groups(groups)
        return cls(
            items=tuple(_plan_item(item) for item in preview.items),
            available_courses=available_courses,
            available_groups=available_groups,
            original_validation_issues=preview.validation_issues,
        )

    def accept_proposed_course(
        self,
        student_id: str,
    ) -> "SchoolYearTransitionPlan":
        """Consciously retain the original automatic course proposal."""
        item = self._item(student_id)
        if item.original_proposed_course_id is None:
            raise SchoolYearTransitionPlanError("proposed_course_missing")
        course = self._course(item.original_proposed_course_id)
        updated = replace(
            item,
            target_course_id=course.course_id,
            target_course_name=course.course_name,
            target_status=_plan_target_status(item.original_target_status),
            course_decision=SchoolYearTransitionCourseDecision.ACCEPT_PROPOSAL,
            edited=True,
        )
        return self._replace(_with_resolution(updated))

    def select_other_course(
        self,
        student_id: str,
        course_id: str,
    ) -> "SchoolYearTransitionPlan":
        """Consciously choose another existing active course."""
        item = self._item(student_id)
        if course_id == item.original_proposed_course_id:
            raise SchoolYearTransitionPlanError(
                "other_course_must_differ_from_proposal"
            )
        course = self._course(course_id)
        updated = replace(
            item,
            target_course_id=course.course_id,
            target_course_name=course.course_name,
            target_status=SchoolYearTransitionPlanTargetStatus.OTHER_COURSE,
            course_decision=(
                SchoolYearTransitionCourseDecision.SELECT_OTHER_COURSE
            ),
            edited=True,
        )
        return self._replace(_with_resolution(updated))

    def repeat_year_level_three(
        self,
        student_id: str,
        course_id: str,
    ) -> "SchoolYearTransitionPlan":
        """Consciously choose an existing active level-three course."""
        item = self._item(student_id)
        if item.original_current_year_level != 3:
            raise SchoolYearTransitionPlanError(
                "repeat_decision_requires_year_level_three_source"
            )
        course = self._course(course_id)
        if course.year_level != 3:
            raise SchoolYearTransitionPlanError(
                "repeat_course_must_have_year_level_three"
            )
        updated = replace(
            item,
            target_course_id=course.course_id,
            target_course_name=course.course_name,
            target_status=(
                SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE
            ),
            course_decision=(
                SchoolYearTransitionCourseDecision.REPEAT_YEAR_LEVEL_THREE
            ),
            edited=True,
        )
        return self._replace(_with_resolution(updated))

    def mark_exited(self, student_id: str) -> "SchoolYearTransitionPlan":
        """Record a conscious exit without a course or group claim."""
        item = self._item(student_id)
        updated = replace(
            item,
            target_group_id=None,
            target_group_name=None,
            target_course_id=None,
            target_course_name=None,
            target_status=SchoolYearTransitionPlanTargetStatus.EXITED,
            course_decision=SchoolYearTransitionCourseDecision.EXITED,
            group_decision=SchoolYearTransitionGroupDecision.NOT_APPLICABLE,
            edited=True,
        )
        return self._replace(_with_resolution(updated))

    def leave_unresolved(self, student_id: str) -> "SchoolYearTransitionPlan":
        """Consciously leave the target unresolved without choosing a course."""
        item = self._item(student_id)
        updated = replace(
            item,
            target_course_id=None,
            target_course_name=None,
            target_status=SchoolYearTransitionPlanTargetStatus.UNRESOLVED,
            course_decision=(
                SchoolYearTransitionCourseDecision.LEAVE_UNRESOLVED
            ),
            edited=True,
            resolved=False,
        )
        return self._replace(updated)

    def keep_proposed_group(
        self,
        student_id: str,
    ) -> "SchoolYearTransitionPlan":
        """Consciously retain the original group proposal."""
        item = self._item(student_id)
        _require_group_applicable(item)
        if item.original_proposed_group_id is None:
            raise SchoolYearTransitionPlanError("proposed_group_missing")
        group = self._group(item.original_proposed_group_id)
        updated = replace(
            item,
            target_group_id=group.group_id,
            target_group_name=group.group_name,
            group_decision=SchoolYearTransitionGroupDecision.KEEP_PROPOSAL,
            edited=True,
        )
        return self._replace(_with_resolution(updated))

    def select_other_group(
        self,
        student_id: str,
        group_id: str,
    ) -> "SchoolYearTransitionPlan":
        """Consciously choose another existing active group."""
        item = self._item(student_id)
        _require_group_applicable(item)
        if group_id == item.original_proposed_group_id:
            raise SchoolYearTransitionPlanError(
                "other_group_must_differ_from_proposal"
            )
        group = self._group(group_id)
        updated = replace(
            item,
            target_group_id=group.group_id,
            target_group_name=group.group_name,
            group_decision=SchoolYearTransitionGroupDecision.SELECT_OTHER_GROUP,
            edited=True,
        )
        return self._replace(_with_resolution(updated))

    def validate(self) -> SchoolYearTransitionPlanValidation:
        """Return deterministic structural validation and counts."""
        global_issues = tuple(
            SchoolYearTransitionPlanValidationIssue(
                None,
                issue.code,
                issue.severity,
            )
            for issue in self.original_validation_issues
            if issue.student_id is None
        )
        item_issues = tuple(
            SchoolYearTransitionPlanValidationIssue(
                item.student_id,
                code,
                SchoolYearTransitionIssueSeverity.BLOCKER,
            )
            for item in self.items
            for code in _item_issue_codes(item)
        )
        issues = global_issues + item_issues
        counts = SchoolYearTransitionPlanCounts(
            student_count=len(self.items),
            resolved_count=sum(item.resolved for item in self.items),
            advance_1_to_2_count=_count_status(
                self.items,
                SchoolYearTransitionPlanTargetStatus.ADVANCE_1_TO_2,
            ),
            advance_2_to_3_count=_count_status(
                self.items,
                SchoolYearTransitionPlanTargetStatus.ADVANCE_2_TO_3,
            ),
            other_course_count=_count_status(
                self.items,
                SchoolYearTransitionPlanTargetStatus.OTHER_COURSE,
            ),
            repeat_year_level_three_count=_count_status(
                self.items,
                SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE,
            ),
            exited_count=_count_status(
                self.items,
                SchoolYearTransitionPlanTargetStatus.EXITED,
            ),
            unresolved_count=sum(not item.resolved for item in self.items),
            edited_count=sum(item.edited for item in self.items),
        )
        return SchoolYearTransitionPlanValidation(
            issues=issues,
            counts=counts,
            complete=not any(
                issue.severity
                is SchoolYearTransitionIssueSeverity.BLOCKER
                for issue in issues
            ),
        )

    def _item(self, student_id: str) -> SchoolYearTransitionPlanItem:
        matches = tuple(
            item for item in self.items if item.student_id == student_id
        )
        if len(matches) != 1:
            raise SchoolYearTransitionPlanError("plan_student_not_found")
        return matches[0]

    def _course(self, course_id: str) -> SchoolYearTransitionCourse:
        matches = tuple(
            course
            for course in self.available_courses
            if course.course_id == course_id
        )
        if len(matches) != 1:
            raise SchoolYearTransitionPlanError(
                "active_plan_course_not_found"
            )
        return matches[0]

    def _group(self, group_id: str) -> SchoolYearTransitionGroup:
        matches = tuple(
            group
            for group in self.available_groups
            if group.group_id == group_id
        )
        if len(matches) != 1:
            raise SchoolYearTransitionPlanError(
                "active_plan_group_not_found"
            )
        return matches[0]

    def _replace(
        self,
        updated: SchoolYearTransitionPlanItem,
    ) -> "SchoolYearTransitionPlan":
        return replace(
            self,
            items=tuple(
                updated if item.student_id == updated.student_id else item
                for item in self.items
            ),
        )


_NON_DECISION_BLOCKERS = frozenset(
    {
        "CURRENT_SCHOOL_YEAR_UNAVAILABLE",
        "STUDENT_MASTER_DATA_MISSING",
        "STUDENT_ARCHIVED",
        "CURRENT_ASSIGNMENT_MISSING",
        "CURRENT_ASSIGNMENT_AMBIGUOUS",
        "CURRENT_ASSIGNMENT_STATUS_INVALID",
    }
)


def _active_courses(
    courses: tuple[SchoolYearTransitionCourse, ...],
) -> tuple[SchoolYearTransitionCourse, ...]:
    return _unique_options(
        tuple(course for course in courses if course.active),
        identifier=lambda course: course.course_id,
        error_code="duplicate_plan_course",
    )


def _active_groups(
    groups: tuple[SchoolYearTransitionGroup, ...],
) -> tuple[SchoolYearTransitionGroup, ...]:
    return _unique_options(
        tuple(group for group in groups if group.active),
        identifier=lambda group: group.group_id,
        error_code="duplicate_plan_group",
    )


def _unique_options(
    options: tuple[_Option, ...],
    *,
    identifier: Callable[[_Option], str],
    error_code: str,
) -> tuple[_Option, ...]:
    sorted_options = tuple(sorted(options, key=identifier))
    identifiers = tuple(identifier(option) for option in sorted_options)
    if len(identifiers) != len(set(identifiers)):
        raise SchoolYearTransitionPlanError(error_code)
    return sorted_options


def _plan_item(
    item: SchoolYearTransitionPreviewItem,
) -> SchoolYearTransitionPlanItem:
    return SchoolYearTransitionPlanItem(
        student_id=item.student_id,
        student_display_name=item.student_display_name,
        target_group_id=item.proposed_group_id,
        target_group_name=item.proposed_group_name,
        target_course_id=item.proposed_course_id,
        target_course_name=item.proposed_course_name,
        target_status=_plan_target_status(item.target_status),
        original_warning_codes=item.warning_codes,
        original_blocker_codes=item.blocker_codes,
        resolved=item.resolved,
        edited=False,
        course_decision=SchoolYearTransitionCourseDecision.UNCHANGED,
        group_decision=SchoolYearTransitionGroupDecision.UNCHANGED,
        original_proposed_group_id=item.proposed_group_id,
        original_proposed_group_name=item.proposed_group_name,
        original_proposed_course_id=item.proposed_course_id,
        original_proposed_course_name=item.proposed_course_name,
        original_target_status=item.target_status,
        original_current_year_level=item.current_year_level,
    )


def _plan_target_status(
    status: SchoolYearTransitionTargetStatus,
) -> SchoolYearTransitionPlanTargetStatus:
    return SchoolYearTransitionPlanTargetStatus(status.value)


def _with_resolution(
    item: SchoolYearTransitionPlanItem,
) -> SchoolYearTransitionPlanItem:
    return replace(item, resolved=not _item_issue_codes(item))


def _require_group_applicable(
    item: SchoolYearTransitionPlanItem,
) -> None:
    if item.target_status is SchoolYearTransitionPlanTargetStatus.EXITED:
        raise SchoolYearTransitionPlanError(
            "exited_plan_has_no_group_decision"
        )


def _item_issue_codes(
    item: SchoolYearTransitionPlanItem,
) -> tuple[str, ...]:
    issues = [
        code
        for code in item.original_blocker_codes
        if code in _NON_DECISION_BLOCKERS
    ]
    if item.target_status is SchoolYearTransitionPlanTargetStatus.UNRESOLVED:
        issues.append("PLAN_TARGET_UNRESOLVED")
    elif item.target_status is not SchoolYearTransitionPlanTargetStatus.EXITED:
        if item.target_course_id is None:
            issues.append("PLAN_TARGET_COURSE_MISSING")
        if item.target_group_id is None:
            issues.append("PLAN_TARGET_GROUP_MISSING")
    return tuple(dict.fromkeys(issues))


def _count_status(
    items: tuple[SchoolYearTransitionPlanItem, ...],
    status: SchoolYearTransitionPlanTargetStatus,
) -> int:
    return sum(item.target_status is status for item in items)
