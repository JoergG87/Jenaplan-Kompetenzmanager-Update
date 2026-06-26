# Jenaplan-Kompetenzmanager

Der Jenaplan-Kompetenzmanager ist ein Python-Projekt zur strukturierten Verwaltung, Auswertung und zukuenftigen Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

In Sprint 0 wird ausschliesslich das technische Fundament erstellt. Es wird keine Excel-Datei erzeugt.

Die vollständige Projektdokumentation befindet sich in `PROJECT.md`. Dauerhafte Architekturentscheidungen befinden sich in `DECISIONS.md`.

## Projektziel

Ziel des Projekts ist der Aufbau eines wartbaren Generators fuer kompetenzorientierte Arbeitsmappen, Auswertungen und Berichte. Die kuenftige Excel-Erzeugung erfolgt ausschliesslich ueber Python und bleibt mit Apple Numbers kompatibel.

## Architektur

Das Projekt ist modular aufgebaut:

- `build.py` dient als Einstiegspunkt fuer den Build-Prozess.
- `src/` enthaelt die Python-Module fuer Workbook-Aufbau, Dashboard, Schuelerdaten, Kompetenzen, Bewertungen, Berichte, Einstellungen und Styles.
- `data/` enthaelt strukturierte Eingabedaten und Konfigurationen.
- `docs/` enthaelt fachliche und technische Dokumentation.
- `tests/` ist fuer automatisierte Tests vorgesehen.
- `output/` ist fuer kuenftig erzeugte Dateien vorgesehen.
- `assets/` ist fuer statische Ressourcen vorgesehen.

Die spätere Excel-Erzeugung erfolgt ausschließlich über Python mit `openpyxl`. Das Projekt verwendet eindeutige IDs im Datenmodell und vermeidet feste Zellreferenzen.

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

Der aktuelle Sprint-0-Build erzeugt keine Excel-Datei. Er prueft lediglich den Einstiegspunkt.

```bash
python3 build.py
```

Ausgabe:

```text
Jenaplan Kompetenzmanager Build
```
