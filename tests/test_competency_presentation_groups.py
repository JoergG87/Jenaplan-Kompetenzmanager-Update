from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionComboBox

from src.desktop_app import theme
from src.desktop_app.adapters.curriculum_desktop_adapter import (
    CurriculumDesktopAdapter,
    DOCUMENTATION_SUBJECT_PREFERRED_ORDER,
)
from src.desktop_app.dialogs.new_observation_dialog import NewObservationDialog
from src.desktop_app.screens.student_profile_screen import StudentProfileScreen
from src.desktop_app.view_models.observation_view_model import (
    COMPETENCY_PRESENTATION_GROUP_CROSS_CURRICULAR,
    COMPETENCY_PRESENTATION_GROUP_SUBJECTS,
    ObservationCompetencyRatingDraft,
    ObservationCompetencyGroupViewModel,
    ObservationCompetencyOptionViewModel,
    ObservationCompetencySubjectGroupViewModel,
    ObservationLearningAreaGroupViewModel,
    ObservationSubjectOptionViewModel,
    StudentCompetencyCockpitSubjectViewModel,
    StudentCompetencyCockpitViewModel,
    competency_presentation_group,
    rating_profile_for_competency,
)
from src.desktop_app.view_models.student_view_model import StudentDetailViewModel


CROSS_CURRICULAR_SUBJECTS = (
    "selbst_sozialkompetenz",
    "arbeits_lernkompetenz",
)
CANONICAL_TEACHING_SUBJECTS = (
    "epu",
    "deutsch",
    "mathematik",
    "kreatives_gestalten",
    "sport",
    "ethik",
    "religion",
    "musik",
    "englisch",
    "schulgarten",
)


def test_presentation_groups_preserve_canonical_source_order_without_duplicates() -> None:
    subjects = CurriculumDesktopAdapter().list_active_subjects()

    assert tuple(subject.subject_key for subject in subjects) == (
        CROSS_CURRICULAR_SUBJECTS + CANONICAL_TEACHING_SUBJECTS
    )
    assert tuple(subject.subject_key for subject in subjects) == (
        DOCUMENTATION_SUBJECT_PREFERRED_ORDER
    )
    assert len({subject.subject_key for subject in subjects}) == len(subjects)
    assert tuple(
        subject.subject_key
        for subject in subjects
        if competency_presentation_group(subject.subject_key)
        == COMPETENCY_PRESENTATION_GROUP_CROSS_CURRICULAR
    ) == CROSS_CURRICULAR_SUBJECTS
    assert tuple(
        subject.subject_key
        for subject in subjects
        if competency_presentation_group(subject.subject_key)
        == COMPETENCY_PRESENTATION_GROUP_SUBJECTS
    ) == CANONICAL_TEACHING_SUBJECTS


def test_cross_curricular_rating_profiles_keep_existing_tokens() -> None:
    social = SimpleNamespace(subject_key="selbst_sozialkompetenz")
    work_learning = SimpleNamespace(subject_key="arbeits_lernkompetenz")

    assert rating_profile_for_competency(social) == "social"
    assert rating_profile_for_competency(work_learning) == "standard"
    assert ObservationCompetencyRatingDraft.from_catalog_entry(
        SimpleNamespace(
            competency_id="CMP-100001",
            subject_key="selbst_sozialkompetenz",
            subject_display_name="Selbst- und Sozialkompetenz",
            learning_area="Miteinander",
            competency_group="Sozial",
            competency_text="Beispiel",
        ),
        "+",
    ).competency_id == "CMP-100001"
    assert ObservationCompetencyRatingDraft.from_catalog_entry(
        SimpleNamespace(
            competency_id="CMP-100009",
            subject_key="arbeits_lernkompetenz",
            subject_display_name="Arbeits-/Lernkompetenz",
            learning_area="Lernen",
            competency_group="Arbeitsweise",
            competency_text="Beispiel",
        ),
        "-",
    ).rating == "-"


def test_observation_dialog_groups_subjects_without_an_extra_click_level() -> None:
    QApplication.instance() or QApplication([])
    subject_labels = {
        subject.subject_key: subject.display_name
        for subject in CurriculumDesktopAdapter().list_active_subjects()
    }
    dialog = NewObservationDialog(
        StudentDetailViewModel("student-1", "Ada Beispiel", "A", "1", "", True),
        subject_options=tuple(
            ObservationSubjectOptionViewModel(subject_key, subject_labels[subject_key])
            for subject_key in DOCUMENTATION_SUBJECT_PREFERRED_ORDER
        ),
    )

    visible_items = tuple(
        dialog.subject_select.itemText(index)
        for index in range(dialog.subject_select.count())
    )
    selectable_ids = tuple(
        dialog.subject_select.itemData(index)
        for index in range(dialog.subject_select.count())
        if dialog.subject_select.itemData(index)
    )
    assert visible_items[:4] == (
        "Überfachliche Entwicklung",
        "Selbst- und Sozialkompetenz",
        "Arbeits-/Lernkompetenz",
        "Fächer",
    )
    assert selectable_ids == DOCUMENTATION_SUBJECT_PREFERRED_ORDER
    assert dialog.subject_select.currentData() == "selbst_sozialkompetenz"
    assert dialog.subject_select.currentText() == "Selbst- und Sozialkompetenz"
    dialog.close()


