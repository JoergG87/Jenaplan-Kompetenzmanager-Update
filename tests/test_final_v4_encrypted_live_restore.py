from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import sys
import uuid
import inspect

import pytest

from src.core.restore_runtime import (
    RestoreHandoffError,
    RestoreJournal,
    RestoreManualRecoveryRequired,
    RestorePreflightError,
    RestoreReplacementError,
    RuntimeInstanceLock,
    restore_transaction_paths,
)
from src.desktop_app.restore_worker import (
    EXIT_SUCCESS,
    RESTORE_MODE_FINAL_V4_ENCRYPTED,
    RestoreWorkerLaunchPlan,
)
from src.desktop_app import restore_worker
from src.desktop_app import main as desktop_main
from src.desktop_app.runtime import runtime_paths
from src.security.final_v4_backup_runtime import (
    FINAL_V4_RESTORE_READY_FILENAME,
    FinalV4EncryptedBackupError,
)
from src.security.backup_container import EncryptedBackupError
from src.security.final_v4_live_restore import (
    FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY,
    FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY,
    FinalV4EncryptedLiveRestoreService,
    FinalV4EncryptedRestoreHandoffService,
    confirm_final_v4_restore_startup,
    prepare_final_v4_live_restore,
    recover_interrupted_final_v4_restore,
)
from src.security import final_v4_live_restore
from src.security.cipher_product_runtime import open_cipher_product_runtime
from tests.test_final_v4_encrypted_backup import (
    _add_all_document_classes,
    _open_case,
)
from tests.test_final_v4_sqlcipher_runtime import requires_exact_417
from tests.test_final_v3_document_runtime import _Consumer


def _write_excluded_sentinels(root: Path) -> tuple[bytes, bytes]:
    security = root / "security"
    security.mkdir(mode=0o700, exist_ok=True)
    security_bytes = b"security-store-must-remain-byte-identical"
    preferences_bytes = b'{"display_name":"Laura"}'
    (security / "security.sqlite").write_bytes(security_bytes)
    (root / "app-preferences.json").write_bytes(preferences_bytes)
    return security_bytes, preferences_bytes


def _assert_excluded(root: Path, expected: tuple[bytes, bytes]) -> None:
    security_bytes, preferences_bytes = expected
    assert (root / "security" / "security.sqlite").read_bytes() == security_bytes
    assert (root / "app-preferences.json").read_bytes() == preferences_bytes


def _prepare_restore(tmp_path: Path, *, include_bootstrap_context: bool = False):
    (
        runtime,
        backup_service,
        key_store,
        _environment,
        account_loader,
        provider,
    ) = _open_case(tmp_path)
    payloads = _add_all_document_classes(runtime)
    with runtime.final_v4.database.connect() as connection:
        connection.execute(
            """
            INSERT INTO school_years (
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES ('SY-PILOT-2026-27', '2026/27', '2026-08-01',
                      '2027-07-31', 'current', '2026-08-09T10:00:00Z', NULL)
            """
        )
        connection.executemany(
            """
            INSERT INTO documentation_subject_settings (
                subject_id, active, updated_at
            ) VALUES (?, ?, '2026-08-09T10:00:00Z')
            """,
            (("DEU", 1), ("MAT", 0)),
        )
        connection.execute(
            """
            INSERT INTO student_documentation_subject_profiles (
                student_id, school_year_id, mode, created_at, updated_at
            ) VALUES ('STU-000001', 'SY-PILOT-2026-27', 'custom',
                      '2026-08-09T10:00:00Z', '2026-08-09T10:00:00Z')
            """
        )
        connection.execute(
            """
            INSERT INTO student_documentation_subject_selections (
                student_id, school_year_id, subject_id
            ) VALUES ('STU-000001', 'SY-PILOT-2026-27', 'DEU')
            """
        )
        connection.commit()
    root = backup_service.paths.final_v4.key_runtime.root
    source = tmp_path / "restore-source.jkmebackup"
    source_result = backup_service.create(source)
    restore_id = str(uuid.uuid4())
    staging_parent = root / FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    staging_parent.mkdir(mode=0o700, exist_ok=True)
    staging = backup_service.restore_staging(
        source,
        staging_parent / restore_id,
    )
    with runtime.final_v4.database.connect() as connection:
        connection.execute(
            """
            INSERT INTO students (
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES ('STU-999999', 'Spaeter', 'Hinzugefuegt', '', 1,
                      '2026-08-09T12:00:00Z', '2026-08-09T12:00:00Z', NULL)
            """
        )
        connection.execute(
            """
            DELETE FROM student_documentation_subject_selections
            WHERE student_id = 'STU-000001'
              AND school_year_id = 'SY-PILOT-2026-27'
            """
        )
        connection.execute(
            """
            INSERT INTO student_documentation_subject_selections (
                student_id, school_year_id, subject_id
            ) VALUES ('STU-000001', 'SY-PILOT-2026-27', 'MAT')
            """
        )
        connection.execute(
            """
            UPDATE documentation_subject_settings
            SET active = CASE subject_id WHEN 'DEU' THEN 0 ELSE 1 END,
                updated_at = '2026-08-09T12:00:00Z'
            WHERE subject_id IN ('DEU', 'MAT')
            """
        )
        connection.commit()
    excluded = _write_excluded_sentinels(root)
    lock = RuntimeInstanceLock(root).acquire()
    preparation = prepare_final_v4_live_restore(
        backup_service=backup_service,
        lock=lock,
        staging_root=staging.staging_root,
        expected_container_sha256=source_result.container_sha256,
        restore_id=restore_id,
        app_version="0.0.test",
        build_commit="60650d5",
        source_tree_state="clean",
    )
    prepared = (
        runtime,
        backup_service,
        source_result,
        staging,
        preparation,
        lock,
        excluded,
        payloads,
    )
    if include_bootstrap_context:
        return (*prepared, key_store, account_loader, provider)
    return prepared


