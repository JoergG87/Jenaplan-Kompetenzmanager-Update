"""Isolated existing-only key port; no product startup composition.

The caller supplies an independently authenticated active account. Neither the
root marker nor keyset/peek_context metadata authenticates that account. A1
does not implement early account authentication or grant runtime admission.
"""
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
from pathlib import Path
from typing import Protocol

from src.core.installation_inventory import InstallationInventoryStatus as InventoryStatus
from .data_keys import (
    DATA_MASTER_KEY_BYTES, DataKeysetRuntimePhase, DataMasterKeyStoreStatus,
    LoadedDataMasterKey, data_master_key_fingerprint,
)
from .database_key_runtime import (
    DATABASE_KEY_RUNTIME_GENERATION, DatabaseKeyRuntimePaths, LoadedDatabaseKeyRuntime,
)
from .database_keys import (
    DatabaseKeyEnvelopeService, DatabaseKeyEnvelopeError, DatabaseKeyEnvelopeStatus,
    derive_database_key_registry_auth_key,
)
from .domain import AccountStatus, SecurityStoreError, validate_uuid4
from .infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
from .infrastructure.data_master_key_store import build_platform_data_master_key_store
from .infrastructure.database_key_envelope_repository import FileDatabaseKeyEnvelopeRepository
from .infrastructure.installation_inventory import ReadOnlyInstallationInventory
from .infrastructure.system import PlatformFilePermissionManager, SystemClock, SystemRandomSource


class ExistingInstallationKeyStatus(StrEnum):
    VALID = "valid"
    KEY_MISSING = "key_missing"
    ACCESS_DENIED = "access_denied"
    CONTEXT_CONFLICT = "context_conflict"
    KEYCHAIN_UNAVAILABLE = "keychain_unavailable"
    INSTALLATION_UNKNOWN = "installation_unknown"


@dataclass(frozen=True)
class ExistingInstallationKeyResult:
    status: ExistingInstallationKeyStatus
    installation_id: str | None = None
    loaded: LoadedDatabaseKeyRuntime | None = field(default=None, repr=False)

    @property
    def normal_runtime_allowed(self) -> bool:
        return False

    @property
    def first_run_allowed(self) -> bool:
        return False

    @property
    def activation_allowed(self) -> bool:
        return False


class ExistingInstallationKeyPort(Protocol):
    def load_existing(self, root: Path, *, authenticated_account) -> ExistingInstallationKeyResult: ...


