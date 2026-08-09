"""Marker-bound Final-V3 runtime on an exact SQLCipher 4.17 provider.

This module is intentionally absent from product startup.  It composes the
existing DMK/Database-Key runtime only after an explicit authenticated test
call and never falls back to the standard-library sqlite3 driver.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from enum import StrEnum
import os
from pathlib import Path
import stat
from typing import Any, Mapping, Protocol

from src.core.database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityStatus,
)
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
    DatabaseEngine,
    DatabaseEngineConfigurationError,
    DatabaseEngineError,
    SQLCipherConnectionProvider,
)
from src.core.final_v3_schema import FinalV3SchemaError, FinalV3SchemaInitializer
from src.core.sqlite_store import SQLiteDatabase

from .database_key_runtime import (
    DMK_DATABASE_KEY_RUNTIME_GATE_ENV,
    DMK_DATABASE_KEY_RUNTIME_GATE_VALUE,
    DMK_DATABASE_KEY_RUNTIME_ROOT_ENV,
    DatabaseKeyRuntimeError,
    DatabaseKeyRuntimeGate,
    DatabaseKeyRuntimePaths,
    LoadedDatabaseKeyRuntime,
    build_database_key_runtime,
)
from .infrastructure.system import PlatformFilePermissionManager


FINAL_V3_SQLCIPHER_RUNTIME_GATE_ENV = "JKM_FINAL_V3_SQLCIPHER_RUNTIME_TEST"
FINAL_V3_SQLCIPHER_RUNTIME_GATE_VALUE = "1"
FINAL_V3_SQLCIPHER_RUNTIME_MARKER = ".jkm-final-v3-sqlcipher-runtime-test-root"
FINAL_V3_SQLCIPHER_RUNTIME_MARKER_BYTES = (
    b"jenaplan-final-v3-sqlcipher-runtime-test-root-v1\n"
)
FINAL_V3_SQLCIPHER_RUNTIME_DIRECTORY = "final-v3-sqlcipher-runtime-v1"
FINAL_V3_SQLCIPHER_DATABASE_FILENAME = "final-v3.sqlcipher"
_SQLITE_HEADER = b"SQLite format 3\x00"


class FinalV3SQLCipherRuntimeDecisionState(StrEnum):
    DISABLED = "DISABLED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class FinalV3SQLCipherRuntimeOperation(StrEnum):
    CLASSIFY = "classify"
    LOAD_KEYS = "load_keys"
    CREATE_DATABASE = "create_database"
    INITIALIZE_SCHEMA = "initialize_schema"
    INSPECT_DATABASE = "inspect_database"
    OPEN_RUNTIME = "open_runtime"


class FinalV3SQLCipherRuntimeError(RuntimeError):
    """Sanitized failure without a path, SQL statement, or key material."""

    def __init__(
        self,
        code: str,
        *,
        operation: FinalV3SQLCipherRuntimeOperation,
    ) -> None:
        self.code = code
        self.operation = operation
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class FinalV3SQLCipherRuntimePaths:
    root: Path
    key_runtime: DatabaseKeyRuntimePaths
    runtime_root: Path
    database: Path

    @classmethod
    def for_key_runtime(
        cls, key_runtime: DatabaseKeyRuntimePaths
    ) -> "FinalV3SQLCipherRuntimePaths":
        runtime_root = key_runtime.root / FINAL_V3_SQLCIPHER_RUNTIME_DIRECTORY
        return cls(
            root=key_runtime.root,
            key_runtime=key_runtime,
            runtime_root=runtime_root,
            database=runtime_root / FINAL_V3_SQLCIPHER_DATABASE_FILENAME,
        )


@dataclass(frozen=True, slots=True)
class KeyedFinalV3CompatibilityReport:
    cipher_version: str
    cipher_provider: str
    cipher_provider_version: str
    sqlite_version: str
    sqlite_user_version: int
    schema_fingerprint: str
    schema_object_count: int


@dataclass(frozen=True)
class OpenedFinalV3SQLCipherRuntime:
    database: SQLiteDatabase
    compatibility: KeyedFinalV3CompatibilityReport
    database_context_id: str
    database_key_id: str
    database_key_generation: int
    first_run: bool
    loaded_keys: LoadedDatabaseKeyRuntime = field(repr=False)


@dataclass(frozen=True)
class FinalV3SQLCipherRuntimeDecision:
    state: FinalV3SQLCipherRuntimeDecisionState
    runtime: OpenedFinalV3SQLCipherRuntime | None = field(
        default=None, repr=False
    )
    error_code: str | None = None
    error_operation: FinalV3SQLCipherRuntimeOperation | None = None


class FinalV3SQLCipherRuntimeGate:
    """Additional marker gate layered on the existing key-runtime root gate."""

    def resolve(
        self, environ: Mapping[str, str] | None = None
    ) -> FinalV3SQLCipherRuntimeDecision:
        environment = os.environ if environ is None else environ
        gate_value = environment.get(FINAL_V3_SQLCIPHER_RUNTIME_GATE_ENV, "")
        if gate_value == "":
            return FinalV3SQLCipherRuntimeDecision(
                FinalV3SQLCipherRuntimeDecisionState.DISABLED
            )
        if gate_value != FINAL_V3_SQLCIPHER_RUNTIME_GATE_VALUE:
            return _blocked("final_v3_sqlcipher_runtime_gate_value_invalid")
        if (
            environment.get(DMK_DATABASE_KEY_RUNTIME_GATE_ENV, "")
            != DMK_DATABASE_KEY_RUNTIME_GATE_VALUE
        ):
            return _blocked("database_key_runtime_gate_required")
        try:
            self.require_paths(
                environment.get(DMK_DATABASE_KEY_RUNTIME_ROOT_ENV, "")
            )
        except (DatabaseKeyRuntimeError, FinalV3SQLCipherRuntimeError) as error:
            return _blocked(
                getattr(error, "code", "final_v3_sqlcipher_runtime_gate_invalid")
            )
        return FinalV3SQLCipherRuntimeDecision(
            FinalV3SQLCipherRuntimeDecisionState.ACTIVE
        )

    @staticmethod
    def require_paths(raw_root: str) -> FinalV3SQLCipherRuntimePaths:
        key_paths = DatabaseKeyRuntimeGate.require_paths(raw_root)
        _require_marker(
            key_paths.root / FINAL_V3_SQLCIPHER_RUNTIME_MARKER,
            FINAL_V3_SQLCIPHER_RUNTIME_MARKER_BYTES,
        )
        return FinalV3SQLCipherRuntimePaths.for_key_runtime(key_paths)


class FinalV3SQLCipherRuntimeScope(Protocol):
    """Revalidatable capability for one exact runtime-path composition."""

    def require_paths(self) -> FinalV3SQLCipherRuntimePaths: ...


class MarkerGatedFinalV3SQLCipherRuntimeScope:
    """Preserve the existing double-marker test scope without product bypass."""

    def __init__(self, environ: Mapping[str, str]) -> None:
        self._environment = dict(environ)

    def require_paths(self) -> FinalV3SQLCipherRuntimePaths:
        gate = FinalV3SQLCipherRuntimeGate()
        decision = gate.resolve(self._environment)
        if decision.state is not FinalV3SQLCipherRuntimeDecisionState.ACTIVE:
            raise FinalV3SQLCipherRuntimeError(
                decision.error_code or "final_v3_sqlcipher_runtime_gate_required",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        return gate.require_paths(
            self._environment.get(DMK_DATABASE_KEY_RUNTIME_ROOT_ENV, "")
        )


class FinalV3SQLCipherConnectionFactory:
    """Path- and key-bound provider shared by schema, repositories and adapters."""

    engine = DatabaseEngine.SQLCIPHER

    def __init__(
        self,
        *,
        provider: SQLCipherConnectionProvider,
        paths: FinalV3SQLCipherRuntimePaths,
        loaded_keys: LoadedDatabaseKeyRuntime,
        environ: Mapping[str, str],
        scope: FinalV3SQLCipherRuntimeScope | None = None,
    ) -> None:
        if (
            provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
            or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION
        ):
            raise FinalV3SQLCipherRuntimeError(
                "sqlcipher_417_provider_configuration_invalid",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        self._scope = scope or MarkerGatedFinalV3SQLCipherRuntimeScope(environ)
        try:
            expected_paths = self._scope.require_paths()
        except FinalV3SQLCipherRuntimeError:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_connection_scope_invalid",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            ) from None
        if paths != expected_paths:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_connection_scope_invalid",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        _require_runtime_scope(paths, expected_paths=expected_paths)
        self._provider = provider
        self._paths = paths
        self._allowed_path = paths.database
        self._loaded_keys = loaded_keys

    def connect(
        self,
        path: Path,
        *,
        create: bool,
        key_material=None,
    ) -> Any:
        self._require_scope(path, key_material)
        return self._provider.connect(
            self._allowed_path,
            create=create,
            key_material=self._loaded_keys.database_key.key_material,
        )

    def connect_read_only(self, path: Path) -> Any:
        self._require_scope(path, None)
        return self._provider.connect_read_only(
            self._allowed_path,
            key_material=self._loaded_keys.database_key.key_material,
        )

    def _require_scope(self, path: Path, key_material) -> None:
        expected_paths = self._scope.require_paths()
        _require_runtime_scope(self._paths, expected_paths=expected_paths)
        if key_material is not None or Path(path) != self._allowed_path:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_connection_scope_invalid",
                operation=FinalV3SQLCipherRuntimeOperation.OPEN_RUNTIME,
            )


class KeyedFinalV3CompatibilityInspector:
    """Inspect only an already-keyed SQLCipher connection without mutation."""

    def inspect_connection(self, connection: Any) -> KeyedFinalV3CompatibilityReport:
        try:
            before_changes = int(connection.total_changes)
            cipher_version = str(
                _required_scalar(connection, "PRAGMA cipher_version")
            )
            cipher_status = str(
                _required_scalar(connection, "PRAGMA cipher_status")
            )
            cipher_provider = str(
                _required_scalar(connection, "PRAGMA cipher_provider")
            )
            provider_version = str(
                _required_scalar(connection, "PRAGMA cipher_provider_version")
            )
            sqlite_version = str(
                _required_scalar(connection, "SELECT sqlite_version()")
            )
            cipher_integrity = connection.execute(
                "PRAGMA cipher_integrity_check"
            ).fetchall()
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            foreign_keys_enabled = str(
                _required_scalar(connection, "PRAGMA foreign_keys")
            )
            compatibility = DatabaseCompatibilityInspector().inspect_connection(
                connection
            )
            after_changes = int(connection.total_changes)
        except FinalV3SQLCipherRuntimeError:
            raise
        except Exception:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_inspection_failed",
                operation=FinalV3SQLCipherRuntimeOperation.INSPECT_DATABASE,
            ) from None

        if cipher_version != SQLCIPHER_4_17_ENGINE_VERSION:
            raise _inspection_error("sqlcipher_417_engine_version_incompatible")
        if cipher_status != "1":
            raise _inspection_error("sqlcipher_417_cipher_inactive")
        if cipher_provider != "commoncrypto" or not provider_version:
            raise _inspection_error("sqlcipher_417_crypto_provider_incompatible")
        if sqlite_version != SQLCIPHER_4_17_SQLITE_VERSION:
            raise _inspection_error("sqlcipher_417_sqlite_version_incompatible")
        integrity_ok = (
            len(integrity) == 1 and str(integrity[0][0]).lower() == "ok"
        )
        if (
            cipher_integrity
            or not integrity_ok
            or foreign_keys
            or foreign_keys_enabled != "1"
        ):
            raise _inspection_error("final_v3_sqlcipher_integrity_failed")
        if (
            compatibility.status is not DatabaseCompatibilityStatus.EXACT
            or compatibility.version.sqlite_user_version != FINAL_SCHEMA_VERSION
            or compatibility.schema_identity.fingerprint
            != FINAL_SCHEMA_FINGERPRINT
        ):
            raise _inspection_error("final_v3_sqlcipher_schema_incompatible")
        if before_changes != after_changes:
            raise _inspection_error("final_v3_sqlcipher_inspection_mutated")
        return KeyedFinalV3CompatibilityReport(
            cipher_version=cipher_version,
            cipher_provider=cipher_provider,
            cipher_provider_version=provider_version,
            sqlite_version=sqlite_version,
            sqlite_user_version=compatibility.version.sqlite_user_version,
            schema_fingerprint=compatibility.schema_identity.fingerprint,
            schema_object_count=compatibility.schema_identity.object_count,
        )


class FinalV3SQLCipherRuntimeCoordinator:
    """Fail-closed First-Run and restart composition for the gated test path."""

    def __init__(
        self,
        *,
        paths: FinalV3SQLCipherRuntimePaths,
        account_loader,
        authentication_confirmed: bool,
        technical_first_run_confirmed: bool,
        key_store=None,
        random_source=None,
        clock=None,
        sqlcipher_provider: SQLCipherConnectionProvider | None = None,
        fault_hook=None,
        environ: Mapping[str, str] | None = None,
        scope: FinalV3SQLCipherRuntimeScope | None = None,
        loaded_keys: LoadedDatabaseKeyRuntime | None = None,
    ) -> None:
        environment = os.environ if environ is None else environ
        self._scope = scope or MarkerGatedFinalV3SQLCipherRuntimeScope(environment)
        expected_paths = self._scope.require_paths()
        if paths != expected_paths:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_runtime_scope_invalid",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        self.paths = paths
        self._environment = dict(environment)
        self._account_loader = account_loader
        self._authentication_confirmed = bool(authentication_confirmed)
        self._technical_first_run_confirmed = bool(
            technical_first_run_confirmed
        )
        self._key_store = key_store
        self._random_source = random_source
        self._clock = clock
        self._loaded_keys = loaded_keys
        self._provider = sqlcipher_provider or SQLCipherConnectionProvider(
            expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        )
        self._fault_hook = fault_hook
        self._operation = FinalV3SQLCipherRuntimeOperation.CLASSIFY

    def open(self) -> OpenedFinalV3SQLCipherRuntime:
        try:
            return self._open()
        except FinalV3SQLCipherRuntimeError:
            raise
        except (DatabaseEngineError, DatabaseKeyRuntimeError, FinalV3SchemaError) as error:
            raise FinalV3SQLCipherRuntimeError(
                str(getattr(error, "code", str(error))),
                operation=self._operation,
            ) from None
        except Exception:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_runtime_failed",
                operation=self._operation,
            ) from None

    def _open(self) -> OpenedFinalV3SQLCipherRuntime:
        expected_paths = self._scope.require_paths()
        _require_runtime_scope(self.paths, expected_paths=expected_paths)
        if not self._authentication_confirmed:
            raise FinalV3SQLCipherRuntimeError(
                "authentication_confirmation_required",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        database_exists = _classify_database_path(self.paths.database)
        _require_no_database_sidecars(self.paths.database)
        keyset_exists = _path_exists_or_symlink(
            self.paths.key_runtime.keyset_metadata
        )
        envelope_exists = _path_exists_or_symlink(
            self.paths.key_runtime.envelope_registry
        )
        if database_exists and not (keyset_exists and envelope_exists):
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_database_without_key_store",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        prepared_product_first_run = bool(
            self._loaded_keys is not None
            and self._loaded_keys.first_run
            and self._technical_first_run_confirmed
            and keyset_exists
            and envelope_exists
        )
        if (
            not database_exists
            and (keyset_exists or envelope_exists)
            and not prepared_product_first_run
        ):
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_database_missing_with_key_store",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        if database_exists:
            _reject_plaintext_header(self.paths.database)
        elif not self._technical_first_run_confirmed:
            raise FinalV3SQLCipherRuntimeError(
                "technical_first_run_confirmation_required",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )

        self._operation = FinalV3SQLCipherRuntimeOperation.LOAD_KEYS
        loaded = self._loaded_keys or build_database_key_runtime(
            self.paths.key_runtime,
            account_loader=self._account_loader,
            key_store=self._key_store,
            random_source=self._random_source,
            clock=self._clock,
        ).open_or_create()
        if database_exists and loaded.first_run:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_database_context_contradictory",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )
        if not database_exists and not loaded.first_run:
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_database_missing_after_first_run",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )

        factory = FinalV3SQLCipherConnectionFactory(
            provider=self._provider,
            paths=self.paths,
            loaded_keys=loaded,
            environ=self._environment,
            scope=self._scope,
        )
        inspector = KeyedFinalV3CompatibilityInspector()
        if database_exists:
            self._operation = FinalV3SQLCipherRuntimeOperation.INSPECT_DATABASE
            with closing(
                factory.connect_read_only(self.paths.database)
            ) as connection:
                report = inspector.inspect_connection(connection)
        else:
            permissions = PlatformFilePermissionManager()
            permissions.prepare_directory(self.paths.runtime_root)
            _require_runtime_scope(
                self.paths,
                expected_paths=self._scope.require_paths(),
            )
            self._operation = FinalV3SQLCipherRuntimeOperation.CREATE_DATABASE
            self._emit("before_database_file_creation")
            with closing(
                factory.connect(self.paths.database, create=True)
            ) as connection:
                permissions.secure_sqlite_files(self.paths.database)
                self._emit("after_database_file_creation")
                self._operation = FinalV3SQLCipherRuntimeOperation.INITIALIZE_SCHEMA
                FinalV3SchemaInitializer.initialize_connection(
                    connection,
                    fault_hook=self._fault_hook,
                )
            self._operation = FinalV3SQLCipherRuntimeOperation.INSPECT_DATABASE
            with closing(
                factory.connect_read_only(self.paths.database)
            ) as connection:
                report = inspector.inspect_connection(connection)
            self._emit("after_full_verification")
            permissions.secure_sqlite_files(self.paths.database)

        self._operation = FinalV3SQLCipherRuntimeOperation.OPEN_RUNTIME
        database = SQLiteDatabase(
            self.paths.database,
            connection_provider=factory,
            create=False,
            initialize_schema=False,
        )
        return OpenedFinalV3SQLCipherRuntime(
            database=database,
            compatibility=report,
            database_context_id=loaded.database_context_id,
            database_key_id=loaded.database_key_id,
            database_key_generation=loaded.database_key_generation,
            first_run=loaded.first_run,
            loaded_keys=loaded,
        )

    def _emit(self, boundary: str) -> None:
        if self._fault_hook is not None:
            self._fault_hook(boundary)


def run_gated_final_v3_sqlcipher_runtime(
    *,
    account_loader,
    authentication_confirmed: bool,
    technical_first_run_confirmed: bool = False,
    environ: Mapping[str, str] | None = None,
    key_store=None,
    random_source=None,
    clock=None,
    sqlcipher_provider: SQLCipherConnectionProvider | None = None,
    fault_hook=None,
) -> FinalV3SQLCipherRuntimeDecision:
    """Run only after both environment/root markers and auth confirmation."""

    environment = os.environ if environ is None else environ
    gate = FinalV3SQLCipherRuntimeGate()
    decision = gate.resolve(environment)
    if decision.state is not FinalV3SQLCipherRuntimeDecisionState.ACTIVE:
        return decision
    try:
        paths = gate.require_paths(
            environment.get(DMK_DATABASE_KEY_RUNTIME_ROOT_ENV, "")
        )
        runtime = FinalV3SQLCipherRuntimeCoordinator(
            paths=paths,
            account_loader=account_loader,
            authentication_confirmed=authentication_confirmed,
            technical_first_run_confirmed=technical_first_run_confirmed,
            key_store=key_store,
            random_source=random_source,
            clock=clock,
            sqlcipher_provider=sqlcipher_provider,
            fault_hook=fault_hook,
            environ=environment,
        ).open()
        return FinalV3SQLCipherRuntimeDecision(
            FinalV3SQLCipherRuntimeDecisionState.ACTIVE,
            runtime=runtime,
        )
    except FinalV3SQLCipherRuntimeError as error:
        return FinalV3SQLCipherRuntimeDecision(
            FinalV3SQLCipherRuntimeDecisionState.BLOCKED,
            error_code=error.code,
            error_operation=error.operation,
        )


def _blocked(code: str) -> FinalV3SQLCipherRuntimeDecision:
    return FinalV3SQLCipherRuntimeDecision(
        FinalV3SQLCipherRuntimeDecisionState.BLOCKED,
        error_code=code,
        error_operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
    )


def _inspection_error(code: str) -> FinalV3SQLCipherRuntimeError:
    return FinalV3SQLCipherRuntimeError(
        code,
        operation=FinalV3SQLCipherRuntimeOperation.INSPECT_DATABASE,
    )


def _required_scalar(connection: Any, statement: str) -> object:
    row = connection.execute(statement).fetchone()
    if row is None or row[0] is None:
        raise _inspection_error("final_v3_sqlcipher_inspection_value_missing")
    return row[0]


def _path_exists_or_symlink(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _require_runtime_scope(
    paths: FinalV3SQLCipherRuntimePaths,
    *,
    expected_paths: FinalV3SQLCipherRuntimePaths | None = None,
) -> None:
    expected = expected_paths or FinalV3SQLCipherRuntimeGate.require_paths(
        str(paths.root)
    )
    if paths != expected:
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_runtime_scope_invalid",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        )
    try:
        metadata = paths.runtime_root.lstat()
    except FileNotFoundError:
        return
    except OSError:
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_runtime_root_unreadable",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        ) from None
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or (hasattr(os, "getuid") and metadata.st_uid != os.getuid())
    ):
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_runtime_root_unsafe",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        )
    try:
        if paths.runtime_root.resolve(strict=True) != paths.runtime_root:
            raise OSError
    except OSError:
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_runtime_root_unsafe",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        ) from None


def _classify_database_path(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_database_path_unreadable",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        ) from None
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_database_path_unsafe",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        )
    return True


def _reject_plaintext_header(path: Path) -> None:
    try:
        with path.open("rb") as stream:
            header = stream.read(len(_SQLITE_HEADER))
    except OSError:
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_database_path_unreadable",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        ) from None
    if header == _SQLITE_HEADER:
        raise FinalV3SQLCipherRuntimeError(
            "plaintext_sqlite_not_supported",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        )


def _require_no_database_sidecars(path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(f"{path}{suffix}")
        if sidecar.exists() or sidecar.is_symlink():
            raise FinalV3SQLCipherRuntimeError(
                "final_v3_sqlcipher_recovery_sidecar_present",
                operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
            )


def _require_marker(path: Path, expected: bytes) -> None:
    descriptor: int | None = None
    try:
        status = os.lstat(path)
        if (
            stat.S_ISLNK(status.st_mode)
            or not stat.S_ISREG(status.st_mode)
            or stat.S_IMODE(status.st_mode) & 0o077
            or (hasattr(os, "getuid") and status.st_uid != os.getuid())
        ):
            raise OSError
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino) != (status.st_dev, status.st_ino)
            or opened.st_size != len(expected)
            or os.read(descriptor, len(expected) + 1) != expected
        ):
            raise OSError
    except OSError:
        raise FinalV3SQLCipherRuntimeError(
            "final_v3_sqlcipher_runtime_marker_invalid",
            operation=FinalV3SQLCipherRuntimeOperation.CLASSIFY,
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
