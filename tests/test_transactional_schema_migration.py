"""Real audited SQLCipher, full historical data, native commit and crash tests."""
from contextlib import closing
from dataclasses import replace
import hashlib
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
from types import SimpleNamespace

import pytest

from src.core.database_compatibility import (DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy, UnsupportedDatabaseVersionError)
from src.core.database_content_evidence import database_content_evidence, require_same_content
from src.core.database_engine import DatabaseEngineError, SQLCipherConnectionProvider
from src.core.lesson_time_templates import LessonTimeTemplateService
from src.core.lesson_times_schema import SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION as TARGET
from src.core.maintenance_gate import MaintenanceGate, MaintenanceState, MaintenanceGateError
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.runtime_root_protection import publish_pilot_product_root, RuntimeRootProtectionError
from src.core.schema_registry import PRODUCT_SCHEMA_REGISTRY, FINAL_V4_SCHEMA_REGISTRATION as SOURCE
from src.core.schema_upgrade import UpgradeError
from src.security.transactional_schema_migration import SyntheticTransactionalMigration
from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupService, _StagedDocumentFactory
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from src.security.infrastructure.lesson_time_templates import SQLiteLessonTimeTemplateRepository
from src.security.upgrade_startup import ProductUpgradeStartupGuard, UpgradeStartupBlocked
from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider
from tests.helpers.sqlcipher_commit_probe import SQLCipherCommitProbe
from tests.helpers.synthetic_v4 import _seed_connection, SYNTHETIC_REPORT_DRAFT_ID, SYNTHETIC_LEG_DRAFT_ID
from tests.test_encrypted_upgrade_source import _open_case
from tests.test_final_v4_encrypted_backup import _add_general_document
from src.core.learning_report import ReportFinalizationService
from src.core.learning_conference import LearningConferenceCompletionService
from src.core.sqlite_store import SQLiteLearningReportRepository, SQLiteLearningConferenceRepository


def _seed_case(directory):
    runtime, service, *_ = _open_case(Path(directory).resolve())
    with runtime.final_v4.database.connect() as c:
        _seed_connection(c)
        c.execute("DELETE FROM documents")
        c.execute("UPDATE learning_conference_drafts SET agreed_goals_text='Synthetische Vereinbarung'")
        c.execute("INSERT INTO timetable_entries VALUES ('TTE-SYNTHETIC',1,'09:00','10:00','SUB-TEST-DE','group','GRP-TEST-A','',1,0,'2026-01-01T08:00:00Z','2026-01-01T08:00:00Z','')")
        c.execute("INSERT INTO persistence_events(operation_token,operation_index,operation_payload_hash,event_kind,student_id,observation_id,technical_timestamp,ordering_state) SELECT 'synthetic-event',0,?,'observation_created',student_id,observation_id,created_at,'not_applicable' FROM observations LIMIT 1", ('e'*64,))
        c.commit()
    _add_general_document(runtime, document_id='MED-000001', payload=b'SYNTHETIC-SECRET-DOCUMENT')
    ReportFinalizationService(SQLiteLearningReportRepository(runtime.final_v4.database)).finalize(
        report_draft_id=SYNTHETIC_REPORT_DRAFT_ID, finalized_by_display_name='Synthetische Lehrkraft')
    LearningConferenceCompletionService(SQLiteLearningConferenceRepository(runtime.final_v4.database)).complete(
        learning_conference_draft_id=SYNTHETIC_LEG_DRAFT_ID)
    return runtime, service


@pytest.fixture
def case(tmp_path):
    return _seed_case(tmp_path)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _protected(service):
    keypaths = service.paths.final_v4.key_runtime
    files = (service.paths.database, keypaths.keyset_metadata, keypaths.envelope_registry,
             *service.paths.storage_root.rglob('*.jkmedoc'))
    return {str(p): _hash(p) for p in files}


def _inspection_service(paths, loaded, installation_id):
    # Existing-only composition, no source/target main runtime initialization.
    provider = qualified_sqlcipher_test_provider()
    return FinalV4EncryptedBackupService(opened_runtime=None, paths=paths,
        loaded_keys=loaded, main_factory=None,
        document_factory=_StagedDocumentFactory(provider, paths.database, loaded.database_key.key_material),
        provider=provider, maintenance_gate=MaintenanceGate(), random_source=SystemRandomSource(),
        clock=SystemClock(), installation_id=installation_id)


