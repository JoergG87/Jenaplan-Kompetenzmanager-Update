"""Fail-closed classification for pilot-product and synthetic runtime roots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Iterable


RUNTIME_ROOT_PROTECTION_MARKER = ".jkm-runtime-root-v1"
RUNTIME_ROOT_PROTECTION_PENDING = ".jkm-runtime-root-v1.pending"
RUNTIME_ROOT_PROTECTION_FORMAT = "jenaplan-runtime-root-protection"
RUNTIME_ROOT_PROTECTION_VERSION = 1

_PRODUCT_EVIDENCE_NAMES = frozenset(
    {
        "app-preferences.json",
        "backups",
        "documents",
        "exports",
        "kompetenzmanager.sqlite",
        "logs",
        "security",
        "security-key-runtime-v1",
        "final-v4-sqlcipher-runtime-v1",
        "restore-handoffs",
        "restore-transactions",
        "encrypted-restore-staging",
        "encrypted-restore-safety",
    }
)


class RuntimeRootKind(StrEnum):
    PILOT_PRODUCT = "pilot_product"
    SYNTHETIC_TEST = "synthetic_test"


class RuntimeRootLifecycle(StrEnum):
    INITIALIZING = "initializing"
    ACTIVE = "active"


class RuntimeRootProtectionError(RuntimeError):
    """Sanitized refusal raised before a protected-root mutation."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class RuntimeRootProtection:
    kind: RuntimeRootKind
    lifecycle: RuntimeRootLifecycle
    version: int = RUNTIME_ROOT_PROTECTION_VERSION


def publish_pilot_product_root(
    root: Path,
    *,
    allowed_existing: Iterable[Path] = (),
) -> RuntimeRootProtection:
    """Publish the initializing product authority before any product artifact."""

    root = _require_root(root)
    allowed = {Path(path) for path in allowed_existing}
    try:
        entries = tuple(root.iterdir())
    except OSError:
        raise RuntimeRootProtectionError("runtime_root_unreadable") from None
    if any(entry not in allowed for entry in entries):
        raise RuntimeRootProtectionError("pilot_product_root_not_fresh")
    protection = RuntimeRootProtection(
        RuntimeRootKind.PILOT_PRODUCT,
        RuntimeRootLifecycle.INITIALIZING,
    )
    _publish(root, protection, replace_existing=False)
    return protection


def activate_pilot_product_root(root: Path) -> RuntimeRootProtection:
    """Atomically activate a fully verified product First Run."""

    root = _require_root(root)
    current = inspect_runtime_root(root)
    if current != RuntimeRootProtection(
        RuntimeRootKind.PILOT_PRODUCT,
        RuntimeRootLifecycle.INITIALIZING,
    ):
        raise RuntimeRootProtectionError("pilot_product_root_activation_invalid")
    protection = RuntimeRootProtection(
        RuntimeRootKind.PILOT_PRODUCT,
        RuntimeRootLifecycle.ACTIVE,
    )
    _publish(root, protection, replace_existing=True)
    return protection


def publish_synthetic_test_root(root: Path) -> RuntimeRootProtection:
    """Mark one already-created empty tool-owned root as synthetic."""

    root = _require_root(root)
    _require_system_temporary_root(root)
    _require_no_product_ancestor(root.parent)
    try:
        entries = tuple(root.iterdir())
    except OSError:
        raise RuntimeRootProtectionError("runtime_root_unreadable") from None
    if entries:
        raise RuntimeRootProtectionError("synthetic_test_root_not_fresh")
    protection = RuntimeRootProtection(
        RuntimeRootKind.SYNTHETIC_TEST,
        RuntimeRootLifecycle.ACTIVE,
    )
    _publish(root, protection, replace_existing=False)
    return protection


def prepare_synthetic_test_root(root: Path) -> RuntimeRootProtection:
    """Create/mark only a fresh owned root below the system temporary tree."""

    candidate = Path(root).expanduser()
    if not candidate.is_absolute() or candidate.is_symlink():
        raise RuntimeRootProtectionError("synthetic_test_root_invalid")
    _require_no_product_ancestor(candidate.parent)
    _require_system_temporary_root(candidate.resolve(strict=False))
    if candidate.exists():
        existing = inspect_runtime_root(candidate)
        if existing is not None:
            if existing.kind is not RuntimeRootKind.SYNTHETIC_TEST:
                raise RuntimeRootProtectionError("pilot_product_root_protected")
            return existing
        try:
            if any(candidate.iterdir()):
                raise RuntimeRootProtectionError("synthetic_test_root_not_fresh")
        except OSError:
            raise RuntimeRootProtectionError("runtime_root_unreadable") from None
    else:
        try:
            candidate.mkdir(mode=0o700)
        except OSError:
            raise RuntimeRootProtectionError("synthetic_test_root_create_failed") from None
    return publish_synthetic_test_root(candidate.resolve(strict=True))


