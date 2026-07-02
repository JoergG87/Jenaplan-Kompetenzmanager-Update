# Projektdokumentation: Jenaplan-Kompetenzmanager

## Aktueller Produktstand

Aktuelle Produktversion: `v0.4`.

Kurzbeschreibung: Erste datengetriebene Version des Jenaplan-Kompetenzmanagers.

Version `v0.4` repräsentiert die abgeschlossene Core Data Architecture mit datengetriebener Workbook-Projektion.

## Projektziel

Der Jenaplan-Kompetenzmanager ist ein professionelles Python-Projekt zur strukturierten Verwaltung, Auswertung und späteren Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

PySide ist kuenftig die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Das Projekt entwickelt sich damit von einer Excel-zentrierten Arbeitsmappe zu einer modernen Desktop-App fuer macOS. Excel/VBA bleibt im Repository als Export-, Berichts- oder Legacy-Projektion erhalten, ist aber nicht mehr die Zielrichtung fuer die Haupt-App.

Python bleibt verantwortlich fuer Datenmodell, Application Layer, Domain Layer, Persistenz, UI-nahe Adapter, PySide-Oberflaeche, Workbook-/Export-Projektionen, Berichte und Build-Artefakte.

Fachliche Logik wandert weder in PySide-Widgets noch nach VBA. Das Datenmodell bleibt unabhaengig von der Oberflaeche.

Sprint 0 dient ausschließlich dem Aufbau des technischen und dokumentarischen Fundaments. Es wird noch keine produktive Excel-Datei erzeugt.

## Leitbild

Das Projekt soll fachlich nachvollziehbar, technisch wartbar und langfristig erweiterbar sein.

Die Entwicklung folgt diesen Grundsätzen:

- Pädagogische Fachlichkeit steht vor technischer Komplexität.
- Daten werden strukturiert, nachvollziehbar und konsistent verarbeitet.
- Jede Version bleibt lauffähig.
- Änderungen werden dokumentiert und versioniert.
- PySide ist die Zielrichtung fuer die Hauptanwendung.
- Excel kann weiterhin als Export-, Berichts- oder Legacy-Projektion dienen.

## Pädagogische Produktvision

### Zielgruppe

Der Kompetenzmanager richtet sich an Lehrkräfte an Jenaplan-Grundschulen und unterstützt die Kompetenzbeobachtung nach dem Thüringer Lehrplan.

Das Projekt verfolgt das Ziel, den Dokumentationsaufwand zu reduzieren und gleichzeitig eine qualitativ hochwertige Kompetenzdokumentation zu ermöglichen.

### Pädagogische Leitlinien

- Beobachtung vor Bewertung.
- Bewertungen entstehen aus dokumentierten Beobachtungen.
- Entwicklung ist wichtiger als Momentaufnahmen.
- Dokumentation soll den Unterricht unterstützen und nicht behindern.
- Kompetenzen werden lehrplanorientiert organisiert.
- Mehrfache Dateneingaben sollen vermieden werden.

### Arbeitsweise der Lehrkraft

Die tägliche Arbeit erfolgt überwiegend über Stammgruppen- und Schüleransichten.

Weitere Ansichten wie Schülerprofil, Stammgruppenübersicht, Kursübersicht, Berichte und Kompetenzbögen entstehen automatisch aus denselben Daten.

Die Stammgruppenübersicht dient als Einstieg in den Arbeitsablauf. Sie hilft dabei, einen Schüler innerhalb einer Stammgruppe schnell zu finden, auszuwählen und anschließend in das Schülerprofil zu wechseln.

Die Stammgruppenübersicht ist kein Dashboard, keine Verwaltungsansicht, keine Analyseansicht und keine Auswertungsseite.

Für den Unterricht darf die Stammgruppenübersicht zusätzlich einen Schnellzugriff `Neue Beobachtung` anbieten. Dieser arbeitet immer im Kontext des ausgewählten Schülers und öffnet denselben zentralen Beobachtungsdialog wie das Schülerprofil.

Kurse bezeichnen fachlich Mathe-/Deutsch-Unterrichtsgruppen innerhalb eines Kursverbunds.

Ein Kursverbund definiert, aus welchen Stammgruppen die Kurse gebildet werden. Eine Kursuebersicht zeigt deshalb nicht global alle Schueler mit demselben Kurslabel, sondern nur Schueler mit passendem Kurs aus den Stammgruppen des ausgewaehlten Kursverbunds.

