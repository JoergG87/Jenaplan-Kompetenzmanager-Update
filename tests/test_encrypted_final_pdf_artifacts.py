"""Qt-free security integration for final RPA/LCA PDF artifacts."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import date
import os
import subprocess
import sys
import uuid

import pytest

from src.core.learning_conference_pdf import LearningConferencePdfError
from src.core.learning_report_pdf import LearningReportPdfError
from src.core.records import seed_reference_data
from src.core.sqlite_store import SQLiteObservationRepository
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.security.final_v3_document_runtime import FinalV3DocumentRuntimeError
from src.security.final_v3_document_runtime import (
    FinalV3DocumentRuntimeDecisionState,
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
from tests import test_learning_conference_pdf as conference_pdf_tests
from tests import test_learning_report_pdf as report_pdf_tests


def _report_case() -> report_pdf_tests.LearningReportPdfTest:
    case = report_pdf_tests.LearningReportPdfTest(
        "test_pdf_is_generated_from_final_revision_and_registered"
    )
    case.setUp()
    return case


def _conference_case() -> conference_pdf_tests.LearningConferencePdfTest:
    case = conference_pdf_tests.LearningConferencePdfTest(
        "test_pdf_is_generated_from_completed_lcv_and_registered"
    )
    case.setUp()
    return case


def _adapter(case: object, runtime: object, *, fault_hook=None) -> StudentDesktopAdapter:
    return StudentDesktopAdapter(
        database=case.adapter.database,
        database_create_allowed=False,
        managed_document_store=runtime,
        managed_pdf_fault_hook=fault_hook,
    )


def _new_runtime(root: Path):
    root.mkdir(mode=0o700)
    return _runtime(root)


def _insert_competencies(database: object, *records: object) -> None:
    unique = {record.competency_id: record for record in records}
    with database.connect() as connection:
        with connection:
            connection.executemany(
                """
                INSERT INTO competencies (
                    competency_id, subject_id, subject_name, subject_full_name,
                    official_subject_name, school_context_name, grade_band,
                    label, description, learning_stage, learning_area,
                    competency_group, source_reference, catalog_status,
                    activation_group_key, sort_order, active,
                    catalog_default_active, is_core_subject
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        item.competency_id,
                        item.subject_id,
                        item.subject_name,
                        item.subject_full_name,
                        item.official_subject_name,
                        item.school_context_name,
                        item.grade_band,
                        item.label,
                        item.description,
                        item.learning_stage,
                        item.learning_area,
                        item.competency_group,
                        item.source_reference,
                        item.catalog_status,
                        item.activation_group_key,
                        item.sort_order,
                        int(item.active),
                        int(item.catalog_default_active),
                        int(item.is_core_subject),
                    )
                    for item in unique.values()
                ),
            )


def _read_report(adapter: StudentDesktopAdapter, artifact_id: str) -> bytes:
    consumer = _Consumer()
    adapter.read_learning_report_pdf_artifact(
        artifact_id=artifact_id,
        consumer=consumer,
    )
    assert consumer.started and consumer.finished and consumer.aborted is None
    return bytes(consumer.payload)


def _read_conference(adapter: StudentDesktopAdapter, artifact_id: str) -> bytes:
    consumer = _Consumer()
    adapter.read_learning_conference_pdf_artifact(
        artifact_id=artifact_id,
        consumer=consumer,
    )
    assert consumer.started and consumer.finished and consumer.aborted is None
    return bytes(consumer.payload)


def test_report_and_conference_use_same_store_without_plaintext_pdf(
    tmp_path: Path,
) -> None:
    runtime = _new_runtime(tmp_path / "cipher")
    report_case = _report_case()
    conference_case = _conference_case()
    try:
        report_adapter = _adapter(report_case, runtime)
        conference_adapter = _adapter(conference_case, runtime)
        report_revision = report_case._finalize()
        conference_revision = conference_case._complete()

        report = report_adapter.generate_learning_report_pdf(report_revision)
        conference = conference_adapter.generate_learning_conference_pdf(
            conference_revision
        )

        assert report.file_path == conference.file_path == ""
        assert _read_report(report_adapter, report.learning_report_pdf_artifact_id).startswith(
            b"%PDF-"
        )
        assert _read_conference(
            conference_adapter,
            conference.learning_conference_pdf_artifact_id,
        ).startswith(b"%PDF-")
        assert report_adapter._managed_document_store is runtime
        assert conference_adapter._managed_document_store is runtime

        containers = tuple(runtime.paths.storage_root.glob("*.jkmedoc"))
        assert len(containers) == 2
        assert not tuple(runtime.paths.container_root.rglob("*.pdf"))
        assert not tuple(runtime.paths.container_root.rglob("*.pdf.tmp"))
        storage_bytes = b"".join(path.read_bytes() for path in containers)
        assert b"%PDF-" not in storage_bytes
        assert report_case.student.display_name.encode("utf-8") not in storage_bytes
        assert conference_case.student.display_name.encode("utf-8") not in storage_bytes
        assert all(path.name.endswith(".jkmedoc") for path in containers)
        assert all("RPA-" not in path.name and "LCA-" not in path.name for path in containers)
    finally:
        report_case.tearDown()
        conference_case.tearDown()


