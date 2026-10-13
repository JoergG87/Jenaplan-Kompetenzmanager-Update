"""Isolated upgrade maintenance coordination through injected ports."""
from __future__ import annotations
from typing import Protocol
from src.core.maintenance_gate import MaintenanceGate, MaintenancePurpose
from src.core.schema_upgrade import UpgradeContext, UpgradeError


class UpgradeLeasePort(Protocol):
    def __enter__(self): ...
    def __exit__(self, exc_type, exc, traceback): ...
    def require_owner(self, context: UpgradeContext) -> None: ...


class UpgradeMaintenance:
    """Nonblocking drain then existing process writer lock. No upgrade work."""
    def __init__(self, gate: MaintenanceGate, lease: UpgradeLeasePort, context: UpgradeContext):
        self.gate, self.lease, self.context = gate, lease, context
        self.capability = None
        self._entered = False
        self._used = False
        self._recovery = False

    def __enter__(self):
        if self._used:
            raise UpgradeError("upgrade_maintenance_reused")
        self._used = True
        try:
            self.capability = self.gate.request_maintenance(
                owner_id=self.context.operation_id, purpose=MaintenancePurpose.SCHEMA_UPGRADE)
            if not self.gate.activate(self.capability, owner_id=self.context.operation_id):
                raise UpgradeError("upgrade_writers_active")
            self.lease.__enter__()
            self._entered = True
            self.lease.require_owner(self.context)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def require_recovery(self) -> None:
        if not self._entered:
            raise UpgradeError("upgrade_maintenance_not_active")
        self.lease.require_owner(self.context)
        self._recovery = True
        self.gate.mark_recovery_required()

    def __exit__(self, exc_type, exc, traceback):
        try:
            if self._entered:
                self._entered = False
                self.lease.__exit__(exc_type, exc, traceback)
        finally:
            if self.capability is not None and not self._recovery:
                self.gate.abort(self.capability, owner_id=self.context.operation_id)
                self.capability = None
        return False
