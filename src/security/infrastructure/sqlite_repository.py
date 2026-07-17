"""Strict transactional SQLite repository for security-only data."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
import hmac
import os
from pathlib import Path
import sqlite3
import tempfile

from ..domain import (
    AccountRecord,
    AccountStatus,
    DEVICE_CREDENTIAL_HASH_BYTES,
    DEVICE_CREDENTIAL_HASH_FORMAT_VERSION,
    DEVICE_CREDENTIAL_SALT_BYTES,
    DeviceCredential,
    DeviceCredentialStatus,
    PASSWORD_HASH_FORMAT_VERSION,
    RECOVERY_CODE_COUNT,
    RECOVERY_CODE_FORMAT_VERSION,
    RecoveryCodeCandidate,
    RecoveryCodeHash,
    SECURITY_FORMAT_VERSION,
    SECURITY_SCHEMA_VERSION,
    SUPPORT_RESET_ACTION,
    SUPPORT_RESET_CLOCK_SKEW,
    SUPPORT_RESET_FORMAT_VERSION,
    SecurityStoreError,
    SupportResetPayload,
    SupportResetRequest,
    UnsupportedSecurityVersionError,
    delay_seconds_for_failure,
    validate_uuid4,
)
from ..ports import FilePermissionManager


_SQLITE_APPLICATION_ID = 0x4A4B4D53

_EXPECTED_TABLE_COLUMNS_V1 = {
    "security_metadata": (
        "metadata_id", "schema_version", "format_version", "created_at_utc", "updated_at_utc"
    ),
    "installations": (
        "installation_id", "marker_reference", "status", "created_at_utc", "updated_at_utc"
    ),
    "local_accounts": (
        "user_id", "installation_id", "password_hash", "hash_format_version", "status",
        "failed_attempts", "locked_until_utc", "last_observed_utc", "recovery_failed_attempts",
        "recovery_locked_until_utc", "recovery_last_observed_utc", "created_at_utc", "updated_at_utc"
    ),
    "recovery_code_sets": (
        "recovery_set_id", "user_id", "status", "created_at_utc", "confirmed_at_utc", "revoked_at_utc"
    ),
    "recovery_codes": (
        "recovery_code_id", "recovery_set_id", "salt", "code_hash", "format_version", "status",
        "created_at_utc", "used_at_utc", "revoked_at_utc"
    ),
}

_EXPECTED_TABLE_COLUMNS = {
    **_EXPECTED_TABLE_COLUMNS_V1,
    "support_reset_requests": (
        "reset_request_id", "installation_id", "user_id", "nonce", "action",
        "status", "created_at_utc", "expires_at_utc", "revoked_at_utc", "consumed_at_utc"
    ),
    "support_reset_token_uses": (
        "token_digest", "reset_request_id", "key_id", "action", "status",
        "created_at_utc", "expires_at_utc", "consumed_at_utc"
    ),
    "security_epochs": (
        "user_id", "installation_id", "generation", "updated_at_utc"
    ),
    "device_credentials": (
        "credential_id", "installation_id", "user_id", "device_label", "salt",
        "secret_hash", "hash_format_version", "security_epoch_at_issue", "status",
        "created_at_utc", "last_used_at_utc", "revoked_at_utc"
    ),
}

_SCHEMA_V1_SQL = """
CREATE TABLE security_metadata (
    metadata_id INTEGER PRIMARY KEY CHECK (metadata_id = 1),
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    format_version INTEGER NOT NULL CHECK (format_version >= 1),
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
) STRICT;

CREATE TABLE installations (
    installation_id TEXT PRIMARY KEY,
    marker_reference TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
) STRICT;

CREATE TABLE local_accounts (
    user_id TEXT PRIMARY KEY,
    installation_id TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    hash_format_version INTEGER NOT NULL CHECK (hash_format_version >= 1),
    status TEXT NOT NULL CHECK (status IN ('active', 'password_reset_pending', 'disabled')),
    failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    locked_until_utc TEXT,
    last_observed_utc TEXT,
    recovery_failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (recovery_failed_attempts >= 0),
    recovery_locked_until_utc TEXT,
    recovery_last_observed_utc TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (installation_id) REFERENCES installations(installation_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE recovery_code_sets (
    recovery_set_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'revoked')),
    created_at_utc TEXT NOT NULL,
    confirmed_at_utc TEXT,
    revoked_at_utc TEXT,
    CHECK (
        (status = 'pending' AND confirmed_at_utc IS NULL AND revoked_at_utc IS NULL)
        OR (status = 'active' AND confirmed_at_utc IS NOT NULL AND revoked_at_utc IS NULL)
        OR (status = 'revoked' AND revoked_at_utc IS NOT NULL)
    ),
    FOREIGN KEY (user_id) REFERENCES local_accounts(user_id) ON DELETE CASCADE
) STRICT;

CREATE UNIQUE INDEX one_active_recovery_set_per_user
ON recovery_code_sets(user_id) WHERE status = 'active';
CREATE UNIQUE INDEX one_pending_recovery_set_per_user
ON recovery_code_sets(user_id) WHERE status = 'pending';

CREATE TABLE recovery_codes (
    recovery_code_id TEXT PRIMARY KEY,
    recovery_set_id TEXT NOT NULL,
    salt BLOB NOT NULL CHECK (length(salt) = 16),
    code_hash BLOB NOT NULL CHECK (length(code_hash) = 32),
    format_version INTEGER NOT NULL CHECK (format_version >= 1),
    status TEXT NOT NULL CHECK (status IN ('active', 'used', 'revoked')),
    created_at_utc TEXT NOT NULL,
    used_at_utc TEXT,
    revoked_at_utc TEXT,
    CHECK (
        (status = 'active' AND used_at_utc IS NULL AND revoked_at_utc IS NULL)
        OR (status = 'used' AND used_at_utc IS NOT NULL AND revoked_at_utc IS NULL)
        OR (status = 'revoked' AND used_at_utc IS NULL AND revoked_at_utc IS NOT NULL)
    ),
    UNIQUE (recovery_set_id, code_hash),
    FOREIGN KEY (recovery_set_id) REFERENCES recovery_code_sets(recovery_set_id) ON DELETE CASCADE
) STRICT;
"""

_SCHEMA_V2_SQL = """
CREATE TABLE support_reset_requests (
    reset_request_id TEXT PRIMARY KEY,
    installation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    nonce TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action = 'reset_local_password_v1'),
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'consumed')),
    created_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    revoked_at_utc TEXT,
    consumed_at_utc TEXT,
    CHECK (
        (status = 'active' AND revoked_at_utc IS NULL AND consumed_at_utc IS NULL)
        OR (status = 'revoked' AND revoked_at_utc IS NOT NULL AND consumed_at_utc IS NULL)
        OR (status = 'consumed' AND consumed_at_utc IS NOT NULL)
    ),
    FOREIGN KEY (installation_id) REFERENCES installations(installation_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES local_accounts(user_id) ON DELETE CASCADE
) STRICT;

CREATE UNIQUE INDEX one_active_support_reset_request_per_user
ON support_reset_requests(user_id) WHERE status = 'active';

