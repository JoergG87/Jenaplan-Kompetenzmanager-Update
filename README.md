# Jenaplan-Kompetenzmanager

Der Jenaplan-Kompetenzmanager ist ein Python-Projekt zur strukturierten Verwaltung, Auswertung und zukuenftigen Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

In Sprint 0 wird ausschliesslich das technische Fundament erstellt. Es wird keine Excel-Datei erzeugt.

Die vollständige Projektdokumentation befindet sich in `PROJECT.md`. Dauerhafte Architekturentscheidungen befinden sich in `DECISIONS.md`.

## Projektziel

Ziel des Projekts ist der Aufbau eines wartbaren Generators fuer kompetenzorientierte Arbeitsmappen, Auswertungen und Berichte fuer Microsoft Excel auf macOS. Microsoft Excel fuer macOS ist die verbindliche Zielplattform.

Python erzeugt Workbook, Datenmodell, UI-Projektionen, Styles, Berichte und Build-Artefakte. Nach erfolgreichem VBA-Packaging uebernimmt VBA ausschliesslich Navigation, Buttons, Dialoge, UserForms und Benutzerinteraktion. Fachliche Logik verbleibt vollstaendig im Python- und Datenmodell.

Die Klassenübersicht ist der Einstieg in den Arbeitsablauf. Sie dient ausschließlich dazu, Schüler schnell zu finden, auszuwählen und anschließend in das Schülerprofil zu wechseln. Verwaltung, Analyse und Auswertung erfolgen nicht in dieser Ansicht.

## Architektur

Das Projekt ist modular aufgebaut:

- `build.py` dient als Einstiegspunkt fuer den Build-Prozess.
- `src/` enthaelt die Python-Module fuer Workbook-Aufbau, Dashboard, Schuelerdaten, Kompetenzen, Bewertungen, Berichte, Einstellungen und Styles.
- `src/core/`, `src/ui/` und `src/ui/screens/` bereiten die spaetere Trennung von Fachkern und UI-Generatoren vor.
- `vba/` ist fuer spaetere exportierte UI-VBA-Bausteine vorbereitet.
- `data/` enthaelt strukturierte Eingabedaten und Konfigurationen.
- `docs/` enthaelt fachliche und technische Dokumentation.
- `tests/` ist fuer automatisierte Tests vorgesehen.
- `output/` ist fuer kuenftig erzeugte Dateien vorgesehen.
- `assets/` ist fuer statische Ressourcen vorgesehen.

Die Excel-Erzeugung erfolgt über Python mit `openpyxl`. Fachliche Logik verbleibt im Python- und Datenmodell. VBA darf nach erfolgreichem Packaging nur Navigation, Dialoge, Benutzerinteraktion und UserForms uebernehmen.

Jede Ansicht besitzt genau eine Hauptaufgabe. Neue Funktionen dürfen diese Hauptaufgabe nicht verwässern.

Das Datenmodell ist die fachliche Grundlage des Projekts. Neue UI-Elemente duerfen das Datenmodell niemals umgehen; alle Ansichten sind Projektionen des Datenmodells.

## Entwicklungsprozess

Jede Implementierung folgt kuenftig dieser Reihenfolge:

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

## Dokumentation

- `PROJECT.md` enthält die zentrale Projektdokumentation.
- `AGENTS.md` enthält die verbindlichen Projektregeln.
- `DECISIONS.md` enthält endgültige Architekturentscheidungen.
- `ROADMAP.md` enthält die Versionsplanung.
- `CHANGELOG.md` dokumentiert Änderungen pro Version.

## Voraussetzungen

- Python 3.11 oder neuer
- Installation der Abhaengigkeiten aus `requirements.txt`

```bash
pip install -r requirements.txt
```

## Build ausfuehren

Der aktuelle Build erzeugt die UX-Prototypen im Ordner `output/`.

```bash
python3 build.py
```

Ausgaben:

```text
output/Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx
output/Jenaplan_UX_Prototype_v0.2.xlsx
```
