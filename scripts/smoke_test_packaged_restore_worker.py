"""Start the real packaged restore worker and verify its takeover protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.commands.backup import (
    BackupApplicationService,
    CreateBackupCommand,
)
from src.application.commands.restore import (
    CreateRestoreHandoffCommand,
    PrepareRestoreStagingCommand,
    RestoreApplicationService,
)
from src.core.restore_runtime import (
    RestoreJournal,
    RuntimeInstanceLock,
    recover_interrupted_restore,
    restore_transaction_paths,
)
from src.core.sqlite_store import SQLiteDatabase
from src.desktop_app.restore_worker import (
    launch_restore_worker,
    resolve_restore_worker_launch,
)
from src.desktop_app.runtime import RuntimePaths, runtime_paths
from src.version import APP_VERSION


APP_NAME = "Jenaplan-Kompetenzmanager"


def _prepare_runtime(root: Path) -> RuntimePaths:
    paths = runtime_paths(root)
    for directory in (
        paths.root,
        paths.documents,
        paths.exports,
        paths.backups,
        paths.logs,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    SQLiteDatabase(paths.database).initialize_schema()
    return paths


def _insert_marker(paths: RuntimePaths, marker: str) -> None:
    with sqlite3.connect(paths.database) as connection:
        connection.execute(
            "INSERT INTO groups VALUES (?, ?, 0, 1)",
            (f"GRP-{marker}", f"Gruppe {marker}"),
        )


def _snapshot(paths: RuntimePaths) -> dict[str, str]:
    result = {
        "kompetenzmanager.sqlite": hashlib.sha256(
            paths.database.read_bytes()
        ).hexdigest()
    }
    result.update(
        {
            f"documents/{path.relative_to(paths.documents).as_posix()}": (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )
            for path in paths.documents.rglob("*")
            if path.is_file()
        }
    )
    return result


def smoke_test(app_path: Path) -> dict[str, object]:
    app = Path(app_path).expanduser().resolve(strict=True)
    executable = app / "Contents" / "MacOS" / APP_NAME
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError("Der gebuendelte Restore-Worker ist nicht ausfuehrbar.")

    with tempfile.TemporaryDirectory(
        prefix="jenaplan-packaged-restore-worker-"
    ) as temporary:
        root = Path(temporary)
        source = _prepare_runtime(root / "source")
        live = _prepare_runtime(root / "live")
        _insert_marker(source, "SOURCE")
        _insert_marker(live, "LIVE")
        before = _snapshot(live)

        archive = BackupApplicationService().create(
            CreateBackupCommand(
                database_path=source.database,
                runtime_paths=source,
                target_path=source.backups,
                app_version=APP_VERSION,
                build_commit="0000000",
                source_tree_state="clean",
            )
        ).path
        restore_id = "RST-PACKAGED-WORKER-SMOKE"
        service = RestoreApplicationService()
        service.prepare_staging(
            PrepareRestoreStagingCommand(
                path=archive,
                runtime_paths=live,
                restore_id=restore_id,
            )
        )
        handoff = service.create_handoff(
            CreateRestoreHandoffCommand(
                path=archive,
                restore_id=restore_id,
                runtime_paths=live,
                app_version=APP_VERSION,
                build_commit="0000000",
                source_tree_state="clean",
            )
        )
        plan = resolve_restore_worker_launch(
            live.root,
            executable=executable,
            frozen=True,
        )
        lock = RuntimeInstanceLock(live.root).acquire()
        started = launch_restore_worker(
            handoff=handoff.path,
            nonce=handoff.nonce,
            lock=lock,
            launch_plan=plan,
        )
        try:
            if started.process.poll() is not None:
                raise RuntimeError("Der gebuendelte Restore-Worker lief nicht weiter.")
            state = RestoreJournal(
                restore_transaction_paths(live.root, restore_id)
            ).read()
            if state.get("phase") != "worker_started":
                raise RuntimeError(
                    "Der gebuendelte Restore-Worker bestaetigte die Uebernahme nicht."
                )
            if _snapshot(live) != before:
                raise RuntimeError(
                    "Der gebuendelte Restore-Worker veraenderte Daten vor Parent-Ende."
                )
            if (
                os.name == "posix"
                and os.getsid(started.process.pid) != started.process.pid
            ):
                raise RuntimeError(
                    "Der gebuendelte Restore-Worker besitzt keine eigene Prozessgruppe."
                )
        finally:
            if started.process.poll() is None:
                started.process.terminate()
            started.process.wait(timeout=5)
            os.close(started.parent_lifetime_fd)

        recovery = recover_interrupted_restore(live.root)
        if recovery.status != "aborted_before_replacement":
            raise RuntimeError(
                "Der abgebrochene Pakettest wurde nicht sicher zurueckgenommen."
            )
        if _snapshot(live) != before:
            raise RuntimeError("Der Pakettest veraenderte den Live-Bestand.")
        return {
            "app": str(app),
            "command_prefix": list(plan.command_prefix),
            "working_directory_is_runtime_root": (
                plan.working_directory == live.root.resolve()
            ),
            "worker_exit_code": started.process.returncode,
            "journal_phase": recovery.status,
            "live_data_unchanged": True,
            "worker_reaped": started.process.poll() is not None,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-Test fuer den gebuendelten Restore-Worker"
    )
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    print(json.dumps(smoke_test(args.app), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
