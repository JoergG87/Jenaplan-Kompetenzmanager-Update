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

## Sprint 5 🔜

- [ ] Status: Scope abgeschlossen; Dialog Framework begonnen

### Titel

Dialog Framework, Schuelerverwaltung und Dokumentenarchitektur

### Ziele

- [x] Scope Freeze abschliessen
- [x] Standard fuer modale VBA-UserForms dokumentieren
- [x] Referenzdialog `Neuer Schueler` als erste Referenzimplementierung einordnen
- [x] Dokumentenstruktur fuer Schuelerdokumente und Beobachtungsanhaenge festlegen
- [x] Dokumentbereich in der Schueler-UserForm vorbereiten
- [x] Spaeteren Beobachtungsdialog mit Kompetenzbezug vorbereiten
- [ ] Produktive Speicherlogik fuer Schueler freigeben

### Sprint 5.1a - Dialog Framework vorbereiten

- [x] Dialogstandard konkretisieren
- [x] `frm_student_new` gegen den Dialogstandard pruefen
- [x] Enter = Speichern und Esc = Abbrechen im Referenzdialog vorbereiten
- [x] Vorgesehenen Dialogoeffner `OpenNewStudentDialog()` registrieren
- [x] Keine produktive Schueler-Speicherlogik
- [x] Kein Seed-Import

### Sprint 5.1b - Schueleranlage ueber UserForm anbinden

- [x] Architekturpfad UserForm -> `StudentService.create_student()` geprueft
- [x] Fehlende freigegebene VBA-zu-Python-Service-Bruecke dokumentiert
- [x] Direkte VBA-Schreiblogik in `tbl_students` ausgeschlossen
- [x] Technische Optionen dokumentiert
- [x] Empfehlung: Command-Queue-Architekturspike
- [x] Keine produktive UserForm-Anbindung umgesetzt
- [x] Kein Seed-Import

### Sprint 5.2a - SQLite Architecture Spike

- [x] SQLite-Verfuegbarkeit geprueft
- [x] Datenbankpfad `data/kompetenzmanager.sqlite` festgelegt
- [x] Tabellen `students`, `groups` und `courses` erzeugt
- [x] Seed-Daten ohne ID-Neuvergabe nach SQLite geschrieben
- [x] SQLite-Repositories fuer Students, Groups und Courses prototypisiert
- [x] Bestehende Excel-Projektion testweise aus SQLite-Daten erzeugt
- [x] Keine produktive Migration
- [x] Keine VBA-zu-Python-Bridge
- [x] Kein Seed-Import

### Sprint 5.3 - Application Command Layer

- [x] Application-Layer-Struktur unter `src/application/` angelegt
- [x] Application Command Dispatcher als Architektur-Skelett eingefuehrt
- [x] `student.create` als erstes Command-DTO vorbereitet
- [x] CLI als spaeteren Adapter dokumentiert
- [x] VBA-Anbindung als spaeteren Command Adapter dokumentiert
- [x] Keine produktive CLI
- [x] Keine UserForm-Anbindung
- [x] Keine Build-Aenderung

### Sprint 5.4 - student.create End-to-End

- [x] `student.create` durch Dispatcher, Command, Service, Repository und SQLite validiert
- [x] `SuccessResult` und `ErrorResult` eingefuehrt
- [x] Keine CLI
- [x] Keine VBA-Anbindung
- [x] Keine Excel-Automation
- [x] Kein Build

### Architecture Baseline v2.0

- [x] Validierten Sprint-5-Architekturstand dokumentiert
- [x] Architecture v1 historisch eingeordnet
- [x] Adapter, Application, Domain, Infrastructure, Projection und Excel UI als Schichten beschrieben
- [x] Standard-Datenfluss dokumentiert
- [x] Keine neue Implementierung

### Nicht Bestandteil

- [x] Keine Beobachtungserfassung
- [x] Keine Schnellbeobachtung oder Gruppenbewertung
- [x] Keine Kompetenzzuordnung in Beobachtungen implementieren
- [x] Kein vollstaendiges Dokumentenmanagement
- [x] Kein Dokument-Upload
- [x] Keine Medienvorschau
- [x] Keine produktive Schueleranlage
- [x] Keine direkte VBA-SQLite-Anbindung
- [x] Keine Berichte
- [x] Keine Kursverwaltung
- [x] Keine Stammgruppenverwaltung
