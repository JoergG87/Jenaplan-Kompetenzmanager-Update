from __future__ import annotations

from dataclasses import replace
import logging
import os
from pathlib import Path
import sqlite3
import uuid

import pytest

from src.security.data_keys import LoadedDataMasterKey
from src.security.backup_container import BACKUP_KEY_WRAP_PURPOSE
from src.security.database_key_runtime import (
    DatabaseKeyRuntimePaths,
    LoadedDatabaseKeyRuntime,
)
from src.security.database_keys import DATABASE_KEY_WRAP_PURPOSE, DatabaseKey
from src.security.document_container import DOCUMENT_KEY_WRAP_PURPOSE
from src.security.final_v3_document_runtime import (
    FINAL_V3_DOCUMENT_APPLICATION_ID,
    FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT,
    FINAL_V3_DOCUMENT_USER_VERSION,
    FinalV3DocumentRuntime,
    FinalV3DocumentRuntimeDecisionState,
    FinalV3DocumentRuntimeError,
    FinalV3DocumentRuntimePaths,
    FinalV3DocumentSchemaV1,
    _initialize_container_layout,
    _require_no_document_database_sidecars,
    run_gated_final_v4_document_runtime,
)
from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from tests.test_final_v4_sqlcipher_runtime import (
    MemoryDataMasterKeyStore,
    _account_loader,
    _environment,
    _root,
    requires_exact_417,
)


INSTALLATION_ID = "11111111-1111-4111-8111-111111111111"
DATABASE_CONTEXT_ID = "22222222-2222-4222-8222-222222222222"
DMK_ID = "33333333-3333-4333-8333-333333333333"
DATABASE_KEY_ID = "44444444-4444-4444-8444-444444444444"
DOCUMENT_ID = "55555555-5555-4555-8555-555555555555"
DMK_MATERIAL = b"\x31" * 32
DATABASE_KEY_MATERIAL = b"\x52" * 32


class _SQLiteFactory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self, *, create: bool):
        if create and self.path.exists():
            raise RuntimeError("exists")
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def connect_read_only(self):
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class _Consumer:
    def __init__(self) -> None:
        self.started = False
        self.finished = False
        self.aborted: str | None = None
        self.payload = bytearray()

    def start(self, _manifest) -> None:
        self.started = True

    def write(self, chunk: bytes) -> None:
        assert not self.finished
        self.payload.extend(chunk)

    def finish(self, _result) -> None:
        self.finished = True

    def abort(self, code: str) -> None:
        self.aborted = code


class _RecordingRandom:
    def __init__(self) -> None:
        self.outputs: list[bytes] = []

    def bytes(self, length: int) -> bytes:
        value = os.urandom(length)
        self.outputs.append(value)
        return value


def _loaded(dmk_material: bytes = DMK_MATERIAL) -> LoadedDatabaseKeyRuntime:
    dmk = LoadedDataMasterKey(DMK_ID, 1, dmk_material)
    database_key = DatabaseKey(DATABASE_KEY_ID, 1, DATABASE_KEY_MATERIAL)
    return LoadedDatabaseKeyRuntime(
        database_context_id=DATABASE_CONTEXT_ID,
        dmk_key_id=dmk.key_id,
        dmk_generation=dmk.generation,
        dmk_fingerprint_sha256=__import__("hashlib").sha256(
            dmk.key_material
        ).hexdigest(),
        database_key_id=database_key.key_id,
        database_key_generation=database_key.generation,
        database_key_fingerprint_sha256=__import__("hashlib").sha256(
            database_key.key_material
        ).hexdigest(),
        first_run=False,
        dmk=dmk,
        database_key=database_key,
    )


def _paths(root: Path) -> FinalV3DocumentRuntimePaths:
    root.mkdir(mode=0o700)
    key_paths = DatabaseKeyRuntimePaths.for_root(root)
    final_paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
    final_paths.runtime_root.mkdir(mode=0o700)
    return FinalV3DocumentRuntimePaths.for_final_v4(final_paths)


def _runtime(
    tmp_path: Path,
    *,
    loaded: LoadedDatabaseKeyRuntime | None = None,
    installation_id: str = INSTALLATION_ID,
    fault_hook=None,
    random_source=None,
) -> FinalV3DocumentRuntime:
    paths = _paths(tmp_path / "runtime")
    factory = _SQLiteFactory(paths.database)
    with factory.connect(create=True) as connection:
        FinalV3DocumentSchemaV1.initialize(
            connection,
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            created_at="2026-08-03T10:00:00Z",
        )
    _initialize_container_layout(paths)
    source_root = tmp_path / "source-input"
    source_root.mkdir(mode=0o700)
    return FinalV3DocumentRuntime(
        paths=paths,
        factory=factory,  # type: ignore[arg-type]
        loaded_keys=loaded or _loaded(),
        installation_id=installation_id,
        source_root=source_root,
        random_source=random_source or SystemRandomSource(),
        clock=SystemClock(),
        fault_hook=fault_hook,
    )


