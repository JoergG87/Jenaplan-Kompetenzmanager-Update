from __future__ import annotations

from contextlib import closing
from datetime import UTC, date, datetime
import hashlib
import importlib.metadata
import inspect
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import uuid

import pytest

import src.desktop_app.main as desktop_main

from src.core.database_engine import (
    SQLCIPHER_4_17_BINDING_VERSION,
    SQLCIPHER_4_17_ENGINE_VERSION,
    SQLCIPHER_4_17_SQLITE_VERSION,
    SQLCIPHER_SPIKE_BINDING_VERSION,
    SQLCIPHER_SPIKE_ENGINE_VERSION,
    SQLiteConnectionProvider,
    SQLCipherConnectionProvider,
)
from src.desktop_app.adapters.backup_restore_desktop_adapter import (
    BackupRestoreDesktopAdapter,
    CipherBackupRestoreUnavailableError,
)
from src.desktop_app.adapters.master_data_desktop_adapter import (
    MasterDataDesktopAdapter,
)
from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
from src.desktop_app.main import (
    _build_cipher_product_student_adapter,
    _preflight_desktop_runtime_root,
)
from src.desktop_app.runtime import runtime_paths
from src.core.runtime_root_protection import (
    RuntimeRootLifecycle,
    activate_pilot_product_root,
    inspect_runtime_root,
    prepare_synthetic_test_root,
    publish_pilot_product_root,
)
from src.desktop_app.view_models.observation_view_model import (
    ObservationDraftViewModel,
)
from src.security.cipher_product_runtime import (
    PILOT_FIRST_RUN_SCHOOL_YEAR_ID,
    CipherProductRuntimeError,
    open_cipher_product_runtime,
)
from src.security.data_keys import (
    DataMasterKeyReadResult,
    DataMasterKeyStoreStatus,
)
from src.security.domain import AccountStatus


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


class FixedClock:
    def utc_now(self) -> datetime:
        return datetime(2026, 8, 9, 10, 30, tzinfo=UTC)


def _has_exact_417() -> bool:
    try:
        if importlib.metadata.version("sqlcipher3") != SQLCIPHER_4_17_BINDING_VERSION:
            return False
        import sqlcipher3.dbapi2 as driver

        with closing(driver.connect(":memory:")) as connection:
            connection.execute("PRAGMA key = \"x'" + ("00" * 32) + "'\"")
            return (
                str(connection.execute("PRAGMA cipher_version").fetchone()[0])
                == SQLCIPHER_4_17_ENGINE_VERSION
                and str(connection.execute("SELECT sqlite_version()").fetchone()[0])
                == SQLCIPHER_4_17_SQLITE_VERSION
                and str(connection.execute("PRAGMA cipher_provider").fetchone()[0])
                == "commoncrypto"
            )
    except Exception:
        return False


requires_exact_417 = pytest.mark.skipif(
    not _has_exact_417(),
    reason="exact local SQLCipher 4.17 build is required",
)


def _case(tmp_path: Path, *, protected: bool = False):
    root = (tmp_path / "product-runtime").resolve()
    if protected:
        root.mkdir(mode=0o700)
        publish_pilot_product_root(root)
    else:
        prepare_synthetic_test_root(root)
    paths = runtime_paths(root)
    installation_id = str(uuid.uuid4())
    account = SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=installation_id,
    )
    store = MemoryDataMasterKeyStore()
    return paths, account, store


def _open(paths, account, store, *, first_run_allowed: bool, provider=None):
    return open_cipher_product_runtime(
        paths=paths,
        account_loader=lambda: account,
        authentication_confirmed=True,
        first_run_allowed=first_run_allowed,
        key_store=store,
        clock=FixedClock(),
        sqlcipher_provider=provider,
    )


def _assert_fresh_first_run_domain_contract(opened, paths) -> None:
    with closing(opened.database.connect()) as connection:
        assert [
            tuple(row)
            for row in connection.execute(
                "SELECT label, start_date, end_date, status FROM school_years"
            ).fetchall()
        ] == [("2026/27", "2026-08-01", "2027-07-31", "current")]
        assert connection.execute(
            "SELECT COUNT(*) FROM competencies"
        ).fetchone()[0] == 331
        for table in (
            "students",
            "groups",
            "courses",
            "course_groups",
            "observations",
            "student_competency_confirmations",
            "report_drafts",
            "learning_reports",
            "learning_report_pdf_artifacts",
            "learning_conference_drafts",
            "learning_conferences",
            "learning_conference_pdf_artifacts",
            "documents",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0] == 0
    assert not tuple(paths.encrypted_document_storage.rglob("*.jkmedoc"))
    assert not tuple(paths.backups.glob("*.jkmebackup"))


