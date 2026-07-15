"""State and lifecycle tests for the central desktop motion system."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from src.desktop_app.components import (
    AppCard,
    FilterChip,
    InlineMessage,
    SegmentedControl,
    Toast,
)
from src.desktop_app.motion import (
    animate_opacity,
    animate_value,
    motion_duration,
    reduced_motion_enabled,
    set_reduced_motion,
    stop_motion,
)
from src.desktop_app.theme import MOTION_FAST_MS, MOTION_STANDARD_MS


class MotionSystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        set_reduced_motion(False)

    def tearDown(self) -> None:
        set_reduced_motion(False)
        self.app.processEvents()

    def test_policy_resolves_reduced_motion_to_immediate_end_state(self) -> None:
        owner = QObject()
        values: list[float] = []

        set_reduced_motion(True)
        animation = animate_value(owner, "value", 0.0, 1.0, values.append)

        self.assertTrue(reduced_motion_enabled())
        self.assertEqual(motion_duration(MOTION_STANDARD_MS), 0)
        self.assertIsNone(animation)
        self.assertEqual(values, [1.0])

    def test_normal_animation_reaches_end_state_and_releases_ownership(self) -> None:
        owner = QObject()
        values: list[float] = []

        animation = animate_value(
            owner,
            "value",
            0.0,
            1.0,
            values.append,
            MOTION_FAST_MS,
        )
        self.assertIsNotNone(animation)
        self.assertEqual(list(owner._motion_animations), ["value"])

        animation.setCurrentTime(MOTION_FAST_MS)

        self.assertAlmostEqual(values[-1], 1.0)
        self.assertEqual(owner._motion_animations, {})

    def test_repeated_animation_replaces_same_key_without_stacking(self) -> None:
        owner = QObject()
        values: list[float] = []
        first = animate_value(owner, "value", 0.0, 1.0, values.append, 240)
        second = animate_value(owner, "value", 0.2, 2.0, values.append, 120)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(owner._motion_animations, {"value": second})

        second.setCurrentTime(120)
        self.assertAlmostEqual(values[-1], 2.0)
        self.assertEqual(owner._motion_animations, {})

    def test_opacity_has_matching_normal_and_reduced_end_states(self) -> None:
        widget = QWidget()
        widget.hide()
        fade_in = animate_opacity(widget, visible=True, duration_ms=MOTION_FAST_MS)
        self.assertIsNotNone(fade_in)
        fade_in.setCurrentTime(MOTION_FAST_MS)
        self.assertFalse(widget.isHidden())
        self.assertAlmostEqual(widget.graphicsEffect().opacity(), 1.0)

        fade_out = animate_opacity(widget, visible=False, duration_ms=MOTION_FAST_MS)
        self.assertIsNotNone(fade_out)
        fade_out.setCurrentTime(MOTION_FAST_MS)
        self.assertTrue(widget.isHidden())

        set_reduced_motion(True)
        animate_opacity(widget, visible=True)
        self.assertFalse(widget.isHidden())
        self.assertAlmostEqual(widget.graphicsEffect().opacity(), 1.0)
        animate_opacity(widget, visible=False)
        self.assertTrue(widget.isHidden())

    def test_interactive_card_reuses_controller_during_repeated_hover(self) -> None:
        card = AppCard("interactive", interactive=True)
        controller = card._motion_card_controller

        for _ in range(4):
            controller._set_hovered(True)

        self.assertIs(card._motion_card_controller, controller)
        self.assertEqual(list(card._motion_animations), ["card_hover"])
        card._motion_animations["card_hover"].setCurrentTime(MOTION_FAST_MS)
        self.assertAlmostEqual(card._motion_hover_progress, 1.0)
        self.assertAlmostEqual(controller.effect.blurRadius(), 14.0)
        self.assertAlmostEqual(controller.effect.offset().y(), 2.0)
        self.assertEqual(controller.effect.color().alpha(), 30)

        controller._set_hovered(False)
        card._motion_animations["card_hover"].setCurrentTime(MOTION_FAST_MS)
        self.assertAlmostEqual(card._motion_hover_progress, 0.0)

        QTest.mousePress(card, Qt.MouseButton.LeftButton)
        self.assertTrue(card.property("pressed"))
        QTest.mouseRelease(card, Qt.MouseButton.LeftButton)
        self.assertFalse(card.property("pressed"))
        self.assertEqual(card.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        card.setDisabled(True)
        controller._set_hovered(True)
        card._motion_animations["card_hover"].setCurrentTime(MOTION_FAST_MS)
        self.assertAlmostEqual(card._motion_hover_progress, 0.0)
        card.close()

    def test_rapid_segment_changes_keep_state_and_signal_count_exact(self) -> None:
        control = SegmentedControl(
            (("groups", "Stammgruppen"), ("courses", "Kurse"), ("all", "Alle"))
        )
        selected: list[str] = []
        control.selection_changed.connect(selected.append)
        control.show()
        self.app.processEvents()

        control.set_current_key("courses", emit=True)
        control.set_current_key("all", emit=True)
        control.set_current_key("groups", emit=True)

        self.assertEqual(control.current_key(), "groups")
        self.assertEqual(selected, ["courses", "all", "groups"])
        self.assertTrue(control._buttons["groups"].isChecked())
        self.assertLessEqual(len(control._buttons["groups"]._motion_animations), 1)
        control.close()

    def test_filter_reset_is_immediate_and_emitted_once(self) -> None:
        chip = FilterChip()
        requests: list[bool] = []
        chip.remove_requested.connect(lambda: requests.append(True))
        chip.set_label("Kurs: Blau")

        chip.click()

        self.assertEqual(requests, [True])

    def test_inline_warning_is_immediate_in_both_motion_modes(self) -> None:
        message = InlineMessage()

        message.set_message("Eingabe prüfen.", tone="warning")
        self.assertFalse(message.isHidden())
        self.assertEqual(message.property("messageTone"), "warning")

        message.hide()
        set_reduced_motion(True)
        message.set_message("Weiterhin prüfen.", tone="error")
        self.assertFalse(message.isHidden())
        self.assertEqual(message.label.text(), "Weiterhin prüfen.")

    def test_toast_replacement_hover_pause_and_lifecycle_are_stable(self) -> None:
        toast = Toast()
        toast.show_message("Erste Meldung", duration_ms=70)
        toast.show_message("Zweite Meldung", duration_ms=70)

        self.assertEqual(toast.text(), "Zweite Meldung")
        self.assertLessEqual(len(toast._motion_animations), 1)
        QApplication.sendEvent(toast, QEvent(QEvent.Type.Enter))
        QTest.qWait(100)
        self.assertFalse(toast.isHidden())

        QApplication.sendEvent(toast, QEvent(QEvent.Type.Leave))
        self.assertTrue(toast.timer.isActive())
        toast._dismiss()
        fade_out = toast._motion_animations.get("opacity")
        self.assertIsNotNone(fade_out)
        fade_out.setCurrentTime(MOTION_STANDARD_MS)
        self.assertTrue(toast.isHidden())
        self.assertEqual(toast._motion_animations, {})

        toast.show_message("Letzte Meldung", duration_ms=10_000)
        toast.clear()
        self.assertTrue(toast.isHidden())
        self.assertEqual(toast.text(), "")
        self.assertEqual(toast._motion_animations, {})

    def test_toast_tones_and_long_text_keep_one_shared_component_contract(self) -> None:
        toast = Toast()
        long_text = "Ausführliche Rückmeldung " * 20

        for tone in ("success", "info", "warning", "error"):
            toast.show_message(long_text, tone=tone, duration_ms=10_000)
            self.assertEqual(toast.property("toastTone"), tone)
            self.assertEqual(toast.text(), long_text)
            self.assertEqual(toast.accessibleDescription(), long_text)
            self.assertTrue(toast.label.wordWrap())
            self.assertEqual(toast.minimumWidth(), 280)
            self.assertEqual(toast.maximumWidth(), 520)

        toast.clear()

    def test_reduced_motion_toast_uses_timer_but_no_transition(self) -> None:
        set_reduced_motion(True)
        toast = Toast()
        toast.show_message("Kurz sichtbar", duration_ms=20)
        self.assertFalse(toast.isHidden())
        self.assertEqual(getattr(toast, "_motion_animations", {}), {})
        self.assertTrue(toast.timer.isActive())

        toast._dismiss()

        self.assertTrue(toast.isHidden())
        self.assertEqual(getattr(toast, "_motion_animations", {}), {})

    def test_stop_and_widget_deletion_leave_no_running_transition(self) -> None:
        widget = QWidget()
        animate_opacity(widget, visible=True, duration_ms=240)
        stop_motion(widget)
        self.assertEqual(widget._motion_animations, {})

        widget.deleteLater()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
