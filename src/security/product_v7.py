"""Product strategies for the existing exact V7 transaction and runtime.

No key creation, implicit migration, alternative restore engine or schema.
"""
from contextlib import closing, contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
import hashlib
import hmac
import json
import os

from src.core.database_engine import SQLCipherConnectionProvider, SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.runtime_root_protection import require_product_runtime_root
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION, SchemaAdmission
from src.core.timetable_weeks_schema import PRODUCT_V7_SCHEMA_REGISTRY, PRODUCT_V7_SCHEMA_REGISTRATION
from src.core.maintenance_gate import MaintenanceGate
from src.core.schema_upgrade import UpgradeError
from src.security.database_key_runtime import DatabaseKeyRuntimePaths
from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths, KeyedFinalV4CompatibilityInspector
from src.security.final_v3_document_runtime import FinalV3DocumentRuntimePaths, FinalV3DocumentRuntime
from src.security.final_v4_backup_runtime import FinalV4EncryptedBackupService, FinalV4EncryptedBackupManifestV1, _StagedDocumentFactory, _fsync_directory, _file_size_sha256
from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService
from src.security.synthetic_v7_runtime import SyntheticV7Runtime, KeyedSyntheticV7CompatibilityInspector
from src.security.transactional_timetable_weeks_migration import SyntheticTimetableWeeksMigration
from src.security.existing_installation_keys import ExistingInstallationKeys, ExistingInstallationKeyStatus
from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from src.security.upgrade_startup import ProductStartupInventory, ProductUpgradeStartupGuard, UpgradeStartupBlocked

TARGET = PRODUCT_V7_SCHEMA_REGISTRATION.identity
SOURCE_DIRECTORY = "schema-upgrade-source/transaction-timetable-weeks-v1"
SOURCE_BACKUP = SOURCE_DIRECTORY + "/source.jkmebackup"
COMPLETION = SOURCE_DIRECTORY + "/completed.json"
_HISTORY = frozenset({"schema-upgrade-source", SOURCE_DIRECTORY, SOURCE_BACKUP, COMPLETION})


def require_product_v7_scope(root):
    root = Path(root)
    if not root.is_absolute() or root.resolve(strict=True) != root:
        raise UpgradeError("product_v7_root_invalid")
    require_product_runtime_root(root, first_run=False)
    from src.core.macos_test_package_profile import test_identity
    if test_identity() is not None:
        from src.security.internal_test_v6_composition import require_internal_test_v6_context
        require_internal_test_v6_context(root)
    return root


@dataclass(frozen=True, slots=True)
class ProductV7BackupManifest(FinalV4EncryptedBackupManifestV1):
    expected_main_schema_version: ClassVar[int] = TARGET.schema_version
    expected_main_schema_fingerprint: ClassVar[str] = TARGET.fingerprint
    expected_manifest_entry_id: ClassVar[str] = "00000000-0000-4000-8000-000000000107"
    manifest_entry_id: str = expected_manifest_entry_id


class ProductV4MigrationBackupService(FinalV4EncryptedBackupService):
    """Existing V4 backup algorithm with immutable pre-auth key metadata reads."""
    _checkpointed_metadata_reads = True
    def _validate_key_metadata(self, keyset_path, registry_path, *, expected):
        return super()._validate_key_metadata(keyset_path, registry_path,
            expected=expected, checkpointed_immutable_reads=True)


class ProductV7BackupService(SyntheticV7EncryptedBackupService):
    manifest_type = ProductV7BackupManifest
    manifest_filename = "product-v7-backup-manifest-v1.json"
    manifest_entry_id = ProductV7BackupManifest.expected_manifest_entry_id

    def require_synthetic(self):
        # Existing shared backup hooks call this scope port on every operation.
        root = require_product_v7_scope(self.paths.final_v4.root)
        expected = FinalV3DocumentRuntimePaths.for_final_v4(
            FinalV4SQLCipherRuntimePaths.for_key_runtime(DatabaseKeyRuntimePaths.for_root(root)))
        if self.paths != expected or self.loaded.first_run:
            raise UpgradeError("product_v7_existing_paths_required")
        provider = self._provider
        if (not isinstance(provider, SQLCipherConnectionProvider)
                or provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
                or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION):
            raise UpgradeError("product_v7_provider_invalid")


