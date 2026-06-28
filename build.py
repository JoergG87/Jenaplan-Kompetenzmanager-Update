"""Build entry point for the Jenaplan Kompetenzmanager project."""

from pathlib import Path

from src.workbook import WorkbookBuilder


OUTPUT_DIR = Path("output")
V04_SOURCE_PATH = OUTPUT_DIR / "Jenaplan_Kompetenzmanager_v0.4.xlsx"


def main() -> None:
    """Start the workbook build and report the result."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        WorkbookBuilder(output_path=V04_SOURCE_PATH, prototype_version="v0.4").build()
    except Exception as exc:
        print(f"Jenaplan Kompetenzmanager Build fehlgeschlagen: {exc}")
        raise

    print("Jenaplan Kompetenzmanager Build erfolgreich:")
    print(f"- {V04_SOURCE_PATH}")


if __name__ == "__main__":
    main()
