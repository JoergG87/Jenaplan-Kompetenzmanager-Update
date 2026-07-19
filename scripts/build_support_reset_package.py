"""Assemble and verify the separate macOS support-reset handoff ZIP."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PEM_PATTERN = re.compile(
    rb"-----BEGIN (?:ENCRYPTED )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{40,}"
)
TOKEN_PATTERN = re.compile(rb"JKM-SR1\.[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{80,}")
RECOVERY_PATTERN = re.compile(rb"JKM1-[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}-[A-Z0-9]")
FORBIDDEN_SUFFIXES = {
    ".sqlite",
    ".db",
    ".jkmbackup",
    ".jkmresetrequest",
    ".jkmresettoken",
    ".pem",
    ".key",
}


def build_package(
    *,
    reset_executable: Path,
    keypair_executable: Path,
    output_root: Path,
    version: str,
    build_commit: str,
    source_tree_state: str,
) -> Path:
    reset_executable = Path(reset_executable).resolve(strict=True)
    keypair_executable = Path(keypair_executable).resolve(strict=True)
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    name = f"Jenaplan-Kompetenzmanager-{version}-Support-Reset-macOS"
    output = output_root / f"{name}.zip"

    with tempfile.TemporaryDirectory(prefix="jenaplan-support-package-") as temporary:
        package = Path(temporary) / name
        bin_directory = package / "bin"
        bin_directory.mkdir(parents=True, mode=0o755)
        copies = (
            (
                ROOT / "support_tools" / "Jenaplan-Support-Reset.command",
                package / "Jenaplan-Support-Reset.command",
                0o755,
            ),
            (
                ROOT / "support_tools" / "Jenaplan-Support-Schluessel-einrichten.command",
                package / "Jenaplan-Support-Schluessel-einrichten.command",
                0o755,
            ),
            (reset_executable, bin_directory / "Jenaplan-Support-Reset", 0o755),
            (
                keypair_executable,
                bin_directory / "Jenaplan-Support-Schluessel-einrichten",
                0o755,
            ),
            (
                ROOT / "docs" / "SUPPORT_RESET_OPERATIONS.md",
                package / "SUPPORT_ANLEITUNG.md",
                0o644,
            ),
            (
                ROOT / "support_tools" / "PUBLIC_KEY_REGISTRY_EXAMPLE.json",
                package / "PUBLIC_KEY_REGISTRY_EXAMPLE.json",
                0o644,
            ),
        )
        for source, target, mode in copies:
            shutil.copyfile(source, target)
            os.chmod(target, mode)
        version_text = (
            "Jenaplan-Kompetenzmanager Support-Reset\n"
            f"Produktversion: {version}\n"
            f"Build-Commit: {build_commit}\n"
            f"Quellbaum: {source_tree_state}\n"
            "Plattform: macOS arm64\n"
            "Netzwerk: nicht erforderlich\n"
            "Produktiver Schlüssel: nicht enthalten\n"
        )
        (package / "VERSION.txt").write_text(version_text, encoding="utf-8")
        os.chmod(package / "VERSION.txt", 0o644)
        _write_checksums(package)
        scan_package_tree(package)
        _write_deterministic_zip(package, output)
    verify_package(output)
    return output


def _write_checksums(package: Path) -> None:
    lines = []
    for path in sorted(item for item in package.rglob("*") if item.is_file()):
        relative = path.relative_to(package).as_posix()
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    checksum_file = package / "SHA256SUMS.txt"
    checksum_file.write_text("\n".join(lines) + "\n", encoding="ascii")
    os.chmod(checksum_file, 0o644)


def scan_package_tree(package: Path) -> None:
    expected = {
        "Jenaplan-Support-Reset.command",
        "Jenaplan-Support-Schluessel-einrichten.command",
        "PUBLIC_KEY_REGISTRY_EXAMPLE.json",
        "SHA256SUMS.txt",
        "SUPPORT_ANLEITUNG.md",
        "VERSION.txt",
        "bin/Jenaplan-Support-Reset",
        "bin/Jenaplan-Support-Schluessel-einrichten",
    }
    actual = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise RuntimeError("support_package_inventory_invalid")
    for path in package.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("support_package_symlink_forbidden")
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise RuntimeError("support_package_secret_artifact_forbidden")
        payload = path.read_bytes()
        if b"/Users/" in payload or b"/private/tmp/" in payload:
            raise RuntimeError("support_package_local_path_forbidden")
        if PRIVATE_PEM_PATTERN.search(payload):
            raise RuntimeError("support_package_private_key_forbidden")
        if TOKEN_PATTERN.search(payload) or RECOVERY_PATTERN.search(payload):
            raise RuntimeError("support_package_generated_secret_forbidden")


def _write_deterministic_zip(package: Path, output: Path) -> None:
    temporary = output.with_suffix(".zip.tmp")
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package.rglob("*")):
            if not path.is_file():
                continue
            relative = Path(package.name) / path.relative_to(package)
            info = zipfile.ZipInfo(relative.as_posix(), (2026, 1, 1, 0, 0, 0))
            mode = stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    os.replace(temporary, output)


def verify_package(output: Path) -> None:
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            Path(name).is_absolute() or ".." in Path(name).parts for name in names
        ):
            raise RuntimeError("support_package_zip_structure_invalid")
        for info in archive.infolist():
            mode = (info.external_attr >> 16) & 0o777
            if info.filename.endswith(
                (
                    ".command",
                    "/bin/Jenaplan-Support-Reset",
                    "/bin/Jenaplan-Support-Schluessel-einrichten",
                )
            ) and mode & 0o111 == 0:
                raise RuntimeError("support_package_executable_mode_invalid")
        with tempfile.TemporaryDirectory(prefix="jenaplan-support-verify-") as temporary:
            archive.extractall(temporary)
            roots = tuple(Path(temporary).iterdir())
            if len(roots) != 1 or not roots[0].is_dir():
                raise RuntimeError("support_package_root_invalid")
            scan_package_tree(roots[0])
            checksums = (roots[0] / "SHA256SUMS.txt").read_text(encoding="ascii")
            for line in checksums.splitlines():
                digest, relative = line.split("  ", 1)
                if hashlib.sha256((roots[0] / relative).read_bytes()).hexdigest() != digest:
                    raise RuntimeError("support_package_checksum_invalid")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-executable", required=True, type=Path)
    parser.add_argument("--keypair-executable", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-commit", required=True)
    parser.add_argument("--source-tree-state", choices=("clean", "dirty"), required=True)
    args = parser.parse_args()
    output = build_package(
        reset_executable=args.reset_executable,
        keypair_executable=args.keypair_executable,
        output_root=args.output_root,
        version=args.version,
        build_commit=args.build_commit,
        source_tree_state=args.source_tree_state,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
