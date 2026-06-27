# Architekturentscheidungen

## ADR-001

Excel-Dateien werden ausschließlich durch Python erzeugt.

Keine manuellen Änderungen.

## ADR-002

VBA ist ausschließlich für UI-Aufgaben freigegeben.

Keine fachliche Logik in VBA.

## ADR-003

Microsoft Excel für macOS ist die verbindliche Zielplattform.

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

Neue Funktionen dürfen die Hauptaufgabe einer Ansicht nicht verwässern.

### Konsequenzen

Klassenübersicht

- Primärer Zweck: Schüler schnell finden und auswählen.
- Keine Kompetenzbewertungen oder Analysen.
- Fokus auf schnelle Navigation.

Schülerprofil

- Primärer Zweck: Beobachtungen erfassen und Kompetenzentwicklung eines einzelnen Kindes verstehen.
- Einstieg über "Neue Beobachtung".

Kompetenzansicht

- Primärer Zweck: Entwicklung einer einzelnen Kompetenz nachvollziehen.

Klassenverwaltung

- Primärer Zweck: Schüler verwalten.
- Schüler hinzufügen, bearbeiten und archivieren.

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

## ADR-021 - UI-Technologie für UX-Prototypen ab v0.2

### Kontext

Der erste UX-Prototyp hat gezeigt, dass rein hyperlinkbasierte Arbeitsmappen für die nächste UX-Generation nicht ausreichen.

Die zweite Generation des UX-Prototyps wird auf Microsoft Excel für macOS ausgerichtet.

### Entscheidung

Python bleibt verantwortlich für:

- Workbook-Erzeugung
- Datenstruktur
- Styles
- Generierung
- Build-Artefakte

VBA übernimmt zukünftig ausschließlich:

- Navigation
- Dialoge
- Benutzerinteraktion
- UserForms

Fachliche Logik verbleibt vollständig im Python- und Datenmodell.

### Konsequenzen

VBA-Code darf keine fachlichen Regeln, Berechnungen, Kompetenzlogik oder Datenmodellentscheidungen enthalten.

Die Trennung zwischen Python-Generator, fachlichem Kern, UI-Screens und späteren VBA-Bausteinen wird vorbereitet, aber in Sprint 3.0 noch nicht groß refaktoriert.

Der bestehende Prototyp v0.1 bleibt als Referenz erhalten. Neue Arbeiten erfolgen ab v0.2.

## ADR-022 - Klassenübersicht als Einstieg

### Kontext

Sprint 3.1 und Sprint 3.1a haben die Klassenübersicht als erste Ansicht der zweiten UX-Prototyp-Generation konkretisiert.

Das Review mit Product Owner und Jenaplan-Lehrkraft hat bestätigt, dass die Klassenübersicht im Unterricht nur dann hilfreich ist, wenn sie schnell erfassbar bleibt und nicht zur Analyse- oder Verwaltungsansicht wird.

### Entscheidung

Die Klassenübersicht ist ausschließlich der Einstieg in den Arbeitsablauf.

Ihre Aufgabe besteht darin:

- Schüler schnell zu finden
- Schüler auszuwählen
- anschließend in das Schülerprofil zu wechseln

Die Klassenübersicht ist ausdrücklich:

- kein Dashboard
- keine Verwaltungsansicht
- keine Analyseansicht
- keine Auswertungsseite

### Konsequenzen

Die Klassenübersicht enthält keine Kompetenzstände, Bewertungen, Analysen, Berichte, Statistiken oder Verwaltungsfunktionen.

Die gesamte Schülerkarte ist die spätere Klickfläche für den Wechsel ins Schülerprofil.

Ein separater Button innerhalb der Karte wird nicht verwendet.

## ADR-023 - Sortierung und Datenquelle der Klassenübersicht

### Kontext

Lehrkräfte suchen Kinder im Unterricht überwiegend über den Vornamen.

Die Klassenübersicht soll aus vorhandenen Schülerdaten entstehen und nicht manuell gepflegt werden.

### Entscheidung

Die Standardreihenfolge der Schüler in der Klassenübersicht erfolgt alphabetisch nach Vorname.

Die Klassenübersicht wird vollständig aus den vorhandenen Schülerdaten generiert.

### Konsequenzen

Schülerkarten werden nicht manuell gepflegt.

Wenn Schüler in der Klassenverwaltung hinzugefügt, bearbeitet, archiviert oder gelöscht werden, aktualisiert sich die Klassenübersicht automatisch aus diesen Daten.

Die Klassenübersicht besitzt keine eigene Geschäftslogik.

Alle Änderungen an Schülerdaten erfolgen über die Klassenverwaltung.

## ADR-024 - Klassenverwaltung als separater Bereich

### Kontext

Die Klassenübersicht soll im Unterricht schnelles Finden und Auswählen ermöglichen.

Verwaltungsfunktionen würden diesen Zweck verwässern.

### Entscheidung

Die Verwaltung von Schülern erfolgt künftig in einem separaten Bereich `Klassenverwaltung`.

Dort können Lehrkräfte:

- Schüler hinzufügen
- Schüler bearbeiten
- Schüler archivieren

### Konsequenzen

Die Klassenübersicht enthält bewusst keine Verwaltungsfunktionen.

Die Klassenverwaltung ist der einzige UI-Ort für Änderungen an Schülerdaten.

## ADR-025 - Design Freeze Klassenübersicht v0.2

### Kontext

Die Klassenübersicht wurde in Sprint 3.1 erstellt und in Sprint 3.1a auf Grundlage eines UX-Reviews für den Unterricht optimiert.

Das aktuelle Layout gilt als Referenzdesign.

### Entscheidung

Bis zu einer ausdrücklichen Product-Owner-Entscheidung dürfen folgende Eigenschaften der Klassenübersicht nicht verändert werden:

- Desktop-Anmutung
- Kartenlayout
- Kartenhöhe
- Informationshierarchie
- Farbkonzept
- Typografie
- 4-spaltiges Raster
- kompakte Darstellung für Klassen bis mindestens 28 Schüler

### Konsequenzen

Designänderungen erfolgen ausschließlich nach:

- UX-Review
- Product-Owner-Freigabe
- anschließender Implementierung
