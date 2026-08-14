"""Exercise the real packaged Final-V4 restore-worker takeover."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.smoke_test_macos_app import _run
from src.core.runtime_root_protection import prepare_synthetic_test_root


APP_NAME = "Jenaplan-Kompetenzmanager"


def smoke_test(app_path: Path) -> dict[str, object]:
    app = Path(app_path).expanduser().resolve(strict=True)
    executable = app / "Contents" / "MacOS" / APP_NAME
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError("Der gebündelte Restore-Worker ist nicht ausführbar.")

    with tempfile.TemporaryDirectory(
        prefix="jenaplan-packaged-smoke-restore-worker-"
    ) as temporary:
        data_root = Path(temporary) / "Application Support" / APP_NAME
        data_root.parent.mkdir(parents=True)
        prepare_synthetic_test_root(data_root)
        initialized = _run(executable, data_root, "initialize")
        try:
            worker = _run(executable, data_root, "restore-worker")
            restarted = _run(executable, data_root, "restart")
        finally:
            cleanup = _run(executable, data_root, "cleanup")

        restore = worker.get("restore", {})
        expected_prefix = [str(executable), "--restore-worker"]
        if (
            restore.get("backup_suffix") != ".jkmebackup"
            or restore.get("ready_state") != "RESTORE_READY"
            or restore.get("worker_phase") != "worker_started"
            or restore.get("recovery") != "aborted_before_replacement"
            or restore.get("command_prefix") != expected_prefix
        ):
            raise RuntimeError(f"Final-V4-Restore-Worker-Vertrag verletzt: {restore}")
        stable_fields = (
            "database_context_id",
            "database_key_fingerprint_sha256",
            "dmk_fingerprint_sha256",
        )
        if any(initialized[name] != restarted[name] for name in stable_fields):
            raise RuntimeError("Restore-Worker-Smoke veränderte den Cipher-Kontext.")
        if cleanup.get("keychain_cleanup") != "ok":
            raise RuntimeError("Restore-Worker-Smoke räumte den Test-DMK nicht auf.")
        return {
            "backup_suffix": restore["backup_suffix"],
            "command_prefix": restore["command_prefix"],
            "context_stable": True,
            "dmk_stable": True,
            "keychain_cleanup": "ok",
            "ready_state": restore["ready_state"],
            "recovery": restore["recovery"],
            "worker_phase": restore["worker_phase"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-Test für den gebündelten Final-V4-Restore-Worker"
    )
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    print(json.dumps(smoke_test(args.app), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
