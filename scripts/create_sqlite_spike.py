"""Create the Sprint 5.2a SQLite spike database and projection workbook."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.sqlite_store import (
    SQLITE_SPIKE_PATH,
    build_workbook_data_from_sqlite,
    create_sqlite_seed_database,
)
from src.ui.screens.klassenuebersicht import ClassOverviewV02WorkbookBuilder


OUTPUT_PATH = Path("output") / "Jenaplan_SQLite_Spike_5_2a.xlsx"


def main() -> None:
    database = create_sqlite_seed_database(SQLITE_SPIKE_PATH)
    projection_data = build_workbook_data_from_sqlite(database.path)
    ClassOverviewV02WorkbookBuilder(OUTPUT_PATH, projection_data).build()
    print(f"SQLite-Datenbank erzeugt: {database.path}")
    print(f"SQLite-Projektion erzeugt: {OUTPUT_PATH}")
    print(f"Students: {len(projection_data.students)}")
    print(f"Groups: {len(projection_data.groups)}")
    print(f"Courses: {len(projection_data.courses)}")


if __name__ == "__main__":
    main()
