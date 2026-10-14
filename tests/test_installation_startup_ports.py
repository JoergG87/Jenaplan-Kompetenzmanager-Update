"""Synthetic A1 boundary tests; no native/product Keychain access."""
import os
import gc
from contextlib import closing
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import uuid

import pytest

from src.core.installation_inventory import InstallationInventoryStatus as I
from src.security.infrastructure.installation_inventory import ReadOnlyInstallationInventory
from src.security.existing_installation_keys import ExistingInstallationKeys, ExistingInstallationKeyStatus as K
from src.security.database_key_runtime import DatabaseKeyRuntimePaths, build_database_key_runtime, DatabaseKeyRuntime
from src.security.data_keys import DataMasterKeyReadResult, DataMasterKeyStoreStatus as S, DataMasterKeyService
from src.security.database_keys import DatabaseKeyEnvelopeService, DatabaseKeyEnvelopeStatus, derive_database_key_registry_auth_key
from dataclasses import replace
from src.security.domain import AccountStatus
from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths
from src.security.final_v3_document_runtime import FinalV3DocumentRuntimePaths
from src.security.infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
from src.security.infrastructure.database_key_envelope_repository import FileDatabaseKeyEnvelopeRepository
from tests.test_database_key_runtime import MemoryDataMasterKeyStore
from src.security.infrastructure.system import PlatformFilePermissionManager


def private_file(path, payload=b"synthetic"):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = path.parent
    while current.name != "installation":
        current.chmod(0o700)
        current = current.parent
    path.write_bytes(payload)
    path.chmod(0o600)


@pytest.fixture
def root(tmp_path):
    result = tmp_path.resolve() / "installation"
    result.mkdir(mode=0o700)
    return result


def paths(root):
    keys = DatabaseKeyRuntimePaths.for_root(root)
    main = FinalV4SQLCipherRuntimePaths.for_key_runtime(keys)
    return keys, main, FinalV3DocumentRuntimePaths.for_final_v4(main)


def complete(root):
    keys, main, docs = paths(root)
    for path in (keys.keyset_metadata, keys.envelope_registry, main.database, docs.database,
                 root / "security/security.sqlite", root / "security/enrollment.marker",
                 root / ".jkm-runtime-root-v1",
                 docs.container_root / ".jkm-security-sprint10-test-root",
                 docs.storage_root / ".jkm-security-sprint10-storage-root"):
        private_file(path)
    docs.layout_source_root.mkdir(mode=0o700)


def snapshot(root):
    # Kernel-managed atime may change on a read; compare content and mutation
    # metadata, not access-time bookkeeping.
    def metadata(path):
        value = path.lstat()
        return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
                value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    return {str(p.relative_to(root)): (metadata(p), p.read_bytes() if p.is_file() else None)
            for p in root.rglob("*")}


def forbidden(*args, **kwargs):
    pytest.fail("forbidden mutation/creation called")


def test_empty_requires_no_entries_and_no_runtime_authority(root):
    port = ReadOnlyInstallationInventory()
    before = snapshot(root)
    result = port.inspect(root)
    assert result.status is I.EMPTY
    assert not result.first_run_allowed and not result.normal_runtime_allowed and not result.activation_allowed
    assert snapshot(root) == before
    private_file(root / "instance.lock")
    assert port.inspect(root).status is I.MAIN_MISSING
    assert port.inspect(root / "absent").status is I.UNSAFE
    assert not (root / "absent").exists()


def test_full_presence_does_not_validate_schema(root):
    complete(root)
    before = snapshot(root)
    result = ReadOnlyInstallationInventory().inspect(root)
    assert result.status is I.V4_ARTIFACTS_PRESENT  # deliberately fake bytes
    assert not result.normal_runtime_allowed
    assert snapshot(root) == before
    _, main, _ = paths(root)
    main.database.unlink()
    assert ReadOnlyInstallationInventory().inspect(root).status is I.MAIN_MISSING


@pytest.mark.parametrize("kind", ["companion", "documents", "security", "keyset"])
def test_incomplete_without_main(root, kind):
    keys, _, docs = paths(root)
    if kind == "documents":
        docs.container_root.parent.mkdir(mode=0o700)
        docs.container_root.mkdir(mode=0o700)
    else:
        private_file({"companion": docs.database, "security": root / "security/security.sqlite",
                      "keyset": keys.keyset_metadata}[kind])
    assert ReadOnlyInstallationInventory().inspect(root).status is I.MAIN_MISSING


