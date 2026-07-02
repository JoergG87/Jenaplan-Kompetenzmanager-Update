# Roadmap

## Zielplattform und Architektur

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Python bleibt verantwortlich für Datenmodell, Application Layer, Domain Layer, Persistenz, PySide-Oberflaeche, UI-Projektionen, Export-Erzeugung, Berichte und Fachlogik.

Excel/VBA bleibt im Repository als Export-, Berichts-, Referenz- oder Legacy-Projektion erhalten, ist aber nicht mehr die Zielrichtung fuer die Haupt-App.

VBA wird nicht weiter als Zielpfad fuer neue Features, UI, Smoke-Tests, Automatisierung oder produktive Workflows verfolgt.

Worksheet-basierte Dialogseiten, VBA-UserForms und VBA-Runtime-Adapter sind historische Artefakte der Excel-Linie.

Der PySide6 Desktop-App-Spike ist zur Hauptanwendungslinie geworden. Excel bleibt im Repository als bestehende Projektion und moeglicher Export-/Berichtspfad erhalten.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut. Ein Ruecksprungpunkt fuer den Excel/xlwings-Pfad existiert mit dem Tag `checkpoint-excel-adapter-before-python-gui`.

Offen bleiben produktiver Nutzer-Datenbankpfad, Backup/Restore, Packaging als macOS-App, Updates/Migrationen und der genaue Umfang kuenftiger Excel-Exporte.

Der VBA-Seed wurde historisch validiert. `.xlsm` ist kein Hauptartefakt der aktiven Produktlinie mehr.

Das Datenmodell ist die fachliche Grundlage des Projekts. Alle Ansichten sind Projektionen dieses Datenmodells.

Das Design-System ist die visuelle Grundlage des Projekts. Alle zukünftigen Ansichten orientieren sich am freigegebenen App-Icon und an der daraus abgeleiteten ruhigen, modernen PySide-Desktop-App-Anmutung.

## Aktueller UX-Prototyp-Pfad

Sprint 3.0: Architekturwechsel auf Microsoft Excel für macOS und Vorbereitung der v0.2-Prototyp-Generation.

Sprint 3.1: Klassenübersicht als erster UX-Screen unter der früheren Bezeichnung.

Sprint 3.2: Schülerprofil als zweiter UX-Screen.

Sprint 3.3a: Architektur konsolidieren und Dokumentation bereinigen.

Sprint 3.3b: VBA-Seed praktisch validieren.

Sprint 3.3c: VBA-Framework als versionierbare Quelle anlegen und ersten `.xlsm`-Interaktionstest vorbereiten.

Sprint 3.4: Design Freeze als dauerhaftes Design-System dokumentieren und Domänenmodell auf Stammgruppe und Kurs präzisieren.

Sprint 4.0: Core Data Architecture, technische Namen, Data Registry, View Ownership und Data Lifecycle dokumentieren.

Sprint 4.1: Core Data Architecture durch Hidden Data Sheets, strukturierte Tabellen und datengetriebene UI-Projektionen validieren. Abgeschlossen mit Release `v0.4`.

Sprint 4.2: Schülerverwaltung vorbereiten und ersten transaktionalen Schreibprozess umsetzen: Schüler anlegen, ändern und archivieren.

Sprint 5: Scope Freeze abgeschlossen, Dialog Framework begonnen und erste Referenz-UserForm `Neuer Schueler` vorbereitet. Sprint 5.1a konkretisiert den Dialogstandard fuer zukuenftige Eingabemasken. Sprint 5.1b stoppt die produktive Schueleranlage an der noch offenen Laufzeitbruecke zwischen Excel/VBA und Python-Service-Schicht. Sprint 5.2a prueft SQLite als moegliche zentrale Datenbasis. Sprint 5.3 fuehrt den Application Command Layer ein. Sprint 5.4 validiert `student.create` im Python-Stack. Architecture Baseline v2.0 dokumentiert diesen erreichten Stand. Feature 1 fuehrt den UX-Prototyp als verbindlichen Zwischenschritt vor Dialogumsetzungen ein und wechselt wegen macOS-UserForm-Problemen auf die worksheet-basierte Dialogseite `dlg_neuer_schueler`. Feature 1.4a definiert den Runtime Adapter und den Refresh Contract fuer `student.create`. Feature 1.4b implementiert den produktiven Schreibpfad bis SQLite ohne Projection Refresh. Der PySide6 Desktop-App-Spike validiert anschliessend einen UI-Adapter ueber denselben Application-/Service-/Repository-Stack. Nach dem freigegebenen App-Icon wird PySide zur Hauptanwendungslinie.

Kurzfristige Produktziele

- PySide-App stabilisieren
- Stammdaten und Kursverbuende weiter klaeren
- Beobachtungspersistenz
- Schuelerprofile ausbauen
- lokale SQLite-Datenhaltung produktionsnaeher machen
- Exportstrategie spaeter definieren

