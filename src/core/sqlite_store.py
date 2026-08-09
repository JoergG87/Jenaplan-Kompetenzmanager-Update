"""SQLite storage spike for Sprint 5.2a."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Mapping
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from types import MappingProxyType

from .database_compatibility import (
    DatabaseCompatibilityError,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityStatus,
)
from .database_engine import SQLiteConnectionProvider
from .final_v4_schema import FinalV4SchemaInitializer
from .maintenance_gate import (
    MaintenanceGate,
    MaintenanceGuardedConnection,
)
from .school_year import (
    AssignmentAtDateProjection,
    AssignmentResolutionStatus,
    CurrentStudentMembershipProjection,
    V3Student,
)
from .sqlite_school_year_assignment import (
    SchoolYearAssignmentReadSession,
    SchoolYearAssignmentRepositoryError,
    V3StudentRepository,
)
from .sqlite_student_documentation_subjects import (
    SQLiteStudentDocumentationSubjectRepository,
)
from .student_documentation_subjects import (
    StudentDocumentationSubjectConfiguration,
)
from .persistence_events import (
    CompetencyFreshness,
    PersistenceEventKind,
    PersistenceEventRecord,
    PersistenceOrderingState,
    SQLitePersistenceEventRepository,
    canonical_payload_hash,
    canonical_utc_second,
    project_competency_freshness,
)

from .constants import (
    ACTIVE,
    ARCHIVED_AT,
    COLOR_HEX,
    COLOR_KEY,
    COLOR_NAME,
    COURSE_COLOR_OPTIONS,
    COURSE_GROUP_ID_PREFIX,
    COURSE_ID,
    COURSE_ID_PREFIX,
    COURSE_NAME,
    CREATED_AT,
    FIRST_NAME,
    GROUP_ID,
    GROUP_ID_PREFIX,
    GROUP_NAME,
    ID_SEQUENCE_WIDTH,
    LAST_NAME,
    MEDIA_ID_PREFIX,
    OBSERVATION_ID_PREFIX,
    LEARNING_REPORT_ID_PREFIX,
    LEARNING_REPORT_PDF_ARTIFACT_ID_PREFIX,
    LEARNING_REPORT_REVISION_ID_PREFIX,
    LEARNING_CONFERENCE_ID_PREFIX,
    LEARNING_CONFERENCE_PDF_ARTIFACT_ID_PREFIX,
    LEARNING_CONFERENCE_REVISION_ID_PREFIX,
    REPORT_DRAFT_ID_PREFIX,
    STUDENT_ID,
    UPDATED_AT,
)


from .observation import (
    ObservationCompetencyRatingRecord,
    ObservationRecord,
    ObservationRepositoryError,
    OBSERVATION_RATING_KEYS,
)
from .learning_conference_draft import (
    LEARNING_CONFERENCE_DRAFT_ID_PREFIX,
    LearningConferenceDraftError,
    LearningConferenceDraftRecord,
)
from .learning_conference import (
    COMPLETED_REVISION_STATUS,
    LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION,
    SUPERSEDED_REVISION_STATUS as LEG_SUPERSEDED_REVISION_STATUS,
    LearningConferenceCompetencySource,
    LearningConferenceCompletionError,
    LearningConferenceCompletionErrorCode,
    LearningConferenceCompletionResult,
    LearningConferenceCompletionSource,
    LearningConferenceObservationRatingSource,
    LearningConferenceObservationSource,
    LearningConferenceRecord,
    LearningConferenceRevisionHistory,
    LearningConferenceRevisionRecord,
    LearningConferenceStudentSource,
    LearningConferenceSubjectSource,
)
from .learning_conference_pdf import (
    LearningConferencePdfArtifactRecord,
    LearningConferencePdfError,
)
from .learning_report import (
    FINALIZED_REVISION_STATUS,
    LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION,
    SUPERSEDED_REVISION_STATUS,
    LearningReportCompetencyEvidenceSource,
    LearningReportCompetencySource,
    LearningReportFinalizationResult,
    LearningReportFinalizationSource,
    LearningReportObservationSource,
    LearningReportRecord,
    LearningReportRevisionHistory,
    LearningReportRevisionRecord,
    LearningReportStudentSource,
    LearningReportSubjectSource,
    ReportFinalizationError,
)
from .learning_report_pdf import (
    LearningReportPdfArtifactRecord,
    LearningReportPdfError,
)
from .records import (
    CourseRecord,
    GroupRecord,
    HISTORICAL_SCHOOL_YEAR_CLOSED_AT,
    ReferenceData,
    SEED_TIMESTAMP,
    StudentRecord,
    seed_reference_data,
)
from .report_draft import (
    ReportDraftChartSelectionRecord,
    ReportDraftError,
    ReportDraftRecord,
    ReportDraftSubjectRecord,
)
from .timetable import TIMETABLE_ENTRY_ID_PREFIX, TimetableEntry


SQLITE_SPIKE_PATH = Path("data") / "kompetenzmanager.sqlite"
DEFAULT_COURSE_GROUP_ID = "course-group-default"
DEFAULT_COURSE_GROUP_NAME = "Mathe/Deutsch Kursverbund A"


@dataclass(frozen=True)
class MasterDataGroupRecord:
    """Persisted group master-data record."""

    group_id: str
    group_name: str
    active: bool
    sort_order: int = 0


@dataclass(frozen=True)
class MasterDataCourseRecord:
    """Persisted course master-data record."""

    course_id: str
    course_name: str
    color_name: str
    color_hex: str
    active: bool
    sort_order: int = 0
    year_level: int | None = None

    def __post_init__(self) -> None:
        if type(self.year_level) is not int or self.year_level not in (1, 2, 3):
            raise ValueError("Kursstufe muss 1, 2 oder 3 sein.")


@dataclass(frozen=True)
class MasterDataCourseGroupRecord:
    """Persisted course-group record including its relations."""

    course_group_id: str
    name: str
    selected_group_ids: tuple[str, ...]
    selected_course_ids: tuple[str, ...]
    active: bool
    sort_order: int = 0


@dataclass(frozen=True)
class CompetencyRecord:
    """Persisted competency catalog record."""

    competency_id: str
    subject_id: str
    subject_name: str
    subject_full_name: str
    official_subject_name: str
    school_context_name: str
    grade_band: str
    label: str
    description: str
    learning_stage: str
    learning_area: str
    competency_group: str
    source_reference: str
    catalog_status: str
    activation_group_key: str
    sort_order: int
    active: bool
    catalog_default_active: bool
    is_core_subject: bool


@dataclass(frozen=True)
class DocumentationSubjectSettingRecord:
    """Persisted documentation-relevance setting for one subject."""

    subject_id: str
    active: bool
    updated_at: str


@dataclass(frozen=True)
class StudentCompetencyConfirmationRecord:
    """Persisted teacher-confirmed competency status for one student."""

    student_id: str
    competency_id: str
    confirmed_rating: str
    confirmed_at: str
    note: str = ""


@dataclass(frozen=True)
class StudentDocumentationProjectionBatch:
    """Refresh-local source rows for student documentation projections."""

    as_of: date
    students: tuple[V3Student, ...]
    memberships_by_student: Mapping[
        str,
        CurrentStudentMembershipProjection | AssignmentAtDateProjection,
    ]
    group_counts: Mapping[str, int]
    course_counts: Mapping[str, int]
    target_student_ids: tuple[str, ...]
    groups: tuple[GroupRecord, ...]
    courses: tuple[CourseRecord, ...]
    course_groups: tuple[MasterDataCourseGroupRecord, ...]
    competencies: tuple[CompetencyRecord, ...]
    active_documentation_subject_ids: tuple[str, ...]
    current_school_year_id: str | None
    current_school_year_label: str | None
    student_documentation_subject_configurations: Mapping[
        str,
        StudentDocumentationSubjectConfiguration,
    ]
    observations_by_student: Mapping[str, tuple[ObservationRecord, ...]]
    documents_by_student: Mapping[str, tuple[DocumentRecord, ...]]
    confirmations_by_student: Mapping[
        str,
        tuple[StudentCompetencyConfirmationRecord, ...],
    ]
    freshness_by_student: Mapping[
        str,
        Mapping[str, CompetencyFreshness],
    ]


@dataclass(frozen=True)
class DocumentRecord:
    """Persisted document or media metadata for one student."""

    document_id: str
    student_id: str
    observation_id: str
    title: str
    document_type: str
    file_path: str
    original_filename: str
    created_at: str
    note: str
    active: bool


class SQLiteDatabase:
    """Manage the Sprint 5.2a SQLite spike database."""

    def __init__(
        self,
        path: Path = SQLITE_SPIKE_PATH,
        *,
        connection_provider=None,
        create: bool = True,
        initialize_schema: bool = True,
        maintenance_gate: MaintenanceGate | None = None,
    ) -> None:
        self.path = Path(path)
        self._connection_provider = (
            connection_provider or SQLiteConnectionProvider()
        )
        self._create = bool(create)
        self._initialize_schema = bool(initialize_schema)
        self.maintenance_gate = maintenance_gate or MaintenanceGate()

    def connect(self) -> sqlite3.Connection:
        return MaintenanceGuardedConnection(
            self._connection_provider.connect(
                self.path,
                create=self._create,
            ),
            self.maintenance_gate,
        )

    def initialize_schema(self) -> None:
        """Create or accept only the exact registered Final-V4 schema."""
        if not self._initialize_schema:
            return
        if not self.path.exists() and not self.path.is_symlink():
            if not self._create:
                raise DatabaseCompatibilityError(
                    "Die Final-V4-Datenbank fehlt am ausdrücklich geöffneten Ziel."
                )
            FinalV4SchemaInitializer(
                connection_provider=self._connection_provider
            ).initialize(self.path)
            return
        with closing(self.connect()) as connection:
            result = DatabaseCompatibilityInspector().inspect_connection(
                connection
            )
            if result.status is not DatabaseCompatibilityStatus.EXACT:
                raise DatabaseCompatibilityError(result.reason)

    def ensure_master_data_defaults(self) -> None:
        """Create default master data only for empty master-data scopes."""
        self.initialize_schema()
        seed_data = seed_reference_data()
        with closing(self.connect()) as connection:
            with connection:
                group_count = connection.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
                course_count = connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
                if group_count == 0:
                    connection.executemany(
                        """
                        INSERT INTO groups (group_id, group_name, sort_order, active)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            (
                                group.group_id,
                                group.group_name,
                                index,
                                int(group.active),
                            )
                            for index, group in enumerate(seed_data.groups)
                        ),
                    )
                if course_count == 0:
                    connection.executemany(
                        """
                        INSERT INTO courses (
                            course_id,
                            course_name,
                            color_key,
                            color_name,
                            color_hex,
                            sort_order,
                            active,
                            year_level
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            _course_seed_row(course, index)
                            for index, course in enumerate(seed_data.courses)
                        ),
                    )
                self._ensure_default_course_group(connection)

    def replace_seed_data(self, data: ReferenceData) -> None:
        """Populate one empty exact Final-V4 database with deterministic data."""
        self.initialize_schema()
        with closing(self.connect()) as connection:
            table_names = tuple(
                str(row["name"])
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_schema
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()
            )
            for table_name in table_names:
                quoted_name = table_name.replace('"', '""')
                if connection.execute(
                    f'SELECT 1 FROM "{quoted_name}" LIMIT 1'
                ).fetchone() is not None:
                    raise RuntimeError(
                        "Synthetische Final-V4-Daten duerfen nur in eine "
                        "vollstaendig leere Datenbank geschrieben werden."
                    )
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.executemany(
                    """
                    INSERT INTO school_years(
                        school_year_id, label, start_date, end_date,
                        status, created_at, closed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            school_year.school_year_id,
                            school_year.label,
                            school_year.start_date.isoformat(),
                            school_year.end_date.isoformat(),
                            school_year.status.value,
                            SEED_TIMESTAMP,
                            (
                                HISTORICAL_SCHOOL_YEAR_CLOSED_AT
                                if school_year.status.value == "closed"
                                else None
                            ),
                        )
                        for school_year in data.school_years
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO groups (group_id, group_name, sort_order, active)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        (group.group_id, group.group_name, index, int(group.active))
                        for index, group in enumerate(data.groups)
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO courses (
                        course_id,
                        course_name,
                        color_key,
                        color_name,
                        color_hex,
                        sort_order,
                        active,
                        year_level
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _course_seed_row(course, index)
                        for index, course in enumerate(data.courses)
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO students (
                        student_id,
                        first_name,
                        last_name,
                        notes,
                        active,
                        created_at,
                        updated_at,
                        archived_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            student.student_id,
                            student.first_name,
                            student.last_name,
                            student.notes,
                            int(student.active),
                            student.created_at.isoformat(),
                            student.updated_at.isoformat(),
                            (
                                student.archived_at.isoformat()
                                if student.archived_at is not None
                                else None
                            ),
                        )
                        for student in data.students
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO student_school_year_assignments(
                        assignment_id,
                        student_id,
                        school_year_id,
                        group_id,
                        course_id,
                        assignment_status,
                        valid_from,
                        valid_to,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            assignment_id,
                            assignment.student_id,
                            assignment.school_year_id,
                            assignment.group_id,
                            assignment.course_id,
                            assignment.assignment_status.value,
                            assignment.valid_from.isoformat(),
                            assignment.valid_to.isoformat(),
                            SEED_TIMESTAMP,
                            SEED_TIMESTAMP,
                        )
                        for assignment_id, assignment in data.assignments
                    ),
                )
                self._ensure_default_course_group(connection)

    def _ensure_default_course_group(self, connection: sqlite3.Connection) -> None:
        course_group_count = connection.execute(
            "SELECT COUNT(*) FROM course_groups"
        ).fetchone()[0]
        if course_group_count:
            return
        group_ids = tuple(
            row[GROUP_ID]
            for row in connection.execute(
                """
                SELECT group_id
                FROM groups
                WHERE active = 1
                ORDER BY sort_order, group_id
                """
            ).fetchall()
        )
        course_ids = tuple(
            row[COURSE_ID]
            for row in connection.execute(
                """
                SELECT course_id
                FROM courses
                WHERE active = 1
                ORDER BY sort_order, course_id
                """
            ).fetchall()
        )
        if not group_ids or not course_ids:
            return
        connection.execute(
            """
            INSERT INTO course_groups (course_group_id, name, sort_order, active)
            VALUES (?, ?, ?, ?)
            """,
            (DEFAULT_COURSE_GROUP_ID, DEFAULT_COURSE_GROUP_NAME, 0, 1),
        )
        connection.executemany(
            """
            INSERT INTO course_group_student_groups (course_group_id, student_group_id)
            VALUES (?, ?)
            """,
            ((DEFAULT_COURSE_GROUP_ID, group_id) for group_id in group_ids),
        )
        connection.executemany(
            """
            INSERT INTO course_group_courses (course_group_id, course_id)
            VALUES (?, ?)
            """,
            ((DEFAULT_COURSE_GROUP_ID, course_id) for course_id in course_ids),
        )


class SQLiteStudentRepository:
    """Read V3 students with their resolved membership projection."""

    def __init__(self, database: SQLiteDatabase, *, as_of: date) -> None:
        self.database = database
        self.as_of = as_of

    def list_students(self) -> tuple[StudentRecord, ...]:
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN")
            try:
                students = V3StudentRepository(connection).list_all()
                memberships = SchoolYearAssignmentReadSession(
                    connection
                ).current_memberships(
                    tuple(student.student_id for student in students),
                    as_of=self.as_of,
                )
                membership_by_student = {
                    membership.student_id: membership
                    for membership in memberships
                }
                return tuple(
                    _student_record_from_v3(
                        student,
                        membership_by_student.get(student.student_id),
                    )
                    for student in students
                )
            finally:
                connection.rollback()

    def get_student(self, student_id: str) -> StudentRecord | None:
        return self.get_student_by_id(student_id)

    def get_student_by_id(self, student_id: str) -> StudentRecord | None:
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN")
            try:
                student = V3StudentRepository(connection).get_by_id(student_id)
                if student is None:
                    return None
                membership = SchoolYearAssignmentReadSession(
                    connection
                ).current_membership(student_id, as_of=self.as_of)
                return _student_record_from_v3(student, membership)
            finally:
                connection.rollback()


