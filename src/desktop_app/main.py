"""Entry point for the PySide6 desktop app and packaged-app smoke check."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from src.desktop_app.app import JenaplanDesktopApp

# Kept as a patchable sentinel for pre-existing startup-isolation tests. Qt is
# imported only after restore recovery has admitted normal startup.
QApplication = None

from src.desktop_app.runtime import (
    APP_DATA_DIR_ENV,
    APP_BUNDLE_ID,
    APP_NAME,
    RuntimePaths,
    RuntimeStorageError,
    application_data_root,
    configure_runtime_logging,
    load_build_info,
    prepare_runtime_storage,
    resource_path,
)
from src.version import APP_VERSION


PACKAGED_SMOKE_MARKER_ENV = "JENAPLAN_PACKAGED_SMOKE_MARKER"
PACKAGED_SMOKE_MARKER_VALUE = "isolated-v1"
PACKAGED_SMOKE_TEMP_PREFIX = "jenaplan-packaged-smoke-"


def _validated_packaged_smoke_data_root(
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Require an explicit marker and a dedicated system-temporary data root."""
    environment = os.environ if environ is None else environ
    if environment.get(PACKAGED_SMOKE_MARKER_ENV) != PACKAGED_SMOKE_MARKER_VALUE:
        raise RuntimeStorageError(
            "Packaged-Smoke ohne gueltigen expliziten Smoke-Marker abgelehnt."
        )
    raw_root = environment.get(APP_DATA_DIR_ENV, "")
    data_root = Path(raw_root).expanduser() if raw_root else Path()
    if not raw_root or not data_root.is_absolute():
        raise RuntimeStorageError(
            "Packaged-Smoke ohne absoluten isolierten Datenpfad abgelehnt."
        )
    temporary_root = Path(tempfile.gettempdir()).resolve()
    resolved_root = data_root.resolve(strict=False)
    try:
        relative = resolved_root.relative_to(temporary_root)
    except ValueError as error:
        raise RuntimeStorageError(
            "Packaged-Smoke ausserhalb der temporaeren Datenwurzel abgelehnt."
        ) from error
    smoke_component_index = next(
        (
            index
            for index, component in enumerate(relative.parts)
            if component.startswith(PACKAGED_SMOKE_TEMP_PREFIX)
        ),
        None,
    )
    if smoke_component_index is None:
        raise RuntimeStorageError(
            "Packaged-Smoke ohne eigenes temporaeres Smoke-Verzeichnis abgelehnt."
        )
    smoke_container = temporary_root.joinpath(
        *relative.parts[: smoke_component_index + 1]
    )
    if not smoke_container.is_dir() or smoke_container.is_symlink():
        raise RuntimeStorageError(
            "Das temporaere Smoke-Verzeichnis ist nicht sicher vorhanden."
        )
    return resolved_root


def _app_icon():
    """Return the application icon used for windows and the task switcher."""
    from PySide6.QtGui import QIcon

    icon_path = resource_path("assets", "app_icon.png")
    return QIcon(str(icon_path))


def _argument_value(arguments: list[str], name: str) -> str | None:
    if name not in arguments:
        return None
    index = arguments.index(name)
    if index + 1 >= len(arguments):
        raise RuntimeStorageError(f"Technisches Startargument ohne Wert: {name}")
    value = arguments[index + 1]
    del arguments[index : index + 2]
    return value


