"""Verified restore staging without any live replacement."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Callable

from .backup import (
    DATABASE_ARCHIVE_PATH,
    MANIFEST_ARCHIVE_PATH,
    BackupError,
    BackupCounts,
    BackupFormatError,
    BackupIntegrityError,
    BackupManifest,
    BackupService,
    BackupVerifier,
    SQLiteBackupEngine,
)
from .database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
    DatabaseCompatibilityError,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
    DatabaseCompatibilityStatus,
)
from .observation_uow import (
    ObservationPersistenceUnitOfWork,
    ObservationWriterLock,
)
from .sqlite_store import SQLiteDatabase


_COPY_CHUNK_SIZE = 1024 * 1024
RESTORE_STAGING_DIRECTORY = "restore-staging"
RESTORE_SOURCE_DIRECTORY = "source"
RESTORE_PREPARED_DIRECTORY = "prepared"
RESTORE_STATE_FILENAME = "staging-state.json"
RESTORE_SAFETY_DIRECTORY = "restore-safety"
_RESTORE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}")
_KNOWN_PHASES = frozenset(
    {
        "source_extracted",
        "database_prepared",
        "files_materialized",
        "paths_rebased",
        "completed",
        "failed",
    }
)


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


@dataclass(frozen=True)
class RestoreStagingPaths:
    """Internally useful paths for one restore-id-bound staging directory."""

    root: Path
    source: Path
    source_database: Path
    prepared: Path
    prepared_database: Path
    prepared_documents: Path
    state: Path


@dataclass(frozen=True)
class RestoreStagingResult:
    """Technical result returned after a fully prepared staging succeeds."""

    restore_id: str
    status: str
    staging_path: Path
    source_compatibility: RestoreCompatibility
    target_compatibility: RestoreCompatibility
    preview: RestorePreview
    managed_files_count: int


@dataclass(frozen=True)
class PreparedRestoreVerificationResult:
    """Repeatable verification result for an already completed staging."""

    restore_id: str
    status: str
    staging_path: Path
    compatibility: RestoreCompatibility
    preview: RestorePreview
    managed_files_count: int


@dataclass(frozen=True)
class RestoreSafetyBackupResult:
    """Verified safety backup evidence for a later live-replacement sprint."""

    restore_id: str
    path: Path
    archive_sha256: str
    archive_size_bytes: int
    verified: bool


class RestoreError(RuntimeError):
    """Base class for controlled restore-verification failures."""


class RestoreFormatError(RestoreError):
    """Raised when the backup container or manifest format is invalid."""


class RestoreCompatibilityError(RestoreError):
    """Raised when database and compatibility metadata are not accepted."""


class RestoreIntegrityError(RestoreError):
    """Raised when archived bytes or SQLite integrity cannot be proven."""


class RestoreStagingError(RestoreError):
    """Raised when persistent staging cannot be prepared safely."""


class RestoreStateError(RestoreStagingError):
    """Raised for collisions, unknown phases, or unbound staging state."""


class RestoreMaterializationError(RestoreStagingError):
    """Raised when a managed file cannot be safely materialized."""


class RestoreSafetyBackupError(RestoreError):
    """Raised when a verified isolated restore safety backup cannot be made."""


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

    def verify_extracted(
        self,
        extraction_root: Path,
        manifest: BackupManifest,
    ) -> tuple[RestoreCompatibility, RestorePreview]:
        """Re-run restore checks on an already safely extracted payload."""
        return self._verify_extracted(Path(extraction_root), manifest)

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


class RestoreStagingService:
    """Prepare and verify restore data while keeping all live data untouched."""

    def __init__(
        self,
        *,
        backup_verifier: BackupVerifier | None = None,
        restore_verifier: RestoreVerifier | None = None,
        compatibility_inspector: DatabaseCompatibilityInspector | None = None,
        now: Callable[[], datetime] | None = None,
        restore_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.backup_verifier = backup_verifier or BackupVerifier()
        self.compatibility_inspector = (
            compatibility_inspector or DatabaseCompatibilityInspector()
        )
        self.restore_verifier = restore_verifier or RestoreVerifier(
            backup_verifier=self.backup_verifier,
            compatibility_inspector=self.compatibility_inspector,
        )
        self.now = now or (lambda: datetime.now(UTC))
        self.restore_id_factory = restore_id_factory or (
            lambda: f"RST-{uuid.uuid4().hex}"
        )

    def prepare(
        self,
        *,
        archive_path: Path,
        runtime_root: Path,
        live_database: Path,
        live_documents: Path,
        restore_id: str | None = None,
    ) -> RestoreStagingResult:
        live_database = _absolute_without_resolving(Path(live_database))
        observation_uow = ObservationPersistenceUnitOfWork(
            SQLiteDatabase(live_database)
        )
        with ObservationWriterLock(observation_uow.staging_root):
            observation_uow.recover_pending_while_writer_locked()
            return self._prepare_locked(
                archive_path=archive_path,
                runtime_root=runtime_root,
                live_database=live_database,
                live_documents=live_documents,
                restore_id=restore_id,
            )

    def _prepare_locked(
        self,
        *,
        archive_path: Path,
        runtime_root: Path,
        live_database: Path,
        live_documents: Path,
        restore_id: str | None = None,
    ) -> RestoreStagingResult:
        """Build one new staging from a fully verified, byte-bound archive."""
        archive_path = Path(archive_path)
        runtime_root = _absolute_without_resolving(Path(runtime_root))
        live_database = _absolute_without_resolving(Path(live_database))
        live_documents = _absolute_without_resolving(Path(live_documents))
        initial_size, initial_sha256 = _size_and_sha256_path(archive_path)
        try:
            backup_verification = self.backup_verifier.verify_backup(archive_path)
        except BackupFormatError as error:
            raise RestoreFormatError(str(error)) from error
        except BackupIntegrityError as error:
            raise RestoreIntegrityError(str(error)) from error
        except BackupError as error:
            raise RestoreStagingError(str(error)) from error
        try:
            restore_verification = self.restore_verifier.verify(archive_path)
        except RestoreError:
            raise
        if (
            initial_size != backup_verification.archive_size_bytes
            or initial_sha256 != backup_verification.archive_sha256
            or initial_size != restore_verification.archive_size_bytes
            or initial_sha256 != restore_verification.archive_sha256
        ):
            raise RestoreIntegrityError(
                "Die Archivbytes wurden waehrend der Vorpruefung veraendert."
            )

        restore_id = _validated_restore_id(
            restore_id if restore_id is not None else self.restore_id_factory()
        )
        paths = _staging_paths(runtime_root, restore_id)
        _validate_staging_boundaries(
            runtime_root=runtime_root,
            staging_root=paths.root.parent,
            live_database=live_database,
            live_documents=live_documents,
        )
        _check_staging_free_space(runtime_root, manifest=backup_verification.manifest)
        self._create_staging_directories(paths)
        manifest = backup_verification.manifest
        state = self._initial_state(
            restore_id=restore_id,
            archive_sha256=initial_sha256,
            archive_size=initial_size,
            manifest=manifest,
            compatibility=restore_verification.compatibility,
        )
        try:
            self._extract_bound_archive(
                archive_path=archive_path,
                expected_size=initial_size,
                expected_sha256=initial_sha256,
                paths=paths,
                manifest=manifest,
            )
            compatibility, preview = self.restore_verifier.verify_extracted(
                paths.source,
                manifest,
            )
            if compatibility != restore_verification.compatibility:
                raise RestoreIntegrityError(
                    "Die extrahierte Datenbank widerspricht der Restore-Vorpruefung."
                )
            state = self._set_phase(state, "source_extracted")
            _write_staging_state(paths.state, state)

            source_rows = _database_rows(paths.source_database)
            _copy_verified_file(
                paths.source_database,
                paths.prepared_database,
                expected_size=manifest.database.size_bytes,
                expected_sha256=manifest.database.sha256,
                allowed_root=paths.prepared,
            )
            copied = self.compatibility_inspector.inspect(paths.prepared_database)
            if copied.status is not DatabaseCompatibilityStatus.EXACT:
                raise RestoreCompatibilityError(
                    "Die kopierte Datenbank entspricht nicht mehr exakt Final-V3."
                )
            prepared_rows = _database_rows(paths.prepared_database)
            if prepared_rows != source_rows:
                raise RestoreIntegrityError(
                    "Die Staging-Kopie hat Datenbankwerte veraendert."
                )
            state = self._set_phase(state, "database_prepared")
            _write_staging_state(paths.state, state)

            document_targets = self._materialize_managed_files(
                paths=paths,
                manifest=manifest,
                live_documents=live_documents,
            )
            state = self._set_phase(state, "files_materialized")
            _write_staging_state(paths.state, state)

            self._rebase_managed_documents(
                paths.prepared_database,
                document_targets,
            )
            state = self._set_phase(state, "paths_rebased")
            _write_staging_state(paths.state, state)

            target_compatibility, verified_preview = self._verify_prepared_payload(
                paths=paths,
                manifest=manifest,
                live_documents=live_documents,
                source_preview=preview,
            )
            state = self._set_phase(state, "completed", completed=True)
            _write_staging_state(paths.state, state)
            return RestoreStagingResult(
                restore_id=restore_id,
                status="completed",
                staging_path=paths.root,
                source_compatibility=compatibility,
                target_compatibility=target_compatibility,
                preview=verified_preview,
                managed_files_count=len(manifest.managed_files),
            )
        except Exception as error:
            failed_state = self._set_phase(state, "failed", failed=True)
            try:
                _write_staging_state(paths.state, failed_state)
            except OSError:
                pass
            if isinstance(error, RestoreError):
                raise
            if isinstance(error, (OSError, sqlite3.Error, zipfile.BadZipFile)):
                raise RestoreStagingError(
                    f"Das Restore-Staging konnte nicht vorbereitet werden: {error}"
                ) from error
            raise

    def verify_prepared(
        self,
        *,
        runtime_root: Path,
        live_documents: Path,
        restore_id: str,
    ) -> PreparedRestoreVerificationResult:
        restore_id = _validated_restore_id(restore_id)
        paths = _staging_paths(Path(runtime_root), restore_id)
        state = _read_staging_state(paths.state, restore_id)
        if state["phase"] != "completed":
            raise RestoreStateError(
                "Nur ein abgeschlossenes Restore-Staging darf final geprueft werden."
            )
        try:
            manifest = self.backup_verifier.parse_manifest(
                paths.source.joinpath(MANIFEST_ARCHIVE_PATH).read_bytes()
            )
        except (OSError, BackupError) as error:
            raise RestoreIntegrityError(
                "Das gebundene Staging-Manifest ist nicht mehr gueltig."
            ) from error
        source_compatibility, source_preview = self.restore_verifier.verify_extracted(
            paths.source,
            manifest,
        )
        _assert_state_matches_source(state, manifest, source_compatibility)
        compatibility, preview = self._verify_prepared_payload(
            paths=paths,
            manifest=manifest,
            live_documents=_absolute_without_resolving(Path(live_documents)),
            source_preview=source_preview,
        )
        if source_compatibility.status is not DatabaseCompatibilityStatus.EXACT:
            raise RestoreCompatibilityError(
                "Die Source-Kompatibilitaet des Stagings ist unbekannt."
            )
        return PreparedRestoreVerificationResult(
            restore_id=restore_id,
            status="verified",
            staging_path=paths.root,
            compatibility=compatibility,
            preview=preview,
            managed_files_count=len(manifest.managed_files),
        )

    def cleanup(self, *, runtime_root: Path, restore_id: str) -> bool:
        """Delete only one directly owned completed or failed staging directory."""
        restore_id = _validated_restore_id(restore_id)
        paths = _staging_paths(Path(runtime_root), restore_id)
        state = _read_staging_state(paths.state, restore_id)
        if state["phase"] not in {"completed", "failed"}:
            raise RestoreStateError(
                "Ein Restore-Staging in Zwischenphase darf nicht bereinigt werden."
            )
        staging_parent = _absolute_without_resolving(paths.root.parent)
        target = _absolute_without_resolving(paths.root)
        if target.parent != staging_parent or target.name != restore_id:
            raise RestoreStateError("Das Restore-Staging ist nicht eindeutig zugeordnet.")
        metadata = target.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RestoreStateError("Das Restore-Staging ist kein sicheres Verzeichnis.")
        shutil.rmtree(target)
        return True

    def _create_staging_directories(self, paths: RestoreStagingPaths) -> None:
        parent = paths.root.parent
        try:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            _assert_real_directory(parent)
            os.chmod(parent, 0o700)
            paths.root.mkdir(mode=0o700, exist_ok=False)
            paths.source.mkdir(mode=0o700)
            paths.prepared.mkdir(mode=0o700)
            paths.prepared_documents.mkdir(mode=0o700)
        except FileExistsError as error:
            raise RestoreStateError(
                "Die technische Restore-ID ist bereits als Staging vorhanden."
            ) from error
        except OSError as error:
            raise RestoreStagingError(
                "Das Restore-Staging-Verzeichnis konnte nicht sicher angelegt werden."
            ) from error

    def _extract_bound_archive(
        self,
        *,
        archive_path: Path,
        expected_size: int,
        expected_sha256: str,
        paths: RestoreStagingPaths,
        manifest: BackupManifest,
    ) -> None:
        try:
            with archive_path.open("rb") as archive_file:
                before_size, before_hash = _size_and_sha256_handle(archive_file)
                if (before_size, before_hash) != (expected_size, expected_sha256):
                    raise RestoreIntegrityError(
                        "Die Archivdatei wurde vor der Staging-Extraktion ausgetauscht."
                    )
                archive_file.seek(0)
                with zipfile.ZipFile(archive_file, mode="r") as archive:
                    self.backup_verifier.extract_isolated(archive, paths.source)
                archive_file.seek(0)
                after_size, after_hash = _size_and_sha256_handle(archive_file)
                if (after_size, after_hash) != (expected_size, expected_sha256):
                    raise RestoreIntegrityError(
                        "Die gebundenen Archivbytes wurden waehrend der Extraktion veraendert."
                    )
            if paths.source.joinpath(MANIFEST_ARCHIVE_PATH).read_bytes() != (
                manifest.canonical_bytes()
            ):
                raise RestoreIntegrityError(
                    "Das extrahierte Manifest widerspricht den gebundenen Archivbytes."
                )
            _harden_tree(paths.source)
        except RestoreError:
            raise
        except (OSError, zipfile.BadZipFile) as error:
            raise RestoreIntegrityError(
                f"Die gebundenen Archivbytes konnten nicht extrahiert werden: {error}"
            ) from error

    def _materialize_managed_files(
        self,
        *,
        paths: RestoreStagingPaths,
        manifest: BackupManifest,
        live_documents: Path,
    ) -> dict[str, str]:
        targets = _managed_file_targets(
            database_path=paths.prepared_database,
            manifest=manifest,
            prepared_documents=paths.prepared_documents,
            live_documents=live_documents,
        )
        document_targets: dict[str, str] = {}
        for item in manifest.managed_files:
            target, runtime_document_path = targets[(item.kind, item.record_id)]
            source = paths.source.joinpath(*PurePosixPath(item.archive_path).parts)
            _copy_verified_file(
                source,
                target,
                expected_size=item.size_bytes,
                expected_sha256=item.sha256,
                allowed_root=paths.prepared_documents,
            )
            if item.kind == "document":
                if runtime_document_path is None:
                    raise RestoreMaterializationError(
                        "Ein Managed Document besitzt keinen technischen Runtime-Pfad."
                    )
                document_targets[item.record_id] = str(runtime_document_path)
        _verify_materialized_inventory(
            paths.prepared_documents,
            manifest,
            targets,
        )
        return document_targets

    @staticmethod
    def _rebase_managed_documents(
        database_path: Path,
        document_targets: dict[str, str],
    ) -> None:
        try:
            with closing(sqlite3.connect(database_path, isolation_level=None)) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                external_before = {
                    str(row[0]): str(row[1])
                    for row in connection.execute(
                        "SELECT document_id, file_path FROM documents ORDER BY document_id"
                    ).fetchall()
                    if str(row[0]) not in document_targets
                }
                connection.execute("BEGIN IMMEDIATE")
                try:
                    RestoreStagingService._apply_document_rebase(
                        connection,
                        document_targets,
                    )
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
                external_after = {
                    str(row[0]): str(row[1])
                    for row in connection.execute(
                        "SELECT document_id, file_path FROM documents ORDER BY document_id"
                    ).fetchall()
                    if str(row[0]) not in document_targets
                }
                if external_after != external_before:
                    raise RestoreMaterializationError(
                        "Externe Dokumentreferenzen wurden beim Rebase veraendert."
                    )
        except RestoreError:
            raise
        except sqlite3.Error as error:
            raise RestoreMaterializationError(
                f"Das Staging-Pfad-Rebasing ist fehlgeschlagen: {error}"
            ) from error
        _verify_sqlite(database_path, RestoreMaterializationError)

    @staticmethod
    def _apply_document_rebase(
        connection: sqlite3.Connection,
        document_targets: dict[str, str],
    ) -> None:
        for document_id, target in sorted(document_targets.items()):
            cursor = connection.execute(
                "UPDATE documents SET file_path = ? WHERE document_id = ?",
                (target, document_id),
            )
            if cursor.rowcount != 1:
                raise RestoreMaterializationError(
                    "Eine Managed-Document-ID fehlt in der Staging-Datenbank."
                )

    def _verify_prepared_payload(
        self,
        *,
        paths: RestoreStagingPaths,
        manifest: BackupManifest,
        live_documents: Path,
        source_preview: RestorePreview,
    ) -> tuple[RestoreCompatibility, RestorePreview]:
        _verify_sqlite(paths.prepared_database, RestoreIntegrityError)
        result = self.compatibility_inspector.inspect(paths.prepared_database)
        if (
            result.status is not DatabaseCompatibilityStatus.EXACT
            or result.version.sqlite_user_version != FINAL_SCHEMA_VERSION
            or result.schema_identity.fingerprint != FINAL_SCHEMA_FINGERPRINT
        ):
            raise RestoreCompatibilityError(
                "Das Prepared-Staging entspricht nicht exakt Final-V3."
            )
        source_rows = _database_rows(paths.source_database)
        prepared_rows = _database_rows(paths.prepared_database)
        targets = _managed_file_targets(
            database_path=paths.prepared_database,
            manifest=manifest,
            prepared_documents=paths.prepared_documents,
            live_documents=live_documents,
        )
        document_targets = {
            item.record_id: str(targets[(item.kind, item.record_id)][1])
            for item in manifest.managed_files
            if item.kind == "document"
        }
        _assert_database_preserved_after_rebase(
            source_rows,
            prepared_rows,
            document_targets,
        )
        counts = RestoreVerifier._verify_database(paths.prepared_database)
        if counts != manifest.counts:
            raise RestoreIntegrityError(
                "Die Prepared-Counts stimmen nicht mit dem Manifest ueberein."
            )
        _verify_materialized_inventory(
            paths.prepared_documents,
            manifest,
            targets,
        )
        compatibility = RestoreCompatibility(
            status=result.status,
            database_compatibility_version=FINAL_SCHEMA_VERSION,
            sqlite_user_version=result.version.sqlite_user_version,
            schema_fingerprint=result.schema_identity.fingerprint,
        )
        preview = RestorePreview(
            created_at=source_preview.created_at,
            app_version=source_preview.app_version,
            backup_format_version=source_preview.backup_format_version,
            database_compatibility_version=FINAL_SCHEMA_VERSION,
            sqlite_user_version=FINAL_SCHEMA_VERSION,
            compatibility_status=DatabaseCompatibilityStatus.EXACT,
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

    def _initial_state(
        self,
        *,
        restore_id: str,
        archive_sha256: str,
        archive_size: int,
        manifest: BackupManifest,
        compatibility: RestoreCompatibility,
    ) -> dict[str, object]:
        timestamp = _utc_timestamp(self.now())
        return {
            "archive_sha256": archive_sha256,
            "archive_size_bytes": archive_size,
            "backup_format_version": manifest.backup_format_version,
            "counts": {
                **manifest.counts.to_dict(),
                "external_references": manifest.external_references.count,
                "managed_files": len(manifest.managed_files),
            },
            "database_compatibility_status": compatibility.status.value,
            "phase": "source_extracted",
            "restore_id": restore_id,
            "source_user_version": compatibility.sqlite_user_version,
            "staging_state_version": 1,
            "target_user_version": FINAL_SCHEMA_VERSION,
            "timestamps": {
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        }

    def _set_phase(
        self,
        state: dict[str, object],
        phase: str,
        *,
        completed: bool = False,
        failed: bool = False,
    ) -> dict[str, object]:
        if phase not in _KNOWN_PHASES:
            raise RestoreStateError("Unbekannte technische Restore-Phase.")
        updated = json.loads(json.dumps(state))
        timestamp = _utc_timestamp(self.now())
        updated["phase"] = phase
        timestamps = updated["timestamps"]
        if not isinstance(timestamps, dict):
            raise RestoreStateError("Der technische Staging-State ist widerspruechlich.")
        timestamps["updated_at"] = timestamp
        if completed:
            timestamps["completed_at"] = timestamp
        if failed:
            timestamps["failed_at"] = timestamp
        return updated


class RestoreSafetyBackupService:
    """Create one verified safety backup for a prepared restore id."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        sqlite_engine: SQLiteBackupEngine | None = None,
        verifier: BackupVerifier | None = None,
    ) -> None:
        self.now = now or (lambda: datetime.now(UTC))
        self.sqlite_engine = sqlite_engine
        self.verifier = verifier or BackupVerifier()

    def create(
        self,
        *,
        restore_id: str,
        runtime_root: Path,
        database_path: Path,
        documents_root: Path,
        backups_root: Path,
        app_version: str,
        build_commit: str,
        source_tree_state: str | None,
    ) -> RestoreSafetyBackupResult:
        restore_id = _validated_restore_id(restore_id)
        runtime_root = _absolute_without_resolving(Path(runtime_root))
        database_path = _absolute_without_resolving(Path(database_path))
        documents_root = _absolute_without_resolving(Path(documents_root))
        backups_root = _absolute_without_resolving(Path(backups_root))
        staging_root = runtime_root / RESTORE_STAGING_DIRECTORY
        target = backups_root / RESTORE_SAFETY_DIRECTORY / restore_id
        target = _absolute_without_resolving(target)
        if (
            not database_path.is_relative_to(runtime_root)
            or not documents_root.is_relative_to(runtime_root)
            or not backups_root.is_relative_to(runtime_root)
            or backups_root == runtime_root
        ):
            raise RestoreSafetyBackupError(
                "Die injizierten Runtime-Pfade sind nicht konsistent."
            )
        if target.exists():
            raise RestoreSafetyBackupError(
                "Der Zielbereich fuer dieses Restore-Sicherheitsbackup existiert bereits."
            )
        if not target.is_relative_to(backups_root):
            raise RestoreSafetyBackupError(
                "Der Sicherheitsbackup-Pfad liegt ausserhalb des Backup-Bereichs."
            )
        if (
            _paths_overlap(target, documents_root)
            or _paths_overlap(target, staging_root)
            or target == database_path
        ):
            raise RestoreSafetyBackupError(
                "Live-, Staging- und Sicherheitsbackup-Pfade sind nicht disjunkt."
            )
        try:
            result = BackupService(
                database_path=database_path,
                data_root=runtime_root,
                documents_root=documents_root,
                target_directory=target,
                app_version=app_version,
                build_commit=build_commit,
                source_tree_state=source_tree_state,
                now=self.now,
                sqlite_engine=self.sqlite_engine,
                verifier=self.verifier,
            ).create_backup()
            verification = self.verifier.verify_backup(result.path)
        except BackupError as error:
            raise RestoreSafetyBackupError(
                f"Das Restore-Sicherheitsbackup ist fehlgeschlagen: {error}"
            ) from error
        if (
            verification.archive_sha256
            != result.verification.archive_sha256
            or verification.archive_size_bytes
            != result.verification.archive_size_bytes
        ):
            raise RestoreSafetyBackupError(
                "Das Sicherheitsbackup widerspricht seiner Abschlusspruefung."
            )
        return RestoreSafetyBackupResult(
            restore_id=restore_id,
            path=result.path,
            archive_sha256=verification.archive_sha256,
            archive_size_bytes=verification.archive_size_bytes,
            verified=True,
        )


