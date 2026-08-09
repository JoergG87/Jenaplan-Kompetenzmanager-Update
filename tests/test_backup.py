"""Focused tests for backup format v1 and its integrity boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import threading
import time
import warnings
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest

from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
    VerifyBackupQuery,
)
from src.core.backup import (
    BACKUP_FORMAT_VERSION,
    BackupInventoryService,
    BackupBusyError,
    BackupFileError,
    BackupFormatError,
    BackupIntegrityError,
    BackupService,
    BackupValidationError,
    BackupVerifier,
    SQLiteBackupEngine,
)
from src.core.database_compatibility import (
    UnknownDatabaseSchemaError,
    UnsupportedDatabaseVersionError,
)
from src.core.final_v4_schema import FinalV4SchemaInitializer
from src.desktop_app.runtime import RuntimePaths, runtime_paths


FIXED_NOW = datetime(2026, 7, 16, 12, 34, 56, tzinfo=UTC)


def _runtime(tmp_path: Path) -> RuntimePaths:
    paths = runtime_paths(tmp_path / "runtime")
    for directory in (
        paths.root,
        paths.documents,
        paths.exports,
        paths.backups,
        paths.logs,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    FinalV4SchemaInitializer().initialize(paths.database)
    return paths


def test_general_app_preferences_are_not_part_of_domain_backup(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    paths.app_preferences.write_text(
        '{"display_name":"Laura","format_version":1,"inactivity_minutes":15}\n',
        encoding="utf-8",
    )
    result = BackupApplicationService(now=lambda: FIXED_NOW).create(
        CreateBackupCommand(
            paths.database,
            paths,
            paths.backups,
            "0.2.0",
            "82df25df150e1de219a334d80904c25dbc371659",
        )
    )
    with zipfile.ZipFile(result.path) as archive:
        assert "app-preferences.json" not in archive.namelist()
        assert b"Laura" not in b"".join(archive.read(name) for name in archive.namelist())


def _insert_base_data(paths: RuntimePaths) -> None:
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO groups VALUES ('GRP-000001', 'Eulen', 0, 1)")
        connection.execute(
            "INSERT INTO courses "
            "(course_id, course_name, color_key, color_name, color_hex, "
            "sort_order, active, year_level) "
            "VALUES ('CRS-000001', 'Kurs 1', NULL, 'Blau', '#0000ff', 0, 1, 1)"
        )
        connection.execute(
            "INSERT INTO school_years VALUES "
            "('SY-2025-26', '2025/26', '2025-08-01', '2026-07-31', "
            "'current', '2025-07-01T00:00:00+00:00', NULL)"
        )
        connection.execute(
            "INSERT INTO students "
            "(student_id, first_name, last_name, notes, active, created_at, "
            "updated_at, archived_at) VALUES "
            "('STU-000001', 'Fiktiv', 'Kind', NULL, 1, "
            "'2026-01-01T00:00:00+00:00', "
            "'2026-01-01T00:00:00+00:00', NULL)"
        )
        connection.execute(
            "INSERT INTO student_school_year_assignments VALUES "
            "('ASG-000001', 'STU-000001', 'SY-2025-26', 'GRP-000001', "
            "'CRS-000001', 'enrolled', '2025-08-01', '2026-07-31', "
            "'2025-07-01T00:00:00+00:00', "
            "'2025-07-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO observations VALUES "
            "('OBS-000001', 'STU-000001', '2026-01-02', 'MAT', '', '', 1, "
            "'2026-01-02T00:00:00+00:00', '2026-01-02T00:00:00+00:00')"
        )


def _add_document(
    paths: RuntimePaths,
    document_id: str,
    payload: bytes,
    *,
    active: bool = True,
    external_path: Path | None = None,
    suffix: str = ".txt",
) -> Path:
    path = external_path or (
        paths.documents / "STU-000001" / f"{document_id}_Originalname{suffix}"
    )
    if external_path is None or payload:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    with sqlite3.connect(paths.database) as connection:
        connection.execute(
            "INSERT INTO documents "
            "(document_id, student_id, observation_id, title, document_type, "
            "file_path, original_filename, created_at, note, active) "
            "VALUES (?, 'STU-000001', NULL, 'Titel', 'Sonstiges', ?, "
            "'Personenname-Geheim.txt', '2026-01-03T00:00:00+00:00', "
            "'Geheime Notiz', ?)",
            (document_id, str(path), int(active)),
        )
    return path


def _add_final_pdfs(paths: RuntimePaths) -> tuple[Path, Path]:
    report_bytes = b"%PDF-1.4\nfinal-report\n%%EOF"
    conference_bytes = b"%PDF-1.4\nfinal-conference\n%%EOF"
    report_relative = Path(
        "documents/STU-000001/reports/RPT-000001/RPV-000001/final.pdf"
    )
    conference_relative = Path(
        "documents/STU-000001/learning_conferences/LCF-000001/LCV-000001/final.pdf"
    )
    report_path = paths.root / report_relative
    conference_path = paths.root / conference_relative
    report_path.parent.mkdir(parents=True, exist_ok=True)
    conference_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(report_bytes)
    conference_path.write_bytes(conference_bytes)
    report_snapshot = hashlib.sha256(b"report-snapshot").hexdigest()
    conference_snapshot = hashlib.sha256(b"conference-snapshot").hexdigest()
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO report_drafts "
            "(report_draft_id, student_id, report_type, period_start, period_end, "
            "status, teacher_name, overall_text, created_at, updated_at) "
            "VALUES ('RPD-000001', 'STU-000001', 'learning_development', "
            "'2026-01-01', '2026-06-30', 'draft', '', '', '2026-01-01', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO learning_reports VALUES "
            "('RPT-000001', 'RPD-000001', 'STU-000001', 'learning_development', "
            "'2026-01-01', '2026-06-30', '2026-06-30')"
        )
        connection.execute(
            "INSERT INTO learning_report_revisions VALUES "
            "('RPV-000001', 'RPT-000001', 1, 'finalized', 1, '{}', ?, "
            "'2026-06-30', 'Lehrkraft', NULL)",
            (report_snapshot,),
        )
        connection.execute(
            "INSERT INTO learning_report_pdf_artifacts VALUES "
            "('RPA-000001', 'RPV-000001', ?, 'application/pdf', ?, ?, ?, '2026-06-30')",
            (
                report_relative.as_posix(),
                len(report_bytes),
                report_snapshot,
                hashlib.sha256(report_bytes).hexdigest(),
            ),
        )
        connection.execute(
            "INSERT INTO learning_conference_drafts "
            "(learning_conference_draft_id, student_id, status, created_at, updated_at) "
            "VALUES ('LCD-000001', 'STU-000001', 'draft', '2026-01-01', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO learning_conferences VALUES "
            "('LCF-000001', 'LCD-000001', 'STU-000001', '2026-06-30')"
        )
        connection.execute(
            "INSERT INTO learning_conference_revisions VALUES "
            "('LCV-000001', 'LCF-000001', 1, 'completed', 1, '{}', ?, "
            "'2026-06-30', 'Lehrkraft', NULL)",
            (conference_snapshot,),
        )
        connection.execute(
            "INSERT INTO learning_conference_pdf_artifacts VALUES "
            "('LCA-000001', 'LCV-000001', ?, 'application/pdf', ?, ?, ?, '2026-06-30')",
            (
                conference_relative.as_posix(),
                len(conference_bytes),
                conference_snapshot,
                hashlib.sha256(conference_bytes).hexdigest(),
            ),
        )
    return report_path, conference_path


def _command(paths: RuntimePaths, target: Path | None = None) -> CreateBackupCommand:
    return CreateBackupCommand(
        database_path=paths.database,
        runtime_paths=paths,
        target_path=target or paths.backups,
        app_version="0.1.2",
        build_commit="82df25df150e1de219a334d80904c25dbc371659",
        source_tree_state="clean",
    )


def _create(
    paths: RuntimePaths,
    *,
    target: Path | None = None,
    engine: SQLiteBackupEngine | None = None,
    verifier: BackupVerifier | None = None,
):
    service = BackupApplicationService(
        now=lambda: FIXED_NOW,
        sqlite_engine=engine,
        verifier=verifier,
    )
    return service.create(_command(paths, target))


def _zip_payload(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def _rewrite_zip(path: Path, payload: dict[str, bytes] | list[tuple[str, bytes]]) -> None:
    entries = payload.items() if isinstance(payload, dict) else payload
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries:
                archive.writestr(name, content)


def _modified_manifest(path: Path, update) -> None:
    payload = _zip_payload(path)
    manifest = json.loads(payload["manifest.json"])
    update(manifest)
    payload["manifest.json"] = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    _rewrite_zip(path, payload)


def _live_state(paths: RuntimePaths) -> tuple[tuple[str, ...], tuple[tuple[str, bytes], ...]]:
    with sqlite3.connect(paths.database) as connection:
        database_dump = tuple(connection.iterdump())
    managed_bytes = tuple(
        sorted(
            (
                path.relative_to(paths.documents).as_posix(),
                path.read_bytes(),
            )
            for path in paths.documents.rglob("*")
            if path.is_file() and not path.is_symlink()
        )
    )
    return database_dump, managed_bytes


def _assert_no_own_backup_artifacts(directory: Path) -> None:
    assert not tuple(directory.glob(".incomplete-jkmbackup-*"))
    assert not tuple(directory.glob(".jkmbackup-staging-*"))


def test_consistent_backup_while_application_connection_is_open(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    open_connection = sqlite3.connect(paths.database)
    try:
        result = _create(paths)
    finally:
        open_connection.close()
    assert result.path.is_file()
    assert result.manifest.counts.students == 1


def test_sqlite_backup_api_is_used(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    used = False
    real_connect = sqlite3.connect

    class TrackingConnection(sqlite3.Connection):
        def backup(self, *args, **kwargs):
            nonlocal used
            used = True
            return super().backup(*args, **kwargs)

    def connect(*args, **kwargs):
        kwargs["factory"] = TrackingConnection
        return real_connect(*args, **kwargs)

    snapshot = tmp_path / "snapshot.sqlite"
    with mock.patch("src.core.backup.sqlite3.connect", side_effect=connect):
        SQLiteBackupEngine().create_snapshot(paths.database, snapshot)
    assert used


def test_long_write_transaction_retries_then_times_out(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    blocker = sqlite3.connect(paths.database, timeout=0)
    blocker.execute("PRAGMA journal_mode = DELETE")
    blocker.execute("BEGIN EXCLUSIVE")
    monotonic_calls: list[float] = []

    def tracked_monotonic() -> float:
        value = time.monotonic()
        monotonic_calls.append(value)
        return value

    started = time.monotonic()
    try:
        with pytest.raises(BackupBusyError):
            SQLiteBackupEngine(
                busy_timeout_seconds=0.12,
                retry_interval_seconds=0.02,
                pages_per_step=1,
                monotonic=tracked_monotonic,
            ).create_snapshot(paths.database, tmp_path / "busy.sqlite")
    finally:
        blocker.rollback()
        blocker.close()
    elapsed = time.monotonic() - started
    # The SQLite C API owns the retry loop and its progress-callback cadence is
    # not a Python-level contract. Two BUSY callbacks prove that a retry
    # occurred and that this engine's bounded-timeout path raised the error.
    assert len(monotonic_calls) >= 2
    assert elapsed >= 0.10
    assert elapsed < 1.0
    assert not (tmp_path / "busy.sqlite").exists()


def test_busy_timeout_restarts_after_detected_progress(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    real_connect = sqlite3.connect
    clock_values = iter((0.0, 0.9, 5.0, 5.9))

    class ScriptedBackupConnection(sqlite3.Connection):
        def backup(self, target, *, pages, progress, sleep):
            progress(sqlite3.SQLITE_BUSY, 2, 2)
            progress(sqlite3.SQLITE_BUSY, 2, 2)
            progress(sqlite3.SQLITE_OK, 1, 2)
            progress(sqlite3.SQLITE_BUSY, 1, 2)
            progress(sqlite3.SQLITE_BUSY, 1, 2)
            target.execute("CREATE TABLE copied_after_two_busy_phases (value TEXT)")
            target.commit()
            progress(sqlite3.SQLITE_DONE, 0, 2)

    scripted_source = real_connect(":memory:", factory=ScriptedBackupConnection)
    source_uri_prefix = paths.database.resolve().as_uri()

    def connect(database, *args, **kwargs):
        if kwargs.get("uri") and str(database).startswith(source_uri_prefix):
            return scripted_source
        return real_connect(database, *args, **kwargs)

    with mock.patch("src.core.backup.sqlite3.connect", side_effect=connect):
        SQLiteBackupEngine(
            busy_timeout_seconds=1.0,
            retry_interval_seconds=0.01,
            monotonic=lambda: next(clock_values),
        ).create_snapshot(paths.database, tmp_path / "phases.sqlite")
    with sqlite3.connect(tmp_path / "phases.sqlite") as snapshot:
        assert snapshot.execute(
            "SELECT name FROM sqlite_master WHERE name = 'copied_after_two_busy_phases'"
        ).fetchone()


def test_wal_mode_is_captured_without_copying_wal_files(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    connection = sqlite3.connect(paths.database)
    journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
    connection.execute(
        "INSERT INTO groups (group_id, group_name, sort_order, active) "
        "VALUES ('GRP-WAL001', ?, 0, 1)",
        ("included" * 10_000,),
    )
    connection.commit()
    wal_path = Path(f"{paths.database}-wal")
    assert journal_mode.lower() == "wal"
    assert wal_path.is_file()
    assert wal_path.stat().st_size > 0
    try:
        result = _create(paths)
    finally:
        connection.close()
    payload = _zip_payload(result.path)
    database_copy = tmp_path / "wal-copy.sqlite"
    database_copy.write_bytes(payload["database/kompetenzmanager.sqlite"])
    with sqlite3.connect(database_copy) as snapshot:
        assert snapshot.execute(
            "SELECT group_name FROM groups WHERE group_id = 'GRP-WAL001'"
        ).fetchone()[0] == ("included" * 10_000)
    assert not any(name.endswith(("-wal", "-shm")) for name in payload)


def test_snapshot_integrity_check_is_successful(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    result = _create(paths)
    verification = BackupApplicationService().verify(VerifyBackupQuery(result.path))
    assert verification.manifest.database.sha256 == result.manifest.database.sha256


def test_snapshot_foreign_key_check_is_successful(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    result = _create(paths)
    assert result.verification.manifest.counts.observations == 1


def test_backup_rejects_newer_sqlite_user_version_without_changing_live_database(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA user_version = 37")
    with pytest.raises(UnsupportedDatabaseVersionError):
        _create(paths)
    with sqlite3.connect(paths.database) as connection:
        live_user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert live_user_version == 37
    assert not tuple(paths.backups.iterdir())


def test_backup_rejects_v3_without_mutation_or_artifact(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA user_version = 3")
    before = paths.database.read_bytes()

    with pytest.raises(UnknownDatabaseSchemaError):
        _create(paths)

    assert paths.database.read_bytes() == before
    assert not tuple(paths.backups.iterdir())


def test_backup_rejects_unknown_unversioned_schema_without_claiming_v1(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    with sqlite3.connect(paths.database) as connection:
        connection.execute("CREATE TABLE unknown_extension (value TEXT)")
        connection.execute("PRAGMA user_version = 0")
    with pytest.raises(UnknownDatabaseSchemaError):
        _create(paths)
    assert not tuple(paths.backups.iterdir())


def test_schema_fingerprint_is_stable_for_identical_schema(tmp_path: Path) -> None:
    database = tmp_path / "stable.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE items (item_id TEXT PRIMARY KEY, status INTEGER NOT NULL);"
            "CREATE INDEX idx_items_active ON items(item_id) WHERE status = 1;"
        )
    first = SQLiteBackupEngine.schema_fingerprint(database)
    second = SQLiteBackupEngine.schema_fingerprint(database)
    assert first == second


def test_schema_fingerprint_structure_excludes_sqlite_internal_index_names(
    tmp_path: Path,
) -> None:
    import src.core.backup as backup_module

    database = tmp_path / "internal-index.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE items (item_id TEXT PRIMARY KEY, code TEXT UNIQUE);"
            "CREATE INDEX idx_items_code ON items(code);"
        )
        structure = backup_module._schema_structure(connection)
    canonical = json.dumps(structure, sort_keys=True)
    assert "sqlite_autoindex" not in canonical
    assert "idx_items_code" in canonical


def test_partial_index_predicate_changes_schema_fingerprint(tmp_path: Path) -> None:
    fingerprints: list[str] = []
    for value in (1, 2):
        database = tmp_path / f"predicate-{value}.sqlite"
        with sqlite3.connect(database) as connection:
            connection.executescript(
                "CREATE TABLE items (item_id TEXT PRIMARY KEY, status INTEGER NOT NULL);"
                "CREATE INDEX idx_items_status ON items(item_id) "
                f"WHERE status = {value};"
            )
        fingerprints.append(SQLiteBackupEngine.schema_fingerprint(database))
    assert fingerprints[0] != fingerprints[1]


@pytest.mark.parametrize(
    ("index_name", "table_name", "changed_predicate"),
    (
        (
            "idx_learning_report_current_revision",
            "learning_report_revisions",
            "status = 'draft'",
        ),
        (
            "idx_learning_conference_current_revision",
            "learning_conference_revisions",
            "status = 'draft'",
        ),
    ),
)
def test_existing_report_and_conference_partial_indexes_affect_fingerprint(
    tmp_path: Path,
    index_name: str,
    table_name: str,
    changed_predicate: str,
) -> None:
    paths = _runtime(tmp_path)
    before = SQLiteBackupEngine.schema_fingerprint(paths.database)
    with sqlite3.connect(paths.database) as connection:
        sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            (index_name,),
        ).fetchone()
        assert sql is not None and "WHERE" in sql[0].upper()
        key_column = (
            "learning_report_id"
            if table_name == "learning_report_revisions"
            else "learning_conference_id"
        )
        connection.execute(f'DROP INDEX "{index_name}"')
        connection.execute(
            f'CREATE UNIQUE INDEX "{index_name}" ON "{table_name}"("{key_column}") '
            f"WHERE {changed_predicate}"
        )
    after = SQLiteBackupEngine.schema_fingerprint(paths.database)
    assert after != before


def test_schema_fingerprint_matches_database_created_by_second_sqlite_version(
    tmp_path: Path,
) -> None:
    sqlite_cli = shutil.which("sqlite3")
    if sqlite_cli is None:
        pytest.skip("Keine zweite lokale SQLite-Laufzeit verfuegbar.")
    python_database = tmp_path / "python-sqlite.sqlite"
    cli_database = tmp_path / "cli-sqlite.sqlite"
    schema_sql = (
        "CREATE TABLE items (item_id TEXT PRIMARY KEY, status INTEGER NOT NULL);"
        "CREATE INDEX idx_items_status ON items(item_id) WHERE status = 1;"
    )
    with sqlite3.connect(python_database) as connection:
        connection.executescript(schema_sql)
    subprocess.run(
        [sqlite_cli, str(cli_database), schema_sql],
        check=True,
        capture_output=True,
        text=True,
    )
    assert SQLiteBackupEngine.schema_fingerprint(python_database) == (
        SQLiteBackupEngine.schema_fingerprint(cli_database)
    )


def test_active_registered_document_is_included(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000001", b"active", active=True)
    result = _create(paths)
    assert _zip_payload(result.path)["files/MED-000001.txt"] == b"active"


def test_inactive_registered_document_is_included(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000002", b"inactive", active=False)
    result = _create(paths)
    assert _zip_payload(result.path)["files/MED-000002.txt"] == b"inactive"


def test_final_report_pdf_is_byte_identical(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    report_path, _conference_path = _add_final_pdfs(paths)
    result = _create(paths)
    assert _zip_payload(result.path)["files/RPA-000001.pdf"] == report_path.read_bytes()


def test_final_conference_pdf_is_byte_identical(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _report_path, conference_path = _add_final_pdfs(paths)
    result = _create(paths)
    assert _zip_payload(result.path)["files/LCA-000001.pdf"] == conference_path.read_bytes()


def test_stored_pdf_hashes_are_checked(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    report_path, _conference_path = _add_final_pdfs(paths)
    report_path.write_bytes(b"%PDF-1.4\nfinam-report\n%%EOF")
    with pytest.raises(BackupIntegrityError, match="PDF-Hash"):
        _create(paths)


def test_external_references_are_not_copied(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    external = tmp_path / "external" / "Personenname.txt"
    _add_document(paths, "MED-000003", b"external", external_path=external)
    result = _create(paths)
    assert not any(name.startswith("files/") for name in _zip_payload(result.path))


def test_external_references_appear_only_as_counts(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    external = tmp_path / "private" / "Klara-Geheim.txt"
    _add_document(paths, "MED-000004", b"external", external_path=external)
    result = _create(paths)
    manifest_bytes = _zip_payload(result.path)["manifest.json"]
    assert result.manifest.external_references.count == 1
    assert str(external).encode() not in manifest_bytes
    assert b"Klara-Geheim" not in manifest_bytes


def test_missing_external_reference_produces_warning(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    missing = tmp_path / "external" / "missing.txt"
    _add_document(paths, "MED-000005", b"", external_path=missing)
    result = _create(paths)
    assert result.manifest.external_references.missing_count == 1
    assert result.warnings


def test_missing_managed_file_aborts(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    document = _add_document(paths, "MED-000006", b"managed")
    document.unlink()
    with pytest.raises(BackupIntegrityError, match="fehlt"):
        _create(paths)


def test_file_changed_during_real_streaming_aborts(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    document = _add_document(paths, "MED-000007", b"a" * (16 * 1024 * 1024))
    first_chunk_read = threading.Event()
    mutation_finished = threading.Event()
    real_fdopen = os.fdopen

    class SignallingSource:
        def __init__(self, source) -> None:
            self._source = source

        def __enter__(self):
            self._source.__enter__()
            return self

        def __exit__(self, *args) -> None:
            self._source.__exit__(*args)

        def read(self, size: int) -> bytes:
            chunk = self._source.read(size)
            if chunk and not first_chunk_read.is_set():
                first_chunk_read.set()
                mutation_finished.wait(timeout=5)
            return chunk

        def __getattr__(self, name: str):
            return getattr(self._source, name)

    def open_source(descriptor: int, mode: str, *args, **kwargs):
        source = real_fdopen(descriptor, mode, *args, **kwargs)
        if mode == "rb":
            return SignallingSource(source)
        return source

    def replace_after_first_chunk() -> None:
        if not first_chunk_read.wait(timeout=5):
            return
        replacement = document.with_suffix(".replacement")
        replacement.write_bytes(b"b" * (16 * 1024 * 1024))
        os.replace(replacement, document)
        mutation_finished.set()

    thread = threading.Thread(target=replace_after_first_chunk)
    thread.start()
    try:
        with mock.patch("src.core.backup.os.fdopen", side_effect=open_source):
            with pytest.raises(BackupIntegrityError, match="veraendert oder ersetzt"):
                _create(paths)
    finally:
        thread.join(timeout=5)
    assert mutation_finished.is_set()
    assert not tuple(paths.backups.iterdir())


def test_unregistered_file_in_documents_aborts(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    unknown = paths.documents / "unknown.txt"
    unknown.write_text("unknown", encoding="utf-8")
    with pytest.raises(BackupIntegrityError, match="Unregistrierte Datei"):
        _create(paths)


def test_ds_store_is_ignored(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    (paths.documents / ".DS_Store").write_bytes(b"finder")
    result = _create(paths)
    assert result.path.is_file()


def test_symlink_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    (paths.documents / "link.txt").symlink_to(target)
    with pytest.raises(BackupIntegrityError, match="Symlink"):
        _create(paths)


def test_registered_end_component_symlink_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    document = _add_document(paths, "MED-000009", b"managed")
    external = tmp_path / "external-secret.txt"
    external.write_bytes(b"external-secret")
    document.unlink()
    document.symlink_to(external)
    with pytest.raises(BackupIntegrityError, match="Symlink"):
        _create(paths)
    assert not tuple(paths.backups.iterdir())


def test_registered_file_below_existing_parent_symlink_is_rejected(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    external_directory = tmp_path / "external-parent"
    external_directory.mkdir()
    parent_link = paths.documents / "STU-000001"
    parent_link.symlink_to(external_directory, target_is_directory=True)
    _add_document(
        paths,
        "MED-000010",
        b"external-through-parent",
        external_path=parent_link / "MED-000010.txt",
    )
    with pytest.raises(BackupIntegrityError, match="Symlink"):
        _create(paths)
    assert not tuple(paths.backups.iterdir())


def test_parent_directory_swapped_to_symlink_after_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    document = _add_document(paths, "MED-000011", b"managed-original")
    parent = document.parent
    parked_parent = paths.documents / "parked-original"
    external_parent = tmp_path / "external-race"
    external_parent.mkdir()
    (external_parent / document.name).write_bytes(b"external-secret")
    real_build_inventory = BackupInventoryService.build_inventory

    def build_then_swap(service, snapshot_path):
        inventory = real_build_inventory(service, snapshot_path)
        parent.rename(parked_parent)
        parent.symlink_to(external_parent, target_is_directory=True)
        return inventory

    with mock.patch.object(
        BackupInventoryService,
        "build_inventory",
        new=build_then_swap,
    ):
        with pytest.raises(BackupIntegrityError, match="Symlink-Folgen"):
            _create(paths)
    assert not tuple(paths.backups.iterdir())
    assert b"external-secret" not in b"".join(
        path.read_bytes() for path in paths.backups.glob("*.jkmbackup")
    )


def test_same_size_and_mtime_inode_replacement_after_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    document = _add_document(paths, "MED-000012", b"original-bytes")
    original_stat = document.stat()
    original_inode = original_stat.st_ino
    real_build_inventory = BackupInventoryService.build_inventory

    def build_then_replace(service, snapshot_path):
        inventory = real_build_inventory(service, snapshot_path)
        replacement = document.with_suffix(".replacement")
        replacement.write_bytes(b"replaced-bytes")
        os.utime(
            replacement,
            ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
        )
        os.replace(replacement, document)
        assert document.stat().st_ino != original_inode
        assert document.stat().st_size == original_stat.st_size
        assert document.stat().st_mtime_ns == original_stat.st_mtime_ns
        return inventory

    with mock.patch.object(
        BackupInventoryService,
        "build_inventory",
        new=build_then_replace,
    ):
        with pytest.raises(BackupIntegrityError, match="Inventarisierung ersetzt"):
            _create(paths)
    assert not tuple(paths.backups.iterdir())


def test_manifest_is_deterministic_with_fixed_time(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    first = _create(paths, target=tmp_path / "first")
    second = _create(paths, target=tmp_path / "second")
    assert _zip_payload(first.path)["manifest.json"] == _zip_payload(second.path)[
        "manifest.json"
    ]


def test_manifest_excludes_personal_text_and_absolute_paths(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000013", b"managed")
    _add_final_pdfs(paths)
    result = _create(paths)
    manifest_bytes = _zip_payload(result.path)["manifest.json"]
    for forbidden in (
        "Fiktiv",
        "Kind",
        "Geheime Notiz",
        "Lehrkraft",
        "Personenname-Geheim.txt",
        "MED-000013_Originalname.txt",
        str(paths.root),
        str(paths.documents),
    ):
        assert forbidden.encode("utf-8") not in manifest_bytes


@pytest.mark.parametrize(
    ("app_version", "build_commit", "source_tree_state"),
    (
        ("/Users/person/private", "82df25df150e1", "clean"),
        ("0.1.2", "/tmp/private", "clean"),
        ("0.1.2 Laura", "82df25df150e1", "clean"),
        ("0.1.2", "82df25df150e1", "Laura arbeitet hier"),
    ),
)
def test_free_text_build_metadata_is_rejected_before_backup(
    tmp_path: Path,
    app_version: str,
    build_commit: str,
    source_tree_state: str,
) -> None:
    paths = _runtime(tmp_path)
    command = CreateBackupCommand(
        database_path=paths.database,
        runtime_paths=paths,
        target_path=paths.backups,
        app_version=app_version,
        build_commit=build_commit,
        source_tree_state=source_tree_state,
    )
    with pytest.raises(BackupValidationError):
        BackupApplicationService(now=lambda: FIXED_NOW).create(command)
    assert not tuple(paths.backups.iterdir())


def test_database_hash_matches_archived_bytes(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    result = _create(paths)
    database_bytes = _zip_payload(result.path)["database/kompetenzmanager.sqlite"]
    assert hashlib.sha256(database_bytes).hexdigest() == result.manifest.database.sha256


def test_managed_file_hash_matches_archived_bytes(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000008", b"hash me")
    result = _create(paths)
    archived = _zip_payload(result.path)["files/MED-000008.txt"]
    assert hashlib.sha256(archived).hexdigest() == result.manifest.managed_files[0].sha256


def test_corrupted_zip_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.jkmbackup"
    path.write_bytes(b"not a zip")
    with pytest.raises(BackupFormatError, match="ZIP"):
        BackupVerifier().verify_backup(path)


def test_wrong_format_version_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    result = _create(paths)
    _modified_manifest(
        result.path,
        lambda manifest: manifest.__setitem__(
            "backup_format_version", BACKUP_FORMAT_VERSION + 1
        ),
    )
    with pytest.raises(BackupFormatError, match="Formatversion"):
        BackupVerifier().verify_backup(result.path)


def test_manifest_build_metadata_with_path_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    result = _create(paths)
    _modified_manifest(
        result.path,
        lambda manifest: manifest.__setitem__("build_commit", "/Users/private"),
    )
    with pytest.raises(BackupFormatError, match="build_commit"):
        BackupVerifier().verify_backup(result.path)


def test_zip_slip_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "zip-slip.jkmbackup"
    _rewrite_zip(path, [("../outside", b"bad"), ("manifest.json", b"{}")])
    with pytest.raises(BackupFormatError, match="Archivpfad"):
        BackupVerifier().verify_backup(path)


def test_duplicate_archive_path_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.jkmbackup"
    _rewrite_zip(path, [("manifest.json", b"{}"), ("manifest.json", b"{}")])
    with pytest.raises(BackupFormatError, match="Doppelter Archivpfad"):
        BackupVerifier().verify_backup(path)


def test_zip_symlink_entry_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "symlink-entry.jkmbackup"
    symlink_info = zipfile.ZipInfo("files/MED-1.bin")
    symlink_info.create_system = 3
    symlink_info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", b"{}")
        archive.writestr(symlink_info, b"../../external")
    with pytest.raises(BackupFormatError, match="Symlink oder Sonderdatei"):
        BackupVerifier().verify_backup(path)


@pytest.mark.parametrize(
    ("first", "second"),
    (
        ("files/\u00e9.bin", "files/e\u0301.bin"),
        ("files/Record.bin", "files/record.bin"),
    ),
)
def test_unicode_nfd_and_casefold_archive_collisions_are_rejected(
    tmp_path: Path,
    first: str,
    second: str,
) -> None:
    path = tmp_path / "unicode-collision.jkmbackup"
    _rewrite_zip(
        path,
        [("manifest.json", b"{}"), (first, b"one"), (second, b"two")],
    )
    with pytest.raises(BackupFormatError, match="macOS kollidierender"):
        BackupVerifier().verify_backup(path)


def test_size_limit_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "large.jkmbackup"
    _rewrite_zip(path, [("manifest.json", b"{}"), ("files/MED-1.bin", b"12345")])
    with pytest.raises(BackupFormatError, match="Groessenlimit"):
        BackupVerifier(max_member_size_bytes=4).verify_backup(path)


def test_total_uncompressed_size_limit_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "total-large.jkmbackup"
    _rewrite_zip(
        path,
        [("manifest.json", b"{}"), ("files/A.bin", b"1234"), ("files/B.bin", b"5678")],
    )
    with pytest.raises(BackupFormatError, match="Gesamtgroessenlimit"):
        BackupVerifier(max_total_size_bytes=7).verify_backup(path)


def test_streaming_limit_rejects_highly_compressed_payload(tmp_path: Path) -> None:
    path = tmp_path / "compressed-bomb.jkmbackup"
    _rewrite_zip(
        path,
        [("manifest.json", b"{}"), ("files/A.bin", b"0" * (2 * 1024 * 1024))],
    )

    class StreamingLimitVerifier(BackupVerifier):
        def _validate_members(self, infos):
            configured_limit = self.max_total_size_bytes
            self.max_total_size_bytes = 10 * 1024 * 1024
            try:
                super()._validate_members(infos)
            finally:
                self.max_total_size_bytes = configured_limit

    with pytest.raises(BackupFormatError, match="beim Entpacken"):
        StreamingLimitVerifier(
            max_total_size_bytes=1024 * 1024,
            max_member_size_bytes=4 * 1024 * 1024,
        ).verify_backup(path)


def test_incomplete_target_is_removed_after_failure(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    report_path, _conference_path = _add_final_pdfs(paths)
    report_path.write_bytes(b"%PDF-1.4\nchanged\n%%EOF")
    with pytest.raises(BackupIntegrityError):
        _create(paths)
    assert not tuple(paths.backups.iterdir())


def test_cleanup_and_live_data_after_failure_immediately_after_zip_close(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000014", b"managed")
    before = _live_state(paths)
    real_write_archive = BackupService._write_archive

    def write_then_fail(*args, **kwargs):
        real_write_archive(*args, **kwargs)
        raise BackupFileError("simulierter Fehler nach ZIP-Schliessen")

    with mock.patch.object(
        BackupService,
        "_write_archive",
        side_effect=write_then_fail,
    ):
        with pytest.raises(BackupFileError, match="ZIP-Schliessen"):
            _create(paths)
    assert _live_state(paths) == before
    assert not tuple(paths.backups.iterdir())
    _assert_no_own_backup_artifacts(paths.backups)


def test_cleanup_and_live_data_after_verifier_failure(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000015", b"managed")
    before = _live_state(paths)

    class RejectingVerifier(BackupVerifier):
        def verify_backup(self, path):
            raise BackupIntegrityError("simulierter Verifier-Fehler")

    with pytest.raises(BackupIntegrityError, match="Verifier-Fehler"):
        _create(paths, verifier=RejectingVerifier())
    assert _live_state(paths) == before
    assert not tuple(paths.backups.iterdir())
    _assert_no_own_backup_artifacts(paths.backups)


def test_cleanup_and_live_data_after_fsync_failure(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000016", b"managed")
    before = _live_state(paths)
    with mock.patch.object(
        BackupService,
        "_fsync_file",
        side_effect=BackupFileError("simulierter fsync-Fehler"),
    ):
        with pytest.raises(BackupFileError, match="fsync-Fehler"):
            _create(paths)
    assert _live_state(paths) == before
    assert not tuple(paths.backups.iterdir())
    _assert_no_own_backup_artifacts(paths.backups)


def test_publish_race_keeps_foreign_backup_byte_identical(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000017", b"managed")
    before = _live_state(paths)
    foreign_bytes = b"backup-created-by-another-process"
    final_path = (
        paths.backups
        / "Jenaplan-Kompetenzmanager-Backup-20260716T123456Z.jkmbackup"
    )

    def lose_publish_race(_temporary, final):
        Path(final).write_bytes(foreign_bytes)
        raise OSError("simulierter konkurrierender Publish")

    with mock.patch("src.core.backup.os.link", side_effect=lose_publish_race):
        with pytest.raises(BackupFileError, match="atomar veroeffentlicht"):
            _create(paths)
    assert final_path.read_bytes() == foreign_bytes
    assert _live_state(paths) == before
    assert tuple(paths.backups.iterdir()) == (final_path,)
    _assert_no_own_backup_artifacts(paths.backups)


def test_cleanup_and_live_data_after_publish_failure_without_winner(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_document(paths, "MED-000018", b"managed")
    before = _live_state(paths)
    with mock.patch(
        "src.core.backup.os.link",
        side_effect=OSError("simulierter Publish-Fehler"),
    ):
        with pytest.raises(BackupFileError, match="atomar veroeffentlicht"):
            _create(paths)
    assert _live_state(paths) == before
    assert not tuple(paths.backups.iterdir())
    _assert_no_own_backup_artifacts(paths.backups)


def test_existing_backup_is_never_overwritten(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    first = _create(paths)
    original = first.path.read_bytes()
    with pytest.raises(BackupFileError, match="existiert bereits"):
        _create(paths)
    assert first.path.read_bytes() == original


def test_counts_match_snapshot(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_final_pdfs(paths)
    result = _create(paths)
    assert result.manifest.counts.to_dict() == {
        "students": 1,
        "observations": 1,
        "learning_report_revisions": 1,
        "learning_conference_revisions": 1,
    }


def test_backup_creation_does_not_change_live_data(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    with sqlite3.connect(paths.database) as connection:
        before = connection.iterdump()
        before_dump = tuple(before)
    _create(paths)
    with sqlite3.connect(paths.database) as connection:
        after_dump = tuple(connection.iterdump())
    assert after_dump == before_dump


def test_report_and_conference_snapshot_hashes_remain_unchanged(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_base_data(paths)
    _add_final_pdfs(paths)
    with sqlite3.connect(paths.database) as connection:
        before = (
            connection.execute(
                "SELECT snapshot_sha256 FROM learning_report_revisions"
            ).fetchall(),
            connection.execute(
                "SELECT snapshot_sha256 FROM learning_conference_revisions"
            ).fetchall(),
        )
    _create(paths)
    with sqlite3.connect(paths.database) as connection:
        after = (
            connection.execute(
                "SELECT snapshot_sha256 FROM learning_report_revisions"
            ).fetchall(),
            connection.execute(
                "SELECT snapshot_sha256 FROM learning_conference_revisions"
            ).fetchall(),
        )
    assert after == before
