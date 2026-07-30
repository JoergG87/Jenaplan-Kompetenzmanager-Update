"""Pure domain values for a read-only school-year transition preview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .school_year import SchoolYear, StudentAssignmentStatus, V3Student


class SchoolYearTransitionIssueSeverity(str, Enum):
    """Severity of a transition-preview validation result."""

    WARNING = "warning"
    BLOCKER = "blocker"


class SchoolYearTransitionTargetStatus(str, Enum):
    """Proposed target status before any conscious editing in SJ-3B."""

    ADVANCE_1_TO_2 = "advance_1_to_2"
    ADVANCE_2_TO_3 = "advance_2_to_3"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class PlannedSchoolYear:
    """Caller-supplied, not-yet-persisted target school year."""

    label: str
    start_date: date
    end_date: date


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionGroup:
    """Group source used only while building a transition preview."""

    group_id: str
    group_name: str
    active: bool


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionCourse:
    """Course source with the only allowed progression attribute."""

    course_id: str
    course_name: str
    active: bool
    year_level: int | None


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionMembership:
    """One current-year assignment candidate at the current year end."""

    student_id: str
    school_year_id: str
    group_id: str | None
    group_name: str | None
    course_id: str | None
    course_name: str | None
    assignment_status: StudentAssignmentStatus


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionValidationIssue:
    """Stable validation code with optional student ownership."""

    code: str
    severity: SchoolYearTransitionIssueSeverity
    student_id: str | None = None


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreviewItem:
    """Complete read-only proposal for exactly one V3 student."""

    student_id: str
    current_school_year_id: str | None
    current_school_year_label: str | None
    current_group_id: str | None
    current_group_name: str | None
    current_course_id: str | None
    current_course_name: str | None
    current_year_level: int | None
    new_school_year_label: str
    proposed_group_id: str | None
    proposed_group_name: str | None
    proposed_course_id: str | None
    proposed_course_name: str | None
    proposed_year_level: int | None
    target_status: SchoolYearTransitionTargetStatus
    warning_codes: tuple[str, ...]
    blocker_codes: tuple[str, ...]
    resolved: bool


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreview:
    """Complete deterministic SJ-3A projection without execution capability."""

    current_school_year: SchoolYear | None
    planned_school_year: PlannedSchoolYear
    items: tuple[SchoolYearTransitionPreviewItem, ...]
    validation_issues: tuple[SchoolYearTransitionValidationIssue, ...]
    student_count: int
    advance_1_to_2_count: int
    advance_2_to_3_count: int
    repeater_count: int
    unresolved_count: int
    executable: bool


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreviewSources:
    """All caller-owned sources required by the pure preview projector."""

    school_years: tuple[SchoolYear, ...]
    students: tuple[V3Student, ...]
    memberships: tuple[SchoolYearTransitionMembership, ...]
    courses: tuple[SchoolYearTransitionCourse, ...]
    groups: tuple[SchoolYearTransitionGroup, ...]
