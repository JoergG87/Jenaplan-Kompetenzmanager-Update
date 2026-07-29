"""Focused SJ-2B schema, migration, rollback and isolation tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, fields, replace
from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

import src.core.school_year_migration as migration_module
from src.core.database_compatibility import (
    DATABASE_COMPATIBILITY_VERSION,
    V2_COMPATIBILITY_FINGERPRINT,
    DatabaseCompatibilityInspector,
)
from src.core.records import StudentRecord
from src.core.school_year import (
    CourseYearLevelConfirmation,
    SchoolYear,
    SchoolYearInitializationPlan,
    SchoolYearSchemaInformation,
    SchoolYearStatus,
    build_school_year_initialization_plan,
    build_school_year_initialization_preview,
)
from src.core.school_year_migration import (
    SCHOOL_YEAR_MIGRATION_ENGINE_FORMAT_VERSION,
    TARGET_V3_DATABASE_VERSION,
    V3_SCHEMA_FINGERPRINT,
    SchoolYearMigrationError,
    SchoolYearMigrationErrorCode,
    SchoolYearMigrationFailpoint,
    SchoolYearV2ToV3MigrationEngine,
    VerifiedBackupEvidence,
    calculate_v2_source_state_sha256,
)
from src.core.sqlite_store import SQLiteDatabase


GROUP_ID = "GRP-SJ2B-1"
SECOND_GROUP_ID = "GRP-SJ2B-2"
COURSE_ID = "CRS-SJ2B-1"
PARALLEL_COURSE_ID = "CRS-SJ2B-1B"
THIRD_COURSE_ID = "CRS-SJ2B-3"
ACTIVE_STUDENT_ID = "STD-SJ2B-A"
ARCHIVED_STUDENT_ID = "STD-SJ2B-H"
SCHOOL_YEAR_ID = "SY-SJ2B-2025-26"


class TrackingConnectionFactory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.calls = 0
        self.connections: list[sqlite3.Connection] = []

    def __call__(self) -> sqlite3.Connection:
        self.calls += 1
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self.connections.append(connection)
        return connection


@dataclass
class MigrationScenario:
    path: Path
    plan: SchoolYearInitializationPlan
    evidence: VerifiedBackupEvidence
    factory: TrackingConnectionFactory
    document_path: Path | None
    preserved_rows: dict[str, tuple[tuple[object, ...], ...]]

    def engine(self) -> SchoolYearV2ToV3MigrationEngine:
        return SchoolYearV2ToV3MigrationEngine(self.factory)


def _initial_school_year(
    *,
    label: str = "2025/26",
    status: SchoolYearStatus = SchoolYearStatus.CURRENT,
) -> SchoolYear:
    return SchoolYear(
        SCHOOL_YEAR_ID,
        label,
        date(2025, 8, 1),
        date(2026, 7, 31),
        status,
    )


def _student_records(connection: sqlite3.Connection) -> tuple[StudentRecord, ...]:
    return tuple(
        StudentRecord(
            student_id=str(row[0]),
            first_name=str(row[1]),
            last_name=str(row[2]),
            group_id=str(row[3]),
            course_id=str(row[4]),
            student_notes="" if row[5] is None else str(row[5]),
            active=bool(row[6]),
            created_at=str(row[7]),
            updated_at=str(row[8]),
            archived_at=None if row[9] is None else str(row[9]),
        )
        for row in connection.execute(
            """
            SELECT student_id, first_name, last_name, group_id, course_id,
                   student_notes, active, created_at, updated_at, archived_at
            FROM students ORDER BY student_id
            """
        ).fetchall()
    )


def _course_confirmations(
    connection: sqlite3.Connection,
) -> tuple[CourseYearLevelConfirmation, ...]:
    levels = {
        COURSE_ID: 1,
        PARALLEL_COURSE_ID: 1,
        THIRD_COURSE_ID: 3,
    }
    return tuple(
        CourseYearLevelConfirmation(str(row[0]), levels[str(row[0])])
        for row in connection.execute(
            "SELECT course_id FROM courses ORDER BY course_id"
        ).fetchall()
    )


def _build_plan(connection: sqlite3.Connection) -> SchoolYearInitializationPlan:
    initial = _initial_school_year()
    groups = tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT group_id FROM groups ORDER BY group_id"
        ).fetchall()
    )
    courses = tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT course_id FROM courses ORDER BY course_id"
        ).fetchall()
    )
    preview = build_school_year_initialization_preview(
        _student_records(connection),
        initial,
        groups,
        courses,
    )
    plan = build_school_year_initialization_plan(
        initial_school_year=initial,
        confirmed_course_year_levels=_course_confirmations(connection),
        preview=preview,
        source_schema=SchoolYearSchemaInformation(
            2,
            V2_COMPATIBILITY_FINGERPRINT,
        ),
        target_schema=SchoolYearSchemaInformation(
            TARGET_V3_DATABASE_VERSION,
            V3_SCHEMA_FINGERPRINT,
        ),
        source_state_sha256="0" * 64,
    )
    return replace(
        plan,
        source_state_sha256=calculate_v2_source_state_sha256(connection, plan),
    )


def _seed_reference_data(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO groups(group_id, group_name, sort_order, active)
        VALUES (?, ?, ?, ?)
        """,
        (
            (GROUP_ID, "Stammgruppe Grün", 1, 1),
            (SECOND_GROUP_ID, "Stammgruppe Blau", 2, 1),
        ),
    )
    connection.executemany(
        """
        INSERT INTO courses(
            course_id, course_name, color_key, color_name, color_hex,
            sort_order, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (COURSE_ID, "Kurs Eins A", "blue", "Blau", "#123456", 1, 1),
            (
                PARALLEL_COURSE_ID,
                "Kurs Eins B",
                None,
                "",
                "",
                2,
                1,
            ),
            (THIRD_COURSE_ID, "Kurs Drei", "green", "Grün", "#00aa00", 3, 1),
        ),
    )


def _seed_students(
    connection: sqlite3.Connection,
    *,
    blocked_student: bool,
) -> None:
    connection.executemany(
        """
        INSERT INTO students(
            student_id, first_name, last_name, group_id, course_id,
            student_notes, active, created_at, updated_at, archived_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                ACTIVE_STUDENT_ID,
                "Ada",
                "Aktiv",
                GROUP_ID,
                COURSE_ID,
                "synthetische Notiz",
                1,
                "2025-08-01T08:00:00+00:00",
                "2025-08-02T08:00:00+00:00",
                None,
            ),
            (
                ARCHIVED_STUDENT_ID,
                "Henri",
                "Historisch",
                SECOND_GROUP_ID,
                PARALLEL_COURSE_ID,
                "",
                0,
                "2025-08-01T08:00:00+00:00",
                "2026-02-10T08:00:00+00:00",
                None
                if blocked_student
                else "2026-02-10T10:00:00+00:00",
            ),
        ),
    )


