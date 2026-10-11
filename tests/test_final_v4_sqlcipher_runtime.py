from __future__ import annotations

from contextlib import closing
from dataclasses import replace
from datetime import UTC, date, datetime
import hashlib
import importlib.metadata
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import uuid

import pytest

from src.application.student_documentation_subjects import (
    StudentDocumentationSubjectService,
)
from src.application.dispatcher import SuccessResult
from src.core.database_compatibility import (
    FINAL_SCHEMA_FINGERPRINT,
    FINAL_SCHEMA_VERSION,
    DatabaseCompatibilityResult,
    DatabaseCompatibilityStatus,
    DatabaseSchemaIdentity,
    DatabaseVersionInfo,
)
from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
    DatabaseKeyRejectedError,
    SQLCipherConnectionProvider,
)
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
)
from src.core.runtime_root_protection import publish_synthetic_test_root
from src.core.runtime_root_protection import RUNTIME_ROOT_PROTECTION_MARKER
from src.core.sqlite_store import SQLiteObservationRepository
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.view_models.observation_view_model import (
    ObservationDraftViewModel,
)
from src.security.data_keys import (
    DataMasterKeyReadResult,
    DataMasterKeyStoreStatus,
)
from src.security.database_key_runtime import (
    DMK_DATABASE_KEY_RUNTIME_GATE_ENV,
    DMK_DATABASE_KEY_RUNTIME_MARKER,
    DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES,
    DMK_DATABASE_KEY_RUNTIME_ROOT_ENV,
    DatabaseKeyRuntimeGate,
    build_database_key_runtime,
    run_gated_database_key_runtime,
)
from src.security.domain import AccountStatus
from src.security.final_v4_sqlcipher_runtime import (
    FINAL_V4_SQLCIPHER_RUNTIME_GATE_ENV,
    FINAL_V4_SQLCIPHER_RUNTIME_MARKER,
    FINAL_V4_SQLCIPHER_RUNTIME_MARKER_BYTES,
    FinalV4SQLCipherConnectionFactory,
    FinalV4SQLCipherRuntimeCoordinator,
    FinalV4SQLCipherRuntimeDecisionState,
    FinalV4SQLCipherRuntimePaths,
    KeyedFinalV4CompatibilityInspector,
    run_gated_final_v4_sqlcipher_runtime,
)


class MemoryDataMasterKeyStore:
    def __init__(self) -> None:
        self.supported = True
        self.values: dict[tuple[str, str], bytes] = {}
        self.create_calls = 0

    def create(
        self, *, installation_id: str, key_id: str, key_material: bytes
    ) -> None:
        self.create_calls += 1
        identity = installation_id, key_id
        if identity in self.values:
            raise RuntimeError("duplicate")
        self.values[identity] = bytes(key_material)

    def read(
        self, *, installation_id: str, key_id: str
    ) -> DataMasterKeyReadResult:
        material = self.values.get((installation_id, key_id))
        if material is None:
            return DataMasterKeyReadResult(DataMasterKeyStoreStatus.NOT_FOUND)
        return DataMasterKeyReadResult(DataMasterKeyStoreStatus.SUCCESS, material)

    def delete(self, *, installation_id: str, key_id: str) -> bool:
        return self.values.pop((installation_id, key_id), None) is not None


def _root(tmp_path: Path) -> Path:
    root = tmp_path / f"jkm-dmk-database-key-runtime-{uuid.uuid4()}"
    root.mkdir(mode=0o700)
    publish_synthetic_test_root(root.resolve(strict=True))
    for name, content in (
        (DMK_DATABASE_KEY_RUNTIME_MARKER, DMK_DATABASE_KEY_RUNTIME_MARKER_BYTES),
        (
            FINAL_V4_SQLCIPHER_RUNTIME_MARKER,
            FINAL_V4_SQLCIPHER_RUNTIME_MARKER_BYTES,
        ),
    ):
        marker = root / name
        marker.write_bytes(content)
        marker.chmod(0o600)
    return root


def _environment(root: Path) -> dict[str, str]:
    return {
        DMK_DATABASE_KEY_RUNTIME_GATE_ENV: "1",
        DMK_DATABASE_KEY_RUNTIME_ROOT_ENV: str(root),
        FINAL_V4_SQLCIPHER_RUNTIME_GATE_ENV: "1",
    }


