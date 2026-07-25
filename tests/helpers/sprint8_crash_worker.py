from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototypes.database_encryption_migration.sprint8_orchestrator import (
    Sprint8MigrationPaths,
    SyntheticMigrationOrchestratorV2,
)
from src.core.database_engine import SQLCipherConnectionProvider
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DatabaseKeyEnvelopeService,
    derive_database_key_registry_auth_key,
)
from src.security.infrastructure.database_key_envelope_repository import (
    DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.simplified_migration_state import (
    AuthenticatedMigrationJournalV2Repository,
    ExternalReplayAnchorV2Repository,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from src.security.migration_lock import ExclusiveMigrationLock


def main() -> int:
    config_path = Path(sys.argv[1])
    config = json.loads(config_path.read_text("ascii"))
    root = Path(config["root"])
    paths = Sprint8MigrationPaths.in_test_root(root)
    dmk = LoadedDataMasterKey(
        config["dmk_key_id"],
        config["dmk_generation"],
        bytes.fromhex(config["dmk_hex"]),
    )
    permissions = PlatformFilePermissionManager()
    envelopes = FileDatabaseKeyEnvelopeRepository(
        root / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME, permissions
    )
    envelope_service = DatabaseKeyEnvelopeService(
        repository=envelopes,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
    )

    def load_database_key(observed_dmk):
        key = envelope_service.load_active(observed_dmk, expected_generation=1)
        registry_key = derive_database_key_registry_auth_key(
            observed_dmk, database_context_id=config["database_context_id"]
        )
        _items, digest = envelopes.load_with_digest(registry_key)
        return key, digest

    migration_lock = ExclusiveMigrationLock(
        root,
        allowed_root=root,
        installation_id=config["installation_id"],
        database_context_id=config["database_context_id"],
        migration_id=config["migration_id"],
    )
    crash_point = config.get("crash_point")

    def fault(point: str) -> None:
        if point == crash_point:
            os._exit(97)

    orchestrator = SyntheticMigrationOrchestratorV2(
        paths=paths,
        allowed_private_root=root,
        installation_id=config["installation_id"],
        database_context_id=config["database_context_id"],
        migration_id=config["migration_id"],
        migration_generation=1,
        dmk_loader=lambda: dmk,
        database_key_loader=load_database_key,
        migration_lock=migration_lock,
        journal_repository=AuthenticatedMigrationJournalV2Repository(paths.journal),
        anchor_repository=ExternalReplayAnchorV2Repository(
            Path(config["anchor_path"])
        ),
        sqlcipher_provider=SQLCipherConnectionProvider(),
        sqlcipher_version_probe=lambda: "4.12.0 community",
        app_instance_available=lambda: True,
        source_closed_probe=lambda _path: True,
        lock_chain_head_loader=lambda: hashlib.sha256(
            f"lock:{config['migration_id']}".encode("ascii")
        ).hexdigest(),
        safety_reserve_bytes=1,
        fault_injector=fault,
    )
    report = orchestrator.recover()
    Path(config["result_path"]).write_text(
        json.dumps(
            {
                "final_phase": report.final_phase,
                "source_sha256_before": report.source_sha256_before,
                "source_sha256_after": report.source_sha256_after,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        "ascii",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
