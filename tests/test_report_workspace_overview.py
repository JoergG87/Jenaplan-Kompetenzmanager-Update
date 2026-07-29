"""Focused Paket-1 checks for the report and LEG overview."""

from __future__ import annotations

import os
import inspect
import unittest
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QWidget,
)

from src.core.learning_conference import (
    COMPLETED_REVISION_STATUS,
    SUPERSEDED_REVISION_STATUS,
    LearningConferenceCompletionError,
    LearningConferenceCompletionErrorCode,
    LearningConferenceRecord,
    LearningConferenceRevisionRecord,
    LearningConferenceRevisionState,
)
from src.core.learning_report import (
    FINALIZED_REVISION_STATUS,
    SUPERSEDED_REVISION_STATUS as REPORT_SUPERSEDED_REVISION_STATUS,
    LearningReportRecord,
    LearningReportRevisionRecord,
    LearningReportRevisionState,
)
from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
from src.desktop_app import shell
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceDraftViewModel,
)
from src.desktop_app.view_models.learning_report_view_model import (
    LearningReportDraftViewModel,
    LearningReportPreparationViewModel,
    LearningReportSubjectViewModel,
)
from src.desktop_app.view_models.report_overview_view_model import (
    ReportOverviewActionViewModel,
    ReportOverviewSubjectDocumentationViewModel,
    ReportOverviewTimelineEventViewModel,
    build_report_overview,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


class ReportWorkspaceOverviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.preparation = LearningReportPreparationViewModel(
            "STU-1",
            "Mara Beispiel",
            "Sonnenbogen",
            (
                LearningReportSubjectViewModel("math", "Mathematik", (), ()),
                LearningReportSubjectViewModel("german", "Deutsch", (), ()),
            ),
        )

    def test_report_no_draft_has_create_action_and_no_period_content(self) -> None:
        overview = self._overview()

        self.assertEqual(overview.report_status.state, "no_draft")
        self.assertEqual(
            overview.report_status.primary_action.label,
            "Bericht erstellen",
        )
        self.assertFalse(overview.report_content_available)
        self.assertEqual(
            overview.report_period_label,
            "Kein Berichtszeitraum gewählt",
        )

    def test_one_report_draft_is_exactly_selected_with_period_and_open_action(
        self,
    ) -> None:
        draft = self._report_draft("RPD-1")
        overview = self._overview(
            report_drafts=(draft,),
            report_states={"RPD-1": self._report_state()},
        )

        self.assertEqual(overview.selected_report_draft_id, "RPD-1")
        self.assertEqual(overview.report_status.state, "draft_without_revision")
        self.assertEqual(overview.report_status.primary_action.action_key, "open_report")
        self.assertEqual(overview.report_status.primary_action.target_id, "RPD-1")
        self.assertEqual(overview.report_period_start_label, "01.02.2026")
        self.assertEqual(overview.report_period_end_label, "31.07.2026")
        self.assertNotIn("Schuljahr", overview.report_period_label)

    def test_multiple_report_drafts_never_select_the_newest(self) -> None:
        newest = self._report_draft(
            "RPD-NEW",
            updated_at="2026-07-27T10:00:00+00:00",
        )
        older = self._report_draft(
            "RPD-OLD",
            start=date(2025, 8, 1),
            end=date(2026, 1, 31),
            updated_at="2026-02-01T10:00:00+00:00",
        )
        overview = self._overview(report_drafts=(newest, older))

        self.assertEqual(overview.report_status.state, "multiple_drafts")
        self.assertEqual(
            overview.report_status.primary_action.action_key,
            "select_report",
        )
        self.assertEqual(overview.selected_report_draft_id, "")
        self.assertFalse(overview.report_content_available)
        self.assertEqual(overview.report_status.period_label, "Berichtszeitraum erst nach Auswahl")

    def test_explicit_selection_among_multiple_drafts_drives_all_report_content(
        self,
    ) -> None:
        first = self._report_draft("RPD-1")
        second = self._report_draft(
            "RPD-2",
            start=date(2025, 8, 1),
            end=date(2026, 1, 31),
        )
        overview = build_report_overview(
            (first, second),
            {
                "RPD-1": self._report_state(),
                "RPD-2": self._report_state(),
            },
            (),
            {},
            self.preparation,
            selected_report_draft_id="RPD-2",
        )

        self.assertEqual(overview.selected_report_draft_id, "RPD-2")
        self.assertTrue(overview.report_content_available)
        self.assertEqual(
            overview.report_period_label,
            "01.08.2025 bis 31.01.2026",
        )
        self.assertEqual(
            overview.report_status.primary_action.action_key,
            "select_report",
        )
        self.assertTrue(all(
            subject.action.target_id == "RPD-2"
            for subject in overview.subjects
        ))

    def test_stale_report_selection_is_not_automatically_replaced(self) -> None:
        report = self._report_draft("RPD-REMAINING")
        leg = self._leg_draft("LCD-REMAINING")

        overview = build_report_overview(
            (report,),
            {"RPD-REMAINING": self._report_state()},
            (leg,),
            {"LCD-REMAINING": self._leg_state()},
            self.preparation,
            selected_report_draft_id="RPD-REMOVED",
            selected_learning_conference_draft_id="LCD-REMOVED",
        )

        self.assertEqual(
            overview.selected_report_draft_id,
            "",
        )
        self.assertEqual(overview.report_status.state, "multiple_drafts")
        self.assertFalse(overview.report_content_available)
        self.assertEqual(overview.learning_conference_status.state, "draft")

    def test_report_revision_zero_one_and_n_states_are_display_ready(self) -> None:
        draft = self._report_draft("RPD-1")
        no_revision = self._overview(
            report_drafts=(draft,),
            report_states={"RPD-1": self._report_state()},
        )
        current = self._report_revision(3, FINALIZED_REVISION_STATUS)
        previous = self._report_revision(2, REPORT_SUPERSEDED_REVISION_STATUS)
        finalized = self._overview(
            report_drafts=(draft,),
            report_states={
                "RPD-1": self._report_state(
                    current=current,
                    revisions=(current, previous),
                )
            },
        )

        self.assertEqual(no_revision.report_status.revision_label, "Keine Revision")
        self.assertEqual(finalized.report_status.state, "finalized")
        self.assertEqual(
            finalized.report_status.status_label,
            "Finalisiert · Revision 3",
        )
        self.assertEqual(
            [item.version_label for item in finalized.history],
            ["Entwurf", "Revision 3", "Revision 2"],
        )

    def test_report_changed_and_integrity_failures_are_textual_states(self) -> None:
        draft = self._report_draft("RPD-1")
        current = self._report_revision(1, FINALIZED_REVISION_STATUS)
        changed = self._overview(
            report_drafts=(draft,),
            report_states={
                "RPD-1": self._report_state(
                    current=current,
                    revisions=(current,),
                    changed=True,
                )
            },
        )
        broken = self._overview(
            report_drafts=(draft,),
            report_states={
                "RPD-1": self._report_state(
                    current=current,
                    revisions=(current,),
                    hash_valid=False,
                )
            },
        )
        unreadable = self._overview(
            report_drafts=(draft,),
            report_states={"RPD-1": ValueError("unreadable")},
        )

        self.assertEqual(changed.report_status.state, "draft_changed")
        self.assertIn("verändert", changed.report_status.status_label)
        self.assertEqual(broken.report_status.state, "integrity_error")
        self.assertIn("Integritätsprüfung", broken.report_status.status_label)
        self.assertEqual(unreadable.report_status.state, "integrity_error")

    def test_comparison_errors_require_review_and_never_offer_finalization(
        self,
    ) -> None:
        report = self._report_draft("RPD-1")
        report_revision = self._report_revision(1, FINALIZED_REVISION_STATUS)
        leg = self._leg_draft("LCD-1")
        leg_revision = self._leg_revision(1, COMPLETED_REVISION_STATUS)
        overview = self._overview(
            report_drafts=(report,),
            report_states={
                "RPD-1": self._report_state(
                    current=report_revision,
                    revisions=(report_revision,),
                    changed=True,
                    comparison_error="Aggregate identity mismatch",
                )
            },
            leg_drafts=(leg,),
            leg_states={
                "LCD-1": self._leg_state(
                    current=leg_revision,
                    revisions=(leg_revision,),
                    changed=True,
                    comparison_error=LearningConferenceCompletionError(
                        LearningConferenceCompletionErrorCode.PERIOD_INVALID,
                        "period invalid",
                    ),
                )
            },
        )

        self.assertEqual(overview.report_status.state, "draft_check_required")
        self.assertEqual(
            overview.learning_conference_status.state,
            "draft_check_required",
        )
        self.assertNotIn(
            "finalize_report",
            [step.action.action_key for step in overview.next_steps],
        )

    def test_unreadable_draft_lists_have_integrity_states_not_empty_semantics(
        self,
    ) -> None:
        overview = build_report_overview(
            (),
            {},
            (),
            {},
            self.preparation,
            report_list_error=ValueError("bad report row"),
            learning_conference_list_error=ValueError("bad LEG row"),
        )

        self.assertEqual(overview.report_status.state, "integrity_error")
        self.assertEqual(
            overview.learning_conference_status.state,
            "integrity_error",
        )
        self.assertNotEqual(
            overview.report_status.status_label,
            "Kein Entwurf vorhanden",
        )

    def test_leg_no_draft_draft_completed_multiple_periods_and_error(self) -> None:
        no_leg = self._overview()
        draft = self._leg_draft("LCD-1")
        draft_only = self._overview(
            leg_drafts=(draft,),
            leg_states={"LCD-1": self._leg_state()},
        )
        current = self._leg_revision(2, COMPLETED_REVISION_STATUS)
        completed = self._overview(
            leg_drafts=(draft,),
            leg_states={
                "LCD-1": self._leg_state(
                    current=current,
                    revisions=(current,),
                )
            },
        )
        other = self._leg_draft(
            "LCD-2",
            start=date(2025, 8, 1),
            end=date(2026, 1, 31),
        )
        multiple = self._overview(leg_drafts=(draft, other))
        selected_multiple = build_report_overview(
            (),
            {},
            (draft, other),
            {
                "LCD-1": self._leg_state(),
                "LCD-2": self._leg_state(),
            },
            self.preparation,
            selected_learning_conference_draft_id="LCD-2",
        )
        broken = self._overview(
            leg_drafts=(draft,),
            leg_states={"LCD-1": ValueError("broken")},
        )

        self.assertEqual(no_leg.learning_conference_status.state, "no_draft")
        self.assertEqual(
            no_leg.learning_conference_status.primary_action.label,
            "LEG beginnen",
        )
        self.assertIn(
            "LEG beginnen",
            [step.action.label for step in no_leg.next_steps],
        )
        self.assertEqual(draft_only.learning_conference_status.state, "draft")
        self.assertEqual(
            draft_only.learning_conference_status.primary_action.label,
            "LEG öffnen",
        )
        self.assertEqual(completed.learning_conference_status.state, "completed")
        self.assertEqual(
            completed.learning_conference_status.status_label,
            "Abgeschlossen · Revision 2",
        )
        self.assertEqual(
            multiple.learning_conference_status.status_label,
            "Mehrere LEG-Zeiträume",
        )
        self.assertEqual(
            multiple.learning_conference_status.primary_action.action_key,
            "select_learning_conference",
        )
        self.assertEqual(
            selected_multiple.learning_conference_status.state,
            "multiple_drafts_selected",
        )
        self.assertEqual(
            selected_multiple.next_steps[-1].action.target_id,
            "LCD-2",
        )
        self.assertEqual(broken.learning_conference_status.state, "integrity_error")

    def test_leg_changed_after_completion_is_not_a_report_state(self) -> None:
        draft = self._leg_draft("LCD-1")
        current = self._leg_revision(1, COMPLETED_REVISION_STATUS)
        overview = self._overview(
            leg_drafts=(draft,),
            leg_states={
                "LCD-1": self._leg_state(
                    current=current,
                    revisions=(current,),
                    changed=True,
                )
            },
        )

        self.assertEqual(
            overview.learning_conference_status.status_label,
            "Entwurf seit Abschluss geändert",
        )
        self.assertNotIn(
            "finalisiert",
            overview.learning_conference_status.status_label.casefold(),
        )

    def test_combined_history_keeps_types_navigation_and_activity_sort(self) -> None:
        report = self._report_draft(
            "RPD-1",
            updated_at="2026-07-20T10:00:00+00:00",
        )
        report_revision = self._report_revision(
            1,
            FINALIZED_REVISION_STATUS,
            at="2026-07-21T10:00:00+00:00",
        )
        leg = self._leg_draft(
            "LCD-1",
            updated_at="2026-07-23T10:00:00+00:00",
        )
        leg_revision = self._leg_revision(
            1,
            COMPLETED_REVISION_STATUS,
            at="2026-07-22T10:00:00+00:00",
        )
        overview = self._overview(
            report_drafts=(report,),
            report_states={
                "RPD-1": self._report_state(
                    current=report_revision,
                    revisions=(report_revision,),
                )
            },
            leg_drafts=(leg,),
            leg_states={
                "LCD-1": self._leg_state(
                    current=leg_revision,
                    revisions=(leg_revision,),
                )
            },
        )

        self.assertEqual(
            [item.document_type for item in overview.history],
            ["LEG", "LEG", "Bericht", "Bericht"],
        )
        self.assertEqual(
            [item.action.action_key for item in overview.history],
            [
                "open_learning_conference",
                "open_learning_conference_revision",
                "open_report_revision",
                "open_report",
            ],
        )

    def test_history_periods_remain_bound_to_each_revision_source(self) -> None:
        report = self._report_draft(
            "RPD-1",
            start=date(2026, 8, 1),
            end=date(2027, 1, 31),
        )
        report_revision = self._report_revision(1, FINALIZED_REVISION_STATUS)
        leg = self._leg_draft(
            "LCD-1",
            start=date(2026, 8, 1),
            end=date(2027, 1, 31),
        )
        leg_revision = self._leg_revision(1, COMPLETED_REVISION_STATUS)
        overview = build_report_overview(
            (report,),
            {
                "RPD-1": self._report_state(
                    current=report_revision,
                    revisions=(report_revision,),
                    changed=True,
                )
            },
            (leg,),
            {
                "LCD-1": self._leg_state(
                    current=leg_revision,
                    revisions=(leg_revision,),
                    changed=True,
                )
            },
            self.preparation,
            learning_conference_revision_periods={
                "LCV-1": ("2026-02-01", "2026-07-31", "2026-07-20"),
            },
        )
        report_rows = {
            item.version_label: item
            for item in overview.history
            if item.document_type == "Bericht"
        }
        leg_rows = {
            item.version_label: item
            for item in overview.history
            if item.document_type == "LEG"
        }

        self.assertEqual(
            report_rows["Entwurf"].period_label,
            "01.08.2026 bis 31.01.2027",
        )
        self.assertEqual(
            report_rows["Revision 1"].period_label,
            "01.02.2026 bis 31.07.2026",
        )
        self.assertEqual(
            leg_rows["Entwurf"].period_label,
            "01.08.2026 bis 31.01.2027",
        )
        self.assertEqual(
            leg_rows["Revision 1"].period_label,
            "01.02.2026 bis 31.07.2026",
        )

    def test_revision_verification_failure_keeps_history_metadata_visible(
        self,
    ) -> None:
        report = self._report_draft("RPD-1")
        report_revision = self._report_revision(
            1,
            FINALIZED_REVISION_STATUS,
        )
        leg = self._leg_draft("LCD-1")
        leg_revision = self._leg_revision(
            1,
            COMPLETED_REVISION_STATUS,
        )

        overview = build_report_overview(
            (report,),
            {
                "RPD-1": self._report_state(
                    current=report_revision,
                    revisions=(report_revision,),
                )
            },
            (leg,),
            {
                "LCD-1": self._leg_state(
                    current=leg_revision,
                    revisions=(leg_revision,),
                )
            },
            self.preparation,
            report_revision_errors=frozenset({"RPV-1"}),
            learning_conference_revision_periods={
                "LCV-1": ("2026-02-01", "2026-07-31", "2026-07-20"),
            },
            learning_conference_revision_errors=frozenset({"LCV-1"}),
            selected_report_draft_id="RPD-1",
        )
        revision_rows = {
            (item.document_type, item.version_label): item
            for item in overview.history
            if item.version_label == "Revision 1"
        }

        self.assertEqual(overview.report_status.state, "integrity_error")
        self.assertEqual(
            overview.learning_conference_status.state,
            "integrity_error",
        )
        self.assertEqual(
            revision_rows[("Bericht", "Revision 1")].status_label,
            "Integrität nicht bestätigt",
        )
        self.assertEqual(
            revision_rows[("LEG", "Revision 1")].status_label,
            "Integrität nicht bestätigt",
        )

    def test_next_steps_use_only_existing_actions(self) -> None:
        draft = self._report_draft("RPD-1")
        current = self._report_revision(1, FINALIZED_REVISION_STATUS)
        overview = self._overview(
            report_drafts=(draft,),
            report_states={
                "RPD-1": self._report_state(
                    current=current,
                    revisions=(current,),
                    changed=True,
                )
            },
            leg_drafts=(self._leg_draft("LCD-1"),),
        )

        self.assertEqual(
            [step.action.action_key for step in overview.next_steps],
            ["open_report", "finalize_report", "open_learning_conference"],
        )
        joined = " ".join(step.title for step in overview.next_steps)
        self.assertNotIn("Empfehl", joined)
        self.assertNotIn("Prior", joined)

    def test_subject_anchor_requests_selection_or_exact_draft_without_competency(
        self,
    ) -> None:
        draft = self._report_draft("RPD-1")
        overview = self._overview(
            report_drafts=(draft,),
            report_states={"RPD-1": self._report_state()},
        )
        screen = self._screen(overview)
        requested: list[tuple[str, str, str, str]] = []
        screen.report_draft_requested.connect(
            lambda *values: requested.append(tuple(values))
        )
        action = overview.subjects[0].action

        screen._dispatch_report_overview_action(action)

        self.assertEqual(
            requested,
            [("STU-1", "RPD-1", "math", "")],
        )
        self.assertEqual(draft.competency_ids, ())

    def test_subject_anchor_is_keyboard_reachable(self) -> None:
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            subject_documentation=(
                self._subject_documentation(
                    "math",
                    "Mathematik",
                    ("CMP-MATH-1",),
                    ("OBS-MATH-1",),
                ),
            ),
        )
        screen = self._screen(overview)
        requested: list[tuple[str, str, str, str]] = []
        screen.report_draft_requested.connect(
            lambda *values: requested.append(tuple(values))
        )
        screen.show()
        self.app.processEvents()
        button = next(
            item
            for item in screen.findChildren(QPushButton)
            if item.objectName() == "ReportOverviewPrepareSubject_math"
        )
        button.setFocus()

        QTest.keyClick(button, Qt.Key.Key_Space)

        self.assertEqual(requested, [("STU-1", "RPD-1", "math", "")])
        self.assertTrue(
            button.focusPolicy() & Qt.FocusPolicy.TabFocus
        )
        screen.close()

    def test_subject_overview_shows_four_then_all_in_existing_order(self) -> None:
        subject_documentation = tuple(
            ReportOverviewSubjectDocumentationViewModel(
                subject_id=f"subject-{index}",
                subject_name=f"Fach {index}",
                competency_ids=tuple(
                    f"CMP-{index}-{competency}"
                    for competency in range(index)
                ),
                observation_ids=tuple(
                    f"OBS-{index}-{observation}"
                    for observation in range(2 if index == 1 else 1)
                ),
                competency_count_text=(
                    f"{index} "
                    f"{'Kompetenz' if index == 1 else 'Kompetenzen'} "
                    "dokumentiert"
                ),
                observation_count_text=(
                    "2 Beobachtungen im Berichtszeitraum"
                    if index == 1
                    else "1 Beobachtung im Berichtszeitraum"
                ),
                accessible_name=(
                    f"Fach {index}: {index} Kompetenzen dokumentiert"
                ),
                evidence_action=ReportOverviewActionViewModel(
                    "show_subject_evidence",
                    "Belege ansehen",
                    f"subject-{index}",
                    f"subject-{index}",
                ),
                prepare_action=ReportOverviewActionViewModel(
                    "prepare_subject",
                    "Bericht vorbereiten",
                    "RPD-1",
                    f"subject-{index}",
                ),
            )
            for index in range(1, 7)
        )
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            subject_documentation=subject_documentation,
        )
        screen = self._screen(overview)
        screen.show()
        screen.resize(1400, 900)
        self.app.processEvents()

        def subject_buttons() -> list[QPushButton]:
            return [
                button
                for button in screen.findChildren(QPushButton)
                if button.objectName().startswith("ReportOverviewPrepareSubject_")
            ]

        self.assertEqual(
            [button.objectName() for button in subject_buttons()],
            [
                "ReportOverviewPrepareSubject_subject-1",
                "ReportOverviewPrepareSubject_subject-2",
                "ReportOverviewPrepareSubject_subject-3",
                "ReportOverviewPrepareSubject_subject-4",
            ],
        )
        toggle = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.objectName() == "ReportOverviewSubjectsToggle"
        )
        self.assertEqual(toggle.text(), "Alle anzeigen (6)")
        first_tile = next(
            widget
            for widget in screen.findChildren(QWidget)
            if (
                widget.objectName() == "ReportOverviewSubjectTile"
                and any(
                    label.text() == "Fach 1"
                    for label in widget.findChildren(QLabel)
                )
            )
        )
        first_tile_text = " ".join(
            label.text() for label in first_tile.findChildren(QLabel)
        )
        segments = [
            widget
            for widget in first_tile.findChildren(QWidget)
            if widget.objectName() == "ReportOverviewCompetencySegment"
        ]
        self.assertIn("1 Kompetenz dokumentiert", first_tile_text)
        self.assertIn(
            "2 Beobachtungen im Berichtszeitraum",
            first_tile_text,
        )
        self.assertEqual(len(segments), 1)
        self.assertFalse(any(
            widget.objectName() == "ReportOverviewSubjectDocumentationRing"
            for widget in first_tile.findChildren(QWidget)
        ))
        self.assertNotIn("/", first_tile_text)
        self.assertNotIn(" von ", first_tile_text)
        self.assertNotIn("%", first_tile_text)
        self.assertEqual(
            first_tile.accessibleName(),
            "Fach 1: 1 Kompetenzen dokumentiert",
        )

        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
        self.app.processEvents()

        self.assertEqual(len(subject_buttons()), 6)
        expanded_toggle = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.objectName() == "ReportOverviewSubjectsToggle"
        )
        self.assertEqual(expanded_toggle.text(), "Weniger anzeigen")
        screen.close()

    def test_subject_cards_render_zero_one_and_many_absolute_segments(self) -> None:
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            subject_documentation=(
                self._subject_documentation("math", "Mathematik", (), ()),
                self._subject_documentation(
                    "german",
                    "Deutsch",
                    ("CMP-DE-1",),
                    ("OBS-DE-1",),
                ),
                self._subject_documentation(
                    "musik",
                    "Musik",
                    tuple(f"CMP-MU-{index}" for index in range(13)),
                    ("OBS-MU-1",),
                ),
                self._subject_documentation(
                    "unknown",
                    "Weiteres Fach",
                    ("CMP-X-1",),
                    (),
                ),
            ),
        )
        screen = self._screen(overview)
        screen.show()
        screen.resize(1400, 900)
        self.app.processEvents()

        # Subject identity is intentionally carried by the child symbol,
        # while the tile exposes only display-ready text and actions.
        tiles = {}
        for tile in screen.findChildren(QWidget):
            if tile.objectName() != "ReportOverviewSubjectTile":
                continue
            symbol = next(
                child
                for child in tile.findChildren(QLabel)
                if child.objectName() == "ReportOverviewSubjectSymbol"
            )
            tiles[str(symbol.property("subject_id"))] = tile

        self.assertEqual(
            len(tiles["math"].findChildren(
                QWidget,
                "ReportOverviewCompetencySegment",
            )),
            0,
        )
        self.assertEqual(
            len(tiles["german"].findChildren(
                QWidget,
                "ReportOverviewCompetencySegment",
            )),
            1,
        )
        music_segments = tiles["musik"].findChildren(
            QWidget,
            "ReportOverviewCompetencySegment",
        )
        self.assertEqual(len(music_segments), 13)
        segment_container = next(
            child
            for child in tiles["musik"].findChildren(QWidget)
            if child.objectName() == "ReportOverviewCompetencySegments"
        )
        segment_rows = {
            segment_container.layout().getItemPosition(index)[0]
            for index in range(segment_container.layout().count())
        }
        self.assertGreater(len(segment_rows), 1)
        symbols = {
            subject_id: next(
                child.text()
                for child in tile.findChildren(QLabel)
                if child.objectName() == "ReportOverviewSubjectSymbol"
            )
            for subject_id, tile in tiles.items()
        }
        self.assertEqual(symbols["math"], "∑")
        self.assertEqual(symbols["german"], "Aa")
        self.assertEqual(symbols["musik"], "♫")
        self.assertEqual(symbols["unknown"], "•")
        labels = " ".join(
            label.text()
            for tile in tiles.values()
            for label in tile.findChildren(QLabel)
        )
        self.assertNotIn("/", labels)
        self.assertNotIn(" von ", labels)
        self.assertNotIn("%", labels)

        grid = next(
            child
            for child in screen.findChildren(QWidget)
            if child.objectName() == "ReportOverviewSubjectGrid"
        ).layout()
        self.assertEqual(
            [grid.getItemPosition(index)[:2] for index in range(4)],
            [(0, 0), (0, 1), (0, 2), (0, 3)],
        )
        screen.resize(1000, 760)
        self.app.processEvents()
        grid = next(
            child
            for child in screen.findChildren(QWidget)
            if child.objectName() == "ReportOverviewSubjectGrid"
        ).layout()
        self.assertEqual(
            [grid.getItemPosition(index)[:2] for index in range(4)],
            [(0, 0), (0, 1), (1, 0), (1, 1)],
        )
        screen.resize(800, 760)
        self.app.processEvents()
        grid = next(
            child
            for child in screen.findChildren(QWidget)
            if child.objectName() == "ReportOverviewSubjectGrid"
        ).layout()
        self.assertEqual(
            [grid.getItemPosition(index)[:2] for index in range(4)],
            [(0, 0), (1, 0), (2, 0), (3, 0)],
        )
        screen.close()

    def test_timeline_renders_every_event_and_supports_controlled_scrolling(
        self,
    ) -> None:
        events = tuple(
            self._timeline_event(index)
            for index in range(1, 19)
        )
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            timeline_events=events,
        )
        screen = self._screen(overview)
        screen.current_profile_dashboard = SimpleNamespace(
            orientation_changes=(
                SimpleNamespace(
                    competency_label="Uhrzeiten ablesen",
                    triggering_event=SimpleNamespace(
                        source="confirmation",
                        event_date=date(2099, 7, 28),
                    ),
                ),
            )
        )
        screen.show()
        screen.resize(1400, 900)
        screen.set_report_overview(overview)
        self.app.processEvents()

        track = next(
            widget
            for widget in screen.findChildren(QWidget)
            if widget.objectName() == "ReportOverviewTimelineTrack"
        )
        cards = [
            card
            for card in track.findChildren(QWidget)
            if card.objectName() == "ReportOverviewTimelineEventCard"
        ]
        markers = track.findChildren(
            QPushButton,
            "ReportOverviewTimelineEventAction",
        )
        connectors = [
            widget
            for widget in track.findChildren(QWidget)
            if widget.objectName() == "ReportOverviewTimelineConnector"
        ]
        labels = " ".join(
            label.text() for label in track.findChildren(QLabel)
        )
        scroll = screen.report_timeline_scroll
        bar = scroll.horizontalScrollBar()

        self.assertEqual(len(cards), 18)
        self.assertEqual(len(markers), 18)
        self.assertEqual(len(connectors), 36)
        self.assertIn("01.01.2026", labels)
        self.assertIn("18.01.2026", labels)
        self.assertNotIn("Uhrzeiten ablesen", labels)
        self.assertEqual(
            scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn,
        )
        self.assertEqual(bar.value(), bar.maximum())
        self.assertGreater(bar.maximum(), 0)
        self.assertFalse(screen.report_timeline_right_button.isEnabled())
        self.assertTrue(screen.report_timeline_left_button.isEnabled())

        QTest.keyClick(scroll, Qt.Key.Key_Home)
        self.assertEqual(bar.value(), bar.minimum())
        self.assertFalse(screen.report_timeline_left_button.isEnabled())
        QTest.keyClick(scroll, Qt.Key.Key_Right)
        self.assertGreater(bar.value(), bar.minimum())
        QTest.keyClick(scroll, Qt.Key.Key_End)
        self.assertEqual(bar.value(), bar.maximum())
        screen.report_timeline_left_button.click()
        self.assertLess(bar.value(), bar.maximum())
        screen.report_timeline_right_button.click()
        self.assertGreaterEqual(bar.value(), bar.maximum() - bar.pageStep())

        for width, expected_capacity in ((800, 2), (1000, 4), (1400, 5)):
            screen.resize(width, 760)
            self.app.processEvents()
            scroll = screen.report_timeline_scroll
            cards = [
                card
                for card in screen.report_timeline_track.findChildren(QWidget)
                if card.objectName() == "ReportOverviewTimelineEventCard"
            ]
            visible_capacity = (
                scroll.viewport().width() / cards[0].width()
            )
            self.assertAlmostEqual(
                visible_capacity,
                expected_capacity,
                delta=0.75,
            )
            self.assertEqual(len(cards), 18)
        screen.close()

    def test_timeline_handles_zero_one_under_and_exact_target_counts(
        self,
    ) -> None:
        base = self._overview(
            report_drafts=(self._report_draft("RPD-1"),),
            report_states={"RPD-1": self._report_state()},
        )
        for event_count in (0, 1, 14, 15):
            with self.subTest(event_count=event_count):
                overview = replace(
                    base,
                    timeline_events=tuple(
                        self._timeline_event(index)
                        for index in range(1, event_count + 1)
                    ),
                )
                screen = self._screen(overview)
                screen.show()
                self.app.processEvents()
                cards = screen.findChildren(
                    QWidget,
                    "ReportOverviewTimelineEventCard",
                )
                self.assertEqual(len(cards), event_count)
                if event_count == 0:
                    labels = " ".join(
                        label.text()
                        for label in screen.timeline_card.findChildren(QLabel)
                    )
                    self.assertIn(
                        "Keine Dokumentationsereignisse im Zeitraum",
                        labels,
                    )
                else:
                    self.assertIsNotNone(screen.report_timeline_scroll)
                screen.close()

    def test_timeline_keeps_anchor_on_resize_and_refresh(self) -> None:
        events = tuple(
            self._timeline_event(index)
            for index in range(1, 13)
        )
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            timeline_events=events,
        )
        screen = self._screen(overview)
        screen.show()
        screen.resize(1400, 900)
        self.app.processEvents()
        cards = [
            card
            for card in screen.report_timeline_track.findChildren(QWidget)
            if card.objectName() == "ReportOverviewTimelineEventCard"
        ]
        anchor_card = cards[5]
        anchor_identity = tuple(
            anchor_card.property("source_identity")
        )
        screen.report_timeline_scroll.horizontalScrollBar().setValue(
            anchor_card.x()
        )

        screen.resize(1000, 760)
        self.app.processEvents()

        self.assertEqual(
            screen._capture_report_timeline_state()[1],
            anchor_identity,
        )
        older = ReportOverviewTimelineEventViewModel(
            "observation",
            ("observation", "OBS-OLDER"),
            date(2025, 12, 31),
            "31.12.2025",
            "Beobachtung dokumentiert",
            "Vorhandener Kontext",
            "31.12.2025 · Beobachtung dokumentiert · Vorhandener Kontext",
            ReportOverviewActionViewModel(
                "show_observation",
                "Beobachtung öffnen",
                "OBS-OLDER",
            ),
        )
        refreshed = replace(
            overview,
            timeline_events=(older, *events),
        )
        screen.set_report_overview(refreshed)
        self.app.processEvents()

        self.assertEqual(
            screen._capture_report_timeline_state()[1],
            anchor_identity,
        )
        self.assertEqual(
            len(screen.report_timeline_track.findChildren(
                QWidget,
                "ReportOverviewTimelineEventCard",
            )),
            13,
        )
        screen.report_timeline_scroll.horizontalScrollBar().setValue(
            screen.report_timeline_scroll.horizontalScrollBar().maximum()
        )
        screen.resize(1400, 900)
        self.app.processEvents()
        self.assertEqual(
            screen.report_timeline_scroll.horizontalScrollBar().value(),
            screen.report_timeline_scroll.horizontalScrollBar().maximum(),
        )
        screen.close()

    def test_timeline_navigation_uses_only_supplied_stable_ids(self) -> None:
        events = (
            self._timeline_event(
                1,
                event_type="observation",
                action=ReportOverviewActionViewModel(
                    "show_observation",
                    "Beobachtung öffnen",
                    "OBS-STABLE",
                ),
            ),
            self._timeline_event(
                2,
                event_type="report",
                action=ReportOverviewActionViewModel(
                    "open_report_revision",
                    "Bericht öffnen",
                    "RPV-STABLE",
                ),
            ),
            self._timeline_event(
                3,
                event_type="learning_conference",
                action=ReportOverviewActionViewModel(
                    "open_learning_conference_revision",
                    "LEG öffnen",
                    "LCV-STABLE",
                ),
            ),
            self._timeline_event(
                4,
                event_type="confirmation",
                action=ReportOverviewActionViewModel(
                    "show_competency",
                    "Kompetenzbereich öffnen",
                    "CMP-STABLE",
                ),
            ),
        )
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            timeline_events=events,
        )
        screen = self._screen(overview)
        report_ids: list[str] = []
        leg_ids: list[str] = []
        screen.report_revision_requested.connect(report_ids.append)
        screen.learning_conference_revision_requested.connect(leg_ids.append)
        screen.show()
        self.app.processEvents()
        cards = {
            tuple(card.property("source_identity")): card
            for card in screen.report_timeline_track.findChildren(QWidget)
            if card.objectName() == "ReportOverviewTimelineEventCard"
        }

        cards[events[0].source_identity].findChild(
            QPushButton,
            "ReportOverviewTimelineEventAction",
        ).click()
        self.assertEqual(screen.profile_tabs.currentIndex(), 1)
        self.assertEqual(screen._focused_observation_id, "OBS-STABLE")
        cards[events[1].source_identity].findChild(
            QPushButton,
            "ReportOverviewTimelineEventAction",
        ).click()
        cards[events[2].source_identity].findChild(
            QPushButton,
            "ReportOverviewTimelineEventAction",
        ).click()
        cards[events[3].source_identity].findChild(
            QPushButton,
            "ReportOverviewTimelineEventAction",
        ).click()

        self.assertEqual(report_ids, ["RPV-STABLE"])
        self.assertEqual(leg_ids, ["LCV-STABLE"])
        self.assertEqual(screen.profile_tabs.currentIndex(), 2)
        self.assertTrue(all(
            card.accessibleName()
            for card in cards.values()
        ))
        self.assertTrue(
            screen.report_timeline_scroll.accessibleName()
        )
        screen.close()

    def test_timeline_wheel_preserves_outer_vertical_scroll_contract(
        self,
    ) -> None:
        overview = replace(
            self._overview(
                report_drafts=(self._report_draft("RPD-1"),),
                report_states={"RPD-1": self._report_state()},
            ),
            timeline_events=tuple(
                self._timeline_event(index)
                for index in range(1, 8)
            ),
        )
        screen = self._screen(overview)
        screen.show()
        self.app.processEvents()
        scroll = screen.report_timeline_scroll
        bar = scroll.horizontalScrollBar()
        bar.setValue(bar.maximum() // 2)
        original_value = bar.value()
        vertical_event = Mock()
        vertical_event.pixelDelta.return_value = QPoint(0, 120)
        vertical_event.angleDelta.return_value = QPoint(0, 120)
        vertical_event.modifiers.return_value = (
            Qt.KeyboardModifier.NoModifier
        )

        scroll.wheelEvent(vertical_event)

        vertical_event.ignore.assert_called_once()
        self.assertEqual(bar.value(), original_value)
        shifted_event = Mock()
        shifted_event.pixelDelta.return_value = QPoint(0, 120)
        shifted_event.angleDelta.return_value = QPoint(0, 120)
        shifted_event.modifiers.return_value = (
            Qt.KeyboardModifier.ShiftModifier
        )
        scroll.wheelEvent(shifted_event)
        shifted_event.accept.assert_called_once()
        self.assertLess(bar.value(), original_value)
        screen.close()

    def test_subject_anchor_focuses_existing_tree_without_checking_items(self) -> None:
        dialog = LearningReportDialog(self.preparation)
        before = set(dialog.selected_competency_ids)
        dialog.show()

        self.assertTrue(dialog.focus_evidence_subject("math"))
        self.app.processEvents()
        tree = dialog.subject_widgets["math"]["tree"]

        self.assertEqual(dialog.mode_stack.currentIndex(), 1)
        self.assertEqual(dialog.evidence_stack.currentIndex(), 0)
        self.assertIsInstance(tree, QTreeWidget)
        self.assertTrue(tree.hasFocus())
        self.assertEqual(dialog.selected_competency_ids, before)
        dialog.close()

    def test_report_page_reflows_through_three_two_and_one_columns(self) -> None:
        screen = self._screen(self._overview())
        screen.show()
        screen.resize(1000, 760)
        self.app.processEvents()
        two_column_positions = {
            card.objectName(): screen.report_overview_grid.getItemPosition(
                screen.report_overview_grid.indexOf(card)
            )
            for card in screen._report_overview_cards
        }
        self.assertEqual(screen._report_overview_columns, 2)

        screen.resize(800, 760)
        self.app.processEvents()
        one_column_positions = {
            card.objectName(): screen.report_overview_grid.getItemPosition(
                screen.report_overview_grid.indexOf(card)
            )
            for card in screen._report_overview_cards
        }
        self.assertEqual(screen._report_overview_columns, 1)

        screen.resize(1400, 900)
        self.app.processEvents()
        wide_positions = {
            card.objectName(): screen.report_overview_grid.getItemPosition(
                screen.report_overview_grid.indexOf(card)
            )
            for card in (
                screen.report_status_card,
                screen.learning_conference_status_card,
                screen.next_steps_card,
                screen.timeline_card,
                screen.subjects_card,
                screen.history_card,
            )
        }
        self.assertEqual(screen._report_overview_columns, 3)
        self.assertEqual(
            [position[:2] for position in two_column_positions.values()],
            [
                (0, 0),
                (0, 1),
                (1, 0),
                (2, 0),
                (3, 0),
                (1, 1),
            ],
        )
        self.assertEqual(
            [position[:2] for position in one_column_positions.values()],
            [(row, 0) for row in range(6)],
        )
        self.assertEqual(
            wide_positions["ReportOverviewReportStatusCard"][:2],
            (0, 0),
        )
        self.assertEqual(
            wide_positions["ReportOverviewLearningConferenceStatusCard"][:2],
            (0, 1),
        )
        self.assertEqual(
            wide_positions["ReportOverviewNextStepsCard"][:2],
            (0, 2),
        )
        self.assertEqual(
            wide_positions["ReportOverviewTimelineCard"],
            (1, 0, 1, 3),
        )
        self.assertEqual(
            wide_positions["ReportOverviewSubjectsCard"],
            (2, 0, 1, 3),
        )
        self.assertEqual(
            wide_positions["ReportOverviewHistoryCard"],
            (3, 0, 1, 3),
        )
        self.assertFalse(hasattr(screen, "competency_selection_card"))
        self.assertFalse(hasattr(screen, "workspace_boundary_card"))
        self.assertTrue(all(card.isVisible() for card in screen._report_overview_cards))
        report_scroll = screen.profile_tabs.widget(3)
        self.assertIsInstance(report_scroll, QScrollArea)
        self.assertEqual(
            report_scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        screen.close()

    def test_ui_exposes_text_status_accessible_actions_and_no_technical_ids(
        self,
    ) -> None:
        draft = self._report_draft("RPD-SECRET")
        revision = self._report_revision(1, FINALIZED_REVISION_STATUS)
        overview = self._overview(
            report_drafts=(draft,),
            report_states={
                "RPD-SECRET": self._report_state(
                    current=revision,
                    revisions=(revision,),
                )
            },
        )
        screen = self._screen(overview)
        labels = " ".join(
            label.text() for label in screen.findChildren(QLabel)
        )
        interactive = (
            tuple(screen.findChildren(QPushButton))
            + tuple(screen.findChildren(QTreeWidget))
        )
        accessible = " ".join(widget.accessibleName() for widget in interactive)

        self.assertIn("Finalisiert · Revision 1", labels)
        self.assertIn("01.02.2026 bis 31.07.2026", labels)
        self.assertNotIn("RPD-SECRET", labels)
        self.assertNotIn("RPV-1", labels)
        self.assertNotIn("RPD-SECRET", accessible)
        report_actions = {
            "Bericht öffnen",
            "Bericht vorbereiten",
            "Vorhandenen Entwurf fortsetzen",
        }
        self.assertTrue(all(
            button.accessibleName()
            for button in screen.findChildren(QPushButton)
            if button.text() in report_actions
        ))

    def test_shell_has_exact_draft_routes_without_drafts_zero_selection(self) -> None:
        report_source = inspect.getsource(shell.AppShell.open_learning_report_dialog)
        leg_source = inspect.getsource(shell.AppShell.open_learning_conference_dialog)

        self.assertIn("if report_draft_id:", report_source)
        self.assertIn("draft.report_draft_id == report_draft_id", report_source)
        self.assertNotIn("drafts[0]", report_source)
        self.assertIn("if learning_conference_draft_id:", leg_source)
        self.assertNotIn("drafts[0]", leg_source)

    def test_shell_refreshes_profile_after_report_and_leg_workspaces_close(
        self,
    ) -> None:
        report = self._report_draft("RPD-1")
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.return_value = (
            report,
        )
        report_shell.adapter.learning_report_preparation_for_student.return_value = (
            self.preparation
        )
        report_shell.adapter.learning_report_revision_status.return_value = Mock()
        report_shell._selected_report_draft_ids = {}
        report_dialog = self._fake_workspace_dialog()
        with (
            patch.object(shell, "LearningReportDialog", return_value=report_dialog),
            patch.object(shell, "exec_maximized_workspace"),
        ):
            shell.AppShell.open_learning_report_dialog(
                report_shell,
                "STU-1",
                "RPD-1",
            )
        report_shell.show_student_profile.assert_called_once_with("STU-1")

        leg = self._leg_draft("LCD-1")
        leg_shell = Mock()
        leg_shell.adapter.list_learning_conference_drafts_for_student.return_value = (
            leg,
        )
        leg_shell.adapter.learning_conference_preparation_for_student.return_value = (
            Mock()
        )
        leg_shell.adapter.learning_conference_revision_status.return_value = Mock()
        leg_shell._selected_learning_conference_draft_ids = {}
        leg_dialog = self._fake_workspace_dialog()
        leg_dialog.draft_view_model.return_value = leg
        with (
            patch.object(
                shell,
                "LearningConferenceDialog",
                return_value=leg_dialog,
            ),
            patch.object(shell, "exec_maximized_workspace"),
        ):
            shell.AppShell.open_learning_conference_dialog(
                leg_shell,
                "STU-1",
                "LCD-1",
            )
        leg_shell.show_student_profile.assert_called_once_with("STU-1")

    def test_report_without_drafts_requires_period_and_passes_it_transiently(
        self,
    ) -> None:
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.return_value = ()
        report_shell.adapter.learning_report_preparation_for_student.return_value = (
            self.preparation
        )
        report_shell._selected_report_draft_ids = {"STU-1": "RPD-STALE"}
        dialog = self._fake_workspace_dialog()
        selected_period = (date(2026, 2, 1), date(2026, 7, 31))

        with (
            patch.object(
                shell.LearningReportPeriodSelectionDialog,
                "choose",
                return_value=(True, selected_period),
            ) as choose_period,
            patch.object(
                shell,
                "LearningReportDialog",
                return_value=dialog,
            ) as create_dialog,
            patch.object(shell, "exec_maximized_workspace"),
        ):
            shell.AppShell.open_learning_report_dialog(
                report_shell,
                "STU-1",
                subject_id="math",
            )

        choose_period.assert_called_once_with(report_shell)
        create_dialog.assert_called_once_with(
            self.preparation,
            report_shell,
            None,
            None,
            selected_period,
        )
        self.assertNotIn("STU-1", report_shell._selected_report_draft_ids)
        dialog.focus_evidence_subject.assert_called_once_with("math")
        report_shell.show_student_profile.assert_called_once_with("STU-1")

    def test_new_report_from_multiple_drafts_also_requires_period(self) -> None:
        first = self._report_draft("RPD-1")
        second = self._report_draft("RPD-2")
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.return_value = (
            first,
            second,
        )
        report_shell.adapter.learning_report_preparation_for_student.return_value = (
            self.preparation
        )
        report_shell._selected_report_draft_ids = {"STU-1": "RPD-1"}
        dialog = self._fake_workspace_dialog()
        selected_period = (date(2026, 8, 1), date(2027, 1, 31))

        with (
            patch.object(
                shell.LearningReportDraftSelectionDialog,
                "choose",
                return_value=(True, None),
            ) as choose_draft,
            patch.object(
                shell.LearningReportPeriodSelectionDialog,
                "choose",
                return_value=(True, selected_period),
            ) as choose_period,
            patch.object(
                shell,
                "LearningReportDialog",
                return_value=dialog,
            ) as create_dialog,
            patch.object(shell, "exec_maximized_workspace"),
        ):
            shell.AppShell.open_learning_report_dialog(report_shell, "STU-1")

        choose_draft.assert_called_once()
        choose_period.assert_called_once_with(report_shell)
        create_dialog.assert_called_once_with(
            self.preparation,
            report_shell,
            None,
            None,
            selected_period,
        )
        self.assertNotIn("STU-1", report_shell._selected_report_draft_ids)
        report_shell.show_student_profile.assert_called_once_with("STU-1")

    def test_new_report_period_cancel_stops_before_preparation(self) -> None:
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.return_value = ()
        report_shell._selected_report_draft_ids = {}

        with (
            patch.object(
                shell.LearningReportPeriodSelectionDialog,
                "choose",
                return_value=(False, None),
            ) as choose_period,
            patch.object(shell, "LearningReportDialog") as create_dialog,
        ):
            shell.AppShell.open_learning_report_dialog(report_shell, "STU-1")

        choose_period.assert_called_once_with(report_shell)
        report_shell.adapter.learning_report_preparation_for_student.assert_not_called()
        create_dialog.assert_not_called()
        report_shell.show_student_profile.assert_not_called()

    def test_single_report_draft_opens_without_period_selection(self) -> None:
        report = self._report_draft("RPD-1")
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.return_value = (
            report,
        )
        report_shell.adapter.learning_report_preparation_for_student.return_value = (
            self.preparation
        )
        report_shell.adapter.learning_report_revision_status.return_value = Mock()
        report_shell._selected_report_draft_ids = {}
        dialog = self._fake_workspace_dialog()

        with (
            patch.object(
                shell.LearningReportPeriodSelectionDialog,
                "choose",
            ) as choose_period,
            patch.object(
                shell,
                "LearningReportDialog",
                return_value=dialog,
            ) as create_dialog,
            patch.object(shell, "exec_maximized_workspace"),
        ):
            shell.AppShell.open_learning_report_dialog(report_shell, "STU-1")

        choose_period.assert_not_called()
        create_dialog.assert_called_once_with(
            self.preparation,
            report_shell,
            report,
            report_shell.adapter.learning_report_revision_status.return_value,
            None,
        )
        self.assertEqual(
            report_shell._selected_report_draft_ids["STU-1"],
            "RPD-1",
        )
        report_shell.show_student_profile.assert_called_once_with("STU-1")

    def test_multiple_draft_subject_route_selects_then_focuses_exact_subject(
        self,
    ) -> None:
        first = self._report_draft("RPD-1")
        second = self._report_draft("RPD-2")
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.return_value = (
            first,
            second,
        )
        report_shell.adapter.learning_report_preparation_for_student.return_value = (
            self.preparation
        )
        report_shell.adapter.learning_report_revision_status.return_value = Mock()
        report_shell._selected_report_draft_ids = {}
        dialog = self._fake_workspace_dialog()

        with (
            patch.object(
                shell.LearningReportDraftSelectionDialog,
                "choose",
                return_value=(True, second),
            ) as choose,
            patch.object(
                shell.LearningReportPeriodSelectionDialog,
                "choose",
            ) as choose_period,
            patch.object(shell, "LearningReportDialog", return_value=dialog),
            patch.object(shell, "exec_maximized_workspace"),
        ):
            shell.AppShell.open_learning_report_dialog(
                report_shell,
                "STU-1",
                subject_id="math",
            )

        choose.assert_called_once()
        choose_period.assert_not_called()
        self.assertEqual(
            report_shell._selected_report_draft_ids["STU-1"],
            "RPD-2",
        )
        report_shell.adapter.learning_report_preparation_for_student.assert_called_once_with(
            "STU-1",
            period_end=second.period_end,
            retained_competency_ids=second.competency_ids,
        )
        dialog.focus_evidence_subject.assert_called_once_with("math")
        report_shell.show_student_profile.assert_called_once_with("STU-1")

    def test_shell_handles_repeated_unreadable_list_actions(self) -> None:
        report_shell = Mock()
        report_shell.adapter.list_learning_report_drafts_for_student.side_effect = (
            ValueError("bad report row")
        )
        leg_shell = Mock()
        leg_shell.adapter.list_learning_conference_drafts_for_student.side_effect = (
            ValueError("bad LEG row")
        )
        with patch.object(shell.QMessageBox, "warning") as warning:
            shell.AppShell.open_learning_report_dialog(report_shell, "STU-1")
            shell.AppShell.open_learning_conference_dialog(leg_shell, "STU-1")

        self.assertEqual(warning.call_count, 2)
        report_shell.show_student_profile.assert_not_called()
        leg_shell.show_student_profile.assert_not_called()

    def test_adapter_composes_separate_report_and_leg_application_reads(self) -> None:
        report = self._report_draft("RPD-1")
        leg = self._leg_draft("LCD-1")
        report_state = self._report_state()
        leg_state = self._leg_state()
        adapter = StudentDesktopAdapter.__new__(StudentDesktopAdapter)
        adapter.list_learning_report_drafts_for_student = Mock(
            return_value=(report,)
        )
        adapter.list_learning_conference_drafts_for_student = Mock(
            return_value=(leg,)
        )
        report_service = Mock()
        report_service.state_for_draft.return_value = report_state
        adapter._report_revision_application_service = Mock(
            return_value=report_service
        )
        leg_service = Mock()
        leg_service.state_for_draft.return_value = leg_state
        adapter._learning_conference_revision_services = Mock(
            return_value=(Mock(), leg_service)
        )
        adapter.learning_report_preparation_for_student = Mock(
            return_value=self.preparation
        )

        overview = adapter.report_overview_for_student(
            "STU-1",
            selected_report_draft_id="RPD-1",
        )

        report_service.state_for_draft.assert_called_once_with("RPD-1")
        leg_service.state_for_draft.assert_called_once()
        self.assertEqual(overview.selected_report_draft_id, "RPD-1")
        self.assertEqual(overview.learning_conference_status.state, "draft")

    def test_adapter_retains_revision_metadata_after_snapshot_failures(
        self,
    ) -> None:
        report = self._report_draft("RPD-1")
        report_revision = self._report_revision(
            1,
            FINALIZED_REVISION_STATUS,
        )
        report_state = self._report_state(
            current=report_revision,
            revisions=(report_revision,),
            hash_valid=False,
        )
        leg = self._leg_draft("LCD-1")
        leg_revision = self._leg_revision(
            1,
            COMPLETED_REVISION_STATUS,
        )
        leg_state = self._leg_state(
            current=leg_revision,
            revisions=(leg_revision,),
            hash_valid=False,
        )
        adapter = StudentDesktopAdapter.__new__(StudentDesktopAdapter)
        adapter.list_learning_report_drafts_for_student = Mock(
            return_value=(report,)
        )
        adapter.list_learning_conference_drafts_for_student = Mock(
            return_value=(leg,)
        )
        report_service = Mock()
        report_service.state_for_draft.return_value = report_state
        adapter._report_revision_application_service = Mock(
            return_value=report_service
        )
        leg_service = Mock()
        leg_service.state_for_draft.return_value = leg_state
        adapter._learning_conference_revision_services = Mock(
            return_value=(Mock(), leg_service)
        )
        adapter.learning_report_preparation_for_student = Mock(
            return_value=self.preparation
        )

        overview = adapter.report_overview_for_student(
            "STU-1",
            selected_report_draft_id="RPD-1",
        )
        revision_rows = {
            (item.document_type, item.version_label): item
            for item in overview.history
            if item.version_label == "Revision 1"
        }

        self.assertEqual(overview.report_status.state, "integrity_error")
        self.assertEqual(
            overview.learning_conference_status.state,
            "integrity_error",
        )
        self.assertEqual(
            revision_rows[("Bericht", "Revision 1")].status_label,
            "Integrität nicht bestätigt",
        )
        self.assertEqual(
            revision_rows[("LEG", "Revision 1")].status_label,
            "Integrität nicht bestätigt",
        )

    def _screen(self, overview: object) -> StudentProfileScreen:
        screen = StudentProfileScreen()
        screen.set_student(
            StudentDetailViewModel(
                "STU-1",
                "Mara Beispiel",
                "Sonnenbogen",
                "Kurs 3",
                "",
                True,
            ),
            report_overview=overview,
        )
        screen.profile_tabs.setCurrentIndex(3)
        return screen

    def _fake_workspace_dialog(self) -> Mock:
        dialog = Mock()
        for signal_name in (
            "save_requested",
            "finalization_requested",
            "finalize_confirmed",
            "revision_open_requested",
            "pdf_requested",
            "completion_requested",
        ):
            setattr(dialog, signal_name, Mock())
        return dialog

    def _overview(
        self,
        *,
        report_drafts: tuple[LearningReportDraftViewModel, ...] = (),
        report_states: dict[str, object] | None = None,
        leg_drafts: tuple[LearningConferenceDraftViewModel, ...] = (),
        leg_states: dict[str, object] | None = None,
    ):
        return build_report_overview(
            report_drafts,
            report_states or {},
            leg_drafts,
            leg_states or {},
            self.preparation,
            selected_report_draft_id=(
                report_drafts[0].report_draft_id
                if len(report_drafts) == 1
                else ""
            ),
        )

    @staticmethod
    def _subject_documentation(
        subject_id: str,
        subject_name: str,
        competency_ids: tuple[str, ...],
        observation_ids: tuple[str, ...],
    ) -> ReportOverviewSubjectDocumentationViewModel:
        competency_count = len(competency_ids)
        observation_count = len(observation_ids)
        return ReportOverviewSubjectDocumentationViewModel(
            subject_id=subject_id,
            subject_name=subject_name,
            competency_ids=competency_ids,
            observation_ids=observation_ids,
            competency_count_text=(
                f"{competency_count} "
                f"{'Kompetenz' if competency_count == 1 else 'Kompetenzen'} "
                "dokumentiert"
            ),
            observation_count_text=(
                f"{observation_count} "
                f"{'Beobachtung' if observation_count == 1 else 'Beobachtungen'} "
                "im Berichtszeitraum"
            ),
            accessible_name=(
                f"{subject_name}: {competency_count} "
                f"{'Kompetenz' if competency_count == 1 else 'Kompetenzen'} "
                "dokumentiert"
            ),
            evidence_action=ReportOverviewActionViewModel(
                "show_subject_evidence",
                "Belege ansehen",
                subject_id,
                subject_id,
            ),
            prepare_action=ReportOverviewActionViewModel(
                "prepare_subject",
                "Bericht vorbereiten",
                "RPD-1",
                subject_id,
            ),
        )

    @staticmethod
    def _timeline_event(
        index: int,
        *,
        event_type: str = "observation",
        action: ReportOverviewActionViewModel | None = None,
    ) -> ReportOverviewTimelineEventViewModel:
        occurred_on = date(2026, 1, index)
        source_id = f"{event_type.upper()}-{index:02d}"
        identity_type = {
            "learning_conference": "learning_conference",
            "confirmation": "confirmation",
            "report": "report",
        }.get(event_type, "observation")
        source_identity = (
            ("confirmation", "STU-1", source_id)
            if event_type == "confirmation"
            else (identity_type, source_id)
        )
        title = {
            "report": "Bericht abgeschlossen",
            "learning_conference": "LEG durchgeführt",
            "confirmation": "Kompetenz bestätigt",
        }.get(event_type, "Beobachtung dokumentiert")
        resolved_action = action or ReportOverviewActionViewModel(
            "show_observation",
            "Beobachtung öffnen",
            source_id,
        )
        date_label = occurred_on.strftime("%d.%m.%Y")
        detail = f"Vorhandener Kontext {index}"
        return ReportOverviewTimelineEventViewModel(
            event_type,
            source_identity,
            occurred_on,
            date_label,
            title,
            detail,
            f"{date_label} · {title} · {detail}",
            resolved_action,
        )

    def _report_draft(
        self,
        draft_id: str,
        *,
        start: date = date(2026, 2, 1),
        end: date = date(2026, 7, 31),
        updated_at: str = "2026-07-22T10:00:00+00:00",
    ) -> LearningReportDraftViewModel:
        return LearningReportDraftViewModel(
            "STU-1",
            start,
            end,
            report_draft_id=draft_id,
            created_at="2026-02-01T09:00:00+00:00",
            updated_at=updated_at,
        )

    def _report_state(
        self,
        *,
        current: LearningReportRevisionRecord | None = None,
        revisions: tuple[LearningReportRevisionRecord, ...] = (),
        changed: bool = False,
        hash_valid: bool = True,
        comparison_error: str | None = None,
    ) -> LearningReportRevisionState:
        report = (
            LearningReportRecord(
                "RPT-1",
                "RPD-1",
                "STU-1",
                "learning_development",
                "2026-02-01",
                "2026-07-31",
                "2026-02-01T09:00:00+00:00",
            )
            if current is not None
            else None
        )
        return LearningReportRevisionState(
            report,
            current,
            revisions,
            changed,
            hash_valid,
            comparison_error,
        )

    def _report_revision(
        self,
        number: int,
        status: str,
        *,
        at: str = "2026-07-21T10:00:00+00:00",
    ) -> LearningReportRevisionRecord:
        return LearningReportRevisionRecord(
            f"RPV-{number}",
            "RPT-1",
            number,
            status,
            1,
            "{}",
            "0" * 64,
            at,
            "Laura",
            None,
        )

    def _leg_draft(
        self,
        draft_id: str,
        *,
        start: date = date(2026, 2, 1),
        end: date = date(2026, 7, 31),
        updated_at: str = "2026-07-20T10:00:00+00:00",
    ) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            "STU-1",
            period_start=start,
            period_end=end,
            learning_conference_draft_id=draft_id,
            created_at="2026-02-01T09:00:00+00:00",
            updated_at=updated_at,
        )

    def _leg_state(
        self,
        *,
        current: LearningConferenceRevisionRecord | None = None,
        revisions: tuple[LearningConferenceRevisionRecord, ...] = (),
        changed: bool = False,
        hash_valid: bool = True,
        comparison_error: LearningConferenceCompletionError | None = None,
    ) -> LearningConferenceRevisionState:
        conference = (
            LearningConferenceRecord(
                "LCF-1",
                "LCD-1",
                "STU-1",
                "2026-02-01T09:00:00+00:00",
            )
            if current is not None
            else None
        )
        return LearningConferenceRevisionState(
            conference,
            current,
            revisions,
            changed,
            hash_valid,
            comparison_error,
        )

    def _leg_revision(
        self,
        number: int,
        status: str,
        *,
        at: str = "2026-07-22T10:00:00+00:00",
    ) -> LearningConferenceRevisionRecord:
        return LearningConferenceRevisionRecord(
            f"LCV-{number}",
            "LCF-1",
            number,
            status,
            1,
            "{}",
            "0" * 64,
            at,
            "Laura",
            None,
        )


if __name__ == "__main__":
    unittest.main()
