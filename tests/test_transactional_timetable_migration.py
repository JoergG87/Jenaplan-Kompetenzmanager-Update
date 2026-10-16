"""Real qualified SQLCipher normalized migration and commit failure boundaries."""
from contextlib import closing
import multiprocessing
from pathlib import Path
import signal
import os
import pytest
from src.core.database_content_evidence import database_content_evidence
from src.core.database_compatibility import DatabaseCompatibilityInspector, DatabaseCompatibilityPolicy
from src.core.lesson_times_schema import SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION, LESSON_TIME_TEMPLATE_STATEMENT
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION, PRODUCT_SCHEMA_REGISTRY
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION as TARGET, SYNTHETIC_TIMETABLE_REGISTRY
from src.security.transactional_timetable_migration import SyntheticTimetableMigration
from src.security.synthetic_v5_backup_runtime import SyntheticV5EncryptedBackupService
from tests.test_transactional_schema_migration import _seed_case, _inspection_service, _protected


def _v5_service(service):
    return SyntheticV5EncryptedBackupService(opened_runtime=service.opened,
        paths=service.paths, loaded_keys=service.loaded, main_factory=service._main_factory,
        document_factory=service._document_factory, provider=service._provider,
        maintenance_gate=service._gate, random_source=service._random, clock=service._clock,
        installation_id=service.installation_id)


def _service_case(path, source):
    runtime, service = _seed_case(path)
    with runtime.final_v4.database.connect() as c:
        c.execute("""INSERT INTO timetable_entries VALUES
            ('TTE-INACTIVE',5,'13:10','14:05','SUB-TEST-DE','group','GRP-TEST-A',
             'Raum historisch',0,17,'2024-01-02T03:04:05','2024-02-03T04:05:06','2024-02-03T04:05:06')""")
        c.commit()
    if source == 5:
        with runtime.final_v4.database.connect() as c:
            c.execute(LESSON_TIME_TEMPLATE_STATEMENT)
            c.execute("INSERT INTO lesson_time_templates VALUES (1,'08:00','08:45')")
            c.execute("PRAGMA user_version=5")
            c.commit()
        service = _v5_service(service)
    return runtime, service


def _restart_worker(paths, loaded, installation_id, source, channel):
    try:
        service = _inspection_service(paths, loaded, installation_id)
        if source == 5:
            service = _v5_service(service)
        identity = SyntheticTimetableMigration(service).inspect_restart()
        channel.send(('ok', identity))
    except BaseException as error:
        channel.send(('error', type(error).__name__, str(error)))
    finally:
        channel.close()


def _restart(service, source):
    ctx=multiprocessing.get_context('spawn'); parent, child=ctx.Pipe()
    process=ctx.Process(target=_restart_worker,args=(service.paths,service.loaded,service.installation_id,source,child))
    process.start(); child.close()
    try:
        assert parent.poll(45)
        result=parent.recv(); process.join(10)
        assert process.exitcode == 0
        assert result[0] == 'ok', result
        return result[1]
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()


@pytest.mark.parametrize('source',[4,5])
def test_both_exact_sources_preserve_history_and_native_keyed_restart(tmp_path, source):
    runtime,service=_service_case(tmp_path,source)
    protected=_protected(service)
    m=SyntheticTimetableMigration(service)
    assert m.execute() == TARGET.identity
    assert _restart(service,source) == TARGET.identity
    assert _protected(service) == protected
    assert not m.main.read_bytes().startswith(b'SQLite format 3')
    assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
    assert not PRODUCT_SCHEMA_REGISTRY.upgrades
    assert len(SYNTHETIC_TIMETABLE_REGISTRY.upgrades) == 2


@pytest.mark.parametrize('boundary', ['parent_created','parent_copied','parent_dropped','subjects_copied','before_commit','after_commit'])
@pytest.mark.parametrize('source',[4,5])
def test_native_transaction_errors_leave_exact_old_or_new(tmp_path, source, boundary):
    _,service=_service_case(tmp_path,source)
    m=SyntheticTimetableMigration(service)
    def fail(value):
        if value == boundary: raise RuntimeError('synthetic interruption')
    m._fault_hook=fail
    with pytest.raises(RuntimeError,match='synthetic interruption'): m.execute()
    expected = TARGET.identity if boundary == 'after_commit' else (
        FINAL_V4_SCHEMA_REGISTRATION.identity if source==4 else SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity)
    assert _restart(service,source) == expected


def _crash_worker(directory, source, boundary, channel):
    try:
        _,service=_service_case(Path(directory),source)
        m=SyntheticTimetableMigration(service)
        channel.send(('ready',service.paths,service.loaded,service.installation_id,_protected(service)))
        from tests.helpers.sqlcipher_commit_probe import SQLCipherCommitProbe
        probe=SQLCipherCommitProbe(service._provider,m.main,channel,boundary) if boundary.startswith('vfs_') else None
        def pause(value):
            if probe is not None and value=='before_commit': probe.armed=True
            if value==boundary:
                channel.send((boundary,)); signal.pause()
        m._fault_hook=pause
        m.execute(); channel.send(('unexpected_completion',))
    except BaseException as error:
        channel.send(('error',type(error).__name__,str(error)))


@pytest.mark.parametrize('source',[4,5])
@pytest.mark.parametrize('boundary',['parent_created','parent_copied','parent_dropped','subjects_copied',
    'before_commit','vfs_before_journal_delete','vfs_after_journal_delete','after_commit'])
