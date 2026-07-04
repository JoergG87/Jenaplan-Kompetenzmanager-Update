"""Validate that openpyxl preserves the VBA project in the seed workbook."""

from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "seeds" / "JenaplanSeed.xlsm"
OUTPUT_PATH = ROOT / "output" / "VBA_Seed_Test.xlsm"
VBA_PROJECT_PATH = "xl/vbaProject.bin"
MARKER_TEXT = "Python war hier"


def main() -> None:
    """Load the macro seed, modify one cell, save it, and verify VBA remains."""
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed-Datei fehlt: {SEED_PATH}")

    workbook = load_workbook(SEED_PATH, keep_vba=True)
    worksheet = workbook.active
    worksheet["A1"] = MARKER_TEXT

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT_PATH)
    if workbook.vba_archive is not None:
        workbook.vba_archive.close()
        workbook.vba_archive = None
    workbook.close()

    with ZipFile(OUTPUT_PATH) as archive:
        if VBA_PROJECT_PATH not in archive.namelist():
            raise RuntimeError(f"VBA-Projekt fehlt in {OUTPUT_PATH}: {VBA_PROJECT_PATH}")

    print(f"Seed validiert: {OUTPUT_PATH}")
    print(f"VBA-Projekt erhalten: {VBA_PROJECT_PATH}")
    print(f"A1 geschrieben: {MARKER_TEXT}")


if __name__ == "__main__":
    main()