def test_report_retry_restart_and_revision_binding(tmp_path: Path) -> None:
    case = _report_case()
    try:
        runtime = _new_runtime(tmp_path / "cipher")
        adapter = _adapter(case, runtime)
        revision_id = case._finalize()
        first = adapter.generate_learning_report_pdf(revision_id)
        retry = adapter.generate_learning_report_pdf(revision_id)
        assert retry == first

        restarted = _adapter(case, _reopen(runtime))
        loaded = restarted.load_learning_report_pdf_artifact(revision_id)
        assert loaded == first
        assert _read_report(restarted, first.learning_report_pdf_artifact_id).startswith(
            b"%PDF-"
        )
        with case.adapter.database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM learning_report_pdf_artifacts"
            ).fetchone()[0] == 1
        with sqlite3.connect(runtime.paths.database) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM final_v3_document_generations"
            ).fetchone()[0] == 1
    finally:
        case.tearDown()


@pytest.mark.parametrize(
    "phase",
    (
        "before_render",
        "after_pdf_stream",
        "after_container_prepare",
        "after_container_verification",
        "before_artifact_commit",
        "after_artifact_commit",
        "during_generation_activation",
        "after_activation_before_complete",
    ),
)
def test_report_retry_after_each_pdf_lifecycle_boundary(
    tmp_path: Path,
    phase: str,
) -> None:
    case = _report_case()
    try:
        runtime = _new_runtime(tmp_path / phase)
        revision_id = case._finalize()

        def fail(current: str) -> None:
            if current == phase:
                raise RuntimeError(f"fault:{phase}")

        with pytest.raises((RuntimeError, LearningReportPdfError)):
            _adapter(case, runtime, fault_hook=fail).generate_learning_report_pdf(
                revision_id
            )

        restarted = _adapter(case, _reopen(runtime))
        artifact = restarted.generate_learning_report_pdf(revision_id)
        assert _read_report(
            restarted, artifact.learning_report_pdf_artifact_id
        ).startswith(b"%PDF-")
        with case.adapter.database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM learning_report_pdf_artifacts"
            ).fetchone()[0] == 1
    finally:
        case.tearDown()


@pytest.mark.parametrize(
    "phase",
    (
        "before_render",
        "after_pdf_stream",
        "after_container_prepare",
        "after_container_verification",
        "before_artifact_commit",
        "after_artifact_commit",
        "during_generation_activation",
        "after_activation_before_complete",
    ),
)
def test_report_real_process_crash_restarts_without_duplicate_artifact(
    tmp_path: Path,
    phase: str,
) -> None:
    case = _report_case()
    try:
        runtime = _new_runtime(tmp_path / phase)
        revision_id = case._finalize()
        child = os.fork()
        if child == 0:
            def crash(current: str) -> None:
                if current == phase:
                    os._exit(73)

            _adapter(case, _reopen(runtime), fault_hook=crash).generate_learning_report_pdf(
                revision_id
            )
            os._exit(74)
        _pid, status = os.waitpid(child, 0)
        assert os.waitstatus_to_exitcode(status) == 73

        restarted = _adapter(case, _reopen(runtime))
        artifact = restarted.generate_learning_report_pdf(revision_id)
        assert _read_report(
            restarted, artifact.learning_report_pdf_artifact_id
        ).startswith(b"%PDF-")
        with case.adapter.database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM learning_report_pdf_artifacts"
            ).fetchone()[0] == 1
    finally:
        case.tearDown()