def _seed_preserved_children(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> Path:
    connection.execute(
        """
        INSERT INTO observations(
            observation_id, student_id, date, subject_id, context, note,
            active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "OBS-SJ2B-1",
            ACTIVE_STUDENT_ID,
            "2025-09-01",
            "SUB-DE",
            "synthetic",
            "preserved",
            1,
            "2025-09-01T10:00:00+00:00",
            "2025-09-01T10:00:00+00:00",
        ),
    )
    document = tmp_path / "synthetic-document.bin"
    document.write_bytes(b"SJ-2B synthetic document bytes")
    connection.execute(
        """
        INSERT INTO documents(
            document_id, student_id, observation_id, title, document_type,
            file_path, original_filename, created_at, note, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "DOC-SJ2B-1",
            ACTIVE_STUDENT_ID,
            "OBS-SJ2B-1",
            "Synthetischer Beleg",
            "application/octet-stream",
            "documents/synthetic-document.bin",
            "synthetic-document.bin",
            "2025-09-01T10:00:00+00:00",
            "metadata preserved",
            1,
        ),
    )
    connection.execute(
        """
        INSERT INTO report_drafts(
            report_draft_id, student_id, report_type, period_start, period_end,
            status, teacher_name, overall_text, created_at, updated_at
        ) VALUES (?, ?, 'learning_development', ?, ?, 'draft', ?, ?, ?, ?)
        """,
        (
            "RPD-SJ2B-1",
            ACTIVE_STUDENT_ID,
            "2025-08-01",
            "2026-01-31",
            "Testlehrkraft",
            "synthetischer Entwurf",
            "2026-01-01T10:00:00+00:00",
            "2026-01-02T10:00:00+00:00",
        ),
    )
    connection.execute(
        """
        INSERT INTO learning_reports(
            learning_report_id, source_report_draft_id, student_id,
            report_type, period_start, period_end, created_at
        ) VALUES (?, ?, ?, 'learning_development', ?, ?, ?)
        """,
        (
            "RPT-SJ2B-1",
            "RPD-SJ2B-1",
            ACTIVE_STUDENT_ID,
            "2025-08-01",
            "2026-01-31",
            "2026-02-01T10:00:00+00:00",
        ),
    )
    report_snapshot = '{"schema_version":1,"synthetic":"report"}'
    connection.execute(
        """
        INSERT INTO learning_report_revisions(
            learning_report_revision_id, learning_report_id, revision_number,
            status, snapshot_schema_version, snapshot_json, snapshot_sha256,
            finalized_at, finalized_by_display_name, superseded_at
        ) VALUES (?, ?, 1, 'finalized', 1, ?, ?, ?, ?, NULL)
        """,
        (
            "RPV-SJ2B-1",
            "RPT-SJ2B-1",
            report_snapshot,
            hashlib.sha256(report_snapshot.encode()).hexdigest(),
            "2026-02-01T10:00:00+00:00",
            "Testlehrkraft",
        ),
    )
    connection.execute(
        """
        INSERT INTO learning_report_pdf_artifacts(
            learning_report_pdf_artifact_id, learning_report_revision_id,
            relative_file_path, mime_type, file_size_bytes, snapshot_sha256,
            pdf_sha256, created_at
        ) VALUES (?, ?, ?, 'application/pdf', ?, ?, ?, ?)
        """,
        (
            "RPA-SJ2B-1",
            "RPV-SJ2B-1",
            "reports/synthetic.pdf",
            64,
            hashlib.sha256(report_snapshot.encode()).hexdigest(),
            "a" * 64,
            "2026-02-01T10:00:00+00:00",
        ),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_drafts(
            learning_conference_draft_id, student_id, status,
            created_at, updated_at
        ) VALUES (?, ?, 'draft', ?, ?)
        """,
        (
            "LCD-SJ2B-1",
            ACTIVE_STUDENT_ID,
            "2026-02-01T10:00:00+00:00",
            "2026-02-02T10:00:00+00:00",
        ),
    )
    connection.execute(
        """
        INSERT INTO learning_conferences(
            learning_conference_id, source_learning_conference_draft_id,
            student_id, created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            "LCF-SJ2B-1",
            "LCD-SJ2B-1",
            ACTIVE_STUDENT_ID,
            "2026-02-03T10:00:00+00:00",
        ),
    )
    leg_snapshot = '{"schema_version":1,"synthetic":"leg"}'
    connection.execute(
        """
        INSERT INTO learning_conference_revisions(
            learning_conference_revision_id, learning_conference_id,
            revision_number, status, snapshot_schema_version, snapshot_json,
            snapshot_sha256, completed_at, completed_by_display_name,
            superseded_at
        ) VALUES (?, ?, 1, 'completed', 1, ?, ?, ?, ?, NULL)
        """,
        (
            "LCV-SJ2B-1",
            "LCF-SJ2B-1",
            leg_snapshot,
            hashlib.sha256(leg_snapshot.encode()).hexdigest(),
            "2026-02-03T10:00:00+00:00",
            "Testlehrkraft",
        ),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_pdf_artifacts(
            learning_conference_pdf_artifact_id,
            learning_conference_revision_id, relative_file_path, mime_type,
            file_size_bytes, snapshot_sha256, pdf_sha256, created_at
        ) VALUES (?, ?, ?, 'application/pdf', ?, ?, ?, ?)
        """,
        (
            "LPA-SJ2B-1",
            "LCV-SJ2B-1",
            "conferences/synthetic.pdf",
            64,
            hashlib.sha256(leg_snapshot.encode()).hexdigest(),
            "b" * 64,
            "2026-02-03T10:00:00+00:00",
        ),
    )
    return document


_PRESERVED_TABLES = (
    "observations",
    "documents",
    "report_drafts",
    "learning_reports",
    "learning_report_revisions",
    "learning_report_pdf_artifacts",
    "learning_conference_drafts",
    "learning_conferences",
    "learning_conference_revisions",
    "learning_conference_pdf_artifacts",
)


def _all_rows(
    connection: sqlite3.Connection,
    table: str,
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        tuple(row)
        for row in connection.execute(
            f"SELECT * FROM {table} ORDER BY 1"
        ).fetchall()
    )


def _scenario(
    tmp_path: Path,
    *,
    with_students: bool = True,
    with_children: bool = True,
    blocked_student: bool = False,
    name: str = "scenario",
) -> MigrationScenario:
    path = tmp_path / f"{name}.sqlite"
    SQLiteDatabase(path).initialize_schema()
    document_path: Path | None = None
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _seed_reference_data(connection)
        if with_students:
            _seed_students(connection, blocked_student=blocked_student)
        if with_students and with_children and not blocked_student:
            document_path = _seed_preserved_children(connection, tmp_path)
        connection.commit()
        plan = _build_plan(connection)
        preserved = {
            table: _all_rows(connection, table) for table in _PRESERVED_TABLES
        }
    evidence = VerifiedBackupEvidence(
        backup_sha256="a" * 64,
        source_state_sha256=plan.source_state_sha256,
        source_schema_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
        verified_at="2026-07-29T12:00:00+00:00",
        backup_id=f"synthetic-{name}",
    )
    return MigrationScenario(
        path=path,
        plan=plan,
        evidence=evidence,
        factory=TrackingConnectionFactory(path),
        document_path=document_path,
        preserved_rows=preserved,
    )


def _migrate(scenario: MigrationScenario, **overrides):
    values = {
        "plan": scenario.plan,
        "operation_token": "operation-sj2b",
        "backup_evidence": scenario.evidence,
        "expected_v2_fingerprint": V2_COMPATIBILITY_FINGERPRINT,
        "expected_v3_fingerprint": V3_SCHEMA_FINGERPRINT,
    }
    values.update(overrides)
    return scenario.engine().migrate(**values)


def _v2_snapshot(path: Path) -> dict[str, object]:
    with sqlite3.connect(path) as connection:
        identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
            connection
        )
        tables = tuple(
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        )
        return {
            "version": int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            ),
            "fingerprint": identity.fingerprint,
            "tables": tables,
            "counts": {
                table: int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                )
                for table in tables
            },
            "student_columns": tuple(
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(students)"
                ).fetchall()
            ),
        }


def _corrupt(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def _assert_v2_unchanged(path: Path, before: dict[str, object]) -> None:
    assert _v2_snapshot(path) == before
    with sqlite3.connect(path) as connection:
        assert [
            tuple(row)
            for row in connection.execute("PRAGMA integrity_check").fetchall()
        ] == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert not connection.execute(
            """
            SELECT 1 FROM sqlite_schema
            WHERE name IN (
                'school_years',
                'student_school_year_assignments',
                'school_year_transitions'
            )
            """
        ).fetchall()


def test_successful_synthetic_pilot_migration_preserves_business_data(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path)
    document_sha = hashlib.sha256(
        scenario.document_path.read_bytes()  # type: ignore[union-attr]
    ).hexdigest()

    result = _migrate(scenario)

    assert result.target_schema_fingerprint == V3_SCHEMA_FINGERPRINT
    assert result.post_reopen_verified is True
    assert scenario.factory.calls == 2
    assert len({id(item) for item in scenario.factory.connections}) == 2
    for closed_connection in scenario.factory.connections:
        with pytest.raises(sqlite3.ProgrammingError):
            closed_connection.execute("SELECT 1")
    with sqlite3.connect(scenario.path) as connection:
        connection.row_factory = sqlite3.Row
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
            connection
        )
        assert identity.fingerprint == V3_SCHEMA_FINGERPRINT
        assert tuple(
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(students)"
            ).fetchall()
        ) == (
            "student_id",
            "first_name",
            "last_name",
            "notes",
            "active",
            "created_at",
            "updated_at",
            "archived_at",
        )
        assert [
            tuple(row)
            for row in connection.execute(
                "SELECT first_name, last_name, notes FROM students ORDER BY student_id"
            ).fetchall()
        ] == [
            ("Ada", "Aktiv", "synthetische Notiz"),
            ("Henri", "Historisch", ""),
        ]
        assert [
            tuple(row)
            for row in connection.execute(
            """
            SELECT course_id, course_name, color_key, color_name, color_hex,
                   sort_order, active, year_level
            FROM courses ORDER BY course_id
            """
            ).fetchall()
        ] == [
            (COURSE_ID, "Kurs Eins A", "blue", "Blau", "#123456", 1, 1, 1),
            (PARALLEL_COURSE_ID, "Kurs Eins B", None, "", "", 2, 1, 1),
            (THIRD_COURSE_ID, "Kurs Drei", "green", "Grün", "#00aa00", 3, 1, 3),
        ]
        assignments = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT student_id, school_year_id, group_id, course_id,
                       assignment_status, valid_from, valid_to
                FROM student_school_year_assignments ORDER BY student_id
                """
            ).fetchall()
        ]
        assert assignments == [
            (
                ACTIVE_STUDENT_ID,
                SCHOOL_YEAR_ID,
                GROUP_ID,
                COURSE_ID,
                "enrolled",
                "2025-08-01",
                "2026-07-31",
            ),
            (
                ARCHIVED_STUDENT_ID,
                SCHOOL_YEAR_ID,
                SECOND_GROUP_ID,
                PARALLEL_COURSE_ID,
                "enrolled",
                "2025-08-01",
                "2026-02-09",
            ),
        ]
        receipt = connection.execute(
            """
            SELECT from_school_year_id, to_school_year_id, plan_sha256,
                   backup_sha256, result_counts_json
            FROM school_year_transitions
            """
        ).fetchone()
        assert receipt[0] is None
        assert receipt[1] == SCHOOL_YEAR_ID
        assert receipt[2] == scenario.plan.plan_sha256
        assert receipt[3] == scenario.evidence.backup_sha256
        assert receipt[4] == (
            '{"assignments":2,"courses":3,"school_years":1,"students":2}'
        )
        assert all(
            private_value not in receipt[4]
            for private_value in (
                "Ada",
                "Henri",
                "synthetische Notiz",
                "documents/",
            )
        )
        assert json.loads(receipt[4]) == {
            "assignments": 2,
            "courses": 3,
            "school_years": 1,
            "students": 2,
        }
        assert connection.execute(
            "SELECT COUNT(*) FROM school_years WHERE status = 'current'"
        ).fetchone()[0] == 1
        for table, rows in scenario.preserved_rows.items():
            assert _all_rows(connection, table) == rows
        assert [
            tuple(row)
            for row in connection.execute("PRAGMA integrity_check").fetchall()
        ] == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert hashlib.sha256(
        scenario.document_path.read_bytes()  # type: ignore[union-attr]
    ).hexdigest() == document_sha


