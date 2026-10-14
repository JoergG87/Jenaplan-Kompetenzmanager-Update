"""Synthetic-only real HMAC/filesystem and subprocess termination checks."""
from dataclasses import replace
import multiprocessing
import os
from pathlib import Path
from uuid import uuid4
import pytest

from tests.test_schema_upgrade_foundation import (context, registry, full_states,
    auth_key, setup_runtime, repository, receipt)
from src.core.schema_upgrade import UpgradePhase, UpgradeRecoveryStatus, advance_upgrade
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION, PRODUCT_SCHEMA_REGISTRY
from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.maintenance_gate import MaintenanceGate
from src.application.commands.schema_upgrade import UpgradeMaintenance
from src.application.commands.upgrade_startup_guard import UpgradeStartupGuard
from src.security.infrastructure.upgrade_process_lease import UpgradeProcessLease


def evaluate(repo, key, observed=(), **changes):
    args = dict(observed=observed, inventory_complete=True,
        live_schema=FINAL_V4_SCHEMA_REGISTRATION.identity, restore_clear=True)
    args.update(changes)
    decision = UpgradeStartupGuard(repo).evaluate(key, **args)
    assert not decision.first_run_allowed
    assert not decision.normal_runtime_allowed
    assert not decision.activation_allowed
    return decision


@pytest.fixture
def case(tmp_path):
    ctx = context(); root, lock, lease = setup_runtime(tmp_path, ctx)
    key = auth_key(ctx)
    try:
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            yield ctx, root, lease, repository(root, ctx, lease), key
    finally:
        lock.release()


def test_absence_requires_complete_consistent_inventory(case):
    ctx, root, lease, repo, key = case
    assert evaluate(repo, key).continue_existing_startup
    for changes in (dict(inventory_complete=False), dict(restore_clear=False),
            dict(live_schema=None), dict(live_schema=ctx.target)):
        assert not evaluate(repo, key, **changes).continue_existing_startup
    assert not PRODUCT_SCHEMA_REGISTRY.upgrades
    for name in ('schema-upgrade-source', 'schema-upgrade-replay', 'schema-upgrade-foundation'):
        path = root / name; path.mkdir(mode=0o700)
        assert not evaluate(repo, key).continue_existing_startup
        path.rmdir()  # test fixture only; guard never cleans


@pytest.mark.parametrize('index', range(11))
def test_current_generation_and_terminal_states_never_admit(case, index):
    ctx, root, lease, repo, key = case
    states, _ = full_states(ctx)
    repo.create(states[0], key)
    for before, after in zip(states[:index], states[1:index+1]):
        repo.save(before, after, key)
    assert repo.load(key) == states[index]
    raw = repo.path.read_bytes(); anchor = repo.anchor.path.read_bytes()
    repo.save(states[index], states[index], key)
    assert repo.path.read_bytes() == raw and repo.anchor.path.read_bytes() == anchor
    recorded = {a.role: a for e in states[index].evidence for a in e.artifacts}
    schema_args = dict(live_schema=ctx.target) if index == 10 else {}
    result = evaluate(repo, key, tuple(recorded.values()), **schema_args)
    assert not result.continue_existing_startup
    if index == 10:
        assert result.status is UpgradeRecoveryStatus.COMPLETED
    for role in ('source', 'backup', 'candidate'):
        if role in recorded:
            missing = tuple(a for k, a in recorded.items() if k != role)
            # Completed state requires live instead of candidate; source and backup always required.
            if index != 10 or role != 'candidate':
                assert evaluate(repo, key, missing, **schema_args).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


@pytest.mark.parametrize('damage', ['old_journal', 'old_anchor', 'journal', 'anchor',
    'missing_anchor', 'missing_journal', 'anchor_permissions', 'journal_symlink', 'unknown_file'])
def test_tamper_replay_and_missing_evidence(case, damage):
    ctx, root, lease, repo, key = case
    states, _ = full_states(ctx); repo.create(states[0], key)
    old_journal = repo.path.read_bytes(); old_anchor = repo.anchor.path.read_bytes()
    repo.save(states[0], states[1], key)
    if damage == 'old_journal': repo.path.write_bytes(old_journal)
    if damage == 'old_anchor': repo.anchor.path.write_bytes(old_anchor)
    if damage == 'journal': repo.path.write_bytes(b'corrupt')
    if damage == 'anchor': repo.anchor.path.write_bytes(b'corrupt')
    if damage == 'missing_anchor': repo.anchor.path.unlink()
    if damage == 'missing_journal': repo.path.unlink()
    if damage == 'anchor_permissions': repo.anchor.path.chmod(0o644)
    if damage == 'journal_symlink':
        repo.path.unlink(); repo.path.symlink_to(repo.anchor.path)
    if damage == 'unknown_file': (repo.path.parent / 'unexpected').write_bytes(b'?')
    assert evaluate(repo, key).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    with pytest.raises(Exception): repo.create(states[0], key)


@pytest.mark.parametrize('field', ['installation_id', 'database_context_id', 'database_key_id',
    'dmk_key_id', 'operation_id', 'database_key_generation', 'dmk_generation', 'target'])
