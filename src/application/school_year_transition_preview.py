"""Pure projection and read-only SQLite composition for SJ-3A."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import date, timedelta
import sqlite3

from src.application.school_year_transition_plan import SchoolYearTransitionPlan
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
    SchoolYearTransitionPreview,
    SchoolYearTransitionPreviewItem,
    SchoolYearTransitionPreviewSources,
    SchoolYearTransitionTargetStatus,
    SchoolYearTransitionValidationIssue,
)
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionPreviewRepository,
)
from src.core.sqlite_school_year_assignment import SchoolYearRepository


ConnectionFactory = Callable[[], sqlite3.Connection]
_BLOCKER = SchoolYearTransitionIssueSeverity.BLOCKER


class SchoolYearTransitionPreviewProjector:
    """Build a deterministic proposal without storage or side effects."""

    def project(
        self,
        *,
        planned_school_year: PlannedSchoolYear,
        sources: SchoolYearTransitionPreviewSources,
    ) -> SchoolYearTransitionPreview:
        global_issues, current = _validate_school_years(
            planned_school_year,
            sources.school_years,
        )
        memberships_by_student: dict[
            str, list[SchoolYearTransitionMembership]
        ] = defaultdict(list)
        for membership in sources.memberships:
            memberships_by_student[membership.student_id].append(membership)
        courses_by_id = {course.course_id: course for course in sources.courses}
        groups_by_id = {group.group_id: group for group in sources.groups}
        target_courses: dict[int, tuple[SchoolYearTransitionCourse, ...]] = {
            year_level: tuple(
                sorted(
                    (
                        course
                        for course in sources.courses
                        if (
                            course.active
                            and _valid_year_level(course.year_level)
                            and course.year_level == year_level
                        )
                    ),
                    key=lambda course: course.course_id,
                )
            )
            for year_level in (1, 2, 3)
        }

        students_by_id = {
            student.student_id: student
            for student in sources.students
        }
        student_ids = tuple(
            sorted(set(students_by_id) | set(memberships_by_student))
        )
        items = tuple(
            self._project_student(
                student_id=student_id,
                student=students_by_id.get(student_id),
                current=current,
                planned_school_year=planned_school_year,
                memberships=tuple(
                    sorted(
                        memberships_by_student.get(student_id, ()),
                        key=_membership_sort_key,
                    )
                ),
                courses_by_id=courses_by_id,
                groups_by_id=groups_by_id,
                target_courses=target_courses,
            )
            for student_id in student_ids
        )
        item_issues = tuple(
            SchoolYearTransitionValidationIssue(code, _BLOCKER, item.student_id)
            for item in items
            for code in item.blocker_codes
        )
        issues = tuple(global_issues) + item_issues
        unresolved_count = sum(not item.resolved for item in items)
        return SchoolYearTransitionPreview(
            current_school_year=current,
            planned_school_year=planned_school_year,
            items=items,
            validation_issues=issues,
            student_count=len(items),
            advance_1_to_2_count=sum(
                item.resolved
                and item.target_status
                is SchoolYearTransitionTargetStatus.ADVANCE_1_TO_2
                for item in items
            ),
            advance_2_to_3_count=sum(
                item.resolved
                and item.target_status
                is SchoolYearTransitionTargetStatus.ADVANCE_2_TO_3
                for item in items
            ),
            repeater_count=0,
            unresolved_count=unresolved_count,
            executable=(
                unresolved_count == 0
                and not any(issue.severity is _BLOCKER for issue in issues)
            ),
        )

    def _project_student(
        self,
        *,
        student_id: str,
        student: V3Student | None,
        current: SchoolYear | None,
        planned_school_year: PlannedSchoolYear,
        memberships: tuple[SchoolYearTransitionMembership, ...],
        courses_by_id: dict[str, SchoolYearTransitionCourse],
        groups_by_id: dict[str, SchoolYearTransitionGroup],
        target_courses: dict[int, tuple[SchoolYearTransitionCourse, ...]],
    ) -> SchoolYearTransitionPreviewItem:
        blockers: list[str] = []
        membership = memberships[0] if len(memberships) == 1 else None
        current_group_id = membership.group_id if membership is not None else None
        current_group_name = (
            membership.group_name if membership is not None else None
        )
        current_course_id = (
            membership.course_id if membership is not None else None
        )
        current_course_name = (
            membership.course_name if membership is not None else None
        )
        current_year_level: int | None = None
        proposed_group_id: str | None = None
        proposed_group_name: str | None = None
        proposed_course: SchoolYearTransitionCourse | None = None
        proposed_year_level: int | None = None
        target_status = SchoolYearTransitionTargetStatus.UNRESOLVED

        if current is None:
            blockers.append("CURRENT_SCHOOL_YEAR_UNAVAILABLE")
        if student is None:
            blockers.append("STUDENT_MASTER_DATA_MISSING")
        student_archived = (
            student is not None
            and (not student.active or student.archived_at is not None)
        )
        if student_archived:
            blockers.append("STUDENT_ARCHIVED")
        if len(memberships) == 0:
            blockers.append("CURRENT_ASSIGNMENT_MISSING")
        elif len(memberships) > 1:
            blockers.append("CURRENT_ASSIGNMENT_AMBIGUOUS")
        elif membership is not None:
            if membership.assignment_status is StudentAssignmentStatus.EXITED:
                blockers.append("STUDENT_EXITED")
            elif membership.assignment_status is not StudentAssignmentStatus.ENROLLED:
                blockers.append("CURRENT_ASSIGNMENT_STATUS_INVALID")
            else:
                group = (
                    groups_by_id.get(membership.group_id)
                    if membership.group_id is not None
                    else None
                )
                if group is None or not group.active:
                    blockers.append("CURRENT_GROUP_INVALID")

                course = (
                    courses_by_id.get(membership.course_id)
                    if membership.course_id is not None
                    else None
                )
                if course is None or not course.active:
                    blockers.append("CURRENT_COURSE_INVALID")
                elif not _valid_year_level(course.year_level):
                    blockers.append("CURRENT_YEAR_LEVEL_INVALID")
                else:
                    current_year_level = int(course.year_level)
                source_valid = (
                    current is not None
                    and not student_archived
                    and group is not None
                    and group.active
                    and course is not None
                    and course.active
                    and _valid_year_level(course.year_level)
                )
                if source_valid:
                    proposed_group_id = group.group_id
                    proposed_group_name = group.group_name
                    if current_year_level == 3:
                        blockers.append("YEAR_LEVEL_THREE_SELECTION_REQUIRED")
                    elif current_year_level is not None:
                        proposed_year_level = current_year_level + 1
                        candidates = target_courses[proposed_year_level]
                        if len(candidates) == 0:
                            blockers.append("TARGET_COURSE_MISSING")
                        elif len(candidates) > 1:
                            blockers.append("TARGET_COURSE_AMBIGUOUS")
                        else:
                            proposed_course = candidates[0]
                            target_status = (
                                SchoolYearTransitionTargetStatus.ADVANCE_1_TO_2
                                if current_year_level == 1
                                else SchoolYearTransitionTargetStatus.ADVANCE_2_TO_3
                            )

        blocker_codes = tuple(dict.fromkeys(blockers))
        return SchoolYearTransitionPreviewItem(
            student_id=student_id,
            student_display_name=_student_display_name(student),
            current_school_year_id=(
                current.school_year_id if current is not None else None
            ),
            current_school_year_label=current.label if current is not None else None,
            current_group_id=current_group_id,
            current_group_name=current_group_name,
            current_course_id=current_course_id,
            current_course_name=current_course_name,
            current_year_level=current_year_level,
            new_school_year_label=planned_school_year.label,
            proposed_group_id=proposed_group_id,
            proposed_group_name=proposed_group_name,
            proposed_course_id=(
                proposed_course.course_id if proposed_course is not None else None
            ),
            proposed_course_name=(
                proposed_course.course_name if proposed_course is not None else None
            ),
            proposed_year_level=proposed_year_level,
            target_status=target_status,
            warning_codes=(),
            blocker_codes=blocker_codes,
            resolved=not blocker_codes,
        )


class SchoolYearTransitionPreviewService:
    """Read all sources once and delegate to the pure SJ-3A projector."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory
        self._projector = SchoolYearTransitionPreviewProjector()

    def preview(
        self,
        *,
        label: str,
        start_date: date,
        end_date: date,
    ) -> SchoolYearTransitionPreview:
        preview, _ = self._preview_with_sources(
            label=label,
            start_date=start_date,
            end_date=end_date,
        )
        return preview

    def preview_plan(
        self,
        *,
        label: str,
        start_date: date,
        end_date: date,
    ) -> SchoolYearTransitionPlan:
        """Build one transient plan from the same read-only source snapshot."""
        preview, sources = self._preview_with_sources(
            label=label,
            start_date=start_date,
            end_date=end_date,
        )
        return SchoolYearTransitionPlan.from_preview(
            preview,
            courses=sources.courses,
            groups=sources.groups,
        )

    def _preview_with_sources(
        self,
        *,
        label: str,
        start_date: date,
        end_date: date,
    ) -> tuple[
        SchoolYearTransitionPreview,
        SchoolYearTransitionPreviewSources,
    ]:
        planned = PlannedSchoolYear(label, start_date, end_date)
        with closing(self._connection_factory()) as connection:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            before_changes = connection.total_changes
            school_years = tuple(
                SchoolYearRepository(connection).list_all()
            )
            current_years = tuple(
                school_year
                for school_year in school_years
                if school_year.status is SchoolYearStatus.CURRENT
            )
            current = current_years[0] if len(current_years) == 1 else None
            sources = SchoolYearTransitionPreviewRepository(
                connection
            ).read_sources(
                school_years=school_years,
                current_school_year=current,
            )
            if connection.total_changes != before_changes:
                raise RuntimeError("school_year_transition_preview_wrote_data")
            connection.rollback()
        return (
            self._projector.project(
                planned_school_year=planned,
                sources=sources,
            ),
            sources,
        )


