"""Strict cryptographic values for the isolated encrypted backup prototype.

This module defines a format and key hierarchy only.  It is not imported by
the product backup, restore, startup, login, UI, or runtime-path code.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .data_keys import LoadedDataMasterKey
from .database_keys import derive_domain_separated_key
from .domain import validate_uuid4


ENCRYPTED_BACKUP_MAGIC = b"JKMEBK01"
ENCRYPTED_BACKUP_FORMAT = "jenaplan-encrypted-backup"
ENCRYPTED_BACKUP_VERSION = 1
ENCRYPTED_BACKUP_HEADER_VERSION = 1
ENCRYPTED_BACKUP_MANIFEST_VERSION = 1
ENCRYPTED_BACKUP_CONTEXT_VERSION = 1
BACKUP_KEY_ENVELOPE_VERSION = 1
BACKUP_KEY_BYTES = 32
BACKUP_KEY_NONCE_BYTES = 12
BACKUP_KEY_WRAP_PURPOSE = (
    "jenaplan-kompetenzmanager/backup-wrapping-key/v1"
)
BACKUP_KEY_WRAP_ALGORITHM = "aes-256-gcm"
BACKUP_KEY_KDF_ALGORITHM = "hkdf-sha256"
BACKUP_KEY_KDF_VERSION = 1
BACKUP_STREAM_ALGORITHM = "libsodium-secretstream-xchacha20poly1305"
DEFAULT_BACKUP_CHUNK_SIZE = 1024 * 1024
MIN_BACKUP_CHUNK_SIZE = 64
MAX_BACKUP_CHUNK_SIZE = 8 * 1024 * 1024
MAX_BACKUP_HEADER_BYTES = 64 * 1024
MAX_BACKUP_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_BACKUP_ENTRIES = 10_000
MAX_BACKUP_ENTRY_BYTES = 1 << 50
MAX_BACKUP_TOTAL_BYTES = 1 << 52

_UTC_PATTERN = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_SHA256_PATTERN = re.compile(r"\A[0-9a-f]{64}\Z")
_VERSION_PATTERN = re.compile(r"\A[ -~]{1,160}\Z")
_RESTORE_DOCUMENT_PATTERN = re.compile(
    r"\Adocument-([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})\.bin\Z"
)


class EncryptedBackupError(RuntimeError):
    """Sanitized fail-closed error which never embeds paths or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class BackupEntryRole(str, Enum):
    SQLCIPHER_DATABASE = "sqlcipher_database"
    MANAGED_DOCUMENT = "managed_document"


