"""Qt-free operator workflow around the unchanged support-reset codec."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
from collections.abc import Callable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from src.security.domain import (
    SUPPORT_RESET_TOKEN_MAX_AGE,
    SupportResetRejected,
    SupportResetRequest,
)
from src.security.support_reset import SupportResetTokenCodec
from tools.generate_support_reset import generate_token_from_request_bytes


MAX_REQUEST_BYTES = 4096
MAX_PRIVATE_KEY_BYTES = 64 * 1024
ALLOWED_LIFETIME_MINUTES = (15, 30, 60, 120)
AUDIT_ACTION = "reset_code_created"
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_FIELDS = {
    "format_version",
    "key_id",
    "algorithm",
    "public_key",
    "status",
    "not_before",
    "not_after",
    "fingerprint_sha256",
}


class SupportAssistantError(RuntimeError):
    """Expected fail-closed operator error without secret-bearing details."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SupportProductKey:
    key_id: str
    public_key: bytes
    status: str
    not_before: datetime
    not_after: datetime
    fingerprint_sha256: str


@dataclass(frozen=True)
class SupportRequestProjection:
    application_name: str
    username: str | None
    installation_id_short: str
    created_at: datetime
    expires_at: datetime
    status: str


@dataclass(frozen=True)
class SupportKeyProjection:
    key_id: str
    status: str
    fingerprint_short: str


@dataclass(frozen=True)
class LoadedSupportRequest:
    request_bytes: bytes
    request: SupportResetRequest
    projection: SupportRequestProjection


@dataclass(frozen=True)
class GeneratedResetCode:
    token: str
    expires_at: datetime
    request_id: str
    key_id: str


