"""Build entry point for the Jenaplan Kompetenzmanager project."""

from pathlib import Path

from src.workbook import WorkbookBuilder


OUTPUT_DIR = Path("output")
FIRST_ATTEMPT_PATH = OUTPUT_DIR / "Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx"
LEGACY_V01_PATH = OUTPUT_DIR / "Jenaplan_UX_Prototype_v0.1.xlsx"
V02_PATH = OUTPUT_DIR / "Jenaplan_UX_Prototype_v0.2.xlsx"


def main() -> None:
    """Start the workbook build and report the result."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if not FIRST_ATTEMPT_PATH.exists():
            if LEGACY_V01_PATH.exists():
                LEGACY_V01_PATH.replace(FIRST_ATTEMPT_PATH)
            else:
                WorkbookBuilder(output_path=FIRST_ATTEMPT_PATH, prototype_version="v0.1").build()

        WorkbookBuilder(output_path=V02_PATH, prototype_version="v0.2").build()
    except Exception as exc:
        print(f"Jenaplan Kompetenzmanager Build fehlgeschlagen: {exc}")
        raise

    print("Jenaplan Kompetenzmanager Build erfolgreich:")
    print(f"- {FIRST_ATTEMPT_PATH}")
    print(f"- {V02_PATH}")


if __name__ == "__main__":
    main()
