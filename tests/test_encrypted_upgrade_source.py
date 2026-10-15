"""Real qualified SQLCipher tests; no substitute or new skip rule."""
from __future__ import annotations
from dataclasses import replace
import hashlib
import importlib.metadata
import multiprocessing
import os
from pathlib import Path
from queue import Empty
import signal
import sqlite3
from uuid import uuid4
import pytest

from src.core.database_content_evidence import database_content_evidence, require_same_content
from src.core.schema_registry import (DatabaseSchemaRegistry, SchemaRegistration, SchemaUpgradeRelation,
    RegisteredSchemaIdentity, FINAL_V4_SCHEMA_REGISTRATION, PRODUCT_SCHEMA_REGISTRY,
    SCHEMA_FINGERPRINT_ALGORITHM)
from src.core.schema_upgrade import UpgradeContext, UpgradeError, UpgradePhase, classify_upgrade, UpgradeRecoveryStatus
from src.core.restore_runtime import RuntimeInstanceLock
from src.core.observation_uow import ObservationWriterLock
from src.core.learning_report import ReportFinalizationService
from src.core.learning_conference import LearningConferenceCompletionService
from src.core.sqlite_store import SQLiteLearningReportRepository, SQLiteLearningConferenceRepository
from tests.historical_upgrade.prepare_upgrade_source import PrepareEncryptedUpgradeSource
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.infrastructure.system import PlatformFilePermissionManager
from tests.historical_upgrade.upgrade_process_lease import UpgradeProcessLease
from tests.historical_upgrade.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository
from tests.historical_upgrade.encrypted_upgrade_source import EncryptedUpgradeSourceAdapter
from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupError
from tests.test_final_v4_encrypted_backup import _add_general_document, INSTALLATION_ID
from tests.test_final_v4_sqlcipher_runtime import MemoryDataMasterKeyStore, _root, _environment, _account_loader
from src.core.database_engine import SQLCipherConnectionProvider, SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION
from src.security.final_v3_document_runtime import run_gated_final_v4_document_runtime
from src.security.final_v4_backup_runtime import build_final_v4_encrypted_backup_service
from tests.historical_upgrade.schema_upgrade import UpgradeMaintenance
from tests.helpers.synthetic_v4 import _seed_connection, SYNTHETIC_REPORT_DRAFT_ID, SYNTHETIC_LEG_DRAFT_ID

from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider


def _open_case(tmp_path):
    root=_root(tmp_path); environment=_environment(root)
    key_store=MemoryDataMasterKeyStore(); account_loader=_account_loader(INSTALLATION_ID)
    provider=qualified_sqlcipher_test_provider()
    decision=run_gated_final_v4_document_runtime(account_loader=account_loader,
        authentication_confirmed=True,technical_first_run_confirmed=True,
        document_database_create_allowed=True,environ=environment,key_store=key_store,
        sqlcipher_provider=provider)
    assert decision.runtime is not None
    service=build_final_v4_encrypted_backup_service(opened_runtime=decision.runtime,
        account_loader=account_loader,environ=environment,key_store=key_store,sqlcipher_provider=provider)
    return decision.runtime,service,key_store,environment,account_loader,provider


def _registry():
    target=RegisteredSchemaIdentity(5,"b"*64,SCHEMA_FINGERPRINT_ALGORITHM)
    return DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION,SchemaRegistration("test_only",target,frozenset())),
        (SchemaUpgradeRelation(FINAL_V4_SCHEMA_REGISTRATION.identity,target),))


def _context(service):
    loaded=service.loaded
    return UpgradeContext(str(uuid4()),service.installation_id,loaded.database_context_id,
        loaded.database_key_id,loaded.database_key_generation,loaded.dmk_key_id,loaded.dmk_generation,
        FINAL_V4_SCHEMA_REGISTRATION.identity,_registry().schemas[1].identity,"synthetic_no_transform")


def _runner(service, lock, ctx, fault_hook=None):
    lease=UpgradeProcessLease(lock,ctx,service.paths.final_v4.runtime_root / ".observation-staging")
    journal=AuthenticatedUpgradeJournalRepository(lock.runtime_root / "schema-upgrade-foundation" / "journal.json",
        PlatformFilePermissionManager(),context=ctx,registry=_registry(),lease=lease)
    key=derive_migration_journal_auth_key(service.loaded.dmk,migration_id=ctx.operation_id)
    adapter=EncryptedUpgradeSourceAdapter(service,lease,ctx,fault_hook=fault_hook)
    runner=PrepareEncryptedUpgradeSource(context=ctx,registry=_registry(),gate=service._gate,
        lease=lease,journal=journal,auth_key=key,adapter=adapter)
    return runner,adapter,journal,key


