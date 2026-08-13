"""State and lifecycle tests for the central desktop motion system."""

from __future__ import annotations

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.desktop_app.components import (
    AppCard,
    FilterChip,
    InlineMessage,
    SectionHeader,
    SegmentedControl,
    StatusBadge,
    Toast,
)
from src.desktop_app.motion import (
    MotionDialog,
    animate_opacity,
    animate_save_confirmation,
    animate_value,
    install_item_selection_motion,
    install_pointer_cursor,
    motion_duration,
    reduced_motion_enabled,
    set_reduced_motion,
    stop_motion,
)
from src.desktop_app.theme import (
    MOTION_FAST_MS,
    MOTION_SELECTION_MS,
    MOTION_STANDARD_MS,
    apply_app_theme,
)


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
        self.assertTrue(toast.sizePolicy().retainSizeWhenHidden())
        toast.show_message("Erste Meldung", duration_ms=70)
        toast.show_message("Zweite Meldung", duration_ms=70)

        self.assertEqual(toast.text(), "Zweite Meldung")
        self.assertEqual(getattr(toast, "_motion_animations", {}), {})
        QApplication.sendEvent(toast, QEvent(QEvent.Type.Enter))
        QTest.qWait(100)
        self.assertFalse(toast.isHidden())

        QApplication.sendEvent(toast, QEvent(QEvent.Type.Leave))
        self.assertTrue(toast.timer.isActive())
        toast._dismiss()
        self.assertTrue(toast.isHidden())
        self.assertEqual(getattr(toast, "_motion_animations", {}), {})
        toast.show_message("Letzte Meldung", duration_ms=10_000)
        toast.clear()
        self.assertTrue(toast.isHidden())
        self.assertEqual(toast.text(), "")
        self.assertEqual(getattr(toast, "_motion_animations", {}), {})

    def test_button_badge_and_save_feedback_share_reduced_motion_policy(self) -> None:
        button = QPushButton("Speichern")
        from src.desktop_app.components import RatingBadgeButton, configure_button

        configure_button(button, "primary", "Änderungen speichern")
        self.assertIsNotNone(button._motion_button_controller)

        badge = RatingBadgeButton("+ sicher", "+")
        badge.show()
        badge.setChecked(True)
        self.assertIn("rating_selection", badge._motion_animations)
        badge._motion_animations["rating_selection"].setCurrentTime(
            MOTION_SELECTION_MS
        )
        self.assertTrue(badge.text().startswith("✓ "))

        animate_save_confirmation(button)
        self.assertTrue(button.property("saveConfirmed"))
        self.assertIn("save_confirmation", button._motion_animations)

        set_reduced_motion(True)
        other = QPushButton("Speichern")
        configure_button(other, "primary")
        self.assertIsNone(animate_save_confirmation(other))
        self.assertEqual(getattr(other, "_motion_animations", {}), {})

    def test_save_feedback_timer_is_cancelled_with_deleted_button(self) -> None:
        button = QPushButton("Speichern")
        errors: list[BaseException] = []
        previous_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _traceback: errors.append(error)
        try:
            animate_save_confirmation(button)
            self.assertTrue(button._motion_save_confirmation_timer.isActive())
            button.deleteLater()
            self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QTest.qWait(600)
            self.app.processEvents()
        finally:
            sys.excepthook = previous_hook

        self.assertEqual(errors, [])

    def test_segment_and_navigation_indicators_move_without_content_animation(self) -> None:
        control = SegmentedControl((("first", "Erste"), ("second", "Zweite")))
        control.resize(300, 38)
        control.show()
        self.app.processEvents()
        start = control.selection_indicator.geometry()

        control.set_current_key("second")

        indicator_animation = control.selection_indicator._motion_animations[
            "segment_indicator"
        ]
        indicator_animation.setCurrentTime(MOTION_SELECTION_MS)
        self.assertGreater(control.selection_indicator.geometry().x(), start.x())

        navigation = QListWidget()
        first = QListWidgetItem("Heute")
        second = QListWidgetItem("Schüler")
        navigation.addItem(first)
        navigation.addItem(second)
        controller = install_item_selection_motion(navigation)
        navigation.resize(220, 160)
        navigation.show()
        navigation.setCurrentRow(0)
        self.app.processEvents()
        first_geometry = controller.indicator.geometry()
        navigation.setCurrentRow(1)
        animation = controller.indicator._motion_animations["navigation_selection"]
        animation.setCurrentTime(MOTION_SELECTION_MS)
        self.assertGreater(controller.indicator.geometry().y(), first_geometry.y())

    def test_dialog_transition_keeps_semantic_state_immediate(self) -> None:
        dialog = MotionDialog()
        dialog.show()
        self.app.processEvents()
        self.assertEqual(getattr(dialog, "_motion_animations", {}), {})
        self.assertAlmostEqual(dialog.windowOpacity(), 1.0)

        dialog.reject()
        self.assertFalse(dialog.isVisible())

        set_reduced_motion(True)
        reduced_dialog = MotionDialog()
        reduced_dialog.show()
        self.app.processEvents()
        self.assertEqual(getattr(reduced_dialog, "_motion_animations", {}), {})
        reduced_dialog.reject()
        self.assertFalse(reduced_dialog.isVisible())

    def test_toast_tones_and_long_text_keep_one_shared_component_contract(self) -> None:
        toast = Toast()
        long_text = "Ausführliche Rückmeldung " * 20

        for tone in ("success", "info", "warning", "error"):
            toast.show_message(long_text, tone=tone, duration_ms=10_000)
            self.assertEqual(toast.property("toastTone"), tone)
            self.assertEqual(toast.text(), long_text)
            self.assertEqual(toast.accessibleDescription(), long_text)
            self.assertTrue(toast.label.wordWrap())
            self.assertLess(toast.minimumWidth(), 280)
            self.assertGreaterEqual(toast.sizeHint().width(), 280)
            self.assertEqual(toast.maximumWidth(), 520)
            self.assertEqual(
                toast.sizeHint().height(),
                toast.heightForWidth(toast.sizeHint().width()),
            )
            self.assertIsNone(toast.graphicsEffect())

        toast.clear()

    def test_success_toast_uses_native_readable_colors_without_compositing(self) -> None:
        previous_stylesheet = self.app.styleSheet()
        try:
            apply_app_theme(self.app)
            toast = Toast()
            toast.show_message(
                "Fächer für die Dokumentation wurden gespeichert.",
                tone="success",
                duration_ms=10_000,
            )
            toast.ensurePolished()
            toast.label.ensurePolished()
            background = toast.palette().color(QPalette.ColorRole.Window)
            foreground = toast.label.palette().color(QPalette.ColorRole.WindowText)

            def luminance(color: QColor) -> float:
                channels = []
                for channel in (color.redF(), color.greenF(), color.blueF()):
                    channels.append(
                        channel / 12.92
                        if channel <= 0.04045
                        else ((channel + 0.055) / 1.055) ** 2.4
                    )
                return (
                    0.2126 * channels[0]
                    + 0.7152 * channels[1]
                    + 0.0722 * channels[2]
                )

            lighter, darker = sorted(
                (luminance(background), luminance(foreground)), reverse=True
            )
            contrast = (lighter + 0.05) / (darker + 0.05)
            self.assertGreaterEqual(contrast, 4.5)
            self.assertEqual(background.name(), "#155e4a")
            self.assertEqual(foreground.name(), "#ffffff")
            self.assertIsNone(toast.graphicsEffect())
            self.assertEqual(toast.windowOpacity(), 1.0)
            self.assertTrue(toast.isEnabled())
            self.assertTrue(toast.label.isEnabled())
            self.assertEqual(
                toast.sizeHint().height(),
                toast.heightForWidth(toast.sizeHint().width()),
            )
        finally:
            self.app.setStyleSheet(previous_stylesheet)

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

    def test_toast_sizes_short_long_and_multiline_text_from_actual_width(self) -> None:
        toast = Toast()

        toast.show_message("Gespeichert.", duration_ms=10_000)
        short_size = toast.sizeHint()
        toast.show_message(
            "Diese lange einzeilige Meldung beschreibt einen vollständig "
            "gespeicherten Arbeitsstand und benötigt bei begrenzter Breite "
            "einen kontrollierten Umbruch.",
            duration_ms=10_000,
        )
        long_size = toast.sizeHint()
        toast.show_message(
            "Erste ausdrücklich gesetzte Zeile.\n"
            "Zweite Zeile mit zusätzlicher Information.",
            duration_ms=10_000,
        )
        multiline_size = toast.sizeHint()

        self.assertEqual(short_size.width(), 280)
        self.assertLess(short_size.height(), long_size.height())
        self.assertGreater(multiline_size.height(), short_size.height())
        self.assertLessEqual(long_size.width(), 520)
        self.assertTrue(toast.hasHeightForWidth())
        toast.clear()

    def test_toast_frame_never_clips_long_product_messages(self) -> None:
        toast = Toast()
        messages = (
            "Entwurf gespeichert – du kannst ihn später fortsetzen.",
            "Fächer für die Dokumentation wurden gespeichert. "
            "Die ausgewählten und weiteren Fächer bleiben für dieses Kind erhalten.",
            "Beobachtung gespeichert.\n"
            "Mehrere Kompetenzbewertungen und Dokumente wurden vollständig übernommen.",
        )

        for tone in ("success", "info", "warning", "error"):
            for width in (300, 340, 380, 520):
                for message in messages:
                    toast.show_message(message, tone=tone, duration_ms=10_000)
                    toast.resize(width, toast.heightForWidth(width))
                    self.app.processEvents()
                    frame_extent = toast.frameWidth() * 2
                    content_width = width - frame_extent - (
                        toast.layout().contentsMargins().left()
                        + toast.layout().contentsMargins().right()
                    )
                    required_label_height = toast.label.heightForWidth(content_width)

                    self.assertGreaterEqual(toast.label.height(), required_label_height)
                    self.assertTrue(toast.contentsRect().contains(toast.label.geometry()))
                    self.assertGreaterEqual(toast.height(), toast.heightForWidth(width))
                    self.assertEqual(toast.text(), message)
                    self.assertEqual(toast.property("toastTone"), tone)

        toast.clear()

    def test_toast_fits_dialog_top_and_shell_bottom_after_parent_resize(self) -> None:
        host = QWidget()
        host.resize(420, 260)
        overlay = Toast(host)
        overlay.show_message(
            "Entwurf gespeichert – du kannst ihn später fortsetzen. "
            "Die Meldung bleibt auch mit einer zweiten Zeile vollständig lesbar.",
            tone="success",
            duration_ms=10_000,
        )
        host.show()
        self.app.processEvents()

        safe_rect = host.contentsRect().adjusted(16, 16, -16, -16)
        self.assertTrue(safe_rect.contains(overlay.geometry()))
        self.assertEqual(overlay.geometry().top(), safe_rect.top())
        self.assertEqual(overlay.height(), overlay.heightForWidth(overlay.width()))
        self.assertIsNone(overlay.graphicsEffect())

        host.resize(340, 300)
        self.app.processEvents()
        resized_safe_rect = host.contentsRect().adjusted(16, 16, -16, -16)
        self.assertTrue(resized_safe_rect.contains(overlay.geometry()))
        self.assertEqual(overlay.height(), overlay.heightForWidth(overlay.width()))

        layout_host = QWidget()
        layout = QVBoxLayout(layout_host)
        layout.addStretch(1)
        managed = Toast()
        layout.addWidget(
            managed,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        managed.show_message(
            "Fächer für die Dokumentation wurden gespeichert. "
            "Die gewählte Fachmenge ist nun aktiv.",
            tone="success",
            duration_ms=10_000,
        )
        layout_host.resize(620, 260)
        layout_host.show()
        self.app.processEvents()
        self.assertFalse(managed._is_parent_overlay())
        self.assertGreaterEqual(
            managed.height(), managed.heightForWidth(managed.width())
        )
        self.assertEqual(
            managed.geometry().bottom(),
            layout_host.contentsRect().bottom() - layout.contentsMargins().bottom(),
        )

        layout_host.resize(380, 300)
        self.app.processEvents()
        self.assertLessEqual(managed.geometry().right(), layout_host.contentsRect().right())
        self.assertGreaterEqual(
            managed.height(), managed.heightForWidth(managed.width())
        )
        host.close()
        layout_host.close()

    def test_shared_headers_and_status_badges_keep_normal_text_readable(self) -> None:
        host = QWidget()
        layout = QVBoxLayout(host)
        header = SectionHeader("Berichte & LEG (Übersicht)")
        badge = StatusBadge("Bestätigungsstand unklar", tone="warning")
        layout.addWidget(header)
        layout.addWidget(badge)
        host.resize(190, 140)
        host.show()
        self.app.processEvents()

        self.assertTrue(header.title_label.wordWrap())
        self.assertGreaterEqual(
            header.title_label.height(),
            2 * header.title_label.fontMetrics().height(),
        )
        self.assertEqual(
            badge.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Minimum,
        )
        self.assertGreaterEqual(
            badge.sizeHint().width(),
            badge.fontMetrics().horizontalAdvance(badge.text()),
        )
        self.assertGreaterEqual(
            badge.minimumWidth(),
            badge.fontMetrics().horizontalAdvance(badge.text()) + 18,
        )
        badge.setText("Bestätigungsstand weiterhin unklar")
        self.assertGreaterEqual(
            badge.minimumWidth(),
            badge.fontMetrics().horizontalAdvance(badge.text()) + 18,
        )
        host.close()

    def test_pointer_cursor_tracks_enter_leave_hide_and_repeated_clicks(self) -> None:
        button = QPushButton("Disclosure")
        install_pointer_cursor(button)
        button.show()
        self.app.processEvents()

        QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
        self.assertEqual(button.cursor().shape(), Qt.CursorShape.PointingHandCursor)

        QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        self.assertEqual(button.cursor().shape(), Qt.CursorShape.ArrowCursor)

        QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
        button.hide()
        self.assertEqual(button.cursor().shape(), Qt.CursorShape.ArrowCursor)

        button.show()
        for _ in range(5):
            QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        self.app.processEvents()
        QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        self.assertEqual(button.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertIsNone(QApplication.overrideCursor())

    def test_stop_and_widget_deletion_leave_no_running_transition(self) -> None:
        widget = QWidget()
        animate_opacity(widget, visible=True, duration_ms=240)
        stop_motion(widget)
        self.assertEqual(widget._motion_animations, {})

        widget.deleteLater()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
