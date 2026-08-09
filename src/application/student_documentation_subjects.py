"""Qt-free application contract for student documentation subjects."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import sqlite3

from src.core.sqlite_student_documentation_subjects import (
    SQLiteStudentDocumentationSubjectRepository,
    StudentDocumentationSubjectRepositoryError,
)
from src.core.student_documentation_subjects import (
    DocumentationSubjectMode,
    DocumentationSubjectWriteResult,
    DocumentationSubjectWriteStatus,
    StudentDocumentationSubjectConfiguration,
)


ConnectionFactory = Callable[[], sqlite3.Connection]
TimestampProvider = Callable[[], datetime]
FaultHook = Callable[[str], None]


class StudentDocumentationSubjectApplicationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class StudentDocumentationSubjectService:
    """Read and atomically replace student/year documentation subjects."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        now_provider: TimestampProvider | None = None,
        fault_hook: FaultHook | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._fault_hook = fault_hook

    def configuration(
        self,
        student_id: str,
        school_year_id: str,
    ) -> StudentDocumentationSubjectConfiguration:
        student, school_year = _validated_ids(student_id, school_year_id)
        with _read_snapshot(self._connection_factory) as connection:
            repository = SQLiteStudentDocumentationSubjectRepository(connection)
            _require_read_references(repository, student, school_year)
            return repository.configuration(student, school_year)

    def effective_documentation_subjects(
        self,
        student_id: str,
        school_year_id: str,
    ) -> tuple[str, ...]:
        student, school_year = _validated_ids(student_id, school_year_id)
        with _read_snapshot(self._connection_factory) as connection:
            repository = SQLiteStudentDocumentationSubjectRepository(connection)
            _require_read_references(repository, student, school_year)
            configuration = repository.configuration(student, school_year)
            return effective_documentation_subjects(
                configuration,
                repository.global_documentation_subject_ids(),
                known_subject_ids=(
                    subject_id
                    for subject_id in configuration.selected_subject_ids
                    if repository.subject_state(subject_id) is not None
                ),
            )

    def set_mode(
        self,
        student_id: str,
        school_year_id: str,
        mode: DocumentationSubjectMode | str,
    ) -> DocumentationSubjectWriteResult:
        student, school_year = _validated_ids(student_id, school_year_id)
        requested_mode = _require_mode(mode)
        timestamp = _require_timestamp(self._now_provider())

        def operation(
            repository: SQLiteStudentDocumentationSubjectRepository,
        ) -> DocumentationSubjectWriteResult:
            _require_write_references(repository, student, school_year)
            before = repository.configuration(student, school_year)
            if before.mode is requested_mode:
                return DocumentationSubjectWriteResult(
                    DocumentationSubjectWriteStatus.NO_CHANGE,
                    before,
                )
            if requested_mode is DocumentationSubjectMode.INHERIT:
                repository.replace_selections(student, school_year, ())
            if before.profile is None:
                repository.insert_profile(
                    student,
                    school_year,
                    requested_mode,
                    timestamp,
                )
            else:
                repository.update_profile_mode(
                    student,
                    school_year,
                    requested_mode,
                    timestamp,
                )
            _call_fault_hook(self._fault_hook, "after_subject_profile_write")
            return DocumentationSubjectWriteResult(
                DocumentationSubjectWriteStatus.CHANGED,
                repository.configuration(student, school_year),
            )

        return _write_transaction(self._connection_factory, operation)

    def replace_custom_subjects(
        self,
        student_id: str,
        school_year_id: str,
        subject_ids: Iterable[str],
    ) -> DocumentationSubjectWriteResult:
        student, school_year = _validated_ids(student_id, school_year_id)
        requested = _require_subject_ids(subject_ids)
        timestamp = _require_timestamp(self._now_provider())

        def operation(
            repository: SQLiteStudentDocumentationSubjectRepository,
        ) -> DocumentationSubjectWriteResult:
            _require_write_references(repository, student, school_year)
            for subject_id in requested:
                state = repository.subject_state(subject_id)
                if state is None:
                    raise StudentDocumentationSubjectApplicationError(
                        "documentation_subject_unknown"
                    )
                if not state[0]:
                    raise StudentDocumentationSubjectApplicationError(
                        "documentation_subject_inactive"
                    )
            ordered = repository.sort_subject_ids(requested)
            before = repository.configuration(student, school_year)
            if (
                before.mode is DocumentationSubjectMode.CUSTOM
                and before.selected_subject_ids == ordered
            ):
                return DocumentationSubjectWriteResult(
                    DocumentationSubjectWriteStatus.NO_CHANGE,
                    before,
                )
            if before.profile is None:
                repository.insert_profile(
                    student,
                    school_year,
                    DocumentationSubjectMode.CUSTOM,
                    timestamp,
                )
            elif before.mode is not DocumentationSubjectMode.CUSTOM:
                repository.update_profile_mode(
                    student,
                    school_year,
                    DocumentationSubjectMode.CUSTOM,
                    timestamp,
                )
            repository.replace_selections(student, school_year, ordered)
            if before.profile is not None and before.mode is DocumentationSubjectMode.CUSTOM:
                repository.update_profile_mode(
                    student,
                    school_year,
                    DocumentationSubjectMode.CUSTOM,
                    timestamp,
                )
            _call_fault_hook(self._fault_hook, "after_custom_subjects_replace")
            return DocumentationSubjectWriteResult(
                DocumentationSubjectWriteStatus.CHANGED,
                repository.configuration(student, school_year),
            )

        return _write_transaction(self._connection_factory, operation)


