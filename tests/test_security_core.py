"""Security-store, Argon2id, password and throttling contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import uuid
import zipfile

from argon2 import PasswordHasher as RawPasswordHasher, extract_parameters
from argon2.low_level import Type
import pytest

from src.application.commands.backup import BackupApplicationService, CreateBackupCommand
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.runtime import prepare_runtime_storage, runtime_paths
from src.security.application import SecurityApplicationService
from src.security.domain import (
    AuthenticationStatus,
    PASSWORD_HASH_FORMAT_VERSION,
    PasswordPolicy,
    PasswordPolicyError,
    PasswordViolation,
    SecurityStateError,
    SecurityStoreError,
    SecurityStoreState,
    delay_seconds_for_failure,
)
from src.security.infrastructure import (
    Argon2idPasswordHasher,
    EnrollmentMarkerFile,
    PlatformFilePermissionManager,
    SQLiteSecurityRepository,
)


PASSWORD = "dies ist eine sichere Test Passphrase"
NEW_PASSWORD = "dies ist eine andere sichere Test Passphrase"
FIXED_NOW = datetime(2026, 7, 17, 10, 0, tzinfo=UTC)


class DeterministicRandom:
    def __init__(self, seed: bytes = b"security-test") -> None:
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
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self.now = now
        self.monotonic_value = 1000.0

    def utc_now(self) -> datetime:
        return self.now

    def monotonic(self) -> float:
        return self.monotonic_value

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)
        self.monotonic_value += seconds


class ToggleFailure:
    def __init__(self) -> None:
        self.point: str | None = None

    def __call__(self, point: str) -> None:
        if point == self.point:
            raise RuntimeError("injected security-store failure")


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


def test_runtime_security_paths_are_canonical_and_not_prepared_on_normal_start(
    tmp_path: Path,
) -> None:
    paths = runtime_paths(tmp_path / "runtime")
    assert paths.security == paths.root / "security"
    assert paths.security_database == paths.root / "security" / "security.sqlite"
    assert paths.enrollment_marker == paths.root / "security" / "enrollment.marker"
    resources = tmp_path / "empty-resources"
    resources.mkdir()
    prepared = prepare_runtime_storage(data_root=paths.root, resource_root_path=resources)
    assert prepared.database == paths.database
    assert not paths.security.exists()


def test_security_import_has_no_runtime_or_database_side_effect(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import src.security; import src.security.infrastructure; print('security import ok')",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(project_root)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "security import ok"
    assert result.stderr == ""
    assert not tuple(tmp_path.rglob("*.sqlite"))
    assert not (tmp_path / "security").exists()


def test_security_layer_has_no_qt_or_desktop_store_access() -> None:
    project_root = Path(__file__).resolve().parents[1]
    security_files = tuple((project_root / "src" / "security").rglob("*.py"))
    assert security_files
    for path in security_files:
        source = path.read_text(encoding="utf-8")
        assert "PySide6" not in source
        assert "src.desktop_app" not in source
        if path.name not in {"sqlite_repository.py", "data_keyset_repository.py"}:
            assert "import sqlite3" not in source
    for path in (
        project_root / "src" / "desktop_app" / "shell.py",
        project_root / "src" / "desktop_app" / "app.py",
        project_root / "src" / "desktop_app" / "main.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "SQLiteSecurityRepository" not in source
        assert "SecurityApplicationService" not in source


def test_product_security_startup_does_not_import_encryption_foundations() -> None:
    project_root = Path(__file__).resolve().parents[1]
    script = """
import sys
import src.security.startup
for name in (
    'src.security.data_keys',
    'src.security.database_keys',
    'src.security.migration_journal',
    'src.security.infrastructure.data_master_key_store',
):
    assert name not in sys.modules, name
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("password", "violation"),
    [
        ("zu kurz", PasswordViolation.TOO_SHORT),
        ("x" * 1025, PasswordViolation.TOO_LARGE),
        ("passwortpasswort", PasswordViolation.BLOCKED),
    ],
)
def test_password_policy_has_structured_rejections_without_secret_message(
    password: str, violation: PasswordViolation
) -> None:
    with pytest.raises(PasswordPolicyError) as caught:
        PasswordPolicy().validate(password)
    assert violation in caught.value.violations
    assert password not in str(caught.value)
    assert password not in repr(caught.value)


def test_password_policy_accepts_spaces_unicode_and_128_characters_unchanged() -> None:
    policy = PasswordPolicy()
    for password in (
        "  eine lange Passphrase mit Rand  ",
        "Lernen mit Ruhe und Überblick 🌿",
        "ä" * 128,
    ):
        policy.validate(password)
    with pytest.raises(PasswordPolicyError):
        policy.validate("a" * 1010 + "🌿" * 4)


