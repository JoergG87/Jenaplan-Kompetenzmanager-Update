"""Calm first-steps orientation inside the existing shell stack."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.app_preferences import ONBOARDING_BASE_STEP_COUNT
from src.desktop_app.components import (
    PageHeader,
    configure_button,
    stabilize_message_box_buttons,
)
from src.desktop_app.theme import create_card, set_label_style


@dataclass(frozen=True)
class OnboardingStatusItem:
    """One aggregate status row without names or domain content."""

    key: str
    label: str
    configured: bool | None


@dataclass(frozen=True)
class OnboardingStatusProjection:
    """Small aggregate setup projection for first-steps orientation."""

    group_configured: bool | None = None
    course_configured: bool | None = None
    timetable_configured: bool | None = None
    children_configured: bool | None = None
    backup_configured: bool | None = None

    def item(self, key: str, label: str) -> OnboardingStatusItem:
        value = {
            "group": self.group_configured,
            "course": self.course_configured,
            "timetable": self.timetable_configured,
            "children": self.children_configured,
            "backup": self.backup_configured,
        }.get(key)
        return OnboardingStatusItem(key, label, value)


@dataclass(frozen=True)
class OnboardingAction:
    """A navigation action to an existing shell destination."""

    label: str
    target: str


@dataclass(frozen=True)
class OnboardingStep:
    """Visible copy and optional navigation for one onboarding step."""

    title: str
    body: str
    bullets: tuple[str, ...] = ()
    actions: tuple[OnboardingAction, ...] = ()
    status_items: tuple[tuple[str, str], ...] = ()
    primary_label: str | None = None


ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        "Willkommen & sicher starten",
        (
            "Willkommen im Jenaplan-Kompetenzmanager. Deine pädagogischen Daten "
            "bleiben lokal auf diesem Mac."
        ),
        (
            "Das App-Passwort schützt den Zugang.",
            "Fachdaten und verwaltete Dokumente werden verschlüsselt gespeichert.",
            "Bewahre deine Recovery-Codes getrennt vom Mac auf.",
        ),
    ),
    OnboardingStep(
        "Deine Arbeitsgrundlage ist vorbereitet",
        (
            "Schuljahr 2026/27 und das Entwicklungsbuch mit 331 Kompetenzen "
            "sind bereits eingerichtet."
        ),
        (
            "Du musst keinen Katalog importieren oder konfigurieren.",
            "Selbst- und Sozialkompetenz sowie Arbeits- und Lernkompetenz sind immer verfügbar.",
            "Diese überfachliche Entwicklung ist von Unterrichtsfächern getrennt.",
        ),
    ),
    OnboardingStep(
        "Unterricht organisieren",
        (
            "Lege in den vorhandenen Bereichen deine Stammgruppen und Kurse an. "
            "Kursverbünde und Stundenplan kannst du bei Bedarf ergänzen."
        ),
        (
            "Ein vollständiger Stundenplan ist keine Voraussetzung zum Weiterarbeiten.",
            "Die Statushinweise sind nur eine Orientierung und blockieren keinen Schritt.",
        ),
        (
            OnboardingAction("Stammdaten öffnen", "master_data"),
            OnboardingAction("Stundenplan öffnen", "settings_timetable"),
        ),
        (
            ("group", "Stammgruppe"),
            ("course", "Kurs"),
            ("timetable", "Stundenplan"),
        ),
    ),
    OnboardingStep(
        "Kinder einrichten und dokumentieren",
        (
            "Lege Kinder an und pflege die relevanten Unterrichtsfächer direkt "
            "beim jeweiligen Kind."
        ),
        (
            "Überfachliche Entwicklung bleibt unabhängig von der Fachauswahl verfügbar.",
            "Erfasse eine erste Beobachtung; fehlende Dokumentation ist kein negativer Status.",
            "Das Kompetenz-Cockpit hilft später bei der Einordnung dokumentierter Entwicklung.",
        ),
        (OnboardingAction("Schüler öffnen", "students"),),
        (("children", "Schüler"),),
    ),
    OnboardingStep(
        "Daten sichern und loslegen",
        (
            "Erstelle auf der Datensicherungsseite ein verschlüsseltes "
            "`.jkmebackup` und bewahre deine Recovery-Codes getrennt auf."
        ),
        (
            "Recovery-Codes sind der normale erste Wiederherstellungsweg.",
            "Ein betreuter Support-Reset ist nur möglich, solange die geschützte lokale Installation vollständig verfügbar ist.",
            "Erste Schritte kannst du später in den Einstellungen erneut öffnen.",
        ),
        (OnboardingAction("Datensicherung öffnen", "settings_backup_restore"),),
        (("backup", "Backup"),),
        primary_label="Erste Schritte abschließen",
    ),
)


class OnboardingScreen(QWidget):
    """Render onboarding steps and emit shell-owned commands."""

    next_requested = Signal()
    back_requested = Signal()
    skip_confirmed = Signal()
    finish_requested = Signal()
    navigation_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("OnboardingScreen")
        self.current_step = 0
        self.status_projection = OnboardingStatusProjection()
        self.display_name: str | None = None
        self.pilot_mode = False
        self.status_grid = QGridLayout()
        self.bullet_layout = QVBoxLayout()
        self.action_layout = QHBoxLayout()
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("OnboardingScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        self.header = PageHeader("Erste Schritte", "Eine kurze Orientierung für den Start")
        layout.addWidget(self.header)
        self.card = create_card()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(14)
        self.step_label = QLabel("")
        self.step_label.setTextFormat(Qt.TextFormat.PlainText)
        set_label_style(self.step_label, "small")
        card_layout.addWidget(self.step_label)
        self.title_label = QLabel("")
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.title_label.setWordWrap(True)
        set_label_style(self.title_label, "screen_title")
        card_layout.addWidget(self.title_label)
        self.body_label = QLabel("")
        self.body_label.setTextFormat(Qt.TextFormat.PlainText)
        self.body_label.setWordWrap(True)
        set_label_style(self.body_label, "muted")
        card_layout.addWidget(self.body_label)
        card_layout.addLayout(self.bullet_layout)
        self.status_container = QFrame()
        self.status_container.setObjectName("AppPanel")
        status_layout = QVBoxLayout(self.status_container)
        status_title = QLabel("Status")
        status_title.setTextFormat(Qt.TextFormat.PlainText)
        set_label_style(status_title, "card_title")
        status_layout.addWidget(status_title)
        status_layout.addLayout(self.status_grid)
        card_layout.addWidget(self.status_container)
        card_layout.addLayout(self.action_layout)
        layout.addWidget(self.card)
        footer = QHBoxLayout()
        self.skip_button = QPushButton("Erste Schritte überspringen")
        configure_button(self.skip_button, "quiet", "Erste Schritte überspringen")
        self.skip_button.clicked.connect(self._confirm_skip)
        footer.addWidget(self.skip_button)
        footer.addStretch(1)
        self.back_button = QPushButton("Zurück")
        configure_button(self.back_button, "secondary", "Vorheriger Schritt")
        self.back_button.clicked.connect(self.back_requested)
        footer.addWidget(self.back_button)
        self.next_button = QPushButton("Weiter")
        configure_button(self.next_button, "primary", "Nächster Schritt")
        self.next_button.clicked.connect(self._primary_clicked)
        self.next_button.setDefault(True)
        footer.addWidget(self.next_button)
        layout.addLayout(footer)
        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.render()

    def set_context(
        self,
        *,
        step: int,
        display_name: str | None,
        status_projection: OnboardingStatusProjection,
        pilot_mode: bool = False,
    ) -> None:
        self.pilot_mode = bool(pilot_mode)
        step_count = self.step_count
        self.current_step = max(0, min(step, step_count - 1))
        self.display_name = display_name
        self.status_projection = status_projection
        self.render()

    def render(self) -> None:
        step = self.steps[self.current_step]
        self.step_label.setText(
            f"Schritt {self.current_step + 1} von {self.step_count}"
        )
        title = step.title
        if self.current_step == 0 and self.display_name:
            title = f"Willkommen, {self.display_name}"
        self.title_label.setText(title)
        self.body_label.setText(step.body)
        self._render_bullets(step.bullets)
        self._render_status(step.status_items)
        self._render_actions(step.actions)
        self.back_button.setEnabled(self.current_step > 0)
        self.next_button.setText(
            step.primary_label
            or ("Abschließen" if self.current_step == self.step_count - 1 else "Weiter")
        )
        self.next_button.setAccessibleName(self.next_button.text())

    def _render_bullets(self, bullets: tuple[str, ...]) -> None:
        self._clear_layout(self.bullet_layout)
        for bullet in bullets:
            row = QLabel(f"• {bullet}")
            row.setTextFormat(Qt.TextFormat.PlainText)
            row.setWordWrap(True)
            set_label_style(row, "body")
            self.bullet_layout.addWidget(row)

    def _render_status(self, items: tuple[tuple[str, str], ...]) -> None:
        self._clear_layout(self.status_grid)
        self.status_container.setVisible(bool(items))
        for row_index, (key, label) in enumerate(items):
            item = self.status_projection.item(key, label)
            name = QLabel(item.label)
            name.setTextFormat(Qt.TextFormat.PlainText)
            name.setWordWrap(True)
            set_label_style(name, "body")
            state = QLabel(self._status_label(item.key, item.configured))
            state.setTextFormat(Qt.TextFormat.PlainText)
            state.setWordWrap(True)
            set_label_style(state, "muted")
            self.status_grid.addWidget(name, row_index, 0)
            self.status_grid.addWidget(state, row_index, 1)

    def _render_actions(self, actions: tuple[OnboardingAction, ...]) -> None:
        self._clear_layout(self.action_layout)
        for action in actions:
            button = QPushButton(action.label)
            configure_button(button, "secondary", action.label)
            button.clicked.connect(
                lambda _checked=False, target=action.target: self.navigation_requested.emit(
                    target
                )
            )
            self.action_layout.addWidget(button)
        self.action_layout.addStretch(1)

    def _primary_clicked(self) -> None:
        if self.current_step == self.step_count - 1:
            self.finish_requested.emit()
            return
        self.next_requested.emit()

    @property
    def steps(self) -> tuple[OnboardingStep, ...]:
        return ONBOARDING_STEPS

    @property
    def step_count(self) -> int:
        return ONBOARDING_BASE_STEP_COUNT

    def _confirm_skip(self) -> None:
        if self._skip_confirmation_accepted():
            self.skip_confirmed.emit()

    def _skip_confirmation_accepted(self) -> bool:
        message, skip = self._skip_confirmation_message()
        message.exec()
        accepted = message.clickedButton() is skip
        message.deleteLater()
        return accepted

    def _skip_confirmation_message(self) -> tuple[QMessageBox, object]:
        message = QMessageBox(self)
        message.setWindowTitle("Erste Schritte überspringen")
        message.setText(
            "Du kannst die Orientierung später in den Einstellungen erneut öffnen.\n\n"
            "Erste Schritte jetzt überspringen?"
        )
        skip = message.addButton(
            "Erste Schritte überspringen",
            QMessageBox.ButtonRole.AcceptRole,
        )
        keep = message.addButton("Weiter ansehen", QMessageBox.ButtonRole.RejectRole)
        configure_button(skip, "secondary", "Erste Schritte überspringen")
        configure_button(keep, "primary", "Weiter ansehen")
        message.setDefaultButton(keep)
        message.setEscapeButton(keep)
        stabilize_message_box_buttons(message, (skip, keep))
        return message, skip

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _status_label(key: str, value: bool | None) -> str:
        if value is True:
            if key == "backup":
                return "Sicherungsdatei gefunden – bitte prüfen"
            return "Bereits eingerichtet"
        if value is False:
            return "Noch offen"
        return "Nicht geprüft"

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
