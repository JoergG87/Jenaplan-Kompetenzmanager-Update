"""Observation view models for the PySide6 desktop app."""

from __future__ import annotations

from dataclasses import dataclass


OBSERVATION_CONTEXT_OPTIONS = (
    "Lernzielkontrolle",
    "Präsentation",
    "Einzelgespräch",
    "Gruppenarbeit",
    "Leseübung",
)

OBSERVATION_RATING_OPTIONS = (
    "++ sicher erreicht",
    "+ erreicht",
    "- in Entwicklung",
    "-- Unterstützungsbedarf",
)

OBSERVATION_RATING_SCORES = {
    "--": 0,
    "-": 1,
    "+": 2,
    "++": 3,
}

OBSERVATION_RATING_WEIGHT_FACTOR = 0.7

OBSERVATION_SAVE_SUCCESS_MESSAGE = "Beobachtung wurde gespeichert."

OBSERVATION_UPDATE_SUCCESS_MESSAGE = "Beobachtung wurde aktualisiert."

OBSERVATION_SAVE_VALIDATION_MESSAGE = (
    "Bitte mindestens eine Kompetenz mit Bewertung auswählen."
)

OBSERVATION_ATTACHMENT_EMPTY_STATE = "Noch keine Anhänge ausgewählt."

OBSERVATION_CROSS_SUBJECT_LABEL = "Fächerübergreifend"

DOCUMENT_TYPE_OPTIONS = (
    "Arbeitsprobe",
    "Lernzielkontrolle",
    "Gesprächsnotiz",
    "Bericht",
    "Foto",
    "Audio",
    "Sonstiges",
)


@dataclass(frozen=True)
class ObservationSubjectOptionViewModel:
    """Display-ready subject option for observation entry."""

    subject_key: str
    display_name: str


@dataclass(frozen=True)
class ObservationCompetencyOptionViewModel:
    """Display-ready selectable competency for observation entry."""

    competency_id: str
    subject_key: str
    subject_display_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    competency_label: str
    selected: bool = False
    rating: str = ""


@dataclass(frozen=True)
class ObservationCompetencyGroupViewModel:
    """Observation competencies grouped by topic."""

    competency_group: str
    competencies: tuple[ObservationCompetencyOptionViewModel, ...]


@dataclass(frozen=True)
class ObservationLearningAreaGroupViewModel:
    """Observation competency topics grouped by learning area."""

    learning_area: str
    competency_groups: tuple[ObservationCompetencyGroupViewModel, ...]


@dataclass(frozen=True)
class ObservationCompetencySubjectGroupViewModel:
    """Observation competencies grouped by subject."""

    subject_key: str
    subject_display_name: str
    learning_area_groups: tuple[ObservationLearningAreaGroupViewModel, ...]


@dataclass(frozen=True)
class ObservationAttachmentDraft:
    """Document or media attachment kept in an observation draft."""

    source_path: str
    title: str
    document_type: str = "Sonstiges"
    note: str = ""
    document_id: str = ""
    file_path: str = ""
    original_filename: str = ""

    @property
    def display_label(self) -> str:
        """Return a compact attachment label."""
        title = self.title or self.original_filename or self.source_path
        return f"{self.document_type} · {title}"


@dataclass(frozen=True)
class ObservationCompetencyRatingDraft:
    """Selected competency rating data kept in the observation draft."""

    subject_key: str
    subject_display_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str
    competency_id: str = ""

    @property
    def display_label(self) -> str:
        """Return the short UI label for selected competencies."""
        return self.learning_area

    @classmethod
    def from_catalog_entry(
        cls,
        entry: object,
        rating: str,
    ) -> "ObservationCompetencyRatingDraft":
        """Create a draft rating from a curriculum catalog entry."""
        return cls(
            competency_id=getattr(entry, "competency_id"),
            subject_key=getattr(entry, "subject_key"),
            subject_display_name=getattr(entry, "subject_display_name"),
            learning_area=getattr(entry, "learning_area"),
            competency_group=getattr(entry, "competency_group"),
            competency_text=getattr(entry, "competency_text"),
            rating=rating,
        )


@dataclass(frozen=True)
class ObservationDraftViewModel:
    """Draft state for the persisted observation workflow."""

    student_id: str
    student_name: str
    date_text: str
    competency_ratings: tuple[ObservationCompetencyRatingDraft, ...]
    context: str
    note: str
    subject_id: str = ""
    subject_display_name: str = ""
    attachment_names: tuple[str, ...] = ()
    attachments: tuple[ObservationAttachmentDraft, ...] = ()
    observation_id: str = ""


@dataclass(frozen=True)
class ObservationRatingViewModel:
    """Displayed competency rating for one persisted observation."""

    competency_id: str
    subject_display_name: str
    learning_area: str
    competency_group: str
    competency_text: str
    rating: str

    @property
    def display_label(self) -> str:
        """Return the compact display label for the profile list."""
        return f"{self.rating} {self.subject_display_name} · {self.learning_area}"


