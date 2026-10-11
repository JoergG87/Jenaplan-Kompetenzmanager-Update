from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace

import pytest

from scripts.prepare_macos_pilot_payload import prepare_payload
from scripts.seed_test_data import SeedDataError, seed_cipher_pilot_test_data, seed_test_data
from prototypes.database_encryption_migration.synthetic_data import (
    create_synthetic_source,
)
from src.core.final_v4_schema import FinalV4SchemaError, FinalV4SchemaInitializer
from src.core.sqlite_store import (
    SQLiteCompetencyRepository,
    SQLiteDatabase,
    seed_reference_data,
)
from src.core.runtime_root_protection import (
    RUNTIME_ROOT_PROTECTION_MARKER,
    RUNTIME_ROOT_PROTECTION_PENDING,
    RuntimeRootKind,
    RuntimeRootLifecycle,
    RuntimeRootProtectionError,
    activate_pilot_product_root,
    inspect_runtime_root,
    prepare_synthetic_test_root,
    publish_pilot_product_root,
    publish_synthetic_test_root,
    require_disposable_tree,
    require_product_runtime_root,
    require_unprotected_output_path,
    require_mutable_test_root,
)


def test_external_downloads_allows_generic_home_folders_only(monkeypatch, tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    for name in ('documents', 'backups', 'exports', 'logs', 'Downloads'):
        (home / name).mkdir()
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))
    require_unprotected_output_path(home / 'Downloads' / 'overview.pdf')
    # This exception is exclusive to output-container inspection.
    with pytest.raises(RuntimeRootProtectionError):
        require_mutable_test_root(home)
    (home / 'security-key-runtime-v1').mkdir()
    with pytest.raises(RuntimeRootProtectionError):
        require_unprotected_output_path(home / 'Downloads' / 'overview.pdf')


def test_external_downloads_still_rejects_nested_unmarked_evidence(monkeypatch, tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    downloads = home / 'Downloads'
    downloads.mkdir()
    (downloads / 'documents').mkdir()
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))
    with pytest.raises(RuntimeRootProtectionError):
        require_unprotected_output_path(downloads / 'overview.pdf')
from src.desktop_app.main import (
    _preflight_desktop_runtime_root,
    _require_existing_product_security,
)
from src.desktop_app.runtime import (
    RuntimeStorageError,
    prepare_runtime_storage,
    prepare_security_runtime_storage,
    runtime_paths,
)
import src.security.packaged_keychain_smoke as packaged_keychain_smoke
from src.security.packaged_keychain_smoke import (
    APP_DATA_DIR_ENV as KEYCHAIN_APP_DATA_DIR_ENV,
    PACKAGED_SMOKE_MARKER_ENV as KEYCHAIN_SMOKE_MARKER_ENV,
    PACKAGED_SMOKE_MARKER_VALUE as KEYCHAIN_SMOKE_MARKER_VALUE,
    _new_environment as new_keychain_smoke_environment,
    _validated_root as validated_keychain_smoke_root,
)
from tests.helpers.final_v3_document_runtime_worker import setup as setup_final_v3_worker
from tests.helpers.sprint10_document_crash_worker import _setup as setup_sprint10_worker
from tests.helpers.sprint9_backup_crash_worker import run as run_sprint9_worker


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protected_root(tmp_path: Path) -> Path:
    root = (tmp_path / "pilot-product").resolve()
    root.mkdir(mode=0o700)
    publish_pilot_product_root(root)
    activate_pilot_product_root(root)
    return root


def test_product_marker_is_atomic_versioned_and_lifecycle_bound(tmp_path: Path) -> None:
    root = (tmp_path / "product").resolve()
    root.mkdir(mode=0o700)

    initializing = publish_pilot_product_root(root)
    assert initializing.kind is RuntimeRootKind.PILOT_PRODUCT
    assert initializing.lifecycle is RuntimeRootLifecycle.INITIALIZING
    assert not (root / RUNTIME_ROOT_PROTECTION_PENDING).exists()
    assert (root / RUNTIME_ROOT_PROTECTION_MARKER).stat().st_mode & 0o077 == 0

    active = activate_pilot_product_root(root)
    assert inspect_runtime_root(root) == active
    assert active.lifecycle is RuntimeRootLifecycle.ACTIVE
    with pytest.raises(
        RuntimeRootProtectionError,
        match="pilot_product_root_lifecycle_invalid",
    ):
        require_product_runtime_root(root, first_run=True)

    copied = (tmp_path / "copied-root").resolve()
    copied.mkdir()
    (copied / RUNTIME_ROOT_PROTECTION_MARKER).write_bytes(
        (root / RUNTIME_ROOT_PROTECTION_MARKER).read_bytes()
    )
    (copied / RUNTIME_ROOT_PROTECTION_MARKER).chmod(0o600)
    with pytest.raises(RuntimeRootProtectionError, match="runtime_root_protection_invalid"):
        inspect_runtime_root(copied)