def test_password_verification_does_not_silently_normalize_unicode(tmp_path: Path) -> None:
    composed = "lange Passphrase mit é"
    decomposed = "lange Passphrase mit e\u0301"
    service, _repository, _clock = make_service(tmp_path / "runtime")
    service.enroll_local_account(composed)
    assert service.authenticate_password(composed).status == AuthenticationStatus.AUTHENTICATED
    assert service.authenticate_password(decomposed).status == AuthenticationStatus.INVALID_CREDENTIALS


def test_argon2id_contract_real_hash_verify_and_individual_salts() -> None:
    hasher = Argon2idPasswordHasher()
    first = hasher.hash(PASSWORD, b"1" * 16)
    second = hasher.hash(PASSWORD, b"2" * 16)
    assert first != second
    assert hasher.verify(first, PASSWORD)
    assert not hasher.verify(first, NEW_PASSWORD)
    parameters = extract_parameters(first)
    assert parameters.type == Type.ID
    assert parameters.memory_cost == 65536
    assert parameters.time_cost == 6
    assert parameters.parallelism == 1
    assert parameters.salt_len == 16
    assert parameters.hash_len == 32
    assert first.startswith("$argon2id$v=19$")
    assert hasher.needs_rehash(first) is False
    assert PASSWORD_HASH_FORMAT_VERSION == 1


