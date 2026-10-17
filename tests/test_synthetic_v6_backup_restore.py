"""Real audited SQLCipher V6 backups and existing restore machinery, no skips."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import multiprocessing
import os
import signal
import uuid
from types import SimpleNamespace

import pytest

from src.security.transactional_timetable_migration import SyntheticTimetableMigration
from src.core.maintenance_gate import MaintenanceGate
from src.core.restore_runtime import RuntimeInstanceLock, RestoreJournal, restore_transaction_paths
from src.security.final_v4_backup_runtime import (
    FinalV4EncryptedBackupError, FinalV4EncryptedBackupManifestV1,
    FINAL_V4_RESTORE_READY_FILENAME,
)
from src.security.synthetic_v6_backup_runtime import (
    SyntheticV6EncryptedBackupService, SyntheticV6EncryptedBackupManifestV1,
    SYNTHETIC_V6_RESTORE_READY_VERSION,
)
from src.security.synthetic_v6_live_restore import (
    SyntheticV6EncryptedLiveRestoreService,
    SyntheticV6EncryptedRestoreHandoffService,
    prepare_synthetic_v6_live_restore, confirm_synthetic_v6_restore_startup,
    recover_interrupted_synthetic_v6_restore,
    classify_terminal_synthetic_v6_restore_artifacts,
)
from src.security.final_v4_live_restore import (
    FinalV4EncryptedRestoreHandoffService, FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY,
)
from src.security.synthetic_v6_runtime import KeyedSyntheticV6CompatibilityInspector
from src.security.final_v3_document_runtime import FinalV3DocumentRuntime
from src.security.final_v4_backup_runtime import _StagedDocumentFactory
from src.security.infrastructure.system import SystemRandomSource, SystemClock
from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider
from tests.test_transactional_schema_migration import _seed_case
from src.core.database_content_evidence import database_content_evidence


class _ExistingMain:
    def __init__(self, provider, path, key):
        self.provider, self.path, self.key = provider, path, key

    def connect(self, path, *, create=False):
        assert Path(path) == self.path and not create
        c = self.provider.connect(self.path, create=False, key_material=self.key)
        try:
            KeyedSyntheticV6CompatibilityInspector().inspect_connection(c)
            return c
        except BaseException:
            c.close()
            raise


def _service(paths, loaded, installation_id, *, fault_hook=None):
    provider = qualified_sqlcipher_test_provider()
    key = loaded.database_key.key_material
    document_factory = _StagedDocumentFactory(provider, paths.database, key)
    documents = FinalV3DocumentRuntime(paths=paths, factory=document_factory,
        loaded_keys=loaded, installation_id=installation_id, source_root=None,
        random_source=SystemRandomSource(), clock=SystemClock())
    opened = SimpleNamespace(documents=documents, installation_id=installation_id,
        database_context_id=loaded.database_context_id,
        final_v4=SimpleNamespace(compatibility=None))
    return SyntheticV6EncryptedBackupService(opened_runtime=opened, paths=paths,
        loaded_keys=loaded, main_factory=_ExistingMain(provider, paths.final_v4.database, key),
        document_factory=document_factory, provider=provider,
        maintenance_gate=MaintenanceGate(), random_source=SystemRandomSource(),
        clock=SystemClock(), fault_hook=fault_hook)


def _migrate_fixture_worker(paths, loaded, installation, channel):
    from tests.test_transactional_schema_migration import _inspection_service
    try:
        service = _inspection_service(paths, loaded, installation)
        documents = FinalV3DocumentRuntime(paths=paths, factory=service._document_factory,
            loaded_keys=loaded, installation_id=installation, source_root=None,
            random_source=SystemRandomSource(), clock=SystemClock())
        service.opened = SimpleNamespace(documents=documents, installation_id=installation,
            database_context_id=loaded.database_context_id, final_v4=SimpleNamespace(compatibility=None))
        service._main_factory = SimpleNamespace(connect=lambda path, create=False:
            service._provider.connect(path, create=create, key_material=loaded.database_key.key_material))
        with closing(service._provider.connect_read_only(paths.final_v4.database,
                key_material=loaded.database_key.key_material)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 5:
            from src.security.synthetic_v5_backup_runtime import SyntheticV5EncryptedBackupService
            service = SyntheticV5EncryptedBackupService(opened_runtime=service.opened,
                paths=paths, loaded_keys=loaded, main_factory=service._main_factory,
                document_factory=service._document_factory, provider=service._provider,
                maintenance_gate=service._gate, random_source=service._random,
                clock=service._clock, installation_id=installation)
        SyntheticTimetableMigration(service).execute()
        channel.send(("ok",))
    except Exception as error:
        channel.send(("error", type(error).__name__, str(error)))
    finally:
        channel.close()


def _migrate_fixture(service):
    # Migration intentionally leaves the old process frozen: enter the target
    # only from a fresh process context, never clear that security boundary.
    parent, child = multiprocessing.get_context("spawn").Pipe()
    process = multiprocessing.get_context("spawn").Process(target=_migrate_fixture_worker,
        args=(service.paths, service.loaded, service.installation_id, child))
    process.start(); child.close()
    try:
        assert parent.poll(30), "migration fixture worker did not report"
        result = parent.recv(); process.join(10)
        assert result == ("ok",) and process.exitcode == 0, result
    finally:
        if process.is_alive():
            process.kill(); process.join(10)
        parent.close()


@pytest.fixture
def case(tmp_path):
    runtime, old = _seed_case(tmp_path)
    historical = old.create(tmp_path / 'historical-v4.jkmebackup')
    _migrate_fixture(old)
    with old._provider.connect(old.paths.final_v4.database, create=False,
            key_material=old.loaded.database_key.key_material) as c:
        c.execute("INSERT INTO lesson_time_templates VALUES(1,'07:45','08:30')")
        columns = [row[1] for row in c.execute("PRAGMA table_info(competencies)")]
        values = dict(c.execute("SELECT * FROM competencies LIMIT 1").fetchone())
        values.update(competency_id="CMP-SYNTHETIC-MATH", subject_id="SUB-SYNTHETIC-MATH",
            subject_name="Mathematik", subject_full_name="Mathematik")
        c.execute("INSERT INTO competencies(" + ",".join(columns) + ") VALUES("
            + ",".join("?" for _ in columns) + ")", [values[name] for name in columns])
        c.execute("INSERT INTO timetable_entry_subjects VALUES(?,?)",
            ("TTE-SYNTHETIC", "SUB-SYNTHETIC-MATH"))
        c.execute("INSERT INTO timetable_entries SELECT ?,2,start_time,end_time,?,target_type,target_id,room,active,sort_order,created_at,updated_at,deleted_at FROM timetable_entries WHERE timetable_entry_id=?",
            ("TTE-HOMEROOM", "homeroom_session", "TTE-SYNTHETIC"))
        c.commit()
    return _service(old.paths, old.loaded, old.installation_id), old, historical


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _content(service):
    with closing(service._provider.connect_read_only(service.paths.final_v4.database,
            key_material=service.loaded.database_key.key_material)) as c:
        return database_content_evidence(c)


def test_v6_encrypted_full_backup_independent_verify_ready_and_history(case, tmp_path):
    service, old, historical = case
    before = _content(service)
    key_before = (_hash(service.paths.final_v4.key_runtime.keyset_metadata),
        _hash(service.paths.final_v4.key_runtime.envelope_registry))
    target = service.create(tmp_path / 'v6.jkmebackup')
    assert type(target.manifest) is SyntheticV6EncryptedBackupManifestV1
    assert target.manifest.format_version == historical.manifest.format_version == 1
    raw = target.path.read_bytes()
    assert b'SQLite format 3' not in raw and b'SYNTHETIC-SECRET-DOCUMENT' not in raw
    assert service.loaded.dmk.key_material not in raw
    independent = _service(service.paths, service.loaded, service.installation_id)
    assert independent.verify(target.path) == target
    stage = independent.restore_staging(target.path, tmp_path / 'v6-stage')
    ready = json.loads(stage.ready_path.read_bytes())
    assert ready['ready_version'] == SYNTHETIC_V6_RESTORE_READY_VERSION
    assert ready['database_schema_version'] == 6
    checked = independent.verify_restore_ready(stage.staging_root,
        expected_container_sha256=target.container_sha256)
    with closing(independent._provider.connect_read_only(checked.paths.final_v4.database,
            key_material=checked.loaded_keys.database_key.key_material)) as c:
        assert database_content_evidence(c) == before
    assert stage.active_document_count == 1
    assert _hash(historical.path) == historical.container_sha256
    assert old.verify(historical.path) == historical
    with pytest.raises(Exception): old.verify(target.path)
    with pytest.raises(Exception): service.verify(historical.path)
    historical_stage = old.restore_staging(historical.path, tmp_path / 'v4-source-only')
    with pytest.raises(Exception):
        service.verify_restore_ready(historical_stage.staging_root,
            expected_container_sha256=historical.container_sha256)
    with pytest.raises(FinalV4EncryptedBackupError):
        FinalV4EncryptedBackupManifestV1.from_bytes(target.manifest.to_bytes())
    with pytest.raises(FinalV4EncryptedBackupError):
        SyntheticV6EncryptedBackupManifestV1.from_bytes(historical.manifest.to_bytes())
    assert _content(service) == before
    assert key_before == (_hash(service.paths.final_v4.key_runtime.keyset_metadata),
        _hash(service.paths.final_v4.key_runtime.envelope_registry))


@pytest.mark.parametrize('damage', ['container','installation','key','manifest','incomplete','old-ready'])
def test_invalid_v6_backup_or_ready_never_changes_live(case, tmp_path, damage):
    service, old, historical = case
    target = service.create(tmp_path / 'target.jkmebackup')
    before = _hash(service.paths.final_v4.database)
    if damage == 'container':
        data = bytearray(target.path.read_bytes()); data[len(data)//2] ^= 1
        target.path.write_bytes(data)
        operation = lambda: service.restore_staging(target.path, tmp_path / 'bad')
    elif damage == 'installation':
        wrong = _service(service.paths, service.loaded, str(uuid.uuid4()))
        operation = lambda: wrong.verify(target.path)
    elif damage == 'key':
        wrong_key = replace(service.loaded.database_key, key_material=os.urandom(32))
        operation = lambda: _service(service.paths, replace(service.loaded, database_key=wrong_key), service.installation_id).verify(target.path)
    else:
        stage = service.restore_staging(target.path, tmp_path / 'stage')
        if damage == 'manifest':
            p = stage.staging_root / service.manifest_filename
            payload = json.loads(p.read_bytes()); payload['installation_id'] = str(uuid.uuid4())
            p.write_text(json.dumps(payload))
        elif damage == 'incomplete':
            (stage.staging_root / service.paths.final_v4.runtime_root.name / service.paths.database.name).unlink()
        else:
            ready = json.loads(stage.ready_path.read_bytes()); ready['ready_version'] = 1
            from src.security.backup_container import canonical_json
            stage.ready_path.write_bytes(canonical_json(ready))
        operation = lambda: service.verify_restore_ready(stage.staging_root,
            expected_container_sha256=target.container_sha256)
    with pytest.raises(Exception): operation()
    assert _hash(service.paths.final_v4.database) == before


@pytest.mark.parametrize('boundary', ['during_main_database_snapshot','during_container_write','after_write_before_verification','after_reopen_before_restore_ready'])
def test_interrupted_backup_or_staging_no_partial_authority(case, tmp_path, boundary):
    service, _, _ = case
    before = _hash(service.paths.final_v4.database)
    target = service.create(tmp_path / 'good.jkmebackup')
    def fail(value):
        if value == boundary: raise OSError('synthetic injected interruption')
    service._fault_hook = fail
    if boundary == 'after_reopen_before_restore_ready':
        stage = tmp_path / 'incomplete-stage'
        with pytest.raises(Exception): service.restore_staging(target.path, stage)
        assert not (stage / FINAL_V4_RESTORE_READY_FILENAME).exists()
    else:
        output = tmp_path / 'interrupted.jkmebackup'
        with pytest.raises(Exception): service.create(output)
        assert not output.exists()
    assert _hash(service.paths.final_v4.database) == before


def _confirm_worker(paths, loaded, installation_id, restore_id, token, channel):
    try:
        service = _service(paths, loaded, installation_id)
        result = confirm_synthetic_v6_restore_startup(backup_service=service,
            runtime_root=paths.final_v4.root, restore_id=restore_id, token=token)
        channel.send(('ok', result.state if hasattr(result, 'state') else result))
    except BaseException as error:
        channel.send(('error', type(error).__name__, str(error)))
    finally:
        channel.close()


def _restore_worker(paths, loaded, installation_id, handoff, nonce, channel, crash=None):
    try:
        service = _service(paths, loaded, installation_id)
        def fault(boundary):
            if boundary == crash:
                os.kill(os.getpid(), signal.SIGKILL)
        strategy = SyntheticV6EncryptedLiveRestoreService(service, fault_hook=fault)
        def restart(transaction, token, lock):
            ctx = multiprocessing.get_context('spawn')
            parent, child = ctx.Pipe()
            process = ctx.Process(target=_confirm_worker,
                args=(paths, loaded, installation_id, transaction.transaction.name, token, child))
            process.start(); child.close()
            assert parent.poll(30), 'real restart verifier did not report'
            result = parent.recv(); process.join(10); parent.close()
            assert result[0] == 'ok', result
            assert process.exitcode == 0
            return True
        with RuntimeInstanceLock(paths.final_v4.root) as lock:
            result = strategy.execute(handoff_path=handoff, nonce=nonce, lock=lock,
                restart=restart, handshake_timeout_seconds=1)
        channel.send(('ok', result.state if hasattr(result, 'state') else result))
    except BaseException as error:
        channel.send(('error', type(error).__name__, str(error)))
    finally:
        channel.close()


def _prepare(service, tmp_path, *, before_handoff=None):
    root = service.paths.final_v4.root
    target = service.create(tmp_path / 'restore-target.jkmebackup')
    original = _content(service)
    with service._main_factory.connect(service.paths.final_v4.database) as c:
        c.execute("UPDATE lesson_time_templates SET start_time='07:50'")
        c.commit()
    current = _content(service)
    restore_id = str(uuid.uuid4())
    parent = root / FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    parent.mkdir(mode=0o700)
    stage = service.restore_staging(target.path, parent / restore_id)
    with RuntimeInstanceLock(root) as lock:
        prep = prepare_synthetic_v6_live_restore(backup_service=service, lock=lock,
            staging_root=stage.staging_root, expected_container_sha256=target.container_sha256,
            restore_id=restore_id, app_version='0.4.4', build_commit='a'*40,
            before_handoff=(lambda: before_handoff(lock)) if before_handoff else None)
    prep.safety_backup.transfer_to_worker()
    return prep, original, current


def _run_restore(service, prep, *, crash=None):
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_restore_worker,
        args=(service.paths, service.loaded, service.installation_id,
            prep.handoff.path, prep.handoff.nonce, child, crash))
    process.start(); child.close()
    if crash is None:
        assert parent.poll(45), 'real restore worker did not report'
        result = parent.recv()
        process.join(10)
        assert result[0] == 'ok', result
        assert process.exitcode == 0
    else:
        process.join(30)
        assert not process.is_alive()
        assert process.exitcode == -signal.SIGKILL
    parent.close()


def test_real_process_v6_restore_keyed_restart_complete_inventory(case, tmp_path):
    service, _, historical = case
    keyset = _hash(service.paths.final_v4.key_runtime.keyset_metadata)
    registry = _hash(service.paths.final_v4.key_runtime.envelope_registry)
    prep, original, current = _prepare(service, tmp_path)
    assert current != original
    _run_restore(service, prep)
    reopened = _service(service.paths, service.loaded, service.installation_id)
    assert _content(reopened) == original
    assert classify_terminal_synthetic_v6_restore_artifacts(reopened)
    keys = reopened.paths.final_v4.key_runtime
    assert reopened._validate_key_metadata(keys.keyset_metadata, keys.envelope_registry,
        expected=service.loaded) == service.loaded
    assert _hash(reopened.paths.final_v4.key_runtime.envelope_registry) == registry
    assert _hash(historical.path) == historical.container_sha256
    assert recover_interrupted_synthetic_v6_restore(backup_service=reopened,
        runtime_root=reopened.paths.final_v4.root).status == 'normal_start'


@pytest.mark.parametrize('crash', ['before_swap','between_main_and_companion','after_swap_before_reopen'])
def test_real_sigkill_restore_existing_recovery(case, tmp_path, crash):
    service, _, _ = case
    prep, original, current = _prepare(service, tmp_path)
    _run_restore(service, prep, crash=crash)
    reopened = _service(service.paths, service.loaded, service.installation_id)
    with RuntimeInstanceLock(service.paths.final_v4.root):
        result = recover_interrupted_synthetic_v6_restore(backup_service=reopened,
            runtime_root=reopened.paths.final_v4.root)
    assert result.status in {'aborted_before_replacement', 'rolled_back'}
    assert _content(reopened) == current
    assert classify_terminal_synthetic_v6_restore_artifacts(reopened)


def test_product_handoff_rejects_synthetic_authority(case, tmp_path):
    service, _, _ = case
    prep, _, _ = _prepare(service, tmp_path)
    with pytest.raises(Exception):
        FinalV4EncryptedRestoreHandoffService(service).consume(prep.handoff.path,
            expected_nonce=prep.handoff.nonce)
    assert prep.handoff.path.exists()


def test_concurrent_process_instance_lock_blocks_restore(case, tmp_path):
    service, _, _ = case
    prep, _, current = _prepare(service, tmp_path)
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    with RuntimeInstanceLock(service.paths.final_v4.root):
        process = ctx.Process(target=_restore_worker,
            args=(service.paths, service.loaded, service.installation_id,
                prep.handoff.path, prep.handoff.nonce, child))
        process.start(); child.close()
        assert parent.poll(30)
        result = parent.recv(); process.join(10)
        assert result[:2] == ('error', 'RestoreLockError')
    parent.close()
    assert _content(_service(service.paths, service.loaded, service.installation_id)) == current


def test_insufficient_storage_preflight_preserves_live(case, tmp_path, monkeypatch):
    service, _, _ = case
    prep, _, current = _prepare(service, tmp_path)
    reopened = _service(service.paths, service.loaded, service.installation_id)
    import src.security.final_v4_live_restore as module
    # Disk exhaustion is an OS capacity condition, not a cryptographic mock.
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda root: SimpleNamespace(free=0))
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        with pytest.raises(Exception):
            SyntheticV6EncryptedLiveRestoreService(reopened).execute(
                handoff_path=prep.handoff.path, nonce=prep.handoff.nonce, lock=lock)
    assert _content(reopened) == current


def test_terminal_restore_allows_later_legitimate_writes_and_fresh_runtime(case, tmp_path):
    from src.security.synthetic_v6_runtime import SyntheticV6Runtime
    service, _, _ = case
    prep, _, _ = _prepare(service, tmp_path)
    _run_restore(service, prep)
    # Both sessions perform the full authenticated terminal classification;
    # the second must accept legitimate independent live changes.
    with SyntheticV6Runtime(_service(service.paths, service.loaded, service.installation_id)).open_existing() as opened:
        opened.lesson_time_templates.set_times(2, '08:35', '09:20')
    with SyntheticV6Runtime(_service(service.paths, service.loaded, service.installation_id)).open_existing() as opened:
        assert opened.lesson_time_templates.suggest(2).start_time == '08:35'


@pytest.mark.parametrize('part', ['main','companion','keyset','envelope','storage'])
def test_synthetic_backup_rejects_redirected_paths_before_any_io(case, tmp_path, part):
    service, _, _ = case
    before = _hash(service.paths.final_v4.database)
    original = service.paths
    external = tmp_path / 'outside-synthetic-root'
    external.mkdir(mode=0o700)
    if part == 'main':
        service.paths = replace(original, final_v4=replace(original.final_v4, database=external/'main'))
    elif part == 'companion': service.paths = replace(original, database=external/'companion')
    elif part == 'storage': service.paths = replace(original, storage_root=external)
    else:
        keys = original.final_v4.key_runtime
        keys = replace(keys, **{('keyset_metadata' if part == 'keyset' else 'envelope_registry'): external/part})
        service.paths = replace(original, final_v4=replace(original.final_v4, key_runtime=keys))
    target = tmp_path/'must-not-exist.jkmebackup'
    with pytest.raises(FinalV4EncryptedBackupError, match='paths_invalid'): service.create(target)
    assert not target.exists() and not tuple(external.iterdir())
    assert _hash(original.final_v4.database) == before


def _backup_crash_worker(paths, loaded, installation_id, output):
    def crash(boundary):
        if boundary == 'during_container_write': os.kill(os.getpid(), signal.SIGKILL)
    _service(paths, loaded, installation_id, fault_hook=crash).create(output)


def test_real_sigkill_backup_never_publishes_partial_container(case, tmp_path):
    service, _, historical = case
    original = _content(service)
    output = tmp_path/'crashed.jkmebackup'
    process = multiprocessing.get_context('spawn').Process(target=_backup_crash_worker,
        args=(service.paths, service.loaded, service.installation_id, output))
    process.start(); process.join(30)
    assert not process.is_alive() and process.exitcode == -signal.SIGKILL
    assert not output.exists()
    assert _content(service) == original
    assert _hash(historical.path) == historical.container_sha256
    # Incomplete encrypted sibling workspace is retained after process death;
    # it has no published backup/READY authority and is never auto-repaired.
    assert not tuple(tmp_path.rglob('RESTORE_READY.json'))


def test_school_year_backup_never_reports_v6_as_v4(case, tmp_path):
    from src.application.commands.school_year_transition_backup import VerifiedCipherSchoolYearTransitionBackupAdapter
    service, _, _ = case
    adapter = VerifiedCipherSchoolYearTransitionBackupAdapter(service,
        lambda: service._main_factory.connect(service.paths.final_v4.database), tmp_path)
    with pytest.raises(RuntimeError, match='final_v4_backup_required'):
        adapter.create_and_verify_during_maintenance()


def test_wrong_dmk_rejected_by_real_container_authentication(case, tmp_path):
    from src.security.backup_container import EncryptedBackupError
    service, _, _ = case
    target = service.create(tmp_path/'dmk-check.jkmebackup')
    before = _content(service)
    wrong_bytes = os.urandom(32)
    wrong = replace(service.loaded, dmk=replace(service.loaded.dmk, key_material=wrong_bytes),
        dmk_fingerprint_sha256=hashlib.sha256(wrong_bytes).hexdigest())
    verifier = _service(service.paths, wrong, service.installation_id)
    with pytest.raises(EncryptedBackupError): verifier.verify(target.path)
    assert _content(service) == before


def test_v5_runtime_manifest_and_ready_cannot_admit_v6(case, tmp_path):
    from src.security.synthetic_v5_backup_runtime import SyntheticV5EncryptedBackupManifestV1
    from src.security.synthetic_v5_runtime import KeyedSyntheticV5CompatibilityInspector, SyntheticV5RuntimeError
    from src.security.final_v4_sqlcipher_runtime import KeyedFinalV4CompatibilityInspector, FinalV4SQLCipherRuntimeError
    from src.core.restore_runtime import RestorePreflightError
    from src.security.synthetic_v5_live_restore import SyntheticV5EncryptedRestoreHandoffService
    service, _, _ = case
    target = service.create(tmp_path / "exact-v6.jkmebackup")
    with pytest.raises(FinalV4EncryptedBackupError):
        SyntheticV5EncryptedBackupManifestV1.from_bytes(target.manifest.to_bytes())
    with closing(service._provider.connect_read_only(service.paths.final_v4.database,
            key_material=service.loaded.database_key.key_material)) as connection:
        with pytest.raises(SyntheticV5RuntimeError):
            KeyedSyntheticV5CompatibilityInspector().inspect_connection(connection)
        with pytest.raises(FinalV4SQLCipherRuntimeError):
            KeyedFinalV4CompatibilityInspector().inspect_connection(connection)
    with pytest.raises(RestorePreflightError):
        SyntheticV5EncryptedRestoreHandoffService(service)


from tests.test_synthetic_v5_backup_restore import case as historical_v5_case


def test_old_v5_backup_and_ready_are_historical_only(historical_v5_case, tmp_path):
    from src.security.synthetic_v5_backup_runtime import SyntheticV5EncryptedBackupService
    service, _, _ = historical_v5_case
    target = service.create(tmp_path / "historical-v5.jkmebackup")
    stage = service.restore_staging(target.path, tmp_path / "historical-v5-stage")
    verifier = _service(service.paths, service.loaded, service.installation_id)
    before = _content(service)
    with pytest.raises(Exception):
        verifier.verify(target.path)
    with pytest.raises(Exception):
        verifier.verify_restore_ready(stage.staging_root,
            expected_container_sha256=target.container_sha256)
    with pytest.raises(Exception):
        SyntheticV6EncryptedRestoreHandoffService(service)
    assert type(service) is SyntheticV5EncryptedBackupService
    assert _content(service) == before


def test_genuine_v4_v5_v6_continuity_runtime_backup_and_live_restore(tmp_path):
    from tests.test_transactional_timetable_migration import _old_v5_source_worker
    from src.security.synthetic_v6_runtime import SyntheticV6Runtime
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=_old_v5_source_worker,
        args=(str(tmp_path.resolve()), child))
    process.start(); child.close()
    try:
        assert parent.poll(45)
        result = parent.recv(); process.join(10)
        assert process.exitcode == 0 and result[0] == "ok", result
    finally:
        if process.is_alive():
            process.kill(); process.join(10)
        parent.close()
    _, paths, loaded, installation = result
    historical_source = paths.final_v4.root / "schema-upgrade-source/transaction-v1/source.jkmebackup"
    source_hash = _hash(historical_source)
    service = _service(paths, loaded, installation)
    _migrate_fixture(service)
    with SyntheticV6Runtime(service).open_existing() as opened:
        opened.lesson_time_templates.set_times(1, "07:45", "08:30")
    prep, original, _ = _prepare(service, tmp_path)
    _run_restore(service, prep)
    with SyntheticV6Runtime(_service(paths, loaded, installation)).open_existing() as opened:
        assert opened.lesson_time_templates.suggest(1).start_time == "07:45"
    assert _content(service) == original
    assert _hash(historical_source) == source_hash
