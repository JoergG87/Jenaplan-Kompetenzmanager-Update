"""Domain model and canonical read projection for the weekly timetable."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Protocol


TIMETABLE_ENTRY_ID_PREFIX = "TTE-"
TIMETABLE_TARGET_TYPES = ("group", "course", "course_group")


class TimetableValidationError(ValueError):
    """Raised when a timetable entry violates a business rule."""


@dataclass(frozen=True)
class TimetableEntry:
    """One persisted lesson in the recurring Monday-to-Friday timetable."""

    timetable_entry_id: str
    weekday: int
    start_time: str
    end_time: str
    subject_id: str
    target_type: str
    target_id: str
    room: str
    active: bool
    sort_order: int
    created_at: str
    updated_at: str
    deleted_at: str = ""


@dataclass(frozen=True)
class TimetableOccurrence:
    """One dated occurrence of a recurring timetable entry."""

    entry: TimetableEntry
    occurrence_date: date
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class TimetableProjection:
    """Canonical read result for one explicit point in time."""

    current: TimetableOccurrence | None
    next: TimetableOccurrence | None
    today: tuple[TimetableOccurrence, ...]


class TimetableRepository(Protocol):
    """Persistence contract required by the domain service."""

    def list_entries(self) -> tuple[TimetableEntry, ...]: ...
    def get_entry(self, timetable_entry_id: str) -> TimetableEntry | None: ...
    def create_entry(self, entry: TimetableEntry) -> TimetableEntry: ...
    def update_entry(self, entry: TimetableEntry) -> TimetableEntry: ...
    def next_timetable_entry_id(self) -> str: ...
    def next_sort_order(self, weekday: int) -> int: ...


class TimetableValidator:
    """Validate timetable fields, references and active overlaps."""

    def validate(
        self,
        entry: TimetableEntry,
        *,
        valid_subject_ids: Iterable[str],
        valid_target_ids: dict[str, Iterable[str]],
        existing_entries: Iterable[TimetableEntry],
    ) -> None:
        if entry.weekday not in range(1, 6):
            raise TimetableValidationError("Wochentag muss Montag bis Freitag sein.")
        start = self.parse_time(entry.start_time, "Beginn")
        end = self.parse_time(entry.end_time, "Ende")
        if start >= end:
            raise TimetableValidationError("Beginn muss vor Ende liegen.")
        if entry.subject_id not in set(valid_subject_ids):
            raise TimetableValidationError("Das ausgewählte Fach ist nicht mehr vorhanden.")
        if entry.target_type not in TIMETABLE_TARGET_TYPES:
            raise TimetableValidationError("Unbekannte Zielart.")
        if entry.target_id not in set(valid_target_ids.get(entry.target_type, ())):
            raise TimetableValidationError(
                "Das ausgewählte Ziel passt nicht zur Zielart oder ist nicht mehr vorhanden."
            )
        if entry.sort_order < 0:
            raise TimetableValidationError("Sortierung darf nicht negativ sein.")
        if not entry.active:
            return
        for existing in existing_entries:
            if (
                not existing.active
                or existing.timetable_entry_id == entry.timetable_entry_id
                or existing.weekday != entry.weekday
            ):
                continue
            existing_start = self.parse_time(existing.start_time, "Beginn")
            existing_end = self.parse_time(existing.end_time, "Ende")
            if start < existing_end and end > existing_start:
                raise TimetableValidationError(
                    "Der Eintrag überschneidet sich mit "
                    f"{existing.start_time}–{existing.end_time}."
                )

    @staticmethod
    def parse_time(value: str, label: str) -> time:
        try:
            return time.fromisoformat(value.strip())
        except (TypeError, ValueError, AttributeError) as error:
            raise TimetableValidationError(
                f"{label} muss als gültige Uhrzeit angegeben werden."
            ) from error


class TimetableService:
    """Coordinate timetable writes while keeping rules outside UI and storage."""

    def __init__(
        self,
        repository: TimetableRepository,
        validator: TimetableValidator,
        subject_ids_provider: Callable[[], Iterable[str]],
        target_ids_provider: Callable[[], dict[str, Iterable[str]]],
        now_provider: Callable[[], datetime],
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.subject_ids_provider = subject_ids_provider
        self.target_ids_provider = target_ids_provider
        self.now_provider = now_provider

    def create_entry(
        self,
        *,
        weekday: int,
        start_time: str,
        end_time: str,
        subject_id: str,
        target_type: str,
        target_id: str,
        room: str = "",
        active: bool = True,
        sort_order: int | None = None,
    ) -> TimetableEntry:
        timestamp = self.now_provider().isoformat(timespec="seconds")
        entry = TimetableEntry(
            self.repository.next_timetable_entry_id(),
            weekday,
            start_time.strip(),
            end_time.strip(),
            subject_id.strip(),
            target_type.strip(),
            target_id.strip(),
            room.strip(),
            active,
            self.repository.next_sort_order(weekday) if sort_order is None else sort_order,
            timestamp,
            timestamp,
        )
        self._validate(entry)
        return self.repository.create_entry(entry)

    def update_entry(self, entry: TimetableEntry) -> TimetableEntry:
        existing = self.repository.get_entry(entry.timetable_entry_id)
        if existing is None:
            raise TimetableValidationError("Der Stundenplaneintrag wurde nicht gefunden.")
        updated = replace(
            entry,
            start_time=entry.start_time.strip(),
            end_time=entry.end_time.strip(),
            subject_id=entry.subject_id.strip(),
            target_type=entry.target_type.strip(),
            target_id=entry.target_id.strip(),
            room=entry.room.strip(),
            created_at=existing.created_at,
            updated_at=self.now_provider().isoformat(timespec="seconds"),
        )
        self._validate(updated)
        return self.repository.update_entry(updated)

    def delete_entry(self, timetable_entry_id: str) -> None:
        existing = self.repository.get_entry(timetable_entry_id)
        if existing is None:
            raise TimetableValidationError("Der Stundenplaneintrag wurde nicht gefunden.")
        timestamp = self.now_provider().isoformat(timespec="seconds")
        self.repository.update_entry(
            replace(
                existing,
                active=False,
                updated_at=timestamp,
                deleted_at=timestamp,
            )
        )

    def _validate(self, entry: TimetableEntry) -> None:
        self.validator.validate(
            entry,
            valid_subject_ids=self.subject_ids_provider(),
            valid_target_ids=self.target_ids_provider(),
            existing_entries=self.repository.list_entries(),
        )


def build_timetable_projection(
    entries: Iterable[TimetableEntry],
    at: datetime,
) -> TimetableProjection:
    """Return current, next and today's active lessons for an explicit time."""
    active_entries = tuple(entry for entry in entries if entry.active)
    today = tuple(
        _occurrence(entry, at.date(), at)
        for entry in sorted(active_entries, key=_entry_sort_key)
        if entry.weekday == at.isoweekday()
    )
    current = next(
        (item for item in today if item.starts_at <= at < item.ends_at),
        None,
    )
    next_occurrence: TimetableOccurrence | None = None
    for day_offset in range(0, 8):
        occurrence_date = at.date() + timedelta(days=day_offset)
        weekday = occurrence_date.isoweekday()
        if weekday > 5:
            continue
        for entry in sorted(active_entries, key=_entry_sort_key):
            if entry.weekday != weekday:
                continue
            occurrence = _occurrence(entry, occurrence_date, at)
            is_same_occurrence = (
                current is not None
                and occurrence.entry.timetable_entry_id
                == current.entry.timetable_entry_id
                and occurrence.starts_at == current.starts_at
            )
            if occurrence.starts_at >= at and not is_same_occurrence:
                next_occurrence = occurrence
                break
        if next_occurrence is not None:
            break
    return TimetableProjection(current, next_occurrence, today)


def _occurrence(
    entry: TimetableEntry,
    occurrence_date: date,
    reference: datetime,
) -> TimetableOccurrence:
    start = TimetableValidator.parse_time(entry.start_time, "Beginn")
    end = TimetableValidator.parse_time(entry.end_time, "Ende")
    return TimetableOccurrence(
        entry,
        occurrence_date,
        datetime.combine(occurrence_date, start, tzinfo=reference.tzinfo),
        datetime.combine(occurrence_date, end, tzinfo=reference.tzinfo),
    )


def _entry_sort_key(entry: TimetableEntry) -> tuple[int, str, str, int, str]:
    return (
        entry.weekday,
        entry.start_time,
        entry.end_time,
        entry.sort_order,
        entry.timetable_entry_id,
    )
