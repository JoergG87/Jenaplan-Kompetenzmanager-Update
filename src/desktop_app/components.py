"""Small, reusable interaction foundations for the PySide desktop app."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.icons import ICON_SIZE_SMALL, load_icon
from src.desktop_app.motion import (
    animate_feedback,
    animate_opacity,
    install_card_motion,
    stop_motion,
)
from src.desktop_app.theme import MOTION_FAST_MS
from src.desktop_app.theme import set_button_role, set_label_style


class AppCard(QFrame):
    """Semantic surface with optional interactive states."""

    def __init__(self, variant: str = "default", *, interactive: bool = False) -> None:
        super().__init__()
        if variant not in {"default", "soft", "accent", "interactive"}:
            raise ValueError(f"Unbekannte Kartenvariante: {variant}")
        self.setObjectName("AppCard")
        self.setProperty("cardVariant", variant)
        self.setProperty("selected", False)
        self.setProperty("pressed", False)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        if interactive or variant == "interactive":
            self.setProperty("interactive", True)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            install_card_motion(self)

    def set_selected(self, selected: bool) -> None:
        """Expose one central selected state to QSS."""
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_pressed(self, pressed: bool) -> None:
        """Expose pointer/key press without screen-local styling."""
        self.setProperty("pressed", pressed)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.property("interactive") and event.button() == Qt.MouseButton.LeftButton:
            self.set_pressed(True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.property("interactive"):
            self.set_pressed(False)
        super().mouseReleaseEvent(event)


class IconButton(QPushButton):
    """Compact SVG action with mandatory accessible naming."""

    def __init__(self, icon_name: str, accessible_name: str, tooltip: str = "") -> None:
        if not accessible_name.strip():
            raise ValueError("IconButton benoetigt einen Accessible Name.")
        super().__init__()
        self.setObjectName("IconButton")
        self.setIcon(load_icon(icon_name))
        self.setIconSize(QSize(ICON_SIZE_SMALL, ICON_SIZE_SMALL))
        self.setFixedSize(30, 30)
        self.setAccessibleName(accessible_name)
        self.setToolTip(tooltip or accessible_name)
        configure_button(self, "quiet", accessible_name)


class SectionHeader(QWidget):
    """Reusable title, explanation, help, and action row."""

    def __init__(self, title: str, description: str = "", help_text: str = "") -> None:
        super().__init__()
        self.setObjectName("SectionHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        labels = QVBoxLayout()
        labels.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionHeaderTitle")
        set_label_style(self.title_label, "section_title")
        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        set_label_style(self.description_label, "muted")
        self.description_label.setVisible(bool(description))
        labels.addWidget(self.title_label)
        labels.addWidget(self.description_label)
        layout.addLayout(labels, 1)
        if help_text:
            self.help_button = IconButton("info", f"Hilfe zu {title}", help_text)
            layout.addWidget(self.help_button)
        else:
            self.help_button = None
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)
        layout.addLayout(self.actions_layout)

    def add_action(self, action: QWidget) -> None:
        self.actions_layout.addWidget(action)


class FilterChip(QPushButton):
    """Visible local filter state with an optional reset request."""

    remove_requested = Signal()

    def __init__(self, label: str = "") -> None:
        super().__init__(label)
        self.setObjectName("FilterChip")
        self.setProperty("selected", True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(self.remove_requested.emit)
        self.setVisible(bool(label))

    def set_label(self, label: str) -> None:
        was_hidden = self.isHidden()
        self.setText(label)
        self.setAccessibleName(f"Aktiver Filter: {label}. Filter zurücksetzen")
        if label and was_hidden:
            animate_opacity(self, visible=True, duration_ms=MOTION_FAST_MS)
        else:
            self.setVisible(bool(label))


class FilterBar(QFrame):
    """Compose search and visible context state without owning filter logic."""

    reset_requested = Signal()

    def __init__(self, search_field: QLineEdit) -> None:
        super().__init__()
        self.setObjectName("FilterBar")
        self.setAccessibleName("Suche und aktive Filter")
        self.search_field = search_field
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        layout.addWidget(search_field, 1)
        self.context_chip = FilterChip()
        self.context_chip.remove_requested.connect(self.reset_requested.emit)
        layout.addWidget(self.context_chip)

    def set_context_filter(self, label: str, active: bool) -> None:
        """Show reset only for a real context filter."""
        self.context_chip.set_label(label if active else "")


class PageHeader(QWidget):
    """Consistent page title, description, and right-aligned actions."""

    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("PageHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        heading = QVBoxLayout()
        heading.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageHeaderTitle")
        set_label_style(self.title_label, "screen_title")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageHeaderSubtitle")
        self.subtitle_label.setWordWrap(True)
        set_label_style(self.subtitle_label, "muted")
        self.subtitle_label.setVisible(bool(subtitle))
        heading.addWidget(self.title_label)
        heading.addWidget(self.subtitle_label)
        layout.addLayout(heading, 1)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)
        layout.addLayout(self.actions_layout)

    def add_action(self, action: QWidget) -> None:
        """Add one page-level action."""
        self.actions_layout.addWidget(action)


class SegmentedControl(QFrame):
    """Exclusive local navigation with pointer and arrow-key operation."""

    selection_changed = Signal(str)

    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        super().__init__()
        self.setObjectName("SegmentedControl")
        self._keys: list[str] = []
        self._buttons: dict[str, QPushButton] = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        item_list = list(items)
        for index, (key, label) in enumerate(item_list):
            button = QPushButton(label)
            button.setObjectName("SegmentedControlButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setAccessibleName(label)
            if index == 0:
                position = "first"
            elif index == len(item_list) - 1:
                position = "last"
            else:
                position = "middle"
            button.setProperty("segmentPosition", position)
            button.installEventFilter(self)
            self.button_group.addButton(button, index)
            self._keys.append(key)
            self._buttons[key] = button
            layout.addWidget(button)
        self.button_group.idClicked.connect(self._emit_selection)
        if self._keys:
            self.set_current_key(self._keys[0])

    def current_key(self) -> str:
        """Return the selected semantic key."""
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return ""

    def set_current_key(self, key: str, *, emit: bool = False) -> None:
        """Select one segment without triggering navigation by default."""
        if key not in self._buttons:
            raise ValueError(f"Unbekannter Segment-Schlüssel: {key}")
        changed = self.current_key() != key
        self._buttons[key].setChecked(True)
        if changed and self.isVisible():
            animate_feedback(self._buttons[key], key="segment_selection")
        if emit:
            self.selection_changed.emit(key)

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.KeyPress and watched in self._buttons.values():
            key_event = event
            if key_event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                direction = -1 if key_event.key() == Qt.Key.Key_Left else 1
                self._move_selection(direction)
                return True
        return super().eventFilter(watched, event)

    def _move_selection(self, direction: int) -> None:
        current = self.current_key()
        if current not in self._keys:
            return
        next_index = (self._keys.index(current) + direction) % len(self._keys)
        next_key = self._keys[next_index]
        self.set_current_key(next_key, emit=True)
        self._buttons[next_key].setFocus()

    def _emit_selection(self, button_id: int) -> None:
        if 0 <= button_id < len(self._keys):
            animate_feedback(
                self._buttons[self._keys[button_id]],
                key="segment_selection",
            )
            self.selection_changed.emit(self._keys[button_id])


class SearchField(QLineEdit):
    """Search input with a clear affordance and Escape-key reset."""

    def __init__(self, placeholder: str) -> None:
        super().__init__()
        self.setObjectName("SearchField")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.addAction(load_icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.setAccessibleName("Schüler suchen")
        self.setAccessibleDescription(
            "Filtert die sichtbare Schülerliste während der Eingabe."
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self.text():
            self.clear()
            event.accept()
            return
        super().keyPressEvent(event)


class StatusBadge(QLabel):
    """Compact, neutral status label."""

    def __init__(self, text: str = "", *, tone: str = "neutral") -> None:
        super().__init__(text)
        self.setObjectName("StatusBadge")
        self.setProperty("badgeTone", tone)
        self.setAccessibleName(text)


class InlineMessage(QFrame):
    """Persistent message for contextual information, warnings, or errors."""

    def __init__(self, text: str = "", *, tone: str = "info") -> None:
        super().__init__()
        self.setObjectName("InlineMessage")
        self.setProperty("messageTone", tone)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.setVisible(bool(text))

    def set_message(self, text: str, *, tone: str = "info") -> None:
        """Update content and tone while retaining space only when needed."""
        was_hidden = self.isHidden()
        self.label.setText(text)
        self.setProperty("messageTone", tone)
        self.setAccessibleName(text)
        self.style().unpolish(self)
        self.style().polish(self)
        if not text:
            if was_hidden:
                stop_motion(self, "opacity")
                self.hide()
            else:
                animate_opacity(self, visible=False)
        elif tone in {"warning", "error"}:
            stop_motion(self, "opacity")
            self.setVisible(True)
            effect = getattr(self, "_motion_opacity_effect", None)
            if effect is not None:
                effect.setOpacity(1.0)
        elif was_hidden:
            animate_opacity(self, visible=True)
        else:
            self.setVisible(True)


class EmptyState(QFrame):
    """Quiet, reusable empty-state panel."""

    def __init__(self, text: str = "", *, title: str = "") -> None:
        super().__init__()
        self.setObjectName("EmptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        self.title_label = QLabel(title)
        set_label_style(self.title_label, "card_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setVisible(bool(title))
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_style(self.label, "muted")
        layout.addWidget(self.title_label)
        layout.addWidget(self.label)
        self.setVisible(bool(text or title))

    def set_message(self, text: str) -> None:
        """Show the state only while it has meaningful content."""
        self.label.setText(text)
        self.setAccessibleName(text)
        self.setVisible(bool(text))


class Toast(QFrame):
    """Non-blocking, automatically disappearing shell feedback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setMinimumWidth(280)
        self.setMaximumWidth(520)
        self.setProperty("toastTone", "info")
        self.setAccessibleName("Statusmeldung")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._dismiss)
        self._duration_ms = 4200
        self._remaining_ms = self._duration_ms
        self.hide()

    def show_message(
        self,
        text: str,
        *,
        tone: str = "info",
        duration_ms: int = 4200,
    ) -> None:
        """Show one message without interrupting the current workflow."""
        if not text:
            self.clear()
            return
        self.label.setText(text)
        self.setProperty("toastTone", tone)
        self.setAccessibleDescription(text)
        self.style().unpolish(self)
        self.style().polish(self)
        was_hidden = self.isHidden()
        stop_motion(self)
        if was_hidden:
            animate_opacity(self, visible=True)
        else:
            animate_feedback(self, key="toast_feedback")
        self._duration_ms = max(0, duration_ms)
        self._remaining_ms = self._duration_ms
        self.timer.start(self._duration_ms)

    def event(self, event: QEvent) -> bool:
        """Pause a toast's reading time while the pointer rests on it."""
        if event.type() == QEvent.Type.Enter and self.timer.isActive():
            self._remaining_ms = max(0, self.timer.remainingTime())
            self.timer.stop()
        elif (
            event.type() == QEvent.Type.Leave
            and self.isVisible()
            and self._remaining_ms > 0
        ):
            self.timer.start(self._remaining_ms)
        return super().event(event)

    def _dismiss(self) -> None:
        self._remaining_ms = 0
        stop_motion(self)
        animate_opacity(self, visible=False)

    def setText(self, text: str) -> None:  # noqa: N802
        """Keep the former shell status-label call site compatible."""
        if not self.window().isVisible():
            self.timer.stop()
            self.label.setText(text)
            self.hide()
            return
        normalized = text.casefold()
        if any(
            term in normalized
            for term in (
                "gespeichert",
                "aktualisiert",
                "erstellt",
                "entfernt",
                "gelöscht",
                "aktiviert",
                "deaktiviert",
                "bestätigt",
            )
        ):
            tone = "success"
        elif "nicht gefunden" in normalized or "nicht verfügbar" in normalized:
            tone = "warning"
        else:
            tone = "info"
        self.show_message(text, tone=tone)

    def text(self) -> str:
        """Return the currently displayed message."""
        return self.label.text()

    def clear(self) -> None:
        """Clear and hide the toast immediately."""
        self.timer.stop()
        self._remaining_ms = 0
        stop_motion(self)
        self.label.clear()
        effect = getattr(self, "_motion_opacity_effect", None)
        if effect is not None:
            effect.setOpacity(1.0)
        self.hide()


def configure_button(button: QPushButton, role: str, accessible_name: str = "") -> None:
    """Apply role, pointer cursor, and optional accessible naming."""
    set_button_role(button, role)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if accessible_name:
        button.setAccessibleName(accessible_name)
