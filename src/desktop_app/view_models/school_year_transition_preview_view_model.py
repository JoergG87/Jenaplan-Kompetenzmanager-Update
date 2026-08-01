"""Qt-free display mapping for the transient school-year transition plan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.application.school_year_transition_plan import (
    SchoolYearTransitionPlan,
    SchoolYearTransitionPlanItem,
    SchoolYearTransitionPlanTargetStatus,
)


EMPTY_VALUE = "—"

ACCEPT_PROPOSAL = "accept_proposal"
SELECT_OTHER_COURSE = "select_other_course"
REPEAT_YEAR_LEVEL_THREE = "repeat_year_level_three"
MARK_EXITED = "mark_exited"
LEAVE_UNRESOLVED = "leave_unresolved"
KEEP_CURRENT_GROUP = "keep_current_group"
SELECT_OTHER_GROUP = "select_other_group"

_TARGET_STATUS_LABELS = {
    SchoolYearTransitionPlanTargetStatus.ADVANCE_1_TO_2: "Wechsel 1 → 2",
    SchoolYearTransitionPlanTargetStatus.ADVANCE_2_TO_3: "Wechsel 2 → 3",
    SchoolYearTransitionPlanTargetStatus.OTHER_COURSE: "Anderer Kurs",
    SchoolYearTransitionPlanTargetStatus.REPEAT_YEAR_LEVEL_THREE: (
        "Kurs 3 wiederholen"
    ),
    SchoolYearTransitionPlanTargetStatus.EXITED: "Ausgeschieden",
    SchoolYearTransitionPlanTargetStatus.UNRESOLVED: "Ungelöst",
}

_ISSUE_LABELS = {
    "CURRENT_ASSIGNMENT_AMBIGUOUS": "Bisherige Zuordnung ist nicht eindeutig.",
    "CURRENT_ASSIGNMENT_MISSING": "Bisherige Zuordnung fehlt.",
    "CURRENT_ASSIGNMENT_STATUS_INVALID": "Bisheriger Zuordnungsstatus ist ungültig.",
    "CURRENT_COURSE_INVALID": "Bisheriger Kurs ist nicht gültig.",
    "CURRENT_GROUP_INVALID": "Bisherige Stammgruppe ist nicht gültig.",
    "CURRENT_SCHOOL_YEAR_AMBIGUOUS": "Aktuelles Schuljahr ist nicht eindeutig.",
    "CURRENT_SCHOOL_YEAR_MISSING": "Aktuelles Schuljahr fehlt.",
    "CURRENT_SCHOOL_YEAR_UNAVAILABLE": "Aktuelles Schuljahr ist nicht verfügbar.",
    "CURRENT_YEAR_LEVEL_INVALID": "Bisherige Kursstufe ist nicht gültig.",
    "NEW_SCHOOL_YEAR_DATE_INVALID": "Zeitraum des neuen Schuljahres ist ungültig.",
    "NEW_SCHOOL_YEAR_DATE_RANGE_INVALID": "Zeitraum des neuen Schuljahres ist ungültig.",
    "NEW_SCHOOL_YEAR_LABEL_INVALID": "Bezeichnung des neuen Schuljahres fehlt.",
    "NEW_SCHOOL_YEAR_NOT_AFTER_CURRENT": (
        "Das neue Schuljahr liegt nicht nach dem aktuellen Schuljahr."
    ),
    "NEW_SCHOOL_YEAR_OVERLAP": "Das neue Schuljahr überschneidet ein vorhandenes.",
    "PLAN_TARGET_COURSE_MISSING": "Im Plan fehlt ein Zielkurs.",
    "PLAN_TARGET_GROUP_MISSING": "Im Plan fehlt eine Zielstammgruppe.",
    "PLAN_TARGET_UNRESOLVED": "Der Zielstand bleibt bewusst ungelöst.",
    "SCHOOL_YEAR_GAP": "Zwischen den Schuljahren besteht eine Lücke.",
    "STUDENT_ARCHIVED": "Kind ist archiviert.",
    "STUDENT_EXITED": "Kind ist ausgeschieden.",
    "STUDENT_MASTER_DATA_MISSING": "Schülerstammdaten fehlen.",
    "TARGET_COURSE_AMBIGUOUS": "Zielkurs ist nicht eindeutig.",
    "TARGET_COURSE_MISSING": "Passender Zielkurs fehlt.",
    "YEAR_LEVEL_THREE_SELECTION_REQUIRED": (
        "Für Kursstufe 3 ist eine bewusste Entscheidung erforderlich."
    ),
}


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionDecisionOptionViewModel:
    """One explicit user choice offered by the transient plan."""

    action: str
    option_id: str | None
    label: str


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreviewRowViewModel:
    """One display-ready row in unchanged plan order."""

    student_id: str
    child_label: str
    current_group_id: str | None
    current_group_label: str
    current_course_id: str | None
    current_course_label: str
    current_year_level_label: str
    target_status_label: str
    target_group_id: str | None
    target_group_label: str
    target_course_id: str | None
    target_course_label: str
    warnings_label: str
    resolved: bool
    exited: bool
    accessible_description: str
    course_choices: tuple[SchoolYearTransitionDecisionOptionViewModel, ...]
    group_choices: tuple[SchoolYearTransitionDecisionOptionViewModel, ...]


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionPreviewViewModel:
    """Complete display mapping of one current transient transition plan."""

    current_school_year_label: str
    planned_school_year_label: str
    period_label: str
    student_count: int
    resolved_count: int
    advance_1_to_2_count: int
    advance_2_to_3_count: int
    other_course_count: int
    repeat_year_level_three_count: int
    exited_count: int
    group_change_count: int
    unresolved_count: int
    edited_count: int
    status_label: str
    status_description: str
    rows: tuple[SchoolYearTransitionPreviewRowViewModel, ...]
    global_issues_label: str

    @classmethod
    def from_plan(
        cls,
        plan: SchoolYearTransitionPlan,
    ) -> "SchoolYearTransitionPreviewViewModel":
        """Map only the current immutable plan and its own validation."""
        validation = plan.validate()
        counts = validation.counts
        item_issue_codes = {
            item.student_id: tuple(
                issue.code
                for issue in validation.issues
                if issue.student_id == item.student_id
            )
            for item in plan.items
        }
        rows = tuple(
            _row_from_item(plan, item, item_issue_codes[item.student_id])
            for item in plan.items
        )
        status_label = (
            "Plan vollständig"
            if validation.complete
            else "Entscheidungen erforderlich"
        )
        status_description = (
            "Alle Zielstände sind im flüchtigen Plan vollständig."
            if validation.complete
            else (
                f"{counts.unresolved_count} von {counts.student_count} "
                "Kindern sind noch ungelöst oder blockiert."
            )
        )
        global_issues = tuple(
            _issue_label(issue.code)
            for issue in validation.issues
            if issue.student_id is None
        )
        return cls(
            current_school_year_label=plan.current_school_year_label,
            planned_school_year_label=plan.planned_school_year_label,
            period_label=_period_label(
                plan.planned_school_year_start_date,
                plan.planned_school_year_end_date,
            ),
            student_count=counts.student_count,
            resolved_count=counts.resolved_count,
            advance_1_to_2_count=counts.advance_1_to_2_count,
            advance_2_to_3_count=counts.advance_2_to_3_count,
            other_course_count=counts.other_course_count,
            repeat_year_level_three_count=(
                counts.repeat_year_level_three_count
            ),
            exited_count=counts.exited_count,
            group_change_count=counts.group_change_count,
            unresolved_count=counts.unresolved_count,
            edited_count=counts.edited_count,
            status_label=status_label,
            status_description=status_description,
            rows=rows,
            global_issues_label=" ".join(global_issues),
        )

    def filtered_rows(
        self,
        *,
        unresolved_only: bool = False,
        current_course_id: str | None = None,
        target_course_id: str | None = None,
        current_group_id: str | None = None,
        target_group_id: str | None = None,
    ) -> tuple[SchoolYearTransitionPreviewRowViewModel, ...]:
        """Combine transient display filters without changing plan order."""
        return tuple(
            row
            for row in self.rows
            if (not unresolved_only or not row.resolved)
            and (
                current_course_id is None
                or row.current_course_id == current_course_id
            )
            and (
                target_course_id is None
                or row.target_course_id == target_course_id
            )
            and (
                current_group_id is None
                or row.current_group_id == current_group_id
            )
            and (
                target_group_id is None
                or row.target_group_id == target_group_id
            )
        )


def apply_course_choice(
    plan: SchoolYearTransitionPlan,
    *,
    student_id: str,
    action: str,
    option_id: str | None,
) -> SchoolYearTransitionPlan:
    """Delegate one explicit UI choice to the immutable plan model."""
    if action == ACCEPT_PROPOSAL:
        return plan.accept_proposed_course(student_id)
    if action == SELECT_OTHER_COURSE and option_id is not None:
        return plan.select_other_course(student_id, option_id)
    if action == REPEAT_YEAR_LEVEL_THREE and option_id is not None:
        return plan.repeat_year_level_three(student_id, option_id)
    if action == MARK_EXITED:
        return plan.mark_exited(student_id)
    if action == LEAVE_UNRESOLVED:
        return plan.leave_unresolved(student_id)
    raise ValueError("unknown_course_choice")


def apply_group_choice(
    plan: SchoolYearTransitionPlan,
    *,
    student_id: str,
    action: str,
    option_id: str | None,
) -> SchoolYearTransitionPlan:
    """Delegate one explicit UI group choice to the immutable plan model."""
    if action == KEEP_CURRENT_GROUP:
        return plan.keep_current_group(student_id)
    if action == SELECT_OTHER_GROUP and option_id is not None:
        return plan.select_other_group(student_id, option_id)
    raise ValueError("unknown_group_choice")


def _row_from_item(
    plan: SchoolYearTransitionPlan,
    item: SchoolYearTransitionPlanItem,
    plan_issue_codes: tuple[str, ...],
) -> SchoolYearTransitionPreviewRowViewModel:
    original_codes = tuple(
        dict.fromkeys(
            item.original_warning_codes + item.original_blocker_codes
        )
    )
    original_issues = tuple(
        f"Aus Vorschau: {_issue_label(code)}" for code in original_codes
    )
    current_issues = tuple(
        f"Aktueller Plan: {_issue_label(code)}"
        for code in plan_issue_codes
        if code not in original_codes
    )
    issue_labels = original_issues + current_issues
    warnings_label = " ".join(issue_labels) if issue_labels else "Keine"
    target_status_label = _TARGET_STATUS_LABELS[item.target_status]
    current_group_label = item.current_group_name or EMPTY_VALUE
    current_course_label = item.current_course_name or EMPTY_VALUE
    current_year_level_label = _year_level_label(item.current_year_level)
    target_group_label = item.target_group_name or EMPTY_VALUE
    target_course_label = item.target_course_name or EMPTY_VALUE
    accessible_description = (
        f"Kind {item.student_display_name}. "
        f"Bisherige Stammgruppe {current_group_label}. "
        f"Bisheriger Kurs {current_course_label}. "
        f"Bisherige Kursstufe {current_year_level_label}. "
        f"Zielstatus {target_status_label}. "
        f"Zielstammgruppe {target_group_label}. "
        f"Zielkurs {target_course_label}. "
        f"Warnungen und Blocker {warnings_label}"
    )
    return SchoolYearTransitionPreviewRowViewModel(
        student_id=item.student_id,
        child_label=item.student_display_name,
        current_group_id=item.current_group_id,
        current_group_label=current_group_label,
        current_course_id=item.current_course_id,
        current_course_label=current_course_label,
        current_year_level_label=current_year_level_label,
        target_status_label=target_status_label,
        target_group_id=item.target_group_id,
        target_group_label=target_group_label,
        target_course_id=item.target_course_id,
        target_course_label=target_course_label,
        warnings_label=warnings_label,
        resolved=item.resolved,
        exited=(
            item.target_status is SchoolYearTransitionPlanTargetStatus.EXITED
        ),
        accessible_description=accessible_description,
        course_choices=_course_choices(plan, item),
        group_choices=_group_choices(plan, item),
    )


def _course_choices(
    plan: SchoolYearTransitionPlan,
    item: SchoolYearTransitionPlanItem,
) -> tuple[SchoolYearTransitionDecisionOptionViewModel, ...]:
    choices: list[SchoolYearTransitionDecisionOptionViewModel] = []
    if item.original_proposed_course_id is not None:
        choices.append(
            SchoolYearTransitionDecisionOptionViewModel(
                ACCEPT_PROPOSAL,
                None,
                (
                    "Vorschlag übernehmen: "
                    f"{item.original_proposed_course_name}"
                ),
            )
        )
    choices.extend(
        SchoolYearTransitionDecisionOptionViewModel(
            SELECT_OTHER_COURSE,
            course.course_id,
            f"Anderen aktiven Kurs wählen: {course.course_name}",
        )
        for course in plan.available_courses
        if course.course_id != item.original_proposed_course_id
    )
    if item.original_current_year_level == 3:
        choices.extend(
            SchoolYearTransitionDecisionOptionViewModel(
                REPEAT_YEAR_LEVEL_THREE,
                course.course_id,
                f"Kurs 3 wiederholen: {course.course_name}",
            )
            for course in plan.available_courses
            if course.year_level == 3
        )
    choices.extend(
        (
            SchoolYearTransitionDecisionOptionViewModel(
                MARK_EXITED,
                None,
                "Als ausgeschieden markieren",
            ),
            SchoolYearTransitionDecisionOptionViewModel(
                LEAVE_UNRESOLVED,
                None,
                "Bewusst ungelöst lassen",
            ),
        )
    )
    return tuple(choices)


def _group_choices(
    plan: SchoolYearTransitionPlan,
    item: SchoolYearTransitionPlanItem,
) -> tuple[SchoolYearTransitionDecisionOptionViewModel, ...]:
    if item.target_status is SchoolYearTransitionPlanTargetStatus.EXITED:
        return ()
    choices: list[SchoolYearTransitionDecisionOptionViewModel] = []
    active_group_ids = {
        group.group_id for group in plan.available_groups
    }
    if (
        item.current_group_id is not None
        and item.current_group_id in active_group_ids
    ):
        choices.append(
            SchoolYearTransitionDecisionOptionViewModel(
                KEEP_CURRENT_GROUP,
                None,
                (
                    "Stammgruppe unverändert lassen: "
                    f"{item.current_group_name}"
                ),
            )
        )
    choices.extend(
        SchoolYearTransitionDecisionOptionViewModel(
            SELECT_OTHER_GROUP,
            group.group_id,
            f"Andere aktive Stammgruppe wählen: {group.group_name}",
        )
        for group in plan.available_groups
        if group.group_id != item.current_group_id
    )
    return tuple(choices)


def _issue_label(code: str) -> str:
    return _ISSUE_LABELS.get(code, f"Hinweis: {code}")


def _year_level_label(year_level: int | None) -> str:
    return f"Stufe {year_level}" if year_level is not None else EMPTY_VALUE


def _period_label(start_date: object, end_date: object) -> str:
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        return "Nicht verfügbar"
    return f"{start_date:%d.%m.%Y} – {end_date:%d.%m.%Y}"
