"""Focused tests for the retained school-year and assignment domain."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.core.school_year import (
    SchoolYear,
    SchoolYearDomainError,
    SchoolYearStatus,
    StudentAssignmentStatus,
    StudentMembershipAssignment,
)


def test_school_year_accepts_inclusive_valid_range() -> None:
    school_year = SchoolYear(
        "SY-2025-26",
        "2025/26",
        date(2025, 8, 1),
        date(2026, 7, 31),
        "current",
    )

    assert school_year.status is SchoolYearStatus.CURRENT
    assert school_year.start_date == date(2025, 8, 1)
    assert school_year.end_date == date(2026, 7, 31)


@pytest.mark.parametrize(
    ("values", "code"),
    (
        (
            ("", "2025/26", date(2025, 8, 1), date(2026, 7, 31), "current"),
            "school_year_id_invalid",
        ),
        (
            ("SY-1", " ", date(2025, 8, 1), date(2026, 7, 31), "current"),
            "school_year_label_invalid",
        ),
        (
            ("SY-1", "2025/26", date(2026, 8, 1), date(2026, 7, 31), "current"),
            "school_year_date_range_invalid",
        ),
        (
            ("SY-1", "2025/26", date(2025, 8, 1), date(2026, 7, 31), "open"),
            "school_year_status_invalid",
        ),
    ),
)
def test_school_year_rejects_invalid_values(
    values: tuple[object, ...],
    code: str,
) -> None:
    with pytest.raises(SchoolYearDomainError, match=code) as error:
        SchoolYear(*values)

    assert error.value.code == code


def test_enrolled_assignment_requires_group_and_course() -> None:
    assignment = StudentMembershipAssignment(
        "STD-1",
        "SY-1",
        "GRP-1",
        "CRS-1",
        "enrolled",
        date(2025, 8, 1),
        date(2026, 7, 31),
    )

    assert assignment.assignment_status is StudentAssignmentStatus.ENROLLED

    with pytest.raises(
        SchoolYearDomainError,
        match="assignment_group_id_required",
    ):
        StudentMembershipAssignment(
            "STD-1",
            "SY-1",
            None,
            "CRS-1",
            "enrolled",
            date(2025, 8, 1),
            date(2026, 7, 31),
        )


def test_exited_assignment_has_no_membership() -> None:
    assignment = StudentMembershipAssignment(
        "STD-1",
        "SY-1",
        None,
        None,
        StudentAssignmentStatus.EXITED,
        date(2026, 3, 1),
        date(2026, 7, 31),
    )

    assert assignment.assignment_status is StudentAssignmentStatus.EXITED

    with pytest.raises(
        SchoolYearDomainError,
        match="exited_assignment_has_membership",
    ):
        StudentMembershipAssignment(
            "STD-1",
            "SY-1",
            "GRP-1",
            None,
            "exited",
            date(2026, 3, 1),
            date(2026, 7, 31),
        )


def test_assignment_rejects_reversed_interval() -> None:
    with pytest.raises(
        SchoolYearDomainError,
        match="assignment_date_range_invalid",
    ):
        StudentMembershipAssignment(
            "STD-1",
            "SY-1",
            "GRP-1",
            "CRS-1",
            "enrolled",
            date(2026, 7, 31),
            date(2025, 8, 1),
        )


def test_domain_values_are_immutable() -> None:
    school_year = SchoolYear(
        "SY-1",
        "2025/26",
        date(2025, 8, 1),
        date(2026, 7, 31),
        SchoolYearStatus.CURRENT,
    )

    with pytest.raises(FrozenInstanceError):
        school_year.label = "changed"  # type: ignore[misc]
