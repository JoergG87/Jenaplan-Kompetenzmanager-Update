"""Qt-free Data Master Key values and lifecycle coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import base64
import hashlib
import json
from typing import Mapping

from .domain import AccountStatus, SecurityError, SecurityStoreError, validate_uuid4
from .ports import DataKeysetRepository, DataMasterKeyStore, RandomSource


DATA_MASTER_KEY_BYTES = 32
DATA_MASTER_KEY_PURPOSE = "data_master_key"
DATA_MASTER_KEY_ALGORITHM = "random-256"
KEY_ENVELOPE_FORMAT_VERSION = 1
KEY_ENVELOPE_MAX_BYTES = 16 * 1024


class DataKeysetStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    FAILED = "failed"


class DataKeysetRuntimePhase(str, Enum):
    """Non-secret publish progress for the gated DMK/Database-Key runtime."""

    PREPARED = "prepared"
    DMK_PUBLISHED = "dmk_published"
    DATABASE_KEY_GENERATION_STARTED = "database_key_generation_started"
    ENVELOPE_PUBLISHED = "envelope_published"
    DATABASE_KEY_ACTIVE = "database_key_active"
    ACTIVE = "active"


class DataMasterKeyStoreStatus(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    ACCESS_DENIED = "access_denied"
    CORRUPT = "corrupt"
    ERROR = "error"


class DataMasterKeyLifecycleError(SecurityError):
    """Sanitized lifecycle failure which never includes key material."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DataKeyset:
    key_id: str
    generation: int
    status: DataKeysetStatus
    fingerprint_sha256: str
    runtime_phase: DataKeysetRuntimePhase = DataKeysetRuntimePhase.PREPARED
    database_context_id: str | None = None


@dataclass(frozen=True)
class DataMasterKeyReadResult:
    status: DataMasterKeyStoreStatus
    key_material: bytes | None = field(default=None, repr=False)


@dataclass(frozen=True)
class LoadedDataMasterKey:
    key_id: str
    generation: int
    key_material: bytes = field(repr=False)