def _account_loader(installation_id: str):
    return lambda: SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=installation_id,
    )


def _has_exact_417() -> bool:
    try:
        if importlib.metadata.version("sqlcipher3") != SQLCIPHER_4_17_BINDING_VERSION:
            return False
        import sqlcipher3.dbapi2 as driver

        with closing(driver.connect(":memory:")) as connection:
            return (
                str(connection.execute("PRAGMA cipher_version").fetchone()[0])
                == SQLCIPHER_4_17_ENGINE_VERSION
                and str(connection.execute("SELECT sqlite_version()").fetchone()[0])
                == SQLCIPHER_4_17_SQLITE_VERSION
            )
    except Exception:
        return False


requires_exact_417 = pytest.mark.skipif(
    not _has_exact_417(),
    reason="exact local SQLCipher 4.17 build is required",
)


def test_gate_off_does_not_touch_root_or_account(tmp_path: Path) -> None:
    missing = tmp_path / "jkm-dmk-database-key-runtime-missing"
    called = False

    def account_loader():
        nonlocal called
        called = True
        raise AssertionError

    decision = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account_loader,
        authentication_confirmed=True,
        environ={DMK_DATABASE_KEY_RUNTIME_ROOT_ENV: str(missing)},
    )

    assert decision.state is FinalV4SQLCipherRuntimeDecisionState.DISABLED
    assert called is False
    assert not missing.exists()


def test_gate_requires_both_exact_gate_values_and_second_marker(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    (root / FINAL_V4_SQLCIPHER_RUNTIME_MARKER).unlink()
    environment = _environment(root)

    missing_marker = run_gated_final_v4_sqlcipher_runtime(
        account_loader=lambda: None,
        authentication_confirmed=True,
        environ=environment,
    )
    wrong_value = run_gated_final_v4_sqlcipher_runtime(
        account_loader=lambda: None,
        authentication_confirmed=True,
        environ={**environment, FINAL_V4_SQLCIPHER_RUNTIME_GATE_ENV: "yes"},
    )
    missing_key_gate = run_gated_final_v4_sqlcipher_runtime(
        account_loader=lambda: None,
        authentication_confirmed=True,
        environ={
            DMK_DATABASE_KEY_RUNTIME_ROOT_ENV: str(root),
            FINAL_V4_SQLCIPHER_RUNTIME_GATE_ENV: "1",
        },
    )

    assert missing_marker.error_code == "final_v4_sqlcipher_runtime_marker_invalid"
    assert wrong_value.error_code == "final_v4_sqlcipher_runtime_gate_value_invalid"
    assert missing_key_gate.error_code == "database_key_runtime_gate_required"


def test_direct_runtime_components_reject_paths_outside_gate_scope(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    key_paths = DatabaseKeyRuntimeGate.require_paths(str(root))
    scoped = FinalV4SQLCipherRuntimePaths.for_key_runtime(key_paths)
    unscoped = FinalV4SQLCipherRuntimePaths(
        root=scoped.root,
        key_runtime=scoped.key_runtime,
        runtime_root=scoped.runtime_root,
        database=tmp_path / "product.sqlite",
    )
    environment = _environment(root)
    provider = SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
    )

    with pytest.raises(Exception) as coordinator_error:
        FinalV4SQLCipherRuntimeCoordinator(
            paths=unscoped,
            account_loader=_account_loader(str(uuid.uuid4())),
            authentication_confirmed=True,
            technical_first_run_confirmed=True,
            sqlcipher_provider=provider,
            environ=environment,
        )
    assert getattr(coordinator_error.value, "code", "") == (
        "final_v4_sqlcipher_runtime_scope_invalid"
    )

    with pytest.raises(Exception) as factory_error:
        FinalV4SQLCipherConnectionFactory(
            provider=provider,
            paths=unscoped,
            loaded_keys=SimpleNamespace(
                database_key=SimpleNamespace(key_material=secrets.token_bytes(32))
            ),
            environ=environment,
        )
    assert getattr(factory_error.value, "code", "") == (
        "final_v4_sqlcipher_connection_scope_invalid"
    )

    factory = FinalV4SQLCipherConnectionFactory(
        provider=provider,
        paths=scoped,
        loaded_keys=SimpleNamespace(
            database_key=SimpleNamespace(key_material=secrets.token_bytes(32))
        ),
        environ=environment,
    )
    external = tmp_path / "post-open-external"
    external.mkdir(mode=0o700)
    scoped.runtime_root.symlink_to(external, target_is_directory=True)
    with pytest.raises(Exception) as post_open_error:
        factory.connect(scoped.database, create=True)
    assert getattr(post_open_error.value, "code", "") == (
        "final_v4_sqlcipher_runtime_root_unsafe"
    )


def test_runtime_root_symlink_and_orphan_sidecar_block_before_keys(
    tmp_path: Path,
) -> None:
    symlink_root = _root(tmp_path)
    external = tmp_path / "external-runtime"
    external.mkdir(mode=0o700)
    (symlink_root / "final-v4-sqlcipher-runtime-v1").symlink_to(
        external,
        target_is_directory=True,
    )
    store = MemoryDataMasterKeyStore()
    symlinked = run_gated_final_v4_sqlcipher_runtime(
        account_loader=_account_loader(str(uuid.uuid4())),
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(symlink_root),
        key_store=store,
    )
    assert symlinked.error_code == "final_v4_sqlcipher_runtime_root_unsafe"
    assert store.create_calls == 0

    sidecar_root = _root(tmp_path)
    runtime_root = sidecar_root / "final-v4-sqlcipher-runtime-v1"
    runtime_root.mkdir(mode=0o700)
    (runtime_root / "final-v4.sqlcipher-journal").write_bytes(b"orphan")
    store = MemoryDataMasterKeyStore()
    sidecar = run_gated_final_v4_sqlcipher_runtime(
        account_loader=_account_loader(str(uuid.uuid4())),
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(sidecar_root),
        key_store=store,
    )
    assert sidecar.error_code == "final_v4_sqlcipher_recovery_sidecar_present"
    assert store.create_calls == 0


def test_auth_and_explicit_first_run_confirmation_precede_key_creation(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))

    unauthenticated = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=False,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    unconfirmed = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=False,
        environ=_environment(root),
        key_store=store,
    )

    assert unauthenticated.error_code == "authentication_confirmation_required"
    assert unconfirmed.error_code == "technical_first_run_confirmation_required"
    assert store.create_calls == 0
    assert set(root.iterdir()) == {
        root / DMK_DATABASE_KEY_RUNTIME_MARKER,
        root / FINAL_V4_SQLCIPHER_RUNTIME_MARKER,
        root / RUNTIME_ROOT_PROTECTION_MARKER,
    }


