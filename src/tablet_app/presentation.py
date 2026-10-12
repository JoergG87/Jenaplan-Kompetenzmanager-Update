"""Tablet layout helpers; all values and actions remain owned by the original UI."""
from PySide6.QtCore import QEvent, QObject, Qt, QSize
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QBoxLayout, QComboBox, QDateTimeEdit, QGridLayout,
    QLabel, QLineEdit, QSizePolicy, QWidget, QStyledItemDelegate, QScrollArea, QScroller, QScrollerProperties,
)
from src.desktop_app.theme import COLOR_BACKGROUND, COLOR_TEXT
from src.desktop_app.components import AppCard, RatingBadgeButton


class TabletTapGuard(QObject):
    """Discard drag/cancel releases before custom cards can treat them as taps."""
    def __init__(self, widget):
        super().__init__(widget)
        self._press = None
        self._dragged = False

    def eventFilter(self, widget, event):
        kind = event.type()
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._dragged = False
        elif kind == QEvent.Type.MouseMove and self._press is not None:
            if (event.globalPosition().toPoint() - self._press).manhattanLength() > QApplication.startDragDistance():
                self._dragged = True
        elif kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            tap = (self._press is not None and not self._dragged
                   and widget.rect().contains(event.position().toPoint())
                   and (event.globalPosition().toPoint() - self._press).manhattanLength() <= QApplication.startDragDistance())
            self._press = None
            self._dragged = False
            if not tap:
                if isinstance(widget, AppCard):
                    widget.set_pressed(False)
                elif isinstance(widget, QAbstractButton):
                    widget.setDown(False)
                return True
        return False


def apply_tablet_theme(app):
    """Keep uncovered native surfaces light even with a dark system palette."""
    palette = app.palette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base):
        palette.setColor(role, QColor(COLOR_BACKGROUND))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text):
        palette.setColor(role, QColor(COLOR_TEXT))
    app.setPalette(palette)
    app.setStyleSheet(app.styleSheet() + '\nQWidget[tabletBackground="true"] { '
                      f'background-color: {COLOR_BACKGROUND}; border: none; }}')


def configure_tablet_scroll_area(scroll):
    """Paint empty viewports and keep swipes inside their content bounds."""
    for surface in (scroll, scroll.viewport()):
        surface.setProperty('tabletBackground', True)
        surface.setBackgroundRole(QPalette.ColorRole.Window)
        surface.setAutoFillBackground(True)
        surface.style().unpolish(surface)
        surface.style().polish(surface)
    if scroll.property('tabletViewportOnly'):
        QScroller.ungrabGesture(scroll.viewport())
        return
    if not scroll.property('tabletScrollGesture'):
        # Qt synthesizes mouse events for the first unhandled finger contact.
        # Use the same path as buttons/cards, rather than competing touch grabs.
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        scroll.setProperty('tabletScrollGesture', True)
    scroller = QScroller.scroller(scroll.viewport())
    properties = scroller.scrollerProperties()
    for metric in (QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy,
                   QScrollerProperties.ScrollMetric.VerticalOvershootPolicy):
        properties.setScrollMetric(metric, QScrollerProperties.OvershootPolicy.OvershootAlwaysOff)
    scroller.setScrollerProperties(properties)


def stop_tablet_scrollers(root):
    for scroll in root.findChildren(QScrollArea):
        if QScroller.hasScroller(scroll.viewport()):
            QScroller.scroller(scroll.viewport()).stop()


def rebind_tablet_scroll_gestures(root):
    """Register gestures in the final window after a dialog becomes a page."""
    stop_tablet_scrollers(root)
    for scroll in root.findChildren(QScrollArea):
        QScroller.ungrabGesture(scroll.viewport())
        scroll.setProperty('tabletScrollGesture', False)
        configure_tablet_scroll_area(scroll)


