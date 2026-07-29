"""Focused SJ-2C tests for read-only database startup coordination."""

from __future__ import annotations

import hashlib
import inspect
from contextlib import ExitStack
from dataclasses import replace
from datetime import date
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest

from src.core.database_compatibility import (
    DATABASE_COMPATIBILITY_VERSION,
    REGISTERED_V3_SCHEMA_FINGERPRINT,
    REGISTERED_V3_SCHEMA_VERSION,
    V2_COMPATIBILITY_FINGERPRINT,
    DatabaseCompatibilityInspector,
    DatabaseCompatibilityPolicy,
    DatabaseCompatibilityResult,
    DatabaseCompatibilityStatus,
    DatabaseSchemaIdentity,
    DatabaseVersionInfo,
)
from src.core.app_preferences import AppPreferences
from src.core.database_startup import (
    DatabaseStartupCoordinator,
    DatabaseStartupResolver,
    DatabaseStartupState,
)
from src.core.sqlite_store import SQLiteCompetencyRepository, SQLiteDatabase
from src.desktop_app import main as desktop_main
from src.desktop_app.runtime import (
    DATABASE_FILENAME,
    INITIAL_DATA_DIRECTORY,
    prepare_runtime_storage,
)
from src.security.startup import SecurityStartState, SecurityStartupDecision


def _v2_database(path: Path) -> Path:
    SQLiteDatabase(path).initialize_schema()
    return path


def _v1_database(path: Path) -> Path:
    _v2_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE persistence_events")
        connection.execute("PRAGMA user_version = 1")
    return path


def _v3_database(path: Path) -> Path:
    from src.core.school_year import (
        SchoolYear,
        SchoolYearSchemaInformation,
        SchoolYearStatus,
        build_school_year_initialization_plan,
        build_school_year_initialization_preview,
    )
    from src.core.school_year_migration import (
        SchoolYearV2ToV3MigrationEngine,
        VerifiedBackupEvidence,
        calculate_v2_source_state_sha256,
    )

    _v2_database(path)
    initial_school_year = SchoolYear(
        "SY-STARTUP-V3",
        "2025/26",
        date(2025, 8, 1),
        date(2026, 7, 31),
        SchoolYearStatus.CURRENT,
    )
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        preview = build_school_year_initialization_preview(
            (),
            initial_school_year,
            (),
            (),
        )
        plan = build_school_year_initialization_plan(
            initial_school_year=initial_school_year,
            confirmed_course_year_levels=(),
            preview=preview,
            source_schema=SchoolYearSchemaInformation(
                DATABASE_COMPATIBILITY_VERSION,
                V2_COMPATIBILITY_FINGERPRINT,
            ),
            target_schema=SchoolYearSchemaInformation(
                REGISTERED_V3_SCHEMA_VERSION,
                REGISTERED_V3_SCHEMA_FINGERPRINT,
            ),
            source_state_sha256="0" * 64,
        )
        plan = replace(
            plan,
            source_state_sha256=calculate_v2_source_state_sha256(
                connection,
                plan,
            ),
        )

    def connection_factory() -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    SchoolYearV2ToV3MigrationEngine(connection_factory).migrate(
        plan=plan,
        operation_token="startup-v3-detection",
        backup_evidence=VerifiedBackupEvidence(
            backup_sha256="a" * 64,
            source_state_sha256=plan.source_state_sha256,
            source_schema_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
            verified_at="2026-07-29T12:00:00+00:00",
        ),
        expected_v2_fingerprint=V2_COMPATIBILITY_FINGERPRINT,
        expected_v3_fingerprint=REGISTERED_V3_SCHEMA_FINGERPRINT,
    )
    return path


def _user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _compatibility_result(
    *,
    version: int,
    fingerprint: str,
    status: DatabaseCompatibilityStatus = DatabaseCompatibilityStatus.INCOMPATIBLE,
    object_count: int = 1,
) -> DatabaseCompatibilityResult:
    return DatabaseCompatibilityResult(
        status=status,
        schema_identity=DatabaseSchemaIdentity(fingerprint, object_count),
        version=DatabaseVersionInfo(version, None),
        reason="synthetic startup classification",
    )