class SQLiteObservationRepository:
    """Read and write observation records in SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_observations(self) -> tuple[ObservationRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    observation_id,
                    student_id,
                    date,
                    subject_id,
                    context,
                    note,
                    active,
                    created_at,
                    updated_at
                FROM observations
                ORDER BY date DESC, observation_id DESC
                """
            ).fetchall()
            return tuple(
                self._observation_from_row(connection, row)
                for row in rows
            )

    def list_observations_for_student(
        self,
        student_id: str,
    ) -> tuple[ObservationRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    observation_id,
                    student_id,
                    date,
                    subject_id,
                    context,
                    note,
                    active,
                    created_at,
                    updated_at
                FROM observations
                WHERE student_id = ? AND active = 1
                ORDER BY date DESC, observation_id DESC
                """,
                (student_id,),
            ).fetchall()
            return tuple(
                self._observation_from_row(connection, row)
                for row in rows
            )

    def get_observation(self, observation_id: str) -> ObservationRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    observation_id,
                    student_id,
                    date,
                    subject_id,
                    context,
                    note,
                    active,
                    created_at,
                    updated_at
                FROM observations
                WHERE observation_id = ?
                """,
                (observation_id,),
            ).fetchone()
            if row is None:
                return None
            return self._observation_from_row(connection, row)

    def create_observation(
        self,
        observation: ObservationRecord,
        *,
        operation_token: str = "",
    ) -> ObservationRecord:
        operation_token = operation_token or uuid.uuid4().hex
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if observation.observation_id:
                    existing = connection.execute(
                        """
                        SELECT 1
                        FROM observations
                        WHERE observation_id = ?
                        """,
                        (observation.observation_id,),
                    ).fetchone()
                    if existing is not None:
                        raise ObservationRepositoryError(
                            "observation_id existiert bereits: "
                            f"{observation.observation_id}"
                        )
                else:
                    observation = ObservationRecord(
                        self._next_observation_id(connection),
                        observation.student_id,
                        observation.date,
                        observation.subject_id,
                        observation.context,
                        observation.note,
                        observation.active,
                        observation.created_at,
                        observation.updated_at,
                        observation.competency_ratings,
                    )
                payload_hash = canonical_payload_hash(
                    _observation_event_payload(observation)
                )
                technical_timestamp = _required_event_timestamp(
                    observation.updated_at
                )
                connection.execute(
                    """
                    INSERT INTO observations (
                        observation_id,
                        student_id,
                        date,
                        subject_id,
                        context,
                        note,
                        active,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        observation.observation_id,
                        observation.student_id,
                        observation.date,
                        observation.subject_id,
                        observation.context,
                        observation.note,
                        int(observation.active),
                        observation.created_at,
                        observation.updated_at,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO observation_competency_ratings (
                        observation_id,
                        competency_id,
                        subject_id,
                        subject_display_name,
                        learning_area,
                        competency_group,
                        competency_text,
                        rating
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            observation.observation_id,
                            rating.competency_id,
                            rating.subject_id,
                            rating.subject_display_name,
                            rating.learning_area,
                            rating.competency_group,
                            rating.competency_text,
                            rating.rating,
                        )
                        for rating in observation.competency_ratings
                    ),
                )
                SQLitePersistenceEventRepository.append(
                    connection,
                    PersistenceEventRecord(
                        None,
                        operation_token,
                        0,
                        payload_hash,
                        PersistenceEventKind.OBSERVATION_CREATED.value,
                        observation.student_id,
                        None,
                        observation.observation_id,
                        technical_timestamp,
                        PersistenceOrderingState.NOT_APPLICABLE.value,
                    ),
                )
                for operation_index, rating in enumerate(
                    sorted(
                        observation.competency_ratings,
                        key=lambda item: item.competency_id,
                    ),
                    start=1,
                ):
                    SQLitePersistenceEventRepository.append(
                        connection,
                        PersistenceEventRecord(
                            None,
                            operation_token,
                            operation_index,
                            payload_hash,
                            PersistenceEventKind.OBSERVATION_COMPETENCY_CHANGED.value,
                            observation.student_id,
                            rating.competency_id,
                            observation.observation_id,
                            technical_timestamp,
                            PersistenceOrderingState.ORDERED.value,
                        ),
                    )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return observation

    def _next_observation_id(self, connection: sqlite3.Connection) -> str:
        used_ids = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT observation_id
                FROM observations
                """
            ).fetchall()
        }
        next_number = 1
        while True:
            observation_id = (
                f"{OBSERVATION_ID_PREFIX}-"
                f"{next_number:0{ID_SEQUENCE_WIDTH}d}"
            )
            if observation_id not in used_ids:
                return observation_id
            next_number += 1

    def update_observation(
        self,
        observation: ObservationRecord,
        *,
        operation_token: str = "",
    ) -> ObservationRecord:
        existing = self.get_observation(observation.observation_id)
        if existing is None:
            raise ObservationRepositoryError(
                f"observation_id nicht gefunden: {observation.observation_id}"
            )
        if _observation_business_payload(existing) == _observation_business_payload(
            observation
        ):
            return existing
        operation_token = operation_token or uuid.uuid4().hex
        payload_hash = canonical_payload_hash(
            {
                "before": _observation_event_payload(existing),
                "after": _observation_event_payload(observation),
            }
        )
        technical_timestamp = _required_event_timestamp(observation.updated_at)
        affected_pairs = _affected_observation_pairs(existing, observation)
        affected_event_kind = (
            PersistenceEventKind.OBSERVATION_DEACTIVATED.value
            if existing.active and not observation.active
            else PersistenceEventKind.OBSERVATION_COMPETENCY_CHANGED.value
        )
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE observations
                    SET
                        student_id = ?,
                        date = ?,
                        subject_id = ?,
                        context = ?,
                        note = ?,
                        active = ?,
                        updated_at = ?
                    WHERE observation_id = ?
                    """,
                    (
                        observation.student_id,
                        observation.date,
                        observation.subject_id,
                        observation.context,
                        observation.note,
                        int(observation.active),
                        observation.updated_at,
                        observation.observation_id,
                    ),
                )
                connection.execute(
                    """
                    DELETE FROM observation_competency_ratings
                    WHERE observation_id = ?
                    """,
                    (observation.observation_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO observation_competency_ratings (
                        observation_id,
                        competency_id,
                        subject_id,
                        subject_display_name,
                        learning_area,
                        competency_group,
                        competency_text,
                        rating
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            observation.observation_id,
                            rating.competency_id,
                            rating.subject_id,
                            rating.subject_display_name,
                            rating.learning_area,
                            rating.competency_group,
                            rating.competency_text,
                            rating.rating,
                        )
                        for rating in observation.competency_ratings
                    ),
                )
                SQLitePersistenceEventRepository.append(
                    connection,
                    PersistenceEventRecord(
                        None,
                        operation_token,
                        0,
                        payload_hash,
                        PersistenceEventKind.OBSERVATION_UPDATED.value,
                        observation.student_id,
                        None,
                        observation.observation_id,
                        technical_timestamp,
                        PersistenceOrderingState.NOT_APPLICABLE.value,
                    ),
                )
                for operation_index, (student_id, competency_id) in enumerate(
                    sorted(affected_pairs),
                    start=1,
                ):
                    SQLitePersistenceEventRepository.append(
                        connection,
                        PersistenceEventRecord(
                            None,
                            operation_token,
                            operation_index,
                            payload_hash,
                            affected_event_kind,
                            student_id,
                            competency_id,
                            observation.observation_id,
                            technical_timestamp,
                            PersistenceOrderingState.ORDERED.value,
                        ),
                    )
        return observation

    def deactivate_observation(
        self,
        observation_id: str,
        updated_at: str,
    ) -> ObservationRecord:
        observation = self.get_observation(observation_id)
        if observation is None:
            raise ObservationRepositoryError(
                f"observation_id nicht gefunden: {observation_id}"
            )
        if not observation.active:
            return observation
        inactive_observation = ObservationRecord(
            observation.observation_id,
            observation.student_id,
            observation.date,
            observation.subject_id,
            observation.context,
            observation.note,
            False,
            observation.created_at,
            updated_at,
            observation.competency_ratings,
        )
        operation_token = uuid.uuid4().hex
        payload_hash = canonical_payload_hash(
            {
                "before": _observation_event_payload(observation),
                "after": _observation_event_payload(inactive_observation),
            }
        )
        technical_timestamp = _required_event_timestamp(updated_at)
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE observations
                    SET active = 0, updated_at = ?
                    WHERE observation_id = ?
                    """,
                    (updated_at, observation_id),
                )
                SQLitePersistenceEventRepository.append(
                    connection,
                    PersistenceEventRecord(
                        None,
                        operation_token,
                        0,
                        payload_hash,
                        PersistenceEventKind.OBSERVATION_UPDATED.value,
                        observation.student_id,
                        None,
                        observation.observation_id,
                        technical_timestamp,
                        PersistenceOrderingState.NOT_APPLICABLE.value,
                    ),
                )
                for operation_index, rating in enumerate(
                    sorted(
                        observation.competency_ratings,
                        key=lambda item: item.competency_id,
                    ),
                    start=1,
                ):
                    SQLitePersistenceEventRepository.append(
                        connection,
                        PersistenceEventRecord(
                            None,
                            operation_token,
                            operation_index,
                            payload_hash,
                            PersistenceEventKind.OBSERVATION_DEACTIVATED.value,
                            observation.student_id,
                            rating.competency_id,
                            observation.observation_id,
                            technical_timestamp,
                            PersistenceOrderingState.ORDERED.value,
                        ),
                    )
        return inactive_observation

    def _ratings_for(
        self,
        connection: sqlite3.Connection,
        observation_id: str,
    ) -> tuple[ObservationCompetencyRatingRecord, ...]:
        rows = connection.execute(
            """
            SELECT
                competency_id,
                subject_id,
                subject_display_name,
                learning_area,
                competency_group,
                competency_text,
                rating
            FROM observation_competency_ratings
            WHERE observation_id = ?
            ORDER BY competency_id
            """,
            (observation_id,),
        ).fetchall()
        return tuple(
            ObservationCompetencyRatingRecord(
                row["competency_id"],
                row["subject_id"],
                row["subject_display_name"],
                row["learning_area"],
                row["competency_group"] or "",
                row["competency_text"],
                row["rating"],
            )
            for row in rows
        )

    def _observation_from_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> ObservationRecord:
        return ObservationRecord(
            row["observation_id"],
            row[STUDENT_ID],
            row["date"],
            row["subject_id"],
            row["context"] or "",
            row["note"] or "",
            bool(row[ACTIVE]),
            row[CREATED_AT],
            row[UPDATED_AT],
            self._ratings_for(connection, row["observation_id"]),
        )


class SQLiteDocumentRepository:
    """Read and write document and media metadata in SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create_document(self, document: DocumentRecord) -> DocumentRecord:
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO documents (
                        document_id,
                        student_id,
                        observation_id,
                        title,
                        document_type,
                        file_path,
                        original_filename,
                        created_at,
                        note,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _document_to_row(document),
                )
        return document

    def get_document(self, document_id: str) -> DocumentRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT document_id, student_id, observation_id, title,
                       document_type, file_path, original_filename, created_at,
                       note, active
                FROM documents WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        return None if row is None else _document_from_row(row)

    def get_active_general_document(
        self, document_id: str
    ) -> DocumentRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT document_id, student_id, observation_id, title,
                       document_type, file_path, original_filename, created_at,
                       note, active
                FROM documents
                WHERE document_id = ? AND observation_id IS NULL AND active = 1
                """,
                (document_id,),
            ).fetchone()
        return None if row is None else _document_from_row(row)

    def update_general_document(self, document: DocumentRecord) -> None:
        with closing(self.database.connect()) as connection:
            with connection:
                changed = connection.execute(
                    """
                    UPDATE documents
                    SET title = ?, document_type = ?, file_path = ?,
                        original_filename = ?, note = ?
                    WHERE document_id = ? AND observation_id IS NULL
                      AND active = 1
                    """,
                    (
                        document.title,
                        document.document_type,
                        document.file_path,
                        document.original_filename,
                        document.note,
                        document.document_id,
                    ),
                ).rowcount
        if changed != 1:
            raise LookupError("managed_document_not_found")

    def delete_general_document(self, document_id: str) -> None:
        with closing(self.database.connect()) as connection:
            with connection:
                changed = connection.execute(
                    """
                    DELETE FROM documents
                    WHERE document_id = ? AND observation_id IS NULL
                    """,
                    (document_id,),
                ).rowcount
        if changed != 1:
            raise LookupError("managed_document_not_found")

    def deactivate_general_document(self, document_id: str) -> None:
        with closing(self.database.connect()) as connection:
            with connection:
                changed = connection.execute(
                    """
                    UPDATE documents SET active = 0
                    WHERE document_id = ? AND observation_id IS NULL
                      AND active = 1
                    """,
                    (document_id,),
                ).rowcount
        if changed != 1:
            raise LookupError("managed_document_not_found")

    def list_documents_for_student(
        self,
        student_id: str,
    ) -> tuple[DocumentRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    document_id,
                    student_id,
                    observation_id,
                    title,
                    document_type,
                    file_path,
                    original_filename,
                    created_at,
                    note,
                    active
                FROM documents
                WHERE student_id = ? AND active = 1
                ORDER BY created_at DESC, document_id DESC
                """,
                (student_id,),
            ).fetchall()
        return tuple(_document_from_row(row) for row in rows)

    def list_documents_for_observation(
        self,
        observation_id: str,
    ) -> tuple[DocumentRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    document_id,
                    student_id,
                    observation_id,
                    title,
                    document_type,
                    file_path,
                    original_filename,
                    created_at,
                    note,
                    active
                FROM documents
                WHERE observation_id = ? AND active = 1
                ORDER BY created_at DESC, document_id DESC
                """,
                (observation_id,),
            ).fetchall()
        return tuple(_document_from_row(row) for row in rows)

    def deactivate_document(self, document_id: str) -> None:
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE documents
                    SET active = 0
                    WHERE document_id = ?
                    """,
                    (document_id,),
                )

    def next_document_id(self) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT document_id
                FROM documents
                """
            ).fetchall()
        used_ids = {row["document_id"] for row in rows}
        next_number = 1
        while True:
            document_id = f"{MEDIA_ID_PREFIX}-{next_number:0{ID_SEQUENCE_WIDTH}}"
            if document_id not in used_ids:
                return document_id
            next_number += 1


