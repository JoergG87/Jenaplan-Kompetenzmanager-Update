"""Descriptor-relative, existing-only root inventory. No content authority.

Two scans detect ordinary concurrent changes, not adversarial ABA or changes
after return. Consumers must rescan under the existing runtime/writer locks.
No file payload is parsed, no key or database is opened, no lock is acquired.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

from src.core.installation_inventory import (
    InstallationArtifact, InstallationInventory, InstallationInventoryStatus as Status,
)
from src.core.runtime_root_protection import (
    RUNTIME_ROOT_PROTECTION_MARKER, RUNTIME_ROOT_PROTECTION_PENDING,
)
from src.security.database_key_runtime import DatabaseKeyRuntimePaths
from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths
from src.security.final_v3_document_runtime import FinalV3DocumentRuntimePaths

_UPGRADE = {"schema-upgrade-foundation", "schema-upgrade-replay", "schema-upgrade-source"}
_RESTORE = {"restore-handoffs", "restore-transactions", "restore-staging",
            "encrypted-restore-staging", "encrypted-restore-safety"}
_ANCILLARY = {"backups", "exports", "logs"}


def _metadata(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


class ReadOnlyInstallationInventory:
    """Inventory every descendant, including unknown and opaque recovery files.

V4_ARTIFACTS_PRESENT means presence only, never verified schema, installation
identity, document crossbindings, RESTORE_READY or journal authority.
"""

    def inspect(self, root: Path) -> InstallationInventory:
        root = Path(root)
        try:
            if not root.is_absolute() or root.resolve(strict=True) != root:
                raise ValueError("inventory_root_not_canonical")
            # Verify every ancestor without following links. Shared sticky system
            # temporary directories are permitted, writable other parents are not.
            for parent in reversed(root.parents):
                value = parent.lstat()
                if (not stat.S_ISDIR(value.st_mode)
                        or value.st_uid not in {0, os.getuid()}
                        or (value.st_mode & 0o022 and not value.st_mode & stat.S_ISVTX)):
                    raise ValueError("inventory_parent_unsafe")
            before = self._scan(root)
            after = self._scan(root)
            if before != after:
                return InstallationInventory(root, Status.CHANGED, reason="inventory_changed")
            return self._classify(root, before)
        except ValueError as error:
            if str(error) == "inventory_changed":
                return InstallationInventory(root, Status.CHANGED, reason="inventory_changed")
            return InstallationInventory(root, Status.UNSAFE, reason="inventory_unreadable_or_unsafe")
        except (OSError, RuntimeError):
            return InstallationInventory(root, Status.UNSAFE, reason="inventory_unreadable_or_unsafe")

    def _scan(self, root):
        entries = []
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK

        def walk(fd, relative):
            if len(entries) > 100000 or relative.count("/") > 64:
                raise ValueError("inventory_limit_exceeded")
            before = os.fstat(fd)
            self._safe(before, directory=True)
            entries.append((relative, _metadata(before)))
            for name in sorted(os.listdir(fd)):
                if len(entries) >= 100000:
                    raise ValueError("inventory_limit_exceeded")
                value = os.stat(name, dir_fd=fd, follow_symlinks=False)
                path = f"{relative}/{name}" if relative else name
                if stat.S_ISDIR(value.st_mode):
                    child = os.open(name, flags, dir_fd=fd)
                    try:
                        if _metadata(os.fstat(child)) != _metadata(value):
                            raise ValueError("inventory_changed")
                        walk(child, path)
                    finally:
                        os.close(child)
                else:
                    self._safe(value, directory=False)
                    child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    try:
                        if _metadata(os.fstat(child)) != _metadata(value):
                            raise ValueError("inventory_changed")
                    finally:
                        os.close(child)
                    entries.append((path, _metadata(value)))
            if _metadata(before) != _metadata(os.fstat(fd)):
                raise ValueError("inventory_changed")

        # Open each parent component through its descriptor. NOFOLLOW on only
        # the final root component would still follow swapped parent symlinks.
        fd = os.open(root.anchor, flags)
        try:
            for component in root.parts[1:]:
                child = os.open(component, flags, dir_fd=fd)
                os.close(fd)
                fd = child
                value = os.fstat(fd)
                if (value.st_uid not in {0, os.getuid()}
                        or (value.st_mode & 0o022 and not value.st_mode & stat.S_ISVTX)):
                    raise ValueError("inventory_parent_unsafe")
            walk(fd, "")
            if _metadata(root.lstat()) != _metadata(os.fstat(fd)):
                raise ValueError("inventory_changed")
        finally:
            os.close(fd)
        return tuple(sorted(entries))

    @staticmethod
    def _safe(value, *, directory):
        required = stat.S_ISDIR if directory else stat.S_ISREG
        if (not required(value.st_mode) or value.st_uid != os.getuid()
                or stat.S_IMODE(value.st_mode) & 0o077
                or not value.st_mode & stat.S_IRUSR
                or (directory and not value.st_mode & stat.S_IXUSR)
                or (not directory and value.st_nlink != 1)):
            raise ValueError("inventory_entry_unsafe")

    @staticmethod
    def _classify(root, scan):
        keys = DatabaseKeyRuntimePaths.for_root(root)
        main = FinalV4SQLCipherRuntimePaths.for_key_runtime(keys)
        documents = FinalV3DocumentRuntimePaths.for_final_v4(main)
        files = {RUNTIME_ROOT_PROTECTION_MARKER, RUNTIME_ROOT_PROTECTION_PENDING,
                 "instance.lock", "app-preferences.json", "security/security.sqlite",
                 "security/enrollment.marker"}
        files.update(str(p.relative_to(root)) for p in
                     (keys.keyset_metadata, keys.envelope_registry, main.database, documents.database))
        database_files = {"security/security.sqlite"}
        database_files.update(str(p.relative_to(root)) for p in
                              (keys.keyset_metadata, main.database, documents.database))
        directories = {"security", keys.metadata_root.name, main.runtime_root.name}
        directories.update(str(p.relative_to(root)) for p in
                           (documents.container_root, documents.layout_source_root, documents.storage_root))
        writer = str((main.runtime_root / ".observation-staging").relative_to(root))
        directories.add(writer)
        files.add(writer + "/.writer.lock")
        # Document marker names are canonical existing layout constants.
        from prototypes.encrypted_document_container.sprint10_container import (
            SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER, SYNTHETIC_DOCUMENT_STORAGE_MARKER,
        )
        files.add(str((documents.container_root / SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER).relative_to(root)))
        files.add(str((documents.storage_root / SYNTHETIC_DOCUMENT_STORAGE_MARKER).relative_to(root)))
        required = (files - {"instance.lock", "app-preferences.json", RUNTIME_ROOT_PROTECTION_PENDING,
                             writer + "/.writer.lock"}) | (directories - {writer})
        artifacts, unknown = [], []
        present = {path for path, _ in scan if path}
        upgrade = bool(present & _UPGRADE)
        restore = bool(present & _RESTORE)
        for path, metadata in scan:
            if not path:
                artifacts.append(InstallationArtifact(path, "root", metadata))
                continue
            top = path.split("/")[0]
            is_directory = stat.S_ISDIR(metadata[2])
            if top in _UPGRADE | _RESTORE | _ANCILLARY:
                # Opaque contents are reported, never authenticated or ignored.
                role = ("upgrade_evidence" if top in _UPGRADE else
                        "restore_evidence" if top in _RESTORE else "ancillary_unverified")
                if path == top and not is_directory:
                    role = "unknown"
            elif (path in directories and is_directory) or (path in files and not is_directory):
                role = "product_artifact"
            elif _operation_artifact_role(path, is_directory, main.runtime_root.relative_to(root)):
                # Shape only: no phase, contents, key or recovery authority.
                # Product preflight and keyed lifecycle verification are separate.
                role = _operation_artifact_role(path, is_directory, main.runtime_root.relative_to(root))
            elif (not is_directory and Path(path).parent == documents.storage_root.relative_to(root)
                  and re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.jkmedoc", path.rsplit("/", 1)[-1])):
                role = "document_container_unverified"
            elif not is_directory and any(path == name + suffix for name in database_files
                                           for suffix in ("-wal", "-shm", "-journal")):
                role = "database_sidecar"
            else:
                role = "unknown"
            if role == "unknown":
                unknown.append(path)
            artifacts.append(InstallationArtifact(path, role, metadata))
        if not present:
            status = Status.EMPTY
        elif unknown or RUNTIME_ROOT_PROTECTION_PENDING in present:
            status = Status.UNKNOWN
        elif upgrade and restore:
            status = Status.UPGRADE_AND_RESTORE_EVIDENCE
        elif upgrade:
            status = Status.UPGRADE_EVIDENCE
        elif restore:
            status = Status.RESTORE_EVIDENCE
        elif str(main.database.relative_to(root)) not in present:
            status = Status.MAIN_MISSING
        elif required <= present:
            status = Status.V4_ARTIFACTS_PRESENT
        else:
            status = Status.PARTIAL
        return InstallationInventory(root, status, tuple(artifacts), upgrade, restore,
                                     tuple(unknown), "unauthenticated_inventory")


def _operation_artifact_role(path, directory, runtime_relative):
    prefix = str(runtime_relative) + "/"
    if not path.startswith(prefix):
        return None
    relative = path[len(prefix):]
    token = r"[a-f0-9]{32}"
    if directory and (re.fullmatch(r"\.observation-staging/" + token, relative)
            or relative in {".managed-document-staging", ".managed-document-staging/pdf-artifacts"}
            or re.fullmatch(r"\.managed-document-staging/" + token, relative)
            or re.fullmatch(r"\.managed-document-staging/pdf-artifacts/[a-f0-9]{64}", relative)):
        return "operation_directory_unverified"
    if not directory:
        if (re.fullmatch(r"\.observation-staging/" + token + r"/journal\.json", relative)
                or re.fullmatch(r"\.managed-document-staging/" + token + r"/managed-document\.json", relative)
                or re.fullmatch(r"\.managed-document-staging/pdf-artifacts/[a-f0-9]{64}/managed-pdf-artifact\.json", relative)):
            return "operation_journal_unverified"
        if re.fullmatch(r"\.managed-document-staging/" + token + r"/MED-[0-9]{6}", relative):
            return "operation_reservation_unverified"
    return None
