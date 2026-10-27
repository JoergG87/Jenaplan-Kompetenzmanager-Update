"""Sealed synthetic V6 desktop composition; no productive schema admission."""
from contextlib import closing, contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import os
import json
import sys

from src.core.database_engine import (SQLCipherConnectionProvider,
    SQLCIPHER_4_17_BINDING_VERSION, SQLCIPHER_4_17_ENGINE_VERSION)
from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.maintenance_gate import MaintenanceGate
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION
from src.core.runtime_root_protection import require_mutable_test_root
from src.security.database_key_runtime import DatabaseKeyRuntimePaths
from src.security.existing_installation_keys import ExistingInstallationKeys, ExistingInstallationKeyStatus
from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths
from src.security.final_v3_document_runtime import FinalV3DocumentRuntimePaths, FinalV3DocumentRuntime
from src.security.final_v4_backup_runtime import _StagedDocumentFactory
from src.security.synthetic_v6_backup_runtime import SyntheticV6EncryptedBackupService
from src.security.synthetic_v6_runtime import SyntheticV6Runtime, SyntheticV6RuntimeError
from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
from src.security.infrastructure.system import SystemRandomSource, SystemClock
from src.security.upgrade_startup import ProductStartupInventory, ProductUpgradeStartupGuard

_HISTORICAL = frozenset({"schema-upgrade-source",
    "schema-upgrade-source/transaction-v1", "schema-upgrade-source/transaction-v1/source.jkmebackup",
    "schema-upgrade-source/transaction-timetable-v1",
    "schema-upgrade-source/transaction-timetable-v1/source.jkmebackup",
    "schema-upgrade-source/transaction-timetable-weeks-v1",
    "schema-upgrade-source/transaction-timetable-weeks-v1/source.jkmebackup"})


def require_internal_test_v6_context(root):
    from src.core.macos_test_package_profile import test_identity, active_internal_test_smoke_root
    profile = test_identity()
    canonical = Path(root)
    if (profile is None or str(canonical) != profile.runtime_root
            or active_internal_test_smoke_root(os.environ, sys.argv[1:]) != canonical):
        raise SyntheticV6RuntimeError("synthetic_v6_sealed_context_required")
    require_mutable_test_root(canonical)
    return profile


class InternalTestStartupInventory(ProductStartupInventory):
    """Keep complete evidence; classify only exact retained source paths separately.

    This is no admission: the guard authenticates every retained source, and
    runtime admission subsequently requires the exact keyed V6 identity.
    """
    @staticmethod
    def _classify(root, scan):
        observed = ProductStartupInventory._classify(root, scan)
        upgrades = {a.relative_path for a in observed.artifacts if a.role == "upgrade_evidence"}
        if upgrades and upgrades <= _HISTORICAL:
            classified = ProductStartupInventory._classify(root,
                [(name, metadata) for name, metadata in scan if name not in upgrades])
            return replace(classified, artifacts=observed.artifacts)
        return observed

    def before_lock(self, root):
        require_internal_test_v6_context(root)
        return super().before_lock(root)


class InternalTestStartupGuard(ProductUpgradeStartupGuard):
    def __init__(self, lock, *, inventory=None):
        require_internal_test_v6_context(lock.runtime_root)
        super().__init__(lock, inventory=inventory or InternalTestStartupInventory())

    def evaluate(self, *, before=None):
        require_internal_test_v6_context(self.lock.runtime_root)
        result = super().evaluate(before=before)
        current = self.inventory.inspect(self.lock.runtime_root)
        if not current.restore_evidence and any(a.role == "upgrade_evidence" for a in current.artifacts):
            service = build_internal_test_v6_backup_service(self.lock.runtime_root)
            internal_test_runtime_type(service)(service)._verify_historical_sources()
            if current != self.inventory.inspect(self.lock.runtime_root):
                raise SyntheticV6RuntimeError("synthetic_v6_inventory_changed")
        return result