CREATE TABLE support_reset_token_uses (
    token_digest BLOB PRIMARY KEY CHECK (length(token_digest) = 32),
    reset_request_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action = 'reset_local_password_v1'),
    status TEXT NOT NULL CHECK (status IN ('consumed', 'revoked')),
    created_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    consumed_at_utc TEXT NOT NULL,
    FOREIGN KEY (reset_request_id) REFERENCES support_reset_requests(reset_request_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE security_epochs (
    user_id TEXT PRIMARY KEY,
    installation_id TEXT NOT NULL UNIQUE,
    generation INTEGER NOT NULL CHECK (generation >= 1),
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES local_accounts(user_id) ON DELETE CASCADE,
    FOREIGN KEY (installation_id) REFERENCES installations(installation_id) ON DELETE CASCADE
) STRICT;
"""

_SCHEMA_V3_SQL = """
CREATE TABLE device_credentials (
    credential_id TEXT PRIMARY KEY,
    installation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    device_label TEXT NOT NULL CHECK (length(device_label) BETWEEN 1 AND 80),
    salt BLOB NOT NULL CHECK (length(salt) = 16),
    secret_hash BLOB NOT NULL CHECK (length(secret_hash) = 32),
    hash_format_version INTEGER NOT NULL CHECK (hash_format_version >= 1),
    security_epoch_at_issue INTEGER NOT NULL CHECK (security_epoch_at_issue >= 1),
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'revoked')),
    created_at_utc TEXT NOT NULL,
    last_used_at_utc TEXT,
    revoked_at_utc TEXT,
    CHECK (
        (status IN ('pending', 'active') AND revoked_at_utc IS NULL)
        OR (status = 'revoked' AND revoked_at_utc IS NOT NULL)
    ),
    FOREIGN KEY (installation_id) REFERENCES installations(installation_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES local_accounts(user_id) ON DELETE CASCADE
) STRICT;