def test_empty_student_inventory_migrates_with_zero_assignments(
    tmp_path: Path,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_students=False,
        with_children=False,
        name="empty",
    )

    result = _migrate(scenario)

    assert json.loads(result.result_counts_json)["students"] == 0
    assert json.loads(result.result_counts_json)["assignments"] == 0


@pytest.fixture
def migrated(tmp_path: Path) -> MigrationScenario:
    scenario = _scenario(tmp_path, with_children=False, name="schema")
    _migrate(scenario)
    return scenario


def test_v3_schema_has_exact_registered_fingerprint(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
            connection
        )
        assert identity.fingerprint == (
            "640a10a76b292eca3a2ba47255711db87e27d4eaa1580fcc58086035cb8d6cd1"
        )
        assert identity.fingerprint == V3_SCHEMA_FINGERPRINT


def test_v3_schema_inventory_matches_registered_tables_indexes_and_triggers(
    migrated: MigrationScenario,
) -> None:
    expected_tables = {
        "school_years",
        "student_school_year_assignments",
        "school_year_transitions",
    }
    expected_indexes = {
        "idx_school_years_one_current",
        "idx_school_years_date_range",
        "idx_school_years_status_start",
        "idx_assignments_student_year_interval",
        "idx_assignments_student_interval",
        "idx_assignments_year_status_student",
        "idx_assignments_year_group_interval",
        "idx_assignments_year_course_interval",
        "idx_assignments_last_known",
    }
    expected_triggers = {
        "trg_school_years_no_overlap_insert",
        "trg_school_years_no_overlap_update",
        "trg_school_years_status_transition",
        "trg_school_years_closed_immutable",
        "trg_school_years_dates_guard",
        "trg_school_years_no_delete",
        "trg_assignments_within_school_year_insert",
        "trg_assignments_within_school_year_update",
        "trg_assignments_no_overlap_insert",
        "trg_assignments_no_overlap_update",
        "trg_assignments_update_guard",
        "trg_assignments_no_delete",
        "trg_school_year_transitions_no_update",
        "trg_school_year_transitions_no_delete",
    }
    with sqlite3.connect(migrated.path) as connection:
        objects = connection.execute(
            """
            SELECT type, name FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
        tables = {str(name) for kind, name in objects if kind == "table"}
        indexes = {
            str(name)
            for kind, name in objects
            if kind == "index"
            and (
                str(name).startswith("idx_school_years_")
                or str(name).startswith("idx_assignments_")
            )
        }
        triggers = {
            str(name)
            for kind, name in objects
            if kind == "trigger"
            and (
                str(name).startswith("trg_school_years_")
                or str(name).startswith("trg_assignments_")
                or str(name).startswith("trg_school_year_transitions_")
            )
        }
        assert expected_tables <= tables
        assert indexes == expected_indexes
        assert triggers == expected_triggers
        assert not any(name.startswith("__sj2b_") for name in tables)
        foreign_keys = {
            (str(row[3]), str(row[2]), str(row[4]), str(row[5]), str(row[6]))
            for row in connection.execute(
                "PRAGMA foreign_key_list(student_school_year_assignments)"
            ).fetchall()
        }
        assert foreign_keys == {
            ("student_id", "students", "student_id", "RESTRICT", "RESTRICT"),
            (
                "school_year_id",
                "school_years",
                "school_year_id",
                "RESTRICT",
                "RESTRICT",
            ),
            ("group_id", "groups", "group_id", "RESTRICT", "RESTRICT"),
            ("course_id", "courses", "course_id", "RESTRICT", "RESTRICT"),
        }


def test_second_current_school_year_is_blocked(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_years VALUES(
                    'SY-2027', '2026/27', '2026-08-01', '2027-07-31',
                    'current', '2026-07-29T12:00:00+00:00', NULL
                )
                """
            )


