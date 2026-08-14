"""Existing-only Final-V4 verification and safety backup for support reset."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from pathlib import Path
import os
import stat

from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCipherConnectionProvider,
)
from src.core.runtime_root_protection import require_product_runtime_root

from .cipher_product_runtime import (
    CipherProductPaths,
    CipherProductRuntimeScope,
    _require_completed_fachlicher_first_run,
    _verify_exact_sqlcipher_runtime,
)
from .data_keys import (
    DATA_MASTER_KEY_BYTES,
    DataKeysetRuntimePhase,
    DataKeysetStatus,
    DataMasterKeyStoreStatus,
    LoadedDataMasterKey,
    data_master_key_fingerprint,
)
from .database_key_runtime import (
    DATABASE_KEY_RUNTIME_GENERATION,
    LoadedDatabaseKeyRuntime,
)
from .database_keys import DatabaseKeyEnvelopeService
from .domain import (
    AccountStatus,
    FinalV4PreAuthRecoveryValidationError,
    SecurityBackupProof,
)
from .final_v3_document_runtime import (
    FinalV3DocumentRuntimeCoordinator,
    FinalV3DocumentRuntimePaths,
)
from .final_v4_backup_runtime import (
    FinalV4EncryptedBackupService,
    FinalV4EncryptedSafetyBackup,
    build_final_v4_encrypted_backup_service,
)
from .final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimeCoordinator
from .infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
from .infrastructure.data_master_key_store import build_platform_data_master_key_store
from .infrastructure.database_key_envelope_repository import (
    FileDatabaseKeyEnvelopeRepository,
)
from .infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)


class FinalV4SupportResetBackupError(RuntimeError):
    """The mandatory encrypted backup could not be published and verified."""


@dataclass(frozen=True)
class FinalV4PreAuthRecoveryFactory:
    """Create the token-gated verifier without touching product data."""

    paths: CipherProductPaths
    account_loader: object
    security_store_validator: object
    key_store: object | None = None
    random_source: object | None = None
    clock: object | None = None
    sqlcipher_provider: SQLCipherConnectionProvider | None = None

    def create(self) -> "FinalV4PreAuthRecoveryVerifier":
        return FinalV4PreAuthRecoveryVerifier(
            paths=self.paths,
            account_loader=self.account_loader,
            security_store_validator=self.security_store_validator,
            key_store=self.key_store,
            random_source=self.random_source,
            clock=self.clock,
            sqlcipher_provider=self.sqlcipher_provider,
        )


class FinalV4PreAuthRecoveryVerifier:
    """Validate one existing Final-V4 identity and create its verified backup."""

    def __init__(
        self,
        *,
        paths: CipherProductPaths,
        account_loader,
        security_store_validator,
        key_store=None,
        random_source=None,
        clock=None,
        sqlcipher_provider: SQLCipherConnectionProvider | None = None,
    ) -> None:
        self._paths = paths
        self._account_loader = account_loader
        self._validate_security_store = security_store_validator
        self._key_store = key_store
        self._random = random_source or SystemRandomSource()
        self._clock = clock or SystemClock()
        self._provider = sqlcipher_provider or SQLCipherConnectionProvider(
            expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        )

    def create_and_verify(self) -> SecurityBackupProof:
        try:
            opened, loaded = self._open_existing_read_only()
            service = build_final_v4_encrypted_backup_service(
                opened_runtime=opened,
                account_loader=self._account_loader,
                environ={},
                key_store=self._key_store,
                random_source=self._random,
                clock=self._clock,
                sqlcipher_provider=self._provider,
                product_paths=self._paths,
                loaded_keys=loaded,
            )
            target = self._new_target()
        except FinalV4PreAuthRecoveryValidationError:
            raise
        except Exception as error:
            raise FinalV4PreAuthRecoveryValidationError(
                "final_v4_pre_auth_validation_failed"
            ) from error
        try:
            result = service.create(target)
        except Exception:
            raise FinalV4SupportResetBackupError(
                "final_v4_support_reset_backup_failed"
            ) from None
        return SecurityBackupProof(str(result.path), result.container_sha256)

    def finish(self, *, reset_committed: bool) -> None:
        """Pre-auth has no retained in-process writer lease to release."""

        del reset_committed

    def _open_existing_read_only(self):
        self._validate_security_store()
        root = Path(self._paths.root)
        require_product_runtime_root(root, first_run=False)
        scope = CipherProductRuntimeScope(self._paths)
        final_paths = scope.require_paths()
        document_paths = FinalV3DocumentRuntimePaths.for_final_v4(final_paths)
        account = self._account_loader()
        if account.status is not AccountStatus.ACTIVE:
            raise FinalV4PreAuthRecoveryValidationError(
                "final_v4_pre_auth_account_not_active"
            )
        stable_account_loader = lambda: account
        _verify_exact_sqlcipher_runtime(self._provider)
        loaded = _load_existing_support_recovery_keys(
            final_paths.key_runtime,
            account=account,
            key_store=self._key_store,
            random_source=self._random,
            clock=self._clock,
        )
        if any(
            (root / name).exists() or (root / name).is_symlink()
            for name in ("restore-handoffs", "restore-transactions")
        ):
            from .final_v4_live_restore import (
                validate_terminal_final_v4_restore_evidence,
            )

            validate_terminal_final_v4_restore_evidence(
                root,
                loaded_keys=loaded,
                installation_id=account.installation_id,
            )
        final_v4 = FinalV4SQLCipherRuntimeCoordinator(
            paths=final_paths,
            account_loader=stable_account_loader,
            authentication_confirmed=False,
            technical_first_run_confirmed=False,
            key_store=self._key_store,
            random_source=self._random,
            clock=self._clock,
            sqlcipher_provider=self._provider,
            environ={},
            scope=scope,
            loaded_keys=loaded,
        ).open_existing_for_support_recovery()
        opened = FinalV3DocumentRuntimeCoordinator(
            final_v4=final_v4,
            paths=document_paths,
            loaded_keys=loaded,
            installation_id=account.installation_id,
            document_database_create_allowed=False,
            provider=self._provider,
            scope=scope,
            environ={},
            source_root=None,
            random_source=self._random,
            clock=self._clock,
        ).open()
        _require_completed_fachlicher_first_run(opened)
        opened.documents.validate_restart()
        return opened, loaded

    def _new_target(self) -> Path:
        backup_root = Path(self._paths.backups)
        try:
            metadata = backup_root.lstat()
        except OSError:
            raise FinalV4PreAuthRecoveryValidationError(
                "final_v4_support_backup_root_missing"
            ) from None
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise FinalV4PreAuthRecoveryValidationError(
                "final_v4_support_backup_root_invalid"
            )
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise FinalV4PreAuthRecoveryValidationError(
                "final_v4_support_backup_root_owner_invalid"
            )
        now = self._clock.utc_now()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise FinalV4PreAuthRecoveryValidationError(
                "final_v4_support_backup_clock_invalid"
            )
        backup_id = self._random.uuid4()
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        return backup_root / f"support-reset-safety-{stamp}-{backup_id}.jkmebackup"


@dataclass(frozen=True)
class FinalV4SupportResetBackupFactory:
    """Bind an authenticated runtime's real maintenance gate to support reset."""

    service: FinalV4EncryptedBackupService
    backup_root: Path
    random_source: object = field(default_factory=SystemRandomSource)
    clock: object = field(default_factory=SystemClock)

    def create(self) -> "FinalV4SupportResetBackupPort":
        return FinalV4SupportResetBackupPort(
            service=self.service,
            backup_root=self.backup_root,
            random_source=self.random_source,
            clock=self.clock,
        )


