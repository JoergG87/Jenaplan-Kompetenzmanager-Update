"""Encrypted backup and verified restore staging for the Final-V4 runtime.

The service accepts only an already opened Final-V4 cipher runtime and uses
the existing writer/maintenance gates.  Live replacement remains owned by the
restore worker; this module supplies its mandatory safety freeze and READY
verifier for gated tests and the activated same-installation product path.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import TYPE_CHECKING, Any, Callable, Mapping

if TYPE_CHECKING:
    from src.security.cipher_product_runtime import CipherProductPaths

from prototypes.encrypted_backup_container.sprint9_container import (
    ENCRYPTED_BACKUP_EXTENSION,
    SYNTHETIC_BACKUP_TEST_ROOT_MARKER,
    SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES,
    BackupSourceFile,
    EncryptedBackupExtractionResult,
    EncryptedBackupVerificationResult,
    SyntheticEncryptedBackupServiceV1,
)
from src.core.database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
)
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
    SQLCipherConnectionProvider,
)
from src.core.maintenance_gate import (
    MaintenanceCapability,
    MaintenanceGate,
    MaintenancePurpose,
    MaintenanceState,
)
from src.core.observation_uow import ObservationWriterLock
from src.security.backup_container import (
    BackupContainerContextV1,
    BackupEntryRole,
    EncryptedBackupError,
    canonical_json,
)
from src.security.data_keys import (
    DataKeysetRuntimePhase,
    DataKeysetStatus,
)
from src.security.database_key_runtime import (
    DatabaseKeyRuntimePaths,
    LoadedDatabaseKeyRuntime,
    build_database_key_runtime,
)
from src.security.database_keys import (
    DatabaseKeyEnvelopeService,
    DatabaseKeyEnvelopeStatus,
    derive_database_key_registry_auth_key,
)
from src.security.domain import validate_uuid4
from src.security.final_v3_document_runtime import (
    DOCUMENT_CONTAINER_EXTENSION,
    FINAL_V3_DOCUMENT_APPLICATION_ID,
    FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT,
    FINAL_V3_DOCUMENT_SCHEMA_VERSION,
    FinalV3DocumentConnectionFactory,
    FinalV3DocumentGeneration,
    FinalV3DocumentRuntime,
    FinalV3DocumentRuntimePaths,
    FinalV3DocumentSchemaV1,
    OpenedFinalV3DocumentRuntime,
    _initialize_container_layout,
)
from src.security.final_v4_sqlcipher_runtime import (
    FinalV4SQLCipherConnectionFactory,
    FinalV4SQLCipherRuntimeGate,
    FinalV4SQLCipherRuntimePaths,
    KeyedFinalV4CompatibilityInspector,
)
from src.security.infrastructure.data_keyset_repository import (
    SQLiteDataKeysetRepository,
)
from src.security.infrastructure.database_key_envelope_repository import (
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from src.version import APP_VERSION


FINAL_V4_ENCRYPTED_BACKUP_FORMAT_VERSION = 1
FINAL_V4_RESTORE_READY_VERSION = 1
FINAL_V4_BACKUP_MANIFEST_ENTRY_ID = "00000000-0000-4000-8000-000000000001"
FINAL_V4_COMPANION_ENTRY_ID = "00000000-0000-4000-8000-000000000002"
FINAL_V4_KEYSET_ENTRY_ID = "00000000-0000-4000-8000-000000000003"
FINAL_V4_ENVELOPE_REGISTRY_ENTRY_ID = "00000000-0000-4000-8000-000000000004"
FINAL_V4_BACKUP_MANIFEST_FILENAME = "final-v4-backup-manifest-v1.json"
FINAL_V4_RESTORE_READY_FILENAME = "RESTORE_READY"
MANAGED_DOCUMENT_REFERENCE_PREFIX = "managed-document:"
_WORKSPACE_PREFIX = ".jkmebackup-work-"
_VERIFY_PREFIX = ".jkmebackup-verify-"
_SHA256 = __import__("re").compile(r"\A[0-9a-f]{64}\Z")


class FinalV4EncryptedBackupError(RuntimeError):
    """Sanitized fail-closed error; messages are stable technical codes."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FinalV4BackupArtifactRole(StrEnum):
    MAIN_DATABASE = "final_v4_main_database"
    DOCUMENT_COMPANION = "document_companion_database"
    KEYSET_METADATA = "keyset_metadata"
    DATABASE_KEY_ENVELOPE_REGISTRY = "database_key_envelope_registry"


