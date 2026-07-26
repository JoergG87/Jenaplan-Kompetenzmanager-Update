"""Authenticated journal and replay anchor for Security Sprint 11."""

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

from .integration_gate import SecurityIntegrationError


SECURITY_INTEGRATION_JOURNAL_VERSION = 1
SECURITY_INTEGRATION_ANCHOR_VERSION = 1
_MAX_STATE_BYTES = 512 * 1024
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_SAFE_CODE = re.compile(r"\A[A-Za-z][A-Za-z0-9_]{0,79}\Z")
_SAFE_RELATIVE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")


@dataclass(frozen=True)
class SecurityIntegrationArtifact:
    role: str
    relative_path: str
    size: int | None
    sha256: str | None

    def to_payload(self) -> dict[str, object]:
        _validate_artifact(self)
        return {
            "relative_path": self.relative_path,
            "role": self.role,
            "sha256": self.sha256,
            "size": self.size,
        }


@dataclass(frozen=True)
class SecurityIntegrationDocumentPlan:
    source_document_id: str
    document_id: str
    storage_id: str
    source_path_sha256: str
    plaintext_size: int
    plaintext_sha256: str
    container_name: str | None = None
    container_sha256: str | None = None

    def to_payload(self) -> dict[str, object]:
        _validate_document_plan(self)
        return {
            "container_name": self.container_name,
            "container_sha256": self.container_sha256,
            "document_id": self.document_id,
            "plaintext_sha256": self.plaintext_sha256,
            "plaintext_size": self.plaintext_size,
            "source_document_id": self.source_document_id,
            "source_path_sha256": self.source_path_sha256,
            "storage_id": self.storage_id,
        }


@dataclass(frozen=True)
class SecurityIntegrationJournalV1:
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_generation: int
    dmk_key_id: str
    dmk_key_generation: int
    database_key_id: str
    database_key_generation: int
    root_sha256: str
    revision: int
    phase: str
    artifacts: tuple[SecurityIntegrationArtifact, ...]
    documents: tuple[SecurityIntegrationDocumentPlan, ...]
    completed_checks: tuple[str, ...]
    error_code: str | None = None
    journal_version: int = SECURITY_INTEGRATION_JOURNAL_VERSION

    def to_payload(self) -> dict[str, object]:
        _validate_journal(self)
        return {
            "artifacts": [item.to_payload() for item in self.artifacts],
            "completed_checks": list(self.completed_checks),
            "database_context_id": self.database_context_id,
            "database_key_generation": self.database_key_generation,
            "database_key_id": self.database_key_id,
            "dmk_key_generation": self.dmk_key_generation,
            "dmk_key_id": self.dmk_key_id,
            "documents": [item.to_payload() for item in self.documents],
            "error_code": self.error_code,
            "installation_id": self.installation_id,
            "journal_version": self.journal_version,
            "migration_generation": self.migration_generation,
            "migration_id": self.migration_id,
            "phase": self.phase,
            "revision": self.revision,
            "root_sha256": self.root_sha256,
        }


@dataclass(frozen=True)
class SecurityIntegrationReplayAnchorV1:
    installation_id: str
    database_context_id: str
    migration_id: str
    migration_generation: int
    revision: int
    journal_revision: int
    journal_sha256: str
    root_sha256: str
    pending: "SecurityIntegrationReplayAnchorV1 | None" = None
    anchor_version: int = SECURITY_INTEGRATION_ANCHOR_VERSION

    def committed(self) -> "SecurityIntegrationReplayAnchorV1":
        return replace(self, pending=None)

    def to_payload(self) -> dict[str, object]:
        _validate_anchor(self)
        return {
            "anchor_version": self.anchor_version,
            "database_context_id": self.database_context_id,
            "installation_id": self.installation_id,
            "journal_revision": self.journal_revision,
            "journal_sha256": self.journal_sha256,
            "migration_generation": self.migration_generation,
            "migration_id": self.migration_id,
            "pending": (
                None if self.pending is None else self.pending.to_payload()
            ),
            "revision": self.revision,
            "root_sha256": self.root_sha256,
        }