def test_observation_subject_names_fit_beside_marker_without_elision() -> None:
    app = QApplication.instance() or QApplication([])
    previous_stylesheet = app.styleSheet()
    theme.apply_app_theme(app)
    subject_labels = {
        subject.subject_key: subject.display_name
        for subject in CurriculumDesktopAdapter().list_active_subjects()
    }
    dialog = NewObservationDialog(
        StudentDetailViewModel("student-1", "Ada Beispiel", "A", "1", "", True),
        subject_options=tuple(
            ObservationSubjectOptionViewModel(subject_key, subject_labels[subject_key])
            for subject_key in DOCUMENTATION_SUBJECT_PREFERRED_ORDER
        ),
    )
    checked_subjects = (
        "selbst_sozialkompetenz",
        "arbeits_lernkompetenz",
        "deutsch",
        "mathematik",
        "kreatives_gestalten",
        "schulgarten",
    )
    try:
        for width, height in ((1400, 900), (1280, 800), (1180, 760)):
            dialog.resize(width, height)
            dialog.show()
            app.processEvents()
            for subject_key in checked_subjects:
                index = dialog.subject_select.findData(subject_key)
                assert index >= 0
                dialog.subject_select.setCurrentIndex(index)
                app.processEvents()

                combo = dialog.subject_select
                full_name = subject_labels[subject_key]
                assert combo.currentText() == full_name
                assert not combo.currentText().endswith("komp.")
                assert not combo.itemIcon(index).isNull()

                option = QStyleOptionComboBox()
                option.initFrom(combo)
                option.currentText = full_name
                option.currentIcon = combo.itemIcon(index)
                edit_rect = combo.style().subControlRect(
                    QStyle.ComplexControl.CC_ComboBox,
                    option,
                    QStyle.SubControl.SC_ComboBoxEditField,
                    combo,
                )
                available_text_width = (
                    edit_rect.width() - combo.iconSize().width() - 12
                )
                assert available_text_width > 0
                assert combo.fontMetrics().elidedText(
                    full_name,
                    Qt.TextElideMode.ElideRight,
                    available_text_width,
                ) == full_name
    finally:
        dialog.close()
        app.setStyleSheet(previous_stylesheet)


def test_student_profile_uses_the_same_two_presentation_groups() -> None:
    QApplication.instance() or QApplication([])
    screen = StudentProfileScreen()
    cockpit = StudentCompetencyCockpitViewModel(tuple(
        StudentCompetencyCockpitSubjectViewModel(
            subject_key,
            label,
            (),
        )
        for subject_key, label in (
            ("selbst_sozialkompetenz", "Selbst- und Sozialkompetenz"),
            ("arbeits_lernkompetenz", "Arbeits-/Lernkompetenz"),
            ("epu", "EPU"),
            ("deutsch", "Deutsch"),
        )
    ))

    screen._populate_competency_subject_filter(cockpit)

    assert tuple(
        screen.competency_subject_filter.itemText(index)
        for index in range(screen.competency_subject_filter.count())
    ) == (
        "Alle Kompetenzen",
        "Überfachliche Entwicklung",
        "Selbst- und Sozialkompetenz",
        "Arbeits-/Lernkompetenz",
        "Fächer",
        "EPU",
        "Deutsch",
    )
    assert screen.competency_subject_filter.findData("arbeits_lernkompetenz") >= 0
    screen.close()


def test_cross_curricular_competencies_remain_selectable_and_keep_rating_tokens() -> None:
    QApplication.instance() or QApplication([])
    entries = tuple(
        next(
            entry
            for entry in CurriculumDesktopAdapter().list_entries()
            if entry.subject_key == subject_key
        )
        for subject_key in CROSS_CURRICULAR_SUBJECTS
    )
    groups = tuple(
        ObservationCompetencySubjectGroupViewModel(
            entry.subject_key,
            entry.subject_display_name,
            (
                ObservationLearningAreaGroupViewModel(
                    entry.learning_area,
                    (
                        ObservationCompetencyGroupViewModel(
                            entry.competency_group,
                            (
                                ObservationCompetencyOptionViewModel(
                                    entry.competency_id,
                                    entry.subject_key,
                                    entry.subject_display_name,
                                    entry.learning_area,
                                    entry.competency_group,
                                    entry.competency_text,
                                    entry.competency_label,
                                    sort_order=entry.sort_order,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        for entry in entries
    )
    dialog = NewObservationDialog(
        StudentDetailViewModel("student-1", "Ada Beispiel", "A", "1", "", True),
        subject_options=tuple(
            ObservationSubjectOptionViewModel(
                entry.subject_key,
                entry.subject_display_name,
            )
            for entry in entries
        ),
        competency_subject_groups=groups,
    )

    for entry, rating in zip(entries, ("++", "-"), strict=True):
        dialog.subject_select.setCurrentIndex(
            dialog.subject_select.findData(entry.subject_key)
        )
        dialog._refresh_competencies()
        dialog.competency_catalog_tiles[entry.competency_id]._activate()
        dialog.competency_rating_widgets[entry.competency_id].buttons[rating].click()

    draft = dialog.create_draft()
    assert tuple(
        (rating.competency_id, rating.rating)
        for rating in draft.competency_ratings
    ) == tuple(
        (entry.competency_id, rating)
        for entry, rating in zip(entries, ("++", "-"), strict=True)
    )
    dialog.close()
