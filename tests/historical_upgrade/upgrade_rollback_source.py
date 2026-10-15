"""Synthetic encrypted rollback publication; no activation or recovery authority."""
from __future__ import annotations
from contextlib import contextmanager
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import stat
import sys
from uuid import UUID

from src.core.database_content_evidence import require_same_content
from src.core.schema_upgrade import UpgradeArtifact, UpgradeError


def _exclusive_rename(directory, source, target):
    """Native atomic no-replace publication; no link or copy/delete fallback."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = libc.renameatx_np
        flags = 4  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        flags = 1  # RENAME_NOREPLACE
    else:
        raise UpgradeError("upgrade_exclusive_rename_unsupported")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(directory, os.fsencode(source), directory, os.fsencode(target), flags):
        value = ctypes.get_errno()
        raise OSError(value, os.strerror(value))


class DurableUpgradeRollbackSource:
    def __init__(self, source_adapter, *, fault_hook=None):
        self.source = source_adapter
        self.rollback_path = source_adapter.workspace / "rollback.sqlcipher"
        self.temporary_path = source_adapter.workspace / "rollback.partial.sqlcipher"
        self._fault_hook = fault_hook
        self._root_identity = None
        self.artifact_id = str(UUID(bytes=hashlib.sha256((source_adapter.context.operation_id + ":durable-rollback").encode()).digest()[:16], version=4))

    def _emit(self, boundary):
        if self._fault_hook:
            self._fault_hook(boundary)

    @staticmethod
    def _identity(details):
        return details.st_dev, details.st_ino

    def _require(self):
        self.source.validate_context()
        if (self.rollback_path != self.source.workspace / "rollback.sqlcipher"
                or self.temporary_path != self.source.workspace / "rollback.partial.sqlcipher"):
            raise UpgradeError("upgrade_rollback_path_invalid")

    @contextmanager
    def _directory(self):
        self._require()
        root = Path(self.source.root)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptors = []
        try:
            fd = os.open(root.anchor, flags); descriptors.append(fd)
            for part in root.parts[1:]:
                fd = os.open(part, flags, dir_fd=fd); descriptors.append(fd)
            root_stat = os.fstat(fd)
            if (root_stat.st_uid != os.getuid() or stat.S_IMODE(root_stat.st_mode) != 0o700):
                raise UpgradeError("upgrade_rollback_root_unsafe")
            identity = self._identity(root_stat)
            if self._root_identity is None:
                self._root_identity = identity
            if identity != self._root_identity:
                raise UpgradeError("upgrade_rollback_root_changed")
            bindings = [(root, fd)]
            current = root
            for part in self.source.workspace.relative_to(root).parts:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
                fd = os.open(part, flags, dir_fd=fd); descriptors.append(fd)
                details = os.fstat(fd)
                if details.st_uid != os.getuid() or stat.S_IMODE(details.st_mode) != 0o700:
                    raise UpgradeError("upgrade_rollback_parent_unsafe")
                current = current / part
                bindings.append((current, fd))
            def recheck():
                self._require()
                for path, descriptor in bindings:
                    named = path.lstat()
                    if not stat.S_ISDIR(named.st_mode) or self._identity(named) != self._identity(os.fstat(descriptor)):
                        raise UpgradeError("upgrade_rollback_parent_changed")
            recheck()
            yield fd, recheck
            recheck()
            # Existing workspace entries may have been created by source staging
            # without ancestor sync. A receipt requires the entire private chain.
            for _path, descriptor in reversed(bindings):
                recheck()
                os.fsync(descriptor)
            recheck()
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _artifact(self, directory, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        try:
            before = os.fstat(descriptor)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o600):
                raise UpgradeError("upgrade_rollback_file_unsafe")
            digest = hashlib.sha256()
            while chunk := os.read(descriptor, 1024 * 1024):
                digest.update(chunk)
            after = os.fstat(descriptor)
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                    or self._identity(after) != self._identity(named)):
                raise UpgradeError("upgrade_rollback_changed")
            return UpgradeArtifact("rollback", self.artifact_id, digest.hexdigest(),
                after.st_dev, after.st_ino, after.st_size, self.source.context.source)
        finally:
            os.close(descriptor)

    def _inputs(self, source, backup):
        for path in (self.source.service.paths.final_v4.database, self.source.backup_path):
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                details = os.fstat(descriptor)
                if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1
                        or details.st_uid != os.getuid() or stat.S_IMODE(details.st_mode) != 0o600):
                    raise UpgradeError("upgrade_rollback_input_unsafe")
            finally:
                os.close(descriptor)
        if self.source.verify_source() != source:
            raise UpgradeError("upgrade_source_changed")
        if self.source.verify_backup(source) != backup:
            raise UpgradeError("upgrade_backup_changed")

    def _verify_file(self, directory, path, source):
        before = self._artifact(directory, path.name)
        require_same_content(source.main_content, self.source._inspect(path, main=True))
        if before != self._artifact(directory, path.name):
            raise UpgradeError("upgrade_rollback_changed")
        if (before.sha256 != source.artifact.sha256 or before.size_bytes != source.artifact.size_bytes
                or before.device_id != source.artifact.device_id
                or (before.device_id, before.file_id) == (source.artifact.device_id, source.artifact.file_id)):
            raise UpgradeError("upgrade_rollback_source_mismatch")
        return before

    def create(self, source, backup):
        with self._directory() as (directory, recheck):
            self._inputs(source, backup)
            # Unknown leftovers are evidence. Never adopt, overwrite or remove them.
            for path in (self.rollback_path, self.temporary_path):
                try:
                    os.stat(path.name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise UpgradeError("upgrade_rollback_unbound_artifact")
            original = os.open(self.source.service.paths.final_v4.database,
                os.O_RDONLY | os.O_NOFOLLOW)
            target = None
            try:
                details = os.fstat(original)
                if (details.st_nlink != 1 or details.st_uid != os.getuid()
                        or stat.S_IMODE(details.st_mode) != 0o600
                        or self._identity(details) != (source.artifact.device_id, source.artifact.file_id)):
                    raise UpgradeError("upgrade_rollback_source_unsafe")
                target = os.open(self.temporary_path.name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
                while chunk := os.read(original, 1024 * 1024):
                    remaining = memoryview(chunk)
                    while remaining:
                        written = os.write(target, remaining)
                        if written <= 0:
                            raise OSError(errno.EIO, "rollback short write")
                        remaining = remaining[written:]
                    self._emit("during_rollback_copy")
                os.fsync(target)
            finally:
                os.close(original)
                if target is not None:
                    os.close(target)
            self._emit("after_rollback_file_fsync")
            receipt = self._verify_file(directory, self.temporary_path, source)
            self._inputs(source, backup)
            recheck()
            self._emit("before_rollback_publication")
            recheck()
            _exclusive_rename(directory, self.temporary_path.name, self.rollback_path.name)
            self._emit("after_rollback_publication")
            os.fsync(directory)
            self._emit("after_rollback_directory_fsync")
            recheck()
            result = self._verify_file(directory, self.rollback_path, source)
            if result != receipt:
                raise UpgradeError("upgrade_rollback_publication_changed")
            return result

    def verify(self, source, backup, expected=None):
        if expected is None:
            raise UpgradeError("upgrade_rollback_bound_receipt_required")
        with self._directory() as (directory, recheck):
            self._inputs(source, backup)
            result = self._verify_file(directory, self.rollback_path, source)
            if expected is not None and result != expected:
                raise UpgradeError("upgrade_rollback_receipt_mismatch")
            recheck()
            return result
