#!/usr/bin/env python3
"""Launch the independent graphical Jenaplan Support-Assistent."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox

from src.support_assistant.application import SupportAssistantApplicationService
from src.support_assistant.product_key import SUPPORT_ASSISTANT_PRODUCT_KEY
from src.support_assistant.ui import SupportAssistantWindow


APP_NAME = "Jenaplan Support-Assistent"


def default_audit_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "Jenaplan Support-Assistent"
        / "audit.jsonl"
    )


def create_service() -> SupportAssistantApplicationService:
    return SupportAssistantApplicationService.from_product_manifest(
        SUPPORT_ASSISTANT_PRODUCT_KEY,
        audit_path=default_audit_path(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--packaged-smoke-test", action="store_true")
    args, _unknown = parser.parse_known_args(argv)
    try:
        service = create_service()
        key = service.key_projection()
    except Exception as error:
        if args.packaged_smoke_test:
            code = getattr(error, "code", error.__class__.__name__)
            print(f"support_assistant_packaged_smoke=failed:{code}", file=sys.stderr)
            return 2
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None,
            APP_NAME,
            "Der öffentliche Supportschlüssel konnte nicht sicher geprüft werden.",
        )
        return 2
    if args.packaged_smoke_test:
        if key.key_id != "support-2026-b" or key.status != "active":
            return 2
        print("support_assistant_packaged_smoke=ok")
        return 0
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Jenaplan")
    window = SupportAssistantWindow(service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