class SQLiteTimetableRepository:
    """Persist recurring timetable entries without resolving display names."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_entries(self) -> tuple[TimetableEntry, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM timetable_entries
                WHERE deleted_at = ''
                ORDER BY weekday, start_time, end_time, sort_order, timetable_entry_id
                """
            ).fetchall()
        return tuple(_timetable_entry_from_row(row) for row in rows)

    def get_entry(self, timetable_entry_id: str) -> TimetableEntry | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT * FROM timetable_entries
                WHERE timetable_entry_id = ? AND deleted_at = ''
                """,
                (timetable_entry_id,),
            ).fetchone()
        return _timetable_entry_from_row(row) if row is not None else None

    def create_entry(self, entry: TimetableEntry) -> TimetableEntry:
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO timetable_entries (
                        timetable_entry_id, weekday, start_time, end_time,
                        subject_id, target_type, target_id, room, active,
                        sort_order, created_at, updated_at, deleted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _timetable_entry_values(entry),
                )
        return entry

    def update_entry(self, entry: TimetableEntry) -> TimetableEntry:
        with closing(self.database.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE timetable_entries
                    SET weekday = ?, start_time = ?, end_time = ?, subject_id = ?,
                        target_type = ?, target_id = ?, room = ?, active = ?,
                        sort_order = ?, created_at = ?, updated_at = ?, deleted_at = ?
                    WHERE timetable_entry_id = ?
                    """,
                    (*_timetable_entry_values(entry)[1:], entry.timetable_entry_id),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Stundenplaneintrag konnte nicht aktualisiert werden.")
        return entry

    def next_timetable_entry_id(self) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                "SELECT timetable_entry_id FROM timetable_entries"
            ).fetchall()
        largest = 0
        for row in rows:
            value = row["timetable_entry_id"]
            if value.startswith(TIMETABLE_ENTRY_ID_PREFIX):
                suffix = value[len(TIMETABLE_ENTRY_ID_PREFIX):]
                if suffix.isdigit():
                    largest = max(largest, int(suffix))
        return f"{TIMETABLE_ENTRY_ID_PREFIX}{largest + 1:06d}"

    def next_sort_order(self, weekday: int) -> int:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_sort_order
                FROM timetable_entries
                WHERE weekday = ?
                """,
                (weekday,),
            ).fetchone()
        return int(row["next_sort_order"])


class SQLiteGroupRepository:
    """Read group records from SQLite for the projection spike."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_groups(self) -> tuple[GroupRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT group_id, group_name, active
                FROM groups
                ORDER BY group_id
                """
            ).fetchall()
        return tuple(
            GroupRecord(row[GROUP_ID], row[GROUP_NAME], bool(row[ACTIVE]))
            for row in rows
        )


class SQLiteCourseRepository:
    """Read course records from SQLite for the projection spike."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_courses(self) -> tuple[CourseRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    course_id, course_name, color_key, color_hex, active,
                    year_level
                FROM courses
                ORDER BY sort_order, course_id
                """
            ).fetchall()
        return tuple(
            CourseRecord(
                row[COURSE_ID],
                row[COURSE_NAME],
                (row[COLOR_HEX] or row[COLOR_KEY] or "").lstrip("#"),
                bool(row[ACTIVE]),
                int(row["year_level"]),
            )
            for row in rows
        )


class SQLiteCompetencyRepository:
    """Read and seed the persistent competency catalog in SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def ensure_catalog_defaults(self, entries: tuple[object, ...]) -> None:
        """Import catalog entries idempotently without deleting local records."""
        self.database.initialize_schema()
        with closing(self.database.connect()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO competencies (
                        competency_id,
                        subject_id,
                        subject_name,
                        subject_full_name,
                        official_subject_name,
                        school_context_name,
                        grade_band,
                        label,
                        description,
                        learning_stage,
                        learning_area,
                        competency_group,
                        source_reference,
                        catalog_status,
                        activation_group_key,
                        sort_order,
                        active,
                        catalog_default_active,
                        is_core_subject
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(competency_id) DO UPDATE SET
                        subject_id = excluded.subject_id,
                        subject_name = excluded.subject_name,
                        subject_full_name = excluded.subject_full_name,
                        official_subject_name = excluded.official_subject_name,
                        school_context_name = excluded.school_context_name,
                        grade_band = excluded.grade_band,
                        label = excluded.label,
                        description = excluded.description,
                        learning_stage = excluded.learning_stage,
                        learning_area = excluded.learning_area,
                        competency_group = excluded.competency_group,
                        source_reference = excluded.source_reference,
                        catalog_status = excluded.catalog_status,
                        activation_group_key = excluded.activation_group_key,
                        sort_order = excluded.sort_order,
                        active = competencies.active,
                        catalog_default_active = excluded.catalog_default_active,
                        is_core_subject = excluded.is_core_subject
                    """,
                    (
                        _competency_catalog_row(entry, index)
                        for index, entry in enumerate(entries)
                    ),
                )

    def list_competencies(self) -> tuple[CompetencyRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    competency_id,
                    subject_id,
                    subject_name,
                    subject_full_name,
                    official_subject_name,
                    school_context_name,
                    grade_band,
                    label,
                    description,
                    learning_stage,
                    learning_area,
                    competency_group,
                    source_reference,
                    catalog_status,
                    activation_group_key,
                    sort_order,
                    active,
                    catalog_default_active,
                    is_core_subject
                FROM competencies
                ORDER BY sort_order, competency_id
                """
            ).fetchall()
        return tuple(_competency_from_row(row) for row in rows)

    def get_competency(self, competency_id: str) -> CompetencyRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    competency_id,
                    subject_id,
                    subject_name,
                    subject_full_name,
                    official_subject_name,
                    school_context_name,
                    grade_band,
                    label,
                    description,
                    learning_stage,
                    learning_area,
                    competency_group,
                    source_reference,
                    catalog_status,
                    activation_group_key,
                    sort_order,
                    active,
                    catalog_default_active,
                    is_core_subject
                FROM competencies
                WHERE competency_id = ?
                """,
                (competency_id,),
            ).fetchone()
        if row is None:
            return None
        return _competency_from_row(row)


class SQLiteDocumentationSubjectSettingsRepository:
    """Read and write documentation-relevant subject settings."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_documentation_subject_settings(
        self,
    ) -> tuple[DocumentationSubjectSettingRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT subject_id, active, updated_at
                FROM documentation_subject_settings
                ORDER BY subject_id
                """
            ).fetchall()
        return tuple(self._setting_from_row(row) for row in rows)

    def list_active_documentation_subject_ids(self) -> tuple[str, ...]:
        settings = self.list_documentation_subject_settings()
        if not settings:
            return self._active_catalog_subject_ids()
        active_subject_ids = {
            setting.subject_id
            for setting in settings
            if setting.active
        }
        return self._sort_subject_ids(active_subject_ids)

    def save_active_documentation_subject_ids(
        self,
        subject_ids: tuple[str, ...],
        *,
        updated_at: str | None = None,
    ) -> tuple[DocumentationSubjectSettingRecord, ...]:
        active_catalog_subject_ids = self._active_catalog_subject_ids()
        active_subject_ids = {
            subject_id.strip()
            for subject_id in subject_ids
            if subject_id.strip()
        }
        timestamp = updated_at or datetime.now(UTC).replace(microsecond=0).isoformat()
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute("DELETE FROM documentation_subject_settings")
                connection.executemany(
                    """
                    INSERT INTO documentation_subject_settings (
                        subject_id,
                        active,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        (
                            subject_id,
                            int(subject_id in active_subject_ids),
                            timestamp,
                        )
                        for subject_id in active_catalog_subject_ids
                    ),
                )
        return self.list_documentation_subject_settings()

    def _active_catalog_subject_ids(self) -> tuple[str, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT subject_id, MIN(sort_order) AS subject_sort_order
                FROM competencies
                WHERE active = 1
                GROUP BY subject_id
                ORDER BY subject_sort_order, subject_id
                """
            ).fetchall()
        return tuple(row["subject_id"] for row in rows)

    def _sort_subject_ids(self, subject_ids: set[str]) -> tuple[str, ...]:
        catalog_order = {
            subject_id: index
            for index, subject_id in enumerate(self._active_catalog_subject_ids())
        }
        fallback_index = len(catalog_order)
        return tuple(
            sorted(
                subject_ids,
                key=lambda subject_id: (
                    catalog_order.get(subject_id, fallback_index),
                    subject_id,
                ),
            )
        )

    def _setting_from_row(
        self,
        row: sqlite3.Row,
    ) -> DocumentationSubjectSettingRecord:
        return DocumentationSubjectSettingRecord(
            row["subject_id"],
            bool(row[ACTIVE]),
            row[UPDATED_AT],
        )


class SQLiteStudentCompetencyConfirmationRepository:
    """Read and write teacher-confirmed competency status records."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_confirmations_for_student(
        self,
        student_id: str,
    ) -> tuple[StudentCompetencyConfirmationRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT student_id, competency_id, confirmed_rating, confirmed_at, note
                FROM student_competency_confirmations
                WHERE student_id = ?
                ORDER BY competency_id
                """,
                (student_id,),
            ).fetchall()
        return tuple(self._confirmation_from_row(row) for row in rows)

    def get_confirmation(
        self,
        student_id: str,
        competency_id: str,
    ) -> StudentCompetencyConfirmationRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT student_id, competency_id, confirmed_rating, confirmed_at, note
                FROM student_competency_confirmations
                WHERE student_id = ? AND competency_id = ?
                """,
                (student_id, competency_id),
            ).fetchone()
        if row is None:
            return None
        return self._confirmation_from_row(row)

    def upsert_confirmation(
        self,
        confirmation: StudentCompetencyConfirmationRecord,
        *,
        operation_token: str = "",
    ) -> StudentCompetencyConfirmationRecord:
        self._validate_confirmation(confirmation)
        operation_token = operation_token or uuid.uuid4().hex
        payload_hash = canonical_payload_hash(
            {
                "student_id": confirmation.student_id,
                "competency_id": confirmation.competency_id,
                "confirmed_rating": confirmation.confirmed_rating,
                "confirmed_at": confirmation.confirmed_at,
                "note": confirmation.note,
            }
        )
        technical_timestamp = _required_event_timestamp(
            confirmation.confirmed_at
        )
        with closing(self.database.connect()) as connection:
            with connection:
                existing_events = connection.execute(
                    """
                    SELECT
                        operation_index,
                        operation_payload_hash,
                        event_kind,
                        student_id,
                        competency_id,
                        observation_id,
                        technical_timestamp,
                        ordering_state
                    FROM persistence_events
                    WHERE operation_token = ?
                    ORDER BY operation_index
                    """,
                    (operation_token,),
                ).fetchall()
                if existing_events:
                    expected = (
                        0,
                        payload_hash,
                        PersistenceEventKind.CONFIRMATION_UPSERTED.value,
                        confirmation.student_id,
                        confirmation.competency_id,
                        None,
                        technical_timestamp,
                        PersistenceOrderingState.ORDERED.value,
                    )
                    if len(existing_events) != 1 or tuple(existing_events[0]) != expected:
                        raise ValueError(
                            "operation_token ist an eine andere Bestaetigung gebunden."
                        )
                    return confirmation
                connection.execute(
                    """
                    INSERT INTO student_competency_confirmations (
                        student_id,
                        competency_id,
                        confirmed_rating,
                        confirmed_at,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, competency_id) DO UPDATE SET
                        confirmed_rating = excluded.confirmed_rating,
                        confirmed_at = excluded.confirmed_at,
                        note = excluded.note
                    """,
                    (
                        confirmation.student_id,
                        confirmation.competency_id,
                        confirmation.confirmed_rating,
                        confirmation.confirmed_at,
                        confirmation.note,
                    ),
                )
                SQLitePersistenceEventRepository.append(
                    connection,
                    PersistenceEventRecord(
                        None,
                        operation_token,
                        0,
                        payload_hash,
                        PersistenceEventKind.CONFIRMATION_UPSERTED.value,
                        confirmation.student_id,
                        confirmation.competency_id,
                        None,
                        technical_timestamp,
                        PersistenceOrderingState.ORDERED.value,
                    ),
                )
        return confirmation

    def _validate_confirmation(
        self,
        confirmation: StudentCompetencyConfirmationRecord,
    ) -> None:
        if not confirmation.student_id.strip():
            raise ValueError("student_id darf nicht leer sein.")
        if not confirmation.competency_id.strip():
            raise ValueError("competency_id darf nicht leer sein.")
        if confirmation.confirmed_rating not in OBSERVATION_RATING_KEYS:
            raise ValueError(f"Ungueltige Bewertung: {confirmation.confirmed_rating}")
        if not confirmation.confirmed_at.strip():
            raise ValueError("confirmed_at darf nicht leer sein.")

    def _confirmation_from_row(
        self,
        row: sqlite3.Row,
    ) -> StudentCompetencyConfirmationRecord:
        return StudentCompetencyConfirmationRecord(
            row[STUDENT_ID],
            row["competency_id"],
            row["confirmed_rating"],
            row["confirmed_at"],
            row["note"] or "",
        )


