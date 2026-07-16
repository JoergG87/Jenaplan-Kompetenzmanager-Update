"""Focused tests for isolated restore-backup verification and preview."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.application.commands.backup import BackupApplicationService, CreateBackupCommand
from src.application.commands.restore import (
    RestoreApplicationService,
    VerifyRestoreBackupQuery,
)
from src.core.backup import SQLiteBackupEngine
from src.core.database_compatibility import DatabaseCompatibilityStatus
from src.core.restore import (
    RestoreCompatibilityError,
    RestoreError,
    RestoreFormatError,
    RestoreIntegrityError,
    RestoreVerifier,
)
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.runtime import RuntimePaths, runtime_paths


FIXED_NOW = datetime(2026, 7, 16, 15, 0, 0, tzinfo=UTC)


def _runtime(tmp_path: Path) -> RuntimePaths:
    paths = runtime_paths(tmp_path / "live")
    for directory in (
        paths.root,
        paths.documents,
        paths.exports,
        paths.backups,
        paths.logs,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    SQLiteDatabase(paths.database).initialize_schema()
    return paths


def _insert_personal_data(paths: RuntimePaths, *, managed_file: bool = False) -> None:
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO groups VALUES ('GRP-000001', 'Geheime Gruppe', 0, 1)"
        )
        connection.execute(
            "INSERT INTO courses "
            "(course_id, course_name, color_key, color_name, color_hex, sort_order, active) "
            "VALUES ('CRS-000001', 'Geheimer Kurs', NULL, 'Blau', '#0000ff', 0, 1)"
        )
        connection.execute(
            "INSERT INTO students VALUES "
            "('STU-000001', 'Klara', 'Geheim', 'GRP-000001', 'CRS-000001', "
            "'Private Notiz', 1, '2026-01-01', '2026-01-01', NULL)"
        )
        connection.execute(
            "INSERT INTO observations VALUES "
            "('OBS-000001', 'STU-000001', '2026-01-02', 'MAT', "
            "'Privater Kontext', 'Geheimer Beobachtungstext', 1, "
            "'2026-01-02', '2026-01-02')"
        )
        if managed_file:
            document = paths.documents / "STU-000001" / "MED-000001_Kindname.txt"
            document.parent.mkdir(parents=True)
            document.write_bytes(b"private managed bytes")
            connection.execute(
                "INSERT INTO documents "
                "(document_id, student_id, observation_id, title, document_type, "
                "file_path, original_filename, created_at, note, active) "
                "VALUES ('MED-000001', 'STU-000001', NULL, 'Privater Titel', "
                "'Sonstiges', ?, 'Kindname-Geheim.txt', '2026-01-03', "
                "'Private Dokumentnotiz', 1)",
                (str(document),),
            )


def _create_backup(paths: RuntimePaths) -> Path:
    result = BackupApplicationService(now=lambda: FIXED_NOW).create(
        CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version="0.1.2",
            build_commit="c029aff",
            source_tree_state="clean",
        )
    )
    return result.path


def _zip_payload(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def _rewrite_zip(path: Path, payload: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in payload.items():
            archive.writestr(name, content)


def _canonical_manifest(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _mutate_archived_database(
    backup_path: Path,
    tmp_path: Path,
    mutate,
    *,
    update_counts: bool = False,
) -> None:
    payload = _zip_payload(backup_path)
    database = tmp_path / "candidate.sqlite"
    database.write_bytes(payload["database/kompetenzmanager.sqlite"])
    with sqlite3.connect(database) as connection:
        mutate(connection)
        connection.commit()
    database_bytes = database.read_bytes()
    manifest = json.loads(payload["manifest.json"])
    manifest["database"]["size_bytes"] = len(database_bytes)
    manifest["database"]["sha256"] = hashlib.sha256(database_bytes).hexdigest()
    manifest["database"]["schema_fingerprint"] = (
        SQLiteBackupEngine.schema_fingerprint(database)
    )
    with sqlite3.connect(database) as connection:
        manifest["database"]["sqlite_user_version"] = int(
            connection.execute("PRAGMA user_version").fetchone()[0]
        )
        if update_counts:
            for manifest_name, table in (
                ("students", "students"),
                ("observations", "observations"),
                ("learning_report_revisions", "learning_report_revisions"),
                (
                    "learning_conference_revisions",
                    "learning_conference_revisions",
                ),
            ):
                manifest["counts"][manifest_name] = int(
                    connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                )
    payload["database/kompetenzmanager.sqlite"] = database_bytes
    payload["manifest.json"] = _canonical_manifest(manifest)
    _rewrite_zip(backup_path, payload)


def _live_state(paths: RuntimePaths) -> tuple[bytes, tuple[tuple[str, bytes], ...]]:
    files = tuple(
        sorted(
            (path.relative_to(paths.documents).as_posix(), path.read_bytes())
            for path in paths.documents.rglob("*")
            if path.is_file()
        )
    )
    return paths.database.read_bytes(), files


def test_valid_v1_backup_produces_exact_preview(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths)
    backup = _create_backup(paths)
    result = RestoreVerifier().verify(backup)
    assert result.compatibility.status is DatabaseCompatibilityStatus.EXACT
    assert result.preview.compatibility_status is DatabaseCompatibilityStatus.EXACT
    assert result.preview.sqlite_user_version == 1
    assert result.preview.students_count == 1
    assert result.preview.observations_count == 1


def test_known_v0_backup_is_migration_required_and_old_format_remains_verifiable(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA user_version = 0")
    backup = _create_backup(paths)
    result = RestoreApplicationService().verify(VerifyRestoreBackupQuery(backup))
    assert result.compatibility.status is (
        DatabaseCompatibilityStatus.MIGRATION_REQUIRED
    )
    assert result.preview.sqlite_user_version == 0
    assert result.preview.database_compatibility_version == 1


def test_manipulated_manifest_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    payload = _zip_payload(backup)
    manifest = json.loads(payload["manifest.json"])
    manifest["app_version"] = "/Users/private"
    payload["manifest.json"] = _canonical_manifest(manifest)
    _rewrite_zip(backup, payload)
    with pytest.raises(RestoreFormatError):
        RestoreVerifier().verify(backup)


def test_manifest_and_database_version_mismatch_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    payload = _zip_payload(backup)
    manifest = json.loads(payload["manifest.json"])
    manifest["database"]["sqlite_user_version"] = 0
    payload["manifest.json"] = _canonical_manifest(manifest)
    _rewrite_zip(backup, payload)
    with pytest.raises(RestoreIntegrityError, match="user_version"):
        RestoreVerifier().verify(backup)


def test_unknown_fingerprint_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    _mutate_archived_database(
        backup,
        tmp_path,
        lambda connection: connection.execute(
            "CREATE TABLE unknown_extension (value TEXT)"
        ),
    )
    with pytest.raises(RestoreCompatibilityError, match="unbekanntes Schema"):
        RestoreVerifier().verify(backup)


def test_corrupted_database_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    payload = _zip_payload(backup)
    payload["database/kompetenzmanager.sqlite"] = b"not a sqlite database"
    manifest = json.loads(payload["manifest.json"])
    database_bytes = payload["database/kompetenzmanager.sqlite"]
    manifest["database"]["size_bytes"] = len(database_bytes)
    manifest["database"]["sha256"] = hashlib.sha256(database_bytes).hexdigest()
    payload["manifest.json"] = _canonical_manifest(manifest)
    _rewrite_zip(backup, payload)
    with pytest.raises(RestoreIntegrityError):
        RestoreVerifier().verify(backup)


def test_foreign_key_violation_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)

    def violate(connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO observations VALUES "
            "('OBS-BROKEN', 'STU-MISSING', '2026-01-01', 'MAT', '', '', 1, "
            "'2026-01-01', '2026-01-01')"
        )

    _mutate_archived_database(
        backup,
        tmp_path,
        violate,
        update_counts=True,
    )
    with pytest.raises(RestoreIntegrityError, match="foreign_key_check"):
        RestoreVerifier().verify(backup)


def test_wrong_manifest_counts_are_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    payload = _zip_payload(backup)
    manifest = json.loads(payload["manifest.json"])
    manifest["counts"]["students"] += 1
    payload["manifest.json"] = _canonical_manifest(manifest)
    _rewrite_zip(backup, payload)
    with pytest.raises(RestoreIntegrityError, match="Counts"):
        RestoreVerifier().verify(backup)


def test_missing_managed_file_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    payload = _zip_payload(backup)
    del payload["files/MED-000001.txt"]
    _rewrite_zip(backup, payload)
    with pytest.raises(RestoreFormatError, match="Nutzdateien"):
        RestoreVerifier().verify(backup)


def test_preview_contains_no_personal_content_or_paths(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    preview = RestoreVerifier().verify(backup).preview
    serialized = json.dumps(asdict(preview), default=str, ensure_ascii=False)
    for forbidden in (
        "Klara",
        "Geheim",
        "Private Notiz",
        "Beobachtungstext",
        "Kindname",
        "MED-000001",
        str(paths.root),
        str(paths.documents),
    ):
        assert forbidden not in serialized
    assert set(asdict(preview)) == {
        "created_at",
        "app_version",
        "backup_format_version",
        "database_compatibility_version",
        "sqlite_user_version",
        "compatibility_status",
        "students_count",
        "observations_count",
        "learning_report_revisions_count",
        "learning_conference_revisions_count",
        "managed_files_count",
        "external_references_count",
        "external_missing_count",
    }


def test_temporary_files_are_removed_after_success_and_error(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    temporary_root = tmp_path / "temporary"
    temporary_root.mkdir()
    verifier = RestoreVerifier(temporary_root=temporary_root)
    verifier.verify(backup)
    assert not tuple(temporary_root.iterdir())

    _mutate_archived_database(
        backup,
        tmp_path,
        lambda connection: connection.execute(
            "CREATE TABLE unknown_after_success (value TEXT)"
        ),
    )
    with pytest.raises(RestoreError):
        verifier.verify(backup)
    assert not tuple(temporary_root.iterdir())


def test_restore_verification_never_changes_live_data(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    before = _live_state(paths)
    RestoreVerifier().verify(backup)
    assert _live_state(paths) == before
