"""Tests for the Sprint 5.2a SQLite architecture spike."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from src.core.constants import (
    ACTIVE,
    COURSE_GROUP_ID_PREFIX,
    COURSE_ID_PREFIX,
    GROUP_ID_PREFIX,
    OBSERVATION_ID_PREFIX,
    STUDENT_ID_PREFIX,
)
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
)
from src.core.sqlite_store import (
    DEFAULT_COURSE_GROUP_ID,
    SQLiteCourseRepository,
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteDocumentationSubjectSettingsRepository,
    SQLiteDocumentRepository,
    SQLiteGroupRepository,
    SQLiteMasterDataRepository,
    SQLiteObservationRepository,
    SQLiteStudentCompetencyConfirmationRepository,
    SQLiteStudentRepository,
    DocumentRecord,
    StudentCompetencyConfirmationRecord,
    create_sqlite_seed_database,
)
from src.core.records import seed_reference_data
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from scripts.seed_test_data import SeedDataError, seed_test_data


class SQLiteSpikeTest(unittest.TestCase):
    def test_schema_contains_students_and_course_group_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = SQLiteDatabase(database_path)
            database.initialize_schema()

            with closing(sqlite3.connect(database_path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                course_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(courses)").fetchall()
                }
                group_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(groups)").fetchall()
                }
                student_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(students)").fetchall()
                }
                competency_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(competencies)"
                    ).fetchall()
                }
                confirmation_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(student_competency_confirmations)"
                    ).fetchall()
                }
                document_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(documents)"
                    ).fetchall()
                }
                documentation_subject_setting_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(documentation_subject_settings)"
                    ).fetchall()
                }
                confirmation_foreign_keys = {
                    (row[3], row[2], row[4])
                    for row in connection.execute(
                        "PRAGMA foreign_key_list(student_competency_confirmations)"
                    ).fetchall()
                }
                document_foreign_keys = {
                    (row[3], row[2], row[4])
                    for row in connection.execute(
                        "PRAGMA foreign_key_list(documents)"
                    ).fetchall()
                }
                student_foreign_keys = {
                    (row[3], row[2], row[4])
                    for row in connection.execute("PRAGMA foreign_key_list(students)").fetchall()
                }

        self.assertIn("students", tables)
        self.assertIn("course_groups", tables)
        self.assertIn("course_group_student_groups", tables)
        self.assertIn("course_group_courses", tables)
        self.assertIn("observations", tables)
        self.assertIn("competencies", tables)
        self.assertIn("observation_competency_ratings", tables)
        self.assertIn("student_competency_confirmations", tables)
        self.assertIn("documents", tables)
        self.assertIn("documentation_subject_settings", tables)
        self.assertIn("student_id", student_columns)
        self.assertIn("first_name", student_columns)
        self.assertIn("last_name", student_columns)
        self.assertIn("group_id", student_columns)
        self.assertIn("course_id", student_columns)
        self.assertIn("sort_order", group_columns)
        self.assertIn("color_name", course_columns)
        self.assertIn("color_hex", course_columns)
        self.assertIn("sort_order", course_columns)
        self.assertIn("competency_id", competency_columns)
        self.assertIn("subject_id", competency_columns)
        self.assertIn("subject_name", competency_columns)
        self.assertIn("subject_full_name", competency_columns)
        self.assertIn("official_subject_name", competency_columns)
        self.assertIn("school_context_name", competency_columns)
        self.assertIn("grade_band", competency_columns)
        self.assertIn("label", competency_columns)
        self.assertIn("learning_stage", competency_columns)
        self.assertIn("source_reference", competency_columns)
        self.assertIn("catalog_status", competency_columns)
        self.assertIn("activation_group_key", competency_columns)
        self.assertIn("catalog_default_active", competency_columns)
        self.assertIn("sort_order", competency_columns)
        self.assertIn("confirmed_rating", confirmation_columns)
        self.assertIn("confirmed_at", confirmation_columns)
        self.assertIn("note", confirmation_columns)
        self.assertIn("document_id", document_columns)
        self.assertIn("student_id", document_columns)
        self.assertIn("observation_id", document_columns)
        self.assertIn("document_type", document_columns)
        self.assertIn("file_path", document_columns)
        self.assertIn("original_filename", document_columns)
        self.assertIn("active", document_columns)
        self.assertIn("subject_id", documentation_subject_setting_columns)
        self.assertIn("active", documentation_subject_setting_columns)
        self.assertIn("updated_at", documentation_subject_setting_columns)
        self.assertIn(("group_id", "groups", "group_id"), student_foreign_keys)
        self.assertIn(("course_id", "courses", "course_id"), student_foreign_keys)
        self.assertIn(("student_id", "students", "student_id"), confirmation_foreign_keys)
        self.assertIn(("competency_id", "competencies", "competency_id"), confirmation_foreign_keys)
        self.assertIn(("student_id", "students", "student_id"), document_foreign_keys)
        self.assertIn(("observation_id", "observations", "observation_id"), document_foreign_keys)

    def test_observation_schema_contains_rating_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = SQLiteDatabase(database_path)
            database.initialize_schema()

            with closing(sqlite3.connect(database_path)) as connection:
                observation_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(observations)"
                    ).fetchall()
                }
                rating_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(observation_competency_ratings)"
                    ).fetchall()
                }
                observation_foreign_keys = {
                    (row[3], row[2], row[4])
                    for row in connection.execute(
                        "PRAGMA foreign_key_list(observations)"
                    ).fetchall()
                }

        self.assertIn("observation_id", observation_columns)
        self.assertIn("student_id", observation_columns)
        self.assertIn("date", observation_columns)
        self.assertIn("subject_id", observation_columns)
        self.assertIn("context", observation_columns)
        self.assertIn("note", observation_columns)
        self.assertIn("observation_id", rating_columns)
        self.assertIn("competency_id", rating_columns)
        self.assertIn("rating", rating_columns)
        self.assertIn(("student_id", "students", "student_id"), observation_foreign_keys)

    def test_student_competency_confirmation_repository_upserts_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = SQLiteDatabase(database_path)
            database.initialize_schema()
            with database.connect() as connection:
                with connection:
                    connection.execute(
                        "INSERT INTO groups (group_id, group_name, sort_order, active) VALUES (?, ?, ?, ?)",
                        (f"{GROUP_ID_PREFIX}-000001", "Grashüpfer", 0, 1),
                    )
                    connection.execute(
                        """
                        INSERT INTO courses (
                            course_id,
                            course_name,
                            color_key,
                            color_name,
                            color_hex,
                            sort_order,
                            active
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{COURSE_ID_PREFIX}-000001",
                            "Kurs 1",
                            "#2563EB",
                            "Blau",
                            "#2563EB",
                            0,
                            1,
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO students (
                            student_id,
                            first_name,
                            last_name,
                            group_id,
                            course_id,
                            student_notes,
                            active,
                            created_at,
                            updated_at,
                            archived_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{STUDENT_ID_PREFIX}-000001",
                            "Mila",
                            "Neumann",
                            f"{GROUP_ID_PREFIX}-000001",
                            f"{COURSE_ID_PREFIX}-000001",
                            "",
                            1,
                            "2026-07-04",
                            "2026-07-04",
                            None,
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO competencies (
                            competency_id,
                            subject_id,
                            subject_name,
                            label,
                            description,
                            learning_area,
                            competency_group,
                            sort_order,
                            active,
                            is_core_subject
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "CMP-000001",
                            "deutsch",
                            "Deutsch",
                            "Lesen",
                            "Texte lesen",
                            "Mit Texten umgehen",
                            "Lesen",
                            0,
                            1,
                            1,
                        ),
                    )
            repository = SQLiteStudentCompetencyConfirmationRepository(database)
            repository.upsert_confirmation(
                StudentCompetencyConfirmationRecord(
                    f"{STUDENT_ID_PREFIX}-000001",
                    "CMP-000001",
                    "+",
                    "2026-07-04T12:00:00+00:00",
                    "passt",
                )
            )
            repository.upsert_confirmation(
                StudentCompetencyConfirmationRecord(
                    f"{STUDENT_ID_PREFIX}-000001",
                    "CMP-000001",
                    "++",
                    "2026-07-05T12:00:00+00:00",
                    "angepasst",
                )
            )

            confirmation = repository.get_confirmation(
                f"{STUDENT_ID_PREFIX}-000001",
                "CMP-000001",
            )
            confirmations = repository.list_confirmations_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )

        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.confirmed_rating, "++")
        self.assertEqual(confirmation.confirmed_at, "2026-07-05T12:00:00+00:00")
        self.assertEqual(confirmation.note, "angepasst")
        self.assertEqual(confirmations, (confirmation,))

    def test_document_repository_persists_metadata_and_soft_deletes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = create_sqlite_seed_database(database_path)
            repository = SQLiteDocumentRepository(database)
            document = DocumentRecord(
                "MED-000001",
                f"{STUDENT_ID_PREFIX}-000001",
                "",
                "Foerderplan",
                "Bericht",
                str(Path(temp_dir) / "documents" / "Foerderplan.pdf"),
                "Foerderplan.pdf",
                "2026-07-04T12:00:00+00:00",
                "wichtiger Hinweis",
                True,
            )

            repository.create_document(document)
            reloaded = repository.list_documents_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )
            repository.deactivate_document("MED-000001")
            after_delete = repository.list_documents_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )

        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].document_type, "Bericht")
        self.assertEqual(reloaded[0].original_filename, "Foerderplan.pdf")
        self.assertEqual(after_delete, ())

    def test_seed_test_data_creates_pilot_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            result = seed_test_data(database_path)

            with closing(sqlite3.connect(database_path)) as connection:
                student_count = connection.execute(
                    "SELECT COUNT(*) FROM students"
                ).fetchone()[0]
                group_count = connection.execute(
                    "SELECT COUNT(*) FROM groups WHERE active = 1"
                ).fetchone()[0]
                course_count = connection.execute(
                    "SELECT COUNT(*) FROM courses WHERE active = 1"
                ).fetchone()[0]
                course_group_count = connection.execute(
                    "SELECT COUNT(*) FROM course_groups WHERE active = 1"
                ).fetchone()[0]
                active_observation_count = connection.execute(
                    "SELECT COUNT(*) FROM observations WHERE active = 1"
                ).fetchone()[0]
                inactive_observation_count = connection.execute(
                    "SELECT COUNT(*) FROM observations WHERE active = 0"
                ).fetchone()[0]
                confirmation_count = connection.execute(
                    "SELECT COUNT(*) FROM student_competency_confirmations"
                ).fetchone()[0]
                document_count = connection.execute(
                    "SELECT COUNT(*) FROM documents WHERE active = 1"
                ).fetchone()[0]
                active_date_range = connection.execute(
                    "SELECT MIN(date), MAX(date) FROM observations WHERE active = 1"
                ).fetchone()
                observed_student_count = connection.execute(
                    "SELECT COUNT(DISTINCT student_id) FROM observations WHERE active = 1"
                ).fetchone()[0]
                longest_rating_history = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM observation_competency_ratings
                    WHERE observation_id IN (
                        SELECT observation_id FROM observations WHERE active = 1
                    )
                    GROUP BY competency_id
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                    """
                ).fetchone()[0]
                blob_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(documents)"
                    ).fetchall()
                    if "blob" in row[1].lower()
                }

            document_files = tuple((Path(temp_dir) / "documents").rglob("*.txt"))

        self.assertEqual(result.student_count, 12)
        self.assertEqual(student_count, 12)
        self.assertGreaterEqual(group_count, 2)
        self.assertEqual(course_count, 3)
        self.assertGreaterEqual(course_group_count, 2)
        self.assertGreaterEqual(active_observation_count, 30)
        self.assertEqual(inactive_observation_count, 1)
        self.assertGreaterEqual(confirmation_count, 4)
        self.assertGreaterEqual(document_count, 3)
        self.assertEqual(active_date_range, ("2025-09-08", "2026-01-23"))
        self.assertGreaterEqual(observed_student_count, 11)
        self.assertGreaterEqual(longest_rating_history, 3)
        self.assertEqual(blob_columns, set())
        self.assertGreaterEqual(len(document_files), 3)

    def test_seed_test_data_requires_reset_for_existing_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            first_result = seed_test_data(database_path)

            with self.assertRaises(SeedDataError):
                seed_test_data(database_path)

            second_result = seed_test_data(database_path, reset=True)

        self.assertEqual(first_result.student_count, second_result.student_count)
        self.assertEqual(first_result.document_count, second_result.document_count)

    def test_seed_data_is_written_to_sqlite_without_id_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            create_sqlite_seed_database(database_path)

            self.assertTrue(database_path.exists())
            with closing(sqlite3.connect(database_path)) as connection:
                with connection:
                    student_count = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                    group_count = connection.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
                    course_count = connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
                    first_student_id = connection.execute(
                        "SELECT student_id FROM students ORDER BY student_id LIMIT 1"
                    ).fetchone()[0]
                    first_group_id = connection.execute(
                        "SELECT group_id FROM groups ORDER BY group_id LIMIT 1"
                    ).fetchone()[0]
                    first_course_id = connection.execute(
                        "SELECT course_id FROM courses ORDER BY course_id LIMIT 1"
                    ).fetchone()[0]

        seed_data = seed_reference_data()
        self.assertEqual(student_count, len(seed_data.students))
        self.assertEqual(group_count, len(seed_data.groups))
        self.assertEqual(course_count, len(seed_data.courses))
        self.assertEqual(first_student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(first_group_id, f"{GROUP_ID_PREFIX}-000001")
        self.assertEqual(first_course_id, f"{COURSE_ID_PREFIX}-000001")

    def test_repositories_read_seed_records_from_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            students = SQLiteStudentRepository(database).list_students()
            groups = SQLiteGroupRepository(database).list_groups()
            courses = SQLiteCourseRepository(database).list_courses()

        self.assertEqual(len(students), 28)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(courses), 3)
        self.assertTrue(all(student.student_id.startswith(STUDENT_ID_PREFIX) for student in students))
        self.assertTrue(all(group.active for group in groups))
        self.assertTrue(all(course.active for course in courses))

    def test_master_data_seed_creates_default_course_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteMasterDataRepository(database)
            course_groups = repository.list_course_groups()

        self.assertEqual(len(course_groups), 1)
        self.assertEqual(course_groups[0].course_group_id, DEFAULT_COURSE_GROUP_ID)
        self.assertEqual(course_groups[0].name, "Mathe/Deutsch Kursverbund A")
        self.assertEqual(course_groups[0].selected_group_ids, (f"{GROUP_ID_PREFIX}-000001",))
        self.assertEqual(
            course_groups[0].selected_course_ids,
            (
                f"{COURSE_ID_PREFIX}-000001",
                f"{COURSE_ID_PREFIX}-000002",
                f"{COURSE_ID_PREFIX}-000003",
            ),
        )

    def test_master_data_repository_creates_next_course_group_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteMasterDataRepository(database)

            next_course_group_id = repository.next_course_group_id()

        self.assertEqual(next_course_group_id, f"{COURSE_GROUP_ID_PREFIX}-000001")

    def test_master_data_defaults_do_not_overwrite_existing_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = SQLiteDatabase(database_path)
            database.initialize_schema()
            with closing(database.connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO groups (group_id, group_name, sort_order, active)
                        VALUES (?, ?, ?, ?)
                        """,
                        (f"{GROUP_ID_PREFIX}-999999", "Eigene Gruppe", 0, 1),
                    )
                    connection.execute(
                        """
                        INSERT INTO courses (
                            course_id,
                            course_name,
                            color_key,
                            color_name,
                            color_hex,
                            sort_order,
                            active
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{COURSE_ID_PREFIX}-999999",
                            "Eigener Kurs",
                            "#EAB308",
                            "Gelb",
                            "#EAB308",
                            0,
                            1,
                        ),
                    )

            database.ensure_master_data_defaults()
            repository = SQLiteMasterDataRepository(database)
            group_names = [group.group_name for group in repository.list_student_groups()]
            course_names = [course.course_name for course in repository.list_courses()]
            course_groups = repository.list_course_groups()

        self.assertEqual(
            group_names,
            ["Eigene Gruppe"],
        )
        self.assertEqual(
            course_names,
            ["Eigener Kurs"],
        )
        self.assertEqual(
            course_groups[0].selected_group_ids,
            (f"{GROUP_ID_PREFIX}-999999",),
        )
        self.assertEqual(
            course_groups[0].selected_course_ids,
            (f"{COURSE_ID_PREFIX}-999999",),
        )

    def test_master_data_defaults_do_not_seed_students(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = SQLiteDatabase(database_path)
            database.ensure_master_data_defaults()

            students = SQLiteStudentRepository(database).list_students()
            groups = SQLiteGroupRepository(database).list_groups()
            courses = SQLiteCourseRepository(database).list_courses()

        self.assertEqual(students, ())
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(courses), 3)

    def test_competency_catalog_upsert_adds_new_entries_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            database.initialize_schema()
            repository = SQLiteCompetencyRepository(database)
            repository.ensure_catalog_defaults((
                self._sample_competency_entry("CMP-000001", "Deutsch", "Lesen"),
                self._sample_competency_entry("CMP-000002", "EPU", "Natur"),
            ))

            seeded = repository.list_competencies()
            repository.ensure_catalog_defaults((
                self._sample_competency_entry("CMP-999999", "Mathematik", "Zahlen"),
            ))
            repository.ensure_catalog_defaults((
                self._sample_competency_entry("CMP-999999", "Mathematik", "Zahlen"),
            ))
            after_second_seed = repository.list_competencies()

        self.assertEqual(
            tuple(competency.competency_id for competency in seeded),
            ("CMP-000001", "CMP-000002"),
        )
        self.assertEqual(
            {competency.competency_id for competency in after_second_seed},
            {"CMP-000001", "CMP-000002", "CMP-999999"},
        )
        self.assertEqual(
            len({competency.competency_id for competency in after_second_seed}),
            len(after_second_seed),
        )

    def test_competency_catalog_upsert_preserves_existing_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteCompetencyRepository(database)
            repository.ensure_catalog_defaults((
                self._sample_competency_entry(
                    "CMP-000001",
                    "Deutsch",
                    "Lesen",
                    active=True,
                ),
            ))
            with database.connect() as connection:
                with connection:
                    connection.execute(
                        "UPDATE competencies SET active = 0 WHERE competency_id = ?",
                        ("CMP-000001",),
                    )

            repository.ensure_catalog_defaults((
                self._sample_competency_entry(
                    "CMP-000001",
                    "Deutsch",
                    "Lesen aktualisiert",
                    active=True,
                ),
            ))
            competency = repository.get_competency("CMP-000001")

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertFalse(competency.active)
            self.assertEqual(competency.label, "Lesen aktualisiert")

    def test_competency_catalog_upsert_persists_catalog_model_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteCompetencyRepository(database)

            repository.ensure_catalog_defaults((
                self._sample_competency_entry(
                    "CMP-000001",
                    "Sport",
                    "Gleiten",
                    active=False,
                    learning_stage="stage_4",
                    catalog_status="legacy",
                    catalog_default_active=False,
                    activation_group_key="sport_ski_ice_inline",
                ),
            ))
            competency = repository.get_competency("CMP-000001")

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertEqual(competency.grade_band, "1-4")
            self.assertEqual(competency.learning_stage, "stage_4")
            self.assertEqual(competency.catalog_status, "legacy")
            self.assertFalse(competency.catalog_default_active)
            self.assertEqual(
                competency.activation_group_key,
                "sport_ski_ice_inline",
            )
            self.assertFalse(competency.active)

    def test_competency_catalog_upsert_updates_catalog_default_not_local_active(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteCompetencyRepository(database)
            repository.ensure_catalog_defaults((
                self._sample_competency_entry(
                    "CMP-000001",
                    "Sport",
                    "Gleiten",
                    active=True,
                    catalog_default_active=True,
                ),
            ))
            with database.connect() as connection:
                with connection:
                    connection.execute(
                        "UPDATE competencies SET active = 0 WHERE competency_id = ?",
                        ("CMP-000001",),
                    )

            repository.ensure_catalog_defaults((
                self._sample_competency_entry(
                    "CMP-000001",
                    "Sport",
                    "Gleiten",
                    active=True,
                    catalog_default_active=False,
                ),
            ))
            competency = repository.get_competency("CMP-000001")

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertFalse(competency.active)
            self.assertFalse(competency.catalog_default_active)

    def test_competency_schema_migrates_existing_database_with_safe_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE competencies (
                        competency_id TEXT PRIMARY KEY,
                        subject_id TEXT NOT NULL,
                        subject_name TEXT NOT NULL,
                        label TEXT NOT NULL,
                        description TEXT NOT NULL,
                        learning_area TEXT NOT NULL,
                        competency_group TEXT,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)),
                        is_core_subject INTEGER NOT NULL CHECK (is_core_subject IN (0, 1)) DEFAULT 1
                    );
                    CREATE TABLE observations (
                        observation_id TEXT PRIMARY KEY,
                        student_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        context TEXT,
                        note TEXT,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)) DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE observation_competency_ratings (
                        observation_id TEXT NOT NULL,
                        competency_id TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        subject_display_name TEXT NOT NULL,
                        learning_area TEXT NOT NULL,
                        competency_group TEXT,
                        competency_text TEXT NOT NULL,
                        rating TEXT NOT NULL,
                        PRIMARY KEY (observation_id, competency_id)
                    );
                    INSERT INTO competencies (
                        competency_id,
                        subject_id,
                        subject_name,
                        label,
                        description,
                        learning_area,
                        competency_group,
                        sort_order,
                        active,
                        is_core_subject
                    )
                    VALUES (
                        'CMP-OLD001',
                        'deutsch',
                        'Deutsch',
                        'Lesen',
                        'Alte Kompetenz',
                        'Lesen',
                        'Grundlage',
                        0,
                        0,
                        1
                    );
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
                    VALUES (
                        'OBS-OLD001',
                        'STU-OLD001',
                        '2026-07-01',
                        'deutsch',
                        'Alt',
                        'Historisch',
                        1,
                        '2026-07-01T10:00:00+00:00',
                        '2026-07-01T10:00:00+00:00'
                    );
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
                    VALUES (
                        'OBS-OLD001',
                        'CMP-OLD001',
                        'deutsch',
                        'Deutsch',
                        'Lesen',
                        'Grundlage',
                        'Alte Kompetenz',
                        '+'
                    );
                    """
                )
                connection.commit()

            database = SQLiteDatabase(database_path)
            database.initialize_schema()
            competency = SQLiteCompetencyRepository(database).get_competency(
                "CMP-OLD001"
            )
            with database.connect() as connection:
                ratings = connection.execute(
                    """
                    SELECT observation_id, competency_id, rating
                    FROM observation_competency_ratings
                    """
                ).fetchall()

        self.assertIsNotNone(competency)
        if competency is not None:
            self.assertFalse(competency.active)
            self.assertEqual(competency.learning_stage, "cross_stage")
            self.assertEqual(competency.catalog_status, "current")
            self.assertTrue(competency.catalog_default_active)
            self.assertEqual(competency.activation_group_key, "")
        self.assertEqual(
            [tuple(row) for row in ratings],
            [("OBS-OLD001", "CMP-OLD001", "+")],
        )

    def test_curriculum_catalog_accepts_old_csv_without_catalog_model_columns(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_path = Path(temp_dir) / "old_catalog.csv"
            catalog_path.write_text(
                "\n".join((
                    "competency_id;subject_key;subject_display_name;subject_full_name;official_subject_name;school_context_name;grade_band;learning_area;competency_group;competency_text;competency_label;source_reference;is_core_subject;is_active",
                    "CMP-OLD001;deutsch;Deutsch;Deutsch;Deutsch;Quelle;1-4;Lesen;Grundlage;Text lesen;Lesen;Quelle;true;false",
                )),
                encoding="utf-8",
            )

            entries = CurriculumDesktopAdapter(catalog_path).list_entries()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].learning_stage, "cross_stage")
        self.assertEqual(entries[0].catalog_status, "current")
        self.assertFalse(entries[0].catalog_default_active)
        self.assertFalse(entries[0].is_active)
        self.assertEqual(entries[0].activation_group_key, "")

    def test_full_curriculum_catalog_imports_concrete_competencies_for_empty_database(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            entries = CurriculumDesktopAdapter().list_entries()
            SQLiteCompetencyRepository(database).ensure_catalog_defaults(entries)

            competencies = SQLiteCompetencyRepository(database).list_competencies()

        self.assertEqual(len(competencies), len(entries))
        by_id = {competency.competency_id: competency for competency in competencies}
        by_subject: dict[str, list[object]] = {}
        for competency in competencies:
            by_subject.setdefault(competency.subject_id, []).append(competency)
        self.assertEqual(by_id["CMP-000318"].subject_id, "mathematik")
        self.assertEqual(
            by_id["CMP-000318"].learning_area,
            "Groessen - Groessenvorstellungen nutzen und mit Groessen umgehen",
        )
        self.assertEqual(by_id["CMP-000318"].competency_group, "Zeit")
        self.assertEqual(
            by_id["CMP-000318"].description,
            "Uhrzeiten ablesen, einstellen, notieren und auf verschiedene Weise benennen.",
        )
        self.assertEqual(by_id["CMP-000318"].grade_band, "1-4")
        self.assertEqual(by_id["CMP-000318"].learning_stage, "cross_stage")
        self.assertEqual(by_id["CMP-000318"].catalog_status, "current")
        self.assertTrue(by_id["CMP-000318"].catalog_default_active)
        self.assertEqual(by_id["CMP-000318"].activation_group_key, "")
        self.assertEqual(by_id["CMP-000083"].catalog_status, "legacy")
        self.assertFalse(by_id["CMP-000083"].catalog_default_active)
        self.assertEqual(by_id["CMP-000059"].subject_id, "deutsch")
        self.assertEqual(by_id["CMP-000099"].subject_id, "epu")
        self.assertIn("sozialkompetenz", by_subject)
        current_social_competencies = [
            competency
            for competency in by_subject["sozialkompetenz"]
            if competency.catalog_status == "current"
        ]
        legacy_social_competencies = [
            competency
            for competency in by_subject["sozialkompetenz"]
            if competency.catalog_status == "legacy"
        ]
        current_ethics_competencies = [
            competency
            for competency in by_subject["ethik"]
            if competency.catalog_status == "current"
        ]
        legacy_ethics_competencies = [
            competency
            for competency in by_subject["ethik"]
            if competency.catalog_status == "legacy"
        ]
        self.assertEqual(len(current_social_competencies), 12)
        self.assertEqual(len(legacy_social_competencies), 24)
        self.assertEqual(len(current_ethics_competencies), 58)
        self.assertEqual(len(legacy_ethics_competencies), 15)
        self.assertTrue(any(
            competency.competency_group == "Rollen und Absprachen"
            and competency.description
            == (
                "Eine übernommene Rolle ausführen und Änderungen einer Absprache "
                "mit der Gruppe klären."
            )
            for competency in current_social_competencies
        ))

    def test_competency_catalog_upsert_keeps_existing_ratings_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = create_sqlite_seed_database(database_path)
            competency_repository = SQLiteCompetencyRepository(database)
            competency_repository.ensure_catalog_defaults((
                self._sample_competency_entry("CMP-000001", "Deutsch", "Lesen"),
            ))
            observation_repository = SQLiteObservationRepository(database)
            observation_repository.create_observation(
                self._sample_observation(
                    ratings=(self._sample_rating("CMP-000001", "+"),),
                )
            )

            competency_repository.ensure_catalog_defaults(
                CurriculumDesktopAdapter().list_entries()
            )
            stored_observation = observation_repository.get_observation(
                f"{OBSERVATION_ID_PREFIX}-000001"
            )
            old_competency = competency_repository.get_competency("CMP-000001")
            new_competency = competency_repository.get_competency("CMP-000318")

        self.assertIsNotNone(stored_observation)
        if stored_observation is not None:
            self.assertEqual(
                tuple(
                    rating.competency_id
                    for rating in stored_observation.competency_ratings
                ),
                ("CMP-000001",),
            )
            self.assertEqual(stored_observation.competency_ratings[0].rating, "+")
        self.assertIsNotNone(old_competency)
        self.assertIsNotNone(new_competency)

    def test_documentation_subject_settings_default_to_active_catalog_subjects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            competency_repository = SQLiteCompetencyRepository(database)
            competency_repository.ensure_catalog_defaults((
                self._sample_competency_entry("CMP-000001", "Deutsch", "Lesen"),
                self._sample_competency_entry("CMP-000002", "EPU", "Natur"),
                self._sample_competency_entry(
                    "CMP-000003",
                    "Kunst",
                    "Farbe",
                    active=False,
                ),
            ))
            repository = SQLiteDocumentationSubjectSettingsRepository(database)

            active_subject_ids = repository.list_active_documentation_subject_ids()
            settings = repository.list_documentation_subject_settings()

        self.assertEqual(active_subject_ids, ("deutsch", "epu"))
        self.assertEqual(settings, ())

    def test_documentation_subject_settings_save_partial_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(Path(temp_dir) / "kompetenzmanager.sqlite")
            SQLiteCompetencyRepository(database).ensure_catalog_defaults((
                self._sample_competency_entry("CMP-000001", "Deutsch", "Lesen"),
                self._sample_competency_entry("CMP-000002", "EPU", "Natur"),
                self._sample_competency_entry("CMP-000003", "Mathematik", "Zahlen"),
            ))
            repository = SQLiteDocumentationSubjectSettingsRepository(database)

            settings = repository.save_active_documentation_subject_ids(
                ("deutsch", "epu"),
                updated_at="2026-07-10T09:00:00+00:00",
            )
            active_subject_ids = repository.list_active_documentation_subject_ids()
            repository.save_active_documentation_subject_ids(
                ("mathematik",),
                updated_at="2026-07-10T10:00:00+00:00",
            )
            replaced_subject_ids = repository.list_active_documentation_subject_ids()

        self.assertEqual(active_subject_ids, ("deutsch", "epu"))
        self.assertEqual(replaced_subject_ids, ("mathematik",))
        self.assertEqual(
            {
                setting.subject_id: (setting.active, setting.updated_at)
                for setting in settings
            },
            {
                "deutsch": (True, "2026-07-10T09:00:00+00:00"),
                "epu": (True, "2026-07-10T09:00:00+00:00"),
                "mathematik": (False, "2026-07-10T09:00:00+00:00"),
            },
        )

    def test_documentation_subject_settings_persist_after_reload_without_changing_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = SQLiteDatabase(database_path)
            competency_repository = SQLiteCompetencyRepository(database)
            competency_repository.ensure_catalog_defaults((
                self._sample_competency_entry("CMP-000001", "Deutsch", "Lesen"),
                self._sample_competency_entry("CMP-000002", "EPU", "Natur"),
            ))
            before_catalog_active = {
                competency.competency_id: competency.active
                for competency in competency_repository.list_competencies()
            }
            SQLiteDocumentationSubjectSettingsRepository(
                database
            ).save_active_documentation_subject_ids(
                ("epu",),
                updated_at="2026-07-10T09:00:00+00:00",
            )

            reloaded_database = SQLiteDatabase(database_path)
            reloaded_subject_ids = SQLiteDocumentationSubjectSettingsRepository(
                reloaded_database
            ).list_active_documentation_subject_ids()
            after_catalog_active = {
                competency.competency_id: competency.active
                for competency in SQLiteCompetencyRepository(
                    reloaded_database
                ).list_competencies()
            }

        self.assertEqual(reloaded_subject_ids, ("epu",))
        self.assertEqual(after_catalog_active, before_catalog_active)

    def test_observation_with_multiple_ratings_is_reloaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "kompetenzmanager.sqlite"
            database = create_sqlite_seed_database(database_path)
            repository = SQLiteObservationRepository(database)
            repository.create_observation(self._sample_observation())

            reloaded_repository = SQLiteObservationRepository(SQLiteDatabase(database_path))
            observations = reloaded_repository.list_observations_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )

        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertEqual(observation.observation_id, f"{OBSERVATION_ID_PREFIX}-000001")
        self.assertEqual(observation.student_id, f"{STUDENT_ID_PREFIX}-000001")
        self.assertEqual(observation.date, "2026-07-03")
        self.assertEqual(observation.subject_id, "deutsch")
        self.assertEqual(observation.context, "Leseübung")
        self.assertEqual(observation.note, "Liest einen bekannten Text.")
        self.assertEqual(
            tuple(rating.rating for rating in observation.competency_ratings),
            ("+", "--"),
        )
        self.assertEqual(
            tuple(rating.competency_id for rating in observation.competency_ratings),
            ("CMP-000001", "CMP-000002"),
        )

    def test_observations_are_filtered_per_student(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteObservationRepository(database)
            repository.create_observation(self._sample_observation(
                observation_id=f"{OBSERVATION_ID_PREFIX}-000001",
                student_id=f"{STUDENT_ID_PREFIX}-000001",
            ))
            repository.create_observation(self._sample_observation(
                observation_id=f"{OBSERVATION_ID_PREFIX}-000002",
                student_id=f"{STUDENT_ID_PREFIX}-000002",
            ))

            first_student_observations = repository.list_observations_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )

        self.assertEqual(len(first_student_observations), 1)
        self.assertEqual(
            first_student_observations[0].student_id,
            f"{STUDENT_ID_PREFIX}-000001",
        )

    def test_observation_and_ratings_are_saved_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteObservationRepository(database)
            duplicate_rating_observation = self._sample_observation(
                ratings=(
                    self._sample_rating("CMP-000001", "+"),
                    self._sample_rating("CMP-000001", "--"),
                )
            )

            with self.assertRaises(sqlite3.IntegrityError):
                repository.create_observation(duplicate_rating_observation)

            observations = repository.list_observations_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )

        self.assertEqual(observations, ())

    def test_update_observation_replaces_competency_ratings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteObservationRepository(database)
            repository.create_observation(self._sample_observation())
            updated_observation = ObservationRecord(
                f"{OBSERVATION_ID_PREFIX}-000001",
                f"{STUDENT_ID_PREFIX}-000001",
                "2026-07-04",
                "deutsch",
                "Präsentation",
                "Aktualisierte Beobachtung.",
                True,
                "2026-07-03T10:00:00+00:00",
                "2026-07-04T10:00:00+00:00",
                (self._sample_rating("CMP-000002", "-"),),
            )

            repository.update_observation(updated_observation)
            stored_observation = repository.get_observation(
                f"{OBSERVATION_ID_PREFIX}-000001"
            )

        self.assertIsNotNone(stored_observation)
        self.assertEqual(stored_observation.date, "2026-07-04")
        self.assertEqual(stored_observation.context, "Präsentation")
        self.assertEqual(stored_observation.note, "Aktualisierte Beobachtung.")
        self.assertEqual(
            tuple(rating.competency_id for rating in stored_observation.competency_ratings),
            ("CMP-000002",),
        )
        self.assertEqual(stored_observation.competency_ratings[0].rating, "-")

    def test_deactivate_observation_hides_it_from_student_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = create_sqlite_seed_database(Path(temp_dir) / "kompetenzmanager.sqlite")
            repository = SQLiteObservationRepository(database)
            repository.create_observation(self._sample_observation())

            repository.deactivate_observation(
                f"{OBSERVATION_ID_PREFIX}-000001",
                "2026-07-04T10:00:00+00:00",
            )
            hidden_observations = repository.list_observations_for_student(
                f"{STUDENT_ID_PREFIX}-000001"
            )
            stored_observation = repository.get_observation(
                f"{OBSERVATION_ID_PREFIX}-000001"
            )

        self.assertEqual(hidden_observations, ())
        self.assertIsNotNone(stored_observation)
        self.assertFalse(stored_observation.active)
        self.assertEqual(stored_observation.updated_at, "2026-07-04T10:00:00+00:00")

    def _sample_observation(
        self,
        *,
        observation_id: str = f"{OBSERVATION_ID_PREFIX}-000001",
        student_id: str = f"{STUDENT_ID_PREFIX}-000001",
        ratings: tuple[ObservationCompetencyRatingRecord, ...] | None = None,
    ) -> ObservationRecord:
        return ObservationRecord(
            observation_id,
            student_id,
            "2026-07-03",
            "deutsch",
            "Leseübung",
            "Liest einen bekannten Text.",
            True,
            "2026-07-03T10:00:00+00:00",
            "2026-07-03T10:00:00+00:00",
            ratings or (
                self._sample_rating("CMP-000001", "+"),
                self._sample_rating("CMP-000002", "--"),
            ),
        )

    def _sample_rating(
        self,
        competency_id: str,
        rating: str,
    ) -> ObservationCompetencyRatingRecord:
        return ObservationCompetencyRatingRecord(
            competency_id,
            "deutsch",
            "Deutsch",
            "Mit Texten und Medien umgehen",
            "Lesen und Verstehen",
            "Texte lesen und zentrale Informationen entnehmen",
            rating,
        )

    def _sample_competency_entry(
        self,
        competency_id: str,
        subject_name: str,
        label: str,
        *,
        active: bool = True,
        learning_stage: str = "cross_stage",
        catalog_status: str = "current",
        catalog_default_active: bool | None = None,
        activation_group_key: str = "",
    ) -> object:
        class Entry:
            pass

        entry = Entry()
        entry.competency_id = competency_id
        entry.subject_id = subject_name.casefold()
        entry.subject_display_name = subject_name
        entry.subject_full_name = subject_name
        entry.official_subject_name = subject_name
        entry.school_context_name = "Testkatalog"
        entry.grade_band = "1-4"
        entry.learning_stage = learning_stage
        entry.competency_label = label
        entry.competency_text = f"{label} beschreiben"
        entry.learning_area = label
        entry.competency_group = "Grundlage"
        entry.source_reference = "Testquelle"
        entry.catalog_status = catalog_status
        entry.catalog_default_active = (
            active if catalog_default_active is None else catalog_default_active
        )
        entry.activation_group_key = activation_group_key
        entry.is_active = active
        entry.is_core_subject = True
        return entry


if __name__ == "__main__":
    unittest.main()
