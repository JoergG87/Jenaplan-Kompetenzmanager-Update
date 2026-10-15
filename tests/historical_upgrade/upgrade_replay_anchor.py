"""Local authenticated high-water mark, NOT a rollback-resistant platform counter."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from src.security.infrastructure.migration_journal_repository import AuthenticatedMigrationJournalRepository
from src.core.schema_upgrade import UpgradeError


@dataclass(frozen=True)
class UpgradeReplayAnchor:
    context_sha256: str
    revision: int
    journal_sha256: str


class UpgradeReplayAnchorRepository(AuthenticatedMigrationJournalRepository):
    def __init__(self, permissions, lease, context):
        super().__init__(lease.lock.runtime_root / "schema-upgrade-replay" / "anchor.json", permissions)
        self.lease, self.context = lease, context

    def _require(self):
        self.lease.require_owner(self.context)
        if self.path != self.lease.lock.runtime_root / "schema-upgrade-replay" / "anchor.json":
            raise UpgradeError("upgrade_anchor_path_invalid")

    def create(self, state, auth_key):
        self._require()
        return super().create(state, auth_key)

    def load(self, auth_key):
        self._require()
        return super().load(auth_key)

    def load_with_digest(self, auth_key):
        self._require()
        return super().load_with_digest(auth_key)

    def save(self, expected, replacement, auth_key):
        self._require()
        if (expected.context_sha256 != replacement.context_sha256
                or expected.journal_sha256 == replacement.journal_sha256):
            raise UpgradeError("upgrade_anchor_transition_invalid")
        return super().save(expected, replacement, auth_key)

    def delete_completed(self, *args, **kwargs):
        raise UpgradeError("upgrade_anchor_retention_required")

    def peek_context(self):
        raise UpgradeError("upgrade_anchor_authentication_required")

    @staticmethod
    def _validate_state(state):
        if (not isinstance(state, UpgradeReplayAnchor)
                or type(state.revision) is not int or not 0 <= state.revision <= 32
                or any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
                       for value in (state.context_sha256, state.journal_sha256))):
            raise UpgradeError("upgrade_anchor_invalid")

    @staticmethod
    def _payload(state):
        return {"protocol": "schema-upgrade-replay-v1", "anchor": asdict(state)}

    @classmethod
    def _restore_payload(cls, payload):
        try:
            if set(payload) != {"protocol", "anchor"} or payload["protocol"] != "schema-upgrade-replay-v1":
                raise ValueError
            state = UpgradeReplayAnchor(**payload["anchor"])
            cls._validate_state(state)
            return state
        except (TypeError, KeyError, ValueError):
            raise UpgradeError("upgrade_anchor_invalid") from None

    @staticmethod
    def for_journal(state, digest):
        context = json.dumps(asdict(state.context), sort_keys=True, separators=(",", ":")).encode("ascii")
        return UpgradeReplayAnchor(hashlib.sha256(context).hexdigest(), state.revision, digest)
