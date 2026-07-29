"""Pure domain model for a future V3 school-year initialization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
import hashlib
import json
import re
import unicodedata

from .records import StudentRecord


SCHOOL_YEAR_INITIALIZATION_PLAN_FORMAT_VERSION = 1

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SchoolYearDomainError(ValueError):
    """Reject an invalid school-year domain value without storage access."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class SchoolYearStatus(str, Enum):
    """Allowed lifecycle states of a school year."""

    PLANNED = "planned"
    CURRENT = "current"
    CLOSED = "closed"


class StudentAssignmentStatus(str, Enum):
    """Allowed membership states inside one school-year interval."""

    ENROLLED = "enrolled"
    EXITED = "exited"


class StudentMigrationClassification(str, Enum):
    """Exactly one primary V2 migration classification per student."""

    ACTIVE_MIGRATABLE = "ACTIVE_MIGRATABLE"
    ARCHIVED_MIGRATABLE = "ARCHIVED_MIGRATABLE"
    TEMPORAL_CONTEXT_UNRESOLVED = "TEMPORAL_CONTEXT_UNRESOLVED"
    MEMBERSHIP_REFERENCE_INVALID = "MEMBERSHIP_REFERENCE_INVALID"
    ACTIVITY_ARCHIVE_CONFLICT = "ACTIVITY_ARCHIVE_CONFLICT"


class StudentMigrationWarningCode(str, Enum):
    """Stable secondary findings that do not replace the primary category."""

    ACTIVE_FLAG_INVALID = "ACTIVE_FLAG_INVALID"
    ACTIVE_WITH_ARCHIVED_AT = "ACTIVE_WITH_ARCHIVED_AT"
    ARCHIVED_AT_MISSING = "ARCHIVED_AT_MISSING"
    ARCHIVED_AT_INVALID = "ARCHIVED_AT_INVALID"
    ARCHIVED_AT_ON_OR_BEFORE_START = "ARCHIVED_AT_ON_OR_BEFORE_START"
    ARCHIVED_AT_AFTER_END = "ARCHIVED_AT_AFTER_END"
    GROUP_ID_MISSING = "GROUP_ID_MISSING"
    GROUP_ID_UNKNOWN = "GROUP_ID_UNKNOWN"
    COURSE_ID_MISSING = "COURSE_ID_MISSING"
    COURSE_ID_UNKNOWN = "COURSE_ID_UNKNOWN"


@dataclass(frozen=True, slots=True)
class SchoolYear:
    """One explicitly supplied inclusive school-year period."""

    school_year_id: str
    label: str
    start_date: date
    end_date: date
    status: SchoolYearStatus

    def __post_init__(self) -> None:
        _require_identifier(self.school_year_id, "school_year_id_invalid")
        _require_text(self.label, "school_year_label_invalid")
        _require_date(self.start_date, "school_year_start_date_invalid")
        _require_date(self.end_date, "school_year_end_date_invalid")
        object.__setattr__(
            self,
            "status",
            _enum_value(
                self.status,
                SchoolYearStatus,
                "school_year_status_invalid",
            ),
        )
        if self.start_date > self.end_date:
            raise SchoolYearDomainError("school_year_date_range_invalid")


@dataclass(frozen=True, slots=True)
class StudentMembershipAssignment:
    """One inclusive membership interval inside one school year."""

    student_id: str
    school_year_id: str
    group_id: str | None
    course_id: str | None
    assignment_status: StudentAssignmentStatus
    valid_from: date
    valid_to: date

    def __post_init__(self) -> None:
        _require_identifier(self.student_id, "assignment_student_id_invalid")
        _require_identifier(
            self.school_year_id,
            "assignment_school_year_id_invalid",
        )
        _require_date(self.valid_from, "assignment_valid_from_invalid")
        _require_date(self.valid_to, "assignment_valid_to_invalid")
        status = _enum_value(
            self.assignment_status,
            StudentAssignmentStatus,
            "assignment_status_invalid",
        )
        object.__setattr__(self, "assignment_status", status)
        if self.valid_from > self.valid_to:
            raise SchoolYearDomainError("assignment_date_range_invalid")
        if status is StudentAssignmentStatus.ENROLLED:
            _require_identifier(self.group_id, "assignment_group_id_required")
            _require_identifier(self.course_id, "assignment_course_id_required")
        elif self.group_id is not None or self.course_id is not None:
            raise SchoolYearDomainError("exited_assignment_has_membership")