class SecurityIntegrationJournalRepository:
    def __init__(
        self,
        path: Path,
        *,
        fsync: Callable[[int], None] = os.fsync,
    ) -> None:
        self.path = Path(path)
        self._fsync = fsync

    def exists(self) -> bool:
        return self.path.exists() or self.path.is_symlink()

    def preview_digest(
        self,
        state: SecurityIntegrationJournalV1,
        key: bytes,
    ) -> str:
        return hashlib.sha256(_encode_journal(state, key)).hexdigest()

    def create(
        self,
        state: SecurityIntegrationJournalV1,
        key: bytes,
    ) -> str:
        if self.exists():
            raise SecurityIntegrationError(
                "security_integration_journal_exists"
            )
        return self._publish(state, key, expected_digest=None)

    def replace(
        self,
        expected_digest: str,
        state: SecurityIntegrationJournalV1,
        key: bytes,
    ) -> str:
        _require_sha256(expected_digest)
        _current, observed_digest = self.load_with_digest(key)
        if not hmac.compare_digest(observed_digest, expected_digest):
            raise SecurityIntegrationError(
                "security_integration_journal_changed"
            )
        return self._publish(
            state,
            key,
            expected_digest=expected_digest,
        )

    def load_with_digest(
        self,
        key: bytes,
    ) -> tuple[SecurityIntegrationJournalV1, str]:
        encoded = _read_regular(self.path)
        state = _decode_journal(encoded, key)
        return state, hashlib.sha256(encoded).hexdigest()

    def _publish(
        self,
        state: SecurityIntegrationJournalV1,
        key: bytes,
        *,
        expected_digest: str | None,
    ) -> str:
        encoded = _encode_journal(state, key)
        _publish_atomic(
            self.path,
            encoded,
            fsync=self._fsync,
            before_replace=(
                None
                if expected_digest is None
                else lambda: self._require_digest(expected_digest, key)
            ),
            require_absent=expected_digest is None,
        )
        observed, digest = self.load_with_digest(key)
        if observed != state:
            raise SecurityIntegrationError(
                "security_integration_journal_publish_mismatch"
            )
        return digest

    def _require_digest(self, expected: str, key: bytes) -> None:
        _state, observed = self.load_with_digest(key)
        if not hmac.compare_digest(observed, expected):
            raise SecurityIntegrationError(
                "security_integration_journal_changed"
            )


class SecurityIntegrationReplayAnchorRepository:
    def __init__(
        self,
        path: Path,
        *,
        fsync: Callable[[int], None] = os.fsync,
    ) -> None:
        self.path = Path(path)
        self._fsync = fsync

    def exists(self) -> bool:
        return self.path.exists() or self.path.is_symlink()

    def read(self, key: bytes) -> SecurityIntegrationReplayAnchorV1:
        return _decode_anchor(_read_regular(self.path), key)

    def initialize(
        self,
        state: SecurityIntegrationReplayAnchorV1,
        key: bytes,
    ) -> SecurityIntegrationReplayAnchorV1:
        if self.exists():
            raise SecurityIntegrationError(
                "security_integration_anchor_exists"
            )
        self._publish(state, key, expected=None)
        return state

    def prepare(
        self,
        expected: SecurityIntegrationReplayAnchorV1,
        planned: SecurityIntegrationReplayAnchorV1,
        key: bytes,
    ) -> SecurityIntegrationReplayAnchorV1:
        current = self.read(key)
        if current != expected or current.pending is not None:
            raise SecurityIntegrationError(
                "security_integration_anchor_changed"
            )
        if (
            planned.pending is not None
            or planned.revision != expected.revision + 1
            or planned.journal_revision != expected.journal_revision + 1
        ):
            raise SecurityIntegrationError(
                "security_integration_anchor_plan_invalid"
            )
        prepared = replace(expected, pending=planned)
        self._publish(prepared, key, expected=expected)
        return prepared

    def commit(
        self,
        prepared: SecurityIntegrationReplayAnchorV1,
        key: bytes,
    ) -> SecurityIntegrationReplayAnchorV1:
        current = self.read(key)
        if current != prepared or prepared.pending is None:
            raise SecurityIntegrationError(
                "security_integration_anchor_changed"
            )
        committed = prepared.pending.committed()
        self._publish(committed, key, expected=prepared)
        return committed

    def abort_pending(
        self,
        prepared: SecurityIntegrationReplayAnchorV1,
        key: bytes,
    ) -> SecurityIntegrationReplayAnchorV1:
        current = self.read(key)
        if current != prepared or prepared.pending is None:
            raise SecurityIntegrationError(
                "security_integration_anchor_changed"
            )
        committed = prepared.committed()
        self._publish(committed, key, expected=prepared)
        return committed

    def _publish(
        self,
        state: SecurityIntegrationReplayAnchorV1,
        key: bytes,
        *,
        expected: SecurityIntegrationReplayAnchorV1 | None,
    ) -> None:
        encoded = _encode_anchor(state, key)
        _publish_atomic(
            self.path,
            encoded,
            fsync=self._fsync,
            before_replace=(
                None
                if expected is None
                else lambda: self._require_state(expected, key)
            ),
            require_absent=expected is None,
        )
        if self.read(key) != state:
            raise SecurityIntegrationError(
                "security_integration_anchor_publish_mismatch"
            )

    def _require_state(
        self,
        expected: SecurityIntegrationReplayAnchorV1,
        key: bytes,
    ) -> None:
        if self.read(key) != expected:
            raise SecurityIntegrationError(
                "security_integration_anchor_changed"
            )


