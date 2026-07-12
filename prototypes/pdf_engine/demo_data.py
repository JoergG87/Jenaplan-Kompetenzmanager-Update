"""Complete fictional output data for the isolated PDF engine prototype."""

from __future__ import annotations

from datetime import date

try:
    from .output_models import (
        ChartBlock,
        CompetencyTimelineData,
        CompetencyTimelinePoint,
        CompetencyTimelineSeries,
        DocumentationCoverageData,
        DocumentationCoverageItem,
        DocumentMetadata,
        HeadingBlock,
        ImagePlaceholderBlock,
        KeyValueBlock,
        ObservationTimelineData,
        ObservationTimelineEvent,
        ParagraphBlock,
        ReportOutputModel,
        ReportPage,
        SignatureBlock,
        SpacerBlock,
        TableBlock,
    )
except ImportError:
    from output_models import (  # type: ignore[no-redef]
        ChartBlock,
        CompetencyTimelineData,
        CompetencyTimelinePoint,
        CompetencyTimelineSeries,
        DocumentationCoverageData,
        DocumentationCoverageItem,
        DocumentMetadata,
        HeadingBlock,
        ImagePlaceholderBlock,
        KeyValueBlock,
        ObservationTimelineData,
        ObservationTimelineEvent,
        ParagraphBlock,
        ReportOutputModel,
        ReportPage,
        SignatureBlock,
        SpacerBlock,
        TableBlock,
    )


COMPETENCIES = (
    "Volle Stunden an Uhrendarstellungen ablesen.",
    "Halbe Stunden an Uhrendarstellungen ablesen.",
    "Viertelstunden an Uhrendarstellungen ablesen.",
    "Uhrzeiten minutengenau ablesen.",
    "Uhrzeiten an einer Uhr einstellen.",
    "Uhrzeiten notieren.",
    "Uhrzeiten zwischen gebräuchlichen Schreib- und Sprechweisen übertragen.",
)


EVIDENCE = (
    ObservationTimelineEvent(
        date(2026, 2, 12),
        "Lernzeit",
        "Mara liest volle und halbe Stunden an zwei unterschiedlichen Uhrendarstellungen ab.",
    ),
    ObservationTimelineEvent(
        date(2026, 4, 23),
        "Partneraufgabe",
        "Sie vergleicht Viertelstunden und korrigiert eine Abweichung nach einem Hinweis selbst.",
    ),
    ObservationTimelineEvent(
        date(2026, 8, 27),
        "Wochenplan",
        "Sie notiert vorgegebene Uhrzeiten und liest die gewählte Schreibweise passend vor.",
    ),
    ObservationTimelineEvent(
        date(2026, 11, 19),
        "Einzelarbeit",
        "Sie bestimmt eine minutengenaue Uhrzeit mit einer Hilfskarte und stellt sie an der Lernuhr ein.",
    ),
)


def _series(label: str, *points: tuple[date, str]) -> CompetencyTimelineSeries:
    return CompetencyTimelineSeries(
        label=label,
        points=tuple(CompetencyTimelinePoint(day, state) for day, state in points),
    )


