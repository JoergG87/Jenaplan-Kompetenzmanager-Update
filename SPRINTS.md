# Sprintplanung

SPRINTS.md dient ausschließlich der operativen Projektplanung.

ROADMAP.md beschreibt die langfristige Vision. SPRINTS.md ersetzt ROADMAP.md nicht.

## Sprintübersicht

## Sprint - PySide Icon Theme ✅

- [x] Status: Abgeschlossen

### Titel

Icon-basierte visuelle Anpassung der PySide-Hauptanwendung

### Ergebnis

- [x] Zentrales PySide-Theme aus der freigegebenen Icon-Farbwelt erstellt
- [x] App-weites Stylesheet fuer Navigation, Karten, Tabellen, Eingaben und Dialoge angebunden
- [x] Bestehende PySide-Screens und Dialoge auf semantische Text- und Card-Helfer umgestellt
- [x] Kursfarbmarker als fachliche Marker erhalten
- [x] Keine Fachlogik, keine Persistenz und kein Excel-/VBA-Pfad geaendert

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
- [x] Durch ADR-046 entschieden: PySide ist Hauptanwendung
- [x] Durch ADR-046 entschieden: Excel/VBA ist Export-, Berichts-, Referenz- oder Legacy-Pfad
- [x] Durch ADR-046 entschieden: xlwings/Excel-Bruecke ist kein Zielpfad fuer neue Haupt-App-Features

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
- [x] Suche in der Schueleruebersicht ergaenzt
- [x] Suche filtert nach Vorname, Nachname, Vollname, Stammgruppe und Kurs
- [x] Suche bleibt mit Gruppenfilter kombinierbar
- [x] Keine Beobachtungsmaske, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Sprint - PySide6 Schuelerprofil UX-Ausbau 1

- [x] Profilkopf mit Zurueck-Button, Name, Stammgruppe, Kurs und dezenter `student_id`-Anzeige umgesetzt
- [x] Schnellaktionen `+ Beobachtung`, `Dokument hinzufügen` und `Schüler bearbeiten` sichtbar gemacht
- [x] Schnellaktionen bleiben reine Platzhalter mit Inline-Hinweis und starten keine produktiven Fachprozesse
- [x] Basisdaten als eigener Profilbereich umgesetzt
- [x] Beobachtungen, Kompetenzen und Dokumente als Karten mit Platzhaltertexten strukturiert
- [x] Keine Beobachtungsmaske, keine Beobachtungspersistenz, keine Dokumentenverwaltung und keine Kompetenzberechnung umgesetzt
- [x] Keine Datenmodelländerung, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Sprint - PySide6 Beobachtungsdialog UX-Prototyp 1

- [x] `+ Beobachtung` im Schuelerprofil oeffnet einen nicht-persistenten Dialog `Neue Beobachtung`
- [x] Dialog zeigt den ausgewaehlten Schueler sichtbar im Titelbereich
- [x] Felder fuer Datum, Fach, Kompetenz(en), Kontext, Bewertung und Notiz umgesetzt
- [x] Bereich `Dokumente & Medien` mit Hinweis, `Datei hinzufügen` und Empty State vorbereitet
- [x] Speichern zeigt nur den Hinweis, dass Beobachtungen spaeter gespeichert werden
- [x] `Datei hinzufügen` zeigt nur den Hinweis, dass Anhaenge spaeter gespeichert werden
- [x] Lokale UI-Listen fuer Fach und Kompetenzen als Spike-Einschraenkung verwendet
- [x] Keine Beobachtungspersistenz, kein Repository, keine SQLite-Aenderung und keine Datenmodelländerung umgesetzt
- [x] Keine Dokumentenanhaenge, kein Packaging, kein Excel-Export-Umbau und keine finale Architekturentscheidung umgesetzt

### Sprint - Curriculum-Katalog v1

- [x] Read-only-Katalog `data/curriculum_catalog_v1.csv` mit Faecher- und Kompetenzeintraegen angelegt
- [x] Kernfaecher Deutsch, Mathematik, EPU, Musik, Kunst, Sport und Sozialkompetenz aufgenommen
- [x] Erweiterte Faecher Ethik, Religion, Werken und Schulgarten aufgenommen
- [x] `EPU` als App-Anzeigename fuer `Epochaler Projektunterricht` modelliert
- [x] Offizielle Quelle fuer EPU als `Heimat- und Sachkunde` dokumentiert
- [x] `Sachunterricht` wird nicht als App-Fach angezeigt
- [x] PySide6-Beobachtungsdialog liest Fach- und Kompetenzlisten aus dem Katalog
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung und keine Datenmodelländerung fuer Beobachtungen umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Hotfix - Beobachtungsdialog Kompetenzauswahl lesbarer