@dataclass(frozen=True)
class KeyEnvelope:
    """Portable container for already protected, never plaintext key material."""

    format_version: int
    key_id: str
    purpose: str
    algorithm: str
    metadata: Mapping[str, str]
    protected_key_material: bytes = field(repr=False)

    def to_bytes(self) -> bytes:
        _validate_key_envelope(self)
        payload = {
            "algorithm": self.algorithm,
            "format_version": self.format_version,
            "key_id": self.key_id,
            "metadata": dict(sorted(self.metadata.items())),
            "protected_key_material": _base64url_encode(self.protected_key_material),
            "purpose": self.purpose,
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        if len(encoded) > KEY_ENVELOPE_MAX_BYTES:
            raise DataMasterKeyLifecycleError("key_envelope_size_invalid")
        return encoded

    @classmethod
    def from_bytes(cls, value: bytes) -> "KeyEnvelope":
        if not isinstance(value, bytes) or not value or len(value) > KEY_ENVELOPE_MAX_BYTES:
            raise DataMasterKeyLifecycleError("key_envelope_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise DataMasterKeyLifecycleError("key_envelope_format_invalid") from None
        if not isinstance(payload, dict) or set(payload) != {
            "algorithm",
            "format_version",
            "key_id",
            "metadata",
            "protected_key_material",
            "purpose",
        }:
            raise DataMasterKeyLifecycleError("key_envelope_fields_invalid")
        try:
            envelope = cls(
                format_version=payload["format_version"],
                key_id=payload["key_id"],
                purpose=payload["purpose"],
                algorithm=payload["algorithm"],
                metadata=payload["metadata"],
                protected_key_material=_base64url_decode(payload["protected_key_material"]),
            )
            _validate_key_envelope(envelope)
        except (TypeError, ValueError, SecurityStoreError):
            raise DataMasterKeyLifecycleError("key_envelope_fields_invalid") from None
        if envelope.to_bytes() != value:
            raise DataMasterKeyLifecycleError("key_envelope_not_canonical")
        return envelope


def data_master_key_fingerprint(key_material: bytes) -> str:
    if not isinstance(key_material, bytes) or len(key_material) != DATA_MASTER_KEY_BYTES:
        raise DataMasterKeyLifecycleError("data_master_key_length_invalid")
    return hashlib.sha256(key_material).hexdigest()


class DataMasterKeyService:
    """Coordinate metadata and platform storage without accepting an app password."""

    def __init__(
        self,
        *,
        repository: DataKeysetRepository,
        key_store: DataMasterKeyStore,
        random_source: RandomSource,
        account_loader,
    ) -> None:
        self._repository = repository
        self._key_store = key_store
        self._random = random_source
        self._account_loader = account_loader

    def provision(self) -> LoadedDataMasterKey:
        account = self._active_account()
        self._recover_pending(account.installation_id)
        if self._repository.active_data_keyset() is not None:
            raise DataMasterKeyLifecycleError("active_data_master_key_exists")
        if not self._key_store.supported:
            raise DataMasterKeyLifecycleError("data_master_key_store_unsupported")

        key_material = bytearray(self._random.bytes(DATA_MASTER_KEY_BYTES))
        stored = False
        try:
            if len(key_material) != DATA_MASTER_KEY_BYTES:
                raise DataMasterKeyLifecycleError("data_master_key_random_invalid")
            key_id = self._random.uuid4()
            validate_uuid4(key_id)
            keyset = DataKeyset(
                key_id=key_id,
                generation=self._repository.next_data_key_generation(),
                status=DataKeysetStatus.PENDING,
                fingerprint_sha256=hashlib.sha256(key_material).hexdigest(),
            )
            self._repository.prepare_data_keyset(keyset)
            try:
                self._key_store.create(
                    installation_id=account.installation_id,
                    key_id=key_id,
                    key_material=bytes(key_material),
                )
                stored = True
            except Exception:
                self._repository.fail_data_keyset(key_id=key_id)
                raise DataMasterKeyLifecycleError("data_master_key_store_create_failed") from None
            try:
                active = self._repository.activate_data_keyset(
                    key_id=key_id
                )
            except Exception:
                if stored:
                    self._delete_best_effort(account.installation_id, key_id)
                try:
                    self._repository.fail_data_keyset(
                        key_id=key_id
                    )
                except Exception:
                    pass
                raise DataMasterKeyLifecycleError("data_master_key_activation_failed") from None
            return LoadedDataMasterKey(
                key_id=active.key_id,
                generation=active.generation,
                key_material=bytes(key_material),
            )
        finally:
            for index in range(len(key_material)):
                key_material[index] = 0

    def create_pending(self, *, fault_hook=None) -> LoadedDataMasterKey:
        """Publish a new DMK but deliberately leave its keyset pending.

        This staged path is reserved for the gated combined runtime.  Unlike
        ``provision()``, it never deletes a possibly correct Keychain value
        when a later metadata operation fails.
        """

        account = self._active_account()
        if self._repository.active_data_keyset() is not None:
            raise DataMasterKeyLifecycleError("active_data_master_key_exists")
        if self._repository.pending_data_keysets():
            raise DataMasterKeyLifecycleError("pending_data_master_key_exists")
        if not self._key_store.supported:
            raise DataMasterKeyLifecycleError("data_master_key_store_unsupported")

        key_material = bytearray(self._random.bytes(DATA_MASTER_KEY_BYTES))
        try:
            if len(key_material) != DATA_MASTER_KEY_BYTES:
                raise DataMasterKeyLifecycleError("data_master_key_random_invalid")
            key_id = self._random.uuid4()
            validate_uuid4(key_id)
            keyset = DataKeyset(
                key_id=key_id,
                generation=self._repository.next_data_key_generation(),
                status=DataKeysetStatus.PENDING,
                fingerprint_sha256=hashlib.sha256(key_material).hexdigest(),
            )
            self._repository.prepare_data_keyset(keyset)
            if fault_hook is not None:
                fault_hook("before_keychain_publish")
            try:
                self._key_store.create(
                    installation_id=account.installation_id,
                    key_id=key_id,
                    key_material=bytes(key_material),
                )
            except Exception as error:
                code = getattr(error, "code", str(error))
                if code == "data_master_key_access_denied":
                    raise DataMasterKeyLifecycleError(
                        "data_master_key_access_denied"
                    ) from None
                raise DataMasterKeyLifecycleError(
                    "data_master_key_store_create_failed"
                ) from None
            if fault_hook is not None:
                fault_hook("after_keychain_publish_before_keyset_persistence")
            published = self._repository.advance_pending_data_keyset(
                key_id=key_id,
                expected_phase=DataKeysetRuntimePhase.PREPARED,
                replacement_phase=DataKeysetRuntimePhase.DMK_PUBLISHED,
            )
            result = self._read(account.installation_id, published)
            if result.status is not DataMasterKeyStoreStatus.SUCCESS:
                raise DataMasterKeyLifecycleError(
                    self._read_failure_code(result.status, pending=True)
                )
            assert result.key_material is not None
            return LoadedDataMasterKey(
                key_id=published.key_id,
                generation=published.generation,
                key_material=result.key_material,
            )
        finally:
            for index in range(len(key_material)):
                key_material[index] = 0

    def load_pending(self) -> LoadedDataMasterKey:
        """Load one pending DMK and recover only a confirmed Keychain publish."""

        account = self._active_account()
        pending = self._repository.pending_data_keysets()
        if len(pending) != 1:
            raise DataMasterKeyLifecycleError("pending_data_master_key_cardinality_invalid")
        keyset = pending[0]
        result = self._read(account.installation_id, keyset)
        if result.status is not DataMasterKeyStoreStatus.SUCCESS:
            raise DataMasterKeyLifecycleError(
                self._read_failure_code(result.status, pending=True)
            )
        assert result.key_material is not None
        if keyset.runtime_phase is DataKeysetRuntimePhase.PREPARED:
            keyset = self._repository.advance_pending_data_keyset(
                key_id=keyset.key_id,
                expected_phase=DataKeysetRuntimePhase.PREPARED,
                replacement_phase=DataKeysetRuntimePhase.DMK_PUBLISHED,
            )
        return LoadedDataMasterKey(
            key_id=keyset.key_id,
            generation=keyset.generation,
            key_material=result.key_material,
        )

    def activate_pending(self, *, key_id: str) -> LoadedDataMasterKey:
        """Activate a previously verified pending DMK without regeneration."""

        account = self._active_account()
        pending = self._repository.pending_data_keysets()
        if len(pending) != 1 or pending[0].key_id != key_id:
            raise DataMasterKeyLifecycleError("pending_data_master_key_missing")
        result = self._read(account.installation_id, pending[0])
        if result.status is not DataMasterKeyStoreStatus.SUCCESS:
            raise DataMasterKeyLifecycleError(
                self._read_failure_code(result.status, pending=True)
            )
        assert result.key_material is not None
        active = self._repository.activate_data_keyset(key_id=key_id)
        return LoadedDataMasterKey(
            key_id=active.key_id,
            generation=active.generation,
            key_material=result.key_material,
        )

    def load(self) -> LoadedDataMasterKey:
        account = self._active_account()
        self._recover_pending(account.installation_id)
        keyset = self._repository.active_data_keyset()
        if keyset is None:
            raise DataMasterKeyLifecycleError("active_data_master_key_missing")
        result = self._read(account.installation_id, keyset)
        if result.status is DataMasterKeyStoreStatus.SUCCESS:
            assert result.key_material is not None
            return LoadedDataMasterKey(
                key_id=keyset.key_id,
                generation=keyset.generation,
                key_material=result.key_material,
            )
        if result.status is DataMasterKeyStoreStatus.ACCESS_DENIED:
            raise DataMasterKeyLifecycleError("data_master_key_access_denied")
        if result.status is DataMasterKeyStoreStatus.UNSUPPORTED:
            raise DataMasterKeyLifecycleError("data_master_key_store_unsupported")
        if result.status is DataMasterKeyStoreStatus.ERROR:
            raise DataMasterKeyLifecycleError("data_master_key_store_read_failed")
        self._repository.fail_data_keyset(key_id=keyset.key_id)
        code = {
            DataMasterKeyStoreStatus.NOT_FOUND: "data_master_key_not_found",
            DataMasterKeyStoreStatus.CORRUPT: "data_master_key_corrupt",
            DataMasterKeyStoreStatus.ERROR: "data_master_key_store_read_failed",
        }.get(result.status, "data_master_key_store_read_failed")
        raise DataMasterKeyLifecycleError(code)

    def delete(self) -> bool:
        account = self._active_account()
        keyset = self._repository.active_data_keyset()
        changed = False
        if keyset is not None:
            if not self._repository.revoke_data_keyset(
                key_id=keyset.key_id
            ):
                raise DataMasterKeyLifecycleError("data_master_key_revoke_failed")
            changed = True
        cleanup = self._repository.data_keysets_for_cleanup()
        if cleanup and not self._key_store.supported:
            raise DataMasterKeyLifecycleError("data_master_key_store_unsupported")
        failed = False
        for terminal in cleanup:
            try:
                changed = self._key_store.delete(
                    installation_id=account.installation_id, key_id=terminal.key_id
                ) or changed
            except Exception:
                failed = True
        if failed:
            raise DataMasterKeyLifecycleError("data_master_key_store_delete_failed") from None
        return changed

    def _recover_pending(self, installation_id: str) -> None:
        for keyset in self._repository.pending_data_keysets():
            if (
                keyset.database_context_id is not None
                or keyset.runtime_phase
                not in {
                    DataKeysetRuntimePhase.PREPARED,
                    DataKeysetRuntimePhase.DMK_PUBLISHED,
                }
            ):
                raise DataMasterKeyLifecycleError(
                    "pending_data_master_key_runtime_incomplete"
                )
            result = self._read(installation_id, keyset)
            if result.status is DataMasterKeyStoreStatus.SUCCESS:
                self._repository.activate_data_keyset(
                    key_id=keyset.key_id
                )
                continue
            if result.status is DataMasterKeyStoreStatus.NOT_FOUND:
                self._repository.fail_data_keyset(
                    key_id=keyset.key_id
                )
                continue
            if result.status is DataMasterKeyStoreStatus.ACCESS_DENIED:
                raise DataMasterKeyLifecycleError("data_master_key_access_denied")
            if result.status is DataMasterKeyStoreStatus.UNSUPPORTED:
                raise DataMasterKeyLifecycleError("data_master_key_store_unsupported")
            if result.status is DataMasterKeyStoreStatus.ERROR:
                raise DataMasterKeyLifecycleError("data_master_key_store_read_failed")
            self._repository.fail_data_keyset(
                key_id=keyset.key_id
            )
            raise DataMasterKeyLifecycleError("pending_data_master_key_corrupt")

    def _read(self, installation_id: str, keyset: DataKeyset) -> DataMasterKeyReadResult:
        try:
            result = self._key_store.read(
                installation_id=installation_id, key_id=keyset.key_id
            )
        except Exception:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.ERROR)
        if result.status is not DataMasterKeyStoreStatus.SUCCESS:
            return result
        material = result.key_material
        if material is None or len(material) != DATA_MASTER_KEY_BYTES:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.CORRUPT)
        if not hashlib.sha256(material).hexdigest() == keyset.fingerprint_sha256:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.CORRUPT)
        return result

    @staticmethod
    def _read_failure_code(
        status: DataMasterKeyStoreStatus, *, pending: bool
    ) -> str:
        if status is DataMasterKeyStoreStatus.ACCESS_DENIED:
            return "data_master_key_access_denied"
        if status is DataMasterKeyStoreStatus.UNSUPPORTED:
            return "data_master_key_store_unsupported"
        if status is DataMasterKeyStoreStatus.ERROR:
            return "data_master_key_store_read_failed"
        if status is DataMasterKeyStoreStatus.NOT_FOUND:
            return (
                "pending_data_master_key_not_found"
                if pending
                else "data_master_key_not_found"
            )
        if status is DataMasterKeyStoreStatus.CORRUPT:
            return (
                "pending_data_master_key_corrupt"
                if pending
                else "data_master_key_corrupt"
            )
        return "data_master_key_store_read_failed"

    def _active_account(self):
        account = self._account_loader()
        if account.status is not AccountStatus.ACTIVE:
            raise DataMasterKeyLifecycleError("data_master_key_account_not_active")
        return account

    def _delete_best_effort(self, installation_id: str, key_id: str) -> None:
        try:
            self._key_store.delete(installation_id=installation_id, key_id=key_id)
        except Exception:
            pass


