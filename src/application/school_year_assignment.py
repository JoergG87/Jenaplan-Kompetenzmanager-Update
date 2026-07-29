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
    AssignmentResolutionStatus,
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
        with _read_snapshot(self._connection_factory) as connection:
            sources = StudentSchoolYearAssignmentRepository(
                connection
            ).get_assignment_at_date(student_id, reference)
            return _resolve_projection(student_id, reference, sources)

    def assignments_at_dates(
        self,
        student_dates: Mapping[str, date],
    ) -> tuple[AssignmentAtDateProjection, ...]:
        requested = tuple(
            (student_id, _require_reference_date(reference_date))
            for student_id, reference_date in student_dates.items()
        )
        with _read_snapshot(self._connection_factory) as connection:
            sources = StudentSchoolYearAssignmentRepository(
                connection
            ).list_assignments_at_dates(requested)
            return tuple(
                _resolve_projection(
                    student_id,
                    reference_date,
                    sources.get(student_id, ()),
                )
                for student_id, reference_date in requested
            )

    def current_membership(
        self,
        student_id: str,
        *,
        as_of: date,
    ) -> CurrentStudentMembershipProjection:
        return self.current_memberships((student_id,), as_of=as_of)[0]

    def current_memberships(
        self,
        student_ids: Sequence[str] | None = None,
        *,
        as_of: date,
        group_id: str | None = None,
        course_id: str | None = None,
        course_group_id: str | None = None,
    ) -> tuple[CurrentStudentMembershipProjection, ...]:
        reference = _require_reference_date(as_of)
        identifiers = (
            tuple(dict.fromkeys(student_ids))
            if student_ids is not None
            else None
        )
        with _read_snapshot(self._connection_factory) as connection:
            current = SchoolYearRepository(connection).get_current()
            if current is None:
                if identifiers is None:
                    return ()
                students = V3StudentRepository(connection).list_by_ids(identifiers)
                return tuple(
                    _missing_current_membership(
                        student_id,
                        reference,
                        students.get(student_id),
                    )
                    for student_id in identifiers
                )
            sources = StudentSchoolYearAssignmentRepository(
                connection
            ).list_current_memberships(
                current.school_year_id,
                reference,
                student_ids=identifiers,
                group_id=group_id,
                course_id=course_id,
                course_group_id=course_group_id,
            )
            grouped: dict[str, list[AssignmentSource]] = {}
            for source in sources:
                grouped.setdefault(source.student_id, []).append(source)
            order = (
                identifiers
                if identifiers is not None
                else tuple(grouped)
            )
            projections = tuple(
                _current_projection(
                    current,
                    reference,
                    _resolve_projection(
                        student_id,
                        reference,
                        grouped.get(student_id, ()),
                    ),
                )
                for student_id in order
            )
            if identifiers is None or any(
                value is not None
                for value in (group_id, course_id, course_group_id)
            ):
                projections = tuple(
                    projection
                    for projection in projections
                    if (
                        projection.resolution_status
                        is AssignmentResolutionStatus.ENROLLED
                        and (
                            group_id is None
                            or projection.group_id == group_id
                        )
                        and (
                            course_id is None
                            or projection.course_id == course_id
                        )
                    )
                )
            return projections

    def membership_in_school_year(
        self,
        student_id: str,
        school_year_id: str,
        *,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        reference = _require_reference_date(reference_date)
        with _read_snapshot(self._connection_factory) as connection:
            school_year = SchoolYearRepository(connection).get_by_id(
                school_year_id
            )
            if school_year is None:
                raise AssignmentApplicationError("school_year_missing")
            if not school_year.start_date <= reference <= school_year.end_date:
                raise AssignmentApplicationError(
                    "reference_date_outside_school_year"
                )
            sources = StudentSchoolYearAssignmentRepository(
                connection
            ).get_assignment_at_date(
                student_id,
                reference,
                school_year_id=school_year_id,
            )
            return _resolve_projection(student_id, reference, sources)

    def last_known_membership(
        self,
        student_id: str,
        *,
        reference_date: date,
    ) -> AssignmentAtDateProjection:
        reference = _require_reference_date(reference_date)
        with _read_snapshot(self._connection_factory) as connection:
            sources = StudentSchoolYearAssignmentRepository(
                connection
            ).get_last_known(student_id, reference)
            return _resolve_projection(student_id, reference, sources)

    def count_current_by_group(
        self,
        *,
        as_of: date,
    ) -> dict[str, int]:
        reference = _require_reference_date(as_of)
        with _read_snapshot(self._connection_factory) as connection:
            current = SchoolYearRepository(connection).get_current()
            if current is None:
                return {}
            return StudentSchoolYearAssignmentRepository(
                connection
            ).count_current_by_group(current.school_year_id, reference)

    def count_current_by_course(
        self,
        *,
        as_of: date,
    ) -> dict[str, int]:
        reference = _require_reference_date(as_of)
        with _read_snapshot(self._connection_factory) as connection:
            current = SchoolYearRepository(connection).get_current()
            if current is None:
                return {}
            return StudentSchoolYearAssignmentRepository(
                connection
            ).count_current_by_course(current.school_year_id, reference)


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


def _resolve_projection(
    student_id: str,
    reference_date: date,
    sources: Sequence[AssignmentSource],
) -> AssignmentAtDateProjection:
    matched = tuple(
        source for source in sources if source.assignment_id is not None
    )
    base = sources[0] if sources else None
    student_active = base.student_active if base is not None else False
    archived_at = base.student_archived_at if base is not None else None
    student_archived = archived_at is not None or not student_active
    if len(matched) > 1:
        return _empty_projection(
            student_id,
            reference_date,
            AssignmentResolutionStatus.AMBIGUOUS,
            student_active,
            student_archived,
        )
    if len(matched) == 1:
        source = matched[0]
        assert source.assignment_status is not None
        status = (
            AssignmentResolutionStatus.ENROLLED
            if source.assignment_status is StudentAssignmentStatus.ENROLLED
            else AssignmentResolutionStatus.EXITED
        )
        accessible_name = _accessible_assignment_name(status, source)
        return AssignmentAtDateProjection(
            student_id=student_id,
            reference_date=reference_date,
            resolution_status=status,
            school_year_id=source.school_year_id,
            school_year_label=source.school_year_label,
            assignment_id=source.assignment_id,
            assignment_status=source.assignment_status,
            valid_from=source.valid_from,
            valid_to=source.valid_to,
            group_id=source.group_id,
            group_name=source.group_name,
            course_id=source.course_id,
            course_name=source.course_name,
            year_level=source.year_level,
            student_active=student_active,
            student_archived=student_archived,
            visible_status_key=status.value,
            accessible_name=accessible_name,
        )
    status = AssignmentResolutionStatus.NO_ASSIGNMENT
    if (
        archived_at is not None
        and archived_at.date() <= reference_date
    ):
        status = AssignmentResolutionStatus.STUDENT_ARCHIVED
    return _empty_projection(
        student_id,
        reference_date,
        status,
        student_active,
        student_archived,
    )


def _empty_projection(
    student_id: str,
    reference_date: date,
    status: AssignmentResolutionStatus,
    student_active: bool,
    student_archived: bool,
) -> AssignmentAtDateProjection:
    accessible_names = {
        AssignmentResolutionStatus.NO_ASSIGNMENT: "Keine Zuordnung vorhanden",
        AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING: (
            "Kein aktuelles Schuljahr festgelegt"
        ),
        AssignmentResolutionStatus.AMBIGUOUS: "Zuordnung nicht eindeutig",
        AssignmentResolutionStatus.STUDENT_ARCHIVED: "Kind ist archiviert",
    }
    return AssignmentAtDateProjection(
        student_id=student_id,
        reference_date=reference_date,
        resolution_status=status,
        school_year_id=None,
        school_year_label=None,
        assignment_id=None,
        assignment_status=None,
        valid_from=None,
        valid_to=None,
        group_id=None,
        group_name=None,
        course_id=None,
        course_name=None,
        year_level=None,
        student_active=student_active,
        student_archived=student_archived,
        visible_status_key=status.value,
        accessible_name=accessible_names[status],
    )


def _accessible_assignment_name(
    status: AssignmentResolutionStatus,
    source: AssignmentSource,
) -> str:
    year = source.school_year_label or "Schuljahr unbekannt"
    if status is AssignmentResolutionStatus.EXITED:
        return f"{year}, ausgeschieden"
    group = source.group_name or "Stammgruppe unbekannt"
    course = source.course_name or "Kurs unbekannt"
    level = (
        f"Stufe {source.year_level}"
        if source.year_level is not None
        else "Stufe unbekannt"
    )
    return f"{year}, eingeschrieben, {group}, {course}, {level}"


def _current_projection(
    current: SchoolYear,
    as_of: date,
    resolved: AssignmentAtDateProjection,
) -> CurrentStudentMembershipProjection:
    return CurrentStudentMembershipProjection(
        current_school_year_id=current.school_year_id,
        current_school_year_label=current.label,
        as_of=as_of,
        student_id=resolved.student_id,
        student_active=resolved.student_active,
        student_archived=resolved.student_archived,
        resolution_status=resolved.resolution_status,
        group_id=resolved.group_id,
        group_name=resolved.group_name,
        course_id=resolved.course_id,
        course_name=resolved.course_name,
        year_level=resolved.year_level,
    )


def _missing_current_membership(
    student_id: str,
    as_of: date,
    student: V3Student | None,
) -> CurrentStudentMembershipProjection:
    return CurrentStudentMembershipProjection(
        current_school_year_id=None,
        current_school_year_label=None,
        as_of=as_of,
        student_id=student_id,
        student_active=student.active if student is not None else False,
        student_archived=(
            student.archived_at is not None if student is not None else False
        ),
        resolution_status=(
            AssignmentResolutionStatus.CURRENT_SCHOOL_YEAR_MISSING
        ),
        group_id=None,
        group_name=None,
        course_id=None,
        course_name=None,
        year_level=None,
    )


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
