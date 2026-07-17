"""Build Laura's deterministic v0.2 pilot handoff from release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path


README_TEXT = """Jenaplan-Kompetenzmanager - Pilotpaket für Laura

Version: {version}
Plattform: macOS 13 oder neuer, Apple Silicon (arm64)

Empfohlene Reihenfolge:

1. README und Release-Hinweise lesen.
2. DMG öffnen und die App nach Programme ziehen.
3. Benutzerhandbuch beziehungsweise Erste Schritte bereithalten.
4. Die Test-Excel für die Rückmeldungen verwenden.

Wichtige Grenzen:

- Diese App ist für den Pilottest vorgesehen.
- Sie ist ad hoc signiert und nicht notarisiert. macOS kann beim ersten Öffnen
  einen Sicherheitshinweis anzeigen; die Installationshinweise im Handbuch
  beschreiben den vorgesehenen Weg.
- Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
  FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen.
- Der produktive Support-Reset ist ohne freigegebenen öffentlichen Schlüssel
  noch nicht freigeschaltet.
- Echte Sleep/Wake- und Touch-ID-Abnahme, App-Switcher-Prüfung sowie die
  vollständige reale Aktivierungs- und Widerrufsreise und die LEG-UX-Bewertung
  von Vorschau beziehungsweise Gesprächsführung sind noch offen.
- Das Paket enthält keine Schüler-, Laufzeit- oder Anmeldedaten.
"""


def _copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Release-Eingabe fehlt: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(
    *,
    output_root: Path,
    version: str,
    architecture: str,
    dmg: Path,
    first_steps_pdf: Path,
    manual_pdf: Path,
    quickstart_pdf: Path,
    installation_pdf: Path,
    backup_guide_pdf: Path,
    pilot_workbook: Path,
    release_notes: Path,
    release_inventory: Path,
) -> tuple[Path, Path]:
    package_name = (
        f"Jenaplan-Kompetenzmanager-{version}-Pilotpaket-Laura-macOS-{architecture}"
    )
    package_root = output_root / package_name
    zip_path = output_root / f"{package_name}.zip"
    if package_root.exists():
        shutil.rmtree(package_root)
    zip_path.unlink(missing_ok=True)
    package_root.mkdir(parents=True)

    (package_root / "README.txt").write_text(
        README_TEXT.format(version=version),
        encoding="utf-8",
    )
    _copy(dmg, package_root / dmg.name)
    _copy(
        manual_pdf,
        package_root / f"Jenaplan-Kompetenzmanager-{version}-Benutzerhandbuch.pdf",
    )
    _copy(
        first_steps_pdf,
        package_root / f"Jenaplan-Kompetenzmanager-{version}-Erste-Schritte.pdf",
    )
    _copy(
        quickstart_pdf,
        package_root / f"Jenaplan-Kompetenzmanager-{version}-Schnellstart.pdf",
    )
    _copy(
        installation_pdf,
        package_root
        / f"Jenaplan-Kompetenzmanager-{version}-Installationsanleitung.pdf",
    )
    _copy(
        backup_guide_pdf,
        package_root / f"Jenaplan-Kompetenzmanager-{version}-Backup-Anleitung.pdf",
    )
    _copy(pilot_workbook, package_root / pilot_workbook.name)
    _copy(release_notes, package_root / "RELEASE_NOTES.md")
    _copy(
        release_inventory,
        package_root / f"RELEASE_INVENTORY-{version}.txt",
    )

    checksum_name = f"SHA256SUMS-{version}.txt"
    checksum_targets = tuple(
        sorted(
            path
            for path in package_root.iterdir()
            if path.is_file() and path.name != checksum_name
        )
    )
    checksum_lines = [f"{_sha256(path)}  {path.name}" for path in checksum_targets]
    (package_root / checksum_name).write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )

    files = tuple(sorted(path for path in package_root.rglob("*") if path.is_file()))
    expected_names = {
        "README.txt",
        dmg.name,
        f"Jenaplan-Kompetenzmanager-{version}-Benutzerhandbuch.pdf",
        f"Jenaplan-Kompetenzmanager-{version}-Erste-Schritte.pdf",
        f"Jenaplan-Kompetenzmanager-{version}-Schnellstart.pdf",
        f"Jenaplan-Kompetenzmanager-{version}-Installationsanleitung.pdf",
        f"Jenaplan-Kompetenzmanager-{version}-Backup-Anleitung.pdf",
        pilot_workbook.name,
        "RELEASE_NOTES.md",
        checksum_name,
        f"RELEASE_INVENTORY-{version}.txt",
    }
    actual_names = {path.name for path in files}
    if actual_names != expected_names:
        raise RuntimeError(
            "Unerwartete Release-Dateien: "
            f"fehlt={sorted(expected_names - actual_names)}, "
            f"zusätzlich={sorted(actual_names - expected_names)}"
        )
    forbidden_suffixes = {
        ".sqlite",
        ".db",
        ".jkmbackup",
        ".jkmresetrequest",
        ".jkmresettoken",
        ".py",
        ".pyc",
        ".log",
        ".key",
        ".pem",
    }
    forbidden_names = {".DS_Store", "app-preferences.json", "enrollment.marker"}
    for path in files:
        relative = path.relative_to(package_root).as_posix()
        if "0.1.2" in relative or "SmokeTest" in relative:
            raise RuntimeError(f"Altes oder unerlaubtes Release-Artefakt: {relative}")
        if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
            raise RuntimeError(f"Unzulässige Datei im Pilotpaket: {relative}")
        if "__pycache__" in path.parts or "__MACOSX" in path.parts:
            raise RuntimeError(f"Entwicklerdatei im Pilotpaket: {relative}")

    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = path.relative_to(output_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    return package_root, zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--dmg", type=Path, required=True)
    parser.add_argument("--first-steps-pdf", type=Path, required=True)
    parser.add_argument("--manual-pdf", type=Path, required=True)
    parser.add_argument("--quickstart-pdf", type=Path, required=True)
    parser.add_argument("--installation-pdf", type=Path, required=True)
    parser.add_argument("--backup-guide-pdf", type=Path, required=True)
    parser.add_argument("--pilot-workbook", type=Path, required=True)
    parser.add_argument("--release-notes", type=Path, required=True)
    parser.add_argument("--release-inventory", type=Path, required=True)
    args = parser.parse_args()
    package_root, zip_path = build_package(
        output_root=args.output_root,
        version=args.version,
        architecture=args.architecture,
        dmg=args.dmg,
        first_steps_pdf=args.first_steps_pdf,
        manual_pdf=args.manual_pdf,
        quickstart_pdf=args.quickstart_pdf,
        installation_pdf=args.installation_pdf,
        backup_guide_pdf=args.backup_guide_pdf,
        pilot_workbook=args.pilot_workbook,
        release_notes=args.release_notes,
        release_inventory=args.release_inventory,
    )
    print(package_root)
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
