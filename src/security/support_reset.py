"""Canonical token codec and application service for offline support reset."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import binascii
import hashlib
import hmac
import json
import re
from typing import Any

from .domain import (
    AccountStatus,
    SUPPORT_RESET_ACTION,
    SUPPORT_RESET_ALGORITHM,
    SUPPORT_RESET_CLOCK_SKEW,
    SUPPORT_RESET_ENVELOPE,
    SUPPORT_RESET_FORMAT_VERSION,
    SUPPORT_RESET_MAX_PAYLOAD_BYTES,
    SUPPORT_RESET_MAX_TOKEN_BYTES,
    SUPPORT_RESET_NONCE_BYTES,
    SUPPORT_RESET_REQUEST_MAX_AGE,
    SUPPORT_RESET_TOKEN_MAX_AGE,
    SECURITY_FORMAT_VERSION,
    SECURITY_SCHEMA_VERSION,
    SecurityBackupProof,
    SecurityStateError,
    SecurityStoreError,
    SupportPublicKeyStatus,
    SupportResetFailureCode,
    SupportResetPayload,
    SupportResetRejected,
    SupportResetRequest,
    SupportResetResult,
    validate_uuid4,
)
from .ports import (
    RandomSource,
    EnrollmentMarkerStore,
    SecurityRepository,
    SupportPublicKeyRegistry,
    SupportResetSignatureVerifier,
    SupportSecurityBackupPort,
    UtcClock,
)


_PAYLOAD_FIELDS = (
    "format_version",
    "algorithm",
    "key_id",
    "installation_id",
    "user_id",
    "reset_request_id",
    "action",
    "created_at",
    "expires_at",
    "nonce",
)
_REQUEST_FIELDS = (
    "format_version",
    "installation_id",
    "user_id",
    "reset_request_id",
    "action",
    "created_at",
    "expires_at",
    "nonce",
)
_BASE64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SupportResetTokenCodec:
    """Strict canonical JSON and base64url contract for JKM-SR1."""

    @classmethod
    def canonical_payload_bytes(cls, payload: SupportResetPayload) -> bytes:
        cls._validate_payload(payload)
        mapping = {
            "format_version": payload.format_version,
            "algorithm": payload.algorithm,
            "key_id": payload.key_id,
            "installation_id": payload.installation_id,
            "user_id": payload.user_id,
            "reset_request_id": payload.reset_request_id,
            "action": payload.action,
            "created_at": _format_utc(payload.created_at),
            "expires_at": _format_utc(payload.expires_at),
            "nonce": payload.nonce,
        }
        encoded = json.dumps(
            mapping,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > SUPPORT_RESET_MAX_PAYLOAD_BYTES:
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
        return encoded

    @classmethod
    def encode(cls, payload: SupportResetPayload, signature: bytes) -> str:
        if not isinstance(signature, bytes) or len(signature) != 64:
            raise SupportResetRejected(SupportResetFailureCode.SIGNATURE_INVALID)
        token = (
            f"{SUPPORT_RESET_ENVELOPE}."
            f"{_base64url_encode(cls.canonical_payload_bytes(payload))}."
            f"{_base64url_encode(signature)}"
        )
        if len(token.encode("ascii")) > SUPPORT_RESET_MAX_TOKEN_BYTES:
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
        return token

    @classmethod
    def decode(cls, token: str) -> tuple[SupportResetPayload, bytes, bytes]:
        if not isinstance(token, str):
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
        try:
            token_bytes = token.encode("ascii")
        except UnicodeEncodeError as error:
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID) from error
        if not token_bytes or len(token_bytes) > SUPPORT_RESET_MAX_TOKEN_BYTES:
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
        parts = token.split(".")
        if len(parts) != 3:
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
        if parts[0] != SUPPORT_RESET_ENVELOPE:
            raise SupportResetRejected(SupportResetFailureCode.ENVELOPE_INVALID)
        payload_bytes = _base64url_decode(parts[1], SUPPORT_RESET_MAX_PAYLOAD_BYTES)
        signature = _base64url_decode(parts[2], 64)
        if len(signature) != 64:
            raise SupportResetRejected(SupportResetFailureCode.SIGNATURE_INVALID)
        pairs = _load_json_pairs(payload_bytes)
        if tuple(key for key, _value in pairs) != _PAYLOAD_FIELDS:
            keys = tuple(key for key, _value in pairs)
            code = (
                SupportResetFailureCode.PAYLOAD_NOT_CANONICAL
                if set(keys) == set(_PAYLOAD_FIELDS) and len(keys) == len(_PAYLOAD_FIELDS)
                else SupportResetFailureCode.FIELDS_INVALID
            )
            raise SupportResetRejected(code)
        values = dict(pairs)
        payload = cls._payload_from_mapping(values)
        if cls.canonical_payload_bytes(payload) != payload_bytes:
            raise SupportResetRejected(SupportResetFailureCode.PAYLOAD_NOT_CANONICAL)
        return payload, payload_bytes, signature

    @classmethod
    def canonical_request_bytes(cls, request: SupportResetRequest) -> bytes:
        _validate_request(request)
        mapping = {
            "format_version": request.format_version,
            "installation_id": request.installation_id,
            "user_id": request.user_id,
            "reset_request_id": request.reset_request_id,
            "action": request.action,
            "created_at": _format_utc(request.created_at),
            "expires_at": _format_utc(request.expires_at),
            "nonce": request.nonce,
        }
        return json.dumps(
            mapping,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def decode_request(cls, payload: bytes) -> SupportResetRequest:
        if not isinstance(payload, bytes) or len(payload) > SUPPORT_RESET_MAX_PAYLOAD_BYTES:
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
        pairs = _load_json_pairs(payload)
        if tuple(key for key, _value in pairs) != _REQUEST_FIELDS:
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        values = dict(pairs)
        if type(values["format_version"]) is not int:
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        for key in _REQUEST_FIELDS[1:]:
            if not isinstance(values[key], str):
                raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        request = SupportResetRequest(
            format_version=values["format_version"],
            installation_id=values["installation_id"],
            user_id=values["user_id"],
            reset_request_id=values["reset_request_id"],
            action=values["action"],
            created_at=_parse_utc(values["created_at"]),
            expires_at=_parse_utc(values["expires_at"]),
            nonce=values["nonce"],
        )
        _validate_request(request)
        if cls.canonical_request_bytes(request) != payload:
            raise SupportResetRejected(SupportResetFailureCode.PAYLOAD_NOT_CANONICAL)
        return request

    @classmethod
    def _payload_from_mapping(cls, values: dict[str, Any]) -> SupportResetPayload:
        if type(values["format_version"]) is not int:
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        for key in _PAYLOAD_FIELDS[1:]:
            if not isinstance(values[key], str):
                raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        payload = SupportResetPayload(
            format_version=values["format_version"],
            algorithm=values["algorithm"],
            key_id=values["key_id"],
            installation_id=values["installation_id"],
            user_id=values["user_id"],
            reset_request_id=values["reset_request_id"],
            action=values["action"],
            created_at=_parse_utc(values["created_at"]),
            expires_at=_parse_utc(values["expires_at"]),
            nonce=values["nonce"],
        )
        cls._validate_payload(payload)
        return payload

    @staticmethod
    def _validate_payload(payload: SupportResetPayload) -> None:
        if type(payload.format_version) is not int:
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        if payload.format_version != SUPPORT_RESET_FORMAT_VERSION:
            raise SupportResetRejected(SupportResetFailureCode.VERSION_UNSUPPORTED)
        if not isinstance(payload.algorithm, str):
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        if not isinstance(payload.key_id, str) or not _KEY_ID_PATTERN.fullmatch(payload.key_id):
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        for identifier in (
            payload.installation_id,
            payload.user_id,
            payload.reset_request_id,
        ):
            _validate_uuid(identifier)
        if not isinstance(payload.action, str):
            raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
        _format_utc(payload.created_at)
        _format_utc(payload.expires_at)
        _validate_nonce(payload.nonce)


class SupportResetService:
    """Create bound requests and execute reset only after verified backup."""

    def __init__(
        self,
        *,
        repository: SecurityRepository,
        marker: EnrollmentMarkerStore,
        random_source: RandomSource,
        utc_clock: UtcClock,
        key_registry: SupportPublicKeyRegistry,
        signature_verifier: SupportResetSignatureVerifier,
    ) -> None:
        self._repository = repository
        self._marker = marker
        self._random = random_source
        self._clock = utc_clock
        self._keys = key_registry
        self._signature_verifier = signature_verifier

    def create_request(
        self, *, duration: timedelta = SUPPORT_RESET_REQUEST_MAX_AGE
    ) -> SupportResetRequest:
        if duration <= timedelta(0) or duration > SUPPORT_RESET_REQUEST_MAX_AGE:
            raise SecurityStateError("support_reset_request_duration_invalid")
        try:
            account = self._ready_account()
        except (SecurityStateError, SecurityStoreError) as error:
            raise SupportResetRejected(SupportResetFailureCode.STORE_UNAVAILABLE) from error
        if account.status != AccountStatus.ACTIVE:
            raise SecurityStateError("support_reset_account_not_active")
        now = self._now()
        request = SupportResetRequest(
            format_version=SUPPORT_RESET_FORMAT_VERSION,
            installation_id=account.installation_id,
            user_id=account.user_id,
            reset_request_id=validate_uuid4(self._random.uuid4()),
            action=SUPPORT_RESET_ACTION,
            created_at=now,
            expires_at=now + duration,
            nonce=_base64url_encode(self._random.bytes(SUPPORT_RESET_NONCE_BYTES)),
        )
        _validate_request(request)
        self._repository.create_support_reset_request(request)
        return request

    def execute(
        self, token: str, *, backup: SupportSecurityBackupPort
    ) -> SupportResetResult:
        payload, canonical_bytes, signature = SupportResetTokenCodec.decode(token)
        if payload.algorithm != SUPPORT_RESET_ALGORITHM:
            raise SupportResetRejected(SupportResetFailureCode.ALGORITHM_UNSUPPORTED)
        now = self._now()
        public_key = self._keys.get(payload.key_id)
        if public_key is None:
            raise SupportResetRejected(SupportResetFailureCode.KEY_UNKNOWN)
        if public_key.status == SupportPublicKeyStatus.REVOKED:
            raise SupportResetRejected(SupportResetFailureCode.KEY_REVOKED)
        if now < public_key.not_before:
            raise SupportResetRejected(SupportResetFailureCode.KEY_NOT_YET_VALID)
        if now > public_key.not_after:
            raise SupportResetRejected(SupportResetFailureCode.KEY_EXPIRED)
        if not self._signature_verifier.verify(
            public_key.public_key, canonical_bytes, signature
        ):
            raise SupportResetRejected(SupportResetFailureCode.SIGNATURE_INVALID)

        try:
            account = self._ready_account()
        except (SecurityStateError, SecurityStoreError) as error:
            raise SupportResetRejected(SupportResetFailureCode.STORE_UNAVAILABLE) from error
        if payload.installation_id != account.installation_id:
            raise SupportResetRejected(SupportResetFailureCode.INSTALLATION_MISMATCH)
        if payload.user_id != account.user_id:
            raise SupportResetRejected(SupportResetFailureCode.USER_MISMATCH)
        try:
            request = self._repository.load_support_reset_request(payload.reset_request_id)
        except SecurityStoreError as error:
            raise SupportResetRejected(SupportResetFailureCode.STORE_UNAVAILABLE) from error
        if request is None:
            raise SupportResetRejected(SupportResetFailureCode.REQUEST_MISMATCH)
        if request.installation_id != payload.installation_id or request.user_id != payload.user_id:
            raise SupportResetRejected(SupportResetFailureCode.REQUEST_MISMATCH)
        if request.nonce != payload.nonce:
            raise SupportResetRejected(SupportResetFailureCode.NONCE_MISMATCH)
        if payload.action != SUPPORT_RESET_ACTION or request.action != payload.action:
            raise SupportResetRejected(SupportResetFailureCode.ACTION_UNSUPPORTED)
        self._validate_time(payload, request, now)

        try:
            token_bytes = token.encode("ascii")
        except UnicodeEncodeError as error:  # already rejected by the codec
            raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID) from error
        token_digest = hashlib.sha256(token_bytes).digest()
        try:
            digest_used = self._repository.support_token_digest_used(token_digest)
        except SecurityStoreError as error:
            raise SupportResetRejected(SupportResetFailureCode.STORE_UNAVAILABLE) from error
        if digest_used:
            raise SupportResetRejected(SupportResetFailureCode.TOKEN_ALREADY_USED)
        if request.status != "active":
            raise SupportResetRejected(SupportResetFailureCode.REQUEST_NOT_ACTIVE)

        try:
            proof = backup.create_and_verify()
        except Exception as error:
            raise SupportResetRejected(SupportResetFailureCode.BACKUP_FAILED) from error
        _validate_backup_proof(proof)

        try:
            epoch = self._repository.consume_support_reset(
                payload=payload,
                token_digest=token_digest,
                now=now,
            )
        except SecurityStoreError as error:
            raise SupportResetRejected(SupportResetFailureCode.STORE_UNAVAILABLE) from error
        if epoch is None:
            raise SupportResetRejected(SupportResetFailureCode.CONCURRENT_USE)
        return SupportResetResult(payload.reset_request_id, epoch, proof)

    @staticmethod
    def _validate_time(
        payload: SupportResetPayload, request: SupportResetRequest, now: datetime
    ) -> None:
        lifetime = payload.expires_at - payload.created_at
        if lifetime <= timedelta(0) or lifetime > SUPPORT_RESET_TOKEN_MAX_AGE:
            raise SupportResetRejected(SupportResetFailureCode.TOKEN_LIFETIME_INVALID)
        if now + SUPPORT_RESET_CLOCK_SKEW < payload.created_at:
            raise SupportResetRejected(SupportResetFailureCode.TOKEN_NOT_YET_VALID)
        if now - SUPPORT_RESET_CLOCK_SKEW > payload.expires_at:
            raise SupportResetRejected(SupportResetFailureCode.TOKEN_EXPIRED)
        if request.expires_at - request.created_at > SUPPORT_RESET_REQUEST_MAX_AGE:
            raise SupportResetRejected(SupportResetFailureCode.REQUEST_EXPIRED)
        if now - SUPPORT_RESET_CLOCK_SKEW > request.expires_at:
            raise SupportResetRejected(SupportResetFailureCode.REQUEST_EXPIRED)
        if payload.created_at + SUPPORT_RESET_CLOCK_SKEW < request.created_at:
            raise SupportResetRejected(SupportResetFailureCode.TOKEN_NOT_YET_VALID)
        if payload.expires_at > request.expires_at + SUPPORT_RESET_CLOCK_SKEW:
            raise SupportResetRejected(SupportResetFailureCode.TOKEN_EXPIRED)

    def _now(self) -> datetime:
        now = self._clock.utc_now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise SecurityStoreError("utc_clock_returned_naive_time")
        return now.astimezone(timezone.utc)

    def _ready_account(self):
        try:
            schema, format_version, marker_reference, account = self._repository.inspect()
            stored_marker = self._marker.read_reference()
        except SecurityStoreError as error:
            raise SecurityStateError("support_reset_store_not_ready") from error
        if (
            schema != SECURITY_SCHEMA_VERSION
            or format_version != SECURITY_FORMAT_VERSION
            or not hmac.compare_digest(marker_reference, stored_marker)
        ):
            raise SecurityStateError("support_reset_store_not_ready")
        return account


def _load_json_pairs(payload: bytes) -> list[tuple[str, Any]]:
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=lambda pairs: pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SupportResetRejected(SupportResetFailureCode.JSON_INVALID) from error
    if not isinstance(value, list) or any(
        not isinstance(pair, tuple) or len(pair) != 2 or not isinstance(pair[0], str)
        for pair in value
    ):
        raise SupportResetRejected(SupportResetFailureCode.JSON_INVALID)
    keys = [key for key, _value in value]
    if len(keys) != len(set(keys)):
        raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
    return value


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str, maximum_bytes: int) -> bytes:
    if not isinstance(value, str) or not value or not _BASE64URL_PATTERN.fullmatch(value):
        raise SupportResetRejected(SupportResetFailureCode.BASE64URL_INVALID)
    if len(value) > ((maximum_bytes + 2) // 3) * 4:
        raise SupportResetRejected(SupportResetFailureCode.FORMAT_INVALID)
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as error:
        raise SupportResetRejected(SupportResetFailureCode.BASE64URL_INVALID) from error
    if len(decoded) > maximum_bytes or _base64url_encode(decoded) != value:
        raise SupportResetRejected(SupportResetFailureCode.BASE64URL_INVALID)
    return decoded


def _format_utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
    utc = value.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or len(value) != 27 or not value.endswith("Z"):
        raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as error:
        raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID) from error
    return parsed.replace(tzinfo=timezone.utc)


def _validate_uuid(value: str) -> None:
    try:
        validate_uuid4(value)
    except SecurityStoreError as error:
        raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID) from error


def _validate_nonce(value: str) -> None:
    decoded = _base64url_decode(value, SUPPORT_RESET_NONCE_BYTES)
    if len(decoded) != SUPPORT_RESET_NONCE_BYTES:
        raise SupportResetRejected(SupportResetFailureCode.FIELDS_INVALID)


def _validate_request(request: SupportResetRequest) -> None:
    if type(request.format_version) is not int or request.format_version != SUPPORT_RESET_FORMAT_VERSION:
        raise SupportResetRejected(SupportResetFailureCode.VERSION_UNSUPPORTED)
    for identifier in (
        request.installation_id,
        request.user_id,
        request.reset_request_id,
    ):
        _validate_uuid(identifier)
    if request.action != SUPPORT_RESET_ACTION:
        raise SupportResetRejected(SupportResetFailureCode.ACTION_UNSUPPORTED)
    _format_utc(request.created_at)
    _format_utc(request.expires_at)
    if request.expires_at <= request.created_at:
        raise SupportResetRejected(SupportResetFailureCode.REQUEST_EXPIRED)
    if request.expires_at - request.created_at > SUPPORT_RESET_REQUEST_MAX_AGE:
        raise SupportResetRejected(SupportResetFailureCode.REQUEST_EXPIRED)
    _validate_nonce(request.nonce)


def _validate_backup_proof(proof: SecurityBackupProof) -> None:
    if (
        not isinstance(proof, SecurityBackupProof)
        or not isinstance(proof.path, str)
        or not proof.path
        or not isinstance(proof.sha256, str)
        or not _SHA256_PATTERN.fullmatch(proof.sha256)
    ):
        raise SupportResetRejected(SupportResetFailureCode.BACKUP_FAILED)
