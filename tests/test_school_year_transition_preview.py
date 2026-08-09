from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest

from src.application.school_year_transition_preview import (
    SchoolYearTransitionPreviewProjector,
    SchoolYearTransitionPreviewService,
)
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
    SchoolYearTransitionMembership,
    SchoolYearTransitionPreviewSources,
    SchoolYearTransitionTargetStatus,
)
from tests.helpers.synthetic_v4 import create_pre_transition_v4_database


create_synthetic_v4_database = create_pre_transition_v4_database


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


def _student(
    student_id: str,
    *,
    archived: bool = False,
) -> V3Student:
    return V3Student(
        student_id=student_id,
        first_name="Test",
        last_name=student_id,
        notes="",
        active=not archived,
        created_at=STAMP,
        updated_at=STAMP,
        archived_at=STAMP if archived else None,
    )


def _membership(
    student_id: str,
    course_id: str,
    *,
    group_id: str = "G-A",
    status: StudentAssignmentStatus = StudentAssignmentStatus.ENROLLED,
) -> SchoolYearTransitionMembership:
    enrolled = status is StudentAssignmentStatus.ENROLLED
    return SchoolYearTransitionMembership(
        student_id=student_id,
        school_year_id=CURRENT.school_year_id,
        group_id=group_id if enrolled else None,
        group_name="Gruppe A" if enrolled else None,
        course_id=course_id if enrolled else None,
        course_name=course_id if enrolled else None,
        assignment_status=status,
    )


def _sources(
    *,
    students: tuple[V3Student, ...] | None = None,
    memberships: tuple[SchoolYearTransitionMembership, ...] | None = None,
    courses: tuple[SchoolYearTransitionCourse, ...] | None = None,
    groups: tuple[SchoolYearTransitionGroup, ...] | None = None,
    school_years: tuple[SchoolYear, ...] = (CURRENT,),
) -> SchoolYearTransitionPreviewSources:
    return SchoolYearTransitionPreviewSources(
        school_years=school_years,
        students=(
            students
            if students is not None
            else (_student("S-1"), _student("S-2"), _student("S-3"))
        ),
        memberships=(
            memberships
            if memberships is not None
            else (
                _membership("S-1", "C-1"),
                _membership("S-2", "C-2"),
                _membership("S-3", "C-3"),
            )
        ),
        courses=(
            courses
            if courses is not None
            else (
                SchoolYearTransitionCourse("C-1", "Kurs 1", True, 1),
                SchoolYearTransitionCourse("C-2", "Kurs 2", True, 2),
                SchoolYearTransitionCourse("C-3", "Kurs 3", True, 3),
            )
        ),
        groups=(
            groups
            if groups is not None
            else (SchoolYearTransitionGroup("G-A", "Gruppe A", True),)
        ),
    )


def _project(
    sources: SchoolYearTransitionPreviewSources | None = None,
    planned: PlannedSchoolYear = PLANNED,
):
    return SchoolYearTransitionPreviewProjector().project(
        planned_school_year=planned,
        sources=sources or _sources(),
    )


def _item(preview, student_id: str):
    return next(item for item in preview.items if item.student_id == student_id)


def test_courses_advance_only_by_canonical_year_level() -> None:
    preview = _project()

    first = _item(preview, "S-1")
    second = _item(preview, "S-2")
    third = _item(preview, "S-3")
    assert first.target_status is SchoolYearTransitionTargetStatus.ADVANCE_1_TO_2
    assert first.proposed_course_id == "C-2"
    assert first.proposed_year_level == 2
    assert second.target_status is SchoolYearTransitionTargetStatus.ADVANCE_2_TO_3
    assert second.proposed_course_id == "C-3"
    assert second.proposed_year_level == 3
    assert third.target_status is SchoolYearTransitionTargetStatus.UNRESOLVED
    assert third.blocker_codes == ("YEAR_LEVEL_THREE_SELECTION_REQUIRED",)
    assert preview.advance_1_to_2_count == 1
    assert preview.advance_2_to_3_count == 1
    assert preview.repeater_count == 0
    assert preview.unresolved_count == 1
    assert preview.executable is False


