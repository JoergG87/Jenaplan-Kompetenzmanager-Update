# Projektdokumentation: Jenaplan-Kompetenzmanager

## Aktueller Produktstand

Aktuelle Produktversion: `v0.4`.

Kurzbeschreibung: PySide-Hauptanwendung mit lokaler SQLite-Datenbasis und archiviertem Excel-/Workbook-Legacy-Pfad.

Version `v0.4` repräsentiert historisch die abgeschlossene Core Data Architecture mit datengetriebener Workbook-Projektion. Die aktive Produktlinie ist inzwischen die PySide-Desktop-App.

## Projektziel

Der Jenaplan-Kompetenzmanager ist ein professionelles Python-Projekt zur strukturierten Verwaltung, Auswertung und späteren Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Das Projekt hat sich damit von einer Excel-zentrierten Arbeitsmappe zu einer modernen Desktop-App fuer macOS entwickelt. Excel/VBA liegt nur noch im Legacy-Archiv `legacy/excel/` und ist nicht mehr Zielrichtung fuer die Haupt-App.

Python bleibt verantwortlich fuer Datenmodell, Application Layer, Domain Layer, Persistenz, UI-nahe Adapter, PySide-Oberflaeche, Berichte, Exporte und Fachlogik.

Fachliche Logik wandert weder in PySide-Widgets noch nach VBA. Das Datenmodell bleibt unabhaengig von der Oberflaeche.

Sprint 0 dient ausschließlich dem Aufbau des technischen und dokumentarischen Fundaments. Es wird noch keine produktive Excel-Datei erzeugt.

## Leitbild

Das Projekt soll fachlich nachvollziehbar, technisch wartbar und langfristig erweiterbar sein.

Die Entwicklung folgt diesen Grundsätzen:

- Pädagogische Fachlichkeit steht vor technischer Komplexität.
- Daten werden strukturiert, nachvollziehbar und konsistent verarbeitet.
- Jede Version bleibt lauffähig.
- Änderungen werden dokumentiert und versioniert.
- PySide ist die Hauptanwendung.
- Excel ist nur noch historischer Legacy-Altstand und kein aktiver Produktpfad.

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

Das stundenplanbasierte Dashboard dient als ruhige Arbeitsstartseite. Es zeigt den unmittelbaren Unterrichtskontext, den heutigen Stundenplan, neutrale Dokumentationsabdeckung sowie direkte Wege zu Stammgruppen, Kursen, Kursverbuenden und dem bestehenden Beobachtungsprozess.

Das Dashboard ist eine reine Lese- und Navigationsansicht. Es veraendert weder Stundenplan noch Kompetenz- oder Beobachtungsdaten und zeigt keine Leistungswerte oder automatischen Entwicklungsurteile.

Dashboard und Uebersicht bleiben getrennte Hauptansichten: Das Dashboard ist der schnelle, stundenplanbasierte Arbeitsstart; die bestehende Uebersicht bleibt der direkte Stammgruppen- und Kursverbundzugang.

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

### Bericht, Lernentwicklungsgespraech und Ausgabe

Das Schuelerprofil bleibt eine Live-Arbeitsansicht. Es zeigt aktuelle Kompetenzstaende, Beobachtungen, Entwicklung, Dokumentationsabdeckung und Vorbereitungsmöglichkeiten, ist aber kein offizielles Dokument.

Die bestehende Berichtsvorschau bleibt eine abgeleitete Arbeitsprojektion. Sprint 7F.1 fuehrt zusaetzlich einen persistenten, weiter bearbeitbaren Berichtsentwurf mit Status `draft`, manuellen Gesamt- und Fachtexten sowie bewussten Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen ein. Sprint 7F.2 verbindet diesen Entwurf mit der verbindlichen UX aus `prototypes/learning_report_ux/`: Laura wechselt zwischen abschnittsweiser Bearbeitung und separater Dokumentvorschau, waehlt Faecher, konkrete Kompetenzen, Beobachtungsbelege und neutrale Diagramme bewusst aus und speichert keine automatisch erzeugten Aussagen. Dieser Arbeitsentwurf ist keine finale Berichtsdomain: Er besitzt weder Freigabe, Versionierung, Archivierung noch eingefrorene Ausgabe und berechnet keinen eigenen Kompetenzstatus. Langfristig wird der freigegebene Lernentwicklungsbericht als eigene fachliche Entitaet mit Pruef- und Freigabestatus sowie finaler Ausgabeversion gefuehrt. Beobachtungen und automatische Vorschlaege liefern Evidenz, aber keine fertigen paedagogischen Aussagen oder Berichtstexte.

