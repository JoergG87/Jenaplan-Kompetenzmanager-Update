#!/usr/bin/env python3
"""Audit two SQLCipher 4.17 macOS-arm64 builds and run the clean-venv smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_sqlcipher_4_17_macos_arm64 import (  # noqa: E402
    BuildError,
    SQLCIPHER_4_17_SOURCE_DATE_EPOCH,
    REPORT_NAME,
    _is_within,
    create_build_root,
    load_manifest,
    sanitized_environment,
    sha256,
)


AUDIT_REPORT_NAME = "sqlcipher-4.17-macos-arm64-audit-report.json"


def _run(command: list[str], *, capture: bool = True) -> str:
    print("$", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        check=False,
        env=sanitized_environment(),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout, file=sys.stderr)
        raise BuildError(f"audit_command_failed:{command[0]}:{result.returncode}")
    return (result.stdout or "").strip()


def load_build_report(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise BuildError("build_report_invalid")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != 1:
        raise BuildError("build_report_format_unsupported")
    root = Path(report["root"])
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise BuildError("build_report_root_invalid")
    root = root.resolve()
    allowed_roots = {
        Path(tempfile.gettempdir()).resolve(),
        Path("/private/tmp").resolve(),
        Path("/tmp").resolve(),
    }
    if not any(_is_within(root, candidate) for candidate in allowed_roots):
        raise BuildError("build_report_root_not_system_temp")
    if path.resolve() != root / REPORT_NAME:
        raise BuildError("build_report_not_bound_to_root")
    wheel_root = root / "wheel"
    if wheel_root.is_symlink() or not wheel_root.is_dir():
        raise BuildError("build_report_wheel_root_invalid")
    wheel = Path(report["wheel"]["path"])
    if not wheel.is_absolute():
        raise BuildError("build_report_wheel_path_invalid")
    if wheel.is_symlink() or not wheel.is_file():
        raise BuildError("build_report_wheel_missing")
    if wheel.resolve().parent != wheel_root.resolve():
        raise BuildError("build_report_wheel_not_bound_to_root")
    if wheel.name != report["wheel"]["name"]:
        raise BuildError("build_report_wheel_name_mismatch")
    if sha256(wheel) != report["wheel"]["sha256"]:
        raise BuildError("build_report_wheel_hash_mismatch")
    return report


def compare_builds(
    first: dict[str, object], second: dict[str, object], manifest: dict[str, object]
) -> tuple[Path, str]:
    if Path(first["root"]).resolve() == Path(second["root"]).resolve():
        raise BuildError("reproducibility_build_roots_not_independent")
    if Path(first["wheel"]["path"]).resolve() == Path(second["wheel"]["path"]).resolve():
        raise BuildError("reproducibility_wheel_paths_not_independent")
    first_status = Path(first["wheel"]["path"]).stat()
    second_status = Path(second["wheel"]["path"]).stat()
    if (first_status.st_dev, first_status.st_ino) == (
        second_status.st_dev,
        second_status.st_ino,
    ):
        raise BuildError("reproducibility_wheels_share_file_identity")
    for section in ("sources", "generated", "binding_patch"):
        if first[section] != second[section]:
            raise BuildError(f"reproducibility_section_mismatch:{section}")
    source_manifest = manifest["sources"]
    for name in ("sqlcipher", "binding"):
        if first["sources"][name]["sha256"] != source_manifest[name]["sha256"]:
            raise BuildError(f"source_not_manifest_bound:{name}")
    generated_manifest = manifest["generated"]
    for key in ("sqlite3_c_sha256", "sqlite3_h_sha256"):
        if first["generated"][key] != generated_manifest[key]:
            raise BuildError(f"amalgamation_not_manifest_bound:{key}")
    for report_key, manifest_key in (
        ("setup_py", "patched_setup_sha256"),
        ("pyproject_toml", "patched_pyproject_sha256"),
        ("sqlcipher_license", "sqlcipher_license_sha256"),
        ("sqlite_license", "sqlite_license_sha256"),
        ("third_party_notice", "third_party_notice_sha256"),
    ):
        if first["binding_patch"][report_key] != generated_manifest[manifest_key]:
            raise BuildError(f"binding_patch_not_manifest_bound:{report_key}")
    first_wheel = Path(first["wheel"]["path"])
    second_wheel = Path(second["wheel"]["path"])
    first_hash = sha256(first_wheel)
    second_hash = sha256(second_wheel)
    if first_wheel.name != second_wheel.name or first_hash != second_hash:
        raise BuildError("wheel_not_byte_reproducible")
    expected = manifest["generated"].get("expected_wheel_sha256")
    if expected and first_hash != expected:
        raise BuildError("wheel_hash_not_manifest_bound")
    return first_wheel, first_hash


def inspect_wheel(
    wheel: Path, audit_root: Path, manifest: dict[str, object], build_roots: list[str]
) -> dict[str, object]:
    unpacked = audit_root / "wheel-unpacked"
    unpacked.mkdir()
    with zipfile.ZipFile(wheel) as bundle:
        names = bundle.namelist()
        timestamps = {info.date_time for info in bundle.infolist()}
        if timestamps != {(2026, 7, 8, 0, 0, 0)}:
            raise BuildError(f"wheel_timestamp_not_reproducible:{sorted(timestamps)}")
        for info in bundle.infolist():
            path = Path(info.filename)
            mode = info.external_attr >> 16
            if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
                raise BuildError(f"wheel_member_rejected:{info.filename}")
        extension_names = [name for name in names if name.endswith("/_sqlite3.cpython-314-darwin.so")]
        if len(extension_names) != 1:
            raise BuildError("wheel_extension_count_invalid")
        wheel_metadata_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
        package_metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(wheel_metadata_names) != 1 or len(package_metadata_names) != 1:
            raise BuildError("wheel_metadata_count_invalid")
        wheel_metadata = bundle.read(wheel_metadata_names[0]).decode("utf-8")
        package_metadata = bundle.read(package_metadata_names[0]).decode("utf-8")
        if "Tag: cp314-cp314-macosx_11_0_arm64" not in wheel_metadata:
            raise BuildError("wheel_platform_tag_invalid")
        if "Version: 0.6.2+jkm.sqlcipher4170.1" not in package_metadata:
            raise BuildError("wheel_binding_version_invalid")
        if "License-Expression: LicenseRef-zlib" not in package_metadata:
            raise BuildError("wheel_license_expression_invalid")
        license_basenames = {
            Path(name).name for name in names if ".dist-info/licenses/" in name
        }
        expected_licenses = {
            "LICENSE",
            "SQLCIPHER_LICENSE.md",
            "SQLITE_LICENSE.md",
            "THIRD_PARTY_NOTICE.md",
        }
        if license_basenames != expected_licenses:
            raise BuildError(f"wheel_license_set_invalid:{sorted(license_basenames)}")
        bundle.extractall(unpacked)

    extension = unpacked / extension_names[0]
    file_output = _run(["file", str(extension)])
    lipo_output = _run(["lipo", "-archs", str(extension)])
    if "Mach-O 64-bit bundle arm64" not in file_output or lipo_output != "arm64":
        raise BuildError("wheel_extension_not_arm64_only")

    otool_output = _run(["otool", "-L", str(extension)])
    dependencies = {
        line.strip().split(" (", 1)[0]
        for line in otool_output.splitlines()[1:]
        if line.strip()
    }
    allowed = set(manifest["build"]["allowed_dynamic_dependencies"])
    if dependencies != allowed:
        raise BuildError(f"wheel_dynamic_dependency_mismatch:{sorted(dependencies)}")
    load_commands = _run(["otool", "-l", str(extension)])
    if "LC_RPATH" in load_commands:
        raise BuildError("wheel_unexpected_rpath")
    if not all(
        marker in load_commands
        for marker in ("cmd LC_BUILD_VERSION", "platform 1", "minos 11.0", "sdk 26.5")
    ):
        raise BuildError("wheel_build_version_mismatch")

    strings_output = _run(["strings", str(extension)])
    forbidden = ["/Users/", "/private/tmp/", "/private/var/folders/", "/var/folders/"]
    forbidden.extend(build_roots)
    leaked = sorted({value for value in forbidden if value and value in strings_output})
    if leaked:
        raise BuildError(f"wheel_build_path_leak:{leaked}")
    return {
        "extension": extension_names[0],
        "architecture": lipo_output,
        "file": file_output,
        "dynamic_dependencies": sorted(dependencies),
        "deployment_target": "macOS 11.0",
        "sdk": "26.5",
        "source_date_epoch": SQLCIPHER_4_17_SOURCE_DATE_EPOCH,
        "rpath": "absent",
        "developer_paths": "absent",
        "licenses": sorted(license_basenames),
    }


def run_clean_venv_smoke(wheel: Path, audit_root: Path) -> dict[str, object]:
    venv_root = audit_root / "test-venv"
    _run([sys.executable, "-m", "venv", "--copies", str(venv_root)], capture=False)
    python = venv_root / "bin/python"
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--no-deps",
            str(wheel),
        ],
        capture=False,
    )
    pip_check = _run([str(python), "-m", "pip", "check"])
    smoke = json.loads(
        _run([str(python), str(ROOT / "scripts/smoke_test_sqlcipher_4_17.py")])
    )
    return {"pip_check": pip_check, "smoke": smoke, "test_venv": str(venv_root)}


def audit(
    *, first_report_path: Path, second_report_path: Path, requested_root: Path | None
) -> Path:
    manifest = load_manifest()
    if first_report_path.resolve() == second_report_path.resolve():
        raise BuildError("reproducibility_report_paths_not_independent")
    first = load_build_report(first_report_path)
    second = load_build_report(second_report_path)
    wheel, wheel_hash = compare_builds(first, second, manifest)
    audit_root = create_build_root(requested_root)
    wheel_evidence = inspect_wheel(
        wheel,
        audit_root,
        manifest,
        [str(first["root"]), str(second["root"])],
    )
    runtime_evidence = run_clean_venv_smoke(wheel, audit_root)
    report = {
        "format": 1,
        "status": "GO",
        "wheel": {"name": wheel.name, "sha256": wheel_hash},
        "reproducibility": {
            "build_a": str(first_report_path.resolve()),
            "build_b": str(second_report_path.resolve()),
            "source_hashes_identical": True,
            "amalgamation_hashes_identical": True,
            "binding_patch_hashes_identical": True,
            "wheel_byte_identical": True,
        },
        "wheel_audit": wheel_evidence,
        "runtime": runtime_evidence,
    }
    report_path = audit_root / AUDIT_REPORT_NAME
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"audit_root={audit_root}")
    print(f"audit_report={report_path}")
    print(f"wheel_sha256={wheel_hash}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-report-a", type=Path, required=True)
    parser.add_argument("--build-report-b", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    audit(
        first_report_path=args.build_report_a,
        second_report_path=args.build_report_b,
        requested_root=args.root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