@pytest.fixture
def case(tmp_path):
    runtime,service,*_= _open_case(tmp_path)
    with runtime.final_v4.database.connect() as connection:
        _seed_connection(connection)
        connection.execute("DELETE FROM documents")  # remove synthetic legacy path references; no files exist
        connection.execute("UPDATE learning_conference_drafts SET agreed_goals_text='Synthetische Vereinbarung'")
        connection.execute("INSERT INTO persistence_events(operation_token,operation_index,operation_payload_hash,event_kind,student_id,observation_id,technical_timestamp,ordering_state) SELECT 'test-event',0,?,'observation_created',student_id,observation_id,created_at,'not_applicable' FROM observations LIMIT 1",("e"*64,))
        connection.execute("INSERT INTO timetable_entries(timetable_entry_id,weekday,start_time,end_time,subject_id,target_type,target_id,room,active,sort_order,created_at,updated_at,deleted_at) VALUES ('TTE-TEST-001',1,'09:00','10:00','SUB-TEST-DE','group','GRP-TEST-A','',1,0,'2026-01-01T08:00:00Z','2026-01-01T08:00:00Z','')")
        connection.commit()
    _add_general_document(runtime,document_id="MED-000001",payload=b"SYNTHETIC-SECRET-DOCUMENT")
    ReportFinalizationService(SQLiteLearningReportRepository(runtime.final_v4.database)).finalize(
        report_draft_id=SYNTHETIC_REPORT_DRAFT_ID,finalized_by_display_name="Synthetische Lehrkraft")
    LearningConferenceCompletionService(SQLiteLearningConferenceRepository(runtime.final_v4.database)).complete(
        learning_conference_draft_id=SYNTHETIC_LEG_DRAFT_ID)
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        ctx=_context(service)
        yield runtime,service,lock,ctx


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_real_encrypted_backup_stage_full_values_and_idempotence(case):
    runtime,service,lock,ctx=case
    runner,adapter,journal,key=_runner(service,lock,ctx)
    source=service.paths.final_v4.database; companion=service.paths.database
    before=(_hash(source),_hash(companion))
    state=runner.execute()
    assert state.phase is UpgradePhase.STAGED
    assert (_hash(source),_hash(companion))==before
    assert runner.execute()==state
    assert (_hash(source),_hash(companion))==before
    assert not tuple(adapter.workspace.rglob('*RESTORE_READY*'))
    assert not adapter.candidate_path.read_bytes().startswith(b'SQLite format 3')
    assert b'SYNTHETIC-SECRET-DOCUMENT' not in adapter.backup_path.read_bytes()
    assert (adapter.candidate_path.stat().st_mode & 0o777)==0o600
    uri=adapter.candidate_path.resolve().as_uri()+'?mode=ro&immutable=1'
    with sqlite3.connect(uri,uri=True) as connection:
        with pytest.raises(sqlite3.DatabaseError): connection.execute('SELECT * FROM students').fetchall()
    with service.verified_snapshot(adapter.backup_path) as snapshot:
        with service._provider.connect_read_only(snapshot.database_path,key_material=service.loaded.database_key.key_material) as connection:
            tables=dict((name,count) for name,count,_ in database_content_evidence(connection).tables)
            assert all(tables[name]>0 for name in ('students','observations','observation_competency_ratings',
                'persistence_events','timetable_entries','learning_report_revisions','learning_conference_revisions'))
        assert not tuple(snapshot.staging_root.rglob('*RESTORE_READY*'))
    assert not snapshot.staging_root.exists()
    assert PRODUCT_SCHEMA_REGISTRY.schemas==(FINAL_V4_SCHEMA_REGISTRATION,)
    assert not PRODUCT_SCHEMA_REGISTRY.upgrades


@pytest.mark.parametrize('field',['installation_id','database_context_id','database_key_id','dmk_key_id'])
def test_wrong_context_and_unknown_target_rejected_before_backup(case,field):
    _,service,lock,ctx=case
    before=_hash(service.paths.final_v4.database)
    bad=replace(ctx,**{field:str(uuid4())})
    runner,adapter,_,_=_runner(service,lock,bad)
    with pytest.raises(UpgradeError,match='context_mismatch'): runner.execute()
    assert not adapter.backup_path.exists() and _hash(service.paths.final_v4.database)==before