def test_database_without_keys_and_keys_without_database_block_before_provider(
    tmp_path: Path,
) -> None:
    database_root = _root(tmp_path)
    runtime_root = database_root / "final-v4-sqlcipher-runtime-v1"
    runtime_root.mkdir(mode=0o700)
    (runtime_root / "final-v4.sqlcipher").write_bytes(b"SQLite format 3\x00")
    no_keys = run_gated_final_v4_sqlcipher_runtime(
        account_loader=_account_loader(str(uuid.uuid4())),
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(database_root),
        key_store=MemoryDataMasterKeyStore(),
    )
    assert no_keys.error_code == "final_v4_sqlcipher_database_without_key_store"

    key_root = _root(tmp_path)
    key_store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    keys = run_gated_database_key_runtime(
        account_loader=account,
        environ=_environment(key_root),
        key_store=key_store,
    )
    assert keys.loaded is not None
    no_database = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(key_root),
        key_store=key_store,
    )
    assert (
        no_database.error_code
        == "final_v4_sqlcipher_database_missing_with_key_store"
    )


def test_plaintext_database_is_rejected_after_key_inventory_exists(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    keys = run_gated_database_key_runtime(
        account_loader=account,
        environ=_environment(root),
        key_store=store,
    )
    assert keys.loaded is not None
    runtime_root = root / "final-v4-sqlcipher-runtime-v1"
    runtime_root.mkdir(mode=0o700)
    database = runtime_root / "final-v4.sqlcipher"
    database.write_bytes(b"SQLite format 3\x00" + b"\x00" * 4096)

    decision = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )

    assert decision.error_code == "plaintext_sqlite_not_supported"
    assert database.read_bytes().startswith(b"SQLite format 3\x00")


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _InspectorConnection:
    def __init__(self, *, cipher_version=SQLCIPHER_4_17_ENGINE_VERSION):
        self.total_changes = 0
        self.cipher_version = cipher_version

    def execute(self, statement: str):
        values = {
            "PRAGMA cipher_version": [(self.cipher_version,)],
            "PRAGMA cipher_status": [("1",)],
            "PRAGMA cipher_provider": [("commoncrypto",)],
            "PRAGMA cipher_provider_version": [("test",)],
            "SELECT sqlite_version()": [(SQLCIPHER_4_17_SQLITE_VERSION,)],
            "PRAGMA cipher_integrity_check": [],
            "PRAGMA integrity_check": [("ok",)],
            "PRAGMA foreign_key_check": [],
            "PRAGMA foreign_keys": [("1",)],
        }
        return _Rows(values[statement])