class SQLiteStudentDocumentationProjectionRepository:
    """Load the student-list and heatmap source rows in one read snapshot."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def read_batch(
        self,
        *,
        as_of: date,
        student_id: str | None = None,
        group_id: str | None = None,
        group_ids: tuple[str, ...] = (),
        course_id: str | None = None,
        course_ids: tuple[str, ...] = (),
        course_group_id: str | None = None,
        target_group_id: str | None = None,
        target_course_id: str | None = None,
        target_course_group_id: str | None = None,
        historical_membership: bool = False,
        include_membership: bool = True,
        include_documents: bool = False,
    ) -> StudentDocumentationProjectionBatch:
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN")
            try:
                assignments = SchoolYearAssignmentReadSession(connection)
                if student_id is not None:
                    if not include_membership:
                        memberships: tuple[
                            CurrentStudentMembershipProjection
                            | AssignmentAtDateProjection,
                            ...,
                        ] = ()
                    elif historical_membership:
                        memberships = (
                            assignments.assignment_at_date(
                                student_id,
                                as_of,
                            ),
                        )
                    else:
                        memberships = (
                            assignments.current_membership(
                                student_id,
                                as_of=as_of,
                            ),
                        )
                    group_counts: Mapping[str, int] = MappingProxyType({})
                    course_counts: Mapping[str, int] = MappingProxyType({})
                else:
                    membership_snapshot = (
                        assignments.current_membership_snapshot(
                            as_of=as_of,
                            group_id=group_id,
                            group_ids=group_ids,
                            course_id=course_id,
                            course_ids=course_ids,
                            course_group_id=course_group_id,
                        )
                    )
                    self._require_current_membership_snapshot(
                        membership_snapshot
                    )
                    memberships = membership_snapshot.memberships
                    group_counts = membership_snapshot.group_counts
                    course_counts = membership_snapshot.course_counts
                membership_by_student = {
                    membership.student_id: membership
                    for membership in memberships
                }
                student_ids = (
                    (student_id,)
                    if student_id is not None
                    else tuple(membership_by_student)
                )
                student_by_id = V3StudentRepository(connection).list_by_ids(
                    student_ids
                )
                students = tuple(
                    student_by_id[student_id]
                    for student_id in student_ids
                    if student_id in student_by_id
                )
                scope_sql, scope_parameters = self._student_scope_sql(
                    student_ids
                )
                target_student_ids = student_ids
                if any(
                    (
                        target_group_id is not None,
                        target_course_id is not None,
                        target_course_group_id is not None,
                    )
                ):
                    target_snapshot = assignments.current_membership_snapshot(
                        as_of=as_of,
                        group_id=target_group_id,
                        course_id=target_course_id,
                        course_group_id=target_course_group_id,
                    )
                    self._require_current_membership_snapshot(target_snapshot)
                    target_student_ids = tuple(
                        membership.student_id
                        for membership in target_snapshot.memberships
                    )
                groups = self._groups(connection)
                courses = self._courses(connection)
                course_groups = self._course_groups(connection)
                competencies = self._competencies(connection)
                active_documentation_subject_ids = (
                    self._active_documentation_subject_ids(
                        connection,
                        competencies,
                    )
                )
                current_school_year_id = (
                    getattr(memberships[0], "current_school_year_id", None)
                    if memberships
                    else None
                )
                current_school_year_label = (
                    getattr(memberships[0], "current_school_year_label", None)
                    if memberships
                    else None
                )
                student_subject_configurations: dict[
                    str,
                    StudentDocumentationSubjectConfiguration,
                ] = {}
                if student_id is not None and current_school_year_id is not None:
                    student_subject_configurations[student_id] = (
                        SQLiteStudentDocumentationSubjectRepository(
                            connection
                        ).configuration(
                            student_id,
                            current_school_year_id,
                        )
                    )
                ratings_by_observation = self._ratings_by_observation(
                    connection,
                    scope_sql,
                    scope_parameters,
                )
                observations_by_student = self._observations_by_student(
                    connection,
                    scope_sql,
                    scope_parameters,
                    ratings_by_observation,
                )
                documents_by_student = (
                    self._documents_by_student(
                        connection,
                        scope_sql,
                        scope_parameters,
                    )
                    if include_documents
                    else {}
                )
                confirmations_by_student = self._confirmations_by_student(
                    connection,
                    scope_sql,
                    scope_parameters,
                )
                freshness_by_student = self._freshness_by_student(
                    connection,
                    scope_sql,
                    scope_parameters,
                )
                return StudentDocumentationProjectionBatch(
                    as_of=as_of,
                    students=students,
                    memberships_by_student=MappingProxyType(
                        membership_by_student
                    ),
                    group_counts=group_counts,
                    course_counts=course_counts,
                    target_student_ids=target_student_ids,
                    groups=groups,
                    courses=courses,
                    course_groups=course_groups,
                    competencies=competencies,
                    active_documentation_subject_ids=(
                        active_documentation_subject_ids
                    ),
                    current_school_year_id=current_school_year_id,
                    current_school_year_label=current_school_year_label,
                    student_documentation_subject_configurations=MappingProxyType(
                        student_subject_configurations
                    ),
                    observations_by_student=MappingProxyType(
                        observations_by_student
                    ),
                    documents_by_student=MappingProxyType(
                        documents_by_student
                    ),
                    confirmations_by_student=MappingProxyType(
                        confirmations_by_student
                    ),
                    freshness_by_student=MappingProxyType(
                        {
                            student_id: MappingProxyType(freshness)
                            for student_id, freshness in (
                                freshness_by_student.items()
                            )
                        }
                    ),
                )
            finally:
                connection.rollback()

    @staticmethod
    def _student_scope_sql(
        student_ids: tuple[str, ...],
    ) -> tuple[str, tuple[str, ...]]:
        if not student_ids:
            return "0 = 1", ()
        placeholders = ", ".join("?" for _ in student_ids)
        return f"student.student_id IN ({placeholders})", student_ids

    @staticmethod
    def _require_current_membership_snapshot(snapshot: object) -> None:
        error_code = getattr(snapshot, "blocking_error_code", None)
        if error_code == "CURRENT_SCHOOL_YEAR_MISSING":
            raise SchoolYearAssignmentRepositoryError(
                "current_school_year_missing"
            )
        if error_code == "ASSIGNMENT_AMBIGUOUS":
            raise SchoolYearAssignmentRepositoryError(
                "assignment_ambiguous"
            )

    @staticmethod
    def _groups(connection: sqlite3.Connection) -> tuple[GroupRecord, ...]:
        rows = connection.execute(
            """
            SELECT group_id, group_name, active
            FROM groups
            WHERE active = 1
            ORDER BY group_id
            """
        ).fetchall()
        return tuple(
            GroupRecord(row[GROUP_ID], row[GROUP_NAME], bool(row[ACTIVE]))
            for row in rows
        )

    @staticmethod
    def _courses(connection: sqlite3.Connection) -> tuple[CourseRecord, ...]:
        rows = connection.execute(
            """
            SELECT
                course_id, course_name, color_key, color_hex, active,
                year_level
            FROM courses
            WHERE active = 1
            ORDER BY sort_order, course_id
            """
        ).fetchall()
        return tuple(
            CourseRecord(
                row[COURSE_ID],
                row[COURSE_NAME],
                (row[COLOR_HEX] or row[COLOR_KEY] or "").lstrip("#"),
                bool(row[ACTIVE]),
                int(row["year_level"]),
            )
            for row in rows
        )

    @staticmethod
    def _course_groups(
        connection: sqlite3.Connection,
    ) -> tuple[MasterDataCourseGroupRecord, ...]:
        rows = connection.execute(
            """
            SELECT course_group_id, name, active, sort_order
            FROM course_groups
            WHERE active = 1
            ORDER BY sort_order, course_group_id
            """
        ).fetchall()
        group_ids_by_course_group = (
            SQLiteStudentDocumentationProjectionRepository
            ._course_group_student_group_ids(connection)
        )
        course_ids_by_course_group = (
            SQLiteStudentDocumentationProjectionRepository
            ._course_group_course_ids(connection)
        )
        return tuple(
            MasterDataCourseGroupRecord(
                row["course_group_id"],
                row["name"],
                group_ids_by_course_group.get(row["course_group_id"], ()),
                course_ids_by_course_group.get(row["course_group_id"], ()),
                bool(row[ACTIVE]),
                int(row["sort_order"]),
            )
            for row in rows
        )

    @staticmethod
    def _course_group_student_group_ids(
        connection: sqlite3.Connection,
    ) -> dict[str, tuple[str, ...]]:
        rows = connection.execute(
            """
            SELECT relation.course_group_id, relation.student_group_id
            FROM course_group_student_groups AS relation
            JOIN course_groups AS course_group
                ON course_group.course_group_id = relation.course_group_id
            WHERE course_group.active = 1
            ORDER BY relation.course_group_id, relation.student_group_id
            """
        ).fetchall()
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["course_group_id"], []).append(
                row["student_group_id"]
            )
        return {
            course_group_id: tuple(group_ids)
            for course_group_id, group_ids in grouped.items()
        }

    @staticmethod
    def _course_group_course_ids(
        connection: sqlite3.Connection,
    ) -> dict[str, tuple[str, ...]]:
        rows = connection.execute(
            """
            SELECT relation.course_group_id, relation.course_id
            FROM course_group_courses AS relation
            JOIN course_groups AS course_group
                ON course_group.course_group_id = relation.course_group_id
            WHERE course_group.active = 1
            ORDER BY relation.course_group_id, relation.course_id
            """
        ).fetchall()
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["course_group_id"], []).append(row[COURSE_ID])
        return {
            course_group_id: tuple(course_ids)
            for course_group_id, course_ids in grouped.items()
        }

    @staticmethod
    def _competencies(
        connection: sqlite3.Connection,
    ) -> tuple[CompetencyRecord, ...]:
        rows = connection.execute(
            """
            SELECT
                competency_id,
                subject_id,
                subject_name,
                subject_full_name,
                official_subject_name,
                school_context_name,
                grade_band,
                label,
                description,
                learning_stage,
                learning_area,
                competency_group,
                source_reference,
                catalog_status,
                activation_group_key,
                sort_order,
                active,
                catalog_default_active,
                is_core_subject
            FROM competencies
            ORDER BY sort_order, competency_id
            """
        ).fetchall()
        return tuple(_competency_from_row(row) for row in rows)

    @staticmethod
    def _active_documentation_subject_ids(
        connection: sqlite3.Connection,
        competencies: tuple[CompetencyRecord, ...],
    ) -> tuple[str, ...]:
        rows = connection.execute(
            """
            SELECT subject_id, active
            FROM documentation_subject_settings
            ORDER BY subject_id
            """
        ).fetchall()
        active_catalog_subject_ids = tuple(
            dict.fromkeys(
                competency.subject_id
                for competency in competencies
                if competency.active
            )
        )
        if not rows:
            return active_catalog_subject_ids
        selected = {
            row["subject_id"]
            for row in rows
            if bool(row[ACTIVE])
        }
        catalog_order = {
            subject_id: index
            for index, subject_id in enumerate(active_catalog_subject_ids)
        }
        fallback_index = len(catalog_order)
        return tuple(
            sorted(
                selected,
                key=lambda subject_id: (
                    catalog_order.get(subject_id, fallback_index),
                    subject_id,
                ),
            )
        )

    @staticmethod
    def _ratings_by_observation(
        connection: sqlite3.Connection,
        scope_sql: str,
        scope_parameters: tuple[str, ...],
    ) -> dict[str, tuple[ObservationCompetencyRatingRecord, ...]]:
        rows = connection.execute(
            f"""
            SELECT
                rating.observation_id,
                rating.competency_id,
                rating.subject_id,
                rating.subject_display_name,
                rating.learning_area,
                rating.competency_group,
                rating.competency_text,
                rating.rating
            FROM observation_competency_ratings AS rating
            JOIN observations AS observation
                ON observation.observation_id = rating.observation_id
            JOIN students AS student
                ON student.student_id = observation.student_id
            WHERE observation.active = 1 AND {scope_sql}
            ORDER BY rating.observation_id, rating.competency_id
            """,
            scope_parameters,
        ).fetchall()
        grouped: dict[str, list[ObservationCompetencyRatingRecord]] = {}
        for row in rows:
            grouped.setdefault(row["observation_id"], []).append(
                ObservationCompetencyRatingRecord(
                    row["competency_id"],
                    row["subject_id"],
                    row["subject_display_name"],
                    row["learning_area"],
                    row["competency_group"] or "",
                    row["competency_text"],
                    row["rating"],
                )
            )
        return {
            observation_id: tuple(ratings)
            for observation_id, ratings in grouped.items()
        }

    @staticmethod
    def _observations_by_student(
        connection: sqlite3.Connection,
        scope_sql: str,
        scope_parameters: tuple[str, ...],
        ratings_by_observation: dict[
            str,
            tuple[ObservationCompetencyRatingRecord, ...],
        ],
    ) -> dict[str, tuple[ObservationRecord, ...]]:
        rows = connection.execute(
            f"""
            SELECT
                observation.observation_id,
                observation.student_id,
                observation.date,
                observation.subject_id,
                observation.context,
                observation.note,
                observation.active,
                observation.created_at,
                observation.updated_at
            FROM observations AS observation
            JOIN students AS student
                ON student.student_id = observation.student_id
            WHERE observation.active = 1 AND {scope_sql}
            ORDER BY
                observation.student_id,
                observation.date DESC,
                observation.observation_id DESC
            """,
            scope_parameters,
        ).fetchall()
        grouped: dict[str, list[ObservationRecord]] = {}
        for row in rows:
            grouped.setdefault(row[STUDENT_ID], []).append(
                ObservationRecord(
                    row["observation_id"],
                    row[STUDENT_ID],
                    row["date"],
                    row["subject_id"],
                    row["context"] or "",
                    row["note"] or "",
                    bool(row[ACTIVE]),
                    row[CREATED_AT],
                    row[UPDATED_AT],
                    ratings_by_observation.get(row["observation_id"], ()),
                )
            )
        return {
            student_id: tuple(observations)
            for student_id, observations in grouped.items()
        }

    @staticmethod
    def _documents_by_student(
        connection: sqlite3.Connection,
        scope_sql: str,
        scope_parameters: tuple[str, ...],
    ) -> dict[str, tuple[DocumentRecord, ...]]:
        rows = connection.execute(
            f"""
            SELECT
                document.document_id,
                document.student_id,
                document.observation_id,
                document.title,
                document.document_type,
                document.file_path,
                document.original_filename,
                document.created_at,
                document.note,
                document.active
            FROM documents AS document
            JOIN students AS student
                ON student.student_id = document.student_id
            WHERE document.active = 1 AND {scope_sql}
            ORDER BY
                document.student_id,
                document.created_at DESC,
                document.document_id DESC
            """,
            scope_parameters,
        ).fetchall()
        grouped: dict[str, list[DocumentRecord]] = {}
        for row in rows:
            grouped.setdefault(row[STUDENT_ID], []).append(
                _document_from_row(row)
            )
        return {
            student_id: tuple(documents)
            for student_id, documents in grouped.items()
        }

    @staticmethod
    def _confirmations_by_student(
        connection: sqlite3.Connection,
        scope_sql: str,
        scope_parameters: tuple[str, ...],
    ) -> dict[str, tuple[StudentCompetencyConfirmationRecord, ...]]:
        rows = connection.execute(
            f"""
            SELECT
                confirmation.student_id,
                confirmation.competency_id,
                confirmation.confirmed_rating,
                confirmation.confirmed_at,
                confirmation.note
            FROM student_competency_confirmations AS confirmation
            JOIN students AS student
                ON student.student_id = confirmation.student_id
            WHERE {scope_sql}
            ORDER BY confirmation.student_id, confirmation.competency_id
            """,
            scope_parameters,
        ).fetchall()
        grouped: dict[str, list[StudentCompetencyConfirmationRecord]] = {}
        for row in rows:
            grouped.setdefault(row[STUDENT_ID], []).append(
                StudentCompetencyConfirmationRecord(
                    row[STUDENT_ID],
                    row["competency_id"],
                    row["confirmed_rating"],
                    row["confirmed_at"],
                    row["note"] or "",
                )
            )
        return {
            student_id: tuple(confirmations)
            for student_id, confirmations in grouped.items()
        }

    @staticmethod
    def _freshness_by_student(
        connection: sqlite3.Connection,
        scope_sql: str,
        scope_parameters: tuple[str, ...],
    ) -> dict[str, dict[str, CompetencyFreshness]]:
        rows = connection.execute(
            f"""
            SELECT
                event.event_sequence,
                event.operation_token,
                event.operation_index,
                event.operation_payload_hash,
                event.event_kind,
                event.student_id,
                event.competency_id,
                event.observation_id,
                event.technical_timestamp,
                event.ordering_state
            FROM persistence_events AS event
            JOIN students AS student
                ON student.student_id = event.student_id
            WHERE {scope_sql}
            ORDER BY event.event_sequence
            """,
            scope_parameters,
        ).fetchall()
        grouped: dict[str, list[PersistenceEventRecord]] = {}
        for row in rows:
            event = PersistenceEventRecord(*row)
            grouped.setdefault(event.student_id, []).append(event)
        return {
            student_id: project_competency_freshness(tuple(events))
            for student_id, events in grouped.items()
        }


class SQLiteMasterDataRepository:
    """Read and write persistent master data in SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_student_groups(self) -> tuple[MasterDataGroupRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT group_id, group_name, active, sort_order
                FROM groups
                ORDER BY sort_order, group_id
                """
            ).fetchall()
        return tuple(
            MasterDataGroupRecord(
                row[GROUP_ID],
                row[GROUP_NAME],
                bool(row[ACTIVE]),
                int(row["sort_order"]),
            )
            for row in rows
        )

    def upsert_student_group(
        self,
        group: MasterDataGroupRecord,
        *,
        as_of: date | None = None,
    ) -> MasterDataGroupRecord:
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                persisted = connection.execute(
                    "SELECT active FROM groups WHERE group_id = ?",
                    (group.group_id,),
                ).fetchone()
                is_deactivation = not group.active and (
                    persisted is None or bool(persisted[ACTIVE])
                )
                if is_deactivation:
                    self._validate_deactivation_reference_date(as_of)
                    self._reject_referenced_group_deactivation(
                        connection,
                        group.group_id,
                        as_of,
                    )
                connection.execute(
                    """
                    INSERT INTO groups (group_id, group_name, sort_order, active)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(group_id) DO UPDATE SET
                        group_name = excluded.group_name,
                        sort_order = excluded.sort_order,
                        active = excluded.active
                    """,
                    (
                        group.group_id,
                        group.group_name,
                        group.sort_order,
                        int(group.active),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return group

    def list_courses(self) -> tuple[MasterDataCourseRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    course_id,
                    course_name,
                    color_name,
                    color_hex,
                    active,
                    sort_order,
                    year_level
                FROM courses
                ORDER BY sort_order, course_id
                """
            ).fetchall()
        return tuple(
            MasterDataCourseRecord(
                row[COURSE_ID],
                row[COURSE_NAME],
                row[COLOR_NAME],
                row[COLOR_HEX],
                bool(row[ACTIVE]),
                int(row["sort_order"]),
                int(row["year_level"]),
            )
            for row in rows
        )

    def upsert_course(
        self,
        course: MasterDataCourseRecord,
        *,
        as_of: date | None = None,
    ) -> MasterDataCourseRecord:
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                persisted = connection.execute(
                    "SELECT active FROM courses WHERE course_id = ?",
                    (course.course_id,),
                ).fetchone()
                is_deactivation = not course.active and (
                    persisted is None or bool(persisted[ACTIVE])
                )
                if is_deactivation:
                    self._validate_deactivation_reference_date(as_of)
                    self._reject_referenced_course_deactivation(
                        connection,
                        course.course_id,
                        as_of,
                    )
                connection.execute(
                    """
                    INSERT INTO courses (
                        course_id,
                        course_name,
                        color_key,
                        color_name,
                        color_hex,
                        sort_order,
                        active,
                        year_level
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(course_id) DO UPDATE SET
                        course_name = excluded.course_name,
                        color_key = excluded.color_key,
                        color_name = excluded.color_name,
                        color_hex = excluded.color_hex,
                        sort_order = excluded.sort_order,
                        active = excluded.active,
                        year_level = excluded.year_level
                    """,
                    (
                        course.course_id,
                        course.course_name,
                        course.color_hex,
                        course.color_name,
                        course.color_hex,
                        course.sort_order,
                        int(course.active),
                        course.year_level,
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return course

    @staticmethod
    def _validate_deactivation_reference_date(as_of: date | None) -> None:
        if type(as_of) is not date:
            raise ValueError(
                "Für die Deaktivierung ist ein ausdrücklicher Stichtag erforderlich."
            )

    @staticmethod
    def _reject_referenced_group_deactivation(
        connection: sqlite3.Connection,
        group_id: str,
        as_of: date,
    ) -> None:
        if connection.execute(
            """
            SELECT 1
            FROM student_school_year_assignments
            WHERE group_id = ?
              AND assignment_status = 'enrolled'
              AND valid_to >= ?
            LIMIT 1
            """,
            (group_id, as_of.isoformat()),
        ).fetchone() is not None:
            raise ValueError(
                "Die Stammgruppe wird in einer aktuellen oder zukünftigen "
                "Einschreibung verwendet und kann nicht deaktiviert werden."
            )

    @staticmethod
    def _reject_referenced_course_deactivation(
        connection: sqlite3.Connection,
        course_id: str,
        as_of: date,
    ) -> None:
        if connection.execute(
            """
            SELECT 1
            FROM student_school_year_assignments
            WHERE course_id = ?
              AND assignment_status = 'enrolled'
              AND valid_to >= ?
            LIMIT 1
            """,
            (course_id, as_of.isoformat()),
        ).fetchone() is not None:
            raise ValueError(
                "Der Kurs wird in einer aktuellen oder zukünftigen "
                "Einschreibung verwendet und kann nicht deaktiviert werden."
            )

    def list_course_groups(self) -> tuple[MasterDataCourseGroupRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT course_group_id, name, active, sort_order
                FROM course_groups
                ORDER BY sort_order, course_group_id
                """
            ).fetchall()
            return tuple(
                MasterDataCourseGroupRecord(
                    row["course_group_id"],
                    row["name"],
                    self._student_group_ids_for(connection, row["course_group_id"]),
                    self._course_ids_for(connection, row["course_group_id"]),
                    bool(row[ACTIVE]),
                    int(row["sort_order"]),
                )
                for row in rows
            )

    def update_course_group(
        self,
        course_group: MasterDataCourseGroupRecord,
    ) -> MasterDataCourseGroupRecord:
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO course_groups (
                        course_group_id,
                        name,
                        sort_order,
                        active
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(course_group_id) DO UPDATE SET
                        name = excluded.name,
                        sort_order = excluded.sort_order,
                        active = excluded.active
                    """,
                    (
                        course_group.course_group_id,
                        course_group.name,
                        course_group.sort_order,
                        int(course_group.active),
                    ),
                )
                self._replace_course_group_student_groups(
                    connection,
                    course_group.course_group_id,
                    course_group.selected_group_ids,
                )
                self._replace_course_group_courses(
                    connection,
                    course_group.course_group_id,
                    course_group.selected_course_ids,
                )
        return course_group

    def get_course_group_relations(
        self,
        course_group_id: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        with closing(self.database.connect()) as connection:
            return (
                self._student_group_ids_for(connection, course_group_id),
                self._course_ids_for(connection, course_group_id),
            )

    def replace_course_group_student_groups(
        self,
        course_group_id: str,
        group_ids: tuple[str, ...],
    ) -> None:
        with closing(self.database.connect()) as connection:
            with connection:
                self._replace_course_group_student_groups(
                    connection,
                    course_group_id,
                    group_ids,
                )

    def replace_course_group_courses(
        self,
        course_group_id: str,
        course_ids: tuple[str, ...],
    ) -> None:
        with closing(self.database.connect()) as connection:
            with connection:
                self._replace_course_group_courses(
                    connection,
                    course_group_id,
                    course_ids,
                )

    def next_student_group_id(self) -> str:
        return self._next_id("groups", "group_id", GROUP_ID_PREFIX)

    def next_course_id(self) -> str:
        return self._next_id("courses", "course_id", COURSE_ID_PREFIX)

    def next_course_group_id(self) -> str:
        return self._next_id(
            "course_groups",
            "course_group_id",
            COURSE_GROUP_ID_PREFIX,
        )

    def _student_group_ids_for(
        self,
        connection: sqlite3.Connection,
        course_group_id: str,
    ) -> tuple[str, ...]:
        rows = connection.execute(
            """
            SELECT student_group_id
            FROM course_group_student_groups
            WHERE course_group_id = ?
            ORDER BY student_group_id
            """,
            (course_group_id,),
        ).fetchall()
        return tuple(row["student_group_id"] for row in rows)

    def _course_ids_for(
        self,
        connection: sqlite3.Connection,
        course_group_id: str,
    ) -> tuple[str, ...]:
        rows = connection.execute(
            """
            SELECT course_id
            FROM course_group_courses
            WHERE course_group_id = ?
            ORDER BY course_id
            """,
            (course_group_id,),
        ).fetchall()
        return tuple(row[COURSE_ID] for row in rows)

    def _replace_course_group_student_groups(
        self,
        connection: sqlite3.Connection,
        course_group_id: str,
        group_ids: tuple[str, ...],
    ) -> None:
        connection.execute(
            "DELETE FROM course_group_student_groups WHERE course_group_id = ?",
            (course_group_id,),
        )
        connection.executemany(
            """
            INSERT INTO course_group_student_groups (
                course_group_id,
                student_group_id
            )
            VALUES (?, ?)
            """,
            ((course_group_id, group_id) for group_id in group_ids),
        )

    def _replace_course_group_courses(
        self,
        connection: sqlite3.Connection,
        course_group_id: str,
        course_ids: tuple[str, ...],
    ) -> None:
        connection.execute(
            "DELETE FROM course_group_courses WHERE course_group_id = ?",
            (course_group_id,),
        )
        connection.executemany(
            """
            INSERT INTO course_group_courses (course_group_id, course_id)
            VALUES (?, ?)
            """,
            ((course_group_id, course_id) for course_id in course_ids),
        )

    def _next_id(self, table_name: str, id_column: str, prefix: str) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                f"SELECT {id_column} FROM {table_name}"
            ).fetchall()
        next_number = 1
        for row in rows:
            value = str(row[id_column])
            if not value.startswith(f"{prefix}-"):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return f"{prefix}-{next_number:0{ID_SEQUENCE_WIDTH}d}"


class SQLiteLearningConferenceDraftRepository:
    """Persist the complete editable LEG-draft aggregate atomically."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def next_learning_conference_draft_id(self) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                "SELECT learning_conference_draft_id FROM learning_conference_drafts"
            ).fetchall()
        next_number = 1
        for row in rows:
            value = str(row["learning_conference_draft_id"])
            if not value.startswith(f"{LEARNING_CONFERENCE_DRAFT_ID_PREFIX}-"):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return (
            f"{LEARNING_CONFERENCE_DRAFT_ID_PREFIX}-"
            f"{next_number:0{ID_SEQUENCE_WIDTH}d}"
        )

    def create_learning_conference_draft(
        self,
        draft: LearningConferenceDraftRecord,
    ) -> LearningConferenceDraftRecord:
        if self.get_learning_conference_draft(
            draft.learning_conference_draft_id
        ) is not None:
            raise LearningConferenceDraftError(
                "learning_conference_draft_id existiert bereits: "
                f"{draft.learning_conference_draft_id}"
            )
        with closing(self.database.connect()) as connection:
            with connection:
                self._validate_references(connection, draft, set())
                connection.execute(
                    f"""
                    INSERT INTO learning_conference_drafts (
                        {', '.join(self._draft_columns())}
                    )
                    VALUES ({', '.join('?' for _ in self._draft_columns())})
                    """,
                    self._draft_row(draft),
                )
                self._replace_relations(connection, draft)
        return draft

    def update_learning_conference_draft(
        self,
        draft: LearningConferenceDraftRecord,
    ) -> LearningConferenceDraftRecord:
        existing = self.get_learning_conference_draft(
            draft.learning_conference_draft_id
        )
        if existing is None:
            raise LearningConferenceDraftError(
                "learning_conference_draft_id nicht gefunden: "
                f"{draft.learning_conference_draft_id}"
            )
        with closing(self.database.connect()) as connection:
            with connection:
                self._validate_references(
                    connection,
                    draft,
                    set(existing.observation_ids),
                )
                update_columns = self._draft_columns()[1:]
                connection.execute(
                    f"""
                    UPDATE learning_conference_drafts
                    SET {', '.join(f'{column} = ?' for column in update_columns)}
                    WHERE learning_conference_draft_id = ?
                    """,
                    (
                        *self._draft_row(draft)[1:],
                        draft.learning_conference_draft_id,
                    ),
                )
                self._replace_relations(connection, draft)
        return draft

    def get_learning_conference_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceDraftRecord | None:
        with closing(self.database.connect()) as connection:
            return self.get_learning_conference_draft_in_connection(
                connection,
                learning_conference_draft_id,
            )

    def get_learning_conference_draft_in_connection(
        self,
        connection: sqlite3.Connection,
        learning_conference_draft_id: str,
    ) -> LearningConferenceDraftRecord | None:
        row = connection.execute(
            f"""
            SELECT {', '.join(self._draft_columns())}
            FROM learning_conference_drafts
            WHERE learning_conference_draft_id = ?
            """,
            (learning_conference_draft_id,),
        ).fetchone()
        if row is None:
            return None
        return self._record_from_row(connection, row)

    def list_learning_conference_drafts_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningConferenceDraftRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT {', '.join(self._draft_columns())}
                FROM learning_conference_drafts
                WHERE student_id = ?
                ORDER BY updated_at DESC, learning_conference_draft_id DESC
                """,
                (student_id,),
            ).fetchall()
            return tuple(self._record_from_row(connection, row) for row in rows)

    def unavailable_observation_ids(
        self,
        draft: LearningConferenceDraftRecord,
    ) -> tuple[str, ...]:
        """Resolve unavailable stored evidence without dropping or replacing IDs."""
        if not draft.observation_ids:
            return ()
        placeholders = ", ".join("?" for _ in draft.observation_ids)
        with closing(self.database.connect()) as connection:
            active_ids = {
                row["observation_id"]
                for row in connection.execute(
                    f"""
                    SELECT observation_id
                    FROM observations
                    WHERE student_id = ?
                      AND active = 1
                      AND observation_id IN ({placeholders})
                    """,
                    (draft.student_id, *draft.observation_ids),
                ).fetchall()
            }
        return tuple(
            observation_id
            for observation_id in draft.observation_ids
            if observation_id not in active_ids
        )

    def _validate_references(
        self,
        connection: sqlite3.Connection,
        draft: LearningConferenceDraftRecord,
        existing_observation_ids: set[str],
    ) -> None:
        if connection.execute(
            "SELECT 1 FROM students WHERE student_id = ?",
            (draft.student_id,),
        ).fetchone() is None:
            raise LearningConferenceDraftError(
                f"student_id nicht gefunden: {draft.student_id}"
            )
        if draft.subject_ids:
            placeholders = ", ".join("?" for _ in draft.subject_ids)
            found_subjects = {
                row["subject_id"]
                for row in connection.execute(
                    f"SELECT DISTINCT subject_id FROM competencies WHERE subject_id IN ({placeholders})",
                    draft.subject_ids,
                ).fetchall()
            }
            missing_subjects = set(draft.subject_ids) - found_subjects
            if missing_subjects:
                raise LearningConferenceDraftError(
                    "Fachreferenzen nicht gefunden: "
                    f"{', '.join(sorted(missing_subjects))}"
                )
        if draft.competency_ids:
            placeholders = ", ".join("?" for _ in draft.competency_ids)
            competency_rows = connection.execute(
                f"SELECT competency_id, subject_id FROM competencies WHERE competency_id IN ({placeholders})",
                draft.competency_ids,
            ).fetchall()
            found_competencies = {
                row["competency_id"] for row in competency_rows
            }
            missing_competencies = set(draft.competency_ids) - found_competencies
            if missing_competencies:
                raise LearningConferenceDraftError(
                    "Kompetenzreferenzen nicht gefunden: "
                    f"{', '.join(sorted(missing_competencies))}"
                )
            unselected_subjects = {
                row["subject_id"]
                for row in competency_rows
                if row["subject_id"] not in set(draft.subject_ids)
            }
            if unselected_subjects:
                raise LearningConferenceDraftError(
                    "Kompetenzen duerfen nur aus ausgewaehlten Faechern stammen: "
                    f"{', '.join(sorted(unselected_subjects))}"
                )
        if draft.observation_ids:
            placeholders = ", ".join("?" for _ in draft.observation_ids)
            rows = connection.execute(
                f"""
                SELECT observation_id, student_id, active
                FROM observations
                WHERE observation_id IN ({placeholders})
                """,
                draft.observation_ids,
            ).fetchall()
            by_id = {row["observation_id"]: row for row in rows}
            invalid = {
                observation_id
                for observation_id in draft.observation_ids
                if observation_id not in by_id
                or by_id[observation_id]["student_id"] != draft.student_id
                or (
                    not bool(by_id[observation_id]["active"])
                    and observation_id not in existing_observation_ids
                )
            }
            if invalid:
                raise LearningConferenceDraftError(
                    "Beobachtungsreferenzen sind inaktiv, fehlen oder gehoeren "
                    "nicht zum Schueler: "
                    f"{', '.join(sorted(invalid))}"
                )

    def _replace_relations(
        self,
        connection: sqlite3.Connection,
        draft: LearningConferenceDraftRecord,
    ) -> None:
        relation_values = (
            ("learning_conference_draft_subjects", "subject_id", draft.subject_ids),
            (
                "learning_conference_draft_cross_topics",
                "cross_topic_key",
                draft.cross_topic_keys,
            ),
            (
                "learning_conference_draft_competencies",
                "competency_id",
                draft.competency_ids,
            ),
            (
                "learning_conference_draft_observations",
                "observation_id",
                draft.observation_ids,
            ),
            ("learning_conference_draft_charts", "chart_type", draft.chart_types),
        )
        for table, column, values in relation_values:
            connection.execute(
                f"DELETE FROM {table} WHERE learning_conference_draft_id = ?",
                (draft.learning_conference_draft_id,),
            )
            connection.executemany(
                f"INSERT INTO {table} (learning_conference_draft_id, {column}) VALUES (?, ?)",
                (
                    (draft.learning_conference_draft_id, value)
                    for value in values
                ),
            )

    def _record_from_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> LearningConferenceDraftRecord:
        draft_id = row["learning_conference_draft_id"]

        def relation_values(table: str, column: str) -> tuple[str, ...]:
            return tuple(
                item[column]
                for item in connection.execute(
                    f"""
                    SELECT {column}
                    FROM {table}
                    WHERE learning_conference_draft_id = ?
                    ORDER BY {column}
                    """,
                    (draft_id,),
                ).fetchall()
            )

        return LearningConferenceDraftRecord(
            *(row[column] for column in self._draft_columns()),
            subject_ids=relation_values(
                "learning_conference_draft_subjects", "subject_id"
            ),
            cross_topic_keys=relation_values(
                "learning_conference_draft_cross_topics", "cross_topic_key"
            ),
            competency_ids=relation_values(
                "learning_conference_draft_competencies", "competency_id"
            ),
            observation_ids=relation_values(
                "learning_conference_draft_observations", "observation_id"
            ),
            chart_types=relation_values(
                "learning_conference_draft_charts", "chart_type"
            ),
        )

    def _draft_row(
        self,
        draft: LearningConferenceDraftRecord,
    ) -> tuple[object, ...]:
        return tuple(getattr(draft, column) for column in self._draft_columns())

    @staticmethod
    def _draft_columns() -> tuple[str, ...]:
        return (
            "learning_conference_draft_id",
            "student_id",
            "period_start",
            "period_end",
            "conference_date",
            "status",
            "responsible_teacher",
            "conversation_entry_text",
            "child_retrospective_text",
            "teacher_perspective_text",
            "strengths_text",
            "development_fields_text",
            "prepared_goals_text",
            "prepared_support_text",
            "prepared_agreements_text",
            "agreed_goals_text",
            "agreed_support_text",
            "agreed_agreements_text",
            "responsibilities_text",
            "next_review_date",
            "created_at",
            "updated_at",
        )


class SQLiteLearningConferenceRepository:
    """Resolve LCD completion sources and persist immutable LCVs atomically."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self._completion_connection: sqlite3.Connection | None = None

    @contextmanager
    def completion_transaction(self):
        """Own LCD resolution, snapshot build and LCV write atomically."""

        if self._completion_connection is not None:
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.PERSISTENCE_FAILED,
                "Eine LEG-Abschlusstransaktion ist bereits aktiv.",
            )
        connection = self.database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._completion_connection = connection
            yield
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            self._completion_connection = None
            connection.close()

    @contextmanager
    def _source_connection(self):
        if self._completion_connection is not None:
            yield self._completion_connection
            return
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN")
            try:
                yield connection
            finally:
                if connection.in_transaction:
                    connection.rollback()

    def load_completion_source(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceCompletionSource | None:
        with self._source_connection() as connection:
            draft = SQLiteLearningConferenceDraftRepository(
                self.database
            ).get_learning_conference_draft_in_connection(
                connection,
                learning_conference_draft_id,
            )
            if draft is None:
                return None
            selected_subject_ids = set(draft.subject_ids)
            reference_date = _require_leg_conference_date(
                draft.conference_date
            )
            assignment = SchoolYearAssignmentReadSession(
                connection
            ).assignment_at_date(draft.student_id, reference_date)
            _require_leg_assignment(assignment)
            student_master = V3StudentRepository(connection).get_by_id(
                draft.student_id
            )
            student = (
                LearningConferenceStudentSource(
                    student_master.student_id,
                    student_master.first_name,
                    student_master.last_name,
                    assignment.group_id or "",
                    assignment.group_name or "",
                    assignment.course_id or "",
                    assignment.course_name or "",
                )
                if (
                    student_master is not None
                    and assignment.group_id is not None
                    and assignment.group_name is not None
                    and assignment.course_id is not None
                    and assignment.course_name is not None
                )
                else None
            )

            subjects: list[LearningConferenceSubjectSource] = []
            missing_subject_ids: list[str] = []
            for subject_id in draft.subject_ids:
                subject_name = self._subject_name(connection, subject_id)
                if not subject_name:
                    missing_subject_ids.append(subject_id)
                else:
                    subjects.append(
                        LearningConferenceSubjectSource(subject_id, subject_name)
                    )

            competencies: list[LearningConferenceCompetencySource] = []
            missing_competency_ids: list[str] = []
            invalid_competency_ids: list[str] = []
            for competency_id in draft.competency_ids:
                row = connection.execute(
                    """
                    SELECT
                        competency_id,
                        subject_id,
                        subject_name,
                        learning_area,
                        competency_group,
                        description,
                        catalog_status,
                        active
                    FROM competencies
                    WHERE competency_id = ?
                    """,
                    (competency_id,),
                ).fetchone()
                if row is None:
                    missing_competency_ids.append(competency_id)
                    continue
                historical = not bool(row["active"]) or row["catalog_status"] != "current"
                latest_snapshot = connection.execute(
                    """
                    SELECT
                        r.subject_id,
                        r.subject_display_name,
                        r.learning_area,
                        r.competency_group,
                        r.competency_text
                    FROM observation_competency_ratings r
                    JOIN observations o ON o.observation_id = r.observation_id
                    WHERE r.competency_id = ? AND o.student_id = ?
                    ORDER BY o.date DESC, o.observation_id DESC
                    LIMIT 1
                    """,
                    (competency_id, draft.student_id),
                ).fetchone()
                visible = latest_snapshot if historical and latest_snapshot is not None else row
                subject_id = visible["subject_id"]
                if subject_id not in selected_subject_ids:
                    invalid_competency_ids.append(competency_id)
                    continue
                competencies.append(
                    LearningConferenceCompetencySource(
                        competency_id=competency_id,
                        subject_id=subject_id,
                        subject_name=(
                            visible["subject_display_name"]
                            if "subject_display_name" in visible.keys()
                            else visible["subject_name"]
                        ),
                        learning_area=visible["learning_area"] or "",
                        competency_group=visible["competency_group"] or "",
                        competency_text=(
                            visible["competency_text"]
                            if "competency_text" in visible.keys()
                            else visible["description"]
                        ),
                        historical_reference=historical,
                        active_at_completion=bool(row["active"]),
                        catalog_status_at_completion=row["catalog_status"],
                    )
                )

            observations: list[LearningConferenceObservationSource] = []
            unavailable_observation_ids: list[str] = []
            invalid_observation_ids: list[str] = []
            for observation_id in draft.observation_ids:
                row = connection.execute(
                    """
                    SELECT observation_id, student_id, date, subject_id, context, note, active
                    FROM observations
                    WHERE observation_id = ?
                    """,
                    (observation_id,),
                ).fetchone()
                if row is None or not bool(row["active"]):
                    unavailable_observation_ids.append(observation_id)
                    continue
                if row["student_id"] != draft.student_id:
                    invalid_observation_ids.append(observation_id)
                    continue
                rating_rows = connection.execute(
                    """
                    SELECT
                        competency_id,
                        subject_id,
                        subject_display_name,
                        learning_area,
                        competency_group,
                        competency_text,
                        rating
                    FROM observation_competency_ratings
                    WHERE observation_id = ?
                    ORDER BY competency_id
                    """,
                    (observation_id,),
                ).fetchall()
                ratings = tuple(
                    LearningConferenceObservationRatingSource(
                        rating["competency_id"],
                        rating["subject_id"],
                        rating["subject_display_name"],
                        rating["learning_area"] or "",
                        rating["competency_group"] or "",
                        rating["competency_text"],
                        rating["rating"],
                    )
                    for rating in rating_rows
                )
                observations.append(
                    LearningConferenceObservationSource(
                        observation_id=observation_id,
                        observed_on=row["date"],
                        subject_id=row["subject_id"],
                        subject_name=(
                            self._subject_name(connection, row["subject_id"])
                            or next(
                                (
                                    rating.subject_name
                                    for rating in ratings
                                    if rating.subject_id == row["subject_id"]
                                ),
                                row["subject_id"],
                            )
                        ),
                        context=row["context"] or "",
                        note=row["note"] or "",
                        ratings=ratings,
                    )
                )

        return LearningConferenceCompletionSource(
            draft=draft,
            student=student,
            subjects=tuple(sorted(subjects, key=lambda item: item.subject_id)),
            competencies=tuple(
                sorted(competencies, key=lambda item: item.competency_id)
            ),
            observations=tuple(
                sorted(observations, key=lambda item: item.observation_id)
            ),
            missing_subject_ids=tuple(sorted(missing_subject_ids)),
            missing_competency_ids=tuple(sorted(missing_competency_ids)),
            invalid_competency_ids=tuple(sorted(invalid_competency_ids)),
            unavailable_observation_ids=tuple(
                sorted(unavailable_observation_ids)
            ),
            invalid_observation_ids=tuple(sorted(invalid_observation_ids)),
        )

    def save_completed_revision(
        self,
        source: LearningConferenceCompletionSource,
        *,
        snapshot_json: str,
        snapshot_sha256: str,
        completed_at: str,
        completed_by_display_name: str,
    ) -> LearningConferenceCompletionResult:
        owns_transaction = self._completion_connection is None
        connection = (
            self.database.connect()
            if owns_transaction
            else self._completion_connection
        )
        assert connection is not None
        try:
            if owns_transaction:
                connection.execute("BEGIN IMMEDIATE")
            current_draft = connection.execute(
                """
                SELECT updated_at
                FROM learning_conference_drafts
                WHERE learning_conference_draft_id = ?
                """,
                (source.draft.learning_conference_draft_id,),
            ).fetchone()
            if current_draft is None or current_draft["updated_at"] != source.draft.updated_at:
                raise LearningConferenceCompletionError(
                    LearningConferenceCompletionErrorCode.DRAFT_CHANGED,
                    "Der LEG-Entwurf wurde während des Abschlusses geändert.",
                )
            conference_row = connection.execute(
                """
                SELECT learning_conference_id, source_learning_conference_draft_id,
                       student_id, created_at
                FROM learning_conferences
                WHERE source_learning_conference_draft_id = ?
                """,
                (source.draft.learning_conference_draft_id,),
            ).fetchone()
            if conference_row is None:
                conference = LearningConferenceRecord(
                    self._next_id(
                        connection,
                        "learning_conferences",
                        "learning_conference_id",
                        LEARNING_CONFERENCE_ID_PREFIX,
                    ),
                    source.draft.learning_conference_draft_id,
                    source.draft.student_id,
                    completed_at,
                )
                connection.execute(
                    """
                    INSERT INTO learning_conferences (
                        learning_conference_id,
                        source_learning_conference_draft_id,
                        student_id,
                        created_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        conference.learning_conference_id,
                        conference.source_learning_conference_draft_id,
                        conference.student_id,
                        conference.created_at,
                    ),
                )
            else:
                conference = self._conference_from_row(conference_row)
                if (
                    conference.source_learning_conference_draft_id
                    != source.draft.learning_conference_draft_id
                    or conference.student_id != source.draft.student_id
                ):
                    raise LearningConferenceCompletionError(
                        LearningConferenceCompletionErrorCode.AGGREGATE_CONFLICT,
                        "Die Identität des bestehenden LCF stimmt nicht mit dem LCD überein.",
                    )

            current_row = connection.execute(
                """
                SELECT learning_conference_revision_id, learning_conference_id,
                       revision_number, status, snapshot_schema_version,
                       snapshot_json, snapshot_sha256, completed_at,
                       completed_by_display_name, superseded_at
                FROM learning_conference_revisions
                WHERE learning_conference_id = ? AND status = ?
                """,
                (conference.learning_conference_id, COMPLETED_REVISION_STATUS),
            ).fetchone()
            if (
                current_row is not None
                and current_row["snapshot_sha256"] == snapshot_sha256
                and current_row["snapshot_json"] == snapshot_json
            ):
                if owns_transaction:
                    connection.commit()
                return LearningConferenceCompletionResult(
                    conference,
                    self._revision_from_row(current_row),
                    False,
                )

            revision_number = int(
                connection.execute(
                    """
                    SELECT COALESCE(MAX(revision_number), 0) + 1
                    FROM learning_conference_revisions
                    WHERE learning_conference_id = ?
                    """,
                    (conference.learning_conference_id,),
                ).fetchone()[0]
            )
            if current_row is not None:
                connection.execute(
                    """
                    UPDATE learning_conference_revisions
                    SET status = ?, superseded_at = ?
                    WHERE learning_conference_revision_id = ?
                    """,
                    (
                        LEG_SUPERSEDED_REVISION_STATUS,
                        completed_at,
                        current_row["learning_conference_revision_id"],
                    ),
                )
            revision = LearningConferenceRevisionRecord(
                learning_conference_revision_id=self._next_id(
                    connection,
                    "learning_conference_revisions",
                    "learning_conference_revision_id",
                    LEARNING_CONFERENCE_REVISION_ID_PREFIX,
                ),
                learning_conference_id=conference.learning_conference_id,
                revision_number=revision_number,
                status=COMPLETED_REVISION_STATUS,
                snapshot_schema_version=LEARNING_CONFERENCE_SNAPSHOT_SCHEMA_VERSION,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                completed_at=completed_at,
                completed_by_display_name=completed_by_display_name.strip(),
                superseded_at=None,
            )
            self._insert_revision(connection, revision)
            if owns_transaction:
                connection.commit()
            return LearningConferenceCompletionResult(conference, revision, True)
        except sqlite3.Error as error:
            if owns_transaction and connection.in_transaction:
                connection.rollback()
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.PERSISTENCE_FAILED,
                f"LEG-Revision konnte nicht gespeichert werden: {error}",
            ) from error
        except Exception:
            if owns_transaction and connection.in_transaction:
                connection.rollback()
            raise
        finally:
            if owns_transaction:
                connection.close()

    def get_conference_for_source_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceRecord | None:
        with self._source_connection() as connection:
            row = connection.execute(
                """
                SELECT learning_conference_id, source_learning_conference_draft_id,
                       student_id, created_at
                FROM learning_conferences
                WHERE source_learning_conference_draft_id = ?
                """,
                (learning_conference_draft_id,),
            ).fetchone()
        return self._conference_from_row(row) if row is not None else None

    def list_revisions(
        self,
        learning_conference_id: str,
    ) -> tuple[LearningConferenceRevisionRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT learning_conference_revision_id, learning_conference_id,
                       revision_number, status, snapshot_schema_version,
                       snapshot_json, snapshot_sha256, completed_at,
                       completed_by_display_name, superseded_at
                FROM learning_conference_revisions
                WHERE learning_conference_id = ?
                ORDER BY revision_number
                """,
                (learning_conference_id,),
            ).fetchall()
        return tuple(self._revision_from_row(row) for row in rows)

    def get_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferenceRevisionRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT learning_conference_revision_id, learning_conference_id,
                       revision_number, status, snapshot_schema_version,
                       snapshot_json, snapshot_sha256, completed_at,
                       completed_by_display_name, superseded_at
                FROM learning_conference_revisions
                WHERE learning_conference_revision_id = ?
                """,
                (learning_conference_revision_id,),
            ).fetchone()
        return self._revision_from_row(row) if row is not None else None

    def list_revision_histories_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningConferenceRevisionHistory, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    conference.learning_conference_id,
                    conference.source_learning_conference_draft_id,
                    conference.student_id,
                    conference.created_at,
                    revision.learning_conference_revision_id,
                    revision.revision_number,
                    revision.status,
                    revision.snapshot_schema_version,
                    revision.snapshot_json,
                    revision.snapshot_sha256,
                    revision.completed_at,
                    revision.completed_by_display_name,
                    revision.superseded_at
                FROM learning_conferences AS conference
                JOIN learning_conference_revisions AS revision
                  ON revision.learning_conference_id =
                     conference.learning_conference_id
                WHERE conference.student_id = ?
                ORDER BY
                    conference.source_learning_conference_draft_id,
                    revision.revision_number DESC,
                    revision.learning_conference_revision_id
                """,
                (student_id,),
            ).fetchall()
        histories: dict[
            str,
            tuple[LearningConferenceRecord, list[LearningConferenceRevisionRecord]],
        ] = {}
        for row in rows:
            conference = self._conference_from_row(row)
            _existing, revisions = histories.setdefault(
                conference.learning_conference_id,
                (conference, []),
            )
            revisions.append(self._revision_from_row(row))
        return tuple(
            LearningConferenceRevisionHistory(conference, tuple(revisions))
            for conference, revisions in histories.values()
        )

    def _subject_name(
        self,
        connection: sqlite3.Connection,
        subject_id: str,
    ) -> str:
        row = connection.execute(
            """
            SELECT subject_name
            FROM competencies
            WHERE subject_id = ?
            ORDER BY CASE WHEN active = 1 AND catalog_status = 'current' THEN 0 ELSE 1 END,
                     sort_order, competency_id
            LIMIT 1
            """,
            (subject_id,),
        ).fetchone()
        return str(row["subject_name"]).strip() if row is not None else ""

    def _next_id(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        prefix: str,
    ) -> str:
        rows = connection.execute(f"SELECT {column_name} FROM {table_name}").fetchall()
        next_number = 1
        for row in rows:
            value = str(row[column_name])
            if not value.startswith(f"{prefix}-"):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return f"{prefix}-{next_number:0{ID_SEQUENCE_WIDTH}d}"

    def _insert_revision(
        self,
        connection: sqlite3.Connection,
        revision: LearningConferenceRevisionRecord,
    ) -> None:
        connection.execute(
            """
            INSERT INTO learning_conference_revisions (
                learning_conference_revision_id, learning_conference_id,
                revision_number, status, snapshot_schema_version, snapshot_json,
                snapshot_sha256, completed_at, completed_by_display_name,
                superseded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.learning_conference_revision_id,
                revision.learning_conference_id,
                revision.revision_number,
                revision.status,
                revision.snapshot_schema_version,
                revision.snapshot_json,
                revision.snapshot_sha256,
                revision.completed_at,
                revision.completed_by_display_name,
                revision.superseded_at,
            ),
        )

    @staticmethod
    def _conference_from_row(row: sqlite3.Row) -> LearningConferenceRecord:
        return LearningConferenceRecord(
            row["learning_conference_id"],
            row["source_learning_conference_draft_id"],
            row["student_id"],
            row["created_at"],
        )

    @staticmethod
    def _revision_from_row(row: sqlite3.Row) -> LearningConferenceRevisionRecord:
        return LearningConferenceRevisionRecord(
            row["learning_conference_revision_id"],
            row["learning_conference_id"],
            int(row["revision_number"]),
            row["status"],
            int(row["snapshot_schema_version"]),
            row["snapshot_json"],
            row["snapshot_sha256"],
            row["completed_at"],
            row["completed_by_display_name"],
            row["superseded_at"],
        )


