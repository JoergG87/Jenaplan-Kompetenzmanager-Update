"""Verified backup boundary for one school-year transition source state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import secrets
import shutil
import sqlite3
import tempfile
import zipfile

from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
    VerifyBackupQuery,
)
from src.core.backup import BackupVerificationResult
from src.core.database_compatibility import (
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
)
from src.core.sqlite_school_year_transition import (
    school_year_transition_source_sha256,
)


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionBackupEvidence:
    """Immutable proof returned only after published-backup re-verification."""

    backup_id: str
    backup_sha256: str
    source_state_sha256: str
    source_schema_fingerprint: str
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class VerifiedSchoolYearTransitionBackupAdapter:
    """Create and independently re-verify one normal ``.jkmbackup``."""

    service: BackupApplicationService
    command: CreateBackupCommand
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC)
    backup_id_provider: Callable[[], str] = lambda: (
        f"SYB-{secrets.token_hex(16)}"
    )

    def create_and_verify(
        self,
    ) -> SchoolYearTransitionBackupEvidence:
        created = self.service.create_without_observation_recovery(self.command)
        verified = self.service.verify(VerifyBackupQuery(created.path))
        if (
            verified.path != created.path
            or verified.archive_sha256
            != created.verification.archive_sha256
            or verified.manifest != created.verification.manifest
        ):
            raise RuntimeError("transition_backup_verification_mismatch")
        source_state, source_schema = _verified_snapshot_identity(verified)
        final_verification = self.service.verify(VerifyBackupQuery(created.path))
        if (
            final_verification.archive_sha256 != verified.archive_sha256
            or final_verification.manifest != verified.manifest
        ):
            raise RuntimeError("transition_backup_verification_mismatch")
        return SchoolYearTransitionBackupEvidence(
            backup_id=self.backup_id_provider(),
            backup_sha256=final_verification.archive_sha256,
            source_state_sha256=source_state,
            source_schema_fingerprint=source_schema,
            verified_at=self.now_provider(),
        )


def _verified_snapshot_identity(
    verification: BackupVerificationResult,
) -> tuple[str, str]:
    manifest = verification.manifest
    with tempfile.TemporaryDirectory(
        prefix="jkm-transition-backup-verify-"
    ) as temporary_name:
        snapshot_path = Path(temporary_name) / "source.sqlite"
        with zipfile.ZipFile(verification.path, mode="r") as archive:
            with archive.open(manifest.database.archive_path) as source:
                with snapshot_path.open("xb") as target:
                    shutil.copyfileobj(source, target)
        if snapshot_path.stat().st_size != manifest.database.size_bytes:
            raise RuntimeError("transition_backup_database_size_mismatch")
        digest = hashlib.sha256()
        with snapshot_path.open("rb") as snapshot:
            while chunk := snapshot.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != manifest.database.sha256:
            raise RuntimeError("transition_backup_database_sha256_mismatch")
        source_schema = DatabaseCompatibilityPolicy.require_backup_compatible(
            DatabaseCompatibilityInspector().inspect(snapshot_path)
        ).schema_identity.fingerprint
        connection = sqlite3.connect(
            f"file:{snapshot_path}?mode=ro",
            uri=True,
        )
        try:
            if connection.row_factory is None:
                connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            source_state = school_year_transition_source_sha256(connection)
        finally:
            connection.close()
    return source_state, source_schema
