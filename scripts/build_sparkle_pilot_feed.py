"""Build one signed Sparkle pilot archive and its signed appcast."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import plistlib
import shutil
import subprocess
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


SPARKLE_NAMESPACE = "http://www.andymatuschak.org/xml-namespaces/sparkle"
EXPECTED_BUNDLE_ID = "de.jenaplan.kompetenzmanager"
EXPECTED_ARCHITECTURE = "arm64"


def _https_prefix(value: str, *, name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{name} muss eine feste HTTPS-URL ohne Zugangsdaten sein.")
    if any(part in value for part in ("/Users/", "/private/tmp", "localhost")):
        raise ValueError(f"{name} enthält einen lokalen Pfad oder Host.")
    return value.rstrip("/") + "/"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_app_bundle(app_path: Path, *, short_version: str, build_version: str) -> None:
    plist_path = app_path / "Contents" / "Info.plist"
    if not plist_path.is_file():
        raise ValueError("Info.plist fehlt im Update-App-Bundle.")
    with plist_path.open("rb") as handle:
        info = plistlib.load(handle)
    expected = {
        "CFBundleIdentifier": EXPECTED_BUNDLE_ID,
        "CFBundleShortVersionString": short_version,
        "CFBundleVersion": build_version,
        "LSMinimumSystemVersion": "13.0",
    }
    for key, value in expected.items():
        if str(info.get(key, "")) != value:
            raise ValueError(f"Update-App besitzt unerwarteten Wert für {key}.")
    if not info.get("SUPublicEDKey") or not info.get("SURequireSignedFeed"):
        raise ValueError("Sparkle-Public-Key oder signierter Feed fehlt im Bundle.")
    if not info.get("SUVerifyUpdateBeforeExtraction"):
        raise ValueError(
            "Die Vorabprüfung des Updatearchivs fehlt für den signierten Feed."
        )
    executable_name = str(info.get("CFBundleExecutable", "")).strip()
    executable = app_path / "Contents" / "MacOS" / executable_name
    if not executable_name or not executable.is_file():
        raise ValueError("Das Update-App-Bundle besitzt kein ausführbares Hauptprogramm.")
    architecture = subprocess.run(
        ["lipo", "-archs", str(executable)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if architecture != [EXPECTED_ARCHITECTURE]:
        raise ValueError("Das Update-App-Bundle besitzt nicht ausschließlich arm64.")
    subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def validate_generated_appcast(
    appcast: Path,
    *,
    archive_url: str,
    short_version: str,
    build_version: str,
) -> None:
    payload = appcast.read_text(encoding="utf-8")
    if any(value in payload for value in ("/Users/", "/private/tmp", "localhost")):
        raise ValueError("Der Appcast enthält einen lokalen Pfad oder Host.")
    root = ET.fromstring(payload)
    item = root.find("./channel/item")
    if item is None:
        raise ValueError("Der Appcast enthält keinen Updateeintrag.")
    enclosure = item.find("enclosure")
    if enclosure is None:
        raise ValueError("Der Appcast enthält kein Updateartefakt.")
    if enclosure.get("url") != archive_url:
        raise ValueError("Die Asset-URL im Appcast ist nicht kanonisch.")
    version = item.find(f"{{{SPARKLE_NAMESPACE}}}version")
    short_version_element = item.find(
        f"{{{SPARKLE_NAMESPACE}}}shortVersionString"
    )
    if version is None or version.text != build_version:
        raise ValueError("Die technische Buildnummer im Appcast ist inkonsistent.")
    if short_version_element is None or short_version_element.text != short_version:
        raise ValueError("Die sichtbare Version im Appcast ist inkonsistent.")
    if not enclosure.get(f"{{{SPARKLE_NAMESPACE}}}edSignature"):
        raise ValueError("Das Updatearchiv besitzt keine EdDSA-Signatur.")
    if "<!-- sparkle-signatures:" not in payload or "edSignature:" not in payload:
        raise ValueError("Der Appcast selbst ist nicht signiert.")


def build_pilot_feed(
    *,
    app_path: Path,
    output_dir: Path,
    sparkle_root: Path,
    short_version: str,
    build_version: str,
    minimum_update_build: str,
    release_download_prefix: str,
    pages_prefix: str,
    release_notes: Path,
    keychain_account: str,
) -> tuple[Path, Path, Path]:
    release_download_prefix = _https_prefix(
        release_download_prefix, name="Release-Download-URL"
    )
    pages_prefix = _https_prefix(pages_prefix, name="Pages-URL")
    validate_app_bundle(
        app_path, short_version=short_version, build_version=build_version
    )
    if not release_notes.is_file():
        raise FileNotFoundError(release_notes)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = f"Jenaplan-Kompetenzmanager-{short_version}-macOS-{EXPECTED_ARCHITECTURE}"
    archive = output_dir / f"{base}.zip"
    notes_target = output_dir / f"{base}.html"
    appcast = output_dir / "appcast.xml"
    for target in (archive, notes_target, appcast):
        target.unlink(missing_ok=True)
    subprocess.run(
        [
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(app_path),
            str(archive),
        ],
        check=True,
    )
    shutil.copy2(release_notes, notes_target)
    generator = sparkle_root / "bin" / "generate_appcast"
    if not generator.is_file():
        raise FileNotFoundError(generator)
    subprocess.run(
        [
            str(generator),
            "--account",
            keychain_account,
            "--download-url-prefix",
            release_download_prefix,
            "--release-notes-url-prefix",
            pages_prefix,
            "--minimum-update-version",
            minimum_update_build,
            "--maximum-deltas",
            "0",
            "--versions",
            build_version,
            "-o",
            str(appcast),
            str(output_dir),
        ],
        check=True,
    )
    archive_url = release_download_prefix + archive.name
    validate_generated_appcast(
        appcast,
        archive_url=archive_url,
        short_version=short_version,
        build_version=build_version,
    )
    checksums = output_dir / "SHA256SUMS.txt"
    checksums.write_text(
        "".join(
            f"{_sha256(path)}  {path.name}\n"
            for path in (archive, appcast, notes_target)
        ),
        encoding="utf-8",
    )
    return archive, appcast, checksums


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sparkle-root", type=Path, required=True)
    parser.add_argument("--short-version", required=True)
    parser.add_argument("--build-version", required=True)
    parser.add_argument("--minimum-update-build", required=True)
    parser.add_argument("--release-download-prefix", required=True)
    parser.add_argument("--pages-prefix", required=True)
    parser.add_argument("--release-notes", type=Path, required=True)
    parser.add_argument(
        "--keychain-account",
        default="de.jenaplan.kompetenzmanager.pilot",
    )
    args = parser.parse_args()
    archive, appcast, checksums = build_pilot_feed(
        app_path=args.app,
        output_dir=args.output,
        sparkle_root=args.sparkle_root,
        short_version=args.short_version,
        build_version=args.build_version,
        minimum_update_build=args.minimum_update_build,
        release_download_prefix=args.release_download_prefix,
        pages_prefix=args.pages_prefix,
        release_notes=args.release_notes,
        keychain_account=args.keychain_account,
    )
    print(archive)
    print(appcast)
    print(checksums)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