def _restart_callback(backup_service):
    def restart(paths, token, _lock):
        result = confirm_final_v4_restore_startup(
            backup_service=backup_service,
            runtime_root=paths.runtime_root,
            restore_id=paths.transaction.name,
            token=token,
        )
        return result.status == "completed"

    return restart


@requires_exact_417
def test_successful_live_restore_keeps_safety_rollback_and_excluded_data(
    tmp_path: Path,
) -> None:
    (
        runtime,
        backup_service,
        source_result,
        _staging,
        preparation,
        lock,
        excluded,
        payloads,
        key_store,
        account_loader,
        provider,
    ) = _prepare_restore(tmp_path, include_bootstrap_context=True)
    dmk_before = dict(key_store.values)
    preparation.safety_backup.transfer_to_worker()
    service = FinalV4EncryptedLiveRestoreService(backup_service)
    result = service.execute(
        handoff_path=preparation.handoff.path,
        nonce=preparation.handoff.nonce,
        lock=lock,
        restart=_restart_callback(backup_service),
        handshake_timeout_seconds=1.0,
    )
    assert result.status == "completed"
    assert result.safety_backup_sha256 == preparation.safety_backup.result.container_sha256
    with runtime.final_v4.database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM students WHERE student_id = 'STU-999999'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM school_years WHERE label = '2026/27' "
            "AND status = 'current'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM students WHERE student_id = 'STU-000001'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM observations WHERE observation_id = 'OBS-000001'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_report_pdf_artifacts "
            "WHERE learning_report_pdf_artifact_id = 'RPA-000001'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_conference_pdf_artifacts "
            "WHERE learning_conference_pdf_artifact_id = 'LCA-000001'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT mode FROM student_documentation_subject_profiles "
            "WHERE student_id = 'STU-000001' "
            "AND school_year_id = 'SY-PILOT-2026-27'"
        ).fetchone()[0] == "custom"
        assert [
            row[0]
            for row in connection.execute(
                "SELECT subject_id FROM student_documentation_subject_selections "
                "WHERE student_id = 'STU-000001' "
                "AND school_year_id = 'SY-PILOT-2026-27' ORDER BY subject_id"
            ).fetchall()
        ] == ["DEU"]
        assert [
            (row[0], row[1])
            for row in connection.execute(
                "SELECT subject_id, active FROM documentation_subject_settings "
                "WHERE subject_id IN ('DEU', 'MAT') ORDER BY subject_id"
            ).fetchall()
        ] == [("DEU", 1), ("MAT", 0)]
    for document_id, payload in payloads.items():
        consumer = _Consumer()
        runtime.documents.read(
            document_id=document_id,
            consumer=consumer,
        )
        assert consumer.started and consumer.finished and consumer.aborted is None
        assert bytes(consumer.payload) == payload
    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )
    assert (paths.rollback / backup_service.paths.final_v4.key_runtime.metadata_root.name).is_dir()
    assert (paths.rollback / backup_service.paths.final_v4.database.name).is_file()
    assert (paths.rollback / backup_service.paths.database.name).is_file()
    assert (paths.rollback / backup_service.paths.container_root.name).is_dir()
    assert preparation.safety_backup.result.path.parent.name == FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY
    assert backup_service.verify_live_runtime(
        paths.runtime_root,
        manifest=source_result.manifest,
    ).manifest == source_result.manifest
    _assert_excluded(paths.runtime_root, excluded)
    assert RestoreJournal(paths).read()["phase"] == "completed"
    assert key_store.values == dmk_before
    product_runtime = open_cipher_product_runtime(
        paths=runtime_paths(paths.runtime_root),
        account_loader=account_loader,
        authentication_confirmed=True,
        first_run_allowed=False,
        key_store=key_store,
        sqlcipher_provider=provider,
    )
    assert product_runtime.database is product_runtime.runtime.final_v4.database
    assert product_runtime.documents is product_runtime.runtime.documents
    lock.release()


