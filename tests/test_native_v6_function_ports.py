"""Exercise native-runner dialog ports with real SQLCipher before packaging.

The sealed outer capability alone is substituted. This is source/offscreen
verification, never a claim of native package or human acceptance.
"""
from types import SimpleNamespace
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
