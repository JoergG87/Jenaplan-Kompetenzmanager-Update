"""Isolated pre-start classification port; not wired into product startup."""
from dataclasses import dataclass
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.schema_upgrade import (UpgradeArtifact, UpgradePhase, UpgradeRecoveryStatus, classify_upgrade)


@dataclass(frozen=True)
class UpgradeStartupDecision:
    status: UpgradeRecoveryStatus
    reason: str

    @property
    def continue_existing_startup(self):
        return self.status is UpgradeRecoveryStatus.NO_OPERATION

    @property
    def normal_runtime_allowed(self):
        return False

    @property
    def first_run_allowed(self):
        return False

    @property
    def activation_allowed(self):
        return False


class UpgradeStartupGuard:
    """Caller supplies fresh independently verified artifacts under the same lease.

    inventory_complete includes source workspace, backup, candidate, document
    crossbindings and restore evidence. False/unknown always blocks. This port
    never opens databases, chooses candidates, repairs files or grants admission.
    """
    def __init__(self, journal):
        self.journal = journal

    def evaluate(self, auth_key, *, observed, inventory_complete,
                 live_schema, restore_clear):
        blocked = UpgradeStartupDecision(UpgradeRecoveryStatus.RECOVERY_REQUIRED,
                                          "upgrade_evidence_required")
        if (inventory_complete is not True or restore_clear is not True
                or not isinstance(observed, tuple)
                or any(not isinstance(item, UpgradeArtifact) for item in observed)):
            return blocked
        try:
            journal = self.journal
            present = journal.exists()  # lease required, includes orphan directories
            if not present:
                if observed or live_schema != FINAL_V4_SCHEMA_REGISTRATION.identity:
                    return blocked
                return UpgradeStartupDecision(UpgradeRecoveryStatus.NO_OPERATION, "upgrade_absent")
            # Fail closed on unexpected entries, including either repository's temp files.
            for path in (journal.path, journal.anchor.path):
                journal._private(path.parent)
                if set(path.parent.iterdir()) != {path}:
                    return blocked
            state = journal.load(auth_key)  # authentication AND freshness AND exact context
            expected_live = (state.context.target if state.phase is UpgradePhase.COMPLETED
                             else state.context.source)
            if live_schema != expected_live or any(
                    item.role == "live" and item.schema != live_schema for item in observed):
                return blocked
            decision = classify_upgrade(state, expected_context=journal.context,
                observed=observed, registry=journal.registry, inventory_complete=True,
                journal_authenticated=True)
            return UpgradeStartupDecision(decision.status, decision.reason)
        except (OSError, ValueError, RuntimeError):
            return blocked
