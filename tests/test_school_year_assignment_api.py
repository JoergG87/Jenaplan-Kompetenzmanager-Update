"""Contract tests for the isolated central final-V3 assignment API."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3

import pytest

from src.application.school_year_assignment import (
    ArchiveStudent,
    AssignmentApplicationError,
    ChangeStudentMembership,
    CreateStudentWithInitialEnrollment,
    EnrollStudent,
    ExitStudentFromSchoolYear,
    MembershipChangeStatus,
    SchoolYearAssignmentQueryService,
    UpdateStudentMasterData,
)
from src.core.final_v3_schema import FinalV3SchemaInitializer
from src.core.school_year import (
    AssignmentResolutionStatus,
    StudentAssignmentStatus,
    V3Student,
)
from src.core.sqlite_school_year_assignment import (
    SchoolYearAssignmentRepositoryError,
    SchoolYearRepository,
    StudentSchoolYearAssignmentRepository,
)
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v3_database,
)


AS_OF = date(2026, 1, 15)
NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


def _factory(path: Path):
    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    return connect


@pytest.fixture
def v3_database(tmp_path: Path) -> Path:
    return create_synthetic_v3_database(tmp_path / "assignment.sqlite")


def _assignment_rows(path: Path, student_id: str) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            connection.execute(
                """
                SELECT
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to
                FROM student_school_year_assignments
                WHERE student_id = ?
                ORDER BY valid_from, assignment_id
                """,
                (student_id,),
            ).fetchall()
        )


def test_school_year_repository_contract_has_no_hidden_transaction(
    v3_database: Path,
) -> None:
    connection = _factory(v3_database)()
    try:
        repository = SchoolYearRepository(connection)
        current = repository.require_current()
        assert repository.get_by_id(current.school_year_id) == current
        assert repository.get_current() == current
        assert repository.list_all() == (current,)
        assert not connection.in_transaction
    finally:
        connection.close()


def test_school_year_require_current_fails_closed(v3_database: Path) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            UPDATE school_years
            SET status = 'closed', closed_at = ?
            WHERE school_year_id = ?
            """,
            (NOW.isoformat(), SYNTHETIC_SCHOOL_YEAR_ID),
        )
    connection = _factory(v3_database)()
    try:
        with pytest.raises(SchoolYearAssignmentRepositoryError) as captured:
            SchoolYearRepository(connection).require_current()
        assert captured.value.code == "current_school_year_missing"
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("reference_date", "expected"),
    (
        (date(2025, 8, 1), AssignmentResolutionStatus.ENROLLED),
        (date(2026, 7, 31), AssignmentResolutionStatus.ENROLLED),
        (date(2025, 7, 31), AssignmentResolutionStatus.NO_ASSIGNMENT),
        (date(2026, 8, 1), AssignmentResolutionStatus.NO_ASSIGNMENT),
    ),
)
def test_assignment_resolution_uses_inclusive_boundaries_without_fallback(
    v3_database: Path,
    reference_date: date,
    expected: AssignmentResolutionStatus,
) -> None:
    projection = SchoolYearAssignmentQueryService(
        _factory(v3_database)
    ).assignment_at_date(SYNTHETIC_STUDENT_IDS[0], reference_date)
    assert projection.reference_date == reference_date
    assert projection.resolution_status is expected
    assert projection.visible_status_key == expected.value
    assert projection.accessible_name
    if expected is AssignmentResolutionStatus.NO_ASSIGNMENT:
        assert projection.assignment_id is None
        assert projection.school_year_id is None


def test_exit_is_resolved_neutrally_and_is_not_archive(v3_database: Path) -> None:
    ExitStudentFromSchoolYear(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-EXIT-001",
        now_provider=lambda: NOW,
    ).execute(SYNTHETIC_STUDENT_IDS[0], effective_on=AS_OF)
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    projection = service.assignment_at_date(SYNTHETIC_STUDENT_IDS[0], AS_OF)
    assert projection.resolution_status is AssignmentResolutionStatus.EXITED
    assert projection.assignment_status is StudentAssignmentStatus.EXITED
    assert projection.group_id is None
    assert projection.course_id is None
    assert projection.student_active is True
    assert projection.student_archived is False


