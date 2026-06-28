# Projektdokumentation: Jenaplan-Kompetenzmanager

## Projektziel

Der Jenaplan-Kompetenzmanager ist ein professionelles Python-Projekt zur strukturierten Verwaltung, Auswertung und späteren Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

Das Projekt stellt die Grundlage für eine Excel-basierte Arbeitsmappe für Microsoft Excel auf macOS bereit. Microsoft Excel für macOS ist die verbindliche Zielplattform.

Python erzeugt Workbook, Datenmodell, UI-Projektionen, Styles, Berichte, Fachlogik und Build-Artefakte. Der VBA-Seed wurde technisch validiert; nach Stabilisierung des VBA-Frameworks wird `.xlsm` als Zielartefakt vorbereitet. Bis dahin bleibt `.xlsx` der Fallback.

VBA übernimmt ausschließlich Navigation, Buttons, Dialoge, Benutzerinteraktion und UserForms.

Fachliche Logik wandert nicht nach VBA. Das Datenmodell bleibt vollständig unabhängig von VBA.

Sprint 0 dient ausschließlich dem Aufbau des technischen und dokumentarischen Fundaments. Es wird noch keine produktive Excel-Datei erzeugt.

## Leitbild

Das Projekt soll fachlich nachvollziehbar, technisch wartbar und langfristig erweiterbar sein.

Die Entwicklung folgt diesen Grundsätzen:

- Pädagogische Fachlichkeit steht vor technischer Komplexität.
- Daten werden strukturiert, nachvollziehbar und konsistent verarbeitet.
- Jede Version bleibt lauffähig.
- Änderungen werden dokumentiert und versioniert.
- Microsoft Excel für macOS ist die verbindliche Zielplattform.

## Pädagogische Produktvision

### Zielgruppe

Der Kompetenzmanager richtet sich an Lehrkräfte an Jenaplan-Grundschulen und unterstützt die Kompetenzbeobachtung nach dem Thüringer Lehrplan.

Das Projekt verfolgt das Ziel, den Dokumentationsaufwand zu reduzieren und gleichzeitig eine qualitativ hochwertige Kompetenzdokumentation zu ermöglichen.

### Pädagogische Leitlinien

- Beobachtung vor Bewertung.
- Bewertungen entstehen aus dokumentierten Beobachtungen.
- Entwicklung ist wichtiger als Momentaufnahmen.
- Dokumentation soll den Unterricht unterstützen und nicht behindern.
- Kompetenzen werden lehrplanorientiert organisiert.
- Mehrfache Dateneingaben sollen vermieden werden.

### Arbeitsweise der Lehrkraft

Die tägliche Arbeit erfolgt überwiegend über Stammgruppen- und Schüleransichten.

Weitere Ansichten wie Schülerprofil, Stammgruppenübersicht, Kursübersicht, Berichte und Kompetenzbögen entstehen automatisch aus denselben Daten.

Die Stammgruppenübersicht dient als Einstieg in den Arbeitsablauf. Sie hilft dabei, einen Schüler innerhalb einer Stammgruppe schnell zu finden, auszuwählen und anschließend in das Schülerprofil zu wechseln.

Die Stammgruppenübersicht ist kein Dashboard, keine Verwaltungsansicht, keine Analyseansicht und keine Auswertungsseite.

Für den Unterricht darf die Stammgruppenübersicht zusätzlich einen Schnellzugriff `Neue Beobachtung` anbieten. Dieser arbeitet immer im Kontext des ausgewählten Schülers und öffnet denselben zentralen Beobachtungsdialog wie das Schülerprofil.

## Fachliches Domänenmodell

### Der Kompetenzmanager ist ein Lernentwicklungsmanager.

Nicht einzelne Bewertungen stehen im Mittelpunkt.

Im Mittelpunkt steht die Lernentwicklung der Schülerinnen und Schüler.

Bewertungen sind lediglich ein Ergebnis dokumentierter Beobachtungen.

### Beobachtungen sind die fachliche Quelle aller Informationen.

Beobachtungen bilden die Grundlage für

- Kompetenzstände
- Schülerprofile
- Lernentwicklungsberichte
- Dashboards
- Auswertungen

### Kompetenzentwicklung

Kompetenzen entwickeln sich über einen längeren Zeitraum.

Das System muss deshalb Kompetenzverläufe speichern können.

Nicht nur den aktuellen Stand.

## Architektur

Das Projekt ist modular aufgebaut.