def _validated_restore_id(value: str) -> str:
    if not isinstance(value, str) or not _RESTORE_ID_PATTERN.fullmatch(value):
        raise RestoreStateError("Die technische Restore-ID ist ungueltig.")
    return value


def _staging_paths(runtime_root: Path, restore_id: str) -> RestoreStagingPaths:
    root = _absolute_without_resolving(Path(runtime_root))
    staging = root / RESTORE_STAGING_DIRECTORY / restore_id
    source = staging / RESTORE_SOURCE_DIRECTORY
    prepared = staging / RESTORE_PREPARED_DIRECTORY
    return RestoreStagingPaths(
        root=staging,
        source=source,
        source_database=source.joinpath(
            *PurePosixPath(DATABASE_ARCHIVE_PATH).parts
        ),
        prepared=prepared,
        prepared_database=prepared / "kompetenzmanager.sqlite",
        prepared_documents=prepared / "documents",
        state=staging / RESTORE_STATE_FILENAME,
    )


def _validate_staging_boundaries(
    *,
    runtime_root: Path,
    staging_root: Path,
    live_database: Path,
    live_documents: Path,
) -> None:
    runtime_root = _absolute_without_resolving(runtime_root)
    staging_root = _absolute_without_resolving(staging_root)
    if (
        not live_database.is_relative_to(runtime_root)
        or not live_documents.is_relative_to(runtime_root)
        or live_documents == runtime_root
    ):
        raise RestoreStagingError("Die injizierten Runtime-Pfade sind nicht konsistent.")
    if not staging_root.is_relative_to(runtime_root) or staging_root == runtime_root:
        raise RestoreStagingError(
            "Der technische Restore-Bereich liegt ausserhalb der Runtime-Wurzel."
        )
    if (
        staging_root == live_database
        or _paths_overlap(staging_root, live_documents)
        or live_database.is_relative_to(staging_root)
    ):
        raise RestoreStagingError(
            "Restore-Staging und produktive Datenpfade sind nicht disjunkt."
        )


