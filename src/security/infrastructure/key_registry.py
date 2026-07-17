"""Offline registry containing public Ed25519 keys only."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timezone
import re

from ..domain import SupportPublicKey


_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


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
        return tuple(sorted(self._records))


# No production key has been approved. Rotation/revocation requires an app update.
DEFAULT_SUPPORT_KEY_REGISTRY = PublicKeyRegistry()
