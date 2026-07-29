"""Fault, retry, and no-clobber tests for observation attachment persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import threading
import time
from unittest import mock

import pytest

from src.core.backup import BackupService
from src.core.observation_uow import (
    ObservationOperationJournal,
    ObservationOperationConflict,
    ObservationPersistenceUnitOfWork,
    ObservationUnitOfWorkError,
    ObservationWriterLock,
)
from src.core.persistence_events import SQLitePersistenceEventRepository
from src.core.restore import RestoreStagingService
from src.core.sqlite_store import SQLiteDocumentRepository
from src.desktop_app.view_models.observation_view_model import ObservationAttachmentDraft

def _case() -> object:
    from test_desktop_app_adapter import DesktopAppAdapterTest

    case = DesktopAppAdapterTest("test_observation_can_save_attachment_metadata")
    case.setUp()
    return case


def _backup(case: object, target_name: str) -> Path:
    root = Path(case.temp_dir.name)
    target = root / target_name
    target.mkdir()
    return BackupService(
        database_path=case.database.path,
        data_root=root,
        documents_root=root / "documents",
        target_directory=target,
        app_version="0.3.0",
        build_commit="1234567",
        source_tree_state="clean",
        now=lambda: datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
    ).create_backup().path


def test_retry_reuses_same_operation_without_duplicate_observation_or_document() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "retry.txt"
        source.write_text("retry", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(
                    str(source),
                    "Retry",
                    "Sonstiges",
                    original_filename=source.name,
                ),
            )
        )
        first = case.adapter.save_observation(draft)
        second = case.adapter.save_observation(draft)
        assert first.success and second.success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(DISTINCT operation_token) FROM persistence_events"
            ).fetchone()[0] == 1
    finally:
        case.tearDown()


def test_multiple_new_attachments_receive_distinct_reserved_ids() -> None:
    case = _case()
    try:
        first = Path(case.temp_dir.name) / "multi-first.txt"
        second = Path(case.temp_dir.name) / "multi-second.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(str(first), "First"),
                ObservationAttachmentDraft(str(second), "Second"),
            )
        )
        assert case.adapter.save_observation(draft).success
        documents = SQLiteDocumentRepository(
            case.database
        ).list_documents_for_observation("OBS-000001")
        assert {document.document_id for document in documents} == {
            "MED-000001",
            "MED-000002",
        }
    finally:
        case.tearDown()


def test_missing_source_keeps_database_unchanged() -> None:
    case = _case()
    try:
        missing = Path(case.temp_dir.name) / "missing.txt"
        draft = case._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(
                    str(missing),
                    "Fehlt",
                    "Sonstiges",
                ),
            )
        )
        result = case.adapter.save_observation(draft)
        assert not result.success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    finally:
        case.tearDown()


def test_update_failure_preserves_old_attachment() -> None:
    case = _case()
    try:
        old = Path(case.temp_dir.name) / "old.txt"
        new = Path(case.temp_dir.name) / "new.txt"
        old.write_text("old", encoding="utf-8")
        new.write_text("new", encoding="utf-8")
        created = case._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(str(old), "Alt", "Sonstiges"),
            )
        )
        assert case.adapter.save_observation(created).success
        update = case._sample_observation_draft(
            observation_id="OBS-000001",
            attachments=(
                ObservationAttachmentDraft(str(new), "Neu", "Sonstiges"),
            ),
        )
        with mock.patch.object(
            SQLitePersistenceEventRepository,
            "append",
            side_effect=RuntimeError("simulierter DB-Abbruch"),
        ):
            result = case.adapter.update_observation(update)
        assert not result.success
        active = SQLiteDocumentRepository(case.database).list_documents_for_observation(
            "OBS-000001"
        )
        assert len(active) == 1
        assert active[0].title == "Alt"
    finally:
        case.tearDown()


def test_crash_after_file_publish_continues_same_operation() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "publish.txt"
        source.write_text("publish", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Publish"),)
        )
        original = ObservationPersistenceUnitOfWork._commit_database
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            side_effect=RuntimeError("simulierter Crash vor DB"),
        ):
            assert not case.adapter.save_observation(draft).success
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            autospec=True,
            side_effect=original,
        ):
            retry = case.adapter.save_observation(draft)
        assert retry.success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    finally:
        case.tearDown()


def test_crash_before_prepared_never_stages_or_mutates_and_retry_succeeds() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "before-prepared.txt"
        source.write_text("before prepared", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Prepared"),)
        )
        with mock.patch.object(
            ObservationOperationJournal,
            "write",
            side_effect=RuntimeError("simulierter Crash vor PREPARED"),
        ):
            assert not case.adapter.save_observation(draft).success
        operation_root = (
            Path(case.temp_dir.name)
            / ".observation-staging"
            / draft.operation_token
        )
        assert not (operation_root / "files").exists()
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert case.adapter.save_observation(draft).success
    finally:
        case.tearDown()


def test_crash_after_database_commit_verifies_exact_events_and_finishes() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "after-db.txt"
        source.write_text("after db", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "After DB"),)
        )
        original_advance = ObservationPersistenceUnitOfWork._advance

        def crash_before_database_journal_advance(
            journal: object,
            state: dict[str, object],
            phase: str,
        ) -> None:
            if phase == "DATABASE_COMMITTED":
                raise RuntimeError("simulierter Crash nach DB-Commit")
            original_advance(journal, state, phase)

        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_advance",
            side_effect=crash_before_database_journal_advance,
        ):
            assert not case.adapter.save_observation(draft).success
        published = (
            Path(case.temp_dir.name)
            / "documents"
            / "STU-000001"
            / "MED-000001_after-db.txt"
        )
        published.unlink()
        assert not published.exists()
        retry = case.adapter.save_observation(draft)
        assert retry.success
        assert published.read_text(encoding="utf-8") == "after db"
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(DISTINCT operation_token) FROM persistence_events"
            ).fetchone()[0] == 1
    finally:
        case.tearDown()


def test_retry_rejects_changed_attachment_payload() -> None:
    case = _case()
    try:
        first_source = Path(case.temp_dir.name) / "first.txt"
        second_source = Path(case.temp_dir.name) / "second.txt"
        first_source.write_text("first", encoding="utf-8")
        second_source.write_text("second", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(first_source), "First"),)
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            side_effect=RuntimeError("simulierter Crash"),
        ):
            assert not case.adapter.save_observation(draft).success
        changed = replace(
            case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(second_source), "Second"),),
            ),
            operation_token=draft.operation_token,
        )
        result = case.adapter.save_observation(changed)
        assert not result.success
        assert result.error_type == "ObservationOperationConflict"
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
    finally:
        case.tearDown()


def test_source_swap_during_copy_is_detected_before_publication() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "source-swap.txt"
        source.write_text("original payload", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Swap"),)
        )
        from src.core import observation_uow as uow_module

        original_write_all = uow_module._write_all

        def mutate_after_source_chunk(fd: int, value: bytes) -> None:
            original_write_all(fd, value)
            if value == b"original payload":
                source.write_text("mutated payload with other size", encoding="utf-8")

        with mock.patch(
            "src.core.observation_uow._write_all",
            side_effect=mutate_after_source_chunk,
        ):
            result = case.adapter.save_observation(draft)
        assert not result.success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    finally:
        case.tearDown()


def test_staging_fsync_failure_is_retryable_without_database_mutation() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "fsync.txt"
        source.write_text("fsync", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Fsync"),)
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_stage_files",
            side_effect=RuntimeError("Stop nach PREPARED"),
        ):
            assert not case.adapter.save_observation(draft).success
        with mock.patch(
            "src.core.observation_uow.os.fsync",
            side_effect=OSError("simulierter fsync-Fehler"),
        ):
            assert not case.adapter.save_observation(draft).success
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert case.adapter.save_observation(draft).success
    finally:
        case.tearDown()


def test_writer_lock_serializes_threads_and_is_reentrant(tmp_path: Path) -> None:
    root = tmp_path / ".observation-staging"
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()

    def first() -> None:
        with ObservationWriterLock(root):
            with ObservationWriterLock(root):
                first_entered.set()
                release_first.wait(timeout=2)

    def second() -> None:
        first_entered.wait(timeout=2)
        with ObservationWriterLock(root):
            second_entered.set()

    first_thread = threading.Thread(target=first)
    second_thread = threading.Thread(target=second)
    first_thread.start()
    second_thread.start()
    assert first_entered.wait(timeout=2)
    time.sleep(0.05)
    assert not second_entered.is_set()
    release_first.set()
    first_thread.join(timeout=2)
    second_thread.join(timeout=2)
    assert second_entered.is_set()


def test_backup_fails_closed_on_conflicting_pending_operation() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "conflict.txt"
        source.write_text("conflict", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Conflict"),)
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            side_effect=RuntimeError("simulierter Crash"),
        ):
            assert not case.adapter.save_observation(draft).success
        with case.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO observations (
                    observation_id, student_id, date, subject_id, context, note,
                    active, created_at, updated_at
                ) VALUES (
                    'OBS-000001', 'STU-000001', '2026-07-26', 'deutsch',
                    'fremd', 'fremd', 1,
                    '2026-07-26T12:00:00+00:00',
                    '2026-07-26T12:00:00+00:00'
                )
                """
            )
        with pytest.raises(ObservationOperationConflict):
            _backup(case, "blocked-backups")
        assert not tuple(
            (Path(case.temp_dir.name) / "blocked-backups").glob("*.jkmbackup")
        )
    finally:
        case.tearDown()


