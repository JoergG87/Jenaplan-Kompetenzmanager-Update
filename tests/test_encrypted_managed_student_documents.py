"""Qt-free integration of general student documents with the cipher runtime."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
import uuid
from unittest import mock

import pytest

from src.application.managed_documents import ManagedDocumentOperationError
from src.core.managed_document_store import ManagedDocumentStore
from src.core.observation_uow import EncryptedObservationAttachmentRuntime
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
)
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.observation_view_model import (
    ObservationAttachmentDraft,
)
from src.security.final_v3_document_runtime import (
    FinalV3DocumentRuntimeDecisionState,
    FinalV3DocumentRuntimeError,
    run_gated_final_v4_document_runtime,
)
from tests.test_final_v3_document_runtime import _Consumer, _loaded, _reopen, _runtime
from tests.test_final_v4_sqlcipher_runtime import (
    MemoryDataMasterKeyStore,
    _account_loader,
    _environment,
    _root,
    requires_exact_417,
)


STUDENT_ID = "STU-000001"


def _case() -> object:
    from test_desktop_app_adapter import DesktopAppAdapterTest

    case = DesktopAppAdapterTest("test_student_document_is_copied_and_metadata_survives_reload")
    case.setUp()
    return case


def _cipher_runtime(tmp_path: Path):
    root = tmp_path / "security"
    root.mkdir(mode=0o700)
    return _runtime(root)


def _adapter(case: object, runtime: object) -> StudentDesktopAdapter:
    return StudentDesktopAdapter(
        database=case.database,
        database_create_allowed=False,
        managed_document_store=runtime,
    )


def _source_root(tmp_path: Path) -> Path:
    root = tmp_path / "managed-input"
    root.mkdir(mode=0o700)
    return root


def _read(adapter: StudentDesktopAdapter, document_id: str) -> bytes:
    consumer = _Consumer()
    adapter.read_managed_student_document(
        document_id=document_id,
        consumer=consumer,
    )
    assert consumer.started and consumer.finished and consumer.aborted is None
    return bytes(consumer.payload)


def _generation_rows(runtime: object, document_id: str) -> list[tuple[object, ...]]:
    with sqlite3.connect(runtime.paths.database) as connection:
        return connection.execute(
            """
            SELECT document_generation, storage_id, lifecycle_status
            FROM final_v3_document_generations
            WHERE document_id = ? ORDER BY document_generation
            """,
            (document_id,),
        ).fetchall()


def test_create_multiple_retry_restart_and_storage_confidentiality(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        sources = _source_root(tmp_path)
        first = sources / "Laura Lernstand vertraulich.txt"
        second = sources / "zweites-geheimnis.bin"
        first_payload = b"allgemeines verwaltetes Dokument eins"
        second_payload = b"allgemeines verwaltetes Dokument zwei"
        first.write_bytes(first_payload)
        second.write_bytes(second_payload)

        one = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=first,
            document_type="Arbeitsprobe",
            title="Lernstand",
            operation_token="1" * 32,
        )
        retry = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=first,
            document_type="Arbeitsprobe",
            title="Lernstand",
            operation_token="1" * 32,
        )
        two = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=second,
            operation_token="2" * 32,
        )

        assert one.document_id == retry.document_id == "MED-000001"
        assert two.document_id == "MED-000002"
        assert one.file_path == two.file_path == ""
        with case.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, file_path, original_filename, active
                FROM documents ORDER BY document_id
                """
            ).fetchall()
        assert [tuple(row) for row in rows] == [
            ("MED-000001", "", first.name, 1),
            ("MED-000002", "", second.name, 1),
        ]

        restarted = _adapter(case, _reopen(runtime))
        assert _read(restarted, one.document_id) == first_payload
        assert _read(restarted, two.document_id) == second_payload
        assert len(_generation_rows(runtime, one.document_id)) == 1
        assert len(_generation_rows(runtime, two.document_id)) == 1

        containers = tuple(runtime.paths.storage_root.glob("*.jkmedoc"))
        assert len(containers) == 2
        assert all(path.suffix == ".jkmedoc" for path in containers)
        assert all("MED-" not in path.name for path in containers)
        assert all(
            first.name not in path.name and second.name not in path.name
            for path in containers
        )
        managed_bytes = b"".join(path.read_bytes() for path in containers)
        assert first_payload not in managed_bytes
        assert second_payload not in managed_bytes
        assert not (Path(case.database.path).parent / "documents").exists()
    finally:
        case.tearDown()