Mittelfristige Produktziele

- Berichte und Auswertungen in PySide
- Excel-/Datei-Exportfunktion
- Packaging/Installer fuer macOS
- Datenschutz, Backup/Restore und Freischaltcode spaeter klaeren

Excel/VBA Legacy/Export

- keine aktive Feature-Roadmap
- alte Workbook-/VBA-Pfade pruefen und bei Bedarf archivieren
- Excel nur als Export, Berichtsausgabe, Referenz oder Legacy-Projektion

Zukünftige Produktziele ohne Sprintzuordnung

- Beobachtungsverwaltung
- Historisierung von Kompetenzständen
- Schülerprofile auf Basis von Beobachtungen
- Lernentwicklungsberichte
- Dashboard auf Basis historischer Daten
- Vorschläge für Kompetenzstände
- Beobachtungsverläufe
- Geplante Beobachtungen
- Spontane Beobachtungen
- Gruppenbeobachtungen
- Schnellbeobachtung / Gruppenbewertung
- Stammgruppenverwaltung
- Kursverwaltung
- Kursübersicht
- UX Hauptfenster fuer die PySide-Hauptanwendung
- Schuelerprofil in der PySide-Hauptanwendung
- Beobachtungsmaske in der PySide-Hauptanwendung
- Packaging als macOS-App
- Produktiver Nutzer-Datenbankpfad, Backup und Restore
- Excel-Export und Berichte auf Basis von SQLite

Diese Punkte stellen zukünftige Produktziele dar.

Sie gehören aktuell noch keinem Sprint an.

Sprint 2c

- Sprint 2c erzeugte den ersten UX-Prototyp, der ab Sprint 3.0 als `Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx` erhalten bleibt.
- Der Prototyp dient dem Anwenderfeedback und ist nicht die produktive Version.
- Auf Basis des UX Blueprint wird der erste klickbare Excel-Prototyp umgesetzt.

Sprint 3.0

- Der erste UX-Prototyp bleibt als `Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx` erhalten.
- Die zweite UX-Prototyp-Generation startet mit `Jenaplan_UX_Prototype_v0.2.xlsx`.
- Zielplattform ist Microsoft Excel für macOS.
- Python bleibt für Workbook, Datenstruktur, Styles und Generierung verantwortlich.
- VBA wird für spätere UI-Aufgaben vorbereitet, aber noch nicht umgesetzt.

Sprint 3.1

- Einziger Auftrag: Klassenübersicht bauen; ab Sprint 3.4 lautet die fachliche Bezeichnung Stammgruppenübersicht.
- Keine weiteren Bildschirme.
- Abschluss mit Review durch Laura.
- Die v0.2-Arbeitsmappe enthält nur die damalige Klassenübersicht.
- Schülerprofil, Beobachtungsdialog und Kompetenzansicht folgen in späteren Sprints.

Sprint 3.1a

- UX-Review der heutigen Stammgruppenübersicht.
- Optimierung auf Stammgruppen bis mindestens 28 Schüler.
- Kompaktes 4-spaltiges Referenzdesign.
- Keine Dashboard-, Analyse- oder Verwaltungsfunktionen in der Stammgruppenübersicht.

Sprint 3.1b

- Dokumentation der Produktentscheidungen aus Sprint 3.1 und Sprint 3.1a.
- Stammgruppenübersicht als Einstieg in den Arbeitsablauf festgeschrieben.
- Schülerverwaltung als separater Bereich für Schülerdaten festgelegt.
- Design Freeze für die Stammgruppenübersicht dokumentiert.

Sprint 3.1c bis 3.1f

- Live-Suche in der Stammgruppenübersicht ergänzt und abgesichert.
- Datenmodell-Schutz für Stammgruppenübersicht und Suche festgeschrieben.
- Schnellzugriff `Neue Beobachtung` als Produktentscheidung dokumentiert.

Sprint 3.2

- Schülerprofil als zweiter UX-Screen ergänzt.
- Testpfad Stammgruppenübersicht -> Schülerprofil -> Stammgruppenübersicht über `student_id` vorbereitet.
- Beobachtungsdialog bleibt zurückgestellt.

Sprint 3.3a

- Zielplattform, Architektur, Entwicklungsprozess und Datenmodell-Prinzipien konsolidiert.
- Keine funktionalen Änderungen.

Sprint 3.3b

- Manuell erzeugten VBA-Seed mit Python und `openpyxl keep_vba=True` validiert.
- Nachgewiesen, dass `xl/vbaProject.bin` beim Laden, Ändern und Speichern erhalten bleibt.

Sprint 3.3c

- Versionierbare VBA-Quellstruktur unter `vba/` vorbereitet.
- `.xlsm`-PoC auf Basis der bestehenden UX-Arbeitsmappe und des validierten Seeds vorbereitet.
- Keine Fachlogik in VBA.

