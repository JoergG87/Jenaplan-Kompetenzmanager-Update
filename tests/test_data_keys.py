from __future__ import annotations

import ctypes
import hashlib
from pathlib import Path
import secrets
import sqlite3
import uuid

import pytest

from src.desktop_app.runtime import prepare_security_runtime_storage
from src.security.data_keys import (
    DATA_MASTER_KEY_BYTES,
    DATA_MASTER_KEY_PURPOSE,
    KEY_ENVELOPE_FORMAT_VERSION,
    DataKeyset,
    DataKeysetStatus,
    DataMasterKeyLifecycleError,
    DataMasterKeyReadResult,
    DataMasterKeyService,
    DataMasterKeyStoreStatus,
    KeyEnvelope,
    data_master_key_fingerprint,
)
from src.security.infrastructure.data_keyset_repository import SQLiteDataKeysetRepository
from src.security.infrastructure.data_master_key_store import (
    MacOSDataMasterKeyStore,
    UnsupportedDataMasterKeyStore,
)
from src.security.infrastructure.system import PlatformFilePermissionManager
from src.security.startup import build_security_runtime
from src.security.domain import SecurityStoreError


PASSWORD = "eine lange sichere DMK Testpassphrase"
NEW_PASSWORD = "eine andere lange sichere DMK Testpassphrase"


class RecordingRandom:
    def __init__(self) -> None:
        self.counter = 0
        self.byte_lengths: list[int] = []

    def bytes(self, length: int) -> bytes:
        self.byte_lengths.append(length)
        self.counter += 1
        return hashlib.sha256(f"dmk-{self.counter}".encode("ascii")).digest()[:length]

    def uuid4(self) -> str:
        self.counter += 1
        raw = bytearray(hashlib.sha256(f"id-{self.counter}".encode("ascii")).digest()[:16])
        raw[6] = (raw[6] & 0x0F) | 0x40
        raw[8] = (raw[8] & 0x3F) | 0x80
        return str(uuid.UUID(bytes=bytes(raw)))


class MemoryDataMasterKeyStore:
    supported = True

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], bytes] = {}
        self.read_status: DataMasterKeyStoreStatus | None = None
        self.fail_create = False
        self.fail_delete = False

    def create(
        self, *, installation_id: str, key_id: str, key_material: bytes
    ) -> None:
        if self.fail_create:
            raise RuntimeError("simulated platform error")
        identity = (installation_id, key_id)
        if identity in self.values:
            raise RuntimeError("duplicate")
        self.values[identity] = bytes(key_material)

    def read(
        self, *, installation_id: str, key_id: str
    ) -> DataMasterKeyReadResult:
        if self.read_status is not None:
            return DataMasterKeyReadResult(self.read_status)
        material = self.values.get((installation_id, key_id))
        if material is None:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.NOT_FOUND)
        return DataMasterKeyReadResult(DataMasterKeyStoreStatus.SUCCESS, material)

    def delete(self, *, installation_id: str, key_id: str) -> bool:
        if self.fail_delete:
            raise RuntimeError("simulated platform error")
        return self.values.pop((installation_id, key_id), None) is not None


def make_environment(tmp_path: Path):
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    runtime.service.enroll_local_account(PASSWORD)
    key_repository = SQLiteDataKeysetRepository(
        paths.security / "data-keysets.sqlite", PlatformFilePermissionManager()
    )
    key_repository.initialize()
    key_store = MemoryDataMasterKeyStore()
    random_source = RecordingRandom()
    service = DataMasterKeyService(
        repository=key_repository,
        key_store=key_store,
        random_source=random_source,
        account_loader=runtime.repository.load_account,
    )
    return runtime, service, key_repository, key_store, random_source


