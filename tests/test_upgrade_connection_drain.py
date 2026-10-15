"""Physical connection evidence with the actual qualified SQLCipher runtime."""
from contextlib import closing
import threading

import pytest

from src.core.maintenance_gate import (ConnectionDrain, MaintenanceGate,
    MaintenanceGateError, MaintenancePurpose)
from src.core.sqlite_store import SQLiteDatabase
from tests.helpers.qualified_sqlcipher_provider import qualified_sqlcipher_test_provider


@pytest.fixture
def setup(tmp_path):
    path = tmp_path.resolve() / "main.sqlcipher"
    path.parent.chmod(0o700)
    provider = qualified_sqlcipher_test_provider()
    key = bytes(range(32))
    with closing(provider.connect(path, create=True, key_material=key)) as c:
        c.execute("CREATE TABLE evidence(value)")
        c.execute("INSERT INTO evidence VALUES (1)")
        c.commit()
    gate = MaintenanceGate()
    capability = gate.request_maintenance(owner_id="test", purpose=MaintenancePurpose.SCHEMA_UPGRADE)
    assert gate.activate(capability, owner_id="test")
    authority = [True]
    def require_authority():
        if not authority[0]:
            raise MaintenanceGateError("test_authority_lost")
    drain = ConnectionDrain([path], gate=gate, capability=capability,
        owner_id="test", require_authority=require_authority)
    return path, provider, key, gate, drain, authority


def opener(setup):
    path, provider, key, *_ = setup
    return lambda: provider.connect(path, create=False, key_material=key)


@pytest.mark.parametrize("transaction", [False, True])
def test_reader_and_open_transaction_block(setup, transaction):
    path, provider, key, gate, drain, _ = setup
    connection = opener(setup)()
    if transaction:
        connection.execute("BEGIN")
    connection.execute("SELECT * FROM evidence").fetchall()
    with pytest.raises(MaintenanceGateError, match="upgrade_connections_active"):
        drain.__enter__()
    assert connection.in_transaction is transaction
    with pytest.raises(MaintenanceGateError, match="open_frozen"):
        qualified_sqlcipher_test_provider().connect_read_only(path, key_material=key)
    connection.close()
    drain.checkpoint(path, opener(setup))
    drain.require_drained()
    drain.release()


def test_runtime_connection_closed_aborted_writer(setup):
    path, provider, key, gate, drain, _ = setup
    class BoundProvider:
        def connect(self, path, *, create):
            return provider.connect(path, create=create, key_material=key)
    db = SQLiteDatabase(path, connection_provider=BoundProvider(), create=False,
                        initialize_schema=False)
    connection = db.connect()
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO evidence VALUES (2)")
    with pytest.raises(MaintenanceGateError, match="connections_active"):
        drain.__enter__()
    connection.rollback()
    connection.close()
    drain.checkpoint(path, opener(setup))
    with drain.maintenance_connections(), closing(opener(setup)()) as c:
        assert c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 1
    drain.require_drained()
    drain.release()


def test_freeze_persists_after_exit_and_rejects_other_thread(setup):
    path, provider, key, gate, drain, _ = setup
    with drain:
        drain.checkpoint(path, opener(setup))
        drain.require_drained()
    failures = []
    def other_thread():
        try:
            opener(setup)()
        except MaintenanceGateError as error:
            failures.append(error.code)
    thread = threading.Thread(target=other_thread)
    thread.start(); thread.join()
    assert failures == ["upgrade_connection_open_frozen"]
    drain.release()


def test_lost_authority_blocks_checkpoint_and_release(setup):
    path, _, _, _, drain, authority = setup
    drain.__enter__()
    authority[0] = False
    with pytest.raises(MaintenanceGateError, match="authority_lost"):
        drain.checkpoint(path, opener(setup))
    with pytest.raises(MaintenanceGateError, match="authority_lost"):
        drain.release()
    authority[0] = True
    drain.release()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecar_is_preserved_and_blocks(setup, suffix):
    path, _, _, _, drain, _ = setup
    drain.__enter__()
    drain.checkpoint(path, opener(setup))
    sidecar = path.with_name(path.name + suffix)
    sidecar.write_bytes(b"unexplained")
    with pytest.raises(MaintenanceGateError, match="sidecar_present"):
        drain.require_drained()
    assert sidecar.read_bytes() == b"unexplained"
    drain.release()


