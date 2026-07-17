"""Transactional application service for the Qt-independent security core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hmac
import math

from .domain import (
    AccountRecord,
    AccountStatus,
    AuthenticationStatus,
    LockState,
    PASSWORD_HASH_FORMAT_VERSION,
    RECOVERY_CODE_COUNT,
    RECOVERY_CODE_ENTROPY_BYTES,
    RECOVERY_CODE_SALT_BYTES,
    RecoveryCodeError,
    RecoveryCodeHash,
    RecoveryStatus,
    SECURITY_FORMAT_VERSION,
    SECURITY_SCHEMA_VERSION,
    SecurityStateError,
    SecurityStoreError,
    SecurityStoreState,
    UnsupportedSecurityVersionError,
    PasswordPolicy,
    canonicalize_recovery_code,
    format_installation_id,
    format_recovery_code,
    hash_recovery_code,
    validate_uuid4,
)
from .ports import (
    EnrollmentMarkerStore,
    FilePermissionManager,
    MonotonicClock,
    PasswordHasher,
    RandomSource,
    SecurityRepository,
    UtcClock,
)


_CLOCK_ROLLBACK_TOLERANCE = timedelta(minutes=5)
_CLOCK_ROLLBACK_LOCK = timedelta(minutes=5)


@dataclass(frozen=True)
class SecurityStateResult:
    state: SecurityStoreState
    installation_id: str | None = None
    user_id: str | None = None
    account_status: AccountStatus | None = None


@dataclass(frozen=True)
class EnrollmentResult:
    installation_id: str
    support_installation_id: str
    user_id: str
    recovery_set_id: str
    recovery_codes: tuple[str, ...] = field(repr=False)


@dataclass(frozen=True)
class AuthenticationResult:
    status: AuthenticationStatus
    retry_after_seconds: int = 0
    password_hash_upgraded: bool = False


@dataclass(frozen=True)
class RecoveryPreparation:
    recovery_set_id: str
    recovery_codes: tuple[str, ...] = field(repr=False)


@dataclass(frozen=True)
class RecoveryConsumptionResult:
    status: RecoveryStatus
    retry_after_seconds: int = 0
    password_reset_required: bool = False


class SecurityApplicationService:
    """Coordinate policy, cryptography, store state and crash-safe adapters."""

    def __init__(
        self,
        *,
        repository: SecurityRepository,
        marker: EnrollmentMarkerStore,
        password_hasher: PasswordHasher,
        random_source: RandomSource,
        utc_clock: UtcClock,
        monotonic_clock: MonotonicClock,
        permissions: FilePermissionManager,
        password_policy: PasswordPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._marker = marker
        self._password_hasher = password_hasher
        self._random = random_source
        self._utc_clock = utc_clock
        self._monotonic_clock = monotonic_clock
        self._permissions = permissions
        self._password_policy = password_policy or PasswordPolicy()
        self._login_monotonic_deadline: float | None = None
        self._recovery_monotonic_deadline: float | None = None

    def security_store_state(self) -> SecurityStateResult:
        store_exists = self._repository.exists()
        marker_exists = self._marker.exists()
        if not store_exists and not marker_exists:
            return SecurityStateResult(SecurityStoreState.UNINITIALIZED)
        if store_exists != marker_exists:
            return SecurityStateResult(SecurityStoreState.INCONSISTENT)
        try:
            schema, format_version, store_reference, account = self._repository.inspect()
            marker_reference = self._marker.read_reference()
        except UnsupportedSecurityVersionError:
            return SecurityStateResult(SecurityStoreState.UNSUPPORTED_VERSION)
        except SecurityStoreError:
            return SecurityStateResult(SecurityStoreState.CORRUPT)
        if (schema, format_version) != (SECURITY_SCHEMA_VERSION, SECURITY_FORMAT_VERSION):
            return SecurityStateResult(SecurityStoreState.CORRUPT)
        if not hmac.compare_digest(store_reference, marker_reference):
            return SecurityStateResult(SecurityStoreState.INCONSISTENT)
        if account.hash_format_version != PASSWORD_HASH_FORMAT_VERSION:
            return SecurityStateResult(SecurityStoreState.UNSUPPORTED_VERSION)
        if account.status == AccountStatus.PASSWORD_RESET_PENDING:
            state = SecurityStoreState.PASSWORD_RESET_PENDING
        elif account.status == AccountStatus.ACTIVE:
            state = SecurityStoreState.READY
        else:
            state = SecurityStoreState.INCONSISTENT
        return SecurityStateResult(
            state, account.installation_id, account.user_id, account.status
        )

    def enroll_local_account(self, password: str) -> EnrollmentResult:
        if self.security_store_state().state != SecurityStoreState.UNINITIALIZED:
            raise SecurityStateError("security_store_not_uninitialized")
        self._password_policy.validate(password)
        now = self._now()
        installation_id = self._new_uuid4()
        marker_reference = self._new_uuid4()
        user_id = self._new_uuid4()
        recovery_set_id = self._new_uuid4()
        displayed_codes, code_hashes = self._new_recovery_codes()
        password_hash = self._password_hasher.hash(
            password, self._random.bytes(16)
        )
        self._repository.initialize(
            installation_id=installation_id,
            marker_reference=marker_reference,
            user_id=user_id,
            password_hash=password_hash,
            hash_format_version=PASSWORD_HASH_FORMAT_VERSION,
            recovery_set_id=recovery_set_id,
            recovery_codes=code_hashes,
            now=now,
        )
        self._marker.publish(marker_reference)
        state = self.security_store_state()
        if state.state != SecurityStoreState.READY:
            raise SecurityStateError("security_enrollment_incomplete")
        self._permissions.secure_sqlite_files(self._repository.database_path)
        return EnrollmentResult(
            installation_id,
            format_installation_id(installation_id),
            user_id,
            recovery_set_id,
            displayed_codes,
        )

    def prepare_local_account_enrollment(self, password: str) -> EnrollmentResult:
        """Create a fail-closed pending account until codes are confirmed."""
        if self.security_store_state().state != SecurityStoreState.UNINITIALIZED:
            raise SecurityStateError("security_store_not_uninitialized")
        self._password_policy.validate(password)
        now = self._now()
        installation_id = self._new_uuid4()
        marker_reference = self._new_uuid4()
        user_id = self._new_uuid4()
        recovery_set_id = self._new_uuid4()
        displayed_codes, code_hashes = self._new_recovery_codes()
        password_hash = self._password_hasher.hash(password, self._random.bytes(16))
        self._repository.initialize(
            installation_id=installation_id,
            marker_reference=marker_reference,
            user_id=user_id,
            password_hash=password_hash,
            hash_format_version=PASSWORD_HASH_FORMAT_VERSION,
            recovery_set_id=recovery_set_id,
            recovery_codes=code_hashes,
            now=now,
            pending=True,
        )
        self._marker.publish(marker_reference)
        if self.security_store_state().state != SecurityStoreState.PASSWORD_RESET_PENDING:
            raise SecurityStateError("security_enrollment_pending_incomplete")
        self._permissions.secure_sqlite_files(self._repository.database_path)
        return EnrollmentResult(
            installation_id,
            format_installation_id(installation_id),
            user_id,
            recovery_set_id,
            displayed_codes,
        )

    def confirm_local_account_enrollment(self, recovery_set_id: str) -> bool:
        self._require_state(SecurityStoreState.PASSWORD_RESET_PENDING)
        validate_uuid4(recovery_set_id)
        confirmed = self._repository.activate_pending_account(
            recovery_set_id=recovery_set_id, now=self._now()
        )
        return confirmed and self.security_store_state().state == SecurityStoreState.READY

    def current_lock_state(self) -> LockState:
        self._require_state(SecurityStoreState.READY)
        account = self._repository.load_account()
        return self._lock_state(account, recovery=False)

    def authenticate_password(self, password: str) -> AuthenticationResult:
        state = self.security_store_state().state
        if state == SecurityStoreState.PASSWORD_RESET_PENDING:
            return AuthenticationResult(AuthenticationStatus.PASSWORD_RESET_REQUIRED)
        if state != SecurityStoreState.READY:
            return AuthenticationResult(AuthenticationStatus.STORE_UNAVAILABLE)
        lock = self._lock_state(self._repository.load_account(), recovery=False)
        if lock.locked:
            return AuthenticationResult(
                AuthenticationStatus.THROTTLED, lock.remaining_seconds
            )
        account = self._repository.load_account()
        try:
            verified = self._password_hasher.verify(account.password_hash, password)
        except SecurityStoreError:
            return AuthenticationResult(AuthenticationStatus.STORE_UNAVAILABLE)
        now = self._now()
        if not verified:
            failed = self._repository.record_login_failure(now=now)
            retry = self._remaining(failed.locked_until_utc, now)
            if retry:
                self._login_monotonic_deadline = self._monotonic_clock.monotonic() + retry
            return AuthenticationResult(
                AuthenticationStatus.INVALID_CREDENTIALS, retry
            )
        replacement_hash: str | None = None
        if self._password_hasher.needs_rehash(account.password_hash):
            replacement_hash = self._password_hasher.hash(password, self._random.bytes(16))
        self._repository.record_login_success(
            now=now, replacement_hash=replacement_hash
        )
        self._login_monotonic_deadline = None
        return AuthenticationResult(
            AuthenticationStatus.AUTHENTICATED,
            password_hash_upgraded=replacement_hash is not None,
        )

    def change_password(
        self, current_password: str, replacement_password: str
    ) -> AuthenticationResult:
        self._require_state(SecurityStoreState.READY)
        lock = self.current_lock_state()
        if lock.locked:
            return AuthenticationResult(AuthenticationStatus.THROTTLED, lock.remaining_seconds)
        account = self._repository.load_account()
        if not self._password_hasher.verify(account.password_hash, current_password):
            failed = self._repository.record_login_failure(now=self._now())
            retry = self._remaining(failed.locked_until_utc, self._now())
            return AuthenticationResult(AuthenticationStatus.INVALID_CREDENTIALS, retry)
        self._password_policy.validate(replacement_password)
        replacement_hash = self._password_hasher.hash(
            replacement_password, self._random.bytes(16)
        )
        if not self._repository.change_password(
            expected_hash=account.password_hash,
            replacement_hash=replacement_hash,
            now=self._now(),
        ):
            raise SecurityStateError("password_change_raced")
        self._login_monotonic_deadline = None
        return AuthenticationResult(AuthenticationStatus.AUTHENTICATED)

    def current_recovery_lock_state(self) -> LockState:
        self._require_state(
            SecurityStoreState.READY, SecurityStoreState.PASSWORD_RESET_PENDING
        )
        return self._lock_state(self._repository.load_account(), recovery=True)

    def verify_and_consume_recovery_code(
        self, recovery_code: str
    ) -> RecoveryConsumptionResult:
        if self.security_store_state().state != SecurityStoreState.READY:
            return RecoveryConsumptionResult(RecoveryStatus.STORE_UNAVAILABLE)
        lock = self.current_recovery_lock_state()
        if lock.locked:
            return RecoveryConsumptionResult(RecoveryStatus.THROTTLED, lock.remaining_seconds)
        candidates = self._repository.active_recovery_codes()
        try:
            canonical = canonicalize_recovery_code(recovery_code)
            format_valid = True
        except RecoveryCodeError:
            canonical = self._dummy_canonical_code()
            format_valid = False
        matched_id: str | None = None
        matched_digest: bytes | None = None
        for candidate in candidates:
            candidate_digest = hash_recovery_code(candidate.salt, canonical)
            matches = hmac.compare_digest(candidate.digest, candidate_digest)
            if matches and candidate.status == "active" and format_valid:
                matched_id = candidate.recovery_code_id
                matched_digest = candidate_digest
        now = self._now()
        if matched_id is not None and matched_digest is not None:
            if self._repository.consume_recovery_code(
                recovery_code_id=matched_id,
                expected_digest=matched_digest,
                now=now,
            ):
                self._recovery_monotonic_deadline = None
                return RecoveryConsumptionResult(
                    RecoveryStatus.ACCEPTED, password_reset_required=True
                )
        failed = self._repository.record_recovery_failure(now=now)
        retry = self._remaining(failed.recovery_locked_until_utc, now)
        if retry:
            self._recovery_monotonic_deadline = self._monotonic_clock.monotonic() + retry
        return RecoveryConsumptionResult(RecoveryStatus.INVALID, retry)

    def prepare_recovery_code_regeneration(self) -> RecoveryPreparation:
        self._require_state(
            SecurityStoreState.READY, SecurityStoreState.PASSWORD_RESET_PENDING
        )
        recovery_set_id = self._new_uuid4()
        displayed, hashed = self._new_recovery_codes()
        self._repository.prepare_recovery_set(
            recovery_set_id=recovery_set_id,
            recovery_codes=hashed,
            now=self._now(),
        )
        return RecoveryPreparation(recovery_set_id, displayed)

    def confirm_recovery_code_regeneration(self, recovery_set_id: str) -> bool:
        self._require_state(
            SecurityStoreState.READY, SecurityStoreState.PASSWORD_RESET_PENDING
        )
        validate_uuid4(recovery_set_id)
        return self._repository.confirm_recovery_set(
            recovery_set_id=recovery_set_id, now=self._now()
        )

    def complete_recovery_password_reset(
        self, replacement_password: str
    ) -> RecoveryPreparation:
        prepared = self.prepare_recovery_password_reset(replacement_password)
        if not self.confirm_recovery_password_reset(prepared.recovery_set_id):
            raise SecurityStateError("password_reset_confirmation_failed")
        return prepared

    def prepare_recovery_password_reset(
        self, replacement_password: str
    ) -> RecoveryPreparation:
        self._require_state(SecurityStoreState.PASSWORD_RESET_PENDING)
        self._password_policy.validate(replacement_password)
        password_hash = self._password_hasher.hash(
            replacement_password, self._random.bytes(16)
        )
        recovery_set_id = self._new_uuid4()
        displayed, hashed = self._new_recovery_codes()
        if not self._repository.prepare_password_reset(
            replacement_hash=password_hash,
            recovery_set_id=recovery_set_id,
            recovery_codes=hashed,
            now=self._now(),
        ):
            raise SecurityStateError("password_reset_state_changed")
        self._login_monotonic_deadline = None
        self._recovery_monotonic_deadline = None
        return RecoveryPreparation(recovery_set_id, displayed)

    def confirm_recovery_password_reset(self, recovery_set_id: str) -> bool:
        self._require_state(SecurityStoreState.PASSWORD_RESET_PENDING)
        validate_uuid4(recovery_set_id)
        confirmed = self._repository.confirm_password_reset(
            recovery_set_id=recovery_set_id, now=self._now()
        )
        return confirmed and self.security_store_state().state == SecurityStoreState.READY

    def _lock_state(self, account: AccountRecord, *, recovery: bool) -> LockState:
        now = self._now()
        monotonic_now = self._monotonic_clock.monotonic()
        last_observed = (
            account.recovery_last_observed_utc if recovery else account.last_observed_utc
        )
        locked_until = (
            account.recovery_locked_until_utc if recovery else account.locked_until_utc
        )
        failure_count = (
            account.recovery_failed_attempts if recovery else account.failed_attempts
        )
        rollback = bool(last_observed and last_observed - now > _CLOCK_ROLLBACK_TOLERANCE)
        if rollback:
            conservative_until = now + _CLOCK_ROLLBACK_LOCK
            if recovery:
                account = self._repository.update_observed_recovery_time(
                    observed=now, locked_until=conservative_until
                )
                self._recovery_monotonic_deadline = monotonic_now + 300
            else:
                account = self._repository.update_observed_login_time(
                    observed=now, locked_until=conservative_until
                )
                self._login_monotonic_deadline = monotonic_now + 300
            return LockState(True, 300, failure_count, True)
        if recovery:
            self._repository.update_observed_recovery_time(observed=now)
            monotonic_deadline = self._recovery_monotonic_deadline
        else:
            self._repository.update_observed_login_time(observed=now)
            monotonic_deadline = self._login_monotonic_deadline
        utc_remaining = self._remaining(locked_until, now)
        if utc_remaining and monotonic_deadline is None:
            monotonic_deadline = monotonic_now + utc_remaining
            if recovery:
                self._recovery_monotonic_deadline = monotonic_deadline
            else:
                self._login_monotonic_deadline = monotonic_deadline
        monotonic_remaining = max(
            0, math.ceil((monotonic_deadline or monotonic_now) - monotonic_now)
        )
        remaining = max(utc_remaining, monotonic_remaining)
        return LockState(remaining > 0, remaining, failure_count, False)

    def _new_recovery_codes(
        self,
    ) -> tuple[tuple[str, ...], tuple[RecoveryCodeHash, ...]]:
        displayed: list[str] = []
        hashed: list[RecoveryCodeHash] = []
        canonicals: set[str] = set()
        while len(displayed) < RECOVERY_CODE_COUNT:
            shown, canonical = format_recovery_code(
                self._random.bytes(RECOVERY_CODE_ENTROPY_BYTES)
            )
            if canonical in canonicals:
                continue
            canonicals.add(canonical)
            salt = self._random.bytes(RECOVERY_CODE_SALT_BYTES)
            displayed.append(shown)
            hashed.append(
                RecoveryCodeHash(
                    self._new_uuid4(), salt, hash_recovery_code(salt, canonical)
                )
            )
        return tuple(displayed), tuple(hashed)

    def _new_uuid4(self) -> str:
        return validate_uuid4(self._random.uuid4())

    def _require_state(self, *allowed: SecurityStoreState) -> None:
        state = self.security_store_state().state
        if state not in allowed:
            raise SecurityStateError(f"security_state_{state.value}")

    def _now(self) -> datetime:
        now = self._utc_clock.utc_now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise SecurityStoreError("utc_clock_returned_naive_time")
        return now.astimezone(timezone.utc)

    @staticmethod
    def _remaining(locked_until: datetime | None, now: datetime) -> int:
        if locked_until is None:
            return 0
        return max(0, math.ceil((locked_until - now).total_seconds()))

    @staticmethod
    def _dummy_canonical_code() -> str:
        _shown, canonical = format_recovery_code(b"\x00" * RECOVERY_CODE_ENTROPY_BYTES)
        return canonical