class SQLiteReportDraftRepository:
    """Persist the complete editable report-draft aggregate atomically."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def next_report_draft_id(self) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                "SELECT report_draft_id FROM report_drafts"
            ).fetchall()
        next_number = 1
        for row in rows:
            value = str(row["report_draft_id"])
            if not value.startswith(f"{REPORT_DRAFT_ID_PREFIX}-"):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return f"{REPORT_DRAFT_ID_PREFIX}-{next_number:0{ID_SEQUENCE_WIDTH}d}"

    def create_report_draft(self, draft: ReportDraftRecord) -> ReportDraftRecord:
        if self.get_report_draft(draft.report_draft_id) is not None:
            raise ReportDraftError(
                f"report_draft_id existiert bereits: {draft.report_draft_id}"
            )
        with closing(self.database.connect()) as connection:
            with connection:
                self._validate_references(connection, draft, set(), set())
                connection.execute(
                    """
                    INSERT INTO report_drafts (
                        report_draft_id,
                        student_id,
                        report_type,
                        period_start,
                        period_end,
                        status,
                        teacher_name,
                        overall_text,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._draft_row(draft),
                )
                self._replace_relations(connection, draft)
        return draft

    def update_report_draft(self, draft: ReportDraftRecord) -> ReportDraftRecord:
        existing = self.get_report_draft(draft.report_draft_id)
        if existing is None:
            raise ReportDraftError(
                f"report_draft_id nicht gefunden: {draft.report_draft_id}"
            )
        with closing(self.database.connect()) as connection:
            with connection:
                self._validate_references(
                    connection,
                    draft,
                    set(existing.competency_ids),
                    set(existing.observation_ids),
                )
                connection.execute(
                    """
                    UPDATE report_drafts
                    SET
                        student_id = ?,
                        report_type = ?,
                        period_start = ?,
                        period_end = ?,
                        status = ?,
                        teacher_name = ?,
                        overall_text = ?,
                        updated_at = ?
                    WHERE report_draft_id = ?
                    """,
                    (
                        draft.student_id,
                        draft.report_type,
                        draft.period_start,
                        draft.period_end,
                        draft.status,
                        draft.teacher_name,
                        draft.overall_text,
                        draft.updated_at,
                        draft.report_draft_id,
                    ),
                )
                self._replace_relations(connection, draft)
        return draft

    def get_report_draft(self, report_draft_id: str) -> ReportDraftRecord | None:
        with closing(self.database.connect()) as connection:
            return self.get_report_draft_in_connection(
                connection,
                report_draft_id,
            )

    def get_report_draft_in_connection(
        self,
        connection: sqlite3.Connection,
        report_draft_id: str,
    ) -> ReportDraftRecord | None:
        row = connection.execute(
            """
            SELECT
                report_draft_id,
                student_id,
                report_type,
                period_start,
                period_end,
                status,
                teacher_name,
                overall_text,
                created_at,
                updated_at
            FROM report_drafts
            WHERE report_draft_id = ?
            """,
            (report_draft_id,),
        ).fetchone()
        if row is None:
            return None
        return self._record_from_row(connection, row)

    def list_report_drafts_for_student(
        self,
        student_id: str,
    ) -> tuple[ReportDraftRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    report_draft_id,
                    student_id,
                    report_type,
                    period_start,
                    period_end,
                    status,
                    teacher_name,
                    overall_text,
                    created_at,
                    updated_at
                FROM report_drafts
                WHERE student_id = ?
                ORDER BY updated_at DESC, report_draft_id DESC
                """,
                (student_id,),
            ).fetchall()
            return tuple(self._record_from_row(connection, row) for row in rows)

    def unavailable_observation_ids(
        self,
        draft: ReportDraftRecord,
    ) -> tuple[str, ...]:
        """Resolve unavailable stored evidence without dropping or replacing IDs."""
        if not draft.observation_ids:
            return ()
        placeholders = ", ".join("?" for _ in draft.observation_ids)
        with closing(self.database.connect()) as connection:
            active_ids = {
                row["observation_id"]
                for row in connection.execute(
                    f"""
                    SELECT observation_id
                    FROM observations
                    WHERE student_id = ?
                      AND active = 1
                      AND observation_id IN ({placeholders})
                    """,
                    (draft.student_id, *draft.observation_ids),
                ).fetchall()
            }
        return tuple(
            observation_id
            for observation_id in draft.observation_ids
            if observation_id not in active_ids
        )

    def _validate_references(
        self,
        connection: sqlite3.Connection,
        draft: ReportDraftRecord,
        existing_competency_ids: set[str],
        existing_observation_ids: set[str],
    ) -> None:
        student = connection.execute(
            "SELECT student_id FROM students WHERE student_id = ?",
            (draft.student_id,),
        ).fetchone()
        if student is None:
            raise ReportDraftError(f"student_id nicht gefunden: {draft.student_id}")
        subject_ids = {subject.subject_id for subject in draft.subjects}
        if subject_ids:
            placeholders = ", ".join("?" for _ in subject_ids)
            found_subjects = {
                row["subject_id"]
                for row in connection.execute(
                    f"SELECT DISTINCT subject_id FROM competencies WHERE subject_id IN ({placeholders})",
                    tuple(subject_ids),
                ).fetchall()
            }
            missing_subjects = subject_ids - found_subjects
            if missing_subjects:
                raise ReportDraftError(
                    "Fachreferenzen nicht gefunden: "
                    f"{', '.join(sorted(missing_subjects))}"
                )
        if draft.competency_ids:
            placeholders = ", ".join("?" for _ in draft.competency_ids)
            rows = connection.execute(
                f"""
                SELECT competency_id, subject_id, active, catalog_status
                FROM competencies
                WHERE competency_id IN ({placeholders})
                """,
                draft.competency_ids,
            ).fetchall()
            by_id = {row["competency_id"]: row for row in rows}
            missing = set(draft.competency_ids) - set(by_id)
            if missing:
                raise ReportDraftError(
                    f"Kompetenzreferenzen nicht gefunden: {', '.join(sorted(missing))}"
                )
            unselected_subjects = {
                row["subject_id"]
                for row in rows
                if row["subject_id"] not in subject_ids
            }
            if unselected_subjects:
                raise ReportDraftError(
                    "Kompetenzen duerfen nur aus ausgewaehlten Faechern stammen: "
                    f"{', '.join(sorted(unselected_subjects))}"
                )
            unavailable_new = {
                competency_id
                for competency_id, row in by_id.items()
                if (
                    not bool(row["active"])
                    or row["catalog_status"] != "current"
                )
                and competency_id not in existing_competency_ids
            }
            if unavailable_new:
                raise ReportDraftError(
                    "Nicht regulär verfügbare Kompetenzen dürfen nicht neu ausgewählt werden: "
                    f"{', '.join(sorted(unavailable_new))}"
                )
        if draft.observation_ids:
            placeholders = ", ".join("?" for _ in draft.observation_ids)
            rows = connection.execute(
                f"""
                SELECT observation_id, student_id, subject_id, active
                FROM observations
                WHERE observation_id IN ({placeholders})
                """,
                draft.observation_ids,
            ).fetchall()
            by_id = {row["observation_id"]: row for row in rows}
            invalid = {
                observation_id
                for observation_id in draft.observation_ids
                if observation_id not in by_id
                or by_id[observation_id]["student_id"] != draft.student_id
                or (
                    not bool(by_id[observation_id]["active"])
                    and observation_id not in existing_observation_ids
                )
            }
            if invalid:
                raise ReportDraftError(
                    "Beobachtungsreferenzen sind inaktiv, fehlen oder gehoeren "
                    "nicht zum Schueler: "
                    f"{', '.join(sorted(invalid))}"
                )
            rating_subjects_by_observation: dict[str, set[str]] = {}
            for row in connection.execute(
                f"""
                SELECT observation_id, subject_id
                FROM observation_competency_ratings
                WHERE observation_id IN ({placeholders})
                """,
                draft.observation_ids,
            ).fetchall():
                rating_subjects_by_observation.setdefault(
                    row["observation_id"], set()
                ).add(row["subject_id"])
            wrong_subject = {
                observation_id
                for observation_id, row in by_id.items()
                if observation_id not in invalid
                and not (
                    {row["subject_id"]}
                    | rating_subjects_by_observation.get(observation_id, set())
                ).intersection(subject_ids)
            }
            if wrong_subject:
                raise ReportDraftError(
                    "Beobachtungen duerfen nur zu ausgewaehlten Faechern gehoeren: "
                    f"{', '.join(sorted(wrong_subject))}"
                )

    def _replace_relations(
        self,
        connection: sqlite3.Connection,
        draft: ReportDraftRecord,
    ) -> None:
        for table in (
            "report_draft_subjects",
            "report_draft_competencies",
            "report_draft_observations",
            "report_draft_charts",
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE report_draft_id = ?",
                (draft.report_draft_id,),
            )
        connection.executemany(
            """
            INSERT INTO report_draft_subjects (
                report_draft_id,
                subject_id,
                strengths_text,
                development_text,
                support_needs_text,
                next_goals_text
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    draft.report_draft_id,
                    subject.subject_id,
                    subject.strengths_text,
                    subject.development_text,
                    subject.support_needs_text,
                    subject.next_goals_text,
                )
                for subject in draft.subjects
            ),
        )
        connection.executemany(
            """
            INSERT INTO report_draft_competencies (report_draft_id, competency_id)
            VALUES (?, ?)
            """,
            (
                (draft.report_draft_id, competency_id)
                for competency_id in draft.competency_ids
            ),
        )
        connection.executemany(
            """
            INSERT INTO report_draft_observations (report_draft_id, observation_id)
            VALUES (?, ?)
            """,
            (
                (draft.report_draft_id, observation_id)
                for observation_id in draft.observation_ids
            ),
        )
        connection.executemany(
            """
            INSERT INTO report_draft_charts (report_draft_id, subject_id, chart_type)
            VALUES (?, ?, ?)
            """,
            (
                (draft.report_draft_id, chart.subject_id, chart.chart_type)
                for chart in draft.chart_selections
            ),
        )

    def _record_from_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> ReportDraftRecord:
        report_draft_id = row["report_draft_id"]
        subjects = tuple(
            ReportDraftSubjectRecord(
                subject["subject_id"],
                subject["strengths_text"],
                subject["development_text"],
                subject["support_needs_text"],
                subject["next_goals_text"],
            )
            for subject in connection.execute(
                """
                SELECT
                    subject_id,
                    strengths_text,
                    development_text,
                    support_needs_text,
                    next_goals_text
                FROM report_draft_subjects
                WHERE report_draft_id = ?
                ORDER BY subject_id
                """,
                (report_draft_id,),
            ).fetchall()
        )
        competency_ids = tuple(
            item["competency_id"]
            for item in connection.execute(
                """
                SELECT competency_id
                FROM report_draft_competencies
                WHERE report_draft_id = ?
                ORDER BY competency_id
                """,
                (report_draft_id,),
            ).fetchall()
        )
        observation_ids = tuple(
            item["observation_id"]
            for item in connection.execute(
                """
                SELECT observation_id
                FROM report_draft_observations
                WHERE report_draft_id = ?
                ORDER BY observation_id
                """,
                (report_draft_id,),
            ).fetchall()
        )
        charts = tuple(
            ReportDraftChartSelectionRecord(item["subject_id"], item["chart_type"])
            for item in connection.execute(
                """
                SELECT subject_id, chart_type
                FROM report_draft_charts
                WHERE report_draft_id = ?
                ORDER BY subject_id, chart_type
                """,
                (report_draft_id,),
            ).fetchall()
        )
        return ReportDraftRecord(
            report_draft_id,
            row["student_id"],
            row["report_type"],
            row["period_start"],
            row["period_end"],
            row["status"],
            row["teacher_name"],
            row["overall_text"],
            row["created_at"],
            row["updated_at"],
            subjects,
            competency_ids,
            observation_ids,
            charts,
        )

    def _draft_row(self, draft: ReportDraftRecord) -> tuple[object, ...]:
        return (
            draft.report_draft_id,
            draft.student_id,
            draft.report_type,
            draft.period_start,
            draft.period_end,
            draft.status,
            draft.teacher_name,
            draft.overall_text,
            draft.created_at,
            draft.updated_at,
        )


