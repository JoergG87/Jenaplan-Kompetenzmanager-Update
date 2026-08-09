"""Strict cryptographic values for encrypted document containers.

This module defines the document-specific format and key hierarchy used by the
isolated prototype and the internally gated Final-V3 document runtime. It is
not imported by product document, backup, restore, startup, login, or UI code.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .data_keys import LoadedDataMasterKey
from .database_keys import derive_domain_separated_key
from .domain import validate_uuid4


ENCRYPTED_DOCUMENT_MAGIC = b"JKMEDC01"
ENCRYPTED_DOCUMENT_FORMAT = "jenaplan-encrypted-document"
ENCRYPTED_DOCUMENT_VERSION = 1
ENCRYPTED_DOCUMENT_HEADER_VERSION = 1
ENCRYPTED_DOCUMENT_MANIFEST_VERSION = 1
DOCUMENT_CONTEXT_VERSION = 1
DOCUMENT_KEY_ENVELOPE_VERSION = 1
DOCUMENT_KEY_BYTES = 32
DOCUMENT_KEY_NONCE_BYTES = 12
DOCUMENT_KEY_WRAP_PURPOSE = (
    "jenaplan-kompetenzmanager/document-wrapping-key/v1"
)
DOCUMENT_KEY_WRAP_ALGORITHM = "aes-256-gcm"
DOCUMENT_KEY_KDF_ALGORITHM = "hkdf-sha256"
DOCUMENT_KEY_KDF_VERSION = 1
DOCUMENT_STREAM_ALGORITHM = "libsodium-secretstream-xchacha20poly1305"
DOCUMENT_RECORD_AAD_DOMAIN = "jenaplan-document-record-aad/v1"
DOCUMENT_ENVELOPE_AAD_DOMAIN = "jenaplan-document-envelope-aad/v1"
DEFAULT_DOCUMENT_CHUNK_SIZE = 1024 * 1024
MIN_DOCUMENT_CHUNK_SIZE = 64
MAX_DOCUMENT_CHUNK_SIZE = 8 * 1024 * 1024
MAX_DOCUMENT_HEADER_BYTES = 64 * 1024
MAX_DOCUMENT_MANIFEST_BYTES = 256 * 1024
MAX_DOCUMENT_BYTES = 1 << 34
ALLOWED_DOCUMENT_MIME_TYPES = frozenset(
    {
        "application/octet-stream",
        "application/pdf",
        "image/jpeg",
        "image/png",
        "text/plain",
    }
)

_UTC_PATTERN = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_SHA256_PATTERN = re.compile(r"\A[0-9a-f]{64}\Z")
_VERSION_PATTERN = re.compile(r"\A[ -~]{1,160}\Z")
_MIME_PATTERN = re.compile(r"\A[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*\Z")


class EncryptedDocumentError(RuntimeError):
    """Sanitized fail-closed error which never embeds paths or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DocumentContainerContextV1:
    installation_id: str
    database_context_id: str
    document_id: str
    document_generation: int
    app_format_version: str
    context_version: int = DOCUMENT_CONTEXT_VERSION

    def binding_payload(self) -> dict[str, object]:
        _validate_context(self)
        return {
            "context_version": self.context_version,
            "database_context_id": self.database_context_id,
            "document_generation": self.document_generation,
            "document_id": self.document_id,
            "installation_id": self.installation_id,
        }

    def to_payload(self) -> dict[str, object]:
        return {
            **self.binding_payload(),
            "app_format_version": self.app_format_version,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "DocumentContainerContextV1":
        required = {
            "app_format_version",
            "context_version",
            "database_context_id",
            "document_generation",
            "document_id",
            "installation_id",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedDocumentError("document_context_fields_invalid")
        try:
            value = cls(
                installation_id=payload["installation_id"],
                database_context_id=payload["database_context_id"],
                document_id=payload["document_id"],
                document_generation=payload["document_generation"],
                app_format_version=payload["app_format_version"],
                context_version=payload["context_version"],
            )
            _validate_context(value)
            return value
        except EncryptedDocumentError:
            raise
        except Exception:
            raise EncryptedDocumentError(
                "document_context_fields_invalid"
            ) from None


@dataclass(frozen=True)
class DocumentKeyEnvelopeV1:
    document_key_id: str
    document_key_generation: int
    rewrap_revision: int
    wrapping_dmk_key_id: str
    wrapping_dmk_generation: int
    nonce: bytes
    ciphertext: bytes = field(repr=False)
    envelope_version: int = DOCUMENT_KEY_ENVELOPE_VERSION
    wrapping_algorithm: str = DOCUMENT_KEY_WRAP_ALGORITHM
    kdf_algorithm: str = DOCUMENT_KEY_KDF_ALGORITHM
    kdf_version: int = DOCUMENT_KEY_KDF_VERSION
    key_purpose: str = DOCUMENT_KEY_WRAP_PURPOSE

    def metadata_payload(self) -> dict[str, object]:
        _validate_envelope(self, require_ciphertext=False)
        return {
            "document_key_generation": self.document_key_generation,
            "document_key_id": self.document_key_id,
            "envelope_version": self.envelope_version,
            "kdf_algorithm": self.kdf_algorithm,
            "kdf_version": self.kdf_version,
            "key_purpose": self.key_purpose,
            "nonce": base64url_encode(self.nonce),
            "rewrap_revision": self.rewrap_revision,
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
    def from_payload(cls, payload: object) -> "DocumentKeyEnvelopeV1":
        required = {
            "ciphertext",
            "document_key_generation",
            "document_key_id",
            "envelope_version",
            "kdf_algorithm",
            "kdf_version",
            "key_purpose",
            "nonce",
            "rewrap_revision",
            "wrapping_algorithm",
            "wrapping_dmk_generation",
            "wrapping_dmk_key_id",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedDocumentError("document_envelope_fields_invalid")
        try:
            value = cls(
                document_key_id=payload["document_key_id"],
                document_key_generation=payload["document_key_generation"],
                rewrap_revision=payload["rewrap_revision"],
                wrapping_dmk_key_id=payload["wrapping_dmk_key_id"],
                wrapping_dmk_generation=payload["wrapping_dmk_generation"],
                nonce=base64url_decode(payload["nonce"]),
                ciphertext=base64url_decode(payload["ciphertext"]),
                envelope_version=payload["envelope_version"],
                wrapping_algorithm=payload["wrapping_algorithm"],
                kdf_algorithm=payload["kdf_algorithm"],
                kdf_version=payload["kdf_version"],
                key_purpose=payload["key_purpose"],
            )
            _validate_envelope(value)
            return value
        except EncryptedDocumentError:
            raise
        except Exception:
            raise EncryptedDocumentError(
                "document_envelope_fields_invalid"
            ) from None


@dataclass(frozen=True)
class DocumentContainerHeaderV1:
    container_id: str
    chunk_size: int
    stream_header: bytes
    document_key_id: str
    document_key_generation: int
    envelope: DocumentKeyEnvelopeV1
    container_format: str = ENCRYPTED_DOCUMENT_FORMAT
    container_version: int = ENCRYPTED_DOCUMENT_VERSION
    header_version: int = ENCRYPTED_DOCUMENT_HEADER_VERSION
    stream_algorithm: str = DOCUMENT_STREAM_ALGORITHM

    def payload_binding_payload(self) -> dict[str, object]:
        _validate_header(self, require_ciphertext=False)
        return {
            "chunk_size": self.chunk_size,
            "container_format": self.container_format,
            "container_id": self.container_id,
            "container_version": self.container_version,
            "document_key_generation": self.document_key_generation,
            "document_key_id": self.document_key_id,
            "header_version": self.header_version,
            "stream_algorithm": self.stream_algorithm,
            "stream_header": base64url_encode(self.stream_header),
        }

    def to_payload(self) -> dict[str, object]:
        _validate_header(self)
        return {
            **self.payload_binding_payload(),
            "envelope": self.envelope.to_payload(),
        }

    def to_bytes(self) -> bytes:
        value = canonical_json(self.to_payload())
        if len(value) > MAX_DOCUMENT_HEADER_BYTES:
            raise EncryptedDocumentError("document_header_size_invalid")
        return value

    def payload_binding_bytes(self) -> bytes:
        return canonical_json(self.payload_binding_payload())

    @classmethod
    def from_bytes(cls, value: bytes) -> "DocumentContainerHeaderV1":
        if not isinstance(value, bytes) or not value or len(value) > MAX_DOCUMENT_HEADER_BYTES:
            raise EncryptedDocumentError("document_header_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EncryptedDocumentError("document_header_format_invalid") from None
        required = {
            "chunk_size",
            "container_format",
            "container_id",
            "container_version",
            "document_key_generation",
            "document_key_id",
            "envelope",
            "header_version",
            "stream_algorithm",
            "stream_header",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedDocumentError("document_header_fields_invalid")
        try:
            result = cls(
                container_id=payload["container_id"],
                chunk_size=payload["chunk_size"],
                stream_header=base64url_decode(payload["stream_header"]),
                document_key_id=payload["document_key_id"],
                document_key_generation=payload["document_key_generation"],
                envelope=DocumentKeyEnvelopeV1.from_payload(payload["envelope"]),
                container_format=payload["container_format"],
                container_version=payload["container_version"],
                header_version=payload["header_version"],
                stream_algorithm=payload["stream_algorithm"],
            )
            _validate_header(result)
        except EncryptedDocumentError:
            raise
        except Exception:
            raise EncryptedDocumentError("document_header_fields_invalid") from None
        if result.to_bytes() != value:
            raise EncryptedDocumentError("document_header_not_canonical")
        return result


@dataclass(frozen=True)
class EncryptedDocumentManifestV1:
    context: DocumentContainerContextV1
    storage_id: str
    container_id: str
    document_key_id: str
    document_key_generation: int
    original_filename: str
    mime_type: str
    plaintext_size: int
    plaintext_sha256: str
    chunk_size: int
    chunk_count: int
    created_at: str
    manifest_version: int = ENCRYPTED_DOCUMENT_MANIFEST_VERSION

    def to_payload(self) -> dict[str, object]:
        _validate_manifest(self)
        return {
            "chunk_count": self.chunk_count,
            "chunk_size": self.chunk_size,
            "container_id": self.container_id,
            "context": self.context.to_payload(),
            "created_at": self.created_at,
            "document_key_generation": self.document_key_generation,
            "document_key_id": self.document_key_id,
            "manifest_version": self.manifest_version,
            "mime_type": self.mime_type,
            "original_filename": self.original_filename,
            "plaintext_sha256": self.plaintext_sha256,
            "plaintext_size": self.plaintext_size,
            "storage_id": self.storage_id,
        }

    def to_bytes(self) -> bytes:
        value = canonical_json(self.to_payload())
        if len(value) > MAX_DOCUMENT_MANIFEST_BYTES:
            raise EncryptedDocumentError("document_manifest_size_invalid")
        return value

    @classmethod
    def from_bytes(cls, value: bytes) -> "EncryptedDocumentManifestV1":
        if not isinstance(value, bytes) or not value or len(value) > MAX_DOCUMENT_MANIFEST_BYTES:
            raise EncryptedDocumentError("document_manifest_size_invalid")
        try:
            payload = json.loads(value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EncryptedDocumentError("document_manifest_format_invalid") from None
        required = {
            "chunk_count",
            "chunk_size",
            "container_id",
            "context",
            "created_at",
            "document_key_generation",
            "document_key_id",
            "manifest_version",
            "mime_type",
            "original_filename",
            "plaintext_sha256",
            "plaintext_size",
            "storage_id",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise EncryptedDocumentError("document_manifest_fields_invalid")
        try:
            result = cls(
                context=DocumentContainerContextV1.from_payload(payload["context"]),
                storage_id=payload["storage_id"],
                container_id=payload["container_id"],
                document_key_id=payload["document_key_id"],
                document_key_generation=payload["document_key_generation"],
                original_filename=payload["original_filename"],
                mime_type=payload["mime_type"],
                plaintext_size=payload["plaintext_size"],
                plaintext_sha256=payload["plaintext_sha256"],
                chunk_size=payload["chunk_size"],
                chunk_count=payload["chunk_count"],
                created_at=payload["created_at"],
                manifest_version=payload["manifest_version"],
            )
            _validate_manifest(result)
        except EncryptedDocumentError:
            raise
        except Exception:
            raise EncryptedDocumentError("document_manifest_fields_invalid") from None
        if result.to_bytes() != value:
            raise EncryptedDocumentError("document_manifest_not_canonical")
        return result


def build_document_key_envelope(
    dmk: LoadedDataMasterKey,
    *,
    context: DocumentContainerContextV1,
    header_without_envelope: DocumentContainerHeaderV1,
    document_key: bytes,
    nonce: bytes,
    rewrap_revision: int,
) -> DocumentKeyEnvelopeV1:
    _validate_dmk(dmk)
    _validate_context(context)
    _validate_header(header_without_envelope, require_ciphertext=False)
    if not isinstance(document_key, bytes) or len(document_key) != DOCUMENT_KEY_BYTES:
        raise EncryptedDocumentError("document_key_length_invalid")
    if not isinstance(nonce, bytes) or len(nonce) != DOCUMENT_KEY_NONCE_BYTES:
        raise EncryptedDocumentError("document_key_nonce_invalid")
    _positive(rewrap_revision, "document_rewrap_revision_invalid")
    wrapping_key = _derive_document_wrapping_key(
        dmk,
        context=context,
        header=header_without_envelope,
        rewrap_revision=rewrap_revision,
    )
    metadata = DocumentKeyEnvelopeV1(
        document_key_id=header_without_envelope.document_key_id,
        document_key_generation=header_without_envelope.document_key_generation,
        rewrap_revision=rewrap_revision,
        wrapping_dmk_key_id=dmk.key_id,
        wrapping_dmk_generation=dmk.generation,
        nonce=nonce,
        ciphertext=b"",
    )
    ciphertext = AESGCM(wrapping_key).encrypt(
        nonce,
        document_key,
        envelope_aad(context, header_without_envelope, metadata),
    )
    return DocumentKeyEnvelopeV1(**{**metadata.__dict__, "ciphertext": ciphertext})


def open_document_key_envelope(
    dmk: LoadedDataMasterKey,
    *,
    context: DocumentContainerContextV1,
    header: DocumentContainerHeaderV1,
) -> bytes:
    _validate_dmk(dmk)
    _validate_context(context)
    _validate_header(header)
    envelope = header.envelope
    if (
        envelope.wrapping_dmk_key_id != dmk.key_id
        or envelope.wrapping_dmk_generation != dmk.generation
        or envelope.document_key_id != header.document_key_id
        or envelope.document_key_generation != header.document_key_generation
    ):
        raise EncryptedDocumentError("document_envelope_context_mismatch")
    wrapping_key = _derive_document_wrapping_key(
        dmk,
        context=context,
        header=header,
        rewrap_revision=envelope.rewrap_revision,
    )
    try:
        key = AESGCM(wrapping_key).decrypt(
            envelope.nonce,
            envelope.ciphertext,
            envelope_aad(context, header, envelope),
        )
    except InvalidTag:
        raise EncryptedDocumentError("document_envelope_authentication_failed") from None
    if len(key) != DOCUMENT_KEY_BYTES:
        raise EncryptedDocumentError("document_key_length_invalid")
    return key


def envelope_aad(
    context: DocumentContainerContextV1,
    header: DocumentContainerHeaderV1,
    envelope: DocumentKeyEnvelopeV1,
) -> bytes:
    return canonical_json(
        {
            "context": context.binding_payload(),
            "domain": DOCUMENT_ENVELOPE_AAD_DOMAIN,
            "envelope": envelope.metadata_payload(),
            "payload_binding": header.payload_binding_payload(),
        }
    )


def manifest_record_aad(
    header: DocumentContainerHeaderV1,
    context: DocumentContainerContextV1,
    plaintext_size: int,
) -> bytes:
    return _record_aad(
        header,
        context,
        {
            "plaintext_size": plaintext_size,
            "record_ordinal": 0,
            "record_type": "manifest",
        },
    )


def chunk_record_aad(
    header: DocumentContainerHeaderV1,
    context: DocumentContainerContextV1,
    *,
    manifest_sha256: str,
    record_ordinal: int,
    chunk_index: int,
    plaintext_size: int,
) -> bytes:
    return _record_aad(
        header,
        context,
        {
            "chunk_index": chunk_index,
            "manifest_sha256": manifest_sha256,
            "plaintext_size": plaintext_size,
            "record_ordinal": record_ordinal,
            "record_type": "document_chunk",
        },
    )


def final_record_aad(
    header: DocumentContainerHeaderV1,
    context: DocumentContainerContextV1,
    *,
    manifest_sha256: str,
    record_ordinal: int,
    chunk_count: int,
    plaintext_size: int,
) -> bytes:
    return _record_aad(
        header,
        context,
        {
            "chunk_count": chunk_count,
            "manifest_sha256": manifest_sha256,
            "plaintext_size": plaintext_size,
            "record_ordinal": record_ordinal,
            "record_type": "final",
        },
    )


def expected_chunk_size(
    manifest: EncryptedDocumentManifestV1, chunk_index: int
) -> int:
    if chunk_index < 0 or chunk_index >= manifest.chunk_count:
        raise EncryptedDocumentError("document_chunk_index_invalid")
    if manifest.plaintext_size == 0:
        return 0
    if chunk_index < manifest.chunk_count - 1:
        return manifest.chunk_size
    return manifest.plaintext_size - manifest.chunk_size * (manifest.chunk_count - 1)


def validate_document_chunk_size(value: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < MIN_DOCUMENT_CHUNK_SIZE
        or value > MAX_DOCUMENT_CHUNK_SIZE
    ):
        raise EncryptedDocumentError("document_chunk_size_invalid")


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError):
        raise EncryptedDocumentError("document_canonical_json_invalid") from None


def base64url_encode(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise EncryptedDocumentError("document_base64_invalid")
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def base64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise EncryptedDocumentError("document_base64_invalid")
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, ValueError):
        raise EncryptedDocumentError("document_base64_invalid") from None
    if base64url_encode(decoded) != value:
        raise EncryptedDocumentError("document_base64_invalid")
    return decoded


def format_utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise EncryptedDocumentError("document_created_at_invalid")
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _record_aad(
    header: DocumentContainerHeaderV1,
    context: DocumentContainerContextV1,
    record: Mapping[str, object],
) -> bytes:
    return canonical_json(
        {
            "context": context.binding_payload(),
            "domain": DOCUMENT_RECORD_AAD_DOMAIN,
            "payload_binding_sha256": hashlib.sha256(
                header.payload_binding_bytes()
            ).hexdigest(),
            "record": dict(record),
        }
    )


def _derive_document_wrapping_key(
    dmk: LoadedDataMasterKey,
    *,
    context: DocumentContainerContextV1,
    header: DocumentContainerHeaderV1,
    rewrap_revision: int,
) -> bytes:
    derived = derive_domain_separated_key(
        dmk,
        purpose=DOCUMENT_KEY_WRAP_PURPOSE,
        derivation_version=DOCUMENT_KEY_KDF_VERSION,
        context={
            "container_id": header.container_id,
            "database_context_id": context.database_context_id,
            "document_generation": context.document_generation,
            "document_id": context.document_id,
            "document_key_generation": header.document_key_generation,
            "document_key_id": header.document_key_id,
            "installation_id": context.installation_id,
            "rewrap_revision": rewrap_revision,
        },
    )
    return derived.key_material


def _validate_context(value: DocumentContainerContextV1) -> None:
    if not isinstance(value, DocumentContainerContextV1):
        raise EncryptedDocumentError("document_context_invalid")
    if (
        type(value.context_version) is not int
        or value.context_version != DOCUMENT_CONTEXT_VERSION
    ):
        raise EncryptedDocumentError("document_context_version_unsupported")
    for identifier, code in (
        (value.installation_id, "document_installation_id_invalid"),
        (value.database_context_id, "document_database_context_id_invalid"),
        (value.document_id, "document_id_invalid"),
    ):
        _uuid(identifier, code)
    _positive(value.document_generation, "document_generation_invalid")
    if not isinstance(value.app_format_version, str) or not _VERSION_PATTERN.fullmatch(
        value.app_format_version
    ):
        raise EncryptedDocumentError("document_app_format_version_invalid")


def _validate_envelope(
    value: DocumentKeyEnvelopeV1, *, require_ciphertext: bool = True
) -> None:
    if not isinstance(value, DocumentKeyEnvelopeV1):
        raise EncryptedDocumentError("document_envelope_invalid")
    if (
        type(value.envelope_version) is not int
        or value.envelope_version != DOCUMENT_KEY_ENVELOPE_VERSION
    ):
        raise EncryptedDocumentError("document_envelope_version_unsupported")
    _uuid(value.document_key_id, "document_key_id_invalid")
    _uuid(value.wrapping_dmk_key_id, "document_dmk_key_id_invalid")
    _positive(value.document_key_generation, "document_key_generation_invalid")
    _positive(value.rewrap_revision, "document_rewrap_revision_invalid")
    _positive(value.wrapping_dmk_generation, "document_dmk_generation_invalid")
    if (
        value.wrapping_algorithm != DOCUMENT_KEY_WRAP_ALGORITHM
        or value.kdf_algorithm != DOCUMENT_KEY_KDF_ALGORITHM
        or type(value.kdf_version) is not int
        or value.kdf_version != DOCUMENT_KEY_KDF_VERSION
        or value.key_purpose != DOCUMENT_KEY_WRAP_PURPOSE
    ):
        raise EncryptedDocumentError("document_envelope_algorithm_unsupported")
    if len(value.nonce) != DOCUMENT_KEY_NONCE_BYTES:
        raise EncryptedDocumentError("document_key_nonce_invalid")
    if require_ciphertext and len(value.ciphertext) != DOCUMENT_KEY_BYTES + 16:
        raise EncryptedDocumentError("document_key_ciphertext_invalid")
    if not require_ciphertext and value.ciphertext and len(value.ciphertext) != DOCUMENT_KEY_BYTES + 16:
        raise EncryptedDocumentError("document_key_ciphertext_invalid")


def _validate_header(
    value: DocumentContainerHeaderV1, *, require_ciphertext: bool = True
) -> None:
    if not isinstance(value, DocumentContainerHeaderV1):
        raise EncryptedDocumentError("document_header_invalid")
    if value.container_format != ENCRYPTED_DOCUMENT_FORMAT:
        raise EncryptedDocumentError("document_container_format_unsupported")
    if (
        type(value.container_version) is not int
        or value.container_version != ENCRYPTED_DOCUMENT_VERSION
    ):
        raise EncryptedDocumentError("document_container_version_unsupported")
    if (
        type(value.header_version) is not int
        or value.header_version != ENCRYPTED_DOCUMENT_HEADER_VERSION
    ):
        raise EncryptedDocumentError("document_header_version_unsupported")
    if value.stream_algorithm != DOCUMENT_STREAM_ALGORITHM:
        raise EncryptedDocumentError("document_stream_algorithm_unsupported")
    _uuid(value.container_id, "document_container_id_invalid")
    _uuid(value.document_key_id, "document_key_id_invalid")
    _positive(value.document_key_generation, "document_key_generation_invalid")
    validate_document_chunk_size(value.chunk_size)
    if not isinstance(value.stream_header, bytes) or len(value.stream_header) != 24:
        raise EncryptedDocumentError("document_stream_header_invalid")
    _validate_envelope(value.envelope, require_ciphertext=require_ciphertext)
    if (
        value.document_key_id != value.envelope.document_key_id
        or value.document_key_generation != value.envelope.document_key_generation
    ):
        raise EncryptedDocumentError("document_header_envelope_mismatch")


def _validate_manifest(value: EncryptedDocumentManifestV1) -> None:
    if not isinstance(value, EncryptedDocumentManifestV1):
        raise EncryptedDocumentError("document_manifest_invalid")
    if (
        type(value.manifest_version) is not int
        or value.manifest_version != ENCRYPTED_DOCUMENT_MANIFEST_VERSION
    ):
        raise EncryptedDocumentError("document_manifest_version_unsupported")
    _validate_context(value.context)
    for identifier, code in (
        (value.storage_id, "document_storage_id_invalid"),
        (value.container_id, "document_container_id_invalid"),
        (value.document_key_id, "document_key_id_invalid"),
    ):
        _uuid(identifier, code)
    _positive(value.document_key_generation, "document_key_generation_invalid")
    if (
        not isinstance(value.original_filename, str)
        or not value.original_filename
        or len(value.original_filename) > 255
        or value.original_filename in {".", ".."}
        or "/" in value.original_filename
        or "\\" in value.original_filename
        or "\x00" in value.original_filename
    ):
        raise EncryptedDocumentError("document_original_filename_invalid")
    if (
        not isinstance(value.mime_type, str)
        or not _MIME_PATTERN.fullmatch(value.mime_type)
        or value.mime_type not in ALLOWED_DOCUMENT_MIME_TYPES
    ):
        raise EncryptedDocumentError("document_mime_type_invalid")
    if (
        isinstance(value.plaintext_size, bool)
        or not isinstance(value.plaintext_size, int)
        or value.plaintext_size < 0
        or value.plaintext_size > MAX_DOCUMENT_BYTES
    ):
        raise EncryptedDocumentError("document_plaintext_size_invalid")
    if not isinstance(value.plaintext_sha256, str) or not _SHA256_PATTERN.fullmatch(
        value.plaintext_sha256
    ):
        raise EncryptedDocumentError("document_plaintext_hash_invalid")
    validate_document_chunk_size(value.chunk_size)
    expected_count = max(
        1, (value.plaintext_size + value.chunk_size - 1) // value.chunk_size
    )
    if type(value.chunk_count) is not int or value.chunk_count != expected_count:
        raise EncryptedDocumentError("document_chunk_count_invalid")
    if not isinstance(value.created_at, str) or not _UTC_PATTERN.fullmatch(value.created_at):
        raise EncryptedDocumentError("document_created_at_invalid")
    try:
        parsed = datetime.strptime(value.created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        raise EncryptedDocumentError("document_created_at_invalid") from None
    if format_utc(parsed) != value.created_at:
        raise EncryptedDocumentError("document_created_at_invalid")


def _validate_dmk(value: LoadedDataMasterKey) -> None:
    if not isinstance(value, LoadedDataMasterKey):
        raise EncryptedDocumentError("document_dmk_invalid")
    _uuid(value.key_id, "document_dmk_key_id_invalid")
    _positive(value.generation, "document_dmk_generation_invalid")
    if not isinstance(value.key_material, bytes) or len(value.key_material) != 32:
        raise EncryptedDocumentError("document_dmk_length_invalid")


def _uuid(value: object, code: str) -> None:
    try:
        validate_uuid4(value)
    except Exception:
        raise EncryptedDocumentError(code) from None


def _positive(value: object, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EncryptedDocumentError(code)