def _check_staging_free_space(runtime_root: Path, *, manifest: BackupManifest) -> None:
    required = 10 * 1024 * 1024
    required += manifest.database.size_bytes * 2
    required += sum(item.size_bytes for item in manifest.managed_files) * 2
    try:
        free = shutil.disk_usage(runtime_root).free
    except OSError as error:
        raise RestoreStagingError(
            "Der freie Speicher fuer das Restore-Staging ist nicht bestimmbar."
        ) from error
    if free < required:
        raise RestoreStagingError(
            "In der Runtime-Datenwurzel ist nicht genug Speicher fuer das Restore-Staging."
        )


def _paths_overlap(first: Path, second: Path) -> bool:
    first = _absolute_without_resolving(first)
    second = _absolute_without_resolving(second)
    return (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    )


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_real_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RestoreStagingError(
            "Ein erforderliches Restore-Verzeichnis ist nicht lesbar."
        ) from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RestoreStagingError(
            "Ein Restore-Verzeichnis ist ein Symlink oder Sonderpfad."
        )


def _harden_tree(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts)):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise RestoreIntegrityError("Symlinks sind im Restore-Staging nicht erlaubt.")
        if stat.S_ISDIR(metadata.st_mode):
            os.chmod(path, 0o700)
        elif stat.S_ISREG(metadata.st_mode):
            os.chmod(path, 0o600)
        else:
            raise RestoreIntegrityError(
                "Sonderdateien sind im Restore-Staging nicht erlaubt."
            )
    os.chmod(root, 0o700)


