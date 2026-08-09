"""Authenticated product composition for a fresh encrypted Final-V3 runtime."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
import os
from pathlib import Path
import secrets
import stat
import tempfile
from typing import Any, Protocol

from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
    DatabaseEngineError,
    SQLCipherConnectionProvider,
)

from .database_key_runtime import (
    DatabaseKeyRuntimeError,
    DatabaseKeyRuntimePaths,
    build_database_key_runtime,
)
from .domain import validate_uuid4
from .final_v3_document_runtime import (
    FinalV3DocumentRuntimeCoordinator,
    FinalV3DocumentRuntimeError,
    FinalV3DocumentRuntimePaths,
    OpenedFinalV3DocumentRuntime,
)
from .final_v3_sqlcipher_runtime import (
    FinalV3SQLCipherRuntimeCoordinator,
    FinalV3SQLCipherRuntimeError,
    FinalV3SQLCipherRuntimePaths,
    FinalV3SQLCipherRuntimeScope,
    KeyedFinalV3CompatibilityInspector,
)
from .infrastructure.system import SystemClock, SystemRandomSource


PILOT_FIRST_RUN_SCHOOL_YEAR_ID = "SY-PILOT-2026-27"
PILOT_FIRST_RUN_SCHOOL_YEAR_LABEL = "2026/27"
PILOT_FIRST_RUN_SCHOOL_YEAR_START = date(2026, 8, 1)
PILOT_FIRST_RUN_SCHOOL_YEAR_END = date(2027, 7, 31)
_SQLITE_HEADER = b"SQLite format 3\x00"
_LEGACY_RESTORE_DIRECTORIES = (
    "restore-handoffs",
    "restore-staging",
    "restore-transactions",
)


class CipherProductRuntimeOperation(StrEnum):
    CLASSIFY = "classify"
    VERIFY_ENGINE = "verify_engine"
    LOAD_KEYS = "load_keys"
    OPEN_FINAL_V3 = "open_final_v3"
    OPEN_DOCUMENTS = "open_documents"
    INITIALIZE_SCHOOL_YEAR = "initialize_school_year"
    VERIFY_RUNTIME = "verify_runtime"


class CipherProductRuntimeError(RuntimeError):
    """Sanitized fail-closed product-start error."""

    def __init__(self, code: str, *, operation: CipherProductRuntimeOperation) -> None:
        self.code = code
        self.operation = operation
        super().__init__(code)


class CipherProductPaths(Protocol):
    root: Path
    database: Path
    documents: Path
    backups: Path

    @property
    def key_runtime_metadata(self) -> Path: ...

    @property
    def keyset_metadata(self) -> Path: ...

    @property
    def database_key_envelope_registry(self) -> Path: ...

    @property
    def final_v3_runtime(self) -> Path: ...

    @property
    def final_v3_database(self) -> Path: ...

    @property
    def document_companion_database(self) -> Path: ...

    @property
    def encrypted_document_storage(self) -> Path: ...


@dataclass(frozen=True)
class OpenedCipherProductRuntime:
    """One verified runtime shared by repositories, adapter and product shell."""

    runtime: OpenedFinalV3DocumentRuntime = field(repr=False)
    first_run: bool
    installation_id: str
    database_context_id: str
    dmk_key_id: str
    dmk_generation: int
    dmk_fingerprint_sha256: str
    database_key_id: str
    database_key_generation: int
    database_key_fingerprint_sha256: str

    @property
    def database(self):
        return self.runtime.final_v3.database

    @property
    def documents(self):
        return self.runtime.documents


class CipherProductRuntimeScope(FinalV3SQLCipherRuntimeScope):
    """Closed scope binding security foundations to productive RuntimePaths."""

    def __init__(self, paths: CipherProductPaths) -> None:
        self._paths = paths
        self._root = Path(paths.root)

    def require_paths(self) -> FinalV3SQLCipherRuntimePaths:
        root = _require_product_root(self._root)
        key_paths = DatabaseKeyRuntimePaths.for_root(root)
        expected = FinalV3SQLCipherRuntimePaths.for_key_runtime(key_paths)
        document_paths = FinalV3DocumentRuntimePaths.for_final_v3(expected)
        roles = (
            (Path(self._paths.database), root / "kompetenzmanager.sqlite"),
            (Path(self._paths.documents), root / "documents"),
            (Path(self._paths.key_runtime_metadata), key_paths.metadata_root),
            (Path(self._paths.keyset_metadata), key_paths.keyset_metadata),
            (
                Path(self._paths.database_key_envelope_registry),
                key_paths.envelope_registry,
            ),
            (Path(self._paths.final_v3_runtime), expected.runtime_root),
            (Path(self._paths.final_v3_database), expected.database),
            (
                Path(self._paths.document_companion_database),
                document_paths.database,
            ),
            (
                Path(self._paths.encrypted_document_storage),
                document_paths.container_root,
            ),
            (Path(self._paths.backups), root / "backups"),
        )
        if any(observed != required for observed, required in roles):
            raise CipherProductRuntimeError(
                "cipher_product_runtime_paths_invalid",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            )
        _require_private_directory_if_present(key_paths.metadata_root)
        _require_private_directory_if_present(expected.runtime_root)
        return expected


class CipherProductRuntimeCoordinator:
    """Open only a complete restart or one explicitly authorized fresh install."""

    def __init__(
        self,
        *,
        paths: CipherProductPaths,
        account_loader,
        authentication_confirmed: bool,
        first_run_allowed: bool,
        key_store=None,
        random_source=None,
        clock=None,
        sqlcipher_provider: SQLCipherConnectionProvider | None = None,
        fault_hook=None,
    ) -> None:
        self.paths = paths
        self.account_loader = account_loader
        self.authentication_confirmed = bool(authentication_confirmed)
        self.first_run_allowed = bool(first_run_allowed)
        self.key_store = key_store
        self.random = random_source or SystemRandomSource()
        self.clock = clock or SystemClock()
        self.provider = sqlcipher_provider or SQLCipherConnectionProvider(
            expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        )
        self.fault_hook = fault_hook
        self.scope = CipherProductRuntimeScope(paths)
        self.operation = CipherProductRuntimeOperation.CLASSIFY

    def open(self) -> OpenedCipherProductRuntime:
        try:
            return self._open()
        except CipherProductRuntimeError:
            raise
        except (FinalV3SQLCipherRuntimeError, FinalV3DocumentRuntimeError) as error:
            raise CipherProductRuntimeError(
                str(getattr(error, "code", "cipher_product_runtime_failed")),
                operation=self.operation,
            ) from None
        except DatabaseKeyRuntimeError as error:
            raise CipherProductRuntimeError(
                error.code,
                operation=CipherProductRuntimeOperation.LOAD_KEYS,
            ) from None
        except DatabaseEngineError as error:
            raise CipherProductRuntimeError(
                error.code,
                operation=CipherProductRuntimeOperation.VERIFY_ENGINE,
            ) from None
        except Exception:
            raise CipherProductRuntimeError(
                "cipher_product_runtime_failed",
                operation=self.operation,
            ) from None

    def _open(self) -> OpenedCipherProductRuntime:
        if not self.authentication_confirmed:
            raise CipherProductRuntimeError(
                "authentication_confirmation_required",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            )
        final_paths = self.scope.require_paths()
        document_paths = FinalV3DocumentRuntimePaths.for_final_v3(final_paths)
        first_run = _classify_product_state(
            self.paths,
            final_paths=final_paths,
            document_paths=document_paths,
            first_run_allowed=self.first_run_allowed,
        )
        account = self.account_loader()
        installation_id = validate_uuid4(getattr(account, "installation_id", ""))
        stable_account_loader = lambda: account

        self.operation = CipherProductRuntimeOperation.VERIFY_ENGINE
        _verify_exact_sqlcipher_runtime(self.provider)

        self.operation = CipherProductRuntimeOperation.LOAD_KEYS
        loaded = build_database_key_runtime(
            final_paths.key_runtime,
            account_loader=stable_account_loader,
            key_store=self.key_store,
            random_source=self.random,
            clock=self.clock,
            fault_hook=self.fault_hook,
        ).open_or_create()
        if loaded.first_run is not first_run:
            raise CipherProductRuntimeError(
                "cipher_product_key_state_contradictory",
                operation=CipherProductRuntimeOperation.LOAD_KEYS,
            )

        self.operation = CipherProductRuntimeOperation.OPEN_FINAL_V3
        final_v3 = FinalV3SQLCipherRuntimeCoordinator(
            paths=final_paths,
            account_loader=stable_account_loader,
            authentication_confirmed=True,
            technical_first_run_confirmed=first_run,
            key_store=self.key_store,
            random_source=self.random,
            clock=self.clock,
            sqlcipher_provider=self.provider,
            fault_hook=self.fault_hook,
            environ={},
            scope=self.scope,
            loaded_keys=loaded,
        ).open()

        self.operation = CipherProductRuntimeOperation.OPEN_DOCUMENTS
        opened = FinalV3DocumentRuntimeCoordinator(
            final_v3=final_v3,
            paths=document_paths,
            loaded_keys=loaded,
            installation_id=installation_id,
            document_database_create_allowed=first_run,
            provider=self.provider,
            scope=self.scope,
            environ={},
            source_root=None,
            random_source=self.random,
            clock=self.clock,
            fault_hook=self.fault_hook,
        ).open()

        if first_run:
            self.operation = CipherProductRuntimeOperation.INITIALIZE_SCHOOL_YEAR
            _initialize_first_run_school_year(opened, self.clock)
        else:
            _require_completed_fachlicher_first_run(opened)

        self.operation = CipherProductRuntimeOperation.VERIFY_RUNTIME
        with closing(opened.final_v3.database.connect()) as connection:
            KeyedFinalV3CompatibilityInspector().inspect_connection(connection)
        opened.documents.validate_restart()
        return OpenedCipherProductRuntime(
            runtime=opened,
            first_run=first_run,
            installation_id=installation_id,
            database_context_id=loaded.database_context_id,
            dmk_key_id=loaded.dmk_key_id,
            dmk_generation=loaded.dmk_generation,
            dmk_fingerprint_sha256=loaded.dmk_fingerprint_sha256,
            database_key_id=loaded.database_key_id,
            database_key_generation=loaded.database_key_generation,
            database_key_fingerprint_sha256=(
                loaded.database_key_fingerprint_sha256
            ),
        )


def open_cipher_product_runtime(**kwargs) -> OpenedCipherProductRuntime:
    """Public Qt-free composition used by normal product startup and tests."""
    return CipherProductRuntimeCoordinator(**kwargs).open()


def _classify_product_state(
    paths: CipherProductPaths,
    *,
    final_paths: FinalV3SQLCipherRuntimePaths,
    document_paths: FinalV3DocumentRuntimePaths,
    first_run_allowed: bool,
) -> bool:
    _reject_legacy_plaintext(paths)
    for directory_name in _LEGACY_RESTORE_DIRECTORIES:
        if _path_exists_or_symlink(Path(paths.root) / directory_name):
            raise CipherProductRuntimeError(
                "cipher_product_legacy_restore_state_not_supported",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            )
    main_exists = _regular_file_exists(final_paths.database)
    companion_exists = _regular_file_exists(document_paths.database)
    if main_exists:
        _reject_plaintext_header(final_paths.database)
    if companion_exists:
        _reject_plaintext_header(document_paths.database)
    artifacts = (
        _regular_file_exists(final_paths.key_runtime.keyset_metadata),
        _regular_file_exists(final_paths.key_runtime.envelope_registry),
        main_exists,
        companion_exists,
        _directory_exists(document_paths.container_root),
    )
    if not any(artifacts):
        if not first_run_allowed:
            raise CipherProductRuntimeError(
                "cipher_product_first_run_not_authorized",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            )
        return True
    if not all(artifacts):
        raise CipherProductRuntimeError(
            "cipher_product_runtime_partial",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )
    return False


def _reject_legacy_plaintext(paths: CipherProductPaths) -> None:
    legacy_database = Path(paths.database)
    if _path_exists_or_symlink(legacy_database):
        if not _regular_file_exists(legacy_database):
            raise CipherProductRuntimeError(
                "legacy_product_database_path_unsafe",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            )
        try:
            with legacy_database.open("rb") as stream:
                header = stream.read(len(_SQLITE_HEADER))
        except OSError:
            raise CipherProductRuntimeError(
                "legacy_product_database_unreadable",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            ) from None
        code = (
            "plaintext_product_database_not_supported"
            if header == _SQLITE_HEADER
            else "legacy_product_database_not_supported"
        )
        raise CipherProductRuntimeError(
            code,
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )
    if _path_exists_or_symlink(Path(paths.documents)):
        raise CipherProductRuntimeError(
            "plaintext_product_documents_not_supported",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )


def _verify_exact_sqlcipher_runtime(provider: SQLCipherConnectionProvider) -> None:
    if (
        provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
        or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION
    ):
        raise CipherProductRuntimeError(
            "sqlcipher_417_provider_configuration_invalid",
            operation=CipherProductRuntimeOperation.VERIFY_ENGINE,
        )
    with tempfile.TemporaryDirectory(prefix="jkm-cipher-product-probe-") as root:
        probe_path = Path(root) / "probe.sqlcipher"
        key = bytearray(secrets.token_bytes(32))
        try:
            with closing(
                provider.connect(probe_path, create=True, key_material=key)
            ) as connection:
                cipher_version = str(
                    connection.execute("PRAGMA cipher_version").fetchone()[0]
                )
                cipher_provider = str(
                    connection.execute("PRAGMA cipher_provider").fetchone()[0]
                ).lower()
                provider_version_row = connection.execute(
                    "PRAGMA cipher_provider_version"
                ).fetchone()
                sqlite_version = str(
                    connection.execute("SELECT sqlite_version()").fetchone()[0]
                )
                cipher_status = str(
                    connection.execute("PRAGMA cipher_status").fetchone()[0]
                )
        finally:
            for index in range(len(key)):
                key[index] = 0
    if (
        cipher_version != SQLCIPHER_4_17_ENGINE_VERSION
        or cipher_provider != "commoncrypto"
        or provider_version_row is None
        or not str(provider_version_row[0])
        or sqlite_version != SQLCIPHER_4_17_SQLITE_VERSION
        or cipher_status != "1"
    ):
        raise CipherProductRuntimeError(
            "sqlcipher_417_runtime_incompatible",
            operation=CipherProductRuntimeOperation.VERIFY_ENGINE,
        )


def _initialize_first_run_school_year(
    runtime: OpenedFinalV3DocumentRuntime,
    clock: Any,
) -> None:
    created_at = _format_utc(clock.utc_now())
    with closing(runtime.final_v3.database.connect()) as connection:
        counts = tuple(
            int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "school_years",
                "students",
                "groups",
                "courses",
                "student_school_year_assignments",
                "observations",
            )
        )
        if any(counts):
            raise CipherProductRuntimeError(
                "cipher_product_first_run_not_empty",
                operation=CipherProductRuntimeOperation.INITIALIZE_SCHOOL_YEAR,
            )
        with connection:
            connection.execute(
                """
                INSERT INTO school_years (
                    school_year_id, label, start_date, end_date,
                    status, created_at, closed_at
                ) VALUES (?, ?, ?, ?, 'current', ?, NULL)
                """,
                (
                    PILOT_FIRST_RUN_SCHOOL_YEAR_ID,
                    PILOT_FIRST_RUN_SCHOOL_YEAR_LABEL,
                    PILOT_FIRST_RUN_SCHOOL_YEAR_START.isoformat(),
                    PILOT_FIRST_RUN_SCHOOL_YEAR_END.isoformat(),
                    created_at,
                ),
            )
    _require_completed_fachlicher_first_run(runtime)


def _require_completed_fachlicher_first_run(
    runtime: OpenedFinalV3DocumentRuntime,
) -> None:
    with closing(runtime.final_v3.database.connect()) as connection:
        rows = connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years ORDER BY start_date, school_year_id
            """
        ).fetchall()
    pilot_rows = [
        tuple(row)
        for row in rows
        if row[0] == PILOT_FIRST_RUN_SCHOOL_YEAR_ID
    ]
    expected_pilot_prefix = (
        PILOT_FIRST_RUN_SCHOOL_YEAR_ID,
        PILOT_FIRST_RUN_SCHOOL_YEAR_LABEL,
        PILOT_FIRST_RUN_SCHOOL_YEAR_START.isoformat(),
        PILOT_FIRST_RUN_SCHOOL_YEAR_END.isoformat(),
    )
    current_count = sum(1 for row in rows if row[4] == "current")
    if (
        len(pilot_rows) != 1
        or pilot_rows[0][:4] != expected_pilot_prefix
        or pilot_rows[0][4] not in {"current", "closed"}
        or current_count != 1
    ):
        raise CipherProductRuntimeError(
            "cipher_product_fachlicher_first_run_incomplete",
            operation=CipherProductRuntimeOperation.VERIFY_RUNTIME,
        )