def test_ambiguous_matches_are_never_silently_selected(
    v3_database: Path,
) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute("DROP TRIGGER trg_assignments_no_overlap_insert")
        connection.execute(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'enrolled', ?, ?, ?, ?)
            """,
            (
                "ASG-AMBIGUOUS",
                SYNTHETIC_STUDENT_IDS[0],
                SYNTHETIC_SCHOOL_YEAR_ID,
                "GRP-TEST-B",
                "CRS-TEST-2",
                "2025-12-01",
                "2026-02-01",
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    projection = service.assignment_at_date(SYNTHETIC_STUDENT_IDS[0], AS_OF)
    assert projection.resolution_status is AssignmentResolutionStatus.AMBIGUOUS
    assert projection.assignment_id is None
    assert projection.group_id is None
    assert projection.course_id is None
    current_group = service.current_memberships(
        as_of=AS_OF,
        group_id="GRP-TEST-A",
    )
    assert [item.student_id for item in current_group] == [
        SYNTHETIC_STUDENT_IDS[1]
    ]
    assert service.count_current_by_group(as_of=AS_OF) == {
        "GRP-TEST-A": 1,
        "GRP-TEST-B": 1,
    }


def test_archived_student_remains_historically_resolvable(
    v3_database: Path,
) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            UPDATE students
            SET active = 0, archived_at = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (
                "2026-08-05T09:00:00+00:00",
                "2026-08-05T09:00:00+00:00",
                SYNTHETIC_STUDENT_IDS[0],
            ),
        )
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    historical = service.assignment_at_date(
        SYNTHETIC_STUDENT_IDS[0],
        date(2026, 1, 15),
    )
    after_archive = service.assignment_at_date(
        SYNTHETIC_STUDENT_IDS[0],
        date(2026, 8, 6),
    )
    assert historical.resolution_status is AssignmentResolutionStatus.ENROLLED
    assert historical.student_archived is True
    assert after_archive.resolution_status is AssignmentResolutionStatus.STUDENT_ARCHIVED
    assert after_archive.assignment_id is None


def test_current_school_year_missing_is_explicit(v3_database: Path) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            UPDATE school_years
            SET status = 'closed', closed_at = ?
            WHERE school_year_id = ?
            """,
            (NOW.isoformat(), SYNTHETIC_SCHOOL_YEAR_ID),
        )
    projection = SchoolYearAssignmentQueryService(
        _factory(v3_database)
    ).current_membership(SYNTHETIC_STUDENT_IDS[0], as_of=AS_OF)
    assert (
        projection.resolution_status
        is AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING
    )
    assert projection.current_school_year_id is None


def test_membership_in_school_year_requires_date_inside_requested_year(
    v3_database: Path,
) -> None:
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    resolved = service.membership_in_school_year(
        SYNTHETIC_STUDENT_IDS[0],
        SYNTHETIC_SCHOOL_YEAR_ID,
        reference_date=AS_OF,
    )
    assert resolved.resolution_status is AssignmentResolutionStatus.ENROLLED
    with pytest.raises(AssignmentApplicationError) as captured:
        service.membership_in_school_year(
            SYNTHETIC_STUDENT_IDS[0],
            SYNTHETIC_SCHOOL_YEAR_ID,
            reference_date=date(2026, 8, 1),
        )
    assert captured.value.code == "reference_date_outside_school_year"


def test_last_known_is_only_used_by_explicit_method(v3_database: Path) -> None:
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    reference = date(2026, 8, 1)
    regular = service.assignment_at_date(SYNTHETIC_STUDENT_IDS[0], reference)
    historical = service.last_known_membership(
        SYNTHETIC_STUDENT_IDS[0],
        reference_date=reference,
    )
    assert regular.resolution_status is AssignmentResolutionStatus.NO_ASSIGNMENT
    assert historical.resolution_status is AssignmentResolutionStatus.ENROLLED
    assert historical.valid_to == date(2026, 7, 31)


