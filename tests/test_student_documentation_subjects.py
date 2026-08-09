"""Focused non-visual tests for school-year documentation subjects."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3

import pytest

from src.application.student_documentation_subjects import (
    StudentDocumentationSubjectApplicationError,
    StudentDocumentationSubjectService,
)
from src.core.sqlite_student_documentation_subjects import (
    SQLiteStudentDocumentationSubjectRepository,
)
from src.core.student_documentation_subjects import (
    DocumentationSubjectMode,
    DocumentationSubjectWriteStatus,
)
from tests.helpers.synthetic_v4 import (
    SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v4_database,
)


NOW = datetime(2026, 8, 9, 10, 30, tzinfo=UTC)
SUBJECT_DE = "SUB-TEST-DE"
SUBJECT_EPU = "SUB-TEST-EPU"
SUBJECT_MATH = "SUB-TEST-MATH"
SUBJECT_INACTIVE = "SUB-TEST-HIST"


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = create_synthetic_v4_database(tmp_path / "subjects.sqlite")
    with sqlite3.connect(path) as connection:
        _insert_subject(connection, SUBJECT_MATH, "Mathematik", 2, active=True)
        _insert_subject(connection, SUBJECT_EPU, "EPU", 3, active=True)
        _insert_subject(
            connection,
            SUBJECT_INACTIVE,
            "Historisches Fach",
            4,
            active=False,
        )
    return path


@pytest.fixture
def service(database_path: Path) -> StudentDocumentationSubjectService:
    return _service(database_path)


def test_missing_profile_and_explicit_inherit_use_global_defaults(
    service: StudentDocumentationSubjectService,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]

    configuration = service.configuration(student, SYNTHETIC_SCHOOL_YEAR_ID)
    assert configuration.mode is DocumentationSubjectMode.INHERIT
    assert configuration.profile is None
    assert service.effective_documentation_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_DE, SUBJECT_MATH, SUBJECT_EPU)

    result = service.set_mode(
        student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        DocumentationSubjectMode.INHERIT,
    )
    assert result.status is DocumentationSubjectWriteStatus.NO_CHANGE
    assert result.configuration.profile is None


def test_custom_is_exact_and_global_changes_only_inherit(
    database_path: Path,
) -> None:
    service = _service(database_path)
    custom_student, inherit_student = SYNTHETIC_STUDENT_IDS[:2]
    result = service.replace_custom_subjects(
        custom_student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        (SUBJECT_EPU, SUBJECT_DE),
    )
    assert result.status is DocumentationSubjectWriteStatus.CHANGED
    assert result.configuration.mode is DocumentationSubjectMode.CUSTOM
    assert service.effective_documentation_subjects(
        custom_student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_DE, SUBJECT_EPU)

    _set_global_subjects(database_path, (SUBJECT_MATH,))

    assert service.effective_documentation_subjects(
        inherit_student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_MATH,)
    assert service.effective_documentation_subjects(
        custom_student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_DE, SUBJECT_EPU)


def test_empty_custom_is_distinct_from_inherit(
    service: StudentDocumentationSubjectService,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    result = service.set_mode(
        student, SYNTHETIC_SCHOOL_YEAR_ID, DocumentationSubjectMode.CUSTOM
    )
    assert result.status is DocumentationSubjectWriteStatus.CHANGED
    assert result.configuration.selected_subject_ids == ()
    assert service.effective_documentation_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == ()


def test_switching_custom_to_inherit_clears_selection_and_follows_global(
    database_path: Path,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    service = _service(database_path)
    service.replace_custom_subjects(
        student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        (SUBJECT_DE,),
    )
    _set_global_subjects(database_path, (SUBJECT_MATH, SUBJECT_EPU))

    changed = service.set_mode(
        student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        DocumentationSubjectMode.INHERIT,
    )

    assert changed.status is DocumentationSubjectWriteStatus.CHANGED
    assert changed.configuration.mode is DocumentationSubjectMode.INHERIT
    assert changed.configuration.selected_subject_ids == ()
    assert service.effective_documentation_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_MATH, SUBJECT_EPU)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM student_documentation_subject_selections
            WHERE student_id = ? AND school_year_id = ?
            """,
            (student, SYNTHETIC_SCHOOL_YEAR_ID),
        ).fetchone()[0] == 0


