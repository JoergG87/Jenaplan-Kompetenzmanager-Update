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
| `documentation_subject_settings` | DocumentationSubjectSetting | keine Workbook-Projektion |
| `timetable_entries` | TimetableEntry | keine Workbook-Projektion |
| `learning_conference_drafts` | LearningConferenceDraft | keine Workbook-Projektion |
| `learning_conference_draft_subjects` | LearningConferenceDraftSubject | keine Workbook-Projektion |
| `learning_conference_draft_cross_topics` | LearningConferenceDraftCrossTopic | keine Workbook-Projektion |
| `learning_conference_draft_competencies` | LearningConferenceDraftCompetency | keine Workbook-Projektion |
| `learning_conference_draft_observations` | LearningConferenceDraftObservation | keine Workbook-Projektion |
| `learning_conference_draft_charts` | LearningConferenceDraftChart | keine Workbook-Projektion |
| `learning_reports` | LearningReport | keine Workbook-Projektion |
| `learning_report_revisions` | LearningReportRevision | keine Workbook-Projektion |
| `learning_report_pdf_artifacts` | LearningReportPdfArtifact | keine Workbook-Projektion |
| `learning_conferences` | LearningConference | keine Workbook-Projektion |
| `learning_conference_revisions` | LearningConferenceRevision | keine Workbook-Projektion |
| `learning_conference_pdf_artifacts` | LearningConferencePdfArtifact | keine Workbook-Projektion |

Regel:

SQLite ist die fachliche Source of Truth. Es darf keine parallele fachliche Source of Truth neben SQLite geben. `data_*`-Sheets und `tbl_*`-Tabellen sind Excel-/Workbook-Projektionen aus SQLite oder historische Legacy-Artefakte.

Produktive PySide-Datenbanken initialisieren `students` leer. Stammdaten-Defaults fuer `groups`, `courses` und Kursverbuende duerfen angelegt werden, Demo-Schueler jedoch nur ueber explizite Seed-/Testpfade.

VBA schreibt nicht direkt in SQLite.

Python bleibt fachliche Schreibschicht.

PySide-Dialoge verwenden fuer produktive Schreibprozesse freigegebene Adapter, Commands, Services und Repositories.

Beobachtungen werden nicht hart geloescht. `observations.active = 0` blendet eine Beobachtung aus aktiven Profil- und Kompetenzuebersichten aus; die zugehoerigen `observation_competency_ratings` bleiben historisch erhalten.

Der Kompetenzkatalog wird aus `data/curriculum_catalog_v1.csv` idempotent in SQLite `competencies` importiert. `grade_band` bleibt Quellenkontext, `learning_stage` speichert die produktbezogene Filterstufe, `catalog_status` speichert den Katalogstatus, `catalog_default_active` speichert den Katalogstandard und `activation_group_key` bereitet optional aktivierbare Bereiche vor. `competencies.active` bleibt die lokale Aktivierung und darf bei bestehenden `competency_id`s durch den Katalogimport nicht ueberschrieben werden.

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
  subject_full_name TEXT NOT NULL DEFAULT '',
  official_subject_name TEXT NOT NULL DEFAULT '',
  school_context_name TEXT NOT NULL DEFAULT '',
  grade_band TEXT NOT NULL DEFAULT '',
  label TEXT NOT NULL,
  description TEXT NOT NULL,
  learning_stage TEXT NOT NULL DEFAULT 'cross_stage',
  learning_area TEXT NOT NULL,
  competency_group TEXT,
  source_reference TEXT NOT NULL DEFAULT '',
  catalog_status TEXT NOT NULL DEFAULT 'current',
  activation_group_key TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL,
  catalog_default_active INTEGER NOT NULL DEFAULT 1,
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

documentation_subject_settings(
  subject_id TEXT PRIMARY KEY,
  active INTEGER NOT NULL CHECK (active IN (0, 1)),
  updated_at TEXT NOT NULL
)

