from __future__ import annotations

from dataclasses import replace
import hashlib
from importlib.util import find_spec
import json
import os
from pathlib import Path
import secrets
import struct
from types import SimpleNamespace
import uuid

import nacl.bindings
import pytest

import prototypes.encrypted_backup_container.sprint9_container as container_module
from prototypes.encrypted_backup_container import (
    BackupSourceFile,
    SyntheticEncryptedBackupServiceV1,
)
from src.core.database_engine import (
    DatabaseEngineError,
    SQLCipherConnectionProvider,
)
from src.security.backup_container import (
    BACKUP_KEY_BYTES,
    BACKUP_KEY_NONCE_BYTES,
    ENCRYPTED_BACKUP_MAGIC,
    BackupContainerContextV1,
    BackupContainerHeaderV1,
    BackupEntryRole,
    EncryptedBackupError,
    build_backup_key_envelope,
    canonical_json,
    manifest_record_aad,
    open_backup_key_envelope,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.infrastructure.system import SystemClock, SystemRandomSource


pytestmark = pytest.mark.skipif(
    find_spec("sqlcipher3") is None,
    reason="isolated Sprint-9 tests require the SQLCipher spike dependency",
)

_UINT32 = struct.Struct(">I")


def _environment(
    tmp_path: Path,
    *,
    chunk_size: int = 4096,
    document_bytes: bytes = b"synthetic-document-marker" * 400,
    fault=None,
):
    root = tmp_path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    (root / container_module.SYNTHETIC_BACKUP_TEST_ROOT_MARKER).write_bytes(
        container_module.SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES
    )
    provider = SQLCipherConnectionProvider()
    database_key = secrets.token_bytes(32)
    database = root / "synthetic-source.sqlcipher"
    connection = provider.connect(
        database, create=True, key_material=database_key
    )
    connection.execute(
        f"PRAGMA application_id = "
        f"{container_module.SYNTHETIC_BACKUP_APPLICATION_ID}"
    )
    connection.execute(
        f"PRAGMA user_version = {container_module.SYNTHETIC_BACKUP_USER_VERSION}"
    )
    connection.execute(
        f'CREATE TABLE "{container_module.SYNTHETIC_BACKUP_GUARD_TABLE}" '
        "(id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
    )
    connection.execute(
        f'INSERT INTO "{container_module.SYNTHETIC_BACKUP_GUARD_TABLE}"'
        "(marker) VALUES (?)",
        (container_module.SYNTHETIC_BACKUP_GUARD_VALUE,),
    )
    sqlite_version = str(
        connection.execute("SELECT sqlite_version()").fetchone()[0]
    )
    sqlcipher_version = str(
        connection.execute("PRAGMA cipher_version").fetchone()[0]
    )
    connection.commit()
    connection.close()
    document = root / "synthetic-document.bin"
    document.write_bytes(document_bytes)
    dmk = LoadedDataMasterKey(
        str(uuid.uuid4()), 1, secrets.token_bytes(32)
    )
    context = BackupContainerContextV1(
        installation_id=str(uuid.uuid4()),
        database_context_id=str(uuid.uuid4()),
        app_version="sprint9-private-app-marker",
        sqlite_version=sqlite_version,
        sqlcipher_version=sqlcipher_version,
    )
    database_source = BackupSourceFile(
        database,
        str(uuid.uuid4()),
        BackupEntryRole.SQLCIPHER_DATABASE,
    )
    document_source = BackupSourceFile(
        document,
        str(uuid.uuid4()),
        BackupEntryRole.MANAGED_DOCUMENT,
    )
    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=provider,
        fault_injector=fault,
        chunk_size=chunk_size,
    )
    return SimpleNamespace(
        root=root,
        provider=provider,
        database_key=database_key,
        database=database,
        document=document,
        dmk=dmk,
        context=context,
        database_source=database_source,
        document_source=document_source,
        service=service,
        target=root / "synthetic.jkmebackup",
    )


def _create(environment):
    return environment.service.create(
        test_root=environment.root,
        target=environment.target,
        dmk=environment.dmk,
        context=environment.context,
        database_source=environment.database_source,
        document_sources=(environment.document_source,),
        database_key=environment.database_key,
    )


def _expected_sources(environment) -> dict[str, Path]:
    return {
        environment.database_source.entry_id: environment.database,
        environment.document_source.entry_id: environment.document,
    }


def _split_container(path: Path) -> tuple[bytes, list[bytes]]:
    value = path.read_bytes()
    assert value[: len(ENCRYPTED_BACKUP_MAGIC)] == ENCRYPTED_BACKUP_MAGIC
    offset = len(ENCRYPTED_BACKUP_MAGIC)
    header_size = _UINT32.unpack(value[offset : offset + _UINT32.size])[0]
    offset += _UINT32.size
    header = value[offset : offset + header_size]
    offset += header_size
    frames: list[bytes] = []
    while offset < len(value):
        size = _UINT32.unpack(value[offset : offset + _UINT32.size])[0]
        end = offset + _UINT32.size + size
        frames.append(value[offset:end])
        offset = end
    assert offset == len(value)
    return header, frames


def _write_container_parts(
    path: Path,
    header: bytes,
    frames: list[bytes],
    *,
    trailing: bytes = b"",
) -> None:
    value = (
        ENCRYPTED_BACKUP_MAGIC
        + _UINT32.pack(len(header))
        + header
        + b"".join(frames)
        + trailing
    )
    path.write_bytes(value)


def _write_header_payload(
    source: Path, target: Path, mutate
) -> None:
    header, frames = _split_container(source)
    payload = json.loads(header.decode("ascii"))
    mutate(payload)
    _write_container_parts(target, canonical_json(payload), frames)


