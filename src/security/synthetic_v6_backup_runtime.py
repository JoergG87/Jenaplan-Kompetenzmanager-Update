"""Explicit synthetic-only V6 backup contract; productive V4 remains exact."""
from contextlib import contextmanager
from dataclasses import dataclass
from typing import ClassVar
from pathlib import Path
import hashlib

from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
from src.core.runtime_root_protection import require_mutable_test_root, RuntimeRootKind
from src.core.database_engine import (SQLCipherConnectionProvider,
    SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION)
from src.security.database_key_runtime import DatabaseKeyRuntimePaths
from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths
from src.security.final_v3_document_runtime import FinalV3DocumentRuntimePaths
from src.security.final_v4_backup_runtime import (
    FinalV4EncryptedBackupManifestV1, FinalV4EncryptedBackupService,
    FinalV4EncryptedBackupError,
)

SYNTHETIC_V6_BACKUP_MANIFEST_ENTRY_ID = "00000000-0000-4000-8000-000000000006"
SYNTHETIC_V6_BACKUP_MANIFEST_FILENAME = "synthetic-v6-backup-manifest-v1.json"
SYNTHETIC_V6_RESTORE_READY_VERSION = 3
_TARGET = SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity


@dataclass(frozen=True, slots=True)
class SyntheticV6EncryptedBackupManifestV1(FinalV4EncryptedBackupManifestV1):
    """Container v1 with a separate, exact V6 inner manifest identity."""
    expected_main_schema_version: ClassVar[int] = _TARGET.schema_version
    expected_main_schema_fingerprint: ClassVar[str] = _TARGET.fingerprint
    expected_manifest_entry_id: ClassVar[str] = SYNTHETIC_V6_BACKUP_MANIFEST_ENTRY_ID
    manifest_entry_id: str = SYNTHETIC_V6_BACKUP_MANIFEST_ENTRY_ID


class SyntheticV6EncryptedBackupService(FinalV4EncryptedBackupService):
    """Reuse authenticated snapshots/staging only inside a synthetic test root.

    Loaded keys are mandatory and never created here. Historic V4/V5 sources
    require their independent exact services; they cannot produce V6
    READY or authorize replacement of V6 live state.
    """
    manifest_type = SyntheticV6EncryptedBackupManifestV1
    manifest_filename = SYNTHETIC_V6_BACKUP_MANIFEST_FILENAME
    manifest_entry_id = SYNTHETIC_V6_BACKUP_MANIFEST_ENTRY_ID
    main_schema_version = _TARGET.schema_version
    main_schema_fingerprint = _TARGET.fingerprint
    restore_ready_version = SYNTHETIC_V6_RESTORE_READY_VERSION

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.require_synthetic()
        if (hashlib.sha256(self.loaded.database_key.key_material).hexdigest()
                != self.loaded.database_key_fingerprint_sha256
                or hashlib.sha256(self.loaded.dmk.key_material).hexdigest()
                != self.loaded.dmk_fingerprint_sha256):
            raise FinalV4EncryptedBackupError("synthetic_v6_loaded_key_binding_invalid")
        if self.loaded.first_run:
            raise FinalV4EncryptedBackupError("synthetic_v6_existing_keys_required")
        provider = self._provider
        if (not isinstance(provider, SQLCipherConnectionProvider)
                or provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
                or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION):
            raise FinalV4EncryptedBackupError("synthetic_v6_provider_invalid")

    def require_synthetic(self):
        root = Path(self.paths.final_v4.key_runtime.root)
        if not root.is_absolute() or root.resolve() != root:
            raise FinalV4EncryptedBackupError("synthetic_v6_root_required")
        protection = require_mutable_test_root(root)
        if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
            raise FinalV4EncryptedBackupError("synthetic_v6_root_required")

        expected_main = FinalV4SQLCipherRuntimePaths.for_key_runtime(DatabaseKeyRuntimePaths.for_root(root))
        expected_paths = FinalV3DocumentRuntimePaths.for_final_v4(expected_main)
        if self.paths != expected_paths:
            raise FinalV4EncryptedBackupError("synthetic_v6_paths_invalid")
        provider = self._provider
        if (not isinstance(provider, SQLCipherConnectionProvider)
                or provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
                or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION):
            raise FinalV4EncryptedBackupError("synthetic_v6_provider_invalid")
        if self.loaded.first_run:
            raise FinalV4EncryptedBackupError("synthetic_v6_existing_keys_required")

    def _create(self, *args, **kwargs):
        self.require_synthetic()
        keys = self.paths.final_v4.key_runtime
        self._validate_key_metadata(keys.keyset_metadata, keys.envelope_registry, expected=self.loaded)
        return super()._create(*args, **kwargs)

    @contextmanager
    def verified_snapshot(self, *args, **kwargs):
        self.require_synthetic()
        with super().verified_snapshot(*args, **kwargs) as result:
            yield result

    def restore_staging(self, *args, **kwargs):
        self.require_synthetic()
        return super().restore_staging(*args, **kwargs)

    def verify_restore_ready(self, *args, **kwargs):
        self.require_synthetic()
        return super().verify_restore_ready(*args, **kwargs)

    def verify_live_runtime(self, *args, **kwargs):
        self.require_synthetic()
        return super().verify_live_runtime(*args, **kwargs)

    def read_manifest(self, *args, **kwargs):
        self.require_synthetic()
        return super().read_manifest(*args, **kwargs)

    def _inspect_main_connection(self, connection):
        from src.security.synthetic_v6_runtime import KeyedSyntheticV6CompatibilityInspector
        self.require_synthetic()
        return KeyedSyntheticV6CompatibilityInspector().inspect_connection(connection)

    def _validate_outer_main_connection(self, connection, context):
        connection.row_factory = self._provider._load_driver().Row
        return super()._validate_outer_main_connection(connection, context)

    def _validate_context(self, manifest):
        self.require_synthetic()
        return super()._validate_context(manifest)
