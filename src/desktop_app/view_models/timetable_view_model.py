"""Display projections for the productive weekly timetable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


WEEKDAY_LABELS = {
    1: "Montag",
    2: "Dienstag",
    3: "Mittwoch",
    4: "Donnerstag",
    5: "Freitag",
}
TARGET_TYPE_LABELS = {
    "group": "Stammgruppe",
    "course": "Kurs",
    "course_group": "Kursverbund",
}


@dataclass(frozen=True)
class TimetableOptionViewModel:
    """Technical ID and calm visible label for one choice."""

    item_id: str
    label: str


@dataclass(frozen=True)
class TimetableEntryViewModel:
    """Display-ready timetable row retaining all editable technical values."""

    timetable_entry_id: str
    weekday: int
    start_time: str
    end_time: str
    subject_id: str
    subject_label: str
    target_type: str
    target_id: str
    target_label: str
    room: str
    active: bool
    sort_order: int

    @property
    def time_label(self) -> str:
        return f"{self.start_time}–{self.end_time}"

    @property
    def target_type_label(self) -> str:
        return TARGET_TYPE_LABELS.get(self.target_type, self.target_type)


@dataclass(frozen=True)
class TimetableDayViewModel:
    """One weekday column/card in the settings projection."""

    weekday: int
    label: str
    entries: tuple[TimetableEntryViewModel, ...]


@dataclass(frozen=True)
class TimetableWeekViewModel:
    """Complete settings projection and dialog option sources."""

    days: tuple[TimetableDayViewModel, ...]
    subjects: tuple[TimetableOptionViewModel, ...]
    targets_by_type: dict[str, tuple[TimetableOptionViewModel, ...]]

    @property
    def is_empty(self) -> bool:
        return not any(day.entries for day in self.days)


@dataclass(frozen=True)
class TimetableOccurrenceViewModel:
    """Dated, display-ready occurrence for dashboard consumers."""

    entry: TimetableEntryViewModel
    occurrence_date: date
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class TimetableReadProjectionViewModel:
    """Canonical UI read model for current, next and today's lessons."""

    current: TimetableOccurrenceViewModel | None
    next: TimetableOccurrenceViewModel | None
    today: tuple[TimetableOccurrenceViewModel, ...]