def build_internal_test_v6_backup_service(root, *, authenticated_account=None,
        key_store=None, provider=None, loaded_keys=None, checkpointed_metadata_reads=False, schema_identity=None):
    profile = require_internal_test_v6_context(root)
    root = Path(root)
    account = authenticated_account
    if account is None:
        account = ExistingStartupAccountRepository(root / "security/security.sqlite", None).load_bound_active_account()
    if account.installation_id != profile.installation_id:
        raise SyntheticV6RuntimeError("synthetic_v6_installation_mismatch")
    if loaded_keys is None:
        result = ExistingInstallationKeys(key_store=key_store,
            inventory=ProductStartupInventory()).load_existing(root, authenticated_account=account)
        if result.status is not ExistingInstallationKeyStatus.VALID or result.loaded is None:
            raise SyntheticV6RuntimeError("synthetic_v6_existing_keys_unavailable")
        loaded_keys = result.loaded
    elif authenticated_account is None:
        raise SyntheticV6RuntimeError("synthetic_v6_authenticated_bootstrap_required")
    provider = provider or SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION)
    paths = FinalV3DocumentRuntimePaths.for_final_v4(
        FinalV4SQLCipherRuntimePaths.for_key_runtime(DatabaseKeyRuntimePaths.for_root(root)))
    key = loaded_keys.database_key.key_material
    document_factory = _StagedDocumentFactory(provider, paths.database, key)
    documents = FinalV3DocumentRuntime(paths=paths, factory=document_factory,
        loaded_keys=loaded_keys, installation_id=account.installation_id, source_root=None,
        random_source=SystemRandomSource(), clock=SystemClock())
    opened = SimpleNamespace(documents=documents, installation_id=account.installation_id,
        database_context_id=loaded_keys.database_context_id,
        final_v4=SimpleNamespace(compatibility=None))
    identity = schema_identity
    if identity is None:
        probe = SimpleNamespace(_provider=provider, paths=paths, loaded=loaded_keys)
        identity = internal_test_schema_identity(probe)
    from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService
    from src.security.synthetic_v7_runtime import KeyedSyntheticV7CompatibilityInspector
    from src.security.synthetic_v6_runtime import KeyedSyntheticV6CompatibilityInspector
    is_v7 = identity == SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity
    service_type = SyntheticV7EncryptedBackupService if is_v7 else SyntheticV6EncryptedBackupService
    inspector_type = KeyedSyntheticV7CompatibilityInspector if is_v7 else KeyedSyntheticV6CompatibilityInspector
    return service_type(opened_runtime=opened, paths=paths,
        checkpointed_metadata_reads=checkpointed_metadata_reads,
        loaded_keys=loaded_keys, main_factory=_ExistingV6MainFactory(provider, paths.final_v4.database, key, inspector_type),
        document_factory=document_factory, provider=provider, maintenance_gate=MaintenanceGate(),
        random_source=SystemRandomSource(), clock=SystemClock())


def internal_test_schema_identity(service):
    """No exception fallback: a corrupt/foreign identity never selects V4."""
    with closing(service._provider.connect_read_only(service.paths.final_v4.database,
            key_material=service.loaded.database_key.key_material)) as connection:
        result = DatabaseCompatibilityInspector().inspect_connection(connection)
        for identity in (FINAL_V4_SCHEMA_REGISTRATION.identity,
                SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity, SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity):
            if (result.version.sqlite_user_version == identity.schema_version
                    and result.schema_identity.fingerprint == identity.fingerprint):
                return identity
    raise SyntheticV6RuntimeError("synthetic_v6_unknown_schema")


def preflight_internal_test_existing_runtime(root, *, lock):
    """Inspect existing sealed data before authentication can write metadata.

    Recovery has already completed under this lock. Load only the ordinary
    existing-only context. Nothing from
    this inspection is retained as post-authentication runtime admission.
    """
    profile = require_internal_test_v6_context(root)
    if lock.runtime_root != Path(root):
        raise SyntheticV6RuntimeError("synthetic_v6_lock_root_mismatch")
    ProductUpgradeStartupGuard(lock)._require_lock()
    service = build_internal_test_v6_backup_service(root, checkpointed_metadata_reads=True)
    if (service.paths.final_v4.root != Path(root)
            or service.installation_id != profile.installation_id):
        raise SyntheticV6RuntimeError("synthetic_v6_installation_mismatch")
    try:
        if internal_test_schema_identity(service) in (SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity, SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity):
            with internal_test_runtime_type(service)(service).open_existing(lock=lock):
                pass
    except Exception:
        raise SyntheticV6RuntimeError("synthetic_v6_full_inspection_failed") from None


