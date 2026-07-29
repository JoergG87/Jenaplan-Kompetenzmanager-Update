from __future__ import annotations

from importlib.util import find_spec
import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

import pytest

from src.core.database_engine import SQLCipherConnectionProvider
from src.core.final_v3_schema import FinalV3SchemaInitializer
from src.core.sqlite_store import SQLiteDatabase
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import DatabaseKey
from src.security.infrastructure.system import SystemClock, SystemRandomSource
from src.security.integration_gate import (
    SecurityIntegrationError,
    SecurityIntegrationGate,
    SecurityIntegrationGateState,
)
from src.security.integration_orchestrator import (
    SecurityIntegrationOrchestrator,
    SecurityIntegrationPhase,
    prepare_security_integration_test_layout,
)
from src.security.migration_lock import ExclusiveMigrationLock


pytestmark = pytest.mark.skipif(
    find_spec("sqlcipher3") is None,
    reason="real SQLCipher is required for Security Sprint 11",
)


PAYLOAD = b"sprint-11-controlled-document-payload\n" * 257


def _id(root: Path, role: str) -> str:
    value = bytearray(
        hashlib.sha256(f"{role}:{root.name}".encode("ascii")).digest()[:16]
    )
    value[6] = (value[6] & 0x0F) | 0x40
    value[8] = (value[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(value)))


def _keys(root: Path) -> tuple[LoadedDataMasterKey, DatabaseKey]:
    return (
        LoadedDataMasterKey(
            _id(root, "dmk"),
            1,
            hashlib.sha256(
                f"sprint11-test-dmk:{root.name}".encode("ascii")
            ).digest(),
        ),
        DatabaseKey(
            _id(root, "database-key"),
            1,
            hashlib.sha256(
                f"sprint11-test-database-key:{root.name}".encode("ascii")
            ).digest(),
        ),
    )


def _environment(root: Path) -> dict[str, str]:
    return {
        "JKM_SECURITY_INTEGRATION_TEST": "1",
        "JKM_SECURITY_INTEGRATION_ROOT": str(root),
    }


