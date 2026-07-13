"""Focused offscreen tests for the productive LEG workspace."""

from __future__ import annotations

import inspect
import os
import unittest
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTextEdit

from src.desktop_app import shell
from src.desktop_app.dialogs.learning_conference_dialog import LearningConferenceDialog
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.view_models.learning_conference_view_model import (
    LEARNING_CONFERENCE_CROSS_TOPICS,
    LearningConferenceCompetencyViewModel,
    LearningConferenceCrossTopicViewModel,
    LearningConferenceDraftViewModel,
    LearningConferenceEvidenceViewModel,
    LearningConferencePreparationViewModel,
    LearningConferenceSubjectViewModel,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


class LearningConferenceUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.preparation = self._preparation()

    def test_profile_has_productive_learning_conference_entry(self) -> None:
        screen = StudentProfileScreen()
        screen.set_student(StudentDetailViewModel("STU-1", "Mara Beispiel", "Sonnenbogen", "Kurs 3", "", True))
        requested: list[str] = []
        screen.learning_conference_requested.connect(requested.append)

        button = screen.findChild(QPushButton, "LearningConferenceProfileAction")
        self.assertIsNotNone(button)
        self.assertEqual(button.text(), "Lernentwicklungsgespräch")
        button.click()

        self.assertEqual(requested, ["STU-1"])

    def test_shell_loads_single_draft_and_controls_multiple_drafts(self) -> None:
        source = inspect.getsource(shell.AppShell.open_learning_conference_dialog)
        self.assertIn("len(drafts) == 1", source)
        self.assertIn("QInputDialog.getItem", source)
        self.assertIn("Neuen Entwurf anlegen", source)
        self.assertNotIn("report_type", source)

    def test_new_draft_collects_all_persistent_content_groups(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        dialog.subject_checks["math"].setChecked(True)
        dialog.cross_topic_checks["social_behavior"].setChecked(True)
        dialog.competency_checks["CMP-1"].setChecked(True)
        dialog.evidence_checks["OBS-1"].setChecked(True)
        dialog.chart_checks["documentation_coverage"].setChecked(True)
        values = {
            "conversation_entry_text": "Einstieg",
            "child_retrospective_text": "Rückblick",
            "teacher_perspective_text": "Lehrkraftsicht",
            "strengths_text": "Stärken",
            "development_fields_text": "Entwicklungsfelder",
            "prepared_goals_text": "Vorbereitete Ziele",
            "prepared_support_text": "Vorbereitete Unterstützung",
            "prepared_agreements_text": "Vorbereitete Vereinbarungen",
            "agreed_goals_text": "Gemeinsame Ziele",
            "agreed_support_text": "Gemeinsame Unterstützung",
            "agreed_agreements_text": "Gemeinsame Vereinbarungen",
            "responsibilities_text": "Zuständigkeiten",
        }
        for key, value in values.items():
            dialog.text_inputs[key].setPlainText(value)

        draft = dialog.draft_view_model()

        for key, value in values.items():
            self.assertEqual(getattr(draft, key), value)
        self.assertEqual(draft.subject_ids, ("math",))
        self.assertEqual(draft.cross_topic_keys, ("social_behavior",))
        self.assertEqual(draft.competency_ids, ("CMP-1",))
        self.assertEqual(draft.observation_ids, ("OBS-1",))
        self.assertEqual(draft.chart_types, ("documentation_coverage",))
        self.assertIsNone(draft.period_start)
        self.assertIsNone(draft.period_end)
        self.assertIsNotNone(draft.conference_date)
        self.assertIsNotNone(draft.next_review_date)

    def test_existing_draft_reconstructs_prepared_and_shared_content_separately(self) -> None:
        draft = self._draft()
        dialog = LearningConferenceDialog(self.preparation, initial_draft=draft)

        reconstructed = dialog.draft_view_model()

        self.assertEqual(reconstructed, draft)
        self.assertEqual(dialog.text_inputs["prepared_goals_text"].toPlainText(), "Vorbereitetes Ziel")
        self.assertEqual(dialog.text_inputs["agreed_goals_text"].toPlainText(), "Gemeinsam vereinbartes Ziel")
        self.assertIsNot(dialog.text_inputs["prepared_goals_text"], dialog.text_inputs["agreed_goals_text"])

    def test_unavailable_observation_is_visible_and_reference_is_preserved(self) -> None:
        dialog = LearningConferenceDialog(self.preparation, initial_draft=self._draft())

        unavailable = dialog.findChild(QLabel, "LearningConferenceUnavailableEvidence")
        # The marker is a frame; the child search below verifies its calm visible copy.
        labels = [label.text() for label in dialog.findChildren(QLabel)]
        self.assertIn("Nicht mehr verfügbarer Beobachtungsbeleg", labels)
        self.assertIn("OBS-X", dialog.draft_view_model().observation_ids)

    def test_evidence_warning_is_soft_and_does_not_change_selection(self) -> None:
        dialog = LearningConferenceDialog(self._preparation(evidence_count=6))
        dialog.subject_checks["math"].setChecked(True)
        for check in dialog.evidence_checks.values():
            check.setChecked(True)

        dialog._update_evidence_warning()

        self.assertTrue(dialog.evidence_warning.isVisibleTo(dialog))
        self.assertIn("6 Belege ausgewählt", dialog.evidence_warning_label.text())
        self.assertEqual(len(dialog.draft_view_model().observation_ids), 6)

    def test_canonical_competency_status_is_read_only(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        status_labels = dialog.findChildren(QLabel, "LearningConferenceCanonicalStatus")

        self.assertEqual(len(status_labels), 1)
        self.assertIn("Bestätigter Stand", status_labels[0].text())
        self.assertFalse(any("rating" in edit.objectName().casefold() for edit in dialog.findChildren(QTextEdit)))

    def test_only_documented_or_confirmed_competencies_are_visible(self) -> None:
        dialog = LearningConferenceDialog(self._filter_preparation())
        dialog.subject_checks["math"].setChecked(True)

        self.assertFalse(dialog.competency_widgets["CMP-OBS"].isHidden())
        self.assertFalse(dialog.competency_widgets["CMP-CONF"].isHidden())
        self.assertTrue(dialog.competency_widgets["CMP-NONE"].isHidden())

    def test_complete_period_filters_observation_dates_but_not_confirmation(self) -> None:
        draft = self._draft_for_filter(period_start=date(2026, 2, 1), period_end=date(2026, 4, 30))
        dialog = LearningConferenceDialog(self._filter_preparation(), initial_draft=draft)

        self.assertFalse(dialog.competency_widgets["CMP-OBS"].isHidden())
        self.assertTrue(dialog.competency_widgets["CMP-LATE"].isHidden())
        self.assertFalse(dialog.competency_widgets["CMP-CONF"].isHidden())

    def test_missing_period_shows_all_documented_competencies(self) -> None:
        draft = self._draft_for_filter(period_start=None, period_end=None)
        dialog = LearningConferenceDialog(self._filter_preparation(), initial_draft=draft)

        self.assertFalse(dialog.competency_widgets["CMP-OBS"].isHidden())
        self.assertFalse(dialog.competency_widgets["CMP-LATE"].isHidden())
        self.assertTrue(dialog.competency_widgets["CMP-NONE"].isHidden())

    def test_quick_observation_does_not_make_competency_visible(self) -> None:
        preparation = self._filter_preparation()
        quick = LearningConferenceEvidenceViewModel(
            "OBS-QUICK", "2026-03-10", "Mathematik", "Lernzeit",
            "Nur Text", (), True,
        )
        preparation = LearningConferencePreparationViewModel(
            preparation.student_id,
            preparation.student_name,
            preparation.group_name,
            preparation.subjects,
            preparation.cross_topics,
            (*preparation.evidence, quick),
        )
        dialog = LearningConferenceDialog(preparation)
        dialog.subject_checks["math"].setChecked(True)

        self.assertTrue(dialog.competency_widgets["CMP-NONE"].isHidden())

    def test_empty_hierarchy_branches_are_hidden(self) -> None:
        draft = self._draft_for_filter(period_start=date(2026, 2, 1), period_end=date(2026, 4, 30))
        dialog = LearningConferenceDialog(self._filter_preparation(), initial_draft=draft)

        late_topics = [
            section for _subject_id, competency_ids, section in dialog.competency_topic_sections
            if "CMP-LATE" in competency_ids
        ]
        late_areas = [
            section for _subject_id, competency_ids, section in dialog.competency_area_sections
            if "CMP-LATE" in competency_ids
        ]
        self.assertTrue(late_topics)
        self.assertTrue(late_areas)
        self.assertTrue(all(section.isHidden() for section in late_topics))
        self.assertTrue(all(section.isHidden() for section in late_areas))

    def test_selected_competency_outside_period_stays_visible_and_selected(self) -> None:
        draft = self._draft_for_filter(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 4, 30),
            competency_ids=("CMP-LATE",),
        )
        dialog = LearningConferenceDialog(self._filter_preparation(), initial_draft=draft)

        self.assertFalse(dialog.competency_widgets["CMP-LATE"].isHidden())
        self.assertTrue(dialog.competency_checks["CMP-LATE"].isChecked())
        self.assertFalse(dialog.competency_filter_notes["CMP-LATE"].isHidden())
        self.assertIn("CMP-LATE", dialog.draft_view_model().competency_ids)

    def test_period_change_does_not_delete_selection(self) -> None:
        draft = self._draft_for_filter(
            period_start=date(2026, 6, 1),
            period_end=date(2026, 8, 31),
            competency_ids=("CMP-LATE",),
        )
        dialog = LearningConferenceDialog(self._filter_preparation(), initial_draft=draft)
        dialog.period_start.setDate(dialog.period_start.minimumDate().addDays(1))
        dialog.period_end.setDate(dialog.period_start.minimumDate().addDays(2))

        self.assertTrue(dialog.competency_checks["CMP-LATE"].isChecked())
        self.assertFalse(dialog.competency_widgets["CMP-LATE"].isHidden())
        self.assertFalse(dialog.competency_filter_notes["CMP-LATE"].isHidden())

    def test_subject_without_documentation_shows_calm_empty_state(self) -> None:
        preparation = self._filter_preparation()
        dialog = LearningConferenceDialog(preparation)
        dialog.subject_checks["empty"].setChecked(True)

        empty = dialog.competency_empty_by_subject["empty"]
        self.assertFalse(empty.isHidden())
        self.assertIn("noch keine kompetenzbezogenen Beobachtungen dokumentiert", empty.text())
        self.assertTrue(dialog.competency_sections["empty"].isHidden())

    def test_save_signal_carries_complete_view_model(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        emitted: list[LearningConferenceDraftViewModel] = []
        dialog.save_requested.connect(emitted.append)

        dialog.save_button.click()

        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0].student_id, "STU-1")

    def _preparation(self, evidence_count: int = 1) -> LearningConferencePreparationViewModel:
        competency = LearningConferenceCompetencyViewModel(
            "CMP-1", "math", "Mathematik", "Größen und Messen", "Zeit",
            "Volle Stunden ablesen", "Dokumentiert", "Beobachtet", "Bestätigter Stand",
            False, True, ("2026-07-13",), False,
        )
        evidence = tuple(
            LearningConferenceEvidenceViewModel(
                f"OBS-{index + 1}", "13.07.2026", "Mathematik", "Lernzeit",
                f"Beleg {index + 1}", ("CMP-1",), False,
            )
            for index in range(evidence_count)
        )
        return LearningConferencePreparationViewModel(
            "STU-1", "Mara Beispiel", "Sonnenbogen",
            (LearningConferenceSubjectViewModel("math", "Mathematik", (competency,)),),
            tuple(LearningConferenceCrossTopicViewModel(*topic) for topic in LEARNING_CONFERENCE_CROSS_TOPICS),
            evidence,
        )

    def _filter_preparation(self) -> LearningConferencePreparationViewModel:
        competencies = (
            LearningConferenceCompetencyViewModel(
                "CMP-OBS", "math", "Mathematik", "Größen und Messen", "Zeit",
                "Dokumentiert im Frühjahr", "Dokumentiert", "erreicht", "",
                False, True, ("2026-03-10",), False,
            ),
            LearningConferenceCompetencyViewModel(
                "CMP-NONE", "math", "Mathematik", "Größen und Messen", "Zeit",
                "Nur Katalog", "Noch nicht dokumentiert", "", "",
                False, True, (), False,
            ),
            LearningConferenceCompetencyViewModel(
                "CMP-CONF", "math", "Mathematik", "Zahlen", "Bestätigung",
                "Aktuell bestätigt", "Bestätigter Stand vorhanden", "", "erreicht",
                False, True, (), True,
            ),
            LearningConferenceCompetencyViewModel(
                "CMP-LATE", "math", "Mathematik", "Raum und Form", "Geometrie",
                "Dokumentiert im Sommer", "Dokumentiert", "in Entwicklung", "",
                False, True, ("2026-07-20",), False,
            ),
        )
        empty_competency = LearningConferenceCompetencyViewModel(
            "CMP-EMPTY", "empty", "Kunst", "Gestalten", "Farbe", "Nur Katalog",
            "Noch nicht dokumentiert", "", "", False, True, (), False,
        )
        return LearningConferencePreparationViewModel(
            "STU-1", "Mara Beispiel", "Sonnenbogen",
            (
                LearningConferenceSubjectViewModel("math", "Mathematik", competencies),
                LearningConferenceSubjectViewModel("empty", "Kunst", (empty_competency,)),
            ),
            tuple(LearningConferenceCrossTopicViewModel(*topic) for topic in LEARNING_CONFERENCE_CROSS_TOPICS),
            (),
        )

    def _draft_for_filter(
        self,
        *,
        period_start: date | None,
        period_end: date | None,
        competency_ids: tuple[str, ...] = (),
    ) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id="STU-1",
            period_start=period_start,
            period_end=period_end,
            conference_date=date(2026, 7, 13),
            subject_ids=("math",),
            competency_ids=competency_ids,
        )

    def _draft(self) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id="STU-1",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 7, 31),
            conference_date=date(2026, 7, 13),
            responsible_teacher="Laura Lernbegleiterin",
            conversation_entry_text="Einstieg",
            child_retrospective_text="Rückblick",
            teacher_perspective_text="Sicht der Lehrkraft",
            strengths_text="Stärken",
            development_fields_text="Entwicklung",
            prepared_goals_text="Vorbereitetes Ziel",
            prepared_support_text="Vorbereitete Unterstützung",
            prepared_agreements_text="Vorbereitete Vereinbarung",
            agreed_goals_text="Gemeinsam vereinbartes Ziel",
            agreed_support_text="Gemeinsam vereinbarte Unterstützung",
            agreed_agreements_text="Gemeinsame Vereinbarung",
            responsibilities_text="Kind und Lehrkraft",
            next_review_date=date(2026, 9, 15),
            subject_ids=("math",),
            cross_topic_keys=("social_behavior",),
            competency_ids=("CMP-1",),
            observation_ids=("OBS-1", "OBS-X"),
            chart_types=("documentation_coverage",),
            learning_conference_draft_id="LCD-000001",
            status="draft",
            created_at="2026-07-13T08:00:00+00:00",
            updated_at="2026-07-13T09:00:00+00:00",
            unavailable_observation_ids=("OBS-X",),
        )


if __name__ == "__main__":
    unittest.main()
