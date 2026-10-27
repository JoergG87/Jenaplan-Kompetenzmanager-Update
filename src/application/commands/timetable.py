"""Application boundary for timetable commands and canonical queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.timetable import (
    TimetableEntry,
    TimetableProjection,
    TimetableRepository,
    TimetableService,
    build_timetable_projection,
)


@dataclass(frozen=True)
class SaveTimetableEntryCommand:
    """Create or replace one timetable entry."""

    timetable_entry_id: str
    weekday: int
    start_time: str
    end_time: str
    subject_id: str
    target_type: str
    target_id: str
    room: str
    active: bool
    sort_order: int = 0
    entry_kind: str = "subject_lesson"
    subject_ids: tuple[str, ...] = ()
    week_pattern: str = "all"


class TimetableApplicationService:
    """Expose timetable writes and reads to adapters."""

    def __init__(
        self,
        domain_service: TimetableService,
        repository: TimetableRepository,
        week_repository=None,
    ) -> None:
        self.domain_service = domain_service
        self.repository = repository
        self.week_repository = week_repository

    def save(self, command: SaveTimetableEntryCommand) -> TimetableEntry:
        if not command.timetable_entry_id:
            return self.domain_service.create_entry(
                weekday=command.weekday,
                start_time=command.start_time,
                end_time=command.end_time,
                subject_id=command.subject_id,
                entry_kind=command.entry_kind,
                subject_ids=command.subject_ids,
                week_pattern=command.week_pattern,
                target_type=command.target_type,
                target_id=command.target_id,
                room=command.room,
                active=command.active,
                sort_order=None,
            )
        existing = self.repository.get_entry(command.timetable_entry_id)
        if existing is None:
            raise ValueError("Der Stundenplaneintrag wurde nicht gefunden.")
        return self.domain_service.update_entry(
            TimetableEntry(
                command.timetable_entry_id,
                command.weekday,
                command.start_time,
                command.end_time,
                command.subject_id,
                command.target_type,
                command.target_id,
                command.room,
                command.active,
                command.sort_order,
                existing.created_at,
                existing.updated_at,
                entry_kind=command.entry_kind,
                subject_ids=command.subject_ids,
                week_pattern=command.week_pattern,
            )
        )

    def delete(self, timetable_entry_id: str) -> None:
        self.domain_service.delete_entry(timetable_entry_id.strip())

    def list_entries(self) -> tuple[TimetableEntry, ...]:
        return self.repository.list_entries()

    def projection(self, at: datetime) -> TimetableProjection:
        weeks = self.week_repository
        cycle, overrides = weeks.snapshot() if weeks else (None, ())
        # Each correction can suppress at most one scheduled week. Search a
        # complete cycle per exception, including week wrap.
        search_days = 15 + 14 * len(overrides)
        kinds = (lambda value: cycle.assignment(value, overrides).effective_kind) if cycle else None
        return build_timetable_projection(self.repository.list_entries(), at, kinds, search_days=search_days)
