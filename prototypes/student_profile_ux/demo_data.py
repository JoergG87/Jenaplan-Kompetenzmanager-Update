"""Static, fictional data for the isolated student-profile UX prototype."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime


@dataclass(frozen=True)
class ObservationDemo:
    date: str
    subject: str
    competency: str
    context: str
    note: str
    competency_count: int
    attachment_count: int = 0
    quick: bool = False


@dataclass(frozen=True)
class CompetencyEventDemo:
    """One traceable status event; never a calculated score."""

    date: str
    subject: str
    competency_area: str
    topic: str
    competency_id: str
    competency: str
    status: str
    source: str
    historical: bool = False


@dataclass(frozen=True)
class CompetencyDemo:
    """Stable demo competency, including competencies without any event."""

    subject: str
    competency_area: str
    topic: str
    competency_id: str
    competency: str
    short_label: str = ""
    historical: bool = False


@dataclass(frozen=True)
class RevisionDemo:
    number: int
    date: str
    responsible: str
    status: str


@dataclass(frozen=True)
class OrientationChangeDemo:
    competency: str
    subject: str
    new_status: str
    date: str
    event_type: str
    evidence: str


@dataclass(frozen=True)
class ProfileScenario:
    key: str
    label: str
    student_name: str
    group_name: str
    courses: tuple[str, ...]
    documented_areas: int
    total_areas: int
    observations: tuple[ObservationDemo, ...]
    competencies: tuple[CompetencyDemo, ...]
    competency_events: tuple[CompetencyEventDemo, ...]
    report_draft_status: str = "Kein Berichtsentwurf"
    report_draft_meta: str = ""
    revisions: tuple[RevisionDemo, ...] = ()
    leg_status: str = "Kein LEG-Entwurf"
    leg_meta: str = ""
    file_count: int = 0
    historical_reference: str = ""
    missing_reference: str = ""
    context_hint: str = ""
    open_by_subject: tuple[tuple[str, int], ...] = ()
    development_points: tuple[tuple[str, int], ...] = ()
    orientation_counts: tuple[int, int, int] = (0, 0, 0)
    orientation_changes: tuple[OrientationChangeDemo, ...] = ()


@dataclass(frozen=True)
class RecognizableDevelopmentDemo:
    competency: CompetencyDemo
    events: tuple[CompetencyEventDemo, ...]
    first_status: str
    last_status: str
    first_date: str
    last_date: str
    latest_change_date: str
    curricular_order: int


def _as_date(value: str) -> datetime:
    return datetime.strptime(value, "%d.%m.%Y")


def recognizable_development_candidates(
    scenario: ProfileScenario,
) -> tuple[RecognizableDevelopmentDemo, ...]:
    """Return real status changes, newest change first, with no interpretation."""

    events_by_competency: dict[str, list[CompetencyEventDemo]] = {}
    for item in scenario.competency_events:
        events_by_competency.setdefault(item.competency_id, []).append(item)
    candidates: list[RecognizableDevelopmentDemo] = []
    for order, item in enumerate(scenario.competencies):
        events = tuple(sorted(
            events_by_competency.get(item.competency_id, ()),
            key=lambda event_item: _as_date(event_item.date),
        ))
        if len(events) < 2:
            continue
        changed_events = tuple(
            current
            for previous, current in zip(events, events[1:])
            if current.status != previous.status
        )
        if not changed_events:
            continue
        candidates.append(RecognizableDevelopmentDemo(
            competency=item,
            events=events,
            first_status=events[0].status,
            last_status=events[-1].status,
            first_date=events[0].date,
            last_date=events[-1].date,
            latest_change_date=changed_events[-1].date,
            curricular_order=order,
        ))
    return tuple(sorted(
        candidates,
        key=lambda item: (-_as_date(item.latest_change_date).timestamp(), item.curricular_order),
    ))


def recognizable_developments(
    scenario: ProfileScenario,
    *,
    limit: int = 3,
) -> tuple[RecognizableDevelopmentDemo, ...]:
    return recognizable_development_candidates(scenario)[:max(0, limit)]


def event(
    date: str,
    subject: str,
    area: str,
    topic: str,
    competency_id: str,
    competency: str,
    status: str,
    source: str,
    *,
    historical: bool = False,
) -> CompetencyEventDemo:
    return CompetencyEventDemo(
        date,
        subject,
        area,
        topic,
        competency_id,
        competency,
        status,
        source,
        historical,
    )


def competency(
    subject: str,
    area: str,
    topic: str,
    competency_id: str,
    text: str,
    short_label: str = "",
    *,
    historical: bool = False,
) -> CompetencyDemo:
    return CompetencyDemo(subject, area, topic, competency_id, text, short_label, historical)


BASE_OBSERVATIONS = (
    ObservationDemo(
        "13.07.2026",
        "Mathematik",
        "Uhrzeiten ablesen und darstellen",
        "Lernzeit",
        "Mara liest Uhrzeiten sicher ab und erklärt ihren Lösungsweg in ruhigen Schritten.",
        2,
        1,
    ),
    ObservationDemo(
        "10.07.2026",
        "Deutsch",
        "Zentrale Informationen in Sachtexten auffinden",
        "Leseübung",
        "Zentrale Informationen wurden markiert und anschließend knapp zusammengefasst.",
        2,
    ),
    ObservationDemo(
        "07.07.2026",
        "Fächerübergreifend",
        "Ergebnisse adressatengerecht vorstellen",
        "Gruppenarbeit",
        "Mara übernahm die Ergebnissicherung und bezog Rückfragen aus der Gruppe ein.",
        3,
    ),
    ObservationDemo(
        "02.07.2026",
        "EPU",
        "Einen Versuchsaufbau beschreiben",
        "Präsentation",
        "Kurze Notiz zur Vorstellung des Versuchsaufbaus.",
        0,
        quick=True,
    ),
)


BASE_COMPETENCIES = (
    competency("Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-001", "Volle Stunden und Minuten an analogen sowie digitalen Uhren ablesen", "Uhrzeiten ablesen"),
    competency("Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-002", "Zeitspannen bestimmen und den eigenen Lösungsweg nachvollziehbar beschreiben", "Zeitspannen bestimmen"),
    competency("Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-007", "Zeitangaben in alltagsnahen Situationen vergleichen", "Zeitangaben vergleichen"),
    competency("Mathematik", "Größen und Messen", "Größen und Messen", "CMP-DEMO-M-003", "Längen vergleichen"),
    competency("Mathematik", "Größen und Messen", "Größen und Messen", "CMP-DEMO-M-004", "Mit Geldbeträgen rechnen"),
    competency("Mathematik", "Raum und Form", "Geometrie", "CMP-DEMO-M-005", "Körper und Flächen zuordnen"),
    competency("Mathematik", "Zahlen und Operationen", "Zahlen und Operationen", "CMP-DEMO-M-006", "Zahlen bis 1000 ordnen"),
    competency("Deutsch", "Lesen", "Lesen", "CMP-DEMO-D-001", "Zentrale Informationen in längeren Sachtexten auffinden und benennen", "Informationen auffinden"),
    competency("Deutsch", "Lesen", "Lesen", "CMP-DEMO-D-002", "Textstellen als Beleg für eine Aussage markieren", "Textstellen belegen"),
    competency("Deutsch", "Schreiben", "Schreiben", "CMP-DEMO-D-003", "Texte verständlich gliedern"),
    competency("Deutsch", "Sprache und Sprachgebrauch", "Sprache untersuchen", "CMP-DEMO-D-004", "Wortarten in Beispielen erkennen"),
    competency("Deutsch", "Sprechen und Zuhören", "Sprechen und Zuhören", "CMP-DEMO-D-005", "Gesprächsbeiträge aufgreifen"),
    competency("Sachunterricht", "Natur und Umwelt", "Natur und Umwelt", "CMP-DEMO-S-001", "Einen Versuchsaufbau beschreiben"),
)


BASE_EVENTS = (
    # Mathematik · Zeit: dense development across two competencies.
    event("15.09.2025", "Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-001", "Volle Stunden und Minuten an analogen sowie digitalen Uhren ablesen", "- in Entwicklung", "Beobachtung"),
    event("18.11.2025", "Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-001", "Volle Stunden und Minuten an analogen sowie digitalen Uhren ablesen", "+ erreicht", "Beobachtung"),
    event("04.02.2026", "Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-001", "Volle Stunden und Minuten an analogen sowie digitalen Uhren ablesen", "+ erreicht", "Bestätigung"),
    event("01.10.2025", "Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-002", "Zeitspannen bestimmen und den eigenen Lösungsweg nachvollziehbar beschreiben", "- in Entwicklung", "Beobachtung"),
    event("21.04.2026", "Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-002", "Zeitspannen bestimmen und den eigenen Lösungsweg nachvollziehbar beschreiben", "- in Entwicklung", "Beobachtung"),
    event("13.07.2026", "Mathematik", "Größen und Messen", "Zeit", "CMP-DEMO-M-002", "Zeitspannen bestimmen und den eigenen Lösungsweg nachvollziehbar beschreiben", "+ erreicht", "Bestätigung"),
    # Mathematik · Größen und Messen: incomplete documentation is intentional.
    event("20.10.2025", "Mathematik", "Größen und Messen", "Größen und Messen", "CMP-DEMO-M-003", "Längen vergleichen", "- in Entwicklung", "Beobachtung"),
    event("18.03.2026", "Mathematik", "Größen und Messen", "Größen und Messen", "CMP-DEMO-M-003", "Längen vergleichen", "+ erreicht", "Bestätigung"),
    event("01.03.2026", "Mathematik", "Größen und Messen", "Größen und Messen", "CMP-DEMO-M-004", "Mit Geldbeträgen rechnen", "- in Entwicklung", "Beobachtung"),
    event("29.06.2026", "Mathematik", "Größen und Messen", "Größen und Messen", "CMP-DEMO-M-004", "Mit Geldbeträgen rechnen", "- in Entwicklung", "Beobachtung"),
    # Mathematik · Geometrie: single point state.
    event("06.07.2026", "Mathematik", "Raum und Form", "Geometrie", "CMP-DEMO-M-005", "Körper und Flächen zuordnen", "+ erreicht", "Beobachtung"),
    # Mathematik · Zahlen und Operationen.
    event("09.12.2025", "Mathematik", "Zahlen und Operationen", "Zahlen und Operationen", "CMP-DEMO-M-006", "Zahlen bis 1000 ordnen", "- in Entwicklung", "Beobachtung"),
    event("12.05.2026", "Mathematik", "Zahlen und Operationen", "Zahlen und Operationen", "CMP-DEMO-M-006", "Zahlen bis 1000 ordnen", "++ sicher erreicht", "Bestätigung"),
    # Deutsch · Lesen.
    event("22.09.2025", "Deutsch", "Lesen", "Lesen", "CMP-DEMO-D-001", "Zentrale Informationen in längeren Sachtexten auffinden und benennen", "-- Unterstützungsbedarf", "Beobachtung"),
    event("14.01.2026", "Deutsch", "Lesen", "Lesen", "CMP-DEMO-D-001", "Zentrale Informationen in längeren Sachtexten auffinden und benennen", "- in Entwicklung", "Beobachtung"),
    event("10.07.2026", "Deutsch", "Lesen", "Lesen", "CMP-DEMO-D-001", "Zentrale Informationen in längeren Sachtexten auffinden und benennen", "+ erreicht", "Bestätigung"),
    event("11.03.2026", "Deutsch", "Lesen", "Lesen", "CMP-DEMO-D-002", "Textstellen als Beleg für eine Aussage markieren", "- in Entwicklung", "Beobachtung"),
    # Deutsch · Schreiben.
    event("10.09.2025", "Deutsch", "Schreiben", "Schreiben", "CMP-DEMO-D-003", "Texte verständlich gliedern", "+ erreicht", "Beobachtung"),
    event("03.11.2025", "Deutsch", "Schreiben", "Schreiben", "CMP-DEMO-D-003", "Texte verständlich gliedern", "- in Entwicklung", "Beobachtung"),
    event("16.06.2026", "Deutsch", "Schreiben", "Schreiben", "CMP-DEMO-D-003", "Texte verständlich gliedern", "+ erreicht", "Bestätigung"),
    # Deutsch · Sprache untersuchen / Sprechen und Zuhören.
    event("08.05.2026", "Deutsch", "Sprache und Sprachgebrauch", "Sprache untersuchen", "CMP-DEMO-D-004", "Wortarten in Beispielen erkennen", "- in Entwicklung", "Beobachtung"),
    event("07.07.2026", "Deutsch", "Sprechen und Zuhören", "Sprechen und Zuhören", "CMP-DEMO-D-005", "Gesprächsbeiträge aufgreifen", "+ erreicht", "Beobachtung"),
    # Sachunterricht: real status change across two events.
    event("15.04.2026", "Sachunterricht", "Natur und Umwelt", "Natur und Umwelt", "CMP-DEMO-S-001", "Einen Versuchsaufbau beschreiben", "-- Unterstützungsbedarf", "Beobachtung"),
    event("02.07.2026", "Sachunterricht", "Natur und Umwelt", "Natur und Umwelt", "CMP-DEMO-S-001", "Einen Versuchsaufbau beschreiben", "- in Entwicklung", "Beobachtung"),
)


THREE_DEVELOPMENTS_EVENTS = tuple(
    item
    for item in BASE_EVENTS
    if item.competency_id in {"CMP-DEMO-M-001", "CMP-DEMO-M-002", "CMP-DEMO-M-006"}
)


CROSS_SUBJECT_DEVELOPMENTS_EVENTS = tuple(
    item
    for item in BASE_EVENTS
    if item.competency_id in {"CMP-DEMO-M-002", "CMP-DEMO-D-001", "CMP-DEMO-S-001"}
)


ORIENTATION_CHANGES = (
    OrientationChangeDemo(
        competency="Zeit lesen",
        subject="Mathematik · Zeit",
        new_status="Sicher bestätigt",
        date="12.07.2026",
        event_type="Beobachtung",
        evidence="Kann Viertelstunden sicher ablesen.",
    ),
    OrientationChangeDemo(
        competency="Vorlesen",
        subject="Deutsch · Lesen",
        new_status="Erreicht",
        date="05.07.2026",
        event_type="Kompetenz bestätigt",
        evidence="Liest im Lesekreis flüssig und betont passende Stellen.",
    ),
    OrientationChangeDemo(
        competency="Wasser im Alltag",
        subject="Sachunterricht · Natur und Umwelt",
        new_status="In Entwicklung",
        date="01.07.2026",
        event_type="Beobachtung",
        evidence="Nennt Beispiele für Wassernutzung und erklärt erste Zusammenhänge.",
    ),
)


LITTLE_DOCUMENTATION_CHANGES = (
    OrientationChangeDemo(
        competency="Versuchsaufbau beschreiben",
        subject="Sachunterricht · Natur und Umwelt",
        new_status="In Entwicklung",
        date="02.07.2026",
        event_type="Beobachtung",
        evidence="Beschreibt Aufbau und Reihenfolge in kurzen verständlichen Schritten.",
    ),
)


BASE = ProfileScenario(
    key="well_documented",
    label="Mehrere Fächer und Themen",
    student_name="Mara Beispielkind",
    group_name="Sonnenbogen",
    courses=("Kurs 3", "Mathematik 3", "Deutsch 3"),
    documented_areas=16,
    total_areas=21,
    observations=BASE_OBSERVATIONS,
    competencies=BASE_COMPETENCIES,
    competency_events=BASE_EVENTS,
    report_draft_status="Berichtsentwurf vorhanden",
    report_draft_meta="Lernentwicklungsbericht · 01.02.–31.07.2026 · Entwurf geändert",
    revisions=(
        RevisionDemo(2, "01.07.2026", "Laura Lernbegleiterin", "Aktuell"),
        RevisionDemo(1, "18.06.2026", "Laura Lernbegleiterin", "Ersetzt"),
    ),
    leg_status="LEG-Entwurf vorhanden",
    leg_meta="Gespräch am 22.07.2026 · zuletzt gespeichert 13.07.2026",
    file_count=4,
    context_hint="Mehrere aktuelle Beobachtungen und bestätigte Kompetenzstände liegen vor.",
    open_by_subject=(("Mathematik", 2), ("Deutsch", 2), ("Sachunterricht", 1)),
    development_points=(("Sep 25", 1), ("Nov 25", 2), ("Feb 26", 2), ("Apr 26", 3), ("Jul 26", 3)),
    orientation_counts=(16, 5, 2),
    orientation_changes=ORIENTATION_CHANGES,
)


SCENARIOS = (
    BASE,
    replace(
        BASE,
        key="three_developments",
        label="Drei erkennbare Entwicklungen",
        competency_events=THREE_DEVELOPMENTS_EVENTS,
    ),
    replace(
        BASE,
        key="cross_subject_developments",
        label="Fachübergreifende Entwicklungen",
        competency_events=CROSS_SUBJECT_DEVELOPMENTS_EVENTS,
    ),
    replace(
        BASE,
        key="little_documentation",
        label="Thema mit wenig Dokumentation",
        student_name="Jonas Beispielkind",
        group_name="Wiesenfüchse",
        courses=("Kurs 1", "Mathematik 1", "Deutsch 1"),
        documented_areas=3,
        total_areas=21,
        observations=BASE_OBSERVATIONS[:1],
        competency_events=tuple(item for item in BASE_EVENTS if item.topic in {"Geometrie", "Natur und Umwelt"}),
        report_draft_status="Kein Berichtsentwurf",
        report_draft_meta="",
        revisions=(),
        leg_status="Kein LEG-Entwurf",
        leg_meta="",
        file_count=1,
        context_hint="Wenige datierte Ereignisse sind sichtbar; fehlende Dokumentation wird nicht bewertet.",
        open_by_subject=(("Mathematik", 6), ("Deutsch", 6), ("Sachunterricht", 4), ("Kunst", 2)),
        development_points=(("Jul 26", 1),),
        orientation_counts=(1, 2, 1),
        orientation_changes=LITTLE_DOCUMENTATION_CHANGES,
    ),
    replace(BASE, key="report_draft", label="Berichtsentwurf vorhanden", revisions=(), leg_status="Kein LEG-Entwurf", leg_meta=""),
    replace(
        BASE,
        key="finalized_revisions",
        label="Finalisierte Revisionen vorhanden",
        report_draft_status="Berichtsentwurf nach Finalisierung",
        report_draft_meta="Lernentwicklungsbericht · Entwurf geändert",
        revisions=(
            RevisionDemo(3, "12.07.2026", "Laura Lernbegleiterin", "Aktuell"),
            RevisionDemo(2, "01.07.2026", "Laura Lernbegleiterin", "Ersetzt"),
            RevisionDemo(1, "18.06.2026", "Laura Lernbegleiterin", "Ersetzt"),
        ),
        leg_status="Kein LEG-Entwurf",
        leg_meta="",
    ),
    replace(BASE, key="leg_available", label="LEG vorhanden", report_draft_status="Kein Berichtsentwurf", report_draft_meta="", revisions=()),
    replace(
        BASE,
        key="no_observations",
        label="Fach ohne Dokumentation",
        student_name="Nele Beispielkind",
        group_name="Regenbogen",
        courses=("Kurs 2", "Mathematik 2", "Deutsch 2"),
        documented_areas=0,
        total_areas=21,
        observations=(),
        competency_events=(),
        report_draft_status="Kein Berichtsentwurf",
        report_draft_meta="",
        revisions=(),
        leg_status="Kein LEG-Entwurf",
        leg_meta="",
        file_count=0,
        context_hint="Noch keine aktiven Beobachtungen dokumentiert.",
        open_by_subject=(("Mathematik", 8), ("Deutsch", 7), ("Sachunterricht", 4), ("Kunst", 2)),
        development_points=(),
        orientation_counts=(0, 0, 0),
        orientation_changes=(),
    ),
    replace(
        BASE,
        key="historical_reference",
        label="Historische Kompetenzreferenz",
        competencies=BASE_COMPETENCIES
        + (
            competency("Mathematik", "Größen und Messen", "Zeit", "CMP-HIST-017", "Zeitspannen bestimmen (alter Katalogstand)", historical=True),
        ),
        competency_events=BASE_EVENTS
        + (
            event("17.01.2024", "Mathematik", "Größen und Messen", "Zeit", "CMP-HIST-017", "Zeitspannen bestimmen (alter Katalogstand)", "- in Entwicklung", "Beobachtung", historical=True),
            event("17.05.2024", "Mathematik", "Größen und Messen", "Zeit", "CMP-HIST-017", "Zeitspannen bestimmen (alter Katalogstand)", "+ erreicht", "Bestätigung", historical=True),
        ),
        historical_reference="Historische Kompetenz: Zeitspannen bestimmen (alter Katalogstand)",
        missing_reference="OBS-000417 · Beobachtungsbeleg nicht mehr verfügbar",
        report_draft_meta="Enthält eine historische Kompetenzreferenz",
        leg_meta="Ein gespeicherter Beleg ist nicht mehr verfügbar",
    ),
)


SCENARIO_BY_KEY = {scenario.key: scenario for scenario in SCENARIOS}