class FinalV4SupportResetBackupPort:
    """Keep the authenticated runtime frozen through the Security commit."""

    def __init__(self, *, service, backup_root, random_source, clock) -> None:
        self._service = service
        self._backup_root = Path(backup_root)
        self._random = random_source
        self._clock = clock
        self._lease: FinalV4EncryptedSafetyBackup | None = None

    def create_and_verify(self) -> SecurityBackupProof:
        if self._lease is not None:
            raise FinalV4SupportResetBackupError("support_backup_already_created")
        now = self._clock.utc_now()
        target = self._backup_root / (
            f"support-reset-safety-{now.strftime('%Y%m%dT%H%M%SZ')}-"
            f"{self._random.uuid4()}.jkmebackup"
        )
        try:
            self._lease = self._service.create_safety_backup(target)
        except Exception:
            raise FinalV4SupportResetBackupError(
                "final_v4_support_reset_backup_failed"
            ) from None
        result = self._lease.result
        return SecurityBackupProof(str(result.path), result.container_sha256)

    def finish(self, *, reset_committed: bool) -> None:
        del reset_committed
        if self._lease is not None:
            self._lease.abort()
            self._lease = None


def _load_existing_support_recovery_keys(
    paths,
    *,
    account,
    key_store,
    random_source,
    clock,
) -> LoadedDatabaseKeyRuntime:
    """Read one active key identity without lifecycle recovery or mutation."""

    permissions = PlatformFilePermissionManager()
    repository = SQLiteDataKeysetRepository(paths.keyset_metadata, permissions)
    active = repository.active_data_keyset()
    if (
        active is None
        or active.status is not DataKeysetStatus.ACTIVE
        or active.runtime_phase is not DataKeysetRuntimePhase.ACTIVE
        or active.database_context_id is None
        or repository.pending_data_keysets()
        or repository.data_keysets_for_cleanup()
    ):
        raise FinalV4PreAuthRecoveryValidationError(
            "final_v4_support_keyset_not_active"
        )
    store = key_store or build_platform_data_master_key_store()
    try:
        observed = store.read(
            installation_id=account.installation_id,
            key_id=active.key_id,
        )
    except Exception:
        raise FinalV4PreAuthRecoveryValidationError(
            "final_v4_support_dmk_unavailable"
        ) from None
    if (
        observed.status is not DataMasterKeyStoreStatus.SUCCESS
        or not isinstance(observed.key_material, bytes)
        or len(observed.key_material) != DATA_MASTER_KEY_BYTES
        or data_master_key_fingerprint(observed.key_material)
        != active.fingerprint_sha256
    ):
        raise FinalV4PreAuthRecoveryValidationError(
            "final_v4_support_dmk_unavailable"
        )
    dmk = LoadedDataMasterKey(
        key_id=active.key_id,
        generation=active.generation,
        key_material=observed.key_material,
    )
    envelope_repository = FileDatabaseKeyEnvelopeRepository(
        paths.envelope_registry,
        permissions,
    )
    if (
        not envelope_repository.exists()
        or envelope_repository.peek_context() != active.database_context_id
    ):
        raise FinalV4PreAuthRecoveryValidationError(
            "final_v4_support_envelope_unavailable"
        )
    database_key = DatabaseKeyEnvelopeService(
        repository=envelope_repository,
        random_source=random_source,
        clock=clock,
    ).load_active(
        dmk,
        expected_generation=DATABASE_KEY_RUNTIME_GENERATION,
    )
    return LoadedDatabaseKeyRuntime(
        database_context_id=active.database_context_id,
        dmk_key_id=dmk.key_id,
        dmk_generation=dmk.generation,
        dmk_fingerprint_sha256=data_master_key_fingerprint(dmk.key_material),
        database_key_id=database_key.key_id,
        database_key_generation=database_key.generation,
        database_key_fingerprint_sha256=hashlib.sha256(
            database_key.key_material
        ).hexdigest(),
        first_run=False,
        dmk=dmk,
        database_key=database_key,
    )
