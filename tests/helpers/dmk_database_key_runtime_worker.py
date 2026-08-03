from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

from src.security.data_keys import DataMasterKeyStoreStatus
from src.security.database_key_runtime import (
    DatabaseKeyRuntimeDecisionState,
    DatabaseKeyRuntimeGate,
    run_gated_database_key_runtime,
)
from src.security.domain import AccountStatus
from src.security.infrastructure.data_keyset_repository import (
    SQLiteDataKeysetRepository,
)
from src.security.infrastructure.data_master_key_store import (
    build_platform_data_master_key_store,
)
from src.security.infrastructure.system import PlatformFilePermissionManager


def main() -> int:
    mode, root_value, installation_id = sys.argv[1:4]
    root = Path(root_value)
    store = build_platform_data_master_key_store()
    if not store.supported:
        print(json.dumps({"state": "BLOCKED", "error": "keychain_unavailable"}))
        return 2
    account_loader = lambda: SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=installation_id,
    )
    if mode in {"first", "restart"}:
        decision = run_gated_database_key_runtime(
            account_loader=account_loader,
            environ={
                "JKM_DMK_DATABASE_KEY_RUNTIME_TEST": "1",
                "JKM_DMK_DATABASE_KEY_RUNTIME_ROOT": str(root),
            },
            key_store=store,
        )
        if (
            decision.state is not DatabaseKeyRuntimeDecisionState.ACTIVE
            or decision.loaded is None
        ):
            print(
                json.dumps(
                    {
                        "state": decision.state.value,
                        "error": decision.error_code,
                        "retryable": decision.retryable,
                    },
                    sort_keys=True,
                )
            )
            return 3
        loaded = decision.loaded
        print(
            json.dumps(
                {
                    "state": decision.state.value,
                    "first_run": loaded.first_run,
                    "database_context_id": loaded.database_context_id,
                    "dmk_key_id": loaded.dmk_key_id,
                    "dmk_generation": loaded.dmk_generation,
                    "dmk_fingerprint_sha256": loaded.dmk_fingerprint_sha256,
                    "database_key_id": loaded.database_key_id,
                    "database_key_generation": loaded.database_key_generation,
                    "database_key_fingerprint_sha256": (
                        loaded.database_key_fingerprint_sha256
                    ),
                },
                sort_keys=True,
            )
        )
        return 0
    if mode == "cleanup":
        paths = DatabaseKeyRuntimeGate.require_paths(str(root))
        repository = SQLiteDataKeysetRepository(
            paths.keyset_metadata, PlatformFilePermissionManager()
        )
        repository.initialize()
        keysets = tuple(
            item
            for item in (
                repository.active_data_keyset(),
                *repository.pending_data_keysets(),
                *repository.data_keysets_for_cleanup(),
            )
            if item is not None
        )
        for keyset in keysets:
            store.delete(
                installation_id=installation_id,
                key_id=keyset.key_id,
            )
        remaining = [
            keyset.key_id
            for keyset in keysets
            if store.read(
                installation_id=installation_id,
                key_id=keyset.key_id,
            ).status
            is not DataMasterKeyStoreStatus.NOT_FOUND
        ]
        print(
            json.dumps(
                {"state": "CLEANED", "remaining": remaining},
                sort_keys=True,
            )
        )
        return 0 if not remaining else 4
    print(json.dumps({"state": "BLOCKED", "error": "mode_invalid"}))
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