class SQLiteLearningReportRepository:
    """Resolve finalization sources and persist immutable revisions atomically."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self._finalization_connection: sqlite3.Connection | None = None

    @contextmanager
    def finalization_transaction(self):
        """Own source resolution, snapshot build and revision write atomically."""

        if self._finalization_connection is not None:
            raise ReportFinalizationError(
                "Eine Berichtfinalisierungstransaktion ist bereits aktiv."
            )
        connection = self.database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._finalization_connection = connection
            yield
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            self._finalization_connection = None
            connection.close()

    @contextmanager
    def _source_connection(self):
        if self._finalization_connection is not None:
            yield self._finalization_connection
            return
        with closing(self.database.connect()) as connection:
            connection.execute("BEGIN")
            try:
                yield connection
            finally:
                if connection.in_transaction:
                    connection.rollback()

    def load_finalization_source(
        self,
        report_draft_id: str,
    ) -> LearningReportFinalizationSource | None:
        with self._source_connection() as connection:
            draft = SQLiteReportDraftRepository(
                self.database
            ).get_report_draft_in_connection(connection, report_draft_id)
            if draft is None:
                return None
            selected_subject_ids = {
                subject.subject_id for subject in draft.subjects
            }
            reference_date = _require_report_period_end(draft.period_end)
            assignment = SchoolYearAssignmentReadSession(
                connection
            ).assignment_at_date(draft.student_id, reference_date)
            _require_report_assignment(assignment)
            student_master = V3StudentRepository(connection).get_by_id(
                draft.student_id
            )
            student = (
                LearningReportStudentSource(
                    student_master.student_id,
                    student_master.first_name,
                    student_master.last_name,
                    assignment.group_id or "",
                    assignment.group_name or "",
                    assignment.course_id or "",
                    assignment.course_name or "",
                )
                if (
                    student_master is not None
                    and assignment.group_id is not None
                    and assignment.group_name is not None
                    and assignment.course_id is not None
                    and assignment.course_name is not None
                )
                else None
            )

            subjects: list[LearningReportSubjectSource] = []
            missing_subject_ids: list[str] = []
            for subject in draft.subjects:
                subject_name = self._subject_name(connection, subject.subject_id)
                if not subject_name:
                    missing_subject_ids.append(subject.subject_id)
                    continue
                coverage = connection.execute(
                    """
                    SELECT
                        COUNT(*) AS current_count,
                        COALESCE(SUM(
                            CASE WHEN
                                EXISTS (
                                    SELECT 1
                                    FROM observation_competency_ratings r
                                    JOIN observations o
                                      ON o.observation_id = r.observation_id
                                    WHERE r.competency_id = competencies.competency_id
                                      AND o.student_id = ?
                                      AND o.active = 1
                                )
                                OR EXISTS (
                                    SELECT 1
                                    FROM student_competency_confirmations confirmation
                                    WHERE confirmation.student_id = ?
                                      AND confirmation.competency_id = competencies.competency_id
                                )
                            THEN 1 ELSE 0 END
                        ), 0) AS documented_count
                    FROM competencies
                    WHERE subject_id = ?
                      AND active = 1
                      AND catalog_status = 'current'
                    """,
                    (draft.student_id, draft.student_id, subject.subject_id),
                ).fetchone()
                subjects.append(
                    LearningReportSubjectSource(
                        subject.subject_id,
                        subject_name,
                        int(coverage["documented_count"]),
                        int(coverage["current_count"]),
                    )
                )

            competencies: list[LearningReportCompetencySource] = []
            missing_competency_ids: list[str] = []
            invalid_competency_ids: list[str] = []
            for competency_id in draft.competency_ids:
                row = connection.execute(
                    """
                    SELECT
                        competency_id,
                        subject_id,
                        subject_name,
                        learning_area,
                        competency_group,
                        description,
                        catalog_status,
                        active
                    FROM competencies
                    WHERE competency_id = ?
                    """,
                    (competency_id,),
                ).fetchone()
                if row is None:
                    missing_competency_ids.append(competency_id)
                    continue
                if row["subject_id"] not in selected_subject_ids:
                    invalid_competency_ids.append(competency_id)
                    continue
                historical = not bool(row["active"]) or row["catalog_status"] != "current"
                latest_snapshot = connection.execute(
                    """
                    SELECT
                        r.subject_id,
                        r.subject_display_name,
                        r.learning_area,
                        r.competency_group,
                        r.competency_text
                    FROM observation_competency_ratings r
                    JOIN observations o ON o.observation_id = r.observation_id
                    WHERE r.competency_id = ?
                      AND o.student_id = ?
                      AND o.active = 1
                    ORDER BY o.date DESC, o.observation_id DESC
                    LIMIT 1
                    """,
                    (competency_id, draft.student_id),
                ).fetchone()
                visible = latest_snapshot if historical and latest_snapshot is not None else row
                visible_subject_id = visible["subject_id"]
                if visible_subject_id not in selected_subject_ids:
                    invalid_competency_ids.append(competency_id)
                    continue
                evidence = self._competency_evidence(
                    connection,
                    draft.student_id,
                    competency_id,
                )
                competencies.append(
                    LearningReportCompetencySource(
                        competency_id=competency_id,
                        subject_id=visible_subject_id,
                        subject_name=(
                            visible["subject_display_name"]
                            if "subject_display_name" in visible.keys()
                            else visible["subject_name"]
                        ),
                        learning_area=visible["learning_area"] or "",
                        competency_group=visible["competency_group"] or "",
                        competency_text=(
                            visible["competency_text"]
                            if "competency_text" in visible.keys()
                            else visible["description"]
                        ),
                        historical_reference=historical,
                        active_at_finalization=bool(row["active"]),
                        catalog_status_at_finalization=row["catalog_status"],
                        evidence_points=evidence,
                    )
                )

            observations: list[LearningReportObservationSource] = []
            unavailable_observation_ids: list[str] = []
            invalid_observation_ids: list[str] = []
            for observation_id in draft.observation_ids:
                row = connection.execute(
                    """
                    SELECT observation_id, student_id, date, subject_id, context, note, active
                    FROM observations
                    WHERE observation_id = ?
                    """,
                    (observation_id,),
                ).fetchone()
                if row is None or not bool(row["active"]):
                    unavailable_observation_ids.append(observation_id)
                    continue
                rating_subject_ids = {
                    rating["subject_id"]
                    for rating in connection.execute(
                        """
                        SELECT DISTINCT subject_id
                        FROM observation_competency_ratings
                        WHERE observation_id = ?
                        """,
                        (observation_id,),
                    ).fetchall()
                }
                matched_subject_ids = tuple(
                    sorted(
                        ({row["subject_id"]} | rating_subject_ids)
                        & selected_subject_ids
                    )
                )
                if row["student_id"] != draft.student_id or not matched_subject_ids:
                    invalid_observation_ids.append(observation_id)
                    continue
                observations.append(
                    LearningReportObservationSource(
                        observation_id=observation_id,
                        observed_on=row["date"],
                        subject_id=row["subject_id"],
                        subject_name=(
                            self._subject_name(connection, row["subject_id"])
                            or row["subject_id"]
                        ),
                        context=row["context"] or "",
                        note=row["note"] or "",
                        matched_subject_ids=matched_subject_ids,
                    )
                )

        return LearningReportFinalizationSource(
            draft=draft,
            student=student,
            subjects=tuple(subjects),
            competencies=tuple(sorted(competencies, key=lambda item: item.competency_id)),
            observations=tuple(sorted(observations, key=lambda item: item.observation_id)),
            missing_subject_ids=tuple(sorted(missing_subject_ids)),
            missing_competency_ids=tuple(sorted(missing_competency_ids)),
            invalid_competency_ids=tuple(sorted(invalid_competency_ids)),
            unavailable_observation_ids=tuple(sorted(unavailable_observation_ids)),
            invalid_observation_ids=tuple(sorted(invalid_observation_ids)),
        )

    def save_finalized_revision(
        self,
        source: LearningReportFinalizationSource,
        *,
        snapshot_json: str,
        snapshot_sha256: str,
        finalized_at: str,
        finalized_by_display_name: str,
    ) -> LearningReportFinalizationResult:
        owns_transaction = self._finalization_connection is None
        connection = (
            self.database.connect()
            if owns_transaction
            else self._finalization_connection
        )
        assert connection is not None
        try:
            if owns_transaction:
                connection.execute("BEGIN IMMEDIATE")
            current_draft = connection.execute(
                """
                SELECT updated_at
                FROM report_drafts
                WHERE report_draft_id = ?
                """,
                (source.draft.report_draft_id,),
            ).fetchone()
            if (
                current_draft is None
                or current_draft["updated_at"] != source.draft.updated_at
            ):
                raise ReportFinalizationError(
                    "Der Berichtsdraft wurde waehrend der Finalisierung geaendert."
                )
            report_row = connection.execute(
                """
                SELECT
                    learning_report_id,
                    source_report_draft_id,
                    student_id,
                    report_type,
                    period_start,
                    period_end,
                    created_at
                FROM learning_reports
                WHERE source_report_draft_id = ?
                """,
                (source.draft.report_draft_id,),
            ).fetchone()
            if report_row is None:
                learning_report_id = self._next_id(
                    connection,
                    "learning_reports",
                    "learning_report_id",
                    LEARNING_REPORT_ID_PREFIX,
                )
                connection.execute(
                    """
                    INSERT INTO learning_reports (
                        learning_report_id,
                        source_report_draft_id,
                        student_id,
                        report_type,
                        period_start,
                        period_end,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        learning_report_id,
                        source.draft.report_draft_id,
                        source.draft.student_id,
                        source.draft.report_type,
                        source.draft.period_start,
                        source.draft.period_end,
                        finalized_at,
                    ),
                )
                report = LearningReportRecord(
                    learning_report_id,
                    source.draft.report_draft_id,
                    source.draft.student_id,
                    source.draft.report_type,
                    source.draft.period_start,
                    source.draft.period_end,
                    finalized_at,
                )
            else:
                report = self._report_from_row(report_row)
                if (
                    report.source_report_draft_id != source.draft.report_draft_id
                    or report.student_id != source.draft.student_id
                    or report.report_type != source.draft.report_type
                    or report.period_start != source.draft.period_start
                    or report.period_end != source.draft.period_end
                ):
                    raise ReportFinalizationError(
                        "Die Aggregateidentitaet des bestehenden RPT weicht vom RPD "
                        "ab. Fuer einen anderen Berichtstyp oder Zeitraum ist ein "
                        "neuer Berichtsdraft erforderlich."
                    )

            current_revision = connection.execute(
                """
                SELECT learning_report_revision_id
                FROM learning_report_revisions
                WHERE learning_report_id = ? AND status = ?
                """,
                (report.learning_report_id, FINALIZED_REVISION_STATUS),
            ).fetchone()
            revision_number = int(
                connection.execute(
                    """
                    SELECT COALESCE(MAX(revision_number), 0) + 1
                    FROM learning_report_revisions
                    WHERE learning_report_id = ?
                    """,
                    (report.learning_report_id,),
                ).fetchone()[0]
            )
            if current_revision is not None:
                connection.execute(
                    """
                    UPDATE learning_report_revisions
                    SET status = ?, superseded_at = ?
                    WHERE learning_report_revision_id = ?
                    """,
                    (
                        SUPERSEDED_REVISION_STATUS,
                        finalized_at,
                        current_revision["learning_report_revision_id"],
                    ),
                )
            revision = LearningReportRevisionRecord(
                learning_report_revision_id=self._next_id(
                    connection,
                    "learning_report_revisions",
                    "learning_report_revision_id",
                    LEARNING_REPORT_REVISION_ID_PREFIX,
                ),
                learning_report_id=report.learning_report_id,
                revision_number=revision_number,
                status=FINALIZED_REVISION_STATUS,
                snapshot_schema_version=LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                finalized_at=finalized_at,
                finalized_by_display_name=finalized_by_display_name,
                superseded_at=None,
            )
            self._insert_revision(connection, revision)
            if owns_transaction:
                connection.commit()
            return LearningReportFinalizationResult(report, revision)
        except sqlite3.Error as error:
            if owns_transaction and connection.in_transaction:
                connection.rollback()
            raise ReportFinalizationError(
                f"Berichtrevision konnte nicht gespeichert werden: {error}"
            ) from error
        except Exception:
            if owns_transaction and connection.in_transaction:
                connection.rollback()
            raise
        finally:
            if owns_transaction:
                connection.close()

    def get_report_for_source_draft(
        self,
        report_draft_id: str,
    ) -> LearningReportRecord | None:
        with self._source_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    learning_report_id,
                    source_report_draft_id,
                    student_id,
                    report_type,
                    period_start,
                    period_end,
                    created_at
                FROM learning_reports
                WHERE source_report_draft_id = ?
                """,
                (report_draft_id,),
            ).fetchone()
        return self._report_from_row(row) if row is not None else None

    def get_report(
        self,
        learning_report_id: str,
    ) -> LearningReportRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    learning_report_id,
                    source_report_draft_id,
                    student_id,
                    report_type,
                    period_start,
                    period_end,
                    created_at
                FROM learning_reports
                WHERE learning_report_id = ?
                """,
                (learning_report_id,),
            ).fetchone()
        return self._report_from_row(row) if row is not None else None

    def list_revisions(
        self,
        learning_report_id: str,
    ) -> tuple[LearningReportRevisionRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    learning_report_revision_id,
                    learning_report_id,
                    revision_number,
                    status,
                    snapshot_schema_version,
                    snapshot_json,
                    snapshot_sha256,
                    finalized_at,
                    finalized_by_display_name,
                    superseded_at
                FROM learning_report_revisions
                WHERE learning_report_id = ?
                ORDER BY revision_number
                """,
                (learning_report_id,),
            ).fetchall()
        return tuple(self._revision_from_row(row) for row in rows)

    def get_revision(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportRevisionRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    learning_report_revision_id,
                    learning_report_id,
                    revision_number,
                    status,
                    snapshot_schema_version,
                    snapshot_json,
                    snapshot_sha256,
                    finalized_at,
                    finalized_by_display_name,
                    superseded_at
                FROM learning_report_revisions
                WHERE learning_report_revision_id = ?
                """,
                (learning_report_revision_id,),
            ).fetchone()
        return self._revision_from_row(row) if row is not None else None

    def list_revision_histories_for_student(
        self,
        student_id: str,
    ) -> tuple[LearningReportRevisionHistory, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    report.learning_report_id,
                    report.source_report_draft_id,
                    report.student_id,
                    report.report_type,
                    report.period_start,
                    report.period_end,
                    report.created_at,
                    revision.learning_report_revision_id,
                    revision.revision_number,
                    revision.status,
                    revision.snapshot_schema_version,
                    revision.snapshot_json,
                    revision.snapshot_sha256,
                    revision.finalized_at,
                    revision.finalized_by_display_name,
                    revision.superseded_at
                FROM learning_reports AS report
                JOIN learning_report_revisions AS revision
                  ON revision.learning_report_id = report.learning_report_id
                WHERE report.student_id = ?
                ORDER BY
                    report.source_report_draft_id,
                    revision.revision_number DESC,
                    revision.learning_report_revision_id
                """,
                (student_id,),
            ).fetchall()
        histories: dict[
            str,
            tuple[LearningReportRecord, list[LearningReportRevisionRecord]],
        ] = {}
        for row in rows:
            report = self._report_from_row(row)
            _existing, revisions = histories.setdefault(
                report.learning_report_id,
                (report, []),
            )
            revisions.append(self._revision_from_row(row))
        return tuple(
            LearningReportRevisionHistory(report, tuple(revisions))
            for report, revisions in histories.values()
        )

    def _competency_evidence(
        self,
        connection: sqlite3.Connection,
        student_id: str,
        competency_id: str,
    ) -> tuple[LearningReportCompetencyEvidenceSource, ...]:
        points = [
            LearningReportCompetencyEvidenceSource(
                row["date"],
                row["rating"],
                "observation",
                row["observation_id"],
            )
            for row in connection.execute(
                """
                SELECT o.date, r.rating, o.observation_id
                FROM observation_competency_ratings r
                JOIN observations o ON o.observation_id = r.observation_id
                WHERE r.competency_id = ?
                  AND o.student_id = ?
                  AND o.active = 1
                """,
                (competency_id, student_id),
            ).fetchall()
        ]
        confirmation = connection.execute(
            """
            SELECT confirmed_at, confirmed_rating
            FROM student_competency_confirmations
            WHERE student_id = ? AND competency_id = ?
            """,
            (student_id, competency_id),
        ).fetchone()
        if confirmation is not None:
            points.append(
                LearningReportCompetencyEvidenceSource(
                    confirmation["confirmed_at"][:10],
                    confirmation["confirmed_rating"],
                    "confirmation",
                    competency_id,
                )
            )
        return tuple(
            sorted(
                points,
                key=lambda item: (
                    item.recorded_on,
                    item.source_type,
                    item.source_id,
                ),
            )
        )

    def _subject_name(
        self,
        connection: sqlite3.Connection,
        subject_id: str,
    ) -> str:
        row = connection.execute(
            """
            SELECT subject_name
            FROM competencies
            WHERE subject_id = ?
            ORDER BY
                CASE WHEN active = 1 AND catalog_status = 'current' THEN 0 ELSE 1 END,
                sort_order,
                competency_id
            LIMIT 1
            """,
            (subject_id,),
        ).fetchone()
        return str(row["subject_name"]).strip() if row is not None else ""

    def _next_id(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        prefix: str,
    ) -> str:
        rows = connection.execute(
            f"SELECT {column_name} FROM {table_name}"
        ).fetchall()
        next_number = 1
        for row in rows:
            value = str(row[column_name])
            if not value.startswith(f"{prefix}-"):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return f"{prefix}-{next_number:0{ID_SEQUENCE_WIDTH}d}"

    def _insert_revision(
        self,
        connection: sqlite3.Connection,
        revision: LearningReportRevisionRecord,
    ) -> None:
        connection.execute(
            """
            INSERT INTO learning_report_revisions (
                learning_report_revision_id,
                learning_report_id,
                revision_number,
                status,
                snapshot_schema_version,
                snapshot_json,
                snapshot_sha256,
                finalized_at,
                finalized_by_display_name,
                superseded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.learning_report_revision_id,
                revision.learning_report_id,
                revision.revision_number,
                revision.status,
                revision.snapshot_schema_version,
                revision.snapshot_json,
                revision.snapshot_sha256,
                revision.finalized_at,
                revision.finalized_by_display_name,
                revision.superseded_at,
            ),
        )

    def _report_from_row(self, row: sqlite3.Row) -> LearningReportRecord:
        return LearningReportRecord(
            row["learning_report_id"],
            row["source_report_draft_id"],
            row["student_id"],
            row["report_type"],
            row["period_start"],
            row["period_end"],
            row["created_at"],
        )

    def _revision_from_row(
        self,
        row: sqlite3.Row,
    ) -> LearningReportRevisionRecord:
        return LearningReportRevisionRecord(
            row["learning_report_revision_id"],
            row["learning_report_id"],
            int(row["revision_number"]),
            row["status"],
            int(row["snapshot_schema_version"]),
            row["snapshot_json"],
            row["snapshot_sha256"],
            row["finalized_at"],
            row["finalized_by_display_name"],
            row["superseded_at"],
        )


