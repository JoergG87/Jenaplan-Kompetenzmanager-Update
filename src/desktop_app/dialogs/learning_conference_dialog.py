"""Conversation-oriented workspace for persistent learning-conference drafts."""

from __future__ import annotations

from src.desktop_app.window_policy import exec_owned_dialog

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime
import textwrap

from PySide6.QtCore import QDate, QEvent, QEventLoop, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QKeyEvent, QKeySequence, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import (
    AppCard,
    DialogHeader,
    FilterBar,
    InlineMessage,
    SearchField,
    SectionHeader,
    StatusBadge,
    SubjectAccentMarker,
    Toast,
    configure_button,
    create_confirmation_message,
)
from src.desktop_app.motion import (
    MotionDialog,
    animate_feedback,
    animate_save_confirmation,
)
from src.desktop_app.theme import set_label_style, subject_accent_icon
from src.desktop_app.view_models.learning_conference_view_model import (
    LearningConferenceCompletionErrorViewModel,
    LearningConferenceCompetencyViewModel,
    LearningConferenceDraftViewModel,
    LearningConferenceEvidenceViewModel,
    LearningConferencePreparationViewModel,
    LearningConferencePdfArtifactViewModel,
    LearningConferenceRevisionStatusViewModel,
    LearningConferenceRevisionViewModel,
)


CHART_OPTIONS = (
    ("documentation_coverage", "Dokumentationsabdeckung"),
    ("competency_timeline", "Kompetenzentwicklung"),
    ("observation_timeline", "Zeitachse ausgewählter Beobachtungsbelege"),
)

PHASES = (
    ("goal", "Gesprächsziel", "Gesprächsrahmen und bewusste Schwerpunkte festlegen."),
    ("strengths", "Was gelingt dem Kind?", "Stärken vorbereiten und den Rückblick des Kindes festhalten."),
    ("development", "Welche Entwicklung sehen wir?", "Lehrkraftsicht und gemeinsam betrachtete Entwicklungsfelder unterscheiden."),
    ("goals", "Woran möchten wir gemeinsam arbeiten?", "Vorbereitete Ideen und gemeinsam formulierte Ziele getrennt bearbeiten."),
    ("evidence", "Welche Beispiele stützen unsere Einschätzung?", "Kompetenzen, Beobachtungsbelege und Gesprächsbilder bewusst auswählen."),
    ("agreements", "Welche Unterstützung und Vereinbarungen treffen wir?", "Unterstützung und Vereinbarungen im bearbeitbaren Entwurf festhalten."),
)

PHASE_GROUPS = (
    ("Vorbereitung", ("goal", "evidence")),
    ("Im Gespräch", ("strengths", "development")),
    ("Vereinbarungen & Abschluss", ("goals", "agreements")),
)

ROLE_PREPARATION = "Nur für die Vorbereitung"
ROLE_CONVERSATION = "Im Gespräch bearbeiten"
ROLE_AGREEMENT = "Im Entwurf als Vereinbarung festgehalten"


def _phase_title(key: str) -> str:
    return next(title for phase_key, title, _description in PHASES if phase_key == key)


def _phase_group_title(key: str) -> str:
    return next(title for title, keys in PHASE_GROUPS if key in keys)


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


def _label(text: str, role: str | None = None) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if role:
        set_label_style(label, role)
    return label


def _frame(layout: QLayout, name: str = "LearningConferenceCard") -> QFrame:
    frame = QFrame()
    frame.setObjectName(name)
    frame.setLayout(layout)
    return frame


def _format_saved_at(value: str) -> str:
    if not value:
        return "Noch nicht gespeichert"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return f"Zuletzt gespeichert: {parsed.astimezone().strftime('%d.%m.%Y, %H:%M')}"
    except ValueError:
        return "Entwurf gespeichert"


