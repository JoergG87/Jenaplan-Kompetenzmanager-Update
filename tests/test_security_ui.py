"""Offscreen security-view and settings contracts."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
)

from src.core.app_preferences import AppPreferences, DISPLAY_NAME_MAX_LENGTH

from src.desktop_app.runtime import prepare_security_runtime_storage
from src.desktop_app.screens.settings_screen import SettingsScreen
from src.desktop_app.security_controller import SecurityUiCoordinator
from src.desktop_app.security_ui import AuthenticationDialog
from src.security.session import InMemorySession, SessionLockReason
from src.security.domain import LocalAuthenticationAvailability
from src.security.startup import (
    SecurityStartState,
    SecurityStartupDecision,
    build_security_runtime,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_fail_closed_dialog_is_opaque_and_has_no_product_content() -> None:
    _app()
    dialog = AuthenticationDialog(
        service=None,
        repository=None,
        decision=SecurityStartupDecision(
            SecurityStartState.CORRUPT, "SEC-CORRUPT"
        ),
    )
    assert dialog.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert "background" in dialog.styleSheet().lower()
    visible = dialog.error_text.text()
    assert "SEC-CORRUPT" in visible
    assert "Schüler" not in visible
    assert "Beobachtung" not in visible


def test_first_and_legacy_enrollment_offer_optional_bounded_display_name() -> None:
    _app()
    for state in (SecurityStartState.FIRST_RUN, SecurityStartState.LEGACY_ENROLLMENT):
        dialog = AuthenticationDialog(
            service=None,
            repository=None,
            decision=SecurityStartupDecision(state, "SEC-ENROLLMENT"),
        )
        assert dialog.display_name.isVisibleTo(dialog.password_page)
        assert dialog.display_name.maxLength() == DISPLAY_NAME_MAX_LENGTH
        assert dialog.display_name.placeholderText() == "Zum Beispiel Laura"
        assert "Optional" in dialog.display_name_hint.text()


def test_login_enter_submits_password_without_opening_recovery() -> None:
    app = _app()
    dialog = AuthenticationDialog(
        service=None,
        repository=None,
        decision=SecurityStartupDecision(
            SecurityStartState.LOGIN_REQUIRED, "SEC-LOGIN_REQUIRED"
        ),
    )
    dialog.show()
    app.processEvents()
    assert dialog.submit_button.isDefault()
    assert not dialog.recovery_submit.isDefault()
    assert not dialog.codes_page.button.isDefault()

    actions: list[str] = []
    dialog.submit_button.clicked.disconnect()
    dialog.submit_button.clicked.connect(lambda: actions.append("login"))
    dialog.recovery_button.clicked.disconnect()
    dialog.recovery_button.clicked.connect(lambda: actions.append("recovery"))
    dialog.password.setFocus()
    QTest.keyClick(dialog.password, Qt.Key.Key_Return)

    assert actions == ["login"]
    assert dialog.stack.currentWidget() is dialog.password_page
    dialog.close()


def test_recovery_enter_submits_code_once() -> None:
    app = _app()
    dialog = AuthenticationDialog(
        service=None,
        repository=None,
        decision=SecurityStartupDecision(
            SecurityStartState.LOGIN_REQUIRED, "SEC-LOGIN_REQUIRED"
        ),
    )
    dialog.show()
    dialog._open_recovery()
    app.processEvents()
    assert not dialog.submit_button.isDefault()
    assert dialog.recovery_submit.isDefault()
    assert not dialog.codes_page.button.isDefault()

    actions: list[str] = []
    dialog.submit_button.clicked.disconnect()
    dialog.submit_button.clicked.connect(lambda: actions.append("login"))
    dialog.recovery_submit.clicked.disconnect()
    dialog.recovery_submit.clicked.connect(lambda: actions.append("recovery"))
    dialog.recovery_code.setFocus()
    QTest.keyClick(dialog.recovery_code, Qt.Key.Key_Return)

    assert actions == ["recovery"]
    assert dialog.stack.currentWidget() is dialog.recovery_page
    dialog.close()


def test_password_reset_pending_enter_submits_new_password_once() -> None:
    app = _app()
    dialog = AuthenticationDialog(
        service=None,
        repository=None,
        decision=SecurityStartupDecision(
            SecurityStartState.PASSWORD_RESET_PENDING,
            "SEC-PASSWORD_RESET_PENDING",
        ),
    )
    dialog.show()
    app.processEvents()
    assert dialog.submit_button.isDefault()
    assert not dialog.recovery_submit.isDefault()
    assert not dialog.codes_page.button.isDefault()

    actions: list[str] = []
    dialog.submit_button.clicked.disconnect()
    dialog.submit_button.clicked.connect(lambda: actions.append("password-reset"))
    dialog.recovery_submit.clicked.disconnect()
    dialog.recovery_submit.clicked.connect(lambda: actions.append("recovery"))
    dialog.password_confirmation.setFocus()
    QTest.keyClick(dialog.password_confirmation, Qt.Key.Key_Return)

    assert actions == ["password-reset"]
    assert dialog.stack.currentWidget() is dialog.password_page
    dialog.close()


def test_security_settings_offer_fixed_intervals_and_device_comfort_is_platform_gated() -> None:
    _app()
    screen = SettingsScreen()
    screen.set_security_status(15)
    combo = screen.findChild(QComboBox)
    assert [combo.itemData(index) for index in range(combo.count())] == [5, 10, 15, 30, 60]
    text = " ".join(label.text() for label in screen.findChildren(QLabel))
    assert "Die App-Sperre ist keine Verschlüsselung" in text
    for excluded in ("Keychain", "Windows Hello"):
        assert excluded not in text
    assert any(
        button.text() == "Technische Support-Reset-Anfrage erstellen"
        for button in screen.findChildren(QPushButton)
    )
    remember = next(
        checkbox
        for checkbox in screen.findChildren(QCheckBox)
        if checkbox.text() == "Auf diesem Gerät angemeldet bleiben"
    )
    touch_id = next(
        checkbox
        for checkbox in screen.findChildren(QCheckBox)
        if checkbox.text() == "Touch ID zum Entsperren verwenden"
    )
    assert remember.isHidden()
    assert touch_id.isHidden()
    screen.set_device_credential_status(
        supported=True,
        enabled=True,
        local_authentication="available",
        touch_id_preferred=True,
        secret_available=True,
    )
    assert not remember.isHidden()
    assert remember.isChecked()
    assert not touch_id.isHidden()
    assert touch_id.isChecked()


def test_settings_security_is_one_separate_subpage() -> None:
    _app()
    screen = SettingsScreen()
    screen.show_page("security")
    assert screen.current_page == "security"
    assert screen.pages.currentIndex() == 4
    screen.show_overview()
    assert screen.current_page == "overview"


def test_settings_change_persists_trimmed_unicode_display_name(tmp_path: Path) -> None:
    app = _app()
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    runtime.service.enroll_local_account("eine lange sichere Profilpassphrase")
    state = runtime.service.security_store_state()
    shell = _FakeShell()
    coordinator = SecurityUiCoordinator(
        app=app,
        shell=shell,
        service=runtime.service,
        repository=runtime.repository,
        preferences_file=runtime.preferences,
        session=InMemorySession(
            state.user_id,
            state.installation_id,
            runtime.repository.security_epoch(),
        ),
        inactivity_minutes=15,
        display_name=None,
    )
    coordinator.set_display_name("  Łucja 🌿  ")
    assert runtime.preferences.load() == AppPreferences(15, "Łucja 🌿")
    assert shell.display_name == "Łucja 🌿"
    assert shell.settings_screen.display_name_input.text() == "Łucja 🌿"
    coordinator.poll_timer.stop()
    coordinator.wake_monitor.timer.stop()
    shell.close()


def test_touch_id_preference_requires_current_password_confirmation(
    tmp_path: Path, monkeypatch
) -> None:
    app = _app()
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    password = "eine lange sichere Touch-ID-Testpassphrase"
    runtime.service.enroll_local_account(password)
    state = runtime.service.security_store_state()

    class AvailableDeviceCredential:
        supported = True

        @staticmethod
        def status():
            return SimpleNamespace(
                enabled=True,
                secret_available=True,
                local_authentication=LocalAuthenticationAvailability.AVAILABLE,
            )

    class ImmediateOperationDialog:
        def __init__(self, operation, _parent):
            self.operation = operation

        def exec_operation(self):
            return self.operation(), None

    monkeypatch.setattr(
        "src.desktop_app.security_controller.QInputDialog.getText",
        lambda *_args, **_kwargs: (password, True),
    )
    monkeypatch.setattr(
        "src.desktop_app.security_controller._ModalOperationDialog",
        ImmediateOperationDialog,
    )
    shell = _FakeShell()
    coordinator = SecurityUiCoordinator(
        app=app,
        shell=shell,
        service=runtime.service,
        repository=runtime.repository,
        preferences_file=runtime.preferences,
        session=InMemorySession(
            state.user_id,
            state.installation_id,
            runtime.repository.security_epoch(),
        ),
        inactivity_minutes=15,
        display_name=None,
        device_credentials=AvailableDeviceCredential(),
    )

    coordinator.set_touch_id_preference(True)

    assert runtime.preferences.load().touch_id_preferred is True
    coordinator.poll_timer.stop()
    coordinator.wake_monitor.timer.stop()
    shell.close()


class _FakeShell(QMainWindow):
    lock_requested = Signal()
    password_change_requested = Signal()
    recovery_codes_requested = Signal()
    inactivity_minutes_changed = Signal(int)
    display_name_changed = Signal(str)
    restore_handoff_started = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings_screen = SettingsScreen()
        self.unsaved = QLineEdit()
        self.unsaved.setText("ungespeicherte Eingabe")
        container = QWidget()
        self.setCentralWidget(container)
        self.unsaved.setParent(container)
        self._prepared_restore_preview = None
        self._restore_confirmed = False
        self.display_name = None

    def set_display_name(self, display_name: str | None) -> None:
        self.display_name = display_name
        self.settings_screen.set_display_name(display_name)


def test_opaque_lock_hides_shell_and_restores_unsaved_memory_state(
    tmp_path: Path,
) -> None:
    app = _app()
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    enrolled = runtime.service.enroll_local_account(
        "eine lange sichere Sperrtestpassphrase"
    )
    state = runtime.service.security_store_state()
    shell = _FakeShell()
    shell.settings_screen.restore_preview = object()
    shell.show()
    app.processEvents()
    coordinator = SecurityUiCoordinator(
        app=app,
        shell=shell,
        service=runtime.service,
        repository=runtime.repository,
        preferences_file=runtime.preferences,
        session=InMemorySession(
            state.user_id,
            state.installation_id,
            runtime.repository.security_epoch(),
        ),
        inactivity_minutes=15,
        display_name=None,
    )
    observations = {"saw_hidden": False}

    def unlock_when_visible() -> None:
        dialog = coordinator._lock_dialog
        if dialog is None:
            QTimer.singleShot(20, unlock_when_visible)
            return
        observations["saw_hidden"] = not shell.isVisible()
        dialog.password.setText("eine lange sichere Sperrtestpassphrase")
        dialog.submit_button.click()

    QTimer.singleShot(0, unlock_when_visible)
    coordinator.lock(SessionLockReason.MANUAL)
    assert observations["saw_hidden"]
    assert shell.isVisible()
    assert shell.unsaved.text() == "ungespeicherte Eingabe"
    assert shell.settings_screen.restore_preview is None
    assert not coordinator.session_controller.locked
    shell.close()


def test_external_epoch_change_forces_new_authentication(tmp_path: Path) -> None:
    app = _app()
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    runtime = build_security_runtime(paths)
    old_password = "eine lange sichere Epoch-Testpassphrase"
    new_password = "eine neue lange sichere Epoch-Testpassphrase"
    runtime.service.enroll_local_account(old_password)
    state = runtime.service.security_store_state()
    shell = _FakeShell()
    confirmed_preview = object()
    shell._restore_confirmed = True
    shell.settings_screen.restore_preview = confirmed_preview
    shell.show()
    coordinator = SecurityUiCoordinator(
        app=app,
        shell=shell,
        service=runtime.service,
        repository=runtime.repository,
        preferences_file=runtime.preferences,
        session=InMemorySession(
            state.user_id,
            state.installation_id,
            runtime.repository.security_epoch(),
        ),
        inactivity_minutes=15,
        display_name=None,
    )
    assert runtime.service.change_password(old_password, new_password).status.value == "authenticated"
    observations = {"locked": False}

    def unlock_when_visible() -> None:
        dialog = coordinator._lock_dialog
        if dialog is None:
            QTimer.singleShot(20, unlock_when_visible)
            return
        observations["locked"] = True
        dialog.password.setText(new_password)
        dialog.submit_button.click()

    QTimer.singleShot(0, unlock_when_visible)
    coordinator._poll()
    assert observations["locked"]
    assert coordinator.session_controller.session.security_epoch == runtime.repository.security_epoch()
    assert shell.settings_screen.restore_preview is confirmed_preview
    shell.close()
