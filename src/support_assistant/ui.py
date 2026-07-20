"""PySide presentation for the independent support operator application."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .application import (
    GeneratedResetCode,
    LoadedSupportRequest,
    SupportAssistantApplicationService,
    SupportAssistantError,
    support_request_reference,
)


_ERROR_MESSAGES = {
    "request_extension_invalid": "Bitte wähle eine .jkmresetrequest-Datei.",
    "request_unreadable": "Die Reset-Anfrage konnte nicht sicher gelesen werden.",
    "request_invalid": "Die Reset-Anfrage ist ungültig oder beschädigt.",
    "request_not_yet_valid": "Die Reset-Anfrage ist noch nicht gültig.",
    "request_expired": "Die Reset-Anfrage ist abgelaufen. Bitte eine neue Anfrage erstellen.",
    "support_key_not_active": "Der freigegebene Supportschlüssel ist nicht aktiv.",
    "private_key_unreadable": "Die private Schlüsseldatei konnte nicht sicher gelesen werden.",
    "private_key_permissions": "Die private Schlüsseldatei benötigt die Dateirechte 600.",
    "private_key_not_encrypted": "Bitte wähle einen verschlüsselten privaten PKCS#8-Schlüssel.",
    "private_key_unlock_failed": "Der private Schlüssel konnte nicht entsperrt werden.",
    "private_key_mismatch": "Der gewählte Schlüssel ist nicht support-2026-b.",
    "private_key_invalid": "Die gewählte Datei ist kein gültiger Ed25519-Schlüssel.",
    "passphrase_required": "Bitte gib die Passphrase des privaten Schlüssels ein.",
    "lifetime_invalid": "Bitte wähle eine zulässige Gültigkeitsdauer.",
    "audit_unavailable": "Das lokale technische Audit konnte nicht sicher geschrieben werden.",
    "token_target_exists": "Die Zieldatei existiert bereits und wird nicht überschrieben.",
    "token_target_invalid": "Der gewählte Zielordner ist nicht sicher verfügbar.",
    "token_write_failed": "Die Reset-Code-Datei konnte nicht sicher gespeichert werden.",
}


class SupportAssistantWindow(QMainWindow):
    """Linear operator flow; protocol and signing stay in the service."""

    def __init__(self, service: SupportAssistantApplicationService) -> None:
        super().__init__()
        self.service = service
        self._loaded_request: LoadedSupportRequest | None = None
        self._private_key_path: Path | None = None
        self._generated: GeneratedResetCode | None = None
        self.setObjectName("SupportAssistantWindow")
        self.setWindowTitle("Jenaplan Support-Assistent")
        self.setMinimumSize(860, 680)
        self.resize(960, 760)
        self._build()
        self.setStyleSheet(_STYLE)

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(42, 30, 42, 26)
        outer.setSpacing(16)

        brand = QHBoxLayout()
        mark = QLabel("J")
        mark.setObjectName("BrandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(40, 40)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        title = QLabel("Jenaplan Support-Assistent")
        title.setObjectName("AppTitle")
        brand_text.addWidget(title)
        subtitle = QLabel("Offline-Werkzeug für den betreuten Passwort-Reset")
        subtitle.setObjectName("Muted")
        brand_text.addWidget(subtitle)
        brand.addLayout(brand_text)
        brand.addStretch(1)
        offline = QLabel("●  Offline")
        offline.setObjectName("OfflineBadge")
        brand.addWidget(offline)
        outer.addLayout(brand)

        self.stack = QStackedWidget()
        self.start_page = self._build_start_page()
        self.review_page = self._build_review_page()
        self.result_page = self._build_result_page()
        for page in (self.start_page, self.review_page, self.result_page):
            self.stack.addWidget(page)
        outer.addWidget(self.stack, 1)

        footer = QLabel(
            "Keine automatische Suche oder Übertragung · Kein Zugriff auf Schülerdaten, "
            "Datenbanken, Dokumente oder Backups"
        )
        footer.setObjectName("Footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setWordWrap(True)
        outer.addWidget(footer)
        self.setCentralWidget(root)

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(76, 46, 76, 40)
        layout.addStretch(1)
        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(44, 40, 44, 40)
        card_layout.setSpacing(18)
        eyebrow = QLabel("BETREIBER-WERKZEUG")
        eyebrow.setObjectName("Eyebrow")
        card_layout.addWidget(eyebrow)
        heading = QLabel("Reset-Anfrage sicher bearbeiten")
        heading.setObjectName("HeroTitle")
        card_layout.addWidget(heading)
        explanation = QLabel(
            "Dieses Werkzeug erzeugt keinen Zugang und kein Passwort.\n"
            "Es erstellt ausschließlich einen zeitlich begrenzten Reset-Code."
        )
        explanation.setObjectName("HeroText")
        explanation.setWordWrap(True)
        card_layout.addWidget(explanation)
        boundary = QLabel(
            "Die Lehrkraft legt das neue Passwort später selbst in der Anwendung fest."
        )
        boundary.setObjectName("InfoBox")
        boundary.setWordWrap(True)
        card_layout.addWidget(boundary)
        self.start_message = QLabel("")
        self.start_message.setObjectName("ErrorMessage")
        self.start_message.setWordWrap(True)
        self.start_message.hide()
        card_layout.addWidget(self.start_message)
        actions = QHBoxLayout()
        actions.addStretch(1)
        open_button = QPushButton("Reset-Anfrage öffnen")
        open_button.setObjectName("PrimaryButton")
        open_button.setAccessibleName("Reset-Anfrage öffnen")
        open_button.setMinimumHeight(46)
        open_button.clicked.connect(self._open_request)
        actions.addWidget(open_button)
        card_layout.addLayout(actions)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_review_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 10, 18, 18)
        layout.setSpacing(14)

        heading_row = QHBoxLayout()
        back = QPushButton("← Andere Anfrage")
        back.setObjectName("QuietButton")
        back.clicked.connect(self.reset_flow)
        heading_row.addWidget(back)
        heading_row.addStretch(1)
        valid = QLabel("✓  Gültig")
        valid.setObjectName("SuccessBadge")
        heading_row.addWidget(valid)
        layout.addLayout(heading_row)

        request_card = self._card()
        request_layout = QVBoxLayout(request_card)
        request_layout.setContentsMargins(24, 20, 24, 22)
        request_layout.setSpacing(10)
        request_layout.addWidget(self._section_title("Geprüfte Reset-Anfrage"))
        self.request_values: dict[str, QLabel] = {}
        for key, label in (
            ("application", "Anwendung"),
            ("username", "Benutzername"),
            ("installation", "Installationskennung"),
            ("created", "Anfragezeit"),
            ("expires", "Ablaufzeit"),
        ):
            value = QLabel("–")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.request_values[key] = value
            request_layout.addLayout(self._value_row(label, value))
        identity_card = self._card()
        identity_layout = QVBoxLayout(identity_card)
        identity_layout.setContentsMargins(24, 20, 24, 22)
        identity_layout.setSpacing(9)
        identity_layout.addWidget(self._section_title("Telefonische Zuordnung"))
        device_label = QLabel("Installationsname")
        device_label.setObjectName("FieldLabel")
        identity_layout.addWidget(device_label)
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("Zum Beispiel Laura MacBook")
        self.device_name_input.setMaxLength(80)
        self.device_name_input.setAccessibleName("Installationsname")
        self.device_name_input.textChanged.connect(self._update_reference)
        identity_layout.addWidget(self.device_name_input)
        hint = QLabel(
            "Nur für dieses Gespräch. Der Name ersetzt nicht die technische UUID-Bindung."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        identity_layout.addWidget(hint)
        ref_row = QHBoxLayout()
        ref_title = QLabel("Anfragecode")
        ref_title.setObjectName("FieldLabel")
        ref_row.addWidget(ref_title)
        ref_row.addStretch(1)
        self.reference_value = QLabel("JKM-GERAET-0000")
        self.reference_value.setObjectName("ReferenceCode")
        self.reference_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        ref_row.addWidget(self.reference_value)
        identity_layout.addLayout(ref_row)
        overview_row = QHBoxLayout()
        overview_row.setSpacing(14)
        overview_row.addWidget(request_card, 1)
        overview_row.addWidget(identity_card, 1)
        layout.addLayout(overview_row)

        key_card = self._card()
        key_layout = QVBoxLayout(key_card)
        key_layout.setContentsMargins(24, 20, 24, 22)
        key_layout.setSpacing(10)
        key_layout.addWidget(self._section_title("Supportschlüssel"))
        self.key_id_value = QLabel("–")
        self.key_status_value = QLabel("–")
        self.key_fingerprint_value = QLabel("–")
        key_layout.addLayout(self._value_row("Schlüssel", self.key_id_value))
        key_layout.addLayout(self._value_row("Status", self.key_status_value))
        key_layout.addLayout(self._value_row("Fingerprint", self.key_fingerprint_value))
        key_layout.addSpacing(4)
        credentials_row = QHBoxLayout()
        credentials_row.setSpacing(16)
        key_choice_box = QVBoxLayout()
        key_choice_label = QLabel("Privater Schlüssel")
        key_choice_label.setObjectName("FieldLabel")
        key_choice_box.addWidget(key_choice_label)
        key_file_row = QHBoxLayout()
        self.private_key_value = QLabel("Noch keine externe Schlüsseldatei gewählt")
        self.private_key_value.setObjectName("Muted")
        key_file_row.addWidget(self.private_key_value, 1)
        choose_key = QPushButton("Schlüsseldatei wählen …")
        choose_key.setObjectName("SecondaryButton")
        choose_key.setAccessibleName("Externen privaten Supportschlüssel wählen")
        choose_key.clicked.connect(self._choose_private_key)
        key_file_row.addWidget(choose_key)
        key_choice_box.addLayout(key_file_row)
        credentials_row.addLayout(key_choice_box, 1)
        passphrase_box = QVBoxLayout()
        passphrase_label = QLabel("Passphrase")
        passphrase_label.setObjectName("FieldLabel")
        passphrase_box.addWidget(passphrase_label)
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_input.setAccessibleName("Passphrase des privaten Supportschlüssels")
        self.passphrase_input.setPlaceholderText("Passphrase eingeben")
        passphrase_box.addWidget(self.passphrase_input)
        credentials_row.addLayout(passphrase_box, 1)
        key_layout.addLayout(credentials_row)
        key_layout.addSpacing(6)
        action_layout = QHBoxLayout()
        duration_box = QVBoxLayout()
        duration_label = QLabel("Gültigkeit")
        duration_label.setObjectName("FieldLabel")
        duration_box.addWidget(duration_label)
        self.lifetime_combo = QComboBox()
        self.lifetime_combo.addItems(("15 Minuten", "30 Minuten", "60 Minuten", "120 Minuten"))
        self.lifetime_combo.setCurrentIndex(1)
        self.lifetime_combo.setAccessibleName("Gültigkeit des Reset-Codes")
        duration_box.addWidget(self.lifetime_combo)
        action_layout.addLayout(duration_box)
        action_layout.addStretch(1)
        self.generate_button = QPushButton("Reset-Code erzeugen")
        self.generate_button.setObjectName("PrimaryButton")
        self.generate_button.setAccessibleName("Reset-Code erzeugen")
        self.generate_button.setMinimumHeight(46)
        self.generate_button.clicked.connect(self._generate_reset_code)
        action_layout.addWidget(self.generate_button, 0, Qt.AlignmentFlag.AlignBottom)
        key_layout.addLayout(action_layout)
        layout.addWidget(key_card)
        self.review_message = QLabel("")
        self.review_message.setObjectName("ErrorMessage")
        self.review_message.setWordWrap(True)
        self.review_message.hide()
        layout.addWidget(self.review_message)
        layout.addStretch(1)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(76, 42, 76, 38)
        layout.addStretch(1)
        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(46, 38, 46, 38)
        card_layout.setSpacing(16)
        success = QLabel("✓")
        success.setObjectName("SuccessMark")
        success.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(success)
        heading = QLabel("Reset-Code ist bereit")
        heading.setObjectName("HeroTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(heading)
        note = QLabel(
            "Der Code erzeugt weder Zugang noch Passwort. Die Lehrkraft legt das neue "
            "Passwort nach dem geprüften Reset selbst fest."
        )
        note.setObjectName("HeroText")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        card_layout.addWidget(note)
        self.result_reference = QLabel("–")
        self.result_reference.setObjectName("ReferenceCodeLarge")
        self.result_reference.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.result_reference)
        self.result_expiry = QLabel("Gültig bis: –")
        self.result_expiry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_expiry.setObjectName("ResultExpiry")
        card_layout.addWidget(self.result_expiry)
        audit_note = QLabel(
            "Das technische Audit enthält nur Zeitpunkt, Request-ID, Key-ID und Aktion."
        )
        audit_note.setObjectName("InfoBox")
        audit_note.setWordWrap(True)
        card_layout.addWidget(audit_note)
        self.result_message = QLabel("")
        self.result_message.setObjectName("InfoMessage")
        self.result_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_message.hide()
        card_layout.addWidget(self.result_message)
        actions = QHBoxLayout()
        actions.addStretch(1)
        copy_button = QPushButton("Kopieren")
        copy_button.setObjectName("SecondaryButton")
        copy_button.setAccessibleName("Reset-Code kopieren")
        copy_button.clicked.connect(self._copy_token)
        actions.addWidget(copy_button)
        save_button = QPushButton("Datei speichern …")
        save_button.setObjectName("PrimaryButton")
        save_button.setAccessibleName("Reset-Code als Datei speichern")
        save_button.clicked.connect(self._save_token)
        actions.addWidget(save_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)
        another = QPushButton("Weitere Anfrage bearbeiten")
        another.setObjectName("QuietButton")
        another.clicked.connect(self.reset_flow)
        card_layout.addWidget(another, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    @staticmethod
    def _value_row(title: str, value: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("ValueLabel")
        value.setObjectName("ValueText")
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(value)
        return row

    def _open_request(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self,
            "Reset-Anfrage öffnen",
            "",
            "Jenaplan Reset-Anfrage (*.jkmresetrequest)",
        )
        if path:
            self.load_request_path(Path(path))

    def load_request_path(self, path: Path) -> bool:
        try:
            loaded = self.service.load_request(path)
            key = self.service.key_projection()
        except SupportAssistantError as error:
            self._show_error(self.start_message, error)
            return False
        self._set_loaded_request(loaded)
        self.key_id_value.setText(key.key_id)
        self.key_status_value.setText("aktiv")
        self.key_fingerprint_value.setText(key.fingerprint_short)
        self.start_message.hide()
        self.stack.setCurrentWidget(self.review_page)
        self.device_name_input.setFocus()
        return True

    def show_loaded_request(self, loaded: LoadedSupportRequest) -> None:
        """Set a pre-inspected synthetic state for screenshots and UI tests."""
        key = self.service.key_projection()
        self._set_loaded_request(loaded)
        self.key_id_value.setText(key.key_id)
        self.key_status_value.setText("aktiv")
        self.key_fingerprint_value.setText(key.fingerprint_short)
        self.stack.setCurrentWidget(self.review_page)

    def _set_loaded_request(self, loaded: LoadedSupportRequest) -> None:
        self._loaded_request = loaded
        projection = loaded.projection
        self.request_values["application"].setText(projection.application_name)
        self.request_values["username"].setText(
            projection.username or "Nicht in dieser Anfrage enthalten"
        )
        self.request_values["installation"].setText(projection.installation_id_short)
        self.request_values["created"].setText(_display_time(projection.created_at))
        self.request_values["expires"].setText(_display_time(projection.expires_at))
        self._update_reference()

    def _choose_private_key(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self,
            "Externen Supportschlüssel wählen",
            "",
            "Verschlüsselter Schlüssel (*.pem);;Alle Dateien (*)",
        )
        if not path:
            return
        self._private_key_path = Path(path)
        self.private_key_value.setText(self._private_key_path.name)

    def _update_reference(self) -> None:
        if self._loaded_request is None:
            return
        reference = support_request_reference(
            self.device_name_input.text(), self._loaded_request.request.reset_request_id
        )
        self.reference_value.setText(reference)

    def _generate_reset_code(self) -> None:
        self.review_message.hide()
        if self._loaded_request is None:
            self._show_error_code(self.review_message, "request_invalid")
            return
        if not self.device_name_input.text().strip():
            self.review_message.setText(
                "Bitte gib einen Installationsnamen für die telefonische Zuordnung ein."
            )
            self.review_message.show()
            self.device_name_input.setFocus()
            return
        if self._private_key_path is None:
            self.review_message.setText("Bitte wähle den externen privaten Supportschlüssel.")
            self.review_message.show()
            return
        lifetime = (15, 30, 60, 120)[self.lifetime_combo.currentIndex()]
        self.generate_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._generated = self.service.generate_reset_code(
                loaded_request=self._loaded_request,
                private_key_path=self._private_key_path,
                passphrase=self.passphrase_input.text(),
                lifetime_minutes=lifetime,
            )
        except SupportAssistantError as error:
            self._show_error(self.review_message, error)
            return
        finally:
            self.passphrase_input.clear()
            QApplication.restoreOverrideCursor()
            self.generate_button.setEnabled(True)
        self.result_reference.setText(self.reference_value.text())
        self.result_expiry.setText(f"Gültig bis: {_display_time(self._generated.expires_at)}")
        self.result_message.hide()
        self.stack.setCurrentWidget(self.result_page)

    def _copy_token(self) -> None:
        if self._generated is None:
            return
        QApplication.clipboard().setText(self._generated.token)
        self.result_message.setText("Reset-Code wurde bewusst in die Zwischenablage kopiert.")
        self.result_message.show()

    def _save_token(self) -> None:
        if self._generated is None:
            return
        suggested = f"{self.result_reference.text()}.jkmresettoken"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Reset-Code speichern",
            suggested,
            "Jenaplan Reset-Code (*.jkmresettoken)",
        )
        if not path:
            return
        try:
            saved = self.service.save_reset_code(Path(path), self._generated.token)
        except SupportAssistantError as error:
            self._show_error(self.result_message, error)
            return
        self.result_message.setText(f"Reset-Code-Datei gespeichert: {saved.name}")
        self.result_message.setObjectName("InfoMessage")
        self.result_message.style().unpolish(self.result_message)
        self.result_message.style().polish(self.result_message)
        self.result_message.show()

    def show_demo_result(self, *, reference: str, expires_at: datetime) -> None:
        """Show a token-free result state for documentation screenshots."""
        self.result_reference.setText(reference)
        self.result_expiry.setText(f"Gültig bis: {_display_time(expires_at)}")
        self.stack.setCurrentWidget(self.result_page)

    def reset_flow(self) -> None:
        self._loaded_request = None
        self._private_key_path = None
        self._generated = None
        self.device_name_input.clear()
        self.passphrase_input.clear()
        self.private_key_value.setText("Noch keine externe Schlüsseldatei gewählt")
        self.review_message.hide()
        self.result_message.hide()
        self.stack.setCurrentWidget(self.start_page)

    @staticmethod
    def _show_error(label: QLabel, error: SupportAssistantError) -> None:
        SupportAssistantWindow._show_error_code(label, error.code)

    @staticmethod
    def _show_error_code(label: QLabel, code: str) -> None:
        label.setText(
            _ERROR_MESSAGES.get(
                code, "Der Reset-Code konnte nicht sicher erzeugt werden. Bitte neu beginnen."
            )
        )
        label.setObjectName("ErrorMessage")
        label.style().unpolish(label)
        label.style().polish(label)
        label.show()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API
        self.passphrase_input.clear()
        self._generated = None
        super().closeEvent(event)


def _display_time(value: datetime) -> str:
    return value.astimezone().strftime("%d.%m.%Y, %H:%M Uhr")


_STYLE = """
QWidget#Root { background: #F2F6F8; color: #17324D; }
QWidget { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI'; font-size: 14px; }
QLabel#AppTitle { font-size: 19px; font-weight: 700; color: #17324D; }
QLabel#BrandMark { background: #176B87; color: white; border-radius: 12px; font-size: 22px; font-weight: 800; }
QLabel#Muted { color: #65788A; font-size: 13px; }
QLabel#Footer { color: #718294; font-size: 12px; }
QLabel#OfflineBadge { background: #E7F5F0; color: #1F6D56; border: 1px solid #B9DDD0; border-radius: 13px; padding: 5px 10px; font-weight: 600; }
QFrame#Card { background: #FFFFFF; border: 1px solid #D8E2E8; border-radius: 14px; }
QLabel#Eyebrow { color: #176B87; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
QLabel#HeroTitle { color: #17324D; font-size: 26px; font-weight: 750; }
QLabel#HeroText { color: #40576B; font-size: 16px; line-height: 1.35; }
QLabel#SectionTitle { color: #17324D; font-size: 17px; font-weight: 700; }
QLabel#InfoBox { background: #EEF7FA; color: #2D5668; border: 1px solid #CAE1E8; border-radius: 9px; padding: 11px 13px; }
QLabel#ErrorMessage { background: #FFF0EF; color: #8B2F2A; border: 1px solid #EBC4C0; border-radius: 9px; padding: 10px 12px; }
QLabel#InfoMessage { background: #EDF7F3; color: #236A53; border: 1px solid #BFDCCF; border-radius: 9px; padding: 10px 12px; }
QLabel#SuccessBadge { background: #E6F5EE; color: #1F6D56; border: 1px solid #B8DDCF; border-radius: 13px; padding: 5px 11px; font-weight: 700; }
QLabel#ValueLabel { color: #65788A; min-width: 155px; }
QLabel#ValueText { color: #17324D; font-weight: 600; }
QLabel#FieldLabel { color: #314D63; font-weight: 650; }
QLabel#ReferenceCode { color: #176B87; background: #EAF5F8; border: 1px solid #BFDDE5; border-radius: 8px; padding: 7px 11px; font-family: Menlo; font-weight: 700; }
QLabel#ReferenceCodeLarge { color: #176B87; background: #EAF5F8; border: 1px solid #BFDDE5; border-radius: 10px; padding: 12px; font-family: Menlo; font-size: 19px; font-weight: 750; }
QLabel#SuccessMark { color: white; background: #2A8A68; border-radius: 24px; font-size: 25px; font-weight: 800; min-width: 48px; max-width: 48px; min-height: 48px; max-height: 48px; }
QLabel#ResultExpiry { color: #314D63; font-size: 15px; font-weight: 650; }
QLineEdit, QComboBox { background: white; border: 1px solid #BFCED7; border-radius: 8px; padding: 9px 10px; min-height: 20px; color: #17324D; }
QLineEdit:focus, QComboBox:focus { border: 2px solid #2B7FA0; padding: 8px 9px; }
QPushButton { border-radius: 8px; padding: 9px 16px; font-weight: 650; min-height: 22px; }
QPushButton#PrimaryButton { background: #176B87; color: white; border: 1px solid #176B87; }
QPushButton#PrimaryButton:hover { background: #125A72; }
QPushButton#PrimaryButton:disabled { background: #9CB4BF; border-color: #9CB4BF; }
QPushButton#SecondaryButton { background: #EDF5F8; color: #175B73; border: 1px solid #B8D3DC; }
QPushButton#SecondaryButton:hover { background: #DDEDF2; }
QPushButton#QuietButton { background: transparent; color: #176B87; border: 1px solid transparent; }
QPushButton#QuietButton:hover { background: #E5EFF3; }
QScrollArea { background: transparent; }
"""