## Fachliches Domänenmodell

### Der Kompetenzmanager ist ein Lernentwicklungsmanager.

Nicht einzelne Bewertungen stehen im Mittelpunkt.

Im Mittelpunkt steht die Lernentwicklung der Schülerinnen und Schüler.

Bewertungen sind lediglich ein Ergebnis dokumentierter Beobachtungen.

### Beobachtungen sind die fachliche Quelle aller Informationen.

Beobachtungen bilden die Grundlage für

- Kompetenzstände
- Schülerprofile
- Lernentwicklungsberichte
- Dashboards
- Auswertungen

### Kompetenzentwicklung

Kompetenzen entwickeln sich über einen längeren Zeitraum.

Das System muss deshalb Kompetenzverläufe speichern können.

Nicht nur den aktuellen Stand.

## Architektur

Das Projekt ist modular aufgebaut.

- `build.py` ist der zentrale Einstiegspunkt für spätere Build-Prozesse.
- `src/workbook.py` ist für die spätere Arbeitsmappen-Erzeugung vorgesehen.
- `src/core/` ist für die spätere Trennung fachlicher Python-Logik vorgesehen.
- `src/ui/` ist für die spätere Trennung UI-naher Python-Generatoren vorgesehen.
- `src/ui/screens/` ist für künftige Bildschirm-Generatoren vorgesehen.
- `src/dashboard.py` ist für das spätere Dashboard vorgesehen.
- `src/students.py` ist für Schülerdaten vorgesehen.
- `src/competencies.py` ist für Kompetenzdaten vorgesehen.
- `src/assessments.py` ist für Bewertungen vorgesehen.
- `src/reports.py` ist für Berichte vorgesehen.
- `src/settings.py` ist für zentrale Einstellungen vorgesehen.
- `src/styles.py` ist für visuelle Formatierungen vorgesehen.
- `src/desktop_app/` enthaelt die PySide-Hauptanwendung mit Shell, Screens, Dialogen, Adaptern und ViewModels.
- `data/` enthält Eingabedaten und Konfigurationen.
- `docs/` enthält fachliche Begleitdokumentation.
- `UX_BLUEPRINT.md` beschreibt die verbindliche UX-Grundlage für den ersten Prototyp.
- `docs/DESIGN_SYSTEM.md` beschreibt das freigegebene Design-System als verbindliche Referenz für zukünftige Ansichten.
- `vba/` enthält versionierbare VBA-Quellen für die spätere Interaktionsschicht.
- `seeds/` enthält validierte Seed-Arbeitsmappen für das spätere `.xlsm`-Packaging.
- `output/` ist für später generierte Dateien vorgesehen.
- `tests/` ist für automatisierte Tests vorgesehen.
- `assets/` ist für statische Ressourcen vorgesehen.
- `BACKLOG.md` sammelt zukünftige Produktideen und Erweiterungen.
- `DISCOVERY.md` dokumentiert fachliche Erkenntnisse aus Anwenderinterviews und Discovery-Workshops.

Die Architektur vermeidet feste Zellreferenzen. Stattdessen sollen strukturierte Daten, eindeutige IDs und wiederverwendbare Builder-Komponenten verwendet werden.

Die Stammgruppenübersicht und die Kursübersicht besitzen keine eigene Geschäftslogik. Sie stellen vorhandene Schülerdaten dar und werden aus diesen Daten generiert. Änderungen an Schülerdaten erfolgen künftig ausschließlich über die Schülerverwaltung.

VBA-Quelländerungen werden versioniert unter `vba/modules/` gepflegt. Der Seed muss dauerhaft das Bootstrap-Modul `SeedImport` enthalten; damit kann `scripts/import_vba_sources_to_seed.py` die versionierten Module `Globals`, `Navigation` und `UI` automatisch in `seeds/JenaplanSeed.xlsm` aktualisieren. Das Skript bricht ab, wenn dieser Bootstrap im Seed fehlt.

## Visuelle Produktlinie

Das freigegebene App-Icon ist die zentrale gestalterische Referenz fuer die PySide-Hauptanwendung.