def test_backup_fails_closed_on_corrupted_pending_journal() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "corrupt-journal.txt"
        source.write_text("corrupt", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Corrupt"),)
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            side_effect=RuntimeError("simulierter Crash"),
        ):
            assert not case.adapter.save_observation(draft).success
        journal = (
            Path(case.temp_dir.name)
            / ".observation-staging"
            / draft.operation_token
            / "journal.json"
        )
        journal.write_text('{"journal_version":1}', encoding="utf-8")
        with pytest.raises(ObservationUnitOfWorkError):
            _backup(case, "corrupt-backups")
        assert not tuple(
            (Path(case.temp_dir.name) / "corrupt-backups").glob("*.jkmbackup")
        )
    finally:
        case.tearDown()


def test_normal_document_writer_uses_reserved_id_after_pending_operation() -> None:
    case = _case()
    try:
        observation_source = Path(case.temp_dir.name) / "observation.txt"
        standalone_source = Path(case.temp_dir.name) / "standalone.txt"
        observation_source.write_text("observation", encoding="utf-8")
        standalone_source.write_text("standalone", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(
                ObservationAttachmentDraft(str(observation_source), "Observation"),
            )
        )
        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_commit_database",
            side_effect=RuntimeError("simulierter Crash"),
        ):
            assert not case.adapter.save_observation(draft).success

        standalone = case.adapter.add_student_document(
            student_id="STU-000001",
            source_path=standalone_source,
            title="Standalone",
        )

        assert standalone.document_id == "MED-000002"
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
    finally:
        case.tearDown()