@requires_exact_417
@pytest.mark.parametrize("boundary", ["during_swap", "after_swap_before_reopen"])
def test_swap_failures_restore_and_keyed_verify_old_live(
    tmp_path: Path,
    boundary: str,
) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()

    def fail(observed: str) -> None:
        if observed == boundary:
            raise RuntimeError(boundary)

    service = FinalV4EncryptedLiveRestoreService(
        backup_service,
        fault_hook=fail,
    )
    with pytest.raises(RestoreReplacementError):
        service.execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
    backup_service.verify_live_runtime(
        backup_service.paths.final_v4.key_runtime.root,
        manifest=preparation.safety_backup.result.manifest,
        enforce_artifact_hashes=False,
    )
    _assert_excluded(backup_service.paths.final_v4.key_runtime.root, excluded)
    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )
    assert RestoreJournal(paths).read()["phase"] == "rolled_back"
    lock.release()


@requires_exact_417
@pytest.mark.parametrize(
    ("boundary", "expected_status"),
    (
        ("before_swap", "aborted_before_replacement"),
        ("between_main_and_companion", "rolled_back"),
        ("after_databases_before_documents", "rolled_back"),
        ("during_documents", "rolled_back"),
        ("after_swap_before_reopen", "rolled_back"),
        ("after_reopen", "rolled_back"),
    ),
)
def test_bootstrap_recovery_classifies_every_cipher_swap_crash_boundary(
    tmp_path: Path,
    boundary: str,
    expected_status: str,
) -> None:
    (
        runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
        key_store,
        account_loader,
        _provider,
    ) = _prepare_restore(tmp_path, include_bootstrap_context=True)
    preparation.safety_backup.transfer_to_worker()

    def crash_process(observed: str) -> None:
        if observed == boundary:
            os._exit(97)

    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through persisted evidence
        FinalV4EncryptedLiveRestoreService(
            backup_service,
            fault_hook=crash_process,
        ).execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
        os._exit(2)
    lock.transfer()
    waited, status = os.waitpid(child, 0)
    assert waited == child
    assert os.waitstatus_to_exitcode(status) == 97

    recovery = recover_interrupted_final_v4_restore(
        runtime_root=backup_service.paths.final_v4.key_runtime.root,
        account_loader=account_loader,
        key_store=key_store,
    )
    assert recovery.status == expected_status
    assert recovery.restore_id == preparation.handoff.restore_id

    root = backup_service.paths.final_v4.key_runtime.root
    backup_service.verify_live_runtime(
        root,
        manifest=preparation.safety_backup.result.manifest,
        enforce_artifact_hashes=False,
    )
    with runtime.final_v4.database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM students WHERE student_id = 'STU-999999'"
        ).fetchone()[0] == 1
    _assert_excluded(root, excluded)
    paths = restore_transaction_paths(root, preparation.handoff.restore_id)
    assert RestoreJournal(paths).read()["phase"] == expected_status
    if expected_status == "aborted_before_replacement":
        assert not any(paths.rollback.iterdir())


