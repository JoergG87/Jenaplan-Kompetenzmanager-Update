"""Central, Qt-free V3 assignment read API and isolated lifecycle services."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
import sqlite3
import uuid
from typing import Iterator, TypeVar

from src.core.school_year import (
    AssignmentAtDateProjection,
    AssignmentReferenceRequest,
    AssignmentResolutionStatus,
    CurrentMembershipReadSnapshot,
    CurrentStudentMembershipProjection,
    SchoolYear,
    StudentAssignmentStatus,
    StudentMembershipAssignment,
    V3Student,
)
from src.core.sqlite_school_year_assignment import (
    AssignmentSource,
    SchoolYearAssignmentRepositoryError,
    SchoolYearRepository,
    SchoolYearAssignmentReadSession,
    StoredStudentSchoolYearAssignment,
    StudentSchoolYearAssignmentRepository,
    V3StudentRepository,
)


ConnectionFactory = Callable[[], sqlite3.Connection]
IdentifierFactory = Callable[[], str]
TimestampProvider = Callable[[], datetime]
_T = TypeVar("_T")


class AssignmentApplicationError(RuntimeError):
    """Sanitized application-layer failure with a stable technical code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MembershipChangeStatus(str, Enum):
    CHANGED = "changed"
    NO_CHANGE = "no_change"


@dataclass(frozen=True, slots=True)
class InitialEnrollmentResult:
    student: V3Student
    assignment: StoredStudentSchoolYearAssignment


@dataclass(frozen=True, slots=True)
class MembershipChangeResult:
    status: MembershipChangeStatus
    previous_assignment_id: str
    assignment: StoredStudentSchoolYearAssignment | None


