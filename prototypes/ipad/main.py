"""Separate synthetic iPad feasibility probe; never imports product startup."""
from pathlib import Path
import sqlite3
import sys

DEMO_COMPETENCIES = (
    "Test: Ich erkenne Zahlen.",
    "Test: Ich lese kurze Wörter.",
    "Test: Ich arbeite mit anderen zusammen.",
)
TOKENS = ("--", "-", "+", "++")
APPLICATION_ID = 0x4A4B4950


class DemoRepository:
    def __init__(self, path: Path):
        path = Path(path)
        if path.is_symlink() or not path.parent.is_dir():
            raise ValueError("Ungültiger Testpfad")
        if path.exists():
            # Existing files are inspected without any write access.
            with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
                    raise ValueError("Fremde Datenbank abgewiesen")
        else:
            descriptor = path.open("xb")
            descriptor.close()
            path.chmod(0o600)
            with sqlite3.connect(path) as db:
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute("CREATE TABLE demo_ratings (competency INTEGER PRIMARY KEY, rating TEXT NOT NULL)")
        self.path = path

    def read(self):
        with sqlite3.connect(self.path) as db:
            return dict(db.execute("SELECT competency, rating FROM demo_ratings"))

    def save(self, selections):
        if set(selections) != set(range(len(DEMO_COMPETENCIES))):
            raise ValueError("Bitte alle Testkompetenzen auswählen")
        if any(value not in TOKENS for value in selections.values()):
            raise ValueError("Ungültige Entwicklungsstufe")
        with sqlite3.connect(self.path) as db:
            db.executemany("INSERT OR REPLACE INTO demo_ratings VALUES (?, ?)", selections.items())


def prototype_data_root():
    from PySide6.QtCore import QStandardPaths
    location = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    if not location:
        raise ValueError("Kein eigener App-Datenordner verfügbar")
    root = Path(location) / "synthetic-ipad-probe"
    if root.is_symlink():
        raise ValueError("Verlinkter Testordner abgewiesen")
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_window(repository):
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QScrollArea
    window = QWidget()
    window.setWindowTitle("Jenaplan – iPad-Test")
    layout = QVBoxLayout(window)
    layout.addWidget(QLabel("iPad-Machbarkeitstest\nNur erfundene Testdaten · keine App-Verschlüsselung"))
    body = QWidget()
    fields = QVBoxLayout(body)
    inputs = []
    stored = repository.read()
    for index, text in enumerate(DEMO_COMPETENCIES):
        label = QLabel(text)
        label.setWordWrap(True)
        fields.addWidget(label)
        choice = QComboBox()
        choice.addItem("Bitte auswählen", None)
        for token in TOKENS:
            choice.addItem(token, token)
        choice.setMinimumHeight(44)
        choice.setCurrentIndex(choice.findData(stored.get(index)))
        fields.addWidget(choice)
        inputs.append(choice)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(body)
    layout.addWidget(scroll)
    status = QLabel("Auswahl speichern und App erneut öffnen, um Persistenz zu prüfen.")
    status.setWordWrap(True)
    button = QPushButton("Testauswahl speichern")
    button.setMinimumHeight(44)

    def save():
        try:
            repository.save({i: field.currentData() for i, field in enumerate(inputs)})
        except ValueError as error:
            status.setText(str(error))
        except sqlite3.Error:
            status.setText("Testauswahl konnte nicht gespeichert werden.")
        else:
            status.setText("Testauswahl lokal gespeichert.")

    button.clicked.connect(save)
    layout.addWidget(button)
    layout.addWidget(status)
    window.resize(700, 600)
    return window


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setOrganizationName("JenaplanPrototype")
    app.setApplicationName("iPadSyntheticProbe")
    window = build_window(DemoRepository(prototype_data_root() / "demo.sqlite"))
    window.show()
    sys.exit(app.exec())
