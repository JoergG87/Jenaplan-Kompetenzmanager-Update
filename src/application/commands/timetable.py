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


class TimetableApplicationService:
    """Expose timetable writes and reads to adapters."""

    def __init__(
        self,
        domain_service: TimetableService,
        repository: TimetableRepository,
    ) -> None:
        self.domain_service = domain_service
        self.repository = repository

    def save(self, command: SaveTimetableEntryCommand) -> TimetableEntry:
        if not command.timetable_entry_id:
            return self.domain_service.create_entry(
                weekday=command.weekday,
                start_time=command.start_time,
                end_time=command.end_time,
                subject_id=command.subject_id,
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
            )
        )

    def delete(self, timetable_entry_id: str) -> None:
        self.domain_service.delete_entry(timetable_entry_id.strip())

    def list_entries(self) -> tuple[TimetableEntry, ...]:
        return self.repository.list_entries()

    def projection(self, at: datetime) -> TimetableProjection:
        return build_timetable_projection(self.repository.list_entries(), at)
