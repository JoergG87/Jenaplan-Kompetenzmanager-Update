"""Explicit, Qt-free database connection engines.

SQLCipher is intentionally available only through direct construction.  This
module does not inspect environment variables and never falls back from a
requested cipher connection to the standard-library sqlite3 driver.
"""

from __future__ import annotations

from enum import Enum
import importlib
from importlib import metadata
import os
from pathlib import Path
import sqlite3
from typing import Any, Protocol


_SQLITE_HEADER = b"SQLite format 3\x00"
_SQLCIPHER_KEY_BYTES = 32
_SQLCIPHER_PAGE_SIZE = 4096
SQLCIPHER_SPIKE_BINDING_VERSION = "0.6.2"
SQLCIPHER_SPIKE_ENGINE_VERSION = "4.12.0 community"
SQLCIPHER_PRODUCT_TARGET_VERSION = "4.17.0"
SQLCIPHER_4_17_BINDING_VERSION = "0.6.2+jkm.sqlcipher4170.1"
SQLCIPHER_4_17_ENGINE_VERSION = "4.17.0 community"
SQLCIPHER_4_17_SQLITE_VERSION = "3.53.3"
SQLITE_RUNTIME_VERSION = sqlite3.sqlite_version


class DatabaseEngine(str, Enum):
    SQLITE = "sqlite"
    SQLCIPHER = "sqlcipher"


DEFAULT_DATABASE_ENGINE = DatabaseEngine.SQLITE