def test_provision_creates_256_bit_dmk_and_persists_only_metadata(tmp_path: Path) -> None:
    runtime, service, key_repository, key_store, random_source = make_environment(tmp_path)
    loaded = service.provision()
    account = runtime.repository.load_account()

    assert random_source.byte_lengths == [DATA_MASTER_KEY_BYTES]
    assert len(loaded.key_material) == DATA_MASTER_KEY_BYTES
    assert key_store.values[(account.installation_id, loaded.key_id)] == loaded.key_material
    keyset = key_repository.active_data_keyset()
    assert keyset is not None
    assert keyset.status is DataKeysetStatus.ACTIVE
    assert keyset.generation == 1
    assert keyset.fingerprint_sha256 == data_master_key_fingerprint(loaded.key_material)
    assert loaded.key_material.hex() not in repr(loaded)

    for database_path in (runtime.repository.database_path, key_repository.database_path):
        database_bytes = database_path.read_bytes()
        assert loaded.key_material not in database_bytes
        assert loaded.key_material.hex().encode("ascii") not in database_bytes
    with sqlite3.connect(key_repository.database_path) as connection:
        columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(data_keysets)"))
        assert columns == (
            "key_id",
            "generation",
            "status",
            "fingerprint_sha256",
            "runtime_phase",
            "database_context_id",
        )


def test_load_survives_service_restart_and_wrong_binding_is_not_found(tmp_path: Path) -> None:
    runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    original = service.provision()
    restarted = DataMasterKeyService(
        repository=SQLiteDataKeysetRepository(
            key_repository.database_path, PlatformFilePermissionManager()
        ),
        key_store=key_store,
        random_source=RecordingRandom(),
        account_loader=runtime.repository.load_account,
    )
    reloaded = restarted.load()
    assert reloaded.key_id == original.key_id
    assert reloaded.key_material == original.key_material
    assert key_store.read(
        installation_id=str(uuid.uuid4()), key_id=original.key_id
    ).status is DataMasterKeyStoreStatus.NOT_FOUND
    assert key_store.read(
        installation_id=runtime.repository.load_account().installation_id,
        key_id=str(uuid.uuid4()),
    ).status is DataMasterKeyStoreStatus.NOT_FOUND


def test_delete_revokes_metadata_and_removes_platform_secret(tmp_path: Path) -> None:
    _runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    loaded = service.provision()
    assert service.delete() is True
    assert service.delete() is False
    assert key_store.values == {}
    assert key_repository.active_data_keyset() is None
    with sqlite3.connect(key_repository.database_path) as connection:
        assert connection.execute(
            "SELECT status FROM data_keysets WHERE key_id = ?", (loaded.key_id,)
        ).fetchone()[0] == "revoked"


def test_platform_create_and_delete_failures_are_sanitized_and_fail_closed(
    tmp_path: Path,
) -> None:
    _runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    key_store.fail_create = True
    with pytest.raises(DataMasterKeyLifecycleError) as created:
        service.provision()
    assert created.value.code == "data_master_key_store_create_failed"
    assert key_repository.active_data_keyset() is None
    with sqlite3.connect(key_repository.database_path) as connection:
        assert connection.execute("SELECT status FROM data_keysets").fetchone()[0] == "failed"

    key_store.fail_create = False
    loaded = service.provision()
    key_store.fail_delete = True
    with pytest.raises(DataMasterKeyLifecycleError) as deleted:
        service.delete()
    assert deleted.value.code == "data_master_key_store_delete_failed"
    assert any(identity[1] == loaded.key_id for identity in key_store.values)
    assert key_repository.active_data_keyset() is None
    key_store.fail_delete = False
    assert service.delete() is True
    assert key_store.values == {}


