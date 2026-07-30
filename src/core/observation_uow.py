"""Recoverable observation and attachment persistence unit of work."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .observation import ObservationCompetencyRatingRecord, ObservationRecord
from .maintenance_gate import product_writer
from .persistence_events import (
    PersistenceEventKind,
    PersistenceEventRecord,
    PersistenceOrderingState,
    SQLitePersistenceEventRepository,
    canonical_payload_hash,
    canonical_utc_second,
)
from .sqlite_store import DocumentRecord, SQLiteDatabase


JOURNAL_VERSION = 1
JOURNAL_MAX_BYTES = 1_000_000
OPERATION_TOKEN_PATTERN = re.compile(r"^[a-f0-9]{32}$")
ID_PATTERN = re.compile(r"^(OBS|MED)-([0-9]{6})$")
PHASES = (
    "PREPARED",
    "FILES_STAGED",
    "FILES_PUBLISHED",
    "DATABASE_COMMITTED",
    "COMPLETE",
)
PHASE_REVISIONS = {
    "PREPARED": 1,
    "FILES_STAGED": 2,
    "FILES_PUBLISHED": 3,
    "DATABASE_COMMITTED": 4,
    "COMPLETE": 5,
}
JOURNAL_FIELDS = {
    "attachment_intent",
    "before_documents",
    "before_observation",
    "before_state_hash",
    "journal_digest",
    "journal_version",
    "mode",
    "new_documents",
    "operation_payload_hash",
    "operation_token",
    "phase",
    "removed_document_ids",
    "revision",
    "target_documents",
    "target_observation",
    "target_state_hash",
}


class ObservationUnitOfWorkError(RuntimeError):
    """Raised when an observation operation cannot be safely continued."""


class ObservationOperationConflict(ObservationUnitOfWorkError):
    """Raised when current persistence state matches neither before nor target."""


def new_operation_token() -> str:
    return uuid.uuid4().hex


class ObservationWriterLock:
    """Kernel-released exclusive advisory lock shared by product writers."""

    _registry_guard = threading.Lock()
    _process_locks: dict[str, threading.RLock] = {}
    _thread_state = threading.local()

    def __init__(self, staging_root: Path) -> None:
        self.staging_root = Path(staging_root)
        self.lock_path = self.staging_root / ".writer.lock"
        self._fd: int | None = None
        self._process_lock: threading.RLock | None = None
        self._lock_key = str(self.lock_path.absolute())
        self._nested = False

    def __enter__(self) -> "ObservationWriterLock":
        with self._registry_guard:
            process_lock = self._process_locks.setdefault(
                self._lock_key,
                threading.RLock(),
            )
        process_lock.acquire()
        self._process_lock = process_lock
        depths = getattr(self._thread_state, "depths", {})
        self._thread_state.depths = depths
        depth = int(depths.get(self._lock_key, 0))
        depths[self._lock_key] = depth + 1
        if depth:
            self._nested = True
            return self
        try:
            self.staging_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._assert_private_directory(self.staging_root)
            flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(self.lock_path, flags, 0o600)
            try:
                os.fchmod(fd, 0o600)
                fcntl.flock(fd, fcntl.LOCK_EX)
            except Exception:
                os.close(fd)
                raise
            self._fd = fd
        except Exception:
            depths.pop(self._lock_key, None)
            process_lock.release()
            self._process_lock = None
            raise
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if not self._nested and self._fd is not None:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                finally:
                    os.close(self._fd)
                    self._fd = None
        finally:
            depths = getattr(self._thread_state, "depths", {})
            depth = int(depths.get(self._lock_key, 0))
            if depth <= 1:
                depths.pop(self._lock_key, None)
            else:
                depths[self._lock_key] = depth - 1
            if self._process_lock is not None:
                self._process_lock.release()
                self._process_lock = None

    @staticmethod
    def _assert_private_directory(path: Path) -> None:
        details = path.lstat()
        if not stat.S_ISDIR(details.st_mode) or path.is_symlink():
            raise ObservationUnitOfWorkError("Observation-Staging ist kein sicheres Verzeichnis.")
        if stat.S_IMODE(details.st_mode) & 0o077:
            os.chmod(path, 0o700)


class ObservationOperationJournal:
    """Canonical crash journal; not an authenticated same-user security log."""

    def __init__(self, operation_root: Path) -> None:
        self.operation_root = Path(operation_root)
        self.path = self.operation_root / "journal.json"

    def write(self, value: dict[str, object]) -> None:
        payload = dict(value)
        payload["journal_version"] = JOURNAL_VERSION
        payload["journal_digest"] = ""
        payload["journal_digest"] = canonical_payload_hash(payload)
        encoded = _canonical_json(payload)
        if len(encoded) > JOURNAL_MAX_BYTES:
            raise ObservationUnitOfWorkError("Observation-Journal ist zu gross.")
        root_created = not self.operation_root.exists()
        self.operation_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.operation_root, 0o700)
        if root_created:
            _fsync_directory(self.operation_root.parent)
        temporary = self.operation_root / f".journal-{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(temporary, flags, 0o600)
        try:
            _write_all(fd, encoded)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temporary, self.path)
        _fsync_directory(self.operation_root)

    def read(self) -> dict[str, object]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags)
        try:
            details = os.fstat(fd)
            if details.st_size > JOURNAL_MAX_BYTES:
                raise ObservationUnitOfWorkError("Observation-Journal ist zu gross.")
            encoded = _read_all(fd, JOURNAL_MAX_BYTES + 1)
        finally:
            os.close(fd)
        try:
            value = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ObservationUnitOfWorkError("Observation-Journal ist beschaedigt.") from error
        if not isinstance(value, dict) or value.get("journal_version") != JOURNAL_VERSION:
            raise ObservationUnitOfWorkError("Observation-Journal-Version ist ungueltig.")
        if set(value) != JOURNAL_FIELDS:
            raise ObservationUnitOfWorkError("Observation-Journal-Felder sind ungueltig.")
        expected = value.get("journal_digest")
        checked = dict(value)
        checked["journal_digest"] = ""
        if not isinstance(expected, str) or canonical_payload_hash(checked) != expected:
            raise ObservationUnitOfWorkError("Observation-Journal-Pruefsumme ist ungueltig.")
        if value.get("phase") not in PHASES:
            raise ObservationUnitOfWorkError("Observation-Journal-Phase ist ungueltig.")
        phase = str(value["phase"])
        if value.get("revision") != PHASE_REVISIONS[phase]:
            raise ObservationUnitOfWorkError("Observation-Journal-Revision ist ungueltig.")
        if value.get("operation_token") != self.operation_root.name:
            raise ObservationUnitOfWorkError("Observation-Journal-Token ist ungueltig.")
        return value


class ObservationPersistenceUnitOfWork:
    """Persist observation, events, and attachment references as one DB unit."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database
        self.data_root = Path(database.path).parent
        self.documents_root = self.data_root / "documents"
        self.staging_root = self.data_root / ".observation-staging"

    @product_writer
    def save(
        self,
        *,
        observation: ObservationRecord,
        attachments: Iterable[object],
        operation_token: str,
        create: bool,
    ) -> ObservationRecord:
        token = self._validate_token(operation_token)
        attachments = tuple(attachments)
        with ObservationWriterLock(self.staging_root):
            self._recover_incomplete(except_token=token)
            if not create and self.is_exact_noop(
                observation=observation,
                attachments=attachments,
            ):
                current = self._read_observation(observation.observation_id)
                if current is None:
                    raise ObservationOperationConflict("Beobachtung wurde nicht gefunden.")
                return current
            journal = ObservationOperationJournal(self.staging_root / token)
            if journal.path.exists():
                state = journal.read()
                self._validate_retry_intent(
                    state,
                    observation,
                    attachments,
                    create,
                )
            else:
                state = self._prepare(
                    journal=journal,
                    observation=observation,
                    attachments=attachments,
                    create=create,
                    operation_token=token,
                )
            self._continue(journal, state)
            return _observation_from_payload(state["target_observation"])

    @product_writer
    def recover_pending(self) -> None:
        with ObservationWriterLock(self.staging_root):
            self._recover_incomplete(except_token=None)

    @product_writer
    def recover_pending_while_writer_locked(self) -> None:
        """Continue pending work while the caller owns the shared writer lock."""
        self._recover_incomplete(except_token=None)

    def is_exact_noop(
        self,
        *,
        observation: ObservationRecord,
        attachments: Iterable[object],
    ) -> bool:
        """Return whether an edit would leave observation and attachments unchanged."""
        current = self._read_observation(observation.observation_id)
        if current is None:
            return False
        if _observation_business_intent(current) != _observation_business_intent(
            observation
        ):
            return False
        requested = tuple(attachments)
        if any(
            not str(getattr(attachment, "document_id", "")).strip()
            for attachment in requested
        ):
            return False
        current_ids = {
            document.document_id
            for document in self._read_active_documents(observation.observation_id)
        }
        requested_ids = {
            str(getattr(attachment, "document_id", "")).strip()
            for attachment in requested
        }
        return requested_ids == current_ids

    def _recover_incomplete(self, *, except_token: str | None) -> None:
        if not self.staging_root.exists():
            return
        for child in sorted(self.staging_root.iterdir(), key=lambda item: item.name):
            if not child.is_dir() or child.is_symlink() or child.name == except_token:
                continue
            journal = ObservationOperationJournal(child)
            if not journal.path.exists():
                continue
            state = journal.read()
            if state["phase"] == "COMPLETE":
                continue
            self._continue(journal, state)

    def _prepare(
        self,
        *,
        journal: ObservationOperationJournal,
        observation: ObservationRecord,
        attachments: tuple[object, ...],
        create: bool,
        operation_token: str,
    ) -> dict[str, object]:
        before_observation = None if create else self._read_observation(
            observation.observation_id
        )
        if create:
            observation = ObservationRecord(
                self._reserve_id("OBS"),
                observation.student_id,
                observation.date,
                observation.subject_id,
                observation.context,
                observation.note,
                observation.active,
                observation.created_at,
                observation.updated_at,
                observation.competency_ratings,
            )
        elif before_observation is None:
            raise ObservationOperationConflict("Beobachtung wurde nicht gefunden.")
        existing_documents = self._read_active_documents(observation.observation_id)
        kept_ids = {
            str(getattr(attachment, "document_id", "")).strip()
            for attachment in attachments
            if str(getattr(attachment, "document_id", "")).strip()
        }
        existing_by_id = {item.document_id: item for item in existing_documents}
        if not kept_ids.issubset(existing_by_id):
            raise ObservationOperationConflict("Ein bestehender Anhang ist unbekannt.")

        operation_root = journal.operation_root
        new_documents: list[dict[str, object]] = []
        reserved_document_ids: set[str] = set()
        for attachment in attachments:
            if str(getattr(attachment, "document_id", "")).strip():
                continue
            source_text = str(getattr(attachment, "source_path", "")).strip()
            if not source_text:
                continue
            document_id = self._reserve_id(
                "MED",
                additional_reserved=reserved_document_ids,
            )
            reserved_document_ids.add(document_id)
            source_path = Path(source_text).expanduser()
            staged_path = operation_root / "files" / f"{document_id}.staged"
            original_filename = source_path.name
            safe_filename = _safe_filename(original_filename)
            final_relative_path = (
                Path("documents")
                / observation.student_id
                / f"{document_id}_{safe_filename}"
            )
            created_at = _event_timestamp()
            document = DocumentRecord(
                document_id=document_id,
                student_id=observation.student_id,
                observation_id=observation.observation_id,
                title=str(getattr(attachment, "title", "")).strip()
                or source_path.stem,
                document_type=str(getattr(attachment, "document_type", "")).strip()
                or "Sonstiges",
                file_path=str(self.data_root / final_relative_path),
                original_filename=original_filename,
                created_at=created_at,
                note=str(getattr(attachment, "note", "")).strip(),
                active=True,
            )
            new_documents.append(
                {
                    "record": asdict(document),
                    "source_display_path": str(source_path),
                    "source_evidence": {},
                    "staging_relative_path": str(staged_path.relative_to(operation_root)),
                    "final_relative_path": str(final_relative_path),
                }
            )
        retained_documents = [
            asdict(existing_by_id[document_id])
            for document_id in sorted(kept_ids)
        ]
        removed_ids = sorted(set(existing_by_id) - kept_ids)
        target_documents = retained_documents + [
            item["record"] for item in new_documents
        ]
        before_payload = {
            "observation": (
                _observation_payload(before_observation)
                if before_observation is not None
                else None
            ),
            "documents": [asdict(item) for item in existing_documents],
        }
        target_payload = {
            "observation": _observation_payload(observation),
            "documents": target_documents,
        }
        state: dict[str, object] = {
            "phase": "PREPARED",
            "revision": 1,
            "operation_token": operation_token,
            "mode": "create" if create else "update",
            "before_state_hash": canonical_payload_hash(before_payload),
            "target_state_hash": canonical_payload_hash(target_payload),
            "operation_payload_hash": canonical_payload_hash(
                {
                    "mode": "create" if create else "update",
                    "before": before_payload,
                    "target": target_payload,
                    "removed_document_ids": removed_ids,
                }
            ),
            "before_observation": before_payload["observation"],
            "target_observation": target_payload["observation"],
            "before_documents": before_payload["documents"],
            "target_documents": target_documents,
            "new_documents": new_documents,
            "removed_document_ids": removed_ids,
            "attachment_intent": _attachment_intent(attachments),
        }
        journal.write(state)
        return state

    def _continue(
        self,
        journal: ObservationOperationJournal,
        state: dict[str, object],
    ) -> None:
        phase = str(state["phase"])
        if phase == "PREPARED":
            self._stage_files(journal, state)
            state = journal.read()
            phase = str(state["phase"])
        if phase == "FILES_STAGED":
            self._publish_files(journal, state)
            state = journal.read()
            phase = str(state["phase"])
        if phase == "FILES_PUBLISHED":
            self._verify_all_published(journal, state)
            self._commit_database(state)
            self._advance(journal, state, "DATABASE_COMMITTED")
            state = journal.read()
            phase = str(state["phase"])
        if phase == "DATABASE_COMMITTED":
            self._verify_all_published(journal, state)
            self._verify_target_state(state)
            self._advance(journal, state, "COMPLETE")
        elif phase != "COMPLETE":
            raise ObservationUnitOfWorkError("Observation-Journal ist blockiert.")

    def _stage_files(
        self,
        journal: ObservationOperationJournal,
        state: dict[str, object],
    ) -> None:
        files_root = journal.operation_root / "files"
        files_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _fsync_directory(journal.operation_root)
        staged_documents: list[dict[str, object]] = []
        for item in _dict_list(state.get("new_documents")):
            updated = dict(item)
            staged = journal.operation_root / str(item["staging_relative_path"])
            if staged.exists() or staged.is_symlink():
                details = staged.lstat()
                if not stat.S_ISREG(details.st_mode) or staged.is_symlink():
                    raise ObservationUnitOfWorkError(
                        "Gestagter Anhang ist kein regulaeres Retry-Artefakt."
                    )
                staged.unlink()
                _fsync_directory(staged.parent)
            updated["source_evidence"] = self._stage_source(
                Path(str(item["source_display_path"])),
                staged,
            )
            staged_stat = staged.stat(follow_symlinks=False)
            updated["staging_evidence"] = {
                "device": int(staged_stat.st_dev),
                "inode": int(staged_stat.st_ino),
                "size": int(staged_stat.st_size),
                "sha256": str(updated["source_evidence"]["sha256"]),
            }
            staged_documents.append(updated)
        updated_state = dict(state)
        updated_state["new_documents"] = staged_documents
        updated_state["operation_payload_hash"] = canonical_payload_hash(
            {
                "prepared_operation_payload_hash": state["operation_payload_hash"],
                "new_documents": staged_documents,
            }
        )
        self._advance(journal, updated_state, "FILES_STAGED")

    def _publish_files(
        self,
        journal: ObservationOperationJournal,
        state: dict[str, object],
    ) -> None:
        for item in _dict_list(state.get("new_documents")):
            staged = journal.operation_root / str(item["staging_relative_path"])
            target = self.data_root / str(item["final_relative_path"])
            ensure_durable_directory(target.parent)
            if target.exists():
                self._verify_published(staged, target, item)
                continue
            try:
                os.link(staged, target, follow_symlinks=False)
            except FileExistsError:
                self._verify_published(staged, target, item)
            except OSError as error:
                raise ObservationUnitOfWorkError(
                    "Anhang konnte nicht no-clobber publiziert werden."
                ) from error
            self._verify_published(staged, target, item)
            _fsync_directory(target.parent)
        self._advance(journal, state, "FILES_PUBLISHED")

    def _verify_all_published(
        self,
        journal: ObservationOperationJournal,
        state: dict[str, object],
    ) -> None:
        for item in _dict_list(state.get("new_documents")):
            staged = journal.operation_root / str(item["staging_relative_path"])
            target = self.data_root / str(item["final_relative_path"])
            if not target.exists() and not target.is_symlink():
                self._verify_staged(staged, item)
                ensure_durable_directory(target.parent)
                try:
                    os.link(staged, target, follow_symlinks=False)
                except FileExistsError:
                    pass
                except OSError as error:
                    raise ObservationUnitOfWorkError(
                        "Fehlender publizierter Anhang konnte nicht recovered werden."
                    ) from error
                _fsync_directory(target.parent)
            self._verify_published(staged, target, item)

    def _verify_staged(
        self,
        staged: Path,
        item: dict[str, object],
    ) -> os.stat_result:
        try:
            staged_stat = staged.stat(follow_symlinks=False)
        except OSError as error:
            raise ObservationUnitOfWorkError("Staginglink fehlt.") from error
        expected = _mapping(item["source_evidence"])
        staged_expected = _mapping(item.get("staging_evidence"))
        if (
            staged.is_symlink()
            or not stat.S_ISREG(staged_stat.st_mode)
            or staged_stat.st_dev != int(staged_expected["device"])
            or staged_stat.st_ino != int(staged_expected["inode"])
            or staged_stat.st_size != int(staged_expected["size"])
            or staged_stat.st_size != int(expected["size"])
            or _sha256_path(staged) != str(expected["sha256"])
        ):
            raise ObservationUnitOfWorkError("Gestagter Anhang widerspricht dem Journal.")
        return staged_stat

    def _verify_published(
        self,
        staged: Path,
        target: Path,
        item: dict[str, object],
    ) -> None:
        staged_stat = self._verify_staged(staged, item)
        try:
            target_stat = target.stat(follow_symlinks=False)
        except OSError as error:
            raise ObservationUnitOfWorkError(
                "Publizierter Anhang oder Staginglink fehlt."
            ) from error
        expected = _mapping(item["source_evidence"])
        if (
            (staged_stat.st_dev, staged_stat.st_ino)
            != (target_stat.st_dev, target_stat.st_ino)
            or target_stat.st_size != int(expected["size"])
            or _sha256_path(target) != str(expected["sha256"])
        ):
            raise ObservationUnitOfWorkError("Publizierter Anhang widerspricht dem Journal.")

    def _commit_database(self, state: dict[str, object]) -> None:
        observation = _observation_from_payload(state["target_observation"])
        token = str(state["operation_token"])
        payload_hash = str(state["operation_payload_hash"])
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing_events = connection.execute(
                    """
                    SELECT
                        operation_index,
                        operation_payload_hash,
                        event_kind,
                        student_id,
                        competency_id,
                        observation_id,
                        technical_timestamp,
                        ordering_state
                    FROM persistence_events
                    WHERE operation_token = ?
                    ORDER BY operation_index
                    """,
                    (token,),
                ).fetchall()
                if existing_events:
                    expected_events = self._events_for(state)
                    expected_rows = tuple(
                        (
                            event.operation_index,
                            event.operation_payload_hash,
                            event.event_kind,
                            event.student_id,
                            event.competency_id,
                            event.observation_id,
                            event.technical_timestamp,
                            event.ordering_state,
                        )
                        for event in expected_events
                    )
                    observed_rows = tuple(tuple(row) for row in existing_events)
                    if observed_rows != expected_rows:
                        raise ObservationOperationConflict(
                            "Operation-Token besitzt keinen exakten Ereignissatz."
                        )
                    self._verify_target_state(state, connection=connection)
                    connection.execute("COMMIT")
                    return
                current_hash = self._current_state_hash(
                    observation.observation_id,
                    connection,
                )
                if current_hash != str(state["before_state_hash"]):
                    raise ObservationOperationConflict(
                        "Beobachtungszustand wurde parallel veraendert."
                    )
                if state["mode"] == "create":
                    self._insert_observation(connection, observation)
                else:
                    self._replace_observation(connection, observation)
                self._insert_documents(
                    connection,
                    _dict_list(state.get("new_documents")),
                )
                removed = tuple(str(value) for value in state.get("removed_document_ids", []))
                if removed:
                    connection.executemany(
                        "UPDATE documents SET active = 0 WHERE document_id = ?",
                        ((document_id,) for document_id in removed),
                    )
                for event in self._events_for(state):
                    SQLitePersistenceEventRepository.append(connection, event)
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def _events_for(
        self,
        state: dict[str, object],
    ) -> tuple[PersistenceEventRecord, ...]:
        target = _observation_from_payload(state["target_observation"])
        before_payload = state.get("before_observation")
        before = (
            _observation_from_payload(before_payload)
            if isinstance(before_payload, dict)
            else None
        )
        token = str(state["operation_token"])
        payload_hash = str(state["operation_payload_hash"])
        timestamp = _required_timestamp(target.updated_at)
        anchor_kind = (
            PersistenceEventKind.OBSERVATION_CREATED.value
            if state["mode"] == "create"
            else PersistenceEventKind.OBSERVATION_UPDATED.value
        )
        events = [
            PersistenceEventRecord(
                None,
                token,
                0,
                payload_hash,
                anchor_kind,
                target.student_id,
                None,
                target.observation_id,
                timestamp,
                PersistenceOrderingState.NOT_APPLICABLE.value,
            )
        ]
        if before is None:
            affected = {
                (target.student_id, rating.competency_id)
                for rating in target.competency_ratings
            }
        else:
            affected = _affected_pairs(before, target)
        event_kind = (
            PersistenceEventKind.OBSERVATION_DEACTIVATED.value
            if before is not None and before.active and not target.active
            else PersistenceEventKind.OBSERVATION_COMPETENCY_CHANGED.value
        )
        for index, (student_id, competency_id) in enumerate(sorted(affected), start=1):
            events.append(
                PersistenceEventRecord(
                    None,
                    token,
                    index,
                    payload_hash,
                    event_kind,
                    student_id,
                    competency_id,
                    target.observation_id,
                    timestamp,
                    PersistenceOrderingState.ORDERED.value,
                )
            )
        return tuple(events)

    def _verify_target_state(
        self,
        state: dict[str, object],
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        observation_id = str(_mapping(state["target_observation"])["observation_id"])
        if connection is not None:
            current = self._current_state_hash(observation_id, connection)
        else:
            with self.database.connect() as opened:
                current = self._current_state_hash(observation_id, opened)
        if current != str(state["target_state_hash"]):
            raise ObservationOperationConflict(
                "Committeter Beobachtungszustand ist nicht der gebundene Sollzustand."
            )

    def _current_state_hash(
        self,
        observation_id: str,
        connection: sqlite3.Connection,
    ) -> str:
        observation = self._read_observation(observation_id, connection=connection)
        documents = self._read_active_documents(observation_id, connection=connection)
        return canonical_payload_hash(
            {
                "observation": (
                    _observation_payload(observation)
                    if observation is not None
                    else None
                ),
                "documents": [asdict(item) for item in documents],
            }
        )

    def _validate_retry_intent(
        self,
        state: dict[str, object],
        observation: ObservationRecord,
        attachments: tuple[object, ...],
        create: bool,
    ) -> None:
        if state["mode"] != ("create" if create else "update"):
            raise ObservationOperationConflict("Operation-Token hat einen anderen Modus.")
        target = _mapping(state["target_observation"])
        requested = _observation_payload(
            ObservationRecord(
                str(target["observation_id"]),
                observation.student_id,
                observation.date,
                observation.subject_id,
                observation.context,
                observation.note,
                observation.active,
                str(target["created_at"]),
                str(target["updated_at"]),
                observation.competency_ratings,
            )
        )
        if canonical_payload_hash(requested) != canonical_payload_hash(target):
            raise ObservationOperationConflict("Retry-Nutzlast wurde veraendert.")
        if _attachment_intent(attachments) != state["attachment_intent"]:
            raise ObservationOperationConflict(
                "Retry-Anhangsnutzlast wurde veraendert."
            )

    def _reserve_id(
        self,
        prefix: str,
        *,
        additional_reserved: set[str] | None = None,
    ) -> str:
        used: set[str] = set(additional_reserved or ())
        with self.database.connect() as connection:
            table, column = (
                ("observations", "observation_id")
                if prefix == "OBS"
                else ("documents", "document_id")
            )
            used.update(
                str(row[0])
                for row in connection.execute(f"SELECT {column} FROM {table}").fetchall()
            )
        if self.staging_root.exists():
            for journal_path in self.staging_root.glob("*/journal.json"):
                try:
                    value = ObservationOperationJournal(journal_path.parent).read()
                except ObservationUnitOfWorkError:
                    # Invalid retained material remains reserved by textual IDs.
                    for match in ID_PATTERN.finditer(
                        journal_path.read_text(encoding="utf-8", errors="ignore")
                    ):
                        used.add(match.group(0))
                    continue
                for key in ("target_observation",):
                    payload = value.get(key)
                    if isinstance(payload, dict):
                        used.add(str(payload.get("observation_id", "")))
                for item in value.get("target_documents", []):
                    if isinstance(item, dict):
                        used.add(str(item.get("document_id", "")))
            for path in self.staging_root.rglob("*"):
                match = ID_PATTERN.search(path.name)
                if match:
                    used.add(match.group(0))
        if self.documents_root.exists():
            for path in self.documents_root.rglob("*"):
                match = ID_PATTERN.match(path.name.split("_", 1)[0])
                if match:
                    used.add(match.group(0))
        number = 1
        while f"{prefix}-{number:06d}" in used:
            number += 1
        return f"{prefix}-{number:06d}"

    @product_writer
    def reserve_id_while_writer_locked(self, prefix: str) -> str:
        """Reserve an OBS/MED identifier while the shared lock is held."""
        if prefix not in {"OBS", "MED"}:
            raise ObservationUnitOfWorkError("ID-Praefix ist ungueltig.")
        return self._reserve_id(prefix)

    def _stage_source(self, source: Path, target: Path) -> dict[str, object]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        source_fd = os.open(source, flags)
        target_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            target_flags |= os.O_NOFOLLOW
        target_fd = os.open(target, target_flags, 0o600)
        digest = hashlib.sha256()
        try:
            before = os.fstat(source_fd)
            if not stat.S_ISREG(before.st_mode):
                raise ObservationUnitOfWorkError("Anhangquelle ist keine regulaere Datei.")
            size = 0
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                _write_all(target_fd, chunk)
                size += len(chunk)
            os.fsync(target_fd)
            after = os.fstat(source_fd)
            identity_before = _stat_identity(before)
            if identity_before != _stat_identity(after) or size != before.st_size:
                raise ObservationUnitOfWorkError(
                    "Anhangquelle wurde waehrend des Stagings veraendert."
                )
        finally:
            os.close(source_fd)
            os.close(target_fd)
        evidence = {
            **identity_before,
            "sha256": digest.hexdigest(),
            "size": size,
        }
        if _sha256_path(target) != evidence["sha256"] or target.stat().st_size != size:
            raise ObservationUnitOfWorkError("Gestagter Anhang ist unvollstaendig.")
        _fsync_directory(target.parent)
        return evidence

    def _read_observation(
        self,
        observation_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> ObservationRecord | None:
        own = connection is None
        opened = connection or self.database.connect()
        try:
            row = opened.execute(
                "SELECT * FROM observations WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
            if row is None:
                return None
            ratings = opened.execute(
                """
                SELECT competency_id, subject_id, subject_display_name,
                       learning_area, competency_group, competency_text, rating
                FROM observation_competency_ratings
                WHERE observation_id = ?
                ORDER BY competency_id
                """,
                (observation_id,),
            ).fetchall()
            return ObservationRecord(
                row["observation_id"],
                row["student_id"],
                row["date"],
                row["subject_id"],
                row["context"] or "",
                row["note"] or "",
                bool(row["active"]),
                row["created_at"],
                row["updated_at"],
                tuple(
                    ObservationCompetencyRatingRecord(
                        rating["competency_id"],
                        rating["subject_id"],
                        rating["subject_display_name"],
                        rating["learning_area"],
                        rating["competency_group"] or "",
                        rating["competency_text"],
                        rating["rating"],
                    )
                    for rating in ratings
                ),
            )
        finally:
            if own:
                opened.close()

    def _read_active_documents(
        self,
        observation_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> tuple[DocumentRecord, ...]:
        own = connection is None
        opened = connection or self.database.connect()
        try:
            rows = opened.execute(
                """
                SELECT document_id, student_id, observation_id, title,
                       document_type, file_path, original_filename, created_at,
                       note, active
                FROM documents
                WHERE observation_id = ? AND active = 1
                ORDER BY document_id
                """,
                (observation_id,),
            ).fetchall()
            return tuple(
                DocumentRecord(
                    row["document_id"],
                    row["student_id"],
                    row["observation_id"],
                    row["title"],
                    row["document_type"],
                    row["file_path"],
                    row["original_filename"],
                    row["created_at"],
                    row["note"] or "",
                    bool(row["active"]),
                )
                for row in rows
            )
        finally:
            if own:
                opened.close()

    @staticmethod
    def _insert_observation(
        connection: sqlite3.Connection,
        observation: ObservationRecord,
    ) -> None:
        connection.execute(
            """
            INSERT INTO observations (
                observation_id, student_id, date, subject_id, context, note,
                active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.observation_id,
                observation.student_id,
                observation.date,
                observation.subject_id,
                observation.context,
                observation.note,
                int(observation.active),
                observation.created_at,
                observation.updated_at,
            ),
        )
        ObservationPersistenceUnitOfWork._insert_ratings(connection, observation)

    @staticmethod
    def _replace_observation(
        connection: sqlite3.Connection,
        observation: ObservationRecord,
    ) -> None:
        connection.execute(
            """
            UPDATE observations
            SET student_id = ?, date = ?, subject_id = ?, context = ?, note = ?,
                active = ?, updated_at = ?
            WHERE observation_id = ?
            """,
            (
                observation.student_id,
                observation.date,
                observation.subject_id,
                observation.context,
                observation.note,
                int(observation.active),
                observation.updated_at,
                observation.observation_id,
            ),
        )
        connection.execute(
            "DELETE FROM observation_competency_ratings WHERE observation_id = ?",
            (observation.observation_id,),
        )
        ObservationPersistenceUnitOfWork._insert_ratings(connection, observation)

    @staticmethod
    def _insert_ratings(
        connection: sqlite3.Connection,
        observation: ObservationRecord,
    ) -> None:
        connection.executemany(
            """
            INSERT INTO observation_competency_ratings (
                observation_id, competency_id, subject_id, subject_display_name,
                learning_area, competency_group, competency_text, rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    observation.observation_id,
                    rating.competency_id,
                    rating.subject_id,
                    rating.subject_display_name,
                    rating.learning_area,
                    rating.competency_group,
                    rating.competency_text,
                    rating.rating,
                )
                for rating in observation.competency_ratings
            ),
        )

    @staticmethod
    def _insert_documents(
        connection: sqlite3.Connection,
        new_documents: list[dict[str, object]],
    ) -> None:
        for item in new_documents:
            document = _mapping(item["record"])
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, student_id, observation_id, title,
                    document_type, file_path, original_filename, created_at,
                    note, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document["document_id"],
                    document["student_id"],
                    document["observation_id"],
                    document["title"],
                    document["document_type"],
                    document["file_path"],
                    document["original_filename"],
                    document["created_at"],
                    document["note"],
                    int(bool(document["active"])),
                ),
            )

    @staticmethod
    def _advance(
        journal: ObservationOperationJournal,
        state: dict[str, object],
        phase: str,
    ) -> None:
        updated = dict(state)
        updated["phase"] = phase
        updated["revision"] = int(state.get("revision", 0)) + 1
        journal.write(updated)

    @staticmethod
    def _validate_token(value: str) -> str:
        token = value.strip().lower()
        if not OPERATION_TOKEN_PATTERN.fullmatch(token):
            raise ObservationUnitOfWorkError("operation_token ist ungueltig.")
        return token


def _observation_payload(observation: ObservationRecord) -> dict[str, object]:
    return {
        "observation_id": observation.observation_id,
        "student_id": observation.student_id,
        "date": observation.date,
        "subject_id": observation.subject_id,
        "context": observation.context,
        "note": observation.note,
        "active": observation.active,
        "created_at": observation.created_at,
        "updated_at": observation.updated_at,
        "competency_ratings": [
            asdict(rating)
            for rating in sorted(
                observation.competency_ratings,
                key=lambda item: item.competency_id,
            )
        ],
    }


def _observation_business_intent(
    observation: ObservationRecord,
) -> dict[str, object]:
    payload = _observation_payload(observation)
    payload.pop("created_at")
    payload.pop("updated_at")
    return payload


def _observation_from_payload(value: object) -> ObservationRecord:
    payload = _mapping(value)
    return ObservationRecord(
        str(payload["observation_id"]),
        str(payload["student_id"]),
        str(payload["date"]),
        str(payload["subject_id"]),
        str(payload["context"]),
        str(payload["note"]),
        bool(payload["active"]),
        str(payload["created_at"]),
        str(payload["updated_at"]),
        tuple(
            ObservationCompetencyRatingRecord(**_mapping(item))
            for item in payload["competency_ratings"]
        ),
    )


def _affected_pairs(
    before: ObservationRecord,
    after: ObservationRecord,
) -> set[tuple[str, str]]:
    before_ratings = {
        rating.competency_id: rating.rating
        for rating in before.competency_ratings
    }
    after_ratings = {
        rating.competency_id: rating.rating
        for rating in after.competency_ratings
    }
    if before.student_id != after.student_id:
        return {
            *((before.student_id, competency_id) for competency_id in before_ratings),
            *((after.student_id, competency_id) for competency_id in after_ratings),
        }
    if before.active and not after.active:
        return {
            (before.student_id, competency_id)
            for competency_id in before_ratings
        }
    return {
        (after.student_id, competency_id)
        for competency_id in set(before_ratings) | set(after_ratings)
        if before_ratings.get(competency_id) != after_ratings.get(competency_id)
    }


def _event_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _required_timestamp(value: str) -> str:
    normalized = canonical_utc_second(value)
    if normalized is None:
        raise ObservationUnitOfWorkError("Technischer Ereigniszeitpunkt ist ungueltig.")
    return normalized


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename.strip())
    return cleaned or "datei"


