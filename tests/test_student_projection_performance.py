"""Equivalence and query-budget tests for batched student projections."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from src.core.database_engine import SQLiteConnectionProvider
from src.core.persistence_events import (
    PersistenceEventKind,
    PersistenceOrderingState,
)
from src.core.records import seed_reference_data
from src.core.sqlite_store import (
    MasterDataCourseGroupRecord,
    MasterDataCourseRecord,
    MasterDataGroupRecord,
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteDocumentationSubjectSettingsRepository,
    SQLiteMasterDataRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    SQLiteStudentDocumentationProjectionRepository,
    SQLiteStudentRepository,
)
from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import (
    StudentDesktopAdapter,
)
from src.desktop_app.view_models.student_view_model import (
    DashboardDocumentationCellViewModel,
    DashboardDocumentationGroupViewModel,
    DashboardDocumentationHeatmapViewModel,
    documentation_summary_from_subjects,
)

AS_OF = date(2026, 8, 13)


class CountingConnectionProvider:
    """Collect statements after connection setup without changing SQLite."""

    def __init__(self) -> None:
        self.base = SQLiteConnectionProvider()
        self.statements: list[str] = []
        self.on_statement: Callable[[str], None] | None = None

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
        def trace(statement: str) -> None:
            self.statements.append(statement)
            if self.on_statement is not None:
                self.on_statement(statement)

        connection.set_trace_callback(trace)
        return connection

    def reset(self) -> None:
        self.statements.clear()


def _database_with_catalog(
    path: Path,
    *,
    provider: CountingConnectionProvider | None = None,
) -> SQLiteDatabase:
    database = SQLiteDatabase(path, connection_provider=provider)
    database.initialize_schema()
    database.replace_seed_data(seed_reference_data())
    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter().list_entries()
    )
    return database


def _insert_historical_unknown_state(
    database: SQLiteDatabase,
    *,
    student_id: str,
    competency_id: str,
) -> None:
    timestamp = "2026-01-10T08:00:00+00:00"
    payload_hash = "a" * 64
    with closing(database.connect()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO observations (
                    observation_id,
                    student_id,
                    date,
                    subject_id,
                    context,
                    note,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, '', 1, ?, ?)
                """,
                (
                    "OBS-PERF-001",
                    student_id,
                    "2026-01-10",
                    "deutsch",
                    "Lesezeit",
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO observation_competency_ratings (
                    observation_id,
                    competency_id,
                    subject_id,
                    subject_display_name,
                    learning_area,
                    competency_group,
                    competency_text,
                    rating
                )
                SELECT
                    ?,
                    competency_id,
                    subject_id,
                    subject_name,
                    learning_area,
                    competency_group,
                    description,
                    '+'
                FROM competencies
                WHERE competency_id = ?
                """,
                ("OBS-PERF-001", competency_id),
            )
            connection.execute(
                """
                INSERT INTO student_competency_confirmations (
                    student_id,
                    competency_id,
                    confirmed_rating,
                    confirmed_at,
                    note
                )
                VALUES (?, ?, '+', ?, 'Historischer Stand')
                """,
                (student_id, competency_id, timestamp),
            )
            connection.executemany(
                """
                INSERT INTO persistence_events (
                    operation_token,
                    operation_index,
                    operation_payload_hash,
                    event_kind,
                    student_id,
                    competency_id,
                    observation_id,
                    technical_timestamp,
                    ordering_state
                )
                VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        "historical-observation-performance",
                        payload_hash,
                        PersistenceEventKind.HISTORICAL_OBSERVATION_STATE.value,
                        student_id,
                        competency_id,
                        "OBS-PERF-001",
                        timestamp,
                        PersistenceOrderingState.UNKNOWN.value,
                    ),
                    (
                        "historical-confirmation-performance",
                        payload_hash,
                        PersistenceEventKind.HISTORICAL_CONFIRMATION_STATE.value,
                        student_id,
                        competency_id,
                        None,
                        timestamp,
                        PersistenceOrderingState.UNKNOWN.value,
                    ),
                ),
            )


def _batch_statuses_for_student(
    adapter: StudentDesktopAdapter,
    student_id: str,
):
    batch = SQLiteStudentDocumentationProjectionRepository(
        adapter.database
    ).read_batch(as_of=AS_OF)
    return adapter._competency_status_projection_from_sources(
        observations=batch.observations_by_student.get(student_id, ()),
        confirmations=batch.confirmations_by_student.get(student_id, ()),
        freshness_by_competency=batch.freshness_by_student.get(student_id, {}),
        competencies=batch.competencies,
    )