def test_current_group_course_and_course_group_members(v3_database: Path) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            INSERT INTO course_groups(course_group_id, name, sort_order, active)
            VALUES ('CG-TEST', 'Testverbund', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO course_group_student_groups(
                course_group_id, student_group_id
            ) VALUES ('CG-TEST', 'GRP-TEST-A')
            """
        )
        connection.execute(
            """
            INSERT INTO course_group_courses(course_group_id, course_id)
            VALUES ('CG-TEST', 'CRS-TEST-1')
            """
        )
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    group = service.current_memberships(as_of=AS_OF, group_id="GRP-TEST-A")
    course = service.current_memberships(as_of=AS_OF, course_id="CRS-TEST-2")
    course_group = service.current_memberships(
        as_of=AS_OF,
        course_group_id="CG-TEST",
    )
    assert {item.student_id for item in group} == set(SYNTHETIC_STUDENT_IDS[:2])
    assert [item.student_id for item in course] == [SYNTHETIC_STUDENT_IDS[1]]
    assert [item.student_id for item in course_group] == [
        SYNTHETIC_STUDENT_IDS[0]
    ]
    assert all(
        item.resolution_status is AssignmentResolutionStatus.ENROLLED
        for item in course_group
    )


def test_current_counts_are_assignment_based(v3_database: Path) -> None:
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    assert service.count_current_by_group(as_of=AS_OF) == {
        "GRP-TEST-A": 2,
        "GRP-TEST-B": 1,
    }
    assert service.count_current_by_course(as_of=AS_OF) == {
        "CRS-TEST-1": 1,
        "CRS-TEST-2": 1,
        "CRS-TEST-3": 1,
    }


class _CountingFactory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.statements: list[str] = []

    def __call__(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.set_trace_callback(self.statements.append)
        return connection

    @property
    def query_count(self) -> int:
        return sum(
            statement.lstrip().upper().startswith(("SELECT", "WITH"))
            for statement in self.statements
        )


def _bulk_database(path: Path, count: int) -> tuple[Path, tuple[str, ...]]:
    FinalV3SchemaInitializer().initialize(path)
    student_ids = tuple(f"STD-BULK-{number:03}" for number in range(count))
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES ('SY-BULK', '2025/26', '2025-08-01', '2026-07-31',
                      'current', ?, NULL)
            """,
            (NOW.isoformat(),),
        )
        connection.execute(
            """
            INSERT INTO groups(group_id, group_name, sort_order, active)
            VALUES ('GRP-BULK', 'Bulkgruppe', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO courses(
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active, year_level
            ) VALUES ('CRS-BULK', 'Bulkkurs', 'blue', 'Blau', '#0000AA',
                      1, 1, 1)
            """
        )
        connection.executemany(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (?, 'Test', ?, '', 1, ?, ?, NULL)
            """,
            (
                (student_id, f"Kind {number:03}", NOW.isoformat(), NOW.isoformat())
                for number, student_id in enumerate(student_ids)
            ),
        )
        connection.executemany(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (?, ?, 'SY-BULK', 'GRP-BULK', 'CRS-BULK', 'enrolled',
                      '2025-08-01', '2026-07-31', ?, ?)
            """,
            (
                (
                    f"ASG-BULK-{number:03}",
                    student_id,
                    NOW.isoformat(),
                    NOW.isoformat(),
                )
                for number, student_id in enumerate(student_ids)
            ),
        )
    return path, student_ids


@pytest.mark.parametrize("student_count", (1, 10, 100))
def test_batch_assignment_query_count_is_constant(
    tmp_path: Path,
    student_count: int,
) -> None:
    path, student_ids = _bulk_database(
        tmp_path / f"bulk-{student_count}.sqlite",
        student_count,
    )
    factory = _CountingFactory(path)
    result = SchoolYearAssignmentQueryService(factory).assignments_at_dates(
        {student_id: AS_OF for student_id in student_ids}
    )
    assert [item.student_id for item in result] == list(student_ids)
    assert all(
        item.resolution_status is AssignmentResolutionStatus.ENROLLED
        for item in result
    )
    assert factory.query_count == 1


@pytest.mark.parametrize("student_count", (1, 10, 100))
def test_current_membership_batch_query_count_is_constant(
    tmp_path: Path,
    student_count: int,
) -> None:
    path, student_ids = _bulk_database(
        tmp_path / f"current-{student_count}.sqlite",
        student_count,
    )
    factory = _CountingFactory(path)
    result = SchoolYearAssignmentQueryService(factory).current_memberships(
        student_ids,
        as_of=AS_OF,
        group_id="GRP-BULK",
        course_id="CRS-BULK",
    )
    assert [item.student_id for item in result] == list(student_ids)
    assert factory.query_count == 2


def _used_assignment_indexes(
    path: Path,
    statement: str,
) -> set[str]:
    registered = {
        "idx_assignments_student_year_interval",
        "idx_assignments_student_interval",
        "idx_assignments_year_status_student",
        "idx_assignments_year_group_interval",
        "idx_assignments_year_course_interval",
        "idx_assignments_last_known",
    }
    with sqlite3.connect(path) as connection:
        plan = connection.execute(
            f"EXPLAIN QUERY PLAN {statement}"
        ).fetchall()
    return {
        index_name
        for index_name in registered
        if any(index_name in str(row[3]) for row in plan)
    }


