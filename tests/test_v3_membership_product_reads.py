"""Focused product-composition tests against the synthetic final-V3 schema."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3

from src.core.database_engine import SQLiteConnectionProvider
from src.core.final_v3_schema import FinalV3SchemaInitializer
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.adapters.student_desktop_adapter import (
    StudentDesktopAdapter,
)
from tests.helpers.synthetic_v3 import (
    SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v3_database,
)


AS_OF = date(2027, 1, 15)
PERF_AS_OF = date(2026, 1, 15)


class _CountingConnectionProvider:
    def __init__(self) -> None:
        self.base = SQLiteConnectionProvider()
        self.statements: list[str] = []

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> sqlite3.Connection:
        connection = self.base.connect(
            path,
            create=create,
            key_material=key_material,
        )
        connection.set_trace_callback(self.statements.append)
        return connection

    def select_count(self, operation: Callable[[], object]) -> int:
        self.statements.clear()
        operation()
        return sum(
            statement.lstrip().upper().startswith(("SELECT", "WITH"))
            for statement in self.statements
        )


def _adapter(path: Path, *, today: date = AS_OF) -> StudentDesktopAdapter:
    database = SQLiteDatabase(
        path,
        create=False,
        initialize_schema=False,
    )
    return StudentDesktopAdapter(
        database=database,
        today_provider=lambda: today,
    )


def _seed_course_group(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO course_groups(course_group_id, name, sort_order, active)
            VALUES ('CG-PRODUCT', 'Produktverbund', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO course_group_student_groups(
                course_group_id, student_group_id
            ) VALUES ('CG-PRODUCT', 'GRP-TEST-A')
            """
        )
        connection.execute(
            """
            INSERT INTO course_group_courses(course_group_id, course_id)
            VALUES ('CG-PRODUCT', 'CRS-TEST-1')
            """
        )


