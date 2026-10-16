"""Read-only product startup veto under an already held runtime process lock.

This adapter has no maintenance/writer capability and cannot activate anything.
Synthetic preparation repositories/leases are deliberately not instantiated.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import stat

from src.core.installation_inventory import InstallationInventory, InstallationInventoryStatus as Status
from src.core.restore_runtime import RuntimeInstanceLock, _process_start_identity
from src.core.runtime_root_protection import (
    RUNTIME_ROOT_PROTECTION_MARKER, RuntimeRootKind, RuntimeRootLifecycle,
    inspect_runtime_root,
)
from src.core.schema_registry import PRODUCT_SCHEMA_REGISTRY
from src.core.schema_upgrade import UpgradeRecoveryStatus, UpgradeStartupDecision, validate_upgrade_state
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.existing_installation_keys import (
    ExistingInstallationKeys, ExistingInstallationKeyStatus,
)
from src.security.infrastructure.installation_inventory import ReadOnlyInstallationInventory
from src.security.infrastructure.migration_journal_repository import AuthenticatedMigrationJournalRepository
from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
from src.security.infrastructure.upgrade_journal_repository import UpgradeJournalCodec
from src.security.infrastructure.upgrade_replay_anchor import UpgradeReplayCodec


class UpgradeStartupBlocked(RuntimeError):
    """Only fixed diagnostic codes escape this boundary, never exception payloads."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ProductStartupInventory(ReadOnlyInstallationInventory):
    """Keep A1 private checks; allow existing non-secret logs/exports/backups modes.

The product creates ancillary directories with the normal umask (often 0755).
Their complete opaque inventory is still included in change/conflict checks.
No group/world write or foreign owner is accepted, even for ancillary entries.
"""
    @staticmethod
    def _safe(value, *, directory):
        required = stat.S_ISDIR if directory else stat.S_ISREG
        if (not required(value.st_mode) or value.st_uid != os.getuid()
                or value.st_mode & 0o022 or not value.st_mode & stat.S_IRUSR
                or directory and not value.st_mode & stat.S_IXUSR
                or not directory and value.st_nlink != 1):
            raise ValueError("inventory_entry_unsafe")

    def inspect(self, root):
        result = super().inspect(root)
        try:
            for item in result.artifacts:
                if item.role != "ancillary_unverified":
                    # stat_result indices differ from the deliberately explicit DTO.
                    mode, uid, links = item.metadata[2], item.metadata[3], item.metadata[5]
                    if uid != os.getuid() or mode & 0o077 or (stat.S_ISREG(mode) and links != 1):
                        raise ValueError
        except ValueError:
            return replace(result, status=Status.UNSAFE, reason="inventory_entry_unsafe")
        if (result.status not in {Status.UNSAFE, Status.CHANGED, Status.UNKNOWN}
                and any(a.role.startswith("operation_") for a in result.artifacts)):
            from src.application.retained_operation_startup import (
                inspect_retained_operation_journals, RetainedOperationStartupError,
            )
            try:
                inspect_retained_operation_journals(root)
            except RetainedOperationStartupError as error:
                return replace(result, status=Status.UNKNOWN, reason=error.code)
            if result != super().inspect(root):
                return replace(result, status=Status.CHANGED, reason="inventory_changed")
        return result

    def before_lock(self, root):
        """Classify absence without allowing the lock to create through aliases."""
        root = Path(root)
        if not root.is_absolute() or root.resolve(strict=False) != root:
            raise UpgradeStartupBlocked("upgrade_root_path_unsafe")
        if root.exists() or root.is_symlink():
            result = self.inspect(root)
        else:
            for parent in root.parents:
                if not parent.exists():
                    continue
                value = parent.lstat()
                if (not stat.S_ISDIR(value.st_mode) or value.st_uid not in {0, os.getuid()}
                        or value.st_mode & 0o022 and not value.st_mode & stat.S_ISVTX):
                    raise UpgradeStartupBlocked("upgrade_root_parent_unsafe")
            result = InstallationInventory(root, Status.EMPTY)
        if result.status in {Status.UNSAFE, Status.CHANGED, Status.UNKNOWN}:
            raise UpgradeStartupBlocked("upgrade_installation_unclear")
        return result


class ReadOnlyUpgradeEvidence:
    """Reuse exact historical codecs and descriptor reads, expose no write port."""
    def __init__(self, guard):
        self.guard = guard
        self.root = guard.lock.runtime_root

    def load(self, loaded, installation_id):
        self.guard._require_lock()
        journal_path = self.root / "schema-upgrade-foundation" / "journal.json"
        anchor_path = self.root / "schema-upgrade-replay" / "anchor.json"
        for path in (journal_path, anchor_path):
            if set(path.parent.iterdir()) != {path}:
                raise UpgradeStartupBlocked("upgrade_evidence_incomplete")
        # The untrusted operation UUID is used only as KDF selector. No context or
        # phase is accepted until the exact original bytes authenticate below.
        raw = AuthenticatedMigrationJournalRepository(journal_path, None)._read_regular_bytes()
        operation_id = json.loads(raw.decode("ascii"))["state"]["context"]["operation_id"]
        key = derive_migration_journal_auth_key(loaded.dmk, migration_id=operation_id)
        state = UpgradeJournalCodec._decode(raw, key)
        anchor_raw = AuthenticatedMigrationJournalRepository(anchor_path, None)._read_regular_bytes()
        anchor = UpgradeReplayCodec._decode(anchor_raw, key)
        if anchor != UpgradeReplayCodec.for_journal(state, hashlib.sha256(raw).hexdigest()):
            raise UpgradeStartupBlocked("upgrade_replay_or_generation_conflict")
        context = state.context
        if (context.installation_id, context.database_context_id, context.database_key_id,
                context.database_key_generation, context.dmk_key_id, context.dmk_generation) != (
                installation_id, loaded.database_context_id, loaded.database_key_id,
                loaded.database_key_generation, loaded.dmk_key_id, loaded.dmk_generation):
            raise UpgradeStartupBlocked("upgrade_installation_context_conflict")
        # Exact identities and explicit edge required. Product registry has NO
        # edge; no synthetic registry or journal claim can add one here.
        validate_upgrade_state(state, PRODUCT_SCHEMA_REGISTRY)
        self.guard._require_lock()
        return state


