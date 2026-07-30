"""Qt adapters for activity, wake and opaque application locking."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, replace
import logging
import time

from PySide6.QtCore import QEvent, QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from src.security.domain import (
    AuthenticationStatus,
    DeviceCredentialAuthenticationStatus,
    PasswordPolicyError,
    SecurityStoreError,
)
from src.security.session import (
    InMemorySession,
    SecuritySessionController,
    SessionActivityKind,
    SessionLockReason,
    WakeObservation,
)
from src.security.startup import (
    SecurityStartState,
    SecurityStartupDecision,
    SecurityStartupResolver,
)
from src.core.app_preferences import AppPreferences, normalize_display_name

from .security_ui import (
    AuthenticationDialog,
    PasswordChangeDialog,
    RecoveryCodesConfirmationDialog,
    SecurityOperationWorker,
)
from .motion import MotionDialog
from .support_reset import SupportResetDialog


_SECURITY_LOG = logging.getLogger("jenaplan.security")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationActivityFilter(QObject):
    """Translate only real user input into the central session activity port."""

    def __init__(self, callback) -> None:
        super().__init__()
        self.callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        mapping = {
            QEvent.Type.KeyPress: SessionActivityKind.KEYBOARD,
            QEvent.Type.MouseButtonPress: SessionActivityKind.MOUSE,
            QEvent.Type.MouseMove: SessionActivityKind.MOUSE,
            QEvent.Type.Wheel: SessionActivityKind.MOUSE,
            QEvent.Type.TouchBegin: SessionActivityKind.TOUCH,
            QEvent.Type.WindowActivate: SessionActivityKind.WINDOW_ACTIVATION,
        }
        kind = mapping.get(event.type())
        if kind is not None:
            self.callback(kind)
        return super().eventFilter(watched, event)


class WakeMonitor(QObject):
    """Cross-platform clock adapter; macOS sleep surfaces as a delayed tick."""

    wake_observed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._monotonic = time.monotonic()
        self._utc = _utc_now()
        self.timer = QTimer(self)
        self.timer.setInterval(5_000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    @Slot()
    def _tick(self) -> None:
        monotonic_now = time.monotonic()
        utc_now = _utc_now()
        monotonic_gap = monotonic_now - self._monotonic
        utc_gap = (utc_now - self._utc).total_seconds()
        self._monotonic = monotonic_now
        self._utc = utc_now
        if max(monotonic_gap, utc_gap) >= 20 or abs(monotonic_gap - utc_gap) >= 5:
            self.wake_observed.emit(
                WakeObservation(
                    monotonic_now,
                    utc_now,
                    time_uncertain=(
                        monotonic_gap < 0
                        or utc_gap < 0
                        or abs(monotonic_gap - utc_gap) >= 5
                    ),
                )
            )


class _ModalOperationDialog(MotionDialog):
    def __init__(self, operation, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result_value = None
        self.error_value = None
        self.setWindowTitle("Sicherheitsvorgang")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Der Sicherheitsvorgang wird sicher ausgeführt …"))
        self.thread = QThread(self)
        self.worker = SecurityOperationWorker(operation)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.succeeded.connect(self._succeeded)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._completed)
        self.thread.finished.connect(self.thread.deleteLater)

    def exec_operation(self):
        self.thread.start()
        self.exec()
        return self.result_value, self.error_value

    @Slot(object)
    def _succeeded(self, value: object) -> None:
        self.result_value = value

    @Slot(object)
    def _failed(self, error: object) -> None:
        self.error_value = error

    @Slot()
    def _completed(self) -> None:
        if self.error_value is None:
            self.accept()
        else:
            super().reject()

    def reject(self) -> None:
        if self.thread.isRunning() and self.error_value is None:
            return
        super().reject()


@dataclass(frozen=True)
class StartupAuthenticationResult:
    session: InMemorySession
    enrollment_display_name: str | None
    enrollment_completed: bool


def should_attempt_startup_device_authentication(
    *, decision: SecurityStartupDecision, touch_id_preferred: bool
) -> bool:
    """Keep Touch ID reachable instead of bypassing its dialog at startup."""
    return (
        decision.state is SecurityStartState.LOGIN_REQUIRED
        and not touch_id_preferred
    )


def run_startup_device_authentication(
    *, service, repository, device_credentials
) -> StartupAuthenticationResult | None:
    result = device_credentials.authenticate()
    if result.status is not DeviceCredentialAuthenticationStatus.AUTHENTICATED:
        return None
    state = service.security_store_state()
    if state.user_id is None or state.installation_id is None:
        raise SecurityStoreError("device_credential_identity_missing")
    return StartupAuthenticationResult(
        InMemorySession(
            state.user_id,
            state.installation_id,
            repository.security_epoch(),
        ),
        None,
        False,
    )


def run_startup_authentication(
    *, service, repository, decision: SecurityStartupDecision, device_credentials=None,
    touch_id_preferred: bool = False,
    support_reset=None,
    support_reset_backup_factory=None,
) -> StartupAuthenticationResult | None:
    dialog = AuthenticationDialog(
        service=service,
        repository=repository,
        decision=decision,
        device_credentials=device_credentials,
        touch_id_preferred=touch_id_preferred,
        support_reset=support_reset,
        support_reset_backup_factory=support_reset_backup_factory,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    if dialog.authenticated_session is None:
        return None
    enrollment_completed = decision.state in (
        SecurityStartState.FIRST_RUN,
        SecurityStartState.LEGACY_ENROLLMENT,
    )
    return StartupAuthenticationResult(
        dialog.authenticated_session,
        dialog.enrollment_display_name,
        enrollment_completed,
    )


class SecurityUiCoordinator(QObject):
    """Own visible lock behavior while shell/widgets keep only view state."""

    def __init__(
        self,
        *,
        app: QApplication,
        shell,
        service,
        repository,
        preferences_file,
        session: InMemorySession,
        inactivity_minutes: int,
        display_name: str | None,
        device_credentials=None,
        touch_id_preferred: bool = False,
        support_reset=None,
        support_reset_backup_factory=None,
    ) -> None:
        super().__init__(shell)
        self.app = app
        self.shell = shell
        self.service = service
        self.repository = repository
        self.preferences_file = preferences_file
        self.device_credentials = device_credentials
        self.touch_id_preferred = touch_id_preferred
        self.support_reset = support_reset
        self.support_reset_backup_factory = support_reset_backup_factory
        self._support_reset_committed = False
        self.session_controller = SecuritySessionController(
            session,
            inactivity_minutes=inactivity_minutes,
            monotonic_now=time.monotonic(),
            utc_now=_utc_now(),
        )
        self._hidden_windows: list[QWidget] = []
        self._lock_dialog: AuthenticationDialog | None = None
        self.activity_filter = ApplicationActivityFilter(self._activity)
        app.installEventFilter(self.activity_filter)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1_000)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start()
        self.wake_monitor = WakeMonitor(self)
        self.wake_monitor.wake_observed.connect(self._wake)
        shell.lock_requested.connect(
            lambda: self.lock(SessionLockReason.MANUAL)
        )
        shell.password_change_requested.connect(self.change_password)
        shell.recovery_codes_requested.connect(self.regenerate_recovery_codes)
        shell.inactivity_minutes_changed.connect(self.set_inactivity_minutes)
        shell.display_name_changed.connect(self.set_display_name)
        if hasattr(shell, "device_credential_enable_requested"):
            shell.device_credential_enable_requested.connect(self.enable_device_credential)
        if hasattr(shell, "device_credential_disable_requested"):
            shell.device_credential_disable_requested.connect(self.disable_device_credential)
        if hasattr(shell, "touch_id_preference_changed"):
            shell.touch_id_preference_changed.connect(self.set_touch_id_preference)
        if hasattr(shell, "support_reset_requested"):
            shell.support_reset_requested.connect(self.open_support_reset)
        shell.restore_handoff_started.connect(self._restore_handoff_started)
        shell.set_display_name(display_name)
        shell.settings_screen.set_security_status(inactivity_minutes)
        self._refresh_device_credential_status()

    def _activity(self, kind: SessionActivityKind) -> None:
        self.session_controller.activity(
            kind, monotonic_now=time.monotonic(), utc_now=_utc_now()
        )

    @Slot()
    def _poll(self) -> None:
        if self._support_reset_committed:
            return
        session = self.session_controller.session
        if session is not None:
            try:
                epoch_changed = self.repository.security_epoch() != session.security_epoch
            except Exception:
                epoch_changed = True
            if epoch_changed:
                self.lock(SessionLockReason.EPOCH_CHANGED)
                return
        reason = self.session_controller.poll(
            monotonic_now=time.monotonic(), utc_now=_utc_now()
        )
        if reason is SessionLockReason.INACTIVITY:
            self.lock(reason)

    @Slot(object)
    def _wake(self, observation: WakeObservation) -> None:
        reason = self.session_controller.observe_wake(observation)
        if reason is SessionLockReason.WAKE:
            self.lock(reason)

    def lock(self, reason: SessionLockReason) -> None:
        if self._lock_dialog is not None or self._support_reset_committed:
            return
        self.session_controller.lock(reason)
        event_code = {
            SessionLockReason.MANUAL: "lock_manual",
            SessionLockReason.INACTIVITY: "lock_inactivity",
            SessionLockReason.WAKE: "lock_wake",
        }.get(reason)
        if event_code is not None:
            _SECURITY_LOG.info(event_code)
        if (
            not self.shell._restore_confirmed
            and self.shell.settings_screen.restore_preview is not None
        ):
            self.shell._prepared_restore_preview = None
            self.shell.settings_screen.clear_restore_preview()
        self._hidden_windows = [
            widget
            for widget in self.app.topLevelWidgets()
            if widget.isVisible()
        ]
        for widget in self._hidden_windows:
            widget.hide()
        security_state = self.service.security_store_state()
        resolved = SecurityStartupResolver().resolve(
            security_state, legacy_installation_present=False
        )
        decision = (
            SecurityStartupDecision(SecurityStartState.LOCKED, "SEC-LOCKED")
            if resolved.state is SecurityStartState.LOGIN_REQUIRED
            else resolved
        )
        dialog = AuthenticationDialog(
            service=self.service,
            repository=self.repository,
            decision=decision,
            device_credentials=self.device_credentials,
            touch_id_preferred=self.touch_id_preferred,
            allow_cancel=False,
        )
        self._lock_dialog = dialog
        result = dialog.exec()
        self._lock_dialog = None
        if result != QDialog.DialogCode.Accepted or dialog.authenticated_session is None:
            self.app.quit()
            return
        self.session_controller.unlock(
            dialog.authenticated_session,
            monotonic_now=time.monotonic(),
            utc_now=_utc_now(),
        )
        for widget in self._hidden_windows:
            if widget is not None:
                widget.show()
        if not self.shell._restore_confirmed:
            self.shell._prepared_restore_preview = None
            self.shell.settings_screen.clear_restore_preview()
        self._hidden_windows = []

    @Slot()
    def _restore_handoff_started(self) -> None:
        """Let confirmed restore shutdown finish even behind the lock."""
        self.poll_timer.stop()
        self.wake_monitor.timer.stop()
        self._hidden_windows = []
        if self._lock_dialog is not None:
            self._lock_dialog.allow_cancel = True
            self._lock_dialog.reject()

    @Slot(int)
    def set_inactivity_minutes(self, minutes: int) -> None:
        previous = self.session_controller.inactivity_minutes
        try:
            current = self.preferences_file.load()
            preferences = replace(current, inactivity_minutes=minutes)
            self.preferences_file.save(preferences)
            self.session_controller.set_inactivity_minutes(minutes)
        except Exception:
            self.shell.settings_screen.set_security_status(previous)
            self.shell.settings_screen.show_security_message(
                "Die Sperrzeit konnte nicht gespeichert werden.", tone="error"
            )
            return
        self.shell.settings_screen.set_security_status(minutes)
        self.shell.settings_screen.show_security_message(
            f"Die App sperrt nach {minutes} Minuten Inaktivität."
        )

    @Slot(str)
    def set_display_name(self, value: str) -> None:
        try:
            display_name = normalize_display_name(value)
            current = self.preferences_file.load()
            self.preferences_file.save(replace(current, display_name=display_name))
        except (OSError, ValueError, RuntimeError):
            self.shell.settings_screen.show_profile_message(
                "Die persönliche Begrüßung konnte nicht gespeichert werden.",
                tone="error",
            )
            return
        self.shell.set_display_name(display_name)
        self.shell.settings_screen.show_profile_message(
            "Die persönliche Begrüßung wurde gespeichert."
        )

    @Slot()
    def change_password(self) -> None:
        dialog = PasswordChangeDialog(self.shell)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        current = dialog.current.text()
        replacement = dialog.replacement.text()
        operation = _ModalOperationDialog(
            lambda: self.service.change_password(current, replacement), self.shell
        )
        result, error = operation.exec_operation()
        current = replacement = ""
        dialog.current.clear()
        dialog.replacement.clear()
        dialog.confirmation.clear()
        if error is not None or result is None:
            message = (
                "Das neue Passwort erfüllt die Anforderungen noch nicht."
                if isinstance(error, PasswordPolicyError)
                else "Das Passwort konnte nicht geändert werden."
            )
            self.shell.settings_screen.show_security_message(message, tone="error")
            return
        if result.status is not AuthenticationStatus.AUTHENTICATED:
            self.shell.settings_screen.show_security_message(
                "Das aktuelle Passwort konnte nicht bestätigt werden.", tone="error"
            )
            return
        state = self.service.security_store_state()
        if state.user_id is None or state.installation_id is None:
            self.shell.settings_screen.show_security_message(
                "Die neue Sitzung konnte nicht sicher gebunden werden.", tone="error"
            )
            return
        session = InMemorySession(
            state.user_id,
            state.installation_id,
            self.repository.security_epoch(),
        )
        self.session_controller.unlock(
            session, monotonic_now=time.monotonic(), utc_now=_utc_now()
        )
        _SECURITY_LOG.info("password_changed")
        self.shell.settings_screen.show_security_message("Das Passwort wurde geändert.")
        if self.device_credentials is not None:
            self._refresh_device_credential_status()

    @Slot()
    def regenerate_recovery_codes(self) -> None:
        operation = _ModalOperationDialog(
            self.service.prepare_recovery_code_regeneration, self.shell
        )
        prepared, error = operation.exec_operation()
        if error is not None or prepared is None:
            self.shell.settings_screen.show_security_message(
                "Neue Recovery-Codes konnten nicht vorbereitet werden.", tone="error"
            )
            return
        dialog = RecoveryCodesConfirmationDialog(prepared.recovery_codes, self.shell)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        confirm = _ModalOperationDialog(
            lambda: self.service.confirm_recovery_code_regeneration(
                prepared.recovery_set_id
            ),
            self.shell,
        )
        confirmed, error = confirm.exec_operation()
        if error is not None or confirmed is not True:
            self.shell.settings_screen.show_security_message(
                "Die neuen Recovery-Codes wurden nicht aktiviert.", tone="error"
            )
            return
        self.shell.settings_screen.show_security_message(
            "Die neuen Recovery-Codes sind aktiv."
        )

    @Slot()
    def open_support_reset(self) -> None:
        if self.support_reset is None or self.support_reset_backup_factory is None:
            self.shell.settings_screen.show_security_message(
                "Die weitere Wiederherstellung ist in dieser App-Version nicht verfügbar.",
                tone="error",
            )
            return
        if self.shell.backup_restore_operations.is_busy:
            self.shell.settings_screen.show_security_message(
                "Schließe zuerst den laufenden Sicherungs- oder Wiederherstellungsvorgang ab.",
                tone="error",
            )
            return
        dialog = SupportResetDialog(
            service=self.support_reset,
            backup_factory=self.support_reset_backup_factory,
            parent=self.shell,
        )
        dialog.reset_completed.connect(self._support_reset_completed)
        dialog.exec()

    @Slot(object)
    def _support_reset_completed(self, _result: object) -> None:
        """Remove every visible product surface immediately after the commit."""
        self._support_reset_committed = True
        self.poll_timer.stop()
        self.wake_monitor.timer.stop()
        self.session_controller.lock(SessionLockReason.EPOCH_CHANGED)
        if self.device_credentials is not None:
            try:
                self.device_credentials.status()
            except Exception:
                pass
        try:
            current = self.preferences_file.load()
            if current.touch_id_preferred:
                self.preferences_file.save(replace(current, touch_id_preferred=False))
        except Exception:
            pass
        for widget in self.app.topLevelWidgets():
            widget.hide()
        self.app.quit()

    @Slot()
    def enable_device_credential(self) -> None:
        if self.device_credentials is None or not self.device_credentials.supported:
            self.shell.settings_screen.show_security_message(
                "Die gespeicherte Anmeldung wird auf diesem Gerät nicht unterstützt.",
                tone="error",
            )
            return
        current_password, accepted = QInputDialog.getText(
            self.shell,
            "Gespeicherte Anmeldung aktivieren",
            "Aktuelles Passwort",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not current_password:
            return
        operation = _ModalOperationDialog(
            lambda: self._enable_device_after_password(current_password), self.shell
        )
        result, error = operation.exec_operation()
        current_password = ""
        if error is not None or result is not True:
            self.shell.settings_screen.show_security_message(
                "Die gespeicherte Anmeldung konnte nicht aktiviert werden.", tone="error"
            )
            self._refresh_device_credential_status()
            return
        _SECURITY_LOG.info("device_credential_enabled")
        self._refresh_device_credential_status()
        self.shell.settings_screen.show_security_message(
            "Die gespeicherte Anmeldung ist auf diesem Gerät aktiv."
        )

    def _enable_device_after_password(self, password: str) -> bool:
        authenticated = self.service.authenticate_password(password)
        if authenticated.status is not AuthenticationStatus.AUTHENTICATED:
            return False
        self.device_credentials.register()
        return True

    @Slot()
    def disable_device_credential(self) -> None:
        if self.device_credentials is None:
            return
        operation = _ModalOperationDialog(self.device_credentials.disable, self.shell)
        _result, error = operation.exec_operation()
        if error is not None:
            self.shell.settings_screen.show_security_message(
                "Die gespeicherte Anmeldung konnte nicht widerrufen werden.", tone="error"
            )
            return
        _SECURITY_LOG.info("device_credential_disabled")
        self._refresh_device_credential_status()
        self.shell.settings_screen.show_security_message(
            "Die gespeicherte Anmeldung wurde widerrufen."
        )

    def _refresh_device_credential_status(self) -> None:
        if not hasattr(self.shell.settings_screen, "set_device_credential_status"):
            return
        if self.device_credentials is None:
            self.shell.settings_screen.set_device_credential_status(
                supported=False,
                enabled=False,
                local_authentication="unsupported",
                touch_id_preferred=False,
                secret_available=False,
            )
            return
        status = self.device_credentials.status()
        if not status.enabled and self.touch_id_preferred:
            try:
                current = self.preferences_file.load()
                self.preferences_file.save(replace(current, touch_id_preferred=False))
            except Exception:
                pass
            self.touch_id_preferred = False
        self.shell.settings_screen.set_device_credential_status(
            supported=self.device_credentials.supported,
            enabled=status.enabled,
            local_authentication=status.local_authentication.value,
            touch_id_preferred=self.touch_id_preferred,
            secret_available=status.secret_available,
        )

    @Slot(bool)
    def set_touch_id_preference(self, enabled: bool) -> None:
        try:
            status = self.device_credentials.status() if self.device_credentials else None
            if enabled and (
                status is None
                or not status.enabled
                or status.local_authentication.value != "available"
            ):
                raise ValueError("touch_id_not_available")
            if enabled:
                current_password, accepted = QInputDialog.getText(
                    self.shell,
                    "Touch ID aktivieren",
                    "Aktuelles Passwort",
                    QLineEdit.EchoMode.Password,
                )
                if not accepted or not current_password:
                    self._refresh_device_credential_status()
                    return
                operation = _ModalOperationDialog(
                    lambda: self.service.authenticate_password(current_password),
                    self.shell,
                )
                authentication, error = operation.exec_operation()
                current_password = ""
                if (
                    error is not None
                    or authentication is None
                    or authentication.status is not AuthenticationStatus.AUTHENTICATED
                ):
                    raise ValueError("touch_id_password_not_confirmed")
            current = self.preferences_file.load()
            self.preferences_file.save(replace(current, touch_id_preferred=enabled))
            self.touch_id_preferred = enabled
        except Exception:
            self.shell.settings_screen.show_security_message(
                "Die Touch-ID-Einstellung konnte nicht gespeichert werden.", tone="error"
            )
        self._refresh_device_credential_status()
