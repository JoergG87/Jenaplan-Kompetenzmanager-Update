"""Product adapters for the existing encrypted Final-V4 backup runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
import uuid

from src.application.commands.backup import CreateBackupCommand, VerifyBackupQuery
from src.application.commands.restore import (
    CreateRestoreHandoffCommand,
    PrepareRestoreStagingCommand,
    VerifyPreparedRestoreQuery,
    VerifyRestoreBackupQuery,
)
from src.core.database_compatibility import (
    DatabaseCompatibilityStatus,
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
)
from src.core.restore import RestoreCompatibility, RestorePreview
from src.core.restore_runtime import RestoreHandoffResult, RuntimeInstanceLock
from src.security.final_v4_backup_runtime import (
    FinalV4EncryptedBackupResult,
    FinalV4EncryptedBackupService,
)
from src.security.final_v4_live_restore import (
    FinalV4LiveRestorePreparation,
    launch_prepared_final_v4_restore,
    prepare_final_v4_live_restore,
)


FINAL_V4_ENCRYPTED_BACKUP_EXTENSION = ".jkmebackup"


class FinalV4BackupRestoreApplicationError(RuntimeError):
    """Small sanitized error vocabulary for the product projection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _verification_error_code(error: Exception) -> str:
    technical_code = str(getattr(error, "code", ""))
    if any(part in technical_code for part in ("installation", "context")):
        return "backup_context_mismatch"
    if any(part in technical_code for part in ("dmk", "key", "envelope")):
        return "backup_key_unavailable"
    return "backup_invalid"


@dataclass(frozen=True, slots=True)
class FinalV4RestoreApplicationResult:
    """Existing restore-preview shape plus the verified READY binding."""

    path: Path
    restore_id: str
    staging_root: Path
    container_sha256: str
    preview: RestorePreview
    compatibility: RestoreCompatibility

    @property
    def target_compatibility(self) -> RestoreCompatibility:
        return self.compatibility


