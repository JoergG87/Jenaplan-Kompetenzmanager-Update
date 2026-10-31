"""Presentation of the explicit product migration consent and result.

The dialog receives presentation state only. Runtime discovery, backup,
validation, process handoff and migration remain outside the widget.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QLabel, QMessageBox, QVBoxLayout,
)

from src.desktop_app.components import DialogHeader, configure_button
from src.desktop_app.dialogs.dialog_buttons import DialogActionBar
from src.desktop_app.motion import MotionDialog


class ProductMigrationDialog(MotionDialog):
    """Require a deliberate decision before handing control to maintenance."""

    def __init__(self, parent=None, *, completing: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Datenbestand aktualisieren")
        self.setModal(True)
        self.resize(580, 420)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(DialogHeader(
            "Datenbestand aktualisieren",
            "Jenaplan-Kompetenzmanager",
            "Die neue Programmversion benötigt einen aktualisierten Datenbestand."
            if not completing else
            "Die Aktualisierung wurde unterbrochen. Der vorhandene Bestand muss vor dem Abschluss erneut geprüft werden.",
        ))
        text = QLabel(
            "Vor der Umstellung wird automatisch eine vollständige verschlüsselte "
            "Sicherung erstellt und unabhängig geprüft. Anschließend werden die Daten "
            "umgestellt und vollständig geprüft. Die Sicherung bleibt erhalten.\n\n"
            "Währenddessen können Sie die Anwendung nicht benutzen. Bitte lassen Sie "
            "den Mac eingeschaltet. Danach startet die Anwendung neu; Ihr bisheriges "
            "Passwort bleibt gültig.\n\n"
            "Ältere Programmversionen wie Build 404 können den aktualisierten "
            "Datenbestand nicht öffnen. Eine Rückkehr erfordert die vollständige "
            "Sicherung von vor der Umstellung."
            if not completing else
            "Der vorhandene Wartungsprozess prüft den vollständigen Zielbestand "
            "erneut anhand der aufbewahrten Sicherung. Nur bei erfolgreicher Prüfung "
            "wird die Aktualisierung abgeschlossen und die Anwendung neu gestartet.\n\n"
            "Sicherung und Wartungsbelege bleiben erhalten. Es wird keine neue "
            "Umstellung begonnen. Bei einem unklaren Zustand wenden Sie sich bitte "
            "an den Support."
        )
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(text)
        self.consent = QCheckBox(
            "Ich möchte die Aktualisierung jetzt starten."
            if not completing else "Ich möchte den vorhandenen Abschluss prüfen lassen."
        )
        layout.addWidget(self.consent)
        self.buttons = DialogActionBar(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        self.start_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.start_button.setText("Aktualisierung starten" if not completing else "Abschluss prüfen")
        configure_button(self.start_button, "primary", self.start_button.text())
        self.start_button.setEnabled(False)
        self.start_button.setAutoDefault(False)
        self.later_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.later_button.setText("Später")
        configure_button(self.later_button, "secondary", "Aktualisierung verschieben")
        self.later_button.setDefault(True)
        self.later_button.setShortcut("Esc")
        self.consent.toggled.connect(self.start_button.setEnabled)
        self.buttons.accepted.connect(self._accept_consent)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _accept_consent(self):
        if self.consent.isChecked():
            self.accept()


def ask_product_migration(parent=None, *, completing: bool = False) -> bool:
    return ProductMigrationDialog(parent, completing=completing).exec() == QDialog.DialogCode.Accepted


def show_product_migration_success(parent=None) -> None:
    QMessageBox.information(
        parent, "Aktualisierung abgeschlossen",
        "Ihr Datenbestand wurde erfolgreich aktualisiert und geprüft. "
        "Die Sicherung von vor der Umstellung bleibt erhalten. "
        "Melden Sie sich mit Ihrem bisherigen Passwort an.",
    )


def show_product_migration_error(parent=None, *, support_code: str = "product_v7_maintenance_failed") -> None:
    box = QMessageBox(parent)
    box.setWindowTitle("Aktualisierung nicht abgeschlossen")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText("Die Aktualisierung konnte nicht sicher abgeschlossen werden.")
    box.setInformativeText(
        "Ihre vorhandenen Daten, Sicherungen und Wartungsbelege werden nicht gelöscht. "
        "Bitte erstellen Sie keinen neuen Datenbestand und wenden Sie sich an den Support."
    )
    # Never display exception text or arbitrary worker output, even in details.
    allowed = {"product_v7_maintenance_failed", "product_v7_target_not_committed",
               "product_v7_completion_inventory_invalid", "product_v7_existing_keys_required"}
    safe_code = support_code if support_code in allowed else "product_v7_maintenance_failed"
    box.setDetailedText("Supporthinweis: " + safe_code)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()
