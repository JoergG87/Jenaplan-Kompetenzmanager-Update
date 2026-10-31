"""Explicit one-shot maintenance entry; ordinary startup never calls execute."""
from pathlib import Path
import os
import sys

from src.core.restore_runtime import RuntimeInstanceLock
from src.security.product_v7 import (
    ProductV7Migration, build_product_v7_service, require_product_v7_scope,
)
from src.security.upgrade_startup import ProductUpgradeStartupGuard


def _command(arguments):
    if getattr(sys, "frozen", False):
        return [sys.executable, *arguments]
    return [sys.executable, "-m", "src.desktop_app.main", *arguments]


def _perform_maintenance(root, *, complete=False, progress=None):
    # Load the existing authenticated account/key context only after acquiring
    # the ordinary product instance lock. Never create an account or a key.
    with RuntimeInstanceLock(root) as lock:
        ProductUpgradeStartupGuard(lock)._require_lock()
        service = build_product_v7_service(root, v4_source=True)
        migration = ProductV7Migration(service, fault_hook=progress)
        if not complete:
            migration.execute(lock=lock)
    if complete:
        # complete() independently reacquires the ordinary lock.
        migration.complete()


def _restart_maintenance(root, *, complete=False, guided=False):
    environment = dict(os.environ)
    if getattr(sys, "frozen", False):
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    working_directory = root if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
    if complete:
        # Fresh image after migration, with no inherited connections or gates.
        arguments = ["--runtime-root", str(root)]
        if guided:
            arguments.append("--v7-migration-completed")
        command = _command(arguments)
    else:
        arguments = ["--complete-v7-migration", "--runtime-root", str(root)]
        if guided:
            arguments.append("--guided-v7-migration")
        command = _command(arguments)
    # Replace each drained image rather than racing a live recorded parent.
    # No lock/descriptor handoff: the new image acquires the lock normally.
    os.chdir(working_directory)
    os.execve(command[0], command, environment)
    raise RuntimeError("product_v7_exec_returned")


_PHASE_TEXT = {
    "source_verified": "Der vorhandene Datenbestand wurde geprüft. Die Sicherung wird erstellt …",
    "backup_verified": "Die verschlüsselte Vollsicherung wurde unabhängig geprüft …",
    "connections_closed": "Die Datenverbindungen sind geschlossen. Die Umstellung wird vorbereitet …",
    "transaction_begun": "Der Datenbestand wird auf die neue Version umgestellt …",
    "schema_changed": "Die umgestellten Daten werden vollständig geprüft …",
    "target_verified": "Die Zielprüfung ist abgeschlossen. Die Änderung wird gespeichert …",
    "before_commit": "Die geprüfte Änderung wird gespeichert …",
    "after_commit": "Die Änderung ist gespeichert. Der sichere Neustart wird vorbereitet …",
    "connection_closed": "Die Wartungsverbindungen sind geschlossen …",
}


def _run_guided_maintenance(root, *, complete):
    from PySide6.QtCore import QThread, Qt, Signal, Slot
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout
    from src.desktop_app.theme import apply_app_theme

    class MaintenanceWorker(QThread):
        phase = Signal(str)

        def __init__(self, parent):
            super().__init__(parent)
            self.failed = False
            self.support_phase = "initialization"
            self.support_error = "unknown"

        def run(self):
            try:
                _perform_maintenance(root, complete=complete, progress=self.report_phase)
            except Exception as error:
                # No exception strings, paths, key material or account content
                # cross the UI boundary. Existing backup/evidence is untouched.
                self.failed = True
                kind = type(error).__name__
                self.support_error = kind if kind in {"UpgradeError", "RuntimeError", "OSError"} else "other"

        def report_phase(self, phase):
            if phase in _PHASE_TEXT:
                self.support_phase = phase
                self.phase.emit(phase)

    class MaintenanceDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Datenbestand aktualisieren")
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            self.setMinimumWidth(480)
            layout = QVBoxLayout(self)
            title = QLabel("Ihre Daten werden sicher aktualisiert")
            layout.addWidget(title)
            self.status = QLabel("Der Datenbestand und die vorhandenen Schlüssel werden geprüft …"
                if not complete else "Die gespeicherten Daten und die Sicherung werden vor dem Neustart erneut geprüft …")
            self.status.setWordWrap(True)
            layout.addWidget(self.status)
            self.progress = QProgressBar()
            self.progress.setRange(0, 0)
            self.progress.setTextVisible(False)
            layout.addWidget(self.progress)
            self.hint = QLabel("Bitte lassen Sie den Mac eingeschaltet. Die Anwendung startet danach neu.")
            self.hint.setWordWrap(True)
            layout.addWidget(self.hint)
            self.close_button = QPushButton("Schließen")
            self.close_button.setVisible(False)
            self.close_button.clicked.connect(self.accept)
            layout.addWidget(self.close_button)
            self.worker = MaintenanceWorker(self)
            self.worker.phase.connect(self.show_phase)
            self.worker.finished.connect(self.finish)

        @Slot(str)
        def show_phase(self, phase):
            if phase in _PHASE_TEXT:
                self.status.setText(_PHASE_TEXT[phase])

        def reject(self):
            if not self.worker.isRunning():
                super().reject()

        def closeEvent(self, event):
            if self.worker.isRunning():
                event.ignore()
            else:
                super().closeEvent(event)

        @Slot()
        def finish(self):
            # QThread.finished precedes complete native-thread unwinding.
            # Never exec with an active migration worker or open connections.
            self.worker.wait()
            if not self.worker.failed:
                try:
                    _restart_maintenance(root, complete=complete, guided=True)
                except Exception:
                    self.worker.failed = True
            self.progress.setVisible(False)
            self.status.setText("Die Aktualisierung konnte nicht abgeschlossen werden. "
                "Ihre vorhandenen Daten, Sicherungen und Wartungsbelege bleiben erhalten. "
                "Bitte wenden Sie sich an die Pilotbetreuung, bevor Sie es erneut versuchen.")
            self.hint.setText("Supporthinweis: Datenaktualisierung – "
                + self.worker.support_phase + " / " + self.worker.support_error
                + ". Abschlussprüfung oder Neustart erforderlich.")
            self.close_button.setVisible(True)

    app = QApplication.instance() or QApplication(sys.argv)
    apply_app_theme(app)
    dialog = MaintenanceDialog()
    dialog.show()
    dialog.worker.start()
    app.exec()
    dialog.worker.wait()
    return 1


def run_product_v7_maintenance(root, *, complete=False, guided=False):
    root = require_product_v7_scope(Path(root))
    if guided:
        return _run_guided_maintenance(root, complete=complete)
    _perform_maintenance(root, complete=complete, progress=lambda boundary:
        print("Wartung: " + boundary, file=sys.stderr, flush=True))
    _restart_maintenance(root, complete=complete)