def build_demo_report() -> ReportOutputModel:
    metadata = DocumentMetadata(
        document_title="Lernentwicklungsbericht",
        student_name="Mara Beispielkind",
        group_name="Sonnenbogen",
        period="Schuljahr 2026",
        teacher_name="Laura Musterlehrerin",
        school_name="Jenaplan-Schule Beispielstadt",
        created_on=date(2026, 12, 18),
        header_text="Jenaplan-Schule Beispielstadt | Lernentwicklungsbericht",
        footer_text="Vertrauliches pädagogisches Dokument | Fiktive Prototypdaten",
    )

    coverage = DocumentationCoverageData(
        title="Dokumentationsabdeckung",
        items=(
            DocumentationCoverageItem("Zeit-Kompetenzen", 6, 7),
            DocumentationCoverageItem("ausgewählte Beobachtungsbelege", 4, 7),
        ),
        note=(
            "Die Darstellung zeigt ausschließlich, zu wie vielen vorgesehenen Elementen "
            "Dokumentation vorliegt. Sie ist keine Leistungsbewertung."
        ),
    )

    competency_timeline = CompetencyTimelineData(
        title="Datierte Kompetenzstände",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        series=(
            _series(COMPETENCIES[0], (date(2026, 2, 12), "beobachtet"), (date(2026, 8, 27), "bestätigt")),
            _series(COMPETENCIES[1], (date(2026, 2, 12), "beobachtet"), (date(2026, 8, 27), "bestätigt")),
            _series(COMPETENCIES[2], (date(2026, 4, 23), "beobachtet"), (date(2026, 11, 19), "beobachtet")),
            _series(COMPETENCIES[3], (date(2026, 11, 19), "mit Unterstützung")),
            _series(COMPETENCIES[4], (date(2026, 2, 12), "beobachtet"), (date(2026, 11, 19), "beobachtet")),
            _series(COMPETENCIES[5], (date(2026, 8, 27), "beobachtet")),
            _series(COMPETENCIES[6]),
        ),
        state_colors=(
            ("beobachtet", "#2A7774"),
            ("bestätigt", "#315F7D"),
            ("mit Unterstützung", "#6C7D8A"),
        ),
        note=(
            "Jeder Marker entspricht einem datierten, bereits vorbereiteten Stand. "
            "Es gibt keine Trendlinie, Zusammenfassung oder automatische Interpretation."
        ),
    )

    observation_timeline = ObservationTimelineData(
        title="Zeitachse der ausgewählten Belege",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        events=EVIDENCE,
        note="Die Auswahl ist beispielhaft und erhebt keinen Anspruch auf Vollständigkeit.",
    )

    overall_text = (
        "Mara gestaltet ihr Lernen zunehmend selbstständig und bringt eigene Fragen aufmerksam "
        "in gemeinsame Arbeitsphasen ein. Sie nutzt Rückmeldungen, um Vorgehensweisen zu prüfen, "
        "und kann immer häufiger benennen, welche Unterstützung ihr beim nächsten Schritt hilft."
        "\n\n"
        "Besonders tragfähig sind ruhige Gesprächssituationen, verlässliche Arbeitsstrukturen "
        "und Aufgaben, in denen sie eigene Lösungswege sichtbar machen kann. Bei umfangreicheren "
        "Aufträgen hilft ihr ein kurzer gemeinsamer Blick auf Ziel und Reihenfolge. Anschließend "
        "arbeitet sie konzentriert weiter und hält Zwischenergebnisse häufiger selbstständig fest."
        "\n\n"
        "Dieser Beispieltext ist bewusst länger angelegt. Er validiert Absatzaufbau, automatischen "
        "Zeilenumbruch und großzügigen Weißraum, ohne Beobachtungen auszuwerten oder Aussagen "
        "automatisch aus Daten abzuleiten."
    )

    pages = (
        ReportPage(
            label="Deckblatt",
            is_cover=True,
            blocks=(
                SpacerBlock(13),
                ImagePlaceholderBlock("LOGO"),
                SpacerBlock(17),
                HeadingBlock(metadata.document_title, level=0),
                ParagraphBlock("Pädagogischer Bericht", emphasis="lead"),
                SpacerBlock(18),
                HeadingBlock(metadata.student_name, level=1),
                KeyValueBlock(
                    (
                        ("Zeitraum", metadata.period),
                        ("Stammgruppe", metadata.group_name),
                        ("Lehrkraft", metadata.teacher_name),
                        ("Schule", metadata.school_name),
                    )
                ),
            ),
        ),
        ReportPage(
            label="Pädagogischer Gesamtblick",
            blocks=(
                HeadingBlock("Pädagogischer Gesamtblick"),
                ParagraphBlock("Ein manueller, pädagogisch verantworteter Beispieltext.", emphasis="lead"),
                SpacerBlock(6),
                ParagraphBlock(overall_text),
            ),
        ),
        ReportPage(
            label="Mathematik",
            blocks=(
                HeadingBlock("Mathematik"),
                KeyValueBlock((("Kompetenzbereich", "Größen und Messen"), ("Thema", "Zeit"))),
                SpacerBlock(5),
                ParagraphBlock(
                    "Sieben getrennte, konkrete Kompetenzen - ohne Sammelkompetenz Zeit.",
                    emphasis="lead",
                ),
                TableBlock(
                    headers=("Nr.", "Konkrete Kompetenz"),
                    rows=tuple((str(index), competency) for index, competency in enumerate(COMPETENCIES, 1)),
                    column_weights=(0.10, 0.90),
                ),
            ),
        ),
        ReportPage(
            label="Entwicklungsdarstellung Mathematik",
            blocks=(
                HeadingBlock("Entwicklungsdarstellung Mathematik"),
                ParagraphBlock(
                    "Neutrale Darstellungen vorbereiteter Ausgabedaten - ohne Score, Ampel oder Deutung.",
                    emphasis="lead",
                ),
                ChartBlock(coverage),
                SpacerBlock(4),
                ChartBlock(competency_timeline),
            ),
        ),
        ReportPage(
            label="Beobachtungsbelege",
            blocks=(
                HeadingBlock("Beobachtungsbelege"),
                ChartBlock(observation_timeline),
                SpacerBlock(6),
                TableBlock(
                    headers=("Datum", "Kontext", "Kurze Notiz"),
                    rows=tuple(
                        (event.observed_on.strftime("%d.%m.%Y"), event.context, event.note)
                        for event in EVIDENCE
                    ),
                    column_weights=(0.18, 0.22, 0.60),
                ),
            ),
        ),
        ReportPage(
            label="Ziele und Unterstützung",
            blocks=(
                HeadingBlock("Ziele und Unterstützung"),
                HeadingBlock("Nächste Lernschritte", level=2),
                TableBlock(
                    headers=("Ziel", "Woran es im Alltag sichtbar wird"),
                    rows=(
                        ("Uhrzeiten übertragen", "Mara verbindet Darstellung, Schreibweise und Sprechweise in vertrauten Aufgaben."),
                        ("Arbeitsschritte planen", "Mara notiert vor längeren Aufgaben zwei überschaubare Zwischenschritte."),
                    ),
                    column_weights=(0.30, 0.70),
                ),
                SpacerBlock(10),
                HeadingBlock("Vereinbarte Unterstützung", level=2),
                TableBlock(
                    headers=("Beteiligte", "Unterstützung"),
                    rows=(
                        ("Schule", "Klare Zwischenziele, ruhiger Arbeitsplatz und kurze Rückschau am Ende längerer Lernzeiten."),
                        ("Lehrkraft", "Strategiefragen anbieten, ohne den Lösungsweg vorwegzunehmen."),
                        ("Kind", "Hilfekarte nutzen und bei Unklarheiten eine konkrete Frage notieren."),
                    ),
                    column_weights=(0.22, 0.78),
                ),
            ),
        ),
        ReportPage(
            label="Abschluss",
            blocks=(
                HeadingBlock("Abschluss"),
                ParagraphBlock(
                    "Dieser Lernentwicklungsbericht hält ausgewählte Inhalte des Schuljahres fest. "
                    "Die endgültige fachliche Prüfung und Freigabe sind nicht Bestandteil des Prototyps.",
                ),
                SpacerBlock(12),
                KeyValueBlock(
                    (
                        ("Datum", metadata.created_on.strftime("%d.%m.%Y")),
                        ("Freigabe", "Platzhalter - späterer Produktentscheid erforderlich"),
                    )
                ),
                SpacerBlock(35),
                SignatureBlock(("Lehrkraft", "Schulleitung", "Erziehungsberechtigte")),
            ),
        ),
    )
    return ReportOutputModel(metadata=metadata, pages=pages)
