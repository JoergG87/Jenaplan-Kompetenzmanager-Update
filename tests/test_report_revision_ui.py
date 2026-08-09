"""Focused Sprint 5B.3 tests for report finalization and revision reads."""

from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
)

from src.core.learning_report import ReportFinalizationError
from src.core.observation import ObservationCompetencyRatingRecord, ObservationRecord
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteObservationRepository,
    create_sqlite_seed_database,
    SQLiteLearningReportRepository,
)
from src.core.learning_report import LearningReportRevisionReadService
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportDialog,
    LearningReportRevisionDialog,
)
from src.desktop_app.motion import set_reduced_motion
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportChartSelectionViewModel,
    LearningReportDraftViewModel,
    LearningReportSubjectDraftViewModel,
)


class ReportRevisionProductTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._revision_dialogs: list[LearningReportRevisionDialog] = []
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "report-revision-ui.sqlite"
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
        self.observation = ObservationRecord(
            "OBS-REVISION-UI",
            self.student.student_id,
            "2026-03-12",
            self.competency.subject_id,
            "Lernzeit",
            "Historisch einzufrierender Beobachtungsbeleg.",
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
        SQLiteObservationRepository(self.adapter.database).create_observation(
            self.observation
        )
        self.saved = self.adapter.save_learning_report_draft(self._draft())

    def tearDown(self) -> None:
        try:
            for dialog in self._revision_dialogs:
                dialog.close()
                dialog.deleteLater()
            QCoreApplication.sendPostedEvents(
                None,
                QEvent.Type.DeferredDelete,
            )
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
            top_level_widgets = QApplication.topLevelWidgets()
            self.assertFalse(
                any(
                    widget is dialog
                    for dialog in self._revision_dialogs
                    for widget in top_level_widgets
                )
            )
        finally:
            self.temp_dir.cleanup()

    def _revision_dialog(self, revision: object) -> LearningReportRevisionDialog:
        dialog = LearningReportRevisionDialog(revision)
        self._revision_dialogs.append(dialog)
        return dialog

    def test_report_teacher_and_period_fields_use_separate_grid_rows(self) -> None:
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        dialog = LearningReportDialog(preparation, initial_draft=self.saved)
        self._revision_dialogs.append(dialog)
        teacher_field = dialog.teacher_input.parentWidget()
        period_start_field = dialog.period_start.parentWidget()
        period_end_field = dialog.period_end.parentWidget()
        context_layout = teacher_field.parentWidget().layout()

        self.assertEqual(
            context_layout.getItemPosition(context_layout.indexOf(teacher_field)),
            (3, 0, 1, 2),
        )
        self.assertEqual(
            context_layout.getItemPosition(context_layout.indexOf(period_start_field)),
            (4, 0, 1, 1),
        )
        self.assertEqual(
            context_layout.getItemPosition(context_layout.indexOf(period_end_field)),
            (4, 1, 1, 1),
        )

    def test_current_revision_action_uses_central_secondary_button_contract(
        self,
    ) -> None:
        status = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        dialog = LearningReportDialog(
            preparation,
            initial_draft=self.saved,
            revision_status=status,
        )
        self._revision_dialogs.append(dialog)
        dialog.show_workspace("revisions")
        button = dialog.findChild(
            QPushButton,
            "LearningReportOpenCurrentRevisionButton",
        )

        self.assertIsNotNone(button)
        self.assertEqual(button.text(), "Finale Fassung öffnen")
        self.assertEqual(button.property("buttonRole"), "secondary")

    def test_status_without_and_with_current_revision(self) -> None:
        empty = self.adapter.learning_report_revision_status(
            self.saved.report_draft_id
        )
        self.assertEqual(empty.state, "not_finalized")
        self.assertEqual(empty.badge_text, "Entwurf")
        self.assertFalse(empty.history)

        finalized = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )

        self.assertEqual(finalized.state, "finalized")
        self.assertEqual(finalized.badge_text, "Finalisiert · Revision 1")
        self.assertEqual(finalized.current_revision_number, 1)
        self.assertTrue(finalized.snapshot_hash_valid)

    def test_unchanged_and_changed_draft_are_compared_centrally(self) -> None:
        self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        unchanged = self.adapter.learning_report_revision_status(
            self.saved.report_draft_id
        )

        self.saved = self.adapter.save_learning_report_draft(
            replace(self.saved, overall_text="Bewusst korrigierter Gesamtblick.")
        )
        changed = self.adapter.learning_report_revision_status(
            self.saved.report_draft_id
        )

        self.assertEqual(unchanged.state, "finalized")
        self.assertEqual(changed.state, "draft_changed")
        self.assertEqual(changed.badge_text, "Entwurf geändert")

    def test_first_and_followup_finalization_use_adapter_and_newest_first_history(self) -> None:
        first = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        self.saved = self.adapter.save_learning_report_draft(
            replace(self.saved, overall_text="Revision zwei.")
        )
        second = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )

        self.assertEqual(first.current_revision_number, 1)
        self.assertEqual(second.current_revision_number, 2)
        self.assertEqual(
            [item.revision_number for item in second.history],
            [2, 1],
        )
        self.assertEqual(
            [item.status_label for item in second.history],
            ["Aktuell", "Ersetzt"],
        )
        current_view = self.adapter.load_learning_report_revision(
            second.history[0].learning_report_revision_id
        )
        replaced_view = self.adapter.load_learning_report_revision(
            second.history[1].learning_report_revision_id
        )
        self.assertEqual(current_view.status_label, "Aktuell")
        self.assertEqual(replaced_view.status_label, "Ersetzt")

    def test_read_service_exposes_aggregate_current_history_and_single_revision(self) -> None:
        status = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        service = LearningReportRevisionReadService(
            SQLiteLearningReportRepository(self.adapter.database)
        )

        report = service.report_for_draft(self.saved.report_draft_id)
        current = service.current_revision_for_draft(self.saved.report_draft_id)
        history = service.revision_history_for_draft(self.saved.report_draft_id)
        single = service.revision_by_id(status.current_revision_id)

        self.assertEqual(report.source_report_draft_id, self.saved.report_draft_id)
        self.assertEqual(current, single)
        self.assertEqual(history, (single,))
        self.assertTrue(service.snapshot_hash_valid(single))

    def test_responsible_display_name_is_required(self) -> None:
        with self.assertRaises(ReportFinalizationError):
            self.adapter.finalize_learning_report(
                self.saved.report_draft_id,
                "   ",
            )
        status = self.adapter.learning_report_revision_status(
            self.saved.report_draft_id
        )
        self.assertEqual(status.state, "not_finalized")

    def test_confirmation_contains_context_and_requires_explicit_acknowledgement(self) -> None:
        preview = self.adapter.prepare_learning_report_finalization(
            self.saved.report_draft_id
        )
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        dialog = LearningReportDialog(preparation, initial_draft=self.saved)
        confirmation = dialog.create_finalization_confirmation(preview)
        text = " ".join(
            label.text() for label in confirmation.findChildren(QPushButton)
        )
        all_text = " ".join(
            [label.text() for label in confirmation.findChildren(QLabel)]
            + [button.text() for button in confirmation.findChildren(QPushButton)]
            + [check.text() for check in confirmation.findChildren(QCheckBox)]
        )
        confirm = confirmation.findChild(
            QPushButton,
            "LearningReportFinalizationConfirmButton",
        )
        responsible = confirmation.findChild(
            QLineEdit,
            "LearningReportFinalizedByInput",
        )
        acknowledge = confirmation.findChild(
            QCheckBox,
            "LearningReportFinalizationAcknowledgement",
        )

        self.assertIn("Bericht finalisieren", text)
        self.assertIn("Revision", all_text)
        self.assertIn("Kind", all_text)
        self.assertIn("Berichtstyp", all_text)
        self.assertIn("Zeitraum", all_text)
        self.assertIn("Fächer", all_text)
        self.assertIn("Kompetenzen", all_text)
        self.assertIn("Beobachtungen", all_text)
        self.assertEqual(
            responsible.accessibleName(),
            "Verantwortliche Lehrkraft für die neue Revision",
        )
        self.assertIn("unveränderliche Revision", acknowledge.text())
        self.assertFalse(confirm.isEnabled())
        acknowledge.setChecked(True)
        self.assertTrue(confirm.isEnabled())
        responsible.clear()
        self.assertFalse(confirm.isEnabled())

    def test_validation_errors_are_projected_without_storage_terms(self) -> None:
        invalid = self.adapter.save_learning_report_draft(
            replace(
                self.saved,
                overall_text="",
                subjects=(LearningReportSubjectDraftViewModel(self.competency.subject_id),),
            )
        )
        with self.assertRaises(ReportFinalizationError) as caught:
            self.adapter.prepare_learning_report_finalization(
                invalid.report_draft_id
            )
        visible = self.adapter.learning_report_finalization_error_message(
            caught.exception
        )

        self.assertIn("bewusst verfassten Berichtstext", visible)
        self.assertNotIn("report_drafts", visible)
        self.assertNotIn("SQLite", visible)

    def test_changed_period_is_blocked_with_new_draft_guidance(self) -> None:
        self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        self.saved = self.adapter.save_learning_report_draft(
            replace(self.saved, period_start=date(2026, 2, 1))
        )
        with self.assertRaises(ReportFinalizationError) as caught:
            self.adapter.prepare_learning_report_finalization(
                self.saved.report_draft_id
            )
        visible = self.adapter.learning_report_finalization_error_message(
            caught.exception
        )

        self.assertIn(
            "Für einen anderen Berichtstyp oder Zeitraum muss ein neuer "
            "Berichtsentwurf angelegt werden.",
            visible,
        )

    def test_final_view_is_snapshot_only_after_all_live_sources_change(self) -> None:
        status = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        revision_id = status.current_revision_id
        before = self.adapter.load_learning_report_revision(revision_id)
        with self.adapter.database.connect() as connection:
            connection.execute(
                "UPDATE students SET first_name = 'Neu' WHERE student_id = ?",
                (self.student.student_id,),
            )
            connection.execute(
                "UPDATE groups SET group_name = 'Neue Gruppe' WHERE group_id = ?",
                (self.student.group_id,),
            )
            connection.execute(
                "UPDATE competencies SET description = 'Neuer Kompetenztext', active = 0 WHERE competency_id = ?",
                (self.competency.competency_id,),
            )
            connection.execute(
                "UPDATE observations SET note = 'Neuer Beleg', active = 0 WHERE observation_id = ?",
                (self.observation.observation_id,),
            )
            connection.commit()

        after = self.adapter.load_learning_report_revision(revision_id)

        self.assertEqual(after, before)
        self.assertEqual(after.student_display_name, self.student.display_name)
        self.assertEqual(
            after.subjects[0].observations[0].content,
            "Historisch einzufrierender Beobachtungsbeleg.",
        )
        self.assertEqual(
            after.subjects[0].competencies[0].competency_text,
            self.competency.description,
        )
        self.assertTrue(after.subjects[0].charts)
        self.assertTrue(
            any(chart.details for chart in after.subjects[0].charts)
        )

    def test_final_view_has_only_final_pdf_and_back_actions(self) -> None:
        status = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        revision = self.adapter.load_learning_report_revision(
            status.current_revision_id
        )
        dialog = self._revision_dialog(revision)
        actions = {button.text() for button in dialog.findChildren(QPushButton)}

        self.assertFalse(dialog.findChildren(QLineEdit))
        self.assertFalse(dialog.findChildren(QTextEdit))
        self.assertEqual(actions, {"Finales PDF erstellen", "Zurück"})
        self.assertFalse(
            {"Bearbeiten", "Löschen", "Entsperren", "Wiederherstellen"}
            & actions
        )
        requested: list[str] = []
        dialog.pdf_requested.connect(requested.append)
        QTest.mouseClick(
            dialog.findChild(QPushButton, "LearningReportGenerateFinalPdfButton"),
            Qt.MouseButton.LeftButton,
        )
        self.assertEqual(requested, [status.current_revision_id])

    def test_superseded_revision_has_no_final_pdf_action(self) -> None:
        first = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        first_revision_id = first.current_revision_id
        self.saved = self.adapter.save_learning_report_draft(
            replace(self.saved, overall_text="Bewusst korrigierte zweite Revision.")
        )
        self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )

        revision = self.adapter.load_learning_report_revision(first_revision_id)
        dialog = self._revision_dialog(revision)
        actions = {button.text() for button in dialog.findChildren(QPushButton)}

        self.assertEqual(actions, {"Zurück"})

    def test_finalization_does_not_emit_pdf_request(self) -> None:
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        dialog = LearningReportDialog(preparation, initial_draft=self.saved)
        requested: list[object] = []
        dialog.pdf_requested.connect(requested.append)

        self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )

        self.assertEqual(requested, [])

    def test_workspace_and_revision_view_support_target_sizes_and_reduced_motion(self) -> None:
        status = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        revision = self.adapter.load_learning_report_revision(
            status.current_revision_id
        )
        set_reduced_motion(True)
        workspace = LearningReportDialog(
            preparation,
            initial_draft=self.saved,
            revision_status=status,
        )
        final_view = self._revision_dialog(revision)
        try:
            for width, height in ((1400, 900), (1280, 800), (1180, 760)):
                workspace.resize(width, height)
                workspace.show()
                final_view.resize(width, height)
                final_view.show()
                self.app.processEvents()
                self.assertTrue(workspace.isVisible())
                self.assertTrue(final_view.isVisible())
                self.assertGreater(workspace.width(), 0)
                self.assertGreater(final_view.height(), 0)
        finally:
            workspace.close()
            final_view.close()
            set_reduced_motion(False)

    def test_workspace_header_exposes_student_context_and_all_revision_states(self) -> None:
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        draft_dialog = LearningReportDialog(
            preparation,
            initial_draft=self.saved,
            revision_status=self.adapter.learning_report_revision_status(
                self.saved.report_draft_id
            ),
        )
        self.assertIn(self.student.display_name, draft_dialog.page_header.title_label.text())
        self.assertIn(self.student.group_name, draft_dialog.header_context.text())
        self.assertIn("Laura Lernbegleiterin", draft_dialog.header_context.text())
        self.assertEqual(draft_dialog.header_status_badge.text(), "Entwurf")
        self.assertEqual(
            draft_dialog.header_revision_context.text(),
            "Noch keine finale Revision",
        )

        finalized = self.adapter.finalize_learning_report(
            self.saved.report_draft_id,
            "Laura Lernbegleiterin",
        )
        finalized_dialog = LearningReportDialog(
            preparation,
            initial_draft=self.saved,
            revision_status=finalized,
        )
        self.assertEqual(
            finalized_dialog.header_status_badge.text(),
            "Finalisiert · Revision 1",
        )
        self.assertIn("Revision 1", finalized_dialog.header_revision_context.text())

        self.saved = self.adapter.save_learning_report_draft(
            replace(self.saved, overall_text="Bewusst geänderter Entwurf.")
        )
        changed = self.adapter.learning_report_revision_status(
            self.saved.report_draft_id
        )
        changed_dialog = LearningReportDialog(
            preparation,
            initial_draft=self.saved,
            revision_status=changed,
        )
        changed_dialog.show_workspace("revisions")
        self.assertEqual(changed_dialog.header_status_badge.text(), "Entwurf geändert")
        visible_hints = " ".join(
            label.text() for label in changed_dialog.findChildren(QLabel)
        )
        self.assertIn("Die vorhandene Revision bleibt unverändert", visible_hints)

    def test_workspace_actions_have_accessible_names_and_one_finalization_action(self) -> None:
        preparation = self.adapter.learning_report_preparation_for_student(
            self.student.student_id,
            period_end=self.saved.period_end,
            retained_competency_ids=self.saved.competency_ids,
        )
        dialog = LearningReportDialog(
            preparation,
            initial_draft=self.saved,
            revision_status=self.adapter.learning_report_revision_status(
                self.saved.report_draft_id
            ),
        )
        dialog.show_workspace("revisions")
        buttons = dialog.findChildren(QPushButton)
        finalization_buttons = [
            button for button in buttons if "finalisieren" in button.text().lower()
        ]

        self.assertEqual(dialog.save_button.accessibleName(), "Berichtsentwurf speichern")
        self.assertEqual(len(finalization_buttons), 1)
        self.assertTrue(dialog.workspace_navigation.accessibleName())

    def test_qt_report_dialog_does_not_reference_sqlite_or_repositories(self) -> None:
        source = inspect.getsource(
            __import__(
                "src.desktop_app.dialogs.learning_report_dialog",
                fromlist=["LearningReportDialog"],
            )
        )
        self.assertNotIn("sqlite3", source)
        self.assertNotIn("SQLiteLearningReportRepository", source)
        self.assertNotIn("PdfRenderer", source)
        self.assertNotIn("hashlib", source)
        self.assertNotIn("learning_report_pdf_artifacts", source)

    def _draft(self) -> LearningReportDraftViewModel:
        return LearningReportDraftViewModel(
            student_id=self.student.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            teacher_name="Laura Lernbegleiterin",
            overall_text="Manuell verfasster pädagogischer Gesamtblick.",
            subjects=(
                LearningReportSubjectDraftViewModel(
                    self.competency.subject_id,
                    "Sorgfältiges Arbeiten.",
                    "Zunehmend selbstständig.",
                    "Ruhige Zwischenschritte.",
                    "Lösungswege festhalten.",
                ),
            ),
            competency_ids=(self.competency.competency_id,),
            observation_ids=(self.observation.observation_id,),
            chart_selections=tuple(
                LearningReportChartSelectionViewModel(
                    self.competency.subject_id,
                    chart_type,
                )
                for chart_type in (
                    "documentation_coverage",
                    "competency_timeline",
                    "observation_timeline",
                )
            ),
        )


if __name__ == "__main__":
    unittest.main()
