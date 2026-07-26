"""Focused persistence tests for Sprint 7G.1 LEG drafts."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.core.learning_conference_draft import LearningConferenceDraftError
from src.core.observation import ObservationCompetencyRatingRecord, ObservationRecord
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
)


class LearningConferenceDraftPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "leg-draft.sqlite"
        create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.students = self.adapter.list_students()
        self.student = self.students[0]
        self.other_student = self.students[1]
        self.competency = next(
            competency
            for competency in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if competency.active and competency.catalog_status == "current"
        )
        self.observation = self._create_observation(
            "OBS-LEG-001",
            self.student.student_id,
            "Bewusst ausgewählter Gesprächsbeleg.",
        )
        self.quick_observation = self._create_observation(
            "OBS-LEG-QUICK",
            self.student.student_id,
            "Schnellbeobachtung als textlicher Beleg.",
        )
        self.foreign_observation = self._create_observation(
            "OBS-LEG-FOREIGN",
            self.other_student.student_id,
            "Beleg eines anderen Kindes.",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_load_and_reopen_complete_leg_draft(self) -> None:
        saved = self.adapter.save_learning_conference_draft(self._draft())
        loaded = self.adapter.load_learning_conference_draft(
            saved.learning_conference_draft_id
        )
        reopened = self.adapter.list_learning_conference_drafts_for_student(
            self.student.student_id
        )[0]

        self.assertEqual(saved.learning_conference_draft_id, "LCD-000001")
        self.assertEqual(saved.status, "draft")
        self.assertEqual(loaded, saved)
        self.assertEqual(reopened, saved)
        self.assertEqual(saved.period_start, date(2026, 2, 1))
        self.assertEqual(saved.period_end, date(2026, 7, 31))
        self.assertEqual(saved.conference_date, date(2026, 7, 10))
        self.assertEqual(saved.subject_ids, (self.competency.subject_id,))
        self.assertEqual(saved.competency_ids, (self.competency.competency_id,))
        self.assertEqual(
            set(saved.observation_ids),
            {self.observation.observation_id, self.quick_observation.observation_id},
        )
        self.assertEqual(
            set(saved.cross_topic_keys),
            {"social_behavior", "independence"},
        )
        self.assertEqual(
            set(saved.chart_types),
            {
                "documentation_coverage",
                "competency_timeline",
                "observation_timeline",
            },
        )

    def test_manual_prepared_and_agreed_contents_round_trip(self) -> None:
        saved = self.adapter.save_learning_conference_draft(self._draft())
        loaded = self.adapter.load_learning_conference_draft(
            saved.learning_conference_draft_id
        )

        self.assertEqual(loaded.conversation_entry_text, "Ruhiger Gesprächseinstieg")
        self.assertEqual(loaded.child_retrospective_text, "Rückblick des Kindes")
        self.assertEqual(loaded.teacher_perspective_text, "Sicht der Lehrkraft")
        self.assertEqual(loaded.strengths_text, "Was gelingt dem Kind?")
        self.assertEqual(loaded.development_fields_text, "Welche Entwicklung sehen wir?")
        self.assertEqual(loaded.prepared_goals_text, "Vorbereitetes Ziel")
        self.assertEqual(loaded.prepared_support_text, "Vorbereitete Unterstützung")
        self.assertEqual(loaded.prepared_agreements_text, "Vorbereitete Vereinbarung")
        self.assertEqual(loaded.agreed_goals_text, "Gemeinsam vereinbartes Ziel")
        self.assertEqual(loaded.agreed_support_text, "Gemeinsam vereinbarte Unterstützung")
        self.assertEqual(loaded.agreed_agreements_text, "Gemeinsame Vereinbarung")
        self.assertEqual(loaded.responsibilities_text, "Kind: üben; Lehrkraft: begleiten")
        self.assertEqual(loaded.next_review_date, date(2026, 9, 15))

    def test_conference_date_without_period_is_valid(self) -> None:
        saved = self.adapter.save_learning_conference_draft(
            replace(self._draft(), period_start=None, period_end=None)
        )

        self.assertIsNone(saved.period_start)
        self.assertIsNone(saved.period_end)
        self.assertEqual(saved.conference_date, date(2026, 7, 10))

    def test_draft_requires_period_or_conference_date(self) -> None:
        with self.assertRaisesRegex(
            LearningConferenceDraftError,
            "Zeitraum oder ein Gespraechsdatum",
        ):
            self.adapter.save_learning_conference_draft(
                replace(
                    self._draft(),
                    period_start=None,
                    period_end=None,
                    conference_date=None,
                )
            )

    def test_update_keeps_student_created_at_and_identity_stable(self) -> None:
        created = self.adapter.save_learning_conference_draft(self._draft())
        update = replace(
            created,
            strengths_text="Überarbeitete Stärke",
            agreed_agreements_text="Im Gespräch ergänzt",
            subject_ids=(),
            competency_ids=(),
            observation_ids=(),
            cross_topic_keys=("work_habits",),
            chart_types=("documentation_coverage",),
        )

        saved = self.adapter.save_learning_conference_draft(update)
        reloaded = self.adapter.load_learning_conference_draft(
            created.learning_conference_draft_id
        )

        self.assertEqual(saved.learning_conference_draft_id, created.learning_conference_draft_id)
        self.assertEqual(saved.student_id, created.student_id)
        self.assertEqual(saved.created_at, created.created_at)
        self.assertEqual(reloaded.strengths_text, "Überarbeitete Stärke")
        self.assertEqual(reloaded.agreed_agreements_text, "Im Gespräch ergänzt")
        self.assertEqual(reloaded.competency_ids, ())
        self.assertEqual(reloaded.observation_ids, ())

    def test_foreign_observation_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            LearningConferenceDraftError,
            "nicht zum Schueler",
        ):
            self.adapter.save_learning_conference_draft(
                replace(
                    self._draft(),
                    observation_ids=(self.foreign_observation.observation_id,),
                )
            )

    def test_invalid_competency_reference_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            LearningConferenceDraftError,
            "Kompetenzreferenzen nicht gefunden",
        ):
            self.adapter.save_learning_conference_draft(
                replace(self._draft(), competency_ids=("CMP-NOT-FOUND",))
            )

    def test_soft_deleted_observation_cannot_be_selected_for_new_draft(self) -> None:
        SQLiteObservationRepository(self.adapter.database).deactivate_observation(
            self.observation.observation_id,
            "2026-07-11T10:00:00+00:00",
        )

        with self.assertRaisesRegex(LearningConferenceDraftError, "inaktiv"):
            self.adapter.save_learning_conference_draft(self._draft())

    def test_referenced_later_deleted_evidence_is_preserved_and_marked(self) -> None:
        saved = self.adapter.save_learning_conference_draft(self._draft())
        SQLiteObservationRepository(self.adapter.database).deactivate_observation(
            self.observation.observation_id,
            "2026-07-11T10:00:00+00:00",
        )

        loaded = self.adapter.load_learning_conference_draft(
            saved.learning_conference_draft_id
        )

        self.assertIn(self.observation.observation_id, loaded.observation_ids)
        self.assertEqual(
            loaded.unavailable_observation_ids,
            (self.observation.observation_id,),
        )
        resaved = self.adapter.save_learning_conference_draft(
            replace(loaded, strengths_text="Weiterbearbeitet")
        )
        self.assertIn(self.observation.observation_id, resaved.observation_ids)

    def test_quick_observation_is_available_as_text_evidence_only(self) -> None:
        statuses_before = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )

        preparation = self.adapter.learning_conference_preparation_for_student(
            self.student.student_id
        )
        saved = self.adapter.save_learning_conference_draft(self._draft())
        statuses_after = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )

        quick = next(
            evidence
            for evidence in preparation.evidence
            if evidence.observation_id == self.quick_observation.observation_id
        )
        self.assertTrue(quick.is_quick_observation)
        self.assertIn(self.quick_observation.observation_id, saved.observation_ids)
        self.assertEqual(statuses_after, statuses_before)

    def test_leg_preparation_uses_active_child_competency_evidence(self) -> None:
        self._create_competency_observation(
            "OBS-LEG-RATED",
            self.student.student_id,
        )

        preparation = self.adapter.learning_conference_preparation_for_student(
            self.student.student_id
        )
        competency = self._prepared_competency(preparation)

        self.assertEqual(competency.observation_dates, ("2026-07-02",))
        self.assertTrue(
            competency.is_documented_in_period(date(2026, 7, 1), date(2026, 7, 31))
        )

    def test_quick_and_foreign_observations_do_not_document_competency(self) -> None:
        self._create_competency_observation(
            "OBS-LEG-FOREIGN-RATED",
            self.other_student.student_id,
        )

        preparation = self.adapter.learning_conference_preparation_for_student(
            self.student.student_id
        )
        competency = self._prepared_competency(preparation)

        self.assertEqual(competency.observation_dates, ())
        self.assertFalse(competency.is_documented_in_period(None, None))

    def test_soft_deleted_observation_does_not_document_competency(self) -> None:
        observation = self._create_competency_observation(
            "OBS-LEG-DELETED-RATED",
            self.student.student_id,
        )
        SQLiteObservationRepository(self.adapter.database).deactivate_observation(
            observation.observation_id,
            "2026-07-12T10:00:00+00:00",
        )

        preparation = self.adapter.learning_conference_preparation_for_student(
            self.student.student_id
        )
        competency = self._prepared_competency(preparation)

        self.assertEqual(competency.observation_dates, ())
        self.assertFalse(competency.is_documented_in_period(None, None))

    def test_current_confirmation_documents_competency_without_observation(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=self.student.student_id,
            competency_id=self.competency.competency_id,
            confirmed_rating="+",
        )

        preparation = self.adapter.learning_conference_preparation_for_student(
            self.student.student_id
        )
        competency = self._prepared_competency(preparation)

        self.assertTrue(competency.has_current_confirmation)
        self.assertTrue(
            competency.is_documented_in_period(date(1900, 1, 1), date(1900, 1, 2))
        )

    def test_retained_draft_competency_is_resolved_without_changing_default_projection(self) -> None:
        historical = next(
            competency
            for competency in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if not competency.active or competency.catalog_status != "current"
        )
        before = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )

        preparation = self.adapter.learning_conference_preparation_for_student(
            self.student.student_id,
            retained_competency_ids=(historical.competency_id,),
        )
        after = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )
        retained = next(
            competency
            for subject in preparation.subjects
            for competency in subject.competencies
            if competency.competency_id == historical.competency_id
        )

        self.assertEqual(after, before)
        self.assertTrue(retained.historical)
        self.assertFalse(retained.selectable)
        self.assertEqual(retained.observation_dates, ())

    def test_leg_persistence_does_not_change_canonical_projection(self) -> None:
        statuses_before = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )
        observations_before = self.adapter.list_observations_for_student(
            self.student.student_id
        )

        self.adapter.save_learning_conference_draft(self._draft())

        self.assertEqual(
            self.adapter.list_competency_status_projection_for_student(
                self.student.student_id
            ),
            statuses_before,
        )
        self.assertEqual(
            self.adapter.list_observations_for_student(self.student.student_id),
            observations_before,
        )

    def test_relation_tables_store_only_references_and_cascade(self) -> None:
        saved = self.adapter.save_learning_conference_draft(self._draft())
        with self.adapter.database.connect() as connection:
            competency_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(learning_conference_draft_competencies)"
                ).fetchall()
            }
            observation_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(learning_conference_draft_observations)"
                ).fetchall()
            }
            with connection:
                connection.execute(
                    "DELETE FROM learning_conference_drafts WHERE learning_conference_draft_id = ?",
                    (saved.learning_conference_draft_id,),
                )
            remaining = connection.execute(
                "SELECT COUNT(*) FROM learning_conference_draft_observations"
            ).fetchone()[0]

        self.assertEqual(
            competency_columns,
            {"learning_conference_draft_id", "competency_id"},
        )
        self.assertEqual(
            observation_columns,
            {"learning_conference_draft_id", "observation_id"},
        )
        self.assertEqual(remaining, 0)

    def _draft(self) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 7, 31),
            conference_date=date(2026, 7, 10),
            responsible_teacher="Laura Lernbegleiterin",
            conversation_entry_text="Ruhiger Gesprächseinstieg",
            child_retrospective_text="Rückblick des Kindes",
            teacher_perspective_text="Sicht der Lehrkraft",
            strengths_text="Was gelingt dem Kind?",
            development_fields_text="Welche Entwicklung sehen wir?",
            prepared_goals_text="Vorbereitetes Ziel",
            prepared_support_text="Vorbereitete Unterstützung",
            prepared_agreements_text="Vorbereitete Vereinbarung",
            agreed_goals_text="Gemeinsam vereinbartes Ziel",
            agreed_support_text="Gemeinsam vereinbarte Unterstützung",
            agreed_agreements_text="Gemeinsame Vereinbarung",
            responsibilities_text="Kind: üben; Lehrkraft: begleiten",
            next_review_date=date(2026, 9, 15),
            subject_ids=(self.competency.subject_id,),
            cross_topic_keys=("social_behavior", "independence"),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(
                self.observation.observation_id,
                self.quick_observation.observation_id,
            ),
            chart_types=(
                "documentation_coverage",
                "competency_timeline",
                "observation_timeline",
            ),
        )

    def _create_observation(
        self,
        observation_id: str,
        student_id: str,
        note: str,
    ) -> ObservationRecord:
        observation = ObservationRecord(
            observation_id,
            student_id,
            "2026-07-02",
            self.competency.subject_id,
            "Lernzeit",
            note,
            True,
            "2026-07-02T10:00:00+00:00",
            "2026-07-02T10:00:00+00:00",
            (),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            observation
        )
        return observation

    def _create_competency_observation(
        self,
        observation_id: str,
        student_id: str,
    ) -> ObservationRecord:
        rating = ObservationCompetencyRatingRecord(
            self.competency.competency_id,
            self.competency.subject_id,
            self.competency.subject_name,
            self.competency.learning_area,
            self.competency.competency_group,
            self.competency.description,
            "+",
        )
        observation = ObservationRecord(
            observation_id,
            student_id,
            "2026-07-02",
            self.competency.subject_id,
            "Lernzeit",
            "Kompetenzbezogene Beobachtung.",
            True,
            "2026-07-02T10:00:00+00:00",
            "2026-07-02T10:00:00+00:00",
            (rating,),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            observation
        )
        return observation

    def _prepared_competency(self, preparation: object) -> object:
        return next(
            competency
            for subject in preparation.subjects
            for competency in subject.competencies
            if competency.competency_id == self.competency.competency_id
        )


class LearningConferenceDraftMigrationTest(unittest.TestCase):
    def test_unknown_partial_schema_is_rejected_without_changing_master_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.sqlite"
            connection = sqlite3.connect(path)
            connection.execute(
                """
                CREATE TABLE groups (
                    group_id TEXT PRIMARY KEY,
                    group_name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL CHECK (active IN (0, 1))
                )
                """
            )
            connection.execute(
                "INSERT INTO groups (group_id, group_name, sort_order, active) VALUES (?, ?, ?, ?)",
                ("GRP-KEEP", "Bestehende Gruppe", 0, 1),
            )
            connection.commit()
            connection.close()

            before = path.read_bytes()
            from src.core.database_compatibility import DatabaseCompatibilityError

            with self.assertRaises(DatabaseCompatibilityError):
                SQLiteDatabase(path).initialize_schema()
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
