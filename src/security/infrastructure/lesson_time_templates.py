"""Isolated cipher persistence. No product/UI composition admits the target yet."""
from contextlib import closing

from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.lesson_time_templates import LessonTimeTemplate, LessonTimeTemplateError
from src.core.lesson_times_schema import SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION


class SQLiteLessonTimeTemplateRepository:
    def __init__(self, connection_factory):
        self._connect = connection_factory

    @staticmethod
    def _require_target(connection):
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        targets = (SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity,
            SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity)
        if (str(connection.execute("PRAGMA cipher_status").fetchone()[0]) != "1"
                or not any(result.version.sqlite_user_version == target.schema_version
                    and result.schema_identity.fingerprint == target.fingerprint for target in targets)):
            raise ValueError("lesson_times_encrypted_target_required")

    def list_templates(self) -> tuple[LessonTimeTemplate, ...]:
        with closing(self._connect()) as connection:
            self._require_target(connection)
            return tuple(LessonTimeTemplate(*row) for row in connection.execute(
                "SELECT lesson_number, start_time, end_time FROM lesson_time_templates ORDER BY lesson_number"))

    def save(self, template: LessonTimeTemplate) -> None:
        with closing(self._connect()) as connection:
            self._require_target(connection)
            with connection:
                connection.execute(
                    "INSERT INTO lesson_time_templates(lesson_number,start_time,end_time) VALUES (?,?,?) "
                    "ON CONFLICT(lesson_number) DO UPDATE SET start_time=excluded.start_time,end_time=excluded.end_time",
                    (template.lesson_number, template.start_time, template.end_time))

    def save_if_unchanged(self, template: LessonTimeTemplate,
                          expected: LessonTimeTemplate | None) -> None:
        """Compare and write atomically; a new number never overwrites a row."""
        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._require_target(connection)
                row = connection.execute(
                    "SELECT lesson_number,start_time,end_time FROM lesson_time_templates WHERE lesson_number=?",
                    (template.lesson_number,),
                ).fetchone()
                actual = LessonTimeTemplate(*row) if row is not None else None
                if actual != expected:
                    raise LessonTimeTemplateError(
                        "Diese Unterrichtszeit wurde inzwischen geändert. Bitte gespeicherte Zeiten neu laden.")
                connection.execute(
                    "INSERT INTO lesson_time_templates(lesson_number,start_time,end_time) VALUES (?,?,?) "
                    "ON CONFLICT(lesson_number) DO UPDATE SET start_time=excluded.start_time,end_time=excluded.end_time",
                    (template.lesson_number, template.start_time, template.end_time))
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