def _copy_verified_file(
    source: Path,
    target: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    allowed_root: Path,
) -> None:
    source_size, source_hash = _size_and_sha256_path(source)
    if (source_size, source_hash) != (expected_size, expected_sha256):
        raise RestoreMaterializationError(
            "Eine Restore-Quelldatei stimmt nicht mit dem Manifest ueberein."
    )
    try:
        _prepare_safe_parent(allowed_root, target)
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as source_file, target.open("xb") as target_file:
            while chunk := source_file.read(_COPY_CHUNK_SIZE):
                target_file.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            target_file.flush()
            os.fsync(target_file.fileno())
        os.chmod(target, 0o600)
    except FileExistsError as error:
        raise RestoreMaterializationError(
            "Ein Materialisierungsziel existiert bereits."
        ) from error
    except OSError as error:
        target.unlink(missing_ok=True)
        raise RestoreMaterializationError(
            f"Eine Managed File konnte nicht materialisiert werden: {error}"
        ) from error
    if (size, digest.hexdigest()) != (expected_size, expected_sha256):
        target.unlink(missing_ok=True)
        raise RestoreMaterializationError(
            "Eine materialisierte Datei besitzt falsche Groesse oder SHA-256."
        )
    final_size, final_hash = _size_and_sha256_path(target)
    if (final_size, final_hash) != (expected_size, expected_sha256):
        target.unlink(missing_ok=True)
        raise RestoreMaterializationError(
            "Eine materialisierte Datei wurde nach dem Schreiben veraendert."
        )


