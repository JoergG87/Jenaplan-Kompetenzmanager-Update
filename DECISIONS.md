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

## ADR-012 - Single Purpose Views

### Kontext

Während der Discovery-Phase und des UX-Entwurfs wurde festgestellt, dass Lehrkräfte je nach Situation unterschiedliche Ziele verfolgen:

- Im Unterricht soll möglichst schnell eine Beobachtung dokumentiert werden.
- Nach dem Unterricht soll die Kompetenzentwicklung analysiert werden.
- In der Klassenübersicht soll lediglich ein Schüler ausgewählt werden.

Frühere Entwürfe versuchten, mehrere Aufgaben gleichzeitig auf einer Ansicht abzubilden.

Dadurch entstand unnötige Komplexität.

### Entscheidung

Jede Ansicht des Kompetenzmanagers verfolgt genau einen primären Zweck.

Jede zusätzliche Information oder Funktion wird daran gemessen, ob sie diesen Zweck unmittelbar unterstützt.

### Konsequenzen

Klassenübersicht

- Primärer Zweck: Schüler auswählen.
- Keine Kompetenzbewertungen oder Analysen.
- Fokus auf schnelle Navigation.

Schülerprofil

- Primärer Zweck: Beobachtungen erfassen und Kompetenzentwicklung eines einzelnen Kindes verstehen.
- Einstieg über "Neue Beobachtung".

Kompetenzansicht

- Primärer Zweck: Entwicklung einer einzelnen Kompetenz nachvollziehen.

Berichte

- Primärer Zweck: Vorbereitung pädagogischer Gespräche und Dokumentationen.

Dashboard

- Primärer Zweck: Handlungsbedarf sichtbar machen.

### Begründung

Dieses Prinzip reduziert die kognitive Belastung der Lehrkraft und sorgt dafür, dass jede Ansicht klar verständlich bleibt.

Neue Funktionen dürfen einer Ansicht nur hinzugefügt werden, wenn sie den primären Zweck dieser Ansicht unterstützen.

## ADR-013

Produktentscheidung.

Beobachtungen sind die fachliche Source of Truth.

Alle weiteren Informationen werden daraus abgeleitet.

## ADR-014

Produktentscheidung.

Eine Beobachtung kann mehreren Kompetenzen zugeordnet werden.

Begründung:

Eine Präsentation, Gruppenarbeit oder Lernzielkontrolle zeigt häufig mehrere Kompetenzen gleichzeitig.

Das Datenmodell muss diese Beziehung unterstützen.

## ADR-015

Produktentscheidung.

Kompetenzstände werden historisiert.

Frühere Entwicklungsstände werden nicht überschrieben.

Lernentwicklung soll nachvollziehbar bleiben.

## ADR-016

Produktentscheidung.

Die Benutzeroberfläche orientiert sich an den Arbeitsabläufen einer Lehrkraft.

Nicht an der internen Datenstruktur.

## ADR-017

Produktentscheidung.

Die Bewertungslogik bleibt zunächst:

- `++`
- `+`
- `-`
- `--`

Sie unterstützt den Alltag der Lehrkräfte.

Die eigentliche Lernentwicklung ergibt sich jedoch aus mehreren Beobachtungen über einen längeren Zeitraum.

## ADR-018

Produktentscheidung.

Die Software schlägt Kompetenzstände vor.

Die endgültige Festlegung erfolgt durch die Lehrkraft.

## ADR-019

Produktentscheidung.

Das Schülerprofil bildet den primären Arbeitsplatz.

Nicht Dashboard oder Klassenmatrix.

## ADR-020

Produktentscheidung.

Die Benutzeroberfläche unterscheidet zwischen

- geplanten Beobachtungen
- spontanen Beobachtungen
