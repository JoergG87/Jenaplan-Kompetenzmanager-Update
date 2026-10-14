"""Synthetic state, real HMAC/persistence and real process-lock tests."""
from __future__ import annotations
from dataclasses import replace
import multiprocessing
import os
from pathlib import Path
from queue import Empty
import secrets
import signal
from uuid import uuid4
import pytest

from src.core.maintenance_gate import MaintenanceGate, MaintenancePurpose, MaintenanceState, MaintenanceWriterBlockedError, MaintenanceGateError
from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.observation_uow import ObservationWriterLock
from src.core.schema_registry import (DatabaseSchemaRegistry, FINAL_V4_SCHEMA_REGISTRATION,
    PRODUCT_SCHEMA_REGISTRY, RegisteredSchemaIdentity, SchemaRegistration, SchemaUpgradeRelation,
    SCHEMA_FINGERPRINT_ALGORITHM, SchemaAdmission, SchemaRegistryError)
from src.core.schema_upgrade import (UpgradeContext, UpgradePhase, UpgradeArtifact, UpgradeEvidence,
    UpgradeState, UpgradeError, UpgradeRecoveryStatus, new_upgrade_state, advance_upgrade,
    classify_upgrade, validate_upgrade_state, UpgradeExchangeIntent, UpgradeExchangeResult,
    UpgradeRestartReceipt, UpgradeTargetInspection)
from src.application.commands.schema_upgrade import UpgradeMaintenance
from src.security.infrastructure.upgrade_process_lease import UpgradeProcessLease
from src.security.infrastructure.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository
from src.security.infrastructure.migration_journal_repository import MigrationJournalError
from src.security.infrastructure.system import PlatformFilePermissionManager
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.data_keys import LoadedDataMasterKey


def registry(context=None):
    target = RegisteredSchemaIdentity(5, "b" * 64, SCHEMA_FINGERPRINT_ALGORITHM)
    other = SchemaRegistration("synthetic_only", target, frozenset())
    return DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION, other), (
        SchemaUpgradeRelation(FINAL_V4_SCHEMA_REGISTRATION.identity, target),))


def context():
    return UpgradeContext(*(str(uuid4()) for _ in range(4)), 1, str(uuid4()), 1,
        FINAL_V4_SCHEMA_REGISTRATION.identity, registry().schemas[1].identity, "synthetic_transform_v1")


def artifact(ctx, role, schema=None):
    return UpgradeArtifact(role, str(uuid4()), "a" * 64, 1, 2, 4096,
        schema or (ctx.source if role in {"source", "backup"} else ctx.target))


def receipt(ctx, phase, artifacts=()):
    return UpgradeEvidence(ctx, phase, artifacts)


def full_states(ctx):
    states = [new_upgrade_state(ctx, registry())]
    source = artifact(ctx, "source")
    backup = replace(artifact(ctx, "backup"), file_id=5, sha256="b" * 64)
    candidate = artifact(ctx, "candidate", ctx.source)
    migrated = replace(candidate, schema=ctx.target, sha256="c" * 64, file_id=3)
    # A migration keeps file identity; staging therefore starts with this inode.
    candidate = replace(candidate, file_id=3)
    live = replace(migrated, role="live")
    rollback = replace(source, role="rollback", artifact_id=str(uuid4()), file_id=4)
    intent = UpgradeExchangeIntent(ctx, str(uuid4()), "activate", source, migrated)
    restart = UpgradeRestartReceipt(ctx, str(uuid4()), live)
    inspection = UpgradeTargetInspection(ctx, str(uuid4()), restart.restart_id, live, True, True, True, True)
    receipts = (
        receipt(ctx, UpgradePhase.EXCLUSIVE),
        receipt(ctx, UpgradePhase.SOURCE_VERIFIED, (source,)),
        receipt(ctx, UpgradePhase.BACKUP_VERIFIED, (backup,)),
        receipt(ctx, UpgradePhase.STAGED, (candidate,)),
        receipt(ctx, UpgradePhase.MIGRATED, (migrated,)),
        receipt(ctx, UpgradePhase.TARGET_VERIFIED, (migrated,)),
        receipt(ctx, UpgradePhase.ACTIVATION_PREPARED, (source, backup, migrated, rollback)),
        UpgradeEvidence(ctx, UpgradePhase.ACTIVATION_INTENT, exchange_intent=intent),
        UpgradeEvidence(ctx, UpgradePhase.TARGET_INSTALLED, (live,),
                        exchange_result=UpgradeExchangeResult(ctx, intent.intent_id, live)),
        UpgradeEvidence(ctx, UpgradePhase.RESTART_CONFIRMED, restart=restart),
        UpgradeEvidence(ctx, UpgradePhase.RUNTIME_VERIFIED, (live,), inspection=inspection),
        UpgradeEvidence(ctx, UpgradePhase.WRITES_ENABLED, inspection=inspection),
        UpgradeEvidence(ctx, UpgradePhase.COMPLETED, inspection=inspection),
    )
    for evidence in receipts:
        states.append(advance_upgrade(states[-1], evidence, registry()))
    return states, (source, backup, migrated, live)


