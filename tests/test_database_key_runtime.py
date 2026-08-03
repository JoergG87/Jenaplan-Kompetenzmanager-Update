from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import subprocess
import sys
from types import SimpleNamespace
import uuid

import pytest

from src.security.data_keys import (
    DATA_MASTER_KEY_BYTES,
    DataMasterKeyLifecycleError,
    DataMasterKeyReadResult,
    DataMasterKeyService,
    DataMasterKeyStoreStatus,
)
from src.security.database_key_runtime import (
    DMK_DATABASE_KEY_RUNTIME_GATE_ENV,
    DMK_DATABASE_KEY_RUNTIME_MARKER,
    DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES,
    DMK_DATABASE_KEY_RUNTIME_ROOT_ENV,
    DatabaseKeyRuntimeDecisionState,
    build_database_key_runtime,
    DatabaseKeyRuntimeGate,
    run_gated_database_key_runtime,
)
from src.security.database_keys import (
    DatabaseKeyEnvelopeStatus,
    derive_database_key_registry_auth_key,
)
from src.security.domain import AccountStatus
from src.security.infrastructure.database_key_envelope_repository import (
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.data_keyset_repository import (
    SQLiteDataKeysetRepository,
)
from src.security.infrastructure.system import PlatformFilePermissionManager


class MemoryDataMasterKeyStore:
    def __init__(self) -> None:
        self.supported = True
        self.values: dict[tuple[str, str], bytes] = {}
        self.read_status: DataMasterKeyStoreStatus | None = None
        self.create_calls = 0

    def create(
        self, *, installation_id: str, key_id: str, key_material: bytes
    ) -> None:
        self.create_calls += 1
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
        return self.values.pop((installation_id, key_id), None) is not None


class RecordingRandom:
    def __init__(self) -> None:
        self.byte_lengths: list[int] = []
        self.counter = 0

    def bytes(self, length: int) -> bytes:
        self.byte_lengths.append(length)
        self.counter += 1
        chunks = bytearray()
        while len(chunks) < length:
            chunks.extend(
                hashlib.sha256(
                    f"runtime-random-{self.counter}-{len(chunks)}".encode("ascii")
                ).digest()
            )
        return bytes(chunks[:length])

    def uuid4(self) -> str:
        self.counter += 1
        raw = bytearray(
            hashlib.sha256(f"runtime-uuid-{self.counter}".encode("ascii")).digest()[:16]
        )
        raw[6] = (raw[6] & 0x0F) | 0x40
        raw[8] = (raw[8] & 0x3F) | 0x80
        return str(uuid.UUID(bytes=bytes(raw)))


class SimulatedCrash(RuntimeError):
    pass


def _root(tmp_path: Path) -> Path:
    root = tmp_path / f"jkm-dmk-database-key-runtime-{uuid.uuid4()}"
    root.mkdir(mode=0o700)
    marker = root / DMK_DATABASE_KEY_RUNTIME_MARKER
    marker.write_bytes(DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES)
    marker.chmod(0o600)
    return root


def _environment(root: Path) -> dict[str, str]:
    return {
        DMK_DATABASE_KEY_RUNTIME_GATE_ENV: "1",
        DMK_DATABASE_KEY_RUNTIME_ROOT_ENV: str(root),
    }


def _account_loader(installation_id: str):
    account = SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=installation_id,
        password="ignored-by-dmk-runtime",
    )
    return lambda: account


def _run(root: Path, store, random_source, installation_id: str, **kwargs):
    return run_gated_database_key_runtime(
        account_loader=_account_loader(installation_id),
        environ=_environment(root),
        key_store=store,
        random_source=random_source,
        **kwargs,
    )