def _prepare_safe_parent(allowed_root: Path, target: Path) -> None:
    allowed_root = _absolute_without_resolving(allowed_root)
    target = _absolute_without_resolving(target)
    if not target.is_relative_to(allowed_root) or target == allowed_root:
        raise RestoreMaterializationError(
            "Ein Materialisierungsziel verlaesst seine erlaubte Wurzel."
        )
    _assert_real_directory(allowed_root)
    current = allowed_root
    for component in target.parent.relative_to(allowed_root).parts:
        current = current / component
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RestoreMaterializationError(
                "Ein Materialisierungspfad enthaelt einen Symlink oder Sonderpfad."
            )
        os.chmod(current, 0o700)


def _managed_file_targets(
    *,
    database_path: Path,
    manifest: BackupManifest,
    prepared_documents: Path,
    live_documents: Path,
) -> dict[tuple[str, str], tuple[Path, Path | None]]:
    targets: dict[tuple[str, str], tuple[Path, Path | None]] = {}
    prepared_documents = _absolute_without_resolving(prepared_documents)
    live_documents = _absolute_without_resolving(live_documents)
    try:
        with closing(_open_read_only_database(database_path)) as connection:
            for item in manifest.managed_files:
                extension = PurePosixPath(item.archive_path).suffix.lower()
                if item.kind == "document":
                    exists = connection.execute(
                        "SELECT 1 FROM documents WHERE document_id = ?",
                        (item.record_id,),
                    ).fetchone()
                    if exists is None:
                        raise RestoreMaterializationError(
                            "Eine Managed-Document-ID fehlt in der Staging-Datenbank."
                        )
                    relative = Path("managed") / item.record_id / (
                        item.record_id + extension
                    )
                    target = prepared_documents / relative
                    runtime_path: Path | None = live_documents / relative
                elif item.kind == "learning_report_pdf":
                    target = _pdf_target(
                        connection=connection,
                        table="learning_report_pdf_artifacts",
                        id_column="learning_report_pdf_artifact_id",
                        record_id=item.record_id,
                        kind=item.kind,
                        expected_size=item.size_bytes,
                        expected_sha256=item.sha256,
                        prepared_documents=prepared_documents,
                    )
                    runtime_path = None
                elif item.kind == "learning_conference_pdf":
                    target = _pdf_target(
                        connection=connection,
                        table="learning_conference_pdf_artifacts",
                        id_column="learning_conference_pdf_artifact_id",
                        record_id=item.record_id,
                        kind=item.kind,
                        expected_size=item.size_bytes,
                        expected_sha256=item.sha256,
                        prepared_documents=prepared_documents,
                    )
                    runtime_path = None
                else:  # pragma: no cover - BackupVerifier rejects this earlier
                    raise RestoreMaterializationError("Unbekannte Managed-File-Art.")
                target = _absolute_without_resolving(target)
                if not target.is_relative_to(prepared_documents):
                    raise RestoreMaterializationError(
                        "Ein Managed-File-Ziel verlaesst prepared/documents."
                    )
                if target in (value[0] for value in targets.values()):
                    raise RestoreMaterializationError(
                        "Mehrere Managed Files besitzen dasselbe Materialisierungsziel."
                    )
                targets[(item.kind, item.record_id)] = (target, runtime_path)
    except RestoreError:
        raise
    except sqlite3.Error as error:
        raise RestoreMaterializationError(
            f"Die Managed-File-Ziele konnten nicht gelesen werden: {error}"
        ) from error
    return targets


