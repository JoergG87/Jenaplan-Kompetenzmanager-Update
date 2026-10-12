from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_sqlcipher_4_17_macos_arm64 import (
    BuildError,
    SQLCIPHER_4_17_LOCAL_BINDING_VERSION,
    SQLCIPHER_4_17_SOURCE_DATE_EPOCH,
    _replace_exact,
    load_manifest,
    sanitized_environment,
)
from scripts.audit_sqlcipher_4_17_macos_arm64 import compare_builds
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
    SQLCIPHER_PRODUCT_TARGET_VERSION,
    SQLCIPHER_SPIKE_BINDING_VERSION,
    SQLCIPHER_SPIKE_ENGINE_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_manifest_binds_exact_target_sources_and_wheel() -> None:
    manifest = load_manifest()

    assert manifest["target"] == {
        "machine": "arm64",
        "platform": "Darwin",
        "python": "3.14.6",
        "macos_deployment_target": "11.0",
        "macos_sdk": "27.0",
        "clang_identity": "Apple clang version 21.0.0 (clang-2100.3.34.2)",
        "crypto_provider": "commoncrypto",
    }
    assert manifest["sources"]["sqlcipher"]["version"] == "4.17.0"
    assert manifest["sources"]["binding"]["version"] == "0.6.2"
    assert (
        manifest["sources"]["binding"]["local_version"]
        == SQLCIPHER_4_17_LOCAL_BINDING_VERSION
    )
    assert manifest["build"]["source_date_epoch"] == SQLCIPHER_4_17_SOURCE_DATE_EPOCH
    assert manifest["generated"]["expected_wheel_sha256"] == (
        "9ce432941a45f28af3877192149ab2583ae22f466e3b22c2a7323c5a84c577f9"
    )
    assert manifest["build"]["allowed_dynamic_dependencies"] == [
        "/usr/lib/libSystem.B.dylib",
        "/System/Library/Frameworks/Security.framework/Versions/A/Security",
        "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation",
    ]


def test_build_requirements_are_exact_and_hash_bound() -> None:
    requirements = (ROOT / "requirements-sqlcipher-4.17-build.txt").read_text()

    for requirement in (
        "pip==26.1.2",
        "setuptools==83.0.0",
        "wheel==0.46.3",
        "packaging==26.2",
    ):
        assert requirement in requirements
    assert requirements.count("--hash=sha256:") == 4
    assert "conan" not in requirements.lower()


def test_license_copies_match_bound_upstream_texts() -> None:
    manifest = load_manifest()

    assert _sha256(ROOT / "packaging/licenses/sqlcipher-4.17.0/LICENSE.md") == (
        manifest["generated"]["sqlcipher_license_sha256"]
    )
    assert _sha256(ROOT / "packaging/licenses/sqlcipher3-0.6.2/LICENSE") == (
        manifest["sources"]["binding"]["license_sha256"]
    )
    assert _sha256(ROOT / "packaging/licenses/sqlcipher-4.17.0/SQLITE_LICENSE.md") == (
        manifest["generated"]["sqlite_license_sha256"]
    )
    assert _sha256(
        ROOT / "packaging/THIRD_PARTY_NOTICES_SQLCIPHER_4_17_MACOS.md"
    ) == manifest["generated"]["third_party_notice_sha256"]


def test_existing_4_12_test_engine_remains_separate() -> None:
    assert SQLCIPHER_SPIKE_BINDING_VERSION == "0.6.2"
    assert SQLCIPHER_SPIKE_ENGINE_VERSION == "4.12.0 community"
    assert SQLCIPHER_PRODUCT_TARGET_VERSION == "4.17.0"
    assert SQLCIPHER_4_17_BINDING_VERSION == SQLCIPHER_4_17_LOCAL_BINDING_VERSION
    assert SQLCIPHER_4_17_ENGINE_VERSION == "4.17.0 community"
    assert SQLCIPHER_4_17_SQLITE_VERSION == "3.53.3"
    assert (ROOT / "requirements-sqlcipher-spike.txt").read_text().endswith(
        "sqlcipher3==0.6.2\n"
    )
    macos_requirements = (ROOT / "requirements-macos-build.txt").read_text()
    assert "sqlcipher3==0.6.2" not in macos_requirements
    macos_build = (ROOT / "scripts/build_macos_pilot.sh").read_text()
    assert "JENAPLAN_SQLCIPHER_417_WHEEL" in macos_build
    assert "expected_wheel_sha256" in macos_build


def test_binding_patch_requires_one_exact_context() -> None:
    assert _replace_exact("a token b", "token", "value", label="test") == "a value b"
    with pytest.raises(BuildError, match="binding_patch_context_mismatch:test"):
        _replace_exact("no match", "token", "value", label="test")
    with pytest.raises(BuildError, match="binding_patch_context_mismatch:test"):
        _replace_exact("token token", "token", "value", label="test")


def test_reproducibility_gate_rejects_same_build_twice() -> None:
    manifest = load_manifest()
    report = {
        "root": "/private/tmp/not-a-real-independent-build",
        "sources": {
            name: {"sha256": source["sha256"]}
            for name, source in manifest["sources"].items()
        },
        "generated": {
            key: manifest["generated"][key]
            for key in ("sqlite3_c_sha256", "sqlite3_h_sha256")
        },
        "binding_patch": {
            "setup_py": manifest["generated"]["patched_setup_sha256"],
            "pyproject_toml": manifest["generated"]["patched_pyproject_sha256"],
            "sqlcipher_license": manifest["generated"]["sqlcipher_license_sha256"],
            "sqlite_license": manifest["generated"]["sqlite_license_sha256"],
            "third_party_notice": manifest["generated"]["third_party_notice_sha256"],
        },
        "wheel": {
            "path": "/private/tmp/not-a-real-independent-build/wheel/basis.whl",
        },
    }

    with pytest.raises(
        BuildError, match="reproducibility_build_roots_not_independent"
    ):
        compare_builds(report, report, manifest)


def test_subprocess_environment_rejects_python_and_pip_injection() -> None:
    environment = sanitized_environment(
        {
            "PATH": "/usr/bin:/bin",
            "PYTHONHOME": "/attacker/python",
            "PYTHONPATH": "/attacker/modules",
            "PYTHONUSERBASE": "/attacker/userbase",
            "PIP_INDEX_URL": "https://attacker.invalid/simple",
            "PIP_REQUIRE_VIRTUALENV": "0",
        }
    )

    assert environment["PATH"] == "/usr/bin:/bin"
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["PIP_CONFIG_FILE"] == "/dev/null"
    assert environment["PIP_NO_INPUT"] == "1"
    assert "PYTHONHOME" not in environment
    assert "PYTHONPATH" not in environment
    assert "PYTHONUSERBASE" not in environment
    assert "PIP_INDEX_URL" not in environment
    assert "PIP_REQUIRE_VIRTUALENV" not in environment


def test_source_manifest_is_valid_json() -> None:
    path = ROOT / "packaging/sqlcipher_4_17_macos_arm64_sources.json"
    assert json.loads(path.read_text()) == load_manifest()