- [x] Kompetenzliste zeigt kurze Lernbereich-Labels statt langer Kompetenztexte
- [x] Lange Kompetenztexte bleiben im Katalog und im nicht-persistenten Draft erhalten
- [x] Mehrfachauswahl als sichtbare Checkbox-Liste umgesetzt
- [x] Fachwechsel aktualisiert die Kompetenzliste und setzt die vorherige Auswahl zurueck
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung und keine Datenmodelländerung umgesetzt

### Sprint - Beobachtungsdialog Bewertung pro Kompetenz

- [x] Globale Bewertung aus dem PySide6-Beobachtungsdialog entfernt
- [x] Bewertungs-Auswahl pro ausgewaehlter Kompetenz vorbereitet
- [x] Nicht-persistenter Draft fuehrt Kompetenzbewertungen statt Beobachtungs-Gesamtbewertung
- [x] Abwaehlen einer Kompetenz entfernt deren Bewertung aus dem Draft
- [x] Fachwechsel setzt Kompetenzauswahl und Kompetenzbewertungen zurueck
- [x] Dialoginhalt scrollbar gemacht, damit die Buttonleiste erreichbar bleibt
- [x] Kompetenzauswahl und Bewertungszeilen kompakter gestaltet
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository und keine Datenmodelländerung umgesetzt

### Hotfix - Beobachtungsdialog faecheruebergreifende Kompetenzbewertungen

- [x] Fachwechsel erhaelt bereits ausgewaehlte Kompetenzbewertungen
- [x] Fach-Dropdown als Filter fuer die sichtbare Kompetenzauswahl praezisiert
- [x] Kompetenzen aus mehreren Faechern koennen gleichzeitig im nicht-persistenten Draft stehen
- [x] Kompetenzbewertungszeilen zeigen den Fach-Anzeigenamen und bieten `Entfernen`
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Sprint - PySide6 Stammdaten light

- [x] Navigationseintrag `Stammdaten` ergaenzt
- [x] Stammdaten-light-Seite mit Bereichen fuer Stammgruppen und Kurse ergaenzt
- [x] Hinzufuegen und Umbenennen fuer Stammgruppen und Kurse als nicht-persistenter UI-/Adapter-Draft vorbereitet
- [x] Leere Namen werden mit verstaendlicher Meldung abgelehnt
- [x] Loeschen, Schueler-Umbuchung und produktive Stammgruppen-/Kurspersistenz bewusst nicht umgesetzt
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung fuer Beobachtungen, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Sprint - PySide6 Schuelerdialog an Stammdaten anbinden

- [x] PySide6-Dialog `Neuer Schüler` nutzt Stammdaten-light fuer Stammgruppen- und Kursauswahl
- [x] Stammgruppen- und Kursfelder verwenden Dropdowns mit `Bitte auswählen`
- [x] Leerer Name, fehlende Stammgruppe und fehlender Kurs werden vor dem Speichern abgefangen
- [x] Session-lokale Stammdaten sind im Dialog sichtbar, aber nur dauerhaft vorhandene Eintraege koennen fuer `student.create` gespeichert werden
- [x] Keine neue Persistenz, keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Hotfix - PySide6 Kursfarben anzeigen

- [x] Kurse im Stammdaten-light-ViewModel um UI-Farbe als Name und Hex-Wert erweitert
- [x] Kursdialoge um feste Farbauswahl fuer Blau, Gruen, Orange, Lila, Rot und Grau erweitert
- [x] Kursfarben in der Stammdaten-Seite als kleiner Farbmarker angezeigt
- [x] Kursfarben in der PySide6-Schuelerliste neben dem Kursnamen angezeigt
- [x] Keine neue Persistenz, keine SQLite-Aenderung, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Sprint - PySide6 UI-Polish

- [x] Dialogbuttons fuer Speichern und Abbrechen vereinheitlicht
- [x] Empty States fuer Schuelerliste und Stammdaten-Seite ergaenzt
- [x] App-Info-Dialog mit Prototyp-Hinweis ergaenzt
- [x] Suchfeld in der Schuelerliste verfeinert
- [x] Einfachen Tastaturkomfort fuer Dialoge vorbereitet
- [x] Keine Fachlogik, keine Persistenz, keine SQLite-Aenderung und keine finale Architekturentscheidung umgesetzt

### Hotfix - macOS-Launcher fuer PySide6-Prototyp