def test_unsupported_delete_revokes_metadata_but_never_reports_success(
    tmp_path: Path,
) -> None:
    runtime, service, key_repository, _key_store, random_source = make_environment(tmp_path)
    loaded = service.provision()
    unsupported = DataMasterKeyService(
        repository=key_repository,
        key_store=UnsupportedDataMasterKeyStore(),
        random_source=random_source,
        account_loader=runtime.repository.load_account,
    )
    with pytest.raises(DataMasterKeyLifecycleError) as caught:
        unsupported.delete()
    assert caught.value.code == "data_master_key_store_unsupported"
    assert key_repository.active_data_keyset() is None
    assert any(
        keyset.key_id == loaded.key_id
        for keyset in key_repository.data_keysets_for_cleanup()
    )


def test_access_denial_keeps_active_metadata_for_retry(tmp_path: Path) -> None:
    _runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    loaded = service.provision()
    key_store.read_status = DataMasterKeyStoreStatus.ACCESS_DENIED
    with pytest.raises(DataMasterKeyLifecycleError) as caught:
        service.load()
    assert caught.value.code == "data_master_key_access_denied"
    assert key_repository.active_data_keyset().key_id == loaded.key_id


def test_transient_read_error_keeps_active_metadata_for_retry(tmp_path: Path) -> None:
    _runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    loaded = service.provision()
    key_store.read_status = DataMasterKeyStoreStatus.ERROR
    with pytest.raises(DataMasterKeyLifecycleError) as caught:
        service.load()
    assert caught.value.code == "data_master_key_store_read_failed"
    assert key_repository.active_data_keyset().key_id == loaded.key_id
    key_store.read_status = None
    assert service.load() == loaded


@pytest.mark.parametrize(
    "corruption", [b"short", secrets.token_bytes(DATA_MASTER_KEY_BYTES)]
)
def test_corrupt_keychain_entry_marks_keyset_failed(
    tmp_path: Path, corruption: bytes
) -> None:
    runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    loaded = service.provision()
    account = runtime.repository.load_account()
    key_store.values[(account.installation_id, loaded.key_id)] = corruption
    with pytest.raises(DataMasterKeyLifecycleError) as caught:
        service.load()
    assert caught.value.code == "data_master_key_corrupt"
    assert key_store.values[(account.installation_id, loaded.key_id)] == corruption
    assert key_repository.active_data_keyset() is None
    with sqlite3.connect(key_repository.database_path) as connection:
        assert connection.execute(
            "SELECT status FROM data_keysets WHERE key_id = ?", (loaded.key_id,)
        ).fetchone()[0] == "failed"


def test_tampered_fingerprint_never_deletes_matching_platform_dmk(
    tmp_path: Path,
) -> None:
    runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    loaded = service.provision()
    account = runtime.repository.load_account()
    identity = (account.installation_id, loaded.key_id)
    original_material = key_store.values[identity]
    with sqlite3.connect(key_repository.database_path) as connection:
        connection.execute(
            "UPDATE data_keysets SET fingerprint_sha256 = ? WHERE key_id = ?",
            (hashlib.sha256(b"tampered-metadata").hexdigest(), loaded.key_id),
        )
    with pytest.raises(DataMasterKeyLifecycleError) as caught:
        service.load()
    assert caught.value.code == "data_master_key_corrupt"
    assert key_store.values[identity] == original_material


def test_restart_completes_pending_keyset_with_matching_platform_secret(tmp_path: Path) -> None:
    runtime, service, key_repository, key_store, _random = make_environment(tmp_path)
    account = runtime.repository.load_account()
    material = secrets.token_bytes(DATA_MASTER_KEY_BYTES)
    key_id = str(uuid.uuid4())
    pending = DataKeyset(
        key_id=key_id,
        generation=1,
        status=DataKeysetStatus.PENDING,
        fingerprint_sha256=data_master_key_fingerprint(material),
    )
    key_repository.prepare_data_keyset(pending)
    key_store.create(
        installation_id=account.installation_id,
        key_id=key_id,
        key_material=material,
    )
    loaded = service.load()
    assert loaded.key_id == key_id
    assert loaded.key_material == material
    assert key_repository.active_data_keyset().status is DataKeysetStatus.ACTIVE


