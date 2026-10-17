"""Real regular V4 startup after retained application writes; no crypto mocks.

Presentation/login automation uses the existing actual-main test ports. This is
source integration evidence, not sealed macOS or human acceptance evidence.
"""
from contextlib import closing
from dataclasses import replace
import gc
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.desktop_app import main as desktop_main
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.observation_view_model import ObservationDraftViewModel
from src.core.observation_uow import ObservationOperationJournal
from src.application.managed_documents import _ManagedDocumentJournal
from tests.test_product_upgrade_startup import product_main_ports
from tests.test_database_key_runtime import MemoryDataMasterKeyStore
from tests.test_installation_startup_ports import snapshot


@pytest.fixture
def regular_case(tmp_path, monkeypatch):
    from src.core.runtime_root_protection import prepare_synthetic_test_root
    root = (tmp_path / "regular-filled-v4").resolve()
    prepare_synthetic_test_root(root)
    store = MemoryDataMasterKeyStore()
    opened = product_main_ports(root, monkeypatch, store)
    assert desktop_main.main() == 0
    runtime = opened[-1]
    assert runtime.first_run
    with closing(runtime.database.connect()) as connection:
        connection.execute("INSERT INTO students VALUES(?,?,?,?,?,?,?,?)", (
            "STD-SYNTHETIC-001", "Synthetisch", "Pruefkind", "", 1,
            "2026-10-16T08:00:00Z", "2026-10-16T08:00:00Z", None))
        connection.execute("INSERT INTO groups VALUES('GRP-SYNTHETIC','Synthetische Gruppe',1,1)")
        connection.execute("INSERT INTO courses VALUES('CRS-SYNTHETIC','Synthetischer Kurs',"
            "'blue','Blau','#4A6FA5',1,1,1)")
        connection.execute("INSERT INTO student_school_year_assignments VALUES(?,?,?,?,?,?,?,?,?,?)", (
            "ASG-SYNTHETIC", "STD-SYNTHETIC-001", "SY-PILOT-2026-27", "GRP-SYNTHETIC",
            "CRS-SYNTHETIC", "enrolled", "2026-08-01", "2027-07-31",
            "2026-10-16T08:00:00Z", "2026-10-16T08:00:00Z"))
        subject = connection.execute("SELECT subject_id,subject_name FROM competencies "
            "WHERE subject_name='Deutsch' LIMIT 1").fetchone()
        connection.commit()
    assert subject is not None
    adapter = StudentDesktopAdapter(database=runtime.database,
        database_create_allowed=False, managed_document_store=runtime.documents)
    source_root = tmp_path / "synthetic-input"
    source_root.mkdir(mode=0o700)
    source = source_root / "synthetische-arbeitsprobe.txt"
    source.write_bytes(b"Ausschliesslich synthetische Arbeitsprobe")
    return SimpleNamespace(root=root, store=store, opened=opened, runtime=runtime,
        adapter=adapter, source=source, subject=tuple(subject), tmp=tmp_path)


def _observation(case, token="a" * 32):
    draft = ObservationDraftViewModel(student_id="STD-SYNTHETIC-001",
        student_name="Synthetisch Pruefkind", date_text="2026-10-16",
        competency_ratings=(), context="Sitzkreis", note="Synthetische Beobachtung",
        subject_id=case.subject[0], subject_display_name=case.subject[1],
        is_quick_observation=True, operation_token=token)
    result = case.adapter.save_observation(draft)
    assert result.success, result
    return result


def _document(case, token="b" * 32):
    return case.adapter.add_student_document(student_id="STD-SYNTHETIC-001",
        source_path=case.source, title="Synthetische Arbeitsprobe", operation_token=token)


def _journals(case):
    parent = Path(case.runtime.database.path).parent
    return (parent / ".observation-staging" / ("a" * 32) / "journal.json",
        parent / ".managed-document-staging" / ("b" * 32) / "managed-document.json")


def _counts(case):
    with closing(case.runtime.database.connect()) as connection:
        return tuple(connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            for table in ("students", "observations", "documents", "persistence_events"))


def _restart(case):
    before_keys, creates = dict(case.store.values), case.store.create_calls
    gc.collect()
    assert desktop_main.main() == 0
    assert not case.opened[-1].first_run
    assert case.store.values == before_keys and case.store.create_calls == creates


