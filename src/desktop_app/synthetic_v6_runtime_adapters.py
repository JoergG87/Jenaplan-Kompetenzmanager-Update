"""Sealed internal-test V6 restore processes; no product startup authority."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from src.core.restore_runtime import RestoreTransactionPaths, RuntimeInstanceLock
from src.desktop_app.restore_worker import (
    RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED,
    RestoreWorkerProcess,
    launch_restore_worker,
)


class DesktopSyntheticV6RestoreWorkerLauncher:
    """Launch the exact same sealed app with the isolated V6 worker mode."""

    def launch(self, *, handoff: Path, nonce: str,
               lock: RuntimeInstanceLock) -> RestoreWorkerProcess:
        from src.security.internal_test_v6_composition import require_internal_test_v6_context

        require_internal_test_v6_context(lock.runtime_root)
        return launch_restore_worker(handoff=handoff, nonce=nonce, lock=lock,
            restore_mode=RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED)


class DesktopSyntheticV6RestartLauncher:
    """Resume the V6 handshake through normal authentication and app lifecycle."""

    def launch(self, *, paths: RestoreTransactionPaths, token: str,
               lock: RuntimeInstanceLock) -> subprocess.Popen[bytes] | None:
        from src.security.internal_test_v6_composition import require_internal_test_v6_context

        require_internal_test_v6_context(paths.runtime_root)
        # The authority above is frozen-only. No source execution or alternative
        # interpreter can inherit this sealed package's V6 admission.
        executable = Path(sys.executable).resolve(strict=True)
        command = [str(executable), "--synthetic-v6-restore-confirm",
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


def build_internal_test_v6_restore_worker_service(root: Path, *, lock: RuntimeInstanceLock):
    """Compose existing-only keys before takeover, open main only after EOF."""
    from src.security.internal_test_v6_composition import (
        build_internal_test_v6_backup_service, require_internal_test_v6_context,
        InternalTestStartupGuard,
    )
    from src.security.synthetic_v6_live_restore import SyntheticV6EncryptedLiveRestoreService

    require_internal_test_v6_context(root)
    if lock.runtime_root != Path(root):
        from src.core.restore_runtime import RestorePreflightError
        raise RestorePreflightError("Der synthetische V6-Workerroot widerspricht der Sperre.")
    InternalTestStartupGuard(lock).evaluate()
    service = build_internal_test_v6_backup_service(root)
    return SyntheticV6EncryptedLiveRestoreService(service,
        restart_launcher=DesktopSyntheticV6RestartLauncher())


def recover_internal_test_v6_restore(root: Path):
    """Use only authenticated V6 evidence, never a V4 or ZIP fallback."""
    from src.security.internal_test_v6_composition import require_internal_test_v6_context
    from src.security.synthetic_v6_live_restore import recover_interrupted_synthetic_v6_restore

    require_internal_test_v6_context(root)
    service = build_internal_test_v6_restore_verifier(root)
    return recover_interrupted_synthetic_v6_restore(backup_service=service, runtime_root=root)


def confirm_internal_test_v6_restore(root: Path, restore_id: str, token: str):
    """Confirm only after authenticated handoff and complete keyed V6 reopen."""
    from src.security.internal_test_v6_composition import (
        build_internal_test_v6_backup_service, require_internal_test_v6_context,
    )
    from src.security.synthetic_v6_live_restore import confirm_synthetic_v6_restore_startup

    require_internal_test_v6_context(root)
    service = build_internal_test_v6_backup_service(root)
    return confirm_synthetic_v6_restore_startup(backup_service=service,
        runtime_root=root, restore_id=restore_id, token=token)


def build_internal_test_v6_restore_verifier(root: Path):
    """Rebind retained metadata only through the existing authenticated bootstrap.

    The ordinary existing-key loader remains the first choice. During an
    interrupted rename, missing live metadata never triggers key generation:
    the old V4 recovery algorithm independently authenticates an exact retained
    metadata candidate against the V6 handoff before a verifier is composed.
    """
    from src.core.restore_runtime import RestoreJournal, RestoreManualRecoveryRequired, restore_transaction_paths
    from src.security.internal_test_v6_composition import (
        build_internal_test_v6_backup_service, require_internal_test_v6_context,
    )
    from src.security.final_v4_live_restore import _bootstrap_handoff_context
    from src.security.synthetic_v6_live_restore import (
        SYNTHETIC_V6_LIVE_RESTORE_KIND, SyntheticV6EncryptedRestoreHandoffService,
    )
    from src.security.infrastructure.sqlite_repository import ExistingStartupAccountRepository

    require_internal_test_v6_context(root)
    try:
        return build_internal_test_v6_backup_service(root)
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
                    if state.get("restore_kind") != SYNTHETIC_V6_LIVE_RESTORE_KIND:
                        raise RestoreManualRecoveryRequired("Ein fremder Restorevertrag blockiert V6-Recovery.")
                    candidates.append((paths, state))
        if len(candidates) != 1:
            raise RestoreManualRecoveryRequired("Der synthetische V6-Recoverykontext ist nicht eindeutig.") from None
        account = ExistingStartupAccountRepository(root / "security/security.sqlite", None).load_bound_active_account()
        paths, state = candidates[0]
        _handoff, loaded = _bootstrap_handoff_context(paths, state,
            account_loader=lambda: account, restore_kind=SYNTHETIC_V6_LIVE_RESTORE_KIND,
            handoff_service_type=SyntheticV6EncryptedRestoreHandoffService)
        return build_internal_test_v6_backup_service(root,
            authenticated_account=account, loaded_keys=loaded)
