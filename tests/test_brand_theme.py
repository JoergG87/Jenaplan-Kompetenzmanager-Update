"""Stable checks for brand colors and non-semantic dialog contexts."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QPushButton

from src.desktop_app import theme
from src.desktop_app.components import CourseBadge, DialogHeader, StatusBadge, configure_button
from src.desktop_app.view_models.observation_view_model import (
    OBSERVATION_RATING_TOKENS,
    rating_chip_options_for_competency,
)


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    light, dark = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (light + 0.05) / (dark + 0.05)


class BrandThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.previous_stylesheet = cls.app.styleSheet()
        theme.apply_app_theme(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.setStyleSheet(cls.previous_stylesheet)

    def test_brand_palette_has_named_roles_and_accessible_action_contrast(self) -> None:
        self.assertGreaterEqual(_contrast(theme.BRAND_NAVY, "#FFFFFF"), 7.0)
        self.assertGreaterEqual(_contrast(theme.BRAND_BLUE, "#FFFFFF"), 4.5)
        self.assertGreaterEqual(_contrast(theme.BRAND_TEAL, "#FFFFFF"), 4.5)
        self.assertGreaterEqual(_contrast(theme.BRAND_GREEN, "#FFFFFF"), 4.5)
        self.assertGreaterEqual(_contrast(theme.BRAND_ORANGE, "#FFFFFF"), 4.5)
        self.assertEqual(theme.COLOR_FOCUS, theme.BRAND_TEAL)
        self.assertEqual(theme.COLOR_BLUE, theme.BRAND_BLUE)
        self.assertEqual(theme.COLOR_TURQUOISE, theme.BRAND_TEAL)

    def test_subject_accent_matrix_uses_only_approved_design_tokens(self) -> None:
        self.assertEqual(
            {
                subject_id: theme.subject_accent_color(subject_id)
                for subject_id in (
                    "deutsch",
                    "mathematik",
                    "englisch",
                    "musik",
                    "ethik",
                    "religion",
                    "schulgarten",
                )
            },
            {
                "deutsch": theme.SUBJECT_ACCENT_RED,
                "mathematik": theme.SUBJECT_ACCENT_BLUE,
                "englisch": theme.SUBJECT_ACCENT_BLACK,
                "musik": theme.SUBJECT_ACCENT_YELLOW,
                "ethik": theme.SUBJECT_ACCENT_ORANGE,
                "religion": theme.SUBJECT_ACCENT_ORANGE,
                "schulgarten": theme.SUBJECT_ACCENT_BROWN,
            },
        )
        for subject_id in (
            "epu",
            "sachkunde",
            "kreatives_gestalten",
            "selbst_sozialkompetenz",
            "arbeits_lernkompetenz",
            "unknown_historical_subject",
        ):
            self.assertEqual(
                theme.subject_accent_color(subject_id),
                theme.SUBJECT_ACCENT_NEUTRAL,
            )
        self.assertNotIn("werken", theme.SUBJECT_ACCENT_COLORS)
        self.assertNotIn("projektplan", theme.SUBJECT_ACCENT_COLORS)

    def test_subject_accents_do_not_change_course_or_rating_contracts(self) -> None:
        course = CourseBadge("Kurs 2", "#2563EB")
        before_course_color = course.property("courseColorHex")
        before_ratings = rating_chip_options_for_competency(
            SimpleNamespace(subject_id="deutsch")
        )

        marker = theme.subject_accent_icon("deutsch").pixmap(12, 12)

        self.assertFalse(marker.isNull())
        self.assertEqual(course.property("courseColorHex"), before_course_color)
        self.assertEqual(
            tuple(token for token, _label in before_ratings),
            OBSERVATION_RATING_TOKENS,
        )

    def test_dialog_header_context_roles_are_explicit_and_keep_text_identity(self) -> None:
        for context_role in (
            "neutral",
            "observation",
            "report",
            "learning_conference",
        ):
            header = DialogHeader(
                "Arbeitsbereich",
                "Amelie Vogel",
                "Der Titel bleibt der primäre Kontext.",
                context_role=context_role,
            )
            self.assertEqual(header.property("dialogContext"), context_role)
            self.assertEqual(header.accessibleName(), "Arbeitsbereich")
            self.assertEqual(header.context_label.text(), "Amelie Vogel")
        with self.assertRaises(ValueError):
            DialogHeader("Unbekannt", context_role="success")

    def test_theme_centrally_styles_shell_buttons_and_dialog_contexts(self) -> None:
        stylesheet = theme.APP_STYLESHEET
        for context_role in (
            "neutral",
            "observation",
            "report",
            "learning_conference",
        ):
            self.assertIn(f'QFrame[dialogContext="{context_role}"]', stylesheet)
        self.assertIn('QDialog[dialogContext="observation"]', stylesheet)
        self.assertIn('QPushButton[phaseCurrent="true"]', stylesheet)
        self.assertIn(f"background-color: {theme.LIGHT_BLUE};", stylesheet)
        self.assertIn(f"border-left: 4px solid {theme.BRAND_BLUE};", stylesheet)
        self.assertNotIn(
            'QDialog[dialogContext="report"] '
            'QPushButton#SegmentedControlButton:checked',
            stylesheet,
        )
        self.assertIn(
            'QPushButton#SegmentedControlButton:checked:disabled',
            stylesheet,
        )
        self.assertIn(f"background-color: {theme.BRAND_BLUE};", stylesheet)
        self.assertIn(f"border: 2px solid {theme.COLOR_FOCUS};", stylesheet)

        primary = QPushButton("Speichern")
        configure_button(primary, "primary", "Entwurf speichern")
        self.assertEqual(primary.property("buttonRole"), "primary")
        self.assertEqual(primary.accessibleName(), "Entwurf speichern")

    def test_course_rating_documentation_and_feedback_systems_stay_separate(self) -> None:
        course = CourseBadge("Kurs 1", "#2563EB")
        self.assertEqual(course.property("courseColorHex"), "#2563EB")
        self.assertIn("Kurs 1", course.accessibleName())

        expected_rating_surfaces = {
            "--": "#F9ECEE",
            "-": "#FBF4DC",
            "+": "#EAF5EE",
            "++": "#DCEDE4",
        }
        for token, surface in expected_rating_surfaces.items():
            badge = StatusBadge(token, rating_token=token)
            self.assertEqual(badge.property("ratingToken"), token)
            self.assertIn(surface, theme.APP_STYLESHEET)

        for level, surface in enumerate(
            ("#F8FAFC", "#EEF6FC", "#E3F0F9", "#D5E9F6", "#C8E2F2")
        ):
            self.assertIn(
                f'coverageLevel="{level}"] {{ background-color: {surface};',
                theme.APP_STYLESHEET,
            )
        self.assertNotEqual(theme.COLOR_SUCCESS, theme.BRAND_GREEN)
        self.assertNotEqual(theme.COLOR_WARNING, theme.BRAND_ORANGE)


if __name__ == "__main__":
    unittest.main()
