from __future__ import annotations

from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from src.application.dispatcher import SuccessResult
from src.application.school_year_assignment import SchoolYearAssignmentQueryService
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
)
from src.core.sqlite_store import SQLiteObservationRepository
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.observation_view_model import (
    ObservationDraftViewModel,
)
from src.security.data_keys import DataMasterKeyStoreStatus
from src.security.database_key_runtime import DatabaseKeyRuntimeGate
from src.security.domain import AccountStatus
from src.security.final_v3_sqlcipher_runtime import (
    FinalV3SQLCipherRuntimeDecisionState,
    run_gated_final_v3_sqlcipher_runtime,
)
from src.security.infrastructure.data_keyset_repository import (
    SQLiteDataKeysetRepository,
)
from src.security.infrastructure.data_master_key_store import (
    build_platform_data_master_key_store,
)
from src.security.infrastructure.system import PlatformFilePermissionManager


def _environment(root: Path) -> dict[str, str]:
    return {
        "JKM_DMK_DATABASE_KEY_RUNTIME_TEST": "1",
        "JKM_DMK_DATABASE_KEY_RUNTIME_ROOT": str(root),
        "JKM_FINAL_V3_SQLCIPHER_RUNTIME_TEST": "1",
    }


def _account_loader(installation_id: str):
    return lambda: SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=installation_id,
    )


def _open(
    root: Path,
    installation_id: str,
    *,
    first_run: bool,
    crash_boundary: str | None = None,
):
    def fault_hook(boundary: str) -> None:
        if boundary == crash_boundary:
            os._exit(97)

    decision = run_gated_final_v3_sqlcipher_runtime(
        account_loader=_account_loader(installation_id),
        authentication_confirmed=True,
        technical_first_run_confirmed=first_run,
        environ=_environment(root),
        fault_hook=fault_hook if crash_boundary is not None else None,
    )
    if (
        decision.state is not FinalV3SQLCipherRuntimeDecisionState.ACTIVE
        or decision.runtime is None
    ):
        print(
            json.dumps(
                {
                    "state": decision.state.value,
                    "error": decision.error_code,
                },
                sort_keys=True,
            )
        )
        raise SystemExit(3)
    return decision.runtime


def _probe(root: Path, installation_id: str) -> dict[str, object]:
    decision = run_gated_final_v3_sqlcipher_runtime(
        account_loader=_account_loader(installation_id),
        authentication_confirmed=True,
        environ=_environment(root),
    )
    return {
        "state": decision.state.value,
        "error": decision.error_code,
        "schema_fingerprint": (
            decision.runtime.compatibility.schema_fingerprint
            if decision.runtime is not None
            else None
        ),
    }


def _first(root: Path, installation_id: str) -> dict[str, object]:
    runtime = _open(root, installation_id, first_run=True)
    database = runtime.database
    created_at = datetime(2026, 8, 1, 8, tzinfo=UTC)
    with database.connect() as connection:
        with connection:
            SchoolYearTransitionExecutionRepository(
                connection
            ).insert_current_school_year(
                school_year_id="SY-PROCESS-2026",
                label="2026/27",
                start_date=date(2026, 8, 1),
                end_date=date(2027, 7, 31),
                created_at=created_at,
            )
    adapter = StudentDesktopAdapter(
        database=database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 3),
        now_provider=lambda: datetime(2026, 8, 3, 9, tzinfo=UTC),
    )
    master = MasterDataDesktopAdapter(adapter)
    group = master.add_group("Prozess Stammgruppe")
    course = master.add_course("Prozess Kurs", year_level=1)
    created = adapter.save_new_student(
        first_name="Nora",
        last_name="Prozesskind",
        group_id=group.item_id,
        course_id=course.item_id,
    )
    if not isinstance(created, SuccessResult):
        raise RuntimeError("process_student_create_failed")
    student_id = created.value.student_id
    observed = adapter.save_observation(
        ObservationDraftViewModel(
            student_id=student_id,
            student_name="Nora Prozesskind",
            date_text="2026-08-03",
            subject_id="deutsch",
            subject_display_name="Deutsch",
            competency_ratings=(),
            context="Prozess Kontext",
            note="Prozess Beobachtung",
            is_quick_observation=True,
        )
    )
    if not isinstance(observed, SuccessResult):
        raise RuntimeError("process_observation_create_failed")
    assignment = SchoolYearAssignmentQueryService(database.connect).assignment_at_date(
        student_id,
        date(2026, 8, 3),
    )
    return {
        "state": "ACTIVE",
        "first_run": runtime.first_run,
        "database_context_id": runtime.database_context_id,
        "student_id": student_id,
        "observation_id": observed.value.observation_id,
        "group_id": group.item_id,
        "course_id": course.item_id,
        "school_year_id": assignment.school_year_id,
        "assignment_id": assignment.assignment_id,
    }