@requires_exact_417
def test_exact_417_product_first_run_is_empty_and_keyed(tmp_path: Path) -> None:
    paths, account, store = _case(tmp_path)

    opened = _open(paths, account, store, first_run_allowed=True)
    _build_cipher_product_student_adapter(opened)

    assert opened.first_run is True
    assert opened.installation_id == account.installation_id
    assert opened.runtime.final_v4.compatibility.cipher_version == (
        SQLCIPHER_4_17_ENGINE_VERSION
    )
    assert opened.runtime.final_v4.compatibility.cipher_provider == "commoncrypto"
    assert opened.runtime.final_v4.compatibility.sqlite_version == (
        SQLCIPHER_4_17_SQLITE_VERSION
    )
    assert opened.database is opened.runtime.final_v4.database
    assert opened.documents is opened.runtime.documents
    assert callable(opened.documents.prepare)
    assert callable(opened.documents.read)
    with closing(opened.database.connect()) as connection:
        year = connection.execute(
            """
            SELECT school_year_id, label, start_date, end_date, status
            FROM school_years
            """
        ).fetchall()
        assert [tuple(row) for row in year] == [
            (
                PILOT_FIRST_RUN_SCHOOL_YEAR_ID,
                "2026/27",
                "2026-08-01",
                "2027-07-31",
                "current",
            )
        ]
        assert connection.execute(
            "SELECT COUNT(*) FROM competencies"
        ).fetchone()[0] == 331
        for table in (
            "students",
            "groups",
            "courses",
            "course_groups",
            "course_group_student_groups",
            "course_group_courses",
            "student_school_year_assignments",
            "school_year_transitions",
            "timetable_entries",
            "observations",
            "observation_competency_ratings",
            "student_competency_confirmations",
            "documentation_subject_settings",
            "student_documentation_subject_profiles",
            "student_documentation_subject_selections",
            "report_drafts",
            "report_draft_subjects",
            "report_draft_competencies",
            "report_draft_observations",
            "report_draft_charts",
            "learning_reports",
            "learning_report_revisions",
            "learning_report_pdf_artifacts",
            "learning_conference_drafts",
            "learning_conference_draft_subjects",
            "learning_conference_draft_cross_topics",
            "learning_conference_draft_competencies",
            "learning_conference_draft_observations",
            "learning_conference_draft_charts",
            "learning_conferences",
            "learning_conference_revisions",
            "learning_conference_pdf_artifacts",
            "documents",
            "persistence_events",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0] == 0
    assert not paths.final_v4_database.read_bytes().startswith(b"SQLite format 3\x00")
    assert not paths.document_companion_database.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
    assert b"2026/27" not in paths.final_v4_database.read_bytes()
    assert not paths.database.exists()
    assert not paths.documents.exists()
    assert not tuple(paths.encrypted_document_storage.rglob("*.jkmedoc"))
    assert not tuple(paths.backups.glob("*.jkmebackup"))
    assert store.create_calls == 1


@requires_exact_417
def test_real_product_root_first_run_activates_only_after_catalog_verification(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "real-product-root").resolve()
    protection, fresh = _preflight_desktop_runtime_root(root, packaged_smoke=False)
    assert protection is None and fresh is True
    root.mkdir(mode=0o700)
    lock_path = root / "instance.lock"
    lock_path.write_bytes(b"held-by-test")
    publish_pilot_product_root(root, allowed_existing=(lock_path,))
    paths = runtime_paths(root)
    account = SimpleNamespace(
        status=AccountStatus.ACTIVE,
        installation_id=str(uuid.uuid4()),
    )
    store = MemoryDataMasterKeyStore()

    opened = _open(paths, account, store, first_run_allowed=True)
    assert inspect_runtime_root(root).lifecycle is RuntimeRootLifecycle.INITIALIZING
    _build_cipher_product_student_adapter(opened)
    _assert_fresh_first_run_domain_contract(opened, paths)
    activate_pilot_product_root(root)
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            paths.final_v4_database,
            paths.document_companion_database,
            paths.keyset_metadata,
            paths.database_key_envelope_registry,
        )
    }

    restarted = _open(paths, account, store, first_run_allowed=False)
    _build_cipher_product_student_adapter(restarted)

    assert restarted.first_run is False
    assert inspect_runtime_root(root).lifecycle is RuntimeRootLifecycle.ACTIVE
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in before
    } == before