@requires_exact_417
def test_unclear_mixed_state_requires_manual_recovery(tmp_path: Path) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()
    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )

    def create_conflict(observed: str) -> None:
        if observed == "after_swap_before_reopen":
            conflict = paths.failed_new / backup_service.paths.database.name
            conflict.mkdir()
            raise RuntimeError("ambiguous")

    service = FinalV4EncryptedLiveRestoreService(
        backup_service,
        fault_hook=create_conflict,
    )
    with pytest.raises(RestoreManualRecoveryRequired):
        service.execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
    assert RestoreJournal(paths).read()["phase"] == "manual_recovery_required"
    _assert_excluded(paths.runtime_root, excluded)
    lock.release()


@requires_exact_417
def test_bootstrap_recovery_marks_ambiguous_crash_state_for_manual_recovery(
    tmp_path: Path,
) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
        key_store,
        account_loader,
        _provider,
    ) = _prepare_restore(tmp_path, include_bootstrap_context=True)
    preparation.safety_backup.transfer_to_worker()
    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )

    class SimulatedProcessCrash(BaseException):
        pass

    def crash_after_swap(observed: str) -> None:
        if observed == "after_swap_before_reopen":
            raise SimulatedProcessCrash()

    with pytest.raises(SimulatedProcessCrash):
        FinalV4EncryptedLiveRestoreService(
            backup_service,
            fault_hook=crash_after_swap,
        ).execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
    lock.release()

    ambiguous = paths.failed_new / backup_service.paths.container_root.name
    ambiguous.mkdir()
    with pytest.raises(RestoreManualRecoveryRequired):
        recover_interrupted_final_v4_restore(
            runtime_root=paths.runtime_root,
            account_loader=account_loader,
            key_store=key_store,
        )
    assert RestoreJournal(paths).read()["phase"] == "manual_recovery_required"
    _assert_excluded(paths.runtime_root, excluded)


@requires_exact_417
def test_keyed_reopen_failure_rolls_back_complete_old_runtime(tmp_path: Path) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()

    def corrupt_new_main(observed: str) -> None:
        if observed == "after_swap_before_reopen":
            database = backup_service.paths.final_v4.database
            with database.open("r+b") as file:
                file.seek(0)
                file.write(b"not-a-valid-sqlcipher-header")

    service = FinalV4EncryptedLiveRestoreService(
        backup_service,
        fault_hook=corrupt_new_main,
    )
    with pytest.raises(RestoreReplacementError):
        service.execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
    backup_service.verify_live_runtime(
        backup_service.paths.final_v4.key_runtime.root,
        manifest=preparation.safety_backup.result.manifest,
        enforce_artifact_hashes=False,
    )
    _assert_excluded(backup_service.paths.final_v4.key_runtime.root, excluded)
    lock.release()


@requires_exact_417
def test_error_before_swap_aborts_without_live_replacement(tmp_path: Path) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()

    def stop_before_swap(observed: str) -> None:
        if observed == "before_swap":
            raise RuntimeError("before-swap")

    with pytest.raises(RestorePreflightError):
        FinalV4EncryptedLiveRestoreService(
            backup_service,
            fault_hook=stop_before_swap,
        ).execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
    backup_service.verify_live_runtime(
        backup_service.paths.final_v4.key_runtime.root,
        manifest=preparation.safety_backup.result.manifest,
        enforce_artifact_hashes=False,
    )
    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )
    assert RestoreJournal(paths).read()["phase"] == "aborted_before_replacement"
    assert not any(paths.rollback.iterdir())
    _assert_excluded(paths.runtime_root, excluded)
    lock.release()


@requires_exact_417
def test_safety_backup_failure_creates_no_handoff_or_live_mutation(
    tmp_path: Path,
) -> None:
    runtime, backup_service, *_ = _open_case(tmp_path)
    _add_all_document_classes(runtime)
    source = tmp_path / "source.jkmebackup"
    source_result = backup_service.create(source)
    root = backup_service.paths.final_v4.key_runtime.root
    restore_id = str(uuid.uuid4())
    parent = root / FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    parent.mkdir(mode=0o700)
    staging = backup_service.restore_staging(source, parent / restore_id)
    before = backup_service.verify_live_runtime(
        root,
        manifest=source_result.manifest,
        enforce_artifact_hashes=False,
    )

    def fail_safety(observed: str) -> None:
        if observed == "during_container_write":
            raise RuntimeError("safety-backup")

    backup_service._fault_hook = fail_safety
    lock = RuntimeInstanceLock(root).acquire()
    with pytest.raises((FinalV4EncryptedBackupError, EncryptedBackupError)):
        prepare_final_v4_live_restore(
            backup_service=backup_service,
            lock=lock,
            staging_root=staging.staging_root,
            expected_container_sha256=source_result.container_sha256,
            restore_id=restore_id,
            app_version="0.0.test",
            build_commit="60650d5",
            source_tree_state="clean",
        )
    paths = restore_transaction_paths(root, restore_id)
    assert not paths.handoff.exists()
    assert not paths.transaction.exists()
    assert not (root / FINAL_V4_LIVE_RESTORE_BACKUP_DIRECTORY / f"safety-{restore_id}.jkmebackup").exists()
    backup_service._fault_hook = None
    assert backup_service.verify_live_runtime(
        root,
        manifest=source_result.manifest,
        enforce_artifact_hashes=False,
    ).manifest == before.manifest
    lock.release()


