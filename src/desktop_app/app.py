"""Main window for the experimental PySide6 desktop app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.sqlite_store import SQLITE_SPIKE_PATH
from src.desktop_app.new_student_dialog import NewStudentDialog
from src.desktop_app.student_adapter import StudentDesktopAdapter
from src.desktop_app.student_list_view import StudentListView


class JenaplanDesktopApp(QMainWindow):
    """Minimal PySide6 adapter for student creation."""

    def __init__(self, database_path: Path = SQLITE_SPIKE_PATH) -> None:
        super().__init__()
        self.adapter = StudentDesktopAdapter(database_path)
        self.setWindowTitle("Jenaplan Kompetenzmanager")
        self.resize(900, 560)
        self._build()
        self.refresh_students()

    def _build(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        header = QHBoxLayout()
        title = QLabel("Jenaplan Kompetenzmanager")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        new_student_button = QPushButton("+ Schüler")
        new_student_button.clicked.connect(self.open_new_student_dialog)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(new_student_button)
        layout.addLayout(header)

        self.student_list = StudentListView()
        layout.addWidget(self.student_list)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setCentralWidget(central)

    def refresh_students(self) -> None:
        """Refresh visible rows from SQLite through the adapter."""
        students = self.adapter.list_students()
        self.student_list.set_students(students)
        self.status_label.setText(f"{len(students)} Schüler")

    def open_new_student_dialog(self) -> None:
        """Open the new-student dialog."""
        dialog = NewStudentDialog(self.adapter)
        dialog.student_created.connect(self.refresh_students)
        dialog.exec()
