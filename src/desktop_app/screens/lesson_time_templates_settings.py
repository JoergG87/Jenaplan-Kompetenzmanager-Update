"""Teacher-facing teaching times editor; all writes leave through a signal."""
from PySide6.QtCore import QTime, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QPushButton, QSpinBox, QTimeEdit, QVBoxLayout
from src.desktop_app.components import AppCard, InlineMessage, configure_button
from src.desktop_app.view_models.lesson_time_templates_view_model import LessonTimeTemplatesViewModel


class LessonTimeTemplatesSettings(AppCard):
    save_requested = Signal(int, str, str, object)
    reload_requested = Signal()

    def __init__(self):
        super().__init__("default")
        self._model = LessonTimeTemplatesViewModel(())
        self._expected = None
        layout = QVBoxLayout(self)
        note = QLabel("Lege die Unterrichtszeiten deiner Schule fest. Im Stundenplan werden sie einmalig vorgeschlagen. Gespeicherte Stunden bleiben unverändert.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.template_combo = QComboBox()
        self.template_combo.setAccessibleName("Unterrichtszeit auswählen oder hinzufügen")
        self.template_combo.currentIndexChanged.connect(self._select)
        layout.addWidget(self.template_combo)
        form = QFormLayout()
        self.lesson_number = QSpinBox()
        self.lesson_number.setRange(1, 2147483647)
        self.lesson_number.setAccessibleName("Nummer der Unterrichtsstunde")
        form.addRow("Unterrichtsstunde", self.lesson_number)
        self.start_time = QTimeEdit(QTime(0, 0))
        self.end_time = QTimeEdit(QTime(0, 0))
        for widget, label in ((self.start_time, "Beginn"), (self.end_time, "Ende")):
            widget.setDisplayFormat("HH:mm")
            widget.setAccessibleName(label + " der Unterrichtszeit")
            form.addRow(label, widget)
        layout.addLayout(form)
        self.message = InlineMessage()
        layout.addWidget(self.message)
        self.save_button = QPushButton("Unterrichtszeit speichern")
        configure_button(self.save_button, "primary", "Ausgewählte Unterrichtszeit speichern")
        self.save_button.clicked.connect(self._save)
        layout.addWidget(self.save_button)
        self.reload_button = QPushButton("Gespeicherte Zeiten neu laden")
        configure_button(self.reload_button, "secondary", "Gespeicherte Zeiten neu laden und ungespeicherte Eingaben verwerfen")
        self.reload_button.clicked.connect(self.reload_requested)
        layout.addWidget(self.reload_button)
        reload_hint = QLabel("Neu laden verwirft ungespeicherte Eingaben.")
        reload_hint.setWordWrap(True)
        layout.addWidget(reload_hint)
        self.set_view_model(self._model)

    def set_view_model(self, model):
        self._model = model
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("Neue Unterrichtsstunde hinzufügen", None)
        for option in model.templates:
            self.template_combo.addItem(option.label, option.template)
        self.template_combo.blockSignals(False)
        self._select()

    def _select(self):
        self._expected = self.template_combo.currentData()
        self.message.set_message("")
        self.lesson_number.setEnabled(self._expected is None)
        if self._expected is None:
            self.lesson_number.setValue(max((v.lesson_number for v in self._model.templates), default=0) + 1)
            self.start_time.setTime(QTime(0, 0))
            self.end_time.setTime(QTime(0, 0))
        else:
            self.lesson_number.setValue(self._expected.lesson_number)
            self.start_time.setTime(QTime.fromString(self._expected.start_time, "HH:mm"))
            self.end_time.setTime(QTime.fromString(self._expected.end_time, "HH:mm"))

    def _save(self):
        self.save_requested.emit(self.lesson_number.value(), self.start_time.time().toString("HH:mm"),
                                 self.end_time.time().toString("HH:mm"), self._expected)

    def show_error(self, message):
        self.message.set_message(message, tone="warning")
