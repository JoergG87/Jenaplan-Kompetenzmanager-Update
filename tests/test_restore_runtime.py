"""Productive restore lock, handoff, journal, rollback and recovery tests."""

from __future__ import annotations

import inspect
import json
import os
import sqlite3
import stat
from pathlib import Path
from unittest import mock

import pytest

from src.application.commands.backup import BackupApplicationService, CreateBackupCommand
from src.application.commands.restore import (
    CreateRestoreHandoffCommand,
    PrepareRestoreStagingCommand,
    RestoreApplicationService,
)
from src.core.restore_runtime import (
    ProductiveRestoreService,
    RestoreHandoffError,
    RestoreHandoffService,
    RestoreJournal,
    RestoreLockError,
    RestoreManualRecoveryRequired,
    RestorePreflightError,
    RestoreReplacementError,
    RuntimeInstanceLock,
    confirm_restore_startup,
    recover_interrupted_restore,
    restore_transaction_paths,
)
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app import main as desktop_main
from src.desktop_app import restore_worker
from src.desktop_app.runtime import RuntimePaths, runtime_paths


def _runtime(root: Path) -> RuntimePaths:
    paths = runtime_paths(root)
    for directory in (paths.root, paths.documents, paths.exports, paths.backups, paths.logs):
        directory.mkdir(parents=True, exist_ok=True)
    SQLiteDatabase(paths.database).initialize_schema()
    return paths


def _insert_data(paths: RuntimePaths, prefix: str, *, managed: bool = False) -> None:
    group_id = f"GRP-{prefix}"
    course_id = f"CRS-{prefix}"
    student_id = f"STU-{prefix}"
    observation_id = f"OBS-{prefix}"
    with sqlite3.connect(paths.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO groups VALUES (?, ?, 0, 1)", (group_id, f"Group {prefix}"))
        connection.execute(
            "INSERT INTO courses (course_id, course_name, color_key, color_name, color_hex, sort_order, active) "
            "VALUES (?, ?, NULL, '', '', 0, 1)",
            (course_id, f"Course {prefix}"),
        )
        connection.execute(
            "INSERT INTO students VALUES (?, ?, ?, ?, ?, '', 1, '2026-01-01', '2026-01-01', NULL)",
            (student_id, f"First {prefix}", f"Last {prefix}", group_id, course_id),
        )
        connection.execute(
            "INSERT INTO observations VALUES (?, ?, '2026-01-02', 'MAT', '', '', 1, '2026-01-02', '2026-01-02')",
            (observation_id, student_id),
        )
        if managed:
            file_path = paths.documents / student_id / f"MED-{prefix}.txt"
            file_path.parent.mkdir(parents=True)
            file_path.write_bytes(f"managed-{prefix}".encode())
            connection.execute(
                "INSERT INTO documents (document_id, student_id, observation_id, title, document_type, "
                "file_path, original_filename, created_at, note, active) "
                "VALUES (?, ?, NULL, '', 'Sonstiges', ?, 'source.txt', '2026-01-03', '', 1)",
                (f"MED-{prefix}", student_id, str(file_path)),
            )


def _backup(paths: RuntimePaths) -> Path:
    return BackupApplicationService().create(
        CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version="0.1.2",
            build_commit="a39345a",
            source_tree_state="clean",
        )
    ).path


def _prepared(tmp_path: Path, restore_id: str = "RST-RUNTIME"):
    source = _runtime(tmp_path / "source")
    _insert_data(source, "NEW001", managed=True)
    archive = _backup(source)
    live = _runtime(tmp_path / "live")
    _insert_data(live, "OLD001", managed=True)
    service = RestoreApplicationService()
    service.prepare_staging(PrepareRestoreStagingCommand(archive, live, restore_id))
    handoff = service.create_handoff(
        CreateRestoreHandoffCommand(
            path=archive,
            restore_id=restore_id,
            runtime_paths=live,
            app_version="0.1.2",
            build_commit="a39345a",
            source_tree_state="clean",
        )
    )
    return source, live, archive, handoff


def _live_bytes(paths: RuntimePaths) -> tuple[bytes, tuple[tuple[str, bytes], ...]]:
    documents = tuple(
        sorted(
            (path.relative_to(paths.documents).as_posix(), path.read_bytes())
            for path in paths.documents.rglob("*")
            if path.is_file()
        )
    ) if paths.documents.exists() else ()
    return paths.database.read_bytes(), documents


def _student_ids(path: Path) -> tuple[str, ...]:
    with sqlite3.connect(path) as connection:
        return tuple(row[0] for row in connection.execute("SELECT student_id FROM students ORDER BY student_id"))


