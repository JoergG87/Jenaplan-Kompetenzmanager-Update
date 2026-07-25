"""Authenticated journal and external replay anchor for Security Sprint 8.

Both repositories are injected with explicit test paths.  The anchor path must
be outside the replayable migration root; no product RuntimePaths are used.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from src.security.database_keys import DerivedDomainKey
from src.security.simplified_migration import (
    SIMPLIFIED_MIGRATION_ARTIFACT_ROLES,
    SimplifiedMigrationArtifactV2,
    SimplifiedMigrationError,
)


MIGRATION_JOURNAL_V2_FILENAME = "database-migration-journal-v2.json"
MIGRATION_JOURNAL_V2_VERSION = 2
REPLAY_ANCHOR_V2_VERSION = 2
_MAX_BYTES = 256 * 1024
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_SAFE_PHASE = re.compile(r"\A[a-z][a-z0-9_]{0,63}\Z")
_SAFE_CODE = re.compile(r"\A[a-z][a-z0-9_]{0,79}\Z")


@dataclass(frozen=True)
class AuthenticatedMigrationJournalV2State:
    journal_version: int
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_generation: int
    dmk_key_id: str
    dmk_key_generation: int
    database_key_id: str
    database_key_generation: int
    envelope_registry_sha256: str
    revision: int
    phase: str
    artifacts: tuple[SimplifiedMigrationArtifactV2, ...]
    completed_checks: tuple[str, ...]
    error_code: str | None = None


@dataclass(frozen=True)
class ExternalReplayAnchorV2State:
    anchor_version: int
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_generation: int
    anchor_revision: int
    envelope_registry_sha256: str
    journal_revision: int
    journal_sha256: str
    lock_chain_head_sha256: str
    pending: ExternalReplayAnchorV2State | None = None

    def committed(self) -> ExternalReplayAnchorV2State:
        return replace(self, pending=None)


class AuthenticatedMigrationJournalV2Repository:
    def __init__(
        self,
        path: Path,
        *,
        fsync: Callable[[int], None] = os.fsync,
        replace_file: Callable[[Path, Path], None] = os.replace,
    ) -> None:
        self.path = Path(path)
        self._fsync = fsync
        self._replace = replace_file

    def exists(self) -> bool:
        return self.path.exists() or self.path.is_symlink()

    def create(
        self, state: AuthenticatedMigrationJournalV2State, key: DerivedDomainKey
    ) -> str:
        if self.exists():
            raise SimplifiedMigrationError("migration_journal_exists")
        return self._publish(state, key, expected_digest=None)

    def replace(
        self,
        expected_digest: str,
        state: AuthenticatedMigrationJournalV2State,
        key: DerivedDomainKey,
    ) -> str:
        _require_sha256(expected_digest)
        _observed, observed_digest = self.load_with_digest(key)
        if not hmac.compare_digest(observed_digest, expected_digest):
            raise SimplifiedMigrationError("migration_journal_changed")
        return self._publish(state, key, expected_digest=expected_digest)

    def preview_digest(
        self, state: AuthenticatedMigrationJournalV2State, key: DerivedDomainKey
    ) -> str:
        return hashlib.sha256(_encode_authenticated(state, key)).hexdigest()

    def load(
        self, key: DerivedDomainKey
    ) -> AuthenticatedMigrationJournalV2State:
        return self.load_with_digest(key)[0]

    def load_with_digest(
        self, key: DerivedDomainKey
    ) -> tuple[AuthenticatedMigrationJournalV2State, str]:
        encoded = _read_regular(self.path)
        state = _decode_authenticated(encoded, key)
        return state, hashlib.sha256(encoded).hexdigest()

    def _publish(
        self,
        state: AuthenticatedMigrationJournalV2State,
        key: DerivedDomainKey,
        *,
        expected_digest: str | None,
    ) -> str:
        _validate_journal(state)
        encoded = _encode_authenticated(state, key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.candidate")
        if temporary.exists() or temporary.is_symlink():
            raise SimplifiedMigrationError("migration_journal_candidate_exists")
        descriptor = None
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(temporary, flags, 0o600)
            os.write(descriptor, encoded)
            os.fchmod(descriptor, 0o600)
            self._fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            if expected_digest is not None:
                _current, current_digest = self.load_with_digest(key)
                if not hmac.compare_digest(current_digest, expected_digest):
                    raise SimplifiedMigrationError("migration_journal_changed")
            elif self.exists():
                raise SimplifiedMigrationError("migration_journal_exists")
            self._replace(temporary, self.path)
            _fsync_directory(self.path.parent, self._fsync)
        except SimplifiedMigrationError:
            raise
        except OSError:
            raise SimplifiedMigrationError("migration_journal_publish_failed") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary.exists() and not temporary.is_symlink():
                try:
                    temporary.unlink()
                except OSError:
                    pass
        observed, digest = self.load_with_digest(key)
        if observed != state:
            raise SimplifiedMigrationError("migration_journal_publish_mismatch")
        return digest


class ExternalReplayAnchorV2Repository:
    """HMAC repository for an anchor injected outside the migration root."""

    def __init__(
        self,
        path: Path,
        *,
        fsync: Callable[[int], None] = os.fsync,
        replace_file: Callable[[Path, Path], None] = os.replace,
    ) -> None:
        self.path = Path(path)
        self._fsync = fsync
        self._replace = replace_file

    def exists(self) -> bool:
        return self.path.exists() or self.path.is_symlink()

    def initialize(
        self, state: ExternalReplayAnchorV2State, key: DerivedDomainKey
    ) -> ExternalReplayAnchorV2State:
        if self.exists():
            raise SimplifiedMigrationError("migration_anchor_exists")
        self._publish(state, key, expected=None)
        return state

    def read(self, key: DerivedDomainKey) -> ExternalReplayAnchorV2State:
        return _decode_anchor(_read_regular(self.path), key)

    def prepare(
        self,
        expected: ExternalReplayAnchorV2State,
        planned: ExternalReplayAnchorV2State,
        key: DerivedDomainKey,
    ) -> ExternalReplayAnchorV2State:
        current = self.read(key)
        if current != expected or current.pending is not None:
            raise SimplifiedMigrationError("migration_anchor_changed")
        if planned.pending is not None or planned.anchor_revision != expected.anchor_revision + 1:
            raise SimplifiedMigrationError("migration_anchor_plan_invalid")
        prepared = replace(expected, pending=planned)
        self._publish(prepared, key, expected=expected)
        return prepared

    def commit(
        self,
        prepared: ExternalReplayAnchorV2State,
        observed: ExternalReplayAnchorV2State,
        key: DerivedDomainKey,
    ) -> ExternalReplayAnchorV2State:
        current = self.read(key)
        if current != prepared or prepared.pending != observed:
            raise SimplifiedMigrationError("migration_anchor_changed")
        committed = observed.committed()
        self._publish(committed, key, expected=prepared)
        return committed

    def abort_pending(
        self, prepared: ExternalReplayAnchorV2State, key: DerivedDomainKey
    ) -> ExternalReplayAnchorV2State:
        current = self.read(key)
        if current != prepared or prepared.pending is None:
            raise SimplifiedMigrationError("migration_anchor_changed")
        committed = prepared.committed()
        self._publish(committed, key, expected=prepared)
        return committed

    def _publish(
        self,
        state: ExternalReplayAnchorV2State,
        key: DerivedDomainKey,
        *,
        expected: ExternalReplayAnchorV2State | None,
    ) -> None:
        _validate_anchor(state)
        encoded = _encode_anchor(state, key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.candidate")
        if temporary.exists() or temporary.is_symlink():
            raise SimplifiedMigrationError("migration_anchor_candidate_exists")
        descriptor = None
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(temporary, flags, 0o600)
            os.write(descriptor, encoded)
            os.fchmod(descriptor, 0o600)
            self._fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            if expected is None:
                if self.exists():
                    raise SimplifiedMigrationError("migration_anchor_exists")
            elif self.read(key) != expected:
                raise SimplifiedMigrationError("migration_anchor_changed")
            self._replace(temporary, self.path)
            _fsync_directory(self.path.parent, self._fsync)
        except SimplifiedMigrationError:
            raise
        except OSError:
            raise SimplifiedMigrationError("migration_anchor_publish_failed") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary.exists() and not temporary.is_symlink():
                try:
                    temporary.unlink()
                except OSError:
                    pass
        if self.read(key) != state:
            raise SimplifiedMigrationError("migration_anchor_publish_mismatch")


def _encode_authenticated(
    state: AuthenticatedMigrationJournalV2State, key: DerivedDomainKey
) -> bytes:
    _validate_journal(state)
    payload = _journal_payload(state)
    payload_bytes = _canonical_bytes(payload)
    tag = hmac.new(key.key_material, payload_bytes, hashlib.sha256).hexdigest()
    return _canonical_bytes({"payload": payload, "tag": tag})


def _decode_authenticated(
    encoded: bytes, key: DerivedDomainKey
) -> AuthenticatedMigrationJournalV2State:
    try:
        wrapper = json.loads(encoded.decode("ascii"))
        if not isinstance(wrapper, dict) or set(wrapper) != {"payload", "tag"}:
            raise ValueError
        payload = wrapper["payload"]
        tag = wrapper["tag"]
        expected = hmac.new(
            key.key_material, _canonical_bytes(payload), hashlib.sha256
        ).hexdigest()
        if not isinstance(tag, str) or not hmac.compare_digest(tag, expected):
            raise SimplifiedMigrationError("migration_journal_authentication_failed")
        state = _journal_from_payload(payload)
    except SimplifiedMigrationError:
        raise
    except Exception:
        raise SimplifiedMigrationError("migration_journal_format_invalid") from None
    if _encode_authenticated(state, key) != encoded:
        raise SimplifiedMigrationError("migration_journal_not_canonical")
    return state


def _journal_payload(state: AuthenticatedMigrationJournalV2State) -> dict[str, object]:
    return {
        "artifacts": [item.to_payload() for item in state.artifacts],
        "completed_checks": list(state.completed_checks),
        "database_context_id": state.database_context_id,
        "database_key_generation": state.database_key_generation,
        "database_key_id": state.database_key_id,
        "dmk_key_generation": state.dmk_key_generation,
        "dmk_key_id": state.dmk_key_id,
        "envelope_registry_sha256": state.envelope_registry_sha256,
        "error_code": state.error_code,
        "installation_id": state.installation_id,
        "journal_version": state.journal_version,
        "migration_generation": state.migration_generation,
        "migration_id": state.migration_id,
        "phase": state.phase,
        "revision": state.revision,
    }


def _journal_from_payload(payload: object) -> AuthenticatedMigrationJournalV2State:
    if not isinstance(payload, dict) or set(payload) != set(
        _journal_payload(
            AuthenticatedMigrationJournalV2State(
                2, "", "", "", 1, "", 1, "", 1, "0" * 64, 0,
                "not_started", (), (), None
            )
        )
    ):
        raise SimplifiedMigrationError("migration_journal_fields_invalid")
    try:
        artifacts = tuple(SimplifiedMigrationArtifactV2(**item) for item in payload["artifacts"])
        state = AuthenticatedMigrationJournalV2State(
            journal_version=payload["journal_version"],
            installation_id=payload["installation_id"],
            database_context_id=payload["database_context_id"],
            migration_id=payload["migration_id"],
            migration_generation=payload["migration_generation"],
            dmk_key_id=payload["dmk_key_id"],
            dmk_key_generation=payload["dmk_key_generation"],
            database_key_id=payload["database_key_id"],
            database_key_generation=payload["database_key_generation"],
            envelope_registry_sha256=payload["envelope_registry_sha256"],
            revision=payload["revision"],
            phase=payload["phase"],
            artifacts=artifacts,
            completed_checks=tuple(payload["completed_checks"]),
            error_code=payload["error_code"],
        )
    except Exception:
        raise SimplifiedMigrationError("migration_journal_fields_invalid") from None
    _validate_journal(state)
    return state


def _validate_journal(state: AuthenticatedMigrationJournalV2State) -> None:
    if not isinstance(state, AuthenticatedMigrationJournalV2State):
        raise SimplifiedMigrationError("migration_journal_state_invalid")
    if state.journal_version != MIGRATION_JOURNAL_V2_VERSION:
        raise SimplifiedMigrationError("migration_journal_version_unsupported")
    if type(state.revision) is not int or state.revision < 0:
        raise SimplifiedMigrationError("migration_journal_revision_invalid")
    if not isinstance(state.phase, str) or not _SAFE_PHASE.fullmatch(state.phase):
        raise SimplifiedMigrationError("migration_journal_phase_invalid")
    if tuple(item.role for item in state.artifacts) != SIMPLIFIED_MIGRATION_ARTIFACT_ROLES:
        raise SimplifiedMigrationError("migration_journal_artifacts_invalid")
    _require_sha256(state.envelope_registry_sha256)
    if not isinstance(state.completed_checks, tuple) or len(set(state.completed_checks)) != len(state.completed_checks):
        raise SimplifiedMigrationError("migration_journal_checks_invalid")
    if any(not isinstance(item, str) or not _SAFE_CODE.fullmatch(item) for item in state.completed_checks):
        raise SimplifiedMigrationError("migration_journal_checks_invalid")
    if state.error_code is not None and (
        not isinstance(state.error_code, str) or not _SAFE_CODE.fullmatch(state.error_code)
    ):
        raise SimplifiedMigrationError("migration_journal_error_invalid")


def _encode_anchor(state: ExternalReplayAnchorV2State, key: DerivedDomainKey) -> bytes:
    _validate_anchor(state)
    payload = _anchor_payload(state)
    tag = hmac.new(key.key_material, _canonical_bytes(payload), hashlib.sha256).hexdigest()
    return _canonical_bytes({"payload": payload, "tag": tag})


def _decode_anchor(encoded: bytes, key: DerivedDomainKey) -> ExternalReplayAnchorV2State:
    try:
        wrapper = json.loads(encoded.decode("ascii"))
        payload = wrapper["payload"]
        tag = wrapper["tag"]
        if set(wrapper) != {"payload", "tag"}:
            raise ValueError
        expected = hmac.new(key.key_material, _canonical_bytes(payload), hashlib.sha256).hexdigest()
        if not isinstance(tag, str) or not hmac.compare_digest(tag, expected):
            raise SimplifiedMigrationError("migration_anchor_authentication_failed")
        state = _anchor_from_payload(payload)
    except SimplifiedMigrationError:
        raise
    except Exception:
        raise SimplifiedMigrationError("migration_anchor_format_invalid") from None
    if _encode_anchor(state, key) != encoded:
        raise SimplifiedMigrationError("migration_anchor_not_canonical")
    return state


def _anchor_payload(state: ExternalReplayAnchorV2State) -> dict[str, object]:
    return {
        "anchor_revision": state.anchor_revision,
        "anchor_version": state.anchor_version,
        "database_context_id": state.database_context_id,
        "envelope_registry_sha256": state.envelope_registry_sha256,
        "installation_id": state.installation_id,
        "journal_revision": state.journal_revision,
        "journal_sha256": state.journal_sha256,
        "lock_chain_head_sha256": state.lock_chain_head_sha256,
        "migration_generation": state.migration_generation,
        "migration_id": state.migration_id,
        "pending": None if state.pending is None else _anchor_payload(state.pending),
    }


def _anchor_from_payload(payload: object) -> ExternalReplayAnchorV2State:
    expected = {
        "anchor_revision", "anchor_version", "database_context_id",
        "envelope_registry_sha256", "installation_id", "journal_revision",
        "journal_sha256", "lock_chain_head_sha256", "migration_generation",
        "migration_id", "pending",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise SimplifiedMigrationError("migration_anchor_fields_invalid")
    try:
        pending = None if payload["pending"] is None else _anchor_from_payload(payload["pending"])
        state = ExternalReplayAnchorV2State(
            anchor_version=payload["anchor_version"],
            installation_id=payload["installation_id"],
            database_context_id=payload["database_context_id"],
            migration_id=payload["migration_id"],
            migration_generation=payload["migration_generation"],
            anchor_revision=payload["anchor_revision"],
            envelope_registry_sha256=payload["envelope_registry_sha256"],
            journal_revision=payload["journal_revision"],
            journal_sha256=payload["journal_sha256"],
            lock_chain_head_sha256=payload["lock_chain_head_sha256"],
            pending=pending,
        )
    except Exception:
        raise SimplifiedMigrationError("migration_anchor_fields_invalid") from None
    _validate_anchor(state)
    return state


def _validate_anchor(state: ExternalReplayAnchorV2State, *, nested: bool = False) -> None:
    if state.anchor_version != REPLAY_ANCHOR_V2_VERSION:
        raise SimplifiedMigrationError("migration_anchor_version_unsupported")
    if type(state.anchor_revision) is not int or state.anchor_revision < 1:
        raise SimplifiedMigrationError("migration_anchor_revision_invalid")
    if type(state.journal_revision) is not int or state.journal_revision < 0:
        raise SimplifiedMigrationError("migration_anchor_revision_invalid")
    for digest in (
        state.envelope_registry_sha256,
        state.journal_sha256,
        state.lock_chain_head_sha256,
    ):
        _require_sha256(digest)
    if state.pending is not None:
        if nested or state.pending.pending is not None:
            raise SimplifiedMigrationError("migration_anchor_pending_invalid")
        _validate_anchor(state.pending, nested=True)
        if state.pending.anchor_revision != state.anchor_revision + 1:
            raise SimplifiedMigrationError("migration_anchor_pending_invalid")


def _read_regular(path: Path) -> bytes:
    try:
        status = path.lstat()
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            raise SimplifiedMigrationError("migration_state_file_invalid")
        if status.st_size <= 0 or status.st_size > _MAX_BYTES:
            raise SimplifiedMigrationError("migration_state_file_size_invalid")
        encoded = path.read_bytes()
    except SimplifiedMigrationError:
        raise
    except OSError:
        raise SimplifiedMigrationError("migration_state_file_unreadable") from None
    if len(encoded) != status.st_size:
        raise SimplifiedMigrationError("migration_state_file_changed")
    return encoded


def _fsync_directory(path: Path, fsync: Callable[[int], None]) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _require_sha256(value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise SimplifiedMigrationError("migration_state_digest_invalid")


__all__ = [
    "AuthenticatedMigrationJournalV2Repository",
    "AuthenticatedMigrationJournalV2State",
    "ExternalReplayAnchorV2Repository",
    "ExternalReplayAnchorV2State",
    "MIGRATION_JOURNAL_V2_FILENAME",
]
