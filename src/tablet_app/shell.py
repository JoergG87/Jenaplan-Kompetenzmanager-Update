"""Tablet presentation of the original AppShell, without a second business model."""
from PySide6.QtCore import QEvent, QEventLoop, QObject, Qt, QTimer
from shiboken6 import isValid
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QBoxLayout, QComboBox, QDialog, QFileDialog, QGridLayout, QMenu,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QScroller, QVBoxLayout, QWidget, QSplitter, QTabWidget, QSizePolicy, QDialogButtonBox, QLayout,
)
from src.desktop_app.components import configure_button, PageHeader
from src.desktop_app.shell import AppShell


class TabletDialogPolicy(QObject):
    """Keep original dialog fields reachable inside the iPad screen."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show and isinstance(obj, QDialog):
            self.adapt(obj)
        return False

    def adapt(self, obj):
        if isinstance(obj, QDialog):
            if not isinstance(obj, QFileDialog) and not obj.property('tabletAdapted'):
                obj.setProperty('tabletAdapted', True)
                splitter = obj.findChild(QSplitter, 'ObservationThreeZoneWorkspace')
                if splitter is not None:
                    self._observation_steps(obj, splitter)
                elif hasattr(obj, 'subject_picker'):
                    pass  # Existing subject pages own scrolling and fixed actions.
                elif hasattr(obj, 'mode_stack') or hasattr(obj, 'phase_stack'):
                    stack = getattr(obj, 'mode_stack', None) or obj.phase_stack
                    stack.setMinimumSize(0, 0)
                    stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
                else:
                    old = obj.layout()
                    if old is not None:
                        footer = obj.findChild(QDialogButtonBox)
                        if footer is not None:
                            old.removeWidget(footer)
                        body = QWidget()
                        body.setLayout(old)
                        old.setAlignment(Qt.AlignmentFlag.AlignTop)
                        body.setMinimumWidth(0)
                        body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                        scroll = QScrollArea()
                        scroll.setWidgetResizable(True)
                        scroll.setWidget(body)
                        layout = QVBoxLayout(obj)
                        layout.setContentsMargins(0, 0, 0, 0)
                        layout.addWidget(scroll, 1)
                        obj.tablet_dialog_scroll = scroll
                        if footer is not None:
                            layout.addWidget(footer)
                        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)
                obj.setMinimumSize(0, 0)
                obj.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
                obj.setMaximumSize(16777215, 16777215)
                obj.resize(obj.screen().availableGeometry().size())
            from src.tablet_app.presentation import touch_targets
            touch_targets(obj)

    def _observation_steps(self, dialog, splitter):
        tabs = QTabWidget()
        tabs.setObjectName('TabletObservationSteps')
        tabs.setAccessibleName('Beobachtung: Kontext, Kompetenzen und Notiz')
        tabs.setMinimumSize(0, 0)
        tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        dialog.tablet_steps = tabs
        dialog.tablet_next_buttons = []
        dialog.tablet_step_scrolls = []
        zones = [splitter.widget(i) for i in range(splitter.count())]
        for zone, title in zip(zones, ('1 · Kontext', '2 · Kompetenzen', '3 · Notiz')):
            zone.setMinimumWidth(0)
            zone.setMaximumWidth(16777215)
            zone.layout().setHorizontalSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
            zone.layout().setVerticalSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(zone)
            scroll.setMinimumSize(0, 0)
            tabs.addTab(scroll, title)
            dialog.tablet_step_scrolls.append(scroll)
        # Preserve the original buttons and their connected application commands.
        footer = QHBoxLayout()
        footer.addWidget(dialog.save_and_continue_button)
        footer.addStretch()
        footer.addWidget(dialog.observation_actions)
        layout = dialog.layout()
        layout.replaceWidget(splitter, tabs)
        splitter.deleteLater()
        layout.addLayout(footer)
        for index in (0, 1):
            next_button = QPushButton('Weiter zu Kompetenzen' if index == 0 else 'Weiter zur Notiz')
            configure_button(next_button, 'secondary', next_button.text())
            next_button.clicked.connect(lambda checked=False, target=index + 1: tabs.setCurrentIndex(target))
            next_button.setMinimumHeight(44)
            zones[index].layout().addWidget(next_button)
            dialog.tablet_next_buttons.append(next_button)
        tabs.tabBar().setMinimumHeight(44)
        dialog.selected_scroll.setMinimumHeight(70)
        dialog.selected_scroll.setMaximumHeight(440)
        dialog.catalog_scroll.setMinimumHeight(420)
        if dialog.competency_rating_entries:
            dialog._update_selection_summary()
        dialog.note_input.setMinimumHeight(160)
        dialog.quick_observation_checkbox.toggled.connect(
            lambda checked: tabs.setCurrentIndex(2) if checked else None
        )


class TabletAppShell(AppShell):
    """Retains every existing screen, ViewModel, signal and application command."""
    def __init__(self, *args, **kwargs):
        from src.desktop_app.screens.students_workspace import StudentsWorkspace
        from src.tablet_app.screens import TabletStudentsScreen, TabletStudentProfileScreen, TabletOverviewScreen
        kwargs['dashboard_screen_factory'] = TabletOverviewScreen
        kwargs['students_workspace_factory'] = lambda: StudentsWorkspace(students_screen=TabletStudentsScreen())
        kwargs['student_profile_screen_factory'] = TabletStudentProfileScreen
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Jenaplan Kompetenzmanager · iPad-Test')
        self.setMinimumSize(0, 0)
        original = self.takeCentralWidget()
        self.tablet_sidebar = original.findChild(QWidget, 'AppSidebar')
        self.tablet_body = original
        original.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.stack.setMinimumSize(0, 0)
        self.stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        outer = QWidget()
        outer.setObjectName('AppRoot')
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QHBoxLayout()
        self.tablet_navigation_button = QPushButton('Navigation')
        configure_button(self.tablet_navigation_button, 'secondary', 'Navigation ein- oder ausblenden')
        menu = QMenu(self.tablet_navigation_button)
        self.tablet_navigation_actions = []
        menu.setStyleSheet('QMenu::item { padding: 14px 24px; }')
        for row in range(self.navigation.count()):
            item = self.navigation.item(row)
            if not item.data(Qt.ItemDataRole.UserRole):
                continue
            action = menu.addAction(item.icon(), item.text())
            action.triggered.connect(lambda checked=False, index=row: self._navigate_tablet(index))
            self.tablet_navigation_actions.append(action)
        self.tablet_navigation_button.setMenu(menu)
        header.addWidget(self.tablet_navigation_button)
        notice = QLabel('iPad-Test · ausschließlich erfundene Daten')
        notice.setWordWrap(True)
        header.addWidget(notice, 1)
        layout.addLayout(header)
        self.tablet_scroll = QScrollArea()
        self.tablet_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        # Hidden desktop pages contribute a height-for-width larger than the
        # viewport. Fit the shell explicitly; each page owns its scrolling.
        self.tablet_scroll.setWidgetResizable(False)
        self.tablet_scroll.setProperty('tabletViewportOnly', True)
        self.tablet_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tablet_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tablet_scroll.setWidget(original)
        self.tablet_scroll.viewport().installEventFilter(self)
        layout.addWidget(self.tablet_scroll, 1)
        QScroller.grabGesture(self.tablet_scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        self.setCentralWidget(outer)
        self.tablet_root_layout = layout
        keyboard = QApplication.inputMethod()
        keyboard.keyboardRectangleChanged.connect(self._keyboard_space)
        keyboard.visibleChanged.connect(self._keyboard_space)
        self.lock_button.hide()
        self._disable_desktop_security()
        self.tablet_dialog_policy = TabletDialogPolicy(self)
        self.tablet_dialog_pages = []
        self._touch_targets()
        profile_header = self.student_profile_screen.profile_page_header
        actions = profile_header.actions_layout
        self.tablet_profile_actions = []
        while actions.count():
            item = actions.takeAt(0)
            if item.widget():
                self.tablet_profile_actions.append(item.widget())
        action_box = QWidget()
        self.tablet_profile_grid = QGridLayout(action_box)
        self.tablet_profile_grid.setContentsMargins(0, 0, 0, 0)
        profile_header.layout().addWidget(action_box)
        self._adapt_width()
        self.tablet_body.resize(self.tablet_scroll.viewport().size())

    def eventFilter(self, obj, event):
        if hasattr(self, 'tablet_scroll') and obj is self.tablet_scroll.viewport() and event.type() == QEvent.Type.Resize:
            self.tablet_body.resize(event.size())
        return super().eventFilter(obj, event)

    def _create_dialog(self, dialog_type, *args, **kwargs):
        from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
        from src.tablet_app.screens import TabletNewObservationDialog
        if dialog_type is NewObservationDialog:
            dialog_type = TabletNewObservationDialog
        from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
        from src.desktop_app.dialogs.learning_conference_dialog import LearningConferenceDialog
        from src.tablet_app.dialogs import TabletLearningReportDialog, TabletLearningConferenceDialog
        from src.desktop_app.dialogs.competency_pdf_completion_dialog import CompetencyPdfCompletionDialog
        from src.tablet_app.dialogs import TabletCompetencyPdfCompletionDialog
        if dialog_type is LearningReportDialog:
            dialog_type = TabletLearningReportDialog
        elif dialog_type is LearningConferenceDialog:
            dialog_type = TabletLearningConferenceDialog
        elif dialog_type is CompetencyPdfCompletionDialog:
            dialog_type = TabletCompetencyPdfCompletionDialog
        dialog = super()._create_dialog(dialog_type, *args, **kwargs)
        if hasattr(self, 'tablet_dialog_policy'):
            self.tablet_dialog_policy.adapt(dialog)
            dialog.installEventFilter(self.tablet_dialog_policy)
        return dialog

    def _present_dialog_page(self, dialog):
        previous = self.stack.currentWidget()
        self.tablet_dialog_pages.append(dialog)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        dialog.setModal(False)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setWindowFlags(Qt.WindowType.Widget)
        dialog.setParent(self.stack)
        dialog.setMinimumSize(0, 0)
        dialog.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.stack.addWidget(dialog)
        self.stack.setCurrentWidget(dialog)
        self.tablet_navigation_button.setEnabled(False)
        self.navigation.setEnabled(False)
        self.tablet_sidebar.hide()
        if not dialog.property('tabletBackAdded'):
            back = QPushButton('← Zurück')
            configure_button(back, 'quiet', 'Eingabe schließen')
            back.setMinimumHeight(44)
            back.clicked.connect(dialog.reject)
            dialog.layout().insertWidget(0, back)
            dialog.setProperty('tabletBackAdded', True)
            dialog.tablet_back_button = back

        def finished(result):
            if self.stack.currentWidget() is dialog and isValid(previous):
                self.stack.setCurrentWidget(previous)
            self.stack.removeWidget(dialog)
            self.tablet_dialog_pages = [page for page in self.tablet_dialog_pages if page is not dialog]
            self.tablet_navigation_button.setEnabled(not self.tablet_dialog_pages)
            self.navigation.setEnabled(not self.tablet_dialog_pages)
            self._adapt_width()
        dialog.finished.connect(finished)
        dialog.show()
        self._adapt_width()
        from src.tablet_app.presentation import rebind_tablet_scroll_gestures
        rebind_tablet_scroll_gestures(dialog)

    def _exec_dialog(self, dialog):
        self.tablet_dialog_policy.adapt(dialog)
        dialog.installEventFilter(self.tablet_dialog_policy)
        result = [int(QDialog.DialogCode.Rejected)]
        loop = QEventLoop()
        def done(code):
            result[0] = code
            loop.quit()
        dialog.finished.connect(done)
        self._present_dialog_page(dialog)
        loop.exec()
        dialog.finished.disconnect(done)
        QTimer.singleShot(0, dialog.deleteLater)
        return result[0]

    def _exec_workspace(self, dialog):
        return self._exec_dialog(dialog)

    def _open_dialog(self, dialog):
        self._present_dialog_page(dialog)
        dialog.finished.connect(dialog.deleteLater)

    def _open_workspace(self, dialog):
        self._open_dialog(dialog)

    def refresh_dashboard(self, *args, **kwargs):
        super().refresh_dashboard(*args, **kwargs)
        if hasattr(self, 'tablet_sidebar'):
            self._adapt_width()
            self._touch_targets()

    def show_student_profile(self, student_id):
        super().show_student_profile(student_id)
        if hasattr(self, 'tablet_sidebar'):
            self._adapt_width()
            self._touch_targets()

    def refresh_students(self):
        super().refresh_students()
        self._touch_targets()
        if hasattr(self, 'students_screen'):
            table = self.students_screen.table
            for row in range(table.rowCount()):
                table.setRowHeight(row, 64)

    def _disable_desktop_security(self):
        for key in ('security', 'updates', 'backup_restore'):
            card = self.settings_screen.settings_cards.get(key)
            if card is not None:
                card.setEnabled(False)
                card.status.setText('Im iPad-Test noch nicht verfügbar')
        self.settings_screen.storage_security_notice.setText(
            'Dieser getrennte Testbestand ist nicht zusätzlich verschlüsselt. Nur erfundene Daten verwenden.'
        )

    def _touch_targets(self):
        from src.tablet_app.presentation import touch_targets
        touch_targets(self)

    def _keyboard_space(self):
        keyboard = QApplication.inputMethod()
        rectangle = keyboard.keyboardRectangle()
        bottom = max(0, int(self.height() - rectangle.top())) if keyboard.isVisible() and not rectangle.isEmpty() else 0
        self.tablet_root_layout.setContentsMargins(8, 8, 8, min(bottom, self.height() // 2) + 8)

    def _navigate_tablet(self, row):
        item = self.navigation.item(row)
        self._show_navigation_item(item)
        self._select_navigation(str(item.data(Qt.ItemDataRole.UserRole)))

    def _adapt_width(self):
        if not hasattr(self, 'tablet_sidebar'):
            return
        narrow = self.width() < 1050
        active = bool(getattr(self, 'tablet_dialog_pages', []))
        self.tablet_sidebar.setVisible(not narrow and not active)
        self.tablet_navigation_button.setVisible(narrow and not active)
        self.tablet_body.setMinimumSize(0, 0)
        self.tablet_body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        for header in self.findChildren(PageHeader):
            header.layout().setDirection(QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight)
        for i, widget in enumerate(self.tablet_profile_actions):
            self.tablet_profile_grid.addWidget(widget, i // 2 if narrow else 0, i % 2 if narrow else i)
        if hasattr(self.dashboard_screen, 'hero_layout'):
            self.dashboard_screen.hero_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self.dashboard_screen.hero_layout.setStretch(0, 3 if narrow else 1)
            self.dashboard_screen.hero_layout.setStretch(1, 2 if narrow else 1)
            if self.dashboard_screen.hero_layout.count() > 1:
                visual = self.dashboard_screen.hero_layout.itemAt(1).widget()
                if visual is not None:
                    self.dashboard_screen.hero_layout.setAlignment(visual, Qt.AlignmentFlag.AlignVCenter)
            self.dashboard_screen.today_layout.setDirection(QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adapt_width()

    def export_competency_overview_pdf(self, student_id):
        from src.application.competency_pdf_completion import pending_competency_pdf_rows
        from src.desktop_app.dialogs.competency_pdf_completion_dialog import CompetencyPdfCompletionDialog
        from src.tablet_app.exports import TabletPdfShareService
        try:
            model = self.adapter.competency_pdf_for_student(student_id)
            if pending_competency_pdf_rows(model):
                dialog = self._create_dialog(CompetencyPdfCompletionDialog, model, self)
                if self._exec_dialog(dialog) != QDialog.DialogCode.Accepted:
                    return
                self.adapter.complete_competency_pdf(student_id, model, dialog.selections())
                self.show_student_profile(student_id)
            with self.maintenance_gate.begin_writer():
                model = self.adapter.competency_pdf_for_student(student_id)
                TabletPdfShareService().competency_pdf(model)
        except Exception:
            QMessageBox.warning(self, 'PDF nicht ausgegeben', 'Die Ausgabe konnte nicht vorbereitet werden. Bitte prüfe die Entwicklungsstände.')
            return
        self.status_label.show_message('PDF zum Teilen geöffnet', tone='success', duration_ms=7000)

    def export_learning_report_pdf(self, output_model, *, parent=None):
        from src.tablet_app.exports import TabletPdfShareService
        try:
            TabletPdfShareService().report_pdf(output_model)
        except Exception:
            QMessageBox.warning(parent or self, 'PDF nicht ausgegeben', 'Die Berichtsausgabe konnte nicht vorbereitet werden.')
            return
        self.status_label.show_message('PDF zum Teilen geöffnet', tone='success', duration_ms=7000)
