from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys

from src.core.runtime_root_protection import prepare_synthetic_test_root
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_key_runtime import (
    DMK_DATABASE_KEY_RUNTIME_GATE_ENV,
    DMK_DATABASE_KEY_RUNTIME_MARKER,
    DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES,
    DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX,
    DMK_DATABASE_KEY_RUNTIME_ROOT_ENV,
    DatabaseKeyRuntimePaths,
    LoadedDatabaseKeyRuntime,
)
from src.security.database_keys import DatabaseKey
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCipherConnectionProvider,
)
from src.security.final_v3_document_runtime import (
    FinalV3DocumentConnectionFactory,
    FinalV3DocumentRuntime,
    FinalV3DocumentRuntimePaths,
    FinalV3DocumentSchemaV1,
    _initialize_container_layout,
)
from src.security.final_v4_sqlcipher_runtime import (
    FINAL_V4_SQLCIPHER_RUNTIME_GATE_ENV,
    FINAL_V4_SQLCIPHER_RUNTIME_MARKER,
    FINAL_V4_SQLCIPHER_RUNTIME_MARKER_BYTES,
    FinalV4SQLCipherRuntimePaths,
)
from src.security.infrastructure.system import SystemClock, SystemRandomSource


INSTALLATION_ID = "11111111-1111-4111-8111-111111111111"
DATABASE_CONTEXT_ID = "22222222-2222-4222-8222-222222222222"
DMK_ID = "33333333-3333-4333-8333-333333333333"
DATABASE_KEY_ID = "44444444-4444-4444-8444-444444444444"
DOCUMENT_ID = "55555555-5555-4555-8555-555555555555"
OLD_PAYLOAD = b"old-active-generation"
NEW_PAYLOAD = b"new-prepared-generation"


class SQLiteFactory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self, *, create: bool):
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def connect_read_only(self):
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def paths_for(base: Path) -> FinalV3DocumentRuntimePaths:
    root = base / f"{DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX}document-crash"
    key_paths = DatabaseKeyRuntimePaths.for_root(root)
    return FinalV3DocumentRuntimePaths.for_final_v4(
        FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
    )


def loaded_keys() -> LoadedDatabaseKeyRuntime:
    dmk = LoadedDataMasterKey(DMK_ID, 1, b"\x31" * 32)
    database_key = DatabaseKey(DATABASE_KEY_ID, 1, b"\x52" * 32)
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


def open_runtime(base: Path, fault_hook=None) -> FinalV3DocumentRuntime:
    paths = paths_for(base)
    return FinalV3DocumentRuntime(
        paths=paths,
        factory=SQLiteFactory(paths.database),  # type: ignore[arg-type]
        loaded_keys=loaded_keys(),
        installation_id=INSTALLATION_ID,
        source_root=base / "source-input",
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_hook=fault_hook,
    )


def exact_environment(base: Path) -> dict[str, str]:
    root = base / f"{DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX}document-crash"
    return {
        DMK_DATABASE_KEY_RUNTIME_GATE_ENV: "1",
        DMK_DATABASE_KEY_RUNTIME_ROOT_ENV: str(root),
        FINAL_V4_SQLCIPHER_RUNTIME_GATE_ENV: "1",
    }


def exact_factory(base: Path) -> FinalV3DocumentConnectionFactory:
    return FinalV3DocumentConnectionFactory(
        provider=SQLCipherConnectionProvider(
            expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        ),
        paths=paths_for(base),
        loaded_keys=loaded_keys(),
        environ=exact_environment(base),
    )


def open_exact_runtime(base: Path, fault_hook=None) -> FinalV3DocumentRuntime:
    return FinalV3DocumentRuntime(
        paths=paths_for(base),
        factory=exact_factory(base),
        loaded_keys=loaded_keys(),
        installation_id=INSTALLATION_ID,
        source_root=base / "source-input",
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_hook=fault_hook,
    )


