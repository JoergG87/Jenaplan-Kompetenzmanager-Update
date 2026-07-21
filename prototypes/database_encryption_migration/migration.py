"""Fail-closed plaintext-to-SQLCipher migration prototype.

This module is deliberately outside the product runtime.  It refuses every
source that does not carry the synthetic Security Sprint 4 fixture guard.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from enum import Enum
import hashlib
import math
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import struct
import time
from typing import Any, Callable

from src.core.database_engine import SQLCipherConnectionProvider

from .synthetic_data import (
    SYNTHETIC_APPLICATION_ID,
    SYNTHETIC_GUARD_TABLE,
    SYNTHETIC_GUARD_VALUE,
    SYNTHETIC_USER_VERSION,
)


class MigrationPrototypeError(RuntimeError):
    """Sanitized prototype failure without paths, SQL, or key material."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FailurePoint(str, Enum):
    BACKUP = "backup"
    EXPORT = "export"
    COMMIT = "commit"
    CORRUPT_TARGET = "corrupt_target"
    WRONG_KEY = "wrong_key"
    INTERRUPT_EXPORT = "interrupt_export"


@dataclass(frozen=True)
class MigrationPaths:
    root: Path
    source: Path
    backup: Path
    target: Path

    @classmethod
    def in_workspace(cls, root: Path, *, run_name: str = "run-1") -> "MigrationPaths":
        workspace = Path(root)
        if not run_name or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in run_name):
            raise ValueError("migration_run_name_invalid")
        return cls(
            root=workspace,
            source=workspace / "synthetic-source.sqlite",
            backup=workspace / f"{run_name}-verified-backup.sqlite",
            target=workspace / f"{run_name}-encrypted.sqlcipher",
        )


@dataclass(frozen=True)
class DatabaseSnapshot:
    tables: tuple[str, ...]
    row_counts: dict[str, int]
    primary_keys: dict[str, tuple[tuple[int, str], ...]]
    foreign_keys: dict[str, tuple[tuple[Any, ...], ...]]
    triggers: tuple[tuple[str, str, str], ...]
    views: tuple[tuple[str, str], ...]
    indexes: tuple[tuple[str, str, str], ...]
    pragmas: dict[str, str]
    schema_hash: str
    table_hashes: dict[str, str]
    data_hash: str


@dataclass(frozen=True)
class ValidationResult:
    table_count: int
    total_rows: int
    schema_hash: str
    data_hash: str
    tables_match: bool
    row_counts_match: bool
    primary_keys_match: bool
    foreign_keys_match: bool
    triggers_match: bool
    views_match: bool
    indexes_match: bool
    pragmas_match: bool
    schema_hash_match: bool
    data_hash_match: bool

    @property
    def successful(self) -> bool:
        return all(
            (
                self.tables_match,
                self.row_counts_match,
                self.primary_keys_match,
                self.foreign_keys_match,
                self.triggers_match,
                self.views_match,
                self.indexes_match,
                self.pragmas_match,
                self.schema_hash_match,
                self.data_hash_match,
            )
        )


@dataclass(frozen=True)
class PerformanceMetrics:
    source_size_bytes: int
    backup_size_bytes: int
    encrypted_size_bytes: int
    source_integrity_seconds: float
    backup_seconds: float
    export_seconds: float
    validation_seconds: float
    reopen_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class MigrationReport:
    validation: ValidationResult
    performance: PerformanceMetrics
    source_sha256_before: str
    source_sha256_after: str
    backup_sha256: str
    successful_reopen: bool
    rollback_required: bool


@dataclass(frozen=True)
class AtomicExchangeSimulation:
    performed: bool
    steps: tuple[str, ...]
    recovery_rule: str


def simulate_atomic_exchange() -> AtomicExchangeSimulation:
    """Describe the later exchange without renaming, replacing, or deleting."""

    return AtomicExchangeSimulation(
        performed=False,
        steps=(
            "exclusive application lock and verified source identity",
            "fsync encrypted candidate and containing directory",
            "rename plaintext source to a retained rollback name",
            "atomically replace the live name with the encrypted candidate",
            "fsync containing directory and reopen through SQLCipher",
            "retain rollback source until an explicit later disposal decision",
        ),
        recovery_rule=(
            "A durable migration journal must select exactly one complete file at "
            "startup; this prototype performs no exchange."
        ),
    )


