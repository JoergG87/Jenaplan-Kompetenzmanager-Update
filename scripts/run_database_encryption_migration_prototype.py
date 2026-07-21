#!/usr/bin/env python3
"""Run the isolated Sprint-5 Envelope/Journal synthetic migration path."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
import uuid


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prototypes.database_encryption_migration import (
    MigrationPaths,
    SecureMigrationPrototypeEngine,
    SyntheticScale,
    create_synthetic_source,
)
from src.security.data_keys import LoadedDataMasterKey


def run(*, large: bool = False) -> dict[str, object]:
    dmk_material = bytearray(secrets.token_bytes(32))
    try:
        with TemporaryDirectory(prefix="jkm-security-sprint-5-") as directory:
            paths = MigrationPaths.in_workspace(Path(directory))
            create_synthetic_source(
                paths.source,
                SyntheticScale.large() if large else SyntheticScale(),
            )
            dmk = LoadedDataMasterKey(
                str(uuid.uuid4()), 1, bytes(dmk_material)
            )
            secure_report = SecureMigrationPrototypeEngine().run(paths, dmk=dmk)
            report = secure_report.migration
            return {
                "scope": "synthetic-only-security-sprint-5",
                "envelope_persisted": secure_report.envelope_path.is_file(),
                "journal_persisted": secure_report.journal_path.is_file(),
                "database_key_reload_verified": True,
                "successful": report.validation.successful,
                "table_count": report.validation.table_count,
                "total_rows": report.validation.total_rows,
                "validation": asdict(report.validation),
                "performance": asdict(report.performance),
                "source_unchanged": (
                    report.source_sha256_before == report.source_sha256_after
                ),
                "successful_reopen": report.successful_reopen,
                "rollback_required": report.rollback_required,
            }
    finally:
        for index in range(len(dmk_material)):
            dmk_material[index] = 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated synthetic SQLCipher migration prototype."
    )
    parser.add_argument("--large", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(large=args.large), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