def _pdf_target(
    *,
    connection: sqlite3.Connection,
    table: str,
    id_column: str,
    record_id: str,
    kind: str,
    expected_size: int,
    expected_sha256: str,
    prepared_documents: Path,
) -> Path:
    if kind == "learning_report_pdf":
        row = connection.execute(
            f"SELECT artifact.relative_file_path, artifact.mime_type, "
            f"artifact.file_size_bytes, artifact.pdf_sha256, report.student_id, "
            f"report.learning_report_id, revision.learning_report_revision_id "
            f"FROM {table} AS artifact "
            "JOIN learning_report_revisions AS revision "
            "ON revision.learning_report_revision_id = "
            "artifact.learning_report_revision_id "
            "JOIN learning_reports AS report "
            "ON report.learning_report_id = revision.learning_report_id "
            f"WHERE artifact.{id_column} = ?",
            (record_id,),
        ).fetchone()
    else:
        row = connection.execute(
            f"SELECT artifact.relative_file_path, artifact.mime_type, "
            f"artifact.file_size_bytes, artifact.pdf_sha256, conference.student_id, "
            f"conference.learning_conference_id, "
            f"revision.learning_conference_revision_id "
            f"FROM {table} AS artifact "
            "JOIN learning_conference_revisions AS revision "
            "ON revision.learning_conference_revision_id = "
            "artifact.learning_conference_revision_id "
            "JOIN learning_conferences AS conference "
            "ON conference.learning_conference_id = revision.learning_conference_id "
            f"WHERE artifact.{id_column} = ?",
            (record_id,),
        ).fetchone()
    if row is None:
        raise RestoreMaterializationError(
            "Eine finale PDF-Artefakt-ID fehlt in der Staging-Datenbank."
        )
    (
        relative_value,
        mime_type,
        stored_size,
        stored_hash,
        student_id,
        aggregate_id,
        revision_id,
    ) = row
    if mime_type != "application/pdf" or int(stored_size) != expected_size:
        raise RestoreMaterializationError(
            "Die technischen PDF-Metadaten widersprechen dem Manifest."
        )
    if str(stored_hash) != expected_sha256:
        raise RestoreMaterializationError(
            "Der gespeicherte PDF-Hash widerspricht dem Manifest."
        )
    relative = _safe_relative_path(relative_value)
    parts = relative.parts
    expected_scope = (
        "reports" if kind == "learning_report_pdf" else "learning_conferences"
    )
    if (
        len(parts) < 6
        or parts[0] != "documents"
        or parts[1] != str(student_id)
        or parts[2] != expected_scope
        or parts[3] != str(aggregate_id)
        or parts[4] != str(revision_id)
        or relative.suffix.lower() != ".pdf"
    ):
        raise RestoreMaterializationError(
            "Ein finaler PDF-Pfad verletzt den registrierten relativen Vertrag."
        )
    return prepared_documents.joinpath(*parts[1:])