@dataclass(frozen=True, slots=True)
class StudentMigrationClassificationRecord:
    """Primary classification and separate stable secondary warnings."""

    student_id: str
    classification: StudentMigrationClassification
    warning_codes: tuple[StudentMigrationWarningCode, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.student_id, "classification_student_id_invalid")
        object.__setattr__(
            self,
            "classification",
            _enum_value(
                self.classification,
                StudentMigrationClassification,
                "student_migration_classification_invalid",
            ),
        )
        warnings = tuple(
            _enum_value(
                warning,
                StudentMigrationWarningCode,
                "student_migration_warning_invalid",
            )
            for warning in self.warning_codes
        )
        if len(warnings) != len(set(warnings)):
            raise SchoolYearDomainError("student_migration_warnings_duplicate")
        object.__setattr__(
            self,
            "warning_codes",
            tuple(sorted(warnings, key=lambda warning: warning.value)),
        )


@dataclass(frozen=True, slots=True)
class StudentMigrationClassificationResult:
    """Pure classification output for exactly one V2 StudentRecord."""

    classification: StudentMigrationClassificationRecord
    initial_assignment: StudentMembershipAssignment | None

    def __post_init__(self) -> None:
        migratable = self.classification.classification in {
            StudentMigrationClassification.ACTIVE_MIGRATABLE,
            StudentMigrationClassification.ARCHIVED_MIGRATABLE,
        }
        if migratable != (self.initial_assignment is not None):
            raise SchoolYearDomainError(
                "student_migration_assignment_classification_mismatch"
            )
        if (
            self.initial_assignment is not None
            and self.initial_assignment.student_id
            != self.classification.student_id
        ):
            raise SchoolYearDomainError(
                "student_migration_assignment_student_mismatch"
            )


@dataclass(frozen=True, slots=True)
class StudentMigrationBlocker:
    """Stable non-display blocker derived from one primary category."""

    student_id: str
    classification: StudentMigrationClassification

    def __post_init__(self) -> None:
        _require_identifier(self.student_id, "blocker_student_id_invalid")
        classification = _enum_value(
            self.classification,
            StudentMigrationClassification,
            "student_migration_blocker_invalid",
        )
        if classification in {
            StudentMigrationClassification.ACTIVE_MIGRATABLE,
            StudentMigrationClassification.ARCHIVED_MIGRATABLE,
        }:
            raise SchoolYearDomainError("migratable_student_cannot_be_blocker")
        object.__setattr__(self, "classification", classification)


@dataclass(frozen=True, slots=True)
class SchoolYearInitializationPreview:
    """Complete deterministic read-only preview for all supplied V2 students."""

    student_classifications: tuple[StudentMigrationClassificationRecord, ...]
    assignment_proposals: tuple[StudentMembershipAssignment, ...]
    blockers: tuple[StudentMigrationBlocker, ...]

    def __post_init__(self) -> None:
        classifications = tuple(
            sorted(
                self.student_classifications,
                key=lambda item: _canonical_text_key(item.student_id),
            )
        )
        assignments = tuple(
            sorted(self.assignment_proposals, key=_assignment_order_key)
        )
        blockers = tuple(
            sorted(
                self.blockers,
                key=lambda item: (
                    _canonical_text_key(item.student_id),
                    item.classification.value,
                ),
            )
        )
        object.__setattr__(self, "student_classifications", classifications)
        object.__setattr__(self, "assignment_proposals", assignments)
        object.__setattr__(self, "blockers", blockers)
        _validate_preview(self)


@dataclass(frozen=True, slots=True)
class CourseYearLevelConfirmation:
    """One explicitly confirmed stable year level for an existing course."""

    course_id: str
    year_level: int

    def __post_init__(self) -> None:
        _require_identifier(self.course_id, "course_year_level_course_id_invalid")
        if isinstance(self.year_level, bool) or self.year_level not in (1, 2, 3):
            raise SchoolYearDomainError("course_year_level_invalid")


@dataclass(frozen=True, slots=True)
class SchoolYearSchemaInformation:
    """Canonical source or target schema identity supplied by the caller."""

    sqlite_user_version: int
    schema_fingerprint_sha256: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.sqlite_user_version, bool)
            or not isinstance(self.sqlite_user_version, int)
            or self.sqlite_user_version < 0
        ):
            raise SchoolYearDomainError("schema_user_version_invalid")
        if (
            not isinstance(self.schema_fingerprint_sha256, str)
            or _SHA256_PATTERN.fullmatch(self.schema_fingerprint_sha256) is None
        ):
            raise SchoolYearDomainError("schema_fingerprint_invalid")