Der Jenaplan Kompetenzmanager soll wie eine moderne paedagogische Entwicklungs-App wirken: ruhig, klar, wachstumsorientiert, datenbewusst und freundlich.

Die Gestaltung nimmt die Icon-Symbolik auf:

- Baum fuer Wachstum und Lernentwicklung
- Personen fuer Schuelerbezug und paedagogische Arbeit
- Diagramm fuer Auswertungen, Kompetenzverlaeufe und Berichte
- Kreis/Bogen fuer Ganzheitlichkeit, Ueberblick und Schutzraum
- farbige Blaetter fuer individuelle Lernwege und Entwicklungsfelder

Die Icon-Farbwelt aus Dunkelblau, Blau, Tuerkis, Gruen, Orange und hellen neutralen Hintergruenden bildet die visuelle Grundlage fuer Navigation, Karten, Kursfarben, Beobachtungen, Auswertungen und Statusbereiche.

## Architecture Baseline v2.0

Architecture Baseline v2.0 dokumentiert den aktuell validierten Zielzustand nach Sprint 5.

Die Baseline entwickelt keine neue Architektur, sondern fasst die bereits umgesetzten Entscheidungen zusammen:

```text
Adapter Layer
(VBA / CLI / zukuenftige Adapter)
-> Application Layer
   (Dispatcher / Commands)
-> Domain Layer
   (Services / Validatoren)
-> Infrastructure Layer
   (SQLite / Repository)
-> Projection Layer
   (Workbook Builder)
-> Excel UI
```

Verbindliche Prinzipien:

- SQLite ist die vorbereitete Source of Truth fuer fachliche Daten.
- Python bleibt die einzige fachliche Schreibschicht.
- Commands sind der Einstiegspunkt fachlicher Ablaeufe.
- Dispatcher routen Commands und enthalten keine Businesslogik.
- Services und Validatoren enthalten die fachliche Logik.
- Repositories kapseln Persistenz und SQLite-Zugriff.
- Builder erzeugen ausschliesslich Excel-Projektionen.
- Excel und VBA bleiben UI-, Projektions- und Interaktionsschicht.
- VBA schreibt weder direkt in SQLite noch in fachliche Workbook-Tabellen.

Historische Architecture v1 bleibt als Grundlage erhalten:

```text
Python
-> Workbook Builder
-> Excel
```

Architecture v2.0 erweitert diese Linie um Application, Domain und Infrastructure Layer, damit spaetere UserForms, CLI-Adapter und weitere Module ohne Sonderarchitektur denselben fachlichen Ablauf nutzen koennen.

## Engineering Lessons Learned

Aenderungen an UI-Projektionen koennen indirekt Hidden-Spalten, Named Ranges, VBA-Navigation, Suchfunktion und weitere UI-Projektionen beeinflussen.

Kuenftige Aenderungen an Projection Buildern muessen deshalb immer eine Regression dieser Bereiche enthalten:

- Hidden-Spalten
- Named Ranges
- VBA-Navigation
- Suchfunktion
- UI-Projektionen

## Sprint 5 - Dialog Framework, Schuelerverwaltung und Dokumentenarchitektur

Sprint 5 hat den Scope Freeze abgeschlossen und das Dialog Framework begonnen.

Der aktuelle Stand:

- Scope abgeschlossen
- Dialog Framework begonnen
- erste UserForm vorbereitet
- Schuelerverwaltung begonnen, aber noch nicht produktiv freigegeben
- Sprint 5.1a bereitet den verbindlichen Dialogstandard vor
- Sprint 5.1b wurde an der fehlenden VBA-zu-Python-Service-Bruecke gestoppt
- Sprint 5.2a prueft SQLite als moegliche zentrale Datenbasis fuer spaetere UserForm-Schreibprozesse
- Sprint 5.3 fuehrt den Application Command Layer als Bruecke zwischen Command-Adaptern und Domain Services ein

Grundsatz:

Der Kompetenzmanager ist eine Anwendung. Excel ist nur die Runtime.

Fachliche Eingaben erfolgen ueber modale VBA-UserForms und nicht direkt in Tabellen.

UserForms sammeln Eingaben, fuehren nur einfache Oberflaechenvalidierung durch, rufen freigegebene Services auf und aktualisieren anschliessend die betroffene Ansicht.