@pytest.mark.parametrize("names,expected", [
    (["schema-upgrade-foundation/journal.json"], I.UPGRADE_EVIDENCE),
    (["schema-upgrade-replay/anchor.json"], I.UPGRADE_EVIDENCE),
    (["schema-upgrade-foundation/journal.json", "schema-upgrade-replay/anchor.json"], I.UPGRADE_EVIDENCE),
    (["schema-upgrade-source/op/candidate.sqlcipher"], I.UPGRADE_EVIDENCE),
    (["restore-handoffs/unknown.json"], I.RESTORE_EVIDENCE),
    (["encrypted-restore-staging/op/RESTORE_READY"], I.RESTORE_EVIDENCE),
    (["schema-upgrade-foundation/journal.json", "restore-transactions/op/current-state.json"], I.UPGRADE_AND_RESTORE_EVIDENCE),
])
def test_recovery_evidence_is_only_evidence(root, names, expected):
    for name in names:
        private_file(root / name, b"untrusted operation identity")
    before = snapshot(root)
    result = ReadOnlyInstallationInventory().inspect(root)
    assert result.status is expected
    assert not result.activation_allowed
    assert snapshot(root) == before
    assert len(result.artifacts) == len(before) + 1


@pytest.mark.parametrize("name", ["schema-upgrade-foundation", "schema-upgrade-replay", "schema-upgrade-source",
                                  "restore-handoffs", "encrypted-restore-safety", "restore-staging"])
def test_empty_evidence_directories_not_empty(root, name):
    (root / name).mkdir(mode=0o700)
    assert ReadOnlyInstallationInventory().inspect(root).status in {I.UPGRADE_EVIDENCE, I.RESTORE_EVIDENCE}


@pytest.mark.parametrize("name", ["unknown", "security/unknown", "final-v4-sqlcipher-runtime-v1/unknown",
                                  ".jkm-runtime-root-v1.pending"])
def test_unknown_never_empty(root, name):
    private_file(root / name)
    assert ReadOnlyInstallationInventory().inspect(root).status is I.UNKNOWN


def test_partial_with_main(root):
    private_file(paths(root)[1].database)
    assert ReadOnlyInstallationInventory().inspect(root).status is I.PARTIAL


@pytest.mark.parametrize("attack", ["symlink", "ancestor_symlink", "fifo", "hardlink", "public", "unreadable", "wrong_type", "owner"])
def test_unsafe_structures(root, attack, monkeypatch):
    if attack == "symlink":
        (root / "security").symlink_to(root.parent, target_is_directory=True)
    elif attack == "ancestor_symlink":
        alias = root.parent / "alias"
        alias.symlink_to(root, target_is_directory=True)
        assert ReadOnlyInstallationInventory().inspect(alias).status is I.UNSAFE
        return
    elif attack == "fifo":
        os.mkfifo(root / "unknown", 0o600)
    elif attack == "hardlink":
        private_file(root / "a")
        os.link(root / "a", root / "b")
    elif attack == "wrong_type":
        (root / "app-preferences.json").mkdir(mode=0o700)
        assert ReadOnlyInstallationInventory().inspect(root).status is I.UNKNOWN
        return
    elif attack == "owner":
        monkeypatch.setattr(os, "getuid", lambda: -1)
    else:
        root.chmod(0o755 if attack == "public" else 0o000)
    try:
        assert ReadOnlyInstallationInventory().inspect(root).status is I.UNSAFE
    finally:
        root.chmod(0o700)


def test_changed_inventory(root, monkeypatch):
    port = ReadOnlyInstallationInventory()
    original = port._scan
    calls = 0
    def changed(path):
        nonlocal calls
        calls += 1
        result = original(path)
        if calls == 1:
            private_file(root / "unknown")
        return result
    monkeypatch.setattr(port, "_scan", changed)
    assert port.inspect(root).status is I.CHANGED


