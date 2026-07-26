"""Focused tests for isolated restore-backup verification and preview."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest

from src.application.commands.backup import BackupApplicationService, CreateBackupCommand
from src.application.commands.restore import (
    CleanupRestoreStagingCommand,
    CreateRestoreSafetyBackupCommand,
    PrepareRestoreStagingCommand,
    RestoreApplicationService,
    VerifyPreparedRestoreQuery,
    VerifyRestoreBackupQuery,
)
from src.core.backup import SQLiteBackupEngine
from src.core.database_compatibility import DatabaseCompatibilityStatus
from src.core.persistence_events import SQLitePersistenceEventRepository
from src.core.restore import (
    RestoreCompatibilityError,
    RestoreError,
    RestoreFormatError,
    RestoreIntegrityError,
    RestoreMigrationError,
    RestoreMaterializationError,
    RestoreStagingError,
    RestoreStagingService,
    RestoreStateError,
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


def _set_v1_schema(paths: RuntimePaths, *, user_version: int = 1) -> None:
    with sqlite3.connect(paths.database) as connection:
        connection.execute("DROP TABLE persistence_events")
        connection.execute(f"PRAGMA user_version = {user_version}")


def _insert_historical_freshness_tie(paths: RuntimePaths) -> None:
    with sqlite3.connect(paths.database) as connection:
        connection.execute(
            """
            INSERT INTO competencies (
                competency_id, subject_id, subject_name, subject_full_name,
                official_subject_name, school_context_name, grade_band, label,
                description, learning_stage, learning_area, competency_group,
                source_reference, catalog_status, activation_group_key,
                sort_order, active, catalog_default_active, is_core_subject
            ) VALUES (
                'CMP-RESTORE-001', 'MAT', 'Mathematik', '', '', '', '',
                'Zahlen', 'Zahlen', 'cross_stage', 'Zahlen', 'Grundlagen',
                '', 'current', '', 0, 1, 1, 1
            )
            """
        )
        connection.execute(
            """
            INSERT INTO observation_competency_ratings (
                observation_id, competency_id, subject_id, subject_display_name,
                learning_area, competency_group, competency_text, rating
            ) VALUES (
                'OBS-000001', 'CMP-RESTORE-001', 'MAT', 'Mathematik',
                'Zahlen', 'Grundlagen', 'Zahlen', '+'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO student_competency_confirmations (
                student_id, competency_id, confirmed_rating, confirmed_at, note
            ) VALUES (
                'STU-000001', 'CMP-RESTORE-001', '+',
                '2026-01-02T00:00:00+00:00', ''
            )
            """
        )


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


def _user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _add_external_document(paths: RuntimePaths, external_path: Path) -> None:
    external_path.parent.mkdir(parents=True, exist_ok=True)
    external_path.write_bytes(b"external bytes")
    with sqlite3.connect(paths.database) as connection:
        connection.execute(
            "INSERT INTO documents "
            "(document_id, student_id, observation_id, title, document_type, "
            "file_path, original_filename, created_at, note, active) "
            "VALUES ('MED-EXT001', 'STU-000001', NULL, 'Extern', 'Sonstiges', "
            "?, 'extern.txt', '2026-01-03', '', 1)",
            (str(external_path),),
        )


def _add_final_pdfs(paths: RuntimePaths) -> tuple[Path, Path]:
    report_bytes = b"%PDF-1.4\nrestore-report\n%%EOF"
    conference_bytes = b"%PDF-1.4\nrestore-conference\n%%EOF"
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
    report_snapshot = hashlib.sha256(b"report snapshot").hexdigest()
    conference_snapshot = hashlib.sha256(b"conference snapshot").hexdigest()
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


def test_valid_v1_backup_produces_exact_preview(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths)
    backup = _create_backup(paths)
    result = RestoreVerifier().verify(backup)
    assert result.compatibility.status is DatabaseCompatibilityStatus.EXACT
    assert result.preview.compatibility_status is DatabaseCompatibilityStatus.EXACT
    assert result.preview.sqlite_user_version == 2
    assert result.preview.students_count == 1
    assert result.preview.observations_count == 1


def test_known_v0_backup_is_migration_required_and_old_format_remains_verifiable(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _set_v1_schema(paths, user_version=0)
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


def test_valid_v1_backup_is_prepared_with_rebased_managed_document(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    before = _live_state(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    result = service.prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-TEST-V1")
    )
    staging = paths.root / "restore-staging" / "RST-TEST-V1"
    prepared_database = staging / "prepared" / "kompetenzmanager.sqlite"
    prepared_file = (
        staging
        / "prepared"
        / "documents"
        / "managed"
        / "MED-000001"
        / "MED-000001.txt"
    )
    assert result.status == "completed"
    assert result.migrated is False
    assert _user_version(prepared_database) == 2
    assert prepared_file.read_bytes() == b"private managed bytes"
    with sqlite3.connect(prepared_database) as connection:
        rebased = connection.execute(
            "SELECT file_path FROM documents WHERE document_id = 'MED-000001'"
        ).fetchone()[0]
    assert rebased == str(
        paths.documents / "managed" / "MED-000001" / "MED-000001.txt"
    )
    state_path = staging / "staging-state.json"
    assert stat_mode(state_path) == 0o600
    state_text = state_path.read_text(encoding="utf-8")
    assert json.loads(state_text)["phase"] == "completed"
    for forbidden in ("Klara", "Geheim", "Kindname", str(paths.documents)):
        assert forbidden not in state_text
    assert _live_state(paths) == before


def test_known_v0_is_migrated_only_in_staging_and_rows_remain_identical(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    _set_v1_schema(paths, user_version=0)
    backup = _create_backup(paths)
    before = _live_state(paths)
    result = RestoreApplicationService(now=lambda: FIXED_NOW).prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-TEST-V0")
    )
    staging = paths.root / "restore-staging" / "RST-TEST-V0"
    source_database = staging / "source" / "database" / "kompetenzmanager.sqlite"
    prepared_database = staging / "prepared" / "kompetenzmanager.sqlite"
    assert result.migrated is True
    assert _user_version(source_database) == 0
    assert _user_version(prepared_database) == 2
    assert _user_version(paths.database) == 0
    with sqlite3.connect(source_database) as source, sqlite3.connect(
        prepared_database
    ) as prepared:
        source_observation = source.execute(
            "SELECT * FROM observations"
        ).fetchall()
        prepared_observation = prepared.execute(
            "SELECT * FROM observations"
        ).fetchall()
    assert source_observation == prepared_observation
    assert _live_state(paths) == before


def test_v1_backup_restore_backfills_historical_unknown_freshness(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths)
    _insert_historical_freshness_tie(paths)
    _set_v1_schema(paths, user_version=1)
    backup = _create_backup(paths)

    result = RestoreApplicationService(now=lambda: FIXED_NOW).prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-V1-EVENT-BACKFILL")
    )
    prepared_database = (
        paths.root
        / "restore-staging"
        / "RST-V1-EVENT-BACKFILL"
        / "prepared"
        / "kompetenzmanager.sqlite"
    )

    assert result.migrated is True
    assert _user_version(prepared_database) == 2
    freshness = SQLitePersistenceEventRepository(
        SQLiteDatabase(prepared_database)
    ).freshness_for_student("STU-000001")
    assert freshness["CMP-RESTORE-001"].state == "confirmation_unknown"
    with sqlite3.connect(prepared_database) as connection:
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM persistence_events
            WHERE competency_id = 'CMP-RESTORE-001'
              AND ordering_state = 'unknown'
            """
        ).fetchone()[0] == 2