@requires_exact_417
@pytest.mark.parametrize("damage", ["ready", "container"])
def test_tampered_ready_or_missing_container_stops_before_handoff(
    tmp_path: Path,
    damage: str,
) -> None:
    runtime, backup_service, *_ = _open_case(tmp_path)
    _add_all_document_classes(runtime)
    source = tmp_path / "source.jkmebackup"
    source_result = backup_service.create(source)
    root = backup_service.paths.final_v4.key_runtime.root
    restore_id = str(uuid.uuid4())
    parent = root / FINAL_V4_LIVE_RESTORE_STAGING_DIRECTORY
    parent.mkdir(mode=0o700)
    staging = backup_service.restore_staging(source, parent / restore_id)
    if damage == "ready":
        ready_path = staging.ready_path
        payload = json.loads(ready_path.read_bytes())
        payload["active_document_count"] += 1
        ready_path.write_bytes(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        )
    else:
        next(backup_service.paths.storage_root.glob("*.jkmedoc"))
        staged_container = next(
            (staging.staging_root / backup_service.paths.container_root.relative_to(root)).glob(
                "storage/*.jkmedoc"
            )
        )
        staged_container.unlink()
    lock = RuntimeInstanceLock(root).acquire()
    with pytest.raises(FinalV4EncryptedBackupError):
        prepare_final_v4_live_restore(
            backup_service=backup_service,
            lock=lock,
            staging_root=staging.staging_root,
            expected_container_sha256=source_result.container_sha256,
            restore_id=restore_id,
            app_version="0.0.test",
            build_commit="60650d5",
            source_tree_state="clean",
        )
    paths = restore_transaction_paths(root, restore_id)
    assert not paths.transaction.exists()
    assert backup_service.opened.final_v4.database.maintenance_gate.state.value == "NORMAL"
    lock.release()


@requires_exact_417
def test_worker_revalidates_restore_ready_after_authenticated_handoff(
    tmp_path: Path,
) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    payload = json.loads(staging.ready_path.read_bytes())
    payload["total_document_generation_count"] += 1
    staging.ready_path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    )
    preparation.safety_backup.transfer_to_worker()

    with pytest.raises(RestorePreflightError):
        FinalV4EncryptedLiveRestoreService(backup_service).execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )

    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )
    assert RestoreJournal(paths).read()["phase"] == "aborted_before_replacement"
    assert not any(paths.rollback.iterdir())
    backup_service.verify_live_runtime(
        paths.runtime_root,
        manifest=preparation.safety_backup.result.manifest,
        enforce_artifact_hashes=False,
    )
    _assert_excluded(paths.runtime_root, excluded)
    lock.release()


@requires_exact_417
def test_wrong_dmk_rejects_authenticated_handoff_before_swap(tmp_path: Path) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()
    original_loaded = backup_service.loaded
    backup_service.loaded = replace(
        original_loaded,
        dmk=replace(original_loaded.dmk, key_material=secrets.token_bytes(32)),
    )
    with pytest.raises(RestoreHandoffError):
        FinalV4EncryptedLiveRestoreService(backup_service).execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=_restart_callback(backup_service),
            handshake_timeout_seconds=1.0,
        )
    backup_service.loaded = original_loaded
    backup_service.verify_live_runtime(
        backup_service.paths.final_v4.key_runtime.root,
        manifest=preparation.safety_backup.result.manifest,
        enforce_artifact_hashes=False,
    )
    _assert_excluded(backup_service.paths.final_v4.key_runtime.root, excluded)
    lock.release()