@requires_exact_417
def test_product_restart_reuses_contexts_key_and_school_year(tmp_path: Path) -> None:
    paths, account, store = _case(tmp_path)
    first = _open(paths, account, store, first_run_allowed=True)
    _build_cipher_product_student_adapter(first)
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            paths.final_v4_database,
            paths.document_companion_database,
            paths.keyset_metadata,
            paths.database_key_envelope_registry,
        )
    }

    restarted = _open(paths, account, store, first_run_allowed=False)
    _build_cipher_product_student_adapter(restarted)

    assert restarted.first_run is False
    assert restarted.installation_id == first.installation_id
    assert restarted.database_context_id == first.database_context_id
    assert restarted.dmk_key_id == first.dmk_key_id
    assert restarted.dmk_generation == first.dmk_generation == 1
    assert restarted.dmk_fingerprint_sha256 == first.dmk_fingerprint_sha256
    assert restarted.database_key_id == first.database_key_id
    assert restarted.database_key_generation == first.database_key_generation == 1
    assert (
        restarted.database_key_fingerprint_sha256
        == first.database_key_fingerprint_sha256
    )
    assert restarted.runtime.database_context_id == first.runtime.database_context_id
    assert store.create_calls == 1
    with closing(restarted.database.connect()) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM school_years WHERE label = '2026/27'"
        ).fetchone()[0] == 1
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in before
    } == before


@requires_exact_417
@pytest.mark.parametrize("damage", ["wrong_label", "closed_without_current"])
def test_restart_rejects_contradictory_first_run_school_year(
    tmp_path: Path,
    damage: str,
) -> None:
    paths, account, store = _case(tmp_path)
    opened = _open(paths, account, store, first_run_allowed=True)
    with closing(opened.database.connect()) as connection, connection:
        if damage == "wrong_label":
            connection.execute(
                "UPDATE school_years SET label = 'falsch' WHERE school_year_id = ?",
                (PILOT_FIRST_RUN_SCHOOL_YEAR_ID,),
            )
        else:
            connection.execute(
                "UPDATE school_years SET status = 'closed', closed_at = ? "
                "WHERE school_year_id = ?",
                ("2026-08-09T10:30:00Z", PILOT_FIRST_RUN_SCHOOL_YEAR_ID),
            )

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == "cipher_product_fachlicher_first_run_incomplete"
    assert caught.value.operation.value == "verify_runtime"


