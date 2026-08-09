"""Qt-free integration of observation attachments with the cipher runtime."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
import uuid
from unittest import mock

import pytest

from src.core.observation_uow import (
    ObservationOperationJournal,
    ObservationPersistenceUnitOfWork,
    ObservationUnitOfWorkError,
)
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.adapters.master_data_desktop_adapter import MasterDataDesktopAdapter
from src.desktop_app.view_models.observation_view_model import (
    ObservationAttachmentDraft,
    ObservationDraftViewModel,
)
from src.security.final_v3_document_runtime import (
    FinalV3DocumentRuntimeDecisionState,
    FinalV3DocumentRuntimeError,
    run_gated_final_v3_document_runtime,
)
from tests.test_final_v3_document_runtime import (
    _Consumer,
    _loaded,
    _reopen,
    _runtime,
)
from tests.test_final_v3_sqlcipher_runtime import (
    MemoryDataMasterKeyStore,
    _account_loader,
    _environment,
    _root,
    requires_exact_417,
)


def _case() -> object:
    from test_desktop_app_adapter import DesktopAppAdapterTest

    case = DesktopAppAdapterTest("test_observation_can_save_attachment_metadata")
    case.setUp()
    return case


def _private_input(tmp_path: Path) -> Path:
    root = tmp_path / "attachment-input"
    root.mkdir(mode=0o700)
    return root


def _cipher_runtime(tmp_path: Path):
    root = tmp_path / "security"
    root.mkdir(mode=0o700)
    return _runtime(root)


def _adapter(case: object, runtime: object) -> StudentDesktopAdapter:
    return StudentDesktopAdapter(
        database=case.database,
        database_create_allowed=False,
        encrypted_observation_attachments=runtime,
    )


def _attachment(
    source: Path | None,
    title: str,
    *,
    document_id: str = "",
) -> ObservationAttachmentDraft:
    return ObservationAttachmentDraft(
        source_path="" if source is None else str(source),
        title=title,
        document_type="Sonstiges",
        document_id=document_id,
        original_filename="" if source is None else source.name,
    )


def _read(adapter: StudentDesktopAdapter, document_id: str) -> bytes:
    consumer = _Consumer()
    adapter.read_encrypted_observation_attachment(
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


def test_create_multiple_retry_restart_and_controlled_read(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        first = source_root / "Laura Beobachtung deutsch.txt"
        second = source_root / "zweites-secret.bin"
        first_payload = b"fachlicher Klartext Laura Deutsch"
        second_payload = b"zweites geheimes Attachment"
        first.write_bytes(first_payload)
        second.write_bytes(second_payload)
        draft = case._sample_observation_draft(
            attachments=(_attachment(first, "Erster"), _attachment(second, "Zweiter"))
        )

        result = adapter.save_observation(draft)
        retry = adapter.save_observation(draft)
        assert result.success and retry.success

        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            documents = connection.execute(
                """
                SELECT document_id, file_path, original_filename
                FROM documents ORDER BY document_id
                """
            ).fetchall()
        assert [row[0] for row in documents] == ["MED-000001", "MED-000002"]
        assert [row[1] for row in documents] == ["", ""]
        assert _read(adapter, "MED-000001") == first_payload
        assert _read(adapter, "MED-000002") == second_payload

        reopened = _reopen(runtime)
        restarted_adapter = _adapter(case, reopened)
        assert _read(restarted_adapter, "MED-000001") == first_payload
        assert len(_generation_rows(reopened, "MED-000001")) == 1
        assert len(_generation_rows(reopened, "MED-000002")) == 1

        storage_names = {
            item.name
            for item in reopened.paths.storage_root.iterdir()
            if item.suffix == ".jkmedoc"
        }
        assert len(storage_names) == 2
        forbidden = ("Laura", "deutsch", "MED-", "secret", "Beobachtung")
        assert all(not any(text in name for text in forbidden) for name in storage_names)
        managed_bytes = b"".join(
            path.read_bytes()
            for path in reopened.paths.storage_root.glob("*.jkmedoc")
        )
        assert first_payload not in managed_bytes
        assert second_payload not in managed_bytes
        assert not (Path(case.database.path).parent / "documents").exists()
    finally:
        case.tearDown()


def test_edit_keep_add_replace_and_remove_preserve_med_identity(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        first = source_root / "first.txt"
        added = source_root / "added.txt"
        replacement = source_root / "replacement.txt"
        first.write_bytes(b"old active payload")
        added.write_bytes(b"added payload")
        replacement.write_bytes(b"replacement payload")

        created = case._sample_observation_draft(
            attachments=(_attachment(first, "Erster"),)
        )
        assert adapter.save_observation(created).success
        keep = _attachment(None, "Erster", document_id="MED-000001")

        unchanged = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(keep,),
        )
        assert adapter.update_observation(unchanged).success
        assert len(_generation_rows(runtime, "MED-000001")) == 1

        add = replace(
            case._sample_observation_draft(
                observation_id="OBS-000001",
                attachments=(keep, _attachment(added, "Ergaenzt")),
            ),
        )
        assert adapter.update_observation(add).success
        assert _read(adapter, "MED-000001") == b"old active payload"
        assert _read(adapter, "MED-000002") == b"added payload"

        replace_draft = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(
                _attachment(replacement, "Ersetzt", document_id="MED-000001"),
                _attachment(None, "Ergaenzt", document_id="MED-000002"),
            ),
        )
        assert adapter.update_observation(replace_draft).success
        assert _read(adapter, "MED-000001") == b"replacement payload"
        assert [row[2] for row in _generation_rows(runtime, "MED-000001")] == [
            "RETAINED",
            "ACTIVE",
        ]

        remove = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(_attachment(None, "Ergaenzt", document_id="MED-000002"),),
        )
        assert adapter.update_observation(remove).success
        with case.database.connect() as connection:
            assert connection.execute(
                "SELECT active FROM documents WHERE document_id = 'MED-000001'"
            ).fetchone()[0] == 0
        assert [row[2] for row in _generation_rows(runtime, "MED-000001")] == [
            "RETAINED",
            "RETAINED",
        ]
        with pytest.raises(ObservationUnitOfWorkError):
            _read(adapter, "MED-000001")
        assert len(tuple(runtime.paths.storage_root.glob("*.jkmedoc"))) == 3
    finally:
        case.tearDown()


def test_retry_after_prepared_and_after_activation_does_not_duplicate(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        source = source_root / "retry.txt"
        source.write_bytes(b"retry payload")
        draft = case._sample_observation_draft(
            attachments=(_attachment(source, "Retry"),)
        )
        original_advance = ObservationPersistenceUnitOfWork._advance

        def fail_after_prepared(journal, state, phase):
            if phase == "FILES_STAGED":
                raise RuntimeError("crash after PREPARED")
            return original_advance(journal, state, phase)

        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_advance",
            side_effect=fail_after_prepared,
        ):
            assert not adapter.save_observation(draft).success
        assert _generation_rows(runtime, "MED-000001")[0][2] == "PREPARED"
        assert adapter.save_observation(draft).success

        original_advance = ObservationPersistenceUnitOfWork._advance

        def fail_before_complete(journal, state, phase):
            if phase == "COMPLETE":
                raise RuntimeError("crash after activation")
            return original_advance(journal, state, phase)

        second = source_root / "second.txt"
        second.write_bytes(b"second payload")
        update = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(
                _attachment(None, "Retry", document_id="MED-000001"),
                _attachment(second, "Second"),
            ),
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_advance",
            side_effect=fail_before_complete,
        ):
            assert not adapter.update_observation(update).success
        assert _generation_rows(runtime, "MED-000002")[0][2] == "ACTIVE"

        restarted = _adapter(case, _reopen(runtime))
        assert _read(restarted, "MED-000002") == b"second payload"
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
    finally:
        case.tearDown()


@pytest.mark.parametrize(
    "boundary",
    ("before_prepare", "before_db_commit", "after_db_commit", "during_activation"),
)
def test_restart_recovers_bound_uow_crash_boundaries(
    tmp_path: Path,
    boundary: str,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        source = source_root / f"{boundary}.txt"
        source.write_bytes(f"payload-{boundary}".encode())
        draft = case._sample_observation_draft(
            attachments=(_attachment(source, boundary),)
        )

        if boundary == "before_prepare":
            patcher = mock.patch.object(
                runtime,
                "prepare",
                side_effect=RuntimeError("crash before prepare"),
            )
        elif boundary == "before_db_commit":
            patcher = mock.patch.object(
                ObservationPersistenceUnitOfWork,
                "_commit_database",
                side_effect=RuntimeError("crash before DB commit"),
            )
        elif boundary == "during_activation":
            patcher = mock.patch.object(
                runtime,
                "apply_journaled_changes",
                side_effect=RuntimeError("crash during activation"),
            )
        else:
            original_advance = ObservationPersistenceUnitOfWork._advance

            def after_db_commit(journal, state, phase):
                if phase == "DATABASE_COMMITTED":
                    raise RuntimeError("crash after DB commit")
                return original_advance(journal, state, phase)

            patcher = mock.patch.object(
                ObservationPersistenceUnitOfWork,
                "_advance",
                side_effect=after_db_commit,
            )

        with patcher:
            assert not adapter.save_observation(draft).success

        restarted_runtime = _reopen(runtime)
        restarted = _adapter(case, restarted_runtime)
        assert _read(restarted, "MED-000001") == f"payload-{boundary}".encode()
        assert _generation_rows(restarted_runtime, "MED-000001") == [
            (
                1,
                _generation_rows(restarted_runtime, "MED-000001")[0][1],
                "ACTIVE",
            )
        ]
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(DISTINCT operation_token) FROM persistence_events"
            ).fetchone()[0] == 1
    finally:
        case.tearDown()


@pytest.mark.parametrize(
    "boundary",
    ("during_container_write", "after_verification_before_prepared"),
)
def test_uow_container_crash_before_prepared_blocks_fail_closed(
    tmp_path: Path,
    boundary: str,
) -> None:
    case = _case()
    try:
        security_root = tmp_path / "security"
        security_root.mkdir(mode=0o700)

        def fail_at_boundary(observed: str) -> None:
            if observed == boundary:
                raise RuntimeError(f"crash at {boundary}")

        runtime = _runtime(security_root, fault_hook=fail_at_boundary)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        source = source_root / f"{boundary}.txt"
        payload = f"secret-{boundary}".encode()
        source.write_bytes(payload)
        draft = case._sample_observation_draft(
            attachments=(_attachment(source, boundary),)
        )

        assert not adapter.save_observation(draft).success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
        assert _generation_rows(runtime, "MED-000001") == []
        assert not (Path(case.database.path).parent / "documents").exists()
        managed_bytes = b"".join(
            path.read_bytes()
            for path in runtime.paths.storage_root.glob("*.jkmedoc")
        )
        assert payload not in managed_bytes

        restarted = _reopen(runtime)
        with pytest.raises(FinalV3DocumentRuntimeError) as captured:
            restarted.validate_restart()
        assert captured.value.code == "document_storage_inventory_invalid"
    finally:
        case.tearDown()


def test_replace_activation_failure_leaves_old_container_readable(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        old = source_root / "old.txt"
        new = source_root / "new.txt"
        old.write_bytes(b"old remains readable")
        new.write_bytes(b"new replacement")
        assert adapter.save_observation(
            case._sample_observation_draft(attachments=(_attachment(old, "Old"),))
        ).success

        update = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(_attachment(new, "New", document_id="MED-000001"),),
        )
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=FinalV3DocumentRuntimeError(
                "simulated_activation_failure",
                operation=runtime._operation,
            ),
        ):
            assert not adapter.update_observation(update).success
            with pytest.raises(FinalV3DocumentRuntimeError):
                adapter.observation_draft_for_edit("OBS-000001")

        consumer = _Consumer()
        runtime.read(document_id="MED-000001", consumer=consumer)
        assert bytes(consumer.payload) == b"old remains readable"
        assert [row[2] for row in _generation_rows(runtime, "MED-000001")] == [
            "ACTIVE",
            "PREPARED",
        ]
        restarted = _adapter(case, _reopen(runtime))
        assert _read(restarted, "MED-000001") == b"new replacement"
    finally:
        case.tearDown()


def test_corrupt_prepared_replacement_does_not_block_old_active_read(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        old = source_root / "old-active.txt"
        replacement = source_root / "corrupt-prepared.txt"
        old.write_bytes(b"old active survives")
        replacement.write_bytes(b"prepared replacement")
        assert adapter.save_observation(
            case._sample_observation_draft(attachments=(_attachment(old, "Old"),))
        ).success

        update = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(
                _attachment(
                    replacement,
                    "Replacement",
                    document_id="MED-000001",
                ),
            ),
        )
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=FinalV3DocumentRuntimeError(
                "simulated_activation_failure",
                operation=runtime._operation,
            ),
        ):
            assert not adapter.update_observation(update).success

        pending = _generation_rows(runtime, "MED-000001")[1]
        container = runtime.paths.storage_root / f"{pending[1]}.jkmedoc"
        with container.open("r+b") as handle:
            handle.seek(-1, 2)
            handle.write(b"X")

        assert _read(adapter, "MED-000001") == b"old active survives"
        with pytest.raises(FinalV3DocumentRuntimeError):
            adapter.observation_draft_for_edit("OBS-000001")
        with pytest.raises(FinalV3DocumentRuntimeError):
            runtime.validate_restart()
    finally:
        case.tearDown()


def test_multi_replace_pointer_failure_rolls_back_all_activations(
    tmp_path: Path,
) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        old_first = source_root / "old-first.txt"
        old_second = source_root / "old-second.txt"
        new_first = source_root / "new-first.txt"
        new_second = source_root / "new-second.txt"
        old_first.write_bytes(b"old first")
        old_second.write_bytes(b"old second")
        new_first.write_bytes(b"new first")
        new_second.write_bytes(b"new second")
        assert adapter.save_observation(
            case._sample_observation_draft(
                attachments=(
                    _attachment(old_first, "Old first"),
                    _attachment(old_second, "Old second"),
                )
            )
        ).success

        update = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(
                _attachment(new_first, "New first", document_id="MED-000001"),
                _attachment(new_second, "New second", document_id="MED-000002"),
            ),
        )
        pointer_switch_count = 0

        def fail_second_pointer_switch(boundary: str) -> None:
            nonlocal pointer_switch_count
            if boundary != "during_pointer_switch":
                return
            pointer_switch_count += 1
            if pointer_switch_count == 2:
                raise RuntimeError("simulated_second_pointer_switch_failure")

        runtime._fault_hook = fail_second_pointer_switch
        try:
            assert not adapter.update_observation(update).success
        finally:
            runtime._fault_hook = None

        assert [row[2] for row in _generation_rows(runtime, "MED-000001")] == [
            "ACTIVE",
            "PREPARED",
        ]
        assert [row[2] for row in _generation_rows(runtime, "MED-000002")] == [
            "ACTIVE",
            "PREPARED",
        ]

        pending_second = _generation_rows(runtime, "MED-000002")[1]
        container = runtime.paths.storage_root / f"{pending_second[1]}.jkmedoc"
        with container.open("r+b") as handle:
            handle.seek(-1, 2)
            handle.write(b"X")

        assert _read(adapter, "MED-000001") == b"old first"
        assert _read(adapter, "MED-000002") == b"old second"
        with pytest.raises(FinalV3DocumentRuntimeError):
            adapter.observation_draft_for_edit("OBS-000001")
        with pytest.raises(FinalV3DocumentRuntimeError):
            runtime.validate_restart()
    finally:
        case.tearDown()


def test_cipher_journal_never_recovers_through_gate_off_plaintext(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        source = source_root / "must-not-publish-clear.txt"
        source.write_bytes(b"never plaintext fallback")
        draft = case._sample_observation_draft(
            attachments=(_attachment(source, "No fallback"),)
        )
        with mock.patch.object(
            runtime,
            "prepare",
            side_effect=RuntimeError("stop encrypted operation"),
        ):
            assert not adapter.save_observation(draft).success

        with pytest.raises(ObservationUnitOfWorkError):
            StudentDesktopAdapter(
                database=case.database,
                database_create_allowed=False,
            )
        assert not (Path(case.database.path).parent / "documents").exists()
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    finally:
        case.tearDown()


def test_remove_failure_blocks_projection_until_restart_recovery(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source_root = _private_input(tmp_path)
        source = source_root / "remove.txt"
        source.write_bytes(b"remove payload")
        assert adapter.save_observation(
            case._sample_observation_draft(attachments=(_attachment(source, "Remove"),))
        ).success
        remove = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(),
        )
        with mock.patch.object(
            runtime,
            "apply_journaled_changes",
            side_effect=RuntimeError("crash during deactivation"),
        ):
            assert not adapter.update_observation(remove).success
            with pytest.raises(RuntimeError, match="deactivation"):
                adapter.list_documents_for_student("STU-000001")

        restarted = _adapter(case, _reopen(runtime))
        assert restarted.list_documents_for_student("STU-000001") == ()
        assert _generation_rows(runtime, "MED-000001")[0][2] == "RETAINED"
        assert len(tuple(runtime.paths.storage_root.glob("*.jkmedoc"))) == 1
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
        source_root = _private_input(tmp_path)
        source = source_root / "read.txt"
        source.write_bytes(b"reader secret")
        assert adapter.save_observation(
            case._sample_observation_draft(attachments=(_attachment(source, "Read"),))
        ).success
        row = _generation_rows(runtime, "MED-000001")[0]
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
            failing_adapter.read_encrypted_observation_attachment(
                document_id="MED-000001",
                consumer=consumer,
            )
        assert not consumer.finished
    finally:
        case.tearDown()


def test_gate_off_path_still_publishes_plain_attachment(tmp_path: Path) -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "gate-off.txt"
        source.write_bytes(b"normal clear path")
        draft = case._sample_observation_draft(
            attachments=(_attachment(source, "Gate Off"),)
        )
        assert case.adapter.save_observation(draft).success
        with case.database.connect() as connection:
            file_path = connection.execute(
                "SELECT file_path FROM documents WHERE document_id = 'MED-000001'"
            ).fetchone()[0]
        assert Path(file_path).read_bytes() == b"normal clear path"
        with pytest.raises(ObservationUnitOfWorkError):
            ObservationPersistenceUnitOfWork(case.database).read_encrypted_attachment(
                document_id="MED-000001",
                consumer=_Consumer(),
            )
    finally:
        case.tearDown()


def test_legacy_plaintext_journal_remains_recoverable(tmp_path: Path) -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "legacy-journal.txt"
        source.write_bytes(b"legacy journal payload")
        draft = case._sample_observation_draft(
            attachments=(_attachment(source, "Legacy"),)
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            side_effect=RuntimeError("stop before commit"),
        ):
            assert not case.adapter.save_observation(draft).success
        journal = ObservationOperationJournal(
            Path(case.database.path).parent
            / ".observation-staging"
            / draft.operation_token
        )
        state = journal.read()
        legacy_items = state["attachment_intent"]["items"]
        for item in legacy_items:
            item.pop("original_filename")
        state["attachment_intent"] = legacy_items
        journal.write(state)

        assert case.adapter.save_observation(draft).success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    finally:
        case.tearDown()


def test_encrypted_reader_rejects_general_student_document(tmp_path: Path) -> None:
    case = _case()
    try:
        runtime = _cipher_runtime(tmp_path)
        adapter = _adapter(case, runtime)
        source = Path(case.temp_dir.name) / "general-document.txt"
        source.write_bytes(b"general document remains outside cipher attachment path")
        document = adapter.add_student_document(
            student_id="STU-000001",
            source_path=source,
            title="Allgemeines Dokument",
        )
        with pytest.raises(ObservationUnitOfWorkError):
            adapter.read_encrypted_observation_attachment(
                document_id=document.document_id,
                consumer=_Consumer(),
            )
        assert Path(document.file_path).read_bytes().startswith(b"general document")
        assert not tuple(runtime.paths.storage_root.glob("*.jkmedoc"))
    finally:
        case.tearDown()


@requires_exact_417
def test_exact_sqlcipher_observation_attachment_create_restart_and_read(
    tmp_path: Path,
) -> None:
    external_source = tmp_path / "external-input"
    external_source.mkdir(mode=0o700)
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    first = run_gated_final_v3_document_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        document_database_create_allowed=True,
        environ=_environment(root),
        key_store=store,
        source_root=external_source,
    )
    assert first.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert first.runtime is not None

    database = first.runtime.final_v3.database
    with database.connect() as connection:
        with connection:
            SchoolYearTransitionExecutionRepository(
                connection
            ).insert_current_school_year(
                school_year_id="SY-CIPHER-ATTACHMENTS",
                label="2026/27",
                start_date=date(2026, 8, 1),
                end_date=date(2027, 7, 31),
                created_at=datetime(2026, 8, 1, 8, tzinfo=UTC),
            )

    adapter = StudentDesktopAdapter(
        database=database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 9),
        encrypted_observation_attachments=first.runtime.documents,
    )
    master = MasterDataDesktopAdapter(adapter)
    group = master.add_group("Cipher Attachment Stammgruppe")
    course = master.add_course("Cipher Attachment Kurs", year_level=1)
    student = adapter.save_new_student(
        first_name="Ada",
        last_name="Attachment",
        group_id=group.item_id,
        course_id=course.item_id,
    )
    student_id = student.value.student_id
    payload = b"exact SQLCipher observation attachment"
    source = external_source / "attachment.txt"
    source.write_bytes(payload)
    draft = ObservationDraftViewModel(
        student_id=student_id,
        student_name="Ada Attachment",
        date_text="2026-08-09",
        subject_id="deutsch",
        subject_display_name="Deutsch",
        competency_ratings=(),
        context="Cipher Attachment",
        note="Cipher Attachment",
        is_quick_observation=True,
        attachments=(_attachment(source, "Cipher Attachment"),),
    )
    assert adapter.save_observation(draft).success
    assert _read(adapter, "MED-000001") == payload

    restarted = run_gated_final_v3_document_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
        source_root=external_source,
    )
    assert restarted.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert restarted.runtime is not None
    restarted_adapter = StudentDesktopAdapter(
        database=restarted.runtime.final_v3.database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 9),
        encrypted_observation_attachments=restarted.runtime.documents,
    )
    assert _read(restarted_adapter, "MED-000001") == payload
    assert not restarted.runtime.final_v3.database.path.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
    assert not restarted.runtime.documents.paths.database.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
