from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import secrets
import uuid

import pytest

from src.core.backup import BackupService
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCipherConnectionProvider,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.final_v3_backup_runtime import (
    FINAL_V3_BACKUP_MANIFEST_ENTRY_ID,
    FINAL_V3_RESTORE_READY_FILENAME,
    FinalV3EncryptedBackupError,
    FinalV3EncryptedBackupManifestV1,
    build_final_v3_encrypted_backup_service,
)
from src.security.final_v3_document_runtime import (
    FinalV3DocumentRuntimeDecisionState,
    run_gated_final_v3_document_runtime,
)
from tests.test_final_v3_sqlcipher_runtime import (
    MemoryDataMasterKeyStore,
    _account_loader,
    _environment,
    _root,
    requires_exact_417,
)


INSTALLATION_ID = "11111111-1111-4111-8111-111111111111"
STUDENT_ID = "STU-000001"
REPORT_DOCUMENT_ID = "22222222-2222-4222-8222-222222222222"
CONFERENCE_DOCUMENT_ID = "33333333-3333-4333-8333-333333333333"


def _open_case(tmp_path: Path, *, fault_hook=None):
    root = _root(tmp_path)
    environment = _environment(root)
    key_store = MemoryDataMasterKeyStore()
    account_loader = _account_loader(INSTALLATION_ID)
    provider = SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
    )
    decision = run_gated_final_v3_document_runtime(
        account_loader=account_loader,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        document_database_create_allowed=True,
        environ=environment,
        key_store=key_store,
        sqlcipher_provider=provider,
    )
    assert decision.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert decision.runtime is not None
    service = build_final_v3_encrypted_backup_service(
        opened_runtime=decision.runtime,
        account_loader=account_loader,
        environ=environment,
        key_store=key_store,
        sqlcipher_provider=provider,
        fault_hook=fault_hook,
    )
    return decision.runtime, service, key_store, environment, account_loader, provider


