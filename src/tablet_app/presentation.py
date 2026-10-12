"""Tablet layout helpers; all values and actions remain owned by the original UI."""
import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QAbstractButton, QBoxLayout, QComboBox, QDateTimeEdit, QGridLayout,
    QLabel, QLineEdit, QSizePolicy, QWidget, QStyledItemDelegate, QScrollArea, QScroller,
)


class TabletChoiceDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(44, size.height()))


def touch_targets(root):
    for widget in root.findChildren(QWidget):
        if isinstance(widget, QScrollArea) and not widget.property('tabletScrollGesture'):
            simulator = sys.platform != 'ios'
            if sys.platform == 'ios':
                from jkm_ios_share import is_simulator
                simulator = is_simulator()
            gesture = QScroller.ScrollerGestureType.LeftMouseButtonGesture if simulator else QScroller.ScrollerGestureType.TouchGesture
            QScroller.grabGesture(widget.viewport(), gesture)
            widget.setProperty('tabletScrollGesture', True)
        if isinstance(widget, (QAbstractButton, QComboBox, QLineEdit, QDateTimeEdit)):
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