def test_wrong_context_or_unknown_target(case, field):
    ctx, root, lease, repo, key = case
    states, _ = full_states(ctx); repo.create(states[0], key)
    value = (2 if 'generation' in field else
             replace(ctx.target, fingerprint='f'*64) if field == 'target' else str(uuid4()))
    other = replace(ctx, **{field: value})
    # Rebind the lease's expected operation only in this synthetic test to reach journal checks.
    lease.context = other
    wrong = repository(root, other, lease)
    assert evaluate(wrong, key).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_wrong_key_and_aborted_evidence(case):
    ctx, root, lease, repo, key = case
    states, _ = full_states(ctx); repo.create(states[0], key)
    assert evaluate(repo, auth_key(ctx)).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    for a, b in zip(states[:2], states[1:3]): repo.save(a, b, key)
    aborted = advance_upgrade(states[2], receipt(ctx, UpgradePhase.ABORTED), registry())
    repo.save(states[2], aborted, key)
    source = states[2].evidence[-1].artifacts
    assert evaluate(repo, key, source).status is UpgradeRecoveryStatus.ABORTED
    assert evaluate(repo, key).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_complete_local_rollback_is_explicitly_outside_guarantee(case):
    ctx, root, lease, repo, key = case
    states, _ = full_states(ctx); repo.create(states[0], key)
    old = repo.path.read_bytes(), repo.anchor.path.read_bytes()
    repo.save(states[0], states[1], key)
    repo.path.write_bytes(old[0]); repo.anchor.path.write_bytes(old[1])
    assert repo.load(key) == states[0]  # no platform counter, cannot detect whole-root rollback
    assert not evaluate(repo, key).continue_existing_startup


def _crash(root, ctx, key, boundary, update):
    root = Path(root)
    with RuntimeInstanceLock(root) as lock:
        lease = UpgradeProcessLease(lock, ctx, root / 'final-v4-sqlcipher-runtime-v1' / '.observation-staging')
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            repo = repository(root, ctx, lease); states, _ = full_states(ctx)
            if update: repo.create(states[0], key)
            def hook(point):
                if point == boundary: os._exit(73)
            repo._fault_hook = hook
            if boundary in {'during_anchor_write', 'during_journal_write'}:
                target = repo.anchor if boundary == 'during_anchor_write' else repo
                original = target._write_temporary
                def temporary(data):
                    original(data)  # real fsynced temp file; abrupt exit, no cleanup
                    os._exit(73)
                target._write_temporary = temporary
            if update: repo.save(states[0], states[1], key)
            else: repo.create(states[0], key)


@pytest.mark.parametrize('update', [False, True])
@pytest.mark.parametrize('boundary', ['before_first_anchor', 'before_anchor_write',
    'during_anchor_write', 'after_anchor_write', 'during_journal_write', 'after_journal_write'])
def test_real_process_termination_and_restart(tmp_path, update, boundary):
    if update and boundary == 'before_first_anchor':
        boundary = 'before_anchor_write'  # first-anchor boundary only exists at initialization
    ctx = context(); key = auth_key(ctx); root = tmp_path / 'runtime'
    prepare_synthetic_test_root(root)
    spawn = multiprocessing.get_context('spawn')
    child = spawn.Process(target=_crash, args=(str(root), ctx, key, boundary, update))
    child.start(); child.join(20)
    if child.is_alive(): child.kill(); child.join(10)
    assert child.exitcode == 73
    with RuntimeInstanceLock(root) as lock:
        lease = UpgradeProcessLease(lock, ctx, root / 'final-v4-sqlcipher-runtime-v1' / '.observation-staging')
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            repo = repository(root, ctx, lease)
            result = evaluate(repo, key)
            if not update and boundary == 'before_first_anchor':
                assert result.status is UpgradeRecoveryStatus.NO_OPERATION
            else:
                assert result.status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
            if boundary == 'after_journal_write' or (update and boundary == 'before_anchor_write'):
                assert repo.load(key).revision == (1 if update and boundary == 'after_journal_write' else 0)
            elif boundary != 'before_first_anchor':
                with pytest.raises(Exception): repo.load(key)


def test_guard_and_anchor_deny_without_active_lease(tmp_path):
    ctx = context(); root, lock, lease = setup_runtime(tmp_path, ctx)
    try:
        repo = repository(root, ctx, lease); key = auth_key(ctx)
        assert evaluate(repo, key).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
        with pytest.raises(Exception): repo.anchor.load(key)
    finally:
        lock.release()


@pytest.mark.parametrize('observed', [None, [], (None,)])
def test_invalid_inventory_is_not_absence(case, observed):
    _, _, _, repo, key = case
    assert evaluate(repo, key, observed).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_valid_hmac_same_revision_different_evidence_blocks(case):
    ctx, _, _, repo, key = case
    states, _ = full_states(ctx)
    repo.create(states[0], key)
    repo.save(states[0], states[1], key)
    repo.save(states[1], states[2], key)
    source = states[2].evidence[-1].artifacts[0]
    changed = replace(states[2], evidence=(states[2].evidence[0],
        replace(states[2].evidence[1], artifacts=(replace(source, sha256='e'*64),))))
    repo.path.write_bytes(repo._encode(changed, key))
    assert evaluate(repo, key).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_completed_requires_live_schema_matching_journal_and_artifacts(case):
    ctx, _, _, repo, key = case
    states, _ = full_states(ctx); repo.create(states[0], key)
    for before, after in zip(states, states[1:]): repo.save(before, after, key)
    recorded = {a.role: a for e in states[-1].evidence for a in e.artifacts}
    observed = tuple(recorded.values())
    assert evaluate(repo, key, observed).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    result = evaluate(repo, key, observed, live_schema=ctx.target)
    assert result.status is UpgradeRecoveryStatus.COMPLETED
    assert not result.continue_existing_startup