def test_replace_keeps_med_changes_storage_and_remove_retains_containers(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        sources = _source_root(tmp_path)
        old = sources / "old.txt"
        new = sources / "new.txt"
        old.write_bytes(b"old managed payload")
        new.write_bytes(b"new managed payload")
        created = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=old,
            title="Arbeitsstand",
        )
        first_row = _generation_rows(runtime, created.document_id)[0]

        replaced = adapter.replace_student_document(
            document_id=created.document_id,
            source_path=new,
        )
        rows = _generation_rows(runtime, created.document_id)
        assert replaced.document_id == created.document_id == "MED-000001"
        assert rows[0][1] != rows[1][1]
        assert [row[2] for row in rows] == ["RETAINED", "ACTIVE"]
        assert first_row[1] == rows[0][1]
        assert _read(adapter, created.document_id) == b"new managed payload"

        adapter.remove_document(created.document_id)
        assert adapter.list_documents_for_student(STUDENT_ID) == ()
        assert [row[2] for row in _generation_rows(runtime, created.document_id)] == [
            "RETAINED",
            "RETAINED",
        ]
        assert len(tuple(runtime.paths.storage_root.glob("*.jkmedoc"))) == 2
        with pytest.raises(ManagedDocumentOperationError):
            _read(adapter, created.document_id)
    finally:
        case.tearDown()


def test_create_retry_after_activation_failure_does_not_duplicate(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "retry.txt"
        source.write_bytes(b"retry payload")
        token = "a" * 32
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=RuntimeError("simulated activation failure"),
        ):
            with pytest.raises(ManagedDocumentOperationError) as captured:
                adapter.add_student_document(
                    student_id=STUDENT_ID,
                    source_path=source,
                    operation_token=token,
                )
            assert captured.value.operation_token == token
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0

        restarted = _adapter(case, _reopen(runtime))
        created = restarted.add_student_document(
            student_id=STUDENT_ID,
            source_path=source,
            operation_token=token,
        )

        assert created.document_id == "MED-000001"
        assert _read(restarted, created.document_id) == b"retry payload"
        assert _generation_rows(runtime, created.document_id)[0][2] == "ACTIVE"
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    finally:
        case.tearDown()


def test_replace_failure_leaves_old_document_readable_and_retryable(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        sources = _source_root(tmp_path)
        old = sources / "old-active.txt"
        new = sources / "new-prepared.txt"
        old.write_bytes(b"old remains active")
        new.write_bytes(b"new after retry")
        document = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=old,
        )
        token = "b" * 32
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=RuntimeError("simulated replace activation failure"),
        ):
            with pytest.raises(ManagedDocumentOperationError):
                adapter.replace_student_document(
                    document_id=document.document_id,
                    source_path=new,
                    operation_token=token,
                )
        restarted = _adapter(case, _reopen(runtime))
        assert _read(restarted, document.document_id) == b"old remains active"
        replaced = restarted.replace_student_document(
            document_id=document.document_id,
            source_path=new,
            operation_token=token,
        )

        assert replaced.document_id == document.document_id
        assert _read(restarted, document.document_id) == b"new after retry"
        assert [row[2] for row in _generation_rows(runtime, document.document_id)] == [
            "RETAINED",
            "ACTIVE",
        ]
    finally:
        case.tearDown()


def test_retry_rejects_changed_source_bytes(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "bound-source.txt"
        source.write_bytes(b"first source bytes")
        token = "c" * 32
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=RuntimeError("keep prepared"),
        ):
            with pytest.raises(ManagedDocumentOperationError):
                adapter.add_student_document(
                    student_id=STUDENT_ID,
                    source_path=source,
                    operation_token=token,
                )
        source.write_bytes(b"changed source bytes")
        with pytest.raises(ManagedDocumentOperationError) as captured:
            adapter.add_student_document(
                student_id=STUDENT_ID,
                source_path=source,
                operation_token=token,
            )
        assert captured.value.code == "managed_document_retry_conflict"
        assert _generation_rows(runtime, "MED-000001")[0][2] == "PREPARED"
    finally:
        case.tearDown()