timetable_entries(
  timetable_entry_id TEXT PRIMARY KEY,
  weekday INTEGER NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  room TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT NOT NULL DEFAULT ''
)
```

## Sprint-3A-Mapping Kompetenzstruktur

Sprint 3A klaert die fachliche Sprache, ohne neue Datenquelle, neue Spalte oder Schema-Migration einzufuehren.

Sichtbare Struktur:

```text
Fach -> Kompetenzbereich -> Thema -> Kompetenz
```

Mapping auf bestehende Datenfelder:

| Sichtbarer Begriff | SQLite / Katalogfeld | Bemerkung |
| --- | --- | --- |
| Fach | `subject_id`, `subject_name`, Katalog `subject_key`, `subject_display_name` | Fachschluessel und sichtbarer Fachname |
| Kompetenzbereich | `learning_area` | bisher teilweise als Lernbereich bezeichnet; ab Sprint 3 fachlich als Kompetenzbereich zu verstehen |
| Thema | `competency_group` | fachliche Untergliederung innerhalb eines Kompetenzbereichs |
| Kompetenz | `competencies.description`, `observation_competency_ratings.competency_text`, Katalog `competency_text` | konkrete beobachtbare Kompetenz |
| Kurzlabel fuer kompakte UI | `competencies.label`, Katalog `competency_label` | kurze Anzeige, keine eigene fachliche Ebene; Sprint 3B fuehrt `competency_label` als optionale CSV-Spalte ein |

Bewertungen:

- `observations` enthaelt keine globale Bewertung.
- `observation_competency_ratings.rating` speichert die Bewertung fuer genau eine Kombination aus `observation_id` und `competency_id`.
- Eine Beobachtung kann mehrere Kompetenzbewertungen enthalten.
- Unterschiedliche Kompetenzen innerhalb derselben Beobachtung duerfen unterschiedliche Bewertungen tragen.
- `offen` ist kein gespeicherter Ratingwert. Wenn eine Kompetenz nicht bewertet werden soll, wird keine Zeile in `observation_competency_ratings` gespeichert.

Bestandsdaten:

- Alte grobe Kompetenzen bleiben ueber ihre `competency_id` historisch lesbar.
- Bestehende `observation_competency_ratings` bleiben gueltig.
- Alte Beobachtungen werden nicht automatisch auf spaetere konkrete Kompetenzen migriert.
- Neue konkrete Kompetenzen werden spaeter fuer neue Beobachtungen ergaenzt.
- Alte grobe Kompetenzen duerfen spaeter deaktiviert oder archiviert werden, aber nicht geloescht werden.
- Sprint 3 braucht fuer Bewertung pro Kompetenz keine Rating-Schema-Migration.

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

Die fachbezogene Schnellauswahl `Zuletzt verwendet` ist keine eigene Datenquelle: Sie ist eine fluechtige `StudentDesktopAdapter`-Projektion aus aktiven SQLite-`observations` mit deren `observation_competency_ratings`, auf vorhandene aktive `current`-Zeilen aus `competencies` begrenzt. Sie speichert weder Historie noch Auswahlzustand.

Datei: `data/curriculum_catalog_v1.csv`

Status: v1-Kataloggrundlage mit abgeschlossenem Sprint-4-Lehrplanabgleich fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz. Die konkreten Kompetenzen folgen den freigegebenen Lehrplan-Mappings, der Katalog-Konsolidierung und den Product-Owner-Entscheidungen. Religion bleibt ausserhalb dieses Sprint-4-Katalogabgleichs.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Wichtige Felder:

- `competency_id`
- `subject_key`
- `subject_display_name`
- `subject_full_name`
- `official_subject_name`
- `school_context_name`
- `grade_band`
- `learning_stage`
- `learning_area`
- `competency_group`
- `competency_text`
- `competency_label`
- `source_reference`
- `catalog_status`
- `catalog_default_active`
- `activation_group_key`
- `is_core_subject`
- `is_active`

Regeln:

- Der Katalog wird nur lesend verwendet.
- `competency_id` ist eine stabile Katalog-ID im Format `CMP-######`.
- Neue konkrete Kompetenzen werden mit neuen global fortlaufenden IDs ergaenzt; bestehende IDs werden nicht fachlich umgedeutet oder wiederverwendet.
- `competency_label` befuellt beim Import das bestehende SQLite-Feld `competencies.label`; es ist keine neue SQLite-Spalte.
- Der SQLite-Katalogimport ist idempotent: neue CSV-IDs werden in bestehende lokale Datenbanken eingefuegt, vorhandene lokale Nicht-CSV-Kompetenzen bleiben erhalten und `competencies.active` vorhandener IDs wird nicht ungefragt aus dem CSV ueberschrieben.
- Vor fachlichen CSV-Aenderungen pruefen die internen Werkzeuge `scripts/validate_curriculum_catalog.py`, `scripts/compare_curriculum_catalog.py` und `scripts/next_competency_ids.py` Header, Pflichtfelder, Wertebereiche, ID-Stabilitaet, stille Text-/Hierarchieveraenderungen und die naechsten freien globalen IDs.
- `catalog_status = current` ist Standard. `catalog_status = legacy` dient ausschliesslich historischen Kompetenzen und macht diese nicht automatisch zu neuen Dokumentationszielen.
- `catalog_default_active = false` bedeutet, dass neue optionale Kompetenzen beim Erstimport standardmaessig deaktiviert werden.
- Alte grobe Kompetenzen bleiben historisch lesbar. Sie duerfen spaeter deaktiviert oder archiviert, aber nicht geloescht werden.
- Bestehende `observation_competency_ratings` bleiben gueltig und werden nicht automatisch auf neue konkrete Kompetenzen migriert.
- Er erzeugt selbst keine Beobachtung; der PySide-Adapter uebergibt die Katalog-IDs an `observation_competency_ratings`.
- `EPU` ist der App-Anzeigename fuer `Epochaler Projektunterricht`.
- Die offizielle Lehrplanquelle fuer `EPU` ist `Heimat- und Sachkunde`.
- `Sachunterricht` wird nicht als App-Fach gefuehrt.
- `Kunst` wird als App-Fach angezeigt; offizielle Quelle ist `Kunsterziehung`.
- `Ethik`, `Religion`, `Werken` und `Schulgarten` sind als erweiterte Faecher enthalten.

