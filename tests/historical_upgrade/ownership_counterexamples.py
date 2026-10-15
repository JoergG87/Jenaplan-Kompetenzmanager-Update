"""Unresolved Darwin ownership contract: intentionally red until P1 is fixed.

Real synthetic roots and kernel locks; no product keys, product roots, or skips.
These assertions express required rejection, never acceptance of the defect.
"""
import fcntl
import os
import select
import subprocess
import sys

import pytest

from src.application.commands.schema_upgrade import UpgradeMaintenance
from src.core.maintenance_gate import MaintenanceGate
from src.core.schema_upgrade import UpgradeError
from tests.test_schema_upgrade_foundation import (
    auth_key, context, full_states, repository, setup_runtime,
)


@pytest.mark.parametrize("forked", [False, True])
def test_darwin_unlock_event_survives_relock(maintenance, forked):
    """Qualify a narrow candidate mechanism, not the complete process contract."""
    ctx, root, lock, lease = maintenance
    descriptor = lock.fileno
    queue = select.kqueue()
    try:
        # sys/event.h NOTE_FUNLOCK; Python select does not export this constant.
        queue.control([select.kevent(descriptor, filter=select.KQ_FILTER_VNODE,
                                    flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                                    fflags=0x100)], 0, 0)
        assert not queue.control([], 1, 0)
        if forked:
            pid = os.fork()
            if pid == 0:
                try:
                    duplicate = os.dup(descriptor)
                    fcntl.flock(duplicate, fcntl.LOCK_UN)
                    fcntl.flock(duplicate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BaseException:
                    os._exit(1)
                os._exit(0)
            _, status = os.waitpid(pid, 0)
            assert status == 0
        else:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert any(event.fflags & 0x100 for event in queue.control([], 1, 0))
    finally:
        queue.close()


@pytest.fixture
def maintenance(tmp_path):
    assert sys.platform == "darwin", "This evidence requires real Darwin processes"
    ctx = context()
    root, lock, lease = setup_runtime(tmp_path.resolve(), ctx)
    try:
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            lease.require_owner(ctx)
            yield ctx, root, lock, lease
    finally:
        lock.release()


@pytest.mark.parametrize("which", ["runtime", "writer"])
def test_direct_relock_must_revoke_original_authority(maintenance, which):
    ctx, root, lock, lease = maintenance
    fd = lock.fileno if which == "runtime" else lease.writer._fd
    assert not os.get_inheritable(fd)
    fcntl.flock(fd, fcntl.LOCK_UN)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with pytest.raises(UpgradeError):
        lease.require_owner(ctx)


@pytest.mark.parametrize("which", ["runtime", "writer"])
def test_fork_dup_relock_must_revoke_original_authority(maintenance, which):
    ctx, root, lock, lease = maintenance
    fd = lock.fileno if which == "runtime" else lease.writer._fd
    assert not os.get_inheritable(fd)
    pid = os.fork()
    if pid == 0:
        try:
            duplicate = os.dup(fd)
            fcntl.flock(duplicate, fcntl.LOCK_UN)
            fcntl.flock(duplicate, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os._exit(1)
        os._exit(0)
    _, status = os.waitpid(pid, 0)
    assert status == 0
    with pytest.raises(UpgradeError):
        lease.require_owner(ctx)


@pytest.mark.parametrize("which", ["runtime", "writer", "both"])
def test_foreign_current_holder_must_not_authorize_original_lease(maintenance, which):
    ctx, root, lock, lease = maintenance
    pairs = [(lock.fileno, lock.path), (lease.writer._fd, lease.writer.lock_path)]
    selected = pairs if which == "both" else [pairs[which == "writer"]]
    for fd, path in selected:
        fcntl.flock(fd, fcntl.LOCK_UN)
    # Fresh exec, close_fds, no pass_fds: foreign independent open descriptions.
    code = (
        "import sys,os,fcntl; "
        "fds=[os.open(p,os.O_RDWR) for p in sys.argv[1:]]; "
        "[fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB) for fd in fds]; "
        "print('held',flush=True); sys.stdin.read(1)"
    )
    child = subprocess.Popen([sys.executable, "-c", code, *[str(p) for _, p in selected]],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, close_fds=True)
    try:
        assert child.stdout.readline().strip() == "held"
        with pytest.raises(UpgradeError):
            lease.require_owner(ctx)
    finally:
        child.communicate("x", timeout=10)
        assert child.returncode == 0


@pytest.mark.parametrize("which", ["runtime", "writer"])
def test_journal_must_not_mutate_after_lock_loss_at_anchor_boundary(maintenance, which):
    ctx, root, lock, lease = maintenance
    repo = repository(root, ctx, lease)
    key = auth_key(ctx)
    states, _ = full_states(ctx)
    repo.create(states[0], key)
    before = repo.path.read_bytes()

    def lose_lock(boundary):
        if boundary == "after_anchor_write":
            fd = lock.fileno if which == "runtime" else lease.writer._fd
            fcntl.flock(fd, fcntl.LOCK_UN)

    repo._fault_hook = lose_lock
    try:
        repo.save(states[0], states[1], key)
    except UpgradeError:
        pass
    assert repo.path.read_bytes() == before, "Journal advanced after kernel lock loss"