class SQLiteLearningReportPdfArtifactRepository:
    """Persist immutable report PDF references beside managed document files."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def next_artifact_id(self) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT learning_report_pdf_artifact_id
                FROM learning_report_pdf_artifacts
                """
            ).fetchall()
        next_number = 1
        for row in rows:
            value = str(row["learning_report_pdf_artifact_id"])
            if not value.startswith(f"{LEARNING_REPORT_PDF_ARTIFACT_ID_PREFIX}-"):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return (
            f"{LEARNING_REPORT_PDF_ARTIFACT_ID_PREFIX}-"
            f"{next_number:0{ID_SEQUENCE_WIDTH}d}"
        )

    def get_for_revision(
        self,
        learning_report_revision_id: str,
    ) -> LearningReportPdfArtifactRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    learning_report_pdf_artifact_id,
                    learning_report_revision_id,
                    relative_file_path,
                    mime_type,
                    file_size_bytes,
                    snapshot_sha256,
                    pdf_sha256,
                    created_at
                FROM learning_report_pdf_artifacts
                WHERE learning_report_revision_id = ?
                """,
                (learning_report_revision_id,),
            ).fetchone()
        return self._artifact_from_row(row) if row is not None else None

    def get_by_artifact_id(
        self,
        learning_report_pdf_artifact_id: str,
    ) -> LearningReportPdfArtifactRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    learning_report_pdf_artifact_id,
                    learning_report_revision_id,
                    relative_file_path,
                    mime_type,
                    file_size_bytes,
                    snapshot_sha256,
                    pdf_sha256,
                    created_at
                FROM learning_report_pdf_artifacts
                WHERE learning_report_pdf_artifact_id = ?
                """,
                (learning_report_pdf_artifact_id,),
            ).fetchone()
        return self._artifact_from_row(row) if row is not None else None

    def save_artifact(
        self,
        artifact: LearningReportPdfArtifactRecord,
    ) -> LearningReportPdfArtifactRecord:
        try:
            with closing(self.database.connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO learning_report_pdf_artifacts (
                            learning_report_pdf_artifact_id,
                            learning_report_revision_id,
                            relative_file_path,
                            mime_type,
                            file_size_bytes,
                            snapshot_sha256,
                            pdf_sha256,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            artifact.learning_report_pdf_artifact_id,
                            artifact.learning_report_revision_id,
                            artifact.relative_file_path,
                            artifact.mime_type,
                            artifact.file_size_bytes,
                            artifact.snapshot_sha256,
                            artifact.pdf_sha256,
                            artifact.created_at,
                        ),
                    )
        except sqlite3.Error as error:
            raise LearningReportPdfError(
                f"Die PDF-Artefaktreferenz konnte nicht gespeichert werden: {error}"
            ) from error
        return artifact

    def resolve_file_path(self, relative_file_path: str) -> Path:
        relative = Path(relative_file_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise LearningReportPdfError(
                "Der verwaltete PDF-Artefaktpfad ist ungueltig."
            )
        root = self.database.path.parent.resolve()
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root):
            raise LearningReportPdfError(
                "Der verwaltete PDF-Artefaktpfad liegt ausserhalb des Datenverzeichnisses."
            )
        return resolved

    def _artifact_from_row(
        self,
        row: sqlite3.Row,
    ) -> LearningReportPdfArtifactRecord:
        return LearningReportPdfArtifactRecord(
            row["learning_report_pdf_artifact_id"],
            row["learning_report_revision_id"],
            row["relative_file_path"],
            row["mime_type"],
            int(row["file_size_bytes"]),
            row["snapshot_sha256"],
            row["pdf_sha256"],
            row["created_at"],
        )