## documentation_subject_settings

Zweck: Auswahl der Faecher, die fuer spaetere Dokumentations- und Auswertungslogik als dokumentationsrelevant gelten.

Entity: DocumentationSubjectSetting.

Storage: SQLite `documentation_subject_settings`.

Projection: PySide6 Einstellungen und Dokumentations-/Auswertungsprojektionen.

Owner: Systemeinstellungen / Dokumentationskonfiguration.

Primary Key: `subject_id`.

Foreign Keys:

- keine, weil `competencies.subject_id` im Kompetenzkatalog mehrfach vorkommt

Wichtige Felder:

- `subject_id`
- `active`
- `updated_at`

Beziehungen:

- `subject_id` verweist fachlich auf die Fachschluessel im aktiven Kompetenzkatalog, speichert aber keine Fachdefinition und keine sichtbaren Fachnamen.

Schreibende Prozesse:

- Dokumentationsrelevante Faecher speichern

Lesende Prozesse:

- Dokumentations- und Auswertungsprojektionen
- PySide6 Einstellungen

Regeln:

- Wenn keine Zeilen vorhanden sind, gelten alle aktiven Katalogfaecher aus `competencies.active = 1` als dokumentationsrelevant.
- Wenn Zeilen vorhanden sind, gilt die gespeicherte Auswahl.
- Die Tabelle veraendert den Kompetenzkatalog nicht.
- `competencies.active` darf nicht fuer diese Dokumentationsauswahl missbraucht werden.
- Sichtbare Fachnamen werden weiterhin aus `competencies` bzw. dem Katalog abgeleitet.
- Nicht dokumentationsrelevante Faecher bleiben in Beobachtungslisten, Kompetenzhistorien und bestaetigten Kompetenzstaenden sichtbar, zaehlen aber nicht als offen im Dokumentationsstand oder in offenen Beobachtungsanlaessen.

## timetable_entries

Zweck: Persistenter Wochenstundenplan fuer Montag bis Freitag.

Entity: TimetableEntry.

Storage: SQLite `timetable_entries`.

Projection: PySide6 Einstellungen sowie kanonische Leseprojektion fuer aktuelle, naechste und heutige Stunden.