def _safe_relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RestoreMaterializationError("Ein relativer Artefaktpfad ist ungueltig.")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RestoreMaterializationError("Ein relativer Artefaktpfad ist ungueltig.")
    return path


def _verify_materialized_inventory(
    prepared_documents: Path,
    manifest: BackupManifest,
    targets: dict[tuple[str, str], tuple[Path, Path | None]],
) -> None:
    expected = {value[0] for value in targets.values()}
    actual: set[Path] = set()
    if prepared_documents.exists():
        for path in prepared_documents.rglob("*"):
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise RestoreMaterializationError(
                    "Ein Symlink liegt im vorbereiteten Dokumentinventar."
                )
            if stat.S_ISREG(metadata.st_mode):
                actual.add(_absolute_without_resolving(path))
            elif not stat.S_ISDIR(metadata.st_mode):
                raise RestoreMaterializationError(
                    "Eine Sonderdatei liegt im vorbereiteten Dokumentinventar."
                )
    if actual != expected:
        raise RestoreMaterializationError(
            "prepared/documents enthaelt nicht exakt das verifizierte Inventar."
        )
    manifest_by_key = {
        (item.kind, item.record_id): item for item in manifest.managed_files
    }
    for key, (path, _runtime_path) in targets.items():
        item = manifest_by_key[key]
        size, sha256 = _size_and_sha256_path(path)
        if (size, sha256) != (item.size_bytes, item.sha256):
            raise RestoreMaterializationError(
                "Eine vorbereitete Managed File stimmt nicht mit dem Manifest ueberein."
            )


def _database_rows(path: Path) -> dict[str, object]:
    try:
        with closing(_open_read_only_database(path)) as connection:
            return _database_rows_from_connection(connection)
    except sqlite3.Error as error:
        raise RestoreIntegrityError(
            f"Die Staging-Datenwerte konnten nicht gelesen werden: {error}"
        ) from error


def _database_rows_from_connection(
    connection: sqlite3.Connection,
) -> dict[str, object]:
    result: dict[str, object] = {}
    table_names = [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    for table in table_names:
        quoted = '"' + table.replace('"', '""') + '"'
        columns = [
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({quoted})").fetchall()
        ]
        rows = [
            [_normalized_sql_value(value) for value in row]
            for row in connection.execute(f"SELECT * FROM {quoted}").fetchall()
        ]
        rows.sort(key=_canonical_bytes)
        result[table] = {"columns": columns, "rows": rows}
    return result


def _normalized_sql_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"blob_hex": value.hex()}
    if value is None or isinstance(value, (str, int, float)):
        return value
    return {"repr": repr(value)}