def _restart(root: Path, installation_id: str) -> dict[str, object]:
    runtime = _open(root, installation_id, first_run=False)
    adapter = StudentDesktopAdapter(
        database=runtime.database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 3),
    )
    students = adapter.list_students()
    if len(students) != 1:
        raise RuntimeError("process_student_count_invalid")
    student_id = students[0].student_id
    profile = adapter.get_student_profile(student_id)
    observations = SQLiteObservationRepository(
        runtime.database
    ).list_observations_for_student(student_id)
    assignment = SchoolYearAssignmentQueryService(
        runtime.database.connect
    ).assignment_at_date(student_id, date(2026, 8, 3))
    if profile is None or len(observations) != 1:
        raise RuntimeError("process_projection_invalid")
    return {
        "state": "ACTIVE",
        "first_run": runtime.first_run,
        "database_context_id": runtime.database_context_id,
        "student_id": student_id,
        "display_name": profile.display_name,
        "observation_id": observations[0].observation_id,
        "observation_note": observations[0].note,
        "group_id": assignment.group_id,
        "course_id": assignment.course_id,
        "school_year_id": assignment.school_year_id,
        "assignment_id": assignment.assignment_id,
    }


def _cleanup(root: Path, installation_id: str) -> dict[str, object]:
    store = build_platform_data_master_key_store()
    paths = DatabaseKeyRuntimeGate.require_paths(str(root))
    repository = SQLiteDataKeysetRepository(
        paths.keyset_metadata, PlatformFilePermissionManager()
    )
    repository.initialize()
    keysets = tuple(
        item
        for item in (
            repository.active_data_keyset(),
            *repository.pending_data_keysets(),
            *repository.data_keysets_for_cleanup(),
        )
        if item is not None
    )
    for keyset in keysets:
        store.delete(installation_id=installation_id, key_id=keyset.key_id)
    remaining = [
        keyset.key_id
        for keyset in keysets
        if store.read(
            installation_id=installation_id,
            key_id=keyset.key_id,
        ).status
        is not DataMasterKeyStoreStatus.NOT_FOUND
    ]
    return {"state": "CLEANED", "remaining": remaining}


def main() -> int:
    mode, root_value, installation_id = sys.argv[1:4]
    root = Path(root_value)
    if mode == "first":
        result = _first(root, installation_id)
    elif mode == "restart":
        result = _restart(root, installation_id)
    elif mode == "probe":
        result = _probe(root, installation_id)
    elif mode.startswith("crash:"):
        _open(
            root,
            installation_id,
            first_run=True,
            crash_boundary=mode.removeprefix("crash:"),
        )
        result = {"state": "CRASH_NOT_TRIGGERED"}
    elif mode == "cleanup":
        result = _cleanup(root, installation_id)
    else:
        result = {"state": "BLOCKED", "error": "mode_invalid"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] in {"ACTIVE", "BLOCKED", "CLEANED"} else 5


if __name__ == "__main__":
    raise SystemExit(main())
