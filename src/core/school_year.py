"""Pure domain values for school years and dated student assignments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class SchoolYearDomainError(ValueError):
    """Reject an invalid school-year domain value without storage access."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class SchoolYearStatus(str, Enum):
    """Allowed lifecycle states of a school year."""

    PLANNED = "planned"
    CURRENT = "current"
    CLOSED = "closed"


class StudentAssignmentStatus(str, Enum):
    """Allowed membership states inside one school-year interval."""

    ENROLLED = "enrolled"
    EXITED = "exited"


@dataclass(frozen=True, slots=True)
class SchoolYear:
    """One explicitly supplied inclusive school-year period."""

    school_year_id: str
    label: str
    start_date: date
    end_date: date
    status: SchoolYearStatus

    def __post_init__(self) -> None:
        _require_identifier(self.school_year_id, "school_year_id_invalid")
        _require_text(self.label, "school_year_label_invalid")
        _require_date(self.start_date, "school_year_start_date_invalid")
        _require_date(self.end_date, "school_year_end_date_invalid")
        object.__setattr__(
            self,
            "status",
            _enum_value(
                self.status,
                SchoolYearStatus,
                "school_year_status_invalid",
            ),
        )
        if self.start_date > self.end_date:
            raise SchoolYearDomainError("school_year_date_range_invalid")


@dataclass(frozen=True, slots=True)
class StudentMembershipAssignment:
    """One inclusive membership interval inside one school year."""

    student_id: str
    school_year_id: str
    group_id: str | None
    course_id: str | None
    assignment_status: StudentAssignmentStatus
    valid_from: date
    valid_to: date

    def __post_init__(self) -> None:
        _require_identifier(self.student_id, "assignment_student_id_invalid")
        _require_identifier(
            self.school_year_id,
            "assignment_school_year_id_invalid",
        )
        _require_date(self.valid_from, "assignment_valid_from_invalid")
        _require_date(self.valid_to, "assignment_valid_to_invalid")
        status = _enum_value(
            self.assignment_status,
            StudentAssignmentStatus,
            "assignment_status_invalid",
        )
        object.__setattr__(self, "assignment_status", status)
        if self.valid_from > self.valid_to:
            raise SchoolYearDomainError("assignment_date_range_invalid")
        if status is StudentAssignmentStatus.ENROLLED:
            _require_identifier(self.group_id, "assignment_group_id_required")
            _require_identifier(self.course_id, "assignment_course_id_required")
        elif self.group_id is not None or self.course_id is not None:
            raise SchoolYearDomainError("exited_assignment_has_membership")


def _require_identifier(value: object, code: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchoolYearDomainError(code)


def _require_text(value: object, code: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchoolYearDomainError(code)


def _require_date(value: object, code: str) -> None:
    if not isinstance(value, date):
        raise SchoolYearDomainError(code)


def _enum_value(value: object, enum_type: type[Enum], code: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise SchoolYearDomainError(code) from error
