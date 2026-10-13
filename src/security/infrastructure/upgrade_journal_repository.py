"""Upgrade payload over the existing authenticated atomic journal mechanism."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
from pathlib import Path

from src.core.schema_registry import DatabaseSchemaRegistry, RegisteredSchemaIdentity
from src.core.schema_upgrade import (UpgradeContext, UpgradeArtifact, UpgradeEvidence,
    UpgradePhase, UpgradeState, UpgradeError, validate_upgrade_structure,
    validate_upgrade_state, advance_upgrade)
from .migration_journal_repository import AuthenticatedMigrationJournalRepository
from .upgrade_process_lease import UpgradeProcessLease


class AuthenticatedUpgradeJournalRepository(AuthenticatedMigrationJournalRepository):
    """Only synthetic, lease-bound access. Existing HMAC and atomic I/O reused."""
    def __init__(self, path: Path, permissions, *, context: UpgradeContext,
                 registry: DatabaseSchemaRegistry, lease: UpgradeProcessLease):
        expected = lease.lock.runtime_root / "schema-upgrade-foundation" / "journal.json"
        if Path(path) != expected:
            raise UpgradeError("upgrade_journal_path_invalid")
        super().__init__(path, permissions)
        self.context, self.registry, self.lease = context, registry, lease

    def _require(self, state=None):
        self.lease.require_owner(self.context)
        if state is not None:
            if state.context != self.context:
                raise UpgradeError("upgrade_journal_context_mismatch")
            validate_upgrade_state(state, self.registry)

    def create(self, state, auth_key):
        self._require(state)
        if state.phase is not UpgradePhase.PREFLIGHT or state.revision != 0:
            raise UpgradeError("upgrade_journal_initial_state_required")
        return super().create(state, auth_key)

    def load(self, auth_key):
        self._require()
        state = super().load(auth_key)
        self._require(state)
        return state

    def load_with_digest(self, auth_key):
        self._require()
        state, digest = super().load_with_digest(auth_key)
        self._require(state)
        return state, digest

    def save(self, expected, replacement, auth_key):
        self._require(expected)
        self._require(replacement)
        if replacement == expected:
            if self.load(auth_key) != expected:
                raise UpgradeError("upgrade_journal_changed")
            return
        if not replacement.evidence or advance_upgrade(expected, replacement.evidence[-1], self.registry) != replacement:
            raise UpgradeError("upgrade_journal_transition_invalid")
        return super().save(expected, replacement, auth_key)

    def delete_completed(self, *args, **kwargs):
        raise UpgradeError("upgrade_journal_retention_required")

    def peek_context(self):
        raise UpgradeError("upgrade_journal_authentication_required")

    @classmethod
    def preview_digest(cls, state, auth_key):
        return hashlib.sha256(cls._encode(state, auth_key)).hexdigest()

    @staticmethod
    def _validate_state(state):
        validate_upgrade_structure(state)

    @staticmethod
    def _payload(state):
        return {"protocol": "schema-upgrade-v1", "state": asdict(state)}

    @staticmethod
    def _restore_payload(payload):
        try:
            if not isinstance(payload, dict) or set(payload) != {"protocol", "state"} or payload["protocol"] != "schema-upgrade-v1":
                raise ValueError
            raw = payload["state"]
            if not isinstance(raw, dict) or set(raw) != {"context", "phase", "revision", "evidence"}:
                raise ValueError
            context = _context(raw["context"])
            evidence = tuple(_evidence(item) for item in raw["evidence"])
            state = UpgradeState(context, UpgradePhase(raw["phase"]), raw["revision"], evidence)
            validate_upgrade_structure(state)
            return state
        except (TypeError, KeyError, ValueError):
            raise UpgradeError("upgrade_journal_payload_invalid") from None


def _context(raw):
    return UpgradeContext(**{**raw, "source": RegisteredSchemaIdentity(**raw["source"]),
                             "target": RegisteredSchemaIdentity(**raw["target"])})


def _evidence(raw):
    if set(raw) != {"context", "phase", "artifacts"}:
        raise ValueError
    return UpgradeEvidence(_context(raw["context"]), UpgradePhase(raw["phase"]), tuple(
        UpgradeArtifact(**{**item, "schema": RegisteredSchemaIdentity(**item["schema"])})
        for item in raw["artifacts"]))
