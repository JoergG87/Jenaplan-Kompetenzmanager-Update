"""Journaled encrypted storage lifecycle for immutable final PDF artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable, Generic, TypeVar
import uuid

from src.core.managed_document_store import (
    ManagedDocumentStore,
    ManagedPdfArtifactError,
)
from src.core.observation_uow import ObservationWriterLock
from src.core.persistence_events import canonical_payload_hash


MANAGED_PDF_REFERENCE_PREFIX = "managed-document:"
_JOURNAL_VERSION = 1
_JOURNAL_NAME = "managed-pdf-artifact.json"
_JOURNAL_MAX_BYTES = 64 * 1024
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_PHASES = frozenset(
    {
        "INTENT",
        "PREPARED",
        "ARTIFACT_COMMIT_PENDING",
        "ARTIFACT_COMMITTED",
        "POINTER_PENDING",
        "COMPLETE",
    }
)

ArtifactT = TypeVar("ArtifactT")


@dataclass(frozen=True)
class ManagedPdfArtifactEvidence:
    artifact_id: str
    revision_id: str
    managed_document_id: str
    managed_reference: str
    pdf_size: int
    pdf_sha256: str
    snapshot_sha256: str
    created_at: str


class ManagedPdfArtifactLifecycle(Generic[ArtifactT]):
    """Bind one fachliches immutable artifact to one encrypted generation."""

    def __init__(
        self,
        *,
        database_path: Path,
        store: ManagedDocumentStore,
        artifact_kind: str,
        next_artifact_id: Callable[[], str],
        get_for_revision: Callable[[str], ArtifactT | None],
        save_artifact: Callable[[ArtifactT], ArtifactT],
        build_artifact: Callable[[ManagedPdfArtifactEvidence], ArtifactT],
        artifact_reference: Callable[[ArtifactT], str],
        artifact_size: Callable[[ArtifactT], int],
        artifact_pdf_sha256: Callable[[ArtifactT], str],
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        if artifact_kind not in {"report", "learning_conference"}:
            raise ValueError("managed_pdf_artifact_kind_invalid")
        self.store = store
        self.artifact_kind = artifact_kind
        self._next_artifact_id = next_artifact_id
        self._get_for_revision = get_for_revision
        self._save_artifact = save_artifact
        self._build_artifact = build_artifact
        self._artifact_reference = artifact_reference
        self._artifact_size = artifact_size
        self._artifact_pdf_sha256 = artifact_pdf_sha256
        self._fault_hook = fault_hook or (lambda _phase: None)
        data_root = Path(database_path).parent
        self._lock_root = data_root / ".observation-staging"
        self._journal_root = data_root / ".managed-document-staging" / "pdf-artifacts"

    def generate(
        self,
        *,
        revision_id: str,
        snapshot_sha256: str,
        created_at: str,
        render_pdf: Callable[[], bytes],
    ) -> ArtifactT:
        with ObservationWriterLock(self._lock_root):
            journal = self._journal(revision_id)
            if journal.exists():
                state = journal.read()
                self._require_identity(
                    state,
                    revision_id=revision_id,
                    snapshot_sha256=snapshot_sha256,
                )
            else:
                existing = self._get_for_revision(revision_id)
                if existing is not None:
                    self.verify_existing(existing)
                    return existing
                document_id = str(uuid.uuid4())
                plan = self.store.plan_prepare(document_id=document_id)
                state = {
                    "journal_version": _JOURNAL_VERSION,
                    "journal_digest": "",
                    "artifact_kind": self.artifact_kind,
                    "artifact_id": self._next_artifact_id(),
                    "revision_id": revision_id,
                    "document_id": document_id,
                    "plan": asdict(plan),
                    "phase": "INTENT",
                    "snapshot_sha256": snapshot_sha256,
                    "pdf_size": 0,
                    "pdf_sha256": "",
                    "created_at": created_at,
                }
                journal.write(state)

            if state["phase"] == "INTENT":
                self._emit("before_render")
                pdf_bytes = render_pdf()
                self._validate_pdf_bytes(pdf_bytes)
                self._emit("after_pdf_stream")
                prepared = self.store.prepare_bytes(
                    document_id=str(state["document_id"]),
                    source_bytes=pdf_bytes,
                    original_filename="final.pdf",
                    mime_type="application/pdf",
                    plan=state["plan"],
                )
                self._emit("after_container_prepare")
                verified = self.store.verify_prepared(plan=state["plan"])
                digest = hashlib.sha256(pdf_bytes).hexdigest()
                if (
                    prepared != verified
                    or getattr(verified, "plaintext_size", None) != len(pdf_bytes)
                    or getattr(verified, "plaintext_sha256", None) != digest
                ):
                    raise ManagedPdfArtifactError(
                        "managed_pdf_prepare_verification_mismatch"
                    )
                self._emit("after_container_verification")
                state["pdf_size"] = len(pdf_bytes)
                state["pdf_sha256"] = digest
                state["phase"] = "PREPARED"
                journal.write(state)

            artifact = self._artifact_from_state(state)
            if state["phase"] in {"PREPARED", "ARTIFACT_COMMIT_PENDING"}:
                state["phase"] = "ARTIFACT_COMMIT_PENDING"
                journal.write(state)
                self._emit("before_artifact_commit")
                existing = self._get_for_revision(revision_id)
                if existing is None:
                    artifact = self._save_artifact(artifact)
                else:
                    self._require_artifact_matches(existing, artifact)
                    artifact = existing
                self._emit("after_artifact_commit")
                state["phase"] = "ARTIFACT_COMMITTED"
                journal.write(state)

            if state["phase"] in {"ARTIFACT_COMMITTED", "POINTER_PENDING"}:
                state["phase"] = "POINTER_PENDING"
                journal.write(state)
                self._emit("during_generation_activation")
                plan = state["plan"]
                if not isinstance(plan, dict):
                    raise ManagedPdfArtifactError("managed_pdf_journal_invalid")
                generation = plan.get("document_generation")
                self.store.activate(
                    document_id=str(state["document_id"]),
                    document_generation=(
                        generation if isinstance(generation, int) else None
                    ),
                )
                self._emit("after_activation_before_complete")
                state["phase"] = "COMPLETE"
                journal.write(state)

            if state["phase"] != "COMPLETE":
                raise ManagedPdfArtifactError("managed_pdf_retry_required")
            self.verify_existing(artifact)
            return artifact

    def verify_existing(self, artifact: ArtifactT) -> bytes:
        document_id = managed_document_id(
            self._artifact_reference(artifact)
        )
        consumer = _BytesConsumer()
        self.store.read(document_id=document_id, consumer=consumer)
        pdf_bytes = consumer.value
        self._validate_pdf_bytes(pdf_bytes)
        if (
            len(pdf_bytes) != self._artifact_size(artifact)
            or hashlib.sha256(pdf_bytes).hexdigest()
            != self._artifact_pdf_sha256(artifact)
        ):
            raise ManagedPdfArtifactError("managed_pdf_integrity_invalid")
        return pdf_bytes

    def recover_pending(self) -> None:
        with ObservationWriterLock(self._lock_root):
            for journal in self._journals():
                state = journal.read()
                if state["artifact_kind"] != self.artifact_kind:
                    continue
                if state["phase"] == "INTENT":
                    continue
                artifact = self._artifact_from_state(state)
                if state["phase"] in {"PREPARED", "ARTIFACT_COMMIT_PENDING"}:
                    state["phase"] = "ARTIFACT_COMMIT_PENDING"
                    journal.write(state)
                    existing = self._get_for_revision(str(state["revision_id"]))
                    if existing is None:
                        artifact = self._save_artifact(artifact)
                    else:
                        self._require_artifact_matches(existing, artifact)
                    state["phase"] = "ARTIFACT_COMMITTED"
                    journal.write(state)
                if state["phase"] in {"ARTIFACT_COMMITTED", "POINTER_PENDING"}:
                    state["phase"] = "POINTER_PENDING"
                    journal.write(state)
                    plan = state["plan"]
                    if not isinstance(plan, dict):
                        raise ManagedPdfArtifactError("managed_pdf_journal_invalid")
                    generation = plan.get("document_generation")
                    self.store.activate(
                        document_id=str(state["document_id"]),
                        document_generation=(
                            generation if isinstance(generation, int) else None
                        ),
                    )
                    state["phase"] = "COMPLETE"
                    journal.write(state)
                if state["phase"] == "COMPLETE":
                    self.verify_existing(artifact)

    def _artifact_from_state(self, state: dict[str, object]) -> ArtifactT:
        return self._build_artifact(
            ManagedPdfArtifactEvidence(
                artifact_id=str(state["artifact_id"]),
                revision_id=str(state["revision_id"]),
                managed_document_id=str(state["document_id"]),
                managed_reference=managed_document_reference(
                    str(state["document_id"])
                ),
                pdf_size=int(state["pdf_size"]),
                pdf_sha256=str(state["pdf_sha256"]),
                snapshot_sha256=str(state["snapshot_sha256"]),
                created_at=str(state["created_at"]),
            )
        )

    def _require_artifact_matches(
        self, existing: ArtifactT, expected: ArtifactT
    ) -> None:
        if existing != expected:
            raise ManagedPdfArtifactError("managed_pdf_artifact_conflict")

    def _require_identity(
        self,
        state: dict[str, object],
        *,
        revision_id: str,
        snapshot_sha256: str,
    ) -> None:
        if (
            state["artifact_kind"] != self.artifact_kind
            or state["revision_id"] != revision_id
            or state["snapshot_sha256"] != snapshot_sha256
        ):
            raise ManagedPdfArtifactError("managed_pdf_retry_conflict")

    def _journal(self, revision_id: str) -> "_ManagedPdfArtifactJournal":
        token = hashlib.sha256(
            f"{self.artifact_kind}:{revision_id}".encode("utf-8")
        ).hexdigest()
        return _ManagedPdfArtifactJournal(self._journal_root / token)

    def _emit(self, phase: str) -> None:
        self._fault_hook(phase)

    def _journals(self) -> tuple["_ManagedPdfArtifactJournal", ...]:
        if not self._journal_root.exists():
            return ()
        _require_private_directory(self._journal_root)
        journals: list[_ManagedPdfArtifactJournal] = []
        for child in sorted(self._journal_root.iterdir(), key=lambda item: item.name):
            if child.is_symlink() or not child.is_dir() or not _SHA256.fullmatch(child.name):
                raise ManagedPdfArtifactError("managed_pdf_journal_root_invalid")
            journal = _ManagedPdfArtifactJournal(child)
            if journal.exists():
                journals.append(journal)
        return tuple(journals)

    @staticmethod
    def _validate_pdf_bytes(pdf_bytes: bytes) -> None:
        if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF-"):
            raise ManagedPdfArtifactError("managed_pdf_render_invalid")


def managed_document_reference(document_id: str) -> str:
    try:
        parsed = uuid.UUID(document_id)
    except (ValueError, TypeError, AttributeError):
        raise ManagedPdfArtifactError("managed_pdf_document_id_invalid") from None
    if parsed.version != 4 or str(parsed) != document_id:
        raise ManagedPdfArtifactError("managed_pdf_document_id_invalid")
    return f"{MANAGED_PDF_REFERENCE_PREFIX}{document_id}"


def managed_document_id(reference: str) -> str:
    if not reference.startswith(MANAGED_PDF_REFERENCE_PREFIX):
        raise ManagedPdfArtifactError("managed_pdf_reference_invalid")
    document_id = reference[len(MANAGED_PDF_REFERENCE_PREFIX) :]
    managed_document_reference(document_id)
    return document_id


class _BytesConsumer:
    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._finished = False

    def start(self, _manifest: object) -> None:
        self._chunks.clear()
        self._finished = False

    def write(self, chunk: bytes) -> None:
        self._chunks.append(bytes(chunk))

    def finish(self, _result: object) -> None:
        self._finished = True

    def abort(self, _code: str) -> None:
        self._chunks.clear()
        self._finished = False

    @property
    def value(self) -> bytes:
        if not self._finished:
            raise ManagedPdfArtifactError("managed_pdf_read_incomplete")
        return b"".join(self._chunks)


class _ManagedPdfArtifactJournal:
    _FIELDS = frozenset(
        {
            "journal_version",
            "journal_digest",
            "artifact_kind",
            "artifact_id",
            "revision_id",
            "document_id",
            "plan",
            "phase",
            "snapshot_sha256",
            "pdf_size",
            "pdf_sha256",
            "created_at",
        }
    )

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = self.root / _JOURNAL_NAME

    def exists(self) -> bool:
        if self.path.is_symlink():
            raise ManagedPdfArtifactError("managed_pdf_journal_symlink")
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
            raise ManagedPdfArtifactError("managed_pdf_journal_too_large")
        staging_root = self.root.parent.parent
        staging_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _require_private_directory(staging_root)
        self.root.parent.mkdir(mode=0o700, exist_ok=True)
        _require_private_directory(self.root.parent)
        self.root.mkdir(mode=0o700, exist_ok=True)
        _require_private_directory(self.root)
        temporary = self.root / f".{_JOURNAL_NAME}-{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(temporary, flags, 0o600)
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("managed_pdf_journal_write_failed")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temporary, self.path)
        _fsync_directory(self.root)
        _fsync_directory(self.root.parent)

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
                raise ManagedPdfArtifactError("managed_pdf_journal_invalid")
            encoded = os.read(fd, _JOURNAL_MAX_BYTES + 1)
        finally:
            os.close(fd)
        try:
            value = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ManagedPdfArtifactError("managed_pdf_journal_invalid") from None
        if (
            not isinstance(value, dict)
            or set(value) != self._FIELDS
            or value.get("journal_version") != _JOURNAL_VERSION
            or value.get("artifact_kind") not in {"report", "learning_conference"}
            or value.get("phase") not in _PHASES
            or not _SHA256.fullmatch(str(value.get("snapshot_sha256", "")))
            or (
                value.get("pdf_sha256")
                and not _SHA256.fullmatch(str(value.get("pdf_sha256")))
            )
        ):
            raise ManagedPdfArtifactError("managed_pdf_journal_invalid")
        managed_document_reference(str(value.get("document_id", "")))
        artifact_kind = str(value["artifact_kind"])
        artifact_id = str(value.get("artifact_id", ""))
        revision_id = str(value.get("revision_id", ""))
        expected_artifact_prefix = "RPA-" if artifact_kind == "report" else "LCA-"
        expected_revision_prefix = "RPV-" if artifact_kind == "report" else "LCV-"
        plan = value.get("plan")
        pdf_size = value.get("pdf_size")
        pdf_sha256 = str(value.get("pdf_sha256", ""))
        phase = str(value["phase"])
        expected_root = hashlib.sha256(
            f"{artifact_kind}:{revision_id}".encode("utf-8")
        ).hexdigest()
        if (
            not artifact_id.startswith(expected_artifact_prefix)
            or not revision_id.startswith(expected_revision_prefix)
            or self.root.name != expected_root
            or not isinstance(plan, dict)
            or plan.get("document_id") != value["document_id"]
            or not isinstance(plan.get("document_generation"), int)
            or isinstance(plan.get("document_generation"), bool)
            or not isinstance(plan.get("storage_id"), str)
            or not isinstance(pdf_size, int)
            or isinstance(pdf_size, bool)
            or (phase == "INTENT" and (pdf_size != 0 or pdf_sha256))
            or (phase != "INTENT" and (pdf_size < 1 or not pdf_sha256))
            or not isinstance(value.get("created_at"), str)
            or not str(value.get("created_at"))
        ):
            raise ManagedPdfArtifactError("managed_pdf_journal_invalid")
        checked = dict(value)
        expected = checked["journal_digest"]
        checked["journal_digest"] = ""
        if not isinstance(expected, str) or canonical_payload_hash(checked) != expected:
            raise ManagedPdfArtifactError("managed_pdf_journal_digest_invalid")
        return value


def _require_private_directory(path: Path) -> None:
    details = path.lstat()
    if (
        not stat.S_ISDIR(details.st_mode)
        or path.is_symlink()
        or details.st_uid != os.getuid()
    ):
        raise ManagedPdfArtifactError("managed_pdf_journal_root_invalid")
    if stat.S_IMODE(details.st_mode) & 0o077:
        os.chmod(path, 0o700)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