def test_password_change_does_not_change_dmk_or_keyset(tmp_path: Path) -> None:
    runtime, service, key_repository, _key_store, _random = make_environment(tmp_path)
    before = service.provision()
    keyset_before = key_repository.active_data_keyset()
    runtime.service.change_password(PASSWORD, NEW_PASSWORD)
    after = service.load()
    assert after == before
    assert key_repository.active_data_keyset() == keyset_before


def test_keyset_status_updates_do_not_change_rc_security_store(tmp_path: Path) -> None:
    runtime, service, key_repository, _key_store, _random = make_environment(tmp_path)
    rc_store_before = runtime.repository.database_path.read_bytes()
    loaded = service.provision()
    assert service.delete() is True
    replacement = service.provision()
    assert replacement.generation == loaded.generation + 1
    assert runtime.repository.database_path.read_bytes() == rc_store_before
    assert key_repository.active_data_keyset().key_id == replacement.key_id


def test_existing_unknown_keyset_store_version_is_rejected_without_migration(
    tmp_path: Path,
) -> None:
    _runtime, _service, key_repository, _key_store, _random = make_environment(tmp_path)
    with sqlite3.connect(key_repository.database_path) as connection:
        connection.execute("PRAGMA user_version = 3")
    before = key_repository.database_path.read_bytes()
    reopened = SQLiteDataKeysetRepository(
        key_repository.database_path, PlatformFilePermissionManager()
    )
    with pytest.raises(SecurityStoreError, match="data_keyset_store_version_invalid"):
        reopened.initialize()
    assert key_repository.database_path.read_bytes() == before


def test_corrupt_metadata_entry_is_rejected_fail_closed(tmp_path: Path) -> None:
    _runtime, service, key_repository, _key_store, _random = make_environment(tmp_path)
    service.provision()
    with sqlite3.connect(key_repository.database_path) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute("UPDATE data_keysets SET status = 'unknown'")
    with pytest.raises(SecurityStoreError, match="data_keyset_store_invalid"):
        key_repository.active_data_keyset()


