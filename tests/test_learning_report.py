"""Focused Sprint 7F checks for the productive learning report."""

from __future__ import annotations

import os
import tempfile
import unittest
import inspect
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pypdf import PdfReader
from PySide6.QtCore import QDate, QEvent, QTimer, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QFrame,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItemIterator,
    QWidget,
)
from shiboken6 import isValid

from prototypes.pdf_engine.output_models import ChartBlock, ReportOutputModel, TableBlock
from prototypes.pdf_engine.renderer import PdfRenderer
from src.desktop_app import shell
from src.desktop_app.dialogs.learning_report_dialog import (
    LearningReportCloseDialog,
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
    build_learning_report_writing_evidence,
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

    @staticmethod
    def _competency_item(tree: QTreeWidget, competency_id: str):
        iterator = QTreeWidgetItemIterator(tree)
        while iterator.value() is not None:
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == competency_id:
                return item
            iterator += 1
        raise AssertionError(f"Competency item not found: {competency_id}")

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
        self.assertIn("retained_observation_ids=", source)
        self.assertNotIn("drafts[0] if drafts else None", source)

    def test_new_report_period_selection_requires_explicit_valid_dates(self) -> None:
        dialog = LearningReportPeriodSelectionDialog(
            initial_period=(date(2026, 8, 1), date(2027, 7, 31))
        )

        self.assertEqual(
            dialog.start_input.date().toPython(),
            date(2026, 8, 1),
        )
        self.assertEqual(
            dialog.end_input.date().toPython(),
            date(2027, 7, 31),
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

    def test_workspace_uses_three_human_tasks_and_keeps_internal_routes(self) -> None:
        dialog = LearningReportDialog(self.preparation)

        self.assertEqual(len(dialog.findChildren(QStackedWidget)), 3)
        self.assertEqual(
            {key for key, built in dialog.workspace_built.items() if built},
            {"writing", "evidence"},
        )
        self.assertTrue(dialog.evidence_subject_built["german"])
        self.assertFalse(dialog.evidence_subject_built["math"])
        self.assertFalse(any(dialog.editor_subject_built.values()))
        self.assertIsInstance(dialog.workspace_navigation, SegmentedControl)
        self.assertEqual(dialog.workspace_navigation.current_key(), "evidence")
        self.assertEqual(
            dialog.evidence_selection_summary.text(),
            "Noch kein Fach ausgewählt",
        )
        self.assertFalse(dialog.continue_to_writing_button.isEnabled())
        self.assertEqual(
            [button.text() for button in dialog.navigation_group.buttons()],
            ["Gesamttext"],
        )
        navigation_buttons = dialog.workspace_navigation.findChildren(
            type(dialog.save_button)
        )
        self.assertEqual(
            [button.accessibleName() for button in navigation_buttons],
            ["Auswählen", "Schreiben", "Prüfen & finalisieren"],
        )
        self.assertEqual(sum(button.isChecked() for button in navigation_buttons), 1)
        evidence_button = navigation_buttons[0]
        evidence_accessible = QAccessible.queryAccessibleInterface(evidence_button)
        self.assertEqual(evidence_accessible.role(), QAccessible.Role.CheckBox)
        self.assertTrue(evidence_accessible.state().checked)
        self.assertEqual(evidence_button.focusPolicy(), Qt.FocusPolicy.StrongFocus)

        QTest.keyClick(evidence_button, Qt.Key.Key_Right)
        self.assertEqual(dialog.workspace_navigation.current_key(), "writing")

        initial_draft = dialog.report_draft_view_model()
        for key, expected_index, expected_label in (
            ("evidence", 1, "Auswählen"),
            ("writing", 0, "Schreiben"),
            ("preview", 2, "Prüfen & finalisieren"),
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
                expected_label,
            )
            self.assertTrue(
                QAccessible.queryAccessibleInterface(active).state().checked
            )
        dialog.show_workspace("revisions")
        self.assertEqual(dialog.workspace_navigation.current_key(), "preview")
        self.assertEqual(dialog.mode_stack.currentIndex(), 3)
        self.assertEqual(dialog.report_draft_view_model(), initial_draft)

    def test_writing_evidence_context_is_visible_and_navigation_stays_read_only(
        self,
    ) -> None:
        initial = LearningReportDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=("CMP-000001",),
            observation_ids=("OBS-000001",),
            report_draft_id="RPD-WRITING-EVIDENCE",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)

        dialog._set_editor_section(2)
        card = dialog.findChild(QWidget, "LearningReportWritingEvidence_math")
        self.assertIsNotNone(card)
        if card is None:
            raise AssertionError("Expected writing evidence card")
        labels = [label.text() for label in card.findChildren(QLabel)]
        self.assertIn("Belege für diesen Bericht", labels)
        self.assertIn("1 Kompetenz · 1 Beobachtungsbeleg", labels)
        self.assertIn("Volle Stunden ablesen · 1 Beobachtung", labels)
        self.assertFalse(dialog._dirty)

        edit = card.findChild(QPushButton, "LearningReportEditEvidence_math")
        self.assertIsNotNone(edit)
        if edit is None:
            raise AssertionError("Expected edit-selection action")
        edit.click()

        self.assertEqual(dialog.workspace_navigation.current_key(), "evidence")
        self.assertTrue(dialog._evidence_subject_buttons["math"].isChecked())
        self.assertFalse(dialog._dirty)

    def test_writing_evidence_context_switches_subject_and_marks_unresolved_neutrally(
        self,
    ) -> None:
        initial = LearningReportDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(
                LearningReportSubjectDraftViewModel("german"),
                LearningReportSubjectDraftViewModel("math"),
            ),
            competency_ids=("CMP-000001",),
            observation_ids=("OBS-MISSING",),
            unavailable_observation_ids=("OBS-MISSING",),
            report_draft_id="RPD-WRITING-UNRESOLVED",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)

        dialog._set_editor_section(1)
        german = dialog.findChild(QWidget, "LearningReportWritingEvidence_german")
        self.assertIsNotNone(german)
        if german is None:
            raise AssertionError("Expected German writing evidence card")
        german_text = " ".join(
            label.text() for label in german.findChildren(QLabel)
        )
        self.assertIn("0 Kompetenzen · 0 Beobachtungsbelege", german_text)
        self.assertIn(
            "1 ausgewählter Beobachtungsbeleg ist nicht mehr vollständig verfügbar.",
            german_text,
        )
        self.assertNotIn("OBS-MISSING", german_text)

        dialog._set_editor_section(2)
        math = dialog.findChild(QWidget, "LearningReportWritingEvidence_math")
        self.assertIsNotNone(math)
        if math is None:
            raise AssertionError("Expected math writing evidence card")
        math_text = " ".join(label.text() for label in math.findChildren(QLabel))
        self.assertIn("1 Kompetenz · 0 Beobachtungsbelege", math_text)
        self.assertIn("Volle Stunden ablesen · 0 Beobachtungen", math_text)
        self.assertFalse(dialog._dirty)

    def test_historical_projected_evidence_counts_without_unresolved_warning(
        self,
    ) -> None:
        active_evidence = self.preparation.subjects[1].evidence[0]
        historical_evidence = replace(
            active_evidence,
            subject_id="math",
            availability_state="historical",
        )
        preparation = replace(
            self.preparation,
            subjects=(
                self.preparation.subjects[0],
                replace(
                    self.preparation.subjects[1],
                    evidence=(historical_evidence,),
                ),
            ),
        )
        initial = LearningReportDraftViewModel(
            student_id=preparation.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=("CMP-000001",),
            observation_ids=("OBS-000001",),
            unavailable_observation_ids=("OBS-000001",),
            report_draft_id="RPD-HISTORICAL-WRITING",
        )

        dialog = LearningReportDialog(preparation, initial_draft=initial)
        dialog._set_editor_section(2)
        card = dialog.findChild(QWidget, "LearningReportWritingEvidence_math")
        self.assertIsNotNone(card)
        if card is None:
            raise AssertionError("Expected math writing evidence card")
        text = " ".join(label.text() for label in card.findChildren(QLabel))

        self.assertIn("1 Kompetenz · 1 Beobachtungsbeleg", text)
        self.assertNotIn("nicht mehr vollständig verfügbar", text)
        self.assertEqual(dialog._unavailable_observation_ids, set())
        self.assertFalse(dialog._dirty)

    def test_writing_evidence_counts_multiple_items_without_other_subjects(self) -> None:
        german = self.preparation.subjects[0].competencies[0]
        math = self.preparation.subjects[1].competencies[0]
        second_math = replace(
            math,
            competency_id="CMP-MATH-SECOND",
            competency_text="Langer zweiter Kompetenztext für die Berichtsevidenz",
        )
        german_evidence = LearningReportEvidenceViewModel(
            "OBS-GERMAN",
            date(2026, 3, 10),
            "Deutsch",
            "Lesezeit",
            "Anderes Fach",
            (german.competency_id,),
            subject_id="german",
        )
        second_math_evidence = LearningReportEvidenceViewModel(
            "OBS-MATH-SECOND",
            date(2026, 3, 13),
            "Mathematik",
            "Lernzeit",
            "Zweiter Beleg",
            (math.competency_id, second_math.competency_id),
            subject_id="math",
        )
        preparation = replace(
            self.preparation,
            subjects=(
                replace(self.preparation.subjects[0], evidence=(german_evidence,)),
                replace(
                    self.preparation.subjects[1],
                    competencies=(math, second_math),
                    evidence=(
                        *self.preparation.subjects[1].evidence,
                        second_math_evidence,
                    ),
                ),
            ),
        )
        draft = LearningReportDraft(
            date(2026, 1, 1),
            date(2026, 7, 31),
            "Laura Lernbegleiterin",
            "",
            "",
            "",
            ("german", "math"),
            (german.competency_id, math.competency_id, second_math.competency_id),
            ("OBS-GERMAN", "OBS-000001", "OBS-MATH-SECOND"),
        )

        context = build_learning_report_writing_evidence(
            preparation,
            draft,
            "math",
        )

        self.assertEqual(context.competency_count, 2)
        self.assertEqual(context.observation_count, 2)
        self.assertEqual(
            tuple(item.observation_count for item in context.competencies),
            (2, 1),
        )
        self.assertEqual(context.unresolved_observation_count, 0)

    def test_new_report_groups_subjects_and_requires_a_deliberate_choice(self) -> None:
        preparation = replace(
            self.preparation,
            subjects=(self.preparation.subjects[1], self.preparation.subjects[0]),
            primary_subject_ids=("math",),
        )
        dialog = LearningReportDialog(preparation)

        group_labels = [
            label.text()
            for label in dialog.findChildren(
                QLabel,
                "LearningReportSubjectGroupLabel",
            )
        ]
        self.assertEqual(group_labels, ["FÄCHER DES KINDES", "WEITERE FÄCHER"])
        self.assertEqual(dialog.workspace_navigation.current_key(), "evidence")
        self.assertFalse(dialog.continue_to_writing_button.isEnabled())

        dialog.subject_widgets["math"]["include"].setChecked(True)

        self.assertEqual(
            dialog.evidence_selection_summary.text(),
            "Ausgewählt: Mathematik",
        )
        self.assertEqual(
            dialog.selected_subject_context.text(),
            "Ausgewählte Berichtsfächer: Mathematik",
        )
        self.assertTrue(dialog.continue_to_writing_button.isEnabled())
        self.assertEqual(
            [button.text() for button in dialog.navigation_group.buttons()],
            ["Gesamttext", "Mathematik"],
        )
        dialog.continue_to_writing_button.click()
        self.assertEqual(dialog.workspace_navigation.current_key(), "writing")
        self.assertTrue(dialog.selected_subject_context.isVisibleTo(dialog))

    def test_preview_overview_contains_only_selected_subjects(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        dialog.subject_widgets["math"]["include"].setChecked(True)

        overview = dialog._overview_preview_page()
        labels = [label.text() for label in overview.findChildren(QLabel)]

        self.assertIn("Mathematik", labels)
        self.assertNotIn("Deutsch", labels)

    def test_subject_sidebar_scrolls_without_compressing_footer_or_buttons(self) -> None:
        subject_data = (
            ("deutsch", "Deutsch"),
            ("mathematik", "Mathematik"),
            ("englisch", "Englisch"),
            ("musik", "Musik"),
            ("ethik", "Ethik"),
            ("religion", "Religion"),
            ("schulgarten", "Schulgarten"),
            ("epu", "EPU / Sachkunde"),
            ("kreatives_gestalten", "Kreatives Gestalten"),
            ("sport", "Sport"),
            ("self_social", "Selbst- und Sozialkompetenz"),
            ("work_learning", "Arbeits-/Lernkompetenz"),
        )
        subjects = tuple(
            LearningReportSubjectViewModel(subject_id, name, (), ())
            for subject_id, name in subject_data
        )
        preparation = LearningReportPreparationViewModel(
            "STU-SIDEBAR",
            "Mara Beispielkind",
            "Sonnenbogen",
            subjects,
            primary_subject_ids=tuple(subject_id for subject_id, _name in subject_data[:8]),
            retained_subject_ids=tuple(subject_id for subject_id, _name in subject_data[8:]),
        )
        initial = LearningReportDraftViewModel(
            student_id=preparation.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=tuple(
                LearningReportSubjectDraftViewModel(subject_id)
                for subject_id, _name in subject_data
            ),
            report_draft_id="RPD-SIDEBAR",
        )
        dialog = LearningReportDialog(preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        dialog.show()

        footer = dialog.findChild(QFrame, "LearningReportSidebarFooter")
        self.assertIsNotNone(footer)
        if footer is None:
            raise AssertionError("Expected fixed report sidebar footer")
        buttons = tuple(dialog._evidence_subject_buttons.values())
        self.assertEqual(len(buttons), len(subject_data))
        self.assertTrue(all(not button.icon().isNull() for button in buttons))

        for width, height in ((1150, 768), (1180, 760), (1280, 800), (1400, 900)):
            dialog.resize(width, height)
            self.app.processEvents()
            self.assertEqual(
                dialog.evidence_subject_scroll.horizontalScrollBarPolicy(),
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )
            self.assertGreater(dialog.evidence_subject_scroll.height(), 0)
            self.assertTrue(all(
                button.height() >= button.sizeHint().height()
                for button in buttons
            ))
            self.assertTrue(all(
                footer.rect().contains(child.geometry())
                for child in (
                    dialog.evidence_selection_summary,
                    dialog.continue_to_writing_button,
                )
            ))
            self.assertGreaterEqual(
                dialog.evidence_selection_summary.height(),
                dialog.evidence_selection_summary.heightForWidth(
                    dialog.evidence_selection_summary.width()
                ),
            )
            self.assertGreaterEqual(
                dialog.continue_to_writing_button.height(),
                dialog.continue_to_writing_button.sizeHint().height(),
            )

        self.assertGreater(
            dialog.evidence_subject_scroll.verticalScrollBar().maximum(),
            0,
        )
        self.assertTrue(dialog.findChildren(QWidget, "SubjectAccentMarker"))
        dialog.close()

    def test_empty_subject_can_be_unselected_without_confirmation(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            report_draft_id="RPD-EMPTY",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        include = dialog.subject_widgets["math"]["include"]
        self.assertIsInstance(include, QCheckBox)

        include.setChecked(False)

        self.assertFalse(include.isChecked())
        self.assertEqual(dialog.report_draft_view_model().selected_subject_ids, ())

    def test_subject_removal_requires_confirmation_for_each_saved_content_kind(self) -> None:
        cases = (
            ("Text", {"subjects": (LearningReportSubjectDraftViewModel("math", "Gespeicherter Text."),)}),
            ("Kompetenz", {"subjects": (LearningReportSubjectDraftViewModel("math"),), "competency_ids": ("CMP-000001",)}),
            ("Beobachtungsbeleg", {"subjects": (LearningReportSubjectDraftViewModel("math"),), "competency_ids": ("CMP-000001",), "observation_ids": ("OBS-000001",)}),
            ("Diagramm", {"subjects": (LearningReportSubjectDraftViewModel("math"),), "chart_selections": (LearningReportChartSelectionViewModel("math", "documentation_coverage"),)}),
        )
        for label, values in cases:
            with self.subTest(content=label):
                initial = LearningReportDraftViewModel(
                    student_id="STU-000001",
                    period_start=date(2026, 1, 1),
                    period_end=date(2026, 7, 31),
                    subjects=(
                        *values.get("subjects", ()),
                        LearningReportSubjectDraftViewModel("german", "Deutsch bleibt."),
                    ),
                    competency_ids=values.get("competency_ids", ()),
                    observation_ids=values.get("observation_ids", ()),
                    chart_selections=values.get("chart_selections", ()),
                    report_draft_id="RPD-REMOVE",
                )
                dialog = LearningReportDialog(self.preparation, initial_draft=initial)
                dialog.show_workspace("evidence")
                dialog._set_evidence_section(1)
                include = dialog.subject_widgets["math"]["include"]
                self.assertIsInstance(include, QCheckBox)
                before = dialog.report_draft_view_model()
                QTimer.singleShot(0, lambda current=dialog: self._click_message_button(current, "Abbrechen"))
                include.setChecked(False)

                self.assertTrue(include.isChecked())
                self.assertEqual(dialog.report_draft_view_model(), before)
                self.assertIn("german", dialog.selected_subject_ids)

    def test_confirmed_subject_removal_changes_only_its_draft_context(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            overall_text="Gesamttext bleibt.",
            subjects=(
                LearningReportSubjectDraftViewModel("math", "Mathetext."),
                LearningReportSubjectDraftViewModel("german", "Deutschtext."),
            ),
            competency_ids=("CMP-000001", "CMP-000002"),
            observation_ids=("OBS-000001",),
            chart_selections=(
                LearningReportChartSelectionViewModel("math", "documentation_coverage"),
            ),
            report_draft_id="RPD-REMOVE",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        include = dialog.subject_widgets["math"]["include"]
        self.assertIsInstance(include, QCheckBox)
        QTimer.singleShot(
            0,
            lambda current=dialog: self._click_message_button(
                current, "Fach aus Entwurf entfernen"
            ),
        )
        include.setChecked(False)

        removed = dialog.report_draft_view_model()
        self.assertEqual(removed.selected_subject_ids, ("german",))
        self.assertEqual(removed.subjects[0].strengths_text, "Deutschtext.")
        self.assertEqual(removed.overall_text, "Gesamttext bleibt.")
        self.assertEqual(removed.competency_ids, ("CMP-000002",))
        self.assertEqual(removed.observation_ids, ())
        self.assertEqual(removed.chart_selections, ())

        include.setChecked(True)
        added_again = dialog.report_draft_view_model()
        math = next(subject for subject in added_again.subjects if subject.subject_id == "math")
        self.assertEqual(
            (math.strengths_text, math.development_text, math.support_needs_text, math.next_goals_text),
            ("", "", "", ""),
        )

    @staticmethod
    def _click_message_button(dialog: LearningReportDialog, label: str) -> None:
        message = next(
            item
            for item in dialog.findChildren(QMessageBox)
            if item.isVisible() or item.windowTitle() == "Fach aus Entwurf entfernen"
        )
        button = next(item for item in message.buttons() if item.text() == label)
        button.click()

    def test_retained_subject_without_competencies_round_trips_as_saved_section(
        self,
    ) -> None:
        retained_subject = LearningReportSubjectViewModel(
            "selbst_sozialkompetenz",
            "Selbst- und Sozialkompetenz",
            (),
            (),
        )
        preparation = LearningReportPreparationViewModel(
            self.preparation.student_id,
            self.preparation.student_name,
            self.preparation.group_name,
            (retained_subject,),
            retained_subject_ids=(retained_subject.subject_id,),
        )
        initial = LearningReportDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(
                LearningReportSubjectDraftViewModel(
                    retained_subject.subject_id,
                    "Gespeicherte Stärke.",
                    "Gespeicherte Entwicklung.",
                    "",
                    "Gespeichertes Ziel.",
                ),
            ),
            report_draft_id="RPD-RETAINED",
        )

        dialog = LearningReportDialog(preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        group_labels = [
            label.text()
            for label in dialog.findChildren(
                QLabel,
                "LearningReportSubjectGroupLabel",
            )
        ]

        self.assertEqual(group_labels, ["GESPEICHERTE FACHABSCHNITTE"])
        self.assertEqual(dialog.report_draft_view_model(), initial)

    def test_lazy_workspaces_and_subjects_build_once_and_reuse_widgets(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            report_draft_id="RPD-LAZY",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)

        self.assertEqual(dialog.workspace_navigation.current_key(), "writing")

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
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            report_draft_id="RPD-PERIOD",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)

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

    def test_preview_owns_finalization_and_secondary_revision_history(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show_workspace("preview")

        self.assertEqual(dialog.workspace_navigation.current_key(), "preview")
        self.assertEqual(dialog.mode_stack.currentIndex(), 2)
        self.assertEqual(dialog.history_button.text(), "Frühere Fassungen")
        self.assertEqual(
            dialog.check_finalization_button.text(),
            "Finalisierung prüfen",
        )

        dialog.history_button.click()
        self.app.processEvents()

        self.assertEqual(dialog.workspace_navigation.current_key(), "preview")
        self.assertEqual(dialog.mode_stack.currentIndex(), 3)
        self.assertEqual(dialog.history_header.title_label.text(), "Frühere Fassungen")
        self.assertTrue(dialog.history_header.accessibleName())

    def test_collapsing_preview_preserves_draft_export_and_survives_refresh(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.selected_subject_ids.update(("math", "german"))
        dialog.show_workspace("preview")
        draft = dialog.report_draft_view_model()
        output = build_report_output_model(self.preparation, dialog.report_draft())
        dirty = dialog._dirty
        toggle, page = dialog.preview_subject_sections["math"]
        self.assertTrue(toggle.isChecked())
        toggle.click()
        self.assertTrue(page.isHidden())
        self.assertFalse(dialog.preview_subject_sections["german"][1].isHidden())
        self.assertIn("ausklappen", toggle.accessibleName())
        self.assertEqual(dialog.report_draft_view_model(), draft)
        self.assertEqual(build_report_output_model(self.preparation, dialog.report_draft()), output)
        self.assertEqual(dialog._dirty, dirty)
        dialog._preview_stale = True
        dialog.update_preview()
        toggle, page = dialog.preview_subject_sections["math"]
        self.assertTrue(page.isHidden())
        toggle.click()
        self.assertFalse(page.isHidden())
        self.assertIn("5 Seiten", dialog.preview_status.text())
        reopened = LearningReportDialog(self.preparation)
        reopened.selected_subject_ids.add("math")
        reopened.show_workspace("preview")
        self.assertTrue(reopened.preview_subject_sections["math"][0].isChecked())

    def test_report_close_dialog_has_safe_three_way_actions(self) -> None:
        confirmation = LearningReportCloseDialog()
        buttons = {
            button.text(): button
            for button in confirmation.findChildren(QPushButton)
        }

        self.assertEqual(
            set(buttons),
            {"Entwurf speichern", "Änderungen verwerfen", "Weiter bearbeiten"},
        )
        self.assertTrue(buttons["Weiter bearbeiten"].isDefault())
        self.assertFalse(buttons["Änderungen verwerfen"].isDefault())
        self.assertFalse(buttons["Entwurf speichern"].isDefault())
        self.assertEqual(
            buttons["Änderungen verwerfen"].property("buttonRole"),
            "destructive",
        )

    def test_dirty_close_saves_discards_continues_and_preserves_failed_save(
        self,
    ) -> None:
        continue_dialog = LearningReportDialog(self.preparation)
        continue_dialog.show()
        continue_dialog.overall_input.setPlainText("Weiter bearbeiten")
        continue_dialog._close_choice_provider = lambda _parent: "continue"
        continue_dialog.close_button.click()
        self.app.processEvents()
        self.assertTrue(continue_dialog.isVisible())
        self.assertTrue(continue_dialog._dirty)
        continue_dialog._close_choice_provider = lambda _parent: "discard"
        continue_dialog.close()

        discard_dialog = LearningReportDialog(self.preparation)
        discard_dialog.show()
        discard_dialog.overall_input.setPlainText("Verwerfen")
        discard_dialog._close_choice_provider = lambda _parent: "discard"
        discard_dialog.close_button.click()
        self.app.processEvents()
        self.assertFalse(discard_dialog.isVisible())

        save_dialog = LearningReportDialog(self.preparation)
        save_dialog.show()
        save_dialog.overall_input.setPlainText("Speichern")
        save_dialog.save_requested.connect(
            lambda draft: save_dialog.apply_saved_draft(
                replace(
                    draft,
                    report_draft_id="RPD-CLOSE",
                    updated_at="2026-08-12T10:00:00+00:00",
                )
            )
        )
        save_dialog._close_choice_provider = lambda _parent: "save"
        save_dialog.close_button.click()
        self.app.processEvents()
        self.assertFalse(save_dialog.isVisible())
        self.assertFalse(save_dialog._dirty)

        failed_dialog = LearningReportDialog(self.preparation)
        failed_dialog.show()
        failed_dialog.overall_input.setPlainText("Fehler erhalten")
        failed_dialog.save_requested.connect(
            lambda _draft: failed_dialog.show_save_error("Testfehler")
        )
        failed_dialog._close_choice_provider = lambda _parent: "save"
        failed_dialog.close_button.click()
        self.app.processEvents()
        self.assertTrue(failed_dialog.isVisible())
        self.assertTrue(failed_dialog._dirty)
        self.assertIn("Testfehler", failed_dialog.workspace_message.label.text())
        failed_dialog._close_choice_provider = lambda _parent: "discard"
        failed_dialog.close()

    def test_escape_and_window_close_use_the_same_report_dirty_guard(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show()
        dialog.overall_input.setPlainText("Ungespeicherter Teststand")
        dialog._close_choice_provider = lambda _parent: "continue"

        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertTrue(dialog.isVisible())
        self.assertTrue(dialog._dirty)

        dialog._close_choice_provider = lambda _parent: "discard"
        dialog.close()
        self.app.processEvents()
        self.assertFalse(dialog.isVisible())

    def test_clean_report_closes_without_asking_for_a_decision(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show()
        dialog._close_choice_provider = mock.Mock(
            side_effect=AssertionError("clean close must not ask")
        )

        dialog.close_button.click()
        self.app.processEvents()

        self.assertFalse(dialog.isVisible())
        dialog._close_choice_provider.assert_not_called()

    def test_subject_filter_preserves_selection_and_historical_visibility(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        widgets = dialog.subject_widgets["math"]
        include = widgets["include"]
        tree = widgets["tree"]
        self.assertIsInstance(include, QCheckBox)
        include.setChecked(True)
        current_item = self._competency_item(tree, "CMP-000001")

        current_item.setCheckState(0, Qt.CheckState.Checked)
        dialog.editor_stack.setCurrentIndex(1)
        dialog.editor_stack.setCurrentIndex(2)
        historical_item = self._competency_item(tree, "CMP-OLD")

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
        current_item = self._competency_item(
            widgets["tree"],
            "CMP-000001",
        )
        current_item.setCheckState(0, Qt.CheckState.Checked)
        check = next(
            widget
            for widget in widgets["evidence_container"].findChildren(QCheckBox)
            if "12.03.2026" in widget.text()
        )

        self.assertNotIn("OBS-000001", dialog.selected_observation_ids)
        check.setChecked(True)

        self.assertIn("OBS-000001", dialog.selected_observation_ids)

    def test_period_evidence_sections_prioritize_without_auto_selection(self) -> None:
        math = self.preparation.subjects[1]
        evidenced = math.competencies[0]
        available = replace(
            math.competencies[0],
            competency_id="CMP-CURRENT-NO-EVIDENCE",
            competency_text="Aktuelle Kompetenz ohne Zeitraumbeleg",
            evidence_points=(),
            documentation_state="undocumented",
            sort_order=2,
        )
        preparation = replace(
            self.preparation,
            subjects=(
                self.preparation.subjects[0],
                replace(
                    math,
                    competencies=(available, evidenced, math.competencies[1]),
                    evidence=(
                        math.evidence[0],
                        replace(
                            math.evidence[0],
                            observation_id="OBS-SECOND-EVIDENCE",
                            observed_on=date(2026, 5, 20),
                        ),
                        replace(
                            math.evidence[0],
                            observation_id="OBS-QUICK-WITHOUT-COMPETENCY",
                            observed_on=date(2026, 4, 10),
                            competency_ids=(),
                        ),
                    ),
                ),
            ),
        )
        dialog = LearningReportDialog(
            preparation,
            initial_period=(date(2026, 3, 12), date(2026, 5, 20)),
        )
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        tree = dialog.subject_widgets["math"]["tree"]
        subject_root = tree.topLevelItem(0)

        self.assertEqual(
            [
                subject_root.child(index).text(0)
                for index in range(subject_root.childCount())
            ],
            [
                "Mit Belegen im Berichtszeitraum",
                "Weitere auswählbare Kompetenzen",
                "Weitere historische Einträge",
            ],
        )
        self.assertIn(
            "Beleg im Berichtszeitraum",
            self._competency_item(tree, evidenced.competency_id).text(0),
        )
        self.assertEqual(
            preparation.subjects[1].competency_ids_with_evidence_in_period(
                date(2026, 3, 12),
                date(2026, 5, 20),
            ),
            (evidenced.competency_id,),
        )
        self.assertEqual(dialog.selected_competency_ids, set())

    def test_subject_without_observation_evidence_has_only_available_group(self) -> None:
        math = self.preparation.subjects[1]
        preparation = replace(
            self.preparation,
            subjects=(
                self.preparation.subjects[0],
                replace(
                    math,
                    competencies=(math.competencies[0],),
                    evidence=(),
                ),
            ),
        )
        dialog = LearningReportDialog(
            preparation,
            initial_period=(date(2026, 1, 1), date(2026, 7, 31)),
        )
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        root = dialog.subject_widgets["math"]["tree"].topLevelItem(0)

        self.assertEqual(root.childCount(), 1)
        self.assertEqual(root.child(0).text(0), "Weitere auswählbare Kompetenzen")
        self.assertEqual(dialog.selected_competency_ids, set())

    def test_period_boundaries_reorder_tree_and_keep_selection(self) -> None:
        competency = self.preparation.subjects[1].competencies[0]
        math = self.preparation.subjects[1]
        self.assertEqual(
            math.competency_ids_with_evidence_in_period(
                date(2026, 3, 12),
                date(2026, 3, 12),
            ),
            (competency.competency_id,),
        )
        self.assertEqual(
            math.competency_ids_with_evidence_in_period(
                date(2026, 3, 13),
                date(2026, 4, 1),
            ),
            (),
        )
        dialog = LearningReportDialog(
            self.preparation,
            initial_period=(date(2026, 3, 12), date(2026, 3, 12)),
        )
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        widgets = dialog.subject_widgets["math"]
        widgets["include"].setChecked(True)
        self._competency_item(widgets["tree"], competency.competency_id).setCheckState(
            0,
            Qt.CheckState.Checked,
        )

        dialog.period_start.setDate(QDate(2026, 3, 13))
        dialog.period_end.setDate(QDate(2026, 4, 1))

        root = widgets["tree"].topLevelItem(0)
        self.assertEqual(root.child(0).text(0), "Weitere auswählbare Kompetenzen")
        self.assertIn(competency.competency_id, dialog.selected_competency_ids)
        self.assertEqual(
            widgets["evidence_header"].description_label.text(),
            "0 von 1 aktuellen Kompetenzen mit Beleg im Berichtszeitraum. "
            "Die Übersicht ist Arbeitsgrundlage und keine automatische Auswertung.",
        )

    def test_selected_historical_reference_has_own_visible_section(self) -> None:
        initial = LearningReportDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=("CMP-OLD",),
            report_draft_id="RPD-HISTORICAL-COMPETENCY",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        tree = dialog.subject_widgets["math"]["tree"]
        root = tree.topLevelItem(0)

        self.assertEqual(
            [root.child(index).text(0) for index in range(root.childCount())],
            [
                "Mit Belegen im Berichtszeitraum",
                "Gespeicherte historische Auswahl",
            ],
        )
        historical = self._competency_item(tree, "CMP-OLD")
        self.assertEqual(historical.checkState(0), Qt.CheckState.Checked)
        self.assertIn("historisch ausgewählt", historical.text(0))

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
        self.app.processEvents()

        self.assertNotIn("CMP-OLD", dialog.selected_competency_ids)
        retained_item = next(
            item
            for item in self._competency_items(tree)
            if item.data(0, Qt.ItemDataRole.UserRole) == "CMP-OLD"
        )
        self.assertFalse(bool(retained_item.flags() & Qt.ItemFlag.ItemIsEnabled))
        self.assertEqual(
            retained_item.parent().parent().parent().text(0),
            "Weitere historische Einträge",
        )

        dialog.selected_competency_ids.add("CMP-OLD")
        dialog._populate_competency_tree(self.preparation.subjects[1], tree)
        QTimer.singleShot(
            0,
            lambda current=dialog: self._click_message_button(
                current, "Fach aus Entwurf entfernen"
            ),
        )
        dialog.subject_widgets["math"]["include"].setChecked(False)
        retained_item = next(
            item
            for item in self._competency_items(tree)
            if item.data(0, Qt.ItemDataRole.UserRole) == "CMP-OLD"
        )
        self.assertEqual(
            retained_item.parent().parent().parent().text(0),
            "Weitere historische Einträge",
        )

    def test_deferred_historical_reprojection_is_cancelled_with_deleted_dialog(
        self,
    ) -> None:
        initial = LearningReportDraftViewModel(
            student_id="STU-000001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 7, 31),
            subjects=(LearningReportSubjectDraftViewModel("math"),),
            competency_ids=("CMP-OLD",),
            report_draft_id="RPD-DEFERRED-DELETE",
        )
        dialog = LearningReportDialog(self.preparation, initial_draft=initial)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.show_workspace("evidence")
        dialog._set_evidence_section(1)
        tree = dialog.subject_widgets["math"]["tree"]
        retained_item = self._competency_item(tree, "CMP-OLD")

        retained_item.setCheckState(0, Qt.CheckState.Unchecked)
        dialog.deleteLater()
        self.app.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)
        self.app.processEvents()

        self.assertFalse(isValid(dialog))

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
            "Gespeicherter Beobachtungsbeleg 1 · nicht vollständig verfügbar",
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