CREATE UNIQUE INDEX one_active_device_credential_per_account
ON device_credentials(installation_id, user_id) WHERE status = 'active';
"""

_SCHEMA_SQL = _SCHEMA_V1_SQL + _SCHEMA_V2_SQL + _SCHEMA_V3_SQL
_RESET_PASSWORD_MARKER = "!password-reset-pending!"


class SQLiteSecurityRepository:
    def __init__(
        self,
        database_path: Path,
        permissions: FilePermissionManager,
        *,
        failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        self._database_path = Path(database_path)
        self._permissions = permissions
        self._failure_injector = failure_injector or (lambda _point: None)

    @property
    def database_path(self) -> Path:
        return self._database_path

    def exists(self) -> bool:
        return self._database_path.exists()

    def inspect(self) -> tuple[int, int, str, AccountRecord]:
        if self._database_path.is_symlink():
            raise SecurityStoreError("security_store_symlink_rejected")
        try:
            self._ensure_current_schema()
            with self._read_connection() as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity is None or integrity[0] != "ok":
                    raise SecurityStoreError("security_store_integrity_failed")
                metadata = connection.execute(
                    "SELECT schema_version, format_version, created_at_utc, updated_at_utc "
                    "FROM security_metadata WHERE metadata_id = 1"
                ).fetchone()
                if metadata is None:
                    raise SecurityStoreError("security_metadata_missing")
                schema_version, format_version = int(metadata[0]), int(metadata[1])
                _parse_required_datetime(metadata[2])
                _parse_required_datetime(metadata[3])
                if schema_version > SECURITY_SCHEMA_VERSION or format_version > SECURITY_FORMAT_VERSION:
                    raise UnsupportedSecurityVersionError("security_store_version_newer")
                if (schema_version, format_version) != (
                    SECURITY_SCHEMA_VERSION,
                    SECURITY_FORMAT_VERSION,
                ):
                    raise SecurityStoreError("security_store_version_invalid")
                application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
                user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if application_id != _SQLITE_APPLICATION_ID or user_version != SECURITY_SCHEMA_VERSION:
                    raise SecurityStoreError("security_store_identity_invalid")
                self._validate_schema_shape(connection)
                fk = connection.execute("PRAGMA foreign_key_check").fetchall()
                if fk:
                    raise SecurityStoreError("security_store_foreign_key_failed")
                installation_rows = connection.execute(
                    "SELECT installation_id, marker_reference, created_at_utc, updated_at_utc "
                    "FROM installations WHERE status = 'active'"
                ).fetchall()
                account_rows = connection.execute("SELECT * FROM local_accounts").fetchall()
                if len(installation_rows) != 1 or len(account_rows) != 1:
                    raise SecurityStoreError("security_store_cardinality_invalid")
                installation_id, marker_reference, installation_created, installation_updated = installation_rows[0]
                validate_uuid4(installation_id)
                validate_uuid4(marker_reference)
                _parse_required_datetime(installation_created)
                _parse_required_datetime(installation_updated)
                account = self._account_from_row(account_rows[0])
                if not account.password_hash.startswith("$argon2id$") and not (
                    account.status == AccountStatus.PASSWORD_RESET_PENDING
                    and account.password_hash == _RESET_PASSWORD_MARKER
                ):
                    raise SecurityStoreError("security_password_hash_format_invalid")
                if account.installation_id != installation_id:
                    raise SecurityStoreError("security_store_binding_invalid")
                self._validate_recovery_sets(connection, account)
                self._validate_support_reset_state(connection, account)
                self._validate_device_credentials(connection, account)
                self._validate_all_timestamps(connection)
                return schema_version, format_version, marker_reference, account
        except UnsupportedSecurityVersionError:
            raise
        except SecurityStoreError:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError) as error:
            raise SecurityStoreError("security_store_invalid") from error

    def initialize(
        self,
        *,
        installation_id: str,
        marker_reference: str,
        user_id: str,
        password_hash: str,
        hash_format_version: int,
        recovery_set_id: str,
        recovery_codes: Sequence[RecoveryCodeHash],
        now: datetime,
        pending: bool = False,
    ) -> None:
        for identifier in (installation_id, marker_reference, user_id, recovery_set_id):
            validate_uuid4(identifier)
        if hash_format_version != PASSWORD_HASH_FORMAT_VERSION:
            raise SecurityStoreError("password_hash_version_invalid")
        if len(recovery_codes) != RECOVERY_CODE_COUNT:
            raise SecurityStoreError("recovery_code_count_invalid")
        self._permissions.prepare_directory(self._database_path.parent)
        if self._database_path.exists():
            raise SecurityStoreError("security_store_already_exists")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".security-store-", suffix=".sqlite", dir=self._database_path.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        self._permissions.secure_file(temporary)
        stamp = _format_datetime(now)
        account_status = "password_reset_pending" if pending else "active"
        recovery_status = "pending" if pending else "active"
        confirmed_at = None if pending else stamp
        try:
            self._failure_injector("before_schema")
            with closing(sqlite3.connect(temporary, isolation_level=None)) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("PRAGMA journal_mode = DELETE")
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for statement in _SCHEMA_SQL.split(";"):
                        if statement.strip():
                            connection.execute(statement)
                    connection.execute(f"PRAGMA application_id = {_SQLITE_APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version = {SECURITY_SCHEMA_VERSION}")
                    connection.execute(
                        "INSERT INTO security_metadata VALUES (1, ?, ?, ?, ?)",
                        (SECURITY_SCHEMA_VERSION, SECURITY_FORMAT_VERSION, stamp, stamp),
                    )
                    connection.execute(
                        "INSERT INTO installations VALUES (?, ?, 'active', ?, ?)",
                        (installation_id, marker_reference, stamp, stamp),
                    )
                    connection.execute(
                        "INSERT INTO local_accounts VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, 0, NULL, NULL, ?, ?)",
                        (user_id, installation_id, password_hash, hash_format_version, account_status, stamp, stamp),
                    )
                    connection.execute(
                        "INSERT INTO recovery_code_sets VALUES (?, ?, ?, ?, ?, NULL)",
                        (recovery_set_id, user_id, recovery_status, stamp, confirmed_at),
                    )
                    self._insert_recovery_codes(
                        connection, recovery_set_id, recovery_codes, stamp
                    )
                    connection.execute(
                        "INSERT INTO security_epochs VALUES (?, ?, 1, ?)",
                        (user_id, installation_id, stamp),
                    )
                    self._failure_injector("before_commit")
                    connection.execute("COMMIT")
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
            self._failure_injector("after_commit")
            _fsync_file(temporary)
            if self._database_path.exists():
                raise SecurityStoreError("security_store_already_exists")
            try:
                os.link(temporary, self._database_path)
            except FileExistsError as error:
                raise SecurityStoreError("security_store_already_exists") from error
            temporary.unlink()
            self._permissions.secure_sqlite_files(self._database_path)
            _fsync_directory(self._database_path.parent)
            self._failure_injector("after_publish")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def activate_pending_account(
        self, *, recovery_set_id: str, now: datetime
    ) -> bool:
        validate_uuid4(recovery_set_id)
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            if account.status != AccountStatus.PASSWORD_RESET_PENDING:
                return False
            pending_count = connection.execute(
                "SELECT COUNT(*) FROM recovery_codes c JOIN recovery_code_sets s "
                "ON s.recovery_set_id = c.recovery_set_id "
                "WHERE s.recovery_set_id = ? AND s.user_id = ? "
                "AND s.status = 'pending' AND c.status = 'active'",
                (recovery_set_id, account.user_id),
            ).fetchone()[0]
            if pending_count != RECOVERY_CODE_COUNT:
                return False
            stamp = _format_datetime(now)
            set_cursor = connection.execute(
                "UPDATE recovery_code_sets SET status = 'active', confirmed_at_utc = ? "
                "WHERE recovery_set_id = ? AND status = 'pending'",
                (stamp, recovery_set_id),
            )
            account_cursor = connection.execute(
                "UPDATE local_accounts SET status = 'active', updated_at_utc = ? "
                "WHERE user_id = ? AND status = 'password_reset_pending'",
                (stamp, account.user_id),
            )
            return set_cursor.rowcount == 1 and account_cursor.rowcount == 1

    def load_account(self) -> AccountRecord:
        self._ensure_current_schema()
        with self._read_connection() as connection:
            rows = connection.execute("SELECT * FROM local_accounts").fetchall()
            if len(rows) != 1:
                raise SecurityStoreError("security_account_cardinality_invalid")
            return self._account_from_row(rows[0])

    def record_login_failure(self, *, now: datetime) -> AccountRecord:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            failures = account.failed_attempts + 1
            delay = delay_seconds_for_failure(failures)
            locked_until = now + timedelta(seconds=delay) if delay else None
            connection.execute(
                "UPDATE local_accounts SET failed_attempts = ?, locked_until_utc = ?, "
                "last_observed_utc = ?, updated_at_utc = ? WHERE user_id = ?",
                (failures, _optional_datetime(locked_until), _format_datetime(now), _format_datetime(now), account.user_id),
            )
            return self._single_account(connection)

    def record_login_success(
        self, *, now: datetime, replacement_hash: str | None = None
    ) -> AccountRecord:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            if account.status != AccountStatus.ACTIVE:
                raise SecurityStoreError("security_account_not_active")
            password_hash = replacement_hash or account.password_hash
            connection.execute(
                "UPDATE local_accounts SET password_hash = ?, failed_attempts = 0, "
                "locked_until_utc = NULL, last_observed_utc = ?, updated_at_utc = ? "
                "WHERE user_id = ?",
                (password_hash, _format_datetime(now), _format_datetime(now), account.user_id),
            )
            return self._single_account(connection)

    def update_observed_login_time(
        self, *, observed: datetime, locked_until: datetime | None = None
    ) -> AccountRecord:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            last = (
                observed
                if locked_until is not None
                else max(filter(None, (account.last_observed_utc, observed)))
            )
            effective_lock = _latest(account.locked_until_utc, locked_until)
            connection.execute(
                "UPDATE local_accounts SET last_observed_utc = ?, locked_until_utc = ?, "
                "updated_at_utc = ? WHERE user_id = ?",
                (_format_datetime(last), _optional_datetime(effective_lock), _format_datetime(observed), account.user_id),
            )
            return self._single_account(connection)

    def change_password(
        self, *, expected_hash: str, replacement_hash: str, now: datetime
    ) -> bool:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            cursor = connection.execute(
                "UPDATE local_accounts SET password_hash = ?, hash_format_version = ?, "
                "failed_attempts = 0, locked_until_utc = NULL, last_observed_utc = ?, "
                "updated_at_utc = ? WHERE user_id = ? AND password_hash = ? AND status = 'active'",
                (replacement_hash, PASSWORD_HASH_FORMAT_VERSION, _format_datetime(now), _format_datetime(now), account.user_id, expected_hash),
            )
            if cursor.rowcount != 1:
                return False
            epoch = connection.execute(
                "UPDATE security_epochs SET generation = generation + 1, updated_at_utc = ? "
                "WHERE user_id = ? AND installation_id = ?",
                (_format_datetime(now), account.user_id, account.installation_id),
            )
            if epoch.rowcount != 1:
                raise SecurityStoreError("security_epoch_missing")
            self._revoke_active_device_credentials(connection, now)
            return True

    def active_recovery_codes(self) -> tuple[RecoveryCodeCandidate, ...]:
        self._ensure_current_schema()
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT c.recovery_code_id, c.salt, c.code_hash, c.status "
                "FROM recovery_codes c JOIN recovery_code_sets s ON s.recovery_set_id = c.recovery_set_id "
                "WHERE s.status = 'active' ORDER BY c.recovery_code_id"
            ).fetchall()
            return tuple(
                RecoveryCodeCandidate(row[0], bytes(row[1]), bytes(row[2]), row[3])
                for row in rows
            )

    def record_recovery_failure(self, *, now: datetime) -> AccountRecord:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            failures = account.recovery_failed_attempts + 1
            delay = delay_seconds_for_failure(failures)
            locked_until = now + timedelta(seconds=delay) if delay else None
            connection.execute(
                "UPDATE local_accounts SET recovery_failed_attempts = ?, recovery_locked_until_utc = ?, "
                "recovery_last_observed_utc = ?, updated_at_utc = ? WHERE user_id = ?",
                (failures, _optional_datetime(locked_until), _format_datetime(now), _format_datetime(now), account.user_id),
            )
            return self._single_account(connection)

    def update_observed_recovery_time(
        self, *, observed: datetime, locked_until: datetime | None = None
    ) -> AccountRecord:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            last = (
                observed
                if locked_until is not None
                else max(
                    filter(None, (account.recovery_last_observed_utc, observed))
                )
            )
            effective_lock = _latest(account.recovery_locked_until_utc, locked_until)
            connection.execute(
                "UPDATE local_accounts SET recovery_last_observed_utc = ?, recovery_locked_until_utc = ?, "
                "updated_at_utc = ? WHERE user_id = ?",
                (_format_datetime(last), _optional_datetime(effective_lock), _format_datetime(observed), account.user_id),
            )
            return self._single_account(connection)

    def consume_recovery_code(
        self, *, recovery_code_id: str, expected_digest: bytes, now: datetime
    ) -> bool:
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            row = connection.execute(
                "SELECT c.code_hash FROM recovery_codes c "
                "JOIN recovery_code_sets s ON s.recovery_set_id = c.recovery_set_id "
                "WHERE c.recovery_code_id = ? AND c.status = 'active' AND s.status = 'active'",
                (recovery_code_id,),
            ).fetchone()
            if row is None or not hmac.compare_digest(bytes(row[0]), expected_digest):
                return False
            stamp = _format_datetime(now)
            cursor = connection.execute(
                "UPDATE recovery_codes SET status = 'used', used_at_utc = ? "
                "WHERE recovery_code_id = ? AND status = 'active'",
                (stamp, recovery_code_id),
            )
            if cursor.rowcount != 1:
                return False
            connection.execute(
                "UPDATE local_accounts SET status = 'password_reset_pending', "
                "recovery_failed_attempts = 0, recovery_locked_until_utc = NULL, "
                "recovery_last_observed_utc = ?, updated_at_utc = ? WHERE user_id = ?",
                (stamp, stamp, account.user_id),
            )
            epoch = connection.execute(
                "UPDATE security_epochs SET generation = generation + 1, updated_at_utc = ? "
                "WHERE user_id = ? AND installation_id = ?",
                (stamp, account.user_id, account.installation_id),
            )
            if epoch.rowcount != 1:
                raise SecurityStoreError("security_epoch_missing")
            self._revoke_active_device_credentials(connection, now)
            return True

    def prepare_recovery_set(
        self,
        *,
        recovery_set_id: str,
        recovery_codes: Sequence[RecoveryCodeHash],
        now: datetime,
    ) -> None:
        validate_uuid4(recovery_set_id)
        if len(recovery_codes) != RECOVERY_CODE_COUNT:
            raise SecurityStoreError("recovery_code_count_invalid")
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            connection.execute(
                "DELETE FROM recovery_code_sets WHERE user_id = ? AND status = 'pending'",
                (account.user_id,),
            )
            stamp = _format_datetime(now)
            connection.execute(
                "INSERT INTO recovery_code_sets VALUES (?, ?, 'pending', ?, NULL, NULL)",
                (recovery_set_id, account.user_id, stamp),
            )
            self._insert_recovery_codes(connection, recovery_set_id, recovery_codes, stamp)

    def confirm_recovery_set(self, *, recovery_set_id: str, now: datetime) -> bool:
        validate_uuid4(recovery_set_id)
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            pending = connection.execute(
                "SELECT COUNT(*) FROM recovery_codes c JOIN recovery_code_sets s "
                "ON s.recovery_set_id = c.recovery_set_id "
                "WHERE s.recovery_set_id = ? AND s.user_id = ? AND s.status = 'pending' AND c.status = 'active'",
                (recovery_set_id, account.user_id),
            ).fetchone()[0]
            if pending != RECOVERY_CODE_COUNT:
                return False
            stamp = _format_datetime(now)
            active_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT recovery_set_id FROM recovery_code_sets WHERE user_id = ? AND status = 'active'",
                    (account.user_id,),
                ).fetchall()
            ]
            for active_id in active_ids:
                connection.execute(
                    "UPDATE recovery_codes SET status = 'revoked', revoked_at_utc = ? "
                    "WHERE recovery_set_id = ? AND status = 'active'",
                    (stamp, active_id),
                )
            connection.execute(
                "UPDATE recovery_code_sets SET status = 'revoked', revoked_at_utc = ? "
                "WHERE user_id = ? AND status = 'active'",
                (stamp, account.user_id),
            )
            cursor = connection.execute(
                "UPDATE recovery_code_sets SET status = 'active', confirmed_at_utc = ? "
                "WHERE recovery_set_id = ? AND status = 'pending'",
                (stamp, recovery_set_id),
            )
            return cursor.rowcount == 1

    def complete_password_reset(
        self,
        *,
        replacement_hash: str,
        recovery_set_id: str,
        recovery_codes: Sequence[RecoveryCodeHash],
        now: datetime,
    ) -> bool:
        validate_uuid4(recovery_set_id)
        if len(recovery_codes) != RECOVERY_CODE_COUNT:
            raise SecurityStoreError("recovery_code_count_invalid")
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            if account.status != AccountStatus.PASSWORD_RESET_PENDING:
                return False
            stamp = _format_datetime(now)
            connection.execute(
                "UPDATE recovery_codes SET status = 'revoked', revoked_at_utc = ? "
                "WHERE status = 'active' AND recovery_set_id IN "
                "(SELECT recovery_set_id FROM recovery_code_sets WHERE user_id = ?)",
                (stamp, account.user_id),
            )
            connection.execute(
                "UPDATE recovery_code_sets SET status = 'revoked', revoked_at_utc = ? "
                "WHERE user_id = ? AND status IN ('active', 'pending')",
                (stamp, account.user_id),
            )
            connection.execute(
                "INSERT INTO recovery_code_sets VALUES (?, ?, 'active', ?, ?, NULL)",
                (recovery_set_id, account.user_id, stamp, stamp),
            )
            self._insert_recovery_codes(connection, recovery_set_id, recovery_codes, stamp)
            cursor = connection.execute(
                "UPDATE local_accounts SET password_hash = ?, hash_format_version = ?, status = 'active', "
                "failed_attempts = 0, locked_until_utc = NULL, last_observed_utc = ?, "
                "updated_at_utc = ? WHERE user_id = ? AND status = 'password_reset_pending'",
                (replacement_hash, PASSWORD_HASH_FORMAT_VERSION, stamp, stamp, account.user_id),
            )
            return cursor.rowcount == 1

    def prepare_password_reset(
        self,
        *,
        replacement_hash: str,
        recovery_set_id: str,
        recovery_codes: Sequence[RecoveryCodeHash],
        now: datetime,
    ) -> bool:
        validate_uuid4(recovery_set_id)
        if len(recovery_codes) != RECOVERY_CODE_COUNT:
            raise SecurityStoreError("recovery_code_count_invalid")
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            if account.status != AccountStatus.PASSWORD_RESET_PENDING:
                return False
            stamp = _format_datetime(now)
            connection.execute(
                "UPDATE recovery_codes SET status = 'revoked', revoked_at_utc = ? "
                "WHERE status = 'active' AND recovery_set_id IN "
                "(SELECT recovery_set_id FROM recovery_code_sets WHERE user_id = ?)",
                (stamp, account.user_id),
            )
            connection.execute(
                "UPDATE recovery_code_sets SET status = 'revoked', revoked_at_utc = ? "
                "WHERE user_id = ? AND status IN ('active', 'pending')",
                (stamp, account.user_id),
            )
            connection.execute(
                "INSERT INTO recovery_code_sets VALUES (?, ?, 'pending', ?, NULL, NULL)",
                (recovery_set_id, account.user_id, stamp),
            )
            self._insert_recovery_codes(connection, recovery_set_id, recovery_codes, stamp)
            cursor = connection.execute(
                "UPDATE local_accounts SET password_hash = ?, hash_format_version = ?, "
                "failed_attempts = 0, locked_until_utc = NULL, last_observed_utc = ?, "
                "recovery_failed_attempts = 0, recovery_locked_until_utc = NULL, "
                "recovery_last_observed_utc = ?, updated_at_utc = ? "
                "WHERE user_id = ? AND status = 'password_reset_pending'",
                (replacement_hash, PASSWORD_HASH_FORMAT_VERSION, stamp, stamp, stamp, account.user_id),
            )
            return cursor.rowcount == 1

    def confirm_password_reset(
        self, *, recovery_set_id: str, now: datetime
    ) -> bool:
        return self.activate_pending_account(recovery_set_id=recovery_set_id, now=now)

    def create_support_reset_request(self, request: SupportResetRequest) -> None:
        for identifier in (
            request.installation_id,
            request.user_id,
            request.reset_request_id,
        ):
            validate_uuid4(identifier)
        if (
            request.format_version != SUPPORT_RESET_FORMAT_VERSION
            or request.action != SUPPORT_RESET_ACTION
            or request.status != "active"
            or request.expires_at <= request.created_at
            or request.expires_at - request.created_at > timedelta(hours=24)
        ):
            raise SecurityStoreError("support_reset_request_invalid")
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            if (
                account.status != AccountStatus.ACTIVE
                or account.installation_id != request.installation_id
                or account.user_id != request.user_id
            ):
                raise SecurityStoreError("support_reset_account_binding_invalid")
            stamp = _format_datetime(request.created_at)
            connection.execute(
                "UPDATE support_reset_requests SET status = 'revoked', revoked_at_utc = ? "
                "WHERE user_id = ? AND status = 'active'",
                (stamp, account.user_id),
            )
            connection.execute(
                "INSERT INTO support_reset_requests VALUES "
                "(?, ?, ?, ?, ?, 'active', ?, ?, NULL, NULL)",
                (
                    request.reset_request_id,
                    request.installation_id,
                    request.user_id,
                    request.nonce,
                    request.action,
                    stamp,
                    _format_datetime(request.expires_at),
                ),
            )

    def load_support_reset_request(
        self, reset_request_id: str
    ) -> SupportResetRequest | None:
        validate_uuid4(reset_request_id)
        self._ensure_current_schema()
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM support_reset_requests WHERE reset_request_id = ?",
                (reset_request_id,),
            ).fetchone()
            if row is None:
                return None
            return SupportResetRequest(
                format_version=SUPPORT_RESET_FORMAT_VERSION,
                installation_id=validate_uuid4(row["installation_id"]),
                user_id=validate_uuid4(row["user_id"]),
                reset_request_id=validate_uuid4(row["reset_request_id"]),
                action=row["action"],
                created_at=_parse_required_datetime(row["created_at_utc"]),
                expires_at=_parse_required_datetime(row["expires_at_utc"]),
                nonce=row["nonce"],
                status=row["status"],
            )

    def support_token_digest_used(self, token_digest: bytes) -> bool:
        if not isinstance(token_digest, bytes) or len(token_digest) != 32:
            raise SecurityStoreError("support_token_digest_invalid")
        self._ensure_current_schema()
        with self._read_connection() as connection:
            return connection.execute(
                "SELECT 1 FROM support_reset_token_uses WHERE token_digest = ?",
                (sqlite3.Binary(token_digest),),
            ).fetchone() is not None

    def consume_support_reset(
        self,
        *,
        payload: SupportResetPayload,
        token_digest: bytes,
        now: datetime,
    ) -> int | None:
        for identifier in (
            payload.installation_id,
            payload.user_id,
            payload.reset_request_id,
        ):
            validate_uuid4(identifier)
        if not isinstance(token_digest, bytes) or len(token_digest) != 32:
            raise SecurityStoreError("support_token_digest_invalid")
        if payload.action != SUPPORT_RESET_ACTION:
            raise SecurityStoreError("support_reset_action_invalid")
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            if (
                account.status != AccountStatus.ACTIVE
                or account.installation_id != payload.installation_id
                or account.user_id != payload.user_id
            ):
                return None
            request = connection.execute(
                "SELECT * FROM support_reset_requests "
                "WHERE reset_request_id = ? AND installation_id = ? AND user_id = ? "
                "AND nonce = ? AND action = ? AND status = 'active'",
                (
                    payload.reset_request_id,
                    payload.installation_id,
                    payload.user_id,
                    payload.nonce,
                    payload.action,
                ),
            ).fetchone()
            if request is None or (
                _parse_required_datetime(request["expires_at_utc"])
                < now - SUPPORT_RESET_CLOCK_SKEW
            ):
                return None
            if connection.execute(
                "SELECT 1 FROM support_reset_token_uses WHERE token_digest = ?",
                (sqlite3.Binary(token_digest),),
            ).fetchone() is not None:
                return None
            stamp = _format_datetime(now)
            connection.execute(
                "INSERT INTO support_reset_token_uses VALUES "
                "(?, ?, ?, ?, 'consumed', ?, ?, ?)",
                (
                    sqlite3.Binary(token_digest),
                    payload.reset_request_id,
                    payload.key_id,
                    payload.action,
                    _format_datetime(payload.created_at),
                    _format_datetime(payload.expires_at),
                    stamp,
                ),
            )
            cursor = connection.execute(
                "UPDATE support_reset_requests SET status = 'consumed', consumed_at_utc = ? "
                "WHERE reset_request_id = ? AND status = 'active'",
                (stamp, payload.reset_request_id),
            )
            if cursor.rowcount != 1:
                return None
            connection.execute(
                "UPDATE recovery_codes SET status = 'revoked', revoked_at_utc = ? "
                "WHERE status = 'active' AND recovery_set_id IN "
                "(SELECT recovery_set_id FROM recovery_code_sets WHERE user_id = ?)",
                (stamp, account.user_id),
            )
            connection.execute(
                "UPDATE recovery_code_sets SET status = 'revoked', revoked_at_utc = ? "
                "WHERE user_id = ? AND status IN ('active', 'pending')",
                (stamp, account.user_id),
            )
            account_cursor = connection.execute(
                "UPDATE local_accounts SET password_hash = ?, status = 'password_reset_pending', "
                "failed_attempts = 0, locked_until_utc = NULL, last_observed_utc = ?, "
                "recovery_failed_attempts = 0, recovery_locked_until_utc = NULL, "
                "recovery_last_observed_utc = ?, updated_at_utc = ? "
                "WHERE user_id = ? AND status = 'active'",
                (_RESET_PASSWORD_MARKER, stamp, stamp, stamp, account.user_id),
            )
            if account_cursor.rowcount != 1:
                raise SecurityStoreError("support_reset_account_state_changed")
            connection.execute(
                "UPDATE security_epochs SET generation = generation + 1, updated_at_utc = ? "
                "WHERE user_id = ? AND installation_id = ?",
                (stamp, account.user_id, account.installation_id),
            )
            self._revoke_active_device_credentials(connection, now)
            row = connection.execute(
                "SELECT generation FROM security_epochs WHERE user_id = ?",
                (account.user_id,),
            ).fetchone()
            if row is None:
                raise SecurityStoreError("security_epoch_missing")
            return int(row[0])

    def security_epoch(self) -> int:
        self._ensure_current_schema()
        with self._read_connection() as connection:
            rows = connection.execute("SELECT generation FROM security_epochs").fetchall()
            if len(rows) != 1 or int(rows[0][0]) < 1:
                raise SecurityStoreError("security_epoch_invalid")
            return int(rows[0][0])

    def active_device_credential(self) -> DeviceCredential | None:
        self._ensure_current_schema()
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM device_credentials WHERE status = 'active'"
            ).fetchall()
            if len(rows) > 1:
                raise SecurityStoreError("device_credential_cardinality_invalid")
            return None if not rows else self._device_credential_from_row(rows[0])

    def pending_device_credentials(self) -> tuple[DeviceCredential, ...]:
        return self._device_credentials_with_status(DeviceCredentialStatus.PENDING)

    def revoked_device_credentials(self) -> tuple[DeviceCredential, ...]:
        return self._device_credentials_with_status(DeviceCredentialStatus.REVOKED)

    def _device_credentials_with_status(
        self, status: DeviceCredentialStatus
    ) -> tuple[DeviceCredential, ...]:
        self._ensure_current_schema()
        with self._read_connection() as connection:
            return tuple(
                self._device_credential_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM device_credentials WHERE status = ?",
                    (status.value,),
                ).fetchall()
            )

    def prepare_device_credential(self, credential: DeviceCredential) -> None:
        self._validate_device_credential_value(credential)
        with self._write_transaction() as connection:
            account = self._single_account(connection)
            epoch = self._single_epoch(connection)
            if (
                credential.installation_id != account.installation_id
                or credential.user_id != account.user_id
                or credential.security_epoch_at_issue != epoch
                or credential.status is not DeviceCredentialStatus.PENDING
            ):
                raise SecurityStoreError("device_credential_binding_invalid")
            stamp = _format_datetime(credential.created_at)
            connection.execute(
                "UPDATE device_credentials SET status = 'revoked', revoked_at_utc = ? "
                "WHERE status = 'pending'",
                (stamp,),
            )
            connection.execute(
                "INSERT INTO device_credentials VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, NULL, NULL)",
                (
                    credential.credential_id,
                    credential.installation_id,
                    credential.user_id,
                    credential.device_label,
                    sqlite3.Binary(credential.salt),
                    sqlite3.Binary(credential.secret_hash),
                    credential.hash_format_version,
                    credential.security_epoch_at_issue,
                    stamp,
                ),
            )

    def activate_device_credential(
        self, *, credential_id: str, now: datetime
    ) -> str | None:
        validate_uuid4(credential_id)
        with self._write_transaction() as connection:
            pending = connection.execute(
                "SELECT * FROM device_credentials WHERE credential_id = ? AND status = 'pending'",
                (credential_id,),
            ).fetchone()
            if pending is None:
                raise SecurityStoreError("device_credential_pending_missing")
            credential = self._device_credential_from_row(pending)
            account = self._single_account(connection)
            if (
                credential.installation_id != account.installation_id
                or credential.user_id != account.user_id
                or credential.security_epoch_at_issue != self._single_epoch(connection)
            ):
                raise SecurityStoreError("device_credential_binding_invalid")
            existing = connection.execute(
                "SELECT credential_id FROM device_credentials WHERE status = 'active'"
            ).fetchall()
            if len(existing) > 1:
                raise SecurityStoreError("device_credential_cardinality_invalid")
            replaced = None if not existing else str(existing[0][0])
            stamp = _format_datetime(now)
            if replaced is not None:
                connection.execute(
                    "UPDATE device_credentials SET status = 'revoked', revoked_at_utc = ? "
                    "WHERE credential_id = ? AND status = 'active'",
                    (stamp, replaced),
                )
            cursor = connection.execute(
                "UPDATE device_credentials SET status = 'active' "
                "WHERE credential_id = ? AND status = 'pending'",
                (credential_id,),
            )
            if cursor.rowcount != 1:
                raise SecurityStoreError("device_credential_activation_failed")
            return replaced

    def touch_device_credential(self, *, credential_id: str, now: datetime) -> bool:
        validate_uuid4(credential_id)
        with self._write_transaction() as connection:
            cursor = connection.execute(
                "UPDATE device_credentials SET last_used_at_utc = ? "
                "WHERE credential_id = ? AND status = 'active'",
                (_format_datetime(now), credential_id),
            )
            return cursor.rowcount == 1

    def revoke_device_credential(self, *, credential_id: str, now: datetime) -> bool:
        validate_uuid4(credential_id)
        with self._write_transaction() as connection:
            cursor = connection.execute(
                "UPDATE device_credentials SET status = 'revoked', revoked_at_utc = ? "
                "WHERE credential_id = ? AND status IN ('pending', 'active')",
                (_format_datetime(now), credential_id),
            )
            return cursor.rowcount == 1

    def revoke_all_device_credentials(self, *, now: datetime) -> tuple[str, ...]:
        with self._write_transaction() as connection:
            rows = connection.execute(
                "SELECT credential_id FROM device_credentials WHERE status IN ('pending', 'active')"
            ).fetchall()
            identifiers = tuple(str(row[0]) for row in rows)
            if identifiers:
                connection.execute(
                    "UPDATE device_credentials SET status = 'revoked', revoked_at_utc = ? "
                    "WHERE status IN ('pending', 'active')",
                    (_format_datetime(now),),
                )
            return identifiers

    def _ensure_current_schema(self) -> None:
        if self._database_path.is_symlink() or not self._database_path.is_file():
            raise SecurityStoreError("security_store_missing")
        try:
            probe = sqlite3.connect(
                f"file:{self._database_path.resolve()}?mode=ro",
                uri=True,
                isolation_level=None,
            )
            try:
                application_id = int(probe.execute("PRAGMA application_id").fetchone()[0])
                user_version = int(probe.execute("PRAGMA user_version").fetchone()[0])
            finally:
                probe.close()
        except sqlite3.Error as error:
            raise SecurityStoreError("security_store_invalid") from error
        if application_id != _SQLITE_APPLICATION_ID:
            raise SecurityStoreError("security_store_identity_invalid")
        if user_version > SECURITY_SCHEMA_VERSION:
            raise UnsupportedSecurityVersionError("security_store_version_newer")
        if user_version == SECURITY_SCHEMA_VERSION:
            return
        if user_version not in (1, 2):
            raise SecurityStoreError("security_store_version_invalid")

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                self._database_path, isolation_level=None, timeout=5.0
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("BEGIN IMMEDIATE")
            application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if application_id != _SQLITE_APPLICATION_ID:
                raise SecurityStoreError("security_store_identity_invalid")
            if user_version > SECURITY_SCHEMA_VERSION:
                raise UnsupportedSecurityVersionError("security_store_version_newer")
            if user_version == SECURITY_SCHEMA_VERSION:
                connection.execute("COMMIT")
                return
            if user_version not in (1, 2):
                raise SecurityStoreError("security_store_version_invalid")
            metadata = connection.execute(
                "SELECT schema_version, format_version FROM security_metadata "
                "WHERE metadata_id = 1"
            ).fetchone()
            if metadata is None:
                raise SecurityStoreError("security_metadata_missing")
            if int(metadata[0]) != user_version or int(metadata[1]) != SECURITY_FORMAT_VERSION:
                raise SecurityStoreError("security_store_version_invalid")
            expected = (
                _EXPECTED_TABLE_COLUMNS_V1
                if user_version == 1
                else {key: value for key, value in _EXPECTED_TABLE_COLUMNS.items() if key != "device_credentials"}
            )
            self._validate_schema_shape(connection, expected)
            self._failure_injector("before_migration")
            if user_version == 1:
                for statement in _SCHEMA_V2_SQL.split(";"):
                    if statement.strip():
                        connection.execute(statement)
                accounts = connection.execute(
                    "SELECT user_id, installation_id, updated_at_utc FROM local_accounts"
                ).fetchall()
                if len(accounts) != 1:
                    raise SecurityStoreError("security_account_cardinality_invalid")
                connection.execute(
                    "INSERT INTO security_epochs VALUES (?, ?, 1, ?)",
                    (accounts[0][0], accounts[0][1], accounts[0][2]),
                )
            for statement in _SCHEMA_V3_SQL.split(";"):
                if statement.strip():
                    connection.execute(statement)
            updated_at = connection.execute(
                "SELECT updated_at_utc FROM local_accounts"
            ).fetchone()
            if updated_at is None:
                raise SecurityStoreError("security_account_cardinality_invalid")
            connection.execute(
                "UPDATE security_metadata SET schema_version = ?, updated_at_utc = ? "
                "WHERE metadata_id = 1",
                (SECURITY_SCHEMA_VERSION, updated_at[0]),
            )
            connection.execute(f"PRAGMA user_version = {SECURITY_SCHEMA_VERSION}")
            self._failure_injector("before_migration_commit")
            connection.execute("COMMIT")
            self._failure_injector("after_migration_commit")
        except (UnsupportedSecurityVersionError, SecurityStoreError):
            if connection is not None and connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError):
            if connection is not None and connection.in_transaction:
                connection.execute("ROLLBACK")
            raise SecurityStoreError("security_store_migration_failed")
        finally:
            if connection is not None:
                connection.close()
            self._permissions.secure_sqlite_files(self._database_path)

    def _connect_read_only(self) -> sqlite3.Connection:
        if self._database_path.is_symlink() or not self._database_path.is_file():
            raise SecurityStoreError("security_store_missing")
        connection = sqlite3.connect(
            f"file:{self._database_path.resolve()}?mode=ro", uri=True, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA query_only = ON")
        return connection

    @contextmanager
    def _read_connection(self):
        connection = self._connect_read_only()
        try:
            yield connection
        finally:
            connection.close()
            self._permissions.secure_sqlite_files(self._database_path)

    def _connect_write(self) -> sqlite3.Connection:
        self._ensure_current_schema()
        connection = sqlite3.connect(self._database_path, isolation_level=None, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        self._permissions.secure_sqlite_files(self._database_path)
        return connection

    def _write_transaction(self):
        return _WriteTransaction(self)

    def _single_account(self, connection: sqlite3.Connection) -> AccountRecord:
        rows = connection.execute("SELECT * FROM local_accounts").fetchall()
        if len(rows) != 1:
            raise SecurityStoreError("security_account_cardinality_invalid")
        return self._account_from_row(rows[0])

    @staticmethod
    def _account_from_row(row: sqlite3.Row) -> AccountRecord:
        return AccountRecord(
            user_id=validate_uuid4(row["user_id"]),
            installation_id=validate_uuid4(row["installation_id"]),
            password_hash=row["password_hash"],
            hash_format_version=int(row["hash_format_version"]),
            status=AccountStatus(row["status"]),
            failed_attempts=int(row["failed_attempts"]),
            locked_until_utc=_parse_optional_datetime(row["locked_until_utc"]),
            last_observed_utc=_parse_optional_datetime(row["last_observed_utc"]),
            recovery_failed_attempts=int(row["recovery_failed_attempts"]),
            recovery_locked_until_utc=_parse_optional_datetime(row["recovery_locked_until_utc"]),
            recovery_last_observed_utc=_parse_optional_datetime(row["recovery_last_observed_utc"]),
        )

    @staticmethod
    def _device_credential_from_row(row: sqlite3.Row) -> DeviceCredential:
        credential = DeviceCredential(
            credential_id=validate_uuid4(row["credential_id"]),
            installation_id=validate_uuid4(row["installation_id"]),
            user_id=validate_uuid4(row["user_id"]),
            device_label=str(row["device_label"]),
            salt=bytes(row["salt"]),
            secret_hash=bytes(row["secret_hash"]),
            hash_format_version=int(row["hash_format_version"]),
            security_epoch_at_issue=int(row["security_epoch_at_issue"]),
            created_at=_parse_required_datetime(row["created_at_utc"]),
            last_used_at=_parse_optional_datetime(row["last_used_at_utc"]),
            revoked_at=_parse_optional_datetime(row["revoked_at_utc"]),
            status=DeviceCredentialStatus(row["status"]),
        )
        SQLiteSecurityRepository._validate_device_credential_value(credential)
        return credential

    @staticmethod
    def _validate_device_credential_value(credential: DeviceCredential) -> None:
        validate_uuid4(credential.credential_id)
        validate_uuid4(credential.installation_id)
        validate_uuid4(credential.user_id)
        if not 1 <= len(credential.device_label) <= 80:
            raise SecurityStoreError("device_credential_label_invalid")
        if len(credential.salt) != DEVICE_CREDENTIAL_SALT_BYTES:
            raise SecurityStoreError("device_credential_salt_invalid")
        if len(credential.secret_hash) != DEVICE_CREDENTIAL_HASH_BYTES:
            raise SecurityStoreError("device_credential_hash_invalid")
        if credential.hash_format_version > DEVICE_CREDENTIAL_HASH_FORMAT_VERSION:
            raise UnsupportedSecurityVersionError("device_credential_version_newer")
        if credential.hash_format_version != DEVICE_CREDENTIAL_HASH_FORMAT_VERSION:
            raise SecurityStoreError("device_credential_version_invalid")
        if credential.security_epoch_at_issue < 1:
            raise SecurityStoreError("device_credential_epoch_invalid")

    @staticmethod
    def _single_epoch(connection: sqlite3.Connection) -> int:
        rows = connection.execute("SELECT generation FROM security_epochs").fetchall()
        if len(rows) != 1 or int(rows[0][0]) < 1:
            raise SecurityStoreError("security_epoch_invalid")
        return int(rows[0][0])

    @staticmethod
    def _insert_recovery_codes(
        connection: sqlite3.Connection,
        recovery_set_id: str,
        recovery_codes: Sequence[RecoveryCodeHash],
        stamp: str,
    ) -> None:
        for code in recovery_codes:
            validate_uuid4(code.recovery_code_id)
            connection.execute(
                "INSERT INTO recovery_codes VALUES (?, ?, ?, ?, ?, 'active', ?, NULL, NULL)",
                (
                    code.recovery_code_id,
                    recovery_set_id,
                    sqlite3.Binary(code.salt),
                    sqlite3.Binary(code.digest),
                    RECOVERY_CODE_FORMAT_VERSION,
                    stamp,
                ),
            )

    @staticmethod
    def _revoke_active_device_credentials(
        connection: sqlite3.Connection, now: datetime
    ) -> None:
        connection.execute(
            "UPDATE device_credentials SET status = 'revoked', revoked_at_utc = ? "
            "WHERE status IN ('pending', 'active')",
            (_format_datetime(now),),
        )

    @staticmethod
    def _validate_recovery_sets(
        connection: sqlite3.Connection, account: AccountRecord
    ) -> None:
        rows = connection.execute(
            "SELECT status, COUNT(*) FROM recovery_code_sets WHERE user_id = ? GROUP BY status",
            (account.user_id,),
        ).fetchall()
        counts = {row[0]: int(row[1]) for row in rows}
        active_count = counts.get("active", 0)
        if (
            active_count > 1
            or counts.get("pending", 0) > 1
            or (account.status == AccountStatus.ACTIVE and active_count != 1)
        ):
            raise SecurityStoreError("recovery_set_cardinality_invalid")
        formats = {
            int(row[0])
            for row in connection.execute(
                "SELECT DISTINCT format_version FROM recovery_codes"
            ).fetchall()
        }
        if any(version > RECOVERY_CODE_FORMAT_VERSION for version in formats):
            raise UnsupportedSecurityVersionError("recovery_code_version_newer")
        if formats != {RECOVERY_CODE_FORMAT_VERSION}:
            raise SecurityStoreError("recovery_code_version_invalid")
        for row in connection.execute(
            "SELECT s.recovery_set_id, s.status, COUNT(c.recovery_code_id) AS code_count "
            "FROM recovery_code_sets s LEFT JOIN recovery_codes c ON c.recovery_set_id = s.recovery_set_id "
            "GROUP BY s.recovery_set_id, s.status"
        ).fetchall():
            if int(row["code_count"]) != RECOVERY_CODE_COUNT:
                raise SecurityStoreError("recovery_code_count_invalid")

    @staticmethod
    def _validate_schema_shape(
        connection: sqlite3.Connection,
        expected: dict[str, tuple[str, ...]] = _EXPECTED_TABLE_COLUMNS,
    ) -> None:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        if tables != set(expected):
            raise SecurityStoreError("security_schema_tables_invalid")
        for table, expected_columns in expected.items():
            columns = tuple(
                row[1] for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            )
            if columns != expected_columns:
                raise SecurityStoreError("security_schema_columns_invalid")

    @staticmethod
    def _validate_all_timestamps(connection: sqlite3.Connection) -> None:
        timestamp_columns = {
            "local_accounts": (
                ("created_at_utc", False), ("updated_at_utc", False),
                ("locked_until_utc", True), ("last_observed_utc", True),
                ("recovery_locked_until_utc", True), ("recovery_last_observed_utc", True),
            ),
            "recovery_code_sets": (
                ("created_at_utc", False), ("confirmed_at_utc", True), ("revoked_at_utc", True),
            ),
            "recovery_codes": (
                ("created_at_utc", False), ("used_at_utc", True), ("revoked_at_utc", True),
            ),
            "support_reset_requests": (
                ("created_at_utc", False), ("expires_at_utc", False),
                ("revoked_at_utc", True), ("consumed_at_utc", True),
            ),
            "support_reset_token_uses": (
                ("created_at_utc", False), ("expires_at_utc", False),
                ("consumed_at_utc", False),
            ),
            "security_epochs": (("updated_at_utc", False),),
            "device_credentials": (
                ("created_at_utc", False), ("last_used_at_utc", True),
                ("revoked_at_utc", True),
            ),
        }
        for table, columns in timestamp_columns.items():
            names = ", ".join(name for name, _nullable in columns)
            for row in connection.execute(f'SELECT {names} FROM "{table}"').fetchall():
                for value, (_name, nullable) in zip(row, columns, strict=True):
                    if value is None and nullable:
                        continue
                    _parse_required_datetime(value)

    @staticmethod
    def _validate_support_reset_state(
        connection: sqlite3.Connection, account: AccountRecord
    ) -> None:
        epochs = connection.execute(
            "SELECT user_id, installation_id, generation, updated_at_utc FROM security_epochs"
        ).fetchall()
        if len(epochs) != 1:
            raise SecurityStoreError("security_epoch_cardinality_invalid")
        epoch = epochs[0]
        if (
            epoch["user_id"] != account.user_id
            or epoch["installation_id"] != account.installation_id
            or int(epoch["generation"]) < 1
        ):
            raise SecurityStoreError("security_epoch_binding_invalid")
        _parse_required_datetime(epoch["updated_at_utc"])
        active_requests = int(
            connection.execute(
                "SELECT COUNT(*) FROM support_reset_requests WHERE status = 'active'"
            ).fetchone()[0]
        )
        if active_requests > 1:
            raise SecurityStoreError("support_reset_request_cardinality_invalid")

    @staticmethod
    def _validate_device_credentials(
        connection: sqlite3.Connection, account: AccountRecord
    ) -> None:
        active = 0
        pending = 0
        for row in connection.execute("SELECT * FROM device_credentials").fetchall():
            credential = SQLiteSecurityRepository._device_credential_from_row(row)
            if (
                credential.installation_id != account.installation_id
                or credential.user_id != account.user_id
            ):
                raise SecurityStoreError("device_credential_binding_invalid")
            if credential.status is DeviceCredentialStatus.ACTIVE:
                active += 1
            elif credential.status is DeviceCredentialStatus.PENDING:
                pending += 1
        if active > 1 or pending > 1:
            raise SecurityStoreError("device_credential_cardinality_invalid")


class _WriteTransaction:
    def __init__(self, repository: SQLiteSecurityRepository):
        self._repository = repository
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self._connection = self._repository._connect_write()
        self._connection.execute("BEGIN IMMEDIATE")
        return self._connection

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        assert self._connection is not None
        try:
            if exc_type:
                self._connection.execute("ROLLBACK")
            else:
                self._repository._failure_injector("before_write_commit")
                self._connection.execute("COMMIT")
                self._repository._failure_injector("after_write_commit")
        finally:
            self._connection.close()
            self._repository._permissions.secure_sqlite_files(
                self._repository.database_path
            )
        return False


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Security timestamps must be timezone-aware UTC values.")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _optional_datetime(value: datetime | None) -> str | None:
    return None if value is None else _format_datetime(value)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SecurityStoreError("security_timestamp_invalid")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None:
        raise SecurityStoreError("security_timestamp_invalid")
    return parsed.astimezone(timezone.utc)


def _parse_required_datetime(value: str) -> datetime:
    parsed = _parse_optional_datetime(value)
    if parsed is None:
        raise SecurityStoreError("security_timestamp_invalid")
    return parsed


def _latest(first: datetime | None, second: datetime | None) -> datetime | None:
    values = tuple(value for value in (first, second) if value is not None)
    return max(values) if values else None


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
