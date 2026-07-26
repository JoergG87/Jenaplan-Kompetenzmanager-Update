from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import sys

from prototypes.encrypted_document_container import (
    DocumentSource,
    SyntheticEncryptedDocumentServiceV1,
)
import prototypes.encrypted_document_container.sprint10_container as module
from src.security.data_keys import LoadedDataMasterKey
from src.security.document_container import DocumentContainerContextV1
from src.security.infrastructure.system import SystemClock, SystemRandomSource


DMK_ID = "11111111-1111-4111-8111-111111111111"
NEW_DMK_ID = "77777777-7777-4777-8777-777777777777"
INSTALLATION_ID = "22222222-2222-4222-8222-222222222222"
DATABASE_ID = "33333333-3333-4333-8333-333333333333"
DOCUMENT_ID = "44444444-4444-4444-8444-444444444444"
STORAGE_ID = "55555555-5555-4555-8555-555555555555"
NEW_STORAGE_ID = "66666666-6666-4666-8666-666666666666"
DMK = LoadedDataMasterKey(DMK_ID, 1, b"\x11" * 32)
NEW_DMK = LoadedDataMasterKey(NEW_DMK_ID, 2, b"\x22" * 32)
CONTEXT = DocumentContainerContextV1(
    INSTALLATION_ID,
    DATABASE_ID,
    DOCUMENT_ID,
    1,
    "sprint10-crash-worker-v1",
)
PAYLOAD = b"crash-worker-secret-payload" * 500
POINTER_NAME = "synthetic-current-storage-id"


def _setup(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    sources = root / module.SOURCES_DIRECTORY
    storage = root / module.STORAGE_DIRECTORY
    exports = root / module.EXPORTS_DIRECTORY
    for directory in (sources, storage, exports):
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)
    (root / module.SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER).write_bytes(
        module.SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES
    )
    (storage / module.SYNTHETIC_DOCUMENT_STORAGE_MARKER).write_bytes(
        module.SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES
    )
    (exports / module.SYNTHETIC_DOCUMENT_EXPORT_MARKER).write_bytes(
        module.SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES
    )
    (sources / "synthetic.bin").write_bytes(
        module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + PAYLOAD
    )
    (storage / "foreign.keep").write_bytes(b"foreign-storage-unchanged")
    (exports / "foreign.keep").write_bytes(b"foreign-export-unchanged")
    (root / POINTER_NAME).write_text(STORAGE_ID, encoding="ascii")
    return sources, storage, exports


def _service(crash_phase: str | None):
    def fault(phase: str) -> None:
        if phase == crash_phase:
            os._exit(73)

    return SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=fault if crash_phase else None,
        chunk_size=256,
    )


def main() -> int:
    mode, phase, root_text = sys.argv[1:4]
    root = Path(root_text).resolve()
    _setup(root)
    source = DocumentSource(
        "synthetic.bin", "synthetic.pdf", "application/pdf"
    )
    if mode == "write":
        _service(phase).create(
            test_root=root,
            source=source,
            storage_id=STORAGE_ID,
            dmk=DMK,
            context=CONTEXT,
        )
    elif mode == "export":
        created = _service(None).create(
            test_root=root,
            source=source,
            storage_id=STORAGE_ID,
            dmk=DMK,
            context=CONTEXT,
        )
        _service(phase).export(
            test_root=root,
            container=created.container_path,
            export_name="export.pdf",
            dmk=DMK,
            context=CONTEXT,
            expected_storage_id=STORAGE_ID,
        )
    elif mode == "exchange":
        created = _service(None).create(
            test_root=root,
            source=source,
            storage_id=STORAGE_ID,
            dmk=DMK,
            context=CONTEXT,
        )
        def switch(prepared) -> bool:
            pointer = root / POINTER_NAME
            fd = os.open(pointer, os.O_WRONLY | os.O_TRUNC)
            try:
                os.write(fd, prepared.manifest.storage_id.encode("ascii"))
                os.fsync(fd)
            finally:
                os.close(fd)
            return True

        _service(phase).exchange_generation(
            test_root=root,
            previous_container=created.container_path,
            previous_dmk=DMK,
            previous_context=CONTEXT,
            previous_storage_id=STORAGE_ID,
            new_source=source,
            new_storage_id=NEW_STORAGE_ID,
            new_dmk=DMK,
            new_context=replace(CONTEXT, document_generation=2),
            pointer_switch=switch,
        )
    elif mode == "rewrap":
        created = _service(None).create(
            test_root=root,
            source=source,
            storage_id=STORAGE_ID,
            dmk=DMK,
            context=CONTEXT,
        )
        _service(phase).rewrap(
            test_root=root,
            container=created.container_path,
            old_dmk=DMK,
            new_dmk=NEW_DMK,
            context=CONTEXT,
            expected_storage_id=STORAGE_ID,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
