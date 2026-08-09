"""Isolated, metadata-only store for the development DMK foundation."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

from ..data_keys import DataKeyset, DataKeysetRuntimePhase, DataKeysetStatus
from ..domain import SecurityStoreError, validate_uuid4
from ..ports import FilePermissionManager


DATA_KEYSET_STORE_SCHEMA_VERSION = 2
_SQLITE_APPLICATION_ID = 0x4A4B4D4B
_EXPECTED_COLUMNS = (
    "key_id",
    "generation",
    "status",
    "fingerprint_sha256",
    "runtime_phase",
    "database_context_id",
)
_SCHEMA_SQL = """
CREATE TABLE data_keysets (
    key_id TEXT PRIMARY KEY,
    generation INTEGER NOT NULL CHECK (generation >= 1),
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'revoked', 'failed')),
    fingerprint_sha256 TEXT NOT NULL CHECK (
        length(fingerprint_sha256) = 64
        AND fingerprint_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    runtime_phase TEXT NOT NULL CHECK (runtime_phase IN (
        'prepared',
        'dmk_published',
        'database_key_generation_started',
        'envelope_published',
        'database_key_active',
        'active'
    )),
    database_context_id TEXT,
    UNIQUE (generation)
) STRICT;

CREATE UNIQUE INDEX one_active_data_keyset
ON data_keysets(status) WHERE status = 'active';
CREATE UNIQUE INDEX one_pending_data_keyset
ON data_keysets(status) WHERE status = 'pending';
"""

_ALLOWED_PENDING_PHASE_TRANSITIONS = {
    DataKeysetRuntimePhase.PREPARED: DataKeysetRuntimePhase.DMK_PUBLISHED,
    DataKeysetRuntimePhase.DMK_PUBLISHED: (
        DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED
    ),
    DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED: (
        DataKeysetRuntimePhase.ENVELOPE_PUBLISHED
    ),
    DataKeysetRuntimePhase.ENVELOPE_PUBLISHED: (
        DataKeysetRuntimePhase.DATABASE_KEY_ACTIVE
    ),
}


class SQLiteDataKeysetRepository:
    """New-store-only repository; it never opens or migrates security.sqlite."""

    def __init__(self, database_path: Path, permissions: FilePermissionManager) -> None:
        self._database_path = Path(database_path)
        self._permissions = permissions

    @property
    def database_path(self) -> Path:
        return self._database_path

    def initialize(self) -> None:
        self._permissions.prepare_directory(self._database_path.parent)
        if self._database_path.exists() or self._database_path.is_symlink():
            self._validate_store()
            return
        try:
            temporary_present = any(
                child.name.startswith(".data-keysets-")
                for child in self._database_path.parent.iterdir()
            )
        except OSError:
            raise SecurityStoreError("data_keyset_store_directory_unreadable") from None
        if temporary_present:
            raise SecurityStoreError("data_keyset_store_temporary_present")
        descriptor, name = tempfile.mkstemp(
            prefix=".data-keysets-", suffix=".sqlite", dir=self._database_path.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        self._permissions.secure_file(temporary)
        try:
            with sqlite3.connect(temporary, isolation_level=None) as connection:
                connection.execute("PRAGMA journal_mode = DELETE")
                connection.execute("PRAGMA synchronous = FULL")
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for statement in _SCHEMA_SQL.split(";"):
                        if statement.strip():
                            connection.execute(statement)
                    connection.execute(f"PRAGMA application_id = {_SQLITE_APPLICATION_ID}")
                    connection.execute(
                        f"PRAGMA user_version = {DATA_KEYSET_STORE_SCHEMA_VERSION}"
                    )
                    connection.execute("COMMIT")
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
            if self._database_path.exists():
                raise SecurityStoreError("data_keyset_store_already_exists")
            os.link(temporary, self._database_path)
            temporary.unlink()
            self._permissions.secure_sqlite_files(self._database_path)
            self._validate_store()
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def create_snapshot(self, target_path: Path) -> Path:
        """Create one consistent no-clobber snapshot of metadata plus WAL."""

        self._validate_store()
        target = Path(target_path)
        if target.exists() or target.is_symlink():
            raise SecurityStoreError("data_keyset_snapshot_target_exists")
        self._permissions.prepare_directory(target.parent)
        descriptor: int | None = None
        identity: tuple[int, int] | None = None
        try:
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(target, flags, 0o600)
            status = os.fstat(descriptor)
            identity = (status.st_dev, status.st_ino)
            os.close(descriptor)
            descriptor = None
            with sqlite3.connect(
                f"file:{self._database_path.resolve()}?mode=ro", uri=True
            ) as source:
                source.execute("PRAGMA query_only = ON")
                with sqlite3.connect(target, isolation_level=None) as snapshot:
                    snapshot.execute("PRAGMA journal_mode = DELETE")
                    snapshot.execute("PRAGMA synchronous = FULL")
                    source.backup(snapshot)
            self._permissions.secure_sqlite_files(target)
            SQLiteDataKeysetRepository(target, self._permissions)._validate_store()
            with target.open("rb") as stream:
                os.fsync(stream.fileno())
            _fsync_directory(target.parent)
            return target
        except SecurityStoreError:
            _unlink_snapshot_if_owned(target, identity)
            raise
        except (OSError, sqlite3.Error):
            _unlink_snapshot_if_owned(target, identity)
            raise SecurityStoreError("data_keyset_snapshot_failed") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def active_data_keyset(self) -> DataKeyset | None:
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM data_keysets WHERE status = 'active'"
            ).fetchall()
            if len(rows) > 1:
                raise SecurityStoreError("data_keyset_cardinality_invalid")
            return None if not rows else self._from_row(rows[0])

    def pending_data_keysets(self) -> tuple[DataKeyset, ...]:
        with self._read_connection() as connection:
            return tuple(
                self._from_row(row)
                for row in connection.execute(
                    "SELECT * FROM data_keysets WHERE status = 'pending' ORDER BY generation"
                ).fetchall()
            )

    def data_keysets_for_cleanup(self) -> tuple[DataKeyset, ...]:
        with self._read_connection() as connection:
            return tuple(
                self._from_row(row)
                for row in connection.execute(
                    "SELECT * FROM data_keysets WHERE status IN ('revoked', 'failed') "
                    "ORDER BY generation"
                ).fetchall()
            )

    def next_data_key_generation(self) -> int:
        with self._read_connection() as connection:
            return int(
                connection.execute(
                    "SELECT COALESCE(MAX(generation), 0) + 1 FROM data_keysets"
                ).fetchone()[0]
            )

    def prepare_data_keyset(self, keyset: DataKeyset) -> None:
        self._validate_value(keyset)
        if keyset.status is not DataKeysetStatus.PENDING:
            raise SecurityStoreError("data_keyset_status_invalid")
        with self._write_connection() as connection:
            if connection.execute(
                "SELECT 1 FROM data_keysets WHERE status IN ('pending', 'active')"
            ).fetchone() is not None:
                raise SecurityStoreError("data_keyset_active_or_pending_exists")
            expected = int(
                connection.execute(
                    "SELECT COALESCE(MAX(generation), 0) + 1 FROM data_keysets"
                ).fetchone()[0]
            )
            if keyset.generation != expected:
                raise SecurityStoreError("data_keyset_generation_invalid")
            connection.execute(
                "INSERT INTO data_keysets VALUES (?, ?, 'pending', ?, ?, ?)",
                (
                    keyset.key_id,
                    keyset.generation,
                    keyset.fingerprint_sha256,
                    keyset.runtime_phase.value,
                    keyset.database_context_id,
                ),
            )

    def advance_pending_data_keyset(
        self,
        *,
        key_id: str,
        expected_phase: DataKeysetRuntimePhase,
        replacement_phase: DataKeysetRuntimePhase,
        database_context_id: str | None = None,
    ) -> DataKeyset:
        validate_uuid4(key_id)
        if (
            not isinstance(expected_phase, DataKeysetRuntimePhase)
            or not isinstance(replacement_phase, DataKeysetRuntimePhase)
            or _ALLOWED_PENDING_PHASE_TRANSITIONS.get(expected_phase)
            is not replacement_phase
        ):
            raise SecurityStoreError("data_keyset_phase_transition_invalid")
        if database_context_id is not None:
            validate_uuid4(database_context_id)
        with self._write_connection() as connection:
            row = connection.execute(
                "SELECT * FROM data_keysets WHERE key_id = ? AND status = 'pending'",
                (key_id,),
            ).fetchone()
            if row is None:
                raise SecurityStoreError("pending_data_keyset_missing")
            current = self._from_row(row)
            if current.runtime_phase is not expected_phase:
                raise SecurityStoreError("data_keyset_phase_changed")
            if replacement_phase is DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED:
                if current.database_context_id is not None or database_context_id is None:
                    raise SecurityStoreError("data_keyset_context_invalid")
                replacement_context = database_context_id
            else:
                if database_context_id is not None:
                    raise SecurityStoreError("data_keyset_context_invalid")
                replacement_context = current.database_context_id
            if replacement_phase in {
                DataKeysetRuntimePhase.ENVELOPE_PUBLISHED,
                DataKeysetRuntimePhase.DATABASE_KEY_ACTIVE,
            } and replacement_context is None:
                raise SecurityStoreError("data_keyset_context_missing")
            cursor = connection.execute(
                "UPDATE data_keysets SET runtime_phase = ?, database_context_id = ? "
                "WHERE key_id = ? AND status = 'pending' AND runtime_phase = ?",
                (
                    replacement_phase.value,
                    replacement_context,
                    key_id,
                    expected_phase.value,
                ),
            )
            if cursor.rowcount != 1:
                raise SecurityStoreError("data_keyset_phase_changed")
            updated = connection.execute(
                "SELECT * FROM data_keysets WHERE key_id = ?", (key_id,)
            ).fetchone()
            assert updated is not None
            return self._from_row(updated)

    def activate_data_keyset(self, *, key_id: str) -> DataKeyset:
        validate_uuid4(key_id)
        with self._write_connection() as connection:
            if connection.execute(
                "SELECT 1 FROM data_keysets WHERE status = 'active'"
            ).fetchone() is not None:
                raise SecurityStoreError("active_data_keyset_exists")
            cursor = connection.execute(
                "UPDATE data_keysets SET status = 'active', runtime_phase = 'active' "
                "WHERE key_id = ? AND status = 'pending'",
                (key_id,),
            )
            if cursor.rowcount != 1:
                raise SecurityStoreError("pending_data_keyset_missing")
            row = connection.execute(
                "SELECT * FROM data_keysets WHERE key_id = ?", (key_id,)
            ).fetchone()
            assert row is not None
            return self._from_row(row)

    def fail_data_keyset(self, *, key_id: str) -> bool:
        return self._set_terminal_status(key_id, DataKeysetStatus.FAILED)

    def revoke_data_keyset(self, *, key_id: str) -> bool:
        return self._set_terminal_status(key_id, DataKeysetStatus.REVOKED)

    def _set_terminal_status(
        self, key_id: str, status: DataKeysetStatus
    ) -> bool:
        validate_uuid4(key_id)
        with self._write_connection() as connection:
            cursor = connection.execute(
                "UPDATE data_keysets SET status = ? "
                "WHERE key_id = ? AND status IN ('pending', 'active')",
                (status.value, key_id),
            )
            return cursor.rowcount == 1

    def _validate_store(self) -> None:
        if self._database_path.is_symlink() or not self._database_path.is_file():
            raise SecurityStoreError("data_keyset_store_missing")
        try:
            with sqlite3.connect(
                f"file:{self._database_path.resolve()}?mode=ro", uri=True
            ) as connection:
                connection.row_factory = sqlite3.Row
                if int(connection.execute("PRAGMA application_id").fetchone()[0]) != _SQLITE_APPLICATION_ID:
                    raise SecurityStoreError("data_keyset_store_identity_invalid")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != DATA_KEYSET_STORE_SCHEMA_VERSION:
                    raise SecurityStoreError("data_keyset_store_version_invalid")
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity is None or integrity[0] != "ok":
                    raise SecurityStoreError("data_keyset_store_integrity_failed")
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' "
                        "AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                if tables != {"data_keysets"}:
                    raise SecurityStoreError("data_keyset_store_tables_invalid")
                columns = tuple(
                    row[1] for row in connection.execute("PRAGMA table_info(data_keysets)")
                )
                if columns != _EXPECTED_COLUMNS:
                    raise SecurityStoreError("data_keyset_store_columns_invalid")
                active = pending = 0
                for row in connection.execute("SELECT * FROM data_keysets").fetchall():
                    keyset = self._from_row(row)
                    active += keyset.status is DataKeysetStatus.ACTIVE
                    pending += keyset.status is DataKeysetStatus.PENDING
                if active > 1 or pending > 1:
                    raise SecurityStoreError("data_keyset_cardinality_invalid")
        except SecurityStoreError:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError):
            raise SecurityStoreError("data_keyset_store_invalid") from None

    @contextmanager
    def _read_connection(self):
        self._validate_store()
        connection = sqlite3.connect(
            f"file:{self._database_path.resolve()}?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write_connection(self):
        self._validate_store()
        connection = sqlite3.connect(self._database_path, isolation_level=None, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
            self._permissions.secure_sqlite_files(self._database_path)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> DataKeyset:
        keyset = DataKeyset(
            key_id=validate_uuid4(row["key_id"]),
            generation=int(row["generation"]),
            status=DataKeysetStatus(row["status"]),
            fingerprint_sha256=str(row["fingerprint_sha256"]),
            runtime_phase=DataKeysetRuntimePhase(row["runtime_phase"]),
            database_context_id=(
                None
                if row["database_context_id"] is None
                else str(row["database_context_id"])
            ),
        )
        SQLiteDataKeysetRepository._validate_value(keyset)
        return keyset

    @staticmethod
    def _validate_value(keyset: DataKeyset) -> None:
        validate_uuid4(keyset.key_id)
        if keyset.generation < 1:
            raise SecurityStoreError("data_keyset_generation_invalid")
        if len(keyset.fingerprint_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in keyset.fingerprint_sha256
        ):
            raise SecurityStoreError("data_keyset_fingerprint_invalid")
        if not isinstance(keyset.runtime_phase, DataKeysetRuntimePhase):
            raise SecurityStoreError("data_keyset_runtime_phase_invalid")
        if keyset.database_context_id is not None:
            validate_uuid4(keyset.database_context_id)
        if keyset.status is DataKeysetStatus.ACTIVE:
            if keyset.runtime_phase is not DataKeysetRuntimePhase.ACTIVE:
                raise SecurityStoreError("data_keyset_runtime_phase_invalid")
        elif (
            keyset.status is DataKeysetStatus.PENDING
            and keyset.runtime_phase is DataKeysetRuntimePhase.ACTIVE
        ):
            raise SecurityStoreError("data_keyset_runtime_phase_invalid")
        if keyset.runtime_phase in {
            DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED,
            DataKeysetRuntimePhase.ENVELOPE_PUBLISHED,
            DataKeysetRuntimePhase.DATABASE_KEY_ACTIVE,
        } and keyset.database_context_id is None:
            raise SecurityStoreError("data_keyset_context_missing")


def _unlink_snapshot_if_owned(
    path: Path, identity: tuple[int, int] | None
) -> None:
    if identity is None:
        return
    try:
        status = path.lstat()
        if (
            not stat.S_ISLNK(status.st_mode)
            and stat.S_ISREG(status.st_mode)
            and (status.st_dev, status.st_ino) == identity
        ):
            path.unlink()
    except OSError:
        return


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        raise SecurityStoreError("data_keyset_snapshot_failed") from None