def _resolver_with_result(
    result: DatabaseCompatibilityResult,
) -> DatabaseStartupResolver:
    inspector = mock.Mock(spec=DatabaseCompatibilityInspector)
    inspector.inspect.return_value = result
    return DatabaseStartupResolver(inspector)


def test_exact_v2_is_detected_then_routed_to_bootstrap_without_writes(
    tmp_path: Path,
) -> None:
    database = _v2_database(tmp_path / DATABASE_FILENAME)
    before_bytes = database.read_bytes()
    before_sha256 = hashlib.sha256(before_bytes).hexdigest()
    before_identity = DatabaseCompatibilityInspector.schema_identity(database)
    before_version = _user_version(database)
    wal = Path(f"{database}-wal")
    shm = Path(f"{database}-shm")

    detection = DatabaseStartupResolver().resolve(database)
    with (
        mock.patch.object(SQLiteDatabase, "initialize_schema") as initialize,
        mock.patch.object(
            SQLiteDatabase,
            "ensure_master_data_defaults",
        ) as master_defaults,
        mock.patch.object(
            SQLiteCompetencyRepository,
            "ensure_catalog_defaults",
        ) as catalog_defaults,
    ):
        decision = DatabaseStartupCoordinator().coordinate(
            database,
            restore_status="normal_start",
        )

    assert detection.state is DatabaseStartupState.V2_MIGRATION_REQUIRED
    assert decision.detected_state is DatabaseStartupState.V2_MIGRATION_REQUIRED
    assert decision.state is DatabaseStartupState.V2_BOOTSTRAP_READY
    assert decision.normal_runtime_allowed is False
    assert decision.rescan_after_runtime_storage_preparation is False
    initialize.assert_not_called()
    master_defaults.assert_not_called()
    catalog_defaults.assert_not_called()
    assert _user_version(database) == before_version == 2
    assert DatabaseCompatibilityInspector.schema_identity(database) == before_identity
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_sha256
    assert database.read_bytes() == before_bytes
    assert not wal.exists()
    assert not shm.exists()


