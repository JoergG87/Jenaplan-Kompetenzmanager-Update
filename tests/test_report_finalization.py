"""Focused Sprint 5B.2 checks for immutable learning-report revisions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

from src.application.commands.report import (
    FinalizeLearningReportCommand,
    ReportFinalizationApplicationService,
)
from src.core.learning_report import (
    ReportFinalizationError,
    ReportFinalizationService,
    canonical_snapshot_json,
    snapshot_sha256,
)
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
)
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteLearningReportRepository,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportSubjectDraftViewModel,
)


class FailingRevisionRepository(SQLiteLearningReportRepository):
    """Inject a write failure after an existing revision was superseded."""

    def _insert_revision(self, connection, revision) -> None:  # type: ignore[no-untyped-def]
        raise sqlite3.IntegrityError("forced revision insert failure")


class ReportFinalizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "report-finalization.sqlite"
        create_sqlite_seed_database(self.database_path)
        self.adapter = StudentDesktopAdapter(self.database_path)
        self.database = self.adapter.database
        self.student = self.adapter.list_students()[0]
        self.competency = next(
            competency
            for competency in SQLiteCompetencyRepository(
                self.database
            ).list_competencies()
            if competency.active and competency.catalog_status == "current"
        )
        self.observation = ObservationRecord(
            "OBS-FINALIZE",
            self.student.student_id,
            "2026-03-12",
            self.competency.subject_id,
            "Lernzeit",
            "Bewusst eingefrorener Beobachtungsinhalt.",
            True,
            "2026-03-12T10:00:00+00:00",
            "2026-03-12T10:00:00+00:00",
            (
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
        SQLiteObservationRepository(self.database).create_observation(self.observation)
        self.saved_draft = self.adapter.save_learning_report_draft(self._draft())
        self.repository = SQLiteLearningReportRepository(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_first_finalization_creates_one_report_and_revision_one(self) -> None:
        result = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )

        self.assertEqual(result.report.learning_report_id, "RPT-000001")
        self.assertEqual(
            result.report.source_report_draft_id,
            self.saved_draft.report_draft_id,
        )
        self.assertEqual(
            result.revision.learning_report_revision_id,
            "RPV-000001",
        )
        self.assertEqual(result.revision.revision_number, 1)
        self.assertEqual(result.revision.status, "finalized")
        self.assertIsNone(result.revision.superseded_at)

    def test_repeated_finalization_reuses_report_and_creates_revision_two(self) -> None:
        first = self._service(datetime(2026, 7, 14, 8, tzinfo=UTC)).finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        updated = replace(self.saved_draft, overall_text="Bewusst korrigierter Gesamtblick.")
        self.saved_draft = self.adapter.save_learning_report_draft(updated)

        second = self._service(datetime(2026, 7, 15, 8, tzinfo=UTC)).finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        revisions = self.repository.list_revisions(first.report.learning_report_id)

        self.assertEqual(second.report, first.report)
        self.assertEqual(second.revision.revision_number, 2)
        self.assertEqual([item.status for item in revisions], ["superseded", "finalized"])
        with self.database.connect() as connection:
            report_count = connection.execute(
                "SELECT COUNT(*) FROM learning_reports"
            ).fetchone()[0]
        self.assertEqual(report_count, 1)

    def test_changed_period_after_revision_one_blocks_revision_two(self) -> None:
        first = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        self.saved_draft = self.adapter.save_learning_report_draft(
            replace(self.saved_draft, period_start=date(2026, 2, 1))
        )

        with self.assertRaisesRegex(
            ReportFinalizationError,
            "Aggregateidentitaet.*neuer Berichtsdraft",
        ):
            self._service(datetime(2026, 7, 15, 8, tzinfo=UTC)).finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

        self.assertEqual(
            self.repository.get_report_for_source_draft(
                self.saved_draft.report_draft_id
            ),
            first.report,
        )
        self.assertEqual(
            self.repository.list_revisions(first.report.learning_report_id),
            (first.revision,),
        )

    def test_changed_report_type_after_revision_one_blocks_revision_two(self) -> None:
        first = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        # The productive draft service and SQLite CHECK already reject this
        # mutation. Bypass only that CHECK to exercise the RPT identity guard.
        with self.database.connect() as connection:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute(
                """
                UPDATE report_drafts
                SET report_type = 'other_report_type',
                    updated_at = '2026-07-15T08:00:00+00:00'
                WHERE report_draft_id = ?
                """,
                (self.saved_draft.report_draft_id,),
            )
            connection.commit()

        with self.assertRaisesRegex(
            ReportFinalizationError,
            "Aggregateidentitaet.*neuer Berichtsdraft",
        ):
            self._service(datetime(2026, 7, 15, 8, tzinfo=UTC)).finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

        self.assertEqual(
            self.repository.get_report_for_source_draft(
                self.saved_draft.report_draft_id
            ),
            first.report,
        )
        self.assertEqual(
            self.repository.list_revisions(first.report.learning_report_id),
            (first.revision,),
        )

    def test_old_snapshot_and_hash_survive_all_source_changes(self) -> None:
        first = self._service(datetime(2026, 7, 14, 8, tzinfo=UTC)).finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        original_json = first.revision.snapshot_json
        original_hash = first.revision.snapshot_sha256
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE students SET first_name = 'Geaendert' WHERE student_id = ?",
                (self.student.student_id,),
            )
            connection.execute(
                "UPDATE competencies SET description = 'Geaenderte Kompetenz' WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.execute(
                "UPDATE observations SET note = 'Geaenderter Beleg' WHERE observation_id = ?",
                (self.observation.observation_id,),
            )
            connection.commit()
        self.saved_draft = self.adapter.save_learning_report_draft(
            replace(self.saved_draft, overall_text="Geaenderter Drafttext")
        )
        self._service(datetime(2026, 7, 15, 8, tzinfo=UTC)).finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )

        first_reloaded = self.repository.list_revisions(
            first.report.learning_report_id
        )[0]
        self.assertEqual(first_reloaded.snapshot_json, original_json)
        self.assertEqual(first_reloaded.snapshot_sha256, original_hash)
        payload = json.loads(original_json)
        self.assertEqual(payload["student"]["first_name"], self.student.first_name)
        self.assertEqual(
            payload["observations"][0]["content"],
            "Bewusst eingefrorener Beobachtungsinhalt.",
        )

    def test_snapshot_contains_ids_visible_values_provenance_and_chart_values(self) -> None:
        result = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )

        payload = json.loads(result.revision.snapshot_json)
        competency = payload["competencies"][0]
        observation = payload["observations"][0]
        chart_types = {chart["chart_type"] for chart in payload["charts"]}
        timeline = next(
            chart
            for chart in payload["charts"]
            if chart["chart_type"] == "competency_timeline"
        )

        self.assertEqual(payload["snapshot_schema_version"], 1)
        self.assertEqual(payload["source_report_draft_id"], "RPD-000001")
        self.assertEqual(payload["student"]["student_id"], self.student.student_id)
        self.assertEqual(competency["competency_id"], self.competency.competency_id)
        self.assertIn("learning_area", competency)
        self.assertEqual(observation["observation_id"], self.observation.observation_id)
        self.assertEqual(
            chart_types,
            {
                "documentation_coverage",
                "competency_timeline",
                "observation_timeline",
            },
        )
        self.assertEqual(
            timeline["values"]["series"][0]["points"][0]["source_type"],
            "observation",
        )

    def test_canonical_serialization_and_hash_are_exact_and_deterministic(self) -> None:
        left = {"z": "ä", "a": {"y": 2, "x": 1}}
        right = {"a": {"x": 1, "y": 2}, "z": "ä"}

        left_json = canonical_snapshot_json(left)
        right_json = canonical_snapshot_json(right)

        self.assertEqual(left_json, right_json)
        self.assertEqual(left_json, '{"a":{"x":1,"y":2},"z":"ä"}')
        self.assertEqual(
            snapshot_sha256(left_json),
            hashlib.sha256(left_json.encode("utf-8")).hexdigest(),
        )

    def test_saved_hash_matches_exact_stored_json_bytes(self) -> None:
        result = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )

        self.assertEqual(
            result.revision.snapshot_sha256,
            hashlib.sha256(result.revision.snapshot_json.encode("utf-8")).hexdigest(),
        )

    def test_missing_manual_content_blocks_finalization(self) -> None:
        empty_subject = LearningReportSubjectDraftViewModel(self.competency.subject_id)
        self.saved_draft = self.adapter.save_learning_report_draft(
            replace(
                self.saved_draft,
                overall_text="",
                subjects=(empty_subject,),
            )
        )

        with self.assertRaisesRegex(ReportFinalizationError, "Berichtstext"):
            self._service().finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

    def test_unavailable_observation_blocks_finalization(self) -> None:
        SQLiteObservationRepository(self.database).deactivate_observation(
            self.observation.observation_id,
            "2026-07-14T09:00:00+00:00",
        )

        with self.assertRaisesRegex(ReportFinalizationError, "Nicht verfuegbare"):
            self._service().finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

    def test_foreign_child_and_wrong_subject_observations_are_rejected(self) -> None:
        other_student = self.adapter.list_students()[1]
        foreign = replace(
            self.observation,
            observation_id="OBS-FOREIGN-FINALIZE",
            student_id=other_student.student_id,
        )
        SQLiteObservationRepository(self.database).create_observation(foreign)
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM report_draft_observations WHERE report_draft_id = ?",
                (self.saved_draft.report_draft_id,),
            )
            connection.execute(
                "INSERT INTO report_draft_observations VALUES (?, ?)",
                (self.saved_draft.report_draft_id, foreign.observation_id),
            )
            connection.commit()

        with self.assertRaisesRegex(ReportFinalizationError, "kind- oder fachfremd"):
            self._service().finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

        other_competency = next(
            competency
            for competency in SQLiteCompetencyRepository(self.database).list_competencies()
            if competency.subject_id != self.competency.subject_id
        )
        wrong_subject = ObservationRecord(
            "OBS-WRONG-SUBJECT-FINALIZE",
            self.student.student_id,
            "2026-04-12",
            other_competency.subject_id,
            "Fachfremd",
            "Fachfremder Beleg",
            True,
            "2026-04-12T10:00:00+00:00",
            "2026-04-12T10:00:00+00:00",
            (),
        )
        SQLiteObservationRepository(self.database).create_observation(wrong_subject)
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE report_draft_observations SET observation_id = ? WHERE report_draft_id = ?",
                (wrong_subject.observation_id, self.saved_draft.report_draft_id),
            )
            connection.commit()

        with self.assertRaisesRegex(ReportFinalizationError, "kind- oder fachfremd"):
            self._service().finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

    def test_wrong_subject_competency_is_rejected(self) -> None:
        other_competency = next(
            competency
            for competency in SQLiteCompetencyRepository(self.database).list_competencies()
            if competency.subject_id != self.competency.subject_id
        )
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM report_draft_competencies WHERE report_draft_id = ?",
                (self.saved_draft.report_draft_id,),
            )
            connection.execute(
                "INSERT INTO report_draft_competencies VALUES (?, ?)",
                (self.saved_draft.report_draft_id, other_competency.competency_id),
            )
            connection.commit()

        with self.assertRaisesRegex(ReportFinalizationError, "fachfremd"):
            self._service().finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

    def test_resolvable_inactive_competency_is_frozen_as_historical(self) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE competencies SET active = 0, description = 'Spaeter geaenderter Katalogtext' WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.commit()

        result = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        competency = json.loads(result.revision.snapshot_json)["competencies"][0]

        self.assertTrue(competency["historical_reference"])
        self.assertFalse(competency["active_at_finalization"])
        self.assertEqual(competency["competency_text"], self.competency.description)

    def test_failed_first_write_leaves_no_report_or_revision(self) -> None:
        service = ReportFinalizationService(
            FailingRevisionRepository(self.database),
            now=lambda: datetime(2026, 7, 14, 8, tzinfo=UTC),
        )

        with self.assertRaises(ReportFinalizationError):
            service.finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

        with self.database.connect() as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM learning_reports").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM learning_report_revisions"
                ).fetchone()[0],
                0,
            )

    def test_failed_followup_keeps_previous_revision_finalized(self) -> None:
        first = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        service = ReportFinalizationService(
            FailingRevisionRepository(self.database),
            now=lambda: datetime(2026, 7, 15, 8, tzinfo=UTC),
        )

        with self.assertRaises(ReportFinalizationError):
            service.finalize(
                report_draft_id=self.saved_draft.report_draft_id,
                finalized_by_display_name="Laura Lernbegleiterin",
            )

        revisions = self.repository.list_revisions(first.report.learning_report_id)
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0].status, "finalized")
        self.assertIsNone(revisions[0].superseded_at)

    def test_revision_payload_cannot_be_updated_or_deleted(self) -> None:
        result = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )
        with self.database.connect() as connection:
            protected_changes = (
                ("snapshot_json", "{}"),
                ("snapshot_sha256", "0" * 64),
                ("revision_number", 99),
                ("finalized_at", "2099-01-01T00:00:00+00:00"),
                ("finalized_by_display_name", "Andere Person"),
            )
            for column_name, value in protected_changes:
                with self.subTest(column_name=column_name):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(
                            f"""
                            UPDATE learning_report_revisions
                            SET {column_name} = ?
                            WHERE learning_report_revision_id = ?
                            """,
                            (value, result.revision.learning_report_revision_id),
                        )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM learning_report_revisions WHERE learning_report_revision_id = ?",
                    (result.revision.learning_report_revision_id,),
                )

        self.assertEqual(
            self.repository.list_revisions(result.report.learning_report_id),
            (result.revision,),
        )

    def test_report_aggregate_cannot_be_updated_or_deleted(self) -> None:
        result = self._service().finalize(
            report_draft_id=self.saved_draft.report_draft_id,
            finalized_by_display_name="Laura Lernbegleiterin",
        )

        with self.database.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE learning_reports
                    SET period_start = '2026-02-01'
                    WHERE learning_report_id = ?
                    """,
                    (result.report.learning_report_id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM learning_reports WHERE learning_report_id = ?",
                    (result.report.learning_report_id,),
                )

        self.assertEqual(
            self.repository.get_report_for_source_draft(
                self.saved_draft.report_draft_id
            ),
            result.report,
        )

    def test_application_command_uses_finalization_service(self) -> None:
        application = ReportFinalizationApplicationService(self._service())

        result = application.finalize(
            FinalizeLearningReportCommand(
                self.saved_draft.report_draft_id,
                "Laura Lernbegleiterin",
            )
        )

        self.assertEqual(result.revision.revision_number, 1)

    def _service(
        self,
        at: datetime = datetime(2026, 7, 14, 8, tzinfo=UTC),
    ) -> ReportFinalizationService:
        return ReportFinalizationService(self.repository, now=lambda: at)

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


