"""Prepare only encrypted source backup/staging; never migrate or activate."""
from typing import Protocol
from src.core.maintenance_gate import MaintenancePurpose
from src.core.schema_upgrade import (UpgradePhase, UpgradeEvidence, UpgradeError,
    advance_upgrade, new_upgrade_state)
from tests.historical_upgrade.schema_upgrade import UpgradeMaintenance


class UpgradeSourcePreparationPort(Protocol):
    def validate_context(self): ...
    def verify_source(self): ...
    def create_backup(self): ...
    def verify_backup(self, source): ...
    def create_staging(self, source, backup): ...
    def verify_staging(self, source): ...


class PrepareEncryptedUpgradeSource:
    def __init__(self, *, context, registry, gate, lease, journal, auth_key,
                 adapter: UpgradeSourcePreparationPort):
        self.context, self.registry, self.gate, self.lease = context, registry, gate, lease
        self.journal, self.auth_key, self.adapter = journal, auth_key, adapter

    def execute(self):
        initial = new_upgrade_state(self.context, self.registry)  # no unknown edge, no I/O
        with UpgradeMaintenance(self.gate, self.lease, self.context) as maintenance:
            with self.gate.exclusive_writer(maintenance.capability,
                    owner_id=self.context.operation_id, purpose=MaintenancePurpose.SCHEMA_UPGRADE):
                state = None
                def persist(phase, artifact=None):
                    nonlocal state
                    replacement = advance_upgrade(state, UpgradeEvidence(
                        self.context, phase, () if artifact is None else (artifact,)), self.registry)
                    self.journal.save(state, replacement, self.auth_key)
                    state = replacement
                try:
                    self.adapter.validate_context()
                    if self.journal.exists():
                        state = self.journal.load(self.auth_key)
                    else:
                        self.journal.create(initial, self.auth_key)
                        state = initial
                    if state.phase is UpgradePhase.PREFLIGHT:
                        persist(UpgradePhase.EXCLUSIVE)
                    if state.phase not in {UpgradePhase.EXCLUSIVE, UpgradePhase.SOURCE_VERIFIED,
                            UpgradePhase.BACKUP_VERIFIED, UpgradePhase.STAGED}:
                        raise UpgradeError("upgrade_source_recovery_required")
                    recorded = {item.role: item for receipt in state.evidence for item in receipt.artifacts}
                    source = self.adapter.verify_source()
                    if "source" in recorded and recorded["source"] != source.artifact:
                        raise UpgradeError("upgrade_source_evidence_changed")
                    if state.phase is UpgradePhase.EXCLUSIVE:
                        persist(UpgradePhase.SOURCE_VERIFIED, source.artifact)
                    if state.phase is UpgradePhase.SOURCE_VERIFIED:
                        self.adapter.create_backup()
                    backup = self.adapter.verify_backup(source)
                    if "backup" in recorded and recorded["backup"] != backup:
                        raise UpgradeError("upgrade_backup_evidence_changed")
                    if state.phase is UpgradePhase.SOURCE_VERIFIED:
                        persist(UpgradePhase.BACKUP_VERIFIED, backup)
                    if state.phase is UpgradePhase.BACKUP_VERIFIED:
                        candidate = self.adapter.create_staging(source, backup)
                    else:
                        candidate = self.adapter.verify_staging(source)
                        if recorded.get("candidate") != candidate:
                            raise UpgradeError("upgrade_staging_evidence_changed")
                    # Recheck source after all snapshot/copy operations.
                    if self.adapter.verify_source() != source:
                        raise UpgradeError("upgrade_source_changed")
                    if state.phase is UpgradePhase.BACKUP_VERIFIED:
                        persist(UpgradePhase.STAGED, candidate)
                    return state
                except Exception:
                    maintenance.require_recovery()
                    if state is not None and state.phase not in {UpgradePhase.RECOVERY_REQUIRED, UpgradePhase.ABORTED}:
                        persist(UpgradePhase.RECOVERY_REQUIRED)
                    raise
