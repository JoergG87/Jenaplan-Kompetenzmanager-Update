"""Real SQLCipher and filesystem evidence for isolated B2, without product admission."""
from contextlib import closing, contextmanager
from dataclasses import replace
import gc
import os
from pathlib import Path
import shutil
import signal
import multiprocessing
from uuid import uuid4
import pytest

from tests.historical_upgrade.schema_upgrade import UpgradeMaintenance
from tests.historical_upgrade.prepare_upgrade_source import PrepareEncryptedUpgradeSource
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.maintenance_gate import ConnectionDrain, MaintenanceState, MaintenanceGateError
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.schema_registry import (DatabaseSchemaRegistry, SchemaRegistration, SchemaUpgradeRelation,
    RegisteredSchemaIdentity, FINAL_V4_SCHEMA_REGISTRATION, SCHEMA_FINGERPRINT_ALGORITHM, PRODUCT_SCHEMA_REGISTRY)
from src.core.schema_upgrade import UpgradeContext, UpgradeEvidence, UpgradePhase, UpgradeError, advance_upgrade
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.infrastructure.system import PlatformFilePermissionManager
from tests.historical_upgrade.upgrade_process_lease import UpgradeProcessLease
from tests.historical_upgrade.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository
from tests.historical_upgrade.encrypted_upgrade_source import EncryptedUpgradeSourceAdapter
from tests.historical_upgrade.upgrade_rollback_source import DurableUpgradeRollbackSource
from tests.historical_upgrade.upgrade_atomic_activation import SyntheticUpgradeActivation, PinnedUpgradeFiles
from tests.test_encrypted_upgrade_source import _open_case, _hash


def _prepare(directory):
    runtime, service, *_ = _open_case(directory)
    provider = service._provider
    main = service.paths.final_v4.database
    probe = main.parent / "synthetic-target-probe.sqlcipher"
    shutil.copyfile(main, probe); probe.chmod(0o600)
    with closing(provider.connect(probe, create=False, key_material=service.loaded.database_key.key_material)) as c:
        c.execute("CREATE INDEX synthetic_b2_index ON students(student_id)")
        c.execute("PRAGMA user_version=5"); c.commit()
        report = DatabaseCompatibilityInspector().inspect_connection(c)
        target = RegisteredSchemaIdentity(5, report.schema_identity.fingerprint, SCHEMA_FINGERPRINT_ALGORITHM)
    probe.unlink()
    registry = DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION,
        SchemaRegistration("synthetic_b2_target", target, frozenset())),
        (SchemaUpgradeRelation(FINAL_V4_SCHEMA_REGISTRATION.identity, target),))
    loaded = service.loaded
    context = UpgradeContext(str(uuid4()), service.installation_id, loaded.database_context_id,
        loaded.database_key_id, loaded.database_key_generation, loaded.dmk_key_id, loaded.dmk_generation,
        FINAL_V4_SCHEMA_REGISTRATION.identity, target, "synthetic_index_only")
    return runtime, service, registry, context


@contextmanager
def _activation_case(directory, hook=None):
    runtime, service, registry, context = _prepare(directory)
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        lease = UpgradeProcessLease(lock, context, service.paths.final_v4.runtime_root / ".observation-staging")
        journal = AuthenticatedUpgradeJournalRepository(lock.runtime_root / "schema-upgrade-foundation" / "journal.json",
            PlatformFilePermissionManager(), context=context, registry=registry, lease=lease)
        key = derive_migration_journal_auth_key(service.loaded.dmk, migration_id=context.operation_id)
        adapter = EncryptedUpgradeSourceAdapter(service, lease, context)
        runner = PrepareEncryptedUpgradeSource(context=context, registry=registry, gate=service._gate,
            lease=lease, journal=journal, auth_key=key, adapter=adapter)
        state = runner.execute()
        with closing(service._provider.connect(adapter.candidate_path, create=False,
                key_material=service.loaded.database_key.key_material)) as c:
            c.execute("CREATE INDEX synthetic_b2_index ON students(student_id)")
            c.execute("PRAGMA user_version=5"); c.commit()
        with UpgradeMaintenance(service._gate, lease, context):
            candidate = replace(adapter._artifact(adapter.candidate_path, "candidate"), schema=context.target)
            for phase in (UpgradePhase.MIGRATED, UpgradePhase.TARGET_VERIFIED):
                next_state = advance_upgrade(state, UpgradeEvidence(context, phase, (candidate,)), registry)
                journal.save(state, next_state, key); state = next_state
        rollback = DurableUpgradeRollbackSource(adapter)
        activation = SyntheticUpgradeActivation(source_adapter=adapter, rollback=rollback, journal=journal,
            auth_key=key, registry=registry, fault_hook=hook)
        gc.collect()
        with UpgradeMaintenance(service._gate, lease, context) as maintenance:
            paths = (service.paths.final_v4.database, service.paths.database, adapter.candidate_path, rollback.rollback_path)
            drain = ConnectionDrain(paths, runtime_paths=paths[:2], gate=service._gate,
                capability=maintenance.capability, owner_id=context.operation_id,
                require_authority=lambda: lease.require_owner(context))
            with drain:
                for path in paths[:2]:
                    drain.checkpoint(path, lambda path=path: service._provider.connect(path, create=False,
                        key_material=service.loaded.database_key.key_material))
                yield activation, maintenance, drain, candidate


