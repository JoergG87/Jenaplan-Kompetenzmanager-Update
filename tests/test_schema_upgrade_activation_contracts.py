"""A0 pure receipts plus real synthetic HMAC/CAS/replay persistence, no activation."""
from dataclasses import asdict, replace
import base64
import hashlib
import hmac
import json
from uuid import uuid4

import pytest

from src.core.schema_upgrade import (
    UpgradeArtifact, UpgradeEvidence, UpgradeExchangeIntent, UpgradeExchangeResult,
    UpgradePhase, UpgradeRecoveryStatus, UpgradeRestartReceipt, UpgradeState,
    UpgradeTargetInspection, UpgradeError, advance_upgrade, classify_upgrade,
    new_upgrade_state, source_rollback_forbidden, validate_upgrade_state,
)
from src.core.schema_registry import PRODUCT_SCHEMA_REGISTRY, FINAL_V4_SCHEMA_REGISTRATION
from src.application.commands.schema_upgrade import UpgradeMaintenance
from src.application.commands.upgrade_startup_guard import UpgradeStartupGuard
from src.core.maintenance_gate import MaintenanceGate
from src.security.infrastructure.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository
from src.security.infrastructure.migration_journal_repository import MigrationJournalError
from tests.test_schema_upgrade_foundation import (
    context, registry, full_states, receipt, artifact, setup_runtime, repository, auth_key,
)


@pytest.fixture
def history():
    ctx = context()
    states, parts = full_states(ctx)
    return ctx, states, parts


@pytest.fixture
def persisted(tmp_path):
    ctx = context()
    root, lock, lease = setup_runtime(tmp_path, ctx)
    try:
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            yield ctx, root, repository(root, ctx, lease), auth_key(ctx)
    finally:
        lock.release()


def classify(state, observed, inspection=None, **changes):
    args = dict(expected_context=state.context, observed=observed, registry=registry(),
                inventory_complete=True, journal_authenticated=True, target_inspection=inspection)
    args.update(changes)
    result = classify_upgrade(state, **args)
    assert not result.activation_allowed
    assert not result.normal_runtime_allowed
    assert not result.writer_admission_allowed
    assert not result.automatic_source_rollback_allowed
    return result


def records(state):
    return {a.role: a for e in state.evidence for a in e.artifacts}


@pytest.mark.parametrize('field', ['operation_id', 'installation_id', 'database_context_id',
    'database_key_id', 'dmk_key_id', 'database_key_generation', 'dmk_generation', 'source', 'target'])
def test_rollback_context_must_match_entire_operation(history, field):
    ctx, states, _ = history
    value = (2 if 'generation' in field else replace(getattr(ctx, field), fingerprint='f'*64)
             if field in {'source', 'target'} else str(uuid4()))
    evidence = replace(states[7].evidence[-1], context=replace(ctx, **{field: value}))
    with pytest.raises(UpgradeError, match='context_mismatch'):
        advance_upgrade(states[6], evidence, registry())


def test_rollback_is_distinct_encrypted_copy_receipt(history):
    ctx, states, _ = history
    data = records(states[7])
    rollback, source = data['rollback'], data['source']
    assert rollback.sha256 == source.sha256 and rollback.schema == ctx.source
    assert rollback.artifact_id != source.artifact_id
    assert rollback.file_id != source.file_id
    validate_upgrade_state(states[7], registry())


@pytest.mark.parametrize('damage', ['missing', 'hash', 'size', 'schema', 'artifact_id', 'inode', 'candidate_inode', 'backup_inode', 'device'])
def test_missing_or_manipulated_rollback_receipt(history, damage):
    ctx, states, _ = history
    evidence = states[7].evidence[-1]
    data = records(states[7]); rollback = data['rollback']
    if damage == 'missing':
        evidence = replace(evidence, artifacts=tuple(a for a in evidence.artifacts if a.role != 'rollback'))
    else:
        changes = {'hash': dict(sha256='f'*64), 'size': dict(size_bytes=8192),
            'schema': dict(schema=ctx.target), 'artifact_id': dict(artifact_id=data['source'].artifact_id),
            'inode': dict(file_id=data['source'].file_id),
            'candidate_inode': dict(file_id=data['candidate'].file_id),
            'backup_inode': dict(file_id=data['backup'].file_id), 'device': dict(device_id=2)}[damage]
        evidence = replace(evidence, artifacts=tuple(replace(rollback, **changes) if a.role == 'rollback' else a for a in evidence.artifacts))
    with pytest.raises(UpgradeError):
        advance_upgrade(states[6], evidence, registry())