def _canonical_heatmap_per_student(
    adapter: StudentDesktopAdapter,
) -> DashboardDocumentationHeatmapViewModel:
    students = tuple(
        student
        for student in SQLiteStudentRepository(
            adapter.database,
            as_of=AS_OF,
        ).list_students()
        if student.active
    )
    statuses_by_student = {
        student.student_id: adapter.list_documentation_status_for_student(
            student.student_id
        )
        for student in students
    }
    groups: list[DashboardDocumentationGroupViewModel] = []
    for group in adapter.list_groups():
        group_students = tuple(
            student for student in students if student.group_id == group.group_id
        )
        subject_totals: dict[str, list[object]] = {}
        for student in group_students:
            for status in statuses_by_student[student.student_id]:
                values = subject_totals.setdefault(
                    status.subject_id,
                    [
                        status.subject_display_name,
                        0,
                        0,
                        status.sort_order,
                    ],
                )
                values[1] = int(values[1]) + int(status.documented_count > 0)
                values[2] = int(values[2]) + 1
                values[3] = min(int(values[3]), status.sort_order)
        cells = tuple(
            DashboardDocumentationCellViewModel(
                subject_id,
                str(values[0]),
                int(values[1]),
                int(values[2]),
            )
            for subject_id, values in sorted(
                subject_totals.items(),
                key=lambda item: (
                    int(item[1][3]),
                    str(item[1][0]).casefold(),
                ),
            )
        )
        groups.append(
            DashboardDocumentationGroupViewModel(
                group.group_id,
                group.group_name,
                cells,
            )
        )
    return DashboardDocumentationHeatmapViewModel(tuple(groups))


def test_batch_matches_canonical_status_and_student_summary(tmp_path: Path) -> None:
    database = _database_with_catalog(tmp_path / "equivalence.sqlite")
    student_id = seed_reference_data().students[0].student_id
    competency_id = "CMP-000241"
    _insert_historical_unknown_state(
        database,
        student_id=student_id,
        competency_id=competency_id,
    )
    adapter = StudentDesktopAdapter(database=database, today_provider=lambda: AS_OF)

    canonical = adapter.list_competency_status_projection_for_student(student_id)
    batched = _batch_statuses_for_student(adapter, student_id)

    assert batched == canonical
    assert next(
        item for item in batched if item.competency_id == competency_id
    ).documentation_state == "confirmation_unknown"
    expected_summary = documentation_summary_from_subjects(
        adapter.list_documentation_status_for_student(student_id)
    )
    actual_item = next(
        item for item in adapter.list_students() if item.student_id == student_id
    )
    assert actual_item.documentation_status == expected_summary
    assert (
        adapter.dashboard_documentation_heatmap()
        == _canonical_heatmap_per_student(adapter)
    )


def _count_statements(
    provider: CountingConnectionProvider,
    operation: Callable[[], object],
) -> tuple[int, int, tuple[str, ...]]:
    provider.reset()
    operation()
    normalized = tuple(" ".join(statement.split()) for statement in provider.statements)
    selects = sum(statement.upper().startswith("SELECT ") for statement in normalized)
    return len(normalized), selects, normalized


def _upsert_course_group(
    database: SQLiteDatabase,
    *,
    course_group_id: str,
    group_ids: tuple[str, ...] = (),
    course_ids: tuple[str, ...] = (),
    active: bool = True,
    sort_order: int = 0,
) -> None:
    SQLiteMasterDataRepository(database).update_course_group(
        MasterDataCourseGroupRecord(
            course_group_id,
            course_group_id,
            group_ids,
            course_ids,
            active,
            sort_order,
        )
    )


def _clear_course_groups(database: SQLiteDatabase) -> None:
    with closing(database.connect()) as connection:
        with connection:
            connection.execute("DELETE FROM course_group_courses")
            connection.execute("DELETE FROM course_group_student_groups")
            connection.execute("DELETE FROM course_groups")


