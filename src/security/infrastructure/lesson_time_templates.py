"""Isolated cipher persistence. No product/UI composition admits the target yet."""
from contextlib import closing

from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.lesson_time_templates import LessonTimeTemplate
from src.core.lesson_times_schema import SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION


class SQLiteLessonTimeTemplateRepository:
    def __init__(self, connection_factory):
        self._connect = connection_factory

    @staticmethod
    def _require_target(connection):
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        target = SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity
        if (str(connection.execute("PRAGMA cipher_status").fetchone()[0]) != "1"
                or result.version.sqlite_user_version != target.schema_version
                or result.schema_identity.fingerprint != target.fingerprint):
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
