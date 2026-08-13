"""Focused persistence tests for Sprint 7F.1 learning-report drafts."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
)
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
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
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
        self.other_competency = next(
            competency
            for competency in SQLiteCompetencyRepository(
                self.adapter.database
            ).list_competencies()
            if (
                competency.active
                and competency.catalog_status == "current"
                and competency.subject_id != self.competency.subject_id
            )
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
        self.other_observation = ObservationRecord(
            "OBS-REPORT-DRAFT-OTHER",
            self.student.student_id,
            "2026-03-13",
            self.other_competency.subject_id,
            "Werkstatt",
            "Bewusst auswählbarer Beleg eines anderen Fachs.",
            True,
            "2026-03-13T10:00:00+00:00",
            "2026-03-13T10:00:00+00:00",
            (),
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            self.other_observation
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

    def test_report_subjects_follow_individual_profile_without_cross_curricular_domains(
        self,
    ) -> None:
        school_year = self.adapter.current_school_year()
        self.assertIsNotNone(school_year)
        if school_year is None:
            raise AssertionError("Expected current school year")
        baseline = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=school_year.end_date,
        )
        self.assertIsNotNone(baseline)
        if baseline is None:
            raise AssertionError("Expected baseline report preparation")
        teaching_subject_ids = tuple(
            subject.subject_id for subject in baseline.subjects
        )
        primary_subject_id = teaching_subject_ids[-1]
        self.adapter.save_student_documentation_subjects(
            self.student.student_id,
            school_year.school_year_id,
            "custom",
            (primary_subject_id,),
        )

        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=school_year.end_date,
        )

        self.assertIsNotNone(preparation)
        if preparation is None:
            raise AssertionError("Expected report preparation")
        offered_subject_ids = tuple(
            subject.subject_id for subject in preparation.subjects
        )
        self.assertEqual(preparation.primary_subject_ids, (primary_subject_id,))
        self.assertEqual(offered_subject_ids[0], primary_subject_id)
        self.assertEqual(set(offered_subject_ids), set(teaching_subject_ids))
        self.assertTrue(
            set(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS).isdisjoint(
                offered_subject_ids
            )
        )

    def test_empty_custom_profile_keeps_teaching_subjects_reachable_but_none_primary(
        self,
    ) -> None:
        school_year = self.adapter.current_school_year()
        self.assertIsNotNone(school_year)
        if school_year is None:
            raise AssertionError("Expected current school year")
        baseline = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=school_year.end_date,
        )
        self.assertIsNotNone(baseline)
        if baseline is None:
            raise AssertionError("Expected baseline report preparation")
        expected_subject_ids = {
            subject.subject_id for subject in baseline.subjects
        }
        self.adapter.save_student_documentation_subjects(
            self.student.student_id,
            school_year.school_year_id,
            "custom",
            (),
        )

        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=school_year.end_date,
        )

        self.assertIsNotNone(preparation)
        if preparation is None:
            raise AssertionError("Expected report preparation")
        self.assertEqual(preparation.primary_subject_ids, ())
        self.assertEqual(
            {subject.subject_id for subject in preparation.subjects},
            expected_subject_ids,
        )
        self.assertTrue(
            set(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS).isdisjoint(
                expected_subject_ids
            )
        )

    def test_saved_subject_without_competency_remains_in_preparation(self) -> None:
        retained_subject_id = COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS[0]
        retained_subject = LearningReportSubjectDraftViewModel(
            retained_subject_id,
            "Gespeicherte Stärke.",
            "Gespeicherte Entwicklung.",
            "",
            "Gespeichertes Ziel.",
        )
        saved = self.adapter.save_learning_report_draft(
            replace(
                self._draft(),
                subjects=(retained_subject,),
                competency_ids=(),
                observation_ids=(),
                chart_selections=(),
            )
        )
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0 WHERE subject_id = ?",
                (retained_subject_id,),
            )
            connection.commit()

        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=saved.period_end,
            retained_subject_ids=saved.selected_subject_ids,
        )

        self.assertIsNotNone(preparation)
        if preparation is None:
            raise AssertionError("Expected report preparation")
        self.assertEqual(preparation.retained_subject_ids, (retained_subject_id,))
        retained = next(
            subject
            for subject in preparation.subjects
            if subject.subject_id == retained_subject_id
        )
        self.assertEqual(retained.competencies, ())

    def test_new_period_creates_a_separate_draft_without_changing_existing_one(self) -> None:
        first = self.adapter.save_learning_report_draft(self._draft())
        second = self.adapter.save_learning_report_draft(
            replace(
                self._draft(),
                period_start=date(2026, 8, 1),
                period_end=date(2027, 1, 31),
                overall_text="Eigenständiger Bericht für den nächsten Zeitraum.",
            )
        )

        listed = self.adapter.list_learning_report_drafts_for_student(
            self.student.student_id
        )
        reloaded_first = self.adapter.load_learning_report_draft(first.report_draft_id)

        self.assertNotEqual(first.report_draft_id, second.report_draft_id)
        self.assertEqual(len(listed), 2)
        self.assertEqual(reloaded_first, first)
        self.assertEqual(
            self.adapter.load_learning_report_draft(second.report_draft_id).period_start,
            date(2026, 8, 1),
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

    def test_confirmed_subject_removal_persists_only_the_affected_context(self) -> None:
        created = self.adapter.save_learning_report_draft(
            replace(
                self._draft(),
                subjects=(
                    LearningReportSubjectDraftViewModel(
                        self.competency.subject_id, "Mathetext"
                    ),
                    LearningReportSubjectDraftViewModel(
                        self.other_competency.subject_id, "Anderer Fachtext"
                    ),
                ),
                competency_ids=(
                    self.competency.competency_id,
                    self.other_competency.competency_id,
                ),
                observation_ids=(
                    self.observation.observation_id,
                    self.other_observation.observation_id,
                ),
                chart_selections=(
                    LearningReportChartSelectionViewModel(
                        self.competency.subject_id, "documentation_coverage"
                    ),
                    LearningReportChartSelectionViewModel(
                        self.other_competency.subject_id, "competency_timeline"
                    ),
                ),
            )
        )

        saved = self.adapter.save_learning_report_draft(
            replace(
                created,
                subjects=(
                    LearningReportSubjectDraftViewModel(
                        self.other_competency.subject_id, "Anderer Fachtext"
                    ),
                ),
                competency_ids=(self.other_competency.competency_id,),
                observation_ids=(self.other_observation.observation_id,),
                chart_selections=(
                    LearningReportChartSelectionViewModel(
                        self.other_competency.subject_id, "competency_timeline"
                    ),
                ),
            )
        )
        reloaded = self.adapter.load_learning_report_draft(created.report_draft_id)

        self.assertEqual(saved.report_draft_id, created.report_draft_id)
        self.assertIsNotNone(reloaded)
        if reloaded is None:
            raise AssertionError("Expected saved report draft")
        self.assertEqual(reloaded.selected_subject_ids, (self.other_competency.subject_id,))
        self.assertEqual(reloaded.competency_ids, (self.other_competency.competency_id,))
        self.assertEqual(reloaded.observation_ids, (self.other_observation.observation_id,))
        self.assertEqual(
            reloaded.chart_selections,
            (
                LearningReportChartSelectionViewModel(
                    self.other_competency.subject_id, "competency_timeline"
                ),
            ),
        )

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
            period_end=loaded.period_end,
            retained_competency_ids=loaded.competency_ids,
            retained_subject_ids=loaded.selected_subject_ids,
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

    def test_active_selected_observation_is_projected_without_writing(self) -> None:
        repository = SQLiteObservationRepository(self.adapter.database)
        repository.update_observation(
            replace(
                self.observation,
                competency_ratings=(
                    ObservationCompetencyRatingRecord(
                        self.competency.competency_id,
                        self.competency.subject_id,
                        self.competency.subject_name,
                        self.competency.learning_area,
                        self.competency.competency_group,
                        self.competency.description,
                        "+",
                    ),
                ),
            )
        )
        before = repository.get_observation(
            self.observation.observation_id
        )

        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=date(2026, 7, 31),
            retained_observation_ids=(self.observation.observation_id,),
            retained_subject_ids=(self.competency.subject_id,),
        )

        self.assertIsNotNone(preparation)
        if preparation is None:
            raise AssertionError("Expected report preparation")
        projected = next(
            evidence
            for subject in preparation.subjects
            for evidence in subject.evidence
            if evidence.observation_id == self.observation.observation_id
        )
        after = repository.get_observation(
            self.observation.observation_id
        )
        self.assertEqual(projected.subject_id, self.competency.subject_id)
        self.assertEqual(projected.availability_state, "active")
        self.assertEqual(after, before)

    def test_soft_deleted_selected_observation_uses_stored_rating_snapshot(self) -> None:
        snapshot_text = "Historisch gespeicherter Kompetenztext"
        snapshot_subject_label = "Historisch gespeichertes Fach"
        rating = ObservationCompetencyRatingRecord(
            self.competency.competency_id,
            self.competency.subject_id,
            snapshot_subject_label,
            "Historischer Kompetenzbereich",
            "Historisches Thema",
            snapshot_text,
            "+",
        )
        repository = SQLiteObservationRepository(self.adapter.database)
        repository.update_observation(
            replace(self.observation, competency_ratings=(rating,))
        )
        saved = self.adapter.save_learning_report_draft(self._draft())
        repository.deactivate_observation(
            self.observation.observation_id,
            "2026-03-13T10:00:00+00:00",
        )
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0, description = ? "
                "WHERE competency_id = ?",
                (
                    "Heutiger Katalogtext darf den Snapshot nicht ersetzen",
                    self.competency.competency_id,
                ),
            )
            connection.commit()
        loaded = self.adapter.load_learning_report_draft(saved.report_draft_id)
        self.assertIsNotNone(loaded)
        if loaded is None:
            raise AssertionError("Expected persisted draft")

        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=loaded.period_end,
            retained_competency_ids=loaded.competency_ids,
            retained_observation_ids=loaded.observation_ids,
            retained_subject_ids=loaded.selected_subject_ids,
        )

        self.assertIsNotNone(preparation)
        if preparation is None:
            raise AssertionError("Expected report preparation")
        subject = next(
            item
            for item in preparation.subjects
            if item.subject_id == self.competency.subject_id
        )
        competency = next(
            item
            for item in subject.competencies
            if item.competency_id == self.competency.competency_id
        )
        evidence = next(
            item
            for item in subject.evidence
            if item.observation_id == self.observation.observation_id
        )
        self.assertEqual(loaded.unavailable_observation_ids, loaded.observation_ids)
        self.assertEqual(competency.competency_text, snapshot_text)
        self.assertEqual(competency.subject_name, snapshot_subject_label)
        self.assertTrue(competency.historical)
        self.assertEqual(competency.documentation_state, "undocumented")
        self.assertEqual(evidence.availability_state, "historical")
        self.assertEqual(evidence.subject_name, snapshot_subject_label)
        self.assertEqual(
            evidence.competency_ids,
            (self.competency.competency_id,),
        )

    def test_missing_and_foreign_retained_observations_are_not_projected(self) -> None:
        foreign_student = self.adapter.list_students()[1]
        foreign_observation = replace(
            self.observation,
            observation_id="OBS-FOREIGN-PROJECTION",
            student_id=foreign_student.student_id,
        )
        SQLiteObservationRepository(self.adapter.database).create_observation(
            foreign_observation
        )

        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=date(2026, 7, 31),
            retained_observation_ids=(
                "OBS-MISSING",
                foreign_observation.observation_id,
            ),
            retained_subject_ids=(self.competency.subject_id,),
        )

        self.assertIsNotNone(preparation)
        if preparation is None:
            raise AssertionError("Expected report preparation")
        self.assertNotIn("OBS-MISSING", preparation.projected_observation_ids)
        self.assertNotIn(
            foreign_observation.observation_id,
            preparation.projected_observation_ids,
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
    def test_unknown_partial_schema_is_rejected_without_replacing_existing_rows(self) -> None:
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