def _exact_compatibility() -> DatabaseCompatibilityResult:
    return DatabaseCompatibilityResult(
        status=DatabaseCompatibilityStatus.EXACT,
        schema_identity=DatabaseSchemaIdentity(FINAL_SCHEMA_FINGERPRINT, 105),
        version=DatabaseVersionInfo(FINAL_SCHEMA_VERSION, FINAL_SCHEMA_VERSION),
        reason="exact",
    )


def test_keyed_inspector_uses_connection_only_and_rejects_unknown_cipher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def inspect_connection(_self, connection):
        nonlocal calls
        calls += 1
        assert isinstance(connection, _InspectorConnection)
        return _exact_compatibility()

    monkeypatch.setattr(
        "src.security.final_v4_sqlcipher_runtime."
        "DatabaseCompatibilityInspector.inspect_connection",
        inspect_connection,
    )
    inspector = KeyedFinalV4CompatibilityInspector()
    report = inspector.inspect_connection(_InspectorConnection())
    assert report.schema_fingerprint == FINAL_SCHEMA_FINGERPRINT
    assert report.sqlite_user_version == FINAL_SCHEMA_VERSION
    assert calls == 1

    with pytest.raises(Exception) as caught:
        inspector.inspect_connection(_InspectorConnection(cipher_version="9.9.9"))
    assert getattr(caught.value, "code", "") == (
        "sqlcipher_417_engine_version_incompatible"
    )


@requires_exact_417
def test_exact_417_first_run_restart_application_stack_and_ciphertext(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    account = _account_loader(installation_id)

    first = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert first.state is FinalV4SQLCipherRuntimeDecisionState.ACTIVE
    assert first.runtime is not None and first.runtime.first_run is True
    database = first.runtime.database

    from src.core.sqlite_store import SQLiteCompetencyRepository
    from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter().list_entries()
    )

    created_at = datetime(2026, 8, 1, 8, tzinfo=UTC)
    with database.connect() as connection:
        with connection:
            SchoolYearTransitionExecutionRepository(
                connection
            ).insert_current_school_year(
                school_year_id="SY-CIPHER-2026",
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
    group = master.add_group("Cipher Stammgruppe")
    course = master.add_course("Cipher Kurs", year_level=1)
    created = adapter.save_new_student(
        first_name="AdaCipherFirstNameProbe",
        last_name="Cipherkind",
        group_id=group.item_id,
        course_id=course.item_id,
        student_notes="Nur verschluesselt",
    )
    assert isinstance(created, SuccessResult)
    student_id = created.value.student_id
    observation = adapter.save_observation(
        ObservationDraftViewModel(
            student_id=student_id,
            student_name="AdaCipherFirstNameProbe Cipherkind",
            date_text="2026-08-03",
            subject_id="deutsch",
            subject_display_name="Deutsch",
            competency_ratings=(),
            context="Cipher Kontext",
            note="Cipher Beobachtung",
            is_quick_observation=True,
        )
    )
    assert isinstance(observation, SuccessResult)
    observation_id = observation.value.observation_id
    assert adapter.database is database
    assert master.database is database
    repository = SQLiteObservationRepository(database)
    assert repository.database is database
    profile = adapter.get_student_profile(student_id)
    assert profile is not None
    assert profile.student_id == student_id

    restarted = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert restarted.state is FinalV4SQLCipherRuntimeDecisionState.ACTIVE
    assert restarted.runtime is not None and restarted.runtime.first_run is False
    restarted_adapter = StudentDesktopAdapter(
        database=restarted.runtime.database,
        database_create_allowed=False,
        today_provider=lambda: date(2026, 8, 3),
    )
    restarted_profile = restarted_adapter.get_student_profile(student_id)
    restarted_observations = SQLiteObservationRepository(
        restarted.runtime.database
    ).list_observations_for_student(student_id)
    assert restarted_profile is not None
    assert restarted_profile.display_name == "AdaCipherFirstNameProbe Cipherkind"
    assert [item.observation_id for item in restarted_observations] == [
        observation_id
    ]
    assert restarted_observations[0].note == "Cipher Beobachtung"

    # Exercise the new read projection on the exact encrypted product provider.
    from src.application.competency_pdf_export import export_competency_pdf
    from pypdf import PdfReader

    export_target = tmp_path / "competencies.pdf"
    export_competency_pdf(
        restarted_adapter.competency_pdf_for_student(student_id),
        export_target, runtime_root=root,
    )
    assert len(PdfReader(export_target).pages) > 1
    assert not tuple(root.rglob("*.pdf"))

    database_path = restarted.runtime.database.path
    content = database_path.read_bytes()
    assert not content.startswith(b"SQLite format 3\x00")
    for plaintext in (
        "SY-CIPHER-2026",
        "Cipher Stammgruppe",
        "Cipher Kurs",
        student_id,
        "AdaCipherFirstNameProbe",
        "Cipherkind",
        observation_id,
        "Cipher Kontext",
        "Cipher Beobachtung",
    ):
        assert plaintext.encode("utf-8") not in content

    wrong_key = secrets.token_bytes(32)
    provider = SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
    )
    with pytest.raises(DatabaseKeyRejectedError):
        provider.connect(database_path, create=False, key_material=wrong_key)


