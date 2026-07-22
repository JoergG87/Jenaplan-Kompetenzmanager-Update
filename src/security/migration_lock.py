"""Exclusive, identity-bound lock for isolated migration prototypes.

The lock file is durable evidence; the kernel ``flock`` is the concurrency
authority.  This module is deliberately not imported by product startup.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import threading
import time
from typing import Callable, Protocol, runtime_checkable

from .domain import validate_uuid4


MIGRATION_LOCK_FILENAME = "database-migration-v1.lock"
MIGRATION_LOCK_VERSION = 1
_MAX_LOCK_BYTES = 16 * 1024
_NONCE = re.compile(r"\A[0-9a-f]{64}\Z")
_PAYLOAD_STATUSES = frozenset({"held", "released"})
_CURRENT_PROCESS_START_IDENTITY = (
    f"self-start:{os.getpid()}:{time.monotonic_ns()}"
)
class MigrationLockError(RuntimeError):
    """Sanitized lock failure without paths, data, or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MigrationLockStatus(StrEnum):
    MISSING = "missing"
    HELD = "held"
    RELEASED = "released"
    STALE = "stale"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class MigrationLockOwner:
    lock_version: int
    installation_id: str
    database_context_id: str
    migration_id: str
    pid: int
    process_start_identity: str
    lock_nonce: str
    acquired_at: str
    updated_at: str
    root_sha256: str


@dataclass(frozen=True)
class MigrationLockInspection:
    status: MigrationLockStatus
    owner: MigrationLockOwner | None = None
    device_id: int | None = None
    file_id: int | None = None
    kernel_locked: bool | None = None
    error_code: str | None = None


@runtime_checkable
class MigrationLockPort(Protocol):
    """Platform-neutral contract used by migration orchestration."""

    def acquire(self) -> "MigrationLockPort": ...

    def verify_owner(self) -> bool: ...

    def release(self) -> bool: ...

    def inspect(self) -> MigrationLockInspection: ...


