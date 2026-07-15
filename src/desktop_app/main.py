"""Entry point for the PySide6 desktop app and packaged-app smoke check."""

from __future__ import annotations

import json
import logging
import sys
from datetime import date

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.desktop_app.app import JenaplanDesktopApp
from src.desktop_app.runtime import (
    APP_BUNDLE_ID,
    APP_NAME,
    RuntimePaths,
    RuntimeStorageError,
    configure_runtime_logging,
    load_build_info,
    prepare_runtime_storage,
    resource_path,
)
from src.desktop_app.theme import apply_app_theme
from src.version import APP_VERSION


def _app_icon() -> QIcon:
    """Return the application icon used for windows and the task switcher."""
    icon_path = resource_path("assets", "app_icon.png")
    return QIcon(str(icon_path))


def main() -> int:
    """Start the desktop app."""
    packaged_smoke = "--packaged-smoke-test" in sys.argv
    if packaged_smoke:
        sys.argv.remove("--packaged-smoke-test")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Jenaplan")
    app.setOrganizationDomain(APP_BUNDLE_ID)
    app.setDesktopFileName(APP_BUNDLE_ID)
    app.setWindowIcon(_app_icon())
    apply_app_theme(app)

    try:
        paths = prepare_runtime_storage()
        configure_runtime_logging(paths)
        window = JenaplanDesktopApp(paths.database)
    except RuntimeStorageError as error:
        QMessageBox.critical(
            None,
            "App-Daten nicht zugänglich",
            f"{error}\n\nDie App wurde nicht gestartet, damit keine Daten gefährdet werden.",
        )
        return 1
    except Exception as error:  # pragma: no cover - startup/platform feedback
        logging.exception("Die App konnte nicht initialisiert werden.")
        QMessageBox.critical(
            None,
            "App konnte nicht gestartet werden",
            "Die lokale Datenbank oder eine benötigte Ressource konnte nicht "
            f"geöffnet werden.\n\nDatenordner: {paths.root}\nFehler: {error}",
        )
        return 1

    window.setWindowIcon(_app_icon())
    if packaged_smoke:
        return _run_packaged_smoke(app, window, paths)
    window.showMaximized()
    return app.exec()


def _run_packaged_smoke(
    app: QApplication,
    window: JenaplanDesktopApp,
    paths: RuntimePaths,
) -> int:
    """Exercise the packaged shell, catalog, SQLite and PDF dependencies."""
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
    student_count = len(window.adapter.list_students())
    competency_count = len(window.curriculum_adapter.list_entries())
    payload = {
        "app_version": APP_VERSION,
        "build_info": load_build_info(),
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
