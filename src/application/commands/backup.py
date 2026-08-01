"""Application boundary for explicit backup creation and verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

from src.core.backup import (
    BackupResult,
    BackupService,
    BackupVerificationResult,
    BackupVerifier,
    SQLiteBackupEngine,
)


class RuntimePathSet(Protocol):
    """Minimal injected runtime-path contract needed by backup operations."""

    root: Path
    database: Path
    documents: Path


@dataclass(frozen=True)
class CreateBackupCommand:
    """Create one explicit backup in the injected target directory."""

    database_path: Path
    runtime_paths: RuntimePathSet
    target_path: Path
    app_version: str
    build_commit: str
    source_tree_state: str | None = None

    command_name: str = "backup.create"


@dataclass(frozen=True)
class VerifyBackupQuery:
    """Verify one existing backup without changing live data."""

    path: Path


class BackupApplicationService:
    """Coordinate backup core services from explicitly injected inputs."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        sqlite_engine: SQLiteBackupEngine | None = None,
        verifier: BackupVerifier | None = None,
    ) -> None:
        self.now = now or (lambda: datetime.now(UTC))
        self.sqlite_engine = sqlite_engine
        self.verifier = verifier or BackupVerifier()

    def create(self, command: CreateBackupCommand) -> BackupResult:
        return self._create(command, recover_pending_observations=True)

    def create_without_observation_recovery(
        self,
        command: CreateBackupCommand,
    ) -> BackupResult:
        """Create a backup that must not perform recovery-side writes."""
        return self._create(command, recover_pending_observations=False)

    def _create(
        self,
        command: CreateBackupCommand,
        *,
        recover_pending_observations: bool,
    ) -> BackupResult:
        paths = command.runtime_paths
        if Path(command.database_path) != Path(paths.database):
            raise ValueError(
                "Der injizierte Datenbankpfad stimmt nicht mit RuntimePaths ueberein."
            )
        return BackupService(
            database_path=command.database_path,
            data_root=paths.root,
            documents_root=paths.documents,
            target_directory=command.target_path,
            app_version=command.app_version,
            build_commit=command.build_commit,
            source_tree_state=command.source_tree_state,
            now=self.now,
            sqlite_engine=self.sqlite_engine,
            verifier=self.verifier,
        ).create_backup(
            recover_pending_observations=recover_pending_observations
        )

    def verify(self, query: VerifyBackupQuery) -> BackupVerificationResult:
        return self.verifier.verify_backup(query.path)
