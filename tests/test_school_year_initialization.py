"""Focused SJ-2A tests for the pure V3 initialization domain."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import hashlib

import pytest

from src.core.records import StudentRecord
from src.core.school_year import (
    CourseYearLevelConfirmation,
    SchoolYear,
    SchoolYearDomainError,
    SchoolYearInitializationPlan,
    SchoolYearSchemaInformation,
    SchoolYearStatus,
    StudentAssignmentStatus,
    StudentMembershipAssignment,
    StudentMigrationClassification,
    StudentMigrationWarningCode,
    build_school_year_initialization_plan,
    build_school_year_initialization_preview,
    classify_v2_student,
)


SCHOOL_YEAR_ID = "SY-2025-26"
GROUP_ID = "GRP-000001"
COURSE_ID = "CRS-000001"
SECOND_COURSE_ID = "CRS-000002"


def _school_year(
    *,
    label: str = "2025/26",
    start_date: date = date(2025, 8, 1),
    end_date: date = date(2026, 7, 31),
    status: SchoolYearStatus = SchoolYearStatus.PLANNED,
) -> SchoolYear:
    return SchoolYear(
        school_year_id=SCHOOL_YEAR_ID,
        label=label,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )


def _student(
    *,
    student_id: str = "STD-000001",
    group_id: str = GROUP_ID,
    course_id: str = COURSE_ID,
    active: bool = True,
    archived_at: str | None = None,
    student_notes: str = "",
) -> StudentRecord:
    return StudentRecord(
        student_id=student_id,
        first_name="Mia",
        last_name="Müller",
        group_id=group_id,
        course_id=course_id,
        student_notes=student_notes,
        active=active,
        created_at="2025-08-01T08:00:00+00:00",
        updated_at="2025-08-01T08:00:00+00:00",
        archived_at=archived_at,
    )


def _classification(student: StudentRecord):
    return classify_v2_student(
        student,
        _school_year(),
        (GROUP_ID,),
        (COURSE_ID, SECOND_COURSE_ID),
    )


def _plan(
    *,
    students: tuple[StudentRecord, ...] | None = None,
    label: str = "2025/26",
    confirmations: tuple[CourseYearLevelConfirmation, ...] | None = None,
) -> SchoolYearInitializationPlan:
    school_year = _school_year(label=label)
    source_students = students or (
        _student(student_id="STD-000002", course_id=SECOND_COURSE_ID),
        _student(
            student_id="STD-000001",
            active=False,
            archived_at="2026-07-31T10:00:00",
        ),
    )
    preview = build_school_year_initialization_preview(
        source_students,
        school_year,
        (GROUP_ID,),
        (COURSE_ID, SECOND_COURSE_ID),
    )
    return build_school_year_initialization_plan(
        initial_school_year=school_year,
        confirmed_course_year_levels=confirmations
        or (
            CourseYearLevelConfirmation(SECOND_COURSE_ID, 2),
            CourseYearLevelConfirmation(COURSE_ID, 1),
        ),
        preview=preview,
        source_schema=SchoolYearSchemaInformation(2, "a" * 64),
        target_schema=SchoolYearSchemaInformation(3, "b" * 64),
        source_state_sha256="c" * 64,
    )


def test_school_year_accepts_valid_inclusive_period() -> None:
    school_year = _school_year()

    assert school_year.start_date == date(2025, 8, 1)
    assert school_year.end_date == date(2026, 7, 31)
    assert school_year.status is SchoolYearStatus.PLANNED


def test_school_year_rejects_start_after_end() -> None:
    with pytest.raises(SchoolYearDomainError) as caught:
        _school_year(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 31),
        )

    assert caught.value.code == "school_year_date_range_invalid"


def test_school_year_accepts_single_day_boundary() -> None:
    school_year = _school_year(
        start_date=date(2025, 8, 1),
        end_date=date(2025, 8, 1),
        status=SchoolYearStatus.CURRENT,
    )

    assert school_year.start_date == school_year.end_date
    assert school_year.status is SchoolYearStatus.CURRENT


def test_school_year_rejects_unknown_status() -> None:
    with pytest.raises(SchoolYearDomainError) as caught:
        SchoolYear(
            SCHOOL_YEAR_ID,
            "2025/26",
            date(2025, 8, 1),
            date(2026, 7, 31),
            "automatic",  # type: ignore[arg-type]
        )

    assert caught.value.code == "school_year_status_invalid"


def test_assignment_uses_inclusive_interval_and_enrolled_membership() -> None:
    assignment = StudentMembershipAssignment(
        student_id="STD-000001",
        school_year_id=SCHOOL_YEAR_ID,
        group_id=GROUP_ID,
        course_id=COURSE_ID,
        assignment_status=StudentAssignmentStatus.ENROLLED,
        valid_from=date(2025, 8, 1),
        valid_to=date(2025, 8, 1),
    )

    assert assignment.valid_from == assignment.valid_to


def test_assignment_rejects_reversed_interval() -> None:
    with pytest.raises(SchoolYearDomainError) as caught:
        StudentMembershipAssignment(
            student_id="STD-000001",
            school_year_id=SCHOOL_YEAR_ID,
            group_id=GROUP_ID,
            course_id=COURSE_ID,
            assignment_status=StudentAssignmentStatus.ENROLLED,
            valid_from=date(2025, 8, 2),
            valid_to=date(2025, 8, 1),
        )

    assert caught.value.code == "assignment_date_range_invalid"


def test_enrolled_requires_group_and_course() -> None:
    with pytest.raises(SchoolYearDomainError) as caught:
        StudentMembershipAssignment(
            student_id="STD-000001",
            school_year_id=SCHOOL_YEAR_ID,
            group_id=None,
            course_id=COURSE_ID,
            assignment_status=StudentAssignmentStatus.ENROLLED,
            valid_from=date(2025, 8, 1),
            valid_to=date(2026, 7, 31),
        )

    assert caught.value.code == "assignment_group_id_required"


def test_exited_has_no_current_membership() -> None:
    assignment = StudentMembershipAssignment(
        student_id="STD-000001",
        school_year_id=SCHOOL_YEAR_ID,
        group_id=None,
        course_id=None,
        assignment_status=StudentAssignmentStatus.EXITED,
        valid_from=date(2025, 8, 1),
        valid_to=date(2026, 7, 31),
    )

    assert assignment.assignment_status is StudentAssignmentStatus.EXITED

    with pytest.raises(SchoolYearDomainError) as caught:
        replace(assignment, group_id=GROUP_ID)
    assert caught.value.code == "exited_assignment_has_membership"


def test_active_student_is_migratable_for_full_initial_year() -> None:
    result = _classification(_student())

    assert (
        result.classification.classification
        is StudentMigrationClassification.ACTIVE_MIGRATABLE
    )
    assert result.classification.warning_codes == ()
    assert result.initial_assignment is not None
    assert result.initial_assignment.valid_from == date(2025, 8, 1)
    assert result.initial_assignment.valid_to == date(2026, 7, 31)


def test_archived_student_is_migratable_until_day_before_archive() -> None:
    result = _classification(
        _student(active=False, archived_at="2026-02-10T14:00:00")
    )

    assert (
        result.classification.classification
        is StudentMigrationClassification.ARCHIVED_MIGRATABLE
    )
    assert result.initial_assignment is not None
    assert result.initial_assignment.assignment_status is StudentAssignmentStatus.ENROLLED
    assert result.initial_assignment.valid_to == date(2026, 2, 9)


def test_unknown_group_has_membership_reference_category() -> None:
    result = _classification(_student(group_id="GRP-UNKNOWN"))

    assert (
        result.classification.classification
        is StudentMigrationClassification.MEMBERSHIP_REFERENCE_INVALID
    )
    assert result.classification.warning_codes == (
        StudentMigrationWarningCode.GROUP_ID_UNKNOWN,
    )
    assert result.initial_assignment is None


def test_unknown_course_has_membership_reference_category() -> None:
    result = _classification(_student(course_id="CRS-UNKNOWN"))

    assert (
        result.classification.classification
        is StudentMigrationClassification.MEMBERSHIP_REFERENCE_INVALID
    )
    assert result.classification.warning_codes == (
        StudentMigrationWarningCode.COURSE_ID_UNKNOWN,
    )


def test_activity_archive_conflict_has_priority_and_keeps_secondary_warning() -> None:
    result = _classification(
        _student(
            group_id="GRP-UNKNOWN",
            active=True,
            archived_at="2026-02-10T14:00:00",
        )
    )

    assert (
        result.classification.classification
        is StudentMigrationClassification.ACTIVITY_ARCHIVE_CONFLICT
    )
    assert set(result.classification.warning_codes) == {
        StudentMigrationWarningCode.ACTIVE_WITH_ARCHIVED_AT,
        StudentMigrationWarningCode.GROUP_ID_UNKNOWN,
    }


def test_inactive_student_without_archived_at_is_temporally_unresolved() -> None:
    result = _classification(_student(active=False, archived_at=None))

    assert (
        result.classification.classification
        is StudentMigrationClassification.TEMPORAL_CONTEXT_UNRESOLVED
    )
    assert result.classification.warning_codes == (
        StudentMigrationWarningCode.ARCHIVED_AT_MISSING,
    )


def test_archived_at_on_start_date_has_empty_interval_and_is_unresolved() -> None:
    result = _classification(
        _student(active=False, archived_at="2025-08-01T12:00:00")
    )

    assert (
        result.classification.classification
        is StudentMigrationClassification.TEMPORAL_CONTEXT_UNRESOLVED
    )
    assert StudentMigrationWarningCode.ARCHIVED_AT_ON_OR_BEFORE_START in (
        result.classification.warning_codes
    )


def test_archived_at_on_end_date_is_migratable() -> None:
    result = _classification(
        _student(active=False, archived_at="2026-07-31T12:00:00")
    )

    assert (
        result.classification.classification
        is StudentMigrationClassification.ARCHIVED_MIGRATABLE
    )
    assert result.initial_assignment is not None
    assert result.initial_assignment.valid_to == date(2026, 7, 30)


@pytest.mark.parametrize(
    ("archived_at", "warning"),
    (
        (
            "2025-07-31T12:00:00",
            StudentMigrationWarningCode.ARCHIVED_AT_ON_OR_BEFORE_START,
        ),
        (
            "2026-08-01T12:00:00",
            StudentMigrationWarningCode.ARCHIVED_AT_AFTER_END,
        ),
    ),
)
def test_archived_at_outside_initial_year_is_unresolved(
    archived_at: str,
    warning: StudentMigrationWarningCode,
) -> None:
    result = _classification(
        _student(active=False, archived_at=archived_at)
    )

    assert (
        result.classification.classification
        is StudentMigrationClassification.TEMPORAL_CONTEXT_UNRESOLVED
    )
    assert warning in result.classification.warning_codes
    assert result.initial_assignment is None


def test_invalid_archived_at_is_unresolved() -> None:
    result = _classification(
        _student(active=False, archived_at="not-an-iso-timestamp")
    )

    assert (
        result.classification.classification
        is StudentMigrationClassification.TEMPORAL_CONTEXT_UNRESOLVED
    )
    assert result.classification.warning_codes == (
        StudentMigrationWarningCode.ARCHIVED_AT_INVALID,
    )


def test_preview_classifies_every_student_exactly_once() -> None:
    students = (
        _student(student_id="STD-000003", active=False, archived_at=None),
        _student(student_id="STD-000001"),
        _student(student_id="STD-000002", course_id="CRS-UNKNOWN"),
    )
    preview = build_school_year_initialization_preview(
        students,
        _school_year(),
        (GROUP_ID,),
        (COURSE_ID, SECOND_COURSE_ID),
    )

    assert tuple(
        item.student_id for item in preview.student_classifications
    ) == ("STD-000001", "STD-000002", "STD-000003")
    assert len(preview.student_classifications) == len(students)
    assert len(preview.assignment_proposals) == 1
    assert len(preview.blockers) == 2


def test_same_input_has_same_serialization_and_hash_independent_of_input_order() -> None:
    students = (
        _student(student_id="STD-000002", course_id=SECOND_COURSE_ID),
        _student(
            student_id="STD-000001",
            active=False,
            archived_at="2026-07-31T10:00:00",
        ),
    )
    first = _plan(students=students)
    second = _plan(
        students=tuple(reversed(students)),
        confirmations=(
            CourseYearLevelConfirmation(COURSE_ID, 1),
            CourseYearLevelConfirmation(SECOND_COURSE_ID, 2),
        ),
    )

    assert first.canonical_json() == second.canonical_json()
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.plan_sha256 == second.plan_sha256
    assert (
        hashlib.sha256(first.canonical_bytes()).hexdigest()
        == first.plan_sha256
    )


def test_changed_input_has_different_hash() -> None:
    first = _plan()
    changed = _plan(label="2025–26")

    assert first.canonical_bytes() != changed.canonical_bytes()
    assert first.plan_sha256 != changed.plan_sha256


def test_plan_format_two_binds_source_state_sha256() -> None:
    first = _plan()
    changed = replace(first, source_state_sha256="d" * 64)

    assert first.format_version == 2
    assert first.canonical_dict()["source_state_sha256"] == "c" * 64
    assert changed.plan_sha256 != first.plan_sha256


def test_canonical_serialization_normalizes_unicode_to_nfc() -> None:
    nfc_plan = _plan(label="Schuljahr Mü")
    nfd_plan = _plan(label="Schuljahr Mu\u0308")

    assert nfc_plan.canonical_bytes() == nfd_plan.canonical_bytes()
    assert nfc_plan.plan_sha256 == nfd_plan.plan_sha256
    assert b"Mu\\u0308" not in nfd_plan.canonical_bytes()


@pytest.mark.parametrize(
    "unregistered_context",
    (
        "OBSERVATION_PRESENT",
        "REPORT_PRESENT",
        "LEARNING_CONFERENCE_PRESENT",
    ),
)
def test_observation_report_and_leg_context_never_influence_classification(
    unregistered_context: str,
) -> None:
    baseline_student = _student()
    student_with_unregistered_context = replace(
        baseline_student,
        student_notes=unregistered_context,
    )

    baseline = _classification(baseline_student)
    with_context = _classification(student_with_unregistered_context)

    assert with_context == baseline
    plan = _plan(students=(student_with_unregistered_context,))
    assert unregistered_context not in plan.canonical_json()
    assert "Mia" not in plan.canonical_json()
    assert "Müller" not in plan.canonical_json()