def test_second_app_or_worker_instance_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    with RuntimeInstanceLock(root):
        with pytest.raises(RestoreLockError):
            RuntimeInstanceLock(root).acquire()


def test_valid_orphaned_lock_is_reused_but_contradictory_lock_is_not_deleted(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    first = RuntimeInstanceLock(root)
    first.acquire()
    first.release()
    with RuntimeInstanceLock(root):
        pass
    lock_path = root / "instance.lock"
    lock_path.write_text("{}", encoding="utf-8")
    with pytest.raises(RestoreLockError, match="widerspruechlich"):
        RuntimeInstanceLock(root).acquire()
    assert lock_path.read_text(encoding="utf-8") == "{}"


def test_handoff_is_0600_runtime_bound_and_contains_no_target_paths(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    assert stat.S_IMODE(handoff.path.stat().st_mode) == 0o600
    payload = json.loads(handoff.path.read_text(encoding="utf-8"))
    assert "archive_path" not in payload
    assert set(key for key in payload if key.endswith("path")) == set()
    paths = restore_transaction_paths(live.root, handoff.restore_id)
    assert paths.bound_archive.is_file()


def test_wrong_nonce_tampering_and_handoff_reuse_are_rejected(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    service = RestoreHandoffService()
    with pytest.raises(RestoreHandoffError, match="Nonce"):
        service.consume(handoff.path, expected_nonce="wrong")
    original = handoff.path.read_bytes()
    payload = json.loads(original)
    payload["archive_sha256"] = "0" * 64
    handoff.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with pytest.raises(RestoreHandoffError, match="kanonisch"):
        service.consume(handoff.path, expected_nonce=handoff.nonce)
    handoff.path.write_bytes(original)
    paths, _payload = service.consume(handoff.path, expected_nonce=handoff.nonce)
    assert paths.consumed_handoff.is_file()
    with pytest.raises(RestoreHandoffError):
        service.consume(handoff.path, expected_nonce=handoff.nonce)
    assert paths.runtime_root == live.root.resolve()


def test_free_runtime_target_projection_is_rejected(tmp_path: Path) -> None:
    source = _runtime(tmp_path / "source")
    archive = _backup(source)
    live = _runtime(tmp_path / "live")
    service = RestoreApplicationService()
    service.prepare_staging(PrepareRestoreStagingCommand(archive, live, "RST-PATH"))
    contradictory = RuntimePaths(
        root=live.root,
        database=tmp_path / "outside.sqlite",
        documents=live.documents,
        exports=live.exports,
        backups=live.backups,
        logs=live.logs,
    )
    with pytest.raises(RestoreHandoffError, match="Pfadprojektion"):
        service.create_handoff(
            CreateRestoreHandoffCommand(
                archive, "RST-PATH", contradictory, "0.1.2", "a39345a", "clean"
            )
        )


def test_successful_v1_restore_completes_only_after_startup_handshake(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    with RuntimeInstanceLock(live.root) as lock:
        result = ProductiveRestoreService().execute(
            handoff_path=handoff.path,
            nonce=handoff.nonce,
            lock=lock,
            restart=lambda paths, token, _lock: bool(
                confirm_restore_startup(paths.runtime_root, paths.transaction.name, token)
            ),
        )
    assert result.status == "completed"
    assert _student_ids(live.database) == ("STU-NEW001",)
    state = RestoreJournal(restore_transaction_paths(live.root, handoff.restore_id)).read()
    assert state["phase"] == "completed"
    assert state["restart_handshake"]["status"] == "confirmed"


def test_successful_prepared_v0_to_v1_restore_keeps_rows_and_installs_v1(tmp_path: Path) -> None:
    source = _runtime(tmp_path / "source-v0")
    _insert_data(source, "V00001", managed=True)
    with sqlite3.connect(source.database) as connection:
        connection.execute("PRAGMA user_version = 0")
    archive = _backup(source)
    live = _runtime(tmp_path / "live-v0")
    service = RestoreApplicationService()
    restore_id = "RST-V0-V1"
    service.prepare_staging(PrepareRestoreStagingCommand(archive, live, restore_id))
    handoff = service.create_handoff(
        CreateRestoreHandoffCommand(archive, restore_id, live, "0.1.2", "a39345a", "clean")
    )
    with RuntimeInstanceLock(live.root) as lock:
        ProductiveRestoreService().execute(
            handoff_path=handoff.path,
            nonce=handoff.nonce,
            lock=lock,
            restart=lambda paths, token, _lock: bool(
                confirm_restore_startup(paths.runtime_root, paths.transaction.name, token)
            ),
        )
    with sqlite3.connect(live.database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT student_id FROM students").fetchall() == [("STU-V00001",)]


@pytest.mark.parametrize("documents_state", ["missing", "empty"])
def test_missing_and_empty_old_documents_are_distinct_and_restore_succeeds(
    tmp_path: Path,
    documents_state: str,
) -> None:
    _source, live, archive, _handoff = _prepared(tmp_path, "RST-DOCS-BASE")
    # Build a second live runtime without a registered old managed file.
    clean_live = _runtime(tmp_path / f"live-{documents_state}")
    if documents_state == "missing":
        clean_live.documents.rmdir()
    service = RestoreApplicationService()
    restore_id = f"RST-DOCS-{documents_state.upper()}"
    service.prepare_staging(PrepareRestoreStagingCommand(archive, clean_live, restore_id))
    handoff = service.create_handoff(
        CreateRestoreHandoffCommand(archive, restore_id, clean_live, "0.1.2", "a39345a", "clean")
    )
    with RuntimeInstanceLock(clean_live.root) as lock:
        ProductiveRestoreService().execute(
            handoff_path=handoff.path,
            nonce=handoff.nonce,
            lock=lock,
            restart=lambda paths, token, _lock: bool(
                confirm_restore_startup(paths.runtime_root, paths.transaction.name, token)
            ),
        )
    state = RestoreJournal(restore_transaction_paths(clean_live.root, restore_id)).read()
    expected_kind = "missing" if documents_state == "missing" else "directory"
    assert state["components"]["documents"]["before"]["kind"] == expected_kind


def test_restart_failure_rolls_back_database_and_documents_byte_identically(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    before = _live_bytes(live)
    with RuntimeInstanceLock(live.root) as lock:
        with pytest.raises(RestoreReplacementError, match="zurueckgerollt"):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: False,
            )
    assert _live_bytes(live) == before
    paths = restore_transaction_paths(live.root, handoff.restore_id)
    assert RestoreJournal(paths).read()["phase"] == "rolled_back"
    assert paths.failed_new.joinpath("kompetenzmanager.sqlite").is_file()


def test_existing_wal_and_shm_are_checkpointed_journaled_and_retained(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, "RST-WAL")
    connection = sqlite3.connect(live.database)
    try:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone()[0] == "wal"
        connection.execute("PRAGMA wal_autocheckpoint = 0")
        connection.execute(
            "UPDATE students SET updated_at = '2026-02-01' WHERE student_id = 'STU-OLD001'"
        )
        connection.commit()
        assert Path(f"{live.database}-wal").exists()
        assert Path(f"{live.database}-shm").exists()
        with RuntimeInstanceLock(live.root) as lock:
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda paths, token, _lock: bool(
                    confirm_restore_startup(paths.runtime_root, paths.transaction.name, token)
                ),
            )
    finally:
        connection.close()
    paths = restore_transaction_paths(live.root, handoff.restore_id)
    state = RestoreJournal(paths).read()
    assert state["components"]["wal"]["before"]["kind"] == "file"
    assert state["components"]["shm"]["before"]["kind"] == "file"
    assert paths.rollback.joinpath("kompetenzmanager.sqlite-wal").exists()
    assert paths.rollback.joinpath("kompetenzmanager.sqlite-shm").exists()


def test_verified_safety_backup_exists_before_first_live_rename(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, "RST-SAFETY-ORDER")
    original = RestoreJournal.rename
    observed = False

    def verify_safety_then_rename(self, *, name, source, target):
        nonlocal observed
        if not observed:
            safety = live.backups / "restore-safety" / handoff.restore_id
            assert tuple(safety.glob("*.jkmbackup"))
            assert self.read()["safety_backup_sha256"]
            observed = True
        return original(self, name=name, source=source, target=target)

    with RuntimeInstanceLock(live.root) as lock, mock.patch.object(
        RestoreJournal, "rename", verify_safety_then_rename
    ):
        ProductiveRestoreService().execute(
            handoff_path=handoff.path,
            nonce=handoff.nonce,
            lock=lock,
            restart=lambda paths, token, _lock: bool(
                confirm_restore_startup(paths.runtime_root, paths.transaction.name, token)
            ),
        )
    assert observed


@pytest.mark.parametrize("fail_after", [1, 2, 3, 4])
def test_failure_after_each_present_critical_rename_never_leaves_mixed_live_state(
    tmp_path: Path,
    fail_after: int,
) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, f"RST-RENAME-{fail_after}")
    before = _live_bytes(live)
    original = RestoreJournal.rename
    calls = 0

    def rename_then_fail(self, *, name, source, target):
        nonlocal calls
        calls += 1
        original(self, name=name, source=source, target=target)
        if calls == fail_after:
            raise OSError("injected rename boundary failure")

    with RuntimeInstanceLock(live.root) as lock, mock.patch.object(
        RestoreJournal, "rename", rename_then_fail
    ):
        with pytest.raises(RestoreReplacementError):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: True,
                handshake_timeout_seconds=0,
            )
    assert _live_bytes(live) == before
    assert RestoreJournal(restore_transaction_paths(live.root, handoff.restore_id)).read()["phase"] == "rolled_back"


@pytest.mark.parametrize("fail_after", [2, 3])
def test_failure_after_wal_and_shm_rename_restores_all_sidecars(
    tmp_path: Path,
    fail_after: int,
) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, f"RST-WAL-FAIL-{fail_after}")
    connection = sqlite3.connect(live.database)
    original = RestoreJournal.rename
    calls = 0

    def rename_then_fail(self, *, name, source, target):
        nonlocal calls
        calls += 1
        original(self, name=name, source=source, target=target)
        if calls == fail_after:
            raise OSError("injected sidecar rename failure")

    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA wal_autocheckpoint = 0")
        connection.execute(
            "UPDATE students SET updated_at = '2026-03-01' WHERE student_id = 'STU-OLD001'"
        )
        connection.commit()
        with RuntimeInstanceLock(live.root) as lock, mock.patch.object(
            RestoreJournal, "rename", rename_then_fail
        ):
            with pytest.raises(RestoreReplacementError):
                ProductiveRestoreService().execute(
                    handoff_path=handoff.path,
                    nonce=handoff.nonce,
                    lock=lock,
                    restart=lambda *_args: True,
                )
    finally:
        connection.close()
    state = RestoreJournal(restore_transaction_paths(live.root, handoff.restore_id)).read()
    assert state["phase"] == "rolled_back"
    assert state["components"]["wal"]["before"]["kind"] == "file"
    assert state["components"]["shm"]["before"]["kind"] == "file"


def test_preflight_hash_or_space_failure_keeps_live_bytes_unchanged(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    before = _live_bytes(live)
    paths = restore_transaction_paths(live.root, handoff.restore_id)
    paths.prepared_database.write_bytes(b"tampered")
    with RuntimeInstanceLock(live.root) as lock:
        with pytest.raises(RestorePreflightError):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: True,
            )
    assert _live_bytes(live) == before


def test_missing_space_fails_closed(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, "RST-NO-SPACE")
    before = _live_bytes(live)
    with RuntimeInstanceLock(live.root) as lock, mock.patch(
        "src.core.restore_runtime.shutil.disk_usage", return_value=mock.Mock(free=0)
    ):
        with pytest.raises(RestorePreflightError, match="freie Speicher"):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: True,
            )
    assert _live_bytes(live) == before


