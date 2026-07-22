from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

from src.security.migration_lock import (
    MIGRATION_LOCK_FILENAME,
    ExclusiveMigrationLock,
    InMemoryMigrationLock,
    MigrationLockError,
    MigrationLockOwner,
    MigrationLockPort,
    MigrationLockStatus,
    UnsupportedMigrationLock,
)


INSTALLATION_ID = "11111111-1111-4111-8111-111111111111"
DATABASE_CONTEXT_ID = "22222222-2222-4222-8222-222222222222"
MIGRATION_ID = "33333333-3333-4333-8333-333333333333"


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "migration-root"
    root.mkdir(mode=0o700, parents=True)
    return root


def _lock(root: Path, **kwargs) -> ExclusiveMigrationLock:
    migration_id = kwargs.pop("migration_id_override", MIGRATION_ID)
    return ExclusiveMigrationLock(
        root,
        installation_id=INSTALLATION_ID,
        database_context_id=DATABASE_CONTEXT_ID,
        migration_id=migration_id,
        allowed_root=root,
        **kwargs,
    )


def _run_python(source: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    project_root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        [sys.executable, "-c", source, *arguments],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root)},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def _crash_owner(root: Path) -> dict[str, object]:
    result = _run_python(
        """
import json, os, sys
from dataclasses import asdict
from pathlib import Path
from src.security.migration_lock import ExclusiveMigrationLock
lock = ExclusiveMigrationLock(
    Path(sys.argv[1]),
    installation_id=sys.argv[2],
    database_context_id=sys.argv[3],
    migration_id=sys.argv[4],
    allowed_root=Path(sys.argv[1]),
).acquire()
print(json.dumps({
    "owner": asdict(lock.owner),
    "identity": lock.file_identity,
}), flush=True)
os._exit(23)
""",
        str(root),
        INSTALLATION_ID,
        DATABASE_CONTEXT_ID,
        MIGRATION_ID,
    )
    assert result.returncode == 23
    return json.loads(result.stdout)


