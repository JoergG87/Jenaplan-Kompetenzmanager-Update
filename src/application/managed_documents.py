"""Journaled application lifecycle for general managed student documents."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import stat
import uuid

from src.core.managed_document_store import ManagedDocumentStore
from src.core.observation_uow import (
    ObservationPersistenceUnitOfWork,
    ObservationWriterLock,
)
from src.core.persistence_events import canonical_payload_hash
from src.core.sqlite_store import (
    DocumentRecord,
    SQLiteDatabase,
    SQLiteDocumentRepository,
)


_TOKEN = re.compile(r"\A[a-f0-9]{32}\Z")
_MED_ID = re.compile(r"\AMED-[0-9]{6}\Z")
_PHASES = frozenset(
    {
        "INTENT",
        "REFERENCE_COMMIT_PENDING",
        "DATABASE_COMMITTED",
        "POINTER_PENDING",
        "REFERENCE_COMPENSATION_REQUIRED",
        "REFERENCE_COMPENSATED",
        "COMPLETE",
    }
)
_JOURNAL_VERSION = 1
_JOURNAL_MAX_BYTES = 64 * 1024
_JOURNAL_FILENAME = "managed-document.json"


class ManagedDocumentOperationError(RuntimeError):
    """Sanitized recoverable failure carrying the stable retry token."""

    def __init__(self, code: str, *, operation_token: str) -> None:
        self.code = code
        self.operation_token = operation_token
        super().__init__(code)


class ManagedStudentDocumentService:
    """Coordinate fachliche references with one shared encrypted store."""

    def __init__(
        self,
        *,
        database: SQLiteDatabase,
        store: ManagedDocumentStore,
        now_provider=None,
    ) -> None:
        self.database = database
        self.store = store
        self._repository = SQLiteDocumentRepository(database)
        self._now = now_provider or (lambda: datetime.now(UTC))
        self._data_root = Path(database.path).parent
        self._shared_lock_root = self._data_root / ".observation-staging"
        self._journal_root = self._data_root / ".managed-document-staging"

    def create(
        self,
        *,
        student_id: str,
        source_path: Path,
        document_type: str,
        title: str,
        note: str,
        operation_token: str = "",
    ) -> DocumentRecord:
        token = self._token(operation_token)
        source = self._source(source_path)
        source_evidence = self._source_evidence(source)
        metadata_hash = self._payload_hash(
            action="create",
            document_id="",
            student_id=student_id,
            source_path=source,
            document_type=document_type,
            title=title,
            note=note,
            source_evidence=source_evidence,
        )
        try:
            with ObservationWriterLock(self._shared_lock_root):
                self._recover_pending(except_token=token, block_retry_required=True)
                journal = _ManagedDocumentJournal(self._journal_root / token)
                if journal.exists():
                    state = journal.read()
                    self._require_retry(state, "create", metadata_hash)
                else:
                    document_id = ObservationPersistenceUnitOfWork(
                        self.database
                    ).reserve_id_while_writer_locked("MED")
                    plan = self.store.plan_prepare(document_id=document_id)
                    state = self._new_state(
                        token=token,
                        action="create",
                        document_id=document_id,
                        plan=plan,
                        payload_hash=metadata_hash,
                    )
                    journal.write(state)
                return self._continue_create(
                    journal=journal,
                    state=state,
                    student_id=student_id,
                    source=source,
                    document_type=document_type,
                    title=title,
                    note=note,
                    source_evidence=source_evidence,
                )
        except ManagedDocumentOperationError:
            raise
        except Exception as error:
            raise ManagedDocumentOperationError(
                getattr(error, "code", "managed_document_create_failed"),
                operation_token=token,
            ) from error

    def replace(
        self,
        *,
        document_id: str,
        source_path: Path,
        operation_token: str = "",
    ) -> DocumentRecord:
        token = self._token(operation_token)
        self._document_id(document_id)
        source = self._source(source_path)
        source_evidence = self._source_evidence(source)
        metadata_hash = self._payload_hash(
            action="replace",
            document_id=document_id,
            student_id="",
            source_path=source,
            document_type="",
            title="",
            note="",
            source_evidence=source_evidence,
        )
        try:
            with ObservationWriterLock(self._shared_lock_root):
                self._recover_pending(except_token=token, block_retry_required=True)
                current = self._require_general_document(document_id)
                journal = _ManagedDocumentJournal(self._journal_root / token)
                if journal.exists():
                    state = journal.read()
                    self._require_retry(state, "replace", metadata_hash)
                else:
                    plan = self.store.plan_prepare(document_id=document_id)
                    state = self._new_state(
                        token=token,
                        action="replace",
                        document_id=document_id,
                        plan=plan,
                        payload_hash=metadata_hash,
                    )
                    journal.write(state)
                updated = DocumentRecord(
                    document_id=current.document_id,
                    student_id=current.student_id,
                    observation_id="",
                    title=current.title,
                    document_type=current.document_type,
                    file_path="",
                    original_filename=source.name,
                    created_at=current.created_at,
                    note=current.note,
                    active=True,
                )
                if state["phase"] == "INTENT":
                    self._prepare(state, source, source_evidence)
                    self._repository.update_general_document(updated)
                    state["phase"] = "POINTER_PENDING"
                    journal.write(state)
                self.store.apply_journaled_changes(
                    prepared_plans=(state["plan"],),
                    deactivated_document_ids=(),
                )
                state["phase"] = "COMPLETE"
                journal.write(state)
                return updated
        except ManagedDocumentOperationError:
            raise
        except Exception as error:
            raise ManagedDocumentOperationError(
                getattr(error, "code", "managed_document_replace_failed"),
                operation_token=token,
            ) from error

    def remove(self, *, document_id: str, operation_token: str = "") -> None:
        token = self._token(operation_token)
        self._document_id(document_id)
        metadata_hash = self._payload_hash(
            action="remove",
            document_id=document_id,
            student_id="",
            source_path=None,
            document_type="",
            title="",
            note="",
            source_evidence=None,
        )
        try:
            with ObservationWriterLock(self._shared_lock_root):
                self._recover_pending(except_token=token, block_retry_required=True)
                journal = _ManagedDocumentJournal(self._journal_root / token)
                if journal.exists():
                    state = journal.read()
                    self._require_retry(state, "remove", metadata_hash)
                else:
                    self._require_general_document(document_id)
                    state = self._new_state(
                        token=token,
                        action="remove",
                        document_id=document_id,
                        plan=None,
                        payload_hash=metadata_hash,
                    )
                    journal.write(state)
                if state["phase"] == "INTENT":
                    state["phase"] = "REFERENCE_COMMIT_PENDING"
                    journal.write(state)
                    self._repository.deactivate_general_document(document_id)
                    state["phase"] = "DATABASE_COMMITTED"
                    journal.write(state)
                elif state["phase"] == "REFERENCE_COMMIT_PENDING":
                    record = self._repository.get_document(document_id)
                    if record is None or record.observation_id or record.active:
                        self._repository.deactivate_general_document(document_id)
                    state["phase"] = "DATABASE_COMMITTED"
                    journal.write(state)
                self.store.apply_journaled_changes(
                    prepared_plans=(),
                    deactivated_document_ids=(document_id,),
                )
                state["phase"] = "COMPLETE"
                journal.write(state)
        except ManagedDocumentOperationError:
            raise
        except Exception as error:
            raise ManagedDocumentOperationError(
                getattr(error, "code", "managed_document_remove_failed"),
                operation_token=token,
            ) from error

    def read(self, *, document_id: str, consumer: object) -> object:
        self._document_id(document_id)
        with ObservationWriterLock(self._shared_lock_root):
            previous_active_generation: int | None = None
            try:
                self._recover_pending(
                    except_token=None,
                    block_retry_required=True,
                )
            except ManagedDocumentOperationError:
                previous_active_generation = (
                    self._pending_replace_active_generation(document_id)
                )
                if previous_active_generation is None:
                    raise
            self._require_general_document(document_id)
            return self.store.read(
                document_id=document_id,
                consumer=consumer,
                document_generation=previous_active_generation,
            )

    def recover_pending(self) -> None:
        with ObservationWriterLock(self._shared_lock_root):
            self._recover_pending(
                except_token=None,
                block_retry_required=False,
            )

    def _continue_create(
        self,
        *,
        journal: "_ManagedDocumentJournal",
        state: dict[str, object],
        student_id: str,
        source: Path,
        document_type: str,
        title: str,
        note: str,
        source_evidence: dict[str, object],
    ) -> DocumentRecord:
        document_id = str(state["document_id"])
        if state["phase"] in {
            "INTENT",
            "REFERENCE_COMMIT_PENDING",
            "REFERENCE_COMPENSATED",
        }:
            self._prepare(state, source, source_evidence)
            timestamp = self._now().astimezone(UTC).replace(microsecond=0).isoformat()
            record = DocumentRecord(
                document_id=document_id,
                student_id=student_id,
                observation_id="",
                title=title.strip() or source.stem,
                document_type=document_type,
                file_path="",
                original_filename=source.name,
                created_at=timestamp,
                note=note.strip(),
                active=True,
            )
            existing = self._repository.get_document(document_id)
            if existing is None:
                state["phase"] = "REFERENCE_COMMIT_PENDING"
                journal.write(state)
                self._repository.create_document(record)
            state["phase"] = "DATABASE_COMMITTED"
            journal.write(state)
        try:
            self.store.apply_journaled_changes(
                prepared_plans=(state["plan"],), deactivated_document_ids=()
            )
        except Exception:
            try:
                self.store.apply_journaled_changes(
                    prepared_plans=(state["plan"],),
                    deactivated_document_ids=(),
                )
            except Exception:
                state["phase"] = "REFERENCE_COMPENSATION_REQUIRED"
                journal.write(state)
                self._delete_general_document_if_present(document_id)
                state["phase"] = "REFERENCE_COMPENSATED"
                journal.write(state)
                raise
        state["phase"] = "COMPLETE"
        journal.write(state)
        return self._require_general_document(document_id)

    def _prepare(
        self,
        state: dict[str, object],
        source: Path,
        source_evidence: dict[str, object],
    ) -> None:
        mime_type = mimetypes.guess_type(source.name, strict=False)[0]
        prepared = self.store.prepare(
            document_id=str(state["document_id"]),
            source_path=source,
            original_filename=source.name,
            mime_type=mime_type or "application/octet-stream",
            plan=state["plan"],
        )
        verified = self.store.verify_prepared(plan=state["plan"])
        if (
            prepared != verified
            or getattr(verified, "plaintext_size", None)
            != source_evidence["size"]
            or getattr(verified, "plaintext_sha256", None)
            != source_evidence["sha256"]
        ):
            raise ManagedDocumentOperationError(
                "managed_document_prepare_verification_mismatch",
                operation_token=str(state["operation_token"]),
            )

    def _recover_pending(
        self,
        *,
        except_token: str | None,
        block_retry_required: bool,
    ) -> None:
        if self._journal_root.is_symlink():
            raise ValueError("managed_document_journal_root_symlink")
        if not self._journal_root.exists():
            return
        _ManagedDocumentJournal._require_private_directory(self._journal_root)
        for child in sorted(self._journal_root.iterdir(), key=lambda item: item.name):
            if child.is_symlink():
                raise ValueError("managed_document_journal_operation_symlink")
            if not child.is_dir() or child.name == except_token:
                continue
            journal = _ManagedDocumentJournal(child)
            if not journal.exists():
                continue
            state = journal.read()
            if state["phase"] == "COMPLETE":
                continue
            if state["phase"] == "REFERENCE_COMMIT_PENDING":
                action = str(state["action"])
                document_id = str(state["document_id"])
                record = self._repository.get_document(document_id)
                if action == "create":
                    if record is None:
                        state["phase"] = "INTENT"
                    elif record.observation_id or not record.active:
                        raise ValueError("managed_document_reference_invalid")
                    else:
                        state["phase"] = "DATABASE_COMMITTED"
                    journal.write(state)
                elif action == "remove":
                    if record is None or record.observation_id:
                        raise ValueError("managed_document_reference_invalid")
                    if record.active:
                        state["phase"] = "INTENT"
                    else:
                        state["phase"] = "DATABASE_COMMITTED"
                    journal.write(state)
            if (
                state["phase"] == "REFERENCE_COMPENSATION_REQUIRED"
                and state["action"] == "create"
            ):
                self._delete_general_document_if_present(
                    str(state["document_id"])
                )
                state["phase"] = "REFERENCE_COMPENSATED"
                journal.write(state)
            if state["phase"] != "DATABASE_COMMITTED":
                if block_retry_required:
                    raise ManagedDocumentOperationError(
                        "managed_document_retry_required",
                        operation_token=str(state["operation_token"]),
                    )
                continue
            action = str(state["action"])
            document_id = str(state["document_id"])
            if action == "create":
                self.store.apply_journaled_changes(
                    prepared_plans=(state["plan"],),
                    deactivated_document_ids=(),
                )
            elif action == "remove":
                self.store.apply_journaled_changes(
                    prepared_plans=(),
                    deactivated_document_ids=(document_id,),
                )
            state["phase"] = "COMPLETE"
            journal.write(state)

    def _pending_replace_active_generation(
        self, document_id: str
    ) -> int | None:
        if self._journal_root.is_symlink():
            raise ValueError("managed_document_journal_root_symlink")
        if not self._journal_root.exists():
            return None
        _ManagedDocumentJournal._require_private_directory(self._journal_root)
        matches: list[dict[str, object]] = []
        for child in sorted(self._journal_root.iterdir(), key=lambda item: item.name):
            if child.is_symlink():
                raise ValueError("managed_document_journal_operation_symlink")
            if not child.is_dir():
                continue
            journal = _ManagedDocumentJournal(child)
            if not journal.exists():
                continue
            state = journal.read()
            if (
                state["phase"] in {"INTENT", "POINTER_PENDING"}
                and state["action"] == "replace"
                and state["document_id"] == document_id
            ):
                matches.append(state)
            elif state["phase"] != "COMPLETE":
                return None
        if len(matches) != 1:
            return None
        plan = matches[0].get("plan")
        if not isinstance(plan, dict):
            return None
        generation = plan.get("previous_active_generation")
        if not isinstance(generation, int) or isinstance(generation, bool):
            return None
        return generation

    def _delete_general_document_if_present(self, document_id: str) -> None:
        if self._repository.get_document(document_id) is not None:
            self._repository.delete_general_document(document_id)

    def _require_general_document(self, document_id: str) -> DocumentRecord:
        record = self._repository.get_active_general_document(document_id)
        if record is None:
            raise ManagedDocumentOperationError(
                "managed_document_not_found",
                operation_token="",
            )
        return record

    @staticmethod
    def _new_state(
        *,
        token: str,
        action: str,
        document_id: str,
        plan: object | None,
        payload_hash: str,
    ) -> dict[str, object]:
        return {
            "journal_version": _JOURNAL_VERSION,
            "journal_digest": "",
            "operation_token": token,
            "action": action,
            "phase": "INTENT",
            "document_id": document_id,
            "plan": None if plan is None else asdict(plan),
            "payload_hash": payload_hash,
        }

    @staticmethod
    def _require_retry(
        state: dict[str, object], action: str, payload_hash: str
    ) -> None:
        if state["action"] != action or state["payload_hash"] != payload_hash:
            raise ManagedDocumentOperationError(
                "managed_document_retry_conflict",
                operation_token=str(state["operation_token"]),
            )

    @staticmethod
    def _payload_hash(
        *,
        action: str,
        document_id: str,
        student_id: str,
        source_path: Path | None,
        document_type: str,
        title: str,
        note: str,
        source_evidence: dict[str, object] | None,
    ) -> str:
        return canonical_payload_hash(
            {
                "action": action,
                "document_id": document_id,
                "student_id": student_id,
                "source_path_sha256": ""
                if source_path is None
                else hashlib.sha256(os.fsencode(source_path)).hexdigest(),
                "original_filename_sha256": ""
                if source_path is None
                else hashlib.sha256(os.fsencode(source_path.name)).hexdigest(),
                "document_type": document_type,
                "title": title,
                "note": note,
                "source_size": ""
                if source_evidence is None
                else source_evidence["size"],
                "source_sha256": ""
                if source_evidence is None
                else source_evidence["sha256"],
            }
        )

    @staticmethod
    def _source_evidence(source: Path) -> dict[str, object]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(source, flags)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("managed_document_source_invalid")
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or size != after.st_size
        ):
            raise ValueError("managed_document_source_changed")
        return {"size": size, "sha256": digest.hexdigest()}

    @staticmethod
    def _source(source_path: Path) -> Path:
        source = Path(source_path).expanduser()
        if not source.is_absolute():
            source = source.absolute()
        try:
            details = source.lstat()
        except OSError:
            raise ManagedDocumentOperationError(
                "managed_document_source_missing", operation_token=""
            ) from None
        if not stat.S_ISREG(details.st_mode) or source.is_symlink():
            raise ManagedDocumentOperationError(
                "managed_document_source_invalid", operation_token=""
            )
        return source

    @staticmethod
    def _document_id(document_id: str) -> None:
        if not _MED_ID.fullmatch(document_id):
            raise ManagedDocumentOperationError(
                "managed_document_id_invalid", operation_token=""
            )

    @staticmethod
    def _token(operation_token: str) -> str:
        token = operation_token or uuid.uuid4().hex
        if not _TOKEN.fullmatch(token):
            raise ManagedDocumentOperationError(
                "managed_document_operation_token_invalid",
                operation_token="",
            )
        return token


class _ManagedDocumentJournal:
    _FIELDS = frozenset(
        {
            "journal_version",
            "journal_digest",
            "operation_token",
            "action",
            "phase",
            "document_id",
            "plan",
            "payload_hash",
        }
    )

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = self.root / _JOURNAL_FILENAME

    def exists(self) -> bool:
        if self.path.is_symlink():
            raise ValueError("managed_document_journal_symlink")
        return self.path.is_file()

    def write(self, state: dict[str, object]) -> None:
        payload = dict(state)
        payload["journal_version"] = _JOURNAL_VERSION
        payload["journal_digest"] = ""
        payload["journal_digest"] = canonical_payload_hash(payload)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > _JOURNAL_MAX_BYTES:
            raise ValueError("managed_document_journal_too_large")
        parent_created = not self.root.parent.exists()
        self.root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._require_private_directory(self.root.parent)
        if parent_created:
            self._fsync_directory(self.root.parent.parent)
        root_created = not self.root.exists()
        self.root.mkdir(mode=0o700, exist_ok=True)
        self._require_private_directory(self.root)
        if root_created:
            self._fsync_directory(self.root.parent)
        marker = self.root / str(payload["document_id"])
        if marker.is_symlink():
            raise ValueError("managed_document_reservation_symlink")
        if not marker.exists():
            marker_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                marker_flags |= os.O_NOFOLLOW
            marker_fd = os.open(marker, marker_flags, 0o600)
            os.close(marker_fd)
        marker_details = marker.lstat()
        if (
            not stat.S_ISREG(marker_details.st_mode)
            or marker_details.st_nlink != 1
            or marker_details.st_uid != os.getuid()
        ):
            raise ValueError("managed_document_reservation_invalid")
        temporary = self.root / f".{_JOURNAL_FILENAME}-{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(temporary, flags, 0o600)
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("managed_document_journal_write_failed")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temporary, self.path)
        directory_fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def read(self) -> dict[str, object]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags)
        try:
            details = os.fstat(fd)
            if (
                not stat.S_ISREG(details.st_mode)
                or details.st_nlink != 1
                or details.st_uid != os.getuid()
                or details.st_size > _JOURNAL_MAX_BYTES
            ):
                raise ValueError("managed_document_journal_too_large")
            chunks: list[bytes] = []
            remaining = _JOURNAL_MAX_BYTES + 1
            while remaining:
                chunk = os.read(fd, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            encoded = b"".join(chunks)
        finally:
            os.close(fd)
        value = json.loads(encoded)
        if (
            not isinstance(value, dict)
            or set(value) != self._FIELDS
            or value.get("journal_version") != _JOURNAL_VERSION
            or value.get("operation_token") != self.root.name
            or value.get("action") not in {"create", "replace", "remove"}
            or value.get("phase") not in _PHASES
            or not _MED_ID.fullmatch(str(value.get("document_id", "")))
        ):
            raise ValueError("managed_document_journal_invalid")
        checked = dict(value)
        expected = checked["journal_digest"]
        checked["journal_digest"] = ""
        if not isinstance(expected, str) or canonical_payload_hash(checked) != expected:
            raise ValueError("managed_document_journal_digest_invalid")
        return value

    @staticmethod
    def _require_private_directory(path: Path) -> None:
        details = path.lstat()
        if (
            not stat.S_ISDIR(details.st_mode)
            or path.is_symlink()
            or details.st_uid != os.getuid()
        ):
            raise ValueError("managed_document_journal_root_invalid")
        if stat.S_IMODE(details.st_mode) & 0o077:
            os.chmod(path, 0o700)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