UserForms enthalten keine Businesslogik und schreiben nicht direkt in Workbook-Tabellen.

Erste Referenzimplementierung des Dialog Frameworks:

- Titel: Neuer Schueler
- Technischer Name: `frm_student_new`
- Felder: Vorname, Nachname, Stammgruppe, Kurs, Notiz, Dokumente
- Aktionen: Abbrechen, Speichern, Dokument hinzufuegen
- Status: vorbereitet, noch nicht produktiv freigegeben

Sprint 5.1a definiert `frm_student_new` als Referenzdialog fuer alle zukuenftigen Eingabemasken. Der Dialog darf UI-nahe Pflichtzustaende vorbereiten, enthaelt aber keine produktive Speicherlogik, keine StudentService-Anbindung und keinen Tabellenzugriff.

Sprint 5.1b pruefte die produktive Anbindung der UserForm an `StudentService.create_student()`. Der produktive Schreibpfad wird nicht umgesetzt, weil aktuell kein freigegebener, validierter Mechanismus existiert, mit dem Excel/VBA den Python-`StudentService` direkt aufrufen kann. Eine direkte VBA-Schreiblogik in `tbl_students` ist ausgeschlossen. Die naechste Architekturentscheidung betrifft die Laufzeitbruecke zwischen UserForm und Python-Service-Schicht; bevorzugt zu pruefen ist eine CSV- oder Hidden-Sheet-Command-Queue.

Sprint 5.2a prueft SQLite als moegliche neue Source of Truth. Der Spike verwendet `data/kompetenzmanager.sqlite`, weil das Projekt bereits `data/` als Datenverzeichnis fuehrt. Python erzeugt die Datenbank, schreibt Seed-Daten fuer Students, Groups und Courses und erzeugt daraus testweise die bestehende Excel-Projektion. VBA schreibt nicht direkt in SQLite; fuer produktive UserForm-Schreibprozesse bleibt eine Python Bridge oder CLI erforderlich.

Sprint 5.3 fuehrt eine Application-Schicht ein:

```text
VBA
-> Command Adapter
-> Application Command Dispatcher
-> Domain Services
-> Repositories
-> SQLite
-> Builder
-> Excel-Projektion
```

Die CLI ist nur ein moeglicher Adapter. Der Dispatcher nimmt Commands entgegen und leitet sie an passende Domain-Service-Handler weiter. Er enthaelt keine Fachlogik, schreibt nicht in SQLite und erzeugt keine Excel-Projektionen. VBA ruft spaeter Commands aus, bleibt aber reine Interaktionsschicht.

Dokumentenstruktur:

- Dateien werden nicht in Excel eingebettet.
- Excel speichert nur Referenzen und Metadaten in `data_media`.
- Dokumente werden studentenzentriert unter `Dokumente/<student_id>/` abgelegt.
- Hauptdokumente liegen unter `Hauptdokumente/`.
- Beobachtungsanhaenge liegen unter `Beobachtungsanhaenge/<observation_id>/`.

Die eigentliche Dokumentenverwaltung ist nicht Bestandteil von Sprint 5. Die Architektur und Grundstruktur werden vorbereitet.

Der Beobachtungsdialog wird nur vorbereitet. Kompetenzen muessen dort zwingend mitgedacht werden; die Beobachtungserfassung selbst bleibt ausserhalb von Sprint 5.

## Entity Blueprint: Student

Der Student-Blueprint ist die Referenzarchitektur fuer die erste fachliche Verwaltungs-Entity.

| Architekturteil | Festlegung |
| --- | --- |
| Entity | Student |
| Technische ID | `student_id` |
| ID-Format | `STU-000001` |
| Storage | `data_students` |
| Tabelle | `tbl_students` |
| Owner | Schuelerverwaltung |
| Validator | `StudentValidator` |
| Repository | `StudentRepository` |
| Service | `StudentService` |
| Builder | `StudentProjectionBuilder` |
| Navigation | `student_id` |

UI-Projektionen:

- Stammgruppenübersicht
- Schülerprofil
- Kursübersicht

Schreibprozesse:

- create
- update
- archive

Regel: Das Schema wird nicht als Python-Klasse implementiert. Die fachliche Definition erfolgt ueber `docs/DATA_REGISTRY.md`; technische Bezeichner werden in `src/core/constants.py` zentral gefuehrt.

