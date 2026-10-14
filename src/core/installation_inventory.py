"""Unauthenticated observations, never startup or recovery capabilities."""
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class InstallationInventoryStatus(StrEnum):
    EMPTY = "empty"
    V4_ARTIFACTS_PRESENT = "v4_artifacts_present"
    PARTIAL = "partial"
    MAIN_MISSING = "main_missing"
    UPGRADE_EVIDENCE = "upgrade_evidence"
    RESTORE_EVIDENCE = "restore_evidence"
    UPGRADE_AND_RESTORE_EVIDENCE = "upgrade_and_restore_evidence"
    UNKNOWN = "unknown"
    UNSAFE = "unsafe"
    CHANGED = "changed"


@dataclass(frozen=True)
class InstallationArtifact:
    relative_path: str
    role: str
    # dev, inode, mode, uid, gid, nlink, size, mtime_ns, ctime_ns
    metadata: tuple[int, ...]


@dataclass(frozen=True)
class InstallationInventory:
    root: Path
    status: InstallationInventoryStatus
    artifacts: tuple[InstallationArtifact, ...] = ()
    upgrade_evidence: bool = False
    restore_evidence: bool = False
    unknown: tuple[str, ...] = ()
    reason: str = ""

    @property
    def normal_runtime_allowed(self) -> bool:
        return False

    @property
    def first_run_allowed(self) -> bool:
        return False

    @property
    def activation_allowed(self) -> bool:
        return False


class InstallationInventoryPort(Protocol):
    def inspect(self, root: Path) -> InstallationInventory: ...