def test_actual_assignment_queries_use_registered_indexes(
    v3_database: Path,
) -> None:
    batch_factory = _CountingFactory(v3_database)
    SchoolYearAssignmentQueryService(batch_factory).assignments_at_dates(
        {SYNTHETIC_STUDENT_IDS[0]: AS_OF}
    )
    batch_query = next(
        statement
        for statement in batch_factory.statements
        if statement.lstrip().startswith("WITH requested")
    )
    assert _used_assignment_indexes(v3_database, batch_query) & {
        "idx_assignments_student_year_interval",
        "idx_assignments_student_interval",
        "idx_assignments_last_known",
    }

    group_factory = _CountingFactory(v3_database)
    SchoolYearAssignmentQueryService(group_factory).current_memberships(
        as_of=AS_OF,
        group_id="GRP-TEST-A",
    )
    group_query = next(
        statement
        for statement in group_factory.statements
        if "scoped_assignment.group_id" in statement
    )
    assert "idx_assignments_year_group_interval" in _used_assignment_indexes(
        v3_database,
        group_query,
    )

    course_factory = _CountingFactory(v3_database)
    SchoolYearAssignmentQueryService(course_factory).current_memberships(
        as_of=AS_OF,
        course_id="CRS-TEST-1",
    )
    course_query = next(
        statement
        for statement in course_factory.statements
        if "scoped_assignment.course_id" in statement
    )
    assert "idx_assignments_year_course_interval" in _used_assignment_indexes(
        v3_database,
        course_query,
    )

    last_known_factory = _CountingFactory(v3_database)
    SchoolYearAssignmentQueryService(last_known_factory).last_known_membership(
        SYNTHETIC_STUDENT_IDS[0],
        reference_date=date(2026, 8, 1),
    )
    last_known_query = next(
        statement
        for statement in last_known_factory.statements
        if statement.lstrip().startswith("WITH last_date")
    )
    assert "idx_assignments_last_known" in _used_assignment_indexes(
        v3_database,
        last_known_query,
    )


def test_v3_student_model_has_no_membership_fields() -> None:
    assert tuple(field.name for field in fields(V3Student)) == (
        "student_id",
        "first_name",
        "last_name",
        "notes",
        "active",
        "created_at",
        "updated_at",
        "archived_at",
    )


def test_create_student_and_initial_enrollment_are_atomic(
    v3_database: Path,
) -> None:
    result = CreateStudentWithInitialEnrollment(
        _factory(v3_database),
        student_id_factory=lambda: "STD-NEW-001",
        assignment_id_factory=lambda: "ASG-NEW-001",
        now_provider=lambda: NOW,
    ).execute(
        first_name="Ada",
        last_name="Beispiel",
        notes="Neu",
        school_year_id=SYNTHETIC_SCHOOL_YEAR_ID,
        valid_from=date(2026, 2, 1),
        valid_to=date(2026, 7, 31),
        group_id="GRP-TEST-A",
        course_id="CRS-TEST-1",
    )
    assert result.student.student_id == "STD-NEW-001"
    assert result.assignment.membership.student_id == "STD-NEW-001"


@pytest.mark.parametrize(
    ("group_id", "course_id", "expected_code"),
    (
        ("GRP-UNKNOWN", "CRS-TEST-1", "group_invalid"),
        ("GRP-TEST-A", "CRS-UNKNOWN", "course_invalid"),
    ),
)
def test_create_rejects_invalid_membership_references(
    v3_database: Path,
    group_id: str,
    course_id: str,
    expected_code: str,
) -> None:
    command = CreateStudentWithInitialEnrollment(
        _factory(v3_database),
        student_id_factory=lambda: "STD-INVALID",
        assignment_id_factory=lambda: "ASG-INVALID",
        now_provider=lambda: NOW,
    )
    with pytest.raises(AssignmentApplicationError) as captured:
        command.execute(
            first_name="Ada",
            last_name="Beispiel",
            notes="",
            school_year_id=SYNTHETIC_SCHOOL_YEAR_ID,
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 7, 31),
            group_id=group_id,
            course_id=course_id,
        )
    assert captured.value.code == expected_code
    with sqlite3.connect(v3_database) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM students WHERE student_id = 'STD-INVALID'"
            ).fetchone()[0]
            == 0
        )


