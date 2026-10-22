"""Source composition regressions using real qualified encrypted databases.

Only the outer sealed-package capability is substituted where explicitly noted.
These tests are not evidence of native package attestation or human UI acceptance.
"""
from contextlib import closing
from types import SimpleNamespace

import pytest

from src.core.restore_runtime import RuntimeInstanceLock, RestoreLockError
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION, PRODUCT_SCHEMA_REGISTRY
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
from src.security import internal_test_v6_composition as composition
from src.security.synthetic_v6_runtime import SyntheticV6Runtime, SyntheticV6RuntimeError
from tests.test_transactional_schema_migration import _seed_case, _protected, _hash
from tests.test_synthetic_v6_backup_restore import _migrate_fixture
from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider
from tests.test_encrypted_upgrade_source import _open_case
from tests.test_final_v4_sqlcipher_runtime import MemoryDataMasterKeyStore


def _source_capability(monkeypatch, service):
    """Substitute attestation only; retain real root/key/schema/lock validation."""
    root = service.paths.final_v4.root
    profile = SimpleNamespace(runtime_root=str(root), installation_id=service.installation_id)
    def require(candidate):
        assert candidate == root
        return profile
    monkeypatch.setattr(composition, "require_internal_test_v6_context", require)
    return profile


def _composed(monkeypatch, old, *, checkpointed_metadata_reads=False):
    _source_capability(monkeypatch, old)
    return composition.build_internal_test_v6_backup_service(old.paths.final_v4.root,
        authenticated_account=SimpleNamespace(installation_id=old.installation_id),
        loaded_keys=old.loaded, provider=qualified_sqlcipher_test_provider(),
        checkpointed_metadata_reads=checkpointed_metadata_reads)


def _remove_technical_fixture_markers(service):
    import gc
    import sqlite3
    from pathlib import Path
    # These authorize the legacy low-level fixture builders, not app startup.
    for name in (".jkm-dmk-database-key-runtime-test-root",
            ".jkm-final-v4-sqlcipher-runtime-test-root"):
        (service.paths.final_v4.root / name).unlink()
    # Model the normal completed technical setup, not its live builder's WAL.
    gc.collect()
    metadata = service.paths.final_v4.key_runtime.keyset_metadata
    with closing(sqlite3.connect(metadata)) as connection:
        assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
    for suffix in ("-wal", "-shm"):
        Path(str(metadata) + suffix).unlink(missing_ok=True)


def test_unsealed_source_context_is_never_a_v6_capability(tmp_path):
    _, old = _seed_case(tmp_path)
    before = _protected(old), _hash(old.paths.final_v4.database)
    with pytest.raises(SyntheticV6RuntimeError, match="sealed_context_required"):
        composition.build_internal_test_v6_backup_service(old.paths.final_v4.root,
            authenticated_account=SimpleNamespace(installation_id=old.installation_id),
            loaded_keys=old.loaded, provider=qualified_sqlcipher_test_provider())
    assert (_protected(old), _hash(old.paths.final_v4.database)) == before


def test_existing_v4_and_migrated_v6_have_exact_distinct_dispatch(monkeypatch, tmp_path):
    _, old = _seed_case(tmp_path)
    service = _composed(monkeypatch, old)
    assert composition.internal_test_schema_identity(service) == FINAL_V4_SCHEMA_REGISTRATION.identity
    _migrate_fixture(old)  # Real migration in fresh process, no gate reset.
    assert composition.internal_test_schema_identity(service) == SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity
    assert PRODUCT_SCHEMA_REGISTRY.schemas == (FINAL_V4_SCHEMA_REGISTRATION,)
    assert not PRODUCT_SCHEMA_REGISTRY.upgrades


@pytest.mark.parametrize("damage", ["unknown", "corrupt", "missing"])
def test_schema_dispatch_never_falls_back_to_v4_or_recreates_main(monkeypatch, tmp_path, damage):
    _, old = _seed_case(tmp_path)
    service = _composed(monkeypatch, old)
    main = old.paths.final_v4.database
    if damage == "unknown":
        with closing(service._provider.connect(main, create=False,
                key_material=old.loaded.database_key.key_material)) as connection:
            connection.execute("CREATE TABLE foreign_identity(value TEXT)")
            connection.commit()
    elif damage == "corrupt":
        main.write_bytes(b"synthetic damaged encrypted database")
    else:
        main.unlink()
    before = main.read_bytes() if main.exists() else None
    with pytest.raises(Exception):
        composition.internal_test_schema_identity(service)
    assert (main.read_bytes() if main.exists() else None) == before


