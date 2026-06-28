# Workbook Data Registry

Dieses Dokument definiert die verbindlichen Workbook-Datenquellen ab Sprint 4.

UI-Ansichten sind Projektionen dieser Datenquellen. Sie duerfen selbst keine fachliche Datenquelle werden.

## Schreib- und Leseprinzip

Python schreibt und aktualisiert Workbook-Datenquellen.

Python-Builder lesen Workbook-Datenquellen und erzeugen daraus UI-Projektionen.

VBA liest technische IDs aus UI-Projektionen fuer Navigation und Interaktion.

VBA greift niemals direkt auf fachliche Tabellen zu.

VBA schreibt keine fachlichen Daten, solange kein eigener fachlich freigegebener Schreibprozess dokumentiert ist.

Jede Datenquelle braucht einen registrierten Primary Key.

Alle Foreign Keys muessen in diesem Dokument explizit dokumentiert sein.

## Physische Workbook-Datenbank

Die `data_*`-Quellen werden spaeter als versteckte Tabellenblaetter im Workbook angelegt.

Jedes `data_*`-Blatt enthaelt genau eine strukturierte Tabelle mit `tbl_*`-Namen.

Der Builder erzeugt diese Tabellen automatisch.

UI-Builder lesen ausschliesslich aus diesen Tabellen und erzeugen daraus UI-Projektionen.

VBA nutzt IDs und benannte Bereiche, aber keine direkten Zugriffe auf fachliche Tabellen.

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
- `active`
- `created_at`
- `updated_at`

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
- Archivierungsfelder werden erst mit dem freigegebenen Archivierungsprozess ergänzt
- keine physische Loeschung ohne eigenen Architekturentscheid

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
- `active`

Beziehungen:

- eine Stammgruppe besitzt viele Schueler

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
- `active`

Beziehungen:

- ein Kurs besitzt viele Schueler

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

Storage: `data_competencies` / `tbl_competencies`.

Projection: Kompetenzkarten, Kompetenzansicht, Kompetenzauswahl, Kompetenzchips.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Primary Key: `competency_id`.

Foreign Keys:

- `subject_id` -> `data_subjects.subject_id`
- `parent_competency_id` -> `data_competencies.competency_id`

Wichtige Felder:

- `competency_id`
- `subject_id`
- `name`
- `description`
- `level`
- `parent_competency_id`
- `sort_order`
- `status`

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

- Kompetenzstruktur bleibt hierarchisch
- neue Kompetenzfelder duerfen keine Beobachtungsdaten duplizieren
- Bewertungen werden nicht als reine Farbwerte gespeichert

## data_observations

Zweck: Beobachtungen als fachliche Quelle der Lernentwicklung.

Entity: Observation.

Storage: `data_observations` / `tbl_observations`.

Projection: Beobachtungsverlauf, Kompetenzverlauf, Berichtsdaten, Dashboard-Auswertung.

Owner: Beobachtungserfassung.

Primary Key: `observation_id`.

Foreign Keys:

- `student_id` -> `data_students.student_id`

Wichtige Felder:

- `observation_id`
- `student_id`
- `date`
- `context`
- `note`
- `created_at`
- `updated_at`
- `status`

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

Storage: `data_observation_competencies` / `tbl_observation_competencies`.

Projection: Kompetenzchips, Kompetenzverlauf, Bewertungsuebersicht.

Owner: Beobachtungserfassung.

Primary Key: zusammengesetzt aus `observation_id` und `competency_id`.

Foreign Keys:

- `observation_id` -> `data_observations.observation_id`
- `competency_id` -> `data_competencies.competency_id`

Wichtige Felder:

- `observation_id`
- `competency_id`
- `rating`
- `note`

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

Zweck: Medien oder Anlagen zu Beobachtungen.

Entity: Media.

Storage: `data_media` / `tbl_media`.

Projection: Medienhinweise, Anlagenliste, Beobachtungsdetails.

Owner: Medienanhang / Beobachtungserfassung.

Primary Key: `media_id`.

Foreign Keys:

- `observation_id` -> `data_observations.observation_id`

Wichtige Felder:

- `media_id`
- `observation_id`
- `file_ref`
- `media_type`
- `caption`
- `status`

Beziehungen:

- ein Medium gehoert zu einer Beobachtung

Schreibende Prozesse:

- Medium hinzufuegen
- Medium bearbeiten
- Medium archivieren

Lesende Prozesse:

- Schuelerprofil
- Beobachtungsdetails
- Berichte

Erlaubte UI-Projektionen:

- Medienhinweise an Beobachtungen
- Anlagenliste

Erweiterungsregeln:

- Medien speichern keine Beobachtungsdaten doppelt
- Medien referenzieren immer eine Beobachtung
- physische Dateiablage wird separat entschieden

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
