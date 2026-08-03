"""Isolated product Database-Key hierarchy and authenticated envelope values."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
import json
import re
from typing import Mapping, Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .data_keys import DATA_MASTER_KEY_BYTES, LoadedDataMasterKey
from .domain import validate_uuid4
from .ports import RandomSource, UtcClock


DATABASE_KEY_BYTES = 32
DATABASE_KEY_NONCE_BYTES = 12
DATABASE_KEY_ENVELOPE_VERSION = 1
DATABASE_KEY_ENVELOPE_MAX_BYTES = 16 * 1024
DATABASE_KEY_PURPOSE = "jenaplan-kompetenzmanager/database-key/v1"
DATABASE_KEY_WRAP_PURPOSE = "jenaplan-kompetenzmanager/database-key-wrap/v1"
MIGRATION_JOURNAL_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/migration-journal-auth/v1"
)
DATABASE_KEY_REGISTRY_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/database-key-registry-auth/v1"
)
DATABASE_KEY_WRAP_ALGORITHM = "aes-256-gcm"
DOMAIN_KDF_ALGORITHM = "hkdf-sha256"
DOMAIN_KDF_VERSION = 1
_HKDF_SALT = b"jenaplan-kompetenzmanager/hkdf-sha256/extract-salt/v1"
_UTC_PATTERN = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


class DatabaseKeyEnvelopeError(RuntimeError):
    """Sanitized fail-closed error that never embeds key material."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class DatabaseKeyEnvelopeStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    FAILED = "failed"


@dataclass(frozen=True)
class DerivedDomainKey:
    purpose: str
    derivation_version: int
    key_material: bytes = field(repr=False)


@dataclass(frozen=True)
class DatabaseKey:
    key_id: str
    generation: int
    key_material: bytes = field(repr=False)


@dataclass(frozen=True)
class DatabaseKeyEnvelope:
    envelope_version: int
    key_id: str
    key_generation: int
    rewrap_revision: int
    key_purpose: str
    lifecycle_status: DatabaseKeyEnvelopeStatus
    wrapping_algorithm: str
    kdf_algorithm: str
    kdf_version: int
    wrapping_dmk_key_id: str
    wrapping_dmk_generation: int
    database_context_id: str
    nonce: bytes
    created_at: str
    ciphertext: bytes = field(repr=False)

    def authenticated_metadata(self) -> dict[str, object]:
        return {
            "created_at": self.created_at,
            "database_context_id": self.database_context_id,
            "envelope_version": self.envelope_version,
            "kdf_algorithm": self.kdf_algorithm,
            "kdf_version": self.kdf_version,
            "key_generation": self.key_generation,
            "key_id": self.key_id,
            "key_purpose": self.key_purpose,
            "lifecycle_status": self.lifecycle_status.value,
            "nonce": _base64url_encode(self.nonce),
            "rewrap_revision": self.rewrap_revision,
            "wrapping_algorithm": self.wrapping_algorithm,
            "wrapping_dmk_generation": self.wrapping_dmk_generation,
            "wrapping_dmk_key_id": self.wrapping_dmk_key_id,
        }

    def aad(self) -> bytes:
        _validate_envelope(self)
        return _canonical_json(self.authenticated_metadata())

    def to_payload(self) -> dict[str, object]:
        _validate_envelope(self)
        return {
            **self.authenticated_metadata(),
            "ciphertext": _base64url_encode(self.ciphertext),
        }

    def to_bytes(self) -> bytes:
        encoded = _canonical_json(self.to_payload())
        if len(encoded) > DATABASE_KEY_ENVELOPE_MAX_BYTES:
            raise DatabaseKeyEnvelopeError("database_key_envelope_size_invalid")
        return encoded

    @classmethod
    def from_payload(cls, payload: object) -> "DatabaseKeyEnvelope":
        required = {
            "ciphertext",
            "created_at",
            "database_context_id",
            "envelope_version",
            "kdf_algorithm",
            "kdf_version",
            "key_generation",
            "key_id",
            "key_purpose",
            "lifecycle_status",
            "nonce",
            "rewrap_revision",
            "wrapping_algorithm",
            "wrapping_dmk_generation",
            "wrapping_dmk_key_id",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise DatabaseKeyEnvelopeError("database_key_envelope_fields_invalid")
        try:
            envelope = cls(
                envelope_version=payload["envelope_version"],
                key_id=payload["key_id"],
                key_generation=payload["key_generation"],
                rewrap_revision=payload["rewrap_revision"],
                key_purpose=payload["key_purpose"],
                lifecycle_status=DatabaseKeyEnvelopeStatus(
                    payload["lifecycle_status"]
                ),
                wrapping_algorithm=payload["wrapping_algorithm"],
                kdf_algorithm=payload["kdf_algorithm"],
                kdf_version=payload["kdf_version"],
                wrapping_dmk_key_id=payload["wrapping_dmk_key_id"],
                wrapping_dmk_generation=payload["wrapping_dmk_generation"],
                database_context_id=payload["database_context_id"],
                nonce=_base64url_decode(payload["nonce"]),
                created_at=payload["created_at"],
                ciphertext=_base64url_decode(payload["ciphertext"]),
            )
            _validate_envelope(envelope)
        except DatabaseKeyEnvelopeError:
            raise
        except Exception:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_fields_invalid"
            ) from None
        return envelope

    @classmethod
    def from_bytes(cls, value: bytes) -> "DatabaseKeyEnvelope":
        if (
            not isinstance(value, bytes)
            or not value
            or len(value) > DATABASE_KEY_ENVELOPE_MAX_BYTES
        ):
            raise DatabaseKeyEnvelopeError("database_key_envelope_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_format_invalid"
            ) from None
        envelope = cls.from_payload(payload)
        if envelope.to_bytes() != value:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_not_canonical"
            )
        return envelope


