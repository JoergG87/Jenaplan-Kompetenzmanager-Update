from __future__ import annotations

from contextlib import closing
from datetime import UTC, date, datetime
import hashlib
import importlib.metadata
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import uuid

import pytest

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
from src.desktop_app.main import _build_cipher_product_student_adapter
from src.desktop_app.runtime import runtime_paths
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


def _case(tmp_path: Path):
    root = (tmp_path / "product-runtime").resolve()
    root.mkdir(mode=0o700)
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


@requires_exact_417
def test_exact_417_product_first_run_is_empty_and_keyed(tmp_path: Path) -> None:
    paths, account, store = _case(tmp_path)

    opened = _open(paths, account, store, first_run_allowed=True)

    assert opened.first_run is True
    assert opened.installation_id == account.installation_id
    assert opened.runtime.final_v3.compatibility.cipher_version == (
        SQLCIPHER_4_17_ENGINE_VERSION
    )
    assert opened.runtime.final_v3.compatibility.cipher_provider == "commoncrypto"
    assert opened.runtime.final_v3.compatibility.sqlite_version == (
        SQLCIPHER_4_17_SQLITE_VERSION
    )
    assert opened.database is opened.runtime.final_v3.database
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
    assert not paths.final_v3_database.read_bytes().startswith(b"SQLite format 3\x00")
    assert not paths.document_companion_database.read_bytes().startswith(
        b"SQLite format 3\x00"
    )
    assert b"2026/27" not in paths.final_v3_database.read_bytes()
    assert not paths.database.exists()
    assert not paths.documents.exists()
    assert store.create_calls == 1


@requires_exact_417
def test_product_restart_reuses_contexts_key_and_school_year(tmp_path: Path) -> None:
    paths, account, store = _case(tmp_path)
    first = _open(paths, account, store, first_run_allowed=True)

    restarted = _open(paths, account, store, first_run_allowed=False)

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
    raw = paths.final_v3_database.read_bytes()
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
    assert not paths.final_v3_database.exists()


def test_plaintext_at_final_v3_product_path_is_rejected_before_keys(
    tmp_path: Path,
) -> None:
    paths, account, store = _case(tmp_path)
    paths.final_v3_runtime.mkdir(mode=0o700)
    with sqlite3.connect(paths.final_v3_database) as connection:
        connection.execute("CREATE TABLE legacy(value TEXT)")
    before = paths.final_v3_database.read_bytes()

    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == "plaintext_product_database_not_supported"
    assert paths.final_v3_database.read_bytes() == before
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
@pytest.mark.parametrize("damage", ["wrong_dmk", "missing_dmk", "envelope"])
def test_product_restart_rejects_key_damage_without_regeneration(
    tmp_path: Path,
    damage: str,
) -> None:
    paths, account, store = _case(tmp_path)
    _open(paths, account, store, first_run_allowed=True)
    main_hash = hashlib.sha256(paths.final_v3_database.read_bytes()).hexdigest()
    companion_hash = hashlib.sha256(
        paths.document_companion_database.read_bytes()
    ).hexdigest()
    if damage == "wrong_dmk":
        identity = next(iter(store.values))
        store.values[identity] = os.urandom(32)
    elif damage == "missing_dmk":
        store.values.clear()
    else:
        paths.database_key_envelope_registry.write_bytes(b"damaged-envelope")

    expected_codes = {
        "wrong_dmk": "data_master_key_corrupt",
        "missing_dmk": "data_master_key_not_found",
        "envelope": "database_key_envelope_registry_invalid",
    }
    with pytest.raises(CipherProductRuntimeError) as caught:
        _open(paths, account, store, first_run_allowed=False)

    assert caught.value.code == expected_codes[damage]
    assert caught.value.operation.value == "load_keys"
    assert store.create_calls == 1
    assert hashlib.sha256(paths.final_v3_database.read_bytes()).hexdigest() == main_hash
    assert (
        hashlib.sha256(paths.document_companion_database.read_bytes()).hexdigest()
        == companion_hash
    )


@requires_exact_417
@pytest.mark.parametrize("missing", ["main", "companion"])
def test_completed_runtime_rejects_missing_database_without_recreation(
    tmp_path: Path,
    missing: str,
) -> None:
    paths, account, store = _case(tmp_path)
    _open(paths, account, store, first_run_allowed=True)
    target = (
        paths.final_v3_database
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
    assert not paths.final_v3_database.exists()


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
    assert not paths.final_v3_database.exists()
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
        "final_v3_runtime": "final-v3-sqlcipher-runtime-v1",
        "final_v3_database": (
            "final-v3-sqlcipher-runtime-v1/final-v3.sqlcipher"
        ),
        "document_companion_database": (
            "final-v3-sqlcipher-runtime-v1/documents-v1.sqlcipher"
        ),
        "encrypted_document_storage": (
            "final-v3-sqlcipher-runtime-v1/document-containers-v1"
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
