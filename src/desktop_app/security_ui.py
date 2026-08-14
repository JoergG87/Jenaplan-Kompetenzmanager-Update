"""Minimal opaque Qt views for enrollment, login and recovery."""

from __future__ import annotations

from collections.abc import Callable
import logging

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.security.application import EnrollmentResult, RecoveryPreparation
from src.security.domain import (
    AuthenticationStatus,
    DeviceCredentialAuthenticationStatus,
    LocalAuthenticationAvailability,
    LocalAuthenticationResult,
    PasswordPolicyError,
    RecoveryStatus,
)
from src.security.session import InMemorySession
from src.security.startup import SecurityStartState, SecurityStartupDecision

from .components import AppCard, InlineMessage, configure_button
from .motion import MotionDialog
from .support_reset import SupportResetDialog
from .theme import set_label_style
from src.core.app_preferences import DISPLAY_NAME_MAX_LENGTH, normalize_display_name


_SECURITY_LOG = logging.getLogger("jenaplan.security")
APP_LOCK_NOTICE = (
    "Das App-Passwort schützt den Zugang. Fachdaten, verwaltete Dokumente und "
    "Backups werden zusätzlich verschlüsselt gespeichert."
)


def _configure_password_input(field: QLineEdit, *, description: str) -> None:
    """Apply Qt's public sensitive-input contract without a private Cocoa bridge."""
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setInputMethodHints(
        Qt.InputMethodHint.ImhHiddenText
        | Qt.InputMethodHint.ImhSensitiveData
        | Qt.InputMethodHint.ImhNoAutoUppercase
        | Qt.InputMethodHint.ImhNoPredictiveText
    )
    field.setAccessibleDescription(description)


def _touch_id_unavailable_text(status) -> str:
    if not status.enabled:
        return "Touch ID steht nach der ersten Anmeldung mit Passwort zur Verfügung."
    if not status.secret_available:
        return "Touch ID ist derzeit nicht verfügbar. Verwende dein Passwort."
    availability = status.local_authentication
    if availability is LocalAuthenticationAvailability.NOT_ENROLLED:
        return "Touch ID ist auf diesem Mac noch nicht eingerichtet. Verwende dein Passwort."
    if availability is LocalAuthenticationAvailability.LOCKED_OUT:
        return "Touch ID ist vorübergehend gesperrt. Verwende dein Passwort."
    if availability in {
        LocalAuthenticationAvailability.NOT_AVAILABLE,
        LocalAuthenticationAvailability.UNSUPPORTED,
    }:
        return "Touch ID ist auf diesem Mac nicht verfügbar. Verwende dein Passwort."
    if availability is not LocalAuthenticationAvailability.AVAILABLE:
        return "Touch ID ist gerade nicht verfügbar. Verwende dein Passwort."
    return ""


class SecurityOperationWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation

    @Slot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self._operation())
        except Exception as error:  # outward UI maps only structured classes
            self.failed.emit(error)
        finally:
            self._operation = lambda: None
            self.finished.emit()


class RecoveryCodesPage(QWidget):
    confirmed = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Recovery-Codes sichern")
        set_label_style(title, "screen_title")
        layout.addWidget(title)
        note = QLabel(
            "Diese zehn Codes werden nur jetzt vollständig angezeigt. "
            "Bewahre sie getrennt und sicher auf."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.codes = QPlainTextEdit()
        self.codes.setReadOnly(True)
        self.codes.setObjectName("RecoveryCodesDisplay")
        self.codes.setAccessibleName("Zehn einmalig angezeigte Recovery-Codes")
        font = QFont("Menlo")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(14)
        self.codes.setFont(font)
        self.codes.setMinimumHeight(300)
        layout.addWidget(self.codes)
        self.confirmation = QCheckBox(
            "Ich habe alle zehn Recovery-Codes sicher aufbewahrt."
        )
        self.confirmation.toggled.connect(self._update)
        layout.addWidget(self.confirmation)
        self.button = QPushButton("Konto aktivieren")
        self.button.setDefault(True)
        self.button.setEnabled(False)
        configure_button(self.button, "primary", "Recovery-Codes bestätigen")
        self.button.clicked.connect(self.confirmed)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignRight)

    def set_codes(self, codes: tuple[str, ...], *, reset: bool = False) -> None:
        self.codes.setPlainText("\n".join(codes))
        self.confirmation.setChecked(False)
        self.button.setText("Sicher bestätigen" if reset else "Konto aktivieren")

    def _update(self, checked: bool) -> None:
        self.button.setEnabled(checked)