class DatabaseKeyEnvelopeRepositoryPort(Protocol):
    def exists(self) -> bool: ...
    def peek_context(self) -> str: ...
    def load(self, auth_key: DerivedDomainKey) -> tuple[DatabaseKeyEnvelope, ...]: ...
    def highest_generation(self, auth_key: DerivedDomainKey) -> int: ...
    def database_context_id(self, auth_key: DerivedDomainKey) -> str: ...
    def create(
        self,
        envelopes: tuple[DatabaseKeyEnvelope, ...],
        auth_key: DerivedDomainKey,
    ) -> None: ...
    def replace(
        self,
        expected: tuple[DatabaseKeyEnvelope, ...],
        replacement: tuple[DatabaseKeyEnvelope, ...],
        auth_key: DerivedDomainKey,
    ) -> None: ...


def derive_domain_separated_key(
    dmk: LoadedDataMasterKey,
    *,
    purpose: str,
    derivation_version: int,
    context: Mapping[str, str | int],
) -> DerivedDomainKey:
    """Derive one 256-bit key from a random DMK with explicit domain context."""

    _validate_loaded_dmk(dmk)
    if (
        not isinstance(purpose, str)
        or not purpose.startswith("jenaplan-kompetenzmanager/")
        or not purpose.endswith(f"/v{derivation_version}")
        or len(purpose) > 120
    ):
        raise DatabaseKeyEnvelopeError("domain_key_purpose_invalid")
    _require_positive_int(derivation_version, "domain_key_version_invalid")
    if not isinstance(context, Mapping) or not context or len(context) > 16:
        raise DatabaseKeyEnvelopeError("domain_key_context_invalid")
    normalized_context: dict[str, str | int] = {}
    for key, value in context.items():
        if not isinstance(key, str) or not key or len(key) > 80:
            raise DatabaseKeyEnvelopeError("domain_key_context_invalid")
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise DatabaseKeyEnvelopeError("domain_key_context_invalid")
        if isinstance(value, str) and (not value or len(value) > 160):
            raise DatabaseKeyEnvelopeError("domain_key_context_invalid")
        if isinstance(value, int) and value < 1:
            raise DatabaseKeyEnvelopeError("domain_key_context_invalid")
        normalized_context[key] = value
    info = _canonical_json(
        {
            "context": normalized_context,
            "derivation_version": derivation_version,
            "dmk_generation": dmk.generation,
            "dmk_key_id": dmk.key_id,
            "purpose": purpose,
        }
    )
    material = HKDF(
        algorithm=hashes.SHA256(),
        length=DATABASE_KEY_BYTES,
        salt=_HKDF_SALT,
        info=info,
    ).derive(dmk.key_material)
    return DerivedDomainKey(purpose, derivation_version, material)