def test_replace_is_atomic_and_noop_preserves_profile_timestamp(
    database_path: Path,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    service = _service(database_path)
    first = service.replace_custom_subjects(
        student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        (SUBJECT_DE, SUBJECT_MATH),
    )
    assert first.configuration.profile is not None

    noop = service.replace_custom_subjects(
        student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        (SUBJECT_MATH, SUBJECT_DE, SUBJECT_DE),
    )
    assert noop.status is DocumentationSubjectWriteStatus.NO_CHANGE
    assert noop.configuration.profile == first.configuration.profile

    replaced = service.replace_custom_subjects(
        student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        (SUBJECT_EPU,),
    )
    assert replaced.status is DocumentationSubjectWriteStatus.CHANGED
    assert replaced.configuration.selected_subject_ids == (SUBJECT_EPU,)
    assert replaced.configuration.profile is not None
    assert replaced.configuration.profile.created_at == first.configuration.profile.created_at


def test_two_students_have_independent_custom_sets(
    service: StudentDocumentationSubjectService,
) -> None:
    first, second = SYNTHETIC_STUDENT_IDS[:2]
    service.replace_custom_subjects(
        first, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_DE,)
    )
    service.replace_custom_subjects(
        second, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_MATH, SUBJECT_EPU)
    )

    assert service.effective_documentation_subjects(
        first, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_DE,)
    assert service.effective_documentation_subjects(
        second, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_MATH, SUBJECT_EPU)


def test_two_school_years_are_independent_and_closed_year_is_read_only(
    database_path: Path,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    service = _service(database_path)
    service.replace_custom_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_DE,)
    )
    _advance_to_2027_28(database_path)
    service.replace_custom_subjects(
        student, "SY-TEST-2027-28", (SUBJECT_MATH, SUBJECT_EPU)
    )

    assert service.effective_documentation_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_DE,)
    assert service.effective_documentation_subjects(
        student, "SY-TEST-2027-28"
    ) == (SUBJECT_MATH, SUBJECT_EPU)
    with pytest.raises(
        StudentDocumentationSubjectApplicationError,
        match="school_year_read_only",
    ):
        service.replace_custom_subjects(
            student, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_EPU,)
        )


@pytest.mark.parametrize(
    ("student_id", "school_year_id", "expected"),
    (
        ("STD-UNKNOWN", SYNTHETIC_SCHOOL_YEAR_ID, "student_unknown"),
        (SYNTHETIC_STUDENT_IDS[0], "SY-UNKNOWN", "school_year_unknown"),
    ),
)
def test_unknown_references_fail_closed(
    service: StudentDocumentationSubjectService,
    student_id: str,
    school_year_id: str,
    expected: str,
) -> None:
    with pytest.raises(StudentDocumentationSubjectApplicationError, match=expected):
        service.effective_documentation_subjects(student_id, school_year_id)
    with pytest.raises(StudentDocumentationSubjectApplicationError, match=expected):
        service.replace_custom_subjects(student_id, school_year_id, ())


@pytest.mark.parametrize(
    ("subject_id", "expected"),
    (
        ("SUB-UNKNOWN", "documentation_subject_unknown"),
        (SUBJECT_INACTIVE, "documentation_subject_inactive"),
    ),
)
def test_unknown_and_inactive_new_subjects_fail_closed(
    service: StudentDocumentationSubjectService,
    subject_id: str,
    expected: str,
) -> None:
    with pytest.raises(StudentDocumentationSubjectApplicationError, match=expected):
        service.replace_custom_subjects(
            SYNTHETIC_STUDENT_IDS[0],
            SYNTHETIC_SCHOOL_YEAR_ID,
            (subject_id,),
        )


def test_archived_student_remains_readable_but_is_not_writable(
    database_path: Path,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    service = _service(database_path)
    service.replace_custom_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_DE,)
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE students
            SET active = 0, archived_at = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (NOW.isoformat(), NOW.isoformat(), student),
        )

    assert service.effective_documentation_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_DE,)
    with pytest.raises(
        StudentDocumentationSubjectApplicationError,
        match="student_read_only",
    ):
        service.set_mode(
            student, SYNTHETIC_SCHOOL_YEAR_ID, DocumentationSubjectMode.INHERIT
        )


def test_later_inactive_custom_subject_remains_resolvable(
    database_path: Path,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    service = _service(database_path)
    service.replace_custom_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_EPU,)
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE competencies SET active = 0 WHERE subject_id = ?",
            (SUBJECT_EPU,),
        )

    assert service.effective_documentation_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ) == (SUBJECT_EPU,)


def test_replace_rollback_preserves_configuration_and_domain_rows(
    database_path: Path,
) -> None:
    student = SYNTHETIC_STUDENT_IDS[0]
    stable = _service(database_path)
    stable.replace_custom_subjects(
        student, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_DE, SUBJECT_MATH)
    )
    before = _domain_snapshot(database_path)

    def fail(stage: str) -> None:
        if stage == "after_custom_subjects_replace":
            raise RuntimeError("injected_subject_replace_failure")

    failing = _service(database_path, fault_hook=fail)
    with pytest.raises(RuntimeError, match="injected_subject_replace_failure"):
        failing.replace_custom_subjects(
            student, SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_EPU,)
        )

    assert stable.configuration(
        student, SYNTHETIC_SCHOOL_YEAR_ID
    ).selected_subject_ids == (SUBJECT_DE, SUBJECT_MATH)
    assert _domain_snapshot(database_path) == before