class _CollapsibleSection(QWidget):
    """Immediate disclosure with central, reduced-motion-aware feedback."""

    def __init__(
        self,
        title: str,
        content: QWidget,
        *,
        expanded: bool = False,
        indent: int = 0,
        on_expand: Callable[[], None] | None = None,
        feedback_on_expand: bool = True,
    ) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(indent, 0, 0, 0)
        layout.setSpacing(2)
        self.button = QToolButton()
        self.button.setObjectName("LearningConferenceHierarchyButton")
        self.button.setText(title)
        self.button.setCheckable(True)
        self.button.setChecked(expanded)
        self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.button.setAccessibleName(title)
        self.content = content
        self._on_expand = on_expand
        self._feedback_on_expand = feedback_on_expand
        self.content.setVisible(expanded)
        self.button.installEventFilter(self)
        self.button.toggled.connect(self._toggle)
        layout.addWidget(self.button)
        layout.addWidget(content)

    def _toggle(self, expanded: bool) -> None:
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        if expanded and self._on_expand is not None:
            self._on_expand()
        self.content.setVisible(expanded)
        if expanded and self._feedback_on_expand:
            animate_feedback(self.button, key="learning_conference_disclosure")

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if (
            watched is self.button
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            self.button.toggle()
            event.accept()
            return True
        return super().eventFilter(watched, event)


class LearningConferencePhaseNavigation(QFrame):
    """Six direct conversation anchors grouped without completion semantics."""

    phase_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("LearningConferencePhaseNavigation")
        self.setAccessibleName("Arbeitsbereiche des Lernentwicklungsgesprächs")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._keys = [key for _group_title, keys in PHASE_GROUPS for key in keys]
        self._buttons: dict[str, QPushButton] = {}
        self._states = {key: "Noch leer" for key in self._keys}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(7)
        heading = _label("ARBEITSBEREICHE", "field_label")
        layout.addWidget(heading)
        button_index = 0
        for group_title, keys in PHASE_GROUPS:
            group_label = _label(group_title.upper(), "small")
            group_label.setObjectName("LearningConferenceNavigationGroupLabel")
            layout.addWidget(group_label)
            for key in keys:
                button = QPushButton()
                button.setObjectName(f"LearningConferencePhaseButton_{key}")
                button.setCheckable(True)
                button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setProperty("phaseCurrent", False)
                button.installEventFilter(self)
                self._group.addButton(button, button_index)
                button_index += 1
                self._buttons[key] = button
                button.clicked.connect(lambda _checked=False, phase_key=key: self.phase_requested.emit(phase_key))
                layout.addWidget(button)
        layout.addStretch(1)
        self.set_current("goal")

    def current_key(self) -> str:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return "goal"

    def set_current(self, key: str) -> None:
        if key not in self._buttons:
            raise ValueError(f"Unbekannte LEG-Phase: {key}")
        self._buttons[key].setChecked(True)
        self._refresh_labels()

    def set_content_state(self, key: str, has_content: bool) -> None:
        self._states[key] = "Inhalt vorhanden" if has_content else "Noch leer"
        self._refresh_labels()

    def button_for(self, key: str) -> QPushButton:
        return self._buttons[key]

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.KeyPress and watched in self._buttons.values():
            key_event = event
            if isinstance(key_event, QKeyEvent):
                if key_event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                    self._move_focus(-1 if key_event.key() == Qt.Key.Key_Up else 1)
                    return True
                if key_event.key() in (Qt.Key.Key_Home, Qt.Key.Key_End):
                    target = self._keys[0] if key_event.key() == Qt.Key.Key_Home else self._keys[-1]
                    self._activate(target)
                    return True
        return super().eventFilter(watched, event)

    def _move_focus(self, direction: int) -> None:
        current = self.current_key()
        target_index = max(0, min(len(self._keys) - 1, self._keys.index(current) + direction))
        self._activate(self._keys[target_index])

    def _activate(self, key: str) -> None:
        self.set_current(key)
        self._buttons[key].setFocus()
        self.phase_requested.emit(key)

    def _refresh_labels(self) -> None:
        current = self.current_key()
        for key in self._keys:
            title = _phase_title(key)
            state = "Aktuell" if key == current else self._states[key]
            button = self._buttons[key]
            navigation_title = {
                "evidence": "Belege vorbereiten",
                "agreements": "Unterstützung & Vereinbarungen",
            }.get(key, title)
            wrapped_title = "\n".join(textwrap.wrap(navigation_title, width=22))
            context_hint = "\nIm Gespräch bei Bedarf" if key == "evidence" else ""
            button.setText(f"{wrapped_title}{context_hint}\n{state}")
            button.setAccessibleName(f"{_phase_group_title(key)}, {title}, {state}")
            button.setAccessibleDescription(
                "Öffnet diesen Gesprächsanker direkt. Pfeil hoch und runter wechseln zwischen den Ankern."
            )
            button.setProperty("phaseCurrent", key == current)
            button.style().unpolish(button)
            button.style().polish(button)


class LearningConferenceCloseDialog(MotionDialog):
    """Three-way decision for closing a dirty LEG workspace."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.choice = "continue"
        self.setObjectName("LearningConferenceCloseDialog")
        self.setWindowTitle("Ungespeicherte Änderungen")
        self.setModal(True)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(DialogHeader(
            "Ungespeicherte Änderungen",
            "Lernentwicklungsgespräch",
            "Möchtest du den bearbeitbaren Entwurf vor dem Schließen speichern?",
            icon_name="conference",
            context_role="learning_conference",
        ))
        note = InlineMessage(
            "Änderungen verwerfen entfernt nur Eingaben seit dem letzten Speichern. Der gespeicherte Draft bleibt erhalten.",
            tone="warning",
        )
        layout.addWidget(note)
        actions = QHBoxLayout()
        actions.addStretch(1)
        continue_button = QPushButton("Weiter bearbeiten")
        discard_button = QPushButton("Änderungen verwerfen")
        save_button = QPushButton("Entwurf speichern")
        configure_button(continue_button, "quiet", "Weiter bearbeiten")
        configure_button(discard_button, "secondary", "Änderungen verwerfen")
        configure_button(save_button, "primary", "Entwurf speichern und schließen")
        continue_button.setDefault(True)
        continue_button.setAutoDefault(True)
        discard_button.setAutoDefault(False)
        save_button.setAutoDefault(False)
        continue_button.clicked.connect(self.reject)
        discard_button.clicked.connect(lambda: self._finish("discard"))
        save_button.clicked.connect(lambda: self._finish("save"))
        actions.addWidget(continue_button)
        actions.addWidget(discard_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        continue_button.setFocus()

    def _finish(self, choice: str) -> None:
        self.choice = choice
        self.accept()

    @classmethod
    def ask(cls, parent: QWidget) -> str:
        dialog = cls(parent)
        return dialog.choice if exec_owned_dialog(dialog) == QDialog.DialogCode.Accepted else "continue"


class LearningConferenceDraftSelectionDialog(MotionDialog):
    """Choose an existing LEG draft or deliberately start an independent one."""

    def __init__(
        self,
        drafts: Sequence[LearningConferenceDraftViewModel],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("LearningConferenceDraftSelectionDialog")
        self.setWindowTitle("Lernentwicklungsgespräch auswählen")
        self.setMinimumSize(660, 420)
        self.selected_draft: LearningConferenceDraftViewModel | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(DialogHeader(
            "Entwurf weiterbearbeiten",
            "Lernentwicklungsgespräch",
            "Wähle einen gespeicherten Stand oder lege einen neuen bearbeitbaren Entwurf an.",
            icon_name="conference",
            context_role="learning_conference",
        ))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(10)
        for draft in drafts:
            card = AppCard("default")
            card.setObjectName(f"LearningConferenceDraftChoice_{draft.learning_conference_draft_id}")
            card.setAccessibleDescription(
                f"Technische Entwurfskennung {draft.learning_conference_draft_id}"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 14, 16, 14)
            text = QVBoxLayout()
            date_text = (
                draft.conference_date.strftime("%d.%m.%Y")
                if draft.conference_date else "Gesprächsdatum offen"
            )
            title = _label(date_text, "card_title")
            status = _label("Status: Entwurf", "body")
            teacher = _label(draft.responsible_teacher or "Lehrkraft offen", "body")
            saved = _label(_format_saved_at(draft.updated_at), "subtle")
            context = (
                f"Zeitraum {draft.period_start.strftime('%d.%m.%Y')} bis {draft.period_end.strftime('%d.%m.%Y')}"
                if draft.period_start and draft.period_end else "Gesprächszeitraum offen"
            )
            text.addWidget(title)
            text.addWidget(status)
            text.addWidget(teacher)
            text.addWidget(_label(context, "small"))
            text.addWidget(saved)
            row.addLayout(text, 1)
            open_button = QPushButton("Öffnen")
            configure_button(open_button, "secondary", f"Entwurf vom {date_text} öffnen")
            open_button.clicked.connect(lambda _checked=False, item=draft: self._choose(item))
            row.addWidget(open_button)
            content_layout.addWidget(card)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        actions = QHBoxLayout()
        cancel_button = QPushButton("Abbrechen")
        new_button = QPushButton("Neues LEG")
        configure_button(cancel_button, "quiet", "Auswahl abbrechen")
        configure_button(new_button, "primary", "Neues eigenständiges LEG anlegen")
        cancel_button.clicked.connect(self.reject)
        new_button.clicked.connect(lambda: self._choose(None))
        actions.addWidget(cancel_button)
        actions.addStretch(1)
        actions.addWidget(new_button)
        layout.addLayout(actions)

    def _choose(self, draft: LearningConferenceDraftViewModel | None) -> None:
        self.selected_draft = draft
        self.accept()

    @classmethod
    def choose(
        cls,
        drafts: Sequence[LearningConferenceDraftViewModel],
        parent: QWidget,
    ) -> tuple[bool, LearningConferenceDraftViewModel | None]:
        dialog = cls(drafts, parent)
        accepted = exec_owned_dialog(dialog) == QDialog.DialogCode.Accepted
        return accepted, dialog.selected_draft


class LearningConferenceRevisionHistoryDialog(MotionDialog):
    """Choose one immutable LCV without exposing persistence or live data."""

    def __init__(
        self,
        status: LearningConferenceRevisionStatusViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.selected_revision_id = ""
        self.setWindowTitle("LEG-Abschlussrevisionen")
        self.setMinimumSize(650, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(DialogHeader(
            "Abschlussrevisionen",
            "Lernentwicklungsgespräch",
            "Unveränderliche, historisch reproduzierbare Gesprächsstände.",
            icon_name="conference",
            context_role="learning_conference",
        ))
        for revision in status.revisions:
            card = AppCard("default")
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            text = QVBoxLayout()
            text.addWidget(_label(
                f"Revision {revision.revision_number} · {revision.status_label}",
                "card_title",
            ))
            text.addWidget(_label(
                f"{revision.completed_at_text} · {revision.completed_by_display_name}",
                "small",
            ))
            row.addLayout(text, 1)
            button = QPushButton("Öffnen")
            configure_button(button, "secondary", f"Revision {revision.revision_number} öffnen")
            button.clicked.connect(
                lambda _checked=False, value=revision.learning_conference_revision_id: self._choose(value)
            )
            row.addWidget(button)
            layout.addWidget(card)
        layout.addStretch(1)
        close_button = QPushButton("Schließen")
        configure_button(close_button, "quiet", "Revisionshistorie schließen")
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignLeft)

    def _choose(self, revision_id: str) -> None:
        self.selected_revision_id = revision_id
        self.accept()

    @classmethod
    def choose(
        cls,
        status: LearningConferenceRevisionStatusViewModel,
        parent: QWidget,
    ) -> str:
        dialog = cls(status, parent)
        return (
            dialog.selected_revision_id
            if exec_owned_dialog(dialog) == QDialog.DialogCode.Accepted
            else ""
        )


class LearningConferenceRevisionDialog(MotionDialog):
    """Read-only view whose only fachliche source is one verified LCV snapshot."""

    pdf_requested = Signal(str)
    pdf_open_requested = Signal(str)

    def __init__(
        self,
        revision: LearningConferenceRevisionViewModel,
        parent: QWidget | None = None,
        artifact: LearningConferencePdfArtifactViewModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.revision = revision
        self.artifact = artifact
        self.setObjectName("LearningConferenceRevisionDialog")
        self.setWindowTitle(
            f"LEG-Abschluss · Revision {revision.revision_number}"
        )
        self.resize(900, 760)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)
        header = DialogHeader(
            f"{revision.student_name} · Revision {revision.revision_number}",
            "Abgeschlossenes Lernentwicklungsgespräch",
            f"{revision.completed_at_text} · {revision.status_label}",
            icon_name="conference",
            context_role="learning_conference",
        )
        if revision.status == "completed":
            self.pdf_button = QPushButton("Finales PDF erstellen")
            self.pdf_button.setObjectName("LearningConferenceGenerateFinalPdfButton")
            configure_button(
                self.pdf_button,
                "secondary",
                "Finales PDF ausschließlich aus dieser unveränderlichen LEG-Revision erstellen",
            )
            self.pdf_button.clicked.connect(self._request_pdf_action)
            header.add_action(self.pdf_button)
        root.addWidget(header)
        self.pdf_status = InlineMessage()
        self.pdf_status.setObjectName("LearningConferenceFinalPdfStatus")
        root.addWidget(self.pdf_status)
        if artifact is not None:
            self.apply_pdf_artifact(artifact)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 8, 12)
        layout.setSpacing(10)
        context = AppCard("soft")
        context_layout = QVBoxLayout(context)
        context_layout.addWidget(SectionHeader(
            "Gesprächskontext",
            f"{revision.conference_date_text} · {revision.period_text}",
        ))
        context_layout.addWidget(_label(
            f"Lehrkraft: {revision.responsible_teacher}\n"
            f"Stammgruppe: {revision.group_name or '–'} · Kurs: {revision.course_name or '–'}",
            "body",
        ))
        layout.addWidget(context)
        for title, value in (
            ("Gemeinsame Ziele", revision.goals),
            ("Unterstützungen", revision.support),
            ("Vereinbarungen", revision.agreements),
            ("Zuständigkeiten", revision.responsibilities),
            ("Überprüfungstermin", revision.next_review_date_text),
        ):
            if value and value != "Nicht festgelegt":
                card = AppCard("default")
                card_layout = QVBoxLayout(card)
                card_layout.addWidget(_label(title, "field_label"))
                card_layout.addWidget(_label(value, "body"))
                layout.addWidget(card)
        layout.addWidget(self._list_card(
            "Kompetenzen",
            revision.competency_lines,
            "Keine Kompetenz als Abschlussbezug ausgewählt.",
        ))
        layout.addWidget(self._list_card(
            "Beobachtungsbelege",
            revision.observation_lines,
            "Keine Beobachtung als Abschlussbeleg ausgewählt.",
        ))
        integrity = InlineMessage(
            f"Integrität geprüft · SHA-256 {revision.snapshot_sha256[:12]}… · "
            f"{revision.learning_conference_revision_id}",
            tone="success",
        )
        layout.addWidget(integrity)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        close_button = QPushButton("Schließen")
        configure_button(close_button, "primary", "Abschlussrevision schließen")
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

    def apply_pdf_artifact(
        self,
        artifact: LearningConferencePdfArtifactViewModel,
    ) -> None:
        """Show the verified immutable artifact without exposing storage logic."""
        self.artifact = artifact
        self.pdf_status.set_message(
            f"Finales PDF vorhanden: {artifact.file_name} · "
            f"erstellt {artifact.created_at}",
            tone="success",
        )
        if hasattr(self, "pdf_button"):
            self.pdf_button.setText("Finales PDF anzeigen")
            self.pdf_button.setEnabled(True)
            self.pdf_button.setAccessibleName(
                "Verifiziertes finales PDF dieser LEG-Revision anzeigen"
            )

    def _request_pdf_action(self) -> None:
        if self.artifact is None:
            self.pdf_requested.emit(
                self.revision.learning_conference_revision_id
            )
            return
        self.pdf_open_requested.emit(
            self.artifact.learning_conference_pdf_artifact_id
        )

    def show_pdf_error(self, message: str) -> None:
        self.pdf_status.set_message(message, tone="error")

    @staticmethod
    def _list_card(title: str, values: tuple[str, ...], empty_text: str) -> AppCard:
        card = AppCard("default")
        layout = QVBoxLayout(card)
        layout.addWidget(_label(title, "field_label"))
        layout.addWidget(_label("\n".join(f"• {value}" for value in values) or empty_text, "body"))
        return card


class LearningConferenceDialog(QDialog):
    """Edit one LEG draft in a safe, phase-oriented workspace."""

    save_requested = Signal(object)
    completion_requested = Signal(str)
    revision_open_requested = Signal(str)

    def __init__(
        self,
        preparation: LearningConferencePreparationViewModel,
        parent: QWidget | None = None,
        initial_draft: LearningConferenceDraftViewModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.preparation = preparation
        self._saved_draft = initial_draft
        self._selected_subject_ids = set(initial_draft.subject_ids if initial_draft else ())
        self._selected_cross_topics = set(initial_draft.cross_topic_keys if initial_draft else ())
        self._selected_competency_ids = set(initial_draft.competency_ids if initial_draft else ())
        self._selected_observation_ids = set(initial_draft.observation_ids if initial_draft else ())
        self._selected_chart_types = set(initial_draft.chart_types if initial_draft else ())
        self.subject_checks: dict[str, QCheckBox] = {}
        self.cross_topic_checks: dict[str, QCheckBox] = {}
        self.competency_checks: dict[str, QCheckBox] = {}
        self.competency_models: dict[str, LearningConferenceCompetencyViewModel] = {}
        self.competency_widgets: dict[str, QWidget] = {}
        self.competency_filter_notes: dict[str, QLabel] = {}
        self.competency_sections: dict[str, _CollapsibleSection] = {}
        self.competency_area_sections: list[tuple[str, tuple[str, ...], _CollapsibleSection]] = []
        self.competency_topic_sections: list[tuple[str, tuple[str, ...], _CollapsibleSection]] = []
        self._competency_section_specs: dict[
            str,
            tuple[str, dict[str, list[LearningConferenceCompetencyViewModel]]],
        ] = {}
        self._competency_section_hosts: dict[str, QWidget] = {}
        self._built_competency_sections: set[str] = set()
        self.competency_empty_by_subject: dict[str, QLabel] = {}
        self.evidence_checks: dict[str, QCheckBox] = {}
        self.evidence_widgets: dict[str, QWidget] = {}
        self.evidence_sections: dict[str, _CollapsibleSection] = {}
        self._evidence_section_specs: dict[str, tuple[LearningConferenceEvidenceViewModel, ...]] = {}
        self._evidence_section_hosts: dict[str, QWidget] = {}
        self._built_evidence_sections: set[str] = set()
        self.chart_checks: dict[str, QCheckBox] = {}
        self.text_inputs: dict[str, QTextEdit] = {}
        self.phase_pages: dict[str, QWidget] = {}
        self.phase_scroll_areas: dict[str, QScrollArea] = {}
        self.phase_first_focus: dict[str, QWidget] = {}
        self.phase_built = {key: False for key, _title, _description in PHASES}
        self._phase_builders = {
            "goal": self._phase_goal,
            "strengths": self._phase_strengths,
            "development": self._phase_development,
            "goals": self._phase_goals,
            "evidence": self._phase_evidence,
            "agreements": self._phase_agreements,
        }
        self.evidence_summary_labels: list[QLabel] = []
        self._baseline: LearningConferenceDraftViewModel | None = None
        self._dirty = False
        self._save_pending = False
        self._completion_status: LearningConferenceRevisionStatusViewModel | None = None
        self._close_choice_provider = LearningConferenceCloseDialog.ask
        self.setWindowTitle(f"Lernentwicklungsgespräch · {preparation.student_name}")
        self.setProperty("dialogContext", "learning_conference")
        self.resize(1400, 900)
        self.setMinimumSize(1080, 700)
        self._build()
        self._baseline = self.draft_view_model()
        self._refresh_ui_state()

    @property
    def active_phase_key(self) -> str:
        return self.phase_navigation.current_key()

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.addWidget(self._context_header())
        workspace = QFrame()
        workspace.setObjectName("LearningConferenceWorkspace")
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(10)
        self.phase_navigation = LearningConferencePhaseNavigation()
        self.phase_navigation.phase_requested.connect(self.set_active_phase)
        workspace_layout.addWidget(self.phase_navigation)
        self.phase_stack = QStackedWidget()
        self.phase_stack.setObjectName("LearningConferencePhaseWorkspace")
        for key, _title, _description in PHASES:
            page = QWidget()
            page.setObjectName(f"LearningConferencePhaseContainer_{key}")
            page.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            page.setAccessibleName(
                next(title for phase_key, title, _description in PHASES if phase_key == key)
            )
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            self.phase_pages[key] = page
            self.phase_stack.addWidget(page)
        workspace_layout.addWidget(self.phase_stack, 1)
        root.addWidget(workspace, 1)
        self.validation_message = InlineMessage()
        self.validation_message.setObjectName("LearningConferenceValidationMessage")
        self.validation_message.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root.addWidget(self.validation_message)
        root.addWidget(self._action_bar())
        self.toast = Toast(self)
        self._ensure_phase_built("goal")
        self.set_active_phase("goal", focus=False)

    def _context_header(self) -> QFrame:
        card = AppCard("accent")
        card.setProperty("dialogContextSurface", "learning_conference")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)
        group_course = " · ".join(
            value for value in (self.preparation.group_name, self.preparation.course_name) if value
        ) or (
            self.preparation.membership_status_label
            or "Stammgruppe und Kurs offen"
        )
        self.page_header = DialogHeader(
            "Lernentwicklungsgespräch",
            f"{self.preparation.student_name} · {group_course}",
            "Bearbeitbarer Entwurf mit sechs direkt wählbaren Gesprächsankern.",
            icon_name="conference",
            context_role="learning_conference",
        )
        self.draft_badge = StatusBadge("Bearbeitbarer Entwurf", tone="info")
        self.completion_badge = StatusBadge("Noch nicht abgeschlossen", tone="neutral")
        self.dirty_badge = StatusBadge("Entwurf gespeichert", tone="neutral")
        self.dirty_badge.setObjectName("LearningConferenceDirtyBadge")
        self.page_header.add_action(self.draft_badge)
        self.page_header.add_action(self.completion_badge)
        self.page_header.add_action(self.dirty_badge)
        layout.addWidget(self.page_header)
        meta = QHBoxLayout()
        meta.setSpacing(18)
        self.group_course_label = _label(group_course, "small")
        self.date_context_label = _label("Gesprächsdatum offen", "small")
        self.teacher_context_label = _label("Lehrkraft offen", "small")
        self.phase_context_label = _label("Vorbereitung · Gesprächsziel", "small")
        self.status_label = _label(_format_saved_at(self._saved_draft.updated_at if self._saved_draft else ""), "small")
        for widget in (
            self.group_course_label,
            self.date_context_label,
            self.teacher_context_label,
            self.phase_context_label,
            self.status_label,
        ):
            meta.addWidget(widget)
        meta.addStretch(1)
        layout.addLayout(meta)
        return card

    def _phase_page(self, key: str, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("LearningConferencePhaseScroll")
        scroll.setProperty("phaseKey", key)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        self.phase_scroll_areas[key] = scroll
        return scroll

    def _ensure_phase_built(self, key: str) -> None:
        if self.phase_built[key]:
            return
        is_evidence_phase = key == "evidence"
        if is_evidence_phase:
            self.validation_message.set_message(
                "Kompetenzen und Belege werden für diesen Arbeitsanker vorbereitet …",
                tone="info",
            )
            QApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )
        try:
            content = self._phase_builders[key]()
        finally:
            if is_evidence_phase:
                self.validation_message.set_message("")
        scroll = self._phase_page(key, content)
        page_layout = self.phase_pages[key].layout()
        if page_layout is None:
            raise RuntimeError(f"LEG-Phasencontainer ohne Layout: {key}")
        page_layout.addWidget(scroll)
        self.phase_built[key] = True
        self._connect_phase_updates(key)
        if key == "evidence":
            self._update_filters()

    def _phase_shell(self, key: str) -> tuple[QWidget, QVBoxLayout]:
        _phase_key, title, description = next(phase for phase in PHASES if phase[0] == key)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 18, 24, 32)
        layout.setSpacing(14)
        group_title = _phase_group_title(key)
        if key == "evidence":
            description = f"Vorbereiten · im Gespräch bei Bedarf. {description}"
        heading = SectionHeader(f"{group_title} · {title}", description)
        heading.title_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        heading.title_label.setAccessibleName(f"{group_title}, {title}")
        self.phase_first_focus.setdefault(key, heading.title_label)
        layout.addWidget(heading)
        return content, layout

    def _phase_goal(self) -> QWidget:
        content, layout = self._phase_shell("goal")
        draft = self._saved_draft
        today = date.today()
        self.period_start = self._optional_date_edit(draft.period_start if draft else None, "Vorbereitung, Gesprächsrahmen, Zeitraum von")
        self.period_end = self._optional_date_edit(draft.period_end if draft else None, "Vorbereitung, Gesprächsrahmen, Zeitraum bis")
        conference_value = draft.conference_date if draft and draft.conference_date else today
        self.conference_date = self._date_edit(conference_value, "Vorbereitung, Gesprächsrahmen, Gesprächsdatum")
        self.teacher_input = QLineEdit(draft.responsible_teacher if draft else "")
        self.teacher_input.setAccessibleName("Vorbereitung, Gesprächsrahmen, verantwortliche Lehrkraft")
        self.phase_first_focus["goal"] = self.period_start
        frame_grid = QGridLayout()
        frame_grid.setSpacing(10)
        frame_grid.addWidget(self._field("Zeitraum von", self.period_start), 0, 0)
        frame_grid.addWidget(self._field("Zeitraum bis", self.period_end), 0, 1)
        frame_grid.addWidget(self._field("Gesprächsdatum", self.conference_date), 1, 0)
        frame_grid.addWidget(self._field("Verantwortliche Lehrkraft", self.teacher_input), 1, 1)
        layout.addWidget(self._role_card(
            ROLE_PREPARATION,
            "Gesprächsrahmen",
            "Der Zeitraum grenzt sichtbare Kompetenzbelege ein; das Gesprächsdatum bezeichnet den Termin.",
            (_frame(frame_grid, "LearningConferenceSoftBlock"),),
            variant="soft",
        ))
        focus_layout = QVBoxLayout()
        focus_layout.setContentsMargins(0, 0, 0, 0)
        focus_layout.setSpacing(8)
        focus_layout.addWidget(_label("FACHLICHE BEREICHE", "field_label"))
        subject_grid = QGridLayout()
        for index, subject in enumerate(self.preparation.subjects):
            check = QCheckBox(subject.subject_name)
            check.setObjectName(f"LearningConferenceSubject_{subject.subject_id}")
            check.setChecked(subject.subject_id in self._selected_subject_ids)
            check.setIcon(subject_accent_icon(subject.subject_id))
            check.setAccessibleName(f"Vorbereitung, Gesprächsziel, Fachbereich {subject.subject_name}")
            self.subject_checks[subject.subject_id] = check
            subject_grid.addWidget(check, index // 3, index % 3)
        focus_layout.addLayout(subject_grid)
        focus_layout.addWidget(_label("ÜBERGREIFENDE GESPRÄCHSTHEMEN", "field_label"))
        cross_grid = QGridLayout()
        for index, topic in enumerate(self.preparation.cross_topics):
            check = QCheckBox(topic.label)
            check.setObjectName(f"LearningConferenceCrossTopic_{topic.cross_topic_key}")
            check.setChecked(topic.cross_topic_key in self._selected_cross_topics)
            check.setAccessibleName(f"Vorbereitung, Gesprächsziel, Gesprächsthema {topic.label}")
            self.cross_topic_checks[topic.cross_topic_key] = check
            cross_grid.addWidget(check, index // 2, index % 2)
        focus_layout.addLayout(cross_grid)
        layout.addWidget(self._role_card(
            ROLE_PREPARATION,
            "Gesprächsschwerpunkte",
            "Fachbereiche und übergreifende Themen bleiben bewusst getrennt.",
            (_frame(focus_layout, "LearningConferenceSoftBlock"),),
            variant="soft",
        ))
        layout.addWidget(self._text_role_card(
            "goal",
            ROLE_PREPARATION,
            "Gesprächseinstieg",
            "conversation_entry_text",
            "Ein kurzer vorbereitender Hinweis für Ziel und Rahmen des Gesprächs.",
        ))
        layout.addStretch(1)
        return content

    def _phase_strengths(self) -> QWidget:
        content, layout = self._phase_shell("strengths")
        first = self._text_role_card(
            "strengths", ROLE_PREPARATION, "Stärken und Lehrkraftsicht", "strengths_text",
            "Interne Orientierung der Lehrkraft; dieser Text ist keine gemeinsame Vereinbarung.",
        )
        layout.addWidget(first)
        layout.addWidget(self._text_role_card(
            "strengths", ROLE_CONVERSATION, "Rückblick des Kindes", "child_retrospective_text",
            "Die Perspektive des Kindes wird im Gespräch gemeinsam festgehalten.",
        ))
        layout.addWidget(self._evidence_summary_card())
        layout.addStretch(1)
        self.phase_first_focus["strengths"] = self.text_inputs["strengths_text"]
        return content

    def _phase_development(self) -> QWidget:
        content, layout = self._phase_shell("development")
        layout.addWidget(self._text_role_card(
            "development", ROLE_PREPARATION, "Sicht der Lehrkraft", "teacher_perspective_text",
            "Vorbereitete Entwicklungsbeobachtungen bleiben als interne Lehrkraftsicht gekennzeichnet.",
        ))
        layout.addWidget(self._text_role_card(
            "development", ROLE_CONVERSATION, "Entwicklungsfelder", "development_fields_text",
            "Diese Entwicklungsfelder werden im Gespräch gemeinsam betrachtet und formuliert.",
        ))
        layout.addWidget(self._evidence_summary_card())
        layout.addStretch(1)
        self.phase_first_focus["development"] = self.text_inputs["teacher_perspective_text"]
        return content

    def _phase_goals(self) -> QWidget:
        content, layout = self._phase_shell("goals")
        layout.addWidget(self._text_role_card(
            "goals", ROLE_PREPARATION, "Vorbereitete Zielideen", "prepared_goals_text",
            "Vorbereitete Ideen werden nicht automatisch zu Vereinbarungen.",
        ))
        layout.addWidget(self._text_role_card(
            "goals", ROLE_AGREEMENT, "Gemeinsam formulierte Ziele", "agreed_goals_text",
            "Diese Ziele sind im Draft als Vereinbarung festgehalten, aber nicht finalisiert.",
            variant="accent",
        ))
        layout.addWidget(self._evidence_summary_card())
        layout.addStretch(1)
        self.phase_first_focus["goals"] = self.text_inputs["prepared_goals_text"]
        return content

    def _phase_evidence(self) -> QWidget:
        content, layout = self._phase_shell("evidence")
        self.evidence_search = SearchField(
            "Kompetenzen und Belege durchsuchen",
            accessible_name="Vorbereitung, Belege, Kompetenzen und Belege durchsuchen",
            accessible_description="Filtert nur die sichtbare Auswahl und verändert keine gespeicherten Referenzen.",
        )
        self.evidence_filter_bar = FilterBar(self.evidence_search)
        layout.addWidget(self.evidence_filter_bar)
        layout.addWidget(self._competencies_card())
        layout.addWidget(self._evidence_card())
        layout.addWidget(self._charts_card())
        layout.addStretch(1)
        self.phase_first_focus["evidence"] = self.evidence_search
        return content

    def _phase_agreements(self) -> QWidget:
        content, layout = self._phase_shell("agreements")
        prepared_widgets = (
            self._text_input("agreements", ROLE_PREPARATION, "Vorbereitete Unterstützung", "prepared_support_text"),
            self._text_input("agreements", ROLE_PREPARATION, "Vorbereitete Vereinbarungen", "prepared_agreements_text"),
        )
        layout.addWidget(self._role_card(
            ROLE_PREPARATION,
            "Unterstützung vorbereiten",
            "Interne Ideen bleiben klar von den gemeinsam festgehaltenen Ergebnissen getrennt.",
            prepared_widgets,
            variant="soft",
        ))
        agreement_widgets: list[QWidget] = [
            self._text_input("agreements", ROLE_AGREEMENT, "Unterstützung", "agreed_support_text"),
            self._text_input("agreements", ROLE_AGREEMENT, "Maßnahmen und Vereinbarungen", "agreed_agreements_text"),
            self._text_input("agreements", ROLE_AGREEMENT, "Zuständigkeiten", "responsibilities_text"),
        ]
        review_value = self._saved_draft.next_review_date if self._saved_draft else None
        self.next_review_date = self._optional_date_edit(
            review_value,
            "Vereinbarungen und Abschluss, optionaler Überprüfungstermin",
        )
        agreement_widgets.append(self._field("Optionaler Überprüfungstermin", self.next_review_date))
        layout.addWidget(self._role_card(
            ROLE_AGREEMENT,
            "Gemeinsam festgehaltene Vereinbarungen",
            "Diese Angaben bleiben Teil eines bearbeitbaren Entwurfs. Sie sind nicht finalisiert.",
            agreement_widgets,
            variant="accent",
        ))
        layout.addWidget(self._evidence_summary_card(include_goals=True))
        layout.addStretch(1)
        self.phase_first_focus["agreements"] = self.text_inputs["prepared_support_text"]
        return content

    def _text_role_card(
        self,
        phase_key: str,
        role: str,
        title: str,
        field_key: str,
        help_text: str,
        *,
        variant: str = "default",
    ) -> AppCard:
        return self._role_card(
            role,
            title,
            help_text,
            (self._text_input(phase_key, role, title, field_key),),
            variant=variant,
        )

    def _text_input(self, phase_key: str, role: str, title: str, field_key: str) -> QWidget:
        value = getattr(self._saved_draft, field_key, "") if self._saved_draft else ""
        edit = QTextEdit(value)
        edit.setObjectName(f"LearningConferenceInput_{field_key}")
        edit.setAccessibleName(
            f"{_phase_group_title(phase_key)}, {_phase_title(phase_key)}, {role.casefold()}, {title}"
        )
        edit.setMinimumHeight(130)
        self.text_inputs[field_key] = edit
        return edit

    def _role_card(
        self,
        role: str,
        title: str,
        help_text: str,
        widgets: Iterable[QWidget],
        *,
        variant: str,
    ) -> AppCard:
        card = AppCard(variant)
        card.setProperty("learningConferenceRole", role)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        role_badge = StatusBadge(role, tone="info" if role != ROLE_AGREEMENT else "neutral")
        role_badge.setAccessibleName(f"Inhaltsrolle: {role}")
        header = SectionHeader(title, help_text)
        header.add_action(role_badge)
        layout.addWidget(header)
        for widget in widgets:
            layout.addWidget(widget)
        return card

    def _competencies_card(self) -> AppCard:
        card = AppCard("default")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)
        layout.addWidget(SectionHeader(
            "Kompetenzen auswählen",
            "Fach → Kompetenzbereich → Thema → Kompetenz. Der angezeigte Stand ist kanonisch und nicht editierbar.",
        ))
        self.competency_empty = _label(
            "Noch kein fachlicher Bereich gewählt. Wähle zuerst unter Gesprächsziel mindestens einen Gesprächsbereich aus.",
            "subtle",
        )
        self.competency_empty.setObjectName("LearningConferenceCompetencyEmpty")
        layout.addWidget(self.competency_empty)
        for subject in self.preparation.subjects:
            grouped: dict[str, dict[str, list[LearningConferenceCompetencyViewModel]]] = defaultdict(lambda: defaultdict(list))
            for competency in subject.competencies:
                grouped[competency.learning_area or "Ohne Kompetenzbereich"][competency.competency_group or "Ohne Thema"].append(competency)
            area_host = QWidget()
            area_layout = QVBoxLayout(area_host)
            area_layout.setContentsMargins(12, 0, 0, 0)
            area_layout.setSpacing(3)
            for area_index, (learning_area, topics) in enumerate(grouped.items()):
                section_id = f"{subject.subject_id}:{area_index}"
                topic_host = QWidget()
                topic_host.setAutoFillBackground(True)
                topic_layout = QVBoxLayout(topic_host)
                topic_layout.setContentsMargins(12, 0, 0, 0)
                topic_layout.setSpacing(3)
                area_ids = tuple(item.competency_id for values in topics.values() for item in values)
                self._competency_section_specs[section_id] = (subject.subject_id, dict(topics))
                self._competency_section_hosts[section_id] = topic_host
                area_section = _CollapsibleSection(
                    learning_area,
                    topic_host,
                    expanded=False,
                    on_expand=lambda section_id=section_id: self._ensure_competency_section_built(section_id),
                    feedback_on_expand=False,
                )
                self.competency_area_sections.append((subject.subject_id, area_ids, area_section))
                area_layout.addWidget(area_section)
            section = _CollapsibleSection(
                subject.subject_name,
                area_host,
                expanded=subject.subject_id in self._selected_subject_ids,
                feedback_on_expand=False,
            )
            section.button.setIcon(subject_accent_icon(subject.subject_id))
            self.competency_sections[subject.subject_id] = section
            layout.addWidget(section)
            empty = _label(
                f"Für dieses Kind sind in {subject.subject_name} noch keine kompetenzbezogenen Beobachtungen dokumentiert. Passe bei Bedarf Zeitraum oder Suche an.",
                "subtle",
            )
            empty.setObjectName(f"LearningConferenceCompetencyEmpty_{subject.subject_id}")
            self.competency_empty_by_subject[subject.subject_id] = empty
            layout.addWidget(empty)
        return card

    def _ensure_competency_section_built(self, section_id: str) -> None:
        if section_id in self._built_competency_sections:
            return
        subject_id, topics = self._competency_section_specs[section_id]
        topic_layout = self._competency_section_hosts[section_id].layout()
        if topic_layout is None:
            raise RuntimeError(f"LEG-Kompetenzbereich ohne Layout: {section_id}")
        for topic, competencies in topics.items():
            options = QWidget()
            options_layout = QVBoxLayout(options)
            options_layout.setContentsMargins(12, 2, 0, 5)
            competency_ids = tuple(item.competency_id for item in competencies)
            for competency in competencies:
                options_layout.addWidget(self._competency_option(competency))
            topic_section = _CollapsibleSection(
                topic,
                options,
                expanded=True,
                feedback_on_expand=False,
            )
            self.competency_topic_sections.append((subject_id, competency_ids, topic_section))
            topic_layout.addWidget(topic_section)
        self._built_competency_sections.add(section_id)
        self._update_competency_visibility(self._subject_ids())

    def _competency_option(self, competency: LearningConferenceCompetencyViewModel) -> QFrame:
        widget = QFrame()
        widget.setObjectName("LearningConferenceSoftBlock")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 9, 12, 10)
        check = QCheckBox(competency.competency_text)
        check.setObjectName(f"LearningConferenceCompetency_{competency.competency_id}")
        check.setAccessibleName(f"Vorbereitung, Belege, Kompetenz auswählen, {competency.competency_text}")
        check.setAccessibleDescription(f"Technische Kompetenz-ID {competency.competency_id}")
        selected = competency.competency_id in self._selected_competency_ids
        check.setChecked(selected)
        check.setEnabled(competency.selectable or selected)
        if selected and not competency.selectable:
            check.toggled.connect(lambda checked, widget=check: widget.setEnabled(checked))
        check.toggled.connect(
            lambda checked, competency_id=competency.competency_id: self._set_competency_selected(
                competency_id,
                checked,
            )
        )
        check.toggled.connect(self._draft_changed)
        check.toggled.connect(self._update_filters)
        self.competency_checks[competency.competency_id] = check
        self.competency_models[competency.competency_id] = competency
        layout.addWidget(check)
        status_text = (
            competency.documented_status_label
            or "Noch kein dokumentierter Stand"
        )
        status = _label(
            f"Aktueller dokumentierter Stand: {status_text}",
            "small",
        )
        status.setObjectName("LearningConferenceCanonicalStatus")
        status.setAccessibleName(
            f"{competency.competency_text}. Aktueller dokumentierter Stand: "
            f"{status_text}"
        )
        layout.addWidget(status)
        if competency.documentation_state:
            layout.addWidget(_label(competency.documentation_state, "subtle"))
        filter_note = _label("Bereits im Entwurf ausgewählt – außerhalb des aktuellen Filters.", "subtle")
        filter_note.setObjectName("LearningConferenceCompetencyFilterNote")
        filter_note.setVisible(False)
        self.competency_filter_notes[competency.competency_id] = filter_note
        layout.addWidget(filter_note)
        if competency.historical or not competency.selectable:
            layout.addWidget(_label("Historischer Bezug – nicht neu auswählbar.", "subtle"))
        self.competency_widgets[competency.competency_id] = widget
        return widget

    def _set_competency_selected(self, competency_id: str, checked: bool) -> None:
        if checked:
            self._selected_competency_ids.add(competency_id)
        else:
            self._selected_competency_ids.discard(competency_id)

    def _evidence_card(self) -> AppCard:
        card = AppCard("default")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)
        layout.addWidget(SectionHeader(
            "Beobachtungsbelege auswählen",
            "Belege dienen als Erinnerung und erzeugen keine pädagogische Interpretation.",
        ))
        self.evidence_warning = _frame(QHBoxLayout(), "LearningConferenceWarning")
        self.evidence_warning.layout().setContentsMargins(11, 9, 11, 9)
        self.evidence_warning_label = QLabel("")
        self.evidence_warning_label.setObjectName("LearningConferenceWarningText")
        self.evidence_warning_label.setWordWrap(True)
        self.evidence_warning.layout().addWidget(self.evidence_warning_label)
        layout.addWidget(self.evidence_warning)
        self.evidence_empty = _label(
            "Für die gewählten Bereiche sind keine Beobachtungsbelege sichtbar. Passe Gesprächsbereiche, Zeitraum oder Suche an.",
            "subtle",
        )
        layout.addWidget(self.evidence_empty)
        grouped: dict[str, list[LearningConferenceEvidenceViewModel]] = defaultdict(list)
        for evidence in self.preparation.evidence:
            grouped[evidence.subject_name or "Übergreifend"].append(evidence)
        for section_index, (subject_name, evidence_items) in enumerate(grouped.items()):
            section_id = f"evidence:{section_index}"
            host = QWidget()
            host.setAutoFillBackground(True)
            host_layout = QVBoxLayout(host)
            host_layout.setContentsMargins(12, 2, 0, 5)
            host_layout.setSpacing(6)
            self._evidence_section_specs[section_id] = tuple(evidence_items)
            self._evidence_section_hosts[section_id] = host
            section = _CollapsibleSection(
                subject_name,
                host,
                expanded=False,
                on_expand=lambda section_id=section_id: self._ensure_evidence_section_built(section_id),
                feedback_on_expand=False,
            )
            section.setObjectName("LearningConferenceEvidenceSection")
            self.evidence_sections[section_id] = section
            layout.addWidget(section)
        unavailable = self._saved_draft.unavailable_observation_ids if self._saved_draft else ()
        if unavailable:
            section_id = "evidence:unavailable"
            host = QWidget()
            host.setAutoFillBackground(True)
            host_layout = QVBoxLayout(host)
            host_layout.setContentsMargins(12, 2, 0, 5)
            host_layout.setSpacing(6)
            section = _CollapsibleSection(
                "Nicht verfügbare Belege",
                host,
                expanded=False,
                on_expand=lambda: self._ensure_unavailable_evidence_built(section_id),
                feedback_on_expand=False,
            )
            section.setObjectName("LearningConferenceEvidenceSection")
            self.evidence_sections[section_id] = section
            self._evidence_section_hosts[section_id] = host
            layout.addWidget(section)
        return card

    def _ensure_evidence_section_built(self, section_id: str) -> None:
        if section_id in self._built_evidence_sections:
            return
        layout = self._evidence_section_hosts[section_id].layout()
        if layout is None:
            raise RuntimeError(f"LEG-Belegbereich ohne Layout: {section_id}")
        for evidence in self._evidence_section_specs[section_id]:
            widget = QFrame()
            widget.setObjectName("LearningConferenceSoftBlock")
            block = QVBoxLayout(widget)
            block.setContentsMargins(12, 9, 12, 10)
            heading = QHBoxLayout()
            subject_id = next(
                (
                    competency.subject_id
                    for subject in self.preparation.subjects
                    for competency in subject.competencies
                    if competency.competency_id in evidence.competency_ids
                ),
                "",
            )
            heading.addWidget(SubjectAccentMarker(subject_id))
            heading.addWidget(_label(evidence.subject_name or "Übergreifend", "card_title"))
            heading.addWidget(_label(f"{evidence.date_text} · {evidence.context}", "small"), 1)
            block.addLayout(heading)
            block.addWidget(_label(evidence.note or "Ohne Notiz", "body"))
            check = QCheckBox("Für das Gespräch auswählen")
            check.setObjectName(f"LearningConferenceEvidence_{evidence.observation_id}")
            check.setAccessibleName(f"Vorbereitung, Belege, Beobachtungsbeleg vom {evidence.date_text} auswählen")
            check.setAccessibleDescription(f"Technische Beobachtungs-ID {evidence.observation_id}")
            check.setChecked(evidence.observation_id in self._selected_observation_ids)
            check.toggled.connect(
                lambda checked, observation_id=evidence.observation_id: self._set_observation_selected(
                    observation_id,
                    checked,
                )
            )
            check.toggled.connect(self._draft_changed)
            check.toggled.connect(self._update_evidence_warning)
            block.addWidget(check)
            if evidence.is_quick_observation:
                block.addWidget(_label("Nur als Textbeleg", "subtle"))
            self.evidence_checks[evidence.observation_id] = check
            self.evidence_widgets[evidence.observation_id] = widget
            layout.addWidget(widget)
        self._built_evidence_sections.add(section_id)
        self._update_evidence_visibility()

    def _ensure_unavailable_evidence_built(self, section_id: str) -> None:
        if section_id in self._built_evidence_sections:
            return
        layout = self._evidence_section_hosts[section_id].layout()
        if layout is None:
            raise RuntimeError(f"LEG-Belegbereich ohne Layout: {section_id}")
        unavailable = self._saved_draft.unavailable_observation_ids if self._saved_draft else ()
        for observation_id in unavailable:
            widget = QFrame()
            widget.setObjectName("LearningConferenceUnavailableEvidence")
            block = QVBoxLayout(widget)
            block.setContentsMargins(12, 9, 12, 10)
            block.addWidget(_label("Beleg nicht mehr verfügbar – gespeicherte Referenz bleibt erhalten", "card_title"))
            block.addWidget(_label(observation_id, "subtle"))
            check = QCheckBox("Gespeicherten Bezug beibehalten")
            check.setChecked(True)
            check.setAccessibleName(f"Vorbereitung, Belege, nicht verfügbaren Beleg {observation_id} beibehalten")
            check.toggled.connect(
                lambda checked, observation_id=observation_id: self._set_observation_selected(
                    observation_id,
                    checked,
                )
            )
            check.toggled.connect(self._draft_changed)
            check.toggled.connect(self._update_evidence_warning)
            block.addWidget(check)
            self.evidence_checks[observation_id] = check
            self.evidence_widgets[observation_id] = widget
            layout.addWidget(widget)
        self._built_evidence_sections.add(section_id)
        self._update_evidence_visibility()

    def _set_observation_selected(self, observation_id: str, checked: bool) -> None:
        if checked:
            self._selected_observation_ids.add(observation_id)
        else:
            self._selected_observation_ids.discard(observation_id)

    def _charts_card(self) -> AppCard:
        card = AppCard("soft")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 16)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(_label("Diagramme sind optional und zeigen nur Dokumentations- beziehungsweise Evidenzzusammenhänge.", "subtle"))
        for key, title in CHART_OPTIONS:
            check = QCheckBox(title)
            check.setObjectName(f"LearningConferenceChart_{key}")
            check.setAccessibleName(f"Vorbereitung, Belege, Gesprächsbild {title}")
            check.setChecked(key in self._selected_chart_types)
            self.chart_checks[key] = check
            layout.addWidget(check)
        disclosure = _CollapsibleSection("Optionale Gesprächsbilder", content, expanded=False)
        outer.addWidget(disclosure)
        return card

    def _evidence_summary_card(self, *, include_goals: bool = False) -> AppCard:
        card = AppCard("soft")
        card.setObjectName("LearningConferenceEvidenceSummary")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 14)
        title = "Ausgewählte Belege und Ziele" if include_goals else "Ausgewählte Belege"
        layout.addWidget(SectionHeader(
            title,
            "Read-only Zusammenfassung. Die Auswahl wird ausschließlich unter Belege vorbereiten geändert.",
        ))
        summary = _label("Noch keine Belege ausgewählt.", "body")
        summary.setAccessibleName("Zusammenfassung ausgewählter Kompetenzen, Beobachtungsbelege und Gesprächsbilder")
        layout.addWidget(summary)
        self.evidence_summary_labels.append(summary)
        button = QPushButton("Belege ansehen")
        configure_button(button, "secondary", "Zum Anker Belege vorbereiten")
        button.clicked.connect(lambda: self.set_active_phase("evidence"))
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _action_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("LearningConferenceActionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        self.close_button = QPushButton("Schließen")
        self.evidence_button = QPushButton("Belege ansehen")
        self.save_button = QPushButton("Entwurf speichern")
        self.save_button.setShortcut(QKeySequence.StandardKey.Save)
        self.complete_button = QPushButton("Gespräch abschließen")
        self.complete_button.setObjectName("LearningConferenceCompleteButton")
        self.revisions_button = QPushButton("Revisionen")
        self.revisions_button.setObjectName("LearningConferenceRevisionsButton")
        self.save_button.setObjectName("LearningConferenceSaveButton")
        configure_button(self.close_button, "quiet", "LEG-Workspace schließen")
        configure_button(self.evidence_button, "secondary", "Zum Anker Belege vorbereiten")
        configure_button(self.save_button, "primary", "LEG-Entwurf speichern")
        configure_button(self.complete_button, "secondary", "Gespeicherten LEG-Entwurf abschließen")
        configure_button(self.revisions_button, "quiet", "Abschlussrevisionen öffnen")
        self.close_button.clicked.connect(self.reject)
        self.evidence_button.clicked.connect(lambda: self.set_active_phase("evidence"))
        self.save_button.clicked.connect(self._request_save)
        self.complete_button.clicked.connect(self._request_completion)
        self.revisions_button.clicked.connect(self._open_revision_history)
        layout.addWidget(self.close_button)
        layout.addWidget(self.evidence_button)
        layout.addStretch(1)
        layout.addWidget(self.revisions_button)
        layout.addWidget(self.complete_button)
        layout.addWidget(self.save_button)
        return bar

    def _connect_phase_updates(self, key: str) -> None:
        if key == "goal":
            for control in (*self.subject_checks.values(), *self.cross_topic_checks.values()):
                control.toggled.connect(self._draft_changed)
                control.toggled.connect(self._update_filters)
            for edit in (self.period_start, self.period_end, self.conference_date):
                edit.dateChanged.connect(self._draft_changed)
            self.period_start.dateChanged.connect(self._update_filters)
            self.period_end.dateChanged.connect(self._update_filters)
            self.teacher_input.textChanged.connect(self._draft_changed)
        elif key == "evidence":
            for control in self.chart_checks.values():
                control.toggled.connect(self._draft_changed)
                control.toggled.connect(self._update_filters)
            self.evidence_search.textChanged.connect(self._update_filters)
        elif key == "agreements":
            self.next_review_date.dateChanged.connect(self._draft_changed)
        for field_key in self._phase_text_field_keys(key):
            self.text_inputs[field_key].textChanged.connect(self._draft_changed)

    def _draft_changed(self, *_args: object) -> None:
        self._refresh_ui_state()

    def _refresh_ui_state(self) -> None:
        if self._baseline is not None:
            self._dirty = self.draft_view_model() != self._baseline
        has_saved_state = bool(
            self._saved_draft
            and (
                self._saved_draft.learning_conference_draft_id
                or self._saved_draft.updated_at
            )
        )
        clean_label = "Entwurf gespeichert" if has_saved_state else "Noch nicht gespeichert"
        self.dirty_badge.setText("Ungespeicherte Änderungen" if self._dirty else clean_label)
        self.dirty_badge.setAccessibleName(self.dirty_badge.text())
        self.dirty_badge.setProperty(
            "badgeTone",
            "warning" if self._dirty else "success" if has_saved_state else "neutral",
        )
        self.dirty_badge.style().unpolish(self.dirty_badge)
        self.dirty_badge.style().polish(self.dirty_badge)
        self.status_label.setText(
            "Ungespeicherte Änderungen"
            if self._dirty else _format_saved_at(self._saved_draft.updated_at if self._saved_draft else "")
        )
        self.date_context_label.setText(f"Gesprächsdatum: {self.conference_date.date().toString('dd.MM.yyyy')}")
        self.teacher_context_label.setText(f"Lehrkraft: {self.teacher_input.text().strip() or 'offen'}")
        for key, _title, _description in PHASES:
            self.phase_navigation.set_content_state(key, self._phase_has_content(key))
        self._update_evidence_summaries()
        self.complete_button.setEnabled(has_saved_state and not self._dirty and not self._save_pending)
        self.revisions_button.setVisible(bool(
            self._completion_status and self._completion_status.revisions
        ))

    def _phase_has_content(self, key: str) -> bool:
        if key == "goal":
            return bool(self._subject_ids() or self._cross_topic_keys() or self._text("conversation_entry_text"))
        if key == "strengths":
            return bool(self._text("strengths_text") or self._text("child_retrospective_text"))
        if key == "development":
            return bool(self._text("teacher_perspective_text") or self._text("development_fields_text"))
        if key == "goals":
            return bool(self._text("prepared_goals_text") or self._text("agreed_goals_text"))
        if key == "evidence":
            return bool(self._competency_ids() or self._observation_ids() or self._chart_types())
        return bool(
            self._text("prepared_support_text")
            or self._text("prepared_agreements_text")
            or self._text("agreed_support_text")
            or self._text("agreed_agreements_text")
            or self._text("responsibilities_text")
            or self._next_review_date_value()
        )

    def set_active_phase(self, key: str, *, focus: bool = True) -> None:
        keys = [phase_key for phase_key, _title, _description in PHASES]
        if key not in keys:
            raise ValueError(f"Unbekannte LEG-Phase: {key}")
        self._ensure_phase_built(key)
        self.phase_navigation.set_current(key)
        active_page = self.phase_pages[key]
        self.phase_stack.setCurrentWidget(active_page)
        for page in self.phase_pages.values():
            is_active = page is active_page
            page.setGraphicsEffect(None)
            page.setEnabled(is_active)
            page.setVisible(is_active)
        active_page.raise_()
        self.phase_stack.update()
        title = _phase_title(key)
        self.phase_context_label.setText(f"{_phase_group_title(key)} · {title}")
        self.evidence_button.setVisible(key in {"strengths", "development", "goals", "agreements"})
        self._refresh_ui_state()
        if focus:
            target = self.phase_first_focus.get(key)
            if target is not None:
                QTimer.singleShot(0, target.setFocus)

    def _update_filters(self, *_args: object) -> None:
        if not self.phase_built["evidence"]:
            self._refresh_ui_state()
            return
        selected_subjects = self._subject_ids()
        self.competency_empty.setVisible(not selected_subjects)
        self._update_competency_visibility(selected_subjects)
        selected_labels = {
            subject.subject_name
            for subject in self.preparation.subjects
            if subject.subject_id in selected_subjects
        }
        self._update_evidence_visibility(selected_labels)
        self._update_evidence_warning()
        self._refresh_ui_state()

    def _update_competency_visibility(self, selected_subjects: set[str]) -> None:
        period_start, period_end = self._competency_filter_period()
        search = self.evidence_search.text().strip().casefold()
        visible_ids: set[str] = set()
        visible_by_id: dict[str, bool] = {}
        for subject in self.preparation.subjects:
            for competency in subject.competencies:
                competency_id = competency.competency_id
                selected = competency_id in self._selected_competency_ids
                documented = competency.is_documented_in_period(period_start, period_end)
                matches_search = not search or search in (
                    f"{competency.subject_name} {competency.learning_area} {competency.competency_group} {competency.competency_text}"
                ).casefold()
                visible = (documented or selected) and matches_search
                visible_by_id[competency_id] = visible
                if visible:
                    visible_ids.add(competency_id)
        for competency_id, widget in self.competency_widgets.items():
            competency = self.competency_models[competency_id]
            selected = competency_id in self._selected_competency_ids
            documented = competency.is_documented_in_period(period_start, period_end)
            widget.setVisible(visible_by_id[competency_id])
            self.competency_filter_notes[competency_id].setVisible(selected and not documented)
        for subject_id, competency_ids, section in self.competency_topic_sections:
            section.setVisible(subject_id in selected_subjects and bool(set(competency_ids) & visible_ids))
        for subject_id, competency_ids, section in self.competency_area_sections:
            section.setVisible(subject_id in selected_subjects and bool(set(competency_ids) & visible_ids))
        for subject_id, section in self.competency_sections.items():
            subject_has_visible = any(
                competency.subject_id == subject_id
                and competency.competency_id in visible_ids
                for subject in self.preparation.subjects
                for competency in subject.competencies
            )
            section.setVisible(subject_id in selected_subjects and subject_has_visible)
            self.competency_empty_by_subject[subject_id].setVisible(subject_id in selected_subjects and not subject_has_visible)
            subject_name = next(subject.subject_name for subject in self.preparation.subjects if subject.subject_id == subject_id)
            period_suffix = " und im gewählten Zeitraum" if period_start and period_end else ""
            self.competency_empty_by_subject[subject_id].setText(
                f"Für dieses Kind sind in {subject_name}{period_suffix} noch keine kompetenzbezogenen Beobachtungen dokumentiert. Passe bei Bedarf Zeitraum oder Suche an."
            )

    def _update_evidence_visibility(self, selected_labels: set[str] | None = None) -> None:
        if selected_labels is None:
            selected_labels = {
                subject.subject_name
                for subject in self.preparation.subjects
                if subject.subject_id in self._subject_ids()
            }
        search = self.evidence_search.text().strip().casefold()
        visible_ids: set[str] = set()
        section_visible: dict[str, bool] = {}
        selected_competencies = self._competency_ids()
        for section_id, evidence_items in self._evidence_section_specs.items():
            has_visible = False
            for evidence in evidence_items:
                matches_subject = evidence.subject_name in selected_labels or bool(
                    set(evidence.competency_ids) & selected_competencies
                )
                haystack = (
                    f"{evidence.subject_name} {evidence.context} {evidence.note} {evidence.date_text}"
                ).casefold()
                visible = matches_subject and (not search or search in haystack)
                has_visible = has_visible or visible
                if visible:
                    visible_ids.add(evidence.observation_id)
                widget = self.evidence_widgets.get(evidence.observation_id)
                if widget is not None:
                    widget.setVisible(visible)
            section_visible[section_id] = has_visible
        for section_id, section in self.evidence_sections.items():
            if section_id == "evidence:unavailable":
                unavailable = self._saved_draft.unavailable_observation_ids if self._saved_draft else ()
                has_visible = any(not search or search in item.casefold() for item in unavailable)
                section.setVisible(has_visible)
                for observation_id in unavailable:
                    widget = self.evidence_widgets.get(observation_id)
                    if widget is not None:
                        widget.setVisible(not search or search in observation_id.casefold())
            else:
                section.setVisible(section_visible.get(section_id, False))
        unavailable_section = self.evidence_sections.get("evidence:unavailable")
        unavailable_visible = bool(
            self._saved_draft
            and self._saved_draft.unavailable_observation_ids
            and unavailable_section is not None
            and not unavailable_section.isHidden()
        )
        self.evidence_empty.setVisible(not visible_ids and not unavailable_visible)

    def _competency_filter_period(self) -> tuple[date | None, date | None]:
        period_start = self._optional_date_value(self.period_start)
        period_end = self._optional_date_value(self.period_end)
        if period_start is None or period_end is None:
            return None, None
        return period_start, period_end

    def _update_evidence_warning(self, *_args: object) -> None:
        count = len(self._observation_ids())
        self.evidence_warning_label.setText(
            f"{count} Belege ausgewählt. Drei bis fünf Belege sind meist gut überschaubar. Die Auswahl bleibt unverändert."
            if count > 5 else ""
        )
        self.evidence_warning.setVisible(count > 5)
        self._refresh_ui_state()

    def _update_evidence_summaries(self) -> None:
        selected_competency_ids = self._competency_ids()
        competencies = len(selected_competency_ids)
        evidence = len(self._observation_ids())
        charts = len(self._chart_types())
        subjects = ", ".join(self._selected_area_labels()) or "Keine Gesprächsbereiche ausgewählt"
        unavailable = len(self._saved_draft.unavailable_observation_ids) if self._saved_draft else 0
        unavailable_text = f" · {unavailable} nicht verfügbarer Bezug" if unavailable else ""
        goals_text = self._text("agreed_goals_text")
        text = (
            f"{subjects}\n{competencies} Kompetenzen · {evidence} Beobachtungsbelege · "
            f"{charts} Gesprächsbilder{unavailable_text}"
        )
        selected_competencies = tuple(
            competency
            for subject in self.preparation.subjects
            for competency in subject.competencies
            if competency.competency_id in selected_competency_ids
        )
        if selected_competencies:
            text += "\n" + "\n".join(
                f"• {competency.competency_text} – Aktueller dokumentierter "
                f"Stand: {competency.documented_status_label or 'Noch kein dokumentierter Stand'}"
                for competency in selected_competencies
            )
        if goals_text:
            text += f"\nVereinbarte Ziele: {goals_text}"
        for label in self.evidence_summary_labels:
            label.setText(text)

    def draft_view_model(self) -> LearningConferenceDraftViewModel:
        return LearningConferenceDraftViewModel(
            student_id=self.preparation.student_id,
            period_start=self._optional_date_value(self.period_start),
            period_end=self._optional_date_value(self.period_end),
            conference_date=self.conference_date.date().toPython(),
            responsible_teacher=self.teacher_input.text().strip(),
            conversation_entry_text=self._text("conversation_entry_text"),
            child_retrospective_text=self._text("child_retrospective_text"),
            teacher_perspective_text=self._text("teacher_perspective_text"),
            strengths_text=self._text("strengths_text"),
            development_fields_text=self._text("development_fields_text"),
            prepared_goals_text=self._text("prepared_goals_text"),
            prepared_support_text=self._text("prepared_support_text"),
            prepared_agreements_text=self._text("prepared_agreements_text"),
            agreed_goals_text=self._text("agreed_goals_text"),
            agreed_support_text=self._text("agreed_support_text"),
            agreed_agreements_text=self._text("agreed_agreements_text"),
            responsibilities_text=self._text("responsibilities_text"),
            next_review_date=self._next_review_date_value(),
            subject_ids=tuple(sorted(self._subject_ids())),
            cross_topic_keys=tuple(sorted(self._cross_topic_keys())),
            competency_ids=tuple(sorted(self._competency_ids())),
            observation_ids=tuple(sorted(self._observation_ids())),
            chart_types=tuple(sorted(self._chart_types())),
            learning_conference_draft_id=self._saved_draft.learning_conference_draft_id if self._saved_draft else "",
            status=self._saved_draft.status if self._saved_draft else "draft",
            created_at=self._saved_draft.created_at if self._saved_draft else "",
            updated_at=self._saved_draft.updated_at if self._saved_draft else "",
            unavailable_observation_ids=self._saved_draft.unavailable_observation_ids if self._saved_draft else (),
        )

    def apply_saved_draft(self, draft: LearningConferenceDraftViewModel) -> None:
        self._saved_draft = draft
        self._baseline = self.draft_view_model()
        self._save_pending = False
        self.save_button.setEnabled(True)
        self.save_button.setText("Entwurf speichern")
        animate_save_confirmation(self.save_button)
        self.validation_message.set_message("")
        self._refresh_ui_state()
        self.toast.show_message("Entwurf gespeichert – du kannst ihn später fortsetzen.", tone="success")

    def apply_revision_status(
        self,
        status: LearningConferenceRevisionStatusViewModel,
    ) -> None:
        self._completion_status = status
        self.completion_badge.setText(status.status_label)
        tone = (
            "warning"
            if status.draft_changed or not status.hash_valid
            else "success" if status.has_completion else "neutral"
        )
        self.completion_badge.setProperty("badgeTone", tone)
        self.completion_badge.style().unpolish(self.completion_badge)
        self.completion_badge.style().polish(self.completion_badge)
        self._refresh_ui_state()

    def show_completion_error(
        self,
        error: LearningConferenceCompletionErrorViewModel,
    ) -> None:
        if error.phase_key:
            self.set_active_phase(error.phase_key, focus=False)
        references = (
            f" ({', '.join(error.reference_ids)})" if error.reference_ids else ""
        )
        self.validation_message.set_message(
            f"Das Gespräch konnte nicht abgeschlossen werden: {error.message}{references}",
            tone="error",
        )
        self.validation_message.setFocus()

    def _request_completion(self) -> None:
        if not self._saved_draft or self._dirty or self._save_pending:
            return
        message, confirm = create_confirmation_message(
            self,
            "Gespräch abschließen",
            "Es wird ein unveränderlicher Abschlussstand erzeugt. "
            "Der Entwurf bleibt für spätere Korrekturen bearbeitbar. Fortfahren?",
            confirm_text="Gespräch abschließen",
        )
        exec_owned_dialog(message, self)
        confirmed = message.clickedButton() is confirm
        message.deleteLater()
        if confirmed:
            self.validation_message.set_message("")
            self.completion_requested.emit(
                self._saved_draft.learning_conference_draft_id
            )

    def _open_revision_history(self) -> None:
        if not self._completion_status:
            return
        revision_id = LearningConferenceRevisionHistoryDialog.choose(
            self._completion_status,
            self,
        )
        if revision_id:
            self.revision_open_requested.emit(revision_id)

    def show_save_error(self, message: str) -> None:
        self._save_pending = False
        self.save_button.setEnabled(True)
        self.save_button.setText("Entwurf speichern")
        self.validation_message.set_message(
            f"Der Entwurf konnte nicht gespeichert werden: {message}",
            tone="error",
        )
        self.validation_message.setFocus()

    def _request_save(self) -> None:
        if self._save_pending:
            return
        self._save_pending = True
        self.save_button.setEnabled(False)
        self.save_button.setText("Wird gespeichert …")
        self.validation_message.set_message("")
        self.save_requested.emit(self.draft_view_model())
        if self._save_pending:
            self._save_pending = False
            self.save_button.setEnabled(True)
            self.save_button.setText("Entwurf speichern")

    def reject(self) -> None:
        if self._confirm_close():
            super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._confirm_close():
            event.accept()
        else:
            event.ignore()

    def _confirm_close(self) -> bool:
        if not self._dirty:
            return True
        choice = self._close_choice_provider(self)
        if choice == "discard":
            return True
        if choice == "save":
            self._request_save()
            return not self._dirty
        return False

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        width = event.size().width()
        self.phase_navigation.setFixedWidth(232 if width >= 1360 else 220 if width >= 1220 else 214)
        super().resizeEvent(event)

    def _subject_ids(self) -> set[str]:
        if not self.phase_built["goal"]:
            return set(self._selected_subject_ids)
        return {key for key, check in self.subject_checks.items() if check.isChecked()}

    def _cross_topic_keys(self) -> set[str]:
        if not self.phase_built["goal"]:
            return set(self._selected_cross_topics)
        return {key for key, check in self.cross_topic_checks.items() if check.isChecked()}

    def _competency_ids(self) -> set[str]:
        return set(self._selected_competency_ids)

    def _observation_ids(self) -> set[str]:
        return set(self._selected_observation_ids)

    def _chart_types(self) -> set[str]:
        if not self.phase_built["evidence"]:
            return set(self._selected_chart_types)
        return {key for key, check in self.chart_checks.items() if check.isChecked()}

    def _text(self, key: str) -> str:
        edit = self.text_inputs.get(key)
        if edit is not None:
            return edit.toPlainText().strip()
        return (getattr(self._saved_draft, key, "") if self._saved_draft else "").strip()

    def _next_review_date_value(self) -> date | None:
        if self.phase_built["agreements"]:
            return self._optional_date_value(self.next_review_date)
        return self._saved_draft.next_review_date if self._saved_draft else None

    @staticmethod
    def _phase_text_field_keys(key: str) -> tuple[str, ...]:
        return {
            "goal": ("conversation_entry_text",),
            "strengths": ("strengths_text", "child_retrospective_text"),
            "development": ("teacher_perspective_text", "development_fields_text"),
            "goals": ("prepared_goals_text", "agreed_goals_text"),
            "evidence": (),
            "agreements": (
                "prepared_support_text",
                "prepared_agreements_text",
                "agreed_support_text",
                "agreed_agreements_text",
                "responsibilities_text",
            ),
        }[key]

    def _selected_area_labels(self) -> tuple[str, ...]:
        labels = [subject.subject_name for subject in self.preparation.subjects if subject.subject_id in self._subject_ids()]
        labels.extend(topic.label for topic in self.preparation.cross_topics if topic.cross_topic_key in self._cross_topic_keys())
        return tuple(labels)

    def _field(self, title: str, widget: QWidget) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(_label(title.upper(), "field_label"))
        layout.addWidget(widget)
        return host

    def _date_edit(self, value: date, accessible_name: str) -> QDateEdit:
        edit = QDateEdit(QDate(value.year, value.month, value.day))
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd.MM.yyyy")
        edit.setAccessibleName(accessible_name)
        return edit

    def _optional_date_edit(self, value: date | None, accessible_name: str) -> QDateEdit:
        minimum = QDate(1900, 1, 1)
        edit = QDateEdit()
        edit.setMinimumDate(minimum)
        edit.setSpecialValueText("Nicht gesetzt")
        edit.setDate(QDate(value.year, value.month, value.day) if value is not None else minimum)
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd.MM.yyyy")
        edit.setAccessibleName(accessible_name)
        return edit

    def _optional_date_value(self, edit: QDateEdit) -> date | None:
        if edit.date() == edit.minimumDate():
            return None
        return edit.date().toPython()