def derive_database_wrapping_key(
    dmk: LoadedDataMasterKey,
    *,
    database_context_id: str,
    key_generation: int,
    rewrap_revision: int = 1,
    derivation_version: int = DOMAIN_KDF_VERSION,
) -> DerivedDomainKey:
    validate_uuid4(database_context_id)
    _require_positive_int(key_generation, "database_key_generation_invalid")
    _require_positive_int(rewrap_revision, "database_key_rewrap_revision_invalid")
    purpose = (
        DATABASE_KEY_WRAP_PURPOSE
        if derivation_version == DOMAIN_KDF_VERSION
        else f"jenaplan-kompetenzmanager/database-key-wrap/v{derivation_version}"
    )
    return derive_domain_separated_key(
        dmk,
        purpose=purpose,
        derivation_version=derivation_version,
        context={
            "database_context_id": database_context_id,
            "database_key_generation": key_generation,
            "rewrap_revision": rewrap_revision,
        },
    )


def derive_migration_journal_auth_key(
    dmk: LoadedDataMasterKey,
    *,
    migration_id: str,
    derivation_version: int = DOMAIN_KDF_VERSION,
) -> DerivedDomainKey:
    validate_uuid4(migration_id)
    purpose = (
        MIGRATION_JOURNAL_AUTH_PURPOSE
        if derivation_version == DOMAIN_KDF_VERSION
        else f"jenaplan-kompetenzmanager/migration-journal-auth/v{derivation_version}"
    )
    return derive_domain_separated_key(
        dmk,
        purpose=purpose,
        derivation_version=derivation_version,
        context={"migration_id": migration_id},
    )


def derive_database_key_registry_auth_key(
    dmk: LoadedDataMasterKey,
    *,
    database_context_id: str,
    derivation_version: int = DOMAIN_KDF_VERSION,
) -> DerivedDomainKey:
    validate_uuid4(database_context_id)
    purpose = (
        DATABASE_KEY_REGISTRY_AUTH_PURPOSE
        if derivation_version == DOMAIN_KDF_VERSION
        else f"jenaplan-kompetenzmanager/database-key-registry-auth/v{derivation_version}"
    )
    return derive_domain_separated_key(
        dmk,
        purpose=purpose,
        derivation_version=derivation_version,
        context={"database_context_id": database_context_id},
    )


