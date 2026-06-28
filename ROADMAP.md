# Roadmap

## Zielplattform und Architektur

Microsoft Excel für macOS ist die verbindliche Zielplattform.

Python bleibt verantwortlich für Build-System, Workbook-Erzeugung, Datenmodell, UI-Projektionen, Styles, Berichte und Fachlogik.

VBA übernimmt ausschließlich Navigation, Buttons, Dialoge, UserForms und Benutzerinteraktion.

Der VBA-Seed wurde praktisch validiert. `.xlsm` ist ab Version `v0.4` das Hauptartefakt.

Das Datenmodell ist die fachliche Grundlage des Projekts. Alle Ansichten sind Projektionen dieses Datenmodells.

Das Design-System ist die visuelle Grundlage des Projekts. Alle zukünftigen Ansichten orientieren sich am freigegebenen Design der Stammgruppenübersicht.

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
- Stammgruppenverwaltung
- Kursverwaltung
- Kursübersicht

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
