"""Tablet runtime preserves real app contracts and rejects foreign/partial roots."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import pytest
from src.core.final_v4_schema import FinalV4SchemaInitializer
from src.tablet_app.runtime import TabletRuntime


@pytest.fixture
def template(tmp_path):
    path=tmp_path/'template.sqlite'
    with closing(sqlite3.connect(path)) as db:
        FinalV4SchemaInitializer.initialize_connection(db)
    return path,hashlib.sha256(path.read_bytes()).hexdigest()


def test_existing_tablet_database_not_replaced_on_update(tmp_path,template):
    source,digest=template
    runtime=TabletRuntime((tmp_path/'tablet').resolve(),source,digest)
    with closing(sqlite3.connect(runtime.database_path)) as db:
        db.execute("INSERT INTO groups VALUES ('GRP-000001','Eigene Testgruppe',0,1)");db.commit()
    before=runtime.database_path.read_bytes()
    reopened=TabletRuntime(runtime.root,source,'different-new-template-hash')
    assert reopened.database_path.read_bytes()==before


def test_partial_foreign_and_symlink_roots_fail_without_writes(tmp_path,template):
    source,digest=template
    root=tmp_path/'foreign';root.mkdir();(root/'sentinel').write_bytes(b'untouched')
    with pytest.raises(ValueError):TabletRuntime(root.resolve(),source,digest)
    assert list(root.iterdir())==[root/'sentinel']
    runtime=TabletRuntime((tmp_path/'tablet').resolve(),source,digest)
    runtime.database_path.unlink()
    with pytest.raises(ValueError):TabletRuntime(runtime.root,source,digest)
    assert not runtime.database_path.exists()
    link=tmp_path/'link';link.symlink_to(root,target_is_directory=True)
    with pytest.raises(ValueError):TabletRuntime(link,source,digest)


def test_corrupt_template_cannot_initialize_root(tmp_path,template):
    source,digest=template
    source.write_bytes(b'changed')
    root=(tmp_path/'tablet').resolve()
    with pytest.raises(ValueError):TabletRuntime(root,source,digest)
    assert not root.exists()


def test_tablet_staging_rejects_symlink_and_checkout_without_writes(tmp_path):
    from scripts.build_ipad_app import ROOT, stage_app
    target=tmp_path/'untouched';target.mkdir()
    link=tmp_path/'link';link.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError):stage_app(link)
    assert not list(target.iterdir())
    with pytest.raises(ValueError):stage_app(ROOT)


def test_original_shell_and_guided_observation_use_same_adapter(tmp_path):
    from PySide6.QtWidgets import QApplication,QTabWidget,QDialogButtonBox
    from scripts.seed_test_data import seed_test_data
    from src.core.sqlite_store import SQLiteDatabase
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.runtime import runtime_paths
    from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
    from src.tablet_app.shell import TabletAppShell
    app=QApplication.instance() or QApplication([])
    path=tmp_path/'runtime'/'kompetenzmanager.sqlite'
    seed_test_data(path)
    adapter=StudentDesktopAdapter(database=SQLiteDatabase(path,create=False))
    shell=TabletAppShell(path,paths=runtime_paths(path.parent),student_adapter=adapter,backup_restore_available=False)
    shell.resize(820,1180);shell.show();app.processEvents()
    assert shell.adapter is adapter
    assert set(shell.screen_index)=={'dashboard','onboarding','students','profile','master_data','settings'}
    assert shell.tablet_sidebar.isHidden()
    child=adapter.list_students()[0]
    assert shell.students_screen._tablet_rows[0][1].minimumHeight() >= 44
    shell.students_screen._tablet_rows[0][1].click()
    assert shell.student_profile_screen.current_student.student_id==child.student_id
    dialog=shell._create_dialog(NewObservationDialog,adapter.get_student_profile(child.student_id),shell.curriculum_adapter,adapter,
       subject_options=adapter.list_observation_subject_options(child.student_id),
       competency_subject_groups=adapter.list_observation_competency_subject_groups(child.student_id),parent=shell)
    previous=shell.stack.currentWidget()
    shell._present_dialog_page(dialog);app.processEvents()
    assert shell.stack.currentWidget() is dialog
    assert not shell.tablet_navigation_button.isEnabled()
    tabs=dialog.findChild(QTabWidget,'TabletObservationSteps')
    assert tabs is not None and tabs.count()==3
    assert dialog._initial_focus_applied
    assert not dialog.catalog_search_input.hasFocus()
    assert not dialog.note_input.hasFocus()
    tabs.setCurrentIndex(1)
    app.processEvents()
    assert dialog.catalog_scroll.viewport().height() >= 400
    assert all(hasattr(tile, 'tablet_tap_guard') for tile in dialog.competency_catalog_tiles.values())
    key, tile = next(iter(dialog.competency_catalog_tiles.items()))
    tile._activate()
    app.processEvents()
    selector = dialog.competency_rating_widgets[key]
    assert all(button.minimumHeight() == button.maximumHeight() == 32
               for button in selector.buttons.values())
    selector.buttons['--'].click()
    app.processEvents()
    assert all(button.height() == 32 for button in selector.buttons.values())
    dialog._remove_competency_rating(key)
    # All three steps must retain a real scroll range with keyboard-sized
    # available space, while their final window is the owning tablet shell.
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtWidgets import QScroller
    shell.resize(810, 620)
    for index, scroll in enumerate(dialog.tablet_step_scrolls):
        tabs.setCurrentIndex(index)
        app.processEvents()
        assert scroll.window() is shell
        assert QScroller.hasScroller(scroll.viewport())
        maximum = scroll.verticalScrollBar().maximum()
        assert maximum > 0
        QScroller.scroller(scroll.viewport()).scrollTo(QPointF(0, maximum), 0)
        app.processEvents()
        assert scroll.verticalScrollBar().value() == maximum
        assert dialog.observation_actions.mapTo(shell.tablet_scroll.viewport(), QPoint(0, dialog.observation_actions.height())).y() <= shell.tablet_scroll.viewport().height()
    shell.resize(810, 1080)
    tabs.setCurrentIndex(0)
    app.processEvents()
    dialog.tablet_next_buttons[0].click()
    assert tabs.currentIndex()==1
    dialog.tablet_next_buttons[1].click()
    assert tabs.currentIndex()==2
    dialog.quick_observation_checkbox.setChecked(True)
    assert tabs.currentIndex()==2
    dialog.note_input.setPlainText('Ausschließlich synthetische iPad-Testnotiz')
    dialog.save_draft();app.processEvents()
    assert dialog.has_saved_observation
    assert shell.stack.currentWidget() is previous
    assert shell.tablet_navigation_button.isEnabled()
    assert any(o.note=='Ausschließlich synthetische iPad-Testnotiz' for o in adapter.list_observations_for_student(child.student_id))
    shell.close()


def test_pdf_share_failure_removes_only_its_temporary_output(tmp_path):
    from src.tablet_app.exports import TabletPdfShareService
    def unavailable(_path):
        raise RuntimeError('native share unavailable')
    service=TabletPdfShareService(share_file=unavailable,temporary_root=tmp_path)
    with pytest.raises(ValueError):service.share_payload(b'invalid','Test')
    with pytest.raises(RuntimeError):service.share_payload(b'%PDF-1.4\n', 'Test / Name')
    assert list(service.temporary_root.iterdir())==[]
    other=tmp_path/'unrelated.pdf';other.write_bytes(b'keep')
    assert other.read_bytes()==b'keep'


def test_tablet_competency_pdf_still_rejects_incomplete_status(tmp_path):
    from src.tablet_app.exports import TabletPdfShareService
    from src.desktop_app.view_models.competency_pdf import CompetencyPdfModel,CompetencyPdfSubject,CompetencyPdfRow
    output=CompetencyPdfModel('Testkind','2026/27',(CompetencyPdfSubject('Deutsch','standard',(CompetencyPdfRow('Test','', '', '', 'CMP-1'),)),))
    consumed=[]
    service=TabletPdfShareService(share_file=consumed.append,temporary_root=tmp_path)
    with pytest.raises(ValueError):service.competency_pdf(output)
    assert not consumed


def test_tablet_report_and_conference_keep_original_selection_and_save_commands(tmp_path):
    from PySide6.QtWidgets import QApplication
    from scripts.seed_test_data import seed_test_data
    from src.core.sqlite_store import SQLiteDatabase
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.runtime import runtime_paths
    from src.desktop_app.dialogs.learning_report_dialog import LearningReportDialog
    from src.desktop_app.dialogs.learning_conference_dialog import LearningConferenceDialog
    from src.tablet_app.shell import TabletAppShell
    app=QApplication.instance() or QApplication([])
    path=tmp_path/'runtime'/'kompetenzmanager.sqlite';seed_test_data(path)
    adapter=StudentDesktopAdapter(database=SQLiteDatabase(path,create=False))
    shell=TabletAppShell(path,paths=runtime_paths(path.parent),student_adapter=adapter,backup_restore_available=False)
    shell.resize(820,1180);shell.show();app.processEvents()
    student=next(item for item in adapter.list_students() if adapter.list_learning_report_drafts_for_student(item.student_id))
    saved=adapter.list_learning_report_drafts_for_student(student.student_id)[0]
    preparation=adapter.learning_report_preparation_for_student(student.student_id,period_end=saved.period_end,retained_competency_ids=saved.competency_ids)
    report=shell._create_dialog(LearningReportDialog,preparation,shell,saved)
    shell._present_dialog_page(report);app.processEvents()
    report.tablet_writer_picker.setCurrentIndex(min(1, report.tablet_writer_picker.count()-1))
    assert report.navigation_group.checkedButton() is report.tablet_writer_picker._buttons[report.tablet_writer_picker.currentIndex()]
    report.show_workspace('evidence');app.processEvents()
    report.tablet_evidence_picker.setCurrentIndex(1)
    assert report.evidence_navigation_group.checkedButton() is report.tablet_evidence_picker._buttons[1]
    report.show_workspace('writing');report._set_editor_section(0)
    report.overall_input.setPlainText('Synthetischer Tabletbericht mit unverändertem Speichervertrag.')
    report.save_requested.connect(lambda draft: report.apply_saved_draft(adapter.save_learning_report_draft(draft)))
    report.save_button.click();app.processEvents()
    persisted=adapter.load_learning_report_draft(report.report_draft_view_model().report_draft_id)
    assert persisted.overall_text=='Synthetischer Tabletbericht mit unverändertem Speichervertrag.'
    report.show_workspace('preview');app.processEvents()
    preview_page=report.preview_layout.itemAt(0).widget()
    assert preview_page.width() >= 600
    assert preview_page.width() <= report.preview_container.width()
    report.reject();app.processEvents()
    conference=shell._create_dialog(LearningConferenceDialog,adapter.learning_conference_preparation_for_student(student.student_id),shell)
    shell._present_dialog_page(conference);app.processEvents()
    # Reserve the screen area occupied by an iPad keyboard. The footer must
    # remain inside the viewport instead of inheriting another page's minimum.
    shell.tablet_root_layout.setContentsMargins(8,8,8,340)
    app.processEvents()
    from PySide6.QtCore import QPoint
    footer_bottom=conference.save_button.mapTo(shell.tablet_scroll.viewport(),QPoint(0,conference.save_button.height())).y()
    assert footer_bottom <= shell.tablet_scroll.viewport().height()
    shell.tablet_root_layout.setContentsMargins(8,8,8,8)
    app.processEvents()
    for index in range(conference.tablet_phase_picker.count()):
        conference.tablet_phase_picker.setCurrentIndex(index);app.processEvents()
        assert conference.phase_navigation._group.checkedButton() is conference.tablet_phase_picker._buttons[index]
    conference.set_active_phase('strengths',focus=False)
    conference.text_inputs['strengths_text'].setPlainText('Nur synthetischer Testinhalt.')
    assert conference.tablet_phase_picker.currentText() == conference.phase_navigation._group.checkedButton().text().replace('\n',' ').replace('&&','&')
    conference.save_requested.connect(lambda draft: conference.apply_saved_draft(adapter.save_learning_conference_draft(draft)))
    conference.save_button.click();app.processEvents()
    assert adapter.load_learning_conference_draft(conference.draft_view_model().learning_conference_draft_id).strengths_text=='Nur synthetischer Testinhalt.'
    conference.reject();shell.close()


def test_tablet_message_choice_and_nested_page_restore(tmp_path):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout
    from scripts.seed_test_data import seed_test_data
    from src.core.sqlite_store import SQLiteDatabase
    from src.desktop_app.adapters.student_desktop_adapter import StudentDesktopAdapter
    from src.desktop_app.runtime import runtime_paths
    from src.tablet_app.shell import TabletAppShell
    from src.tablet_app.dialogs import install_tablet_message_port
    app=QApplication.instance() or QApplication([])
    path=tmp_path/'runtime'/'kompetenzmanager.sqlite';seed_test_data(path)
    shell=TabletAppShell(path,paths=runtime_paths(path.parent),student_adapter=StudentDesktopAdapter(database=SQLiteDatabase(path,create=False)),backup_restore_available=False)
    page=QDialog(shell);QVBoxLayout(page);shell.tablet_dialog_policy.adapt(page)
    shell._present_dialog_page(page)
    originals=install_tablet_message_port()
    try:
        def choose():
            message=shell.stack.currentWidget()
            assert isinstance(message,QMessageBox)
            message.button(QMessageBox.StandardButton.Cancel).click()
        QTimer.singleShot(0,choose)
        result=QMessageBox.question(page,'Testentscheidung','Keine automatische Zustimmung.',QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
        assert result==QMessageBox.StandardButton.Cancel
        assert shell.stack.currentWidget() is page
        assert not shell.tablet_navigation_button.isEnabled()
    finally:
        for key,value in originals.items():setattr(QMessageBox,key,value)
        page.reject();shell.close()


def test_empty_tablet_scroll_surface_renders_light_with_dark_system_palette():
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QApplication, QScrollArea, QWidget
    from src.desktop_app.theme import COLOR_BACKGROUND, apply_app_theme
    from src.tablet_app.presentation import apply_tablet_theme, configure_tablet_scroll_area
    app = QApplication.instance() or QApplication([])
    original_palette, original_style = app.palette(), app.styleSheet()
    scroll = None
    try:
        dark = QPalette()
        dark.setColor(QPalette.ColorRole.Window, QColor('black'))
        dark.setColor(QPalette.ColorRole.Base, QColor('black'))
        app.setPalette(dark)
        apply_app_theme(app)
        apply_tablet_theme(app)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(QWidget())
        configure_tablet_scroll_area(scroll)
        scroll.resize(320, 240)
        scroll.show()
        app.processEvents()
        image = scroll.viewport().grab().toImage()
        assert image.pixelColor(image.width() // 2, image.height() // 2) == QColor(COLOR_BACKGROUND)
    finally:
        if scroll is not None:
            scroll.close()
        app.setStyleSheet(original_style)
        app.setPalette(original_palette)


def test_projection_cleanup_stops_active_swipe_without_detaching_native_window():
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QApplication, QScrollArea, QScroller, QVBoxLayout, QWidget
    from src.tablet_app.presentation import clear_tablet_layout, configure_tablet_scroll_area
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    layout = QVBoxLayout(parent)
    scroll = QScrollArea(parent)
    content = QWidget()
    content.setMinimumHeight(2000)
    scroll.setWidget(content)
    layout.addWidget(scroll)
    configure_tablet_scroll_area(scroll)
    parent.resize(320, 240)
    parent.show()
    app.processEvents()
    scroller = QScroller.scroller(scroll.viewport())
    scroller.scrollTo(QPointF(0, 1000), 500)
    assert scroller.state() != QScroller.State.Inactive
    clear_tablet_layout(layout)
    assert scroll.parentWidget() is parent
    assert scroll.isHidden()
    assert scroller.state() == QScroller.State.Inactive
    app.processEvents()
    parent.close()


@pytest.mark.parametrize('kind', ['card', 'button', 'catalog'])
def test_tablet_swipe_and_scroller_cancel_do_not_activate_but_taps_do(kind):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
    from src.desktop_app.screens.overview_screen import DashboardMatchingStudentAction
    from src.desktop_app.view_models.student_view_model import DashboardSuggestedStudentViewModel
    from src.tablet_app.presentation import touch_targets
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    layout = QVBoxLayout(parent)
    activations = []
    if kind == 'card':
        target = DashboardMatchingStudentAction(
            DashboardSuggestedStudentViewModel('STU-TEST', 'Testkind', 'Nur Testdaten'),
            lambda: activations.append('open'))
    elif kind == 'catalog':
        from src.desktop_app.dialogs.new_observation_dialog import ObservationCatalogCompetencyTile
        target = ObservationCatalogCompetencyTile('CMP-TEST', lambda: activations.append('open'), False)
    else:
        target = QPushButton('Testaktion')
        target.clicked.connect(lambda: activations.append('open'))
    layout.addWidget(target)
    touch_targets(parent)
    parent.resize(320, 160)
    parent.show()
    app.processEvents()

    def pointer(kind, x, y):
        point = QPointF(x, y)
        button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
        buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
        event = QMouseEvent(kind, point, point, button, buttons, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(target, event)

    # A drag returning to its starting point must still remain a drag.
    pointer(QEvent.Type.MouseButtonPress, 20, 20)
    pointer(QEvent.Type.MouseMove, 100, 20)
    pointer(QEvent.Type.MouseButtonRelease, 20, 20)
    assert not activations
    # QScroller sends a synthetic cancellation at INT_MIN, INT_MIN.
    pointer(QEvent.Type.MouseButtonPress, 20, 20)
    pointer(QEvent.Type.MouseButtonRelease, -2147483648, -2147483648)
    pointer(QEvent.Type.MouseButtonRelease, 20, 20)
    assert not activations
    pointer(QEvent.Type.MouseButtonPress, 20, 20)
    pointer(QEvent.Type.MouseButtonRelease, 20, 20)
    assert activations == ['open']
    parent.close()


def test_one_pointer_drag_moves_tablet_scroll_area():
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QScrollArea, QWidget
    from src.tablet_app.presentation import configure_tablet_scroll_area
    app = QApplication.instance() or QApplication([])
    scroll = QScrollArea()
    content = QWidget()
    content.setMinimumHeight(2000)
    scroll.setWidget(content)
    scroll.resize(320, 500)
    scroll.show()
    configure_tablet_scroll_area(scroll)
    app.processEvents()
    viewport = scroll.viewport()
    # Real press/move/release delivery, rather than calling scrollTo directly.
    for kind, y in ((QEvent.Type.MouseButtonPress, 400),
                    (QEvent.Type.MouseMove, 350), (QEvent.Type.MouseMove, 250),
                    (QEvent.Type.MouseMove, 150), (QEvent.Type.MouseButtonRelease, 150)):
        point = QPointF(100, y)
        button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
        buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
        app.sendEvent(viewport, QMouseEvent(kind, point, QPointF(viewport.mapToGlobal(point.toPoint())),
                      button, buttons, Qt.KeyboardModifier.NoModifier))
        QTest.qWait(30)
    assert scroll.verticalScrollBar().value() > 150
    scroll.close()


def test_tablet_pdf_completion_reaches_every_subject_without_arrow_tabs():
    from PySide6.QtWidgets import QApplication
    from src.desktop_app.view_models.competency_pdf import CompetencyPdfModel, CompetencyPdfSubject, CompetencyPdfRow
    from src.tablet_app.dialogs import TabletCompetencyPdfCompletionDialog
    app = QApplication.instance() or QApplication([])
    model = CompetencyPdfModel('Testkind', '2026/27', tuple(
        CompetencyPdfSubject(f'Langes Testfach {index}', profile,
            (CompetencyPdfRow('Synthetische Kompetenz', '', '', '', f'CMP-{index}'),))
        for index, profile in enumerate(['standard', 'social', 'sport'] * 4)))
    dialog = TabletCompetencyPdfCompletionDialog(model)
    assert dialog.subject_tabs.tabBar().isHidden()
    assert dialog.subject_picker.count() == 12
    assert not dialog.save_button.isEnabled()
    for index in range(12):
        dialog.subject_picker.setCurrentIndex(index)
        assert dialog.subject_tabs.currentIndex() == index
        choice = dialog.rating_inputs[f'CMP-{index}']
        assert not choice.currentData()
        assert [choice.itemData(i) for i in range(1, 5)] == ['--', '-', '+', '++']
        assert choice.itemText(1) == 'Erste Erfahrungen'
        choice.setCurrentIndex(2)
    assert dialog.save_button.isEnabled()
    assert set(dialog.selections().values()) == {'-'}
    dialog.reject()
    dialog.deleteLater()
    app.processEvents()


@pytest.mark.parametrize('width', [460, 940])
def test_observation_rating_buttons_keep_size_when_selection_changes(width):
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
    from src.desktop_app.dialogs.new_observation_dialog import ObservationRatingSelector
    from src.tablet_app.presentation import touch_targets
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    layout = QVBoxLayout(parent)
    selector = ObservationRatingSelector('')
    layout.addWidget(selector)
    touch_targets(parent)
    parent.resize(width, 120)
    parent.show()
    app.processEvents()
    before = {token: (button.minimumHeight(), button.size()) for token, button in selector.buttons.items()}
    for token, button in selector.buttons.items():
        button.click()
        app.processEvents()
        assert selector.currentData() == token
        assert {key: (item.minimumHeight(), item.size()) for key, item in selector.buttons.items()} == before
        assert all(item.height() == 32 for item in selector.buttons.values())
    parent.close()