def test_existing_v2_stops_before_runtime_storage_and_product_shell(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    _v2_database(root / DATABASE_FILENAME)
    prepare = mock.Mock()

    _paths, decision = desktop_main._coordinate_product_database_startup(
        data_root=root,
        restore_status="normal_start",
        coordinator=DatabaseStartupCoordinator(),
        prepare_storage=prepare,
        new_database_initialization_allowed=False,
    )

    assert decision.state is DatabaseStartupState.V2_BOOTSTRAP_READY
    assert decision.normal_runtime_allowed is False
    prepare.assert_not_called()
    main_source = inspect.getsource(desktop_main.main)
    assert main_source.index("_coordinate_product_database_startup(") < (
        main_source.index("JenaplanDesktopApp(paths.database")
    )


def test_new_database_candidate_rejects_preexisting_runtime_artifacts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    lock_path = root / "restore-runtime.lock"
    lock_path.write_text("synthetic held lock", encoding="utf-8")
    assert desktop_main._new_database_initialization_candidate(
        root,
        runtime_lock_path=lock_path,
    )

    (root / "backups").mkdir()

    assert not desktop_main._new_database_initialization_candidate(
        root,
        runtime_lock_path=lock_path,
    )


@pytest.mark.parametrize("database_present", (True, False))
def test_authenticated_existing_installation_stops_before_all_product_writers(
    tmp_path: Path,
    database_present: bool,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    if database_present:
        _v2_database(root / DATABASE_FILENAME)
    paths = desktop_main.runtime_paths(root)
    security_runtime = SimpleNamespace(
        service=mock.Mock(),
        repository=mock.Mock(),
        preferences=mock.Mock(),
        device_credentials=mock.Mock(),
        support_reset=mock.Mock(),
    )
    security_runtime.service.security_store_state.return_value = object()
    security_runtime.preferences.load.return_value = AppPreferences()
    security_decision = SecurityStartupDecision(
        SecurityStartState.LOGIN_REQUIRED,
        "SEC-LOGIN_REQUIRED",
    )
    authentication = SimpleNamespace(
        session=object(),
        enrollment_completed=False,
    )
    restore_result = SimpleNamespace(
        status="normal_start",
        restore_id=None,
        resume_token=None,
    )
    runtime_lock = mock.Mock()
    runtime_lock.path = root / "restore-runtime.lock"
    runtime_lock.path.write_text("synthetic held lock", encoding="utf-8")
    application = mock.Mock()
    pre_auth_buffer = mock.Mock()
    window_constructor = mock.Mock()
    fake_app_module = ModuleType("src.desktop_app.app")
    fake_app_module.JenaplanDesktopApp = window_constructor

    with ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(desktop_main.sys, "argv", ["app"])
        )
        stack.enter_context(
            mock.patch.object(
                desktop_main,
                "application_data_root",
                return_value=root,
            )
        )
        stack.enter_context(
            mock.patch.object(
                desktop_main,
                "prepare_security_runtime_storage",
                return_value=paths,
            )
        )
        prepare_runtime = stack.enter_context(
            mock.patch.object(desktop_main, "prepare_runtime_storage")
        )
        stack.enter_context(
            mock.patch.object(
                desktop_main,
                "begin_pre_auth_security_logging",
                return_value=pre_auth_buffer,
            )
        )
        discard_pre_auth = stack.enter_context(
            mock.patch.object(
                desktop_main,
                "discard_pre_auth_security_logging",
            )
        )
        configure_logging = stack.enter_context(
            mock.patch.object(desktop_main, "configure_runtime_logging")
        )
        stack.enter_context(
            mock.patch.object(desktop_main, "load_build_info", return_value={})
        )
        stack.enter_context(
            mock.patch.object(
                desktop_main,
                "_app_icon",
                return_value=mock.Mock(),
            )
        )
        stack.enter_context(
            mock.patch(
                "src.core.restore_runtime.RuntimeInstanceLock",
                return_value=runtime_lock,
            )
        )
        stack.enter_context(
            mock.patch(
                "src.core.restore_runtime.recover_interrupted_restore",
                return_value=restore_result,
            )
        )
        stack.enter_context(
            mock.patch(
                "PySide6.QtWidgets.QApplication",
                return_value=application,
            )
        )
        stack.enter_context(
            mock.patch("src.desktop_app.theme.apply_app_theme")
        )
        stack.enter_context(
            mock.patch(
                "src.security.startup.build_security_runtime",
                return_value=security_runtime,
            )
        )
        stack.enter_context(
            mock.patch(
                "src.security.startup.legacy_installation_present",
                return_value=True,
            )
        )
        security_resolver = stack.enter_context(
            mock.patch("src.security.startup.SecurityStartupResolver")
        )
        stack.enter_context(
            mock.patch(
                "src.desktop_app.security_controller."
                "should_attempt_startup_device_authentication",
                return_value=False,
            )
        )
        stack.enter_context(
            mock.patch(
                "src.desktop_app.security_controller."
                "run_startup_authentication",
                return_value=authentication,
            )
        )
        device_authentication = stack.enter_context(
            mock.patch(
                "src.desktop_app.security_controller."
                "run_startup_device_authentication",
            )
        )
        stack.enter_context(
            mock.patch(
                "src.desktop_app.support_reset.SupportResetBackupFactory",
                return_value=mock.Mock(),
            )
        )
        initialize = stack.enter_context(
            mock.patch.object(SQLiteDatabase, "initialize_schema")
        )
        master_defaults = stack.enter_context(
            mock.patch.object(
                SQLiteDatabase,
                "ensure_master_data_defaults",
            )
        )
        catalog_defaults = stack.enter_context(
            mock.patch.object(
                SQLiteCompetencyRepository,
                "ensure_catalog_defaults",
            )
        )
        student_adapter = stack.enter_context(
            mock.patch(
                "src.desktop_app.adapters.student_desktop_adapter."
                "StudentDesktopAdapter",
            )
        )
        stack.enter_context(
            mock.patch.dict(
                sys.modules,
                {"src.desktop_app.app": fake_app_module},
            )
        )
        security_resolver.return_value.resolve.return_value = security_decision
        result = desktop_main.main()

    assert result == 4
    runtime_lock.acquire.assert_called_once_with()
    runtime_lock.release.assert_called_once_with()
    prepare_runtime.assert_not_called()
    configure_logging.assert_not_called()
    discard_pre_auth.assert_called_once_with(pre_auth_buffer)
    initialize.assert_not_called()
    master_defaults.assert_not_called()
    catalog_defaults.assert_not_called()
    student_adapter.assert_not_called()
    window_constructor.assert_not_called()
    device_authentication.assert_not_called()
    if database_present:
        assert (root / DATABASE_FILENAME).is_file()
    else:
        assert not (root / DATABASE_FILENAME).exists()


def test_exact_v3_is_detected_but_current_v2_runtime_is_not_admitted(
    tmp_path: Path,
) -> None:
    database = _v3_database(tmp_path / DATABASE_FILENAME)
    resolver = DatabaseStartupResolver()

    detection = resolver.resolve(database)
    blocked = DatabaseStartupCoordinator(resolver).coordinate(
        database,
        restore_status="normal_start",
    )

    assert detection.state is DatabaseStartupState.V3_READY
    assert blocked.state is DatabaseStartupState.V3_READY
    assert blocked.normal_runtime_allowed is False
    assert blocked.reason_code == "DB-START-V3-RUNTIME-NOT-COMPATIBLE"


def test_active_compatibility_policy_remains_v2_only() -> None:
    identity = DatabaseSchemaIdentity(
        REGISTERED_V3_SCHEMA_FINGERPRINT,
        1,
    )
    result = DatabaseCompatibilityPolicy().evaluate(
        sqlite_user_version=REGISTERED_V3_SCHEMA_VERSION,
        schema_identity=identity,
    )
    assert DATABASE_COMPATIBILITY_VERSION == 2
    assert result.status is DatabaseCompatibilityStatus.INCOMPATIBLE


def test_migration_engine_keeps_neutral_v3_identity_aliases() -> None:
    from src.core.school_year_migration import (
        TARGET_V3_DATABASE_VERSION,
        V3_SCHEMA_FINGERPRINT,
    )

    assert TARGET_V3_DATABASE_VERSION == REGISTERED_V3_SCHEMA_VERSION == 3
    assert V3_SCHEMA_FINGERPRINT == REGISTERED_V3_SCHEMA_FINGERPRINT


def test_startup_import_does_not_import_isolated_migration_engine() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import src.core.database_startup; "
            "print('src.core.school_year_migration' in sys.modules)",
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "False"


def test_unknown_schema_is_unsupported_and_unchanged(tmp_path: Path) -> None:
    database = _v2_database(tmp_path / "unknown.sqlite")
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unknown_extension (value TEXT)")
    before = database.read_bytes()

    decision = DatabaseStartupCoordinator().coordinate(
        database,
        restore_status="normal_start",
    )

    assert decision.state is DatabaseStartupState.SCHEMA_UNSUPPORTED
    assert database.read_bytes() == before


def test_newer_schema_version_is_unsupported_and_unchanged(tmp_path: Path) -> None:
    database = _v2_database(tmp_path / "newer.sqlite")
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 4")
    before = database.read_bytes()

    decision = DatabaseStartupCoordinator().coordinate(
        database,
        restore_status="normal_start",
    )

    assert decision.state is DatabaseStartupState.SCHEMA_UNSUPPORTED
    assert _user_version(database) == 4
    assert database.read_bytes() == before


def test_existing_sqlite_wal_or_shm_requires_recovery_before_inspection(
    tmp_path: Path,
) -> None:
    database = _v2_database(tmp_path / "wal.sqlite")
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("CREATE TABLE wal_only_extension (value TEXT)")
        connection.commit()
        assert Path(f"{database}-wal").is_file()

        decision = DatabaseStartupCoordinator().coordinate(
            database,
            restore_status="normal_start",
        )

        assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
        assert (
            decision.reason_code
            == "DB-START-SQLITE-SIDECAR-RECOVERY-REQUIRED"
        )
        assert decision.normal_runtime_allowed is False
    finally:
        connection.close()


@pytest.mark.parametrize("suffix", ("-wal", "-shm"))
def test_orphaned_sqlite_sidecar_blocks_authorized_first_run(
    tmp_path: Path,
    suffix: str,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    database = root / DATABASE_FILENAME
    Path(f"{database}{suffix}").write_bytes(b"orphaned-sidecar")
    prepare = mock.Mock()

    _paths, decision = desktop_main._coordinate_product_database_startup(
        data_root=root,
        restore_status="normal_start",
        coordinator=DatabaseStartupCoordinator(),
        prepare_storage=prepare,
        new_database_initialization_allowed=True,
    )

    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert (
        decision.reason_code
        == "DB-START-SQLITE-SIDECAR-RECOVERY-REQUIRED"
    )
    assert decision.normal_runtime_allowed is False
    prepare.assert_not_called()
    assert not database.exists()


@pytest.mark.parametrize(
    ("version", "fingerprint"),
    (
        (2, REGISTERED_V3_SCHEMA_FINGERPRINT),
        (3, V2_COMPATIBILITY_FINGERPRINT),
        (4, REGISTERED_V3_SCHEMA_FINGERPRINT),
    ),
)
def test_version_fingerprint_crossbind_is_unsupported(
    tmp_path: Path,
    version: int,
    fingerprint: str,
) -> None:
    database = tmp_path / f"crossbind-{version}.sqlite"
    database.write_bytes(b"synthetic-inspector-target")
    resolver = _resolver_with_result(
        _compatibility_result(
            version=version,
            fingerprint=fingerprint,
        )
    )
    decision = DatabaseStartupCoordinator(resolver).coordinate(
        database,
        restore_status="normal_start",
    )
    assert decision.state is DatabaseStartupState.SCHEMA_UNSUPPORTED


def test_known_v1_predecessor_does_not_enter_automatic_v2_migration(
    tmp_path: Path,
) -> None:
    database = _v1_database(tmp_path / "v1.sqlite")
    before = database.read_bytes()

    decision = DatabaseStartupCoordinator().coordinate(
        database,
        restore_status="normal_start",
    )

    assert decision.state is DatabaseStartupState.SCHEMA_UNSUPPORTED
    assert _user_version(database) == 1
    assert database.read_bytes() == before


def test_missing_database_is_detected_without_creation_or_inspection(
    tmp_path: Path,
) -> None:
    database = tmp_path / DATABASE_FILENAME
    inspector = mock.Mock(spec=DatabaseCompatibilityInspector)
    resolver = DatabaseStartupResolver(inspector)

    detection = resolver.resolve(database)
    decision = DatabaseStartupCoordinator(resolver).coordinate(
        database,
        restore_status="normal_start",
    )

    assert detection.state is DatabaseStartupState.DATABASE_NOT_FOUND
    assert decision.detected_state is DatabaseStartupState.DATABASE_NOT_FOUND
    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert decision.normal_runtime_allowed is False
    assert decision.rescan_after_runtime_storage_preparation is False
    inspector.inspect.assert_not_called()
    assert not database.exists()


def test_real_first_run_keeps_existing_v2_creation_path(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    resources = tmp_path / "resources"
    resources.mkdir()

    def prepare(*, data_root: Path):
        return prepare_runtime_storage(
            data_root=data_root,
            resource_root_path=resources,
        )

    paths, decision = desktop_main._coordinate_product_database_startup(
        data_root=root,
        restore_status="normal_start",
        coordinator=DatabaseStartupCoordinator(),
        prepare_storage=prepare,
        new_database_initialization_allowed=True,
    )

    assert decision.state is DatabaseStartupState.DATABASE_NOT_FOUND
    assert decision.normal_runtime_allowed is True
    assert decision.rescan_after_runtime_storage_preparation is False
    assert paths.root.is_dir()
    assert not paths.database.exists()


def test_installed_v2_initial_data_is_rescanned_before_shell(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    resources = tmp_path / "resources"
    initial = resources / INITIAL_DATA_DIRECTORY / DATABASE_FILENAME
    initial.parent.mkdir(parents=True)
    _v2_database(initial)

    def prepare(*, data_root: Path):
        return prepare_runtime_storage(
            data_root=data_root,
            resource_root_path=resources,
        )

    paths, decision = desktop_main._coordinate_product_database_startup(
        data_root=root,
        restore_status="normal_start",
        coordinator=DatabaseStartupCoordinator(),
        prepare_storage=prepare,
        new_database_initialization_allowed=True,
    )

    assert paths.database.is_file()
    assert decision.detected_state is DatabaseStartupState.V2_MIGRATION_REQUIRED
    assert decision.state is DatabaseStartupState.V2_BOOTSTRAP_READY
    assert decision.normal_runtime_allowed is False


@pytest.mark.parametrize(
    "restore_status",
    (
        "normal_start",
        "completed",
        "rolled_back",
        "aborted_before_replacement",
    ),
)
def test_terminal_restore_states_are_classified_before_runtime(
    tmp_path: Path,
    restore_status: str,
) -> None:
    database = _v2_database(tmp_path / f"{restore_status}.sqlite")
    decision = DatabaseStartupCoordinator().coordinate(
        database,
        restore_status=restore_status,
    )
    assert decision.state is DatabaseStartupState.V2_BOOTSTRAP_READY
    assert decision.normal_runtime_allowed is False


@pytest.mark.parametrize(
    "restore_status",
    ("resume_required", "manual_recovery_required", "unknown"),
)
def test_open_or_unknown_restore_state_requires_recovery_without_inspection(
    tmp_path: Path,
    restore_status: str,
) -> None:
    resolver = mock.Mock(spec=DatabaseStartupResolver)
    coordinator = DatabaseStartupCoordinator(resolver)
    decision = coordinator.coordinate(
        tmp_path / DATABASE_FILENAME,
        restore_status=restore_status,
    )
    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert decision.normal_runtime_allowed is False
    resolver.resolve.assert_not_called()


@pytest.mark.parametrize(
    "restore_status",
    ("completed", "rolled_back", "aborted_before_replacement"),
)
def test_database_missing_after_restore_requires_recovery(
    tmp_path: Path,
    restore_status: str,
) -> None:
    decision = DatabaseStartupCoordinator().coordinate(
        tmp_path / DATABASE_FILENAME,
        restore_status=restore_status,
    )
    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert decision.normal_runtime_allowed is False


@pytest.mark.parametrize("kind", ("empty", "corrupt"))
def test_empty_or_corrupt_existing_database_requires_recovery(
    tmp_path: Path,
    kind: str,
) -> None:
    database = tmp_path / f"{kind}.sqlite"
    if kind == "empty":
        sqlite3.connect(database).close()
    else:
        database.write_bytes(b"not a sqlite database")

    detection = DatabaseStartupResolver().resolve(database)

    assert detection.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert database.exists()


def test_symlink_database_path_requires_recovery(tmp_path: Path) -> None:
    target = _v2_database(tmp_path / "target.sqlite")
    database = tmp_path / DATABASE_FILENAME
    database.symlink_to(target)

    decision = DatabaseStartupCoordinator().coordinate(
        database,
        restore_status="normal_start",
    )

    assert decision.state is DatabaseStartupState.RECOVERY_REQUIRED
    assert decision.normal_runtime_allowed is False