@pytest.mark.parametrize('damage',['version','schema','cipher','target_reference','foreign_key','document_reference','sidecar'])
def test_bad_source_never_authorizes_backup(case,damage):
    _,service,lock,ctx=case
    path=service.paths.final_v4.database
    if damage=='cipher':
        data=bytearray(path.read_bytes()); data[60]^=1; path.write_bytes(data)
    elif damage=='document_reference':
        with service._main_factory.connect(path,create=False) as connection:
            connection.execute("UPDATE documents SET document_id='MED-999999'"); connection.commit()
    elif damage=='foreign_key':
        with service._provider.connect(path,create=False,key_material=service.loaded.database_key.key_material) as connection:
            connection.execute('PRAGMA foreign_keys=OFF')
            connection.execute("UPDATE observations SET student_id='missing-student'")
            connection.commit()
    elif damage=='sidecar':
        Path(str(path)+'-wal').write_bytes(b'synthetic-unresolved-sidecar')
    else:
        with service._main_factory.connect(path,create=False) as connection:
            if damage=='version': connection.execute('PRAGMA user_version=5')
            elif damage=='schema': connection.execute('CREATE TABLE unknown(value TEXT)')
            else: connection.execute("UPDATE timetable_entries SET target_id='missing'")
            connection.commit()
    before=_hash(path)
    runner,adapter,_,_=_runner(service,lock,ctx)
    with pytest.raises(Exception): runner.execute()
    assert not adapter.backup_path.exists() and _hash(path)==before


@pytest.mark.parametrize('boundary',['during_staging_copy','after_staging_copy','after_backup_publication'])
def test_faults_keep_original_and_recovery_blocks_repeat(case,boundary):
    _,service,lock,ctx=case
    before=_hash(service.paths.final_v4.database)
    def fault(value):
        if value==boundary: raise OSError('synthetic ENOSPC/access error')
    runner,adapter,_,_=_runner(service,lock,ctx,fault)
    with pytest.raises(OSError): runner.execute()
    assert _hash(service.paths.final_v4.database)==before
    assert not adapter.candidate_path.exists()
    assert b'"recovery_required"' in runner.journal.path.read_bytes()
    with pytest.raises(Exception): runner.execute()
    assert _hash(service.paths.final_v4.database)==before


