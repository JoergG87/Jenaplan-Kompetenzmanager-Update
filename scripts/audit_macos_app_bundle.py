"""Static release audit for the internal macOS Security RC bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import plistlib
import subprocess


APP_NAME = "Jenaplan-Kompetenzmanager"
FORBIDDEN_SUFFIXES = {
    ".db",
    ".jkmbackup",
    ".jkmebackup",
    ".jkmedoc",
    ".key",
    ".pem",
    ".p12",
    ".sqlite",
    ".xlsm",
    ".xlsx",
}
TEXT_SUFFIXES = {".json", ".md", ".plist", ".txt"}
REQUIRED_LICENSE_DIRECTORIES = {
    "PyNaCl",
    "cffi",
    "cryptography",
    "libsodium",
    "sqlcipher3",
}
ALLOWED_UPSTREAM_BUILD_PATH_RESOURCE = (
    "Contents/Resources/"
    "cryptography-49.0.0.dist-info/sboms/"
    "cryptography-rust.cyclonedx.json"
)
ALLOWED_UPSTREAM_BUILD_PATH = b"/Users/runner/work/cryptography/"


def audit_bundle(
    app_path: Path,
    *,
    expected_version: str,
    expected_build: str,
) -> dict[str, object]:
    app_path = Path(app_path).resolve()
    if not app_path.is_dir() or app_path.name != f"{APP_NAME}.app":
        raise RuntimeError("App-Bundle fehlt oder ist falsch benannt.")
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as source:
        plist = plistlib.load(source)
    expected_plist = {
        "CFBundleIdentifier": "de.jenaplan.kompetenzmanager",
        "CFBundleShortVersionString": expected_version,
        "CFBundleVersion": expected_build,
        "LSMinimumSystemVersion": "13.0",
    }
    if any(plist.get(key) != value for key, value in expected_plist.items()):
        raise RuntimeError("Bundle-Metadaten sind inkonsistent.")

    files = tuple(
        item
        for item in app_path.rglob("*")
        if item.is_file() and not item.is_symlink()
    )
    forbidden = tuple(
        item
        for item in files
        if item.suffix.lower() in FORBIDDEN_SUFFIXES
    )
    if forbidden:
        raise RuntimeError(
            f"Verbotenes Artefakt im Bundle: {forbidden[0].name}"
        )
    upstream_build_path_references = 0
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        payload = path.read_bytes()
        if b"/Users/" not in payload:
            continue
        relative = path.relative_to(app_path).as_posix()
        user_path_references = payload.count(b"/Users/")
        allowed_references = payload.count(ALLOWED_UPSTREAM_BUILD_PATH)
        if (
            relative == ALLOWED_UPSTREAM_BUILD_PATH_RESOURCE
            and user_path_references == allowed_references
        ):
            upstream_build_path_references += allowed_references
            continue
        if user_path_references:
            raise RuntimeError(
                f"Entwicklerpfad in Bundle-Ressource: {relative}"
            )

    architectures: dict[str, list[str]] = {}
    for path in files:
        values = _architectures(path)
        if not values:
            continue
        relative = path.relative_to(app_path).as_posix()
        architectures[relative] = list(values)
        if values != ("arm64",):
            raise RuntimeError(
                f"Nicht reines arm64-Mach-O im Bundle: {relative}"
            )
    if not architectures:
        raise RuntimeError("Bundle enthält keine prüfbaren Mach-O-Dateien.")

    native_names = {Path(name).name for name in architectures}
    required_native_fragments = (
        "_cffi_backend",
        "_sodium",
        "_sqlite3",
        "QtCore",
        "Shiboken",
        "libjkm_macos_security",
    )
    for fragment in required_native_fragments:
        if not any(fragment in name for name in native_names):
            raise RuntimeError(
                f"Native Laufzeit fehlt im Bundle: {fragment}"
            )

    license_root = (
        app_path
        / "Contents"
        / "Resources"
        / "third_party_licenses"
    )
    license_directories = {
        item.name for item in license_root.iterdir() if item.is_dir()
    }
    if not REQUIRED_LICENSE_DIRECTORIES <= license_directories:
        raise RuntimeError("Security-Lizenztexte fehlen im Bundle.")
    notice = (
        license_root / "THIRD_PARTY_NOTICES_SECURITY_0.3.0.md"
    )
    if not notice.is_file():
        raise RuntimeError("Security-Drittanbieterhinweis fehlt im Bundle.")
    return {
        "bundle_id": plist["CFBundleIdentifier"],
        "build": plist["CFBundleVersion"],
        "forbidden_artifacts": 0,
        "mach_o_count": len(architectures),
        "status": "ok",
        "upstream_build_path_references": (
            upstream_build_path_references
        ),
        "version": plist["CFBundleShortVersionString"],
    }


def _architectures(path: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["file", "-b", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or "Mach-O" not in result.stdout:
        return ()
    lipo = subprocess.run(
        ["lipo", "-archs", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if lipo.returncode != 0:
        raise RuntimeError(f"Mach-O-Prüfung fehlgeschlagen: {path.name}")
    return tuple(lipo.stdout.strip().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-build", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            audit_bundle(
                args.app,
                expected_version=args.expected_version,
                expected_build=args.expected_build,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
