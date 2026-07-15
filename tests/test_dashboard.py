"""Focused offscreen tests for the Sprint 8B dashboard."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QScrollArea

from src.application.commands.timetable import SaveTimetableEntryCommand
from src.core.sqlite_store import SQLiteCompetencyRepository, SQLiteDatabase
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
from src.desktop_app.components import CourseBadge
from src.desktop_app.screens.overview_screen import DashboardLessonCard, OverviewScreen
from src.desktop_app.shell import AppShell
from src.desktop_app import theme
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.view_models.observation_view_model import (
    ObservationCompetencyRatingDraft,
    ObservationDraftViewModel,
    ObservationSubjectOptionViewModel,
)
from src.desktop_app.view_models.student_view_model import (
    DashboardDocumentationCellViewModel,
    DashboardDocumentationGroupViewModel,
    DashboardDocumentationHeatmapViewModel,
    StudentDetailViewModel,
)


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "dashboard.sqlite"
        database = SQLiteDatabase(self.database_path)
        database.initialize_schema()
        database.ensure_master_data_defaults()
        SQLiteCompetencyRepository(database).ensure_catalog_defaults(
            CurriculumDesktopAdapter().list_entries()
        )
        self.adapter = TimetableDesktopAdapter(database)
        self.student_adapter = StudentDesktopAdapter(self.database_path)
        self.master_data_adapter = MasterDataDesktopAdapter(self.student_adapter)
        week = self.adapter.week_view_model()
        self.subject = week.subjects[0]
        self.other_subject = week.subjects[1]
        self.group = week.targets_by_type["group"][0]
        self.course = week.targets_by_type["course"][0]
        self.course_group = week.targets_by_type["course_group"][0]
        entries = CurriculumDesktopAdapter(database=database).list_entries()
        self.competency = next(
            entry
            for entry in entries
            if entry.subject_key == self.subject.item_id and entry.is_active
        )
        self.other_competency = next(
            entry
            for entry in entries
            if entry.subject_key == self.other_subject.item_id and entry.is_active
        )
        self.heatmap = DashboardDocumentationHeatmapViewModel(
            (
                DashboardDocumentationGroupViewModel(
                    self.group.item_id,
                    self.group.label,
                    (
                        DashboardDocumentationCellViewModel(
                            self.subject.item_id,
                            self.subject.label,
                            3,
                            8,
                        ),
                    ),
                ),
            )
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dashboard_covers_current_before_gap_after_weekend_and_empty(self) -> None:
        self._save(1, "08:00", "08:45")
        self._save(1, "10:00", "10:45")
        screen = OverviewScreen()

        cases = (
            (datetime(2026, 7, 13, 7, 30), "Als Nächstes · heute", 0),
            (datetime(2026, 7, 13, 8, 15), "Jetzt", 1),
            (datetime(2026, 7, 13, 9, 0), "Als Nächstes · heute", 0),
            (datetime(2026, 7, 13, 11, 0), "Nächster Unterrichtskontext", 0),
            (datetime(2026, 7, 19, 12, 0), "Nächster Unterrichtskontext", 0),
        )
        for at, expected_status, current_count in cases:
            with self.subTest(at=at):
                screen.set_dashboard(
                    self.adapter.read_projection(at), self.heatmap, at, True
                )
                labels = tuple(label.text() for label in screen.findChildren(QLabel))
                self.assertTrue(any(expected_status in text for text in labels))
                current_cards = tuple(
                    card
                    for card in screen.findChildren(DashboardLessonCard)
                    if card.property("lessonState") == "current"
                )
                self.assertEqual(len(current_cards), current_count)

        at = datetime(2026, 7, 13, 9, 0)
        screen.set_dashboard(self.adapter.read_projection(at), self.heatmap, at, True)
        target_requests: list[tuple[str, str]] = []
        screen.timetable_target_selected.connect(
            lambda target_type, target_id: target_requests.append(
                (target_type, target_id)
            )
        )
        screen.show()
        self.app.processEvents()
        QTest.mouseClick(
            screen.findChildren(DashboardLessonCard)[0],
            Qt.MouseButton.LeftButton,
        )
        self.assertEqual(target_requests, [("group", self.group.item_id)])

        empty_screen = OverviewScreen()
        empty_database = SQLiteDatabase(Path(self.temp_dir.name) / "empty.sqlite")
        empty_database.initialize_schema()
        empty_screen.set_dashboard(
            TimetableDesktopAdapter(empty_database).read_projection(
                datetime(2026, 7, 13, 8, 0)
            ),
            DashboardDocumentationHeatmapViewModel(()),
            datetime(2026, 7, 13, 8, 0),
            False,
        )
        labels = tuple(label.text() for label in empty_screen.findChildren(QLabel))
        self.assertIn("Noch kein Stundenplan eingerichtet", labels)
        settings_button = next(
            button
            for button in empty_screen.findChildren(QPushButton)
            if button.text() == "Zu Einstellungen · Stundenplan"
        )
        settings_requests: list[bool] = []
        empty_screen.settings_timetable_requested.connect(
            lambda: settings_requests.append(True)
        )
        settings_button.click()
        self.assertEqual(settings_requests, [True])

    def test_disabled_entries_are_absent_and_today_marks_past_lessons(self) -> None:
        self._save(1, "09:00", "09:45", active=False)
        screen = OverviewScreen()
        at = datetime(2026, 7, 13, 10, 0)
        screen.set_dashboard(self.adapter.read_projection(at), self.heatmap, at, True)
        labels = tuple(label.text() for label in screen.findChildren(QLabel))
        self.assertIn("Keine aktive Stunde geplant", labels)

        self._save(1, "08:00", "08:45")
        at = datetime(2026, 7, 13, 10, 0)
        screen.set_dashboard(self.adapter.read_projection(at), self.heatmap, at, True)

        cards = screen.findChildren(DashboardLessonCard)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].property("lessonState"), "past")
        labels = tuple(label.text() for label in screen.findChildren(QLabel))
        self.assertNotIn("09:00–09:45", labels)

    def test_heatmap_is_documentation_only_and_dashboard_scales_down(self) -> None:
        screen = OverviewScreen()
        screen.resize(620, 650)
        at = datetime(2026, 7, 13, 7, 30)
        screen.set_dashboard(self.adapter.read_projection(at), self.heatmap, at, False)

        labels = tuple(label.text() for label in screen.findChildren(QLabel))
        self.assertIn("Heute", labels)
        self.assertIn("3/8", labels)
        self.assertTrue(any("keine Leistung" in text for text in labels))
        self.assertFalse(any("++" in text or "Score" in text for text in labels))
        scroll = screen.findChild(QScrollArea, "DashboardScrollArea")
        self.assertIsNotNone(scroll)
        self.assertTrue(scroll.widgetResizable())
        self.assertLessEqual(screen.minimumWidth(), 620)
        markers = screen.findChildren(QFrame, "DashboardHeatmapMarker")
        self.assertTrue(markers)
        cells = screen.findChildren(QFrame, "DashboardHeatmapCell")
        self.assertTrue(cells)
        self.assertIn("3 / 8 Kinder dokumentiert", cells[0].accessibleName())
        self.assertIn("keine Leistungsbewertung", cells[0].accessibleName())
        self.assertNotIn("QLabel#DashboardHeatmapMarker", theme.APP_STYLESHEET)
        self.assertIn("background-color: #4F7599", theme.APP_STYLESHEET)

    def test_shell_navigates_all_target_types_and_builds_observation_prefill(self) -> None:
        instant = datetime(2026, 7, 13, 8, 15)
        shell = AppShell(self.database_path, now_provider=lambda: instant)
        week = shell.timetable_adapter.week_view_model()
        targets = {
            target_type: options[0].item_id
            for target_type, options in week.targets_by_type.items()
        }

        shell.show_students_for_timetable_target("group", targets["group"])
        self.assertEqual(shell.selected_group_id, targets["group"])
        shell.show_students_for_timetable_target("course", targets["course"])
        self.assertEqual(shell.selected_course_id, targets["course"])
        shell.show_students_for_timetable_target(
            "course_group", targets["course_group"]
        )
        self.assertEqual(shell.selected_course_group_id, targets["course_group"])

        shell.prepare_timetable_observation(
            self.subject.item_id,
            self.subject.label,
            "group",
            targets["group"],
            self.group.label,
        )
        shell.adapter.save_new_student(
            first_name="Mara",
            last_name="Beispiel",
            group_id=targets["group"],
            course_id=targets["course"],
        )
        student = shell.adapter.list_students(group_id=targets["group"])[0]
        with patch("src.desktop_app.shell.NewObservationDialog") as dialog_type:
            dialog_type.return_value.exec.return_value = 0
            shell.open_quick_observation_dialog(student.student_id)
        kwargs = dialog_type.call_args.kwargs
        self.assertEqual(kwargs["prefill_subject_id"], self.subject.item_id)
        self.assertEqual(kwargs["prefill_context"], f"Unterricht · {self.group.label}")
        self.assertEqual(shell.pending_observation_subject_id, "")

    def test_observation_dialog_applies_timetable_subject_and_target_context(self) -> None:
        student = StudentDetailViewModel(
            "STU-000001",
            "Mara Beispiel",
            self.group.label,
            "Kurs 1",
            "",
            True,
        )
        dialog = NewObservationDialog(
            student,
            subject_options=(
                ObservationSubjectOptionViewModel(
                    self.subject.item_id, self.subject.label
                ),
            ),
            prefill_subject_id=self.subject.item_id,
            prefill_context=f"Unterricht · {self.group.label}",
        )

        self.assertEqual(dialog.subject_select.currentData(), self.subject.item_id)
        self.assertEqual(
            dialog.context_select.currentText(), f"Unterricht · {self.group.label}"
        )

    def test_suggestions_use_group_course_and_course_group_memberships(self) -> None:
        inside = self._add_student("Anna", "Innen")
        other_group = self.master_data_adapter.add_group("Andere Gruppe")
        group_peer = self._add_student(
            "Berta", "Kurs",
            group_id=other_group.item_id,
        )
        other_course = self.master_data_adapter.add_course("Anderer Kurs")
        course_peer = self._add_student(
            "Carla", "Gruppe",
            course_id=other_course.item_id,
        )
        restricted = self.master_data_adapter.add_course_group(
            "Eingeschränkter Verbund",
            (self.group.item_id,),
            (self.course.item_id,),
        )
        inactive = self._add_student("Dora", "Inaktiv")
        with self.student_adapter.database.connect() as connection:
            connection.execute(
                "UPDATE students SET active = 0 WHERE student_id = ?",
                (inactive.student_id,),
            )
            connection.commit()
        at = datetime(2026, 7, 13, 8, 15)

        group_ids = self._suggestion_ids("group", self.group.item_id, at)
        course_ids = self._suggestion_ids("course", self.course.item_id, at)
        course_group_ids = self._suggestion_ids(
            "course_group", restricted.course_group_id, at
        )

        self.assertEqual(set(group_ids), {inside.student_id, course_peer.student_id})
        self.assertEqual(set(course_ids), {inside.student_id, group_peer.student_id})
        self.assertEqual(course_group_ids, (inside.student_id,))
        self.assertNotIn(inactive.student_id, group_ids)

    def test_suggestions_prioritize_dates_ignore_ratings_and_limit_stably(self) -> None:
        students = {
            name: self._add_student(name, "Beispiel")
            for name in ("Anna", "Berta", "Carla", "Dora", "Emil", "Frieda", "Greta")
        }
        self._add_observation(students["Berta"].student_id, "2026-06-25")
        self._add_observation(
            students["Carla"].student_id,
            "2026-07-11",
            quick=True,
            rating="--",
        )
        self._add_observation(
            students["Dora"].student_id, "2026-07-13", rating="--"
        )
        deleted = self._add_observation(students["Emil"].student_id, "2026-07-01")
        self.student_adapter.delete_observation(deleted)
        self._add_observation(
            students["Frieda"].student_id,
            "2026-07-10",
            quick=True,
            subject_id="cross_subject",
        )
        self._add_observation(
            students["Greta"].student_id,
            "2026-07-12",
            competency=self.other_competency,
            subject_id=self.other_subject.item_id,
        )
        foreign_group = self.master_data_adapter.add_group("Fremde Gruppe")
        foreign = self._add_student(
            "Hanna", "Fremd", group_id=foreign_group.item_id
        )
        self._add_observation(foreign.student_id, "2026-06-01")
        at = datetime(2026, 7, 13, 8, 15)

        all_suggestions = self.student_adapter.list_dashboard_suggested_students(
            target_type="group",
            target_id=self.group.item_id,
            subject_id=self.subject.item_id,
            subject_label=self.subject.label,
            at=at,
            limit=10,
        )
        limited = self.student_adapter.list_dashboard_suggested_students(
            target_type="group",
            target_id=self.group.item_id,
            subject_id=self.subject.item_id,
            subject_label=self.subject.label,
            at=at,
        )

        self.assertEqual(
            tuple(item.display_name.split()[0] for item in all_suggestions),
            ("Anna", "Emil", "Frieda", "Greta", "Berta", "Carla", "Dora"),
        )
        self.assertEqual(len(limited), 5)
        self.assertEqual(limited[-1].display_name, "Berta Beispiel")
        hints = {item.display_name.split()[0]: item.documentation_hint for item in all_suggestions}
        self.assertEqual(hints["Anna"], f"Noch keine Dokumentation in {self.subject.label}")
        self.assertEqual(hints["Berta"], "Letzte Beobachtung vor 18 Tagen")
        self.assertEqual(hints["Dora"], "Heute bereits dokumentiert")
        self.assertNotIn("++", " ".join(hints.values()))

    def test_matching_children_rows_emit_direct_observation_and_empty_state(self) -> None:
        student = self._add_student("Mara", "Beispiel")
        self._save(1, "08:00", "08:45")
        at = datetime(2026, 7, 13, 8, 15)
        projection = self.adapter.read_projection(at)
        suggestions = self.student_adapter.list_dashboard_suggested_students(
            target_type="group",
            target_id=self.group.item_id,
            subject_id=self.subject.item_id,
            subject_label=self.subject.label,
            at=at,
        )
        screen = OverviewScreen()
        emitted: list[tuple[str, str, str, str]] = []
        screen.timetable_student_observation_requested.connect(
            lambda *values: emitted.append(tuple(values))
        )
        screen.set_dashboard(projection, self.heatmap, at, True, suggestions)
        course_badges = screen.findChildren(CourseBadge)
        self.assertEqual(len(course_badges), 1)
        self.assertEqual(course_badges[0].label.text(), suggestions[0].course_name)
        self.assertEqual(
            course_badges[0].property("courseColorHex"),
            suggestions[0].course_color_hex,
        )
        self.assertTrue(course_badges[0].accessibleName().startswith("Kurszugehörigkeit:"))
        observe = next(
            button
            for button in screen.findChildren(QPushButton)
            if button.text() == "Beobachten"
        )
        observe.click()
        self.assertEqual(
            emitted,
            [(student.student_id, self.subject.item_id, self.subject.label, self.group.label)],
        )
        self.assertTrue(
            any(
                button.text() == "Alle Kinder anzeigen"
                for button in screen.findChildren(QPushButton)
            )
        )

        empty = OverviewScreen()
        empty.set_dashboard(projection, self.heatmap, at, True, ())
        labels = tuple(label.text() for label in empty.findChildren(QLabel))
        self.assertTrue(
            any(
                "keine aktiven Kinder zugeordnet" in text
                for text in labels
            )
        )

    def test_shell_opens_direct_suggestion_with_lesson_prefill(self) -> None:
        student = self._add_student("Mara", "Direkt")
        instant = datetime(2026, 7, 13, 8, 15)
        shell = AppShell(self.database_path, now_provider=lambda: instant)
        with patch("src.desktop_app.shell.NewObservationDialog") as dialog_type:
            dialog_type.return_value.exec.return_value = 0
            shell.open_dashboard_observation(
                student.student_id,
                self.subject.item_id,
                self.subject.label,
                self.group.label,
            )
        kwargs = dialog_type.call_args.kwargs
        self.assertEqual(kwargs["prefill_subject_id"], self.subject.item_id)
        self.assertEqual(kwargs["prefill_context"], f"Unterricht · {self.group.label}")

    def _add_student(
        self,
        first_name: str,
        last_name: str,
        *,
        group_id: str | None = None,
        course_id: str | None = None,
    ) -> object:
        result = self.student_adapter.save_new_student(
            first_name=first_name,
            last_name=last_name,
            group_id=group_id or self.group.item_id,
            course_id=course_id or self.course.item_id,
        )
        self.assertTrue(result.success)
        return result.value

    def _add_observation(
        self,
        student_id: str,
        date_text: str,
        *,
        quick: bool = False,
        competency: object | None = None,
        subject_id: str | None = None,
        rating: str = "++",
    ) -> str:
        catalog_entry = competency or self.competency
        ratings = () if quick else (
            ObservationCompetencyRatingDraft.from_catalog_entry(catalog_entry, rating),
        )
        draft = ObservationDraftViewModel(
            student_id=student_id,
            student_name="Testkind",
            date_text=date_text,
            competency_ratings=ratings,
            context="Unterricht",
            note="Dokumentation",
            subject_id=subject_id or catalog_entry.subject_key,
            subject_display_name=catalog_entry.subject_display_name,
            is_quick_observation=quick,
        )
        result = self.student_adapter.save_observation(draft)
        self.assertTrue(result.success)
        return result.value.observation_id

    def _suggestion_ids(
        self,
        target_type: str,
        target_id: str,
        at: datetime,
    ) -> tuple[str, ...]:
        return tuple(
            item.student_id
            for item in self.student_adapter.list_dashboard_suggested_students(
                target_type=target_type,
                target_id=target_id,
                subject_id=self.subject.item_id,
                subject_label=self.subject.label,
                at=at,
                limit=10,
            )
        )

    def _save(
        self,
        weekday: int,
        start: str,
        end: str,
        *,
        active: bool = True,
    ) -> None:
        self.adapter.save_entry(
            SaveTimetableEntryCommand(
                "",
                weekday,
                start,
                end,
                self.subject.item_id,
                "group",
                self.group.item_id,
                "Raum 2",
                active,
            )
        )


if __name__ == "__main__":
    unittest.main()