def _restart_worker(paths, loaded, installation_id, channel, use_times=False):
    try:
        service = _inspection_service(paths, loaded, installation_id)
        identity = SyntheticTransactionalMigration(service).inspect_restart()
        if use_times:
            migration = SyntheticTransactionalMigration(service)
            restored = service.restore_staging(migration.backup,
                paths.final_v4.root.parent / 'synthetic-restored-v4-source')
            assert restored.state == 'RESTORE_READY'
            assert restored.active_document_count == 1
            main = paths.final_v4.database
            key = loaded.database_key.key_material
            repo = SQLiteLessonTimeTemplateRepository(lambda: service._provider.connect(main, create=False, key_material=key))
            domain = LessonTimeTemplateService(repo)
            domain.set_times(1, '08:00', '08:45')
            copy = domain.suggest(1)
            explicit = domain.suggest(1, start_time='08:10', end_time='08:55')
            domain.set_times(1, '08:05', '08:50')
            assert copy.start_time == '08:00' and explicit.start_time == '08:10'
            with closing(service._provider.connect_read_only(main, key_material=key)) as c:
                assert tuple(c.execute("SELECT start_time,end_time FROM timetable_entries WHERE timetable_entry_id='TTE-SYNTHETIC'").fetchone()) == ('09:00', '10:00')
            assert repo.list_templates() == (domain.suggest(1),)
        channel.send(('ok', identity))
    except BaseException as error:
        channel.send(('error', type(error).__name__, str(error)))
    finally:
        channel.close()


def _restart(service, use_times=False):
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_restart_worker,
        args=(service.paths, service.loaded, service.installation_id, child, use_times))
    process.start(); child.close()
    try:
        assert parent.poll(45), 'restart worker did not report'
        result = parent.recv()
        process.join(10)
        assert process.exitcode == 0
        assert result[0] == 'ok', result
        return result[1]
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()


def test_real_atomic_migration_full_backup_source_and_domain_function(case):
    runtime, service = case
    protected = _protected(service)
    loaded = service.loaded
    m = SyntheticTransactionalMigration(service)
    existing_files = {p for p in m.root.rglob('*') if p.is_file()}
    source_hash = _hash(m.main)
    emitted = []
    def observe(boundary):
        emitted.append(boundary)
        if boundary in {'source_verified', 'backup_verified', 'connections_closed'}:
            assert _hash(m.main) == source_hash
    m._fault_hook = observe
    assert m.execute() == TARGET.identity
    assert emitted[-1] == 'connection_closed'
    assert service._gate.state is MaintenanceState.RECOVERY_REQUIRED
    assert service.loaded == loaded and _protected(service) == protected
    with pytest.raises(MaintenanceGateError):
        service._provider.connect(m.main, create=False, key_material=loaded.database_key.key_material)
    assert _restart(service, use_times=True) == TARGET.identity
    assert PRODUCT_SCHEMA_REGISTRY.schemas == (SOURCE,) and not PRODUCT_SCHEMA_REGISTRY.upgrades
    assert m.main.stat().st_nlink == 1
    assert not m.main.read_bytes().startswith(b'SQLite format 3')
    assert b'SYNTHETIC-SECRET-DOCUMENT' not in m.backup.read_bytes()
    for path in (p for p in m.root.rglob('*') if p.is_file() and p not in existing_files):
        raw = path.read_bytes()
        assert not raw.startswith(b'SQLite format 3')
        assert b'SYNTHETIC-SECRET-DOCUMENT' not in raw
        assert loaded.dmk.key_material not in raw
        assert loaded.database_key.key_material not in raw
    with sqlite3.connect(f'{m.main.as_uri()}?mode=ro&immutable=1', uri=True) as plain:
        with pytest.raises(sqlite3.DatabaseError): plain.execute('SELECT * FROM students').fetchall()
    with pytest.raises(UpgradeError, match='restart_required'): m.execute()
    with pytest.raises(UpgradeError, match='existing_evidence'): SyntheticTransactionalMigration(service).execute()