def test_macos_keychain_adapter_uses_separate_namespace_and_installation_binding() -> None:
    class Library:
        def __init__(self) -> None:
            self.values: dict[tuple[bytes, bytes], bytes] = {}
            self.buffers: list[object] = []
            self.create_status: int | None = None
            self.read_status: int | None = None
            self.delete_status: int | None = None
            self.free_calls = 0

        def jkm_keychain_create(self, service, account, buffer, length):
            if self.create_status is not None:
                return self.create_status
            identity = (service, account)
            if identity in self.values:
                return -25299
            self.values[identity] = bytes(buffer[:length])
            return 0

        def jkm_keychain_read(self, service, account, pointer_out, length_out):
            if self.read_status is not None:
                return self.read_status
            material = self.values.get((service, account))
            if material is None:
                return -25300
            buffer = (ctypes.c_uint8 * len(material)).from_buffer_copy(material)
            self.buffers.append(buffer)
            ctypes.cast(
                pointer_out, ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8))
            )[0] = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint8))
            ctypes.cast(length_out, ctypes.POINTER(ctypes.c_size_t))[0] = len(material)
            return 0

        def jkm_keychain_delete(self, service, account):
            if self.delete_status is not None:
                return self.delete_status
            return 0 if self.values.pop((service, account), None) is not None else -25300

        def jkm_secret_free(self, _pointer, _length):
            self.free_calls += 1

    class Bridge:
        def __init__(self) -> None:
            self.library = Library()

    bridge = Bridge()
    adapter = MacOSDataMasterKeyStore(bridge)
    installation_id = str(uuid.uuid4())
    key_id = str(uuid.uuid4())
    material = secrets.token_bytes(DATA_MASTER_KEY_BYTES)
    adapter.create(
        installation_id=installation_id, key_id=key_id, key_material=material
    )
    assert {
        service for service, _account in bridge.library.values
    } == {b"de.jenaplan.kompetenzmanager.data-master-key"}
    assert adapter.read(
        installation_id=installation_id, key_id=key_id
    ).key_material == material
    assert adapter.read(
        installation_id=str(uuid.uuid4()), key_id=key_id
    ).status is DataMasterKeyStoreStatus.NOT_FOUND
    bridge.library.read_status = -25308
    assert adapter.read(
        installation_id=installation_id, key_id=key_id
    ).status is DataMasterKeyStoreStatus.ACCESS_DENIED
    bridge.library.read_status = -1
    assert adapter.read(
        installation_id=installation_id, key_id=key_id
    ).status is DataMasterKeyStoreStatus.ERROR
    bridge.library.read_status = -26275
    assert adapter.read(
        installation_id=installation_id, key_id=key_id
    ).status is DataMasterKeyStoreStatus.CORRUPT
    bridge.library.read_status = None
    bridge.library.values[
        (b"de.jenaplan.kompetenzmanager.data-master-key", f"v1:{installation_id}:{key_id}".encode("ascii"))
    ] = b"short"
    assert adapter.read(
        installation_id=installation_id, key_id=key_id
    ).status is DataMasterKeyStoreStatus.CORRUPT
    assert bridge.library.free_calls >= 2
    bridge.library.values[
        (b"de.jenaplan.kompetenzmanager.data-master-key", f"v1:{installation_id}:{key_id}".encode("ascii"))
    ] = material
    with pytest.raises(SecurityStoreError, match="data_master_key_already_exists"):
        adapter.create(
            installation_id=installation_id, key_id=key_id, key_material=material
        )
    bridge.library.create_status = -1
    with pytest.raises(SecurityStoreError, match="data_master_key_create_failed"):
        adapter.create(
            installation_id=installation_id,
            key_id=str(uuid.uuid4()),
            key_material=material,
        )
    bridge.library.create_status = -25308
    with pytest.raises(SecurityStoreError, match="data_master_key_access_denied"):
        adapter.create(
            installation_id=installation_id,
            key_id=str(uuid.uuid4()),
            key_material=material,
        )
    bridge.library.create_status = None
    bridge.library.delete_status = -1
    with pytest.raises(SecurityStoreError, match="data_master_key_delete_failed"):
        adapter.delete(installation_id=installation_id, key_id=key_id)
    bridge.library.delete_status = None
    assert adapter.delete(installation_id=installation_id, key_id=key_id) is True
    assert adapter.delete(installation_id=installation_id, key_id=key_id) is False


def test_key_envelope_serializes_already_protected_material_canonically() -> None:
    protected = secrets.token_bytes(32)
    envelope = KeyEnvelope(
        format_version=KEY_ENVELOPE_FORMAT_VERSION,
        key_id=str(uuid.uuid4()),
        purpose=DATA_MASTER_KEY_PURPOSE,
        algorithm="dpapi-ng-v1",
        metadata={"protection_scope": "current-user", "provider": "windows"},
        protected_key_material=protected,
    )
    encoded = envelope.to_bytes()
    assert KeyEnvelope.from_bytes(encoded) == envelope
    assert protected.hex() not in repr(envelope)
    assert protected not in encoded
    with pytest.raises(DataMasterKeyLifecycleError):
        KeyEnvelope.from_bytes(encoded + b" ")
    oversized = KeyEnvelope(
        format_version=KEY_ENVELOPE_FORMAT_VERSION,
        key_id=str(uuid.uuid4()),
        purpose=DATA_MASTER_KEY_PURPOSE,
        algorithm="dpapi-ng-v1",
        metadata={},
        protected_key_material=b"x" * (16 * 1024),
    )
    with pytest.raises(DataMasterKeyLifecycleError, match="key_envelope_size_invalid"):
        oversized.to_bytes()
