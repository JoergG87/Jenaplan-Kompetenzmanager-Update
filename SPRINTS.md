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
- [x] UX-Prototyp fuer Feature 1 `Neuer Schueler` als verbindliche visuelle Vorlage vorbereiten
- [x] UX-Prototyp als Pflichtschritt vor kuenftiger Dialogumsetzung dokumentieren
- [x] VBA-UserForm-Ansatz fuer Excel auf macOS als nicht belastbar bewertet
- [x] Worksheet-basierte Dialogseite `dlg_neuer_schueler` als neuen Feature-1-Pfad vorbereitet
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

### Feature 1 - UX-Prototyp `Neuer Schueler`

- [x] `output/Jenaplan_UX_Prototype_v0.1.xlsx` um das Blatt `Feature 1 – Neuer Schüler` ergaenzt
- [x] Fenstertitel, Pflichtfelder, Notizbereich, Dokumentbereich, Dokument-Hinzufuegen-Button sowie Abbrechen/Speichern visuell dargestellt
- [x] Blatt als visuelle Vorlage fuer den spaeteren Eingabedialog dokumentiert
- [x] Keine VBA-UserForm, keine Python-Aenderung, keine Validierung, keine Adapter-Anbindung und kein Build umgesetzt
- [ ] UX-Review mit Laura bzw. Product Owner durchfuehren
- [ ] UX-Freigabe vor technischer Dialogumsetzung dokumentieren

### Feature 1 - Architekturwechsel zu `dlg_neuer_schueler`

- [x] VBA-UserForms auf Excel fuer macOS als instabil bewertet
- [x] `frm_student_new` als experimentell/deprecated eingeordnet
- [x] Worksheet-basierte Dialogseiten als primaeres Eingabe-Pattern dokumentiert
- [x] `dlg_neuer_schueler` als Dialogseite fuer `Neuer Schueler` vorbereitet
- [x] Absprungpunkt `+ Schüler` von der Stammgruppenuebersicht zur Dialogseite vorbereitet
- [x] Keine Speicherlogik, keine Validierung, kein Python-Command und kein SQLite-Schreibzugriff umgesetzt

### Feature 1.3 - Dialogseite vorbereiten

- [x] Dialogseite `dlg_neuer_schueler` bleibt geschuetzt
- [x] Nur Eingabebereiche fuer Vorname, Nachname, Stammgruppe, Kurs und Notiz entsperrt
- [x] Eingabebereiche ueber registrierte Named Ranges vorbereitet
- [x] Abbrechen als Navigation zur Stammgruppenuebersicht vorbereitet
- [x] Speichern optisch vorbereitet, aber ohne Aktion
- [x] Dokumentbereich sichtbar, `+ Dokument hinzufügen` ohne Funktion
- [x] Keine Speicherung, keine Validierung, kein Python-Command und kein SQLite-Schreibzugriff umgesetzt

### Feature 1.4a - Runtime Adapter und Refresh Contract

- [x] Runtime-Pfad `Dialogseite -> VBA Adapter -> Python CLI/Bridge -> Dispatcher -> StudentService -> Repository -> SQLite` freigegeben
- [x] Refresh Contract ueber Python-generiertes Projection-Refresh-Paket freigegeben
- [x] VBA darf nur Projection Output importieren und keine fachliche Tabellenlogik ausfuehren
- [x] SQLite als Source of Truth fuer `student.create` im Feature-1-Schreibprozess festgelegt
- [x] Feature 1.4 darf implementiert werden, wenn dieser Vertrag eingehalten wird
- [x] Keine Speicherung, keine Validierung, kein Python-Aufruf aus VBA und kein Workbook-Refresh umgesetzt

### Feature 1.4b - Produktiver Speichervorgang bis SQLite