def _bulk_product_database(
    path: Path,
    *,
    student_count: int,
    provider: _CountingConnectionProvider,
) -> SQLiteDatabase:
    FinalV3SchemaInitializer().initialize(path)
    timestamp = "2025-07-01T08:00:00+00:00"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (
                'SY-PERF', '2025/26', '2025-08-01', '2026-07-31',
                'current', ?, NULL
            )
            """,
            (timestamp,),
        )
        connection.execute(
            """
            INSERT INTO groups(group_id, group_name, sort_order, active)
            VALUES ('GRP-PERF', 'Performancegruppe', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO courses(
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active, year_level
            ) VALUES (
                'CRS-PERF', 'Performancekurs', 'blue', 'Blau', '#335577',
                1, 1, 1
            )
            """
        )
        connection.execute(
            """
            INSERT INTO course_groups(
                course_group_id, name, sort_order, active
            ) VALUES ('CG-PERF', 'Performanceverbund', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO course_group_student_groups(
                course_group_id, student_group_id
            ) VALUES ('CG-PERF', 'GRP-PERF')
            """
        )
        connection.execute(
            """
            INSERT INTO course_group_courses(course_group_id, course_id)
            VALUES ('CG-PERF', 'CRS-PERF')
            """
        )
        connection.executemany(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (?, 'Testkind', ?, '', 1, ?, ?, NULL)
            """,
            (
                (
                    f"STD-PERF-{number:03}",
                    f"{number:03}",
                    timestamp,
                    timestamp,
                )
                for number in range(student_count)
            ),
        )
        connection.executemany(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (
                ?, ?, 'SY-PERF', 'GRP-PERF', 'CRS-PERF', 'enrolled',
                '2025-08-01', '2026-07-31', ?, ?
            )
            """,
            (
                (
                    f"ASG-PERF-{number:03}",
                    f"STD-PERF-{number:03}",
                    timestamp,
                    timestamp,
                )
                for number in range(student_count)
            ),
        )
    return SQLiteDatabase(
        path,
        connection_provider=provider,
        create=False,
        initialize_schema=False,
    )


def test_current_lists_counts_and_course_group_scope_use_v3_assignments(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "current-scopes.sqlite")
    _seed_course_group(path)
    adapter = _adapter(path)

    all_students = adapter.list_students()
    group_students = adapter.list_students(group_id="GRP-TEST-A")
    course_students = adapter.list_students(course_id="CRS-TEST-2")
    course_group_students = adapter.list_students(
        course_group_id="CG-PRODUCT"
    )
    group_counts = {
        item.group_id: item.active_student_count
        for item in adapter.list_group_summaries()
    }

    assert {item.student_id for item in all_students} == set(
        SYNTHETIC_STUDENT_IDS
    )
    assert {item.student_id for item in group_students} == set(
        SYNTHETIC_STUDENT_IDS[:2]
    )
    assert tuple(item.student_id for item in course_students) == (
        SYNTHETIC_STUDENT_IDS[1],
    )
    assert tuple(item.student_id for item in course_group_students) == (
        SYNTHETIC_STUDENT_IDS[0],
    )
    assert group_counts == {"GRP-TEST-A": 2, "GRP-TEST-B": 1}
    assert course_group_students[0].group_name == "Testgruppe A"
    assert course_group_students[0].course_name == "Testkurs 1"


def test_student_profile_exposes_neutral_and_blocking_membership_states(
    tmp_path: Path,
) -> None:
    exited_path = create_synthetic_v3_database(tmp_path / "exited.sqlite")
    with sqlite3.connect(exited_path) as connection:
        connection.execute("DROP TRIGGER trg_assignments_update_guard")
        connection.execute(
            """
            UPDATE student_school_year_assignments
            SET assignment_status = 'exited',
                group_id = NULL,
                course_id = NULL
            WHERE student_id = ?
            """,
            (SYNTHETIC_STUDENT_IDS[0],),
        )
    exited_adapter = _adapter(exited_path)
    exited = exited_adapter.get_student_profile(SYNTHETIC_STUDENT_IDS[0])
    assert (
        exited_adapter.student_profile_projection_bundle(
            SYNTHETIC_STUDENT_IDS[0]
        ).student
        == exited
    )
    assert exited is not None
    assert exited.resolution_status == "exited"
    assert exited.status_label == "Im aktuellen Schuljahr ausgeschieden"
    assert not exited.membership_blocking

    missing_path = create_synthetic_v3_database(
        tmp_path / "no-assignment.sqlite"
    )
    with sqlite3.connect(missing_path) as connection:
        connection.execute("DROP TRIGGER trg_assignments_no_delete")
        connection.execute(
            "DELETE FROM student_school_year_assignments WHERE student_id = ?",
            (SYNTHETIC_STUDENT_IDS[0],),
        )
    missing_adapter = _adapter(missing_path)
    missing = missing_adapter.get_student_profile(SYNTHETIC_STUDENT_IDS[0])
    assert (
        missing_adapter.student_profile_projection_bundle(
            SYNTHETIC_STUDENT_IDS[0]
        ).student
        == missing
    )
    assert missing is not None
    assert missing.resolution_status == "no_assignment"
    assert missing.status_label == "Keine aktuelle Zuordnung"
    assert not missing.membership_blocking

    ambiguous_path = create_synthetic_v3_database(
        tmp_path / "ambiguous.sqlite"
    )
    with sqlite3.connect(ambiguous_path) as connection:
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
                "ASG-PRODUCT-AMBIGUOUS",
                SYNTHETIC_STUDENT_IDS[0],
                SYNTHETIC_SCHOOL_YEAR_ID,
                "GRP-TEST-B",
                "CRS-TEST-2",
                "2026-12-01",
                "2027-02-01",
                "2027-01-01T08:00:00+00:00",
                "2027-01-01T08:00:00+00:00",
            ),
        )
    ambiguous_adapter = _adapter(ambiguous_path)
    ambiguous = ambiguous_adapter.get_student_profile(
        SYNTHETIC_STUDENT_IDS[0]
    )
    assert (
        ambiguous_adapter.student_profile_projection_bundle(
            SYNTHETIC_STUDENT_IDS[0]
        ).student
        == ambiguous
    )
    assert ambiguous is not None
    assert ambiguous.resolution_status == "ambiguous"
    assert ambiguous.status_label == "Aktuelle Zuordnung nicht eindeutig"
    assert ambiguous.membership_blocking

    no_current_path = create_synthetic_v3_database(
        tmp_path / "no-current.sqlite"
    )
    with sqlite3.connect(no_current_path) as connection:
        connection.execute(
            """
            UPDATE school_years
            SET status = 'closed', closed_at = ?
            WHERE school_year_id = ?
            """,
            (
                "2026-07-31T12:00:00+00:00",
                SYNTHETIC_SCHOOL_YEAR_ID,
            ),
        )
    no_current_adapter = _adapter(no_current_path)
    no_current = no_current_adapter.get_student_profile(
        SYNTHETIC_STUDENT_IDS[0]
    )
    assert (
        no_current_adapter.student_profile_projection_bundle(
            SYNTHETIC_STUDENT_IDS[0]
        ).student
        == no_current
    )
    assert no_current is not None
    assert no_current.resolution_status == "current_school_year_missing"
    assert no_current.status_label == "Kein aktuelles Schuljahr festgelegt"
    assert no_current.membership_blocking

    archived_path = create_synthetic_v3_database(tmp_path / "archived.sqlite")
    with sqlite3.connect(archived_path) as connection:
        connection.execute(
            """
            UPDATE students
            SET active = 0, archived_at = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (
                "2026-01-10T08:00:00+00:00",
                "2026-01-10T08:00:00+00:00",
                SYNTHETIC_STUDENT_IDS[0],
            ),
        )
    archived_adapter = _adapter(archived_path)
    archived = archived_adapter.get_student_profile(
        SYNTHETIC_STUDENT_IDS[0]
    )
    assert (
        archived_adapter.student_profile_projection_bundle(
            SYNTHETIC_STUDENT_IDS[0]
        ).student
        == archived
    )
    assert archived is not None
    assert archived.resolution_status == "student_archived"
    assert archived.status_label == "Kind ist archiviert"
    assert not archived.membership_blocking


def test_dashboard_uses_one_as_of_and_batch_target_student_ids(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "dashboard.sqlite")
    _seed_course_group(path)
    adapter = _adapter(path)

    class CountingDateTime(datetime):
        date_call_count = 0

        def date(self) -> date:
            type(self).date_call_count += 1
            return super().date()

    at = CountingDateTime(2027, 1, 15, 9, 0, tzinfo=UTC)
    heatmap, suggestions = adapter.dashboard_documentation_refresh(
        target_type="course_group",
        target_id="CG-PRODUCT",
        subject_id="SUB-TEST-DE",
        subject_label="Testsprache",
        at=at,
    )

    assert CountingDateTime.date_call_count == 1
    assert tuple(item.student_id for item in suggestions) == (
        SYNTHETIC_STUDENT_IDS[0],
    )
    group_a = next(
        item for item in heatmap.groups if item.group_id == "GRP-TEST-A"
    )
    test_subject = next(
        item for item in group_a.cells if item.subject_id == "SUB-TEST-DE"
    )
    assert test_subject.total_count == 2
    assert test_subject.documented_count == 1


def test_observation_edit_context_resolves_at_observation_date(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "historical-edit.sqlite")
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE student_school_year_assignments
            SET valid_to = '2025-10-31'
            WHERE student_id = ? AND school_year_id = ?
            """,
            (SYNTHETIC_STUDENT_IDS[0], SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID),
        )
        connection.execute(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'enrolled', ?, ?, ?, ?)
            """,
            (
                "ASG-PRODUCT-LATER",
                SYNTHETIC_STUDENT_IDS[0],
                SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,
                "GRP-TEST-B",
                "CRS-TEST-2",
                "2025-11-01",
                "2026-07-31",
                "2025-11-01T08:00:00+00:00",
                "2025-11-01T08:00:00+00:00",
            ),
        )
    adapter = _adapter(path)
    draft = adapter.observation_draft_for_edit("OBS-TEST-001")
    assert draft is not None

    current = adapter.get_student_profile(SYNTHETIC_STUDENT_IDS[0])
    current_bundle = adapter.student_profile_projection_bundle(
        SYNTHETIC_STUDENT_IDS[0]
    )
    historical = adapter.get_student_profile(
        SYNTHETIC_STUDENT_IDS[0],
        reference_date=date.fromisoformat(draft.date_text),
    )
    report_preparation = adapter.learning_report_preparation_for_student(
        SYNTHETIC_STUDENT_IDS[0],
        period_end=date.fromisoformat(draft.date_text),
    )
    historical_leg_preparation = (
        adapter.learning_conference_preparation_for_student(
            SYNTHETIC_STUDENT_IDS[0],
            conference_date=date.fromisoformat(draft.date_text),
        )
    )
    neutral_leg_preparation = (
        adapter.learning_conference_preparation_for_student(
            SYNTHETIC_STUDENT_IDS[0],
            conference_date=None,
        )
    )

    assert current is not None
    assert current_bundle.student == current
    assert historical is not None
    assert report_preparation is not None
    assert historical_leg_preparation is not None
    assert neutral_leg_preparation is not None
    assert (current.group_name, current.course_name) == (
        "Testgruppe A",
        "Testkurs 1",
    )
    assert (historical.group_name, historical.course_name) == (
        "Testgruppe A",
        "Testkurs 1",
    )
    assert report_preparation.group_name == "Testgruppe A"
    assert report_preparation.course_name == "Testkurs 1"
    assert historical_leg_preparation.group_name == "Testgruppe A"
    assert historical_leg_preparation.course_name == "Testkurs 1"
    assert neutral_leg_preparation.group_name == ""
    assert neutral_leg_preparation.course_name == ""
    assert (
        neutral_leg_preparation.membership_status_label
        == "Zuordnung noch nicht aufgelöst"
    )