@pytest.mark.parametrize(
    ("school_year_id", "start_date", "end_date"),
    (
        ("SY-OVERLAP", "2026-07-01", "2027-06-30"),
        ("SY-BOUNDARY", "2026-07-31", "2026-07-31"),
    ),
)
def test_school_year_overlap_including_equal_boundary_is_blocked(
    migrated: MigrationScenario,
    school_year_id: str,
    start_date: str,
    end_date: str,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_years VALUES(
                    ?, 'overlap', ?, ?, 'planned',
                    '2026-07-29T12:00:00+00:00', NULL
                )
                """,
                (school_year_id, start_date, end_date),
            )


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    (
        ("2025-02-30", "2025-03-01"),
        ("2025-13-01", "2025-13-02"),
        ("2025-01-01x", "2025-01-02"),
    ),
)
def test_invalid_real_or_canonical_school_year_dates_are_blocked(
    migrated: MigrationScenario,
    start_date: str,
    end_date: str,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_years VALUES(
                    'SY-BAD-DATE', 'bad', ?, ?, 'planned',
                    '2026-07-29T12:00:00+00:00', NULL
                )
                """,
                (start_date, end_date),
            )


def test_invalid_assignment_calendar_date_is_blocked(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (
                    'ASY-BAD-DATE', ?, ?, ?, ?, 'enrolled',
                    '2025-02-30', '2025-03-01', ?, ?
                )
                """,
                (
                    ACTIVE_STUDENT_ID,
                    SCHOOL_YEAR_ID,
                    GROUP_ID,
                    COURSE_ID,
                    "2026-07-29T12:00:00+00:00",
                    "2026-07-29T12:00:00+00:00",
                ),
            )


def test_invalid_status_transition_and_closed_mutation_are_blocked(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute(
            """
            INSERT INTO school_years VALUES(
                'SY-FUTURE', '2026/27', '2026-08-01', '2027-07-31',
                'planned', '2026-07-29T12:00:00+00:00', NULL
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE school_years
                SET status = 'closed', closed_at = '2026-07-29T12:00:00+00:00'
                WHERE school_year_id = 'SY-FUTURE'
                """
            )
        connection.execute(
            """
            UPDATE school_years
            SET status = 'closed', closed_at = '2026-07-29T12:00:00+00:00'
            WHERE school_year_id = ?
            """,
            (SCHOOL_YEAR_ID,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE school_years SET label = 'changed' WHERE school_year_id = ?",
                (SCHOOL_YEAR_ID,),
            )


def test_productive_deletes_are_blocked(migrated: MigrationScenario) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement, parameters in (
            (
                "DELETE FROM student_school_year_assignments WHERE student_id = ?",
                (ACTIVE_STUDENT_ID,),
            ),
            (
                "DELETE FROM school_year_transitions WHERE to_school_year_id = ?",
                (SCHOOL_YEAR_ID,),
            ),
            (
                "DELETE FROM school_years WHERE school_year_id = ?",
                (SCHOOL_YEAR_ID,),
            ),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement, parameters)


@pytest.mark.parametrize(
    ("valid_from", "valid_to"),
    (
        ("2025-07-31", "2025-08-02"),
        ("2025-09-01", "2025-09-30"),
        ("2025-07-01", "2027-01-01"),
        ("2026-07-31", "2026-07-31"),
        ("2025-08-01", "2026-07-31"),
    ),
)
def test_assignment_outside_year_or_any_overlap_is_blocked(
    migrated: MigrationScenario,
    valid_from: str,
    valid_to: str,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'enrolled', ?, ?, ?, ?)
                """,
                (
                    f"ASY-OVERLAP-{valid_from}",
                    ACTIVE_STUDENT_ID,
                    SCHOOL_YEAR_ID,
                    GROUP_ID,
                    COURSE_ID,
                    valid_from,
                    valid_to,
                    "2026-07-29T12:00:00+00:00",
                    "2026-07-29T12:00:00+00:00",
                ),
            )


def test_assignment_outside_school_year_is_blocked_without_overlap(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (
                'STD-NO-ASSIGNMENT', 'No', 'Assignment', '', 1,
                '2026-01-01T10:00:00+00:00',
                '2026-01-01T10:00:00+00:00', NULL
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (
                    'ASY-OUTSIDE', 'STD-NO-ASSIGNMENT', ?, ?, ?,
                    'enrolled', '2025-07-31', '2025-07-31', ?, ?
                )
                """,
                (
                    SCHOOL_YEAR_ID,
                    GROUP_ID,
                    COURSE_ID,
                    "2026-07-29T12:00:00+00:00",
                    "2026-07-29T12:00:00+00:00",
                ),
            )


@pytest.mark.parametrize(
    ("status", "group_id", "course_id"),
    (
        ("enrolled", None, COURSE_ID),
        ("enrolled", GROUP_ID, None),
        ("exited", GROUP_ID, COURSE_ID),
    ),
)
def test_assignment_status_membership_shape_is_enforced(
    migrated: MigrationScenario,
    status: str,
    group_id: str | None,
    course_id: str | None,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES ('ASY-BAD-SHAPE', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ACTIVE_STUDENT_ID,
                    SCHOOL_YEAR_ID,
                    group_id,
                    course_id,
                    status,
                    "2025-08-01",
                    "2025-08-01",
                    "2026-07-29T12:00:00+00:00",
                    "2026-07-29T12:00:00+00:00",
                ),
            )


@pytest.mark.parametrize("year_level", (None, 0, 4, "zwei"))
def test_invalid_course_year_level_is_blocked(
    migrated: MigrationScenario,
    year_level: object,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO courses(
                    course_id, course_name, color_key, color_name, color_hex,
                    sort_order, active, year_level
                ) VALUES ('CRS-BAD-LEVEL', 'bad', NULL, '', '', 99, 1, ?)
                """,
                (year_level,),
            )


@pytest.mark.parametrize("year_level", (1, 2, 3))
def test_valid_course_year_levels_are_allowed(
    migrated: MigrationScenario,
    year_level: int,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute(
            """
            INSERT INTO courses(
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active, year_level
            ) VALUES (?, ?, NULL, '', '', 99, 1, ?)
            """,
            (f"CRS-VALID-{year_level}", f"valid {year_level}", year_level),
        )


def test_transition_update_and_delete_are_blocked(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        for statement in (
            "UPDATE school_year_transitions SET result_counts_json = '{}'",
            "DELETE FROM school_year_transitions",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)


def test_transition_requires_distinct_years_and_lowercase_sha256(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO school_years VALUES(
                'SY-FUTURE', '2026/27', '2026-08-01', '2027-07-31',
                'planned', '2026-07-29T12:00:00+00:00', NULL
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_year_transitions VALUES(
                    'SYT-BAD-SAME', 'SY-FUTURE', 'SY-FUTURE',
                    'operation-bad-same', ?, ?, '{}', ?
                )
                """,
                (
                    "c" * 64,
                    "d" * 64,
                    "2026-07-29T12:00:00+00:00",
                ),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO school_year_transitions VALUES(
                    'SYT-BAD-SHA', NULL, 'SY-FUTURE',
                    'operation-bad-sha', ?, ?, '{}', ?
                )
                """,
                (
                    "C" * 64,
                    "d" * 64,
                    "2026-07-29T12:00:00+00:00",
                ),
            )


def test_restrictive_parent_deletes_are_blocked(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement, value in (
            ("DELETE FROM students WHERE student_id = ?", ACTIVE_STUDENT_ID),
            ("DELETE FROM groups WHERE group_id = ?", GROUP_ID),
            ("DELETE FROM courses WHERE course_id = ?", COURSE_ID),
            (
                "DELETE FROM school_years WHERE school_year_id = ?",
                SCHOOL_YEAR_ID,
            ),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement, (value,))


def test_assignment_immutable_fields_and_interval_extension_are_blocked(
    migrated: MigrationScenario,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        assignment_id = connection.execute(
            """
            SELECT assignment_id FROM student_school_year_assignments
            WHERE student_id = ?
            """,
            (ARCHIVED_STUDENT_ID,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE student_school_year_assignments
                SET course_id = ?
                WHERE assignment_id = ?
                """,
                (THIRD_COURSE_ID, assignment_id),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE student_school_year_assignments
                SET valid_to = '2026-03-01',
                    updated_at = '2026-07-30T12:00:00+00:00'
                WHERE assignment_id = ?
                """,
                (assignment_id,),
            )
        connection.execute(
            """
            UPDATE student_school_year_assignments
            SET valid_to = '2026-02-08',
                updated_at = '2026-07-30T12:00:00+00:00'
            WHERE assignment_id = ?
            """,
            (assignment_id,),
        )


@pytest.mark.parametrize(
    ("created_at", "updated_at"),
    (
        (
            "2026-01-01T10:00:00+00:00",
            "2026-01-01T11:00:00+02:00",
        ),
        ("not-a-time", "also-not-a-time"),
    ),
)
def test_assignment_timestamps_require_real_non_decreasing_instants(
    migrated: MigrationScenario,
    created_at: str,
    updated_at: str,
) -> None:
    with sqlite3.connect(migrated.path) as connection:
        connection.execute(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (
                'STD-TIMESTAMP', 'Time', 'Stamp', '', 1,
                '2026-01-01T10:00:00+00:00',
                '2026-01-01T10:00:00+00:00', NULL
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (
                    'ASY-BAD-TIME', 'STD-TIMESTAMP', ?, ?, ?,
                    'enrolled', '2026-03-01', '2026-03-01', ?, ?
                )
                """,
                (
                    SCHOOL_YEAR_ID,
                    GROUP_ID,
                    COURSE_ID,
                    created_at,
                    updated_at,
                ),
            )


@pytest.mark.parametrize(
    "failpoint",
    tuple(
        item
        for item in SchoolYearMigrationFailpoint
        if item
        not in {
            SchoolYearMigrationFailpoint.AFTER_COMMIT,
            SchoolYearMigrationFailpoint.AFTER_REOPEN_BEFORE_VERIFICATION,
        }
    ),
)
def test_every_precommit_failpoint_rolls_back_to_exact_v2(
    tmp_path: Path,
    failpoint: SchoolYearMigrationFailpoint,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"rollback-{failpoint.value}",
    )
    before = _v2_snapshot(scenario.path)

    def hook(point: SchoolYearMigrationFailpoint) -> None:
        if point is failpoint:
            raise RuntimeError("injected")

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, failpoint_hook=hook)

    assert caught.value.code is SchoolYearMigrationErrorCode.MIGRATION_ROLLED_BACK
    assert caught.value.committed is False
    assert caught.value.rollback_verified is True
    for closed_connection in scenario.factory.connections:
        with pytest.raises(sqlite3.ProgrammingError):
            closed_connection.execute("SELECT 1")
    _assert_v2_unchanged(scenario.path, before)


@pytest.mark.parametrize(
    "failpoint",
    (
        SchoolYearMigrationFailpoint.AFTER_COMMIT,
        SchoolYearMigrationFailpoint.AFTER_REOPEN_BEFORE_VERIFICATION,
    ),
)
def test_postcommit_failpoints_leave_recognizable_committed_v3(
    tmp_path: Path,
    failpoint: SchoolYearMigrationFailpoint,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"postcommit-{failpoint.value}",
    )

    def hook(point: SchoolYearMigrationFailpoint) -> None:
        if point is failpoint:
            raise RuntimeError("injected")

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, failpoint_hook=hook)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED
    )
    assert caught.value.committed is True
    with sqlite3.connect(scenario.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert (
            DatabaseCompatibilityInspector.schema_identity_for_connection(
                connection
            ).fingerprint
            == V3_SCHEMA_FINGERPRINT
        )
        receipt = connection.execute(
            "SELECT from_school_year_id, to_school_year_id FROM school_year_transitions"
        ).fetchone()
        assert receipt == (None, SCHOOL_YEAR_ID)


def test_commit_exception_after_durable_commit_is_recovery_state(
    tmp_path: Path,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="durable-commit-error",
    )
    calls = 0

    class CommitRaisesAfterDurableCommit:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self.connection = connection

        def commit(self) -> None:
            self.connection.commit()
            raise RuntimeError("injected commit return failure")

        def __getattr__(self, name):
            return getattr(self.connection, name)

    def factory():
        nonlocal calls
        calls += 1
        connection = sqlite3.connect(scenario.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if calls == 1:
            return CommitRaisesAfterDurableCommit(connection)
        return connection

    with pytest.raises(SchoolYearMigrationError) as caught:
        SchoolYearV2ToV3MigrationEngine(factory).migrate(
            plan=scenario.plan,
            operation_token="operation-durable-commit-error",
            backup_evidence=scenario.evidence,
            expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            expected_v3_fingerprint=V3_SCHEMA_FINGERPRINT,
        )

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED
    )
    assert caught.value.committed is True
    with sqlite3.connect(scenario.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute(
            "SELECT COUNT(*) FROM school_year_transitions"
        ).fetchone()[0] == 1


def test_failed_rollback_reopen_is_not_claimed_as_verified_rollback(
    tmp_path: Path,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="rollback-reopen-failure",
    )
    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("injected reopen failure")
        connection = sqlite3.connect(scenario.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def hook(point: SchoolYearMigrationFailpoint) -> None:
        if point is SchoolYearMigrationFailpoint.AFTER_BEGIN:
            raise RuntimeError("injected migration failure")

    with pytest.raises(SchoolYearMigrationError) as caught:
        SchoolYearV2ToV3MigrationEngine(factory).migrate(
            plan=scenario.plan,
            operation_token="operation-rollback-reopen-failure",
            backup_evidence=scenario.evidence,
            expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            expected_v3_fingerprint=V3_SCHEMA_FINGERPRINT,
            failpoint_hook=hook,
        )

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED
    )
    assert caught.value.committed is None
    assert caught.value.rollback_verified is False
    assert _v2_snapshot(scenario.path)["fingerprint"] == V2_COMPATIBILITY_FINGERPRINT


def test_missing_backup_evidence_blocks_before_schema_change(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="missing-backup")
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, backup_evidence=None)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISSING
    )
    _assert_v2_unchanged(scenario.path, before)


def test_malformed_backup_hash_blocks_before_schema_change(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="bad-backup")
    before = _v2_snapshot(scenario.path)
    evidence = _corrupt(scenario.evidence, backup_sha256="not-a-sha")

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, backup_evidence=evidence)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISMATCH
    )
    _assert_v2_unchanged(scenario.path, before)


def test_backup_evidence_is_frozen_and_rejects_paths_or_naive_time() -> None:
    evidence = VerifiedBackupEvidence(
        backup_sha256="a" * 64,
        source_state_sha256="b" * 64,
        source_schema_fingerprint="c" * 64,
        verified_at="2026-07-29T12:00:00+00:00",
        backup_id="backup-safe-1",
    )
    with pytest.raises(FrozenInstanceError):
        evidence.backup_sha256 = "d" * 64  # type: ignore[misc]
    with pytest.raises(ValueError, match="verified_at"):
        replace(evidence, verified_at="2026-07-29T12:00:00")
    with pytest.raises(ValueError, match="evidence_id"):
        replace(evidence, backup_id="/tmp/not-allowed")


@pytest.mark.parametrize(
    "mutation",
    (
        "UPDATE students SET last_name = 'changed' WHERE student_id = 'STD-SJ2B-A'",
        "UPDATE groups SET group_name = 'changed' WHERE group_id = 'GRP-SJ2B-1'",
        "UPDATE courses SET course_name = 'changed' WHERE course_id = 'CRS-SJ2B-1'",
    ),
)
def test_source_state_detects_relevant_row_changes_before_begin(
    tmp_path: Path,
    mutation: str,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=hashlib.sha256(mutation.encode()).hexdigest()[:8],
    )
    with sqlite3.connect(scenario.path) as connection:
        connection.execute(mutation)
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert caught.value.code is SchoolYearMigrationErrorCode.SOURCE_STATE_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_source_state_detects_relevant_count_and_document_metadata_changes(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, name="count-and-revision-drift")
    with sqlite3.connect(scenario.path) as connection:
        connection.execute(
            """
            INSERT INTO groups(group_id, group_name, sort_order, active)
            VALUES ('GRP-ADDED', 'added', 99, 1)
            """
        )
        connection.execute(
            """
            UPDATE documents
            SET note = 'changed'
            WHERE document_id = 'DOC-SJ2B-1'
            """
        )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert caught.value.code is SchoolYearMigrationErrorCode.SOURCE_STATE_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_schema_change_is_rejected_as_v2_mismatch(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="schema-drift")
    with sqlite3.connect(scenario.path) as connection:
        connection.execute(
            "CREATE INDEX idx_sj2b_unexpected ON groups(active)"
        )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert caught.value.code is SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_backup_must_bind_same_source_state_and_schema(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="backup-binding")
    before = _v2_snapshot(scenario.path)
    evidence = replace(scenario.evidence, source_state_sha256="b" * 64)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, backup_evidence=evidence)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISMATCH
    )
    _assert_v2_unchanged(scenario.path, before)


def test_blocked_plan_is_rejected_before_begin(tmp_path: Path) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        blocked_student=True,
        name="blocked",
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.INITIALIZATION_PLAN_BLOCKED
    )
    _assert_v2_unchanged(scenario.path, before)


@pytest.mark.parametrize("kind", ("missing", "additional"))
def test_incomplete_or_unknown_course_mapping_is_rejected(
    tmp_path: Path,
    kind: str,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"course-map-{kind}",
    )
    confirmations = scenario.plan.confirmed_course_year_levels
    if kind == "missing":
        changed = confirmations[:-1]
    else:
        changed = (
            *confirmations,
            CourseYearLevelConfirmation("CRS-UNKNOWN", 2),
        )
    plan = _corrupt(
        scenario.plan,
        confirmed_course_year_levels=tuple(changed),
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.COURSE_LEVEL_MAPPING_INCOMPLETE
    )
    _assert_v2_unchanged(scenario.path, before)


@pytest.mark.parametrize("kind", ("missing", "duplicate"))
def test_missing_or_duplicate_student_classification_is_rejected(
    tmp_path: Path,
    kind: str,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"student-plan-{kind}",
    )
    classifications = scenario.plan.student_classifications
    changed = (
        classifications[:-1]
        if kind == "missing"
        else (*classifications, classifications[0])
    )
    plan = _corrupt(
        scenario.plan,
        student_classifications=tuple(changed),
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.STUDENT_CLASSIFICATION_MISMATCH
    )
    _assert_v2_unchanged(scenario.path, before)


def test_assignment_plan_difference_is_rejected(tmp_path: Path) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="assignment-difference",
    )
    changed = scenario.plan.assignment_proposals[:-1]
    plan = _corrupt(scenario.plan, assignment_proposals=changed)
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.ASSIGNMENT_PLAN_MISMATCH
    )
    _assert_v2_unchanged(scenario.path, before)


@pytest.mark.parametrize("change", ("initial_year", "course_level", "format"))
def test_source_state_detects_plan_semantic_changes(
    tmp_path: Path,
    change: str,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"plan-source-{change}",
    )
    if change == "initial_year":
        plan = _corrupt(
            scenario.plan,
            confirmed_initial_school_year=_initial_school_year(label="changed"),
        )
    elif change == "course_level":
        confirmations = tuple(
            replace(item, year_level=2)
            if item.course_id == COURSE_ID
            else item
            for item in scenario.plan.confirmed_course_year_levels
        )
        plan = _corrupt(
            scenario.plan,
            confirmed_course_year_levels=confirmations,
        )
    else:
        plan = _corrupt(
            scenario.plan,
            format_version=scenario.plan.format_version + 1,
        )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan)

    assert caught.value.code is SchoolYearMigrationErrorCode.SOURCE_STATE_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_source_state_detects_engine_format_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="engine-format-drift",
    )
    monkeypatch.setattr(
        migration_module,
        "SCHOOL_YEAR_MIGRATION_ENGINE_FORMAT_VERSION",
        SCHOOL_YEAR_MIGRATION_ENGINE_FORMAT_VERSION + 1,
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert caught.value.code is SchoolYearMigrationErrorCode.SOURCE_STATE_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_wrong_expected_v2_fingerprint_is_rejected_before_begin(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="wrong-v2")
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, expected_v2_fingerprint="f" * 64)

    assert caught.value.code is SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_initial_school_year_must_be_current(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="planned-initial")
    plan = _corrupt(
        scenario.plan,
        confirmed_initial_school_year=_initial_school_year(
            status=SchoolYearStatus.PLANNED
        ),
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.INITIALIZATION_PLAN_BLOCKED
    )
    _assert_v2_unchanged(scenario.path, before)


@pytest.mark.parametrize("source", ("expected", "plan"))
def test_wrong_v3_fingerprint_is_rejected_before_begin(
    tmp_path: Path,
    source: str,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"wrong-v3-{source}",
    )
    overrides: dict[str, object] = {}
    if source == "expected":
        overrides["expected_v3_fingerprint"] = "f" * 64
    else:
        overrides["plan"] = _corrupt(
            scenario.plan,
            target_schema=SchoolYearSchemaInformation(3, "f" * 64),
        )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, **overrides)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.V3_FINGERPRINT_MISMATCH
    )
    _assert_v2_unchanged(scenario.path, before)


def test_wrong_plan_source_schema_is_rejected_before_begin(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="wrong-source")
    plan = _corrupt(
        scenario.plan,
        source_schema=SchoolYearSchemaInformation(2, "f" * 64),
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan)

    assert caught.value.code is SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_wrong_v2_user_version_is_rejected_before_begin(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path, with_children=False, name="wrong-v2-version")
    with sqlite3.connect(scenario.path) as connection:
        connection.execute("PRAGMA user_version = 1")
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert caught.value.code is SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
    _assert_v2_unchanged(scenario.path, before)


def test_invalid_legacy_membership_reference_is_rejected(
    tmp_path: Path,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="invalid-reference",
    )
    with sqlite3.connect(scenario.path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "UPDATE students SET course_id = 'CRS-UNKNOWN' WHERE student_id = ?",
            (ACTIVE_STUDENT_ID,),
        )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.STUDENT_CLASSIFICATION_MISMATCH
    )
    assert _v2_snapshot(scenario.path) == before
    with sqlite3.connect(scenario.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall()
        assert not connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE name = 'school_years'"
        ).fetchone()


@pytest.mark.parametrize(
    ("state", "expected_code"),
    (
        ("transaction", SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH),
        ("query_only", SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH),
        ("foreign_keys_off", SchoolYearMigrationErrorCode.FOREIGN_KEY_CHECK_FAILED),
    ),
)
def test_invalid_provider_connection_state_is_rejected(
    tmp_path: Path,
    state: str,
    expected_code: SchoolYearMigrationErrorCode,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name=f"provider-{state}",
    )

    def factory() -> sqlite3.Connection:
        connection = sqlite3.connect(scenario.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if state == "transaction":
            connection.execute("BEGIN")
        elif state == "query_only":
            connection.execute("PRAGMA query_only = ON")
        else:
            connection.execute("PRAGMA foreign_keys = OFF")
        return connection

    engine = SchoolYearV2ToV3MigrationEngine(factory)
    with pytest.raises(SchoolYearMigrationError) as caught:
        engine.migrate(
            plan=scenario.plan,
            operation_token="operation-invalid-provider",
            backup_evidence=scenario.evidence,
            expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            expected_v3_fingerprint=V3_SCHEMA_FINGERPRINT,
        )
    assert caught.value.code is expected_code


def test_v2_foreign_key_check_failure_is_reported_before_begin(
    tmp_path: Path,
) -> None:
    scenario = _scenario(tmp_path, name="fk-preflight")
    with sqlite3.connect(scenario.path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            UPDATE documents
            SET student_id = 'STD-UNKNOWN'
            WHERE document_id = 'DOC-SJ2B-1'
            """
        )
        plan = _build_plan(connection)
    evidence = replace(
        scenario.evidence,
        source_state_sha256=plan.source_state_sha256,
    )
    before = _v2_snapshot(scenario.path)

    with pytest.raises(SchoolYearMigrationError) as caught:
        _migrate(scenario, plan=plan, backup_evidence=evidence)

    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.FOREIGN_KEY_CHECK_FAILED
    )
    assert _v2_snapshot(scenario.path) == before


def test_v2_integrity_check_failure_is_reported_before_begin(
    tmp_path: Path,
) -> None:
    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="integrity-preflight",
    )

    class IntegrityFailureConnection:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self.connection = connection

        def execute(self, statement, parameters=()):
            if statement.strip().lower() == "pragma integrity_check":
                return self.connection.execute("SELECT 'not ok'")
            return self.connection.execute(statement, parameters)

        def __getattr__(self, name):
            return getattr(self.connection, name)

    def factory():
        connection = sqlite3.connect(scenario.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return IntegrityFailureConnection(connection)

    with pytest.raises(SchoolYearMigrationError) as caught:
        SchoolYearV2ToV3MigrationEngine(factory).migrate(
            plan=scenario.plan,
            operation_token="operation-integrity-failure",
            backup_evidence=scenario.evidence,
            expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            expected_v3_fingerprint=V3_SCHEMA_FINGERPRINT,
        )
    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.INTEGRITY_CHECK_FAILED
    )


def test_plain_sqlite_cannot_be_declared_as_sqlcipher(tmp_path: Path) -> None:
    from src.core.database_engine import DatabaseEngine

    scenario = _scenario(
        tmp_path,
        with_children=False,
        name="provider-mismatch",
    )
    with pytest.raises(SchoolYearMigrationError) as caught:
        SchoolYearV2ToV3MigrationEngine(
            scenario.factory,
            provider_engine=DatabaseEngine.SQLCIPHER,
        ).migrate(
            plan=scenario.plan,
            operation_token="operation-provider-mismatch",
            backup_evidence=scenario.evidence,
            expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            expected_v3_fingerprint=V3_SCHEMA_FINGERPRINT,
        )
    assert (
        caught.value.code
        is SchoolYearMigrationErrorCode.CIPHER_INTEGRITY_CHECK_FAILED
    )


def test_runtime_compatibility_and_initialize_schema_remain_v2(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-v2.sqlite"
    assert DATABASE_COMPATIBILITY_VERSION == 2
    SQLiteDatabase(path).initialize_schema()
    SQLiteDatabase(path).initialize_schema()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert (
            DatabaseCompatibilityInspector.schema_identity_for_connection(
                connection
            ).fingerprint
            == V2_COMPATIBILITY_FINGERPRINT
        )
        assert not connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE name = 'school_years'"
        ).fetchone()


def test_runtime_modules_do_not_import_or_activate_migration_engine() -> None:
    runtime_files = (
        Path("src/core/database_compatibility.py"),
        Path("src/core/sqlite_store.py"),
        Path("src/desktop_app/adapters/student_desktop_adapter.py"),
        Path("src/desktop_app/shell.py"),
        Path("src/desktop_app/main.py"),
    )
    for path in runtime_files:
        source = path.read_text(encoding="utf-8")
        assert "school_year_migration" not in source
        assert "SchoolYearV2ToV3MigrationEngine" not in source
        assert "TARGET_V3_DATABASE_VERSION" not in source


def test_migration_module_import_has_no_qt_or_filesystem_side_effect(
    tmp_path: Path,
) -> None:
    script = (
        "import json, pathlib, sys;"
        "before=set(pathlib.Path('.').iterdir());"
        "import src.core.school_year_migration;"
        "after=set(pathlib.Path('.').iterdir());"
        "print(json.dumps({'same':before==after,'pyside':'PySide6' in sys.modules,"
        "'desktop':any(k.startswith('src.desktop_app') for k in sys.modules)}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={"PYTHONPATH": str(Path.cwd())},
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result == {"same": True, "pyside": False, "desktop": False}


def test_failpoints_have_no_environment_or_file_activation_surface() -> None:
    assert SCHOOL_YEAR_MIGRATION_ENGINE_FORMAT_VERSION == 1
    assert len(SchoolYearMigrationFailpoint) == 19
    module_source = Path(
        "src/core/school_year_migration.py"
    ).read_text(encoding="utf-8")
    assert "os.environ" not in module_source
    assert "getenv" not in module_source
    assert "data/" not in module_source
    assert ".executescript(" not in module_source
    assert "VACUUM" not in module_source
    assert "journal_mode" not in module_source
    assert "PySide" not in module_source
    assert "desktop_app" not in module_source
    assert "SQLiteBackupEngine" not in module_source


@pytest.mark.skipif(
    importlib.util.find_spec("sqlcipher3") is None,
    reason="Repository-SQLCipher-Testprovider ist nicht verfügbar.",
)
def test_sqlcipher_provider_runs_isolated_migration_without_fallback(
    tmp_path: Path,
) -> None:
    from src.core.database_engine import DatabaseEngine, SQLCipherConnectionProvider

    provider = SQLCipherConnectionProvider()
    key_material = bytearray(b"s" * 32)
    path = tmp_path / "synthetic-v2.sqlcipher"
    engine_statements: list[str] = []

    class BoundCreationProvider:
        engine = DatabaseEngine.SQLCIPHER

        def connect(self, database_path, *, create, key_material=None):
            return provider.connect(
                database_path,
                create=create,
                key_material=bytes(b"s" * 32),
            )

    try:
        SQLiteDatabase(
            path,
            connection_provider=BoundCreationProvider(),
        ).initialize_schema()
        connection = provider.connect(
            path,
            create=False,
            key_material=key_material,
        )
        try:
            _seed_reference_data(connection)
            _seed_students(connection, blocked_student=False)
            connection.commit()
            plan = _build_plan(connection)
        finally:
            connection.close()

        evidence = VerifiedBackupEvidence(
            backup_sha256="e" * 64,
            source_state_sha256=plan.source_state_sha256,
            source_schema_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            verified_at="2026-07-29T12:00:00+00:00",
            backup_id="synthetic-sqlcipher",
        )

        class LoggingConnection:
            def __init__(self, connection) -> None:
                self.connection = connection

            def execute(self, statement, parameters=()):
                engine_statements.append(statement.strip().lower())
                return self.connection.execute(statement, parameters)

            def __getattr__(self, name):
                return getattr(self.connection, name)

        def factory():
            return LoggingConnection(provider.connect(
                path,
                create=False,
                key_material=key_material,
            ))

        result = SchoolYearV2ToV3MigrationEngine(
            factory,
            provider_engine=DatabaseEngine.SQLCIPHER,
        ).migrate(
            plan=plan,
            operation_token="operation-sqlcipher",
            backup_evidence=evidence,
            expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            expected_v3_fingerprint=V3_SCHEMA_FINGERPRINT,
        )
        assert result.post_reopen_verified is True
        assert engine_statements.count("pragma cipher_integrity_check") == 3
        assert path.read_bytes()[:16] != b"SQLite format 3\x00"
        with sqlite3.connect(path) as plaintext_connection:
            with pytest.raises(sqlite3.DatabaseError):
                plaintext_connection.execute(
                    "SELECT COUNT(*) FROM sqlite_schema"
                ).fetchone()
        reopened = provider.connect(
            path,
            create=False,
            key_material=key_material,
        )
        try:
            assert reopened.execute("PRAGMA user_version").fetchone()[0] == 3
            assert (
                DatabaseCompatibilityInspector.schema_identity_for_connection(
                    reopened
                ).fingerprint
                == V3_SCHEMA_FINGERPRINT
            )
        finally:
            reopened.close()
    finally:
        for index in range(len(key_material)):
            key_material[index] = 0
