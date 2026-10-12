"""Central, optional motion primitives for the PySide desktop app."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
import weakref
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QRect,
    QTimer,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QListWidget,
    QPushButton,
    QWidget,
)

from src.desktop_app.theme import (
    MOTION_DIALOG_MS,
    MOTION_FAST_MS,
    MOTION_HOVER_MS,
    MOTION_PRESSED_MS,
    MOTION_SELECTION_MS,
    MOTION_STANDARD_MS,
)


class MotionPolicy(QObject):
    """Own the application-wide reduced-motion preference."""

    changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._reduced_motion = False

    @property
    def reduced_motion(self) -> bool:
        return self._reduced_motion

    def set_reduced_motion(self, enabled: bool) -> None:
        normalized = bool(enabled)
        if normalized == self._reduced_motion:
            return
        self._reduced_motion = normalized
        self.changed.emit(normalized)


motion_policy = MotionPolicy()


def set_reduced_motion(enabled: bool) -> None:
    """Set the global motion preference."""
    motion_policy.set_reduced_motion(enabled)


def reduced_motion_enabled() -> bool:
    """Return whether transitions must resolve without movement."""
    return motion_policy.reduced_motion


def motion_duration(duration_ms: int) -> int:
    """Return the effective duration for the current policy."""
    if reduced_motion_enabled():
        return 0
    return max(0, int(duration_ms))


def _animations(owner: QObject) -> dict[str, QVariantAnimation]:
    animations = getattr(owner, "_motion_animations", None)
    if animations is None:
        animations = {}
        setattr(owner, "_motion_animations", animations)
    return animations


def _animation_cache(owner: QObject) -> dict[str, QVariantAnimation]:
    cache = getattr(owner, "_motion_animation_cache", None)
    if cache is None:
        cache = {}
        setattr(owner, "_motion_animation_cache", cache)
    return cache


def stop_motion(owner: QObject, key: str | None = None) -> None:
    """Stop one transition, or all transitions, owned by a widget."""
    animations = getattr(owner, "_motion_animations", None)
    if not animations:
        return
    keys = [key] if key is not None else list(animations)
    for current_key in keys:
        animation = animations.pop(current_key, None)
        if animation is None:
            continue
        animation.stop()
        if getattr(animation, "_motion_connected", False):
            animation.valueChanged.disconnect()
            animation.finished.disconnect()
            setattr(animation, "_motion_connected", False)


def animate_value(
    owner: QObject,
    key: str,
    start_value: Any,
    end_value: Any,
    update: Callable[[Any], None],
    duration_ms: int = MOTION_STANDARD_MS,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QVariantAnimation | None:
    """Animate one value while replacing a transition with the same key."""
    animations = _animations(owner)
    cache = _animation_cache(owner)
    animation = cache.get(key)
    if animation is not None:
        animation.stop()
        animations.pop(key, None)
        if getattr(animation, "_motion_connected", False):
            animation.valueChanged.disconnect()
            animation.finished.disconnect()
            setattr(animation, "_motion_connected", False)
    effective_duration = motion_duration(duration_ms)
    if effective_duration == 0:
        update(end_value)
        return None

    if animation is None:
        animation = QVariantAnimation(owner)
        cache[key] = animation
    animation.setStartValue(start_value)
    animation.setEndValue(end_value)
    animation.setDuration(effective_duration)
    animation.setEasingCurve(easing)
    animation.valueChanged.connect(update)
    animations[key] = animation

    def release() -> None:
        animations = getattr(owner, "_motion_animations", None)
        if animations is not None and animations.get(key) is animation:
            animations.pop(key, None)

    animation.finished.connect(release)
    setattr(animation, "_motion_connected", True)
    animation.start()
    return animation


def _opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect | None:
    if sys.platform == "ios":
        return None
    effect = getattr(widget, "_motion_opacity_effect", None)
    if effect is not None:
        return effect
    existing = widget.graphicsEffect()
    if existing is not None:
        return None
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(1.0)
    widget.setGraphicsEffect(effect)
    setattr(widget, "_motion_opacity_effect", effect)
    return effect


def animate_opacity(
    widget: QWidget,
    *,
    visible: bool,
    duration_ms: int = MOTION_STANDARD_MS,
    key: str = "opacity",
) -> QVariantAnimation | None:
    """Fade a widget without delaying its already-applied semantic state."""
    was_hidden = widget.isHidden()
    effect = _opacity_effect(widget)
    if effect is None:
        stop_motion(widget, key)
        widget.setVisible(visible)
        return None
    if visible:
        widget.show()
    start_value = 0.0 if visible and was_hidden else effect.opacity()
    effect.setOpacity(start_value)
    end_value = 1.0 if visible else 0.0
    easing = QEasingCurve.Type.OutCubic if visible else QEasingCurve.Type.InCubic
    animation = animate_value(
        widget,
        key,
        start_value,
        end_value,
        effect.setOpacity,
        duration_ms,
        easing,
    )

    if animation is None:
        widget.setVisible(visible)
    elif not visible:
        def finish_hide() -> None:
            widget.hide()

        animation.finished.connect(finish_hide)
    return animation


def animate_feedback(
    widget: QWidget,
    *,
    key: str = "feedback",
    duration_ms: int = MOTION_FAST_MS,
) -> QVariantAnimation | None:
    """Confirm an already completed interaction with a short opacity pulse."""
    effect = _opacity_effect(widget)
    if effect is None:
        return None
    effect.setOpacity(0.78)
    return animate_value(
        widget,
        key,
        effect.opacity(),
        1.0,
        effect.setOpacity,
        duration_ms,
        QEasingCurve.Type.OutCubic,
    )


def animate_selection(
    widget: QWidget,
    *,
    key: str = "selection",
) -> QVariantAnimation | None:
    """Confirm a selected control without delaying its check state or label."""
    effect = _opacity_effect(widget)
    if effect is None:
        return None
    effect.setOpacity(0.82)
    return animate_value(
        widget,
        key,
        effect.opacity(),
        1.0,
        effect.setOpacity,
        MOTION_SELECTION_MS,
        QEasingCurve.Type.OutCubic,
    )


def animate_save_confirmation(button: QPushButton) -> QVariantAnimation | None:
    """Show one short, semantic confirmation on a persistent save action."""
    button.setProperty("saveConfirmed", True)
    button.style().unpolish(button)
    button.style().polish(button)
    animation = animate_selection(button, key="save_confirmation")

    def reset() -> None:
        button.setProperty("saveConfirmed", False)
        button.style().unpolish(button)
        button.style().polish(button)

    reset_timer = getattr(button, "_motion_save_confirmation_timer", None)
    if reset_timer is None:
        reset_timer = QTimer(button)
        reset_timer.setSingleShot(True)
        reset_timer.timeout.connect(reset)
        setattr(button, "_motion_save_confirmation_timer", reset_timer)
    reset_timer.start(520)
    return animation


class MotionDialog(QDialog):
    """Product dialog with quiet open and close transitions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._motion_dialog_closing = False
        self._motion_dialog_origin = QPoint()

    @staticmethod
    def _supports_window_motion() -> bool:
        return (
            not reduced_motion_enabled()
            and QApplication.platformName().casefold() not in {"offscreen", "minimal"}
        )

    def showEvent(self, event: object) -> None:  # noqa: N802
        super().showEvent(event)
        self._motion_dialog_closing = False
        self._motion_dialog_origin = self.pos()
        if not self._supports_window_motion():
            self.setWindowOpacity(1.0)
            return
        self.setWindowOpacity(0.0)
        moves = not self.isMaximized() and not self.isFullScreen()
        if moves:
            self.move(self._motion_dialog_origin + QPoint(0, 5))

        def update(value: Any) -> None:
            progress = float(value)
            self.setWindowOpacity(progress)
            if moves:
                self.move(
                    self._motion_dialog_origin
                    + QPoint(0, round(5.0 * (1.0 - progress)))
                )

        animate_value(
            self,
            "dialog_open",
            0.0,
            1.0,
            update,
            MOTION_DIALOG_MS,
            QEasingCurve.Type.OutCubic,
        )

    def done(self, result: int) -> None:
        if (
            not self._supports_window_motion()
            or not self.isVisible()
            or self._motion_dialog_closing
            or QApplication.closingDown()
        ):
            QDialog.done(self, result)
            return
        self._motion_dialog_closing = True
        stop_motion(self, "dialog_open")
        start_opacity = self.windowOpacity()

        def update(value: Any) -> None:
            self.setWindowOpacity(float(value))

        animation = animate_value(
            self,
            "dialog_close",
            start_opacity,
            0.0,
            update,
            MOTION_DIALOG_MS,
            QEasingCurve.Type.InCubic,
        )
        if animation is None:
            self.setWindowOpacity(1.0)
            QDialog.done(self, result)
            return

        def finish() -> None:
            self.setWindowOpacity(1.0)
            QDialog.done(self, result)

        animation.finished.connect(finish)


