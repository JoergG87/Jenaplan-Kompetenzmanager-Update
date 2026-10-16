"""Acceptance infrastructure boundaries, never claimed as native crypto evidence."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import macos_native_acceptance as native
from scripts import smoke_test_macos_keychain as keychain
from scripts import smoke_test_packaged_restore_worker as restore
from scripts import smoke_test_macos_security_integration as security
from src.core import macos_test_package_profile as identity
from tests.test_macos_test_package_profile import profile, config, smoke_bundle


@pytest.mark.parametrize("mode", sorted(identity.NATIVE_TEST_MODES))
def test_closed_native_mode_list(profile, mode):
    identity._validate_arguments(SimpleNamespace(**profile), ["--internal-native-test", mode])


@pytest.mark.parametrize("arguments", [
    ["--internal-native-test", "unknown"], ["--internal-native-test", "matrix", "extra"],
    ["--internal-native-test", "matrix", "--runtime-root", "/foreign"],
    ["--internal-native-test", "matrix", "--internal-native-test", "restart"],
])
def test_unknown_native_arguments_fail_closed(profile, arguments):
    with pytest.raises(ValueError): identity._validate_arguments(SimpleNamespace(**profile), arguments)


def test_nonfrozen_and_unbound_native_execution_is_rejected(monkeypatch):
    monkeypatch.setattr(native, "test_identity", lambda: None)
    assert native.run_frozen("initialize") == 1


def test_main_rejects_native_entry_without_profile(monkeypatch):
    from src.desktop_app import main
    monkeypatch.setattr(identity, "_test_identity", None)
    monkeypatch.setattr(main.sys, "argv", ["app", "--internal-native-test", "matrix"])
    assert main.main() == 2


@pytest.mark.parametrize("module", [keychain, restore, security])
def test_profile_runner_never_enters_legacy_path_or_misreports_failure(monkeypatch, tmp_path, module):
    run = Mock(return_value={"returncode": 4, "payload": {"status": "blocked"}})
    monkeypatch.setattr(native, "run_profile", run)
    monkeypatch.setattr(module, "tempfile", Mock(side_effect=AssertionError("legacy root")))
    with pytest.raises(RuntimeError): module.smoke_test(tmp_path / "sealed.app", test_profile=tmp_path / "profile.json")
    assert run.call_count == 1


@pytest.mark.parametrize("damage", ["digest", "snapshot", "root_override", "symlink", "mode"])
def test_native_runner_attests_before_any_launch(profile, smoke_bundle, tmp_path, monkeypatch, damage):
    import json, plistlib
    app, exe, validated = smoke_bundle
    path = config(tmp_path, profile)
    mode = "restart"
    if damage == "digest":
        info = app / "Contents/Info.plist"; payload = plistlib.loads(info.read_bytes())
        payload["JKMInternalTestProfileSHA256"] = "0" * 64; info.write_bytes(plistlib.dumps(payload))
    elif damage == "snapshot":
        (app / "Contents/Resources/internal_test_profile.json").write_text('{}')
    elif damage == "root_override": monkeypatch.setenv("JENAPLAN_APP_DATA_DIR", "/foreign")
    elif damage == "symlink": (Path(profile["runtime_root"]) / "foreign").symlink_to(tmp_path)
    elif damage == "mode": mode = "unknown"
    launch = Mock(side_effect=AssertionError("must not launch")); monkeypatch.setattr(native.subprocess, "run", launch)
    with pytest.raises(ValueError): native.run_profile(app, path, mode)
    launch.assert_not_called()


def valid_integrity():
    return {"cipher": "4.17.0 community", "provider": "commoncrypto", "sqlite": "3.53.3",
            "cipher_integrity": [], "integrity": [("ok",)], "fk": []}


@pytest.mark.parametrize("field,value", [
    ("cipher", "4.12.0 community"), ("provider", "openssl"), ("sqlite", "unknown"),
    ("cipher_integrity", [("corrupt",)]), ("integrity", [("bad",)]), ("fk", [("orphan",)]),
])
def test_actual_integrity_results_must_pass(field, value):
    check = valid_integrity(); native._check_integrity(check)
    check[field] = value
    with pytest.raises(RuntimeError): native._check_integrity(check)


ORDER = ["upgrade_startup.py:before_lock", "main.py:_preflight_desktop_runtime_root",
         "restore_runtime.py:acquire", "upgrade_startup.py:evaluate", "upgrade_startup.py:inspect",
         "final_v4_live_restore.py:recover_interrupted_final_v4_restore", "upgrade_startup.py:evaluate",
         "main.py:_new_database_initialization_candidate", "startup.py:build_security_runtime",
         "main.py:_isolated_packaged_smoke_session", "cipher_product_runtime.py:open_cipher_product_runtime"]


@pytest.mark.parametrize("missing", range(len(ORDER)))
def test_every_required_startup_boundary_is_enforced(missing):
    native._check_order({"payload": {"events": ORDER}})
    events = ORDER.copy(); events.pop(missing)
    with pytest.raises(RuntimeError): native._check_order({"payload": {"events": events}})


@pytest.mark.parametrize("forbidden", [
    "final_v4_live_restore.py:recover_interrupted_final_v4_restore", "startup.py:build_security_runtime",
    "main.py:_new_database_initialization_candidate", "data_master_key_store.py:create", "data_master_key_store.py:delete",
])
def test_guard_veto_forbids_every_later_mutation_port(forbidden):
    native._check_order({"payload": {"events": ORDER[:5]}}, guard_blocked=True)
    with pytest.raises(RuntimeError): native._check_order({"payload": {"events": ORDER[:5] + [forbidden]}}, guard_blocked=True)


def test_authenticated_synthetic_evidence_has_real_valid_codecs(tmp_path):
    from src.security.database_key_runtime import LoadedDatabaseKeyRuntime
    from src.security.data_keys import LoadedDataMasterKey
    from src.security.database_keys import DatabaseKey
    from uuid import uuid4
    from src.security.infrastructure.upgrade_journal_repository import AuthenticatedUpgradeJournalRepository as Journal
    from src.security.infrastructure.upgrade_replay_anchor import UpgradeReplayAnchorRepository as Anchor
    from src.security.database_keys import derive_migration_journal_auth_key
    account = SimpleNamespace(installation_id=str(uuid4()))
    # Evidence needs identifiers and a genuine HMAC key, no Keychain substitution.
    loaded = SimpleNamespace(database_context_id=str(uuid4()), database_key_id=str(uuid4()), database_key_generation=1,
        dmk_key_id=str(uuid4()), dmk_generation=1)
    loaded.dmk = LoadedDataMasterKey(loaded.dmk_key_id, 1, b"s" * 32)
    old = native._evidence(tmp_path, account, loaded)
    raw = (tmp_path / "schema-upgrade-foundation/journal.json").read_bytes()
    import json, hashlib
    operation = json.loads(raw)["state"]["context"]["operation_id"]
    key = derive_migration_journal_auth_key(loaded.dmk, migration_id=operation)
    state = Journal._decode(raw, key)
    assert state.phase.value == "STAGED" or state.phase.value == "staged"
    anchor = Anchor._decode((tmp_path / "schema-upgrade-replay/anchor.json").read_bytes(), key)
    assert anchor == Anchor.for_journal(state, hashlib.sha256(raw).hexdigest())
    assert Journal._decode(old, key).revision < state.revision


def test_native_module_is_spec_selected_only_for_internal_profile():
    spec = Path("packaging/macos_pilot.spec").read_text()
    modules = '["scripts.macos_native_acceptance", "scripts.macos_native_v6_acceptance"]'
    assert f'] + ({modules} if TEST_PROFILE is not None else [])' in spec
    assert f'] + ({modules} if TEST_PROFILE is None else [])' in spec
    assert '"src.security.packaged_integration_smoke"' in spec


def test_metadata_readers_leave_checkpointed_state_without_garbage_collection(tmp_path):
    import gc
    from uuid import uuid4
    from src.core.runtime_root_protection import prepare_synthetic_test_root
    from src.desktop_app.runtime import prepare_security_runtime_storage
    from src.security.startup import build_security_runtime
    from src.security.infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    from src.security.infrastructure.system import PlatformFilePermissionManager
    from src.security.data_keys import DataKeyset, DataKeysetStatus
    root = tmp_path.resolve() / "installation"; prepare_synthetic_test_root(root)
    paths = prepare_security_runtime_storage(data_root=root)
    enabled = gc.isenabled()
    gc.disable()
    try:
        security = build_security_runtime(paths)
        security.service.enroll_local_account("synthetic metadata lifecycle regression password")
        account = security.repository.load_account()
        keysets = SQLiteDataKeysetRepository(root / "keys/metadata.sqlite", PlatformFilePermissionManager())
        keysets.initialize()
        key_id = str(uuid4())
        keysets.prepare_data_keyset(DataKeyset(key_id, 1, DataKeysetStatus.PENDING, "a" * 64))
        keysets.activate_data_keyset(key_id=key_id)
        for _ in range(3):
            security.repository.require_current_read_only()
            assert security.repository.load_account() == account
            assert keysets.active_data_keyset().key_id == key_id
        snapshot = keysets.create_snapshot(root / "snapshot.sqlite")
        keysets.checkpoint_truncate()
        assert SQLiteDataKeysetRepository(snapshot, PlatformFilePermissionManager()).active_data_keyset().key_id == key_id
        # The standalone backup inherits WAL mode; SQLite can create empty
        # reader sidecars there. The live startup metadata must be checkpointed.
        for database in (paths.security_database, keysets.database_path):
            assert not any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))
        assert ExistingStartupAccountRepository(paths.security_database, None).load_bound_active_account() == account
    finally:
        if enabled: gc.enable()


def test_failed_metadata_validation_also_closes_the_real_sqlite_reader(tmp_path):
    import gc, sqlite3
    from contextlib import closing
    from src.security.infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
    from src.security.infrastructure.system import PlatformFilePermissionManager
    from src.security.domain import SecurityStoreError
    path = tmp_path / "invalid.sqlite"
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE invalid(value)"); db.commit()
    enabled = gc.isenabled(); gc.disable()
    try:
        with pytest.raises(SecurityStoreError):
            SQLiteDataKeysetRepository(path, PlatformFilePermissionManager()).active_data_keyset()
        with closing(sqlite3.connect(path)) as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        assert not Path(str(path) + "-wal").exists()
        assert not Path(str(path) + "-shm").exists()
    finally:
        if enabled: gc.enable()


@pytest.mark.parametrize("invalid", ["released", "foreign_path", "missing_keyset", "immutable"])
def test_security_finalization_rejects_invalid_context(tmp_path, invalid):
    from src.core.runtime_root_protection import prepare_synthetic_test_root
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.runtime import prepare_security_runtime_storage
    from src.security.startup import build_security_runtime, finalize_security_runtime
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    from src.security.infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
    from src.security.infrastructure.system import PlatformFilePermissionManager
    from dataclasses import replace
    root = tmp_path.resolve() / "installation"
    prepare_synthetic_test_root(root)
    paths = prepare_security_runtime_storage(data_root=root)
    runtime = build_security_runtime(paths)
    runtime.service.enroll_local_account("synthetic lifecycle regression password")
    if invalid != "missing_keyset":
        SQLiteDataKeysetRepository(paths.keyset_metadata, PlatformFilePermissionManager()).initialize()
    lock = RuntimeInstanceLock(root).acquire()
    try:
        if invalid == "released": lock.release()
        if invalid == "foreign_path":
            runtime = replace(runtime, repository=SimpleNamespace(database_path=tmp_path / "foreign.sqlite"))
        if invalid == "immutable":
            runtime = replace(runtime, repository=ExistingStartupAccountRepository(paths.security_database, None))
        with pytest.raises(Exception):
            finalize_security_runtime(runtime, paths, lock)
        if invalid == "missing_keyset": assert not paths.keyset_metadata.exists()
    finally:
        lock.release()


def test_security_finalization_keeps_metadata_and_releases_empty_sidecars(tmp_path):
    from src.core.runtime_root_protection import prepare_synthetic_test_root
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.desktop_app.runtime import prepare_security_runtime_storage
    from src.security.startup import build_security_runtime, finalize_security_runtime
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    from src.security.infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
    from src.security.infrastructure.system import PlatformFilePermissionManager
    root = tmp_path.resolve() / "installation"
    prepare_synthetic_test_root(root)
    paths = prepare_security_runtime_storage(data_root=root)
    runtime = build_security_runtime(paths)
    runtime.service.enroll_local_account("synthetic lifecycle regression password")
    account = runtime.repository.load_account()
    SQLiteDataKeysetRepository(paths.keyset_metadata, PlatformFilePermissionManager()).initialize()
    lock = RuntimeInstanceLock(root).acquire()
    try:
        finalize_security_runtime(runtime, paths, lock)
        for database in (paths.security_database, paths.keyset_metadata):
            assert not any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))
        assert ExistingStartupAccountRepository(paths.security_database, None).load_bound_active_account() == account
    finally:
        lock.release()