def test_synthetic_authority_cannot_be_published_outside_system_temp() -> None:
    with pytest.raises(
        RuntimeRootProtectionError,
        match="synthetic_test_root_outside_temporary",
    ):
        publish_synthetic_test_root(Path.cwd().resolve())


def test_synthetic_authority_cannot_be_minted_below_protected_root(
    tmp_path: Path,
) -> None:
    product = _protected_root(tmp_path)
    child = product / "synthetic-bypass"
    child.mkdir()

    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        publish_synthetic_test_root(child)

    assert not (child / RUNTIME_ROOT_PROTECTION_MARKER).exists()


def test_configured_temp_root_inside_product_does_not_hide_product_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = _protected_root(tmp_path)
    configured_temp = product / "configured-temp"
    configured_temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(configured_temp))
    child = configured_temp / "synthetic-child"
    child.mkdir()
    database = child / "test.sqlite"
    before = tuple(product.rglob("*"))

    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        prepare_synthetic_test_root(child)
    with pytest.raises(FinalV4SchemaError, match="pilot_product_root_protected"):
        FinalV4SchemaInitializer().initialize(database)

    assert tuple(product.rglob("*")) == before


def test_initializing_product_root_allows_only_first_run_security_prepare(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "initializing-product").resolve()
    root.mkdir(mode=0o700)
    publish_pilot_product_root(root)

    paths = prepare_security_runtime_storage(data_root=root)

    assert paths.security.is_dir()
    assert inspect_runtime_root(root).lifecycle is RuntimeRootLifecycle.INITIALIZING


def test_incomplete_or_unclassified_product_state_blocks_before_security_write(
    tmp_path: Path,
) -> None:
    incomplete = (tmp_path / "incomplete").resolve()
    incomplete.mkdir()
    publish_pilot_product_root(incomplete)
    before = tuple(incomplete.iterdir())
    with pytest.raises(
        RuntimeRootProtectionError,
        match="pilot_product_root_initialization_incomplete",
    ):
        _preflight_desktop_runtime_root(incomplete, packaged_smoke=False)
    assert tuple(incomplete.iterdir()) == before

    unclassified = (tmp_path / "unclassified").resolve()
    (unclassified / "final-v4-sqlcipher-runtime-v1").mkdir(parents=True)
    before = tuple(unclassified.rglob("*"))
    with pytest.raises(
        RuntimeRootProtectionError,
        match="runtime_root_protection_missing",
    ):
        _preflight_desktop_runtime_root(unclassified, packaged_smoke=False)
    assert tuple(unclassified.rglob("*")) == before
    with pytest.raises(
        SeedDataError,
        match="pilot_product_root_evidence_unclassified",
    ):
        seed_test_data(unclassified / "test.sqlite", reset=True)
    assert tuple(unclassified.rglob("*")) == before


def test_active_product_missing_security_is_rejected_without_creation(
    tmp_path: Path,
) -> None:
    root = _protected_root(tmp_path)
    paths = runtime_paths(root)

    with pytest.raises(
        RuntimeRootProtectionError,
        match="pilot_product_security_incomplete",
    ):
        _require_existing_product_security(paths)

    assert not paths.security.exists()


def test_legacy_developer_storage_prepare_cannot_mutate_product_root(
    tmp_path: Path,
) -> None:
    root = _protected_root(tmp_path)

    with pytest.raises(RuntimeStorageError, match="pilot_product_root_protected"):
        prepare_runtime_storage(data_root=root)
    with pytest.raises(RuntimeStorageError, match="pilot_product_root_protected"):
        prepare_security_runtime_storage(data_root=root)

    assert not (root / "documents").exists()
    assert not (root / "exports").exists()