@pytest.mark.parametrize("damage", [None, "template", "missing_template", "document_binding", "missing_main"])
def test_borrowed_runtime_lock_retains_owner_on_success_and_failure(monkeypatch, tmp_path, damage):
    _, old = _seed_case(tmp_path)
    _migrate_fixture(old)
    service = _composed(monkeypatch, old)
    main = service.paths.final_v4.database
    if damage in {"template", "missing_template", "document_binding"}:
        with closing(service._provider.connect(main, create=False,
                key_material=old.loaded.database_key.key_material)) as connection:
            if damage == "template":
                connection.execute("PRAGMA ignore_check_constraints=ON")
                connection.execute("INSERT INTO lesson_time_templates VALUES(1,'25:00','26:00')")
            elif damage == "missing_template":
                connection.execute("DROP TABLE lesson_time_templates")
            else:
                connection.execute("UPDATE documents SET active=0")
            connection.commit()
    elif damage == "missing_main":
        main.unlink()
    protected = _protected(service)
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        generation, descriptor = lock.authority_generation, lock.fileno
        if damage is None:
            with SyntheticV6Runtime(service).open_existing(lock=lock) as opened:
                assert opened.identity == SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity
                assert opened.compatibility.cipher_provider == "commoncrypto"
                assert opened.lesson_time_templates.repository.list_templates() == ()
        else:
            with pytest.raises(Exception):
                with SyntheticV6Runtime(service).open_existing(lock=lock):
                    pytest.fail("Invalid source acquired a target runtime")
        assert lock.authority_generation == generation and lock.fileno == descriptor
        # A second real flock still fails after the borrowed scope ends.
        with pytest.raises(RestoreLockError):
            RuntimeInstanceLock(service.paths.final_v4.root).acquire()
    with pytest.raises(RestoreLockError):
        _ = lock.fileno
    assert _protected(service) == protected
    if damage == "missing_main":
        assert not main.exists()


def test_bootstrap_requires_authenticated_matching_installation(monkeypatch, tmp_path):
    _, old = _seed_case(tmp_path)
    _source_capability(monkeypatch, old)
    with pytest.raises(SyntheticV6RuntimeError, match="installation_mismatch"):
        composition.build_internal_test_v6_backup_service(old.paths.final_v4.root,
            authenticated_account=SimpleNamespace(installation_id="foreign-installation"),
            loaded_keys=old.loaded, provider=qualified_sqlcipher_test_provider())


def test_inherited_lock_is_borrowed_without_release(monkeypatch, tmp_path):
    import os
    _, old = _seed_case(tmp_path)
    _migrate_fixture(old)
    service = _composed(monkeypatch, old)
    with RuntimeInstanceLock(service.paths.final_v4.root) as parent:
        inherited = RuntimeInstanceLock(service.paths.final_v4.root,
            inherited_fd=os.dup(parent.fileno)).acquire()
        try:
            descriptor, generation = inherited.fileno, inherited.authority_generation
            with SyntheticV6Runtime(service).open_existing(lock=inherited) as opened:
                assert opened.identity == SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity
            assert inherited.fileno == descriptor and inherited.authority_generation == generation
            with pytest.raises(RestoreLockError):
                RuntimeInstanceLock(service.paths.final_v4.root).acquire()
        finally:
            inherited.release()


@pytest.mark.parametrize("missing", [False, True])
def test_existing_key_loader_never_creates_replacement_keys(monkeypatch, tmp_path, missing):
    _, old, store, _, account_loader, provider = _open_case(tmp_path)
    _remove_technical_fixture_markers(old)
    _source_capability(monkeypatch, old)
    before = _protected(old)
    creates = store.create_calls
    if missing:
        store.values.clear()
        with pytest.raises(SyntheticV6RuntimeError, match="existing_keys_unavailable"):
            composition.build_internal_test_v6_backup_service(old.paths.final_v4.root,
                authenticated_account=account_loader(), key_store=store, provider=provider)
    else:
        result = composition.ExistingInstallationKeys(key_store=store,
            inventory=composition.ProductStartupInventory()).load_existing(
                old.paths.final_v4.root, authenticated_account=account_loader())
        assert result.status is composition.ExistingInstallationKeyStatus.VALID, (
            result.status, composition.ProductStartupInventory().inspect(old.paths.final_v4.root))
        actual = composition.build_internal_test_v6_backup_service(old.paths.final_v4.root,
            authenticated_account=account_loader(), key_store=store, provider=provider)
        assert actual.loaded == old.loaded
        assert composition.internal_test_schema_identity(actual) == FINAL_V4_SCHEMA_REGISTRATION.identity
    assert store.create_calls == creates
    assert _protected(old) == before