def test_checkpoint_required(setup):
    *_, drain, authority = setup
    drain.__enter__()
    with pytest.raises(MaintenanceGateError, match="checkpoint_required"):
        drain.require_drained()
    drain.release()


def test_unclosed_privileged_connection_remains_blocker(setup):
    path, _, _, _, drain, _ = setup
    drain.__enter__()
    connection = None
    with pytest.raises(MaintenanceGateError, match="connections_active"):
        with drain.maintenance_connections():
            connection = opener(setup)()
    connection.close()
    drain.checkpoint(path, opener(setup))
    drain.release()


def test_cursor_connection_preserves_tracking(setup):
    path, _, _, _, drain, _ = setup
    connection = opener(setup)()
    cursor = connection.execute("SELECT 1")
    assert cursor.connection is connection
    cursor.connection.close()
    drain.__enter__()
    drain.checkpoint(path, opener(setup))
    drain.release()


def test_privileged_verification_is_query_only(setup):
    path, _, _, _, drain, _ = setup
    drain.__enter__()
    with drain.maintenance_connections(), closing(opener(setup)()) as c:
        with pytest.raises(Exception, match="readonly"):
            c.execute("INSERT INTO evidence VALUES (99)")
    drain.checkpoint(path, opener(setup))
    drain.require_drained()
    drain.release()


def test_immutable_artifact_freeze_needs_only_runtime_checkpoint(setup):
    path, provider, key, gate, original, authority = setup
    artifact = path.with_name("rollback.sqlcipher")
    drain = ConnectionDrain([path, artifact], runtime_paths=[path],
        gate=gate, capability=original.capability, owner_id="test",
        require_authority=original._authority)
    drain.__enter__()
    with pytest.raises(MaintenanceGateError, match="open_frozen"):
        provider.connect(artifact, create=True, key_material=key)
    assert not artifact.exists()
    drain.checkpoint(path, opener(setup))
    drain.require_drained()
    drain.release()


@pytest.mark.parametrize("outcome", ["busy", "io"])
def test_checkpoint_failure_blocks_completion(setup, outcome):
    path, _, _, _, drain, _ = setup
    drain.__enter__()
    class CheckpointFault:
        def __init__(self, raw):
            self.raw = raw
        def __getattr__(self, name):
            return getattr(self.raw, name)
        def execute(self, statement):
            if outcome == "io":
                raise OSError("synthetic EIO")
            return self
        def fetchone(self):
            return (1, 4, 2)
        def close(self):
            self.raw.close()
    def faulted_open():
        connection = opener(setup)()
        object.__setattr__(connection, "_raw", CheckpointFault(connection._raw))
        return connection
    with pytest.raises((MaintenanceGateError, OSError)):
        drain.checkpoint(path, faulted_open)
    with pytest.raises(MaintenanceGateError, match="checkpoint_required"):
        drain.require_drained()
    drain.release()


def test_inflight_open_is_reserved_before_physical_connect(setup, monkeypatch):
    path, provider, key, gate, drain, _ = setup
    admitted, proceed = threading.Event(), threading.Event()
    original = provider._load_driver
    def delayed_driver():
        admitted.set()
        assert proceed.wait(5)
        return original()
    monkeypatch.setattr(provider, "_load_driver", delayed_driver)
    failures = []
    def existing_open():
        try:
            with closing(opener(setup)()) as c:
                assert c.execute("SELECT 1").fetchone()[0] == 1
        except BaseException as error:
            failures.append(error)
    thread = threading.Thread(target=existing_open)
    thread.start()
    assert admitted.wait(5)
    try:
        with pytest.raises(MaintenanceGateError, match="connections_active"):
            drain.__enter__()
        with pytest.raises(MaintenanceGateError, match="open_frozen"):
            qualified_sqlcipher_test_provider().connect_read_only(path, key_material=key)
    finally:
        proceed.set()
        thread.join(5)
    assert not thread.is_alive()
    assert not failures
    drain.checkpoint(path, opener(setup))
    drain.release()


def test_other_provider_hardlink_cannot_bypass_freeze(setup):
    import os
    path, provider, key, gate, drain, _ = setup
    alias = path.with_name("alias.sqlcipher")
    drain.__enter__()
    os.link(path, alias)
    try:
        with pytest.raises(Exception, match="open_frozen"):
            provider.connect_read_only(alias, key_material=key)
    finally:
        alias.unlink()
    drain.checkpoint(path, opener(setup))
    drain.release()