class _ButtonMotionController(QObject):
    """Add short pointer and focus feedback without changing button geometry."""

    def __init__(self, button: QPushButton) -> None:
        super().__init__(button)
        self._button_ref = weakref.ref(button)
        self.effect: QGraphicsOpacityEffect | None = None
        button.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        button = self._button_ref()
        if button is not None and watched is button:
            event_type = event.type()
            if event_type in (QEvent.Type.Enter, QEvent.Type.FocusIn):
                self._respond(0.94, MOTION_HOVER_MS, "button_hover")
            elif event_type == QEvent.Type.MouseButtonPress:
                self._respond(0.86, MOTION_PRESSED_MS, "button_pressed", 0.94)
            elif event_type == QEvent.Type.MouseButtonRelease:
                effect = self._ensure_effect()
                if effect is not None:
                    self._respond(
                        effect.opacity(),
                        MOTION_PRESSED_MS,
                        "button_pressed",
                    )
            elif (
                event_type == QEvent.Type.EnabledChange
                and not button.isEnabled()
                and self.effect is not None
            ):
                stop_motion(button)
                self.effect.setOpacity(1.0)
        return False

    def _ensure_effect(self) -> QGraphicsOpacityEffect | None:
        button = self._button_ref()
        if button is None:
            return None
        if self.effect is None:
            self.effect = _opacity_effect(button)
        return self.effect

    def _respond(
        self,
        start: float,
        duration_ms: int,
        key: str,
        end: float = 1.0,
    ) -> None:
        button = self._button_ref()
        effect = self._ensure_effect()
        if button is None or not button.isEnabled() or effect is None:
            return
        stop_motion(button)
        effect.setOpacity(start)
        animate_value(
            button,
            key,
            start,
            end,
            effect.setOpacity,
            duration_ms,
            QEasingCurve.Type.OutCubic,
        )


