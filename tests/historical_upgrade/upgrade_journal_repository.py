"""Upgrade payload over the existing authenticated atomic journal mechanism."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import stat
from pathlib import Path

from src.core.schema_registry import DatabaseSchemaRegistry, RegisteredSchemaIdentity
from src.core.schema_upgrade import (UpgradeContext, UpgradeArtifact, UpgradeEvidence,
    UpgradePhase, UpgradeState, UpgradeError, UpgradeExchangeIntent, UpgradeExchangeResult,
    UpgradeRestartReceipt, UpgradeTargetInspection, validate_upgrade_structure,
    validate_upgrade_state, advance_upgrade)
from src.security.infrastructure.migration_journal_repository import AuthenticatedMigrationJournalRepository
from tests.historical_upgrade.upgrade_process_lease import UpgradeProcessLease
from tests.historical_upgrade.upgrade_replay_anchor import UpgradeReplayAnchorRepository
from src.security.infrastructure.migration_journal_repository import _fsync_directory


class AuthenticatedUpgradeJournalRepository(AuthenticatedMigrationJournalRepository):
    """Only synthetic, lease-bound access. Existing HMAC and atomic I/O reused."""
    def __init__(self, path: Path, permissions, *, context: UpgradeContext,
                 registry: DatabaseSchemaRegistry, lease: UpgradeProcessLease, fault_hook=None):
        expected = lease.lock.runtime_root / "schema-upgrade-foundation" / "journal.json"
        if Path(path) != expected:
            raise UpgradeError("upgrade_journal_path_invalid")
        super().__init__(path, permissions)
        self.context, self.registry, self.lease = context, registry, lease
        self.anchor = UpgradeReplayAnchorRepository(permissions, lease, context)
        self._fault_hook = fault_hook

    def _emit(self, boundary):
        if self._fault_hook is not None:
            self._fault_hook(boundary)

    def _private(self, path):
        details = path.lstat()
        expected = 0o700 if stat.S_ISDIR(details.st_mode) else 0o600
        if (path.is_symlink() or stat.S_IMODE(details.st_mode) != expected
                or not (stat.S_ISDIR(details.st_mode) or stat.S_ISREG(details.st_mode))):
            raise UpgradeError("upgrade_replay_path_unsafe")

    def _anchor_for(self, state, auth_key):
        return self.anchor.for_journal(state, self.preview_digest(state, auth_key))

    def _verify_anchor(self, state, digest, auth_key):
        self._private(self.path.parent)
        self._private(self.path)
        self._private(self.anchor.path.parent)
        self._private(self.anchor.path)
        if self.anchor.load(auth_key) != self.anchor.for_journal(state, digest):
            raise UpgradeError("upgrade_replay_or_generation_conflict")

    def _require(self, state=None):
        self.lease.require_owner(self.context)
        if self.path != self.lease.lock.runtime_root / "schema-upgrade-foundation" / "journal.json":
            raise UpgradeError("upgrade_journal_path_invalid")
        if state is not None:
            if state.context != self.context:
                raise UpgradeError("upgrade_journal_context_mismatch")
            validate_upgrade_state(state, self.registry)

    def exists(self) -> bool:
        self._require()
        self._require_clean_directory(prepare=False)
        # Even an empty directory is retained evidence, never a fresh operation.
        present = False
        for path in (self.path.parent, self.anchor.path.parent,
                     self.lease.lock.runtime_root / "schema-upgrade-source"):
            try:
                path.lstat()  # exists() can hide permission/I/O errors as absence
                present = True
            except FileNotFoundError:
                pass
        return present

    def create(self, state, auth_key):
        self._require(state)
        if state.phase is not UpgradePhase.PREFLIGHT or state.revision != 0:
            raise UpgradeError("upgrade_journal_initial_state_required")
        if self.exists():
            from src.security.infrastructure.migration_journal_repository import MigrationJournalError
            raise MigrationJournalError("migration_journal_already_exists")
        self._emit("before_first_anchor")
        self.anchor._require_clean_directory(prepare=True)
        self._private(self.anchor.path.parent)
        _fsync_directory(self.lease.lock.runtime_root)
        self._emit("before_anchor_write")
        self.anchor.create(self._anchor_for(state, auth_key), auth_key)
        self._emit("after_anchor_write")
        self._require_clean_directory(prepare=True)
        self._private(self.path.parent)
        _fsync_directory(self.lease.lock.runtime_root)
        super().create(state, auth_key)
        self._emit("after_journal_write")

    def load(self, auth_key):
        return self.load_with_digest(auth_key)[0]

    def load_with_digest(self, auth_key):
        self._require()
        state, digest = super().load_with_digest(auth_key)
        self._require(state)
        self._verify_anchor(state, digest, auth_key)
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
        if self.load(auth_key) != expected:
            from src.security.infrastructure.migration_journal_repository import MigrationJournalError
            raise MigrationJournalError("migration_journal_changed")
        self._emit("before_anchor_write")
        self.anchor.save(self._anchor_for(expected, auth_key),
                         self._anchor_for(replacement, auth_key), auth_key)
        self._emit("after_anchor_write")
        super().save(expected, replacement, auth_key)
        self._emit("after_journal_write")

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
        raw = asdict(state)
        if state.contract_version == 1:
            # Preserve historical authenticated bytes AND anchor digest exactly.
            raw.pop("contract_version")
            for evidence in raw["evidence"]:
                for field in ("exchange_intent", "exchange_result", "restart", "inspection"):
                    evidence.pop(field)
        return {"protocol": f"schema-upgrade-v{state.contract_version}", "state": raw}

    @staticmethod
    def _restore_payload(payload):
        try:
            if not isinstance(payload, dict) or set(payload) != {"protocol", "state"}:
                raise ValueError
            versions = {"schema-upgrade-v1": 1, "schema-upgrade-v2": 2}
            version = versions[payload["protocol"]]
            raw = payload["state"]
            fields = {"context", "phase", "revision", "evidence"}
            if version == 2:
                fields.add("contract_version")
            if not isinstance(raw, dict) or set(raw) != fields:
                raise ValueError
            if version == 2 and (type(raw["contract_version"]) is not int or raw["contract_version"] != 2):
                raise ValueError
            context = _context(raw["context"])
            if not isinstance(raw["evidence"], list):
                raise ValueError
            evidence = tuple(_evidence(item, version) for item in raw["evidence"])
            state = UpgradeState(context, UpgradePhase(raw["phase"]), raw["revision"], evidence, version)
            validate_upgrade_structure(state)
            return state
        except (TypeError, KeyError, ValueError, AttributeError):
            raise UpgradeError("upgrade_journal_payload_invalid") from None


def _context(raw):
    return UpgradeContext(**{**raw, "source": RegisteredSchemaIdentity(**raw["source"]),
                             "target": RegisteredSchemaIdentity(**raw["target"])})


def _artifact(raw):
    return UpgradeArtifact(**{**raw, "schema": RegisteredSchemaIdentity(**raw["schema"])})


def _nested(raw, kind, artifact_fields):
    if raw is None:
        return None
    converted = {**raw, "context": _context(raw["context"])}
    for field in artifact_fields:
        converted[field] = _artifact(raw[field])
    return kind(**converted)


def _evidence(raw, version):
    fields = {"context", "phase", "artifacts"}
    if version == 2:
        fields |= {"exchange_intent", "exchange_result", "restart", "inspection"}
    if not isinstance(raw, dict) or set(raw) != fields or not isinstance(raw["artifacts"], list):
        raise ValueError
    extra = {} if version == 1 else {
        "exchange_intent": _nested(raw["exchange_intent"], UpgradeExchangeIntent, ("expected_live", "replacement")),
        "exchange_result": _nested(raw["exchange_result"], UpgradeExchangeResult, ("installed",)),
        "restart": _nested(raw["restart"], UpgradeRestartReceipt, ("installed",)),
        "inspection": _nested(raw["inspection"], UpgradeTargetInspection, ("target",)),
    }
    return UpgradeEvidence(_context(raw["context"]), UpgradePhase(raw["phase"]),
                           tuple(_artifact(item) for item in raw["artifacts"]), **extra)
