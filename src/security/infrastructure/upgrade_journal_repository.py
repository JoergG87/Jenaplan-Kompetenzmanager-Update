"""Upgrade payload over the existing authenticated atomic journal mechanism."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import stat
from pathlib import Path

from src.core.schema_registry import DatabaseSchemaRegistry, RegisteredSchemaIdentity
from src.core.schema_upgrade import (UpgradeContext, UpgradeArtifact, UpgradeEvidence,
    UpgradePhase, UpgradeState, UpgradeError, validate_upgrade_structure,
    validate_upgrade_state, advance_upgrade)
from .migration_journal_repository import AuthenticatedMigrationJournalRepository
from .upgrade_process_lease import UpgradeProcessLease
from .upgrade_replay_anchor import UpgradeReplayAnchorRepository
from .migration_journal_repository import _fsync_directory


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
            from .migration_journal_repository import MigrationJournalError
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
            from .migration_journal_repository import MigrationJournalError
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
