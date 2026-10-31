"""Focused process/UI handoff checks; migration integrity uses existing product suite."""
from pathlib import Path

import pytest

from src.desktop_app import product_v7_maintenance as maintenance


def test_guided_restart_retains_root_and_completion_flags(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(maintenance.os, "chdir", lambda path: None)
    monkeypatch.setattr(maintenance.os, "execve", lambda exe, command, env: commands.append(command))
    for complete in (False, True):
        with pytest.raises(RuntimeError, match="product_v7_exec_returned"):
            maintenance._restart_maintenance(tmp_path, complete=complete, guided=True)
    assert "--complete-v7-migration" in commands[0]
    assert "--guided-v7-migration" in commands[0]
    assert "--v7-migration-completed" in commands[1]
    assert "--migrate-v4-to-v7" not in commands[1]
    for command in commands:
        assert command[command.index("--runtime-root") + 1] == str(tmp_path)


def test_guided_failure_is_sanitized_and_never_retries(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton
    app = QApplication.instance() or QApplication([])
    calls = []
    def fail(*args, **kwargs):
        calls.append("operation")
        raise RuntimeError("SECRET-PASSWORD /private/student-name")
    monkeypatch.setattr(maintenance, "_perform_maintenance", fail)
    monkeypatch.setattr(maintenance, "_restart_maintenance", lambda *a, **k: calls.append("restart"))
    seen = []
    timer = QTimer()
    def close_error():
        for widget in app.topLevelWidgets():
            buttons = widget.findChildren(QPushButton)
            for button in buttons:
                if button.isVisible() and button.text() == "Schließen":
                    seen.extend(label.text() for label in widget.findChildren(QLabel))
                    button.click()
    timer.timeout.connect(close_error)
    timer.start(10)
    try:
        assert maintenance._run_guided_maintenance(tmp_path, complete=False) == 1
    finally:
        timer.stop()
    assert calls == ["operation"]
    assert seen and "SECRET-PASSWORD" not in " ".join(seen)
    assert "/private/" not in " ".join(seen)
    assert "Wartungsbelege" in " ".join(seen)