@pytest.mark.parametrize("writes", ["fresh", "observation", "document", "both", "repeat"])
def test_regular_filled_v4_reopens_after_real_saves(regular_case, writes):
    case = regular_case
    if writes in {"observation", "both", "repeat"}:
        _observation(case)
    if writes in {"document", "both", "repeat"}:
        _document(case)
    if writes == "repeat":
        _observation(case)  # Exact retries retain their original operation.
        _document(case)
        _observation(case, "c" * 32)
        _document(case, "d" * 32)
    before = _counts(case)
    _restart(case)
    assert _counts(case) == before
    if writes != "fresh":
        assert any(json.loads(path.read_text())["phase"] == "COMPLETE"
            for path in _journals(case) if path.exists())


def _without_lock(root):
    return {name: value for name, value in snapshot(root).items() if name != "instance.lock"}


@pytest.mark.parametrize("damage", ["open_observation", "open_document", "bad_digest",
    "bad_schema", "unknown_journal", "foreign_sibling", "token", "path", "symlink",
    "unsafe_rights", "missing_main", "missing_dmk", "upgrade", "replay", "upgrade_restore"])
def test_uncertain_retained_operations_fail_closed_before_application_writes(regular_case, damage):
    case = regular_case
    _observation(case)
    _document(case)
    observation, document = _journals(case)
    if damage == "open_observation":
        journal = ObservationOperationJournal(observation.parent)
        state = journal.read(); state.update(phase="PREPARED", revision=1); journal.write(state)
    elif damage == "open_document":
        journal = _ManagedDocumentJournal(document.parent)
        state = journal.read(); state["phase"] = "INTENT"; journal.write(state)
    elif damage in {"bad_digest", "bad_schema"}:
        state = json.loads(observation.read_text())
        state["journal_digest" if damage == "bad_digest" else "journal_version"] = "invalid"
        observation.write_text(json.dumps(state)); observation.chmod(0o600)
    elif damage == "unknown_journal":
        state = json.loads(observation.read_text()); state["foreign_field"] = True
        observation.write_text(json.dumps(state)); observation.chmod(0o600)
    elif damage == "foreign_sibling":
        sibling = observation.parent.parent / "unbekannter-fremdbestand"
        sibling.mkdir(mode=0o700); (sibling / "unknown").write_bytes(b"unknown")
        (sibling / "unknown").chmod(0o600)
    elif damage == "token":
        journal = ObservationOperationJournal(observation.parent)
        state = journal.read(); state["operation_token"] = "f" * 32; journal.write(state)
    elif damage == "path":
        journal = _ManagedDocumentJournal(document.parent)
        state = journal.read(); state["plan"]["storage_id"] = "../../foreign"; journal.write(state)
    elif damage == "symlink":
        preserved = case.tmp / "original-journal.json"; observation.rename(preserved)
        observation.symlink_to(preserved)
    elif damage == "unsafe_rights":
        document.chmod(0o644)
    elif damage == "missing_main":
        Path(case.runtime.database.path).unlink()
    elif damage == "missing_dmk":
        case.store.values.clear()
    else:
        for name in ({"upgrade": ("schema-upgrade-foundation",),
                "replay": ("schema-upgrade-replay",),
                "upgrade_restore": ("schema-upgrade-foundation", "restore-transactions")})[damage]:
            (case.root / name).mkdir(mode=0o700)
    gc.collect()
    before, keys, creates = _without_lock(case.root), dict(case.store.values), case.store.create_calls
    old_runtime_count = len(case.opened)
    assert desktop_main.main() != 0
    assert len(case.opened) == old_runtime_count, "Unclear installation reached authenticated app runtime"
    after = _without_lock(case.root)
    if damage == "missing_dmk":
        # Ordinary authentication has its separate security-store lifecycle.
        # A failed existing-key read must preserve every encrypted data and
        # operation artifact, and must never create or replace key material.
        protected = lambda values: {name: value for name, value in values.items()
            if name.startswith("final-v4-sqlcipher-runtime-v1")
            or name.endswith("database-key-envelopes-v1.json")}
        assert protected(after) == protected(before)
    else:
        assert after == before
    assert case.store.values == keys and case.store.create_calls == creates