@pytest.fixture
def keyed(root, monkeypatch):
    store = MemoryDataMasterKeyStore()
    account = SimpleNamespace(status=AccountStatus.ACTIVE, installation_id=str(uuid.uuid4()))
    loaded = build_database_key_runtime(paths(root)[0], account_loader=lambda: account, key_store=store).open_or_create()
    metadata = paths(root)[0].keyset_metadata
    gc.collect()
    with closing(sqlite3.connect(metadata)) as db:
        assert db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
    for suffix in ("-wal", "-shm"):
        Path(str(metadata) + suffix).unlink(missing_ok=True)
    # Fixture created keys in memory only; prohibit every lifecycle mutation thereafter.
    for cls, names in [(DatabaseKeyRuntime, ["open_or_create"]),
                       (DataMasterKeyService, ["load", "load_pending", "create_pending", "activate_pending"]),
                       (SQLiteDataKeysetRepository, ["initialize", "fail_data_keyset", "activate_data_keyset", "checkpoint_truncate"]),
                       (DatabaseKeyEnvelopeService, ["create_pending", "activate", "rewrap"]),
                       (FileDatabaseKeyEnvelopeRepository, ["create", "replace"])]:
        for name in names:
            if hasattr(cls, name):
                monkeypatch.setattr(cls, name, forbidden)
    for name in ("prepare_directory", "secure_file", "secure_sqlite_files"):
        monkeypatch.setattr(PlatformFilePermissionManager, name, forbidden)
    monkeypatch.setattr(store, "create", forbidden)
    monkeypatch.setattr(store, "delete", forbidden)
    return account, store, loaded


def test_existing_keys_exact_and_no_mutations(root, keyed):
    account, store, expected = keyed
    before = snapshot(root)
    result = ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account)
    assert result.status is K.VALID
    assert result.loaded.database_key == expected.database_key
    assert result.loaded.dmk == expected.dmk
    assert result.installation_id == account.installation_id
    assert not result.loaded.first_run and not result.first_run_allowed and not result.normal_runtime_allowed
    assert snapshot(root) == before
    assert not paths(root)[1].database.exists()
    assert not (root / "schema-upgrade-foundation").exists()


@pytest.mark.parametrize("native_status,expected", [(S.NOT_FOUND, K.KEY_MISSING), (S.ACCESS_DENIED, K.ACCESS_DENIED),
    (S.CORRUPT, K.CONTEXT_CONFLICT), (S.UNSUPPORTED, K.KEYCHAIN_UNAVAILABLE), (S.ERROR, K.KEYCHAIN_UNAVAILABLE)])
def test_key_failures_no_fallback(root, keyed, native_status, expected):
    account, store, _ = keyed
    store.read_status = native_status
    before = snapshot(root)
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is expected
    assert snapshot(root) == before


def test_wrong_dmk_fingerprint(root, keyed):
    account, store, loaded = keyed
    store.values[(account.installation_id, loaded.dmk_key_id)] = b"x" * 32
    before = snapshot(root)
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is K.CONTEXT_CONFLICT
    assert snapshot(root) == before


def test_changed_key_context(root, keyed):
    account, store, _ = keyed
    with sqlite3.connect(paths(root)[0].keyset_metadata) as db:
        db.execute("UPDATE data_keysets SET database_context_id = ?", (str(uuid.uuid4()),))
    before = snapshot(root)
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is K.CONTEXT_CONFLICT
    assert snapshot(root) == before


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_immutable_key_read_rejects_sidecars(root, keyed, suffix):
    account, store, _ = keyed
    private_file(Path(str(paths(root)[0].keyset_metadata) + suffix))
    before = snapshot(root)
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is K.CONTEXT_CONFLICT
    assert snapshot(root) == before


def test_missing_envelope_and_unknown_account(root, keyed):
    account, store, _ = keyed
    paths(root)[0].envelope_registry.unlink()
    before = snapshot(root)
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is K.KEY_MISSING
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=None).status is K.INSTALLATION_UNKNOWN
    assert snapshot(root) == before


def test_unknown_installation_does_not_read_keychain(root):
    store = SimpleNamespace(read=forbidden)
    account = SimpleNamespace(status=AccountStatus.ACTIVE, installation_id=str(uuid.uuid4()))
    for name in (None, "mystery"):
        if name:
            private_file(root / name)
        assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is K.INSTALLATION_UNKNOWN