Owner: Stundenplankonfiguration.

Primary Key: `timetable_entry_id` im Format `TTE-######`.

Fachliche Referenzen:

- `subject_id` muss als bestehender Fachschluessel in SQLite `competencies` vorkommen; ein sichtbarer Fachname wird nicht gespeichert.
- `target_type = group` referenziert mit `target_id` genau SQLite `groups.group_id`.
- `target_type = course` referenziert mit `target_id` genau SQLite `courses.course_id`.
- `target_type = course_group` referenziert mit `target_id` genau SQLite `course_groups.course_group_id`.

Wichtige Felder:

- `weekday` als ISO-Wochentag 1 bis 5
- `start_time` und `end_time` als `HH:MM`
- `room` als optionaler Anzeigeort
- `active` fuer bewusste Aktivierung oder Deaktivierung
- `sort_order` fuer stabile Reihenfolge bei sonst gleichen Anzeigeattributen
- `created_at` und `updated_at` als technische Zeitstempel
- `deleted_at` fuer kontrolliertes Entfernen ohne Wiederverwendung der ID

Regeln:

- Beginn liegt strikt vor Ende; ein Eintrag kann daher nicht ueber Mitternacht reichen.
- Aktive Eintraege duerfen sich zeitlich nicht ueberschneiden.
- Inaktive Eintraege werden weder als aktuell noch als naechste Stunde projiziert.
- Die Leseprojektion erhaelt einen expliziten Zeitpunkt und liest hoechstens bis zum folgenden Wochenumlauf.
- Das Ende ist exklusiv: bei `end_time` ist die Stunde nicht mehr aktuell.
- Es werden keine Fach-, Stammgruppen-, Kurs- oder Kursverbundnamen kopiert.
- Loeschen blendet den Eintrag ueber `deleted_at` aus; die technische ID wird nicht wiederverwendet.

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

Zweck: Faecher als fachliche Struktur. Kompetenzbereiche liegen im Kompetenzkatalog ueber `learning_area`.

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

Sprint-3A-Mapping:

- `subject_id` / `subject_name` = Fach
- `learning_area` = Kompetenzbereich
- `competency_group` = Thema
- `description` = konkrete Kompetenz
- `label` = Kurzlabel fuer kompakte UI

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

Sprint-3A-Mapping:

- `subject_id` / `subject_display_name` = Fach zum Zeitpunkt der Beobachtung
- `learning_area` = Kompetenzbereich zum Zeitpunkt der Beobachtung
- `competency_group` = Thema zum Zeitpunkt der Beobachtung
- `competency_text` = konkrete Kompetenz zum Zeitpunkt der Beobachtung
- `rating` = Bewertung dieser konkreten Kompetenz innerhalb dieser Beobachtung

Beziehungen:

- eine Beobachtung kann vielen Kompetenzen zugeordnet werden
- eine Kompetenz kann in vielen Beobachtungen vorkommen
- `rating` gehoert zur Zuordnung, nicht global zur Beobachtung

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

## report_drafts und Berichtsentwurf-Relationen

Zweck: Persistenter, weiter bearbeitbarer Arbeitsentwurf fuer Lernentwicklungsberichte.

Entity: ReportDraft. Keine finale Berichtsentitaet.

Storage:

- SQLite `report_drafts` fuer Identitaet, Schuelerbezug, Berichtstyp, Zeitraum, Status, Lehrkraft, Gesamtblick und Zeitstempel
- SQLite `report_draft_subjects` fuer bewusste Fachauswahl und vier manuelle Fachtexte
- SQLite `report_draft_competencies` fuer reine `competency_id`-Referenzen
- SQLite `report_draft_observations` fuer reine `observation_id`-Referenzen
- SQLite `report_draft_charts` fuer Diagrammtyp je ausgewaehltem Fach

Owner: Lernentwicklungsbericht / Berichtsvorbereitung.

Primary Key: `report_draft_id`.

Foreign Keys:

- `student_id` -> `students.student_id`
- `competency_id` -> `competencies.competency_id`
- `observation_id` -> `observations.observation_id`
- alle Relationstabellen -> `report_drafts.report_draft_id` mit `ON DELETE CASCADE`