@pytest.mark.parametrize("product_state", ["empty", "system", "student"])
@pytest.mark.parametrize("reset", [False, True])
def test_plain_seed_and_reset_are_blocked_before_product_mutation(
    tmp_path: Path,
    product_state: str,
    reset: bool,
) -> None:
    root = _protected_root(tmp_path)
    database = root / "kompetenzmanager.sqlite"
    if product_state == "system":
        (root / "security").mkdir()
        (root / "security" / "security.sqlite").write_bytes(b"system-state")
    elif product_state == "student":
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE students(student_id TEXT PRIMARY KEY)")
            connection.execute("INSERT INTO students VALUES ('REAL-001')")
    before = tuple(sorted((path.relative_to(root), _sha256(path)) for path in root.rglob("*") if path.is_file()))

    with pytest.raises(SeedDataError, match="pilot_product_root_protected"):
        seed_test_data(database, reset=reset)

    after = tuple(sorted((path.relative_to(root), _sha256(path)) for path in root.rglob("*") if path.is_file()))
    assert after == before
    assert not (root / "documents").exists()


@pytest.mark.parametrize("product_state", ["empty", "system", "student"])
def test_comparison_seed_rejects_every_protected_product_state(
    tmp_path: Path,
    product_state: str,
) -> None:
    root = _protected_root(tmp_path)
    if product_state == "system":
        (root / "security").mkdir()
        (root / "security" / "security.sqlite").write_bytes(b"system-state")
    elif product_state == "student":
        with sqlite3.connect(root / "student-state.sqlite") as connection:
            connection.execute("CREATE TABLE students(student_id TEXT PRIMARY KEY)")
            connection.execute("INSERT INTO students VALUES ('REAL-001')")
    opened = SimpleNamespace(database=SimpleNamespace(path=root / "unused.sqlcipher"))
    before = tuple(
        sorted(
            (path.relative_to(root), _sha256(path))
            for path in root.rglob("*")
            if path.is_file()
        )
    )

    with pytest.raises(SeedDataError, match="cipher_seed_test_root_authority_required"):
        seed_cipher_pilot_test_data(opened, source_root=root)

    after = tuple(
        sorted(
            (path.relative_to(root), _sha256(path))
            for path in root.rglob("*")
            if path.is_file()
        )
    )
    assert after == before


def test_schema_recreate_rejects_existing_product_database_unchanged(
    tmp_path: Path,
) -> None:
    root = _protected_root(tmp_path)
    database = root / "existing-final-v4.sqlcipher"
    database.write_bytes(b"existing-encrypted-product-bytes")
    before = _sha256(database)

    with pytest.raises(FinalV4SchemaError, match="final_v4_target_must_not_exist"):
        FinalV4SchemaInitializer().initialize(database)

    assert _sha256(database) == before


def test_low_level_schema_and_seed_creators_block_missing_product_database(
    tmp_path: Path,
) -> None:
    root = _protected_root(tmp_path)
    runtime_directory = root / "final-v4-sqlcipher-runtime-v1"
    runtime_directory.mkdir()
    database = runtime_directory / "missing-final-v4.sqlcipher"
    before = tuple(root.rglob("*"))

    with pytest.raises(FinalV4SchemaError, match="pilot_product_root_protected"):
        FinalV4SchemaInitializer().initialize(database)
    with pytest.raises(RuntimeError, match="pilot_product_root_protected"):
        SQLiteDatabase(root / "missing-seed.sqlite").replace_seed_data(
            seed_reference_data()
        )

    assert tuple(root.rglob("*")) == before
    assert not database.exists()
    assert not (root / "missing-seed.sqlite").exists()


def test_default_initializers_cannot_mutate_compatible_active_product_database(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "active-compatible-product").resolve()
    root.mkdir()
    publish_pilot_product_root(root)
    database_path = root / "existing.sqlite"
    with sqlite3.connect(database_path) as connection:
        FinalV4SchemaInitializer.initialize_connection(connection)
    activate_pilot_product_root(root)
    database = SQLiteDatabase(database_path, create=False)
    before = _sha256(database_path)

    with pytest.raises(RuntimeError, match="pilot_product_root_protected"):
        database.ensure_master_data_defaults()
    with pytest.raises(RuntimeError, match="pilot_product_root_protected"):
        SQLiteCompetencyRepository(database).ensure_catalog_defaults(())

    assert _sha256(database_path) == before