@pytest.mark.parametrize("damage", [None, "source_corrupt", "unknown_upgrade", "main_missing"])
def test_internal_startup_guard_authenticates_retained_sources(monkeypatch, tmp_path, damage):
    import gc
    import sqlite3
    from pathlib import Path
    from src.desktop_app.runtime import prepare_security_runtime_storage
    from src.security import startup
    from src.security.upgrade_startup import UpgradeStartupBlocked

    _, old = _seed_case(tmp_path)
    _migrate_fixture(old)
    _remove_technical_fixture_markers(old)
    profile = _source_capability(monkeypatch, old)
    # Source-only substitute for the same profile read used during enrollment.
    monkeypatch.setattr(startup, "test_identity", lambda: profile)
    paths = prepare_security_runtime_storage(data_root=old.paths.final_v4.root)
    security = startup.build_security_runtime(paths)
    security.service.enroll_local_account("Synthetische Startup-Pruefung ohne Produktdaten")
    account = security.repository.load_account()
    assert account.installation_id == old.installation_id
    gc.collect()
    with closing(sqlite3.connect(paths.security_database)) as connection:
        assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
    for suffix in ("-wal", "-shm"):
        Path(str(paths.security_database) + suffix).unlink(missing_ok=True)
    store = MemoryDataMasterKeyStore()
    store.values[(old.installation_id, old.loaded.dmk_key_id)] = old.loaded.dmk.key_material
    original_builder = composition.build_internal_test_v6_backup_service
    def with_existing_test_store(root):
        return original_builder(root, key_store=store, provider=qualified_sqlcipher_test_provider())
    monkeypatch.setattr(composition, "build_internal_test_v6_backup_service", with_existing_test_store)
    root = old.paths.final_v4.root
    source = root / "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup"
    if damage == "source_corrupt":
        source.write_bytes(b"invalid synthetic historical encrypted backup")
    elif damage == "unknown_upgrade":
        (source.parent / "unknown-evidence").write_bytes(b"unknown")
        (source.parent / "unknown-evidence").chmod(0o600)
    elif damage == "main_missing":
        old.paths.final_v4.database.unlink()
    inventory = composition.InternalTestStartupInventory()
    before = inventory.before_lock(root)
    protected = _protected(old)
    with RuntimeInstanceLock(root) as lock:
        guard = composition.InternalTestStartupGuard(lock, inventory=inventory)
        if damage is None:
            assert guard.evaluate(before=before).reason == "upgrade_absent"
        else:
            with pytest.raises((SyntheticV6RuntimeError, UpgradeStartupBlocked)):
                guard.evaluate(before=before)
        assert lock.fileno >= 0
    assert _protected(old) == protected and store.create_calls == 0


def test_authenticated_wrapper_injects_real_template_adapter_into_desktop_app(monkeypatch, tmp_path):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTime
    from src.desktop_app.app import JenaplanDesktopApp
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.adapters.lesson_time_templates_desktop_adapter import LessonTimeTemplatesDesktopAdapter
    from src.desktop_app.runtime import runtime_paths
    from src.security import cipher_product_runtime as product

    from tests.helpers import synthetic_v4
    # Seed the actual required year and its references, rather than bypassing
    # the completed fachlicher-first-run validation in the real wrapper.
    monkeypatch.setattr(synthetic_v4, "SYNTHETIC_SCHOOL_YEAR_ID", product.PILOT_FIRST_RUN_SCHOOL_YEAR_ID)
    _, old = _seed_case(tmp_path)
    _migrate_fixture(old)
    service = _composed(monkeypatch, old)
    app = QApplication.instance() or QApplication([])
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        with composition.open_internal_test_v6_runtime(service, lock=lock) as opened:
            assert not opened.first_run and opened.installation_id == old.installation_id
            templates = LessonTimeTemplatesDesktopAdapter(opened.runtime)
            students = StudentDesktopAdapter(database=opened.runtime.database,
                database_create_allowed=False, managed_document_store=opened.runtime.documents)
            window = JenaplanDesktopApp(student_adapter=students,
                paths=runtime_paths(service.paths.final_v4.root), backup_restore_available=False,
                lesson_time_templates_adapter=templates)
            window.show()
            app.processEvents()
            assert window.lesson_time_templates_adapter is templates
            assert window.timetable_adapter.week_view_model().supports_extended_entries
            editor = window.settings_screen.lesson_time_templates_editor
            editor.start_time.setTime(QTime(7, 45))
            editor.end_time.setTime(QTime(8, 30))
            editor.save_button.click()
            app.processEvents()
            assert templates.view_model().templates[0].start_time == "07:45"
            window.close()
            app.processEvents()
        assert lock.fileno >= 0
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        with composition.open_internal_test_v6_runtime(service, lock=lock) as reopened:
            assert reopened.runtime.lesson_time_templates.suggest(1).start_time == "07:45"


