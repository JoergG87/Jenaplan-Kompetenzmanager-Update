"""Real encrypted product strategies; only synthetic roots and in-memory keys."""
from contextlib import closing
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import uuid
import pytest

from src.core.restore_runtime import RuntimeInstanceLock
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.security.product_v7 import (
    ProductV7Migration, ProductV7Runtime, ProductV7StartupGuard,
    ProductV7StartupInventory, build_product_v7_service, product_schema_identity,
    verify_product_v7_completion, TARGET, COMPLETION,
)
from tests.test_transactional_schema_migration import _seed_case, _inspection_service, _protected
from tests.test_timetable_consumers_v6 import _run_process
from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider


def service(paths, loaded, installation):
    return build_product_v7_service(paths.final_v4.root,
        authenticated_account=SimpleNamespace(installation_id=installation),
        loaded_keys=loaded, provider=qualified_sqlcipher_test_provider(), checkpointed_metadata_reads=True)


def migrate(directory, fail, channel):
    try:
        _, old = _seed_case(Path(directory))
        from src.desktop_app.runtime import prepare_security_runtime_storage
        from src.security.startup import build_security_runtime, finalize_security_runtime
        from tests.test_internal_test_v6_composition import _remove_technical_fixture_markers
        security_paths = prepare_security_runtime_storage(data_root=old.paths.final_v4.root)
        security = build_security_runtime(security_paths)
        security.service._installation_id_factory = lambda: old.installation_id
        security.service.enroll_local_account("Synthetische-Produkt-V7-Passphrase!")
        with RuntimeInstanceLock(old.paths.final_v4.root) as lock:
            finalize_security_runtime(security, security_paths, lock)
        _remove_technical_fixture_markers(old)
        old = build_product_v7_service(old.paths.final_v4.root,
            authenticated_account=security.repository.load_account(), loaded_keys=old.loaded,
            provider=qualified_sqlcipher_test_provider(), v4_source=True)
        protected = _protected(old)
        def fault(boundary):
            if boundary == fail:
                raise RuntimeError("interrupted product maintenance")
        migration = ProductV7Migration(old, fault_hook=fault)
        if fail:
            with pytest.raises(RuntimeError, match="interrupted product maintenance"):
                migration.execute()
        else:
            migration.execute()
        assert _protected(old) == protected
        channel.send(("ok", old.paths, old.loaded, old.installation_id))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()


def complete(paths, loaded, installation, channel):
    try:
        source = build_product_v7_service(paths.final_v4.root,
            authenticated_account=SimpleNamespace(installation_id=installation), loaded_keys=loaded,
            provider=qualified_sqlcipher_test_provider(), v4_source=True)
        ProductV7Migration(source).complete()
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally: channel.close()


def reopen(paths, loaded, installation, channel):
    try:
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        current = service(paths, loaded, installation)
        verify_product_v7_completion(current)
        with RuntimeInstanceLock(paths.final_v4.root) as lock:
            observed=ProductV7StartupInventory().inspect(paths.final_v4.root)
            assert observed.status.value not in {"unknown","unsafe"}, (observed.status,observed.reason,observed.unknown)
            ProductV7StartupGuard(lock, service_factory=lambda _: current).evaluate()
            with ProductV7Runtime(current).open_existing(lock=lock) as opened:
                adapter = TimetableDesktopAdapter(opened.database)
                adapter.configure_week_cycle(date(2026,10,26), "A")
                adapter.set_week_override(date(2026,11,2), "A")
                opened.lesson_time_templates.set_times(1, "08:00", "08:45")
                assert adapter.week_assignment(date(2026,11,2)).manual
                with closing(opened.database.connect()) as connection:
                    assert connection.execute("SELECT count(*) FROM observations").fetchone()[0] > 0
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally: channel.close()


@pytest.fixture
def migrated(tmp_path):
    _, paths, loaded, installation = _run_process(migrate, (str(tmp_path), None))
    _run_process(complete, (paths,loaded,installation))
    return paths,loaded,installation


def test_product_migration_completion_regular_write_and_restart(migrated):
    paths,loaded,installation=migrated
    _run_process(reopen,(paths,loaded,installation))
    _run_process(reopen,(paths,loaded,installation))