class MigrationPrototypeEngine:
    """Migrate one guarded synthetic fixture into one separate SQLCipher file."""

    def __init__(self, provider: SQLCipherConnectionProvider | None = None) -> None:
        self._provider = provider or SQLCipherConnectionProvider()

    def migrate(
        self,
        paths: MigrationPaths,
        *,
        key_material: bytes | bytearray | memoryview,
        failure_point: FailurePoint | None = None,
        phase_observer: Callable[[str, MigrationPaths], None] | None = None,
    ) -> MigrationReport:
        started = time.perf_counter()
        _validate_workspace_paths(paths)
        if paths.backup.exists() or paths.backup.is_symlink():
            raise MigrationPrototypeError("migration_backup_target_exists")
        if paths.target.exists() or paths.target.is_symlink():
            raise MigrationPrototypeError("migration_encrypted_target_exists")
        source_before = _sha256_file(paths.source)
        target_identity: tuple[int, int] | None = None
        backup_created = False
        source_integrity_seconds = 0.0
        backup_seconds = 0.0
        export_seconds = 0.0
        validation_seconds = 0.0
        reopen_seconds = 0.0
        try:
            _notify(phase_observer, "preflight_started", paths)
            integrity_started = time.perf_counter()
            with closing(_open_plaintext_read_only(paths.source)) as source:
                _require_guarded_synthetic_source(source)
                _verify_plaintext_integrity(source)
                source_snapshot = _snapshot(source)
            source_integrity_seconds = time.perf_counter() - integrity_started
            _notify(phase_observer, "source_verified", paths)

            _notify(phase_observer, "backup_started", paths)
            backup_started = time.perf_counter()
            self._create_verified_backup(
                paths,
                source_snapshot,
                fail=failure_point is FailurePoint.BACKUP,
                phase_observer=phase_observer,
            )
            backup_created = True
            backup_seconds = time.perf_counter() - backup_started
            _notify(phase_observer, "backup_verified", paths)

            _notify(phase_observer, "target_creation_started", paths)
            export_started = time.perf_counter()
            target_identity = self._export_to_encrypted_target(
                paths,
                key_material=key_material,
                failure_point=failure_point,
                phase_observer=phase_observer,
            )
            export_seconds = time.perf_counter() - export_started

            if failure_point is FailurePoint.CORRUPT_TARGET:
                _corrupt_encrypted_target(paths.target)

            reopen_key: bytes | bytearray | memoryview = key_material
            wrong_key: bytearray | None = None
            if failure_point is FailurePoint.WRONG_KEY:
                wrong_key = bytearray(secrets.token_bytes(32))
                reopen_key = wrong_key
            try:
                _notify(phase_observer, "validation_started", paths)
                validation_started = time.perf_counter()
                with closing(
                    self._provider.connect(
                        paths.target,
                        create=False,
                        key_material=reopen_key,
                    )
                ) as target:
                    _notify(phase_observer, "validation_in_progress", paths)
                    target_snapshot = _snapshot(target)
                    validation = _compare_snapshots(source_snapshot, target_snapshot)
                validation_seconds = time.perf_counter() - validation_started
                _notify(phase_observer, "validation_completed", paths)
                reopen_started = time.perf_counter()
                _notify(phase_observer, "reopen_started", paths)
                with closing(
                    self._provider.connect(
                        paths.target,
                        create=False,
                        key_material=reopen_key,
                    )
                ):
                    pass
                reopen_seconds = time.perf_counter() - reopen_started
                _notify(phase_observer, "reopen_verified", paths)
            finally:
                if wrong_key is not None:
                    _erase(wrong_key)
            if not validation.successful:
                raise MigrationPrototypeError("migration_validation_failed")
            source_after = _sha256_file(paths.source)
            if source_after != source_before:
                raise MigrationPrototypeError("migration_source_changed")
            return MigrationReport(
                validation=validation,
                performance=PerformanceMetrics(
                    source_size_bytes=paths.source.stat().st_size,
                    backup_size_bytes=paths.backup.stat().st_size,
                    encrypted_size_bytes=paths.target.stat().st_size,
                    source_integrity_seconds=source_integrity_seconds,
                    backup_seconds=backup_seconds,
                    export_seconds=export_seconds,
                    validation_seconds=validation_seconds,
                    reopen_seconds=reopen_seconds,
                    total_seconds=time.perf_counter() - started,
                ),
                source_sha256_before=source_before,
                source_sha256_after=source_after,
                backup_sha256=_sha256_file(paths.backup),
                successful_reopen=True,
                rollback_required=False,
            )
        except Exception as error:
            if target_identity is not None:
                _notify(phase_observer, "rollback_started", paths)
                if not _unlink_same_identity(paths.target, target_identity):
                    raise MigrationPrototypeError(
                        "migration_target_cleanup_blocked"
                    )
                _notify(phase_observer, "rollback_completed", paths)
            self._verify_rollback_state(paths, source_before, backup_created)
            if isinstance(error, MigrationPrototypeError):
                raise
            code = getattr(error, "code", "migration_prototype_failed")
            raise MigrationPrototypeError(str(code)) from None

    def validate(
        self,
        paths: MigrationPaths,
        *,
        key_material: bytes | bytearray | memoryview,
    ) -> ValidationResult:
        """Run the standalone structural and value comparison component."""

        _validate_workspace_paths(paths)
        with closing(_open_plaintext_read_only(paths.source)) as source:
            _require_guarded_synthetic_source(source)
            _verify_plaintext_integrity(source)
            source_snapshot = _snapshot(source)
        with closing(
            self._provider.connect(
                paths.target,
                create=False,
                key_material=key_material,
            )
        ) as target:
            target_snapshot = _snapshot(target)
        return _compare_snapshots(source_snapshot, target_snapshot)

    def _create_verified_backup(
        self,
        paths: MigrationPaths,
        source_snapshot: DatabaseSnapshot,
        *,
        fail: bool,
        phase_observer: Callable[[str, MigrationPaths], None] | None = None,
    ) -> None:
        backup_identity = _reserve_new_file(paths.backup)
        destination = None
        try:
            destination = sqlite3.connect(paths.backup)
            with closing(_open_plaintext_read_only(paths.source)) as source:
                callback_count = 0

                def progress(_status: int, _remaining: int, _total: int) -> None:
                    nonlocal callback_count
                    callback_count += 1
                    if fail and callback_count == 1:
                        raise MigrationPrototypeError("migration_backup_failed")

                source.backup(destination, pages=1, progress=progress)
            destination.commit()
        except Exception:
            if destination is not None:
                destination.close()
            if not _unlink_same_identity(paths.backup, backup_identity):
                raise MigrationPrototypeError(
                    "migration_backup_cleanup_blocked"
                )
            raise
        finally:
            if destination is not None:
                destination.close()
        try:
            _fsync_file(paths.backup)
            _notify(phase_observer, "backup_created", paths)
            with closing(_open_plaintext_read_only(paths.backup)) as backup:
                _require_guarded_synthetic_source(backup)
                _verify_plaintext_integrity(backup)
                backup_snapshot = _snapshot(backup)
            if _compare_snapshots(source_snapshot, backup_snapshot).successful is False:
                raise MigrationPrototypeError("migration_backup_verification_failed")
        except Exception:
            if not _unlink_same_identity(paths.backup, backup_identity):
                raise MigrationPrototypeError(
                    "migration_backup_cleanup_blocked"
                ) from None
            raise

    def _export_to_encrypted_target(
        self,
        paths: MigrationPaths,
        *,
        key_material: bytes | bytearray | memoryview,
        failure_point: FailurePoint | None,
        phase_observer: Callable[[str, MigrationPaths], None] | None = None,
    ) -> tuple[int, int]:
        connection = self._provider.connect(
            paths.target,
            create=True,
            key_material=key_material,
        )
        try:
            target_status = paths.target.lstat()
        except OSError:
            connection.close()
            raise MigrationPrototypeError("migration_target_identity_missing") from None
        if paths.target.is_symlink() or not stat.S_ISREG(target_status.st_mode):
            connection.close()
            raise MigrationPrototypeError("migration_target_identity_invalid")
        target_identity = (target_status.st_dev, target_status.st_ino)
        attached = False
        failure: Exception | None = None
        try:
            _notify(phase_observer, "target_created", paths)
            _notify(phase_observer, "export_started", paths)
            connection.execute("PRAGMA auto_vacuum = FULL")
            source_uri = f"{paths.source.resolve().as_uri()}?mode=ro&immutable=1"
            connection.execute(
                "ATTACH DATABASE ? AS plaintext KEY ''",
                (source_uri,),
            )
            attached = True
            if failure_point is FailurePoint.EXPORT:
                raise MigrationPrototypeError("migration_export_failed")
            if failure_point is FailurePoint.INTERRUPT_EXPORT:
                callbacks = 0

                def interrupt() -> int:
                    nonlocal callbacks
                    callbacks += 1
                    return 1 if callbacks >= 3 else 0

                connection.set_progress_handler(interrupt, 100)
            try:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    _notify(phase_observer, "export_in_progress", paths)
                    connection.execute(
                        "SELECT sqlcipher_export('main', 'plaintext')"
                    ).fetchone()
                except Exception:
                    if failure_point is FailurePoint.INTERRUPT_EXPORT:
                        raise MigrationPrototypeError(
                            "migration_export_interrupted"
                        ) from None
                    raise
                connection.execute(f"PRAGMA application_id = {SYNTHETIC_APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version = {SYNTHETIC_USER_VERSION}")
                if failure_point is FailurePoint.COMMIT:
                    raise MigrationPrototypeError("migration_commit_failed")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.set_progress_handler(None, 0)
            connection.execute("DETACH DATABASE plaintext")
            attached = False
        except Exception as error:
            failure = error
        finally:
            if attached:
                try:
                    connection.execute("DETACH DATABASE plaintext")
                except Exception:
                    pass
            connection.close()
        if failure is not None:
            _notify(phase_observer, "rollback_started", paths)
            if not _unlink_same_identity(paths.target, target_identity):
                raise MigrationPrototypeError(
                    "migration_target_cleanup_blocked"
                )
            _notify(phase_observer, "rollback_completed", paths)
            raise failure
        _fsync_file(paths.target)
        _notify(phase_observer, "export_completed", paths)
        return target_identity

    @staticmethod
    def _verify_rollback_state(
        paths: MigrationPaths,
        source_before: str,
        backup_created: bool,
    ) -> None:
        if _sha256_file(paths.source) != source_before:
            raise MigrationPrototypeError("migration_rollback_source_changed")
        with closing(_open_plaintext_read_only(paths.source)) as source:
            _require_guarded_synthetic_source(source)
            _verify_plaintext_integrity(source)
            source_snapshot = _snapshot(source)
        if backup_created:
            with closing(_open_plaintext_read_only(paths.backup)) as backup:
                _verify_plaintext_integrity(backup)
                backup_snapshot = _snapshot(backup)
            if not _compare_snapshots(source_snapshot, backup_snapshot).successful:
                raise MigrationPrototypeError("migration_rollback_backup_invalid")


