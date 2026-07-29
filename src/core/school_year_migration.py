"""Isolated, explicit V2 to V3 school-year schema migration.

This module is deliberately not imported by product startup, the desktop
adapter or ``SQLiteDatabase.initialize_schema``.  It only migrates the
database returned by its injected connection factory.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import hashlib
import json
import re
import sqlite3
from typing import Any

from .database_compatibility import (
    REGISTERED_V3_SCHEMA_FINGERPRINT,
    REGISTERED_V3_SCHEMA_VERSION,
    DatabaseCompatibilityInspector,
)
from .database_engine import DatabaseEngine
from .records import StudentRecord
from .school_year import (
    CourseYearLevelConfirmation,
    SCHOOL_YEAR_INITIALIZATION_PLAN_FORMAT_VERSION,
    SchoolYearInitializationPlan,
    SchoolYearStatus,
    StudentMembershipAssignment,
    build_school_year_initialization_preview,
)


TARGET_V3_DATABASE_VERSION = REGISTERED_V3_SCHEMA_VERSION
SCHOOL_YEAR_MIGRATION_ENGINE_FORMAT_VERSION = 1

V3_SCHEMA_FINGERPRINT = REGISTERED_V3_SCHEMA_FINGERPRINT

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_BACKUP_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class SchoolYearMigrationErrorCode(str, Enum):
    V2_SCHEMA_MISMATCH = "V2_SCHEMA_MISMATCH"
    SOURCE_STATE_MISMATCH = "SOURCE_STATE_MISMATCH"
    BACKUP_EVIDENCE_MISSING = "BACKUP_EVIDENCE_MISSING"
    BACKUP_EVIDENCE_MISMATCH = "BACKUP_EVIDENCE_MISMATCH"
    INITIALIZATION_PLAN_BLOCKED = "INITIALIZATION_PLAN_BLOCKED"
    COURSE_LEVEL_MAPPING_INCOMPLETE = "COURSE_LEVEL_MAPPING_INCOMPLETE"
    STUDENT_CLASSIFICATION_MISMATCH = "STUDENT_CLASSIFICATION_MISMATCH"
    ASSIGNMENT_PLAN_MISMATCH = "ASSIGNMENT_PLAN_MISMATCH"
    V3_SCHEMA_CREATE_FAILED = "V3_SCHEMA_CREATE_FAILED"
    COURSE_REBUILD_FAILED = "COURSE_REBUILD_FAILED"
    STUDENT_REBUILD_FAILED = "STUDENT_REBUILD_FAILED"
    V3_FINGERPRINT_MISMATCH = "V3_FINGERPRINT_MISMATCH"
    FOREIGN_KEY_CHECK_FAILED = "FOREIGN_KEY_CHECK_FAILED"
    INTEGRITY_CHECK_FAILED = "INTEGRITY_CHECK_FAILED"
    CIPHER_INTEGRITY_CHECK_FAILED = "CIPHER_INTEGRITY_CHECK_FAILED"
    TRANSITION_RECEIPT_CONFLICT = "TRANSITION_RECEIPT_CONFLICT"
    MIGRATION_ROLLED_BACK = "MIGRATION_ROLLED_BACK"
    POST_COMMIT_VERIFICATION_FAILED = "POST_COMMIT_VERIFICATION_FAILED"


class SchoolYearMigrationError(RuntimeError):
    """Sanitized migration failure with stable technical classification."""

    def __init__(
        self,
        code: SchoolYearMigrationErrorCode,
        *,
        cause_code: SchoolYearMigrationErrorCode | None = None,
        committed: bool | None = False,
        rollback_verified: bool | None = None,
    ) -> None:
        self.code = code
        self.cause_code = cause_code
        self.committed = committed
        self.rollback_verified = rollback_verified
        super().__init__(code.value)


class SchoolYearMigrationFailpoint(str, Enum):
    BEFORE_BEGIN = "before_begin"
    AFTER_BEGIN = "after_begin"
    AFTER_SCHOOL_YEARS_DDL = "after_school_years_ddl"
    AFTER_ASSIGNMENT_DDL = "after_assignment_ddl"
    AFTER_TRANSITION_DDL = "after_transition_ddl"
    AFTER_COURSE_COPY = "after_course_copy"
    AFTER_COURSE_DROP_RENAME = "after_course_drop_rename"
    AFTER_ASSIGNMENT_INSERT = "after_assignment_insert"
    AFTER_STUDENT_COPY = "after_student_copy"
    AFTER_STUDENT_DROP_RENAME = "after_student_drop_rename"
    AFTER_SCHEMA_OBJECTS_RESTORED = "after_schema_objects_restored"
    AFTER_TRANSITION_RECEIPT = "after_transition_receipt"
    AFTER_USER_VERSION = "after_user_version"
    AFTER_FINGERPRINT_CHECK = "after_fingerprint_check"
    AFTER_INTEGRITY_CHECK = "after_integrity_check"
    AFTER_FOREIGN_KEY_CHECK = "after_foreign_key_check"
    BEFORE_COMMIT = "before_commit"
    AFTER_COMMIT = "after_commit"
    AFTER_REOPEN_BEFORE_VERIFICATION = "after_reopen_before_verification"


@dataclass(frozen=True, slots=True)
class VerifiedBackupEvidence:
    """Immutable proof produced by an external backup-verification owner."""

    backup_sha256: str
    source_state_sha256: str
    source_schema_fingerprint: str
    verified_at: str
    backup_id: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.backup_sha256,
            self.source_state_sha256,
            self.source_schema_fingerprint,
        ):
            if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError("backup_evidence_sha256_invalid")
        if not isinstance(self.verified_at, str):
            raise ValueError("backup_evidence_verified_at_invalid")
        try:
            parsed = datetime.fromisoformat(self.verified_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("backup_evidence_verified_at_invalid") from error
        if parsed.tzinfo is None:
            raise ValueError("backup_evidence_verified_at_invalid")
        if self.backup_id is not None and (
            not isinstance(self.backup_id, str)
            or _SAFE_BACKUP_ID_PATTERN.fullmatch(self.backup_id) is None
        ):
            raise ValueError("backup_evidence_id_invalid")


@dataclass(frozen=True, slots=True)
class SchoolYearMigrationResult:
    """Success returned only after a new-connection V3 verification."""

    transition_id: str
    operation_token: str
    target_schema_fingerprint: str
    result_counts_json: str
    post_reopen_verified: bool = True


FailpointHook = Callable[[SchoolYearMigrationFailpoint], None]
ConnectionFactory = Callable[[], Any]


_SCHOOL_YEAR_TABLE = """
CREATE TABLE school_years (
    school_year_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(school_year_id)) > 0),
    label TEXT NOT NULL CHECK (length(trim(label)) > 0),
    start_date TEXT NOT NULL CHECK (
        length(start_date) = 10
        AND start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND substr(start_date, 1, 4) BETWEEN '0001' AND '9999'
        AND date(julianday(start_date)) = start_date
    ),
    end_date TEXT NOT NULL CHECK (
        length(end_date) = 10
        AND end_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND substr(end_date, 1, 4) BETWEEN '0001' AND '9999'
        AND date(julianday(end_date)) = end_date
    ),
    status TEXT NOT NULL CHECK (status IN ('planned', 'current', 'closed')),
    created_at TEXT NOT NULL,
    closed_at TEXT,
    CHECK (start_date <= end_date),
    CHECK (
        (status = 'closed' AND closed_at IS NOT NULL)
        OR
        (status IN ('planned', 'current') AND closed_at IS NULL)
    )
)
"""

_SCHOOL_YEAR_INDEXES = (
    """
    CREATE UNIQUE INDEX idx_school_years_one_current
    ON school_years(status) WHERE status = 'current'
    """,
    """
    CREATE INDEX idx_school_years_date_range
    ON school_years(start_date, end_date)
    """,
    """
    CREATE INDEX idx_school_years_status_start
    ON school_years(status, start_date)
    """,
)

_SCHOOL_YEAR_TRIGGERS = (
    """
    CREATE TRIGGER trg_school_years_no_overlap_insert
    BEFORE INSERT ON school_years
    WHEN EXISTS (
        SELECT 1 FROM school_years AS existing
        WHERE NOT (
            existing.end_date < NEW.start_date
            OR existing.start_date > NEW.end_date
        )
    )
    BEGIN
        SELECT RAISE(ABORT, 'school_year_overlap');
    END
    """,
    """
    CREATE TRIGGER trg_school_years_no_overlap_update
    BEFORE UPDATE OF start_date, end_date ON school_years
    WHEN EXISTS (
        SELECT 1 FROM school_years AS existing
        WHERE existing.school_year_id <> OLD.school_year_id
          AND NOT (
              existing.end_date < NEW.start_date
              OR existing.start_date > NEW.end_date
          )
    )
    BEGIN
        SELECT RAISE(ABORT, 'school_year_overlap');
    END
    """,
    """
    CREATE TRIGGER trg_school_years_status_transition
    BEFORE UPDATE OF status ON school_years
    WHEN NOT (
        NEW.status = OLD.status
        OR (OLD.status = 'planned' AND NEW.status = 'current')
        OR (OLD.status = 'current' AND NEW.status = 'closed')
    )
    BEGIN
        SELECT RAISE(ABORT, 'school_year_status_transition_invalid');
    END
    """,
    """
    CREATE TRIGGER trg_school_years_closed_immutable
    BEFORE UPDATE ON school_years
    WHEN OLD.status = 'closed'
    BEGIN
        SELECT RAISE(ABORT, 'closed_school_year_immutable');
    END
    """,
    """
    CREATE TRIGGER trg_school_years_dates_guard
    BEFORE UPDATE OF start_date, end_date ON school_years
    WHEN (
        NEW.start_date IS NOT OLD.start_date
        OR NEW.end_date IS NOT OLD.end_date
    )
    AND (
        OLD.status <> 'planned'
        OR EXISTS (
            SELECT 1 FROM student_school_year_assignments
            WHERE school_year_id = OLD.school_year_id
        )
    )
    BEGIN
        SELECT RAISE(ABORT, 'school_year_dates_immutable');
    END
    """,
    """
    CREATE TRIGGER trg_school_years_no_delete
    BEFORE DELETE ON school_years
    BEGIN
        SELECT RAISE(ABORT, 'school_year_delete_forbidden');
    END
    """,
)

_ASSIGNMENT_TABLE = """
CREATE TABLE student_school_year_assignments (
    assignment_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(assignment_id)) > 0),
    student_id TEXT NOT NULL CHECK (length(trim(student_id)) > 0),
    school_year_id TEXT NOT NULL CHECK (length(trim(school_year_id)) > 0),
    group_id TEXT,
    course_id TEXT,
    assignment_status TEXT NOT NULL
        CHECK (assignment_status IN ('enrolled', 'exited')),
    valid_from TEXT NOT NULL CHECK (
        length(valid_from) = 10
        AND valid_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND substr(valid_from, 1, 4) BETWEEN '0001' AND '9999'
        AND date(julianday(valid_from)) = valid_from
    ),
    valid_to TEXT NOT NULL CHECK (
        length(valid_to) = 10
        AND valid_to GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND substr(valid_to, 1, 4) BETWEEN '0001' AND '9999'
        AND date(julianday(valid_to)) = valid_to
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (valid_from <= valid_to),
    CHECK (
        julianday(created_at) IS NOT NULL
        AND julianday(updated_at) IS NOT NULL
        AND julianday(updated_at) >= julianday(created_at)
    ),
    CHECK (
        (
            assignment_status = 'enrolled'
            AND group_id IS NOT NULL
            AND length(trim(group_id)) > 0
            AND course_id IS NOT NULL
            AND length(trim(course_id)) > 0
        )
        OR
        (
            assignment_status = 'exited'
            AND group_id IS NULL
            AND course_id IS NULL
        )
    ),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (school_year_id) REFERENCES school_years(school_year_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
)
"""

_ASSIGNMENT_INDEXES = (
    """
    CREATE INDEX idx_assignments_student_year_interval
    ON student_school_year_assignments(
        student_id, school_year_id, valid_from, valid_to
    )
    """,
    """
    CREATE INDEX idx_assignments_student_interval
    ON student_school_year_assignments(student_id, valid_from, valid_to)
    """,
    """
    CREATE INDEX idx_assignments_year_status_student
    ON student_school_year_assignments(
        school_year_id, assignment_status, student_id
    )
    """,
    """
    CREATE INDEX idx_assignments_year_group_interval
    ON student_school_year_assignments(
        school_year_id, group_id, valid_from, valid_to
    )
    """,
    """
    CREATE INDEX idx_assignments_year_course_interval
    ON student_school_year_assignments(
        school_year_id, course_id, valid_from, valid_to
    )
    """,
    """
    CREATE INDEX idx_assignments_last_known
    ON student_school_year_assignments(student_id, valid_to DESC, valid_from DESC)
    """,
)

_ASSIGNMENT_TRIGGERS = (
    """
    CREATE TRIGGER trg_assignments_within_school_year_insert
    BEFORE INSERT ON student_school_year_assignments
    WHEN NOT EXISTS (
        SELECT 1 FROM school_years
        WHERE school_year_id = NEW.school_year_id
          AND NEW.valid_from >= start_date
          AND NEW.valid_to <= end_date
    )
    BEGIN
        SELECT RAISE(ABORT, 'assignment_outside_school_year');
    END
    """,
    """
    CREATE TRIGGER trg_assignments_within_school_year_update
    BEFORE UPDATE OF valid_to ON student_school_year_assignments
    WHEN NOT EXISTS (
        SELECT 1 FROM school_years
        WHERE school_year_id = NEW.school_year_id
          AND NEW.valid_from >= start_date
          AND NEW.valid_to <= end_date
    )
    BEGIN
        SELECT RAISE(ABORT, 'assignment_outside_school_year');
    END
    """,
    """
    CREATE TRIGGER trg_assignments_no_overlap_insert
    BEFORE INSERT ON student_school_year_assignments
    WHEN EXISTS (
        SELECT 1 FROM student_school_year_assignments AS existing
        WHERE existing.student_id = NEW.student_id
          AND NOT (
              existing.valid_to < NEW.valid_from
              OR existing.valid_from > NEW.valid_to
          )
    )
    BEGIN
        SELECT RAISE(ABORT, 'assignment_overlap');
    END
    """,
    """
    CREATE TRIGGER trg_assignments_no_overlap_update
    BEFORE UPDATE OF valid_to ON student_school_year_assignments
    WHEN EXISTS (
        SELECT 1 FROM student_school_year_assignments AS existing
        WHERE existing.student_id = NEW.student_id
          AND existing.assignment_id <> OLD.assignment_id
          AND NOT (
              existing.valid_to < NEW.valid_from
              OR existing.valid_from > NEW.valid_to
          )
    )
    BEGIN
        SELECT RAISE(ABORT, 'assignment_overlap');
    END
    """,
    """
    CREATE TRIGGER trg_assignments_update_guard
    BEFORE UPDATE ON student_school_year_assignments
    WHEN NOT (
        NEW.assignment_id IS OLD.assignment_id
        AND NEW.student_id IS OLD.student_id
        AND NEW.school_year_id IS OLD.school_year_id
        AND NEW.group_id IS OLD.group_id
        AND NEW.course_id IS OLD.course_id
        AND NEW.assignment_status IS OLD.assignment_status
        AND NEW.valid_from IS OLD.valid_from
        AND NEW.created_at IS OLD.created_at
        AND NEW.valid_to <= OLD.valid_to
        AND julianday(NEW.updated_at) >= julianday(OLD.updated_at)
    )
    BEGIN
        SELECT RAISE(ABORT, 'assignment_update_forbidden');
    END
    """,
    """
    CREATE TRIGGER trg_assignments_no_delete
    BEFORE DELETE ON student_school_year_assignments
    BEGIN
        SELECT RAISE(ABORT, 'assignment_delete_forbidden');
    END
    """,
)

_TRANSITION_TABLE = """
CREATE TABLE school_year_transitions (
    transition_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(transition_id)) > 0),
    from_school_year_id TEXT,
    to_school_year_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(to_school_year_id)) > 0),
    operation_token TEXT NOT NULL UNIQUE
        CHECK (length(trim(operation_token)) > 0),
    plan_sha256 TEXT NOT NULL CHECK (
        length(plan_sha256) = 64
        AND plan_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    backup_sha256 TEXT NOT NULL CHECK (
        length(backup_sha256) = 64
        AND backup_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    result_counts_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    CHECK (
        from_school_year_id IS NULL
        OR from_school_year_id <> to_school_year_id
    ),
    FOREIGN KEY (from_school_year_id) REFERENCES school_years(school_year_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (to_school_year_id) REFERENCES school_years(school_year_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
)
"""

_TRANSITION_TRIGGERS = (
    """
    CREATE TRIGGER trg_school_year_transitions_no_update
    BEFORE UPDATE ON school_year_transitions
    BEGIN
        SELECT RAISE(ABORT, 'school_year_transition_update_forbidden');
    END
    """,
    """
    CREATE TRIGGER trg_school_year_transitions_no_delete
    BEFORE DELETE ON school_year_transitions
    BEGIN
        SELECT RAISE(ABORT, 'school_year_transition_delete_forbidden');
    END
    """,
)

_COURSES_V3_TABLE = """
CREATE TABLE __sj2b_courses_v3 (
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    color_key TEXT,
    color_name TEXT NOT NULL DEFAULT '',
    color_hex TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    year_level INTEGER NOT NULL CHECK (
        typeof(year_level) = 'integer' AND year_level IN (1, 2, 3)
    )
)
"""

_STUDENTS_V3_TABLE = """
CREATE TABLE __sj2b_students_v3 (
    student_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    notes TEXT,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
)
"""


def calculate_v2_source_state_sha256(
    connection: Any,
    plan: SchoolYearInitializationPlan,
) -> str:
    """Hash migration-relevant V2 state without emitting cleartext fields."""

    schema = DatabaseCompatibilityInspector.schema_identity_for_connection(
        connection
    )
    table_payloads: list[dict[str, object]] = []
    table_names = tuple(
        str(row[0])
        for row in connection.execute(
            """
            SELECT name FROM sqlite_schema
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    )
    for table_name in table_names:
        quoted_table = _quote_identifier(table_name)
        columns = tuple(
            str(row[1])
            for row in connection.execute(
                f"PRAGMA table_xinfo({quoted_table})"
            ).fetchall()
            if int(row[6]) == 0
        )
        quoted_columns = ", ".join(_quote_identifier(item) for item in columns)
        rows = connection.execute(
            f"SELECT {quoted_columns} FROM {quoted_table}"
        ).fetchall()
        row_digests = sorted(
            hashlib.sha256(
                _canonical_json_bytes(
                    [
                        _cell_digest(row[index])
                        for index in range(len(columns))
                    ]
                )
            ).hexdigest()
            for row in rows
        )
        table_payloads.append(
            {
                "count": len(rows),
                "name": table_name,
                "row_digests": row_digests,
            }
        )
    school_year = plan.confirmed_initial_school_year
    payload = {
        "course_year_levels": [
            {
                "course_id": item.course_id,
                "year_level": item.year_level,
            }
            for item in plan.confirmed_course_year_levels
        ],
        "engine_format_version": SCHOOL_YEAR_MIGRATION_ENGINE_FORMAT_VERSION,
        "initial_school_year": {
            "end_date": school_year.end_date.isoformat(),
            "label": school_year.label,
            "school_year_id": school_year.school_year_id,
            "start_date": school_year.start_date.isoformat(),
            "status": school_year.status.value,
        },
        "plan_format_version": plan.format_version,
        "schema_fingerprint": schema.fingerprint,
        "sqlite_user_version": int(
            connection.execute("PRAGMA user_version").fetchone()[0]
        ),
        "tables": table_payloads,
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def verify_v3_schema(
    connection: Any,
    *,
    expected_fingerprint: str = V3_SCHEMA_FINGERPRINT,
) -> str:
    """Verify only version and exact full schema identity of an open V3 DB."""

    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
        connection
    )
    if (
        version != TARGET_V3_DATABASE_VERSION
        or identity.fingerprint != expected_fingerprint
    ):
        raise SchoolYearMigrationError(
            SchoolYearMigrationErrorCode.V3_FINGERPRINT_MISMATCH
        )
    return identity.fingerprint


class SchoolYearV2ToV3MigrationEngine:
    """Atomically migrate only an explicitly supplied V2 connection target."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        provider_engine: DatabaseEngine = DatabaseEngine.SQLITE,
    ) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory_required")
        self._connection_factory = connection_factory
        self._provider_engine = DatabaseEngine(provider_engine)

    def migrate(
        self,
        *,
        plan: SchoolYearInitializationPlan,
        operation_token: str,
        backup_evidence: VerifiedBackupEvidence | None,
        expected_v2_fingerprint: str,
        expected_v3_fingerprint: str,
        failpoint_hook: FailpointHook | None = None,
    ) -> SchoolYearMigrationResult:
        if backup_evidence is None:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISSING
            )
        if not isinstance(backup_evidence, VerifiedBackupEvidence):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISMATCH
            )
        if any(
            not isinstance(value, str)
            or _SHA256_PATTERN.fullmatch(value) is None
            for value in (
                backup_evidence.backup_sha256,
                backup_evidence.source_state_sha256,
                backup_evidence.source_schema_fingerprint,
            )
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISMATCH
            )
        if (
            not isinstance(operation_token, str)
            or not operation_token.strip()
            or not isinstance(expected_v2_fingerprint, str)
            or _SHA256_PATTERN.fullmatch(expected_v2_fingerprint) is None
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
            )
        if (
            not isinstance(expected_v3_fingerprint, str)
            or _SHA256_PATTERN.fullmatch(expected_v3_fingerprint) is None
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V3_FINGERPRINT_MISMATCH
            )

        try:
            connection = self._connection_factory()
        except Exception as error:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
            ) from error
        committed = False
        transaction_started = False
        transition_id = _transition_id(operation_token)
        counts_json = ""
        try:
            self._require_connection_state(connection)
            self._preflight(
                connection,
                plan=plan,
                backup_evidence=backup_evidence,
                expected_v2_fingerprint=expected_v2_fingerprint,
                expected_v3_fingerprint=expected_v3_fingerprint,
            )
            connection.execute("PRAGMA foreign_keys = OFF")
            if int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) != 0:
                raise SchoolYearMigrationError(
                    SchoolYearMigrationErrorCode.FOREIGN_KEY_CHECK_FAILED
                )
            _hit(failpoint_hook, SchoolYearMigrationFailpoint.BEFORE_BEGIN)
            connection.execute("BEGIN IMMEDIATE")
            transaction_started = True
            _hit(failpoint_hook, SchoolYearMigrationFailpoint.AFTER_BEGIN)
            self._require_v2_identity(
                connection,
                plan=plan,
                expected_v2_fingerprint=expected_v2_fingerprint,
            )
            self._require_source_state(
                connection,
                plan=plan,
                backup_evidence=backup_evidence,
            )

            try:
                self._create_school_year_schema(connection)
                _hit(
                    failpoint_hook,
                    SchoolYearMigrationFailpoint.AFTER_SCHOOL_YEARS_DDL,
                )
                self._create_assignment_schema(connection)
                _hit(
                    failpoint_hook,
                    SchoolYearMigrationFailpoint.AFTER_ASSIGNMENT_DDL,
                )
                self._create_transition_schema(connection)
                _hit(
                    failpoint_hook,
                    SchoolYearMigrationFailpoint.AFTER_TRANSITION_DDL,
                )
            except SchoolYearMigrationError:
                raise
            except Exception as error:
                raise _StepFailure(
                    SchoolYearMigrationErrorCode.V3_SCHEMA_CREATE_FAILED
                ) from error

            now = datetime.now(UTC).isoformat()
            school_year = plan.confirmed_initial_school_year
            connection.execute(
                """
                INSERT INTO school_years(
                    school_year_id, label, start_date, end_date,
                    status, created_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    school_year.school_year_id,
                    school_year.label,
                    school_year.start_date.isoformat(),
                    school_year.end_date.isoformat(),
                    school_year.status.value,
                    now,
                ),
            )

            self._rebuild_courses(
                connection,
                plan.confirmed_course_year_levels,
                failpoint_hook,
            )
            current_preview = self._reclassify_v2(connection, plan)
            self._require_preview_matches_plan(current_preview, plan)
            self._insert_assignments(connection, plan, now)
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_ASSIGNMENT_INSERT,
            )
            self._rebuild_students(connection, failpoint_hook)
            self._verify_restored_schema_objects(connection)
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_SCHEMA_OBJECTS_RESTORED,
            )

            counts_json = _result_counts_json(
                students=_table_count(connection, "students"),
                courses=_table_count(connection, "courses"),
                assignments=_table_count(
                    connection, "student_school_year_assignments"
                ),
            )
            try:
                connection.execute(
                    """
                    INSERT INTO school_year_transitions(
                        transition_id, from_school_year_id, to_school_year_id,
                        operation_token, plan_sha256, backup_sha256,
                        result_counts_json, completed_at
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transition_id,
                        school_year.school_year_id,
                        operation_token,
                        plan.plan_sha256,
                        backup_evidence.backup_sha256,
                        counts_json,
                        now,
                    ),
                )
            except Exception as error:
                raise _StepFailure(
                    SchoolYearMigrationErrorCode.TRANSITION_RECEIPT_CONFLICT
                ) from error
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_TRANSITION_RECEIPT,
            )

            connection.execute(
                f"PRAGMA user_version = {TARGET_V3_DATABASE_VERSION}"
            )
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_USER_VERSION,
            )
            self._require_v3_fingerprint(connection, expected_v3_fingerprint)
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_FINGERPRINT_CHECK,
            )
            self._require_integrity(connection)
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_INTEGRITY_CHECK,
            )
            self._require_foreign_keys_clean(connection)
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_FOREIGN_KEY_CHECK,
            )
            self._require_cipher_integrity(connection)
            _hit(failpoint_hook, SchoolYearMigrationFailpoint.BEFORE_COMMIT)
            try:
                connection.commit()
            except Exception as error:
                if not bool(getattr(connection, "in_transaction", True)):
                    _close(connection)
                    if self._committed_v3_is_recognizable(
                        plan=plan,
                        operation_token=operation_token,
                        transition_id=transition_id,
                        backup_evidence=backup_evidence,
                        expected_v3_fingerprint=expected_v3_fingerprint,
                        result_counts_json=counts_json,
                    ):
                        committed = True
                        raise SchoolYearMigrationError(
                            SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                            committed=True,
                        ) from error
                raise
            transaction_started = False
            committed = True
            _hit(failpoint_hook, SchoolYearMigrationFailpoint.AFTER_COMMIT)
        except Exception as error:
            if committed:
                _close(connection)
                raise SchoolYearMigrationError(
                    SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                    committed=True,
                ) from error
            if transaction_started:
                try:
                    connection.rollback()
                except Exception:
                    pass
                _close(connection)
                rollback_verified = self._v2_is_reverified(
                    plan=plan,
                    backup_evidence=backup_evidence,
                    expected_v2_fingerprint=expected_v2_fingerprint,
                )
                cause_code = (
                    error.code
                    if isinstance(error, _StepFailure)
                    else (
                        error.code
                        if isinstance(error, SchoolYearMigrationError)
                        else None
                    )
                )
                if rollback_verified:
                    raise SchoolYearMigrationError(
                        SchoolYearMigrationErrorCode.MIGRATION_ROLLED_BACK,
                        cause_code=cause_code,
                        rollback_verified=True,
                    ) from error
                raise SchoolYearMigrationError(
                    SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                    cause_code=cause_code,
                    committed=None,
                    rollback_verified=False,
                ) from error
            _close(connection)
            if isinstance(error, SchoolYearMigrationError):
                raise
            rollback_verified = self._v2_is_reverified(
                plan=plan,
                backup_evidence=backup_evidence,
                expected_v2_fingerprint=expected_v2_fingerprint,
            )
            if rollback_verified:
                raise SchoolYearMigrationError(
                    SchoolYearMigrationErrorCode.MIGRATION_ROLLED_BACK,
                    rollback_verified=True,
                ) from error
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                committed=None,
                rollback_verified=False,
            ) from error
        finally:
            if not committed:
                _close(connection)

        _close(connection)
        reopened = None
        try:
            reopened = self._connection_factory()
            if int(reopened.execute("PRAGMA foreign_keys").fetchone()[0]) != 1:
                raise SchoolYearMigrationError(
                    SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                    committed=True,
                )
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_REOPEN_BEFORE_VERIFICATION,
            )
            self._post_commit_verify(
                reopened,
                plan=plan,
                operation_token=operation_token,
                transition_id=transition_id,
                backup_evidence=backup_evidence,
                expected_v3_fingerprint=expected_v3_fingerprint,
                result_counts_json=counts_json,
            )
        except Exception as error:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                committed=True,
            ) from error
        finally:
            if reopened is not None:
                _close(reopened)

        return SchoolYearMigrationResult(
            transition_id=transition_id,
            operation_token=operation_token,
            target_schema_fingerprint=expected_v3_fingerprint,
            result_counts_json=counts_json,
        )

    def _v2_is_reverified(
        self,
        *,
        plan: SchoolYearInitializationPlan,
        backup_evidence: VerifiedBackupEvidence,
        expected_v2_fingerprint: str,
    ) -> bool:
        connection = None
        try:
            connection = self._connection_factory()
            self._require_connection_state(connection)
            self._require_v2_identity(
                connection,
                plan=plan,
                expected_v2_fingerprint=expected_v2_fingerprint,
            )
            self._require_source_state(
                connection,
                plan=plan,
                backup_evidence=backup_evidence,
            )
            self._require_integrity(connection)
            self._require_foreign_keys_clean(connection)
            self._require_cipher_integrity(connection)
            return True
        except Exception:
            return False
        finally:
            if connection is not None:
                _close(connection)

    def _committed_v3_is_recognizable(
        self,
        *,
        plan: SchoolYearInitializationPlan,
        operation_token: str,
        transition_id: str,
        backup_evidence: VerifiedBackupEvidence,
        expected_v3_fingerprint: str,
        result_counts_json: str,
    ) -> bool:
        connection = None
        try:
            connection = self._connection_factory()
            if int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) != 1:
                return False
            self._post_commit_verify(
                connection,
                plan=plan,
                operation_token=operation_token,
                transition_id=transition_id,
                backup_evidence=backup_evidence,
                expected_v3_fingerprint=expected_v3_fingerprint,
                result_counts_json=result_counts_json,
            )
            return True
        except Exception:
            return False
        finally:
            if connection is not None:
                _close(connection)

    def _require_connection_state(self, connection: Any) -> None:
        if bool(getattr(connection, "in_transaction", False)):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
            )
        if int(connection.execute("PRAGMA query_only").fetchone()[0]) != 0:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
            )
        if int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) != 1:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.FOREIGN_KEY_CHECK_FAILED
            )
        row = connection.execute("PRAGMA cipher_version").fetchone()
        is_cipher_connection = row is not None and bool(str(row[0]).strip())
        if is_cipher_connection != (
            self._provider_engine is DatabaseEngine.SQLCIPHER
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.CIPHER_INTEGRITY_CHECK_FAILED
            )

    def _preflight(
        self,
        connection: Any,
        *,
        plan: SchoolYearInitializationPlan,
        backup_evidence: VerifiedBackupEvidence,
        expected_v2_fingerprint: str,
        expected_v3_fingerprint: str,
    ) -> None:
        self._require_v2_identity(
            connection,
            plan=plan,
            expected_v2_fingerprint=expected_v2_fingerprint,
        )
        if (
            plan.format_version
            != SCHOOL_YEAR_INITIALIZATION_PLAN_FORMAT_VERSION
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.SOURCE_STATE_MISMATCH
            )
        if (
            plan.target_schema.sqlite_user_version
            != TARGET_V3_DATABASE_VERSION
            or plan.target_schema.schema_fingerprint_sha256
            != expected_v3_fingerprint
            or expected_v3_fingerprint != V3_SCHEMA_FINGERPRINT
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V3_FINGERPRINT_MISMATCH
            )
        if plan.confirmed_initial_school_year.status is not SchoolYearStatus.CURRENT:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.INITIALIZATION_PLAN_BLOCKED
            )
        if plan.blockers:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.INITIALIZATION_PLAN_BLOCKED
            )
        self._require_course_mapping(connection, plan)
        preview = self._reclassify_v2(connection, plan)
        self._require_preview_matches_plan(preview, plan)
        self._require_source_state(
            connection,
            plan=plan,
            backup_evidence=backup_evidence,
        )
        self._require_integrity(connection)
        self._require_foreign_keys_clean(connection)
        self._require_cipher_integrity(connection)

    @staticmethod
    def _require_v2_identity(
        connection: Any,
        *,
        plan: SchoolYearInitializationPlan,
        expected_v2_fingerprint: str,
    ) -> None:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
            connection
        )
        if (
            version != 2
            or identity.fingerprint != expected_v2_fingerprint
            or plan.source_schema.sqlite_user_version != 2
            or plan.source_schema.schema_fingerprint_sha256
            != expected_v2_fingerprint
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.V2_SCHEMA_MISMATCH
            )

    @staticmethod
    def _require_source_state(
        connection: Any,
        *,
        plan: SchoolYearInitializationPlan,
        backup_evidence: VerifiedBackupEvidence,
    ) -> None:
        actual = calculate_v2_source_state_sha256(connection, plan)
        if actual != plan.source_state_sha256:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.SOURCE_STATE_MISMATCH
            )
        if (
            backup_evidence.source_state_sha256 != actual
            or backup_evidence.source_schema_fingerprint
            != plan.source_schema.schema_fingerprint_sha256
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.BACKUP_EVIDENCE_MISMATCH
            )

    @staticmethod
    def _require_course_mapping(
        connection: Any,
        plan: SchoolYearInitializationPlan,
    ) -> None:
        source_ids = {
            str(row[0])
            for row in connection.execute(
                "SELECT course_id FROM courses"
            ).fetchall()
        }
        mapping_ids = {
            item.course_id for item in plan.confirmed_course_year_levels
        }
        if source_ids != mapping_ids or len(mapping_ids) != len(
            plan.confirmed_course_year_levels
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.COURSE_LEVEL_MAPPING_INCOMPLETE
            )

    @staticmethod
    def _reclassify_v2(
        connection: Any,
        plan: SchoolYearInitializationPlan,
    ):
        group_ids = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT group_id FROM groups ORDER BY group_id"
            ).fetchall()
        )
        course_ids = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT course_id FROM courses ORDER BY course_id"
            ).fetchall()
        )
        students = tuple(
            StudentRecord(
                student_id=str(row[0]),
                first_name=str(row[1]),
                last_name=str(row[2]),
                group_id=str(row[3]),
                course_id=str(row[4]),
                student_notes="" if row[5] is None else str(row[5]),
                active=bool(row[6]),
                created_at=str(row[7]),
                updated_at=str(row[8]),
                archived_at=None if row[9] is None else str(row[9]),
            )
            for row in connection.execute(
                """
                SELECT student_id, first_name, last_name, group_id, course_id,
                       student_notes, active, created_at, updated_at, archived_at
                FROM students ORDER BY student_id
                """
            ).fetchall()
        )
        return build_school_year_initialization_preview(
            students,
            plan.confirmed_initial_school_year,
            group_ids,
            course_ids,
        )

    @staticmethod
    def _require_preview_matches_plan(preview, plan) -> None:
        if (
            len(preview.student_classifications)
            != _table_length(plan.student_classifications)
            or preview.student_classifications != plan.student_classifications
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.STUDENT_CLASSIFICATION_MISMATCH
            )
        if (
            preview.assignment_proposals != plan.assignment_proposals
            or len(
                {
                    _assignment_id(item)
                    for item in plan.assignment_proposals
                }
            )
            != len(plan.assignment_proposals)
        ):
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.ASSIGNMENT_PLAN_MISMATCH
            )

    @staticmethod
    def _create_school_year_schema(connection: Any) -> None:
        connection.execute(_SCHOOL_YEAR_TABLE)
        for statement in _SCHOOL_YEAR_INDEXES:
            connection.execute(statement)
        for statement in _SCHOOL_YEAR_TRIGGERS:
            connection.execute(statement)

    @staticmethod
    def _create_assignment_schema(connection: Any) -> None:
        connection.execute(_ASSIGNMENT_TABLE)
        for statement in _ASSIGNMENT_INDEXES:
            connection.execute(statement)
        for statement in _ASSIGNMENT_TRIGGERS:
            connection.execute(statement)

    @staticmethod
    def _create_transition_schema(connection: Any) -> None:
        connection.execute(_TRANSITION_TABLE)
        for statement in _TRANSITION_TRIGGERS:
            connection.execute(statement)

    @staticmethod
    def _rebuild_courses(
        connection: Any,
        confirmations: tuple[CourseYearLevelConfirmation, ...],
        failpoint_hook: FailpointHook | None,
    ) -> None:
        mapping = {item.course_id: item.year_level for item in confirmations}
        old_rows = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT course_id, course_name, color_key, color_name, color_hex,
                       sort_order, active
                FROM courses ORDER BY course_id
                """
            ).fetchall()
        ]
        try:
            connection.execute(_COURSES_V3_TABLE)
            connection.executemany(
                """
                INSERT INTO __sj2b_courses_v3(
                    course_id, course_name, color_key, color_name, color_hex,
                    sort_order, active, year_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(*row, mapping[str(row[0])]) for row in old_rows],
            )
            copied = [
                tuple(row)
                for row in connection.execute(
                    """
                    SELECT course_id, course_name, color_key, color_name,
                           color_hex, sort_order, active, year_level
                    FROM __sj2b_courses_v3 ORDER BY course_id
                    """
                ).fetchall()
            ]
            if [row[:7] for row in copied] != old_rows:
                raise _StepFailure(
                    SchoolYearMigrationErrorCode.COURSE_REBUILD_FAILED
                )
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_COURSE_COPY,
            )
            connection.execute("DROP TABLE courses")
            connection.execute(
                "ALTER TABLE __sj2b_courses_v3 RENAME TO courses"
            )
            connection.execute(
                "CREATE INDEX idx_courses_name ON courses(course_name)"
            )
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_COURSE_DROP_RENAME,
            )
        except _StepFailure:
            raise
        except Exception as error:
            raise _StepFailure(
                SchoolYearMigrationErrorCode.COURSE_REBUILD_FAILED
            ) from error

    @staticmethod
    def _insert_assignments(
        connection: Any,
        plan: SchoolYearInitializationPlan,
        timestamp: str,
    ) -> None:
        try:
            connection.executemany(
                """
                INSERT INTO student_school_year_assignments(
                    assignment_id, student_id, school_year_id, group_id,
                    course_id, assignment_status, valid_from, valid_to,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        _assignment_id(item),
                        item.student_id,
                        item.school_year_id,
                        item.group_id,
                        item.course_id,
                        item.assignment_status.value,
                        item.valid_from.isoformat(),
                        item.valid_to.isoformat(),
                        timestamp,
                        timestamp,
                    )
                    for item in plan.assignment_proposals
                ],
            )
            if _table_count(
                connection, "student_school_year_assignments"
            ) != len(plan.assignment_proposals):
                raise _StepFailure(
                    SchoolYearMigrationErrorCode.ASSIGNMENT_PLAN_MISMATCH
                )
        except _StepFailure:
            raise
        except Exception as error:
            raise _StepFailure(
                SchoolYearMigrationErrorCode.ASSIGNMENT_PLAN_MISMATCH
            ) from error

    @staticmethod
    def _rebuild_students(
        connection: Any,
        failpoint_hook: FailpointHook | None,
    ) -> None:
        old_rows = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT student_id, first_name, last_name, student_notes,
                       active, created_at, updated_at, archived_at
                FROM students ORDER BY student_id
                """
            ).fetchall()
        ]
        try:
            connection.execute(_STUDENTS_V3_TABLE)
            connection.execute(
                """
                INSERT INTO __sj2b_students_v3(
                    student_id, first_name, last_name, notes, active,
                    created_at, updated_at, archived_at
                )
                SELECT student_id, first_name, last_name, student_notes, active,
                       created_at, updated_at, archived_at
                FROM students
                """
            )
            copied = [
                tuple(row)
                for row in connection.execute(
                    """
                    SELECT student_id, first_name, last_name, notes, active,
                           created_at, updated_at, archived_at
                    FROM __sj2b_students_v3 ORDER BY student_id
                    """
                ).fetchall()
            ]
            if copied != old_rows:
                raise _StepFailure(
                    SchoolYearMigrationErrorCode.STUDENT_REBUILD_FAILED
                )
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_STUDENT_COPY,
            )
            connection.execute("DROP TABLE students")
            connection.execute(
                "ALTER TABLE __sj2b_students_v3 RENAME TO students"
            )
            _hit(
                failpoint_hook,
                SchoolYearMigrationFailpoint.AFTER_STUDENT_DROP_RENAME,
            )
        except _StepFailure:
            raise
        except Exception as error:
            raise _StepFailure(
                SchoolYearMigrationErrorCode.STUDENT_REBUILD_FAILED
            ) from error

    @staticmethod
    def _verify_restored_schema_objects(connection: Any) -> None:
        required = {
            "idx_courses_name",
            "idx_school_years_one_current",
            "idx_assignments_last_known",
            "trg_school_years_no_delete",
            "trg_assignments_no_delete",
            "trg_school_year_transitions_no_update",
        }
        found = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_schema
                WHERE name IN (
                    'idx_courses_name',
                    'idx_school_years_one_current',
                    'idx_assignments_last_known',
                    'trg_school_years_no_delete',
                    'trg_assignments_no_delete',
                    'trg_school_year_transitions_no_update'
                )
                """
            ).fetchall()
        }
        if found != required:
            raise _StepFailure(
                SchoolYearMigrationErrorCode.V3_SCHEMA_CREATE_FAILED
            )

    @staticmethod
    def _require_v3_fingerprint(
        connection: Any,
        expected_v3_fingerprint: str,
    ) -> None:
        identity = DatabaseCompatibilityInspector.schema_identity_for_connection(
            connection
        )
        if identity.fingerprint != expected_v3_fingerprint:
            raise _StepFailure(
                SchoolYearMigrationErrorCode.V3_FINGERPRINT_MISMATCH
            )

    @staticmethod
    def _require_integrity(connection: Any) -> None:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
        if len(rows) != 1 or str(rows[0][0]) != "ok":
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.INTEGRITY_CHECK_FAILED
            )

    @staticmethod
    def _require_foreign_keys_clean(connection: Any) -> None:
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.FOREIGN_KEY_CHECK_FAILED
            )

    def _require_cipher_integrity(self, connection: Any) -> None:
        if self._provider_engine is not DatabaseEngine.SQLCIPHER:
            return
        rows = connection.execute("PRAGMA cipher_integrity_check").fetchall()
        if rows:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.CIPHER_INTEGRITY_CHECK_FAILED
            )

    def _post_commit_verify(
        self,
        connection: Any,
        *,
        plan: SchoolYearInitializationPlan,
        operation_token: str,
        transition_id: str,
        backup_evidence: VerifiedBackupEvidence,
        expected_v3_fingerprint: str,
        result_counts_json: str,
    ) -> None:
        verify_v3_schema(
            connection,
            expected_fingerprint=expected_v3_fingerprint,
        )
        current_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM school_years WHERE status = 'current'"
            ).fetchone()[0]
        )
        if current_count != 1:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                committed=True,
            )
        row = connection.execute(
            """
            SELECT transition_id, from_school_year_id, to_school_year_id,
                   operation_token, plan_sha256, backup_sha256,
                   result_counts_json
            FROM school_year_transitions
            WHERE operation_token = ?
            """,
            (operation_token,),
        ).fetchone()
        expected = (
            transition_id,
            None,
            plan.confirmed_initial_school_year.school_year_id,
            operation_token,
            plan.plan_sha256,
            backup_evidence.backup_sha256,
            result_counts_json,
        )
        if row is None or tuple(row) != expected:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                committed=True,
            )
        counts = json.loads(result_counts_json)
        if counts != {
            "assignments": _table_count(
                connection, "student_school_year_assignments"
            ),
            "courses": _table_count(connection, "courses"),
            "school_years": _table_count(connection, "school_years"),
            "students": _table_count(connection, "students"),
        }:
            raise SchoolYearMigrationError(
                SchoolYearMigrationErrorCode.POST_COMMIT_VERIFICATION_FAILED,
                committed=True,
            )
        self._require_integrity(connection)
        self._require_foreign_keys_clean(connection)
        self._require_cipher_integrity(connection)