class DatabaseKeyEnvelopeService:
    """Coordinate isolated Database-Key generation, AEAD and envelope lifecycle."""

    def __init__(
        self,
        *,
        repository: DatabaseKeyEnvelopeRepositoryPort,
        random_source: RandomSource,
        clock: UtcClock,
    ) -> None:
        self._repository = repository
        self._random = random_source
        self._clock = clock

    def create_pending(
        self,
        dmk: LoadedDataMasterKey,
        *,
        database_context_id: str,
        generation: int,
        fault_hook=None,
    ) -> DatabaseKey:
        validate_uuid4(database_context_id)
        _require_positive_int(generation, "database_key_generation_invalid")
        current, registry_auth_key = self._load_or_empty(
            dmk, database_context_id=database_context_id
        )
        opened = self._open_all(dmk, current)
        if any(
            envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.PENDING
            for envelope, _key in opened
        ):
            raise DatabaseKeyEnvelopeError("pending_database_key_exists")
        if self._repository.exists() and (
            self._repository.database_context_id(registry_auth_key)
            != database_context_id
        ):
            raise DatabaseKeyEnvelopeError("database_key_context_mismatch")
        expected_generation = (
            self._repository.highest_generation(registry_auth_key) + 1
            if self._repository.exists()
            else 1
        )
        if generation != expected_generation:
            raise DatabaseKeyEnvelopeError("database_key_generation_invalid")
        material = bytearray(self._random.bytes(DATABASE_KEY_BYTES))
        try:
            if len(material) != DATABASE_KEY_BYTES:
                raise DatabaseKeyEnvelopeError("database_key_random_invalid")
            key_id = self._random.uuid4()
            validate_uuid4(key_id)
            key = DatabaseKey(key_id, generation, bytes(material))
            if fault_hook is not None:
                fault_hook("after_database_key_generation")
            envelope = self._seal(
                dmk,
                key=key,
                database_context_id=database_context_id,
                status=DatabaseKeyEnvelopeStatus.PENDING,
                created_at=_format_utc(self._clock.utc_now()),
            )
            replacement = (*current, envelope)
            if self._repository.exists():
                self._repository.replace(current, replacement, registry_auth_key)
            else:
                self._repository.create(replacement, registry_auth_key)
            return key
        finally:
            _erase(material)

    def activate(
        self, dmk: LoadedDataMasterKey, *, generation: int
    ) -> DatabaseKey:
        current, registry_auth_key = self._load_registry(dmk)
        opened = self._open_all(dmk, current)
        target = self._find_generation(opened, generation)
        envelope, key = target
        active = [
            item for item in opened
            if item[0].lifecycle_status is DatabaseKeyEnvelopeStatus.ACTIVE
        ]
        if envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.ACTIVE:
            if len(active) != 1:
                raise DatabaseKeyEnvelopeError("multiple_active_database_keys")
            return key
        if envelope.lifecycle_status is not DatabaseKeyEnvelopeStatus.PENDING:
            raise DatabaseKeyEnvelopeError("database_key_activation_invalid")
        if active:
            raise DatabaseKeyEnvelopeError("active_database_key_exists")
        return self._transition(
            dmk,
            current,
            envelope,
            key,
            DatabaseKeyEnvelopeStatus.ACTIVE,
            registry_auth_key,
        )

    def load_active(
        self,
        dmk: LoadedDataMasterKey,
        *,
        expected_generation: int | None = None,
    ) -> DatabaseKey:
        current, _registry_auth_key = self._load_registry(dmk)
        opened = self._open_all(dmk, current)
        active = [
            key for envelope, key in opened
            if envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.ACTIVE
        ]
        if not active:
            raise DatabaseKeyEnvelopeError("active_database_key_missing")
        if len(active) != 1:
            raise DatabaseKeyEnvelopeError("multiple_active_database_keys")
        key = active[0]
        if expected_generation is not None and key.generation != expected_generation:
            raise DatabaseKeyEnvelopeError("database_key_generation_mismatch")
        return key

    def revoke(self, dmk: LoadedDataMasterKey, *, generation: int) -> DatabaseKey:
        current, registry_auth_key = self._load_registry(dmk)
        opened = self._open_all(dmk, current)
        envelope, key = self._find_generation(opened, generation)
        if envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.REVOKED:
            return key
        if envelope.lifecycle_status is not DatabaseKeyEnvelopeStatus.ACTIVE:
            raise DatabaseKeyEnvelopeError("database_key_revocation_invalid")
        return self._transition(
            dmk,
            current,
            envelope,
            key,
            DatabaseKeyEnvelopeStatus.REVOKED,
            registry_auth_key,
        )

    def fail(self, dmk: LoadedDataMasterKey, *, generation: int) -> DatabaseKey:
        current, registry_auth_key = self._load_registry(dmk)
        opened = self._open_all(dmk, current)
        envelope, key = self._find_generation(opened, generation)
        if envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.FAILED:
            return key
        if envelope.lifecycle_status not in {
            DatabaseKeyEnvelopeStatus.PENDING,
            DatabaseKeyEnvelopeStatus.ACTIVE,
        }:
            raise DatabaseKeyEnvelopeError("database_key_failure_transition_invalid")
        return self._transition(
            dmk,
            current,
            envelope,
            key,
            DatabaseKeyEnvelopeStatus.FAILED,
            registry_auth_key,
        )

    def delete_terminal_metadata(
        self, dmk: LoadedDataMasterKey, *, generation: int
    ) -> bool:
        if not self._repository.exists():
            return False
        current, registry_auth_key = self._load_registry(dmk)
        opened = self._open_all(dmk, current)
        matches = [item for item in opened if item[0].key_generation == generation]
        if not matches:
            if generation <= self._repository.highest_generation(registry_auth_key):
                return False
            raise DatabaseKeyEnvelopeError("database_key_generation_unknown")
        envelope, _key = self._find_generation(opened, generation)
        if envelope.lifecycle_status not in {
            DatabaseKeyEnvelopeStatus.REVOKED,
            DatabaseKeyEnvelopeStatus.FAILED,
        }:
            raise DatabaseKeyEnvelopeError("database_key_metadata_delete_invalid")
        replacement = tuple(item for item in current if item is not envelope)
        self._repository.replace(current, replacement, registry_auth_key)
        return True

    def _load_or_empty(
        self, dmk: LoadedDataMasterKey, *, database_context_id: str
    ) -> tuple[tuple[DatabaseKeyEnvelope, ...], DerivedDomainKey]:
        if self._repository.exists():
            return self._load_registry(dmk)
        auth_key = derive_database_key_registry_auth_key(
            dmk, database_context_id=database_context_id
        )
        return (), auth_key

    def _load_registry(
        self, dmk: LoadedDataMasterKey
    ) -> tuple[tuple[DatabaseKeyEnvelope, ...], DerivedDomainKey]:
        if not self._repository.exists():
            raise DatabaseKeyEnvelopeError("database_key_envelope_missing")
        context_id = self._repository.peek_context()
        auth_key = derive_database_key_registry_auth_key(
            dmk, database_context_id=context_id
        )
        return self._repository.load(auth_key), auth_key

    def _open_all(
        self,
        dmk: LoadedDataMasterKey,
        envelopes: tuple[DatabaseKeyEnvelope, ...],
    ) -> tuple[tuple[DatabaseKeyEnvelope, DatabaseKey], ...]:
        opened = tuple((envelope, self._open(dmk, envelope)) for envelope in envelopes)
        generations = [envelope.key_generation for envelope in envelopes]
        key_ids = [envelope.key_id for envelope in envelopes]
        if len(set(generations)) != len(generations) or len(set(key_ids)) != len(key_ids):
            raise DatabaseKeyEnvelopeError("database_key_envelope_duplicate")
        if sum(
            envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.ACTIVE
            for envelope in envelopes
        ) > 1:
            raise DatabaseKeyEnvelopeError("multiple_active_database_keys")
        if sum(
            envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.PENDING
            for envelope in envelopes
        ) > 1:
            raise DatabaseKeyEnvelopeError("multiple_pending_database_keys")
        return opened

    @staticmethod
    def _find_generation(
        opened: tuple[tuple[DatabaseKeyEnvelope, DatabaseKey], ...], generation: int
    ) -> tuple[DatabaseKeyEnvelope, DatabaseKey]:
        _require_positive_int(generation, "database_key_generation_invalid")
        matches = [item for item in opened if item[0].key_generation == generation]
        if len(matches) != 1:
            raise DatabaseKeyEnvelopeError("database_key_generation_unknown")
        return matches[0]

    def _transition(
        self,
        dmk: LoadedDataMasterKey,
        current: tuple[DatabaseKeyEnvelope, ...],
        envelope: DatabaseKeyEnvelope,
        key: DatabaseKey,
        status: DatabaseKeyEnvelopeStatus,
        registry_auth_key: DerivedDomainKey,
    ) -> DatabaseKey:
        replacement_envelope = self._seal(
            dmk,
            key=key,
            database_context_id=envelope.database_context_id,
            status=status,
            created_at=envelope.created_at,
            rewrap_revision=envelope.rewrap_revision + 1,
        )
        if replacement_envelope.nonce == envelope.nonce:
            raise DatabaseKeyEnvelopeError("database_key_nonce_reused")
        replacement = tuple(
            replacement_envelope if item is envelope else item for item in current
        )
        self._repository.replace(current, replacement, registry_auth_key)
        return key

    def _seal(
        self,
        dmk: LoadedDataMasterKey,
        *,
        key: DatabaseKey,
        database_context_id: str,
        status: DatabaseKeyEnvelopeStatus,
        created_at: str,
        rewrap_revision: int = 1,
    ) -> DatabaseKeyEnvelope:
        wrapping_key = derive_database_wrapping_key(
            dmk,
            database_context_id=database_context_id,
            key_generation=key.generation,
            rewrap_revision=rewrap_revision,
        )
        nonce = self._random.bytes(DATABASE_KEY_NONCE_BYTES)
        if len(nonce) != DATABASE_KEY_NONCE_BYTES:
            raise DatabaseKeyEnvelopeError("database_key_nonce_invalid")
        header = DatabaseKeyEnvelope(
            envelope_version=DATABASE_KEY_ENVELOPE_VERSION,
            key_id=key.key_id,
            key_generation=key.generation,
            rewrap_revision=rewrap_revision,
            key_purpose=DATABASE_KEY_PURPOSE,
            lifecycle_status=status,
            wrapping_algorithm=DATABASE_KEY_WRAP_ALGORITHM,
            kdf_algorithm=DOMAIN_KDF_ALGORITHM,
            kdf_version=DOMAIN_KDF_VERSION,
            wrapping_dmk_key_id=dmk.key_id,
            wrapping_dmk_generation=dmk.generation,
            database_context_id=database_context_id,
            nonce=nonce,
            created_at=created_at,
            ciphertext=b"0" * (DATABASE_KEY_BYTES + 16),
        )
        ciphertext = AESGCM(wrapping_key.key_material).encrypt(
            nonce, key.key_material, header.aad()
        )
        return replace(header, ciphertext=ciphertext)

    @staticmethod
    def _open(
        dmk: LoadedDataMasterKey, envelope: DatabaseKeyEnvelope
    ) -> DatabaseKey:
        _validate_envelope(envelope)
        _validate_loaded_dmk(dmk)
        if (
            envelope.wrapping_dmk_key_id != dmk.key_id
            or envelope.wrapping_dmk_generation != dmk.generation
        ):
            raise DatabaseKeyEnvelopeError("database_key_dmk_binding_mismatch")
        wrapping_key = derive_database_wrapping_key(
            dmk,
            database_context_id=envelope.database_context_id,
            key_generation=envelope.key_generation,
            rewrap_revision=envelope.rewrap_revision,
            derivation_version=envelope.kdf_version,
        )
        try:
            material = AESGCM(wrapping_key.key_material).decrypt(
                envelope.nonce, envelope.ciphertext, envelope.aad()
            )
        except InvalidTag:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_authentication_failed"
            ) from None
        except Exception:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_decryption_failed"
            ) from None
        if len(material) != DATABASE_KEY_BYTES:
            raise DatabaseKeyEnvelopeError("database_key_length_invalid")
        return DatabaseKey(envelope.key_id, envelope.key_generation, material)