def effective_documentation_subjects(
    configuration: StudentDocumentationSubjectConfiguration,
    global_subject_ids: Iterable[str],
    *,
    known_subject_ids: Iterable[str] | None = None,
) -> tuple[str, ...]:
    """Resolve one already ordered snapshot without introducing a second policy."""
    if configuration.mode is DocumentationSubjectMode.INHERIT:
        return tuple(global_subject_ids)
    selected = configuration.selected_subject_ids
    if known_subject_ids is not None and set(selected) - set(known_subject_ids):
        raise StudentDocumentationSubjectApplicationError(
            "documentation_subject_configuration_invalid"
        )
    return selected


def _validated_ids(student_id: str, school_year_id: str) -> tuple[str, str]:
    return (
        _require_identifier(student_id, "student_id_invalid"),
        _require_identifier(school_year_id, "school_year_id_invalid"),
    )


def _require_identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise StudentDocumentationSubjectApplicationError(code)
    return value


def _require_mode(value: DocumentationSubjectMode | str) -> DocumentationSubjectMode:
    try:
        return DocumentationSubjectMode(value)
    except (TypeError, ValueError):
        raise StudentDocumentationSubjectApplicationError(
            "documentation_subject_mode_invalid"
        ) from None


def _require_subject_ids(subject_ids: Iterable[str]) -> tuple[str, ...]:
    try:
        values = tuple(subject_ids)
    except TypeError:
        raise StudentDocumentationSubjectApplicationError(
            "documentation_subject_ids_invalid"
        ) from None
    normalized = tuple(
        _require_identifier(value, "documentation_subject_id_invalid")
        for value in values
    )
    return tuple(dict.fromkeys(normalized))


def _require_timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise StudentDocumentationSubjectApplicationError(
            "documentation_subject_timestamp_invalid"
        )
    return value


def _require_read_references(
    repository: SQLiteStudentDocumentationSubjectRepository,
    student_id: str,
    school_year_id: str,
) -> None:
    if repository.student_state(student_id) is None:
        raise StudentDocumentationSubjectApplicationError("student_unknown")
    if repository.school_year_status(school_year_id) is None:
        raise StudentDocumentationSubjectApplicationError("school_year_unknown")


def _require_write_references(
    repository: SQLiteStudentDocumentationSubjectRepository,
    student_id: str,
    school_year_id: str,
) -> None:
    student_state = repository.student_state(student_id)
    if student_state is None:
        raise StudentDocumentationSubjectApplicationError("student_unknown")
    if not student_state[0] or student_state[1] is not None:
        raise StudentDocumentationSubjectApplicationError("student_read_only")
    school_year_status = repository.school_year_status(school_year_id)
    if school_year_status is None:
        raise StudentDocumentationSubjectApplicationError("school_year_unknown")
    if school_year_status != "current":
        raise StudentDocumentationSubjectApplicationError("school_year_read_only")


@contextmanager
def _read_snapshot(
    connection_factory: ConnectionFactory,
) -> Iterator[sqlite3.Connection]:
    connection = connection_factory()
    try:
        if connection.row_factory is None:
            connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN")
        yield connection
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def _write_transaction(
    connection_factory: ConnectionFactory,
    operation: Callable[
        [SQLiteStudentDocumentationSubjectRepository],
        DocumentationSubjectWriteResult,
    ],
) -> DocumentationSubjectWriteResult:
    connection = connection_factory()
    try:
        if connection.row_factory is None:
            connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        result = operation(SQLiteStudentDocumentationSubjectRepository(connection))
        connection.commit()
        return result
    except StudentDocumentationSubjectApplicationError:
        if connection.in_transaction:
            connection.rollback()
        raise
    except StudentDocumentationSubjectRepositoryError as error:
        if connection.in_transaction:
            connection.rollback()
        raise StudentDocumentationSubjectApplicationError(error.code) from None
    except (sqlite3.Error, ValueError):
        if connection.in_transaction:
            connection.rollback()
        raise StudentDocumentationSubjectApplicationError(
            "documentation_subject_write_failed"
        ) from None
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _call_fault_hook(fault_hook: FaultHook | None, stage: str) -> None:
    if fault_hook is not None:
        fault_hook(stage)
