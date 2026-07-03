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

FONT_FAMILY = "Arial"

APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT};
    font-family: {FONT_FAMILY};
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
    font-family: {FONT_FAMILY};
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
QListWidget#AppNavigation {{
    background-color: transparent;
    color: #EAF2F8;
    border: none;
    padding: 8px 0;
    outline: none;
}}
QListWidget#AppNavigation::item {{
    border-radius: 8px;
    padding: 9px 10px;
    margin: 2px 0;
}}
QListWidget#AppNavigation::item:selected {{
    background-color: {COLOR_BLUE};
    color: #FFFFFF;
}}
QListWidget#AppNavigation::item:hover {{
    background-color: #174A74;
}}
QFrame#AppCard {{
    background-color: {COLOR_GLASS};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#AppPanel {{
    background-color: {COLOR_GLASS_SOFT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#ObservationFilterBar {{
    background-color: rgba(248, 251, 253, 210);
    border: 1px solid #DCE7EF;
    border-radius: 8px;
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
    """Apply the app-wide PySide stylesheet."""
    app.setStyleSheet(APP_STYLESHEET)


def create_card() -> QFrame:
    """Return a consistently styled content card."""
    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    card.setObjectName("AppCard")
    return card


def set_label_style(label: QLabel, role: str) -> None:
    """Apply a semantic text style to a label."""
    styles = {
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
    label.setStyleSheet(styles[role])