@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
def test_interruption_never_admits_uncompleted_runtime(tmp_path,boundary):
    _,paths,loaded,installation=_run_process(migrate,(str(tmp_path),boundary))
    current=service(paths,loaded,installation)
    assert not (paths.final_v4.root/COMPLETION).exists()
    assert product_schema_identity(current)==(TARGET if boundary=="after_commit" else FINAL_V4_SCHEMA_REGISTRATION.identity)
    with RuntimeInstanceLock(paths.final_v4.root) as lock:
        with pytest.raises(Exception): ProductV7StartupGuard(lock,service_factory=lambda _:current).evaluate()
    if boundary=="after_commit":
        _run_process(complete,(paths,loaded,installation))
        _run_process(reopen,(paths,loaded,installation))
    else:
        with pytest.raises(Exception): ProductV7Migration(_inspection_service(paths,loaded,installation)).complete()


def test_completion_tampering_is_rejected(migrated):
    import json
    paths,loaded,installation=migrated
    path=paths.final_v4.root/COMPLETION
    payload=json.loads(path.read_text());payload["installation_id"]=str(uuid.uuid4());path.write_text(json.dumps(payload));path.chmod(0o600)
    with pytest.raises(Exception): verify_product_v7_completion(service(paths,loaded,installation))


def test_product_v7_manifest_and_restore_contract_are_distinct(migrated,tmp_path):
    from src.security.product_v7 import ProductV7BackupManifest
    from src.security.product_v7_restore import ProductV7RestoreHandoffService, PRODUCT_V7_RESTORE_KIND
    from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupManifestV1
    paths,loaded,installation=migrated
    current=service(paths,loaded,installation)
    result=current.create(tmp_path/'product.jkmebackup')
    assert type(result.manifest) is ProductV7BackupManifest
    assert current.verify(result.path)==result
    with pytest.raises(Exception): SyntheticV7EncryptedBackupManifestV1.from_bytes(result.manifest.to_bytes())
    assert ProductV7RestoreHandoffService(current).restore_kind==PRODUCT_V7_RESTORE_KIND
    from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService
    from src.security.product_v7_restore import ProductV7LiveRestoreService
    synthetic=SyntheticV7EncryptedBackupService(opened_runtime=current.opened,paths=current.paths,
        loaded_keys=current.loaded,main_factory=current._main_factory,
        document_factory=current._document_factory,provider=current._provider,
        maintenance_gate=current._gate,random_source=current._random,clock=current._clock,
        checkpointed_metadata_reads=True)
    with pytest.raises(Exception): ProductV7LiveRestoreService(synthetic)


def existing_migrate(paths, loaded, installation, channel):
    try:
        from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
        account=ExistingStartupAccountRepository(paths.final_v4.root/'security/security.sqlite',None).load_bound_active_account()
        source=build_product_v7_service(paths.final_v4.root,authenticated_account=account,
            loaded_keys=loaded,provider=qualified_sqlcipher_test_provider(),v4_source=True)
        ProductV7Migration(source).execute()
        channel.send(('ok',))
    except BaseException:
        import traceback
        channel.send(('error',traceback.format_exc()))
    finally:channel.close()


def test_actual_product_main_v4_then_v7_authentication_and_adapters(tmp_path,monkeypatch):
    import gc
    from src.desktop_app import main
    from tests.test_product_upgrade_startup import product_main_ports, MemoryDataMasterKeyStore
    import src.security.product_v7 as product
    root=(tmp_path/'installation').resolve()
    store=MemoryDataMasterKeyStore()
    opened=product_main_ports(root,monkeypatch,store)
    assert main.main()==0
    gc.collect()
    assert main.main()==0
    gc.collect()
    old=opened[-1]
    source=build_product_v7_service(root,authenticated_account=SimpleNamespace(installation_id=old.installation_id),
        loaded_keys=old.runtime.final_v4.loaded_keys,provider=qualified_sqlcipher_test_provider(),v4_source=True)
    paths,loaded,installation=source.paths,source.loaded,source.installation_id
    _run_process(existing_migrate,(paths,loaded,installation))
    _run_process(complete,(paths,loaded,installation))
    real_builder=product.build_product_v7_service
    def builder(root,**kwargs):
        kwargs.setdefault('provider',qualified_sqlcipher_test_provider())
        kwargs.setdefault('key_store',store)
        return real_builder(root,**kwargs)
    monkeypatch.setattr(product,'build_product_v7_service',builder)
    import src.desktop_app.security_controller as controller
    import src.desktop_app.app as app_module
    from unittest.mock import MagicMock
    original_authenticate=controller.run_startup_authentication
    authenticated=[]
    def authenticate(**kwargs):
        result=kwargs['service'].authenticate_password("synthetische sichere Testpassphrase")
        assert result.status.value=='authenticated'
        authenticated.append(True)
        return original_authenticate(**kwargs)
    monkeypatch.setattr(controller,'run_startup_authentication',authenticate)
    windows=[]
    def window(*args,**kwargs):
        windows.append(kwargs)
        return MagicMock()
    monkeypatch.setattr(app_module,'JenaplanDesktopApp',window)
    before=dict(store.values)
    assert main.main()==0
    assert authenticated==[True]
    assert windows[-1]['lesson_time_templates_adapter'] is not None
    assert windows[-1]['backup_restore_available'] is True
    assert store.values==before
    (root/COMPLETION).write_text('{}')
    assert main.main()==3
    assert store.values==before