def _mutate_frame(frame: bytes) -> bytes:
    size = _UINT32.unpack(frame[: _UINT32.size])[0]
    payload = bytearray(frame[_UINT32.size :])
    assert size == len(payload) and payload
    payload[len(payload) // 2] ^= 0x80
    return _UINT32.pack(size) + bytes(payload)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_roundtrip_restore_reopen_and_visible_metadata_minimization(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)

    result = _create(environment)
    repeated = environment.service.verify(
        test_root=environment.root,
        container=environment.target,
        dmk=environment.dmk,
        context=environment.context,
    )

    assert repeated == result
    assert result.manifest.entries[0].role is BackupEntryRole.SQLCIPHER_DATABASE
    assert result.manifest.entries[1].role is BackupEntryRole.MANAGED_DOCUMENT
    assert result.container_size == environment.target.stat().st_size
    raw = environment.target.read_bytes()
    assert b"synthetic-database-marker-never-visible" not in raw
    assert b"synthetic-document-marker" not in raw
    assert environment.context.installation_id.encode("ascii") not in raw
    assert environment.context.database_context_id.encode("ascii") not in raw
    assert environment.context.app_version.encode("ascii") not in raw
    assert str(environment.database).encode() not in raw
    assert str(environment.document).encode() not in raw
    assert environment.dmk.key_material not in raw
    assert environment.database_key not in raw

    header_bytes, _frames = _split_container(environment.target)
    header_payload = json.loads(header_bytes.decode("ascii"))
    assert set(header_payload) == {
        "chunk_size",
        "container_format",
        "container_id",
        "container_version",
        "envelope",
        "header_version",
        "stream_algorithm",
        "stream_header",
    }
    assert "ciphertext" in header_payload["envelope"]
    assert "installation_id" not in header_payload
    assert "database_context_id" not in header_payload
    assert "created_at" not in header_payload
    assert "app_version" not in header_payload

    restored = environment.service.restore(
        test_root=environment.root,
        container=environment.target,
        restore_root=environment.root / "restore",
        dmk=environment.dmk,
        context=environment.context,
        database_key=environment.database_key,
        expected_sources=_expected_sources(environment),
    )
    assert restored.database_path.read_bytes() == environment.database.read_bytes()
    assert (
        restored.document_paths[0].read_bytes()
        == environment.document.read_bytes()
    )
    assert restored.completion_path.is_file()
    connection = environment.provider.connect(
        restored.database_path,
        create=False,
        key_material=environment.database_key,
    )
    assert connection.execute(
        f'SELECT marker FROM "{container_module.SYNTHETIC_BACKUP_GUARD_TABLE}"'
    ).fetchone()[0] == container_module.SYNTHETIC_BACKUP_GUARD_VALUE
    connection.close()
    with pytest.raises(DatabaseEngineError):
        environment.provider.connect(
            restored.database_path,
            create=False,
            key_material=secrets.token_bytes(32),
        )


def test_each_container_uses_distinct_backup_key_envelope_and_ciphertext(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    first = _create(environment)
    second_target = environment.root / "second.jkmebackup"
    second = environment.service.create(
        test_root=environment.root,
        target=second_target,
        dmk=environment.dmk,
        context=environment.context,
        database_source=environment.database_source,
        document_sources=(environment.document_source,),
        database_key=environment.database_key,
    )

    assert first.header.container_id != second.header.container_id
    assert (
        first.header.envelope.backup_key_id
        != second.header.envelope.backup_key_id
    )
    assert first.header.envelope.nonce != second.header.envelope.nonce
    assert (
        first.header.envelope.ciphertext
        != second.header.envelope.ciphertext
    )
    assert environment.target.read_bytes() != second_target.read_bytes()
    assert "ciphertext" not in repr(first.header.envelope)


def test_wrong_dmk_wrong_context_and_validly_wrapped_wrong_backup_key_fail(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    _create(environment)

    wrong_material = LoadedDataMasterKey(
        environment.dmk.key_id,
        environment.dmk.generation,
        secrets.token_bytes(32),
    )
    with pytest.raises(
        EncryptedBackupError,
        match="backup_key_envelope_authentication_failed",
    ):
        environment.service.verify(
            test_root=environment.root,
            container=environment.target,
            dmk=wrong_material,
            context=environment.context,
        )

    wrong_id = LoadedDataMasterKey(
        str(uuid.uuid4()),
        environment.dmk.generation,
        environment.dmk.key_material,
    )
    with pytest.raises(EncryptedBackupError, match="dmk_mismatch"):
        environment.service.verify(
            test_root=environment.root,
            container=environment.target,
            dmk=wrong_id,
            context=environment.context,
        )

    wrong_context = replace(
        environment.context, database_context_id=str(uuid.uuid4())
    )
    with pytest.raises(
        EncryptedBackupError,
        match="backup_key_envelope_authentication_failed",
    ):
        environment.service.verify(
            test_root=environment.root,
            container=environment.target,
            dmk=environment.dmk,
            context=wrong_context,
        )

    header_bytes, frames = _split_container(environment.target)
    header = BackupContainerHeaderV1.from_bytes(header_bytes)
    wrong_key = secrets.token_bytes(BACKUP_KEY_BYTES)
    wrong_envelope = build_backup_key_envelope(
        environment.dmk,
        context=environment.context,
        container_id=header.container_id,
        backup_key_id=header.envelope.backup_key_id,
        stream_header=header.stream_header,
        chunk_size=header.chunk_size,
        backup_key=wrong_key,
        nonce=secrets.token_bytes(BACKUP_KEY_NONCE_BYTES),
    )
    wrong_header = replace(header, envelope=wrong_envelope).to_bytes()
    wrong_key_container = environment.root / "wrong-key.jkmebackup"
    _write_container_parts(wrong_key_container, wrong_header, frames)
    with pytest.raises(EncryptedBackupError, match="stream_authentication"):
        environment.service.verify(
            test_root=environment.root,
            container=wrong_key_container,
            dmk=environment.dmk,
            context=environment.context,
        )


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda payload: payload.update({"container_version": 2}),
            "backup_container_version_unsupported",
        ),
        (
            lambda payload: payload.update({"container_version": True}),
            "backup_container_version_unsupported",
        ),
        (
            lambda payload: payload["envelope"].update(
                {"envelope_version": True}
            ),
            "backup_key_envelope_version_unsupported",
        ),
        (
            lambda payload: payload["envelope"].update({"kdf_version": True}),
            "backup_key_envelope_kdf_unsupported",
        ),
        (
            lambda payload: payload.update({"unknown": "field"}),
            "backup_header_fields_invalid",
        ),
        (
            lambda payload: payload.update(
                {"stream_algorithm": "unknown-stream"}
            ),
            "backup_stream_algorithm_unsupported",
        ),
        (
            lambda payload: payload["envelope"].update(
                {"wrapping_algorithm": "unknown-aead"}
            ),
            "backup_key_envelope_algorithm_unsupported",
        ),
    ],
)
def test_unknown_header_versions_fields_and_algorithms_fail_closed(
    tmp_path: Path, mutation, code: str
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    mutated = environment.root / "mutated-header.jkmebackup"
    _write_header_payload(environment.target, mutated, mutation)

    with pytest.raises(EncryptedBackupError, match=code):
        environment.service.verify(
            test_root=environment.root,
            container=mutated,
            dmk=environment.dmk,
            context=environment.context,
        )


def test_current_runtime_version_drift_can_open_historical_container(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(tmp_path)
    historical_context = replace(
        environment.context,
        app_version="historical-app-version",
        sqlite_version="historical-sqlite-version",
        sqlcipher_version="historical-sqlcipher-version",
    )
    monkeypatch.setattr(
        environment.service,
        "_verify_bound_sqlcipher",
        lambda *_args, **_kwargs: None,
    )
    created = environment.service.create(
        test_root=environment.root,
        target=environment.target,
        dmk=environment.dmk,
        context=historical_context,
        database_source=environment.database_source,
        document_sources=(environment.document_source,),
        database_key=environment.database_key,
    )
    monkeypatch.undo()

    verified = environment.service.verify(
        test_root=environment.root,
        container=environment.target,
        dmk=environment.dmk,
        context=environment.context,
    )
    restored = environment.service.restore(
        test_root=environment.root,
        container=environment.target,
        restore_root=environment.root / "version-drift-restore",
        dmk=environment.dmk,
        context=environment.context,
        database_key=environment.database_key,
        expected_sources=_expected_sources(environment),
    )

    assert verified.manifest.context == historical_context
    assert created.manifest.context == historical_context
    assert restored.database_path.read_bytes() == environment.database.read_bytes()


@pytest.mark.parametrize("chunk_size", [0, 1, True])
def test_invalid_service_chunk_sizes_are_rejected(
    tmp_path: Path, chunk_size
) -> None:
    environment = _environment(tmp_path)

    with pytest.raises(EncryptedBackupError, match="backup_chunk_size_invalid"):
        SyntheticEncryptedBackupServiceV1(
            random_source=SystemRandomSource(),
            clock=SystemClock(),
            sqlcipher_provider=environment.provider,
            chunk_size=chunk_size,
        )


def test_envelope_and_manifest_ciphertext_tampering_fail_closed(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    envelope_tampered = environment.root / "envelope-tampered.jkmebackup"

    def mutate_envelope(payload):
        ciphertext = payload["envelope"]["ciphertext"]
        replacement = "A" if ciphertext[0] != "A" else "B"
        payload["envelope"]["ciphertext"] = replacement + ciphertext[1:]

    _write_header_payload(
        environment.target, envelope_tampered, mutate_envelope
    )
    with pytest.raises(EncryptedBackupError, match="envelope_authentication"):
        environment.service.verify(
            test_root=environment.root,
            container=envelope_tampered,
            dmk=environment.dmk,
            context=environment.context,
        )

    header, frames = _split_container(environment.target)
    manifest_tampered = environment.root / "manifest-tampered.jkmebackup"
    frames[0] = _mutate_frame(frames[0])
    _write_container_parts(manifest_tampered, header, frames)
    with pytest.raises(EncryptedBackupError, match="stream_authentication"):
        environment.service.verify(
            test_root=environment.root,
            container=manifest_tampered,
            dmk=environment.dmk,
            context=environment.context,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda frames: frames.__setitem__(1, _mutate_frame(frames[1])),
        lambda frames: frames.__setitem__(
            slice(1, 3), [frames[2], frames[1]]
        ),
        lambda frames: frames.insert(2, frames[1]),
        lambda frames: frames.pop(1),
        lambda frames: frames.pop(),
    ],
    ids=[
        "tampered-chunk",
        "reordered-chunks",
        "duplicated-chunk",
        "missing-chunk",
        "missing-final",
    ],
)
def test_chunk_tamper_reorder_duplicate_missing_and_final_are_rejected(
    tmp_path: Path, mutation
) -> None:
    environment = _environment(
        tmp_path, chunk_size=1024, document_bytes=b"doc" * 4000
    )
    _create(environment)
    header, frames = _split_container(environment.target)
    assert len(frames) >= 5
    mutation(frames)
    mutated = environment.root / "mutated-stream.jkmebackup"
    _write_container_parts(mutated, header, frames)

    with pytest.raises(EncryptedBackupError):
        environment.service.verify(
            test_root=environment.root,
            container=mutated,
            dmk=environment.dmk,
            context=environment.context,
        )


def test_truncation_and_trailing_bytes_are_rejected(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    original = environment.target.read_bytes()
    for index, cut in enumerate(
        [
            0,
            len(ENCRYPTED_BACKUP_MAGIC) - 1,
            len(ENCRYPTED_BACKUP_MAGIC) + 2,
            len(original) // 2,
            len(original) - 1,
        ]
    ):
        truncated = environment.root / f"truncated-{index}.jkmebackup"
        truncated.write_bytes(original[:cut])
        with pytest.raises(EncryptedBackupError):
            environment.service.verify(
                test_root=environment.root,
                container=truncated,
                dmk=environment.dmk,
                context=environment.context,
            )

    header, frames = _split_container(environment.target)
    trailing = environment.root / "trailing.jkmebackup"
    _write_container_parts(trailing, header, frames, trailing=b"extra")
    with pytest.raises(EncryptedBackupError, match="backup_trailing_data"):
        environment.service.verify(
            test_root=environment.root,
            container=trailing,
            dmk=environment.dmk,
            context=environment.context,
        )


def _write_authenticated_invalid_manifest(
    environment, *, mutate
) -> Path:
    result = _create(environment)
    old_header_bytes, _old_frames = _split_container(environment.target)
    old_header = BackupContainerHeaderV1.from_bytes(old_header_bytes)
    backup_key = open_backup_key_envelope(
        environment.dmk,
        context=environment.context,
        header=old_header,
    )
    push_state = (
        nacl.bindings.crypto_secretstream_xchacha20poly1305_state()
    )
    stream_header = (
        nacl.bindings.crypto_secretstream_xchacha20poly1305_init_push(
            push_state, backup_key
        )
    )
    envelope = build_backup_key_envelope(
        environment.dmk,
        context=environment.context,
        container_id=old_header.container_id,
        backup_key_id=old_header.envelope.backup_key_id,
        stream_header=stream_header,
        chunk_size=old_header.chunk_size,
        backup_key=backup_key,
        nonce=secrets.token_bytes(BACKUP_KEY_NONCE_BYTES),
    )
    header = replace(
        old_header, stream_header=stream_header, envelope=envelope
    )
    header_bytes = header.to_bytes()
    payload = result.manifest.to_payload()
    mutate(payload)
    invalid_manifest = canonical_json(payload)
    ciphertext = (
        nacl.bindings.crypto_secretstream_xchacha20poly1305_push(
            push_state,
            invalid_manifest,
            ad=manifest_record_aad(
                header_bytes, len(invalid_manifest)
            ),
            tag=nacl.bindings.crypto_secretstream_xchacha20poly1305_TAG_MESSAGE,
        )
    )
    frame = _UINT32.pack(len(ciphertext)) + ciphertext
    target = environment.root / "authenticated-invalid.jkmebackup"
    _write_container_parts(target, header_bytes, [frame])
    return target


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda payload: payload["entries"][1].update(
                {"restore_name": "../escape"}
            ),
            "backup_restore_name_invalid",
        ),
        (
            lambda payload: payload["entries"][1].update(
                {"restore_name": "/absolute"}
            ),
            "backup_restore_name_invalid",
        ),
        (
            lambda payload: payload["entries"][1].update(
                {"restore_name": "C:\\escape"}
            ),
            "backup_restore_name_invalid",
        ),
        (
            lambda payload: payload["entries"][1].update(
                {"role": "unknown-role"}
            ),
            "backup_manifest_entry_fields_invalid",
        ),
        (
            lambda payload: payload["entries"][1].update({"extra": True}),
            "backup_manifest_entry_fields_invalid",
        ),
    ],
)
def test_authenticated_path_traversal_roles_and_unknown_fields_are_rejected(
    tmp_path: Path, mutation, code: str
) -> None:
    environment = _environment(tmp_path)
    malicious = _write_authenticated_invalid_manifest(
        environment, mutate=mutation
    )

    with pytest.raises(EncryptedBackupError, match=code):
        environment.service.verify(
            test_root=environment.root,
            container=malicious,
            dmk=environment.dmk,
            context=environment.context,
        )
    assert not (environment.root.parent / "escape").exists()


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda payload: (
                payload["entries"].append(dict(payload["entries"][1])),
                payload.update(
                    {
                        "entry_count": 3,
                        "total_plaintext_size": (
                            payload["total_plaintext_size"]
                            + payload["entries"][1]["plaintext_size"]
                        ),
                    }
                ),
            ),
            "backup_manifest_duplicate_entry",
        ),
        (
            lambda payload: (
                payload["entries"].reverse(),
                payload.update({"entry_count": 2}),
            ),
            "backup_database_entry_invalid",
        ),
        (
            lambda payload: (
                payload["entries"].pop(0),
                payload.update(
                    {
                        "entry_count": 1,
                        "total_plaintext_size": payload["entries"][0][
                            "plaintext_size"
                        ],
                    }
                ),
            ),
            "backup_manifest_entry_count_invalid",
        ),
    ],
    ids=["duplicate-entry", "swapped-entries", "missing-database"],
)
def test_authenticated_duplicate_swapped_and_missing_entries_are_rejected(
    tmp_path: Path, mutation, code: str
) -> None:
    environment = _environment(tmp_path)
    malicious = _write_authenticated_invalid_manifest(
        environment, mutate=mutation
    )

    with pytest.raises(EncryptedBackupError, match=code):
        environment.service.verify(
            test_root=environment.root,
            container=malicious,
            dmk=environment.dmk,
            context=environment.context,
        )


