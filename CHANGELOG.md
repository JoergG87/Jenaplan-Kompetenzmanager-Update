# CHANGELOG

## Sprint 5.0 - Dialog- und Dokumentenarchitektur

### Added

- Standard fuer modale VBA-UserForms dokumentiert.
- Referenz-UserForm `frm_student_new` fuer den Zielzustand `Neuer Schueler` dokumentiert.
- Studentenzentrierte Dokumentenstruktur mit `Dokumente/<student_id>/Hauptdokumente/` und `Dokumente/<student_id>/Beobachtungsanhaenge/<observation_id>/` dokumentiert.
- Beobachtungsdialog als spaeterer Zielzustand mit Kompetenzen, Bewertung, Notiz sowie Dokumenten und Medien vorbereitet.
- Schnellbeobachtung / Gruppenbewertung als Backlog-Thema ergaenzt.
- ADR-035 fuer modale UserForms und studentenzentrierte Dokumentreferenzen ergaenzt.

### Changed

- `data_media` in der Workbook Data Registry von rein beobachtungsbezogenen Anlagen zu studentenzentrierten Dokument- und Medienreferenzen erweitert.
- Data Lifecycle, View Data Ownership und UI Data Mapping um Schuelerdokumente, Beobachtungsanhaenge und den Neuer-Schueler-Dialog ergaenzt.
- Technical Naming Registry um UserForm- und Control-Namen sowie Dokument-/Medienfelder erweitert.

### Not Changed

- Keine Implementierung, kein Build, keine Beobachtungserfassung, keine Schnellbeobachtung, kein vollstaendiges Dokumentenmanagement und keine Datei-Vorschau umgesetzt.

## VBA-Seed-Import-Automation

### Added

- `vba/modules/SeedImport.bas` als dauerhaftes Bootstrap-Makro fuer den Seed ergänzt.
- `scripts/import_vba_sources_to_seed.py` und `scripts/import_vba_sources_to_seed.applescript` zum automatischen Aktualisieren der versionierten VBA-Module im Seed ergänzt.

### Changed

- `vba/README.md` um den automatischen Seed-Import-Workflow und die Bootstrap-Grenze erweitert.
- `SeedImport` meldet blockierten Zugriff auf `ThisWorkbook.VBProject` mit einer expliziten Ursache statt eines rohen Excel-Fehlers 1004.

### Not Changed

- Keine fachliche Logik, keine Workbook-Datenquellen, keine UI-Projektionen und keine Designregeln geaendert.

## UX-Verbesserung - temporaeren UI-State zuruecksetzen

### Added

- Architekturregel fuer temporaeren UI-State in `VIEW_DATA_OWNERSHIP.md` ergänzt.
- VBA-Navigation `OpenClassOverview` ergänzt, die den Suchzustand der Stammgruppenuebersicht vor dem Ruecksprung leert.
- Technischer Anker `ui_profile_back_to_class_overview` fuer den Ruecksprung aus dem Schuelerprofil ergänzt.

### Changed

- `ConfigureStudentCardNavigation` konfiguriert zusaetzlich die klickbare Ruecksprungflaeche im Schuelerprofil.
- `OpenClassOverview` leert das Suchfeld merge-sicher ueber den gesamten Eingabebereich.

### Not Changed

- Keine fachlichen Daten, keine Student-Entity-Schichten und keine Datenquellen geaendert.

## Sprint 4.2c

### Added

- `StudentValidator`, `StudentRepository`, `StudentService` und `StudentProjectionBuilder` als Referenzimplementierung fuer die Entity Student ergänzt.
- Unit-Tests fuer create, update, archive, ID-Kollision und Workbook-Projektion ergänzt.

### Changed

- Seed-IDs kontrolliert von `s001` auf `STU-000001`-Format migriert.
- Gruppen- und Kurs-Seed-IDs auf `GRP-000001` und `CRS-000001`-Format umgestellt.
- `tbl_students` um `student_notes` und `archived_at` erweitert.
- Student-Projektionen verwenden technische Feldnamen aus `src/core/constants.py`.
- Legacy-Named-Range `ui_profile_student_s001` entfernt, da sie nicht als zentraler Navigationsanker verwendet wird.

### Not Changed

