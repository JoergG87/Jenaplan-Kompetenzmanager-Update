"""Clearly fictional, in-memory demo content for the report UX prototype."""

from __future__ import annotations


DEMO_CONTEXT = {
    "student_name": "Mara Beispielkind",
    "group_name": "Stammgruppe Sonnenbogen",
    "report_type": "Lernentwicklungsbericht · Halbjahr",
    "period_from": "01.08.2026",
    "period_to": "31.01.2027",
    "teacher_name": "Laura Musterlehrerin",
    "overall": (
        "Mara beteiligt sich aufmerksam am gemeinsamen Lernen und bringt eigene Ideen "
        "zunehmend klar in Arbeitsphasen ein. Sie nutzt Rückmeldungen, um Vorgehensweisen "
        "zu prüfen, und kann immer häufiger benennen, was ihr beim Lernen hilft. Besonders "
        "tragfähig sind ruhige Gesprächssituationen und Aufgaben, in denen sie eigene "
        "Lösungswege sichtbar machen kann."
    ),
    "next_steps": (
        "Mara plant überschaubare Arbeitsschritte zunehmend selbstständig und hält kurze "
        "Zwischenergebnisse fest. In neuen Lernsituationen soll sie weiterhin darin "
        "bestärkt werden, Rückfragen früh zu formulieren."
    ),
    "closing": (
        "Im Berichtszeitraum hat Mara vielfältige Lerngelegenheiten genutzt. Die nächsten "
        "Schritte knüpfen an ihre sorgfältige Arbeitsweise und ihre wachsende Sicherheit "
        "im Austausch über eigene Lösungswege an."
    ),
    "internal_note": (
        "Nur intern: Beim nächsten Teamgespräch die vereinbarten ruhigen Arbeitsplätze "
        "und die Materialauswahl abstimmen."
    ),
}


