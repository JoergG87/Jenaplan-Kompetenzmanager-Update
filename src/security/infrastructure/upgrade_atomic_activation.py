"""Synthetic-only atomic Main replacement. Stops at TARGET_INSTALLED."""
from __future__ import annotations

from contextlib import closing
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import stat
from uuid import uuid4

from src.core.database_compatibility import DatabaseCompatibilityInspector
from src.core.database_content_evidence import database_content_evidence, require_same_content
from src.core.maintenance_gate import ConnectionDrain, MaintenancePurpose, MaintenanceState
from src.core.runtime_root_protection import require_mutable_test_root, RuntimeRootKind
from src.core.schema_registry import RegisteredSchemaIdentity, SCHEMA_FINGERPRINT_ALGORITHM
from src.core.schema_upgrade import (UpgradeArtifact, UpgradeError, UpgradeEvidence,
    UpgradeExchangeIntent, UpgradeExchangeResult, UpgradePhase, advance_upgrade)


class PinnedUpgradeFiles:
    """Private descendants of a pinned synthetic root, opened without following links."""
    def __init__(self, root):
        self.root = Path(root)
        self._fds = {}
        self._identities = {}

    @staticmethod
    def _private(details, *, directory):
        if ((not stat.S_ISDIR(details.st_mode) if directory else not stat.S_ISREG(details.st_mode))
                or details.st_uid != os.getuid()
                or stat.S_IMODE(details.st_mode) != (0o700 if directory else 0o600)
                or (not directory and details.st_nlink != 1)):
            raise UpgradeError("upgrade_exchange_path_unsafe")

    def __enter__(self):
        try:
            protection = require_mutable_test_root(self.root)
            if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
                raise UpgradeError("upgrade_synthetic_root_required")
            # Traverse every absolute ancestor without following symlinks.
            descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
            try:
                for part in self.root.parts[1:]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    os.close(descriptor)
                    descriptor = child
                self._private(os.fstat(descriptor), directory=True)
                self._fds[self.root] = descriptor
                details = os.fstat(descriptor)
                self._identities[self.root] = (details.st_dev, details.st_ino)
                descriptor = None
            finally:
                if descriptor is not None:
                    os.close(descriptor)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def parent(self, path):
        path = Path(path)
        try:
            relative = path.parent.relative_to(self.root)
        except ValueError:
            raise UpgradeError("upgrade_exchange_path_invalid") from None
        if any(part in {".", ".."} for part in relative.parts):
            raise UpgradeError("upgrade_exchange_path_invalid")
        current = self.root
        for part in relative.parts:
            child = current / part
            if child not in self._fds:
                descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=self._fds[current])
                try:
                    details = os.fstat(descriptor)
                    self._private(details, directory=True)
                except BaseException:
                    os.close(descriptor)
                    raise
                self._fds[child] = descriptor
                self._identities[child] = (details.st_dev, details.st_ino)
            current = child
        self.require_bound()
        return self._fds[path.parent]

    def require_bound(self):
        for path, descriptor in self._fds.items():
            opened = os.fstat(descriptor)
            self._private(opened, directory=True)
            if path == self.root:
                # Also check canonical ancestors on every decision boundary.
                if path.resolve(strict=True) != path:
                    raise UpgradeError("upgrade_exchange_parent_changed")
                named = path.lstat()
            else:
                named = os.stat(path.name, dir_fd=self._fds[path.parent], follow_symlinks=False)
            self._private(named, directory=True)
            if (opened.st_dev, opened.st_ino) != self._identities[path] or (
                    named.st_dev, named.st_ino) != self._identities[path]:
                raise UpgradeError("upgrade_exchange_parent_changed")

    def artifact(self, path, expected):
        parent = self.parent(path)
        descriptor = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            before = os.fstat(descriptor)
            self._private(before, directory=False)
            digest = hashlib.sha256()
            while chunk := os.read(descriptor, 1024 * 1024):
                digest.update(chunk)
            after = os.fstat(descriptor)
            named = os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False)
            self._private(named, directory=False)
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                    or (named.st_dev, named.st_ino) != (after.st_dev, after.st_ino)):
                raise UpgradeError("upgrade_exchange_file_changed")
            actual = replace(expected, sha256=digest.hexdigest(), device_id=after.st_dev,
                file_id=after.st_ino, size_bytes=after.st_size)
            if actual != expected:
                raise UpgradeError("upgrade_exchange_file_changed")
            self.require_bound()
            return actual
        finally:
            os.close(descriptor)

    def sync_file(self, path, expected):
        self.artifact(path, expected)
        descriptor = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.parent(path))
        try:
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (expected.device_id, expected.file_id):
                raise UpgradeError("upgrade_exchange_file_changed")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self.artifact(path, expected)

    def sync(self, *paths):
        for path in paths:
            self.parent(path)
        # Include every pinned private ancestor, bottom-up through the root.
        for parent in sorted(self._fds, key=lambda value: len(value.parts), reverse=True):
            self.require_bound()
            os.fsync(self._fds[parent])
        self.require_bound()

    def __exit__(self, *args):
        for descriptor in reversed(tuple(self._fds.values())):
            os.close(descriptor)
        self._fds.clear()


