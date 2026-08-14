from __future__ import annotations

from dataclasses import replace
import hashlib
from importlib.util import find_spec
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest

from prototypes.database_encryption_migration.sprint8_orchestrator import (
    Sprint8MigrationPaths,
    SyntheticMigrationOrchestratorV2,
)
from prototypes.database_encryption_migration.synthetic_data import (
    create_synthetic_source,
)
from src.core.database_engine import SQLCipherConnectionProvider
from src.core.runtime_root_protection import (
    activate_pilot_product_root,
    publish_pilot_product_root,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DatabaseKeyEnvelopeService,
    derive_database_key_registry_auth_key,
)
from src.security.infrastructure.database_key_envelope_repository import (
    DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.simplified_migration_state import (
    AuthenticatedMigrationJournalV2Repository,
    ExternalReplayAnchorV2Repository,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)
from src.security.migration_lock import InMemoryMigrationLock
from src.security.simplified_migration import (
    SimplifiedMigrationError,
    SimplifiedMigrationPreflightMode,
)


pytestmark = pytest.mark.skipif(
    find_spec("sqlcipher3") is None,
    reason="real SQLCipher is required for the Sprint 8 synthetic path",
)


def test_product_root_never_authorizes_synthetic_migration(tmp_path: Path) -> None:
    root = (tmp_path / "product-root").resolve()
    root.mkdir(mode=0o700)
    publish_pilot_product_root(root)
    activate_pilot_product_root(root)
    before = tuple((path.relative_to(root), path.read_bytes()) for path in root.iterdir())
    orchestrator = object.__new__(SyntheticMigrationOrchestratorV2)
    orchestrator.paths = Sprint8MigrationPaths.in_test_root(root)
    orchestrator.allowed_private_root = root

    with pytest.raises(SimplifiedMigrationError, match="migration_root_not_synthetic"):
        orchestrator._require_root_and_fixed_paths()

    after = tuple((path.relative_to(root), path.read_bytes()) for path in root.iterdir())
    assert after == before


class _Fixture:
    def __init__(self, tmp_path: Path, *, fault=None, disk_free=None, permissions=None):
        self.root = tmp_path / "migration-root"
        self.root.mkdir(mode=0o700, parents=True)
        os.chmod(self.root, 0o700)
        self.paths = Sprint8MigrationPaths.in_test_root(self.root)
        create_synthetic_source(self.paths.source)
        os.chmod(self.paths.source, 0o600)
        self.installation_id = str(uuid4())
        self.database_context_id = str(uuid4())
        self.migration_id = str(uuid4())
        self.dmk = LoadedDataMasterKey(str(uuid4()), 1, secrets.token_bytes(32))
        self.permissions = PlatformFilePermissionManager()
        self.envelopes = FileDatabaseKeyEnvelopeRepository(
            self.root / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
            self.permissions,
        )
        self.envelope_service = DatabaseKeyEnvelopeService(
            repository=self.envelopes,
            random_source=SystemRandomSource(),
            clock=SystemClock(),
        )
        self.envelope_service.create_pending(
            self.dmk, database_context_id=self.database_context_id, generation=1
        )
        self.envelope_service.activate(self.dmk, generation=1)
        self.lock = InMemoryMigrationLock(
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            namespace=f"sprint8:{self.migration_id}",
        )
        self.anchor_path = tmp_path / "external-anchor-v2.json"
        self.provider = SQLCipherConnectionProvider()
        self._fault = fault
        self._disk_free = disk_free
        self._permissions = permissions

    def database_key_loader(self, dmk):
        key = self.envelope_service.load_active(dmk, expected_generation=1)
        registry_key = derive_database_key_registry_auth_key(
            dmk, database_context_id=self.database_context_id
        )
        _items, digest = self.envelopes.load_with_digest(registry_key)
        return key, digest

    def orchestrator(self, *, lock=None, fault=None):
        return SyntheticMigrationOrchestratorV2(
            paths=self.paths,
            allowed_private_root=self.root,
            installation_id=self.installation_id,
            database_context_id=self.database_context_id,
            migration_id=self.migration_id,
            migration_generation=1,
            dmk_loader=lambda: self.dmk,
            database_key_loader=self.database_key_loader,
            migration_lock=lock or self.lock,
            journal_repository=AuthenticatedMigrationJournalV2Repository(
                self.paths.journal
            ),
            anchor_repository=ExternalReplayAnchorV2Repository(self.anchor_path),
            sqlcipher_provider=self.provider,
            sqlcipher_version_probe=lambda: "4.12.0 community",
            app_instance_available=lambda: True,
            source_closed_probe=lambda _path: True,
            lock_chain_head_loader=lambda: hashlib.sha256(
                f"lock:{self.migration_id}".encode("ascii")
            ).hexdigest(),
            disk_free_probe=self._disk_free,
            permissions_probe=self._permissions,
            safety_reserve_bytes=1,
            fault_injector=fault or self._fault,
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_synthetic_migration_backup_reopen_and_swap_simulation(
    tmp_path: Path,
):
    fixture = _Fixture(tmp_path)
    source_before = fixture.paths.source.read_bytes()
    preflight = fixture.orchestrator().preflight()
    assert preflight.mode is SimplifiedMigrationPreflightMode.NEW

    report = fixture.orchestrator().run()

    assert report.final_phase == "completed"
    assert report.validation.successful
    assert report.reopened
    assert report.source_sha256_before == report.source_sha256_after
    assert fixture.paths.source.read_bytes() == source_before
    assert fixture.paths.backup.read_bytes() == source_before
    assert report.backup_sha256 == _sha256(fixture.paths.source)
    assert report.exchange.performed_on_copies
    assert report.exchange.predecessor_retained
    assert report.exchange.candidate_sha256 == report.exchange.post_swap_live_sha256
    assert (fixture.paths.exchange_directory / "plaintext-predecessor.sqlite").exists()

    with sqlite3.connect(f"file:{fixture.paths.target}?mode=ro", uri=True) as plain:
        with pytest.raises(sqlite3.DatabaseError):
            plain.execute("SELECT count(*) FROM sqlite_schema").fetchone()


def test_preflight_blocks_active_wal_or_shm_without_mutation(tmp_path: Path):
    fixture = _Fixture(tmp_path)
    sidecar = Path(str(fixture.paths.source) + "-wal")
    sidecar.write_bytes(b"foreign-active-session")
    before = sidecar.read_bytes()
    result = fixture.orchestrator().preflight()
    assert result.mode is SimplifiedMigrationPreflightMode.BLOCKED
    assert sidecar.read_bytes() == before
    assert not fixture.paths.backup.exists()
    assert not fixture.paths.target.exists()


def test_preflight_blocks_foreign_artifact_and_existing_backup(tmp_path: Path):
    fixture = _Fixture(tmp_path)
    foreign = fixture.root / "foreign.bin"
    foreign.write_bytes(b"foreign")
    result = fixture.orchestrator().preflight()
    assert result.mode is SimplifiedMigrationPreflightMode.BLOCKED
    assert foreign.read_bytes() == b"foreign"

    foreign.unlink()
    fixture.paths.backup.write_bytes(b"foreign-backup")
    os.chmod(fixture.paths.backup, 0o600)
    assert fixture.orchestrator().preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED
    assert fixture.paths.backup.read_bytes() == b"foreign-backup"


def test_preflight_blocks_enospc_permissions_and_competing_instance(tmp_path: Path):
    enospc = _Fixture(tmp_path / "a", disk_free=lambda _root: 0)
    assert enospc.orchestrator().preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED

    denied = _Fixture(tmp_path / "b", permissions=lambda _root: False)
    assert denied.orchestrator().preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED

    active_app = _Fixture(tmp_path / "active-app")
    active_app_orchestrator = active_app.orchestrator()
    active_app_orchestrator._app_instance_available = lambda: False
    assert active_app_orchestrator.preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED

    open_source = _Fixture(tmp_path / "open-source")
    open_source_orchestrator = open_source.orchestrator()
    open_source_orchestrator._source_closed_probe = lambda _path: False
    assert open_source_orchestrator.preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED

    busy = _Fixture(tmp_path / "c")
    foreign_lock = InMemoryMigrationLock(
        installation_id=busy.installation_id,
        database_context_id=busy.database_context_id,
        migration_id=busy.migration_id,
        namespace=f"sprint8:{busy.migration_id}",
    )
    foreign_lock.acquire()
    try:
        second = busy.orchestrator(lock=busy.lock).preflight()
        assert second.mode is SimplifiedMigrationPreflightMode.BLOCKED
    finally:
        foreign_lock.release()


def test_tampered_journal_and_replayed_old_journal_block(tmp_path: Path):
    fixture = _Fixture(tmp_path)
    fixture.orchestrator().run()
    final_bytes = fixture.paths.journal.read_bytes()
    fixture.paths.journal.write_bytes(final_bytes[:-1] + b"0")
    assert fixture.orchestrator().preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED


def test_replay_of_older_valid_journal_is_rejected_by_external_anchor(tmp_path: Path):
    fixture = _Fixture(tmp_path)

    def stop_after_backup(point: str) -> None:
        if point == "crash_after_backup_before_verification":
            raise RuntimeError("stop")

    with pytest.raises(RuntimeError):
        fixture.orchestrator(fault=stop_after_backup).run()
    old_authenticated_journal = fixture.paths.journal.read_bytes()
    fixture.orchestrator().recover()
    fixture.paths.journal.write_bytes(old_authenticated_journal)
    assert fixture.orchestrator().preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED


def test_fsync_and_replace_faults_preserve_source_and_are_recoverable(tmp_path: Path):
    fsync_fixture = _Fixture(tmp_path / "fsync")
    source_before = _sha256(fsync_fixture.paths.source)
    calls = 0

    def fail_first_operation_fsync(_descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated-fsync")
        os.fsync(_descriptor)

    failing_fsync = fsync_fixture.orchestrator()
    failing_fsync._fsync = fail_first_operation_fsync
    with pytest.raises(SimplifiedMigrationError):
        failing_fsync.run()
    assert _sha256(fsync_fixture.paths.source) == source_before
    fsync_fixture.orchestrator().recover()
    assert _sha256(fsync_fixture.paths.source) == source_before

    replace_fixture = _Fixture(tmp_path / "replace")
    replace_source_before = _sha256(replace_fixture.paths.source)

    def fail_swap_replace(source: Path, target: Path) -> None:
        if source.name == "live.sqlite":
            raise OSError("simulated-replace")
        os.replace(source, target)

    failing_replace = replace_fixture.orchestrator()
    failing_replace._replace_file = fail_swap_replace
    with pytest.raises(OSError):
        failing_replace.run()
    assert _sha256(replace_fixture.paths.source) == replace_source_before
    replace_fixture.orchestrator().recover()
    assert _sha256(replace_fixture.paths.source) == replace_source_before


def test_swapped_source_backup_or_target_blocks(tmp_path: Path):
    fixture = _Fixture(tmp_path)
    fixture.orchestrator().run()
    for path in (fixture.paths.source, fixture.paths.backup, fixture.paths.target):
        original = path.read_bytes()
        replacement = fixture.root / "replacement.bin"
        replacement.write_bytes(b"not-the-bound-artifact")
        os.replace(replacement, path)
        assert fixture.orchestrator().preflight().mode is SimplifiedMigrationPreflightMode.BLOCKED
        path.write_bytes(original)
        os.chmod(path, 0o600)


def test_no_identity_vfs_or_attach_dependency_in_product_orchestrator():
    source = Path(
        "prototypes/database_encryption_migration/sprint8_orchestrator.py"
    ).read_text("utf-8")
    lowered = source.lower()
    assert "native.identity_vfs" not in lowered
    assert "prototypes.identity_vfs" not in lowered
    assert "identityvf" not in lowered
    assert "attach database" not in lowered
    assert "sqlcipher_export" not in lowered
    assert "runtimepaths" not in lowered.replace("no product runtimepaths", "")

    for product_module in Path("src").rglob("*.py"):
        product_source = product_module.read_text("utf-8")
        assert "database_encryption_migration.sprint8_orchestrator" not in product_source
        assert "SyntheticMigrationOrchestratorV2" not in product_source


def test_wrong_sqlcipher_version_blocks_before_artifact_creation(tmp_path: Path):
    fixture = _Fixture(tmp_path)
    orchestrator = fixture.orchestrator()
    orchestrator._sqlcipher_version_probe = lambda: "4.17.0"
    result = orchestrator.preflight()
    assert result.mode is SimplifiedMigrationPreflightMode.BLOCKED
    assert not fixture.paths.backup.exists()
    assert not fixture.paths.target.exists()


@pytest.mark.parametrize(
    "crash_point",
    [
        "crash_before_backup",
        "crash_during_backup",
        "crash_after_backup_before_verification",
        "crash_during_target_creation",
        "crash_during_export",
        "crash_during_validation",
        "crash_before_reopen",
        "crash_after_reopen",
        "crash_before_simulated_swap",
        "crash_during_simulated_swap",
    ],
)
def test_real_process_crash_recovers_in_a_new_process(
    tmp_path: Path, crash_point: str
):
    fixture = _Fixture(tmp_path)
    source_before = _sha256(fixture.paths.source)
    config_path = tmp_path / "worker-config.json"
    result_path = tmp_path / "worker-result.json"
    config = {
        "anchor_path": str(fixture.anchor_path),
        "crash_point": crash_point,
        "database_context_id": fixture.database_context_id,
        "dmk_generation": fixture.dmk.generation,
        "dmk_hex": fixture.dmk.key_material.hex(),
        "dmk_key_id": fixture.dmk.key_id,
        "installation_id": fixture.installation_id,
        "migration_id": fixture.migration_id,
        "result_path": str(result_path),
        "root": str(fixture.root),
    }
    config_path.write_text(json.dumps(config), "ascii")
    worker = Path("tests/helpers/sprint8_crash_worker.py")
    crashed = subprocess.run(
        [sys.executable, str(worker), str(config_path)],
        cwd=Path.cwd(),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert crashed.returncode == 97, crashed.stderr
    assert _sha256(fixture.paths.source) == source_before

    config["crash_point"] = None
    config_path.write_text(json.dumps(config), "ascii")
    recovered = subprocess.run(
        [sys.executable, str(worker), str(config_path)],
        cwd=Path.cwd(),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert recovered.returncode == 0, recovered.stderr
    result = json.loads(result_path.read_text("ascii"))
    assert result["final_phase"] == "completed"
    assert result["source_sha256_before"] == result["source_sha256_after"]
    assert _sha256(fixture.paths.source) == source_before
    assert fixture.paths.backup.exists()
    assert fixture.paths.target.exists()