- Keine Excel-Verwaltungsansicht, keine Testmaske, keine VBA-Architekturänderung, kein `GroupRepository` und kein `CourseRepository` eingefuehrt.

## Sprint 4.2b Architecture Gate

### Changed

- Builder-Regel praezisiert: Builder veraendert keine fachlichen Entitaeten und erzeugt ausschliesslich Workbook-Struktur und Projektionen.
- Fuer Schuelerprojektionen `tbl_students`, `tbl_groups` und `tbl_courses` als lesende Quellen bestaetigt.
- Festgelegt, dass Sprint 4.2 keine neue Verwaltungsansicht und keine Testmaske erstellt.
- Validator-Kontext fuer `StudentValidator` dokumentiert: gueltige `group_id` und `course_id` kommen aus dem `StudentService`-Kontext.
- Legacy-Analyse fuer Student-ID-Referenzen dokumentiert.

### Not Changed

- Keine Implementierung, keine Tests, kein Build, keine VBA-Aenderung und keine Migration umgesetzt.

## Sprint 4.2a

### Added

- Student-Blueprint als Referenzarchitektur fuer die erste fachliche Verwaltungs-Entity dokumentiert.
- Verbindliche projektweite ID-Strategie mit `STU-000001`, `GRP-000001`, `CRS-000001`, `CMP-000001`, `OBS-000001` und `MED-000001` ergänzt.
- Zentrale technische Konstantendatei `src/core/constants.py` angelegt.
- ID-Migrationsplan fuer die spaetere Umstellung der Seed-IDs auf `STU-000001` dokumentiert.

### Changed

- Student-Felder in der Workbook Data Registry um `student_notes` und `archived_at` erweitert.
- Archivierung im Data Lifecycle konkretisiert: `active = FALSE`, `archived_at` als Zeitstempel, historische Daten bleiben erhalten.
- Project Constitution um den Entity-Aufbau `Entity -> Validator -> Repository -> Service -> Builder -> UI -> Navigation` ergänzt.

### Not Changed

- Keine Benutzerfunktion, kein Validator, kein Repository, kein Service, keine Schreiblogik, keine UI-Anpassung, keine VBA-Aenderung und kein Build umgesetzt.

## v0.4 - Core Data Architecture + datengetriebene Workbook-Projektion

### Added

- Core Data Architecture abgeschlossen und erstmals vollständig durch den Build validiert.
- Workbook Data Builder erzeugt `data_students`, `data_groups` und `data_courses` als versteckte Tabellenblaetter mit `tbl_students`, `tbl_groups` und `tbl_courses`.
- Workbook Data Registry in der physischen Workbook-Struktur umgesetzt.

### Changed

- Stammgruppenuebersicht und Schuelerprofil lesen die Beispieldaten aus den Workbook-Datenquellen statt aus direkt im UI definierten Schuelerdaten.
- Builder erzeugt UI-Projektionen aus den registrierten Datenquellen.
- Stammgruppenuebersicht liest Schueler aus `tbl_students`.
- Schuelerprofil liest den Profilkopf ueber `student_id` aus `tbl_students`.
- Workbook Data Registry und UI Data Mapping auf die Phase-1-Felder `active`, `group_name`, `course_name` und `color_key` geschärft.
- Build-Ausgabe auf `output/Jenaplan_Kompetenzmanager_v0.4.xlsm` vereinheitlicht.
- VBA-Navigation bleibt weiterhin funktionsfähig.

### Fixed

- Die Sortierung der Stammgruppenuebersicht erfolgt wieder vollstaendig im Python Projection Builder.
- Excel-SORTBY wurde entfernt, um eine stabile Zuordnung zwischen Schuelerkarte, `student_id` und VBA-Navigation sicherzustellen.

### Improved

- Stammgruppenuebersicht sortiert Schueler nach Kurs und anschliessend alphabetisch.
- Sortierung erfolgt ausschliesslich innerhalb der UI-Projektion.

### Known Open Points

- Seed enthält aktuell 28 Testschueler; Demo-Seed und Minimal-Seed werden spaeter getrennt.
- Kursfarben werden noch nicht dynamisch aus `tbl_courses[color_key]` im Workbook projiziert.
- Header `Stammgruppenübersicht` wird in der aktuellen Darstellung noch abgeschnitten.

