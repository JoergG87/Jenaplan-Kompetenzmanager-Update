"""Authenticated, canonical and atomic migration-journal persistence."""

from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile
from types import MappingProxyType

from ..database_keys import DerivedDomainKey, MIGRATION_JOURNAL_AUTH_PURPOSE
from ..migration_journal import (
    MIGRATION_JOURNAL_AUTH_ALGORITHM,
    MIGRATION_JOURNAL_MAX_EVENTS,
    MIGRATION_JOURNAL_VERSION,
    MigrationFileEvidence,
    MigrationJournalError,
    MigrationJournalEvent,
    MigrationJournalState,
    MigrationPhase,
    validate_migration_journal,
)
from ..ports import FilePermissionManager


MIGRATION_JOURNAL_FILENAME = "database-migration-journal-v1.json"
_MAX_JOURNAL_BYTES = 512 * 1024
_TEMP_PREFIX = ".database-migration-journal-"


class AuthenticatedMigrationJournalRepository:
    def __init__(self, path: Path, permissions: FilePermissionManager) -> None:
        self.path = Path(path)
        self._permissions = permissions

    def create(
        self, state: MigrationJournalState, auth_key: DerivedDomainKey
    ) -> None:
        self._require_clean_directory(prepare=True)
        if self.path.exists() or self.path.is_symlink():
            raise MigrationJournalError("migration_journal_already_exists")
        data = self._encode(state, auth_key)
        temporary = self._write_temporary(data)
        try:
            try:
                os.link(temporary, self.path)
            except FileExistsError:
                raise MigrationJournalError("migration_journal_already_exists") from None
            temporary.unlink()
            self._permissions.secure_file(self.path)
            _fsync_directory(self.path.parent)
            if self._read_regular_bytes() != data:
                raise MigrationJournalError("migration_journal_publish_failed")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def load(self, auth_key: DerivedDomainKey) -> MigrationJournalState:
        self._require_clean_directory(prepare=False)
        if not self.path.exists() and not self.path.is_symlink():
            raise MigrationJournalError("migration_journal_missing")
        return self._decode(self._read_regular_bytes(), auth_key)

    def save(
        self,
        expected: MigrationJournalState,
        replacement: MigrationJournalState,
        auth_key: DerivedDomainKey,
    ) -> None:
        self._require_clean_directory(prepare=False)
        if replacement.revision != expected.revision + 1:
            raise MigrationJournalError("migration_journal_revision_invalid")
        expected_data = self._encode(expected, auth_key)
        current, identity = self._read_with_identity()
        if current != expected_data:
            raise MigrationJournalError("migration_journal_changed")
        replacement_data = self._encode(replacement, auth_key)
        temporary = self._write_temporary(replacement_data)
        try:
            current_again, identity_again = self._read_with_identity()
            if current_again != expected_data or identity_again != identity:
                raise MigrationJournalError("migration_journal_changed")
            os.replace(temporary, self.path)
            self._permissions.secure_file(self.path)
            _fsync_directory(self.path.parent)
            published = self._read_regular_bytes()
            if published != replacement_data:
                raise MigrationJournalError("migration_journal_publish_failed")
            self._decode(published, auth_key)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def delete_completed(
        self, expected: MigrationJournalState, auth_key: DerivedDomainKey
    ) -> bool:
        self._require_clean_directory(prepare=False)
        if not self.path.exists() and not self.path.is_symlink():
            return False
        if expected.phase is not MigrationPhase.COMPLETED:
            raise MigrationJournalError("migration_journal_delete_not_completed")
        expected_data = self._encode(expected, auth_key)
        current, identity = self._read_with_identity()
        if current != expected_data:
            raise MigrationJournalError("migration_journal_changed")
        self._decode(current, auth_key)
        status = self.path.lstat()
        if self.path.is_symlink() or (status.st_dev, status.st_ino) != identity:
            raise MigrationJournalError("migration_journal_changed")
        self.path.unlink()
        _fsync_directory(self.path.parent)
        return True

    def peek_context(self) -> tuple[str, str, int, int]:
        """Read only untrusted key-selection metadata; callers must authenticate next."""

        self._require_clean_directory(prepare=False)
        raw = self._read_regular_bytes()
        try:
            payload = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MigrationJournalError("migration_journal_format_invalid") from None
        if not isinstance(payload, dict):
            raise MigrationJournalError("migration_journal_format_invalid")
        try:
            return (
                str(payload["migration_id"]),
                str(payload["wrapping_dmk_key_id"]),
                int(payload["wrapping_dmk_generation"]),
                int(payload["auth_kdf_version"]),
            )
        except (KeyError, TypeError, ValueError):
            raise MigrationJournalError("migration_journal_format_invalid") from None

    def _require_clean_directory(self, *, prepare: bool) -> None:
        if prepare:
            try:
                self._permissions.prepare_directory(self.path.parent)
            except Exception:
                raise MigrationJournalError(
                    "migration_journal_directory_invalid"
                ) from None
        if self.path.parent.is_symlink() or not self.path.parent.is_dir():
            if not prepare and not self.path.parent.exists():
                return
            raise MigrationJournalError("migration_journal_directory_invalid")
        try:
            leftovers = tuple(
                child for child in self.path.parent.iterdir()
                if child.name.startswith(_TEMP_PREFIX)
            )
        except OSError:
            raise MigrationJournalError("migration_journal_directory_unreadable") from None
        if leftovers:
            raise MigrationJournalError("migration_journal_temporary_present")

    def _write_temporary(self, data: bytes) -> Path:
        descriptor, name = tempfile.mkstemp(
            prefix=_TEMP_PREFIX, suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(name)
        try:
            if os.name == "posix":
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            return temporary
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary.unlink(missing_ok=True)
            raise

    def _read_regular_bytes(self) -> bytes:
        value, _identity = self._read_with_identity()
        return value

    def _read_with_identity(self) -> tuple[bytes, tuple[int, int]]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags)
        except OSError:
            raise MigrationJournalError("migration_journal_unreadable") from None
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise MigrationJournalError("migration_journal_not_regular")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, 64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_JOURNAL_BYTES:
                    raise MigrationJournalError("migration_journal_size_invalid")
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        try:
            path_status = self.path.lstat()
        except OSError:
            raise MigrationJournalError("migration_journal_changed") from None
        identity = (before.st_dev, before.st_ino)
        if (
            self.path.is_symlink()
            or not stat.S_ISREG(path_status.st_mode)
            or identity != (after.st_dev, after.st_ino)
            or identity != (path_status.st_dev, path_status.st_ino)
            or before.st_size != after.st_size
        ):
            raise MigrationJournalError("migration_journal_changed")
        return b"".join(chunks), identity

    @classmethod
    def _encode(
        cls, state: MigrationJournalState, auth_key: DerivedDomainKey
    ) -> bytes:
        validate_migration_journal(state)
        cls._validate_auth_key(auth_key)
        payload = _state_payload(state)
        authenticated = _canonical_json(payload)
        tag = hmac.new(auth_key.key_material, authenticated, hashlib.sha256).digest()
        encoded = _canonical_json({**payload, "auth_tag": _b64_encode(tag)})
        if len(encoded) > _MAX_JOURNAL_BYTES:
            raise MigrationJournalError("migration_journal_size_invalid")
        return encoded

    @classmethod
    def _decode(
        cls, value: bytes, auth_key: DerivedDomainKey
    ) -> MigrationJournalState:
        cls._validate_auth_key(auth_key)
        if not value or len(value) > _MAX_JOURNAL_BYTES:
            raise MigrationJournalError("migration_journal_size_invalid")
        try:
            payload = json.loads(value.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MigrationJournalError("migration_journal_format_invalid") from None
        if not isinstance(payload, dict) or "auth_tag" not in payload:
            raise MigrationJournalError("migration_journal_format_invalid")
        tag = _b64_decode(payload.pop("auth_tag"))
        authenticated = _canonical_json(payload)
        expected = hmac.new(
            auth_key.key_material, authenticated, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(tag, expected):
            raise MigrationJournalError("migration_journal_authentication_failed")
        state = _state_from_payload(payload)
        if cls._encode(state, auth_key) != value:
            raise MigrationJournalError("migration_journal_not_canonical")
        return state

    @staticmethod
    def _validate_auth_key(auth_key: DerivedDomainKey) -> None:
        if (
            not isinstance(auth_key, DerivedDomainKey)
            or auth_key.purpose != MIGRATION_JOURNAL_AUTH_PURPOSE
            or auth_key.derivation_version != 1
            or not isinstance(auth_key.key_material, bytes)
            or len(auth_key.key_material) != 32
        ):
            raise MigrationJournalError("migration_journal_auth_key_invalid")


def _state_payload(state: MigrationJournalState) -> dict[str, object]:
    return {
        "auth_algorithm": state.auth_algorithm,
        "auth_kdf_version": state.auth_kdf_version,
        "completed_checks": list(state.completed_checks),
        "created_at": state.created_at,
        "data_context_id": state.data_context_id,
        "database_key_generation": state.database_key_generation,
        "database_key_id": state.database_key_id,
        "error_class": state.error_class,
        "file_evidence": {
            role: asdict(evidence)
            for role, evidence in sorted(state.file_evidence.items())
        },
        "history": [
            {
                "at": event.at,
                "completed_checks": list(event.completed_checks),
                "error_class": event.error_class,
                "phase": event.phase.value,
                "revision": event.revision,
            }
            for event in state.history
        ],
        "journal_version": state.journal_version,
        "migration_id": state.migration_id,
        "phase": state.phase.value,
        "planned_paths": dict(sorted(state.planned_paths.items())),
        "revision": state.revision,
        "updated_at": state.updated_at,
        "wrapping_dmk_generation": state.wrapping_dmk_generation,
        "wrapping_dmk_key_id": state.wrapping_dmk_key_id,
    }


def _state_from_payload(payload: object) -> MigrationJournalState:
    required = {
        "auth_algorithm",
        "auth_kdf_version",
        "completed_checks",
        "created_at",
        "data_context_id",
        "database_key_generation",
        "database_key_id",
        "error_class",
        "file_evidence",
        "history",
        "journal_version",
        "migration_id",
        "phase",
        "planned_paths",
        "revision",
        "updated_at",
        "wrapping_dmk_generation",
        "wrapping_dmk_key_id",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise MigrationJournalError("migration_journal_fields_invalid")
    try:
        raw_evidence = payload["file_evidence"]
        if not isinstance(raw_evidence, dict):
            raise TypeError
        evidence = {
            role: MigrationFileEvidence(**value)
            for role, value in raw_evidence.items()
        }
        raw_history = payload["history"]
        if not isinstance(raw_history, list) or len(raw_history) > MIGRATION_JOURNAL_MAX_EVENTS:
            raise TypeError
        history = tuple(
            MigrationJournalEvent(
                revision=item["revision"],
                phase=MigrationPhase(item["phase"]),
                at=item["at"],
                completed_checks=tuple(item["completed_checks"]),
                error_class=item["error_class"],
            )
            for item in raw_history
        )
        state = MigrationJournalState(
            journal_version=payload["journal_version"],
            migration_id=payload["migration_id"],
            data_context_id=payload["data_context_id"],
            database_key_id=payload["database_key_id"],
            database_key_generation=payload["database_key_generation"],
            wrapping_dmk_key_id=payload["wrapping_dmk_key_id"],
            wrapping_dmk_generation=payload["wrapping_dmk_generation"],
            auth_algorithm=payload["auth_algorithm"],
            auth_kdf_version=payload["auth_kdf_version"],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            revision=payload["revision"],
            phase=MigrationPhase(payload["phase"]),
            planned_paths=MappingProxyType(dict(payload["planned_paths"])),
            file_evidence=MappingProxyType(evidence),
            completed_checks=tuple(payload["completed_checks"]),
            error_class=payload["error_class"],
            history=history,
        )
        validate_migration_journal(state)
        return state
    except MigrationJournalError:
        raise
    except (KeyError, TypeError, ValueError):
        raise MigrationJournalError("migration_journal_fields_invalid") from None


def _canonical_json(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise MigrationJournalError("migration_journal_fields_invalid") from None


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise MigrationJournalError("migration_journal_auth_tag_invalid")
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (TypeError, ValueError):
        raise MigrationJournalError("migration_journal_auth_tag_invalid") from None
    if _b64_encode(decoded) != value or len(decoded) != 32:
        raise MigrationJournalError("migration_journal_auth_tag_invalid")
    return decoded


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