def install_button_motion(button: QPushButton) -> QObject:
    """Install the shared button microinteraction exactly once."""
    controller = getattr(button, "_motion_button_controller", None)
    if controller is None:
        controller = _ButtonMotionController(button)
        setattr(button, "_motion_button_controller", controller)
    return controller


class _PointerCursorController(QObject):
    """Keep a pointing cursor local to the currently hovered interactive widget."""

    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self._widget_ref = weakref.ref(widget)
        self._inside = False
        widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        widget = self._widget_ref()
        if widget is None or watched is not widget:
            return False
        event_type = event.type()
        if event_type == QEvent.Type.Enter and widget.isEnabled():
            self._inside = True
            widget.setCursor(Qt.CursorShape.PointingHandCursor)
        elif event_type in {
            QEvent.Type.Leave,
            QEvent.Type.Hide,
            QEvent.Type.Close,
        }:
            self._inside = False
            widget.unsetCursor()
        elif event_type == QEvent.Type.EnabledChange:
            if widget.isEnabled() and self._inside:
                widget.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                widget.unsetCursor()
        elif event_type == QEvent.Type.MouseButtonRelease:
            widget_ref = self._widget_ref
            controller_ref = weakref.ref(self)

            def reconcile_after_click() -> None:
                current = widget_ref()
                controller = controller_ref()
                if current is None or controller is None:
                    return
                try:
                    if (
                        current.isVisible()
                        and current.isEnabled()
                        and controller._inside
                    ):
                        current.setCursor(Qt.CursorShape.PointingHandCursor)
                    else:
                        current.unsetCursor()
                except RuntimeError:
                    return

            QTimer.singleShot(0, reconcile_after_click)
        return False