def _add_general_document(runtime, *, document_id: str, payload: bytes) -> None:
    _activate_document(runtime, document_id=document_id, payload=payload)
    with runtime.final_v3.database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT OR IGNORE INTO students (
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (?, 'Test', 'Kind', '', 1, ?, ?, NULL)
            """,
            (STUDENT_ID, "2026-08-09T10:00:00Z", "2026-08-09T10:00:00Z"),
        )
        connection.execute(
            """
            INSERT INTO documents (
                document_id, student_id, observation_id, title,
                document_type, file_path, original_filename, created_at,
                note, active
            ) VALUES (?, ?, NULL, 'Arbeitsprobe', 'general', '',
                      'vertraulich.txt', ?, '', 1)
            """,
            (document_id, STUDENT_ID, "2026-08-09T10:00:00Z"),
        )
        connection.commit()


def _activate_document(runtime, *, document_id: str, payload: bytes) -> None:
    prepared = runtime.documents.prepare_bytes(
        document_id=document_id,
        source_bytes=payload,
        original_filename="vertraulich.txt",
        mime_type="text/plain",
    )
    runtime.documents.activate(
        document_id=document_id,
        document_generation=prepared.document_generation,
    )


def _add_all_document_classes(runtime) -> dict[str, bytes]:
    payloads = {
        "MED-000001": b"Allgemeines Schuelerdokument mit Klartextinhalt",
        "MED-000002": b"Beobachtungsanhang mit vertraulichem Inhalt",
        REPORT_DOCUMENT_ID: b"%PDF-1.7\nVertraulicher Bericht\n%%EOF",
        CONFERENCE_DOCUMENT_ID: b"%PDF-1.7\nVertrauliches LEG\n%%EOF",
    }
    for document_id, payload in payloads.items():
        _activate_document(runtime, document_id=document_id, payload=payload)

    timestamp = "2026-08-09T10:00:00Z"
    report_snapshot = hashlib.sha256(b"report-snapshot").hexdigest()
    conference_snapshot = hashlib.sha256(b"conference-snapshot").hexdigest()
    with runtime.final_v3.database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT OR IGNORE INTO students (
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES (?, 'Test', 'Kind', '', 1, ?, ?, NULL)
            """,
            (STUDENT_ID, "2026-08-09T10:00:00Z", "2026-08-09T10:00:00Z"),
        )
        connection.execute(
            """
            INSERT INTO observations (
                observation_id, student_id, date, subject_id, context,
                note, active, created_at, updated_at
            ) VALUES ('OBS-000001', ?, '2026-08-09', 'DEU', '', '', 1, ?, ?)
            """,
            (STUDENT_ID, timestamp, timestamp),
        )
        connection.executemany(
            """
            INSERT INTO documents (
                document_id, student_id, observation_id, title,
                document_type, file_path, original_filename, created_at,
                note, active
            ) VALUES (?, ?, ?, ?, ?, '', ?, ?, '', 1)
            """,
            (
                (
                    "MED-000001", STUDENT_ID, None, "Arbeitsprobe", "general",
                    "arbeitsprobe.txt", timestamp,
                ),
                (
                    "MED-000002", STUDENT_ID, "OBS-000001", "Anhang",
                    "observation_attachment", "beobachtung.txt", timestamp,
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO report_drafts (
                report_draft_id, student_id, report_type, period_start,
                period_end, status, teacher_name, overall_text, created_at,
                updated_at
            ) VALUES ('RPD-000001', ?, 'learning_development', '2026-01-01',
                      '2026-06-30', 'draft', '', '', ?, ?)
            """,
            (STUDENT_ID, timestamp, timestamp),
        )
        connection.execute(
            """INSERT INTO learning_reports VALUES
            ('RPT-000001', 'RPD-000001', ?, 'learning_development',
             '2026-01-01', '2026-06-30', '2026-06-30')""",
            (STUDENT_ID,),
        )
        connection.execute(
            """INSERT INTO learning_report_revisions VALUES
            ('RPV-000001', 'RPT-000001', 1, 'finalized', 1, '{}', ?,
             '2026-06-30', 'Lehrkraft', NULL)""",
            (report_snapshot,),
        )
        connection.execute(
            """INSERT INTO learning_report_pdf_artifacts VALUES
            ('RPA-000001', 'RPV-000001', ?, 'application/pdf', ?, ?, ?, ?)""",
            (
                f"managed-document:{REPORT_DOCUMENT_ID}",
                len(payloads[REPORT_DOCUMENT_ID]),
                report_snapshot,
                hashlib.sha256(payloads[REPORT_DOCUMENT_ID]).hexdigest(),
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO learning_conference_drafts (
                learning_conference_draft_id, student_id, status,
                created_at, updated_at
            ) VALUES ('LCD-000001', ?, 'draft', ?, ?)
            """,
            (STUDENT_ID, timestamp, timestamp),
        )
        connection.execute(
            """INSERT INTO learning_conferences VALUES
            ('LCF-000001', 'LCD-000001', ?, '2026-06-30')""",
            (STUDENT_ID,),
        )
        connection.execute(
            """INSERT INTO learning_conference_revisions VALUES
            ('LCV-000001', 'LCF-000001', 1, 'completed', 1, '{}', ?,
             '2026-06-30', 'Lehrkraft', NULL)""",
            (conference_snapshot,),
        )
        connection.execute(
            """INSERT INTO learning_conference_pdf_artifacts VALUES
            ('LCA-000001', 'LCV-000001', ?, 'application/pdf', ?, ?, ?, ?)""",
            (
                f"managed-document:{CONFERENCE_DOCUMENT_ID}",
                len(payloads[CONFERENCE_DOCUMENT_ID]),
                conference_snapshot,
                hashlib.sha256(payloads[CONFERENCE_DOCUMENT_ID]).hexdigest(),
                timestamp,
            ),
        )
        connection.commit()
    return payloads


@requires_exact_417
def test_create_verify_restart_restore_ready_and_same_installation_metadata(
    tmp_path: Path,
) -> None:
    runtime, service, key_store, environment, account_loader, provider = _open_case(
        tmp_path
    )
    payload = b"Laura vertraulicher Lernstand ohne Klartextbackup"
    _add_general_document(runtime, document_id="MED-000001", payload=payload)
    target = tmp_path / "pilot.jkmebackup"

    created = service.create(target)
    repeated = service.verify(target)

    assert repeated.container_sha256 == created.container_sha256
    assert repeated.manifest == created.manifest
    assert repeated.manifest.active_document_ids == ("MED-000001",)
    assert len(repeated.manifest.documents) == 1
    assert repeated.manifest.database_key_rewrap_revision >= 1
    assert {item.role.value for item in repeated.manifest.artifacts} == {
        "final_v3_main_database",
        "document_companion_database",
        "keyset_metadata",
        "database_key_envelope_registry",
    }
    raw = target.read_bytes()
    assert payload not in raw
    assert b"SQLite format 3" not in raw
    assert b"%PDF-" not in raw
    assert service.loaded.dmk.key_material not in raw
    assert service.loaded.database_key.key_material not in raw

    restarted = run_gated_final_v3_document_runtime(
        account_loader=account_loader,
        authentication_confirmed=True,
        technical_first_run_confirmed=False,
        document_database_create_allowed=False,
        environ=environment,
        key_store=key_store,
        sqlcipher_provider=provider,
    )
    assert restarted.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
    assert restarted.runtime is not None
    restarted_service = build_final_v3_encrypted_backup_service(
        opened_runtime=restarted.runtime,
        account_loader=account_loader,
        environ=environment,
        key_store=key_store,
        sqlcipher_provider=provider,
    )
    assert restarted_service.verify(target).container_sha256 == created.container_sha256

    restored = restarted_service.restore_staging(
        target, tmp_path / "restore-staging"
    )
    assert restored.state == "RESTORE_READY"
    assert restored.active_document_count == 1
    assert restored.total_document_generation_count == 1
    assert restored.ready_path.name == FINAL_V3_RESTORE_READY_FILENAME
    assert restored.ready_path.is_file()
    assert restored.staging_root.stat().st_mode & 0o077 == 0
    ready = json.loads(restored.ready_path.read_text(encoding="ascii"))
    assert ready["state"] == "RESTORE_READY"
    assert ready["manifest_sha256"] == hashlib.sha256(
        repeated.manifest.to_bytes()
    ).hexdigest()
    assert runtime.final_v3.database.path.is_file()
    staged_manifest = (
        restored.staging_root / "final-v3-backup-manifest-v1.json"
    ).read_bytes()
    for secret in (
        service.loaded.dmk.key_material,
        service.loaded.database_key.key_material,
        payload,
    ):
        assert secret not in staged_manifest
        assert secret.hex().encode("ascii") not in staged_manifest
    assert b"password" not in staged_manifest.lower()
    assert b"recovery_code" not in staged_manifest.lower()
    assert b"security.sqlite" not in staged_manifest.lower()


@requires_exact_417
def test_retained_generations_are_preserved_but_active_inventory_is_exact(
    tmp_path: Path,
) -> None:
    runtime, service, *_rest = _open_case(tmp_path)
    _add_general_document(runtime, document_id="MED-000001", payload=b"old")
    plan = runtime.documents.plan_prepare(document_id="MED-000001")
    runtime.documents.prepare_bytes(
        document_id="MED-000001",
        source_bytes=b"new",
        original_filename="new.txt",
        mime_type="text/plain",
        plan=plan,
    )
    runtime.documents.activate(
        document_id="MED-000001",
        document_generation=plan.document_generation,
    )

    result = service.create(tmp_path / "generations.jkmebackup")
    restored = service.restore_staging(
        result.path, tmp_path / "generation-staging"
    )

    assert [item.lifecycle_status for item in result.manifest.documents] == [
        "RETAINED",
        "ACTIVE",
    ]
    assert result.manifest.active_document_ids == ("MED-000001",)
    assert restored.active_document_count == 1
    assert restored.total_document_generation_count == 2


@requires_exact_417
def test_inventory_includes_general_attachment_report_and_conference_pdf(
    tmp_path: Path,
) -> None:
    runtime, service, *_rest = _open_case(tmp_path)
    payloads = _add_all_document_classes(runtime)

    result = service.create(tmp_path / "complete-inventory.jkmebackup")
    restored = service.restore_staging(
        result.path, tmp_path / "complete-inventory-staging"
    )

    assert set(result.manifest.active_document_ids) == set(payloads)
    assert len(result.manifest.documents) == 4
    assert restored.active_document_count == 4
    assert restored.total_document_generation_count == 4
    outer = result.path.read_bytes()
    assert b"%PDF-" not in outer
    assert all(payload not in outer for payload in payloads.values())


@requires_exact_417
def test_wrong_dmk_context_existing_targets_and_plaintext_reference_fail_closed(
    tmp_path: Path,
) -> None:
    runtime, service, *_rest = _open_case(tmp_path)
    _add_general_document(runtime, document_id="MED-000001", payload=b"secret")
    target = tmp_path / "protected.jkmebackup"
    created = service.create(target)
    before = target.read_bytes()

    with pytest.raises(FinalV3EncryptedBackupError, match="backup_target_exists"):
        service.create(target)
    assert target.read_bytes() == before

    wrong_loaded = replace(
        service.loaded,
        dmk=LoadedDataMasterKey(
            service.loaded.dmk_key_id,
            service.loaded.dmk_generation,
            secrets.token_bytes(32),
        ),
    )
    wrong = replace_service_loaded(service, wrong_loaded)
    with pytest.raises(Exception) as wrong_dmk:
        wrong.verify(created.path)
    error_text = repr(wrong_dmk.value)
    assert service.loaded.dmk.key_material.hex() not in error_text
    assert wrong_loaded.dmk.key_material.hex() not in error_text
    assert str(created.path) not in error_text

    wrong_context = replace(
        service.context,
        database_context_id="44444444-4444-4444-8444-444444444444",
    )
    with pytest.raises(Exception):
        service._container_service().verify_path(
            container=created.path,
            dmk=service.loaded.dmk,
            context=wrong_context,
        )

    existing_staging = tmp_path / "existing-staging"
    existing_staging.mkdir()
    (existing_staging / "sentinel").write_bytes(b"unchanged")
    with pytest.raises(FinalV3EncryptedBackupError, match="restore_staging_exists"):
        service.restore_staging(target, existing_staging)
    assert (existing_staging / "sentinel").read_bytes() == b"unchanged"

    with runtime.final_v3.database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE documents SET file_path = '/tmp/plain.txt' WHERE document_id = ?",
            ("MED-000001",),
        )
        connection.commit()
    with pytest.raises(
        FinalV3EncryptedBackupError,
        match="unexpected_plaintext_document_reference",
    ):
        service.create(tmp_path / "plaintext-rejected.jkmebackup")


@requires_exact_417
@pytest.mark.parametrize("damage", ("tamper", "truncate", "trailing"))
def test_container_damage_fails_without_changing_valid_backup(
    tmp_path: Path,
    damage: str,
) -> None:
    runtime, service, *_rest = _open_case(tmp_path)
    _add_general_document(runtime, document_id="MED-000001", payload=b"secret")
    valid = tmp_path / "valid.jkmebackup"
    service.create(valid)
    original = valid.read_bytes()
    damaged = tmp_path / f"damaged-{damage}.jkmebackup"
    if damage == "tamper":
        changed = bytearray(original)
        changed[len(changed) // 2] ^= 1
        damaged.write_bytes(changed)
    elif damage == "truncate":
        damaged.write_bytes(original[:-1])
    else:
        damaged.write_bytes(original + b"unexpected")

    with pytest.raises(Exception):
        service.verify(damaged)
    assert valid.read_bytes() == original
    assert service.verify(valid).container_sha256 == hashlib.sha256(
        original
    ).hexdigest()


@requires_exact_417
def test_backup_builder_never_recreates_missing_key_metadata(
    tmp_path: Path,
) -> None:
    runtime, service, key_store, environment, account_loader, provider = _open_case(
        tmp_path
    )
    keyset = service.paths.final_v3.key_runtime.keyset_metadata
    keyset.unlink()

    with pytest.raises(
        FinalV3EncryptedBackupError,
        match="final_v3_backup_key_runtime_incomplete",
    ):
        build_final_v3_encrypted_backup_service(
            opened_runtime=runtime,
            account_loader=account_loader,
            environ=environment,
            key_store=key_store,
            sqlcipher_provider=provider,
        )
    assert not keyset.exists()


def replace_service_loaded(service, loaded):
    from src.security.final_v3_backup_runtime import FinalV3EncryptedBackupService

    return FinalV3EncryptedBackupService(
        opened_runtime=service.opened,
        paths=service.paths,
        loaded_keys=loaded,
        main_factory=service._main_factory,
        document_factory=service._document_factory,
        provider=service._provider,
        maintenance_gate=service._gate,
        random_source=service._random,
        clock=service._clock,
    )


@requires_exact_417
@pytest.mark.parametrize(
    "boundary",
    [
        "before_snapshot",
        "during_main_database_snapshot",
        "during_companion_snapshot",
        "during_document_inventory",
        "during_container_write",
        "after_write_before_verification",
        "after_verification_before_publication",
    ],
)
def test_backup_fault_boundaries_leave_no_published_target_and_retry(
    tmp_path: Path,
    boundary: str,
) -> None:
    fired = False

    def fault(observed: str) -> None:
        nonlocal fired
        if observed == boundary and not fired:
            fired = True
            raise FinalV3EncryptedBackupError("injected_backup_fault")

    runtime, failing, key_store, environment, account_loader, provider = _open_case(
        tmp_path, fault_hook=fault
    )
    _add_general_document(runtime, document_id="MED-000001", payload=b"retry")
    target = tmp_path / f"fault-{boundary}.jkmebackup"
    with pytest.raises(Exception):
        failing.create(target)
    assert fired
    assert not target.exists()
    retry = build_final_v3_encrypted_backup_service(
        opened_runtime=runtime,
        account_loader=account_loader,
        environ=environment,
        key_store=key_store,
        sqlcipher_provider=provider,
    )
    assert retry.create(target).path == target


@requires_exact_417
@pytest.mark.parametrize(
    "boundary",
    [
        "during_restore_extraction",
        "after_extraction_before_reopen",
        "after_reopen_before_restore_ready",
    ],
)
def test_restore_fault_boundaries_never_publish_restore_ready(
    tmp_path: Path,
    boundary: str,
) -> None:
    runtime, service, key_store, environment, account_loader, provider = _open_case(
        tmp_path
    )
    _add_general_document(runtime, document_id="MED-000001", payload=b"restore")
    target = tmp_path / "restore-fault-source.jkmebackup"
    service.create(target)

    fired = False

    def fault(observed: str) -> None:
        nonlocal fired
        if observed == boundary and not fired:
            fired = True
            raise FinalV3EncryptedBackupError("injected_restore_fault")

    failing = build_final_v3_encrypted_backup_service(
        opened_runtime=runtime,
        account_loader=account_loader,
        environ=environment,
        key_store=key_store,
        sqlcipher_provider=provider,
        fault_hook=fault,
    )
    staging = tmp_path / f"restore-{boundary}"
    with pytest.raises(Exception):
        failing.restore_staging(target, staging)
    assert fired
    assert not (staging / FINAL_V3_RESTORE_READY_FILENAME).exists()
    assert service.verify(target).container_sha256 == hashlib.sha256(
        target.read_bytes()
    ).hexdigest()
    retried = service.restore_staging(
        target,
        tmp_path / f"restore-{boundary}-retry",
    )
    assert retried.state == "RESTORE_READY"


def test_gate_off_zip_v1_modules_do_not_import_cipher_backup_runtime() -> None:
    repository = Path(__file__).resolve().parents[1]
    for relative in (
        "src/core/backup.py",
        "src/core/restore.py",
        "src/core/restore_runtime.py",
        "src/desktop_app/adapters/backup_restore_desktop_adapter.py",
    ):
        assert "final_v3_backup_runtime" not in (
            repository / relative
        ).read_text(encoding="utf-8")
    assert BackupService is not None


def test_manifest_is_strict_and_contains_no_secret_fields() -> None:
    source = Path(__file__).resolve().parents[1] / "src/security/final_v3_backup_runtime.py"
    text = source.read_text(encoding="utf-8")
    forbidden = (
        '"password"',
        '"recovery_code"',
        '"security.sqlite"',
        '"dmk_material"',
        '"database_key_material"',
    )
    assert not any(value in text for value in forbidden)
    assert FINAL_V3_BACKUP_MANIFEST_ENTRY_ID.startswith("00000000-")