class SQLiteLearningConferencePdfArtifactRepository:
    """Persist immutable LEG PDF references beside managed document files."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def next_artifact_id(self) -> str:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT learning_conference_pdf_artifact_id
                FROM learning_conference_pdf_artifacts
                """
            ).fetchall()
        next_number = 1
        for row in rows:
            value = str(row["learning_conference_pdf_artifact_id"])
            if not value.startswith(
                f"{LEARNING_CONFERENCE_PDF_ARTIFACT_ID_PREFIX}-"
            ):
                continue
            try:
                next_number = max(next_number, int(value.split("-", 1)[1]) + 1)
            except ValueError:
                continue
        return (
            f"{LEARNING_CONFERENCE_PDF_ARTIFACT_ID_PREFIX}-"
            f"{next_number:0{ID_SEQUENCE_WIDTH}d}"
        )

    def get_for_revision(
        self,
        learning_conference_revision_id: str,
    ) -> LearningConferencePdfArtifactRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    learning_conference_pdf_artifact_id,
                    learning_conference_revision_id,
                    relative_file_path,
                    mime_type,
                    file_size_bytes,
                    snapshot_sha256,
                    pdf_sha256,
                    created_at
                FROM learning_conference_pdf_artifacts
                WHERE learning_conference_revision_id = ?
                """,
                (learning_conference_revision_id,),
            ).fetchone()
        return self._artifact_from_row(row) if row is not None else None

    def get_by_artifact_id(
        self,
        learning_conference_pdf_artifact_id: str,
    ) -> LearningConferencePdfArtifactRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    learning_conference_pdf_artifact_id,
                    learning_conference_revision_id,
                    relative_file_path,
                    mime_type,
                    file_size_bytes,
                    snapshot_sha256,
                    pdf_sha256,
                    created_at
                FROM learning_conference_pdf_artifacts
                WHERE learning_conference_pdf_artifact_id = ?
                """,
                (learning_conference_pdf_artifact_id,),
            ).fetchone()
        return self._artifact_from_row(row) if row is not None else None

    def save_artifact(
        self,
        artifact: LearningConferencePdfArtifactRecord,
    ) -> LearningConferencePdfArtifactRecord:
        try:
            with closing(self.database.connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO learning_conference_pdf_artifacts (
                            learning_conference_pdf_artifact_id,
                            learning_conference_revision_id,
                            relative_file_path,
                            mime_type,
                            file_size_bytes,
                            snapshot_sha256,
                            pdf_sha256,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            artifact.learning_conference_pdf_artifact_id,
                            artifact.learning_conference_revision_id,
                            artifact.relative_file_path,
                            artifact.mime_type,
                            artifact.file_size_bytes,
                            artifact.snapshot_sha256,
                            artifact.pdf_sha256,
                            artifact.created_at,
                        ),
                    )
        except sqlite3.Error as error:
            raise LearningConferencePdfError(
                "Die LEG-PDF-Artefaktreferenz konnte nicht gespeichert werden: "
                f"{error}"
            ) from error
        return artifact

    def resolve_file_path(self, relative_file_path: str) -> Path:
        relative = Path(relative_file_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise LearningConferencePdfError(
                "Der verwaltete LEG-PDF-Artefaktpfad ist ungueltig."
            )
        root = self.database.path.parent.resolve()
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root):
            raise LearningConferencePdfError(
                "Der verwaltete LEG-PDF-Artefaktpfad liegt ausserhalb des Datenverzeichnisses."
            )
        return resolved

    @staticmethod
    def _artifact_from_row(
        row: sqlite3.Row,
    ) -> LearningConferencePdfArtifactRecord:
        return LearningConferencePdfArtifactRecord(
            row["learning_conference_pdf_artifact_id"],
            row["learning_conference_revision_id"],
            row["relative_file_path"],
            row["mime_type"],
            int(row["file_size_bytes"]),
            row["snapshot_sha256"],
            row["pdf_sha256"],
            row["created_at"],
        )


def create_sqlite_seed_database(path: Path = SQLITE_SPIKE_PATH) -> SQLiteDatabase:
    """Create a SQLite test database from deterministic reference data."""
    database = SQLiteDatabase(path)
    database.replace_seed_data(seed_reference_data())
    return database


def _course_seed_row(course: CourseRecord, index: int) -> tuple[object, ...]:
    color_name, color_hex = _course_color_from_key(course.color_key, index)
    return (
        course.course_id,
        course.course_name,
        color_hex,
        color_name,
        color_hex,
        index,
        int(course.active),
        course.year_level,
    )


def _course_color_from_key(color_key: str, fallback_index: int = 0) -> tuple[str, str]:
    normalized_color_key = color_key.strip()
    if normalized_color_key and not normalized_color_key.startswith("#"):
        normalized_color_key = f"#{normalized_color_key}"
    for color_name, color_hex in COURSE_COLOR_OPTIONS:
        if normalized_color_key.upper() == color_hex.upper():
            return color_name, color_hex
    return COURSE_COLOR_OPTIONS[fallback_index % len(COURSE_COLOR_OPTIONS)]


def _competency_catalog_row(entry: object, index: int) -> tuple[object, ...]:
    label = str(getattr(entry, "competency_label", "")).strip()
    if not label:
        label = str(getattr(entry, "learning_area", "")).strip()
    subject_id = getattr(entry, "subject_id", None)
    if subject_id is None:
        subject_id = getattr(entry, "subject_key")
    catalog_default_active = bool(
        getattr(entry, "catalog_default_active", getattr(entry, "is_active"))
    )
    return (
        getattr(entry, "competency_id"),
        subject_id,
        getattr(entry, "subject_display_name"),
        getattr(entry, "subject_full_name", ""),
        getattr(entry, "official_subject_name", ""),
        getattr(entry, "school_context_name", ""),
        getattr(entry, "grade_band", ""),
        label,
        getattr(entry, "competency_text"),
        getattr(entry, "learning_stage", "cross_stage"),
        getattr(entry, "learning_area"),
        getattr(entry, "competency_group"),
        getattr(entry, "source_reference", ""),
        getattr(entry, "catalog_status", "current"),
        getattr(entry, "activation_group_key", ""),
        index,
        int(catalog_default_active),
        int(catalog_default_active),
        int(getattr(entry, "is_core_subject")),
    )


def _competency_from_row(row: sqlite3.Row) -> CompetencyRecord:
    return CompetencyRecord(
        row["competency_id"],
        row["subject_id"],
        row["subject_name"],
        row["subject_full_name"],
        row["official_subject_name"],
        row["school_context_name"],
        row["grade_band"],
        row["label"],
        row["description"],
        row["learning_stage"],
        row["learning_area"],
        row["competency_group"] or "",
        row["source_reference"],
        row["catalog_status"],
        row["activation_group_key"],
        int(row["sort_order"]),
        bool(row[ACTIVE]),
        bool(row["catalog_default_active"]),
        bool(row["is_core_subject"]),
    )


def _student_record_from_v3(
    student: V3Student,
    membership: CurrentStudentMembershipProjection | None,
) -> StudentRecord:
    enrolled = (
        membership is not None
        and membership.resolution_status is AssignmentResolutionStatus.ENROLLED
    )
    return StudentRecord(
        student.student_id,
        student.first_name,
        student.last_name,
        membership.group_id if enrolled and membership.group_id is not None else "",
        (
            membership.course_id
            if enrolled and membership.course_id is not None
            else ""
        ),
        student.notes,
        student.active,
        student.created_at.isoformat(),
        student.updated_at.isoformat(),
        (
            student.archived_at.isoformat()
            if student.archived_at is not None
            else None
        ),
    )


def _require_report_period_end(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ReportFinalizationError(
            "Berichtszeitraum muss ein gültiges period_end enthalten."
        ) from error


def _require_leg_conference_date(value: str) -> date:
    if not value:
        raise LearningConferenceCompletionError(
            LearningConferenceCompletionErrorCode.CONFERENCE_DATE_MISSING,
            "Für den Abschluss ist ein Gesprächsdatum erforderlich.",
        )
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise LearningConferenceCompletionError(
            LearningConferenceCompletionErrorCode.CONFERENCE_DATE_INVALID,
            "Das Gesprächsdatum ist ungültig.",
        ) from error


def _require_report_assignment(
    assignment: AssignmentAtDateProjection,
) -> None:
    if (
        assignment.resolution_status
        is AssignmentResolutionStatus.ENROLLED
    ):
        if all(
            (
                assignment.group_id,
                assignment.group_name,
                assignment.course_id,
                assignment.course_name,
            )
        ):
            return
        raise ReportFinalizationError(
            "Die historische Kurs- oder Stammgruppenbezeichnung ist nicht "
            "vollständig auflösbar."
        )
    if (
        assignment.resolution_status
        is AssignmentResolutionStatus.AMBIGUOUS
    ):
        raise ReportFinalizationError(
            "Die Zuordnung am Ende des Berichtszeitraums ist nicht eindeutig."
        )
    raise ReportFinalizationError(
        "Am Ende des Berichtszeitraums besteht keine eindeutige "
        "eingeschriebene Kurs- und Stammgruppenzuordnung."
    )


def _require_leg_assignment(
    assignment: AssignmentAtDateProjection,
) -> None:
    status = assignment.resolution_status
    if status is AssignmentResolutionStatus.ENROLLED:
        if all(
            (
                assignment.group_id,
                assignment.group_name,
                assignment.course_id,
                assignment.course_name,
            )
        ):
            return
        raise LearningConferenceCompletionError(
            LearningConferenceCompletionErrorCode.ASSIGNMENT_MISSING,
            "Die historische Kurs- oder Stammgruppenbezeichnung ist nicht "
            "vollständig auflösbar.",
        )
    if status is AssignmentResolutionStatus.AMBIGUOUS:
        raise LearningConferenceCompletionError(
            LearningConferenceCompletionErrorCode.ASSIGNMENT_AMBIGUOUS,
            "Die Zuordnung am Gesprächsdatum ist nicht eindeutig.",
        )
    if status is AssignmentResolutionStatus.EXITED:
        raise LearningConferenceCompletionError(
            LearningConferenceCompletionErrorCode.ASSIGNMENT_EXITED,
            "Am Gesprächsdatum besteht keine eingeschriebene Zuordnung.",
        )
    raise LearningConferenceCompletionError(
        LearningConferenceCompletionErrorCode.ASSIGNMENT_MISSING,
        "Am Gesprächsdatum besteht keine eindeutige Kurs- und "
        "Stammgruppenzuordnung.",
    )


def _document_from_row(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        row["document_id"],
        row[STUDENT_ID],
        row["observation_id"] or "",
        row["title"],
        row["document_type"],
        row["file_path"],
        row["original_filename"],
        row[CREATED_AT],
        row["note"] or "",
        bool(row[ACTIVE]),
    )


def _required_event_timestamp(value: str) -> str:
    normalized = canonical_utc_second(value)
    if normalized is None:
        raise ObservationRepositoryError(
            "Technischer Ereigniszeitpunkt ist ungueltig."
        )
    return normalized


def _rating_event_payload(
    rating: ObservationCompetencyRatingRecord,
) -> dict[str, object]:
    return {
        "competency_id": rating.competency_id,
        "subject_id": rating.subject_id,
        "subject_display_name": rating.subject_display_name,
        "learning_area": rating.learning_area,
        "competency_group": rating.competency_group,
        "competency_text": rating.competency_text,
        "rating": rating.rating,
    }


def _observation_business_payload(
    observation: ObservationRecord,
) -> dict[str, object]:
    return {
        "observation_id": observation.observation_id,
        "student_id": observation.student_id,
        "date": observation.date,
        "subject_id": observation.subject_id,
        "context": observation.context,
        "note": observation.note,
        "active": observation.active,
        "ratings": [
            _rating_event_payload(rating)
            for rating in sorted(
                observation.competency_ratings,
                key=lambda item: item.competency_id,
            )
        ],
    }


def _observation_event_payload(
    observation: ObservationRecord,
) -> dict[str, object]:
    return {
        **_observation_business_payload(observation),
        "created_at": observation.created_at,
        "updated_at": observation.updated_at,
    }


def _affected_observation_pairs(
    before: ObservationRecord,
    after: ObservationRecord,
) -> set[tuple[str, str]]:
    before_ratings = {
        rating.competency_id: rating.rating
        for rating in before.competency_ratings
    }
    after_ratings = {
        rating.competency_id: rating.rating
        for rating in after.competency_ratings
    }
    if before.student_id != after.student_id:
        return {
            *((before.student_id, competency_id) for competency_id in before_ratings),
            *((after.student_id, competency_id) for competency_id in after_ratings),
        }
    if before.active and not after.active:
        return {
            (before.student_id, competency_id)
            for competency_id in before_ratings
        }
    return {
        (after.student_id, competency_id)
        for competency_id in set(before_ratings) | set(after_ratings)
        if before_ratings.get(competency_id) != after_ratings.get(competency_id)
    }


def _document_to_row(document: DocumentRecord) -> tuple[object, ...]:
    return (
        document.document_id,
        document.student_id,
        document.observation_id or None,
        document.title,
        document.document_type,
        document.file_path,
        document.original_filename,
        document.created_at,
        document.note,
        int(document.active),
    )


def _timetable_entry_from_row(row: sqlite3.Row) -> TimetableEntry:
    return TimetableEntry(
        row["timetable_entry_id"],
        int(row["weekday"]),
        row["start_time"],
        row["end_time"],
        row["subject_id"],
        row["target_type"],
        row["target_id"],
        row["room"] or "",
        bool(row["active"]),
        int(row["sort_order"]),
        row["created_at"],
        row["updated_at"],
        row["deleted_at"],
    )


def _timetable_entry_values(entry: TimetableEntry) -> tuple[object, ...]:
    return (
        entry.timetable_entry_id,
        entry.weekday,
        entry.start_time,
        entry.end_time,
        entry.subject_id,
        entry.target_type,
        entry.target_id,
        entry.room,
        int(entry.active),
        entry.sort_order,
        entry.created_at,
        entry.updated_at,
        entry.deleted_at,
    )
