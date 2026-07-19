"""Strict versioned offline registry containing public Ed25519 keys only."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import base64
import binascii
import hashlib
import re
from typing import Any, Mapping

from ..domain import SupportPublicKey, SupportPublicKeyStatus
from .product_support_keys import PRODUCT_SUPPORT_KEY_REGISTRY


_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REGISTRY_FIELDS = {"format_version", "keys"}
_KEY_FIELDS = {
    "key_id",
    "algorithm",
    "public_key",
    "status",
    "not_before",
    "not_after",
    "revoked_at",
    "fingerprint_sha256",
}
SUPPORT_KEY_REGISTRY_FORMAT_VERSION = 1


class PublicKeyRegistry:
    def __init__(self, keys: Iterable[SupportPublicKey] = ()) -> None:
        records: dict[str, SupportPublicKey] = {}
        for key in keys:
            if not _KEY_ID_PATTERN.fullmatch(key.key_id):
                raise ValueError("invalid_support_key_id")
            if not isinstance(key.public_key, bytes) or len(key.public_key) != 32:
                raise ValueError("invalid_support_public_key")
            if (
                key.not_before.tzinfo is None
                or key.not_before.utcoffset() is None
                or key.not_after.tzinfo is None
                or key.not_after.utcoffset() is None
            ):
                raise ValueError("support_key_time_must_be_aware")
            if key.not_after.astimezone(timezone.utc) <= key.not_before.astimezone(timezone.utc):
                raise ValueError("invalid_support_key_lifetime")
            if key.key_id in records:
                raise ValueError("duplicate_support_key_id")
            records[key.key_id] = key
        self._records = records

    def get(self, key_id: str) -> SupportPublicKey | None:
        return self._records.get(key_id)

    def key_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                key_id
                for key_id, key in self._records.items()
                if key.status in {
                    SupportPublicKeyStatus.ACTIVE,
                    SupportPublicKeyStatus.RETIRING,
                }
            )
        )

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, Any]) -> "PublicKeyRegistry":
        if not isinstance(manifest, Mapping) or set(manifest) != _REGISTRY_FIELDS:
            raise ValueError("invalid_support_key_registry_fields")
        if (
            type(manifest["format_version"]) is not int
            or manifest["format_version"] != SUPPORT_KEY_REGISTRY_FORMAT_VERSION
        ):
            raise ValueError("unsupported_support_key_registry_version")
        records = manifest["keys"]
        if not isinstance(records, (tuple, list)):
            raise ValueError("invalid_support_key_registry_records")
        return cls(_key_from_manifest(record) for record in records)


def _key_from_manifest(record: object) -> SupportPublicKey:
    if not isinstance(record, Mapping) or set(record) != _KEY_FIELDS:
        raise ValueError("invalid_support_key_record_fields")
    if record["algorithm"] != "Ed25519":
        raise ValueError("invalid_support_key_algorithm")
    key_id = record["key_id"]
    if not isinstance(key_id, str) or not _KEY_ID_PATTERN.fullmatch(key_id):
        raise ValueError("invalid_support_key_id")
    try:
        status = SupportPublicKeyStatus(record["status"])
    except (TypeError, ValueError) as error:
        raise ValueError("invalid_support_key_status") from error
    public_key = _decode_public_key(record["public_key"])
    fingerprint = record["fingerprint_sha256"]
    if (
        not isinstance(fingerprint, str)
        or not _FINGERPRINT_PATTERN.fullmatch(fingerprint)
        or not hashlib.sha256(public_key).hexdigest() == fingerprint
    ):
        raise ValueError("invalid_support_key_fingerprint")
    revoked_at = record["revoked_at"]
    if revoked_at is not None:
        _parse_registry_time(revoked_at)
        if status is not SupportPublicKeyStatus.REVOKED:
            raise ValueError("support_key_revocation_status_mismatch")
    return SupportPublicKey(
        key_id=key_id,
        public_key=public_key,
        status=status,
        not_before=_parse_registry_time(record["not_before"]),
        not_after=_parse_registry_time(record["not_after"]),
    )


def _decode_public_key(value: object) -> bytes:
    if not isinstance(value, str) or len(value) != 43 or "=" in value:
        raise ValueError("invalid_support_public_key_encoding")
    try:
        decoded = base64.b64decode(value + "=", altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("invalid_support_public_key_encoding") from error
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if len(decoded) != 32 or canonical != value:
        raise ValueError("invalid_support_public_key_encoding")
    return decoded


def _parse_registry_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid_support_key_time")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ValueError("invalid_support_key_time") from error
    return parsed.replace(tzinfo=timezone.utc)


# No production key has been approved. Rotation/revocation requires an app update.
DEFAULT_SUPPORT_KEY_REGISTRY = PublicKeyRegistry.from_manifest(
    PRODUCT_SUPPORT_KEY_REGISTRY
)