def test_atomic_install_exact_identity_and_no_writer_admission(tmp_path):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database
        before = _hash(main)
        state = activation.execute(maintenance=maintenance, drain=drain)
        assert state.phase is UpgradePhase.TARGET_INSTALLED
        assert main.stat().st_ino == candidate.file_id
        assert _hash(main) == candidate.sha256
        assert _hash(activation.rollback.rollback_path) == before
        assert not activation.source.candidate_path.exists()
        assert maintenance.gate.state is MaintenanceState.RECOVERY_REQUIRED
        assert {e.phase for e in state.evidence}.isdisjoint({UpgradePhase.RESTART_CONFIRMED,
            UpgradePhase.RUNTIME_VERIFIED, UpgradePhase.WRITES_ENABLED, UpgradePhase.COMPLETED})
        with pytest.raises((UpgradeError, MaintenanceGateError, OSError)):
            activation.source.service._provider.connect_read_only(main,
                key_material=activation.source.service.loaded.database_key.key_material)
        assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
        assert not PRODUCT_SCHEMA_REGISTRY.upgrades


@pytest.mark.parametrize("damage", ["candidate", "main_missing", "main_identity", "hardlink", "symlink", "parent", "wrong_context", "wrong_drain"])
def test_preflight_damage_never_exchanges(tmp_path, damage):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database
        before = _hash(main)
        if damage == "candidate":
            activation.source.candidate_path.write_bytes(b"damaged")
        elif damage == "main_missing":
            main.unlink()
        elif damage == "main_identity":
            raw = main.read_bytes(); main.unlink(); main.write_bytes(raw); main.chmod(0o600)
        elif damage == "hardlink":
            os.link(main, main.parent / "unexpected-hardlink")
        elif damage == "symlink":
            activation.source.candidate_path.unlink(); activation.source.candidate_path.symlink_to(main)
        elif damage == "parent":
            activation.source.workspace.chmod(0o777)
        elif damage == "wrong_context":
            activation.context = replace(activation.context, operation_id=str(uuid4()))
        else:
            drain = ConnectionDrain(drain.paths[:2], gate=maintenance.gate,
                capability=maintenance.capability, owner_id=activation.context.operation_id,
                require_authority=lambda: activation.source.lease.require_owner(activation.context))
        with pytest.raises((UpgradeError, MaintenanceGateError, OSError)):
            activation.execute(maintenance=maintenance, drain=drain)
        if damage != "main_missing":
            assert _hash(main) == before


@pytest.mark.parametrize("boundary", ["after_prepared_files_sync", "after_activation_prepared", "after_activation_intent",
    "before_atomic_replace", "after_atomic_replace", "after_exchange_directory_sync", "after_target_installed"])
def test_interruption_preserves_evidence_and_atomic_main(tmp_path, boundary):
    def fail(value):
        if value == boundary:
            raise OSError("synthetic persistence interruption")
    with _activation_case(tmp_path, fail) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database
        before = _hash(main)
        with pytest.raises(OSError):
            activation.execute(maintenance=maintenance, drain=drain)
        assert main.exists()
        assert _hash(main) in {before, candidate.sha256}
        assert activation.rollback.rollback_path.exists()
        assert maintenance.gate.state is MaintenanceState.RECOVERY_REQUIRED