Ein Lernentwicklungsgespraech ist fachlich kein Bericht. Seine Vorbereitung nutzt dieselben kanonischen Kompetenz- und Evidenzprojektionen ausschliesslich lesend. Sprint 7G.1 fuehrt dafuer einen eigenen persistenten LEG-Arbeitsentwurf mit Status `draft` ein: Gespraechsrahmen, manuelle Vorbereitung, bewusste Fach-/Themen-, Kompetenz-, Beobachtungs- und Diagrammauswahl sowie getrennte vorbereitete und gemeinsam vereinbarte Ziele, Unterstuetzungen und Vereinbarungen. Der Entwurf referenziert Live-Daten, ist kein eingefrorener oder finaler Gespraechsstand und besitzt weder Freigabe, Versionierung noch Archivierung. Sprint 7G.2 verbindet diesen Entwurf mit der verbindlichen Zwei-Seiten-UX aus `prototypes/learning_conference_ux/`: Vorbereitung und live synchronisierte Gespraechsmappe bleiben sichtbar getrennt, alle fachlichen Inhalte werden ueber den Draft gespeichert und Kompetenzstaende ausschliesslich kanonisch gelesen. Sprint 7G.3 begrenzt die Kompetenzauswahl auf aktive kindbezogene Kompetenzbeobachtungen im LEG-Zeitraum und aktuelle Bestaetigungen; bereits ausgewaehlte Draft-Referenzen bleiben ausserhalb dieses Sichtfilters erhalten.

PDF ist ausschliesslich ein Ausgabeformat. Der produktiv angebundene PDF-Renderer erhaelt ein neutrales `ReportOutputModel`, greift nicht direkt auf SQLite zu und berechnet oder interpretiert keine Fachlogik. Dieses Modell wird fuer die aktuelle Draft-Vorschau aus dem bearbeitbaren Entwurf und den freigegebenen Leseprojektionen aufgebaut; es ist noch kein eingefrorener oder freigegebener Ausgabestand. Fuer einen spaeteren finalen Bericht muss derselbe reine Renderer sein Eingangsmodell aus einer getrennt freigegebenen, versionierten und eingefrorenen Berichtsdomain erhalten. Professionelle Ausgaben koennen Deckblatt, Kompetenzuebersichten, Diagramme, Fachseiten, Lernentwicklung und klar getrennte LEG-Seiten enthalten.

Verbindliche Zielkette:

```text
SQLite
-> Repositories
-> kanonische Kompetenzprojektion
-> zeitraumbezogene Evidenzprojektion
-> Bericht-/LEG-Komposition
-> freigegebener Ausgabestand
-> PDF Renderer
```

Grafiken zeigen ausschliesslich Dokumentationsabdeckung und Entwicklungsevidenz, zum Beispiel Abdeckung je Fach, Entwicklung ueber Zeit oder Vergleiche fachlich passender Zeitpunkte. Sie erzeugen keine algorithmische Leistungsbewertung und duerfen nicht als solche gestaltet oder bezeichnet werden.

## Architektur

Das Projekt ist modular aufgebaut.