Wichtige Regeln:

- `status` ist in Sprint 7F.1 ausschliesslich `draft`.
- Kompetenztexte, Hierarchie, Bewertungen, Vorschlaege und Bestaetigungen werden nicht kopiert.
- Beobachtungsdatum, Kontext und Notiz werden nicht kopiert.
- Fachtexte stammen ausschliesslich aus manueller Eingabe durch Laura.
- Eine Zeile in `report_draft_subjects` repraesentiert ein bewusst ausgewaehltes Fach, auch wenn alle vier Texte noch leer sind.
- Der Berichtsentwurf liest Kompetenzstatus weiterhin ausschliesslich aus der kanonischen Sprint-6-Projektion.
- Neue Kompetenzreferenzen muessen aktiv und `current` sein sowie zu einem ausgewaehlten Fach gehoeren. Bereits gespeicherte, spaeter deaktivierte oder historische Kompetenz-IDs bleiben als nicht mehr regulaer verfuegbare Auswahl erhalten und werden nicht erneut zur Auswahl angeboten.
- Neue Beobachtungsreferenzen muessen aktiv sein, zum Kind gehoeren und mindestens einem ausgewaehlten Fach ueber Beobachtungsfach oder Kompetenzbewertung zugeordnet sein. Bereits gespeicherte, spaeter soft-geloeschte `OBS`-IDs bleiben als nicht verfuegbare Referenzen erhalten; Beobachtungsinhalte werden nicht rekonstruiert.
- Der Entwurf ist nicht freigegeben, versioniert, archiviert oder eingefroren.

Schreibende Prozesse:

- Berichtsentwurf anlegen
- Berichtsentwurf aktualisieren

Lesende Prozesse:

- Berichtsentwurf laden
- Berichtsentwuerfe eines Schuelers auflisten
- spaetere Sprint-7F.2-Berichtswerkstatt

## learning_reports und learning_report_revisions

Zweck: Stabile Lernentwicklungsbericht-Aggregate und unveraenderliche fachliche Revisionen aus einer bewussten Finalisierung eines weiterhin bearbeitbaren Berichtsentwurfs.

Entities: LearningReport und LearningReportRevision. Keine PDF-Artefakte und keine LEG-Entitaeten.

Storage:

```text
learning_reports(
  learning_report_id TEXT PRIMARY KEY,
  source_report_draft_id TEXT NOT NULL UNIQUE,
  student_id TEXT NOT NULL,
  report_type TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_report_draft_id) REFERENCES report_drafts(report_draft_id),
  FOREIGN KEY(student_id) REFERENCES students(student_id)
)

learning_report_revisions(
  learning_report_revision_id TEXT PRIMARY KEY,
  learning_report_id TEXT NOT NULL,
  revision_number INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('finalized', 'superseded')),
  snapshot_schema_version INTEGER NOT NULL,
  snapshot_json TEXT NOT NULL,
  snapshot_sha256 TEXT NOT NULL,
  finalized_at TEXT NOT NULL,
  finalized_by_display_name TEXT NOT NULL,
  superseded_at TEXT,
  UNIQUE(learning_report_id, revision_number),
  FOREIGN KEY(learning_report_id) REFERENCES learning_reports(learning_report_id)
)
```

Owner: Lernentwicklungsbericht / Finalisierung und Revisionshistorie.

Primary Keys:

- `learning_reports.learning_report_id` im Format `RPT-######`
- `learning_report_revisions.learning_report_revision_id` im Format `RPV-######`

Foreign Keys:

- `source_report_draft_id` -> `report_drafts.report_draft_id`
- `student_id` -> `students.student_id`
- `learning_report_id` -> `learning_reports.learning_report_id`

Wichtige Regeln:

- Pro `source_report_draft_id` existiert hoechstens ein stabiles `RPT`-Aggregat.
- Nach der Erstfinalisierung sind `source_report_draft_id`, `student_id`, `report_type`, `period_start` und `period_end` unveraenderliche Aggregateidentitaet. `learning_reports` besitzt keinen Update- oder Delete-Pfad. Weicht ein spaeter bearbeiteter `RPD` in Berichtstyp oder Zeitraum ab, wird die Folgerevision abgelehnt; der abweichende Bericht braucht einen neuen Draft und ein neues Aggregat.
- Revisionsnummern sind innerhalb eines `RPT` eindeutig, beginnen bei 1 und steigen ohne Luecke im normalen Finalisierungspfad.
- Pro `RPT` besitzt hoechstens eine Revision den Status `finalized`.
- Revisionszeilen werden weder geloescht noch fachlich aktualisiert. Nur beim Erzeugen einer Folgerevision darf die bisherige aktuelle Revision in derselben Transaktion von `finalized` auf `superseded` wechseln; dabei wird ausschliesslich `superseded_at` zusaetzlich gesetzt.
- Der fachliche Snapshot ist die historische Source of Truth. Er enthaelt Quell-`RPD`, eingefrorene sichtbare Schuelerdaten, Berichtskontext, verantwortlichen Anzeigenamen, manuelle Texte, Faecher, Kompetenzen mit Historienkennzeichnung, aktive ausgewaehlte Beobachtungsbelege, bewusst ausgewaehlte Diagrammdaten und Snapshot-Zeitpunkt.
- `snapshot_json` ist exakt die kanonische UTF-8-JSON-Darstellung. `snapshot_sha256` ist der SHA-256-Hexdigest genau dieser Bytes.
- `ReportOutputModel`, PDF-Dateien, Renderer-Versionen und Artefaktpfade sind keine Felder dieser Tabellen.
- Die bestehenden `report_drafts*`-Tabellen und ihr ausschliesslicher Status `draft` bleiben unveraendert.

Schreibender Prozess:

- Lernentwicklungsbericht-Draft finalisieren beziehungsweise als neue Revision erneut finalisieren

Lesende Prozesse:

- stabiles Berichtaggregat zum Quell-Draft lesen
- aktuelle oder historische Revisionen eines Berichtaggregats lesen

## learning_report_pdf_artifacts

Zweck: Unveraenderliche Dateireferenz fuer das genau aus einer verifizierten finalisierten Lernentwicklungsbericht-Revision erzeugte PDF.

Entity: LearningReportPdfArtifact. Kein fachlicher Berichtssnapshot, keine allgemeine Dokumententitaet und kein LEG-Artefakt.

Storage:

```text
learning_report_pdf_artifacts(
  learning_report_pdf_artifact_id TEXT PRIMARY KEY,
  learning_report_revision_id TEXT NOT NULL UNIQUE,
  relative_file_path TEXT NOT NULL UNIQUE,
  mime_type TEXT NOT NULL CHECK(mime_type = 'application/pdf'),
  file_size_bytes INTEGER NOT NULL CHECK(file_size_bytes > 0),
  snapshot_sha256 TEXT NOT NULL,
  pdf_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(learning_report_revision_id)
    REFERENCES learning_report_revisions(learning_report_revision_id)
)
```

Owner: Lernentwicklungsbericht / finaler PDF-Druck.

Primary Key:

- `learning_report_pdf_artifacts.learning_report_pdf_artifact_id` im Format `RPA-######`

Foreign Key:

- `learning_report_revision_id` -> `learning_report_revisions.learning_report_revision_id`

Wichtige Regeln:

- Pro `RPV` existiert hoechstens eine Artefaktreferenz. Die Zeile wird nach ihrer Erstellung weder aktualisiert noch geloescht.
- Ein neues Artefakt darf nur erzeugt werden, solange die Quellrevision den Status `finalized` besitzt und ihr kanonischer Snapshot sowie dessen interne Referenzen vollstaendig validiert sind.
- `relative_file_path` liegt relativ zum Verzeichnis der SQLite-Datei unter `documents/<student_id>/reports/<RPT>/<RPV>/`; der Dateiname enthaelt technische IDs und keinen Schuelerklarnamen.
- `snapshot_sha256` entspricht exakt dem bei der Erzeugung bestaetigten `learning_report_revisions.snapshot_sha256`.
- `pdf_sha256` ist der SHA-256-Hexdigest der gespeicherten PDF-Bytes; `file_size_bytes` ist deren exakte Bytegroesse.
- Der fachliche Snapshot bleibt Source of Truth. Das Artefakt ist ein abgeleitetes unveraenderliches Ausgabeobjekt und keine Quelle fuer neue Berichtsinhalte.
- Renderer-Versionierung, mehrere Artefakte pro Revision, Archivstatus, Retention und LEG-PDF sind nicht Teil dieser Tabelle.