def test_synthetic_helpers_block_protected_root_and_descendants(
    tmp_path: Path,
) -> None:
    root = _protected_root(tmp_path)
    before = tuple(root.rglob("*"))

    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        create_synthetic_source(root / "migration-child" / "source.sqlite")
    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        setup_sprint10_worker(root / "document-child")
    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        setup_final_v3_worker(root)
    assert run_sprint9_worker(["write", "writer_after_header", str(root)]) == 2

    assert tuple(root.rglob("*")) == before


def test_keychain_smoke_accepts_prepared_synthetic_root(tmp_path: Path) -> None:
    root = (tmp_path / "jenaplan-keychain-smoke-synthetic").resolve()
    prepare_synthetic_test_root(root)

    validated = validated_keychain_smoke_root(
        {
            KEYCHAIN_APP_DATA_DIR_ENV: str(root),
            KEYCHAIN_SMOKE_MARKER_ENV: KEYCHAIN_SMOKE_MARKER_VALUE,
        }
    )

    assert validated == root
    protection = inspect_runtime_root(root)
    assert protection is not None
    assert protection.kind is RuntimeRootKind.SYNTHETIC_TEST


def test_keychain_smoke_new_environment_accepts_prepared_synthetic_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "jenaplan-keychain-smoke-environment").resolve()
    prepare_synthetic_test_root(root)

    def reached_prepare_paths(candidate: Path):
        assert candidate == root
        raise RuntimeError("reached_prepare_paths")

    monkeypatch.setattr(
        packaged_keychain_smoke,
        "_prepare_paths",
        reached_prepare_paths,
    )

    with pytest.raises(RuntimeError, match="reached_prepare_paths"):
        new_keychain_smoke_environment(root)


def test_keychain_smoke_cleanup_cannot_accept_product_root(tmp_path: Path) -> None:
    root = (tmp_path / "jenaplan-keychain-smoke-product").resolve()
    root.mkdir()
    publish_pilot_product_root(root)
    activate_pilot_product_root(root)

    with pytest.raises(RuntimeError, match="keychain_smoke_test_root_unmarked"):
        validated_keychain_smoke_root(
            {
                KEYCHAIN_APP_DATA_DIR_ENV: str(root),
                KEYCHAIN_SMOKE_MARKER_ENV: KEYCHAIN_SMOKE_MARKER_VALUE,
            }
        )


def test_partial_marker_and_protected_descendant_block_cleanup(tmp_path: Path) -> None:
    partial = (tmp_path / "partial").resolve()
    partial.mkdir()
    (partial / RUNTIME_ROOT_PROTECTION_PENDING).write_bytes(b"partial")
    with pytest.raises(RuntimeRootProtectionError, match="runtime_root_protection_partial"):
        require_disposable_tree(partial)

    output = (tmp_path / "build-output").resolve()
    protected = output / "nested-product"
    protected.mkdir(parents=True)
    publish_pilot_product_root(protected)
    activate_pilot_product_root(protected)
    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        require_disposable_tree(output)


def test_payload_builder_never_replaces_existing_protected_root(tmp_path: Path) -> None:
    root = _protected_root(tmp_path)
    sentinel = root / "existing.bin"
    sentinel.write_bytes(b"keep")

    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        prepare_payload(
            root,
            data_mode="release",
            version="test",
            git_commit="test",
            source_tree_state="clean",
            architecture="arm64",
        )
    with pytest.raises(RuntimeRootProtectionError, match="pilot_product_root_protected"):
        prepare_payload(
            root / "nested-output",
            data_mode="release",
            version="test",
            git_commit="test",
            source_tree_state="clean",
            architecture="arm64",
        )

    assert sentinel.read_bytes() == b"keep"
    assert not (root / "nested-output").exists()
    assert inspect_runtime_root(root).kind is RuntimeRootKind.PILOT_PRODUCT


def test_synthetic_root_remains_seedable_and_resettable(tmp_path: Path) -> None:
    root = (tmp_path / "synthetic").resolve()
    prepare_synthetic_test_root(root)
    database = root / "test.sqlite"

    first = seed_test_data(database)
    second = seed_test_data(database, reset=True)

    assert first.student_count == second.student_count > 0
    assert inspect_runtime_root(root).kind is RuntimeRootKind.SYNTHETIC_TEST