### Not Changed

- Keine Verwaltungsfunktion, keine Dialoge, keine VBA-Erweiterung, keine Kursuebersicht und keine Beobachtungserfassung implementiert.

## Sprint 4.0c

### Added

- Entity-first-Prinzip, Entity/Storage/Projection-Trennung und Builder-Schicht als verbindliche Architekturprinzipien ergänzt.
- Transaktionales Denken fuer Schreibprozesse dokumentiert.
- Owner je zentraler Datenquelle in der Workbook Data Registry ergänzt.
- Änderungs-Lifecycles fuer Schueler, Stammgruppe, Kurs und Kompetenz ergänzt.
- ADR-032 Entity-first-Architektur, ADR-033 Builder-Schicht und ADR-034 offene Historisierung von Bezeichnern ergänzt.
- Backlog-relevante Architekturanforderungen ohne Feature-Spezifikation aufgenommen.

### Changed

- View Ownership fachlich begrenzt: Ansichten duerfen nur fachlich begruendete Datenquellen lesen.
- Codex-Regeln um Dokumentationsbegrenzung ab Sprint 4.1 erweitert.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Excel-Datei, kein Build und keine Produktfunktion geaendert.

## Sprint 4.0b

### Added

- ADR-031 `Dokumentation geht Implementierung voraus` ergänzt.
- Verbindliche Implementierungsreihenfolge fuer neue Funktionen dokumentiert.

### Changed

- Technische Namenskonvention finalisiert: technische Namen sind englisch, ASCII-kompatibel und stabil; sichtbare Begriffe duerfen sich aendern.
- Physische Workbook-Datenbank finalisiert: `data_*`-Quellen werden als versteckte Tabellenblaetter mit `tbl_*`-Tabellen angelegt.
- Legacy-Regeln fuer bestehende technische Namen wie `wsClassOverview` und `ui_class_search` dokumentiert.
- View Ownership um die Regel erweitert, dass Ansichten nur dokumentierte Datenquellen verwenden duerfen.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Workbook-Artefakte, kein Build und keine Produktfunktion geaendert.

## Sprint 4.0a

### Added

- View Data Ownership fuer Ansichten, erlaubte Datenquellen, Schreibrechte, IDs und UI-Projektionen erstellt.
- Data Lifecycle fuer zentrale Schreibprozesse wie Schueleranlage, Archivierung, Beobachtungserfassung, Kompetenzergänzung und Medienanlage erstellt.

### Changed

- Project Constitution um Identitaets-, Projektions-, Erweiterbarkeits- und Schattenlogik-Regeln vertieft.
- Workbook Data Registry um Foreign Keys, Schreib-/Leseprozesse, erlaubte UI-Projektionen und Erweiterungsregeln je Datenquelle vertieft.
- UI Data Mapping um Projektionstyp, Schreibregel und verantwortliche Datenquelle erweitert.
- Codex-Arbeitsregeln in `AGENTS.md` um View Ownership und Data Lifecycle erweitert.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Excel-Datei, kein Build und keine Produktfunktion geaendert.

## Sprint 4.0

### Added

- Projektverfassung fuer Source-of-Truth-Regeln und Architekturprinzipien erstellt.
- Technical Naming Registry fuer technische Namen, Praefixe, IDs, Named Ranges und Shape-Muster erstellt.
- Workbook Data Registry fuer zentrale Datenquellen erstellt.
- UI Data Mapping fuer die Herkunft sichtbarer UI-Informationen erstellt.

### Changed

- VBA-Dokumentation um den Standard fuer spaetere Absprungpunkte ergaenzt.
- Codex-Arbeitsregeln in `AGENTS.md` um Registry-Pruefungen vor Codeaenderungen ergaenzt.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Excel-Datei und keine Produktfunktion geaendert.

## Sprint 3.5g

### Changed

- Initialisierungsabhängigkeit in `OpenStudentProfileById` beseitigt: Das Zielblatt wird aus dem technischen Profil-Named-Range abgeleitet und vor der Nutzung geprüft.
- Named-Range-Zugriffe in `Navigation.bas` und `UI.bas` ohne `On Error Resume Next` auf explizite Workbook-Namenssuche umgestellt.

