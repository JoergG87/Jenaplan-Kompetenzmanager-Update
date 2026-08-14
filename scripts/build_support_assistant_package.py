"""Assemble and verify the separate graphical Support-Assistent ZIP."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Jenaplan Support-Assistent.app"
BUNDLE_ID = "de.jenaplan.support-assistent"
FORBIDDEN_SUFFIXES = {
    ".sqlite",
    ".sqlite3",
    ".db",
    ".jkmbackup",
    ".jkmebackup",
    ".jkmresetrequest",
    ".jkmresettoken",
    ".pem",
    ".key",
}
PRIVATE_PEM_PATTERN = re.compile(
    rb"-----BEGIN (?:ENCRYPTED )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{40,}"
)
TOKEN_PATTERN = re.compile(rb"JKM-SR1\.[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{80,}")
RECOVERY_PATTERN = re.compile(rb"JKM1-[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}-[A-Z0-9]")


def build_package(
    *,
    app_bundle: Path,
    output_root: Path,
    version: str,
    build_version: str,
    minimum_macos_version: str,
    build_commit: str,
    source_tree_state: str,
) -> Path:
    app_bundle = Path(app_bundle).resolve(strict=True)
    if not app_bundle.is_dir() or app_bundle.name != APP_NAME:
        raise RuntimeError("support_assistant_app_bundle_invalid")
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    package_name = f"Jenaplan-Support-Assistent-{version}-macOS-arm64"
    output = output_root / f"{package_name}.zip"
    with tempfile.TemporaryDirectory(prefix="jenaplan-support-assistant-package-") as temporary:
        package = Path(temporary) / package_name
        package.mkdir(mode=0o755)
        shutil.copytree(app_bundle, package / APP_NAME, symlinks=True)
        operations = (
            (ROOT / "docs" / "SUPPORT_ASSISTANT_OPERATIONS.md")
            .read_text(encoding="utf-8")
            .replace("{{PILOT_VERSION}}", version)
            .replace("{{PILOT_BUILD}}", build_version)
        )
        (package / "SUPPORT_ANLEITUNG.md").write_text(
            operations,
            encoding="utf-8",
        )
        version_text = (
            "Jenaplan Support-Assistent\n"
            f"Produktversion: {version}\n"
            f"Build-Commit: {build_commit}\n"
            f"Quellbaum: {source_tree_state}\n"
            "Plattform: macOS arm64\n"
            "Bundle-ID: de.jenaplan.support-assistent\n"
            "Netzwerk: nicht erforderlich\n"
            "Privater Schlüssel: nicht enthalten\n"
            "Developer ID / Notarisierung: nicht behauptet\n"
        )
        (package / "VERSION.txt").write_text(version_text, encoding="utf-8")
        os.chmod(package / "SUPPORT_ANLEITUNG.md", 0o644)
        os.chmod(package / "VERSION.txt", 0o644)
        _write_checksums(package)
        scan_package_tree(
            package,
            expected_version=version,
            expected_build_version=build_version,
            expected_minimum_macos=minimum_macos_version,
        )
        _write_macos_zip(package, output)
    verify_package(
        output,
        expected_version=version,
        expected_build_version=build_version,
        expected_minimum_macos=minimum_macos_version,
    )
    return output


def _write_checksums(package: Path) -> None:
    lines: list[str] = []
    for path in sorted(
        item for item in package.rglob("*") if item.is_file() or item.is_symlink()
    ):
        relative = path.relative_to(package).as_posix()
        lines.append(f"{_entry_sha256(path)}  {relative}")
    checksum_file = package / "SHA256SUMS.txt"
    checksum_file.write_text("\n".join(lines) + "\n", encoding="ascii")
    os.chmod(checksum_file, 0o644)


def scan_package_tree(
    package: Path,
    *,
    expected_version: str,
    expected_build_version: str,
    expected_minimum_macos: str,
) -> None:
    if not (package / APP_NAME).is_dir():
        raise RuntimeError("support_assistant_app_missing")
    if {path.name for path in package.iterdir()} != {
        APP_NAME,
        "SHA256SUMS.txt",
        "SUPPORT_ANLEITUNG.md",
        "VERSION.txt",
    }:
        raise RuntimeError("support_assistant_package_inventory_invalid")
    info_path = package / APP_NAME / "Contents" / "Info.plist"
    try:
        info = plistlib.loads(info_path.read_bytes())
    except (OSError, plistlib.InvalidFileException) as error:
        raise RuntimeError("support_assistant_info_plist_invalid") from error
    if (
        info.get("CFBundleIdentifier") != BUNDLE_ID
        or info.get("CFBundleDisplayName") != "Jenaplan Support-Assistent"
    ):
        raise RuntimeError("support_assistant_bundle_identity_invalid")
    if (
        info.get("CFBundleShortVersionString") != expected_version
        or str(info.get("CFBundleVersion", "")) != expected_build_version
        or info.get("LSMinimumSystemVersion") != expected_minimum_macos
    ):
        raise RuntimeError("support_assistant_release_metadata_invalid")
    executable = package / APP_NAME / "Contents" / "MacOS" / "Jenaplan Support-Assistent"
    if not executable.is_file() or executable.stat().st_mode & 0o111 == 0:
        raise RuntimeError("support_assistant_executable_invalid")
    app_root = (package / APP_NAME).resolve()
    for path in package.rglob("*"):
        if path.is_symlink():
            target = Path(os.readlink(path))
            try:
                resolved = path.resolve(strict=True)
            except OSError as error:
                raise RuntimeError("support_assistant_package_symlink_invalid") from error
            if target.is_absolute() or not resolved.is_relative_to(app_root):
                raise RuntimeError("support_assistant_package_symlink_invalid")
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise RuntimeError("support_assistant_runtime_artifact_forbidden")
        payload = path.read_bytes()
        if PRIVATE_PEM_PATTERN.search(payload):
            raise RuntimeError("support_assistant_private_key_forbidden")
        if TOKEN_PATTERN.search(payload) or RECOVERY_PATTERN.search(payload):
            raise RuntimeError("support_assistant_generated_secret_forbidden")


def _write_macos_zip(package: Path, output: Path) -> None:
    temporary = output.with_suffix(".zip.tmp")
    temporary.unlink(missing_ok=True)
    try:
        subprocess.run(
            ["/usr/bin/ditto", "-c", "-k", "--keepParent", str(package), str(temporary)],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("support_assistant_zip_creation_failed") from error
    os.replace(temporary, output)


def verify_package(
    output: Path,
    *,
    expected_version: str,
    expected_build_version: str,
    expected_minimum_macos: str,
) -> None:
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            Path(name).is_absolute() or ".." in Path(name).parts for name in names
        ):
            raise RuntimeError("support_assistant_zip_structure_invalid")
        with tempfile.TemporaryDirectory(prefix="jenaplan-support-assistant-verify-") as temporary:
            try:
                subprocess.run(
                    ["/usr/bin/ditto", "-x", "-k", str(output), temporary],
                    check=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                raise RuntimeError("support_assistant_zip_extraction_failed") from error
            root_items = tuple(Path(temporary).iterdir())
            if len(root_items) != 1 or not root_items[0].is_dir():
                raise RuntimeError("support_assistant_zip_root_invalid")
            package = root_items[0]
            scan_package_tree(
                package,
                expected_version=expected_version,
                expected_build_version=expected_build_version,
                expected_minimum_macos=expected_minimum_macos,
            )
            checksums = (package / "SHA256SUMS.txt").read_text(encoding="ascii")
            for line in checksums.splitlines():
                digest, relative = line.split("  ", 1)
                if _entry_sha256(package / relative) != digest:
                    raise RuntimeError("support_assistant_checksum_invalid")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry_sha256(path: Path) -> str:
    if path.is_symlink():
        return hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
    return _sha256(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-bundle", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-version", required=True)
    parser.add_argument("--minimum-macos-version", required=True)
    parser.add_argument("--build-commit", required=True)
    parser.add_argument("--source-tree-state", choices=("clean", "dirty"), required=True)
    args = parser.parse_args()
    output = build_package(
        app_bundle=args.app_bundle,
        output_root=args.output_root,
        version=args.version,
        build_version=args.build_version,
        minimum_macos_version=args.minimum_macos_version,
        build_commit=args.build_commit,
        source_tree_state=args.source_tree_state,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
