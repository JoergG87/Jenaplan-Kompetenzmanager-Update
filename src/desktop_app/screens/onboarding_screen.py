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

from src.core.app_preferences import ONBOARDING_STEP_COUNT
from src.desktop_app.components import PageHeader, configure_button
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

    documentation_subjects_configured: bool | None = None
    timetable_configured: bool | None = None
    organization_configured: bool | None = None
    children_configured: bool | None = None

    def item(self, key: str, label: str) -> OnboardingStatusItem:
        value = {
            "documentation_subjects": self.documentation_subjects_configured,
            "timetable": self.timetable_configured,
            "organization": self.organization_configured,
            "children": self.children_configured,
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


ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        "Willkommen",
        (
            "Die App hilft dir, Beobachtungen zu dokumentieren, Lernstände zu "
            "überblicken und Gespräche oder Berichte vorzubereiten."
        ),
        (
            "Deine Arbeitsdaten bleiben lokal auf diesem Gerät.",
            "Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.",
        ),
    ),
    OnboardingStep(
        "Arbeitsgrundlage prüfen",
        "Diese Bereiche legen fest, wie du später dokumentierst und sortierst.",
        (
            "Fächer für die Dokumentation auswählen.",
            "Stundenplan prüfen.",
            "Vorhandene Stammgruppen, Kurse und Organisationsdaten ansehen.",
        ),
        (
            OnboardingAction("Fächer öffnen", "settings_documentation_subjects"),
            OnboardingAction("Stundenplan öffnen", "settings_timetable"),
            OnboardingAction("Stammdaten öffnen", "master_data"),
        ),
        (
            ("documentation_subjects", "Fächer"),
            ("timetable", "Stundenplan"),
            ("organization", "Stammgruppen/Kurse"),
        ),
    ),
    OnboardingStep(
        "Kinder und Zuordnungen",
        (
            "Kinder und ihre Zuordnungen sind die Grundlage, damit Beobachtungen "
            "später an der richtigen Stelle erscheinen."
        ),
        (
            "Nutze die vorhandene Schüler- und Organisationsverwaltung.",
            "Ein Schülerlisten-Import gehört nicht zu diesem Sprint.",
        ),
        (
            OnboardingAction("Schüler öffnen", "students"),
            OnboardingAction("Stammdaten öffnen", "master_data"),
        ),
        (("children", "Kinder"), ("organization", "Zuordnungen")),
    ),
    OnboardingStep(
        "Erste Beobachtung",
        (
            "Wenn ein Kind ausgewählt ist, öffnest du über die vorhandene "
            "Navigation den Beobachtungsdialog."
        ),
        (
            "Es wird nichts automatisch angelegt.",
            "Fachliche Inhalte bleiben vollständig bei dir.",
        ),
        (OnboardingAction("Zu den Schülern", "students"),),
        (("children", "Kinder vorhanden"),),
    ),
    OnboardingStep(
        "Datensicherung und Abschluss",
        (
            "Auf der Datensicherungsseite kannst du lokale Sicherungen bewusst "
            "erstellen und prüfen."
        ),
        (
            "Es startet kein automatisches Backup.",
            "Erste Schritte kannst du später in den Einstellungen erneut öffnen.",
        ),
        (OnboardingAction("Datensicherung öffnen", "settings_backup_restore"),),
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
    ) -> None:
        self.current_step = max(0, min(step, ONBOARDING_STEP_COUNT - 1))
        self.display_name = display_name
        self.status_projection = status_projection
        self.render()

    def render(self) -> None:
        step = ONBOARDING_STEPS[self.current_step]
        self.step_label.setText(
            f"Schritt {self.current_step + 1} von {ONBOARDING_STEP_COUNT}"
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
            "Abschließen"
            if self.current_step == ONBOARDING_STEP_COUNT - 1
            else "Weiter"
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
            state = QLabel(self._status_label(item.configured))
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
        if self.current_step == ONBOARDING_STEP_COUNT - 1:
            self.finish_requested.emit()
            return
        self.next_requested.emit()

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
        message.setDefaultButton(keep)
        return message, skip

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _status_label(value: bool | None) -> str:
        if value is True:
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