def test_preview_plan_receives_preview_and_options_from_one_service_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "preview-plan.sqlite"
    create_synthetic_v4_database(database_path)
    connection_count = 0
    write_actions: list[int] = []
    write_codes = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
    }

    def connect() -> sqlite3.Connection:
        nonlocal connection_count
        connection_count += 1
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row

        def authorize(
            action: int,
            _argument_1: str | None,
            _argument_2: str | None,
            _database: str | None,
            _trigger: str | None,
        ) -> int:
            if action in write_codes:
                write_actions.append(action)
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
        return connection

    service = SchoolYearTransitionPreviewService(connect)
    captured: dict[str, object] = {}
    original = SchoolYearTransitionPlan.from_preview

    def capture(
        preview,
        *,
        courses,
        groups,
        source_sha256,
    ):
        captured["preview"] = preview
        captured["courses"] = courses
        captured["groups"] = groups
        captured["source_sha256"] = source_sha256
        return original(
            preview,
            courses=courses,
            groups=groups,
            source_sha256=source_sha256,
        )

    with patch.object(
        SchoolYearTransitionPlan,
        "from_preview",
        side_effect=capture,
    ) as build_plan:
        plan = service.preview_plan(
            label="2026/27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
        )

    build_plan.assert_called_once()
    assert connection_count == 1
    assert write_actions == []
    preview = captured["preview"]
    assert preview.planned_school_year.label == plan.planned_school_year_label
    assert tuple(item.student_id for item in preview.items) == tuple(
        item.student_id for item in plan.items
    )
    assert tuple(course.course_id for course in captured["courses"]) == tuple(
        course.course_id for course in plan.available_courses
    )
    assert tuple(group.group_id for group in captured["groups"]) == tuple(
        group.group_id for group in plan.available_groups
    )
    assert captured["source_sha256"] == plan.source_sha256
    assert len(plan.source_sha256) == 64


def test_student_display_name_uses_v3_master_data_and_keeps_stable_id() -> None:
    named_student = V3Student(
        student_id="STABLE-ID",
        first_name="Mara",
        last_name="Sommer",
        notes="",
        active=True,
        created_at=STAMP,
        updated_at=STAMP,
        archived_at=None,
    )
    sources = _sources(
        students=(named_student,),
        memberships=(_membership("STABLE-ID", "C-1"),),
    )

    item = _project(sources).items[0]

    assert item.student_id == "STABLE-ID"
    assert item.student_display_name == "Mara Sommer"


def test_missing_student_master_data_is_neutral_and_never_shows_id_as_name() -> None:
    sources = _sources(
        students=(),
        memberships=(_membership("ORPHAN-STUDENT-ID", "C-1"),),
    )

    preview = _project(sources)

    assert preview.student_count == 1
    assert preview.items[0].student_id == "ORPHAN-STUDENT-ID"
    assert preview.items[0].student_display_name == "Name nicht verfügbar"
    assert preview.items[0].student_display_name != preview.items[0].student_id
    assert "STUDENT_MASTER_DATA_MISSING" in preview.items[0].blocker_codes
    assert preview.items[0].resolved is False


def test_multiple_target_courses_require_conscious_selection() -> None:
    sources = _sources(
        courses=_sources().courses
        + (SchoolYearTransitionCourse("C-2-B", "Noch Stufe 2", True, 2),)
    )

    item = _item(_project(sources), "S-1")

    assert item.proposed_course_id is None
    assert item.blocker_codes == ("TARGET_COURSE_AMBIGUOUS",)
    assert item.resolved is False


