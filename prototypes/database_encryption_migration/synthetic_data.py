"""Deterministic, unmistakably synthetic data for the migration prototype."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3


SYNTHETIC_GUARD_TABLE = "__jkm_security_sprint_4_synthetic_guard"
SYNTHETIC_GUARD_VALUE = "jkm-security-sprint-4-synthetic-only-v1"
SYNTHETIC_APPLICATION_ID = 0x4A4B4D34
SYNTHETIC_USER_VERSION = 4


@dataclass(frozen=True)
class SyntheticScale:
    students: int = 48
    courses: int = 8
    competencies: int = 36
    observations: int = 480
    reports: int = 96
    documents: int = 144
    attachments: int = 240

    @classmethod
    def large(cls) -> "SyntheticScale":
        return cls(
            students=320,
            courses=20,
            competencies=120,
            observations=8_000,
            reports=960,
            documents=1_600,
            attachments=3_200,
        )

    def validate(self) -> None:
        values = (
            self.students,
            self.courses,
            self.competencies,
            self.observations,
            self.reports,
            self.documents,
            self.attachments,
        )
        if any(value < 1 for value in values):
            raise ValueError("synthetic_scale_must_be_positive")


def create_synthetic_source(path: Path, scale: SyntheticScale | None = None) -> None:
    """Create one standalone fixture; every visible value says synthetic."""

    selected = scale or SyntheticScale()
    selected.validate()
    database = Path(path)
    if database.exists() or database.is_symlink():
        raise FileExistsError("synthetic_source_target_exists")
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA page_size = 4096")
        connection.execute("PRAGMA auto_vacuum = FULL")
        connection.execute(f"PRAGMA application_id = {SYNTHETIC_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {SYNTHETIC_USER_VERSION}")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA secure_delete = ON")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.executescript(_SCHEMA)
        with connection:
            connection.execute(
                f"INSERT INTO {SYNTHETIC_GUARD_TABLE}(guard_value, fixture_version) "
                "VALUES (?, ?)",
                (SYNTHETIC_GUARD_VALUE, 1),
            )
            _insert_courses(connection, selected)
            _insert_students(connection, selected)
            _insert_competencies(connection, selected)
            _insert_observations(connection, selected)
            _insert_reports(connection, selected)
            _insert_documents(connection, selected)
            _insert_attachments(connection, selected)
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != [("ok",)] or foreign_keys:
            raise RuntimeError("synthetic_source_integrity_failed")
    finally:
        connection.close()


def _insert_courses(connection: sqlite3.Connection, scale: SyntheticScale) -> None:
    connection.executemany(
        "INSERT INTO courses(course_id, title, color_hex) VALUES (?, ?, ?)",
        [
            (
                f"SYN-CRS-{index:04d}",
                f"Synthetischer Kurs {index:04d}",
                f"#{(index * 2_654_435_761) & 0xFFFFFF:06X}",
            )
            for index in range(1, scale.courses + 1)
        ],
    )


def _insert_students(connection: sqlite3.Connection, scale: SyntheticScale) -> None:
    connection.executemany(
        "INSERT INTO students(student_id, display_name, course_id, active) "
        "VALUES (?, ?, ?, ?)",
        [
            (
                f"SYN-STU-{index:06d}",
                f"Synthetische Testperson {index:06d}",
                f"SYN-CRS-{((index - 1) % scale.courses) + 1:04d}",
                0 if index % 19 == 0 else 1,
            )
            for index in range(1, scale.students + 1)
        ],
    )


def _insert_competencies(
    connection: sqlite3.Connection, scale: SyntheticScale
) -> None:
    subjects = ("Mathematik", "Deutsch", "Englisch", "Sachunterricht")
    connection.executemany(
        "INSERT INTO competencies(competency_id, subject, area, title) "
        "VALUES (?, ?, ?, ?)",
        [
            (
                f"SYN-CMP-{index:06d}",
                subjects[(index - 1) % len(subjects)],
                f"Synthetischer Bereich {((index - 1) % 12) + 1:02d}",
                f"Synthetische Kompetenz {index:06d}",
            )
            for index in range(1, scale.competencies + 1)
        ],
    )


def _insert_observations(
    connection: sqlite3.Connection, scale: SyntheticScale
) -> None:
    ratings = ("--", "-", "0", "+", "++")
    observations = []
    links = []
    for index in range(1, scale.observations + 1):
        observation_id = f"SYN-OBS-{index:08d}"
        observations.append(
            (
                observation_id,
                f"SYN-STU-{((index - 1) % scale.students) + 1:06d}",
                f"2026-{((index - 1) % 12) + 1:02d}-{((index - 1) % 28) + 1:02d}",
                f"Rein synthetische Beobachtung {index:08d}",
            )
        )
        for offset in range(3):
            competency_index = ((index * 7 + offset * 13) % scale.competencies) + 1
            links.append(
                (
                    observation_id,
                    f"SYN-CMP-{competency_index:06d}",
                    ratings[(index + offset) % len(ratings)],
                )
            )
    connection.executemany(
        "INSERT INTO observations(observation_id, student_id, observed_on, note) "
        "VALUES (?, ?, ?, ?)",
        observations,
    )
    connection.executemany(
        "INSERT INTO observation_competencies(observation_id, competency_id, rating) "
        "VALUES (?, ?, ?)",
        links,
    )


def _insert_reports(connection: sqlite3.Connection, scale: SyntheticScale) -> None:
    reports = []
    links = []
    for index in range(1, scale.reports + 1):
        report_id = f"SYN-RPT-{index:07d}"
        reports.append(
            (
                report_id,
                f"SYN-STU-{((index - 1) % scale.students) + 1:06d}",
                f"SYNTH-{2025 + (index % 2)}-H{1 + (index % 2)}",
                "draft" if index % 4 else "final-synthetic",
                f"Rein synthetischer Berichtstext {index:07d}",
            )
        )
        for offset in range(4):
            competency_index = ((index * 11 + offset * 17) % scale.competencies) + 1
            links.append(
                (report_id, f"SYN-CMP-{competency_index:06d}", offset + 1)
            )
    connection.executemany(
        "INSERT INTO reports(report_id, student_id, period_code, status, body) "
        "VALUES (?, ?, ?, ?, ?)",
        reports,
    )
    connection.executemany(
        "INSERT INTO report_competencies(report_id, competency_id, position) "
        "VALUES (?, ?, ?)",
        links,
    )


def _insert_documents(connection: sqlite3.Connection, scale: SyntheticScale) -> None:
    connection.executemany(
        "INSERT INTO documents(document_id, student_id, synthetic_file_name, sha256) "
        "VALUES (?, ?, ?, ?)",
        [
            (
                f"SYN-DOC-{index:07d}",
                f"SYN-STU-{((index - 1) % scale.students) + 1:06d}",
                f"synthetic-document-{index:07d}.txt",
                hashlib.sha256(f"synthetic-document-{index}".encode()).hexdigest(),
            )
            for index in range(1, scale.documents + 1)
        ],
    )


def _insert_attachments(connection: sqlite3.Connection, scale: SyntheticScale) -> None:
    rows = []
    for index in range(1, scale.attachments + 1):
        seed = hashlib.sha256(f"synthetic-attachment-{index}".encode()).digest()
        payload = (seed * (1 + (index % 9)))[: 32 + (index % 241)]
        rows.append(
            (
                f"SYN-ATT-{index:07d}",
                f"SYN-DOC-{((index - 1) % scale.documents) + 1:07d}",
                "application/x-jkm-synthetic",
                payload,
            )
        )
    connection.executemany(
        "INSERT INTO attachments(attachment_id, document_id, media_type, payload) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )


_SCHEMA = f"""
CREATE TABLE {SYNTHETIC_GUARD_TABLE} (
    guard_value TEXT PRIMARY KEY,
    fixture_version INTEGER NOT NULL CHECK(fixture_version = 1)
) WITHOUT ROWID;

CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    color_hex TEXT NOT NULL CHECK(length(color_hex) = 7)
);

CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    course_id TEXT NOT NULL REFERENCES courses(course_id),
    active INTEGER NOT NULL CHECK(active IN (0, 1))
);

CREATE TABLE competencies (
    competency_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    area TEXT NOT NULL,
    title TEXT NOT NULL
);

CREATE TABLE observations (
    observation_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    observed_on TEXT NOT NULL,
    note TEXT NOT NULL
);

CREATE TABLE observation_competencies (
    observation_id TEXT NOT NULL REFERENCES observations(observation_id) ON DELETE CASCADE,
    competency_id TEXT NOT NULL REFERENCES competencies(competency_id),
    rating TEXT NOT NULL CHECK(rating IN ('--', '-', '0', '+', '++')),
    PRIMARY KEY (observation_id, competency_id)
) WITHOUT ROWID;

CREATE TABLE observation_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id TEXT NOT NULL UNIQUE,
    event_name TEXT NOT NULL
);

CREATE TABLE reports (
    report_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    period_code TEXT NOT NULL,
    status TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE report_competencies (
    report_id TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    competency_id TEXT NOT NULL REFERENCES competencies(competency_id),
    position INTEGER NOT NULL CHECK(position > 0),
    PRIMARY KEY (report_id, competency_id),
    UNIQUE (report_id, position)
);

CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    synthetic_file_name TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK(length(sha256) = 64)
);

CREATE TABLE attachments (
    attachment_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    media_type TEXT NOT NULL,
    payload BLOB NOT NULL
);

CREATE INDEX idx_students_course ON students(course_id, student_id);
CREATE INDEX idx_observations_student_date ON observations(student_id, observed_on);
CREATE INDEX idx_reports_student_period ON reports(student_id, period_code);
CREATE INDEX idx_documents_student ON documents(student_id, document_id);
CREATE INDEX idx_attachments_document ON attachments(document_id, attachment_id);

CREATE TRIGGER trg_observations_audit_after_insert
AFTER INSERT ON observations
BEGIN
    INSERT INTO observation_audit(observation_id, event_name)
    VALUES (NEW.observation_id, 'synthetic_insert');
END;

CREATE VIEW student_evidence_summary AS
SELECT s.student_id,
       COUNT(DISTINCT o.observation_id) AS observation_count,
       COUNT(DISTINCT r.report_id) AS report_count,
       COUNT(DISTINCT d.document_id) AS document_count
FROM students AS s
LEFT JOIN observations AS o ON o.student_id = s.student_id
LEFT JOIN reports AS r ON r.student_id = s.student_id
LEFT JOIN documents AS d ON d.student_id = s.student_id
GROUP BY s.student_id;

CREATE VIEW report_document_summary AS
SELECT r.report_id, r.student_id, r.period_code, COUNT(d.document_id) AS document_count
FROM reports AS r
LEFT JOIN documents AS d ON d.student_id = r.student_id
GROUP BY r.report_id, r.student_id, r.period_code;
"""