### Not Changed

- Keine Doppelaufrufe, keine `Workbook_Open`-Logik, keine Designänderung und keine Fachlogik umgesetzt.

## Sprint 3.5f

### Changed

- Sichtbare Bezeichnung der bisherigen Übersicht auf `Stammgruppenübersicht` finalisiert.
- Schülerkarten zeigen in der Stammgruppenübersicht den Kurs statt der Stammgruppe.
- Kartenfarben der Schülerkarten werden aus der Kurszuordnung abgeleitet vorbereitet.
- UX-Dokumentation zur sichtbaren Terminologie, Kursanzeige und kursbasierten Kartenfarbe aktualisiert.

### Not Changed

- Keine neue Ansicht, keine neue Fachfunktion, keine Designänderung, keine VBA-Navigation und keine technischen Navigationsnamen geändert.

## Sprint 3.5e

### Changed

- `ConfigureStudentCardNavigation` für den Erstaufruf stabilisiert: numerische Office-Ersatzkonstanten zentralisiert und technische Anker defensiv geprüft.
- Die Klassenübersicht für die Shape-Erzeugung wird aus dem technischen Pfeil-Anker ermittelt, ohne sichtbare Blattnamen zu verwenden.

### Not Changed

- Kein `Auto_Open`, keine AppleScript-Automation, keine Designänderung und keine Fachlogik umgesetzt.

## Sprint 3.5d

### Changed

- Klickfläche der VBA-Schülerkartennavigation auf den sichtbaren Pfeil der jeweiligen Karte begrenzt und nach vorn gelegt.
- Temporäre Diagnose für Schülerkarten-Navigation ergänzt: geklicktes Shape, erkannter Slot und gelesene `student_id` werden beim Test angezeigt.

### Not Changed

- Keine Designänderung, keine Suche-Änderung, kein `Auto_Open`, keine Beobachtungslogik und keine neue Fachfunktion umgesetzt.

## Sprint 3.5c

### Changed

- `UI.bas` compile-sicher für Excel macOS bereinigt: Excel-Objekte werden spät gebunden, problematische Variablennamen vermieden und Office-Konstanten durch kommentierte numerische Werte ersetzt.

### Not Changed

- Keine Import-Automation, kein `Auto_Open`, keine Designänderung, keine Fachlogik und keine Beobachtungslogik umgesetzt.

## Sprint 3.5b

### Changed

- VBA-Variablennamen in der Karten-Navigation compile-freundlich bereinigt und Kollisionen mit Excel-Objekttypen vermieden.

## Sprint 3.5a

### Changed

- VBA-Navigation nutzt technische Sheet-CodeNames statt sichtbarer Blattnamen mit Umlauten.
- Defensive Meldungen ergänzt, wenn keine `student_id` gelesen werden kann oder der technische Profil-Zielbereich fehlt.

## Sprint 3.5

### Added

- VBA-Navigation für Schülerkarten vorbereitet: sichtbare Karten-Slots erhalten versteckte `student_id`-Projektionen und werden über zentrale VBA-Logik geöffnet.
- Schülerprofil erhält eine definierte technische Zielzelle für die aktuell übergebene `student_id`.

### Changed

- Direkter Hyperlink-Testpfad von der Schülerkarte zum Schülerprofil wurde durch VBA-Navigation ersetzt.
- Versionierte VBA-Quellen `Globals`, `Navigation` und `UI` um zentrale Karten-Navigation erweitert.

### Not Changed

- Keine Beobachtungslogik, keine UserForms, keine Kursübersicht und keine Designänderungen umgesetzt.

### Technical Notes

- Der `.xlsm`-Seed muss nach VBA-Quelländerungen in Excel aktualisiert werden; ein automatischer Import der geänderten `.bas`-Quellen in `vbaProject.bin` konnte in dieser Umgebung nicht validiert werden.

## Sprint 3.4

### Added

- Design-System als verbindliche Referenz für alle zukünftigen Ansichten dokumentiert.
- Stammgruppe und Kurs als eigenständige fachliche Entitäten dokumentiert.
- Kursübersicht als zukünftige Hauptansicht aufgenommen.
- Backlog um Schülerverwaltung, Stammgruppenverwaltung, Kursverwaltung und Kursübersicht erweitert.

