"""Focused SJ-3C.3 maintenance-gate and productive-writer coverage."""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from src.core.maintenance_gate import (
    MaintenanceCapabilityError,
    MaintenanceGate,
    MaintenancePurpose,
    MaintenanceState,
    MaintenanceWriterBlockedError,
)
from src.core.observation_uow import ObservationPersistenceUnitOfWork
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import (
    StudentDesktopAdapter,
)
from src.desktop_app.adapters.timetable_desktop_adapter import (
    TimetableDesktopAdapter,
)
from tests.helpers.synthetic_v4 import create_synthetic_v4_database


OWNER = "school-year-maintenance"
PRODUCT_TABLES = frozenset(
    {
        "competencies",
        "course_group_courses",
        "course_group_student_groups",
        "course_groups",
        "courses",
        "documentation_subject_settings",
        "documents",
        "groups",
        "learning_conference_draft_charts",
        "learning_conference_draft_competencies",
        "learning_conference_draft_cross_topics",
        "learning_conference_draft_observations",
        "learning_conference_draft_subjects",
        "learning_conference_drafts",
        "learning_conference_pdf_artifacts",
        "learning_conference_revisions",
        "learning_conferences",
        "learning_report_pdf_artifacts",
        "learning_report_revisions",
        "learning_reports",
        "observation_competency_ratings",
        "observations",
        "persistence_events",
        "report_draft_charts",
        "report_draft_competencies",
        "report_draft_observations",
        "report_draft_subjects",
        "report_drafts",
        "school_year_transitions",
        "school_years",
        "student_competency_confirmations",
        "student_documentation_subject_profiles",
        "student_documentation_subject_selections",
        "student_school_year_assignments",
        "students",
        "timetable_entries",
    }
)


def _request(gate: MaintenanceGate):
    return gate.request_maintenance(
        owner_id=OWNER,
        purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
    )


def test_writer_starts_and_finishes_in_normal() -> None:
    gate = MaintenanceGate()

    with gate.begin_writer():
        assert gate.state is MaintenanceState.NORMAL
        assert gate.active_writer_count == 1

    assert gate.active_writer_count == 0


def test_pending_blocks_new_writer_but_admitted_nested_write_can_finish() -> None:
    gate = MaintenanceGate()
    outer = gate.begin_writer()
    capability = _request(gate)

    with gate.begin_writer():
        assert gate.active_writer_count == 1
    result: list[object] = []

    def new_thread_writer() -> None:
        try:
            gate.begin_writer()
        except Exception as error:
            result.append(error)

    thread = threading.Thread(target=new_thread_writer)
    thread.start()
    thread.join(timeout=1)
    assert thread.is_alive() is False
    assert len(result) == 1
    assert isinstance(result[0], MaintenanceWriterBlockedError)

    assert gate.activate(capability, owner_id=OWNER) is False
    outer.release()
    assert gate.activate(capability, owner_id=OWNER) is True


def test_waiter_activates_only_after_complete_writer_drain() -> None:
    gate = MaintenanceGate()
    lease = gate.begin_writer()
    capability = _request(gate)
    activated = threading.Event()

    def wait_for_drain() -> None:
        for _attempt in range(200):
            if gate.activate(capability, owner_id=OWNER):
                activated.set()
                return
            if activated.wait(0.01):
                return

    waiter = threading.Thread(target=wait_for_drain)
    waiter.start()
    assert activated.wait(0.05) is False
    assert gate.state is MaintenanceState.MAINTENANCE_PENDING

    lease.release()
    waiter.join(timeout=2)

    assert waiter.is_alive() is False
    assert activated.is_set()
    assert gate.state is MaintenanceState.MAINTENANCE_ACTIVE


def test_wrong_owner_is_blocked_and_clean_abort_releases_gate() -> None:
    gate = MaintenanceGate()
    capability = _request(gate)

    with pytest.raises(MaintenanceCapabilityError) as captured:
        gate.activate(capability, owner_id="different-owner")
    assert captured.value.code == "maintenance_capability_owner_mismatch"
    assert gate.state is MaintenanceState.MAINTENANCE_PENDING

    gate.abort(capability, owner_id=OWNER)
    assert gate.state is MaintenanceState.NORMAL
    with gate.begin_writer():
        pass


def test_gate_cannot_be_released_while_exclusive_owner_is_writing() -> None:
    gate = MaintenanceGate()
    capability = _request(gate)
    assert gate.activate(capability, owner_id=OWNER)

    with gate.exclusive_writer(
        capability,
        owner_id=OWNER,
        purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
    ):
        with pytest.raises(MaintenanceCapabilityError) as captured:
            gate.abort(capability, owner_id=OWNER)
        assert captured.value.code == "maintenance_exclusive_writer_active"
        with gate.begin_writer():
            pass

    gate.abort(capability, owner_id=OWNER)
    assert gate.state is MaintenanceState.NORMAL


def test_recovery_required_remains_fail_closed() -> None:
    gate = MaintenanceGate()
    capability = _request(gate)
    gate.mark_recovery_required()

    with pytest.raises(MaintenanceWriterBlockedError):
        gate.begin_writer()
    with pytest.raises(MaintenanceCapabilityError):
        gate.abort(capability, owner_id=OWNER)
    assert gate.state is MaintenanceState.RECOVERY_REQUIRED


