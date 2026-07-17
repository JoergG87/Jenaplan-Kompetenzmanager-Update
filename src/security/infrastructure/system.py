"""System clock, randomness, marker and permission adapters."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time
import uuid

from ..domain import (
    ENROLLMENT_MARKER_VERSION,
    SecurityStoreError,
    UnsupportedSecurityVersionError,
    validate_uuid4,
)


class SystemRandomSource:
    def bytes(self, length: int) -> bytes:
        return secrets.token_bytes(length)

    def uuid4(self) -> str:
        return str(uuid.uuid4())


class SystemClock:
    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


class PlatformFilePermissionManager:
    """Apply POSIX protection only inside the injected security directory."""

    def prepare_directory(self, path: Path) -> None:
        if path.is_symlink():
            raise SecurityStoreError("security_directory_symlink_rejected")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not path.is_dir() or path.is_symlink():
            raise SecurityStoreError("security_directory_invalid")
        if os.name == "posix":
            os.chmod(path, 0o700)

    def secure_file(self, path: Path) -> None:
        if path.is_symlink():
            raise SecurityStoreError("security_file_symlink_rejected")
        if path.exists() and os.name == "posix":
            os.chmod(path, 0o600)

    def secure_sqlite_files(self, database_path: Path) -> None:
        for suffix in ("", "-wal", "-shm", "-journal"):
            self.secure_file(Path(f"{database_path}{suffix}"))

    def verify(self, security_directory: Path) -> bool | None:
        if os.name != "posix":
            return None
        if stat.S_IMODE(security_directory.stat().st_mode) != 0o700:
            return False
        for path in security_directory.iterdir():
            if path.is_file() and stat.S_IMODE(path.stat().st_mode) != 0o600:
                return False
        return True


class EnrollmentMarkerFile:
    """Strict non-secret marker with atomic publish and directory fsync."""

    def __init__(self, path: Path, permissions: PlatformFilePermissionManager):
        self._path = Path(path)
        self._permissions = permissions

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists()

    def read_reference(self) -> str:
        if self._path.is_symlink():
            raise SecurityStoreError("enrollment_marker_symlink_rejected")
        try:
            payload = json.loads(self._path.read_text(encoding="ascii"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SecurityStoreError("enrollment_marker_invalid") from error
        if not isinstance(payload, dict) or set(payload) != {
            "format_version",
            "marker_reference",
        }:
            raise SecurityStoreError("enrollment_marker_invalid")
        marker_version = payload["format_version"]
        if not isinstance(marker_version, int) or isinstance(marker_version, bool):
            raise SecurityStoreError("enrollment_marker_invalid")
        if marker_version > ENROLLMENT_MARKER_VERSION:
            raise UnsupportedSecurityVersionError("enrollment_marker_version_newer")
        if marker_version != ENROLLMENT_MARKER_VERSION:
            raise SecurityStoreError("enrollment_marker_version_unsupported")
        return validate_uuid4(payload["marker_reference"])

    def publish(self, marker_reference: str) -> None:
        validate_uuid4(marker_reference)
        if self._path.exists():
            raise SecurityStoreError("enrollment_marker_already_exists")
        self._permissions.prepare_directory(self._path.parent)
        payload = json.dumps(
            {
                "format_version": ENROLLMENT_MARKER_VERSION,
                "marker_reference": marker_reference,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii") + b"\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".enrollment-marker-", dir=self._path.parent
        )
        temporary = Path(temporary_name)
        try:
            if os.name == "posix":
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, self._path)
            except FileExistsError as error:
                raise SecurityStoreError("enrollment_marker_already_exists") from error
            temporary.unlink()
            self._permissions.secure_file(self._path)
            _fsync_directory(self._path.parent)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