SUBJECTS = {
    "Deutsch": {
        "summary": "12 Beobachtungen · 9 konkrete Kompetenzen dokumentiert · 2 bestätigte Stände",
        "areas": ["Lesen", "Schreiben", "Sprechen und Zuhören"],
        "competencies": [
            ("Informationen in kurzen Sachtexten gezielt auffinden", "Bestätigt · sicher"),
            ("eigene Texte mit einer einfachen Planung strukturieren", "Beobachtet · zunehmend sicher"),
            ("Gesprächsbeiträge anderer aufgreifen", "Beobachtet · mit wenig Unterstützung"),
        ],
        "evidence": [
            "18.09. · Lesekonferenz – passende Textstellen markiert und begründet",
            "07.11. · Schreibwerkstatt – Gliederung vor dem ersten Entwurf genutzt",
            "12.01. · Erzählkreis – an einen vorherigen Beitrag angeknüpft",
        ],
        "strengths": (
            "Mara liest kurze Sachtexte ausdauernd und findet gezielt Informationen, wenn "
            "die Fragestellung klar eingegrenzt ist. Im Gespräch hört sie aufmerksam zu."
        ),
        "development": (
            "Beim Schreiben nutzt Mara erste Planungsschritte verlässlicher. Sie überarbeitet "
            "ausgewählte Textstellen nach Rückmeldung und kann ihre Änderungen begründen."
        ),
        "support": (
            "Bei längeren Schreibvorhaben helfen ihr sichtbare Zwischenziele und ein kurzer "
            "Austausch vor dem Formulieren."
        ),
        "goals": (
            "Eigene Texte vor dem Schreiben gliedern und beim Überarbeiten gezielt auf "
            "Verständlichkeit und Satzanfänge achten."
        ),
        "coverage": [("Lesen", 6, 7), ("Schreiben", 4, 7), ("Sprechen & Zuhören", 3, 5)],
        "timeline_title": "Schreiben · Texte planen und überarbeiten",
        "timeline": [
            ("Sep", 1, "observation"),
            ("Nov", 2, "observation"),
            ("Jan", 2, "confirmed"),
        ],
        "area_timelines": [
            [("18.09.2026", 1, "observation"), ("07.11.2026", 2, "observation"), ("12.01.2027", 2, "confirmed")],
            [("07.11.2026", 1, "observation"), ("12.01.2027", 2, "observation")],
            [("12.01.2027", 1, "observation")],
        ],
        "density": [("Aug", 1), ("Sep", 3), ("Okt", 1), ("Nov", 3), ("Dez", 1), ("Jan", 3)],
    },
    "Mathematik": {
        "summary": "15 Beobachtungen · 11 konkrete Kompetenzen dokumentiert · 3 bestätigte Stände",
        "areas": ["Größen und Messen", "Zahlen und Operationen", "Raum und Form"],
        "competencies": [
            ("volle Stunden an Uhrendarstellungen ablesen", "Bestätigt · sicher"),
            ("halbe Stunden an Uhrendarstellungen ablesen", "Bestätigt · sicher"),
            ("Viertelstunden an Uhrendarstellungen ablesen", "Beobachtet · zunehmend sicher"),
            ("Uhrzeiten minutengenau ablesen", "Beobachtet · mit Unterstützung"),
            ("Uhrzeiten einstellen", "Beobachtet · zunehmend sicher"),
            ("Uhrzeiten notieren", "Beobachtet · zunehmend sicher"),
            ("Schreib- und Sprechweisen übertragen", "Beobachtet · mit Unterstützung"),
        ],
        "evidence": [
            "09.09. · Tagesplan – volle und halbe Stunden sicher eingestellt",
            "21.10. · Lernzeit – Viertelstunden an drei Uhrendarstellungen verglichen",
            "02.12. · Partneraufgabe – Uhrzeiten notiert und vorgelesen",
            "19.01. · Wochenplan – minutengenaue Uhrzeiten mit Hilfskarte bestimmt",
        ],
        "strengths": (
            "Mara arbeitet bei Aufgaben zu Zeitvorstellungen sorgfältig und prüft ihre "
            "Ergebnisse an der Uhrendarstellung. Volle und halbe Stunden liest sie sicher ab."
        ),
        "development": (
            "Im Verlauf des Halbjahres hat Mara ihre Strategien beim Einstellen und Notieren "
            "von Uhrzeiten erweitert. Viertelstunden erkennt sie in vertrauten Darstellungen "
            "zunehmend selbstständig."
        ),
        "support": (
            "Beim minutengenauen Ablesen und beim Übertragen zwischen Schreib- und "
            "Sprechweise benötigt Mara noch strukturierende Fragen und Anschauungsmaterial."
        ),
        "goals": (
            "Minutenabstände an analogen Uhren sicher nutzen und Uhrzeiten zwischen "
            "Darstellung, Schreibweise und Sprechweise übertragen."
        ),
        "coverage": [("Größen und Messen", 7, 10), ("Zahlen und Operationen", 5, 8), ("Raum und Form", 3, 6)],
        "timeline_title": "Größen und Messen · Zeit",
        "timeline": [
            ("Sep", 1, "observation"),
            ("Okt", 2, "observation"),
            ("Dez", 2, "confirmed"),
            ("Jan", 3, "observation"),
        ],
        "area_timelines": [
            [("09.09.2026", 1, "observation"), ("21.10.2026", 2, "observation"), ("02.12.2026", 2, "confirmed"), ("19.01.2027", 3, "observation")],
            [("21.10.2026", 1, "observation"), ("19.01.2027", 2, "confirmed")],
            [("19.01.2027", 1, "observation")],
        ],
        "density": [("Aug", 1), ("Sep", 4), ("Okt", 3), ("Nov", 2), ("Dez", 2), ("Jan", 3)],
    },
    "EPU": {
        "summary": "7 Beobachtungen · 5 konkrete Kompetenzen dokumentiert · kein bestätigter Stand",
        "areas": ["Mensch und Gemeinschaft", "Natur und Umwelt"],
        "competencies": [
            ("Beobachtungen zu einem Sachthema geordnet festhalten", "Beobachtet · zunehmend sicher"),
            ("Ergebnisse einer Erkundung verständlich vorstellen", "Beobachtet · mit Unterstützung"),
        ],
        "evidence": [
            "30.09. · Bacherkundung – Beobachtungen mit Skizzen festgehalten",
            "24.11. · Präsentation – zwei Ergebnisse der Gruppe vorgestellt",
        ],
        "strengths": "Mara beobachtet genau und bringt passende Fragen in Erkundungen ein.",
        "development": "Ihre Aufzeichnungen werden übersichtlicher und enthalten häufiger eigene Beschriftungen.",
        "support": "Für Präsentationen helfen ihr kurze Stichwortkarten und ein klarer Redeauftrag.",
        "goals": "Erkundungsergebnisse ordnen und mit eigenen Worten zusammenhängend vorstellen.",
        "coverage": [("Mensch & Gemeinschaft", 3, 6), ("Natur & Umwelt", 2, 5)],
        "timeline_title": "Natur und Umwelt · Ergebnisse vorstellen",
        "timeline": [("Sep", 1, "observation")],
        "area_timelines": [
            [("30.09.2026", 2, "observation")],
            [("24.11.2026", 1, "observation")],
        ],
        "density": [("Aug", 0), ("Sep", 2), ("Okt", 1), ("Nov", 2), ("Dez", 1), ("Jan", 1)],
    },
    "Sozialkompetenz": {
        "summary": "9 Beobachtungen · 4 konkrete Kompetenzen dokumentiert · 1 bestätigter Stand",
        "areas": ["Zusammenarbeiten", "Verantwortung übernehmen"],
        "competencies": [
            ("Absprachen in einer Arbeitsgruppe einhalten", "Bestätigt · zunehmend sicher"),
            ("eigene Anliegen respektvoll formulieren", "Beobachtet · zunehmend sicher"),
        ],
        "evidence": [
            "16.09. · Gruppenarbeit – Materialdienst verlässlich übernommen",
            "08.12. · Klassenrat – eigenes Anliegen ruhig formuliert",
        ],
        "strengths": "Mara nimmt andere Perspektiven aufmerksam wahr und übernimmt verlässlich vereinbarte Aufgaben.",
        "development": "Eigene Anliegen bringt sie in vertrauten Gruppen zunehmend klar zur Sprache.",
        "support": "In unübersichtlichen Situationen helfen ihr kurze Absprachen zu Rollen und Reihenfolge.",
        "goals": "In Gruppen früh benennen, welche Aufgabe sie übernimmt und wann sie Unterstützung benötigt.",
        "coverage": [("Zusammenarbeiten", 3, 5), ("Verantwortung", 2, 4)],
        "timeline_title": "Zusammenarbeiten · Absprachen einhalten",
        "timeline": [("Sep", 2, "observation"), ("Dez", 2, "confirmed")],
        "area_timelines": [
            [("16.09.2026", 2, "observation"), ("08.12.2026", 2, "confirmed")],
            [("08.12.2026", 2, "observation")],
        ],
        "density": [("Aug", 0), ("Sep", 2), ("Okt", 1), ("Nov", 2), ("Dez", 3), ("Jan", 1)],
    },
}


RATING_LEVELS = [
    "mit Unterstützung",
    "zunehmend sicher",
    "sicher",
    "sicher und übertragbar",
]