def test_acquire_verify_release_reuses_same_inode_and_repeated_release_is_safe(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    lock = _lock(root).acquire()
    assert lock.verify_owner() is True
    first_identity = lock.file_identity
    assert lock.inspect().status is MigrationLockStatus.HELD

    assert lock.release() is True
    assert lock.release() is False
    released = lock.inspect()
    assert released.status is MigrationLockStatus.RELEASED
    assert (released.device_id, released.file_id) == first_identity

    restarted = _lock(
        root, migration_id_override="44444444-4444-4444-8444-444444444444"
    )
    restarted.acquire()
    assert restarted.file_identity == first_identity
    restarted.release()


def test_second_real_process_is_rejected_while_owner_holds_kernel_lock(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    with _lock(root):
        result = _run_python(
            """
import sys
from pathlib import Path
from src.security.migration_lock import ExclusiveMigrationLock, MigrationLockError
try:
    ExclusiveMigrationLock(
        Path(sys.argv[1]),
        installation_id=sys.argv[2],
        database_context_id=sys.argv[3],
        migration_id=sys.argv[4],
        allowed_root=Path(sys.argv[1]),
    ).acquire()
except MigrationLockError as error:
    print(error.code)
    raise SystemExit(17)
raise SystemExit(0)
""",
            str(root),
            INSTALLATION_ID,
            DATABASE_CONTEXT_ID,
            MIGRATION_ID,
        )
    assert result.returncode == 17
    assert result.stdout.strip() == "migration_lock_busy"


def test_live_owner_with_unlocked_crash_evidence_is_not_misclassified_stale(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            """
import json, os, sys, time
from dataclasses import asdict
from pathlib import Path
from src.security.migration_lock import ExclusiveMigrationLock
lock = ExclusiveMigrationLock(
    Path(sys.argv[1]),
    installation_id=sys.argv[2],
    database_context_id=sys.argv[3],
    migration_id=sys.argv[4],
    allowed_root=Path(sys.argv[1]),
).acquire()
os.close(lock._descriptor)
lock._descriptor = None
lock._held = False
print(json.dumps(asdict(lock.owner)), flush=True)
time.sleep(15)
""",
            str(root),
            INSTALLATION_ID,
            DATABASE_CONTEXT_ID,
            MIGRATION_ID,
        ],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        owner = MigrationLockOwner(**json.loads(process.stdout.readline()))
        inspection = _lock(root).inspect()
        assert inspection.status is MigrationLockStatus.BLOCKED
        assert inspection.error_code in {
            "migration_lock_owner_still_alive",
            "migration_lock_process_identity_unavailable",
        }
        assert inspection.owner == owner
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_crashed_real_process_requires_explicit_nonce_and_identity_takeover(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    evidence = _crash_owner(root)
    expected_owner = MigrationLockOwner(**evidence["owner"])

    replacement = _lock(root)
    assert replacement.inspect().status is MigrationLockStatus.STALE
    with pytest.raises(MigrationLockError) as ordinary:
        replacement.acquire()
    assert ordinary.value.code == "migration_lock_stale_takeover_required"
    with pytest.raises(MigrationLockError) as wrong_nonce:
        replacement.take_over_stale(
            expected_owner=replace(expected_owner, lock_nonce="0" * 64),
            expected_device_id=evidence["identity"][0],
            expected_file_id=evidence["identity"][1],
        )
    assert wrong_nonce.value.code == "migration_lock_stale_evidence_mismatch"

    with pytest.raises(MigrationLockError) as missing_recovery_evidence:
        replacement.take_over_stale(
            expected_owner=expected_owner,
            expected_device_id=evidence["identity"][0],
            expected_file_id=evidence["identity"][1],
        )
    assert (
        missing_recovery_evidence.value.code
        == "migration_lock_recovery_evidence_required"
    )

    with pytest.raises(MigrationLockError) as invalid_recovery_evidence:
        replacement.take_over_stale(
            expected_owner=expected_owner,
            expected_device_id=evidence["identity"][0],
            expected_file_id=evidence["identity"][1],
            recovery_evidence_validator=lambda _owner, _identity: False,
        )
    assert (
        invalid_recovery_evidence.value.code
        == "migration_lock_recovery_evidence_invalid"
    )

    validated = []

    replacement.take_over_stale(
        expected_owner=expected_owner,
        expected_device_id=evidence["identity"][0],
        expected_file_id=evidence["identity"][1],
        recovery_evidence_validator=lambda owner, identity: validated.append(
            (owner, identity)
        )
        or True,
    )
    assert validated == [(expected_owner, tuple(evidence["identity"]))]
    assert replacement.verify_owner()
    replacement.release()


def test_live_pid_reuse_can_be_taken_over_only_with_changed_start_identity(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    evidence = _crash_owner(root)
    expected_owner = MigrationLockOwner(**evidence["owner"])

    replacement = _lock(
        root,
        process_exists=lambda _pid: True,
        process_identity=lambda _pid: "different-process-start",
    )
    replacement.take_over_stale(
        expected_owner=expected_owner,
        expected_device_id=evidence["identity"][0],
        expected_file_id=evidence["identity"][1],
        recovery_evidence_validator=lambda _owner, _identity: True,
    )
    replacement.release()


def test_unavailable_live_process_identity_blocks_stale_takeover(tmp_path: Path) -> None:
    root = _root(tmp_path)
    evidence = _crash_owner(root)
    expected_owner = MigrationLockOwner(**evidence["owner"])

    replacement = _lock(
        root,
        process_exists=lambda _pid: True,
        process_identity=lambda _pid: None,
    )
    assert replacement.inspect().status is MigrationLockStatus.BLOCKED
    with pytest.raises(MigrationLockError) as blocked:
        replacement.take_over_stale(
            expected_owner=expected_owner,
            expected_device_id=evidence["identity"][0],
            expected_file_id=evidence["identity"][1],
        )
    assert blocked.value.code == "migration_lock_process_identity_unavailable"


def test_matching_live_process_identity_blocks_false_stale_takeover(tmp_path: Path) -> None:
    root = _root(tmp_path)
    evidence = _crash_owner(root)
    expected_owner = MigrationLockOwner(**evidence["owner"])
    recorded = expected_owner.process_start_identity

    replacement = _lock(
        root,
        process_exists=lambda _pid: True,
        process_identity=lambda _pid: recorded,
    )
    with pytest.raises(MigrationLockError) as blocked:
        replacement.take_over_stale(
            expected_owner=expected_owner,
            expected_device_id=evidence["identity"][0],
            expected_file_id=evidence["identity"][1],
        )
    assert blocked.value.code == "migration_lock_owner_still_alive"


def test_tampered_payload_blocks_verify_and_is_not_overwritten(tmp_path: Path) -> None:
    root = _root(tmp_path)
    lock = _lock(root).acquire()
    path = root / MIGRATION_LOCK_FILENAME
    path.write_text("{}", encoding="ascii")
    with pytest.raises(MigrationLockError) as caught:
        lock.verify_owner()
    assert caught.value.code == "migration_lock_payload_invalid"
    with pytest.raises(MigrationLockError):
        lock.release()
    assert path.read_text(encoding="ascii") == "{}"


def test_canonical_owner_tamper_cannot_satisfy_explicit_stale_evidence(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    evidence = _crash_owner(root)
    expected_owner = MigrationLockOwner(**evidence["owner"])
    path = root / MIGRATION_LOCK_FILENAME
    payload = json.loads(path.read_bytes())
    payload["pid"] = os.getpid()
    payload["process_start_identity"] = "tampered-process-start"
    path.write_bytes(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    )

    replacement = _lock(
        root,
        process_exists=lambda _pid: True,
        process_identity=lambda _pid: "different-process-start",
    )
    with pytest.raises(MigrationLockError) as caught:
        replacement.take_over_stale(
            expected_owner=expected_owner,
            expected_device_id=evidence["identity"][0],
            expected_file_id=evidence["identity"][1],
        )
    assert caught.value.code == "migration_lock_stale_evidence_mismatch"


def test_exchanged_path_blocks_owner_and_never_modifies_foreign_file(tmp_path: Path) -> None:
    root = _root(tmp_path)
    lock = _lock(root).acquire()
    path = root / MIGRATION_LOCK_FILENAME
    displaced = root / "owned-old.lock"
    path.rename(displaced)
    foreign = b"foreign-sentinel"
    path.write_bytes(foreign)

    with pytest.raises(MigrationLockError) as caught:
        lock.verify_owner()
    assert caught.value.code == "migration_lock_file_changed"
    with pytest.raises(MigrationLockError):
        lock.release()
    assert path.read_bytes() == foreign


def test_symlink_lock_and_symlink_root_are_rejected_without_touching_target(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    target = tmp_path / "foreign.txt"
    target.write_bytes(b"unchanged")
    (root / MIGRATION_LOCK_FILENAME).symlink_to(target)
    with pytest.raises(MigrationLockError) as lock_error:
        _lock(root).acquire()
    assert lock_error.value.code == "migration_lock_symlink_rejected"
    assert target.read_bytes() == b"unchanged"

    real_root = _root(tmp_path / "second")
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(real_root, target_is_directory=True)
    with pytest.raises(MigrationLockError) as root_error:
        ExclusiveMigrationLock(
            linked_root,
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            migration_id=MIGRATION_ID,
            allowed_root=real_root,
        )
    assert root_error.value.code == "migration_lock_root_symlink_rejected"


def test_root_outside_explicit_allowed_boundary_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    with pytest.raises(MigrationLockError) as caught:
        ExclusiveMigrationLock(
            outside,
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            migration_id=MIGRATION_ID,
            allowed_root=allowed,
        )
    assert caught.value.code == "migration_lock_root_outside_allowed"


def test_foreign_instance_cannot_release_or_verify_owner(tmp_path: Path) -> None:
    root = _root(tmp_path)
    owner = _lock(root).acquire()
    foreign = _lock(root)
    with pytest.raises(MigrationLockError) as verify:
        foreign.verify_owner()
    assert verify.value.code == "migration_lock_not_owned"
    with pytest.raises(MigrationLockError) as release:
        foreign.release()
    assert release.value.code == "migration_lock_not_owned"
    assert owner.verify_owner()
    owner.release()


def test_parallel_acquire_has_exactly_one_winner(tmp_path: Path) -> None:
    root = _root(tmp_path)

    def attempt(index: int) -> tuple[int, ExclusiveMigrationLock | None]:
        contender = _lock(
            root,
            migration_id_override=str(uuid.UUID(int=index + 10, version=4)),
        )
        try:
            contender.acquire()
        except MigrationLockError:
            return 0, None
        return 1, contender

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    winners = [lock for won, lock in results if won and lock is not None]
    assert len(winners) == 1
    winners[0].release()


def test_payload_is_canonical_secret_free_and_context_bound(tmp_path: Path) -> None:
    root = _root(tmp_path)
    lock = _lock(
        root,
        now=lambda: datetime(2026, 7, 22, 1, 2, 3, tzinfo=UTC),
        nonce_source=lambda: "a" * 64,
    ).acquire()
    raw = (root / MIGRATION_LOCK_FILENAME).read_bytes()
    payload = json.loads(raw)
    assert raw == json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    assert payload["installation_id"] == INSTALLATION_ID
    assert payload["database_context_id"] == DATABASE_CONTEXT_ID
    assert payload["migration_id"] == MIGRATION_ID
    assert payload["lock_nonce"] == "a" * 64
    assert payload["acquired_at"] == "2026-07-22T01:02:03Z"
    assert not any(
        marker in raw
        for marker in (
            b"password",
            b"student",
            b"document",
            b"database-key",
            b"dmk",
            b"secret-sentinel",
        )
    )
    lock.release()


def test_invalid_context_and_missing_release_fail_closed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    with pytest.raises(MigrationLockError) as invalid:
        ExclusiveMigrationLock(
            root,
            installation_id="not-a-uuid",
            database_context_id=DATABASE_CONTEXT_ID,
            migration_id=MIGRATION_ID,
            allowed_root=root,
        )
    assert invalid.value.code == "migration_lock_context_invalid"
    with pytest.raises(MigrationLockError) as missing:
        _lock(root).release()
    assert missing.value.code == "migration_lock_not_owned"


def test_platform_neutral_port_is_runtime_checkable(tmp_path: Path) -> None:
    namespace = f"port-{uuid.uuid4()}"
    assert isinstance(_lock(_root(tmp_path)), MigrationLockPort)
    assert isinstance(
        InMemoryMigrationLock(
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            migration_id=MIGRATION_ID,
            namespace=namespace,
        ),
        MigrationLockPort,
    )
    assert isinstance(UnsupportedMigrationLock(), MigrationLockPort)


def test_in_memory_lock_parallel_foreign_release_and_retained_identity() -> None:
    namespace = f"parallel-{uuid.uuid4()}"

    def contender(index: int) -> InMemoryMigrationLock | None:
        lock = InMemoryMigrationLock(
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            migration_id=str(uuid.UUID(int=index + 100, version=4)),
            namespace=namespace,
        )
        try:
            return lock.acquire()
        except MigrationLockError as error:
            assert error.code == "migration_lock_busy"
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(contender, range(8)))
    winners = [lock for lock in results if lock is not None]
    assert len(winners) == 1
    winner = winners[0]
    first_identity = winner.file_identity
    foreign = InMemoryMigrationLock(
        installation_id=INSTALLATION_ID,
        database_context_id=DATABASE_CONTEXT_ID,
        migration_id=MIGRATION_ID,
        namespace=namespace,
    )
    with pytest.raises(MigrationLockError) as release:
        foreign.release()
    assert release.value.code == "migration_lock_not_owned"
    assert winner.verify_owner()
    assert winner.release() is True
    assert winner.release() is False

    replacement = foreign.acquire()
    assert replacement.file_identity == first_identity
    replacement.release()


def test_in_memory_lock_context_mismatch_is_fail_closed() -> None:
    namespace = f"context-{uuid.uuid4()}"
    owner = InMemoryMigrationLock(
        installation_id=INSTALLATION_ID,
        database_context_id=DATABASE_CONTEXT_ID,
        migration_id=MIGRATION_ID,
        namespace=namespace,
    ).acquire()
    foreign_context = InMemoryMigrationLock(
        installation_id="44444444-4444-4444-8444-444444444444",
        database_context_id=DATABASE_CONTEXT_ID,
        migration_id=MIGRATION_ID,
        namespace=namespace,
    )
    inspection = foreign_context.inspect()
    assert inspection.status is MigrationLockStatus.BLOCKED
    assert inspection.error_code == "migration_lock_context_mismatch"
    with pytest.raises(MigrationLockError) as acquire:
        foreign_context.acquire()
    assert acquire.value.code == "migration_lock_context_mismatch"
    owner.release()


@pytest.mark.parametrize("method", ["acquire", "verify_owner", "release"])
def test_unsupported_migration_lock_fails_closed(method: str) -> None:
    lock = UnsupportedMigrationLock()
    inspection = lock.inspect()
    assert inspection.status is MigrationLockStatus.BLOCKED
    assert inspection.error_code == "migration_lock_platform_unsupported"
    with pytest.raises(MigrationLockError) as caught:
        getattr(lock, method)()
    assert caught.value.code == "migration_lock_platform_unsupported"