def _validate_workspace_paths(paths: MigrationPaths) -> None:
    root = paths.root.resolve()
    if not root.is_dir() or paths.root.is_symlink():
        raise MigrationPrototypeError("migration_workspace_invalid")
    resolved = [candidate.resolve(strict=False) for candidate in (paths.source, paths.backup, paths.target)]
    if len(set(resolved)) != 3:
        raise MigrationPrototypeError("migration_paths_overlap")
    for candidate in resolved:
        if candidate.parent != root:
            raise MigrationPrototypeError("migration_path_outside_workspace")
    if paths.source.is_symlink() or not paths.source.is_file():
        raise MigrationPrototypeError("migration_source_invalid")


def validate_migration_preflight(paths: MigrationPaths) -> None:
    """Validate the isolated synthetic source before any Sprint-5 sidecar write."""

    _validate_workspace_paths(paths)
    if paths.backup.exists() or paths.backup.is_symlink():
        raise MigrationPrototypeError("migration_backup_target_exists")
    if paths.target.exists() or paths.target.is_symlink():
        raise MigrationPrototypeError("migration_encrypted_target_exists")
    with closing(_open_plaintext_read_only(paths.source)) as source:
        _require_guarded_synthetic_source(source)
        _verify_plaintext_integrity(source)


def _notify(
    observer: Callable[[str, MigrationPaths], None] | None,
    phase: str,
    paths: MigrationPaths,
) -> None:
    if observer is not None:
        observer(phase, paths)