def clear_tablet_layout(layout):
    """Avoid creating temporary native iOS windows when rebuilding a projection."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            stop_tablet_scrollers(widget)
            if isinstance(widget, QScrollArea) and QScroller.hasScroller(widget.viewport()):
                QScroller.scroller(widget.viewport()).stop()
            widget.hide()
            widget.deleteLater()
        elif item.layout() is not None:
            clear_tablet_layout(item.layout())


class TabletChoiceDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(44, size.height()))


def touch_targets(root):
    for widget in root.findChildren(QWidget):
        if (isinstance(widget, QAbstractButton)
                or isinstance(widget, AppCard) and (widget.property('interactive')
                    or widget.objectName() in ('ObservationCatalogCompetencyTile', 'ObservationRecentCompetencyChip'))):
            if not hasattr(widget, 'tablet_tap_guard'):
                widget.tablet_tap_guard = TabletTapGuard(widget)
                widget.installEventFilter(widget.tablet_tap_guard)
        if isinstance(widget, QScrollArea):
            configure_tablet_scroll_area(widget)
        if isinstance(widget, (QAbstractButton, QComboBox, QLineEdit, QDateTimeEdit)) and not isinstance(widget, RatingBadgeButton):
            widget.setMaximumHeight(max(44, widget.maximumHeight()))
            widget.setMinimumHeight(max(44, widget.minimumHeight()))
        if isinstance(widget, QComboBox):
            if not isinstance(widget.itemDelegate(), TabletChoiceDelegate):
                delegate = TabletChoiceDelegate(widget)
                widget.setItemDelegate(delegate)
                widget.tablet_choice_delegate = delegate
            widget.setMaxVisibleItems(8)
            widget.view().setStyleSheet('QAbstractItemView::item { min-height: 44px; padding: 4px 8px; }')


def reflow_filter_bar(bar):
    """Give the original search field a full row, retaining all filter signals."""
    if bar.property('tabletFilterRows'):
        return
    layout = bar.layout()
    controls = []
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            controls.append(item.widget())
    layout.setDirection(QBoxLayout.Direction.TopToBottom)
    search = bar.search_field
    search.setMinimumWidth(0)
    search.setMaximumWidth(16777215)
    layout.addWidget(search)
    row = QGridLayout()
    for index, widget in enumerate(w for w in controls if w is not search):
        widget.setMinimumWidth(0)
        row.addWidget(widget, index // 3, index % 3)
    layout.addLayout(row)
    bar.setProperty('tabletFilterRows', True)
    touch_targets(bar)


def reflow_actions(bar, columns=3):
    """Move the existing actions into a compact grid, without reconnecting them."""
    if bar.property('tabletActionGrid'):
        return
    old = bar.layout()
    controls = []
    while old.count():
        item = old.takeAt(0)
        if item.widget():
            controls.append(item.widget())
    old.setDirection(QBoxLayout.Direction.TopToBottom)
    status = [w for w in controls if isinstance(w, QLabel)]
    for label in status:
        label.setWordWrap(True)
        old.addWidget(label)
    grid = QGridLayout()
    for index, widget in enumerate(w for w in controls if w not in status):
        widget.setMinimumWidth(0)
        grid.addWidget(widget, index // columns, index % columns)
    old.addLayout(grid)
    bar.setProperty('tabletActionGrid', True)
    touch_targets(bar)


class NavigationPicker(QComboBox):
    """A compact projection of existing exclusive navigation buttons."""
    def __init__(self, buttons, title, parent=None):
        super().__init__(parent)
        self.setAccessibleName(title)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._buttons = []
        self.currentIndexChanged.connect(self._activate)
        self.refresh(buttons)

    def refresh(self, buttons):
        previous_buttons = self._buttons
        self.blockSignals(True)
        self.clear()
        self._buttons = list(buttons)
        selected = 0
        for index, button in enumerate(self._buttons):
            self.addItem(button.icon(), button.text().replace('\n', ' ').replace('&&', '&'))
            if button.isChecked():
                selected = index
            if button not in previous_buttons:
                button.toggled.connect(lambda checked, item=button: self._selected(item) if checked else None)
        self.setCurrentIndex(selected)
        self.blockSignals(False)

    def _selected(self, button):
        if button in self._buttons:
            self.blockSignals(True)
            self.setCurrentIndex(self._buttons.index(button))
            self.blockSignals(False)

    def _activate(self, index):
        if 0 <= index < len(self._buttons):
            self._buttons[index].click()