def test_migration_failure_rolls_back_prepared_database_and_marks_failed(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths)
    _set_v1_schema(paths, user_version=0)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    with mock.patch(
        "src.core.restore.migrate_persistence_events",
        side_effect=sqlite3.OperationalError("simulierter Migrationsfehler"),
    ):
        with pytest.raises(RestoreMigrationError):
            service.prepare_staging(
                PrepareRestoreStagingCommand(backup, paths, "RST-FAIL-MIGRATION")
            )
    staging = paths.root / "restore-staging" / "RST-FAIL-MIGRATION"
    assert _user_version(staging / "prepared" / "kompetenzmanager.sqlite") == 0
    state = json.loads((staging / "staging-state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "failed"
    assert _user_version(paths.database) == 0


def test_external_reference_is_byte_identical_and_never_materialized(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths)
    external = tmp_path / "external" / "private.txt"
    _add_external_document(paths, external)
    backup = _create_backup(paths)
    before_external = external.read_bytes()
    RestoreApplicationService(now=lambda: FIXED_NOW).prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-EXTERNAL")
    )
    staging = paths.root / "restore-staging" / "RST-EXTERNAL"
    with sqlite3.connect(staging / "prepared" / "kompetenzmanager.sqlite") as connection:
        stored_path = connection.execute(
            "SELECT file_path FROM documents WHERE document_id = 'MED-EXT001'"
        ).fetchone()[0]
    assert stored_path == str(external)
    assert external.read_bytes() == before_external
    assert not tuple((staging / "prepared" / "documents").rglob("*"))


def test_final_report_and_conference_pdfs_keep_contract_paths_and_hashes(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths)
    report, conference = _add_final_pdfs(paths)
    backup = _create_backup(paths)
    live_before = _live_state(paths)
    RestoreApplicationService(now=lambda: FIXED_NOW).prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-PDFS")
    )
    prepared = paths.root / "restore-staging" / "RST-PDFS" / "prepared"
    prepared_report = prepared / report.relative_to(paths.root)
    prepared_conference = prepared / conference.relative_to(paths.root)
    assert prepared_report.read_bytes() == report.read_bytes()
    assert prepared_conference.read_bytes() == conference.read_bytes()
    with sqlite3.connect(prepared / "kompetenzmanager.sqlite") as connection:
        report_row = connection.execute(
            "SELECT relative_file_path, file_size_bytes, pdf_sha256 "
            "FROM learning_report_pdf_artifacts"
        ).fetchone()
        conference_row = connection.execute(
            "SELECT relative_file_path, file_size_bytes, pdf_sha256 "
            "FROM learning_conference_pdf_artifacts"
        ).fetchone()
        snapshots = (
            connection.execute(
                "SELECT snapshot_json, snapshot_sha256 FROM learning_report_revisions"
            ).fetchall(),
            connection.execute(
                "SELECT snapshot_json, snapshot_sha256 FROM learning_conference_revisions"
            ).fetchall(),
        )
    assert report_row[0] == report.relative_to(paths.root).as_posix()
    assert conference_row[0] == conference.relative_to(paths.root).as_posix()
    assert report_row[1:] == (
        len(report.read_bytes()),
        hashlib.sha256(report.read_bytes()).hexdigest(),
    )
    assert conference_row[1:] == (
        len(conference.read_bytes()),
        hashlib.sha256(conference.read_bytes()).hexdigest(),
    )
    assert snapshots[0][0][0] == "{}"
    assert snapshots[1][0][0] == "{}"
    assert _live_state(paths) == live_before