def test_replace_restart_recovers_crash_after_pointer_commit(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        sources = _source_root(tmp_path)
        old = sources / "before-crash.txt"
        new = sources / "after-crash.txt"
        old.write_bytes(b"before crash")
        new.write_bytes(b"after crash")
        document = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=old,
        )
        original_apply = runtime.apply_journaled_changes

        def crash_after_commit(**kwargs):
            original_apply(**kwargs)
            raise SystemExit("simulated abrupt boundary")

        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=crash_after_commit,
        ):
            with pytest.raises(SystemExit):
                adapter.replace_student_document(
                    document_id=document.document_id,
                    source_path=new,
                    operation_token="d" * 32,
                )

        restarted = _adapter(case, _reopen(runtime))
        restarted.replace_student_document(
            document_id=document.document_id,
            source_path=new,
            operation_token="d" * 32,
        )
        assert _read(restarted, document.document_id) == b"after crash"
        assert [row[2] for row in _generation_rows(runtime, document.document_id)] == [
            "RETAINED",
            "ACTIVE",
        ]
    finally:
        case.tearDown()


def test_remove_pointer_failure_recovers_after_restart(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "remove-retry.txt"
        source.write_bytes(b"remove retry")
        document = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=source,
        )
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=RuntimeError("remove pointer failure"),
        ):
            with pytest.raises(ManagedDocumentOperationError):
                adapter.remove_document(document.document_id, "e" * 32)
        assert adapter.list_documents_for_student(STUDENT_ID) == ()
        restarted = _adapter(case, _reopen(runtime))
        assert restarted.list_documents_for_student(STUDENT_ID) == ()
        assert _generation_rows(runtime, document.document_id)[0][2] == "RETAINED"
    finally:
        case.tearDown()


def test_create_restart_recovers_crash_after_reference_commit(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "create-reference-crash.txt"
        source.write_bytes(b"create reference crash")
        repository = adapter._managed_documents._repository
        original_create = repository.create_document

        def crash_after_reference(record):
            original_create(record)
            raise SystemExit("crash after reference commit")

        with mock.patch.object(
            repository,
            "create_document",
            side_effect=crash_after_reference,
        ):
            with pytest.raises(SystemExit):
                adapter.add_student_document(
                    student_id=STUDENT_ID,
                    source_path=source,
                    operation_token="0" * 32,
                )
        restarted = _adapter(case, _reopen(runtime))
        documents = restarted.list_documents_for_student(STUDENT_ID)
        assert [item.document_id for item in documents] == ["MED-000001"]
        assert _read(restarted, "MED-000001") == b"create reference crash"
    finally:
        case.tearDown()


def test_remove_restart_recovers_crash_after_reference_deactivation(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "remove-reference-crash.txt"
        source.write_bytes(b"remove reference crash")
        document = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=source,
        )
        repository = adapter._managed_documents._repository
        original_deactivate = repository.deactivate_general_document

        def crash_after_deactivation(document_id):
            original_deactivate(document_id)
            raise SystemExit("crash after reference deactivation")

        with mock.patch.object(
            repository,
            "deactivate_general_document",
            side_effect=crash_after_deactivation,
        ):
            with pytest.raises(SystemExit):
                adapter.remove_document(document.document_id, "9" * 32)
        restarted = _adapter(case, _reopen(runtime))
        assert restarted.list_documents_for_student(STUDENT_ID) == ()
        assert _generation_rows(runtime, document.document_id)[0][2] == "RETAINED"
    finally:
        case.tearDown()


def test_journal_root_symlink_is_rejected_without_redirected_write(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "symlink.txt"
        source.write_bytes(b"symlink guard")
        redirected = tmp_path / "redirected"
        redirected.mkdir(mode=0o700)
        journal_root = Path(case.database.path).parent / ".managed-document-staging"
        journal_root.symlink_to(redirected, target_is_directory=True)
        with pytest.raises(ManagedDocumentOperationError):
            adapter.add_student_document(
                student_id=STUDENT_ID,
                source_path=source,
            )
        assert tuple(redirected.iterdir()) == ()
    finally:
        case.tearDown()


def test_general_and_observation_writers_share_med_reservations(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        sources = _source_root(tmp_path)
        general = sources / "pending-general.txt"
        attachment = sources / "observation-attachment.txt"
        general.write_bytes(b"pending general")
        attachment.write_bytes(b"observation attachment")
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=RuntimeError("leave MED reservation pending"),
        ):
            with pytest.raises(ManagedDocumentOperationError):
                adapter.add_student_document(
                    student_id=STUDENT_ID,
                    source_path=general,
                    operation_token="f" * 32,
                )
        draft = case._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(
                    source_path=str(attachment),
                    title="Beobachtungsanhang",
                    document_type="Sonstiges",
                    original_filename=attachment.name,
                ),
            )
        )
        assert adapter.save_observation(draft).success
        with case.database.connect() as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT document_id FROM documents ORDER BY document_id"
                ).fetchall()
            ]
        assert ids == ["MED-000002"]
        assert _generation_rows(runtime, "MED-000001")[0][2] == "PREPARED"
        assert _generation_rows(runtime, "MED-000002")[0][2] == "ACTIVE"
    finally:
        case.tearDown()