def test_create_rejects_course_without_valid_year_level(
    v3_database: Path,
) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute(
            "UPDATE courses SET year_level = 4 WHERE course_id = 'CRS-TEST-1'"
        )
    command = CreateStudentWithInitialEnrollment(
        _factory(v3_database),
        student_id_factory=lambda: "STD-BAD-LEVEL",
        assignment_id_factory=lambda: "ASG-BAD-LEVEL",
        now_provider=lambda: NOW,
    )
    with pytest.raises(AssignmentApplicationError) as captured:
        command.execute(
            first_name="Ada",
            last_name="Beispiel",
            notes="",
            school_year_id=SYNTHETIC_SCHOOL_YEAR_ID,
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 7, 31),
            group_id="GRP-TEST-A",
            course_id="CRS-TEST-1",
        )
    assert captured.value.code == "course_year_level_invalid"


def test_create_rolls_back_student_when_assignment_insert_fails(
    v3_database: Path,
) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_test_assignment_insert
            BEFORE INSERT ON student_school_year_assignments
            BEGIN
                SELECT RAISE(ABORT, 'test_failure');
            END
            """
        )
    command = CreateStudentWithInitialEnrollment(
        _factory(v3_database),
        student_id_factory=lambda: "STD-ROLLBACK",
        assignment_id_factory=lambda: "ASG-ROLLBACK",
        now_provider=lambda: NOW,
    )
    with pytest.raises(AssignmentApplicationError) as captured:
        command.execute(
            first_name="Ada",
            last_name="Rollback",
            notes="",
            school_year_id=SYNTHETIC_SCHOOL_YEAR_ID,
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 7, 31),
            group_id="GRP-TEST-A",
            course_id="CRS-TEST-1",
        )
    assert captured.value.code == "initial_enrollment_failed"
    with sqlite3.connect(v3_database) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM students WHERE student_id = 'STD-ROLLBACK'"
            ).fetchone()[0]
            == 0
        )


def test_enroll_student_uses_explicit_interval_and_rejects_overlap(
    v3_database: Path,
) -> None:
    command = EnrollStudent(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-OVERLAP",
        now_provider=lambda: NOW,
    )
    with pytest.raises(AssignmentApplicationError) as captured:
        command.execute(
            SYNTHETIC_STUDENT_IDS[0],
            school_year_id=SYNTHETIC_SCHOOL_YEAR_ID,
            valid_from=AS_OF,
            valid_to=date(2026, 3, 1),
            group_id="GRP-TEST-A",
            course_id="CRS-TEST-1",
        )
    assert captured.value.code == "assignment_overlap"


def test_enroll_student_succeeds_in_explicit_later_school_year(
    v3_database: Path,
) -> None:
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (
                'SY-TEST-2026-27', '2026/27', '2026-08-01', '2027-07-31',
                'planned', ?, NULL
            )
            """,
            (NOW.isoformat(),),
        )
    stored = EnrollStudent(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-LATER-YEAR",
        now_provider=lambda: NOW,
    ).execute(
        SYNTHETIC_STUDENT_IDS[0],
        school_year_id="SY-TEST-2026-27",
        valid_from=date(2026, 8, 1),
        valid_to=date(2027, 7, 31),
        group_id="GRP-TEST-A",
        course_id="CRS-TEST-2",
    )
    assert stored.assignment_id == "ASG-LATER-YEAR"
    assert stored.membership.school_year_id == "SY-TEST-2026-27"
    connection = _factory(v3_database)()
    try:
        repository = StudentSchoolYearAssignmentRepository(connection)
        assert repository.get_by_id("ASG-LATER-YEAR") == stored
        assert repository.list_for_student(SYNTHETIC_STUDENT_IDS[0])[-1] == stored
    finally:
        connection.close()


def test_update_master_data_never_changes_membership(v3_database: Path) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    updated = UpdateStudentMasterData(
        _factory(v3_database),
        now_provider=lambda: NOW,
    ).execute(
        SYNTHETIC_STUDENT_IDS[0],
        first_name="Neuer",
        last_name="Name",
        notes="Neue Notiz",
    )
    after = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    assert (updated.first_name, updated.last_name, updated.notes) == (
        "Neuer",
        "Name",
        "Neue Notiz",
    )
    assert after == before