def product_schema_identity(service):
    with closing(service._provider.connect_read_only(service.paths.final_v4.database,
            key_material=service.loaded.database_key.key_material)) as connection:
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        for identity in (FINAL_V4_SCHEMA_REGISTRATION.identity, TARGET):
            if (result.version.sqlite_user_version == identity.schema_version
                    and result.schema_identity.fingerprint == identity.fingerprint):
                return identity
    raise UpgradeError("product_v7_unknown_schema")


class _ProductMainFactory:
    def __init__(self, provider, path, key, inspector):
        self.provider, self.path, self.key, self.inspector = provider, path, key, inspector

    def connect(self, path, *, create=False):
        if Path(path) != self.path or create:
            raise UpgradeError("product_v7_existing_main_required")
        connection = self.provider.connect(self.path, create=False, key_material=self.key)
        try:
            self.inspector().inspect_connection(connection)
            return connection
        except BaseException:
            connection.close()
            raise


def build_product_v7_service(root, *, authenticated_account=None, key_store=None,
        provider=None, loaded_keys=None, checkpointed_metadata_reads=False,
        v4_source=False):
    root = require_product_v7_scope(root)
    account = authenticated_account or ExistingStartupAccountRepository(
        root / "security/security.sqlite", None).load_bound_active_account()
    if loaded_keys is None:
        result = ExistingInstallationKeys(key_store=key_store,
            inventory=ProductStartupInventory()).load_existing(root, authenticated_account=account)
        if result.status is not ExistingInstallationKeyStatus.VALID or result.loaded is None:
            raise UpgradeError("product_v7_existing_keys_required")
        loaded_keys = result.loaded
    elif authenticated_account is None:
        raise UpgradeError("product_v7_authenticated_bootstrap_required")
    provider = provider or SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION)
    paths = FinalV3DocumentRuntimePaths.for_final_v4(
        FinalV4SQLCipherRuntimePaths.for_key_runtime(DatabaseKeyRuntimePaths.for_root(root)))
    documents_factory = _StagedDocumentFactory(provider, paths.database, loaded_keys.database_key.key_material)
    documents = FinalV3DocumentRuntime(paths=paths, factory=documents_factory,
        loaded_keys=loaded_keys, installation_id=account.installation_id, source_root=None,
        random_source=SystemRandomSource(), clock=SystemClock())
    opened = SimpleNamespace(documents=documents, installation_id=account.installation_id,
        database_context_id=loaded_keys.database_context_id, final_v4=SimpleNamespace(compatibility=None))
    kwargs = dict(opened_runtime=opened, paths=paths, loaded_keys=loaded_keys,
        main_factory=_ProductMainFactory(provider, paths.final_v4.database,
            loaded_keys.database_key.key_material,
            KeyedFinalV4CompatibilityInspector if v4_source else KeyedSyntheticV7CompatibilityInspector),
        document_factory=documents_factory, provider=provider, maintenance_gate=MaintenanceGate(),
        random_source=SystemRandomSource(), clock=SystemClock())
    if v4_source:
        return ProductV4MigrationBackupService(**kwargs)
    return ProductV7BackupService(checkpointed_metadata_reads=checkpointed_metadata_reads, **kwargs)


def _receipt_payload(service):
    loaded = service.loaded
    return dict(format="product-v4-v7-completed-v1", installation_id=service.installation_id,
        database_context_id=loaded.database_context_id, dmk_key_id=loaded.dmk_key_id,
        dmk_generation=loaded.dmk_generation, database_key_id=loaded.database_key_id,
        database_key_generation=loaded.database_key_generation,
        target_version=TARGET.schema_version, target_fingerprint=TARGET.fingerprint,
        source_sha256=_file_size_sha256(service.paths.final_v4.root / SOURCE_BACKUP)[1])