@requires_exact_417
def test_exact_417_student_subject_service_preserves_keyed_row_factory(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    opened = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert opened.runtime is not None
    database = opened.runtime.database
    timestamp = datetime(2026, 8, 9, 12, tzinfo=UTC).isoformat()
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO school_years(
                school_year_id, label, start_date, end_date,
                status, created_at, closed_at
            ) VALUES ('SY-CIPHER-2026', '2026/27', '2026-08-01',
                      '2027-07-31', 'current', ?, NULL)
            """,
            (timestamp,),
        )
        connection.execute(
            """
            INSERT INTO students(
                student_id, first_name, last_name, notes, active,
                created_at, updated_at, archived_at
            ) VALUES ('STU-CIPHER', 'Ada', 'Cipherkind', '', 1, ?, ?, NULL)
            """,
            (timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO competencies(
                competency_id, subject_id, subject_name, subject_full_name,
                official_subject_name, school_context_name, grade_band,
                label, description, learning_stage, learning_area,
                competency_group, source_reference, catalog_status,
                activation_group_key, sort_order, active,
                catalog_default_active, is_core_subject
            ) VALUES ('CMP-CIPHER-DE', 'SUB-CIPHER-DE', 'Deutsch', 'Deutsch',
                      'Deutsch', 'Test', '1-3', 'Kompetenz Deutsch', 'Test',
                      'stage_1_3', 'Test', 'Test', 'ACCEPTANCE', 'current',
                      'ACCEPTANCE', 1, 1, 1, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO documentation_subject_settings(
                subject_id, active, updated_at
            ) VALUES ('SUB-CIPHER-DE', 1, ?)
            """,
            (timestamp,),
        )
        connection.commit()

    service = StudentDocumentationSubjectService(database.connect)

    assert service.effective_documentation_subjects(
        'STU-CIPHER', 'SY-CIPHER-2026'
    ) == ('SUB-CIPHER-DE',)
    assert service.replace_custom_subjects(
        'STU-CIPHER', 'SY-CIPHER-2026', ()
    ).configuration.selected_subject_ids == ()