Schreibender Prozess:

- finales PDF aus einer aktuellen `finalized`-Berichtrevision erzeugen

Lesende Prozesse:

- vorhandenes PDF-Artefakt fuer eine Revision laden und gegen Pfad, Groesse und Hash pruefen

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

## learning_conference_drafts und LEG-Entwurfsrelationen

Zweck: Persistenter, weiter bearbeitbarer Arbeitsentwurf fuer Vorbereitung und Durchfuehrung eines Lernentwicklungsgespraechs.

Entity: LearningConferenceDraft. Kein Bericht und keine finale Gespraechsversion.

Storage:

- `learning_conference_drafts` fuer Identitaet, Schuelerbezug, Zeitraum, Gespraechsdatum, Status, verantwortliche Lehrkraft, manuell verantwortete Vorbereitungs- und Gespraechsinhalte sowie Zeitstempel
- `learning_conference_draft_subjects` fuer bewusste `subject_id`-Auswahl
- `learning_conference_draft_cross_topics` fuer die vier freigegebenen uebergreifenden Themen
- `learning_conference_draft_competencies` fuer reine `competency_id`-Referenzen
- `learning_conference_draft_observations` fuer reine `observation_id`-Referenzen
- `learning_conference_draft_charts` fuer die drei freigegebenen neutralen Darstellungsarten

Owner: Lernentwicklungsgespraech.

Primary Key: `learning_conference_draft_id`.

Foreign Keys:

- `student_id` -> `students.student_id`
- `competency_id` -> `competencies.competency_id`
- `observation_id` -> `observations.observation_id`
- alle Relationstabellen -> `learning_conference_drafts.learning_conference_draft_id` mit `ON DELETE CASCADE`

Wichtige Regeln:

- `status` ist in Sprint 7G.1 ausschliesslich `draft`.
- Der Entwurf referenziert Live-Daten und friert weder Kompetenz- noch Beobachtungsinhalte ein.
- Kompetenztexte, Hierarchie, Bewertungen, Bestaetigungen und berechnete Kompetenzstaende werden nicht kopiert.
- Beobachtungsdatum, Kontext, Notiz und Kompetenzbewertungen werden nicht kopiert.
- Ausgewaehlte Beobachtungen muessen zum betroffenen Kind gehoeren. Neue Auswahl ist nur fuer aktive Beobachtungen erlaubt; bereits referenzierte, spaeter soft-geloeschte Beobachtungen bleiben als nicht verfuegbarer Beleg identifizierbar.
- Schnellbeobachtungen duerfen als `observation_id` referenziert werden und bleiben ohne Wirkung auf Kompetenzstatus und Diagrammberechnungen.
- Ziele, Unterstuetzung, Vereinbarungen, Zustaendigkeiten und weitere Gespraechstexte sind ausschliesslich manuelle Inhalte. Vorbereitete und gemeinsam vereinbarte Inhalte bleiben getrennt.
- Diagrammzeilen speichern nur den Typ, keine berechneten Darstellungsdaten.
- Keine Freigabe, Versionierung, Archivierung, Signatur oder finale Dokumentation.

Schreibende Prozesse:

- LEG-Arbeitsentwurf anlegen
- LEG-Arbeitsentwurf aktualisieren

Lesende Prozesse:

- LEG-Arbeitsentwurf laden
- LEG-Arbeitsentwuerfe eines Schuelers auflisten
- Sprint-7G.2-LEG-Arbeitsbereich

## learning_conferences und learning_conference_revisions

Zweck: Stabiles fachliches LEG-Aggregat und unveraenderliche, reproduzierbare Abschlussrevisionen.

Entities:

- `LearningConferenceRecord` (`LCF`) als stabile Identitaet eines explizit abgeschlossenen LCD
- `LearningConferenceRevisionRecord` (`LCV`) als unveraenderlicher Abschlussstand

