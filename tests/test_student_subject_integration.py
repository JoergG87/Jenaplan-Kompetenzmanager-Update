"""Focused non-visual integration tests for student-specific subject relevance."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from src.application.student_documentation_subjects import (
    StudentDocumentationSubjectApplicationError,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
)
from tests.helpers.synthetic_v4 import (
    SYNTHETIC_SCHOOL_YEAR_ID,
    SYNTHETIC_STUDENT_IDS,
    create_synthetic_v4_database,
)


SUBJECT_LANGUAGE = "SUB-TEST-DE"
SUBJECT_MATH = "SUB-TEST-MATH"
COMPETENCY_MATH = "CMP-TEST-MATH"


@pytest.fixture
def adapter(tmp_path: Path) -> StudentDesktopAdapter:
    database_path = create_synthetic_v4_database(tmp_path / "integration.sqlite")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO competencies(
                competency_id, subject_id, subject_name, subject_full_name,
                official_subject_name, school_context_name, grade_band,
                label, description, learning_stage, learning_area,
                competency_group, source_reference, catalog_status,
                activation_group_key, sort_order, active,
                catalog_default_active, is_core_subject
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                COMPETENCY_MATH,
                SUBJECT_MATH,
                "Testmathematik",
                "Synthetisches Mathematikfach",
                "Synthetisches Mathematikfach",
                "Testkontext",
                "1-3",
                "Synthetisch rechnen",
                "Ausschließlich für automatisierte Tests.",
                "stage_1_3",
                "Zahlen",
                "Rechnen",
                "SYNTHETIC",
                "current",
                "TEST-MATH",
                2,
                1,
                1,
                1,
            ),
        )
        connection.execute(
            """
            INSERT INTO observations(
                observation_id, student_id, date, subject_id, context, note,
                active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                "OBS-TEST-MATH",
                SYNTHETIC_STUDENT_IDS[0],
                "2026-08-05",
                SUBJECT_MATH,
                "Synthetische Rechensituation",
                "Nur Testdaten.",
                "2026-08-05T10:00:00+00:00",
                "2026-08-05T10:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO observation_competency_ratings(
                observation_id, competency_id, subject_id,
                subject_display_name, learning_area, competency_group,
                competency_text, rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "OBS-TEST-MATH",
                COMPETENCY_MATH,
                SUBJECT_MATH,
                "Testmathematik",
                "Zahlen",
                "Rechnen",
                "Synthetisch rechnen",
                "+",
            ),
        )
    return StudentDesktopAdapter(database_path)


def test_inherit_projection_binds_current_school_year_and_global_catalog(
    adapter: StudentDesktopAdapter,
) -> None:
    projection = adapter.student_profile_projection_bundle(
        SYNTHETIC_STUDENT_IDS[0]
    ).documentation_subjects

    assert projection.school_year_id == SYNTHETIC_SCHOOL_YEAR_ID
    assert projection.school_year_label == "2026/27"
    assert projection.mode == "inherit"
    available_ids = tuple(item.subject_id for item in projection.available_subjects)
    assert SUBJECT_LANGUAGE in available_ids
    assert SUBJECT_MATH in available_ids
    assert set(projection.selected_subject_ids) == set(available_ids)
    assert projection.is_read_only is False


def test_custom_filters_instructional_subjects_but_keeps_cross_curricular_and_evidence(
    adapter: StudentDesktopAdapter,
) -> None:
    student_id = SYNTHETIC_STUDENT_IDS[0]
    before = adapter.student_profile_projection_bundle(student_id)
    assert before.profile_dashboard.documentation_summary.total_learning_area_count > 1

    adapter.save_student_documentation_subjects(
        student_id,
        SYNTHETIC_SCHOOL_YEAR_ID,
        "custom",
        (SUBJECT_LANGUAGE,),
    )
    _deactivate_subject(adapter, SUBJECT_MATH)
    bundle = adapter.student_profile_projection_bundle(student_id)

    assert bundle.documentation_subjects.mode == "custom"
    assert bundle.documentation_subjects.selected_subject_ids == (SUBJECT_LANGUAGE,)
    expected_current_subject_ids = {
        *COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
        SUBJECT_LANGUAGE,
    }
    assert {
        item.subject_id for item in bundle.documentation_statuses
    } == expected_current_subject_ids
    assert {
        item.subject_id for item in bundle.competency_cockpit.subjects
    } == expected_current_subject_ids
    assert tuple(
        item.subject_id for item in bundle.competency_cockpit.historical_subjects
    ) == (SUBJECT_MATH,)
    assert bundle.profile_dashboard.documentation_summary.total_learning_area_count == 3
    assert all(
        item.subject_display_name != "Testmathematik"
        for item in bundle.profile_dashboard.undocumented_subjects
    )