def test_fsync_failure_before_first_rename_restores_preflight_bytes(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, "RST-FSYNC")
    before = _live_bytes(live)
    from src.core import restore_runtime as runtime_module

    original = runtime_module._fsync_path
    failed = False

    def fail_live_database(path: Path) -> None:
        nonlocal failed
        if path == live.database.resolve() and not failed:
            failed = True
            raise OSError("injected fsync failure")
        original(path)

    with RuntimeInstanceLock(live.root) as lock, mock.patch(
        "src.core.restore_runtime._fsync_path", side_effect=fail_live_database
    ):
        with pytest.raises(RestorePreflightError):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: True,
            )
    assert _live_bytes(live) == before


def test_start_recovery_rolls_back_a_partially_moved_database_idempotently(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    before = _live_bytes(live)
    service = ProductiveRestoreService()
    with RuntimeInstanceLock(live.root) as lock:
        paths, payload = service.handoff_service.consume(handoff.path, expected_nonce=handoff.nonce)
        journal = RestoreJournal(paths)
        journal.transition("maintenance", next_step="verify_preflight")
        service._preflight(paths, payload, journal)
        journal.transition("replacement_started", next_step="move_live_database")
        journal.rename(
            name="old_database_to_rollback",
            source=paths.live_database,
            target=paths.rollback / "kompetenzmanager.sqlite",
        )
    first = recover_interrupted_restore(live.root)
    second = recover_interrupted_restore(live.root)
    assert first.status == "rolled_back"
    assert second.status == "normal_start"
    assert _live_bytes(live) == before


def test_installed_without_handshake_gets_one_controlled_resume(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)

    def simulate_process_abort(*_args):
        raise KeyboardInterrupt

    with RuntimeInstanceLock(live.root) as lock:
        with pytest.raises(KeyboardInterrupt):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=simulate_process_abort,
            )
    recovery = recover_interrupted_restore(live.root)
    assert recovery.status == "resume_required"
    assert recovery.restore_id == handoff.restore_id
    assert recovery.resume_token is not None
    confirm_restore_startup(live.root, recovery.restore_id, recovery.resume_token)
    assert recover_interrupted_restore(live.root).status == "normal_start"