def _attachment_intent(
    attachments: Iterable[object],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for attachment in attachments:
        document_id = str(getattr(attachment, "document_id", "")).strip()
        source_text = str(getattr(attachment, "source_path", "")).strip()
        source_path = (
            str(Path(source_text).expanduser())
            if source_text
            else ""
        )
        result.append(
            {
                "document_id": document_id,
                "source_path": source_path,
                "title": str(getattr(attachment, "title", "")).strip(),
                "document_type": (
                    str(getattr(attachment, "document_type", "")).strip()
                    or "Sonstiges"
                ),
                "note": str(getattr(attachment, "note", "")).strip(),
            }
        )
    return result


def _stat_identity(value: os.stat_result) -> dict[str, int]:
    return {
        "device": int(value.st_dev),
        "inode": int(value.st_ino),
        "size": int(value.st_size),
        "mtime_ns": int(value.st_mtime_ns),
        "ctime_ns": int(value.st_ctime_ns),
    }


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        os.close(fd)
    return digest.hexdigest()


def _write_all(fd: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        written = os.write(fd, value[offset:])
        if written <= 0:
            raise ObservationUnitOfWorkError("Datei konnte nicht vollstaendig geschrieben werden.")
        offset += written


def _read_all(fd: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(fd, min(1024 * 1024, limit - size))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size >= limit:
            return b"".join(chunks)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def ensure_durable_directory(path: Path) -> None:
    """Create a directory chain and fsync every newly added parent entry."""
    path = Path(path)
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise ObservationUnitOfWorkError("Zielverzeichnis ist ungueltig.")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        _fsync_directory(directory.parent)
    if path.is_symlink() or not path.is_dir():
        raise ObservationUnitOfWorkError("Zielverzeichnis ist ungueltig.")


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ObservationUnitOfWorkError("Observation-Journal-Struktur ist ungueltig.")
    return value


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ObservationUnitOfWorkError("Observation-Journal-Liste ist ungueltig.")
    return [_mapping(item) for item in value]
