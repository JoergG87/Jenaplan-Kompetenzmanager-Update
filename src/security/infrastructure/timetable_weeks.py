"""Encrypted Main repository; never AppPreferences."""
from contextlib import closing, nullcontext
from datetime import date
from src.core.timetable_weeks import TimetableWeekCycle, TimetableWeekAssignment, iso_week_monday, _kind, verify_timetable_weeks


class SQLiteTimetableWeekRepository:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def supports_connection(connection):
        from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION
        from src.core.database_compatibility import DatabaseCompatibilityInspector
        identity = SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity
        return (connection.execute("PRAGMA user_version").fetchone()[0] == identity.schema_version
            and DatabaseCompatibilityInspector.schema_identity_for_connection(connection).fingerprint == identity.fingerprint)

    @property
    def supported(self):
        with closing(self.database.connect()) as connection:
            return self.supports_connection(connection)

    def snapshot(self, *, connection=None):
        owned = connection is None
        with (closing(self.database.connect()) if owned else nullcontext(connection)) as connection:
            if not self.supports_connection(connection):
                return None, ()
            with (connection if owned else nullcontext()):
                if owned:
                    connection.execute("BEGIN")
                verify_timetable_weeks(connection)
                row = connection.execute("SELECT reference_monday,reference_kind FROM timetable_week_cycle WHERE singleton_id=1").fetchone()
                overrides = tuple((date.fromisoformat(r[0]), r[1]) for r in connection.execute("SELECT week_monday,week_kind FROM timetable_week_overrides"))
                return (TimetableWeekCycle(date.fromisoformat(row[0]), row[1]) if row else None), overrides

    def assignment(self, value):
        cycle, overrides = self.snapshot()
        return cycle.assignment(value, overrides) if cycle else TimetableWeekAssignment(iso_week_monday(value), None, None)

    def configure(self, value, kind):
        cycle = TimetableWeekCycle(value, kind)
        self._write("INSERT INTO timetable_week_cycle VALUES (1,?,?) ON CONFLICT(singleton_id) DO UPDATE SET reference_monday=excluded.reference_monday, reference_kind=excluded.reference_kind",
            (cycle.reference_monday.isoformat(), cycle.reference_kind))

    def set_override(self, value, kind):
        self._write("INSERT INTO timetable_week_overrides VALUES (?,?) ON CONFLICT(week_monday) DO UPDATE SET week_kind=excluded.week_kind",
            (iso_week_monday(value).isoformat(), _kind(kind)))

    def clear_override(self, value):
        self._write("DELETE FROM timetable_week_overrides WHERE week_monday=?", (iso_week_monday(value).isoformat(),))

    def _write(self, sql, values):
        with closing(self.database.connect()) as connection:
            if not self.supports_connection(connection):
                raise ValueError("A-/B-Wochen benötigen die freigegebene Testinstallation.")
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(sql, values)
                verify_timetable_weeks(connection)
