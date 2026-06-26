"""Build entry point for the Jenaplan Kompetenzmanager project."""

from pathlib import Path

from src.workbook import WorkbookBuilder


def main() -> None:
    """Start the workbook build and report the result."""
    output_path = Path("output") / "Jenaplan_v3.2.xlsx"

    try:
        WorkbookBuilder(output_path=output_path).build()
    except Exception as exc:
        print(f"Jenaplan Kompetenzmanager Build fehlgeschlagen: {exc}")
        raise

    print(f"Jenaplan Kompetenzmanager Build erfolgreich: {output_path}")


if __name__ == "__main__":
    main()