def _reopen(
    runtime: FinalV3DocumentRuntime,
    *,
    loaded: LoadedDatabaseKeyRuntime | None = None,
    installation_id: str = INSTALLATION_ID,
    fault_hook=None,
) -> FinalV3DocumentRuntime:
    return FinalV3DocumentRuntime(
        paths=runtime.paths,
        factory=_SQLiteFactory(runtime.paths.database),  # type: ignore[arg-type]
        loaded_keys=loaded or _loaded(),
        installation_id=installation_id,
        source_root=runtime.source_root,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_hook=fault_hook,
    )


def _source(runtime: FinalV3DocumentRuntime, name: str, payload: bytes) -> None:
    (runtime.source_root / name).write_bytes(payload)


def _read(runtime: FinalV3DocumentRuntime) -> bytes:
    consumer = _Consumer()
    runtime.read(document_id=DOCUMENT_ID, consumer=consumer)
    assert consumer.started and consumer.finished and consumer.aborted is None
    return bytes(consumer.payload)


def test_schema_v1_has_exact_identity_and_context_binding(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with sqlite3.connect(runtime.paths.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("PRAGMA application_id").fetchone()[0] == (
            FINAL_V3_DOCUMENT_APPLICATION_ID
        )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == (
            FINAL_V3_DOCUMENT_USER_VERSION
        )
        identity = __import__(
            "src.core.database_compatibility", fromlist=["DatabaseCompatibilityInspector"]
        ).DatabaseCompatibilityInspector.schema_identity_for_connection(connection)
        assert identity.fingerprint == FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT
        FinalV3DocumentSchemaV1.validate(
            connection,
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
        )
        with pytest.raises(FinalV3DocumentRuntimeError):
            FinalV3DocumentSchemaV1.validate(
                connection,
                installation_id=str(uuid.uuid4()),
                database_context_id=DATABASE_CONTEXT_ID,
            )


def test_document_hkdf_purpose_is_distinct_from_database_and_backup() -> None:
    assert DOCUMENT_KEY_WRAP_PURPOSE not in {
        DATABASE_KEY_WRAP_PURPOSE,
        BACKUP_KEY_WRAP_PURPOSE,
    }


def test_prepare_activate_read_replace_and_restart_are_verified(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    first_payload = b"Interner Fachtext eins\n" * 100
    _source(runtime, "first.bin", first_payload)
    prepared = runtime.prepare(
        document_id=DOCUMENT_ID,
        source_name="first.bin",
        original_filename="Laura vertraulich.pdf",
        mime_type="application/pdf",
    )
    assert prepared.lifecycle_status == "PREPARED"
    assert _CONTAINER_FILENAME(prepared.storage_id) == (
        runtime.paths.storage_root / f"{prepared.storage_id}.jkmedoc"
    ).name
    active = runtime.activate(
        document_id=DOCUMENT_ID,
        document_generation=prepared.document_generation,
    )
    assert active.lifecycle_status == "ACTIVE"
    assert _read(_reopen(runtime)) == first_payload

    second_payload = b"Interner Fachtext zwei\n" * 140
    _source(runtime, "second.bin", second_payload)
    replacement = runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="second.bin",
        original_filename="Neuer Originalname.png",
        mime_type="image/png",
    )
    assert replacement.document_generation == 2
    assert _read(_reopen(runtime)) == second_payload
    with sqlite3.connect(runtime.paths.database) as connection:
        states = connection.execute(
            """
            SELECT document_generation, lifecycle_status
            FROM final_v3_document_generations
            WHERE document_id = ? ORDER BY document_generation
            """,
            (DOCUMENT_ID,),
        ).fetchall()
        pointer = connection.execute(
            "SELECT active_generation FROM final_v3_documents WHERE document_id = ?",
            (DOCUMENT_ID,),
        ).fetchone()[0]
    assert states == [(1, "RETAINED"), (2, "ACTIVE")]
    assert pointer == 2
    assert (runtime.paths.storage_root / f"{active.storage_id}.jkmedoc").exists()


def test_twenty_lifecycle_cycles_keep_one_active_and_all_old_containers(
    tmp_path: Path,
) -> None:
    random_source = _RecordingRandom()
    runtime = _runtime(tmp_path, random_source=random_source)
    expected = b""
    storage_ids: list[str] = []
    for cycle in range(1, 21):
        expected = f"Fachtext generation {cycle}\n".encode() * 9
        name = f"source-{cycle}.bin"
        _source(runtime, name, expected)
        record = runtime.replace(
            document_id=DOCUMENT_ID,
            source_name=name,
            original_filename=f"Fachdatei {cycle}.pdf",
            mime_type="application/pdf",
        )
        storage_ids.append(record.storage_id)
        assert _read(runtime) == expected
    with sqlite3.connect(runtime.paths.database) as connection:
        counts = connection.execute(
            """
            SELECT lifecycle_status, COUNT(*)
            FROM final_v3_document_generations
            GROUP BY lifecycle_status ORDER BY lifecycle_status
            """
        ).fetchall()
        active = connection.execute(
            """
            SELECT COUNT(*) FROM final_v3_document_generations
            WHERE lifecycle_status = 'ACTIVE'
            """
        ).fetchone()[0]
    assert counts == [("ACTIVE", 1), ("RETAINED", 19)]
    assert active == 1
    assert len(tuple(runtime.paths.storage_root.glob("*.jkmedoc"))) == 20
    assert len(set(storage_ids)) == 20
    document_keys = [value for value in random_source.outputs if len(value) == 32]
    assert len(document_keys) == 20
    assert len(set(document_keys)) == 20
    for container in runtime.paths.storage_root.glob("*.jkmedoc"):
        raw = container.read_bytes()
        assert all(document_key not in raw for document_key in document_keys)
    _reopen(runtime).validate_restart()


def test_existing_prepared_generation_requires_explicit_resume(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    _source(runtime, "first.bin", b"first prepared payload")
    prepared = runtime.prepare(
        document_id=DOCUMENT_ID,
        source_name="first.bin",
        original_filename="first.pdf",
        mime_type="application/pdf",
    )
    _source(runtime, "changed.bin", b"different source must not replace intent")
    with pytest.raises(FinalV3DocumentRuntimeError) as captured:
        _reopen(runtime).prepare(
            document_id=DOCUMENT_ID,
            source_name="changed.bin",
            original_filename="changed.pdf",
            mime_type="application/pdf",
        )
    assert captured.value.code == "document_prepared_activation_required"
    active = _reopen(runtime).activate(document_id=DOCUMENT_ID)
    assert active.document_generation == prepared.document_generation
    assert _read(_reopen(runtime)) == b"first prepared payload"


def test_restart_read_does_not_depend_on_source_root(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    payload = b"restart read without source directory"
    _source(runtime, "source.bin", payload)
    runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="source.bin",
        original_filename="source.pdf",
        mime_type="application/pdf",
    )
    runtime.source_root.rename(tmp_path / "detached-source")
    restarted = FinalV3DocumentRuntime(
        paths=runtime.paths,
        factory=_SQLiteFactory(runtime.paths.database),  # type: ignore[arg-type]
        loaded_keys=_loaded(),
        installation_id=INSTALLATION_ID,
        source_root=None,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
    )
    assert _read(restarted) == payload
    with pytest.raises(FinalV3DocumentRuntimeError) as captured:
        restarted.prepare(
            document_id=str(uuid.uuid4()),
            source_name="missing.bin",
            original_filename="missing.pdf",
            mime_type="application/pdf",
        )
    assert captured.value.code == "document_source_root_required"


@pytest.mark.parametrize(
    "boundary", ["during_pointer_switch", "after_activation_before_retained"]
)
def test_failed_pointer_switch_rolls_back_and_old_active_remains_readable(
    tmp_path: Path, boundary: str
) -> None:
    runtime = _runtime(tmp_path)
    old_payload = b"alter aktiver Inhalt"
    _source(runtime, "old.bin", old_payload)
    runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="old.bin",
        original_filename="old.pdf",
        mime_type="application/pdf",
    )
    new_payload = b"neuer vorbereiteter Inhalt"
    _source(runtime, "new.bin", new_payload)
    prepared = runtime.prepare(
        document_id=DOCUMENT_ID,
        source_name="new.bin",
        original_filename="new.pdf",
        mime_type="application/pdf",
    )

    def fail(observed: str) -> None:
        if observed == boundary:
            raise RuntimeError("injected")

    faulted = _reopen(runtime, fault_hook=fail)
    with pytest.raises(FinalV3DocumentRuntimeError) as captured:
        faulted.activate(
            document_id=DOCUMENT_ID,
            document_generation=prepared.document_generation,
        )
    assert captured.value.code == "document_activation_failed"
    restarted = _reopen(runtime)
    assert _read(restarted) == old_payload
    with sqlite3.connect(runtime.paths.database) as connection:
        assert connection.execute(
            """
            SELECT document_generation, lifecycle_status
            FROM final_v3_document_generations ORDER BY document_generation
            """
        ).fetchall() == [(1, "ACTIVE"), (2, "PREPARED")]


def test_container_exchange_during_activation_rolls_back_pointer(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    old_payload = b"old remains active"
    _source(runtime, "old.bin", old_payload)
    runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="old.bin",
        original_filename="old.pdf",
        mime_type="application/pdf",
    )
    _source(runtime, "new.bin", b"new prepared payload")
    prepared = runtime.prepare(
        document_id=DOCUMENT_ID,
        source_name="new.bin",
        original_filename="new.pdf",
        mime_type="application/pdf",
    )
    container = runtime.paths.storage_root / f"{prepared.storage_id}.jkmedoc"
    original = container.read_bytes()

    def exchange(boundary: str) -> None:
        if boundary == "after_activation_before_retained":
            changed = bytearray(original)
            changed[-1] ^= 0x01
            container.write_bytes(changed)

    with pytest.raises(FinalV3DocumentRuntimeError):
        _reopen(runtime, fault_hook=exchange).activate(
            document_id=DOCUMENT_ID,
            document_generation=prepared.document_generation,
        )
    with sqlite3.connect(runtime.paths.database) as connection:
        assert connection.execute(
            "SELECT active_generation FROM final_v3_documents WHERE document_id = ?",
            (DOCUMENT_ID,),
        ).fetchone()[0] == 1
        assert connection.execute(
            """
            SELECT document_generation, lifecycle_status
            FROM final_v3_document_generations ORDER BY document_generation
            """
        ).fetchall() == [(1, "ACTIVE"), (2, "PREPARED")]
    container.write_bytes(original)
    assert _read(_reopen(runtime)) == old_payload


def test_pointer_tamper_is_rejected_on_restart(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _source(runtime, "old.bin", b"old")
    runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="old.bin",
        original_filename="old.pdf",
        mime_type="application/pdf",
    )
    _source(runtime, "new.bin", b"new")
    runtime.prepare(
        document_id=DOCUMENT_ID,
        source_name="new.bin",
        original_filename="new.pdf",
        mime_type="application/pdf",
    )
    with sqlite3.connect(runtime.paths.database) as connection:
        connection.execute(
            "UPDATE final_v3_documents SET active_generation = 2 WHERE document_id = ?",
            (DOCUMENT_ID,),
        )
    with pytest.raises(FinalV3DocumentRuntimeError) as captured:
        _reopen(runtime).validate_restart()
    assert captured.value.code == "document_pointer_invariant_failed"


def test_wrong_dmk_context_tamper_and_unknown_storage_fail_closed(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    payload = b"kein Klartext im verwalteten Storage"
    _source(runtime, "source.bin", payload)
    active = runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="source.bin",
        original_filename="Geheime Lernnotiz.txt",
        mime_type="text/plain",
    )
    wrong_dmk = replace(
        _loaded(),
        dmk=LoadedDataMasterKey(DMK_ID, 1, b"\x99" * 32),
    )
    with pytest.raises(FinalV3DocumentRuntimeError):
        _reopen(runtime, loaded=wrong_dmk).validate_restart()
    with pytest.raises(FinalV3DocumentRuntimeError):
        _reopen(runtime, installation_id=str(uuid.uuid4())).validate_restart()

    container = runtime.paths.storage_root / f"{active.storage_id}.jkmedoc"
    value = bytearray(container.read_bytes())
    value[-20] ^= 0x01
    container.write_bytes(value)
    with pytest.raises(FinalV3DocumentRuntimeError):
        _reopen(runtime).validate_restart()

    container.write_bytes(bytes(value[:-20] + bytes([value[-20] ^ 0x01]) + value[-19:]))
    unknown = runtime.paths.storage_root / f"{uuid.uuid4()}.jkmedoc"
    unknown.symlink_to(runtime.source_root / "source.bin")
    with pytest.raises(FinalV3DocumentRuntimeError) as captured:
        _reopen(runtime).validate_restart()
    assert captured.value.code == "document_storage_inventory_invalid"


def test_no_plaintext_secrets_or_business_text_in_storage_names_headers_or_repr(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    random_source = _RecordingRandom()
    runtime = _runtime(tmp_path, random_source=random_source)
    payload = b"Laura Fachtext Mathematik sehr vertraulich" * 20
    original = "Laura Mathematik Foerdernotiz.pdf"
    _source(runtime, "source.bin", payload)
    record = runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="source.bin",
        original_filename=original,
        mime_type="application/pdf",
    )
    names = [
        path.name
        for path in runtime.paths.storage_root.iterdir()
        if path.name.endswith(".jkmedoc")
    ]
    assert names == [f"{record.storage_id}.jkmedoc"]
    container = runtime.paths.storage_root / names[0]
    raw = container.read_bytes()
    assert payload not in raw
    assert original.encode() not in raw
    assert b"application/pdf" not in raw
    assert DMK_MATERIAL not in raw
    assert DATABASE_KEY_MATERIAL not in raw
    document_keys = [value for value in random_source.outputs if len(value) == 32]
    assert len(document_keys) == 1
    assert document_keys[0] not in raw
    assert not runtime.source_root.is_relative_to(runtime.paths.container_root)
    for managed_file in runtime.paths.container_root.rglob("*"):
        if managed_file.is_file():
            managed_bytes = managed_file.read_bytes()
            assert payload not in managed_bytes
            assert original.encode() not in managed_bytes
    assert all(
        document_keys[0].hex() not in record.getMessage()
        and DMK_MATERIAL.hex() not in record.getMessage()
        and DATABASE_KEY_MATERIAL.hex() not in record.getMessage()
        for record in caplog.records
    )
    rendered = repr(_loaded()) + repr(runtime)
    assert DMK_MATERIAL.hex() not in rendered
    assert DATABASE_KEY_MATERIAL.hex() not in rendered
    assert original not in rendered

    wrong_dmk = replace(
        _loaded(),
        dmk=LoadedDataMasterKey(DMK_ID, 1, b"\x99" * 32),
    )
    with pytest.raises(FinalV3DocumentRuntimeError) as captured:
        _reopen(runtime, loaded=wrong_dmk).validate_restart()
    error_text = repr(captured.value) + str(captured.value)
    assert document_keys[0].hex() not in error_text
    assert DMK_MATERIAL.hex() not in error_text
    assert DATABASE_KEY_MATERIAL.hex() not in error_text


def test_database_sidecars_are_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "documents-v1.sqlcipher"
    database.write_bytes(b"database")
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = Path(f"{database}{suffix}")
        sidecar.write_bytes(b"pending")
        with pytest.raises(FinalV3DocumentRuntimeError) as captured:
            _require_no_document_database_sidecars(database)
        assert captured.value.code == "document_database_sidecar_present"
        sidecar.unlink()


def test_gate_off_does_not_touch_account_or_filesystem(tmp_path: Path) -> None:
    touched = False

    def account_loader():
        nonlocal touched
        touched = True
        raise AssertionError("must not be called")

    decision = run_gated_final_v4_document_runtime(
        account_loader=account_loader,
        authentication_confirmed=False,
        environ={},
    )
    assert decision.state is FinalV3DocumentRuntimeDecisionState.DISABLED
    assert not touched
    assert tuple(tmp_path.iterdir()) == ()


@requires_exact_417
def test_exact_sqlcipher_composition_create_read_and_restart(
    tmp_path: Path,
) -> None:
    external_source = tmp_path / "external-input"
    external_source.mkdir(mode=0o700)
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    first = run_gated_final_v4_document_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        document_database_create_allowed=True,
        environ=_environment(root),
        key_store=store,
        source_root=external_source,
    )
    assert first.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert first.runtime is not None
    documents = first.runtime.documents
    payload = b"exact SQLCipher document runtime"
    _source(documents, "exact.bin", payload)
    active = documents.replace(
        document_id=DOCUMENT_ID,
        source_name="exact.bin",
        original_filename="exact.pdf",
        mime_type="application/pdf",
    )
    assert active.lifecycle_status == "ACTIVE"
    assert _read(documents) == payload
    assert not documents.paths.database.read_bytes().startswith(
        b"SQLite format 3\x00"
    )

    restarted = run_gated_final_v4_document_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
        source_root=external_source,
    )
    assert restarted.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert restarted.runtime is not None
    assert _read(restarted.runtime.documents) == payload


def _CONTAINER_FILENAME(storage_id: str) -> str:
    return f"{storage_id}.jkmedoc"