Storage:

- `learning_conferences` fuer `learning_conference_id`, Quell-LCD, Schuelerbezug und Erzeugungszeitpunkt
- `learning_conference_revisions` fuer Revisionsnummer, Status, Snapshotvertrag, Snapshot-JSON, SHA-256 und Abschluss-/Ersetzungsmetadaten

Owner: LEG-Abschlussdomain. Keine Berichtsdomain.

Primary Keys:

- `learning_conferences.learning_conference_id`
- `learning_conference_revisions.learning_conference_revision_id`

Foreign Keys:

- `learning_conferences.source_learning_conference_draft_id` -> `learning_conference_drafts.learning_conference_draft_id`
- `learning_conferences.student_id` -> `students.student_id`
- `learning_conference_revisions.learning_conference_id` -> `learning_conferences.learning_conference_id`

Wichtige Regeln:

- Pro LCD existiert hoechstens ein LCF; der LCD bleibt `draft` und bearbeitbar.
- Pro LCF existiert hoechstens eine aktuelle LCV mit Status `completed`.
- LCV-Snapshots sind unveraenderlich und nicht loeschbar; nur der Statuswechsel `completed` nach `superseded` mit `superseded_at` ist erlaubt.
- Ein identischer kanonischer Snapshot erzeugt keine neue LCV.
- Der Snapshot ist die historische Source of Truth und enthaelt keine interne Lehrkraftvorbereitung oder private Notizen.
- Ausgewaehlte historische Kompetenzen muessen vollstaendig aufloesbar und gekennzeichnet sein; fehlende Pflichtbelege blockieren den Schreibprozess.
- Diagramme bleiben in Sprint 10A Draftreferenzen und sind nicht Bestandteil des Abschluss-Snapshotvertrags.

Schreibender Prozess:

- expliziter LEG-Abschluss beziehungsweise korrigierender Folgeabschluss

Lesende Prozesse:

- LEG-Abschlussstatus zu einem LCD
- LCV-Historie eines LCF
- verifizierte snapshotbasierte LCV-Lesesicht

## learning_conference_pdf_artifacts

Zweck: Unveraenderliche Referenz auf genau ein verwaltetes finales PDF einer abgeschlossenen LEG-Revision.

Entity:

- `LearningConferencePdfArtifactRecord` (`LCA`)

Storage:

```text
learning_conference_pdf_artifacts(
  learning_conference_pdf_artifact_id TEXT PRIMARY KEY,
  learning_conference_revision_id TEXT NOT NULL UNIQUE,
  relative_file_path TEXT NOT NULL UNIQUE,
  mime_type TEXT NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  snapshot_sha256 TEXT NOT NULL,
  pdf_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
)
```

Owner: LEG-PDF-Domain. Keine Berichtsdomain und keine Workbook-Projektion.

Primary Key:

- `learning_conference_pdf_artifacts.learning_conference_pdf_artifact_id` im Format `LCA-######`

Foreign Key:

- `learning_conference_pdf_artifacts.learning_conference_revision_id` -> `learning_conference_revisions.learning_conference_revision_id`

Wichtige Regeln:

- Pro LCV existiert hoechstens eine Artefaktzeile; sie darf weder aktualisiert noch geloescht werden.
- Ein neues Artefakt darf nur fuer eine LCV mit Status `completed` entstehen.
- `snapshot_sha256` entspricht exakt dem vor dem Rendern bestaetigten Hash der LCV.
- `pdf_sha256` und `file_size_bytes` beschreiben exakt die unveraenderten gespeicherten PDF-Bytes.
- `relative_file_path` liegt unter `documents/<student_id>/learning_conferences/<LCF>/<LCV>/` relativ zum Verzeichnis der SQLite-Datei.
- Wiederaufrufe lesen und verifizieren die bestehende Zeile und Datei; es entsteht kein zweites Artefakt.

Schreibender Prozess:

- finales LEG-PDF aus einer verifizierten aktuellen LCV erzeugen

Lesender Prozess:

- vorhandenes LEG-PDF-Artefakt nach Pfad, Dateigroesse und SHA-256 verifizieren