@requires_exact_417
def test_cipher_runtime_rejects_v3_declaration_without_restart_mutation(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    first = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert first.runtime is not None
    database = first.runtime.database.path
    with first.runtime.database.connect() as connection:
        connection.execute("PRAGMA user_version = 3")
        connection.commit()
    before = hashlib.sha256(database.read_bytes()).digest()

    restarted = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )

    assert restarted.state is FinalV4SQLCipherRuntimeDecisionState.BLOCKED
    assert restarted.runtime is None
    assert hashlib.sha256(database.read_bytes()).digest() == before


@requires_exact_417
@pytest.mark.parametrize("damage", ("missing", "ciphertext", "schema"))
def test_completed_runtime_rejects_missing_corrupt_or_incomplete_database(
    tmp_path: Path,
    damage: str,
) -> None:
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    first = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert first.runtime is not None
    database = first.runtime.database.path

    if damage == "missing":
        database.unlink()
    elif damage == "ciphertext":
        content = bytearray(database.read_bytes())
        content[-64] ^= 1
        database.write_bytes(content)
    else:
        with first.runtime.database.connect() as connection:
            connection.execute("DROP TABLE documentation_subject_settings")
            connection.commit()

    restarted = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert restarted.state is FinalV4SQLCipherRuntimeDecisionState.BLOCKED
    assert restarted.runtime is None


