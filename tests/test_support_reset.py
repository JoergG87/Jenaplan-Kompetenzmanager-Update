"""Offline support-reset serialization, binding, migration and reset contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from src.application.commands.backup import BackupApplicationService, CreateBackupCommand
from src.application.commands.security_backup import VerifiedSecurityBackupAdapter
from src.core.final_v4_schema import FinalV4SchemaInitializer
from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.runtime import runtime_paths
from src.security.application import SecurityApplicationService
from src.security.domain import (
    AuthenticationStatus,
    DeviceCredential,
    DeviceCredentialStatus,
    SecurityBackupProof,
    SecurityStoreError,
    SecurityStoreState,
    SupportPublicKey,
    SupportPublicKeyStatus,
    SupportResetFailureCode,
    SupportResetPayload,
    SupportResetRejected,
)
from src.security.infrastructure import (
    Argon2idPasswordHasher,
    Ed25519SignatureVerifier,
    EnrollmentMarkerFile,
    PlatformFilePermissionManager,
    PublicKeyRegistry,
    SQLiteSecurityRepository,
)
from src.security.support_reset import SupportResetService, SupportResetTokenCodec


PASSWORD = "dies ist eine sichere Support Reset Testpassphrase"
NOW = datetime(2026, 7, 17, 14, 0, tzinfo=UTC)


class DeterministicRandom:
    def __init__(self, seed: bytes = b"support-reset") -> None:
        self.seed = seed
        self.counter = 0

    def bytes(self, length: int) -> bytes:
        output = b""
        while len(output) < length:
            self.counter += 1
            output += hashlib.sha256(
                self.seed + self.counter.to_bytes(8, "big")
            ).digest()
        return output[:length]

    def uuid4(self) -> str:
        raw = bytearray(self.bytes(16))
        raw[6] = (raw[6] & 0x0F) | 0x40
        raw[8] = (raw[8] & 0x3F) | 0x80
        return str(uuid.UUID(bytes=bytes(raw)))


class MutableClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now
        self.monotonic_value = 100.0

    def utc_now(self) -> datetime:
        return self.now

    def monotonic(self) -> float:
        return self.monotonic_value


class ToggleFailure:
    def __init__(self) -> None:
        self.point: str | None = None

    def __call__(self, point: str) -> None:
        if point == self.point:
            raise RuntimeError(f"injected failure at {point}")


class BackupPort:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0
        self.finish_calls: list[bool] = []
        self._lock = threading.Lock()

    def create_and_verify(self) -> SecurityBackupProof:
        with self._lock:
            self.calls += 1
        if self.error is not None:
            raise self.error
        return SecurityBackupProof("/tmp/verified-security-backup.jkmbackup", "a" * 64)

    def finish(self, *, reset_committed: bool) -> None:
        self.finish_calls.append(reset_committed)


def make_environment(
    root: Path,
    *,
    clock: MutableClock | None = None,
    random_source: DeterministicRandom | None = None,
    failure: ToggleFailure | None = None,
    private_key: Ed25519PrivateKey | None = None,
    key_status: SupportPublicKeyStatus = SupportPublicKeyStatus.ACTIVE,
    key_id: str = "support-2026-a",
) -> tuple[
    SecurityApplicationService,
    SupportResetService,
    SQLiteSecurityRepository,
    MutableClock,
    Ed25519PrivateKey,
]:
    paths = runtime_paths(root)
    permissions = PlatformFilePermissionManager()
    repository = SQLiteSecurityRepository(
        paths.security_database, permissions, failure_injector=failure
    )
    clock = clock or MutableClock()
    random_source = random_source or DeterministicRandom()
    marker = EnrollmentMarkerFile(paths.enrollment_marker, permissions)
    security = SecurityApplicationService(
        repository=repository,
        marker=marker,
        password_hasher=Argon2idPasswordHasher(),
        random_source=random_source,
        utc_clock=clock,
        monotonic_clock=clock,
        permissions=permissions,
    )
    if not repository.exists():
        security.enroll_local_account(PASSWORD)
    private_key = private_key or Ed25519PrivateKey.generate()
    raw_public = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    registry = PublicKeyRegistry(
        (
            SupportPublicKey(
                key_id,
                raw_public,
                key_status,
                NOW - timedelta(days=1),
                NOW + timedelta(days=30),
            ),
        )
    )
    reset = SupportResetService(
        repository=repository,
        marker=marker,
        random_source=random_source,
        utc_clock=clock,
        key_registry=registry,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    return security, reset, repository, clock, private_key


def signed_token(
    request,
    private_key: Ed25519PrivateKey,
    *,
    key_id: str = "support-2026-a",
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    **changes,
) -> str:
    created_at = created_at or request.created_at
    payload = SupportResetPayload(
        format_version=1,
        algorithm="Ed25519",
        key_id=key_id,
        installation_id=request.installation_id,
        user_id=request.user_id,
        reset_request_id=request.reset_request_id,
        action=request.action,
        created_at=created_at,
        expires_at=expires_at or created_at + timedelta(minutes=30),
        nonce=request.nonce,
    )
    payload = replace(payload, **changes)
    canonical = SupportResetTokenCodec.canonical_payload_bytes(payload)
    return SupportResetTokenCodec.encode(payload, private_key.sign(canonical))


def token_with_payload_bytes(payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = base64.urlsafe_b64encode(b"x" * 64).decode("ascii").rstrip("=")
    return f"JKM-SR1.{encoded}.{signature}"


def security_snapshot(path: Path) -> tuple:
    with sqlite3.connect(path) as connection:
        return tuple(connection.iterdump())


def test_canonical_payload_is_deterministic_and_has_fixed_field_order(tmp_path: Path) -> None:
    _security, reset, _repository, _clock, private = make_environment(tmp_path / "runtime")
    request = reset.create_request()
    token = signed_token(request, private)
    payload, canonical, signature = SupportResetTokenCodec.decode(token)
    assert canonical == SupportResetTokenCodec.canonical_payload_bytes(payload)
    assert len(signature) == 64
    assert tuple(json.loads(canonical).keys()) == (
        "format_version", "algorithm", "key_id", "installation_id", "user_id",
        "reset_request_id", "action", "created_at", "expires_at", "nonce",
    )
    assert canonical == SupportResetTokenCodec.canonical_payload_bytes(payload)


def test_token_input_normalizes_only_outer_ascii_whitespace(tmp_path: Path) -> None:
    _security, reset, repository, _clock, private = make_environment(tmp_path / "runtime")
    request = reset.create_request()
    token = signed_token(request, private)
    before = security_snapshot(repository.database_path)
    verified = reset.verify_token(f" \t{token}\r\n")
    assert verified.reset_request_id == request.reset_request_id
    assert security_snapshot(repository.database_path) == before
    with pytest.raises(SupportResetRejected):
        reset.verify_token(token.replace(".", ". ", 1))


def test_preview_verification_never_consumes_request_or_creates_backup(tmp_path: Path) -> None:
    _security, reset, repository, _clock, private = make_environment(tmp_path / "runtime")
    assert reset.product_enabled is True
    request = reset.create_request()
    token = signed_token(request, private)
    before = security_snapshot(repository.database_path)
    result = reset.verify_token(token)
    assert result.key_id == "support-2026-a"
    assert result.expires_at == request.created_at + timedelta(minutes=30)
    assert repository.load_support_reset_request(request.reset_request_id).status == "active"
    assert security_snapshot(repository.database_path) == before


def test_support_reset_request_never_contains_local_display_name(tmp_path: Path) -> None:
    _security, reset, _repository, _clock, _private = make_environment(tmp_path / "runtime")
    preferences = tmp_path / "runtime" / "app-preferences.json"
    preferences.write_text(
        '{"display_name":"Laura","format_version":1,"inactivity_minutes":15}\n',
        encoding="utf-8",
    )
    before = preferences.read_bytes()
    request = reset.create_request()
    encoded = SupportResetTokenCodec.canonical_request_bytes(request)
    assert b"Laura" not in encoded
    assert b"display_name" not in encoded
    assert preferences.read_bytes() == before


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (lambda raw: raw.replace(b'{"format_version"', b'{ "format_version"'), SupportResetFailureCode.PAYLOAD_NOT_CANONICAL),
        (lambda raw: raw.replace(b'"format_version":1', b'"format_version":1.0'), SupportResetFailureCode.JSON_INVALID),
        (lambda raw: raw.replace(b'"algorithm"', b'"unknown"'), SupportResetFailureCode.FIELDS_INVALID),
        (lambda raw: raw.replace(b'"algorithm":"Ed25519"', b'"format_version":1,"algorithm":"Ed25519"'), SupportResetFailureCode.FIELDS_INVALID),
        (lambda raw: raw.replace(b'.000000Z', b'Z', 1), SupportResetFailureCode.FIELDS_INVALID),
    ],
)
def test_noncanonical_unknown_duplicate_float_and_time_are_rejected(
    tmp_path: Path, mutator, code: SupportResetFailureCode
) -> None:
    _security, reset, _repository, _clock, private = make_environment(tmp_path / code.value)
    request = reset.create_request()
    valid = signed_token(request, private)
    _payload, canonical, _signature = SupportResetTokenCodec.decode(valid)
    with pytest.raises(SupportResetRejected) as caught:
        SupportResetTokenCodec.decode(token_with_payload_bytes(mutator(canonical)))
    assert caught.value.code == code
    assert str(caught.value) == "support_reset_rejected"


def test_invalid_utf8_base64url_and_size_are_rejected() -> None:
    with pytest.raises(SupportResetRejected) as utf8:
        SupportResetTokenCodec.decode(token_with_payload_bytes(b"\xff"))
    assert utf8.value.code == SupportResetFailureCode.JSON_INVALID
    with pytest.raises(SupportResetRejected) as base64_error:
        SupportResetTokenCodec.decode("JKM-SR1.abc=." + "eA" * 32)
    assert base64_error.value.code == SupportResetFailureCode.BASE64URL_INVALID
    with pytest.raises(SupportResetRejected) as size:
        SupportResetTokenCodec.decode("J" * 8193)
    assert size.value.code == SupportResetFailureCode.FORMAT_INVALID


def test_request_is_deterministic_uuid_nonce_once_active_and_max_24h(tmp_path: Path) -> None:
    _security, reset, repository, _clock, _private = make_environment(tmp_path / "runtime")
    first = reset.create_request()
    second = reset.create_request()
    assert uuid.UUID(first.reset_request_id).version == 4
    assert len(base64.urlsafe_b64decode(first.nonce + "==")) == 32
    assert second.expires_at - second.created_at == timedelta(hours=24)
    assert repository.load_support_reset_request(first.reset_request_id).status == "revoked"
    assert repository.load_support_reset_request(second.reset_request_id).status == "active"
    with pytest.raises(Exception):
        reset.create_request(duration=timedelta(hours=24, seconds=1))


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"installation_id": "11111111-1111-4111-8111-111111111111"}, SupportResetFailureCode.INSTALLATION_MISMATCH),
        ({"user_id": "22222222-2222-4222-8222-222222222222"}, SupportResetFailureCode.USER_MISMATCH),
        ({"reset_request_id": "33333333-3333-4333-8333-333333333333"}, SupportResetFailureCode.REQUEST_MISMATCH),
        ({"nonce": base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("=")}, SupportResetFailureCode.NONCE_MISMATCH),
        ({"action": "different_action"}, SupportResetFailureCode.ACTION_UNSUPPORTED),
    ],
)
def test_full_request_binding_is_enforced(tmp_path: Path, change: dict, code) -> None:
    _security, reset, _repository, _clock, private = make_environment(tmp_path / code.value)
    request = reset.create_request()
    token = signed_token(request, private, **change)
    backup = BackupPort()
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(token, backup=backup)
    assert caught.value.code == code
    assert backup.calls == 0


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (SupportPublicKeyStatus.REVOKED, SupportResetFailureCode.KEY_REVOKED),
        (SupportPublicKeyStatus.RETIRED, SupportResetFailureCode.KEY_NOT_ACTIVE),
    ],
)
def test_non_active_key_is_rejected_before_signature(tmp_path: Path, status, code) -> None:
    _security, reset, _repository, _clock, private = make_environment(
        tmp_path / "runtime", key_status=status
    )
    request = reset.create_request()
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(signed_token(request, private), backup=BackupPort())
    assert caught.value.code == code


def test_unknown_wrong_expired_and_rotating_keys(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    _security, reset, repository, clock, private = make_environment(root)
    request = reset.create_request()
    unknown = signed_token(request, private, key_id="unknown-key")
    backup = BackupPort()
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(unknown, backup=backup)
    assert caught.value.code == SupportResetFailureCode.KEY_UNKNOWN
    assert backup.calls == 0

    other = Ed25519PrivateKey.generate()
    wrong = signed_token(request, other)
    backup = BackupPort()
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(wrong, backup=backup)
    assert caught.value.code == SupportResetFailureCode.SIGNATURE_INVALID
    assert backup.calls == 0

    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    retiring = SupportResetService(
        repository=repository,
        marker=EnrollmentMarkerFile(runtime_paths(root).enrollment_marker, PlatformFilePermissionManager()),
        random_source=DeterministicRandom(b"rotation"),
        utc_clock=clock,
        key_registry=PublicKeyRegistry((SupportPublicKey(
            "support-2026-a", raw, SupportPublicKeyStatus.RETIRING,
            NOW - timedelta(days=2), NOW + timedelta(days=1),
        ),)),
        signature_verifier=Ed25519SignatureVerifier(),
    )
    assert retiring.execute(signed_token(request, private), backup=BackupPort()).security_epoch == 2


def test_key_validity_window_and_empty_registry_are_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    _security, reset, repository, clock, private = make_environment(root)
    request = reset.create_request()
    token = signed_token(request, private)
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    marker = EnrollmentMarkerFile(
        runtime_paths(root).enrollment_marker, PlatformFilePermissionManager()
    )
    for record, code in (
        (
            SupportPublicKey("support-2026-a", raw, SupportPublicKeyStatus.ACTIVE, NOW + timedelta(seconds=1), NOW + timedelta(days=1)),
            SupportResetFailureCode.KEY_NOT_YET_VALID,
        ),
        (
            SupportPublicKey("support-2026-a", raw, SupportPublicKeyStatus.ACTIVE, NOW - timedelta(days=1), NOW - timedelta(seconds=1)),
            SupportResetFailureCode.KEY_EXPIRED,
        ),
    ):
        service = SupportResetService(
            repository=repository,
            marker=marker,
            random_source=DeterministicRandom(code.value.encode()),
            utc_clock=clock,
            key_registry=PublicKeyRegistry((record,)),
            signature_verifier=Ed25519SignatureVerifier(),
        )
        with pytest.raises(SupportResetRejected) as caught:
            service.execute(token, backup=BackupPort())
        assert caught.value.code == code
    empty = SupportResetService(
        repository=repository,
        marker=marker,
        random_source=DeterministicRandom(b"empty"),
        utc_clock=clock,
        key_registry=PublicKeyRegistry(),
        signature_verifier=Ed25519SignatureVerifier(),
    )
    with pytest.raises(SupportResetRejected) as caught:
        empty.execute(token, backup=BackupPort())
    assert caught.value.code == SupportResetFailureCode.KEY_UNKNOWN


def test_algorithm_version_payload_and_signature_tampering_are_rejected(tmp_path: Path) -> None:
    _security, reset, _repository, _clock, private = make_environment(tmp_path / "runtime")
    request = reset.create_request()
    valid = signed_token(request, private)
    payload, canonical, signature = SupportResetTokenCodec.decode(valid)

    algorithm_token = signed_token(request, private, algorithm="Ed448")
    with pytest.raises(SupportResetRejected) as algorithm:
        reset.execute(algorithm_token, backup=BackupPort())
    assert algorithm.value.code == SupportResetFailureCode.ALGORITHM_UNSUPPORTED

    version_bytes = canonical.replace(b'"format_version":1', b'"format_version":2')
    with pytest.raises(SupportResetRejected) as version:
        SupportResetTokenCodec.decode(token_with_payload_bytes(version_bytes))
    assert version.value.code == SupportResetFailureCode.VERSION_UNSUPPORTED

    tampered_payload = replace(payload, expires_at=payload.expires_at - timedelta(seconds=1))
    with pytest.raises(SupportResetRejected) as tampered:
        reset.execute(
            SupportResetTokenCodec.encode(tampered_payload, signature),
            backup=BackupPort(),
        )
    assert tampered.value.code == SupportResetFailureCode.SIGNATURE_INVALID

    damaged = bytearray(signature)
    damaged[-1] ^= 1
    with pytest.raises(SupportResetRejected) as damaged_signature:
        reset.execute(
            SupportResetTokenCodec.encode(payload, bytes(damaged)), backup=BackupPort()
        )
    assert damaged_signature.value.code == SupportResetFailureCode.SIGNATURE_INVALID


@pytest.mark.parametrize(
    ("offset_seconds", "accepted", "code"),
    [
        (-120, True, None),
        (-121, False, SupportResetFailureCode.TOKEN_NOT_YET_VALID),
        (30 * 60 + 120, True, None),
        (30 * 60 + 121, False, SupportResetFailureCode.TOKEN_EXPIRED),
    ],
)
def test_two_minute_clock_tolerance(
    tmp_path: Path, offset_seconds: int, accepted: bool, code
) -> None:
    clock = MutableClock()
    _security, reset, _repository, _clock, private = make_environment(
        tmp_path / str(offset_seconds), clock=clock
    )
    request = reset.create_request()
    token = signed_token(request, private)
    clock.now = request.created_at + timedelta(seconds=offset_seconds)
    if accepted:
        assert reset.execute(token, backup=BackupPort()).security_epoch == 2
    else:
        with pytest.raises(SupportResetRejected) as caught:
            reset.execute(token, backup=BackupPort())
        assert caught.value.code == code


def test_token_lifetime_is_at_most_two_hours(tmp_path: Path) -> None:
    _security, reset, _repository, _clock, private = make_environment(tmp_path / "runtime")
    request = reset.create_request()
    token = signed_token(
        request, private, expires_at=request.created_at + timedelta(hours=2, seconds=1)
    )
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(token, backup=BackupPort())
    assert caught.value.code == SupportResetFailureCode.TOKEN_LIFETIME_INVALID


def test_expired_request_is_rejected_even_while_token_is_still_current(tmp_path: Path) -> None:
    clock = MutableClock()
    _security, reset, _repository, _clock, private = make_environment(
        tmp_path / "runtime", clock=clock
    )
    request = reset.create_request(duration=timedelta(minutes=5))
    token = signed_token(request, private)
    clock.now = request.expires_at + timedelta(minutes=3)
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(token, backup=BackupPort())
    assert caught.value.code == SupportResetFailureCode.REQUEST_EXPIRED


def test_request_creation_requires_bound_marker_and_active_account(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    _security, reset, repository, _clock, _private = make_environment(root)
    paths = runtime_paths(root)
    paths.enrollment_marker.write_text(
        '{"format_version":1,"marker_reference":"44444444-4444-4444-8444-444444444444"}\n',
        encoding="utf-8",
    )
    with pytest.raises(SupportResetRejected) as caught:
        reset.create_request()
    assert caught.value.code == SupportResetFailureCode.STORE_UNAVAILABLE
    assert repository.security_epoch() == 1


def test_successful_reset_requires_backup_and_changes_only_security_state(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    main_database = root / "kompetenzmanager.sqlite"
    document = root / "documents" / "unchanged.bin"
    document.parent.mkdir(parents=True)
    main_database.write_bytes(b"fachliche-db-unveraendert")
    document.write_bytes(b"dokument-unveraendert")
    app_preferences = root / "app-preferences.json"
    app_preferences.write_text(
        '{"display_name":"Laura","format_version":1,"inactivity_minutes":15}\n',
        encoding="utf-8",
    )
    app_preferences_before = app_preferences.read_bytes()
    security, reset, repository, _clock, private = make_environment(root)
    account_record = repository.load_account()
    device_credential = DeviceCredential(
        credential_id=str(uuid.uuid4()),
        installation_id=account_record.installation_id,
        user_id=account_record.user_id,
        device_label="Dieser Mac",
        salt=b"s" * 16,
        secret_hash=b"h" * 32,
        hash_format_version=1,
        security_epoch_at_issue=repository.security_epoch(),
        created_at=NOW,
        last_used_at=None,
        revoked_at=None,
        status=DeviceCredentialStatus.PENDING,
    )
    repository.prepare_device_credential(device_credential)
    repository.activate_device_credential(
        credential_id=device_credential.credential_id, now=NOW
    )
    enrolled_codes = security.prepare_recovery_code_regeneration()
    request = reset.create_request()
    token = signed_token(request, private)
    backup = BackupPort()
    result = reset.execute(token, backup=backup)
    assert backup.calls == 1
    assert backup.finish_calls == [True]
    assert result.security_epoch == 2
    assert repository.security_epoch() == 2
    assert security.security_store_state().state == SecurityStoreState.PASSWORD_RESET_PENDING
    assert security.authenticate_password(PASSWORD).status == AuthenticationStatus.PASSWORD_RESET_REQUIRED
    assert repository.load_support_reset_request(request.reset_request_id).status == "consumed"
    with sqlite3.connect(repository.database_path) as connection:
        account = connection.execute(
            "SELECT password_hash, failed_attempts, locked_until_utc, recovery_failed_attempts, recovery_locked_until_utc FROM local_accounts"
        ).fetchone()
        assert account == ("!password-reset-pending!", 0, None, 0, None)
        assert connection.execute(
            "SELECT COUNT(*) FROM recovery_code_sets WHERE status IN ('active', 'pending')"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM recovery_codes WHERE status = 'active'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT status FROM device_credentials WHERE credential_id = ?",
            (device_credential.credential_id,),
        ).fetchone()[0] == "revoked"
        assert connection.execute(
            "SELECT length(token_digest), key_id, action, status FROM support_reset_token_uses"
        ).fetchone() == (32, "support-2026-a", "reset_local_password_v1", "consumed")
    assert enrolled_codes.recovery_codes
    assert main_database.read_bytes() == b"fachliche-db-unveraendert"
    assert document.read_bytes() == b"dokument-unveraendert"
    assert app_preferences.read_bytes() == app_preferences_before
    with pytest.raises(SupportResetRejected) as reused:
        reset.execute(token, backup=BackupPort())
    assert reused.value.code in {
        SupportResetFailureCode.TOKEN_ALREADY_USED,
        SupportResetFailureCode.REQUEST_NOT_ACTIVE,
    }


def test_real_jkmbackup_is_created_verified_and_excludes_security_store(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    paths = runtime_paths(root)
    for directory in (paths.root, paths.documents, paths.backups, paths.exports, paths.logs):
        directory.mkdir(parents=True, exist_ok=True)
    FinalV4SchemaInitializer().initialize(paths.database)
    _security, reset, _repository, _clock, private = make_environment(root)
    request = reset.create_request()
    adapter = VerifiedSecurityBackupAdapter(
        BackupApplicationService(now=lambda: NOW),
        CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version="0.1.2",
            build_commit="783bca2288941a37145ae6982d49352b831a4c4c",
            source_tree_state="dirty",
        ),
    )
    result = reset.execute(signed_token(request, private), backup=adapter)
    archive = Path(result.backup.path)
    assert archive.suffix == ".jkmbackup"
    assert archive.is_file()
    import zipfile

    with zipfile.ZipFile(archive) as package:
        assert all("security" not in name for name in package.namelist())
        assert all("enrollment.marker" not in name for name in package.namelist())
        assert all("app-preferences.json" not in name for name in package.namelist())


@pytest.mark.parametrize("error", [RuntimeError("create"), ValueError("verify"), OSError("port")])
def test_every_backup_failure_leaves_store_unchanged(tmp_path: Path, error: Exception) -> None:
    _security, reset, repository, _clock, private = make_environment(
        tmp_path / type(error).__name__
    )
    request = reset.create_request()
    before = security_snapshot(repository.database_path)
    backup = BackupPort(error)
    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(signed_token(request, private), backup=backup)
    assert caught.value.code == SupportResetFailureCode.BACKUP_FAILED
    assert backup.finish_calls == [False]
    assert security_snapshot(repository.database_path) == before
    assert repository.security_epoch() == 1


def test_token_is_revalidated_after_a_slow_backup(tmp_path: Path) -> None:
    clock = MutableClock()
    _security, reset, repository, _clock, private = make_environment(
        tmp_path / "slow-backup", clock=clock
    )
    request = reset.create_request()
    token = signed_token(request, private)
    before = security_snapshot(repository.database_path)

    class SlowBackup(BackupPort):
        def create_and_verify(self):
            proof = super().create_and_verify()
            clock.now = request.created_at + timedelta(minutes=33)
            return proof

    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(token, backup=SlowBackup())
    assert caught.value.code == SupportResetFailureCode.TOKEN_EXPIRED
    assert security_snapshot(repository.database_path) == before


def test_finish_failure_before_commit_requires_runtime_shutdown(tmp_path: Path) -> None:
    clock = MutableClock()
    _security, reset, repository, _clock, private = make_environment(
        tmp_path / "finish-before-commit", clock=clock
    )
    request = reset.create_request()
    before = security_snapshot(repository.database_path)

    class FailingFinishBackup(BackupPort):
        def create_and_verify(self):
            proof = super().create_and_verify()
            clock.now += timedelta(hours=1)
            return proof

        def finish(self, *, reset_committed: bool) -> None:
            assert reset_committed is False
            raise RuntimeError("injected finish failure")

    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(
            signed_token(request, private),
            backup=FailingFinishBackup(),
        )

    assert caught.value.code is SupportResetFailureCode.RUNTIME_RECOVERY_REQUIRED
    assert security_snapshot(repository.database_path) == before
    assert repository.security_epoch() == 1


def test_finish_failure_after_commit_still_returns_success(tmp_path: Path) -> None:
    security, reset, repository, _clock, private = make_environment(
        tmp_path / "finish-after-commit"
    )
    request = reset.create_request()

    class FailingFinishBackup(BackupPort):
        def finish(self, *, reset_committed: bool) -> None:
            assert reset_committed is True
            raise RuntimeError("injected finish failure")

    result = reset.execute(
        signed_token(request, private),
        backup=FailingFinishBackup(),
    )

    assert result.reset_request_id == request.reset_request_id
    assert repository.security_epoch() == 2
    assert security.security_store_state().state is SecurityStoreState.PASSWORD_RESET_PENDING


@pytest.mark.parametrize(
    ("point", "committed", "returns_success"),
    [
        ("before_write_commit", False, False),
        ("after_write_commit", True, True),
    ],
)
def test_reset_transaction_crash_boundaries(
    tmp_path: Path, point: str, committed: bool, returns_success: bool
) -> None:
    failure = ToggleFailure()
    security, reset, repository, _clock, private = make_environment(
        tmp_path / point, failure=failure
    )
    request = reset.create_request()
    failure.point = point
    backup = BackupPort()
    if returns_success:
        result = reset.execute(signed_token(request, private), backup=backup)
        assert result.reset_request_id == request.reset_request_id
        assert backup.finish_calls == [True]
    else:
        with pytest.raises(SupportResetRejected) as caught:
            reset.execute(signed_token(request, private), backup=backup)
        assert caught.value.code is SupportResetFailureCode.RUNTIME_RECOVERY_REQUIRED
        assert backup.finish_calls == [False]
    failure.point = None
    assert (security.security_store_state().state == SecurityStoreState.PASSWORD_RESET_PENDING) is committed
    assert repository.security_epoch() == (2 if committed else 1)


def test_unprovable_commit_state_requires_runtime_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = ToggleFailure()
    security, reset, repository, _clock, private = make_environment(
        tmp_path / "unprovable-commit", failure=failure
    )
    request = reset.create_request()
    original_consume = repository.consume_support_reset
    original_load_account = repository.load_account
    reconciliation_blocked = False

    def consume_support_reset(**kwargs):
        nonlocal reconciliation_blocked
        try:
            return original_consume(**kwargs)
        finally:
            reconciliation_blocked = True

    def load_account():
        if reconciliation_blocked:
            raise SecurityStoreError("injected_reconciliation_read_failure")
        return original_load_account()

    monkeypatch.setattr(repository, "consume_support_reset", consume_support_reset)
    monkeypatch.setattr(repository, "load_account", load_account)
    failure.point = "after_write_commit"
    backup = BackupPort()

    with pytest.raises(SupportResetRejected) as caught:
        reset.execute(signed_token(request, private), backup=backup)

    assert caught.value.code is SupportResetFailureCode.RUNTIME_RECOVERY_REQUIRED
    assert backup.finish_calls == [False]
    reconciliation_blocked = False
    failure.point = None
    assert security.security_store_state().state is SecurityStoreState.PASSWORD_RESET_PENDING
    assert repository.security_epoch() == 2


def test_concurrent_token_use_has_exactly_one_winner(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    _security, first, repository, clock, private = make_environment(root)
    request = first.create_request()
    token = signed_token(request, private)
    _security2, second, _repository2, _clock2, _private2 = make_environment(
        root, clock=clock, private_key=private, random_source=DeterministicRandom(b"second")
    )
    backup = BackupPort()

    def run(service: SupportResetService):
        try:
            return service.execute(token, backup=backup)
        except SupportResetRejected as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(run, (first, second)))
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert repository.security_epoch() == 2
    assert backup.calls >= 1


def downgrade_store_to_v1(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE device_credentials")
        connection.execute("DROP TABLE support_reset_token_uses")
        connection.execute("DROP TABLE support_reset_requests")
        connection.execute("DROP TABLE security_epochs")
        connection.execute("UPDATE security_metadata SET schema_version = 1")
        connection.execute("PRAGMA user_version = 1")


def test_v1_migrates_transactionally_and_preserves_existing_auth_data(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    security, _reset, repository, clock, _private = make_environment(root)
    before_hash = repository.load_account().password_hash
    with sqlite3.connect(repository.database_path) as connection:
        before_codes = connection.execute("SELECT COUNT(*), hex(min(code_hash)) FROM recovery_codes").fetchone()
    downgrade_store_to_v1(repository.database_path)
    reopened = SQLiteSecurityRepository(repository.database_path, PlatformFilePermissionManager())
    assert reopened.inspect()[0] == 3
    assert reopened.load_account().password_hash == before_hash
    assert reopened.security_epoch() == 1
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*), hex(min(code_hash)) FROM recovery_codes").fetchone() == before_codes
    assert security.authenticate_password(PASSWORD).status == AuthenticationStatus.AUTHENTICATED
    assert clock.now == NOW


def test_product_start_read_only_gate_rejects_v1_without_migration(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime-read-only"
    _security, _reset, repository, _clock, _private = make_environment(root)
    downgrade_store_to_v1(repository.database_path)
    before = repository.database_path.read_bytes()
    reopened = SQLiteSecurityRepository(
        repository.database_path,
        PlatformFilePermissionManager(),
    )

    with pytest.raises(SecurityStoreError, match="security_store_version_invalid"):
        reopened.require_current_read_only()

    assert repository.database_path.read_bytes() == before
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_v2_migrates_to_v3_without_changing_account_recovery_or_epoch(tmp_path: Path) -> None:
    root = tmp_path / "runtime-v2"
    security, _reset, repository, _clock, _private = make_environment(root)
    account_before = repository.load_account()
    epoch_before = repository.security_epoch()
    with sqlite3.connect(repository.database_path) as connection:
        recovery_before = connection.execute(
            "SELECT recovery_code_id, salt, code_hash, status FROM recovery_codes "
            "ORDER BY recovery_code_id"
        ).fetchall()
        connection.execute("DROP TABLE device_credentials")
        connection.execute("UPDATE security_metadata SET schema_version = 2")
        connection.execute("PRAGMA user_version = 2")
    reopened = SQLiteSecurityRepository(
        repository.database_path, PlatformFilePermissionManager()
    )
    assert reopened.inspect()[0] == 3
    assert reopened.load_account() == account_before
    assert reopened.security_epoch() == epoch_before
    assert reopened.active_device_credential() is None
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute(
            "SELECT recovery_code_id, salt, code_hash, status FROM recovery_codes "
            "ORDER BY recovery_code_id"
        ).fetchall() == recovery_before
    assert security.authenticate_password(PASSWORD).status == AuthenticationStatus.AUTHENTICATED


@pytest.mark.parametrize(
    ("point", "version"),
    [("before_migration", 1), ("before_migration_commit", 1), ("after_migration_commit", 3)],
)
def test_migration_crash_before_and_after_commit(tmp_path: Path, point: str, version: int) -> None:
    root = tmp_path / point
    _security, _reset, repository, _clock, _private = make_environment(root)
    downgrade_store_to_v1(repository.database_path)
    failure = ToggleFailure()
    failure.point = point
    migrating = SQLiteSecurityRepository(
        repository.database_path, PlatformFilePermissionManager(), failure_injector=failure
    )
    with pytest.raises(RuntimeError, match="injected"):
        migrating.inspect()
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == version
    failure.point = None
    assert migrating.inspect()[0] == 3


def test_unknown_newer_security_schema_fails_closed(tmp_path: Path) -> None:
    security, _reset, repository, _clock, _private = make_environment(tmp_path / "runtime")
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute("UPDATE security_metadata SET schema_version = 4")
        connection.execute("PRAGMA user_version = 4")
    assert security.security_store_state().state == SecurityStoreState.UNSUPPORTED_VERSION
