# Data Registry

Dieses Dokument definiert die verbindlichen Datenquellen des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Source of Truth. Workbook-Tabellen sind historische Legacy-Projektionen unter `legacy/excel/`.

UI-Ansichten sind Projektionen dieser Datenquellen. Sie duerfen selbst keine fachliche Datenquelle werden.

## Schreib- und Leseprinzip

Python schreibt fachliche Daten ausschliesslich ueber Application, Domain, Repository und SQLite.

PySide-Adapter und ViewModels lesen fachliche Daten ueber freigegebene Adapter, Repositories oder Query-Schichten.

Export-Builder duerfen nur nach ausdruecklicher Freigabe Projektionen aus SQLite erzeugen. Der alte Workbook-Builder ist archiviert.

VBA greift niemals direkt auf fachliche Tabellen oder SQLite zu.

VBA schreibt keine fachlichen Daten. Neue VBA-Schreibprozesse werden nicht mehr verfolgt.

Jede Datenquelle braucht einen registrierten Primary Key.

Alle Foreign Keys muessen in diesem Dokument explizit dokumentiert sein.

## SQLite Datenbasis

SQLite ist die produktive lokale Datenbasis.

Spike-Pfad:

```text
data/kompetenzmanager.sqlite
```

Der Pfad verwendet das bestehende Projektverzeichnis `data/`. Der alternative Vorschlag `Daten/kompetenzmanager.sqlite` wird im Spike nicht eingefuehrt, weil dafuer keine bestehende Projektkonvention vorliegt.

Gepruefte Tabellen:

| SQLite-Tabelle | Entity | Bisherige Workbook-Projektion |
| --- | --- | --- |
| `students` | Student | `data_students` / `tbl_students` |
| `groups` | Group | `data_groups` / `tbl_groups` |
| `courses` | Course | `data_courses` / `tbl_courses` |
| `course_groups` | CourseGroup | keine Workbook-Projektion |
| `course_group_student_groups` | CourseGroupStudentGroup | keine Workbook-Projektion |
| `course_group_courses` | CourseGroupCourse | keine Workbook-Projektion |
| `competencies` | Competency | `data_competencies` / `tbl_competencies` |
| `observations` | Observation | `data_observations` / `tbl_observations` |
| `observation_competency_ratings` | ObservationCompetencyRating | `data_observation_competencies` / `tbl_observation_competencies` |
| `student_competency_confirmations` | StudentCompetencyConfirmation | keine Workbook-Projektion |
| `documents` | Document / Media | `data_media` / `tbl_media` |

Regel:

SQLite ist die fachliche Source of Truth. Es darf keine parallele fachliche Source of Truth neben SQLite geben. `data_*`-Sheets und `tbl_*`-Tabellen sind Excel-/Workbook-Projektionen aus SQLite oder historische Legacy-Artefakte.

Produktive PySide-Datenbanken initialisieren `students` leer. Stammdaten-Defaults fuer `groups`, `courses` und Kursverbuende duerfen angelegt werden, Demo-Schueler jedoch nur ueber explizite Seed-/Testpfade.

VBA schreibt nicht direkt in SQLite.

Python bleibt fachliche Schreibschicht.

PySide-Dialoge verwenden fuer produktive Schreibprozesse freigegebene Adapter, Commands, Services und Repositories.

Beobachtungen werden nicht hart geloescht. `observations.active = 0` blendet eine Beobachtung aus aktiven Profil- und Kompetenzuebersichten aus; die zugehoerigen `observation_competency_ratings` bleiben historisch erhalten.

VBA-UserForms und worksheet-basierte Dialogseiten sind historische Artefakte der Excel-Linie und kein Zielpfad fuer neue Features.

Feature 1.4a gab historisch fuer `student.create` den Runtime Adapter und den Projection Refresh Contract frei. Dieser Pfad liegt inzwischen unter `legacy/excel/` und ist kein aktiver Standardpfad.

Fuer diesen Schreibprozess ist SQLite die fachliche Source of Truth.

`data_*`-Sheets und `tbl_*`-Tabellen in der geoeffneten Arbeitsmappe sind danach Projection Output aus SQLite und duerfen nur ueber Python-erzeugte Projection-Refresh-Pakete aktualisiert werden.

Minimales Spike-Schema:

```text
students(
  student_id TEXT PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  group_id TEXT NOT NULL,
  course_id TEXT NOT NULL,
  student_notes TEXT,
  active INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_at TEXT
)

groups(
  group_id TEXT PRIMARY KEY,
  group_name TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL
)

courses(
  course_id TEXT PRIMARY KEY,
  course_name TEXT NOT NULL,
  color_key TEXT,
  color_name TEXT NOT NULL,
  color_hex TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL
)

course_groups(
  course_group_id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL
)

course_group_student_groups(
  course_group_id TEXT NOT NULL,
  student_group_id TEXT NOT NULL,
  PRIMARY KEY(course_group_id, student_group_id),
  FOREIGN KEY(course_group_id) REFERENCES course_groups(course_group_id),
  FOREIGN KEY(student_group_id) REFERENCES groups(group_id)
)

course_group_courses(
  course_group_id TEXT NOT NULL,
  course_id TEXT NOT NULL,
  PRIMARY KEY(course_group_id, course_id),
  FOREIGN KEY(course_group_id) REFERENCES course_groups(course_group_id),
  FOREIGN KEY(course_id) REFERENCES courses(course_id)
)

competencies(
  competency_id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  subject_name TEXT NOT NULL,
  label TEXT NOT NULL,
  description TEXT NOT NULL,
  learning_area TEXT NOT NULL,
  competency_group TEXT,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL,
  is_core_subject INTEGER NOT NULL
)

observations(
  observation_id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL,
  date TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  context TEXT,
  note TEXT,
  active INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(student_id) REFERENCES students(student_id)
)

observation_competency_ratings(
  observation_id TEXT NOT NULL,
  competency_id TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  subject_display_name TEXT NOT NULL,
  learning_area TEXT NOT NULL,
  competency_group TEXT,
  competency_text TEXT NOT NULL,
  rating TEXT NOT NULL,
  PRIMARY KEY(observation_id, competency_id),
  FOREIGN KEY(observation_id) REFERENCES observations(observation_id)
)

student_competency_confirmations(
  student_id TEXT NOT NULL,
  competency_id TEXT NOT NULL,
  confirmed_rating TEXT NOT NULL,
  confirmed_at TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(student_id, competency_id),
  FOREIGN KEY(student_id) REFERENCES students(student_id),
  FOREIGN KEY(competency_id) REFERENCES competencies(competency_id)
)
```

## Legacy: Physische Workbook-/Export-Projektion

Die `data_*`-Quellen konnten in der Excel-Linie als versteckte Tabellenblaetter in Workbooks angelegt werden. Der zugehoerige Code liegt unter `legacy/excel/` und ist kein aktiver Standardpfad.

Jedes `data_*`-Blatt enthaelt genau eine strukturierte Tabelle mit `tbl_*`-Namen.

Der archivierte Builder erzeugte diese Tabellen automatisch.

Historische UI-Builder lasen ausschliesslich aus registrierten Tabellen und erzeugten daraus UI-Projektionen.

Eine Projektion darf mehrere registrierte Tabellen lesen, wenn die fachliche Herkunft in `docs/UI_DATA_MAPPING.md` dokumentiert und die View Ownership freigegeben ist.

Fuer Schuelerprojektionen sind mindestens `tbl_students`, `tbl_groups` und `tbl_courses` als lesende Quellen zulaessig.

Der Builder veraendert keine fachlichen Entitaeten und erzeugt keine doppelte Datenhaltung.

VBA nutzt IDs und benannte Bereiche, aber keine direkten Zugriffe auf fachliche Tabellen.

Worksheet-basierte Dialogseiten sind historische UI-Projektionen und temporaere Eingabeflaechen aus der Excel-Linie.

Sie sind keine fachlichen Datenquellen, erzeugen keine Schattenhaltung und duerfen fachliche Daten erst ueber freigegebene Schreibprozesse veraendern.

VBA darf keine fachlichen Daten in `data_*`-Tabellen schreiben.

VBA darf nur Projection Output importieren, der zuvor durch Python aus SQLite erzeugt wurde.

Registrierte Zuordnung:

| Hidden Sheet | Tabelle |
| --- | --- |
| `data_students` | `tbl_students` |
| `data_groups` | `tbl_groups` |
| `data_courses` | `tbl_courses` |
| `data_subjects` | `tbl_subjects` |
| `data_competencies` | `tbl_competencies` |
| `data_observations` | `tbl_observations` |
| `data_observation_competencies` | `tbl_observation_competencies` |
| `data_media` | `tbl_media` |
| `data_settings` | `tbl_settings` |