def test_key_read_concurrent_inventory_change(root, keyed, monkeypatch):
    account, store, _ = keyed
    original = store.read
    def read(**kwargs):
        private_file(root / "mystery")
        return original(**kwargs)
    monkeypatch.setattr(store, "read", read)
    result = ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account)
    assert result.status is K.INSTALLATION_UNKNOWN and result.loaded is None


def test_no_product_wiring():
    for name in ("src/desktop_app/main.py", "src/security/startup.py", "src/security/cipher_product_runtime.py"):
        text = Path(name).read_text()
        assert "existing_installation_keys" not in text and "installation_inventory" not in text


@pytest.mark.parametrize("mutation", ["tamper", "pending", "missing_dmk", "inactive_account", "read_exception"])
def test_key_context_boundaries(root, keyed, monkeypatch, mutation):
    account, store, loaded = keyed
    if mutation == "tamper":
        envelope = paths(root)[0].envelope_registry
        envelope.write_bytes(envelope.read_bytes().replace(b'"registry_auth_tag":"', b'"registry_auth_tag":"x'))
        expected = K.CONTEXT_CONFLICT
    elif mutation == "pending":
        with closing(sqlite3.connect(paths(root)[0].keyset_metadata)) as db:
            db.execute("UPDATE data_keysets SET status='pending', runtime_phase='envelope_published'")
            db.commit()
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        expected = K.CONTEXT_CONFLICT
    elif mutation == "missing_dmk":
        store.values.clear()
        expected = K.KEY_MISSING
    elif mutation == "inactive_account":
        account.status = None
        expected = K.INSTALLATION_UNKNOWN
    else:
        def unavailable(**kwargs):
            raise RuntimeError("native unavailable")
        monkeypatch.setattr(store, "read", unavailable)
        expected = K.KEYCHAIN_UNAVAILABLE
    before = snapshot(root)
    result = ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account)
    assert result.status is expected and result.loaded is None
    assert snapshot(root) == before


def test_document_container_and_nested_unknown(root):
    complete(root)
    docs = paths(root)[2]
    private_file(docs.storage_root / (str(uuid.uuid4()) + ".jkmedoc"))
    result = ReadOnlyInstallationInventory().inspect(root)
    assert result.status is I.V4_ARTIFACTS_PRESENT
    assert any(a.role == "document_container_unverified" for a in result.artifacts)
    private_file(docs.storage_root / "unexpected" / (str(uuid.uuid4()) + ".jkmedoc"))
    assert ReadOnlyInstallationInventory().inspect(root).status is I.UNKNOWN


def test_unreadable_scandir_not_downgraded(root, monkeypatch):
    def denied(fd):
        raise PermissionError
    monkeypatch.setattr(os, "listdir", denied)
    assert ReadOnlyInstallationInventory().inspect(root).status is I.UNSAFE


def test_recovery_paths_untouched_by_key_load(root, keyed):
    account, store, _ = keyed
    for name in ("schema-upgrade-foundation/journal.json", "schema-upgrade-replay/anchor.json",
                 "restore-handoffs/untrusted.json"):
        private_file(root / name)
    before = snapshot(root)
    result = ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account)
    assert result.status is K.VALID  # Keys alone never validate any recovery operation.
    assert not result.activation_allowed and not result.normal_runtime_allowed
    assert snapshot(root) == before


def test_authenticated_pending_envelope_refused(root, keyed):
    account, store, loaded = keyed
    path = paths(root)[0].envelope_registry
    repository = FileDatabaseKeyEnvelopeRepository(path, None)
    auth_key = derive_database_key_registry_auth_key(loaded.dmk, database_context_id=loaded.database_context_id)
    current = repository.load(auth_key)
    pending = replace(current[0], lifecycle_status=DatabaseKeyEnvelopeStatus.PENDING)
    path.write_bytes(repository._encode_registry(loaded.database_context_id, 1, (pending,), auth_key))
    before = snapshot(root)
    assert ExistingInstallationKeys(key_store=store).load_existing(root, authenticated_account=account).status is K.CONTEXT_CONFLICT
    assert snapshot(root) == before