class ExclusiveMigrationLock:
    """POSIX/macOS prototype with explicit, evidence-bound stale takeover."""

    def __init__(
        self,
        root: Path,
        *,
        installation_id: str,
        database_context_id: str,
        migration_id: str,
        allowed_root: Path | None = None,
        now: Callable[[], datetime] | None = None,
        nonce_source: Callable[[], str] | None = None,
        process_exists: Callable[[int], bool | None] | None = None,
        process_identity: Callable[[int], str | None] | None = None,
    ) -> None:
        self.installation_id = _validated_context(installation_id)
        self.database_context_id = _validated_context(database_context_id)
        self.migration_id = _validated_context(migration_id)
        self._now = now or (lambda: datetime.now(UTC))
        self._nonce_source = nonce_source or (lambda: secrets.token_hex(32))
        self._process_exists = process_exists or _default_process_exists
        self._process_identity = process_identity or _default_process_start_identity

        self.root, self._root_identity = _validated_root(
            Path(root), Path(root) if allowed_root is None else Path(allowed_root)
        )
        self.path = self.root / MIGRATION_LOCK_FILENAME
        self._root_sha256 = hashlib.sha256(str(self.root).encode("utf-8")).hexdigest()
        self._descriptor: int | None = None
        self._owner: MigrationLockOwner | None = None
        self._file_identity: tuple[int, int] | None = None
        self._held = False
        self._released_once = False

    @property
    def owner(self) -> MigrationLockOwner:
        if self._owner is None:
            raise MigrationLockError("migration_lock_not_owned")
        return self._owner

    @property
    def file_identity(self) -> tuple[int, int]:
        if self._file_identity is None:
            raise MigrationLockError("migration_lock_not_owned")
        return self._file_identity

    def acquire(self) -> "ExclusiveMigrationLock":
        if self._held:
            self.verify_owner()
            return self
        owner = self._new_owner()
        root_descriptor = self._open_root_descriptor()
        descriptor: int | None = None
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(
                    MIGRATION_LOCK_FILENAME,
                    flags,
                    0o600,
                    dir_fd=root_descriptor,
                )
            except FileExistsError:
                descriptor = self._open_existing_descriptor(root_descriptor)
                return self._acquire_existing(
                    root_descriptor, descriptor, replacement_owner=owner
                )
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.EMLINK}:
                    raise MigrationLockError("migration_lock_symlink_rejected") from None
                raise MigrationLockError("migration_lock_create_failed") from None

            os.fchmod(descriptor, 0o600)
            identity = self._validate_descriptor_and_entry(
                root_descriptor, descriptor
            )
            if not _lock_created_descriptor(descriptor):
                raise MigrationLockError("migration_lock_busy")
            self._write_payload(descriptor, "held", owner)
            self._validate_entry_identity(root_descriptor, identity)
            os.fsync(root_descriptor)
            self._adopt(descriptor, owner, identity)
            descriptor = None
            return self
        except Exception:
            if descriptor is not None:
                _unlock_best_effort(descriptor)
                os.close(descriptor)
            raise
        finally:
            os.close(root_descriptor)

    def verify_owner(self) -> bool:
        if not self._held or self._descriptor is None or self._owner is None:
            raise MigrationLockError("migration_lock_not_owned")
        root_descriptor = self._open_root_descriptor()
        try:
            identity = self._validate_descriptor_and_entry(
                root_descriptor, self._descriptor
            )
            if identity != self._file_identity:
                raise MigrationLockError("migration_lock_file_changed")
            status, observed = self._read_payload(self._descriptor)
            if status != "held" or observed != self._owner:
                raise MigrationLockError("migration_lock_owner_mismatch")
            actual_identity = self._process_identity(os.getpid())
            if actual_identity is None:
                raise MigrationLockError("migration_lock_process_identity_unavailable")
            if actual_identity != self._owner.process_start_identity:
                raise MigrationLockError("migration_lock_process_identity_changed")
            return True
        finally:
            os.close(root_descriptor)

    def release(self) -> bool:
        if not self._held or self._descriptor is None or self._owner is None:
            if self._released_once:
                return False
            raise MigrationLockError("migration_lock_not_owned")
        try:
            self.verify_owner()
            released_owner = replace(
                self._owner, updated_at=self._utc_now()
            )
            self._write_payload(self._descriptor, "released", released_owner)
            root_descriptor = self._open_root_descriptor()
            try:
                self._validate_entry_identity(root_descriptor, self.file_identity)
                os.fsync(root_descriptor)
            finally:
                os.close(root_descriptor)
            self._owner = released_owner
        except Exception:
            self._abandon_descriptor()
            raise
        assert self._descriptor is not None
        _unlock(self._descriptor)
        os.close(self._descriptor)
        self._descriptor = None
        self._held = False
        self._released_once = True
        return True

    def inspect(self) -> MigrationLockInspection:
        if self._held:
            try:
                self.verify_owner()
            except MigrationLockError as error:
                return MigrationLockInspection(
                    MigrationLockStatus.BLOCKED,
                    self._owner,
                    *(self._file_identity or (None, None)),
                    True,
                    error.code,
                )
            return MigrationLockInspection(
                MigrationLockStatus.HELD,
                self._owner,
                *self.file_identity,
                True,
            )

        root_descriptor: int | None = None
        descriptor: int | None = None
        identity: tuple[int, int] | None = None
        try:
            root_descriptor = self._open_root_descriptor()
            try:
                descriptor = self._open_existing_descriptor(root_descriptor)
            except FileNotFoundError:
                return MigrationLockInspection(MigrationLockStatus.MISSING)
            identity = self._validate_descriptor_and_entry(root_descriptor, descriptor)
            status, owner = self._read_payload(descriptor)
            if not self._context_matches(owner, allow_different_migration=True):
                raise MigrationLockError("migration_lock_context_mismatch")
            kernel_locked = not _try_lock(descriptor)
            if not kernel_locked:
                _unlock(descriptor)
            if status == "released":
                if kernel_locked:
                    return MigrationLockInspection(
                        MigrationLockStatus.BLOCKED,
                        owner,
                        *identity,
                        True,
                        "migration_lock_released_but_kernel_locked",
                    )
                return MigrationLockInspection(
                    MigrationLockStatus.RELEASED, owner, *identity, False
                )
            if kernel_locked:
                return MigrationLockInspection(
                    MigrationLockStatus.HELD, owner, *identity, True
                )
            stale, code = self._stale_state(owner)
            return MigrationLockInspection(
                MigrationLockStatus.STALE if stale else MigrationLockStatus.BLOCKED,
                owner,
                *identity,
                False,
                code,
            )
        except FileNotFoundError:
            return MigrationLockInspection(MigrationLockStatus.MISSING)
        except MigrationLockError as error:
            return MigrationLockInspection(
                MigrationLockStatus.BLOCKED,
                None,
                *(identity or (None, None)),
                None,
                error.code,
            )
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if root_descriptor is not None:
                os.close(root_descriptor)

    def take_over_stale(
        self,
        *,
        expected_owner: MigrationLockOwner,
        expected_device_id: int,
        expected_file_id: int,
        recovery_evidence_validator: Callable[
            [MigrationLockOwner, tuple[int, int]], bool
        ]
        | None = None,
    ) -> "ExclusiveMigrationLock":
        if self._held:
            raise MigrationLockError("migration_lock_already_owned")
        root_descriptor = self._open_root_descriptor()
        descriptor: int | None = None
        try:
            descriptor = self._open_existing_descriptor(root_descriptor)
            identity = self._validate_descriptor_and_entry(root_descriptor, descriptor)
            if not _try_lock(descriptor):
                raise MigrationLockError("migration_lock_busy")
            status, previous = self._read_payload(descriptor)
            if (
                status != "held"
                or not isinstance(expected_owner, MigrationLockOwner)
                or previous != expected_owner
                or identity != (expected_device_id, expected_file_id)
            ):
                raise MigrationLockError("migration_lock_stale_evidence_mismatch")
            if not self._context_matches(previous, allow_different_migration=False):
                raise MigrationLockError("migration_lock_context_mismatch")
            stale, code = self._stale_state(previous)
            if not stale:
                raise MigrationLockError(code or "migration_lock_stale_not_proven")
            if recovery_evidence_validator is None:
                raise MigrationLockError(
                    "migration_lock_recovery_evidence_required"
                )
            try:
                evidence_valid = recovery_evidence_validator(previous, identity) is True
            except Exception:
                evidence_valid = False
            if not evidence_valid:
                raise MigrationLockError(
                    "migration_lock_recovery_evidence_invalid"
                )
            replacement_owner = self._new_owner()
            self._write_payload(descriptor, "held", replacement_owner)
            self._validate_entry_identity(root_descriptor, identity)
            os.fsync(root_descriptor)
            self._adopt(descriptor, replacement_owner, identity)
            descriptor = None
            return self
        except FileNotFoundError:
            raise MigrationLockError("migration_lock_missing") from None
        except Exception:
            if descriptor is not None:
                _unlock_best_effort(descriptor)
            raise
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(root_descriptor)

    def _acquire_existing(
        self,
        root_descriptor: int,
        descriptor: int,
        *,
        replacement_owner: MigrationLockOwner,
    ) -> "ExclusiveMigrationLock":
        identity = self._validate_descriptor_and_entry(root_descriptor, descriptor)
        if not _try_lock(descriptor):
            raise MigrationLockError("migration_lock_busy")
        status, previous = self._read_payload(descriptor)
        if not self._context_matches(previous, allow_different_migration=True):
            raise MigrationLockError("migration_lock_context_mismatch")
        if status == "held":
            stale, code = self._stale_state(previous)
            if stale:
                raise MigrationLockError("migration_lock_stale_takeover_required")
            raise MigrationLockError(code or "migration_lock_state_blocked")
        self._write_payload(descriptor, "held", replacement_owner)
        self._validate_entry_identity(root_descriptor, identity)
        os.fsync(root_descriptor)
        self._adopt(descriptor, replacement_owner, identity)
        return self

    def _new_owner(self) -> MigrationLockOwner:
        process_identity = self._process_identity(os.getpid())
        if process_identity is None:
            raise MigrationLockError("migration_lock_process_identity_unavailable")
        _validate_process_identity(process_identity)
        nonce = self._nonce_source()
        if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
            raise MigrationLockError("migration_lock_nonce_invalid")
        timestamp = self._utc_now()
        return MigrationLockOwner(
            MIGRATION_LOCK_VERSION,
            self.installation_id,
            self.database_context_id,
            self.migration_id,
            os.getpid(),
            process_identity,
            nonce,
            timestamp,
            timestamp,
            self._root_sha256,
        )

    def _stale_state(self, owner: MigrationLockOwner) -> tuple[bool, str | None]:
        exists = self._process_exists(owner.pid)
        if exists is False:
            return True, None
        if exists is None:
            return False, "migration_lock_process_state_unavailable"
        actual_identity = self._process_identity(owner.pid)
        if actual_identity is None:
            return False, "migration_lock_process_identity_unavailable"
        if actual_identity == owner.process_start_identity:
            return False, "migration_lock_owner_still_alive"
        return True, None

    def _context_matches(
        self, owner: MigrationLockOwner, *, allow_different_migration: bool
    ) -> bool:
        return (
            owner.installation_id == self.installation_id
            and owner.database_context_id == self.database_context_id
            and owner.root_sha256 == self._root_sha256
            and (
                allow_different_migration
                or owner.migration_id == self.migration_id
            )
        )

    def _adopt(
        self,
        descriptor: int,
        owner: MigrationLockOwner,
        identity: tuple[int, int],
    ) -> None:
        self._descriptor = descriptor
        self._owner = owner
        self._file_identity = identity
        self._held = True
        self._released_once = False

    def _open_root_descriptor(self) -> int:
        self._assert_root_current()
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.root, flags)
        except OSError:
            raise MigrationLockError("migration_lock_root_invalid") from None
        status = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(status.st_mode)
            or (status.st_dev, status.st_ino) != self._root_identity
        ):
            os.close(descriptor)
            raise MigrationLockError("migration_lock_root_changed")
        return descriptor

    def _assert_root_current(self) -> None:
        try:
            status = self.root.lstat()
        except OSError:
            raise MigrationLockError("migration_lock_root_invalid") from None
        if (
            self.root.is_symlink()
            or not stat.S_ISDIR(status.st_mode)
            or (status.st_dev, status.st_ino) != self._root_identity
        ):
            raise MigrationLockError("migration_lock_root_changed")

    @staticmethod
    def _open_existing_descriptor(root_descriptor: int) -> int:
        flags = os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            return os.open(MIGRATION_LOCK_FILENAME, flags, dir_fd=root_descriptor)
        except FileNotFoundError:
            raise
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.EMLINK}:
                raise MigrationLockError("migration_lock_symlink_rejected") from None
            raise MigrationLockError("migration_lock_unreadable") from None

    def _validate_descriptor_and_entry(
        self, root_descriptor: int, descriptor: int
    ) -> tuple[int, int]:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise MigrationLockError("migration_lock_not_regular")
        if status.st_ino == 0:
            raise MigrationLockError("migration_lock_identity_unavailable")
        if status.st_nlink != 1:
            raise MigrationLockError("migration_lock_link_count_invalid")
        if os.name == "posix":
            if status.st_uid != os.geteuid():
                raise MigrationLockError("migration_lock_owner_invalid")
            if stat.S_IMODE(status.st_mode) != 0o600:
                raise MigrationLockError("migration_lock_permissions_invalid")
        identity = (int(status.st_dev), int(status.st_ino))
        self._validate_entry_identity(root_descriptor, identity)
        return identity

    @staticmethod
    def _validate_entry_identity(
        root_descriptor: int, expected: tuple[int, int]
    ) -> None:
        try:
            status = os.stat(
                MIGRATION_LOCK_FILENAME,
                dir_fd=root_descriptor,
                follow_symlinks=False,
            )
        except OSError:
            raise MigrationLockError("migration_lock_file_changed") from None
        if stat.S_ISLNK(status.st_mode):
            raise MigrationLockError("migration_lock_symlink_rejected")
        if not stat.S_ISREG(status.st_mode) or (
            int(status.st_dev), int(status.st_ino)
        ) != expected:
            raise MigrationLockError("migration_lock_file_changed")

    @staticmethod
    def _write_payload(
        descriptor: int, status: str, owner: MigrationLockOwner
    ) -> None:
        data = _encode_payload(status, owner)
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            written = 0
            while written < len(data):
                count = os.write(descriptor, data[written:])
                if count <= 0:
                    raise OSError("short write")
                written += count
            os.fsync(descriptor)
        except OSError:
            raise MigrationLockError("migration_lock_write_failed") from None

    @staticmethod
    def _read_payload(descriptor: int) -> tuple[str, MigrationLockOwner]:
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, 4096)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_LOCK_BYTES:
                    raise MigrationLockError("migration_lock_payload_too_large")
                chunks.append(chunk)
        except MigrationLockError:
            raise
        except OSError:
            raise MigrationLockError("migration_lock_unreadable") from None
        return _decode_payload(b"".join(chunks))

    def _utc_now(self) -> str:
        value = self._now()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise MigrationLockError("migration_lock_clock_invalid")
        return (
            value.astimezone(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _abandon_descriptor(self) -> None:
        if self._descriptor is not None:
            _unlock_best_effort(self._descriptor)
            os.close(self._descriptor)
        self._descriptor = None
        self._held = False

    def __enter__(self) -> "ExclusiveMigrationLock":
        return self.acquire()

    def __exit__(self, *_args: object) -> None:
        self.release()

    def __del__(self) -> None:  # pragma: no cover - process cleanup safeguard
        descriptor = getattr(self, "_descriptor", None)
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


@dataclass(frozen=True)
class _InMemoryMigrationLockRecord:
    status: MigrationLockStatus
    owner: MigrationLockOwner
    device_id: int
    file_id: int
    owner_token: object


class InMemoryMigrationLock:
    """Thread-safe fake preserving ownership and foreign-release semantics."""

    _registry_lock = threading.RLock()
    _registry: dict[str, _InMemoryMigrationLockRecord] = {}
    _next_file_id = 1

    def __init__(
        self,
        *,
        installation_id: str,
        database_context_id: str,
        migration_id: str,
        namespace: str | None = None,
        now: Callable[[], datetime] | None = None,
        nonce_source: Callable[[], str] | None = None,
        process_identity: Callable[[int], str | None] | None = None,
    ) -> None:
        self.installation_id = _validated_context(installation_id)
        self.database_context_id = _validated_context(database_context_id)
        self.migration_id = _validated_context(migration_id)
        self._namespace = namespace or self.database_context_id
        if not isinstance(self._namespace, str) or not self._namespace:
            raise MigrationLockError("migration_lock_namespace_invalid")
        self._now = now or (lambda: datetime.now(UTC))
        self._nonce_source = nonce_source or (lambda: secrets.token_hex(32))
        self._process_identity = process_identity or _default_process_start_identity
        self._root_sha256 = hashlib.sha256(
            f"memory:{self._namespace}".encode("utf-8")
        ).hexdigest()
        self._owner_token = object()
        self._owner: MigrationLockOwner | None = None
        self._file_identity: tuple[int, int] | None = None
        self._held = False
        self._released_once = False

    @property
    def owner(self) -> MigrationLockOwner:
        if self._owner is None:
            raise MigrationLockError("migration_lock_not_owned")
        return self._owner

    @property
    def file_identity(self) -> tuple[int, int]:
        if self._file_identity is None:
            raise MigrationLockError("migration_lock_not_owned")
        return self._file_identity

    def acquire(self) -> "InMemoryMigrationLock":
        with self._registry_lock:
            if self._held:
                self.verify_owner()
                return self
            record = self._registry.get(self._namespace)
            if record is not None and not self._context_matches(record.owner):
                raise MigrationLockError("migration_lock_context_mismatch")
            if record is not None and record.status is MigrationLockStatus.HELD:
                raise MigrationLockError("migration_lock_busy")
            owner = self._new_owner()
            if record is None:
                file_identity = (0, type(self)._next_file_id)
                type(self)._next_file_id += 1
            else:
                file_identity = (record.device_id, record.file_id)
            self._registry[self._namespace] = _InMemoryMigrationLockRecord(
                MigrationLockStatus.HELD,
                owner,
                *file_identity,
                self._owner_token,
            )
            self._owner = owner
            self._file_identity = file_identity
            self._held = True
            self._released_once = False
            return self

    def verify_owner(self) -> bool:
        with self._registry_lock:
            if not self._held or self._owner is None:
                raise MigrationLockError("migration_lock_not_owned")
            record = self._registry.get(self._namespace)
            if (
                record is None
                or record.status is not MigrationLockStatus.HELD
                or record.owner_token is not self._owner_token
                or record.owner != self._owner
                or (record.device_id, record.file_id) != self._file_identity
            ):
                raise MigrationLockError("migration_lock_owner_mismatch")
            actual_identity = self._process_identity(os.getpid())
            if actual_identity is None:
                raise MigrationLockError(
                    "migration_lock_process_identity_unavailable"
                )
            if actual_identity != self._owner.process_start_identity:
                raise MigrationLockError("migration_lock_process_identity_changed")
            return True

    def release(self) -> bool:
        with self._registry_lock:
            if not self._held or self._owner is None:
                if self._released_once:
                    return False
                raise MigrationLockError("migration_lock_not_owned")
            self.verify_owner()
            released_owner = replace(self._owner, updated_at=self._utc_now())
            assert self._file_identity is not None
            self._registry[self._namespace] = _InMemoryMigrationLockRecord(
                MigrationLockStatus.RELEASED,
                released_owner,
                *self._file_identity,
                self._owner_token,
            )
            self._owner = released_owner
            self._held = False
            self._released_once = True
            return True

    def inspect(self) -> MigrationLockInspection:
        with self._registry_lock:
            record = self._registry.get(self._namespace)
            if record is None:
                return MigrationLockInspection(MigrationLockStatus.MISSING)
            if not self._context_matches(record.owner):
                return MigrationLockInspection(
                    MigrationLockStatus.BLOCKED,
                    record.owner,
                    record.device_id,
                    record.file_id,
                    record.status is MigrationLockStatus.HELD,
                    "migration_lock_context_mismatch",
                )
            return MigrationLockInspection(
                record.status,
                record.owner,
                record.device_id,
                record.file_id,
                record.status is MigrationLockStatus.HELD,
            )

    def _context_matches(self, owner: MigrationLockOwner) -> bool:
        return (
            owner.installation_id == self.installation_id
            and owner.database_context_id == self.database_context_id
            and owner.root_sha256 == self._root_sha256
        )

    def _new_owner(self) -> MigrationLockOwner:
        process_identity = self._process_identity(os.getpid())
        if process_identity is None:
            raise MigrationLockError("migration_lock_process_identity_unavailable")
        _validate_process_identity(process_identity)
        nonce = self._nonce_source()
        if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
            raise MigrationLockError("migration_lock_nonce_invalid")
        timestamp = self._utc_now()
        return MigrationLockOwner(
            MIGRATION_LOCK_VERSION,
            self.installation_id,
            self.database_context_id,
            self.migration_id,
            os.getpid(),
            process_identity,
            nonce,
            timestamp,
            timestamp,
            self._root_sha256,
        )

    def _utc_now(self) -> str:
        value = self._now()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise MigrationLockError("migration_lock_clock_invalid")
        return (
            value.astimezone(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )


class UnsupportedMigrationLock:
    """Fail-closed adapter for platforms without a reviewed lock backend."""

    error_code = "migration_lock_platform_unsupported"

    def acquire(self) -> "UnsupportedMigrationLock":
        raise MigrationLockError(self.error_code)

    def verify_owner(self) -> bool:
        raise MigrationLockError(self.error_code)

    def release(self) -> bool:
        raise MigrationLockError(self.error_code)

    def inspect(self) -> MigrationLockInspection:
        return MigrationLockInspection(
            MigrationLockStatus.BLOCKED,
            error_code=self.error_code,
        )


def _validated_context(value: str) -> str:
    try:
        return validate_uuid4(value)
    except Exception:
        raise MigrationLockError("migration_lock_context_invalid") from None


def _validated_root(root: Path, allowed_root: Path) -> tuple[Path, tuple[int, int]]:
    raw_root = root.expanduser()
    raw_allowed = allowed_root.expanduser()
    if raw_root.is_symlink():
        raise MigrationLockError("migration_lock_root_symlink_rejected")
    if raw_allowed.is_symlink():
        raise MigrationLockError("migration_lock_allowed_root_symlink_rejected")
    try:
        canonical = raw_root.resolve(strict=True)
        allowed = raw_allowed.resolve(strict=True)
        status = canonical.lstat()
    except OSError:
        raise MigrationLockError("migration_lock_root_invalid") from None
    if not stat.S_ISDIR(status.st_mode):
        raise MigrationLockError("migration_lock_root_invalid")
    if canonical != allowed and not canonical.is_relative_to(allowed):
        raise MigrationLockError("migration_lock_root_outside_allowed")
    if status.st_ino == 0:
        raise MigrationLockError("migration_lock_root_identity_unavailable")
    if os.name == "posix":
        if status.st_uid != os.geteuid():
            raise MigrationLockError("migration_lock_root_owner_invalid")
        if stat.S_IMODE(status.st_mode) != 0o700:
            raise MigrationLockError("migration_lock_root_permissions_invalid")
    return canonical, (int(status.st_dev), int(status.st_ino))


def _owner_payload(status: str, owner: MigrationLockOwner) -> dict[str, object]:
    return {
        "acquired_at": owner.acquired_at,
        "database_context_id": owner.database_context_id,
        "installation_id": owner.installation_id,
        "lock_nonce": owner.lock_nonce,
        "lock_version": owner.lock_version,
        "migration_id": owner.migration_id,
        "pid": owner.pid,
        "process_start_identity": owner.process_start_identity,
        "root_sha256": owner.root_sha256,
        "status": status,
        "updated_at": owner.updated_at,
    }


def _encode_payload(status: str, owner: MigrationLockOwner) -> bytes:
    if status not in _PAYLOAD_STATUSES:
        raise MigrationLockError("migration_lock_status_invalid")
    _validate_owner(owner)
    try:
        encoded = json.dumps(
            _owner_payload(status, owner),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError):
        raise MigrationLockError("migration_lock_payload_invalid") from None
    if len(encoded) > _MAX_LOCK_BYTES:
        raise MigrationLockError("migration_lock_payload_too_large")
    return encoded


def _decode_payload(value: bytes) -> tuple[str, MigrationLockOwner]:
    if not value or len(value) > _MAX_LOCK_BYTES:
        raise MigrationLockError("migration_lock_payload_invalid")
    try:
        payload = json.loads(value.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError):
        raise MigrationLockError("migration_lock_payload_invalid") from None
    expected = {
        "acquired_at",
        "database_context_id",
        "installation_id",
        "lock_nonce",
        "lock_version",
        "migration_id",
        "pid",
        "process_start_identity",
        "root_sha256",
        "status",
        "updated_at",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise MigrationLockError("migration_lock_payload_invalid")
    try:
        owner = MigrationLockOwner(
            lock_version=payload["lock_version"],
            installation_id=payload["installation_id"],
            database_context_id=payload["database_context_id"],
            migration_id=payload["migration_id"],
            pid=payload["pid"],
            process_start_identity=payload["process_start_identity"],
            lock_nonce=payload["lock_nonce"],
            acquired_at=payload["acquired_at"],
            updated_at=payload["updated_at"],
            root_sha256=payload["root_sha256"],
        )
        status = payload["status"]
        if not isinstance(status, str) or status not in _PAYLOAD_STATUSES:
            raise MigrationLockError("migration_lock_status_invalid")
        _validate_owner(owner)
    except MigrationLockError:
        raise
    except (TypeError, ValueError):
        raise MigrationLockError("migration_lock_payload_invalid") from None
    if _encode_payload(status, owner) != value:
        raise MigrationLockError("migration_lock_payload_not_canonical")
    return status, owner


def _validate_owner(owner: MigrationLockOwner) -> None:
    if type(owner.lock_version) is not int or owner.lock_version != MIGRATION_LOCK_VERSION:
        raise MigrationLockError("migration_lock_version_unsupported")
    for value in (
        owner.installation_id,
        owner.database_context_id,
        owner.migration_id,
    ):
        _validated_context(value)
    if type(owner.pid) is not int or owner.pid <= 0:
        raise MigrationLockError("migration_lock_pid_invalid")
    _validate_process_identity(owner.process_start_identity)
    if not isinstance(owner.lock_nonce, str) or not _NONCE.fullmatch(owner.lock_nonce):
        raise MigrationLockError("migration_lock_nonce_invalid")
    acquired = _parse_utc(owner.acquired_at)
    updated = _parse_utc(owner.updated_at)
    if updated < acquired:
        raise MigrationLockError("migration_lock_timestamp_invalid")
    if (
        not isinstance(owner.root_sha256, str)
        or len(owner.root_sha256) != 64
        or any(character not in "0123456789abcdef" for character in owner.root_sha256)
    ):
        raise MigrationLockError("migration_lock_root_binding_invalid")


def _validate_process_identity(value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 256
        or any(ord(character) < 32 for character in value)
    ):
        raise MigrationLockError("migration_lock_process_identity_invalid")


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise MigrationLockError("migration_lock_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MigrationLockError("migration_lock_timestamp_invalid") from None
    if (
        parsed.tzinfo is None
        or parsed.microsecond != 0
        or parsed.astimezone(UTC).isoformat().replace("+00:00", "Z") != value
    ):
        raise MigrationLockError("migration_lock_timestamp_invalid")
    return parsed.astimezone(UTC)


def _try_lock(descriptor: int) -> bool:
    try:
        import fcntl
    except ImportError:
        raise MigrationLockError("migration_lock_platform_unsupported") from None
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    except OSError:
        raise MigrationLockError("migration_lock_kernel_failed") from None


def _lock_created_descriptor(descriptor: int) -> bool:
    for attempt in range(20):
        if _try_lock(descriptor):
            return True
        if attempt != 19:
            time.sleep(0.001)
    return False


def _unlock(descriptor: int) -> None:
    try:
        import fcntl
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    except ImportError:
        raise MigrationLockError("migration_lock_platform_unsupported") from None
    except OSError:
        raise MigrationLockError("migration_lock_kernel_failed") from None


def _unlock_best_effort(descriptor: int) -> None:
    try:
        _unlock(descriptor)
    except MigrationLockError:
        pass


def _default_process_exists(pid: int) -> bool | None:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None


def _default_process_start_identity(pid: int) -> str | None:
    proc_stat = Path(f"/proc/{pid}/stat")
    try:
        raw = proc_stat.read_text(encoding="ascii")
        closing = raw.rfind(")")
        fields = raw[closing + 2 :].split()
        if closing > 0 and len(fields) > 19:
            return f"proc-start:{fields[19]}"
    except (OSError, UnicodeError):
        pass
    try:
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return _CURRENT_PROCESS_START_IDENTITY if pid == os.getpid() else None
    value = result.stdout.strip()
    if result.returncode == 0 and value:
        return f"ps-start:{value}"
    return _CURRENT_PROCESS_START_IDENTITY if pid == os.getpid() else None


__all__ = [
    "MIGRATION_LOCK_FILENAME",
    "ExclusiveMigrationLock",
    "InMemoryMigrationLock",
    "MigrationLockError",
    "MigrationLockInspection",
    "MigrationLockOwner",
    "MigrationLockPort",
    "MigrationLockStatus",
    "UnsupportedMigrationLock",
]