class ReportFinalizationMigrationTest(unittest.TestCase):
    def test_additive_idempotent_migration_preserves_filled_report_draft_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "migration.sqlite"
            create_sqlite_seed_database(path)
            adapter = StudentDesktopAdapter(path)
            student = adapter.list_students()[0]
            competency = next(
                item
                for item in SQLiteCompetencyRepository(adapter.database).list_competencies()
                if item.active and item.catalog_status == "current"
            )
            observation = ObservationRecord(
                "OBS-MIGRATION-KEEP",
                student.student_id,
                "2026-03-12",
                competency.subject_id,
                "Lernzeit",
                "Bestandsbeleg",
                True,
                "2026-03-12T10:00:00+00:00",
                "2026-03-12T10:00:00+00:00",
                (),
            )
            SQLiteObservationRepository(adapter.database).create_observation(observation)
            draft = adapter.save_learning_report_draft(
                LearningReportDraftViewModel(
                    student_id=student.student_id,
                    period_start=date(2026, 1, 1),
                    period_end=date(2026, 7, 31),
                    teacher_name="Laura",
                    overall_text="Bestandsinhalt",
                    subjects=(
                        LearningReportSubjectDraftViewModel(
                            competency.subject_id,
                            "Staerke",
                            "Entwicklung",
                            "Unterstuetzung",
                            "Ziel",
                        ),
                    ),
                    competency_ids=(competency.competency_id,),
                    observation_ids=(observation.observation_id,),
                    chart_selections=(
                        LearningReportChartSelectionViewModel(
                            competency.subject_id,
                            "documentation_coverage",
                        ),
                    ),
                )
            )
            with adapter.database.connect() as connection:
                connection.execute("DROP TABLE learning_report_revisions")
                connection.execute("DROP TABLE learning_reports")
                connection.commit()

            database = SQLiteDatabase(path)
            database.initialize_schema()
            database.initialize_schema()

            with database.connect() as connection:
                main = connection.execute(
                    "SELECT * FROM report_drafts WHERE report_draft_id = ?",
                    (draft.report_draft_id,),
                ).fetchone()
                subject = connection.execute(
                    "SELECT * FROM report_draft_subjects WHERE report_draft_id = ?",
                    (draft.report_draft_id,),
                ).fetchone()
                competency_row = connection.execute(
                    "SELECT * FROM report_draft_competencies WHERE report_draft_id = ?",
                    (draft.report_draft_id,),
                ).fetchone()
                observation_row = connection.execute(
                    "SELECT * FROM report_draft_observations WHERE report_draft_id = ?",
                    (draft.report_draft_id,),
                ).fetchone()
                chart = connection.execute(
                    "SELECT * FROM report_draft_charts WHERE report_draft_id = ?",
                    (draft.report_draft_id,),
                ).fetchone()
                tables = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }

            self.assertEqual(main["overall_text"], "Bestandsinhalt")
            self.assertEqual(subject["strengths_text"], "Staerke")
            self.assertEqual(competency_row["competency_id"], competency.competency_id)
            self.assertEqual(
                observation_row["observation_id"],
                observation.observation_id,
            )
            self.assertEqual(chart["chart_type"], "documentation_coverage")
            self.assertIn("learning_reports", tables)
            self.assertIn("learning_report_revisions", tables)


if __name__ == "__main__":
    unittest.main()
