"""SQLite storage spike for Sprint 5.2a."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from .constants import (
    ACTIVE,
    ARCHIVED_AT,
    COLOR_KEY,
    COURSE_ID,
    COURSE_NAME,
    CREATED_AT,
    FIRST_NAME,
    GROUP_ID,
    GROUP_NAME,
    LAST_NAME,
    STUDENT_ID,
    STUDENT_NOTES,
    UPDATED_AT,
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
                        active INTEGER NOT NULL CHECK (active IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS courses (
                        course_id TEXT PRIMARY KEY,
                        course_name TEXT NOT NULL,
                        color_key TEXT,
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
                    """
                )

    def replace_seed_data(self, data: WorkbookData) -> None:
        self.initialize_schema()
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("DELETE FROM students")
                connection.execute("DELETE FROM groups")
                connection.execute("DELETE FROM courses")
                connection.executemany(
                    """
                    INSERT INTO groups (group_id, group_name, active)
                    VALUES (?, ?, ?)
                    """,
                    (
                        (group.group_id, group.group_name, int(group.active))
                        for group in data.groups
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO courses (course_id, course_name, color_key, active)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        (
                            course.course_id,
                            course.course_name,
                            course.color_key,
                            int(course.active),
                        )
                        for course in data.courses
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
                SELECT course_id, course_name, color_key, active
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()
        return tuple(
            CourseRecord(
                row[COURSE_ID],
                row[COURSE_NAME],
                row[COLOR_KEY] or "",
                bool(row[ACTIVE]),
            )
            for row in rows
        )


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