def _open_plaintext_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA temp_store = MEMORY")
    return connection


def _require_guarded_synthetic_source(connection: sqlite3.Connection) -> None:
    try:
        row = connection.execute(
            f"SELECT guard_value, fixture_version FROM {SYNTHETIC_GUARD_TABLE}"
        ).fetchone()
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    except sqlite3.Error:
        raise MigrationPrototypeError("migration_source_not_synthetic") from None
    if (
        row is None
        or row[0] != SYNTHETIC_GUARD_VALUE
        or row[1] != 1
        or application_id != SYNTHETIC_APPLICATION_ID
        or user_version != SYNTHETIC_USER_VERSION
    ):
        raise MigrationPrototypeError("migration_source_not_synthetic")


def _verify_plaintext_integrity(connection: sqlite3.Connection) -> None:
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    except sqlite3.Error:
        raise MigrationPrototypeError("migration_plaintext_integrity_failed") from None
    if len(integrity) != 1 or integrity[0][0] != "ok" or foreign_keys:
        raise MigrationPrototypeError("migration_plaintext_integrity_failed")


def _snapshot(connection: Any) -> DatabaseSnapshot:
    table_rows = connection.execute(
        "SELECT name FROM sqlite_schema "
        "WHERE type = 'table' "
        "AND (name NOT LIKE 'sqlite_%' OR name = 'sqlite_sequence') "
        "ORDER BY name"
    ).fetchall()
    tables = tuple(str(row[0]) for row in table_rows)
    row_counts: dict[str, int] = {}
    primary_keys: dict[str, tuple[tuple[int, str], ...]] = {}
    foreign_keys: dict[str, tuple[tuple[Any, ...], ...]] = {}
    table_hashes: dict[str, str] = {}
    for table in tables:
        quoted = _quote_identifier(table)
        info = connection.execute(f"PRAGMA table_info({quoted})").fetchall()
        columns = tuple(str(row[1]) for row in info)
        primary_keys[table] = tuple(
            sorted((int(row[5]), str(row[1])) for row in info if int(row[5]) > 0)
        )
        foreign_keys[table] = tuple(
            sorted(
                tuple(value for value in row)
                for row in connection.execute(f"PRAGMA foreign_key_list({quoted})").fetchall()
            )
        )
        rows = connection.execute(
            f"SELECT {', '.join(_quote_identifier(column) for column in columns)} FROM {quoted}"
        ).fetchall()
        encoded_rows = sorted(_encode_row(row) for row in rows)
        table_digest = hashlib.sha256()
        for encoded in encoded_rows:
            table_digest.update(struct.pack(">Q", len(encoded)))
            table_digest.update(encoded)
        row_counts[table] = len(encoded_rows)
        table_hashes[table] = table_digest.hexdigest()

    schema_rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
        "WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL "
        "ORDER BY type, name"
    ).fetchall()
    normalized_schema = tuple(
        (str(row[0]), str(row[1]), str(row[2]), _normalize_sql(str(row[3])))
        for row in schema_rows
    )
    schema_hash = _hash_repr(normalized_schema)
    triggers = tuple(
        (str(row[1]), str(row[2]), _normalize_sql(str(row[3])))
        for row in schema_rows
        if row[0] == "trigger"
    )
    views = tuple(
        (str(row[1]), _normalize_sql(str(row[3])))
        for row in schema_rows
        if row[0] == "view"
    )
    indexes = tuple(
        (str(row[1]), str(row[2]), _normalize_sql(str(row[3])))
        for row in schema_rows
        if row[0] == "index"
    )
    pragmas = {
        pragma: str(connection.execute(f"PRAGMA {pragma}").fetchone()[0]).lower()
        for pragma in (
            "application_id",
            "user_version",
            "auto_vacuum",
            "encoding",
            "page_size",
        )
    }
    global_data = hashlib.sha256()
    for table in tables:
        global_data.update(table.encode("utf-8"))
        global_data.update(bytes.fromhex(table_hashes[table]))
        global_data.update(str(row_counts[table]).encode("ascii"))
    return DatabaseSnapshot(
        tables=tables,
        row_counts=row_counts,
        primary_keys=primary_keys,
        foreign_keys=foreign_keys,
        triggers=triggers,
        views=views,
        indexes=indexes,
        pragmas=pragmas,
        schema_hash=schema_hash,
        table_hashes=table_hashes,
        data_hash=global_data.hexdigest(),
    )


