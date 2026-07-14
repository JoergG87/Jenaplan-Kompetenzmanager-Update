"""Focused persistence tests for Sprint 7F.1 learning-report drafts."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.core.observation import ObservationRecord
from src.core.report_draft import ReportDraftError
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportSubjectDraftViewModel,
)


class ReportDraftPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "report-draft.sqlite"
        create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.student = self.adapter.list_students()[0]
        self.competency = next(
            competency
            for competency in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if competency.active and competency.catalog_status == "current"
        )
        self.observation = ObservationRecord(
            "OBS-REPORT-DRAFT",
            self.student.student_id,
            "2026-03-12",
            self.competency.subject_id,
            "Lernzeit",
            "Bewusst auswählbarer Beobachtungsbeleg.",
            True,
            "2026-03-12T10:00:00+00:00",
            "2026-03-12T10:00:00+00:00",
            (),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            self.observation
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_load_complete_report_draft(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())

        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)

        self.assertEqual(saved.report_draft_id, "RPD-000001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded, saved)
        self.assertEqual(saved.status, "draft")
        self.assertEqual(saved.report_type, "learning_development")
        self.assertEqual(saved.selected_subject_ids, (self.competency.subject_id,))
        self.assertEqual(saved.competency_ids, (self.competency.competency_id,))
        self.assertEqual(saved.observation_ids, (self.observation.observation_id,))
        self.assertEqual(
            {chart.chart_type for chart in saved.chart_selections},
            {
                "documentation_coverage",
                "competency_timeline",
                "observation_timeline",
            },
        )

    def test_update_replaces_texts_and_all_selections_atomically(self) -> None:
        created = self.adapter.save_learning_report_draft(self._draft())
        updated_subject = LearningReportSubjectDraftViewModel(
            self.competency.subject_id,
            "Neue Stärke",
            "Neue Lernentwicklung",
            "Neue Unterstützung",
            "Neues Ziel",
        )
        update = replace(
            created,
            overall_text="Überarbeiteter Gesamtblick",
            subjects=(updated_subject,),
            competency_ids=(),
            observation_ids=(),
            chart_selections=(
                LearningReportChartSelectionViewModel(
                    self.competency.subject_id,
                    "documentation_coverage",
                ),
            ),
        )

        saved = self.adapter.save_learning_report_draft(update)
        reloaded = self.adapter.load_learning_report_draft(created.report_draft_id)

        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.overall_text, "Überarbeiteter Gesamtblick")
        self.assertEqual(reloaded.subjects, (updated_subject,))
        self.assertEqual(reloaded.competency_ids, ())
        self.assertEqual(reloaded.observation_ids, ())
        self.assertEqual(len(reloaded.chart_selections), 1)
        self.assertEqual(reloaded.created_at, created.created_at)
        self.assertEqual(saved.report_draft_id, created.report_draft_id)

    def test_list_drafts_for_student(self) -> None:
        first = self.adapter.save_learning_report_draft(self._draft())
        second = self.adapter.save_learning_report_draft(
            replace(self._draft(), overall_text="Zweiter Entwurf")
        )

        listed = self.adapter.list_learning_report_drafts_for_student(
            self.student.student_id
        )

        self.assertEqual(
            {draft.report_draft_id for draft in listed},
            {first.report_draft_id, second.report_draft_id},
        )

    def test_manual_subject_texts_round_trip(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())
        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)

        self.assertEqual(loaded.subjects[0].strengths_text, "Mara arbeitet sorgfältig.")
        self.assertEqual(
            loaded.subjects[0].development_text,
            "Sie nutzt Rückmeldungen zunehmend selbstständig.",
        )
        self.assertEqual(
            loaded.subjects[0].support_needs_text,
            "Überschaubare Zwischenschritte helfen.",
        )
        self.assertEqual(
            loaded.subjects[0].next_goals_text,
            "Eigene Lösungswege kurz festhalten.",
        )

    def test_competency_selection_round_trip(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())

        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)

        self.assertEqual(loaded.competency_ids, (self.competency.competency_id,))

    def test_observation_evidence_selection_round_trip(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())

        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)

        self.assertEqual(loaded.observation_ids, (self.observation.observation_id,))

    def test_chart_selection_round_trip(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())

        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)

        self.assertEqual(
            {chart.chart_type for chart in loaded.chart_selections},
            {
                "documentation_coverage",
                "competency_timeline",
                "observation_timeline",
            },
        )

    def test_persistence_does_not_change_competency_or_observation_projection(self) -> None:
        statuses_before = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )
        observations_before = self.adapter.list_observations_for_student(
            self.student.student_id
        )

        self.adapter.save_learning_report_draft(self._draft())

        statuses_after = self.adapter.list_competency_status_projection_for_student(
            self.student.student_id
        )
        observations_after = self.adapter.list_observations_for_student(
            self.student.student_id
        )
        self.assertEqual(statuses_after, statuses_before)
        self.assertEqual(observations_after, observations_before)

    def test_relation_tables_store_references_not_copied_source_content(self) -> None:
        self.adapter.save_learning_report_draft(self._draft())
        with self.adapter.database.connect() as connection:
            competency_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(report_draft_competencies)"
                ).fetchall()
            }
            observation_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(report_draft_observations)"
                ).fetchall()
            }

        self.assertEqual(
            competency_columns,
            {"report_draft_id", "competency_id"},
        )
        self.assertEqual(
            observation_columns,
            {"report_draft_id", "observation_id"},
        )

    def test_deactivated_selected_competency_remains_resolvable_and_selected(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0 WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.commit()

        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            retained_competency_ids=loaded.competency_ids,
        )
        retained = next(
            competency
            for subject in preparation.subjects
            for competency in subject.competencies
            if competency.competency_id == self.competency.competency_id
        )
        resaved = self.adapter.save_learning_report_draft(loaded)

        self.assertEqual(loaded.competency_ids, (self.competency.competency_id,))
        self.assertEqual(resaved.competency_ids, (self.competency.competency_id,))
        self.assertTrue(retained.historical)
        self.assertFalse(retained.selectable)

    def test_deactivated_competency_cannot_be_newly_selected(self) -> None:
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0 WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.commit()

        with self.assertRaises(ReportDraftError):
            self.adapter.save_learning_report_draft(self._draft())

    def test_soft_deleted_selected_observation_remains_unavailable_reference(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())
        SQLiteObservationRepository(self.adapter.database).deactivate_observation(
            self.observation.observation_id,
            "2026-03-13T10:00:00+00:00",
        )

        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)
        resaved = self.adapter.save_learning_report_draft(loaded)
        reloaded = self.adapter.load_learning_report_draft(resaved.report_draft_id)

        self.assertEqual(reloaded.observation_ids, (self.observation.observation_id,))
        self.assertEqual(
            reloaded.unavailable_observation_ids,
            (self.observation.observation_id,),
        )

    def test_soft_deleted_observation_cannot_be_newly_selected(self) -> None:
        SQLiteObservationRepository(self.adapter.database).deactivate_observation(
            self.observation.observation_id,
            "2026-03-13T10:00:00+00:00",
        )

        with self.assertRaises(ReportDraftError):
            self.adapter.save_learning_report_draft(self._draft())

    def test_explicit_deselection_removes_retained_relations(self) -> None:
        saved = self.adapter.save_learning_report_draft(self._draft())
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0 WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.execute(
                "UPDATE observations SET active = 0 WHERE observation_id = ?",
                (self.observation.observation_id,),
            )
            connection.commit()

        updated = self.adapter.save_learning_report_draft(
            replace(saved, competency_ids=(), observation_ids=())
        )

        self.assertEqual(updated.competency_ids, ())
        self.assertEqual(updated.observation_ids, ())
        self.assertEqual(updated.unavailable_observation_ids, ())

    def test_foreign_child_subject_and_observation_references_are_rejected(self) -> None:
        other_student = self.adapter.list_students()[1]
        other_subject_competency = next(
            competency
            for competency in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if competency.active
            and competency.catalog_status == "current"
            and competency.subject_id != self.competency.subject_id
        )
        foreign_child_observation = ObservationRecord(
            "OBS-FOREIGN-CHILD",
            other_student.student_id,
            "2026-03-12",
            self.competency.subject_id,
            "Lernzeit",
            "Fremder Beleg.",
            True,
            "2026-03-12T10:00:00+00:00",
            "2026-03-12T10:00:00+00:00",
            (),
        )
        wrong_subject_observation = replace(
            self.observation,
            observation_id="OBS-WRONG-SUBJECT",
            subject_id=other_subject_competency.subject_id,
        )
        repository = SQLiteObservationRepository(self.adapter.database)
        repository.create_observation(foreign_child_observation)
        repository.create_observation(wrong_subject_observation)

        with self.assertRaises(ReportDraftError):
            self.adapter.save_learning_report_draft(
                replace(
                    self._draft(),
                    observation_ids=(foreign_child_observation.observation_id,),
                )
            )
        with self.assertRaises(ReportDraftError):
            self.adapter.save_learning_report_draft(
                replace(
                    self._draft(),
                    competency_ids=(other_subject_competency.competency_id,),
                    observation_ids=(),
                )
            )
        with self.assertRaises(ReportDraftError):
            self.adapter.save_learning_report_draft(
                replace(
                    self._draft(),
                    observation_ids=(wrong_subject_observation.observation_id,),
                )
            )

    def _draft(self) -> LearningReportDraftViewModel:
        subject = LearningReportSubjectDraftViewModel(
            self.competency.subject_id,
            "Mara arbeitet sorgfältig.",
            "Sie nutzt Rückmeldungen zunehmend selbstständig.",
            "Überschaubare Zwischenschritte helfen.",
            "Eigene Lösungswege kurz festhalten.",
        )
        charts = tuple(
            LearningReportChartSelectionViewModel(
                self.competency.subject_id,
                chart_type,
            )
            for chart_type in (
                "documentation_coverage",
                "competency_timeline",
                "observation_timeline",
            )
        )
        return LearningReportDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            teacher_name="Laura Lernbegleiterin",
            overall_text="Manuell verfasster pädagogischer Gesamtblick.",
            subjects=(subject,),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(self.observation.observation_id,),
            chart_selections=charts,
        )


class ReportDraftMigrationTest(unittest.TestCase):
    def test_initialize_schema_adds_report_tables_without_replacing_existing_rows(self) -> None:
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

            database = SQLiteDatabase(path)
            database.initialize_schema()

            with database.connect() as migrated:
                tables = {
                    row["name"]
                    for row in migrated.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                group = migrated.execute(
                    "SELECT group_name FROM groups WHERE group_id = ?",
                    ("GRP-KEEP",),
                ).fetchone()
            self.assertEqual(
                {
                    "report_drafts",
                    "report_draft_subjects",
                    "report_draft_competencies",
                    "report_draft_observations",
                    "report_draft_charts",
                }
                - tables,
                set(),
            )
            self.assertEqual(group["group_name"], "Bestehende Gruppe")


if __name__ == "__main__":
    unittest.main()