def test_repository_respects_caller_owned_rollback(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("BEGIN IMMEDIATE")
    repository = SQLiteStudentDocumentationSubjectRepository(connection)
    repository.insert_profile(
        SYNTHETIC_STUDENT_IDS[0],
        SYNTHETIC_SCHOOL_YEAR_ID,
        DocumentationSubjectMode.CUSTOM,
        NOW,
    )
    repository.replace_selections(
        SYNTHETIC_STUDENT_IDS[0], SYNTHETIC_SCHOOL_YEAR_ID, (SUBJECT_DE,)
    )
    connection.rollback()
    connection.close()

    assert _service(database_path).configuration(
        SYNTHETIC_STUDENT_IDS[0], SYNTHETIC_SCHOOL_YEAR_ID
    ).profile is None


def test_resolver_is_deterministic_by_catalog_order_then_subject_id(
    database_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        _insert_subject(connection, "SUB-TEST-A", "A", 2, active=True)
        _insert_subject(connection, "SUB-TEST-Z", "Z", 2, active=True)
    service = _service(database_path)
    service.replace_custom_subjects(
        SYNTHETIC_STUDENT_IDS[0],
        SYNTHETIC_SCHOOL_YEAR_ID,
        ("SUB-TEST-Z", SUBJECT_EPU, "SUB-TEST-A", SUBJECT_DE),
    )
    expected = (SUBJECT_DE, "SUB-TEST-A", "SUB-TEST-Z", SUBJECT_EPU)

    assert service.effective_documentation_subjects(
        SYNTHETIC_STUDENT_IDS[0], SYNTHETIC_SCHOOL_YEAR_ID
    ) == expected
    assert service.effective_documentation_subjects(
        SYNTHETIC_STUDENT_IDS[0], SYNTHETIC_SCHOOL_YEAR_ID
    ) == expected


def test_direct_repository_write_to_closed_year_is_blocked(
    database_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        repository = SQLiteStudentDocumentationSubjectRepository(connection)
        with pytest.raises(sqlite3.IntegrityError, match="school_year_read_only"):
            repository.insert_profile(
                SYNTHETIC_STUDENT_IDS[0],
                SYNTHETIC_HISTORICAL_SCHOOL_YEAR_ID,
                DocumentationSubjectMode.CUSTOM,
                NOW,
            )


def _service(
    path: Path,
    *,
    fault_hook=None,
) -> StudentDocumentationSubjectService:
    return StudentDocumentationSubjectService(
        lambda: sqlite3.connect(path),
        now_provider=lambda: NOW,
        fault_hook=fault_hook,
    )


def _insert_subject(
    connection: sqlite3.Connection,
    subject_id: str,
    name: str,
    sort_order: int,
    *,
    active: bool,
) -> None:
    connection.execute(
        """
        INSERT INTO competencies(
            competency_id, subject_id, subject_name, subject_full_name,
            official_subject_name, school_context_name, grade_band,
            label, description, learning_stage, learning_area,
            competency_group, source_reference, catalog_status,
            activation_group_key, sort_order, active,
            catalog_default_active, is_core_subject
        ) VALUES (?, ?, ?, ?, ?, ?, '1-3', ?, ?, 'stage_1_3', ?, ?, ?,
                  'current', 'TEST', ?, ?, 1, 1)
        """,
        (
            f"CMP-{subject_id}",
            subject_id,
            name,
            name,
            name,
            "Testkontext",
            f"Kompetenz {name}",
            "Nur Testdaten.",
            "Testbereich",
            "Testgruppe",
            "SYNTHETIC",
            sort_order,
            int(active),
        ),
    )


def _set_global_subjects(path: Path, subject_ids: tuple[str, ...]) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM documentation_subject_settings")
        connection.executemany(
            """
            INSERT INTO documentation_subject_settings(subject_id, active, updated_at)
            VALUES (?, 1, ?)
            """,
            ((subject_id, NOW.isoformat()) for subject_id in subject_ids),
        )


def _advance_to_2027_28(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES ('SY-TEST-2027-28', '2027/28', '2027-08-01', '2028-07-31',
                      'planned', ?, NULL)
            """,
            (NOW.isoformat(),),
        )
        connection.execute(
            """
            UPDATE school_years
            SET status = 'closed', closed_at = ?
            WHERE school_year_id = ?
            """,
            (NOW.isoformat(), SYNTHETIC_SCHOOL_YEAR_ID),
        )
        connection.execute(
            """
            UPDATE school_years SET status = 'current'
            WHERE school_year_id = 'SY-TEST-2027-28'
            """
        )


def _domain_snapshot(path: Path) -> tuple[tuple[object, ...], ...]:
    statements = (
        "SELECT * FROM observations ORDER BY observation_id",
        "SELECT * FROM observation_competency_ratings ORDER BY observation_id, competency_id",
        "SELECT * FROM student_competency_confirmations ORDER BY student_id, competency_id",
        "SELECT * FROM competencies ORDER BY competency_id",
    )
    with sqlite3.connect(path) as connection:
        return tuple(
            tuple(tuple(row) for row in connection.execute(statement).fetchall())
            for statement in statements
        )
