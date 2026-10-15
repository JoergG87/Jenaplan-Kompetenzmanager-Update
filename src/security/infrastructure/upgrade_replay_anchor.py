"""Local authenticated high-water mark, NOT a rollback-resistant platform counter."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from .migration_journal_repository import AuthenticatedMigrationJournalRepository
from src.core.schema_upgrade import UpgradeError


@dataclass(frozen=True)
class UpgradeReplayAnchor:
    context_sha256: str
    revision: int
    journal_sha256: str


from src.core.retired_upgrade import RetiredUpgradeAPI


class UpgradeReplayCodec:
    _encode = classmethod(AuthenticatedMigrationJournalRepository._encode.__func__)
    _decode = classmethod(AuthenticatedMigrationJournalRepository._decode.__func__)
    _validate_auth_key = staticmethod(AuthenticatedMigrationJournalRepository._validate_auth_key)

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


class UpgradeReplayAnchorRepository(RetiredUpgradeAPI, UpgradeReplayCodec):
    """Compatibility name: no filesystem authority."""