def test_first_run_restart_and_exact_database_key_recovery(tmp_path: Path) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    random_source = RecordingRandom()

    first = _run(root, store, random_source, installation_id)
    restarted = _run(root, store, RecordingRandom(), installation_id)

    assert first.state is DatabaseKeyRuntimeDecisionState.ACTIVE
    assert restarted.state is DatabaseKeyRuntimeDecisionState.ACTIVE
    assert first.loaded is not None and restarted.loaded is not None
    assert first.loaded.first_run is True
    assert restarted.loaded.first_run is False
    assert first.loaded.dmk.key_material == restarted.loaded.dmk.key_material
    assert (
        first.loaded.database_key.key_material
        == restarted.loaded.database_key.key_material
    )
    assert first.loaded.dmk.key_material != first.loaded.database_key.key_material
    assert first.loaded.database_context_id == restarted.loaded.database_context_id
    assert first.loaded.dmk_key_id == restarted.loaded.dmk_key_id
    assert first.loaded.dmk_generation == restarted.loaded.dmk_generation == 1
    assert first.loaded.database_key_id == restarted.loaded.database_key_id
    assert first.loaded.database_key_generation == restarted.loaded.database_key_generation == 1
    assert (
        first.loaded.dmk_fingerprint_sha256
        == restarted.loaded.dmk_fingerprint_sha256
    )
    assert (
        first.loaded.database_key_fingerprint_sha256
        == restarted.loaded.database_key_fingerprint_sha256
    )
    assert random_source.byte_lengths.count(DATA_MASTER_KEY_BYTES) == 2
    assert random_source.byte_lengths.count(12) == 2
    assert store.create_calls == 1
    generated_names = {path.name for path in root.rglob("*")}
    assert "kompetenzmanager.sqlite" not in generated_names
    assert not any(name.endswith(".sqlcipher") for name in generated_names)


def test_password_is_not_an_input_and_secrets_never_reach_files_logs_or_errors(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    caplog.set_level(logging.DEBUG)
    first = _run(root, store, RecordingRandom(), installation_id)
    assert first.loaded is not None

    account = SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=installation_id,
        password="a completely different password",
    )
    restarted = run_gated_database_key_runtime(
        account_loader=lambda: account,
        environ=_environment(root),
        key_store=store,
        random_source=RecordingRandom(),
    )
    assert restarted.loaded is not None
    assert restarted.loaded.database_key == first.loaded.database_key

    dmk = first.loaded.dmk.key_material
    database_key = first.loaded.database_key.key_material
    for path in (root / "security-key-runtime-v1").iterdir():
        if path.is_file():
            raw = path.read_bytes()
            for secret in (dmk, database_key):
                assert secret not in raw
                assert secret.hex().encode("ascii") not in raw
    combined = "\n".join(record.getMessage() for record in caplog.records)
    assert dmk.hex() not in combined
    assert database_key.hex() not in combined
    assert dmk.hex() not in repr(first)
    assert database_key.hex() not in repr(first)

    metadata = root / "security-key-runtime-v1"
    assert stat.S_IMODE(metadata.stat().st_mode) == 0o700
    for path in metadata.iterdir():
        if path.is_file():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_gate_off_does_not_resolve_paths_call_account_or_write(tmp_path: Path) -> None:
    missing = tmp_path / "jkm-dmk-database-key-runtime-missing"
    called = False

    def account_loader():
        nonlocal called
        called = True
        raise AssertionError

    decision = run_gated_database_key_runtime(
        account_loader=account_loader,
        environ={DMK_DATABASE_KEY_RUNTIME_ROOT_ENV: str(missing)},
    )
    assert decision.state is DatabaseKeyRuntimeDecisionState.DISABLED
    assert called is False
    assert not missing.exists()


