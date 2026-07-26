"""Fail-closed activation gate for the Security Sprint 11 test path.

The normal product startup does not import or call this module.  Activation
requires both explicit environment values and an already existing, private,
marker-bound root below the system temporary directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
import stat
import tempfile
from typing import Mapping


SECURITY_INTEGRATION_GATE_ENV = "JKM_SECURITY_INTEGRATION_TEST"
SECURITY_INTEGRATION_ROOT_ENV = "JKM_SECURITY_INTEGRATION_ROOT"
SECURITY_INTEGRATION_GATE_VALUE = "1"
SECURITY_INTEGRATION_ROOT_PREFIX = "jkm-security-integration-"
SECURITY_INTEGRATION_ROOT_MARKER = ".jkm-security-integration-test-root"
SECURITY_INTEGRATION_ROOT_MARKER_BYTES = (
    b"jenaplan-security-integration-test-root-v1\n"
)
SECURITY_INTEGRATION_SOURCE_MARKER = (
    ".jkm-security-integration-plaintext-source"
)
SECURITY_INTEGRATION_SOURCE_MARKER_BYTES = (
    b"jenaplan-security-integration-plaintext-source-v1\n"
)


class SecurityIntegrationError(RuntimeError):
    """Sanitized integration failure which never embeds paths or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SecurityIntegrationGateState(StrEnum):
    DISABLED = "DISABLED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SecurityIntegrationPaths:
    """Fixed roles below one marker-bound temporary integration root."""

    root: Path
    source_database: Path
    source_documents: Path
    safety_copy: Path
    encrypted_database: Path
    document_storage: Path
    exports: Path
    encrypted_backup: Path
    journal: Path
    retained_marker: Path
    replay_anchor: Path

    @classmethod
    def for_root(cls, root: Path) -> "SecurityIntegrationPaths":
        base = Path(root)
        return cls(
            root=base,
            source_database=base / "kompetenzmanager.sqlite",
            source_documents=base / "sources",
            safety_copy=base / "plaintext-safety-copy.sqlite",
            encrypted_database=base / "integration.sqlcipher",
            document_storage=base / "storage",
            exports=base / "exports",
            encrypted_backup=base / "integration.jkmebackup",
            journal=base / "security-integration-journal-v1.json",
            retained_marker=base / "plaintext-retained-v1.json",
            replay_anchor=base.parent / f".{base.name}.replay-anchor-v1.json",
        )


@dataclass(frozen=True)
class SecurityIntegrationGateDecision:
    state: SecurityIntegrationGateState
    paths: SecurityIntegrationPaths | None = None
    error_code: str | None = None


class SecurityIntegrationGate:
    """Resolve the internal gate without mutating any filesystem state."""

    def resolve(
        self,
        environ: Mapping[str, str] | None = None,
    ) -> SecurityIntegrationGateDecision:
        environment = os.environ if environ is None else environ
        raw_gate = environment.get(SECURITY_INTEGRATION_GATE_ENV, "")
        if raw_gate == "":
            return SecurityIntegrationGateDecision(
                SecurityIntegrationGateState.DISABLED
            )
        if raw_gate != SECURITY_INTEGRATION_GATE_VALUE:
            return SecurityIntegrationGateDecision(
                SecurityIntegrationGateState.BLOCKED,
                error_code="security_integration_gate_value_invalid",
            )
        raw_root = environment.get(SECURITY_INTEGRATION_ROOT_ENV, "")
        try:
            paths = self._validate_root(raw_root)
        except SecurityIntegrationError as error:
            return SecurityIntegrationGateDecision(
                SecurityIntegrationGateState.BLOCKED,
                error_code=error.code,
            )
        return SecurityIntegrationGateDecision(
            SecurityIntegrationGateState.ACTIVE,
            paths=paths,
        )

    def require_active(
        self,
        environ: Mapping[str, str] | None = None,
    ) -> SecurityIntegrationPaths:
        decision = self.resolve(environ)
        if (
            decision.state is not SecurityIntegrationGateState.ACTIVE
            or decision.paths is None
        ):
            raise SecurityIntegrationError(
                decision.error_code or "security_integration_gate_disabled"
            )
        return decision.paths

    @staticmethod
    def _validate_root(raw_root: str) -> SecurityIntegrationPaths:
        if not isinstance(raw_root, str) or not raw_root:
            raise SecurityIntegrationError(
                "security_integration_root_missing"
            )
        root = Path(raw_root)
        if not root.is_absolute() or root.name == "":
            raise SecurityIntegrationError(
                "security_integration_root_invalid"
            )
        try:
            root_status = os.lstat(root)
            resolved_root = root.resolve(strict=True)
            temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
            relative = resolved_root.relative_to(temporary_root)
        except (OSError, RuntimeError, ValueError):
            raise SecurityIntegrationError(
                "security_integration_root_invalid"
            ) from None
        if (
            stat.S_ISLNK(root_status.st_mode)
            or not stat.S_ISDIR(root_status.st_mode)
            or resolved_root != root
            or not relative.parts
            or not root.name.startswith(SECURITY_INTEGRATION_ROOT_PREFIX)
        ):
            raise SecurityIntegrationError(
                "security_integration_root_invalid"
            )
        if stat.S_IMODE(root_status.st_mode) & 0o077:
            raise SecurityIntegrationError(
                "security_integration_root_not_private"
            )
        if hasattr(os, "getuid") and root_status.st_uid != os.getuid():
            raise SecurityIntegrationError(
                "security_integration_root_owner_invalid"
            )
        _require_marker(
            root / SECURITY_INTEGRATION_ROOT_MARKER,
            SECURITY_INTEGRATION_ROOT_MARKER_BYTES,
            "security_integration_root_marker_invalid",
        )
        _require_marker(
            root / SECURITY_INTEGRATION_SOURCE_MARKER,
            SECURITY_INTEGRATION_SOURCE_MARKER_BYTES,
            "security_integration_source_marker_invalid",
        )
        paths = SecurityIntegrationPaths.for_root(root)
        _require_private_directory(
            paths.source_documents,
            "security_integration_source_documents_invalid",
        )
        return paths


def _require_marker(path: Path, expected: bytes, code: str) -> None:
    descriptor: int | None = None
    try:
        status = os.lstat(path)
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            raise SecurityIntegrationError(code)
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino) != (status.st_dev, status.st_ino)
            or opened.st_size != len(expected)
            or os.read(descriptor, len(expected) + 1) != expected
        ):
            raise SecurityIntegrationError(code)
    except SecurityIntegrationError:
        raise
    except OSError:
        raise SecurityIntegrationError(code) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _require_private_directory(path: Path, code: str) -> None:
    try:
        status = os.lstat(path)
    except OSError:
        raise SecurityIntegrationError(code) from None
    if (
        stat.S_ISLNK(status.st_mode)
        or not stat.S_ISDIR(status.st_mode)
        or stat.S_IMODE(status.st_mode) & 0o077
        or (hasattr(os, "getuid") and status.st_uid != os.getuid())
    ):
        raise SecurityIntegrationError(code)
