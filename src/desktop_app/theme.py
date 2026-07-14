"""Central visual theme for the PySide desktop app."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame, QLabel


COLOR_NAVY = "#0B3A63"
COLOR_BLUE = "#2563EB"
COLOR_BLUE_DARK = "#1D4ED8"
COLOR_BLUE_PRESSED = "#1E40AF"
COLOR_BLUE_SOFT = "#DBEAFE"
COLOR_TURQUOISE = "#0EA5A7"
COLOR_GREEN = "#16A34A"
COLOR_ORANGE = "#F97316"
COLOR_BACKGROUND = "#F4F8FB"
COLOR_SURFACE = "#FFFFFF"
COLOR_SURFACE_SOFT = "#F8FBFD"
COLOR_GLASS = "rgba(255, 255, 255, 246)"
COLOR_GLASS_SOFT = "rgba(248, 251, 253, 242)"
COLOR_BORDER = "#C9D8E4"
COLOR_TEXT = "#1F2937"
COLOR_TEXT_MUTED = "#556372"
COLOR_TEXT_SUBTLE = "#6B7280"
COLOR_ERROR = "#B00020"
COLOR_SUCCESS = "#24705A"
COLOR_WARNING = "#8A6418"
COLOR_INFO = "#315F83"
COLOR_FOCUS = "#5B8DEF"

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

TYPOGRAPHY_STYLES = {
    "app_title": f"font-size: 24px; font-weight: 700; color: {COLOR_NAVY};",
    "screen_title": f"font-size: 22px; font-weight: 700; color: {COLOR_NAVY};",
    "dialog_title": f"font-size: 20px; font-weight: 700; color: {COLOR_NAVY};",
    "section_title": f"font-size: 16px; font-weight: 600; color: {COLOR_NAVY};",
    "card_title": f"font-weight: 600; color: {COLOR_NAVY};",
    "muted": f"color: {COLOR_TEXT_MUTED};",
    "subtle": f"color: {COLOR_TEXT_SUBTLE};",
    "body": f"color: {COLOR_TEXT};",
    "error": f"color: {COLOR_ERROR};",
    "small": f"color: {COLOR_TEXT_SUBTLE}; font-size: 11px;",
    "field_label": f"color: {COLOR_TEXT_MUTED}; font-size: 12px;",
}

APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT};
}}
QWidget#AppRoot {{
    background-color: {COLOR_BACKGROUND};
}}
QWidget#AppSidebar {{
    background-color: {COLOR_NAVY};
    border-top-right-radius: 14px;
    border-bottom-right-radius: 14px;
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
    background-color: #174A74;
}}
QListWidget#AppNavigation {{
    background-color: transparent;
    color: #EAF2F8;
    border: none;
    padding: 8px 0;
    outline: none;
}}
QListWidget#AppNavigation::item {{
    border-radius: 8px;
    padding: 9px 10px 9px 8px;
    margin: 2px 0;
}}
QListWidget#AppNavigation::item:selected {{
    background-color: {COLOR_BLUE};
    color: #FFFFFF;
}}
QListWidget#AppNavigation::item:hover {{
    background-color: #174A74;
}}
QListWidget#AppNavigation::item:focus {{
    border: 2px solid #9FC5F1;
}}
QListWidget#AppNavigation::item:disabled {{
    color: #9FB6C8;
    background-color: transparent;
    padding-top: 16px;
    padding-bottom: 3px;
    font-size: 10px;
    font-weight: 700;
}}
QFrame#AppCard, QFrame[cardVariant="default"], QFrame[cardVariant="soft"],
QFrame[cardVariant="accent"], QFrame[cardVariant="interactive"] {{
    background-color: {COLOR_GLASS};
    border: 1px solid #D8E4EC;
    border-radius: 14px;
}}
QFrame[cardVariant="soft"] {{
    background-color: {COLOR_SURFACE_SOFT};
    border-color: #E1EAF0;
}}
QFrame[cardVariant="accent"] {{
    background-color: #EEF5FF;
    border-color: #BBD1EE;
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
QFrame#AppPanel {{
    background-color: {COLOR_GLASS_SOFT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#DashboardHero {{
    background-color: #EAF3FF;
    border: 1px solid #ABC8EA;
    border-radius: 18px;
}}
QFrame#DashboardTimeline, QFrame#DashboardHeatmap,
QFrame#DashboardMatchingChildren {{
    background-color: {COLOR_GLASS};
    border: 1px solid #D8E4EC;
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
QFrame#FilterBar {{
    background-color: {COLOR_SURFACE_SOFT};
    border: 1px solid #DCE7EF;
    border-radius: 12px;
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
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    border-radius: 8px;
}}
QLineEdit#SearchField {{
    min-height: 20px;
    background-color: #FFFFFF;
    border: 1px solid #C9D8E4;
    border-radius: 9px;
    padding: 7px 10px;
}}
QLineEdit#SearchField:hover {{ border-color: #9CB8CE; }}
QLineEdit#SearchField:focus {{ border: 2px solid {COLOR_FOCUS}; padding: 6px 9px; }}
QLabel#StatusBadge {{
    background-color: #EDF2F6;
    color: {COLOR_TEXT_MUTED};
    border: 1px solid #D8E2EA;
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#StatusBadge[badgeTone="info"] {{ background-color: #E8F2FB; color: {COLOR_INFO}; border-color: #C7DCEB; }}
QLabel#StatusBadge[badgeTone="success"] {{ background-color: #EAF6F0; color: {COLOR_SUCCESS}; border-color: #C7E3D6; }}
QFrame#DashboardHeatmapCell[coverageLevel="0"] QFrame#DashboardHeatmapMarker {{ background-color: #CBD5E1; }}
QFrame#DashboardHeatmapCell[coverageLevel="1"] QFrame#DashboardHeatmapMarker {{ background-color: #B7C9DC; }}
QFrame#DashboardHeatmapCell[coverageLevel="2"] QFrame#DashboardHeatmapMarker {{ background-color: #91ADC8; }}
QFrame#DashboardHeatmapCell[coverageLevel="3"] QFrame#DashboardHeatmapMarker {{ background-color: #6F91B2; }}
QFrame#DashboardHeatmapCell[coverageLevel="4"] QFrame#DashboardHeatmapMarker {{ background-color: #4F7599; }}
QFrame#LearningReportTopBar {{
    background-color: {COLOR_NAVY};
    border: none;
    border-radius: 0px;
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
    background-color: #F7FAFB;
    border-right: 1px solid #D8E2E7;
}}
QPushButton#LearningReportSubjectButton {{
    text-align: left;
    background-color: transparent;
    border: none;
    padding: 10px 12px;
    color: #49606F;
}}
QPushButton#LearningReportSubjectButton:checked {{
    background-color: #E5F0F4;
    color: {COLOR_NAVY};
    border-left: 3px solid {COLOR_BLUE};
}}
QLabel#LearningReportEyebrow {{
    color: {COLOR_BLUE};
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
    border: 1px solid #BED0DE;
    border-radius: 8px;
    padding: 6px 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLOR_BLUE_SOFT};
    border-color: #B7CEE2;
}}
QPushButton:pressed {{
    background-color: #C7DDF3;
}}
QPushButton:disabled {{
    color: #94A3B8;
    background-color: #EEF3F7;
    border-color: #E3EAF0;
}}
QPushButton:focus {{
    border: 2px solid {COLOR_FOCUS};
    padding: 5px 12px;
}}
QPushButton[buttonRole="primary"] {{
    background-color: {COLOR_BLUE};
    color: #FFFFFF;
    border-color: {COLOR_BLUE_DARK};
    font-weight: 600;
}}
QPushButton[buttonRole="primary"]:hover {{ background-color: {COLOR_BLUE_DARK}; }}
QPushButton[buttonRole="primary"]:pressed {{ background-color: {COLOR_BLUE_PRESSED}; }}
QPushButton[buttonRole="primary"]:disabled {{
    background-color: #93C5FD;
    border-color: #93C5FD;
    color: #F8FAFC;
}}
QPushButton[buttonRole="secondary"] {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_NAVY};
}}
QPushButton[buttonRole="quiet"] {{
    background-color: transparent;
    color: {COLOR_TEXT_MUTED};
    border-color: transparent;
}}
QPushButton[buttonRole="quiet"]:hover {{
    background-color: #EAF2F8;
    color: {COLOR_NAVY};
}}
QPushButton[buttonRole="destructive"] {{
    background-color: #FFF5F5;
    color: {COLOR_ERROR};
    border-color: #E7B8C0;
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
    padding: 7px 14px;
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
    background-color: {COLOR_NAVY};
    border-color: {COLOR_NAVY};
    color: #FFFFFF;
    font-weight: 600;
}}
QWidget#StudentProfilePageHeader {{
    background-color: transparent;
}}
QFrame#StudentProfileHeaderSurface {{
    background-color: #EEF5FF;
    border-color: #BBD1EE;
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
QFrame#ObservationSelectedCompetencyCard[historical="true"] {{
    background-color: #FFFAF5;
    border-color: #E9E1D6;
}}
QFrame#ObservationCatalogCompetencyTile[selected="false"]:hover,
QFrame#ObservationRecentCompetencyChip[selected="false"]:hover {{
    background-color: #EEF6FB;
    border-color: #AFCADC;
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
QPushButton#ObservationHierarchyToggle:hover {{ background-color: #EEF6FB; }}
QPushButton#ObservationHierarchyToggle:focus {{ border: 2px solid {COLOR_FOCUS}; }}
QPushButton#ObservationRatingChip {{
    background-color: #F7FAFC;
    border: 1px solid #D2E0EA;
    border-radius: 7px;
    color: #38546B;
    min-height: 27px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#ObservationRatingChip:checked {{
    background-color: {COLOR_BLUE};
    border-color: {COLOR_BLUE};
    color: #FFFFFF;
}}
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
QLineEdit, QTextEdit, QComboBox, QDateEdit, QDateTimeEdit, QTimeEdit {{
    background-color: rgba(255, 255, 255, 248);
    color: {COLOR_TEXT};
    border: 1px solid #C9D8E4;
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {COLOR_BLUE};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus {{
    border: 1px solid {COLOR_BLUE};
}}
QLineEdit#SearchField {{
    min-width: 260px;
    padding-left: 10px;
}}
QTableWidget:focus, QListWidget:focus {{
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
QLabel#StatusBadge {{
    background-color: #E7EEF5;
    color: {COLOR_INFO};
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QFrame#Toast {{
    background-color: #22384A;
    border: 1px solid #38566E;
    border-radius: 9px;
}}
QFrame#Toast QLabel {{ color: #FFFFFF; }}
QFrame#Toast[toastTone="success"] {{
    background-color: {COLOR_SUCCESS};
    border-color: #3C806D;
}}
QFrame#Toast[toastTone="warning"] {{
    background-color: #755719;
    border-color: #947333;
}}
QComboBox, QDateEdit, QDateTimeEdit, QTimeEdit {{
    padding-right: 26px;
    min-height: 24px;
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
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLOR_TEXT_MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_TEXT};
    border: 1px solid #C9D8E4;
    selection-background-color: {COLOR_BLUE_SOFT};
    selection-color: {COLOR_TEXT};
    padding: 4px;
    outline: none;
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
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLOR_TEXT_MUTED};
    margin-right: 8px;
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
QTableWidget, QListWidget {{
    background-color: {COLOR_GLASS};
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
QTableWidget#PremiumTable::item:hover {{ background-color: #F2F7FB; }}
QTableWidget#PremiumTable::item:selected {{ background-color: #E6F0FB; color: {COLOR_TEXT}; }}
QTableWidget#PremiumTable:focus {{ border: 2px solid {COLOR_FOCUS}; }}
QHeaderView::section {{
    background-color: #EAF2F8;
    color: {COLOR_NAVY};
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 7px 8px;
    font-weight: 600;
}}
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    margin-top: 10px;
    padding: 10px;
    background-color: {COLOR_GLASS_SOFT};
    font-weight: 600;
    color: {COLOR_NAVY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
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