@requires_exact_417
@pytest.mark.parametrize("damage", ("missing_dmk", "envelope", "context"))
def test_completed_runtime_rejects_combined_key_inventory_damage_without_db_write(
    tmp_path: Path,
    damage: str,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    store = MemoryDataMasterKeyStore()
    account = _account_loader(installation_id)
    first = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert first.runtime is not None
    database = first.runtime.database.path
    before = (database.stat().st_ino, hashlib.sha256(database.read_bytes()).digest())

    paths = DatabaseKeyRuntimeGate.require_paths(str(root))
    if damage == "missing_dmk":
        store.values.clear()
    elif damage == "envelope":
        payload = bytearray(paths.envelope_registry.read_bytes())
        payload[-2] = ord("A") if payload[-2] != ord("A") else ord("B")
        paths.envelope_registry.write_bytes(payload)
    else:
        with sqlite3.connect(paths.keyset_metadata) as connection:
            connection.execute(
                "UPDATE data_keysets SET database_context_id = ?",
                (str(uuid.uuid4()),),
            )

    restarted = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    after = (database.stat().st_ino, hashlib.sha256(database.read_bytes()).digest())
    assert restarted.state is FinalV4SQLCipherRuntimeDecisionState.BLOCKED
    assert restarted.runtime is None
    assert after == before
    assert store.create_calls == 1


@requires_exact_417
def test_coordinator_rejects_wrong_loaded_database_key_without_db_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _root(tmp_path)
    store = MemoryDataMasterKeyStore()
    account = _account_loader(str(uuid.uuid4()))
    first = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        technical_first_run_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    assert first.runtime is not None
    database = first.runtime.database.path
    before = (database.stat().st_ino, hashlib.sha256(database.read_bytes()).digest())
    loaded = build_database_key_runtime(
        DatabaseKeyRuntimeGate.require_paths(str(root)),
        account_loader=account,
        key_store=store,
    ).open_or_create()
    wrong_loaded = replace(
        loaded,
        database_key=replace(
            loaded.database_key,
            key_material=secrets.token_bytes(32),
        ),
    )
    monkeypatch.setattr(
        "src.security.final_v4_sqlcipher_runtime.build_database_key_runtime",
        lambda *args, **kwargs: SimpleNamespace(
            open_or_create=lambda: wrong_loaded
        ),
    )

    restarted = run_gated_final_v4_sqlcipher_runtime(
        account_loader=account,
        authentication_confirmed=True,
        environ=_environment(root),
        key_store=store,
    )
    after = (database.stat().st_ino, hashlib.sha256(database.read_bytes()).digest())
    assert restarted.state is FinalV4SQLCipherRuntimeDecisionState.BLOCKED
    assert restarted.runtime is None
    assert after == before


def test_factory_rejects_the_separate_412_provider(tmp_path: Path) -> None:
    root = _root(tmp_path)
    paths = FinalV4SQLCipherRuntimePaths.for_key_runtime(
        DatabaseKeyRuntimeGate.require_paths(str(root))
    )
    loaded = SimpleNamespace(
        database_key=SimpleNamespace(key_material=secrets.token_bytes(32))
    )
    with pytest.raises(Exception) as caught:
        FinalV4SQLCipherConnectionFactory(
            provider=SQLCipherConnectionProvider(),
            paths=paths,
            loaded_keys=loaded,
            environ=_environment(root),
        )
    assert getattr(caught.value, "code", "") == (
        "sqlcipher_417_provider_configuration_invalid"
    )


@requires_exact_417
@pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("JKM_REAL_KEYCHAIN_TEST") != "1",
    reason="explicit real macOS Keychain crash acceptance required",
)
@pytest.mark.parametrize(
    ("boundary", "restart_state"),
    (
        ("before_database_file_creation", "BLOCKED"),
        ("after_database_file_creation", "BLOCKED"),
        ("during_schema_transaction", "BLOCKED"),
        ("after_schema_commit", "ACTIVE"),
        ("after_full_verification", "ACTIVE"),
    ),
)
def test_real_process_crash_boundaries_restart_or_block_fail_closed(
    tmp_path: Path,
    boundary: str,
    restart_state: str,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    worker = (
        Path(__file__).parent
        / "helpers"
        / "final_v4_sqlcipher_runtime_worker.py"
    )
    repository_root = Path(__file__).parents[1]

    def invoke(mode: str):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(repository_root)
        completed = subprocess.run(
            [sys.executable, str(worker), mode, str(root), installation_id],
            cwd=repository_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        payload = (
            __import__("json").loads(completed.stdout)
            if completed.stdout.strip()
            else {}
        )
        return completed, payload

    database = root / "final-v4-sqlcipher-runtime-v1" / "final-v4.sqlcipher"
    try:
        crashed, payload = invoke(f"crash:{boundary}")
        assert crashed.returncode == 97, (payload, crashed.stderr)
        before_probe = (
            (database.stat().st_ino, hashlib.sha256(database.read_bytes()).digest())
            if database.exists()
            else None
        )
        probed, result = invoke("probe")
        assert probed.returncode == 0, result
        assert result["state"] == restart_state
        if restart_state == "ACTIVE":
            assert result["schema_fingerprint"] == FINAL_SCHEMA_FINGERPRINT
        after_probe = (
            (database.stat().st_ino, hashlib.sha256(database.read_bytes()).digest())
            if database.exists()
            else None
        )
        assert after_probe == before_probe
    finally:
        cleaned, cleanup = invoke("cleanup")
    assert cleaned.returncode == 0, cleanup
    assert cleanup == {"remaining": [], "state": "CLEANED"}


@requires_exact_417
@pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("JKM_REAL_KEYCHAIN_TEST") != "1",
    reason="explicit real macOS Keychain acceptance required",
)
def test_new_process_reopens_same_keyed_application_projection(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    installation_id = str(uuid.uuid4())
    worker = (
        Path(__file__).parent
        / "helpers"
        / "final_v4_sqlcipher_runtime_worker.py"
    )
    repository_root = Path(__file__).parents[1]

    def invoke(mode: str):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(repository_root)
        completed = subprocess.run(
            [sys.executable, str(worker), mode, str(root), installation_id],
            cwd=repository_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        try:
            payload = __import__("json").loads(completed.stdout)
        except Exception:
            payload = {"state": "INVALID_OUTPUT", "stderr": completed.stderr}
        return completed, payload

    try:
        first_result, first = invoke("first")
        assert first_result.returncode == 0, first
        restart_result, restarted = invoke("restart")
        assert restart_result.returncode == 0, restarted
        assert first["first_run"] is True
        assert restarted["first_run"] is False
        assert first["database_context_id"] == restarted["database_context_id"]
        assert first["student_id"] == restarted["student_id"]
        assert first["observation_id"] == restarted["observation_id"]
        assert first["group_id"] == restarted["group_id"]
        assert first["course_id"] == restarted["course_id"]
        assert first["school_year_id"] == restarted["school_year_id"]
        assert first["assignment_id"] == restarted["assignment_id"]
        assert restarted["display_name"] == "Nora Prozesskind"
        assert restarted["observation_note"] == "Prozess Beobachtung"
    finally:
        cleanup_result, cleaned = invoke("cleanup")
    assert cleanup_result.returncode == 0, cleaned
    assert cleaned == {"remaining": [], "state": "CLEANED"}
