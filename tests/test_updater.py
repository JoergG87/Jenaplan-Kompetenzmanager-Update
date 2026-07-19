"""Update service and settings projection without network or native side effects."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.desktop_app.screens.settings_screen import SettingsScreen
from src.updater.application import UpdateApplicationService
from src.updater.domain import UpdateChannel, UpdateState


class FakeUpdateAdapter:
    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self._can_check = available
        self.checked = 0
        self.last_checked: str | None = None

    @property
    def available(self) -> bool:
        return self._available

    @property
    def can_check(self) -> bool:
        return self._can_check

    def last_check_date(self) -> str | None:
        return self.last_checked

    def check_for_updates(self) -> None:
        self.checked += 1
        self._can_check = False
        self.last_checked = "2026-07-19T20:30:00Z"


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_update_service_is_explicit_pilot_only_and_projects_no_secret() -> None:
    adapter = FakeUpdateAdapter()
    service = UpdateApplicationService(
        adapter,
        current_version="0.2.1",
        build_version="201",
        channel=UpdateChannel.PILOT,
    )
    initial = service.projection()
    assert initial.state is UpdateState.READY
    assert initial.channel is UpdateChannel.PILOT
    assert initial.last_checked_at is None
    assert adapter.checked == 0

    checking = service.check_for_updates()
    assert adapter.checked == 1
    assert checking.state is UpdateState.CHECKING
    assert checking.last_checked_at == "2026-07-19T20:30:00Z"


def test_update_service_fails_closed_when_native_adapter_is_unavailable() -> None:
    service = UpdateApplicationService(
        FakeUpdateAdapter(available=False),
        current_version="0.2.1",
        build_version="201",
    )
    projection = service.check_for_updates()
    assert projection.state is UpdateState.UNAVAILABLE
    assert not projection.can_check
    assert "DMG" in projection.message


def test_settings_updates_page_is_one_local_destination() -> None:
    _app()
    screen = SettingsScreen()
    adapter = FakeUpdateAdapter()
    projection = UpdateApplicationService(
        adapter,
        current_version="0.2.1",
        build_version="201",
    ).projection()
    screen.set_update_status(projection)
    assert set(screen.settings_cards) == {
        "timetable",
        "documentation_subjects",
        "backup_restore",
        "security",
        "updates",
    }
    screen.show_page("updates")
    assert screen.current_page == "updates"
    assert "0.2.1" in screen.update_version_label.text()
    assert "Pilot" in screen.update_channel_label.text()
    assert screen.update_check_button.isEnabled()