def _assert_database_preserved_after_rebase(
    source: dict[str, object],
    prepared: dict[str, object],
    document_targets: dict[str, str],
) -> None:
    source_tables = set(source) - {"persistence_events"}
    prepared_tables = set(prepared) - {"persistence_events"}
    if source_tables != prepared_tables:
        raise RestoreIntegrityError("Tabellenbestand wurde im Prepared-Staging veraendert.")
    for table in source_tables:
        if table != "documents":
            if source[table] != prepared[table]:
                raise RestoreIntegrityError(
                    f"Datenwerte der Tabelle {table} wurden im Staging veraendert."
                )
            continue
        source_table = source[table]
        prepared_table = prepared[table]
        if not isinstance(source_table, dict) or not isinstance(prepared_table, dict):
            raise RestoreIntegrityError("Dokumentmetadaten sind nicht pruefbar.")
        columns = source_table.get("columns")
        if columns != prepared_table.get("columns") or not isinstance(columns, list):
            raise RestoreIntegrityError("Dokumentschema wurde im Staging veraendert.")
        document_index = columns.index("document_id")
        path_index = columns.index("file_path")
        source_rows = {
            str(row[document_index]): row for row in source_table.get("rows", [])
        }
        prepared_rows = {
            str(row[document_index]): row for row in prepared_table.get("rows", [])
        }
        if set(source_rows) != set(prepared_rows):
            raise RestoreIntegrityError("Dokument-IDs wurden im Staging veraendert.")
        for document_id, source_row in source_rows.items():
            prepared_row = prepared_rows[document_id]
            expected_path = document_targets.get(document_id, source_row[path_index])
            for index, value in enumerate(source_row):
                expected = expected_path if index == path_index else value
                if prepared_row[index] != expected:
                    raise RestoreIntegrityError(
                        "Dokumentmetadaten wurden ausserhalb des erlaubten Rebase veraendert."
                    )


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _verify_sqlite(path: Path, error_type: type[RestoreError]) -> None:
    try:
        with closing(_open_read_only_database(path)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            if integrity != [("ok",)]:
                raise error_type("SQLite integrity_check ist fehlgeschlagen.")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise error_type("SQLite foreign_key_check ist fehlgeschlagen.")
    except RestoreError:
        raise
    except sqlite3.Error as error:
        raise error_type(f"Die Staging-Datenbank ist beschaedigt: {error}") from error


def _write_staging_state(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{RESTORE_STATE_FILENAME}.tmp")
    data = _canonical_bytes(payload)
    try:
        with temporary.open("xb") as state_file:
            state_file.write(data)
            state_file.flush()
            os.fsync(state_file.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _read_staging_state(path: Path, restore_id: str) -> dict[str, object]:
    try:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise RestoreStateError("Der Staging-State ist keine regulaere Datei.")
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except RestoreError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RestoreStateError("Der Staging-State ist nicht lesbar.") from error
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise RestoreStateError("Der Staging-State ist nicht kanonisch.")
    required = {
        "archive_sha256",
        "archive_size_bytes",
        "backup_format_version",
        "counts",
        "database_compatibility_status",
        "phase",
        "restore_id",
        "source_user_version",
        "staging_state_version",
        "target_user_version",
        "timestamps",
    }
    if set(payload) != required or payload.get("restore_id") != restore_id:
        raise RestoreStateError("Der Staging-State gehoert nicht zur Restore-ID.")
    if payload.get("phase") not in _KNOWN_PHASES:
        raise RestoreStateError("Der Staging-State besitzt eine unbekannte Phase.")
    archive_hash = payload.get("archive_sha256")
    if (
        not isinstance(archive_hash, str)
        or len(archive_hash) != 64
        or any(character not in "0123456789abcdef" for character in archive_hash)
    ):
        raise RestoreStateError("Der Staging-State besitzt keinen gueltigen Archivhash.")
    for key in (
        "archive_size_bytes",
        "backup_format_version",
        "source_user_version",
        "staging_state_version",
        "target_user_version",
    ):
        value = payload.get(key)
        if type(value) is not int or value < 0:
            raise RestoreStateError("Der Staging-State besitzt ungueltige Versionen.")
    counts = payload.get("counts")
    expected_count_keys = {
        "external_references",
        "learning_conference_revisions",
        "learning_report_revisions",
        "managed_files",
        "observations",
        "students",
    }
    if not isinstance(counts, dict) or set(counts) != expected_count_keys:
        raise RestoreStateError("Der Staging-State besitzt ungueltige Counts.")
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise RestoreStateError("Der Staging-State besitzt ungueltige Counts.")
    timestamps = payload.get("timestamps")
    if not isinstance(timestamps, dict) or not {"created_at", "updated_at"}.issubset(
        timestamps
    ):
        raise RestoreStateError("Der Staging-State besitzt ungueltige Zeitpunkte.")
    phase = payload["phase"]
    if phase == "completed" and "completed_at" not in timestamps:
        raise RestoreStateError("Ein abgeschlossener Staging-State ist unvollstaendig.")
    if phase == "failed" and "failed_at" not in timestamps:
        raise RestoreStateError("Ein fehlgeschlagener Staging-State ist unvollstaendig.")
    return payload


def _assert_state_matches_source(
    state: dict[str, object],
    manifest: BackupManifest,
    compatibility: RestoreCompatibility,
) -> None:
    expected_counts = {
        **manifest.counts.to_dict(),
        "external_references": manifest.external_references.count,
        "managed_files": len(manifest.managed_files),
    }
    if (
        state.get("backup_format_version") != manifest.backup_format_version
        or state.get("database_compatibility_status")
        != compatibility.status.value
        or state.get("source_user_version") != compatibility.sqlite_user_version
        or state.get("target_user_version") != FINAL_SCHEMA_VERSION
        or state.get("staging_state_version") != 1
        or state.get("counts") != expected_counts
    ):
        raise RestoreStateError(
            "Der Staging-State widerspricht der verifizierten Restore-Quelle."
        )


def _utc_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise RestoreStateError("Die technische Zeitquelle ist ungueltig.")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


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
