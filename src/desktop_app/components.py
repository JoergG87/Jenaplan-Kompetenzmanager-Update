"""Small, reusable interaction foundations for the PySide desktop app."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QEasingCurve, QEvent, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.icons import ICON_SIZE_LARGE, ICON_SIZE_SMALL, load_icon
from src.desktop_app.motion import (
    animate_feedback,
    animate_opacity,
    animate_selection,
    animate_value,
    install_button_motion,
    install_card_motion,
    install_pointer_cursor,
    stop_motion,
)
from src.desktop_app.theme import (
    MOTION_FAST_MS,
    MOTION_SELECTION_MS,
)
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
            install_pointer_cursor(self)
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

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Activate compact icon actions consistently outside dialogs."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)


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

    def add_filter_widget(self, widget: QWidget) -> None:
        """Insert a screen-owned filter before the visible context chip."""
        layout = self.layout()
        if isinstance(layout, QHBoxLayout):
            layout.insertWidget(max(1, layout.count() - 1), widget)


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


class DialogHeader(QFrame):
    """Consistent dialog identity, context, description, and action zone."""

    CONTEXT_ROLES = frozenset(
        {"neutral", "observation", "report", "learning_conference"}
    )

    def __init__(
        self,
        title: str,
        context: str = "",
        description: str = "",
        *,
        icon_name: str = "info",
        context_role: str = "neutral",
    ) -> None:
        super().__init__()
        if context_role not in self.CONTEXT_ROLES:
            raise ValueError(f"Unbekannte Dialog-Kontextrolle: {context_role}")
        self.setObjectName("DialogHeader")
        self.setProperty("dialogContext", context_role)
        self.setAccessibleName(title)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 14)
        layout.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("DialogHeaderIcon")
        self.icon_label.setFixedSize(42, 42)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(
            load_icon(icon_name).pixmap(ICON_SIZE_LARGE, ICON_SIZE_LARGE)
        )
        self.icon_label.setAccessibleName("")
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("DialogHeaderTitle")
        self.title_label.setWordWrap(True)
        set_label_style(self.title_label, "dialog_title")
        self.context_label = QLabel(context)
        self.context_label.setObjectName("DialogHeaderContext")
        self.context_label.setWordWrap(True)
        set_label_style(self.context_label, "field_label")
        self.context_label.setVisible(bool(context))
        self.description_label = QLabel(description)
        self.description_label.setObjectName("DialogHeaderDescription")
        self.description_label.setWordWrap(True)
        set_label_style(self.description_label, "muted")
        self.description_label.setVisible(bool(description))
        heading.addWidget(self.title_label)
        heading.addWidget(self.context_label)
        heading.addWidget(self.description_label)
        layout.addLayout(heading, 1)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)
        layout.addLayout(self.actions_layout)

    def add_action(self, action: QWidget) -> None:
        """Add one compact status or dialog-level action."""
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
            install_pointer_cursor(button)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            accessible_label = label.replace("&&", "\0").replace("&", "").replace("\0", "&")
            button.setAccessibleName(accessible_label)
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
        self.selection_indicator = QFrame(self)
        self.selection_indicator.setObjectName("SegmentedControlIndicator")
        self.selection_indicator.setFixedHeight(2)
        self.selection_indicator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.selection_indicator.hide()
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
        self._move_selection_indicator(key, animated=changed and self.isVisible())
        if changed and self.isVisible():
            animate_selection(self._buttons[key], key="segment_selection")
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
            key = self._keys[button_id]
            self._move_selection_indicator(key, animated=self.isVisible())
            animate_selection(
                self._buttons[key],
                key="segment_selection",
            )
            self.selection_changed.emit(key)

    def showEvent(self, event: object) -> None:  # noqa: N802
        super().showEvent(event)
        self._move_selection_indicator(self.current_key(), animated=False)

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._move_selection_indicator(self.current_key(), animated=False)

    def _move_selection_indicator(self, key: str, *, animated: bool) -> None:
        button = self._buttons.get(key)
        if button is None:
            self.selection_indicator.hide()
            return
        target = QRect(
            button.x() + 7,
            max(0, self.height() - 3),
            max(4, button.width() - 14),
            2,
        )
        if self.selection_indicator.isHidden() or not animated:
            self.selection_indicator.setGeometry(target)
            self.selection_indicator.show()
            self.selection_indicator.raise_()
            return
        animate_value(
            self.selection_indicator,
            "segment_indicator",
            self.selection_indicator.geometry(),
            target,
            self.selection_indicator.setGeometry,
            MOTION_SELECTION_MS,
            QEasingCurve.Type.OutCubic,
        )
        self.selection_indicator.raise_()


class SearchField(QLineEdit):
    """Search input with a clear affordance and Escape-key reset."""

    def __init__(
        self,
        placeholder: str,
        *,
        accessible_name: str = "Schüler suchen",
        accessible_description: str = (
            "Filtert die sichtbare Schülerliste während der Eingabe."
        ),
    ) -> None:
        super().__init__()
        self.setObjectName("SearchField")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.addAction(load_icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.setAccessibleName(accessible_name)
        self.setAccessibleDescription(accessible_description)
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.find_shortcut.activated.connect(self.setFocus)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self.text():
            self.clear()
            event.accept()
            return
        super().keyPressEvent(event)


class StatusBadge(QLabel):
    """Compact, neutral status label."""

    def __init__(
        self,
        text: str = "",
        *,
        tone: str = "neutral",
        rating_token: str = "",
    ) -> None:
        super().__init__(text)
        self.setObjectName("StatusBadge")
        self.setProperty("badgeTone", tone)
        if rating_token:
            apply_rating_badge_variant(self, rating_token)
        self.setAccessibleName(text)

    def setText(self, text: str) -> None:  # noqa: N802
        """Keep the spoken status synchronized with its visible wording."""
        super().setText(text)
        self.setAccessibleName(text)


def apply_rating_badge_variant(widget: QWidget, rating_token: str) -> None:
    """Apply the shared four-level rating palette without owning rating logic."""
    if rating_token not in {"--", "-", "+", "++"}:
        raise ValueError(f"Unbekannte Bewertungsstufe: {rating_token}")
    widget.setProperty("ratingBadge", True)
    widget.setProperty("ratingToken", rating_token)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class RatingBadgeButton(QPushButton):
    """Checkable rating badge with visible and spoken selection state."""

    def __init__(self, text: str, rating_token: str) -> None:
        super().__init__(text)
        self._rating_text = text
        self._rating_token = rating_token
        self._compact = False
        self.setObjectName("RatingBadgeButton")
        self.setProperty("compact", False)
        self.setCheckable(True)
        install_pointer_cursor(self)
        apply_rating_badge_variant(self, rating_token)
        install_button_motion(self)
        self.toggled.connect(self._sync_selection_state)
        self._sync_selection_state(False)

    def set_compact(self, compact: bool) -> None:
        """Show only the symbol when the selector cannot fit full meanings."""
        if self._compact == compact:
            return
        self._compact = compact
        self.setProperty("compact", compact)
        self.setToolTip(self._rating_text if compact else "")
        self._sync_selection_state(self.isChecked())

    def _sync_selection_state(self, selected: bool) -> None:
        visible_text = self._rating_token if self._compact else self._rating_text
        self.setText(f"✓ {visible_text}" if selected else visible_text)
        state = "ausgewählt" if selected else "nicht ausgewählt"
        self.setAccessibleName(f"Bewertung {self._rating_text}, {state}")
        self.setAccessibleDescription(
            "Gespeicherte Bewertungsstufe. "
            f"Aktueller Auswahlstatus: {state}."
        )
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        if selected and self.isVisible():
            animate_selection(self, key="rating_selection")

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)


class CourseBadge(QFrame):
    """Compact course context whose visible text never depends on color."""

    NEUTRAL_COLOR = "#6B7280"

    def __init__(self, course_name: str = "", color_hex: str = "") -> None:
        super().__init__()
        self.setObjectName("CourseBadge")
        self.setProperty("semanticRole", "courseContext")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 2, 8, 2)
        layout.setSpacing(6)
        self.indicator = QFrame()
        self.indicator.setObjectName("CourseBadgeIndicator")
        self.indicator.setFixedSize(8, 8)
        self.indicator.setAccessibleName("")
        self.label = QLabel()
        self.label.setObjectName("CourseBadgeLabel")
        self.label.setAccessibleName("")
        layout.addWidget(self.indicator)
        layout.addWidget(self.label)
        self.set_course(course_name, color_hex)

    def set_course(self, course_name: str, color_hex: str = "") -> None:
        """Update the visible course name and its supporting master-data color."""
        visible_name = course_name.strip() or "Kein Kurs"
        color = QColor(color_hex.strip())
        uses_neutral_color = not color.isValid()
        if uses_neutral_color:
            color = QColor(self.NEUTRAL_COLOR)

        background = self._blend_with_white(color, 0.12)
        border = self._blend_with_white(color, 0.38)
        accent_hex = color.name().upper()
        background_hex = background.name().upper()
        border_hex = border.name().upper()
        self.setStyleSheet(
            f"""
            QFrame#CourseBadge {{
                background-color: {background_hex};
                border: 1px solid {border_hex};
                border-radius: 10px;
            }}
            QFrame#CourseBadgeIndicator {{
                background-color: {accent_hex};
                border: none;
                border-radius: 4px;
            }}
            QLabel#CourseBadgeLabel {{
                background-color: transparent;
                color: #24313A;
                border: none;
                font-size: 11px;
                font-weight: 650;
            }}
            """
        )
        self.label.setText(visible_name)
        self.setProperty("courseColorHex", accent_hex)
        self.setProperty("usesNeutralColor", uses_neutral_color)
        accessible_name = f"Kurszugehörigkeit: {visible_name}"
        self.setAccessibleName(accessible_name)
        self.setToolTip(accessible_name)

    @staticmethod
    def _blend_with_white(color: QColor, color_share: float) -> QColor:
        return QColor(
            round(color.red() * color_share + 255 * (1 - color_share)),
            round(color.green() * color_share + 255 * (1 - color_share)),
            round(color.blue() * color_share + 255 * (1 - color_share)),
        )


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
        self._update_accessibility()
        self.setVisible(bool(text or title))

    def set_message(self, text: str) -> None:
        """Show the state only while it has meaningful content."""
        self.label.setText(text)
        self._update_accessibility()
        self.setVisible(bool(text))

    def _update_accessibility(self) -> None:
        spoken = ". ".join(
            part.strip().rstrip(".")
            for part in (self.title_label.text(), self.label.text())
            if part.strip()
        )
        self.setAccessibleName(f"{spoken}." if spoken else "")


class Toast(QFrame):
    """Non-blocking, automatically disappearing shell feedback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setMinimumWidth(280)
        self.setMaximumWidth(520)
        size_policy = self.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        self.setSizePolicy(size_policy)
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
        stop_motion(self)
        self.setGraphicsEffect(None)
        self.show()
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
        self.setGraphicsEffect(None)
        self.hide()

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
    install_pointer_cursor(button)
    install_button_motion(button)
    if accessible_name:
        button.setAccessibleName(accessible_name)


