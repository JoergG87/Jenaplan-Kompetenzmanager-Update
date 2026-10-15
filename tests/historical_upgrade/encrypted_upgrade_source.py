"""Synthetic-only keyed source/backup/staging adapter; never activates data."""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import stat

from src.core.database_content_evidence import (database_content_evidence, require_same_content, UpgradeSourceVerification)
from src.core.schema_registry import FINAL_V4_SCHEMA_REGISTRATION
from src.core.schema_upgrade import UpgradeArtifact, UpgradeContext, UpgradeError
from src.core.timetable import TimetableEntry, TimetableValidator
from src.core.learning_report import snapshot_sha256
from src.core.learning_conference import learning_conference_snapshot_sha256
from src.security.final_v4_sqlcipher_runtime import KeyedFinalV4CompatibilityInspector
from tests.historical_upgrade.upgrade_process_lease import UpgradeProcessLease


class EncryptedUpgradeSourceAdapter:
    def __init__(self, service, lease: UpgradeProcessLease, context: UpgradeContext, *, fault_hook=None):
        self.service, self.lease, self.context = service, lease, context
        self.root = service.paths.final_v4.root
        self.workspace = self.root / "schema-upgrade-source" / context.operation_id
        self.backup_path = self.workspace / "source.jkmebackup"
        self.candidate_path = self.workspace / "candidate.sqlcipher"
        self._fault_hook = fault_hook

    def _require(self):
        self.lease.require_owner(self.context)
        loaded = self.service.loaded
        if (self.root != self.lease.lock.runtime_root
            or self.context.source != FINAL_V4_SCHEMA_REGISTRATION.identity
            or self.context.installation_id != self.service.installation_id
            or self.context.database_context_id != loaded.database_context_id
            or self.context.database_key_id != loaded.database_key_id
            or self.context.database_key_generation != loaded.database_key_generation
            or self.context.dmk_key_id != loaded.dmk_key_id
            or self.context.dmk_generation != loaded.dmk_generation):
            raise UpgradeError("upgrade_source_context_mismatch")
        expected_main = self.root / "final-v4-sqlcipher-runtime-v1" / "final-v4.sqlcipher"
        expected_companion = self.root / "final-v4-sqlcipher-runtime-v1" / "documents-v1.sqlcipher"
        if (self.service.paths.final_v4.database.resolve() != expected_main
            or self.service.paths.database.resolve() != expected_companion
            or not self.service.paths.storage_root.resolve().is_relative_to(self.root)
            or self.backup_path != self.workspace / "source.jkmebackup"
            or self.candidate_path != self.workspace / "candidate.sqlcipher"):
            raise UpgradeError("upgrade_artifact_path_invalid")
        expected = self.root / "schema-upgrade-source" / self.context.operation_id
        if self.workspace.resolve() != expected:
            raise UpgradeError("upgrade_workspace_unsafe")

    def validate_context(self):
        self._require()

    def _emit(self, boundary):
        if self._fault_hook is not None:
            self._fault_hook(boundary)

    def _directory(self):
        self._require()
        for path in (self.workspace.parent, self.workspace):
            path.mkdir(mode=0o700, exist_ok=True)
            details = path.lstat()
            if path.is_symlink() or not stat.S_ISDIR(details.st_mode) or stat.S_IMODE(details.st_mode) != 0o700:
                raise UpgradeError("upgrade_workspace_unsafe")

    @staticmethod
    def _no_sidecars(path):
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                raise UpgradeError("upgrade_sidecar_recovery_required")

    def _inspect(self, path, *, main):
        self._no_sidecars(path)
        try:
            with closing(self.service._provider.connect_read_only(
                    path, key_material=self.service.loaded.database_key.key_material)) as connection:
                if main:
                    KeyedFinalV4CompatibilityInspector().inspect_connection(connection)
                    self._references(connection)
                else:
                    self.service._inspect_companion(path, self.service.loaded.database_key.key_material)
                return database_content_evidence(connection)
        except UpgradeError:
            raise
        except Exception:
            raise UpgradeError("upgrade_keyed_source_invalid") from None

    @staticmethod
    def _references(connection):
        subjects = {row[0] for row in connection.execute("SELECT DISTINCT subject_id FROM competencies")}
        targets = {kind: {row[0] for row in connection.execute(f"SELECT {column} FROM {table}")}
                   for kind, table, column in (("group", "groups", "group_id"),
                       ("course", "courses", "course_id"), ("course_group", "course_groups", "course_group_id"))}
        entries = tuple(TimetableEntry(**dict(row)) for row in connection.execute("SELECT * FROM timetable_entries"))
        try:
            for entry in entries:
                TimetableValidator().validate(entry, valid_subject_ids=subjects,
                    valid_target_ids=targets, existing_entries=entries)
            for table, hash_function in (("learning_report_revisions", snapshot_sha256),
                    ("learning_conference_revisions", learning_conference_snapshot_sha256)):
                for version, payload, digest in connection.execute(
                        f"SELECT snapshot_schema_version, snapshot_json, snapshot_sha256 FROM {table}"):
                    if version != 1 or hash_function(payload) != digest or not isinstance(json.loads(payload), dict):
                        raise ValueError
        except Exception:
            raise UpgradeError("upgrade_domain_reference_invalid") from None

    def _artifact(self, path, role):
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise UpgradeError("upgrade_artifact_unsafe")
            digest = hashlib.sha256()
            while chunk := os.read(descriptor, 1024 * 1024):
                digest.update(chunk)
            after = os.fstat(descriptor)
            named = Path(path).lstat()
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (after.st_dev, after.st_ino) != (named.st_dev, named.st_ino)
                or Path(path).is_symlink()):
                raise UpgradeError("upgrade_artifact_changed")
            return UpgradeArtifact(role, self.context.operation_id, digest.hexdigest(),
                after.st_dev, after.st_ino, after.st_size, self.context.source)
        finally:
            os.close(descriptor)

    def verify_source(self):
        self._require()
        source = self.service.paths.final_v4.database
        companion = self.service.paths.database
        before = self._artifact(source, "source")
        main = self._inspect(source, main=True)
        companion_content = self._inspect(companion, main=False)
        self.service.opened.documents.validate_restart()
        self.service._validate_crossbindings(source, companion, self.service.loaded.database_key.key_material)
        if self._artifact(source, "source") != before:
            raise UpgradeError("upgrade_source_changed")
        return UpgradeSourceVerification(before, main, companion_content)

    def create_backup(self):
        self._directory()
        if self.backup_path.exists() or self.backup_path.is_symlink():
            raise UpgradeError("upgrade_unbound_backup_present")
        self.service.create_during_maintenance(self.backup_path)
        self._emit("after_backup_publication")

    def verify_backup(self, source):
        self._require()
        with self.service.verified_snapshot(self.backup_path) as snapshot:
            require_same_content(source.main_content, self._inspect(snapshot.database_path, main=True))
            require_same_content(source.companion_content, self._inspect(snapshot.companion_path, main=False))
            artifact = self._artifact(self.backup_path, "backup")
            if artifact.sha256 != snapshot.result.container_sha256:
                raise UpgradeError("upgrade_backup_changed")
            return artifact

    def create_staging(self, source, backup):
        self._directory()
        with self.service.verified_snapshot(self.backup_path) as snapshot:
            if self._artifact(self.backup_path, "backup") != backup:
                raise UpgradeError("upgrade_backup_changed")
            require_same_content(source.main_content, self._inspect(snapshot.database_path, main=True))
            require_same_content(source.companion_content, self._inspect(snapshot.companion_path, main=False))
            self._no_sidecars(snapshot.database_path)
            copied_from = self._artifact(snapshot.database_path, "source")
            identity = None
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self.candidate_path, flags, 0o600)
            try:
                details = os.fstat(descriptor); identity = (details.st_dev, details.st_ino)
                with os.fdopen(descriptor, "wb") as target, snapshot.database_path.open("rb") as original:
                    while chunk := original.read(1024 * 1024):
                        target.write(chunk)
                        self._emit("during_staging_copy")
                    target.flush(); os.fsync(target.fileno())
                self._emit("after_staging_copy")
                fd = os.open(self.workspace, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try: os.fsync(fd)
                finally: os.close(fd)
                candidate = self.verify_staging(source)
                if (candidate.sha256 != copied_from.sha256
                    or self._artifact(snapshot.database_path, "source") != copied_from):
                    raise UpgradeError("upgrade_staging_copy_mismatch")
                return candidate
            except BaseException:
                if identity is not None:
                    current = self.candidate_path.lstat()
                    if not self.candidate_path.is_symlink() and (current.st_dev, current.st_ino) == identity:
                        self.candidate_path.unlink()
                raise

    def verify_staging(self, source):
        self._require()
        before = self._artifact(self.candidate_path, "candidate")
        mode = stat.S_IMODE(self.candidate_path.lstat().st_mode)
        if mode != 0o600:
            raise UpgradeError("upgrade_staging_permissions_invalid")
        require_same_content(source.main_content, self._inspect(self.candidate_path, main=True))
        after = self._artifact(self.candidate_path, "candidate")
        if after != before:
            raise UpgradeError("upgrade_staging_changed")
        return after
