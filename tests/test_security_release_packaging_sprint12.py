from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import uuid

import pytest

from scripts.audit_macos_security_runtime import (
    EXPECTED_VERSIONS,
    audit_environment,
)
from src.security.packaged_integration_smoke import (
    run_packaged_security_integration_smoke,
)
from src.version import APP_BUILD_VERSION, APP_VERSION


def _environment(root: Path, *, gate: bool = True) -> dict[str, str]:
    result = {
        "JENAPLAN_PACKAGED_SMOKE_MARKER": "isolated-v1",
        "JKM_SECURITY_INTEGRATION_ROOT": str(root),
    }
    if gate:
        result["JKM_SECURITY_INTEGRATION_TEST"] = "1"
    return result


def _root(tmp_path: Path) -> Path:
    return tmp_path / f"jkm-security-integration-{uuid.uuid4()}"


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_030_release_versions_and_security_dependencies_are_pinned() -> None:
    assert APP_VERSION == "0.3.0"
    assert APP_BUILD_VERSION == "303"
    requirements = Path("requirements-macos-build.txt").read_text(
        encoding="utf-8"
    )
    assert "PyNaCl==1.6.2" in requirements
    assert "sqlcipher3==0.6.2" not in requirements
    spec = Path("packaging/macos_pilot.spec").read_text(encoding="utf-8")
    for required in (
        '"_cffi_backend"',
        '"nacl._sodium"',
        '"sqlcipher3._sqlite3"',
        '"src.security.packaged_keychain_smoke"',
        '"src.desktop_app.restore_worker"',
        '"src.security.cipher_product_runtime"',
        '"src.security.final_v4_backup_runtime"',
        '"src.security.final_v4_live_restore"',
        '"src.application.managed_documents"',
        '"scripts.seed_test_data"',
    ):
        assert required in spec
    for excluded in (
        '"src.security.packaged_integration_smoke"',
        '"src.security.integration_orchestrator"',
    ):
        assert excluded in spec
    build_script = Path("scripts/build_macos_pilot.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/smoke_test_packaged_restore_worker.py" in build_script
    assert "JENAPLAN_SQLCIPHER_417_WHEEL" in build_script
    assert "expected_wheel_sha256" in build_script
    assert "rm -f \"$SQLCIPHER_DIRECT_URL\"" in build_script
    assert "scripts/smoke_test_macos_security_integration.py" not in build_script
    restore_worker = Path("src/desktop_app/restore_worker.py").read_text(
        encoding="utf-8"
    )
    assert "WORKER_READY_TIMEOUT_SECONDS = 5.0" in restore_worker


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="macOS arm64 build runtime audit",
)
def test_current_environment_matches_security_build_runtime() -> None:
    result = audit_environment()
    assert result["versions"] == EXPECTED_VERSIONS
    assert result["sqlcipher"] == "4.17.0 community"
    assert result["sqlite"] == "3.53.3"
    assert result["sqlcipher_provider"] == "commoncrypto"


def test_packaged_gate_on_roundtrip_restart_wrong_key_and_gate_off_stock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    root = _root(tmp_path)
    environment = _environment(root)

    assert (
        run_packaged_security_integration_smoke(
            "initialize",
            environ=environment,
        )
        == 0
    )
    assert (
        run_packaged_security_integration_smoke(
            "run",
            environ=environment,
        )
        == 0
    )
    assert (
        run_packaged_security_integration_smoke(
            "verify",
            environ=environment,
        )
        == 0
    )
    assert (
        run_packaged_security_integration_smoke(
            "wrong-key",
            environ=environment,
        )
        == 0
    )

    before = _snapshot(root)
    assert (
        run_packaged_security_integration_smoke(
            "disabled",
            environ=_environment(root, gate=False),
        )
        == 0
    )
    assert _snapshot(root) == before


@pytest.mark.parametrize("mode", ("tamper-backup", "tamper-document"))
def test_packaged_gate_on_tamper_is_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    root = _root(tmp_path)
    environment = _environment(root)
    assert (
        run_packaged_security_integration_smoke(
            "initialize",
            environ=environment,
        )
        == 0
    )
    assert (
        run_packaged_security_integration_smoke(
            "run",
            environ=environment,
        )
        == 0
    )
    assert (
        run_packaged_security_integration_smoke(
            mode,
            environ=environment,
        )
        == 0
    )


def test_packaged_security_entry_rejects_non_frozen_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert (
        run_packaged_security_integration_smoke(
            "initialize",
            environ=_environment(_root(tmp_path)),
        )
        == 1
    )
