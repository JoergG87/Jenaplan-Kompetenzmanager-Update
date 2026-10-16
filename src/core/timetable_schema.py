"""Exact synthetic normalized timetable schema; product remains Final V4."""
from .schema_registry import (DatabaseSchemaRegistry, FINAL_V4_SCHEMA_REGISTRATION,
    RegisteredSchemaIdentity, SCHEMA_FINGERPRINT_ALGORITHM, SchemaRegistration,
    SchemaUpgradeRelation)
from .lesson_times_schema import SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION

TIMETABLE_TARGET_STATEMENT = """CREATE TABLE timetable_entries_v5_target (
    timetable_entry_id TEXT PRIMARY KEY NOT NULL,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 5),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    entry_kind TEXT NOT NULL CHECK (entry_kind IN ('subject_lesson', 'homeroom_session')),
    target_type TEXT NOT NULL CHECK (target_type IN ('group', 'course', 'course_group')),
    target_id TEXT NOT NULL,
    room TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT NOT NULL DEFAULT '',
    CHECK (entry_kind <> 'homeroom_session' OR target_type = 'group')
)"""
TIMETABLE_SUBJECTS_STATEMENT = """CREATE TABLE timetable_entry_subjects (
    timetable_entry_id TEXT NOT NULL,
    subject_id TEXT NOT NULL CHECK (length(trim(subject_id)) > 0),
    PRIMARY KEY (timetable_entry_id, subject_id),
    FOREIGN KEY (timetable_entry_id) REFERENCES timetable_entries(timetable_entry_id)
        ON UPDATE RESTRICT ON DELETE CASCADE
)"""
TIMETABLE_INDEX_STATEMENT = """CREATE INDEX idx_timetable_entries_week_time
    ON timetable_entries(weekday, start_time, end_time, sort_order)"""

SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION = SchemaRegistration(
    "synthetic_v6_normalized_timetable",
    RegisteredSchemaIdentity(6, "4d8f4e056f5897114b3af8899947bce1f7362c52a3da96525f32baec3e9d2cc2", SCHEMA_FINGERPRINT_ALGORITHM),
    frozenset(),
)
SYNTHETIC_TIMETABLE_REGISTRY = DatabaseSchemaRegistry(
    (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION,
     SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION),
    tuple(SchemaUpgradeRelation(source.identity, SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity)
          for source in (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION)),
)

# Native SQLCipher 4.17 fingerprint measured after the complete transactional rebuild.