### Changed

- Domänensprache von Klasse auf Stammgruppe präzisiert.
- Bisherige Klassenübersicht künftig als Stammgruppenübersicht dokumentiert.
- Datenmodell-Dokumentation um `stammgruppe_id` und `kurs_id` für Schüler erweitert.

### Not Changed

- Kein Code, keine VBA-Dateien, kein Seed und kein Build wurden in Sprint 3.4 geändert.

## Sprint 3.3f

### Changed

- Klassenübersicht öffnet im UX-Prototyp wieder mit 140 % Zoom gemäß freigegebener Design-Referenz.

## Sprint 3.3d

### Changed

- VBA-Seed-Bereinigung geprüft und dokumentiert.
- Packaging-Skript gegen alte Seed-Strukturen abgesichert: `Globals`, `Navigation` und `UI` müssen im Seed vorhanden sein; `Modul1` darf nicht mehr registriert sein.
- Workbook- und Worksheet-CodeNames werden im PoC soweit technisch möglich über `openpyxl` gesetzt.
- `seeds/JenaplanSeed.xlsm` als bereinigte Modulbasis validiert: `Globals`, `Navigation` und `UI` sind registriert; `Modul1` ist nicht mehr als Modul registriert.
- Zielarbeitsmappe `Jenaplan_UX_Prototype_v0.3_VBA_Framework.xlsm` erfolgreich mit `xl/vbaProject.bin`, `Klassenübersicht` und `Schülerprofil` erzeugt.

### Technical Notes

- Excel-Objekte des Seeds bleiben auf die Seed-Arbeitsmappe beschränkt.
- Die fachlich relevanten Excel-Objekte entstehen in der generierten Framework-Datei und werden dort als `DieseArbeitsmappe`, `wsClassOverview` und `wsStudentProfile` gesetzt.
- Alte Textfragmente können im binären `vbaProject.bin` noch per `strings` sichtbar sein; maßgeblich ist die registrierte `Module=`-Struktur.

## Sprint 3.3c

### Added

- VBA-Seed-Validierung dokumentiert: Python kann eine `.xlsm` mit `keep_vba=True` laden, verändern und speichern, ohne `xl/vbaProject.bin` zu verlieren.
- `.xlsm` als künftiges Zielartefakt vorbereitet; `.xlsx` bleibt Fallback, bis das VBA-Framework stabil ist.
- Versionierbare VBA-Quellstruktur unter `vba/` ergänzt.
- Erste VBA-Quellmodule angelegt: `Globals.bas`, `Navigation.bas`, `UI.bas`.
- Separaten PoC-Packaging-Schritt für `Jenaplan_UX_Prototype_v0.3_VBA_Framework.xlsm` ergänzt.

### Not Changed

- Keine Produktlogik, keine Fachlogik und keine UserForms umgesetzt.
- `build.py`, `src/` und bestehende UX-Screens nicht geändert.
- Die neuen `.bas`-Quellen sind noch nicht in das binäre `vbaProject.bin` importiert; der PoC erhält zunächst das validierte Seed-VBA-Projekt.

## Sprint 3.3a

### Changed

- Zielplattform dauerhaft auf Microsoft Excel für macOS festgelegt.
- Konsolidierte Zielarchitektur dokumentiert: Python für Build-System, Workbook-Erzeugung, Datenmodell, UI-Projektionen, Styles, Berichte und Fachlogik; VBA nach erfolgreichem Packaging ausschließlich für Interaktion.
- Standard-Reihenfolge jeder Implementierung dokumentiert.
- Datenmodell als zentrale fachliche Grundlage hervorgehoben.
- Projektdokumentation bereinigt und Roadmap auf den aktuellen UX-Prototyp-Pfad ausgerichtet.

### Not Changed

- Keine funktionalen Änderungen.
- Kein Python, keine Excel-Dateien und keine VBA-Implementierung geändert.

## Technischer Spike VBA-Packaging

### Added

