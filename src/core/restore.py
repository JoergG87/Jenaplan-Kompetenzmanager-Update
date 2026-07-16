"""Isolated restore-backup verification without staging or live replacement."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .backup import (
    DATABASE_ARCHIVE_PATH,
    BackupCounts,
    BackupError,
    BackupFormatError,
    BackupIntegrityError,
    BackupManifest,
    BackupVerifier,
)
from .database_compatibility import (
    DatabaseCompatibilityError,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
    DatabaseCompatibilityStatus,
)


_COPY_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class RestorePreview:
    """Privacy-minimized technical preview of a verified backup."""

    created_at: str
    app_version: str
    backup_format_version: int
    database_compatibility_version: int
    sqlite_user_version: int
    compatibility_status: DatabaseCompatibilityStatus
    students_count: int
    observations_count: int
    learning_report_revisions_count: int
    learning_conference_revisions_count: int
    managed_files_count: int
    external_references_count: int
    external_missing_count: int


@dataclass(frozen=True)
class RestoreCompatibility:
    """Technical compatibility evidence for a restore candidate."""

    status: DatabaseCompatibilityStatus
    database_compatibility_version: int
    sqlite_user_version: int
    schema_fingerprint: str


@dataclass(frozen=True)
class RestoreVerificationResult:
    """Successful verification result without a retained staging directory."""

    path: Path
    archive_sha256: str
    archive_size_bytes: int
    compatibility: RestoreCompatibility
    preview: RestorePreview
    warnings: tuple[str, ...] = ()


class RestoreError(RuntimeError):
    """Base class for controlled restore-verification failures."""


class RestoreFormatError(RestoreError):
    """Raised when the backup container or manifest format is invalid."""


class RestoreCompatibilityError(RestoreError):
    """Raised when database and compatibility metadata are not accepted."""


class RestoreIntegrityError(RestoreError):
    """Raised when archived bytes or SQLite integrity cannot be proven."""


class RestoreVerifier:
    """Verify and preview a backup without changing or retaining its payload."""

    def __init__(
        self,
        *,
        backup_verifier: BackupVerifier | None = None,
        compatibility_inspector: DatabaseCompatibilityInspector | None = None,
        temporary_root: Path | None = None,
    ) -> None:
        self.backup_verifier = backup_verifier or BackupVerifier()
        self.compatibility_inspector = (
            compatibility_inspector or DatabaseCompatibilityInspector()
        )
        self.temporary_root = None if temporary_root is None else Path(temporary_root)

    def verify(self, path: Path) -> RestoreVerificationResult:
        path = Path(path)
        try:
            backup_verification = self.backup_verifier.verify_backup(path)
        except BackupFormatError as error:
            raise RestoreFormatError(str(error)) from error
        except BackupIntegrityError as error:
            raise RestoreIntegrityError(str(error)) from error
        except BackupError as error:
            raise RestoreError(str(error)) from error

        try:
            with path.open("rb") as archive_file:
                archive_size, archive_sha256 = _size_and_sha256_handle(archive_file)
                if (
                    archive_size != backup_verification.archive_size_bytes
                    or archive_sha256 != backup_verification.archive_sha256
                ):
                    raise RestoreIntegrityError(
                        "Die Archivbytes wurden nach der Backup-Pruefung veraendert."
                    )
                archive_file.seek(0)
                with tempfile.TemporaryDirectory(
                    prefix="jkmrestore-verify-",
                    dir=self.temporary_root,
                ) as temporary_name:
                    extraction_root = Path(temporary_name)
                    with zipfile.ZipFile(archive_file, mode="r") as archive:
                        self.backup_verifier.extract_isolated(
                            archive,
                            extraction_root,
                        )
                    compatibility, preview = self._verify_extracted(
                        extraction_root,
                        backup_verification.manifest,
                    )
        except RestoreError:
            raise
        except BackupFormatError as error:
            raise RestoreFormatError(str(error)) from error
        except BackupIntegrityError as error:
            raise RestoreIntegrityError(str(error)) from error
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            raise RestoreIntegrityError(
                f"Das Restore-Backup konnte nicht isoliert geprueft werden: {error}"
            ) from error

        return RestoreVerificationResult(
            path=path,
            archive_sha256=archive_sha256,
            archive_size_bytes=archive_size,
            compatibility=compatibility,
            preview=preview,
            warnings=backup_verification.warnings,
        )

    def _verify_extracted(
        self,
        extraction_root: Path,
        manifest: BackupManifest,
    ) -> tuple[RestoreCompatibility, RestorePreview]:
        database_path = extraction_root.joinpath(
            *PurePosixPath(DATABASE_ARCHIVE_PATH).parts
        )
        try:
            result = self.compatibility_inspector.inspect(database_path)
            DatabaseCompatibilityPolicy.require_backup_compatible(result)
        except DatabaseCompatibilityError as error:
            raise RestoreCompatibilityError(str(error)) from error

        actual_compatibility_version = result.version.compatibility_version
        if actual_compatibility_version is None:
            raise RestoreCompatibilityError(
                "Die Kandidatendatenbank besitzt keine unterstuetzte Kompatibilitaet."
            )
        if (
            manifest.database.sqlite_user_version
            != result.version.sqlite_user_version
        ):
            raise RestoreCompatibilityError(
                "Manifest und Datenbank widersprechen sich bei sqlite_user_version."
            )
        if (
            manifest.database.compatibility_version
            != actual_compatibility_version
        ):
            raise RestoreCompatibilityError(
                "Manifest und Datenbank widersprechen sich bei compatibility_version."
            )

        counts = self._verify_database(database_path)
        if counts != manifest.counts:
            raise RestoreIntegrityError(
                "Die Datenbank-Counts stimmen nicht mit dem Manifest ueberein."
            )
        self._verify_managed_files(extraction_root, manifest)

        compatibility = RestoreCompatibility(
            status=result.status,
            database_compatibility_version=actual_compatibility_version,
            sqlite_user_version=result.version.sqlite_user_version,
            schema_fingerprint=result.schema_identity.fingerprint,
        )
        preview = RestorePreview(
            created_at=manifest.created_at,
            app_version=manifest.app_version,
            backup_format_version=manifest.backup_format_version,
            database_compatibility_version=actual_compatibility_version,
            sqlite_user_version=result.version.sqlite_user_version,
            compatibility_status=result.status,
            students_count=counts.students,
            observations_count=counts.observations,
            learning_report_revisions_count=counts.learning_report_revisions,
            learning_conference_revisions_count=(
                counts.learning_conference_revisions
            ),
            managed_files_count=len(manifest.managed_files),
            external_references_count=manifest.external_references.count,
            external_missing_count=manifest.external_references.missing_count,
        )
        return compatibility, preview

    @staticmethod
    def _verify_database(database_path: Path) -> BackupCounts:
        try:
            with closing(_open_read_only_database(database_path)) as connection:
                integrity_rows = connection.execute(
                    "PRAGMA integrity_check"
                ).fetchall()
                if integrity_rows != [("ok",)]:
                    detail = "; ".join(str(row[0]) for row in integrity_rows[:5])
                    raise RestoreIntegrityError(
                        f"SQLite integrity_check ist fehlgeschlagen: {detail}"
                    )
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise RestoreIntegrityError(
                        "SQLite foreign_key_check meldet verletzte Referenzen."
                    )
                return BackupCounts(
                    students=_count(connection, "students"),
                    observations=_count(connection, "observations"),
                    learning_report_revisions=_count(
                        connection, "learning_report_revisions"
                    ),
                    learning_conference_revisions=_count(
                        connection, "learning_conference_revisions"
                    ),
                )
        except RestoreIntegrityError:
            raise
        except sqlite3.Error as error:
            raise RestoreIntegrityError(
                f"Die Kandidatendatenbank konnte nicht geprueft werden: {error}"
            ) from error

    @staticmethod
    def _verify_managed_files(
        extraction_root: Path,
        manifest: BackupManifest,
    ) -> None:
        for item in manifest.managed_files:
            file_path = extraction_root.joinpath(
                *PurePosixPath(item.archive_path).parts
            )
            size, sha256 = _size_and_sha256_path(file_path)
            if size != item.size_bytes or sha256 != item.sha256:
                raise RestoreIntegrityError(
                    "Eine verwaltete Datei stimmt nicht mit dem Manifest ueberein."
                )


def _open_read_only_database(path: Path) -> sqlite3.Connection:
    uri = f"{Path(path).resolve().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _count(connection: sqlite3.Connection, table: str) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if exists is None:
        return 0
    quoted = '"' + table.replace('"', '""') + '"'
    return int(connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])


def _size_and_sha256_path(path: Path) -> tuple[int, str]:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RestoreIntegrityError("Eine verwaltete Backup-Datei fehlt.") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RestoreIntegrityError(
            "Eine verwaltete Backup-Datei ist keine regulaere Datei."
        )
    try:
        with path.open("rb") as file:
            return _size_and_sha256_handle(file)
    except OSError as error:
        raise RestoreIntegrityError(
            "Eine verwaltete Backup-Datei konnte nicht gelesen werden."
        ) from error


def _size_and_sha256_handle(file) -> tuple[int, str]:
    metadata = os.fstat(file.fileno())
    if not stat.S_ISREG(metadata.st_mode):
        raise RestoreFormatError("Die Backup-Datei ist keine regulaere Datei.")
    digest = hashlib.sha256()
    size = 0
    while chunk := file.read(_COPY_CHUNK_SIZE):
        digest.update(chunk)
        size += len(chunk)
    return size, digest.hexdigest()
