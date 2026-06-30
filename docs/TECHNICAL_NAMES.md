# Technical Naming Registry

Dieses Dokument ist ab Sprint 4 die verbindliche Registry fuer technische Namen.

## Grundregeln

Technische Namen werden grundsaetzlich englisch und ASCII-kompatibel gefuehrt.

Technische Namen enthalten keine Umlaute, keine Leerzeichen und keine sichtbaren deutschen UI-Begriffe.

Sichtbare Blattnamen und UI-Texte duerfen deutsch sein. Technische Schluessel bleiben stabil und englisch oder bereits registrierte ASCII-Namen.

Sichtbare Begriffe duerfen sich aendern. Technische Namen bleiben stabil.

Keine neuen technischen Namen ohne Erweiterung dieser Registry.

Bestehende technische Namen werden nicht ohne eigenen Migrationssprint umbenannt.

Beispiele fuer stabile technische IDs:

- `student_id`
- `group_id`
- `course_id`
- `subject_id`
- `competency_id`
- `observation_id`
- `media_id`

Beispiele fuer technische Feldnamen:

- `file_ref`
- `media_category`

Beispiele fuer sichtbare Begriffe:

- Stammgruppe
- Kurs
- Schuelerprofil
- Kompetenz
- Lernentwicklungsbericht

## Workbook-CodeNames

| Objekt | Sichtbar | Technisch | Status |
| --- | --- | --- | --- |
| Workbook | Arbeitsmappe | `DieseArbeitsmappe` | bestehend |
| Stammgruppenuebersicht | `Stammgruppenübersicht` | `wsClassOverview` | bestehend, nicht umbenennen |
| Schuelerprofil | `Schülerprofil` | `wsStudentProfile` | bestehend |

Hinweis: `wsClassOverview` bleibt trotz sichtbarer Umbenennung auf `Stammgruppenübersicht` bestehen. Eine technische Umbenennung ist kein Bestandteil von Sprint 4.0.

## Legacy-Regeln

Bestehende technische Namen wie `wsClassOverview`, `ui_class_search`, `ui_class_search_input` und `ui_action_new_observation` werden vorerst nicht umbenannt.

Sie gelten als technische Altlasten und bleiben stabil, bis eine kontrollierte Migration in dieser Registry dokumentiert und freigegeben ist.

Keine spontane Umbenennung bestehender technischer Namen waehrend Feature-Sprints.

## Sichtbare Blattnamen

| Sichtbarer Blattname | Zweck |
| --- | --- |
| `Stammgruppenübersicht` | Einstieg in eine Stammgruppe |
| `Schülerprofil` | Profil eines Schuelers |
| `Kursübersicht` | zukuenftige Ansicht fuer einen Kurs |

## Hidden-Data-Sheets

Workbook-Datenquellen verwenden das Praefix `data_`.

Registrierte Hidden-Data-Sheets:

- `data_students`
- `data_groups`
- `data_courses`
- `data_subjects`
- `data_competencies`
- `data_observations`
- `data_observation_competencies`
- `data_media`
- `data_settings`

## Tabellen

Tabellennamen verwenden das Praefix `tbl_` und beziehen sich auf das jeweilige Hidden-Data-Sheet.

Registrierte Tabellennamen:

- `tbl_students`
- `tbl_groups`
- `tbl_courses`
- `tbl_subjects`
- `tbl_competencies`
- `tbl_observations`
- `tbl_observation_competencies`
- `tbl_media`
- `tbl_settings`

## ID-Felder

Verbindliche ID-Felder fuer neue Architekturarbeit:

- `student_id`
- `group_id`
- `course_id`
- `subject_id`
- `competency_id`
- `observation_id`
- `media_id`
- `report_id`

Bestehende historische Seed-IDs und Prototyp-Bezeichner werden nur kontrolliert migriert.

Die fachlichen Zuordnungsfelder fuer neue Architekturarbeit sind `group_id` und `course_id`.

## ID-Strategie

Die folgende ID-Strategie ist projektweit verbindlich fuer neue fachliche Entitaeten:

| Entity | ID-Feld | Format | Beispiel |
| --- | --- | --- | --- |
| Student | `student_id` | `STU-######` | `STU-000001` |
| Group | `group_id` | `GRP-######` | `GRP-000001` |
| Course | `course_id` | `CRS-######` | `CRS-000001` |
| Competency | `competency_id` | `CMP-######` | `CMP-000001` |
| Observation | `observation_id` | `OBS-######` | `OBS-000001` |
| Media | `media_id` | `MED-######` | `MED-000001` |

Regeln:

- IDs sind technische Identitaeten und bleiben stabil.
- Sichtbare Namen duerfen sich aendern, IDs nicht.
- Neue IDs werden fortlaufend je Entity erzeugt.
- Historische Seed-IDs wurden fuer Student in Sprint 4.2c kontrolliert migriert.
- VBA-Navigation verwendet weiterhin ausschliesslich das jeweilige ID-Feld, nicht das konkrete Praefix.

