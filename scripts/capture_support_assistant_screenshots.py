"""Create privacy-neutral screenshots of the separate Support-Assistent."""

from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.security.domain import SupportResetRequest
from src.security.support_reset import SupportResetTokenCodec
from src.support_assistant.application import (
    SupportAssistantApplicationService,
    support_request_reference,
)
from src.support_assistant.product_key import SUPPORT_ASSISTANT_PRODUCT_KEY
from src.support_assistant.ui import SupportAssistantWindow


NOW = datetime(2026, 7, 20, 10, 15, tzinfo=UTC)


def capture(output: Path) -> tuple[Path, ...]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
    with tempfile.TemporaryDirectory(prefix="jenaplan-support-assistant-shot-") as temporary:
        service = SupportAssistantApplicationService.from_product_manifest(
            SUPPORT_ASSISTANT_PRODUCT_KEY,
            audit_path=Path(temporary) / "audit.jsonl",
            now_fn=lambda: NOW,
        )
        start_window = SupportAssistantWindow(service)
        start_window.resize(960, 760)
        start_window.show()
        app.processEvents()
        start = output / "01_start.png"
        start_window.grab().save(str(start), "PNG")
        start_window.close()

        request = SupportResetRequest(
            format_version=1,
            installation_id="5e9a2a9d-382f-46e5-a8b4-d3043c7e60b1",
            user_id="8a39fbd8-5d4d-4e98-81d7-3b82a9dd43eb",
            reset_request_id="ccf4cb52-3906-4aec-a03a-4b7b27ded927",
            action="reset_local_password_v1",
            created_at=NOW - timedelta(minutes=8),
            expires_at=NOW + timedelta(hours=23, minutes=52),
            nonce=base64.urlsafe_b64encode(b"s" * 32).decode("ascii").rstrip("="),
        )
        loaded = service.inspect_request_bytes(
            SupportResetTokenCodec.canonical_request_bytes(request)
        )
        review_window = SupportAssistantWindow(service)
        review_window.resize(960, 760)
        review_window.show_loaded_request(loaded)
        review_window.device_name_input.setText("Laura MacBook")
        review_window.private_key_value.setText("support-2026-b-private.pem")
        review_window.show()
        app.processEvents()
        review = output / "02_anfrage_geprueft.png"
        review_window.grab().save(str(review), "PNG")
        review_window.close()

        reference = support_request_reference("Laura MacBook", request.reset_request_id)
        result_window = SupportAssistantWindow(service)
        result_window.resize(960, 760)
        result_window.show_demo_result(
            reference=reference, expires_at=NOW + timedelta(minutes=30)
        )
        result_window.show()
        app.processEvents()
        result = output / "03_reset_code_bereit.png"
        result_window.grab().save(str(result), "PNG")
        result_window.close()
    return start, review, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "support_assistant" / "screenshots",
    )
    args = parser.parse_args()
    for path in capture(args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