@pytest.mark.parametrize(
    ("group_id", "course_id", "expected_group", "expected_course"),
    (
        (None, "CRS-TEST-2", "GRP-TEST-A", "CRS-TEST-2"),
        ("GRP-TEST-B", None, "GRP-TEST-B", "CRS-TEST-1"),
        ("GRP-TEST-B", "CRS-TEST-3", "GRP-TEST-B", "CRS-TEST-3"),
    ),
)
def test_change_membership_supports_course_group_or_both(
    v3_database: Path,
    group_id: str | None,
    course_id: str | None,
    expected_group: str,
    expected_course: str,
) -> None:
    result = ChangeStudentMembership(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-CHANGED",
        now_provider=lambda: NOW,
    ).execute(
        SYNTHETIC_STUDENT_IDS[0],
        effective_on=AS_OF,
        group_id=group_id,
        course_id=course_id,
    )
    assert result.status is MembershipChangeStatus.CHANGED
    assert result.assignment is not None
    assert result.assignment.membership.group_id == expected_group
    assert result.assignment.membership.course_id == expected_course
    rows = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    assert rows[0][7] == "2026-01-14"
    assert rows[1][6] == "2026-01-15"


def test_change_membership_returns_no_change_without_write(
    v3_database: Path,
) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    result = ChangeStudentMembership(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-SHOULD-NOT-BE-USED",
        now_provider=lambda: NOW,
    ).execute(
        SYNTHETIC_STUDENT_IDS[0],
        effective_on=AS_OF,
        group_id="GRP-TEST-A",
        course_id="CRS-TEST-1",
    )
    assert result.status is MembershipChangeStatus.NO_CHANGE
    assert result.assignment is None
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_change_membership_blocks_first_interval_day(
    v3_database: Path,
) -> None:
    with pytest.raises(AssignmentApplicationError) as captured:
        ChangeStudentMembership(
            _factory(v3_database),
            now_provider=lambda: NOW,
        ).execute(
            SYNTHETIC_STUDENT_IDS[0],
            effective_on=date(2025, 8, 1),
            course_id="CRS-TEST-2",
        )
    assert captured.value.code == "membership_change_on_first_interval_day"


def test_change_membership_allows_last_interval_day(v3_database: Path) -> None:
    result = ChangeStudentMembership(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-LAST-DAY",
        now_provider=lambda: NOW,
    ).execute(
        SYNTHETIC_STUDENT_IDS[0],
        effective_on=date(2026, 7, 31),
        course_id="CRS-TEST-2",
    )
    assert result.assignment is not None
    assert result.assignment.membership.valid_from == date(2026, 7, 31)
    assert result.assignment.membership.valid_to == date(2026, 7, 31)


