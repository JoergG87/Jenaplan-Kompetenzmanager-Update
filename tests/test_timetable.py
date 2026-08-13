"""Focused persistence, domain, projection and offscreen tests for Sprint 8A."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTabBar

from src.application.commands.timetable import SaveTimetableEntryCommand
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteTimetableRepository,
)
from src.core.timetable import TimetableValidationError
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.screens.overview_screen import OverviewScreen, dashboard_greeting
from src.desktop_app.components import SubjectAccentMarker
from src.desktop_app.view_models.student_view_model import DashboardDocumentationHeatmapViewModel
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
)


class TimetableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "kompetenzmanager.sqlite"
        self.database = SQLiteDatabase(self.database_path)
        self.database.initialize_schema()
        self.database.ensure_master_data_defaults()
        SQLiteCompetencyRepository(self.database).ensure_catalog_defaults(
            CurriculumDesktopAdapter().list_entries()
        )
        self.adapter = TimetableDesktopAdapter(self.database)
        week = self.adapter.week_view_model()
        self.subject_id = week.subjects[0].item_id
        self.group_id = week.targets_by_type["group"][0].item_id

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_migration_is_additive_and_idempotent(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            before = self._master_counts(connection)

        self.database.initialize_schema()
        self.database.initialize_schema()

        with closing(sqlite3.connect(self.database_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(timetable_entries)"
                ).fetchall()
            }
            after = self._master_counts(connection)
        self.assertEqual(before, after)
        self.assertEqual(
            columns,
            {
                "timetable_entry_id",
                "weekday",
                "start_time",
                "end_time",
                "subject_id",
                "target_type",
                "target_id",
                "room",
                "active",
                "sort_order",
                "created_at",
                "updated_at",
                "deleted_at",
            },
        )

    def test_crud_sorting_and_reopen(self) -> None:
        later = self._save(weekday=2, start="10:00", end="10:45", room="Atelier")
        earlier = self._save(weekday=2, start="08:00", end="08:45")
        updated = self.adapter.save_entry(
            SaveTimetableEntryCommand(
                later.timetable_entry_id,
                2,
                "09:30",
                "10:15",
                self.subject_id,
                "group",
                self.group_id,
                "Raum 2",
                True,
                later.sort_order,
            )
        )

        reopened = TimetableDesktopAdapter(SQLiteDatabase(self.database_path))
        entries = reopened.week_view_model().days[1].entries

        self.assertEqual(
            tuple(item.timetable_entry_id for item in entries),
            (earlier.timetable_entry_id, updated.timetable_entry_id),
        )
        self.assertEqual(entries[1].room, "Raum 2")
        reopened.set_entry_active(earlier.timetable_entry_id, False)
        self.assertFalse(reopened.week_view_model().days[1].entries[0].active)
        reopened.delete_entry(updated.timetable_entry_id)
        self.assertEqual(len(reopened.week_view_model().days[1].entries), 1)
        replacement = reopened.save_entry(
            SaveTimetableEntryCommand(
                "",
                3,
                "08:00",
                "08:45",
                self.subject_id,
                "group",
                self.group_id,
                "",
                True,
            )
        )
        self.assertEqual(replacement.timetable_entry_id, "TTE-000003")
        with closing(sqlite3.connect(self.database_path)) as connection:
            deleted_at = connection.execute(
                """
                SELECT deleted_at FROM timetable_entries
                WHERE timetable_entry_id = ?
                """,
                (updated.timetable_entry_id,),
            ).fetchone()[0]
        self.assertTrue(deleted_at)

    def test_subject_options_and_validation_exclude_cross_curricular_domains(self) -> None:
        week = self.adapter.week_view_model()
        subject_ids = {option.item_id for option in week.subjects}

        self.assertTrue(
            subject_ids.isdisjoint(COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS)
        )
        self.assertEqual(
            len(subject_ids),
            10,
        )
        for subject_id in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS:
            with self.subTest(subject_id=subject_id):
                with self.assertRaisesRegex(
                    TimetableValidationError,
                    "Das ausgewählte Fach ist nicht mehr vorhanden",
                ):
                    self._save(
                        weekday=1,
                        start="08:00",
                        end="08:45",
                        subject_id=subject_id,
                    )

    def test_references_time_and_overlap_are_validated(self) -> None:
        self._save(weekday=1, start="08:00", end="09:00")
        with self.assertRaisesRegex(TimetableValidationError, "Beginn muss vor Ende"):
            self._save(weekday=1, start="10:00", end="10:00")
        with self.assertRaisesRegex(TimetableValidationError, "Fach"):
            self._save(
                weekday=1,
                start="10:00",
                end="11:00",
                subject_id="missing-subject",
            )
        with self.assertRaisesRegex(TimetableValidationError, "Ziel"):
            self._save(
                weekday=1,
                start="10:00",
                end="11:00",
                target_type="course",
                target_id=self.group_id,
            )
        with self.assertRaisesRegex(TimetableValidationError, "überschneidet"):
            self._save(weekday=1, start="08:30", end="09:30")

        inactive = self._save(
            weekday=1,
            start="08:30",
            end="09:30",
            active=False,
        )
        with self.assertRaisesRegex(TimetableValidationError, "überschneidet"):
            self.adapter.set_entry_active(inactive.timetable_entry_id, True)

    def test_projection_covers_day_gaps_end_week_and_disabled_entries(self) -> None:
        monday_first = self._save(weekday=1, start="08:00", end="08:45")
        monday_second = self._save(weekday=1, start="10:00", end="10:45")
        friday = self._save(weekday=5, start="09:00", end="09:45")
        self._save(
            weekday=1,
            start="09:00",
            end="09:30",
            active=False,
        )

        before = self.adapter.read_projection(datetime(2026, 7, 13, 7, 30))
        during = self.adapter.read_projection(datetime(2026, 7, 13, 8, 15))
        gap = self.adapter.read_projection(datetime(2026, 7, 13, 9, 0))
        exact_end = self.adapter.read_projection(datetime(2026, 7, 13, 8, 45))
        after = self.adapter.read_projection(datetime(2026, 7, 13, 11, 0))
        friday_after = self.adapter.read_projection(datetime(2026, 7, 17, 10, 0))
        sunday_midnight = self.adapter.read_projection(datetime(2026, 7, 19, 0, 0))

        self.assertIsNone(before.current)
        self.assertEqual(before.next.entry.timetable_entry_id, monday_first.timetable_entry_id)
        self.assertEqual(during.current.entry.timetable_entry_id, monday_first.timetable_entry_id)
        self.assertEqual(during.next.entry.timetable_entry_id, monday_second.timetable_entry_id)
        self.assertIsNone(gap.current)
        self.assertIsNone(exact_end.current)
        self.assertEqual(exact_end.next.entry.timetable_entry_id, monday_second.timetable_entry_id)
        self.assertEqual(gap.next.entry.timetable_entry_id, monday_second.timetable_entry_id)
        self.assertIsNone(after.current)
        self.assertEqual(after.next.entry.timetable_entry_id, friday.timetable_entry_id)
        self.assertEqual(
            friday_after.next.entry.timetable_entry_id,
            monday_first.timetable_entry_id,
        )
        self.assertEqual(friday_after.next.occurrence_date.isoformat(), "2026-07-20")
        self.assertEqual(sunday_midnight.next.occurrence_date.isoformat(), "2026-07-20")
        self.assertEqual(
            tuple(item.entry.timetable_entry_id for item in before.today),
            (monday_first.timetable_entry_id, monday_second.timetable_entry_id),
        )

    def test_day_without_lessons_has_no_current_and_keeps_next(self) -> None:
        friday = self._save(weekday=5, start="09:00", end="09:45")

        projection = self.adapter.read_projection(datetime(2026, 7, 15, 12, 0))

        self.assertIsNone(projection.current)
        self.assertEqual(projection.today, ())
        self.assertEqual(projection.next.entry.timetable_entry_id, friday.timetable_entry_id)

    def test_only_recurring_lesson_is_its_own_next_week_occurrence(self) -> None:
        monday = self._save(weekday=1, start="08:00", end="08:45")

        projection = self.adapter.read_projection(datetime(2026, 7, 13, 8, 15))

        self.assertEqual(projection.current.entry.timetable_entry_id, monday.timetable_entry_id)
        self.assertEqual(projection.next.entry.timetable_entry_id, monday.timetable_entry_id)
        self.assertEqual(projection.next.occurrence_date.isoformat(), "2026-07-20")

    def test_settings_week_switches_all_days_and_adds_to_selected_day(self) -> None:
        screen = SettingsScreen()
        screen.set_timetable(self.adapter.week_view_model())
        emitted_weekdays: list[int] = []
        screen.timetable_add_requested.connect(emitted_weekdays.append)

        empty = screen.findChild(QLabel, "TimetableEmptyState")
        tabs = screen.findChild(QTabBar)
        self.assertEqual(tabs.count(), 5)
        self.assertEqual(
            empty.text(),
            "Für Montag sind noch keine Stunden eingetragen. "
            "Über „Stunde hinzufügen“ kannst du den Tagesplan beginnen.",
        )
        self.assertFalse(empty.isHidden())
        for index, weekday in enumerate(range(1, 6)):
            tabs.setCurrentIndex(index)
            self.assertEqual(screen.selected_timetable_weekday, weekday)
        screen.timetable_add_button.click()
        self.assertEqual(emitted_weekdays, [5])

    def test_settings_shows_only_selected_day_in_chronological_wide_rows(self) -> None:
        later = self._save(weekday=1, start="10:00", end="10:45")
        earlier = self._save(weekday=1, start="08:00", end="08:45", active=False)
        self._save(weekday=2, start="09:00", end="09:45")
        screen = SettingsScreen()
        screen.resize(640, 700)
        screen.set_timetable(self.adapter.week_view_model())

        monday_rows = [
            screen.findChild(QFrame, f"TimetableEntry_{entry_id}")
            for entry_id in (earlier.timetable_entry_id, later.timetable_entry_id)
        ]
        self.assertTrue(all(row is not None for row in monday_rows))
        self.assertIsNotNone(monday_rows[0].graphicsEffect())
        self.assertIsNone(
            screen.findChild(QFrame, "TimetableEntry_TTE-000003")
        )
        self.assertFalse(screen.timetable_tabs.usesScrollButtons())
        markers = screen.findChildren(SubjectAccentMarker)
        self.assertEqual(len(markers), 2)
        self.assertTrue(all(
            marker.property("subjectId") == self.subject_id
            for marker in markers
        ))

    def test_dashboard_greeting_boundaries_with_and_without_display_name(self) -> None:
        self.assertEqual(dashboard_greeting(datetime(2026, 7, 17, 10, 59)), "Guten Morgen")
        self.assertEqual(dashboard_greeting(datetime(2026, 7, 17, 11, 0), "Laura"), "Guten Tag, Laura")
        self.assertEqual(dashboard_greeting(datetime(2026, 7, 17, 17, 59), "Łucja"), "Guten Tag, Łucja")
        self.assertEqual(dashboard_greeting(datetime(2026, 7, 17, 18, 0), "Laura"), "Guten Abend, Laura")

    def test_dashboard_projects_display_name_as_plain_text(self) -> None:
        screen = OverviewScreen()
        at = datetime(2026, 7, 17, 8, 0)
        screen.set_dashboard(
            self.adapter.read_projection(at),
            DashboardDocumentationHeatmapViewModel(()),
            at,
            False,
            (),
            "<b>Laura</b>",
        )
        self.assertEqual(screen.greeting_label.text(), "Guten Morgen, <b>Laura</b>")
        self.assertEqual(screen.greeting_label.textFormat(), Qt.TextFormat.PlainText)

    def _save(
        self,
        *,
        weekday: int,
        start: str,
        end: str,
        subject_id: str | None = None,
        target_type: str = "group",
        target_id: str | None = None,
        room: str = "",
        active: bool = True,
    ):
        return self.adapter.save_entry(
            SaveTimetableEntryCommand(
                "",
                weekday,
                start,
                end,
                subject_id or self.subject_id,
                target_type,
                target_id or self.group_id,
                room,
                active,
            )
        )

    @staticmethod
    def _master_counts(connection: sqlite3.Connection) -> tuple[int, int, int, int]:
        return tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("groups", "courses", "course_groups", "competencies")
        )
