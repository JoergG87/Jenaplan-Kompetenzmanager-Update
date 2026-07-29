"""Focused integration checks for Phase-2 report-overview read sources."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.database_engine import SQLiteConnectionProvider
from src.core.observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
)
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteLearningConferenceRepository,
    SQLiteLearningReportRepository,
    SQLiteObservationRepository,
    SQLiteStudentDocumentationProjectionRepository,
    create_sqlite_seed_database,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
)
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportSubjectDraftViewModel,
)


class _TracingConnectionProvider:
    def __init__(self) -> None:
        self.base = SQLiteConnectionProvider()
        self.statements: list[str] = []

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> sqlite3.Connection:
        connection = self.base.connect(
            path,
            create=create,
            key_material=key_material,
        )
        connection.set_trace_callback(self.statements.append)
        return connection


class ReportOverviewPhase2AdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "phase2.sqlite"
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
        self.observation = self._observation(
            "OBS-PHASE2-START",
            "2026-01-01",
        )
        observation_repository = SQLiteObservationRepository(
            self.adapter.database
        )
        observation_repository.create_observation(self.observation)
        deleted = self._observation("OBS-PHASE2-DELETED", "2026-07-31")
        observation_repository.create_observation(deleted)
        observation_repository.deactivate_observation(
            deleted.observation_id,
            "2026-07-31T12:00:00+00:00",
        )
        self.report_draft = self.adapter.save_learning_report_draft(
            self._report_draft()
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_phase2_requires_one_explicit_current_rpd_selection(self) -> None:
        without_selection = self.adapter.report_overview_for_student(
            self.student.student_id
        )
        stale_selection = self.adapter.report_overview_for_student(
            self.student.student_id,
            selected_report_draft_id="RPD-REMOVED",
        )
        selected = self.adapter.report_overview_for_student(
            self.student.student_id,
            selected_report_draft_id=self.report_draft.report_draft_id,
        )
        second_draft = self.adapter.save_learning_report_draft(
            replace(
                self._report_draft(),
                overall_text="Zweiter bewusst angelegter Berichtsentwurf.",
            )
        )
        multiple_without_selection = (
            self.adapter.report_overview_for_student(
                self.student.student_id
            )
        )

        self.assertEqual(without_selection.selected_report_draft_id, "")
        self.assertEqual(without_selection.timeline_events, ())
        self.assertEqual(without_selection.subject_documentation, ())
        self.assertEqual(stale_selection.selected_report_draft_id, "")
        self.assertEqual(stale_selection.timeline_events, ())
        self.assertEqual(
            selected.selected_report_draft_id,
            self.report_draft.report_draft_id,
        )
        self.assertEqual(
            [event.source_identity for event in selected.timeline_events],
            [("observation", self.observation.observation_id)],
        )
        self.assertNotEqual(
            second_draft.report_draft_id,
            self.report_draft.report_draft_id,
        )
        self.assertEqual(multiple_without_selection.timeline_events, ())

    def test_live_snapshot_filters_soft_deleted_rows_and_keeps_stable_ids(self) -> None:
        self.adapter.save_competency_confirmation(
            student_id=self.student.student_id,
            competency_id=self.competency.competency_id,
            confirmed_rating="+",
        )

        overview = self.adapter.report_overview_for_student(
            self.student.student_id,
            selected_report_draft_id=self.report_draft.report_draft_id,
        )

        identities = {
            event.source_identity for event in overview.timeline_events
        }
        self.assertIn(("observation", "OBS-PHASE2-START"), identities)
        self.assertNotIn(("observation", "OBS-PHASE2-DELETED"), identities)
        self.assertIn(
            (
                "confirmation",
                self.student.student_id,
                self.competency.competency_id,
            ),
            identities,
        )
        subject = next(
            item
            for item in overview.subject_documentation
            if item.subject_id == self.competency.subject_id
        )
        self.assertEqual(
            subject.competency_ids,
            (self.competency.competency_id,),
        )
        self.assertEqual(subject.observation_ids, ("OBS-PHASE2-START",))

    def test_report_and_leg_histories_select_latest_valid_revision(self) -> None:
        self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        self.report_draft = self.adapter.save_learning_report_draft(
            replace(
                self.report_draft,
                overall_text="Bewusst korrigierter Berichtstext.",
            )
        )
        report_status = self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        leg_draft = self.adapter.save_learning_conference_draft(
            self._learning_conference_draft()
        )
        self.adapter.complete_learning_conference(
            leg_draft.learning_conference_draft_id
        )
        leg_draft = self.adapter.save_learning_conference_draft(
            replace(
                leg_draft,
                agreed_agreements_text="Bewusst korrigierte Vereinbarung.",
            )
        )
        leg_status = self.adapter.complete_learning_conference(
            leg_draft.learning_conference_draft_id
        )

        overview = self.adapter.report_overview_for_student(
            self.student.student_id,
            selected_report_draft_id=self.report_draft.report_draft_id,
        )
        report_events = tuple(
            event
            for event in overview.timeline_events
            if event.event_type == "report"
        )
        leg_events = tuple(
            event
            for event in overview.timeline_events
            if event.event_type == "learning_conference"
        )

        self.assertEqual(len(report_events), 1)
        self.assertEqual(
            report_events[0].source_identity,
            ("report", self.report_draft.report_draft_id),
        )
        self.assertEqual(
            report_events[0].action.target_id,
            report_status.current_revision_id,
        )
        self.assertEqual(len(leg_events), 1)
        self.assertEqual(
            leg_events[0].source_identity,
            ("learning_conference", leg_draft.learning_conference_draft_id),
        )
        self.assertEqual(
            leg_events[0].action.target_id,
            next(
                item.learning_conference_revision_id
                for item in leg_status.revisions
                if item.status == "completed"
            ),
        )
        self.assertEqual(leg_events[0].occurred_on, date(2026, 7, 10))

    def test_live_read_failure_retains_valid_document_events(self) -> None:
        self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )

        with patch.object(
            SQLiteStudentDocumentationProjectionRepository,
            "read_batch",
            side_effect=RuntimeError("live unavailable"),
        ):
            overview = self.adapter.report_overview_for_student(
                self.student.student_id,
                selected_report_draft_id=self.report_draft.report_draft_id,
            )

        self.assertEqual(
            tuple(
                event.event_type
                for event in overview.timeline_events
            ),
            ("report",),
        )
        self.assertIn(
            "source:live_documentation",
            {warning.warning_key for warning in overview.projection_warnings},
        )

    def test_invalid_newest_report_revision_falls_back_without_losing_event(
        self,
    ) -> None:
        self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        self.report_draft = self.adapter.save_learning_report_draft(
            replace(
                self.report_draft,
                overall_text="Zweite finale Berichtsfassung.",
            )
        )
        self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        real_service = self.adapter._report_revision_application_service()
        histories = real_service.revision_histories_for_student(
            self.student.student_id
        )
        newest, previous = histories[0].revisions
        wrapped_service = Mock(wraps=real_service)

        def verify(revision):  # type: ignore[no-untyped-def]
            if revision.learning_report_revision_id == (
                newest.learning_report_revision_id
            ):
                raise ValueError("defekte Einzelrevision")
            return real_service.verify_revision(revision)

        wrapped_service.verify_revision.side_effect = verify
        with patch.object(
            self.adapter,
            "_report_revision_application_service",
            return_value=wrapped_service,
        ):
            overview = self.adapter.report_overview_for_student(
                self.student.student_id,
                selected_report_draft_id=self.report_draft.report_draft_id,
            )

        report_event = next(
            event
            for event in overview.timeline_events
            if event.event_type == "report"
        )
        self.assertEqual(
            report_event.action.target_id,
            previous.learning_report_revision_id,
        )
        self.assertIn(
            f"report_revision_invalid:{self.report_draft.report_draft_id}",
            {warning.warning_key for warning in overview.projection_warnings},
        )

    def test_batch_reads_have_no_revision_n_plus_one_or_forbidden_sources(
        self,
    ) -> None:
        self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        self.report_draft = self.adapter.save_learning_report_draft(
            replace(
                self.report_draft,
                overall_text="Zweite Fassung für den Query-Test.",
            )
        )
        self.adapter.finalize_learning_report(
            self.report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        leg_draft = self.adapter.save_learning_conference_draft(
            self._learning_conference_draft()
        )
        self.adapter.complete_learning_conference(
            leg_draft.learning_conference_draft_id
        )
        leg_draft = self.adapter.save_learning_conference_draft(
            replace(
                leg_draft,
                agreed_agreements_text="Zweite Vereinbarung im Query-Test.",
            )
        )
        self.adapter.complete_learning_conference(
            leg_draft.learning_conference_draft_id
        )
        provider = _TracingConnectionProvider()
        traced_database = SQLiteDatabase(
            self.database_path,
            connection_provider=provider,
            create=False,
            initialize_schema=False,
        )

        report_histories = SQLiteLearningReportRepository(
            traced_database
        ).list_revision_histories_for_student(self.student.student_id)
        report_statements = tuple(provider.statements)
        provider.statements.clear()
        leg_histories = SQLiteLearningConferenceRepository(
            traced_database
        ).list_revision_histories_for_student(self.student.student_id)
        leg_statements = tuple(provider.statements)
        provider.statements.clear()
        live_batch = SQLiteStudentDocumentationProjectionRepository(
            traced_database
        ).read_batch(student_id=self.student.student_id)
        live_statements = tuple(provider.statements)

        self.assertEqual(len(report_histories), 1)
        self.assertEqual(len(leg_histories), 1)
        self.assertEqual(len(report_histories[0].revisions), 2)
        self.assertEqual(len(leg_histories[0].revisions), 2)
        self.assertEqual(
            sum(
                statement.lstrip().upper().startswith("SELECT")
                for statement in report_statements
            ),
            1,
        )
        self.assertEqual(
            sum(
                statement.lstrip().upper().startswith("SELECT")
                for statement in leg_statements
            ),
            1,
        )
        combined = "\n".join(
            (*report_statements, *leg_statements, *live_statements)
        ).lower()
        self.assertNotIn("orientation_changes", combined)
        self.assertEqual(
            tuple(item.student_id for item in live_batch.students),
            (self.student.student_id,),
        )

    def _observation(
        self,
        observation_id: str,
        observed_on: str,
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
        return ObservationRecord(
            observation_id,
            self.student.student_id,
            observed_on,
            self.competency.subject_id,
            "Lernzeit",
            "Vorhandener Beobachtungstext.",
            True,
            f"{observed_on}T10:00:00+00:00",
            f"{observed_on}T10:00:00+00:00",
            (rating,),
        )

    def _report_draft(self) -> LearningReportDraftViewModel:
        subject = LearningReportSubjectDraftViewModel(
            self.competency.subject_id,
            "Manueller Fachtext.",
            "Vorhandene Entwicklung.",
            "Vorhandene Unterstützung.",
            "Bewusster Ausblick.",
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
            overall_text="Manuell verfasster Gesamtblick.",
            subjects=(subject,),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(self.observation.observation_id,),
            chart_selections=charts,
        )

    def _learning_conference_draft(
        self,
    ) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            conference_date=date(2026, 7, 10),
            responsible_teacher="Laura Lernbegleiterin",
            conversation_entry_text="Interner Gesprächseinstieg",
            child_retrospective_text="Rückblick des Kindes",
            teacher_perspective_text="Interne Lehrkraftsicht",
            strengths_text="Interne Vorbereitung",
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