def test_student_list_and_heatmap_have_constant_query_budget(tmp_path: Path) -> None:
    provider = CountingConnectionProvider()
    database = _database_with_catalog(
        tmp_path / "query-budget.sqlite",
        provider=provider,
    )
    adapter = StudentDesktopAdapter(database=database)

    student_budget = _count_statements(provider, adapter.list_students)
    heatmap_budget = _count_statements(
        provider,
        adapter.dashboard_documentation_heatmap,
    )
    dashboard_refresh_budget = _count_statements(
        provider,
        lambda: adapter.dashboard_documentation_refresh(
            target_type="group",
            target_id=seed_reference_data().groups[0].group_id,
            subject_id="deutsch",
            subject_label="Deutsch",
            at=datetime(2026, 8, 13, 8, 15),
        ),
    )
    _clear_course_groups(database)
    no_course_group_budget = _count_statements(
        provider,
        lambda: adapter.dashboard_documentation_refresh(
            target_type="course_group",
            target_id="course-group-missing",
            subject_id="deutsch",
            subject_label="Deutsch",
            at=datetime(2026, 8, 13, 8, 15),
        ),
    )
    group_id = seed_reference_data().groups[0].group_id
    course_ids = tuple(course.course_id for course in seed_reference_data().courses)
    _upsert_course_group(
        database,
        course_group_id="course-group-one",
        group_ids=(group_id,),
        course_ids=course_ids,
    )
    one_course_group_budget = _count_statements(
        provider,
        lambda: adapter.dashboard_documentation_refresh(
            target_type="course_group",
            target_id="course-group-one",
            subject_id="deutsch",
            subject_label="Deutsch",
            at=datetime(2026, 8, 13, 8, 15),
        ),
    )
    master_data = SQLiteMasterDataRepository(database)
    relation_group_ids = [group_id]
    relation_course_ids = list(course_ids)
    for index in range(10):
        relation_group_id = f"GRP-BUDGET-{index:02d}"
        relation_course_id = f"CRS-BUDGET-{index:02d}"
        master_data.upsert_student_group(
            MasterDataGroupRecord(
                relation_group_id,
                relation_group_id,
                True,
                index + 1,
            )
        )
        master_data.upsert_course(
                MasterDataCourseRecord(
                    relation_course_id,
                    relation_course_id,
                    "",
                    "",
                    True,
                    index + 3,
                    (index % 3) + 1,
                )
        )
        relation_group_ids.append(relation_group_id)
        relation_course_ids.append(relation_course_id)
        _upsert_course_group(
            database,
            course_group_id=f"course-group-{index + 2:02d}",
            group_ids=tuple(relation_group_ids),
            course_ids=tuple(relation_course_ids),
            sort_order=index + 2,
        )
    many_course_groups_budget = _count_statements(
        provider,
        lambda: adapter.dashboard_documentation_refresh(
            target_type="course_group",
            target_id="course-group-11",
            subject_id="deutsch",
            subject_label="Deutsch",
            at=datetime(2026, 8, 13, 8, 15),
        ),
    )

    with closing(database.connect()) as connection:
        with connection:
            connection.executemany(
                """
                INSERT INTO observations (
                    observation_id,
                    student_id,
                    date,
                    subject_id,
                    context,
                    note,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, '2026-06-01', 'deutsch', '', '', 1, ?, ?)
                """,
                (
                    (
                        f"OBS-BUDGET-{index:04d}",
                        seed_reference_data().students[
                            index % len(seed_reference_data().students)
                        ].student_id,
                        "2026-06-01T08:00:00+00:00",
                        "2026-06-01T08:00:00+00:00",
                    )
                    for index in range(280)
                ),
            )
            connection.executemany(
                """
                INSERT INTO observation_competency_ratings (
                    observation_id,
                    competency_id,
                    subject_id,
                    subject_display_name,
                    learning_area,
                    competency_group,
                    competency_text,
                    rating
                )
                VALUES (?, 'CMP-000241', 'deutsch', 'Deutsch',
                        'Leseverstehen', 'Lesen', 'Texte verstehen', '+')
                """,
                ((f"OBS-BUDGET-{index:04d}",) for index in range(280)),
            )

    loaded_student_budget = _count_statements(provider, adapter.list_students)
    loaded_heatmap_budget = _count_statements(
        provider,
        adapter.dashboard_documentation_heatmap,
    )

    assert student_budget[:2] == heatmap_budget[:2]
    assert loaded_student_budget[:2] == student_budget[:2]
    assert loaded_heatmap_budget[:2] == heatmap_budget[:2]
    assert student_budget[0] <= 17
    assert student_budget[1] <= 14
    assert dashboard_refresh_budget[0] <= 18
    assert dashboard_refresh_budget[1] <= 15
    assert no_course_group_budget[:2] == one_course_group_budget[:2]
    assert no_course_group_budget[:2] == many_course_groups_budget[:2]
    assert no_course_group_budget[0] <= 20
    assert no_course_group_budget[1] <= 16
    for statements in (
        student_budget[2],
        heatmap_budget[2],
        dashboard_refresh_budget[2],
        no_course_group_budget[2],
        one_course_group_budget[2],
        many_course_groups_budget[2],
        loaded_student_budget[2],
        loaded_heatmap_budget[2],
    ):
        assert not any(
            token in statement.upper()
            for statement in statements
            for token in ("CREATE TABLE", "ALTER TABLE", "DROP TABLE")
        )