Validator-Kontext:

- `StudentValidator` prueft `group_id` und `course_id` gegen Referenzdaten, die vom `StudentService` bereitgestellt werden.
- In Sprint 4.2 werden keine eigenen `GroupRepository`- oder `CourseRepository`-Klassen eingefuehrt.
- Der Validator validiert nur gegen bereitgestellte Referenzdaten und liest selbst keine Workbook-Tabellen.

UI-Regel fuer Sprint 4.2:

- Es wird keine neue Excel-Verwaltungsansicht erstellt.
- Es wird keine Testmaske erstellt.
- Der erste Architekturtest erfolgt ausschliesslich ueber `StudentValidator`, `StudentRepository` und `StudentService`.
- Eine Benutzeroberflaeche folgt erst nach Erweiterung von `docs/VIEW_DATA_OWNERSHIP.md` und `docs/UI_DATA_MAPPING.md`.

## ID-Migrationsplan Student

Die bisherigen Seed-IDs wie `s001` wurden in Sprint 4.2c kontrolliert migriert.

Die Migration auf `STU-000001` erfolgte gemeinsam mit der Implementierung des `StudentService`.

Betroffene Dateien und Komponenten:

- `src/core/workbook_data.py`: Seed-Daten auf neue `student_id`-Strategie umstellen.
- `src/core/constants.py`: technische Feldnamen und ID-Praefixe verwenden.
- `src/ui/screens/klassenuebersicht.py`: Projektion liest weiterhin `student_id`, darf aber kein konkretes ID-Format voraussetzen.
- `src/ui/screens/schuelerprofil.py`: Profilprojektion liest weiterhin `student_id`, darf aber kein konkretes ID-Format voraussetzen.
- `scripts/create_vba_framework_poc.py`: Packaging bleibt unveraendert, solange Named Ranges und CodeNames stabil bleiben.
- `vba/modules/Navigation.bas`: VBA verwendet weiterhin ausschliesslich `student_id`; keine Navigation ueber Namen oder Zellpositionen.
- `vba/modules/UI.bas`: Slot-ID-Mechanismus bleibt unveraendert und liest die sichtbare `student_id`-Projektion.

Migrationsregel: Die Umstellung erfolgt kontrolliert in einem Schritt, damit Seed, Workbook-Tabellen, UI-Projektionen, Named Ranges und VBA-Navigation dasselbe ID-Format verwenden.

## Legacy-Analyse Student-ID

| Legacy-Name / Referenz | Fundstelle | Status | Entscheidung |
| --- | --- | --- | --- |
| `ui_profile_student_s001` | frueher `src/ui/screens/schuelerprofil.py` | entfernt | wurde entfernt, da kein zentraler Navigationsanker |
| `s001` als `DEFAULT_STUDENT_ID` | frueher `src/core/workbook_data.py` | migriert | `STU-000001` |
| `s001` in Seed-Daten | frueher `src/core/workbook_data.py` | migriert | `STU-000001`-Strategie |
| `ui_student_slot_id_XX` | `src/ui/screens/klassenuebersicht.py`, `vba/modules/Globals.bas` | formatneutraler Slot-ID-Mechanismus | bleibt als Legacy-Namensmuster bestehen |
| `ui_profile_selected_student_id` | `src/ui/screens/schuelerprofil.py`, `vba/modules/Globals.bas` | formatneutraler Zielbereich fuer `student_id` | bleibt bestehen |
| VBA-Meldungstexte mit `student_id` | `vba/modules/Navigation.bas` | technische Diagnose-/Fehlermeldung | bleibt bestehen |

Die Legacy-Migration fuer Student-Seed-IDs ist mit Sprint 4.2c umgesetzt.

Architecture Gate fuer Sprint 4.2c:

- Builder-Regel ist geklaert.
- Keine Verwaltungsoberflaeche in Sprint 4.2.
- Validator-Kontext ist geklaert.
- Legacy-Migration ist vorbereitet, aber nicht ausgefuehrt.
- Student ist ohne weitere Architekturentscheidung implementierbar.

Ergebnis: PASS.

Offener Implementierungspunkt:

- Die Stammgruppenübersicht besitzt weiterhin 28 sichtbare Karten-Slots. Ein zusaetzlich per Service erzeugter 29. aktiver Seed-Schueler ist in `tbl_students` vorhanden, benoetigt fuer sichtbare Karten-Navigation aber eine spaetere Slot-/Seed-Entscheidung.