def ensure_button_text_width(button: QPushButton, *, horizontal_chrome: int = 40) -> int:
    """Reserve complete text, padding and focus chrome after final font polishing."""
    button.ensurePolished()
    required_width = button.fontMetrics().horizontalAdvance(button.text()) + horizontal_chrome
    button.setMinimumWidth(max(button.minimumWidth(), required_width))
    button.updateGeometry()
    return button.minimumWidth()


def stabilize_message_box_buttons(
    message: QMessageBox,
    buttons: Iterable[QPushButton],
    *,
    spacing: int = 12,
) -> None:
    """Keep long message-box actions complete under native macOS focus metrics."""
    for button in buttons:
        ensure_button_text_width(button)
    button_box = message.findChild(QDialogButtonBox)
    if button_box is not None and button_box.layout() is not None:
        button_box.layout().setSpacing(max(spacing, button_box.layout().spacing()))
    message.ensurePolished()
    message.adjustSize()


def create_confirmation_message(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    confirm_text: str,
    cancel_text: str = "Abbrechen",
) -> tuple[QMessageBox, QPushButton]:
    """Build an explicit, safe-by-default product confirmation message."""
    message = QMessageBox(parent)
    message.setWindowTitle(title)
    message.setText(text)
    cancel = message.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    confirm = message.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
    configure_button(cancel, "secondary", cancel_text)
    configure_button(confirm, "primary", confirm_text)
    cancel.setDefault(True)
    confirm.setAutoDefault(False)
    message.setDefaultButton(cancel)
    message.setEscapeButton(cancel)
    stabilize_message_box_buttons(message, (cancel, confirm))
    return message, confirm