@contextmanager
def open_internal_test_v6_runtime(service, *, lock):
    from src.security.cipher_product_runtime import OpenedCipherProductRuntime, _require_completed_fachlicher_first_run
    require_internal_test_v6_context(lock.runtime_root)
    with internal_test_runtime_type(service)(service).open_existing(lock=lock) as opened:
        _require_completed_fachlicher_first_run(opened)
        loaded = service.loaded
        yield OpenedCipherProductRuntime(runtime=opened, first_run=False,
            installation_id=service.installation_id, database_context_id=loaded.database_context_id,
            dmk_key_id=loaded.dmk_key_id, dmk_generation=loaded.dmk_generation,
            dmk_fingerprint_sha256=loaded.dmk_fingerprint_sha256,
            database_key_id=loaded.database_key_id, database_key_generation=loaded.database_key_generation,
            database_key_fingerprint_sha256=loaded.database_key_fingerprint_sha256)


class _ExistingV6MainFactory:
    def __init__(self, provider, path, key, inspector_type=None):
        self.provider, self.path, self.key = provider, path, key
        self.inspector_type = inspector_type

    def connect(self, path, *, create=False):
        from src.security.synthetic_v6_runtime import KeyedSyntheticV6CompatibilityInspector
        if Path(path) != self.path or create:
            raise SyntheticV6RuntimeError("synthetic_v6_existing_path_required")
        connection = self.provider.connect(self.path, create=False, key_material=self.key)
        try:
            (self.inspector_type or KeyedSyntheticV6CompatibilityInspector)().inspect_connection(connection)
            return connection
        except BaseException:
            connection.close()
            raise


def internal_test_restore_kind(root):
    """Unauthenticated routing only; the selected exact verifier grants admission.

    A foreign/mixed contract blocks, never falls back to the V4 verifier.
    """
    from src.core.restore_runtime import RestoreJournal, restore_transaction_paths
    from src.security.synthetic_v6_live_restore import SYNTHETIC_V6_LIVE_RESTORE_KIND
    from src.security.final_v4_live_restore import FINAL_V4_LIVE_RESTORE_KIND
    require_internal_test_v6_context(root)
    root = Path(root)
    kinds = set()
    for directory in (root / "restore-transactions", root / "restore-handoffs"):
        if not directory.exists():
            continue
        for child in directory.iterdir():
            if child.is_symlink():
                raise SyntheticV6RuntimeError("synthetic_v6_restore_evidence_invalid")
            if directory.name == "restore-transactions":
                state = RestoreJournal(restore_transaction_paths(root, child.name)).read()
            else:
                state = json.loads(child.read_text())
            kinds.add(state.get("restore_kind"))
    from src.security.synthetic_v7_live_restore import SYNTHETIC_V7_LIVE_RESTORE_KIND
    if not kinds:
        return None
    if len(kinds) == 1 and kinds <= {SYNTHETIC_V6_LIVE_RESTORE_KIND, SYNTHETIC_V7_LIVE_RESTORE_KIND, FINAL_V4_LIVE_RESTORE_KIND}:
        return next(iter(kinds))
    raise SyntheticV6RuntimeError("synthetic_v6_restore_contract_conflict")


def internal_test_restore_is_v6(root):
    from src.security.synthetic_v6_live_restore import SYNTHETIC_V6_LIVE_RESTORE_KIND
    return internal_test_restore_kind(root) == SYNTHETIC_V6_LIVE_RESTORE_KIND


def internal_test_runtime_type(service):
    from src.security.synthetic_v7_runtime import SyntheticV7Runtime
    return SyntheticV7Runtime if internal_test_schema_identity(service) == SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity else SyntheticV6Runtime