class ProductUpgradeStartupGuard:
    def __init__(self, lock: RuntimeInstanceLock, *, inventory=None, keys=None):
        self.lock = lock
        self.inventory = inventory or ProductStartupInventory()
        self.keys = keys or ExistingInstallationKeys(inventory=self.inventory)

    def _require_lock(self):
        try:
            if not isinstance(self.lock, RuntimeInstanceLock):
                raise ValueError
            descriptor = os.fstat(self.lock.fileno)
            path = self.lock.path.lstat()
            raw = self.lock.path.read_text()
            payload = json.loads(raw)
            self.lock._validate_locked_payload(raw, allow_live_owner=True)
            if (self.lock.path.is_symlink() or not stat.S_ISREG(path.st_mode)
                    or (descriptor.st_dev, descriptor.st_ino) != (path.st_dev, path.st_ino)
                    or payload["pid"] != os.getpid()
                    or payload["process_start_identity"] != _process_start_identity(os.getpid())):
                raise ValueError
        except Exception:
            raise UpgradeStartupBlocked("upgrade_runtime_lock_required") from None

    def evaluate(self, *, before=None):
        self._require_lock()
        root = self.lock.runtime_root
        if before is not None and before.root != root:
            raise UpgradeStartupBlocked("upgrade_inventory_changed")
        current = self.inventory.inspect(root)
        if current.status in {Status.UNSAFE, Status.CHANGED, Status.UNKNOWN}:
            raise UpgradeStartupBlocked("upgrade_installation_unclear")
        if before is not None:
            old = {a.relative_path: a.metadata for a in before.artifacts if a.relative_path != "instance.lock"}
            new = {a.relative_path: a.metadata for a in current.artifacts if a.relative_path != "instance.lock"}
            if old:
                # APFS also updates directory nlink when a regular file is
                # created. Descendant identities still compare in full.
                old[""] = old[""][:5]
                new[""] = new[""][:5]
            else:
                new.pop("", None)  # previously absent root, only controlled lock creation
            if old != new:
                raise UpgradeStartupBlocked("upgrade_inventory_changed")
        protection = inspect_runtime_root(root)
        if current.upgrade_evidence and current.restore_evidence:
            raise UpgradeStartupBlocked("upgrade_restore_conflict")
        if current.upgrade_evidence:
            if protection is None or protection.lifecycle is not RuntimeRootLifecycle.ACTIVE:
                raise UpgradeStartupBlocked("upgrade_installation_unknown")
            try:
                account = ExistingStartupAccountRepository(root / "security/security.sqlite", None).load_bound_active_account()
                result = self.keys.load_existing(root, authenticated_account=account)
                if result.status is not ExistingInstallationKeyStatus.VALID or result.loaded is None:
                    raise UpgradeStartupBlocked("upgrade_existing_key_unavailable")
                ReadOnlyUpgradeEvidence(self).load(result.loaded, account.installation_id)
            except UpgradeStartupBlocked:
                raise
            except Exception:
                raise UpgradeStartupBlocked("upgrade_evidence_unverified") from None
            finally:
                self._require_lock()
                if current != self.inventory.inspect(root):
                    raise UpgradeStartupBlocked("upgrade_inventory_changed")
            raise UpgradeStartupBlocked("upgrade_recovery_required")
        fresh = {a.relative_path for a in current.artifacts if a.relative_path}
        if fresh <= {"instance.lock", RUNTIME_ROOT_PROTECTION_MARKER}:
            if protection is not None and not (
                    protection.kind is RuntimeRootKind.SYNTHETIC_TEST
                    or protection.lifecycle is RuntimeRootLifecycle.INITIALIZING):
                raise UpgradeStartupBlocked("upgrade_installation_partial")
        elif protection is None:
            raise UpgradeStartupBlocked("upgrade_installation_unknown")
        elif not current.restore_evidence and current.status is not Status.V4_ARTIFACTS_PRESENT:
            raise UpgradeStartupBlocked("upgrade_installation_partial")
        # Restore evidence is delegated without keys or schema reads: during a
        # legitimate interrupted rename the live metadata/main may be absent.
        self._require_lock()
        if current != self.inventory.inspect(root):
            raise UpgradeStartupBlocked("upgrade_inventory_changed")
        return UpgradeStartupDecision(UpgradeRecoveryStatus.NO_OPERATION, "upgrade_absent")
