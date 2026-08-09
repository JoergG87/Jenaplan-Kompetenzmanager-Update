"""Focused tests for final-schema-only startup coordination."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from src.core.database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
    DatabaseCompatibilityError,
)
from src.core.database_startup import (
    DatabaseStartupCoordinator,
    DatabaseStartupResolver,
    DatabaseStartupState,
)
from src.core.final_v4_schema import initialize_final_v4_schema
from src.desktop_app.main import _coordinate_product_database_startup
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.runtime import prepare_runtime_storage, runtime_paths


def test_missing_database_is_detected_without_creating_it(tmp_path: Path) -> None:
    path = tmp_path / "missing.sqlite"

    detection = DatabaseStartupResolver().resolve(path)

    assert detection.state is DatabaseStartupState.DATABASE_NOT_FOUND
    assert not path.exists()


def test_exact_final_schema_is_recognized_and_runtime_is_allowed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "final.sqlite"
    initialize_final_v4_schema(path)

    detection = DatabaseStartupResolver().resolve(path)
    decision = DatabaseStartupCoordinator().coordinate(
        path,
        restore_status="normal_start",
    )

    expected = DatabaseStartupState.V4_SCHEMA_READY
    assert detection.state is expected
    assert decision.state is expected
    assert decision.sqlite_user_version == FINAL_SCHEMA_VERSION
    assert decision.schema_fingerprint == FINAL_SCHEMA_FINGERPRINT
    assert decision.normal_runtime_allowed is True
    assert decision.final_schema_initialization_required is False
    assert "V2" not in decision.reason_code
    assert "BOOTSTRAP" not in decision.reason_code


def test_legacy_development_schema_has_no_product_route(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_student(value TEXT)")
        connection.execute("PRAGMA user_version = 2")

    detection = DatabaseStartupResolver().resolve(path)
    decision = DatabaseStartupCoordinator().coordinate(
        path,
        restore_status="normal_start",
    )

    assert detection.state is DatabaseStartupState.SCHEMA_UNSUPPORTED
    assert decision.state is DatabaseStartupState.SCHEMA_UNSUPPORTED
    assert decision.normal_runtime_allowed is False
    assert decision.final_schema_initialization_required is False
    assert "MIGRATION" not in decision.reason_code
    assert "BOOTSTRAP" not in decision.reason_code


def test_missing_database_requires_explicit_initialization_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "new.sqlite"
    coordinator = DatabaseStartupCoordinator()

    blocked = coordinator.coordinate(
        path,
        restore_status="normal_start",
        new_database_initialization_allowed=False,
    )
    allowed = coordinator.coordinate(
        path,
        restore_status="normal_start",
        new_database_initialization_allowed=True,
    )

    assert blocked.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert allowed.state is DatabaseStartupState.V4_INITIALIZATION_REQUIRED
    assert allowed.final_schema_initialization_required is True
    assert allowed.normal_runtime_allowed is False
    assert not path.exists()


def test_main_startup_boundary_creates_final_schema_then_rescans(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "runtime"
    data_root.mkdir()

    paths, decision = _coordinate_product_database_startup(
        data_root=data_root,
        restore_status="normal_start",
        coordinator=DatabaseStartupCoordinator(),
        prepare_storage=prepare_runtime_storage,
        initialize_final_schema=initialize_final_v4_schema,
        new_database_initialization_allowed=True,
    )

    assert paths == runtime_paths(data_root)
    assert paths.database.exists()
    assert (
        decision.state
        is DatabaseStartupState.V4_SCHEMA_READY
    )
    assert decision.normal_runtime_allowed is True


def test_main_startup_boundary_does_not_replace_existing_unknown_database(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "runtime"
    data_root.mkdir()
    database = runtime_paths(data_root).database
    database.write_bytes(b"not sqlite")
    before = database.read_bytes()
    calls: list[Path] = []

    _, decision = _coordinate_product_database_startup(
        data_root=data_root,
        restore_status="normal_start",
        coordinator=DatabaseStartupCoordinator(),
        prepare_storage=prepare_runtime_storage,
        initialize_final_schema=calls.append,
        new_database_initialization_allowed=True,
    )

    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert calls == []
    assert database.read_bytes() == before


def test_admitted_database_disappearance_never_creates_a_replacement(
    tmp_path: Path,
) -> None:
    path = tmp_path / "admitted.sqlite"
    initialize_final_v4_schema(path)
    decision = DatabaseStartupCoordinator().coordinate(
        path,
        restore_status="normal_start",
    )
    assert decision.normal_runtime_allowed is True

    path.unlink()

    with pytest.raises(
        DatabaseCompatibilityError,
        match="Final-V4-Datenbank fehlt",
    ):
        StudentDesktopAdapter(
            path,
            database_create_allowed=False,
        )
    assert not path.exists()


@pytest.mark.parametrize(
    "restore_status",
    ("pending", "failed", "handoff_required"),
)
def test_incomplete_restore_state_blocks_before_schema_detection(
    tmp_path: Path,
    restore_status: str,
) -> None:
    path = tmp_path / "final.sqlite"
    initialize_final_v4_schema(path)

    decision = DatabaseStartupCoordinator().coordinate(
        path,
        restore_status=restore_status,
        new_database_initialization_allowed=True,
    )

    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert decision.reason_code == "DB-START-RESTORE-RECOVERY-REQUIRED"


def test_missing_database_after_restore_is_recovery_required(
    tmp_path: Path,
) -> None:
    decision = DatabaseStartupCoordinator().coordinate(
        tmp_path / "missing.sqlite",
        restore_status="completed",
        new_database_initialization_allowed=True,
    )

    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert decision.final_schema_initialization_required is False


def test_empty_unknown_and_corrupt_schemas_fail_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.sqlite"
    empty.touch()
    unknown = tmp_path / "unknown.sqlite"
    with sqlite3.connect(unknown) as connection:
        connection.execute("CREATE TABLE unknown(value TEXT)")
        connection.execute(f"PRAGMA user_version = {FINAL_SCHEMA_VERSION}")
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"not a sqlite database")
    resolver = DatabaseStartupResolver()

    assert resolver.resolve(empty).state is DatabaseStartupState.RECOVERY_REQUIRED
    assert resolver.resolve(unknown).state is DatabaseStartupState.SCHEMA_UNSUPPORTED
    assert resolver.resolve(corrupt).state is DatabaseStartupState.RECOVERY_REQUIRED


@pytest.mark.parametrize("suffix", ("-wal", "-shm"))
def test_sqlite_sidecars_require_recovery(
    tmp_path: Path,
    suffix: str,
) -> None:
    path = tmp_path / "final.sqlite"
    initialize_final_v4_schema(path)
    Path(f"{path}{suffix}").write_bytes(b"synthetic-sidecar")

    detection = DatabaseStartupResolver().resolve(path)

    assert detection.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert detection.reason_code == "DB-START-SQLITE-SIDECAR-RECOVERY-REQUIRED"


def test_symlink_database_path_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.sqlite"
    initialize_final_v4_schema(target)
    link = tmp_path / "link.sqlite"
    link.symlink_to(target)

    detection = DatabaseStartupResolver().resolve(link)

    assert detection.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert detection.reason_code == "DB-START-DATABASE-PATH-UNSAFE"


def test_startup_import_does_not_import_legacy_migration_module() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import src.core.database_startup; "
                "print('src.core.school_year_migration' in sys.modules)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "False"
