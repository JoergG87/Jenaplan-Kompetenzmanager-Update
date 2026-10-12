"""Touch-oriented variants of the existing projections; no business logic."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from src.desktop_app.components import AppCard, configure_button
from src.desktop_app.screens.overview_screen import OverviewScreen
from src.desktop_app.screens.students_screen import StudentsScreen
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen


class TabletStudentsScreen(StudentsScreen):
    """A compact card list replaces the desktop action table on tablets."""
    def __init__(self):
        self._tablet_rows = []
        self.tablet_list = QScrollArea()
        self.tablet_list.setWidgetResizable(True)
        content = QWidget()
        self.tablet_cards = QVBoxLayout(content)
        self.tablet_cards.setContentsMargins(0, 0, 0, 0)
        self.tablet_cards.setSpacing(8)
        self.tablet_cards.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tablet_list.setWidget(content)
        super().__init__(show_header=False)
        self.layout().addWidget(self.tablet_list, 1)
        self.table.hide()

    def _render_students(self, students):
        self.table.hide()
        self._update_empty_state(students)
        while self.tablet_cards.count():
            item = self.tablet_cards.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._tablet_rows = []
        for student in students:
            card = AppCard('soft')
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(3)
            actions = QHBoxLayout()
            profile = QPushButton(student.display_name + ' · ' + student.course_name)
            configure_button(profile, 'quiet', 'Profil von ' + student.display_name + ' öffnen')
            profile.setMinimumHeight(44)
            profile.setStyleSheet('text-align: left; font-size: 16px; font-weight: 600;')
            profile.clicked.connect(lambda checked=False, key=student.student_id: self.student_selected.emit(key))
            actions.addWidget(profile, 1)
            observe = QPushButton('Beobachten')
            configure_button(observe, 'secondary', 'Neue Beobachtung für ' + student.display_name)
            observe.setMinimumHeight(44)
            observe.clicked.connect(lambda checked=False, key=student.student_id: self.observation_requested.emit(key))
            actions.addWidget(observe)
            layout.addLayout(actions)
            status = QLabel(student.documentation_status.list_label)
            status.setWordWrap(True)
            layout.addWidget(status)
            self.tablet_cards.addWidget(card)
            # Keep Python signal wrappers alive across native ownership transfer.
            self._tablet_rows.append((card, profile, observe, status))
        self.tablet_list.setVisible(bool(students))


class TabletStudentProfileScreen(StudentProfileScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from src.tablet_app.presentation import reflow_filter_bar
        reflow_filter_bar(self.competency_filter_bar)
        reflow_filter_bar(self.observation_filter_bar)

    def apply_competency_cockpit_filters(self, *args, **kwargs):
        super().apply_competency_cockpit_filters(*args, **kwargs)
        from src.tablet_app.presentation import touch_targets
        touch_targets(self.competency_cockpit_container)

    def apply_observation_filters(self, *args, **kwargs):
        super().apply_observation_filters(*args, **kwargs)
        from src.tablet_app.presentation import touch_targets
        touch_targets(self.observations_container)

    def _clear_layout(self, layout):
        # Don't detach widgets into temporary iOS windows or force an immediate
        # native event-loop flush while a profile projection is being rebuilt.
        from src.tablet_app.presentation import clear_tablet_layout
        clear_tablet_layout(layout)


from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog


class TabletNewObservationDialog(NewObservationDialog):
    def _update_selection_summary(self):
        super()._update_selection_summary()
        if self.competency_rating_entries:
            self.selected_scroll.setMinimumHeight(max(260, self.selected_scroll.minimumHeight()))

    def _refresh_competencies(self, *args, **kwargs):
        super()._refresh_competencies(*args, **kwargs)
        from src.tablet_app.presentation import touch_targets
        touch_targets(self.competency_zone)

    def _focus_initial_input(self):
        if not hasattr(self, 'tablet_steps'):
            return super()._focus_initial_input()
        if not self._initial_focus_applied and self.isVisible():
            self._initial_focus_applied = True
            self.tablet_steps.tabBar().setFocus(Qt.FocusReason.OtherFocusReason)

    def _add_competency_rating_row(self, *args, **kwargs):
        super()._add_competency_rating_row(*args, **kwargs)
        from src.desktop_app.components import RatingBadgeButton
        for card in self.competency_rating_rows.values():
            for button in card.findChildren(QPushButton):
                if isinstance(button, RatingBadgeButton):
                    continue
                button.setMaximumHeight(16777215)
                button.setMinimumHeight(44)
            from src.tablet_app.presentation import touch_targets
            touch_targets(card)


class TabletOverviewScreen(OverviewScreen):
    """Keep the visual day schedule beside the current lesson on iPad."""
    @staticmethod
    def _clear_layout(layout):
        from src.tablet_app.presentation import clear_tablet_layout
        clear_tablet_layout(layout)

    def set_dashboard(self, *args, **kwargs):
        from src.tablet_app.presentation import stop_tablet_scrollers, touch_targets
        stop_tablet_scrollers(self)
        super().set_dashboard(*args, **kwargs)
        touch_targets(self)

    def _render_heatmap(self, *args, **kwargs):
        super()._render_heatmap(*args, **kwargs)
        item = self.heatmap_layout.itemAt(self.heatmap_layout.count() - 1)
        scroll = item.widget() if item is not None else None
        if isinstance(scroll, QScrollArea):
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            height = scroll.widget().minimumSizeHint().height() + scroll.horizontalScrollBar().sizeHint().height() + 4
            scroll.setMinimumHeight(min(280, height))

    def _hero_visual(self, *args, **kwargs):
        visual = super()._hero_visual(*args, **kwargs)
        visual.setMaximumWidth(280 if self.width() < 1050 else 16777215)
        self.tablet_hero_visual = visual
        if self._hero_vignette is not None and self.hero_layout.count():
            content = self.hero_layout.itemAt(0).widget()
            if content is not None:
                body = QWidget()
                body.setLayout(content.layout())
                layout = QHBoxLayout(content)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(8)
                layout.addWidget(body, 1)
                self._hero_vignette.setParent(content)
                layout.addWidget(self._hero_vignette, 0, Qt.AlignmentFlag.AlignVCenter)
                self._hero_vignette.show()
        return visual

    def _update_hero_vignette_visibility(self):
        super()._update_hero_vignette_visibility()
        if self._hero_vignette is not None:
            self._layout_subject_vignette(self._hero_vignette, (104, 88))
            self._hero_vignette.show()
            self._hero_vignette_layout.setColumnMinimumWidth(0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'tablet_hero_visual'):
            self.tablet_hero_visual.setMaximumWidth(280 if self.width() < 1050 else 16777215)