@requires_exact_417
def test_product_adapter_observation_roundtrip_uses_same_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths, account, store = _case(tmp_path)
    first = _open(paths, account, store, first_run_allowed=True)

    def reject_fallback(*_args, **_kwargs):
        raise AssertionError("standard SQLite fallback must not be opened")

    monkeypatch.setattr(StudentDesktopAdapter, "_open_database", reject_fallback)
    adapter = _build_cipher_product_student_adapter(first)
    assert adapter.database is first.database
    assert adapter._managed_document_store is first.documents
    with closing(first.database.connect()) as connection:
        for table in (
            "students",
            "groups",
            "courses",
            "student_school_year_assignments",
            "observations",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM competencies").fetchone()[0] > 0
    master = MasterDataDesktopAdapter(adapter)
    group = master.add_group("Cipher Gruppe")
    course = master.add_course("Cipher Kurs", year_level=1)
    student = adapter.save_new_student(
        first_name="Ada",
        last_name="Cipherprodukt",
        group_id=group.item_id,
        course_id=course.item_id,
    )
    observation = adapter.save_observation(
        ObservationDraftViewModel(
            student_id=student.value.student_id,
            student_name="Ada Cipherprodukt",
            date_text="2026-08-09",
            subject_id="deutsch",
            subject_display_name="Deutsch",
            competency_ratings=(),
            context="Produktkomposition",
            note="Nur verschlüsselt gespeichert",
            is_quick_observation=True,
        )
    )
    assert observation.success

    restarted = _open(paths, account, store, first_run_allowed=False)
    restarted_adapter = _build_cipher_product_student_adapter(restarted)
    assert restarted_adapter.database is restarted.database
    rows = restarted_adapter.list_observations_for_student(student.value.student_id)
    assert [row.observation_id for row in rows] == [observation.value.observation_id]
    assert rows[0].note == "Nur verschlüsselt gespeichert"
    raw = paths.final_v4_database.read_bytes()
    for plaintext in (
        "Ada",
        "Cipherprodukt",
        "Produktkomposition",
        "Nur verschlüsselt gespeichert",
    ):
        assert plaintext.encode("utf-8") not in raw


def test_plaintext_product_database_is_rejected_unchanged_before_keys(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)
    with sqlite3.connect(paths.database) as connection:
        connection.execute("CREATE TABLE legacy(value TEXT)")
        connection.execute("INSERT INTO legacy VALUES ('nicht migrieren')")
    before = paths.database.stat().st_ino, hashlib.sha256(
        paths.database.read_bytes()
    ).hexdigest()

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    after = paths.database.stat().st_ino, hashlib.sha256(
        paths.database.read_bytes()
    ).hexdigest()
    assert caught.value.code == "plaintext_product_database_not_supported"
    assert after == before
    assert store.create_calls == 0
    assert not paths.keyset_metadata.exists()
    assert not paths.final_v4_database.exists()


def test_plaintext_at_final_v4_product_path_is_rejected_before_keys(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)
    paths.final_v4_runtime.mkdir(mode=0o700)
    with sqlite3.connect(paths.final_v4_database) as connection:
        connection.execute("CREATE TABLE legacy(value TEXT)")
    before = paths.final_v4_database.read_bytes()

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == "plaintext_product_database_not_supported"
    assert paths.final_v4_database.read_bytes() == before
    assert store.create_calls == 0


def test_plaintext_document_directory_is_rejected_unchanged_before_keys(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)
    paths.documents.mkdir()
    sentinel = paths.documents / "legacy.txt"
    sentinel.write_bytes(b"unveraendert")

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == "plaintext_product_documents_not_supported"
    assert sentinel.read_bytes() == b"unveraendert"
    assert store.create_calls == 0
    assert not paths.keyset_metadata.exists()


@requires_exact_417
@pytest.mark.parametrize(
    "damage",
    ["wrong_dmk", "missing_dmk", "access_denied", "envelope"],
)
def test_product_restart_rejects_key_damage_without_regeneration(
    tmp_path: Path,
    damage: str,
) -> None:
    paths, account, store = _case(tmp_path, protected=True)
    _open(paths, account, store, first_run_allowed=True)
    activate_pilot_product_root(paths.root)
    main_hash = hashlib.sha256(paths.final_v4_database.read_bytes()).hexdigest()
    companion_hash = hashlib.sha256(
        paths.document_companion_database.read_bytes()
    ).hexdigest()
    if damage == "wrong_dmk":
        identity = next(iter(store.values))
        store.values[identity] = os.urandom(32)
    elif damage == "missing_dmk":
        store.values.clear()
    elif damage == "access_denied":
        store.read = lambda **_kwargs: DataMasterKeyReadResult(
            DataMasterKeyStoreStatus.ACCESS_DENIED
        )
    else:
        paths.database_key_envelope_registry.write_bytes(b"damaged-envelope")

    expected_codes = {
        "wrong_dmk": "data_master_key_corrupt",
        "missing_dmk": "data_master_key_not_found",
        "access_denied": "data_master_key_access_denied",
        "envelope": "database_key_envelope_registry_invalid",
    }
    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == expected_codes[damage]
    assert caught.value.operation.value == "load_keys"
    assert store.create_calls == 1
    assert hashlib.sha256(paths.final_v4_database.read_bytes()).hexdigest() == main_hash
    assert (
        hashlib.sha256(paths.document_companion_database.read_bytes()).hexdigest()
        == companion_hash
    )


@requires_exact_417
def test_product_restart_rejects_unknown_newer_schema_without_recreation(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path, protected=True)
    opened = _open(paths, account, store, first_run_allowed=True)
    activate_pilot_product_root(paths.root)
    with closing(opened.database.connect()) as connection:
        connection.execute("PRAGMA user_version = 99")
        connection.commit()
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            paths.final_v4_database,
            paths.document_companion_database,
            paths.keyset_metadata,
            paths.database_key_envelope_registry,
        )
    }

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == "final_v4_sqlcipher_schema_incompatible"
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in before
    } == before


@requires_exact_417
@pytest.mark.parametrize("missing", ["main", "companion"])
def test_completed_runtime_rejects_missing_database_without_recreation(
    tmp_path: Path,
    missing: str,
) -> None:
    paths, account, store = _case(tmp_path, protected=True)
    _open(paths, account, store, first_run_allowed=True)
    activate_pilot_product_root(paths.root)
    target = (
        paths.final_v4_database
        if missing == "main"
        else paths.document_companion_database
    )
    target.unlink()

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == "cipher_product_runtime_partial"
    assert not target.exists()
    assert store.create_calls == 1


def test_sqlcipher_412_configuration_is_rejected_without_product_files(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)
    provider = SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_SPIKE_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_SPIKE_ENGINE_VERSION,
    )

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(
            paths,
            account,
            store,
            first_run_allowed=True,
            provider=provider,
        )

    assert caught.value.code == "sqlcipher_417_provider_configuration_invalid"
    assert store.create_calls == 0
    assert not paths.final_v4_database.exists()