@pytest.mark.parametrize("error", [18, 28, 5, 13])
def test_replace_errors_no_fallback(tmp_path, monkeypatch, error):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database; before = _hash(main)
        def fail(*args, **kwargs):
            raise OSError(error, "synthetic replace failure")
        # Patch only the single exchange, after journal/rollback preparation.
        def hook(boundary):
            if boundary == "before_atomic_replace":
                monkeypatch.setattr(os, "replace", fail)
        activation._fault_hook = hook
        with pytest.raises(OSError):
            activation.execute(maintenance=maintenance, drain=drain)
        assert _hash(main) == before and activation.source.candidate_path.exists()


def _crash_worker(directory, queue, boundary):
    def pause(value):
        if value == boundary:
            queue.put(True)
            signal.pause()
    with _activation_case(Path(directory), pause) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database
        queue.put((str(main), _hash(main), candidate.sha256, str(activation.rollback.rollback_path), activation.context, activation.auth_key))
        activation.execute(maintenance=maintenance, drain=drain)


@pytest.mark.parametrize("boundary", ["after_activation_intent", "after_atomic_replace", "after_exchange_directory_sync"])
def test_real_sigkill_exchange_boundaries(tmp_path, boundary):
    spawn = multiprocessing.get_context("spawn"); queue = spawn.Queue()
    child = spawn.Process(target=_crash_worker, args=(str(tmp_path), queue, boundary)); child.start()
    try:
        main, source_hash, candidate_hash, rollback, context, key = queue.get(timeout=50)
        assert queue.get(timeout=50) is True
        os.kill(child.pid, signal.SIGKILL); child.join(15)
        assert child.exitcode == -signal.SIGKILL
        assert Path(main).exists()
        assert _hash(main) == (source_hash if boundary == "after_activation_intent" else candidate_hash)
        assert _hash(rollback) == source_hash
        root = Path(main).parent.parent
        registry = DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION,
            SchemaRegistration("synthetic_b2_target", context.target, frozenset())),
            (SchemaUpgradeRelation(context.source, context.target),))
        with RuntimeInstanceLock(root) as lock:
            lease = UpgradeProcessLease(lock, context, Path(main).parent / ".observation-staging")
            with lease:
                journal = AuthenticatedUpgradeJournalRepository(root / "schema-upgrade-foundation" / "journal.json",
                    PlatformFilePermissionManager(), context=context, registry=registry, lease=lease)
                state = journal.load(key)
                assert state.phase is UpgradePhase.ACTIVATION_INTENT
                assert not any(e.phase in {UpgradePhase.WRITES_ENABLED, UpgradePhase.COMPLETED} for e in state.evidence)
    finally:
        if child.is_alive(): child.kill(); child.join(15)


@pytest.mark.parametrize("kind", ["candidate_file", "post_exchange_directory"])
def test_fsync_failure_never_claims_target_installed(tmp_path, monkeypatch, kind):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database
        before = _hash(main)
        original = os.fsync
        def fail(descriptor):
            details = os.fstat(descriptor)
            if kind == "candidate_file" and details.st_ino == candidate.file_id:
                raise OSError(5, "synthetic candidate fsync")
            original(descriptor)
        if kind == "candidate_file":
            monkeypatch.setattr(os, "fsync", fail)
        else:
            original_sync = PinnedUpgradeFiles.sync
            def hook(boundary):
                if boundary == "after_atomic_replace":
                    def fail_sync(self, *paths):
                        raise OSError(5, "synthetic directory fsync")
                    monkeypatch.setattr(PinnedUpgradeFiles, "sync", fail_sync)
            activation._fault_hook = hook
        with pytest.raises(OSError):
            activation.execute(maintenance=maintenance, drain=drain)
        # Inspect persisted phase under the still-held process lease, not runtime admission.
        state = activation.journal.load(activation.auth_key)
        assert state.phase is (UpgradePhase.TARGET_VERIFIED if kind == "candidate_file" else UpgradePhase.ACTIVATION_INTENT)
        assert _hash(main) == (before if kind == "candidate_file" else candidate.sha256)


def test_replayed_old_journal_revision_blocks_before_exchange(tmp_path):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database; before = _hash(main)
        old = activation.journal.path.read_bytes()
        def hook(boundary):
            if boundary == "after_activation_intent":
                activation.journal.path.write_bytes(old)
        activation._fault_hook = hook
        with pytest.raises(UpgradeError, match="replay_or_generation_conflict"):
            activation.execute(maintenance=maintenance, drain=drain)
        assert _hash(main) == before


