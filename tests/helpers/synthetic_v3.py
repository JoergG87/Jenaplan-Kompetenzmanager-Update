"""Deterministic synthetic data for temporary final-V3 test databases."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from src.core.final_v3_schema import FinalV3SchemaInitializer


SYNTHETIC_SCHOOL_YEAR_ID = "SY-TEST-2025-26"
SYNTHETIC_COURSE_GROUP_ID = "CG-TEST-CORE"
SYNTHETIC_REPORT_DRAFT_ID = "RPD-TEST-001"
SYNTHETIC_LEG_DRAFT_ID = "LCD-TEST-001"
SYNTHETIC_STUDENT_IDS = (
    "STD-TEST-001",
    "STD-TEST-002",
    "STD-TEST-003",
)
SYNTHETIC_DOCUMENT_IDS = (
    "DOC-TEST-001",
    "DOC-TEST-002",
)


class SyntheticV3SeedBuilder:
    """Build deterministic fictional rows in one fresh temporary database."""

    def create(self, database_path: Path) -> Path:
        path = Path(database_path)
        FinalV3SchemaInitializer().initialize(path)
        self._seed(path)
        return path

    @staticmethod
    def _seed(path: Path) -> None:
        with sqlite3.connect(path) as connection:
            _seed_connection(connection)


def _seed_connection(connection: sqlite3.Connection) -> None:
    """Insert the deterministic fixture in one transaction."""

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute(
        """
        INSERT INTO school_years(
            school_year_id, label, start_date, end_date,
            status, created_at, closed_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            SYNTHETIC_SCHOOL_YEAR_ID,
            "2025/26",
            "2025-08-01",
            "2026-07-31",
            "current",
            "2025-07-01T08:00:00+00:00",
        ),
    )
    connection.executemany(
        """
        INSERT INTO groups(group_id, group_name, sort_order, active)
        VALUES (?, ?, ?, 1)
        """,
        (
            ("GRP-TEST-A", "Testgruppe A", 1),
            ("GRP-TEST-B", "Testgruppe B", 2),
        ),
    )
    connection.executemany(
        """
        INSERT INTO courses(
            course_id, course_name, color_key, color_name, color_hex,
            sort_order, active, year_level
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            (
                "CRS-TEST-1",
                "Testkurs 1",
                "blue",
                "Blau",
                "#4A6FA5",
                1,
                1,
            ),
            (
                "CRS-TEST-2",
                "Testkurs 2",
                "green",
                "Grün",
                "#4F7A65",
                2,
                2,
            ),
            (
                "CRS-TEST-3",
                "Testkurs 3",
                "amber",
                "Bernstein",
                "#9A6B34",
                3,
                3,
            ),
        ),
    )
    connection.executemany(
        """
        INSERT INTO students(
            student_id, first_name, last_name, notes, active,
            created_at, updated_at, archived_at
        ) VALUES (?, ?, ?, ?, 1, ?, ?, NULL)
        """,
        (
            (
                SYNTHETIC_STUDENT_IDS[0],
                "Testkind",
                "Eins",
                "Synthetischer Datensatz",
                "2025-07-01T08:10:00+00:00",
                "2025-07-01T08:10:00+00:00",
            ),
            (
                SYNTHETIC_STUDENT_IDS[1],
                "Testkind",
                "Zwei",
                "Synthetischer Datensatz",
                "2025-07-01T08:20:00+00:00",
                "2025-07-01T08:20:00+00:00",
            ),
            (
                SYNTHETIC_STUDENT_IDS[2],
                "Testkind",
                "Drei",
                "Synthetischer Datensatz",
                "2025-07-01T08:30:00+00:00",
                "2025-07-01T08:30:00+00:00",
            ),
        ),
    )
    connection.executemany(
        """
        INSERT INTO student_school_year_assignments(
            assignment_id, student_id, school_year_id, group_id,
            course_id, assignment_status, valid_from, valid_to,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'enrolled', ?, ?, ?, ?)
        """,
        (
            (
                "ASG-TEST-001",
                SYNTHETIC_STUDENT_IDS[0],
                SYNTHETIC_SCHOOL_YEAR_ID,
                "GRP-TEST-A",
                "CRS-TEST-1",
                "2025-08-01",
                "2026-07-31",
                "2025-07-01T09:10:00+00:00",
                "2025-07-01T09:10:00+00:00",
            ),
            (
                "ASG-TEST-002",
                SYNTHETIC_STUDENT_IDS[1],
                SYNTHETIC_SCHOOL_YEAR_ID,
                "GRP-TEST-A",
                "CRS-TEST-2",
                "2025-08-01",
                "2026-07-31",
                "2025-07-01T09:20:00+00:00",
                "2025-07-01T09:20:00+00:00",
            ),
            (
                "ASG-TEST-003",
                SYNTHETIC_STUDENT_IDS[2],
                SYNTHETIC_SCHOOL_YEAR_ID,
                "GRP-TEST-B",
                "CRS-TEST-3",
                "2025-08-01",
                "2026-07-31",
                "2025-07-01T09:30:00+00:00",
                "2025-07-01T09:30:00+00:00",
            ),
        ),
    )
    connection.execute(
        """
        INSERT INTO course_groups(
            course_group_id, name, sort_order, active
        ) VALUES (?, ?, ?, 1)
        """,
        (
            SYNTHETIC_COURSE_GROUP_ID,
            "Synthetischer Kursverbund",
            1,
        ),
    )
    connection.executemany(
        """
        INSERT INTO course_group_student_groups(
            course_group_id, student_group_id
        ) VALUES (?, ?)
        """,
        (
            (SYNTHETIC_COURSE_GROUP_ID, "GRP-TEST-A"),
            (SYNTHETIC_COURSE_GROUP_ID, "GRP-TEST-B"),
        ),
    )
    connection.executemany(
        """
        INSERT INTO course_group_courses(course_group_id, course_id)
        VALUES (?, ?)
        """,
        (
            (SYNTHETIC_COURSE_GROUP_ID, "CRS-TEST-1"),
            (SYNTHETIC_COURSE_GROUP_ID, "CRS-TEST-2"),
            (SYNTHETIC_COURSE_GROUP_ID, "CRS-TEST-3"),
        ),
    )
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
            "CMP-TEST-001",
            "SUB-TEST-DE",
            "Testsprache",
            "Synthetisches Sprachfach",
            "Synthetisches Sprachfach",
            "Testkontext",
            "1-3",
            "Synthetische Kompetenz",
            "Ausschließlich für automatisierte Tests.",
            "stage_1_3",
            "Testbereich",
            "Testgruppe",
            "SYNTHETIC",
            "current",
            "TEST",
            1,
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
            "OBS-TEST-001",
            SYNTHETIC_STUDENT_IDS[0],
            "2025-10-15",
            "SUB-TEST-DE",
            "Synthetische Lernsituation",
            "Nur Testdaten.",
            "2025-10-15T10:00:00+00:00",
            "2025-10-15T10:00:00+00:00",
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
            "OBS-TEST-001",
            "CMP-TEST-001",
            "SUB-TEST-DE",
            "Testsprache",
            "Testbereich",
            "Testgruppe",
            "Synthetische Kompetenz",
            "+",
        ),
    )
    connection.execute(
        """
        INSERT INTO student_competency_confirmations(
            student_id, competency_id, confirmed_rating, confirmed_at, note
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            SYNTHETIC_STUDENT_IDS[0],
            "CMP-TEST-001",
            "+",
            "2025-10-20T09:00:00+00:00",
            "Nur Testdaten.",
        ),
    )
    connection.executemany(
        """
        INSERT INTO documents(
            document_id, student_id, observation_id, title, document_type,
            file_path, original_filename, created_at, note, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            (
                SYNTHETIC_DOCUMENT_IDS[0],
                SYNTHETIC_STUDENT_IDS[0],
                "OBS-TEST-001",
                "Synthetischer Beobachtungsbeleg",
                "Testbeleg",
                "synthetic-documents/DOC-TEST-001.txt",
                "synthetischer-beobachtungsbeleg.txt",
                "2025-10-15T10:05:00+00:00",
                "Nur deterministische Testmetadaten.",
            ),
            (
                SYNTHETIC_DOCUMENT_IDS[1],
                SYNTHETIC_STUDENT_IDS[1],
                None,
                "Synthetischer freier Beleg",
                "Testbeleg",
                "synthetic-documents/DOC-TEST-002.txt",
                "synthetischer-freier-beleg.txt",
                "2025-11-01T09:00:00+00:00",
                "Kein fachliches Referenzdatum.",
            ),
        ),
    )
    connection.execute(
        """
        INSERT INTO report_drafts(
            report_draft_id, student_id, report_type, period_start,
            period_end, status, teacher_name, overall_text,
            created_at, updated_at
        ) VALUES (?, ?, 'learning_development', ?, ?, 'draft', ?, ?, ?, ?)
        """,
        (
            SYNTHETIC_REPORT_DRAFT_ID,
            SYNTHETIC_STUDENT_IDS[0],
            "2025-08-01",
            "2026-01-31",
            "Testlehrkraft",
            "Synthetischer Berichtsentwurf.",
            "2026-01-15T08:00:00+00:00",
            "2026-01-15T08:00:00+00:00",
        ),
    )
    connection.execute(
        """
        INSERT INTO report_draft_subjects(
            report_draft_id, subject_id, strengths_text,
            development_text, support_needs_text, next_goals_text
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            SYNTHETIC_REPORT_DRAFT_ID,
            "SUB-TEST-DE",
            "Synthetischer Stärkentext.",
            "Synthetischer Entwicklungstext.",
            "",
            "Synthetisches nächstes Ziel.",
        ),
    )
    connection.execute(
        """
        INSERT INTO report_draft_competencies(
            report_draft_id, competency_id
        ) VALUES (?, ?)
        """,
        (SYNTHETIC_REPORT_DRAFT_ID, "CMP-TEST-001"),
    )
    connection.execute(
        """
        INSERT INTO report_draft_observations(
            report_draft_id, observation_id
        ) VALUES (?, ?)
        """,
        (SYNTHETIC_REPORT_DRAFT_ID, "OBS-TEST-001"),
    )
    connection.execute(
        """
        INSERT INTO report_draft_charts(
            report_draft_id, subject_id, chart_type
        ) VALUES (?, ?, 'documentation_coverage')
        """,
        (SYNTHETIC_REPORT_DRAFT_ID, "SUB-TEST-DE"),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_drafts(
            learning_conference_draft_id, student_id, period_start,
            period_end, conference_date, status, responsible_teacher,
            conversation_entry_text, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)
        """,
        (
            SYNTHETIC_LEG_DRAFT_ID,
            SYNTHETIC_STUDENT_IDS[0],
            "2025-08-01",
            "2026-01-31",
            "2026-02-10",
            "Testlehrkraft",
            "Synthetischer LEG-Entwurf.",
            "2026-02-01T08:00:00+00:00",
            "2026-02-01T08:00:00+00:00",
        ),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_draft_subjects(
            learning_conference_draft_id, subject_id
        ) VALUES (?, ?)
        """,
        (SYNTHETIC_LEG_DRAFT_ID, "SUB-TEST-DE"),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_draft_cross_topics(
            learning_conference_draft_id, cross_topic_key
        ) VALUES (?, 'learning_organization')
        """,
        (SYNTHETIC_LEG_DRAFT_ID,),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_draft_competencies(
            learning_conference_draft_id, competency_id
        ) VALUES (?, ?)
        """,
        (SYNTHETIC_LEG_DRAFT_ID, "CMP-TEST-001"),
    )
    connection.execute(
        """
        INSERT INTO learning_conference_draft_observations(
            learning_conference_draft_id, observation_id
        ) VALUES (?, ?)
        """,
        (SYNTHETIC_LEG_DRAFT_ID, "OBS-TEST-001"),
    )
    connection.commit()


def create_synthetic_v3_database(database_path: Path) -> Path:
    """Create a fresh complete V3 database and deterministic fictional rows."""

    return SyntheticV3SeedBuilder().create(database_path)
