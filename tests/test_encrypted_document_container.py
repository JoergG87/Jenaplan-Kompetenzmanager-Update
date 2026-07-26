from __future__ import annotations

from dataclasses import replace
import hashlib
import errno
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid

import pytest

import prototypes.encrypted_document_container.sprint10_container as service_module
from prototypes.encrypted_document_container import (
    DocumentSource,
    SyntheticEncryptedDocumentServiceV1,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.document_container import (
    DOCUMENT_KEY_NONCE_BYTES,
    ENCRYPTED_DOCUMENT_MAGIC,
    DocumentContainerContextV1,
    DocumentContainerHeaderV1,
    DocumentKeyEnvelopeV1,
    EncryptedDocumentError,
    build_document_key_envelope,
    canonical_json,
)
from src.security.infrastructure.system import SystemClock, SystemRandomSource


_UINT32 = struct.Struct(">I")


def _environment(
    tmp_path: Path,
    *,
    payload: bytes = b"synthetic-secret-document-content" * 300,
    chunk_size: int = 256,
    fault=None,
):
    root = tmp_path.resolve()
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    sources = root / service_module.SOURCES_DIRECTORY
    storage = root / service_module.STORAGE_DIRECTORY
    exports = root / service_module.EXPORTS_DIRECTORY
    for directory in (sources, storage, exports):
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)
    (root / service_module.SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER).write_bytes(
        service_module.SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES
    )
    (storage / service_module.SYNTHETIC_DOCUMENT_STORAGE_MARKER).write_bytes(
        service_module.SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES
    )
    (exports / service_module.SYNTHETIC_DOCUMENT_EXPORT_MARKER).write_bytes(
        service_module.SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES
    )
    source_path = sources / "synthetic-input.bin"
    source_path.write_bytes(
        service_module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + payload
    )
    dmk = LoadedDataMasterKey(str(uuid.uuid4()), 1, os.urandom(32))
    context = DocumentContainerContextV1(
        installation_id=str(uuid.uuid4()),
        database_context_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        document_generation=1,
        app_format_version="sprint10-synthetic-v1",
    )
    storage_id = str(uuid.uuid4())
    service = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=fault,
        chunk_size=chunk_size,
    )
    source = DocumentSource(
        "synthetic-input.bin", "Original Schülername.pdf", "application/pdf"
    )
    return {
        "root": root,
        "sources": sources,
        "storage": storage,
        "exports": exports,
        "source_path": source_path,
        "payload": payload,
        "dmk": dmk,
        "context": context,
        "storage_id": storage_id,
        "service": service,
        "source": source,
    }


def _create(env):
    return env["service"].create(
        test_root=env["root"],
        source=env["source"],
        storage_id=env["storage_id"],
        dmk=env["dmk"],
        context=env["context"],
    )


def _split(path: Path) -> tuple[bytes, list[bytes]]:
    value = path.read_bytes()
    assert value.startswith(ENCRYPTED_DOCUMENT_MAGIC)
    offset = len(ENCRYPTED_DOCUMENT_MAGIC)
    header_size = _UINT32.unpack(value[offset : offset + 4])[0]
    offset += 4
    header = value[offset : offset + header_size]
    offset += header_size
    frames: list[bytes] = []
    while offset < len(value):
        size = _UINT32.unpack(value[offset : offset + 4])[0]
        frames.append(value[offset : offset + 4 + size])
        offset += 4 + size
    return header, frames


def _write(path: Path, header: bytes, frames: list[bytes], trailing=b"") -> None:
    path.write_bytes(
        ENCRYPTED_DOCUMENT_MAGIC
        + _UINT32.pack(len(header))
        + header
        + b"".join(frames)
        + trailing
    )