def restore_confirm(paths,loaded,installation,restore_id,token,channel):
    try:
        from src.security.product_v7_restore import confirm_product_v7_restore
        confirm_product_v7_restore(backup_service=service(paths,loaded,installation),
            runtime_root=paths.final_v4.root,restore_id=restore_id,token=token)
        channel.send(('ok',))
    except BaseException:
        import traceback
        channel.send(('error',traceback.format_exc()))
    finally:channel.close()


def restore_worker(paths,loaded,installation,handoff,nonce,channel):
    try:
        from src.security.product_v7_restore import ProductV7LiveRestoreService
        from src.desktop_app import restore_worker as worker
        import src.security.product_v7 as product
        current=service(paths,loaded,installation)
        # Only existing-key/provider composition ports are supplied from the
        # synthetic fixture. Execute the actual product worker dispatch/guard.
        real_guard=product.ProductV7StartupGuard
        class Guard(real_guard):
            def __init__(self,lock,**kwargs):
                super().__init__(lock,service_factory=lambda _:current,**kwargs)
        product.ProductV7StartupGuard=Guard
        class Restart:
            def launch(self,*,paths,token,lock):
                _run_process(restore_confirm,(current.paths,loaded,installation,paths.transaction.name,token))
                return True
        result=worker.run(['--restore-mode','final_v7_encrypted','--handoff',str(handoff),f'--nonce={nonce}'],
            encrypted_service_factory=lambda _:ProductV7LiveRestoreService(current,restart_launcher=Restart()))
        assert result==0,result
        channel.send(('ok',))
    except BaseException:
        import traceback
        channel.send(('error',traceback.format_exc()))
    finally:channel.close()


def test_product_worker_restore_and_confirm_preserve_complete_snapshot(migrated,tmp_path):
    from src.security.product_v7_restore import prepare_product_v7_restore
    from src.core.database_content_evidence import database_content_evidence
    from src.security.final_v4_live_restore import FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    paths,loaded,installation=migrated
    current=service(paths,loaded,installation)
    with closing(current._main_factory.connect(paths.final_v4.database)) as connection:
        before=database_content_evidence(connection)
    backup=current.create(tmp_path/'before.jkmebackup')
    restore_id=str(uuid.uuid4())
    parent=paths.final_v4.root/FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    parent.mkdir(mode=0o700)
    stage=current.restore_staging(backup.path,parent/restore_id)
    with RuntimeInstanceLock(paths.final_v4.root) as lock:
        prepared=prepare_product_v7_restore(backup_service=current,lock=lock,
            staging_root=stage.staging_root,expected_container_sha256=backup.container_sha256,
            restore_id=restore_id,app_version='0.4.4',build_commit='1f92f15'+'0'*33)
    prepared.safety_backup.transfer_to_worker()
    _run_process(restore_worker,(paths,loaded,installation,prepared.handoff.path,prepared.handoff.nonce))
    with closing(current._main_factory.connect(paths.final_v4.database)) as connection:
        assert database_content_evidence(connection)==before
    _run_process(reopen,(paths,loaded,installation))


