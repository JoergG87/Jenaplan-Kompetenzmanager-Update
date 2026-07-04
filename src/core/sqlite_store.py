"""SQLite storage spike for Sprint 5.2a."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

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
from .student import StudentRepositoryError
from .student_projection import StudentProjectionBuilder
from .workbook_data import (
    CourseRecord,
    GroupRecord,
    StudentRecord,
    WorkbookData,
    seed_workbook_data,
)


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
    label: str
    description: str
    learning_area: str
    competency_group: str
    sort_order: int
    active: bool
    is_core_subject: bool


@dataclass(frozen=True)
class StudentCompetencyConfirmationRecord:
    """Persisted teacher-confirmed competency status for one student."""

    student_id: str
    competency_id: str
    confirmed_rating: str
    confirmed_at: str
    note: str = ""


class SQLiteDatabase:
    """Manage the Sprint 5.2a SQLite spike database."""

    def __init__(self, path: Path = SQLITE_SPIKE_PATH) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        with closing(self.connect()) as connection:
            with connection:
                connection.executescript(
                    """
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
                        label TEXT NOT NULL,
                        description TEXT NOT NULL,
                        learning_area TEXT NOT NULL,
                        competency_group TEXT,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL CHECK (active IN (0, 1)),
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
                    CREATE INDEX IF NOT EXISTS idx_course_groups_name
                        ON course_groups(name);
                    CREATE INDEX IF NOT EXISTS idx_course_group_student_groups_group
                        ON course_group_student_groups(student_group_id);
                    CREATE INDEX IF NOT EXISTS idx_course_group_courses_course
                        ON course_group_courses(course_id);
                    """
                )
                self._ensure_column(connection, "groups", "sort_order", "INTEGER NOT NULL DEFAULT 0")
                self._ensure_column(connection, "courses", "color_name", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "courses", "color_hex", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(connection, "courses", "sort_order", "INTEGER NOT NULL DEFAULT 0")
                self._ensure_column(connection, "competencies", "is_core_subject", "INTEGER NOT NULL DEFAULT 1")
                self._backfill_course_colors(connection)

    def ensure_master_data_defaults(self) -> None:
        """Create default master data only for empty master-data scopes."""
        self.initialize_schema()
        seed_data = seed_workbook_data()
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

    def replace_seed_data(self, data: WorkbookData) -> None:
        self.initialize_schema()
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("DELETE FROM observation_competency_ratings")
                connection.execute("DELETE FROM observations")
                connection.execute("DELETE FROM student_competency_confirmations")
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

    def create_observation(self, observation: ObservationRecord) -> ObservationRecord:
        if self.get_observation(observation.observation_id) is not None:
            raise ObservationRepositoryError(
                f"observation_id existiert bereits: {observation.observation_id}"
            )
        with closing(self.database.connect()) as connection:
            with connection:
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
        return observation

    def update_observation(self, observation: ObservationRecord) -> ObservationRecord:
        if self.get_observation(observation.observation_id) is None:
            raise ObservationRepositoryError(
                f"observation_id nicht gefunden: {observation.observation_id}"
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
        """Seed competencies only when the catalog table is empty."""
        self.database.initialize_schema()
        with closing(self.database.connect()) as connection:
            with connection:
                competency_count = connection.execute(
                    "SELECT COUNT(*) FROM competencies"
                ).fetchone()[0]
                if competency_count:
                    return
                connection.executemany(
                    """
                    INSERT INTO competencies (
                        competency_id,
                        subject_id,
                        subject_name,
                        label,
                        description,
                        learning_area,
                        competency_group,
                        sort_order,
                        active,
                        is_core_subject
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    label,
                    description,
                    learning_area,
                    competency_group,
                    sort_order,
                    active,
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
                    label,
                    description,
                    learning_area,
                    competency_group,
                    sort_order,
                    active,
                    is_core_subject
                FROM competencies
                WHERE competency_id = ?
                """,
                (competency_id,),
            ).fetchone()
        if row is None:
            return None
        return _competency_from_row(row)


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
    ) -> StudentCompetencyConfirmationRecord:
        self._validate_confirmation(confirmation)
        with closing(self.database.connect()) as connection:
            with connection:
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


def create_sqlite_seed_database(path: Path = SQLITE_SPIKE_PATH) -> SQLiteDatabase:
    """Create the SQLite spike database from the current workbook seed data."""
    database = SQLiteDatabase(path)
    database.replace_seed_data(seed_workbook_data())
    return database


def build_workbook_data_from_sqlite(path: Path = SQLITE_SPIKE_PATH) -> WorkbookData:
    """Read SQLite records and return the existing workbook projection model."""
    database = SQLiteDatabase(path)
    seed_data = seed_workbook_data()
    groups = SQLiteGroupRepository(database).list_groups()
    courses = SQLiteCourseRepository(database).list_courses()
    students = SQLiteStudentRepository(database).list_students()
    return StudentProjectionBuilder(
        groups,
        courses,
        seed_data.default_group_id,
        seed_data.default_student_id,
        seed_data.school_year,
    ).build(students)


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
    return (
        getattr(entry, "competency_id"),
        subject_id,
        getattr(entry, "subject_display_name"),
        label,
        getattr(entry, "competency_text"),
        getattr(entry, "learning_area"),
        getattr(entry, "competency_group"),
        index,
        int(getattr(entry, "is_active")),
        int(getattr(entry, "is_core_subject")),
    )


def _competency_from_row(row: sqlite3.Row) -> CompetencyRecord:
    return CompetencyRecord(
        row["competency_id"],
        row["subject_id"],
        row["subject_name"],
        row["label"],
        row["description"],
        row["learning_area"],
        row["competency_group"] or "",
        int(row["sort_order"]),
        bool(row[ACTIVE]),
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