@dataclass(frozen=True)
class ObservationListItem:
    """Profile-list item for one persisted observation."""

    observation_id: str
    student_id: str
    date_text: str
    subject_display_name: str
    context: str
    note: str
    competency_ratings: tuple[ObservationRatingViewModel, ...]
    attachments: tuple[object, ...] = ()

    @property
    def summary(self) -> str:
        """Return the compact first line for profile rendering."""
        parts = [self.date_text, self.subject_display_name]
        if self.context:
            parts.append(self.context)
        return " · ".join(part for part in parts if part)


@dataclass(frozen=True)
class StudentCompetencyStatusViewModel:
    """Calculated observed rating status for one student competency."""

    competency_id: str
    competency_label: str
    subject_id: str
    subject_display_name: str
    rating: str
    rating_label: str
    last_observation_date: str
    sort_order: int
    rating_history: tuple[str, ...] = ()
    observation_count: int = 1
    weighted_score: float = 0.0
    confirmed_rating: str = ""
    confirmed_at: str = ""
    confirmation_note: str = ""

    @property
    def rating_history_label(self) -> str:
        """Return the chronological rating path."""
        if not self.rating_history:
            return "keine aktive Beobachtungshistorie"
        return " → ".join(self.rating_history)

    @property
    def observation_count_label(self) -> str:
        """Return a compact observation count label."""
        if self.observation_count == 0:
            return "keine aktive Beobachtung"
        if self.observation_count == 1:
            return "1 Beobachtung"
        return f"{self.observation_count} Beobachtungen"

    @property
    def confirmation_status_label(self) -> str:
        """Return proposal and teacher confirmation state."""
        if not self.confirmed_rating:
            return (
                f"Vorschlag aus Beobachtungen: {self.rating} · "
                "noch nicht bestätigt"
            )
        if not self.rating_history:
            return f"von Laura bestätigt: {self.confirmed_rating}"
        return (
            f"aus Beobachtungen abgeleitet: {self.rating} · "
            f"von Laura bestätigt: {self.confirmed_rating}"
        )

    @property
    def confirmation_meta_label(self) -> str:
        """Return compact confirmation metadata for profile rendering."""
        if not self.confirmed_at:
            return ""
        confirmed_date = self.confirmed_at[:10]
        if self.last_observation_date > confirmed_date:
            return (
                f"von Laura bestätigt am {confirmed_date} · "
                "neuer Vorschlag aus Beobachtungen vorhanden"
            )
        return f"aktuell bestätigt seit {confirmed_date}"


@dataclass(frozen=True)
class StudentMissingCompetencyViewModel:
    """Catalog competency not yet documented for one student."""

    competency_id: str
    competency_label: str
    sort_order: int


@dataclass(frozen=True)
class StudentDocumentationSubjectStatus:
    """Documentation progress for one subject in the student profile."""

    subject_id: str
    subject_display_name: str
    documented_count: int
    total_count: int
    missing_competencies: tuple[StudentMissingCompetencyViewModel, ...]
    sort_order: int

    @property
    def progress_label(self) -> str:
        """Return compact progress text."""
        return (
            f"{self.subject_display_name}: "
            f"{self.documented_count} / {self.total_count} dokumentiert"
        )

    @property
    def missing_count_label(self) -> str:
        """Return compact missing-competency text."""
        count = len(self.missing_competencies)
        if count == 1:
            return "Noch nicht dokumentierte Kompetenzen (1)"
        return f"Noch nicht dokumentierte Kompetenzen ({count})"


@dataclass(frozen=True)
class StudentCompetencySubjectGroup:
    """Student competency statuses grouped by subject."""

    subject_id: str
    subject_display_name: str
    competencies: tuple[StudentCompetencyStatusViewModel, ...]
    missing_competencies: tuple[StudentMissingCompetencyViewModel, ...] = ()


def observation_rating_label(rating: str) -> str:
    """Return the visible rating label for a persisted rating token."""
    for option in OBSERVATION_RATING_OPTIONS:
        if option.split(" ", 1)[0] == rating:
            return option
    return rating


def calculated_rating_from_history(
    ratings_newest_first: tuple[str, ...],
) -> tuple[str, float]:
    """Return weighted current rating token and score from newest-first ratings."""
    if not ratings_newest_first:
        return "", 0.0
    weighted_sum = 0.0
    weight_sum = 0.0
    for index, rating in enumerate(ratings_newest_first):
        weight = OBSERVATION_RATING_WEIGHT_FACTOR ** index
        weighted_sum += OBSERVATION_RATING_SCORES[rating] * weight
        weight_sum += weight
    score = weighted_sum / weight_sum
    return rating_from_weighted_score(score), score


def rating_from_weighted_score(score: float) -> str:
    """Map a weighted numeric score back to the rating token."""
    if score < 0.75:
        return "--"
    if score < 1.5:
        return "-"
    if score < 2.5:
        return "+"
    return "++"


def observation_rating_keys() -> tuple[str, ...]:
    """Return the stable rating tokens shown in the prototype labels."""
    return tuple(option.split(" ", 1)[0] for option in OBSERVATION_RATING_OPTIONS)
