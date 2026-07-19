"""First-steps onboarding contracts for local preferences and shell UI."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
)

from src.core.app_preferences import (
    AppPreferences,
    AppPreferencesError,
    ONBOARDING_BASE_STEP_COUNT,
    ONBOARDING_PILOT_STEP_COUNT,
    OnboardingStatus,
)
from src.core.onboarding import OnboardingController
from src.core.sqlite_store import SQLiteCompetencyRepository, SQLiteDatabase
from src.desktop_app.adapters.curriculum_desktop_adapter import CurriculumDesktopAdapter
from src.desktop_app.runtime import (
    prepare_runtime_storage,
    prepare_security_runtime_storage,
    runtime_paths,
)
from src.desktop_app.screens.onboarding_screen import (
    ONBOARDING_STEPS,
    OnboardingScreen,
    OnboardingStatusProjection,
)
from src.desktop_app.shell import AppShell
from src.security.startup import build_security_runtime


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _runtime(tmp_path: Path):
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    return paths, build_security_runtime(paths)


def test_app_preferences_store_onboarding_states_and_versions(tmp_path: Path) -> None:
    paths, runtime = _runtime(tmp_path)
    assert runtime.preferences.load().onboarding_status is OnboardingStatus.NOT_STARTED
    assert runtime.preferences.load().onboarding_current_step == 0

    for status in OnboardingStatus:
        step = 3 if status is OnboardingStatus.IN_PROGRESS else 0
        runtime.preferences.save(
            AppPreferences(
                inactivity_minutes=30,
                display_name="Laura",
                onboarding_status=status,
                onboarding_current_step=step,
            )
        )
        loaded = runtime.preferences.load()
        assert loaded.inactivity_minutes == 30
        assert loaded.display_name == "Laura"
        assert loaded.onboarding_status is status
        assert loaded.onboarding_current_step == step
        assert not list(paths.root.glob(".app-preferences-*"))

    paths.app_preferences.write_text(
        json.dumps(
            {
                "display_name": "Legacy",
                "format_version": 1,
                "inactivity_minutes": 15,
            }
        ),
        encoding="utf-8",
    )
    migrated = runtime.preferences.load()
    assert migrated.display_name == "Legacy"
    assert migrated.onboarding_status is OnboardingStatus.NOT_STARTED

    paths.app_preferences.write_text(
        json.dumps(
            {
                "display_name": "Neu",
                "format_version": 99,
                "inactivity_minutes": 10,
                "onboarding_status": "future",
                "future_key": "ignored",
            }
        ),
        encoding="utf-8",
    )
    newer = runtime.preferences.load()
    assert newer.display_name == "Neu"
    assert newer.inactivity_minutes == 10
    assert newer.onboarding_status is OnboardingStatus.DISMISSED

    paths.app_preferences.write_text("{", encoding="utf-8")
    with pytest.raises(AppPreferencesError):
        runtime.preferences.load()
    recovered = OnboardingController(runtime.preferences).preferences
    assert recovered.onboarding_status is OnboardingStatus.NOT_STARTED


def test_onboarding_controller_auto_resume_complete_dismiss_and_manual_preview(
    tmp_path: Path,
) -> None:
    _paths, runtime = _runtime(tmp_path)
    controller = OnboardingController(runtime.preferences)
    assert controller.should_open_automatically()
    assert not controller.should_open_automatically(packaged_smoke=True)

    session = controller.start()
    assert session.current_step == 0
    assert runtime.preferences.load().onboarding_status is OnboardingStatus.IN_PROGRESS
    controller.set_step(2)
    assert runtime.preferences.load().onboarding_current_step == 2

    resumed = OnboardingController(runtime.preferences).start()
    assert resumed.current_step == 2
    OnboardingController(runtime.preferences).complete()
    assert not OnboardingController(runtime.preferences).should_open_automatically()

    preview_controller = OnboardingController(runtime.preferences)
    preview = preview_controller.start(manual=True)
    assert preview.manual_preview
    assert runtime.preferences.load().onboarding_status is OnboardingStatus.COMPLETED
    preview_controller.next_step()
    assert runtime.preferences.load().onboarding_status is OnboardingStatus.IN_PROGRESS

    preview_controller.dismiss()
    assert runtime.preferences.load().onboarding_status is OnboardingStatus.DISMISSED
    assert not OnboardingController(runtime.preferences).should_open_automatically()


def test_onboarding_screen_steps_keyboard_skip_and_sizes() -> None:
    app = _app()
    screen = OnboardingScreen()
    screen.set_context(
        step=0,
        display_name="Laura",
        status_projection=OnboardingStatusProjection(
            documentation_subjects_configured=True,
            timetable_configured=False,
            organization_configured=None,
            children_configured=True,
        ),
    )
    texts = " ".join(label.text() for label in screen.findChildren(QLabel))
    assert "Willkommen, Laura" in texts
    assert "Die App-Sperre ist keine Verschlüsselung" in texts
    assert len(ONBOARDING_STEPS) == ONBOARDING_BASE_STEP_COUNT

    emitted: list[str] = []
    screen.next_requested.connect(lambda: emitted.append("next"))
    screen.skip_confirmed.connect(lambda: emitted.append("skip"))
    screen.show()
    app.processEvents()
    screen.next_button.setFocus()
    QTest.keyClick(screen.next_button, Qt.Key.Key_Return)
    assert emitted == ["next"]

    QTest.keyClick(screen, Qt.Key.Key_Escape)
    assert emitted == ["next"]
    for width, height in ((1180, 760), (1400, 900)):
        screen.resize(width, height)
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Escape):
            message, skip_button = screen._skip_confirmation_message()
            keep_button = next(
                button for button in message.buttons() if button.text() == "Weiter ansehen"
            )
            try:
                message.show()
                app.processEvents()
                assert "Erste Schritte jetzt überspringen?" in message.text()
                assert skip_button.text() == "Erste Schritte überspringen"
                assert skip_button.minimumWidth() >= (
                    skip_button.fontMetrics().horizontalAdvance(skip_button.text()) + 40
                )
                assert keep_button.property("buttonRole") == "primary"
                assert keep_button.isDefault()
                button_box = message.findChild(QDialogButtonBox)
                assert button_box.layout().spacing() >= 12
                keep_button.setFocus()
                app.processEvents()
                assert keep_button.hasFocus()
                target = keep_button if key == Qt.Key.Key_Return else message
                QTest.keyClick(target, key)
                app.processEvents()
                assert message.clickedButton() is not skip_button
                if key == Qt.Key.Key_Return:
                    assert message.clickedButton() is keep_button
                else:
                    assert message.clickedButton() in (None, keep_button)
            finally:
                message.close()
                message.hide()
                message.deleteLater()
                app.processEvents()
    screen._skip_confirmation_accepted = lambda: True
    screen.skip_button.click()
    assert emitted[-1] == "skip"

    for width, height in ((1180, 760), (1400, 900)):
        screen.resize(width, height)
        app.processEvents()
        scroll = screen.findChild(QScrollArea)
        assert scroll.horizontalScrollBar().maximum() == 0
    screen.close()


def test_pilot_onboarding_adds_only_deliberate_restore_and_guide_actions() -> None:
    _app()
    screen = OnboardingScreen()
    screen.set_context(
        step=ONBOARDING_PILOT_STEP_COUNT - 1,
        display_name="Laura",
        status_projection=OnboardingStatusProjection(),
        pilot_mode=True,
    )
    texts = " ".join(label.text() for label in screen.findChildren(QLabel))
    assert "Pilottest mit Beispieldaten fortsetzen" in texts
    assert "synthetischen Datenbestand" in texts
    assert screen.next_button.text() == "Später über Einstellungen"
    labels = {button.text() for button in screen.findChildren(QPushButton)}
    assert "Testdaten jetzt einspielen" in labels
    assert "Anleitung öffnen" in labels

    screen.set_context(
        step=ONBOARDING_BASE_STEP_COUNT - 1,
        display_name=None,
        status_projection=OnboardingStatusProjection(),
        pilot_mode=False,
    )
    assert screen.step_count == ONBOARDING_BASE_STEP_COUNT
    assert screen.next_button.text() == "Abschließen"


def test_shell_opens_onboarding_after_auth_and_navigates_existing_targets(
    tmp_path: Path,
) -> None:
    app = _app()
    shell, runtime = _shell_with_onboarding(
        tmp_path,
        AppPreferences(display_name="Laura"),
    )
    try:
        shell.configure_onboarding(
            preferences_file=runtime.preferences,
            preferences=runtime.preferences.load(),
            automatic_open=True,
        )
        app.processEvents()
        assert shell.stack.currentWidget() is shell.onboarding_screen
        assert runtime.preferences.load().onboarding_status is OnboardingStatus.IN_PROGRESS

        shell._navigate_from_onboarding("settings_timetable")
        assert shell.stack.currentWidget() is shell.settings_screen
        assert shell.settings_screen.current_page == "timetable"
        assert shell.onboarding_return_button.isVisible()
        assert runtime.preferences.load().onboarding_current_step == 0

        shell._return_to_onboarding()
        assert shell.stack.currentWidget() is shell.onboarding_screen
        shell._onboarding_next()
        shell._navigate_from_onboarding("master_data")
        assert shell.stack.currentWidget() is shell.master_data_screen
        assert runtime.preferences.load().onboarding_current_step == 1

        shell._return_to_onboarding()
        shell._onboarding_complete()
        assert runtime.preferences.load().onboarding_status is OnboardingStatus.COMPLETED
        assert shell.stack.currentWidget() is shell.dashboard_screen
    finally:
        shell.close()


def test_shell_respects_completed_dismissed_in_progress_and_missing_targets(
    tmp_path: Path,
) -> None:
    app = _app()
    completed_shell, completed_runtime = _shell_with_onboarding(
        tmp_path / "completed",
        AppPreferences(onboarding_status=OnboardingStatus.COMPLETED),
    )
    try:
        completed_shell.configure_onboarding(
            preferences_file=completed_runtime.preferences,
            preferences=completed_runtime.preferences.load(),
            automatic_open=True,
        )
        app.processEvents()
        assert completed_shell.stack.currentWidget() is completed_shell.dashboard_screen
    finally:
        completed_shell.close()

    dismissed_shell, dismissed_runtime = _shell_with_onboarding(
        tmp_path / "dismissed",
        AppPreferences(onboarding_status=OnboardingStatus.DISMISSED),
    )
    try:
        dismissed_shell.configure_onboarding(
            preferences_file=dismissed_runtime.preferences,
            preferences=dismissed_runtime.preferences.load(),
            automatic_open=True,
        )
        app.processEvents()
        assert dismissed_shell.stack.currentWidget() is dismissed_shell.dashboard_screen
        dismissed_shell.open_onboarding_from_settings()
        assert dismissed_runtime.preferences.load().onboarding_status is OnboardingStatus.DISMISSED
        dismissed_shell._onboarding_next()
        assert dismissed_runtime.preferences.load().onboarding_status is OnboardingStatus.IN_PROGRESS
    finally:
        dismissed_shell.close()

    progress_shell, progress_runtime = _shell_with_onboarding(
        tmp_path / "progress",
        AppPreferences(
            onboarding_status=OnboardingStatus.IN_PROGRESS,
            onboarding_current_step=3,
        ),
    )
    try:
        progress_shell.configure_onboarding(
            preferences_file=progress_runtime.preferences,
            preferences=progress_runtime.preferences.load(),
            automatic_open=True,
        )
        app.processEvents()
        assert progress_shell.onboarding_screen.current_step == 3
        progress_shell._navigate_from_onboarding("missing")
        assert "nicht verfügbar" in progress_shell.status_label.text()
    finally:
        progress_shell.close()


def _shell_with_onboarding(tmp_path: Path, preferences: AppPreferences):
    root = tmp_path / "runtime"
    root.mkdir(parents=True, exist_ok=True)
    paths = runtime_paths(root)
    database = SQLiteDatabase(paths.database)
    database.initialize_schema()
    database.ensure_master_data_defaults()
    SQLiteCompetencyRepository(database).ensure_catalog_defaults(
        CurriculumDesktopAdapter(database=database).list_entries()
    )
    resources = tmp_path / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    paths = prepare_runtime_storage(data_root=root, resource_root_path=resources)
    security_paths = prepare_security_runtime_storage(data_root=root)
    runtime = build_security_runtime(security_paths)
    runtime.preferences.save(preferences)
    shell = AppShell(paths.database, paths=paths)
    shell.set_display_name(preferences.display_name)
    shell.show()
    _app().processEvents()
    return shell, runtime
