from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.database_engine import SQLCipherConnectionProvider
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import DatabaseKey
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from src.security.integration_orchestrator import (
    SecurityIntegrationOrchestrator,
)


def _id(root: Path, role: str) -> str:
    value = bytearray(
        hashlib.sha256(f"{role}:{root.name}".encode("ascii")).digest()[:16]
    )
    value[6] = (value[6] & 0x0F) | 0x40
    value[8] = (value[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(value)))


def _keys(root: Path) -> tuple[LoadedDataMasterKey, DatabaseKey]:
    dmk = LoadedDataMasterKey(
        _id(root, "dmk"),
        1,
        hashlib.sha256(
            f"sprint11-test-dmk:{root.name}".encode("ascii")
        ).digest(),
    )
    database_key = DatabaseKey(
        _id(root, "database-key"),
        1,
        hashlib.sha256(
            f"sprint11-test-database-key:{root.name}".encode("ascii")
        ).digest(),
    )
    return dmk, database_key


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    crash_point = sys.argv[2]
    dmk, database_key = _keys(root)

    def fault(point: str) -> None:
        if point == crash_point:
            os._exit(91)

    orchestrator = SecurityIntegrationOrchestrator.from_environment(
        environ={
            "JKM_SECURITY_INTEGRATION_TEST": "1",
            "JKM_SECURITY_INTEGRATION_ROOT": str(root),
        },
        installation_id=_id(root, "installation"),
        database_context_id=_id(root, "database"),
        migration_id=_id(root, "migration"),
        migration_generation=1,
        dmk_loader=lambda: dmk,
        database_key_loader=lambda _observed_dmk: database_key,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=SQLCipherConnectionProvider(),
        app_instance_available=lambda: True,
        source_closed_probe=lambda _path: True,
        app_version="sprint11-crash-test",
        fault_injector=fault,
    )
    orchestrator.recover()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