def test_second_missing_handshake_attempt_rolls_back_instead_of_starting(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, "RST-RESUME-LIMIT")
    before = _live_bytes(live)
    with RuntimeInstanceLock(live.root) as lock:
        with pytest.raises(KeyboardInterrupt):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt()),
            )
    assert recover_interrupted_restore(live.root).status == "resume_required"
    assert recover_interrupted_restore(live.root).status == "rolled_back"
    assert _live_bytes(live) == before


def test_invalid_resume_token_is_rejected_without_normal_start(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    with RuntimeInstanceLock(live.root) as lock:
        with pytest.raises(KeyboardInterrupt):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt()),
            )
    with pytest.raises(RestoreHandoffError, match="Resume-Token"):
        confirm_restore_startup(live.root, handoff.restore_id, "wrong")
    assert RestoreJournal(restore_transaction_paths(live.root, handoff.restore_id)).read()["phase"] == "installed_verified"


def test_partial_rollback_failure_enters_manual_recovery_and_blocks_recovery(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path)
    with RuntimeInstanceLock(live.root) as lock, mock.patch(
        "src.core.restore_runtime.rollback_restore",
        side_effect=OSError("injected rollback failure"),
    ):
        with pytest.raises(RestoreManualRecoveryRequired):
            ProductiveRestoreService().execute(
                handoff_path=handoff.path,
                nonce=handoff.nonce,
                lock=lock,
                restart=lambda *_args: False,
            )
    with pytest.raises(RestoreManualRecoveryRequired):
        recover_interrupted_restore(live.root)