def main() -> int:
    """Start the desktop app."""
    arguments = list(sys.argv)
    if "--restore-worker" in arguments:
        arguments.remove("--restore-worker")
        from src.desktop_app.restore_worker import run as run_restore_worker

        return run_restore_worker(arguments[1:])

    packaged_smoke = "--packaged-smoke-test" in arguments
    if packaged_smoke:
        arguments.remove("--packaged-smoke-test")
        try:
            smoke_data_root = _validated_packaged_smoke_data_root()
        except RuntimeStorageError as error:
            print(f"Packaged-App-Smoke abgelehnt: {error}", file=sys.stderr)
            return 2
    else:
        smoke_data_root = None

    try:
        resume_restore_id = _argument_value(arguments, "--restore-resume")
        resume_token = _argument_value(arguments, "--restore-token")
        inherited_lock_value = _argument_value(arguments, "--restore-lock-fd")
        if (resume_restore_id is None) != (resume_token is None):
            raise RuntimeStorageError("Der Restore-Resume-Start ist unvollstaendig.")
        inherited_lock_fd = (
            None if inherited_lock_value is None else int(inherited_lock_value)
        )
    except (RuntimeStorageError, ValueError) as error:
        print(f"App-Start abgelehnt: {error}", file=sys.stderr)
        return 3

    data_root = smoke_data_root or application_data_root()
    from src.core.restore_runtime import (
        RestoreManualRecoveryRequired,
        RestoreRuntimeError,
        RuntimeInstanceLock,
        confirm_restore_startup,
        recover_interrupted_restore,
    )

    lock = RuntimeInstanceLock(data_root, inherited_fd=inherited_lock_fd)
    try:
        lock.acquire()
        if resume_restore_id is not None and resume_token is not None:
            confirm_restore_startup(data_root, resume_restore_id, resume_token)
        else:
            recovery = recover_interrupted_restore(data_root)
            if recovery.status == "resume_required":
                if recovery.restore_id is None or recovery.resume_token is None:
                    raise RestoreManualRecoveryRequired(
                        "Der Resume-Zustand ist unvollstaendig."
                    )
                confirm_restore_startup(
                    data_root,
                    recovery.restore_id,
                    recovery.resume_token,
                )
    except (RestoreManualRecoveryRequired, RestoreRuntimeError) as error:
        lock.release()
        print(
            "App-Start wegen eines unsicheren Restore-Zustands abgelehnt: "
            f"{error}",
            file=sys.stderr,
        )
        return 3

    from PySide6.QtWidgets import QApplication, QMessageBox
    from src.desktop_app.app import JenaplanDesktopApp
    from src.desktop_app.theme import apply_app_theme

    sys.argv[:] = arguments
    app = QApplication(arguments)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Jenaplan")
    app.setOrganizationDomain(APP_BUNDLE_ID)
    app.setDesktopFileName(APP_BUNDLE_ID)
    app.setWindowIcon(_app_icon())
    apply_app_theme(app)

    try:
        paths = prepare_runtime_storage(data_root=smoke_data_root)
        configure_runtime_logging(paths)
        window = JenaplanDesktopApp(paths.database)
    except RuntimeStorageError as error:
        QMessageBox.critical(
            None,
            "App-Daten nicht zugänglich",
            f"{error}\n\nDie App wurde nicht gestartet, damit keine Daten gefährdet werden.",
        )
        lock.release()
        return 1
    except Exception as error:  # pragma: no cover - startup/platform feedback
        logging.exception("Die App konnte nicht initialisiert werden.")
        QMessageBox.critical(
            None,
            "App konnte nicht gestartet werden",
            "Die lokale Datenbank oder eine benötigte Ressource konnte nicht "
            f"geöffnet werden.\n\nDatenordner: {data_root}\nFehler: {error}",
        )
        lock.release()
        return 1

    window.setWindowIcon(_app_icon())
    if packaged_smoke:
        result = _run_packaged_smoke(app, window, paths)
        lock.release()
        return result
    window.showMaximized()
    try:
        return app.exec()
    finally:
        lock.release()


def _run_packaged_smoke(
    app: QApplication,
    window: JenaplanDesktopApp,
    paths: RuntimePaths,
) -> int:
    """Exercise packaged shell, catalog, SQLite, PDF and backup dependencies."""
    from src.application.commands.backup import (
        BackupApplicationService,
        CreateBackupCommand,
    )
    from prototypes.pdf_engine.output_models import (
        DocumentMetadata,
        HeadingBlock,
        ParagraphBlock,
        ReportOutputModel,
        ReportPage,
    )
    from prototypes.pdf_engine.renderer import PdfRenderer

    window.show()
    app.processEvents()
    pdf_path = paths.exports / "packaged-app-smoke.pdf"
    model = ReportOutputModel(
        metadata=DocumentMetadata(
            document_title="Paket-Smoke-Test",
            student_name="Fiktives Testkind",
            group_name="Testgruppe",
            period="Pilot",
            teacher_name="Technischer Test",
            school_name="Jenaplan",
            created_on=date.today(),
            header_text="Jenaplan-Kompetenzmanager",
            footer_text="Technischer Pakettest",
        ),
        pages=(
            ReportPage(
                "Smoke",
                (
                    HeadingBlock("Paket-Smoke-Test"),
                    ParagraphBlock("PDF-Laufzeit erfolgreich geladen."),
                ),
            ),
        ),
    )
    PdfRenderer().render(model, pdf_path)
    build_info = load_build_info()
    backup_result = BackupApplicationService().create(
        CreateBackupCommand(
            database_path=paths.database,
            runtime_paths=paths,
            target_path=paths.backups,
            app_version=APP_VERSION,
            build_commit=str(build_info.get("git_commit", "unknown")),
            source_tree_state=(
                str(build_info["source_tree_state"])
                if build_info.get("source_tree_state") is not None
                else None
            ),
        )
    )
    student_count = len(window.adapter.list_students())
    competency_count = len(window.curriculum_adapter.list_entries())
    payload = {
        "app_version": APP_VERSION,
        "backup_exists": backup_result.path.is_file(),
        "backup_verified": backup_result.verification.path == backup_result.path,
        "build_info": build_info,
        "competency_count": competency_count,
        "data_root": str(paths.root),
        "database_exists": paths.database.is_file(),
        "pdf_exists": pdf_path.is_file(),
        "student_count": student_count,
        "window_title": window.windowTitle(),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
