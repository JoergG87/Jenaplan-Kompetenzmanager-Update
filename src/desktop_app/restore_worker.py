"""Qt-free productive restore worker for source and frozen executions."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from src.core.restore_runtime import (
    ProductiveRestoreService,
    RestoreHandoffError,
    RestoreLockError,
    RestoreManualRecoveryRequired,
    RestorePreflightError,
    RestoreReplacementError,
    RestoreRuntimeError,
    RuntimeInstanceLock,
)


EXIT_SUCCESS = 0
EXIT_USAGE = 10
EXIT_LOCKED = 20
EXIT_HANDOFF_INVALID = 21
EXIT_PREFLIGHT_FAILED = 30
EXIT_REPLACEMENT_ROLLED_BACK = 40
EXIT_MANUAL_RECOVERY_REQUIRED = 41
EXIT_UNEXPECTED = 50


def launch_restore_worker(
    *,
    handoff: Path,
    nonce: str,
    lock: RuntimeInstanceLock,
) -> subprocess.Popen[bytes]:
    """Transfer the already-held kernel lock to a dedicated restore worker."""
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--restore-worker"]
    else:
        command = [sys.executable, "-m", "src.desktop_app.restore_worker"]
    command.extend(
        [
            "--handoff",
            str(handoff),
            "--nonce",
            nonce,
            "--lock-fd",
            str(lock.fileno),
        ]
    )
    process = subprocess.Popen(
        command,
        pass_fds=(lock.fileno,),
        close_fds=True,
    )
    lock.transfer()
    return process


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jenaplan Restore-Worker")
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--lock-fd", type=int)
    return parser


def run(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as error:
        return EXIT_SUCCESS if error.code == 0 else EXIT_USAGE
    try:
        handoff = args.handoff.expanduser().resolve(strict=True)
        if handoff.parent.name != "restore-handoffs" or handoff.suffix != ".json":
            return EXIT_HANDOFF_INVALID
        runtime_root = handoff.parent.parent
    except OSError:
        return EXIT_HANDOFF_INVALID
    try:
        lock = RuntimeInstanceLock(runtime_root, inherited_fd=args.lock_fd)
        lock.acquire()
        try:
            ProductiveRestoreService().execute(
                handoff_path=args.handoff,
                nonce=args.nonce,
                lock=lock,
            )
            lock.transfer()
        except Exception:
            lock.release()
            raise
        return EXIT_SUCCESS
    except RestoreLockError:
        return EXIT_LOCKED
    except RestoreHandoffError:
        return EXIT_HANDOFF_INVALID
    except RestorePreflightError:
        return EXIT_PREFLIGHT_FAILED
    except RestoreManualRecoveryRequired:
        return EXIT_MANUAL_RECOVERY_REQUIRED
    except RestoreReplacementError:
        return EXIT_REPLACEMENT_ROLLED_BACK
    except RestoreRuntimeError:
        return EXIT_UNEXPECTED
    except Exception:
        return EXIT_UNEXPECTED


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
