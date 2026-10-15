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
from .migration_journal_repository import AuthenticatedMigrationJournalRepository


from src.core.retired_upgrade import RetiredUpgradeAPI


class UpgradeJournalCodec:
    """Authenticated in-memory codec only; no inherited filesystem methods."""
    _encode = classmethod(AuthenticatedMigrationJournalRepository._encode.__func__)
    _decode = classmethod(AuthenticatedMigrationJournalRepository._decode.__func__)
    _validate_auth_key = staticmethod(AuthenticatedMigrationJournalRepository._validate_auth_key)

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


class AuthenticatedUpgradeJournalRepository(RetiredUpgradeAPI, UpgradeJournalCodec):
    """Compatibility name: codec available, every execution entry rejected."""
