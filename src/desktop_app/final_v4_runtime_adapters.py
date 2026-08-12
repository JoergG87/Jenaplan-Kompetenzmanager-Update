"""Desktop process adapters for the Qt-free Final-V4 security runtime."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from src.core.restore_runtime import RestoreTransactionPaths, RuntimeInstanceLock
from src.desktop_app.restore_worker import (
    RESTORE_MODE_FINAL_V4_ENCRYPTED,
    RestoreWorkerProcess,
    launch_restore_worker,
)


class DesktopFinalV4RestoreWorkerLauncher:
    """Start and confirm the existing desktop restore worker."""

    def launch(
        self,
        *,
        handoff: Path,
        nonce: str,
        lock: RuntimeInstanceLock,
    ) -> RestoreWorkerProcess:
        return launch_restore_worker(
            handoff=handoff,
            nonce=nonce,
            lock=lock,
            restore_mode=RESTORE_MODE_FINAL_V4_ENCRYPTED,
        )


class DesktopFinalV4RestartLauncher:
    """Start the source or frozen app for the restore resume handshake."""

    def launch(
        self,
        *,
        paths: RestoreTransactionPaths,
        token: str,
        lock: RuntimeInstanceLock,
    ) -> subprocess.Popen[bytes] | None:
        try:
            executable = Path(sys.executable).expanduser().resolve(strict=True)
        except OSError:
            return None
        arguments = [
            "--final-v4-restore-confirm",
            "--runtime-root",
            str(paths.runtime_root),
            "--restore-id",
            paths.transaction.name,
            "--restore-token",
            token,
            "--restore-lock-fd",
            str(lock.fileno),
        ]
        environment = dict(os.environ)
        if getattr(sys, "frozen", False):
            command = [str(executable), *arguments]
            environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
            working_directory = paths.runtime_root
        else:
            command = [
                str(executable),
                "-m",
                "src.desktop_app.main",
                *arguments,
            ]
            working_directory = Path(__file__).resolve().parents[2]
        try:
            return subprocess.Popen(
                command,
                pass_fds=(lock.fileno,),
                close_fds=True,
                cwd=working_directory,
                start_new_session=os.name == "posix",
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            return None
