"""SQLite storage spike for Sprint 5.2a."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .database_compatibility import (
    DATABASE_COMPATIBILITY_VERSION,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
    DatabaseCompatibilityStatus,
)
from .database_engine import SQLiteConnectionProvider
from .persistence_events import (
    PersistenceEventKind,
    PersistenceEventRecord,
    PersistenceOrderingState,
    SQLitePersistenceEventRepository,
    canonical_payload_hash,
    canonical_utc_second,
    migrate_persistence_events,
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
    STUDENT_NOTES,
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
    LearningReportRevisionRecord,
    LearningReportStudentSource,
    LearningReportSubjectSource,
    ReportFinalizationError,
)
from .learning_report_pdf import (
    LearningReportPdfArtifactRecord,
    LearningReportPdfError,
)
from .student import StudentRepositoryError
from .records import (
    CourseRecord,
    GroupRecord,
    ReferenceData,
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
    ) -> None:
        self.path = path
        self._connection_provider = (
            connection_provider or SQLiteConnectionProvider()
        )
        self._create = bool(create)
        self._initialize_schema = bool(initialize_schema)

    def connect(self) -> sqlite3.Connection:
        return self._connection_provider.connect(
            self.path,
            create=self._create,
        )

    def initialize_schema(self) -> None:
        if not self._initialize_schema:
            return
        with closing(self.connect()) as connection:
            schema_object_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM sqlite_schema
                    WHERE name NOT LIKE 'sqlite_%'
                    """
                ).fetchone()[0]
            )
            if schema_object_count:
                compatibility = DatabaseCompatibilityInspector().inspect_connection(
                    connection
                )
                if compatibility.status is DatabaseCompatibilityStatus.EXACT:
                    return
                DatabaseCompatibilityPolicy.require_backup_compatible(compatibility)
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    migrate_persistence_events(
                        connection,
                        target_user_version=DATABASE_COMPATIBILITY_VERSION,
                    )
                return
            with connection:
                connection.executescript(
                    """
                    BEGIN IMMEDIATE;

                    CREATE TABLE IF NOT EXISTS groups (
                        group_id TEXT PRIMARY KEY,
                        group_name TEXT NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL CHECK (active IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS courses (
                        course_id TEXT PRIMARY KEY,
                        course_name TEXT NOT NULL,
                        color_key TEXT,
                        color_name TEXT NOT NULL DEFAULT '',
                        color_hex TEXT NOT NULL DEFAULT '',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL CHECK (active IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS students (
                        student_id TEXT PRIMARY KEY,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        course_id TEXT NOT NULL,
                        student_notes TEXT,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        archived_at TEXT,
                        FOREIGN KEY (group_id) REFERENCES groups(group_id),
                        FOREIGN KEY (course_id) REFERENCES courses(course_id)
                    );

                    CREATE TABLE IF NOT EXISTS observations (
                        observation_id TEXT PRIMARY KEY,
                        student_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        context TEXT,
                        note TEXT,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)) DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (student_id) REFERENCES students(student_id)
                    );

                    CREATE TABLE IF NOT EXISTS competencies (
                        competency_id TEXT PRIMARY KEY,
                        subject_id TEXT NOT NULL,
                        subject_name TEXT NOT NULL,
                        subject_full_name TEXT NOT NULL DEFAULT '',
                        official_subject_name TEXT NOT NULL DEFAULT '',
                        school_context_name TEXT NOT NULL DEFAULT '',
                        grade_band TEXT NOT NULL DEFAULT '',
                        label TEXT NOT NULL,
                        description TEXT NOT NULL,
                        learning_stage TEXT NOT NULL DEFAULT 'cross_stage'
                            CHECK (learning_stage IN ('stage_1_3', 'stage_4', 'cross_stage')),
                        learning_area TEXT NOT NULL,
                        competency_group TEXT,
                        source_reference TEXT NOT NULL DEFAULT '',
                        catalog_status TEXT NOT NULL DEFAULT 'current'
                            CHECK (catalog_status IN ('current', 'legacy')),
                        activation_group_key TEXT NOT NULL DEFAULT '',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)),
                        catalog_default_active INTEGER NOT NULL CHECK (catalog_default_active IN (0, 1)) DEFAULT 1,
                        is_core_subject INTEGER NOT NULL CHECK (is_core_subject IN (0, 1)) DEFAULT 1
                    );

                    CREATE TABLE IF NOT EXISTS observation_competency_ratings (
                        observation_id TEXT NOT NULL,
                        competency_id TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        subject_display_name TEXT NOT NULL,
                        learning_area TEXT NOT NULL,
                        competency_group TEXT,
                        competency_text TEXT NOT NULL,
                        rating TEXT NOT NULL CHECK (rating IN ('++', '+', '-', '--')),
                        PRIMARY KEY (observation_id, competency_id),
                        FOREIGN KEY (observation_id)
                            REFERENCES observations(observation_id)
                            ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS student_competency_confirmations (
                        student_id TEXT NOT NULL,
                        competency_id TEXT NOT NULL,
                        confirmed_rating TEXT NOT NULL CHECK (confirmed_rating IN ('++', '+', '-', '--')),
                        confirmed_at TEXT NOT NULL,
                        note TEXT,
                        PRIMARY KEY (student_id, competency_id),
                        FOREIGN KEY (student_id) REFERENCES students(student_id),
                        FOREIGN KEY (competency_id) REFERENCES competencies(competency_id)
                    );

                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY,
                        student_id TEXT NOT NULL,
                        observation_id TEXT,
                        title TEXT NOT NULL,
                        document_type TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        original_filename TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        note TEXT,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)) DEFAULT 1,
                        FOREIGN KEY (student_id) REFERENCES students(student_id),
                        FOREIGN KEY (observation_id) REFERENCES observations(observation_id)
                    );

                    CREATE TABLE IF NOT EXISTS course_groups (
                        course_group_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL CHECK (active IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS course_group_student_groups (
                        course_group_id TEXT NOT NULL,
                        student_group_id TEXT NOT NULL,
                        PRIMARY KEY (course_group_id, student_group_id),
                        FOREIGN KEY (course_group_id) REFERENCES course_groups(course_group_id),
                        FOREIGN KEY (student_group_id) REFERENCES groups(group_id)
                    );

                    CREATE TABLE IF NOT EXISTS course_group_courses (
                        course_group_id TEXT NOT NULL,
                        course_id TEXT NOT NULL,
                        PRIMARY KEY (course_group_id, course_id),
                        FOREIGN KEY (course_group_id) REFERENCES course_groups(course_group_id),
                        FOREIGN KEY (course_id) REFERENCES courses(course_id)
                    );

                    CREATE TABLE IF NOT EXISTS documentation_subject_settings (
                        subject_id TEXT PRIMARY KEY,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)),
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS timetable_entries (
                        timetable_entry_id TEXT PRIMARY KEY,
                        weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 5),
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        target_type TEXT NOT NULL CHECK (
                            target_type IN ('group', 'course', 'course_group')
                        ),
                        target_id TEXT NOT NULL,
                        room TEXT NOT NULL DEFAULT '',
                        active INTEGER NOT NULL CHECK (active IN (0, 1)),
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        deleted_at TEXT NOT NULL DEFAULT ''
                    );

                    CREATE TABLE IF NOT EXISTS report_drafts (
                        report_draft_id TEXT PRIMARY KEY,
                        student_id TEXT NOT NULL,
                        report_type TEXT NOT NULL CHECK (report_type = 'learning_development'),
                        period_start TEXT NOT NULL,
                        period_end TEXT NOT NULL,
                        status TEXT NOT NULL CHECK (status = 'draft'),
                        teacher_name TEXT NOT NULL DEFAULT '',
                        overall_text TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (student_id) REFERENCES students(student_id)
                    );

                    CREATE TABLE IF NOT EXISTS report_draft_subjects (
                        report_draft_id TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        strengths_text TEXT NOT NULL DEFAULT '',
                        development_text TEXT NOT NULL DEFAULT '',
                        support_needs_text TEXT NOT NULL DEFAULT '',
                        next_goals_text TEXT NOT NULL DEFAULT '',
                        PRIMARY KEY (report_draft_id, subject_id),
                        FOREIGN KEY (report_draft_id)
                            REFERENCES report_drafts(report_draft_id)
                            ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS report_draft_competencies (
                        report_draft_id TEXT NOT NULL,
                        competency_id TEXT NOT NULL,
                        PRIMARY KEY (report_draft_id, competency_id),
                        FOREIGN KEY (report_draft_id)
                            REFERENCES report_drafts(report_draft_id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (competency_id) REFERENCES competencies(competency_id)
                    );

                    CREATE TABLE IF NOT EXISTS report_draft_observations (
                        report_draft_id TEXT NOT NULL,
                        observation_id TEXT NOT NULL,
                        PRIMARY KEY (report_draft_id, observation_id),
                        FOREIGN KEY (report_draft_id)
                            REFERENCES report_drafts(report_draft_id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (observation_id) REFERENCES observations(observation_id)
                    );

                    CREATE TABLE IF NOT EXISTS report_draft_charts (
                        report_draft_id TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        chart_type TEXT NOT NULL CHECK (
                            chart_type IN (
                                'documentation_coverage',
                                'competency_timeline',
                                'observation_timeline'
                            )
                        ),
                        PRIMARY KEY (report_draft_id, subject_id, chart_type),
                        FOREIGN KEY (report_draft_id)
                            REFERENCES report_drafts(report_draft_id)
                            ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS learning_reports (
                        learning_report_id TEXT PRIMARY KEY,
                        source_report_draft_id TEXT NOT NULL UNIQUE,
                        student_id TEXT NOT NULL,
                        report_type TEXT NOT NULL,
                        period_start TEXT NOT NULL,
                        period_end TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (source_report_draft_id)
                            REFERENCES report_drafts(report_draft_id),
                        FOREIGN KEY (student_id) REFERENCES students(student_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_report_revisions (
                        learning_report_revision_id TEXT PRIMARY KEY,
                        learning_report_id TEXT NOT NULL,
                        revision_number INTEGER NOT NULL CHECK (revision_number > 0),
                        status TEXT NOT NULL CHECK (
                            status IN ('finalized', 'superseded')
                        ),
                        snapshot_schema_version INTEGER NOT NULL CHECK (
                            snapshot_schema_version > 0
                        ),
                        snapshot_json TEXT NOT NULL,
                        snapshot_sha256 TEXT NOT NULL CHECK (
                            length(snapshot_sha256) = 64
                        ),
                        finalized_at TEXT NOT NULL,
                        finalized_by_display_name TEXT NOT NULL CHECK (
                            length(trim(finalized_by_display_name)) > 0
                        ),
                        superseded_at TEXT,
                        UNIQUE (learning_report_id, revision_number),
                        CHECK (
                            (status = 'finalized' AND superseded_at IS NULL)
                            OR
                            (status = 'superseded' AND superseded_at IS NOT NULL)
                        ),
                        FOREIGN KEY (learning_report_id)
                            REFERENCES learning_reports(learning_report_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_report_pdf_artifacts (
                        learning_report_pdf_artifact_id TEXT PRIMARY KEY,
                        learning_report_revision_id TEXT NOT NULL UNIQUE,
                        relative_file_path TEXT NOT NULL UNIQUE,
                        mime_type TEXT NOT NULL CHECK (mime_type = 'application/pdf'),
                        file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0),
                        snapshot_sha256 TEXT NOT NULL CHECK (
                            length(snapshot_sha256) = 64
                        ),
                        pdf_sha256 TEXT NOT NULL CHECK (length(pdf_sha256) = 64),
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (learning_report_revision_id)
                            REFERENCES learning_report_revisions(
                                learning_report_revision_id
                            )
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_drafts (
                        learning_conference_draft_id TEXT PRIMARY KEY,
                        student_id TEXT NOT NULL,
                        period_start TEXT NOT NULL DEFAULT '',
                        period_end TEXT NOT NULL DEFAULT '',
                        conference_date TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL CHECK (status = 'draft'),
                        responsible_teacher TEXT NOT NULL DEFAULT '',
                        conversation_entry_text TEXT NOT NULL DEFAULT '',
                        child_retrospective_text TEXT NOT NULL DEFAULT '',
                        teacher_perspective_text TEXT NOT NULL DEFAULT '',
                        strengths_text TEXT NOT NULL DEFAULT '',
                        development_fields_text TEXT NOT NULL DEFAULT '',
                        prepared_goals_text TEXT NOT NULL DEFAULT '',
                        prepared_support_text TEXT NOT NULL DEFAULT '',
                        prepared_agreements_text TEXT NOT NULL DEFAULT '',
                        agreed_goals_text TEXT NOT NULL DEFAULT '',
                        agreed_support_text TEXT NOT NULL DEFAULT '',
                        agreed_agreements_text TEXT NOT NULL DEFAULT '',
                        responsibilities_text TEXT NOT NULL DEFAULT '',
                        next_review_date TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (student_id) REFERENCES students(student_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_conferences (
                        learning_conference_id TEXT PRIMARY KEY,
                        source_learning_conference_draft_id TEXT NOT NULL UNIQUE,
                        student_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (source_learning_conference_draft_id)
                            REFERENCES learning_conference_drafts(
                                learning_conference_draft_id
                            ),
                        FOREIGN KEY (student_id) REFERENCES students(student_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_revisions (
                        learning_conference_revision_id TEXT PRIMARY KEY,
                        learning_conference_id TEXT NOT NULL,
                        revision_number INTEGER NOT NULL CHECK (revision_number > 0),
                        status TEXT NOT NULL CHECK (
                            status IN ('completed', 'superseded')
                        ),
                        snapshot_schema_version INTEGER NOT NULL CHECK (
                            snapshot_schema_version > 0
                        ),
                        snapshot_json TEXT NOT NULL,
                        snapshot_sha256 TEXT NOT NULL CHECK (
                            length(snapshot_sha256) = 64
                        ),
                        completed_at TEXT NOT NULL,
                        completed_by_display_name TEXT NOT NULL CHECK (
                            length(trim(completed_by_display_name)) > 0
                        ),
                        superseded_at TEXT,
                        UNIQUE (learning_conference_id, revision_number),
                        CHECK (
                            (status = 'completed' AND superseded_at IS NULL)
                            OR
                            (status = 'superseded' AND superseded_at IS NOT NULL)
                        ),
                        FOREIGN KEY (learning_conference_id)
                            REFERENCES learning_conferences(learning_conference_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_pdf_artifacts (
                        learning_conference_pdf_artifact_id TEXT PRIMARY KEY,
                        learning_conference_revision_id TEXT NOT NULL UNIQUE,
                        relative_file_path TEXT NOT NULL UNIQUE,
                        mime_type TEXT NOT NULL CHECK (mime_type = 'application/pdf'),
                        file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0),
                        snapshot_sha256 TEXT NOT NULL CHECK (
                            length(snapshot_sha256) = 64
                        ),
                        pdf_sha256 TEXT NOT NULL CHECK (length(pdf_sha256) = 64),
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (learning_conference_revision_id)
                            REFERENCES learning_conference_revisions(
                                learning_conference_revision_id
                            )
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_draft_subjects (
                        learning_conference_draft_id TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        PRIMARY KEY (learning_conference_draft_id, subject_id),
                        FOREIGN KEY (learning_conference_draft_id)
                            REFERENCES learning_conference_drafts(learning_conference_draft_id)
                            ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_draft_cross_topics (
                        learning_conference_draft_id TEXT NOT NULL,
                        cross_topic_key TEXT NOT NULL CHECK (
                            cross_topic_key IN (
                                'work_habits',
                                'social_behavior',
                                'independence',
                                'learning_organization'
                            )
                        ),
                        PRIMARY KEY (learning_conference_draft_id, cross_topic_key),
                        FOREIGN KEY (learning_conference_draft_id)
                            REFERENCES learning_conference_drafts(learning_conference_draft_id)
                            ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_draft_competencies (
                        learning_conference_draft_id TEXT NOT NULL,
                        competency_id TEXT NOT NULL,
                        PRIMARY KEY (learning_conference_draft_id, competency_id),
                        FOREIGN KEY (learning_conference_draft_id)
                            REFERENCES learning_conference_drafts(learning_conference_draft_id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (competency_id) REFERENCES competencies(competency_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_draft_observations (
                        learning_conference_draft_id TEXT NOT NULL,
                        observation_id TEXT NOT NULL,
                        PRIMARY KEY (learning_conference_draft_id, observation_id),
                        FOREIGN KEY (learning_conference_draft_id)
                            REFERENCES learning_conference_drafts(learning_conference_draft_id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (observation_id) REFERENCES observations(observation_id)
                    );

                    CREATE TABLE IF NOT EXISTS learning_conference_draft_charts (
                        learning_conference_draft_id TEXT NOT NULL,
                        chart_type TEXT NOT NULL CHECK (
                            chart_type IN (
                                'documentation_coverage',
                                'competency_timeline',
                                'observation_timeline'
                            )
                        ),
                        PRIMARY KEY (learning_conference_draft_id, chart_type),
                        FOREIGN KEY (learning_conference_draft_id)
                            REFERENCES learning_conference_drafts(learning_conference_draft_id)
                            ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_groups_name
                        ON groups(group_name);
                    CREATE INDEX IF NOT EXISTS idx_courses_name
                        ON courses(course_name);
                    CREATE INDEX IF NOT EXISTS idx_observations_student_date
                        ON observations(student_id, date);
                    CREATE INDEX IF NOT EXISTS idx_competencies_subject_sort
                        ON competencies(subject_id, sort_order);
                    CREATE INDEX IF NOT EXISTS idx_observation_ratings_competency
                        ON observation_competency_ratings(competency_id);
                    CREATE INDEX IF NOT EXISTS idx_competency_confirmations_student
                        ON student_competency_confirmations(student_id);
                    CREATE INDEX IF NOT EXISTS idx_competency_confirmations_competency
                        ON student_competency_confirmations(competency_id);
                    CREATE INDEX IF NOT EXISTS idx_documents_student
                        ON documents(student_id, active, created_at);
                    CREATE INDEX IF NOT EXISTS idx_documents_observation
                        ON documents(observation_id, active, created_at);
                    CREATE INDEX IF NOT EXISTS idx_course_groups_name
                        ON course_groups(name);
                    CREATE INDEX IF NOT EXISTS idx_course_group_student_groups_group
                        ON course_group_student_groups(student_group_id);
                    CREATE INDEX IF NOT EXISTS idx_course_group_courses_course
                        ON course_group_courses(course_id);
                    CREATE INDEX IF NOT EXISTS idx_documentation_subject_settings_active
                        ON documentation_subject_settings(active, subject_id);
                    CREATE INDEX IF NOT EXISTS idx_timetable_entries_week_time
                        ON timetable_entries(weekday, start_time, end_time, sort_order);
                    CREATE INDEX IF NOT EXISTS idx_report_drafts_student_updated
                        ON report_drafts(student_id, updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_report_draft_competencies_competency
                        ON report_draft_competencies(competency_id);
                    CREATE INDEX IF NOT EXISTS idx_report_draft_observations_observation
                        ON report_draft_observations(observation_id);
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_report_current_revision
                        ON learning_report_revisions(learning_report_id)
                        WHERE status = 'finalized';
                    CREATE INDEX IF NOT EXISTS idx_learning_report_revisions_report_number
                        ON learning_report_revisions(learning_report_id, revision_number);
                    CREATE INDEX IF NOT EXISTS idx_learning_report_pdf_artifacts_revision
                        ON learning_report_pdf_artifacts(learning_report_revision_id);
                    CREATE INDEX IF NOT EXISTS idx_learning_conference_drafts_student_updated
                        ON learning_conference_drafts(student_id, updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_learning_conference_draft_competencies
                        ON learning_conference_draft_competencies(competency_id);
                    CREATE INDEX IF NOT EXISTS idx_learning_conference_draft_observations
                        ON learning_conference_draft_observations(observation_id);
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_conference_current_revision
                        ON learning_conference_revisions(learning_conference_id)
                        WHERE status = 'completed';
                    CREATE INDEX IF NOT EXISTS idx_learning_conference_revisions_number
                        ON learning_conference_revisions(
                            learning_conference_id,
                            revision_number
                        );
                    CREATE INDEX IF NOT EXISTS idx_learning_conference_pdf_artifacts_revision
                        ON learning_conference_pdf_artifacts(
                            learning_conference_revision_id
                        );

                    CREATE TRIGGER IF NOT EXISTS trg_learning_report_revisions_immutable_update
                    BEFORE UPDATE ON learning_report_revisions
                    WHEN NOT (
                        OLD.status = 'finalized'
                        AND NEW.status = 'superseded'
                        AND OLD.superseded_at IS NULL
                        AND NEW.superseded_at IS NOT NULL
                        AND NEW.learning_report_revision_id IS OLD.learning_report_revision_id
                        AND NEW.learning_report_id IS OLD.learning_report_id
                        AND NEW.revision_number IS OLD.revision_number
                        AND NEW.snapshot_schema_version IS OLD.snapshot_schema_version
                        AND NEW.snapshot_json IS OLD.snapshot_json
                        AND NEW.snapshot_sha256 IS OLD.snapshot_sha256
                        AND NEW.finalized_at IS OLD.finalized_at
                        AND NEW.finalized_by_display_name IS OLD.finalized_by_display_name
                    )
                    BEGIN
                        SELECT RAISE(ABORT, 'learning report revisions are immutable');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_report_revisions_immutable_delete
                    BEFORE DELETE ON learning_report_revisions
                    BEGIN
                        SELECT RAISE(ABORT, 'learning report revisions cannot be deleted');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_reports_immutable_update
                    BEFORE UPDATE ON learning_reports
                    BEGIN
                        SELECT RAISE(ABORT, 'learning reports are immutable');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_reports_immutable_delete
                    BEFORE DELETE ON learning_reports
                    BEGIN
                        SELECT RAISE(ABORT, 'learning reports cannot be deleted');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_report_pdf_artifacts_immutable_update
                    BEFORE UPDATE ON learning_report_pdf_artifacts
                    BEGIN
                        SELECT RAISE(ABORT, 'learning report PDF artifacts are immutable');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_report_pdf_artifacts_immutable_delete
                    BEFORE DELETE ON learning_report_pdf_artifacts
                    BEGIN
                        SELECT RAISE(ABORT, 'learning report PDF artifacts cannot be deleted');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_conference_revisions_immutable_update
                    BEFORE UPDATE ON learning_conference_revisions
                    WHEN NOT (
                        OLD.status = 'completed'
                        AND NEW.status = 'superseded'
                        AND OLD.superseded_at IS NULL
                        AND NEW.superseded_at IS NOT NULL
                        AND NEW.learning_conference_revision_id IS OLD.learning_conference_revision_id
                        AND NEW.learning_conference_id IS OLD.learning_conference_id
                        AND NEW.revision_number IS OLD.revision_number
                        AND NEW.snapshot_schema_version IS OLD.snapshot_schema_version
                        AND NEW.snapshot_json IS OLD.snapshot_json
                        AND NEW.snapshot_sha256 IS OLD.snapshot_sha256
                        AND NEW.completed_at IS OLD.completed_at
                        AND NEW.completed_by_display_name IS OLD.completed_by_display_name
                    )
                    BEGIN
                        SELECT RAISE(ABORT, 'learning conference revisions are immutable');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_conference_revisions_immutable_delete
                    BEFORE DELETE ON learning_conference_revisions
                    BEGIN
                        SELECT RAISE(ABORT, 'learning conference revisions cannot be deleted');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_conferences_immutable_update
                    BEFORE UPDATE ON learning_conferences
                    BEGIN
                        SELECT RAISE(ABORT, 'learning conferences are immutable');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_conferences_immutable_delete
                    BEFORE DELETE ON learning_conferences
                    BEGIN
                        SELECT RAISE(ABORT, 'learning conferences cannot be deleted');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_conference_pdf_artifacts_immutable_update
                    BEFORE UPDATE ON learning_conference_pdf_artifacts
                    BEGIN
                        SELECT RAISE(ABORT, 'learning conference PDF artifacts are immutable');
                    END;

                    CREATE TRIGGER IF NOT EXISTS trg_learning_conference_pdf_artifacts_immutable_delete
                    BEFORE DELETE ON learning_conference_pdf_artifacts
                    BEGIN
                        SELECT RAISE(ABORT, 'learning conference PDF artifacts cannot be deleted');
                    END;
                    """
                )
                self._ensure_column(connection, "groups", "sort_order", "INTEGER NOT NULL DEFAULT 0")
                self._ensure_column(connection, "courses", "color_name", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "courses", "color_hex", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "courses", "sort_order", "INTEGER NOT NULL DEFAULT 0")
                self._ensure_column(connection, "competencies", "subject_full_name", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "competencies", "official_subject_name", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "competencies", "school_context_name", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "competencies", "grade_band", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "competencies", "learning_stage", "TEXT NOT NULL DEFAULT 'cross_stage'")
                self._ensure_column(connection, "competencies", "source_reference", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "competencies", "catalog_status", "TEXT NOT NULL DEFAULT 'current'")
                self._ensure_column(connection, "competencies", "activation_group_key", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "competencies", "catalog_default_active", "INTEGER NOT NULL DEFAULT 1")
                self._ensure_column(connection, "competencies", "is_core_subject", "INTEGER NOT NULL DEFAULT 1")
                self._ensure_column(connection, "timetable_entries", "deleted_at", "TEXT NOT NULL DEFAULT ''")
                self._backfill_course_colors(connection)
                migrate_persistence_events(
                    connection,
                    target_user_version=DATABASE_COMPATIBILITY_VERSION,
                )

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
                            active
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            _course_seed_row(course, index)
                            for index, course in enumerate(seed_data.courses)
                        ),
                    )
                self._ensure_default_course_group(connection)

    def replace_seed_data(self, data: ReferenceData) -> None:
        self.initialize_schema()
        with closing(self.connect()) as connection:
            with connection:
                if connection.execute(
                    "SELECT 1 FROM persistence_events LIMIT 1"
                ).fetchone() is not None:
                    raise RuntimeError(
                        "Seed-Daten koennen nach Persistenzereignissen nur durch "
                        "einen vollstaendigen Store-Neuaufbau ersetzt werden."
                    )
                connection.execute("DELETE FROM learning_conference_drafts")
                connection.execute("DELETE FROM report_drafts")
                connection.execute("DELETE FROM observation_competency_ratings")
                connection.execute("DELETE FROM documents")
                connection.execute("DELETE FROM observations")
                connection.execute("DELETE FROM student_competency_confirmations")
                connection.execute("DELETE FROM documentation_subject_settings")
                connection.execute("DELETE FROM timetable_entries")
                connection.execute("DELETE FROM course_group_courses")
                connection.execute("DELETE FROM course_group_student_groups")
                connection.execute("DELETE FROM course_groups")
                connection.execute("DELETE FROM students")
                connection.execute("DELETE FROM groups")
                connection.execute("DELETE FROM courses")
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
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
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
                        group_id,
                        course_id,
                        student_notes,
                        active,
                        created_at,
                        updated_at,
                        archived_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            student.student_id,
                            student.first_name,
                            student.last_name,
                            student.group_id,
                            student.course_id,
                            student.student_notes,
                            int(student.active),
                            student.created_at,
                            student.updated_at,
                            student.archived_at,
                        )
                        for student in data.students
                    ),
                )
                self._ensure_default_course_group(connection)

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        declaration: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {declaration}"
            )

    def _backfill_course_colors(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT course_id, color_key, color_name, color_hex
            FROM courses
            ORDER BY sort_order, course_id
            """
        ).fetchall()
        for index, row in enumerate(rows):
            if row[COLOR_NAME] and row[COLOR_HEX]:
                continue
            color_name, color_hex = _course_color_from_key(row[COLOR_KEY] or "", index)
            connection.execute(
                """
                UPDATE courses
                SET color_name = ?, color_hex = ?, color_key = ?
                WHERE course_id = ?
                """,
                (color_name, color_hex, color_hex, row[COURSE_ID]),
            )

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
    """Read and write student records in SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_students(self) -> tuple[StudentRecord, ...]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    student_id,
                    first_name,
                    last_name,
                    group_id,
                    course_id,
                    student_notes,
                    active,
                    created_at,
                    updated_at,
                    archived_at
                FROM students
                ORDER BY student_id
                """
            ).fetchall()
        return tuple(_student_from_row(row) for row in rows)

    def get_student(self, student_id: str) -> StudentRecord | None:
        return self.get_student_by_id(student_id)

    def get_student_by_id(self, student_id: str) -> StudentRecord | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    student_id,
                    first_name,
                    last_name,
                    group_id,
                    course_id,
                    student_notes,
                    active,
                    created_at,
                    updated_at,
                    archived_at
                FROM students
                WHERE student_id = ?
                """,
                (student_id,),
            ).fetchone()
        if row is None:
            return None
        return _student_from_row(row)

    def create_student(self, student: StudentRecord) -> StudentRecord:
        if self.get_student_by_id(student.student_id) is not None:
            raise StudentRepositoryError(f"student_id existiert bereits: {student.student_id}")
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO students (
                        student_id,
                        first_name,
                        last_name,
                        group_id,
                        course_id,
                        student_notes,
                        active,
                        created_at,
                        updated_at,
                        archived_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _student_to_row(student),
                )
        return student

    def update_student(self, student: StudentRecord) -> StudentRecord:
        if self.get_student_by_id(student.student_id) is None:
            raise StudentRepositoryError(f"student_id nicht gefunden: {student.student_id}")
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE students
                    SET
                        first_name = ?,
                        last_name = ?,
                        group_id = ?,
                        course_id = ?,
                        student_notes = ?,
                        active = ?,
                        created_at = ?,
                        updated_at = ?,
                        archived_at = ?
                    WHERE student_id = ?
                    """,
                    (
                        student.first_name,
                        student.last_name,
                        student.group_id,
                        student.course_id,
                        student.student_notes,
                        int(student.active),
                        student.created_at,
                        student.updated_at,
                        student.archived_at,
                        student.student_id,
                    ),
                )
        return student

    def archive_student(self, student: StudentRecord) -> StudentRecord:
        return self.update_student(student)


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
                SELECT course_id, course_name, color_key, color_hex, active
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
        self.database.initialize_schema()

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
        self.database.initialize_schema()

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


class SQLiteMasterDataRepository:
    """Read and write persistent master data in SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self.database.ensure_master_data_defaults()

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

    def upsert_student_group(self, group: MasterDataGroupRecord) -> MasterDataGroupRecord:
        with closing(self.database.connect()) as connection:
            with connection:
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
                    sort_order
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
            )
            for row in rows
        )

    def upsert_course(self, course: MasterDataCourseRecord) -> MasterDataCourseRecord:
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO courses (
                        course_id,
                        course_name,
                        color_key,
                        color_name,
                        color_hex,
                        sort_order,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(course_id) DO UPDATE SET
                        course_name = excluded.course_name,
                        color_key = excluded.color_key,
                        color_name = excluded.color_name,
                        color_hex = excluded.color_hex,
                        sort_order = excluded.sort_order,
                        active = excluded.active
                    """,
                    (
                        course.course_id,
                        course.course_name,
                        course.color_hex,
                        course.color_name,
                        course.color_hex,
                        course.sort_order,
                        int(course.active),
                    ),
                )
        return course

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

    def load_completion_source(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceCompletionSource | None:
        draft = SQLiteLearningConferenceDraftRepository(
            self.database
        ).get_learning_conference_draft(learning_conference_draft_id)
        if draft is None:
            return None
        selected_subject_ids = set(draft.subject_ids)
        with closing(self.database.connect()) as connection:
            student_row = connection.execute(
                """
                SELECT
                    s.student_id,
                    s.first_name,
                    s.last_name,
                    s.group_id,
                    COALESCE(g.group_name, '') AS group_name,
                    s.course_id,
                    COALESCE(c.course_name, '') AS course_name
                FROM students s
                LEFT JOIN groups g ON g.group_id = s.group_id
                LEFT JOIN courses c ON c.course_id = s.course_id
                WHERE s.student_id = ?
                """,
                (draft.student_id,),
            ).fetchone()
            student = (
                LearningConferenceStudentSource(
                    student_row["student_id"],
                    student_row["first_name"],
                    student_row["last_name"],
                    student_row["group_id"],
                    student_row["group_name"],
                    student_row["course_id"],
                    student_row["course_name"],
                )
                if student_row is not None
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
        connection = self.database.connect()
        try:
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
            connection.commit()
            return LearningConferenceCompletionResult(conference, revision, True)
        except sqlite3.Error as error:
            connection.rollback()
            raise LearningConferenceCompletionError(
                LearningConferenceCompletionErrorCode.PERSISTENCE_FAILED,
                f"LEG-Revision konnte nicht gespeichert werden: {error}",
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_conference_for_source_draft(
        self,
        learning_conference_draft_id: str,
    ) -> LearningConferenceRecord | None:
        with closing(self.database.connect()) as connection:
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

    def load_finalization_source(
        self,
        report_draft_id: str,
    ) -> LearningReportFinalizationSource | None:
        draft = SQLiteReportDraftRepository(self.database).get_report_draft(
            report_draft_id
        )
        if draft is None:
            return None
        selected_subject_ids = {subject.subject_id for subject in draft.subjects}
        with closing(self.database.connect()) as connection:
            student_row = connection.execute(
                """
                SELECT
                    s.student_id,
                    s.first_name,
                    s.last_name,
                    s.group_id,
                    COALESCE(g.group_name, '') AS group_name,
                    s.course_id,
                    COALESCE(c.course_name, '') AS course_name
                FROM students s
                LEFT JOIN groups g ON g.group_id = s.group_id
                LEFT JOIN courses c ON c.course_id = s.course_id
                WHERE s.student_id = ?
                """,
                (draft.student_id,),
            ).fetchone()
            student = (
                LearningReportStudentSource(
                    student_row["student_id"],
                    student_row["first_name"],
                    student_row["last_name"],
                    student_row["group_id"],
                    student_row["group_name"],
                    student_row["course_id"],
                    student_row["course_name"],
                )
                if student_row is not None
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
        connection = self.database.connect()
        try:
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
            connection.commit()
            return LearningReportFinalizationResult(report, revision)
        except sqlite3.Error as error:
            connection.rollback()
            raise ReportFinalizationError(
                f"Berichtrevision konnte nicht gespeichert werden: {error}"
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_report_for_source_draft(
        self,
        report_draft_id: str,
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


def _student_from_row(row: sqlite3.Row) -> StudentRecord:
    return StudentRecord(
        row[STUDENT_ID],
        row[FIRST_NAME],
        row[LAST_NAME],
        row[GROUP_ID],
        row[COURSE_ID],
        row[STUDENT_NOTES] or "",
        bool(row[ACTIVE]),
        row[CREATED_AT],
        row[UPDATED_AT],
        row[ARCHIVED_AT],
    )


def _student_to_row(student: StudentRecord) -> tuple[object, ...]:
    return (
        student.student_id,
        student.first_name,
        student.last_name,
        student.group_id,
        student.course_id,
        student.student_notes,
        int(student.active),
        student.created_at,
        student.updated_at,
        student.archived_at,
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
