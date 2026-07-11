"""Print the next free global CMP IDs for new curriculum competencies."""

from __future__ import annotations

import argparse
from pathlib import Path

from curriculum_catalog_tools import next_competency_ids


DEFAULT_CATALOG_PATH = Path("data") / "curriculum_catalog_v1.csv"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Return the next global CMP IDs without reusing gaps."
    )
    parser.add_argument(
        "catalog",
        nargs="?",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to the semicolon-delimited curriculum catalog CSV.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of IDs to print.",
    )
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be at least 1")
    for competency_id in next_competency_ids(args.catalog, args.count):
        print(competency_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
