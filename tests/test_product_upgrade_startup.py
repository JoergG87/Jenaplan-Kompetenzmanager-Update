"""A2 real desktop ordering with synthetic roots, real codecs and process locks."""
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
import gc
import os
from pathlib import Path
import signal
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.desktop_app import main as desktop_main
from src.desktop_app.runtime import runtime_paths, prepare_security_runtime_storage, prepare_cipher_runtime_storage
from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.core.restore_runtime import RuntimeInstanceLock, RestoreJournal, restore_transaction_paths
from src.core.schema_upgrade import UpgradeContext, UpgradePhase
from src.security.startup import build_security_runtime
from src.security.database_key_runtime import build_database_key_runtime, DatabaseKeyRuntimePaths
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.data_keys import DataMasterKeyReadResult, DataMasterKeyStoreStatus
from src.security.domain import SecurityStoreError
from src.security.upgrade_startup import (
    ProductStartupInventory, ProductUpgradeStartupGuard, UpgradeStartupBlocked,
    ExistingStartupAccountRepository, ReadOnlyUpgradeEvidence,
)
from src.security.infrastructure.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository
from src.security.infrastructure.upgrade_replay_anchor import UpgradeReplayAnchorRepository
from tests.test_installation_startup_ports import paths, private_file, snapshot, forbidden
from tests.test_database_key_runtime import MemoryDataMasterKeyStore
from tests.test_schema_upgrade_foundation import context, full_states
from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider


class RuntimeReached(Exception):
    pass