class SchoolYearAssignmentQueryService:
    """Resolve assignments in one consistent snapshot per public request."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def assignment_at_date(
        self,
        student_id: str,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        reference = _require_reference_date(reference_date)
        with self.read_session() as session:
            return session.assignment_at_date(student_id, reference)

    def assignments_at_dates(
        self,
        student_dates: Mapping[str, date],
    ) -> tuple[AssignmentAtDateProjection, ...]:
        requested = {
            student_id: _require_reference_date(reference_date)
            for student_id, reference_date in student_dates.items()
        }
        with self.read_session() as session:
            return session.assignments_at_dates(requested)

    def assignments_for_references(
        self,
        references: Sequence[AssignmentReferenceRequest],
    ) -> dict[str, AssignmentAtDateProjection]:
        requested = tuple(
            AssignmentReferenceRequest(
                reference.request_key,
                reference.student_id,
                _require_reference_date(reference.reference_date),
            )
            for reference in references
        )
        with self.read_session() as session:
            return session.assignments_for_references(requested)

    def current_membership(
        self,
        student_id: str,
        *,
        as_of: date,
    ) -> CurrentStudentMembershipProjection:
        reference = _require_reference_date(as_of)
        with self.read_session() as session:
            return session.current_membership(student_id, as_of=reference)

    def current_memberships(
        self,
        student_ids: Sequence[str] | None = None,
        *,
        as_of: date,
        group_id: str | None = None,
        group_ids: Sequence[str] = (),
        course_id: str | None = None,
        course_ids: Sequence[str] = (),
        course_group_id: str | None = None,
    ) -> tuple[CurrentStudentMembershipProjection, ...]:
        reference = _require_reference_date(as_of)
        with self.read_session() as session:
            return session.current_memberships(
                student_ids,
                as_of=reference,
                group_id=group_id,
                group_ids=group_ids,
                course_id=course_id,
                course_ids=course_ids,
                course_group_id=course_group_id,
            )

    def current_membership_snapshot(
        self,
        *,
        as_of: date,
        group_id: str | None = None,
        group_ids: Sequence[str] = (),
        course_id: str | None = None,
        course_ids: Sequence[str] = (),
        course_group_id: str | None = None,
    ) -> CurrentMembershipReadSnapshot:
        reference = _require_reference_date(as_of)
        with self.read_session() as session:
            return session.current_membership_snapshot(
                as_of=reference,
                group_id=group_id,
                group_ids=group_ids,
                course_id=course_id,
                course_ids=course_ids,
                course_group_id=course_group_id,
            )

    def membership_in_school_year(
        self,
        student_id: str,
        school_year_id: str,
        *,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        reference = _require_reference_date(reference_date)
        try:
            with self.read_session() as session:
                return session.membership_in_school_year(
                    student_id,
                    school_year_id,
                    reference_date=reference,
                )
        except SchoolYearAssignmentRepositoryError as error:
            raise AssignmentApplicationError(error.code) from None

    def last_known_membership(
        self,
        student_id: str,
        *,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        reference = _require_reference_date(reference_date)
        with self.read_session() as session:
            return session.last_known_membership(
                student_id,
                reference_date=reference,
            )

    def count_current_by_group(
        self,
        *,
        as_of: date,
    ) -> dict[str, int]:
        reference = _require_reference_date(as_of)
        try:
            with self.read_session() as session:
                return session.count_current_by_group(as_of=reference)
        except SchoolYearAssignmentRepositoryError as error:
            raise AssignmentApplicationError(error.code) from None

    def count_current_by_course(
        self,
        *,
        as_of: date,
    ) -> dict[str, int]:
        reference = _require_reference_date(as_of)
        try:
            with self.read_session() as session:
                return session.count_current_by_course(as_of=reference)
        except SchoolYearAssignmentRepositoryError as error:
            raise AssignmentApplicationError(error.code) from None

    @contextmanager
    def read_session(self) -> Iterator[SchoolYearAssignmentReadSession]:
        """Open one transaction-bound session for a composed product read."""

        with _read_snapshot(self._connection_factory) as connection:
            yield SchoolYearAssignmentReadSession(connection)


class CreateStudentWithInitialEnrollment:
    """Create V3 master data and its first enrolled interval atomically."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        student_id_factory: IdentifierFactory | None = None,
        assignment_id_factory: IdentifierFactory | None = None,
        now_provider: TimestampProvider | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._student_id_factory = student_id_factory or (
            lambda: f"STD-{uuid.uuid4()}"
        )
        self._assignment_id_factory = assignment_id_factory or (
            lambda: f"ASG-{uuid.uuid4()}"
        )
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(
        self,
        *,
        first_name: str,
        last_name: str,
        notes: str,
        school_year_id: str,
        valid_from: date,
        valid_to: date,
        group_id: str,
        course_id: str,
    ) -> InitialEnrollmentResult:
        first, last, student_notes = _master_data_values(
            first_name,
            last_name,
            notes,
        )
        start = _require_reference_date(valid_from)
        end = _require_reference_date(valid_to)
        timestamp = _require_timestamp(self._now_provider())
        student_id = _require_identifier(
            self._student_id_factory(),
            "student_id_invalid",
        )
        assignment_id = _require_identifier(
            self._assignment_id_factory(),
            "assignment_id_invalid",
        )

        def operation(connection: sqlite3.Connection) -> InitialEnrollmentResult:
            _validate_enrollment_references(
                connection,
                student_id=None,
                school_year_id=school_year_id,
                valid_from=start,
                valid_to=end,
                group_id=group_id,
                course_id=course_id,
            )
            student = V3Student(
                student_id=student_id,
                first_name=first,
                last_name=last,
                notes=student_notes,
                active=True,
                created_at=timestamp,
                updated_at=timestamp,
                archived_at=None,
            )
            V3StudentRepository(connection).create(student)
            assignment = StudentSchoolYearAssignmentRepository(
                connection
            ).insert(
                assignment_id,
                StudentMembershipAssignment(
                    student_id=student_id,
                    school_year_id=school_year_id,
                    group_id=group_id,
                    course_id=course_id,
                    assignment_status=StudentAssignmentStatus.ENROLLED,
                    valid_from=start,
                    valid_to=end,
                ),
                timestamp,
            )
            return InitialEnrollmentResult(student, assignment)

        return _write_transaction(
            self._connection_factory,
            operation,
            "initial_enrollment_failed",
        )


class UpdateStudentMasterData:
    """Update names and notes without reading or changing assignments."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        now_provider: TimestampProvider | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(
        self,
        student_id: str,
        *,
        first_name: str,
        last_name: str,
        notes: str,
    ) -> V3Student:
        first, last, student_notes = _master_data_values(
            first_name,
            last_name,
            notes,
        )
        timestamp = _require_timestamp(self._now_provider())
        return _write_transaction(
            self._connection_factory,
            lambda connection: V3StudentRepository(
                connection
            ).update_master_data(
                student_id,
                first,
                last,
                student_notes,
                timestamp,
            ),
            "student_master_data_update_failed",
        )


class EnrollStudent:
    """Create one explicit, non-overlapping enrolled interval."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        assignment_id_factory: IdentifierFactory | None = None,
        now_provider: TimestampProvider | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._assignment_id_factory = assignment_id_factory or (
            lambda: f"ASG-{uuid.uuid4()}"
        )
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(
        self,
        student_id: str,
        *,
        school_year_id: str,
        valid_from: date,
        valid_to: date,
        group_id: str,
        course_id: str,
    ) -> StoredStudentSchoolYearAssignment:
        start = _require_reference_date(valid_from)
        end = _require_reference_date(valid_to)
        timestamp = _require_timestamp(self._now_provider())
        assignment_id = _require_identifier(
            self._assignment_id_factory(),
            "assignment_id_invalid",
        )

        def operation(
            connection: sqlite3.Connection,
        ) -> StoredStudentSchoolYearAssignment:
            _validate_enrollment_references(
                connection,
                student_id=student_id,
                school_year_id=school_year_id,
                valid_from=start,
                valid_to=end,
                group_id=group_id,
                course_id=course_id,
            )
            repository = StudentSchoolYearAssignmentRepository(connection)
            if repository.has_overlap(student_id, start, end):
                raise AssignmentApplicationError("assignment_overlap")
            return repository.insert(
                assignment_id,
                StudentMembershipAssignment(
                    student_id=student_id,
                    school_year_id=school_year_id,
                    group_id=group_id,
                    course_id=course_id,
                    assignment_status=StudentAssignmentStatus.ENROLLED,
                    valid_from=start,
                    valid_to=end,
                ),
                timestamp,
            )

        return _write_transaction(
            self._connection_factory,
            operation,
            "enrollment_failed",
        )


