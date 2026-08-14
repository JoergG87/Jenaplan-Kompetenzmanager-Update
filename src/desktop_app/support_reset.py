"""Visible Qt handoff for the existing offline support-reset protocol."""

from __future__ import annotations

from collections.abc import Callable
import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.security.domain import (
    SUPPORT_RESET_MAX_TOKEN_BYTES,
    SupportResetFailureCode,
    SupportResetRejected,
    SupportResetRequest,
)
from src.security.support_reset import SupportResetTokenCodec

from .components import AppCard, InlineMessage, configure_button
from .motion import MotionDialog
from .theme import set_label_style


_SECURITY_LOG = logging.getLogger("jenaplan.security")
SUPPORT_RESET_NOT_RELEASED = (
    "Der Support-Reset ist in dieser App-Version noch nicht für den produktiven "
    "Betrieb freigeschaltet."
)


class SupportResetOperationWorker(QObject):
    """Run validation or backup/reset work away from the UI thread."""

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
        except Exception as error:
            self.failed.emit(error)
        finally:
            self._operation = lambda: None
            self.finished.emit()


class SupportResetDialog(MotionDialog):
    """Guided request, validation preview, and confirmed reset UI."""

    reset_completed = Signal(object)
    reset_shutdown_required = Signal(object)

    def __init__(self, *, service, backup_factory, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.backup_factory = backup_factory
        self._request: SupportResetRequest | None = None
        self._verified_token = ""
        self._busy = False
        self._committed = False
        self._thread: QThread | None = None
        self._worker: SupportResetOperationWorker | None = None
        self._truncating_token = False
        self.setObjectName("SupportResetDialog")
        self.setWindowTitle("Weitere Wiederherstellungsmöglichkeiten")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QDialog#SupportResetDialog { background: #F3F7FA; }")
        self.setMinimumSize(720, 650)
        self.resize(860, 720)
        self._build()
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)
        self.create_request_button.setDefault(True)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(56, 40, 56, 40)
        title = QLabel("Weitere Wiederherstellungsmöglichkeiten")
        set_label_style(title, "screen_title")
        outer.addWidget(title)
        intro = QLabel(
            "Wenn Passwort und Recovery-Codes nicht mehr verfügbar sind, kann der "
            "Support einen offline signierten Reset-Code für diese Installation erstellen. "
            "Die geschützte lokale Dateninstallation muss vollständig verfügbar sein."
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)
        self.stack = QStackedWidget()
        self.request_page = self._build_request_page()
        self.token_page = self._build_token_page()
        self.preview_page = self._build_preview_page()
        self.progress_page = self._build_progress_page()
        for page in (self.request_page, self.token_page, self.preview_page, self.progress_page):
            self.stack.addWidget(page)
        outer.addWidget(self.stack, 1)

    def _card_page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        card = AppCard("default")
        layout = QVBoxLayout(card)
        page_layout.addWidget(card)
        return page, layout

    def _build_request_page(self) -> QWidget:
        page, layout = self._card_page()
        heading = QLabel("1. Support-Anfrage erstellen")
        set_label_style(heading, "section_title")
        layout.addWidget(heading)
        note = QLabel(
            "Support kann nur die lokale Authentifizierung zurücksetzen. Fachliche Daten "
            "und ihre vorhandenen Schlüssel bleiben unverändert geschützt. "
            "Die Anfrage enthält nur technische Kennungen, Gültigkeitszeiten und eine "
            "zufällige Einmalbindung."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.release_message = InlineMessage()
        if not self.service.product_enabled:
            self.release_message.set_message(SUPPORT_RESET_NOT_RELEASED, tone="error")
        layout.addWidget(self.release_message)
        self.request_display = QPlainTextEdit()
        self.request_display.setObjectName("SupportResetRequestDisplay")
        self.request_display.setReadOnly(True)
        self.request_display.setPlaceholderText("Noch keine Support-Anfrage erstellt.")
        self.request_display.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.request_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.request_display.setMinimumHeight(190)
        font = QFont("Menlo")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.request_display.setFont(font)
        layout.addWidget(self.request_display)
        self.request_summary = QLabel("")
        self.request_summary.setWordWrap(True)
        self.request_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.request_summary)
        self.request_message = InlineMessage()
        layout.addWidget(self.request_message)
        actions = QHBoxLayout()
        self.copy_request_button = QPushButton("Anfrage kopieren")
        configure_button(self.copy_request_button, "quiet", "Support-Anfrage kopieren")
        self.copy_request_button.setEnabled(False)
        self.copy_request_button.clicked.connect(self._copy_request)
        actions.addWidget(self.copy_request_button)
        self.export_request_button = QPushButton("Anfrage speichern …")
        configure_button(self.export_request_button, "secondary", "Support-Anfrage speichern")
        self.export_request_button.setEnabled(False)
        self.export_request_button.clicked.connect(self._export_request)
        actions.addWidget(self.export_request_button)
        actions.addStretch(1)
        self.create_request_button = QPushButton("Reset-Anfrage erstellen")
        configure_button(self.create_request_button, "primary", "Support-Anfrage erstellen")
        self.create_request_button.clicked.connect(self._create_request)
        actions.addWidget(self.create_request_button)
        layout.addLayout(actions)
        self.open_token_button = QPushButton("Reset-Code eingeben")
        configure_button(self.open_token_button, "secondary", "Reset-Code eingeben")
        self.open_token_button.setEnabled(False)
        self.open_token_button.clicked.connect(self._show_token_page)
        layout.addWidget(self.open_token_button, 0, Qt.AlignmentFlag.AlignRight)
        return page

    def _build_token_page(self) -> QWidget:
        page, layout = self._card_page()
        heading = QLabel("2. Reset-Code prüfen")
        set_label_style(heading, "section_title")
        layout.addWidget(heading)
        note = QLabel(
            "Füge den vom Support erhaltenen Reset-Code ein oder öffne eine "
            ".jkmresettoken-Datei. Die Prüfung verändert noch keine Daten."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.token_input = QPlainTextEdit()
        self.token_input.setObjectName("SupportResetTokenInput")
        self.token_input.setAccessibleName("Offline Reset-Code")
        self.token_input.setPlaceholderText("JKM-SR1.…")
        self.token_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.token_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.token_input.setMinimumHeight(220)
        self.token_input.textChanged.connect(self._bound_token_input)
        layout.addWidget(self.token_input)
        self.token_message = InlineMessage()
        layout.addWidget(self.token_message)
        actions = QHBoxLayout()
        back = QPushButton("Zurück")
        configure_button(back, "quiet", "Zurück zur Support-Anfrage")
        back.clicked.connect(self._back_to_request)
        actions.addWidget(back)
        import_button = QPushButton("Code-Datei öffnen …")
        configure_button(import_button, "secondary", "Reset-Code-Datei öffnen")
        import_button.clicked.connect(self._import_token)
        actions.addWidget(import_button)
        actions.addStretch(1)
        self.verify_button = QPushButton("Reset-Code prüfen")
        configure_button(self.verify_button, "primary", "Reset-Code prüfen")
        self.verify_button.clicked.connect(self._verify_token)
        actions.addWidget(self.verify_button)
        layout.addLayout(actions)
        return page

    def _build_preview_page(self) -> QWidget:
        page, layout = self._card_page()
        heading = QLabel("3. Reset bestätigen")
        set_label_style(heading, "section_title")
        layout.addWidget(heading)
        self.preview_text = QLabel()
        self.preview_text.setWordWrap(True)
        self.preview_text.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.preview_text)
        boundary = QLabel(
            "Vor dem Reset wird automatisch ein vollständiges Backup erstellt und geprüft. "
            "Danach wird das lokale Passwort zurückgesetzt; Recovery-Codes, gespeicherte "
            "Geräteanmeldung und Touch ID werden ungültig. Fachliche Daten und Dokumente "
            "bleiben unverändert. Das geprüfte Backup liegt im lokalen Backup-Ordner."
        )
        boundary.setWordWrap(True)
        layout.addWidget(boundary)
        warning = InlineMessage()
        warning.set_message(
            "Nach der Bestätigung endet die aktuelle Sitzung. Beim nächsten Start legst du "
            "ein neues Passwort und neue Recovery-Codes fest."
        )
        layout.addWidget(warning)
        actions = QHBoxLayout()
        back = QPushButton("Zurück")
        configure_button(back, "quiet", "Zurück zum Reset-Code")
        back.clicked.connect(self._back_to_token)
        actions.addWidget(back)
        actions.addStretch(1)
        self.execute_button = QPushButton("Sicherheitsbackup erstellen und Passwort zurücksetzen")
        configure_button(
            self.execute_button,
            "primary",
            "Sicherheitsbackup erstellen und Passwort zurücksetzen",
        )
        self.execute_button.clicked.connect(self._execute_reset)
        actions.addWidget(self.execute_button)
        layout.addLayout(actions)
        return page

    def _build_progress_page(self) -> QWidget:
        page, layout = self._card_page()
        heading = QLabel("Backup und Reset werden abgeschlossen …")
        set_label_style(heading, "section_title")
        layout.addWidget(heading)
        text = QLabel(
            "Bitte schließe die App nicht. Der Vorgang kann während Backup und Reset nicht "
            "abgebrochen werden."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        progress = QProgressBar()
        progress.setObjectName("SupportResetProgress")
        progress.setRange(0, 0)
        progress.setTextVisible(False)
        layout.addWidget(progress)
        self.progress_message = InlineMessage()
        layout.addWidget(self.progress_message)
        layout.addStretch(1)
        return page

    def _run(self, operation: Callable[[], object], success, failure) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_actions_enabled(False)
        thread = QThread(self)
        worker = SupportResetOperationWorker(operation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._operation_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot()
    def _operation_finished(self) -> None:
        self._busy = False
        self._set_actions_enabled(True)
        self._thread = None
        self._worker = None

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.create_request_button.setEnabled(enabled)
        self.copy_request_button.setEnabled(enabled and self._request is not None)
        self.export_request_button.setEnabled(enabled and self._request is not None)
        self.open_token_button.setEnabled(
            enabled and self._request is not None and self.service.product_enabled
        )
        self.verify_button.setEnabled(enabled)
        self.execute_button.setEnabled(enabled)

    def _create_request(self) -> None:
        self.request_message.set_message("")
        self._run(self.service.create_request, self._request_created, self._request_failed)

    def _request_created(self, request: SupportResetRequest) -> None:
        self._request = request
        content = SupportResetTokenCodec.canonical_request_bytes(request).decode("utf-8")
        self.request_display.setPlainText(content)
        self.request_summary.setText(
            f"Installation: {self._short_id(request.installation_id)} · "
            f"Nutzer: {self._short_id(request.user_id)} · "
            f"Anfrage: {self._short_id(request.reset_request_id)}\n"
            "Die vollständigen technischen Kennungen sind im kopierbaren Exporttext enthalten."
        )
        self.request_message.set_message(
            f"Anfrage {self._short_id(request.reset_request_id)} ist bis "
            f"{request.expires_at.astimezone().strftime('%d.%m.%Y, %H:%M')} Uhr gültig."
        )
        _SECURITY_LOG.info("support_reset_request_created")
        self._set_actions_enabled(True)
        self.create_request_button.setDefault(False)
        self.open_token_button.setDefault(self.service.product_enabled)

    def _request_failed(self, _error: object) -> None:
        self.request_message.set_message(
            "Die Support-Anfrage konnte nicht erstellt werden.", tone="error"
        )

    def _copy_request(self) -> None:
        if self._request is None:
            return
        QApplication.clipboard().setText(self.request_display.toPlainText())
        self.request_message.set_message("Die Support-Anfrage wurde kopiert.")

    def _export_request(self) -> None:
        if self._request is None:
            return
        suggested = f"support-reset-{self._short_id(self._request.reset_request_id)}.jkmresetrequest"
        path, _selected = QFileDialog.getSaveFileName(
            self, "Support-Anfrage speichern", suggested, "Support-Anfrage (*.jkmresetrequest)"
        )
        if not path:
            return
        target = Path(path)
        if target.suffix != ".jkmresetrequest":
            target = target.with_suffix(".jkmresetrequest")
        try:
            data = SupportResetTokenCodec.canonical_request_bytes(self._request)
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                raise
            if os.name == "posix":
                os.chmod(target, 0o600)
        except OSError:
            self.request_message.set_message(
                "Die Support-Anfrage konnte nicht gespeichert werden.", tone="error"
            )
            return
        self.request_message.set_message("Die Support-Anfrage wurde gespeichert.")

    def _back_to_request(self) -> None:
        self._clear_token()
        self.stack.setCurrentWidget(self.request_page)
        self.create_request_button.setDefault(self._request is None)
        self.open_token_button.setDefault(
            self._request is not None and self.service.product_enabled
        )
        self.verify_button.setDefault(False)
        self.execute_button.setDefault(False)

    def _show_token_page(self) -> None:
        self.stack.setCurrentWidget(self.token_page)
        self.create_request_button.setDefault(False)
        self.open_token_button.setDefault(False)
        self.verify_button.setDefault(True)
        self.execute_button.setDefault(False)
        self.token_input.setFocus()

    def _import_token(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self, "Reset-Code öffnen", "", "Reset-Code (*.jkmresettoken);;Alle Dateien (*)"
        )
        if not path:
            return
        try:
            with Path(path).open("rb") as stream:
                raw = stream.read(SUPPORT_RESET_MAX_TOKEN_BYTES + 9)
            if len(raw) > SUPPORT_RESET_MAX_TOKEN_BYTES + 8:
                raise ValueError("token_too_large")
            text = raw.decode("ascii")
            SupportResetTokenCodec.normalize_input(text)
        except (OSError, UnicodeError, ValueError, SupportResetRejected):
            self._generic_token_error()
            return
        self.token_input.setPlainText(text)
        self.token_message.set_message("Die Code-Datei wurde geöffnet.")

    def _bound_token_input(self) -> None:
        if self._truncating_token:
            return
        text = self.token_input.toPlainText()
        maximum = SUPPORT_RESET_MAX_TOKEN_BYTES + 8
        if len(text) <= maximum:
            return
        self._truncating_token = True
        self.token_input.setPlainText(text[:maximum])
        self.token_input.moveCursor(self.token_input.textCursor().MoveOperation.End)
        self._truncating_token = False
        self.token_message.set_message(
            "Der Reset-Code ist länger als das unterstützte Format.", tone="error"
        )

    def _verify_token(self) -> None:
        try:
            token = SupportResetTokenCodec.normalize_input(self.token_input.toPlainText())
        except SupportResetRejected:
            self._generic_token_error()
            return
        self.token_message.set_message("")
        self._run(
            lambda: self.service.verify_token(token),
            lambda result: self._token_verified(result, token),
            self._token_rejected,
        )

    def _token_verified(self, result, token: str) -> None:
        self._verified_token = token
        self.token_input.clear()
        self.preview_text.setText(
            "Die Signatur und die Bindung an diese Installation wurden bestätigt.\n\n"
            f"Anfrage: {self._short_id(result.reset_request_id)}\n"
            f"Support-Schlüssel: {result.key_id}\n"
            f"Reset-Code gültig bis: {result.expires_at.astimezone().strftime('%d.%m.%Y, %H:%M')} Uhr"
        )
        self.stack.setCurrentWidget(self.preview_page)
        self.create_request_button.setDefault(False)
        self.verify_button.setDefault(False)
        self.execute_button.setDefault(True)
        _SECURITY_LOG.info("support_reset_token_accepted")

    def _token_rejected(self, _error: object) -> None:
        _SECURITY_LOG.info("support_reset_token_rejected")
        self._generic_token_error()

    def _generic_token_error(self) -> None:
        self._clear_token()
        self.token_message.set_message(
            "Der Reset-Code ist ungültig, abgelaufen oder passt nicht zu dieser Installation.",
            tone="error",
        )

    def _back_to_token(self) -> None:
        self._clear_token()
        self._show_token_page()

    def _execute_reset(self) -> None:
        if not self._verified_token:
            self._generic_token_error()
            self._show_token_page()
            return
        token = self._verified_token
        self.stack.setCurrentWidget(self.progress_page)
        self.execute_button.setDefault(False)
        self.progress_message.set_message("Das Sicherheitsbackup wird erstellt und geprüft.")
        _SECURITY_LOG.info("support_reset_backup_started")
        self._run(
            lambda: self.service.execute(token, backup=self.backup_factory.create()),
            self._reset_succeeded,
            self._reset_failed,
        )

    def _reset_succeeded(self, result) -> None:
        self._committed = True
        self._clear_token()
        self.progress_message.set_message(
            f"Sicherheitsbackup geprüft: {Path(result.backup.path).name}. Die App wird beendet."
        )
        _SECURITY_LOG.info("support_reset_completed")
        self.reset_completed.emit(result)
        self.accept()

    def _reset_failed(self, error: object) -> None:
        self._clear_token()
        if (
            isinstance(error, SupportResetRejected)
            and error.code is SupportResetFailureCode.RUNTIME_RECOVERY_REQUIRED
        ):
            _SECURITY_LOG.error("support_reset_runtime_recovery_required")
            self.progress_message.set_message(
                "Der Sicherheitszustand konnte nicht eindeutig bestätigt werden. "
                "Die App wird beendet und prüft ihn beim nächsten Start.",
                tone="error",
            )
            self.reset_shutdown_required.emit(error)
            self.accept()
            return
        if isinstance(error, SupportResetRejected) and error.code is SupportResetFailureCode.BACKUP_FAILED:
            _SECURITY_LOG.info("support_reset_backup_failed")
            text = "Das Sicherheitsbackup konnte nicht erstellt und geprüft werden. Es wurde nichts zurückgesetzt."
        elif (
            isinstance(error, SupportResetRejected)
            and error.code is SupportResetFailureCode.PRODUCT_VALIDATION_FAILED
        ):
            _SECURITY_LOG.info("support_reset_product_validation_failed")
            text = (
                "Die geschützten lokalen Daten konnten nicht vollständig geprüft werden. "
                "Das Passwort wurde nicht zurückgesetzt."
            )
        else:
            _SECURITY_LOG.info("support_reset_token_rejected")
            text = "Der Reset konnte nicht sicher bestätigt werden. Es wurde nichts zurückgesetzt."
        self.progress_message.set_message(text, tone="error")
        self._show_token_page()

    def _clear_token(self) -> None:
        self._verified_token = ""
        self.token_input.clear()

    @staticmethod
    def _short_id(value: str) -> str:
        return value.split("-")[0].upper()

    def reject(self) -> None:
        if self._busy or self._committed:
            return
        self._clear_token()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._busy or self._committed:
            event.ignore()
            return
        self._clear_token()
        event.accept()
