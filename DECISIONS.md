# Architekturentscheidungen

## ADR-001

Excel-Dateien werden ausschließlich durch Python erzeugt.

Keine manuellen Änderungen.

## ADR-002

Es werden keine Makros und kein VBA verwendet.

## ADR-003

Apple Numbers wird vollständig unterstützt.

## ADR-004

Die Projektentwicklung erfolgt sprintbasiert.

## ADR-005

Das Bewertungssystem besteht aus:

- `++`
- `+`
- `-`
- `--`

Die Darstellung erfolgt später über Ampelfarben.

## ADR-006

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs.

## ADR-007

Produktentscheidung.

Die Excel-Arbeitsmappe stellt die Benutzeroberfläche dar.

Die interne Datenstruktur darf technisch aufgebaut sein.

Die sichtbaren Arbeitsblätter orientieren sich ausschließlich an den Arbeitsabläufen der Lehrkraft.

## ADR-008

Produktentscheidung.

Die Klassenmatrix bildet zukünftig die zentrale Arbeitsansicht.

Bewertungen werden möglichst nur einmal erfasst.

Weitere Ansichten werden automatisch daraus erzeugt.

## ADR-009

Produktentscheidung.

Kompetenzen werden hierarchisch gespeichert.

Beispiel:

- Fach
- Lernbereich
- Kompetenzgruppe
- Kompetenz

## ADR-010

Produktentscheidung.

Das Datenmodell soll eine Entwicklungsdokumentation ermöglichen.

Mehrere Beobachtungen einer Kompetenz über einen längeren Zeitraum müssen zukünftig möglich sein.

## ADR-011

Produktentscheidung.

Die Software soll pädagogische Prozesse unterstützen.

Neue Funktionen werden danach bewertet, ob sie den Arbeitsalltag einer Lehrkraft vereinfachen.

## ADR-012

Produktentscheidung.

Beobachtungen sind die fachliche Source of Truth.

Alle weiteren Informationen werden daraus abgeleitet.

## ADR-013

Produktentscheidung.

Eine Beobachtung kann mehreren Kompetenzen zugeordnet werden.

Begründung:

Eine Präsentation, Gruppenarbeit oder Lernzielkontrolle zeigt häufig mehrere Kompetenzen gleichzeitig.

Das Datenmodell muss diese Beziehung unterstützen.

## ADR-014

Produktentscheidung.

Kompetenzstände werden historisiert.

Frühere Entwicklungsstände werden nicht überschrieben.

Lernentwicklung soll nachvollziehbar bleiben.

## ADR-015

Produktentscheidung.

Die Benutzeroberfläche orientiert sich an den Arbeitsabläufen einer Lehrkraft.

Nicht an der internen Datenstruktur.

## ADR-016

Produktentscheidung.

Die Bewertungslogik bleibt zunächst:

- `++`
- `+`
- `-`
- `--`

Sie unterstützt den Alltag der Lehrkräfte.

Die eigentliche Lernentwicklung ergibt sich jedoch aus mehreren Beobachtungen über einen längeren Zeitraum.

## ADR-017

Produktentscheidung.

Die Software schlägt Kompetenzstände vor.

Die endgültige Festlegung erfolgt durch die Lehrkraft.

## ADR-018

Produktentscheidung.

Das Schülerprofil bildet den primären Arbeitsplatz.

Nicht Dashboard oder Klassenmatrix.

## ADR-019

Produktentscheidung.

Die Benutzeroberfläche unterscheidet zwischen

- geplanten Beobachtungen
- spontanen Beobachtungen
