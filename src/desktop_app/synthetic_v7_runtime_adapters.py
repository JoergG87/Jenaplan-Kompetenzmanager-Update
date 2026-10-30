"""Sealed internal-test V7 restore processes; no product startup authority."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from src.core.restore_runtime import RestoreTransactionPaths, RuntimeInstanceLock
from src.desktop_app.restore_worker import (
    RESTORE_MODE_SYNTHETIC_V7_ENCRYPTED,
    RestoreWorkerProcess,
    launch_restore_worker,
)


class DesktopSyntheticV7RestoreWorkerLauncher:
    """Launch the exact same sealed app with the isolated V7 worker mode."""

    def launch(self, *, handoff: Path, nonce: str,
               lock: RuntimeInstanceLock) -> RestoreWorkerProcess:
        from src.security.internal_test_v7_composition import require_internal_test_v7_context

        require_internal_test_v7_context(lock.runtime_root)
        return launch_restore_worker(handoff=handoff, nonce=nonce, lock=lock,
            restore_mode=RESTORE_MODE_SYNTHETIC_V7_ENCRYPTED)


class DesktopSyntheticV7RestartLauncher:
    """Resume the V7 handshake through normal authentication and app lifecycle."""

    def launch(self, *, paths: RestoreTransactionPaths, token: str,
               lock: RuntimeInstanceLock) -> subprocess.Popen[bytes] | None:
        from src.security.internal_test_v7_composition import require_internal_test_v7_context

        require_internal_test_v7_context(paths.runtime_root)
        # The authority above is frozen-only. No source execution or alternative
        # interpreter can inherit this sealed package's V7 admission.
        executable = Path(sys.executable).resolve(strict=True)
        command = [str(executable), "--synthetic-v7-restore-confirm",
            "--runtime-root", str(paths.runtime_root),
            "--restore-id", paths.transaction.name, "--restore-token", token,
            "--restore-lock-fd", str(lock.fileno)]
        environment = dict(os.environ)
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            return subprocess.Popen(command, pass_fds=(lock.fileno,), close_fds=True,
                cwd=paths.runtime_root, start_new_session=os.name == "posix",
                env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            return None


def build_internal_test_v7_restore_worker_service(root: Path, *, lock: RuntimeInstanceLock):
    """Compose existing-only keys before takeover, open main only after EOF."""
    from src.security.internal_test_v7_composition import (
        build_internal_test_v7_backup_service, require_internal_test_v7_context,
        InternalTestStartupGuard,
    )
    from src.security.synthetic_v7_live_restore import SyntheticV7EncryptedLiveRestoreService

    require_internal_test_v7_context(root)
    if lock.runtime_root != Path(root):
        from src.core.restore_runtime import RestorePreflightError
        raise RestorePreflightError("Der synthetische V7-Workerroot widerspricht der Sperre.")
    InternalTestStartupGuard(lock).evaluate()
    service = build_internal_test_v7_backup_service(root)
    return SyntheticV7EncryptedLiveRestoreService(service,
        restart_launcher=DesktopSyntheticV7RestartLauncher())


def recover_internal_test_v7_restore(root: Path, *, on_verified_rollback=None):
    """Use only authenticated V7 evidence, never a V4 or ZIP fallback."""
    from src.security.internal_test_v7_composition import require_internal_test_v7_context
    from src.security.synthetic_v7_live_restore import recover_interrupted_synthetic_v7_restore

    require_internal_test_v7_context(root)
    service = build_internal_test_v7_restore_verifier(root)
    result = recover_interrupted_synthetic_v7_restore(backup_service=service, runtime_root=root)
    # _rollback has authenticated the handoff and independently verified the
    # safety backup, complete keyed live runtime, documents and excluded files.
    # Preserve that exact context across normal authentication reads, which may
    # legitimately reopen checkpointed WAL-mode metadata. Never retry a failed
    # Existing-only load or grant this path to an unresolved/ordinary startup.
    if result.status == "rolled_back" and on_verified_rollback is not None:
        on_verified_rollback(service)
    return result


def confirm_internal_test_v7_restore(root: Path, restore_id: str, token: str):
    """Confirm only after authenticated handoff and complete keyed V7 reopen."""
    from src.security.internal_test_v7_composition import (
        build_internal_test_v7_backup_service, require_internal_test_v7_context,
    )
    from src.security.synthetic_v7_live_restore import confirm_synthetic_v7_restore_startup

    require_internal_test_v7_context(root)
    service = build_internal_test_v7_backup_service(root)
    return confirm_synthetic_v7_restore_startup(backup_service=service,
        runtime_root=root, restore_id=restore_id, token=token)


def build_internal_test_v7_restore_verifier(root: Path):
    """Rebind retained metadata only through the existing authenticated bootstrap.

    The ordinary existing-key loader remains the first choice. During an
    interrupted rename, missing live metadata never triggers key generation:
    the old V4 recovery algorithm independently authenticates an exact retained
    metadata candidate against the V7 handoff before a verifier is composed.
    """
    from src.security.internal_test_v7_composition import (
        build_internal_test_v7_backup_service, require_internal_test_v7_context,
    )
    from src.security.synthetic_v7_live_restore import (
        SYNTHETIC_V7_LIVE_RESTORE_KIND, SyntheticV7EncryptedRestoreHandoffService,
    )

    return _build_v7_restore_verifier(root,
        require_context=require_internal_test_v7_context,
        service_builder=build_internal_test_v7_backup_service,
        restore_kind=SYNTHETIC_V7_LIVE_RESTORE_KIND,
        handoff_type=SyntheticV7EncryptedRestoreHandoffService)


def _build_v7_restore_verifier(root, *, require_context, service_builder,
        restore_kind, handoff_type):
    from src.core.restore_runtime import RestoreJournal, RestoreManualRecoveryRequired, restore_transaction_paths
    from src.security.final_v4_live_restore import _bootstrap_handoff_context
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository
    require_context(root)
    try:
        return service_builder(root)
    except Exception:
        # The fallback can only authenticate existing metadata; it cannot
        # create, rotate, restore, or normalize any key or directory.
        transaction_root = root / "restore-transactions"
        candidates = []
        if transaction_root.is_dir() and not transaction_root.is_symlink():
            for child in transaction_root.iterdir():
                if child.is_symlink() or not child.is_dir():
                    raise RestoreManualRecoveryRequired("Der synthetische Restorebereich ist ungueltig.")
                paths = restore_transaction_paths(root, child.name)
                state = RestoreJournal(paths).read()
                if state.get("phase") not in {"completed", "rolled_back", "aborted_before_replacement"}:
                    if state.get("restore_kind") != restore_kind:
                        raise RestoreManualRecoveryRequired("Ein fremder Restorevertrag blockiert V7-Recovery.")
                    candidates.append((paths, state))
        if len(candidates) != 1:
            raise RestoreManualRecoveryRequired("Der synthetische V7-Recoverykontext ist nicht eindeutig.") from None
        account = ExistingStartupAccountRepository(root / "security/security.sqlite", None).load_bound_active_account()
        paths, state = candidates[0]
        _handoff, loaded = _bootstrap_handoff_context(paths, state,
            account_loader=lambda: account, restore_kind=restore_kind,
            handoff_service_type=handoff_type)
        return service_builder(root,
            authenticated_account=account, loaded_keys=loaded)
