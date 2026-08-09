"""Same-installation live restore strategy for the gated Final-V4 runtime.

The module plugs Cipher-specific preflight, component replacement, keyed
verification and rollback into the existing productive restore state machine.
It deliberately has no UI or product-default composition.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys
from typing import Callable, Mapping

from src.core.observation_uow import ObservationWriterLock
from src.core.restore_runtime import (
    HANDOFF_MAX_AGE,
    RESTORE_HANDOFF_VERSION,
    RESTORE_JOURNAL_VERSION,
    RESTORE_RESUME_TOKEN_VERSION,
    ProductiveRestoreService,
    RestoreExecutionResult,
    RestoreHandoffError,
    RestoreHandoffResult,
    RestoreJournal,
    RestoreJournalError,
    RestoreManualRecoveryRequired,
    RestorePreflightError,
    RestoreRecoveryResult,
    RestoreReplacementError,
    RestoreRuntimeError,
    RestoreTransactionPaths,
    RuntimeInstanceLock,
    _atomic_write_json,
    _evidence_matches,
    _fsync_directory,
    _fsync_path,
    _parse_utc,
    _path_evidence,
    _read_canonical_json,
    _tree_evidence,
    _utc_now,
    _utc_timestamp,
    _validate_build_metadata,
    restore_transaction_paths,
)
from src.security.backup_container import canonical_json
from src.security.database_keys import derive_domain_separated_key
from src.security.data_keys import (
    DataKeyset,
    DataKeysetRuntimePhase,
    DataKeysetStatus,
    DataMasterKeyStoreStatus,
    LoadedDataMasterKey,
    data_master_key_fingerprint,
)
from src.security.database_key_runtime import (
    DatabaseKeyRuntimePaths,
    LoadedDatabaseKeyRuntime,
)
from src.security.database_keys import DatabaseKeyEnvelopeService
from src.security.infrastructure.data_keyset_repository import (
    DATA_KEYSET_STORE_SCHEMA_VERSION,
)
from src.security.infrastructure.data_master_key_store import (
    build_platform_data_master_key_store,
)
from src.security.infrastructure.database_key_envelope_repository import (
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from src.security.final_v4_backup_runtime import (
    FINAL_V4_BACKUP_MANIFEST_FILENAME,
    FinalV4EncryptedBackupError,
    FinalV4EncryptedBackupManifestV1,
    FinalV4EncryptedBackupService,
    FinalV4EncryptedSafetyBackup,
)


FINAL_V4_LIVE_RESTORE_KIND = "final_v4_encrypted_same_installation"
FINAL_V4_LIVE_RESTORE_HANDOFF_VERSION = 1
FINAL_V4_LIVE_RESTORE_AUTH_PURPOSE = (
    "jenaplan-kompetenzmanager/final-v4-live-restore-handoff/v1"
)
FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY = "encrypted-restore-safety"
FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY = "encrypted-restore-staging"
FINAL_V4_LIVE_RESTORE_COMPONENTS = (
    "key_runtime_metadata",
    "final_v4_main_database",
    "document_companion_database",
    "managed_document_storage",
)
_HASH_LENGTH = 64


@dataclass(frozen=True, slots=True)
class FinalV4LiveRestorePreparation:
    handoff: RestoreHandoffResult
    safety_backup: FinalV4EncryptedSafetyBackup = field(repr=False)


@dataclass(frozen=True, slots=True)
class _CipherComponent:
    role: str
    live: Path
    prepared: Path
    rollback: Path
    failed_new: Path


class FinalV4EncryptedRestoreHandoffService:
    """DMK-authenticated handoff using the existing one-time journal contract."""

    def __init__(
        self,
        backup_service: FinalV4EncryptedBackupService | None = None,
        *,
        runtime_root: Path | None = None,
        loaded_keys: LoadedDatabaseKeyRuntime | None = None,
        installation_id: str | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.backup_service = backup_service
        if backup_service is not None:
            runtime_root = backup_service.paths.final_v4.key_runtime.root
            loaded_keys = backup_service.loaded
            installation_id = backup_service.opened.installation_id
        if runtime_root is None or loaded_keys is None or installation_id is None:
            raise ValueError("Cipher-Handoff-Kontext fehlt.")
        self.runtime_root = Path(runtime_root).expanduser().resolve(strict=True)
        self.loaded_keys = loaded_keys
        self.installation_id = installation_id
        self.now = now or (lambda: datetime.now(UTC))

    def create(
        self,
        *,
        staging_root: Path,
        expected_container_sha256: str,
        safety_backup: FinalV4EncryptedSafetyBackup,
        restore_id: str,
        app_version: str,
        build_commit: str,
        source_tree_state: str | None = None,
    ) -> RestoreHandoffResult:
        if self.backup_service is None:
            raise RestoreHandoffError("Der Cipher-Handoff kann nicht vorbereitet werden.")
        root = self._runtime_root()
        paths = restore_transaction_paths(root, restore_id)
        if paths.handoff.exists() or paths.consumed_handoff.exists() or paths.transaction.exists():
            raise RestoreHandoffError("Der Cipher-Restore existiert bereits.")
        _validate_build_metadata(app_version, build_commit, source_tree_state)
        ready = self.backup_service.verify_restore_ready(
            staging_root,
            expected_container_sha256=expected_container_sha256,
        )
        if ready.staging_root.parent != root / FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY:
            raise RestoreHandoffError("Das Cipher-Restore-Staging ist nicht gebunden.")
        verified_safety = self.backup_service.verify(safety_backup.result.path)
        if verified_safety != safety_backup.result:
            raise RestoreHandoffError("Das Cipher-Sicherheitsbackup ist widerspruechlich.")
        safety_path = verified_safety.path.resolve(strict=True)
        if safety_path.parent != root / FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY:
            raise RestoreHandoffError("Das Cipher-Sicherheitsbackup liegt ausserhalb der Zulassung.")

        nonce = secrets.token_urlsafe(32)
        created_at = _utc_timestamp(self.now())
        payload: dict[str, object] = {
            "app_version": app_version,
            "build_commit": build_commit,
            "container_sha256": expected_container_sha256,
            "created_at": created_at,
            "database_context_id": ready.manifest.database_context_id,
            "excluded_evidence": _excluded_evidence(root),
            "handoff_version": RESTORE_HANDOFF_VERSION,
            "installation_id": ready.manifest.installation_id,
            "live_restore_handoff_version": FINAL_V4_LIVE_RESTORE_HANDOFF_VERSION,
            "manifest_sha256": hashlib.sha256(ready.manifest.to_bytes()).hexdigest(),
            "nonce": nonce,
            "restore_id": restore_id,
            "restore_kind": FINAL_V4_LIVE_RESTORE_KIND,
            "runtime_root": str(root),
            "safety_backup_relative": safety_path.relative_to(root).as_posix(),
            "safety_backup_sha256": verified_safety.container_sha256,
            "source_tree_state": source_tree_state,
            "staging_root_relative": ready.staging_root.relative_to(root).as_posix(),
        }
        payload["authentication_hmac_sha256"] = self._authenticate(payload)
        RestoreJournal(paths).create(
            {
                "archive_sha256": expected_container_sha256,
                "completed_renames": [],
                "components": {},
                "created_at": created_at,
                "error_class": None,
                "journal_version": RESTORE_JOURNAL_VERSION,
                "next_step": "consume_handoff",
                "phase": "handoff_created",
                "prepared_database_sha256": str(payload["manifest_sha256"]),
                "rename_intent": None,
                "restart_handshake": {"attempts": 0, "status": "not_started"},
                "restore_id": restore_id,
                "restore_kind": FINAL_V4_LIVE_RESTORE_KIND,
                "safety_backup_sha256": verified_safety.container_sha256,
            }
        )
        paths.handoff.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            _atomic_write_json(paths.handoff, payload, exclusive=True)
        except Exception:
            RestoreJournal(paths).transition(
                "aborted_before_replacement",
                next_step="none",
                error_class="RestoreHandoffWriteError",
            )
            raise
        return RestoreHandoffResult(
            restore_id,
            nonce,
            paths.handoff,
            expected_container_sha256,
            str(payload["manifest_sha256"]),
        )

    def consume(
        self,
        handoff_path: Path,
        *,
        expected_nonce: str,
    ) -> tuple[RestoreTransactionPaths, dict[str, object]]:
        try:
            handoff_path = Path(handoff_path).expanduser().resolve(strict=True)
        except OSError as error:
            raise RestoreHandoffError("Der Cipher-Handoff fehlt.") from error
        payload = _read_canonical_json(handoff_path, RestoreHandoffError)
        required = {
            "app_version",
            "authentication_hmac_sha256",
            "build_commit",
            "container_sha256",
            "created_at",
            "database_context_id",
            "excluded_evidence",
            "handoff_version",
            "installation_id",
            "live_restore_handoff_version",
            "manifest_sha256",
            "nonce",
            "restore_id",
            "restore_kind",
            "runtime_root",
            "safety_backup_relative",
            "safety_backup_sha256",
            "source_tree_state",
            "staging_root_relative",
        }
        if (
            set(payload) != required
            or payload.get("handoff_version") != RESTORE_HANDOFF_VERSION
            or payload.get("live_restore_handoff_version")
            != FINAL_V4_LIVE_RESTORE_HANDOFF_VERSION
            or payload.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
            or not secrets.compare_digest(str(payload.get("nonce", "")), expected_nonce)
        ):
            raise RestoreHandoffError("Der Cipher-Handoff ist ungueltig.")
        created_at = _parse_utc(str(payload.get("created_at", "")))
        now = datetime.now(UTC)
        if created_at > now + timedelta(minutes=1) or now - created_at > HANDOFF_MAX_AGE:
            raise RestoreHandoffError("Der Cipher-Handoff ist abgelaufen.")
        root = self._runtime_root()
        if payload.get("runtime_root") != str(root):
            raise RestoreHandoffError("Der Cipher-Handoff besitzt einen falschen Root.")
        if (
            payload.get("installation_id") != self.installation_id
            or payload.get("database_context_id")
            != self.loaded_keys.database_context_id
        ):
            raise RestoreHandoffError("Der Cipher-Handoff besitzt einen falschen Kontext.")
        paths = restore_transaction_paths(root, str(payload.get("restore_id", "")))
        if handoff_path != paths.handoff or paths.consumed_handoff.exists():
            raise RestoreHandoffError("Der Cipher-Handoff wurde bereits konsumiert.")
        _validate_build_metadata(
            str(payload.get("app_version", "")),
            str(payload.get("build_commit", "")),
            payload.get("source_tree_state"),
        )
        for name in ("container_sha256", "manifest_sha256", "safety_backup_sha256"):
            value = payload.get(name)
            if not _is_hash(value):
                raise RestoreHandoffError("Der Cipher-Handoff enthaelt einen ungueltigen Hash.")
        observed_hmac = str(payload["authentication_hmac_sha256"])
        unsigned = dict(payload)
        del unsigned["authentication_hmac_sha256"]
        if not hmac.compare_digest(observed_hmac, self._authenticate(unsigned)):
            raise RestoreHandoffError("Der Cipher-Handoff ist nicht authentisiert.")
        for name in ("staging_root_relative", "safety_backup_relative"):
            _resolve_relative(root, str(payload[name]))
        os.rename(paths.handoff, paths.consumed_handoff)
        os.chmod(paths.consumed_handoff, 0o600)
        _fsync_directory(paths.consumed_handoff.parent)
        return paths, payload

    def _runtime_root(self) -> Path:
        return self.runtime_root

    def _authenticate(self, payload: Mapping[str, object]) -> str:
        loaded = self.loaded_keys
        key = derive_domain_separated_key(
            loaded.dmk,
            purpose=FINAL_V4_LIVE_RESTORE_AUTH_PURPOSE,
            derivation_version=1,
            context={
                "database_context_id": loaded.database_context_id,
                "installation_id": self.installation_id,
            },
        ).key_material
        return hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()


class FinalV4EncryptedLiveRestoreService(ProductiveRestoreService):
    """Cipher strategy for the existing worker/journal/restart state machine."""

    def __init__(
        self,
        backup_service: FinalV4EncryptedBackupService | None,
        *,
        handoff_service: FinalV4EncryptedRestoreHandoffService | None = None,
        backup_service_factory: Callable[[], FinalV4EncryptedBackupService]
        | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        if backup_service is None and (
            handoff_service is None or backup_service_factory is None
        ):
            raise ValueError("Cipher-Restore-Komposition fehlt.")
        self.backup_service = backup_service
        self._backup_service_factory = backup_service_factory
        self.cipher_handoff = handoff_service or FinalV4EncryptedRestoreHandoffService(
            backup_service
        )
        self._fault_hook = fault_hook
        super().__init__(handoff_service=self.cipher_handoff)

    @contextmanager
    def _execution_lock(self, paths: RestoreTransactionPaths):
        if self.backup_service is None:
            if self._backup_service_factory is None:
                raise RestorePreflightError("Die Cipher-Runtime ist nicht komponierbar.")
            self.backup_service = self._backup_service_factory()
        lock_root = self.backup_service.paths.final_v4.runtime_root / ".observation-staging"
        with ObservationWriterLock(lock_root):
            yield

    def _recover_pending_writes(self, paths: RestoreTransactionPaths) -> None:
        self.backup_service.opened.documents.validate_restart()

    def _preflight(
        self,
        paths: RestoreTransactionPaths,
        handoff: Mapping[str, object],
        journal: RestoreJournal,
    ) -> str:
        root = paths.runtime_root
        staging_root = _resolve_relative(root, str(handoff["staging_root_relative"]))
        safety_path = _resolve_relative(root, str(handoff["safety_backup_relative"]))
        safety = self.backup_service.verify(safety_path)
        if safety.container_sha256 != handoff["safety_backup_sha256"]:
            raise RestorePreflightError("Das Cipher-Sicherheitsbackup ist nicht beweisbar.")
        ready = self.backup_service.verify_restore_ready(
            staging_root,
            expected_container_sha256=str(handoff["container_sha256"]),
        )
        if hashlib.sha256(ready.manifest.to_bytes()).hexdigest() != handoff["manifest_sha256"]:
            raise RestorePreflightError("RESTORE_READY und Handoff widersprechen sich.")
        self._checkpoint_live_databases()
        self._require_no_sidecars(root)
        excluded = handoff.get("excluded_evidence")
        if not isinstance(excluded, dict) or _excluded_evidence(root) != excluded:
            raise RestorePreflightError(
                "Ausgeschlossene Security- oder Preference-Daten widersprechen dem Handoff."
            )
        components = self._components(paths, staging_root)
        component_state: dict[str, object] = {}
        for component in components:
            if (
                not component.live.exists()
                or component.live.is_symlink()
                or not component.prepared.exists()
                or component.prepared.is_symlink()
            ):
                raise RestorePreflightError("Der Cipher-Dateisatz ist unvollstaendig.")
            component_state[component.role] = {
                "before": _path_evidence(component.live),
                "failed_path": str(component.failed_new),
                "prepared": _path_evidence(component.prepared),
                "rollback_path": str(component.rollback),
            }
        if tuple(component_state) != FINAL_V4_LIVE_RESTORE_COMPONENTS:
            raise RestorePreflightError("Der Cipher-Komponentenplan ist ungueltig.")
        if len({component.live.stat().st_dev for component in components} | {component.prepared.stat().st_dev for component in components}) != 1:
            raise RestorePreflightError("Cipher-Swap und Staging liegen nicht auf demselben Dateisystem.")
        required = sum(int(record["before"]["size_bytes"]) + int(record["prepared"]["size_bytes"]) for record in component_state.values())
        if shutil.disk_usage(root).free < required + 10 * 1024 * 1024:
            raise RestorePreflightError("Der freie Speicher reicht fuer Cipher-Restore und Rollback nicht aus.")
        journal.transition(
            "maintenance",
            next_step="mark_preflight_verified",
            components=component_state,
            excluded_evidence=excluded,
            prepared_manifest_sha256=str(handoff["manifest_sha256"]),
            safety_backup_sha256=safety.container_sha256,
        )
        self._emit("before_swap")
        return safety.container_sha256

    def _replace(self, paths: RestoreTransactionPaths, journal: RestoreJournal) -> None:
        staging_root = _resolve_relative(
            paths.runtime_root,
            str(self._handoff_payload(paths)["staging_root_relative"]),
        )
        components = self._components(paths, staging_root)
        for component in components:
            _journaled_rename(
                journal,
                name=f"old_{component.role}_to_rollback",
                source=component.live,
                target=component.rollback,
            )
            if component.role == "final_v4_main_database":
                self._emit("during_swap")
                self._emit("between_main_and_companion")
        for component in components:
            if component.role == "managed_document_storage":
                self._emit("after_databases_before_documents")
                self._emit("during_documents")
            _journaled_rename(
                journal,
                name=f"prepared_{component.role}_to_live",
                source=component.prepared,
                target=component.live,
            )
        self._emit("after_swap_before_reopen")

    def _verify_new_live(
        self,
        paths: RestoreTransactionPaths,
        handoff: Mapping[str, object],
        documents: Mapping[str, object],
        expected_documents: object,
    ) -> None:
        del documents, expected_documents
        manifest = _read_manifest(
            _resolve_relative(paths.runtime_root, str(handoff["staging_root_relative"]))
        )
        self.backup_service.verify_live_runtime(paths.runtime_root, manifest=manifest)
        self._verify_excluded(paths)
        self._emit("after_reopen")

    def _replacement_mutated(
        self,
        paths: RestoreTransactionPaths,
        state: Mapping[str, object],
    ) -> bool:
        components = state.get("components")
        if not isinstance(components, dict) or not components:
            return False
        staging_root = _resolve_relative(
            paths.runtime_root,
            str(self._handoff_payload(paths)["staging_root_relative"]),
        )
        for component in self._components(paths, staging_root):
            record = components.get(component.role)
            if not isinstance(record, dict) or not isinstance(record.get("before"), dict):
                raise RestoreJournalError("Eine Cipher-Komponente ist nicht beweisbar.")
            if component.rollback.exists() or component.failed_new.exists():
                return True
            if not _evidence_matches(component.live, record["before"]):
                return True
            if not component.prepared.exists():
                return True
        return False

    def _rollback(self, paths: RestoreTransactionPaths, journal: RestoreJournal) -> None:
        state = journal.read()
        components_state = state.get("components")
        if not isinstance(components_state, dict):
            raise RestoreManualRecoveryRequired("Cipher-Rollbackkomponenten fehlen.")
        journal.transition("rollback_started", next_step="restore_old_cipher_runtime")
        staging_root = _resolve_relative(
            paths.runtime_root,
            str(self._handoff_payload(paths)["staging_root_relative"]),
        )
        for component in reversed(self._components(paths, staging_root)):
            record = components_state.get(component.role)
            if not isinstance(record, dict) or not isinstance(record.get("before"), dict):
                raise RestoreManualRecoveryRequired("Cipher-Rollbackevidenz fehlt.")
            before = record["before"]
            if component.live.exists():
                if component.failed_new.exists():
                    raise RestoreManualRecoveryRequired("Der Cipher-Mischzustand ist uneindeutig.")
                if _evidence_matches(component.live, before) and not component.rollback.exists():
                    continue
                _journaled_rename(
                    journal,
                    name=f"new_{component.role}_to_failed",
                    source=component.live,
                    target=component.failed_new,
                )
            if component.rollback.exists():
                if not _evidence_matches(component.rollback, before):
                    raise RestoreManualRecoveryRequired("Cipher-Rollbackevidenz weicht ab.")
                _journaled_rename(
                    journal,
                    name=f"old_{component.role}_to_live",
                    source=component.rollback,
                    target=component.live,
                )
            if not _evidence_matches(component.live, before):
                raise RestoreManualRecoveryRequired("Der alte Cipher-Bestand ist nicht vollstaendig.")
        safety_path = _resolve_relative(
            paths.runtime_root,
            str(self._handoff_payload(paths)["safety_backup_relative"]),
        )
        safety = self.backup_service.verify(safety_path)
        self.backup_service.verify_live_runtime(
            paths.runtime_root,
            manifest=safety.manifest,
            enforce_artifact_hashes=False,
        )
        self._verify_excluded(paths)
        journal.transition("rolled_back", next_step="none", error_class=None)

    @staticmethod
    def _restore_preflight_state(paths: RestoreTransactionPaths) -> None:
        del paths

    def _verify_excluded(self, paths: RestoreTransactionPaths) -> None:
        state = RestoreJournal(paths).read()
        expected = state.get("excluded_evidence")
        if not isinstance(expected, dict) or _excluded_evidence(paths.runtime_root) != expected:
            raise RestoreReplacementError("Ausgeschlossene Security- oder Preference-Daten wurden veraendert.")

    def _components(
        self,
        paths: RestoreTransactionPaths,
        staging_root: Path,
    ) -> tuple[_CipherComponent, ...]:
        live_key = self.backup_service.paths.final_v4.key_runtime.metadata_root
        live_final = self.backup_service.paths.final_v4.runtime_root
        prepared_key = staging_root / live_key.name
        prepared_final = staging_root / live_final.name
        return (
            _CipherComponent(
                "key_runtime_metadata",
                live_key,
                prepared_key,
                paths.rollback / live_key.name,
                paths.failed_new / live_key.name,
            ),
            _CipherComponent(
                "final_v4_main_database",
                self.backup_service.paths.final_v4.database,
                prepared_final / self.backup_service.paths.final_v4.database.name,
                paths.rollback / self.backup_service.paths.final_v4.database.name,
                paths.failed_new / self.backup_service.paths.final_v4.database.name,
            ),
            _CipherComponent(
                "document_companion_database",
                self.backup_service.paths.database,
                prepared_final / self.backup_service.paths.database.name,
                paths.rollback / self.backup_service.paths.database.name,
                paths.failed_new / self.backup_service.paths.database.name,
            ),
            _CipherComponent(
                "managed_document_storage",
                self.backup_service.paths.container_root,
                prepared_final / self.backup_service.paths.container_root.name,
                paths.rollback / self.backup_service.paths.container_root.name,
                paths.failed_new / self.backup_service.paths.container_root.name,
            ),
        )

    @staticmethod
    def _handoff_payload(paths: RestoreTransactionPaths) -> dict[str, object]:
        return _read_canonical_json(paths.consumed_handoff, RestoreHandoffError)

    def _require_no_sidecars(self, root: Path) -> None:
        for path in (
            self.backup_service.paths.final_v4.database,
            self.backup_service.paths.database,
            self.backup_service.paths.final_v4.key_runtime.keyset_metadata,
        ):
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(f"{path}{suffix}")
                if sidecar.exists() or sidecar.is_symlink():
                    raise RestorePreflightError("Ein Cipher-Sidecar blockiert den Live-Restore.")
        if self.backup_service.paths.final_v4.key_runtime.root != root:
            raise RestorePreflightError("Der Cipher-Runtime-Root ist widerspruechlich.")

    def _checkpoint_live_databases(self) -> None:
        connections = (
            lambda: self.backup_service._main_factory.connect(
                self.backup_service.paths.final_v4.database,
                create=False,
            ),
            lambda: self.backup_service._document_factory.connect(create=False),
            lambda: sqlite3.connect(
                self.backup_service.paths.final_v4.key_runtime.keyset_metadata,
                timeout=5.0,
            ),
        )
        try:
            for connect in connections:
                connection = connect()
                try:
                    result = connection.execute(
                        "PRAGMA wal_checkpoint(TRUNCATE)"
                    ).fetchone()
                    if result is not None and int(result[0]) != 0:
                        raise RestorePreflightError(
                            "Ein Cipher-WAL konnte nicht geschlossen werden."
                        )
                finally:
                    connection.close()
            for path in (
                self.backup_service.paths.final_v4.database,
                self.backup_service.paths.database,
                self.backup_service.paths.final_v4.key_runtime.keyset_metadata,
            ):
                for suffix in ("-wal", "-shm"):
                    sidecar = Path(f"{path}{suffix}")
                    if sidecar.exists():
                        sidecar.unlink()
                        _fsync_directory(sidecar.parent)
        except RestoreRuntimeError:
            raise
        except Exception:
            raise RestorePreflightError(
                "Die Cipher-Datenbanken konnten nicht vollstaendig geschlossen werden."
            ) from None

    def _emit(self, boundary: str) -> None:
        if self._fault_hook is not None:
            self._fault_hook(boundary)

    @staticmethod
    def _launch_restart(
        paths: RestoreTransactionPaths,
        token: str,
        lock: RuntimeInstanceLock,
    ) -> subprocess.Popen[bytes] | None:
        try:
            executable = Path(sys.executable).expanduser().resolve(strict=True)
        except OSError:
            return None
        arguments = [
            "--final-v4-restore-confirm",
            "--runtime-root",
            str(paths.runtime_root),
            "--restore-id",
            paths.transaction.name,
            "--restore-token",
            token,
            "--restore-lock-fd",
            str(lock.fileno),
        ]
        environment = dict(os.environ)
        if getattr(sys, "frozen", False):
            command = [str(executable), *arguments]
            environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
            working_directory = paths.runtime_root
        else:
            command = [
                str(executable),
                "-m",
                "src.desktop_app.main",
                *arguments,
            ]
            working_directory = Path(__file__).resolve().parents[2]
        try:
            return subprocess.Popen(
                command,
                pass_fds=(lock.fileno,),
                close_fds=True,
                cwd=working_directory,
                start_new_session=os.name == "posix",
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            return None


def prepare_final_v4_live_restore(
    *,
    backup_service: FinalV4EncryptedBackupService,
    lock: RuntimeInstanceLock,
    staging_root: Path,
    expected_container_sha256: str,
    restore_id: str,
    app_version: str,
    build_commit: str,
    source_tree_state: str | None = None,
) -> FinalV4LiveRestorePreparation:
    """Freeze writers, create+verify safety backup, then publish the handoff."""

    root = backup_service.paths.final_v4.key_runtime.root.resolve(strict=True)
    if lock.runtime_root != root or lock._file is None:
        raise RestorePreflightError("Der Cipher-Livebestand ist nicht instanzgesperrt.")
    backup_root = root / FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY
    backup_root.mkdir(mode=0o700, exist_ok=True)
    safety_path = backup_root / f"safety-{restore_id}.jkmebackup"
    safety = backup_service.create_safety_backup(safety_path)
    try:
        handoff = FinalV4EncryptedRestoreHandoffService(backup_service).create(
            staging_root=staging_root,
            expected_container_sha256=expected_container_sha256,
            safety_backup=safety,
            restore_id=restore_id,
            app_version=app_version,
            build_commit=build_commit,
            source_tree_state=source_tree_state,
        )
    except Exception:
        safety.abort()
        raise
    return FinalV4LiveRestorePreparation(handoff, safety)


def launch_prepared_final_v4_restore(
    *,
    preparation: FinalV4LiveRestorePreparation,
    lock: RuntimeInstanceLock,
    launch_plan=None,
):
    """Use the established worker takeover and release the freeze fail-closed."""

    from src.desktop_app.restore_worker import (
        RESTORE_MODE_FINAL_V4_ENCRYPTED,
        launch_restore_worker,
    )

    try:
        process = launch_restore_worker(
            handoff=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            launch_plan=launch_plan,
            restore_mode=RESTORE_MODE_FINAL_V4_ENCRYPTED,
        )
    except Exception:
        try:
            paths = restore_transaction_paths(
                lock.runtime_root,
                preparation.handoff.restore_id,
            )
            journal = RestoreJournal(paths)
            state = journal.read()
            if state.get("phase") in {"handoff_created", "worker_started"}:
                journal.transition(
                    "aborted_before_replacement",
                    next_step="none",
                )
        except RestoreRuntimeError:
            pass
        preparation.safety_backup.abort()
        raise
    preparation.safety_backup.transfer_to_worker()
    return process


def confirm_final_v4_restore_startup(
    *,
    backup_service: FinalV4EncryptedBackupService | None = None,
    runtime_root: Path,
    restore_id: str,
    token: str,
    account_loader=None,
    key_store=None,
) -> RestoreRecoveryResult:
    """Consume the resume token only after a fresh keyed full-runtime reopen."""

    root = Path(runtime_root).expanduser().resolve(strict=True)
    if (
        backup_service is not None
        and backup_service.paths.final_v4.key_runtime.root.resolve(strict=True) != root
    ):
        raise RestoreHandoffError("Der Cipher-Restart-Root ist widerspruechlich.")
    paths = restore_transaction_paths(root, restore_id)
    journal = RestoreJournal(paths)
    state = journal.read()
    if state.get("phase") != "installed_verified" or state.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND:
        raise RestoreJournalError("Der Cipher-Restore erwartet keinen Startup-Handshake.")
    payload = _read_canonical_json(paths.resume_token, RestoreHandoffError)
    if (
        payload.get("resume_token_version") != RESTORE_RESUME_TOKEN_VERSION
        or payload.get("restore_id") != restore_id
        or not secrets.compare_digest(str(payload.get("token", "")), token)
        or _parse_utc(str(payload.get("expires_at", ""))) < datetime.now(UTC)
        or paths.consumed_resume_token.exists()
    ):
        raise RestoreHandoffError("Der Cipher-Resume-Token ist ungueltig.")
    handoff = _read_canonical_json(paths.consumed_handoff, RestoreHandoffError)
    if (
        handoff.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
        or handoff.get("runtime_root") != str(root)
    ):
        raise RestoreHandoffError("Der Cipher-Restart-Handoff ist widerspruechlich.")
    staging_root = _resolve_relative(root, str(handoff["staging_root_relative"]))
    manifest = _read_manifest(staging_root)
    if backup_service is None:
        loader = account_loader or _security_account_loader(root)
        handoff, loaded = _bootstrap_handoff_context(
            paths,
            state,
            account_loader=loader,
            key_store=key_store,
        )
        verifier = _build_bootstrap_verifier(
            root,
            loaded=loaded,
            installation_id=str(handoff["installation_id"]),
        )
    else:
        verifier = backup_service
    verifier.verify_live_runtime(root, manifest=manifest)
    expected_excluded = state.get("excluded_evidence")
    if not isinstance(expected_excluded, dict) or _excluded_evidence(root) != expected_excluded:
        raise RestoreReplacementError("Ausgeschlossene Daten widersprechen dem Restart.")
    os.rename(paths.resume_token, paths.consumed_resume_token)
    _fsync_directory(paths.transaction)
    handshake = dict(state.get("restart_handshake", {}))
    handshake.update({"status": "confirmed", "confirmed_at": _utc_now()})
    journal.transition("completed", next_step="none", restart_handshake=handshake)
    return RestoreRecoveryResult("completed", restore_id)


def recover_interrupted_final_v4_restore(
    *,
    runtime_root: Path,
    backup_service: FinalV4EncryptedBackupService | None = None,
    account_loader=None,
    key_store=None,
) -> RestoreRecoveryResult:
    """Recover one non-terminal Cipher journal before fachlicher startup."""

    root = Path(runtime_root).expanduser().resolve(strict=True)
    transaction_root = root / "restore-transactions"
    if not transaction_root.exists():
        return RestoreRecoveryResult("normal_start")
    candidates: list[tuple[RestoreTransactionPaths, dict[str, object]]] = []
    for child in sorted(transaction_root.iterdir()):
        if child.is_symlink() or not child.is_dir():
            raise RestoreManualRecoveryRequired(
                "Der Cipher-Restore-Transaktionsbereich ist widerspruechlich."
            )
        paths = restore_transaction_paths(root, child.name)
        state = RestoreJournal(paths).read()
        if (
            state.get("restore_kind") == FINAL_V4_LIVE_RESTORE_KIND
            and state.get("phase")
            not in {"completed", "rolled_back", "aborted_before_replacement"}
        ):
            candidates.append((paths, state))
    if not candidates:
        return RestoreRecoveryResult("normal_start")
    if len(candidates) != 1:
        raise RestoreManualRecoveryRequired(
            "Mehrere offene Cipher-Restore-Transaktionen wurden gefunden."
        )
    paths, state = candidates[0]
    journal = RestoreJournal(paths)
    phase = str(state.get("phase"))
    if phase == "manual_recovery_required":
        raise RestoreManualRecoveryRequired(
            "Der Cipher-Restore verlangt manuelle Wiederherstellung."
        )
    try:
        if phase in {
            "handoff_created",
            "worker_started",
            "maintenance",
            "preflight_verified",
        } and not state.get("completed_renames"):
            journal.transition("aborted_before_replacement", next_step="none")
            return RestoreRecoveryResult(
                "aborted_before_replacement",
                paths.transaction.name,
            )
        repository_loader = account_loader or _security_account_loader(root)
        if backup_service is None:
            handoff, loaded = _bootstrap_handoff_context(
                paths,
                state,
                account_loader=repository_loader,
                key_store=key_store,
            )
            verifier = _build_bootstrap_verifier(
                root,
                loaded=loaded,
                installation_id=str(handoff["installation_id"]),
            )
        else:
            handoff = _read_canonical_json(
                paths.consumed_handoff,
                RestoreHandoffError,
            )
            verifier = backup_service
        if phase == "installed_verified" and paths.resume_token.is_file():
            manifest = _read_manifest(
                _resolve_relative(root, str(handoff["staging_root_relative"]))
            )
            verifier.verify_live_runtime(root, manifest=manifest)
            payload = _read_canonical_json(paths.resume_token, RestoreHandoffError)
            handshake = dict(state.get("restart_handshake", {}))
            attempts = int(handshake.get("attempts", 0))
            if (
                attempts < 2
                and _parse_utc(str(payload.get("expires_at", "")))
                >= datetime.now(UTC)
            ):
                handshake.update(
                    {
                        "attempts": attempts + 1,
                        "status": "startup_recovery_resume",
                    }
                )
                journal.transition(
                    "installed_verified",
                    next_step="confirm_startup",
                    restart_handshake=handshake,
                )
                return RestoreRecoveryResult(
                    "resume_required",
                    paths.transaction.name,
                    str(payload.get("token", "")),
                )
        if backup_service is None:
            _bootstrap_restore_old_runtime(
                paths,
                journal,
                handoff=handoff,
                account_loader=repository_loader,
                key_store=key_store,
            )
        else:
            FinalV4EncryptedLiveRestoreService(backup_service)._rollback(
                paths,
                journal,
            )
        return RestoreRecoveryResult("rolled_back", paths.transaction.name)
    except RestoreManualRecoveryRequired:
        try:
            journal.transition(
                "manual_recovery_required",
                next_step="manual_recovery",
                error_class="RestoreManualRecoveryRequired",
            )
        except RestoreRuntimeError:
            pass
        raise
    except Exception as error:
        try:
            journal.transition(
                "manual_recovery_required",
                next_step="manual_recovery",
                error_class=type(error).__name__,
            )
        except RestoreRuntimeError:
            pass
        raise RestoreManualRecoveryRequired(
            "Der unterbrochene Cipher-Restore ist nicht automatisch beweisbar."
        ) from error


def build_final_v4_live_restore_worker_service(
    runtime_root: Path,
    *,
    restore_id: str | None = None,
    account_loader=None,
    key_store=None,
    sqlcipher_provider=None,
) -> FinalV4EncryptedLiveRestoreService:
    """Compose the worker from the existing ADR-101 Cipher product runtime."""

    try:
        root = Path(runtime_root).expanduser().resolve(strict=True)
        from src.core.database_engine import (
            SQLCIPHER_4_17_BINDING_VERSION,
            SQLCIPHER_4_17_ENGINE_VERSION,
            SQLCipherConnectionProvider,
        )
        from src.desktop_app.runtime import runtime_paths
        from src.security.cipher_product_runtime import open_cipher_product_runtime
        from src.security.final_v4_backup_runtime import (
            build_final_v4_encrypted_backup_service,
        )
        from src.security.domain import SECURITY_SCHEMA_VERSION
        from src.security.infrastructure.sqlite_repository import (
            SQLiteSecurityRepository,
        )
        from src.security.infrastructure.system import (
            PlatformFilePermissionManager,
        )

        security_database = root / "security" / "security.sqlite"
        if security_database.is_symlink() or not security_database.is_file():
            raise RestorePreflightError("Der bestehende Security Store fehlt.")
        security_uri = f"{security_database.resolve(strict=True).as_uri()}?mode=ro"
        with sqlite3.connect(security_uri, uri=True) as security_probe:
            security_probe.execute("PRAGMA query_only = ON")
            if int(security_probe.execute("PRAGMA user_version").fetchone()[0]) != SECURITY_SCHEMA_VERSION:
                raise RestorePreflightError(
                    "Der Security Store ist fuer Cipher-Restore nicht exakt aktuell."
                )
        repository = SQLiteSecurityRepository(
            security_database,
            PlatformFilePermissionManager(),
        )
        stable_account_loader = account_loader or repository.load_account
        provider = sqlcipher_provider or SQLCipherConnectionProvider(
            expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
            expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        )
        product_paths = runtime_paths(root)
        loaded = _load_existing_key_runtime(
            root,
            account_loader=stable_account_loader,
            key_store=key_store,
        )
        account = stable_account_loader()
        handoff_service = FinalV4EncryptedRestoreHandoffService(
            runtime_root=root,
            loaded_keys=loaded,
            installation_id=account.installation_id,
        )

        def open_after_parent_eof() -> FinalV4EncryptedBackupService:
            product_runtime = open_cipher_product_runtime(
                paths=product_paths,
                account_loader=stable_account_loader,
                authentication_confirmed=True,
                first_run_allowed=False,
                key_store=key_store,
                sqlcipher_provider=provider,
                active_restore_id=restore_id,
            )
            service = build_final_v4_encrypted_backup_service(
                opened_runtime=product_runtime.runtime,
                account_loader=stable_account_loader,
                environ=os.environ,
                key_store=key_store,
                sqlcipher_provider=provider,
                product_root=root,
            )
            if service.paths.final_v4.key_runtime.root != root:
                raise RestorePreflightError("Der Cipher-Worker-Root ist ungueltig.")
            return service

        return FinalV4EncryptedLiveRestoreService(
            None,
            handoff_service=handoff_service,
            backup_service_factory=open_after_parent_eof,
        )
    except RestoreRuntimeError:
        raise
    except Exception:
        raise RestorePreflightError(
            "Der Cipher-Restore-Worker konnte nicht sicher komponiert werden."
        ) from None


def _security_account_loader(root: Path):
    from src.security.infrastructure.sqlite_repository import SQLiteSecurityRepository

    database = root / "security" / "security.sqlite"
    repository = SQLiteSecurityRepository(
        database,
        PlatformFilePermissionManager(),
    )
    return repository.load_account


def classify_terminal_final_v4_restore_artifacts(runtime_root: Path) -> bool:
    """Return true only for structurally terminal Cipher journal artifacts."""

    root = Path(runtime_root)
    transaction_root = root / "restore-transactions"
    handoff_root = root / "restore-handoffs"
    if not transaction_root.exists() and not handoff_root.exists():
        return True
    if (
        transaction_root.is_symlink()
        or handoff_root.is_symlink()
        or not transaction_root.is_dir()
        or not handoff_root.is_dir()
    ):
        return False
    transaction_ids: set[str] = set()
    try:
        for child in transaction_root.iterdir():
            if child.is_symlink() or not child.is_dir():
                return False
            paths = restore_transaction_paths(root, child.name)
            state = RestoreJournal(paths).read()
            if (
                state.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
                or state.get("phase")
                not in {"completed", "rolled_back", "aborted_before_replacement"}
            ):
                return False
            transaction_ids.add(child.name)
        if not transaction_ids:
            return False
        handoff_ids: set[str] = set()
        for child in handoff_root.iterdir():
            if child.is_symlink() or not child.is_file() or child.suffix != ".json":
                return False
            name = child.name
            restore_id = (
                name.removesuffix(".consumed.json")
                if name.endswith(".consumed.json")
                else name.removesuffix(".json")
            )
            if restore_id not in transaction_ids:
                return False
            handoff_ids.add(restore_id)
        return handoff_ids == transaction_ids
    except (OSError, RestoreRuntimeError):
        return False


def classify_active_final_v4_restore_artifacts(
    runtime_root: Path,
    *,
    restore_id: str,
) -> bool:
    """Allow exactly one structurally active Cipher transaction for its worker."""

    try:
        root = Path(runtime_root).expanduser().resolve(strict=True)
        paths = restore_transaction_paths(root, restore_id)
        transaction_root = root / "restore-transactions"
        handoff_root = root / "restore-handoffs"
        if (
            transaction_root.is_symlink()
            or handoff_root.is_symlink()
            or not transaction_root.is_dir()
            or not handoff_root.is_dir()
        ):
            return False
        transaction_ids: set[str] = set()
        for child in transaction_root.iterdir():
            if child.is_symlink() or not child.is_dir():
                return False
            candidate = restore_transaction_paths(root, child.name)
            state = RestoreJournal(candidate).read()
            if child.name == restore_id:
                if (
                    state.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
                    or state.get("phase")
                    in {
                        "completed",
                        "rolled_back",
                        "aborted_before_replacement",
                        "manual_recovery_required",
                    }
                ):
                    return False
            elif (
                state.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
                or state.get("phase")
                not in {"completed", "rolled_back", "aborted_before_replacement"}
            ):
                return False
            transaction_ids.add(child.name)
        handoff_ids: set[str] = set()
        for child in handoff_root.iterdir():
            if child.is_symlink() or not child.is_file() or child.suffix != ".json":
                return False
            name = child.name
            handoff_ids.add(
                name.removesuffix(".consumed.json")
                if name.endswith(".consumed.json")
                else name.removesuffix(".json")
            )
        return (
            handoff_ids == transaction_ids
            and restore_id in transaction_ids
            and paths.consumed_handoff.is_file()
        )
    except (OSError, RestoreRuntimeError):
        return False


def validate_terminal_final_v4_restore_evidence(
    runtime_root: Path,
    *,
    loaded_keys: LoadedDatabaseKeyRuntime,
    installation_id: str,
) -> None:
    """Authenticate terminal Cipher handoffs after the product keys are loaded."""

    root = Path(runtime_root).expanduser().resolve(strict=True)
    if not classify_terminal_final_v4_restore_artifacts(root):
        raise RestoreManualRecoveryRequired("Cipher-Restore-Evidenz ist nicht terminal.")
    transaction_root = root / "restore-transactions"
    if not transaction_root.exists():
        return
    service = FinalV4EncryptedRestoreHandoffService(
        runtime_root=root,
        loaded_keys=loaded_keys,
        installation_id=installation_id,
    )
    for child in transaction_root.iterdir():
        paths = restore_transaction_paths(root, child.name)
        handoff_path = (
            paths.consumed_handoff
            if paths.consumed_handoff.is_file()
            else paths.handoff
        )
        payload = _read_canonical_json(handoff_path, RestoreHandoffError)
        unsigned = dict(payload)
        observed = str(unsigned.pop("authentication_hmac_sha256", ""))
        if (
            payload.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
            or payload.get("runtime_root") != str(root)
            or payload.get("restore_id") != child.name
            or payload.get("installation_id") != installation_id
            or payload.get("database_context_id") != loaded_keys.database_context_id
            or not hmac.compare_digest(observed, service._authenticate(unsigned))
        ):
            raise RestoreManualRecoveryRequired(
                "Cipher-Restore-Evidenz ist nicht authentisiert."
            )


def validate_active_final_v4_restore_evidence(
    runtime_root: Path,
    *,
    restore_id: str,
    loaded_keys: LoadedDatabaseKeyRuntime,
    installation_id: str,
) -> None:
    """Re-authenticate the one active worker handoff with its existing DMK."""

    root = Path(runtime_root).expanduser().resolve(strict=True)
    if not classify_active_final_v4_restore_artifacts(
        root,
        restore_id=restore_id,
    ):
        raise RestoreManualRecoveryRequired("Aktive Cipher-Restore-Evidenz ist ungueltig.")
    service = FinalV4EncryptedRestoreHandoffService(
        runtime_root=root,
        loaded_keys=loaded_keys,
        installation_id=installation_id,
    )
    for child in (root / "restore-transactions").iterdir():
        paths = restore_transaction_paths(root, child.name)
        handoff_path = (
            paths.consumed_handoff
            if paths.consumed_handoff.is_file()
            else paths.handoff
        )
        payload = _read_canonical_json(handoff_path, RestoreHandoffError)
        unsigned = dict(payload)
        observed = str(unsigned.pop("authentication_hmac_sha256", ""))
        if (
            payload.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
            or payload.get("runtime_root") != str(root)
            or payload.get("restore_id") != child.name
            or payload.get("installation_id") != installation_id
            or payload.get("database_context_id") != loaded_keys.database_context_id
            or not hmac.compare_digest(observed, service._authenticate(unsigned))
        ):
            raise RestoreManualRecoveryRequired(
                "Aktive Cipher-Restore-Evidenz ist nicht authentisiert."
            )


def _bootstrap_components(
    paths: RestoreTransactionPaths,
    handoff: Mapping[str, object],
) -> tuple[_CipherComponent, ...]:
    from src.security.final_v3_document_runtime import FinalV3DocumentRuntimePaths
    from src.security.final_v4_sqlcipher_runtime import FinalV4SQLCipherRuntimePaths

    key_paths = DatabaseKeyRuntimePaths.for_root(paths.runtime_root)
    final_paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
    document_paths = FinalV3DocumentRuntimePaths.for_final_v4(final_paths)
    staging_root = _resolve_relative(
        paths.runtime_root,
        str(handoff["staging_root_relative"]),
    )
    return (
        _CipherComponent(
            "key_runtime_metadata",
            key_paths.metadata_root,
            staging_root / key_paths.metadata_root.name,
            paths.rollback / key_paths.metadata_root.name,
            paths.failed_new / key_paths.metadata_root.name,
        ),
        _CipherComponent(
            "final_v4_main_database",
            final_paths.database,
            staging_root / final_paths.runtime_root.name / final_paths.database.name,
            paths.rollback / final_paths.database.name,
            paths.failed_new / final_paths.database.name,
        ),
        _CipherComponent(
            "document_companion_database",
            document_paths.database,
            staging_root / final_paths.runtime_root.name / document_paths.database.name,
            paths.rollback / document_paths.database.name,
            paths.failed_new / document_paths.database.name,
        ),
        _CipherComponent(
            "managed_document_storage",
            document_paths.container_root,
            staging_root / final_paths.runtime_root.name / document_paths.container_root.name,
            paths.rollback / document_paths.container_root.name,
            paths.failed_new / document_paths.container_root.name,
        ),
    )


def _bootstrap_handoff_context(
    paths: RestoreTransactionPaths,
    state: Mapping[str, object],
    *,
    account_loader,
    key_store=None,
) -> tuple[dict[str, object], LoadedDatabaseKeyRuntime]:
    handoff_path = (
        paths.consumed_handoff
        if paths.consumed_handoff.is_file()
        else paths.handoff
    )
    handoff = _read_canonical_json(handoff_path, RestoreHandoffError)
    if (
        handoff.get("restore_kind") != FINAL_V4_LIVE_RESTORE_KIND
        or handoff.get("runtime_root") != str(paths.runtime_root)
        or handoff.get("restore_id") != paths.transaction.name
    ):
        raise RestoreManualRecoveryRequired("Der Cipher-Handoff ist nicht gebunden.")
    components = state.get("components")
    if not isinstance(components, dict):
        raise RestoreManualRecoveryRequired("Die Cipher-Komponentenevidenz fehlt.")
    metadata_component = _bootstrap_components(paths, handoff)[0]
    record = components.get(metadata_component.role)
    if not isinstance(record, dict):
        raise RestoreManualRecoveryRequired("Die Cipher-Keyevidenz fehlt.")
    candidates: list[Path] = []
    for evidence_name, expected_path in (
        ("before", metadata_component.live),
        ("before", metadata_component.rollback),
        ("prepared", metadata_component.live),
        ("prepared", metadata_component.prepared),
        ("prepared", metadata_component.failed_new),
    ):
        evidence = record.get(evidence_name)
        if (
            isinstance(evidence, dict)
            and expected_path not in candidates
            and _evidence_matches(expected_path, evidence)
        ):
            candidates.append(expected_path)
    authenticated: list[LoadedDatabaseKeyRuntime] = []
    account = account_loader()
    for metadata_root in candidates:
        try:
            loaded = _load_existing_key_runtime(
                paths.runtime_root,
                account_loader=lambda: account,
                key_store=key_store,
                metadata_root=metadata_root,
            )
            service = FinalV4EncryptedRestoreHandoffService(
                runtime_root=paths.runtime_root,
                loaded_keys=loaded,
                installation_id=account.installation_id,
            )
            observed = str(handoff.get("authentication_hmac_sha256", ""))
            unsigned = dict(handoff)
            unsigned.pop("authentication_hmac_sha256", None)
            if (
                handoff.get("installation_id") == account.installation_id
                and handoff.get("database_context_id")
                == loaded.database_context_id
                and hmac.compare_digest(observed, service._authenticate(unsigned))
            ):
                authenticated.append(loaded)
        except RestoreRuntimeError:
            continue
    identities = {
        (
            item.dmk_key_id,
            item.dmk_generation,
            item.dmk_fingerprint_sha256,
            item.database_key_id,
            item.database_key_generation,
            item.database_key_fingerprint_sha256,
            item.database_context_id,
        )
        for item in authenticated
    }
    if len(identities) != 1 or not authenticated:
        raise RestoreManualRecoveryRequired(
            "Der DMK-authentisierte Cipher-Handoff ist nicht eindeutig beweisbar."
        )
    return handoff, authenticated[0]


def _build_bootstrap_verifier(
    root: Path,
    *,
    loaded: LoadedDatabaseKeyRuntime,
    installation_id: str,
) -> FinalV4EncryptedBackupService:
    from src.security.final_v4_backup_runtime import build_final_v4_restore_verifier

    return build_final_v4_restore_verifier(
        runtime_root=root,
        loaded_keys=loaded,
        installation_id=installation_id,
    )


def _bootstrap_restore_old_runtime(
    paths: RestoreTransactionPaths,
    journal: RestoreJournal,
    *,
    handoff: Mapping[str, object],
    account_loader,
    key_store=None,
) -> None:
    state = journal.read()
    components_state = state.get("components")
    if not isinstance(components_state, dict):
        raise RestoreManualRecoveryRequired("Cipher-Rollbackkomponenten fehlen.")
    journal.transition("rollback_started", next_step="restore_old_cipher_runtime")
    for component in reversed(_bootstrap_components(paths, handoff)):
        record = components_state.get(component.role)
        before = None if not isinstance(record, dict) else record.get("before")
        prepared = None if not isinstance(record, dict) else record.get("prepared")
        if not isinstance(before, dict) or not isinstance(prepared, dict):
            raise RestoreManualRecoveryRequired("Cipher-Rollbackevidenz fehlt.")
        live_is_old = _evidence_matches(component.live, before)
        rollback_is_old = _evidence_matches(component.rollback, before)
        if live_is_old:
            if not rollback_is_old:
                continue
            if (
                component.prepared.exists()
                or component.prepared.is_symlink()
                or not _evidence_matches(component.live, prepared)
            ):
                raise RestoreManualRecoveryRequired(
                    f"Der alte Cipher-Bestand ist doppelt und uneindeutig: {component.role}."
                )
        if not rollback_is_old:
            raise RestoreManualRecoveryRequired(
                f"Der alte Cipher-Rollbackbestand ist nicht beweisbar: {component.role}."
            )
        if component.live.exists() or component.live.is_symlink():
            if (
                not _evidence_matches(component.live, prepared)
                or component.failed_new.exists()
                or component.failed_new.is_symlink()
            ):
                raise RestoreManualRecoveryRequired(
                    "Der neue Cipher-Bestand ist nicht eindeutig separierbar."
                )
            _journaled_rename(
                journal,
                name=f"bootstrap_new_{component.role}_to_failed",
                source=component.live,
                target=component.failed_new,
            )
        _journaled_rename(
            journal,
            name=f"bootstrap_old_{component.role}_to_live",
            source=component.rollback,
            target=component.live,
        )
        if not _evidence_matches(component.live, before):
            raise RestoreManualRecoveryRequired(
                "Der alte Cipher-Bestand ist nach Recovery unvollstaendig."
            )
    handoff_verified, loaded = _bootstrap_handoff_context(
        paths,
        journal.read(),
        account_loader=account_loader,
        key_store=key_store,
    )
    verifier = _build_bootstrap_verifier(
        paths.runtime_root,
        loaded=loaded,
        installation_id=str(handoff_verified["installation_id"]),
    )
    safety_path = _resolve_relative(
        paths.runtime_root,
        str(handoff_verified["safety_backup_relative"]),
    )
    safety = verifier.verify(safety_path)
    verifier.verify_live_runtime(
        paths.runtime_root,
        manifest=safety.manifest,
        enforce_artifact_hashes=False,
    )
    expected_excluded = journal.read().get("excluded_evidence")
    if (
        not isinstance(expected_excluded, dict)
        or _excluded_evidence(paths.runtime_root) != expected_excluded
    ):
        raise RestoreManualRecoveryRequired("Ausgeschlossene Daten widersprechen Recovery.")
    journal.transition("rolled_back", next_step="none", error_class=None)


def run_confirm(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--final-v4-restore-confirm", action="store_true")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--restore-id", required=True)
    parser.add_argument("--restore-token", required=True)
    parser.add_argument("--restore-lock-fd", type=int, required=True)
    try:
        args = parser.parse_args(argv)
        lock = RuntimeInstanceLock(
            args.runtime_root,
            inherited_fd=args.restore_lock_fd,
        ).acquire()
        confirm_final_v4_restore_startup(
            runtime_root=args.runtime_root,
            restore_id=args.restore_id,
            token=args.restore_token,
        )
        lock.transfer()
        return 0
    except (SystemExit, RestoreRuntimeError, FinalV4EncryptedBackupError):
        return 1


def main() -> int:
    return run_confirm()


def _journaled_rename(
    journal: RestoreJournal,
    *,
    name: str,
    source: Path,
    target: Path,
) -> None:
    state = journal.read()
    if target.exists() or target.is_symlink():
        raise RestoreReplacementError("Ein Cipher-Rename-Ziel existiert bereits.")
    if not source.exists() or source.is_symlink():
        raise RestoreReplacementError("Eine Cipher-Rename-Quelle ist ungueltig.")
    state["rename_intent"] = {
        "name": name,
        "source": source.name,
        "target": f"{target.parent.name}/{target.name}",
    }
    state = journal.write(state, event=f"rename_intent:{name}")
    _fsync_path(source)
    _fsync_directory(source.parent)
    _fsync_directory(target.parent)
    os.rename(source, target)
    _fsync_directory(source.parent)
    _fsync_directory(target.parent)
    state["rename_intent"] = None
    completed = list(state.get("completed_renames", []))
    completed.append(name)
    state["completed_renames"] = completed
    journal.write(state, event=f"rename_completed:{name}")


def _read_manifest(staging_root: Path) -> FinalV4EncryptedBackupManifestV1:
    try:
        return FinalV4EncryptedBackupManifestV1.from_bytes(
            (staging_root / FINAL_V4_BACKUP_MANIFEST_FILENAME).read_bytes()
        )
    except (OSError, FinalV4EncryptedBackupError):
        raise RestoreReplacementError("Das Cipher-Restore-Manifest ist nicht lesbar.") from None


def _load_existing_key_runtime(
    runtime_root: Path,
    *,
    account_loader,
    key_store=None,
    metadata_root: Path | None = None,
) -> LoadedDatabaseKeyRuntime:
    """Load an already-active DMK/envelope set without creating or repairing it."""

    try:
        root = Path(runtime_root).expanduser().resolve(strict=True)
        if metadata_root is None:
            paths = DatabaseKeyRuntimePaths.for_root(root)
        else:
            metadata = Path(metadata_root).expanduser().resolve(strict=True)
            canonical = DatabaseKeyRuntimePaths.for_root(root)
            paths = DatabaseKeyRuntimePaths(
                root=root,
                metadata_root=metadata,
                keyset_metadata=metadata / canonical.keyset_metadata.name,
                envelope_registry=metadata / canonical.envelope_registry.name,
            )
        permissions = PlatformFilePermissionManager()
        active = _read_active_keyset_immutable(paths.keyset_metadata)
        if (
            active is None
            or active.status is not DataKeysetStatus.ACTIVE
            or active.runtime_phase is not DataKeysetRuntimePhase.ACTIVE
            or active.database_context_id is None
        ):
            raise RestorePreflightError("Die Cipher-Keymetadaten sind nicht aktiv.")
        account = account_loader()
        store = key_store or build_platform_data_master_key_store()
        observed = store.read(
            installation_id=account.installation_id,
            key_id=active.key_id,
        )
        if (
            observed.status is not DataMasterKeyStoreStatus.SUCCESS
            or observed.key_material is None
        ):
            raise RestorePreflightError("Der vorhandene DMK ist nicht lesbar.")
        dmk = LoadedDataMasterKey(
            key_id=active.key_id,
            generation=active.generation,
            key_material=observed.key_material,
        )
        dmk_fingerprint = data_master_key_fingerprint(dmk.key_material)
        if dmk_fingerprint != active.fingerprint_sha256:
            raise RestorePreflightError("Der vorhandene DMK widerspricht den Metadaten.")
        envelope_repository = FileDatabaseKeyEnvelopeRepository(
            paths.envelope_registry,
            permissions,
        )
        database_key = DatabaseKeyEnvelopeService(
            repository=envelope_repository,
            random_source=SystemRandomSource(),
            clock=SystemClock(),
        ).load_active(dmk)
        return LoadedDatabaseKeyRuntime(
            database_context_id=active.database_context_id,
            dmk_key_id=active.key_id,
            dmk_generation=active.generation,
            dmk_fingerprint_sha256=dmk_fingerprint,
            database_key_id=database_key.key_id,
            database_key_generation=database_key.generation,
            database_key_fingerprint_sha256=hashlib.sha256(
                database_key.key_material
            ).hexdigest(),
            first_run=False,
            dmk=dmk,
            database_key=database_key,
        )
    except RestoreRuntimeError:
        raise
    except Exception:
        raise RestorePreflightError(
            "Die vorhandenen Cipher-Schluessel konnten nicht read-only geladen werden."
        ) from None


def _read_active_keyset_immutable(path: Path) -> DataKeyset | None:
    """Read the existing keyset through SQLite immutable mode without sidecars."""

    database = Path(path).expanduser().resolve(strict=True)
    uri = f"{database.as_uri()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True, isolation_level=None) as connection:
        connection.execute("PRAGMA query_only = ON")
        if (
            int(connection.execute("PRAGMA application_id").fetchone()[0])
            != 0x4A4B4D4B
            or int(connection.execute("PRAGMA user_version").fetchone()[0])
            != DATA_KEYSET_STORE_SCHEMA_VERSION
        ):
            raise RestorePreflightError("Die Cipher-Keymetadaten sind inkompatibel.")
        rows = connection.execute(
            "SELECT key_id, generation, status, fingerprint_sha256, "
            "runtime_phase, database_context_id FROM data_keysets"
        ).fetchall()
    if not rows:
        return None
    if len(rows) != 1:
        raise RestorePreflightError("Die Cipher-Keymetadaten sind nicht eindeutig.")
    row = rows[0]
    return DataKeyset(
        key_id=str(row[0]),
        generation=int(row[1]),
        status=DataKeysetStatus(str(row[2])),
        fingerprint_sha256=str(row[3]),
        runtime_phase=DataKeysetRuntimePhase(str(row[4])),
        database_context_id=None if row[5] is None else str(row[5]),
    )


def _excluded_evidence(root: Path) -> dict[str, object]:
    return {
        "app_preferences": _path_evidence(root / "app-preferences.json"),
        "security_store": _path_evidence(root / "security" / "security.sqlite"),
    }


def _resolve_relative(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not relative or ".." in candidate.parts:
        raise RestoreHandoffError("Ein Cipher-Handoff-Pfad ist ungueltig.")
    root = Path(root).resolve(strict=True)
    resolved = (root / candidate).resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise RestoreHandoffError("Ein Cipher-Handoff-Pfad verlaesst den Runtime-Root.")
    return resolved


def _is_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


if __name__ == "__main__":  # pragma: no cover - subprocess entry point
    raise SystemExit(main())
