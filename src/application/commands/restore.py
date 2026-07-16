"""Application boundary for read-only restore-backup verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.restore import RestoreVerificationResult, RestoreVerifier


@dataclass(frozen=True)
class VerifyRestoreBackupQuery:
    """Verify one backup and produce a technical restore preview."""

    path: Path


class RestoreApplicationService:
    """Coordinate restore verification without commands that mutate data."""

    def __init__(self, verifier: RestoreVerifier | None = None) -> None:
        self.verifier = verifier or RestoreVerifier()

    def verify(self, query: VerifyRestoreBackupQuery) -> RestoreVerificationResult:
        return self.verifier.verify(query.path)