def test_unavailable_keychain_before_publish_is_retryable_without_key_regeneration(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    store.supported = False
    random_source = RecordingRandom()

    unavailable = _run(root, store, random_source, installation_id)
    assert unavailable.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert unavailable.error_code == "data_master_key_store_unsupported"
    assert unavailable.retryable is True
    assert store.create_calls == 0
    assert random_source.byte_lengths == []
    assert not (root / "security-key-runtime-v1").exists()

    store.supported = True
    retried = _run(root, store, random_source, installation_id)
    assert retried.state is DatabaseKeyRuntimeDecisionState.ACTIVE
    assert retried.loaded is not None
    assert store.create_calls == 1


@pytest.mark.parametrize(
    ("boundary", "restart_state", "expected_error"),
    [
        (
            "before_keychain_publish",
            DatabaseKeyRuntimeDecisionState.BLOCKED,
            "pending_data_master_key_not_found",
        ),
        (
            "after_keychain_publish_before_keyset_persistence",
            DatabaseKeyRuntimeDecisionState.ACTIVE,
            None,
        ),
        (
            "after_keyset_pending",
            DatabaseKeyRuntimeDecisionState.ACTIVE,
            None,
        ),
        (
            "after_database_key_generation",
            DatabaseKeyRuntimeDecisionState.BLOCKED,
            "database_key_envelope_missing_after_generation",
        ),
        (
            "after_envelope_publish",
            DatabaseKeyRuntimeDecisionState.ACTIVE,
            None,
        ),
        (
            "before_keyset_activation",
            DatabaseKeyRuntimeDecisionState.ACTIVE,
            None,
        ),
        (
            "after_keyset_activation",
            DatabaseKeyRuntimeDecisionState.ACTIVE,
            None,
        ),
    ],
)
def test_crash_restart_at_every_publish_boundary(
    tmp_path: Path,
    boundary: str,
    restart_state: DatabaseKeyRuntimeDecisionState,
    expected_error: str | None,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    random_source = RecordingRandom()
    crashed = False

    def fault_hook(current: str) -> None:
        nonlocal crashed
        if current == boundary and not crashed:
            crashed = True
            raise SimulatedCrash(boundary)

    with pytest.raises(SimulatedCrash, match=boundary):
        _run(
            root,
            store,
            random_source,
            installation_id,
            fault_hook=fault_hook,
        )
    creates_before_restart = store.create_calls
    random_before_restart = tuple(random_source.byte_lengths)

    restarted = _run(root, store, random_source, installation_id)
    assert restarted.state is restart_state
    assert restarted.error_code == expected_error
    assert store.create_calls == creates_before_restart
    if restart_state is DatabaseKeyRuntimeDecisionState.BLOCKED:
        assert tuple(random_source.byte_lengths) == random_before_restart


def test_generic_dmk_load_cannot_activate_incomplete_combined_runtime(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    paths = DatabaseKeyRuntimeGate.require_paths(str(root))

    def fault_hook(boundary: str) -> None:
        if boundary == "before_keyset_activation":
            raise SimulatedCrash(boundary)

    runtime = build_database_key_runtime(
        paths,
        account_loader=_account_loader(installation_id),
        key_store=store,
        random_source=RecordingRandom(),
        fault_hook=fault_hook,
    )
    with pytest.raises(SimulatedCrash):
        runtime.open_or_create()

    repository = SQLiteDataKeysetRepository(
        paths.keyset_metadata, PlatformFilePermissionManager()
    )
    generic = DataMasterKeyService(
        repository=repository,
        key_store=store,
        random_source=RecordingRandom(),
        account_loader=_account_loader(installation_id),
    )
    with pytest.raises(DataMasterKeyLifecycleError) as caught:
        generic.load()
    assert caught.value.code == "pending_data_master_key_runtime_incomplete"
    assert repository.active_data_keyset() is None


def test_missing_wrong_and_access_denied_dmk_fail_without_regeneration(
    tmp_path: Path,
) -> None:
    installation_id = str(uuid.uuid4())

    denied_root = _root(tmp_path)
    denied_store = MemoryDataMasterKeyStore()
    denied_first = _run(
        denied_root, denied_store, RecordingRandom(), installation_id
    )
    assert denied_first.loaded is not None
    denied_store.read_status = DataMasterKeyStoreStatus.ACCESS_DENIED
    denied = _run(denied_root, denied_store, RecordingRandom(), installation_id)
    assert denied.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert denied.error_code == "data_master_key_access_denied"
    assert denied.retryable is True
    denied_store.read_status = None
    retried = _run(denied_root, denied_store, RecordingRandom(), installation_id)
    assert retried.state is DatabaseKeyRuntimeDecisionState.ACTIVE
    assert retried.loaded is not None
    assert retried.loaded.database_key == denied_first.loaded.database_key

    missing_root = _root(tmp_path)
    missing_store = MemoryDataMasterKeyStore()
    missing_first = _run(
        missing_root, missing_store, RecordingRandom(), installation_id
    )
    assert missing_first.loaded is not None
    missing_identity = (installation_id, missing_first.loaded.dmk_key_id)
    missing_store.values.pop(missing_identity)
    missing = _run(
        missing_root, missing_store, RecordingRandom(), installation_id
    )
    assert missing.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert missing.error_code == "data_master_key_not_found"
    assert missing_store.create_calls == 1

    wrong_root = _root(tmp_path)
    wrong_store = MemoryDataMasterKeyStore()
    wrong_first = _run(wrong_root, wrong_store, RecordingRandom(), installation_id)
    assert wrong_first.loaded is not None
    wrong_identity = (installation_id, wrong_first.loaded.dmk_key_id)
    wrong_store.values[wrong_identity] = secrets.token_bytes(DATA_MASTER_KEY_BYTES)
    wrong = _run(wrong_root, wrong_store, RecordingRandom(), installation_id)
    assert wrong.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert wrong.error_code == "data_master_key_corrupt"
    assert wrong_store.create_calls == 1


def test_corrupt_keyset_tampered_registry_and_wrong_context_block(
    tmp_path: Path,
) -> None:
    installation_id = str(uuid.uuid4())

    corrupt_root = _root(tmp_path)
    corrupt_store = MemoryDataMasterKeyStore()
    corrupt = _run(corrupt_root, corrupt_store, RecordingRandom(), installation_id)
    assert corrupt.loaded is not None
    keyset_path = corrupt_root / "security-key-runtime-v1" / "data-keysets.sqlite"
    keyset_path.write_bytes(b"not-a-sqlite-store")
    corrupted = _run(corrupt_root, corrupt_store, RecordingRandom(), installation_id)
    assert corrupted.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert corrupted.error_code in {
        "data_keyset_store_identity_invalid",
        "data_keyset_store_invalid",
    }

    registry_root = _root(tmp_path)
    registry_store = MemoryDataMasterKeyStore()
    registry = _run(registry_root, registry_store, RecordingRandom(), installation_id)
    assert registry.loaded is not None
    registry_path = (
        registry_root
        / "security-key-runtime-v1"
        / "database-key-envelopes-v1.json"
    )
    payload = bytearray(registry_path.read_bytes())
    payload[-2] = ord("A") if payload[-2] != ord("A") else ord("B")
    registry_path.write_bytes(payload)
    tampered = _run(registry_root, registry_store, RecordingRandom(), installation_id)
    assert tampered.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert tampered.error_code in {
        "database_key_envelope_registry_authentication_failed",
        "database_key_envelope_format_invalid",
        "database_key_envelope_not_canonical",
        "database_key_envelope_registry_invalid",
    }

    context_root = _root(tmp_path)
    context_store = MemoryDataMasterKeyStore()
    context = _run(context_root, context_store, RecordingRandom(), installation_id)
    assert context.loaded is not None
    context_keyset = context_root / "security-key-runtime-v1" / "data-keysets.sqlite"
    with sqlite3.connect(context_keyset) as connection:
        connection.execute(
            "UPDATE data_keysets SET database_context_id = ?",
            (str(uuid.uuid4()),),
        )
    mismatch = _run(context_root, context_store, RecordingRandom(), installation_id)
    assert mismatch.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert mismatch.error_code == "database_key_context_mismatch"


def test_runtime_rejects_aead_tampering_and_unknown_registry_version(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    first = _run(root, store, RecordingRandom(), installation_id)
    assert first.loaded is not None
    paths = DatabaseKeyRuntimeGate.require_paths(str(root))
    repository = FileDatabaseKeyEnvelopeRepository(
        paths.envelope_registry, PlatformFilePermissionManager()
    )
    auth_key = derive_database_key_registry_auth_key(
        first.loaded.dmk,
        database_context_id=first.loaded.database_context_id,
    )
    envelopes = repository.load(auth_key)
    original = envelopes[0]
    changed = bytearray(original.ciphertext)
    changed[-1] ^= 1
    repository.replace(envelopes, (replace(original, ciphertext=bytes(changed)),), auth_key)
    tampered = _run(root, store, RecordingRandom(), installation_id)
    assert tampered.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert tampered.error_code == "database_key_envelope_authentication_failed"

    version_root = _root(tmp_path)
    version_store = MemoryDataMasterKeyStore()
    versioned = _run(version_root, version_store, RecordingRandom(), installation_id)
    assert versioned.loaded is not None
    version_path = (
        version_root
        / "security-key-runtime-v1"
        / "database-key-envelopes-v1.json"
    )
    payload = json.loads(version_path.read_text(encoding="ascii"))
    payload["registry_version"] = 2
    version_auth_key = derive_database_key_registry_auth_key(
        versioned.loaded.dmk,
        database_context_id=versioned.loaded.database_context_id,
    )
    payload.pop("registry_auth_tag")
    authenticated = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    payload["registry_auth_tag"] = base64.urlsafe_b64encode(
        hmac.new(
            version_auth_key.key_material,
            authenticated,
            hashlib.sha256,
        ).digest()
    ).rstrip(b"=").decode("ascii")
    version_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )
    unknown = _run(version_root, version_store, RecordingRandom(), installation_id)
    assert unknown.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert unknown.error_code == "database_key_envelope_registry_version_unsupported"


def test_only_one_active_envelope_is_present_after_restart(tmp_path: Path) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    first = _run(root, store, RecordingRandom(), installation_id)
    assert first.loaded is not None
    paths = DatabaseKeyRuntimeGate.require_paths(str(root))
    repository = FileDatabaseKeyEnvelopeRepository(
        paths.envelope_registry, PlatformFilePermissionManager()
    )
    auth_key = derive_database_key_registry_auth_key(
        first.loaded.dmk,
        database_context_id=first.loaded.database_context_id,
    )
    envelopes = repository.load(auth_key)
    assert [
        envelope.lifecycle_status for envelope in envelopes
    ] == [DatabaseKeyEnvelopeStatus.ACTIVE]


def test_multiple_active_keysets_are_rejected_as_corrupt_metadata(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    first = _run(root, store, RecordingRandom(), installation_id)
    assert first.loaded is not None
    keyset_path = root / "security-key-runtime-v1" / "data-keysets.sqlite"
    with sqlite3.connect(keyset_path) as connection:
        connection.execute("DROP INDEX one_active_data_keyset")
        connection.execute(
            "INSERT INTO data_keysets VALUES (?, 2, 'active', ?, 'active', ?)",
            (
                str(uuid.uuid4()),
                hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
                first.loaded.database_context_id,
            ),
        )

    decision = _run(root, store, RecordingRandom(), installation_id)
    assert decision.state is DatabaseKeyRuntimeDecisionState.BLOCKED
    assert decision.error_code == "data_keyset_cardinality_invalid"


@pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("JKM_REAL_KEYCHAIN_TEST") != "1",
    reason="explicit real macOS Keychain acceptance required",
)
def test_real_macos_keychain_survives_separate_process_restart_and_cleans_up(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    worker = Path(__file__).parent / "helpers" / "dmk_database_key_runtime_worker.py"
    repository_root = Path(__file__).parents[1]

    def invoke(mode: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(repository_root)
        completed = subprocess.run(
            [sys.executable, str(worker), mode, str(root), installation_id],
            cwd=repository_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = {"state": "INVALID_OUTPUT"}
        return completed, payload

    cleanup_result: subprocess.CompletedProcess[str] | None = None
    cleanup_payload: dict[str, object] = {}
    try:
        first_result, first = invoke("first")
        assert first_result.returncode == 0, first
        restart_result, restarted = invoke("restart")
        assert restart_result.returncode == 0, restarted
        assert first["state"] == restarted["state"] == "ACTIVE"
        assert first["first_run"] is True
        assert restarted["first_run"] is False
        for field in (
            "database_context_id",
            "dmk_key_id",
            "dmk_generation",
            "dmk_fingerprint_sha256",
            "database_key_id",
            "database_key_generation",
            "database_key_fingerprint_sha256",
        ):
            assert first[field] == restarted[field]
        assert first["dmk_fingerprint_sha256"] != first[
            "database_key_fingerprint_sha256"
        ]
    finally:
        cleanup_result, cleanup_payload = invoke("cleanup")
    assert cleanup_result.returncode == 0, cleanup_payload
    assert cleanup_payload == {"remaining": [], "state": "CLEANED"}