## Technischer Stack

- Python 3.11 oder neuer
- `openpyxl` für die spätere Excel-Erzeugung
- `pandas` für strukturierte Datenverarbeitung
- `pillow` für spätere Bild- oder Asset-Verarbeitung
- Markdown für Projektdokumentation
- CSV und JSON für strukturierte Eingabe- und Konfigurationsdaten

## Rollen

- Product Owner: Gibt neue Funktionen, fachliche Änderungen und Änderungen am Datenmodell frei.
- Entwicklung: Implementiert die freigegebenen Funktionen nach Projektregeln.
- Fachliche Review: Prüft pädagogische Verständlichkeit, Bewertungssystem und Lehrplanbezug.
- Technische Review: Prüft Wartbarkeit, Kompatibilität und Lauffähigkeit.

## Entwicklungsprinzipien

- Keine Implementierung ohne fachliche Freigabe.
- Keine Änderung am Datenmodell ohne Rücksprache.
- Jede Änderung wird im Changelog dokumentiert.
- Jede Version muss lauffähig bleiben.
- Funktionen werden sprintbasiert geplant und umgesetzt.
- Generierte Excel-Dateien werden nicht manuell verändert.
- Die spätere Darstellung wird für Microsoft Excel auf macOS ausgelegt.
- Fachliche Logik verbleibt vollständig im Python- und Datenmodell.
- VBA darf ausschließlich UI-Aufgaben wie Navigation, Buttons, Dialoge, Benutzerinteraktion und UserForms übernehmen.
- Das Datenmodell ist Source of Truth für fachliche Daten.
- Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.
- Strukturierte Tabellen und eindeutige IDs haben Vorrang vor festen Zellpositionen.
- Jede Ansicht besitzt genau eine Hauptaufgabe.
- Neue Funktionen dürfen die Hauptaufgabe einer Ansicht nicht verwässern.
- Eine Funktion besitzt genau eine Implementierung, darf aber mehrere Einstiegspunkte besitzen.

### Standard-Reihenfolge jeder Implementierung

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

## Versionierung

Das Projekt verwendet ab Version `v0.4` eine produktorientierte Versionsfolge.

Aktuelles Hauptartefakt:

- `output/Jenaplan_Kompetenzmanager_v0.4.xlsm`

Optionale aktuelle Kopie:

- `output/latest.xlsm`

Historische UX-Prototyp-Namen bleiben im Git-Verlauf erhalten, werden aber künftig nicht weitergeführt.

Änderungen werden in `CHANGELOG.md` dokumentiert. Grundsätzliche Architekturentscheidungen werden in `DECISIONS.md` festgehalten.

## Roadmap

Die verbindliche Roadmap befindet sich in `ROADMAP.md`.

Aktuelle Planung:

- Sprint 3.0: Architekturwechsel auf Microsoft Excel für macOS
- Sprint 3.1: Klassenübersicht als frühere Bezeichnung der heutigen Stammgruppenübersicht
- Sprint 3.2: Schülerprofil
- Sprint 3.3a: Architektur konsolidieren
- Sprint 5: Scope abgeschlossen, Dialog Framework begonnen, erste UserForm vorbereitet
- Weitere Produktbereiche erst nach fachlicher Freigabe und Review

## Bekannte offene Punkte v0.4

- Seed enthält aktuell 28 Testschüler; Demo-Seed und Minimal-Seed werden später getrennt.
- Kursfarben werden noch nicht dynamisch aus `tbl_courses[color_key]` im Workbook projiziert.
- Header `Stammgruppenübersicht` wird in der aktuellen Darstellung noch abgeschnitten.

## Bewertungssystem

Das Bewertungssystem wird in einem später freigegebenen Sprint fachlich ausgearbeitet.

Die Architekturentscheidung für das Bewertungssystem ist bereits festgelegt:

- `++`
- `+`
- `-`
- `--`

Die visuelle Darstellung erfolgt später über Ampelfarben. Die Bewertungssymbole sind fachliche Datenwerte und dürfen nicht durch reine Farbwerte ersetzt werden.

## Datenmodell

Das Datenmodell basiert auf strukturierten Datenquellen in `data/`.

