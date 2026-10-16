"""Real SQLCipher existing-only runtime in a fresh process after migration."""
from contextlib import closing
from dataclasses import replace
import multiprocessing
from pathlib import Path

import pytest

from src.core.lesson_times_schema import SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION as TARGET
from src.core.schema_registry import PRODUCT_SCHEMA_REGISTRY, FINAL_V4_SCHEMA_REGISTRATION
from src.security.synthetic_v5_runtime import SyntheticV5Runtime, SyntheticV5RuntimeError
from src.security.transactional_schema_migration import SyntheticTransactionalMigration
from tests.test_transactional_schema_migration import _seed_case, _inspection_service, _protected, _hash


def _lock_probe(root, channel):
    from src.core.restore_runtime import RuntimeInstanceLock, RestoreLockError
    try:
        with RuntimeInstanceLock(root):
            channel.send('acquired')
    except RestoreLockError:
        channel.send('blocked')
    finally:
        channel.close()


def _runtime_worker(paths, loaded, installation, channel, mode):
    try:
        service = _inspection_service(paths, loaded, installation)
        main = paths.final_v4.database
        key = loaded.database_key.key_material
        if mode in {"schema", "version", "domain", "foreign_key", "template", "crossbinding"}:
            with closing(service._provider.connect(main, create=False, key_material=key)) as c:
                if mode == "schema": c.execute("CREATE TABLE unknown(value TEXT)")
                if mode == "version": c.execute("PRAGMA user_version=6")
                if mode == "domain": c.execute("UPDATE timetable_entries SET subject_id='UNKNOWN'")
                if mode == "foreign_key":
                    c.execute("PRAGMA foreign_keys=OFF")
                    c.execute("UPDATE observations SET student_id='UNKNOWN'")
                if mode == "template":
                    c.execute("PRAGMA ignore_check_constraints=ON")
                    c.execute("INSERT INTO lesson_time_templates VALUES(1,'25:00','26:00')")
                if mode == "crossbinding": c.execute("UPDATE documents SET active=0")
                c.commit()
        if mode == "wrong_key":
            service.loaded = replace(loaded, database_key=replace(loaded.database_key, key_material=b"x" * 32))
        if mode == "wrong_installation": service.installation_id = "00000000-0000-4000-8000-000000000099"
        if mode == "missing_main": main.unlink()
        if mode == "missing_metadata": paths.final_v4.key_runtime.envelope_registry.unlink()
        if mode == "pending_restore": (paths.final_v4.root / 'restore-transactions').mkdir(mode=0o700)
        if mode == "unknown_upgrade":
            (paths.final_v4.root / 'schema-upgrade-source' / 'unknown').write_bytes(b'unknown')
        if mode == "sidecar": Path(str(main) + '-journal').write_bytes(b'unknown')
        before = _protected(service) if mode not in {"missing_metadata"} else None
        runtime = SyntheticV5Runtime(service)
        entered = False
        try:
            with runtime.open_existing() as opened:
                entered = True
                assert mode == 'valid', mode
                assert opened.identity == TARGET.identity and not opened.first_run
                assert opened.compatibility.cipher_provider == 'commoncrypto'
                opened.lesson_time_templates.set_times(1, '07:45', '08:30')
                assert opened.lesson_time_templates.suggest(1).start_time == '07:45'
                ctx = multiprocessing.get_context('spawn'); recv, send = ctx.Pipe()
                contender = ctx.Process(target=_lock_probe, args=(paths.final_v4.root, send))
                contender.start(); send.close()
                assert recv.poll(20) and recv.recv() == 'blocked'
                contender.join(10); assert contender.exitcode == 0
                recv.close()
                companion = runtime.document_factory.connect(create=False)
                late_document_method = opened.documents.prepare_bytes
                leaked = opened.database.connect()
                cursor = leaked.execute('SELECT student_id FROM students')
                with closing(opened.database.connect()) as c:
                    assert c.execute('SELECT COUNT(*) FROM observations').fetchone()[0] > 0
                    assert c.execute('SELECT COUNT(*) FROM learning_report_revisions').fetchone()[0] > 0
                assert _protected(service) == before
            with pytest.raises(SyntheticV5RuntimeError, match='used'):
                with runtime.open_existing(): pass
            for operation in (lambda: opened.documents.validate_restart(),
                    lambda: late_document_method(document_id='unused', plaintext=b'no'),
                    lambda: runtime.document_factory.connect(create=False)):
                with pytest.raises(SyntheticV5RuntimeError, match='closed'): operation()
            assert _protected(service) == before
            for operation in (lambda: leaked.execute('SELECT 1'), lambda: cursor.fetchone(), leaked.commit,
                    lambda: companion.execute('SELECT 1')):
                with pytest.raises(Exception): operation()
            with pytest.raises(SyntheticV5RuntimeError, match='closed'):
                opened.database.connect()
            channel.send(('ok',))
        except Exception as error:
            if mode == 'valid' or entered or isinstance(error, AssertionError): raise
            assert not main.exists() if mode == 'missing_main' else True
            assert _protected(service) == before if before is not None else True
            channel.send(('blocked', type(error).__name__))
    except BaseException as error:
        channel.send(('error', type(error).__name__, str(error)))
    finally:
        channel.close()


@pytest.mark.parametrize('mode', ['valid', 'schema', 'version', 'domain', 'foreign_key',
    'template', 'crossbinding', 'wrong_key', 'wrong_installation', 'missing_main',
    'missing_metadata', 'pending_restore', 'unknown_upgrade', 'sidecar'])
def test_existing_only_full_runtime(mode, tmp_path):
    _, service = _seed_case(tmp_path)
    SyntheticTransactionalMigration(service).execute()
    source = service.paths.final_v4.root / 'schema-upgrade-source/transaction-v1/source.jkmebackup'
    original = _hash(source)
    ctx = multiprocessing.get_context('spawn'); parent, child = ctx.Pipe()
    process = ctx.Process(target=_runtime_worker,
        args=(service.paths, service.loaded, service.installation_id, child, mode))
    process.start(); child.close()
    try:
        assert parent.poll(50), 'runtime worker did not report'
        result = parent.recv(); process.join(10)
        assert process.exitcode == 0 and result[0] == ('ok' if mode == 'valid' else 'blocked'), result
        assert _hash(source) == original
        assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
        assert not PRODUCT_SCHEMA_REGISTRY.upgrades
    finally:
        if process.is_alive(): process.kill(); process.join(10)
        parent.close()