def test_inactive_stored_custom_subject_remains_visible_and_selected(
    adapter: StudentDesktopAdapter,
) -> None:
    student_id = SYNTHETIC_STUDENT_IDS[0]
    adapter.save_student_documentation_subjects(
        student_id,
        SYNTHETIC_SCHOOL_YEAR_ID,
        "custom",
        (SUBJECT_LANGUAGE, SUBJECT_MATH),
    )
    _deactivate_subject(adapter, SUBJECT_MATH)

    projection = adapter.student_profile_projection_bundle(
        student_id
    ).documentation_subjects
    assert projection.mode == "custom"
    assert projection.selected_subject_ids == (SUBJECT_LANGUAGE, SUBJECT_MATH)
    assert tuple(
        item.subject_id for item in projection.retained_inactive_subjects
    ) == (SUBJECT_MATH,)
    assert projection.retained_inactive_subjects[0].label == "Testmathematik"


def test_two_students_and_global_changes_keep_custom_separate_from_inherit(
    adapter: StudentDesktopAdapter,
) -> None:
    custom_student, inherit_student = SYNTHETIC_STUDENT_IDS[:2]
    adapter.save_student_documentation_subjects(
        custom_student,
        SYNTHETIC_SCHOOL_YEAR_ID,
        "custom",
        (SUBJECT_LANGUAGE,),
    )

    adapter.save_active_documentation_subjects((SUBJECT_MATH,))

    custom = adapter.student_profile_projection_bundle(
        custom_student
    ).documentation_subjects
    inherited = adapter.student_profile_projection_bundle(
        inherit_student
    ).documentation_subjects
    assert custom.selected_subject_ids == (SUBJECT_LANGUAGE,)
    assert inherited.selected_subject_ids == (SUBJECT_MATH,)


def test_empty_instructional_custom_keeps_cross_curricular_and_inherit_reloads(
    adapter: StudentDesktopAdapter,
) -> None:
    student_id = SYNTHETIC_STUDENT_IDS[0]
    adapter.save_active_documentation_subjects((SUBJECT_MATH,))
    adapter.save_student_documentation_subjects(
        student_id,
        SYNTHETIC_SCHOOL_YEAR_ID,
        "custom",
        (),
    )
    empty = adapter.student_profile_projection_bundle(student_id)
    assert empty.documentation_subjects.selected_subject_ids == ()
    assert {
        item.subject_id for item in empty.documentation_statuses
    } == set(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS)
    assert empty.profile_dashboard.documentation_summary.total_learning_area_count == 2

    adapter.save_student_documentation_subjects(
        student_id,
        SYNTHETIC_SCHOOL_YEAR_ID,
        "inherit",
        (),
    )
    inherited = adapter.student_profile_projection_bundle(student_id)
    assert inherited.documentation_subjects.mode == "inherit"
    assert inherited.documentation_subjects.selected_subject_ids == (SUBJECT_MATH,)


def test_failed_custom_write_keeps_previous_complete_selection(
    adapter: StudentDesktopAdapter,
) -> None:
    student_id = SYNTHETIC_STUDENT_IDS[0]
    adapter.save_student_documentation_subjects(
        student_id,
        SYNTHETIC_SCHOOL_YEAR_ID,
        "custom",
        (SUBJECT_LANGUAGE,),
    )

    with pytest.raises(
        StudentDocumentationSubjectApplicationError,
        match="documentation_subject_unknown",
    ):
        adapter.save_student_documentation_subjects(
            student_id,
            SYNTHETIC_SCHOOL_YEAR_ID,
            "custom",
            (SUBJECT_MATH, "SUB-UNKNOWN"),
        )

    projection = adapter.student_profile_projection_bundle(
        student_id
    ).documentation_subjects
    assert projection.mode == "custom"
    assert projection.selected_subject_ids == (SUBJECT_LANGUAGE,)


def test_archived_student_projects_subject_editor_read_only(
    adapter: StudentDesktopAdapter,
) -> None:
    student_id = SYNTHETIC_STUDENT_IDS[0]
    with adapter.database.connect() as connection:
        connection.execute(
            """
            UPDATE students
            SET active = 0, archived_at = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (
                "2026-08-09T12:00:00+00:00",
                "2026-08-09T12:00:00+00:00",
                student_id,
            ),
        )

    projection = adapter.student_profile_projection_bundle(
        student_id
    ).documentation_subjects
    assert projection.is_read_only is True


def _deactivate_subject(adapter: StudentDesktopAdapter, subject_id: str) -> None:
    with adapter.database.connect() as connection:
        connection.execute(
            "UPDATE competencies SET active = 0 WHERE subject_id = ?",
            (subject_id,),
        )
