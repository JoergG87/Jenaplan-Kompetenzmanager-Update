"""Atomic file repository for already protected Database-Key envelopes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile

from ..database_keys import (
    DATABASE_KEY_REGISTRY_AUTH_PURPOSE,
    DatabaseKeyEnvelope,
    DatabaseKeyEnvelopeError,
    DerivedDomainKey,
)
from ..domain import validate_uuid4
from ..ports import FilePermissionManager


DATABASE_KEY_ENVELOPE_REGISTRY_VERSION = 1
DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME = "database-key-envelopes-v1.json"
_TEMP_PREFIX = ".database-key-envelope-registry-"
_MAX_REGISTRY_BYTES = 256 * 1024
_REGISTRY_AUTH_ALGORITHM = "hmac-sha256"


class FileDatabaseKeyEnvelopeRepository:
    """Strict single-file registry outside SQLite and the platform secret store."""

    def __init__(self, path: Path, permissions: FilePermissionManager) -> None:
        self.path = Path(path)
        self._permissions = permissions

    def exists(self) -> bool:
        self._require_clean_directory(prepare=False)
        if self.path.is_symlink():
            raise DatabaseKeyEnvelopeError("database_key_envelope_symlink_rejected")
        return self.path.is_file()

    def peek_context(self) -> str:
        """Return untrusted KDF-selection context; callers must authenticate next."""

        self._require_clean_directory(prepare=False)
        raw = self._read_regular_bytes()
        try:
            payload = json.loads(raw.decode("ascii"))
            context_id = payload["database_context_id"]
            validate_uuid4(context_id)
        except Exception:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_invalid"
            ) from None
        return context_id

    def load(
        self, auth_key: DerivedDomainKey
    ) -> tuple[DatabaseKeyEnvelope, ...]:
        self._require_clean_directory(prepare=False)
        if not self.path.exists() and not self.path.is_symlink():
            raise DatabaseKeyEnvelopeError("database_key_envelope_missing")
        raw = self._read_regular_bytes()
        _context_id, _highest_generation, envelopes = self._decode_registry(
            raw, auth_key
        )
        return envelopes

    def highest_generation(self, auth_key: DerivedDomainKey) -> int:
        self._require_clean_directory(prepare=False)
        _context_id, highest_generation, _envelopes = self._decode_registry(
            self._read_regular_bytes(), auth_key
        )
        return highest_generation

    def database_context_id(self, auth_key: DerivedDomainKey) -> str:
        self._require_clean_directory(prepare=False)
        context_id, _highest_generation, _envelopes = self._decode_registry(
            self._read_regular_bytes(), auth_key
        )
        return context_id

    def create(
        self,
        envelopes: tuple[DatabaseKeyEnvelope, ...],
        auth_key: DerivedDomainKey,
    ) -> None:
        self._require_clean_directory(prepare=True)
        if self.path.exists() or self.path.is_symlink():
            raise DatabaseKeyEnvelopeError("database_key_envelope_already_exists")
        context_id, highest_generation = self._registry_identity(envelopes)
        data = self._encode_registry(
            context_id, highest_generation, envelopes, auth_key
        )
        temporary = self._write_temporary(data)
        try:
            try:
                os.link(temporary, self.path)
            except FileExistsError:
                raise DatabaseKeyEnvelopeError(
                    "database_key_envelope_already_exists"
                ) from None
            temporary.unlink()
            self._permissions.secure_file(self.path)
            _fsync_directory(self.path.parent)
            if self._read_regular_bytes() != data:
                raise DatabaseKeyEnvelopeError("database_key_envelope_publish_failed")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def replace(
        self,
        expected: tuple[DatabaseKeyEnvelope, ...],
        replacement: tuple[DatabaseKeyEnvelope, ...],
        auth_key: DerivedDomainKey,
    ) -> None:
        self._require_clean_directory(prepare=False)
        current_data, identity = self._read_with_identity()
        context_id, highest_generation, current = self._decode_registry(
            current_data, auth_key
        )
        if current != expected:
            raise DatabaseKeyEnvelopeError("database_key_envelope_changed")
        for envelope in replacement:
            if envelope.database_context_id != context_id:
                raise DatabaseKeyEnvelopeError("database_key_context_mismatch")
        replacement_high_water = max(
            (envelope.key_generation for envelope in replacement),
            default=highest_generation,
        )
        if replacement_high_water < highest_generation:
            replacement_high_water = highest_generation
        replacement_data = self._encode_registry(
            context_id, replacement_high_water, replacement, auth_key
        )
        temporary = self._write_temporary(replacement_data)
        try:
            current_again, identity_again = self._read_with_identity()
            if current_again != current_data or identity_again != identity:
                raise DatabaseKeyEnvelopeError("database_key_envelope_changed")
            os.replace(temporary, self.path)
            self._permissions.secure_file(self.path)
            _fsync_directory(self.path.parent)
            if self._read_regular_bytes() != replacement_data:
                raise DatabaseKeyEnvelopeError("database_key_envelope_publish_failed")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _require_clean_directory(self, *, prepare: bool) -> None:
        if prepare:
            try:
                self._permissions.prepare_directory(self.path.parent)
            except Exception:
                raise DatabaseKeyEnvelopeError(
                    "database_key_envelope_directory_invalid"
                ) from None
        if self.path.parent.is_symlink() or not self.path.parent.is_dir():
            if not prepare and not self.path.parent.exists():
                return
            raise DatabaseKeyEnvelopeError("database_key_envelope_directory_invalid")
        try:
            leftovers = tuple(
                child for child in self.path.parent.iterdir()
                if child.name.startswith(_TEMP_PREFIX)
            )
        except OSError:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_directory_unreadable"
            ) from None
        if leftovers:
            raise DatabaseKeyEnvelopeError("database_key_envelope_temporary_present")

    def _write_temporary(self, data: bytes) -> Path:
        descriptor, name = tempfile.mkstemp(
            prefix=_TEMP_PREFIX, suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(name)
        try:
            if os.name == "posix":
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            return temporary
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary.unlink(missing_ok=True)
            raise

    def _read_regular_bytes(self) -> bytes:
        data, _identity = self._read_with_identity()
        return data

    def _read_with_identity(self) -> tuple[bytes, tuple[int, int]]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags)
        except OSError:
            raise DatabaseKeyEnvelopeError("database_key_envelope_unreadable") from None
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise DatabaseKeyEnvelopeError("database_key_envelope_not_regular")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, 64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_REGISTRY_BYTES:
                    raise DatabaseKeyEnvelopeError("database_key_envelope_size_invalid")
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        try:
            path_status = self.path.lstat()
        except OSError:
            raise DatabaseKeyEnvelopeError("database_key_envelope_changed") from None
        identity = (before.st_dev, before.st_ino)
        if (
            self.path.is_symlink()
            or not stat.S_ISREG(path_status.st_mode)
            or identity != (after.st_dev, after.st_ino)
            or identity != (path_status.st_dev, path_status.st_ino)
            or before.st_size != after.st_size
        ):
            raise DatabaseKeyEnvelopeError("database_key_envelope_changed")
        return b"".join(chunks), identity

    @staticmethod
    def _registry_identity(
        envelopes: tuple[DatabaseKeyEnvelope, ...],
    ) -> tuple[str, int]:
        if not isinstance(envelopes, tuple) or not envelopes:
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_empty")
        context_ids = {envelope.database_context_id for envelope in envelopes}
        if len(context_ids) != 1:
            raise DatabaseKeyEnvelopeError("database_key_context_mismatch")
        return next(iter(context_ids)), max(
            envelope.key_generation for envelope in envelopes
        )

    @staticmethod
    def _encode_registry(
        database_context_id: str,
        highest_generation: int,
        envelopes: tuple[DatabaseKeyEnvelope, ...],
        auth_key: DerivedDomainKey,
    ) -> bytes:
        FileDatabaseKeyEnvelopeRepository._validate_auth_key(auth_key)
        try:
            validate_uuid4(database_context_id)
        except Exception:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_invalid"
            ) from None
        if type(highest_generation) is not int or highest_generation < 1:
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        if not isinstance(envelopes, tuple):
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        if any(
            envelope.database_context_id != database_context_id
            or envelope.key_generation > highest_generation
            for envelope in envelopes
        ):
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        payload = {
            "database_context_id": database_context_id,
            "envelopes": [envelope.to_payload() for envelope in envelopes],
            "highest_generation": highest_generation,
            "registry_auth_algorithm": _REGISTRY_AUTH_ALGORITHM,
            "registry_auth_kdf_version": 1,
            "registry_version": DATABASE_KEY_ENVELOPE_REGISTRY_VERSION,
        }
        authenticated = _canonical_json(payload)
        tag = hmac.new(
            auth_key.key_material, authenticated, hashlib.sha256
        ).digest()
        data = _canonical_json(
            {**payload, "registry_auth_tag": _base64url_encode(tag)}
        )
        if len(data) > _MAX_REGISTRY_BYTES:
            raise DatabaseKeyEnvelopeError("database_key_envelope_size_invalid")
        return data

    @classmethod
    def _decode_registry(
        cls, value: bytes, auth_key: DerivedDomainKey
    ) -> tuple[str, int, tuple[DatabaseKeyEnvelope, ...]]:
        cls._validate_auth_key(auth_key)
        if not value or len(value) > _MAX_REGISTRY_BYTES:
            raise DatabaseKeyEnvelopeError("database_key_envelope_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise DatabaseKeyEnvelopeError("database_key_envelope_format_invalid") from None
        if not isinstance(payload, dict) or set(payload) != {
            "database_context_id",
            "envelopes",
            "highest_generation",
            "registry_auth_algorithm",
            "registry_auth_kdf_version",
            "registry_auth_tag",
            "registry_version",
        }:
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        tag = _base64url_decode(payload.pop("registry_auth_tag"))
        expected_tag = hmac.new(
            auth_key.key_material, _canonical_json(payload), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_authentication_failed"
            )
        if type(payload["registry_version"]) is not int:
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        if payload["registry_version"] != DATABASE_KEY_ENVELOPE_REGISTRY_VERSION:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_version_unsupported"
            )
        if (
            payload["registry_auth_algorithm"] != _REGISTRY_AUTH_ALGORITHM
            or type(payload["registry_auth_kdf_version"]) is not int
            or payload["registry_auth_kdf_version"] != 1
        ):
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_auth_unsupported"
            )
        if not isinstance(payload["envelopes"], list):
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        context_id = payload["database_context_id"]
        highest_generation = payload["highest_generation"]
        try:
            validate_uuid4(context_id)
        except Exception:
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_invalid"
            ) from None
        if type(highest_generation) is not int or highest_generation < 1:
            raise DatabaseKeyEnvelopeError("database_key_envelope_registry_invalid")
        envelopes = tuple(
            DatabaseKeyEnvelope.from_payload(item) for item in payload["envelopes"]
        )
        if cls._encode_registry(
            context_id, highest_generation, envelopes, auth_key
        ) != value:
            raise DatabaseKeyEnvelopeError("database_key_envelope_not_canonical")
        return context_id, highest_generation, envelopes

    @staticmethod
    def _validate_auth_key(auth_key: DerivedDomainKey) -> None:
        if (
            not isinstance(auth_key, DerivedDomainKey)
            or auth_key.purpose != DATABASE_KEY_REGISTRY_AUTH_PURPOSE
            or auth_key.derivation_version != 1
            or not isinstance(auth_key.key_material, bytes)
            or len(auth_key.key_material) != 32
        ):
            raise DatabaseKeyEnvelopeError(
                "database_key_envelope_registry_auth_key_invalid"
            )


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
        raise DatabaseKeyEnvelopeError(
            "database_key_envelope_registry_invalid"
        ) from None


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise DatabaseKeyEnvelopeError(
            "database_key_envelope_registry_auth_tag_invalid"
        )
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (TypeError, ValueError):
        raise DatabaseKeyEnvelopeError(
            "database_key_envelope_registry_auth_tag_invalid"
        ) from None
    if _base64url_encode(decoded) != value or len(decoded) != 32:
        raise DatabaseKeyEnvelopeError(
            "database_key_envelope_registry_auth_tag_invalid"
        )
    return decoded
