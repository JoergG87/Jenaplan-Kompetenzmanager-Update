"""Central, optional motion primitives for the PySide desktop app."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QWidget,
)

from src.desktop_app.theme import MOTION_FAST_MS, MOTION_STANDARD_MS


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


class _CardMotionController(QObject):
    """Translate pointer presence into layout-neutral card elevation."""

    def __init__(self, card: QWidget) -> None:
        super().__init__(card)
        self.card = card
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
        if watched is getattr(self, "card", None):
            if event.type() == QEvent.Type.Enter:
                self._set_hovered(True)
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.EnabledChange):
                self._set_hovered(False)
        return super().eventFilter(watched, event)

    def _set_hovered(self, hovered: bool) -> None:
        if not self._installed:
            return
        start_value = float(getattr(self.card, "_motion_hover_progress", 0.0))

        def update(value: Any) -> None:
            progress = float(value)
            setattr(self.card, "_motion_hover_progress", progress)
            self.effect.setBlurRadius(12.0 * progress)
            self.effect.setOffset(0.0, 2.0 * progress)
            self.effect.setColor(QColor(31, 65, 97, round(46 * progress)))

        animate_value(
            self.card,
            "card_hover",
            start_value,
            1.0 if hovered and self.card.isEnabled() else 0.0,
            update,
            MOTION_FAST_MS,
        )


def install_card_motion(card: QWidget) -> QObject:
    """Install the shared interactive-card hover behavior exactly once."""
    controller = getattr(card, "_motion_card_controller", None)
    if controller is None:
        controller = _CardMotionController(card)
        setattr(card, "_motion_card_controller", controller)
    return controller
