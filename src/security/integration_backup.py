"""Encrypted backup and restore staging for Security Sprint 11."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Callable, Mapping

from prototypes.encrypted_backup_container.sprint9_container import (
    BackupSourceFile,
    EncryptedBackupRestoreResult,
    EncryptedBackupVerificationResult,
    SyntheticEncryptedBackupServiceV1,
)
from prototypes.encrypted_document_container.sprint10_container import (
    EXPORTS_DIRECTORY,
    SOURCES_DIRECTORY,
    STORAGE_DIRECTORY,
    SYNTHETIC_DOCUMENT_EXPORT_MARKER,
    SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES,
    SYNTHETIC_DOCUMENT_STORAGE_MARKER,
    SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
    SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
    SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
    SyntheticEncryptedDocumentServiceV1,
)
from src.security.backup_container import (
    BackupContainerContextV1,
    BackupEntryRole,
    EncryptedBackupError,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.document_container import DocumentContainerContextV1

from .integration_database import (
    EncryptedDocumentGenerationRecord,
    SECURITY_INTEGRATION_APP_FORMAT_VERSION,
    SecurityIntegrationConnectionFactory,
    validate_security_integration_schema,
)
from .integration_gate import (
    SecurityIntegrationError,
    SecurityIntegrationPaths,
)


@dataclass(frozen=True)
class SecurityEncryptedRestoreResult:
    restore: EncryptedBackupRestoreResult
    database_verified: bool
    document_count: int
    document_test_root: Path


class SecurityEncryptedBackupAdapter:
    """Bridge validated Sprint-11 inventory to the Sprint-9 container."""

    def __init__(
        self,
        *,
        paths: SecurityIntegrationPaths,
        service: SyntheticEncryptedBackupServiceV1,
        document_service: SyntheticEncryptedDocumentServiceV1,
        database_factory: SecurityIntegrationConnectionFactory,
        dmk_loader: Callable[[], LoadedDataMasterKey],
        installation_id: str,
        database_context_id: str,
        migration_id: str,
        context: BackupContainerContextV1,
    ) -> None:
        self.paths = paths
        self.service = service
        self.document_service = document_service
        self.database_factory = database_factory
        self._dmk_loader = dmk_loader
        self.installation_id = installation_id
        self.database_context_id = database_context_id
        self.migration_id = migration_id
        self.context = context

    def create_or_verify(
        self,
        records: tuple[EncryptedDocumentGenerationRecord, ...],
    ) -> EncryptedBackupVerificationResult:
        database_source, document_sources, _expected = (
            self._backup_sources(records)
        )
        dmk = self._dmk_loader()
        if self.paths.encrypted_backup.exists():
            return self.service.verify(
                test_root=self.paths.root,
                container=self.paths.encrypted_backup,
                dmk=dmk,
                context=self.context,
            )
        database_key = self.database_factory.load_database_key()
        result = self.service.create(
            test_root=self.paths.root,
            target=self.paths.encrypted_backup,
            dmk=dmk,
            context=self.context,
            database_source=database_source,
            document_sources=document_sources,
            database_key=database_key.key_material,
        )
        confirmed = self.service.verify(
            test_root=self.paths.root,
            container=self.paths.encrypted_backup,
            dmk=dmk,
            context=self.context,
        )
        if confirmed != result:
            raise SecurityIntegrationError(
                "security_integration_backup_reverify_mismatch"
            )
        return confirmed

    def restore_verified(
        self,
        *,
        records: tuple[EncryptedDocumentGenerationRecord, ...],
        restore_name: str,
    ) -> SecurityEncryptedRestoreResult:
        database_source, _document_sources, expected = self._backup_sources(
            records
        )
        restore_root = self.paths.root / restore_name
        database_key = self.database_factory.load_database_key()
        restored = self.service.restore(
            test_root=self.paths.root,
            container=self.paths.encrypted_backup,
            restore_root=restore_root,
            dmk=self._dmk_loader(),
            context=self.context,
            database_key=database_key.key_material,
            expected_sources=expected,
        )
        self._validate_restored_database(
            restored.database_path,
            database_key.key_material,
        )
        document_test_root = restored.restore_root / "document-verification"
        _create_document_verification_layout(document_test_root)
        document_entries = {
            entry.entry_id: entry
            for entry in restored.verification.manifest.entries
            if entry.role is BackupEntryRole.MANAGED_DOCUMENT
        }
        if set(document_entries) != {record.storage_id for record in records}:
            raise SecurityIntegrationError(
                "security_integration_restore_document_inventory_invalid"
            )
        for record in records:
            entry = document_entries[record.storage_id]
            restored_path = restored.restore_root / entry.restore_name
            target = (
                document_test_root
                / STORAGE_DIRECTORY
                / record.container_name
            )
            _link_same_bytes(restored_path, target)
            self.document_service.verify(
                test_root=document_test_root,
                container=target,
                dmk=self._dmk_loader(),
                context=DocumentContainerContextV1(
                    installation_id=self.installation_id,
                    database_context_id=self.database_context_id,
                    document_id=record.document_id,
                    document_generation=record.document_generation,
                    app_format_version=SECURITY_INTEGRATION_APP_FORMAT_VERSION,
                ),
                expected_storage_id=record.storage_id,
            )
        return SecurityEncryptedRestoreResult(
            restore=restored,
            database_verified=True,
            document_count=len(records),
            document_test_root=document_test_root,
        )

    def _backup_sources(
        self,
        records: tuple[EncryptedDocumentGenerationRecord, ...],
    ) -> tuple[
        BackupSourceFile,
        tuple[BackupSourceFile, ...],
        Mapping[str, Path],
    ]:
        if not records:
            raise SecurityIntegrationError(
                "security_integration_backup_document_inventory_empty"
            )
        database_source = BackupSourceFile(
            path=self.paths.encrypted_database,
            entry_id=self.database_context_id,
            role=BackupEntryRole.SQLCIPHER_DATABASE,
        )
        document_sources: list[BackupSourceFile] = []
        expected: dict[str, Path] = {
            self.database_context_id: self.paths.encrypted_database
        }
        for record in sorted(records, key=lambda item: item.storage_id):
            source = self.paths.document_storage / record.container_name
            staging = self.paths.root / f"backup-{record.storage_id}.jkmedoc"
            _link_same_bytes(source, staging)
            document_sources.append(
                BackupSourceFile(
                    path=staging,
                    entry_id=record.storage_id,
                    role=BackupEntryRole.MANAGED_DOCUMENT,
                )
            )
            expected[record.storage_id] = staging
        return database_source, tuple(document_sources), expected

    def _validate_restored_database(
        self,
        path: Path,
        _key_material: bytes,
    ) -> None:
        factory = self.database_factory.scoped_to(
            path,
            validator=lambda connection: validate_security_integration_schema(
                connection,
                installation_id=self.installation_id,
                database_context_id=self.database_context_id,
                migration_id=self.migration_id,
            ),
        )
        connection = factory.open_existing()
        try:
            return None
        finally:
            connection.close()


def integration_backup_sqlcipher_guard(
    *,
    installation_id: str,
    database_context_id: str,
    migration_id: str,
) -> Callable[[object, BackupContainerContextV1], None]:
    def validate(
        connection: object,
        _context: BackupContainerContextV1,
    ) -> None:
        try:
            validate_security_integration_schema(
                connection,
                installation_id=installation_id,
                database_context_id=database_context_id,
                migration_id=migration_id,
            )
        except SecurityIntegrationError:
            raise EncryptedBackupError(
                "backup_sqlcipher_integration_guard_invalid"
            ) from None

    return validate


def _create_document_verification_layout(root: Path) -> None:
    try:
        root.mkdir(mode=0o700)
        os.chmod(root, 0o700)
        (root / SOURCES_DIRECTORY).mkdir(mode=0o700)
        storage = root / STORAGE_DIRECTORY
        storage.mkdir(mode=0o700)
        exports = root / EXPORTS_DIRECTORY
        exports.mkdir(mode=0o700)
        _write_exclusive(
            root / SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
            SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
        )
        _write_exclusive(
            storage / SYNTHETIC_DOCUMENT_STORAGE_MARKER,
            SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
        )
        _write_exclusive(
            exports / SYNTHETIC_DOCUMENT_EXPORT_MARKER,
            SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES,
        )
    except SecurityIntegrationError:
        raise
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_restore_document_layout_failed"
        ) from None


def _write_exclusive(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _link_same_bytes(source: Path, target: Path) -> None:
    if target.exists():
        if _file_sha256(source) != _file_sha256(target):
            raise SecurityIntegrationError(
                "security_integration_backup_staging_changed"
            )
        return
    if target.is_symlink():
        raise SecurityIntegrationError(
            "security_integration_backup_staging_invalid"
        )
    try:
        os.link(source, target, follow_symlinks=False)
    except FileExistsError:
        if _file_sha256(source) != _file_sha256(target):
            raise SecurityIntegrationError(
                "security_integration_backup_staging_changed"
            )
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_backup_staging_failed"
        ) from None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_backup_source_read_failed"
        ) from None
    return digest.hexdigest()
