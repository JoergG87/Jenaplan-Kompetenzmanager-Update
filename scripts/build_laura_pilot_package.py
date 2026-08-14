"""Build Laura's deterministic v0.2 pilot handoff from release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.commands.backup import (
    BackupApplicationService,
    VerifyBackupQuery,
)
from src.application.commands.restore import (
    RestoreApplicationService,
    VerifyRestoreBackupQuery,
)
from src.core.runtime_root_protection import require_unprotected_output_path


EMPTY_README_TEXT = """Jenaplan-Kompetenzmanager - Leere Pilotvariante

Version: {version}
Pilot-Commit: {pilot_commit}
Plattform: macOS 13 oder neuer, Apple Silicon (arm64)

Diese Variante ist für Erststart-, Konto-, Onboarding-, Login-, Touch-ID-,
Stammdaten-, Backup-/Restore- und Leerzustandstests bestimmt.

Empfohlene Reihenfolge:

1. README und Release-Hinweise lesen.
2. DMG öffnen und die App nach Programme ziehen.
3. Benutzerhandbuch beziehungsweise Erste Schritte bereithalten.
4. Leere App, Konto, Recovery, Sperre und erstes Backup prüfen.
5. Updates später ausschließlich unter Einstellungen > Updates bewusst prüfen.
6. Die Test-Excel für die Rückmeldungen verwenden.

Wichtige Grenzen:

- Diese App ist für den begleiteten Pilottest vorgesehen. Sie enthält das
  harmonisierte Branding und die abgestimmten Dialogkontexte aus Version {version}.
- Sie ist ad hoc signiert und nicht notarisiert. macOS kann beim ersten Öffnen
  einen Sicherheitshinweis anzeigen; die Installationshinweise im Handbuch
  beschreiben den vorgesehenen Weg.
- Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
  FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen.
- Der produktive Support-Reset ist ab Version 0.2.2 als betreuter Ausnahmeweg
  nach Kontakt mit dem Support freigeschaltet.
- Der Sparkle-Pilotkanal prüft oder installiert nichts automatisch. Version
  0.2.2 wird später bewusst unter Einstellungen > Updates angestoßen.
- Das Paket enthält keine Schüler-, Fach-, Laufzeit- oder Anmeldedaten.

Offene reale Prüfungen:

- echter Sleep/Wake
- physische Touch-ID-Systemaufforderung und Fingerabdruck
- App-Switcher-Prüfung
- vollständige Aktivierungs-/Widerrufsreise
- reale Keychain-/Touch-ID-Prüfung nach einem Support-Reset
- LEG-UX-Bewertung zur Sichtbarkeit von Vorschau und Gesprächsführung
- Developer-ID-Signierung
- Apple-Notarisierung
"""


LAURA_TESTDATA_README_TEXT = """Jenaplan-Kompetenzmanager - Laura-Testdatenvariante

Version: {version}
Pilot-Commit: {pilot_commit}
Plattform: macOS 13 oder neuer, Apple Silicon (arm64)

Diese Variante ist für den fachlichen Pilottest mit einem vorbereiteten,
ausschließlich synthetischen Acht-Monats-Datenbestand bestimmt.

Empfohlene Reihenfolge:

1. README und Release-Hinweise lesen.
2. DMG öffnen und dieselbe leere App wie in der Erststartvariante installieren.
3. Beim Erststart das lokale Konto vollständig einrichten und anmelden.
4. Zuerst leere App, Recovery, Sperre und erstes Backup prüfen.
5. Im letzten Schritt der Ersten Schritte "Testdaten jetzt einspielen" wählen
   oder später Einstellungen > Datensicherung öffnen.
6. "Laura-Testdaten-{version}.jkmbackup" über den normalen Restore-Weg auswählen,
   die schreibgeschützte Vorschau prüfen und die Wiederherstellung bestätigen.
7. Nach dem automatischen Neustart mit dem zuvor lokal angelegten Konto anmelden.
8. Die Test-Excel für die Rückmeldungen verwenden.
9. Version 0.2.2 später unter Einstellungen > Updates bewusst installieren.

Klare Trennung:

- App-Bundle und DMG enthalten keine Schüler- oder Fachdaten.
- Nur die separat beiliegende .jkmbackup-Datei enthält synthetische Fachdaten.
- Konto, Passwort, Recovery-Codes, Touch-ID-Zuordnung, Gerätecredentials,
  Security Store, Support-Tokens und Schlüssel sind nicht Bestandteil des Backups.
