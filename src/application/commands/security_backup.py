"""Adapter from the support-reset backup port to the existing backup service."""

from __future__ import annotations

from dataclasses import dataclass

from src.security.domain import SecurityBackupProof

from .backup import BackupApplicationService, CreateBackupCommand, VerifyBackupQuery


@dataclass(frozen=True)
class VerifiedSecurityBackupAdapter:
    """Create one normal .jkmbackup and verify the published bytes again."""

    service: BackupApplicationService
    command: CreateBackupCommand

    def create_and_verify(self) -> SecurityBackupProof:
        created = self.service.create(self.command)
        verified = self.service.verify(VerifyBackupQuery(created.path))
        if (
            verified.path != created.path
            or verified.archive_sha256 != created.verification.archive_sha256
        ):
            raise RuntimeError("security_backup_verification_mismatch")
        return SecurityBackupProof(
            path=str(verified.path),
            sha256=verified.archive_sha256,
        )