def test_missing_sqlcipher_never_uses_standard_sqlite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths, account, store = _case(tmp_path)

    def missing_driver():
        raise ImportError("missing")

    provider = SQLCipherConnectionProvider(
        expected_binding_version=SQLCIPHER_4_17_BINDING_VERSION,
        expected_engine_version=SQLCIPHER_4_17_ENGINE_VERSION,
        driver_loader=missing_driver,
        binding_version_loader=lambda: SQLCIPHER_4_17_BINDING_VERSION,
    )
    monkeypatch.setattr(
        SQLiteConnectionProvider,
        "connect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("SQLite fallback reached")
        ),
    )

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(
            paths,
            account,
            store,
            first_run_allowed=True,
            provider=provider,
        )

    assert caught.value.code == "sqlcipher_unavailable"
    assert caught.value.operation.value == "verify_engine"
    assert store.create_calls == 0
    assert not paths.final_v4_database.exists()
    assert not paths.database.exists()


def test_runtime_paths_register_cipher_roles_without_creating_them(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "paths").resolve()
    paths = runtime_paths(root)
    roles = {
        "key_runtime_metadata": "security-key-runtime-v1",
        "keyset_metadata": "security-key-runtime-v1/data-keysets.sqlite",
        "database_key_envelope_registry": (
            "security-key-runtime-v1/database-key-envelopes-v1.json"
        ),
        "final_v4_runtime": "final-v4-sqlcipher-runtime-v1",
        "final_v4_database": (
            "final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher"
        ),
        "document_companion_database": (
            "final-v4-sqlcipher-runtime-v1/documents-v1.sqlcipher"
        ),
        "encrypted_document_storage": (
            "final-v4-sqlcipher-runtime-v1/document-containers-v1"
        ),
        "backups": "backups",
    }
    for role, relative in roles.items():
        path = getattr(paths, role)
        assert path == root / relative
        assert path.is_relative_to(root)
        assert not path.exists()
        assert "key_material" not in str(path)


def test_cipher_mode_blocks_zip_v1_adapter_entrypoints(tmp_path: Path) -> None:
    root = (tmp_path / "blocked").resolve()
    paths = runtime_paths(root)
    adapter = BackupRestoreDesktopAdapter(
        paths,
        app_version="test",
        backup_service=object(),
        restore_service=object(),
        enabled=False,
    )
    calls = (
        lambda: adapter.create_backup_operation(root),
        adapter.discover_verified_backups_operation,
        lambda: adapter.verify_backup_operation(root / "legacy.jkmbackup"),
        lambda: adapter.verify_restore_operation(root / "legacy.jkmbackup"),
        lambda: adapter.prepare_restore_operation(root / "legacy.jkmbackup"),
        lambda: adapter.verify_prepared_restore_operation("restore-id"),
        lambda: adapter.create_restore_safety_backup_operation("restore-id"),
        lambda: adapter.create_restore_handoff(SimpleNamespace(restore_id="x")),
        lambda: adapter.launch_prepared_restore(SimpleNamespace()),
    )
    for call in calls:
        with pytest.raises(CipherBackupRestoreUnavailableError) as caught:
            call()
        assert caught.value.code == "cipher_backup_restore_not_available"


def test_product_main_activates_only_encrypted_backup_restore_services() -> None:
    source = inspect.getsource(desktop_main.main)
    product_start = source.index("encrypted_backup_service =")
    product_end = source.index("window.security_coordinator =")
    product_composition = source[product_start:product_end]
    assert "build_final_v4_encrypted_backup_service" in product_composition
    assert "FinalV4EncryptedBackupApplicationService" in product_composition
    assert "FinalV4EncryptedRestoreApplicationService" in product_composition
    assert 'backup_extension=".jkmebackup"' in product_composition
    assert "backup_restore_available=True" in product_composition
    assert "configure_school_year_transition_activation" in product_composition
    assert "BackupApplicationService()" not in product_composition
    assert "RestoreApplicationService()" not in product_composition
    assert "FinalV4PreAuthRecoveryFactory" in source
    assert "FinalV4SupportResetBackupFactory" in product_composition


def test_importing_product_shell_does_not_create_a_database(tmp_path: Path) -> None:
    data_root = (tmp_path / "import-only").resolve()
    environment = dict(os.environ)
    environment["JENAPLAN_APP_DATA_DIR"] = str(data_root)
    result = subprocess.run(
        [sys.executable, "-c", "import src.desktop_app.app"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not data_root.exists()
