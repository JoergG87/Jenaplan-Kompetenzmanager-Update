"""Sprint 10A tests for LEG completion, immutable LCVs and snapshot reads."""

from __future__ import annotations

import inspect
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.core.learning_conference import (
    LearningConferenceCompletionError,
    LearningConferenceCompletionErrorCode,
    LearningConferenceRevisionReadService,
)
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
)
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteLearningConferenceRepository,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs import learning_conference_dialog
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
)


class LearningConferenceCompletionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "leg-completion.sqlite"
        create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.student = self.adapter.list_students()[0]
        self.competency = next(
            item
            for item in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if item.active and item.catalog_status == "current"
        )
        rating = ObservationCompetencyRatingRecord(
            self.competency.competency_id,
            self.competency.subject_id,
            self.competency.subject_name,
            self.competency.learning_area,
            self.competency.competency_group,
            self.competency.description,
            "+",
        )
        self.observation = ObservationRecord(
            "OBS-LEG-COMPLETE",
            self.student.student_id,
            "2026-07-10",
            self.competency.subject_id,
            "Lernzeit",
            "Konkreter gemeinsamer Gesprächsbeleg.",
            True,
            "2026-07-10T10:00:00+00:00",
            "2026-07-10T10:00:00+00:00",
            (rating,),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            self.observation
        )
        self.saved = self.adapter.save_learning_conference_draft(self._draft())
        self.repository = SQLiteLearningConferenceRepository(self.adapter.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_completion_creates_lcf_and_lcv_without_converting_lcd(self) -> None:
        status = self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        revisions = self.repository.list_revisions(
            conference.learning_conference_id
        )
        reloaded_draft = self.adapter.load_learning_conference_draft(
            self.saved.learning_conference_draft_id
        )

        self.assertEqual(conference.learning_conference_id, "LCF-000001")
        self.assertEqual(revisions[0].learning_conference_revision_id, "LCV-000001")
        self.assertEqual(revisions[0].status, "completed")
        self.assertEqual(revisions[0].revision_number, 1)
        self.assertEqual(reloaded_draft.status, "draft")
        self.assertTrue(status.has_completion)
        self.assertFalse(status.draft_changed)

    def test_snapshot_contains_shared_results_and_excludes_internal_preparation(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        revision = self.repository.list_revisions(
            conference.learning_conference_id
        )[0]
        snapshot = json.loads(revision.snapshot_json)

        self.assertEqual(
            snapshot["shared_results"]["goals"],
            "Gemeinsam vereinbartes Ziel",
        )
        self.assertEqual(
            snapshot["observations"][0]["observation_id"],
            self.observation.observation_id,
        )
        self.assertTrue(snapshot["observations"][0]["ratings"])
        self.assertNotIn("prepared_goals_text", revision.snapshot_json)
        self.assertNotIn("teacher_perspective_text", revision.snapshot_json)
        self.assertNotIn("conversation_entry_text", revision.snapshot_json)
        self.assertNotIn("charts", snapshot)

    def test_identical_completion_is_idempotent_and_sha_is_stable(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        first = self.repository.list_revisions(conference.learning_conference_id)[0]

        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        revisions = self.repository.list_revisions(conference.learning_conference_id)

        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0].snapshot_sha256, first.snapshot_sha256)
        self.assertEqual(revisions[0].snapshot_json, first.snapshot_json)

    def test_correction_creates_new_revision_and_supersedes_previous(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        corrected = self.adapter.save_learning_conference_draft(
            replace(
                self.saved,
                agreed_agreements_text="Korrigierte gemeinsame Vereinbarung",
            )
        )

        self.adapter.complete_learning_conference(
            corrected.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            corrected.learning_conference_draft_id
        )
        revisions = self.repository.list_revisions(conference.learning_conference_id)

        self.assertEqual([item.revision_number for item in revisions], [1, 2])
        self.assertEqual([item.status for item in revisions], ["superseded", "completed"])
        self.assertIsNotNone(revisions[0].superseded_at)
        self.assertNotEqual(revisions[0].snapshot_sha256, revisions[1].snapshot_sha256)

    def test_failed_follow_up_keeps_previous_revision_completed(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        corrected = self.adapter.save_learning_conference_draft(
            replace(self.saved, agreed_goals_text="Korrigiertes gemeinsames Ziel")
        )
        conference = self.repository.get_conference_for_source_draft(
            corrected.learning_conference_draft_id
        )
        with self.adapter.database.connect() as connection:
            connection.execute(
                """
                CREATE TRIGGER reject_test_lcv_insert
                BEFORE INSERT ON learning_conference_revisions
                BEGIN
                    SELECT RAISE(ABORT, 'test insert failure');
                END
                """
            )
            connection.commit()

        with self.assertRaises(LearningConferenceCompletionError) as caught:
            self.adapter.complete_learning_conference(
                corrected.learning_conference_draft_id
            )

        revisions = self.repository.list_revisions(conference.learning_conference_id)
        self.assertEqual(caught.exception.code, LearningConferenceCompletionErrorCode.PERSISTENCE_FAILED)
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0].status, "completed")
        self.assertIsNone(revisions[0].superseded_at)

    def test_draft_change_does_not_change_existing_revision_or_historical_view(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        revision = self.repository.list_revisions(conference.learning_conference_id)[0]
        before = self.adapter.load_learning_conference_revision(
            revision.learning_conference_revision_id
        )

        self.adapter.save_learning_conference_draft(
            replace(
                self.saved,
                agreed_goals_text="Spätere, noch nicht abgeschlossene Korrektur",
                teacher_perspective_text="Neue private Vorbereitung",
            )
        )
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE students SET first_name = ? WHERE student_id = ?",
                ("Geändert", self.student.student_id),
            )
            connection.commit()
        after = self.adapter.load_learning_conference_revision(
            revision.learning_conference_revision_id
        )
        persisted = self.repository.get_revision(
            revision.learning_conference_revision_id
        )

        self.assertEqual(after, before)
        self.assertEqual(persisted.snapshot_json, revision.snapshot_json)
        self.assertEqual(persisted.snapshot_sha256, revision.snapshot_sha256)
        self.assertTrue(
            self.adapter.learning_conference_revision_status(
                self.saved.learning_conference_draft_id
            ).draft_changed
        )

    def test_invalid_required_states_are_typed_and_prevent_completion(self) -> None:
        cases = (
            (
                replace(self.saved, conference_date=None),
                LearningConferenceCompletionErrorCode.CONFERENCE_DATE_MISSING,
            ),
            (
                replace(self.saved, responsible_teacher=""),
                LearningConferenceCompletionErrorCode.RESPONSIBLE_TEACHER_MISSING,
            ),
            (
                replace(
                    self.saved,
                    agreed_goals_text="",
                    agreed_support_text="",
                    agreed_agreements_text="",
                ),
                LearningConferenceCompletionErrorCode.SHARED_RESULT_MISSING,
            ),
        )
        for invalid, expected_code in cases:
            with self.subTest(code=expected_code):
                saved = self.adapter.save_learning_conference_draft(invalid)
                with self.assertRaises(LearningConferenceCompletionError) as caught:
                    self.adapter.complete_learning_conference(
                        saved.learning_conference_draft_id
                    )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertIsNone(
                    self.repository.get_conference_for_source_draft(
                        saved.learning_conference_draft_id
                    )
                )

    def test_unavailable_selected_evidence_blocks_completion_without_removal(self) -> None:
        SQLiteObservationRepository(self.adapter.database).deactivate_observation(
            self.observation.observation_id,
            "2026-07-15T10:00:00+00:00",
        )

        with self.assertRaises(LearningConferenceCompletionError) as caught:
            self.adapter.complete_learning_conference(
                self.saved.learning_conference_draft_id
            )

        self.assertEqual(
            caught.exception.code,
            LearningConferenceCompletionErrorCode.OBSERVATION_UNAVAILABLE,
        )
        reloaded = self.adapter.load_learning_conference_draft(
            self.saved.learning_conference_draft_id
        )
        self.assertIn(self.observation.observation_id, reloaded.observation_ids)
        self.assertIn(
            self.observation.observation_id,
            reloaded.unavailable_observation_ids,
        )

    def test_resolvable_historical_competency_is_marked_in_snapshot(self) -> None:
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0, catalog_status = 'legacy' WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.commit()

        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        revision = self.repository.list_revisions(conference.learning_conference_id)[0]
        competency = json.loads(revision.snapshot_json)["competencies"][0]

        self.assertTrue(competency["historical_reference"])
        self.assertFalse(competency["active_at_completion"])
        self.assertEqual(competency["catalog_status_at_completion"], "legacy")

    def test_lcv_rows_cannot_be_changed_or_deleted(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        revision = self.repository.list_revisions(conference.learning_conference_id)[0]

        with self.adapter.database.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE learning_conference_revisions SET snapshot_json = '{}' WHERE learning_conference_revision_id = ?",
                    (revision.learning_conference_revision_id,),
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM learning_conference_revisions WHERE learning_conference_revision_id = ?",
                    (revision.learning_conference_revision_id,),
                )

    def test_hash_mismatch_prevents_historical_display_projection(self) -> None:
        self.adapter.complete_learning_conference(
            self.saved.learning_conference_draft_id
        )
        conference = self.repository.get_conference_for_source_draft(
            self.saved.learning_conference_draft_id
        )
        revision = self.repository.list_revisions(conference.learning_conference_id)[0]

        class CorruptRepository:
            def get_revision(self, revision_id: str) -> object:
                del revision_id
                return replace(revision, snapshot_json=revision.snapshot_json + " ")

        with self.assertRaises(LearningConferenceCompletionError) as caught:
            LearningConferenceRevisionReadService(
                CorruptRepository()
            ).load_verified_revision(revision.learning_conference_revision_id)

        self.assertEqual(
            caught.exception.code,
            LearningConferenceCompletionErrorCode.SNAPSHOT_INVALID,
        )

    def test_dialog_contains_no_persistence_snapshot_or_hash_logic(self) -> None:
        source = inspect.getsource(learning_conference_dialog)

        self.assertNotIn("sqlite3", source)
        self.assertNotIn("SQLiteLearningConferenceRepository", source)
        self.assertNotIn("hashlib", source)
        self.assertNotIn("snapshot_json", source)

    def _draft(self) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 7, 31),
            conference_date=date(2026, 7, 10),
            responsible_teacher="Laura Lernbegleiterin",
            conversation_entry_text="Interner Gesprächseinstieg",
            child_retrospective_text="Rückblick des Kindes",
            teacher_perspective_text="Interne Lehrkraftsicht",
            strengths_text="Interne Vorbereitung zu Stärken",
            development_fields_text="Gemeinsam betrachtete Entwicklung",
            prepared_goals_text="Vorbereitetes Ziel",
            prepared_support_text="Vorbereitete Unterstützung",
            prepared_agreements_text="Vorbereitete Vereinbarung",
            agreed_goals_text="Gemeinsam vereinbartes Ziel",
            agreed_support_text="Gemeinsam vereinbarte Unterstützung",
            agreed_agreements_text="Gemeinsame Vereinbarung",
            responsibilities_text="Kind: üben; Lehrkraft: begleiten",
            next_review_date=date(2026, 9, 15),
            subject_ids=(self.competency.subject_id,),
            cross_topic_keys=("social_behavior",),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(self.observation.observation_id,),
            chart_types=("documentation_coverage",),
        )


if __name__ == "__main__":
    unittest.main()