class SupportAssistantAuditLog:
    """Append-only local audit restricted to four non-secret fields."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, *, occurred_at: datetime, request_id: str, key_id: str) -> None:
        occurred_at = _aware_utc(occurred_at)
        parent = self.path.parent
        if parent.exists():
            if parent.is_symlink() or not parent.is_dir():
                raise SupportAssistantError("audit_unavailable")
        else:
            try:
                parent.mkdir(parents=True, mode=0o700)
            except OSError as error:
                raise SupportAssistantError("audit_unavailable") from error
        try:
            os.chmod(parent, 0o700)
        except OSError as error:
            raise SupportAssistantError("audit_unavailable") from error
        if self.path.is_symlink():
            raise SupportAssistantError("audit_unavailable")
        if self.path.exists() and not self.path.is_file():
            raise SupportAssistantError("audit_unavailable")
        record = {
            "timestamp": _format_utc(occurred_at),
            "request_id": request_id,
            "key_id": key_id,
            "action": AUDIT_ACTION,
        }
        payload = (
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags, 0o600)
            try:
                os.fchmod(descriptor, 0o600)
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise SupportAssistantError("audit_unavailable") from error


class SupportAssistantApplicationService:
    """Inspect one request and create one protocol-identical signed token."""

    def __init__(
        self,
        *,
        product_key: SupportProductKey,
        audit_log: SupportAssistantAuditLog,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._key = product_key
        self._audit = audit_log
        self._now_fn = now_fn

    @classmethod
    def from_manifest(
        cls,
        manifest_path: Path,
        *,
        audit_path: Path,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> "SupportAssistantApplicationService":
        return cls(
            product_key=load_product_key(manifest_path),
            audit_log=SupportAssistantAuditLog(audit_path),
            now_fn=now_fn,
        )

    @classmethod
    def from_product_manifest(
        cls,
        manifest: Mapping[str, object],
        *,
        audit_path: Path,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> "SupportAssistantApplicationService":
        return cls(
            product_key=product_key_from_mapping(manifest),
            audit_log=SupportAssistantAuditLog(audit_path),
            now_fn=now_fn,
        )

    def load_request(self, path: Path) -> LoadedSupportRequest:
        path = Path(path)
        if path.suffix.lower() != ".jkmresetrequest":
            raise SupportAssistantError("request_extension_invalid")
        if path.is_symlink() or not path.is_file():
            raise SupportAssistantError("request_unreadable")
        try:
            with path.open("rb") as stream:
                payload = stream.read(MAX_REQUEST_BYTES + 1)
        except OSError as error:
            raise SupportAssistantError("request_unreadable") from error
        return self.inspect_request_bytes(payload)

    def inspect_request_bytes(self, payload: bytes) -> LoadedSupportRequest:
        if not isinstance(payload, bytes) or not payload or len(payload) > MAX_REQUEST_BYTES:
            raise SupportAssistantError("request_invalid")
        payload = payload.rstrip(b"\r\n")
        try:
            request = SupportResetTokenCodec.decode_request(payload)
        except Exception as error:
            raise SupportAssistantError("request_invalid") from error
        now = self._now()
        if now < request.created_at:
            raise SupportAssistantError("request_not_yet_valid")
        if now >= request.expires_at:
            raise SupportAssistantError("request_expired")
        projection = SupportRequestProjection(
            application_name="Jenaplan-Kompetenzmanager",
            username=None,
            installation_id_short=_short_identifier(request.installation_id),
            created_at=request.created_at,
            expires_at=request.expires_at,
            status="valid",
        )
        return LoadedSupportRequest(payload, request, projection)

    def key_projection(self) -> SupportKeyProjection:
        self._active_key(self._now())
        return SupportKeyProjection(
            key_id=self._key.key_id,
            status="active",
            fingerprint_short=_short_fingerprint(self._key.fingerprint_sha256),
        )

    def generate_reset_code(
        self,
        *,
        loaded_request: LoadedSupportRequest,
        private_key_path: Path,
        passphrase: str,
        lifetime_minutes: int,
    ) -> GeneratedResetCode:
        now = self._now()
        key = self._active_key(now)
        request = self.inspect_request_bytes(loaded_request.request_bytes).request
        if request != loaded_request.request:
            raise SupportAssistantError("request_changed")
        if lifetime_minutes not in ALLOWED_LIFETIME_MINUTES:
            raise SupportAssistantError("lifetime_invalid")
        private_key = _load_matching_private_key(
            Path(private_key_path), passphrase, key.public_key
        )
        passphrase = ""
        try:
            try:
                token = generate_token_from_request_bytes(
                    request_bytes=loaded_request.request_bytes,
                    private_key_path=Path(private_key_path),
                    key_id=key.key_id,
                    passphrase=_last_passphrase_bytes(private_key),
                    now=now,
                    lifetime=timedelta(minutes=lifetime_minutes),
                )
            except Exception as error:
                raise SupportAssistantError("token_generation_failed") from error
        finally:
            _forget_private_key_passphrase(private_key)
        try:
            payload, canonical, signature = SupportResetTokenCodec.decode(token)
            Ed25519PublicKey.from_public_bytes(key.public_key).verify(
                signature, canonical
            )
        except (InvalidSignature, SupportResetRejected, ValueError) as error:
            token = ""
            raise SupportAssistantError("generated_token_invalid") from error
        if (
            payload.reset_request_id != request.reset_request_id
            or payload.installation_id != request.installation_id
            or payload.user_id != request.user_id
            or payload.key_id != key.key_id
            or payload.expires_at - payload.created_at > SUPPORT_RESET_TOKEN_MAX_AGE
        ):
            token = ""
            raise SupportAssistantError("generated_token_invalid")
        self._audit.append(
            occurred_at=now,
            request_id=request.reset_request_id,
            key_id=key.key_id,
        )
        return GeneratedResetCode(
            token=token,
            expires_at=payload.expires_at,
            request_id=request.reset_request_id,
            key_id=key.key_id,
        )

    def save_reset_code(self, path: Path, token: str) -> Path:
        path = Path(path)
        if path.suffix.lower() != ".jkmresettoken":
            path = path.with_suffix(".jkmresettoken")
        if path.exists() or path.is_symlink():
            raise SupportAssistantError("token_target_exists")
        if not path.parent.is_dir() or path.parent.is_symlink():
            raise SupportAssistantError("token_target_invalid")
        try:
            SupportResetTokenCodec.decode(token)
        except Exception as error:
            raise SupportAssistantError("token_invalid") from error
        descriptor = -1
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(token.encode("ascii") + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(path, 0o600)
        except OSError as error:
            if descriptor >= 0:
                os.close(descriptor)
            path.unlink(missing_ok=True)
            raise SupportAssistantError("token_write_failed") from error
        return path

    def _active_key(self, now: datetime) -> SupportProductKey:
        if (
            self._key.status != "active"
            or now < self._key.not_before
            or now >= self._key.not_after
        ):
            raise SupportAssistantError("support_key_not_active")
        return self._key

    def _now(self) -> datetime:
        return _aware_utc(self._now_fn())


@dataclass
class _LoadedPrivateKey:
    key: Ed25519PrivateKey
    passphrase_bytes: bytearray


def _load_matching_private_key(
    path: Path, passphrase: str, expected_public_key: bytes
) -> _LoadedPrivateKey:
    if path.is_symlink() or not path.is_file():
        raise SupportAssistantError("private_key_unreadable")
    try:
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise SupportAssistantError("private_key_permissions")
        private_bytes = path.read_bytes()
    except OSError as error:
        raise SupportAssistantError("private_key_unreadable") from error
    if len(private_bytes) > MAX_PRIVATE_KEY_BYTES:
        raise SupportAssistantError("private_key_invalid")
    encrypted_private_key_marker = b"BEGIN ENCRYPTED " + b"PRIVATE KEY"
    if encrypted_private_key_marker not in private_bytes[:80]:
        raise SupportAssistantError("private_key_not_encrypted")
    passphrase_bytes = bytearray(passphrase.encode("utf-8"))
    if not passphrase_bytes:
        raise SupportAssistantError("passphrase_required")
    try:
        loaded = serialization.load_pem_private_key(
            private_bytes, password=bytes(passphrase_bytes)
        )
    except (TypeError, ValueError) as error:
        _wipe(passphrase_bytes)
        raise SupportAssistantError("private_key_unlock_failed") from error
    if not isinstance(loaded, Ed25519PrivateKey):
        _wipe(passphrase_bytes)
        raise SupportAssistantError("private_key_invalid")
    if loaded.public_key().public_bytes_raw() != expected_public_key:
        _wipe(passphrase_bytes)
        raise SupportAssistantError("private_key_mismatch")
    return _LoadedPrivateKey(loaded, passphrase_bytes)


def _last_passphrase_bytes(loaded: _LoadedPrivateKey) -> bytes:
    return bytes(loaded.passphrase_bytes)


def _forget_private_key_passphrase(loaded: _LoadedPrivateKey) -> None:
    _wipe(loaded.passphrase_bytes)


def _wipe(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0


def load_product_key(path: Path) -> SupportProductKey:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SupportAssistantError("support_key_manifest_unavailable")
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SupportAssistantError("support_key_manifest_invalid") from error
    return product_key_from_mapping(value)


def product_key_from_mapping(value: object) -> SupportProductKey:
    if not isinstance(value, Mapping) or set(value) != _MANIFEST_FIELDS:
        raise SupportAssistantError("support_key_manifest_invalid")
    if (
        type(value["format_version"]) is not int
        or value["format_version"] != 1
        or value["algorithm"] != "Ed25519"
        or value["status"] != "active"
        or not isinstance(value["key_id"], str)
        or not _KEY_ID_PATTERN.fullmatch(value["key_id"])
    ):
        raise SupportAssistantError("support_key_manifest_invalid")
    encoded = value["public_key"]
    if not isinstance(encoded, str) or len(encoded) != 43 or "=" in encoded:
        raise SupportAssistantError("support_key_manifest_invalid")
    try:
        public_key = base64.b64decode(encoded + "=", altchars=b"-_", validate=True)
    except (binascii.Error, ValueError, TypeError) as error:
        raise SupportAssistantError("support_key_manifest_invalid") from error
    canonical_public_key = base64.urlsafe_b64encode(public_key).decode("ascii").rstrip("=")
    fingerprint = value["fingerprint_sha256"]
    if (
        len(public_key) != 32
        or canonical_public_key != encoded
        or not isinstance(fingerprint, str)
        or not _FINGERPRINT_PATTERN.fullmatch(fingerprint)
        or hashlib.sha256(public_key).hexdigest() != fingerprint
    ):
        raise SupportAssistantError("support_key_manifest_invalid")
    not_before = _parse_utc(value["not_before"])
    not_after = _parse_utc(value["not_after"])
    if not_after <= not_before:
        raise SupportAssistantError("support_key_manifest_invalid")
    return SupportProductKey(
        key_id=value["key_id"],
        public_key=public_key,
        status=value["status"],
        not_before=not_before,
        not_after=not_after,
        fingerprint_sha256=fingerprint,
    )


def support_request_reference(device_name: str, reset_request_id: str) -> str:
    normalized = unicodedata.normalize("NFKD", device_name.strip())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").upper()
    words = re.findall(r"[A-Z0-9]+", ascii_name)
    label = (words[0] if words else "GERAET")[:8]
    suffix = int.from_bytes(
        hashlib.sha256(reset_request_id.encode("ascii")).digest()[:4], "big"
    ) % 10000
    return f"JKM-{label}-{suffix:04d}"


def _short_identifier(value: str) -> str:
    return f"{value[:8]}…{value[-4:]}"


def _short_fingerprint(value: str) -> str:
    return f"{value[:12]}…{value[-8:]}"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SupportAssistantError("system_time_invalid")
    return value.astimezone(UTC)


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise SupportAssistantError("support_key_manifest_invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise SupportAssistantError("support_key_manifest_invalid") from error
    return parsed.replace(tzinfo=UTC)


def _format_utc(value: datetime) -> str:
    return _aware_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")
