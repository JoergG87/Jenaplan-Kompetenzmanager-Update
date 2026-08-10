"""Focused Sprint 7F checks for the productive learning report."""

from __future__ import annotations

import os
import tempfile
import unittest
import inspect
from datetime import date
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pypdf import PdfReader
from PySide6.QtCore import QDate, QEvent, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QWidget,
)

from prototypes.pdf_engine.output_models import ChartBlock, ReportOutputModel, TableBlock
from prototypes.pdf_engine.renderer import PdfRenderer
from src.desktop_app import shell
from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportDialog,
    LearningReportDraftSelectionDialog,
    LearningReportPeriodSelectionDialog,
)
from src.desktop_app.components import SegmentedControl
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
    build_selected_report_evidence,
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

    def test_shell_always_offers_existing_or_new_report_selection(self) -> None:
        source = inspect.getsource(shell.AppShell.open_learning_report_dialog)

        self.assertIn('elif len(drafts) == 1 and selected_ui == "qt":', source)
        self.assertIn("elif drafts:", source)
        self.assertIn("LearningReportDraftSelectionDialog.choose", source)
        self.assertIn("LearningReportPeriodSelectionDialog.choose", source)
        self.assertNotIn("drafts[0] if drafts else None", source)

    def test_new_report_period_selection_requires_explicit_valid_dates(self) -> None:
        dialog = LearningReportPeriodSelectionDialog()

        self.assertEqual(dialog.start_input.specialValueText(), "Bitte wählen")
        self.assertEqual(dialog.end_input.specialValueText(), "Bitte wählen")
        dialog._accept_selected_period()
        self.assertEqual(
            dialog.validation_message.text(),
            "Bitte wähle Beginn und Ende des Berichtszeitraums aus.",
        )
        dialog.start_input.setDate(QDate(2026, 2, 1))
        dialog.end_input.setDate(QDate(2026, 2, 1))
        dialog._accept_selected_period()
        self.assertEqual(
            dialog.validation_message.text(),
            "Das Ende des Berichtszeitraums muss nach dem Beginn liegen.",
        )
        dialog.end_input.setDate(QDate(2026, 7, 31))
        dialog._accept_selected_period()

        self.assertEqual(dialog.selected_period, (date(2026, 2, 1), date(2026, 7, 31)))
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

    def test_report_draft_selection_lists_periods_and_allows_new_or_cancel(self) -> None:
        first = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            teacher_name="Laura Lernbegleiterin",
            report_draft_id="RPD-000001",
        )
        second = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2025, 8, 1),
            period_end=date(2026, 1, 31),
            teacher_name="Mika Lernbegleiter",
            report_draft_id="RPD-000002",
        )
        dialog = LearningReportDraftSelectionDialog((first, second))
        labels = [label.text() for label in dialog.findChildren(QLabel)]
        buttons = [button.text() for button in dialog.findChildren(QPushButton)]

        self.assertIn("Zeitraum 01.01.2026 bis 31.07.2026", labels)
        self.assertIn("Zeitraum 01.08.2025 bis 31.01.2026", labels)
        self.assertEqual(labels.count("Status: Entwurf"), 2)
        self.assertEqual(buttons.count("Öffnen"), 2)
        self.assertIn("Neuer Entwurf", buttons)
        self.assertIn("Abbrechen", buttons)

        dialog._choose(second)
        self.assertEqual(dialog.selected_draft, second)
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

        new_dialog = LearningReportDraftSelectionDialog((first,))
        new_dialog._choose(None)
        new_dialog._choose(None)
        self.assertIsNone(new_dialog.selected_draft)
        self.assertEqual(new_dialog.result(), new_dialog.DialogCode.Accepted)

        cancelled = LearningReportDraftSelectionDialog((first,))
        cancelled.reject()
        self.assertIsNone(cancelled.selected_draft)
        self.assertEqual(cancelled.result(), cancelled.DialogCode.Rejected)

    def test_workspace_uses_four_calm_sections_and_subject_navigation(self) -> None:
        dialog = LearningReportDialog(self.preparation)

        self.assertEqual(len(dialog.findChildren(QStackedWidget)), 2)
        self.assertEqual(
            {key for key, built in dialog.workspace_built.items() if built},
            {"writing"},
        )
        self.assertFalse(any(dialog.editor_subject_built.values()))
        self.assertIsInstance(dialog.workspace_navigation, SegmentedControl)
        self.assertEqual(dialog.workspace_navigation.current_key(), "writing")
        self.assertEqual(
            [button.text() for button in dialog.navigation_group.buttons()],
            ["Gesamttext", "Deutsch", "Mathematik"],
        )
        navigation_buttons = dialog.workspace_navigation.findChildren(
            type(dialog.save_button)
        )
        self.assertEqual(
            [button.accessibleName() for button in navigation_buttons],
            ["Schreiben", "Kompetenzen & Belege", "Vorschau", "Revisionen"],
        )
        self.assertEqual(sum(button.isChecked() for button in navigation_buttons), 1)
        writing_button = navigation_buttons[0]
        writing_accessible = QAccessible.queryAccessibleInterface(writing_button)
        self.assertEqual(writing_accessible.role(), QAccessible.Role.CheckBox)
        self.assertTrue(writing_accessible.state().checked)
        self.assertEqual(writing_button.focusPolicy(), Qt.FocusPolicy.StrongFocus)

        QTest.keyClick(writing_button, Qt.Key.Key_Right)
        self.assertEqual(dialog.workspace_navigation.current_key(), "evidence")

        initial_draft = dialog.report_draft_view_model()
        for expected_index, key in enumerate(
            ("writing", "evidence", "preview", "revisions")
        ):
            dialog.workspace_navigation.set_current_key(key, emit=True)
            self.assertEqual(dialog.mode_stack.currentIndex(), expected_index)
            self.assertEqual(
                sum(button.isChecked() for button in navigation_buttons),
                1,
            )
            active = next(button for button in navigation_buttons if button.isChecked())
            self.assertEqual(
                active.accessibleName(),
                ("Schreiben", "Kompetenzen & Belege", "Vorschau", "Revisionen")[
                    expected_index
                ],
            )
            self.assertTrue(
                QAccessible.queryAccessibleInterface(active).state().checked
            )
        self.assertEqual(dialog.report_draft_view_model(), initial_draft)

    def test_lazy_workspaces_and_subjects_build_once_and_reuse_widgets(self) -> None:
        dialog = LearningReportDialog(self.preparation)

        for key in ("evidence", "preview", "revisions"):
            self.assertEqual(
                dialog.workspace_pages[key].findChildren(QWidget),
                [],
            )

        dialog._set_editor_section(2)
        math_text = dialog.subject_widgets["math"]["texts"]["strengths"]
        math_editor_children = len(
            dialog.editor_subject_pages["math"].findChildren(QWidget)
        )
        dialog._set_editor_section(0)
        dialog._set_editor_section(2)

        self.assertIs(
            dialog.subject_widgets["math"]["texts"]["strengths"],
            math_text,
        )
        self.assertEqual(
            len(dialog.editor_subject_pages["math"].findChildren(QWidget)),
            math_editor_children,
        )

        dialog.show_workspace("evidence")
        german_tree = dialog.subject_widgets["german"]["tree"]
        evidence_children = len(
            dialog.evidence_subject_pages["german"].findChildren(QWidget)
        )
        dialog.show_workspace("writing")
        dialog.show_workspace("evidence")

        self.assertIs(dialog.subject_widgets["german"]["tree"], german_tree)
        self.assertEqual(
            len(dialog.evidence_subject_pages["german"].findChildren(QWidget)),
            evidence_children,
        )

    def test_unopened_subjects_preserve_saved_texts_charts_and_references(self) -> None:
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

        current = dialog.report_draft_view_model()

        self.assertEqual(current, initial)
        self.assertFalse(any(dialog.editor_subject_built.values()))
        self.assertFalse(dialog.workspace_built["evidence"])
        self.assertFalse(dialog.workspace_built["preview"])

    def test_period_change_does_not_build_evidence_before_first_activation(self) -> None:
        dialog = LearningReportDialog(self.preparation)

        dialog.period_start.setDate(QDate(2026, 2, 1))
        self.app.processEvents()

        self.assertFalse(dialog.workspace_built["evidence"])
        self.assertFalse(any(dialog.evidence_subject_built.values()))
        dialog.show_workspace("evidence")
        self.assertTrue(dialog.evidence_subject_built["german"])
        self.assertEqual(dialog.period_start.date(), QDate(2026, 2, 1))

    def test_revision_summary_is_complete_without_opening_preview_and_stays_current(self) -> None:
        dialog = LearningReportDialog(self.preparation)

        dialog.show_workspace("revisions")

        self.assertEqual(
            dialog.closing_summary.text(),
            "0 Fachabschnitte · 0 Kompetenzen · 0 Beobachtungsbelege",
        )
        self.assertFalse(dialog.workspace_built["preview"])
        dialog.show_workspace("evidence")
        dialog.subject_widgets["german"]["include"].setChecked(True)
        self.assertEqual(
            dialog.closing_summary.text(),
            "1 Fachabschnitte · 0 Kompetenzen · 0 Beobachtungsbelege",
        )
        self.assertFalse(dialog.workspace_built["preview"])

    def test_twenty_report_open_close_cycles_leave_no_top_level_workspace(self) -> None:
        baseline_top_levels = len(QApplication.topLevelWidgets())

        for _ in range(20):
            dialog = LearningReportDialog(self.preparation)
            dialog.show()
            self.app.processEvents()
            dialog.close()
            dialog.deleteLater()
            self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
            self.assertNotIn(dialog, QApplication.topLevelWidgets())

        self.assertLessEqual(
            len(QApplication.topLevelWidgets()),
            baseline_top_levels,
        )

    def test_writing_and_evidence_are_visually_separate_but_keep_shared_state(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog._set_editor_section(1)
        dialog.show_workspace("evidence")
        german = dialog.subject_widgets["german"]

        self.assertIsInstance(german["texts"]["strengths"], QTextEdit)
        self.assertIsInstance(german["tree"], QTreeWidget)
        self.assertEqual(
            german["texts"]["strengths"].accessibleName(),
            "Stärken im Fach Deutsch",
        )
        self.assertEqual(
            german["tree"].accessibleName(),
            "Kompetenzauswahl für Deutsch",
        )
        self.assertIn(
            german["texts"]["strengths"],
            dialog.editor_stack.widget(1).findChildren(QTextEdit),
        )
        self.assertIn(
            german["tree"],
            dialog.evidence_stack.widget(0).findChildren(QTreeWidget),
        )

    def test_preview_is_explicitly_draft_and_reports_unsaved_source_state(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.overall_input.setPlainText("Noch nicht gespeicherter Text")
        dialog.show_workspace("preview")

        self.assertIn("Vorschau des aktuellen Entwurfs", dialog.preview_status.text())
        self.assertIn("noch nicht gespeicherte Änderungen", dialog.preview_status.text())
        self.assertEqual(dialog.draft_status.text(), "Ungespeicherte Änderungen")

    def test_unsaved_close_actions_keep_complete_macos_button_text(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.overall_input.setPlainText("Ungespeicherter Teststand")
        captured: dict[str, object] = {}

        def inspect_confirmation(message: QMessageBox) -> int:
            buttons = {
                button.text(): button
                for button in message.buttons()
                if isinstance(button, QPushButton)
            }
            discard = buttons["Änderungen verwerfen"]
            keep = buttons["Weiter bearbeiten"]
            captured.update(discard=discard, keep=keep)
            self.assertGreaterEqual(
                discard.minimumWidth(),
                discard.fontMetrics().horizontalAdvance(discard.text()) + 40,
            )
            self.assertGreaterEqual(
                keep.minimumWidth(),
                keep.fontMetrics().horizontalAdvance(keep.text()) + 40,
            )
            self.assertEqual(keep.property("buttonRole"), "primary")
            self.assertTrue(keep.isDefault())
            self.assertIs(message.escapeButton(), keep)
            return int(QMessageBox.DialogCode.Rejected)

        with mock.patch.object(QMessageBox, "exec", new=inspect_confirmation):
            dialog.reject()

        self.assertEqual(set(captured), {"discard", "keep"})

    def test_subject_filter_preserves_selection_and_historical_visibility(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
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
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
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

    def test_preview_and_pdf_keep_all_selected_evidence_once_in_identical_order(
        self,
    ) -> None:
        long_note = (
            "LANGER-BELEG vollständig erhalten. "
            + "Die Beobachtung beschreibt eine längere konkrete Lernhandlung. " * 6
        )
        german_competency = self.preparation.subjects[0].competencies[0]
        math_competency = self.preparation.subjects[1].competencies[0]
        shared = LearningReportEvidenceViewModel(
            "OBS-SHARED",
            date(2026, 7, 13),
            "Fächerübergreifend",
            "Projekt",
            "GETEILTER-BELEG",
            (german_competency.competency_id, math_competency.competency_id),
        )
        german_evidence = (
            LearningReportEvidenceViewModel(
                "OBS-DE-2",
                date(2026, 7, 14),
                "Deutsch",
                "Lesekreis",
                "DEUTSCH-ZWEI",
                (german_competency.competency_id,),
            ),
            shared,
            LearningReportEvidenceViewModel(
                "OBS-DE-1",
                date(2026, 7, 12),
                "Deutsch",
                "Sachtext",
                long_note,
                (german_competency.competency_id,),
            ),
        )
        math_evidence = (
            shared,
            LearningReportEvidenceViewModel(
                "OBS-MA-2",
                date(2026, 7, 11),
                "Mathematik",
                "Lernzeit",
                "",
                (math_competency.competency_id,),
            ),
            LearningReportEvidenceViewModel(
                "OBS-MA-1",
                date(2026, 6, 22),
                "Mathematik",
                "Präsentation",
                "MATHE-EINS",
                (math_competency.competency_id,),
            ),
            LearningReportEvidenceViewModel(
                "OBS-NOT-SELECTED",
                date(2026, 6, 20),
                "Mathematik",
                "Nicht gewählt",
                "NICHT-AUSGEWÄHLT",
                (math_competency.competency_id,),
            ),
        )
        preparation = LearningReportPreparationViewModel(
            self.preparation.student_id,
            self.preparation.student_name,
            self.preparation.group_name,
            (
                LearningReportSubjectViewModel(
                    "german",
                    "Deutsch",
                    (german_competency,),
                    german_evidence,
                ),
                LearningReportSubjectViewModel(
                    "math",
                    "Mathematik",
                    (math_competency,),
                    math_evidence,
                ),
            ),
        )
        selected_ids = (
            "OBS-DE-1",
            "OBS-DE-2",
            "OBS-SHARED",
            "OBS-MA-1",
            "OBS-MA-2",
        )
        draft = LearningReportDraft(
            date(2025, 8, 1),
            date(2026, 1, 31),
            "Laura Lernbegleiterin",
            "Manueller Gesamtblick.",
            "",
            "",
            ("german", "math"),
            (),
            selected_ids,
        )

        projection = build_selected_report_evidence(preparation, draft)
        output = build_report_output_model(preparation, draft)
        evidence_rows = tuple(
            row
            for page in output.pages
            for block in page.blocks
            if isinstance(block, TableBlock)
            and block.headers == ("Datum", "Kontext", "Notiz")
            for row in block.rows
        )
        initial = LearningReportDraftViewModel(
            student_id=preparation.student_id,
            period_start=draft.period_start,
            period_end=draft.period_end,
            subjects=(
                LearningReportSubjectDraftViewModel("german"),
                LearningReportSubjectDraftViewModel("math"),
            ),
            observation_ids=selected_ids,
            report_draft_id="RPD-EVIDENCE-TEST",
        )
        dialog = LearningReportDialog(preparation, initial_draft=initial)
        dialog.show_workspace("preview")
        preview_text = "\n".join(
            label.text() for label in dialog.findChildren(QLabel)
        )

        self.assertEqual(
            tuple(item.evidence.observation_id for item in projection),
            ("OBS-DE-2", "OBS-SHARED", "OBS-DE-1", "OBS-MA-2", "OBS-MA-1"),
        )
        self.assertEqual(
            tuple(row[2] for row in evidence_rows),
            (
                "DEUTSCH-ZWEI",
                "GETEILTER-BELEG",
                long_note,
                "Keine Notiz",
                "MATHE-EINS",
            ),
        )
        expected_preview_order = (
            preview_text.index("DEUTSCH-ZWEI"),
            preview_text.index("GETEILTER-BELEG"),
            preview_text.index("LANGER-BELEG"),
            preview_text.index("Keine Notiz"),
            preview_text.index("MATHE-EINS"),
        )
        self.assertEqual(expected_preview_order, tuple(sorted(expected_preview_order)))

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "five-selected-evidence.pdf"
            PdfRenderer().render(output, target)
            pdf_text = "\n".join(
                page.extract_text() or "" for page in PdfReader(target).pages
            )

        for marker in (
            "DEUTSCH-ZWEI",
            "GETEILTER-BELEG",
            "LANGER-BELEG",
            "MATHE-EINS",
        ):
            self.assertEqual(pdf_text.count(marker), 1)
        self.assertNotIn("NICHT-AUSGEWÄHLT", pdf_text)

    def test_retained_historical_competency_is_visible_selected_and_removable(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=("CMP-OLD",),
            report_draft_id="RPD-000001",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        tree = dialog.subject_widgets["math"]["tree"]
        retained_item = next(
            item
            for item in self._competency_items(tree)
            if item.data(0, Qt.ItemDataRole.UserRole) == "CMP-OLD"
        )

        self.assertEqual(retained_item.checkState(0), Qt.CheckState.Checked)
        self.assertIn("nicht mehr regulär verfügbar", retained_item.text(0))
        retained_item.setCheckState(0, Qt.CheckState.Unchecked)

        self.assertNotIn("CMP-OLD", dialog.selected_competency_ids)
        self.assertFalse(bool(retained_item.flags() & Qt.ItemFlag.ItemIsEnabled))

    def test_unavailable_evidence_survives_view_and_period_changes_until_unchecked(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=("CMP-000001",),
            observation_ids=("OBS-MISSING",),
            report_draft_id="RPD-000001",
            unavailable_observation_ids=("OBS-MISSING",),
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        unavailable_check = next(
            check
            for check in dialog.findChildren(QCheckBox)
            if check.objectName() == "LearningReportUnavailableEvidence_OBS-MISSING"
        )

        dialog.editor_stack.setCurrentIndex(1)
        dialog.editor_stack.setCurrentIndex(0)
        dialog.period_start.setDate(date(2026, 2, 1))
        self.app.processEvents()

        self.assertIn("OBS-MISSING", dialog.selected_observation_ids)
        self.assertTrue(unavailable_check.isChecked())
        unavailable_check.setChecked(False)
        self.assertNotIn("OBS-MISSING", dialog.report_draft_view_model().observation_ids)

    def test_preview_and_output_model_show_unavailable_saved_references(self) -> None:
        draft = LearningReportDraft(
            date(2026, 1, 1),
            date(2026, 12, 31),
            "Laura Lernbegleiterin",
            "Manueller Gesamtblick.",
            "",
            "",
            ("math",),
            ("CMP-OLD",),
            ("OBS-MISSING",),
            unavailable_observation_ids=("OBS-MISSING",),
        )

        output = build_report_output_model(self.preparation, draft)
        subject_table = next(
            block for block in output.pages[2].blocks if isinstance(block, TableBlock)
        )
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=draft.period_start,
            period_end=draft.period_end,
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=draft.selected_competency_ids,
            observation_ids=draft.selected_observation_ids,
            unavailable_observation_ids=draft.unavailable_observation_ids,
            report_draft_id="RPD-000001",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.show_workspace("preview")
        preview_text = " ".join(
            label.text() for label in dialog.findChildren(QLabel)
        )
        output_text = " ".join(
            block.text
            for block in output.pages[-1].blocks
            if hasattr(block, "text")
        )

        self.assertIn("historisch ausgewählt", str(subject_table.rows))
        self.assertIn("1 bewusst ausgewählte Beobachtungsbeleg", output_text)
        self.assertNotIn("OBS-MISSING", output_text)
        self.assertIn(
            "Gespeicherter Beobachtungsbeleg 1 · nicht mehr verfügbar",
            preview_text,
        )
        self.assertNotIn("OBS-MISSING", preview_text)

    def test_unresolved_selected_evidence_fails_controlled_without_export(self) -> None:
        draft = LearningReportDraft(
            date(2026, 1, 1),
            date(2026, 12, 31),
            "Laura Lernbegleiterin",
            "Manueller Gesamtblick.",
            "",
            "",
            ("math",),
            (),
            ("OBS-UNRESOLVED",),
        )

        with self.assertRaisesRegex(
            ValueError,
            "nicht vollständig.*aufgelöst",
        ):
            build_report_output_model(self.preparation, draft)

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
        dialog._set_editor_section(2)
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
        dialog._set_mode(2)
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

    @staticmethod
    def _competency_items(tree):
        from PySide6.QtWidgets import QTreeWidgetItemIterator

        iterator = QTreeWidgetItemIterator(tree)
        items = []
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole):
                items.append(item)
            iterator += 1
        return items


if __name__ == "__main__":
    unittest.main()
