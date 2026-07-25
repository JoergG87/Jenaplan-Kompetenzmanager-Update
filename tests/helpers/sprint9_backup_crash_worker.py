"""Subprocess crash worker for the isolated Security Sprint 9 prototype."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import prototypes.encrypted_backup_container.sprint9_container as container_module
from prototypes.encrypted_backup_container import (
    BackupSourceFile,
    SyntheticEncryptedBackupServiceV1,
)
from src.core.database_engine import SQLCipherConnectionProvider
from src.security.backup_container import (
    BackupContainerContextV1,
    BackupEntryRole,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.infrastructure.system import SystemClock, SystemRandomSource


DATABASE_KEY = bytes(range(32))
DMK_MATERIAL = bytes(reversed(range(32)))
DMK_ID = "11111111-1111-4111-8111-111111111111"
INSTALLATION_ID = "22222222-2222-4222-8222-222222222222"
DATABASE_CONTEXT_ID = "33333333-3333-4333-8333-333333333333"
DATABASE_ENTRY_ID = "44444444-4444-4444-8444-444444444444"
DOCUMENT_ENTRY_ID = "55555555-5555-4555-8555-555555555555"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _values(root: Path, *, create_sources: bool):
    provider = SQLCipherConnectionProvider()
    driver = provider._load_driver()
    probe = driver.connect(":memory:", cached_statements=0)
    sqlite_version = str(probe.execute("SELECT sqlite_version()").fetchone()[0])
    sqlcipher_version = str(
        probe.execute("PRAGMA cipher_version").fetchone()[0]
    )
    probe.close()
    database = root / "source.sqlcipher"
    document = root / "document.bin"
    foreign = root / "foreign.bin"
    if create_sources:
        connection = provider.connect(
            database, create=True, key_material=DATABASE_KEY
        )
        connection.execute(
            f"PRAGMA application_id = "
            f"{container_module.SYNTHETIC_BACKUP_APPLICATION_ID}"
        )
        connection.execute(
            f"PRAGMA user_version = "
            f"{container_module.SYNTHETIC_BACKUP_USER_VERSION}"
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
        connection.commit()
        connection.close()
        document.write_bytes(b"crash-document" * 5000)
        foreign.write_bytes(b"foreign-file-must-never-change")
        (root / "source-hashes.json").write_text(
            json.dumps(
                {
                    "database": _sha256(database),
                    "document": _sha256(document),
                    "foreign": _sha256(foreign),
                },
                sort_keys=True,
            ),
            encoding="ascii",
        )
    return {
        "provider": provider,
        "database": database,
        "document": document,
        "foreign": foreign,
        "dmk": LoadedDataMasterKey(DMK_ID, 1, DMK_MATERIAL),
        "context": BackupContainerContextV1(
            installation_id=INSTALLATION_ID,
            database_context_id=DATABASE_CONTEXT_ID,
            app_version="sprint9-crash-worker",
            sqlite_version=sqlite_version,
            sqlcipher_version=sqlcipher_version,
        ),
        "database_source": BackupSourceFile(
            database,
            DATABASE_ENTRY_ID,
            BackupEntryRole.SQLCIPHER_DATABASE,
        ),
        "document_source": BackupSourceFile(
            document,
            DOCUMENT_ENTRY_ID,
            BackupEntryRole.MANAGED_DOCUMENT,
        ),
    }


def _service(values, phase: str | None):
    def fault(observed: str) -> None:
        if phase is not None and observed == phase:
            os._exit(73)

    return SyntheticEncryptedBackupServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=values["provider"],
        fault_injector=fault,
        chunk_size=4096,
    )


def _create(root: Path, values, service) -> None:
    service.create(
        test_root=root,
        target=root / "container.jkmebackup",
        dmk=values["dmk"],
        context=values["context"],
        database_source=values["database_source"],
        document_sources=(values["document_source"],),
        database_key=DATABASE_KEY,
    )


def run(argv: list[str]) -> int:
    if len(argv) != 3:
        return 2
    mode, phase, root_value = argv
    root = Path(root_value).resolve()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    (root / container_module.SYNTHETIC_BACKUP_TEST_ROOT_MARKER).write_bytes(
        container_module.SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES
    )
    if mode == "write":
        values = _values(root, create_sources=True)
        _create(root, values, _service(values, phase))
        return 3
    if mode == "restore":
        values = _values(root, create_sources=True)
        _create(root, values, _service(values, None))
        _service(values, phase).restore(
            test_root=root,
            container=root / "container.jkmebackup",
            restore_root=root / "restore",
            dmk=values["dmk"],
            context=values["context"],
            database_key=DATABASE_KEY,
            expected_sources={
                DATABASE_ENTRY_ID: values["database"],
                DOCUMENT_ENTRY_ID: values["document"],
            },
        )
        return 4
    if mode == "verify":
        values = _values(root, create_sources=False)
        _service(values, None).verify(
            test_root=root,
            container=root / "container.jkmebackup",
            dmk=values["dmk"],
            context=values["context"],
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
