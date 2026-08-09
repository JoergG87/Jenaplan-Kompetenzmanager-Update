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
FORBIDDEN_PATH_COMPONENTS = {
    "__pycache__",
    "buildtemp",
    "pyinstaller-work",
    "venv",
}
FORBIDDEN_CONTENT = (
    b"src.security.packaged_integration_smoke",
    b"src.security.integration_orchestrator",
    b"prototypes.database_encryption_migration",
)
REQUIRED_SUBJECT_VIGNETTES = {
    "deutsch.png",
    "epu.png",
    "ethik.png",
    "kunst.png",
    "mathematik.png",
    "musik.png",
    "religion.png",
    "schulgarten.png",
    "sport.png",
    "werken.png",
}
REQUIRED_LICENSE_DIRECTORIES = {
    "PyNaCl",
    "cffi",
    "cryptography",
    "libsodium",
    "sqlcipher3",
}
REQUIRED_SECURITY_NOTICES = {
    "THIRD_PARTY_NOTICES_SECURITY_0.3.0.md",
    "THIRD_PARTY_NOTICES_SQLCIPHER_4_17_MACOS.md",
}
LOCAL_DEVELOPER_PATH_PREFIX = b"/Users/lauragehrke/"


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
        or item.suffix.lower() == ".whl"
        or any(part.lower() in FORBIDDEN_PATH_COMPONENTS for part in item.parts)
    )
    if forbidden:
        raise RuntimeError(
            f"Verbotenes Artefakt im Bundle: {forbidden[0].name}"
        )
    upstream_build_path_references = 0
    for path in files:
        payload = path.read_bytes()
        relative = path.relative_to(app_path).as_posix()
        user_path_references = payload.count(b"/Users/")
        if LOCAL_DEVELOPER_PATH_PREFIX in payload:
            raise RuntimeError(
                f"Entwicklerpfad in Bundle-Ressource: {relative}"
            )
        upstream_build_path_references += user_path_references
        if b"/private/tmp/jkm-" in payload:
            raise RuntimeError(f"Buildtemp-Pfad im Bundle: {relative}")
        if any(token in payload for token in FORBIDDEN_CONTENT):
            raise RuntimeError(f"Veralteter Security-Prototyp im Bundle: {relative}")

    architectures: dict[str, list[str]] = {}
    rpaths: dict[str, list[str]] = {}
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
        observed_rpaths = _rpaths(path)
        if any(
            not value.startswith(("@loader_path", "@executable_path"))
            for value in observed_rpaths
        ):
            raise RuntimeError(f"Unerwarteter LC_RPATH im Bundle: {relative}")
        rpaths[relative] = list(observed_rpaths)
        for dependency in _linked_libraries(path):
            if dependency.startswith(("/System/Library/", "/usr/lib/")):
                continue
            if dependency.startswith(("@rpath/", "@loader_path/", "@executable_path/")):
                continue
            raise RuntimeError(
                f"Unerwartete native Abhängigkeit im Bundle: {relative}"
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
    if any(not (license_root / name).is_file() for name in REQUIRED_SECURITY_NOTICES):
        raise RuntimeError("Security-Drittanbieterhinweis fehlt im Bundle.")
    sqlcipher_extensions = tuple(
        path
        for path in files
        if path.parent.name == "sqlcipher3"
        and path.name.startswith("_sqlite3")
        and _architectures(path)
    )
    if len(sqlcipher_extensions) != 1:
        raise RuntimeError("SQLCipher-native Extension fehlt oder ist mehrdeutig.")
    linkage = _linked_libraries(sqlcipher_extensions[0])
    if not any("Security.framework" in item for item in linkage):
        raise RuntimeError("SQLCipher-Extension ist nicht an CommonCrypto gebunden.")
    forbidden_linkage = ("libcrypto", "libssl", "/usr/local/", "/opt/homebrew/")
    if any(token in item for item in linkage for token in forbidden_linkage):
        raise RuntimeError("SQLCipher-Extension besitzt unzulässige Abhängigkeiten.")
    vignette_root = app_path / "Contents" / "Resources" / "assets" / "subject_vignettes"
    if (
        not vignette_root.is_dir()
        or {path.name for path in vignette_root.iterdir() if path.is_file()}
        != REQUIRED_SUBJECT_VIGNETTES
    ):
        raise RuntimeError("Fachillustrationsassets fehlen oder sind unerwartet.")
    runtime = _audit_packaged_runtime(app_path)
    return {
        "bundle_id": plist["CFBundleIdentifier"],
        "build": plist["CFBundleVersion"],
        "forbidden_artifacts": 0,
        "mach_o_count": len(architectures),
        "rpath_count": sum(len(values) for values in rpaths.values()),
        "runtime": runtime,
        "sqlcipher_native": sqlcipher_extensions[0].name,
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


def _linked_libraries(path: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["otool", "-L", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("Native SQLCipher-Abhängigkeiten sind nicht prüfbar.")
    return tuple(
        line.strip().split(" (", 1)[0]
        for line in result.stdout.splitlines()[1:]
        if line.strip()
    )


def _rpaths(path: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["otool", "-l", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LC_RPATH-Prüfung fehlgeschlagen: {path.name}")
    lines = result.stdout.splitlines()
    values: list[str] = []
    for index, line in enumerate(lines[:-1]):
        if line.strip() == "cmd LC_RPATH":
            path_line = lines[index + 2].strip()
            if not path_line.startswith("path ") or " (offset " not in path_line:
                raise RuntimeError(f"LC_RPATH ist nicht auswertbar: {path.name}")
            values.append(path_line[5:].split(" (offset ", 1)[0])
    return tuple(values)


def _audit_packaged_runtime(app_path: Path) -> dict[str, object]:
    executable = app_path / "Contents" / "MacOS" / APP_NAME
    result = subprocess.run(
        [str(executable), "--packaged-runtime-audit"],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError("Gebündelte SQLCipher-Runtime ist nicht ausführbar.")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    if payload != {
        "binding": "0.6.2+jkm.sqlcipher4170.1",
        "cipher_provider": "commoncrypto",
        "cipher_version": "4.17.0 community",
        "integrity": [],
        "sqlite_version": "3.53.3",
    }:
        raise RuntimeError("Gebündelte SQLCipher-Runtime ist unerwartet.")
    return payload


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