def test_backup_restore_capability_cannot_authorize_school_year_write() -> None:
    gate = MaintenanceGate()
    capability = gate.request_maintenance(
        owner_id=OWNER,
        purpose=MaintenancePurpose.BACKUP_RESTORE,
    )
    assert gate.activate(capability, owner_id=OWNER)

    with pytest.raises(MaintenanceCapabilityError) as captured:
        with gate.exclusive_writer(
            capability,
            owner_id=OWNER,
            purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
        ):
            pass

    assert captured.value.code == "maintenance_capability_purpose_mismatch"


def test_writer_inventory_matches_complete_final_v4_schema(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v4_database(tmp_path / "inventory.sqlite")
    database = SQLiteDatabase(path, create=False)

    with database.connect() as connection:
        actual_tables = frozenset(
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        )

    assert actual_tables == PRODUCT_TABLES


@pytest.mark.parametrize(
    "table_name",
    tuple(sorted(PRODUCT_TABLES)),
)
def test_each_product_database_writer_scope_is_blocked_at_shared_boundary(
    tmp_path: Path,
    table_name: str,
) -> None:
    path = create_synthetic_v4_database(tmp_path / "product.sqlite")
    gate = MaintenanceGate()
    database = SQLiteDatabase(path, create=False, maintenance_gate=gate)
    _request(gate)

    with database.connect() as connection:
        with pytest.raises(MaintenanceWriterBlockedError):
            connection.execute(f'DELETE FROM "{table_name}" WHERE 1 = 0')


def test_reads_remain_allowed_while_pending(tmp_path: Path) -> None:
    path = create_synthetic_v4_database(tmp_path / "reads.sqlite")
    gate = MaintenanceGate()
    database = SQLiteDatabase(path, create=False, maintenance_gate=gate)
    _request(gate)

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]


@pytest.mark.parametrize(
    ("owner", "method_names"),
    (
        (
            StudentDesktopAdapter,
            (
                "save_active_documentation_subjects",
                "save_new_student",
                "save_existing_student",
                "change_student_membership",
                "exit_student_from_school_year",
                "archive_student_master_data",
                "save_observation",
                "update_observation",
                "delete_observation",
                "add_student_document",
                "remove_document",
                "save_learning_report_draft",
                "finalize_learning_report",
                "generate_learning_report_pdf",
                "save_learning_conference_draft",
                "complete_learning_conference",
                "generate_learning_conference_pdf",
                "save_competency_confirmation",
            ),
        ),
        (
            MasterDataDesktopAdapter,
            (
                "add_group",
                "add_course",
                "rename_group",
                "rename_course",
                "update_course_group",
                "add_course_group",
            ),
        ),
        (
            TimetableDesktopAdapter,
            (
                "save_entry",
                "set_entry_active",
                "delete_entry",
            ),
        ),
        (
            ObservationPersistenceUnitOfWork,
            (
                "save",
                "recover_pending",
                "recover_pending_while_writer_locked",
                "reserve_id_while_writer_locked",
            ),
        ),
    ),
)
def test_file_and_multistep_product_writer_aggregates_hold_outer_lease(
    owner: type,
    method_names: tuple[str, ...],
) -> None:
    for method_name in method_names:
        method = inspect.getattr_static(owner, method_name)
        assert hasattr(method, "__wrapped__"), (
            f"{owner.__name__}.{method_name} lacks product_writer"
        )


def test_pending_drain_does_not_block_qt_event_loop() -> None:
    script = """
from PySide6.QtCore import QCoreApplication, QTimer
from src.core.maintenance_gate import MaintenanceGate, MaintenancePurpose

app = QCoreApplication([])
gate = MaintenanceGate()
lease = gate.begin_writer()
capability = gate.request_maintenance(
    owner_id="school-year-maintenance",
    purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
)
callbacks = []
QTimer.singleShot(0, lambda: callbacks.append("responsive"))
QTimer.singleShot(1, lease.release)
QTimer.singleShot(
    2,
    lambda: callbacks.append(
        "active" if gate.activate(
            capability,
            owner_id="school-year-maintenance",
        ) else "pending"
    ),
)
QTimer.singleShot(5, app.quit)
app.exec()
assert callbacks == ["responsive", "active"]
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert completed.returncode == 0, completed.stderr


def test_cursor_and_chained_cursor_writes_cannot_bypass_gate(
    tmp_path: Path,
) -> None:
    path = create_synthetic_v4_database(tmp_path / "cursor.sqlite")
    gate = MaintenanceGate()
    database = SQLiteDatabase(path, create=False, maintenance_gate=gate)
    _request(gate)

    with database.connect() as connection:
        with pytest.raises(MaintenanceWriterBlockedError):
            connection.cursor().execute(
                "DELETE FROM students WHERE 1 = 0"
            )
        guarded_cursor = connection.execute("SELECT 1")
        with pytest.raises(MaintenanceWriterBlockedError):
            guarded_cursor.execute("DELETE FROM students WHERE 1 = 0")
        with pytest.raises(MaintenanceWriterBlockedError):
            guarded_cursor.connection.execute(
                "DELETE FROM students WHERE 1 = 0"
            )


def test_gate_state_changes_do_not_modify_database(tmp_path: Path) -> None:
    path = create_synthetic_v4_database(tmp_path / "unchanged.sqlite")
    before = hashlib.sha256(path.read_bytes()).digest()
    gate = MaintenanceGate()
    capability = _request(gate)
    assert gate.activate(capability, owner_id=OWNER)
    gate.abort(capability, owner_id=OWNER)

    assert hashlib.sha256(path.read_bytes()).digest() == before