def _validate_envelope(envelope: DatabaseKeyEnvelope) -> None:
    if type(envelope.envelope_version) is not int:
        raise DatabaseKeyEnvelopeError("database_key_envelope_version_invalid")
    if envelope.envelope_version != DATABASE_KEY_ENVELOPE_VERSION:
        raise DatabaseKeyEnvelopeError("database_key_envelope_version_unsupported")
    validate_uuid4(envelope.key_id)
    _require_positive_int(envelope.key_generation, "database_key_generation_invalid")
    _require_positive_int(
        envelope.rewrap_revision, "database_key_rewrap_revision_invalid"
    )
    if envelope.key_purpose != DATABASE_KEY_PURPOSE:
        raise DatabaseKeyEnvelopeError("database_key_purpose_unsupported")
    if not isinstance(envelope.lifecycle_status, DatabaseKeyEnvelopeStatus):
        raise DatabaseKeyEnvelopeError("database_key_status_invalid")
    if envelope.wrapping_algorithm != DATABASE_KEY_WRAP_ALGORITHM:
        raise DatabaseKeyEnvelopeError("database_key_algorithm_unsupported")
    if envelope.kdf_algorithm != DOMAIN_KDF_ALGORITHM:
        raise DatabaseKeyEnvelopeError("database_key_kdf_unsupported")
    if type(envelope.kdf_version) is not int or envelope.kdf_version != DOMAIN_KDF_VERSION:
        raise DatabaseKeyEnvelopeError("database_key_kdf_version_unsupported")
    validate_uuid4(envelope.wrapping_dmk_key_id)
    _require_positive_int(
        envelope.wrapping_dmk_generation, "database_key_dmk_generation_invalid"
    )
    validate_uuid4(envelope.database_context_id)
    if not isinstance(envelope.nonce, bytes) or len(envelope.nonce) != DATABASE_KEY_NONCE_BYTES:
        raise DatabaseKeyEnvelopeError("database_key_nonce_invalid")
    _parse_utc(envelope.created_at)
    if (
        not isinstance(envelope.ciphertext, bytes)
        or len(envelope.ciphertext) != DATABASE_KEY_BYTES + 16
    ):
        raise DatabaseKeyEnvelopeError("database_key_ciphertext_invalid")