def test_real_sigkill_rebuild_and_native_commit(tmp_path,source,boundary):
    ctx=multiprocessing.get_context('spawn'); parent,child=ctx.Pipe()
    process=ctx.Process(target=_crash_worker,args=(str(tmp_path.resolve()),source,boundary,child))
    process.start(); child.close()
    try:
        assert parent.poll(50); ready=parent.recv(); assert ready[0]=='ready',ready
        _,paths,loaded,installation,protected=ready
        assert parent.poll(50); reached=parent.recv(); assert reached[0]==boundary,reached
        journal=Path(str(paths.final_v4.database)+'-journal')
        if boundary=='vfs_before_journal_delete':
            assert journal.exists() and journal.stat().st_size>512 and reached[1]==1
            assert not journal.read_bytes().startswith(b'SQLite format 3')
        if boundary=='vfs_after_journal_delete': assert not journal.exists() and reached[2]==0
        os.kill(process.pid,signal.SIGKILL); process.join(10)
        assert process.exitcode == -signal.SIGKILL
        service=_inspection_service(paths,loaded,installation)
        old=FINAL_V4_SCHEMA_REGISTRATION.identity if source==4 else SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity
        expected=TARGET.identity if boundary in {'vfs_after_journal_delete','after_commit'} else old
        assert _restart(service,source)==expected
        assert _protected(service)==protected
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()


@pytest.mark.parametrize('invalid_sql',[
    "UPDATE timetable_entries SET subject_id='missing'",
    "UPDATE timetable_entries SET target_id='missing'",
    "UPDATE timetable_entries SET timetable_entry_id=NULL",
    "UPDATE timetable_entries SET start_time='11:00'",
])
def test_invalid_source_refuses_before_backup_or_ddl(tmp_path,invalid_sql):
    runtime,service=_service_case(tmp_path,4)
    with runtime.final_v4.database.connect() as c:
        c.execute(invalid_sql); c.commit()
    before=service.paths.final_v4.database.read_bytes()
    m=SyntheticTimetableMigration(service)
    from src.core.schema_upgrade import UpgradeError
    with pytest.raises(UpgradeError): m.execute()
    assert m.main.read_bytes()==before and not m.backup.exists()


def _old_v5_source_worker(directory,channel):
    try:
        from src.security.transactional_schema_migration import SyntheticTransactionalMigration
        _,service=_seed_case(Path(directory))
        SyntheticTransactionalMigration(service).execute()
        channel.send(('ok',service.paths,service.loaded,service.installation_id))
    except BaseException as error:
        channel.send(('error',type(error).__name__,str(error)))


def test_old_migrated_v5_retains_independently_verified_v4_source_backup(tmp_path):
    ctx=multiprocessing.get_context('spawn'); recv,send=ctx.Pipe()
    process=ctx.Process(target=_old_v5_source_worker,args=(str(tmp_path.resolve()),send))
    process.start(); send.close()
    assert recv.poll(45); result=recv.recv(); process.join(10)
    assert process.exitcode==0 and result[0]=='ok',result
    _,paths,loaded,installation=result
    service=_inspection_service(paths,loaded,installation)
    service=_v5_service(service)
    from types import SimpleNamespace
    service._main_factory=SimpleNamespace(connect=lambda path,create=False:
        service._provider.connect(path,create=create,key_material=loaded.database_key.key_material))
    from src.security.final_v3_document_runtime import FinalV3DocumentRuntime
    from types import SimpleNamespace
    documents=FinalV3DocumentRuntime(paths=service.paths,factory=service._document_factory,
        loaded_keys=service.loaded,installation_id=installation,source_root=None,
        random_source=service._random,clock=service._clock)
    service.opened=SimpleNamespace(documents=documents,installation_id=installation,
        database_context_id=loaded.database_context_id, final_v4=SimpleNamespace(compatibility=None))
    old_backup=paths.final_v4.root/'schema-upgrade-source/transaction-v1/source.jkmebackup'
    before=old_backup.read_bytes()
    assert SyntheticTimetableMigration(service).execute()==TARGET.identity
    assert old_backup.read_bytes()==before
    assert _restart(service,5)==TARGET.identity


def test_independent_target_overlap_uses_parsed_legacy_time_semantics(tmp_path):
    runtime,service=_service_case(tmp_path,4)
    m=SyntheticTimetableMigration(service)
    with runtime.final_v4.database.connect() as c:
        c.execute("UPDATE timetable_entries SET start_time='0900', end_time='10:00:00' WHERE active=1")
        m._apply_schema(c)
        from src.core.upgrade_validation import verify_timetable_target_references
        verify_timetable_target_references(c)
        c.execute("""UPDATE timetable_entries SET active=1, weekday=1,
            start_time='09:30', end_time='10:30' WHERE timetable_entry_id='TTE-INACTIVE'""")
        from src.core.schema_upgrade import UpgradeError
        with pytest.raises(UpgradeError): verify_timetable_target_references(c)


@pytest.mark.parametrize('subject',['selbst_sozialkompetenz','arbeits_lernkompetenz'])
def test_development_domains_are_not_instructional_subjects(tmp_path,subject):
    runtime,service=_service_case(tmp_path,4)
    with runtime.final_v4.database.connect() as c:
        c.execute("UPDATE competencies SET subject_id=?",(subject,))
        c.execute("UPDATE timetable_entries SET subject_id=?",(subject,))
        c.commit()
    from src.core.schema_upgrade import UpgradeError
    with pytest.raises(UpgradeError): SyntheticTimetableMigration(service).execute()