Sprint 3.4

- Laura hat das aktuelle Design der Stammgruppenübersicht freigegeben.
- Das freigegebene Design wird als Design-System und Source of Truth für zukünftige Benutzeroberflächen dokumentiert.
- Die Domänensprache ersetzt `Klasse` durch `Stammgruppe`.
- `Stammgruppe` und `Kurs` werden als eigenständige fachliche Entitäten dokumentiert.
- `Kursübersicht`, Schülerverwaltung, Stammgruppenverwaltung und Kursverwaltung werden als zukünftige Produktbereiche aufgenommen.
- Keine Codeänderungen und kein Build.

Sprint 4.1

- Core Data Architecture erstmals technisch validiert.
- Builder erzeugt Hidden Data Sheets `data_students`, `data_groups` und `data_courses`.
- Builder erzeugt strukturierte Tabellen `tbl_students`, `tbl_groups` und `tbl_courses`.
- Stammgruppenübersicht und Schülerprofil lesen aus den Workbook-Datenquellen.
- VBA-Navigation über `student_id` bleibt funktionsfähig.
- Release-Artefakt: `output/Jenaplan_Kompetenzmanager_v0.4.xlsm`.

Sprint 4.2

- Schülerverwaltung als nächste Funktion vorbereitet.
- Fokus: erster transaktionaler Schreibprozess.
- Umfang: Schüler anlegen, Schüler ändern, Schüler archivieren.
- Keine physische Löschung.

Sprint 5

- Scope Freeze abgeschlossen.
- Dialog Framework begonnen.
- Sprint 5.1a konkretisiert Standardgroesse, Titelbereich, Abstaende, Labels, Pflichtfeldkennzeichnung, Button-Reihenfolge, Tab-Reihenfolge, Enter/Esc-Verhalten und modales Oeffnen.
- Erste Referenz-UserForm `Neuer Schueler` als nicht-produktive Referenzimplementierung vorbereitet.
- Sprint 5.1b prueft die produktive Anbindung und stoppt ohne Implementierung, weil kein freigegebener direkter VBA-zu-Python-Service-Aufruf existiert.
- Naechster Architekturspike: Command Queue zwischen UserForm und Python-Service-Schicht pruefen.
- Sprint 5.2a erzeugt `data/kompetenzmanager.sqlite` mit Students, Groups und Courses und baut daraus eine separate Excel-Projektion.
- Naechster Architekturspike: Python Bridge / CLI fuer UserForm-Auftraege nach SQLite pruefen.
- Sprint 5.3 fuehrt den Application Command Dispatcher als Zwischenschicht zwischen Command-Adaptern und Domain Services ein.
- `student.create` Adapter bis SQLite umgesetzt, ohne Fachlogik in CLI oder VBA zu verschieben.
- Architecture Baseline v2.0 fasst den validierten Zielzustand zusammen: Adapter -> Application -> Domain -> Infrastructure -> Projection -> Excel UI.
- UX-Prototypen sind fuer neue Eingabedialoge kuenftig verbindlicher Zwischenschritt vor der technischen Umsetzung.
- `output/Jenaplan_UX_Prototype_v0.1.xlsx` enthaelt das Blatt `Feature 1 – Neuer Schüler` als visuelle Vorlage fuer `dlg_neuer_schueler`.
- VBA-UserForms sind fuer Feature 1 auf macOS als instabil bewertet und nicht mehr primaeres Eingabe-Pattern.
- Worksheet-basierte Dialogseite `dlg_neuer_schueler` wird als neuer UI-Pfad vorbereitet.
- PySide6 Desktop-App-Spike erfolgreich validiert: App startet, Maske `Neuer Schüler` funktioniert, Speichern schreibt ueber ApplicationCommandDispatcher, StudentService und SQLiteStudentRepository nach SQLite.
- PySide6 wurde durch ADR-046 zur Hauptanwendung. Excel/VBA bleibt Export-, Berichts-, Referenz- oder Legacy-Projektion.
- `docs/PYSIDE6_APP_FEASIBILITY.md` dokumentiert die Umsetzungspruefung fuer App-Struktur, MVP-Navigation, Risiken und naechsten moeglichen Sprint, ohne eine finale Architekturentscheidung zu treffen.
- Dokumentenbereich fuer Schuelerdokumente dokumentiert.
- Studentenzentrierte Dokumenten- und Medienstruktur festgelegt.
- Beobachtungsdialog mit Kompetenzen, Bewertung, Notiz sowie Dokumenten und Medien nur vorbereitet.
- Keine Beobachtungserfassung, Schnellbeobachtung, Kompetenzzuordnung im Beobachtungsdialog, Dokument-Upload, Medienvorschau, Kursverwaltung, Stammgruppenverwaltung oder Berichte umsetzen.