- [x] Doppelklick-faehige Launcher-Datei `launcher/Jenaplan_Kompetenzmanager.command` ergaenzt
- [x] Launcher wechselt robust ins Projektverzeichnis
- [x] Launcher nutzt `.venv/bin/python`, falls vorhanden, sonst `python3`
- [x] README um Terminalstart und Doppelklick-Start ergaenzt
- [x] Kein PyInstaller, kein Installer, kein `.app`-Bundle und keine Packaging-Toolchain umgesetzt
- [x] Keine Fachlogik, keine Persistenz, keine SQLite-Aenderung und keine finale Architekturentscheidung umgesetzt

### Dokumentation - Icon-basierte visuelle Leitlinie

- [x] App-Icon als zentrale gestalterische Referenz dokumentiert
- [x] Farbwelt aus Dunkelblau, Blau, Tuerkis, Gruen, Orange und hellen neutralen Hintergruenden festgehalten
- [x] Weiche Formensprache, Kartenoptik, Weissraum und klare visuelle Hierarchie als UI-Leitlinie ergaenzt
- [x] Leichte moderne Glasoptik als optionales, zurueckhaltendes Stilmittel beschrieben
- [x] Bedeutungsanker Baum, Personen, Diagramm, Kreis/Bogen und farbige Blaetter dokumentiert
- [x] PySide als kuenftige Hauptanwendung dokumentiert
- [x] Keine Codeaenderung, kein Build und kein Commit umgesetzt

### Korrektur-Hotfix - PySide Kursverbuende und Schuelerliste

- [x] Speichern-Buttons in PySide-Dialogen zentral im blauen Primary-Stil dargestellt
- [x] Kursfarben-Palette um Gelb `#EAB308` erweitert
- [x] Schuelerliste wieder mit sauber getrennter Kurs-Spalte hergestellt
- [x] Kursmarker und Kursname in getrenntem Kurs-Zelllayout ohne Ueberlagerung dargestellt
- [x] Session-lokalen Default-Kursverbund `Mathe/Deutsch Kursverbund A` ergaenzt
- [x] Uebersicht `Stammgruppen und Schülerbestand` zeigt Stammgruppen aus dem aktuellen Stammdaten-Scope
- [x] Uebersicht `Stammgruppen und Schülerbestand` zeigt Kurse mit farbigem Marker innerhalb des Kursverbunds
- [x] Kursfilter beruecksichtigt Kurs und Stammgruppen des Kursverbunds
- [x] Offenen UX-Punkt dokumentiert: Kompetenznamen in der Bewertungsliste spaeter eventuell fett darstellen
- [x] Keine neue Persistenz, keine SQLite-Aenderung, kein ObservationRepository, kein Excel-/VBA-Umbau und keine Packaging-Toolchain umgesetzt

### Architektur-Sprint - PySide Hauptanwendung, Excel/VBA Legacy/Export

- [x] Arbeitsbaum vor Sprintbeginn sauber vorgefunden
- [x] ADR-046 ergaenzt: PySide ist Hauptanwendung
- [x] SQLite als produktive lokale Datenbasis dokumentiert
- [x] Excel/VBA auf Export-, Berichts-, Referenz- und Legacy-Kontext zurueckgestuft
- [x] Keine neuen Excel-/VBA-Features, keine VBA-Smoke-Tests und keine VBA-Automation als Zielpfad dokumentiert
- [x] README, PROJECT, ROADMAP, AGENTS und Governance-Dokumente bereinigt
- [x] PySide6-Feasibility als abgeschlossene Machbarkeitsphase markiert
- [x] Backlog um Legacy-Bereinigung, Exportstrategie, Packaging/Installer und SQLite-Ausbau ergaenzt
- [x] Keine Code-Loeschung, keine Produktlogik, keine SQLite-Migration, kein Packaging und kein Commit umgesetzt

### Sprint - PySide Kursverbund bearbeiten

- [x] Arbeitsbaum vor Sprintbeginn sauber vorgefunden
- [x] Kursverbund-Bearbeiten-Dialog fuer Name, Stammgruppen und Kurse ergaenzt
- [x] Stammgruppen und Kurse im Kursverbund per Checkbox auswaehlbar gemacht
- [x] Leerer Name, fehlende Stammgruppe und fehlender Kurs werden verstaendlich abgelehnt
- [x] Kursverbund wird session-lokal im `MasterDataDesktopAdapter` gespeichert
- [x] Stammdaten-Seite zeigt aktualisierte Kursverbund-Auswahl
- [x] Uebersicht nutzt aktualisierte Kurse des Kursverbunds
- [x] Kursfilter bleibt `course_id` plus ausgewaehlte `group_ids`
- [x] Schueleruebersicht mit Kurs-Spalte und farbigem Marker erhalten
- [x] Keine SQLite-Persistenz, keine Migration, kein Repository, kein Excel-/VBA-Umbau und kein Commit umgesetzt

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