def test_second_activation_attempt_never_replaces_again(tmp_path):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        activation.execute(maintenance=maintenance, drain=drain)
        main = activation.source.service.paths.final_v4.database
        before = _hash(main)
        with pytest.raises(UpgradeError, match="authority_required"):
            activation.execute(maintenance=maintenance, drain=drain)
        assert _hash(main) == before


@pytest.mark.parametrize("boundary", ["after_activation_intent", "after_atomic_replace"])
@pytest.mark.parametrize("loss", ["runtime_unlock", "writer_unlock", "runtime_reacquire", "writer_context_release", "writer_context_reacquire"])
def test_lost_authority_keeps_recovery_gate_after_context_exit(tmp_path, boundary, loss):
    import fcntl
    gate = None
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        gate = maintenance.gate
        main = activation.source.service.paths.final_v4.database
        before = _hash(main)
        def hook(value):
            if value == boundary:
                lease = activation.source.lease
                if loss == "runtime_reacquire":
                    lease.lock.release(); lease.lock.acquire()
                elif loss in {"writer_context_release", "writer_context_reacquire"}:
                    lease.writer.__exit__(None, None, None)
                    if loss == "writer_context_reacquire":
                        lease.writer.__enter__()
                else:
                    descriptor = lease.lock.fileno if loss == "runtime_unlock" else lease.writer._fd
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
        activation._fault_hook = hook
        with pytest.raises(UpgradeError, match="lock_required|process_context_mismatch"):
            activation.execute(maintenance=maintenance, drain=drain)
        assert gate.state is MaintenanceState.RECOVERY_REQUIRED
        assert _hash(main) == (before if boundary == "after_activation_intent" else candidate.sha256)
    assert gate.state is MaintenanceState.RECOVERY_REQUIRED
    with pytest.raises(MaintenanceGateError):
        gate.begin_writer()



def test_exactly_one_main_replace_without_main_rename_gap(tmp_path, monkeypatch):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database
        original = os.replace
        exchanges = []
        def observe(source, target, *args, **kwargs):
            if target == main.name:
                assert main.exists()
                assert source == activation.source.candidate_path.name
                assert "src_dir_fd" in kwargs and "dst_dir_fd" in kwargs
                exchanges.append((source, target))
                result = original(source, target, *args, **kwargs)
                assert main.exists()
                return result
            return original(source, target, *args, **kwargs)
        monkeypatch.setattr(os, "replace", observe)
        activation.execute(maintenance=maintenance, drain=drain)
        assert exchanges == [(activation.source.candidate_path.name, main.name)]


@pytest.mark.parametrize("ancestor", ["operation", "workspace_parent", "root"])
def test_activation_ancestor_sync_failure_never_persists_intent(tmp_path, monkeypatch, ancestor):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        main = activation.source.service.paths.final_v4.database; before = _hash(main)
        # Arm after rollback has independently completed its own full fsync chain.
        original_verify = activation.rollback.verify
        original = os.fsync
        target = {"operation": activation.source.workspace,
            "workspace_parent": activation.source.workspace.parent,
            "root": activation.source.root}[ancestor].stat().st_ino
        def verify(*args, **kwargs):
            result = original_verify(*args, **kwargs)
            def fail(descriptor):
                if os.fstat(descriptor).st_ino == target:
                    raise OSError(5, "synthetic activation ancestor fsync")
                original(descriptor)
            monkeypatch.setattr(os, "fsync", fail)
            return result
        monkeypatch.setattr(activation.rollback, "verify", verify)
        with pytest.raises(OSError, match="ancestor fsync"):
            activation.execute(maintenance=maintenance, drain=drain)
        assert _hash(main) == before
        assert activation.journal.load(activation.auth_key).phase is UpgradePhase.TARGET_VERIFIED


def test_pinned_activation_sync_includes_entire_private_chain(tmp_path, monkeypatch):
    with _activation_case(tmp_path) as (activation, maintenance, drain, candidate):
        calls = []; original = os.fsync
        with PinnedUpgradeFiles(activation.source.root) as files:
            files.parent(activation.source.candidate_path)
            expected = [activation.source.workspace.stat().st_ino,
                activation.source.workspace.parent.stat().st_ino, activation.source.root.stat().st_ino]
            def observe(descriptor):
                calls.append(os.fstat(descriptor).st_ino); original(descriptor)
            monkeypatch.setattr(os, "fsync", observe)
            files.sync(activation.source.candidate_path)
            assert calls == expected
