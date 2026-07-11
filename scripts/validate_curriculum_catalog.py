"""Validate the curriculum catalog CSV before fachliche catalog work."""

from __future__ import annotations

import argparse
from pathlib import Path

from curriculum_catalog_tools import validate_catalog


DEFAULT_CATALOG_PATH = Path("data") / "curriculum_catalog_v1.csv"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the curriculum catalog CSV structure and invariants."
    )
    parser.add_argument(
        "catalog",
        nargs="?",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to the semicolon-delimited curriculum catalog CSV.",
    )
    args = parser.parse_args()

    issues = validate_catalog(args.catalog)
    if issues:
        for issue in issues:
            print(issue.format())
        return 1
    print(f"OK: {args.catalog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