def test_intent_is_not_a_result_or_admission(history):
    ctx, states, _ = history
    assert states[7].phase is UpgradePhase.ACTIVATION_PREPARED
    assert states[8].phase is UpgradePhase.ACTIVATION_INTENT
    assert states[9].phase is UpgradePhase.TARGET_INSTALLED
    assert classify(states[8], tuple(records(states[7]).values())).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify(states[9], tuple(records(states[9]).values())).status is UpgradeRecoveryStatus.INSTALLED
    with pytest.raises(UpgradeError):
        advance_upgrade(states[8], receipt(ctx, UpgradePhase.TARGET_INSTALLED), registry())


@pytest.mark.parametrize('damage', ['id', 'context', 'hash', 'schema', 'inode'])
def test_exchange_result_is_bound_to_actual_intent(history, damage):
    ctx, states, _ = history
    evidence = states[9].evidence[-1]; result = evidence.exchange_result
    if damage == 'id':
        result = replace(result, intent_id=str(uuid4()))
    elif damage == 'context':
        result = replace(result, context=replace(ctx, installation_id=str(uuid4())))
    else:
        changes = {'hash': dict(sha256='f'*64), 'schema': dict(schema=ctx.source), 'inode': dict(file_id=99)}[damage]
        result = replace(result, installed=replace(result.installed, **changes))
    with pytest.raises(UpgradeError):
        advance_upgrade(states[8], replace(evidence, exchange_result=result), registry())


@pytest.mark.parametrize('index', range(2, 14))
def test_new_phases_cannot_be_skipped(history, index):
    _, states, _ = history
    with pytest.raises(UpgradeError):
        advance_upgrade(states[index-2], states[index].evidence[-1], registry())


@pytest.mark.parametrize('damage', ['missing', 'wrong_target', 'wrong_context'])
def test_restart_must_confirm_installed_target(history, damage):
    ctx, states, _ = history
    evidence = states[10].evidence[-1]
    restart = evidence.restart
    if damage == 'missing': restart = None
    if damage == 'wrong_target': restart = replace(restart, installed=replace(restart.installed, sha256='f'*64))
    if damage == 'wrong_context': restart = replace(restart, context=replace(ctx, operation_id=str(uuid4())))
    with pytest.raises(UpgradeError):
        advance_upgrade(states[9], replace(evidence, restart=restart), registry())


@pytest.mark.parametrize('field', ['integrity_verified', 'key_context_verified', 'domain_verified', 'documents_verified'])
@pytest.mark.parametrize('value', [False, None, 1])
def test_failed_or_unknown_runtime_checks_cannot_be_receipts(history, field, value):
    _, states, _ = history
    with pytest.raises(UpgradeError, match='inspection_invalid'):
        replace(states[11].evidence[-1].inspection, **{field: value})


def test_restart_success_without_runtime_checks_cannot_enable_writes(history):
    ctx, states, _ = history
    with pytest.raises(UpgradeError):
        advance_upgrade(states[10], states[12].evidence[-1], registry())
    with pytest.raises(UpgradeError):
        advance_upgrade(states[11], receipt(ctx, UpgradePhase.WRITES_ENABLED), registry())
    wrong = replace(states[11].evidence[-1].inspection, restart_id=str(uuid4()))
    with pytest.raises(UpgradeError):
        advance_upgrade(states[10], replace(states[11].evidence[-1], inspection=wrong), registry())
    with pytest.raises(UpgradeError):
        advance_upgrade(states[11], replace(states[12].evidence[-1],
            inspection=replace(states[12].evidence[-1].inspection, inspection_id=str(uuid4()))), registry())


@pytest.mark.parametrize('index', [8, 9, 10, 11])
def test_active_rollback_has_own_intent_result_and_terminal_phase(history, index):
    ctx, states, _ = history
    data = records(states[index]); expected = data['source'] if index == 8 else data['live']
    intent = UpgradeExchangeIntent(ctx, str(uuid4()), 'rollback', expected, data['rollback'])
    rolling = advance_upgrade(states[index], UpgradeEvidence(ctx, UpgradePhase.ROLLBACK_INTENT, exchange_intent=intent), registry())
    installed = replace(data['rollback'], role='rollback_live')
    rolled = advance_upgrade(rolling, UpgradeEvidence(ctx, UpgradePhase.ROLLBACK_INSTALLED,
        (installed,), exchange_result=UpgradeExchangeResult(ctx, intent.intent_id, installed)), registry())
    rolled = advance_upgrade(rolled, receipt(ctx, UpgradePhase.ROLLED_BACK, (installed,)), registry())
    assert rolled.phase is UpgradePhase.ROLLED_BACK
    assert classify(rolled, (data['backup'], installed)).status is UpgradeRecoveryStatus.ROLLED_BACK
    for start in (states[index], rolling, rolled):
        with pytest.raises(UpgradeError): advance_upgrade(start, receipt(ctx, UpgradePhase.ABORTED), registry())