@dataclass(frozen=True, slots=True)
class FinalV4BackupArtifactV1:
    entry_id: str
    role: FinalV4BackupArtifactRole
    outer_restore_name: str
    size: int
    sha256: str
    application_id: int | None = None
    schema_version: int | None = None
    schema_fingerprint: str | None = None

    def to_payload(self) -> dict[str, object]:
        _validate_artifact(self)
        return {
            "application_id": self.application_id,
            "entry_id": self.entry_id,
            "outer_restore_name": self.outer_restore_name,
            "role": self.role.value,
            "schema_fingerprint": self.schema_fingerprint,
            "schema_version": self.schema_version,
            "sha256": self.sha256,
            "size": self.size,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "FinalV4BackupArtifactV1":
        required = {
            "application_id",
            "entry_id",
            "outer_restore_name",
            "role",
            "schema_fingerprint",
            "schema_version",
            "sha256",
            "size",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise FinalV4EncryptedBackupError("backup_manifest_artifact_invalid")
        try:
            value = cls(
                entry_id=payload["entry_id"],
                role=FinalV4BackupArtifactRole(payload["role"]),
                outer_restore_name=payload["outer_restore_name"],
                size=payload["size"],
                sha256=payload["sha256"],
                application_id=payload["application_id"],
                schema_version=payload["schema_version"],
                schema_fingerprint=payload["schema_fingerprint"],
            )
            _validate_artifact(value)
            return value
        except FinalV4EncryptedBackupError:
            raise
        except Exception:
            raise FinalV4EncryptedBackupError(
                "backup_manifest_artifact_invalid"
            ) from None


@dataclass(frozen=True, slots=True)
class FinalV4BackupDocumentV1:
    entry_id: str
    outer_restore_name: str
    document_id: str
    document_generation: int
    storage_id: str
    document_key_id: str
    document_key_generation: int
    envelope_revision: int
    lifecycle_status: str
    container_size: int
    container_sha256: str

    def to_payload(self) -> dict[str, object]:
        _validate_document(self)
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: object) -> "FinalV4BackupDocumentV1":
        required = set(cls.__dataclass_fields__)
        if not isinstance(payload, dict) or set(payload) != required:
            raise FinalV4EncryptedBackupError("backup_manifest_document_invalid")
        try:
            value = cls(**payload)
            _validate_document(value)
            return value
        except FinalV4EncryptedBackupError:
            raise
        except Exception:
            raise FinalV4EncryptedBackupError(
                "backup_manifest_document_invalid"
            ) from None


@dataclass(frozen=True, slots=True)
class FinalV4EncryptedBackupManifestV1:
    created_at: str
    installation_id: str
    database_context_id: str
    dmk_key_id: str
    dmk_generation: int
    database_key_id: str
    database_key_generation: int
    database_key_rewrap_revision: int
    app_version: str
    sqlcipher_binding_version: str
    sqlcipher_version: str
    sqlite_version: str
    artifacts: tuple[FinalV4BackupArtifactV1, ...]
    documents: tuple[FinalV4BackupDocumentV1, ...]
    active_document_ids: tuple[str, ...]
    format_version: int = FINAL_V4_ENCRYPTED_BACKUP_FORMAT_VERSION
    manifest_entry_id: str = FINAL_V4_BACKUP_MANIFEST_ENTRY_ID

    def to_payload(self) -> dict[str, object]:
        _validate_manifest(self)
        return {
            "active_document_ids": list(self.active_document_ids),
            "app_version": self.app_version,
            "artifacts": [item.to_payload() for item in self.artifacts],
            "created_at": self.created_at,
            "database_context_id": self.database_context_id,
            "database_key_generation": self.database_key_generation,
            "database_key_id": self.database_key_id,
            "database_key_rewrap_revision": self.database_key_rewrap_revision,
            "dmk_generation": self.dmk_generation,
            "dmk_key_id": self.dmk_key_id,
            "documents": [item.to_payload() for item in self.documents],
            "format_version": self.format_version,
            "installation_id": self.installation_id,
            "manifest_entry_id": self.manifest_entry_id,
            "sqlcipher_binding_version": self.sqlcipher_binding_version,
            "sqlcipher_version": self.sqlcipher_version,
            "sqlite_version": self.sqlite_version,
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_payload())

    @classmethod
    def from_bytes(cls, value: bytes) -> "FinalV4EncryptedBackupManifestV1":
        try:
            payload = json.loads(value.decode("ascii"))
        except Exception:
            raise FinalV4EncryptedBackupError("backup_manifest_format_invalid") from None
        required = {
            "active_document_ids",
            "app_version",
            "artifacts",
            "created_at",
            "database_context_id",
            "database_key_generation",
            "database_key_id",
            "database_key_rewrap_revision",
            "dmk_generation",
            "dmk_key_id",
            "documents",
            "format_version",
            "installation_id",
            "manifest_entry_id",
            "sqlcipher_binding_version",
            "sqlcipher_version",
            "sqlite_version",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise FinalV4EncryptedBackupError("backup_manifest_fields_invalid")
        try:
            manifest = cls(
                created_at=payload["created_at"],
                installation_id=payload["installation_id"],
                database_context_id=payload["database_context_id"],
                dmk_key_id=payload["dmk_key_id"],
                dmk_generation=payload["dmk_generation"],
                database_key_id=payload["database_key_id"],
                database_key_generation=payload["database_key_generation"],
                database_key_rewrap_revision=payload[
                    "database_key_rewrap_revision"
                ],
                app_version=payload["app_version"],
                sqlcipher_binding_version=payload["sqlcipher_binding_version"],
                sqlcipher_version=payload["sqlcipher_version"],
                sqlite_version=payload["sqlite_version"],
                artifacts=tuple(
                    FinalV4BackupArtifactV1.from_payload(item)
                    for item in payload["artifacts"]
                ),
                documents=tuple(
                    FinalV4BackupDocumentV1.from_payload(item)
                    for item in payload["documents"]
                ),
                active_document_ids=tuple(payload["active_document_ids"]),
                format_version=payload["format_version"],
                manifest_entry_id=payload["manifest_entry_id"],
            )
            _validate_manifest(manifest)
        except FinalV4EncryptedBackupError:
            raise
        except Exception:
            raise FinalV4EncryptedBackupError("backup_manifest_fields_invalid") from None
        if manifest.to_bytes() != value:
            raise FinalV4EncryptedBackupError("backup_manifest_not_canonical")
        return manifest


@dataclass(frozen=True, slots=True)
class FinalV4EncryptedBackupResult:
    path: Path
    container_size: int
    container_sha256: str
    manifest: FinalV4EncryptedBackupManifestV1 = field(repr=False)


@dataclass(frozen=True, slots=True)
class FinalV4RestoreStagingResult:
    staging_root: Path
    ready_path: Path
    container_sha256: str
    active_document_count: int
    total_document_generation_count: int
    state: str = "RESTORE_READY"


@dataclass(frozen=True, slots=True)
class FinalV4RestoreReadyVerification:
    staging_root: Path
    ready_path: Path
    container_sha256: str
    manifest: FinalV4EncryptedBackupManifestV1 = field(repr=False)
    paths: FinalV3DocumentRuntimePaths = field(repr=False)
    loaded_keys: LoadedDatabaseKeyRuntime = field(repr=False)


@dataclass(frozen=True, slots=True)
class FinalV4RestorePreviewCounts:
    students: int
    observations: int
    learning_report_revisions: int
    learning_conference_revisions: int
    managed_documents: int


@dataclass(slots=True)
class FinalV4EncryptedSafetyBackup:
    """Verified backup plus the in-process maintenance freeze it established."""

    result: FinalV4EncryptedBackupResult
    _gate: MaintenanceGate = field(repr=False)
    _capability: MaintenanceCapability = field(repr=False)
    _owner_id: str = field(repr=False)
    _transferred: bool = field(default=False, init=False, repr=False)
    _released: bool = field(default=False, init=False, repr=False)

    def transfer_to_worker(self) -> None:
        if self._released:
            raise FinalV4EncryptedBackupError("safety_backup_freeze_released")
        self._transferred = True

    def abort(self) -> None:
        if self._released:
            return
        if self._transferred:
            raise FinalV4EncryptedBackupError("safety_backup_freeze_transferred")
        self._gate.abort(self._capability, owner_id=self._owner_id)
        self._released = True


@dataclass(frozen=True, slots=True)
class _MaterializedStaging:
    root: Path
    manifest: FinalV4EncryptedBackupManifestV1
    paths: FinalV3DocumentRuntimePaths
    loaded_keys: LoadedDatabaseKeyRuntime = field(repr=False)


@dataclass(frozen=True, slots=True)
class _BoundFinalV4RuntimeScope:
    """Revalidate one already-derived Security-owned Final-V4 path set."""

    paths: FinalV4SQLCipherRuntimePaths

    def require_paths(self) -> FinalV4SQLCipherRuntimePaths:
        try:
            root = self.paths.key_runtime.root
            if root.is_symlink() or not root.is_dir():
                raise OSError("runtime root invalid")
            resolved = root.resolve(strict=True)
        except OSError:
            raise FinalV4EncryptedBackupError(
                "final_v4_backup_scope_invalid"
            ) from None
        expected = FinalV4SQLCipherRuntimePaths.for_key_runtime(
            DatabaseKeyRuntimePaths.for_root(resolved)
        )
        if expected != self.paths:
            raise FinalV4EncryptedBackupError("final_v4_backup_scope_invalid")
        return expected


class _StagedDocumentFactory:
    def __init__(
        self,
        provider: SQLCipherConnectionProvider,
        path: Path,
        database_key: bytes,
    ) -> None:
        self._provider = provider
        self._path = Path(path)
        self._key = database_key

    def connect(self, *, create: bool) -> Any:
        if create:
            raise FinalV4EncryptedBackupError("restore_staging_create_forbidden")
        return self._provider.connect(
            self._path, create=False, key_material=self._key
        )

    def connect_read_only(self) -> Any:
        return self._provider.connect_read_only(
            self._path, key_material=self._key
        )


class FinalV4EncryptedBackupService:
    """Create, verify and stage same-installation encrypted Final-V4 backups."""

    def __init__(
        self,
        *,
        opened_runtime: OpenedFinalV3DocumentRuntime | None,
        paths: FinalV3DocumentRuntimePaths,
        loaded_keys: LoadedDatabaseKeyRuntime,
        main_factory: FinalV4SQLCipherConnectionFactory,
        document_factory: FinalV3DocumentConnectionFactory,
        provider: SQLCipherConnectionProvider,
        maintenance_gate: MaintenanceGate,
        random_source: Any,
        clock: Any,
        installation_id: str | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        resolved_installation_id = (
            opened_runtime.installation_id
            if opened_runtime is not None
            else installation_id
        )
        if resolved_installation_id is None:
            raise FinalV4EncryptedBackupError("backup_installation_context_missing")
        if (
            opened_runtime is not None
            and opened_runtime.database_context_id != loaded_keys.database_context_id
        ):
            raise FinalV4EncryptedBackupError("backup_database_context_mismatch")
        self.opened = opened_runtime
        self.installation_id = resolved_installation_id
        self.paths = paths
        self.loaded = loaded_keys
        self._main_factory = main_factory
        self._document_factory = document_factory
        self._provider = provider
        self._gate = maintenance_gate
        self._random = random_source
        self._clock = clock
        self._fault_hook = fault_hook

    @property
    def context(self) -> BackupContainerContextV1:
        compatibility = None if self.opened is None else self.opened.final_v4.compatibility
        return BackupContainerContextV1(
            installation_id=self.installation_id,
            database_context_id=self.loaded.database_context_id,
            app_version=APP_VERSION,
            sqlite_version=(
                SQLCIPHER_4_17_SQLITE_VERSION
                if compatibility is None
                else compatibility.sqlite_version
            ),
            sqlcipher_version=(
                SQLCIPHER_4_17_ENGINE_VERSION
                if compatibility is None
                else compatibility.cipher_version
            ),
        )

    def create(self, target: Path) -> FinalV4EncryptedBackupResult:
        result = self._create(target, retain_maintenance=False)
        if not isinstance(result, FinalV4EncryptedBackupResult):
            raise FinalV4EncryptedBackupError("encrypted_backup_state_invalid")
        return result

    def create_during_maintenance(
        self,
        target: Path,
    ) -> FinalV4EncryptedBackupResult:
        """Create while the calling thread already owns the active gate.

        ``MaintenanceGate.begin_existing_maintenance_writer`` is the
        authorization proof for this exact thread.  This lets the school-year
        transition reuse its existing freeze without nesting another
        maintenance capability.
        """

        result = self._create(
            target,
            retain_maintenance=False,
            existing_maintenance=True,
        )
        if not isinstance(result, FinalV4EncryptedBackupResult):
            raise FinalV4EncryptedBackupError("encrypted_backup_state_invalid")
        return result

    def create_safety_backup(self, target: Path) -> FinalV4EncryptedSafetyBackup:
        """Create+verify a backup and keep normal writers blocked for handoff."""

        result = self._create(target, retain_maintenance=True)
        if not isinstance(result, FinalV4EncryptedSafetyBackup):
            raise FinalV4EncryptedBackupError("encrypted_backup_state_invalid")
        return result

    def _create(
        self,
        target: Path,
        *,
        retain_maintenance: bool,
        existing_maintenance: bool = False,
    ) -> FinalV4EncryptedBackupResult | FinalV4EncryptedSafetyBackup:
        if retain_maintenance and existing_maintenance:
            raise FinalV4EncryptedBackupError(
                "backup_maintenance_transfer_invalid"
            )
        destination = _validate_backup_target(target)
        workspace = _new_private_sibling(destination, _WORKSPACE_PREFIX)
        owner_id = f"encrypted-backup:{self._new_uuid()}"
        capability = None
        safe_release = False
        maintenance_transferred = False
        try:
            _write_exclusive(
                workspace / SYNTHETIC_BACKUP_TEST_ROOT_MARKER,
                SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES,
            )
            if existing_maintenance:
                writer_scope = self._gate.begin_existing_maintenance_writer()
            else:
                capability = self._gate.request_maintenance(
                    owner_id=owner_id,
                    purpose=MaintenancePurpose.BACKUP_RESTORE,
                )
                if not self._gate.activate(capability, owner_id=owner_id):
                    raise FinalV4EncryptedBackupError("backup_writers_active")
                safe_release = True
                writer_scope = self._gate.exclusive_writer(
                    capability,
                    owner_id=owner_id,
                    purpose=MaintenancePurpose.BACKUP_RESTORE,
                )
            lock_root = self.paths.final_v4.runtime_root / ".observation-staging"
            with writer_scope:
                with ObservationWriterLock(lock_root):
                    self._emit("before_snapshot")
                    self.opened.documents.validate_restart()
                    main_path = workspace / "main.snapshot.sqlcipher"
                    companion_path = workspace / "companion.snapshot.sqlcipher"
                    self._snapshot_database(
                        source=lambda: self._main_factory.connect(
                            self.paths.final_v4.database, create=False
                        ),
                        target=main_path,
                        boundary="during_main_database_snapshot",
                    )
                    main_report = self._inspect_main(main_path, self.loaded.database_key.key_material)
                    self._snapshot_database(
                        source=lambda: self._document_factory.connect(create=False),
                        target=companion_path,
                        boundary="during_companion_snapshot",
                    )
                    self._inspect_companion(
                        companion_path, self.loaded.database_key.key_material
                    )
                    self._emit("during_document_inventory")
                    records = self._document_records(
                        companion_path, self.loaded.database_key.key_material
                    )
                    active_ids = self._validate_crossbindings(
                        main_path,
                        companion_path,
                        self.loaded.database_key.key_material,
                    )
                    copied_documents = self._copy_document_inventory(
                        workspace, records
                    )
                    keyset_path = workspace / "keyset-metadata.sqlite"
                    registry_path = workspace / "database-key-envelope-registry.json"
                    SQLiteDataKeysetRepository(
                        self.paths.final_v4.key_runtime.keyset_metadata,
                        PlatformFilePermissionManager(),
                    ).create_snapshot(keyset_path)
                    _copy_regular_verified(
                        self.paths.final_v4.key_runtime.envelope_registry,
                        registry_path,
                    )
                    self._validate_key_metadata(
                        keyset_path,
                        registry_path,
                        expected=self.loaded,
                    )
                    database_key_rewrap_revision = (
                        self._database_key_rewrap_revision(
                            registry_path, expected=self.loaded
                        )
                    )
                    manifest = self._build_manifest(
                        main_path=main_path,
                        companion_path=companion_path,
                        keyset_path=keyset_path,
                        registry_path=registry_path,
                        records=records,
                        active_ids=active_ids,
                        copied_documents=copied_documents,
                        main_schema_fingerprint=main_report.schema_fingerprint,
                        database_key_rewrap_revision=(
                            database_key_rewrap_revision
                        ),
                    )
                    manifest_path = workspace / FINAL_V4_BACKUP_MANIFEST_FILENAME
                    _write_exclusive(manifest_path, manifest.to_bytes())
                    service = self._container_service()
                    workspace_container = workspace / "payload.jkmebackup"
                    verification = service.create(
                        test_root=workspace,
                        target=workspace_container,
                        dmk=self.loaded.dmk,
                        context=self.context,
                        database_source=BackupSourceFile(
                            main_path,
                            self.loaded.database_context_id,
                            BackupEntryRole.SQLCIPHER_DATABASE,
                        ),
                        document_sources=tuple(
                            BackupSourceFile(path, entry_id, BackupEntryRole.MANAGED_DOCUMENT)
                            for entry_id, path in self._outer_document_sources(
                                manifest,
                                companion_path=companion_path,
                                keyset_path=keyset_path,
                                registry_path=registry_path,
                                manifest_path=manifest_path,
                                copied_documents=copied_documents,
                            )
                        ),
                        database_key=self.loaded.database_key.key_material,
                    )
                    self._validate_outer_manifest(verification, manifest, manifest_path)
                    self._emit("after_verification_before_publication")
                    _publish_no_clobber(workspace_container, destination)
                    published = self.verify(destination)
                    if published.manifest != manifest:
                        raise FinalV4EncryptedBackupError(
                            "backup_published_manifest_mismatch"
                        )
                    self.opened.documents.validate_restart()
                    if retain_maintenance:
                        maintenance_transferred = True
                        return FinalV4EncryptedSafetyBackup(
                            result=published,
                            _gate=self._gate,
                            _capability=capability,
                            _owner_id=owner_id,
                        )
                    return published
        except (FinalV4EncryptedBackupError, EncryptedBackupError):
            raise
        except Exception:
            raise FinalV4EncryptedBackupError("encrypted_backup_failed") from None
        finally:
            if capability is not None and not maintenance_transferred:
                try:
                    if safe_release and self._gate.state is not MaintenanceState.RECOVERY_REQUIRED:
                        self._gate.abort(capability, owner_id=owner_id)
                    elif not safe_release and self._gate.state is MaintenanceState.MAINTENANCE_PENDING:
                        self._gate.abort(capability, owner_id=owner_id)
                except Exception:
                    self._gate.mark_recovery_required()
            _remove_owned_workspace(workspace, expected_parent=destination.parent)

    def verify(self, container: Path) -> FinalV4EncryptedBackupResult:
        path = _validate_existing_backup(container)
        verification = self._container_service().verify_path(
            container=path,
            dmk=self.loaded.dmk,
            context=self.context,
        )
        staging = path.parent / f"{_VERIFY_PREFIX}{self._new_uuid()}"
        try:
            extraction = self._container_service().extract_to_new_root(
                container=path,
                restore_root=staging,
                dmk=self.loaded.dmk,
                context=self.context,
            )
            materialized = self._materialize_and_validate(extraction)
            return FinalV4EncryptedBackupResult(
                path=path,
                container_size=verification.container_size,
                container_sha256=verification.container_sha256,
                manifest=materialized.manifest,
            )
        finally:
            _remove_owned_workspace(staging, expected_parent=path.parent)

    def restore_staging(
        self,
        container: Path,
        staging_root: Path,
    ) -> FinalV4RestoreStagingResult:
        path = _validate_existing_backup(container)
        destination = _validate_new_staging_target(staging_root)
        extraction = self._container_service().extract_to_new_root(
            container=path,
            restore_root=destination,
            dmk=self.loaded.dmk,
            context=self.context,
        )
        try:
            materialized = self._materialize_and_validate(extraction)
            self._emit("after_reopen_before_restore_ready")
            ready_path = destination / FINAL_V4_RESTORE_READY_FILENAME
            ready = canonical_json(
                {
                    "active_document_count": len(
                        materialized.manifest.active_document_ids
                    ),
                    "container_sha256": extraction.verification.container_sha256,
                    "database_context_id": materialized.manifest.database_context_id,
                    "database_schema_fingerprint": FINAL_SCHEMA_FINGERPRINT,
                    "database_schema_version": FINAL_SCHEMA_VERSION,
                    "installation_id": materialized.manifest.installation_id,
                    "manifest_sha256": hashlib.sha256(
                        materialized.manifest.to_bytes()
                    ).hexdigest(),
                    "ready_version": FINAL_V4_RESTORE_READY_VERSION,
                    "state": "RESTORE_READY",
                    "total_document_generation_count": len(
                        materialized.manifest.documents
                    ),
                }
            )
            _write_exclusive(ready_path, ready)
            _fsync_directory(destination)
            return FinalV4RestoreStagingResult(
                staging_root=destination,
                ready_path=ready_path,
                container_sha256=extraction.verification.container_sha256,
                active_document_count=len(materialized.manifest.active_document_ids),
                total_document_generation_count=len(materialized.manifest.documents),
            )
        except Exception:
            # The private staging root intentionally remains for diagnosis;
            # absence of RESTORE_READY makes it non-activatable.
            raise

    def verify_restore_ready(
        self,
        staging_root: Path,
        *,
        expected_container_sha256: str,
    ) -> FinalV4RestoreReadyVerification:
        """Re-open and fully verify an existing RESTORE_READY tree."""

        if not _SHA256.fullmatch(expected_container_sha256):
            raise FinalV4EncryptedBackupError("restore_ready_container_hash_invalid")
        try:
            root = Path(staging_root).expanduser().resolve(strict=True)
            metadata = root.lstat()
        except OSError:
            raise FinalV4EncryptedBackupError("restore_ready_root_invalid") from None
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise FinalV4EncryptedBackupError("restore_ready_root_invalid")
        ready_path = root / FINAL_V4_RESTORE_READY_FILENAME
        try:
            ready_bytes = _read_regular(ready_path)
            ready = json.loads(ready_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise FinalV4EncryptedBackupError("restore_ready_invalid") from None
        required = {
            "active_document_count",
            "container_sha256",
            "database_context_id",
            "database_schema_fingerprint",
            "database_schema_version",
            "installation_id",
            "manifest_sha256",
            "ready_version",
            "state",
            "total_document_generation_count",
        }
        if (
            not isinstance(ready, dict)
            or set(ready) != required
            or canonical_json(ready) != ready_bytes
            or ready.get("ready_version") != FINAL_V4_RESTORE_READY_VERSION
            or ready.get("state") != "RESTORE_READY"
            or ready.get("container_sha256") != expected_container_sha256
            or ready.get("database_schema_version") != FINAL_SCHEMA_VERSION
            or ready.get("database_schema_fingerprint")
            != FINAL_SCHEMA_FINGERPRINT
        ):
            raise FinalV4EncryptedBackupError("restore_ready_invalid")

        manifest_path = root / FINAL_V4_BACKUP_MANIFEST_FILENAME
        manifest = FinalV4EncryptedBackupManifestV1.from_bytes(
            _read_regular(manifest_path)
        )
        self._validate_context(manifest)
        if (
            ready.get("installation_id") != manifest.installation_id
            or ready.get("database_context_id") != manifest.database_context_id
            or ready.get("manifest_sha256")
            != hashlib.sha256(manifest.to_bytes()).hexdigest()
            or ready.get("active_document_count")
            != len(manifest.active_document_ids)
            or ready.get("total_document_generation_count")
            != len(manifest.documents)
        ):
            raise FinalV4EncryptedBackupError("restore_ready_crossbinding_invalid")

        materialized = self.verify_live_runtime(root, manifest=manifest)
        return FinalV4RestoreReadyVerification(
            staging_root=root,
            ready_path=ready_path,
            container_sha256=expected_container_sha256,
            manifest=manifest,
            paths=materialized.paths,
            loaded_keys=materialized.loaded_keys,
        )

    def restore_preview_counts(
        self,
        staging_root: Path,
        *,
        expected_container_sha256: str,
    ) -> FinalV4RestorePreviewCounts:
        """Project privacy-minimized counts from a freshly reverified READY tree."""

        ready = self.verify_restore_ready(
            staging_root,
            expected_container_sha256=expected_container_sha256,
        )
        connection = self._provider.connect_read_only(
            ready.paths.final_v4.database,
            key_material=ready.loaded_keys.database_key.key_material,
        )
        try:
            connection.execute("PRAGMA query_only = ON")
            table_counts = {
                table: int(
                    connection.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
                )
                for table in (
                    "students",
                    "observations",
                    "learning_report_revisions",
                    "learning_conference_revisions",
                )
            }
        except Exception:
            raise FinalV4EncryptedBackupError(
                "restore_preview_projection_failed"
            ) from None
        finally:
            connection.close()
        return FinalV4RestorePreviewCounts(
            students=table_counts["students"],
            observations=table_counts["observations"],
            learning_report_revisions=table_counts[
                "learning_report_revisions"
            ],
            learning_conference_revisions=table_counts[
                "learning_conference_revisions"
            ],
            managed_documents=len(ready.manifest.active_document_ids),
        )

    def verify_live_runtime(
        self,
        runtime_root: Path,
        *,
        manifest: FinalV4EncryptedBackupManifestV1,
        enforce_artifact_hashes: bool = True,
    ) -> _MaterializedStaging:
        """Keyed full-runtime verification used after swap and during restart."""

        try:
            root = Path(runtime_root).expanduser().resolve(strict=True)
            metadata = root.lstat()
        except OSError:
            raise FinalV4EncryptedBackupError("restore_runtime_root_invalid") from None
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise FinalV4EncryptedBackupError("restore_runtime_root_invalid")
        self._validate_context(manifest)
        key_paths = DatabaseKeyRuntimePaths.for_root(root)
        final_paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
        paths = FinalV3DocumentRuntimePaths.for_final_v4(final_paths)
        artifacts = {item.role: item for item in manifest.artifacts}
        actual_artifacts = {
            FinalV4BackupArtifactRole.MAIN_DATABASE: final_paths.database,
            FinalV4BackupArtifactRole.DOCUMENT_COMPANION: paths.database,
            FinalV4BackupArtifactRole.KEYSET_METADATA: key_paths.keyset_metadata,
            FinalV4BackupArtifactRole.DATABASE_KEY_ENVELOPE_REGISTRY:
                key_paths.envelope_registry,
        }
        if set(artifacts) != set(actual_artifacts):
            raise FinalV4EncryptedBackupError("restore_artifact_inventory_invalid")
        if enforce_artifact_hashes:
            for role, path in actual_artifacts.items():
                try:
                    size, digest = _file_size_sha256(path)
                except OSError:
                    raise FinalV4EncryptedBackupError(
                        "restore_artifact_changed"
                    ) from None
                artifact = artifacts[role]
                if size != artifact.size or digest != artifact.sha256:
                    raise FinalV4EncryptedBackupError("restore_artifact_changed")

        staged_loaded = self._validate_key_metadata(
            key_paths.keyset_metadata,
            key_paths.envelope_registry,
            expected=self.loaded,
        )
        if (
            self._database_key_rewrap_revision(
                key_paths.envelope_registry,
                expected=staged_loaded,
            )
            != manifest.database_key_rewrap_revision
        ):
            raise FinalV4EncryptedBackupError(
                "restore_database_key_envelope_revision_mismatch"
            )
        main_report = self._inspect_main(
            final_paths.database,
            staged_loaded.database_key.key_material,
        )
        if main_report.schema_fingerprint != FINAL_SCHEMA_FINGERPRINT:
            raise FinalV4EncryptedBackupError("restore_main_schema_mismatch")
        self._inspect_companion(
            paths.database,
            staged_loaded.database_key.key_material,
        )
        staged_runtime = FinalV3DocumentRuntime(
            paths=paths,
            factory=_StagedDocumentFactory(
                self._provider,
                paths.database,
                staged_loaded.database_key.key_material,
            ),
            loaded_keys=staged_loaded,
            installation_id=manifest.installation_id,
            source_root=None,
            random_source=self._random,
            clock=self._clock,
        )
        try:
            staged_runtime.validate_restart()
        except Exception:
            raise FinalV4EncryptedBackupError(
                "restore_document_runtime_invalid"
            ) from None
        observed_records = self._document_records(
            paths.database,
            staged_loaded.database_key.key_material,
        )
        if (
            tuple(_document_manifest(record) for record in observed_records)
            != manifest.documents
        ):
            raise FinalV4EncryptedBackupError("restore_document_manifest_mismatch")
        active_ids = self._validate_crossbindings(
            final_paths.database,
            paths.database,
            staged_loaded.database_key.key_material,
        )
        if active_ids != manifest.active_document_ids:
            raise FinalV4EncryptedBackupError("restore_active_inventory_mismatch")
        return _MaterializedStaging(root, manifest, paths, staged_loaded)

    def _materialize_and_validate(
        self, extraction: EncryptedBackupExtractionResult
    ) -> _MaterializedStaging:
        manifest_path = extraction.entry_paths.get(FINAL_V4_BACKUP_MANIFEST_ENTRY_ID)
        if manifest_path is None:
            raise FinalV4EncryptedBackupError("backup_manifest_entry_missing")
        manifest = FinalV4EncryptedBackupManifestV1.from_bytes(
            _read_regular(manifest_path)
        )
        self._validate_context(manifest)
        self._validate_outer_manifest(
            extraction.verification, manifest, manifest_path
        )
        artifact_by_role = {item.role: item for item in manifest.artifacts}
        root = extraction.restore_root
        key_paths = DatabaseKeyRuntimePaths.for_root(root)
        final_paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
        document_paths = FinalV3DocumentRuntimePaths.for_final_v4(final_paths)
        PlatformFilePermissionManager().prepare_directory(key_paths.metadata_root)
        PlatformFilePermissionManager().prepare_directory(final_paths.runtime_root)
        _initialize_container_layout(document_paths)

        moves = {
            artifact_by_role[FinalV4BackupArtifactRole.MAIN_DATABASE].entry_id:
                final_paths.database,
            artifact_by_role[FinalV4BackupArtifactRole.DOCUMENT_COMPANION].entry_id:
                document_paths.database,
            artifact_by_role[FinalV4BackupArtifactRole.KEYSET_METADATA].entry_id:
                key_paths.keyset_metadata,
            artifact_by_role[
                FinalV4BackupArtifactRole.DATABASE_KEY_ENVELOPE_REGISTRY
            ].entry_id: key_paths.envelope_registry,
            FINAL_V4_BACKUP_MANIFEST_ENTRY_ID:
                root / FINAL_V4_BACKUP_MANIFEST_FILENAME,
        }
        for document in manifest.documents:
            moves[document.entry_id] = document_paths.storage_root / (
                f"{document.storage_id}{DOCUMENT_CONTAINER_EXTENSION}"
            )
        if set(extraction.entry_paths) != set(moves):
            raise FinalV4EncryptedBackupError("backup_entry_inventory_mismatch")
        for entry_id, target in moves.items():
            _move_no_clobber(extraction.entry_paths[entry_id], target)
        _fsync_directory(root)

        staged_loaded = self._validate_key_metadata(
            key_paths.keyset_metadata,
            key_paths.envelope_registry,
            expected=self.loaded,
        )
        if (
            self._database_key_rewrap_revision(
                key_paths.envelope_registry,
                expected=staged_loaded,
            )
            != manifest.database_key_rewrap_revision
        ):
            raise FinalV4EncryptedBackupError(
                "restore_database_key_envelope_revision_mismatch"
            )
        main_report = self._inspect_main(
            final_paths.database, staged_loaded.database_key.key_material
        )
        if main_report.schema_fingerprint != FINAL_SCHEMA_FINGERPRINT:
            raise FinalV4EncryptedBackupError("restore_main_schema_mismatch")
        self._inspect_companion(
            document_paths.database, staged_loaded.database_key.key_material
        )
        staged_runtime = FinalV3DocumentRuntime(
            paths=document_paths,
            factory=_StagedDocumentFactory(
                self._provider,
                document_paths.database,
                staged_loaded.database_key.key_material,
            ),
            loaded_keys=staged_loaded,
            installation_id=manifest.installation_id,
            source_root=None,
            random_source=self._random,
            clock=self._clock,
        )
        staged_runtime.validate_restart()
        observed_records = self._document_records(
            document_paths.database, staged_loaded.database_key.key_material
        )
        if tuple(_document_manifest(record) for record in observed_records) != manifest.documents:
            raise FinalV4EncryptedBackupError("restore_document_manifest_mismatch")
        active_ids = self._validate_crossbindings(
            final_paths.database,
            document_paths.database,
            staged_loaded.database_key.key_material,
        )
        if active_ids != manifest.active_document_ids:
            raise FinalV4EncryptedBackupError("restore_active_inventory_mismatch")
        return _MaterializedStaging(
            root=root,
            manifest=manifest,
            paths=document_paths,
            loaded_keys=staged_loaded,
        )

    def _snapshot_database(
        self,
        *,
        source: Callable[[], Any],
        target: Path,
        boundary: str,
    ) -> None:
        self._emit(boundary)
        source_connection = target_connection = None
        try:
            source_connection = source()
            target_connection = self._provider.connect(
                target,
                create=True,
                key_material=self.loaded.database_key.key_material,
            )
            source_connection.backup(target_connection)
            target_connection.commit()
        except Exception:
            raise FinalV4EncryptedBackupError("sqlcipher_snapshot_failed") from None
        finally:
            if target_connection is not None:
                target_connection.close()
            if source_connection is not None:
                source_connection.close()
        os.chmod(target, 0o600)

    def _inspect_main(self, path: Path, database_key: bytes):
        try:
            with closing(
                self._provider.connect_read_only(path, key_material=database_key)
            ) as connection:
                return KeyedFinalV4CompatibilityInspector().inspect_connection(
                    connection
                )
        except Exception:
            raise FinalV4EncryptedBackupError("restore_main_database_invalid") from None

    def _inspect_companion(self, path: Path, database_key: bytes) -> None:
        try:
            with closing(
                self._provider.connect_read_only(path, key_material=database_key)
            ) as connection:
                FinalV3DocumentSchemaV1.validate(
                    connection,
                    installation_id=self.installation_id,
                    database_context_id=self.loaded.database_context_id,
                )
        except Exception:
            raise FinalV4EncryptedBackupError(
                "restore_companion_database_invalid"
            ) from None

    def _document_records(
        self, path: Path, database_key: bytes
    ) -> tuple[FinalV3DocumentGeneration, ...]:
        try:
            with closing(
                self._provider.connect_read_only(path, key_material=database_key)
            ) as connection:
                rows = connection.execute(
                    """
                    SELECT document_id, document_generation, storage_id,
                           document_key_id, document_key_generation,
                           envelope_revision, container_format,
                           container_format_version, plaintext_size,
                           plaintext_sha256, container_size, container_sha256,
                           mime_type, lifecycle_status, created_at
                    FROM final_v3_document_generations
                    ORDER BY document_id, document_generation
                    """
                ).fetchall()
            return tuple(FinalV3DocumentGeneration(*tuple(row)) for row in rows)
        except Exception:
            raise FinalV4EncryptedBackupError("document_inventory_invalid") from None

    def _validate_crossbindings(
        self, main_path: Path, companion_path: Path, database_key: bytes
    ) -> tuple[str, ...]:
        try:
            with closing(
                self._provider.connect_read_only(
                    main_path, key_material=database_key
                )
            ) as main:
                plaintext_documents = main.execute(
                    "SELECT document_id FROM documents WHERE file_path <> ''"
                ).fetchall()
                if plaintext_documents:
                    raise FinalV4EncryptedBackupError(
                        "unexpected_plaintext_document_reference"
                    )
                referenced = {
                    str(row[0])
                    for row in main.execute(
                        "SELECT document_id FROM documents WHERE active = 1"
                    ).fetchall()
                }
                for table in (
                    "learning_report_pdf_artifacts",
                    "learning_conference_pdf_artifacts",
                ):
                    for row in main.execute(
                        f"SELECT relative_file_path FROM {table}"
                    ).fetchall():
                        reference = str(row[0])
                        if not reference.startswith(MANAGED_DOCUMENT_REFERENCE_PREFIX):
                            raise FinalV4EncryptedBackupError(
                                "unexpected_plaintext_pdf_reference"
                            )
                        document_id = reference[len(MANAGED_DOCUMENT_REFERENCE_PREFIX):]
                        validate_uuid4(document_id)
                        referenced.add(document_id)
            with closing(
                self._provider.connect_read_only(
                    companion_path, key_material=database_key
                )
            ) as companion:
                active_rows = companion.execute(
                    """
                    SELECT document_id, COUNT(*)
                    FROM final_v3_document_generations
                    WHERE lifecycle_status = 'ACTIVE'
                    GROUP BY document_id ORDER BY document_id
                    """
                ).fetchall()
            if any(int(row[1]) != 1 for row in active_rows):
                raise FinalV4EncryptedBackupError("active_generation_cardinality_invalid")
            active = tuple(str(row[0]) for row in active_rows)
            if set(active) != referenced:
                raise FinalV4EncryptedBackupError("active_document_crossbinding_invalid")
            return tuple(sorted(active))
        except FinalV4EncryptedBackupError:
            raise
        except Exception:
            raise FinalV4EncryptedBackupError("document_crossbinding_invalid") from None

    def _copy_document_inventory(
        self,
        workspace: Path,
        records: tuple[FinalV3DocumentGeneration, ...],
    ) -> dict[str, Path]:
        copied: dict[str, Path] = {}
        for record in records:
            source = self.paths.storage_root / (
                f"{record.storage_id}{DOCUMENT_CONTAINER_EXTENSION}"
            )
            target = workspace / f"container-{record.storage_id}.jkmedoc"
            size, digest = _copy_regular_verified(source, target)
            if size != record.container_size or digest != record.container_sha256:
                raise FinalV4EncryptedBackupError("document_container_changed")
            copied[record.storage_id] = target
        return copied

    def _build_manifest(
        self,
        *,
        main_path: Path,
        companion_path: Path,
        keyset_path: Path,
        registry_path: Path,
        records: tuple[FinalV3DocumentGeneration, ...],
        active_ids: tuple[str, ...],
        copied_documents: Mapping[str, Path],
        main_schema_fingerprint: str,
        database_key_rewrap_revision: int,
    ) -> FinalV4EncryptedBackupManifestV1:
        artifacts = (
            _artifact(
                main_path,
                self.loaded.database_context_id,
                FinalV4BackupArtifactRole.MAIN_DATABASE,
                application_id=0,
                schema_version=FINAL_SCHEMA_VERSION,
                schema_fingerprint=main_schema_fingerprint,
            ),
            _artifact(
                companion_path,
                FINAL_V4_COMPANION_ENTRY_ID,
                FinalV4BackupArtifactRole.DOCUMENT_COMPANION,
                application_id=FINAL_V3_DOCUMENT_APPLICATION_ID,
                schema_version=FINAL_V3_DOCUMENT_SCHEMA_VERSION,
                schema_fingerprint=FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT,
            ),
            _artifact(
                keyset_path,
                FINAL_V4_KEYSET_ENTRY_ID,
                FinalV4BackupArtifactRole.KEYSET_METADATA,
            ),
            _artifact(
                registry_path,
                FINAL_V4_ENVELOPE_REGISTRY_ENTRY_ID,
                FinalV4BackupArtifactRole.DATABASE_KEY_ENVELOPE_REGISTRY,
            ),
        )
        documents = tuple(
            _document_manifest(record) for record in records
        )
        for document in documents:
            path = copied_documents[document.storage_id]
            size, digest = _file_size_sha256(path)
            if size != document.container_size or digest != document.container_sha256:
                raise FinalV4EncryptedBackupError("document_container_changed")
        return FinalV4EncryptedBackupManifestV1(
            created_at=_format_utc(self._clock.utc_now()),
            installation_id=self.installation_id,
            database_context_id=self.loaded.database_context_id,
            dmk_key_id=self.loaded.dmk_key_id,
            dmk_generation=self.loaded.dmk_generation,
            database_key_id=self.loaded.database_key_id,
            database_key_generation=self.loaded.database_key_generation,
            database_key_rewrap_revision=database_key_rewrap_revision,
            app_version=APP_VERSION,
            sqlcipher_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            sqlcipher_version=SQLCIPHER_4_17_ENGINE_VERSION,
            sqlite_version=SQLCIPHER_4_17_SQLITE_VERSION,
            artifacts=artifacts,
            documents=documents,
            active_document_ids=active_ids,
        )

    def _outer_document_sources(
        self,
        manifest: FinalV4EncryptedBackupManifestV1,
        *,
        companion_path: Path,
        keyset_path: Path,
        registry_path: Path,
        manifest_path: Path,
        copied_documents: Mapping[str, Path],
    ) -> tuple[tuple[str, Path], ...]:
        return (
            (FINAL_V4_COMPANION_ENTRY_ID, companion_path),
            (FINAL_V4_KEYSET_ENTRY_ID, keyset_path),
            (FINAL_V4_ENVELOPE_REGISTRY_ENTRY_ID, registry_path),
            (FINAL_V4_BACKUP_MANIFEST_ENTRY_ID, manifest_path),
            *( (item.entry_id, copied_documents[item.storage_id]) for item in manifest.documents ),
        )

    def _validate_outer_manifest(
        self,
        verification: EncryptedBackupVerificationResult,
        manifest: FinalV4EncryptedBackupManifestV1,
        manifest_path: Path,
    ) -> None:
        outer = {item.entry_id: item for item in verification.manifest.entries}
        expected = {
            artifact.entry_id: (artifact.size, artifact.sha256, artifact.outer_restore_name)
            for artifact in manifest.artifacts
        }
        expected.update(
            {
                document.entry_id: (
                    document.container_size,
                    document.container_sha256,
                    document.outer_restore_name,
                )
                for document in manifest.documents
            }
        )
        manifest_size, manifest_hash = _file_size_sha256(manifest_path)
        expected[FINAL_V4_BACKUP_MANIFEST_ENTRY_ID] = (
            manifest_size,
            manifest_hash,
            _outer_restore_name(FINAL_V4_BACKUP_MANIFEST_ENTRY_ID, False),
        )
        if set(outer) != set(expected):
            raise FinalV4EncryptedBackupError("backup_entry_inventory_mismatch")
        for entry_id, (size, digest, restore_name) in expected.items():
            entry = outer[entry_id]
            if (
                entry.plaintext_size != size
                or entry.sha256 != digest
                or entry.restore_name != restore_name
            ):
                raise FinalV4EncryptedBackupError("backup_entry_crossbinding_invalid")

    def _validate_context(self, manifest: FinalV4EncryptedBackupManifestV1) -> None:
        if (
            manifest.installation_id != self.installation_id
            or manifest.database_context_id != self.loaded.database_context_id
            or manifest.dmk_key_id != self.loaded.dmk_key_id
            or manifest.dmk_generation != self.loaded.dmk_generation
            or manifest.database_key_id != self.loaded.database_key_id
            or manifest.database_key_generation != self.loaded.database_key_generation
            or manifest.sqlcipher_binding_version != SQLCIPHER_4_17_BINDING_VERSION
            or manifest.sqlcipher_version != SQLCIPHER_4_17_ENGINE_VERSION
            or manifest.sqlite_version != SQLCIPHER_4_17_SQLITE_VERSION
        ):
            raise FinalV4EncryptedBackupError("backup_context_crossbinding_invalid")

    def _validate_key_metadata(
        self,
        keyset_path: Path,
        registry_path: Path,
        *,
        expected: LoadedDatabaseKeyRuntime,
    ) -> LoadedDatabaseKeyRuntime:
        try:
            permissions = PlatformFilePermissionManager()
            repository = SQLiteDataKeysetRepository(keyset_path, permissions)
            active = repository.active_data_keyset()
            if (
                active is None
                or repository.pending_data_keysets()
                or repository.data_keysets_for_cleanup()
                or active.status is not DataKeysetStatus.ACTIVE
                or active.runtime_phase is not DataKeysetRuntimePhase.ACTIVE
                or active.key_id != expected.dmk_key_id
                or active.generation != expected.dmk_generation
                or active.fingerprint_sha256 != expected.dmk_fingerprint_sha256
                or active.database_context_id != expected.database_context_id
            ):
                raise FinalV4EncryptedBackupError("backup_keyset_crossbinding_invalid")
            envelope_repository = FileDatabaseKeyEnvelopeRepository(
                registry_path, permissions
            )
            database_key = DatabaseKeyEnvelopeService(
                repository=envelope_repository,
                random_source=self._random,
                clock=self._clock,
            ).load_active(
                expected.dmk,
                expected_generation=expected.database_key_generation,
            )
            if (
                database_key.key_id != expected.database_key_id
                or hashlib.sha256(database_key.key_material).hexdigest()
                != expected.database_key_fingerprint_sha256
            ):
                raise FinalV4EncryptedBackupError(
                    "backup_database_key_crossbinding_invalid"
                )
            return LoadedDatabaseKeyRuntime(
                database_context_id=expected.database_context_id,
                dmk_key_id=expected.dmk_key_id,
                dmk_generation=expected.dmk_generation,
                dmk_fingerprint_sha256=expected.dmk_fingerprint_sha256,
                database_key_id=database_key.key_id,
                database_key_generation=database_key.generation,
                database_key_fingerprint_sha256=hashlib.sha256(
                    database_key.key_material
                ).hexdigest(),
                first_run=False,
                dmk=expected.dmk,
                database_key=database_key,
            )
        except FinalV4EncryptedBackupError:
            raise
        except Exception:
            raise FinalV4EncryptedBackupError("backup_key_metadata_invalid") from None

    @staticmethod
    def _database_key_rewrap_revision(
        registry_path: Path,
        *,
        expected: LoadedDatabaseKeyRuntime,
    ) -> int:
        try:
            repository = FileDatabaseKeyEnvelopeRepository(
                registry_path,
                PlatformFilePermissionManager(),
            )
            auth_key = derive_database_key_registry_auth_key(
                expected.dmk,
                database_context_id=expected.database_context_id,
            )
            matches = tuple(
                envelope
                for envelope in repository.load(auth_key)
                if envelope.lifecycle_status is DatabaseKeyEnvelopeStatus.ACTIVE
            )
            if len(matches) != 1:
                raise FinalV4EncryptedBackupError(
                    "backup_database_key_envelope_cardinality_invalid"
                )
            envelope = matches[0]
            if (
                envelope.key_id != expected.database_key_id
                or envelope.key_generation != expected.database_key_generation
                or envelope.wrapping_dmk_key_id != expected.dmk_key_id
                or envelope.wrapping_dmk_generation != expected.dmk_generation
                or envelope.database_context_id != expected.database_context_id
            ):
                raise FinalV4EncryptedBackupError(
                    "backup_database_key_envelope_crossbinding_invalid"
                )
            return envelope.rewrap_revision
        except FinalV4EncryptedBackupError:
            raise
        except Exception:
            raise FinalV4EncryptedBackupError(
                "backup_database_key_envelope_invalid"
            ) from None

    def _container_service(self) -> SyntheticEncryptedBackupServiceV1:
        return SyntheticEncryptedBackupServiceV1(
            random_source=self._random,
            clock=self._clock,
            sqlcipher_provider=self._provider,
            fault_injector=self._container_fault,
            sqlcipher_guard_validator=self._validate_outer_main_connection,
        )

    @staticmethod
    def _validate_outer_main_connection(
        connection: Any, _context: BackupContainerContextV1
    ) -> None:
        connection.execute("PRAGMA foreign_keys = ON")
        KeyedFinalV4CompatibilityInspector().inspect_connection(connection)

    def _container_fault(self, boundary: str) -> None:
        mapped = {
            "writer_after_header": "during_container_write",
            "writer_after_manifest": "during_container_write",
            "writer_before_final": "during_container_write",
            "writer_after_final": "during_container_write",
            "writer_after_file_fsync": "after_write_before_verification",
            "writer_after_preverify": "after_verification_before_publication",
            "restore_after_root_created": "during_restore_extraction",
            "restore_write:sqlcipher_database": "during_restore_extraction",
            "restore_write:managed_document": "during_restore_extraction",
            "restore_after_extraction_before_reopen": "after_extraction_before_reopen",
        }.get(boundary)
        if mapped is not None:
            self._emit(mapped)

    def _emit(self, boundary: str) -> None:
        if self._fault_hook is not None:
            self._fault_hook(boundary)

    def _new_uuid(self) -> str:
        value = self._random.uuid4()
        validate_uuid4(value)
        return value


def build_final_v4_encrypted_backup_service(
    *,
    opened_runtime: OpenedFinalV3DocumentRuntime,
    account_loader,
    environ: Mapping[str, str],
    key_store=None,
    random_source=None,
    clock=None,
    sqlcipher_provider: SQLCipherConnectionProvider | None = None,
    product_paths: CipherProductPaths | None = None,
    product_root: Path | None = None,
    loaded_keys: LoadedDatabaseKeyRuntime | None = None,
    fault_hook=None,
) -> FinalV4EncryptedBackupService:
    """Compose backup services from the gate or an injected product path port."""

    environment = dict(environ)
    runtime_scope = None
    if product_paths is not None and product_root is not None:
        raise FinalV4EncryptedBackupError("final_v4_backup_scope_ambiguous")
    if product_paths is None and product_root is None:
        gate = FinalV4SQLCipherRuntimeGate()
        decision = gate.resolve(environment)
        if decision.state.value != "ACTIVE":
            raise FinalV4EncryptedBackupError("final_v4_backup_gate_required")
        final_paths = gate.require_paths(
            environment.get("JKM_DMK_DATABASE_KEY_RUNTIME_ROOT", "")
        )
    elif product_paths is not None:
        from src.security.cipher_product_runtime import CipherProductRuntimeScope

        runtime_scope = CipherProductRuntimeScope(product_paths)
        final_paths = runtime_scope.require_paths()
    else:
        root = Path(product_root).expanduser().resolve(strict=True)
        final_paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(
            DatabaseKeyRuntimePaths.for_root(root)
        )
        runtime_scope = _BoundFinalV4RuntimeScope(final_paths)
    paths = FinalV3DocumentRuntimePaths.for_final_v4(final_paths)
    if opened_runtime.documents.paths != paths:
        raise FinalV4EncryptedBackupError("final_v4_backup_scope_invalid")
    for metadata_path in (
        final_paths.key_runtime.keyset_metadata,
        final_paths.key_runtime.envelope_registry,
    ):
        try:
            metadata_status = metadata_path.lstat()
        except OSError:
            raise FinalV4EncryptedBackupError(
                "final_v4_backup_key_runtime_incomplete"
            ) from None
        if stat.S_ISLNK(metadata_status.st_mode) or not stat.S_ISREG(
            metadata_status.st_mode
        ):
            raise FinalV4EncryptedBackupError(
                "final_v4_backup_key_runtime_incomplete"
            )
    random = random_source or SystemRandomSource()
    runtime_clock = clock or SystemClock()
    provider = sqlcipher_provider or SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
    )
    loaded = loaded_keys or build_database_key_runtime(
        final_paths.key_runtime,
        account_loader=account_loader,
        key_store=key_store,
        random_source=random,
        clock=runtime_clock,
    ).open_or_create()
    if loaded.first_run:
        raise FinalV4EncryptedBackupError("final_v4_backup_existing_keys_required")
    if (
        opened_runtime.final_v4.loaded_keys.database_context_id
        != loaded.database_context_id
        or opened_runtime.final_v4.loaded_keys.dmk_key_id != loaded.dmk_key_id
        or opened_runtime.final_v4.loaded_keys.dmk_generation
        != loaded.dmk_generation
        or opened_runtime.final_v4.loaded_keys.database_key_id
        != loaded.database_key_id
        or opened_runtime.final_v4.loaded_keys.database_key_generation
        != loaded.database_key_generation
        or opened_runtime.final_v4.loaded_keys.dmk_fingerprint_sha256
        != loaded.dmk_fingerprint_sha256
        or opened_runtime.final_v4.loaded_keys.database_key_fingerprint_sha256
        != loaded.database_key_fingerprint_sha256
    ):
        raise FinalV4EncryptedBackupError("final_v4_backup_key_binding_mismatch")
    return FinalV4EncryptedBackupService(
        opened_runtime=opened_runtime,
        paths=paths,
        loaded_keys=loaded,
        main_factory=FinalV4SQLCipherConnectionFactory(
            provider=provider,
            paths=final_paths,
            loaded_keys=loaded,
            environ=environment,
            scope=runtime_scope,
        ),
        document_factory=FinalV3DocumentConnectionFactory(
            provider=provider,
            paths=paths,
            loaded_keys=loaded,
            environ=environment,
            scope=runtime_scope,
        ),
        provider=provider,
        maintenance_gate=opened_runtime.final_v4.database.maintenance_gate,
        random_source=random,
        clock=runtime_clock,
        fault_hook=fault_hook,
    )


def build_final_v4_restore_verifier(
    *,
    runtime_root: Path,
    loaded_keys: LoadedDatabaseKeyRuntime,
    installation_id: str,
    product_paths: CipherProductPaths,
    sqlcipher_provider: SQLCipherConnectionProvider | None = None,
    random_source=None,
    clock=None,
) -> FinalV4EncryptedBackupService:
    """Build a read-only keyed verifier without opening a product runtime."""

    root = Path(runtime_root).expanduser().resolve(strict=True)
    from src.security.cipher_product_runtime import CipherProductRuntimeScope

    scope = CipherProductRuntimeScope(product_paths)
    key_paths = DatabaseKeyRuntimePaths.for_root(root)
    final_paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
    paths = FinalV3DocumentRuntimePaths.for_final_v4(final_paths)
    provider = sqlcipher_provider or SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
    )
    random = random_source or SystemRandomSource()
    runtime_clock = clock or SystemClock()
    return FinalV4EncryptedBackupService(
        opened_runtime=None,
        paths=paths,
        loaded_keys=loaded_keys,
        main_factory=FinalV4SQLCipherConnectionFactory(
            provider=provider,
            paths=final_paths,
            loaded_keys=loaded_keys,
            environ={},
            scope=scope,
        ),
        document_factory=FinalV3DocumentConnectionFactory(
            provider=provider,
            paths=paths,
            loaded_keys=loaded_keys,
            environ={},
            scope=scope,
        ),
        provider=provider,
        maintenance_gate=MaintenanceGate(),
        random_source=random,
        clock=runtime_clock,
        installation_id=installation_id,
    )


def _artifact(
    path: Path,
    entry_id: str,
    role: FinalV4BackupArtifactRole,
    *,
    application_id: int | None = None,
    schema_version: int | None = None,
    schema_fingerprint: str | None = None,
) -> FinalV4BackupArtifactV1:
    size, digest = _file_size_sha256(path)
    return FinalV4BackupArtifactV1(
        entry_id=entry_id,
        role=role,
        outer_restore_name=_outer_restore_name(
            entry_id, role is FinalV4BackupArtifactRole.MAIN_DATABASE
        ),
        size=size,
        sha256=digest,
        application_id=application_id,
        schema_version=schema_version,
        schema_fingerprint=schema_fingerprint,
    )


def _document_manifest(
    record: FinalV3DocumentGeneration,
) -> FinalV4BackupDocumentV1:
    return FinalV4BackupDocumentV1(
        entry_id=record.storage_id,
        outer_restore_name=_outer_restore_name(record.storage_id, False),
        document_id=record.document_id,
        document_generation=record.document_generation,
        storage_id=record.storage_id,
        document_key_id=record.document_key_id,
        document_key_generation=record.document_key_generation,
        envelope_revision=record.envelope_revision,
        lifecycle_status=record.lifecycle_status,
        container_size=record.container_size,
        container_sha256=record.container_sha256,
    )


def _outer_restore_name(entry_id: str, main: bool) -> str:
    return "database.sqlcipher" if main else f"document-{entry_id}.bin"


def _validate_manifest(manifest: FinalV4EncryptedBackupManifestV1) -> None:
    if manifest.format_version != FINAL_V4_ENCRYPTED_BACKUP_FORMAT_VERSION:
        raise FinalV4EncryptedBackupError("backup_manifest_version_unsupported")
    for value in (
        manifest.installation_id,
        manifest.database_context_id,
        manifest.dmk_key_id,
        manifest.database_key_id,
        manifest.manifest_entry_id,
    ):
        try:
            validate_uuid4(value)
        except Exception:
            raise FinalV4EncryptedBackupError("backup_manifest_identity_invalid") from None
    if manifest.manifest_entry_id != FINAL_V4_BACKUP_MANIFEST_ENTRY_ID:
        raise FinalV4EncryptedBackupError("backup_manifest_identity_invalid")
    if type(manifest.dmk_generation) is not int or manifest.dmk_generation < 1:
        raise FinalV4EncryptedBackupError("backup_manifest_generation_invalid")
    if (
        type(manifest.database_key_generation) is not int
        or manifest.database_key_generation < 1
    ):
        raise FinalV4EncryptedBackupError("backup_manifest_generation_invalid")
    if (
        type(manifest.database_key_rewrap_revision) is not int
        or manifest.database_key_rewrap_revision < 1
    ):
        raise FinalV4EncryptedBackupError("backup_manifest_generation_invalid")
    if not isinstance(manifest.created_at, str) or not manifest.created_at.endswith("Z"):
        raise FinalV4EncryptedBackupError("backup_manifest_created_at_invalid")
    expected_roles = tuple(FinalV4BackupArtifactRole)
    if tuple(item.role for item in manifest.artifacts) != expected_roles:
        raise FinalV4EncryptedBackupError("backup_manifest_artifact_roles_invalid")
    for item in manifest.artifacts:
        _validate_artifact(item)
    main_artifact = next(
        item
        for item in manifest.artifacts
        if item.role is FinalV4BackupArtifactRole.MAIN_DATABASE
    )
    if (
        main_artifact.application_id != 0
        or main_artifact.schema_version != FINAL_SCHEMA_VERSION
        or main_artifact.schema_fingerprint != FINAL_SCHEMA_FINGERPRINT
    ):
        raise FinalV4EncryptedBackupError(
            "backup_manifest_main_schema_incompatible"
        )
    if tuple(sorted(manifest.documents, key=lambda item: (item.document_id, item.document_generation))) != manifest.documents:
        raise FinalV4EncryptedBackupError("backup_manifest_document_order_invalid")
    for item in manifest.documents:
        _validate_document(item)
    ids = [item.entry_id for item in manifest.artifacts]
    ids.extend(item.entry_id for item in manifest.documents)
    ids.append(manifest.manifest_entry_id)
    if len(ids) != len(set(ids)):
        raise FinalV4EncryptedBackupError("backup_manifest_entry_duplicate")
    active = tuple(
        sorted(item.document_id for item in manifest.documents if item.lifecycle_status == "ACTIVE")
    )
    if manifest.active_document_ids != active or len(active) != len(set(active)):
        raise FinalV4EncryptedBackupError("backup_manifest_active_inventory_invalid")


def _validate_artifact(item: FinalV4BackupArtifactV1) -> None:
    try:
        validate_uuid4(item.entry_id)
    except Exception:
        raise FinalV4EncryptedBackupError("backup_manifest_artifact_invalid") from None
    if (
        not isinstance(item.outer_restore_name, str)
        or item.outer_restore_name != _outer_restore_name(
            item.entry_id,
            item.role is FinalV4BackupArtifactRole.MAIN_DATABASE,
        )
        or type(item.size) is not int
        or item.size < 1
        or not isinstance(item.sha256, str)
        or not _SHA256.fullmatch(item.sha256)
    ):
        raise FinalV4EncryptedBackupError("backup_manifest_artifact_invalid")
    database_role = item.role in {
        FinalV4BackupArtifactRole.MAIN_DATABASE,
        FinalV4BackupArtifactRole.DOCUMENT_COMPANION,
    }
    if database_role:
        if (
            type(item.application_id) is not int
            or type(item.schema_version) is not int
            or item.schema_version < 1
            or not isinstance(item.schema_fingerprint, str)
            or not _SHA256.fullmatch(item.schema_fingerprint)
        ):
            raise FinalV4EncryptedBackupError("backup_manifest_artifact_invalid")
    elif any(value is not None for value in (item.application_id, item.schema_version, item.schema_fingerprint)):
        raise FinalV4EncryptedBackupError("backup_manifest_artifact_invalid")


def _validate_document(item: FinalV4BackupDocumentV1) -> None:
    try:
        validate_uuid4(item.entry_id)
        validate_uuid4(item.storage_id)
        validate_uuid4(item.document_key_id)
    except Exception:
        raise FinalV4EncryptedBackupError("backup_manifest_document_invalid") from None
    if (
        item.entry_id != item.storage_id
        or item.outer_restore_name != _outer_restore_name(item.entry_id, False)
        or not isinstance(item.document_id, str)
        or not item.document_id
        or type(item.document_generation) is not int
        or item.document_generation < 1
        or type(item.document_key_generation) is not int
        or item.document_key_generation < 1
        or type(item.envelope_revision) is not int
        or item.envelope_revision < 1
        or item.lifecycle_status not in {"PREPARED", "ACTIVE", "RETAINED", "QUARANTINED"}
        or type(item.container_size) is not int
        or item.container_size < 1
        or not isinstance(item.container_sha256, str)
        or not _SHA256.fullmatch(item.container_sha256)
    ):
        raise FinalV4EncryptedBackupError("backup_manifest_document_invalid")


def _validate_backup_target(path: Path) -> Path:
    target = Path(path)
    if not target.is_absolute() or target.suffix != ENCRYPTED_BACKUP_EXTENSION:
        raise FinalV4EncryptedBackupError("backup_target_invalid")
    _validate_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise FinalV4EncryptedBackupError("backup_target_exists")
    return target


def _validate_existing_backup(path: Path) -> Path:
    target = Path(path)
    if not target.is_absolute() or target.suffix != ENCRYPTED_BACKUP_EXTENSION:
        raise FinalV4EncryptedBackupError("backup_path_invalid")
    try:
        status = target.lstat()
    except OSError:
        raise FinalV4EncryptedBackupError("backup_path_invalid") from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise FinalV4EncryptedBackupError("backup_path_invalid")
    return target


def _validate_new_staging_target(path: Path) -> Path:
    target = Path(path)
    if not target.is_absolute() or target.name in {"", ".", ".."}:
        raise FinalV4EncryptedBackupError("restore_staging_path_invalid")
    _validate_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise FinalV4EncryptedBackupError("restore_staging_exists")
    return target


def _validate_parent(path: Path) -> None:
    try:
        status = path.lstat()
    except OSError:
        raise FinalV4EncryptedBackupError("backup_parent_invalid") from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        raise FinalV4EncryptedBackupError("backup_parent_invalid")


def _new_private_sibling(target: Path, prefix: str) -> Path:
    try:
        value = Path(tempfile.mkdtemp(prefix=prefix, dir=target.parent))
        os.chmod(value, 0o700)
        return value
    except OSError:
        raise FinalV4EncryptedBackupError("backup_workspace_create_failed") from None


def _copy_regular_verified(source: Path, target: Path) -> tuple[int, str]:
    source_fd = target_fd = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        source_fd = os.open(source, flags)
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode):
            raise FinalV4EncryptedBackupError("backup_source_invalid")
        target_fd = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            _write_all(target_fd, chunk)
            digest.update(chunk)
            size += len(chunk)
        os.fsync(target_fd)
        after = os.fstat(source_fd)
        path_status = source.lstat()
        if (
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or (before.st_dev, before.st_ino) != (path_status.st_dev, path_status.st_ino)
            or size != before.st_size
        ):
            raise FinalV4EncryptedBackupError("backup_source_changed")
        return size, digest.hexdigest()
    except FinalV4EncryptedBackupError:
        raise
    except OSError:
        raise FinalV4EncryptedBackupError("backup_source_copy_failed") from None
    finally:
        if target_fd is not None:
            os.close(target_fd)
        if source_fd is not None:
            os.close(source_fd)


def _file_size_sha256(path: Path) -> tuple[int, str]:
    value = _read_regular(path)
    return len(value), hashlib.sha256(value).hexdigest()


def _read_regular(path: Path) -> bytes:
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        status = os.fstat(fd)
        if not stat.S_ISREG(status.st_mode):
            raise FinalV4EncryptedBackupError("backup_regular_file_required")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except FinalV4EncryptedBackupError:
        raise
    except OSError:
        raise FinalV4EncryptedBackupError("backup_regular_file_required") from None
    finally:
        if fd is not None:
            os.close(fd)


def _write_exclusive(path: Path, payload: bytes) -> None:
    fd = None
    try:
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        _write_all(fd, payload)
        os.fsync(fd)
    except OSError:
        raise FinalV4EncryptedBackupError("backup_file_write_failed") from None
    finally:
        if fd is not None:
            os.close(fd)


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError("short write")
        offset += written


def _publish_no_clobber(source: Path, target: Path) -> None:
    try:
        os.link(source, target, follow_symlinks=False)
    except FileExistsError:
        raise FinalV4EncryptedBackupError("backup_target_exists") from None
    except OSError:
        raise FinalV4EncryptedBackupError("backup_publish_failed") from None
    _fsync_directory(target.parent)


def _move_no_clobber(source: Path, target: Path) -> None:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise FinalV4EncryptedBackupError("restore_staging_target_exists")
    try:
        os.link(source, target, follow_symlinks=False)
        source.unlink()
        os.chmod(target, 0o600)
        _fsync_directory(target.parent)
    except OSError:
        raise FinalV4EncryptedBackupError("restore_staging_materialization_failed") from None


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_owned_workspace(path: Path, *, expected_parent: Path) -> None:
    if (
        path.parent != expected_parent
        or not path.name.startswith((_WORKSPACE_PREFIX, _VERIFY_PREFIX))
    ):
        return
    try:
        status = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        return
    if stat.S_ISDIR(status.st_mode) and not stat.S_ISLNK(status.st_mode):
        shutil.rmtree(path, ignore_errors=True)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