- `build.py` ist der zentrale Einstiegspunkt für spätere Build-Prozesse.
- `src/workbook.py` ist für die spätere Arbeitsmappen-Erzeugung vorgesehen.
- `src/core/` ist für die spätere Trennung fachlicher Python-Logik vorgesehen.
- `src/ui/` ist für die spätere Trennung UI-naher Python-Generatoren vorgesehen.
- `src/ui/screens/` ist für künftige Bildschirm-Generatoren vorgesehen.
- `src/dashboard.py` ist für das spätere Dashboard vorgesehen.
- `src/students.py` ist für Schülerdaten vorgesehen.
- `src/competencies.py` ist für Kompetenzdaten vorgesehen.
- `src/assessments.py` ist für Bewertungen vorgesehen.
- `src/reports.py` ist für Berichte vorgesehen.
- `src/settings.py` ist für zentrale Einstellungen vorgesehen.
- `src/styles.py` ist für visuelle Formatierungen vorgesehen.
- `data/` enthält Eingabedaten und Konfigurationen.
- `docs/` enthält fachliche Begleitdokumentation.
- `UX_BLUEPRINT.md` beschreibt die verbindliche UX-Grundlage für den ersten Prototyp.
- `docs/DESIGN_SYSTEM.md` beschreibt das freigegebene Design-System als verbindliche Referenz für zukünftige Ansichten.
- `vba/` enthält versionierbare VBA-Quellen für die spätere Interaktionsschicht.
- `seeds/` enthält validierte Seed-Arbeitsmappen für das spätere `.xlsm`-Packaging.
- `output/` ist für später generierte Dateien vorgesehen.
- `tests/` ist für automatisierte Tests vorgesehen.
- `assets/` ist für statische Ressourcen vorgesehen.
- `BACKLOG.md` sammelt zukünftige Produktideen und Erweiterungen.
- `DISCOVERY.md` dokumentiert fachliche Erkenntnisse aus Anwenderinterviews und Discovery-Workshops.

Die Architektur vermeidet feste Zellreferenzen. Stattdessen sollen strukturierte Daten, eindeutige IDs und wiederverwendbare Builder-Komponenten verwendet werden.

Die Stammgruppenübersicht und die Kursübersicht besitzen keine eigene Geschäftslogik. Sie stellen vorhandene Schülerdaten dar und werden aus diesen Daten generiert. Änderungen an Schülerdaten erfolgen künftig ausschließlich über die Schülerverwaltung.

## Technischer Stack

- Python 3.11 oder neuer
- `openpyxl` für die spätere Excel-Erzeugung
- `pandas` für strukturierte Datenverarbeitung
- `pillow` für spätere Bild- oder Asset-Verarbeitung
- Markdown für Projektdokumentation
- CSV und JSON für strukturierte Eingabe- und Konfigurationsdaten

## Rollen

- Product Owner: Gibt neue Funktionen, fachliche Änderungen und Änderungen am Datenmodell frei.
- Entwicklung: Implementiert die freigegebenen Funktionen nach Projektregeln.
- Fachliche Review: Prüft pädagogische Verständlichkeit, Bewertungssystem und Lehrplanbezug.
- Technische Review: Prüft Wartbarkeit, Kompatibilität und Lauffähigkeit.

## Entwicklungsprinzipien

- Keine Implementierung ohne fachliche Freigabe.
- Keine Änderung am Datenmodell ohne Rücksprache.
- Jede Änderung wird im Changelog dokumentiert.
- Jede Version muss lauffähig bleiben.
- Funktionen werden sprintbasiert geplant und umgesetzt.
- Generierte Excel-Dateien werden nicht manuell verändert.
- Die spätere Darstellung wird für Microsoft Excel auf macOS ausgelegt.
- Fachliche Logik verbleibt vollständig im Python- und Datenmodell.
- VBA darf ausschließlich UI-Aufgaben wie Navigation, Buttons, Dialoge, Benutzerinteraktion und UserForms übernehmen.
- Das Datenmodell ist Source of Truth für fachliche Daten.
- Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.
- Strukturierte Tabellen und eindeutige IDs haben Vorrang vor festen Zellpositionen.
- Jede Ansicht besitzt genau eine Hauptaufgabe.
- Neue Funktionen dürfen die Hauptaufgabe einer Ansicht nicht verwässern.
- Eine Funktion besitzt genau eine Implementierung, darf aber mehrere Einstiegspunkte besitzen.

### Standard-Reihenfolge jeder Implementierung

1. Vision
2. Product Discovery
3. Produktentscheidung
4. Datenmodell-Review
5. Architektur-Review
6. UX-Review
7. Prompt-Review
8. Implementierung
9. Technical Review
10. Test
11. Commit

## Versionierung

Das Projekt verwendet eine produktorientierte Versionsfolge.

- Version 3.1 bildet das Fundament.
- Versionen 3.2 bis 3.6 erweitern das Projekt schrittweise um fachliche und technische Funktionen.
- Version 4.0 ist als produktive Version vorgesehen.

UX-Prototypen besitzen eine eigene Versionierung.

Der erste Prototyp bleibt als `Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx` erhalten.

Die zweite Generation des UX-Prototyps wird als `Jenaplan_UX_Prototype_v0.2.xlsx` erzeugt.

Die v3.x-Linie beschreibt weiterhin den technischen Generator und den bisherigen Entwicklungsstand.

Änderungen werden in `CHANGELOG.md` dokumentiert. Grundsätzliche Architekturentscheidungen werden in `DECISIONS.md` festgehalten.

## Roadmap

Die verbindliche Roadmap befindet sich in `ROADMAP.md`.

Aktuelle Planung:

- Sprint 3.0: Architekturwechsel auf Microsoft Excel für macOS
- Sprint 3.1: Klassenübersicht als frühere Bezeichnung der heutigen Stammgruppenübersicht
- Sprint 3.2: Schülerprofil
- Sprint 3.3a: Architektur konsolidieren
- Weitere Produktbereiche erst nach fachlicher Freigabe und Review

## Bewertungssystem

Das Bewertungssystem wird in einem später freigegebenen Sprint fachlich ausgearbeitet.

Die Architekturentscheidung für das Bewertungssystem ist bereits festgelegt:

- `++`
- `+`
- `-`
- `--`

Die visuelle Darstellung erfolgt später über Ampelfarben. Die Bewertungssymbole sind fachliche Datenwerte und dürfen nicht durch reine Farbwerte ersetzt werden.

## Datenmodell

Das Datenmodell basiert auf strukturierten Datenquellen in `data/`.

Aktuelle Dateien:

- `data/competencies.csv` für Kompetenzdaten
- `data/colors.json` für Farbdefinitionen
- `data/config.json` für Projektkonfiguration

Das Datenmodell ist die fachliche Grundlage des Projekts.

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs. Das Datenmodell darf nicht ohne Rücksprache mit dem Product Owner geändert werden.

Neue UI-Elemente, Hilfstabellen, Formeln, VBA-Routinen und Screens dürfen das Datenmodell niemals umgehen. Alle Ansichten sind Projektionen des Datenmodells.

Die Domänensprache ersetzt `Klasse` durch `Stammgruppe`. Jeder Schüler gehört genau einer Stammgruppe und genau einem Kurs an. Der Kurs beschreibt den Jahrgang, die Stammgruppe beschreibt die organisatorische Zugehörigkeit.

Die zentralen Entitäten für Schülerzuordnung sind:

- Student mit `student_id`, Vorname, Nachname, `stammgruppe_id`, `kurs_id`
- Stammgruppe mit `stammgruppe_id`, Name
- Kurs mit `kurs_id`, Name und optionaler Farbe für spätere UI

Die Standardreihenfolge der Schüler in der Stammgruppenübersicht erfolgt alphabetisch nach Vorname. Diese Sortierung gilt als Projektstandard, weil Lehrkräfte Kinder im Unterricht überwiegend mit dem Vornamen suchen und ansprechen.

Schülerkarten werden nicht manuell gepflegt. Wenn Schüler in der Schülerverwaltung hinzugefügt, bearbeitet oder archiviert werden, aktualisieren sich Stammgruppenübersicht und Kursübersicht automatisch aus den vorhandenen Schülerdaten. Eine physische Löschung von Schülern ist nicht vorgesehen.

Stammgruppen und Kurse sind eigenständige fachliche Entitäten. Neue Stammgruppen werden über die Stammgruppenverwaltung angelegt, nicht automatisch beim Anlegen eines Schülers. Kurse werden über die Kursverwaltung gepflegt.

## Design-System

Das aktuelle Design der Stammgruppenübersicht wurde durch Laura freigegeben und ist die verbindliche Referenz für alle zukünftigen Ansichten.

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen. Es umfasst Farbwelt, Typografie, Kartenlayout, Kartenabstände, Desktop-App-Anmutung, 140-%-Zoom der Stammgruppenübersicht, Suchfeld, Weißraum und visuelle Hierarchie.

Neue Ansichten müssen sich an diesem Design-System orientieren. Designänderungen erfolgen ausschließlich in einem eigenen UX-Sprint.

## Projektregeln

Die dauerhaften Projektregeln sind in `AGENTS.md` festgelegt.

Zusammenfassung:

- Python erzeugt Workbook, Datenstruktur, Styles und Build-Artefakte.
- VBA ist nach erfolgreichem Packaging nur für UI-Aufgaben freigegeben.
- Keine fachliche Logik in VBA.
- Zielplattform ist Microsoft Excel für macOS.
- `openpyxl` verwenden.
- Keine festen Zellreferenzen.
- Strukturierte Tabellen bevorzugen.
- Datenmodell niemals ohne Rücksprache ändern.
- Design-System nicht ohne eigenen UX-Sprint ändern.
- Jede Änderung muss im Changelog dokumentiert werden.
- Jede Version muss lauffähig bleiben.
- Neue Funktionen nur nach Freigabe durch den Product Owner.

## Definition of Done

Eine Änderung gilt als abgeschlossen, wenn:

- die fachliche Anforderung umgesetzt oder dokumentiert ist,
- keine Projektregel verletzt wurde,
- die Projektdokumentation konsistent bleibt,
- das Changelog aktualisiert wurde,
- der Build-Einstiegspunkt weiterhin lauffähig ist,
- keine nicht freigegebenen Funktionen eingeführt wurden,
- keine Excel-Datei erzeugt wurde, sofern der Sprint dies nicht ausdrücklich vorsieht.

## Aktueller Sprint

Aktueller Sprint: Sprint 3.4 - Design Freeze und Domänenmodell aktualisieren.

Ziel des aktuellen Sprints ist die dauerhafte Dokumentation des freigegebenen Design-Systems und der präzisierten Domänensprache mit Stammgruppe und Kurs. Es werden keine Codeänderungen, keine VBA-Änderungen und kein Build umgesetzt.