def test_worker_command_keeps_zip_default_and_adds_explicit_cipher_mode(
    tmp_path: Path,
) -> None:
    plan = RestoreWorkerLaunchPlan(("python", "worker"), tmp_path)
    arguments = {
        "handoff": tmp_path / "restore-handoffs" / "id.json",
        "nonce": "nonce",
        "lock_fd": 4,
        "ready_fd": 5,
        "parent_lifetime_fd": 6,
    }
    assert "--restore-mode" not in plan.command(**arguments)
    cipher = plan.command(
        **arguments,
        restore_mode=RESTORE_MODE_FINAL_V4_ENCRYPTED,
    )
    assert cipher[-2:] == ["--restore-mode", RESTORE_MODE_FINAL_V4_ENCRYPTED]


def test_cipher_worker_dispatch_never_falls_back_to_zip_v1(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "runtime"
    handoff_root = root / "restore-handoffs"
    handoff_root.mkdir(parents=True)
    handoff = handoff_root / f"{uuid.uuid4()}.json"
    handoff.write_text("{}", encoding="utf-8")
    calls: list[tuple[Path, str]] = []

    class CipherService:
        def execute(self, *, handoff_path, nonce, lock, worker_started):
            del lock, worker_started
            calls.append((handoff_path, nonce))

    def forbidden_zip_service():
        raise AssertionError("ZIP-v1 must not be composed in Cipher mode")

    monkeypatch.setattr(
        restore_worker,
        "ProductiveRestoreService",
        forbidden_zip_service,
    )
    result = restore_worker.run(
        [
            "--handoff",
            str(handoff),
            "--nonce",
            "authenticated-nonce",
            "--restore-mode",
            RESTORE_MODE_FINAL_V4_ENCRYPTED,
        ],
        encrypted_service_factory=lambda observed_root: (
            CipherService()
            if observed_root == root.resolve()
            else forbidden_zip_service()
        ),
    )
    assert result == EXIT_SUCCESS
    assert calls == [(handoff.resolve(), "authenticated-nonce")]


@requires_exact_417
def test_cipher_runtime_is_opened_only_after_worker_started_and_parent_eof(
    tmp_path: Path,
) -> None:
    (
        _runtime,
        backup_service,
        _source_result,
        _staging,
        preparation,
        lock,
        _excluded,
        _payloads,
        key_store,
        account_loader,
        provider,
    ) = _prepare_restore(tmp_path, include_bootstrap_context=True)
    preparation.safety_backup.transfer_to_worker()
    events: list[str] = []

    def open_cipher_runtime():
        assert events == ["worker_started_parent_eof"]
        opened = open_cipher_product_runtime(
            paths=runtime_paths(backup_service.paths.final_v4.key_runtime.root),
            account_loader=account_loader,
            authentication_confirmed=True,
            first_run_allowed=False,
            key_store=key_store,
            sqlcipher_provider=provider,
            active_restore_id=preparation.handoff.restore_id,
        )
        assert opened.database is opened.runtime.final_v4.database
        events.append("cipher_runtime_opened")
        return backup_service

    service = FinalV4EncryptedLiveRestoreService(
        None,
        handoff_service=FinalV4EncryptedRestoreHandoffService(backup_service),
        backup_service_factory=open_cipher_runtime,
    )

    def worker_started_and_parent_eof(_paths) -> None:
        assert service.backup_service is None
        events.append("worker_started_parent_eof")

    result = service.execute(
        handoff_path=preparation.handoff.path,
        nonce=preparation.handoff.nonce,
        lock=lock,
        worker_started=worker_started_and_parent_eof,
        restart=_restart_callback(backup_service),
        handshake_timeout_seconds=1.0,
    )
    assert result.status == "completed"
    assert events == ["worker_started_parent_eof", "cipher_runtime_opened"]
    lock.release()


def test_source_restart_command_reenters_normal_desktop_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    paths = restore_transaction_paths(root, str(uuid.uuid4()))
    lock = RuntimeInstanceLock(root).acquire()
    observed: dict[str, object] = {}
    sentinel = object()

    def fake_popen(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(final_v4_live_restore.subprocess, "Popen", fake_popen)
    result = FinalV4EncryptedLiveRestoreService._launch_restart(
        paths,
        "resume-token",
        lock,
    )
    assert result is sentinel
    command = observed["command"]
    assert command[:4] == [
        str(Path(sys.executable).resolve()),
        "-m",
        "src.desktop_app.main",
        "--final-v4-restore-confirm",
    ]
    assert command[command.index("--runtime-root") + 1] == str(root.resolve())
    assert command[command.index("--restore-id") + 1] == paths.transaction.name
    assert command[command.index("--restore-token") + 1] == "resume-token"
    assert command[command.index("--restore-lock-fd") + 1] == str(lock.fileno)
    assert observed["kwargs"]["pass_fds"] == (lock.fileno,)
    lock.release()


def test_restore_confirm_continues_into_regular_auth_and_product_startup() -> None:
    source = inspect.getsource(desktop_main.main)
    confirm = source.index("confirm_final_v4_restore_startup(")
    authentication = source.index("run_startup_authentication(")
    product = source.index("open_cipher_product_runtime(")
    application = source.index("JenaplanDesktopApp(")
    assert confirm < authentication < product < application
    assert "return run_confirm" not in source


@requires_exact_417
def test_real_worker_process_takes_over_after_parent_eof_and_completes_restore(
    tmp_path: Path,
) -> None:
    (
        _runtime,
        backup_service,
        source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()
    ready_read, ready_write = os.pipe()
    lifetime_read, lifetime_write = os.pipe()

    child = os.fork()
    if child == 0:  # pragma: no cover - asserted through persisted evidence
        os.close(ready_read)
        os.close(lifetime_write)
        channel = restore_worker._WorkerTakeoverChannel(ready_write, lifetime_read)
        try:
            result = FinalV4EncryptedLiveRestoreService(backup_service).execute(
                handoff_path=preparation.handoff.path,
                nonce=preparation.handoff.nonce,
                lock=lock,
                worker_started=channel.confirm_and_wait_for_parent_exit,
                restart=_restart_callback(backup_service),
                handshake_timeout_seconds=1.0,
            )
            os._exit(0 if result.status == "completed" else 2)
        except BaseException:
            os._exit(3)

    os.close(ready_write)
    os.close(lifetime_read)
    assert os.read(ready_read, 256) == restore_worker.WORKER_READY_MESSAGE
    os.close(ready_read)
    paths = restore_transaction_paths(
        backup_service.paths.final_v4.key_runtime.root,
        preparation.handoff.restore_id,
    )
    assert RestoreJournal(paths).read()["phase"] == "worker_started"
    lock.transfer()
    os.close(lifetime_write)
    waited, status = os.waitpid(child, 0)
    assert waited == child
    assert os.waitstatus_to_exitcode(status) == 0
    assert RestoreJournal(paths).read()["phase"] == "completed"
    assert backup_service.verify_live_runtime(
        paths.runtime_root,
        manifest=source_result.manifest,
    ).manifest == source_result.manifest
    _assert_excluded(paths.runtime_root, excluded)


@requires_exact_417
def test_interrupted_installed_state_resumes_only_after_fresh_keyed_reopen(
    tmp_path: Path,
) -> None:
    (
        _runtime,
        backup_service,
        source_result,
        _staging,
        preparation,
        lock,
        excluded,
        _payloads,
    ) = _prepare_restore(tmp_path)
    preparation.safety_backup.transfer_to_worker()

    class SimulatedProcessExit(BaseException):
        pass

    def stop_after_install(_paths, _token, _lock):
        raise SimulatedProcessExit()

    with pytest.raises(SimulatedProcessExit):
        FinalV4EncryptedLiveRestoreService(backup_service).execute(
            handoff_path=preparation.handoff.path,
            nonce=preparation.handoff.nonce,
            lock=lock,
            restart=stop_after_install,
            handshake_timeout_seconds=1.0,
        )
    lock.release()
    recovery = recover_interrupted_final_v4_restore(
        backup_service=backup_service,
        runtime_root=backup_service.paths.final_v4.key_runtime.root,
    )
    assert recovery.status == "resume_required"
    assert recovery.restore_id == preparation.handoff.restore_id
    assert recovery.resume_token
    confirmed = confirm_final_v4_restore_startup(
        backup_service=backup_service,
        runtime_root=backup_service.paths.final_v4.key_runtime.root,
        restore_id=recovery.restore_id,
        token=recovery.resume_token,
    )
    assert confirmed.status == "completed"
    backup_service.verify_live_runtime(
        backup_service.paths.final_v4.key_runtime.root,
        manifest=source_result.manifest,
    )
    _assert_excluded(backup_service.paths.final_v4.key_runtime.root, excluded)