def test_course_group_snapshot_preserves_existing_filter_semantics(
    tmp_path: Path,
) -> None:
    database = _database_with_catalog(tmp_path / "course-groups.sqlite")
    adapter = StudentDesktopAdapter(database=database)
    _clear_course_groups(database)
    group_id = seed_reference_data().groups[0].group_id
    course_ids = tuple(course.course_id for course in seed_reference_data().courses)
    _upsert_course_group(
        database,
        course_group_id="course-group-groups-only",
        group_ids=(group_id,),
        sort_order=2,
    )
    _upsert_course_group(
        database,
        course_group_id="course-group-courses-only",
        course_ids=(course_ids[0],),
        sort_order=1,
    )
    _upsert_course_group(
        database,
        course_group_id="course-group-both",
        group_ids=(group_id,),
        course_ids=(course_ids[0],),
        sort_order=3,
    )
    _upsert_course_group(
        database,
        course_group_id="course-group-empty",
        sort_order=4,
    )
    _upsert_course_group(
        database,
        course_group_id="course-group-inactive",
        group_ids=(group_id,),
        course_ids=(course_ids[0],),
        active=False,
        sort_order=5,
    )

    batch = SQLiteStudentDocumentationProjectionRepository(
        database
    ).read_batch(as_of=AS_OF)
    assert tuple(item.course_group_id for item in batch.course_groups) == (
        "course-group-courses-only",
        "course-group-groups-only",
        "course-group-both",
        "course-group-empty",
    )
    assert not adapter.list_students(
        course_group_id="course-group-groups-only"
    )
    assert not adapter.list_students(
        course_group_id="course-group-courses-only"
    )
    assert not adapter.list_students(
        course_group_id="course-group-empty"
    )
    assert not adapter.list_students(
        course_group_id="course-group-missing"
    )

    with closing(database.connect()) as connection:
        with connection:
            connection.execute(
                "UPDATE groups SET active = 0 WHERE group_id = ?", (group_id,)
            )
    assert not adapter.list_students(
        course_group_id="course-group-groups-only"
    )

    heatmap, suggestions = adapter.dashboard_documentation_refresh(
        target_type="course_group",
        target_id="course-group-both",
        subject_id="deutsch",
        subject_label="Deutsch",
        at=datetime(2026, 8, 13, 8, 15),
        limit=100,
    )
    expected_student_ids = tuple(
        student.student_id
        for student in adapter.list_students(
            course_group_id="course-group-both"
        )
    )
    assert heatmap == adapter.dashboard_documentation_heatmap()
    assert {item.student_id for item in suggestions} == set(expected_student_ids)


def test_course_group_refresh_uses_one_snapshot_without_follow_up_read(
    tmp_path: Path,
) -> None:
    provider = CountingConnectionProvider()
    database = _database_with_catalog(
        tmp_path / "course-group-snapshot.sqlite",
        provider=provider,
    )
    group_id = seed_reference_data().groups[0].group_id
    _upsert_course_group(
        database,
        course_group_id="course-group-snapshot",
        group_ids=(group_id,),
        course_ids=tuple(
            course.course_id for course in seed_reference_data().courses
        ),
    )
    with closing(database.connect()) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
    mutated = False

    def mutate_after_student_read(statement: str) -> None:
        nonlocal mutated
        if mutated or "FROM groups" not in statement:
            return
        mutated = True
        with closing(sqlite3.connect(database.path)) as writer:
            writer.execute(
                "UPDATE course_groups SET active = 0 WHERE course_group_id = ?",
                ("course-group-snapshot",),
            )
            writer.commit()

    provider.on_statement = mutate_after_student_read
    adapter = StudentDesktopAdapter(database=database)
    heatmap, suggestions = adapter.dashboard_documentation_refresh(
        target_type="course_group",
        target_id="course-group-snapshot",
        subject_id="deutsch",
        subject_label="Deutsch",
        at=datetime(2026, 8, 13, 8, 15),
        limit=100,
    )
    provider.on_statement = None

    assert mutated
    assert heatmap == adapter.dashboard_documentation_heatmap()
    assert suggestions
    assert not any(
        item.course_group_id == "course-group-snapshot"
        for item in SQLiteStudentDocumentationProjectionRepository(
            database
        ).read_batch(as_of=AS_OF).course_groups
    )


def test_read_repository_constructors_do_not_initialize_schema() -> None:
    class DatabaseWithoutReadInitialization:
        def initialize_schema(self) -> None:
            raise AssertionError("Read-Konstruktor darf kein Schema initialisieren")

        def ensure_master_data_defaults(self) -> None:
            raise AssertionError("Read-Konstruktor darf keine Defaults schreiben")

    database = DatabaseWithoutReadInitialization()

    SQLiteDocumentationSubjectSettingsRepository(database)
    SQLiteStudentCompetencyConfirmationRepository(database)
    SQLiteMasterDataRepository(database)
    SQLiteStudentDocumentationProjectionRepository(database)