def test_missing_target_course_is_unresolved() -> None:
    sources = _sources(
        courses=tuple(course for course in _sources().courses if course.year_level != 2)
    )

    item = _item(_project(sources), "S-1")

    assert item.proposed_course_id is None
    assert item.blocker_codes == ("TARGET_COURSE_MISSING",)


def test_group_is_proposed_unchanged() -> None:
    item = _item(_project(), "S-1")

    assert item.current_group_id == "G-A"
    assert item.proposed_group_id == "G-A"
    assert item.proposed_group_name == "Gruppe A"


def test_preview_is_executable_only_without_unresolved_or_blocking_cases() -> None:
    sources = _sources(
        students=(_student("S-1"), _student("S-2")),
        memberships=(
            _membership("S-1", "C-1"),
            _membership("S-2", "C-2"),
        ),
    )

    preview = _project(sources)

    assert preview.unresolved_count == 0
    assert preview.validation_issues == ()
    assert preview.executable is True


@pytest.mark.parametrize(
    ("student", "memberships", "expected_code"),
    (
        (
            _student("S-X", archived=True),
            (_membership("S-X", "C-1"),),
            "STUDENT_ARCHIVED",
        ),
        (
            _student("S-X"),
            (
                _membership(
                    "S-X",
                    "C-1",
                    status=StudentAssignmentStatus.EXITED,
                ),
            ),
            "STUDENT_EXITED",
        ),
        (_student("S-X"), (), "CURRENT_ASSIGNMENT_MISSING"),
        (
            _student("S-X"),
            (_membership("S-X", "C-1"), _membership("S-X", "C-2")),
            "CURRENT_ASSIGNMENT_AMBIGUOUS",
        ),
    ),
)
def test_non_automatic_student_cases_remain_visible_and_unresolved(
    student: V3Student,
    memberships: tuple[SchoolYearTransitionMembership, ...],
    expected_code: str,
) -> None:
    sources = _sources(students=(student,), memberships=memberships)

    preview = _project(sources)

    assert tuple(item.student_id for item in preview.items) == ("S-X",)
    assert expected_code in preview.items[0].blocker_codes
    assert preview.items[0].resolved is False
    if expected_code == "STUDENT_ARCHIVED":
        assert preview.items[0].proposed_course_id is None
        assert preview.items[0].proposed_group_id is None


def test_missing_year_level_is_unresolved() -> None:
    courses = (
        SchoolYearTransitionCourse("C-1", "Kurs ohne Stufe", True, None),
        SchoolYearTransitionCourse("C-2", "Kurs 2", True, 2),
    )
    sources = _sources(
        students=(_student("S-X"),),
        memberships=(_membership("S-X", "C-1"),),
        courses=courses,
    )

    item = _project(sources).items[0]

    assert item.current_year_level is None
    assert item.blocker_codes == ("CURRENT_YEAR_LEVEL_INVALID",)


@pytest.mark.parametrize(
    ("sources", "expected_code"),
    (
        (
            _sources(
                groups=(SchoolYearTransitionGroup("G-A", "Gruppe A", False),)
            ),
            "CURRENT_GROUP_INVALID",
        ),
        (
            _sources(
                courses=(
                    SchoolYearTransitionCourse("C-1", "Kurs 1", False, 1),
                    SchoolYearTransitionCourse("C-2", "Kurs 2", True, 2),
                    SchoolYearTransitionCourse("C-3", "Kurs 3", True, 3),
                )
            ),
            "CURRENT_COURSE_INVALID",
        ),
    ),
)
def test_invalid_current_references_block_assignment(
    sources: SchoolYearTransitionPreviewSources,
    expected_code: str,
) -> None:
    assert expected_code in _item(_project(sources), "S-1").blocker_codes


def test_overlapping_new_school_year_is_a_global_blocker() -> None:
    planned = PlannedSchoolYear(
        "2026/27",
        date(2026, 7, 31),
        date(2027, 7, 30),
    )

    preview = _project(planned=planned)

    codes = tuple(issue.code for issue in preview.validation_issues)
    assert "NEW_SCHOOL_YEAR_OVERLAP" in codes
    assert "NEW_SCHOOL_YEAR_NOT_AFTER_CURRENT" in codes
    assert preview.executable is False