def test_rollback_needs_its_own_intent_and_observed_result(history):
    ctx, states, _ = history
    for phase in (UpgradePhase.ROLLBACK_INTENT, UpgradePhase.ROLLBACK_INSTALLED, UpgradePhase.ROLLED_BACK):
        with pytest.raises(UpgradeError): advance_upgrade(states[9], receipt(ctx, phase), registry())


@pytest.mark.parametrize('index', [12, 13])
def test_write_fence_forbids_rollback_even_without_observed_business_write(history, index):
    ctx, states, _ = history
    assert not source_rollback_forbidden(states[11])
    assert source_rollback_forbidden(states[index])
    with pytest.raises(UpgradeError):
        advance_upgrade(states[index], receipt(ctx, UpgradePhase.ROLLBACK_INTENT), registry())
    with pytest.raises(UpgradeError):
        advance_upgrade(states[index], receipt(ctx, UpgradePhase.ABORTED), registry())
    if index == 12:
        failed = advance_upgrade(states[index], receipt(ctx, UpgradePhase.RECOVERY_REQUIRED), registry())
        assert source_rollback_forbidden(failed)
        assert classify(failed, ()).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_fence_survives_real_persistence_retry_and_replay(persisted):
    ctx, _, repo, key = persisted; states, _ = full_states(ctx)
    repo.create(states[0], key)
    for previous, current in zip(states[:12], states[1:13]): repo.save(previous, current, key)
    assert source_rollback_forbidden(repo.load(key))
    before = repo.path.read_bytes(), repo.anchor.path.read_bytes()
    repo.save(states[12], states[12], key)
    assert before == (repo.path.read_bytes(), repo.anchor.path.read_bytes())
    assert b'schema-upgrade-v2' in before[0] and b'writes_enabled' in before[0]
    assert key.key_material not in before[0]
    with pytest.raises(MigrationJournalError): repo.save(states[11], states[12], key)
    repo.path.write_bytes(repo._encode(states[11], key))
    with pytest.raises(UpgradeError, match='replay_or_generation_conflict'): repo.load(key)


def test_every_new_receipt_roundtrips_under_real_journal_anchor(persisted):
    ctx, _, repo, key = persisted; states, _ = full_states(ctx)
    repo.create(states[0], key)
    for previous, current in zip(states, states[1:]):
        repo.save(previous, current, key)
        assert repo.load(key) == current
        assert repo.anchor.load(key).revision == current.revision
        assert advance_upgrade(current, current.evidence[-1], registry()) is current


def test_fresh_mutable_target_is_not_compared_to_frozen_candidate(history):
    ctx, states, _ = history
    state = states[-1]; initial = states[11].evidence[-1].inspection
    changed = replace(initial.target, sha256='e'*64, file_id=99, size_bytes=8192)
    fresh = replace(initial, inspection_id=str(uuid4()), restart_id=str(uuid4()), target=changed)
    assert classify(state, (changed,), fresh).status is UpgradeRecoveryStatus.COMPLETED
    assert classify(states[12], (changed,), fresh).status is UpgradeRecoveryStatus.WRITES_ENABLED
    assert records(state)['candidate'].sha256 != changed.sha256
    assert classify(state, (changed,)).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify(state, (changed,), fresh, journal_authenticated=False).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert source_rollback_forbidden(state)
    wrong = replace(fresh, target=replace(changed, artifact_id=str(uuid4())))
    assert classify(state, (wrong.target,), wrong).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify(states[11], (changed,), fresh).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