- Die produktive Public-Key-Registry enthält den freigegebenen öffentlichen
  Support-Schlüssel; private Schlüssel und Passphrasen bleiben außerhalb.
- Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
  FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen.
- Der produktive Support-Reset ist ab Version 0.2.2 als betreuter Ausnahmeweg
  nach Kontakt mit dem Support freigeschaltet.
- Testdaten werden niemals automatisch gesucht, ausgewählt oder importiert.
- Der Sparkle-Pilotkanal prüft oder installiert nichts automatisch.

Offene reale Prüfungen:

- echter Sleep/Wake
- physische Touch-ID-Systemaufforderung und Fingerabdruck
- App-Switcher-Prüfung
- vollständige Aktivierungs-/Widerrufsreise
- reale Keychain-/Touch-ID-Prüfung nach einem Support-Reset
- LEG-UX-Bewertung zur Sichtbarkeit von Vorschau und Gesprächsführung
- Developer-ID-Signierung
- Apple-Notarisierung
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
    pilot_commit: str = "nicht angegeben",
    variant: str = "empty",
    pilot_backup: Path | None = None,
) -> tuple[Path, Path]:
    if variant == "empty":
        package_variant = "Leer"
        readme_text = EMPTY_README_TEXT
        if pilot_backup is not None:
            raise ValueError("Die leere Pilotvariante darf kein Testdaten-Backup enthalten.")
    elif variant == "laura_testdata":
        package_variant = "Laura-Testdaten"
        readme_text = LAURA_TESTDATA_README_TEXT
        if pilot_backup is None:
            raise ValueError("Die Laura-Testdatenvariante benötigt ein Testdaten-Backup.")
        backup_verification = BackupApplicationService().verify(
            VerifyBackupQuery(pilot_backup)
        )
        restore_verification = RestoreApplicationService().verify(
            VerifyRestoreBackupQuery(pilot_backup)
        )
        if backup_verification.manifest.app_version != version:
            raise ValueError("Das Testdaten-Backup gehört zu einer anderen App-Version.")
        if restore_verification.preview.students_count <= 0:
            raise ValueError("Das Testdaten-Backup enthält keine synthetischen Schülerdaten.")
    else:
        raise ValueError(f"Unbekannte Pilotvariante: {variant}")
    package_name = (
        f"Jenaplan-Kompetenzmanager-{version}-Pilotpaket-{package_variant}-macOS-{architecture}"
    )
    package_root = output_root / package_name
    zip_path = output_root / f"{package_name}.zip"
    require_unprotected_output_path(output_root)
    if package_root.exists() or package_root.is_symlink():
        raise FileExistsError("Das Pilotpaket-Ziel existiert bereits.")
    if zip_path.exists() or zip_path.is_symlink():
        raise FileExistsError("Das Pilotpaket-Archiv existiert bereits.")
    package_root.mkdir(parents=True)

    (package_root / "README.txt").write_text(
        readme_text.format(version=version, pilot_commit=pilot_commit),
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
    if pilot_backup is not None:
        expected_backup_name = f"Laura-Testdaten-{version}.jkmbackup"
        if pilot_backup.name != expected_backup_name:
            raise ValueError(
                f"Das Testdaten-Backup muss {expected_backup_name} heißen."
            )
        _copy(pilot_backup, package_root / expected_backup_name)

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
    if pilot_backup is not None:
        expected_names.add(f"Laura-Testdaten-{version}.jkmbackup")
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
        allowed_backup = (
            variant == "laura_testdata"
            and path.name == f"Laura-Testdaten-{version}.jkmbackup"
        )
        if path.name in forbidden_names or (
            path.suffix.lower() in forbidden_suffixes and not allowed_backup
        ):
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
    parser.add_argument("--pilot-commit", required=True)
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
    parser.add_argument(
        "--variant",
        choices=("empty", "laura_testdata"),
        default="empty",
    )
    parser.add_argument("--pilot-backup", type=Path)
    args = parser.parse_args()
    package_root, zip_path = build_package(
        output_root=args.output_root,
        version=args.version,
        pilot_commit=args.pilot_commit,
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
        variant=args.variant,
        pilot_backup=args.pilot_backup,
    )
    print(package_root)
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