class ExistingInstallationKeys:
    """Reuse direct DMK read and authenticated envelope load, never lifecycle load.

Immutable metadata reads require absent WAL/SHM/journal; no checkpoint/repair.
No product main/companion DB is opened. Recheck under runtime lock in A2.
"""

    def __init__(self, *, key_store=None):
        self._key_store = key_store

    def load_existing(self, root: Path, *, authenticated_account) -> ExistingInstallationKeyResult:
        status = ExistingInstallationKeyStatus
        try:
            installation_id = validate_uuid4(authenticated_account.installation_id)
            if authenticated_account.status is not AccountStatus.ACTIVE:
                raise ValueError
        except (AttributeError, ValueError, SecurityStoreError):
            return ExistingInstallationKeyResult(status.INSTALLATION_UNKNOWN)
        inventory_port = ReadOnlyInstallationInventory()
        before = inventory_port.inspect(root)
        if before.status in {InventoryStatus.EMPTY, InventoryStatus.UNSAFE,
                             InventoryStatus.CHANGED, InventoryStatus.UNKNOWN}:
            return ExistingInstallationKeyResult(status.INSTALLATION_UNKNOWN)
        paths = DatabaseKeyRuntimePaths.for_root(before.root)
        present = {item.relative_path for item in before.artifacts}
        if any(str(p.relative_to(before.root)) not in present
               for p in (paths.keyset_metadata, paths.envelope_registry)):
            return ExistingInstallationKeyResult(status.KEY_MISSING)
        # Reject every metadata sidecar; immutable=1 must never hide committed WAL.
        if any(str(Path(str(paths.keyset_metadata) + suffix).relative_to(before.root)) in present
               for suffix in ("-wal", "-shm", "-journal")):
            return ExistingInstallationKeyResult(status.CONTEXT_CONFLICT)
        try:
            permissions = PlatformFilePermissionManager()
            repository = SQLiteDataKeysetRepository(
                paths.keyset_metadata, permissions, checkpointed_immutable_reads=True,
            )
            active = repository.active_data_keyset()
            if (repository.pending_data_keysets() or repository.data_keysets_for_cleanup()
                    or active is not None and (active.runtime_phase is not DataKeysetRuntimePhase.ACTIVE
                                              or active.database_context_id is None)):
                return ExistingInstallationKeyResult(status.CONTEXT_CONFLICT)
            if active is None:
                return ExistingInstallationKeyResult(status.KEY_MISSING)
            store = self._key_store if self._key_store is not None else build_platform_data_master_key_store()
            try:
                observed = store.read(installation_id=installation_id, key_id=active.key_id)
            except Exception:
                return ExistingInstallationKeyResult(status.KEYCHAIN_UNAVAILABLE)
            failures = {
                DataMasterKeyStoreStatus.NOT_FOUND: status.KEY_MISSING,
                DataMasterKeyStoreStatus.ACCESS_DENIED: status.ACCESS_DENIED,
                DataMasterKeyStoreStatus.CORRUPT: status.CONTEXT_CONFLICT,
                DataMasterKeyStoreStatus.UNSUPPORTED: status.KEYCHAIN_UNAVAILABLE,
                DataMasterKeyStoreStatus.ERROR: status.KEYCHAIN_UNAVAILABLE,
            }
            if observed.status is not DataMasterKeyStoreStatus.SUCCESS:
                return ExistingInstallationKeyResult(failures.get(observed.status, status.KEYCHAIN_UNAVAILABLE))
            if (not isinstance(observed.key_material, bytes)
                    or len(observed.key_material) != DATA_MASTER_KEY_BYTES
                    or data_master_key_fingerprint(observed.key_material) != active.fingerprint_sha256):
                return ExistingInstallationKeyResult(status.CONTEXT_CONFLICT)
            dmk = LoadedDataMasterKey(active.key_id, active.generation, observed.key_material)
            envelopes = FileDatabaseKeyEnvelopeRepository(paths.envelope_registry, permissions)
            auth_key = derive_database_key_registry_auth_key(
                dmk, database_context_id=active.database_context_id,
            )
            authenticated_envelopes = envelopes.load(auth_key)
            if (len(authenticated_envelopes) != 1
                    or authenticated_envelopes[0].lifecycle_status is not DatabaseKeyEnvelopeStatus.ACTIVE
                    or envelopes.highest_generation(auth_key) != DATABASE_KEY_RUNTIME_GENERATION):
                return ExistingInstallationKeyResult(status.CONTEXT_CONFLICT)
            key = DatabaseKeyEnvelopeService(
                repository=envelopes, random_source=SystemRandomSource(), clock=SystemClock(),
            ).load_active(dmk, expected_generation=DATABASE_KEY_RUNTIME_GENERATION)
            # Compare the authenticated opened context, not unauthenticated peek metadata.
            if envelopes.database_context_id(auth_key) != active.database_context_id:
                return ExistingInstallationKeyResult(status.CONTEXT_CONFLICT)
            loaded = LoadedDatabaseKeyRuntime(
                active.database_context_id, dmk.key_id, dmk.generation,
                data_master_key_fingerprint(dmk.key_material), key.key_id, key.generation,
                hashlib.sha256(key.key_material).hexdigest(), False, dmk, key,
            )
            if before != inventory_port.inspect(root):
                return ExistingInstallationKeyResult(status.INSTALLATION_UNKNOWN)
            return ExistingInstallationKeyResult(status.VALID, installation_id, loaded)
        except (SecurityStoreError, DatabaseKeyEnvelopeError, ValueError, OSError):
            return ExistingInstallationKeyResult(status.CONTEXT_CONFLICT)