@pytest.mark.parametrize('damage', ['context', 'observed_hash', 'unknown_schema', 'inventory'])
def test_mutable_target_still_needs_exact_context_schema_and_checks(history, damage):
    ctx, states, _ = history; fresh = states[11].evidence[-1].inspection
    observed = (fresh.target,); changes = {}
    if damage == 'context': fresh = replace(fresh, context=replace(ctx, database_key_generation=2))
    if damage == 'observed_hash': observed = (replace(fresh.target, sha256='f'*64),)
    if damage == 'unknown_schema':
        other = replace(ctx, target=replace(ctx.target, fingerprint='f'*64))
        fresh = replace(fresh, context=other, target=replace(fresh.target, schema=other.target))
        observed = (fresh.target,)
    if damage == 'inventory': changes['inventory_complete'] = False
    assert classify(states[-1], observed, fresh, **changes).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def legacy_states(ctx):
    # Independent historical graph/field shape, not generated by the v2 transition map.
    source, backup = artifact(ctx, 'source'), artifact(ctx, 'backup')
    candidate = artifact(ctx, 'candidate', ctx.source)
    migrated = replace(candidate, schema=ctx.target, sha256='c'*64)
    live = replace(migrated, role='live')
    phases = [UpgradePhase.EXCLUSIVE, UpgradePhase.SOURCE_VERIFIED, UpgradePhase.BACKUP_VERIFIED,
        UpgradePhase.STAGED, UpgradePhase.MIGRATED, UpgradePhase.TARGET_VERIFIED,
        UpgradePhase.ACTIVATION_PREPARED, UpgradePhase.ACTIVATING,
        UpgradePhase.RUNTIME_VERIFIED, UpgradePhase.COMPLETED]
    evidence = []
    states = [UpgradeState(ctx, contract_version=1)]
    for phase in phases:
        value = {UpgradePhase.SOURCE_VERIFIED: source, UpgradePhase.BACKUP_VERIFIED: backup,
            UpgradePhase.STAGED: candidate, UpgradePhase.RUNTIME_VERIFIED: live,
            UpgradePhase.COMPLETED: live}.get(phase, migrated)
        evidence.append(receipt(ctx, phase, () if phase is UpgradePhase.EXCLUSIVE else (value,)))
        states.append(UpgradeState(ctx, phase, len(evidence), tuple(evidence), 1))
    return states


def old_bytes(state, key):
    raw = asdict(state); raw.pop('contract_version')
    for item in raw['evidence']:
        for field in ('exchange_intent', 'exchange_result', 'restart', 'inspection'): item.pop(field)
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    payload = {'protocol': 'schema-upgrade-v1', 'state': raw}
    tag = base64.urlsafe_b64encode(hmac.new(key.key_material, canonical(payload), hashlib.sha256).digest()).decode('ascii').rstrip('=')
    return canonical({**payload, 'auth_tag': tag})


def test_legacy_authentication_and_exact_bytes_remain_compatible():
    ctx = context(); key = auth_key(ctx)
    for state in legacy_states(ctx):
        raw = old_bytes(state, key)
        assert AuthenticatedUpgradeJournalRepository._decode(raw, key) == state
        assert AuthenticatedUpgradeJournalRepository._encode(state, key) == raw
        assert source_rollback_forbidden(state)  # legacy has no trustworthy write boundary
    with pytest.raises(UpgradeError):
        advance_upgrade(legacy_states(ctx)[4], receipt(ctx, UpgradePhase.MIGRATED,
            (artifact(ctx, 'candidate'),)), registry())


def test_legacy_staged_preparation_can_persist_without_upgrade(persisted):
    ctx, _, repo, key = persisted; states = legacy_states(ctx)
    repo.create(states[0], key)
    for previous, current in zip(states[:4], states[1:5]): repo.save(previous, current, key)
    assert repo.load(key) == states[4]
    assert b'schema-upgrade-v1' in repo.path.read_bytes()
    with pytest.raises(UpgradeError): repo.save(states[4], replace(states[4], contract_version=2), key)


@pytest.mark.parametrize('damage', ['version', 'extra_field', 'missing_field', 'nested_field', 'contradiction'])
def test_codec_rejects_unknown_or_contradictory_payloads(history, damage):
    _, states, _ = history
    raw = AuthenticatedUpgradeJournalRepository._payload(states[9])
    if damage == 'version': raw['protocol'] = 'schema-upgrade-v3'
    if damage == 'extra_field': raw['state']['unregistered'] = True
    if damage == 'missing_field': del raw['state']['evidence'][-1]['exchange_result']
    if damage == 'nested_field': raw['state']['evidence'][-1]['exchange_result']['surprise'] = True
    if damage == 'contradiction': raw['state']['evidence'][-1]['exchange_result']['intent_id'] = str(uuid4())
    with pytest.raises(UpgradeError): AuthenticatedUpgradeJournalRepository._restore_payload(raw)


