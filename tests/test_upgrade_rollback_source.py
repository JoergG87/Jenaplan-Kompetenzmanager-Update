"""Durable rollback tests use the real qualified SQLCipher synthetic fixture."""
from dataclasses import replace
import os
from pathlib import Path
import pytest
from tests.test_encrypted_upgrade_source import case, _runner, _hash
from src.application.commands.schema_upgrade import UpgradeMaintenance
from src.core.schema_upgrade import UpgradeError
from src.security.infrastructure.upgrade_rollback_source import DurableUpgradeRollbackSource


def _prepared(case):
    _, service, lock, context = case
    runner, adapter, _, _ = _runner(service, lock, context)
    runner.execute()
    return runner, adapter, DurableUpgradeRollbackSource(adapter)


def test_real_encrypted_durable_rollback(case):
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        result = rollback.create(source, backup)
        assert result.role == "rollback" and result.artifact_id != source.artifact.artifact_id
        assert result.sha256 == source.artifact.sha256
        assert result.file_id != source.artifact.file_id
        assert rollback.rollback_path.stat().st_nlink == 1
        assert rollback.verify(source, backup, result) == result
        assert DurableUpgradeRollbackSource(adapter).verify(source, backup, result) == result
        with pytest.raises(UpgradeError, match="bound_receipt_required"):
            rollback.verify(source, backup)
        assert not rollback.rollback_path.read_bytes().startswith(b"SQLite format 3")
        with pytest.raises(UpgradeError, match="unbound"):
            rollback.create(source, backup)