def install_pointer_cursor(widget: QWidget) -> QObject:
    """Derive an interactive widget's cursor from its current hover state."""
    controller = getattr(widget, "_pointer_cursor_controller", None)
    if controller is None:
        controller = _PointerCursorController(widget)
        setattr(widget, "_pointer_cursor_controller", controller)
    return controller


class _CardMotionController(QObject):
    """Translate pointer presence into layout-neutral card elevation."""

    def __init__(self, card: QWidget) -> None:
        super().__init__(card)
        self._card_ref = weakref.ref(card)
        setattr(card, "_motion_hover_progress", 0.0)
        self.effect = QGraphicsDropShadowEffect(card)
        self.effect.setBlurRadius(0.0)
        self.effect.setOffset(0.0, 0.0)
        self.effect.setColor(QColor(31, 65, 97, 0))
        self._installed = card.graphicsEffect() is None
        if self._installed:
            card.setGraphicsEffect(self.effect)
            card.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        card = self._card_ref()
        if card is not None and watched is card:
            if event.type() == QEvent.Type.Enter:
                self._set_hovered(True)
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.EnabledChange):
                self._set_hovered(False)
        return False

    def _set_hovered(self, hovered: bool) -> None:
        card = self._card_ref()
        if card is None:
            return
        if not self._installed:
            return
        start_value = float(getattr(card, "_motion_hover_progress", 0.0))

        def update(value: Any) -> None:
            progress = float(value)
            setattr(card, "_motion_hover_progress", progress)
            self.effect.setBlurRadius(14.0 * progress)
            self.effect.setOffset(0.0, 2.0 * progress)
            self.effect.setColor(QColor(31, 65, 97, round(30 * progress)))

        animate_value(
            card,
            "card_hover",
            start_value,
            1.0 if hovered and card.isEnabled() else 0.0,
            update,
            MOTION_HOVER_MS,
        )


def install_card_motion(card: QWidget) -> QObject:
    """Install the shared interactive-card hover behavior exactly once."""
    if sys.platform == "ios":
        return install_pointer_cursor(card)
    controller = getattr(card, "_motion_card_controller", None)
    if controller is None:
        controller = _CardMotionController(card)
        setattr(card, "_motion_card_controller", controller)
    return controller


class _ItemSelectionController(QObject):
    """Move one tiny overlay along a list without animating list content."""

    def __init__(self, list_widget: QListWidget) -> None:
        super().__init__(list_widget)
        self._list_widget_ref = weakref.ref(list_widget)
        self.viewport = list_widget.viewport()
        self.indicator = QFrame(self.viewport)
        self.indicator.setObjectName("NavigationSelectionIndicator")
        self.indicator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.indicator.hide()
        list_widget.currentRowChanged.connect(self._move_to_current)
        self.viewport.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is getattr(self, "viewport", None) and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            list_widget = self._list_widget_ref()
            if list_widget is None:
                return False
            try:
                row = list_widget.currentRow()
            except (AttributeError, RuntimeError):
                return False
            self._move_to_current(row, animated=False)
        return False

    def _move_to_current(self, row: int, *, animated: bool = True) -> None:
        list_widget = self._list_widget_ref()
        if list_widget is None:
            return
        try:
            item = list_widget.item(row)
        except RuntimeError:
            return
        if item is None or not item.flags():
            self.indicator.hide()
            return
        rect = list_widget.visualItemRect(item)
        target = QRect(1, rect.top() + 5, 3, max(4, rect.height() - 10))
        if self.indicator.isHidden() or not animated:
            self.indicator.setGeometry(target)
            self.indicator.show()
            self.indicator.raise_()
            return
        animate_value(
            self.indicator,
            "navigation_selection",
            self.indicator.geometry(),
            target,
            self.indicator.setGeometry,
            MOTION_SELECTION_MS,
            QEasingCurve.Type.OutCubic,
        )
        self.indicator.raise_()


def install_item_selection_motion(list_widget: QListWidget) -> QObject:
    """Install one layout-neutral active-item indicator on a compact list."""
    controller = getattr(list_widget, "_motion_selection_controller", None)
    if controller is None:
        controller = _ItemSelectionController(list_widget)
        setattr(list_widget, "_motion_selection_controller", controller)
    return controller
