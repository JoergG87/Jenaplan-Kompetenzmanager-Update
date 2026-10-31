"""Consent and connection-drain ordering at the product migration entry."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.timetable_weeks_schema import PRODUCT_V7_SCHEMA_REGISTRATION
import src.desktop_app.main as main
import src.desktop_app.product_migration_dialog as dialog
import src.security.product_v7 as product


@pytest.fixture
def entry(monkeypatch, tmp_path):
    events = []
    service = object()
    identity = Mock(return_value=FINAL_V4_SCHEMA_REGISTRATION.identity)
    consent = Mock(return_value=True)
    restart = Mock(side_effect=lambda root: events.append(("restart", root)))
    monkeypatch.setattr(product, "product_schema_identity", identity)
    monkeypatch.setattr(dialog, "ask_product_migration", consent)
    monkeypatch.setattr(main, "_restart_product_migration", restart)
    stack = SimpleNamespace(close=lambda: events.append("close"))
    lock = SimpleNamespace(release=lambda: events.append("release"))
    def run(**kwargs):
        return main._offer_product_migration(tmp_path, service=service,
            runtime_stack=stack, lock=lock, **kwargs)
    return SimpleNamespace(run=run, events=events, service=service,
        identity=identity, consent=consent, restart=restart, root=tmp_path)


def test_confirmed_v4_closes_connections_and_releases_lock_before_restart(entry):
    entry.run()
    entry.identity.assert_called_once_with(entry.service)
    entry.consent.assert_called_once()
    assert entry.events == ["close", "release", ("restart", entry.root)]


def test_declined_v4_preserves_runtime_and_does_not_restart(entry):
    entry.consent.return_value = False
    entry.run()
    entry.consent.assert_called_once()
    assert entry.events == []
    entry.restart.assert_not_called()


def test_existing_v7_never_prompts_or_repeats_migration(entry):
    entry.identity.return_value = PRODUCT_V7_SCHEMA_REGISTRATION.identity
    entry.run()
    entry.consent.assert_not_called()
    entry.restart.assert_not_called()
    assert entry.events == []


def test_unknown_schema_never_prompts_or_mutates(entry):
    entry.identity.side_effect = RuntimeError("unrecognized schema")
    with pytest.raises(RuntimeError, match="unrecognized schema"):
        entry.run()
    entry.consent.assert_not_called()
    assert entry.events == []


def test_smoke_does_not_initiate_interactive_migration(entry):
    entry.run(packaged_smoke=True)
    entry.identity.assert_not_called()
    entry.consent.assert_not_called()
    entry.restart.assert_not_called()
    assert entry.events == []


def test_failed_connection_close_never_releases_lock_or_starts_worker(entry):
    def fail():
        raise RuntimeError("close failed")
    lock = Mock()
    stack = SimpleNamespace(close=fail)
    with pytest.raises(RuntimeError, match="close failed"):
        main._offer_product_migration(entry.root, service=entry.service,
            runtime_stack=stack, lock=lock)
    lock.release.assert_not_called()
    entry.restart.assert_not_called()


@pytest.mark.parametrize("complete", [False, True])
def test_restart_replaces_drained_image_with_existing_maintenance_entry(monkeypatch, tmp_path, complete):
    import src.desktop_app.product_v7_maintenance as maintenance
    captured = []
    def replace(executable, arguments, environment):
        captured.append((executable, arguments, environment))
        raise SystemExit(0)
    monkeypatch.setattr(maintenance, "_command", lambda args: ["/qualified/app", *args])
    monkeypatch.setattr(main.os, "execve", replace)
    monkeypatch.setattr(main.sys, "frozen", True, raising=False)
    with pytest.raises(SystemExit):
        main._restart_product_migration(tmp_path, complete=complete)
    executable, arguments, environment = captured[0]
    assert executable == "/qualified/app"
    assert arguments == ["/qualified/app",
        "--complete-v7-migration" if complete else "--migrate-v4-to-v7",
        "--guided-v7-migration", "--runtime-root", str(tmp_path)]
    assert environment["PYINSTALLER_RESET_ENVIRONMENT"] == "1"


@pytest.fixture
def completion(monkeypatch, tmp_path):
    import src.security.upgrade_startup as startup
    import PySide6.QtWidgets as widgets
    artifacts = {"schema-upgrade-source", product.SOURCE_DIRECTORY, product.SOURCE_BACKUP}
    inventory = SimpleNamespace(status=SimpleNamespace(value="existing"),
        restore_evidence=False, artifacts=tuple(SimpleNamespace(role="upgrade_evidence", relative_path=p)
            for p in artifacts))
    inspect = Mock(return_value=inventory)
    monkeypatch.setattr(startup.ProductStartupInventory, "inspect", inspect)
    monkeypatch.setattr(widgets, "QApplication", SimpleNamespace(instance=lambda: object()))
    consent = Mock(return_value=True)
    restart = Mock()
    monkeypatch.setattr(dialog, "ask_product_migration", consent)
    monkeypatch.setattr(main, "_restart_product_migration", restart)
    return SimpleNamespace(root=tmp_path, inventory=inventory, inspect=inspect,
        consent=consent, restart=restart,
        run=lambda **kwargs: main._offer_product_migration_completion(tmp_path, **kwargs))


def test_retained_source_backup_offers_only_confirmed_completion(completion):
    assert completion.run() is True
    completion.consent.assert_called_once_with(completing=True)
    completion.restart.assert_called_once_with(completion.root, complete=True)


def test_completion_decline_preserves_state_without_restart(completion):
    completion.consent.return_value=False
    assert completion.run() is False
    completion.restart.assert_not_called()


@pytest.mark.parametrize("status", ["unsafe", "unknown", "changed"])
def test_completion_rejects_unsafe_inventory(completion, status):
    completion.inventory.status.value=status
    assert completion.run() is False
    completion.consent.assert_not_called()
    completion.restart.assert_not_called()


def test_completion_rejects_restore_evidence(completion):
    completion.inventory.restore_evidence=True
    assert completion.run() is False
    completion.consent.assert_not_called()
    completion.restart.assert_not_called()


@pytest.mark.parametrize("path", [product.COMPLETION,
    "schema-upgrade-source/foreign-transaction/source.jkmebackup"])
def test_completion_rejects_completed_or_foreign_upgrade_evidence(completion, path):
    completion.inventory.artifacts += (SimpleNamespace(role="upgrade_evidence",relative_path=path),)
    assert completion.run() is False
    completion.consent.assert_not_called()
    completion.restart.assert_not_called()


def test_completion_rejects_missing_source_backup(completion):
    completion.inventory.artifacts=tuple(a for a in completion.inventory.artifacts
        if a.relative_path != product.SOURCE_BACKUP)
    assert completion.run() is False
    completion.consent.assert_not_called()
    completion.restart.assert_not_called()


def test_completion_smoke_skips_inventory_and_prompt(completion):
    assert completion.run(packaged_smoke=True) is False
    completion.inspect.assert_not_called()
    completion.consent.assert_not_called()
    completion.restart.assert_not_called()



def test_finalization_runs_under_lock_before_drain_and_restart(entry):
    stack=SimpleNamespace(close=lambda: entry.events.append("close"))
    lock=SimpleNamespace(release=lambda: entry.events.append("release"))
    main._offer_product_migration(entry.root, service=entry.service,
        runtime_stack=stack, lock=lock,
        before_close=lambda: entry.events.append("finalize"))
    assert entry.events == ["finalize", "close", "release", ("restart", entry.root)]


def test_finalization_failure_never_releases_lock_or_starts_worker(entry):
    lock=Mock()
    stack=Mock()
    def fail(): raise RuntimeError("checkpoint failed")
    with pytest.raises(RuntimeError, match="checkpoint failed"):
        main._offer_product_migration(entry.root, service=entry.service,
            runtime_stack=stack, lock=lock, before_close=fail)
    lock.release.assert_not_called()
    stack.close.assert_not_called()
    entry.restart.assert_not_called()


def test_actual_main_confirmation_finalizes_metadata_and_releases_product_lock(tmp_path, monkeypatch):
    import gc
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.security.database_key_runtime import DatabaseKeyRuntimePaths
    from tests.test_product_upgrade_startup import product_main_ports, MemoryDataMasterKeyStore
    root=(tmp_path / "installation").resolve()
    store=MemoryDataMasterKeyStore()
    opened=product_main_ports(root, monkeypatch, store)
    assert main.main() == 0
    gc.collect()
    keys_before=dict(store.values)
    class ReplacedImage(BaseException): pass
    reached=[]
    def replace(runtime_root):
        assert runtime_root == root
        with RuntimeInstanceLock(root):
            pass
        paths=DatabaseKeyRuntimePaths.for_root(root)
        for metadata in (root / "security/security.sqlite", paths.keyset_metadata, paths.envelope_registry):
            for suffix in ("-wal", "-shm"):
                assert not Path(str(metadata)+suffix).exists()
        reached.append(True)
        raise ReplacedImage()
    monkeypatch.setattr(dialog, "ask_product_migration", lambda: True)
    monkeypatch.setattr(main, "_restart_product_migration", replace)
    with pytest.raises(ReplacedImage):
        main.main()
    assert reached == [True]
    assert not opened[-1].first_run
    assert store.values == keys_before