def test_all_ordered_transitions_and_exact_retries():
    states, _ = full_states(context())
    for state in states:
        validate_upgrade_state(state, registry())
        if state.evidence:
            assert advance_upgrade(state, state.evidence[-1], registry()) is state
    assert states[-1].phase is UpgradePhase.COMPLETED


@pytest.mark.parametrize("phase", list(UpgradePhase)[2:11])
def test_phase_skips_rejected(phase):
    ctx = context()
    with pytest.raises(UpgradeError):
        advance_upgrade(new_upgrade_state(ctx, registry()), receipt(ctx, phase), registry())


@pytest.mark.parametrize("field", ["operation_id", "installation_id", "database_context_id", "database_key_id", "dmk_key_id"])
def test_evidence_context_mismatch(field):
    ctx = context()
    with pytest.raises(UpgradeError, match="context_mismatch"):
        advance_upgrade(new_upgrade_state(ctx, registry()), receipt(replace(ctx, **{field: str(uuid4())}), UpgradePhase.EXCLUSIVE), registry())


def test_missing_source_target_and_unregistered_schemas():
    ctx = context()
    states, _ = full_states(ctx)
    for index in (1, 5):
        with pytest.raises(UpgradeError, match="artifact_missing"):
            advance_upgrade(states[index], receipt(ctx, states[index+1].phase), registry())
    with pytest.raises(SchemaRegistryError):
        new_upgrade_state(ctx, PRODUCT_SCHEMA_REGISTRY)
    with pytest.raises(SchemaRegistryError):
        new_upgrade_state(replace(ctx, target=replace(ctx.target, fingerprint="f" * 64)), registry())
    assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
    assert not PRODUCT_SCHEMA_REGISTRY.upgrades


@pytest.mark.parametrize("index", range(8))
def test_controlled_abort_before_activation(index):
    ctx = context(); states, _ = full_states(ctx)
    aborted = advance_upgrade(states[index], receipt(ctx, UpgradePhase.ABORTED), registry())
    assert aborted.phase is UpgradePhase.ABORTED
    with pytest.raises(UpgradeError):
        advance_upgrade(aborted, receipt(ctx, UpgradePhase.EXCLUSIVE), registry())


def test_activation_cannot_be_called_aborted_and_missing_observations_block():
    ctx = context(); states, artifacts = full_states(ctx)
    with pytest.raises(UpgradeError):
        advance_upgrade(states[8], receipt(ctx, UpgradePhase.ABORTED), registry())
    decision = classify(states[-1], ctx, ())
    assert decision.status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def classify(state, ctx, observed, **changes):
    args = dict(expected_context=ctx, observed=observed, registry=registry(),
                inventory_complete=True, journal_authenticated=True)
    if state is not None and isinstance(state, UpgradeState) and state.phase in {UpgradePhase.COMPLETED, UpgradePhase.WRITES_ENABLED}:
        args["target_inspection"] = state.evidence[-1].inspection
    args.update(changes)
    return classify_upgrade(state, **args)