def test_no_clobber_rejects_foreign_final_file() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "foreign.txt"
        source.write_text("intended", encoding="utf-8")
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(source), "Foreign"),)
        )
        original_publish = ObservationPersistenceUnitOfWork._publish_files

        def publish_with_collision(
            unit: ObservationPersistenceUnitOfWork,
            journal: object,
            state: dict[str, object],
        ) -> None:
            item = state["new_documents"][0]
            target = unit.data_root / item["final_relative_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("foreign", encoding="utf-8")
            original_publish(unit, journal, state)

        with mock.patch.object(
            ObservationPersistenceUnitOfWork,
            "_publish_files",
            autospec=True,
            side_effect=publish_with_collision,
        ):
            result = case.adapter.save_observation(draft)
        assert not result.success
        target = (
            Path(case.temp_dir.name)
            / "documents"
            / "STU-000001"
            / "MED-000001_foreign.txt"
        )
        assert target.read_text(encoding="utf-8") == "foreign"
        with case.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
    finally:
        case.tearDown()


def test_symlink_source_is_rejected() -> None:
    case = _case()
    try:
        source = Path(case.temp_dir.name) / "real.txt"
        link = Path(case.temp_dir.name) / "link.txt"
        source.write_text("real", encoding="utf-8")
        link.symlink_to(source)
        draft = case._sample_observation_draft(
            attachments=(ObservationAttachmentDraft(str(link), "Link"),)
        )
        assert not case.adapter.save_observation(draft).success
    finally:
        case.tearDown()
