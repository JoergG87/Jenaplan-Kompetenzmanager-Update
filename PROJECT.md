# Projektdokumentation: Jenaplan-Kompetenzmanager

## Projektziel

Der Jenaplan-Kompetenzmanager ist ein professionelles Python-Projekt zur strukturierten Verwaltung, Auswertung und späteren Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

Das Projekt stellt die Grundlage für eine Excel-basierte Arbeitsmappe bereit, die vollständig durch Python erzeugt wird. Es werden keine Makros, kein VBA und keine manuellen Änderungen an generierten Excel-Dateien verwendet.

Sprint 0 dient ausschließlich dem Aufbau des technischen und dokumentarischen Fundaments. Es wird noch keine produktive Excel-Datei erzeugt.

## Leitbild

Das Projekt soll fachlich nachvollziehbar, technisch wartbar und langfristig erweiterbar sein.

Die Entwicklung folgt diesen Grundsätzen:

- Pädagogische Fachlichkeit steht vor technischer Komplexität.
- Daten werden strukturiert, nachvollziehbar und konsistent verarbeitet.
- Jede Version bleibt lauffähig.
- Änderungen werden dokumentiert und versioniert.
- Apple Numbers Kompatibilität ist ein verbindliches Architekturziel.

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

Die tägliche Arbeit erfolgt überwiegend über eine Klassenmatrix.

Weitere Ansichten wie Schülerprofil, Berichte und Kompetenzbögen entstehen automatisch aus denselben Daten.

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
- `src/dashboard.py` ist für das spätere Dashboard vorgesehen.
- `src/students.py` ist für Schülerdaten vorgesehen.
- `src/competencies.py` ist für Kompetenzdaten vorgesehen.
- `src/assessments.py` ist für Bewertungen vorgesehen.
- `src/reports.py` ist für Berichte vorgesehen.
- `src/settings.py` ist für zentrale Einstellungen vorgesehen.
- `src/styles.py` ist für visuelle Formatierungen vorgesehen.
- `data/` enthält Eingabedaten und Konfigurationen.
- `docs/` enthält fachliche Begleitdokumentation.
- `output/` ist für später generierte Dateien vorgesehen.
- `tests/` ist für automatisierte Tests vorgesehen.
- `assets/` ist für statische Ressourcen vorgesehen.
- `BACKLOG.md` sammelt zukünftige Produktideen und Erweiterungen.
- `DISCOVERY.md` dokumentiert fachliche Erkenntnisse aus Anwenderinterviews und Discovery-Workshops.

Die Architektur vermeidet feste Zellreferenzen. Stattdessen sollen strukturierte Daten, eindeutige IDs und wiederverwendbare Builder-Komponenten verwendet werden.

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
- Die spätere Darstellung muss in Excel und Apple Numbers funktionieren.
- Strukturierte Tabellen und eindeutige IDs haben Vorrang vor festen Zellpositionen.

## Versionierung

Das Projekt verwendet eine produktorientierte Versionsfolge.

- Version 3.1 bildet das Fundament.
- Versionen 3.2 bis 3.6 erweitern das Projekt schrittweise um fachliche und technische Funktionen.
- Version 4.0 ist als produktive Version vorgesehen.

Änderungen werden in `CHANGELOG.md` dokumentiert. Grundsätzliche Architekturentscheidungen werden in `DECISIONS.md` festgehalten.

## Roadmap

Die verbindliche Roadmap befindet sich in `ROADMAP.md`.

Aktuelle Planung:

- Version 3.1: Fundament
- Version 3.2: Dashboard
- Version 3.3: Bewertungssystem
- Version 3.4: Klassenmatrix
- Version 3.5: Schülerprofil
- Version 3.6: Thüringer Lehrplan
- Version 4.0: Produktive Version

## Bewertungssystem

Das Bewertungssystem wird in Version 3.3 fachlich ausgearbeitet.

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

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs. Das Datenmodell darf nicht ohne Rücksprache mit dem Product Owner geändert werden.

## Projektregeln

Die dauerhaften Projektregeln sind in `AGENTS.md` festgelegt.

Zusammenfassung:

- Niemals Makros verwenden.
- Niemals VBA verwenden.
- Immer Apple Numbers kompatibel bleiben.
- Excel wird ausschließlich über Python erzeugt.
- `openpyxl` verwenden.
- Keine festen Zellreferenzen.
- Strukturierte Tabellen bevorzugen.
- Datenmodell niemals ohne Rücksprache ändern.
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

Aktueller Sprint: Sprint 1 - Excel-Generator.

Ziel des aktuellen Sprints ist die technische Grundlage für die Excel-Erzeugung über Python. Die Grundversion erzeugt `output/Jenaplan_v3.2.xlsx` mit den vorbereiteten Arbeitsblättern Dashboard, Schüler, Kompetenzen, Bewertungen, Einstellungen und Changelog.
