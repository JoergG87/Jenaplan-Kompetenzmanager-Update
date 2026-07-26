from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from prototypes.encrypted_document_container import SyntheticEncryptedDocumentServiceV1
import prototypes.encrypted_document_container.sprint10_container as module
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from tests.helpers.sprint10_document_crash_worker import (
    CONTEXT,
    DMK,
    NEW_DMK,
    NEW_STORAGE_ID,
    PAYLOAD,
    POINTER_NAME,
    STORAGE_ID,
)


@pytest.mark.parametrize(
    ("mode", "phase"),
    [
        ("write", "writer_after_header_prefix"),
        ("write", "writer_after_envelope"),
        ("write", "writer_after_manifest"),
        ("write", "writer_after_first_chunk"),
        ("write", "writer_after_middle_chunk"),
        ("write", "writer_before_final"),
        ("write", "writer_after_final"),
        ("write", "writer_after_file_fsync"),
        ("write", "writer_after_retained_directory_fsync"),
        ("write", "verifier_after_manifest"),
        ("write", "writer_after_preverify"),
        ("write", "writer_after_publish"),
        ("write", "writer_after_published_verify"),
        ("export", "export_after_chunk"),
        ("export", "export_after_fsync"),
        ("export", "export_after_publish"),
        ("exchange", "exchange_after_new_generation_verified"),
        ("exchange", "exchange_after_pointer_switch"),
        ("exchange", "exchange_after_retained_mark"),
        ("rewrap", "rewrap_after_preverify"),
        ("rewrap", "rewrap_after_publish"),
    ],
)
def test_real_process_abort_never_accepts_partial_output(
    tmp_path: Path, mode: str, phase: str
) -> None:
    root = tmp_path / "crash-root"
    completed = subprocess.run(
        [
            sys.executable,
            "tests/helpers/sprint10_document_crash_worker.py",
            mode,
            phase,
            str(root),
        ],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        timeout=15,
    )
    assert completed.returncode == 73
    assert completed.stdout == b"" and completed.stderr == b""
    source = root / module.SOURCES_DIRECTORY / "synthetic.bin"
    assert source.read_bytes() == module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + PAYLOAD
    storage = root / module.STORAGE_DIRECTORY
    assert (storage / "foreign.keep").read_bytes() == b"foreign-storage-unchanged"
    for path in storage.iterdir():
        if path.name == module.SYNTHETIC_DOCUMENT_STORAGE_MARKER:
            continue
        assert PAYLOAD[:24] not in path.read_bytes()
    service = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(), clock=SystemClock(), chunk_size=256
    )
    visible = sorted(storage.glob("*.jkmedoc"))
    for path in visible:
        storage_id = NEW_STORAGE_ID if path.name.startswith(NEW_STORAGE_ID) else STORAGE_ID
        context = (
            __import__("dataclasses").replace(CONTEXT, document_generation=2)
            if storage_id == NEW_STORAGE_ID
            else CONTEXT
        )
        dmk = NEW_DMK if mode == "rewrap" and ".w2." in path.name else DMK
        service.verify(
            test_root=root,
            container=path,
            dmk=dmk,
            context=context,
            expected_storage_id=storage_id,
        )
    if mode in {"exchange", "rewrap"}:
        old = storage / f"{STORAGE_ID}.w1.jkmedoc"
        assert old.exists()
        service.verify(
            test_root=root,
            container=old,
            dmk=DMK,
            context=CONTEXT,
            expected_storage_id=STORAGE_ID,
        )
    if mode == "exchange":
        expected_pointer = (
            STORAGE_ID
            if phase == "exchange_after_new_generation_verified"
            else NEW_STORAGE_ID
        )
        assert (root / POINTER_NAME).read_text(encoding="ascii") == expected_pointer
        old_status = os.stat(storage / f"{STORAGE_ID}.w1.jkmedoc")
        retained_old = tuple(storage.glob(f".{STORAGE_ID}.w1.jkmedoc.*.retained"))
        assert len(retained_old) == 1
        assert os.stat(retained_old[0]).st_ino == old_status.st_ino
    export = root / module.EXPORTS_DIRECTORY / "export.pdf"
    assert (
        root / module.EXPORTS_DIRECTORY / "foreign.keep"
    ).read_bytes() == b"foreign-export-unchanged"
    hidden_exports = tuple(
        (root / module.EXPORTS_DIRECTORY).glob(".export.pdf.*.retained")
    )
    if export.exists():
        assert export.read_bytes() == PAYLOAD
        assert hashlib.sha256(export.read_bytes()).hexdigest() == hashlib.sha256(
            PAYLOAD
        ).hexdigest()
        assert hidden_exports == ()
    elif mode == "export":
        assert len(hidden_exports) == 1
        assert len(hidden_exports[0].read_bytes()) <= len(PAYLOAD)