class _StepFailure(SchoolYearMigrationError):
    pass


def _assignment_id(assignment: StudentMembershipAssignment) -> str:
    payload = "|".join(
        (
            assignment.student_id,
            assignment.school_year_id,
            assignment.assignment_status.value,
            assignment.group_id or "",
            assignment.course_id or "",
            assignment.valid_from.isoformat(),
            assignment.valid_to.isoformat(),
        )
    ).encode("utf-8")
    return "ASY-" + hashlib.sha256(payload).hexdigest()[:32]


def _transition_id(operation_token: str) -> str:
    return "SYT-" + hashlib.sha256(operation_token.encode("utf-8")).hexdigest()[:32]


def _result_counts_json(
    *,
    students: int,
    courses: int,
    assignments: int,
) -> str:
    return json.dumps(
        {
            "assignments": assignments,
            "courses": courses,
            "school_years": 1,
            "students": students,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _cell_digest(value: object) -> str:
    if value is None:
        payload = b"null:"
    elif isinstance(value, bytes):
        payload = b"bytes:" + value
    elif isinstance(value, str):
        payload = b"text:" + value.encode("utf-8")
    elif isinstance(value, int):
        payload = b"integer:" + str(value).encode("ascii")
    elif isinstance(value, float):
        payload = b"real:" + repr(value).encode("ascii")
    else:
        payload = b"other:" + str(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _hit(
    hook: FailpointHook | None,
    failpoint: SchoolYearMigrationFailpoint,
) -> None:
    if hook is not None:
        hook(failpoint)


def _table_count(connection: Any, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _table_length(value: object) -> int:
    try:
        return len(value)  # type: ignore[arg-type]
    except TypeError:
        return -1


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _close(connection: Any) -> None:
    try:
        connection.close()
    except Exception:
        pass
