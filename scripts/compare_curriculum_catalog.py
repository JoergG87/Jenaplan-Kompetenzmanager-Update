"""Compare two curriculum catalog CSV versions before updating the catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from curriculum_catalog_tools import compare_catalogs, has_blocking_compare_issue


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two curriculum catalog CSV versions by competency_id."
    )
    parser.add_argument("old_catalog", type=Path, help="Approved baseline catalog CSV.")
    parser.add_argument("new_catalog", type=Path, help="Candidate catalog CSV.")
    args = parser.parse_args()

    issues = compare_catalogs(args.old_catalog, args.new_catalog)
    if not issues:
        print("OK: catalogs have no differences.")
        return 0
    for issue in issues:
        print(issue.format())
    return 1 if has_blocking_compare_issue(issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