@pytest.mark.parametrize('boundary', ['schema_changed', 'target_verified', 'before_commit'])
def test_sql_error_rolls_back_all_ddl_and_version(case, boundary):
    _, service = case
    m = SyntheticTransactionalMigration(service)
    protected = _protected(service); before = _hash(m.main)
    # Execute invalid SQL through the same native connection, rather than a mock exception.
    original = m._configure_transaction
    def configure(c):
        original(c)
        m._fault_hook = lambda value: c.execute('INSERT INTO deliberately_missing_synthetic_table VALUES (1)') if value == boundary else None
    m._configure_transaction = configure
    with pytest.raises(service._provider._load_driver().OperationalError): m.execute()
    assert _hash(m.main) == before
    assert _protected(service) == protected
    assert _restart(service) == SOURCE.identity


def _crash_worker(directory, boundary, channel):
    try:
        _, service = _seed_case(directory)
        m = SyntheticTransactionalMigration(service)
        channel.send(('ready', service.paths, service.loaded, service.installation_id,
                      _hash(m.main), _protected(service), m.main.stat().st_ino))
        probe = None
        if boundary.startswith('vfs_'):
            probe = SQLCipherCommitProbe(service._provider, m.main, channel, boundary)
        def pause(value):
            if probe is not None and value == 'before_commit': probe.armed = True
            if value == boundary:
                channel.send((boundary,))
                signal.pause()
        m._fault_hook = pause
        m.execute()
        channel.send(('unexpected_completion',))
    except BaseException as error:
        channel.send(('error', type(error).__name__, str(error)))


@pytest.mark.parametrize('boundary', ['transaction_begun', 'schema_changed', 'target_verified',
    'before_commit', 'vfs_before_journal_delete', 'vfs_after_journal_delete', 'after_commit', 'connection_closed'])
def test_real_sigkill_including_native_commit_deletion(tmp_path, boundary):
    ctx = multiprocessing.get_context('spawn'); parent, child = ctx.Pipe()
    process = ctx.Process(target=_crash_worker, args=(str(tmp_path.resolve()), boundary, child))
    process.start(); child.close()
    try:
        assert parent.poll(50); ready = parent.recv(); assert ready[0] == 'ready', ready
        _, paths, loaded, installation, source_hash, protected, inode = ready
        assert parent.poll(50); reached = parent.recv(); assert reached[0] == boundary, reached
        main = paths.final_v4.database
        journal = Path(str(main)+'-journal')
        if boundary == 'vfs_before_journal_delete':
            assert journal.exists() and journal.stat().st_size > 512
            assert _hash(main) != source_hash, 'Must interrupt after real main-page writes'
            assert reached[1] == 1, 'EXTRA requires directory sync'
            assert b'SYNTHETIC-SECRET' not in journal.read_bytes()
            assert not journal.read_bytes().startswith(b'SQLite format 3')
        if boundary == 'vfs_after_journal_delete':
            assert not journal.exists() and reached[2] == 0
        os.kill(process.pid, signal.SIGKILL); process.join(10)
        assert process.exitcode == -signal.SIGKILL
        service = _inspection_service(paths, loaded, installation)
        # A fresh spawned process opens with the same existing keys, SQLite
        # recovers a hot journal, then independently verifies all data+backup.
        expected = TARGET.identity if boundary in {'vfs_after_journal_delete','after_commit','connection_closed'} else SOURCE.identity
        assert _restart(service) == expected
        assert _protected(service) == protected
        assert main.stat().st_ino == inode
        if journal.exists():
            # SQLite leaves an unsynced, non-hot journal when only its page
            # cache changed. Preserve it: no application-side deletion.
            assert expected == SOURCE.identity
            assert journal.read_bytes()[:8] == b'\x00'*8
            assert _hash(main) == source_hash
        assert not main.read_bytes().startswith(b'SQLite format 3')
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()