def _encode_journal(
    state: SecurityIntegrationJournalV1,
    key: bytes,
) -> bytes:
    _validate_hmac_key(key)
    payload = state.to_payload()
    return _encode_authenticated(payload, key)


def _decode_journal(
    encoded: bytes,
    key: bytes,
) -> SecurityIntegrationJournalV1:
    payload = _decode_authenticated(encoded, key)
    required = {
        "artifacts",
        "completed_checks",
        "database_context_id",
        "database_key_generation",
        "database_key_id",
        "dmk_key_generation",
        "dmk_key_id",
        "documents",
        "error_code",
        "installation_id",
        "journal_version",
        "migration_generation",
        "migration_id",
        "phase",
        "revision",
        "root_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise SecurityIntegrationError(
            "security_integration_journal_fields_invalid"
        )
    try:
        state = SecurityIntegrationJournalV1(
            installation_id=payload["installation_id"],
            database_context_id=payload["database_context_id"],
            migration_id=payload["migration_id"],
            migration_generation=payload["migration_generation"],
            dmk_key_id=payload["dmk_key_id"],
            dmk_key_generation=payload["dmk_key_generation"],
            database_key_id=payload["database_key_id"],
            database_key_generation=payload["database_key_generation"],
            root_sha256=payload["root_sha256"],
            revision=payload["revision"],
            phase=payload["phase"],
            artifacts=tuple(
                SecurityIntegrationArtifact(**item)
                for item in payload["artifacts"]
            ),
            documents=tuple(
                SecurityIntegrationDocumentPlan(**item)
                for item in payload["documents"]
            ),
            completed_checks=tuple(payload["completed_checks"]),
            error_code=payload["error_code"],
            journal_version=payload["journal_version"],
        )
        _validate_journal(state)
        return state
    except SecurityIntegrationError:
        raise
    except Exception:
        raise SecurityIntegrationError(
            "security_integration_journal_fields_invalid"
        ) from None


def _encode_anchor(
    state: SecurityIntegrationReplayAnchorV1,
    key: bytes,
) -> bytes:
    _validate_hmac_key(key)
    return _encode_authenticated(state.to_payload(), key)


def _decode_anchor(
    encoded: bytes,
    key: bytes,
) -> SecurityIntegrationReplayAnchorV1:
    payload = _decode_authenticated(encoded, key)
    return _anchor_from_payload(payload)


def _anchor_from_payload(payload: object) -> SecurityIntegrationReplayAnchorV1:
    required = {
        "anchor_version",
        "database_context_id",
        "installation_id",
        "journal_revision",
        "journal_sha256",
        "migration_generation",
        "migration_id",
        "pending",
        "revision",
        "root_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise SecurityIntegrationError(
            "security_integration_anchor_fields_invalid"
        )
    try:
        pending_payload = payload["pending"]
        state = SecurityIntegrationReplayAnchorV1(
            installation_id=payload["installation_id"],
            database_context_id=payload["database_context_id"],
            migration_id=payload["migration_id"],
            migration_generation=payload["migration_generation"],
            revision=payload["revision"],
            journal_revision=payload["journal_revision"],
            journal_sha256=payload["journal_sha256"],
            root_sha256=payload["root_sha256"],
            pending=(
                None
                if pending_payload is None
                else _anchor_from_payload(pending_payload)
            ),
            anchor_version=payload["anchor_version"],
        )
        _validate_anchor(state)
        return state
    except SecurityIntegrationError:
        raise
    except Exception:
        raise SecurityIntegrationError(
            "security_integration_anchor_fields_invalid"
        ) from None


def _encode_authenticated(payload: object, key: bytes) -> bytes:
    payload_bytes = _canonical_bytes(payload)
    tag = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    return _canonical_bytes({"payload": payload, "tag": tag})


