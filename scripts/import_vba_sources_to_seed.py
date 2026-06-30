"""Import versioned VBA module sources into the validated seed workbook."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "seeds" / "JenaplanSeed.xlsm"
MODULE_DIR = ROOT / "vba" / "modules"
APPLESCRIPT_PATH = ROOT / "scripts" / "import_vba_sources_to_seed.applescript"
MODULE_SOURCES = (
    MODULE_DIR / "Globals.bas",
    MODULE_DIR / "Navigation.bas",
    MODULE_DIR / "UI.bas",
)
VBA_PROJECT_PATH = "xl/vbaProject.bin"
BOOTSTRAP_MARKERS = (
    b"SeedImport",
    b"ImportVbaSourcesToSeedFromRepo",
    b"ImportVbaSourcesToSeed",
)
REQUIRED_MODULE_MARKERS = (
    b"Module=Globals",
    b"Module=Navigation",
    b"Module=UI",
)


def main() -> None:
    """Run the Excel-hosted VBA import macro for the seed workbook."""
    parser = argparse.ArgumentParser(
        description="Importiere versionierte .bas-Quellen in seeds/JenaplanSeed.xlsm.",
    )
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    args = parser.parse_args()

    seed_path = args.seed.resolve()
    module_paths = tuple(path.resolve() for path in MODULE_SOURCES)
    _validate_inputs(seed_path, module_paths)
    _require_seed_importer(seed_path)

    command = [
        "osascript",
        str(APPLESCRIPT_PATH),
        str(seed_path),
    ]
    subprocess.run(command, check=True)
    _validate_imported_modules(seed_path)

    print(f"VBA-Quellen in Seed importiert: {seed_path}")
    for path in module_paths:
        print(f"- {path}")


def _validate_inputs(seed_path: Path, module_paths: tuple[Path, ...]) -> None:
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed-Datei fehlt: {seed_path}")
    if seed_path.suffix.lower() != ".xlsm":
        raise ValueError(f"Seed muss eine .xlsm-Datei sein: {seed_path}")
    if not APPLESCRIPT_PATH.exists():
        raise FileNotFoundError(f"AppleScript fehlt: {APPLESCRIPT_PATH}")
    for module_path in module_paths:
        if not module_path.exists():
            raise FileNotFoundError(f"VBA-Quelldatei fehlt: {module_path}")


def _require_seed_importer(seed_path: Path) -> None:
    project = _read_vba_project(seed_path)
    if any(marker not in project for marker in BOOTSTRAP_MARKERS):
        raise RuntimeError(
            "SeedImport-Makro fehlt im Seed oder ist veraltet. "
            "Bitte die aktuelle Datei vba/modules/SeedImport.bas einmalig in "
            "seeds/JenaplanSeed.xlsm importieren und den Seed speichern; danach "
            "kann dieses Skript Globals, Navigation und UI automatisch aktualisieren."
        )


def _validate_imported_modules(seed_path: Path) -> None:
    project = _read_vba_project(seed_path)
    missing = [
        marker.decode("ascii")
        for marker in REQUIRED_MODULE_MARKERS
        if marker not in project
    ]
    if missing:
        raise RuntimeError(
            "Seed-VBA-Projekt ist nach dem Import unvollstaendig. "
            f"Fehlende Module: {', '.join(missing)}"
        )


def _read_vba_project(seed_path: Path) -> bytes:
    with ZipFile(seed_path) as archive:
        if VBA_PROJECT_PATH not in archive.namelist():
            raise RuntimeError(f"VBA-Projekt fehlt im Seed: {VBA_PROJECT_PATH}")
        return archive.read(VBA_PROJECT_PATH)


if __name__ == "__main__":
    main()