def _validate_key_envelope(envelope: KeyEnvelope) -> None:
    if envelope.format_version != KEY_ENVELOPE_FORMAT_VERSION:
        raise DataMasterKeyLifecycleError("key_envelope_version_unsupported")
    validate_uuid4(envelope.key_id)
    if not isinstance(envelope.purpose, str) or not envelope.purpose or len(envelope.purpose) > 80:
        raise DataMasterKeyLifecycleError("key_envelope_purpose_invalid")
    if not isinstance(envelope.algorithm, str) or not envelope.algorithm or len(envelope.algorithm) > 120:
        raise DataMasterKeyLifecycleError("key_envelope_algorithm_invalid")
    if not isinstance(envelope.metadata, Mapping) or len(envelope.metadata) > 32:
        raise DataMasterKeyLifecycleError("key_envelope_metadata_invalid")
    for key, value in envelope.metadata.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise DataMasterKeyLifecycleError("key_envelope_metadata_invalid")
        if not key or len(key) > 80 or len(value) > 512:
            raise DataMasterKeyLifecycleError("key_envelope_metadata_invalid")
    if not isinstance(envelope.protected_key_material, bytes) or not envelope.protected_key_material:
        raise DataMasterKeyLifecycleError("key_envelope_material_invalid")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise ValueError("invalid base64url")
    padding = "=" * ((4 - len(value) % 4) % 4)
    decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    if _base64url_encode(decoded) != value:
        raise ValueError("non-canonical base64url")
    return decoded