def test_tampered_event_journal_and_contradictory_live_path_block_start(tmp_path: Path) -> None:
    _source, live, _archive, handoff = _prepared(tmp_path, "RST-JOURNAL-TAMPER")
    paths = restore_transaction_paths(live.root, handoff.restore_id)
    with paths.events.open("ab") as events:
        events.write(b"not-json\n")
    with pytest.raises(RestoreManualRecoveryRequired):
        recover_interrupted_restore(live.root)

    other_root = tmp_path / "other-case"
    _source, other_live, _archive, other_handoff = _prepared(
        other_root, "RST-PATH-CONTRADICTION"
    )
    service = ProductiveRestoreService()
    with RuntimeInstanceLock(other_live.root) as lock:
        tx, payload = service.handoff_service.consume(
            other_handoff.path, expected_nonce=other_handoff.nonce
        )
        journal = RestoreJournal(tx)
        journal.transition("maintenance", next_step="verify_preflight")
        service._preflight(tx, payload, journal)
        journal.transition("preflight_verified", next_step="move_live_database")
    os.rename(other_live.documents, other_live.root / "documents-unexpected")
    with pytest.raises(RestoreManualRecoveryRequired, match="Live-Pfad"):
        recover_interrupted_restore(other_live.root)


def test_no_restore_journal_allows_normal_start(tmp_path: Path) -> None:
    live = _runtime(tmp_path / "live")
    assert recover_interrupted_restore(live.root).status == "normal_start"


def test_startup_recovery_is_positioned_before_runtime_qt_and_logging() -> None:
    source = inspect.getsource(desktop_main.main)
    recovery = source.index("recover_interrupted_restore(data_root)")
    assert recovery < source.index("QApplication(arguments)")
    assert recovery < source.index("prepare_runtime_storage")
    assert recovery < source.index("configure_runtime_logging")


def test_developer_and_packaged_worker_dispatch_use_same_productive_service(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    assert restore_worker.run(["--handoff", str(missing), "--nonce", "x"]) == restore_worker.EXIT_HANDOFF_INVALID
    with mock.patch("src.desktop_app.restore_worker.run", return_value=37) as run:
        with mock.patch.object(
            desktop_main.sys,
            "argv",
            ["app", "--restore-worker", "--handoff", str(missing), "--nonce", "x"],
        ):
            assert desktop_main.main() == 37
    run.assert_called_once_with(["--handoff", str(missing), "--nonce", "x"])