@dataclass(frozen=True, slots=True)
class SchoolYearInitializationPlan:
    """Canonical, hashable and persistence-free V3 initialization plan."""

    format_version: int
    confirmed_initial_school_year: SchoolYear
    confirmed_course_year_levels: tuple[CourseYearLevelConfirmation, ...]
    student_classifications: tuple[StudentMigrationClassificationRecord, ...]
    assignment_proposals: tuple[StudentMembershipAssignment, ...]
    blockers: tuple[StudentMigrationBlocker, ...]
    source_schema: SchoolYearSchemaInformation
    target_schema: SchoolYearSchemaInformation

    def __post_init__(self) -> None:
        if self.format_version != SCHOOL_YEAR_INITIALIZATION_PLAN_FORMAT_VERSION:
            raise SchoolYearDomainError(
                "school_year_initialization_plan_format_unsupported"
            )
        course_levels = tuple(
            sorted(
                self.confirmed_course_year_levels,
                key=lambda item: _canonical_text_key(item.course_id),
            )
        )
        canonical_course_ids = {
            _canonical_text_key(item.course_id) for item in course_levels
        }
        if len(course_levels) != len(canonical_course_ids):
            raise SchoolYearDomainError("course_year_level_course_id_duplicate")
        object.__setattr__(self, "confirmed_course_year_levels", course_levels)

        preview = SchoolYearInitializationPreview(
            self.student_classifications,
            self.assignment_proposals,
            self.blockers,
        )
        object.__setattr__(
            self,
            "student_classifications",
            preview.student_classifications,
        )
        object.__setattr__(
            self,
            "assignment_proposals",
            preview.assignment_proposals,
        )
        object.__setattr__(self, "blockers", preview.blockers)
        for assignment in self.assignment_proposals:
            if (
                assignment.school_year_id
                != self.confirmed_initial_school_year.school_year_id
            ):
                raise SchoolYearDomainError(
                    "assignment_school_year_does_not_match_initial_year"
                )
            if (
                assignment.valid_from
                < self.confirmed_initial_school_year.start_date
                or assignment.valid_to
                > self.confirmed_initial_school_year.end_date
            ):
                raise SchoolYearDomainError(
                    "assignment_outside_initial_school_year"
                )

    def canonical_dict(self) -> dict[str, object]:
        """Return the complete payload whose UTF-8 bytes are hashed."""

        school_year = self.confirmed_initial_school_year
        return {
            "assignment_proposals": [
                {
                    "assignment_status": assignment.assignment_status.value,
                    "course_id": assignment.course_id,
                    "group_id": assignment.group_id,
                    "school_year_id": assignment.school_year_id,
                    "student_id": assignment.student_id,
                    "valid_from": assignment.valid_from.isoformat(),
                    "valid_to": assignment.valid_to.isoformat(),
                }
                for assignment in self.assignment_proposals
            ],
            "blockers": [
                {
                    "classification": blocker.classification.value,
                    "student_id": blocker.student_id,
                }
                for blocker in self.blockers
            ],
            "confirmed_course_year_levels": [
                {
                    "course_id": confirmation.course_id,
                    "year_level": confirmation.year_level,
                }
                for confirmation in self.confirmed_course_year_levels
            ],
            "confirmed_initial_school_year": {
                "end_date": school_year.end_date.isoformat(),
                "label": school_year.label,
                "school_year_id": school_year.school_year_id,
                "start_date": school_year.start_date.isoformat(),
                "status": school_year.status.value,
            },
            "format_version": self.format_version,
            "source_schema": _schema_dict(self.source_schema),
            "student_classifications": [
                {
                    "classification": classification.classification.value,
                    "student_id": classification.student_id,
                    "warning_codes": [
                        warning.value
                        for warning in classification.warning_codes
                    ],
                }
                for classification in self.student_classifications
            ],
            "target_schema": _schema_dict(self.target_schema),
        }

    def canonical_json(self) -> str:
        """Serialize with NFC strings, sorted keys and stable array ordering."""

        return json.dumps(
            _normalize_nfc(self.canonical_dict()),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def canonical_bytes(self) -> bytes:
        """Return the exact canonical UTF-8 representation."""

        return self.canonical_json().encode("utf-8")

    @property
    def plan_sha256(self) -> str:
        """Hash exactly the canonical payload bytes, excluding the hash itself."""

        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def classify_v2_student(
    student: StudentRecord,
    initial_school_year: SchoolYear,
    known_group_ids: Iterable[str],
    known_course_ids: Iterable[str],
) -> StudentMigrationClassificationResult:
    """Classify one V2 record without repositories, UI state or estimates."""

    warnings: set[StudentMigrationWarningCode] = set()
    group_ids = frozenset(known_group_ids)
    course_ids = frozenset(known_course_ids)

    group_reference_invalid = _reference_warning(
        student.group_id,
        group_ids,
        StudentMigrationWarningCode.GROUP_ID_MISSING,
        StudentMigrationWarningCode.GROUP_ID_UNKNOWN,
        warnings,
    )
    course_reference_invalid = _reference_warning(
        student.course_id,
        course_ids,
        StudentMigrationWarningCode.COURSE_ID_MISSING,
        StudentMigrationWarningCode.COURSE_ID_UNKNOWN,
        warnings,
    )

    archived_at_present = _has_archived_at(student.archived_at)
    local_archive_date: date | None = None
    if archived_at_present:
        local_archive_date = _local_date(student.archived_at)
        if local_archive_date is None:
            warnings.add(StudentMigrationWarningCode.ARCHIVED_AT_INVALID)
        elif local_archive_date <= initial_school_year.start_date:
            warnings.add(
                StudentMigrationWarningCode.ARCHIVED_AT_ON_OR_BEFORE_START
            )
        elif local_archive_date > initial_school_year.end_date:
            warnings.add(StudentMigrationWarningCode.ARCHIVED_AT_AFTER_END)

    activity_archive_conflict = False
    if not isinstance(student.active, bool):
        warnings.add(StudentMigrationWarningCode.ACTIVE_FLAG_INVALID)
        activity_archive_conflict = True
    elif student.active and archived_at_present:
        warnings.add(StudentMigrationWarningCode.ACTIVE_WITH_ARCHIVED_AT)
        activity_archive_conflict = True
    elif not student.active and not archived_at_present:
        warnings.add(StudentMigrationWarningCode.ARCHIVED_AT_MISSING)

    reference_invalid = group_reference_invalid or course_reference_invalid
    assignment: StudentMembershipAssignment | None = None

    if activity_archive_conflict:
        category = StudentMigrationClassification.ACTIVITY_ARCHIVE_CONFLICT
    elif reference_invalid:
        category = StudentMigrationClassification.MEMBERSHIP_REFERENCE_INVALID
    elif student.active is True and not archived_at_present:
        category = StudentMigrationClassification.ACTIVE_MIGRATABLE
        assignment = StudentMembershipAssignment(
            student_id=student.student_id,
            school_year_id=initial_school_year.school_year_id,
            group_id=student.group_id,
            course_id=student.course_id,
            assignment_status=StudentAssignmentStatus.ENROLLED,
            valid_from=initial_school_year.start_date,
            valid_to=initial_school_year.end_date,
        )
    elif (
        student.active is False
        and local_archive_date is not None
        and initial_school_year.start_date
        < local_archive_date
        <= initial_school_year.end_date
    ):
        category = StudentMigrationClassification.ARCHIVED_MIGRATABLE
        assignment = StudentMembershipAssignment(
            student_id=student.student_id,
            school_year_id=initial_school_year.school_year_id,
            group_id=student.group_id,
            course_id=student.course_id,
            assignment_status=StudentAssignmentStatus.ENROLLED,
            valid_from=initial_school_year.start_date,
            valid_to=local_archive_date - timedelta(days=1),
        )
    else:
        category = StudentMigrationClassification.TEMPORAL_CONTEXT_UNRESOLVED

    classification = StudentMigrationClassificationRecord(
        student_id=student.student_id,
        classification=category,
        warning_codes=tuple(warnings),
    )
    return StudentMigrationClassificationResult(classification, assignment)


def build_school_year_initialization_preview(
    students: Iterable[StudentRecord],
    initial_school_year: SchoolYear,
    known_group_ids: Iterable[str],
    known_course_ids: Iterable[str],
) -> SchoolYearInitializationPreview:
    """Classify every supplied V2 record exactly once in canonical ID order."""

    group_ids = frozenset(known_group_ids)
    course_ids = frozenset(known_course_ids)
    records = tuple(students)
    canonical_student_ids = tuple(
        _canonical_text_key(student.student_id) for student in records
    )
    if len(canonical_student_ids) != len(set(canonical_student_ids)):
        raise SchoolYearDomainError("v2_student_id_duplicate")

    results = tuple(
        classify_v2_student(
            student,
            initial_school_year,
            group_ids,
            course_ids,
        )
        for student in records
    )
    classifications = tuple(result.classification for result in results)
    assignments = tuple(
        result.initial_assignment
        for result in results
        if result.initial_assignment is not None
    )
    blockers = tuple(
        StudentMigrationBlocker(
            result.classification.student_id,
            result.classification.classification,
        )
        for result in results
        if result.initial_assignment is None
    )
    return SchoolYearInitializationPreview(
        classifications,
        assignments,
        blockers,
    )


def build_school_year_initialization_plan(
    *,
    initial_school_year: SchoolYear,
    confirmed_course_year_levels: Iterable[CourseYearLevelConfirmation],
    preview: SchoolYearInitializationPreview,
    source_schema: SchoolYearSchemaInformation,
    target_schema: SchoolYearSchemaInformation,
) -> SchoolYearInitializationPlan:
    """Create the validated canonical plan without reading or writing storage."""

    return SchoolYearInitializationPlan(
        format_version=SCHOOL_YEAR_INITIALIZATION_PLAN_FORMAT_VERSION,
        confirmed_initial_school_year=initial_school_year,
        confirmed_course_year_levels=tuple(confirmed_course_year_levels),
        student_classifications=preview.student_classifications,
        assignment_proposals=preview.assignment_proposals,
        blockers=preview.blockers,
        source_schema=source_schema,
        target_schema=target_schema,
    )


def _validate_preview(preview: SchoolYearInitializationPreview) -> None:
    classifications_by_student: dict[
        str, StudentMigrationClassificationRecord
    ] = {}
    for classification in preview.student_classifications:
        key = _canonical_text_key(classification.student_id)
        if key in classifications_by_student:
            raise SchoolYearDomainError("student_classification_duplicate")
        classifications_by_student[key] = classification

    assignments_by_student: dict[str, StudentMembershipAssignment] = {}
    for assignment in preview.assignment_proposals:
        key = _canonical_text_key(assignment.student_id)
        if key in assignments_by_student:
            raise SchoolYearDomainError("student_assignment_proposal_duplicate")
        assignments_by_student[key] = assignment

    blockers_by_student: dict[str, StudentMigrationBlocker] = {}
    for blocker in preview.blockers:
        key = _canonical_text_key(blocker.student_id)
        if key in blockers_by_student:
            raise SchoolYearDomainError("student_migration_blocker_duplicate")
        blockers_by_student[key] = blocker

    migratable_students = {
        key
        for key, item in classifications_by_student.items()
        if item.classification
        in {
            StudentMigrationClassification.ACTIVE_MIGRATABLE,
            StudentMigrationClassification.ARCHIVED_MIGRATABLE,
        }
    }
    blocked_students = set(classifications_by_student) - migratable_students
    if set(assignments_by_student) != migratable_students:
        raise SchoolYearDomainError(
            "student_assignment_proposals_incomplete"
        )
    if any(
        assignment.assignment_status is not StudentAssignmentStatus.ENROLLED
        for assignment in assignments_by_student.values()
    ):
        raise SchoolYearDomainError(
            "initial_assignment_proposal_must_be_enrolled"
        )
    if set(blockers_by_student) != blocked_students:
        raise SchoolYearDomainError("student_migration_blockers_incomplete")
    for key, blocker in blockers_by_student.items():
        if (
            blocker.classification
            is not classifications_by_student[key].classification
        ):
            raise SchoolYearDomainError(
                "student_migration_blocker_classification_mismatch"
            )


def _reference_warning(
    value: object,
    known_ids: frozenset[str],
    missing_code: StudentMigrationWarningCode,
    unknown_code: StudentMigrationWarningCode,
    warnings: set[StudentMigrationWarningCode],
) -> bool:
    if not isinstance(value, str) or not value.strip():
        warnings.add(missing_code)
        return True
    if value not in known_ids:
        warnings.add(unknown_code)
        return True
    return False


def _has_archived_at(value: object) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _local_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone().date() if parsed.tzinfo is not None else parsed.date()


def _assignment_order_key(
    assignment: StudentMembershipAssignment,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        _canonical_text_key(assignment.student_id),
        _canonical_text_key(assignment.school_year_id),
        assignment.valid_from.isoformat(),
        assignment.valid_to.isoformat(),
        assignment.assignment_status.value,
        _canonical_text_key(assignment.group_id or ""),
        _canonical_text_key(assignment.course_id or ""),
    )


def _schema_dict(schema: SchoolYearSchemaInformation) -> dict[str, object]:
    return {
        "schema_fingerprint_sha256": schema.schema_fingerprint_sha256,
        "sqlite_user_version": schema.sqlite_user_version,
    }


def _normalize_nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", key): _normalize_nfc(item)
            for key, item in value.items()
        }
    return value


def _canonical_text_key(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _enum_value(value: object, enum_type: type[Enum], code: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise SchoolYearDomainError(code) from exc


def _require_identifier(value: object, code: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchoolYearDomainError(code)


def _require_text(value: object, code: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchoolYearDomainError(code)


def _require_date(value: object, code: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise SchoolYearDomainError(code)
