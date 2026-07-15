"""Build the Laura handoff directory and deterministic ZIP from fresh outputs."""

from __future__ import annotations

import argparse
import shutil
import stat
import zipfile
from pathlib import Path


START_TEXT = """Willkommen beim Pilot des
Jenaplan-Kompetenzmanagers

Pilotversion {version}

Vielen Dank für die Teilnahme am Pilot.

Diese Version enthält ausschließlich fiktive Testdaten.

Empfohlene Reihenfolge:

1. Lies zuerst \"Erste Schritte\".
2. Installiere die App.
3. Öffne die Anwendung.
4. Nutze anschließend die Excel-Datei:
   Pilottest_Laura_Schuelerprofil_Variante_A.xlsx

Feedback:

Bitte bei Rückmeldungen immer angeben:

- Testnummer
- Beschreibung
- Screenshot (wenn möglich)
- Kategorie: Bug / UX / Wunsch / Produktentscheidung
"""

VERSION_TEXT = """Jenaplan-Kompetenzmanager

Pilotversion:
{version}

Tester:
Laura

Daten:
Fiktive Pilotdaten

Enthalten:
- Dashboard
- Beobachtungen
- Schülerprofile
- Berichte
- Revisionen
- LEG
- Stundenplan
- Stammdaten

Nicht enthalten:
- Cloud
- Benutzerkonten
- Rollen
- automatische Backups
- Auto-Updater
"""


def _copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Release-Eingabe fehlt: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def build_package(
    *,
    output_root: Path,
    version: str,
    dmg: Path,
    installation_pdf: Path,
    first_steps_pdf: Path,
    manual_pdf: Path,
    quickstart_pdf: Path,
    pilot_workbook: Path,
    backup_pdf: Path,
    backup_script: Path,
) -> tuple[Path, Path]:
    package_name = f"Jenaplan-Kompetenzmanager_Pilot_{version}_Laura"
    package_root = output_root / package_name
    zip_path = output_root / f"{package_name}.zip"
    if package_root.exists():
        shutil.rmtree(package_root)
    zip_path.unlink(missing_ok=True)
    package_root.mkdir(parents=True)

    (package_root / "00_START_HIER.txt").write_text(
        START_TEXT.format(version=version),
        encoding="utf-8",
    )
    (package_root / "PILOT_VERSION.txt").write_text(
        VERSION_TEXT.format(version=version),
        encoding="utf-8",
    )
    _copy(dmg, package_root / "01_App" / dmg.name)
    _copy(installation_pdf, package_root / "02_Installation" / "Installationsanleitung.pdf")
    _copy(first_steps_pdf, package_root / "02_Installation" / "Erste_Schritte.pdf")
    _copy(manual_pdf, package_root / "03_Benutzerhandbuch" / "Jenaplan-Kompetenzmanager_Benutzerhandbuch.pdf")
    _copy(quickstart_pdf, package_root / "03_Benutzerhandbuch" / "Schnellstart_Lehrkraefte.pdf")
    _copy(pilot_workbook, package_root / "04_Pilottest" / pilot_workbook.name)
    _copy(backup_pdf, package_root / "05_Backup" / "Backup-Anleitung.pdf")
    backup_target = package_root / "05_Backup" / "Backup-Skript.sh"
    _copy(backup_script, backup_target)
    backup_target.chmod(backup_target.stat().st_mode | stat.S_IXUSR)

    files = tuple(sorted(path for path in package_root.rglob("*") if path.is_file()))
    if len(files) != 10:
        raise RuntimeError(f"Unerwartete Anzahl Release-Dateien: {len(files)}")
    forbidden_suffixes = {".sqlite", ".db", ".py", ".pyc", ".log"}
    for path in files:
        relative = path.relative_to(package_root).as_posix()
        if "0.1.0" in relative or path.name == ".DS_Store":
            raise RuntimeError(f"Altes oder unerlaubtes Release-Artefakt: {relative}")
        if path.suffix.lower() in forbidden_suffixes or "__pycache__" in path.parts:
            raise RuntimeError(f"Entwicklerdatei im Release-Artefakt: {relative}")
    for text_name in ("00_START_HIER.txt", "PILOT_VERSION.txt"):
        content = (package_root / text_name).read_text(encoding="utf-8")
        if version not in content or "0.1.0" in content:
            raise RuntimeError(f"Falsche Pilotversion in {text_name}")

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
    parser.add_argument("--dmg", type=Path, required=True)
    parser.add_argument("--installation-pdf", type=Path, required=True)
    parser.add_argument("--first-steps-pdf", type=Path, required=True)
    parser.add_argument("--manual-pdf", type=Path, required=True)
    parser.add_argument("--quickstart-pdf", type=Path, required=True)
    parser.add_argument("--pilot-workbook", type=Path, required=True)
    parser.add_argument("--backup-pdf", type=Path, required=True)
    parser.add_argument("--backup-script", type=Path, required=True)
    args = parser.parse_args()
    package_root, zip_path = build_package(
        output_root=args.output_root,
        version=args.version,
        dmg=args.dmg,
        installation_pdf=args.installation_pdf,
        first_steps_pdf=args.first_steps_pdf,
        manual_pdf=args.manual_pdf,
        quickstart_pdf=args.quickstart_pdf,
        pilot_workbook=args.pilot_workbook,
        backup_pdf=args.backup_pdf,
        backup_script=args.backup_script,
    )
    print(package_root)
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