def _receipt_mac(service, payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    from src.security.database_keys import derive_domain_separated_key
    key = derive_domain_separated_key(service.loaded.dmk,
        purpose="jenaplan-kompetenzmanager/product-v4-v7-completed/v1",
        derivation_version=1, context={"installation_id": service.installation_id,
            "database_context_id": service.loaded.database_context_id})
    return hmac.new(key.key_material, raw, hashlib.sha256).hexdigest()


def verify_product_v7_completion(service):
    path = service.paths.final_v4.root / COMPLETION
    if path.is_symlink():
        raise UpgradeError("product_v7_completion_invalid")
    payload = json.loads(path.read_text("ascii"))
    mac = payload.pop("hmac_sha256", None)
    if (payload != _receipt_payload(service) or not isinstance(mac, str)
            or not hmac.compare_digest(mac, _receipt_mac(service, payload))):
        raise UpgradeError("product_v7_completion_invalid")


class ProductV7Runtime(SyntheticV7Runtime):
    extra_historical_sources = ((SOURCE_BACKUP, (FinalV4EncryptedBackupService,)),)
    extra_historical_paths = frozenset({SOURCE_DIRECTORY, SOURCE_BACKUP, COMPLETION})

    def _require_scope(self):
        PRODUCT_V7_SCHEMA_REGISTRY.require_admission(TARGET, SchemaAdmission.RUNTIME)
        self.service.require_synthetic()
        keys = self.service.paths.final_v4.key_runtime
        self.service._validate_key_metadata(keys.keyset_metadata, keys.envelope_registry, expected=self.service.loaded)

    def _verify_historical_sources(self):
        verify_product_v7_completion(self.service)
        # Reuse the independent encrypted extraction/inspection algorithm;
        # no V5/V6 product source paths are admitted by _preflight.
        super()._verify_historical_sources()

    def _classify_terminal_restore(self):
        from src.security.synthetic_v7_live_restore import classify_terminal_synthetic_v7_restore_artifacts
        return classify_terminal_synthetic_v7_restore_artifacts(self.service)

    def _preflight(self):
        inventory = ProductStartupInventory().inspect(self.root)
        if any(a.role == "upgrade_evidence" and a.relative_path not in _HISTORY for a in inventory.artifacts):
            raise UpgradeError("product_v7_foreign_upgrade_evidence")
        super()._preflight()


@contextmanager
def open_product_v7_runtime(service, *, lock):
    from src.security.cipher_product_runtime import OpenedCipherProductRuntime, _require_completed_fachlicher_first_run
    with ProductV7Runtime(service).open_existing(lock=lock) as opened:
        _require_completed_fachlicher_first_run(opened)
        loaded = service.loaded
        yield OpenedCipherProductRuntime(runtime=opened, first_run=False,
            installation_id=service.installation_id, database_context_id=loaded.database_context_id,
            dmk_key_id=loaded.dmk_key_id, dmk_generation=loaded.dmk_generation,
            dmk_fingerprint_sha256=loaded.dmk_fingerprint_sha256,
            database_key_id=loaded.database_key_id, database_key_generation=loaded.database_key_generation,
            database_key_fingerprint_sha256=loaded.database_key_fingerprint_sha256)


class ProductV7Migration(SyntheticTimetableWeeksMigration):
    def _require_synthetic(self):
        require_product_v7_scope(self.root)
        expected = FinalV3DocumentRuntimePaths.for_final_v4(
            FinalV4SQLCipherRuntimePaths.for_key_runtime(DatabaseKeyRuntimePaths.for_root(self.root)))
        if self.service.paths != expected or self.service.loaded.first_run:
            raise UpgradeError("product_v7_existing_paths_required")
        provider = self.service._provider
        if (not isinstance(provider, SQLCipherConnectionProvider)
                or provider.expected_binding_version != SQLCIPHER_4_17_BINDING_VERSION
                or provider.expected_engine_version != SQLCIPHER_4_17_ENGINE_VERSION):
            raise UpgradeError("product_v7_provider_invalid")

    def _require_upgrade(self):
        PRODUCT_V7_SCHEMA_REGISTRY.require_upgrade(FINAL_V4_SCHEMA_REGISTRATION.identity, TARGET)

    def _require_source_connection(self, connection):
        KeyedFinalV4CompatibilityInspector().inspect_connection(connection)
        from src.core.upgrade_validation import verify_timetable_source_references
        verify_timetable_source_references(connection)
        self.source_identity = FINAL_V4_SCHEMA_REGISTRATION.identity
        return self.source_identity

    def _require_inventory(self, inventory):
        if inventory.restore_evidence or inventory.upgrade_evidence:
            raise UpgradeError("transaction_existing_evidence")

    def _transaction_connection(self, drain):
        return drain.product_transaction_connection(self.main, lambda: self._connect(self.main))

    def complete(self):
        # A fresh maintenance process only: inspect_restart rechecks full
        # source/target content, companion and documents under the instance lock.
        from src.core.restore_runtime import RuntimeInstanceLock
        with RuntimeInstanceLock(self.root) as lock:
            inventory = ProductStartupInventory().inspect(self.root)
            if (inventory.status.value in {"unsafe", "unknown", "changed"}
                    or inventory.restore_evidence
                    or any(a.role == "upgrade_evidence" and a.relative_path not in _HISTORY - {COMPLETION}
                           for a in inventory.artifacts)):
                raise UpgradeError("product_v7_completion_inventory_invalid")
            if self.inspect_restart(lock=lock) != TARGET:
                raise UpgradeError("product_v7_target_not_committed")
            payload = _receipt_payload(self.service)
            payload["hmac_sha256"] = _receipt_mac(self.service, payload)
            path = self.root / COMPLETION
            with path.open("x", encoding="ascii") as output:
                path.chmod(0o600)
                json.dump(payload, output, sort_keys=True, separators=(",", ":"))
                output.flush(); os.fsync(output.fileno())
                if os.sys.platform == "darwin":
                    import fcntl
                    fcntl.fcntl(output.fileno(), fcntl.F_FULLFSYNC)
            _fsync_directory(path.parent)



class ProductV7StartupInventory(ProductStartupInventory):
    @staticmethod
    def _classify(root, scan):
        observed = ProductStartupInventory._classify(root, scan)
        upgrades = {a.relative_path for a in observed.artifacts if a.role == "upgrade_evidence"}
        if upgrades and upgrades <= _HISTORY and COMPLETION in upgrades:
            classified = ProductStartupInventory._classify(root,
                [(name, metadata) for name, metadata in scan if name not in upgrades])
            return replace(classified, artifacts=observed.artifacts)
        return observed


class ProductV7StartupGuard(ProductUpgradeStartupGuard):
    def __init__(self, lock, *, inventory=None, keys=None, service_factory=None):
        super().__init__(lock, inventory=inventory or ProductV7StartupInventory(), keys=keys)
        self.service_factory = service_factory or (lambda root: build_product_v7_service(root, checkpointed_metadata_reads=True))

    def evaluate(self, *, before=None):
        result = super().evaluate(before=before)
        current = self.inventory.inspect(self.lock.runtime_root)
        try:
            if not current.restore_evidence and any(a.role == "upgrade_evidence" for a in current.artifacts):
                service = self.service_factory(self.lock.runtime_root)
                verify_product_v7_completion(service)
                with ProductV7Runtime(service).open_existing(lock=self.lock):
                    pass
                if current != self.inventory.inspect(self.lock.runtime_root):
                    raise UpgradeError("product_v7_inventory_changed")
        except Exception as error:
            if isinstance(error, UpgradeStartupBlocked):
                raise
            raise UpgradeStartupBlocked("product_v7_startup_invalid") from None
        return result
