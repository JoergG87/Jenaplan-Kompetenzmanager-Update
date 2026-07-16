"""Safe, format-versioned backups of SQLite data and managed files."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import time
import unicodedata
import zipfile
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping


BACKUP_FORMAT = "jenaplan-kompetenzmanager-backup"
BACKUP_FORMAT_VERSION = 1
DATABASE_COMPATIBILITY_VERSION = 1
BACKUP_EXTENSION = ".jkmbackup"
DATABASE_ARCHIVE_PATH = "database/kompetenzmanager.sqlite"
MANIFEST_ARCHIVE_PATH = "manifest.json"
EXTERNAL_REFERENCE_NOTE = (
    "Externe Dateireferenzen sind nicht im Backup enthalten."
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_TECHNICAL_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_CREATED_AT_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_APP_VERSION_PATTERN = re.compile(
    r"(?:unknown|\d+\.\d+\.\d+(?:[-+][0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?)"
)
_BUILD_COMMIT_PATTERN = re.compile(r"(?:unknown|[0-9a-f]{7,64})")
_SOURCE_TREE_STATES = frozenset({"clean", "dirty"})
_COPY_CHUNK_SIZE = 1024 * 1024


class BackupError(RuntimeError):
    """Base class for controlled backup failures."""


class BackupValidationError(BackupError):
    """Raised when inputs or inventory violate the backup contract."""


class BackupIntegrityError(BackupError):
    """Raised when database or managed-file integrity cannot be proven."""


class BackupBusyError(BackupError):
    """Raised after the bounded SQLite backup wait expires."""


class BackupFileError(BackupError):
    """Raised for safe file-system preparation or publication failures."""


class BackupFormatError(BackupError):
    """Raised when an archive does not conform to backup format v1."""


@dataclass(frozen=True)
class BackupCounts:
    """Non-personal aggregate counts captured from the database snapshot."""

    students: int
    observations: int
    learning_report_revisions: int
    learning_conference_revisions: int

    def to_dict(self) -> dict[str, int]:
        return {
            "learning_conference_revisions": self.learning_conference_revisions,
            "learning_report_revisions": self.learning_report_revisions,
            "observations": self.observations,
            "students": self.students,
        }


@dataclass(frozen=True)
class BackupExternalReferenceSummary:
    """Path-free summary of registered documents outside managed storage."""

    included: bool
    count: int
    missing_count: int
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "included": self.included,
            "missing_count": self.missing_count,
            "note": self.note,
        }


@dataclass(frozen=True)
class BackupManagedFile:
    """Manifest-safe identity and integrity metadata for one managed file."""

    kind: str
    record_id: str
    archive_path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "archive_path": self.archive_path,
            "kind": self.kind,
            "record_id": self.record_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class BackupDatabaseInfo:
    """Integrity and compatibility metadata for the SQLite snapshot."""

    archive_path: str
    sha256: str
    size_bytes: int
    sqlite_user_version: int
    compatibility_version: int
    schema_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "archive_path": self.archive_path,
            "compatibility_version": self.compatibility_version,
            "schema_fingerprint": self.schema_fingerprint,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "sqlite_user_version": self.sqlite_user_version,
        }


@dataclass(frozen=True)
class BackupManifest:
    """Canonical, privacy-minimized manifest for backup format v1."""

    backup_format: str
    backup_format_version: int
    created_at: str
    app_version: str
    build_commit: str
    source_tree_state: str | None
    database: BackupDatabaseInfo
    counts: BackupCounts
    managed_files: tuple[BackupManagedFile, ...]
    external_references: BackupExternalReferenceSummary

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "app_version": self.app_version,
            "backup_format": self.backup_format,
            "backup_format_version": self.backup_format_version,
            "build_commit": self.build_commit,
            "counts": self.counts.to_dict(),
            "created_at": self.created_at,
            "database": self.database.to_dict(),
            "external_references": self.external_references.to_dict(),
            "managed_files": [item.to_dict() for item in self.managed_files],
        }
        if self.source_tree_state is not None:
            payload["source_tree_state"] = self.source_tree_state
        return payload

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())


@dataclass(frozen=True)
class BackupVerificationResult:
    """Successful isolated verification result."""

    path: Path
    manifest: BackupManifest
    archive_sha256: str
    archive_size_bytes: int
    archive_file_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackupResult:
    """Result returned only after verified exclusive publication."""

    path: Path
    manifest: BackupManifest
    verification: BackupVerificationResult
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _InventoryFile:
    kind: str
    record_id: str
    source_path: Path
    archive_path: str
    expected_signature: tuple[int, int, int, int, int]
    expected_size: int | None = None
    expected_sha256: str | None = None


@dataclass(frozen=True)
class _BackupInventory:
    files: tuple[_InventoryFile, ...]
    external_references: BackupExternalReferenceSummary


class SQLiteBackupEngine:
    """Create and validate SQLite snapshots through the Python backup API."""

    def __init__(
        self,
        *,
        busy_timeout_seconds: float = 3.0,
        retry_interval_seconds: float = 0.05,
        pages_per_step: int = 128,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if busy_timeout_seconds < 0 or retry_interval_seconds <= 0:
            raise ValueError("Backup-Timeout und Retry-Intervall sind ungueltig.")
        self.busy_timeout_seconds = busy_timeout_seconds
        self.retry_interval_seconds = retry_interval_seconds
        self.pages_per_step = max(1, pages_per_step)
        self.monotonic = monotonic

    def create_snapshot(self, source_path: Path, snapshot_path: Path) -> Path:
        source_path = Path(source_path)
        snapshot_path = Path(snapshot_path)
        if not source_path.is_file():
            raise BackupFileError(f"Die Quelldatenbank fehlt: {source_path}")
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot_path.exists():
            raise BackupFileError(
                f"Der temporaere Datenbanksnapshot existiert bereits: {snapshot_path}"
            )
        busy_since: float | None = None

        def progress(status: int, _remaining: int, _total: int) -> None:
            nonlocal busy_since
            if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                now = self.monotonic()
                if busy_since is None:
                    busy_since = now
                if now - busy_since >= self.busy_timeout_seconds:
                    raise BackupBusyError(
                        "Die Datenbank blieb fuer die Sicherung zu lange blockiert."
                    )
                return
            busy_since = None

        source_uri = f"{source_path.resolve().as_uri()}?mode=ro"
        try:
            with closing(
                sqlite3.connect(
                    source_uri,
                    uri=True,
                    timeout=self.retry_interval_seconds,
                )
            ) as source:
                source.execute("PRAGMA query_only = ON")
                with closing(sqlite3.connect(snapshot_path)) as target:
                    source.backup(
                        target,
                        pages=self.pages_per_step,
                        progress=progress,
                        sleep=self.retry_interval_seconds,
                    )
                    target.commit()
        except BackupBusyError:
            self._remove_snapshot_files(snapshot_path)
            raise
        except sqlite3.OperationalError as error:
            self._remove_snapshot_files(snapshot_path)
            if "busy" in str(error).lower() or "locked" in str(error).lower():
                raise BackupBusyError(
                    "Die Datenbank konnte innerhalb des Zeitlimits nicht gesichert werden."
                ) from error
            raise BackupIntegrityError(
                f"Der SQLite-Snapshot konnte nicht erstellt werden: {error}"
            ) from error
        except sqlite3.Error as error:
            self._remove_snapshot_files(snapshot_path)
            raise BackupIntegrityError(
                f"Der SQLite-Snapshot konnte nicht erstellt werden: {error}"
            ) from error
        try:
            self.validate_snapshot(snapshot_path)
        except BackupError:
            self._remove_snapshot_files(snapshot_path)
            raise
        return snapshot_path

    @staticmethod
    def validate_snapshot(snapshot_path: Path) -> None:
        try:
            with closing(_open_read_only_database(snapshot_path)) as connection:
                integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
                if integrity_rows != [("ok",)]:
                    detail = "; ".join(str(row[0]) for row in integrity_rows[:5])
                    raise BackupIntegrityError(
                        f"SQLite integrity_check ist fehlgeschlagen: {detail}"
                    )
                foreign_key_rows = connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
                if foreign_key_rows:
                    raise BackupIntegrityError(
                        "SQLite foreign_key_check meldet verletzte Referenzen."
                    )
        except BackupIntegrityError:
            raise
        except sqlite3.Error as error:
            raise BackupIntegrityError(
                f"Der SQLite-Snapshot konnte nicht geprueft werden: {error}"
            ) from error

    @staticmethod
    def schema_fingerprint(database_path: Path) -> str:
        try:
            with closing(_open_read_only_database(database_path)) as connection:
                structure = _schema_structure(connection)
        except sqlite3.Error as error:
            raise BackupIntegrityError(
                f"Das SQLite-Schema konnte nicht gelesen werden: {error}"
            ) from error
        return hashlib.sha256(_canonical_json_bytes(structure)).hexdigest()

    @staticmethod
    def _remove_snapshot_files(snapshot_path: Path) -> None:
        snapshot_path.unlink(missing_ok=True)
        Path(f"{snapshot_path}-wal").unlink(missing_ok=True)
        Path(f"{snapshot_path}-shm").unlink(missing_ok=True)


class BackupInventoryService:
    """Build the exact managed-file inventory from a SQLite snapshot."""

    def __init__(self, *, data_root: Path, documents_root: Path) -> None:
        self.data_root = _absolute_without_resolving(Path(data_root))
        self.documents_root = _absolute_without_resolving(Path(documents_root))

    def build_inventory(self, snapshot_path: Path) -> _BackupInventory:
        inventory: list[_InventoryFile] = []
        external_count = 0
        external_missing_count = 0
        try:
            with closing(_open_read_only_database(snapshot_path)) as connection:
                if _table_exists(connection, "documents"):
                    rows = connection.execute(
                        "SELECT document_id, file_path FROM documents ORDER BY document_id"
                    ).fetchall()
                    for document_id, stored_path in rows:
                        path = self._document_path(stored_path)
                        if path.is_relative_to(self.documents_root):
                            inventory.append(
                                self._inventory_file(
                                    "document",
                                    str(document_id),
                                    path,
                                )
                            )
                        else:
                            external_count += 1
                            if not path.exists():
                                external_missing_count += 1
                inventory.extend(
                    self._pdf_inventory(
                        connection,
                        table="learning_report_pdf_artifacts",
                        id_column="learning_report_pdf_artifact_id",
                        kind="learning_report_pdf",
                    )
                )
                inventory.extend(
                    self._pdf_inventory(
                        connection,
                        table="learning_conference_pdf_artifacts",
                        id_column="learning_conference_pdf_artifact_id",
                        kind="learning_conference_pdf",
                    )
                )
        except BackupError:
            raise
        except (sqlite3.Error, OSError, TypeError) as error:
            raise BackupIntegrityError(
                f"Das Backup-Inventar konnte nicht gelesen werden: {error}"
            ) from error

        self._validate_inventory(inventory)
        return _BackupInventory(
            tuple(sorted(inventory, key=lambda item: (item.kind, item.record_id))),
            BackupExternalReferenceSummary(
                included=False,
                count=external_count,
                missing_count=external_missing_count,
                note=EXTERNAL_REFERENCE_NOTE,
            ),
        )

    def _document_path(self, stored_path: object) -> Path:
        if not isinstance(stored_path, str) or not stored_path.strip():
            raise BackupIntegrityError(
                "Eine registrierte Dokumentreferenz besitzt keinen gueltigen Pfad."
            )
        path = Path(stored_path).expanduser()
        return _absolute_without_resolving(path)

    def _pdf_inventory(
        self,
        connection: sqlite3.Connection,
        *,
        table: str,
        id_column: str,
        kind: str,
    ) -> list[_InventoryFile]:
        if not _table_exists(connection, table):
            return []
        rows = connection.execute(
            f"SELECT {id_column}, relative_file_path, file_size_bytes, pdf_sha256 "
            f"FROM {table} ORDER BY {id_column}"
        ).fetchall()
        result: list[_InventoryFile] = []
        for record_id, relative_file_path, size_bytes, sha256 in rows:
            relative = _safe_relative_path(relative_file_path)
            source_path = _absolute_without_resolving(self.data_root / relative)
            if not source_path.is_relative_to(self.documents_root):
                raise BackupIntegrityError(
                    "Ein registriertes finales PDF liegt ausserhalb des verwalteten "
                    "Dokumentverzeichnisses."
                )
            result.append(
                self._inventory_file(
                    kind,
                    str(record_id),
                    source_path,
                    expected_size=int(size_bytes),
                    expected_sha256=str(sha256),
                )
            )
        return result

    @staticmethod
    def _inventory_file(
        kind: str,
        record_id: str,
        source_path: Path,
        *,
        expected_size: int | None = None,
        expected_sha256: str | None = None,
    ) -> _InventoryFile:
        if not _TECHNICAL_ID_PATTERN.fullmatch(record_id):
            raise BackupIntegrityError(
                f"Ungueltige technische Datei-ID im Backup-Inventar: {record_id}"
            )
        extension = _neutral_extension(source_path)
        expected_signature = _stat_signature(_assert_regular_file(source_path))
        return _InventoryFile(
            kind=kind,
            record_id=record_id,
            source_path=source_path,
            archive_path=f"files/{record_id}.{extension}",
            expected_signature=expected_signature,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )

    def _validate_inventory(self, inventory: list[_InventoryFile]) -> None:
        archive_paths: set[str] = set()
        registered_paths: set[Path] = set()
        for item in inventory:
            if item.archive_path in archive_paths:
                raise BackupIntegrityError(
                    f"Doppelter Archivpfad im Backup-Inventar: {item.archive_path}"
                )
            archive_paths.add(item.archive_path)
            registered_paths.add(item.source_path)
            if _stat_signature(_assert_regular_file(item.source_path)) != (
                item.expected_signature
            ):
                raise BackupIntegrityError(
                    f"Eine verwaltete Datei wurde waehrend der Inventarisierung veraendert: "
                    f"{item.record_id}"
                )
        self._reject_unregistered_document_files(registered_paths)

    def _reject_unregistered_document_files(
        self,
        registered_paths: set[Path],
    ) -> None:
        if not self.documents_root.exists():
            if registered_paths:
                raise BackupIntegrityError(
                    "Das Verzeichnis fuer verwaltete Dokumente fehlt."
                )
            return
        _assert_directory_without_symlink(self.documents_root)
        for root, directory_names, file_names in os.walk(
            self.documents_root,
            topdown=True,
            followlinks=False,
        ):
            root_path = Path(root)
            for directory_name in tuple(directory_names):
                directory_path = root_path / directory_name
                if directory_path.is_symlink():
                    raise BackupIntegrityError(
                        f"Symlink im verwalteten Dokumentverzeichnis: {directory_path}"
                    )
                _assert_directory_without_symlink(directory_path)
            for file_name in file_names:
                path = _absolute_without_resolving(root_path / file_name)
                if file_name == ".DS_Store":
                    continue
                _assert_regular_file(path)
                if path not in registered_paths:
                    relative = path.relative_to(self.documents_root)
                    raise BackupIntegrityError(
                        "Unregistrierte Datei im verwalteten Dokumentverzeichnis: "
                        f"{relative.as_posix()}"
                    )


class BackupService:
    """Orchestrate creation, self-verification, and exclusive publication."""

    def __init__(
        self,
        *,
        database_path: Path,
        data_root: Path,
        documents_root: Path,
        target_directory: Path,
        app_version: str,
        build_commit: str,
        source_tree_state: str | None,
        now: Callable[[], datetime],
        sqlite_engine: SQLiteBackupEngine | None = None,
        verifier: BackupVerifier | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.data_root = Path(data_root)
        self.documents_root = Path(documents_root)
        self.target_directory = Path(target_directory)
        self.app_version = _validated_app_version(
            app_version,
            error_type=BackupValidationError,
        )
        self.build_commit = _validated_build_commit(
            build_commit,
            error_type=BackupValidationError,
        )
        self.source_tree_state = _validated_source_tree_state(
            source_tree_state,
            error_type=BackupValidationError,
        )
        self.now = now
        self.sqlite_engine = sqlite_engine or SQLiteBackupEngine()
        self.verifier = verifier or BackupVerifier()

    def create_backup(self) -> BackupResult:
        created_at = _normalize_utc(self.now())
        final_path = self.target_directory / _backup_filename(created_at)
        temporary_archive: Path | None = None
        try:
            self._prepare_target(final_path)
            self._check_free_space()
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".incomplete-jkmbackup-",
                suffix=BACKUP_EXTENSION,
                dir=self.target_directory,
            )
            os.close(descriptor)
            temporary_archive = Path(temporary_name)
            with tempfile.TemporaryDirectory(
                prefix=".jkmbackup-staging-",
                dir=self.target_directory,
            ) as staging_name:
                staging = Path(staging_name)
                snapshot_path = staging / "database" / "kompetenzmanager.sqlite"
                self.sqlite_engine.create_snapshot(self.database_path, snapshot_path)
                inventory = BackupInventoryService(
                    data_root=self.data_root,
                    documents_root=self.documents_root,
                ).build_inventory(snapshot_path)
                managed_files = self._stage_managed_files(inventory.files, staging)
                manifest = self._manifest(
                    created_at,
                    snapshot_path,
                    managed_files,
                    inventory.external_references,
                )
                self._write_archive(
                    temporary_archive,
                    snapshot_path,
                    staging,
                    manifest,
                )
            verification = self.verifier.verify_backup(temporary_archive)
            self._fsync_file(temporary_archive)
            self._publish_exclusively(temporary_archive, final_path)
            temporary_archive = None
            final_verification = replace(verification, path=final_path)
            return BackupResult(
                path=final_path,
                manifest=manifest,
                verification=final_verification,
                warnings=final_verification.warnings,
            )
        except BackupError:
            raise
        except OSError as error:
            raise BackupFileError(f"Das Backup konnte nicht erstellt werden: {error}") from error
        finally:
            if temporary_archive is not None:
                temporary_archive.unlink(missing_ok=True)

    def _prepare_target(self, final_path: Path) -> None:
        try:
            self.target_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise BackupFileError(
                f"Der Backup-Zielordner konnte nicht angelegt werden: {self.target_directory}"
            ) from error
        if not self.target_directory.is_dir():
            raise BackupFileError(
                f"Der Backup-Zielpfad ist kein Ordner: {self.target_directory}"
            )
        target_absolute = _absolute_without_resolving(self.target_directory)
        documents_absolute = _absolute_without_resolving(self.documents_root)
        if target_absolute == documents_absolute or target_absolute.is_relative_to(
            documents_absolute
        ):
            raise BackupValidationError(
                "Der Backup-Zielordner darf nicht im verwalteten Dokumentverzeichnis liegen."
            )
        if final_path.exists():
            raise BackupFileError(f"Ein Backup mit diesem Namen existiert bereits: {final_path}")
        try:
            descriptor, probe_name = tempfile.mkstemp(
                prefix=".jkmbackup-write-check-",
                dir=self.target_directory,
            )
            os.close(descriptor)
            Path(probe_name).unlink()
        except OSError as error:
            raise BackupFileError(
                f"Der Backup-Zielordner ist nicht beschreibbar: {self.target_directory}"
            ) from error

    def _check_free_space(self) -> None:
        required = 10 * 1024 * 1024
        for path in (
            self.database_path,
            Path(f"{self.database_path}-wal"),
            Path(f"{self.database_path}-shm"),
        ):
            try:
                if path.is_file():
                    required += path.stat().st_size * 2
            except OSError as error:
                raise BackupFileError(
                    f"Der Speicherbedarf konnte nicht ermittelt werden: {path}"
                ) from error
        if self.documents_root.exists():
            for root, _directories, files in os.walk(
                self.documents_root,
                followlinks=False,
            ):
                for name in files:
                    path = Path(root) / name
                    try:
                        metadata = path.lstat()
                    except OSError as error:
                        raise BackupFileError(
                            f"Der Speicherbedarf konnte nicht ermittelt werden: {path}"
                        ) from error
                    if stat.S_ISREG(metadata.st_mode):
                        required += metadata.st_size * 2
        free = shutil.disk_usage(self.target_directory).free
        if free < required:
            raise BackupFileError(
                "Im Backup-Zielordner ist nicht genug freier Speicherplatz vorhanden."
            )

    def _stage_managed_files(
        self,
        inventory: tuple[_InventoryFile, ...],
        staging: Path,
    ) -> tuple[BackupManagedFile, ...]:
        if not inventory:
            return ()
        managed: list[BackupManagedFile] = []
        documents_fd = _open_directory_fd(self.documents_root)
        try:
            for item in inventory:
                try:
                    relative_path = item.source_path.relative_to(
                        _absolute_without_resolving(self.documents_root)
                    )
                except ValueError as error:
                    raise BackupIntegrityError(
                        "Eine verwaltete Datei liegt ausserhalb des Dokumentverzeichnisses."
                    ) from error
                destination = staging / PurePosixPath(item.archive_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                size_bytes, sha256 = _copy_stable_managed_file(
                    documents_fd,
                    relative_path,
                    destination,
                    item.expected_signature,
                )
                if item.expected_size is not None and size_bytes != item.expected_size:
                    raise BackupIntegrityError(
                        f"Die gespeicherte Dateigroesse stimmt nicht: {item.record_id}"
                    )
                if item.expected_sha256 is not None and sha256 != item.expected_sha256:
                    raise BackupIntegrityError(
                        f"Der gespeicherte PDF-Hash stimmt nicht: {item.record_id}"
                    )
                managed.append(
                    BackupManagedFile(
                        kind=item.kind,
                        record_id=item.record_id,
                        archive_path=item.archive_path,
                        size_bytes=size_bytes,
                        sha256=sha256,
                    )
                )
        finally:
            os.close(documents_fd)
        return tuple(sorted(managed, key=lambda item: (item.kind, item.record_id)))

    def _manifest(
        self,
        created_at: datetime,
        snapshot_path: Path,
        managed_files: tuple[BackupManagedFile, ...],
        external_references: BackupExternalReferenceSummary,
    ) -> BackupManifest:
        database_size, database_sha256 = _file_size_and_sha256(snapshot_path)
        with closing(_open_read_only_database(snapshot_path)) as connection:
            sqlite_user_version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            counts = _read_counts(connection)
        return BackupManifest(
            backup_format=BACKUP_FORMAT,
            backup_format_version=BACKUP_FORMAT_VERSION,
            created_at=created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            app_version=self.app_version,
            build_commit=self.build_commit,
            source_tree_state=self.source_tree_state,
            database=BackupDatabaseInfo(
                archive_path=DATABASE_ARCHIVE_PATH,
                sha256=database_sha256,
                size_bytes=database_size,
                sqlite_user_version=sqlite_user_version,
                compatibility_version=DATABASE_COMPATIBILITY_VERSION,
                schema_fingerprint=self.sqlite_engine.schema_fingerprint(snapshot_path),
            ),
            counts=counts,
            managed_files=managed_files,
            external_references=external_references,
        )

    @staticmethod
    def _write_archive(
        archive_path: Path,
        snapshot_path: Path,
        staging: Path,
        manifest: BackupManifest,
    ) -> None:
        try:
            with zipfile.ZipFile(
                archive_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
                allowZip64=True,
            ) as archive:
                _write_zip_bytes(archive, MANIFEST_ARCHIVE_PATH, manifest.canonical_bytes())
                _write_zip_file(archive, DATABASE_ARCHIVE_PATH, snapshot_path)
                for managed_file in sorted(
                    manifest.managed_files,
                    key=lambda item: item.archive_path,
                ):
                    _write_zip_file(
                        archive,
                        managed_file.archive_path,
                        staging / PurePosixPath(managed_file.archive_path),
                    )
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            raise BackupFileError(f"Das Backup-Archiv konnte nicht geschrieben werden: {error}") from error

    @staticmethod
    def _fsync_file(path: Path) -> None:
        try:
            with path.open("rb") as archive_file:
                os.fsync(archive_file.fileno())
        except OSError as error:
            raise BackupFileError(
                f"Das Backup-Archiv konnte nicht dauerhaft geschrieben werden: {error}"
            ) from error

    def _publish_exclusively(self, temporary_path: Path, final_path: Path) -> None:
        published_by_us = False
        try:
            os.link(temporary_path, final_path)
            published_by_us = True
            temporary_path.unlink()
            try:
                descriptor = os.open(self.target_directory, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            except OSError:
                pass
        except FileExistsError as error:
            raise BackupFileError(
                f"Ein Backup mit diesem Namen existiert bereits: {final_path}"
            ) from error
        except OSError as error:
            if published_by_us:
                final_path.unlink(missing_ok=True)
            raise BackupFileError(
                f"Das Backup konnte nicht atomar veroeffentlicht werden: {error}"
            ) from error


class BackupVerifier:
    """Verify a backup archive in an isolated temporary directory."""

    def __init__(
        self,
        *,
        max_file_count: int = 10_000,
        max_total_size_bytes: int = 5 * 1024 * 1024 * 1024,
        max_member_size_bytes: int = 2 * 1024 * 1024 * 1024,
        max_manifest_size_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self.max_file_count = max_file_count
        self.max_total_size_bytes = max_total_size_bytes
        self.max_member_size_bytes = max_member_size_bytes
        self.max_manifest_size_bytes = max_manifest_size_bytes

    def verify_backup(self, path: Path) -> BackupVerificationResult:
        path = Path(path)
        if path.suffix != BACKUP_EXTENSION:
            raise BackupFormatError(
                f"Backup-Dateien muessen die Endung {BACKUP_EXTENSION} besitzen."
            )
        _assert_regular_file(path, error_type=BackupFormatError)
        if not zipfile.is_zipfile(path):
            raise BackupFormatError("Die Backup-Datei ist kein gueltiges ZIP-Archiv.")
        try:
            with zipfile.ZipFile(path, mode="r") as archive:
                infos = archive.infolist()
                self._validate_members(infos)
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise BackupIntegrityError(
                        f"ZIP-CRC-Pruefung fehlgeschlagen: {bad_member}"
                    )
                with tempfile.TemporaryDirectory(prefix="jkmbackup-verify-") as temp:
                    extraction_root = Path(temp)
                    self._extract_isolated(archive, infos, extraction_root)
                    manifest_bytes = (
                        extraction_root / MANIFEST_ARCHIVE_PATH
                    ).read_bytes()
                    manifest = self._parse_manifest(manifest_bytes)
                    self._verify_payload(extraction_root, infos, manifest)
        except BackupError:
            raise
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            raise BackupFormatError(f"Das Backup-Archiv ist ungueltig: {error}") from error
        archive_size, archive_sha256 = _file_size_and_sha256(path)
        warnings = ()
        if manifest.external_references.missing_count:
            warnings = (
                "Mindestens eine externe Dateireferenz war bei der Sicherung nicht erreichbar.",
            )
        return BackupVerificationResult(
            path=path,
            manifest=manifest,
            archive_sha256=archive_sha256,
            archive_size_bytes=archive_size,
            archive_file_count=len(infos),
            warnings=warnings,
        )

    def _validate_members(self, infos: list[zipfile.ZipInfo]) -> None:
        if not infos or len(infos) > self.max_file_count:
            raise BackupFormatError("Die Anzahl der Backup-Dateien ist ungueltig.")
        exact_names: set[str] = set()
        macos_names: set[str] = set()
        total_size = 0
        manifest_count = 0
        for info in infos:
            name = info.filename
            if name == MANIFEST_ARCHIVE_PATH:
                manifest_count += 1
                if info.file_size > self.max_manifest_size_bytes:
                    raise BackupFormatError("Das Backup-Manifest ist zu gross.")
            self._validate_archive_path(name)
            if name in exact_names:
                raise BackupFormatError(f"Doppelter Archivpfad: {name}")
            exact_names.add(name)
            macos_name = unicodedata.normalize("NFD", name).casefold()
            if macos_name in macos_names:
                raise BackupFormatError(
                    f"Unter macOS kollidierender Archivpfad: {name}"
                )
            macos_names.add(macos_name)
            file_type = stat.S_IFMT(info.external_attr >> 16)
            if info.is_dir() or file_type not in (0, stat.S_IFREG):
                raise BackupFormatError(
                    f"Symlink oder Sonderdatei im Backup-Archiv: {name}"
                )
            if info.file_size < 0 or info.file_size > self.max_member_size_bytes:
                raise BackupFormatError(f"Backup-Datei ueberschreitet das Groessenlimit: {name}")
            total_size += info.file_size
            if total_size > self.max_total_size_bytes:
                raise BackupFormatError("Das Backup ueberschreitet das Gesamtgroessenlimit.")
        if manifest_count != 1:
            raise BackupFormatError("Das Backup muss genau eine manifest.json enthalten.")

    @staticmethod
    def _validate_archive_path(name: str) -> None:
        if not name or "\\" in name or name.startswith("/"):
            raise BackupFormatError(f"Ungueltiger absoluter Archivpfad: {name}")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise BackupFormatError(f"Ungueltiger Archivpfad: {name}")
        allowed = (
            name == MANIFEST_ARCHIVE_PATH
            or name == DATABASE_ARCHIVE_PATH
            or (len(path.parts) == 2 and path.parts[0] == "files" and bool(path.parts[1]))
        )
        if not allowed:
            raise BackupFormatError(f"Unbekannter Archivpfad: {name}")

    def _extract_isolated(
        self,
        archive: zipfile.ZipFile,
        infos: list[zipfile.ZipInfo],
        extraction_root: Path,
    ) -> None:
        total_written = 0
        for info in infos:
            destination = extraction_root.joinpath(*PurePosixPath(info.filename).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            try:
                with archive.open(info, "r") as source, destination.open("xb") as target:
                    while chunk := source.read(_COPY_CHUNK_SIZE):
                        written += len(chunk)
                        total_written += len(chunk)
                        if written > info.file_size or written > self.max_member_size_bytes:
                            raise BackupFormatError(
                                f"Deklarierte Dateigroesse ist ungueltig: {info.filename}"
                            )
                        if total_written > self.max_total_size_bytes:
                            raise BackupFormatError(
                                "Das Backup ueberschreitet beim Entpacken das "
                                "Gesamtgroessenlimit."
                            )
                        target.write(chunk)
            except FileExistsError as error:
                raise BackupFormatError(
                    f"Doppeltes Extraktionsziel: {info.filename}"
                ) from error
            if written != info.file_size:
                raise BackupFormatError(
                    f"Deklarierte Dateigroesse ist ungueltig: {info.filename}"
                )

    def _parse_manifest(self, manifest_bytes: bytes) -> BackupManifest:
        if len(manifest_bytes) > self.max_manifest_size_bytes:
            raise BackupFormatError("Das Backup-Manifest ist zu gross.")
        try:
            payload = json.loads(manifest_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BackupFormatError("manifest.json ist kein gueltiges UTF-8-JSON.") from error
        if not isinstance(payload, dict) or _canonical_json_bytes(payload) != manifest_bytes:
            raise BackupFormatError("manifest.json ist nicht kanonisch serialisiert.")
        required = {
            "app_version",
            "backup_format",
            "backup_format_version",
            "build_commit",
            "counts",
            "created_at",
            "database",
            "external_references",
            "managed_files",
        }
        allowed = required | {"source_tree_state"}
        if set(payload) != required and set(payload) != allowed:
            raise BackupFormatError("manifest.json besitzt unbekannte oder fehlende Felder.")
        if payload["backup_format"] != BACKUP_FORMAT:
            raise BackupFormatError("Das Backup-Format ist unbekannt.")
        if payload["backup_format_version"] != BACKUP_FORMAT_VERSION:
            raise BackupFormatError("Die Backup-Formatversion wird nicht unterstuetzt.")
        if not isinstance(payload["created_at"], str) or not _CREATED_AT_PATTERN.fullmatch(
            payload["created_at"]
        ):
            raise BackupFormatError("created_at ist kein kanonischer UTC-Zeitpunkt.")
        app_version = _validated_app_version(
            payload.get("app_version"),
            error_type=BackupFormatError,
        )
        build_commit = _validated_build_commit(
            payload.get("build_commit"),
            error_type=BackupFormatError,
        )
        source_tree_state = _validated_source_tree_state(
            payload.get("source_tree_state"),
            error_type=BackupFormatError,
        )
        database = self._parse_database(payload["database"])
        counts = self._parse_counts(payload["counts"])
        managed_files = self._parse_managed_files(payload["managed_files"])
        external_references = self._parse_external_references(
            payload["external_references"]
        )
        return BackupManifest(
            backup_format=BACKUP_FORMAT,
            backup_format_version=BACKUP_FORMAT_VERSION,
            created_at=payload["created_at"],
            app_version=app_version,
            build_commit=build_commit,
            source_tree_state=source_tree_state,
            database=database,
            counts=counts,
            managed_files=managed_files,
            external_references=external_references,
        )

    @staticmethod
    def _parse_database(value: object) -> BackupDatabaseInfo:
        expected = {
            "archive_path",
            "compatibility_version",
            "schema_fingerprint",
            "sha256",
            "size_bytes",
            "sqlite_user_version",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise BackupFormatError("Die Datenbankinformationen im Manifest sind ungueltig.")
        if value["archive_path"] != DATABASE_ARCHIVE_PATH:
            raise BackupFormatError("Der Datenbank-Archivpfad ist ungueltig.")
        _validate_sha256(value["sha256"], "Datenbankhash")
        _validate_sha256(value["schema_fingerprint"], "Schema-Fingerprint")
        size = _non_negative_int(value["size_bytes"], "Datenbankgroesse")
        user_version = _non_negative_int(value["sqlite_user_version"], "user_version")
        compatibility = _non_negative_int(
            value["compatibility_version"], "compatibility_version"
        )
        if compatibility != DATABASE_COMPATIBILITY_VERSION:
            raise BackupFormatError("Die Datenbank-Kompatibilitaetsversion ist unbekannt.")
        return BackupDatabaseInfo(
            archive_path=DATABASE_ARCHIVE_PATH,
            sha256=value["sha256"],
            size_bytes=size,
            sqlite_user_version=user_version,
            compatibility_version=compatibility,
            schema_fingerprint=value["schema_fingerprint"],
        )

    @staticmethod
    def _parse_counts(value: object) -> BackupCounts:
        keys = {
            "students",
            "observations",
            "learning_report_revisions",
            "learning_conference_revisions",
        }
        if not isinstance(value, dict) or set(value) != keys:
            raise BackupFormatError("Die Manifest-Counts sind ungueltig.")
        return BackupCounts(
            students=_non_negative_int(value["students"], "students"),
            observations=_non_negative_int(value["observations"], "observations"),
            learning_report_revisions=_non_negative_int(
                value["learning_report_revisions"], "learning_report_revisions"
            ),
            learning_conference_revisions=_non_negative_int(
                value["learning_conference_revisions"],
                "learning_conference_revisions",
            ),
        )

    @staticmethod
    def _parse_managed_files(value: object) -> tuple[BackupManagedFile, ...]:
        if not isinstance(value, list):
            raise BackupFormatError("managed_files ist keine Liste.")
        expected_keys = {"kind", "record_id", "archive_path", "size_bytes", "sha256"}
        result: list[BackupManagedFile] = []
        archive_paths: set[str] = set()
        for item in value:
            if not isinstance(item, dict) or set(item) != expected_keys:
                raise BackupFormatError("Ein Managed-File-Eintrag ist ungueltig.")
            kind = _required_string(item, "kind")
            if kind not in {"document", "learning_report_pdf", "learning_conference_pdf"}:
                raise BackupFormatError(f"Unbekannte Managed-File-Art: {kind}")
            record_id = _required_string(item, "record_id")
            if not _TECHNICAL_ID_PATTERN.fullmatch(record_id):
                raise BackupFormatError("Eine technische Datei-ID ist ungueltig.")
            archive_path = _required_string(item, "archive_path")
            BackupVerifier._validate_archive_path(archive_path)
            if not archive_path.startswith("files/") or archive_path in archive_paths:
                raise BackupFormatError("Ein Managed-File-Archivpfad ist ungueltig oder doppelt.")
            archive_name = PurePosixPath(archive_path).name
            stem, separator, extension = archive_name.rpartition(".")
            if (
                not separator
                or stem != record_id
                or not extension
                or len(extension) > 12
                or not extension.isascii()
                or not extension.isalnum()
            ):
                raise BackupFormatError(
                    "Ein Managed-File-Archivpfad passt nicht zur technischen ID."
                )
            archive_paths.add(archive_path)
            _validate_sha256(item["sha256"], "Dateihash")
            result.append(
                BackupManagedFile(
                    kind=kind,
                    record_id=record_id,
                    archive_path=archive_path,
                    size_bytes=_non_negative_int(item["size_bytes"], "Dateigroesse"),
                    sha256=item["sha256"],
                )
            )
        sorted_result = sorted(result, key=lambda item: (item.kind, item.record_id))
        if result != sorted_result:
            raise BackupFormatError("managed_files ist nicht stabil sortiert.")
        return tuple(result)

    @staticmethod
    def _parse_external_references(value: object) -> BackupExternalReferenceSummary:
        keys = {"included", "count", "missing_count", "note"}
        if not isinstance(value, dict) or set(value) != keys:
            raise BackupFormatError("external_references ist ungueltig.")
        if value["included"] is not False or value["note"] != EXTERNAL_REFERENCE_NOTE:
            raise BackupFormatError("Externe Referenzen duerfen nicht enthalten sein.")
        count = _non_negative_int(value["count"], "externe Referenzen")
        missing_count = _non_negative_int(value["missing_count"], "fehlende Referenzen")
        if missing_count > count:
            raise BackupFormatError("missing_count ist groesser als count.")
        return BackupExternalReferenceSummary(False, count, missing_count, value["note"])

    def _verify_payload(
        self,
        extraction_root: Path,
        infos: list[zipfile.ZipInfo],
        manifest: BackupManifest,
    ) -> None:
        archive_names = {info.filename for info in infos}
        expected_names = {
            MANIFEST_ARCHIVE_PATH,
            manifest.database.archive_path,
            *(item.archive_path for item in manifest.managed_files),
        }
        if archive_names != expected_names:
            raise BackupFormatError(
                "Das Backup enthaelt fehlende oder unbekannte Nutzdateien."
            )
        database_path = extraction_root.joinpath(
            *PurePosixPath(manifest.database.archive_path).parts
        )
        database_size, database_sha256 = _file_size_and_sha256(database_path)
        if database_size != manifest.database.size_bytes:
            raise BackupIntegrityError("Die Datenbankgroesse stimmt nicht mit dem Manifest ueberein.")
        if database_sha256 != manifest.database.sha256:
            raise BackupIntegrityError("Der Datenbankhash stimmt nicht mit dem Manifest ueberein.")
        SQLiteBackupEngine.validate_snapshot(database_path)
        with closing(_open_read_only_database(database_path)) as connection:
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            counts = _read_counts(connection)
        if user_version != manifest.database.sqlite_user_version:
            raise BackupIntegrityError("SQLite user_version stimmt nicht mit dem Manifest ueberein.")
        if SQLiteBackupEngine.schema_fingerprint(database_path) != (
            manifest.database.schema_fingerprint
        ):
            raise BackupIntegrityError("Der Schema-Fingerprint stimmt nicht mit dem Manifest ueberein.")
        if counts != manifest.counts:
            raise BackupIntegrityError("Die Datenbank-Counts stimmen nicht mit dem Manifest ueberein.")
        for managed_file in manifest.managed_files:
            file_path = extraction_root.joinpath(
                *PurePosixPath(managed_file.archive_path).parts
            )
            size_bytes, sha256 = _file_size_and_sha256(file_path)
            if size_bytes != managed_file.size_bytes:
                raise BackupIntegrityError(
                    f"Die Dateigroesse stimmt nicht: {managed_file.record_id}"
                )
            if sha256 != managed_file.sha256:
                raise BackupIntegrityError(
                    f"Der Dateihash stimmt nicht: {managed_file.record_id}"
                )


def _canonical_json_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise BackupFormatError(f"Kanonisches JSON konnte nicht erzeugt werden: {error}") from error


def _normalize_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise BackupValidationError("Die Zeitquelle muss einen datetime-Wert liefern.")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)


def _backup_filename(created_at: datetime) -> str:
    return (
        "Jenaplan-Kompetenzmanager-Backup-"
        f"{created_at.strftime('%Y%m%dT%H%M%SZ')}{BACKUP_EXTENSION}"
    )


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _safe_relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        raise BackupIntegrityError("Ein verwalteter relativer Dateipfad ist ungueltig.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise BackupIntegrityError("Ein verwalteter relativer Dateipfad ist ungueltig.")
    return path


def _neutral_extension(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix and len(suffix) <= 12 and suffix.isascii() and suffix.isalnum():
        return suffix
    return "bin"


def _assert_regular_file(
    path: Path,
    *,
    error_type: type[BackupError] = BackupIntegrityError,
) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise error_type(f"Eine erforderliche verwaltete Datei fehlt: {path}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise error_type(f"Symlinks sind im Backup nicht erlaubt: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise error_type(f"Sonderdateien sind im Backup nicht erlaubt: {path}")
    return metadata


def _assert_directory_without_symlink(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BackupIntegrityError(f"Dokumentverzeichnis nicht lesbar: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise BackupIntegrityError(
            f"Symlink oder Sonderpfad im Dokumentverzeichnis: {path}"
        )


def _stat_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _open_directory_fd(path: Path) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        raise BackupIntegrityError(
            f"Das verwaltete Dokumentverzeichnis konnte nicht sicher geoeffnet werden: {path}"
        ) from error
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise BackupIntegrityError(
            f"Der verwaltete Dokumentpfad ist kein Verzeichnis: {path}"
        )
    return descriptor


def _open_relative_regular_file(
    documents_fd: int,
    relative_path: Path,
) -> tuple[int, os.stat_result]:
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or any(part in {"", ".", ".."} for part in relative_path.parts)
    ):
        raise BackupIntegrityError(
            "Ein verwalteter relativer Dateipfad ist ungueltig."
        )
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    file_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        file_flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    current_fd: int | None = None
    try:
        current_fd = os.dup(documents_fd)
        try:
            for component in relative_path.parts[:-1]:
                next_fd = os.open(
                    component,
                    directory_flags,
                    dir_fd=current_fd,
                )
                os.close(current_fd)
                current_fd = next_fd
            descriptor = os.open(
                relative_path.parts[-1],
                file_flags,
                dir_fd=current_fd,
            )
        finally:
            if current_fd is not None:
                os.close(current_fd)
        metadata = os.fstat(descriptor)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        raise BackupIntegrityError(
            "Eine verwaltete Datei konnte nicht ohne Symlink-Folgen geoeffnet werden: "
            f"{relative_path.as_posix()}"
        ) from error
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        raise BackupIntegrityError(
            f"Sonderdatei im verwalteten Dokumentverzeichnis: {relative_path.as_posix()}"
        )
    return descriptor, metadata


def _copy_stable_managed_file(
    documents_fd: int,
    relative_path: Path,
    destination_path: Path,
    expected_signature: tuple[int, int, int, int, int],
) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        descriptor, before_handle = _open_relative_regular_file(
            documents_fd,
            relative_path,
        )
        with os.fdopen(descriptor, "rb") as source, destination_path.open("xb") as target:
            if _stat_signature(before_handle) != expected_signature:
                raise BackupIntegrityError(
                    "Eine verwaltete Datei wurde nach der Inventarisierung ersetzt: "
                    f"{relative_path.as_posix()}"
                )
            while chunk := source.read(_COPY_CHUNK_SIZE):
                target.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            after_handle = os.fstat(source.fileno())
    except BackupError:
        destination_path.unlink(missing_ok=True)
        raise
    except OSError as error:
        destination_path.unlink(missing_ok=True)
        raise BackupFileError(
            f"Eine verwaltete Datei konnte nicht gelesen werden: {relative_path.as_posix()}"
        ) from error
    try:
        after_descriptor, after_path = _open_relative_regular_file(
            documents_fd,
            relative_path,
        )
        os.close(after_descriptor)
    except BackupError as error:
        destination_path.unlink(missing_ok=True)
        raise BackupIntegrityError(
            "Eine verwaltete Datei verschwand oder ihr Pfad wurde waehrend des "
            f"Backups ersetzt: {relative_path.as_posix()}"
        ) from error
    if (
        _stat_signature(before_handle) != expected_signature
        or _stat_signature(after_handle) != expected_signature
        or _stat_signature(after_path) != expected_signature
    ):
        destination_path.unlink(missing_ok=True)
        raise BackupIntegrityError(
            "Eine verwaltete Datei wurde waehrend des Lesens veraendert oder ersetzt: "
            f"{relative_path.as_posix()}"
        )
    return size, digest.hexdigest()


def _file_size_and_sha256(path: Path) -> tuple[int, str]:
    _assert_regular_file(path)
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as file:
            while chunk := file.read(_COPY_CHUNK_SIZE):
                digest.update(chunk)
                size += len(chunk)
    except OSError as error:
        raise BackupFileError(f"Eine Backup-Datei konnte nicht gelesen werden: {path}") from error
    return size, digest.hexdigest()


def _open_read_only_database(path: Path) -> sqlite3.Connection:
    uri = f"{Path(path).resolve().as_uri()}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone() is not None


def _read_counts(connection: sqlite3.Connection) -> BackupCounts:
    def count(table: str) -> int:
        if not _table_exists(connection, table):
            return 0
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])

    return BackupCounts(
        students=count("students"),
        observations=count("observations"),
        learning_report_revisions=count("learning_report_revisions"),
        learning_conference_revisions=count("learning_conference_revisions"),
    )


def _schema_structure(connection: sqlite3.Connection) -> dict[str, object]:
    table_names = [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    tables: list[dict[str, object]] = []
    for table_name in table_names:
        quoted_table = table_name.replace('"', '""')
        columns = [
            {
                "cid": int(row[0]),
                "name": str(row[1]),
                "type": str(row[2]),
                "not_null": bool(row[3]),
                "default": row[4],
                "primary_key_position": int(row[5]),
                "hidden": int(row[6]) if len(row) > 6 else 0,
            }
            for row in connection.execute(
                f'PRAGMA table_xinfo("{quoted_table}")'
            ).fetchall()
        ]
        foreign_keys = sorted(
            (
                {
                    "id": int(row[0]),
                    "sequence": int(row[1]),
                    "table": str(row[2]),
                    "from": str(row[3]),
                    "to": str(row[4]),
                    "on_update": str(row[5]),
                    "on_delete": str(row[6]),
                    "match": str(row[7]),
                }
                for row in connection.execute(
                    f'PRAGMA foreign_key_list("{quoted_table}")'
                ).fetchall()
            ),
            key=lambda item: (item["id"], item["sequence"]),
        )
        indexes: list[dict[str, object]] = []
        for row in connection.execute(
            f'PRAGMA index_list("{quoted_table}")'
        ).fetchall():
            index_name = str(row[1])
            quoted_index = index_name.replace('"', '""')
            sql_row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
                (index_name,),
            ).fetchone()
            index_sql = (
                _normalize_schema_sql(str(sql_row[0]))
                if sql_row is not None and sql_row[0] is not None
                else None
            )
            index_columns = [
                {
                    "sequence": int(column[0]),
                    "column_id": int(column[1]),
                    "name": None if column[2] is None else str(column[2]),
                    "descending": bool(column[3]),
                    "collation": None if column[4] is None else str(column[4]),
                    "key": bool(column[5]),
                }
                for column in connection.execute(
                    f'PRAGMA index_xinfo("{quoted_index}")'
                ).fetchall()
            ]
            indexes.append(
                {
                    "name": index_name if index_sql is not None else None,
                    "unique": bool(row[2]),
                    "origin": str(row[3]),
                    "partial": bool(row[4]),
                    "sql": index_sql,
                    "columns": index_columns,
                }
            )
        indexes.sort(key=_canonical_json_bytes)
        tables.append(
            {
                "name": table_name,
                "columns": columns,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
            }
        )
    return {"tables": tables}


def _normalize_schema_sql(sql: str) -> str:
    """Normalize stored explicit-index SQL without changing quoted content."""
    tokens: list[str] = []
    index = 0
    length = len(sql)
    while index < length:
        character = sql[index]
        if character.isspace():
            index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if character in {'\'', '"', '`', '['}:
            closing = ']' if character == '[' else character
            start = index
            index += 1
            while index < length:
                if sql[index] == closing:
                    if closing != ']' and index + 1 < length and sql[index + 1] == closing:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            tokens.append(sql[start:index])
            continue
        if character.isalnum() or character in {"_", "$"}:
            start = index
            index += 1
            while index < length and (
                sql[index].isalnum() or sql[index] in {"_", "$"}
            ):
                index += 1
            tokens.append(sql[start:index].lower())
            continue
        tokens.append(character)
        index += 1
    if tokens and tokens[-1] == ";":
        tokens.pop()
    return " ".join(tokens)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    return info


def _write_zip_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    archive.writestr(_zip_info(name), payload)


def _write_zip_file(archive: zipfile.ZipFile, name: str, source_path: Path) -> None:
    with source_path.open("rb") as source, archive.open(_zip_info(name), "w") as target:
        shutil.copyfileobj(source, target, length=_COPY_CHUNK_SIZE)


def _required_string(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise BackupFormatError(f"Manifestfeld {key} ist ungueltig.")
    return value


def _validated_app_version(
    value: object,
    *,
    error_type: type[BackupError],
) -> str:
    if not isinstance(value, str) or not _APP_VERSION_PATTERN.fullmatch(value):
        raise error_type("app_version ist kein erlaubter technischer Versionswert.")
    return value


def _validated_build_commit(
    value: object,
    *,
    error_type: type[BackupError],
) -> str:
    if not isinstance(value, str) or not _BUILD_COMMIT_PATTERN.fullmatch(value):
        raise error_type("build_commit ist keine erlaubte technische Git-ID.")
    return value


def _validated_source_tree_state(
    value: object,
    *,
    error_type: type[BackupError],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in _SOURCE_TREE_STATES:
        raise error_type("source_tree_state ist kein erlaubter technischer Status.")
    return value


def _non_negative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise BackupFormatError(f"Manifestwert {label} ist ungueltig.")
    return value


def _validate_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise BackupFormatError(f"{label} ist kein SHA-256-Hexdigest.")
