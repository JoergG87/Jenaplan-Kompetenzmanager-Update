from __future__ import annotations

import os
from pathlib import Path
from contextlib import closing
import hashlib
import signal
import subprocess
import sys
import textwrap

import pytest

from src.security.database_keys import DerivedDomainKey, MIGRATION_JOURNAL_AUTH_PURPOSE
from src.security.database_keys import derive_migration_journal_auth_key
from src.security.data_keys import LoadedDataMasterKey
from src.security.infrastructure.migration_journal_repository import (
    AuthenticatedMigrationJournalRepository,
)
from src.security.infrastructure.system import PlatformFilePermissionManager
from src.security.migration_journal import MigrationPhase
from src.security.migration_journal import MigrationRecoveryEvaluator, RecoveryDecision
from prototypes.database_encryption_migration.migration import (
    _open_plaintext_read_only,
    _require_guarded_synthetic_source,
    _snapshot,
    _verify_plaintext_integrity,
)


@pytest.mark.skipif(os.name != "posix", reason="POSIX signal semantics required")
@pytest.mark.parametrize(
    "phase,abort_point,signal_name,expected_phase",
    [
        (MigrationPhase.BACKUP_STARTED, "before_recover", "SIGTERM", MigrationPhase.BACKUP_STARTED),
        (MigrationPhase.BACKUP_CREATED, "backup_callback", "SIGKILL", MigrationPhase.BACKUP_CREATED),
        (MigrationPhase.TARGET_CREATED, "before_target_quarantine", "SIGTERM", MigrationPhase.ROLLBACK_STARTED),
        (MigrationPhase.EXPORT_STARTED, "before_target_quarantine", "SIGKILL", MigrationPhase.ROLLBACK_STARTED),
        (MigrationPhase.VALIDATION_STARTED, "validation_callback", "SIGTERM", MigrationPhase.VALIDATION_STARTED),
        (MigrationPhase.BACKUP_CREATED, "after_anchor_prepare", "SIGKILL", MigrationPhase.BACKUP_CREATED),
        (MigrationPhase.BACKUP_CREATED, "after_journal_publish", "SIGTERM", MigrationPhase.BACKUP_VERIFIED),
        (MigrationPhase.BACKUP_CREATED, "before_journal_os_replace", "SIGKILL", MigrationPhase.BACKUP_CREATED),
        (MigrationPhase.BACKUP_CREATED, "after_journal_os_replace", "SIGTERM", MigrationPhase.BACKUP_VERIFIED),
    ],
)
def test_real_process_abort_during_recovery_preserves_authenticated_state(
    tmp_path: Path,
    phase: MigrationPhase,
    abort_point: str,
    signal_name: str,
    expected_phase: MigrationPhase,
) -> None:
    root = tmp_path / f"{phase.value}-{abort_point}"
    script = textwrap.dedent(
        """
        import os, signal, sys
        from pathlib import Path
        sys.path.insert(0, str(Path.cwd() / "tests"))
        from test_security_migration_recovery import _fixture
        from src.security.migration_journal import MigrationPhase

        root = Path(sys.argv[1])
        root.mkdir(mode=0o700)
        phase = MigrationPhase(sys.argv[2])
        abort_point = sys.argv[3]
        signal_value = getattr(signal, sys.argv[4])
        def abort(_unused=None):
            os.kill(os.getpid(), signal_value)
        def fault(point):
            if point == abort_point:
                abort()
        options = {"fault_injector": fault}
        if abort_point == "backup_callback":
            options["backup_verifier"] = abort
        if abort_point == "validation_callback":
            options["target_validator"] = abort
        paths, repository, key, anchor, lock, orchestrator, calls = _fixture(
            root, phase, **options
        )
        if abort_point in {"before_journal_os_replace", "after_journal_os_replace"}:
            import src.security.infrastructure.migration_journal_repository as journal_module
            original_replace = journal_module.os.replace
            def replace_and_abort(source, destination):
                if Path(destination).name != "database-migration-journal-v1.json":
                    return original_replace(source, destination)
                if abort_point == "before_journal_os_replace":
                    abort()
                result = original_replace(source, destination)
                abort()
                return result
            journal_module.os.replace = replace_and_abort
        if abort_point == "before_recover":
            abort()
        orchestrator.recover()
        """
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(root),
            phase.value,
            abort_point,
            signal_name,
        ],
        cwd=Path(__file__).parent.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    expected_signal = getattr(signal, signal_name)
    assert completed.returncode == -expected_signal
    workspaces = list(root.glob("root-*"))
    assert len(workspaces) == 1
    workspace = workspaces[0]
    source = workspace / "synthetic-source.sqlite"
    backup = workspace / "run-1-verified-backup.sqlite"
    if backup.exists():
        with closing(_open_plaintext_read_only(source)) as source_connection:
            _require_guarded_synthetic_source(source_connection)
            _verify_plaintext_integrity(source_connection)
            source_snapshot = _snapshot(source_connection)
        with closing(_open_plaintext_read_only(backup)) as backup_connection:
            _require_guarded_synthetic_source(backup_connection)
            _verify_plaintext_integrity(backup_connection)
            assert _snapshot(backup_connection) == source_snapshot
    repository = AuthenticatedMigrationJournalRepository(
        workspace / "database-migration-journal-v1.json",
        PlatformFilePermissionManager(),
    )
    key = DerivedDomainKey(MIGRATION_JOURNAL_AUTH_PURPOSE, 1, b"j" * 32)
    unexpected_temps = list(workspace.glob(".database-migration-journal-*"))
    if abort_point == "before_journal_os_replace":
        assert unexpected_temps
        state = repository._decode(repository.path.read_bytes(), key)
        assert MigrationRecoveryEvaluator().decide(
            state, workspace=workspace
        ) is not RecoveryDecision.BLOCK_MANUAL_REVIEW
    else:
        state = repository.load(key)
    assert state.phase is expected_phase
    decision = MigrationRecoveryEvaluator().decide(state, workspace=workspace)
    assert isinstance(decision, RecoveryDecision)
    assert "j" * 32 not in completed.stdout
    assert "j" * 32 not in completed.stderr


