"""Gated, Qt-free DMK and Database-Key runtime composition.

This module is intentionally not imported by product startup.  It composes
the existing DMK/keyset and Database-Key envelope foundations only for an
explicit, marker-bound internal test root.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import os
from pathlib import Path
import stat
import tempfile
from typing import Mapping

from .data_keys import (
    DataKeyset,
    DataKeysetRuntimePhase,
    DataMasterKeyLifecycleError,
    DataMasterKeyService,
    LoadedDataMasterKey,
    data_master_key_fingerprint,
)
from .database_keys import (
    DatabaseKey,
    DatabaseKeyEnvelopeError,
    DatabaseKeyEnvelopeService,
)
from .domain import SecurityStoreError, validate_uuid4
from .infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
from .infrastructure.data_master_key_store import (
    build_platform_data_master_key_store,
)
from .infrastructure.database_key_envelope_repository import (
    DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
    FileDatabaseKeyEnvelopeRepository,
)
from .infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)


DMK_DATABASE_KEY_RUNTIME_GATE_ENV = "JKM_DMK_DATABASE_KEY_RUNTIME_TEST"
DMK_DATABASE_KEY_RUNTIME_ROOT_ENV = "JKM_DMK_DATABASE_KEY_RUNTIME_ROOT"
DMK_DATABASE_KEY_RUNTIME_GATE_VALUE = "1"
DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX = "jkm-dmk-database-key-runtime-"
DMK_DATABASE_KEY_RUNTIME_MARKER = ".jkm-dmk-database-key-runtime-test-root"
DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES = (
    b"jenaplan-dmk-database-key-runtime-test-root-v1\n"
)
DMK_DATABASE_KEY_RUNTIME_METADATA_DIRECTORY = "security-key-runtime-v1"
DMK_DATABASE_KEY_RUNTIME_KEYSET_FILENAME = "data-keysets.sqlite"
DATABASE_KEY_RUNTIME_GENERATION = 1


class DatabaseKeyRuntimeDecisionState(StrEnum):
    DISABLED = "DISABLED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class DatabaseKeyRuntimeOperation(StrEnum):
    CLASSIFY = "classify"
    PREPARE_DMK = "prepare_dmk"
    LOAD_DMK = "load_dmk"
    PREPARE_DATABASE_KEY = "prepare_database_key"
    VERIFY_ENVELOPE = "verify_envelope"
    ACTIVATE_KEYSET = "activate_keyset"


class DatabaseKeyRuntimeError(RuntimeError):
    """Structured, sanitized failure without paths or key material."""

    def __init__(
        self,
        code: str,
        *,
        operation: DatabaseKeyRuntimeOperation,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.operation = operation
        self.retryable = retryable
        super().__init__(code)


@dataclass(frozen=True)
class DatabaseKeyRuntimePaths:
    root: Path
    metadata_root: Path
    keyset_metadata: Path
    envelope_registry: Path

    @classmethod
    def for_root(cls, root: Path) -> "DatabaseKeyRuntimePaths":
        base = Path(root)
        metadata = base / DMK_DATABASE_KEY_RUNTIME_METADATA_DIRECTORY
        return cls(
            root=base,
            metadata_root=metadata,
            keyset_metadata=metadata / DMK_DATABASE_KEY_RUNTIME_KEYSET_FILENAME,
            envelope_registry=metadata / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
        )


@dataclass(frozen=True)
class LoadedDatabaseKeyRuntime:
    database_context_id: str
    dmk_key_id: str
    dmk_generation: int
    dmk_fingerprint_sha256: str
    database_key_id: str
    database_key_generation: int
    database_key_fingerprint_sha256: str
    first_run: bool
    dmk: LoadedDataMasterKey = field(repr=False)
    database_key: DatabaseKey = field(repr=False)


@dataclass(frozen=True)
class DatabaseKeyRuntimeDecision:
    state: DatabaseKeyRuntimeDecisionState
    loaded: LoadedDatabaseKeyRuntime | None = field(default=None, repr=False)
    error_code: str | None = None
    error_operation: DatabaseKeyRuntimeOperation | None = None
    retryable: bool = False


class DatabaseKeyRuntimeGate:
    """Read-only resolver for the disabled-by-default internal test gate."""

    def resolve(
        self, environ: Mapping[str, str] | None = None
    ) -> DatabaseKeyRuntimeDecision:
        environment = os.environ if environ is None else environ
        raw_gate = environment.get(DMK_DATABASE_KEY_RUNTIME_GATE_ENV, "")
        if raw_gate == "":
            return DatabaseKeyRuntimeDecision(
                DatabaseKeyRuntimeDecisionState.DISABLED
            )
        if raw_gate != DMK_DATABASE_KEY_RUNTIME_GATE_VALUE:
            return DatabaseKeyRuntimeDecision(
                DatabaseKeyRuntimeDecisionState.BLOCKED,
                error_code="database_key_runtime_gate_value_invalid",
                error_operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        raw_root = environment.get(DMK_DATABASE_KEY_RUNTIME_ROOT_ENV, "")
        try:
            self.require_paths(raw_root)
        except DatabaseKeyRuntimeError as error:
            return DatabaseKeyRuntimeDecision(
                DatabaseKeyRuntimeDecisionState.BLOCKED,
                error_code=error.code,
                error_operation=error.operation,
                retryable=error.retryable,
            )
        return DatabaseKeyRuntimeDecision(DatabaseKeyRuntimeDecisionState.ACTIVE)

    @staticmethod
    def require_paths(raw_root: str) -> DatabaseKeyRuntimePaths:
        if not isinstance(raw_root, str) or not raw_root:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_root_missing",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        root = Path(raw_root)
        if not root.is_absolute() or root.name == "":
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_root_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        try:
            status = os.lstat(root)
            resolved = root.resolve(strict=True)
            temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
            relative = resolved.relative_to(temporary_root)
        except (OSError, RuntimeError, ValueError):
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_root_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            ) from None
        if (
            stat.S_ISLNK(status.st_mode)
            or not stat.S_ISDIR(status.st_mode)
            or resolved != root
            or not relative.parts
            or not root.name.startswith(DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX)
        ):
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_root_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_root_not_private",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        if hasattr(os, "getuid") and status.st_uid != os.getuid():
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_root_owner_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        _require_marker(root / DMK_DATABASE_KEY_RUNTIME_MARKER)
        return DatabaseKeyRuntimePaths.for_root(root)


class DatabaseKeyRuntime:
    """Restart-aware composition without database, UI, or product activation."""

    def __init__(
        self,
        *,
        paths: DatabaseKeyRuntimePaths,
        key_repository: SQLiteDataKeysetRepository,
        key_store,
        dmk_service: DataMasterKeyService,
        envelope_repository: FileDatabaseKeyEnvelopeRepository,
        envelope_service: DatabaseKeyEnvelopeService,
        random_source,
        fault_hook=None,
    ) -> None:
        self.paths = paths
        self._key_repository = key_repository
        self._key_store = key_store
        self._dmk_service = dmk_service
        self._envelope_repository = envelope_repository
        self._envelope_service = envelope_service
        self._random = random_source
        self._fault_hook = fault_hook
        self._operation = DatabaseKeyRuntimeOperation.CLASSIFY

    def open_or_create(self) -> LoadedDatabaseKeyRuntime:
        try:
            return self._open_or_create()
        except DatabaseKeyRuntimeError:
            raise
        except (
            DataMasterKeyLifecycleError,
            DatabaseKeyEnvelopeError,
            SecurityStoreError,
        ) as error:
            code = getattr(error, "code", str(error))
            raise DatabaseKeyRuntimeError(
                code,
                operation=self._operation,
                retryable=(
                    code
                    in {
                        "data_master_key_access_denied",
                        "data_master_key_store_read_failed",
                        "data_master_key_store_unsupported",
                    }
                    and not (
                        code == "data_master_key_access_denied"
                        and self._operation
                        is DatabaseKeyRuntimeOperation.PREPARE_DMK
                    )
                ),
            ) from None
        except OSError:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_storage_unavailable",
                operation=self._operation,
                retryable=True,
            ) from None

    def _open_or_create(self) -> LoadedDatabaseKeyRuntime:
        self._operation = DatabaseKeyRuntimeOperation.CLASSIFY
        keyset_exists = (
            self.paths.keyset_metadata.exists()
            or self.paths.keyset_metadata.is_symlink()
        )
        registry_exists = self._envelope_repository.exists()
        if not keyset_exists and not registry_exists:
            if not self._key_store.supported:
                raise DatabaseKeyRuntimeError(
                    "data_master_key_store_unsupported",
                    operation=DatabaseKeyRuntimeOperation.PREPARE_DMK,
                    retryable=True,
                )
            self._key_repository.initialize()
            return self._first_run()
        if keyset_exists != registry_exists:
            if keyset_exists:
                self._key_repository.initialize()
                pending = self._key_repository.pending_data_keysets()
                if len(pending) == 1:
                    return self._resume_pending(pending[0], registry_exists=False)
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_partial_store",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )

        self._key_repository.initialize()
        active = self._key_repository.active_data_keyset()
        pending = self._key_repository.pending_data_keysets()
        terminal = self._key_repository.data_keysets_for_cleanup()
        if terminal or (active is not None and pending) or len(pending) > 1:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_keyset_cardinality_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        if active is not None:
            return self._load_active(active)
        if len(pending) == 1:
            return self._resume_pending(pending[0], registry_exists=True)
        raise DatabaseKeyRuntimeError(
            "database_key_runtime_keyset_missing",
            operation=DatabaseKeyRuntimeOperation.CLASSIFY,
        )

    def _first_run(self) -> LoadedDatabaseKeyRuntime:
        self._operation = DatabaseKeyRuntimeOperation.PREPARE_DMK
        dmk = self._dmk_service.create_pending(fault_hook=self._fault_hook)
        self._emit("after_keyset_pending")
        context_id = self._random.uuid4()
        validate_uuid4(context_id)
        pending = self._only_pending()
        pending = self._key_repository.advance_pending_data_keyset(
            key_id=pending.key_id,
            expected_phase=DataKeysetRuntimePhase.DMK_PUBLISHED,
            replacement_phase=DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED,
            database_context_id=context_id,
        )
        return self._publish_and_activate(dmk, pending, first_run=True)

    def _resume_pending(
        self, pending: DataKeyset, *, registry_exists: bool
    ) -> LoadedDatabaseKeyRuntime:
        self._operation = DatabaseKeyRuntimeOperation.LOAD_DMK
        dmk = self._dmk_service.load_pending()
        pending = self._only_pending()
        self._verify_dmk_binding(dmk, pending)
        if pending.runtime_phase is DataKeysetRuntimePhase.DMK_PUBLISHED:
            if registry_exists:
                raise DatabaseKeyRuntimeError(
                    "database_key_runtime_context_missing",
                    operation=DatabaseKeyRuntimeOperation.CLASSIFY,
                )
            context_id = self._random.uuid4()
            validate_uuid4(context_id)
            pending = self._key_repository.advance_pending_data_keyset(
                key_id=pending.key_id,
                expected_phase=DataKeysetRuntimePhase.DMK_PUBLISHED,
                replacement_phase=(
                    DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED
                ),
                database_context_id=context_id,
            )
            return self._publish_and_activate(dmk, pending, first_run=False)
        if pending.runtime_phase is DataKeysetRuntimePhase.PREPARED:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_dmk_publish_unconfirmed",
                operation=DatabaseKeyRuntimeOperation.LOAD_DMK,
            )
        if pending.database_context_id is None:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_context_missing",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        if not registry_exists:
            raise DatabaseKeyRuntimeError(
                "database_key_envelope_missing_after_generation",
                operation=DatabaseKeyRuntimeOperation.VERIFY_ENVELOPE,
            )
        return self._finish_published(dmk, pending, first_run=False)

    def _publish_and_activate(
        self,
        dmk: LoadedDataMasterKey,
        pending: DataKeyset,
        *,
        first_run: bool,
    ) -> LoadedDatabaseKeyRuntime:
        assert pending.database_context_id is not None
        self._operation = DatabaseKeyRuntimeOperation.PREPARE_DATABASE_KEY
        created = self._envelope_service.create_pending(
            dmk,
            database_context_id=pending.database_context_id,
            generation=DATABASE_KEY_RUNTIME_GENERATION,
            fault_hook=self._fault_hook,
        )
        self._emit("after_envelope_publish")
        pending = self._key_repository.advance_pending_data_keyset(
            key_id=pending.key_id,
            expected_phase=DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED,
            replacement_phase=DataKeysetRuntimePhase.ENVELOPE_PUBLISHED,
        )
        loaded = self._finish_published(dmk, pending, first_run=first_run)
        if loaded.database_key != created:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_created_key_mismatch",
                operation=DatabaseKeyRuntimeOperation.VERIFY_ENVELOPE,
            )
        return loaded

    def _finish_published(
        self,
        dmk: LoadedDataMasterKey,
        pending: DataKeyset,
        *,
        first_run: bool,
    ) -> LoadedDatabaseKeyRuntime:
        assert pending.database_context_id is not None
        self._operation = DatabaseKeyRuntimeOperation.VERIFY_ENVELOPE
        if (
            self._envelope_repository.peek_context()
            != pending.database_context_id
        ):
            raise DatabaseKeyRuntimeError(
                "database_key_context_mismatch",
                operation=DatabaseKeyRuntimeOperation.VERIFY_ENVELOPE,
            )
        database_key = self._envelope_service.activate(
            dmk, generation=DATABASE_KEY_RUNTIME_GENERATION
        )
        if pending.runtime_phase is DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED:
            pending = self._key_repository.advance_pending_data_keyset(
                key_id=pending.key_id,
                expected_phase=(
                    DataKeysetRuntimePhase.DATABASE_KEY_GENERATION_STARTED
                ),
                replacement_phase=DataKeysetRuntimePhase.ENVELOPE_PUBLISHED,
            )
        if pending.runtime_phase is DataKeysetRuntimePhase.ENVELOPE_PUBLISHED:
            pending = self._key_repository.advance_pending_data_keyset(
                key_id=pending.key_id,
                expected_phase=DataKeysetRuntimePhase.ENVELOPE_PUBLISHED,
                replacement_phase=DataKeysetRuntimePhase.DATABASE_KEY_ACTIVE,
            )
        if pending.runtime_phase is not DataKeysetRuntimePhase.DATABASE_KEY_ACTIVE:
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_phase_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        self._emit("before_keyset_activation")
        self._operation = DatabaseKeyRuntimeOperation.ACTIVATE_KEYSET
        active_dmk = self._dmk_service.activate_pending(key_id=pending.key_id)
        self._emit("after_keyset_activation")
        active = self._key_repository.active_data_keyset()
        if active is None:
            raise DatabaseKeyRuntimeError(
                "active_data_master_key_missing",
                operation=DatabaseKeyRuntimeOperation.ACTIVATE_KEYSET,
            )
        self._verify_dmk_binding(active_dmk, active)
        return self._result(
            active_dmk,
            database_key,
            active,
            first_run=first_run,
        )

    def _load_active(self, active: DataKeyset) -> LoadedDatabaseKeyRuntime:
        if (
            active.runtime_phase is not DataKeysetRuntimePhase.ACTIVE
            or active.database_context_id is None
        ):
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_active_keyset_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        self._operation = DatabaseKeyRuntimeOperation.LOAD_DMK
        dmk = self._dmk_service.load()
        self._verify_dmk_binding(dmk, active)
        self._operation = DatabaseKeyRuntimeOperation.VERIFY_ENVELOPE
        if self._envelope_repository.peek_context() != active.database_context_id:
            raise DatabaseKeyRuntimeError(
                "database_key_context_mismatch",
                operation=DatabaseKeyRuntimeOperation.VERIFY_ENVELOPE,
            )
        database_key = self._envelope_service.load_active(
            dmk, expected_generation=DATABASE_KEY_RUNTIME_GENERATION
        )
        return self._result(dmk, database_key, active, first_run=False)

    def _result(
        self,
        dmk: LoadedDataMasterKey,
        database_key: DatabaseKey,
        keyset: DataKeyset,
        *,
        first_run: bool,
    ) -> LoadedDatabaseKeyRuntime:
        assert keyset.database_context_id is not None
        return LoadedDatabaseKeyRuntime(
            database_context_id=keyset.database_context_id,
            dmk_key_id=dmk.key_id,
            dmk_generation=dmk.generation,
            dmk_fingerprint_sha256=data_master_key_fingerprint(dmk.key_material),
            database_key_id=database_key.key_id,
            database_key_generation=database_key.generation,
            database_key_fingerprint_sha256=hashlib.sha256(
                database_key.key_material
            ).hexdigest(),
            first_run=first_run,
            dmk=dmk,
            database_key=database_key,
        )

    def _only_pending(self) -> DataKeyset:
        pending = self._key_repository.pending_data_keysets()
        if len(pending) != 1:
            raise DatabaseKeyRuntimeError(
                "pending_data_master_key_cardinality_invalid",
                operation=DatabaseKeyRuntimeOperation.CLASSIFY,
            )
        return pending[0]

    @staticmethod
    def _verify_dmk_binding(dmk: LoadedDataMasterKey, keyset: DataKeyset) -> None:
        if (
            dmk.key_id != keyset.key_id
            or dmk.generation != keyset.generation
            or data_master_key_fingerprint(dmk.key_material)
            != keyset.fingerprint_sha256
        ):
            raise DatabaseKeyRuntimeError(
                "database_key_runtime_dmk_binding_mismatch",
                operation=DatabaseKeyRuntimeOperation.LOAD_DMK,
            )

    def _emit(self, boundary: str) -> None:
        if self._fault_hook is not None:
            self._fault_hook(boundary)


def build_database_key_runtime(
    paths: DatabaseKeyRuntimePaths,
    *,
    account_loader,
    key_store=None,
    random_source=None,
    clock=None,
    fault_hook=None,
) -> DatabaseKeyRuntime:
    """Compose only existing repositories/services for the gated test root."""

    permissions = PlatformFilePermissionManager()
    random = random_source or SystemRandomSource()
    store = key_store or build_platform_data_master_key_store()
    key_repository = SQLiteDataKeysetRepository(
        paths.keyset_metadata, permissions
    )
    envelope_repository = FileDatabaseKeyEnvelopeRepository(
        paths.envelope_registry, permissions
    )
    return DatabaseKeyRuntime(
        paths=paths,
        key_repository=key_repository,
        key_store=store,
        dmk_service=DataMasterKeyService(
            repository=key_repository,
            key_store=store,
            random_source=random,
            account_loader=account_loader,
        ),
        envelope_repository=envelope_repository,
        envelope_service=DatabaseKeyEnvelopeService(
            repository=envelope_repository,
            random_source=random,
            clock=clock or SystemClock(),
        ),
        random_source=random,
        fault_hook=fault_hook,
    )


def run_gated_database_key_runtime(
    *,
    account_loader,
    environ: Mapping[str, str] | None = None,
    key_store=None,
    random_source=None,
    clock=None,
    fault_hook=None,
) -> DatabaseKeyRuntimeDecision:
    """Return DISABLED without resolving paths or constructing runtime stores."""

    environment = os.environ if environ is None else environ
    gate = DatabaseKeyRuntimeGate()
    decision = gate.resolve(environment)
    if decision.state is not DatabaseKeyRuntimeDecisionState.ACTIVE:
        return decision
    try:
        paths = gate.require_paths(
            environment.get(DMK_DATABASE_KEY_RUNTIME_ROOT_ENV, "")
        )
        loaded = build_database_key_runtime(
            paths,
            account_loader=account_loader,
            key_store=key_store,
            random_source=random_source,
            clock=clock,
            fault_hook=fault_hook,
        ).open_or_create()
        return DatabaseKeyRuntimeDecision(
            DatabaseKeyRuntimeDecisionState.ACTIVE,
            loaded=loaded,
        )
    except DatabaseKeyRuntimeError as error:
        return DatabaseKeyRuntimeDecision(
            DatabaseKeyRuntimeDecisionState.BLOCKED,
            error_code=error.code,
            error_operation=error.operation,
            retryable=error.retryable,
        )


def _require_marker(path: Path) -> None:
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
            or opened.st_size != len(DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES)
            or os.read(
                descriptor, len(DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES) + 1
            )
            != DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES
        ):
            raise OSError
    except OSError:
        raise DatabaseKeyRuntimeError(
            "database_key_runtime_marker_invalid",
            operation=DatabaseKeyRuntimeOperation.CLASSIFY,
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