## Curriculum-Katalog v1

Zweck: Read-only-Katalog fuer Fachauswahl und Kompetenzauswahl im PySide6-Beobachtungsdialog.

Datei: `data/curriculum_catalog_v1.csv`

Status: v1-Kataloggrundlage, noch nicht final vollstaendig ausdifferenziert.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Wichtige Felder:

- `competency_id`
- `subject_key`
- `subject_display_name`
- `subject_full_name`
- `official_subject_name`
- `school_context_name`
- `grade_band`
- `learning_area`
- `competency_group`
- `competency_text`
- `source_reference`
- `is_core_subject`
- `is_active`

Regeln:

- Der Katalog wird nur lesend verwendet.
- `competency_id` ist eine stabile Katalog-ID im Format `CMP-######`.
- Er erzeugt selbst keine Beobachtung; der PySide-Adapter uebergibt die Katalog-IDs an `observation_competency_ratings`.
- `EPU` ist der App-Anzeigename fuer `Epochaler Projektunterricht`.
- Die offizielle Lehrplanquelle fuer `EPU` ist `Heimat- und Sachkunde`.
- `Sachunterricht` wird nicht als App-Fach gefuehrt.
- `Kunst` wird als App-Fach angezeigt; offizielle Quelle ist `Kunsterziehung`.
- `Ethik`, `Religion`, `Werken` und `Schulgarten` sind als erweiterte Faecher enthalten.

## data_students

Zweck: Stammdaten der Schueler.

Entity: Student.

Storage: `data_students` / `tbl_students`.

Projection: Schuelerkarten, Schuelerprofil, Auswahllisten, Berichtskopf.

Owner: Schuelerverwaltung.

Primary Key: `student_id`.

Foreign Keys:

- `group_id` -> `data_groups.group_id`
- `course_id` -> `data_courses.course_id`

Wichtige Felder:

- `student_id`
- `first_name`
- `last_name`
- `group_id`
- `course_id`
- `student_notes`
- `active`
- `created_at`
- `updated_at`
- `archived_at`

Pflichtfelder:

- `first_name`
- `last_name`
- `group_id`
- `course_id`

Optionale Felder:

- `student_notes`
- `archived_at`

Beziehungen:

- viele Schueler gehoeren zu einer Stammgruppe
- viele Schueler gehoeren zu einem Kurs
- ein Schueler kann viele Beobachtungen besitzen

Schreibende Prozesse:

- Schueler anlegen
- Schueler bearbeiten
- Schueler archivieren
- Python-Datenimport

Lesende Prozesse:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Beobachtungsdialog
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Schuelerkarten in Stammgruppenuebersicht
- Schuelerkarten in Kursuebersicht
- Kopfbereich im Schuelerprofil
- Schuelerauswahl im Beobachtungsdialog
- Berichtskopf

Erweiterungsregeln:

- keine fachlichen Schuelerdaten in UI-Projektionen speichern
- `display_name` ist eine UI-Projektion, kein gespeichertes Feld
- Archivierung setzt `active = FALSE` und `archived_at`
- keine physische Loeschung ohne eigenen Architekturentscheid
- produktiver App-Start erzeugt keine Demo-Schueler; explizite Seed-Daten dienen Tests, Legacy-Projektionen oder Demo-Szenarien

## data_groups

Zweck: Stammgruppen als organisatorische Zugehoerigkeit.

Entity: Group.

Storage: `data_groups` / `tbl_groups`.

Projection: Stammgruppenueberschrift, Stammgruppenanzeige, Gruppenauswahl.

Owner: Stammgruppenverwaltung.

Primary Key: `group_id`.

Foreign Keys:

- keine

Wichtige Felder:

- `group_id`
- `group_name`
- `sort_order`
- `active`

Beziehungen:

- eine Stammgruppe besitzt viele Schueler
- eine Stammgruppe kann in mehreren Kursverbuenden enthalten sein

Schreibende Prozesse:

- Stammgruppe anlegen
- Stammgruppe bearbeiten
- Stammgruppe archivieren
- Python-Datenimport

Lesende Prozesse:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Erlaubte UI-Projektionen:

- Ueberschrift der Stammgruppenuebersicht
- Stammgruppenanzeige in der Kursuebersicht
- Stammgruppenanzeige im Schuelerprofil

Erweiterungsregeln:

- neue Stammgruppen entstehen ueber Stammgruppenverwaltung
- keine automatische Stammgruppenanlage beim Anlegen eines Schuelers
- Archivierung statt physischer Loeschung

## data_courses

Zweck: Kurse als Jahrgangszuordnung.

Entity: Course.

Storage: `data_courses` / `tbl_courses`.

Projection: Kursanzeige, Kursuebersicht, Kartenfarbe.

Owner: Kursverwaltung.

Primary Key: `course_id`.

Foreign Keys:

- keine

Wichtige Felder:

- `course_id`
- `course_name`
- `color_key`
- `color_name`
- `color_hex`
- `sort_order`
- `active`

Beziehungen:

- ein Kurs besitzt viele Schueler
- ein Kurs kann in mehreren Kursverbuenden enthalten sein

Schreibende Prozesse:

- Kurs anlegen
- Kurs bearbeiten
- Kurs archivieren
- Python-Datenimport

Lesende Prozesse:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Erlaubte UI-Projektionen:

- Kursanzeige auf Schuelerkarten der Stammgruppenuebersicht
- Kartenfarbe aus Kurszuordnung
- Kursuebersicht
- Kursanzeige im Schuelerprofil

Erweiterungsregeln:

- Farben sind fachliche UI-Metadaten des Kurses
- Kartenfarben duerfen nicht manuell pro Schueler vergeben werden
- Archivierung statt physischer Loeschung

## course_groups

Zweck: Fachlicher Scope fuer kursverbundbezogene Mathe-/Deutsch-Kurse.

Entity: CourseGroup.

Storage: SQLite `course_groups`.

Projection: PySide-Uebersicht `Stammgruppen und Schülerbestand`, Stammdaten-Seite.

Owner: Stammdatenverwaltung.

Primary Key: `course_group_id`.

Foreign Keys:

- keine direkt in `course_groups`

Wichtige Felder:

- `course_group_id`
- `name`
- `sort_order`
- `active`

Beziehungen:

- ein Kursverbund enthaelt viele Stammgruppen ueber `course_group_student_groups`
- ein Kursverbund enthaelt viele Kurse ueber `course_group_courses`

Schreibende Prozesse:

- Kursverbund bearbeiten
- Stammdaten-Defaults initialisieren

Lesende Prozesse:

- PySide-Uebersicht `Stammgruppen und Schülerbestand`
- Stammdaten-Seite
- Schuelerliste mit Kursverbund-/Kursfilter

Erweiterungsregeln:

- Kursverbund definiert einen Filter-Scope, keine Schueler-Umbuchung
- Name, Stammgruppen- und Kurszuordnung werden atomar gespeichert
- Loeschen bleibt einem spaeteren Sprint vorbehalten

## course_group_student_groups

Zweck: Relation zwischen Kursverbund und Stammgruppen.

Entity: CourseGroupStudentGroup.

Storage: SQLite `course_group_student_groups`.

Owner: Stammdatenverwaltung.

Primary Key:

- `course_group_id`
- `student_group_id`

Foreign Keys:

- `course_group_id` -> `course_groups.course_group_id`
- `student_group_id` -> `groups.group_id`

Regel: Diese Relation filtert, welche Stammgruppen in einem Kursverbund ausgewertet werden. Sie erzeugt keine neue Stammgruppe und bucht keine Schueler um.

## course_group_courses

Zweck: Relation zwischen Kursverbund und Kursen.

Entity: CourseGroupCourse.

Storage: SQLite `course_group_courses`.

Owner: Stammdatenverwaltung.

Primary Key:

- `course_group_id`
- `course_id`

Foreign Keys:

- `course_group_id` -> `course_groups.course_group_id`
- `course_id` -> `courses.course_id`

Regel: Diese Relation filtert, welche Kurse innerhalb eines Kursverbunds angezeigt werden. Kursfarben bleiben Metadaten des Kurses.

## data_subjects

Zweck: Faecher oder Lernbereiche als fachliche Struktur.

Entity: Subject.

Storage: `data_subjects` / `tbl_subjects`.

Projection: Fachauswahl, Fachnavigation, Kompetenzstruktur.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Primary Key: `subject_id`.

Foreign Keys:

- keine

Wichtige Felder:

- `subject_id`
- `name`
- `sort_order`
- `status`

Beziehungen:

- ein Fach besitzt viele Kompetenzen

Schreibende Prozesse:

- Fach anlegen
- Fach bearbeiten
- Fach archivieren
- Python-Datenimport

Lesende Prozesse:

- Kompetenzansichten
- Beobachtungsdialog
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Fachauswahl
- Kompetenznavigation
- Kompetenzkarten

Erweiterungsregeln:

- Fachstruktur nur ueber fachlich freigegebene Konfiguration aendern
- Sortierung ueber `sort_order`, nicht ueber sichtbare Reihenfolge

## data_competencies

Zweck: Kompetenzen und Kompetenzstruktur.

Entity: Competency.

Storage: SQLite `competencies`, Export-/Legacy-Projektion `data_competencies` / `tbl_competencies`.

Projection: Kompetenzkarten, Kompetenzansicht, Kompetenzauswahl, Kompetenzchips.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Primary Key: `competency_id`.

Foreign Keys:

- `subject_id` -> `data_subjects.subject_id` spaeter; aktuell mit `subject_name` aus dem Katalog denormalisiert
- `parent_competency_id` -> `data_competencies.competency_id`

Wichtige Felder:

- `competency_id`
- `subject_id`
- `subject_name`
- `label`
- `description`
- `learning_area`
- `competency_group`
- `parent_competency_id`
- `sort_order`
- `active`
- `is_core_subject`

Beziehungen:

- eine Kompetenz gehoert zu einem Fach
- eine Kompetenz kann eine uebergeordnete Kompetenz besitzen
- eine Kompetenz kann vielen Beobachtungen zugeordnet werden

Schreibende Prozesse:

- Kompetenz ergaenzen
- Kompetenz bearbeiten
- Kompetenz archivieren
- Python-Datenimport

Lesende Prozesse:

- Beobachtungsdialog
- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Kompetenzkarten
- Kompetenzauswahl im Beobachtungsdialog
- Kompetenzverlauf
- Kompetenzchips an Beobachtungen

Erweiterungsregeln:

- Kompetenzstruktur wird aus dem freigegebenen Katalog geseedet und spaeter fachlich weiterentwickelt
- neue Kompetenzfelder duerfen keine Beobachtungsdaten duplizieren
- Bewertungen werden nicht als reine Farbwerte gespeichert

## data_observations

Zweck: Beobachtungen als fachliche Quelle der Lernentwicklung.

Entity: Observation.

Storage: SQLite `observations`, Export-/Legacy-Projektion `data_observations` / `tbl_observations`.

Projection: Beobachtungsverlauf, Kompetenzverlauf, Berichtsdaten, Dashboard-Auswertung.

Owner: Beobachtungserfassung.

Primary Key: `observation_id`.

Foreign Keys:

- `student_id` -> `data_students.student_id`

Wichtige Felder:

- `observation_id`
- `student_id`
- `date`
- `subject_id`
- `context`
- `note`
- `created_at`
- `updated_at`
- `active`

Beziehungen:

- eine Beobachtung gehoert zu einem Schueler
- eine Beobachtung kann vielen Kompetenzen zugeordnet werden
- eine Beobachtung kann Medien besitzen

Schreibende Prozesse:

- Beobachtung erfassen
- Beobachtung bearbeiten
- Beobachtung archivieren

Lesende Prozesse:

- Schuelerprofil
- Kompetenzansicht
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Beobachtungsverlauf im Schuelerprofil
- Kompetenzverlauf
- Berichtsdaten
- Dashboard-Auswertungen

Erweiterungsregeln:

- Beobachtungen bleiben Source of Truth fuer Lernentwicklung
- keine Auswertung darf Beobachtungsinhalte kopieren
- Archivierung statt physischer Loeschung

## data_observation_competencies

Zweck: Zuordnung von Beobachtungen zu Kompetenzen.

Entity: ObservationCompetency.

Storage: SQLite `observation_competency_ratings`, Export-/Legacy-Projektion `data_observation_competencies` / `tbl_observation_competencies`.

Projection: Kompetenzchips, Kompetenzverlauf, Bewertungsuebersicht.

Owner: Beobachtungserfassung.

Primary Key: zusammengesetzt aus `observation_id` und `competency_id`.

Foreign Keys:

- `observation_id` -> `data_observations.observation_id`
- `competency_id` -> SQLite `competencies.competency_id`

Wichtige Felder:

- `observation_id`
- `competency_id`
- `subject_id`
- `subject_display_name`
- `learning_area`
- `competency_group`
- `competency_text`
- `rating`