@pytest.mark.parametrize("damage", ["source", "backup", "hardlink", "symlink", "parent", "partial", "wrong_key"])
def test_unsafe_or_changed_inputs_block(case, damage):
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        before = _hash(adapter.service.paths.final_v4.database)
        if damage in {"source", "backup"}:
            path = adapter.service.paths.final_v4.database if damage == "source" else adapter.backup_path
            data = bytearray(path.read_bytes()); data[len(data)//2] ^= 1; path.write_bytes(data)
        elif damage == "hardlink":
            os.link(adapter.service.paths.final_v4.database, rollback.rollback_path)
        elif damage == "symlink":
            rollback.rollback_path.symlink_to(adapter.service.paths.final_v4.database)
        elif damage == "parent":
            adapter.workspace.chmod(0o777)
        elif damage == "partial":
            rollback.temporary_path.write_bytes(b"interrupted encrypted copy")
        else:
            service = adapter.service
            service.loaded = replace(service.loaded, database_key=replace(service.loaded.database_key, key_material=os.urandom(32)))
        with pytest.raises(Exception):
            rollback.create(source, backup)
        if damage != "source":
            assert _hash(adapter.service.paths.final_v4.database) == before


@pytest.mark.parametrize("boundary", ["during_rollback_copy", "after_rollback_file_fsync", "before_rollback_publication", "after_rollback_publication", "after_rollback_directory_fsync"])
def test_interruption_never_returns_receipt_or_overwrites_source(case, boundary):
    runner, adapter, rollback = _prepared(case)
    def fault(value):
        if value == boundary:
            raise OSError("synthetic interrupted persistence")
    rollback._fault_hook = fault
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        before = _hash(adapter.service.paths.final_v4.database)
        with pytest.raises(OSError):
            rollback.create(source, backup)
        assert _hash(adapter.service.paths.final_v4.database) == before
        rollback._fault_hook = None
        with pytest.raises(UpgradeError, match="unbound"):
            rollback.create(source, backup)


def test_full_content_reopen_detects_rollback_change(case):
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        receipt = rollback.create(source, backup)
        with adapter.service._provider.connect(rollback.rollback_path, create=False,
                key_material=adapter.service.loaded.database_key.key_material) as connection:
            connection.execute("UPDATE students SET notes='synthetic changed content'")
            connection.commit()
        with pytest.raises(UpgradeError):
            rollback.verify(source, backup, receipt)


def _crash_rollback(directory, queue, boundary):
    import signal
    from tests.test_encrypted_upgrade_source import _open_case, _context
    from src.core.restore_runtime import RuntimeInstanceLock
    runtime, service, *_ = _open_case(Path(directory))
    with RuntimeInstanceLock(service.paths.final_v4.root) as lock:
        context = _context(service)
        runner, adapter, _, _ = _runner(service, lock, context)
        runner.execute()
        def pause(value):
            if value == boundary:
                queue.put((str(service.paths.final_v4.database), _hash(service.paths.final_v4.database),
                    str(rollback.rollback_path), str(rollback.temporary_path)))
                signal.pause()
        rollback = DurableUpgradeRollbackSource(adapter, fault_hook=pause)
        with UpgradeMaintenance(service._gate, runner.lease, context):
            source = adapter.verify_source()
            rollback.create(source, adapter.verify_backup(source))


@pytest.mark.parametrize("boundary", ["before_rollback_publication", "after_rollback_publication"])
def test_real_sigkill_rollback_persistence_boundary(tmp_path, boundary):
    import multiprocessing
    import signal
    spawn = multiprocessing.get_context("spawn"); queue = spawn.Queue()
    directory = tmp_path / "rollback-crash"; directory.mkdir()
    child = spawn.Process(target=_crash_rollback, args=(str(directory), queue, boundary))
    child.start()
    try:
        main, before, published, temporary = queue.get(timeout=45)
        os.kill(child.pid, signal.SIGKILL)
        child.join(15)
        assert child.exitcode == -signal.SIGKILL
        assert _hash(main) == before
        if boundary == "before_rollback_publication":
            assert not Path(published).exists() and Path(temporary).exists()
        else:
            assert Path(published).exists() and not Path(temporary).exists()
            assert _hash(published) == before
    finally:
        if child.is_alive():
            child.kill(); child.join(15)


@pytest.mark.parametrize("error", [28, 5, 13])
def test_publication_io_errors_preserve_source(case, monkeypatch, error):
    import src.security.infrastructure.upgrade_rollback_source as module
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        def fail(*args):
            raise OSError(error, "synthetic publication failure")
        monkeypatch.setattr(module, "_exclusive_rename", fail)
        with pytest.raises(OSError):
            rollback.create(source, backup)
        assert _hash(adapter.service.paths.final_v4.database) == source.artifact.sha256
        assert not rollback.rollback_path.exists()
        assert rollback.temporary_path.exists()



def test_missing_source_never_publishes_rollback(case):
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        adapter.service.paths.final_v4.database.unlink()
        with pytest.raises(FileNotFoundError):
            rollback.create(source, backup)
        assert not rollback.rollback_path.exists()


def test_foreign_uid_is_rejected_by_rollback_file_port(case, monkeypatch):
    from types import SimpleNamespace
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        receipt = rollback.create(source, backup)
        real = os.fstat
        def foreign(descriptor):
            value = real(descriptor)
            if value.st_ino == receipt.file_id:
                return SimpleNamespace(**{name: getattr(value, name) for name in dir(value) if name.startswith("st_")})
            return value
        def changed_uid(descriptor):
            value = foreign(descriptor)
            if value.st_ino == receipt.file_id:
                value.st_uid += 1
            return value
        monkeypatch.setattr(os, "fstat", changed_uid)
        with pytest.raises(UpgradeError, match="file_unsafe"):
            rollback.verify(source, backup, receipt)


@pytest.mark.parametrize("ancestor", ["operation", "workspace_parent", "root"])
def test_every_rollback_ancestor_fsync_failure_withholds_receipt(case, monkeypatch, ancestor):
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        before = _hash(adapter.service.paths.final_v4.database)
        target = {"operation": adapter.workspace, "workspace_parent": adapter.workspace.parent,
            "root": adapter.root}[ancestor].stat().st_ino
        original = os.fsync
        def fail(descriptor):
            if os.fstat(descriptor).st_ino == target:
                raise OSError(5, "synthetic ancestor fsync failure")
            original(descriptor)
        monkeypatch.setattr(os, "fsync", fail)
        with pytest.raises(OSError, match="ancestor fsync"):
            rollback.create(source, backup)
        assert _hash(adapter.service.paths.final_v4.database) == before


def test_rollback_receipt_requires_bottom_up_ancestor_sync(case, monkeypatch):
    runner, adapter, rollback = _prepared(case)
    with UpgradeMaintenance(adapter.service._gate, runner.lease, adapter.context):
        source = adapter.verify_source(); backup = adapter.verify_backup(source)
        expected = [adapter.workspace.stat().st_ino, adapter.workspace.parent.stat().st_ino,
            adapter.root.stat().st_ino]
        calls = []; original = os.fsync
        def observe(descriptor):
            calls.append(os.fstat(descriptor).st_ino)
            original(descriptor)
        monkeypatch.setattr(os, "fsync", observe)
        receipt = rollback.create(source, backup)
        assert receipt.role == "rollback"
        assert calls[-3:] == expected