def setup(base: Path) -> None:
    prepare_synthetic_test_root(base)
    root = base / f"{DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX}document-crash"
    root.mkdir(mode=0o700)
    paths = paths_for(base)
    paths.final_v4.runtime_root.mkdir(mode=0o700)
    factory = SQLiteFactory(paths.database)
    with factory.connect(create=True) as connection:
        FinalV3DocumentSchemaV1.initialize(
            connection,
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            created_at="2026-08-03T10:00:00Z",
        )
    _initialize_container_layout(paths)
    (base / "source-input").mkdir(mode=0o700)
    runtime = open_runtime(base)
    (runtime.source_root / "old.bin").write_bytes(OLD_PAYLOAD)
    runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="old.bin",
        original_filename="old.pdf",
        mime_type="application/pdf",
    )


def setup_exact(base: Path) -> None:
    prepare_synthetic_test_root(base)
    root = base / f"{DMK_DATABASE_KEY_RUNTIME_ROOT_PREFIX}document-crash"
    root.mkdir(mode=0o700)
    for name, payload in (
        (DMK_DATABASE_KEY_RUNTIME_MARKER, DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES),
        (
            FINAL_V4_SQLCIPHER_RUNTIME_MARKER,
            FINAL_V4_SQLCIPHER_RUNTIME_MARKER_BYTES,
        ),
    ):
        marker = root / name
        marker.write_bytes(payload)
        marker.chmod(0o600)
    paths = paths_for(base)
    paths.final_v4.runtime_root.mkdir(mode=0o700)
    with exact_factory(base).connect(create=True) as connection:
        FinalV3DocumentSchemaV1.initialize(
            connection,
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            created_at="2026-08-03T10:00:00Z",
        )
    _initialize_container_layout(paths)
    (base / "source-input").mkdir(mode=0o700)
    runtime = open_exact_runtime(base)
    (runtime.source_root / "old.bin").write_bytes(OLD_PAYLOAD)
    runtime.replace(
        document_id=DOCUMENT_ID,
        source_name="old.bin",
        original_filename="old.pdf",
        mime_type="application/pdf",
    )


def crash(base: Path, boundary: str) -> None:
    def fault(observed: str) -> None:
        if observed == boundary:
            os._exit(73)

    paths = paths_for(base)
    (base / "source-input" / "new.bin").write_bytes(NEW_PAYLOAD)
    if boundary in {"during_pointer_switch", "after_activation_before_retained"}:
        prepared = open_runtime(base).prepare(
            document_id=DOCUMENT_ID,
            source_name="new.bin",
            original_filename="new.pdf",
            mime_type="application/pdf",
        )
        open_runtime(base, fault_hook=fault).activate(
            document_id=DOCUMENT_ID,
            document_generation=prepared.document_generation,
        )
    else:
        open_runtime(base, fault_hook=fault).prepare(
            document_id=DOCUMENT_ID,
            source_name="new.bin",
            original_filename="new.pdf",
            mime_type="application/pdf",
        )
    raise RuntimeError("crash boundary was not reached")


def crash_exact(base: Path, boundary: str) -> None:
    def fault(observed: str) -> None:
        if observed == boundary:
            os._exit(73)

    (base / "source-input" / "new.bin").write_bytes(NEW_PAYLOAD)
    if boundary in {"during_pointer_switch", "after_activation_before_retained"}:
        prepared = open_exact_runtime(base).prepare(
            document_id=DOCUMENT_ID,
            source_name="new.bin",
            original_filename="new.pdf",
            mime_type="application/pdf",
        )
        open_exact_runtime(base, fault_hook=fault).activate(
            document_id=DOCUMENT_ID,
            document_generation=prepared.document_generation,
        )
    else:
        open_exact_runtime(base, fault_hook=fault).prepare(
            document_id=DOCUMENT_ID,
            source_name="new.bin",
            original_filename="new.pdf",
            mime_type="application/pdf",
        )
    raise RuntimeError("crash boundary was not reached")


def main() -> int:
    mode = sys.argv[1]
    base = Path(sys.argv[2]).resolve()
    if mode == "setup":
        setup(base)
        return 0
    if mode == "crash":
        crash(base, sys.argv[3])
        return 1
    if mode == "exact-setup":
        setup_exact(base)
        return 0
    if mode == "exact-crash":
        crash_exact(base, sys.argv[3])
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
