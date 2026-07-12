"""Fiktive In-Memory-Daten fuer den isolierten LEG-UX-Prototyp."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompetencyDemo:
    subject: str
    learning_area: str
    topic: str
    short_label: str
    text: str
    confirmed_state: str
    last_observation: str
    selected: bool = False


@dataclass(frozen=True)
class ObservationDemo:
    date: str
    area: str
    context: str
    note: str
    selected: bool = False


@dataclass(frozen=True)
class ChartDemo:
    title: str
    description: str
    selected: bool = False


DOCUMENT_HEADER = {
    "student": "Mara Beispielkind",
    "group": "Sonnenbogen",
    "period": "Februar bis Juli 2026",
    "date": "10. Juli 2026",
    "teacher": "Laura Musterlehrerin",
}


SUBJECT_AREAS = (
    ("Deutsch", False),
    ("Mathematik", True),
    ("EPU", False),
    ("Kunst", False),
)


CROSS_CUTTING_AREAS = (
    ("Arbeitsverhalten", False),
    ("Sozialverhalten", True),
    ("Selbstständigkeit", True),
    ("Lernorganisation", False),
)


COMPETENCIES = (
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Volle Stunden ablesen",
        "Mara liest volle Uhrzeiten auf analogen und digitalen Uhren ab.",
        "sicher", "24.06. · Lernzeit · ohne Erinnerung erklärt", True,
    ),
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Halbe Stunden ablesen",
        "Mara liest halbe Uhrzeiten und ordnet sie passenden Schreibweisen zu.",
        "weitgehend sicher", "24.06. · Lernzeit · bei einer Aufgabe kurz nachgefragt",
    ),
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Viertelstunden ablesen",
        "Mara liest Viertelstunden in gebräuchlichen Formulierungen ab.",
        "mit wenig Unterstützung", "24.06. · Lernzeit · beide Lesarten verglichen", True,
    ),
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Uhrzeiten minutengenau ablesen",
        "Mara liest Uhrzeiten minutengenau ab.",
        "in Entwicklung", "02.07. · Partnerarbeit · Minutenzeiger noch einmal geprüft",
    ),
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Uhrzeiten einstellen",
        "Mara stellt vorgegebene Uhrzeiten auf einer Lernuhr ein.",
        "weitgehend sicher", "02.07. · Partnerarbeit · vier von fünf Beispielen selbstständig",
    ),
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Uhrzeiten notieren",
        "Mara notiert abgelesene Uhrzeiten passend und gut lesbar.",
        "sicher", "02.07. · Partnerarbeit · Schreibweise selbst kontrolliert", True,
    ),
    CompetencyDemo(
        "Mathematik", "Größen und Messen", "Zeit", "Schreib- und Sprechweisen übertragen",
        "Mara überträgt Uhrzeiten zwischen analoger, digitaler und sprachlicher Schreibweise.",
        "mit Unterstützung", "02.07. · Partnerarbeit · Sprachform gemeinsam geklärt",
    ),
    CompetencyDemo(
        "Deutsch", "Sprechen und Zuhören", "Erlebnisse erzählen", "Erzählfaden halten",
        "Mara erzählt Erlebnisse in einer nachvollziehbaren Reihenfolge.",
        "weitgehend sicher", "18.06. · Erzählkreis · Reihenfolge mit Stichwortkarte gehalten",
    ),
    CompetencyDemo(
        "EPU", "Fragen und Forschen", "Wasser", "Eigene Fragen entwickeln",
        "Mara entwickelt eigene Fragen zu einem gemeinsamen Sachthema.",
        "sicher", "11.06. · Projektzeit · zwei weiterführende Fragen eingebracht",
    ),
    CompetencyDemo(
        "Kunst", "Gestalten", "Farbe", "Farbwirkungen beschreiben",
        "Mara beschreibt die Wirkung selbst gewählter Farben an ihrem Bild.",
        "erste Beobachtung", "06.06. · Atelier · Farbauswahl im Partnergespräch erklärt",
    ),
)


OBSERVATIONS = (
    ObservationDemo(
        "24.06.2026", "Mathematik", "Lernzeit mit Lernuhr",
        "Mara erklärte ihrem Partner volle Uhrzeiten sicher. Bei Viertelstunden verglich sie zwei Formulierungen und fragte gezielt nach.", True,
    ),
    ObservationDemo(
        "02.07.2026", "Mathematik", "Partnerarbeit Uhrzeiten",
        "Sie stellte mehrere Uhrzeiten selbstständig ein und kontrollierte ihre Notation. Beim Übertragen in die Sprachform half eine kurze Rückfrage.", True,
    ),
    ObservationDemo(
        "04.07.2026", "Sozialverhalten", "Stammgruppenrat",
        "Mara ließ einen Beitrag ausreden, fasste den Gedanken in eigenen Worten zusammen und ergänzte eine passende Idee.", True,
    ),
    ObservationDemo(
        "27.06.2026", "Sozialverhalten", "Gruppenarbeit",
        "Bei der Aufgabenverteilung brachte Mara einen Vorschlag ein. An die gemeinsame Absprache musste sie später noch einmal erinnert werden.", False,
    ),
    ObservationDemo(
        "18.06.2026", "Deutsch", "Erzählkreis",
        "Mit einer kleinen Stichwortkarte erzählte Mara ein Erlebnis in nachvollziehbarer Reihenfolge und beantwortete Rückfragen.", False,
    ),
    ObservationDemo(
        "11.06.2026", "EPU", "Projektzeit Wasser",
        "Mara formulierte zwei eigene Fragen und wählte gemeinsam mit ihrer Gruppe eine Frage für die weitere Recherche aus.", False,
    ),
    ObservationDemo(
        "08.07.2026", "Selbstständigkeit", "Freie Lernzeit",
        "Mara wählte ihr Material selbst, prüfte nach der Hälfte ihren Arbeitsstand und plante den letzten Schritt neu.", False,
    ),
)


GUIDE = {
    "strengths": (
        "Mara erklärt eigene Lösungswege gern und hört aufmerksam zu, wenn andere Kinder ihre Ideen vorstellen. "
        "Beim Arbeiten mit Uhrzeiten kontrolliert sie viele Ergebnisse bereits selbstständig."
    ),
    "development": (
        "Mara nutzt Rückfragen zunehmend gezielt. Bei verschiedenen Schreib- und Sprechweisen von Uhrzeiten braucht sie noch Zeit zum Vergleichen."
    ),
    "shared_work": (
        "Wir möchten gemeinsam überlegen, wie Mara Uhrzeit-Schreibweisen sicher verbinden und Absprachen in Gruppen eigenständig im Blick behalten kann."
    ),
    "support": (
        "Als Gesprächsgedanke: eine kleine Merkkarte zu Uhrzeit-Schreibweisen erproben und Gruppenaufgaben am Ende mit einem Partner prüfen."
    ),
}


CHARTS = (
    ChartDemo("Dokumentationsabdeckung", "Zeigt nur, in welchen ausgewählten Gesprächsbereichen Belege vorliegen.", True),
    ChartDemo("Kompetenzentwicklung", "Ordnet datierte Einzelstände ausgewählter Kompetenzen ein – ohne Trendlinie.", True),
    ChartDemo("Zeitachse ausgewählter Beobachtungsbelege", "Ordnet nur bewusst ausgewählte Beispiele chronologisch ein.", False),
)


COVERAGE_DEMO = {
    "Deutsch": (True, False, False, True),
    "Mathematik": (True, True, True, True, False, True, False),
    "EPU": (True, False, True, False),
    "Kunst": (True, False, False),
    "Arbeitsverhalten": (True, False, True),
    "Sozialverhalten": (True, True, False, True),
    "Selbstständigkeit": (True, False, True, True),
    "Lernorganisation": (False, True, False),
}


COMPETENCY_MOMENTS = {
    "Volle Stunden ablesen": (("12.03.", "mit Erinnerung"), ("08.05.", "meist selbstständig"), ("24.06.", "sicher gezeigt")),
    "Viertelstunden ablesen": (("08.05.", "mit Unterstützung"), ("24.06.", "mit wenig Unterstützung")),
    "Uhrzeiten notieren": (("08.05.", "weitgehend sicher"), ("02.07.", "sicher gezeigt")),
}
