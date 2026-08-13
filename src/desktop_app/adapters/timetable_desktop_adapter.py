"""Desktop adapter for timetable settings and canonical reads."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.commands.timetable import (
    SaveTimetableEntryCommand,
    TimetableApplicationService,
)
from src.core.maintenance_gate import product_writer
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    SQLiteMasterDataRepository,
    SQLiteTimetableRepository,
)
from src.core.timetable import TimetableEntry, TimetableService, TimetableValidator
from src.desktop_app.view_models.timetable_view_model import (
    WEEKDAY_LABELS,
    TimetableDayViewModel,
    TimetableEntryViewModel,
    TimetableOccurrenceViewModel,
    TimetableOptionViewModel,
    TimetableReadProjectionViewModel,
    TimetableWeekViewModel,
)
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS,
)


class TimetableDesktopAdapter:
    """Translate widget requests to the application and domain layers."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self.repository = SQLiteTimetableRepository(database)
        self.master_data_repository = SQLiteMasterDataRepository(database)
        self.competency_repository = SQLiteCompetencyRepository(database)
        domain_service = TimetableService(
            self.repository,
            TimetableValidator(),
            self._valid_subject_ids,
            self._valid_target_ids,
            lambda: datetime.now(UTC),
        )
        self.application_service = TimetableApplicationService(
            domain_service,
            self.repository,
        )

    def week_view_model(self) -> TimetableWeekViewModel:
        """Return the complete Monday-to-Friday settings projection."""
        entries = self.application_service.list_entries()
        return TimetableWeekViewModel(
            days=tuple(
                TimetableDayViewModel(
                    weekday,
                    WEEKDAY_LABELS[weekday],
                    tuple(
                        self._entry_view_model(entry)
                        for entry in entries
                        if entry.weekday == weekday
                    ),
                )
                for weekday in range(1, 6)
            ),
            subjects=self._subject_options(),
            targets_by_type=self._target_options(),
        )

    @product_writer
    def save_entry(self, command: SaveTimetableEntryCommand) -> TimetableEntryViewModel:
        """Create or update one validated entry."""
        return self._entry_view_model(self.application_service.save(command))

    @product_writer
    def set_entry_active(
        self,
        timetable_entry_id: str,
        active: bool,
    ) -> TimetableEntryViewModel:
        """Activate or deactivate an entry through the same validation path."""
        existing = self.repository.get_entry(timetable_entry_id)
        if existing is None:
            raise ValueError("Der Stundenplaneintrag wurde nicht gefunden.")
        return self.save_entry(
            SaveTimetableEntryCommand(
                existing.timetable_entry_id,
                existing.weekday,
                existing.start_time,
                existing.end_time,
                existing.subject_id,
                existing.target_type,
                existing.target_id,
                existing.room,
                active,
                existing.sort_order,
            )
        )

    @product_writer
    def delete_entry(self, timetable_entry_id: str) -> None:
        """Delete the explicitly selected timetable entry."""
        self.application_service.delete(timetable_entry_id)

    def read_projection(self, at: datetime) -> TimetableReadProjectionViewModel:
        """Return the sole display-ready current/next/today projection."""
        projection = self.application_service.projection(at)

        def occurrence_view_model(occurrence: object) -> TimetableOccurrenceViewModel:
            return TimetableOccurrenceViewModel(
                self._entry_view_model(occurrence.entry),
                occurrence.occurrence_date,
                occurrence.starts_at,
                occurrence.ends_at,
            )

        return TimetableReadProjectionViewModel(
            occurrence_view_model(projection.current) if projection.current else None,
            occurrence_view_model(projection.next) if projection.next else None,
            tuple(occurrence_view_model(item) for item in projection.today),
        )

    def _entry_view_model(self, entry: TimetableEntry) -> TimetableEntryViewModel:
        subjects = dict((item.item_id, item.label) for item in self._subject_options())
        targets = {
            target_type: dict((item.item_id, item.label) for item in options)
            for target_type, options in self._target_options().items()
        }
        return TimetableEntryViewModel(
            entry.timetable_entry_id,
            entry.weekday,
            entry.start_time,
            entry.end_time,
            entry.subject_id,
            subjects.get(entry.subject_id, entry.subject_id),
            entry.target_type,
            entry.target_id,
            targets.get(entry.target_type, {}).get(entry.target_id, entry.target_id),
            entry.room,
            entry.active,
            entry.sort_order,
        )

    def _subject_options(self) -> tuple[TimetableOptionViewModel, ...]:
        labels: dict[str, str] = {}
        sort_order: dict[str, int] = {}
        for competency in self.competency_repository.list_competencies():
            if competency.subject_id in COMPETENCY_CROSS_CURRICULAR_SUBJECT_KEYS:
                continue
            labels.setdefault(competency.subject_id, competency.subject_name)
            sort_order[competency.subject_id] = min(
                sort_order.get(competency.subject_id, competency.sort_order),
                competency.sort_order,
            )
        return tuple(
            TimetableOptionViewModel(subject_id, labels[subject_id])
            for subject_id in sorted(
                labels,
                key=lambda value: (sort_order[value], labels[value].casefold(), value),
            )
        )

    def _target_options(
        self,
    ) -> dict[str, tuple[TimetableOptionViewModel, ...]]:
        return {
            "group": tuple(
                TimetableOptionViewModel(item.group_id, item.group_name)
                for item in self.master_data_repository.list_student_groups()
                if item.active
            ),
            "course": tuple(
                TimetableOptionViewModel(item.course_id, item.course_name)
                for item in self.master_data_repository.list_courses()
                if item.active
            ),
            "course_group": tuple(
                TimetableOptionViewModel(item.course_group_id, item.name)
                for item in self.master_data_repository.list_course_groups()
                if item.active
            ),
        }

    def _valid_subject_ids(self) -> tuple[str, ...]:
        return tuple(option.item_id for option in self._subject_options())

    def _valid_target_ids(self) -> dict[str, tuple[str, ...]]:
        return {
            "group": tuple(
                item.group_id
                for item in self.master_data_repository.list_student_groups()
            ),
            "course": tuple(
                item.course_id for item in self.master_data_repository.list_courses()
            ),
            "course_group": tuple(
                item.course_group_id
                for item in self.master_data_repository.list_course_groups()
            ),
        }
