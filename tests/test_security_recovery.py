"""Recovery-code format, storage, concurrency and rotation contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
import sqlite3
import uuid
from unittest.mock import Mock

import src.security.infrastructure.sqlite_repository as repository_module

import pytest

from src.desktop_app.runtime import runtime_paths
from src.security.application import SecurityApplicationService
from src.security.domain import (
    AuthenticationStatus,
    RecoveryCodeError,
    RecoveryStatus,
    SecurityStoreState,
    canonicalize_recovery_code,
    format_recovery_code,
)
from src.security.infrastructure import (
    Argon2idPasswordHasher,
    EnrollmentMarkerFile,
    PlatformFilePermissionManager,
    SQLiteSecurityRepository,
)


PASSWORD = "dies ist eine sichere Recovery Testpassphrase"
NEW_PASSWORD = "dies ist eine neue Recovery Testpassphrase"
FIXED_NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


class DeterministicRandom:
    def __init__(self, seed: bytes = b"recovery-test") -> None:
        self.seed = seed
        self.counter = 0

    def bytes(self, length: int) -> bytes:
        result = b""
        while len(result) < length:
            self.counter += 1
            result += hashlib.sha256(
                self.seed + self.counter.to_bytes(8, "big")
            ).digest()
        return result[:length]

    def uuid4(self) -> str:
        raw = bytearray(self.bytes(16))
        raw[6] = (raw[6] & 0x0F) | 0x40
        raw[8] = (raw[8] & 0x3F) | 0x80
        return str(uuid.UUID(bytes=bytes(raw)))


class MutableClock:
    def __init__(self) -> None:
        self.now = FIXED_NOW
        self.monotonic_value = 500.0

    def utc_now(self) -> datetime:
        return self.now

    def monotonic(self) -> float:
        return self.monotonic_value

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)
        self.monotonic_value += seconds


class ToggleFailure:
    def __init__(self) -> None:
        self.point: str | None = None

    def __call__(self, point: str) -> None:
        if point == self.point:
            raise RuntimeError("injected recovery transaction failure")


def make_service(
    root: Path,
    *,
    clock: MutableClock | None = None,
    random_source: DeterministicRandom | None = None,
    failure: ToggleFailure | None = None,
) -> tuple[SecurityApplicationService, SQLiteSecurityRepository, MutableClock]:
    paths = runtime_paths(root)
    permissions = PlatformFilePermissionManager()
    repository = SQLiteSecurityRepository(
        paths.security_database,
        permissions,
        failure_injector=failure,
    )
    clock = clock or MutableClock()
    service = SecurityApplicationService(
        repository=repository,
        marker=EnrollmentMarkerFile(paths.enrollment_marker, permissions),
        password_hasher=Argon2idPasswordHasher(),
        random_source=random_source or DeterministicRandom(),
        utc_clock=clock,
        monotonic_clock=clock,
        permissions=permissions,
    )
    return service, repository, clock


def enroll(root: Path, **kwargs):
    service, repository, clock = make_service(root, **kwargs)
    result = service.enroll_local_account(PASSWORD)
    return service, repository, clock, result


def test_recovery_format_has_80_bit_payload_and_check_symbol() -> None:
    displayed, canonical = format_recovery_code(bytes(range(10)))
    assert displayed.startswith("JKM1-")
    assert [len(part) for part in displayed.split("-")] == [4, 4, 4, 4, 4, 1]
    assert len(canonical) == 21
    assert canonicalize_recovery_code(displayed) == canonical
    assert canonicalize_recovery_code(displayed.lower()) == canonical
    assert canonicalize_recovery_code(displayed.replace("-", " ")) == canonical
    assert canonicalize_recovery_code(displayed.replace("-", "")) == canonical


def test_recovery_normalization_maps_only_ascii_aliases_and_rejects_lookalikes() -> None:
    zero_display, zero_canonical = format_recovery_code(b"\x00" * 10)
    assert canonicalize_recovery_code(zero_display.replace("0", "O", 1)) == zero_canonical
    one_display, one_canonical = format_recovery_code(b"\x08" + b"\x00" * 9)
    payload_alias = one_display.replace("1", "L", 1)
    assert canonicalize_recovery_code(payload_alias) == one_canonical
    with pytest.raises(RecoveryCodeError):
        canonicalize_recovery_code(zero_display.replace("J", "Ｊ", 1))
    with pytest.raises(RecoveryCodeError):
        canonicalize_recovery_code(zero_display[:-1] + "Z")


def test_large_deterministic_recovery_sample_has_no_duplicates() -> None:
    codes = {
        format_recovery_code(index.to_bytes(10, "big"))[1]
        for index in range(10_000)
    }
    assert len(codes) == 10_000


def test_store_contains_only_individually_salted_recovery_hashes(tmp_path: Path) -> None:
    service, repository, _clock, result = enroll(tmp_path / "runtime")
    database_bytes = repository.database_path.read_bytes()
    assert PASSWORD.encode("utf-8") not in database_bytes
    for code in result.recovery_codes:
        assert code.encode("ascii") not in database_bytes
        assert canonicalize_recovery_code(code).encode("ascii") not in database_bytes
    with sqlite3.connect(repository.database_path) as connection:
        rows = connection.execute(
            "SELECT salt, code_hash, format_version FROM recovery_codes"
        ).fetchall()
        assert len(rows) == 10
        assert len({bytes(row[0]) for row in rows}) == 10
        assert all(len(bytes(row[0])) == 16 for row in rows)
        assert all(len(bytes(row[1])) == 32 for row in rows)
        assert all(row[2] == 1 for row in rows)


def test_recovery_code_is_once_only_and_forces_password_reset(tmp_path: Path) -> None:
    service, _repository, _clock, enrolled = enroll(tmp_path / "runtime")
    accepted = service.verify_and_consume_recovery_code(enrolled.recovery_codes[0])
    assert accepted.status == RecoveryStatus.ACCEPTED
    assert accepted.password_reset_required
    assert service.security_store_state().state == SecurityStoreState.PASSWORD_RESET_PENDING
    assert service.authenticate_password(PASSWORD).status == AuthenticationStatus.PASSWORD_RESET_REQUIRED
    replacement = service.complete_recovery_password_reset(NEW_PASSWORD)
    assert len(replacement.recovery_codes) == 10
    assert service.security_store_state().state == SecurityStoreState.READY
    assert service.authenticate_password(NEW_PASSWORD).status == AuthenticationStatus.AUTHENTICATED
    assert (
        service.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status
        == RecoveryStatus.INVALID
    )


def test_two_phase_regeneration_keeps_old_set_until_confirmation(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    service, _repository, clock, enrolled = enroll(root)
    prepared = service.prepare_recovery_code_regeneration()
    assert len(prepared.recovery_codes) == 10

    reopened, _repository, _clock = make_service(root, clock=clock)
    assert reopened.confirm_recovery_code_regeneration(prepared.recovery_set_id)
    assert (
        reopened.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status
        == RecoveryStatus.INVALID
    )
    assert (
        reopened.verify_and_consume_recovery_code(prepared.recovery_codes[0]).status
        == RecoveryStatus.ACCEPTED
    )


def test_crash_before_regeneration_confirmation_leaves_old_set_valid(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    service, _repository, clock, enrolled = enroll(root)
    prepared = service.prepare_recovery_code_regeneration()
    assert prepared.recovery_set_id
    reopened, _repository, _clock = make_service(root, clock=clock)
    assert (
        reopened.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status
        == RecoveryStatus.ACCEPTED
    )


def test_regeneration_activation_rolls_back_as_one_transaction(tmp_path: Path) -> None:
    failure = ToggleFailure()
    root = tmp_path / "runtime"
    service, _repository, _clock, enrolled = enroll(root, failure=failure)
    prepared = service.prepare_recovery_code_regeneration()
    failure.point = "before_write_commit"
    with pytest.raises(RuntimeError, match="injected"):
        service.confirm_recovery_code_regeneration(prepared.recovery_set_id)
    failure.point = None
    assert (
        service.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status
        == RecoveryStatus.ACCEPTED
    )


def test_regeneration_crash_after_commit_has_complete_new_active_set(
    tmp_path: Path,
) -> None:
    failure = ToggleFailure()
    root = tmp_path / "runtime"
    service, _repository, _clock, enrolled = enroll(root, failure=failure)
    prepared = service.prepare_recovery_code_regeneration()
    failure.point = "after_write_commit"
    with pytest.raises(RuntimeError, match="injected"):
        service.confirm_recovery_code_regeneration(prepared.recovery_set_id)
    failure.point = None
    assert (
        service.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status
        == RecoveryStatus.INVALID
    )
    assert (
        service.verify_and_consume_recovery_code(prepared.recovery_codes[0]).status
        == RecoveryStatus.ACCEPTED
    )


@pytest.mark.parametrize("attempt", range(20))
def test_concurrent_double_consumption_has_exactly_one_winner(tmp_path: Path, attempt: int) -> None:
    root = tmp_path / "runtime"
    first, _repository, clock, enrolled = enroll(root)
    second, _repository, _clock = make_service(
        root, clock=clock, random_source=DeterministicRandom(b"second")
    )
    code = enrolled.recovery_codes[0]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.map(lambda service: service.verify_and_consume_recovery_code(code), (first, second))
        )
    assert sum(result.status == RecoveryStatus.ACCEPTED for result in results) == 1


def test_recovery_throttling_is_separate_persistent_and_bounded(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    service, repository, clock, _enrolled = enroll(root)
    retries = []
    for _attempt in range(9):
        result = service.verify_and_consume_recovery_code("not a recovery code")
        retries.append(result.retry_after_seconds)
        if result.retry_after_seconds:
            clock.advance(result.retry_after_seconds)
    assert retries == [0, 0, 0, 0, 30, 60, 120, 240, 300]
    account = repository.load_account()
    assert account.recovery_failed_attempts == 9
    assert account.failed_attempts == 0
    reopened, reopened_repository, _clock = make_service(root, clock=clock)
    assert reopened_repository.load_account().recovery_failed_attempts == 9
    assert reopened.current_recovery_lock_state().locked is False


def test_recovery_results_repr_and_process_output_do_not_expose_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    service, _repository, _clock, result = enroll(tmp_path / "runtime")
    prepared = service.prepare_recovery_code_regeneration()
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""
    for code in (*result.recovery_codes, *prepared.recovery_codes):
        assert code not in repr(result)
        assert code not in repr(prepared)


@pytest.mark.parametrize("code", (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))
def test_wal_setup_retries_transient_contention_only(monkeypatch, code) -> None:
    error = sqlite3.OperationalError("transient test contention")
    error.sqlite_errorcode = code
    connection = Mock()
    connection.execute.side_effect = (error, None)
    sleep = Mock()
    monkeypatch.setattr(repository_module.time, "sleep", sleep)
    monkeypatch.setattr(repository_module.time, "monotonic", lambda: 100.0)
    SQLiteSecurityRepository._enable_wal_mode(connection)
    assert connection.execute.call_count == 2
    sleep.assert_called_once_with(0.01)


@pytest.mark.parametrize("code", (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_IOERR))
def test_wal_setup_expires_or_preserves_non_lock_errors(monkeypatch, code) -> None:
    error = sqlite3.OperationalError("test failure")
    error.sqlite_errorcode = code
    connection = Mock()
    connection.execute.side_effect = error
    ticks = iter((100.0, 105.0))
    monkeypatch.setattr(repository_module.time, "monotonic", lambda: next(ticks))
    sleep = Mock()
    monkeypatch.setattr(repository_module.time, "sleep", sleep)
    with pytest.raises(sqlite3.OperationalError) as caught:
        SQLiteSecurityRepository._enable_wal_mode(connection)
    assert caught.value is error
    assert connection.execute.call_count == 1
    sleep.assert_not_called()


def test_failed_write_connection_setup_closes_new_connection(tmp_path, monkeypatch) -> None:
    _service, repository, _clock, _enrolled = enroll(tmp_path / "runtime")
    error = sqlite3.OperationalError("test IO failure")
    error.sqlite_errorcode = sqlite3.SQLITE_IOERR
    connection = Mock()
    connection.execute.side_effect = (None, error)
    monkeypatch.setattr(repository, "_ensure_current_schema", lambda: None)
    monkeypatch.setattr(repository_module.sqlite3, "connect", lambda *args, **kwargs: connection)
    with pytest.raises(sqlite3.OperationalError) as caught:
        repository._connect_write()
    assert caught.value is error
    connection.close.assert_called_once_with()