- `src/desktop_app/` enthaelt die PySide-Hauptanwendung mit Shell, Screens, Dialogen, Adaptern und ViewModels.
- `src/core/` enthaelt fachliche Python-Logik, Application-/Domain-/Infrastructure-Bausteine und SQLite-Repositories.
- `legacy/excel/` enthaelt alte Workbook-Builder, openpyxl-Projektionen, VBA-Quellen, Seeds und Hilfsskripte aus der Excel-Linie.
- `data/` enthält Eingabedaten und Konfigurationen.
- `docs/` enthält fachliche Begleitdokumentation.
- `docs/DESIGN_SYSTEM.md` beschreibt das freigegebene Design-System als verbindliche Referenz für zukünftige Ansichten.
- `tests/` ist für automatisierte Tests vorgesehen.
- `assets/` ist für statische Ressourcen vorgesehen.
- `BACKLOG.md` sammelt zukünftige Produktideen und Erweiterungen.
- `DISCOVERY.md` dokumentiert fachliche Erkenntnisse aus Anwenderinterviews und Discovery-Workshops.

Die Architektur vermeidet feste Zellreferenzen und UI-nahe Schattenlogik. Stattdessen sollen strukturierte Daten, eindeutige IDs, Repositories, ViewModels und wiederverwendbare Builder-/Export-Komponenten verwendet werden.

Die Stammgruppenübersicht und die Kursübersicht besitzen keine eigene Geschäftslogik. Sie stellen vorhandene Schülerdaten dar und werden aus diesen Daten generiert. Änderungen an Schülerdaten erfolgen künftig ausschließlich über die Schülerverwaltung.

VBA-Quellstände bleiben als Legacy-Altstand unter `legacy/excel/vba/` nachvollziehbar. Neue Features werden nicht mehr in VBA umgesetzt. Der Seed-Import-Pfad ist archiviert und kein aktiver Workflow.

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

## Architecture Baseline v3.0

Architecture Baseline v3.0 dokumentiert den aktuell freigegebenen Zielzustand nach der PySide-Architekturentscheidung.

Die Baseline entwickelt keine neue Architektur, sondern fasst die bereits umgesetzten Entscheidungen zusammen:

```text
Adapter Layer
(PySide Desktop Adapter / CLI / Export Adapter)
-> Application Layer
   (Dispatcher / Commands)
-> Domain Layer
   (Services / Validatoren)
-> Infrastructure Layer
   (SQLite / Repository)
-> Projection Layer
   (PySide ViewModels / Export Builder)
-> PySide UI / Exportprojektion
```

Verbindliche Prinzipien:

- SQLite ist die produktive lokale Source of Truth fuer fachliche Daten.
- Python bleibt die einzige fachliche Schreibschicht.
- Commands sind der Einstiegspunkt fachlicher Ablaeufe.
- Dispatcher routen Commands und enthalten keine Businesslogik.
- Services und Validatoren enthalten die fachliche Logik.
- Repositories kapseln Persistenz und SQLite-Zugriff.
- PySide ViewModels und Screens zeigen fachliche Daten, sind aber keine fachliche Datenquelle.
- Builder erzeugen aktive PySide-ViewModels oder explizit beauftragte Exporte.
- Excel bleibt archivierter Legacy-Altstand.
- VBA ist kein Zielpfad fuer neue Features, UI, Smoke-Tests oder produktive Workflows.

Historische Architecture v1 bleibt als Grundlage erhalten:

```text
Python
-> Workbook Builder
-> Excel
```

Architecture v2.0 bleibt als historischer Zwischenschritt dokumentiert. Architecture v3.0 richtet dieselben Application-, Domain- und Infrastructure-Layer auf PySide als Hauptanwendung aus; Excel ist unter `legacy/excel/` archiviert.

## Engineering Lessons Learned

Aenderungen an UI-Projektionen koennen indirekt Hidden-Spalten, Named Ranges, VBA-Navigation, Suchfunktion und weitere UI-Projektionen beeinflussen.

Kuenftige Aenderungen an Projection Buildern muessen deshalb immer eine Regression dieser Bereiche enthalten:

- Hidden-Spalten
- Named Ranges
- VBA-Navigation
- Suchfunktion
- UI-Projektionen

## Sprint 5 - Dialog Framework, Schuelerverwaltung und Dokumentenarchitektur

Historischer Stand der Excel-/VBA-Linie. Dieser Abschnitt beschreibt den damaligen Sprint-5-Kontext und ist nicht mehr Zielbild fuer neue UI-Entwicklung.

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

Damals geltender Grundsatz:

Der Kompetenzmanager ist eine Anwendung. Excel war in dieser Linie nur die Runtime.

Fachliche Eingaben sollten in dieser historischen Linie ueber modale VBA-UserForms und nicht direkt in Tabellen erfolgen.

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

- `legacy/excel/src/core/workbook_data.py`: historischer Seed-Datenstand mit neuer `student_id`-Strategie.
- `src/core/constants.py`: technische Feldnamen und ID-Praefixe verwenden.
- `legacy/excel/src/ui/screens/klassenuebersicht.py`: historische Projektion liest `student_id`, darf aber kein konkretes ID-Format voraussetzen.
- `legacy/excel/src/ui/screens/schuelerprofil.py`: historische Profilprojektion liest `student_id`, darf aber kein konkretes ID-Format voraussetzen.
- `legacy/excel/scripts/create_vba_framework_poc.py`: historisches Packaging bleibt unveraendert, solange Named Ranges und CodeNames stabil bleiben.
- `legacy/excel/vba/modules/Navigation.bas`: VBA verwendet weiterhin ausschliesslich `student_id`; keine Navigation ueber Namen oder Zellpositionen.
- `legacy/excel/vba/modules/UI.bas`: Slot-ID-Mechanismus bleibt unveraendert und liest die sichtbare `student_id`-Projektion.

Migrationsregel: Die Umstellung erfolgt kontrolliert in einem Schritt, damit Seed, Workbook-Tabellen, UI-Projektionen, Named Ranges und VBA-Navigation dasselbe ID-Format verwenden.

## Legacy-Analyse Student-ID

| Legacy-Name / Referenz | Fundstelle | Status | Entscheidung |
| --- | --- | --- | --- |
| `ui_profile_student_s001` | frueher `legacy/excel/src/ui/screens/schuelerprofil.py` | entfernt | wurde entfernt, da kein zentraler Navigationsanker |
| `s001` als `DEFAULT_STUDENT_ID` | frueher `legacy/excel/src/core/workbook_data.py` | migriert | `STU-000001` |
| `s001` in Seed-Daten | frueher `legacy/excel/src/core/workbook_data.py` | migriert | `STU-000001`-Strategie |
| `ui_student_slot_id_XX` | `legacy/excel/src/ui/screens/klassenuebersicht.py`, `legacy/excel/vba/modules/Globals.bas` | formatneutraler Slot-ID-Mechanismus | bleibt als Legacy-Namensmuster bestehen |
| `ui_profile_selected_student_id` | `legacy/excel/src/ui/screens/schuelerprofil.py`, `legacy/excel/vba/modules/Globals.bas` | formatneutraler Zielbereich fuer `student_id` | bleibt bestehen |
| VBA-Meldungstexte mit `student_id` | `legacy/excel/vba/modules/Navigation.bas` | technische Diagnose-/Fehlermeldung | bleibt bestehen |

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
- `pandas` für strukturierte Datenverarbeitung
- `pillow` für spätere Bild- oder Asset-Verarbeitung
- `PySide6` fuer die Desktop-App
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

- PySide ist die Hauptanwendung.
- SQLite ist die produktive lokale Datenbasis.
- Python verantwortet Datenmodell, Application Layer, Domain Layer, Persistenz, ViewModels, Adapter, UI-Projektionen, Berichte, Exporte und Fachlogik.
- Keine Businesslogik in PySide-Widgets.
- Keine direkte SQLite-Logik in Qt-Widgets.
- Excel/openpyxl nur im archivierten `legacy/excel/`-Pfad anfassen, wenn ein ausdruecklicher Legacy- oder Exportauftrag vorliegt.
- Keine neuen Excel-/VBA-Features und keine VBA-Smoke-Tests als Zielpfad.
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

Sprint 4 ist fachlich und technisch fuer den lehrplanbasierten Kompetenzkatalog abgeschlossen.

Aktueller Stand: Der CSV-Katalog umfasst die freigegebenen Sprint-4-Lehrplanuebernahmen fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz. Historische Kompetenzen bleiben als `legacy` lesbar; Religion war nicht Teil dieses Katalogabgleichs.