def test_existing_targets_symlinks_and_paths_outside_root_are_never_mutated(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    database_before = _hash(environment.database)
    document_before = _hash(environment.document)
    existing = b"foreign-target-must-survive"
    environment.target.write_bytes(existing)

    with pytest.raises(EncryptedBackupError, match="backup_target_exists"):
        _create(environment)
    assert environment.target.read_bytes() == existing
    assert _hash(environment.database) == database_before
    assert _hash(environment.document) == document_before

    environment.target.unlink()
    foreign = environment.root / "foreign.bin"
    foreign.write_bytes(existing)
    environment.target.symlink_to(foreign)
    with pytest.raises(EncryptedBackupError, match="backup_target_exists"):
        _create(environment)
    assert foreign.read_bytes() == existing

    environment.target.unlink()
    real_document = environment.document
    symlink_document = environment.root / "symlink-document.bin"
    symlink_document.symlink_to(real_document)
    bad_document = replace(
        environment.document_source, path=symlink_document
    )
    with pytest.raises(
        EncryptedBackupError, match="backup_regular_file_required"
    ):
        environment.service.create(
            test_root=environment.root,
            target=environment.target,
            dmk=environment.dmk,
            context=environment.context,
            database_source=environment.database_source,
            document_sources=(bad_document,),
            database_key=environment.database_key,
        )
    assert real_document.read_bytes() == environment.document.read_bytes()

    with pytest.raises(
        EncryptedBackupError, match="backup_path_outside_test_root"
    ):
        environment.service.create(
            test_root=environment.root,
            target=environment.root.parent / "outside.jkmebackup",
            dmk=environment.dmk,
            context=environment.context,
            database_source=environment.database_source,
            document_sources=(environment.document_source,),
            database_key=environment.database_key,
        )


def test_unmarked_nonprivate_and_outside_roots_are_rejected_before_source_open(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path / "valid")
    outside = (tmp_path / "outside.sqlcipher").resolve()
    outside.write_bytes(environment.database.read_bytes())
    outside_before = _hash(outside)
    outside_source = replace(environment.database_source, path=outside)

    with pytest.raises(
        EncryptedBackupError, match="backup_path_outside_test_root"
    ):
        environment.service.create(
            test_root=environment.root,
            target=environment.target,
            dmk=environment.dmk,
            context=environment.context,
            database_source=outside_source,
            document_sources=(environment.document_source,),
            database_key=environment.database_key,
        )
    assert _hash(outside) == outside_before

    unmarked = (tmp_path / "unmarked").resolve()
    unmarked.mkdir()
    os.chmod(unmarked, 0o700)
    with pytest.raises(EncryptedBackupError, match="test_root"):
        environment.service.verify(
            test_root=unmarked,
            container=unmarked / "anything.jkmebackup",
            dmk=environment.dmk,
            context=environment.context,
        )

    os.chmod(environment.root, 0o755)
    with pytest.raises(EncryptedBackupError, match="not_private"):
        _create(environment)


def test_invalid_synthetic_sqlcipher_guard_fails_without_further_mutation(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    connection = environment.provider.connect(
        environment.database,
        create=False,
        key_material=environment.database_key,
    )
    connection.execute(
        f'DROP TABLE "{container_module.SYNTHETIC_BACKUP_GUARD_TABLE}"'
    )
    connection.commit()
    connection.close()
    before = _hash(environment.database)

    with pytest.raises(
        EncryptedBackupError, match="backup_sqlcipher_verification_failed"
    ):
        _create(environment)

    assert _hash(environment.database) == before
    assert not environment.target.exists()


@pytest.mark.parametrize(
    "phase",
    [
        "writer_after_header",
        "writer_after_manifest",
        "writer_after_chunk:sqlcipher_database",
        "writer_after_chunk:managed_document",
        "writer_before_final",
        "writer_after_final",
        "writer_after_file_fsync",
        "writer_after_retained_fsync",
        "writer_after_preverify",
    ],
)
def test_writer_faults_publish_no_valid_target_and_preserve_sources(
    tmp_path: Path, phase: str
) -> None:
    def fault(observed: str) -> None:
        if observed == phase:
            raise EncryptedBackupError("injected_writer_failure")

    environment = _environment(tmp_path, fault=fault)
    database_before = _hash(environment.database)
    document_before = _hash(environment.document)

    with pytest.raises(EncryptedBackupError, match="injected_writer_failure"):
        _create(environment)

    assert not environment.target.exists()
    assert _hash(environment.database) == database_before
    assert _hash(environment.document) == document_before
    assert not list(environment.root.glob("*.jkmebackup"))


def test_fault_after_publication_leaves_verified_target_and_retained_evidence(
    tmp_path: Path,
) -> None:
    def fault(observed: str) -> None:
        if observed == "writer_after_publish":
            raise EncryptedBackupError("injected_writer_failure")

    environment = _environment(tmp_path, fault=fault)
    database_before = _hash(environment.database)
    document_before = _hash(environment.document)

    with pytest.raises(EncryptedBackupError, match="injected_writer_failure"):
        _create(environment)

    result = environment.service.verify(
        test_root=environment.root,
        container=environment.target,
        dmk=environment.dmk,
        context=environment.context,
    )
    retained = list(environment.root.glob(".*.retained"))
    assert len(retained) == 1
    assert os.stat(retained[0]).st_ino == os.stat(environment.target).st_ino
    assert result.container_sha256 == _hash(retained[0])
    assert _hash(environment.database) == database_before
    assert _hash(environment.document) == document_before


def test_enospc_fsync_publish_and_publish_race_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(tmp_path / "write")
    original_write = container_module.os.write
    calls = 0

    def enospc(fd, value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(28, "synthetic enospc")
        return original_write(fd, value)

    monkeypatch.setattr(container_module.os, "write", enospc)
    with pytest.raises(EncryptedBackupError):
        _create(environment)
    assert not environment.target.exists()
    monkeypatch.setattr(container_module.os, "write", original_write)

    environment = _environment(tmp_path / "fsync")
    monkeypatch.setattr(
        container_module.os,
        "fsync",
        lambda _fd: (_ for _ in ()).throw(OSError(5, "synthetic fsync")),
    )
    with pytest.raises(EncryptedBackupError, match="fsync"):
        _create(environment)
    assert not environment.target.exists()
    monkeypatch.undo()

    environment = _environment(tmp_path / "publish")
    monkeypatch.setattr(
        container_module.os,
        "link",
        lambda _source, _target, **_kwargs: (_ for _ in ()).throw(
            OSError(5, "synthetic publish")
        ),
    )
    with pytest.raises(EncryptedBackupError, match="publish"):
        _create(environment)
    assert not environment.target.exists()
    monkeypatch.undo()

    environment = _environment(tmp_path / "race")
    foreign = b"publish-race-foreign"

    def race(phase: str) -> None:
        if phase == "writer_after_preverify":
            environment.target.write_bytes(foreign)

    environment.service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=race,
        chunk_size=4096,
    )
    with pytest.raises(EncryptedBackupError, match="backup_target_exists"):
        _create(environment)
    assert environment.target.read_bytes() == foreign


@pytest.mark.parametrize("failure_call", [1, 2, 3])
def test_each_writer_fsync_failure_has_defined_publication_state(
    tmp_path: Path, monkeypatch, failure_call: int
) -> None:
    environment = _environment(tmp_path)
    original_fsync = container_module.os.fsync
    calls = 0

    def fail_selected_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError(5, "synthetic writer fsync")
        return original_fsync(fd)

    monkeypatch.setattr(container_module.os, "fsync", fail_selected_fsync)
    with pytest.raises(EncryptedBackupError, match="fsync"):
        _create(environment)

    if failure_call < 3:
        assert not environment.target.exists()
    else:
        environment.service.verify(
            test_root=environment.root,
            container=environment.target,
            dmk=environment.dmk,
            context=environment.context,
        )


def test_writer_and_restore_permission_failures_do_not_publish_success(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(tmp_path / "writer")
    original_open = container_module.os.open

    def deny_retained_create(path, flags, *args, **kwargs):
        if (
            isinstance(path, Path)
            and path.parent == environment.root
            and path.name.endswith(".retained")
            and flags & os.O_CREAT
        ):
            raise PermissionError("synthetic retained create denied")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(container_module.os, "open", deny_retained_create)
    with pytest.raises(EncryptedBackupError, match="temp_create_failed"):
        _create(environment)
    assert not environment.target.exists()
    monkeypatch.undo()

    environment = _environment(tmp_path / "restore")
    _create(environment)
    original_mkdir = container_module.os.mkdir
    restore_root = environment.root / "restore-denied"

    def deny_restore_root(path, *args, **kwargs):
        if Path(path) == restore_root:
            raise PermissionError("synthetic restore mkdir denied")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(container_module.os, "mkdir", deny_restore_root)
    with pytest.raises(
        EncryptedBackupError, match="restore_root_create_failed"
    ):
        environment.service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert not restore_root.exists()


def test_same_content_source_path_replacement_is_detected(
    tmp_path: Path,
) -> None:
    environment = _environment(
        tmp_path,
        chunk_size=1024,
        document_bytes=b"same-content-replacement" * 1000,
    )
    original = environment.document.read_bytes()
    moved = environment.root / "document-original.bin"
    swapped = False

    def replace_source(phase: str) -> None:
        nonlocal swapped
        if phase == "writer_after_chunk:managed_document" and not swapped:
            swapped = True
            environment.document.rename(moved)
            environment.document.write_bytes(original)

    environment.service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=replace_source,
        chunk_size=1024,
    )

    with pytest.raises(EncryptedBackupError, match="backup_source_changed"):
        _create(environment)
    assert environment.document.read_bytes() == original
    assert moved.read_bytes() == original
    assert not environment.target.exists()


def test_source_change_and_read_permission_failure_are_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(
        tmp_path / "changed",
        chunk_size=1024,
        document_bytes=b"document-before-change" * 1000,
    )
    original_document = environment.document.read_bytes()
    changed = False

    def change_source(phase: str) -> None:
        nonlocal changed
        if phase == "writer_after_chunk:managed_document" and not changed:
            changed = True
            environment.document.write_bytes(b"mutated-during-stream")

    environment.service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=change_source,
        chunk_size=1024,
    )
    with pytest.raises(EncryptedBackupError, match="backup_source_changed"):
        _create(environment)
    assert not environment.target.exists()
    assert environment.database.is_file()
    assert original_document != environment.document.read_bytes()

    environment = _environment(tmp_path / "permission")
    original_open = container_module.os.open

    def denied_open(path, flags, *args, **kwargs):
        if Path(path) == environment.document and flags & os.O_RDONLY == os.O_RDONLY:
            raise PermissionError("synthetic denied")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(container_module.os, "open", denied_open)
    with pytest.raises(
        EncryptedBackupError, match="backup_regular_file_required"
    ):
        _create(environment)
    assert not environment.target.exists()


def test_verifier_read_failure_is_sanitized_and_non_mutating(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    container_before = environment.target.read_bytes()
    original_read = container_module.os.read
    calls = 0

    def denied_read(fd, size):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise PermissionError("synthetic denied")
        return original_read(fd, size)

    monkeypatch.setattr(container_module.os, "read", denied_read)
    with pytest.raises(
        EncryptedBackupError, match="backup_container_read_failed"
    ) as caught:
        environment.service.verify(
            test_root=environment.root,
            container=environment.target,
            dmk=environment.dmk,
            context=environment.context,
        )
    assert str(environment.target) not in str(caught.value)
    assert environment.target.read_bytes() == container_before


def test_verifier_detects_same_content_path_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    original = environment.target.read_bytes()
    moved = environment.root / "container-original.jkmebackup"
    original_read = container_module.os.read
    calls = 0

    def swap_after_binding(fd, size):
        nonlocal calls
        calls += 1
        if calls == 2:
            environment.target.rename(moved)
            environment.target.write_bytes(original)
        return original_read(fd, size)

    monkeypatch.setattr(container_module.os, "read", swap_after_binding)
    with pytest.raises(EncryptedBackupError, match="backup_container_changed"):
        environment.service.verify(
            test_root=environment.root,
            container=environment.target,
            dmk=environment.dmk,
            context=environment.context,
        )


def test_noncanonical_header_and_oversized_lengths_fail_before_allocation(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    header, frames = _split_container(environment.target)
    payload = json.loads(header.decode("ascii"))
    noncanonical_header = json.dumps(
        payload, sort_keys=False, indent=2
    ).encode("ascii")
    noncanonical = environment.root / "noncanonical.jkmebackup"
    _write_container_parts(noncanonical, noncanonical_header, frames)
    with pytest.raises(EncryptedBackupError, match="not_canonical"):
        environment.service.verify(
            test_root=environment.root,
            container=noncanonical,
            dmk=environment.dmk,
            context=environment.context,
        )

    oversized_header = environment.root / "oversized-header.jkmebackup"
    oversized_header.write_bytes(
        ENCRYPTED_BACKUP_MAGIC + _UINT32.pack(65 * 1024)
    )
    with pytest.raises(EncryptedBackupError, match="header_size_invalid"):
        environment.service.verify(
            test_root=environment.root,
            container=oversized_header,
            dmk=environment.dmk,
            context=environment.context,
        )

    oversized_record = environment.root / "oversized-record.jkmebackup"
    _write_container_parts(
        oversized_record,
        header,
        [_UINT32.pack(0xFFFFFFFF)],
    )
    with pytest.raises(EncryptedBackupError, match="record_size_invalid"):
        environment.service.verify(
            test_root=environment.root,
            container=oversized_record,
            dmk=environment.dmk,
            context=environment.context,
        )


@pytest.mark.parametrize(
    "phase",
    [
        "restore_after_root_created",
        "restore_write:sqlcipher_database",
        "restore_write:managed_document",
        "restore_before_fsync:sqlcipher_database",
        "restore_after_entry:sqlcipher_database",
        "restore_after_entry:managed_document",
        "restore_before_completion",
    ],
)
def test_restore_faults_never_publish_completion_or_mutate_sources(
    tmp_path: Path, phase: str
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    database_before = _hash(environment.database)
    document_before = _hash(environment.document)

    def fault(observed: str) -> None:
        if observed == phase:
            raise EncryptedBackupError("injected_restore_failure")

    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=fault,
        chunk_size=4096,
    )
    restore_root = environment.root / "restore-failed"
    with pytest.raises(EncryptedBackupError, match="injected_restore_failure"):
        service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert not (
        restore_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()
    assert _hash(environment.database) == database_before
    assert _hash(environment.document) == document_before


def test_restore_root_swap_before_open_and_expected_source_swap_fail_closed(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path / "root-swap")
    _create(environment)
    restore_root = environment.root / "restore-root-race"
    moved_root = environment.root / "restore-root-owned"
    foreign_root = environment.root / "restore-root-foreign"
    foreign_root.mkdir()

    def swap_root(phase: str) -> None:
        if phase == "restore_before_root_open":
            restore_root.rename(moved_root)
            restore_root.symlink_to(foreign_root, target_is_directory=True)

    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=swap_root,
        chunk_size=4096,
    )
    with pytest.raises(EncryptedBackupError, match="restore_root_changed"):
        service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert not list(foreign_root.iterdir())
    assert not (
        moved_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()

    environment = _environment(tmp_path / "source-swap")
    _create(environment)
    original = environment.document.read_bytes()
    original_path = environment.root / "expected-original.bin"
    swapped = False

    def swap_expected(phase: str) -> None:
        nonlocal swapped
        if phase == "restore_after_root_created" and not swapped:
            swapped = True
            environment.document.rename(original_path)
            environment.document.write_bytes(original)

    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=swap_expected,
        chunk_size=4096,
    )
    restore_root = environment.root / "restore-source-race"
    with pytest.raises(EncryptedBackupError, match="backup_source_changed"):
        service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert not (
        restore_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()


def test_restore_revalidates_restored_file_paths_before_completion(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    restore_root = environment.root / "restore-late-file-swap"
    moved = environment.root / "restored-document-original.bin"
    foreign = environment.root / "late-foreign.bin"
    foreign.write_bytes(b"late-foreign-bytes")

    def swap_restored_file(phase: str) -> None:
        if phase == "restore_before_completion":
            document_path = (
                restore_root
                / f"document-{environment.document_source.entry_id}.bin"
            )
            document_path.rename(moved)
            document_path.symlink_to(foreign)

    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=swap_restored_file,
        chunk_size=4096,
    )
    with pytest.raises(EncryptedBackupError, match="backup_source_changed"):
        service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert foreign.read_bytes() == b"late-foreign-bytes"
    assert not (
        restore_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()


def test_restore_existing_target_and_symlink_attack_fail_without_foreign_write(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    existing_root = environment.root / "existing-restore"
    existing_root.mkdir()
    foreign = environment.root / "foreign-restore-target"
    foreign.write_bytes(b"foreign-restore-bytes")
    (existing_root / "sentinel").write_bytes(b"sentinel")

    with pytest.raises(
        EncryptedBackupError, match="backup_restore_root_exists"
    ):
        environment.service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=existing_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert (existing_root / "sentinel").read_bytes() == b"sentinel"

    symlink_root = environment.root / "symlink-restore"
    symlink_root.symlink_to(existing_root, target_is_directory=True)
    with pytest.raises(
        EncryptedBackupError, match="backup_restore_root_exists"
    ):
        environment.service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=symlink_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )

    restore_root = environment.root / "symlink-entry-restore"

    def symlink_attack(phase: str) -> None:
        if phase == "restore_after_root_created":
            (restore_root / "database.sqlcipher").symlink_to(foreign)

    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=symlink_attack,
        chunk_size=4096,
    )
    with pytest.raises(
        EncryptedBackupError, match="backup_restore_target_create_failed"
    ):
        service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert foreign.read_bytes() == b"foreign-restore-bytes"
    assert not (
        restore_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()


def test_restore_enospc_wrong_database_key_and_root_swap_never_complete(
    tmp_path: Path, monkeypatch
) -> None:
    environment = _environment(tmp_path / "enospc")
    _create(environment)
    original_write = container_module.os.write
    calls = 0

    def enospc(fd, value):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError(28, "synthetic restore enospc")
        return original_write(fd, value)

    monkeypatch.setattr(container_module.os, "write", enospc)
    restore_root = environment.root / "restore-enospc"
    with pytest.raises(EncryptedBackupError, match="restore_write_failed"):
        environment.service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert not (
        restore_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()
    monkeypatch.setattr(container_module.os, "write", original_write)

    wrong_key_root = environment.root / "restore-wrong-db-key"
    with pytest.raises(
        EncryptedBackupError, match="backup_sqlcipher_verification_failed"
    ):
        environment.service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=wrong_key_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=secrets.token_bytes(32),
            expected_sources=_expected_sources(environment),
        )
    assert not (
        wrong_key_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()

    environment = _environment(tmp_path / "swap")
    _create(environment)
    restore_root = environment.root / "restore-swapped"
    moved_root = environment.root / "restore-owned-moved"
    replacement_root = environment.root / "restore-foreign"

    def swap_root(phase: str) -> None:
        if phase == "restore_before_completion":
            os.rename(restore_root, moved_root)
            replacement_root.mkdir()
            replacement_root.rename(restore_root)

    service = SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=environment.provider,
        fault_injector=swap_root,
        chunk_size=4096,
    )
    with pytest.raises(EncryptedBackupError, match="restore_root_changed"):
        service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )
    assert not (
        restore_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()
    assert not (
        moved_root / container_module.RESTORE_COMPLETION_FILENAME
    ).exists()


@pytest.mark.parametrize("failure_call", [1, 2, 3, 4, 5])
def test_each_restore_fsync_failure_has_defined_completion_state(
    tmp_path: Path, monkeypatch, failure_call: int
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    original_fsync = container_module.os.fsync
    calls = 0

    def fail_selected_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError(5, "synthetic restore fsync")
        return original_fsync(fd)

    monkeypatch.setattr(container_module.os, "fsync", fail_selected_fsync)
    restore_root = environment.root / "restore-fsync"
    with pytest.raises(EncryptedBackupError, match="fsync"):
        environment.service.restore(
            test_root=environment.root,
            container=environment.target,
            restore_root=restore_root,
            dmk=environment.dmk,
            context=environment.context,
            database_key=environment.database_key,
            expected_sources=_expected_sources(environment),
        )

    completion = restore_root / container_module.RESTORE_COMPLETION_FILENAME
    if failure_call < 5:
        assert not completion.exists()
    else:
        assert completion.is_file()
        payload = json.loads(completion.read_text(encoding="ascii"))
        assert payload["container_sha256"] == _hash(environment.target)


def test_large_document_streaming_uses_bounded_reads(
    tmp_path: Path, monkeypatch
) -> None:
    large = b"large-synthetic-block-" * (16 * 1024 * 1024 // 22)
    environment = _environment(
        tmp_path, chunk_size=256 * 1024, document_bytes=large
    )
    original_read = container_module.os.read
    requested_sizes: list[int] = []

    def bounded_read(fd, size):
        requested_sizes.append(size)
        return original_read(fd, size)

    monkeypatch.setattr(container_module.os, "read", bounded_read)
    _create(environment)
    verification = environment.service.verify(
        test_root=environment.root,
        container=environment.target,
        dmk=environment.dmk,
        context=environment.context,
    )

    assert verification.manifest.entries[1].plaintext_size == len(large)
    assert verification.manifest.entries[1].chunk_count > 60
    assert requested_sizes
    assert max(requested_sizes) <= 1024 * 1024


def test_empty_document_is_bound_by_one_authenticated_record(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path, document_bytes=b"")
    result = _create(environment)

    assert result.manifest.entries[1].plaintext_size == 0
    assert result.manifest.entries[1].chunk_count == 1
    restored = environment.service.restore(
        test_root=environment.root,
        container=environment.target,
        restore_root=environment.root / "empty-restore",
        dmk=environment.dmk,
        context=environment.context,
        database_key=environment.database_key,
        expected_sources=_expected_sources(environment),
    )
    assert restored.document_paths[0].read_bytes() == b""


def test_product_backup_restore_startup_and_identity_vfs_are_not_integrated(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    _create(environment)
    repository_root = Path(__file__).resolve().parents[1]
    protected_product_files = (
        repository_root / "src/core/backup.py",
        repository_root / "src/core/restore.py",
        repository_root / "src/core/restore_runtime.py",
        repository_root / "src/security/startup.py",
        repository_root / "src/desktop_app/main.py",
        repository_root
        / "src/desktop_app/adapters/backup_restore_desktop_adapter.py",
    )
    for path in protected_product_files:
        content = path.read_text(encoding="utf-8")
        assert "encrypted_backup_container" not in content
        assert "backup_container" not in content
        assert ".jkmebackup" not in content

    new_sources = (
        repository_root / "src/security/backup_container.py",
        repository_root
        / "prototypes/encrypted_backup_container/sprint9_container.py",
    )
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in new_sources
    ).lower()
    assert "from src.core.paths import runtimepaths" not in combined
    assert "import runtimepaths" not in combined
    assert "security.sqlite" not in combined
    assert "identity_vfs" not in combined
    assert "sqlcipher_export" not in combined
    assert "attach database" not in combined

    from src.core.backup import BackupVerifier

    with pytest.raises(Exception):
        BackupVerifier().verify(environment.target)
