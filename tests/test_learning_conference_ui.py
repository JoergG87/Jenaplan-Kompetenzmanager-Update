"""Focused offscreen tests for the productive LEG workspace."""

from __future__ import annotations

import inspect
import os
import unittest
from dataclasses import replace
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton, QTextEdit

from src.desktop_app import shell
from src.desktop_app.dialogs.learning_conference_dialog import (
    PHASES,
    ROLE_AGREEMENT,
    ROLE_CONVERSATION,
    ROLE_PREPARATION,
    LearningConferenceDialog,
    LearningConferenceDraftSelectionDialog,
)
from src.desktop_app.motion import set_reduced_motion
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

        action = next(
            action
            for action in screen.profile_more_action.menu().actions()
            if action.text() == "Lernentwicklungsgespräch öffnen"
        )
        action.trigger()

        self.assertEqual(requested, ["STU-1"])

    def test_shell_always_offers_existing_or_new_leg_selection(self) -> None:
        source = inspect.getsource(shell.AppShell.open_learning_conference_dialog)
        self.assertIn("if drafts:", source)
        self.assertIn("LearningConferenceDraftSelectionDialog.choose", source)
        self.assertNotIn("len(drafts) == 1", source)
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
        self.assertIsNone(draft.next_review_date)

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
        self.assertIn("Beleg nicht mehr verfügbar – gespeicherte Referenz bleibt erhalten", labels)
        self.assertIn("OBS-X", dialog.draft_view_model().observation_ids)

    def test_evidence_warning_is_soft_and_does_not_change_selection(self) -> None:
        dialog = LearningConferenceDialog(self._preparation(evidence_count=6))
        dialog.subject_checks["math"].setChecked(True)
        for check in dialog.evidence_checks.values():
            check.setChecked(True)

        dialog.set_active_phase("evidence", focus=False)
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

    def test_six_phases_have_fixed_order_and_neutral_states(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)

        self.assertEqual(
            tuple(key for key, _title, _description in PHASES),
            ("goal", "strengths", "development", "goals", "evidence", "agreements"),
        )
        self.assertIn("Aktuell", dialog.phase_navigation.button_for("goal").text())
        for key in ("strengths", "development", "goals", "evidence", "agreements"):
            self.assertIn("Noch leer", dialog.phase_navigation.button_for(key).text())
        dialog.text_inputs["strengths_text"].setPlainText("Ruhige Stärke")
        self.assertIn("Inhalt vorhanden", dialog.phase_navigation.button_for("strengths").text())
        dialog.set_active_phase("strengths", focus=False)
        self.assertIn("Aktuell", dialog.phase_navigation.button_for("strengths").text())

    def test_exactly_one_phase_stays_visible_and_interactive_across_navigation(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        dialog.resize(1180, 760)
        dialog.show()
        self.app.processEvents()
        dialog.text_inputs["strengths_text"].setPlainText("Bleibt im Entwurf erhalten")

        sequence = ("strengths", "development", "goals", "evidence", "goals", "strengths")
        for index, key in enumerate(sequence):
            dialog.set_active_phase(key)
            dialog.resize(1180 + (index % 2) * 220, 760 + (index % 2) * 140)
            self.app.processEvents()
            active_page = dialog.phase_pages[key]
            self.assertIs(dialog.phase_stack.currentWidget(), active_page)
            self.assertTrue(active_page.isVisibleTo(dialog))
            self.assertTrue(active_page.isEnabled())
            for other_key, page in dialog.phase_pages.items():
                if other_key == key:
                    continue
                self.assertTrue(page.isHidden(), other_key)
                self.assertFalse(page.isEnabled(), other_key)
            focused = self.app.focusWidget()
            self.assertTrue(
                focused is not None
                and (focused is active_page or active_page.isAncestorOf(focused))
            )

        self.assertEqual(
            dialog.text_inputs["strengths_text"].toPlainText(),
            "Bleibt im Entwurf erhalten",
        )
        self.assertIsNone(dialog.phase_stack.graphicsEffect())
        dialog._close_choice_provider = lambda _parent: "discard"
        dialog.close()

    def test_existing_navigation_reaches_conversation_editing_roles(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)

        for key in ("strengths", "development"):
            self.assertTrue(dialog.phase_navigation.button_for(key).isEnabled())
            dialog.set_active_phase(key, focus=False)
            labels = [label.text() for label in dialog.phase_pages[key].findChildren(QLabel)]
            self.assertIn(ROLE_CONVERSATION, labels)

        self.assertEqual(dialog.active_phase_key, "development")

    def test_all_existing_fields_are_assigned_to_the_decided_phases(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        expected = {
            "conversation_entry_text": "goal",
            "strengths_text": "strengths",
            "child_retrospective_text": "strengths",
            "teacher_perspective_text": "development",
            "development_fields_text": "development",
            "prepared_goals_text": "goals",
            "agreed_goals_text": "goals",
            "prepared_support_text": "agreements",
            "prepared_agreements_text": "agreements",
            "agreed_support_text": "agreements",
            "agreed_agreements_text": "agreements",
            "responsibilities_text": "agreements",
        }

        self.assertEqual(set(dialog.text_inputs), set(expected))
        for field_key, phase_key in expected.items():
            self.assertTrue(
                dialog.phase_pages[phase_key].isAncestorOf(dialog.text_inputs[field_key]),
                field_key,
            )
        self.assertTrue(dialog.phase_pages["goal"].isAncestorOf(dialog.next_review_date) is False)
        self.assertTrue(dialog.phase_pages["agreements"].isAncestorOf(dialog.next_review_date))

    def test_roles_are_textual_and_agreed_goals_are_in_phase_four(self) -> None:
        dialog = LearningConferenceDialog(self.preparation, initial_draft=self._draft())
        labels = {label.text() for label in dialog.findChildren(QLabel)}

        self.assertIn(ROLE_PREPARATION, labels)
        self.assertIn(ROLE_CONVERSATION, labels)
        self.assertIn(ROLE_AGREEMENT, labels)
        self.assertTrue(
            dialog.phase_pages["goals"].isAncestorOf(dialog.text_inputs["agreed_goals_text"])
        )
        self.assertFalse(
            dialog.phase_pages["agreements"].isAncestorOf(dialog.text_inputs["agreed_goals_text"])
        )

    def test_evidence_selection_lives_only_in_phase_five_and_summaries_are_read_only(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)

        for widget in (
            *dialog.competency_checks.values(),
            *dialog.evidence_checks.values(),
            *dialog.chart_checks.values(),
        ):
            self.assertTrue(dialog.phase_pages["evidence"].isAncestorOf(widget))
        for key in ("strengths", "development", "goals", "agreements"):
            summaries = dialog.phase_pages[key].findChildren(QLabel)
            self.assertTrue(any("Kompetenzen" in label.text() for label in summaries))
            self.assertFalse(any(isinstance(widget, QCheckBox) for widget in dialog.phase_pages[key].findChildren(QCheckBox)))

    def test_dirty_state_covers_text_date_and_all_reference_selections(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        changes = (
            lambda: dialog.text_inputs["strengths_text"].setPlainText("Stärke"),
            lambda: dialog.conference_date.setDate(dialog.conference_date.date().addDays(1)),
            lambda: dialog.competency_checks["CMP-1"].setChecked(True),
            lambda: dialog.evidence_checks["OBS-1"].setChecked(True),
            lambda: dialog.chart_checks["documentation_coverage"].setChecked(True),
        )
        for change in changes:
            change()
            self.assertTrue(dialog.is_dirty)
            dialog.apply_saved_draft(
                replace(
                    dialog.draft_view_model(),
                    learning_conference_draft_id="LCD-000001",
                    updated_at="2026-07-14T10:30:00+00:00",
                )
            )
            self.assertFalse(dialog.is_dirty)
        self.assertEqual(dialog.dirty_badge.text(), "Entwurf gespeichert")

    def test_search_and_phase_changes_do_not_dirty_or_save_the_draft(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        emitted: list[object] = []
        dialog.save_requested.connect(emitted.append)

        dialog.evidence_search.setText("Zeit")
        dialog.set_active_phase("evidence", focus=False)
        dialog.set_active_phase("goals", focus=False)

        self.assertFalse(dialog.is_dirty)
        self.assertEqual(emitted, [])

    def test_successful_save_resets_dirty_state(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        dialog.text_inputs["strengths_text"].setPlainText("Stärke")
        dialog.save_requested.connect(
            lambda draft: dialog.apply_saved_draft(
                replace(
                    draft,
                    learning_conference_draft_id="LCD-000001",
                    updated_at="2026-07-14T10:30:00+00:00",
                )
            )
        )

        dialog.save_button.click()

        self.assertFalse(dialog.is_dirty)
        self.assertEqual(dialog.save_button.text(), "Entwurf speichern")
        self.assertIn("Zuletzt gespeichert", dialog.status_label.text())

    def test_dirty_close_can_continue_discard_or_save(self) -> None:
        continue_dialog = LearningConferenceDialog(self.preparation)
        continue_dialog.show()
        self.app.processEvents()
        continue_dialog.text_inputs["strengths_text"].setPlainText("Änderung")
        continue_dialog._close_choice_provider = lambda _parent: "continue"
        continue_dialog.reject()
        self.assertTrue(continue_dialog.isVisible())
        continue_dialog._close_choice_provider = lambda _parent: "discard"
        continue_dialog.reject()
        self.assertFalse(continue_dialog.isVisible())

        save_dialog = LearningConferenceDialog(self.preparation)
        save_dialog.show()
        self.app.processEvents()
        save_dialog.text_inputs["strengths_text"].setPlainText("Änderung")
        save_dialog.save_requested.connect(
            lambda draft: save_dialog.apply_saved_draft(
                replace(
                    draft,
                    learning_conference_draft_id="LCD-000001",
                    updated_at="2026-07-14T10:30:00+00:00",
                )
            )
        )
        save_dialog._close_choice_provider = lambda _parent: "save"
        save_dialog.reject()
        self.assertFalse(save_dialog.isVisible())

    def test_escape_and_window_close_use_the_same_dirty_guard(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        dialog.show()
        self.app.processEvents()
        dialog.text_inputs["strengths_text"].setPlainText("Änderung")
        dialog._close_choice_provider = lambda _parent: "continue"

        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertTrue(dialog.isVisible())

        dialog._close_choice_provider = lambda _parent: "discard"
        dialog.close()
        self.app.processEvents()
        self.assertFalse(dialog.isVisible())

    def test_optional_review_date_starts_and_remains_empty(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)

        self.assertEqual(dialog.next_review_date.date(), dialog.next_review_date.minimumDate())
        self.assertIsNone(dialog.draft_view_model().next_review_date)
        dialog.show_save_error("Testfehler")
        self.assertNotIn("Überprüfungstermin", dialog.validation_message.label.text())

    def test_multiple_draft_selection_is_calm_and_has_no_destructive_actions(self) -> None:
        drafts = (
            self._draft(),
            replace(
                self._draft(),
                learning_conference_draft_id="LCD-000002",
                conference_date=date(2026, 6, 10),
                responsible_teacher="Mika Lernbegleiter",
            ),
        )
        dialog = LearningConferenceDraftSelectionDialog(drafts)
        labels = [label.text() for label in dialog.findChildren(QLabel)]
        buttons = [button.text() for button in dialog.findChildren(QPushButton)]

        self.assertIn("13.07.2026", labels)
        self.assertIn("Mika Lernbegleiter", labels)
        self.assertEqual(buttons.count("Öffnen"), 2)
        self.assertIn("Status: Entwurf", labels)
        self.assertIn("Neues LEG", buttons)
        self.assertFalse(any(term in " ".join(buttons) for term in ("Löschen", "Archivieren", "Abschließen")))

    def test_phase_navigation_is_keyboard_accessible(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        dialog.show()
        self.app.processEvents()
        first = dialog.phase_navigation.button_for("goal")
        first.setFocus()

        QTest.keyClick(first, Qt.Key.Key_Down)
        self.assertEqual(dialog.active_phase_key, "strengths")
        QTest.keyClick(dialog.phase_navigation.button_for("strengths"), Qt.Key.Key_End)
        self.assertEqual(dialog.active_phase_key, "agreements")
        QTest.keyClick(dialog.phase_navigation.button_for("agreements"), Qt.Key.Key_Home)
        self.assertEqual(dialog.active_phase_key, "goal")
        for key, _title, _description in PHASES:
            self.assertIn("Phase", dialog.phase_navigation.button_for(key).accessibleName())
        self.assertTrue(all(edit.accessibleName() for edit in dialog.text_inputs.values()))
        dialog.close()

    def test_phase_and_scroll_state_survive_local_switches(self) -> None:
        dialog = LearningConferenceDialog(self._preparation(evidence_count=24))
        dialog.subject_checks["math"].setChecked(True)
        dialog.set_active_phase("evidence", focus=False)
        dialog.resize(1180, 760)
        dialog.show()
        self.app.processEvents()
        bar = dialog.phase_scroll_areas["evidence"].verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        expected = min(80, bar.maximum())
        bar.setValue(expected)

        dialog.set_active_phase("goals", focus=False)
        dialog.set_active_phase("evidence", focus=False)

        self.assertEqual(bar.value(), expected)
        dialog._close_choice_provider = lambda _parent: "discard"
        dialog.close()

    def test_reduced_motion_applies_phase_end_state_immediately(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        set_reduced_motion(True)
        try:
            dialog.set_active_phase("goals", focus=False)
            self.assertEqual(dialog.active_phase_key, "goals")
            self.assertFalse(getattr(dialog.phase_stack, "_motion_animations", {}))
        finally:
            set_reduced_motion(False)

    def test_workspace_geometry_is_usable_at_all_target_sizes(self) -> None:
        for width, height in ((1400, 900), (1280, 800), (1180, 760)):
            dialog = LearningConferenceDialog(self._preparation(evidence_count=8))
            dialog.resize(width, height)
            dialog.show()
            self.app.processEvents()
            self.assertEqual((dialog.width(), dialog.height()), (width, height))
            self.assertTrue(dialog.save_button.isVisibleTo(dialog))
            self.assertTrue(dialog.phase_navigation.isVisibleTo(dialog))
            self.assertLessEqual(dialog.phase_navigation.width(), 232)
            for scroll in dialog.phase_scroll_areas.values():
                self.assertEqual(scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            dialog.close()

    def test_workspace_exposes_no_completion_or_export_actions(self) -> None:
        dialog = LearningConferenceDialog(self.preparation)
        button_text = " ".join(button.text() for button in dialog.findChildren(QPushButton))

        for forbidden in ("Abschließen", "Finalisieren", "PDF", "Drucken", "Exportieren"):
            self.assertNotIn(forbidden, button_text)
        self.assertEqual(dialog.save_button.text(), "Entwurf speichern")

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
