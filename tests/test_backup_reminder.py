"""Read-only backup reminder boundaries and settings behavior."""

from datetime import UTC, datetime, timedelta

import pytest
from PySide6.QtWidgets import QApplication

from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.view_models.backup_restore_view_model import (
    BackupSummaryViewModel,
    build_backup_reminder,
)


@pytest.mark.parametrize(
    "timestamp,verified,checked,expected",
    [
        (None, True, False, "unknown"),
        (None, True, True, "missing"),
        ("2026-09-07T10:00:00Z", True, True, "current"),
        ("2026-08-31T10:00:01Z", True, True, "current"),
        ("2026-08-31T10:00:00Z", True, True, "due"),
        ("2026-08-31T12:00:00+02:00", True, True, "due"),
        ("2026-09-07T10:00:01Z", True, True, "unknown"),
        ("2026-08-31T10:00:00", True, True, "unknown"),
        ("not a timestamp", True, True, "unknown"),
        ("2026-08-31T10:00:00Z", False, True, "unknown"),
        ("2026-08-31T10:00:00Z", True, False, "unknown"),
    ],
)
def test_only_confirmed_valid_timestamps_produce_age_reminders(
    timestamp, verified, checked, expected
):
    summary = BackupSummaryViewModel(timestamp, "synthetic.jkmebackup", 2048, verified) if timestamp else None
    reminder = build_backup_reminder(
        summary, now=datetime(2026, 9, 7, 10, tzinfo=UTC), checked=checked,
    )
    assert reminder.state == expected
    assert "synthetic" not in reminder.message
    assert ("Tage" in reminder.message) == (expected == "due")


def test_settings_recomputes_age_and_clears_reminder_after_verified_backup():
    app = QApplication.instance() or QApplication([])
    instant = datetime(2026, 9, 7, 10, tzinfo=UTC)
    screen = SettingsScreen(now_provider=lambda: instant)
    created = []
    screen.backup_create_requested.connect(lambda: created.append(True))
    assert "nicht bestätigt" in screen.settings_cards["backup_restore"].status.text()
    screen.set_backup_status(None)
    assert "gefunden" in screen.backup_reminder.label.text()
    summary = BackupSummaryViewModel(instant.isoformat(), "synthetic.jkmebackup", 2048, True)
    screen.show_backup_success(summary)
    assert screen.backup_reminder.label.text() == ""
    instant += timedelta(days=7)
    screen.show_overview()
    assert "vor 7 Tagen" in screen.settings_cards["backup_restore"].status.text()
    screen.show_page("backup_restore")
    assert "7 Tage alt" in screen.backup_reminder.label.text()
    screen.set_backup_restore_available(False)
    assert screen.backup_reminder.label.text() == ""
    assert screen.settings_cards["backup_restore"].status.text() == "Noch nicht verfügbar"
    screen.set_backup_status(None, checked=False)
    assert "nicht bestätigt" in screen.latest_backup_label.text()
    assert created == []
    screen.close()
    app.processEvents()