def _mutate_frame(frame: bytes) -> bytes:
    payload = bytearray(frame[4:])
    payload[len(payload) // 2] ^= 0x80
    return frame[:4] + bytes(payload)


def test_roundtrip_hides_document_metadata_and_plaintext(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    repeated = env["service"].verify(
        test_root=env["root"],
        container=result.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )
    assert repeated == replace(result, retained_path=None)
    assert result.retained_path is not None and result.retained_path.exists()
    assert os.stat(result.container_path).st_ino == os.stat(result.retained_path).st_ino
    assert result.manifest.plaintext_size == len(env["payload"])
    assert result.manifest.plaintext_sha256 == hashlib.sha256(env["payload"]).hexdigest()
    raw = result.container_path.read_bytes()
    for forbidden in (
        env["payload"][:24],
        b"Original",
        b"application/pdf",
        env["context"].document_id.encode(),
        env["context"].installation_id.encode(),
        env["source_path"].as_posix().encode(),
        env["dmk"].key_material,
    ):
        assert forbidden not in raw
    header_bytes, _frames = _split(result.container_path)
    header = json.loads(header_bytes)
    assert set(header) == {
        "chunk_size",
        "container_format",
        "container_id",
        "container_version",
        "document_key_generation",
        "document_key_id",
        "envelope",
        "header_version",
        "stream_algorithm",
        "stream_header",
    }
    assert "document_id" not in header and "storage_id" not in header


@pytest.mark.parametrize(
    "payload",
    [b"", b"x", b"x" * 3_000_000],
    ids=["empty", "small", "large"],
)
def test_empty_small_and_large_documents_stream(tmp_path: Path, payload: bytes) -> None:
    env = _environment(tmp_path, payload=payload, chunk_size=4096)
    result = _create(env)
    assert result.manifest.plaintext_size == len(payload)
    assert result.manifest.chunk_count == max(1, (len(payload) + 4095) // 4096)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda env: LoadedDataMasterKey(str(uuid.uuid4()), 1, os.urandom(32)),
        lambda env: LoadedDataMasterKey(env["dmk"].key_id, 2, os.urandom(32)),
    ],
)
def test_wrong_dmk_fails_closed(tmp_path: Path, mutate) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=result.container_path,
            dmk=mutate(env),
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )


@pytest.mark.parametrize(
    "context_change",
    [
        {"installation_id": lambda: str(uuid.uuid4())},
        {"database_context_id": lambda: str(uuid.uuid4())},
        {"document_id": lambda: str(uuid.uuid4())},
        {"document_generation": lambda: 2},
    ],
)
def test_wrong_bound_context_fails_closed(tmp_path: Path, context_change) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    key, factory = next(iter(context_change.items()))
    wrong = replace(env["context"], **{key: factory()})
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=result.container_path,
            dmk=env["dmk"],
            context=wrong,
            expected_storage_id=env["storage_id"],
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest",
        "first_chunk",
        "middle_chunk",
        "missing_chunk",
        "duplicate_chunk",
        "swapped_chunks",
        "missing_final",
        "truncated",
        "trailing",
    ],
)
def test_record_manipulation_truncation_and_extra_bytes_fail(
    tmp_path: Path, mutation: str
) -> None:
    env = _environment(tmp_path, payload=b"z" * 3000, chunk_size=256)
    result = _create(env)
    header, frames = _split(result.container_path)
    target = env["storage"] / f"{uuid.uuid4()}.w1.jkmedoc"
    changed = list(frames)
    trailing = b""
    if mutation == "manifest":
        changed[0] = _mutate_frame(changed[0])
    elif mutation == "first_chunk":
        changed[1] = _mutate_frame(changed[1])
    elif mutation == "middle_chunk":
        changed[len(changed) // 2] = _mutate_frame(changed[len(changed) // 2])
    elif mutation == "missing_chunk":
        del changed[2]
    elif mutation == "duplicate_chunk":
        changed.insert(2, changed[1])
    elif mutation == "swapped_chunks":
        changed[1], changed[2] = changed[2], changed[1]
    elif mutation == "missing_final":
        changed.pop()
    elif mutation == "truncated":
        changed[-1] = changed[-1][:-1]
    else:
        trailing = b"x"
    _write(target, header, changed, trailing)
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=target,
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("container_version", 2),
        ("container_version", True),
        ("stream_algorithm", "unknown"),
        ("extra", "forbidden"),
    ],
)
def test_unknown_header_versions_algorithms_and_fields_fail(
    tmp_path: Path, field: str, value
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    header, frames = _split(result.container_path)
    payload = json.loads(header)
    payload[field] = value
    target = env["storage"] / f"{uuid.uuid4()}.w1.jkmedoc"
    _write(target, canonical_json(payload), frames)
    with pytest.raises(EncryptedDocumentError):
        env["service"].inspect_header(test_root=env["root"], container=target)


def test_envelope_manipulation_and_wrong_storage_id_fail(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    header, frames = _split(result.container_path)
    payload = json.loads(header)
    ciphertext = payload["envelope"]["ciphertext"]
    payload["envelope"]["ciphertext"] = (
        ("A" if ciphertext[0] != "A" else "B") + ciphertext[1:]
    )
    target = env["storage"] / f"{uuid.uuid4()}.w1.jkmedoc"
    _write(target, canonical_json(payload), frames)
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=target,
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=result.container_path,
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=str(uuid.uuid4()),
        )


def test_valid_envelope_with_wrong_document_key_fails_stream_authentication(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    wrong_placeholder = DocumentKeyEnvelopeV1(
        document_key_id=result.header.document_key_id,
        document_key_generation=result.header.document_key_generation,
        rewrap_revision=1,
        wrapping_dmk_key_id=env["dmk"].key_id,
        wrapping_dmk_generation=env["dmk"].generation,
        nonce=os.urandom(DOCUMENT_KEY_NONCE_BYTES),
        ciphertext=b"",
    )
    bare = replace(result.header, envelope=wrong_placeholder)
    wrong_envelope = build_document_key_envelope(
        env["dmk"],
        context=env["context"],
        header_without_envelope=bare,
        document_key=os.urandom(32),
        nonce=wrong_placeholder.nonce,
        rewrap_revision=1,
    )
    wrong_header = replace(result.header, envelope=wrong_envelope)
    _old_header, frames = _split(result.container_path)
    target = env["storage"] / f"{uuid.uuid4()}.w1.jkmedoc"
    _write(target, wrong_header.to_bytes(), frames)
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=target,
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )


class _Consumer:
    def __init__(self) -> None:
        self.value = bytearray()
        self.finished = False
        self.aborted = None

    def start(self, manifest) -> None:
        self.manifest = manifest

    def write(self, chunk: bytes) -> None:
        self.value.extend(chunk)

    def finish(self, result) -> None:
        self.finished = True

    def abort(self, code: str) -> None:
        self.aborted = code


def test_controlled_reader_preverifies_and_finishes_only_after_full_stream(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    consumer = _Consumer()
    env["service"].stream_verified(
        test_root=env["root"],
        container=result.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
        consumer=consumer,
    )
    assert bytes(consumer.value) == env["payload"]
    assert consumer.finished and consumer.aborted is None


def test_source_symlink_hardlink_traversal_and_existing_target_are_rejected(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    original_hash = hashlib.sha256(env["source_path"].read_bytes()).hexdigest()
    env["source_path"].unlink()
    outside = tmp_path.parent / f"outside-{uuid.uuid4()}.bin"
    outside.write_bytes(
        service_module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + b"outside"
    )
    env["source_path"].symlink_to(outside)
    with pytest.raises(EncryptedDocumentError):
        _create(env)
    env["source_path"].unlink()
    os.link(outside, env["source_path"])
    with pytest.raises(EncryptedDocumentError):
        _create(env)
    assert hashlib.sha256(outside.read_bytes()).hexdigest() != original_hash
    with pytest.raises(EncryptedDocumentError):
        env["service"].create(
            test_root=env["root"],
            source=replace(env["source"], source_name="../outside"),
            storage_id=env["storage_id"],
            dmk=env["dmk"],
            context=env["context"],
        )
    env["source_path"].unlink()
    env["source_path"].write_bytes(
        service_module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + env["payload"]
    )
    result = _create(env)
    before = result.container_path.read_bytes()
    with pytest.raises(EncryptedDocumentError):
        _create(env)
    assert result.container_path.read_bytes() == before


def test_metadata_validation_happens_before_retained_file_creation(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    with pytest.raises(EncryptedDocumentError):
        env["service"].create(
            test_root=env["root"],
            source=replace(env["source"], mime_type="application/x-unknown"),
            storage_id=env["storage_id"],
            dmk=env["dmk"],
            context=env["context"],
        )
    assert [
        item.name
        for item in env["storage"].iterdir()
        if item.name != service_module.SYNTHETIC_DOCUMENT_STORAGE_MARKER
    ] == []


def test_container_path_exchange_during_verification_blocks_success(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    displaced = env["storage"] / f"{uuid.uuid4()}.w1.jkmedoc"
    swapped = False

    def fault(phase: str) -> None:
        nonlocal swapped
        if phase == "verifier_after_manifest" and not swapped:
            swapped = True
            os.replace(result.container_path, displaced)
            result.container_path.write_bytes(b"foreign replacement")

    verifier = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=fault,
        chunk_size=256,
    )
    with pytest.raises(EncryptedDocumentError, match="document_container_changed"):
        verifier.verify(
            test_root=env["root"],
            container=result.container_path,
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )
    assert result.container_path.read_bytes() == b"foreign replacement"


def test_source_path_exchange_during_write_blocks_publication(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    replacement = env["sources"] / "replacement.bin"
    replacement.write_bytes(
        service_module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + b"replacement"
    )
    swapped = False

    def fault(phase: str) -> None:
        nonlocal swapped
        if phase == "writer_after_manifest" and not swapped:
            swapped = True
            os.replace(replacement, env["source_path"])

    env["service"] = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=fault,
        chunk_size=256,
    )
    with pytest.raises(EncryptedDocumentError, match="document_source_changed"):
        _create(env)
    assert not tuple(env["storage"].glob("*.jkmedoc"))


def test_root_exchange_before_first_write_is_rejected(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    moved = tmp_path.parent / f"moved-{uuid.uuid4()}"
    foreign_marker = b"foreign-unchanged"
    swapped = False

    def fault(phase: str) -> None:
        nonlocal swapped
        if phase != "writer_after_source_bound" or swapped:
            return
        swapped = True
        os.rename(env["root"], moved)
        env["root"].mkdir(mode=0o700)
        for name in (
            service_module.SOURCES_DIRECTORY,
            service_module.STORAGE_DIRECTORY,
            service_module.EXPORTS_DIRECTORY,
        ):
            (env["root"] / name).mkdir(mode=0o700)
        (env["root"] / service_module.SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER).write_bytes(
            service_module.SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES
        )
        (
            env["root"]
            / service_module.STORAGE_DIRECTORY
            / service_module.SYNTHETIC_DOCUMENT_STORAGE_MARKER
        ).write_bytes(service_module.SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES)
        (
            env["root"]
            / service_module.EXPORTS_DIRECTORY
            / service_module.SYNTHETIC_DOCUMENT_EXPORT_MARKER
        ).write_bytes(service_module.SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES)
        (
            env["root"] / service_module.STORAGE_DIRECTORY / "foreign.bin"
        ).write_bytes(foreign_marker)

    env["service"] = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=fault,
        chunk_size=256,
    )
    with pytest.raises(EncryptedDocumentError, match="document_test_root_changed"):
        _create(env)
    assert (
        env["root"] / service_module.STORAGE_DIRECTORY / "foreign.bin"
    ).read_bytes() == foreign_marker


@pytest.mark.parametrize("failure", ["enospc", "fsync", "publish"])
def test_io_fsync_and_publication_failures_never_create_visible_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    env = _environment(tmp_path)
    if failure == "enospc":
        original = service_module.os.write
        calls = 0

        def failing_write(fd, value):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(errno.ENOSPC, "synthetic")
            return original(fd, value)

        monkeypatch.setattr(service_module.os, "write", failing_write)
    elif failure == "fsync":
        monkeypatch.setattr(
            service_module.os,
            "fsync",
            lambda _fd: (_ for _ in ()).throw(OSError(errno.EIO, "synthetic")),
        )
    else:
        monkeypatch.setattr(
            service_module.os,
            "link",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                OSError(errno.EPERM, "synthetic")
            ),
        )
    with pytest.raises(EncryptedDocumentError):
        _create(env)
    assert not tuple(env["storage"].glob("*.jkmedoc"))


def test_private_root_permissions_are_required(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    os.chmod(env["root"], 0o755)
    with pytest.raises(EncryptedDocumentError):
        _create(env)


def test_all_reads_are_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = _environment(tmp_path, payload=b"x" * 2_000_000)
    original = service_module.os.read
    requested: list[int] = []

    def bounded_read(fd: int, size: int) -> bytes:
        requested.append(size)
        assert size <= 1024 * 1024
        return original(fd, size)

    monkeypatch.setattr(service_module.os, "read", bounded_read)
    result = _create(env)
    env["service"].verify(
        test_root=env["root"],
        container=result.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )
    assert requested


def test_import_is_side_effect_free_and_product_has_no_sprint10_imports(
    tmp_path: Path,
) -> None:
    repository = Path.cwd()
    script = (
        "import sys\n"
        "import src.security\n"
        "import src.security.startup\n"
        "forbidden = {\n"
        "    'src.security.document_container',\n"
        "    'prototypes.encrypted_document_container',\n"
        "    'prototypes.encrypted_document_container.sprint10_container',\n"
        "}\n"
        "raise SystemExit(1 if forbidden.intersection(sys.modules) else 0)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(repository)},
        check=False,
        capture_output=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert tuple(tmp_path.iterdir()) == ()
    for root in (Path("src/core"), Path("src/application"), Path("src/desktop_app")):
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "document_container" not in text
            assert "encrypted_document_container" not in text
    assert "document_container" not in Path("src/security/startup.py").read_text(
        encoding="utf-8"
    )
