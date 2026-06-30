# Sprintplanung

SPRINTS.md dient ausschließlich der operativen Projektplanung.

ROADMAP.md beschreibt die langfristige Vision. SPRINTS.md ersetzt ROADMAP.md nicht.

## Sprintübersicht

## Sprint 0 ✅

- [x] Status: Abgeschlossen

### Ziele

- [x] Projektstruktur erstellt
- [x] Git eingerichtet
- [x] Dokumentation angelegt
- [x] build.py erstellt
- [x] Python-Projekt lauffähig

### Ergebnis

Das Projekt kann erfolgreich mit

```bash
python3 build.py
```

gestartet werden.

## Sprint 1 🔄

- [ ] Status: In Arbeit

### Titel

Excel-Generator

### Ziele

- [x] Build-Architektur erstellen
- [x] Workbook-Generator implementieren
- [x] Erste Excel-Datei erzeugen
- [x] Dashboard-Blatt erstellen
- [x] Schüler-Blatt erstellen
- [x] Kompetenzen-Blatt erstellen
- [x] Bewertungen-Blatt erstellen
- [x] Einstellungen-Blatt erstellen
- [x] Changelog-Blatt erstellen

### Akzeptanzkriterien

- [x] python3 build.py läuft fehlerfrei
- [x] output/Jenaplan_v3.2.xlsx wird erzeugt
- [ ] Datei lässt sich in Excel öffnen

## Sprint 2

Dashboard & Design

## Sprint 3

Architekturwechsel UX-Prototyp

- [x] Bestehender UX-Prototyp bleibt als First Attempt erhalten
- [x] Neue UX-Prototyp-Version v0.2 vorbereitet
- [x] Zielplattform Microsoft Excel für macOS dokumentiert
- [x] UI-Technologie-ADR ergänzt
- [x] Projektstruktur für spätere Trennung vorbereitet
- [x] Sprint 3.1: Klassenübersicht bauen
- [x] v0.2 enthält keine weiteren Bildschirme
- [x] UI-Anker für spätere VBA-Interaktion vorbereitet
- [ ] Review durch Laura

## Sprint 4.0 ✅

- [x] Status: Abgeschlossen

### Titel

Core Data Architecture

### Ergebnis

- [x] Projektverfassung dokumentiert
- [x] Technical Naming Registry dokumentiert
- [x] Workbook Data Registry dokumentiert
- [x] UI Data Mapping dokumentiert
- [x] View Data Ownership dokumentiert
- [x] Data Lifecycle dokumentiert

## Sprint 4.1 ✅

- [x] Status: Abgeschlossen

### Titel

Schülerverwaltung Phase 1: Architektur validieren

### Ergebnis

- [x] Architektur erfolgreich validiert
- [x] Hidden Data Sheets erzeugt
- [x] `tbl_students`, `tbl_groups`, `tbl_courses` erzeugt
- [x] Stammgruppenübersicht aus Daten projiziert
- [x] Schülerprofil aus Daten projiziert
- [x] VBA-Navigation über `student_id` bleibt funktionsfähig
- [x] Release `v0.4` vorbereitet

## Sprint 4.2 🔜

- [ ] Status: Vorbereitet

### Titel

Schülerverwaltung: erster transaktionaler Schreibprozess

### Ziele

- [ ] Schüler anlegen
- [ ] Schüler ändern
- [ ] Schüler archivieren
- [ ] Keine physische Löschung
- [ ] Schreibprozess vollständig oder gar nicht ausführen

## Sprint 5.0 🔜

- [ ] Status: Vorbereitet

### Titel

Dialog- und Dokumentenarchitektur vorbereiten

### Ziele

- [ ] Standard fuer modale VBA-UserForms dokumentieren
- [ ] Referenzdialog `Neuer Schueler` dokumentieren
- [ ] Dokumentenstruktur fuer Schuelerdokumente und Beobachtungsanhaenge festlegen
- [ ] Dokumentbereich in der Schueler-UserForm vorbereiten
- [ ] Spaeteren Beobachtungsdialog mit Kompetenzbezug vorbereiten

### Nicht Bestandteil

- [ ] Keine Beobachtungserfassung
- [ ] Keine Schnellbeobachtung oder Gruppenbewertung
- [ ] Keine Kompetenzzuordnung in Beobachtungen implementieren
- [ ] Kein vollstaendiges Dokumentenmanagement
- [ ] Keine Datei-Vorschau
- [ ] Keine Berichte
- [ ] Keine Kursverwaltung
- [ ] Keine Stammgruppenverwaltung