@pytest.mark.parametrize("damage", [None, "main", "companion", "history", "binding", "schema"])
def test_pre_auth_existing_v6_validation_preserves_every_file_and_borrowed_lock(monkeypatch, tmp_path, damage):
    import hashlib
    _, old = _seed_case(tmp_path)
    _migrate_fixture(old)
    _remove_technical_fixture_markers(old)
    service = _composed(monkeypatch, old, checkpointed_metadata_reads=True)
    monkeypatch.setattr(composition, "build_internal_test_v6_backup_service", lambda *args, **kwargs: service)
    root = service.paths.final_v4.root
    if damage == "main":
        service.paths.final_v4.database.write_bytes(b"corrupt encrypted main")
    elif damage == "companion":
        service.paths.database.write_bytes(b"corrupt encrypted companion")
    elif damage == "history":
        (root / "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup").write_bytes(b"corrupt")
    elif damage in {"binding", "schema"}:
        with closing(service._provider.connect(service.paths.final_v4.database, create=False,
                key_material=service.loaded.database_key.key_material)) as connection:
            connection.execute("UPDATE documents SET active=0" if damage == "binding" else "PRAGMA user_version=99")
            connection.commit()
    def snapshot():
        return {str(p.relative_to(root)): (p.stat().st_mode, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in root.rglob("*") if p.is_file() and p.name != "instance.lock"}
    before = snapshot()
    with RuntimeInstanceLock(root) as lock:
        descriptor = lock.fileno
        if damage is None:
            composition.preflight_internal_test_existing_runtime(root, lock=lock)
        else:
            with pytest.raises(SyntheticV6RuntimeError, match="full_inspection_failed"):
                composition.preflight_internal_test_existing_runtime(root, lock=lock)
        assert lock.fileno == descriptor
        with pytest.raises(RestoreLockError):
            RuntimeInstanceLock(root).acquire()
    assert snapshot() == before


@pytest.mark.parametrize("sidecar", [None, "-wal", "-shm", "-journal"])
def test_pre_auth_checkpointed_wal_metadata_never_creates_or_ignores_sidecars(monkeypatch, tmp_path, sidecar):
    import sqlite3
    import hashlib
    from pathlib import Path
    _, old = _seed_case(tmp_path)
    _migrate_fixture(old)
    _remove_technical_fixture_markers(old)
    metadata = old.paths.final_v4.key_runtime.keyset_metadata
    with closing(sqlite3.connect(metadata)) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
    assert metadata.read_bytes()[18:20] == bytes((2, 2))
    assert all(not Path(str(metadata) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))
    service = _composed(monkeypatch, old, checkpointed_metadata_reads=True)
    monkeypatch.setattr(composition, "build_internal_test_v6_backup_service", lambda *args, **kwargs: service)
    if sidecar:
        Path(str(metadata) + sidecar).write_bytes(b"unresolved sidecar must never be ignored")
    root = service.paths.final_v4.root
    def snapshot():
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and p.name != "instance.lock"}
    before = snapshot()
    with RuntimeInstanceLock(root) as lock:
        if sidecar:
            with pytest.raises(SyntheticV6RuntimeError, match="full_inspection_failed"):
                composition.preflight_internal_test_existing_runtime(root, lock=lock)
        else:
            composition.preflight_internal_test_existing_runtime(root, lock=lock)
    assert snapshot() == before