@pytest.fixture
def installation(tmp_path):
    root = (tmp_path / "installation").resolve()
    prepare_synthetic_test_root(root)
    product_paths = prepare_security_runtime_storage(data_root=root)
    security = build_security_runtime(product_paths)
    security.service.enroll_local_account("synthetische sichere Testpassphrase")
    account = security.repository.load_account()
    store = MemoryDataMasterKeyStore()
    loaded = build_database_key_runtime(paths(root)[0], account_loader=lambda: account, key_store=store).open_or_create()
    _, main, docs = paths(root)
    for path in (main.database, docs.database,
                 docs.container_root / ".jkm-security-sprint10-test-root",
                 docs.storage_root / ".jkm-security-sprint10-storage-root"):
        private_file(path)
    docs.layout_source_root.mkdir(mode=0o700)
    gc.collect()
    for database in (product_paths.security_database, paths(root)[0].keyset_metadata):
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
        for suffix in ("-wal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
    return root, account, store, loaded


def bind_main(root, monkeypatch):
    import PySide6.QtWidgets as widgets
    monkeypatch.setattr(desktop_main.sys, "argv", ["app"])
    monkeypatch.setattr(desktop_main, "application_data_root", lambda: root)
    monkeypatch.setattr(desktop_main, "_show_upgrade_startup_blocked", lambda *a, **k: None)
    def reached(*args):
        # Any dangerous post-guard initialization is beyond this runtime boundary.
        raise RuntimeReached
    monkeypatch.setattr(widgets, "QApplication", reached)


def no_startup_mutations(monkeypatch):
    import src.security.final_v4_live_restore as restore
    import src.security.startup as startup
    import src.security.cipher_product_runtime as cipher
    import src.security.final_v4_backup_runtime as backup
    monkeypatch.setattr(restore, "recover_interrupted_final_v4_restore", forbidden)
    monkeypatch.setattr(restore, "confirm_final_v4_restore_startup", forbidden)
    monkeypatch.setattr(startup, "build_security_runtime", forbidden)
    monkeypatch.setattr(cipher, "open_cipher_product_runtime", forbidden)
    monkeypatch.setattr(desktop_main, "publish_pilot_product_root", forbidden)
    monkeypatch.setattr(desktop_main, "prepare_security_runtime_storage", forbidden)
    monkeypatch.setattr(desktop_main, "_new_database_initialization_candidate", forbidden)


def evidence(root, account, loaded, *, phase=UpgradePhase.STAGED, alteration=None):
    ctx = replace(context(), installation_id=account.installation_id,
        database_context_id=loaded.database_context_id, database_key_id=loaded.database_key_id,
        database_key_generation=loaded.database_key_generation, dmk_key_id=loaded.dmk_key_id,
        dmk_generation=loaded.dmk_generation)
    if alteration:
        ctx = replace(ctx, **alteration)
    states, _ = full_states(ctx)
    state = next(s for s in states if s.phase is phase)
    key = derive_migration_journal_auth_key(loaded.dmk, migration_id=ctx.operation_id)
    raw = AuthenticatedUpgradeJournalRepository._encode(state, key)
    anchor = UpgradeReplayAnchorRepository.for_journal(state, AuthenticatedUpgradeJournalRepository.preview_digest(state, key))
    private_file(root / "schema-upgrade-foundation/journal.json", raw)
    private_file(root / "schema-upgrade-replay/anchor.json", UpgradeReplayAnchorRepository._encode(anchor, key))
    return states, key


@pytest.mark.parametrize("entry", [
    "schema-upgrade-foundation/journal.json", "schema-upgrade-replay/anchor.json",
    "schema-upgrade-source/op/rollback.sqlcipher", "schema-upgrade-foundation",
    "schema-upgrade-replay", "schema-upgrade-source", "unexpected",
])
def test_actual_main_stops_before_every_mutating_startup_port(tmp_path, monkeypatch, entry):
    root = (tmp_path / "installation").resolve()
    prepare_synthetic_test_root(root)
    if "." in entry.rsplit("/", 1)[-1] or entry == "unexpected":
        private_file(root / entry)
    else:
        (root / entry).mkdir(mode=0o700)
    bind_main(root, monkeypatch)
    no_startup_mutations(monkeypatch)
    before = snapshot(root)
    assert desktop_main.main() == 3
    after = snapshot(root)
    after.pop("instance.lock", None)
    assert after == before
    assert not paths(root)[1].database.exists()


@pytest.mark.parametrize("damage", ["journal_only", "anchor_only", "journal_tamper", "anchor_tamper",
    "replay", "staged", "wrong_installation", "wrong_database", "wrong_key", "wrong_dmk",
    "dmk_missing", "denied", "wrong_material", "metadata_missing", "security_corrupt", "enrollment_corrupt"])
def test_product_evidence_and_keys_never_reach_restore_or_first_run(installation, monkeypatch, damage):
    root, account, store, loaded = installation
    alterations = {
        "wrong_installation": {"installation_id": str(uuid4())},
        "wrong_database": {"database_context_id": str(uuid4())},
        "wrong_key": {"database_key_id": str(uuid4())},
        "wrong_dmk": {"dmk_key_id": str(uuid4())},
    }
    states, key = evidence(root, account, loaded, alteration=alterations.get(damage))
    journal = root / "schema-upgrade-foundation/journal.json"
    anchor = root / "schema-upgrade-replay/anchor.json"
    if damage == "journal_only": anchor.unlink()
    elif damage == "anchor_only": journal.unlink()
    elif damage == "journal_tamper": journal.write_bytes(journal.read_bytes() + b"x")
    elif damage == "anchor_tamper": anchor.write_bytes(b"corrupt")
    elif damage == "replay": journal.write_bytes(AuthenticatedUpgradeJournalRepository._encode(states[0], key))
    elif damage == "dmk_missing": store.values.clear()
    elif damage == "denied": store.read_status = DataMasterKeyStoreStatus.ACCESS_DENIED
    elif damage == "wrong_material": store.values[(account.installation_id, loaded.dmk_key_id)] = b"x" * 32
    elif damage == "metadata_missing": paths(root)[0].keyset_metadata.unlink()
    elif damage == "security_corrupt": (root / "security/security.sqlite").write_bytes(b"corrupt")
    elif damage == "enrollment_corrupt": (root / "security/enrollment.marker").write_bytes(b"corrupt")
    import src.security.existing_installation_keys as keys
    monkeypatch.setattr(keys, "build_platform_data_master_key_store", lambda: store)
    monkeypatch.setattr(store, "create", forbidden)
    monkeypatch.setattr(store, "delete", forbidden)
    bind_main(root, monkeypatch)
    no_startup_mutations(monkeypatch)
    before = snapshot(root)
    assert desktop_main.main() == 3
    after = snapshot(root); after.pop("instance.lock", None)
    assert after == before


@pytest.mark.parametrize("alteration,code", [
    ({"installation_id": str(uuid4())}, "upgrade_installation_context_conflict"),
    ({"dmk_generation": 2}, "upgrade_installation_context_conflict"),
    ({"database_key_generation": 2}, "upgrade_installation_context_conflict"),
])
def test_authenticated_context_is_checked_before_registry(installation, alteration, code):
    root, account, _, loaded = installation
    evidence(root, account, loaded, alteration=alteration)
    with RuntimeInstanceLock(root) as lock:
        with pytest.raises(UpgradeStartupBlocked, match=code):
            ReadOnlyUpgradeEvidence(ProductUpgradeStartupGuard(lock)).load(loaded, account.installation_id)


def test_replayed_generation_and_exact_product_registry(installation):
    root, account, _, loaded = installation
    states, key = evidence(root, account, loaded)
    with RuntimeInstanceLock(root) as lock:
        reader = ReadOnlyUpgradeEvidence(ProductUpgradeStartupGuard(lock))
        with pytest.raises(ValueError):  # unregistered synthetic target, no product edge
            reader.load(loaded, account.installation_id)
        private_file(root / "schema-upgrade-foundation/journal.json", AuthenticatedUpgradeJournalRepository._encode(states[0], key))
        with pytest.raises(UpgradeStartupBlocked, match="upgrade_replay_or_generation_conflict"):
            reader.load(loaded, account.installation_id)


def test_account_inspection_is_existing_only_and_immutable(installation, monkeypatch):
    root, expected, _, _ = installation
    from src.security.infrastructure.system import PlatformFilePermissionManager
    for name in ("prepare_directory", "secure_file", "secure_sqlite_files"):
        monkeypatch.setattr(PlatformFilePermissionManager, name, forbidden)
    before = snapshot(root)
    account = ExistingStartupAccountRepository(root / "security/security.sqlite", None).load_bound_active_account()
    assert account == expected
    assert snapshot(root) == before


def test_early_account_repository_has_no_writer_port(installation):
    root = installation[0]
    repository = ExistingStartupAccountRepository(root / "security/security.sqlite", None)
    before = snapshot(root)
    with pytest.raises(SecurityStoreError): repository.initialize()
    with pytest.raises(SecurityStoreError): repository.record_login_success(now=datetime.now(UTC))
    assert snapshot(root) == before


def test_actual_main_detects_inventory_change_during_existing_key_read(installation, monkeypatch):
    root, account, store, loaded = installation
    evidence(root, account, loaded)
    import src.security.existing_installation_keys as keys
    monkeypatch.setattr(keys, "build_platform_data_master_key_store", lambda: store)
    original = store.read
    def changed(**kwargs):
        private_file(root / "logs/new.log", b"changed during read")
        return original(**kwargs)
    monkeypatch.setattr(store, "read", changed)
    monkeypatch.setattr(store, "create", forbidden)
    bind_main(root, monkeypatch); no_startup_mutations(monkeypatch)
    assert desktop_main.main() == 3


@pytest.mark.parametrize("kind", ["complete", "fresh_marked", "empty", "absent"])
def test_actual_main_admits_only_existing_paths_without_key_initialization(installation, tmp_path, monkeypatch, kind):
    root = installation[0]
    if kind != "complete":
        root = (tmp_path / kind).resolve()
        if kind == "fresh_marked": prepare_synthetic_test_root(root)
        elif kind == "empty": root.mkdir(mode=0o700)
    import src.security.existing_installation_keys as keys
    monkeypatch.setattr(keys, "build_platform_data_master_key_store", forbidden)
    bind_main(root, monkeypatch)
    with pytest.raises(RuntimeReached): desktop_main.main()
    # No upgrade artifact is introduced, even on the accepted new-install path.
    assert not (root / "schema-upgrade-foundation").exists()
    assert not (root / "schema-upgrade-replay").exists()


@pytest.mark.parametrize("damage", ["main_missing", "rollback_without_main", "partial", "unreadable", "symlink", "root_alias"])
def test_main_does_not_reclassify_unknown_installations_as_empty(installation, monkeypatch, damage):
    root = installation[0]
    if damage in {"main_missing", "rollback_without_main"}: paths(root)[1].database.unlink()
    if damage == "rollback_without_main": private_file(root / "schema-upgrade-source/op/rollback.sqlcipher")
    elif damage == "partial": paths(root)[2].database.unlink()
    elif damage == "unreadable": root.chmod(0o000)
    elif damage == "symlink": (root / "unsafe").symlink_to(root.parent)
    elif damage == "root_alias":
        alias = root.parent / "alias"; alias.symlink_to(root, target_is_directory=True); root = alias
    bind_main(root, monkeypatch); no_startup_mutations(monkeypatch)
    try:
        assert desktop_main.main() == 3
    finally:
        if damage == "unreadable": root.chmod(0o700)


def test_changed_inventory_between_preflight_and_lock_blocks(installation, monkeypatch):
    root = installation[0]
    original = RuntimeInstanceLock.acquire
    def changed(self):
        result = original(self)
        private_file(root / "schema-upgrade-foundation/journal.json")
        return result
    monkeypatch.setattr(RuntimeInstanceLock, "acquire", changed)
    bind_main(root, monkeypatch); no_startup_mutations(monkeypatch)
    assert desktop_main.main() == 3


def test_upgrade_restore_conflict_before_keychain_or_recovery(installation, monkeypatch):
    root = installation[0]
    private_file(root / "schema-upgrade-foundation/journal.json")
    private_file(root / "encrypted-restore-staging/op/RESTORE_READY")
    import src.security.existing_installation_keys as keys
    monkeypatch.setattr(keys, "build_platform_data_master_key_store", forbidden)
    bind_main(root, monkeypatch); no_startup_mutations(monkeypatch)
    before = snapshot(root)
    assert desktop_main.main() == 3
    after = snapshot(root); after.pop("instance.lock", None)
    assert before == after


def test_real_process_lock_competition_and_release_after_kill(installation, monkeypatch):
    root = installation[0]
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(read_fd)
        with RuntimeInstanceLock(root):
            os.write(write_fd, b"held")
            signal.pause()
        os._exit(2)
    os.close(write_fd)
    try:
        assert os.read(read_fd, 4) == b"held"
        bind_main(root, monkeypatch)
        assert desktop_main.main() == 3
    finally:
        os.close(read_fd); os.kill(child, signal.SIGKILL); os.waitpid(child, 0)
    with pytest.raises(RuntimeReached): desktop_main.main()


def test_product_guard_requires_current_lock(installation):
    root = installation[0]
    with pytest.raises(UpgradeStartupBlocked, match="upgrade_runtime_lock_required"):
        ProductUpgradeStartupGuard(RuntimeInstanceLock(root)).evaluate()


def test_lock_must_belong_to_the_preflight_root_even_when_both_are_empty(tmp_path):
    expected = (tmp_path / "expected").resolve()
    other = (tmp_path / "other").resolve()
    before = ProductStartupInventory().before_lock(expected)
    with RuntimeInstanceLock(other) as lock:
        with pytest.raises(UpgradeStartupBlocked, match="upgrade_inventory_changed"):
            ProductUpgradeStartupGuard(lock).evaluate(before=before)
    assert not expected.exists()


def test_ancillary_product_modes_are_not_first_run_or_upgrade_authority(installation):
    root = installation[0]
    prepare_cipher_runtime_storage(data_root=root)
    (root / "logs/log.txt").write_text("synthetic")
    with RuntimeInstanceLock(root) as lock:
        assert ProductUpgradeStartupGuard(lock).evaluate().continue_existing_startup
    (root / "logs/log.txt").chmod(0o666)
    with RuntimeInstanceLock(root) as lock:
        with pytest.raises(UpgradeStartupBlocked): ProductUpgradeStartupGuard(lock).evaluate()


def product_main_ports(root, monkeypatch, store):
    """Replace only presentation/login interaction; exercise real product composition."""
    from unittest.mock import MagicMock
    import PySide6.QtWidgets as widgets
    import src.desktop_app.theme as theme
    import src.desktop_app.app as app_module
    import src.desktop_app.security_controller as controller
    import src.security.cipher_product_runtime as cipher
    import src.security.final_v4_backup_runtime as backup
    from src.security.session import InMemorySession
    app = MagicMock(); app.exec.return_value = 0
    application_factory = MagicMock(return_value=app)
    application_factory.instance.return_value = app
    monkeypatch.setattr(widgets, "QApplication", application_factory)
    monkeypatch.setattr(widgets.QMessageBox, "critical", lambda *a: None)
    monkeypatch.setattr(desktop_main, "_show_upgrade_startup_blocked", lambda *a, **k: None)
    monkeypatch.setattr(desktop_main.sys, "argv", ["app"])
    monkeypatch.setattr(desktop_main, "application_data_root", lambda: root)
    monkeypatch.setattr(desktop_main, "_app_icon", lambda: None)
    monkeypatch.setattr(theme, "apply_app_theme", lambda app: None)
    monkeypatch.setattr(app_module, "JenaplanDesktopApp", lambda *a, **k: MagicMock())
    monkeypatch.setattr(controller, "SecurityUiCoordinator", lambda **k: None)
    monkeypatch.setattr(controller, "should_attempt_startup_device_authentication", lambda **k: False)
    def authenticate(**kwargs):
        service, repository = kwargs["service"], kwargs["repository"]
        if not repository.exists(): service.enroll_local_account("synthetische sichere Testpassphrase")
        account = repository.load_account()
        return SimpleNamespace(session=InMemorySession(account.user_id, account.installation_id, repository.security_epoch()), enrollment_completed=False)
    monkeypatch.setattr(controller, "run_startup_authentication", authenticate)
    real_open = cipher.open_cipher_product_runtime
    opened = []
    def open_product(**kwargs):
        result = real_open(**kwargs, key_store=store, sqlcipher_provider=qualified_sqlcipher_test_provider())
        opened.append(result)
        return result
    monkeypatch.setattr(cipher, "open_cipher_product_runtime", open_product)
    real_backup = backup.build_final_v4_encrypted_backup_service
    monkeypatch.setattr(backup, "build_final_v4_encrypted_backup_service", lambda **kwargs:
        real_backup(**kwargs, key_store=store, sqlcipher_provider=qualified_sqlcipher_test_provider()))
    return opened


def test_full_actual_main_first_run_restart_and_unknown_schema(tmp_path, monkeypatch):
    root = (tmp_path / "installation").resolve()
    store = MemoryDataMasterKeyStore()
    opened = product_main_ports(root, monkeypatch, store)
    assert desktop_main.main() == 0
    assert opened[-1].first_run
    dmk_before = dict(store.values)
    gc.collect()  # settle old connection sidecars before simulating a new process
    assert desktop_main.main() == 0
    assert not opened[-1].first_run
    assert store.values == dmk_before
    from tests.test_cipher_product_composition import _assert_fresh_first_run_domain_contract
    _assert_fresh_first_run_domain_contract(opened[-1], runtime_paths(root))
    assert not (root / "schema-upgrade-foundation").exists()
    assert not (root / "schema-upgrade-replay").exists()
    with closing(opened[-1].database.connect()) as db:
        db.execute("PRAGMA user_version = 99")
    gc.collect()  # also finish the second runtime's connections before a third start
    assert desktop_main.main() == 4  # unchanged keyed compatibility gate rejects
    assert store.values == dmk_before


@pytest.mark.parametrize("failure", ["missing", "denied", "wrong_material"])
def test_existing_v4_main_key_failure_never_creates_a_replacement(tmp_path, monkeypatch, failure):
    root = (tmp_path / "installation").resolve()
    store = MemoryDataMasterKeyStore()
    opened = product_main_ports(root, monkeypatch, store)
    assert desktop_main.main() == 0
    assert opened[-1].first_run
    gc.collect()  # a true restart has no surviving previous SQLite connections
    create_count = store.create_calls
    if failure == "missing": store.values.clear()
    elif failure == "denied": store.read_status = DataMasterKeyStoreStatus.ACCESS_DENIED
    else:
        for identity in store.values: store.values[identity] = b"x" * 32
    assert desktop_main.main() == 4
    assert store.create_calls == create_count


def prepare_restore_case(tmp_path, monkeypatch):
    import tests.test_final_v4_encrypted_live_restore as restore_tests
    import src.security.final_v4_backup_runtime as backup_runtime
    from src.security.cipher_product_runtime import open_cipher_product_runtime
    def open_case(_tmp_path):
        root = (_tmp_path / "installation").resolve()
        prepare_synthetic_test_root(root)
        product_paths = prepare_security_runtime_storage(data_root=root)
        security = build_security_runtime(product_paths)
        security.service.enroll_local_account("synthetische sichere Testpassphrase")
        account = security.repository.load_account()
        store = MemoryDataMasterKeyStore()
        provider = qualified_sqlcipher_test_provider()
        opened = open_cipher_product_runtime(paths=product_paths, account_loader=lambda: account,
            authentication_confirmed=True, first_run_allowed=True, key_store=store, sqlcipher_provider=provider)
        desktop_main._build_cipher_product_student_adapter(opened)
        # Reuse the true product installation rather than admitting gated-test
        # marker files or weakening the startup inventory for synthetic tests.
        service = backup_runtime.build_final_v4_encrypted_backup_service(
            opened_runtime=opened.runtime, account_loader=lambda: account, environ={},
            key_store=store, sqlcipher_provider=provider, product_paths=product_paths)
        return opened.runtime, service, store, {}, lambda: account, provider
    monkeypatch.setattr(restore_tests, "_open_case", open_case)
    monkeypatch.setattr(backup_runtime, "SQLCipherConnectionProvider", lambda **k: qualified_sqlcipher_test_provider())
    original = restore_tests._write_excluded_sentinels
    def private_sentinels(root):
        result = original(root)
        (root / "security/security.sqlite").chmod(0o600)
        (root / "app-preferences.json").chmod(0o600)
        return result
    monkeypatch.setattr(restore_tests, "_write_excluded_sentinels", private_sentinels)
    return restore_tests._prepare_restore(tmp_path, include_bootstrap_context=True)


@pytest.mark.parametrize("boundary,expected", [
    ("before_swap", "aborted_before_replacement"),
    ("between_main_and_companion", "rolled_back"),
    ("after_databases_before_documents", "rolled_back"),
    ("during_documents", "rolled_back"),
    ("after_swap_before_reopen", "rolled_back"),
    ("after_reopen", "rolled_back"),
])
def test_actual_main_recovers_real_restore_process_crash(tmp_path, monkeypatch, boundary, expected):
    import src.security.final_v4_live_restore as restore
    import tests.test_final_v4_encrypted_live_restore as restore_tests
    case = prepare_restore_case(tmp_path, monkeypatch)
    runtime, service, _, _, prepared, lock, excluded, _, store, account_loader, _ = case
    root = service.paths.final_v4.key_runtime.root
    dmk_before = dict(store.values)
    prepared.safety_backup.transfer_to_worker()
    child = os.fork()
    if child == 0:
        def crash(observed):
            if observed == boundary: os._exit(97)
        restore.FinalV4EncryptedLiveRestoreService(service, fault_hook=crash).execute(
            handoff_path=prepared.handoff.path, nonce=prepared.handoff.nonce,
            lock=lock, restart=restore_tests._restart_callback(service), handshake_timeout_seconds=1)
        os._exit(2)
    lock.transfer()
    assert os.waitstatus_to_exitcode(os.waitpid(child, 0)[1]) == 97
    original = restore.recover_interrupted_final_v4_restore
    recovery_results = []
    def recover(**kwargs):
        result = original(**kwargs, key_store=store, account_loader=account_loader)
        recovery_results.append(result)
        return result
    monkeypatch.setattr(restore, "recover_interrupted_final_v4_restore", recover)
    # No normal security initialization may precede this actual recovery.
    import src.security.startup as startup
    import src.security.existing_installation_keys as keys
    monkeypatch.setattr(startup, "build_security_runtime", forbidden)
    monkeypatch.setattr(keys, "build_platform_data_master_key_store", forbidden)
    monkeypatch.setattr(store, "create", forbidden)
    bind_main(root, monkeypatch)
    with pytest.raises(RuntimeReached): desktop_main.main()
    assert recovery_results[0].status == expected
    assert RestoreJournal(restore_transaction_paths(root, prepared.handoff.restore_id)).read()["phase"] == expected
    restore_tests._assert_excluded(root, excluded)
    service.verify_live_runtime(root, manifest=prepared.safety_backup.result.manifest, enforce_artifact_hashes=False)
    assert store.values == dmk_before


def test_restore_ready_and_completed_restore_cross_the_real_main_guard(tmp_path, monkeypatch):
    import src.security.final_v4_live_restore as restore
    import tests.test_final_v4_encrypted_live_restore as restore_tests
    case = prepare_restore_case(tmp_path, monkeypatch)
    _, service, _, staging, prepared, lock, _, _, store, _, _ = case
    root = lock.runtime_root
    assert (staging.staging_root / "RESTORE_READY").is_file()
    assert ProductUpgradeStartupGuard(lock).evaluate().continue_existing_startup
    prepared.safety_backup.transfer_to_worker()
    restore.FinalV4EncryptedLiveRestoreService(service).execute(
        handoff_path=prepared.handoff.path, nonce=prepared.handoff.nonce,
        lock=lock, restart=restore_tests._restart_callback(service), handshake_timeout_seconds=1)
    lock.release()
    monkeypatch.setattr(store, "create", forbidden)
    bind_main(root, monkeypatch)
    with pytest.raises(RuntimeReached): desktop_main.main()


@pytest.mark.parametrize("damage", ["handoff_missing", "journal_corrupt", "resume_token_missing"])
def test_incomplete_restore_evidence_never_authorizes_first_run(tmp_path, monkeypatch, damage):
    case = prepare_restore_case(tmp_path, monkeypatch)
    _, _, _, _, prepared, lock, _, _, _, _, _ = case
    root = lock.runtime_root
    tx = restore_transaction_paths(root, prepared.handoff.restore_id)
    if damage == "handoff_missing":
        prepared.handoff.path.unlink()
        RestoreJournal(tx).transition("worker_started", next_step="maintenance")
        RestoreJournal(tx).transition("maintenance", next_step="preflight")
        # Missing authenticated components after a claimed replacement cannot recover.
        RestoreJournal(tx).transition("preflight_verified", next_step="replace")
        RestoreJournal(tx).transition("replacing", next_step="verify")
    elif damage == "journal_corrupt": tx.current_state.write_bytes(b"corrupt")
    else:
        RestoreJournal(tx).transition("worker_started", next_step="maintenance")
        RestoreJournal(tx).transition("maintenance", next_step="preflight")
        RestoreJournal(tx).transition("preflight_verified", next_step="replace")
        RestoreJournal(tx).transition("replacing", next_step="verify")
        RestoreJournal(tx).transition("installed_verified", next_step="confirm_startup")
    lock.release()
    bind_main(root, monkeypatch)
    monkeypatch.setattr(desktop_main, "_new_database_initialization_candidate", forbidden)
    assert desktop_main.main() == 3


def test_worker_and_parent_abort_cannot_mutate_upgrade_restore_conflict(installation, monkeypatch):
    from src.desktop_app import restore_worker
    root = installation[0]
    restore_id = str(uuid4())
    handoff = root / "restore-handoffs" / f"{restore_id}.json"
    private_file(handoff, b"{}")
    private_file(root / "schema-upgrade-foundation/journal.json")
    before = snapshot(root)
    assert restore_worker.run(["--handoff", str(handoff), "--nonce", "unused",
        "--restore-mode", restore_worker.RESTORE_MODE_FINAL_V4_ENCRYPTED], encrypted_service_factory=forbidden) == restore_worker.EXIT_MANUAL_RECOVERY_REQUIRED
    with RuntimeInstanceLock(root) as lock:
        restore_worker._abort_unconfirmed_restore(lock, restore_id, restore_worker.RESTORE_MODE_FINAL_V4_ENCRYPTED)
    after = snapshot(root); after.pop("instance.lock", None)
    assert before == after


def test_actual_main_restart_handoff_uses_existing_keys_after_guard(tmp_path, monkeypatch):
    import src.security.final_v4_live_restore as restore
    case = prepare_restore_case(tmp_path, monkeypatch)
    _, service, _, _, prepared, lock, _, _, store, account_loader, _ = case
    root = lock.runtime_root
    original_confirm = restore.confirm_final_v4_restore_startup
    confirms = []
    def confirm(**kwargs):
        result = original_confirm(**kwargs, key_store=store, account_loader=account_loader)
        confirms.append(result)
        return result
    monkeypatch.setattr(restore, "confirm_final_v4_restore_startup", confirm)
    monkeypatch.setattr(store, "create", forbidden)
    bind_main(root, monkeypatch)
    prepared.safety_backup.transfer_to_worker()
    def restart(tx, token, held_lock):
        monkeypatch.setattr(desktop_main.sys, "argv", ["app", "--final-v4-restore-confirm",
            "--runtime-root", str(root), "--restore-id", tx.transaction.name,
            "--restore-token", token, "--restore-lock-fd", str(os.dup(held_lock.fileno))])
        with pytest.raises(RuntimeReached): desktop_main.main()
        return True
    result = restore.FinalV4EncryptedLiveRestoreService(service).execute(
        handoff_path=prepared.handoff.path, nonce=prepared.handoff.nonce,
        lock=lock, restart=restart, handshake_timeout_seconds=1)
    assert result.status == "completed"
    assert len(confirms) == 1 and confirms[0].status == "completed"
    lock.release()


def test_error_port_is_sanitized_and_offers_no_repair(monkeypatch):
    from unittest.mock import MagicMock
    import PySide6.QtWidgets as widgets
    app = MagicMock()
    factory = MagicMock(); factory.instance.return_value = app
    message_box = widgets.QMessageBox
    dialog = MagicMock()
    error_port = MagicMock(return_value=dialog)
    error_port.Option = message_box.Option
    error_port.Icon = message_box.Icon
    error_port.StandardButton = message_box.StandardButton
    monkeypatch.setattr(widgets, "QApplication", factory)
    monkeypatch.setattr(widgets, "QMessageBox", error_port)
    desktop_main._show_upgrade_startup_blocked(["app"], packaged_smoke=False)
    factory.assert_not_called()
    error_port.assert_called_once_with()
    dialog.setOption.assert_called_once_with(message_box.Option.DontUseNativeDialog, True)
    dialog.setIcon.assert_called_once_with(message_box.Icon.Critical)
    dialog.setStandardButtons.assert_called_once_with(message_box.StandardButton.Ok)
    dialog.setWindowTitle.assert_called_once_with("Sicherer Start angehalten")
    assert "Support" in dialog.setText.call_args.args[0]
    assert "Reparieren" not in dialog.setText.call_args.args[0]
    dialog.exec.assert_called_once_with()


def test_direct_confirm_entry_cannot_bypass_upgrade_guard(installation, monkeypatch):
    import src.security.final_v4_live_restore as restore
    root = installation[0]
    private_file(root / "schema-upgrade-foundation/journal.json")
    monkeypatch.setattr(restore, "confirm_final_v4_restore_startup", forbidden)
    with RuntimeInstanceLock(root) as lock:
        assert restore.run_confirm(["--runtime-root", str(root), "--restore-id", str(uuid4()),
            "--restore-token", "unused", "--restore-lock-fd", str(os.dup(lock.fileno))]) == 1