- [x] `SaveNewStudentDialog()` als VBA Adapter fuer die Dialogseite umgesetzt
- [x] Adapter liest ausschliesslich registrierte Named Ranges von `dlg_neuer_schueler`
- [x] Adapter schreibt `runtime_command.json` und startet `km.py student create`
- [x] `km.py` verwendet `ApplicationCommandDispatcher`, `CreateStudentCommand`, `StudentService` und `SQLiteStudentRepository`
- [x] `student.create` schreibt produktiv in `data/kompetenzmanager.sqlite`
- [x] Erfolg und Fehler werden ueber `runtime_result.json` an Excel zurueckgegeben
- [x] Noch kein Projection Refresh, keine Workbook-Aktualisierung und keine Navigation nach dem Speichern umgesetzt

### Spike - PySide6 Desktop-App als alternativer Adapter

- [x] Branch `spike/python-gui` genutzt
- [x] Ruecksprungpunkt `checkpoint-excel-adapter-before-python-gui` bleibt fuer Excel/xlwings erhalten
- [x] PySide6 statt tkinter als Spike-UI verwendet
- [x] App `Jenaplan Kompetenzmanager` startet
- [x] Maske `Neuer Schüler` funktioniert
- [x] Schueler wird ueber `CreateStudentCommand`, `ApplicationCommandDispatcher`, `StudentService` und `SQLiteStudentRepository` in SQLite geschrieben
- [x] Keine Businesslogik in der GUI
- [x] Kein direkter SQLite-Write aus Qt Widgets
- [x] Tests gruen: 26 passed
- [x] Build gruen
- [x] Commit `5363e18` und Tag `spike-pyside6-student-create` gesetzt
- [ ] Entscheidung ueber Python-GUI als Hauptanwendung offen
- [ ] Entscheidung ueber xlwings als Excel-Bruecke offen
- [ ] Entscheidung ueber Excel als Export-/Berichtspfad offen

### GUI-Umsetzungspruefung 1 - PySide6 App-Struktur und MVP-Navigation

- [x] PySide6 als moegliche Hauptanwendung fachlich und technisch geprueft
- [x] Ziel-App-Struktur fuer Hauptfenster, Navigation, Schuelerliste, Schuelerprofil light und Platzhalterbereiche skizziert
- [x] MVP-Schnitt ohne Beobachtungsmaske, Packaging und Excel-Export-Umbau definiert
- [x] Design-System-Uebertragung auf PySide6 dokumentiert
- [x] Risiken fuer Packaging, Datenbankpfad, Backup/Restore, Updates, Excel-Export und Testbarkeit bewertet
- [x] Nutzen-Aufwand-Vergleich fuer PySide6, xlwings und Excel/VBA-Runtime-Adapter dokumentiert
- [x] Keine finale Architekturentscheidung getroffen
- [x] Keine Feature-Implementierung umgesetzt

### Sprint - PySide6 MVP Shell und Navigation

- [x] Hauptfenster `Jenaplan Kompetenzmanager` mit Navigation umgesetzt
- [x] Navigationspunkte `Übersicht`, `Schüler`, `Beobachtungen`, `Kompetenzen`, `Berichte` und `Einstellungen` umgesetzt
- [x] Uebersicht mit Stammgruppen-/Gruppenkarten und Schuelerzahlen umgesetzt
- [x] Schuelerseite mit SQLite-Schuelerliste umgesetzt
- [x] Bestehenden Dialog `+ Schüler` integriert
- [x] Schuelerprofil light mit Stammdaten und Notiz umgesetzt
- [x] Platzhalter fuer Beobachtungen, Kompetenzen, Berichte und Einstellungen umgesetzt
- [x] Keine Beobachtungsmaske, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Sprint - PySide6 UX Stabilisierung 1

- [x] Zurueck-Button im Schuelerprofil light umgesetzt
- [x] Ruecksprung zur Schuelerliste erhaelt den aktuellen Gruppenfilter
- [x] Klick auf `Schüler` in der linken Navigation fuehrt aus dem Profil zur Liste
- [x] Schuelerprofil in Titel, Stammgruppe/Kurs, Notiz und Beobachtungsplatzhalter gegliedert
- [x] Nicht-modale Statusmeldung `Schüler wurde gespeichert.` nach erfolgreichem Speichern ergaenzt
- [x] Keine Beobachtungsmaske, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

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
