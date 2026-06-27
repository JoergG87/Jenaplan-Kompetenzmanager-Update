# CHANGELOG

## Sprint 3.1b

### Added

- Produktentscheidung dokumentiert: Die Klassenübersicht ist ausschließlich Einstieg, Such- und Auswahlansicht.
- Produktentscheidung dokumentiert: Jede Ansicht besitzt genau eine Hauptaufgabe.
- Projektstandard dokumentiert: Schüler werden in der Klassenübersicht alphabetisch nach Vorname sortiert.
- Produktentscheidung dokumentiert: Schülerverwaltung erfolgt künftig in einer separaten Klassenverwaltung.
- Architekturprinzip dokumentiert: Die Klassenübersicht besitzt keine eigene Geschäftslogik und wird aus vorhandenen Schülerdaten generiert.
- Design Freeze für das aktuelle Referenzdesign der Klassenübersicht dokumentiert.

### Changed

- UX Blueprint zur Klassenübersicht an die Sprint-3.1/3.1a-Entscheidungen angepasst.

## Sprint 3.1a

### Added

- UX-Review der Klassenübersicht dokumentiert und in Layoutentscheidungen übertragen.
- `src/ui/theme.py` und `src/ui/components.py` als wiederverwendbare UI-Basis für Excel-Screens ergänzt.
- Dynamische UI-Anker für 28 Schülerkarten vorbereitet.

### Changed

- Klassenübersicht auf bis zu 28 Schüler optimiert.
- Schülerkarten deutlich kompakter gestaltet.
- Der separate Button `Schülerprofil` wurde entfernt; die gesamte Karte ist als spätere Klickfläche vorbereitet.
- Suchfeld auf eine kompakte, einzeilige Fläche reduziert.
- Raster auf eine 4-spaltige, unterrichtstaugliche Übersicht umgestellt.
- Screen-Code aus `src/ui/screens/klassenuebersicht.py` in Theme, Komponenten und Screen-Verantwortung getrennt.

### Deferred

- Sichtbarkeit und Platzierung von `Neue Beobachtung` bleiben als Produktentscheidung für Sprint 3.2 offen.
- Echte Navigation, VBA-Code und UserForms bleiben zurückgestellt.
- Schülerprofil, Beobachtungsdialog, Kompetenzansicht und fachliche Auswertungen bleiben unverändert außerhalb dieses Sprints.

## Sprint 3.1

### Added

- Klassenübersicht für `Jenaplan_UX_Prototype_v0.2.xlsx` als einzige v0.2-Ansicht umgesetzt.
- Hochwertiges Excel/macOS-Layout mit ausgeblendeten Gitternetzlinien, ausgeblendeten Zeilen- und Spaltenköpfen sowie ausgeblendeten Blattregistern erstellt.
- Stabile benannte UI-Anker für spätere VBA-Interaktion ergänzt.

### Changed

- v0.2-Build erzeugt keine Schülerprofil-, Beobachtungs-, Kompetenz- oder Dashboard-Blätter mehr.
- Projektstatus und Sprintplanung auf Sprint 3.1 aktualisiert.

## Sprint 3.0

### Added

- ADR-021 zur UI-Technologie ab UX-Prototyp v0.2 ergänzt.
- Vorbereitende Projektstruktur für `src/core/`, `src/ui/`, `src/ui/screens/` und `vba/` angelegt.
- Build-Ziele für `Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx` und `Jenaplan_UX_Prototype_v0.2.xlsx` vorbereitet.

### Changed

- Zielplattform auf Microsoft Excel für macOS umgestellt.
- Projektregeln und Dokumentation auf Python-Generator plus UI-VBA ohne fachliche Logik aktualisiert.
- Bestehender UX-Prototyp v0.1 wird beim Build als First Attempt erhalten.

## Sprint 2c

### Added

- Erster klickbarer UX-Prototyp auf Basis des UX Blueprint v1.0 erstellt.
- Prototyp-Versionierung auf `UX Prototype v0.1` umgestellt.
- Klassenübersicht, Schülerprofil, Neue Beobachtung und Kompetenzansicht als prototypische Excel-Bildschirme umgesetzt.

## Sprint 2b

### Added

- ADR-012 als UX- und Architekturentscheidung zu Single Purpose Views dokumentiert.
- UX_BLUEPRINT.md v1.0 als Grundlage für den ersten Excel-Prototyp erstellt.

## Sprint 2a

### Added

- Discovery Phase 1 dokumentiert.
- DISCOVERY.md eingeführt.
- Fachliche Erkenntnisse aus Anwenderinterviews dokumentiert.
- Unterrichtskontexte beschrieben.
- Kompetenzentwicklung präzisiert.

## Projektinfrastruktur

### Added

- Product Backlog eingeführt.
- BACKLOG.md als Bestandteil der Projektstruktur ergänzt.

## Sprint 1.2

### Added

- Fachliches Domänenmodell dokumentiert.
- Lernentwicklungsmanager als Produktvision definiert.
- Beobachtungen als Source of Truth festgelegt.
- Historisierung der Kompetenzentwicklung dokumentiert.
- Discovery-Erkenntnisse aus erster Lehreranalyse übernommen.

## Version 3.2

### Added

- Pädagogische Produktvision dokumentiert
- Fachliche Leitlinien ergänzt
- Produktentscheidungen erweitert
- Roadmap um langfristige Produktziele ergänzt
- VISION.md ergänzt

### Changed

- Ersten Excel-Generator implementiert
- WorkbookBuilder für Arbeitsmappenerzeugung erstellt
- Blattmodule für Dashboard, Schüler, Kompetenzen, Bewertungen, Einstellungen und Changelog umgesetzt
- Zentrale Stylestruktur für Arbeitsmappen und Tabellen eingeführt
- Build-Prozess für output/Jenaplan_v3.2.xlsx eingerichtet
- Sprintplanung und Projektdokumentation auf Sprint 1 aktualisiert

## Version 3.1

- Datenmodell erstellt
- Projektgenerator eingerichtet
- Projektdokumentation erstellt
- Architekturentscheidungen dokumentiert
- README und Projektregeln aktualisiert
