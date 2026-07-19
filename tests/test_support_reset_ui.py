"""Offscreen contracts for the guided support-reset handoff."""

from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import UTC, datetime, timedelta
import base64
import time
from pathlib import Path

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton

from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.runtime import prepare_security_runtime_storage
from src.desktop_app.support_reset import SUPPORT_RESET_NOT_RELEASED, SupportResetDialog
from src.security.domain import (
    SUPPORT_RESET_ACTION,
    SUPPORT_RESET_MAX_TOKEN_BYTES,
    SecurityBackupProof,
    SupportResetRequest,
    SupportResetResult,
    SupportResetVerificationResult,
)
from src.security.support_reset import SupportResetTokenCodec
from src.security.infrastructure.key_registry import PublicKeyRegistry
from src.security.startup import build_security_runtime


NOW = datetime(2026, 7, 17, 14, 0, tzinfo=UTC)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _wait_until(predicate, timeout: float = 2.0) -> None:
    app = _app()
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert predicate()


class _Backup:
    def create_and_verify(self):
        return SecurityBackupProof("/tmp/support-reset-backup.jkmbackup", "a" * 64)


class _BackupFactory:
    def create(self):
        return _Backup()


class _Service:
    def __init__(self, *, enabled: bool) -> None:
        self.product_enabled = enabled
        self.verify_calls = 0
        self.execute_calls = 0
        self.request = SupportResetRequest(
            format_version=1,
            installation_id="11111111-1111-4111-8111-111111111111",
            user_id="22222222-2222-4222-8222-222222222222",
            reset_request_id="33333333-3333-4333-8333-333333333333",
            action=SUPPORT_RESET_ACTION,
            created_at=NOW,
            expires_at=NOW + timedelta(hours=24),
            nonce=base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("="),
        )

    def create_request(self):
        return self.request

    def verify_token(self, _token: str):
        self.verify_calls += 1
        return SupportResetVerificationResult(
            self.request.reset_request_id,
            "support-test-a",
            NOW + timedelta(minutes=30),
        )

    def execute(self, _token: str, *, backup):
        self.execute_calls += 1
        proof = backup.create_and_verify()
        return SupportResetResult(self.request.reset_request_id, 2, proof)


def test_empty_product_registry_allows_request_but_blocks_token_step(
    tmp_path: Path, monkeypatch
) -> None:
    app = _app()
    monkeypatch.setattr(
        "src.security.startup.DEFAULT_SUPPORT_KEY_REGISTRY", PublicKeyRegistry()
    )
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    runtime.service.enroll_local_account("eine ausreichend lange Support-Reset-Testpassphrase")
    service = runtime.support_reset
    assert service.product_enabled is False
    dialog = SupportResetDialog(service=service, backup_factory=_BackupFactory())
    assert SUPPORT_RESET_NOT_RELEASED in dialog.release_message.label.text()
    app.clipboard().setText("unverändert")
    dialog._create_request()
    _wait_until(lambda: dialog._request is not None and not dialog._busy)
    assert "display_name" not in dialog.request_display.toPlainText()
    assert app.clipboard().text() == "unverändert"
    assert not tuple((tmp_path / "runtime").rglob("*.jkmresetrequest"))
    dialog._copy_request()
    assert app.clipboard().text().startswith("{")
    assert dialog.open_token_button.isEnabled() is False
    dialog.reject()


def test_token_preview_is_separate_from_explicit_reset() -> None:
    _app()
    service = _Service(enabled=True)
    dialog = SupportResetDialog(service=service, backup_factory=_BackupFactory())
    dialog._create_request()
    _wait_until(lambda: dialog._request is not None and not dialog._busy)
    dialog.stack.setCurrentWidget(dialog.token_page)
    dialog.token_input.setPlainText("  JKM-SR1.payload.signature\n")
    dialog._verify_token()
    _wait_until(lambda: dialog.stack.currentWidget() is dialog.preview_page and not dialog._busy)
    assert service.verify_calls == 1
    assert service.execute_calls == 0
    assert dialog.execute_button.text() == "Sicherheitsbackup erstellen und Passwort zurücksetzen"
    dialog._back_to_token()
    dialog.reject()
    assert service.execute_calls == 0


def test_request_export_and_bounded_token_import_are_explicit(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    service = _Service(enabled=True)
    dialog = SupportResetDialog(service=service, backup_factory=_BackupFactory())
    dialog._request = service.request
    target = tmp_path / "request.jkmresetrequest"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(target), ""),
    )
    dialog._export_request()
    assert SupportResetTokenCodec.decode_request(target.read_bytes()) == service.request
    if os.name == "posix":
        assert target.stat().st_mode & 0o777 == 0o600

    oversized = tmp_path / "too-large.jkmresettoken"
    oversized.write_bytes(b"x" * (SUPPORT_RESET_MAX_TOKEN_BYTES + 9))
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(oversized), ""),
    )
    dialog._import_token()
    assert dialog.token_input.toPlainText() == ""
    assert "ungültig, abgelaufen" in dialog.token_message.label.text()
    dialog.reject()


def test_confirmed_reset_emits_handoff_only_after_worker_success() -> None:
    _app()
    service = _Service(enabled=True)
    dialog = SupportResetDialog(service=service, backup_factory=_BackupFactory())
    completed = QSignalSpy(dialog.reset_completed)
    dialog._request = service.request
    dialog._verified_token = "JKM-SR1.payload.signature"
    dialog.stack.setCurrentWidget(dialog.preview_page)
    dialog._execute_reset()
    _wait_until(lambda: completed.count() == 1 and not dialog._busy)
    assert service.execute_calls == 1
    assert dialog._committed is True
    assert dialog._verified_token == ""


def test_settings_exposes_recovery_action_without_support_reset_navigation_area() -> None:
    _app()
    screen = SettingsScreen()
    buttons = {
        button.text(): button for button in screen.findChildren(QPushButton)
    }
    assert "Technische Support-Reset-Anfrage erstellen" in buttons
    assert set(screen.settings_cards) == {
        "timetable",
        "documentation_subjects",
        "backup_restore",
        "security",
        "updates",
    }
    spy = QSignalSpy(screen.support_reset_requested)
    buttons["Technische Support-Reset-Anfrage erstellen"].click()
    assert spy.count() == 1
