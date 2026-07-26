"""Real-Keychain lifecycle check through a built internal macOS app."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid


APP_NAME = "Jenaplan-Kompetenzmanager"


def smoke_test(app_path: Path) -> dict[str, object]:
    app_path = Path(app_path).resolve()
    executable = app_path / "Contents" / "MacOS" / APP_NAME
    if not executable.is_file():
        raise RuntimeError("App-Bundle für Keychain-Smoke fehlt.")
    with tempfile.TemporaryDirectory(
        prefix="jenaplan-keychain-smoke-"
    ) as temporary:
        parent = Path(temporary)
        lifecycle_root = parent / "lifecycle"
        initialized = _run(executable, lifecycle_root, "initialize")
        try:
            copied_app = parent / "copied" / app_path.name
            copied_app.parent.mkdir()
            subprocess.run(
                ["ditto", str(app_path), str(copied_app)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            copied_executable = (
                copied_app / "Contents" / "MacOS" / APP_NAME
            )
            reloaded = _run(
                copied_executable,
                lifecycle_root,
                "reload-password-change",
            )
            if (
                initialized.get("fingerprint_sha256")
                != reloaded.get("fingerprint_sha256")
            ):
                raise RuntimeError(
                    "Keychain-Fingerprint änderte sich nach Bundle-Wechsel."
                )
        finally:
            cleanup = _run(executable, lifecycle_root, "cleanup")

        missing = _run(
            executable,
            parent / f"missing-{uuid.uuid4()}",
            "missing",
        )
        corrupt = _run(
            executable,
            parent / f"corrupt-{uuid.uuid4()}",
            "corrupt",
        )
    return {
        "bundle_copy_reload": reloaded["status"],
        "cleanup": cleanup["status"],
        "corrupt_entry": corrupt["status"],
        "missing_entry": missing["status"],
        "password_change_preserved_dmk": True,
        "status": "ok",
    }


def _run(
    executable: Path,
    data_root: Path,
    mode: str,
) -> dict[str, object]:
    environment = os.environ.copy()
    environment["JENAPLAN_PACKAGED_SMOKE_MARKER"] = "isolated-v1"
    environment["JENAPLAN_APP_DATA_DIR"] = str(data_root)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [str(executable), "--packaged-keychain-smoke", mode],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Gebündelter Keychain-Smoke fehlgeschlagen: "
            f"mode={mode}, code={result.returncode}, "
            f"stdout={result.stdout[-1000:]}, stderr={result.stderr[-1000:]}"
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    if payload.get("status") != "ok":
        raise RuntimeError(
            f"Gebündelter Keychain-Smoke blockierte: {payload}"
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            smoke_test(args.app),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
