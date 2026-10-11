"""Read-only export of the canonical cockpit; never turns proposals into decisions."""
from dataclasses import dataclass

from src.desktop_app.view_models.observation_view_model import (
    StudentCompetencyCockpitViewModel, rating_profile_for_competency,
)


@dataclass(frozen=True)
class CompetencyPdfRow:
    text: str
    context: str
    rating: str
    source: str


@dataclass(frozen=True)
class CompetencyPdfSubject:
    name: str
    rating_profile: str
    rows: tuple[CompetencyPdfRow, ...]


@dataclass(frozen=True)
class CompetencyPdfModel:
    student_name: str
    school_year: str
    subjects: tuple[CompetencyPdfSubject, ...]


def build_competency_pdf_model(
    student_name: str, school_year: str,
    cockpit: StudentCompetencyCockpitViewModel, subject_id: str = "",
) -> CompetencyPdfModel:
    subjects = []
    for subject in cockpit.subjects:
        if subject_id and subject.subject_id != subject_id:
            continue
        rows = []
        for area in subject.learning_areas:
            for topic in area.topics:
                for status in topic.competencies:
                    if status.historical or not status.is_active or status.catalog_status != "current":
                        continue
                    rating = ""
                    source = {
                        "undocumented": "Noch nicht dokumentiert",
                        "observed_unconfirmed": "Beobachtet, noch nicht bestätigt",
                        "confirmation_unknown": "Bestätigungsstand unklar",
                    }.get(status.documentation_state, "Kein sicher bestätigter Stand")
                    if status.documentation_state in {"confirmed", "newer_observations"} and status.confirmed_rating in {"--", "-", "+", "++"}:
                        rating = status.confirmed_rating
                        source = "Bestätigt"
                        if status.confirmed_at:
                            source += " am " + status.confirmed_at[:10]
                        if status.documentation_state == "newer_observations":
                            source += " · neuere Beobachtungen vorhanden"
                    rows.append(CompetencyPdfRow(
                        status.competency_text or status.competency_label,
                        " / ".join(dict.fromkeys((area.learning_area, topic.competency_group))),
                        rating, source,
                    ))
        if rows:
            subjects.append(CompetencyPdfSubject(
                subject.subject_display_name,
                rating_profile_for_competency(subject), tuple(rows),
            ))
    if not subjects:
        raise ValueError("Keine aktuellen Kompetenzen für diesen Export vorhanden.")
    return CompetencyPdfModel(student_name, school_year, tuple(subjects))
