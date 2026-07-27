"""Fail-closed runtime replacement, rollback, journal and startup recovery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Mapping, Protocol

from .backup import BackupVerifier
from .database_compatibility import (
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityStatus,
)
from .observation_uow import (
    ObservationPersistenceUnitOfWork,
    ObservationWriterLock,
)
from .restore import (
    RESTORE_STAGING_DIRECTORY,
    RESTORE_STATE_FILENAME,
    RestoreSafetyBackupService,
    RestoreStagingService,
    _validated_restore_id,
)
from .sqlite_store import SQLiteDatabase


RESTORE_HANDOFF_VERSION = 1
RESTORE_JOURNAL_VERSION = 1
RESTORE_RESUME_TOKEN_VERSION = 1
RESTORE_HANDOFF_DIRECTORY = "restore-handoffs"
RESTORE_TRANSACTION_DIRECTORY = "restore-transactions"
RESTORE_CURRENT_STATE_FILENAME = "current-state.json"
RESTORE_EVENTS_FILENAME = "events.jsonl"
RESTORE_LOCK_FILENAME = "instance.lock"
RESTORE_ROLLBACK_DIRECTORY = "rollback"
RESTORE_FAILED_NEW_DIRECTORY = "failed-new"
RESTORE_PREFLIGHT_ORIGINAL_DIRECTORY = "preflight-original"
RESTORE_RESUME_TOKEN_FILENAME = "resume-token.json"
RESTORE_CONSUMED_RESUME_TOKEN_FILENAME = "resume-token.consumed.json"
HANDOFF_MAX_AGE = timedelta(minutes=15)
RESUME_TOKEN_MAX_AGE = timedelta(minutes=5)
MAX_RESUME_ATTEMPTS = 2
_TERMINAL_PHASES = frozenset({"completed", "rolled_back", "aborted_before_replacement"})


class RestoreRuntimeError(RuntimeError):
    """Base class for controlled productive-restore failures."""


class RestoreLockError(RestoreRuntimeError):
    """Raised when the runtime lock is busy or contradictory."""


class RestoreHandoffError(RestoreRuntimeError):
    """Raised when a one-time handoff is invalid or already consumed."""


class RestoreJournalError(RestoreRuntimeError):
    """Raised when persisted transaction evidence is contradictory."""


class RestorePreflightError(RestoreRuntimeError):
    """Raised before the first live rename."""


class RestoreReplacementError(RestoreRuntimeError):
    """Raised after live replacement has begun."""


class RestoreRollbackError(RestoreRuntimeError):
    """Raised when the old state cannot be restored completely."""


class RestoreManualRecoveryRequired(RestoreRuntimeError):
    """Raised when no safe automatic continuation can be proven."""


class RuntimeRestorePathSet(Protocol):
    root: Path
    database: Path
    documents: Path
    backups: Path


@dataclass(frozen=True)
class RestoreTransactionPaths:
    runtime_root: Path
    staging_root: Path
    prepared_database: Path
    prepared_documents: Path
    staging_state: Path
    handoff: Path
    consumed_handoff: Path
    transaction: Path
    current_state: Path
    events: Path
    bound_archive: Path
    rollback: Path
    failed_new: Path
    preflight_original: Path
    resume_token: Path
    consumed_resume_token: Path
    live_database: Path
    live_wal: Path
    live_shm: Path
    live_documents: Path
    backups: Path


@dataclass(frozen=True)
class RestoreHandoffResult:
    restore_id: str
    nonce: str
    path: Path
    archive_sha256: str
    prepared_database_sha256: str


@dataclass(frozen=True)
class RestoreExecutionResult:
    restore_id: str
    status: str
    safety_backup_sha256: str


@dataclass(frozen=True)
class RestoreRecoveryResult:
    status: str
    restore_id: str | None = None
    resume_token: str | None = None


def _canonical_root(path: Path, *, create: bool = False) -> Path:
    path = Path(path).expanduser()
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.lstat()
    except OSError as error:
        raise RestoreRuntimeError("Die kanonische Runtime-Wurzel ist nicht lesbar.") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RestoreRuntimeError("Die Runtime-Wurzel ist kein regulaeres Verzeichnis.")
    return resolved


def restore_transaction_paths(runtime_root: Path, restore_id: str) -> RestoreTransactionPaths:
    root = _canonical_root(runtime_root)
    restore_id = _validated_restore_id(restore_id)
    staging = root / RESTORE_STAGING_DIRECTORY / restore_id
    transaction = root / RESTORE_TRANSACTION_DIRECTORY / restore_id
    handoff_dir = root / RESTORE_HANDOFF_DIRECTORY
    database = root / "kompetenzmanager.sqlite"
    return RestoreTransactionPaths(
        runtime_root=root,
        staging_root=staging,
        prepared_database=staging / "prepared" / "kompetenzmanager.sqlite",
        prepared_documents=staging / "prepared" / "documents",
        staging_state=staging / RESTORE_STATE_FILENAME,
        handoff=handoff_dir / f"{restore_id}.json",
        consumed_handoff=handoff_dir / f"{restore_id}.consumed.json",
        transaction=transaction,
        current_state=transaction / RESTORE_CURRENT_STATE_FILENAME,
        events=transaction / RESTORE_EVENTS_FILENAME,
        bound_archive=transaction / "source-backup.jkmbackup",
        rollback=transaction / RESTORE_ROLLBACK_DIRECTORY,
        failed_new=transaction / RESTORE_FAILED_NEW_DIRECTORY,
        preflight_original=transaction / RESTORE_PREFLIGHT_ORIGINAL_DIRECTORY,
        resume_token=transaction / RESTORE_RESUME_TOKEN_FILENAME,
        consumed_resume_token=transaction / RESTORE_CONSUMED_RESUME_TOKEN_FILENAME,
        live_database=database,
        live_wal=Path(f"{database}-wal"),
        live_shm=Path(f"{database}-shm"),
        live_documents=root / "documents",
        backups=root / "backups",
    )


class RuntimeInstanceLock:
    """Kernel-backed exclusive lock; the JSON file is evidence, not authority."""

    def __init__(self, runtime_root: Path, *, inherited_fd: int | None = None) -> None:
        self.runtime_root = _canonical_root(runtime_root, create=True)
        self.path = self.runtime_root / RESTORE_LOCK_FILENAME
        self._file = None
        self._inherited_fd = inherited_fd

    @property
    def fileno(self) -> int:
        if self._file is None:
            raise RestoreLockError("Der Runtime-Lock wird nicht gehalten.")
        return self._file.fileno()

    def acquire(self) -> "RuntimeInstanceLock":
        if self._file is not None:
            return self
        if self._inherited_fd is not None:
            try:
                self._file = os.fdopen(self._inherited_fd, "r+", closefd=True)
                self._file.seek(0)
                self._validate_locked_payload(self._file.read(), allow_live_owner=True)
                self._write_current_owner()
                return self
            except Exception as error:
                if self._file is not None:
                    self._file.close()
                self._file = None
                raise RestoreLockError("Der uebergebene Runtime-Lock ist ungueltig.") from error
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_file = self.path.open("a+", encoding="utf-8")
        try:
            _lock_file(lock_file)
            lock_file.seek(0)
            existing = lock_file.read()
            if existing:
                self._validate_locked_payload(existing, allow_live_owner=False)
            self._file = lock_file
            self._write_current_owner()
            return self
        except Exception:
            try:
                _unlock_file(lock_file)
            finally:
                lock_file.close()
                self._file = None
            raise

    def _validate_locked_payload(self, raw: str, *, allow_live_owner: bool) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise RestoreLockError("Die Runtime-Lockdatei ist widerspruechlich.") from error
        expected = {"acquired_at", "pid", "process_start_identity", "runtime_root_sha256", "version"}
        if (
            not isinstance(payload, dict)
            or set(payload) != expected
            or payload.get("version") != 1
            or payload.get("runtime_root_sha256") != _text_sha256(str(self.runtime_root))
            or not isinstance(payload.get("pid"), int)
            or int(payload.get("pid", 0)) <= 0
            or not isinstance(payload.get("process_start_identity"), str)
            or not payload.get("process_start_identity")
            or not isinstance(payload.get("acquired_at"), str)
            or _canonical_bytes(payload).decode("utf-8") != raw
        ):
            raise RestoreLockError("Die Runtime-Lockdatei ist widerspruechlich.")
        try:
            _parse_utc(str(payload["acquired_at"]))
        except RestoreHandoffError as error:
            raise RestoreLockError("Die Runtime-Lockdatei besitzt keine gueltige UTC-Zeit.") from error
        recorded_pid = int(payload["pid"])
        actual_identity = _process_start_identity(recorded_pid)
        if (
            not allow_live_owner
            and recorded_pid != os.getpid()
            and not actual_identity.startswith("unavailable:")
            and actual_identity == payload["process_start_identity"]
        ):
            raise RestoreLockError(
                "Ein lebender Prozess passt zur Lock-Identitaet, haelt aber keinen beweisbaren Lock."
            )

    def _write_current_owner(self) -> None:
        if self._file is None:
            raise RestoreLockError("Der Runtime-Lock wird nicht gehalten.")
        payload = {
            "acquired_at": _utc_now(),
            "pid": os.getpid(),
            "process_start_identity": _process_start_identity(os.getpid()),
            "runtime_root_sha256": _text_sha256(str(self.runtime_root)),
            "version": 1,
        }
        self._file.seek(0)
        self._file.truncate()
        self._file.write(_canonical_bytes(payload).decode("utf-8"))
        self._file.flush()
        os.fsync(self._file.fileno())
        os.chmod(self.path, 0o600)
        _fsync_directory(self.path.parent)

    def transfer(self) -> None:
        """Close this process descriptor without explicitly unlocking it."""
        if self._file is None:
            raise RestoreLockError("Der Runtime-Lock kann nicht uebergeben werden.")
        self._file.close()
        self._file = None

    def release(self) -> None:
        if self._file is None:
            return
        try:
            _unlock_file(self._file)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> "RuntimeInstanceLock":
        return self.acquire()

    def __exit__(self, *_args: object) -> None:
        self.release()


def _lock_file(file) -> None:
    try:
        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RestoreLockError("Eine App- oder Restore-Instanz haelt den Runtime-Lock.") from error
    except ImportError:  # pragma: no cover - Windows fallback
        import msvcrt

        try:
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RestoreLockError("Eine App- oder Restore-Instanz haelt den Runtime-Lock.") from error


def _unlock_file(file) -> None:
    try:
        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
    except ImportError:  # pragma: no cover - Windows fallback
        import msvcrt

        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)


def _process_start_identity(pid: int) -> str:
    try:
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        value = result.stdout.strip()
        if value:
            return value
    except (OSError, subprocess.SubprocessError):
        pass
    return f"unavailable:{pid}"


class RestoreJournal:
    """Atomic current state plus append-only, fsynced JSONL events."""

    def __init__(self, paths: RestoreTransactionPaths) -> None:
        self.paths = paths

    def create(self, initial: Mapping[str, object]) -> dict[str, object]:
        self.paths.transaction.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.paths.transaction.mkdir(mode=0o700, exist_ok=False)
        for directory in (self.paths.rollback, self.paths.failed_new, self.paths.preflight_original):
            directory.mkdir(mode=0o700)
        state = dict(initial)
        self.write(state, event="journal_created")
        return state

    def read(self) -> dict[str, object]:
        state = _read_canonical_json(self.paths.current_state, RestoreJournalError)
        required = {
            "archive_sha256", "completed_renames", "components", "created_at",
            "error_class", "journal_version", "next_step", "phase",
            "prepared_database_sha256", "rename_intent", "restart_handshake",
            "restore_id", "safety_backup_sha256", "updated_at",
        }
        if (
            not required.issubset(state)
            or state.get("journal_version") != RESTORE_JOURNAL_VERSION
            or state.get("restore_id") != self.paths.transaction.name
        ):
            raise RestoreJournalError("Der aktuelle Restore-State ist unvollstaendig.")
        self._validate_events(state)
        return state

    def _validate_events(self, state: Mapping[str, object]) -> None:
        try:
            raw = _read_regular_bytes(self.paths.events)
            lines = raw.splitlines()
            if not lines or raw[-1:] != b"\n":
                raise RestoreJournalError("Das Restore-Ereignisjournal ist unvollstaendig.")
            events = [json.loads(line) for line in lines]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RestoreJournalError("Das Restore-Ereignisjournal ist nicht lesbar.") from error
        for line, event in zip(lines, events, strict=True):
            if (
                not isinstance(event, dict)
                or _canonical_bytes(event) != line
                or event.get("journal_version") != RESTORE_JOURNAL_VERSION
                or event.get("restore_id") != self.paths.transaction.name
            ):
                raise RestoreJournalError("Das Restore-Ereignisjournal ist widerspruechlich.")

    def write(self, state: Mapping[str, object], *, event: str) -> dict[str, object]:
        payload = dict(state)
        payload["updated_at"] = _utc_now()
        _atomic_write_json(self.paths.current_state, payload)
        event_payload = {
            "at": payload["updated_at"],
            "error_class": payload.get("error_class"),
            "event": event,
            "journal_version": RESTORE_JOURNAL_VERSION,
            "next_step": payload.get("next_step"),
            "phase": payload.get("phase"),
            "rename_intent": payload.get("rename_intent"),
            "restore_id": payload.get("restore_id"),
        }
        _append_jsonl(self.paths.events, event_payload)
        return payload

    def transition(self, phase: str, *, next_step: str, **updates: object) -> dict[str, object]:
        state = self.read()
        if _restart_is_confirmed(state) and phase != "completed":
            raise RestoreJournalError(
                "Ein bestaetigter Restore-Zustand ist endgueltig."
            )
        state.update(updates)
        state["phase"] = phase
        state["next_step"] = next_step
        return self.write(state, event=phase)

    def rename(self, *, name: str, source: Path, target: Path) -> None:
        state = self.read()
        if target.exists() or target.is_symlink():
            raise RestoreReplacementError("Ein technisches Rename-Ziel existiert bereits.")
        intent = {"name": name, "source": _path_role(source, self.paths), "target": _path_role(target, self.paths)}
        state["rename_intent"] = intent
        state = self.write(state, event=f"rename_intent:{name}")
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
        self.write(state, event=f"rename_completed:{name}")


class RestoreHandoffService:
    def __init__(
        self,
        *,
        staging_service: RestoreStagingService | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.staging_service = staging_service or RestoreStagingService()
        self.now = now or (lambda: datetime.now(UTC))

    def create(
        self,
        *,
        archive_path: Path,
        runtime_paths: RuntimeRestorePathSet,
        restore_id: str,
        app_version: str,
        build_commit: str,
        source_tree_state: str | None = None,
    ) -> RestoreHandoffResult:
        root = _canonical_root(runtime_paths.root)
        paths = restore_transaction_paths(root, restore_id)
        _assert_runtime_projection(runtime_paths, paths)
        self.staging_service.verify_prepared(
            runtime_root=root,
            live_documents=paths.live_documents,
            restore_id=restore_id,
        )
        archive_path = Path(archive_path).expanduser().resolve(strict=True)
        archive_size, archive_hash = _file_evidence_values(archive_path)
        staging_state_bytes = _read_regular_bytes(paths.staging_state)
        staging_state = json.loads(staging_state_bytes)
        if (
            staging_state.get("phase") != "completed"
            or staging_state.get("archive_sha256") != archive_hash
            or staging_state.get("archive_size_bytes") != archive_size
        ):
            raise RestoreHandoffError("Archiv und abgeschlossenes Staging widersprechen sich.")
        prepared_size, prepared_hash = _file_evidence_values(paths.prepared_database)
        if paths.handoff.exists() or paths.consumed_handoff.exists() or paths.transaction.exists():
            raise RestoreHandoffError("Die Restore-Uebergabe oder Transaktion existiert bereits.")
        _validate_build_metadata(app_version, build_commit, source_tree_state)
        nonce = secrets.token_urlsafe(32)
        created_at = _utc_timestamp(self.now())
        payload = {
            "app_version": app_version,
            "archive_sha256": archive_hash,
            "archive_size_bytes": archive_size,
            "build_commit": build_commit,
            "created_at": created_at,
            "handoff_version": RESTORE_HANDOFF_VERSION,
            "nonce": nonce,
            "prepared_database_sha256": prepared_hash,
            "prepared_database_size_bytes": prepared_size,
            "restore_id": restore_id,
            "runtime_root": str(root),
            "source_tree_state": source_tree_state,
            "staging_state_sha256": hashlib.sha256(staging_state_bytes).hexdigest(),
        }
        RestoreJournal(paths).create(
            {
                "archive_sha256": archive_hash,
                "completed_renames": [],
                "components": {},
                "created_at": created_at,
                "error_class": None,
                "journal_version": RESTORE_JOURNAL_VERSION,
                "next_step": "consume_handoff",
                "phase": "handoff_created",
                "prepared_database_sha256": prepared_hash,
                "rename_intent": None,
                "restart_handshake": {"attempts": 0, "status": "not_started"},
                "restore_id": restore_id,
                "safety_backup_sha256": None,
            }
        )
        _copy_bound_archive(
            archive_path,
            paths.bound_archive,
            expected_size=archive_size,
            expected_hash=archive_hash,
        )
        paths.handoff.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _atomic_write_json(paths.handoff, payload, exclusive=True)
        return RestoreHandoffResult(restore_id, nonce, paths.handoff, archive_hash, prepared_hash)

    def consume(self, handoff_path: Path, *, expected_nonce: str) -> tuple[RestoreTransactionPaths, dict[str, object]]:
        try:
            handoff_path = Path(handoff_path).expanduser().resolve(strict=True)
        except OSError as error:
            raise RestoreHandoffError("Die Handoff-Datei fehlt oder ist nicht lesbar.") from error
        payload = _read_canonical_json(handoff_path, RestoreHandoffError)
        required = {
            "app_version", "archive_sha256", "archive_size_bytes", "build_commit",
            "created_at", "handoff_version", "nonce", "prepared_database_sha256",
            "prepared_database_size_bytes", "restore_id", "runtime_root", "source_tree_state",
            "staging_state_sha256",
        }
        if set(payload) != required or payload.get("handoff_version") != RESTORE_HANDOFF_VERSION:
            raise RestoreHandoffError("Die Handoff-Struktur ist ungueltig.")
        if not secrets.compare_digest(str(payload.get("nonce", "")), expected_nonce):
            raise RestoreHandoffError("Die Handoff-Nonce ist ungueltig.")
        created_at = _parse_utc(str(payload.get("created_at", "")))
        now = datetime.now(UTC)
        if created_at > now + timedelta(minutes=1) or now - created_at > HANDOFF_MAX_AGE:
            raise RestoreHandoffError("Die Handoff-Datei ist abgelaufen.")
        root = _canonical_root(Path(str(payload.get("runtime_root", ""))))
        paths = restore_transaction_paths(root, str(payload.get("restore_id", "")))
        if handoff_path != paths.handoff or paths.consumed_handoff.exists():
            raise RestoreHandoffError("Die Handoff-Datei ist nicht eindeutig oder bereits konsumiert.")
        _validate_hash_fields(payload)
        _validate_build_metadata(
            str(payload.get("app_version", "")),
            str(payload.get("build_commit", "")),
            payload.get("source_tree_state"),
        )
        os.rename(paths.handoff, paths.consumed_handoff)
        os.chmod(paths.consumed_handoff, 0o600)
        _fsync_directory(paths.consumed_handoff.parent)
        return paths, payload


class ProductiveRestoreService:
    """Apply one prepared restore and roll back unless startup confirms it."""

    def __init__(
        self,
        *,
        staging_service: RestoreStagingService | None = None,
        safety_service: RestoreSafetyBackupService | None = None,
        handoff_service: RestoreHandoffService | None = None,
        compatibility_inspector: DatabaseCompatibilityInspector | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.staging_service = staging_service or RestoreStagingService()
        self.safety_service = safety_service or RestoreSafetyBackupService()
        self.handoff_service = handoff_service or RestoreHandoffService(staging_service=self.staging_service)
        self.compatibility_inspector = compatibility_inspector or DatabaseCompatibilityInspector()
        self.now = now or (lambda: datetime.now(UTC))

    def execute(
        self,
        *,
        handoff_path: Path,
        nonce: str,
        lock: RuntimeInstanceLock,
        restart: Callable[[RestoreTransactionPaths, str, RuntimeInstanceLock], bool] | None = None,
        worker_started: Callable[[RestoreTransactionPaths], None] | None = None,
        handshake_timeout_seconds: float = 30.0,
    ) -> RestoreExecutionResult:
        paths, handoff = self.handoff_service.consume(handoff_path, expected_nonce=nonce)
        if lock.runtime_root != paths.runtime_root or lock._file is None:
            raise RestoreLockError("Der Worker haelt nicht den passenden Runtime-Lock.")
        observation_uow = ObservationPersistenceUnitOfWork(
            SQLiteDatabase(paths.live_database)
        )
        with ObservationWriterLock(observation_uow.staging_root):
            observation_uow.recover_pending_while_writer_locked()
            return self._execute_locked(
                paths=paths,
                handoff=handoff,
                lock=lock,
                restart=restart,
                worker_started=worker_started,
                handshake_timeout_seconds=handshake_timeout_seconds,
            )

    def _execute_locked(
        self,
        *,
        paths: RestoreTransactionPaths,
        handoff: Mapping[str, object],
        lock: RuntimeInstanceLock,
        restart: Callable[[RestoreTransactionPaths, str, RuntimeInstanceLock], bool] | None,
        worker_started: Callable[[RestoreTransactionPaths], None] | None,
        handshake_timeout_seconds: float,
    ) -> RestoreExecutionResult:
        journal = RestoreJournal(paths)
        restart_process: subprocess.Popen[bytes] | None = None
        safety_hash: str | None = None
        journal.transition(
            "worker_started",
            next_step="await_main_app_exit",
        )
        try:
            if worker_started is not None:
                worker_started(paths)
            journal.transition("maintenance", next_step="verify_preflight")
            safety_hash = self._preflight(paths, handoff, journal)
            journal.transition("preflight_verified", next_step="move_live_database")
            journal.transition("replacement_started", next_step="move_live_database")
            self._replace(paths, journal)
            new_documents = _tree_evidence(paths.live_documents)
            self._verify_new_live(
                paths,
                handoff,
                new_documents,
                journal.read().get("prepared_documents"),
            )
            journal.transition(
                "installed_verified",
                next_step="restart_with_resume_token",
                installed_documents=new_documents,
            )
            token = self._create_resume_token(paths)
            if restart is None:
                restart_process = _restart_application(paths, token, lock)
                if restart_process is None:
                    raise RestoreReplacementError("Der kontrollierte App-Neustart ist fehlgeschlagen.")
            elif not restart(paths, token, lock):
                raise RestoreReplacementError("Der kontrollierte App-Neustart ist fehlgeschlagen.")
            deadline = time.monotonic() + handshake_timeout_seconds
            while True:
                state = journal.read()
                if _restart_is_confirmed(state):
                    return RestoreExecutionResult(paths.transaction.name, "completed", safety_hash)
                if restart_process is not None:
                    exit_code = restart_process.poll()
                    if exit_code is not None:
                        state = journal.read()
                        if _restart_is_confirmed(state):
                            return RestoreExecutionResult(
                                paths.transaction.name,
                                "completed",
                                safety_hash,
                            )
                        handshake = dict(state.get("restart_handshake", {}))
                        handshake.update(
                            {
                                "exit_code": exit_code,
                                "status": "process_exited_early",
                            }
                        )
                        journal.transition(
                            str(state.get("phase")),
                            next_step="rollback",
                            restart_handshake=handshake,
                        )
                        raise RestoreReplacementError(
                            "Der App-Neustartprozess wurde vor dem Startup-Handshake beendet."
                        )
                if time.monotonic() >= deadline:
                    state = journal.read()
                    if _restart_is_confirmed(state):
                        return RestoreExecutionResult(
                            paths.transaction.name,
                            "completed",
                            safety_hash,
                        )
                    if restart_process is not None:
                        exit_code = _terminate_and_reap_restart_process(
                            restart_process
                        )
                        state = journal.read()
                        if _restart_is_confirmed(state):
                            return RestoreExecutionResult(
                                paths.transaction.name,
                                "completed",
                                safety_hash,
                            )
                        handshake = dict(state.get("restart_handshake", {}))
                        handshake.update(
                            {
                                "exit_code": exit_code,
                                "status": "process_exited_early",
                            }
                        )
                        journal.transition(
                            str(state.get("phase")),
                            next_step="rollback",
                            restart_handshake=handshake,
                        )
                    raise RestoreReplacementError(
                        "Der Startup-Handshake wurde nicht rechtzeitig bestaetigt."
                    )
                time.sleep(0.05)
        except Exception as error:
            try:
                terminal_state = journal.read()
            except RestoreRuntimeError:
                terminal_state = None
            if terminal_state is not None and _restart_is_confirmed(terminal_state):
                if safety_hash is None:
                    raise RestoreManualRecoveryRequired(
                        "Der bestaetigte Restore besitzt keinen vollstaendigen Sicherheitsnachweis."
                    ) from error
                return RestoreExecutionResult(
                    paths.transaction.name,
                    "completed",
                    safety_hash,
                )
            if restart_process is not None:
                exit_code = restart_process.poll()
                if exit_code is None:
                    try:
                        terminal_state = journal.read()
                    except RestoreRuntimeError:
                        terminal_state = None
                    if (
                        terminal_state is not None
                        and _restart_is_confirmed(terminal_state)
                    ):
                        if safety_hash is None:
                            raise RestoreManualRecoveryRequired(
                                "Der bestaetigte Restore besitzt keinen vollstaendigen Sicherheitsnachweis."
                            ) from error
                        return RestoreExecutionResult(
                            paths.transaction.name,
                            "completed",
                            safety_hash,
                        )
                    raise RestoreManualRecoveryRequired(
                        "Der Neustartprozess konnte vor dem Rollback nicht sicher beendet werden."
                    ) from error
            try:
                terminal_state = journal.read()
            except RestoreRuntimeError:
                terminal_state = None
            if terminal_state is not None and _restart_is_confirmed(terminal_state):
                if safety_hash is None:
                    raise RestoreManualRecoveryRequired(
                        "Der bestaetigte Restore besitzt keinen vollstaendigen Sicherheitsnachweis."
                    ) from error
                return RestoreExecutionResult(
                    paths.transaction.name,
                    "completed",
                    safety_hash,
                )
            try:
                mutation_started = _replacement_has_mutated(paths, journal.read())
            except RestoreRuntimeError as journal_error:
                try:
                    journal.transition(
                        "manual_recovery_required",
                        next_step="manual_recovery",
                        error_class=type(journal_error).__name__,
                    )
                except RestoreRuntimeError:
                    pass
                raise RestoreManualRecoveryRequired(
                    "Der Restore-Zustand ist nach einem Fehler nicht beweisbar."
                ) from journal_error
            if not mutation_started:
                self._restore_preflight_bytes(paths)
                journal.transition(
                    "aborted_before_replacement",
                    next_step="none",
                    error_class=type(error).__name__,
                )
                if isinstance(error, RestorePreflightError):
                    raise
                raise RestorePreflightError(
                    "Der Restore-Preflight wurde ohne Live-Austausch abgebrochen."
                ) from error
            try:
                rollback_restore(paths, journal)
            except Exception as rollback_error:
                journal.transition(
                    "manual_recovery_required",
                    next_step="manual_recovery",
                    error_class=type(rollback_error).__name__,
                )
                raise RestoreManualRecoveryRequired(
                    "Der Restore und sein automatischer Rollback sind fehlgeschlagen."
                ) from rollback_error
            raise RestoreReplacementError("Der Restore wurde vollstaendig zurueckgerollt.") from error

    def _preflight(self, paths: RestoreTransactionPaths, handoff: Mapping[str, object], journal: RestoreJournal) -> str:
        _validate_boundaries(paths)
        self.staging_service.verify_prepared(
            runtime_root=paths.runtime_root,
            live_documents=paths.live_documents,
            restore_id=str(handoff["restore_id"]),
        )
        _assert_evidence(paths.staging_state, int(paths.staging_state.stat().st_size), str(handoff["staging_state_sha256"]), hash_only=True)
        _assert_evidence(
            paths.prepared_database,
            int(handoff["prepared_database_size_bytes"]),
            str(handoff["prepared_database_sha256"]),
        )
        archive = paths.bound_archive
        _assert_evidence(archive, int(handoff["archive_size_bytes"]), str(handoff["archive_sha256"]))
        BackupVerifier().verify_backup(archive)
        _check_space_and_filesystem(paths)
        if not paths.live_database.is_file():
            raise RestorePreflightError("Die produktive SQLite-Datei fehlt.")
        safety = self.safety_service.create(
            restore_id=str(handoff["restore_id"]),
            runtime_root=paths.runtime_root,
            database_path=paths.live_database,
            documents_root=paths.live_documents,
            backups_root=paths.backups,
            app_version=str(handoff["app_version"]),
            build_commit=str(handoff["build_commit"]),
            source_tree_state=(None if handoff["source_tree_state"] is None else str(handoff["source_tree_state"])),
        )
        self._snapshot_preflight_bytes(paths)
        _checkpoint_and_verify_live(paths.live_database)
        components = {
            "database": _component_record(paths.live_database, paths.rollback / "kompetenzmanager.sqlite", paths.failed_new / "kompetenzmanager.sqlite"),
            "wal": _component_record(paths.live_wal, paths.rollback / "kompetenzmanager.sqlite-wal", paths.failed_new / "kompetenzmanager.sqlite-wal"),
            "shm": _component_record(paths.live_shm, paths.rollback / "kompetenzmanager.sqlite-shm", paths.failed_new / "kompetenzmanager.sqlite-shm"),
            "documents": _component_record(paths.live_documents, paths.rollback / "documents", paths.failed_new / "documents"),
        }
        journal.transition(
            "maintenance",
            next_step="mark_preflight_verified",
            components=components,
            live_database_sha256=components["database"]["before"]["sha256"],
            prepared_documents=_tree_evidence(paths.prepared_documents),
            safety_backup_sha256=safety.archive_sha256,
        )
        return safety.archive_sha256

    @staticmethod
    def _snapshot_preflight_bytes(paths: RestoreTransactionPaths) -> None:
        captured: dict[str, object] = {}
        for source, name in (
            (paths.live_database, "kompetenzmanager.sqlite"),
            (paths.live_wal, "kompetenzmanager.sqlite-wal"),
            (paths.live_shm, "kompetenzmanager.sqlite-shm"),
        ):
            evidence = _path_evidence(source)
            captured[name] = evidence
            if evidence.get("kind") == "file":
                shutil.copyfile(source, paths.preflight_original / name)
                _fsync_path(paths.preflight_original / name)
        _atomic_write_json(paths.preflight_original / "captured.json", captured, exclusive=True)
        _fsync_directory(paths.preflight_original)

    @staticmethod
    def _restore_preflight_bytes(paths: RestoreTransactionPaths) -> None:
        marker = paths.preflight_original / "captured.json"
        if not marker.exists():
            return
        captured = _read_canonical_json(marker, RestoreJournalError)
        for live, name in (
            (paths.live_database, "kompetenzmanager.sqlite"),
            (paths.live_wal, "kompetenzmanager.sqlite-wal"),
            (paths.live_shm, "kompetenzmanager.sqlite-shm"),
        ):
            snapshot = paths.preflight_original / name
            expected = captured.get(name)
            if not isinstance(expected, dict):
                raise RestoreJournalError("Ein physischer Preflight-Vorzustand ist unvollstaendig.")
            if expected.get("kind") == "file" and _evidence_matches(snapshot, expected):
                shutil.copyfile(snapshot, live)
                _fsync_path(live)
                if not _evidence_matches(live, expected):
                    raise RestoreJournalError("Ein physischer Preflight-Vorzustand weicht ab.")
            elif expected.get("kind") == "missing" and live.exists():
                live.unlink()
            elif expected.get("kind") == "file":
                raise RestoreJournalError("Ein physischer Preflight-Vorzustand fehlt.")
        _fsync_directory(paths.runtime_root)

    @staticmethod
    def _replace(paths: RestoreTransactionPaths, journal: RestoreJournal) -> None:
        for name, source, target in (
            ("old_database_to_rollback", paths.live_database, paths.rollback / "kompetenzmanager.sqlite"),
            ("old_wal_to_rollback", paths.live_wal, paths.rollback / "kompetenzmanager.sqlite-wal"),
            ("old_shm_to_rollback", paths.live_shm, paths.rollback / "kompetenzmanager.sqlite-shm"),
            ("old_documents_to_rollback", paths.live_documents, paths.rollback / "documents"),
        ):
            if source.exists() or source.is_symlink():
                journal.rename(name=name, source=source, target=target)
        journal.rename(name="prepared_database_to_live", source=paths.prepared_database, target=paths.live_database)
        journal.rename(name="prepared_documents_to_live", source=paths.prepared_documents, target=paths.live_documents)

    def _verify_new_live(
        self,
        paths: RestoreTransactionPaths,
        handoff: Mapping[str, object],
        documents: Mapping[str, object],
        expected_documents: object,
    ) -> None:
        _assert_evidence(
            paths.live_database,
            int(handoff["prepared_database_size_bytes"]),
            str(handoff["prepared_database_sha256"]),
        )
        result = self.compatibility_inspector.inspect(paths.live_database)
        if result.status is not DatabaseCompatibilityStatus.EXACT:
            raise RestoreReplacementError("Die installierte Datenbank ist nicht exakt V1-kompatibel.")
        _verify_sqlite_read_only(paths.live_database)
        if (
            documents.get("kind") != "directory"
            or not isinstance(expected_documents, dict)
            or dict(documents) != expected_documents
        ):
            raise RestoreReplacementError(
                "Das installierte Documents-Inventar widerspricht dem Prepared-Staging."
            )

    def _create_resume_token(self, paths: RestoreTransactionPaths) -> str:
        token = secrets.token_urlsafe(32)
        now = self.now()
        payload = {
            "created_at": _utc_timestamp(now),
            "expires_at": _utc_timestamp(now + RESUME_TOKEN_MAX_AGE),
            "restore_id": paths.transaction.name,
            "resume_token_version": RESTORE_RESUME_TOKEN_VERSION,
            "token": token,
        }
        _atomic_write_json(paths.resume_token, payload, exclusive=True)
        journal = RestoreJournal(paths)
        state = journal.read()
        handshake = dict(state.get("restart_handshake", {}))
        handshake.update({"attempts": 1, "status": "token_created"})
        journal.transition("installed_verified", next_step="await_startup_handshake", restart_handshake=handshake)
        return token


def confirm_restore_startup(runtime_root: Path, restore_id: str, token: str) -> RestoreRecoveryResult:
    paths = restore_transaction_paths(runtime_root, restore_id)
    journal = RestoreJournal(paths)
    state = journal.read()
    if state.get("phase") != "installed_verified":
        raise RestoreJournalError("Der Restore erwartet keinen Startup-Handshake.")
    payload = _read_canonical_json(paths.resume_token, RestoreHandoffError)
    if (
        payload.get("resume_token_version") != RESTORE_RESUME_TOKEN_VERSION
        or payload.get("restore_id") != restore_id
        or not secrets.compare_digest(str(payload.get("token", "")), token)
        or _parse_utc(str(payload.get("expires_at", ""))) < datetime.now(UTC)
        or paths.consumed_resume_token.exists()
    ):
        raise RestoreHandoffError("Der Resume-Token ist ungueltig oder abgelaufen.")
    expected_hash = str(state.get("prepared_database_sha256", ""))
    size, actual_hash = _file_evidence_values(paths.live_database)
    if actual_hash != expected_hash or size <= 0:
        raise RestoreReplacementError("Die Live-Datenbank widerspricht dem installierten Zustand.")
    result = DatabaseCompatibilityInspector().inspect(paths.live_database)
    if result.status is not DatabaseCompatibilityStatus.EXACT:
        raise RestoreReplacementError("Die Live-Datenbank ist beim Startup nicht exakt V1.")
    _verify_sqlite_read_only(paths.live_database)
    expected_documents = state.get("installed_documents")
    if not isinstance(expected_documents, dict) or _tree_evidence(paths.live_documents) != expected_documents:
        raise RestoreReplacementError("Das Documents-Inventar widerspricht dem installierten Zustand.")
    os.rename(paths.resume_token, paths.consumed_resume_token)
    _fsync_directory(paths.transaction)
    handshake = dict(state.get("restart_handshake", {}))
    handshake.update({"status": "confirmed", "confirmed_at": _utc_now()})
    journal.transition("completed", next_step="none", restart_handshake=handshake)
    return RestoreRecoveryResult("completed", restore_id)


def recover_interrupted_restore(runtime_root: Path) -> RestoreRecoveryResult:
    root = _canonical_root(runtime_root)
    parent = root / RESTORE_TRANSACTION_DIRECTORY
    if not parent.exists():
        return RestoreRecoveryResult("normal_start")
    candidates: list[tuple[RestoreTransactionPaths, dict[str, object]]] = []
    for child in sorted(parent.iterdir()):
        if child.is_symlink() or not child.is_dir():
            raise RestoreManualRecoveryRequired("Der Restore-Transaktionsbereich ist widerspruechlich.")
        try:
            paths = restore_transaction_paths(root, child.name)
            state = RestoreJournal(paths).read()
        except RestoreRuntimeError as error:
            raise RestoreManualRecoveryRequired("Ein Restore-Journal ist nicht beweisbar.") from error
        phase = str(state.get("phase"))
        if phase not in _TERMINAL_PHASES and not _restart_is_confirmed(state):
            candidates.append((paths, state))
    if not candidates:
        return RestoreRecoveryResult("normal_start")
    if len(candidates) != 1:
        raise RestoreManualRecoveryRequired("Mehrere offene Restore-Transaktionen wurden gefunden.")
    paths, state = candidates[0]
    journal = RestoreJournal(paths)
    phase = str(state.get("phase"))
    if phase == "manual_recovery_required":
        raise RestoreManualRecoveryRequired("Der Restore verlangt manuelle Wiederherstellung.")
    if phase in {
        "handoff_created",
        "worker_started",
        "maintenance",
        "preflight_verified",
    }:
        if state.get("completed_renames"):
            return _recover_by_rollback(paths, journal)
        components = state.get("components")
        if isinstance(components, dict) and components:
            live_by_name = {
                "database": paths.live_database,
                "wal": paths.live_wal,
                "shm": paths.live_shm,
                "documents": paths.live_documents,
            }
            for name, live in live_by_name.items():
                record = components.get(name)
                before = record.get("before") if isinstance(record, dict) else None
                if not isinstance(before, dict) or not _evidence_matches(live, before):
                    raise RestoreManualRecoveryRequired(
                        "Ein Live-Pfad widerspricht dem journalisierten Vorzustand."
                    )
        ProductiveRestoreService._restore_preflight_bytes(paths)
        journal.transition("aborted_before_replacement", next_step="none")
        return RestoreRecoveryResult("aborted_before_replacement", paths.transaction.name)
    if phase in {"replacement_started", "rollback_started"}:
        if phase == "replacement_started" and not _replacement_has_mutated(paths, state):
            ProductiveRestoreService._restore_preflight_bytes(paths)
            journal.transition("aborted_before_replacement", next_step="none")
            return RestoreRecoveryResult(
                "aborted_before_replacement", paths.transaction.name
            )
        return _recover_by_rollback(paths, journal)
    if phase == "installed_verified":
        handshake = state.get("restart_handshake")
        attempts = int(handshake.get("attempts", 0)) if isinstance(handshake, dict) else 0
        if attempts >= MAX_RESUME_ATTEMPTS or not paths.resume_token.is_file():
            return _recover_by_rollback(paths, journal)
        payload = _read_canonical_json(paths.resume_token, RestoreHandoffError)
        if _parse_utc(str(payload.get("expires_at", ""))) < datetime.now(UTC):
            return _recover_by_rollback(paths, journal)
        handshake = dict(handshake or {})
        handshake["attempts"] = attempts + 1
        handshake["status"] = "startup_recovery_resume"
        journal.transition("installed_verified", next_step="confirm_startup", restart_handshake=handshake)
        return RestoreRecoveryResult("resume_required", paths.transaction.name, str(payload.get("token")))
    raise RestoreManualRecoveryRequired("Der Restore-Zustand ist unbekannt.")


def _recover_by_rollback(paths: RestoreTransactionPaths, journal: RestoreJournal) -> RestoreRecoveryResult:
    try:
        rollback_restore(paths, journal)
    except Exception as error:
        journal.transition("manual_recovery_required", next_step="manual_recovery", error_class=type(error).__name__)
        raise RestoreManualRecoveryRequired("Der Start-Rollback ist fehlgeschlagen.") from error
    return RestoreRecoveryResult("rolled_back", paths.transaction.name)


def rollback_restore(paths: RestoreTransactionPaths, journal: RestoreJournal) -> None:
    state = journal.transition("rollback_started", next_step="remove_new_live")
    components = state.get("components")
    if not isinstance(components, dict) or "database" not in components:
        raise RestoreRollbackError("Die Rollback-Komponenten sind nicht beweisbar.")
    live_by_name = {
        "database": paths.live_database,
        "wal": paths.live_wal,
        "shm": paths.live_shm,
        "documents": paths.live_documents,
    }
    for name in ("database", "wal", "shm", "documents"):
        record = components.get(name)
        if not isinstance(record, dict):
            raise RestoreRollbackError("Eine Rollback-Komponente fehlt.")
        live = live_by_name[name]
        failed = Path(str(record["failed_path"]))
        before = record.get("before")
        if live.exists() or live.is_symlink():
            if isinstance(before, dict) and _evidence_matches(live, before) and not Path(str(record["rollback_path"])).exists():
                continue
            if failed.exists() or failed.is_symlink():
                raise RestoreRollbackError("Alter und neuer Bestand sind widerspruechlich vorhanden.")
            journal.rename(name=f"new_{name}_to_failed", source=live, target=failed)
        rollback = Path(str(record["rollback_path"]))
        if not isinstance(before, dict):
            raise RestoreRollbackError("Der Vorzustand ist ungueltig.")
        if before.get("kind") == "missing":
            if rollback.exists() or rollback.is_symlink():
                raise RestoreRollbackError("Ein als fehlend erfasster Altbestand existiert.")
            continue
        if rollback.exists() or rollback.is_symlink():
            if not _evidence_matches(rollback, before):
                raise RestoreRollbackError("Ein Rollbackbestand weicht vom Vorzustand ab.")
            journal.rename(name=f"old_{name}_to_live", source=rollback, target=live)
        elif not _evidence_matches(live, before):
            raise RestoreRollbackError("Der alte Bestand kann nicht vollstaendig hergestellt werden.")
    _verify_sqlite_read_only(paths.live_database, immutable=False)
    for name, live in live_by_name.items():
        if not _evidence_matches(live, components[name]["before"]):
            raise RestoreRollbackError("Der wiederhergestellte Bestand ist nicht byteidentisch.")
    journal.transition("rolled_back", next_step="none", error_class=None)


def _component_record(live: Path, rollback: Path, failed: Path) -> dict[str, object]:
    return {
        "before": _path_evidence(live),
        "failed_path": str(failed),
        "rollback_path": str(rollback),
    }


def _replacement_has_mutated(
    paths: RestoreTransactionPaths,
    state: Mapping[str, object],
) -> bool:
    components = state.get("components")
    if not isinstance(components, dict) or not components:
        return False
    live_by_name = {
        "database": paths.live_database,
        "wal": paths.live_wal,
        "shm": paths.live_shm,
        "documents": paths.live_documents,
    }
    for name, live in live_by_name.items():
        record = components.get(name)
        if not isinstance(record, dict) or not isinstance(record.get("before"), dict):
            raise RestoreJournalError("Eine Rename-Komponente ist nicht beweisbar.")
        rollback = Path(str(record.get("rollback_path", "")))
        failed = Path(str(record.get("failed_path", "")))
        if rollback.exists() or rollback.is_symlink() or failed.exists() or failed.is_symlink():
            return True
        if not _evidence_matches(live, record["before"]):
            return True
    if not paths.prepared_database.exists() or not paths.prepared_documents.exists():
        return True
    return False


def _path_evidence(path: Path) -> dict[str, object]:
    if not path.exists() and not path.is_symlink():
        return {"kind": "missing"}
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raise RestorePreflightError("Symlinks sind in Live- oder Restore-Pfaden unzulaessig.")
    if stat.S_ISREG(metadata.st_mode):
        size, sha256 = _file_evidence_values(path)
        return {"kind": "file", "sha256": sha256, "size_bytes": size}
    if stat.S_ISDIR(metadata.st_mode):
        return _tree_evidence(path)
    raise RestorePreflightError("Sonderdateien sind in Live- oder Restore-Pfaden unzulaessig.")


def _tree_evidence(root: Path) -> dict[str, object]:
    if not root.exists():
        return {"kind": "missing"}
    if root.is_symlink() or not root.is_dir():
        raise RestorePreflightError("Das Documents-Inventar ist kein regulaeres Verzeichnis.")
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        metadata = path.lstat()
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if stat.S_ISLNK(metadata.st_mode):
            raise RestorePreflightError("Ein Symlink liegt im Documents-Inventar.")
        if stat.S_ISDIR(metadata.st_mode):
            digest.update(b"D\0" + relative + b"\0")
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise RestorePreflightError("Eine Sonderdatei liegt im Documents-Inventar.")
        size, sha256 = _file_evidence_values(path)
        digest.update(b"F\0" + relative + b"\0" + str(size).encode("ascii") + b"\0" + sha256.encode("ascii") + b"\0")
        count += 1
        total += size
    return {"file_count": count, "kind": "directory", "sha256": digest.hexdigest(), "size_bytes": total}


def _evidence_matches(path: Path, expected: Mapping[str, object]) -> bool:
    try:
        return _path_evidence(path) == dict(expected)
    except RestoreRuntimeError:
        return False


def _checkpoint_and_verify_live(path: Path) -> None:
    try:
        with closing(sqlite3.connect(path, timeout=5.0)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RestorePreflightError("Live-SQLite integrity_check ist fehlgeschlagen.")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise RestorePreflightError("Live-SQLite foreign_key_check ist fehlgeschlagen.")
            mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if mode == "wal":
                checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if checkpoint is None or int(checkpoint[0]) != 0:
                    raise RestorePreflightError("Der WAL-Checkpoint ist blockiert.")
            connection.execute("BEGIN EXCLUSIVE")
            connection.commit()
    except RestoreRuntimeError:
        raise
    except sqlite3.Error as error:
        raise RestorePreflightError("Die Live-Datenbank ist noch belegt oder nicht pruefbar.") from error


def _verify_sqlite_read_only(path: Path, *, immutable: bool = True) -> None:
    try:
        suffix = "?mode=ro&immutable=1" if immutable else "?mode=ro"
        uri = f"{path.resolve(strict=True).as_uri()}{suffix}"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only = ON")
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RestoreReplacementError("SQLite integrity_check ist fehlgeschlagen.")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise RestoreReplacementError("SQLite foreign_key_check ist fehlgeschlagen.")
    except RestoreRuntimeError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise RestoreReplacementError("Die SQLite-Datei ist nicht read-only pruefbar.") from error


def _validate_boundaries(paths: RestoreTransactionPaths) -> None:
    fixed = [
        paths.live_database, paths.live_documents, paths.staging_root, paths.transaction,
        paths.backups, paths.bound_archive,
    ]
    for path in fixed:
        absolute = Path(os.path.abspath(path))
        if path in {paths.live_database, paths.live_documents, paths.staging_root, paths.transaction, paths.backups} and not absolute.is_relative_to(paths.runtime_root):
            raise RestorePreflightError("Ein Restore-Pfad verlaesst die Runtime-Wurzel.")
    for index, first in enumerate((paths.live_database, paths.live_documents, paths.staging_root, paths.transaction)):
        for second in (paths.live_database, paths.live_documents, paths.staging_root, paths.transaction)[index + 1:]:
            if _overlap(first, second):
                raise RestorePreflightError("Live-, Staging- und Transaktionspfade sind nicht disjunkt.")


def _check_space_and_filesystem(paths: RestoreTransactionPaths) -> None:
    roots = [paths.runtime_root, paths.prepared_database.parent, paths.prepared_documents]
    devices = {path.stat().st_dev for path in roots}
    if len(devices) != 1:
        raise RestorePreflightError("Restore-Renames liegen nicht auf demselben Dateisystem.")
    prepared = paths.prepared_database.stat().st_size + int(_tree_evidence(paths.prepared_documents).get("size_bytes", 0))
    live = paths.live_database.stat().st_size if paths.live_database.exists() else 0
    live += int(_tree_evidence(paths.live_documents).get("size_bytes", 0)) if paths.live_documents.exists() else 0
    if shutil.disk_usage(paths.runtime_root).free < prepared + live + 10 * 1024 * 1024:
        raise RestorePreflightError("Der freie Speicher reicht fuer Restore und Rollback nicht aus.")
    probe = paths.transaction / ".write-probe"
    try:
        with probe.open("xb") as file:
            file.write(b"ok")
            file.flush()
            os.fsync(file.fileno())
        probe.unlink()
        _fsync_directory(paths.transaction)
    except OSError as error:
        raise RestorePreflightError("Der Restore-Transaktionsbereich ist nicht beschreibbar.") from error


def _assert_runtime_projection(runtime_paths: RuntimeRestorePathSet, paths: RestoreTransactionPaths) -> None:
    expected = {
        "root": paths.runtime_root,
        "database": paths.live_database,
        "documents": paths.live_documents,
        "backups": paths.backups,
    }
    for name, value in expected.items():
        actual = Path(getattr(runtime_paths, name)).expanduser().resolve(strict=False)
        if actual != value:
            raise RestoreHandoffError("Die Runtime-Pfadprojektion ist widerspruechlich.")


def _assert_evidence(path: Path, expected_size: int, expected_hash: str, *, hash_only: bool = False) -> None:
    size, sha256 = _file_evidence_values(path)
    if sha256 != expected_hash or (not hash_only and size != expected_size):
        raise RestorePreflightError("Eine gebundene Restore-Datei wurde veraendert.")


def _validate_hash_fields(payload: Mapping[str, object]) -> None:
    for key in ("archive_sha256", "prepared_database_sha256", "staging_state_sha256"):
        value = payload.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise RestoreHandoffError("Die Handoff-Datei enthaelt einen ungueltigen Hash.")
    for key in ("archive_size_bytes", "prepared_database_size_bytes"):
        if type(payload.get(key)) is not int or int(payload[key]) < 0:
            raise RestoreHandoffError("Die Handoff-Datei enthaelt eine ungueltige Groesse.")


def _validate_build_metadata(
    app_version: str,
    build_commit: str,
    source_tree_state: str | None,
) -> None:
    if not isinstance(app_version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+\-]{0,63}", app_version):
        raise RestoreHandoffError("Die technische App-Version ist ungueltig.")
    if not isinstance(build_commit, str) or not re.fullmatch(r"(?:[0-9a-f]{7,64}|unknown)", build_commit):
        raise RestoreHandoffError("Der technische Build-Commit ist ungueltig.")
    if source_tree_state not in {None, "clean", "dirty"}:
        raise RestoreHandoffError("Der technische Source-Tree-Status ist ungueltig.")


def _copy_bound_archive(
    source: Path,
    target: Path,
    *,
    expected_size: int,
    expected_hash: str,
) -> None:
    if target.exists():
        raise RestoreHandoffError("Die gebundene Restore-Quelle existiert bereits.")
    try:
        with source.open("rb") as input_file, target.open("xb") as output_file:
            os.chmod(target, 0o600)
            shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
            output_file.flush()
            os.fsync(output_file.fileno())
        _fsync_directory(target.parent)
        _assert_evidence(target, expected_size, expected_hash)
    except (OSError, RestoreRuntimeError) as error:
        target.unlink(missing_ok=True)
        raise RestoreHandoffError("Die Restore-Quelle konnte nicht stabil gebunden werden.") from error


def _restart_is_confirmed(state: Mapping[str, object]) -> bool:
    handshake = state.get("restart_handshake")
    return state.get("phase") == "completed" or (
        isinstance(handshake, dict) and handshake.get("status") == "confirmed"
    )


def _terminate_and_reap_restart_process(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float = 2.0,
) -> int:
    exit_code = process.poll()
    if exit_code is not None:
        return exit_code
    try:
        process.terminate()
    except ProcessLookupError:
        pass
    try:
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        return process.wait(timeout=timeout_seconds)


def _restart_application(
    paths: RestoreTransactionPaths,
    token: str,
    lock: RuntimeInstanceLock,
) -> subprocess.Popen[bytes] | None:
    try:
        executable = Path(sys.executable).expanduser().resolve(strict=True)
    except OSError:
        return None
    if not executable.is_file() or not os.access(executable, os.X_OK):
        return None
    frozen = getattr(sys, "frozen", False)
    if frozen:
        command = [str(executable)]
        working_directory = paths.runtime_root
        environment = dict(os.environ)
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    else:
        command = [str(executable), "-m", "src.desktop_app.main"]
        working_directory = Path(__file__).resolve().parents[2]
    command.extend([
        "--restore-resume", paths.transaction.name,
        "--restore-token", token,
        "--restore-lock-fd", str(lock.fileno),
    ])
    try:
        if frozen:
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
        return subprocess.Popen(
            command,
            pass_fds=(lock.fileno,),
            close_fds=True,
            cwd=working_directory,
            start_new_session=os.name == "posix",
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _path_role(path: Path, paths: RestoreTransactionPaths) -> str:
    mappings = {
        paths.live_database: "live_database", paths.live_wal: "live_wal", paths.live_shm: "live_shm",
        paths.live_documents: "live_documents", paths.prepared_database: "prepared_database",
        paths.prepared_documents: "prepared_documents",
    }
    if path in mappings:
        return mappings[path]
    for root, label in ((paths.rollback, "rollback"), (paths.failed_new, "failed_new")):
        if path.is_relative_to(root):
            return f"{label}/{path.relative_to(root).as_posix()}"
    raise RestoreJournalError("Ein Rename-Pfad besitzt keine registrierte technische Rolle.")


def _atomic_write_json(path: Path, payload: Mapping[str, object], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    data = _canonical_bytes(payload)
    try:
        with temporary.open("xb") as file:
            os.chmod(temporary, 0o600)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if exclusive and path.exists():
            raise FileExistsError(path)
        if exclusive:
            os.link(temporary, path)
            temporary.unlink()
        else:
            os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, _canonical_bytes(payload) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, 0o600)
    _fsync_directory(path.parent)


def _read_canonical_json(path: Path, error_type: type[RestoreRuntimeError]) -> dict[str, object]:
    try:
        raw = _read_regular_bytes(path)
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise error_type("Eine technische Restore-Datei ist nicht lesbar.") from error
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise error_type("Eine technische Restore-Datei ist nicht kanonisch.")
    return payload


def _read_regular_bytes(path: Path) -> bytes:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RestoreRuntimeError("Eine technische Restore-Datei ist keine regulaere Datei.")
    return path.read_bytes()


def _file_evidence_values(path: Path) -> tuple[int, str]:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RestoreRuntimeError("Eine technische Restore-Datei ist keine regulaere Datei.")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utc_now() -> str:
    return _utc_timestamp(datetime.now(UTC))


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RestoreHandoffError("Ein technischer UTC-Zeitpunkt ist ungueltig.") from error
    if parsed.tzinfo is None:
        raise RestoreHandoffError("Ein technischer UTC-Zeitpunkt besitzt keine Zeitzone.")
    return parsed.astimezone(UTC)


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _overlap(first: Path, second: Path) -> bool:
    first = Path(os.path.abspath(first))
    second = Path(os.path.abspath(second))
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_path(path: Path) -> None:
    flags = os.O_RDONLY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