def test_unknown_target_and_product_registry_never_gain_an_upgrade(history):
    ctx, states, _ = history
    assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
    assert not PRODUCT_SCHEMA_REGISTRY.upgrades
    with pytest.raises(ValueError): validate_upgrade_state(states[-1], PRODUCT_SCHEMA_REGISTRY)
    with pytest.raises(ValueError): new_upgrade_state(replace(ctx, target=replace(ctx.target, fingerprint='f'*64)), registry())
    assert source_rollback_forbidden(None)


def test_synthetic_completed_contract_never_admits_startup(persisted):
    ctx, _, repo, key = persisted; states, _ = full_states(ctx)
    repo.create(states[0], key)
    for previous, current in zip(states, states[1:]): repo.save(previous, current, key)
    result = UpgradeStartupGuard(repo).evaluate(key, observed=tuple(records(states[-1]).values()),
        inventory_complete=True, live_schema=ctx.target, restore_clear=True)
    assert not result.continue_existing_startup
    assert not result.normal_runtime_allowed and not result.first_run_allowed and not result.activation_allowed


@pytest.mark.parametrize('index', [7, 8, 9, 10, 11, 12])
def test_boundary_receipts_are_not_valid_in_unrelated_phases(history, index):
    ctx, states, _ = history
    evidence = states[index].evidence[-1]
    if index == 7:
        evidence = replace(evidence, exchange_intent=states[8].evidence[-1].exchange_intent)
    with pytest.raises(UpgradeError):
        advance_upgrade(states[1], replace(evidence, phase=UpgradePhase.SOURCE_VERIFIED,
            artifacts=(artifact(ctx, 'source'),)), registry())


def test_active_rollback_roundtrips_through_existing_anchor(persisted):
    ctx, _, repo, key = persisted; states, _ = full_states(ctx)
    repo.create(states[0], key)
    for previous, current in zip(states[:9], states[1:10]): repo.save(previous, current, key)
    state = states[9]; data = records(state)
    intent = UpgradeExchangeIntent(ctx, str(uuid4()), 'rollback', data['live'], data['rollback'])
    installed = replace(data['rollback'], role='rollback_live')
    receipts = (
        UpgradeEvidence(ctx, UpgradePhase.ROLLBACK_INTENT, exchange_intent=intent),
        UpgradeEvidence(ctx, UpgradePhase.ROLLBACK_INSTALLED, (installed,),
                        exchange_result=UpgradeExchangeResult(ctx, intent.intent_id, installed)),
        receipt(ctx, UpgradePhase.ROLLED_BACK, (installed,)),
    )
    for evidence in receipts:
        replacement = advance_upgrade(state, evidence, registry())
        repo.save(state, replacement, key)
        assert repo.load(key) == replacement
        state = replacement
    assert classify(state, (data['backup'], installed)).status is UpgradeRecoveryStatus.ROLLED_BACK


def test_fence_anchor_journal_crash_window_never_authorizes_rollback(persisted):
    ctx, _, repo, key = persisted; states, _ = full_states(ctx)
    repo.create(states[0], key)
    for previous, current in zip(states[:11], states[1:12]): repo.save(previous, current, key)
    def fault(boundary):
        if boundary == 'after_anchor_write': raise OSError('synthetic interruption')
    repo._fault_hook = fault
    with pytest.raises(OSError): repo.save(states[11], states[12], key)
    with pytest.raises(UpgradeError, match='replay_or_generation_conflict'): repo.load(key)
    decision = UpgradeStartupGuard(repo).evaluate(key, observed=tuple(records(states[11]).values()),
        inventory_complete=True, live_schema=ctx.target, restore_clear=True)
    assert decision.status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert not decision.activation_allowed and not decision.normal_runtime_allowed


def test_legacy_completed_is_still_classified_without_new_rights(persisted):
    ctx, _, repo, key = persisted; states = legacy_states(ctx)
    repo.create(states[0], key)
    # Simulate a pre-A0 historical snapshot, including its matching authenticated anchor.
    repo.path.write_bytes(old_bytes(states[-1], key))
    anchor = repo.anchor.for_journal(states[-1], hashlib.sha256(repo.path.read_bytes()).hexdigest())
    repo.anchor.path.write_bytes(repo.anchor._encode(anchor, key))
    historical = repo.load(key)
    result = classify(historical, tuple(records(historical).values()))
    assert result.status is UpgradeRecoveryStatus.COMPLETED
    assert source_rollback_forbidden(historical)
    assert b'schema-upgrade-v1' in repo.path.read_bytes()