def test_archive_change_after_verification_is_detected_and_failed_state_is_kept(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)

    class MutatingRestoreVerifier(RestoreVerifier):
        def verify(self, path: Path):
            result = super().verify(path)
            with path.open("ab") as archive_file:
                archive_file.write(b"changed-after-verification")
            return result

    service = RestoreApplicationService(
        verifier=MutatingRestoreVerifier(),
        now=lambda: FIXED_NOW,
    )
    with pytest.raises(RestoreIntegrityError, match="ausgetauscht"):
        service.prepare_staging(
            PrepareRestoreStagingCommand(backup, paths, "RST-ARCHIVE-CHANGE")
        )
    staging = paths.root / "restore-staging" / "RST-ARCHIVE-CHANGE"
    state = json.loads((staging / "staging-state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "failed"


def test_restore_id_collision_repeated_verification_and_scoped_cleanup(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    command = PrepareRestoreStagingCommand(backup, paths, "RST-IDEMPOTENT")
    service.prepare_staging(command)
    with pytest.raises(RestoreStateError, match="bereits"):
        service.prepare_staging(command)
    first = service.verify_prepared(
        VerifyPreparedRestoreQuery("RST-IDEMPOTENT", paths)
    )
    second = service.verify_prepared(
        VerifyPreparedRestoreQuery("RST-IDEMPOTENT", paths)
    )
    assert first == second
    neighbor = paths.root / "restore-staging" / "RST-NEIGHBOR"
    neighbor.mkdir()
    (neighbor / "keep.txt").write_text("keep", encoding="utf-8")
    assert service.cleanup_staging(
        CleanupRestoreStagingCommand("RST-IDEMPOTENT", paths)
    )
    assert not (paths.root / "restore-staging" / "RST-IDEMPOTENT").exists()
    assert (neighbor / "keep.txt").read_text(encoding="utf-8") == "keep"
    with pytest.raises(RestoreStateError):
        service.cleanup_staging(CleanupRestoreStagingCommand("../live", paths))


def test_corrupted_prepared_file_blocks_final_verification(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    service.prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-CORRUPT-PREPARED")
    )
    prepared_file = (
        paths.root
        / "restore-staging"
        / "RST-CORRUPT-PREPARED"
        / "prepared"
        / "documents"
        / "managed"
        / "MED-000001"
        / "MED-000001.txt"
    )
    prepared_file.write_bytes(b"corrupted")
    with pytest.raises(RestoreError):
        service.verify_prepared(
            VerifyPreparedRestoreQuery("RST-CORRUPT-PREPARED", paths)
        )


def test_contradictory_canonical_staging_state_is_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    service.prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-STATE-CONFLICT")
    )
    state_path = (
        paths.root
        / "restore-staging"
        / "RST-STATE-CONFLICT"
        / "staging-state.json"
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["counts"]["students"] += 1
    state_path.write_bytes(_canonical_manifest(state))
    with pytest.raises(RestoreStateError, match="widerspricht"):
        service.verify_prepared(
            VerifyPreparedRestoreQuery("RST-STATE-CONFLICT", paths)
        )


def test_missing_space_is_rejected_before_staging_directory_is_created(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    with mock.patch(
        "src.core.restore.shutil.disk_usage",
        return_value=mock.Mock(free=0),
    ):
        with pytest.raises(RestoreStagingError, match="nicht genug Speicher"):
            service.prepare_staging(
                PrepareRestoreStagingCommand(backup, paths, "RST-NO-SPACE")
            )
    assert not (paths.root / "restore-staging" / "RST-NO-SPACE").exists()


def test_missing_staging_permissions_are_rejected_before_payload_write(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    with mock.patch(
        "src.core.restore.os.chmod",
        side_effect=PermissionError("simulierte fehlende Rechte"),
    ):
        with pytest.raises(RestoreStagingError, match="nicht sicher angelegt"):
            service.prepare_staging(
                PrepareRestoreStagingCommand(backup, paths, "RST-NO-PERMISSION")
            )
    staging = paths.root / "restore-staging" / "RST-NO-PERMISSION"
    assert not staging.exists()


def test_rebase_transaction_failure_rolls_back_and_failed_staging_can_be_cleaned(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    original_path = str(
        paths.documents / "STU-000001" / "MED-000001_Kindname.txt"
    )
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)

    def fail_after_first_update(connection, document_targets):
        document_id, target = next(iter(sorted(document_targets.items())))
        connection.execute(
            "UPDATE documents SET file_path = ? WHERE document_id = ?",
            (target, document_id),
        )
        raise sqlite3.OperationalError("simulierter Rebasefehler")

    with mock.patch.object(
        RestoreStagingService,
        "_apply_document_rebase",
        side_effect=fail_after_first_update,
    ):
        with pytest.raises(RestoreMaterializationError, match="Rebasing"):
            service.prepare_staging(
                PrepareRestoreStagingCommand(backup, paths, "RST-REBASE-FAIL")
            )
    staging = paths.root / "restore-staging" / "RST-REBASE-FAIL"
    with sqlite3.connect(staging / "prepared" / "kompetenzmanager.sqlite") as connection:
        stored = connection.execute(
            "SELECT file_path FROM documents WHERE document_id = 'MED-000001'"
        ).fetchone()[0]
    assert stored == original_path
    assert json.loads((staging / "staging-state.json").read_text())["phase"] == "failed"
    assert service.cleanup_staging(
        CleanupRestoreStagingCommand("RST-REBASE-FAIL", paths)
    )
    assert not staging.exists()


def test_corrupted_prepared_database_and_symlink_are_rejected(tmp_path: Path) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    service.prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-CORRUPT-DB")
    )
    staging = paths.root / "restore-staging" / "RST-CORRUPT-DB"
    database = staging / "prepared" / "kompetenzmanager.sqlite"
    database.write_bytes(b"not sqlite")
    with pytest.raises(RestoreError):
        service.verify_prepared(VerifyPreparedRestoreQuery("RST-CORRUPT-DB", paths))

    service.prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-SYMLINK")
    )
    managed = (
        paths.root
        / "restore-staging"
        / "RST-SYMLINK"
        / "prepared"
        / "documents"
        / "managed"
        / "MED-000001"
        / "MED-000001.txt"
    )
    external = tmp_path / "outside.txt"
    external.write_bytes(b"private managed bytes")
    managed.unlink()
    managed.symlink_to(external)
    with pytest.raises(RestoreMaterializationError, match="Symlink"):
        service.verify_prepared(VerifyPreparedRestoreQuery("RST-SYMLINK", paths))


def test_verified_restore_safety_backup_is_isolated_and_never_overwritten(
    tmp_path: Path,
) -> None:
    paths = _runtime(tmp_path)
    _insert_personal_data(paths, managed_file=True)
    backup = _create_backup(paths)
    before = _live_state(paths)
    service = RestoreApplicationService(now=lambda: FIXED_NOW)
    service.prepare_staging(
        PrepareRestoreStagingCommand(backup, paths, "RST-SAFETY")
    )
    safety = service.create_safety_backup(
        CreateRestoreSafetyBackupCommand(
            restore_id="RST-SAFETY",
            runtime_paths=paths,
            app_version="0.1.2",
            build_commit="e9d3338",
            source_tree_state="clean",
        )
    )
    assert safety.verified is True
    assert safety.path.parent == (
        paths.backups / "restore-safety" / "RST-SAFETY"
    )
    assert hashlib.sha256(safety.path.read_bytes()).hexdigest() == safety.archive_sha256
    assert safety.path.stat().st_size == safety.archive_size_bytes
    with pytest.raises(RestoreError, match="existiert bereits"):
        service.create_safety_backup(
            CreateRestoreSafetyBackupCommand(
                restore_id="RST-SAFETY",
                runtime_paths=paths,
                app_version="0.1.2",
                build_commit="e9d3338",
                source_tree_state="clean",
            )
        )
    assert _live_state(paths) == before


def stat_mode(path: Path) -> int:
    return os.stat(path).st_mode & 0o777