class SyntheticUpgradeActivation:
    """Requires held maintenance and full drain; never grants runtime/writer rights."""
    def __init__(self, *, source_adapter, rollback, journal, auth_key, registry, fault_hook=None):
        self.source = source_adapter
        self.rollback = rollback
        self.journal = journal
        self.auth_key = auth_key
        self.registry = registry
        self.context = source_adapter.context
        self._fault_hook = fault_hook

    def _emit(self, boundary):
        if self._fault_hook is not None:
            self._fault_hook(boundary)

    def _authority(self, maintenance, drain):
        self.source.validate_context()
        if (maintenance.context != self.context or not maintenance._entered
                or maintenance.gate is not self.source.service._gate
                or maintenance.capability is None
                or maintenance.capability.purpose is not MaintenancePurpose.SCHEMA_UPGRADE
                or maintenance.gate.state is not MaintenanceState.MAINTENANCE_ACTIVE):
            raise UpgradeError("upgrade_activation_authority_required")
        expected_paths = {self.source.service.paths.final_v4.database,
            self.source.service.paths.database, self.source.candidate_path, self.rollback.rollback_path}
        runtime_paths = {self.source.service.paths.final_v4.database, self.source.service.paths.database}
        if (not isinstance(drain, ConnectionDrain) or drain.gate is not maintenance.gate
                or drain.capability is not maintenance.capability
                or drain.owner_id != self.context.operation_id
                or set(drain.paths) != expected_paths or set(drain.runtime_paths) != runtime_paths):
            raise UpgradeError("upgrade_activation_drain_mismatch")
        # Check token against the actual gate, including owner and ACTIVE state.
        maintenance.gate._require_capability(maintenance.capability,
            owner_id=self.context.operation_id)
        drain.require_drained()

    def _target(self, path, expected, source):
        self.source._no_sidecars(path)
        with closing(self.source.service._provider.connect_read_only(path,
                key_material=self.source.service.loaded.database_key.key_material)) as connection:
            inspected = DatabaseCompatibilityInspector().inspect_connection(connection)
            identity = RegisteredSchemaIdentity(inspected.version.sqlite_user_version,
                inspected.schema_identity.fingerprint, SCHEMA_FINGERPRINT_ALGORITHM)
            if identity != self.context.target:
                raise UpgradeError("upgrade_activation_target_invalid")
            require_same_content(source.main_content, database_content_evidence(connection))
        return expected

    def execute(self, *, maintenance, drain):
        """Only a fresh TARGET_VERIFIED decision may prepare and install once."""
        state = None
        try:
            self._authority(maintenance, drain)
            state = self.journal.load(self.auth_key)
            if state.context != self.context or state.phase is not UpgradePhase.TARGET_VERIFIED:
                raise UpgradeError("upgrade_activation_phase_invalid")
            self.registry.require_upgrade(self.context.source, self.context.target)
            recorded = {a.role: a for e in state.evidence for a in e.artifacts}
            main = self.source.service.paths.final_v4.database
            candidate = self.source.candidate_path
            with PinnedUpgradeFiles(self.source.root) as files:
                files.artifact(main, recorded["source"])
                files.artifact(candidate, recorded["candidate"])
                files.artifact(self.source.backup_path, recorded["backup"])
                # Maintenance-only verifier admissions remain tracked and close before exchange.
                with drain.maintenance_connections():
                    source = self.source.verify_source()
                    if source.artifact != recorded["source"]:
                        raise UpgradeError("upgrade_source_changed")
                    if self.source.verify_backup(source) != recorded["backup"]:
                        raise UpgradeError("upgrade_backup_changed")
                    self._target(candidate, recorded["candidate"], source)
                    rollback = self.rollback.create(source, recorded["backup"])
                    self.rollback.verify(source, recorded["backup"], expected=rollback)
                self._authority(maintenance, drain)
                files.artifact(self.rollback.rollback_path, rollback)
                if len({(a.device_id, a.file_id) for a in (*recorded.values(), rollback)}) != len(recorded) + 1:
                    raise UpgradeError("upgrade_exchange_alias")
                candidate_parent = files.parent(candidate)
                main_parent = files.parent(main)
                if (recorded["candidate"].device_id != recorded["source"].device_id
                        or os.fstat(candidate_parent).st_dev != os.fstat(main_parent).st_dev):
                    raise UpgradeError("upgrade_exchange_cross_device")
                capacity = os.fstatvfs(main_parent)
                reserve = max(16 * 1024 * 1024, sum(a.size_bytes for a in recorded.values()) + rollback.size_bytes)
                if capacity.f_bavail * capacity.f_frsize < reserve:
                    raise UpgradeError("upgrade_exchange_insufficient_space")
                for path, evidence in ((main, recorded["source"]), (candidate, recorded["candidate"]),
                        (self.rollback.rollback_path, rollback), (self.source.backup_path, recorded["backup"])):
                    files.sync_file(path, evidence)
                files.sync(main, candidate, self.rollback.rollback_path, self.source.backup_path)
                self._emit("after_prepared_files_sync")
                def persist(evidence):
                    nonlocal state
                    replacement = advance_upgrade(state, evidence, self.registry)
                    self.journal.save(state, replacement, self.auth_key)
                    state = replacement
                persist(UpgradeEvidence(self.context, UpgradePhase.ACTIVATION_PREPARED,
                    (recorded["source"], recorded["backup"], recorded["candidate"], rollback)))
                self._emit("after_activation_prepared")
                intent = UpgradeExchangeIntent(self.context, str(uuid4()), "activate",
                    recorded["source"], recorded["candidate"])
                persist(UpgradeEvidence(self.context, UpgradePhase.ACTIVATION_INTENT, exchange_intent=intent))
                self._emit("after_activation_intent")
                if self.journal.load(self.auth_key) != state:
                    raise UpgradeError("upgrade_activation_journal_changed")
                self._authority(maintenance, drain)
                for path, evidence in ((main, recorded["source"]), (candidate, recorded["candidate"]),
                        (self.rollback.rollback_path, rollback), (self.source.backup_path, recorded["backup"])):
                    files.artifact(path, evidence)
                self._emit("before_atomic_replace")
                # Revalidate after the test/fault boundary as well.
                self._authority(maintenance, drain)
                files.artifact(main, recorded["source"])
                files.artifact(candidate, recorded["candidate"])
                os.replace(candidate.name, main.name, src_dir_fd=candidate_parent, dst_dir_fd=main_parent)
                self._emit("after_atomic_replace")
                installed = replace(recorded["candidate"], role="live")
                files.artifact(main, installed)
                files.sync(main, candidate)
                self._emit("after_exchange_directory_sync")
                self._authority(maintenance, drain)
                files.artifact(main, installed)
                persist(UpgradeEvidence(self.context, UpgradePhase.TARGET_INSTALLED, (installed,),
                    exchange_result=UpgradeExchangeResult(self.context, intent.intent_id, installed)))
                self._emit("after_target_installed")
                maintenance.require_recovery()
                return state
        except BaseException:
            # No cleanup/rollback/retry after an ambiguous result. Preserve intent and all files.
            if maintenance._entered:
                maintenance.require_recovery()
            raise
