"""Real synthetic lock lifecycle continuity checks; no product roots or keys."""
import os
from uuid import uuid4
import pytest
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.schema_upgrade import UpgradeContext, UpgradeError
from tests.historical_upgrade.upgrade_process_lease import UpgradeProcessLease


def context():
    identity = FINAL_V4_SCHEMA_REGISTRATION.identity
    return UpgradeContext(*(str(uuid4()) for _ in range(4)), 1, str(uuid4()), 1,
                          identity, identity, "synthetic_lock_check")


def lease_for(lock, ctx):
    return UpgradeProcessLease(lock, ctx, lock.runtime_root /
                              "final-v4-sqlcipher-runtime-v1" / ".observation-staging")


def test_release_reacquire_same_object_revokes_existing_lease(tmp_path):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        with lease_for(lock, ctx) as lease:
            lease.require_owner(ctx)
            original_generation = lock.authority_generation
            lock.release()
            lock.acquire()
            assert lock.authority_generation > original_generation
            with pytest.raises(UpgradeError, match="upgrade_runtime_lock_required"):
                lease.require_owner(ctx)


def test_idempotent_acquire_preserves_lease(tmp_path):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        with lease_for(lock, ctx) as lease:
            generation = lock.authority_generation
            lock.acquire()
            assert lock.authority_generation == generation
            lease.require_owner(ctx)


def test_transfer_revokes_existing_lease(tmp_path):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        with lease_for(lock, ctx) as lease:
            retained_fd = os.dup(lock.fileno)
            try:
                lock.transfer()
                with pytest.raises(UpgradeError, match="upgrade_runtime_lock_required"):
                    lease.require_owner(ctx)
            finally:
                os.close(retained_fd)


def test_root_inode_replacement_revokes_lease(tmp_path):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        lease = lease_for(lock, ctx)
        moved = tmp_path / "original"
        root.rename(moved)
        root.mkdir(mode=0o700)
        (root / ".jkm-runtime-root-v1").write_bytes(
            (moved / ".jkm-runtime-root-v1").read_bytes())
        (root / ".jkm-runtime-root-v1").chmod(0o600)
        with pytest.raises(UpgradeError, match="upgrade_runtime_lock_required"):
            lease.__enter__()


@pytest.mark.parametrize("which", ["runtime", "writer"])
def test_direct_kernel_unlock_is_rejected(tmp_path, which):
    import fcntl
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        with lease_for(lock, ctx) as lease:
            descriptor = lock.fileno if which == "runtime" else lease.writer._fd
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            with pytest.raises(UpgradeError, match="upgrade_kernel_lock_required"):
                lease.require_owner(ctx)


def test_reused_descriptor_cannot_restore_lease(tmp_path):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        with lease_for(lock, ctx) as lease:
            original_fd = lock.fileno
            lock.release()
            unrelated = tmp_path / "unrelated"
            unrelated.write_bytes(b"unrelated")
            opened = os.open(unrelated, os.O_RDONLY)
            try:
                # Force the old descriptor number to name another inode.
                if opened != original_fd:
                    os.dup2(opened, original_fd)
                with pytest.raises(UpgradeError, match="upgrade_runtime_lock_required"):
                    lease.require_owner(ctx)
            finally:
                os.close(opened)
                if opened != original_fd:
                    os.close(original_fd)


@pytest.mark.parametrize("reacquire", [False, True])
def test_writer_context_release_revokes_lease(tmp_path, reacquire):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    ctx = context()
    with RuntimeInstanceLock(root) as lock:
        with lease_for(lock, ctx) as lease:
            lease.writer.__exit__(None, None, None)
            if reacquire:
                lease.writer.__enter__()
            with pytest.raises(UpgradeError, match="upgrade_process_context_mismatch"):
                lease.require_owner(ctx)
