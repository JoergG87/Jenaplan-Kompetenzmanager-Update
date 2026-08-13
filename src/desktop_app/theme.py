"""Central visual theme for the PySide desktop app."""

from __future__ import annotations

from types import MappingProxyType

from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QLabel

from src.desktop_app.icons import icon_path


BRAND_NAVY = "#123F67"
BRAND_BLUE = "#176BC1"
BRAND_BLUE_HOVER = "#115AA7"
BRAND_BLUE_PRESSED = "#0D4A8E"
BRAND_TEAL = "#087F83"
BRAND_GREEN = "#3B7F34"
BRAND_LIME = "#8DCB22"
BRAND_ORANGE = "#B2530A"

LIGHT_BLUE = "#EAF4FE"
LIGHT_TEAL = "#E8F7F5"
LIGHT_GREEN = "#EDF7EA"
LIGHT_LIME = "#F4F9E8"
LIGHT_ORANGE = "#FFF2E5"
LIGHT_NEUTRAL = "#F6F9FB"

# Backwards-compatible semantic aliases used by existing UI projections.
COLOR_NAVY = BRAND_NAVY
COLOR_BLUE = BRAND_BLUE
COLOR_BLUE_DARK = BRAND_BLUE_HOVER
COLOR_BLUE_PRESSED = BRAND_BLUE_PRESSED
COLOR_BLUE_SOFT = LIGHT_BLUE
COLOR_TURQUOISE = BRAND_TEAL
COLOR_GREEN = BRAND_GREEN
COLOR_ORANGE = BRAND_ORANGE
COLOR_BACKGROUND = "#F0F5F8"
COLOR_SURFACE = "#FFFFFF"
COLOR_SURFACE_SOFT = "#F7FAFC"
COLOR_GLASS = "rgba(255, 255, 255, 246)"
COLOR_GLASS_SOFT = "rgba(248, 251, 253, 242)"
COLOR_BORDER = "#CBD8E2"
COLOR_TEXT = "#1F2937"
COLOR_TEXT_MUTED = "#556372"
COLOR_TEXT_SUBTLE = "#6B7280"
COLOR_ERROR = "#B00020"
COLOR_SUCCESS = "#24705A"
COLOR_WARNING = "#8A6418"
COLOR_INFO = "#315F83"
COLOR_FOCUS = BRAND_TEAL

# Read-only UI orientation. Subject accents are deliberately separate from
# persisted course colors and from the four competency-rating colors.
SUBJECT_ACCENT_RED = "#B3261E"
SUBJECT_ACCENT_BLUE = BRAND_BLUE
SUBJECT_ACCENT_BLACK = COLOR_TEXT
SUBJECT_ACCENT_YELLOW = "#D4A500"
SUBJECT_ACCENT_ORANGE = BRAND_ORANGE
SUBJECT_ACCENT_BROWN = "#795548"
SUBJECT_ACCENT_WHITE = "#FFFFFF"
SUBJECT_ACCENT_NEUTRAL = "#82909D"
SUBJECT_ACCENT_BORDER = "#52616D"
SUBJECT_ACCENT_YELLOW_BORDER = "#6B5700"
SUBJECT_ACCENT_COLORS = MappingProxyType({
    "deutsch": SUBJECT_ACCENT_RED,
    "mathematik": SUBJECT_ACCENT_BLUE,
    "englisch": SUBJECT_ACCENT_BLACK,
    "musik": SUBJECT_ACCENT_YELLOW,
    "ethik": SUBJECT_ACCENT_ORANGE,
    "religion": SUBJECT_ACCENT_ORANGE,
    "schulgarten": SUBJECT_ACCENT_BROWN,
})


def subject_accent_color(subject_id: str) -> str:
    """Return one approved subject accent or the neutral UI fallback."""
    return SUBJECT_ACCENT_COLORS.get(subject_id.strip(), SUBJECT_ACCENT_NEUTRAL)


def subject_accent_icon(subject_id: str, size: int = 12) -> QIcon:
    """Create a small decorative subject marker without changing semantics."""
    edge = max(8, size)
    fill = QColor(subject_accent_color(subject_id))
    border = QColor(
        SUBJECT_ACCENT_YELLOW_BORDER
        if fill.name().upper() == SUBJECT_ACCENT_YELLOW
        else SUBJECT_ACCENT_BORDER
    )
    image = QImage(edge, edge, QImage.Format.Format_ARGB32)
    image.fill(border)
    for x in range(1, edge - 1):
        for y in range(1, edge - 1):
            image.setPixelColor(x, y, fill)
    return QIcon(QPixmap.fromImage(image))

# UI Sprint 1 tokens. Qt keeps the native platform font; no family is forced.
SPACING_4 = 4
SPACING_8 = 8
SPACING_12 = 12
SPACING_16 = 16
SPACING_24 = 24
SPACING_32 = 32
SPACING_48 = 48

RADIUS_SMALL = 6
RADIUS_MEDIUM = 8
RADIUS_LARGE = 12
RADIUS_XLARGE = 16

ELEVATION_FLAT = 0
ELEVATION_CARD = 1
ELEVATION_OVERLAY = 2

MOTION_FAST_MS = 120
MOTION_STANDARD_MS = 180
MOTION_SLOW_MS = 240
MOTION_HOVER_MS = 100
MOTION_PRESSED_MS = 80
MOTION_SELECTION_MS = 160
MOTION_DIALOG_MS = 200
MOTION_TOAST_MS = 220

TYPOGRAPHY_STYLES = {
    "app_title": f"font-size: 24px; font-weight: 650; color: {COLOR_NAVY};",
    "screen_title": f"font-size: 22px; font-weight: 650; color: {COLOR_NAVY};",
    "dialog_title": f"font-size: 20px; font-weight: 650; color: {COLOR_NAVY};",
    "section_title": f"font-size: 16px; font-weight: 650; color: {COLOR_NAVY};",
    "card_title": f"font-weight: 650; color: {COLOR_NAVY};",
    "muted": f"color: {COLOR_TEXT_MUTED};",
    "subtle": f"color: {COLOR_TEXT_SUBTLE};",
    "body": f"color: {COLOR_TEXT};",
    "error": f"color: {COLOR_ERROR};",
    "small": f"color: {COLOR_TEXT_SUBTLE}; font-size: 11px; font-weight: 500;",
    "field_label": f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: 600;",
}

APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT};
}}
QWidget#AppRoot {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #ECF4F8,
        stop: 0.56 #F6F9FB,
        stop: 1 #EAF5F4
    );
}}
QWidget#AppSidebar {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 rgba(18, 63, 103, 252),
        stop: 0.56 rgba(15, 72, 111, 250),
        stop: 1 rgba(9, 78, 96, 252)
    );
    border-right: 1px solid #3E7F99;
    border-top-right-radius: 16px;
    border-bottom-right-radius: 16px;
}}
QWidget {{
    color: {COLOR_TEXT};
    font-size: 13px;
}}
QLabel#AppIconLabel {{
    background-color: transparent;
}}
QLabel#SidebarBrandTitle {{
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
}}
QLabel#SidebarBrandSubtitle {{
    color: #CFE2F0;
    font-size: 12px;
}}
QWidget#AppSidebar QPushButton[buttonRole="quiet"] {{
    color: #EAF2F8;
    background-color: transparent;
    border-color: transparent;
}}
QWidget#AppSidebar QPushButton[buttonRole="quiet"]:hover {{
    color: #FFFFFF;
    background-color: rgba(48, 151, 165, 72);
}}
QListWidget#AppNavigation {{
    background-color: transparent;
    color: #EAF2F8;
    border: none;
    padding: 10px 0;
    outline: none;
}}
QListWidget#AppNavigation::item {{
    border: none;
    border-left: 3px solid transparent;
    border-radius: 7px;
    padding: 10px 10px 10px 9px;
    margin: 2px 0;
}}
QListWidget#AppNavigation::item:selected {{
    background-color: rgba(226, 247, 246, 42);
    border-left: 3px solid #62D1D0;
    color: #FFFFFF;
}}
QListWidget#AppNavigation::item:hover {{
    background-color: rgba(130, 205, 211, 30);
    color: #FFFFFF;
}}
QListWidget#AppNavigation::item:focus {{
    border: 1px solid #85D8D6;
    border-left: 3px solid #85D8D6;
}}
QListWidget#AppNavigation::item:disabled {{
    color: #9FB6C8;
    background-color: transparent;
    padding-top: 18px;
    padding-bottom: 4px;
    font-size: 10px;
    font-weight: 700;
}}
QFrame#AppCard, QFrame[cardVariant="default"], QFrame[cardVariant="soft"],
QFrame[cardVariant="accent"], QFrame[cardVariant="interactive"] {{
    background-color: {COLOR_SURFACE};
    border: 1px solid #D5E0E8;
    border-bottom: 2px solid #C9D7E1;
    border-radius: 13px;
}}
QFrame[cardVariant="soft"] {{
    background-color: {COLOR_SURFACE_SOFT};
    border-color: #DEE7ED;
    border-bottom-width: 1px;
}}
QFrame#ProfileObservationCard[interactive="true"]:hover {{
    background-color: #F3F8FB;
    border-color: #B9CDD9;
}}
QFrame[cardVariant="accent"] {{
    background-color: {LIGHT_BLUE};
    border-color: #B8D5EC;
    border-bottom: 2px solid #9BC3E2;
}}
QFrame#AppCard[dialogContextSurface="learning_conference"] {{
    background-color: {LIGHT_GREEN};
    border-color: #B8D7B1;
    border-bottom: 2px solid #95C28C;
}}
QFrame#AppCard[cardVariant="interactive"]:hover,
QFrame[cardVariant="interactive"]:hover {{
    background-color: #F8FBFF;
    border-color: #8EB6E5;
}}
QFrame#AppCard[cardVariant="interactive"]:focus,
QFrame[cardVariant="interactive"]:focus {{
    border: 2px solid {COLOR_FOCUS};
}}
QFrame#AppCard[cardVariant="interactive"][pressed="true"],
QFrame[cardVariant="interactive"][pressed="true"] {{
    background-color: #E7F0FA;
    border-color: #6C9FD3;
}}
QFrame#AppCard[cardVariant="interactive"]:disabled,
QFrame[cardVariant="interactive"]:disabled {{
    background-color: #F3F6F8;
    border-color: #E2E8ED;
}}
QFrame#AppCard[selected="true"], QFrame[cardVariant][selected="true"] {{
    background-color: #EEF5FF;
    border: 2px solid {COLOR_BLUE};
}}
QFrame#AppCard[cardVariant][selected="true"]:focus,
QFrame[cardVariant][selected="true"]:focus {{
    background-color: #EEF5FF;
    border: 2px solid {COLOR_FOCUS};
    border-left-color: {COLOR_BLUE};
}}
QFrame#AppCard[cardVariant][selected="true"]:disabled,
QFrame[cardVariant][selected="true"]:disabled {{
    background-color: #F3F6F8;
    border: 2px solid #E2E8ED;
}}
QFrame#AppPanel {{
    background-color: {COLOR_GLASS_SOFT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#DashboardHero {{
    background-color: {LIGHT_BLUE};
    border: 1px solid #A8CDEA;
    border-radius: 18px;
}}
QFrame#DashboardTimeline, QFrame#DashboardHeatmap,
QFrame#DashboardMatchingChildren {{
    background-color: {COLOR_SURFACE};
    border: 1px solid #D8E4EC;
    border-bottom: 2px solid #CBD9E3;
    border-radius: 15px;
}}
QLabel#DashboardHeroTitle {{
    color: {COLOR_NAVY};
    font-size: 20px;
    font-weight: 700;
}}
QLabel#DashboardHeroStatus {{
    color: {COLOR_BLUE_DARK};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#DashboardHeroSubject {{
    color: {COLOR_NAVY};
    font-size: 21px;
    font-weight: 700;
}}
QLabel#DashboardHeroTime {{
    color: {COLOR_NAVY};
    font-size: 22px;
    font-weight: 700;
}}
QFrame#DashboardHeroIllustrationSpace {{
    background-color: rgba(255, 255, 255, 185);
    border: 1px solid #D8E5F5;
    border-radius: 14px;
}}
QLabel#DashboardHeroVisualTime {{
    color: #70839A;
    font-size: 10px;
}}
QFrame#DashboardHeroVisualBlock {{
    background-color: #E7EEF8;
    border: none;
    border-radius: 4px;
    min-height: 17px;
}}
QFrame#DashboardHeroVisualCurrent {{
    background-color: #77A6E8;
    border: 1px solid #3B75C5;
    border-radius: 4px;
    min-height: 24px;
}}
QFrame#DashboardHeroSubjectVignette {{
    background: transparent;
    border: none;
}}
QFrame#DashboardHeroSubjectImage {{
    background: transparent;
    border: none;
}}
QFrame#DashboardLessonCard {{
    background-color: #FFFFFF;
    border: 1px solid #D7E3EC;
    border-radius: 13px;
}}
QFrame#DashboardLessonCard:hover {{
    border-color: {COLOR_BLUE};
}}
QFrame#DashboardLessonCard[lessonState="current"] {{
    background-color: #EEF6FF;
    border: 1px solid {COLOR_BLUE};
}}
QFrame#DashboardLessonCard[lessonState="past"] {{
    background-color: #F8FAFC;
    border-color: #E2E8F0;
}}
QFrame#DashboardLessonCard[lessonState="past"] QLabel {{
    color: #7B8794;
}}
QLabel#DashboardLessonState {{
    color: #FFFFFF;
    background-color: {COLOR_BLUE};
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
}}
QFrame#DashboardMatchingChildrenRow, QFrame#DashboardMatchingChildRow {{
    background-color: #FBFCFE;
    border: 1px solid #DFE7EF;
    border-radius: 10px;
}}
QFrame#DashboardHeatmapCell {{
    border: 1px solid #D7E3EC;
    border-radius: 9px;
}}
QFrame#DashboardHeatmapCell[coverageLevel="0"] {{ background-color: #F8FAFC; }}
QFrame#DashboardHeatmapCell[coverageLevel="1"] {{ background-color: #EEF6FC; }}
QFrame#DashboardHeatmapCell[coverageLevel="2"] {{ background-color: #E3F0F9; }}
QFrame#DashboardHeatmapCell[coverageLevel="3"] {{ background-color: #D5E9F6; }}
QFrame#DashboardHeatmapCell[coverageLevel="4"] {{ background-color: #C8E2F2; }}
QFrame#DashboardHeatmapMarker {{
    border: none;
    border-radius: 5px;
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
}}
QFrame#CourseColorMarker {{
    border: none;
    border-radius: 5px;
}}
QWidget#SectionHeader {{ background-color: transparent; }}
QLabel#SectionHeaderTitle {{ font-size: 16px; font-weight: 650; }}
QFrame#DialogHeader {{
    background-color: {COLOR_GLASS};
    border: none;
    border-bottom: 1px solid #D7E2EA;
}}
QLabel#DialogHeaderIcon {{
    background-color: {LIGHT_BLUE};
    border: 1px solid #BCD9EC;
    border-radius: 11px;
}}
QLabel#DialogHeaderTitle {{
    color: {COLOR_NAVY};
    font-size: 20px;
    font-weight: 650;
}}
QLabel#DialogHeaderContext {{
    color: #365966;
    font-size: 12px;
    font-weight: 650;
}}
QFrame#DialogHeader[dialogContext="neutral"],
QFrame[dialogContext="neutral"] {{
    border-bottom: 2px solid #B8D5EC;
}}
QFrame#DialogHeader[dialogContext="observation"],
QFrame[dialogContext="observation"] {{
    background-color: {LIGHT_TEAL};
    border-bottom: 2px solid {BRAND_TEAL};
}}
QFrame[dialogContext="observation"] QLabel#DialogHeaderIcon {{
    background-color: #D9F1EE;
    border-color: #9BCFCB;
}}
QFrame#DialogHeader[dialogContext="report"],
QFrame[dialogContext="report"] {{
    background-color: {LIGHT_ORANGE};
    border-bottom: 2px solid {BRAND_ORANGE};
}}
QFrame[dialogContext="report"] QLabel#DialogHeaderIcon {{
    background-color: #FFE5CB;
    border-color: #EDBD8C;
}}
QFrame#DialogHeader[dialogContext="learning_conference"],
QFrame[dialogContext="learning_conference"] {{
    background-color: {LIGHT_GREEN};
    border-bottom: 2px solid {BRAND_GREEN};
}}
QFrame[dialogContext="learning_conference"] QLabel#DialogHeaderIcon {{
    background-color: #DDF0D8;
    border-color: #ACD0A5;
}}
QDialogButtonBox#DialogActionBar,
QDialogButtonBox#ObservationPersistentActions {{
    background-color: transparent;
    border: none;
    border-top: 1px solid #D7E2EA;
    padding-top: 12px;
}}
QFrame#FilterBar {{
    background-color: rgba(255, 255, 255, 232);
    border: 1px solid #D7E2EA;
    border-bottom: 2px solid #C8D8E3;
    border-radius: 11px;
}}
QPushButton#FilterChip {{
    background-color: #E6F0FB;
    color: {COLOR_NAVY};
    border: 1px solid #BDD3E8;
    border-radius: 13px;
    padding: 5px 11px;
    font-weight: 600;
}}
QPushButton#FilterChip:hover {{ background-color: #D8E9F8; border-color: #8EB6D8; }}
QPushButton#FilterChip:focus {{ border: 2px solid {COLOR_FOCUS}; padding: 4px 10px; }}
QPushButton#IconButton {{
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    border: 1px solid {BRAND_BLUE_HOVER};
    border-radius: 9px;
    background-color: {BRAND_BLUE};
}}
QPushButton#IconButton:hover {{
    background-color: {BRAND_BLUE_HOVER};
    border-color: {BRAND_BLUE_HOVER};
}}
QPushButton#IconButton:pressed {{
    background-color: {COLOR_NAVY};
    border-color: {COLOR_NAVY};
}}
QPushButton#IconButton:focus {{
    border: 2px solid {COLOR_FOCUS};
}}
QLineEdit#SearchField {{
    min-height: 22px;
    background-color: {COLOR_GLASS};
    border: 1px solid #C5D3DE;
    border-bottom: 2px solid #B8CAD7;
    border-radius: 10px;
    padding: 7px 11px;
}}
QLineEdit#SearchField:hover {{ border-color: #9CB8CE; }}
QLineEdit#SearchField:focus {{ border: 2px solid {COLOR_FOCUS}; padding: 6px 10px; }}
QLabel#StatusBadge, QLabel#LearningConferenceDirtyBadge {{
    background-color: #EDF2F6;
    color: {COLOR_TEXT_MUTED};
    border: 1px solid #D8E2EA;
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#StatusBadge[badgeTone="info"], QLabel#LearningConferenceDirtyBadge[badgeTone="info"] {{ background-color: #E8F2FB; color: {COLOR_INFO}; border-color: #C7DCEB; }}
QLabel#StatusBadge[badgeTone="success"], QLabel#LearningConferenceDirtyBadge[badgeTone="success"] {{ background-color: #EAF6F0; color: {COLOR_SUCCESS}; border-color: #C7E3D6; }}
QLabel#StatusBadge[badgeTone="warning"], QLabel#LearningConferenceDirtyBadge[badgeTone="warning"] {{ background-color: #FFF6E8; color: #76501E; border-color: #ECD8A6; }}
QLabel#StatusBadge[ratingBadge="true"],
QPushButton#RatingBadgeButton[ratingBadge="true"] {{
    border: 1px solid #D5E0E4;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 700;
}}
QLabel#StatusBadge[ratingToken="--"],
QPushButton#RatingBadgeButton[ratingToken="--"] {{
    color: #754B52;
    background-color: #F9ECEE;
    border-color: #E8CDD2;
}}
QLabel#StatusBadge[ratingToken="-"],
QPushButton#RatingBadgeButton[ratingToken="-"] {{
    color: #6F5B2D;
    background-color: #FBF4DC;
    border-color: #E8DCA9;
}}
QLabel#StatusBadge[ratingToken="+"],
QPushButton#RatingBadgeButton[ratingToken="+"] {{
    color: #3F6752;
    background-color: #EAF5EE;
    border-color: #CBE1D3;
}}
QLabel#StatusBadge[ratingToken="++"],
QPushButton#RatingBadgeButton[ratingToken="++"] {{
    color: #315B47;
    background-color: #DCEDE4;
    border-color: #B8D5C5;
}}
QPushButton#RatingBadgeButton:hover {{
    color: {COLOR_NAVY};
    border: 2px solid #7897B0;
    padding: 2px 7px;
}}
QPushButton#RatingBadgeButton:pressed {{
    color: {COLOR_NAVY};
    border: 2px solid #38546B;
    padding: 2px 7px;
}}
QPushButton#RatingBadgeButton:checked {{
    color: {COLOR_NAVY};
    border: 2px solid {COLOR_NAVY};
    padding: 2px 7px;
    font-weight: 750;
}}
QPushButton#RatingBadgeButton:focus {{
    color: {COLOR_NAVY};
    border: 2px solid {COLOR_FOCUS};
    padding: 2px 7px;
}}
QPushButton#RatingBadgeButton:checked:pressed {{
    background-color: #E1ECF5;
    border-color: #38546B;
}}
QPushButton#RatingBadgeButton:disabled {{
    color: #718096;
    background-color: #EDF2F6;
    border-color: #D8E2EA;
}}
QFrame#DashboardHeatmapCell[coverageLevel="0"] QFrame#DashboardHeatmapMarker {{ background-color: #CBD5E1; }}
QFrame#DashboardHeatmapCell[coverageLevel="1"] QFrame#DashboardHeatmapMarker {{ background-color: #B7C9DC; }}
QFrame#DashboardHeatmapCell[coverageLevel="2"] QFrame#DashboardHeatmapMarker {{ background-color: #91ADC8; }}
QFrame#DashboardHeatmapCell[coverageLevel="3"] QFrame#DashboardHeatmapMarker {{ background-color: #6F91B2; }}
QFrame#DashboardHeatmapCell[coverageLevel="4"] QFrame#DashboardHeatmapMarker {{ background-color: #4F7599; }}
QFrame#LearningReportTopBar {{
    background-color: {LIGHT_ORANGE};
    border: none;
    border-bottom: 1px solid #E8C9A8;
    border-radius: 0px;
}}
QFrame#LearningReportTopBar QWidget#PageHeader {{
    background-color: transparent;
}}
QLabel#LearningReportBrand {{
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 700;
}}
QLabel#LearningReportTopHint {{
    color: #D8E9F0;
    font-size: 12px;
}}
QPushButton#LearningReportModeButton {{
    background-color: transparent;
    color: #DCEAF0;
    border: none;
    border-radius: 9px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton#LearningReportModeButton:hover {{
    background-color: #244661;
}}
QPushButton#LearningReportModeButton:checked {{
    background-color: #FFFFFF;
    color: {COLOR_NAVY};
}}
QFrame#LearningReportSidebar {{
    background-color: {COLOR_GLASS_SOFT};
    border-right: 1px solid #D8E2E7;
}}
QFrame#LearningReportWorkspaceNavigation {{
    background-color: #FFFAF5;
    border: none;
    border-bottom: 1px solid #D8E2E7;
}}
QFrame#LearningReportActionBar {{
    background-color: #FFFFFF;
    border: none;
    border-top: 1px solid #D8E2E7;
}}
QPushButton#LearningReportSubjectButton {{
    text-align: left;
    background-color: transparent;
    border: none;
    padding: 10px 12px;
    color: #49606F;
}}
QPushButton#LearningReportSubjectButton:checked {{
    background-color: {LIGHT_ORANGE};
    color: {COLOR_NAVY};
    border-left: 3px solid {BRAND_ORANGE};
}}
QLabel#LearningReportEyebrow {{
    color: {BRAND_ORANGE};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#LearningReportStatusPill {{
    color: #73521C;
    background-color: #FFF4DB;
    border: 1px solid #ECD8A6;
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 600;
}}
QFrame#LearningReportInternalCard {{
    background-color: #F4F7F8;
    border: 1px dashed #B7C7CF;
    border-radius: 12px;
}}
QLabel#LearningReportInternalBadge {{
    color: #76501E;
    background-color: #FFF6E8;
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 700;
}}
QFrame#LearningReportReportCard {{
    background-color: #FFFFFF;
    border: 1px solid #CFE0E6;
    border-radius: 12px;
}}
QFrame#LearningConferenceTopBar {{
    background-color: {COLOR_NAVY};
    border: none;
}}
QLabel#LearningConferenceEyebrow {{
    color: #A9D7D5;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#LearningConferenceTopTitle {{
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
}}
QLabel#LearningConferenceTopMeta {{
    color: #DCEAEC;
    font-size: 12px;
}}
QFrame#LearningConferencePreparationPanel {{
    background-color: #F4F8F8;
    border: none;
}}
QFrame#LearningConferenceConversationPanel {{
    background-color: #F8FAF9;
    border: none;
}}
QFrame#LearningConferenceWorkspace {{
    background-color: transparent;
    border: none;
}}
QFrame#LearningConferencePhaseNavigation {{
    background-color: {COLOR_GLASS_SOFT};
    border: 1px solid #D8E4EC;
    border-radius: 14px;
}}
QFrame#LearningConferencePhaseNavigation QPushButton[phaseCurrent="false"] {{
    min-height: 44px;
    background-color: transparent;
    color: {COLOR_TEXT};
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 7px 9px;
    text-align: left;
    font-size: 11px;
}}
QFrame#LearningConferencePhaseNavigation QPushButton[phaseCurrent="false"]:hover {{
    background-color: #EDF3F7;
    border-color: #D4E1E9;
}}
QFrame#LearningConferencePhaseNavigation QPushButton[phaseCurrent="true"] {{
    min-height: 44px;
    background-color: {LIGHT_BLUE};
    color: {COLOR_NAVY};
    border: 1px solid #9FB9CE;
    border-left: 4px solid {BRAND_BLUE};
    border-radius: 9px;
    padding: 7px 9px 7px 7px;
    text-align: left;
    font-weight: 700;
    font-size: 11px;
}}
QFrame#LearningConferencePhaseNavigation QPushButton[phaseCurrent="false"]:focus,
QFrame#LearningConferencePhaseNavigation QPushButton[phaseCurrent="true"]:focus {{
    border: 2px solid {COLOR_FOCUS};
}}
QFrame#LearningConferenceActionBar {{
    background-color: #FFFFFF;
    border: 1px solid #D8E4EC;
    border-radius: 12px;
}}
QScrollArea#LearningConferencePhaseScroll {{
    background-color: #F8FAFB;
    border: 1px solid #DCE6ED;
    border-radius: 14px;
}}
QFrame#LearningConferenceCard {{
    background-color: #FFFFFF;
    border: 1px solid #DCE6E9;
    border-radius: 15px;
}}
QFrame#LearningConferenceSoftBlock {{
    background-color: #F7FAFA;
    border: none;
    border-radius: 10px;
}}
QFrame#LearningConferenceChartCard {{
    background-color: #F7FAF9;
    border: 1px solid #E3EBEA;
    border-radius: 12px;
}}
QFrame#LearningConferenceHero {{
    background-color: {COLOR_NAVY};
    border: none;
    border-radius: 18px;
}}
QFrame#LearningConferenceSection {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid #E1E8E8;
}}
QFrame#LearningConferencePrepared {{
    background-color: #F2F7F6;
    border: none;
    border-radius: 11px;
}}
QFrame#LearningConferenceShared {{
    background-color: #FFFFFF;
    border: 1px dashed #BFCFD0;
    border-radius: 11px;
}}
QFrame#LearningConferenceWarning {{
    background-color: #FFF5E8;
    border: none;
    border-radius: 9px;
}}
QLabel#LearningConferenceWarningText {{ color: #865424; }}
QLabel#LearningConferenceSectionNumber {{
    color: {COLOR_TURQUOISE};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#LearningConferenceHeroTitle {{
    color: #FFFFFF;
    font-size: 25px;
    font-weight: 700;
}}
QLabel#LearningConferenceHeroMeta {{ color: #DCEAEC; }}
QToolButton#LearningConferenceHierarchyButton {{
    color: {COLOR_NAVY};
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 7px 5px;
    font-weight: 600;
}}
QToolButton#LearningConferenceHierarchyButton:hover {{
    background-color: #EFF5F4;
    border-radius: 7px;
}}
QPushButton#LearningConferenceSaveButton {{
    background-color: {COLOR_BLUE};
    color: #FFFFFF;
    border: 1px solid {COLOR_BLUE_DARK};
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 700;
}}
QPushButton#LearningConferenceSaveButton:hover {{ background-color: {COLOR_BLUE_DARK}; }}
QPushButton#LearningConferenceSaveButton:pressed {{ background-color: {COLOR_BLUE_PRESSED}; }}
QFrame#LearningReportResponsibilityNote {{
    background-color: #EDF6FA;
    border: 1px solid #CFE2EA;
    border-radius: 9px;
}}
QFrame#LearningReportPreviewPanel {{
    background-color: #E9F0F3;
    border: 1px solid #D0DCE2;
    border-radius: 12px;
}}
QWidget#LearningReportPreviewCanvas {{
    background-color: #E9F0F3;
}}
QFrame#LearningReportPaperPage {{
    background-color: #FFFFFF;
    border: 1px solid #D1DCE1;
    border-radius: 3px;
}}
QWidget#LearningReportRevisionCanvas {{
    background-color: #E9F0F3;
}}
QFrame#LearningReportRevisionPaper {{
    background-color: #FFFFFF;
    border: 1px solid #D1DCE1;
    border-radius: 3px;
}}
QFrame#LearningReportDocumentBlock {{
    background-color: #F7FAFB;
    border: 1px solid #D8E2E7;
    border-radius: 8px;
}}
QFrame#ObservationFilterBar {{
    background-color: rgba(248, 251, 253, 210);
    border: 1px solid #DCE7EF;
    border-radius: 8px;
}}
QProgressBar#CompetencyCockpitProgressBar {{
    min-height: 8px;
    max-height: 8px;
    background-color: #E5E7EB;
    border: none;
    border-radius: 4px;
}}
QProgressBar#CompetencyCockpitProgressBar::chunk {{
    background-color: #7C91A3;
    border-radius: 4px;
}}
QPushButton {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_NAVY};
    border: 1px solid #B9CAD7;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 550;
}}
QPushButton:hover {{
    background-color: #EFF5FA;
    border-color: #92ABC0;
}}
QPushButton:pressed {{
    background-color: #E1ECF5;
    border-color: #7897B0;
}}
QPushButton:disabled {{
    color: #94A3B8;
    background-color: #EEF3F7;
    border-color: #E3EAF0;
}}
QPushButton:focus {{
    border: 2px solid {COLOR_FOCUS};
    padding: 6px 13px;
}}
QPushButton[buttonRole="primary"] {{
    background-color: {COLOR_BLUE};
    color: #FFFFFF;
    border-color: {COLOR_BLUE_DARK};
    font-weight: 650;
}}
QPushButton[buttonRole="primary"]:hover {{ background-color: {COLOR_BLUE_DARK}; }}
QPushButton[buttonRole="primary"]:pressed {{ background-color: {COLOR_BLUE_PRESSED}; }}
QPushButton[buttonRole="primary"]:disabled {{
    background-color: #93C5FD;
    border-color: #93C5FD;
    color: #F8FAFC;
}}
QPushButton[buttonRole="secondary"] {{
    background-color: {LIGHT_BLUE};
    color: {COLOR_NAVY};
    border-color: #AFCFE5;
}}
QPushButton[buttonRole="secondary"]:hover {{
    background-color: {LIGHT_TEAL};
    color: {COLOR_NAVY};
    border-color: #8FC7C5;
}}
QPushButton[buttonRole="secondary"]:focus {{ color: {COLOR_NAVY}; }}
QPushButton[buttonRole="secondary"]:pressed {{ color: {COLOR_NAVY}; }}
QPushButton[buttonRole="quiet"] {{
    background-color: transparent;
    color: {COLOR_TEXT_MUTED};
    border-color: transparent;
}}
QPushButton[buttonRole="quiet"]:hover {{
    background-color: {LIGHT_TEAL};
    color: {COLOR_NAVY};
}}
QPushButton[buttonRole="destructive"] {{
    background-color: #FFF8F8;
    color: {COLOR_ERROR};
    border-color: #E5C3C8;
}}
QPushButton[buttonRole="destructive"]:hover {{ background-color: #FCE8EB; }}
QPushButton[buttonRole="icon"] {{
    background-color: transparent;
    border-color: transparent;
    padding: 6px;
    min-width: 28px;
}}
QPushButton[buttonRole="link"] {{
    background-color: transparent;
    color: {COLOR_BLUE_DARK};
    border-color: transparent;
    padding-left: 2px;
    padding-right: 2px;
}}
QPushButton[buttonRole="link"]:hover {{ text-decoration: underline; }}
QPushButton#SegmentedControlButton {{
    border-radius: 0px;
    border-right: none;
    padding: 8px 15px;
}}
QPushButton#SegmentedControlButton[segmentPosition="first"] {{
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
}}
QPushButton#SegmentedControlButton[segmentPosition="last"] {{
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    border-right: 1px solid #BED0DE;
}}
QPushButton#SegmentedControlButton:checked {{
    background-color: {LIGHT_BLUE};
    border-color: #9FB9CE;
    color: {COLOR_NAVY};
    font-weight: 650;
}}
QPushButton#SegmentedControlButton:focus {{
    border: 2px solid {COLOR_FOCUS};
    padding: 7px 14px;
}}
QDialog[dialogContext="observation"] QPushButton#SegmentedControlButton:checked {{
    background-color: {LIGHT_TEAL};
    border-color: #8FC7C5;
}}
QPushButton#SegmentedControlButton:disabled,
QPushButton#SegmentedControlButton:checked:disabled {{
    color: #94A3B8;
    background-color: #EEF3F7;
    border-color: #E3EAF0;
}}
QWidget#StudentProfilePageHeader {{
    background-color: transparent;
}}
QFrame#StudentProfileHeaderSurface {{
    background-color: #FFFFFF;
    border-color: #D8E4EC;
    border-radius: 18px;
}}
QLabel#StudentProfileAvatar {{
    background-color: {BRAND_TEAL};
    color: #FFFFFF;
    border-radius: 26px;
    font-size: 16px;
    font-weight: 700;
}}
QLabel#StudentProfileContextBadge {{
    color: #365966;
    background-color: #E9F1F3;
    border: 1px solid #D4E2E5;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
}}
QFrame#StudentProfileOrientationCard {{
    background-color: #FFFFFF;
    border-color: #D8E4EC;
}}
QFrame#StudentProfileCompetencySummaryCard {{
    background-color: {LIGHT_TEAL};
    border-color: #C2E2DE;
}}
QFrame#StudentProfileUndocumentedCard {{
    background-color: {LIGHT_ORANGE};
    border-color: #EBCBAA;
}}
QLabel#StudentProfileEyebrow {{
    color: {BRAND_TEAL};
    font-size: 10px;
    font-weight: 700;
}}
QLabel#StudentProfileDocumentationMetric {{
    color: {COLOR_NAVY};
    font-size: 25px;
    font-weight: 700;
}}
QFrame#StudentProfileOrientationChange,
QFrame#StudentProfileDashboardSummaryRow {{
    background-color: #FAFCFC;
    border-color: #DFE8EA;
    border-radius: 11px;
}}
QFrame#StudentProfileOrientationChange[interactive="true"]:hover {{
    background-color: #F4F8FC;
    border-color: #9BBBD2;
}}
QFrame#StudentProfileOrientationChange[interactive="true"]:focus {{
    border: 2px solid {COLOR_FOCUS};
}}
QFrame#StudentProfileOrientationChange[interactive="true"][pressed="true"] {{
    background-color: #EAF2F8;
    border-color: #7EA6C2;
}}
QFrame#StudentProfileOrientationStatusChange {{
    background-color: transparent;
    border: none;
    min-width: 250px;
}}
QLabel#StudentProfileDevelopmentArrow {{
    color: #718491;
    font-size: 13px;
    font-weight: 700;
    min-height: 12px;
}}
QFrame#StudentProfileOrientationEvidence {{
    background-color: #F3F7F8;
    border: none;
    border-radius: 8px;
}}
QLabel#StudentProfileEvidenceBadge,
QLabel#StudentProfileHistoricalBadge {{
    color: #365966;
    background-color: #E9F1F3;
    border: 1px solid #D4E2E5;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
}}
QFrame#StudentProfileNavigation {{
    background-color: transparent;
    border: none;
}}
QTabWidget#StudentProfileTabs::pane {{
    border: none;
    background-color: transparent;
}}
QLineEdit#CompetencyCockpitSearch,
QLineEdit#ObservationCatalogSearch {{
    min-height: 20px;
    background-color: #FFFFFF;
    border: 1px solid #C9D8E4;
    border-radius: 9px;
    padding: 7px 10px;
}}
QLineEdit#CompetencyCockpitSearch:focus,
QLineEdit#ObservationCatalogSearch:focus {{
    border: 2px solid {COLOR_FOCUS};
    padding: 6px 9px;
}}
QFrame#ObservationDialogZone {{
    background-color: #FFFFFF;
    border: 1px solid #C9D8E4;
    border-radius: 14px;
}}
QFrame#ObservationDialogZone[zoneRole="context"] {{
    background-color: {LIGHT_TEAL};
    border-color: #C4E1DE;
}}
QFrame#ObservationDialogZone[zoneRole="primary"] {{
    background-color: #FFFFFF;
    border-color: #9FCFCC;
}}
QFrame#ObservationDialogZone[zoneRole="entry"] {{
    background-color: #FBFCFE;
    border-color: #CAD9E4;
}}
QFrame#ObservationSelectedCompetencyCard[historical="true"] {{
    background-color: #FFFAF5;
    border-color: #E9E1D6;
}}
QFrame#ObservationCatalogCompetencyTile[selected="false"]:hover,
QFrame#ObservationRecentCompetencyChip[selected="false"]:hover {{
    background-color: {LIGHT_TEAL};
    border-color: #9BCFCC;
}}
QFrame#ObservationCatalogCompetencyTile QLabel,
QFrame#ObservationRecentCompetencyChip QLabel,
QFrame#ObservationCatalogCompetencyTile:hover QLabel,
QFrame#ObservationRecentCompetencyChip:hover QLabel,
QFrame#ObservationCatalogCompetencyTile:focus QLabel,
QFrame#ObservationRecentCompetencyChip:focus QLabel,
QFrame#ObservationCatalogCompetencyTile[selected="true"] QLabel,
QFrame#ObservationRecentCompetencyChip[selected="true"] QLabel {{
    color: {COLOR_TEXT};
    background-color: transparent;
}}
QFrame#ObservationCatalogCompetencyTile[selected="false"]:focus,
QFrame#ObservationRecentCompetencyChip[selected="false"]:focus {{
    border: 2px solid {COLOR_FOCUS};
}}
QFrame#ObservationCatalogCompetencyTile[selected="true"],
QFrame#ObservationRecentCompetencyChip[selected="true"] {{
    background-color: #F2F7FA;
    border-color: #D9E5EC;
}}
QFrame#ObservationCatalogCompetencyTile[selected="true"]:focus,
QFrame#ObservationRecentCompetencyChip[selected="true"]:focus {{
    background-color: #EEF5FF;
    border: 2px solid {COLOR_FOCUS};
    border-left-color: {COLOR_BLUE};
}}
QFrame#ObservationCatalogCompetencyTile[selected="true"]:disabled,
QFrame#ObservationRecentCompetencyChip[selected="true"]:disabled {{
    background-color: #F3F6F8;
    border: 2px solid #E2E8ED;
}}
QFrame#ObservationRecentCompetencyChip {{ border-radius: 12px; }}
QLabel#ObservationHistoricalBadge {{
    color: #76502F;
    background-color: #F8EEE4;
    border: 1px solid #E7D2BB;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#ObservationQuickObservationBadge {{
    color: {COLOR_TEXT_MUTED};
    background-color: #EDF2F6;
    border: 1px solid #D8E2EA;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#ObservationHierarchyToggle {{
    background-color: transparent;
    border: none;
    color: {COLOR_NAVY};
    padding: 7px 5px;
    text-align: left;
    font-weight: 600;
}}
QPushButton#ObservationHierarchyToggle:hover {{
    background-color: #EEF6FB;
    color: {COLOR_NAVY};
}}
QPushButton#ObservationHierarchyToggle:focus {{
    color: {COLOR_NAVY};
    border: 2px solid {COLOR_FOCUS};
}}
QPushButton#ObservationHierarchyToggle:pressed {{ color: {COLOR_NAVY}; }}
QPushButton#ObservationRemoveCompetencyButton {{
    min-width: 30px;
    max-width: 30px;
    min-height: 28px;
    padding: 2px;
}}
QFrame#ObservationFileRow {{ border-radius: 8px; }}
QFrame#CompetencyCockpitSubjectCard {{ border-color: #BBD1EE; }}
QFrame#CompetencyCockpitLearningAreaCard {{ margin-left: 8px; }}
QFrame#CompetencyCockpitTopicCard {{ margin-left: 12px; }}
QFrame#CompetencyCockpitSubjectCard[interactive="true"]:hover,
QFrame#CompetencyCockpitLearningAreaCard[interactive="true"]:hover,
QFrame#CompetencyCockpitTopicCard[interactive="true"]:hover,
QFrame#CompetencyCockpitCompetencyRow[interactive="true"]:hover {{
    background-color: #F4F8FC;
    border-color: #8EB6E5;
}}
QFrame#CompetencyCockpitSubjectCard[interactive="true"]:focus,
QFrame#CompetencyCockpitLearningAreaCard[interactive="true"]:focus,
QFrame#CompetencyCockpitTopicCard[interactive="true"]:focus,
QFrame#CompetencyCockpitCompetencyRow[interactive="true"]:focus {{
    border: 2px solid {COLOR_FOCUS};
}}
QFrame#CompetencyCockpitSubjectCard[interactive="true"][pressed="true"],
QFrame#CompetencyCockpitLearningAreaCard[interactive="true"][pressed="true"],
QFrame#CompetencyCockpitTopicCard[interactive="true"][pressed="true"],
QFrame#CompetencyCockpitCompetencyRow[interactive="true"][pressed="true"] {{
    background-color: #E7F0FA;
    border-color: #6C9FD3;
}}
QFrame#ReportOverviewCompetencySegment {{
    background-color: #7BBFC0;
    border: none;
    border-radius: 3px;
}}
QFrame#ReportOverviewTimelineConnector {{
    background-color: #B9CEDB;
    border: none;
}}
QFrame#ReportOverviewTimelineConnector[edge="true"] {{
    background-color: transparent;
}}
QPushButton#ReportOverviewTimelinePrevious,
QPushButton#ReportOverviewTimelineNext {{
    min-width: 30px;
    max-width: 30px;
    padding: 4px;
    font-size: 19px;
}}
QLabel#ReportOverviewSubjectSymbol {{
    min-width: 23px;
    min-height: 23px;
    max-width: 23px;
    max-height: 23px;
    background-color: #EAF5F5;
    color: {COLOR_NAVY};
    border: 1px solid #BFDCDC;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
}}
QLabel#ReportOverviewProjectionWarning {{
    background-color: #FFF8E8;
    border: 1px solid #E8D3A2;
    border-radius: 7px;
    padding: 7px 9px;
}}
QPushButton#CompetencyCockpitCompetencyButton {{
    text-align: left;
    padding: 7px 9px;
}}
QPushButton#ObservationTextActionButton {{
    background-color: transparent;
    border: none;
    color: {COLOR_TEXT_MUTED};
    padding: 3px 6px;
    font-weight: 500;
}}
QPushButton#ObservationTextActionButton:hover {{
    background-color: #EEF6FB;
    color: {COLOR_NAVY};
}}
QPushButton#ObservationResetButton {{
    background-color: transparent;
    color: {COLOR_TEXT_MUTED};
    border: 1px solid #D7E3EC;
    border-radius: 7px;
    padding: 4px 9px;
    font-weight: 500;
}}
QPushButton#ObservationResetButton:hover {{
    background-color: #EEF6FB;
    color: {COLOR_NAVY};
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QDateTimeEdit,
QTimeEdit, QSpinBox, QDoubleSpinBox {{
    background-color: rgba(255, 255, 255, 248);
    color: {COLOR_TEXT};
    border: 1px solid #C5D3DE;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: {BRAND_BLUE};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
QDateEdit:hover, QDateTimeEdit:hover, QTimeEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #9FB4C5;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {COLOR_FOCUS};
    padding: 6px 8px;
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QComboBox:disabled, QDateEdit:disabled, QDateTimeEdit:disabled,
QTimeEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: #8796A5;
    background-color: #EEF2F5;
    border-color: #DDE4E9;
}}
QLineEdit#SearchField {{
    min-width: 260px;
    padding-left: 10px;
}}
QTableWidget:focus, QListWidget:focus, QTreeWidget:focus {{
    border: 1px solid {COLOR_FOCUS};
}}
QFrame#InlineMessage {{
    background-color: #EEF5FA;
    border: 1px solid #CBDCE9;
    border-radius: 8px;
}}
QFrame#InlineMessage[messageTone="warning"] {{
    background-color: #FFF8E8;
    border-color: #E8D3A2;
}}
QFrame#InlineMessage[messageTone="error"] {{
    background-color: #FFF1F2;
    border-color: #E7B8C0;
}}
QFrame#EmptyState {{
    background-color: {COLOR_SURFACE_SOFT};
    border: 1px dashed {COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#Toast {{
    background-color: #22384A;
    border: 1px solid #38566E;
    border-radius: 9px;
}}
QFrame#Toast QLabel {{
    color: #FFFFFF;
    font-weight: 600;
}}
QFrame#Toast[toastTone="success"] {{
    background-color: #155E4A;
    border-color: #0F4C3D;
}}
QFrame#Toast[toastTone="warning"] {{
    background-color: #755719;
    border-color: #947333;
}}
QFrame#Toast[toastTone="error"] {{
    background-color: #8F1D2C;
    border-color: #6F1622;
}}
QFrame#NavigationSelectionIndicator {{
    background-color: #85D8D6;
    border: none;
    border-radius: 2px;
}}
QFrame#SegmentedControlIndicator {{
    background-color: {COLOR_FOCUS};
    border: none;
    border-radius: 1px;
}}
QPushButton[saveConfirmed="true"] {{
    background-color: {COLOR_SUCCESS};
    border-color: #3C806D;
    color: #FFFFFF;
}}
QComboBox, QDateEdit, QDateTimeEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {{
    padding-right: 26px;
    min-height: 25px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E2EAF1;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background-color: rgba(238, 246, 251, 150);
}}
QComboBox::down-arrow {{
    image: url("{icon_path('chevron-down').as_posix()}");
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_TEXT};
    border: 1px solid #C9D8E4;
    selection-background-color: {COLOR_BLUE_SOFT};
    selection-color: {COLOR_TEXT};
    padding: 5px;
    outline: none;
}}
QMenu {{
    background-color: rgba(255, 255, 255, 250);
    color: {COLOR_TEXT};
    border: 1px solid #C9D7E1;
    border-radius: 9px;
    padding: 6px;
}}
QMenu::item {{
    border-radius: 6px;
    padding: 7px 24px 7px 10px;
}}
QMenu::item:selected {{
    background-color: {LIGHT_TEAL};
    color: {COLOR_NAVY};
}}
QMenu::item:disabled {{
    color: #93A1AE;
    background-color: transparent;
}}
QMenu::separator {{
    height: 1px;
    background-color: #E2E9EE;
    margin: 5px 8px;
}}
QToolTip {{
    background-color: {BRAND_NAVY};
    color: #FFFFFF;
    border: 1px solid #49677F;
    border-radius: 6px;
    padding: 5px 7px;
}}
QDateEdit::drop-down, QDateTimeEdit::drop-down, QTimeEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E2EAF1;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background-color: rgba(238, 246, 251, 150);
}}
QDateEdit::down-arrow, QDateTimeEdit::down-arrow, QTimeEdit::down-arrow {{
    image: url("{icon_path('chevron-down').as_posix()}");
    width: 12px;
    height: 12px;
}}
QLineEdit#ObservationFilterInput {{
    background-color: rgba(255, 255, 255, 232);
    border: 1px solid #D7E3EC;
    border-radius: 7px;
    padding: 4px 9px;
    min-height: 22px;
}}
QLineEdit#ObservationFilterInput:focus {{
    border: 1px solid #A8C5DD;
}}
QTabBar::tab {{
    background-color: #F1F5F8;
    color: {COLOR_TEXT_MUTED};
    border: 1px solid #C7D5E0;
    border-right: none;
    padding: 8px 15px;
    font-weight: 550;
}}
QTabBar::tab:first {{
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
}}
QTabBar::tab:last {{
    border-right: 1px solid #C7D5E0;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}
QTabBar::tab:hover:!selected {{
    background-color: #E8F0F6;
    color: {COLOR_NAVY};
}}
QTabBar::tab:selected {{
    background-color: #FFFFFF;
    color: {COLOR_NAVY};
    border-color: #91AAC0;
    font-weight: 650;
}}
QTableWidget, QListWidget, QTreeWidget {{
    background-color: {COLOR_SURFACE};
    alternate-background-color: #F3F8FB;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    gridline-color: #E5EDF3;
    selection-background-color: {COLOR_BLUE_SOFT};
    selection-color: {COLOR_TEXT};
}}
QTableWidget#PremiumTable {{
    background-color: #FFFFFF;
    alternate-background-color: #FAFCFD;
    border: 1px solid #DCE6ED;
    border-radius: 12px;
    gridline-color: transparent;
    outline: none;
}}
QTableWidget#PremiumTable::item {{
    border-bottom: 1px solid #E8EEF2;
    padding: 9px 10px;
}}
QTableWidget#PremiumTable::item:hover {{ background-color: #F4F8FB; }}
QTableWidget#PremiumTable::item:selected {{ background-color: #E2EEF9; color: {COLOR_TEXT}; }}
QTableWidget#PremiumTable::item:focus {{
    border: 1px solid {COLOR_FOCUS};
    background-color: #EDF5FF;
}}
QTableWidget#PremiumTable:focus {{ border: 2px solid {COLOR_FOCUS}; }}
QListWidget::item {{
    min-height: 28px;
    padding: 6px 9px;
    border-radius: 6px;
}}
QListWidget::item:hover {{ background-color: #F2F7FB; }}
QListWidget::item:selected {{ background-color: #E6F0FB; color: {COLOR_TEXT}; }}
QTreeWidget {{
    background-color: #FFFFFF;
    border: 1px solid #DCE6ED;
    border-radius: 10px;
    outline: none;
    padding: 4px;
}}
QTreeWidget::item {{
    min-height: 26px;
    padding: 5px 7px;
    border-radius: 6px;
}}
QTreeWidget::item:hover {{ background-color: #F2F7FB; }}
QTreeWidget::item:selected {{ background-color: #E6F0FB; color: {COLOR_TEXT}; }}
QTreeWidget::item:focus {{ border: 1px solid {COLOR_FOCUS}; }}
QHeaderView::section {{
    background-color: #EAF1F5;
    color: {COLOR_NAVY};
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 7px 8px;
    font-weight: 600;
}}
QHeaderView::section:hover {{ background-color: #DDE8EF; }}
QFrame[frameShape="4"] {{
    background-color: #DDE6EC;
    border: none;
    max-height: 1px;
}}
QFrame[frameShape="5"] {{
    background-color: #DDE6EC;
    border: none;
    max-width: 1px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 1px;
}}
QScrollBar::handle:vertical {{
    background-color: #B8C6D0;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background-color: #8CA2B3; }}
QScrollBar::handle:vertical:pressed {{ background-color: #70899D; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: transparent;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 1px 2px;
}}
QScrollBar::handle:horizontal {{
    background-color: #B8C6D0;
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: #8CA2B3; }}
QScrollBar::handle:horizontal:pressed {{ background-color: #70899D; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: transparent;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    margin-top: 10px;
    padding: 10px;
    background-color: {COLOR_SURFACE_SOFT};
    font-weight: 600;
    color: {COLOR_NAVY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
QMessageBox {{
    background-color: {COLOR_BACKGROUND};
}}
QMessageBox QLabel#qt_msgbox_label {{
    min-width: 320px;
    color: {COLOR_TEXT};
    font-size: 13px;
}}
QMessageBox QPushButton {{
    min-width: 92px;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QDialog {{
    background-color: {COLOR_BACKGROUND};
}}
"""

PRIMARY_BUTTON_STYLESHEET = f"""
QPushButton {{
    background-color: {COLOR_BLUE};
    color: #FFFFFF;
    border: 1px solid {COLOR_BLUE_DARK};
    border-radius: 7px;
    padding: 6px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {COLOR_BLUE_DARK};
}}
QPushButton:pressed {{
    background-color: {COLOR_BLUE_PRESSED};
}}
QPushButton:disabled {{
    background-color: #93C5FD;
    border-color: #93C5FD;
}}
"""


def apply_app_theme(app: QApplication) -> None:
    """Apply the app-wide stylesheet while retaining the native system font."""
    app.setStyleSheet(APP_STYLESHEET)


def create_card() -> QFrame:
    """Return a consistently styled content card."""
    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    card.setObjectName("AppCard")
    card.setProperty("cardVariant", "default")
    return card


def set_label_style(label: QLabel, role: str) -> None:
    """Apply a semantic text style to a label."""
    label.setStyleSheet(TYPOGRAPHY_STYLES[role])


def set_button_role(button: object, role: str) -> None:
    """Assign one semantic button role and refresh its stylesheet state."""
    button.setProperty("buttonRole", role)
    style = button.style()
    style.unpolish(button)
    style.polish(button)