def test_wrong_dmk_context_tamper_and_missing_container_fail_closed(
    tmp_path: Path,
) -> None:
    case = _conference_case()
    try:
        runtime = _new_runtime(tmp_path / "cipher")
        adapter = _adapter(case, runtime)
        revision_id = case._complete()
        artifact = adapter.generate_learning_conference_pdf(revision_id)
        container = next(runtime.paths.storage_root.glob("*.jkmedoc"))

        with pytest.raises(FinalV3DocumentRuntimeError):
            _adapter(case, _reopen(runtime, loaded=_loaded(b"\x99" * 32)))
        with pytest.raises(FinalV3DocumentRuntimeError):
            _adapter(
                case,
                _reopen(
                    runtime,
                    installation_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                ),
            )

        original = container.read_bytes()
        changed = bytearray(original)
        changed[-1] ^= 1
        container.write_bytes(changed)
        with pytest.raises(FinalV3DocumentRuntimeError):
            _adapter(case, _reopen(runtime))

        container.write_bytes(original)
        container.unlink()
        with pytest.raises(FinalV3DocumentRuntimeError):
            _adapter(case, _reopen(runtime))

        assert artifact.learning_conference_revision_id == revision_id
    finally:
        case.tearDown()


def test_gate_off_does_not_import_or_use_managed_pdf_lifecycle(tmp_path: Path) -> None:
    report_case = _report_case()
    conference_case = _conference_case()
    try:
        report_revision = report_case._finalize()
        conference_revision = conference_case._complete()
        report = report_case.adapter.generate_learning_report_pdf(report_revision)
        conference = conference_case.adapter.generate_learning_conference_pdf(
            conference_revision
        )
        assert Path(report.file_path).is_file()
        assert Path(conference.file_path).is_file()
        assert not report.file_path.startswith("managed-document:")
        assert not conference.file_path.startswith("managed-document:")
        check = subprocess.run(
            (
                sys.executable,
                "-c",
                "import sys; import src.desktop_app.adapters.student_desktop_adapter; "
                "assert 'src.security.final_v3_document_runtime' not in sys.modules",
            ),
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        assert check.returncode == 0, check.stderr
    finally:
        report_case.tearDown()
        conference_case.tearDown()


@requires_exact_417
def test_exact_sqlcipher_report_and_conference_restart_read(tmp_path: Path) -> None:
    report_case = _report_case()
    conference_case = _conference_case()
    try:
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
            source_root=None,
        )
        assert first.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
        assert first.runtime is not None
        database = first.runtime.final_v4.database
        database.replace_seed_data(seed_reference_data())
        _insert_competencies(
            database,
            report_case.competency,
            conference_case.competency,
        )
        SQLiteObservationRepository(database).create_observation(report_case.observation)
        SQLiteObservationRepository(database).create_observation(
            conference_case.observation
        )
        adapter = StudentDesktopAdapter(
            database=database,
            database_create_allowed=False,
            today_provider=lambda: date(2026, 8, 9),
            managed_document_store=first.runtime.documents,
        )
        report_draft = adapter.save_learning_report_draft(report_case._draft())
        report_status = adapter.finalize_learning_report(
            report_draft.report_draft_id,
            "Laura Lernbegleiterin",
        )
        conference_draft = adapter.save_learning_conference_draft(
            conference_case._draft()
        )
        conference_status = adapter.complete_learning_conference(
            conference_draft.learning_conference_draft_id
        )
        conference_revision_id = next(
            item.learning_conference_revision_id
            for item in conference_status.revisions
            if item.status == "completed"
        )
        report = adapter.generate_learning_report_pdf(
            report_status.current_revision_id
        )
        conference = adapter.generate_learning_conference_pdf(
            conference_revision_id
        )

        restarted = run_gated_final_v4_document_runtime(
            account_loader=account,
            authentication_confirmed=True,
            environ=_environment(root),
            key_store=store,
            source_root=None,
        )
        assert restarted.state is FinalV3DocumentRuntimeDecisionState.ACTIVE
        assert restarted.runtime is not None
        restarted_adapter = StudentDesktopAdapter(
            database=restarted.runtime.final_v4.database,
            database_create_allowed=False,
            today_provider=lambda: date(2026, 8, 9),
            managed_document_store=restarted.runtime.documents,
        )
        assert _read_report(
            restarted_adapter, report.learning_report_pdf_artifact_id
        ).startswith(b"%PDF-")
        assert _read_conference(
            restarted_adapter,
            conference.learning_conference_pdf_artifact_id,
        ).startswith(b"%PDF-")
        assert not restarted.runtime.final_v4.database.path.read_bytes().startswith(
            b"SQLite format 3\x00"
        )
        assert not restarted.runtime.documents.paths.database.read_bytes().startswith(
            b"SQLite format 3\x00"
        )
    finally:
        report_case.tearDown()
        conference_case.tearDown()