class DatabaseEngineError(RuntimeError):
    """Sanitized engine failure that contains no path, SQL, or key material."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SQLCipherUnavailableError(DatabaseEngineError):
    pass


class SQLCipherVersionError(DatabaseEngineError):
    pass


class DatabaseKeyMissingError(DatabaseEngineError):
    pass


class DatabaseKeyInvalidError(DatabaseEngineError):
    pass


class DatabaseKeyRejectedError(DatabaseEngineError):
    """The key/header/format combination could not authenticate.

    SQLCipher does not reliably distinguish a wrong key from encrypted-header
    corruption or incompatible cipher parameters at this boundary.
    """


class DatabaseCorruptError(DatabaseEngineError):
    pass


class DatabaseFormatUnsupportedError(DatabaseEngineError):
    pass


class DatabaseEngineConfigurationError(DatabaseEngineError):
    pass


class DatabaseConnectionProvider(Protocol):
    engine: DatabaseEngine

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> Any: ...


class SQLiteConnectionProvider:
    """Standard SQLite provider and unchanged product default."""

    engine = DatabaseEngine.SQLITE

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> sqlite3.Connection:
        if key_material is not None:
            raise DatabaseEngineConfigurationError("sqlite_key_not_supported")
        database_path = Path(path)
        if create:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(database_path)
        else:
            _require_existing_regular_file(database_path)
            connection = sqlite3.connect(
                f"{database_path.resolve().as_uri()}?mode=rw", uri=True
            )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class SQLiteReadOnlyConnectionProvider:
    """Existing-file SQLite provider which cannot create or mutate a store."""

    engine = DatabaseEngine.SQLITE

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> sqlite3.Connection:
        if create or key_material is not None:
            raise DatabaseEngineConfigurationError(
                "sqlite_read_only_configuration_invalid"
            )
        database_path = Path(path)
        _require_existing_regular_file(database_path)
        try:
            connection = sqlite3.connect(
                f"{database_path.resolve().as_uri()}?mode=ro&immutable=1",
                uri=True,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error:
            raise DatabaseEngineConfigurationError(
                "sqlite_read_only_open_failed"
            ) from None


class SQLCipherConnectionProvider:
    """Isolated SQLCipher provider with explicit keying and no fallback."""

    engine = DatabaseEngine.SQLCIPHER

    def __init__(
        self,
        *,
        expected_binding_version: str = SQLCIPHER_SPIKE_BINDING_VERSION,
        expected_engine_version: str = SQLCIPHER_SPIKE_ENGINE_VERSION,
        driver_loader=None,
        binding_version_loader=None,
    ) -> None:
        self._expected_binding_version = expected_binding_version
        self._expected_engine_version = expected_engine_version
        self._driver_loader = driver_loader or _load_sqlcipher_driver
        self._binding_version_loader = (
            binding_version_loader or _load_sqlcipher_binding_version
        )

    @property
    def expected_binding_version(self) -> str:
        return self._expected_binding_version

    @property
    def expected_engine_version(self) -> str:
        return self._expected_engine_version

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> Any:
        key_buffer = _validated_key_buffer(key_material)
        connection = None
        creation_identity: tuple[int, int] | None = None
        database_path = Path(path)
        try:
            existing_identity = self._validate_path(database_path, create=create)
            driver = self._load_driver()
            self._probe_engine_version(driver)
            database_path.parent.mkdir(parents=True, exist_ok=True)
            if create:
                creation_identity = _reserve_new_database_file(database_path)
                connection = driver.connect(database_path, cached_statements=0)
                _require_same_file_identity(database_path, creation_identity)
            else:
                assert existing_identity is not None
                connection = driver.connect(
                    f"{database_path.resolve().as_uri()}?mode=rw",
                    uri=True,
                    cached_statements=0,
                )
                _require_same_file_identity(database_path, existing_identity)
            self._apply_key(connection, key_buffer)
            self._verify_engine_version(connection)
            self._configure_cipher_before_authentication(connection)
            self._authenticate_schema(connection)
            self._configure_database_after_authentication(connection, driver)
            self.verify_integrity(connection)
            return connection
        except DatabaseEngineError:
            if connection is not None:
                _close_without_masking_primary_error(connection)
            if creation_identity is not None:
                _unlink_if_same_file_identity(database_path, creation_identity)
            raise
        except Exception:
            if connection is not None:
                _close_without_masking_primary_error(connection)
            if creation_identity is not None:
                _unlink_if_same_file_identity(database_path, creation_identity)
            raise DatabaseEngineConfigurationError(
                "sqlcipher_connection_failed"
            ) from None
        finally:
            for index in range(len(key_buffer)):
                key_buffer[index] = 0

    def verify_integrity(self, connection: Any) -> None:
        try:
            cipher_rows = connection.execute(
                "PRAGMA cipher_integrity_check"
            ).fetchall()
            integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
            foreign_key_rows = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        except Exception:
            raise DatabaseCorruptError("sqlcipher_database_corrupt") from None
        integrity_ok = (
            len(integrity_rows) == 1 and str(integrity_rows[0][0]) == "ok"
        )
        if cipher_rows or not integrity_ok or foreign_key_rows:
            raise DatabaseCorruptError("sqlcipher_database_corrupt")

    def connect_read_only(
        self,
        path: Path,
        *,
        key_material: bytes | bytearray | memoryview | None = None,
    ) -> Any:
        key_buffer = _validated_key_buffer(key_material)
        connection = None
        database_path = Path(path)
        try:
            existing_identity = self._validate_path(
                database_path,
                create=False,
            )
            assert existing_identity is not None
            before = database_path.stat()
            driver = self._load_driver()
            self._probe_engine_version(driver)
            connection = driver.connect(
                f"{database_path.resolve().as_uri()}?mode=ro&immutable=1",
                uri=True,
                cached_statements=0,
            )
            _require_same_file_identity(database_path, existing_identity)
            self._apply_key(connection, key_buffer)
            self._verify_engine_version(connection)
            self._configure_cipher_before_authentication(connection)
            self._authenticate_schema(connection)
            connection.row_factory = driver.Row
            connection.execute("PRAGMA query_only = ON")
            connection.execute("PRAGMA foreign_keys = ON")
            self.verify_integrity(connection)
            after = database_path.stat()
            if (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            ) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise DatabaseEngineConfigurationError(
                    "database_read_only_changed"
                )
            return connection
        except DatabaseEngineError:
            if connection is not None:
                _close_without_masking_primary_error(connection)
            raise
        except Exception:
            if connection is not None:
                _close_without_masking_primary_error(connection)
            raise DatabaseEngineConfigurationError(
                "sqlcipher_read_only_connection_failed"
            ) from None
        finally:
            for index in range(len(key_buffer)):
                key_buffer[index] = 0

    def _load_driver(self):
        try:
            binding_version = self._binding_version_loader()
            driver = self._driver_loader()
        except (ImportError, ModuleNotFoundError, metadata.PackageNotFoundError):
            raise SQLCipherUnavailableError("sqlcipher_unavailable") from None
        if binding_version != self._expected_binding_version:
            raise SQLCipherVersionError("sqlcipher_binding_version_incompatible")
        if not callable(getattr(driver, "connect", None)) or not hasattr(driver, "Row"):
            raise DatabaseEngineConfigurationError(
                "sqlcipher_driver_contract_invalid"
            )
        return driver

    def _probe_engine_version(self, driver: Any) -> None:
        probe = None
        try:
            probe = driver.connect(":memory:", cached_statements=0)
            self._verify_engine_version(probe)
        except DatabaseEngineError:
            raise
        except Exception:
            raise SQLCipherUnavailableError("sqlcipher_engine_unavailable") from None
        finally:
            if probe is not None:
                _close_without_masking_primary_error(probe)

    def _validate_path(
        self, path: Path, *, create: bool
    ) -> tuple[int, int] | None:
        if create:
            if path.exists() or path.is_symlink():
                raise DatabaseEngineConfigurationError(
                    "sqlcipher_create_target_exists"
                )
            return None
        _require_existing_regular_file(path)
        try:
            status = path.stat()
            size = status.st_size
            with path.open("rb") as database_file:
                header = database_file.read(len(_SQLITE_HEADER))
        except OSError:
            raise DatabaseEngineConfigurationError(
                "database_path_unreadable"
            ) from None
        if header == _SQLITE_HEADER:
            raise DatabaseFormatUnsupportedError(
                "plaintext_sqlite_not_supported"
            )
        if size == 0 or size % _SQLCIPHER_PAGE_SIZE != 0:
            raise DatabaseCorruptError("sqlcipher_database_corrupt")
        return status.st_dev, status.st_ino

    @staticmethod
    def _apply_key(connection: Any, key_buffer: bytearray) -> None:
        key_hex = key_buffer.hex()
        statement = f'PRAGMA key = "x\'{key_hex}\'"'
        try:
            connection.execute(statement)
        except Exception:
            raise DatabaseKeyRejectedError(
                "database_key_or_header_rejected"
            ) from None
        finally:
            statement = ""
            key_hex = ""

    def _verify_engine_version(self, connection: Any) -> None:
        try:
            row = connection.execute("PRAGMA cipher_version").fetchone()
        except Exception:
            raise SQLCipherUnavailableError("sqlcipher_engine_unavailable") from None
        if row is None or str(row[0]) != self._expected_engine_version:
            raise SQLCipherVersionError("sqlcipher_engine_version_incompatible")

    @staticmethod
    def _configure_cipher_before_authentication(connection: Any) -> None:
        try:
            connection.execute("PRAGMA cipher_plaintext_header_size = 0")
            connection.execute(f"PRAGMA cipher_page_size = {_SQLCIPHER_PAGE_SIZE}")
            connection.execute("PRAGMA kdf_iter = 256000")
            connection.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
            connection.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
            connection.execute("PRAGMA cipher_use_hmac = ON")
            connection.execute("PRAGMA cipher_memory_security = ON")
            connection.execute("PRAGMA temp_store = MEMORY")
            expected = {
                "cipher_status": "1",
                "cipher_plaintext_header_size": "0",
                "cipher_page_size": str(_SQLCIPHER_PAGE_SIZE),
                "kdf_iter": "256000",
                "cipher_hmac_algorithm": "hmac_sha512",
                "cipher_kdf_algorithm": "pbkdf2_hmac_sha512",
                "cipher_use_hmac": "1",
                "cipher_memory_security": "1",
                "temp_store": "2",
            }
            for pragma, value in expected.items():
                row = connection.execute(f"PRAGMA {pragma}").fetchone()
                if row is None or str(row[0]).lower() != value:
                    raise DatabaseEngineConfigurationError(
                        "sqlcipher_pragma_verification_failed"
                    )
        except DatabaseEngineError:
            raise
        except Exception:
            raise DatabaseEngineConfigurationError(
                "sqlcipher_cipher_configuration_failed"
            ) from None

    @staticmethod
    def _authenticate_schema(connection: Any) -> None:
        try:
            connection.execute("SELECT count(*) FROM sqlite_schema").fetchone()
        except Exception as error:
            if getattr(error, "sqlite_errorcode", None) == 26:
                raise DatabaseKeyRejectedError(
                    "database_key_or_header_rejected"
                ) from None
            raise DatabaseEngineConfigurationError(
                "sqlcipher_schema_read_failed"
            ) from None

    @staticmethod
    def _configure_database_after_authentication(connection: Any, driver: Any) -> None:
        try:
            connection.row_factory = driver.Row
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA secure_delete = ON")
            connection.execute("PRAGMA foreign_keys = ON")
            expected = {
                "journal_mode": "delete",
                "synchronous": "2",
                "secure_delete": "1",
                "foreign_keys": "1",
            }
            for pragma, value in expected.items():
                row = connection.execute(f"PRAGMA {pragma}").fetchone()
                if row is None or str(row[0]).lower() != value:
                    raise DatabaseEngineConfigurationError(
                        "sqlcipher_pragma_verification_failed"
                    )
        except DatabaseEngineError:
            raise
        except Exception:
            raise DatabaseEngineConfigurationError(
                "sqlcipher_database_configuration_failed"
            ) from None


def _validated_key_buffer(
    key_material: bytes | bytearray | memoryview | None,
) -> bytearray:
    if key_material is None:
        raise DatabaseKeyMissingError("database_key_missing")
    if not isinstance(key_material, (bytes, bytearray, memoryview)):
        raise DatabaseKeyInvalidError("database_key_invalid")
    key_buffer = bytearray(key_material)
    if len(key_buffer) != _SQLCIPHER_KEY_BYTES:
        for index in range(len(key_buffer)):
            key_buffer[index] = 0
        raise DatabaseKeyInvalidError("database_key_invalid")
    return key_buffer


def _require_existing_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise DatabaseEngineConfigurationError("database_path_invalid")


def _load_sqlcipher_driver():
    return importlib.import_module("sqlcipher3.dbapi2")


def _load_sqlcipher_binding_version() -> str:
    return metadata.version("sqlcipher3")


def _reserve_new_database_file(path: Path) -> tuple[int, int]:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        raise DatabaseEngineConfigurationError(
            "sqlcipher_create_target_exists"
        ) from None
    except OSError:
        raise DatabaseEngineConfigurationError(
            "sqlcipher_create_target_invalid"
        ) from None
    try:
        status = os.fstat(descriptor)
        return status.st_dev, status.st_ino
    finally:
        os.close(descriptor)


def _require_same_file_identity(path: Path, expected: tuple[int, int]) -> None:
    try:
        status = path.lstat()
    except OSError:
        raise DatabaseEngineConfigurationError(
            "sqlcipher_create_target_changed"
        ) from None
    if path.is_symlink() or (status.st_dev, status.st_ino) != expected:
        raise DatabaseEngineConfigurationError(
            "sqlcipher_create_target_changed"
        )


def _close_without_masking_primary_error(connection: Any) -> None:
    try:
        connection.close()
    except Exception:
        pass


def _unlink_if_same_file_identity(path: Path, expected: tuple[int, int]) -> None:
    try:
        status = path.lstat()
        if path.is_symlink() or (status.st_dev, status.st_ino) != expected:
            return
        path.unlink()
    except OSError:
        pass