Beziehungen:

- eine Beobachtung kann vielen Kompetenzen zugeordnet werden
- eine Kompetenz kann in vielen Beobachtungen vorkommen

Schreibende Prozesse:

- Beobachtung erfassen
- Kompetenzzuordnung bearbeiten
- Beobachtung archivieren

Lesende Prozesse:

- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Kompetenzchips an Beobachtungen
- Kompetenzverlauf
- Bewertungsuebersicht

Erweiterungsregeln:

- keine Kompetenzzuordnung ohne gueltige Beobachtung
- keine Kompetenzzuordnung ohne gueltige Kompetenz
- Bewertungswerte muessen aus der fachlich freigegebenen Skala stammen

## data_media

Zweck: Dokumente, Medien oder Anlagen zu Schuelern und Beobachtungen.

Entity: Media.

Storage: SQLite `documents`, optionale Export-/Legacy-Projektion `data_media` / `tbl_media`.

Projection: Dokumentliste, Medienhinweise, Anlagenliste, Beobachtungsdetails.

Owner: Dokumentenverwaltung / Medienanhang / Beobachtungserfassung.

Primary Key: `document_id`.

Foreign Keys:

- `student_id` -> SQLite `students.student_id`
- `observation_id` -> SQLite `observations.observation_id` optional fuer Beobachtungsanhaenge

Wichtige Felder:

- `document_id`
- `student_id`
- `observation_id`
- `title`
- `document_type`
- `file_path`
- `original_filename`
- `created_at`
- `note`
- `active`

Beziehungen:

- ein Dokument oder Medium gehoert immer zu einem Schueler
- ein Beobachtungsanhang kann zusaetzlich einer Beobachtung zugeordnet sein
- eine Beobachtung kann viele Anhaenge besitzen

Schreibende Prozesse:

- Schuelerdokument hinzufuegen
- Beobachtungsanhang hinzufuegen
- Dokument oder Medium bearbeiten
- Dokument oder Medium archivieren

Lesende Prozesse:

- Schuelerverwaltung
- Schuelerprofil
- Beobachtungsdetails
- Berichte

Erlaubte UI-Projektionen:

- Dokumentbereich in Schueler-UserForms
- Medienhinweise an Beobachtungen
- Anlagenliste

Erweiterungsregeln:

- Medien speichern keine Beobachtungsdaten doppelt
- SQLite speichert nur Metadaten, keine Datei-BLOBs
- Dateien werden nicht in Excel eingebettet
- Excel speichert hoechstens Referenzen und Metadaten
- physische Dateiablage erfolgt studentenzentriert im Dateisystem unter `data/documents/<student_id>/`
- Beobachtungsanhaenge liegen unter dem Schueler und tragen zusaetzlich den Beobachtungsbezug
- `document_type` nutzt die freigegebene MVP-Auswahl: Arbeitsprobe, Lernzielkontrolle, Gespraechsnotiz, Bericht, Foto, Audio, Sonstiges

Vorgesehene physische Dateiablage:

```text
data/
|-- kompetenzmanager.sqlite
`-- documents/
    |-- STU-000001/
    |   |-- MED-000001_Foerderplan.pdf
    |   `-- MED-000002_Arbeitsprobe.txt
    |-- STU-000002/
    `-- ...
```

## data_settings

Zweck: Workbook- und Anwendungseinstellungen.

Entity: Setting.

Storage: `data_settings` / `tbl_settings`.

Projection: Build-Kontext, Anzeigeeinstellungen, App-Bar-Kontext.

Owner: Systemeinstellungen.

Primary Key: `setting_key`.

Foreign Keys:

- keine

Wichtige Felder:

- `setting_key`
- `setting_value`
- `value_type`
- `description`

Beziehungen:

- keine fachlichen Beziehungen

Schreibende Prozesse:

- Python-Build
- Einstellungsverwaltung nach Freigabe

Lesende Prozesse:

- Python-Builder
- UI-Projektionen
- VBA nur fuer technische Interaktion bei Bedarf

Erlaubte UI-Projektionen:

- Schuljahr
- sichtbare Stammdaten im App-Bar-Kontext
- optionale Anzeigeeinstellungen

Erweiterungsregeln:

- Settings duerfen keine fachlichen Daten ersetzen
- fachliche Konfiguration gehoert in die passende Datenquelle, nicht pauschal in Settings