@pytest.mark.parametrize('damage',['backup','candidate','candidate_value','journal'])
def test_successful_evidence_is_rechecked_on_repeat(case,damage):
    _,service,lock,ctx=case
    runner,adapter,_,_=_runner(service,lock,ctx)
    runner.execute(); before=_hash(service.paths.final_v4.database)
    if damage=='candidate_value':
        with service._provider.connect(adapter.candidate_path,create=False,key_material=service.loaded.database_key.key_material) as connection:
            connection.execute("UPDATE students SET notes='changed without row-count change'"); connection.commit()
    else:
        path={'backup':adapter.backup_path,'candidate':adapter.candidate_path,'journal':runner.journal.path}[damage]
        data=bytearray(path.read_bytes()); data[len(data)//2]^=1; path.write_bytes(data)
    with pytest.raises(Exception): runner.execute()
    assert _hash(service.paths.final_v4.database)==before


def test_unregistered_product_edge_cannot_create_preparation(case):
    _,service,lock,ctx=case
    runner,adapter,_,_=_runner(service,lock,ctx); runner.registry=PRODUCT_SCHEMA_REGISTRY
    with pytest.raises(ValueError): runner.execute()
    assert not runner.journal.path.exists() and not adapter.workspace.exists()


def test_wrong_key_rejected_without_source_change(case):
    _,service,lock,ctx=case
    source=service.paths.final_v4.database; before=_hash(source)
    service.loaded=replace(service.loaded,database_key=replace(service.loaded.database_key,key_material=os.urandom(32)))
    runner,adapter,_,_=_runner(service,lock,ctx)
    with pytest.raises(Exception): runner.execute()
    assert _hash(source)==before and not adapter.backup_path.exists()


def test_typed_comparison_values_null_blob_types_and_order():
    with sqlite3.connect(':memory:') as left,sqlite3.connect(':memory:') as right:
        for connection in (left,right): connection.execute('CREATE TABLE typed(value)')
        values=[(None,),(1,),(1.0,),('1',),(b'1',),('Ä\ntext',)]
        left.executemany('INSERT INTO typed VALUES (?)',values)
        right.executemany('INSERT INTO typed VALUES (?)',reversed(values))
        first=database_content_evidence(left)
        require_same_content(first,database_content_evidence(right))
        right.execute("UPDATE typed SET value='NULL' WHERE value IS NULL")
        with pytest.raises(UpgradeError): require_same_content(first,database_content_evidence(right))


def _competing(root,queue):
    try:
        with RuntimeInstanceLock(Path(root)): queue.put('unexpected-acquisition')
    except Exception as error: queue.put(type(error).__name__)


def _crash_prepare(root_directory,queue,boundary):
    # All generated data and keys are fresh and synthetic in this separate process.
    root_directory=Path(root_directory)
    runtime,service,*_=_open_case(root_directory)
    lock=RuntimeInstanceLock(service.paths.final_v4.root).acquire(); ctx=_context(service)
    before=_hash(service.paths.final_v4.database)
    def pause(value):
        if value==boundary:
            queue.put((str(service.paths.final_v4.root),before,ctx,service.loaded.dmk))
            signal.pause()
    runner,adapter,_,_=_runner(service,lock,ctx,pause)
    runner.execute()


def test_real_competing_process_cannot_enter(case):
    _,service,lock,ctx=case
    spawn=multiprocessing.get_context('spawn'); queue=spawn.Queue()
    child=spawn.Process(target=_competing,args=(str(lock.runtime_root),queue)); child.start()
    try:
        assert queue.get(timeout=15)=='RestoreLockError'
        child.join(15); assert child.exitcode==0
    finally:
        if child.is_alive(): child.terminate(); child.join(15)


@pytest.mark.parametrize('boundary',['after_backup_publication','during_staging_copy'])
def test_real_process_crash_never_publishes_staged_phase(tmp_path,boundary):
    spawn=multiprocessing.get_context('spawn'); queue=spawn.Queue()
    directory=tmp_path / 'crash-case'; directory.mkdir()
    child=spawn.Process(target=_crash_prepare,args=(str(directory),queue,boundary)); child.start()
    try:
        root,before,ctx,dmk=queue.get(timeout=30)
    finally:
        child.terminate(); child.join(15)
    root=Path(root)
    assert _hash(root / 'final-v4-sqlcipher-runtime-v1' / 'final-v4.sqlcipher')==before
    raw=(root / 'schema-upgrade-foundation' / 'journal.json').read_bytes()
    assert b'"staged"' not in raw and b'"completed"' not in raw
    key_store=MemoryDataMasterKeyStore()
    key_store.values[(ctx.installation_id,dmk.key_id)]=dmk.key_material
    environment=_environment(root); account_loader=_account_loader(ctx.installation_id)
    provider=qualified_sqlcipher_test_provider()
    decision=run_gated_final_v4_document_runtime(account_loader=account_loader,
        authentication_confirmed=True,technical_first_run_confirmed=False,
        document_database_create_allowed=False,environ=environment,key_store=key_store,
        sqlcipher_provider=provider)
    assert decision.runtime is not None
    service=build_final_v4_encrypted_backup_service(opened_runtime=decision.runtime,
        account_loader=account_loader,environ=environment,key_store=key_store,sqlcipher_provider=provider)
    with RuntimeInstanceLock(root) as lock:
        runner,adapter,journal,key=_runner(service,lock,ctx)
        with pytest.raises(Exception): runner.execute()  # never adopt unjournaled backup/candidate
        with runner.lease:
            recovered=journal.load(key)  # real HMAC with the same synthetic DMK after process death
        classification=classify_upgrade(recovered,expected_context=ctx,observed=(),registry=_registry(),
            inventory_complete=True,journal_authenticated=True)
        assert recovered.phase is UpgradePhase.RECOVERY_REQUIRED
        assert classification.status is UpgradeRecoveryStatus.RECOVERY_REQUIRED
        assert not classification.activation_allowed and not classification.normal_runtime_allowed
        assert _hash(service.paths.final_v4.database)==before


@pytest.mark.parametrize('boundary',['before_snapshot','during_main_database_snapshot',
    'during_document_inventory','after_verification_before_publication'])
def test_real_backup_pipeline_errors_never_authorize_staging(case,boundary):
    _,service,lock,ctx=case; before=_hash(service.paths.final_v4.database)
    def fault(value):
        if value==boundary: raise OSError(28,'synthetic ENOSPC')
    service._fault_hook=fault
    runner,adapter,_,_=_runner(service,lock,ctx)
    with pytest.raises(Exception): runner.execute()
    assert _hash(service.paths.final_v4.database)==before
    assert not adapter.backup_path.exists() and not adapter.candidate_path.exists()


def test_missing_snapshot_component_blocks_staging(case,monkeypatch):
    from contextlib import contextmanager
    _,service,lock,ctx=case; before=_hash(service.paths.final_v4.database)
    original=service.verified_snapshot
    @contextmanager
    def missing_component(path):
        with original(path) as snapshot:
            snapshot.companion_path.unlink()
            yield snapshot
    monkeypatch.setattr(service,'verified_snapshot',missing_component)
    runner,adapter,_,_=_runner(service,lock,ctx)
    with pytest.raises(Exception): runner.execute()
    assert _hash(service.paths.final_v4.database)==before
    assert not adapter.candidate_path.exists()


def test_external_target_path_is_rejected_before_io(case,tmp_path):
    _,service,lock,ctx=case; runner,adapter,_,_=_runner(service,lock,ctx)
    outside=tmp_path / 'outside.sqlcipher'; adapter.candidate_path=outside
    before=_hash(service.paths.final_v4.database)
    with pytest.raises(UpgradeError,match='artifact_path_invalid'): runner.execute()
    assert not outside.exists() and not runner.journal.path.exists()
    assert _hash(service.paths.final_v4.database)==before


def test_actual_snapshot_version_overrules_manifest_assertion(case,monkeypatch):
    from contextlib import contextmanager
    _,service,lock,ctx=case; before=_hash(service.paths.final_v4.database)
    original=service.verified_snapshot
    @contextmanager
    def changed_schema(path):
        with original(path) as snapshot:
            with service._provider.connect(snapshot.database_path,create=False,key_material=service.loaded.database_key.key_material) as connection:
                connection.execute('PRAGMA user_version=5'); connection.commit()
            yield snapshot
    monkeypatch.setattr(service,'verified_snapshot',changed_schema)
    runner,adapter,_,_=_runner(service,lock,ctx)
    with pytest.raises(Exception): runner.execute()
    assert _hash(service.paths.final_v4.database)==before and not adapter.candidate_path.exists()



def test_qualified_provider_keeps_stock_driver_and_metadata_unchanged():
    import sqlcipher3.dbapi2 as stock
    before=importlib.metadata.version('sqlcipher3')
    connection=stock.connect(':memory:')
    original=connection.execute('PRAGMA cipher_version').fetchone(); connection.close()
    provider=qualified_sqlcipher_test_provider()
    driver=provider._load_driver()
    with driver.connect(':memory:') as native:
        assert native.execute('PRAGMA cipher_version').fetchone()[0]=='4.17.0 community'
        assert native.execute('SELECT sqlite_version()').fetchone()[0]=='3.53.3'
    connection=stock.connect(':memory:')
    assert connection.execute('PRAGMA cipher_version').fetchone()==original; connection.close()
    assert importlib.metadata.version('sqlcipher3')==before


@pytest.mark.parametrize("rollback_candidate", [False, True])
def test_real_cipher_old_valid_journal_cannot_resume(case, rollback_candidate):
    _, service, lock, ctx = case
    runner, adapter, journal, key = _runner(service, lock, ctx)
    state = runner.execute()
    old = replace(state, phase=UpgradePhase.BACKUP_VERIFIED, revision=3,
                  evidence=state.evidence[:3])
    journal.path.write_bytes(journal._encode(old, key))  # genuinely valid old HMAC
    if rollback_candidate:
        # A prior valid encrypted candidate from this unchanged V4 source.
        with service.verified_snapshot(adapter.backup_path) as snapshot:
            adapter.candidate_path.write_bytes(snapshot.database_path.read_bytes())
    with pytest.raises(UpgradeError, match="generation_conflict"):
        runner.execute()


@pytest.mark.parametrize("missing", [None, "backup", "candidate"])
def test_isolated_guard_with_real_keyed_evidence(case, missing):
    from src.application.commands.upgrade_startup_guard import UpgradeStartupGuard
    _, service, lock, ctx = case
    runner, adapter, journal, key = _runner(service, lock, ctx)
    runner.execute()
    with UpgradeMaintenance(service._gate, journal.lease, ctx):
        source = adapter.verify_source()
        backup = adapter.verify_backup(source)
        candidate = adapter.verify_staging(source)
        observed = (source.artifact, backup, candidate)
        if missing:
            path = adapter.backup_path if missing == "backup" else adapter.candidate_path
            path.unlink()  # synthetic evidence loss
            with pytest.raises(Exception):
                adapter.verify_backup(source) if missing == "backup" else adapter.verify_staging(source)
        result = UpgradeStartupGuard(journal).evaluate(key, observed=observed,
            inventory_complete=missing is None, live_schema=ctx.source, restore_clear=True)
        assert result.status is (UpgradeRecoveryStatus.RECOVERY_REQUIRED if missing
                                 else UpgradeRecoveryStatus.VERIFY_CANDIDATE)
        assert not result.continue_existing_startup
        assert not result.first_run_allowed and not result.activation_allowed