class ChangeStudentMembership:
    """End one enrolled interval and create its replacement atomically."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        assignment_id_factory: IdentifierFactory | None = None,
        now_provider: TimestampProvider | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._assignment_id_factory = assignment_id_factory or (
            lambda: f"ASG-{uuid.uuid4()}"
        )
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(
        self,
        student_id: str,
        *,
        effective_on: date,
        group_id: str | None = None,
        course_id: str | None = None,
    ) -> MembershipChangeResult:
        effective = _require_reference_date(effective_on)
        timestamp = _require_timestamp(self._now_provider())

        def operation(connection: sqlite3.Connection) -> MembershipChangeResult:
            repository = StudentSchoolYearAssignmentRepository(connection)
            source = _require_unique_enrolled(
                repository.get_assignment_at_date(student_id, effective)
            )
            assert source.assignment_id is not None
            assert source.school_year_id is not None
            assert source.valid_from is not None
            assert source.valid_to is not None
            target_group = group_id if group_id is not None else source.group_id
            target_course = (
                course_id if course_id is not None else source.course_id
            )
            assert target_group is not None
            assert target_course is not None
            if (
                target_group == source.group_id
                and target_course == source.course_id
            ):
                return MembershipChangeResult(
                    MembershipChangeStatus.NO_CHANGE,
                    source.assignment_id,
                    None,
                )
            if effective == source.valid_from:
                raise AssignmentApplicationError(
                    "membership_change_on_first_interval_day"
                )
            _validate_enrollment_references(
                connection,
                student_id=student_id,
                school_year_id=source.school_year_id,
                valid_from=effective,
                valid_to=source.valid_to,
                group_id=target_group,
                course_id=target_course,
            )
            repository.shorten(
                source.assignment_id,
                effective - timedelta(days=1),
                timestamp,
            )
            replacement = repository.insert(
                _require_identifier(
                    self._assignment_id_factory(),
                    "assignment_id_invalid",
                ),
                StudentMembershipAssignment(
                    student_id=student_id,
                    school_year_id=source.school_year_id,
                    group_id=target_group,
                    course_id=target_course,
                    assignment_status=StudentAssignmentStatus.ENROLLED,
                    valid_from=effective,
                    valid_to=source.valid_to,
                ),
                timestamp,
            )
            return MembershipChangeResult(
                MembershipChangeStatus.CHANGED,
                source.assignment_id,
                replacement,
            )

        return _write_transaction(
            self._connection_factory,
            operation,
            "membership_change_failed",
        )


class ExitStudentFromSchoolYear:
    """Replace the remaining enrolled interval with an exited interval."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        assignment_id_factory: IdentifierFactory | None = None,
        now_provider: TimestampProvider | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._assignment_id_factory = assignment_id_factory or (
            lambda: f"ASG-{uuid.uuid4()}"
        )
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(
        self,
        student_id: str,
        *,
        effective_on: date,
    ) -> MembershipChangeResult:
        effective = _require_reference_date(effective_on)
        timestamp = _require_timestamp(self._now_provider())

        def operation(connection: sqlite3.Connection) -> MembershipChangeResult:
            repository = StudentSchoolYearAssignmentRepository(connection)
            source = _require_unique_enrolled(
                repository.get_assignment_at_date(student_id, effective)
            )
            assert source.assignment_id is not None
            assert source.school_year_id is not None
            assert source.valid_from is not None
            assert source.valid_to is not None
            if effective == source.valid_from:
                raise AssignmentApplicationError(
                    "membership_exit_on_first_interval_day"
                )
            repository.shorten(
                source.assignment_id,
                effective - timedelta(days=1),
                timestamp,
            )
            exited = repository.insert(
                _require_identifier(
                    self._assignment_id_factory(),
                    "assignment_id_invalid",
                ),
                StudentMembershipAssignment(
                    student_id=student_id,
                    school_year_id=source.school_year_id,
                    group_id=None,
                    course_id=None,
                    assignment_status=StudentAssignmentStatus.EXITED,
                    valid_from=effective,
                    valid_to=source.valid_to,
                ),
                timestamp,
            )
            return MembershipChangeResult(
                MembershipChangeStatus.CHANGED,
                source.assignment_id,
                exited,
            )

        return _write_transaction(
            self._connection_factory,
            operation,
            "school_year_exit_failed",
        )


