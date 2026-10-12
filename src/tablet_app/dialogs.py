"""Tablet variants of the original report and conference presentation."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QSizePolicy, QLayout
from src.desktop_app.components import DialogHeader
from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
from src.desktop_app.dialogs.learning_conference_dialog import LearningConferenceDialog
from src.tablet_app.presentation import NavigationPicker, reflow_actions, touch_targets


def _replace_sidebar(screen, buttons, title):
    layout = screen.layout()
    sidebar = layout.itemAt(0).widget()
    picker = NavigationPicker(buttons, title, screen)
    sidebar.hide()
    layout.setDirection(QBoxLayout.Direction.TopToBottom)
    layout.setContentsMargins(12, 8, 12, 0)
    layout.setSpacing(8)
    layout.insertWidget(0, picker)
    return picker


def _relax_content(root):
    """Wrap text instead of letting desktop titles force horizontal clipping."""
    for header in root.findChildren(DialogHeader):
        if header.property('tabletHeaderRows') or not header.actions_layout.count():
            continue
        layout = header.layout()
        icon = layout.takeAt(0)
        heading = layout.takeAt(0)
        top = QHBoxLayout()
        top.addItem(icon)
        top.addItem(heading)
        top.setStretch(1, 1)
        layout.setDirection(QBoxLayout.Direction.TopToBottom)
        layout.insertLayout(0, top)
        header.setProperty('tabletHeaderRows', True)
    for label in root.findChildren(QLabel):
        if not label.pixmap() or label.pixmap().isNull():
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            policy.setHeightForWidth(True)
            label.setSizePolicy(policy)
    touch_targets(root)


class TabletLearningReportDialog(LearningReportDialog):
    def _preview_screen(self):
        screen = super()._preview_screen()
        tools = screen.layout().itemAt(0).widget()
        tools.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        return screen

    def _editor_screen(self):
        screen = super()._editor_screen()
        self.tablet_writer_picker = _replace_sidebar(screen, self.navigation_group.buttons(), 'Schreibbereich wählen')
        _relax_content(screen)
        return screen

    def _refresh_editor_subject_navigation(self):
        super()._refresh_editor_subject_navigation()
        if hasattr(self, 'tablet_writer_picker'):
            self.tablet_writer_picker.refresh(self.navigation_group.buttons())

    def _evidence_screen(self):
        screen = super()._evidence_screen()
        self.tablet_evidence_picker = _replace_sidebar(screen, self.evidence_navigation_group.buttons(), 'Fach für Belege wählen')
        _relax_content(screen)
        return screen

    def _ensure_workspace_built(self, key):
        super()._ensure_workspace_built(key)
        if key in self.workspace_pages:
            _relax_content(self.workspace_pages[key])
            if key == 'preview':
                tools = self.workspace_pages[key].layout().itemAt(0).widget()
                for label in tools.findChildren(QLabel):
                    policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                    policy.setHeightForWidth(True)
                    label.setSizePolicy(policy)

    def _ensure_editor_subject_built(self, *args, **kwargs):
        result = super()._ensure_editor_subject_built(*args, **kwargs)
        _relax_content(self.editor_stack)
        return result

    def _ensure_evidence_subject_built(self, index):
        super()._ensure_evidence_subject_built(index)
        _relax_content(self.evidence_stack)

    def _page_canvas(self):
        content, layout = super()._page_canvas()
        layout.setContentsMargins(16, 16, 16, 24)
        return content, layout

    def _paper_page(self, kicker):
        page, layout = super()._paper_page(kicker)
        page.setMinimumWidth(0)
        page.setMaximumWidth(820)
        page.setMinimumHeight(0)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.setContentsMargins(22, 24, 22, 24)
        return page, layout

    def _subject_preview_section(self, subject, page):
        section = super()._subject_preview_section(subject, page)
        section.setMinimumWidth(0)
        section.setMaximumWidth(820)
        section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        return section

    def update_preview(self):
        result = super().update_preview()
        if hasattr(self, 'preview_container'):
            _relax_content(self.preview_container)
            self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.preview_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
            self.preview_layout.setContentsMargins(16, 16, 16, 24)
            for index in range(self.preview_layout.count()):
                widget = self.preview_layout.itemAt(index).widget()
                if widget is not None:
                    self.preview_layout.setAlignment(widget, Qt.AlignmentFlag.AlignTop)
        return result

    def _action_bar(self):
        bar = super()._action_bar()
        reflow_actions(bar)
        return bar


class TabletLearningConferenceDialog(LearningConferenceDialog):
    def _refresh_ui_state(self):
        super()._refresh_ui_state()
        if hasattr(self, 'tablet_phase_picker'):
            self.tablet_phase_picker.refresh(self.phase_navigation._group.buttons())

    def _context_header(self):
        card = super()._context_header()
        meta = card.layout().itemAt(1).layout()
        labels = []
        while meta.count():
            item = meta.takeAt(0)
            if item.widget():
                labels.append(item.widget())
        grid = QGridLayout()
        for index, label in enumerate(labels):
            grid.addWidget(label, index // 3, index % 3)
        meta.addLayout(grid)
        return card

    def _build(self):
        super()._build()
        workspace = self.findChild(QFrame, 'LearningConferenceWorkspace')
        self.tablet_phase_picker = _replace_sidebar(workspace, self.phase_navigation._group.buttons(), 'Gesprächsbereich wählen')
        _relax_content(self)

    def _ensure_phase_built(self, key):
        super()._ensure_phase_built(key)
        _relax_content(self.phase_pages[key])

    def _action_bar(self):
        bar = super()._action_bar()
        reflow_actions(bar)
        return bar


def install_tablet_message_port():
    """Route static Qt messages through the owning tablet window in this process."""
    originals = {}
    for name, icon in (
        ('warning', QMessageBox.Icon.Warning), ('information', QMessageBox.Icon.Information),
        ('critical', QMessageBox.Icon.Critical), ('question', QMessageBox.Icon.Question),
    ):
        original = getattr(QMessageBox, name)
        originals[name] = original
        def message(parent, title, text, buttons=(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) if name == 'question' else QMessageBox.StandardButton.Ok,
                    defaultButton=QMessageBox.StandardButton.NoButton, *, _original=original, _icon=icon):
            owner = parent.window() if parent is not None else None
            presenter = getattr(owner, '_exec_dialog', None)
            if not callable(presenter):
                return _original(parent, title, text, buttons, defaultButton)
            dialog = QMessageBox(parent)
            dialog.setWindowTitle(title)
            dialog.setText(text)
            dialog.setIcon(_icon)
            dialog.setStandardButtons(buttons)
            dialog.setDefaultButton(defaultButton)
            presenter(dialog)
            return dialog.standardButton(dialog.clickedButton())
        setattr(QMessageBox, name, message)

    return originals