def _validate_school_years(
    planned: PlannedSchoolYear,
    school_years: Sequence[SchoolYear],
) -> tuple[list[SchoolYearTransitionValidationIssue], SchoolYear | None]:
    issues: list[SchoolYearTransitionValidationIssue] = []
    current_years = tuple(
        school_year
        for school_year in school_years
        if school_year.status is SchoolYearStatus.CURRENT
    )
    current = current_years[0] if len(current_years) == 1 else None
    if not isinstance(planned.label, str) or not planned.label.strip():
        issues.append(
            SchoolYearTransitionValidationIssue(
                "NEW_SCHOOL_YEAR_LABEL_INVALID",
                _BLOCKER,
            )
        )
    if not isinstance(planned.start_date, date) or not isinstance(
        planned.end_date,
        date,
    ):
        issues.append(
            SchoolYearTransitionValidationIssue(
                "NEW_SCHOOL_YEAR_DATE_INVALID",
                _BLOCKER,
            )
        )
        return issues, current
    if planned.start_date > planned.end_date:
        issues.append(
            SchoolYearTransitionValidationIssue(
                "NEW_SCHOOL_YEAR_DATE_RANGE_INVALID",
                _BLOCKER,
            )
        )
    if len(current_years) == 0:
        issues.append(
            SchoolYearTransitionValidationIssue(
                "CURRENT_SCHOOL_YEAR_MISSING",
                _BLOCKER,
            )
        )
    elif len(current_years) > 1:
        issues.append(
            SchoolYearTransitionValidationIssue(
                "CURRENT_SCHOOL_YEAR_AMBIGUOUS",
                _BLOCKER,
            )
        )
    if any(
        not (
            existing.end_date < planned.start_date
            or existing.start_date > planned.end_date
        )
        for existing in school_years
    ):
        issues.append(
            SchoolYearTransitionValidationIssue(
                "NEW_SCHOOL_YEAR_OVERLAP",
                _BLOCKER,
            )
        )
    if current is not None:
        if planned.start_date <= current.end_date:
            issues.append(
                SchoolYearTransitionValidationIssue(
                    "NEW_SCHOOL_YEAR_NOT_AFTER_CURRENT",
                    _BLOCKER,
                )
            )
        if planned.start_date != current.end_date + timedelta(days=1):
            issues.append(
                SchoolYearTransitionValidationIssue(
                    "SCHOOL_YEAR_GAP",
                    _BLOCKER,
                )
            )
    return issues, current


def _valid_year_level(value: object) -> bool:
    return type(value) is int and value in (1, 2, 3)


def _student_display_name(student: V3Student | None) -> str:
    if student is None:
        return "Name nicht verfügbar"
    return f"{student.first_name.strip()} {student.last_name.strip()}"


def _membership_sort_key(
    membership: SchoolYearTransitionMembership,
) -> tuple[str, str, str, str]:
    return (
        membership.school_year_id,
        membership.group_id or "",
        membership.course_id or "",
        membership.assignment_status.value,
    )