def test_wrong_keys_corruption_unknown_target_and_product_root_block(case, tmp_path):
    _, service = case
    m = SyntheticTransactionalMigration(service); before = _hash(m.main)
    with pytest.raises(DatabaseEngineError):
        with closing(service._provider.connect_read_only(m.main, key_material=b'W'*32)): pass
    assert _hash(m.main) == before
    # Root rejection happens before any key/database access; no product data created.
    root = tmp_path / 'synthetic-product-protection-probe'; root.mkdir(mode=0o700)
    publish_pilot_product_root(root.resolve())
    service_paths = SimpleNamespace(final_v4=SimpleNamespace(root=root.resolve()))
    with pytest.raises(RuntimeRootProtectionError):
        SyntheticTransactionalMigration(SimpleNamespace(paths=service_paths))
    assert not tuple(root.glob('**/*.sqlcipher'))
    # Unknown source cannot be converted into an empty/new database.
    with closing(service._provider.connect(m.main, create=False, key_material=service.loaded.database_key.key_material)) as c:
        c.execute('PRAGMA user_version=99'); c.commit()
    damaged = _hash(m.main)
    with pytest.raises(Exception): m.execute()
    assert _hash(m.main) == damaged and not m.backup.exists()


def test_initial_sidecars_refused_without_checkpoint_or_cleanup(case):
    _, service = case
    m = SyntheticTransactionalMigration(service)
    sidecar = Path(str(m.main)+'-wal'); sidecar.write_bytes(b'SYNTHETIC WAL EVIDENCE'); sidecar.chmod(0o600)
    before = _hash(m.main)
    with pytest.raises(UpgradeError, match='sidecar_requires_separate_recovery'): m.execute()
    assert _hash(m.main) == before and sidecar.read_bytes() == b'SYNTHETIC WAL EVIDENCE'
    assert not m.backup.exists()


def test_live_own_connection_prevents_migration_and_never_force_commits(case):
    runtime, service = case
    connection = runtime.final_v4.database.connect()
    main = service.paths.final_v4.database; before = _hash(main)
    try:
        with pytest.raises(MaintenanceGateError, match='connections_active'):
            SyntheticTransactionalMigration(service).execute()
        assert _hash(main) == before and not connection.in_transaction
    finally:
        connection.close()
    assert _restart(service) == SOURCE.identity


def _raw_existing(provider, path, key):
    """Real keyed connection preserving WAL mode for explicit checkpoint probes."""
    driver = provider._load_driver()
    c = driver.connect(f'{Path(path).as_uri()}?mode=rw', uri=True, cached_statements=0)
    provider._apply_key(c, bytearray(key))
    provider._configure_cipher_before_authentication(c)
    provider._authenticate_schema(c)
    c.row_factory = driver.Row
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=0')
    return c


def _competing_process(root, main, key, kind, channel):
    try:
        if kind == 'app':
            with RuntimeInstanceLock(Path(root)):
                channel.send('held'); channel.recv()
        else:
            p = qualified_sqlcipher_test_provider()
            with closing(_raw_existing(p, main, key)) as c:
                c.execute('BEGIN IMMEDIATE' if kind == 'writer' else 'BEGIN')
                c.execute('SELECT count(*) FROM students').fetchone()
                channel.send('held'); channel.recv(); c.rollback()
    finally:
        channel.close()


def _competitor(service, kind):
    ctx = multiprocessing.get_context('spawn'); parent, child = ctx.Pipe()
    process = ctx.Process(target=_competing_process, args=(str(service.paths.final_v4.root),
        service.paths.final_v4.database, service.loaded.database_key.key_material, kind, child))
    process.start(); child.close()
    assert parent.poll(30) and parent.recv() == 'held'
    return process, parent


def _release_competitor(process, channel):
    channel.send('finish'); process.join(10)
    if process.is_alive(): process.kill(); process.join(10)
    channel.close()
    assert process.exitcode == 0


@pytest.mark.parametrize('kind', ['app', 'reader', 'writer'])
def test_real_normal_app_and_sqlite_competitors_block_without_main_mutation(case, kind):
    from src.core.restore_runtime import RestoreLockError
    _, service = case
    m = SyntheticTransactionalMigration(service)
    before = _hash(m.main); protected = _protected(service)
    process, channel = _competitor(service, kind)
    try:
        if kind == 'app':
            with pytest.raises(RestoreLockError): m.execute()
            assert not m.backup.exists()
        else:
            with pytest.raises(service._provider._load_driver().OperationalError, match='locked'):
                m.execute()
            assert m.backup.exists(), 'Backup can read a stable source before EXCLUSIVE refuses competition'
        assert _hash(m.main) == before and _protected(service) == protected
    finally:
        _release_competitor(process, channel)
    if kind != 'app': assert _restart(service) == SOURCE.identity