def test_enrollment_creates_strict_schema_uuid4_ids_and_posix_permissions(
    tmp_path: Path,
) -> None:
    service, repository, _clock, result = enroll(tmp_path / "runtime")
    paths = runtime_paths(tmp_path / "runtime")
    state = service.security_store_state()
    assert state.state == SecurityStoreState.READY
    assert state.installation_id == result.installation_id
    assert state.user_id == result.user_id
    assert uuid.UUID(result.installation_id).version == 4
    assert uuid.UUID(result.user_id).version == 4
    assert result.support_installation_id == f"INS-{result.installation_id}"
    assert len(result.recovery_codes) == 10
    assert paths.database.exists() is False
    with sqlite3.connect(repository.database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 0x4A4B4D53
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert tables == {
            "security_metadata",
            "installations",
            "local_accounts",
            "recovery_code_sets",
            "recovery_codes",
            "support_reset_requests",
            "support_reset_token_uses",
            "security_epochs",
            "device_credentials",
        }
        columns = {
            row[1]
            for table in tables
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        assert not columns.intersection(
            {"email", "school_name", "os_username", "full_name", "role", "password_hint"}
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO local_accounts "
                "(user_id, installation_id, password_hash, hash_format_version, status, created_at_utc, updated_at_utc) "
                "VALUES (?, ?, 'x', 1, 'active', 'x', 'x')",
                (str(uuid.uuid4()), str(uuid.uuid4())),
            )
    if os.name == "posix":
        assert stat.S_IMODE(paths.security.stat().st_mode) == 0o700
        assert stat.S_IMODE(paths.security_database.stat().st_mode) == 0o600
        assert stat.S_IMODE(paths.enrollment_marker.stat().st_mode) == 0o600


def test_marker_and_store_combinations_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    service, _repository, _clock, _result = enroll(root)
    paths = runtime_paths(root)
    store_bytes = paths.security_database.read_bytes()
    marker_bytes = paths.enrollment_marker.read_bytes()

    paths.security_database.unlink()
    assert service.security_store_state().state == SecurityStoreState.INCONSISTENT
    paths.security_database.write_bytes(store_bytes)
    paths.enrollment_marker.unlink()
    assert service.security_store_state().state == SecurityStoreState.INCONSISTENT
    paths.enrollment_marker.write_bytes(marker_bytes)
    paths.security_database.write_bytes(b"not sqlite")
    assert service.security_store_state().state == SecurityStoreState.CORRUPT


def test_marker_binding_mismatch_and_extra_schema_object_fail_closed(tmp_path: Path) -> None:
    binding_root = tmp_path / "binding"
    service, _repository, _clock, _result = enroll(binding_root)
    marker_path = runtime_paths(binding_root).enrollment_marker
    payload = json.loads(marker_path.read_text(encoding="ascii"))
    payload["marker_reference"] = str(uuid.uuid4())
    marker_path.write_text(json.dumps(payload), encoding="ascii")
    assert service.security_store_state().state == SecurityStoreState.INCONSISTENT

    schema_root = tmp_path / "schema"
    service, repository, _clock, _result = enroll(schema_root)
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute("CREATE TABLE unexpected_shadow(value TEXT) STRICT")
    assert service.security_store_state().state == SecurityStoreState.CORRUPT


def test_newer_store_and_marker_versions_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "store-newer"
    service, _repository, _clock, _result = enroll(root)
    paths = runtime_paths(root)
    with sqlite3.connect(paths.security_database) as connection:
        connection.execute("UPDATE security_metadata SET schema_version = 4")
    assert service.security_store_state().state == SecurityStoreState.UNSUPPORTED_VERSION

    root = tmp_path / "marker-newer"
    service, _repository, _clock, _result = enroll(root)
    paths = runtime_paths(root)
    marker = json.loads(paths.enrollment_marker.read_text(encoding="ascii"))
    marker["format_version"] = 2
    paths.enrollment_marker.write_text(json.dumps(marker), encoding="ascii")
    assert service.security_store_state().state == SecurityStoreState.UNSUPPORTED_VERSION


@pytest.mark.parametrize("failure_point", ["before_schema", "before_commit", "after_commit"])
def test_enrollment_failure_before_publish_leaves_no_accepted_half_state(
    tmp_path: Path, failure_point: str
) -> None:
    failure = ToggleFailure()
    failure.point = failure_point
    service, _repository, _clock = make_service(tmp_path / failure_point, failure=failure)
    with pytest.raises(RuntimeError, match="injected"):
        service.enroll_local_account(PASSWORD)
    paths = runtime_paths(tmp_path / failure_point)
    assert not paths.security_database.exists()
    assert not paths.enrollment_marker.exists()
    assert service.security_store_state().state == SecurityStoreState.UNINITIALIZED


def test_crash_after_store_publish_is_visible_inconsistent_not_first_start(
    tmp_path: Path,
) -> None:
    failure = ToggleFailure()
    failure.point = "after_publish"
    service, _repository, _clock = make_service(tmp_path / "runtime", failure=failure)
    with pytest.raises(RuntimeError, match="injected"):
        service.enroll_local_account(PASSWORD)
    paths = runtime_paths(tmp_path / "runtime")
    assert paths.security_database.exists()
    assert not paths.enrollment_marker.exists()
    assert service.security_store_state().state == SecurityStoreState.INCONSISTENT


def test_repeated_enrollment_is_defined_and_never_adds_second_account(tmp_path: Path) -> None:
    service, repository, _clock, _result = enroll(tmp_path / "runtime")
    with pytest.raises(SecurityStateError):
        service.enroll_local_account(NEW_PASSWORD)
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM local_accounts").fetchone()[0] == 1


def test_failure_delay_sequence_is_bounded() -> None:
    assert [delay_seconds_for_failure(index) for index in range(1, 12)] == [
        0, 0, 0, 0, 30, 60, 120, 240, 300, 300, 300
    ]


def test_login_throttling_persists_across_reopen_and_success_resets_it(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    service, _repository, clock, _result = enroll(root)
    observed = []
    for _attempt in range(9):
        result = service.authenticate_password("falsches Passwort mit ausreichender Länge")
        observed.append(result.retry_after_seconds)
        if result.retry_after_seconds:
            clock.advance(result.retry_after_seconds)
    assert observed == [0, 0, 0, 0, 30, 60, 120, 240, 300]
    reopened, _repository, _clock = make_service(root, clock=clock)
    account = _repository.load_account()
    assert account.failed_attempts == 9
    assert reopened.authenticate_password(PASSWORD).status == AuthenticationStatus.AUTHENTICATED
    assert _repository.load_account().failed_attempts == 0
    assert reopened.current_lock_state().locked is False


def test_monotonic_deadline_prevents_utc_jump_from_shortening_process_lock(
    tmp_path: Path,
) -> None:
    service, _repository, clock, _result = enroll(tmp_path / "runtime")
    for _attempt in range(5):
        result = service.authenticate_password("falsches Passwort mit ausreichender Länge")
    assert result.retry_after_seconds == 30
    clock.now += timedelta(minutes=10)
    lock = service.current_lock_state()
    assert lock.locked
    assert lock.remaining_seconds == 30


def test_utc_rollback_over_five_minutes_persists_conservative_lock(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    service, _repository, clock, _result = enroll(root)
    assert not service.current_lock_state().locked
    clock.now -= timedelta(minutes=5, seconds=1)
    lock = service.current_lock_state()
    assert lock.locked and lock.clock_rollback_detected
    assert lock.remaining_seconds == 300
    reopened, _repository, _clock = make_service(root, clock=clock)
    assert reopened.current_lock_state().locked
    clock.advance(300)
    assert reopened.current_lock_state().locked is False


def test_time_cost_3_hash_rehashes_after_success_but_never_after_wrong_password(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    service, repository, _clock, _result = enroll(root)
    old_hasher = RawPasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=1,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )
    old_hash = old_hasher.hash(PASSWORD)
    current_hasher = Argon2idPasswordHasher()
    assert current_hasher.verify(old_hash, PASSWORD)
    assert current_hasher.needs_rehash(old_hash)
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute("UPDATE local_accounts SET password_hash = ?", (old_hash,))
    wrong = service.authenticate_password("falsches Passwort mit ausreichender Länge")
    assert wrong.status == AuthenticationStatus.INVALID_CREDENTIALS
    assert repository.load_account().password_hash == old_hash
    success = service.authenticate_password(PASSWORD)
    assert success.status == AuthenticationStatus.AUTHENTICATED
    assert success.password_hash_upgraded
    upgraded_hash = repository.load_account().password_hash
    assert upgraded_hash != old_hash
    assert extract_parameters(upgraded_hash).time_cost == 6
    assert current_hasher.needs_rehash(upgraded_hash) is False


def test_password_change_checks_current_password_and_rolls_back_before_commit(
    tmp_path: Path,
) -> None:
    failure = ToggleFailure()
    root = tmp_path / "runtime"
    service, _repository, _clock, _result = enroll(root, failure=failure)
    wrong = service.change_password(
        "falsches aktuelles Passwort", NEW_PASSWORD
    )
    assert wrong.status == AuthenticationStatus.INVALID_CREDENTIALS
    assert service.authenticate_password(PASSWORD).status == AuthenticationStatus.AUTHENTICATED

    failure.point = "before_write_commit"
    with pytest.raises(RuntimeError, match="injected"):
        service.change_password(PASSWORD, NEW_PASSWORD)
    failure.point = None
    assert service.authenticate_password(PASSWORD).status == AuthenticationStatus.AUTHENTICATED
    assert service.authenticate_password(NEW_PASSWORD).status == AuthenticationStatus.INVALID_CREDENTIALS


def test_password_change_has_defined_pre_and_post_commit_crash_states(
    tmp_path: Path,
) -> None:
    failure = ToggleFailure()
    _service, repository, clock, _result = enroll(
        tmp_path / "runtime", failure=failure
    )
    old_hash = repository.load_account().password_hash
    replacement_hash = Argon2idPasswordHasher().hash(NEW_PASSWORD, b"r" * 16)

    failure.point = "before_write_commit"
    with pytest.raises(RuntimeError, match="injected"):
        repository.change_password(
            expected_hash=old_hash,
            replacement_hash=replacement_hash,
            now=clock.utc_now(),
        )
    failure.point = None
    assert repository.load_account().password_hash == old_hash

    failure.point = "after_write_commit"
    with pytest.raises(RuntimeError, match="injected"):
        repository.change_password(
            expected_hash=old_hash,
            replacement_hash=replacement_hash,
            now=clock.utc_now(),
        )
    failure.point = None
    assert repository.load_account().password_hash == replacement_hash


def test_security_permissions_reject_symlink_without_chmod_outside_scope(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    security_link = tmp_path / "security"
    security_link.symlink_to(outside, target_is_directory=True)
    permissions = PlatformFilePermissionManager()
    before = stat.S_IMODE(outside.stat().st_mode)
    with pytest.raises(SecurityStoreError, match="security_directory_symlink_rejected"):
        permissions.prepare_directory(security_link)
    assert stat.S_IMODE(outside.stat().st_mode) == before


def test_security_write_uses_wal_and_secures_all_existing_sidecars(tmp_path: Path) -> None:
    service, repository, _clock, _result = enroll(tmp_path / "runtime")
    service.authenticate_password("falsches Passwort mit ausreichender Länge")
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    if os.name == "posix":
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = Path(f"{repository.database_path}{suffix}")
            if path.exists():
                assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_backup_archive_explicitly_excludes_security_directory_and_sidecars(
    tmp_path: Path,
) -> None:
    paths = runtime_paths(tmp_path / "runtime")
    for directory in (paths.root, paths.documents, paths.exports, paths.backups, paths.logs):
        directory.mkdir(parents=True, exist_ok=True)
    SQLiteDatabase(paths.database).initialize_schema()
    service, _repository, _clock, result = enroll(paths.root)
    for suffix in ("-wal", "-shm", "-journal"):
        Path(f"{paths.security_database}{suffix}").write_bytes(b"security-sidecar-sentinel")
    backup = BackupApplicationService(now=lambda: FIXED_NOW).create(
        CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version="0.1.2",
            build_commit="78a3011",
            source_tree_state="clean",
        )
    )
    with zipfile.ZipFile(backup.path) as archive:
        names = archive.namelist()
        payload = b"".join(archive.read(name) for name in names)
    assert all(not name.startswith("security/") for name in names)
    assert paths.enrollment_marker.read_bytes() not in payload
    assert result.recovery_codes[0].encode("ascii") not in payload