def inspect_runtime_root(root: Path) -> RuntimeRootProtection | None:
    """Read one marker without creating, repairing, or normalizing anything."""

    root = Path(root)
    marker = root / RUNTIME_ROOT_PROTECTION_MARKER
    pending = root / RUNTIME_ROOT_PROTECTION_PENDING
    if _exists_or_symlink(pending):
        raise RuntimeRootProtectionError("runtime_root_protection_partial")
    if not _exists_or_symlink(marker):
        return None
    descriptor = None
    try:
        descriptor = os.open(
            marker,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or (hasattr(os, "getuid") and metadata.st_uid != os.getuid())
        ):
            raise OSError
        raw = os.read(descriptor, 4097)
        if len(raw) > 4096 or os.read(descriptor, 1):
            raise ValueError
        payload = json.loads(raw.decode("utf-8"))
        if set(payload) != {
            "format",
            "kind",
            "lifecycle",
            "root_sha256",
            "version",
        }:
            raise ValueError
        if payload["format"] != RUNTIME_ROOT_PROTECTION_FORMAT:
            raise ValueError
        if payload["version"] != RUNTIME_ROOT_PROTECTION_VERSION:
            raise ValueError
        if payload["root_sha256"] != _root_sha256(root.resolve(strict=True)):
            raise ValueError
        protection = RuntimeRootProtection(
            RuntimeRootKind(payload["kind"]),
            RuntimeRootLifecycle(payload["lifecycle"]),
            int(payload["version"]),
        )
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        raise RuntimeRootProtectionError("runtime_root_protection_invalid") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if (
        protection.kind is RuntimeRootKind.SYNTHETIC_TEST
        and protection.lifecycle is not RuntimeRootLifecycle.ACTIVE
    ):
        raise RuntimeRootProtectionError("runtime_root_protection_invalid")
    return protection


def require_product_runtime_root(
    root: Path,
    *,
    first_run: bool,
    synthetic_allowed: bool = True,
) -> RuntimeRootProtection:
    """Admit an authorized product lifecycle or an explicit synthetic root."""

    protection = inspect_runtime_root(root)
    if protection is None:
        raise RuntimeRootProtectionError("runtime_root_protection_missing")
    if protection.kind is RuntimeRootKind.SYNTHETIC_TEST:
        if not synthetic_allowed:
            raise RuntimeRootProtectionError("synthetic_test_root_not_allowed")
        return protection
    required = (
        RuntimeRootLifecycle.INITIALIZING
        if first_run
        else RuntimeRootLifecycle.ACTIVE
    )
    if protection.lifecycle is not required:
        raise RuntimeRootProtectionError("pilot_product_root_lifecycle_invalid")
    return protection


def require_mutable_test_root(root: Path) -> RuntimeRootProtection | None:
    """Reject product, partial, invalid, or unclassified product-evidence roots."""

    root = Path(root)
    protection = inspect_runtime_root(root)
    if protection is not None:
        if protection.kind is RuntimeRootKind.PILOT_PRODUCT:
            raise RuntimeRootProtectionError("pilot_product_root_protected")
        return protection
    if _contains_product_evidence(root):
        raise RuntimeRootProtectionError("pilot_product_root_evidence_unclassified")
    return None


def require_or_prepare_synthetic_test_root(root: Path) -> RuntimeRootProtection:
    """Admit an existing synthetic root or mark one completely empty temp root."""

    candidate = Path(root)
    if not candidate.exists() and not candidate.is_symlink():
        return prepare_synthetic_test_root(candidate)
    protection = inspect_runtime_root(candidate)
    if protection is None:
        require_mutable_test_root(candidate)
        try:
            if any(candidate.iterdir()):
                raise RuntimeRootProtectionError("synthetic_test_root_authority_required")
        except OSError:
            raise RuntimeRootProtectionError("runtime_root_unreadable") from None
        return prepare_synthetic_test_root(candidate)
    if protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
        raise RuntimeRootProtectionError("pilot_product_root_protected")
    return protection


def require_database_mutation_authority(
    database_path: Path,
    *,
    allow_initializing_product: bool = False,
) -> RuntimeRootProtection:
    """Bind a DB initializer/seeder to a synthetic or controlled First-Run root."""

    current = Path(database_path).parent.resolve(strict=False)
    evidence_boundaries = {
        Path(tempfile.gettempdir()).resolve(strict=True),
        Path("/private/tmp").resolve(strict=True),
    }
    inspect_unmarked_evidence = True
    synthetic = None
    while True:
        protection = inspect_runtime_root(current)
        if protection is not None:
            if protection.kind is RuntimeRootKind.SYNTHETIC_TEST:
                synthetic = protection
            if (
                synthetic is None
                and allow_initializing_product
                and protection.lifecycle is RuntimeRootLifecycle.INITIALIZING
            ):
                return protection
            if protection.kind is RuntimeRootKind.PILOT_PRODUCT:
                raise RuntimeRootProtectionError("pilot_product_root_protected")
        if (
            inspect_unmarked_evidence
            and protection is None
            and _contains_product_evidence(current)
        ):
            raise RuntimeRootProtectionError(
                "pilot_product_root_evidence_unclassified"
            )
        if current in evidence_boundaries:
            inspect_unmarked_evidence = False
        if current.parent == current:
            break
        current = current.parent
    if synthetic is not None:
        return synthetic
    raise RuntimeRootProtectionError("synthetic_test_root_authority_required")