def _compare_snapshots(
    source: DatabaseSnapshot, target: DatabaseSnapshot
) -> ValidationResult:
    return ValidationResult(
        table_count=len(source.tables),
        total_rows=sum(source.row_counts.values()),
        schema_hash=source.schema_hash,
        data_hash=source.data_hash,
        tables_match=source.tables == target.tables,
        row_counts_match=source.row_counts == target.row_counts,
        primary_keys_match=source.primary_keys == target.primary_keys,
        foreign_keys_match=source.foreign_keys == target.foreign_keys,
        triggers_match=source.triggers == target.triggers,
        views_match=source.views == target.views,
        indexes_match=source.indexes == target.indexes,
        pragmas_match=source.pragmas == target.pragmas,
        schema_hash_match=source.schema_hash == target.schema_hash,
        data_hash_match=(
            source.data_hash == target.data_hash
            and source.table_hashes == target.table_hashes
        ),
    )


def _encode_row(row: Any) -> bytes:
    encoded = bytearray()
    for value in row:
        item = _encode_value(value)
        encoded.extend(struct.pack(">Q", len(item)))
        encoded.extend(item)
    return bytes(encoded)


def _encode_value(value: Any) -> bytes:
    if value is None:
        return b"n"
    if isinstance(value, bool):
        return b"i" + str(int(value)).encode("ascii")
    if isinstance(value, int):
        return b"i" + str(value).encode("ascii")
    if isinstance(value, float):
        if math.isnan(value):
            return b"f-nan" + struct.pack(">d", value)
        return b"f" + struct.pack(">d", value)
    if isinstance(value, str):
        return b"s" + value.encode("utf-8")
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        return b"b" + bytes(value)
    raise MigrationPrototypeError("migration_value_type_unsupported")


def _normalize_sql(statement: str) -> str:
    return " ".join(statement.split())


def _hash_repr(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reserve_new_file(path: Path) -> tuple[int, int]:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        status = os.fstat(descriptor)
        identity = (status.st_dev, status.st_ino)
    finally:
        os.close(descriptor)
    if os.name == "posix":
        os.chmod(path, 0o600)
    return identity


def _corrupt_encrypted_target(path: Path) -> None:
    with path.open("r+b", buffering=0) as stream:
        size = stream.seek(0, os.SEEK_END)
        offset = min(max(64, size // 2), size - 1)
        stream.seek(offset)
        original = stream.read(1)
        stream.seek(offset)
        stream.write(bytes((original[0] ^ 0xFF,)))
        stream.flush()
        os.fsync(stream.fileno())


def _unlink_same_identity(path: Path, identity: tuple[int, int]) -> bool:
    try:
        status = path.lstat()
        if path.is_symlink() or (status.st_dev, status.st_ino) != identity:
            return False
        path.unlink()
        return True
    except OSError:
        return False


def _erase(material: bytearray) -> None:
    for index in range(len(material)):
        material[index] = 0