def _require_product_root(path: Path) -> Path:
    try:
        status = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        raise CipherProductRuntimeError(
            "cipher_product_root_invalid",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        ) from None
    if (
        not path.is_absolute()
        or resolved != path
        or stat.S_ISLNK(status.st_mode)
        or not stat.S_ISDIR(status.st_mode)
        or (hasattr(os, "getuid") and status.st_uid != os.getuid())
    ):
        raise CipherProductRuntimeError(
            "cipher_product_root_invalid",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )
    return resolved


def _require_private_directory_if_present(path: Path) -> None:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        raise CipherProductRuntimeError(
            "cipher_product_runtime_directory_unsafe",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        ) from None
    if (
        stat.S_ISLNK(status.st_mode)
        or not stat.S_ISDIR(status.st_mode)
        or stat.S_IMODE(status.st_mode) & 0o077
        or (hasattr(os, "getuid") and status.st_uid != os.getuid())
        or path.resolve(strict=True) != path
    ):
        raise CipherProductRuntimeError(
            "cipher_product_runtime_directory_unsafe",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )


def _regular_file_exists(path: Path) -> bool:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        raise CipherProductRuntimeError(
            "cipher_product_artifact_unreadable",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        ) from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise CipherProductRuntimeError(
            "cipher_product_artifact_unsafe",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )
    return True


def _directory_exists(path: Path) -> bool:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        raise CipherProductRuntimeError(
            "cipher_product_artifact_unreadable",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        ) from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        raise CipherProductRuntimeError(
            "cipher_product_artifact_unsafe",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )
    return True


def _reject_plaintext_header(path: Path) -> None:
    try:
        with path.open("rb") as stream:
            header = stream.read(len(_SQLITE_HEADER))
    except OSError:
        raise CipherProductRuntimeError(
            "cipher_product_database_unreadable",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        ) from None
    if header == _SQLITE_HEADER:
        raise CipherProductRuntimeError(
            "plaintext_product_database_not_supported",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )


def _path_exists_or_symlink(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CipherProductRuntimeError(
            "cipher_product_clock_invalid",
            operation=CipherProductRuntimeOperation.INITIALIZE_SCHOOL_YEAR,
        )
    return value.astimezone(UTC).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
