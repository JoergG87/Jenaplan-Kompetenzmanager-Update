"""Read-only admission checks for retained, completed application journals.

Journal digests describe historical operations; only keyed persisted evidence
binds them to an installation. No recovery, garbage collection or current-state
rollback is authorized here. An older restored snapshot that lacks retained
operation evidence remains a safe halt, requiring explicit reconciliation.
"""
from contextlib import closing
import os
from pathlib import Path
import re
import stat

from src.application.managed_documents import _ManagedDocumentJournal
from src.application.managed_pdf_artifacts import _ManagedPdfArtifactJournal
from src.core.observation_uow import (
    ObservationOperationJournal, ObservationPersistenceUnitOfWork,
    _journal_uses_encrypted_attachments, _encrypted_generation_evidence,
)
from src.core.persistence_events import canonical_payload_hash
from src.security.final_v3_document_runtime import (
    _GENERATION_SELECT, _record_from_row, _document_id, _uuid,
)

_TOKEN = re.compile(r"[0-9a-f]{32}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class RetainedOperationStartupError(RuntimeError):
    """Fixed diagnostic code; no journal content, source paths or secrets."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _fail(code="retained_operation_damaged"):
    raise RetainedOperationStartupError(code)


def _safe(path, *, directory=False, empty=False):
    value = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if (not expected(value.st_mode) or value.st_uid != os.getuid()
            or value.st_mode & 0o077 or not directory and value.st_nlink != 1
            or not value.st_mode & stat.S_IRUSR
            or directory and not value.st_mode & stat.S_IXUSR
            or empty and value.st_size != 0):
        _fail()


def _children(path):
    _safe(path, directory=True)
    return {child.name: child for child in path.iterdir()}


def _complete(state):
    if state["phase"] != "COMPLETE":
        _fail("retained_operation_pending")


def _inspect_plan(plan, document_id, *, action=None):
    """Pure counterpart of the existing document runtime's prepare-plan checks."""
    _document_id(document_id)
    if not isinstance(plan, dict) or set(plan) != {
            "document_id", "document_generation", "storage_id", "previous_active_generation"}:
        _fail()
    generation = plan["document_generation"]
    previous = plan["previous_active_generation"]
    if (plan["document_id"] != document_id
            or not isinstance(generation, int) or isinstance(generation, bool) or generation < 1
            or previous is not None and (not isinstance(previous, int)
                or isinstance(previous, bool) or previous < 1)
            or action == "create" and previous is not None
            or action == "replace" and previous is None):
        _fail()
    _uuid(plan["storage_id"], "retained_operation_damaged")


def inspect_retained_operation_journals(root):
    """Inspect exact retained layouts below one application runtime root.

    Return (kind, parsed_state, journal_path) tuples. Parsers are reused without
    their writers/recovery routines; missing, temporary or unknown payloads halt.
    """
    try:
        return _inspect_data_root(Path(root) / "final-v4-sqlcipher-runtime-v1")
    except RetainedOperationStartupError:
        raise
    except Exception:
        _fail()


def _inspect_data_root(data_root):
    records = []
    observation_root = data_root / ".observation-staging"
    if observation_root.exists() or observation_root.is_symlink():
        for name, operation in _children(observation_root).items():
            if name == ".writer.lock":
                _safe(operation, empty=True)
                continue
            if not _TOKEN.fullmatch(name) or set(_children(operation)) != {"journal.json"}:
                _fail()
            journal = ObservationOperationJournal(operation)
            _safe(journal.path)
            state = journal.read()
            _complete(state)
            if not _journal_uses_encrypted_attachments(state):
                _fail()
            for prefix in ("before", "target"):
                payload = {"observation": state[prefix + "_observation"],
                    "documents": state[prefix + "_documents"]}
                if canonical_payload_hash(payload) != state[prefix + "_state_hash"]:
                    _fail()
            if not _SHA.fullmatch(str(state["operation_payload_hash"])):
                _fail()
            before = {"observation": state["before_observation"], "documents": state["before_documents"]}
            target = {"observation": state["target_observation"], "documents": state["target_documents"]}
            original_hash = canonical_payload_hash({"mode": state["mode"],
                "before": before, "target": target,
                "removed_document_ids": state["removed_document_ids"]})
            prepared_hash = canonical_payload_hash({"prepared_operation_payload_hash": original_hash,
                "new_documents": state["new_documents"]})
            if prepared_hash != state["operation_payload_hash"]:
                _fail()
            for item in state["new_documents"]:
                action = item["write_action"]
                if action not in {"insert", "replace"}:
                    _fail()
                _inspect_plan(item["encrypted_plan"], item["record"]["document_id"],
                    action="create" if action == "insert" else "replace")
            records.append(("observation", state, journal.path))
    managed_root = data_root / ".managed-document-staging"
    if managed_root.exists() or managed_root.is_symlink():
        for name, operation in _children(managed_root).items():
            if name == "pdf-artifacts":
                for token, pdf_operation in _children(operation).items():
                    if not _SHA.fullmatch(token) or set(_children(pdf_operation)) != {"managed-pdf-artifact.json"}:
                        _fail()
                    journal = _ManagedPdfArtifactJournal(pdf_operation)
                    _safe(journal.path)
                    state = journal.read()
                    _complete(state)
                    _inspect_plan(state["plan"], state["document_id"], action="create")
                    records.append(("pdf", state, journal.path))
                continue
            if not _TOKEN.fullmatch(name):
                _fail()
            journal = _ManagedDocumentJournal(operation)
            _safe(journal.path)
            state = journal.read()
            _complete(state)
            if set(_children(operation)) != {"managed-document.json", state["document_id"]}:
                _fail()
            _safe(operation / state["document_id"], empty=True)
            if not _SHA.fullmatch(str(state["payload_hash"])):
                _fail()
            if state["action"] == "remove":
                if state["plan"] is not None:
                    _fail()
            else:
                _inspect_plan(state["plan"], state["document_id"], action=state["action"])
            records.append(("managed", state, journal.path))
    return tuple(records)


def _generation(documents, companion, plan, document_id):
    parsed = documents._require_prepare_plan(plan, document_id=document_id)
    row = companion.execute(_GENERATION_SELECT +
        " WHERE document_id=? AND document_generation=?",
        (parsed.document_id, parsed.document_generation)).fetchone()
    if row is None:
        _fail("retained_operation_unbound")
    record = _record_from_row(row)
    if record.storage_id != parsed.storage_id or record.lifecycle_status not in {"ACTIVE", "RETAINED"}:
        _fail("retained_operation_unbound")
    return record


def verify_retained_operation_journals(opened_runtime):
    """Bind historical terminal claims to keyed immutable persisted evidence.

    Current observations, attachment metadata and active document generations
    may legitimately differ after later operations. Their historical records
    and exact persistence-event sets must still exist; missing history is never
    interpreted as an empty or successful operation.
    """
    try:
        database = opened_runtime.final_v4.database
        records = _inspect_data_root(Path(database.path).parent)
        if not records:
            return
        exposed_documents = opened_runtime.documents
        exposed_documents.validate_restart()
        documents = getattr(exposed_documents, "_documents", exposed_documents)
        uow = ObservationPersistenceUnitOfWork(database, encrypted_attachments=exposed_documents)
        with closing(database._connection_provider.connect_read_only(database.path)) as main, \
                closing(documents._factory.connect_read_only()) as companion:
            for kind, state, _path in records:
                if kind == "observation":
                    expected = tuple((event.operation_index, event.operation_payload_hash,
                        event.event_kind, event.student_id, event.competency_id,
                        event.observation_id, event.technical_timestamp, event.ordering_state)
                        for event in uow._events_for(state))
                    observed = tuple(tuple(row) for row in main.execute(
                        "SELECT operation_index,operation_payload_hash,event_kind,student_id,"
                        "competency_id,observation_id,technical_timestamp,ordering_state "
                        "FROM persistence_events WHERE operation_token=? ORDER BY operation_index",
                        (state["operation_token"],)))
                    if not expected or observed != expected:
                        _fail("retained_operation_unbound")
                    for item in state["new_documents"]:
                        document_id = item["record"]["document_id"]
                        generation = _generation(documents, companion, item["encrypted_plan"], document_id)
                        expected_generation = dict(item["encrypted_generation"])
                        observed_generation = _encrypted_generation_evidence(generation)
                        # The journal records PREPARED evidence. Activation and
                        # later replacement legitimately change only lifecycle.
                        if expected_generation.pop("lifecycle_status", None) != "PREPARED":
                            _fail("retained_operation_unbound")
                        observed_generation.pop("lifecycle_status")
                        if observed_generation != expected_generation:
                            _fail("retained_operation_unbound")
                elif kind == "managed":
                    row = main.execute("SELECT observation_id,active FROM documents WHERE document_id=?",
                        (state["document_id"],)).fetchone()
                    if row is None or row[0]:
                        _fail("retained_operation_unbound")
                    if state["action"] == "remove":
                        pointer = companion.execute("SELECT active_generation FROM final_v3_documents WHERE document_id=?",
                            (state["document_id"],)).fetchone()
                        if state["plan"] is not None or row[1] or pointer is None or pointer[0] is not None:
                            _fail("retained_operation_unbound")
                    else:
                        _generation(documents, companion, state["plan"], state["document_id"])
                else:
                    report = state["artifact_kind"] == "report"
                    table = "learning_report_pdf_artifacts" if report else "learning_conference_pdf_artifacts"
                    prefix = "learning_report" if report else "learning_conference"
                    observed = main.execute(f"SELECT {prefix}_pdf_artifact_id,{prefix}_revision_id,"
                        f"relative_file_path,mime_type,file_size_bytes,snapshot_sha256,pdf_sha256,created_at FROM {table} "
                        f"WHERE {prefix}_revision_id=?", (state["revision_id"],)).fetchone()
                    expected = (state["artifact_id"], state["revision_id"],
                        "managed-document:" + state["document_id"], "application/pdf",
                        state["pdf_size"], state["snapshot_sha256"], state["pdf_sha256"], state["created_at"])
                    if observed is None or tuple(observed) != expected:
                        _fail("retained_operation_unbound")
                    generation = _generation(documents, companion, state["plan"], state["document_id"])
                    if (generation.plaintext_size != state["pdf_size"]
                            or generation.plaintext_sha256 != state["pdf_sha256"]
                            or generation.mime_type != "application/pdf"):
                        _fail("retained_operation_unbound")
    except RetainedOperationStartupError:
        raise
    except Exception:
        _fail()