@dataclass(frozen=True)
class BackupContainerContextV1:
    installation_id: str
    database_context_id: str
    app_version: str
    sqlite_version: str
    sqlcipher_version: str
    context_version: int = ENCRYPTED_BACKUP_CONTEXT_VERSION

    def to_payload(self) -> dict[str, object]:
        _validate_context(self)
        return {
            "app_version": self.app_version,
            "context_version": self.context_version,
            "database_context_id": self.database_context_id,
            "installation_id": self.installation_id,
            "sqlcipher_version": self.sqlcipher_version,
            "sqlite_version": self.sqlite_version,
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_payload())

    def binding_payload(self) -> dict[str, object]:
        """Values an opener can know before decrypting historical metadata."""

        _validate_context(self)
        return {
            "context_version": self.context_version,
            "database_context_id": self.database_context_id,
            "installation_id": self.installation_id,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "BackupContainerContextV1":
        required = {
            "app_version",
            "context_version",
            "database_context_id",
            "installation_id",
            "sqlcipher_version",
            "sqlite_version",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedBackupError("backup_context_fields_invalid")
        try:
            context = cls(
                installation_id=payload["installation_id"],
                database_context_id=payload["database_context_id"],
                app_version=payload["app_version"],
                sqlite_version=payload["sqlite_version"],
                sqlcipher_version=payload["sqlcipher_version"],
                context_version=payload["context_version"],
            )
            _validate_context(context)
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_context_fields_invalid") from None
        return context


@dataclass(frozen=True)
class BackupKeyEnvelopeV1:
    envelope_version: int
    backup_key_id: str
    wrapping_dmk_key_id: str
    wrapping_dmk_generation: int
    wrapping_algorithm: str
    kdf_algorithm: str
    kdf_version: int
    key_purpose: str
    nonce: bytes
    ciphertext: bytes = field(repr=False)

    def metadata_payload(self) -> dict[str, object]:
        _validate_envelope(self, require_ciphertext=False)
        return {
            "backup_key_id": self.backup_key_id,
            "envelope_version": self.envelope_version,
            "kdf_algorithm": self.kdf_algorithm,
            "kdf_version": self.kdf_version,
            "key_purpose": self.key_purpose,
            "nonce": base64url_encode(self.nonce),
            "wrapping_algorithm": self.wrapping_algorithm,
            "wrapping_dmk_generation": self.wrapping_dmk_generation,
            "wrapping_dmk_key_id": self.wrapping_dmk_key_id,
        }

    def to_payload(self) -> dict[str, object]:
        _validate_envelope(self)
        return {
            **self.metadata_payload(),
            "ciphertext": base64url_encode(self.ciphertext),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "BackupKeyEnvelopeV1":
        required = {
            "backup_key_id",
            "ciphertext",
            "envelope_version",
            "kdf_algorithm",
            "kdf_version",
            "key_purpose",
            "nonce",
            "wrapping_algorithm",
            "wrapping_dmk_generation",
            "wrapping_dmk_key_id",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedBackupError("backup_key_envelope_fields_invalid")
        try:
            envelope = cls(
                envelope_version=payload["envelope_version"],
                backup_key_id=payload["backup_key_id"],
                wrapping_dmk_key_id=payload["wrapping_dmk_key_id"],
                wrapping_dmk_generation=payload["wrapping_dmk_generation"],
                wrapping_algorithm=payload["wrapping_algorithm"],
                kdf_algorithm=payload["kdf_algorithm"],
                kdf_version=payload["kdf_version"],
                key_purpose=payload["key_purpose"],
                nonce=base64url_decode(payload["nonce"]),
                ciphertext=base64url_decode(payload["ciphertext"]),
            )
            _validate_envelope(envelope)
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError(
                "backup_key_envelope_fields_invalid"
            ) from None
        return envelope


@dataclass(frozen=True)
class BackupContainerHeaderV1:
    container_id: str
    chunk_size: int
    stream_header: bytes
    envelope: BackupKeyEnvelopeV1
    container_format: str = ENCRYPTED_BACKUP_FORMAT
    container_version: int = ENCRYPTED_BACKUP_VERSION
    header_version: int = ENCRYPTED_BACKUP_HEADER_VERSION
    stream_algorithm: str = BACKUP_STREAM_ALGORITHM

    def metadata_payload(self) -> dict[str, object]:
        _validate_header(self, require_ciphertext=False)
        return {
            "chunk_size": self.chunk_size,
            "container_format": self.container_format,
            "container_id": self.container_id,
            "container_version": self.container_version,
            "envelope": self.envelope.metadata_payload(),
            "header_version": self.header_version,
            "stream_algorithm": self.stream_algorithm,
            "stream_header": base64url_encode(self.stream_header),
        }

    def to_payload(self) -> dict[str, object]:
        _validate_header(self)
        payload = self.metadata_payload()
        payload["envelope"] = self.envelope.to_payload()
        return payload

    def to_bytes(self) -> bytes:
        encoded = canonical_json(self.to_payload())
        if len(encoded) > MAX_BACKUP_HEADER_BYTES:
            raise EncryptedBackupError("backup_header_size_invalid")
        return encoded

    @classmethod
    def from_bytes(cls, value: bytes) -> "BackupContainerHeaderV1":
        if (
            not isinstance(value, bytes)
            or not value
            or len(value) > MAX_BACKUP_HEADER_BYTES
        ):
            raise EncryptedBackupError("backup_header_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EncryptedBackupError("backup_header_format_invalid") from None
        required = {
            "chunk_size",
            "container_format",
            "container_id",
            "container_version",
            "envelope",
            "header_version",
            "stream_algorithm",
            "stream_header",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedBackupError("backup_header_fields_invalid")
        try:
            header = cls(
                container_id=payload["container_id"],
                chunk_size=payload["chunk_size"],
                stream_header=base64url_decode(payload["stream_header"]),
                envelope=BackupKeyEnvelopeV1.from_payload(payload["envelope"]),
                container_format=payload["container_format"],
                container_version=payload["container_version"],
                header_version=payload["header_version"],
                stream_algorithm=payload["stream_algorithm"],
            )
            _validate_header(header)
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_header_fields_invalid") from None
        if header.to_bytes() != value:
            raise EncryptedBackupError("backup_header_not_canonical")
        return header


@dataclass(frozen=True)
class BackupManifestEntryV1:
    entry_id: str
    role: BackupEntryRole
    restore_name: str
    plaintext_size: int
    sha256: str
    chunk_count: int

    def to_payload(self) -> dict[str, object]:
        _validate_manifest_entry(self)
        return {
            "chunk_count": self.chunk_count,
            "entry_id": self.entry_id,
            "plaintext_size": self.plaintext_size,
            "restore_name": self.restore_name,
            "role": self.role.value,
            "sha256": self.sha256,
        }

    @classmethod
    def from_payload(
        cls, payload: object, *, chunk_size: int
    ) -> "BackupManifestEntryV1":
        required = {
            "chunk_count",
            "entry_id",
            "plaintext_size",
            "restore_name",
            "role",
            "sha256",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedBackupError("backup_manifest_entry_fields_invalid")
        try:
            entry = cls(
                entry_id=payload["entry_id"],
                role=BackupEntryRole(payload["role"]),
                restore_name=payload["restore_name"],
                plaintext_size=payload["plaintext_size"],
                sha256=payload["sha256"],
                chunk_count=payload["chunk_count"],
            )
            _validate_manifest_entry(entry, chunk_size=chunk_size)
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError(
                "backup_manifest_entry_fields_invalid"
            ) from None
        return entry


@dataclass(frozen=True)
class EncryptedBackupManifestV1:
    container_id: str
    created_at: str
    context: BackupContainerContextV1
    entries: tuple[BackupManifestEntryV1, ...]
    total_plaintext_size: int
    chunk_size: int
    manifest_version: int = ENCRYPTED_BACKUP_MANIFEST_VERSION

    def to_payload(self) -> dict[str, object]:
        _validate_manifest(self)
        return {
            "chunk_size": self.chunk_size,
            "container_id": self.container_id,
            "created_at": self.created_at,
            "entries": [entry.to_payload() for entry in self.entries],
            "entry_count": len(self.entries),
            "manifest_version": self.manifest_version,
            "technical_context": self.context.to_payload(),
            "total_plaintext_size": self.total_plaintext_size,
        }

    def to_bytes(self) -> bytes:
        encoded = canonical_json(self.to_payload())
        if len(encoded) > MAX_BACKUP_MANIFEST_BYTES:
            raise EncryptedBackupError("backup_manifest_size_invalid")
        return encoded

    @classmethod
    def from_bytes(cls, value: bytes) -> "EncryptedBackupManifestV1":
        if (
            not isinstance(value, bytes)
            or not value
            or len(value) > MAX_BACKUP_MANIFEST_BYTES
        ):
            raise EncryptedBackupError("backup_manifest_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EncryptedBackupError("backup_manifest_format_invalid") from None
        required = {
            "chunk_size",
            "container_id",
            "created_at",
            "entries",
            "entry_count",
            "manifest_version",
            "technical_context",
            "total_plaintext_size",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedBackupError("backup_manifest_fields_invalid")
        if (
            not isinstance(payload["entries"], list)
            or isinstance(payload["entry_count"], bool)
            or not isinstance(payload["entry_count"], int)
            or payload["entry_count"] != len(payload["entries"])
        ):
            raise EncryptedBackupError("backup_manifest_entry_count_invalid")
        try:
            chunk_size = payload["chunk_size"]
            manifest = cls(
                container_id=payload["container_id"],
                created_at=payload["created_at"],
                context=BackupContainerContextV1.from_payload(
                    payload["technical_context"]
                ),
                entries=tuple(
                    BackupManifestEntryV1.from_payload(
                        item, chunk_size=chunk_size
                    )
                    for item in payload["entries"]
                ),
                total_plaintext_size=payload["total_plaintext_size"],
                chunk_size=chunk_size,
                manifest_version=payload["manifest_version"],
            )
            _validate_manifest(manifest)
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_manifest_fields_invalid") from None
        if manifest.to_bytes() != value:
            raise EncryptedBackupError("backup_manifest_not_canonical")
        return manifest


def format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    normalized = value.astimezone(timezone.utc).replace(microsecond=0)
    return normalized.strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise EncryptedBackupError("backup_canonical_json_invalid") from None


def base64url_encode(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise EncryptedBackupError("backup_base64_value_invalid")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def base64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 2 * MAX_BACKUP_HEADER_BYTES:
        raise EncryptedBackupError("backup_base64_value_invalid")
    if "=" in value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise EncryptedBackupError("backup_base64_value_invalid")
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(
            value + padding, altchars=b"-_", validate=True
        )
    except (ValueError, TypeError):
        raise EncryptedBackupError("backup_base64_value_invalid") from None
    if base64url_encode(decoded) != value:
        raise EncryptedBackupError("backup_base64_value_invalid")
    return decoded


def build_backup_key_envelope(
    dmk: LoadedDataMasterKey,
    *,
    context: BackupContainerContextV1,
    container_id: str,
    backup_key_id: str,
    stream_header: bytes,
    chunk_size: int,
    backup_key: bytes,
    nonce: bytes,
) -> BackupKeyEnvelopeV1:
    """Wrap one random Backup-Key with complete header/context AAD."""

    _validate_context(context)
    _validate_uuid(container_id, "backup_container_id_invalid")
    _validate_uuid(backup_key_id, "backup_key_id_invalid")
    _validate_dmk(dmk)
    _validate_chunk_size(chunk_size)
    if not isinstance(backup_key, bytes) or len(backup_key) != BACKUP_KEY_BYTES:
        raise EncryptedBackupError("backup_key_length_invalid")
    if not isinstance(nonce, bytes) or len(nonce) != BACKUP_KEY_NONCE_BYTES:
        raise EncryptedBackupError("backup_key_nonce_invalid")
    envelope = BackupKeyEnvelopeV1(
        envelope_version=BACKUP_KEY_ENVELOPE_VERSION,
        backup_key_id=backup_key_id,
        wrapping_dmk_key_id=dmk.key_id,
        wrapping_dmk_generation=dmk.generation,
        wrapping_algorithm=BACKUP_KEY_WRAP_ALGORITHM,
        kdf_algorithm=BACKUP_KEY_KDF_ALGORITHM,
        kdf_version=BACKUP_KEY_KDF_VERSION,
        key_purpose=BACKUP_KEY_WRAP_PURPOSE,
        nonce=nonce,
        ciphertext=b"",
    )
    header = BackupContainerHeaderV1(
        container_id=container_id,
        chunk_size=chunk_size,
        stream_header=stream_header,
        envelope=envelope,
    )
    wrapping_key = _derive_backup_wrapping_key(
        dmk,
        context=context,
        container_id=container_id,
        backup_key_id=backup_key_id,
    )
    try:
        ciphertext = AESGCM(wrapping_key).encrypt(
            nonce,
            backup_key,
            _envelope_aad(context, header),
        )
    except Exception:
        raise EncryptedBackupError("backup_key_envelope_seal_failed") from None
    sealed = BackupKeyEnvelopeV1(
        **{
            **envelope.__dict__,
            "ciphertext": ciphertext,
        }
    )
    _validate_envelope(sealed)
    return sealed


def open_backup_key_envelope(
    dmk: LoadedDataMasterKey,
    *,
    context: BackupContainerContextV1,
    header: BackupContainerHeaderV1,
) -> bytes:
    """Open one Backup-Key or fail closed without regenerating anything."""

    _validate_dmk(dmk)
    _validate_context(context)
    _validate_header(header)
    envelope = header.envelope
    if (
        dmk.key_id != envelope.wrapping_dmk_key_id
        or dmk.generation != envelope.wrapping_dmk_generation
    ):
        raise EncryptedBackupError("backup_key_envelope_dmk_mismatch")
    wrapping_key = _derive_backup_wrapping_key(
        dmk,
        context=context,
        container_id=header.container_id,
        backup_key_id=envelope.backup_key_id,
    )
    try:
        backup_key = AESGCM(wrapping_key).decrypt(
            envelope.nonce,
            envelope.ciphertext,
            _envelope_aad(context, header),
        )
    except InvalidTag:
        raise EncryptedBackupError(
            "backup_key_envelope_authentication_failed"
        ) from None
    except Exception:
        raise EncryptedBackupError("backup_key_envelope_open_failed") from None
    if len(backup_key) != BACKUP_KEY_BYTES:
        raise EncryptedBackupError("backup_key_length_invalid")
    return backup_key


def manifest_record_aad(header_bytes: bytes, plaintext_size: int) -> bytes:
    return _record_aad(
        header_bytes,
        {
            "plaintext_size": plaintext_size,
            "record_ordinal": 0,
            "record_type": "manifest",
        },
    )


def entry_record_aad(
    header_bytes: bytes,
    *,
    manifest_sha256: str,
    record_ordinal: int,
    entry: BackupManifestEntryV1,
    chunk_index: int,
    plaintext_size: int,
) -> bytes:
    _validate_manifest_entry(entry)
    if not _SHA256_PATTERN.fullmatch(manifest_sha256):
        raise EncryptedBackupError("backup_manifest_hash_invalid")
    _require_nonnegative_int(record_ordinal, "backup_record_ordinal_invalid")
    _require_nonnegative_int(chunk_index, "backup_chunk_index_invalid")
    _require_nonnegative_int(plaintext_size, "backup_chunk_size_invalid")
    return _record_aad(
        header_bytes,
        {
            "chunk_count": entry.chunk_count,
            "chunk_index": chunk_index,
            "entry_id": entry.entry_id,
            "entry_plaintext_size": entry.plaintext_size,
            "manifest_sha256": manifest_sha256,
            "plaintext_size": plaintext_size,
            "record_ordinal": record_ordinal,
            "record_type": "entry_chunk",
            "role": entry.role.value,
        },
    )


def final_record_aad(
    header_bytes: bytes,
    *,
    manifest_sha256: str,
    record_ordinal: int,
    entry_count: int,
    total_plaintext_size: int,
) -> bytes:
    if not _SHA256_PATTERN.fullmatch(manifest_sha256):
        raise EncryptedBackupError("backup_manifest_hash_invalid")
    _require_nonnegative_int(record_ordinal, "backup_record_ordinal_invalid")
    _require_positive_int(entry_count, "backup_manifest_entry_count_invalid")
    _require_nonnegative_int(
        total_plaintext_size, "backup_manifest_total_size_invalid"
    )
    return _record_aad(
        header_bytes,
        {
            "entry_count": entry_count,
            "manifest_sha256": manifest_sha256,
            "plaintext_size": 0,
            "record_ordinal": record_ordinal,
            "record_type": "final",
            "total_plaintext_size": total_plaintext_size,
        },
    )


def expected_chunk_size(
    entry: BackupManifestEntryV1, *, chunk_size: int, chunk_index: int
) -> int:
    _validate_manifest_entry(entry, chunk_size=chunk_size)
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index < 0
        or chunk_index >= entry.chunk_count
    ):
        raise EncryptedBackupError("backup_chunk_index_invalid")
    if entry.plaintext_size == 0:
        return 0
    remaining = entry.plaintext_size - (chunk_index * chunk_size)
    return min(chunk_size, remaining)


def manifest_sha256(manifest_bytes: bytes) -> str:
    if not isinstance(manifest_bytes, bytes):
        raise EncryptedBackupError("backup_manifest_format_invalid")
    return hashlib.sha256(manifest_bytes).hexdigest()


def validate_backup_chunk_size(value: int) -> None:
    _validate_chunk_size(value)


def _record_aad(header_bytes: bytes, record: Mapping[str, object]) -> bytes:
    if (
        not isinstance(header_bytes, bytes)
        or not header_bytes
        or len(header_bytes) > MAX_BACKUP_HEADER_BYTES
    ):
        raise EncryptedBackupError("backup_header_size_invalid")
    return canonical_json(
        {
            "header_sha256": hashlib.sha256(header_bytes).hexdigest(),
            "record": dict(record),
        }
    )


def _envelope_aad(
    context: BackupContainerContextV1, header: BackupContainerHeaderV1
) -> bytes:
    return canonical_json(
        {
            "stable_context_binding": context.binding_payload(),
            "visible_header": header.metadata_payload(),
        }
    )


def _derive_backup_wrapping_key(
    dmk: LoadedDataMasterKey,
    *,
    context: BackupContainerContextV1,
    container_id: str,
    backup_key_id: str,
) -> bytes:
    derived = derive_domain_separated_key(
        dmk,
        purpose=BACKUP_KEY_WRAP_PURPOSE,
        derivation_version=BACKUP_KEY_KDF_VERSION,
        context={
            "backup_key_id": backup_key_id,
            "container_id": container_id,
            "database_context_id": context.database_context_id,
            "installation_id": context.installation_id,
        },
    )
    return derived.key_material


def _validate_context(context: BackupContainerContextV1) -> None:
    if not isinstance(context, BackupContainerContextV1):
        raise EncryptedBackupError("backup_context_invalid")
    if (
        type(context.context_version) is not int
        or context.context_version != ENCRYPTED_BACKUP_CONTEXT_VERSION
    ):
        raise EncryptedBackupError("backup_context_version_unsupported")
    _validate_uuid(context.installation_id, "backup_installation_id_invalid")
    _validate_uuid(
        context.database_context_id, "backup_database_context_id_invalid"
    )
    for value in (
        context.app_version,
        context.sqlite_version,
        context.sqlcipher_version,
    ):
        if not isinstance(value, str) or not _VERSION_PATTERN.fullmatch(value):
            raise EncryptedBackupError("backup_context_version_value_invalid")


def _validate_envelope(
    envelope: BackupKeyEnvelopeV1, *, require_ciphertext: bool = True
) -> None:
    if not isinstance(envelope, BackupKeyEnvelopeV1):
        raise EncryptedBackupError("backup_key_envelope_invalid")
    if (
        type(envelope.envelope_version) is not int
        or envelope.envelope_version != BACKUP_KEY_ENVELOPE_VERSION
    ):
        raise EncryptedBackupError("backup_key_envelope_version_unsupported")
    _validate_uuid(envelope.backup_key_id, "backup_key_id_invalid")
    _validate_uuid(envelope.wrapping_dmk_key_id, "backup_dmk_key_id_invalid")
    _require_positive_int(
        envelope.wrapping_dmk_generation,
        "backup_dmk_generation_invalid",
    )
    if envelope.wrapping_algorithm != BACKUP_KEY_WRAP_ALGORITHM:
        raise EncryptedBackupError("backup_key_envelope_algorithm_unsupported")
    if (
        envelope.kdf_algorithm != BACKUP_KEY_KDF_ALGORITHM
        or type(envelope.kdf_version) is not int
        or envelope.kdf_version != BACKUP_KEY_KDF_VERSION
        or envelope.key_purpose != BACKUP_KEY_WRAP_PURPOSE
    ):
        raise EncryptedBackupError("backup_key_envelope_kdf_unsupported")
    if len(envelope.nonce) != BACKUP_KEY_NONCE_BYTES:
        raise EncryptedBackupError("backup_key_nonce_invalid")
    if require_ciphertext and len(envelope.ciphertext) != BACKUP_KEY_BYTES + 16:
        raise EncryptedBackupError("backup_key_ciphertext_invalid")
    if (
        not require_ciphertext
        and envelope.ciphertext
        and len(envelope.ciphertext) != BACKUP_KEY_BYTES + 16
    ):
        raise EncryptedBackupError("backup_key_ciphertext_invalid")


def _validate_header(
    header: BackupContainerHeaderV1, *, require_ciphertext: bool = True
) -> None:
    if not isinstance(header, BackupContainerHeaderV1):
        raise EncryptedBackupError("backup_header_invalid")
    if header.container_format != ENCRYPTED_BACKUP_FORMAT:
        raise EncryptedBackupError("backup_container_format_unsupported")
    if (
        type(header.container_version) is not int
        or header.container_version != ENCRYPTED_BACKUP_VERSION
    ):
        raise EncryptedBackupError("backup_container_version_unsupported")
    if (
        type(header.header_version) is not int
        or header.header_version != ENCRYPTED_BACKUP_HEADER_VERSION
    ):
        raise EncryptedBackupError("backup_header_version_unsupported")
    if header.stream_algorithm != BACKUP_STREAM_ALGORITHM:
        raise EncryptedBackupError("backup_stream_algorithm_unsupported")
    _validate_uuid(header.container_id, "backup_container_id_invalid")
    _validate_chunk_size(header.chunk_size)
    if not isinstance(header.stream_header, bytes) or len(header.stream_header) != 24:
        raise EncryptedBackupError("backup_stream_header_invalid")
    _validate_envelope(header.envelope, require_ciphertext=require_ciphertext)


def _validate_manifest_entry(
    entry: BackupManifestEntryV1, *, chunk_size: int | None = None
) -> None:
    if not isinstance(entry, BackupManifestEntryV1):
        raise EncryptedBackupError("backup_manifest_entry_invalid")
    _validate_uuid(entry.entry_id, "backup_entry_id_invalid")
    if not isinstance(entry.role, BackupEntryRole):
        raise EncryptedBackupError("backup_entry_role_invalid")
    if not isinstance(entry.restore_name, str) or not entry.restore_name:
        raise EncryptedBackupError("backup_restore_name_invalid")
    if (
        "/" in entry.restore_name
        or "\\" in entry.restore_name
        or "\x00" in entry.restore_name
        or entry.restore_name in {".", ".."}
    ):
        raise EncryptedBackupError("backup_restore_name_invalid")
    if entry.role is BackupEntryRole.SQLCIPHER_DATABASE:
        if entry.restore_name != "database.sqlcipher":
            raise EncryptedBackupError("backup_restore_name_invalid")
    elif (
        not (match := _RESTORE_DOCUMENT_PATTERN.fullmatch(entry.restore_name))
        or match.group(1) != entry.entry_id
    ):
        raise EncryptedBackupError("backup_restore_name_invalid")
    _require_nonnegative_int(
        entry.plaintext_size, "backup_entry_size_invalid"
    )
    if entry.plaintext_size > MAX_BACKUP_ENTRY_BYTES:
        raise EncryptedBackupError("backup_entry_size_invalid")
    if not isinstance(entry.sha256, str) or not _SHA256_PATTERN.fullmatch(
        entry.sha256
    ):
        raise EncryptedBackupError("backup_entry_hash_invalid")
    _require_positive_int(entry.chunk_count, "backup_chunk_count_invalid")
    if chunk_size is not None:
        _validate_chunk_size(chunk_size)
        expected = max(
            1,
            (entry.plaintext_size + chunk_size - 1) // chunk_size,
        )
        if entry.chunk_count != expected:
            raise EncryptedBackupError("backup_chunk_count_invalid")


def _validate_manifest(manifest: EncryptedBackupManifestV1) -> None:
    if not isinstance(manifest, EncryptedBackupManifestV1):
        raise EncryptedBackupError("backup_manifest_invalid")
    if (
        type(manifest.manifest_version) is not int
        or manifest.manifest_version != ENCRYPTED_BACKUP_MANIFEST_VERSION
    ):
        raise EncryptedBackupError("backup_manifest_version_unsupported")
    _validate_uuid(manifest.container_id, "backup_container_id_invalid")
    if not isinstance(manifest.created_at, str) or not _UTC_PATTERN.fullmatch(
        manifest.created_at
    ):
        raise EncryptedBackupError("backup_created_at_invalid")
    try:
        parsed_created_at = datetime.strptime(
            manifest.created_at, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        raise EncryptedBackupError("backup_created_at_invalid") from None
    if format_utc(parsed_created_at) != manifest.created_at:
        raise EncryptedBackupError("backup_created_at_invalid")
    _validate_context(manifest.context)
    _validate_chunk_size(manifest.chunk_size)
    if (
        not isinstance(manifest.entries, tuple)
        or len(manifest.entries) < 2
        or len(manifest.entries) > MAX_BACKUP_ENTRIES
    ):
        raise EncryptedBackupError("backup_manifest_entry_count_invalid")
    for entry in manifest.entries:
        _validate_manifest_entry(entry, chunk_size=manifest.chunk_size)
    database_entries = [
        entry
        for entry in manifest.entries
        if entry.role is BackupEntryRole.SQLCIPHER_DATABASE
    ]
    if len(database_entries) != 1 or manifest.entries[0] is not database_entries[0]:
        raise EncryptedBackupError("backup_database_entry_invalid")
    document_entries = manifest.entries[1:]
    if any(
        entry.role is not BackupEntryRole.MANAGED_DOCUMENT
        for entry in document_entries
    ):
        raise EncryptedBackupError("backup_entry_role_invalid")
    if tuple(sorted(document_entries, key=lambda item: item.entry_id)) != document_entries:
        raise EncryptedBackupError("backup_manifest_order_invalid")
    ids = [entry.entry_id for entry in manifest.entries]
    names = [entry.restore_name for entry in manifest.entries]
    if len(set(ids)) != len(ids) or len(set(names)) != len(names):
        raise EncryptedBackupError("backup_manifest_duplicate_entry")
    _require_nonnegative_int(
        manifest.total_plaintext_size,
        "backup_manifest_total_size_invalid",
    )
    if (
        manifest.total_plaintext_size > MAX_BACKUP_TOTAL_BYTES
        or manifest.total_plaintext_size
        != sum(entry.plaintext_size for entry in manifest.entries)
    ):
        raise EncryptedBackupError("backup_manifest_total_size_invalid")


def _validate_dmk(dmk: LoadedDataMasterKey) -> None:
    if not isinstance(dmk, LoadedDataMasterKey):
        raise EncryptedBackupError("backup_dmk_invalid")
    _validate_uuid(dmk.key_id, "backup_dmk_key_id_invalid")
    _require_positive_int(dmk.generation, "backup_dmk_generation_invalid")
    if not isinstance(dmk.key_material, bytes) or len(dmk.key_material) != 32:
        raise EncryptedBackupError("backup_dmk_length_invalid")


def _validate_chunk_size(value: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < MIN_BACKUP_CHUNK_SIZE
        or value > MAX_BACKUP_CHUNK_SIZE
    ):
        raise EncryptedBackupError("backup_chunk_size_invalid")


def _validate_uuid(value: object, code: str) -> None:
    try:
        validate_uuid4(value)
    except Exception:
        raise EncryptedBackupError(code) from None


def _require_positive_int(value: object, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EncryptedBackupError(code)


def _require_nonnegative_int(value: object, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EncryptedBackupError(code)