class FinalV4EncryptedBackupApplicationService:
    """Translate the existing desktop backup command to one `.jkmebackup`."""

    def __init__(
        self,
        service: FinalV4EncryptedBackupService,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.service = service
        self._now = now_provider or (lambda: datetime.now(UTC))

    def create(self, command: CreateBackupCommand) -> FinalV4EncryptedBackupResult:
        target_directory = Path(command.target_path).expanduser().resolve(strict=True)
        timestamp = self._now().astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = (
            target_directory
            / f"Jenaplan-Kompetenzmanager-Backup-{timestamp}.jkmebackup"
        )
        try:
            return self.service.create(target)
        except Exception:
            raise FinalV4BackupRestoreApplicationError(
                "backup_create_failed"
            ) from None

    def verify(self, query: VerifyBackupQuery) -> FinalV4EncryptedBackupResult:
        if Path(query.path).suffix != FINAL_V4_ENCRYPTED_BACKUP_EXTENSION:
            raise FinalV4BackupRestoreApplicationError("backup_invalid")
        try:
            return self.service.verify(Path(query.path))
        except Exception as error:
            raise FinalV4BackupRestoreApplicationError(
                _verification_error_code(error)
            ) from None


class FinalV4EncryptedRestoreApplicationService:
    """Bind READY staging and the existing live worker to desktop commands."""

    def __init__(
        self,
        service: FinalV4EncryptedBackupService,
        *,
        lock: RuntimeInstanceLock,
        restore_id_provider: Callable[[], str] | None = None,
    ) -> None:
        self.service = service
        self.lock = lock
        self._restore_id = restore_id_provider or (lambda: str(uuid.uuid4()))
        self._sessions: dict[str, FinalV4RestoreApplicationResult] = {}
        self._preparations: dict[str, FinalV4LiveRestorePreparation] = {}

    def verify(
        self,
        query: VerifyRestoreBackupQuery,
    ) -> FinalV4RestoreApplicationResult:
        source = Path(query.path)
        if source.suffix != FINAL_V4_ENCRYPTED_BACKUP_EXTENSION:
            raise FinalV4BackupRestoreApplicationError("backup_invalid")
        try:
            verified = self.service.verify(source)
        except Exception as error:
            raise FinalV4BackupRestoreApplicationError(
                _verification_error_code(error)
            ) from None
        restore_id = self._restore_id()
        staging_parent = (
            self.service.paths.final_v4.key_runtime.root
            / "encrypted-restore-staging"
        )
        staging_parent.mkdir(mode=0o700, exist_ok=True)
        try:
            staged = self.service.restore_staging(
                source,
                staging_parent / restore_id,
            )
            ready = self.service.verify_restore_ready(
                staged.staging_root,
                expected_container_sha256=verified.container_sha256,
            )
            counts = self.service.restore_preview_counts(
                ready.staging_root,
                expected_container_sha256=verified.container_sha256,
            )
        except Exception:
            raise FinalV4BackupRestoreApplicationError(
                "restore_staging_failed"
            ) from None
        compatibility = RestoreCompatibility(
            status=DatabaseCompatibilityStatus.EXACT,
            database_compatibility_version=FINAL_SCHEMA_VERSION,
            sqlite_user_version=FINAL_SCHEMA_VERSION,
            schema_fingerprint=FINAL_SCHEMA_FINGERPRINT,
        )
        preview = RestorePreview(
            created_at=verified.manifest.created_at,
            app_version=verified.manifest.app_version,
            backup_format_version=verified.manifest.format_version,
            database_compatibility_version=FINAL_SCHEMA_VERSION,
            sqlite_user_version=FINAL_SCHEMA_VERSION,
            compatibility_status=DatabaseCompatibilityStatus.EXACT,
            students_count=counts.students,
            observations_count=counts.observations,
            learning_report_revisions_count=counts.learning_report_revisions,
            learning_conference_revisions_count=(
                counts.learning_conference_revisions
            ),
            managed_files_count=counts.managed_documents,
            external_references_count=0,
            external_missing_count=0,
        )
        result = FinalV4RestoreApplicationResult(
            path=source,
            restore_id=restore_id,
            staging_root=ready.staging_root,
            container_sha256=ready.container_sha256,
            preview=preview,
            compatibility=compatibility,
        )
        self._sessions[restore_id] = result
        return result

    def prepare_staging(
        self,
        command: PrepareRestoreStagingCommand,
    ) -> FinalV4RestoreApplicationResult:
        for session in self._sessions.values():
            if session.path == Path(command.path):
                return self._reverify(session)
        return self.verify(VerifyRestoreBackupQuery(Path(command.path)))

    def verify_prepared(
        self,
        query: VerifyPreparedRestoreQuery,
    ) -> FinalV4RestoreApplicationResult:
        try:
            session = self._sessions[query.restore_id]
        except KeyError:
            raise RuntimeError("cipher_restore_session_missing") from None
        return self._reverify(session)

    def create_handoff(
        self,
        command: CreateRestoreHandoffCommand,
    ) -> RestoreHandoffResult:
        try:
            session = self._sessions[command.restore_id]
        except KeyError:
            raise RuntimeError("cipher_restore_session_missing") from None
        session = self._reverify(session)
        try:
            preparation = prepare_final_v4_live_restore(
                backup_service=self.service,
                lock=self.lock,
                staging_root=session.staging_root,
                expected_container_sha256=session.container_sha256,
                restore_id=session.restore_id,
                app_version=command.app_version,
                build_commit=command.build_commit,
                source_tree_state=command.source_tree_state,
            )
        except Exception as error:
            technical_code = str(getattr(error, "code", ""))
            if "backup" in technical_code:
                code = "restore_safety_backup_failed"
            elif "ready" in technical_code or "staging" in technical_code:
                code = "restore_ready_invalid"
            else:
                code = "worker_handoff_failed"
            raise FinalV4BackupRestoreApplicationError(
                code
            ) from None
        self._preparations[session.restore_id] = preparation
        return preparation.handoff

    def launch_prepared_restore(
        self,
        handoff: RestoreHandoffResult,
    ):
        try:
            preparation = self._preparations.pop(handoff.restore_id)
        except KeyError:
            raise RuntimeError("cipher_restore_preparation_missing") from None
        try:
            return launch_prepared_final_v4_restore(
                preparation=preparation,
                lock=self.lock,
            )
        except Exception:
            raise FinalV4BackupRestoreApplicationError(
                "worker_takeover_failed"
            ) from None

    def _reverify(
        self,
        session: FinalV4RestoreApplicationResult,
    ) -> FinalV4RestoreApplicationResult:
        try:
            ready = self.service.verify_restore_ready(
                session.staging_root,
                expected_container_sha256=session.container_sha256,
            )
        except Exception:
            raise FinalV4BackupRestoreApplicationError(
                "restore_ready_invalid"
            ) from None
        if ready.container_sha256 != session.container_sha256:
            raise RuntimeError("cipher_restore_ready_mismatch")
        return session