class ArchiveStudent:
    """Archive master data only after an explicit enrollment check date."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        now_provider: TimestampProvider | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(self, student_id: str, *, as_of: date) -> V3Student:
        reference = _require_reference_date(as_of)
        timestamp = _require_timestamp(self._now_provider())
        if timestamp.date() != reference:
            raise AssignmentApplicationError(
                "archive_reference_date_timestamp_mismatch"
            )

        def operation(connection: sqlite3.Connection) -> V3Student:
            assignments = StudentSchoolYearAssignmentRepository(connection)
            if assignments.has_active_enrollment(student_id, reference):
                raise AssignmentApplicationError(
                    "active_enrollment_blocks_archive"
                )
            return V3StudentRepository(connection).archive(
                student_id,
                timestamp,
            )

        return _write_transaction(
            self._connection_factory,
            operation,
            "student_archive_failed",
        )


@contextmanager
def _read_snapshot(
    connection_factory: ConnectionFactory,
) -> Iterator[sqlite3.Connection]:
    connection = connection_factory()
    try:
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
    operation: Callable[[sqlite3.Connection], _T],
    failure_code: str,
) -> _T:
    connection = connection_factory()
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        result = operation(connection)
        connection.commit()
        return result
    except AssignmentApplicationError:
        if connection.in_transaction:
            connection.rollback()
        raise
    except SchoolYearAssignmentRepositoryError as error:
        if connection.in_transaction:
            connection.rollback()
        raise AssignmentApplicationError(error.code) from None
    except (sqlite3.Error, ValueError):
        if connection.in_transaction:
            connection.rollback()
        raise AssignmentApplicationError(failure_code) from None
    finally:
        connection.close()


def _require_unique_enrolled(
    sources: Sequence[AssignmentSource],
) -> AssignmentSource:
    matched = tuple(
        source for source in sources if source.assignment_id is not None
    )
    if len(matched) > 1:
        raise AssignmentApplicationError("assignment_ambiguous")
    if not matched:
        raise AssignmentApplicationError("assignment_missing")
    source = matched[0]
    if source.assignment_status is not StudentAssignmentStatus.ENROLLED:
        raise AssignmentApplicationError("student_not_enrolled")
    return source


def _validate_enrollment_references(
    connection: sqlite3.Connection,
    *,
    student_id: str | None,
    school_year_id: str,
    valid_from: date,
    valid_to: date,
    group_id: str,
    course_id: str,
) -> None:
    if valid_from > valid_to:
        raise AssignmentApplicationError("assignment_date_range_invalid")
    school_year = SchoolYearRepository(connection).get_by_id(school_year_id)
    if school_year is None:
        raise AssignmentApplicationError("school_year_missing")
    if (
        valid_from < school_year.start_date
        or valid_to > school_year.end_date
    ):
        raise AssignmentApplicationError("assignment_outside_school_year")
    if student_id is not None:
        student = V3StudentRepository(connection).get_by_id(student_id)
        if student is None:
            raise AssignmentApplicationError("student_missing")
        if student.archived_at is not None or not student.active:
            raise AssignmentApplicationError("student_archived")
    group = connection.execute(
        "SELECT active FROM groups WHERE group_id = ?",
        (group_id,),
    ).fetchone()
    if group is None or not bool(group["active"]):
        raise AssignmentApplicationError("group_invalid")
    course = connection.execute(
        "SELECT active, year_level FROM courses WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    if course is None or not bool(course["active"]):
        raise AssignmentApplicationError("course_invalid")
    if course["year_level"] not in (1, 2, 3):
        raise AssignmentApplicationError("course_year_level_invalid")


def _master_data_values(
    first_name: str,
    last_name: str,
    notes: str,
) -> tuple[str, str, str]:
    first = _require_identifier(first_name, "student_first_name_invalid")
    last = _require_identifier(last_name, "student_last_name_invalid")
    if not isinstance(notes, str):
        raise AssignmentApplicationError("student_notes_invalid")
    return first, last, notes


def _require_identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssignmentApplicationError(code)
    return value.strip()


def _require_reference_date(value: object) -> date:
    if type(value) is not date:
        raise AssignmentApplicationError("reference_date_invalid")
    return value


def _require_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise AssignmentApplicationError("technical_timestamp_invalid")
    return value