class AuthenticationDialog(MotionDialog):
    """Single-purpose auth gate; it never imports or exposes product adapters."""

    def __init__(
        self,
        *,
        service,
        repository,
        decision: SecurityStartupDecision,
        device_credentials=None,
        touch_id_preferred: bool = False,
        support_reset=None,
        support_reset_backup_factory=None,
        parent: QWidget | None = None,
        allow_cancel: bool = True,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.repository = repository
        self.decision = decision
        self.device_credentials = device_credentials
        self.touch_id_preferred = touch_id_preferred
        self.support_reset = support_reset
        self.support_reset_backup_factory = support_reset_backup_factory
        self.allow_cancel = allow_cancel
        self.authenticated_session: InMemorySession | None = None
        self.enrollment_display_name: str | None = None
        self._pending_result: EnrollmentResult | RecoveryPreparation | None = None
        self._thread: QThread | None = None
        self._worker: SecurityOperationWorker | None = None
        self._operation_busy = False
        self._accept_when_finished = False
        self.setObjectName("AuthenticationDialog")
        self.setWindowTitle("Jenaplan Kompetenzmanager")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QDialog#AuthenticationDialog { background: #F3F7FA; }")
        self.setMinimumSize(720, 650)
        self.resize(860, 720)
        self._build()
        self._show_initial_state()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(72, 48, 72, 48)
        brand = QLabel("Jenaplan Kompetenzmanager")
        set_label_style(brand, "screen_title")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(brand)
        self.stack = QStackedWidget()
        self.password_page = self._password_page()
        self.recovery_page = self._recovery_page()
        self.codes_page = RecoveryCodesPage()
        self.codes_page.confirmed.connect(self._confirm_codes)
        self.error_page = self._error_page()
        for page in (
            self.password_page,
            self.recovery_page,
            self.codes_page,
            self.error_page,
        ):
            self.stack.addWidget(page)
        outer.addWidget(self.stack, 1)
        notice = QLabel(APP_LOCK_NOTICE)
        notice.setWordWrap(True)
        notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(notice, "small")
        outer.addWidget(notice)

    def _password_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = AppCard("default")
        form = QVBoxLayout(card)
        self.heading = QLabel("")
        set_label_style(self.heading, "section_title")
        form.addWidget(self.heading)
        self.explanation = QLabel("")
        self.explanation.setWordWrap(True)
        form.addWidget(self.explanation)
        self.display_name_label = QLabel("Wie dürfen wir dich begrüßen?")
        self.display_name_label.setVisible(False)
        form.addWidget(self.display_name_label)
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("Zum Beispiel Laura")
        self.display_name.setAccessibleName("Optionaler Anzeigename für die persönliche Begrüßung")
        self.display_name.setMaxLength(DISPLAY_NAME_MAX_LENGTH)
        self.display_name.setVisible(False)
        form.addWidget(self.display_name)
        self.display_name_hint = QLabel("Optional · Du kannst das später in den Einstellungen ändern.")
        self.display_name_hint.setVisible(False)
        set_label_style(self.display_name_hint, "small")
        form.addWidget(self.display_name_hint)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Passwort")
        self.password.setAccessibleName("Passwort")
        _configure_password_input(
            self.password,
            description="Lokales Passwort; die Eingabe wird nicht gespeichert oder vorhergesagt.",
        )
        form.addWidget(self.password)
        self.password_confirmation = QLineEdit()
        self.password_confirmation.setPlaceholderText("Passwort bestätigen")
        self.password_confirmation.setAccessibleName("Passwort bestätigen")
        _configure_password_input(
            self.password_confirmation,
            description="Bestätigung des neuen lokalen Passworts; die Eingabe wird nicht gespeichert oder vorhergesagt.",
        )
        form.addWidget(self.password_confirmation)
        self.show_password = QCheckBox("Passwort anzeigen")
        self.show_password.toggled.connect(self._toggle_password_visibility)
        form.addWidget(self.show_password)
        self.remember_device = QCheckBox("Auf diesem Gerät angemeldet bleiben")
        self.remember_device.setAccessibleName("Auf diesem Gerät angemeldet bleiben")
        self.remember_device.setVisible(False)
        form.addWidget(self.remember_device)
        self.remember_device_hint = QLabel(
            "Die App wird weiterhin nach Inaktivität oder Ruhezustand gesperrt."
        )
        self.remember_device_hint.setWordWrap(True)
        self.remember_device_hint.setVisible(False)
        set_label_style(self.remember_device_hint, "small")
        form.addWidget(self.remember_device_hint)
        self.message = InlineMessage()
        form.addWidget(self.message)
        actions = QHBoxLayout()
        self.recovery_button = QPushButton("Recovery-Code verwenden")
        self.recovery_button.setAutoDefault(False)
        configure_button(self.recovery_button, "quiet", "Recovery öffnen")
        self.recovery_button.clicked.connect(self._open_recovery)
        actions.addWidget(self.recovery_button)
        self.support_reset_button = QPushButton("Weitere Wiederherstellungsmöglichkeiten")
        self.support_reset_button.setAutoDefault(False)
        configure_button(
            self.support_reset_button,
            "quiet",
            "Weitere Wiederherstellungsmöglichkeiten öffnen",
        )
        self.support_reset_button.clicked.connect(self._open_support_reset)
        self.support_reset_button.setVisible(False)
        self.touch_id_button = QPushButton("Mit Touch ID entsperren")
        self.touch_id_button.setAutoDefault(False)
        configure_button(self.touch_id_button, "secondary", "Mit Touch ID entsperren")
        self.touch_id_button.clicked.connect(self._submit_touch_id)
        self.touch_id_button.setVisible(False)
        actions.addWidget(self.touch_id_button)
        self.touch_id_notice = QLabel()
        self.touch_id_notice.setWordWrap(True)
        set_label_style(self.touch_id_notice, "small")
        self.touch_id_notice.setVisible(False)
        form.addWidget(self.touch_id_notice)
        actions.addStretch(1)
        self.submit_button = QPushButton("Weiter")
        self.submit_button.setDefault(True)
        configure_button(self.submit_button, "primary", "Authentifizierung fortsetzen")
        self.submit_button.clicked.connect(self._submit_password)
        actions.addWidget(self.submit_button)
        form.addLayout(actions)
        form.addWidget(
            self.support_reset_button, 0, Qt.AlignmentFlag.AlignLeft
        )
        layout.addStretch(1)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _recovery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = AppCard("default")
        form = QVBoxLayout(card)
        title = QLabel("Zugang wiederherstellen")
        set_label_style(title, "section_title")
        form.addWidget(title)
        note = QLabel("Gib einen deiner noch nicht verwendeten Recovery-Codes ein.")
        note.setWordWrap(True)
        form.addWidget(note)
        self.recovery_code = QLineEdit()
        self.recovery_code.setPlaceholderText("JKM1-…")
        self.recovery_code.setAccessibleName("Recovery-Code")
        form.addWidget(self.recovery_code)
        self.recovery_message = InlineMessage()
        form.addWidget(self.recovery_message)
        actions = QHBoxLayout()
        back = QPushButton("Zurück")
        back.setAutoDefault(False)
        configure_button(back, "quiet", "Zurück zum Login")
        back.clicked.connect(self._return_to_password)
        actions.addWidget(back)
        actions.addStretch(1)
        self.recovery_submit = QPushButton("Code prüfen")
        self.recovery_submit.setDefault(True)
        configure_button(self.recovery_submit, "primary", "Recovery-Code prüfen")
        self.recovery_submit.clicked.connect(self._submit_recovery)
        actions.addWidget(self.recovery_submit)
        form.addLayout(actions)
        layout.addStretch(1)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _error_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.error_heading = QLabel("Sicherer Start nicht möglich")
        set_label_style(self.error_heading, "screen_title")
        layout.addStretch(1)
        layout.addWidget(self.error_heading)
        self.error_text = QLabel("")
        self.error_text.setWordWrap(True)
        layout.addWidget(self.error_text)
        layout.addStretch(1)
        return page

    def _show_initial_state(self) -> None:
        state = self.decision.state
        self.touch_id_button.setVisible(False)
        self.touch_id_notice.setVisible(False)
        if state in (SecurityStartState.FIRST_RUN, SecurityStartState.LEGACY_ENROLLMENT):
            self._set_password_semantics(is_new_password=True)
            self.heading.setText("Lokales Konto einrichten")
            self.explanation.setText(
                "Lege ein Passwort mit mindestens 15 Zeichen fest. "
                "Danach erhältst du zehn Recovery-Codes."
            )
            self.submit_button.setText("Recovery-Codes erzeugen")
            self.password_confirmation.setVisible(True)
            self.recovery_button.setVisible(False)
            self.display_name_label.setVisible(True)
            self.display_name.setVisible(True)
            self.display_name_hint.setVisible(True)
        elif state is SecurityStartState.PASSWORD_RESET_PENDING:
            self._show_password_reset()
        elif state in (
            SecurityStartState.LOGIN_REQUIRED,
            SecurityStartState.LOCKED,
            SecurityStartState.RECOVERY_AVAILABLE,
        ):
            self._set_password_semantics(is_new_password=False)
            self.heading.setText("App entsperren")
            self.explanation.setText("Gib dein lokales Passwort ein.")
            self.submit_button.setText("Entsperren")
            self.password_confirmation.setVisible(False)
            self.recovery_button.setVisible(True)
            self.support_reset_button.setVisible(
                state is SecurityStartState.LOGIN_REQUIRED
                and self.support_reset is not None
                and self.support_reset_backup_factory is not None
            )
            can_remember = (
                state is SecurityStartState.LOGIN_REQUIRED
                and self.device_credentials is not None
                and self.device_credentials.supported
            )
            self.remember_device.setVisible(can_remember)
            self.remember_device_hint.setVisible(can_remember)
            if self.device_credentials is not None:
                status = self.device_credentials.status()
                touch_id_available = (
                    status.enabled
                    and status.secret_available
                    and self.touch_id_preferred
                    and status.local_authentication
                    is LocalAuthenticationAvailability.AVAILABLE
                )
                self.touch_id_button.setVisible(touch_id_available)
                notice = _touch_id_unavailable_text(status)
                if notice:
                    self.touch_id_notice.setText(notice)
                    self.touch_id_notice.setVisible(True)
        else:
            self.error_text.setText(
                "Die Sicherheitsdaten konnten nicht eindeutig geprüft werden. "
                "Die fachliche App bleibt geschlossen. Wende dich mit der "
                f"technischen Kennung {self.decision.technical_code} an den Support."
            )
            self.stack.setCurrentWidget(self.error_page)
        if self.stack.currentWidget() is self.password_page:
            self.recovery_submit.setDefault(False)
            self.codes_page.button.setDefault(False)
            self.submit_button.setDefault(True)
        else:
            self.submit_button.setDefault(False)
            self.recovery_submit.setDefault(False)
            self.codes_page.button.setDefault(False)

    def _show_password_reset(self) -> None:
        self._set_password_semantics(is_new_password=True)
        self.heading.setText("Neues Passwort festlegen")
        self.explanation.setText(
            "Der Zugang wurde wiederhergestellt. Lege jetzt ein neues Passwort fest."
        )
        self.submit_button.setText("Neue Recovery-Codes erzeugen")
        self.password_confirmation.setVisible(True)
        self.recovery_button.setVisible(False)
        self.password.clear()
        self.password_confirmation.clear()
        self.stack.setCurrentWidget(self.password_page)
        self.recovery_submit.setDefault(False)
        self.codes_page.button.setDefault(False)
        self.submit_button.setDefault(True)

    def _submit_password(self) -> None:
        if self._operation_busy:
            return
        password = self.password.text()
        state = self.decision.state
        if self.password_confirmation.isVisible() and password != self.password_confirmation.text():
            self.message.set_message("Die Passwörter stimmen nicht überein.", tone="error")
            return
        if state in (SecurityStartState.FIRST_RUN, SecurityStartState.LEGACY_ENROLLMENT):
            operation = lambda: self.service.prepare_local_account_enrollment(password)
            handler = self._enrollment_prepared
        elif state is SecurityStartState.PASSWORD_RESET_PENDING:
            operation = lambda: self.service.prepare_recovery_password_reset(password)
            handler = self._reset_prepared
        else:
            remember = self.remember_device.isVisible() and self.remember_device.isChecked()
            operation = lambda: self._authenticate_password(password, remember)
            handler = self._authentication_finished
        self._run_operation(operation, handler, self._password_operation_failed)

    def _authenticate_password(self, password: str, remember: bool):
        result = self.service.authenticate_password(password)
        registration_failed = False
        if (
            remember
            and result.status is AuthenticationStatus.AUTHENTICATED
            and self.device_credentials is not None
        ):
            try:
                self.device_credentials.register()
                _SECURITY_LOG.info("device_credential_enabled")
            except Exception:
                registration_failed = True
                _SECURITY_LOG.info("device_credential_rejected")
        return result, registration_failed

    def _submit_touch_id(self) -> None:
        if self._operation_busy or self.device_credentials is None:
            return
        self._run_operation(
            lambda: self.device_credentials.authenticate(require_local_authentication=True),
            self._touch_id_finished,
            lambda _error: self.message.set_message(
                "Touch ID ist gerade nicht verfügbar. Verwende dein Passwort.", tone="error"
            ),
        )

    def _submit_recovery(self) -> None:
        if self._operation_busy:
            return
        code = self.recovery_code.text()
        _SECURITY_LOG.info("recovery_started")
        self._run_operation(
            lambda: self.service.verify_and_consume_recovery_code(code),
            self._recovery_finished,
            lambda _error: self._generic_recovery_error(),
        )

    def _run_operation(
        self,
        operation: Callable[[], object],
        success: Callable[[object], None],
        failure: Callable[[object], None],
    ) -> None:
        self._operation_busy = True
        self.submit_button.setDisabled(True)
        self.recovery_submit.setDisabled(True)
        thread = QThread(self)
        worker = SecurityOperationWorker(operation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._operation_ended)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _operation_ended(self) -> None:
        self._operation_busy = False
        self.submit_button.setDisabled(False)
        self.recovery_submit.setDisabled(False)
        self.password.clear()
        self.password_confirmation.clear()
        self.recovery_code.clear()
        self._thread = None
        self._worker = None
        if self._accept_when_finished:
            self._accept_when_finished = False
            self.accept()

    def _enrollment_prepared(self, result: EnrollmentResult) -> None:
        self.enrollment_display_name = normalize_display_name(self.display_name.text())
        self._pending_result = result
        self.codes_page.set_codes(result.recovery_codes)
        self.stack.setCurrentWidget(self.codes_page)
        self.submit_button.setDefault(False)
        self.recovery_submit.setDefault(False)
        self.codes_page.button.setDefault(True)

    def _reset_prepared(self, result: RecoveryPreparation) -> None:
        self._pending_result = result
        self.codes_page.set_codes(result.recovery_codes, reset=True)
        self.stack.setCurrentWidget(self.codes_page)
        self.submit_button.setDefault(False)
        self.recovery_submit.setDefault(False)
        self.codes_page.button.setDefault(True)

    def _confirm_codes(self) -> None:
        if self._operation_busy or self._pending_result is None:
            return
        pending = self._pending_result
        if isinstance(pending, EnrollmentResult):
            operation = lambda: self.service.confirm_local_account_enrollment(
                pending.recovery_set_id
            )
        else:
            operation = lambda: self.service.confirm_recovery_password_reset(
                pending.recovery_set_id
            )
        self._run_operation(operation, self._codes_confirmed, self._password_operation_failed)

    def _codes_confirmed(self, confirmed: object) -> None:
        if confirmed is not True:
            self._password_operation_failed(RuntimeError("confirmation_failed"))
            return
        if isinstance(self._pending_result, RecoveryPreparation):
            _SECURITY_LOG.info("recovery_completed")
        self._accept_current_session()

    def _authentication_finished(self, result) -> None:
        registration_failed = False
        if isinstance(result, tuple):
            result, registration_failed = result
        if result.status is AuthenticationStatus.AUTHENTICATED:
            _SECURITY_LOG.info("login_success")
            if registration_failed:
                self.message.set_message(
                    "Die gespeicherte Anmeldung konnte nicht aktiviert werden. "
                    "Die Anmeldung mit Passwort war erfolgreich.",
                    tone="error",
                )
            self._accept_current_session()
            return
        _SECURITY_LOG.info("login_failed")
        if result.status is AuthenticationStatus.THROTTLED:
            self.message.set_message(
                f"Bitte warte noch {result.retry_after_seconds} Sekunden.", tone="error"
            )
        elif result.status is AuthenticationStatus.PASSWORD_RESET_REQUIRED:
            self.decision = SecurityStartupDecision(
                SecurityStartState.PASSWORD_RESET_PENDING,
                "SEC-PASSWORD_RESET_PENDING",
            )
            self._show_password_reset()
        else:
            self.message.set_message(
                "Das Passwort konnte nicht bestätigt werden.", tone="error"
            )

    def _touch_id_finished(self, result) -> None:
        if result.status is DeviceCredentialAuthenticationStatus.AUTHENTICATED:
            _SECURITY_LOG.info("local_auth_success")
            self._accept_current_session()
            return
        if result.local_authentication_result in {
            LocalAuthenticationResult.USER_CANCEL,
            LocalAuthenticationResult.FALLBACK_REQUESTED,
            LocalAuthenticationResult.SYSTEM_CANCEL,
        }:
            _SECURITY_LOG.info("local_auth_cancelled")
            self.message.set_message("Touch ID wurde beendet. Verwende dein Passwort.")
        else:
            _SECURITY_LOG.info("local_auth_unavailable")
            self.message.set_message(
                "Touch ID ist gerade nicht verfügbar. Verwende dein Passwort.",
                tone="error",
            )
        self.touch_id_button.setVisible(False)
        self.password.setFocus()

    def _recovery_finished(self, result) -> None:
        if result.status is RecoveryStatus.ACCEPTED:
            self.decision = SecurityStartupDecision(
                SecurityStartState.PASSWORD_RESET_PENDING,
                "SEC-PASSWORD_RESET_PENDING",
            )
            self._show_password_reset()
        elif result.status is RecoveryStatus.THROTTLED:
            self.recovery_message.set_message(
                f"Bitte warte noch {result.retry_after_seconds} Sekunden.", tone="error"
            )
        else:
            self._generic_recovery_error()

    def _generic_recovery_error(self) -> None:
        self.recovery_message.set_message(
            "Der Recovery-Code konnte nicht bestätigt werden.", tone="error"
        )

    def _password_operation_failed(self, error: object) -> None:
        if isinstance(error, PasswordPolicyError):
            text = "Das Passwort erfüllt die Anforderungen noch nicht. Verwende mindestens 15 Zeichen."
        else:
            text = "Der Sicherheitsvorgang konnte nicht abgeschlossen werden."
        self.message.set_message(text, tone="error")

    def _accept_current_session(self) -> None:
        state = self.service.security_store_state()
        if state.installation_id is None or state.user_id is None:
            self._password_operation_failed(RuntimeError("identity_missing"))
            return
        self.authenticated_session = InMemorySession(
            user_id=state.user_id,
            installation_id=state.installation_id,
            security_epoch=self.repository.security_epoch(),
        )
        if self._operation_busy:
            self._accept_when_finished = True
        else:
            self.accept()

    def _open_recovery(self) -> None:
        self.message.set_message("")
        self.stack.setCurrentWidget(self.recovery_page)
        self.submit_button.setDefault(False)
        self.codes_page.button.setDefault(False)
        self.recovery_submit.setDefault(True)
        self.recovery_code.setFocus()

    def _open_support_reset(self) -> None:
        if (
            self._operation_busy
            or self.support_reset is None
            or self.support_reset_backup_factory is None
        ):
            return
        dialog = SupportResetDialog(
            service=self.support_reset,
            backup_factory=self.support_reset_backup_factory,
            parent=self,
        )
        dialog.reset_completed.connect(self._support_reset_completed)
        dialog.reset_shutdown_required.connect(
            self._support_reset_shutdown_required
        )
        dialog.exec()

    @Slot(object)
    def _support_reset_shutdown_required(self, _error: object) -> None:
        self.password.clear()
        self.password_confirmation.clear()
        self.recovery_code.clear()
        app = QApplication.instance()
        if app is not None:
            app.quit()
        super().reject()

    @Slot(object)
    def _support_reset_completed(self, _result: object) -> None:
        self.password.clear()
        self.password_confirmation.clear()
        self.recovery_code.clear()
        self.authenticated_session = None
        if self.device_credentials is not None:
            try:
                # Store revocation is authoritative; this performs best-effort
                # cleanup of the now-unusable platform secret.
                self.device_credentials.status()
            except Exception:
                pass
        app = QApplication.instance()
        if app is not None:
            app.quit()
        super().reject()

    def _return_to_password(self) -> None:
        self.stack.setCurrentWidget(self.password_page)
        self.recovery_submit.setDefault(False)
        self.codes_page.button.setDefault(False)
        self.submit_button.setDefault(True)
        self.password.setFocus()

    def _toggle_password_visibility(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password.setEchoMode(mode)
        self.password_confirmation.setEchoMode(mode)

    def _set_password_semantics(self, *, is_new_password: bool) -> None:
        if is_new_password:
            self.password.setAccessibleName("Neues Passwort")
            self.password.setAccessibleDescription(
                "Neues lokales Passwort; die Eingabe wird nicht gespeichert oder vorhergesagt."
            )
            self.password_confirmation.setAccessibleName("Neues Passwort bestätigen")
        else:
            self.password.setAccessibleName("Lokales Passwort")
            self.password.setAccessibleDescription(
                "Lokales Passwort; die Eingabe wird nicht gespeichert oder vorhergesagt."
            )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._operation_busy or not self.allow_cancel:
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self) -> None:
        if not self.allow_cancel:
            return
        super().reject()


class PasswordChangeDialog(MotionDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Passwort ändern")
        layout = QVBoxLayout(self)
        self.current = QLineEdit()
        self.current.setPlaceholderText("Aktuelles Passwort")
        self.current.setAccessibleName("Aktuelles Passwort")
        _configure_password_input(
            self.current,
            description="Aktuelles lokales Passwort; die Eingabe wird nicht gespeichert oder vorhergesagt.",
        )
        self.replacement = QLineEdit()
        self.replacement.setPlaceholderText("Neues Passwort")
        self.replacement.setAccessibleName("Neues Passwort")
        _configure_password_input(
            self.replacement,
            description="Neues lokales Passwort; die Eingabe wird nicht gespeichert oder vorhergesagt.",
        )
        self.confirmation = QLineEdit()
        self.confirmation.setPlaceholderText("Neues Passwort bestätigen")
        self.confirmation.setAccessibleName("Neues Passwort bestätigen")
        _configure_password_input(
            self.confirmation,
            description="Bestätigung des neuen lokalen Passworts; die Eingabe wird nicht gespeichert oder vorhergesagt.",
        )
        for field in (self.current, self.replacement, self.confirmation):
            layout.addWidget(field)
        show = QCheckBox("Passwörter anzeigen")
        show.toggled.connect(self._toggle_visibility)
        layout.addWidget(show)
        self.message = InlineMessage()
        layout.addWidget(self.message)
        button = QPushButton("Passwort ändern")
        button.setDefault(True)
        configure_button(button, "primary", "Passwort ändern")
        button.clicked.connect(self._validate)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignRight)

    def _toggle_visibility(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        for field in (self.current, self.replacement, self.confirmation):
            field.setEchoMode(mode)

    def _validate(self) -> None:
        if self.replacement.text() != self.confirmation.text():
            self.message.set_message("Die Passwörter stimmen nicht überein.", tone="error")
            return
        self.accept()


class RecoveryCodesConfirmationDialog(MotionDialog):
    def __init__(self, codes: tuple[str, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recovery-Codes sichern")
        self.setMinimumSize(650, 620)
        layout = QVBoxLayout(self)
        page = RecoveryCodesPage()
        page.button.setText("Sicher bestätigen")
        page.set_codes(codes, reset=True)
        page.confirmed.connect(self.accept)
        layout.addWidget(page)
