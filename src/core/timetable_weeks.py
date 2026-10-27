"""Calendar rules for the encrypted recurring two-week timetable."""
from dataclasses import dataclass
from datetime import date, timedelta


def iso_week_monday(value: date) -> date:
    return value - timedelta(days=value.isoweekday() - 1)


def _kind(value):
    if value not in ("A", "B"):
        raise ValueError("Bitte A oder B auswählen.")
    return value


@dataclass(frozen=True)
class TimetableWeekAssignment:
    monday: date
    automatic_kind: str | None
    effective_kind: str | None
    manual: bool = False

    @property
    def label(self):
        year, week, _ = self.monday.isocalendar()
        if self.effective_kind is None:
            return f"KW {week:02d} / {year} · A-/B-Rhythmus noch nicht eingerichtet"
        source = "manuell" if self.manual else "automatisch"
        return f"KW {week:02d} / {year} · {self.effective_kind}-Woche · {source}"


@dataclass(frozen=True)
class TimetableWeekCycle:
    reference_monday: date
    reference_kind: str

    def __post_init__(self):
        object.__setattr__(self, "reference_monday", iso_week_monday(self.reference_monday))
        _kind(self.reference_kind)

    def assignment(self, value: date, overrides=()):
        monday = iso_week_monday(value)
        weeks = (monday - self.reference_monday).days // 7
        automatic = self.reference_kind if weeks % 2 == 0 else ("B" if self.reference_kind == "A" else "A")
        manual = dict(overrides).get(monday)
        if manual is not None:
            _kind(manual)
        return TimetableWeekAssignment(monday, automatic, manual or automatic, manual is not None)


def verify_timetable_weeks(connection):
    """Independent read-only calendar content verification for restart/restore."""
    rows = connection.execute("SELECT singleton_id, reference_monday, reference_kind FROM timetable_week_cycle").fetchall()
    if len(rows) > 1 or (rows and rows[0][0] != 1):
        raise ValueError("Ungültige Wochenreferenz.")
    def monday(text):
        value = date.fromisoformat(text)
        if value.isoformat() != text or iso_week_monday(value) != value:
            raise ValueError("Ungültige ISO-Woche.")
        return value
    if rows:
        TimetableWeekCycle(monday(rows[0][1]), rows[0][2])
    for value, kind in connection.execute("SELECT week_monday, week_kind FROM timetable_week_overrides"):
        monday(value); _kind(kind)
        if not rows:
            raise ValueError("Wochenkorrektur ohne Referenz.")
    for (pattern,) in connection.execute("SELECT week_pattern FROM timetable_entries"):
        if pattern not in ("all", "A", "B") or (pattern != "all" and not rows):
            raise ValueError("Ungültige Wochengültigkeit.")