def test_classification_requires_authenticated_current_independent_evidence():
    ctx = context(); states, artifacts = full_states(ctx)
    observed = artifacts[:2] + (artifacts[-1],)
    result = classify(states[-1], ctx, observed)
    assert result.status is UpgradeRecoveryStatus.COMPLETED
    assert not result.activation_allowed and not result.normal_runtime_allowed
    for changes in ({"journal_authenticated": False}, {"inventory_complete": False},
        {"expected_context": replace(ctx, installation_id=str(uuid4()))}):
        assert classify(states[-1], ctx, observed, **changes).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify("unknown", ctx, ()).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify(None, None, (), inventory_complete=False).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify(None, None, ()).status is UpgradeRecoveryStatus.NO_OPERATION
    staged = states[4]
    observations = tuple(item for evidence in staged.evidence for item in evidence.artifacts)
    for _ in range(2):
        decision = classify(staged, ctx, observations)
        assert decision.status is UpgradeRecoveryStatus.VERIFY_CANDIDATE
        assert not decision.activation_allowed
    assert classify(states[2], ctx, (artifacts[0],)).status is UpgradeRecoveryStatus.NOT_ACTIVATED
    aborted = advance_upgrade(states[2], receipt(ctx, UpgradePhase.ABORTED), registry())
    assert classify(aborted, ctx, (artifacts[0],)).status is UpgradeRecoveryStatus.ABORTED
    assert classify(states[8], ctx, artifacts).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_inconsistent_artifact_rejected():
    ctx = context(); states, artifacts = full_states(ctx)
    with pytest.raises(UpgradeError, match="artifact_changed"):
        advance_upgrade(states[6], receipt(ctx, UpgradePhase.ACTIVATION_PREPARED,
            tuple(replace(a, sha256="d" * 64) if a.role == "candidate" else a
                  for a in states[7].evidence[-1].artifacts)), registry())