def test_gap_between_school_years_is_a_global_blocker() -> None:
    planned = PlannedSchoolYear(
        "2026/27",
        date(2026, 8, 2),
        date(2027, 8, 1),
    )

    preview = _project(planned=planned)

    assert "SCHOOL_YEAR_GAP" in tuple(
        issue.code for issue in preview.validation_issues
    )


def test_exactly_one_current_school_year_is_required() -> None:
    missing = _project(_sources(school_years=()))
    ambiguous = _project(
        _sources(
            school_years=(
                CURRENT,
                replace(CURRENT, school_year_id="SY-OTHER"),
            )
        )
    )

    assert "CURRENT_SCHOOL_YEAR_MISSING" in tuple(
        issue.code for issue in missing.validation_issues
    )
    assert "CURRENT_SCHOOL_YEAR_AMBIGUOUS" in tuple(
        issue.code for issue in ambiguous.validation_issues
    )
    assert all(not item.resolved for item in missing.items)
    assert all(not item.resolved for item in ambiguous.items)


def test_preview_contains_every_student_exactly_once() -> None:
    students = tuple(_student(f"S-{number}") for number in range(8, 0, -1))
    memberships = (
        _membership("S-1", "C-1"),
        _membership("S-2", "C-2"),
        _membership("S-3", "C-3"),
        _membership(
            "S-4",
            "C-1",
            status=StudentAssignmentStatus.EXITED,
        ),
        _membership("S-5", "C-1"),
        _membership("S-5", "C-2"),
    )

    preview = _project(_sources(students=students, memberships=memberships))

    assert preview.student_count == 8
    assert tuple(item.student_id for item in preview.items) == tuple(
        f"S-{number}" for number in range(1, 9)
    )


def test_projection_is_deterministic_for_reordered_sources() -> None:
    sources = _sources()
    reordered = replace(
        sources,
        school_years=tuple(reversed(sources.school_years)),
        students=tuple(reversed(sources.students)),
        memberships=tuple(reversed(sources.memberships)),
        courses=tuple(reversed(sources.courses)),
        groups=tuple(reversed(sources.groups)),
    )

    assert _project(sources) == _project(reordered)


def test_sqlite_preview_uses_no_write_statement(tmp_path: Path) -> None:
    path = create_synthetic_v4_database(tmp_path / "preview.sqlite")
    write_actions: list[int] = []
    write_codes = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
    }

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row

        def authorize(
            action: int,
            _argument_1: str | None,
            _argument_2: str | None,
            _database: str | None,
            _trigger: str | None,
        ) -> int:
            if action in write_codes:
                write_actions.append(action)
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
        return connection

    with sqlite3.connect(path) as connection:
        counts_before = (
            connection.execute("SELECT count(*) FROM students").fetchone()[0],
            connection.execute(
                "SELECT count(*) FROM student_school_year_assignments"
            ).fetchone()[0],
            connection.execute(
                "SELECT count(*) FROM school_year_transitions"
            ).fetchone()[0],
        )

    preview = SchoolYearTransitionPreviewService(connect).preview(
        label="2026/27",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 7, 31),
    )

    with sqlite3.connect(path) as connection:
        counts_after = (
            connection.execute("SELECT count(*) FROM students").fetchone()[0],
            connection.execute(
                "SELECT count(*) FROM student_school_year_assignments"
            ).fetchone()[0],
            connection.execute(
                "SELECT count(*) FROM school_year_transitions"
            ).fetchone()[0],
        )
    assert preview.student_count == 3
    assert tuple(item.student_display_name for item in preview.items) == (
        "Testkind Eins",
        "Testkind Zwei",
        "Testkind Drei",
    )
    assert counts_after == counts_before
    assert write_actions == []