def test_missing_active_course_never_leaks_the_technical_id(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v3_database(tmp_path / "inactive-course.sqlite")
    with sqlite3.connect(path) as connection:
        connection.execute(
        "UPDATE courses SET active = 0 WHERE course_id = 'CRS-TEST-1'"
        )
    adapter = _adapter(path)

    profile = adapter.get_student_profile(SYNTHETIC_STUDENT_IDS[0])
    list_item = next(
        item
        for item in adapter.list_students()
        if item.student_id == SYNTHETIC_STUDENT_IDS[0]
    )

    assert profile is not None
    assert profile.course_name == "Testkurs 1"
    assert list_item.course_name == "Testkurs 1"
    assert profile.course_name != "CRS-TEST-1"
    assert list_item.course_name != "CRS-TEST-1"


def test_composed_product_query_budgets_are_constant_for_1_10_100_students(
    tmp_path: Path,
) -> None:
    counts_by_size: dict[int, dict[str, int]] = {}
    for student_count in (1, 10, 100):
        provider = _CountingConnectionProvider()
        database = _bulk_product_database(
            tmp_path / f"product-budget-{student_count}.sqlite",
            student_count=student_count,
            provider=provider,
        )
        adapter = StudentDesktopAdapter(
            database=database,
            today_provider=lambda: PERF_AS_OF,
        )
        student_id = "STD-PERF-000"
        counts_by_size[student_count] = {
            "student_list": provider.select_count(adapter.list_students),
            "group_overview": provider.select_count(
                adapter.list_group_summaries
            ),
            "course_members": provider.select_count(
                lambda: adapter.list_students(course_id="CRS-PERF")
            ),
            "course_group": provider.select_count(
                lambda: adapter.list_students(course_group_id="CG-PERF")
            ),
            "dashboard": provider.select_count(
                lambda: adapter.dashboard_documentation_refresh(
                    target_type="course_group",
                    target_id="CG-PERF",
                    subject_id="SUB-PERF",
                    subject_label="Testfach",
                    at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
                    limit=100,
                )
            ),
            "report_preparation": provider.select_count(
                lambda: adapter.learning_report_preparation_for_student(
                    student_id,
                    period_end=PERF_AS_OF,
                )
            ),
        }

    assert counts_by_size[1] == counts_by_size[10]
    assert counts_by_size[10] == counts_by_size[100]
    assert counts_by_size[100] == {
        "student_list": 14,
        "group_overview": 14,
        "course_members": 14,
        "course_group": 14,
        "dashboard": 15,
        "report_preparation": 13,
    }