def test_real_wal_busy_checkpoint_and_no_implicit_checkpoint(case):
    _, service = case
    m = SyntheticTransactionalMigration(service); key = service.loaded.database_key.key_material
    with closing(_raw_existing(service._provider, m.main, key)) as writer:
        assert writer.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
        writer.execute('PRAGMA wal_autocheckpoint=0')
        writer.execute("UPDATE students SET notes='SYNTHETIC WAL FIRST'"); writer.commit()
        process, channel = _competitor(service, 'reader')
        try:
            writer.execute("UPDATE students SET notes='SYNTHETIC WAL SECOND'"); writer.commit()
            wal = Path(str(m.main)+'-wal'); before_wal = wal.read_bytes(); before_main = _hash(m.main)
            assert len(before_wal) > 32 and b'SYNTHETIC WAL' not in before_wal
            row = writer.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            assert row[0] == 1, tuple(row)
            with pytest.raises(UpgradeError, match='sidecar_requires_separate_recovery'): m.execute()
            assert _hash(m.main) == before_main and wal.read_bytes() == before_wal
            assert not m.backup.exists()
        finally:
            _release_competitor(process, channel)
        assert tuple(writer.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()) == (0,0,0)
        assert not wal.exists() or wal.stat().st_size == 0
    assert not Path(str(m.main)+'-wal').exists()
    with closing(service._provider.connect_read_only(m.main, key_material=key)) as c:
        service._provider.verify_integrity(c)
        assert {row[0] for row in c.execute('SELECT notes FROM students')} == {'SYNTHETIC WAL SECOND'}


@pytest.mark.parametrize('damage', ['foreign_key', 'data_loss'])
def test_real_fk_error_or_incomplete_transfer_rolls_back(case, damage):
    _, service = case
    m = SyntheticTransactionalMigration(service); before = _hash(m.main)
    original = m._configure_transaction
    def configure(c):
        original(c)
        def inject(boundary):
            if boundary == 'schema_changed':
                if damage == 'foreign_key':
                    c.execute("INSERT INTO observations(observation_id,student_id,date,subject_id,active,created_at,updated_at) VALUES ('OBS-INVALID','MISSING-STUDENT','2026-10-15','SUB-TEST-DE',1,'2026-10-15','2026-10-15')")
                else:
                    c.execute("UPDATE students SET first_name='SYNTHETIC LOST VALUE'")
        m._fault_hook = inject
    m._configure_transaction = configure
    error = service._provider._load_driver().IntegrityError if damage == 'foreign_key' else UpgradeError
    with pytest.raises(error): m.execute()
    assert _hash(m.main) == before
    assert _restart(service) == SOURCE.identity


@pytest.mark.parametrize('damage', ['cipher_page', 'bad_fk', 'domain_reference', 'missing_main'])
def test_real_corrupt_sources_never_backup_migrate_or_first_run(case, damage):
    from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimeError
    _, service = case
    m = SyntheticTransactionalMigration(service)
    if damage == 'cipher_page':
        data = bytearray(m.main.read_bytes()); data[5000] ^= 0x7f; m.main.write_bytes(data)
    elif damage == 'missing_main':
        m.main.unlink()
    else:
        with closing(service._provider.connect(m.main, create=False, key_material=service.loaded.database_key.key_material)) as c:
            if damage == 'bad_fk':
                c.execute('PRAGMA foreign_keys=OFF')
                c.execute("UPDATE observations SET student_id='MISSING-STUDENT'")
            else:
                c.execute("UPDATE timetable_entries SET subject_id='MISSING-SUBJECT'")
            c.commit()
    before = m.main.read_bytes() if m.main.exists() else None
    with pytest.raises((DatabaseEngineError, FinalV4SQLCipherRuntimeError, UpgradeError)):
        m.execute()
    assert (m.main.read_bytes() if m.main.exists() else None) == before
    assert not m.backup.exists()