def _validate_loaded_dmk(dmk: LoadedDataMasterKey) -> None:
    if not isinstance(dmk, LoadedDataMasterKey):
        raise DatabaseKeyEnvelopeError("data_master_key_context_invalid")
    validate_uuid4(dmk.key_id)
    _require_positive_int(dmk.generation, "data_master_key_generation_invalid")
    if not isinstance(dmk.key_material, bytes) or len(dmk.key_material) != DATA_MASTER_KEY_BYTES:
        raise DatabaseKeyEnvelopeError("data_master_key_length_invalid")


def _require_positive_int(value: object, code: str) -> None:
    if type(value) is not int or value < 1:
        raise DatabaseKeyEnvelopeError(code)


def _canonical_json(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise DatabaseKeyEnvelopeError("database_key_envelope_fields_invalid") from None


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise DatabaseKeyEnvelopeError("database_key_envelope_base64_invalid")
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        raise DatabaseKeyEnvelopeError("database_key_envelope_base64_invalid") from None
    if _base64url_encode(decoded) != value:
        raise DatabaseKeyEnvelopeError("database_key_envelope_base64_invalid")
    return decoded


def _format_utc(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise DatabaseKeyEnvelopeError("database_key_timestamp_invalid")
    if value.tzinfo is None:
        raise DatabaseKeyEnvelopeError("database_key_timestamp_invalid")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not _UTC_PATTERN.fullmatch(value):
        raise DatabaseKeyEnvelopeError("database_key_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DatabaseKeyEnvelopeError("database_key_timestamp_invalid") from None
    return parsed.astimezone(timezone.utc)


def _erase(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0
