"""Qt-free productive restore worker for source and frozen executions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import select
import subprocess
import sys
from typing import Callable

from src.core.restore_runtime import (
    ProductiveRestoreService,
    RestoreHandoffError,
    RestoreJournal,
    RestoreLockError,
    RestoreManualRecoveryRequired,
    RestorePreflightError,
    RestoreReplacementError,
    RestoreRuntimeError,
    RuntimeInstanceLock,
    recover_interrupted_restore,
    restore_transaction_paths,
)


LOGGER = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_USAGE = 10
EXIT_LOCKED = 20
EXIT_HANDOFF_INVALID = 21
EXIT_PREFLIGHT_FAILED = 30
EXIT_REPLACEMENT_ROLLED_BACK = 40
EXIT_MANUAL_RECOVERY_REQUIRED = 41
EXIT_UNEXPECTED = 50

WORKER_READY_MESSAGE = b"worker_started\n"
WORKER_READY_TIMEOUT_SECONDS = 5.0
WORKER_TERMINATE_TIMEOUT_SECONDS = 2.0
RESTORE_MODE_ZIP_V1 = "zip_v1"
RESTORE_MODE_FINAL_V4_ENCRYPTED = "final_v4_encrypted"


class RestoreWorkerLaunchError(RuntimeError):
    """Raised while the main app still owns a recoverable restore start."""


@dataclass(frozen=True)
class RestoreWorkerLaunchPlan:
    """One shell-free executable prefix and deterministic working directory."""

    command_prefix: tuple[str, ...]
    working_directory: Path

    def command(
        self,
        *,
        handoff: Path,
        nonce: str,
        lock_fd: int,
        ready_fd: int,
        parent_lifetime_fd: int,
        restore_mode: str = RESTORE_MODE_ZIP_V1,
    ) -> list[str]:
        command = [
            *self.command_prefix,
            "--handoff",
            str(handoff),
            "--nonce",
            nonce,
            "--lock-fd",
            str(lock_fd),
            "--ready-fd",
            str(ready_fd),
            "--parent-lifetime-fd",
            str(parent_lifetime_fd),
        ]
        if restore_mode != RESTORE_MODE_ZIP_V1:
            command.extend(["--restore-mode", restore_mode])
        return command


@dataclass(frozen=True)
class RestoreWorkerProcess:
    """A confirmed worker plus the descriptor held until main-process exit."""

    process: subprocess.Popen[bytes]
    parent_lifetime_fd: int


class _WorkerTakeoverChannel:
    def __init__(self, ready_fd: int, parent_lifetime_fd: int) -> None:
        self.ready_fd: int | None = ready_fd
        self.parent_lifetime_fd: int | None = parent_lifetime_fd

    def confirm_and_wait_for_parent_exit(self, _paths: object) -> None:
        ready_fd = self.ready_fd
        if ready_fd is None:
            raise RestorePreflightError("Der Worker-Ready-Kanal ist nicht verfuegbar.")
        try:
            _write_all(ready_fd, WORKER_READY_MESSAGE)
        finally:
            _close_fd(ready_fd)
            self.ready_fd = None

        parent_lifetime_fd = self.parent_lifetime_fd
        if parent_lifetime_fd is None:
            raise RestorePreflightError(
                "Der Parent-Lebensdauerkanal ist nicht verfuegbar."
            )
        try:
            if os.read(parent_lifetime_fd, 1):
                raise RestorePreflightError(
                    "Der Parent-Lebensdauerkanal enthielt unerwartete Daten."
                )
        finally:
            _close_fd(parent_lifetime_fd)
            self.parent_lifetime_fd = None

    def close(self) -> None:
        for attribute in ("ready_fd", "parent_lifetime_fd"):
            descriptor = getattr(self, attribute)
            if descriptor is not None:
                _close_fd(descriptor)
                setattr(self, attribute, None)


def resolve_restore_worker_launch(
    runtime_root: Path,
    *,
    executable: Path | None = None,
    frozen: bool | None = None,
) -> RestoreWorkerLaunchPlan:
    """Resolve a source or bundle worker without a shell or relative bundle path."""
    try:
        root = Path(runtime_root).expanduser().resolve(strict=True)
        candidate = Path(executable or sys.executable).expanduser().resolve(
            strict=True
        )
    except OSError as error:
        raise RestoreWorkerLaunchError(
            "Der Restore-Worker ist nicht sicher aufloesbar."
        ) from error
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise RestoreWorkerLaunchError(
            "Der Restore-Worker ist nicht sicher ausfuehrbar."
        )

    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        command_prefix = (str(candidate), "--restore-worker")
        working_directory = root
    else:
        command_prefix = (
            str(candidate),
            "-m",
            "src.desktop_app.restore_worker",
        )
        working_directory = Path(__file__).resolve().parents[2]
    if not working_directory.is_dir():
        raise RestoreWorkerLaunchError(
            "Das Restore-Worker-Arbeitsverzeichnis ist nicht verfuegbar."
        )
    return RestoreWorkerLaunchPlan(command_prefix, working_directory)


def launch_restore_worker(
    *,
    handoff: Path,
    nonce: str,
    lock: RuntimeInstanceLock,
    launch_plan: RestoreWorkerLaunchPlan | None = None,
    ready_timeout_seconds: float = WORKER_READY_TIMEOUT_SECONDS,
    restore_mode: str = RESTORE_MODE_ZIP_V1,
) -> RestoreWorkerProcess:
    """Start, authenticate and confirm a worker before transferring the lock."""
    if ready_timeout_seconds <= 0:
        raise ValueError("ready_timeout_seconds must be positive")

    try:
        plan = launch_plan or resolve_restore_worker_launch(lock.runtime_root)
        handoff_path = Path(handoff).expanduser().resolve(strict=True)
    except (OSError, RestoreWorkerLaunchError) as error:
        LOGGER.error(
            "Restore worker launch resolution failed: error_class=%s",
            type(error).__name__,
        )
        _abort_unconfirmed_restore(lock, None, restore_mode)
        if isinstance(error, RestoreWorkerLaunchError):
            raise
        raise RestoreWorkerLaunchError(
            "Der Restore-Handoff ist nicht sicher aufloesbar."
        ) from error

    ready_read_fd, ready_write_fd = os.pipe()
    lifetime_read_fd, lifetime_write_fd = os.pipe()
    process: subprocess.Popen[bytes] | None = None
    try:
        command = plan.command(
            handoff=handoff_path,
            nonce=nonce,
            lock_fd=lock.fileno,
            ready_fd=ready_write_fd,
            parent_lifetime_fd=lifetime_read_fd,
            restore_mode=restore_mode,
        )
        process = subprocess.Popen(
            command,
            pass_fds=(lock.fileno, ready_write_fd, lifetime_read_fd),
            close_fds=True,
            cwd=plan.working_directory,
            start_new_session=os.name == "posix",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as error:
        LOGGER.error(
            "Restore worker process start failed: error_class=%s",
            type(error).__name__,
        )
        _close_fd(ready_read_fd)
        _close_fd(lifetime_write_fd)
        _abort_unconfirmed_restore(lock, handoff_path.stem, restore_mode)
        raise RestoreWorkerLaunchError(
            "Der Restore-Worker-Prozess konnte nicht gestartet werden."
        ) from error
    finally:
        _close_fd(ready_write_fd)
        _close_fd(lifetime_read_fd)

    try:
        ready, _, _ = select.select(
            [ready_read_fd],
            [],
            [],
            ready_timeout_seconds,
        )
        message = os.read(ready_read_fd, 256) if ready else b""
        paths = restore_transaction_paths(lock.runtime_root, handoff_path.stem)
        state = RestoreJournal(paths).read()
        takeover_confirmed = (
            message == WORKER_READY_MESSAGE
            and state.get("phase") == "worker_started"
            and process.poll() is None
        )
        if not takeover_confirmed:
            _terminate_and_reap(process)
            LOGGER.error(
                "Restore worker takeover failed: exit_code=%s journal_phase=%s",
                process.returncode,
                state.get("phase"),
            )
            _close_fd(lifetime_write_fd)
            _abort_unconfirmed_restore(lock, handoff_path.stem, restore_mode)
            raise RestoreWorkerLaunchError(
                "Der Restore-Worker hat die Uebernahme nicht bestaetigt."
            )
        lock.transfer()
        LOGGER.info("Restore worker takeover confirmed: pid=%s", process.pid)
        return RestoreWorkerProcess(process, lifetime_write_fd)
    except RestoreWorkerLaunchError:
        raise
    except Exception as error:
        _terminate_and_reap(process)
        _close_fd(lifetime_write_fd)
        _abort_unconfirmed_restore(lock, handoff_path.stem, restore_mode)
        LOGGER.error(
            "Restore worker takeover check failed: error_class=%s",
            type(error).__name__,
        )
        raise RestoreWorkerLaunchError(
            "Die Restore-Worker-Uebernahme konnte nicht bestaetigt werden."
        ) from error
    finally:
        _close_fd(ready_read_fd)


def _abort_unconfirmed_restore(
    lock: RuntimeInstanceLock,
    restore_id: str | None,
    restore_mode: str,
) -> None:
    if restore_mode == RESTORE_MODE_FINAL_V4_ENCRYPTED:
        if restore_id is None:
            return
        try:
            paths = restore_transaction_paths(lock.runtime_root, restore_id)
            journal = RestoreJournal(paths)
            state = journal.read()
            if (
                state.get("phase") in {"handoff_created", "worker_started"}
                and not state.get("completed_renames")
            ):
                journal.transition(
                    "aborted_before_replacement",
                    next_step="none",
                )
        except RestoreRuntimeError as error:
            LOGGER.error(
                "Cipher restore worker start recovery failed: error_class=%s",
                type(error).__name__,
            )
        return
    try:
        result = recover_interrupted_restore(lock.runtime_root)
    except RestoreRuntimeError as error:
        LOGGER.error(
            "Restore worker start recovery failed: error_class=%s",
            type(error).__name__,
        )
        return
    LOGGER.warning(
        "Restore worker start aborted before replacement: status=%s",
        result.status,
    )


def _terminate_and_reap(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        process.wait()
        return
    try:
        process.terminate()
    except ProcessLookupError:
        process.wait()
        return
    try:
        process.wait(timeout=WORKER_TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=WORKER_TERMINATE_TIMEOUT_SECONDS)


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("worker ready pipe write failed")
        view = view[written:]


def _close_fd(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jenaplan Restore-Worker")
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--lock-fd", type=int)
    parser.add_argument("--ready-fd", type=int)
    parser.add_argument("--parent-lifetime-fd", type=int)
    parser.add_argument(
        "--restore-mode",
        choices=(RESTORE_MODE_ZIP_V1, RESTORE_MODE_FINAL_V4_ENCRYPTED),
        default=RESTORE_MODE_ZIP_V1,
    )
    return parser


def run(
    argv: list[str] | None = None,
    *,
    encrypted_service_factory: Callable[[Path], ProductiveRestoreService]
    | None = None,
) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as error:
        return EXIT_SUCCESS if error.code == 0 else EXIT_USAGE
    if (args.ready_fd is None) != (args.parent_lifetime_fd is None):
        return EXIT_USAGE
    try:
        handoff = args.handoff.expanduser().resolve(strict=True)
        if handoff.parent.name != "restore-handoffs" or handoff.suffix != ".json":
            return EXIT_HANDOFF_INVALID
        runtime_root = handoff.parent.parent
    except OSError:
        return EXIT_HANDOFF_INVALID

    channel = (
        _WorkerTakeoverChannel(args.ready_fd, args.parent_lifetime_fd)
        if args.ready_fd is not None and args.parent_lifetime_fd is not None
        else None
    )
    try:
        lock = RuntimeInstanceLock(runtime_root, inherited_fd=args.lock_fd)
        lock.acquire()
        try:
            if args.restore_mode == RESTORE_MODE_FINAL_V4_ENCRYPTED:
                if encrypted_service_factory is None:
                    from src.desktop_app.final_v4_runtime_adapters import (
                        DesktopFinalV4RestartLauncher,
                    )
                    from src.desktop_app.runtime import runtime_paths
                    from src.security.final_v4_live_restore import (
                        build_final_v4_live_restore_worker_service,
                    )

                    service = build_final_v4_live_restore_worker_service(
                        runtime_root,
                        restore_id=handoff.stem,
                        product_paths=runtime_paths(runtime_root),
                        restart_launcher=DesktopFinalV4RestartLauncher(),
                    )
                else:
                    service = encrypted_service_factory(runtime_root)
            else:
                service = ProductiveRestoreService()
            service.execute(
                handoff_path=args.handoff,
                nonce=args.nonce,
                lock=lock,
                worker_started=(
                    channel.confirm_and_wait_for_parent_exit
                    if channel is not None
                    else None
                ),
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
    finally:
        if channel is not None:
            channel.close()


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
