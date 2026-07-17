"""Pure values, states and rules for the local application lock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import re
import uuid


SECURITY_SCHEMA_VERSION = 1
SECURITY_FORMAT_VERSION = 1
ENROLLMENT_MARKER_VERSION = 1
PASSWORD_HASH_FORMAT_VERSION = 1
RECOVERY_CODE_FORMAT_VERSION = 1
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_ENTROPY_BYTES = 10
RECOVERY_CODE_SALT_BYTES = 16
RECOVERY_CODE_HASH_BYTES = 32

_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_CHECK_ALPHABET = _CROCKFORD_ALPHABET + "*~$=U"
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class SecurityError(RuntimeError):
    """Base error whose message never contains credential material."""


class SecurityStateError(SecurityError):
    """The operation is not valid for the current fail-closed state."""


class SecurityStoreError(SecurityError):
    """The isolated security store is corrupt or unavailable."""


class UnsupportedSecurityVersionError(SecurityStoreError):
    """The store uses an unknown newer schema or format."""


class ConcurrentSecurityOperationError(SecurityError):
    """A competing critical operation won the transaction."""


class PasswordViolation(str, Enum):
    TOO_SHORT = "too_short"
    TOO_LARGE = "too_large"
    BLOCKED = "blocked"


class PasswordPolicyError(SecurityError):
    """Structured password-policy rejection without retaining the password."""

    def __init__(self, violations: tuple[PasswordViolation, ...]):
        self.violations = violations
        super().__init__("password_policy_rejected")


class RecoveryCodeError(SecurityError):
    """A recovery code has invalid public formatting."""

    def __init__(self, code: str = "invalid_recovery_code"):
        self.code = code
        super().__init__(code)


class SecurityStoreState(str, Enum):
    UNINITIALIZED = "uninitialized"
    READY = "ready"
    PASSWORD_RESET_PENDING = "password_reset_pending"
    INCONSISTENT = "inconsistent"
    CORRUPT = "corrupt"
    UNSUPPORTED_VERSION = "unsupported_version"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    PASSWORD_RESET_PENDING = "password_reset_pending"
    DISABLED = "disabled"


class AuthenticationStatus(str, Enum):
    AUTHENTICATED = "authenticated"
    INVALID_CREDENTIALS = "invalid_credentials"
    THROTTLED = "throttled"
    STORE_UNAVAILABLE = "store_unavailable"
    PASSWORD_RESET_REQUIRED = "password_reset_required"


class RecoveryStatus(str, Enum):
    ACCEPTED = "accepted"
    INVALID = "invalid"
    THROTTLED = "throttled"
    STORE_UNAVAILABLE = "store_unavailable"


@dataclass(frozen=True)
class PasswordPolicy:
    min_characters: int = 15
    max_utf8_bytes: int = 1024
    blocked_passwords: frozenset[str] = frozenset(
        {
            "123456789012345",
            "passwortpasswort",
            "passwordpassword",
            "qwertzuiopasdfg",
            "jenaplankompetenzmanager",
        }
    )

    def validate(self, password: str) -> None:
        violations: list[PasswordViolation] = []
        if len(password) < self.min_characters:
            violations.append(PasswordViolation.TOO_SHORT)
        try:
            encoded_length = len(password.encode("utf-8"))
        except UnicodeEncodeError:
            encoded_length = self.max_utf8_bytes + 1
        if encoded_length > self.max_utf8_bytes:
            violations.append(PasswordViolation.TOO_LARGE)
        if password in self.blocked_passwords:
            violations.append(PasswordViolation.BLOCKED)
        if violations:
            raise PasswordPolicyError(tuple(violations))


@dataclass(frozen=True)
class LockState:
    locked: bool
    remaining_seconds: int
    failure_count: int
    clock_rollback_detected: bool = False


@dataclass(frozen=True)
class AccountRecord:
    user_id: str
    installation_id: str
    password_hash: str
    hash_format_version: int
    status: AccountStatus
    failed_attempts: int
    locked_until_utc: datetime | None
    last_observed_utc: datetime | None
    recovery_failed_attempts: int
    recovery_locked_until_utc: datetime | None
    recovery_last_observed_utc: datetime | None


@dataclass(frozen=True)
class RecoveryCodeHash:
    recovery_code_id: str
    salt: bytes
    digest: bytes


@dataclass(frozen=True)
class RecoveryCodeCandidate:
    recovery_code_id: str
    salt: bytes
    digest: bytes
    status: str


def validate_uuid4(value: str) -> str:
    if not isinstance(value, str) or not _UUID_PATTERN.fullmatch(value):
        raise SecurityStoreError("invalid_uuid4")
    parsed = uuid.UUID(value)
    if parsed.version != 4 or parsed.variant != uuid.RFC_4122:
        raise SecurityStoreError("invalid_uuid4")
    return value


def format_installation_id(installation_id: str) -> str:
    return f"INS-{validate_uuid4(installation_id)}"


def delay_seconds_for_failure(failure_count: int) -> int:
    if failure_count < 5:
        return 0
    return min(30 * (2 ** (failure_count - 5)), 300)


def encode_recovery_payload(entropy: bytes) -> str:
    if len(entropy) != RECOVERY_CODE_ENTROPY_BYTES:
        raise ValueError("Recovery entropy must contain exactly 10 bytes.")
    number = int.from_bytes(entropy, "big")
    chars = ["0"] * 16
    for index in range(15, -1, -1):
        chars[index] = _CROCKFORD_ALPHABET[number & 31]
        number >>= 5
    return "".join(chars)


def recovery_check_symbol(payload: str) -> str:
    value = 0
    for character in payload:
        try:
            digit = _CROCKFORD_ALPHABET.index(character)
        except ValueError as error:
            raise RecoveryCodeError() from error
        value = (value * 32 + digit) % 37
    return _CROCKFORD_CHECK_ALPHABET[value]


def format_recovery_code(entropy: bytes) -> tuple[str, str]:
    payload = encode_recovery_payload(entropy)
    check = recovery_check_symbol(payload)
    displayed = "JKM1-" + "-".join(payload[index : index + 4] for index in range(0, 16, 4))
    return f"{displayed}-{check}", f"JKM1{payload}{check}"


def canonicalize_recovery_code(value: str) -> str:
    if not isinstance(value, str) or any(ord(character) > 127 for character in value):
        raise RecoveryCodeError()
    compact = value.replace("-", "").replace(" ", "").upper()
    compact = compact.replace("O", "0").replace("I", "1").replace("L", "1")
    if len(compact) != 21 or not compact.startswith("JKM1"):
        raise RecoveryCodeError()
    payload, check = compact[4:20], compact[20]
    if any(character not in _CROCKFORD_ALPHABET for character in payload):
        raise RecoveryCodeError()
    if not hmac.compare_digest(recovery_check_symbol(payload), check):
        raise RecoveryCodeError()
    return compact


def hash_recovery_code(salt: bytes, canonical_code: str) -> bytes:
    if len(salt) != RECOVERY_CODE_SALT_BYTES:
        raise ValueError("Recovery salt must contain exactly 16 bytes.")
    return hashlib.sha256(salt + canonical_code.encode("ascii")).digest()