@pytest.mark.parametrize("damage", ["foreign_schema", "missing_backup", "missing_completion"])
def test_invalid_product_v7_state_is_preserved_and_rejected(migrated,damage):
    paths,loaded,installation=migrated
    current=service(paths,loaded,installation)
    if damage=='foreign_schema':
        with closing(current._provider.connect(paths.final_v4.database,create=False,
                key_material=loaded.database_key.key_material)) as connection:
            connection.execute('CREATE TABLE foreign_schema(value TEXT)');connection.commit()
    elif damage=='missing_backup':
        (paths.final_v4.root/'schema-upgrade-source/transaction-timetable-weeks-v1/source.jkmebackup').unlink()
    else:
        (paths.final_v4.root/COMPLETION).unlink()
    before=paths.final_v4.database.read_bytes()
    with RuntimeInstanceLock(paths.final_v4.root) as lock:
        with pytest.raises(Exception): ProductV7StartupGuard(lock,service_factory=lambda _:current).evaluate()
    assert paths.final_v4.database.read_bytes()==before


def test_explicit_completion_entry_restarts_normal_product_app(tmp_path,monkeypatch):
    from src.desktop_app import main
    import src.desktop_app.product_v7_maintenance as maintenance
    _,paths,loaded,installation=_run_process(migrate,(str(tmp_path),None))
    def builder(root,**kwargs):
        return build_product_v7_service(root,
            authenticated_account=SimpleNamespace(installation_id=installation),loaded_keys=loaded,
            provider=qualified_sqlcipher_test_provider(),**kwargs)
    monkeypatch.setattr(maintenance,'build_product_v7_service',builder)
    starts=[]
    real_popen=maintenance.subprocess.Popen
    def launch(command,**kwargs):
        if '--runtime-root' in command:
            starts.append((command,kwargs));return SimpleNamespace()
        return real_popen(command,**kwargs)
    monkeypatch.setattr(maintenance.subprocess,'Popen',launch)
    monkeypatch.setattr(main.sys,'argv',['app','--complete-v7-migration','--runtime-root',str(paths.final_v4.root)])
    assert main.main()==0
    assert starts and starts[0][0][-2:]==['--runtime-root',str(paths.final_v4.root)]
    verify_product_v7_completion(service(paths,loaded,installation))


def test_explicit_migration_entry_uses_fresh_completion_process(tmp_path,monkeypatch):
    import src.desktop_app.product_v7_maintenance as maintenance
    # An intentionally interrupted pre-commit fixture is not silently reused:
    # create a fresh ordinary V4 product fixture through the actual main path.
    from tests.test_product_upgrade_startup import product_main_ports,MemoryDataMasterKeyStore
    from src.desktop_app import main
    import gc
    root=(tmp_path/'installation').resolve();store=MemoryDataMasterKeyStore()
    opened=product_main_ports(root,monkeypatch,store)
    assert main.main()==0
    gc.collect()
    assert main.main()==0
    gc.collect()
    current=opened[-1]
    def builder(root,**kwargs):
        return build_product_v7_service(root,authenticated_account=SimpleNamespace(installation_id=current.installation_id),
            loaded_keys=current.runtime.final_v4.loaded_keys,provider=qualified_sqlcipher_test_provider(),**kwargs)
    monkeypatch.setattr(maintenance,'build_product_v7_service',builder)
    commands=[]
    real_run=maintenance.subprocess.run
    def child(command,**kwargs):
        if '--complete-v7-migration' not in command:
            return real_run(command,**kwargs)
        commands.append(command)
        source=builder(root,v4_source=True)
        _run_process(complete,(source.paths,source.loaded,source.installation_id))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(maintenance.subprocess,'run',child)
    monkeypatch.setattr(main.sys,'argv',['app','--migrate-v4-to-v7','--runtime-root',str(root)])
    assert main.main()==0
    assert '--complete-v7-migration' in commands[0]


def test_unprotected_runtime_override_is_rejected_without_mutation(tmp_path,monkeypatch):
    from src.desktop_app import main
    root=tmp_path.resolve()
    before=set(root.iterdir())
    monkeypatch.setattr(main.sys,'argv',['app','--runtime-root',str(root)])
    assert main.main()==3
    assert set(root.iterdir())==before


