"""Exercise the gated Security Sprint 11 path through a built macOS app."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid


APP_NAME = "Jenaplan-Kompetenzmanager"
CRASH_POINTS = (
    "initial_after_journal_publish",
    "safety_copy_after_publish",
    "documents_after_prepared_generation",
    "phase_encrypted_backup_verified_committed",
)


def smoke_test(app_path: Path) -> dict[str, object]:
    app_path = Path(app_path).resolve()
    executable = app_path / "Contents" / "MacOS" / APP_NAME
    if not executable.is_file():
        raise RuntimeError("Gebautes App-Bundle ist unvollständig.")
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(
        prefix="jkm-security-packaged-"
    ) as temporary:
        parent = Path(temporary).resolve(strict=True)
        roundtrip = _new_root(parent)
        results.extend(
            (
                _run(executable, roundtrip, "initialize"),
                _run(executable, roundtrip, "run"),
                _run(executable, roundtrip, "verify"),
                _run(executable, roundtrip, "wrong-key"),
            )
        )
        before = _snapshot(roundtrip)
        results.append(
            _run(executable, roundtrip, "disabled", gate=False)
        )
        if _snapshot(roundtrip) != before:
            raise RuntimeError(
                "Gate-Off hat den vorhandenen Testbestand verändert."
            )

        for tamper_mode in ("tamper-backup", "tamper-document"):
            root = _new_root(parent)
            results.append(_run(executable, root, "initialize"))
            results.append(_run(executable, root, "run"))
            results.append(_run(executable, root, tamper_mode))

        for crash_point in CRASH_POINTS:
            root = _new_root(parent)
            results.append(_run(executable, root, "initialize"))
            _run(
                executable,
                root,
                f"crash:{crash_point}",
                expected_returncode=91,
            )
            results.append(_run(executable, root, "recover"))
            results.append(_run(executable, root, "verify"))

    versions = next(
        result["versions"]
        for result in results
        if isinstance(result.get("versions"), dict)
    )
    expected_versions = {
        "cffi": "2.0.0",
        "cryptography": "49.0.0",
        "pynacl": "1.6.2",
        "pyside6": "6.11.1",
        "shiboken6": "6.11.1",
        "sqlcipher3": "0.6.2",
    }
    for name, expected in expected_versions.items():
        if versions.get(name) != expected:
            raise RuntimeError(
                f"Gebündelte Laufzeitversion stimmt nicht: {name}"
            )
    if versions.get("sqlcipher") != "4.12.0 community":
        raise RuntimeError("Gebündelte SQLCipher-Engine stimmt nicht.")
    return {
        "crash_points": list(CRASH_POINTS),
        "gate_disabled_stock_unchanged": True,
        "scenario_steps": len(results),
        "status": "ok",
        "versions": versions,
    }


def _new_root(parent: Path) -> Path:
    return parent / f"jkm-security-integration-{uuid.uuid4()}"


def _environment(root: Path, *, gate: bool) -> dict[str, str]:
    environment = os.environ.copy()
    environment["JENAPLAN_PACKAGED_SMOKE_MARKER"] = "isolated-v1"
    environment["JKM_SECURITY_INTEGRATION_ROOT"] = str(root)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    if gate:
        environment["JKM_SECURITY_INTEGRATION_TEST"] = "1"
    else:
        environment.pop("JKM_SECURITY_INTEGRATION_TEST", None)
    return environment


def _run(
    executable: Path,
    root: Path,
    mode: str,
    *,
    gate: bool = True,
    expected_returncode: int = 0,
) -> dict[str, object]:
    result = subprocess.run(
        [
            str(executable),
            "--packaged-security-integration-test",
            mode,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        env=_environment(root, gate=gate),
    )
    if result.returncode != expected_returncode:
        raise RuntimeError(
            "Gebündelter Security-Smoke fehlgeschlagen: "
            f"mode={mode}, code={result.returncode}, "
            f"stdout={result.stdout[-1000:]}, stderr={result.stderr[-1000:]}"
        )
    if expected_returncode != 0:
        return {"mode": mode, "status": "crashed-as-expected"}
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(
            f"Gebündelter Security-Smoke lieferte kein Ergebnis: {mode}"
        )
    payload = json.loads(lines[-1])
    if payload.get("status") != "ok":
        raise RuntimeError(
            f"Gebündelter Security-Smoke blockierte unerwartet: {payload}"
        )
    return payload


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


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