Aktuelle Dateien:

- `data/competencies.csv` für Kompetenzdaten
- `data/colors.json` für Farbdefinitionen
- `data/config.json` für Projektkonfiguration

Das Datenmodell ist die fachliche Grundlage des Projekts.

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs. Das Datenmodell darf nicht ohne Rücksprache mit dem Product Owner geändert werden.

Neue UI-Elemente, Hilfstabellen, Formeln, VBA-Routinen und Screens dürfen das Datenmodell niemals umgehen. Alle Ansichten sind Projektionen des Datenmodells.

Die Domänensprache ersetzt `Klasse` durch `Stammgruppe`. Jeder Schüler gehört genau einer Stammgruppe und genau einem Kurs an. Der Kurs beschreibt den Jahrgang, die Stammgruppe beschreibt die organisatorische Zugehörigkeit.

Die zentralen Entitäten für Schülerzuordnung sind:

- Student mit `student_id`, Vorname, Nachname, `stammgruppe_id`, `kurs_id`
- Stammgruppe mit `stammgruppe_id`, Name
- Kurs mit `kurs_id`, Name und optionaler Farbe für spätere UI

Die Standardreihenfolge der Schüler in der Stammgruppenübersicht erfolgt alphabetisch nach Vorname. Diese Sortierung gilt als Projektstandard, weil Lehrkräfte Kinder im Unterricht überwiegend mit dem Vornamen suchen und ansprechen.

Schülerkarten werden nicht manuell gepflegt. Wenn Schüler in der Schülerverwaltung hinzugefügt, bearbeitet oder archiviert werden, aktualisieren sich Stammgruppenübersicht und Kursübersicht automatisch aus den vorhandenen Schülerdaten. Eine physische Löschung von Schülern ist nicht vorgesehen.

Stammgruppen und Kurse sind eigenständige fachliche Entitäten. Neue Stammgruppen werden über die Stammgruppenverwaltung angelegt, nicht automatisch beim Anlegen eines Schülers. Kurse werden über die Kursverwaltung gepflegt.

## Design-System

Das aktuelle Design der Stammgruppenübersicht wurde durch Laura freigegeben und ist die verbindliche Referenz für alle zukünftigen Ansichten.

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen. Es umfasst Farbwelt, Typografie, Kartenlayout, Kartenabstände, Desktop-App-Anmutung, 140-%-Zoom der Stammgruppenübersicht, Suchfeld, Weißraum und visuelle Hierarchie.

Neue Ansichten müssen sich an diesem Design-System orientieren. Designänderungen erfolgen ausschließlich in einem eigenen UX-Sprint.

## Projektregeln

Die dauerhaften Projektregeln sind in `AGENTS.md` festgelegt.

Zusammenfassung:

- Python erzeugt Workbook, Datenstruktur, Styles und Build-Artefakte.
- VBA ist nach erfolgreichem Packaging nur für UI-Aufgaben freigegeben.
- Keine fachliche Logik in VBA.
- Zielplattform ist Microsoft Excel für macOS.
- `openpyxl` verwenden.
- Keine festen Zellreferenzen.
- Strukturierte Tabellen bevorzugen.
- Datenmodell niemals ohne Rücksprache ändern.
- Design-System nicht ohne eigenen UX-Sprint ändern.
- Jede Änderung muss im Changelog dokumentiert werden.
- Jede Version muss lauffähig bleiben.
- Neue Funktionen nur nach Freigabe durch den Product Owner.

## Definition of Done

Eine Änderung gilt als abgeschlossen, wenn:

- die fachliche Anforderung umgesetzt oder dokumentiert ist,
- keine Projektregel verletzt wurde,
- die Projektdokumentation konsistent bleibt,
- das Changelog aktualisiert wurde,
- der Build-Einstiegspunkt weiterhin lauffähig ist,
- keine nicht freigegebenen Funktionen eingeführt wurden,
- keine Excel-Datei erzeugt wurde, sofern der Sprint dies nicht ausdrücklich vorsieht.

## Aktueller Sprint

Sprint 4.1 ist abgeschlossen.

Aktueller Stand: Sprint 5.3 - Application Command Layer als Architektur-Skelett eingefuehrt; produktive CLI und UserForm-Anbindung bleiben offen.