@pytest.mark.skipif(os.name != "posix", reason="POSIX flock semantics required")
def test_second_process_cannot_enter_recovery_while_owner_holds_lock(
    tmp_path: Path,
) -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from test_security_migration_recovery import _fixture

    paths, _repository, _key, _anchor, lock, _orchestrator, _calls = _fixture(
        tmp_path, MigrationPhase.BACKUP_CREATED
    )
    script = textwrap.dedent(
        """
        import sys
        from pathlib import Path
        from src.security.migration_lock import ExclusiveMigrationLock, MigrationLockError
        try:
            ExclusiveMigrationLock(
                Path(sys.argv[1]),
                installation_id="11111111-1111-4111-8111-111111111111",
                database_context_id="22222222-2222-4222-8222-222222222222",
                migration_id="33333333-3333-4333-8333-333333333333",
                allowed_root=Path(sys.argv[1]),
            ).acquire()
        except MigrationLockError:
            raise SystemExit(0)
        raise SystemExit(1)
        """
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", script, str(paths.root)],
            cwd=Path(__file__).parent.parent,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0
    finally:
        lock.release()


@pytest.mark.skipif(os.name != "posix", reason="POSIX signal semantics required")
@pytest.mark.parametrize(
    "event,signal_name,expected_phase",
    [
        ("backup_started", "SIGTERM", MigrationPhase.BACKUP_STARTED),
        ("backup_created", "SIGKILL", MigrationPhase.BACKUP_CREATED),
        (
            "target_creation_started",
            "SIGTERM",
            MigrationPhase.TARGET_CREATION_STARTED,
        ),
        ("export_in_progress", "SIGKILL", MigrationPhase.EXPORT_STARTED),
        ("validation_in_progress", "SIGTERM", MigrationPhase.VALIDATION_STARTED),
    ],
)
def test_real_migration_process_abort_persists_stable_recovery_decision(
    tmp_path: Path,
    event: str,
    signal_name: str,
    expected_phase: MigrationPhase,
) -> None:
    root = tmp_path / event
    root.mkdir(mode=0o700)
    script = textwrap.dedent(
        """
        import os, signal, sys
        from pathlib import Path
        from prototypes.database_encryption_migration import MigrationPaths
        from prototypes.database_encryption_migration.migration import MigrationPrototypeEngine
        from prototypes.database_encryption_migration.secure_migration import SecureMigrationPrototypeEngine
        from prototypes.database_encryption_migration.synthetic_data import SyntheticScale, create_synthetic_source
        from src.security.data_keys import LoadedDataMasterKey

        class KillingMigrationEngine(MigrationPrototypeEngine):
            def migrate(self, paths, *, key_material, failure_point=None, phase_observer=None):
                def observer(event, observed_paths):
                    phase_observer(event, observed_paths)
                    if event == sys.argv[2]:
                        os.kill(os.getpid(), getattr(signal, sys.argv[3]))
                return super().migrate(
                    paths,
                    key_material=key_material,
                    failure_point=failure_point,
                    phase_observer=observer,
                )

        root = Path(sys.argv[1])
        paths = MigrationPaths.in_workspace(root)
        create_synthetic_source(paths.source, SyntheticScale(1, 1, 5, 1, 1, 1, 1))
        dmk = LoadedDataMasterKey(
            "77777777-7777-4777-8777-777777777777", 1, b"public-test-dmk-material-32byte!"
        )
        SecureMigrationPrototypeEngine(
            migration_engine=KillingMigrationEngine()
        ).run(paths, dmk=dmk)
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), event, signal_name],
        cwd=Path(__file__).parent.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == -getattr(signal, signal_name)
    source = root / "synthetic-source.sqlite"
    backup = root / "run-1-verified-backup.sqlite"
    if backup.exists():
        with closing(_open_plaintext_read_only(source)) as source_connection:
            _require_guarded_synthetic_source(source_connection)
            _verify_plaintext_integrity(source_connection)
            source_snapshot = _snapshot(source_connection)
        with closing(_open_plaintext_read_only(backup)) as backup_connection:
            _require_guarded_synthetic_source(backup_connection)
            _verify_plaintext_integrity(backup_connection)
            assert _snapshot(backup_connection) == source_snapshot
    journal_path = root / "database-migration-journal-v1.json"
    import json

    migration_id = json.loads(journal_path.read_bytes())["migration_id"]
    dmk = LoadedDataMasterKey(
        "77777777-7777-4777-8777-777777777777",
        1,
        b"public-test-dmk-material-32byte!",
    )
    repository = AuthenticatedMigrationJournalRepository(
        journal_path, PlatformFilePermissionManager()
    )
    key = derive_migration_journal_auth_key(dmk, migration_id=migration_id)
    state = repository.load(key)
    assert state.phase is expected_phase
    assert hashlib.sha256(source.read_bytes()).hexdigest() == state.file_evidence["source"].sha256
    first = MigrationRecoveryEvaluator().decide(state, workspace=root)
    second = MigrationRecoveryEvaluator().decide(state, workspace=root)
    assert first is second
    assert first is not RecoveryDecision.BLOCK_MANUAL_REVIEW
    assert "public-test-dmk" not in completed.stdout
    assert "public-test-dmk" not in completed.stderr