## Named Ranges

Registrierte bestehende Named Ranges:

- `ui_profile_selected_student_id`
- `ui_profile_back_to_class_overview`
- `ui_student_slot_XX`
- `ui_student_slot_id_XX`
- `ui_class_search`
- `ui_class_search_input`
- `ui_action_new_observation`

`XX` steht fuer zweistellige Slotnummern wie `01`, `02`, `03`.

Zukuenftige Named-Range-Muster:

- `ui_competency_slot_XX`
- `ui_competency_slot_id_XX`
- `ui_report_slot_XX`
- `ui_report_slot_id_XX`
- `ui_subject_slot_XX`
- `ui_subject_slot_id_XX`

## Shape-Praefixe

Registrierte bestehende Shape-Praefixe:

- `ui_nav_student_card_`
- `ui_nav_profile_back`

Zukuenftige Shape-Praefixe:

- `ui_nav_competency_card_`
- `ui_nav_report_card_`
- `ui_nav_subject_card_`

Shape-Namen bestehen aus Praefix plus zweistelliger Slotnummer.

Beispiele:

- `ui_nav_student_card_01`
- `ui_nav_competency_card_01`
- `ui_nav_report_card_01`
- `ui_nav_subject_card_01`

## Erlaubte Praefixe

- `data_` fuer Workbook-Datenquellen und Tabellen
- `ui_` fuer UI-Anker und UI-Projektionen
- `ui_nav_` fuer navigierende Shapes
- `frm_` fuer VBA-UserForms
- `ctl_` fuer technische UserForm-Control-Namen
- `ws` fuer Worksheet-CodeNames
- `Open` fuer zentrale VBA-Navigationsprozeduren

## Verbotene technische Namen

Nicht erlaubt sind:

- technische Namen mit Umlauten
- technische Namen mit Leerzeichen
- sichtbare deutsche UI-Begriffe als technische Schluessel
- Namen, die mit Excel/VBA-Objekttypen kollidieren, zum Beispiel `shape`, `range`, `worksheet`, `name`, `index`
- neue kreative Praefixe ohne Registry-Erweiterung
- fachliche Anzeigenamen als technische Identitaet

## Navigationsprozeduren

Registriert:

- `OpenStudentProfileById(student_id)`
- `OpenClassOverview()`
- `ImportVbaSourcesToSeed(globalsPath, navigationPath, uiPath)`

Vorgesehen:

- `OpenNewStudentDialog()`
- `OpenCompetencyById(competency_id)`
- `OpenReportById(report_id)`
- `OpenSubjectById(subject_id)`

## SQLite-Spike

Registrierter Spike-Pfad:

- `data/kompetenzmanager.sqlite`

Registrierte SQLite-Tabellen:

- `students`
- `groups`
- `courses`

Registrierte Python-Spike-Komponenten:

- `SQLiteDatabase`
- `SQLiteStudentRepository`
- `SQLiteGroupRepository`
- `SQLiteCourseRepository`
- `create_sqlite_seed_database(path)`
- `build_workbook_data_from_sqlite(path)`

Registrierte Spike-Skripte:

- `scripts/create_sqlite_spike.py`

## Application Command Layer

Registrierte Python-Module:

- `src/application/dispatcher.py`
- `src/application/commands/student.py`
- `src/application/commands/observation.py`
- `src/application/commands/report.py`

Registrierte Python-Klassen und Funktionen:

- `ApplicationCommandDispatcher`
- `CommandDispatchError`
- `CommandHandler`
- `SuccessResult`
- `ErrorResult`
- `CreateStudentCommand`
- `student_create_handler(service)`

Registrierte Command-Namen:

- `student.create`

## UserForms

Registrierte UserForm-Namen:

- `frm_student_new`

Vorgesehene UserForm-Namen:

- `frm_observation_new`

Registrierte Control-Namen fuer `frm_student_new`:

- `ctl_first_name_label`
- `ctl_first_name`
- `ctl_last_name_label`
- `ctl_last_name`
- `ctl_group_id_label`
- `ctl_group_id`
- `ctl_course_id_label`
- `ctl_course_id`
- `ctl_student_notes_label`
- `ctl_student_notes`
- `ctl_document_section_label`
- `ctl_document_empty_state`
- `ctl_document_list`
- `ctl_add_document`
- `ctl_cancel`
- `ctl_save`

Vorgesehene Control-Namen fuer `frm_observation_new`:

- `ctl_observation_date`
- `ctl_observation_context`
- `ctl_competency_selection`
- `ctl_rating`
- `ctl_observation_note`
- `ctl_media_list`
- `ctl_add_media`

## VBA-Module

Registrierte Standardmodule im Seed:

- `Globals`
- `Navigation`
- `UI`
- `SeedImport`

`SeedImport` ist das Bootstrap-Modul fuer den automatischen Import versionierter `.bas`-Quellen in `seeds/JenaplanSeed.xlsm`.