def test_change_rolls_back_shortening_when_replacement_insert_fails(
    v3_database: Path,
) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_replacement_insert
            BEFORE INSERT ON student_school_year_assignments
            WHEN NEW.assignment_id = 'ASG-FAIL-SECOND'
            BEGIN
                SELECT RAISE(ABORT, 'test_failure');
            END
            """
        )
    with pytest.raises(AssignmentApplicationError):
        ChangeStudentMembership(
            _factory(v3_database),
            assignment_id_factory=lambda: "ASG-FAIL-SECOND",
            now_provider=lambda: NOW,
        ).execute(
            SYNTHETIC_STUDENT_IDS[0],
            effective_on=AS_OF,
            course_id="CRS-TEST-2",
        )
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_exit_shortens_enrollment_and_creates_exited_interval(
    v3_database: Path,
) -> None:
    result = ExitStudentFromSchoolYear(
        _factory(v3_database),
        assignment_id_factory=lambda: "ASG-EXIT",
        now_provider=lambda: NOW,
    ).execute(SYNTHETIC_STUDENT_IDS[0], effective_on=AS_OF)
    assert result.assignment is not None
    assert result.assignment.membership.assignment_status is StudentAssignmentStatus.EXITED
    assert result.assignment.membership.group_id is None
    assert result.assignment.membership.course_id is None
    with sqlite3.connect(v3_database) as connection:
        student = connection.execute(
            "SELECT active, archived_at FROM students WHERE student_id = ?",
            (SYNTHETIC_STUDENT_IDS[0],),
        ).fetchone()
    assert student == (1, None)


def test_exit_rolls_back_when_exited_insert_fails(v3_database: Path) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    with sqlite3.connect(v3_database) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_exit_insert
            BEFORE INSERT ON student_school_year_assignments
            WHEN NEW.assignment_status = 'exited'
            BEGIN
                SELECT RAISE(ABORT, 'test_failure');
            END
            """
        )
    with pytest.raises(AssignmentApplicationError):
        ExitStudentFromSchoolYear(
            _factory(v3_database),
            assignment_id_factory=lambda: "ASG-EXIT-FAIL",
            now_provider=lambda: NOW,
        ).execute(SYNTHETIC_STUDENT_IDS[0], effective_on=AS_OF)
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_archive_is_blocked_by_active_enrollment(v3_database: Path) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    with pytest.raises(AssignmentApplicationError) as captured:
        ArchiveStudent(
            _factory(v3_database),
            now_provider=lambda: NOW,
        ).execute(SYNTHETIC_STUDENT_IDS[0], as_of=AS_OF)
    assert captured.value.code == "active_enrollment_blocks_archive"
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_archive_without_active_enrollment_changes_no_assignment(
    v3_database: Path,
) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    archived = ArchiveStudent(
        _factory(v3_database),
        now_provider=lambda: datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
    ).execute(
        SYNTHETIC_STUDENT_IDS[0],
        as_of=date(2026, 8, 1),
    )
    assert archived.active is False
    assert archived.archived_at is not None
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_archive_rejects_mismatched_reference_and_archive_day(
    v3_database: Path,
) -> None:
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    with pytest.raises(AssignmentApplicationError) as captured:
        ArchiveStudent(
            _factory(v3_database),
            now_provider=lambda: datetime(2026, 8, 2, 9, 0, tzinfo=UTC),
        ).execute(
            SYNTHETIC_STUDENT_IDS[0],
            as_of=date(2026, 8, 1),
        )
    assert (
        captured.value.code
        == "archive_reference_date_timestamp_mismatch"
    )
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_repository_write_respects_caller_transaction(v3_database: Path) -> None:
    connection = _factory(v3_database)()
    before = _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0])
    try:
        connection.execute("BEGIN IMMEDIATE")
        StudentSchoolYearAssignmentRepository(connection).shorten(
            "ASG-TEST-001",
            date(2026, 7, 30),
            NOW,
        )
        assert connection.in_transaction
        connection.rollback()
    finally:
        connection.close()
    assert _assignment_rows(v3_database, SYNTHETIC_STUDENT_IDS[0]) == before


def test_historical_domain_reference_dates_resolve_without_runtime_rewire(
    v3_database: Path,
) -> None:
    with sqlite3.connect(v3_database) as connection:
        observation_date = date.fromisoformat(
            connection.execute(
                "SELECT date FROM observations WHERE observation_id = 'OBS-TEST-001'"
            ).fetchone()[0]
        )
        confirmation_date = date.fromisoformat(
            connection.execute(
                """
                SELECT substr(confirmed_at, 1, 10)
                FROM student_competency_confirmations
                WHERE student_id = ?
                """,
                (SYNTHETIC_STUDENT_IDS[0],),
            ).fetchone()[0]
        )
        report_period_end = date.fromisoformat(
            connection.execute(
                "SELECT period_end FROM report_drafts WHERE report_draft_id = 'RPD-TEST-001'"
            ).fetchone()[0]
        )
        conference_date = date.fromisoformat(
            connection.execute(
                """
                SELECT conference_date
                FROM learning_conference_drafts
                WHERE learning_conference_draft_id = 'LCD-TEST-001'
                """
            ).fetchone()[0]
        )
    service = SchoolYearAssignmentQueryService(_factory(v3_database))
    for reference in (
        observation_date,
        confirmation_date,
        report_period_end,
        conference_date,
    ):
        assert (
            service.assignment_at_date(SYNTHETIC_STUDENT_IDS[0], reference)
            .resolution_status
            is AssignmentResolutionStatus.ENROLLED
        )


def test_assignment_module_has_no_qt_or_desktop_dependency() -> None:
    sources = (
        Path("src/core/school_year.py").read_text(encoding="utf-8"),
        Path("src/core/sqlite_school_year_assignment.py").read_text(
            encoding="utf-8"
        ),
        Path("src/application/school_year_assignment.py").read_text(
            encoding="utf-8"
        ),
    )
    assert all("PySide" not in source for source in sources)
    assert all("src.desktop_app" not in source for source in sources)