def test_checkpoint_cannot_substitute_another_database(setup):
    path, provider, key, gate, drain, _ = setup
    other = path.with_name("other.sqlcipher")
    with closing(provider.connect(other, create=True, key_material=key)) as c:
        c.execute("CREATE TABLE other(value)")
        c.commit()
    drain.__enter__()
    with pytest.raises(MaintenanceGateError, match="connection_mismatch"):
        drain.checkpoint(path, lambda: provider.connect(other, create=False, key_material=key))
    with pytest.raises(MaintenanceGateError, match="checkpoint_required"):
        drain.require_drained()
    drain.checkpoint(path, opener(setup))
    drain.release()


def test_preexisting_hardlink_handle_is_counted_after_alias_unlink(setup):
    import os
    from src.core.database_engine import SQLiteConnectionProvider
    path, provider, key, gate, drain, _ = setup
    alias = path.with_name("unlinked-alias.sqlcipher")
    os.link(path, alias)
    connection = SQLiteConnectionProvider().connect(alias, create=False)
    alias.unlink()
    with pytest.raises(MaintenanceGateError, match="connections_active"):
        drain.__enter__()
    connection.close()
    drain.checkpoint(path, opener(setup))
    drain.require_drained()
    drain.release()


def test_new_rollback_inode_is_enrolled_without_losing_original_freeze(setup):
    import os
    from src.core.database_engine import SQLiteConnectionProvider
    path, provider, key, gate, original, authority = setup
    rollback = path.with_name("rollback.sqlcipher")
    alias = path.with_name("rollback-alias.sqlcipher")
    drain = ConnectionDrain([path, rollback], runtime_paths=[path], gate=gate,
        capability=original.capability, owner_id="test",
        require_authority=original._authority)
    drain.__enter__()
    # Rollback publication copies encrypted bytes; it does not open SQLite.
    rollback.write_bytes(path.read_bytes())
    rollback.chmod(0o600)
    drain.require_frozen()
    os.link(rollback, alias)
    try:
        with pytest.raises(MaintenanceGateError, match="open_frozen"):
            SQLiteConnectionProvider().connect(alias, create=False)
    finally:
        alias.unlink()
    drain.checkpoint(path, opener(setup))
    drain.require_drained()
    drain.release()


@pytest.mark.parametrize("purpose", [MaintenancePurpose.BACKUP_RESTORE, MaintenancePurpose.SCHOOL_YEAR_TRANSITION])
def test_competing_maintenance_operation_blocks_upgrade(setup, purpose):
    path, provider, key, _, original, _ = setup
    gate = MaintenanceGate()
    capability = gate.request_maintenance(owner_id="existing-operation", purpose=purpose)
    assert gate.activate(capability, owner_id="existing-operation")
    with pytest.raises(MaintenanceGateError, match="request_not_available"):
        gate.request_maintenance(owner_id="upgrade", purpose=MaintenancePurpose.SCHEMA_UPGRADE)
    gate.abort(capability, owner_id="existing-operation")


def test_actual_parallel_encrypted_backup_blocks_upgrade(tmp_path):
    from tests.test_encrypted_upgrade_source import _open_case, _context
    from src.application.commands.schema_upgrade import UpgradeMaintenance
    from src.security.infrastructure.upgrade_process_lease import UpgradeProcessLease
    from src.core.restore_runtime import RuntimeInstanceLock
    runtime, service, *_ = _open_case(tmp_path)
    entered, proceed = threading.Event(), threading.Event()
    errors = []
    def pause(boundary):
        if boundary == "before_snapshot":
            entered.set()
            assert proceed.wait(10)
    service._fault_hook = pause
    def backup_worker():
        try:
            service.create(tmp_path / "parallel.jkmebackup")
        except BaseException as error:
            errors.append(error)
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        context = _context(service)
        lease = UpgradeProcessLease(lock, context, service.paths.final_v4.runtime_root / ".observation-staging")
        worker = threading.Thread(target=backup_worker); worker.start()
        try:
            assert entered.wait(10)
            with pytest.raises(MaintenanceGateError, match="request_not_available"):
                with UpgradeMaintenance(service._gate, lease, context):
                    pytest.fail("competing upgrade was admitted")
        finally:
            proceed.set(); worker.join(20)
    assert not worker.is_alive() and not errors
    assert (tmp_path / "parallel.jkmebackup").is_file()