def setup_runtime(tmp_path, ctx):
    root = tmp_path / "runtime"
    prepare_synthetic_test_root(root)
    lock = RuntimeInstanceLock(root).acquire()
    lease = UpgradeProcessLease(lock, ctx, root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging")
    return root, lock, lease


def repository(root, ctx, lease):
    return AuthenticatedUpgradeJournalRepository(root / "schema-upgrade-foundation" / "journal.json",
        PlatformFilePermissionManager(), context=ctx, registry=registry(), lease=lease)


def auth_key(ctx):
    return derive_migration_journal_auth_key(LoadedDataMasterKey(ctx.dmk_key_id, 1, secrets.token_bytes(32)),
        migration_id=ctx.operation_id)


def test_real_authentication_cas_and_duplicate_operation(tmp_path):
    ctx = context(); root, lock, lease = setup_runtime(tmp_path, ctx)
    key = auth_key(ctx); state = new_upgrade_state(ctx, registry())
    try:
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            repo = repository(root, ctx, lease)
            repo.create(state, key)
            with pytest.raises(MigrationJournalError, match="already_exists"):
                repo.create(state, key)
            updated = advance_upgrade(state, receipt(ctx, UpgradePhase.EXCLUSIVE), registry())
            repo.save(state, updated, key)
            repo.save(updated, updated, key)
            assert repo.load(key) == updated
            with pytest.raises(MigrationJournalError, match="changed"):
                repo.save(state, updated, key)
            with pytest.raises(MigrationJournalError, match="authentication_failed"):
                repo.load(auth_key(ctx))
            with pytest.raises(UpgradeError, match="context_mismatch"):
                repository(root, replace(ctx, installation_id=str(uuid4())), lease).load(key)
            raw = repo.path.read_bytes()
            assert key.key_material not in raw
            repo.path.write_bytes(raw.replace(b"preflight", b"corrupted"))
            # Change authenticated content in the state itself, not just whitespace.
            repo.path.write_bytes(raw.replace(b"exclusive", b"corrupted"))
            with pytest.raises(MigrationJournalError, match="authentication_failed"):
                repo.load(key)
    finally:
        lock.release()


def test_failed_tempwrite_preserves_old_authenticated_state(tmp_path, monkeypatch):
    ctx = context(); root, lock, lease = setup_runtime(tmp_path, ctx); key=auth_key(ctx)
    try:
        with UpgradeMaintenance(MaintenanceGate(), lease, ctx):
            repo=repository(root,ctx,lease); state=new_upgrade_state(ctx,registry()); repo.create(state,key)
            old=repo.path.read_bytes()
            def fail(_data):
                raise OSError("synthetic_disk_error")
            monkeypatch.setattr(repo, "_write_temporary", fail)
            updated=advance_upgrade(state,receipt(ctx,UpgradePhase.EXCLUSIVE),registry())
            with pytest.raises(OSError):
                repo.save(state,updated,key)
            assert repo.path.read_bytes()==old
            with pytest.raises(UpgradeError, match="generation_conflict"):
                repo.load(key)
    finally:
        lock.release()


def test_maintenance_drain_error_abort_and_backup_exclusion(tmp_path):
    ctx=context(); root,lock,lease=setup_runtime(tmp_path,ctx); gate=MaintenanceGate()
    try:
        writer=gate.begin_writer()
        with pytest.raises(UpgradeError,match="writers_active"):
            with UpgradeMaintenance(gate,lease,ctx): pass
        assert gate.state is MaintenanceState.NORMAL
        writer.release()
        with pytest.raises(RuntimeError):
            with UpgradeMaintenance(gate,lease,ctx):
                with pytest.raises(MaintenanceWriterBlockedError): gate.begin_writer()
                with pytest.raises(MaintenanceGateError):
                    gate.request_maintenance(owner_id="backup",purpose=MaintenancePurpose.BACKUP_RESTORE)
                raise RuntimeError("synthetic_phase_abort")
        assert gate.state is MaintenanceState.NORMAL
        with gate.begin_writer(): pass
        with UpgradeMaintenance(gate,lease,ctx) as maintenance:
            maintenance.require_recovery()
        assert gate.state is MaintenanceState.RECOVERY_REQUIRED
    finally:
        lock.release()


def _process(root, ctx, queue, mode, key=None):
    root=Path(root)
    if mode == "writer":
        queue.put("waiting")
        with ObservationWriterLock(root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging"):
            queue.put("entered")
        return
    try:
        with RuntimeInstanceLock(root) as lock:
            lease=UpgradeProcessLease(lock,ctx,root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging")
            with UpgradeMaintenance(MaintenanceGate(),lease,ctx):
                if mode == "crash":
                    repo=repository(root,ctx,lease); repo.create(new_upgrade_state(ctx,registry()),key)
                if mode == "partial":
                    repo=repository(root,ctx,lease); state=new_upgrade_state(ctx,registry()); repo.create(state,key)
                    def interrupt_write(_data):
                        with (repo.path.parent / ".database-migration-journal-crash.tmp").open("xb") as stream:
                            stream.write(b"partial"); stream.flush(); os.fsync(stream.fileno())
                        queue.put("held")
                        signal.pause()
                    repo._write_temporary = interrupt_write
                    updated = advance_upgrade(state, receipt(ctx, UpgradePhase.EXCLUSIVE), registry())
                    repo.save(state, updated, key)
                queue.put("held")
                signal.pause()  # parent terminates this real process
    except Exception as error:
        queue.put(type(error).__name__)


def test_real_competing_upgrade_and_backup_writer_processes(tmp_path):
    ctx=context(); root,lock,lease=setup_runtime(tmp_path,ctx)
    spawn=multiprocessing.get_context("spawn")
    try:
        queue=spawn.Queue(); child=spawn.Process(target=_process,args=(str(root),ctx,queue,"upgrade")); child.start()
        assert queue.get(timeout=10)=="RestoreLockError"
        child.join(10); assert child.exitcode==0
        with UpgradeMaintenance(MaintenanceGate(),lease,ctx):
            queue=spawn.Queue(); child=spawn.Process(target=_process,args=(str(root),ctx,queue,"writer")); child.start()
            assert queue.get(timeout=10)=="waiting"
            with pytest.raises(Empty): queue.get(timeout=0.3)
        assert queue.get(timeout=10)=="entered"
        child.join(10); assert child.exitcode==0
    finally:
        if child.is_alive(): child.terminate(); child.join(10)
        lock.release()


@pytest.mark.parametrize("mode", ["crash", "partial"])
def test_real_process_crash_releases_lock_but_never_completes_upgrade(tmp_path, mode):
    ctx=context(); root=tmp_path / "runtime"; prepare_synthetic_test_root(root); key=auth_key(ctx)
    spawn=multiprocessing.get_context("spawn"); queue=spawn.Queue()
    child=spawn.Process(target=_process,args=(str(root),ctx,queue,mode,key)); child.start()
    try:
        assert queue.get(timeout=10)=="held"
    finally:
        child.terminate(); child.join(10)
    assert child.exitcode != 0
    with RuntimeInstanceLock(root) as lock:
        lease=UpgradeProcessLease(lock,ctx,root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging")
        with UpgradeMaintenance(MaintenanceGate(),lease,ctx):
            repo=repository(root,ctx,lease)
            if mode=="partial":
                with pytest.raises(MigrationJournalError,match="temporary_present"): repo.load(key)
            else:
                state=repo.load(key)
                for _ in range(2):
                    assert classify(state,ctx,()).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED


def test_lease_entry_failure_releases_maintenance_and_runtime_owner_keeps_lock(tmp_path):
    ctx=context(); root,lock,lease=setup_runtime(tmp_path,ctx); gate=MaintenanceGate()
    try:
        with pytest.raises(UpgradeError,match="context_mismatch"):
            with UpgradeMaintenance(gate,lease,replace(ctx,operation_id=str(uuid4()))): pass
        assert gate.state is MaintenanceState.NORMAL and not lease.active
        assert lock.fileno >= 0
        with UpgradeMaintenance(gate,lease,ctx): pass
        assert gate.state is MaintenanceState.NORMAL
    finally:
        lock.release()


def test_authenticated_structural_contradiction_and_journal_prefix_rejected(tmp_path):
    ctx=context(); root,lock,lease=setup_runtime(tmp_path,ctx); key=auth_key(ctx)
    try:
        with UpgradeMaintenance(MaintenanceGate(),lease,ctx):
            repo=repository(root,ctx,lease); state=new_upgrade_state(ctx,registry())
            with pytest.raises(UpgradeError):
                repo.create(replace(state,phase=UpgradePhase.COMPLETED),key)
            repo.create(state,key)
            with pytest.raises(UpgradeError):
                repo.save(state,replace(state,revision=1,phase=UpgradePhase.COMPLETED),key)
            (repo.path.parent / ".database-migration-journal-leftover.tmp").write_bytes(b"partial")
            with pytest.raises(MigrationJournalError,match="temporary_present"):
                repo.load(key)
    finally:
        lock.release()


def test_no_product_root_authority_and_no_journal_access_without_lease(tmp_path):
    ctx=context(); root=tmp_path / "unmarked"; root.mkdir()
    with RuntimeInstanceLock(root) as lock:
        lease=UpgradeProcessLease(lock,ctx,root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging")
        with pytest.raises(UpgradeError,match="synthetic_root_required"):
            with UpgradeMaintenance(MaintenanceGate(),lease,ctx): pass
    root,lock,lease=setup_runtime(tmp_path,ctx)
    try:
        with pytest.raises(UpgradeError):
            repository(root,ctx,lease).create(new_upgrade_state(ctx,registry()),auth_key(ctx))
    finally:
        lock.release()


def test_live_reopen_evidence_must_match_prepared_candidate():
    ctx=context(); states,parts=full_states(ctx)
    with pytest.raises(UpgradeError,match="runtime_target_mismatch"):
        advance_upgrade(states[10], UpgradeEvidence(ctx,UpgradePhase.RUNTIME_VERIFIED,
            (replace(parts[-1],artifact_id=str(uuid4())),),
            inspection=states[11].evidence[-1].inspection), registry())


def test_extra_unrecorded_or_contradictory_observations_require_recovery():
    ctx=context(); states,parts=full_states(ctx)
    assert classify(states[2],ctx,(parts[0],parts[-1])).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
    assert classify(states[-1],ctx,(parts[0],parts[1],replace(parts[-1],sha256="f" * 64))).status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
