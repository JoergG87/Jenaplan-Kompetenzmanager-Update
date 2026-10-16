"""Exercise native-runner dialog ports with real SQLCipher before packaging.

The sealed outer capability alone is substituted. This is source/offscreen
verification, never a claim of native package or human acceptance.
"""
from types import SimpleNamespace
from pathlib import Path
from PySide6.QtWidgets import QApplication as RealApplication
from src.desktop_app.theme import apply_app_theme as real_theme
from tests.test_retained_operation_startup import regular_case


def test_real_dialog_ports_and_persisted_reopen(regular_case, monkeypatch):
    from PySide6 import QtWidgets
    import src.desktop_app.theme as theme
    from src.security import internal_test_v6_composition as composition
    from src.security.final_v4_backup_runtime import build_final_v4_encrypted_backup_service
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    from src.security.startup import build_security_runtime, finalize_security_runtime
    from src.desktop_app.runtime import runtime_paths
    from src.core.restore_runtime import RuntimeInstanceLock
    from tests.test_synthetic_v6_backup_restore import _migrate_fixture, _service
    from scripts.macos_native_v6_acceptance import _functions
    case = regular_case
    account = ExistingStartupAccountRepository(case.root / "security/security.sqlite", None).load_bound_active_account()
    old = build_final_v4_encrypted_backup_service(opened_runtime=case.runtime.runtime,
        account_loader=lambda: account, environ={}, product_paths=runtime_paths(case.root))
    with RuntimeInstanceLock(case.root) as lock:
        finalize_security_runtime(build_security_runtime(runtime_paths(case.root)), runtime_paths(case.root), lock)
    _migrate_fixture(old)
    profile = SimpleNamespace(runtime_root=str(case.root), installation_id=account.installation_id)
    monkeypatch.setattr(composition, "require_internal_test_v6_context", lambda root: profile)
    monkeypatch.setattr(composition, "build_internal_test_v6_backup_service", lambda *a, **k:
        _service(old.paths, old.loaded, old.installation_id))
    monkeypatch.setattr(QtWidgets, "QApplication", RealApplication)
    monkeypatch.setattr(theme, "apply_app_theme", real_theme)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = RealApplication.instance() or RealApplication([])
    result = _functions(profile)
    assert result["status"] == "ok" and not result["manual_ui_performed"]
    assert _functions(profile, reopen=True)["fresh_process_persistence"]


def test_v6_handoff_finishes_metadata_before_signing_and_worker_key_load(regular_case):
    from src.application.commands.synthetic_v6_backup_restore import SyntheticV6EncryptedRestoreApplicationService
    from src.application.commands.restore import VerifyRestoreBackupQuery, CreateRestoreHandoffCommand
    from src.security.final_v4_backup_runtime import build_final_v4_encrypted_backup_service
    from src.security.synthetic_v6_live_restore import SyntheticV6EncryptedRestoreHandoffService
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    from src.security.existing_installation_keys import ExistingInstallationKeys, ExistingInstallationKeyStatus
    from src.security.upgrade_startup import ProductStartupInventory
    from src.security.startup import build_security_runtime, finalize_security_runtime
    from src.desktop_app.runtime import runtime_paths
    from src.core.restore_runtime import RuntimeInstanceLock
    from tests.test_synthetic_v6_backup_restore import _migrate_fixture, _service
    case = regular_case
    paths = runtime_paths(case.root)
    account = ExistingStartupAccountRepository(case.root / "security/security.sqlite", None).load_bound_active_account()
    old = build_final_v4_encrypted_backup_service(opened_runtime=case.runtime.runtime,
        account_loader=lambda: account, environ={}, product_paths=paths)
    with RuntimeInstanceLock(case.root) as lock:
        finalize_security_runtime(build_security_runtime(paths), paths, lock)
    _migrate_fixture(old)
    service = _service(old.paths, old.loaded, old.installation_id)
    calls = []
    with RuntimeInstanceLock(case.root) as lock:
        def finalize():
            calls.append(Path(str(paths.keyset_metadata) + "-wal").exists())
            finalize_security_runtime(build_security_runtime(paths), paths, lock)
        finalize()
        backup = service.create(case.tmp / "v6-parent-target.jkmebackup")
        application = SyntheticV6EncryptedRestoreApplicationService(service,
            lock=lock, worker_launcher=None, before_handoff=finalize)
        ready = application.verify(VerifyRestoreBackupQuery(backup.path))
        handoff = application.create_handoff(CreateRestoreHandoffCommand(
            backup.path, ready.restore_id, paths, "0.4.4", "a" * 40, "dirty"))
        assert len(calls) == 3 and calls[-1], "Safety backup must precede final metadata closure"
        for database in (paths.security_database, paths.keyset_metadata):
            assert not any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm"))
        existing_account = ExistingStartupAccountRepository(case.root / "security/security.sqlite", None).load_bound_active_account()
        loaded = ExistingInstallationKeys(key_store=case.store,
            inventory=ProductStartupInventory()).load_existing(case.root,
                authenticated_account=existing_account)
        assert loaded.status is ExistingInstallationKeyStatus.VALID
        # Authenticated consume rechecks excluded security bytes: a checkpoint
        # after signing would invalidate this evidence if it changed them.
        SyntheticV6EncryptedRestoreHandoffService(service).consume(
            handoff.path, expected_nonce=handoff.nonce)