@pytest.mark.parametrize('ancestor', ['transaction', 'source', 'root'])
def test_backup_directory_sync_failure_aborts_before_main_transaction(case, monkeypatch, ancestor):
    _, service = case
    m = SyntheticTransactionalMigration(service); before = _hash(m.main); reached = []
    original = m._sync_backup_chain
    expected = {'transaction': m.backup.parent, 'source': m.backup.parent.parent, 'root': m.root}[ancestor]
    def arm():
        original_fsync = os.fsync
        def fail(fd):
            if os.fstat(fd).st_ino == expected.stat().st_ino:
                raise OSError('synthetic directory fsync failure')
            return original_fsync(fd)
        monkeypatch.setattr(os, 'fsync', fail)
        original()
    m._sync_backup_chain = arm; m._fault_hook = reached.append
    with pytest.raises(OSError, match='directory fsync failure'): m.execute()
    assert _hash(m.main) == before
    assert 'transaction_begun' not in reached


def test_backup_sync_chain_is_complete_and_precedes_begin(case, monkeypatch):
    _, service = case
    m = SyntheticTransactionalMigration(service); synced = []; reached = []
    import src.security.transactional_schema_migration as module
    original = module._fsync_directory
    def record(path): synced.append(path); original(path)
    monkeypatch.setattr(module, '_fsync_directory', record)
    def observe(boundary):
        reached.append(boundary)
        if boundary == 'transaction_begun':
            assert synced == [m.backup.parent, m.backup.parent.parent, m.root]
    m._fault_hook = observe
    m.execute()
    assert reached.index('backup_verified') < reached.index('transaction_begun')


def test_conflicting_restore_evidence_never_migrates(case):
    _, service = case
    (service.paths.final_v4.root/'restore-transactions').mkdir(mode=0o700)
    m = SyntheticTransactionalMigration(service); before = _hash(m.main)
    with pytest.raises(UpgradeError, match='existing_evidence'): m.execute()
    assert _hash(m.main) == before and not m.backup.exists()


def _old_runtime_worker(paths, loaded, installation_id, channel):
    from tests.test_final_v4_sqlcipher_runtime import MemoryDataMasterKeyStore, _account_loader, _environment
    from src.security.final_v4_sqlcipher_runtime import run_gated_final_v4_sqlcipher_runtime
    store = MemoryDataMasterKeyStore()
    store.values[(installation_id, loaded.dmk_key_id)] = loaded.dmk.key_material
    environment = _environment(paths.final_v4.root)
    provider = qualified_sqlcipher_test_provider()
    before = _hash(paths.final_v4.database)
    with closing(provider.connect_read_only(paths.final_v4.database, key_material=loaded.database_key.key_material)) as c:
        report = DatabaseCompatibilityInspector().inspect_connection(c)
        try: DatabaseCompatibilityPolicy.require_backup_compatible(report)
        except UnsupportedDatabaseVersionError: pass
        else: raise AssertionError('Old backup policy admitted V5')
    decision = run_gated_final_v4_sqlcipher_runtime(account_loader=_account_loader(installation_id),
        authentication_confirmed=True, technical_first_run_confirmed=True,
        environ=environment, key_store=store, sqlcipher_provider=provider)
    assert decision.runtime is None
    assert store.create_calls == 0 and _hash(paths.final_v4.database) == before
    with RuntimeInstanceLock(paths.final_v4.root) as lock:
        try: ProductUpgradeStartupGuard(lock).evaluate()
        except UpgradeStartupBlocked: pass
        else: raise AssertionError('A2 admitted new transaction evidence')
    channel.send(('blocked', decision.error_code))


def test_old_runtime_backup_and_a2_refuse_target_without_first_run(case):
    _, service = case
    SyntheticTransactionalMigration(service).execute()
    ctx = multiprocessing.get_context('spawn'); parent, child = ctx.Pipe()
    process = ctx.Process(target=_old_runtime_worker, args=(service.paths, service.loaded, service.installation_id, child))
    process.start(); child.close()
    try:
        assert parent.poll(45); assert parent.recv()[0] == 'blocked'
        process.join(10); assert process.exitcode == 0
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()
