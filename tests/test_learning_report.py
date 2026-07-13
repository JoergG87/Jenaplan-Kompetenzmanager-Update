"""Focused Sprint 7F checks for the productive learning report."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QButtonGroup, QCheckBox, QStackedWidget

from prototypes.pdf_engine.output_models import ChartBlock, ReportOutputModel, TableBlock
from prototypes.pdf_engine.renderer import PdfRenderer
from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportCompetencyViewModel,
    LearningReportChartSelectionViewModel,
    LearningReportDraft,
    LearningReportDraftViewModel,
    LearningReportEvidenceViewModel,
    LearningReportPreparationViewModel,
    LearningReportSubjectDraftViewModel,
    LearningReportSubjectViewModel,
    build_report_output_model,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


class LearningReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        evidence = LearningReportEvidenceViewModel(
            "OBS-000001",
            date(2026, 3, 12),
            "Mathematik",
            "Lernzeit",
            "Uhrzeit passend eingestellt.",
            ("CMP-000001",),
        )
        current = LearningReportCompetencyViewModel(
            "CMP-000001",
            "math",
            "Mathematik",
            "Größen und Messen",
            "Zeit",
            "Volle Stunden ablesen",
            "observed_unconfirmed",
            False,
            True,
            ((date(2026, 3, 12), "+"),),
        )
        historical = LearningReportCompetencyViewModel(
            "CMP-OLD",
            "math",
            "Mathematik",
            "Größen und Messen",
            "Zeit",
            "Historische Sammelkompetenz Zeit",
            "observed_unconfirmed",
            True,
            False,
            ((date(2025, 9, 1), "-"),),
        )
        german = LearningReportCompetencyViewModel(
            "CMP-000002",
            "german",
            "Deutsch",
            "Lesen",
            "Sachtexte",
            "Informationen auffinden",
            "undocumented",
            False,
            True,
            (),
        )
        self.preparation = LearningReportPreparationViewModel(
            "STU-000001",
            "Mara Beispielkind",
            "Sonnenbogen",
            (
                LearningReportSubjectViewModel("german", "Deutsch", (german,), ()),
                LearningReportSubjectViewModel(
                    "math", "Mathematik", (current, historical), (evidence,)
                ),
            ),
        )

    def test_report_starts_from_student_profile(self) -> None:
        screen = StudentProfileScreen()
        student = StudentDetailViewModel(
            "STU-000001", "Mara Beispielkind", "Sonnenbogen", "Kurs 1", "", True
        )
        screen.set_student(student)
        requested: list[str] = []
        screen.report_requested.connect(requested.append)

        screen.report_create_button.click()

        self.assertEqual(requested, ["STU-000001"])

    def test_workspace_uses_prototype_mode_and_section_navigation(self) -> None:
        dialog = LearningReportDialog(self.preparation)

        self.assertEqual(len(dialog.findChildren(QStackedWidget)), 2)
        self.assertEqual(len(dialog.findChildren(QButtonGroup)), 2)
        self.assertEqual(dialog.edit_mode_button.text(), "✎  Bericht bearbeiten")
        self.assertEqual(dialog.preview_mode_button.text(), "▤  Berichtsvorschau")
        self.assertEqual(
            [button.text() for button in dialog.navigation_group.buttons()],
            ["Dokument & Gesamtblick", "Deutsch", "Mathematik", "Abschluss"],
        )

    def test_subject_filter_preserves_selection_and_historical_visibility(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        widgets = dialog.subject_widgets["math"]
        include = widgets["include"]
        tree = widgets["tree"]
        self.assertIsInstance(include, QCheckBox)
        include.setChecked(True)
        root = tree.topLevelItem(0)
        area = root.child(0)
        topic = area.child(0)
        current_item = topic.child(0)

        current_item.setCheckState(0, Qt.CheckState.Checked)
        dialog.editor_stack.setCurrentIndex(1)
        dialog.editor_stack.setCurrentIndex(2)
        root = tree.topLevelItem(0)
        area = root.child(0)
        topic = area.child(0)
        historical_item = topic.child(1)

        self.assertIn("math", dialog.selected_subject_ids)
        self.assertIn("CMP-000001", dialog.selected_competency_ids)
        self.assertIn("historisch", historical_item.text(0))
        self.assertFalse(bool(historical_item.flags() & Qt.ItemFlag.ItemIsEnabled))

    def test_observation_selection_is_deliberate(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        widgets = dialog.subject_widgets["math"]
        widgets["include"].setChecked(True)
        root = widgets["tree"].topLevelItem(0)
        current_item = root.child(0).child(0).child(0)
        current_item.setCheckState(0, Qt.CheckState.Checked)
        check = next(
            widget
            for widget in widgets["evidence_container"].findChildren(QCheckBox)
            if "12.03.2026" in widget.text()
        )

        self.assertNotIn("OBS-000001", dialog.selected_observation_ids)
        check.setChecked(True)

        self.assertIn("OBS-000001", dialog.selected_observation_ids)

    def test_output_model_contains_only_deliberate_choices(self) -> None:
        draft = self._draft()

        output = build_report_output_model(self.preparation, draft)

        self.assertIsInstance(output, ReportOutputModel)
        self.assertEqual(output.metadata.document_title, "Lernentwicklungsbericht")
        self.assertEqual(output.metadata.teacher_name, "Laura Lernbegleiterin")
        self.assertEqual([page.label for page in output.pages].count("Mathematik"), 1)
        self.assertNotIn("Deutsch", [page.label for page in output.pages])
        subject_table = next(
            block for block in output.pages[2].blocks if isinstance(block, TableBlock)
        )
        self.assertEqual(subject_table.rows[0][2], "Volle Stunden ablesen")
        self.assertNotIn("Historische Sammelkompetenz Zeit", str(subject_table.rows))

    def test_saved_draft_loads_and_emits_complete_manual_state(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            teacher_name="Laura Lernbegleiterin",
            overall_text="Gespeicherter Gesamtblick.",
            subjects=(
                LearningReportSubjectDraftViewModel(
                    "math",
                    "Gespeicherte Stärke.",
                    "Gespeicherte Entwicklung.",
                    "Gespeicherter Unterstützungsbedarf.",
                    "Gespeichertes Ziel.",
                ),
            ),
            competency_ids=("CMP-000001",),
            observation_ids=("OBS-000001",),
            chart_selections=(
                LearningReportChartSelectionViewModel(
                    "math", "documentation_coverage"
                ),
            ),
            report_draft_id="RPD-000001",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        texts = dialog.subject_widgets["math"]["texts"]

        self.assertEqual(dialog.teacher_input.text(), "Laura Lernbegleiterin")
        self.assertEqual(dialog.overall_input.toPlainText(), "Gespeicherter Gesamtblick.")
        self.assertEqual(texts["strengths"].toPlainText(), "Gespeicherte Stärke.")
        self.assertIn("CMP-000001", dialog.selected_competency_ids)
        self.assertIn("OBS-000001", dialog.selected_observation_ids)

        texts["development"].setPlainText("Bearbeitete Entwicklung.")
        emitted: list[LearningReportDraftViewModel] = []
        dialog.save_requested.connect(emitted.append)
        dialog.save_button.click()

        self.assertEqual(emitted[0].report_draft_id, "RPD-000001")
        self.assertEqual(
            emitted[0].subjects[0].development_text, "Bearbeitete Entwicklung."
        )

    def test_only_selected_allowed_charts_reach_output_model(self) -> None:
        draft = self._draft()
        draft = LearningReportDraft(
            **{
                **draft.__dict__,
                "chart_selections": (
                    LearningReportChartSelectionViewModel(
                        "math", "observation_timeline"
                    ),
                ),
            }
        )

        output = build_report_output_model(self.preparation, draft)
        chart_blocks = [
            block for block in output.pages[2].blocks if isinstance(block, ChartBlock)
        ]

        self.assertEqual(len(chart_blocks), 1)
        self.assertEqual(
            chart_blocks[0].data.title,
            "Zeitachse ausgewählter Beobachtungen",
        )

    def test_preview_pages_are_stacked_without_overlap(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show()
        self.app.processEvents()
        dialog._set_mode(1)
        self.app.processEvents()
        pages = [
            dialog.preview_layout.itemAt(index).widget()
            for index in range(dialog.preview_layout.count())
            if dialog.preview_layout.itemAt(index).widget() is not None
        ]

        self.assertGreaterEqual(pages[1].geometry().top(), pages[0].geometry().bottom())
        self.assertGreaterEqual(pages[2].geometry().top(), pages[1].geometry().bottom())
        dialog.close()

    def test_unchanged_pdf_engine_processes_output_model(self) -> None:
        draft = self._draft()
        draft = LearningReportDraft(
            **{
                **draft.__dict__,
                "subject_texts": (
                    LearningReportSubjectDraftViewModel(
                        "math",
                        "Manuelle Stärke.",
                        "Manuelle Lernentwicklung.",
                        "Manueller Unterstützungsbedarf.",
                        "Manuelles nächstes Ziel.",
                    ),
                ),
                "chart_selections": tuple(
                    LearningReportChartSelectionViewModel("math", chart_type)
                    for chart_type in (
                        "documentation_coverage",
                        "competency_timeline",
                        "observation_timeline",
                    )
                ),
            }
        )
        output = build_report_output_model(self.preparation, draft)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.pdf"

            rendered = PdfRenderer().render(output, target)

            self.assertEqual(rendered, target)
            self.assertGreater(target.stat().st_size, 1000)

    def _draft(self):
        from src.desktop_app.view_models.learning_report_view_model import LearningReportDraft

        return LearningReportDraft(
            date(2026, 1, 1),
            date(2026, 12, 31),
            "Laura Lernbegleiterin",
            "Manueller Gesamtblick.",
            "Ein manuell gesetztes Ziel.",
            "Ruhige Lernzeit anbieten.",
            ("math",),
            ("CMP-000001",),
            ("OBS-000001",),
        )


if __name__ == "__main__":
    unittest.main()