- ADR-027 um das Packaging-Ergebnis ergänzt: Ein `.xlsm`-PoC ist ohne echtes `vbaProject.bin` oder validierte `.xlsm`-Seed-Datei nicht aussagekräftig.
- Dokumentiert, dass `openpyxl` vorhandene VBA-Projekte mit `keep_vba=True` erhalten kann, aber kein neues VBA-Projekt erzeugt.
- Künftigen Build-Prozess dokumentiert: Python erzeugt Workbook, Datenmodell, UI-Projektionen und Styles; der Packaging-Schritt übernimmt ein validiertes VBA-Projekt ausschließlich als Interaktionsschicht.

### Not Created

- Kein `.xlsm`-PoC erzeugt, da im Repository aktuell kein `vbaProject.bin`, keine `.xlsm`-Vorlage und kein exportiertes VBA-Projekt vorhanden ist.

## ADR-Spike VBA

### Added

- ADR-027 zur Einführung von VBA als Interaktionsschicht ergänzt.
- Variantenbewertung `.xlsx` mit Formeln gegenüber `.xlsm` mit VBA dokumentiert.
- Empfehlung dokumentiert: Python bleibt für Workbook, Datenmodell, UI-Projektionen, Styles und Build-Artefakte verantwortlich; VBA übernimmt ausschließlich Interaktion.
- Technisches Spike-Ergebnis dokumentiert: lokales Excel ist erreichbar, automatisierte `.xlsm`-Erzeugung mit eingebettetem VBA ist ohne `vbaProject.bin` oder freigegebene VBA-Projekt-Injektion noch nicht validiert.

## Sprint 3.2

### Added

- Schülerprofil als zweiter UX-Screen in `Jenaplan_UX_Prototype_v0.2.xlsx` ergänzt.
- Klickbarer Testpfad von der Klassenübersicht zum Schülerprofil für `student_id s001` umgesetzt.
- Beispielhafte Beobachtungskarten im Schülerprofil ergänzt.
- Zurück-Link vom Schülerprofil zur Klassenübersicht ergänzt.

### Deferred

- Zentraler Beobachtungsdialog bleibt zurückgestellt.
- Dynamische Navigation für alle Schüler bleibt zurückgestellt; Sprint 3.2 bindet den Testpfad bewusst über `student_id s001` an.

## Sprint 3.1f

### Added

- Produktentscheidung dokumentiert: `Neue Beobachtung` darf als Schnellzugriff aus der Klassenübersicht und als Aktion im Schülerprofil erreichbar sein.
- Architekturentscheidung dokumentiert: Beide Einstiege öffnen denselben zentralen Beobachtungsdialog.
- Dokumentiert, dass die Klassenübersicht ausschließlich `student_id` an den Beobachtungsdialog übergibt und keine eigene Beobachtungslogik enthält.

## Sprint 3.1e

### Changed

- Verbindung zwischen verborgener UI-Projektion und sichtbaren Schülerkarten repariert.
- Live-Suche auf einfache Treffer-Hilfsspalten und `INDEX`/`MATCH` umgestellt.
- Suche auf den Vornamen ausgerichtet, passend zur Standardsortierung der Klassenübersicht.
- Leerer Suchzustand zeigt wieder alle 28 aktiven Schüler.
- Kein-Treffer-Zustand zeigt `Kein Schüler gefunden`.

## Sprint 3.1d

### Added

- Datenmodell-Schutz für die Klassenübersicht dokumentiert.
- Verborgene UI-Projektion der Klassenübersicht um `student_id`, `first_name`, `last_name`, `display_name`, `class_id`, `status` und `search_key` abgesichert.
- ID-basierte UI-Anker für Schülerkarten ergänzt.

### Changed

- Schülernamen werden nicht mehr als technische Identität verwendet.
- Sichtbare Karten und Live-Suche leiten sich ausschließlich aus der verborgenen UI-Projektion ab.

## Sprint 3.1c

### Added

- Live-Suche in der Klassenübersicht ergänzt.
- Suchfeld filtert die Schülerkarten automatisch ohne Suchbutton.
- Sortierung nach Vorname technisch über die alphabetisch sortierte Schülerdatenquelle der Klassenübersicht umgesetzt.

### Changed

- Klassenübersicht bleibt optisch im v0.2-Referenzdesign; ergänzt wurde ausschließlich die Suchfunktion.

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

- Sichtbarkeit und Platzierung von `Neue Beobachtung` blieben bis zur Produktentscheidung in Sprint 3.1f offen.
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
