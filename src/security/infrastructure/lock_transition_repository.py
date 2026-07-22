"""Immutable per-entry persistence for authenticated migration lock transitions."""

from __future__ import annotations

import os
from pathlib import Path
import re
import stat
from typing import Callable

from src.security.database_keys import DerivedDomainKey
from src.security.lock_transition import (
    AuthenticatedLockTransition,
    AuthenticatedLockTransitionChain,
    LockTransitionError,
    validate_lock_transition_chain,
)


LOCK_TRANSITION_DIRECTORY = "database-migration-lock-transitions-v1"
_ENTRY_NAME = re.compile(r"\A[0-9]{20}\.json\Z")


class AppendOnlyLockTransitionRepository:
    def __init__(
        self,
        root: Path,
        *,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        self.root = Path(root)
        self.path = self.root / LOCK_TRANSITION_DIRECTORY
        self._fault = fault_injector or (lambda _point: None)

    def load(
        self,
        auth_key: DerivedDomainKey,
        *,
        expected_head_digest: str | None = None,
        expected_sequence: int | None = None,
    ) -> AuthenticatedLockTransitionChain:
        if expected_head_digest is None or expected_sequence is None:
            raise LockTransitionError("lock_transition_replay_expectation_required")
        if not self.path.exists():
            chain = AuthenticatedLockTransitionChain()
            validate_lock_transition_chain(
                chain,
                auth_key,
                expected_head_digest=expected_head_digest,
                expected_sequence=expected_sequence,
            )
            return chain
        if self.path.is_symlink() or not self.path.is_dir():
            raise LockTransitionError("lock_transition_store_invalid")
        entries: list[AuthenticatedLockTransition] = []
        names = sorted(item.name for item in self.path.iterdir())
        if any(not _ENTRY_NAME.fullmatch(name) for name in names):
            raise LockTransitionError("lock_transition_store_unknown_entry")
        for expected, name in enumerate(names, start=1):
            if name != _entry_name(expected):
                raise LockTransitionError("lock_transition_chain_broken")
            candidate = self.path / name
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(candidate, flags)
            except OSError:
                raise LockTransitionError("lock_transition_store_unreadable") from None
            try:
                status = os.fstat(descriptor)
                if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
                    raise LockTransitionError("lock_transition_store_invalid")
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = os.read(descriptor, 4096)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 16 * 1024:
                        raise LockTransitionError("lock_transition_size_invalid")
                    chunks.append(chunk)
            finally:
                os.close(descriptor)
            entries.append(AuthenticatedLockTransition.from_bytes(b"".join(chunks)))
        chain = AuthenticatedLockTransitionChain(tuple(entries))
        validate_lock_transition_chain(
            chain,
            auth_key,
            expected_head_digest=expected_head_digest,
            expected_sequence=expected_sequence,
        )
        return chain

    def append(
        self,
        expected: AuthenticatedLockTransitionChain,
        replacement: AuthenticatedLockTransitionChain,
        auth_key: DerivedDomainKey,
    ) -> AuthenticatedLockTransitionChain:
        validate_lock_transition_chain(expected, auth_key)
        validate_lock_transition_chain(replacement, auth_key)
        if (
            len(replacement.entries) != len(expected.entries) + 1
            or replacement.entries[:-1] != expected.entries
        ):
            raise LockTransitionError("lock_transition_append_invalid")
        observed = self.load(
            auth_key,
            expected_head_digest=expected.head_digest,
            expected_sequence=expected.sequence,
        )
        if observed != expected:
            raise LockTransitionError("lock_transition_concurrent_change")
        self._fault("before_persist")
        self._ensure_directory()
        entry = replacement.entries[-1]
        target = self.path / _entry_name(entry.sequence)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags, 0o600)
        except FileExistsError:
            raise LockTransitionError("lock_transition_concurrent_change") from None
        except OSError:
            raise LockTransitionError("lock_transition_persist_failed") from None
        try:
            data = entry.to_bytes()
            written = 0
            while written < len(data):
                count = os.write(descriptor, data[written:])
                if count <= 0:
                    raise OSError
                written += count
            os.fsync(descriptor)
        except OSError:
            raise LockTransitionError("lock_transition_persist_failed") from None
        finally:
            os.close(descriptor)
        self._fault("after_entry_fsync")
        directory = os.open(self.path, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self._fault("after_directory_fsync")
        return self.load(
            auth_key,
            expected_head_digest=replacement.head_digest,
            expected_sequence=replacement.sequence,
        )

    def _ensure_directory(self) -> None:
        if self.root.is_symlink() or not self.root.is_dir():
            raise LockTransitionError("lock_transition_root_invalid")
        try:
            self.path.mkdir(mode=0o700, exist_ok=True)
        except OSError:
            raise LockTransitionError("lock_transition_persist_failed") from None
        if self.path.is_symlink() or not self.path.is_dir():
            raise LockTransitionError("lock_transition_store_invalid")


def _entry_name(sequence: int) -> str:
    return f"{sequence:020d}.json"