def _decode_authenticated(encoded: bytes, key: bytes) -> object:
    _validate_hmac_key(key)
    if not encoded or len(encoded) > _MAX_STATE_BYTES:
        raise SecurityIntegrationError(
            "security_integration_state_size_invalid"
        )
    try:
        envelope = json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SecurityIntegrationError(
            "security_integration_state_format_invalid"
        ) from None
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"payload", "tag"}
        or not isinstance(envelope["tag"], str)
        or not _SHA256.fullmatch(envelope["tag"])
        or _canonical_bytes(envelope) != encoded
    ):
        raise SecurityIntegrationError(
            "security_integration_state_format_invalid"
        )
    expected = hmac.new(
        key,
        _canonical_bytes(envelope["payload"]),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, envelope["tag"]):
        raise SecurityIntegrationError(
            "security_integration_state_auth_invalid"
        )
    return envelope["payload"]


def _validate_journal(state: SecurityIntegrationJournalV1) -> None:
    if state.journal_version != SECURITY_INTEGRATION_JOURNAL_VERSION:
        raise SecurityIntegrationError(
            "security_integration_journal_version_invalid"
        )
    _validate_identifiers(
        state.installation_id,
        state.database_context_id,
        state.migration_id,
        state.dmk_key_id,
        state.database_key_id,
    )
    if (
        type(state.migration_generation) is not int
        or state.migration_generation < 1
        or type(state.dmk_key_generation) is not int
        or state.dmk_key_generation < 1
        or type(state.database_key_generation) is not int
        or state.database_key_generation < 1
        or type(state.revision) is not int
        or state.revision < 0
    ):
        raise SecurityIntegrationError(
            "security_integration_journal_generation_invalid"
        )
    _require_sha256(state.root_sha256)
    if not isinstance(state.phase, str) or not _SAFE_CODE.fullmatch(state.phase):
        raise SecurityIntegrationError(
            "security_integration_journal_phase_invalid"
        )
    if not isinstance(state.artifacts, tuple):
        raise SecurityIntegrationError(
            "security_integration_journal_artifacts_invalid"
        )
    for item in state.artifacts:
        _validate_artifact(item)
    roles = tuple(item.role for item in state.artifacts)
    if len(set(roles)) != len(roles):
        raise SecurityIntegrationError(
            "security_integration_journal_artifacts_invalid"
        )
    if not isinstance(state.documents, tuple):
        raise SecurityIntegrationError(
            "security_integration_journal_documents_invalid"
        )
    for item in state.documents:
        _validate_document_plan(item)
    if (
        len({item.source_document_id for item in state.documents})
        != len(state.documents)
        or
        len({item.document_id for item in state.documents})
        != len(state.documents)
        or len({item.storage_id for item in state.documents})
        != len(state.documents)
    ):
        raise SecurityIntegrationError(
            "security_integration_journal_documents_invalid"
        )
    if (
        not isinstance(state.completed_checks, tuple)
        or len(set(state.completed_checks)) != len(state.completed_checks)
        or any(
            not isinstance(item, str) or not _SAFE_CODE.fullmatch(item)
            for item in state.completed_checks
        )
    ):
        raise SecurityIntegrationError(
            "security_integration_journal_checks_invalid"
        )
    if state.error_code is not None and (
        not isinstance(state.error_code, str)
        or not _SAFE_CODE.fullmatch(state.error_code)
    ):
        raise SecurityIntegrationError(
            "security_integration_journal_error_invalid"
        )


def _validate_anchor(state: SecurityIntegrationReplayAnchorV1) -> None:
    if state.anchor_version != SECURITY_INTEGRATION_ANCHOR_VERSION:
        raise SecurityIntegrationError(
            "security_integration_anchor_version_invalid"
        )
    _validate_identifiers(
        state.installation_id,
        state.database_context_id,
        state.migration_id,
    )
    if (
        type(state.migration_generation) is not int
        or state.migration_generation < 1
        or type(state.revision) is not int
        or state.revision < 0
        or type(state.journal_revision) is not int
        or state.journal_revision < 0
    ):
        raise SecurityIntegrationError(
            "security_integration_anchor_revision_invalid"
        )
    _require_sha256(state.journal_sha256)
    _require_sha256(state.root_sha256)
    if state.pending is not None:
        if state.pending.pending is not None:
            raise SecurityIntegrationError(
                "security_integration_anchor_pending_invalid"
            )
        _validate_anchor(state.pending)
        if (
            state.pending.revision != state.revision + 1
            or state.pending.journal_revision != state.journal_revision + 1
            or _anchor_context(state.pending) != _anchor_context(state)
        ):
            raise SecurityIntegrationError(
                "security_integration_anchor_pending_invalid"
            )