def require_disposable_tree(root: Path) -> None:
    """Reject deleting an output tree containing protected or partial roots."""

    root = Path(root)
    if not _exists_or_symlink(root):
        return
    require_mutable_test_root(root)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeRootProtectionError("disposable_tree_path_invalid")
    try:
        for directory, names, _files in os.walk(root, followlinks=False):
            current = Path(directory)
            if current != root:
                require_mutable_test_root(current)
            if any((current / name).is_symlink() for name in names):
                continue
    except RuntimeRootProtectionError:
        raise
    except OSError:
        raise RuntimeRootProtectionError("disposable_tree_unreadable") from None


def require_unprotected_output_path(path: Path) -> None:
    """Reject build/test output located at or below a protected product root."""

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve(strict=False)
    _require_no_product_ancestor(candidate, output_container=True)


def _publish(
    root: Path,
    protection: RuntimeRootProtection,
    *,
    replace_existing: bool,
) -> None:
    marker = root / RUNTIME_ROOT_PROTECTION_MARKER
    pending = root / RUNTIME_ROOT_PROTECTION_PENDING
    if _exists_or_symlink(pending):
        raise RuntimeRootProtectionError("runtime_root_protection_partial")
    if not replace_existing and _exists_or_symlink(marker):
        raise RuntimeRootProtectionError("runtime_root_protection_already_exists")
    payload = (
        json.dumps(
            {
                "format": RUNTIME_ROOT_PROTECTION_FORMAT,
                "kind": protection.kind.value,
                "lifecycle": protection.lifecycle.value,
                "root_sha256": _root_sha256(root),
                "version": protection.version,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    descriptor = None
    try:
        descriptor = os.open(
            pending,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise OSError
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(pending, marker)
        directory_descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except OSError:
        if descriptor is not None:
            os.close(descriptor)
        raise RuntimeRootProtectionError("runtime_root_protection_publish_failed") from None


def _require_root(root: Path) -> Path:
    path = Path(root)
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        raise RuntimeRootProtectionError("runtime_root_invalid") from None
    if (
        not path.is_absolute()
        or resolved != path
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or (hasattr(os, "getuid") and metadata.st_uid != os.getuid())
    ):
        raise RuntimeRootProtectionError("runtime_root_invalid")
    return resolved


def _contains_product_evidence(root: Path) -> bool:
    if not root.is_dir() or root.is_symlink():
        return False
    return any(_exists_or_symlink(root / name) for name in _PRODUCT_EVIDENCE_NAMES)


def _require_no_product_ancestor(path: Path, *, output_container: bool = False) -> None:
    current = Path(path).resolve(strict=False)
    evidence_boundaries = {
        Path(tempfile.gettempdir()).resolve(strict=True),
        Path("/private/tmp").resolve(strict=True),
    }
    inspect_unmarked_evidence = True
    home = Path.home().resolve(strict=True)
    while True:
        protection = inspect_runtime_root(current)
        if protection is not None:
            if protection.kind is RuntimeRootKind.PILOT_PRODUCT:
                raise RuntimeRootProtectionError("pilot_product_root_protected")
        if (
            inspect_unmarked_evidence
            and protection is None
            and (
                any(_exists_or_symlink(current / name) for name in
                    _PRODUCT_EVIDENCE_NAMES - {"documents", "backups", "exports", "logs"})
                if output_container and current == home
                else _contains_product_evidence(current)
            )
        ):
            raise RuntimeRootProtectionError("pilot_product_root_evidence_unclassified")
        if current in evidence_boundaries:
            inspect_unmarked_evidence = False
        if current.parent == current:
            return
        current = current.parent


def _require_system_temporary_root(root: Path) -> None:
    resolved = Path(root).resolve(strict=False)
    temporary_roots = {
        Path(tempfile.gettempdir()).resolve(strict=True),
        Path("/private/tmp").resolve(strict=True),
    }
    for temporary in temporary_roots:
        try:
            relative_parts = resolved.relative_to(temporary).parts
        except ValueError:
            continue
        if relative_parts:
            return
        raise RuntimeRootProtectionError("synthetic_test_root_invalid")
    raise RuntimeRootProtectionError("synthetic_test_root_outside_temporary")


def _exists_or_symlink(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _root_sha256(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()
