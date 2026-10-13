"""Reuse product RuntimeInstanceLock and ObservationWriterLock, no new lock file."""
from __future__ import annotations
import json
import os
from pathlib import Path
from src.core.observation_uow import ObservationWriterLock
from src.core.restore_runtime import RuntimeInstanceLock, _process_start_identity
from src.core.runtime_root_protection import require_mutable_test_root, RuntimeRootKind
from src.core.schema_upgrade import UpgradeContext, UpgradeError


class UpgradeProcessLease:
    def __init__(self, runtime_lock: RuntimeInstanceLock, context: UpgradeContext,
                 writer_root: Path):
        if Path(writer_root).resolve() != runtime_lock.runtime_root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging":
            raise UpgradeError("upgrade_writer_root_invalid")
        self.lock, self.context = runtime_lock, context
        self.writer = ObservationWriterLock(writer_root)
        self.pid = os.getpid()
        self.active = False

    def _require_process(self) -> None:
        expected_root = self.lock.runtime_root / "final-v4-sqlcipher-runtime-v1" / ".observation-staging"
        if self.writer.staging_root.resolve() != expected_root:
            raise UpgradeError("upgrade_writer_root_changed")
        protection = require_mutable_test_root(self.lock.runtime_root)
        if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
            raise UpgradeError("upgrade_synthetic_root_required")
        if self.pid != os.getpid():
            raise UpgradeError("upgrade_process_changed")
        try:
            fd = os.fstat(self.lock.fileno)
            path = self.lock.path.lstat()
            payload = json.loads(self.lock.path.read_text())
            if (fd.st_dev, fd.st_ino) != (path.st_dev, path.st_ino) or self.lock.path.is_symlink():
                raise ValueError
            if payload["pid"] != self.pid or payload["process_start_identity"] != _process_start_identity(self.pid):
                raise ValueError
        except Exception:
            raise UpgradeError("upgrade_runtime_lock_required") from None

    def __enter__(self):
        self._require_process()
        if self.active:
            raise UpgradeError("upgrade_process_lease_reused")
        self.writer.__enter__()
        if self.writer._fd is None:
            self.writer.__exit__(None, None, None)
            raise UpgradeError("upgrade_nested_writer_lock_denied")
        self.active = True
        return self

    def require_owner(self, context: UpgradeContext) -> None:
        self._require_process()
        if self.active and self.writer._fd is not None:
            fd, path = os.fstat(self.writer._fd), self.writer.lock_path.lstat()
            if (fd.st_dev, fd.st_ino) != (path.st_dev, path.st_ino) or self.writer.lock_path.is_symlink():
                raise UpgradeError("upgrade_writer_lock_changed")
        if not self.active or context != self.context:
            raise UpgradeError("upgrade_process_context_mismatch")

    def __exit__(self, exc_type, exc, traceback):
        if self.active:
            self.active = False
            self.writer.__exit__(exc_type, exc, traceback)
        return False