def _anchor_context(
    state: SecurityIntegrationReplayAnchorV1,
) -> tuple[object, ...]:
    return (
        state.installation_id,
        state.database_context_id,
        state.migration_id,
        state.migration_generation,
        state.root_sha256,
    )


def _validate_artifact(item: SecurityIntegrationArtifact) -> None:
    if (
        not isinstance(item, SecurityIntegrationArtifact)
        or not _SAFE_CODE.fullmatch(item.role)
        or not _SAFE_RELATIVE.fullmatch(item.relative_path)
        or (
            item.size is not None
            and (type(item.size) is not int or item.size < 0)
        )
        or (item.sha256 is None) != (item.size is None)
    ):
        raise SecurityIntegrationError(
            "security_integration_artifact_invalid"
        )
    if item.sha256 is not None:
        _require_sha256(item.sha256)


def _validate_document_plan(
    item: SecurityIntegrationDocumentPlan,
) -> None:
    if (
        not isinstance(item, SecurityIntegrationDocumentPlan)
        or not isinstance(item.source_document_id, str)
        or not item.source_document_id
        or len(item.source_document_id) > 128
        or not isinstance(item.document_id, str)
        or not item.document_id
        or len(item.document_id) > 128
        or not isinstance(item.storage_id, str)
        or len(item.storage_id) != 36
        or type(item.plaintext_size) is not int
        or item.plaintext_size < 0
        or (item.container_name is None) != (item.container_sha256 is None)
    ):
        raise SecurityIntegrationError(
            "security_integration_document_plan_invalid"
        )
    _require_sha256(item.source_path_sha256)
    _require_sha256(item.plaintext_sha256)
    if item.container_name is not None:
        if not _SAFE_RELATIVE.fullmatch(item.container_name):
            raise SecurityIntegrationError(
                "security_integration_document_plan_invalid"
            )
        _require_sha256(item.container_sha256)


def _validate_identifiers(*values: object) -> None:
    if any(
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or any(character.isspace() for character in value)
        for value in values
    ):
        raise SecurityIntegrationError(
            "security_integration_identifier_invalid"
        )


def _require_sha256(value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise SecurityIntegrationError(
            "security_integration_sha256_invalid"
        )


def _validate_hmac_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) != 32:
        raise SecurityIntegrationError(
            "security_integration_state_key_invalid"
        )


def _read_regular(path: Path) -> bytes:
    descriptor: int | None = None
    try:
        status = os.lstat(path)
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            raise SecurityIntegrationError(
                "security_integration_state_path_invalid"
            )
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (status.st_dev, status.st_ino):
            raise SecurityIntegrationError(
                "security_integration_state_changed"
            )
        encoded = os.read(descriptor, _MAX_STATE_BYTES + 1)
        if len(encoded) > _MAX_STATE_BYTES or len(encoded) != opened.st_size:
            raise SecurityIntegrationError(
                "security_integration_state_size_invalid"
            )
        return encoded
    except SecurityIntegrationError:
        raise
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_state_read_failed"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _publish_atomic(
    path: Path,
    encoded: bytes,
    *,
    fsync: Callable[[int], None],
    before_replace: Callable[[], None] | None,
    require_absent: bool,
) -> None:
    if not encoded or len(encoded) > _MAX_STATE_BYTES:
        raise SecurityIntegrationError(
            "security_integration_state_size_invalid"
        )
    candidate = path.with_name(f".{path.name}.candidate")
    if candidate.exists() or candidate.is_symlink():
        raise SecurityIntegrationError(
            "security_integration_state_candidate_exists"
        )
    descriptor: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(candidate, flags, 0o600)
        _write_all(descriptor, encoded)
        os.fchmod(descriptor, 0o600)
        fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        if before_replace is not None:
            before_replace()
        elif require_absent and (path.exists() or path.is_symlink()):
            raise SecurityIntegrationError(
                "security_integration_state_exists"
            )
        os.replace(candidate, path)
        _fsync_directory(path.parent, fsync)
    except SecurityIntegrationError:
        raise
    except OSError:
        raise SecurityIntegrationError(
            "security_integration_state_publish_failed"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if candidate.exists() and not candidate.is_symlink():
            try:
                candidate.unlink()
            except OSError:
                pass


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short write")
        offset += written


def _fsync_directory(
    directory: Path,
    fsync: Callable[[int], None],
) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise SecurityIntegrationError(
            "security_integration_state_format_invalid"
        ) from None