@pytest.mark.parametrize("failure", ["tamper", "missing", "wrong_dmk", "wrong_context"])
def test_controlled_reader_fails_closed_for_invalid_container_or_context(
    tmp_path: Path,
    failure: str,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = _source_root(tmp_path) / "reader.txt"
        source.write_bytes(b"managed reader secret")
        document = adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=source,
        )
        row = _generation_rows(runtime, document.document_id)[0]
        container = runtime.paths.storage_root / f"{row[1]}.jkmedoc"
        failing_runtime = runtime
        if failure == "tamper":
            with container.open("r+b") as handle:
                handle.seek(-1, 2)
                handle.write(b"X")
        elif failure == "missing":
            container.unlink()
        elif failure == "wrong_dmk":
            failing_runtime = _reopen(runtime, loaded=_loaded(b"\x99" * 32))
        else:
            failing_runtime = _reopen(
                runtime,
                installation_id="99999999-9999-4999-8999-999999999999",
            )
        failing_adapter = _adapter(case, failing_runtime)
        consumer = _Consumer()
        with pytest.raises(FinalV3DocumentRuntimeError):
            failing_adapter.read_managed_student_document(
                document_id=document.document_id,
                consumer=consumer,
            )
        assert not consumer.finished
    finally:
        case.tearDown()


def test_shared_store_contract_and_gate_off_plaintext_path_are_unchanged(
    tmp_path: Path,
) -> None:
    assert EncryptedObservationAttachmentRuntime is ManagedDocumentStore
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "gate-off.txt"
        source.write_bytes(b"existing gate-off plaintext")
        document = case.adapter.add_student_document(
            student_id=STUDENT_ID,
            source_path=source,
        )
        assert Path(document.file_path).read_bytes() == b"existing gate-off plaintext"
        assert "documents" in Path(document.file_path).parts
        with pytest.raises(RuntimeError, match="not active"):
            case.adapter.read_managed_student_document(
                document_id=document.document_id,
                consumer=_Consumer(),
            )
    finally:
        case.tearDown()


@requires_exact_417
def test_exact_sqlcipher_managed_document_create_restart_and_read(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "external-input"
    source_root.mkdir(mode=0o700)
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    first = run_gated_final_v4_document_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        document_database_create_allowed=True,
        environ=_environment(root),
        key_store=store,
        source_root=source_root,
    )
    assert first.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert first.runtime is not None
    database = first.runtime.final_v4.database
    with database.connect() as connection:
        with connection:
            SchoolYearTransitionExecutionRepository(connection).insert_current_school_year(
                school_year_id="SY-CIPHER-MANAGED-DOCUMENTS",
                label="2026/27",
                start_date=date(2026, 8, 1),
                end_date=date(2027, 7, 31),
                created_at=datetime(2026, 8, 1, 8, tzinfo=UTC),
            )
    adapter = StudentDesktopAdapter(
        database=database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 9),
        managed_document_store=first.runtime.documents,
    )
    master = MasterDataDesktopAdapter(adapter)
    group = master.add_group("Cipher Dokument Stammgruppe")
    course = master.add_course("Cipher Dokument Kurs", year_level=1)
    student = adapter.save_new_student(
        first_name="Ada",
        last_name="Dokument",
        group_id=group.item_id,
        course_id=course.item_id,
    )
    payload = b"exact SQLCipher managed student document"
    source = source_root / "managed.txt"
    source.write_bytes(payload)
    document = adapter.add_student_document(
        student_id=student.value.student_id,
        source_path=source,
    )

    restarted = run_gated_final_v4_document_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
        source_root=source_root,
    )
    assert restarted.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert restarted.runtime is not None
    restarted_adapter = StudentDesktopAdapter(
        database=restarted.runtime.final_v4.database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 9),
        managed_document_store=restarted.runtime.documents,
    )
    assert _read(restarted_adapter, document.document_id) == payload
    assert not restarted.runtime.final_v4.database.path.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
    assert not restarted.runtime.documents.paths.database.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