def test_packaged_v7_write_and_snapshot_use_real_encrypted_product(migrated, capsys):
    import json
    from unittest.mock import MagicMock
    from src.desktop_app.main import _run_packaged_smoke
    from src.desktop_app.runtime import runtime_paths
    paths, loaded, installation = migrated
    current = service(paths, loaded, installation)
    with RuntimeInstanceLock(paths.final_v4.root) as lock:
        with ProductV7Runtime(current).open_existing(lock=lock) as runtime:
            opened = SimpleNamespace(runtime=runtime, database=runtime.database,
                documents=runtime.documents, first_run=False,
                database_context_id=loaded.database_context_id,
                database_key_fingerprint_sha256=loaded.database_key_fingerprint_sha256,
                dmk_fingerprint_sha256=loaded.dmk_fingerprint_sha256)
            window = MagicMock()
            window.adapter.current_school_year.return_value = None
            window.curriculum_adapter.list_entries.return_value = ()
            window.windowTitle.return_value = "synthetic"
            window.isVisible.return_value = False
            for mode in ("v7-write", "migration-snapshot"):
                assert _run_packaged_smoke(MagicMock(), window,
                    runtime_paths(paths.final_v4.root), mode=mode,
                    product_runtime=opened, security_runtime=None,
                    backup_application=None, restore_application=None,
                    login_authenticated=True) == 0
                result = json.loads(capsys.readouterr().out.splitlines()[-1])
                assert result["schema_version"] == 7
                assert dict((name, count) for name, count, digest in result["main_content"])["observations"] > 0
                assert result["managed_document_hashes"]
            assert opened.runtime.lesson_time_templates.suggest(1).start_time == "08:00"


def test_realistically_populated_product_source_migrates(tmp_path, monkeypatch):
    import gc
    from src.core.runtime_root_protection import prepare_synthetic_test_root
    from src.desktop_app import main
    from src.desktop_app.runtime import runtime_paths
    from src.security.startup import build_security_runtime, finalize_security_runtime
    from scripts.seed_test_data import seed_cipher_pilot_test_data
    from tests.test_product_upgrade_startup import product_main_ports, MemoryDataMasterKeyStore
    root = (tmp_path / "populated").resolve()
    prepare_synthetic_test_root(root)
    store = MemoryDataMasterKeyStore()
    opened = product_main_ports(root, monkeypatch, store)
    assert main.main() == 0
    gc.collect()
    assert main.main() == 0
    current = opened[-1]
    with RuntimeInstanceLock(root) as lock:
        seed_cipher_pilot_test_data(current, source_root=root)
        paths = runtime_paths(root)
        finalize_security_runtime(build_security_runtime(paths), paths, lock)
    loaded = current.runtime.final_v4.loaded_keys
    _run_process(maintenance_existing_keys, (str(root), store, False))
    _run_process(maintenance_existing_keys, (str(root), store, True))
    _run_process(reopen, (current.runtime.documents.paths, loaded, current.installation_id))


def maintenance_existing_keys(root, store, complete_phase, channel):
    try:
        source = build_product_v7_service(Path(root), key_store=store,
            provider=qualified_sqlcipher_test_provider(), v4_source=True)
        migration = ProductV7Migration(source)
        if complete_phase:
            migration.complete()
        else:
            migration.execute()
        channel.send(("ok",))
    except BaseException:
        import traceback
        channel.send(("error", traceback.format_exc()))
    finally:
        channel.close()


@pytest.mark.parametrize("diagnostic, expected", [
    ("product_v7_existing_keys_required", "product_v7_existing_keys_required"),
    ("private secret /Users/example", "product_v7_maintenance_failed"),
])
def test_maintenance_failure_prints_only_sanitized_code(monkeypatch, capsys, diagnostic, expected):
    from src.desktop_app import main
    import src.desktop_app.product_v7_maintenance as maintenance
    from src.core.schema_upgrade import UpgradeError
    def fail(*args, **kwargs):
        raise UpgradeError(diagnostic)
    monkeypatch.setattr(maintenance, "run_product_v7_maintenance", fail)
    monkeypatch.setattr(main.sys, "argv", ["app", "--migrate-v4-to-v7", "--runtime-root", "/synthetic"])
    assert main.main() == 3
    message = capsys.readouterr().err
    assert expected in message
    assert "private secret" not in message and "/Users/" not in message