def test_complete_retained_journals_are_read_only_preflight_evidence(regular_case):
    from src.application.retained_operation_startup import inspect_retained_operation_journals
    case = regular_case
    _observation(case); _document(case)
    before = snapshot(case.root)
    inspect_retained_operation_journals(case.root)
    assert snapshot(case.root) == before


def test_existing_retained_journals_never_become_first_run(regular_case):
    case = regular_case
    _observation(case); _document(case)
    for _ in range(2):
        _restart(case)
    assert all(not runtime.first_run for runtime in case.opened[1:])


def test_terminal_observation_history_allows_a_real_later_update(regular_case):
    case = regular_case
    created = _observation(case).value
    draft = case.adapter.observation_draft_for_edit(created.observation_id)
    assert draft is not None
    updated = case.adapter.update_observation(replace(draft,
        note="Spaeter bewusst geaenderte synthetische Beobachtung", operation_token="9" * 32))
    assert updated.success, updated
    assert updated.value.observation_id == created.observation_id
    historical = ObservationOperationJournal(_journals(case)[0].parent).read()
    assert historical["target_observation"]["note"] == "Synthetische Beobachtung"
    _restart(case)
    with closing(case.opened[-1].database.connect()) as connection:
        rows = connection.execute("SELECT observation_id,note FROM observations").fetchall()
        assert [tuple(row) for row in rows] == [(created.observation_id,
            "Spaeter bewusst geaenderte synthetische Beobachtung")]


def test_rehashed_forged_observation_payload_halts_before_authentication(regular_case):
    from src.core.persistence_events import canonical_payload_hash
    from src.application.retained_operation_startup import (
        inspect_retained_operation_journals, RetainedOperationStartupError)
    case = regular_case
    _observation(case)
    journal = ObservationOperationJournal(_journals(case)[0].parent)
    state = journal.read()
    original_operation_hash = state["operation_payload_hash"]
    state["target_observation"]["note"] = "Manipulierter synthetischer Journalinhalt"
    state["target_state_hash"] = canonical_payload_hash({
        "observation": state["target_observation"], "documents": state["target_documents"]})
    journal.write(state)  # Recompute envelope digest, leaving original intent hash.
    assert journal.read()["operation_payload_hash"] == original_operation_hash
    before = _without_lock(case.root)
    with pytest.raises(RetainedOperationStartupError):
        inspect_retained_operation_journals(case.root)
    assert _without_lock(case.root) == before
    runtime_count, creates = len(case.opened), case.store.create_calls
    assert desktop_main.main() != 0
    assert len(case.opened) == runtime_count and case.store.create_calls == creates
    assert _without_lock(case.root) == before


@pytest.mark.parametrize("binding", ["missing_event", "changed_event", "foreign_generation"])
def test_syntactically_complete_claim_needs_real_keyed_persistence_binding(regular_case, binding):
    from uuid import uuid4
    from src.application.retained_operation_startup import inspect_retained_operation_journals
    case = regular_case
    _observation(case); _document(case)
    if binding == "foreign_generation":
        journal = _ManagedDocumentJournal(_journals(case)[1].parent)
        state = journal.read(); state["plan"]["storage_id"] = str(uuid4()); journal.write(state)
    else:
        with closing(case.runtime.database.connect()) as connection:
            if binding == "missing_event":
                connection.execute("DELETE FROM persistence_events WHERE operation_token=?", ("a" * 32,))
            else:
                connection.execute("UPDATE persistence_events SET operation_payload_hash=? WHERE operation_token=?",
                    ("e" * 64, "a" * 32))
            connection.commit()
    # Morphology and digests alone cannot admit a terminal operation.
    inspected = inspect_retained_operation_journals(case.root)
    assert len(inspected) == 2
    before = _without_lock(case.root)
    keys, creates = dict(case.store.values), case.store.create_calls
    runtime_count = len(case.opened)
    assert desktop_main.main() != 0
    assert len(case.opened) == runtime_count
    after = _without_lock(case.root)
    for name, value in before.items():
        if name.startswith("final-v4-sqlcipher-runtime-v1"):
            assert after[name] == value
    assert case.store.values == keys and case.store.create_calls == creates