def _prepare_plaintext_installation(tmp_path: Path) -> Path:
    root = tmp_path / f"jkm-security-integration-{uuid.uuid4()}"
    paths = prepare_security_integration_test_layout(
        root=root,
        environ=_environment(root),
    )
    document_path = paths.source_documents / "legacy-report.pdf"
    document_path.write_bytes(PAYLOAD)
    os.chmod(document_path, 0o600)
    FinalV3SchemaInitializer().initialize(paths.source_database)
    database = SQLiteDatabase(
        paths.source_database,
        create=False,
        initialize_schema=False,
    )
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO groups (group_id, group_name, sort_order, active)
            VALUES ('G-1', 'Testgruppe', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO courses (
                course_id, course_name, color_key, color_name, color_hex,
                sort_order, active, year_level
            )
            VALUES ('C-1', 'Testkurs', '', '', '', 1, 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES (
                'SY-TEST', '2025/26', '2025-08-01', '2026-07-31',
                'current', '2025-07-01T10:00:00+00:00', NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO students (
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            )
            VALUES (
                'S-1', 'Fiktiv', 'Testkind', '', 1,
                '2026-07-26T10:00:00+00:00',
                '2026-07-26T10:00:00+00:00',
                NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO student_school_year_assignments(
                assignment_id, student_id, school_year_id, group_id,
                course_id, assignment_status, valid_from, valid_to,
                created_at, updated_at
            ) VALUES (
                'ASG-TEST', 'S-1', 'SY-TEST', 'G-1', 'C-1', 'enrolled',
                '2025-08-01', '2026-07-31',
                '2025-07-01T10:00:00+00:00',
                '2025-07-01T10:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO documents (
                document_id, student_id, observation_id, title,
                document_type, file_path, original_filename, created_at,
                note, active
            )
            VALUES (
                'DOC-LEGACY-1', 'S-1', NULL, 'Lernbericht', 'Bericht',
                ?, 'Lernbericht Fiktiv.pdf',
                '2026-07-26T10:00:00+00:00', '', 1
            )
            """,
            (str(document_path),),
        )
        connection.commit()
    os.chmod(paths.source_database, 0o600)
    return root


def _orchestrator(
    root: Path,
    *,
    dmk: LoadedDataMasterKey | None = None,
    database_key: DatabaseKey | None = None,
    fault=None,
) -> SecurityIntegrationOrchestrator:
    expected_dmk, expected_database_key = _keys(root)
    dmk = dmk or expected_dmk
    database_key = database_key or expected_database_key
    return SecurityIntegrationOrchestrator.from_environment(
        environ=_environment(root),
        installation_id=_id(root, "installation"),
        database_context_id=_id(root, "database"),
        migration_id=_id(root, "migration"),
        migration_generation=1,
        dmk_loader=lambda: dmk,
        database_key_loader=lambda _observed_dmk: database_key,
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        sqlcipher_provider=SQLCipherConnectionProvider(),
        app_instance_available=lambda: True,
        source_closed_probe=lambda _path: True,
        app_version="sprint11-integration-test",
        fault_injector=fault,
    )


class _ByteConsumer:
    def __init__(self) -> None:
        self.payload = bytearray()
        self.finished = False
        self.aborted: str | None = None

    def start(self, _manifest) -> None:
        return None

    def write(self, chunk: bytes) -> None:
        self.payload.extend(chunk)

    def finish(self, _result) -> None:
        self.finished = True

    def abort(self, code: str) -> None:
        self.aborted = code


def test_gate_is_disabled_by_default_and_rejects_unknown_value(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "jkm-security-integration-not-created"
    disabled = SecurityIntegrationGate().resolve({})
    blocked = SecurityIntegrationGate().resolve(
        {
            "JKM_SECURITY_INTEGRATION_TEST": "yes",
            "JKM_SECURITY_INTEGRATION_ROOT": str(missing),
        }
    )
    assert disabled.state is SecurityIntegrationGateState.DISABLED
    assert blocked.state is SecurityIntegrationGateState.BLOCKED
    assert not missing.exists()


def test_disabled_gate_does_not_touch_an_existing_completed_test_stock(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    _orchestrator(root).run()
    before = {
        path.relative_to(root): (path.stat().st_mtime_ns, path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }

    decision = SecurityIntegrationGate().resolve(
        {"JKM_SECURITY_INTEGRATION_ROOT": str(root)}
    )

    assert decision.state is SecurityIntegrationGateState.DISABLED
    after = {
        path.relative_to(root): (path.stat().st_mtime_ns, path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_gate_rejects_symlink_and_noncanonical_root_paths(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    symlink = tmp_path / f"jkm-security-integration-{uuid.uuid4()}"
    symlink.symlink_to(root, target_is_directory=True)

    symlink_decision = SecurityIntegrationGate().resolve(
        _environment(symlink)
    )
    noncanonical_decision = SecurityIntegrationGate().resolve(
        _environment(root / ".." / root.name)
    )

    assert symlink_decision.state is SecurityIntegrationGateState.BLOCKED
    assert noncanonical_decision.state is SecurityIntegrationGateState.BLOCKED


def test_complete_gate_bound_migration_documents_backup_runtime_and_restore(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    paths = SecurityIntegrationGate().require_active(_environment(root))
    source_before = paths.source_database.read_bytes()

    orchestrator = _orchestrator(root)
    assert orchestrator.preflight().phase is SecurityIntegrationPhase.PREFLIGHT
    report = orchestrator.run()

    assert report.phase is SecurityIntegrationPhase.COMPLETED
    assert report.document_count == 1
    assert report.source_retained
    assert report.reopened
    assert paths.source_database.read_bytes() == source_before
    assert paths.safety_copy.read_bytes() == source_before
    assert paths.encrypted_database.read_bytes()[:16] != b"SQLite format 3\x00"
    assert PAYLOAD not in paths.encrypted_backup.read_bytes()
    containers = tuple(
        path
        for path in paths.document_storage.iterdir()
        if path.suffix == ".jkmedoc"
    )
    assert len(containers) == 1
    assert PAYLOAD not in containers[0].read_bytes()

    runtime = _orchestrator(root).open_runtime()
    assert runtime.student_count() == 1
    consumer = _ByteConsumer()
    runtime.documents.stream_active("DOC-LEGACY-1", consumer)
    assert bytes(consumer.payload) == PAYLOAD
    assert consumer.finished and consumer.aborted is None
    exported = runtime.documents.export_active(
        "DOC-LEGACY-1",
        "bewusster-export.pdf",
    )
    assert exported.export_path.read_bytes() == PAYLOAD
    assert "unverschlüsselt" in exported.warning
    with pytest.raises(Exception):
        runtime.documents.export_active(
            "DOC-LEGACY-1",
            "bewusster-export.pdf",
        )

    after_export = _orchestrator(root).preflight()
    assert after_export.phase is SecurityIntegrationPhase.COMPLETED, after_export
    restored = _orchestrator(root).restore_verified_backup(
        "restore-roundtrip"
    )
    assert restored.database_verified
    assert restored.document_count == 1
    assert restored.restore.completion_path.is_file()
    assert _orchestrator(root).preflight().phase is SecurityIntegrationPhase.COMPLETED
    assert not tuple(root.glob("*.jkmbackup"))


def test_document_replacement_is_verified_before_atomic_pointer_switch(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    _orchestrator(root).run()
    paths = SecurityIntegrationGate().require_active(_environment(root))
    replacement_payload = b"verified replacement payload\n" * 193
    replacement_source = paths.source_documents / "replacement.pdf"
    replacement_source.write_bytes(replacement_payload)
    os.chmod(replacement_source, 0o600)

    writer = _orchestrator(root).open_document_writer()
    prepared = writer.prepare_replacement(
        source_document_id="DOC-LEGACY-1",
        source_name=replacement_source.name,
        original_filename="Lernbericht Fiktiv neu.pdf",
        mime_type="application/pdf",
        storage_id=_id(root, "replacement-storage"),
    )
    assert prepared.document_generation == 2
    assert prepared.lifecycle_status == "PREPARED"
    assert (
        writer.prepare_replacement(
            source_document_id="DOC-LEGACY-1",
            source_name=replacement_source.name,
            original_filename="Lernbericht Fiktiv neu.pdf",
            mime_type="application/pdf",
            storage_id=_id(root, "replacement-storage"),
        )
        == prepared
    )
    before_switch = _ByteConsumer()
    writer.stream_active("DOC-LEGACY-1", before_switch)
    assert bytes(before_switch.payload) == PAYLOAD

    active = writer.activate_replacement(prepared)
    assert active.document_generation == 2
    assert active.lifecycle_status == "ACTIVE"
    after_switch = _ByteConsumer()
    writer.stream_active("DOC-LEGACY-1", after_switch)
    assert bytes(after_switch.payload) == replacement_payload
    with writer.factory.open_existing() as connection:
        rows = connection.execute(
            """
            SELECT document_generation, lifecycle_status
            FROM security_document_generations
            WHERE source_document_id = 'DOC-LEGACY-1'
            ORDER BY document_generation
            """
        ).fetchall()
        pointer = connection.execute(
            """
            SELECT file_path, original_filename
            FROM documents
            WHERE document_id = 'DOC-LEGACY-1'
            """
        ).fetchone()
    assert tuple(tuple(row) for row in rows) == (
        (1, "RETAINED"),
        (2, "ACTIVE"),
    )
    assert pointer["file_path"].endswith(
        f"{active.storage_id}/{active.document_generation}"
    )
    assert pointer["original_filename"] == "Lernbericht Fiktiv neu.pdf"
    with pytest.raises(
        SecurityIntegrationError,
        match="security_integration_document_delete_deferred",
    ):
        writer.delete_active("DOC-LEGACY-1")
    containers = tuple(
        path.read_bytes()
        for path in paths.document_storage.iterdir()
        if path.suffix == ".jkmedoc"
    )
    assert len(containers) == 2
    assert all(PAYLOAD not in payload for payload in containers)
    assert all(replacement_payload not in payload for payload in containers)


@pytest.mark.parametrize(
    "crash_point",
    (
        "initial_after_journal_publish",
        "initial_after_anchor_publish",
        "transition_after_anchor_prepare",
        "transition_after_journal_publish",
        "safety_copy_after_publish",
        "phase_backup_verified_committed",
        "phase_database_migrated_committed",
        "documents_after_prepared_generation",
        "phase_documents_prepared_committed",
        "phase_references_switched_committed",
        "phase_encrypted_backup_verified_committed",
        "phase_reopen_verified_committed",
        "phase_completed_committed",
    ),
)
def test_real_process_crash_recovers_idempotently(
    tmp_path: Path,
    crash_point: str,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "tests/helpers/sprint11_integration_crash_worker.py",
            str(root),
            crash_point,
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 91
    assert result.stdout == ""
    assert result.stderr == ""
    recovered = _orchestrator(root).recover()
    assert recovered.phase is SecurityIntegrationPhase.COMPLETED
    assert _orchestrator(root).recover() == recovered


def test_wrong_or_missing_keys_and_tampered_document_block_without_fallback(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    orchestrator = _orchestrator(root)
    orchestrator.run()
    dmk, database_key = _keys(root)
    wrong_database_key = DatabaseKey(
        database_key.key_id,
        database_key.generation,
        secrets.token_bytes(32),
    )
    assert (
        _orchestrator(
            root,
            database_key=wrong_database_key,
        ).preflight().phase
        is SecurityIntegrationPhase.BLOCKED
    )
    wrong_dmk = LoadedDataMasterKey(
        dmk.key_id,
        dmk.generation,
        secrets.token_bytes(32),
    )
    assert (
        _orchestrator(
            root,
            dmk=wrong_dmk,
        ).preflight().phase
        is SecurityIntegrationPhase.BLOCKED
    )
    paths = SecurityIntegrationGate().require_active(_environment(root))
    container = next(
        path
        for path in paths.document_storage.iterdir()
        if path.suffix == ".jkmedoc"
    )
    payload = bytearray(container.read_bytes())
    payload[-1] ^= 0x01
    container.write_bytes(payload)
    assert (
        _orchestrator(root).preflight().phase
        is SecurityIntegrationPhase.BLOCKED
    )


@pytest.mark.parametrize(
    "artifact_name",
    ("integration.sqlcipher", "integration.jkmebackup"),
)
def test_database_or_backup_exchange_blocks_without_source_loss(
    tmp_path: Path,
    artifact_name: str,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    paths = SecurityIntegrationGate().require_active(_environment(root))
    source_before = paths.source_database.read_bytes()
    _orchestrator(root).run()
    artifact = root / artifact_name
    changed = bytearray(artifact.read_bytes())
    changed[-1] ^= 0x01
    artifact.write_bytes(changed)

    preflight = _orchestrator(root).preflight()

    assert preflight.phase is SecurityIntegrationPhase.BLOCKED
    assert paths.source_database.read_bytes() == source_before
    assert paths.safety_copy.read_bytes() == source_before


def test_unknown_plaintext_in_managed_storage_is_a_blocking_mixed_state(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    paths = SecurityIntegrationGate().require_active(_environment(root))
    _orchestrator(root).run()
    known_storage_id = next(
        path.name.split(".", 1)[0]
        for path in paths.document_storage.iterdir()
        if path.suffix == ".jkmedoc"
    )
    unexpected = paths.document_storage / (
        f"unexpected-{known_storage_id}-plaintext.txt"
    )
    unexpected.write_bytes(b"must never be accepted")

    preflight = _orchestrator(root).preflight()

    assert preflight.phase is SecurityIntegrationPhase.BLOCKED
    assert unexpected.read_bytes() == b"must never be accepted"


def test_parallel_second_instance_is_blocked_without_lock_takeover(
    tmp_path: Path,
) -> None:
    root = _prepare_plaintext_installation(tmp_path)
    lock = ExclusiveMigrationLock(
        root,
        installation_id=_id(root, "installation"),
        database_context_id=_id(root, "database"),
        migration_id=_id(root, "migration"),
        allowed_root=root,
    )
    lock.acquire()
    try:
        with pytest.raises(Exception, match="migration_lock_busy"):
            _orchestrator(root).run()
    finally:
        lock.release()
    assert _orchestrator(root).run().phase is SecurityIntegrationPhase.COMPLETED


def test_normal_startup_import_does_not_import_or_activate_integration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import src.desktop_app.main; "
                "assert 'src.security.integration_orchestrator' "
                "not in sys.modules"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            key: value
            for key, value in os.environ.items()
            if key
            not in {
                "JKM_SECURITY_INTEGRATION_TEST",
                "JKM_SECURITY_INTEGRATION_ROOT",
            }
        },
    )
    assert result.returncode == 0, result.stderr