@pytest.mark.parametrize("lifecycle", ["observation_and_document", "reopen", "restore", "restore_crash"])
def test_retained_real_operations_in_synthetic_v6_runtime(regular_case, monkeypatch, lifecycle):
    from src.core import macos_test_package_profile as profile_module
    from src.desktop_app.runtime import runtime_paths
    from src.security import final_v4_backup_runtime as v4_backups
    from src.security import internal_test_v6_composition as composition
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    from tests.test_synthetic_v6_backup_restore import _migrate_fixture, _service, _prepare, _run_restore
    from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider
    from src.security.synthetic_v6_runtime import SyntheticV6Runtime
    from src.core.restore_runtime import RuntimeInstanceLock
    from src.security.startup import build_security_runtime, finalize_security_runtime
    case = regular_case
    _observation(case); _document(case)
    account = ExistingStartupAccountRepository(case.root / "security/security.sqlite", None).load_bound_active_account()
    old = v4_backups.build_final_v4_encrypted_backup_service(opened_runtime=case.runtime.runtime,
        account_loader=lambda: account, environ={}, product_paths=runtime_paths(case.root))
    # The fixture's maintenance-service builder lives in this process. Complete
    # its normal successful metadata lifecycle before simulating process exit;
    # never weaken the existing-only loader's rejection of metadata sidecars.
    with RuntimeInstanceLock(case.root) as lock:
        finalize_security_runtime(build_security_runtime(runtime_paths(case.root)),
            runtime_paths(case.root), lock)
    gc.collect()
    _migrate_fixture(old)
    service = _service(old.paths, old.loaded, old.installation_id)
    with SyntheticV6Runtime(service).open_existing() as opened:
        case.adapter = StudentDesktopAdapter(database=opened.database,
            database_create_allowed=False, managed_document_store=opened.documents)
        _observation(case, "e" * 32); _document(case, "f" * 32)
        opened.lesson_time_templates.set_times(1, "07:45", "08:30")
    if lifecycle in {"restore", "restore_crash"}:
        prep, _, _ = _prepare(service, case.tmp,
            before_handoff=lambda lock: finalize_security_runtime(
                build_security_runtime(runtime_paths(case.root)), runtime_paths(case.root), lock))
        _run_restore(service, prep,
            crash="between_main_and_companion" if lifecycle == "restore_crash" else None)
    # As in the real application's successful V6 shutdown, complete metadata
    # reads performed by the explicitly opened fixture session/worker verifier.
    if lifecycle != "restore_crash":
        with RuntimeInstanceLock(case.root) as lock:
            finalize_security_runtime(build_security_runtime(runtime_paths(case.root)),
                runtime_paths(case.root), lock)
    # Source capability substitution only: all real schema/key/document/journal
    # checks remain active. No native attestation is claimed by this test.
    profile = SimpleNamespace(runtime_root=str(case.root), installation_id=account.installation_id,
        bundle_id="de.jenaplan.synthetic.retained-tests", account_prefix="synthetic-retained")
    monkeypatch.setattr(profile_module, "test_identity", lambda: profile)
    monkeypatch.setattr(composition, "require_internal_test_v6_context", lambda root: profile)
    real_builder = composition.build_internal_test_v6_backup_service
    def existing_test_keys(root, **kwargs):
        return real_builder(root, **kwargs, key_store=case.store,
            provider=qualified_sqlcipher_test_provider())
    monkeypatch.setattr(composition, "build_internal_test_v6_backup_service", existing_test_keys)
    from src.security import final_v4_live_restore
    monkeypatch.setattr(final_v4_live_restore, "build_platform_data_master_key_store", lambda: case.store)
    keys, creates = dict(case.store.values), case.store.create_calls
    for _ in range(2 if lifecycle in {"reopen", "restore_crash"} else 1):
        assert desktop_main.main() == 0
    assert case.store.values == keys and case.store.create_calls == creates
    reopened = _service(old.paths, old.loaded, old.installation_id)
    with SyntheticV6Runtime(reopened).open_existing() as opened:
        with closing(opened.database.connect()) as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert opened.lesson_time_templates.suggest(1).start_time == (
            "07:50" if lifecycle == "restore_crash" else "07:45")
