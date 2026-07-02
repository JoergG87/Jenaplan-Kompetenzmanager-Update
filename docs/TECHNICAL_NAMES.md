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
| Neuer-Schueler-Dialogseite | `dlg_neuer_schueler` | `wsDialogNewStudent` | Feature 1, worksheet-basierter Dialog |

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
| `dlg_neuer_schueler` | worksheet-basierte Dialogseite fuer neuen Schueler |
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
- `ui_action_new_student`
- `ui_action_new_observation`
- `ui_dialog_new_student_first_name`
- `ui_dialog_new_student_last_name`
- `ui_dialog_new_student_group`
- `ui_dialog_new_student_course`
- `ui_dialog_new_student_notes`
- `ui_dialog_new_student_document_list`
- `ui_dialog_new_student_add_document`
- `ui_dialog_new_student_cancel`
- `ui_dialog_new_student_save`

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
- `ui_dialog_` fuer worksheet-basierte Dialogseiten-Anker
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
- `ImportUserForm(formName, sourcePath)`

Vorgesehen:

- `OpenNewStudentDialog()` - deprecated UserForm-Testoeffner, nicht produktiver Feature-1-Einstieg
- `OpenCompetencyById(competency_id)`
- `OpenReportById(report_id)`
- `OpenSubjectById(subject_id)`

## Worksheet-basierte Dialogseiten

Registrierte Dialogseiten:

- `dlg_neuer_schueler`

Registrierte Anker fuer `dlg_neuer_schueler`:

- `ui_action_new_student`
- `ui_dialog_new_student_first_name`
- `ui_dialog_new_student_last_name`
- `ui_dialog_new_student_group`
- `ui_dialog_new_student_course`
- `ui_dialog_new_student_notes`
- `ui_dialog_new_student_document_list`
- `ui_dialog_new_student_add_document`
- `ui_dialog_new_student_cancel`
- `ui_dialog_new_student_save`

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

## Desktop-App-Spike

Status:

Der Desktop-App-Spike prueft PySide6 als alternativen Adapter. Er ist keine endgueltige Architekturentscheidung.

Registrierte Katalogdateien:

- `data/curriculum_catalog_v1.csv`

Registrierte Python-Module:

- `src/desktop_app/main.py`
- `src/desktop_app/app.py`
- `src/desktop_app/shell.py`
- `src/desktop_app/navigation.py`
- `src/desktop_app/student_adapter.py`
- `src/desktop_app/student_list_view.py`
- `src/desktop_app/new_student_dialog.py`
- `src/desktop_app/adapters/curriculum_desktop_adapter.py`
- `src/desktop_app/adapters/student_desktop_adapter.py`
- `src/desktop_app/dialogs/new_observation_dialog.py`
- `src/desktop_app/dialogs/new_student_dialog.py`
- `src/desktop_app/screens/overview_screen.py`
- `src/desktop_app/screens/students_screen.py`
- `src/desktop_app/screens/student_profile_screen.py`
- `src/desktop_app/screens/placeholder_screen.py`
- `src/desktop_app/view_models/observation_view_model.py`
- `src/desktop_app/view_models/student_view_model.py`

Registrierte Launcher:

- `launcher/Jenaplan_Kompetenzmanager.command`

Registrierte Python-Klassen und Funktionen:

- `JenaplanDesktopApp`
- `AppShell`
- `NavigationItem`
- `NavigationTarget`
- `NAVIGATION_ITEMS`
- `resolve_navigation_target(key)`
- `StudentDesktopAdapter`
- `MasterDataDesktopAdapter`
- `CurriculumDesktopAdapter`
- `CurriculumCatalogEntry`
- `CurriculumSubjectOption`
- `CURRICULUM_CATALOG_V1_PATH`
- `CurriculumCatalogEntry.competency_display_name`
- `CurriculumCatalogEntry.competency_detail_label`
- `StudentListItem`
- `StudentDetailViewModel`
- `GroupSummaryViewModel`
- `MasterDataItemViewModel`
- `MasterDataViewModel`
- `CourseGroupViewModel`
- `normalize_master_data_name(name)`
- `course_color_from_key(color_key, fallback_index)`
- `course_color_name(color_hex)`
- `COURSE_COLOR_OPTIONS`
- `MASTER_DATA_EMPTY_NAME_MESSAGE`
- `MASTER_DATA_SAVE_PLACEHOLDER_MESSAGE`
- `filter_student_list(students, search_text)`
- `PROFILE_ACTION_MESSAGES`
- `PROFILE_SECTION_PLACEHOLDERS`
- `ObservationCompetencyRatingDraft`
- `ObservationCompetencyRatingDraft.subject_display_name`
- `ObservationDraftViewModel`
- `OBSERVATION_CONTEXT_OPTIONS`
- `OBSERVATION_RATING_OPTIONS`
- `OBSERVATION_SAVE_PLACEHOLDER_MESSAGE`
- `OBSERVATION_ATTACHMENT_PLACEHOLDER_MESSAGE`
- `OBSERVATION_ATTACHMENT_EMPTY_STATE`
- `observation_rating_keys()`
- `DIALOG_CANCEL_TEXT`
- `DIALOG_SAVE_TEXT`
- `DIALOG_PRIMARY_BUTTON_STYLE`
- `configure_save_cancel_buttons(buttons)`
- `AppShell.refresh_overview()`
- `AppShell.show_students_for_course_group(course_group_id, course_id)`
- `OverviewScreen.set_master_data(view_model, group_summaries)`
- `OVERVIEW_GROUP_EMPTY_STATE`
- `OVERVIEW_COURSE_EMPTY_STATE`
- `MASTER_DATA_COURSE_GROUP_EMPTY_STATE`
- `APP_INFO_TITLE`
- `APP_INFO_APP_NAME`
- `APP_INFO_MODE`
- `APP_INFO_VERSION`
- `APP_INFO_STORAGE_HINT`
- `APP_INFO_EXCEL_HINT`
- `STUDENT_SEARCH_PLACEHOLDER`
- `STUDENT_LIST_EMPTY_STATE`
- `STUDENT_SEARCH_EMPTY_STATE`
- `MASTER_DATA_GROUP_EMPTY_STATE`
- `MASTER_DATA_COURSE_EMPTY_STATE`
- `STUDENT_DIALOG_SELECT_PLACEHOLDER`
- `STUDENT_DIALOG_EMPTY_NAME_MESSAGE`
- `STUDENT_DIALOG_GROUP_REQUIRED_MESSAGE`
- `STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE`
- `STUDENT_DIALOG_DRAFT_GROUP_MESSAGE`
- `STUDENT_DIALOG_DRAFT_COURSE_MESSAGE`
- `StudentListView`
- `OverviewScreen`
- `StudentsScreen`
- `StudentProfileScreen`
- `MasterDataScreen`
- `PlaceholderScreen`
- `AppInfoDialog`
- `MasterDataNameDialog`
- `NewObservationDialog`
- `NewStudentDialog`
- `main()`

Regel:

Der Desktop-App-Spike ist Adapter Layer. Er darf Daten anzeigen, Eingaben sammeln, Commands erzeugen und den `ApplicationCommandDispatcher` aufrufen. Er darf keine Businesslogik enthalten, keine Schueler-IDs erzeugen und nicht direkt in SQLite schreiben.

## Runtime Adapter und Projection Refresh

Produktiv umgesetzte VBA-Adapter-Prozeduren:

- `SaveNewStudentDialog()`

Vorgesehene VBA-Adapter-Prozeduren:

- `CancelNewStudentDialog()`
- `ImportProjectionRefresh()`

Produktiv umgesetzte Python-CLI/Bridge:

- `km.py`
- `student create`

Produktiv umgesetzte Runtime-Artefakte:

- `runtime_command.json`
- `runtime_result.json`

Vorgesehene Runtime-Artefakte:

- `runtime_projection_refresh.json`

Registrierte VBA-Konstanten fuer `dlg_neuer_schueler`:

- `NAME_DIALOG_NEW_STUDENT_FIRST_NAME`
- `NAME_DIALOG_NEW_STUDENT_LAST_NAME`
- `NAME_DIALOG_NEW_STUDENT_GROUP`
- `NAME_DIALOG_NEW_STUDENT_COURSE`
- `NAME_DIALOG_NEW_STUDENT_NOTES`
- `NAME_DIALOG_NEW_STUDENT_SAVE`
- `SHAPE_DIALOG_NEW_STUDENT_SAVE`
- `RUNTIME_COMMAND_FILE_NAME`
- `RUNTIME_RESULT_FILE_NAME`
- `RUNTIME_DATABASE_RELATIVE_PATH`

Regel:

Runtime-Artefakte enthalten keine neue fachliche Source of Truth.

Sie transportieren Commands, Ergebnisse oder Python-generierten Projection Output.

VBA darf Projection-Refresh-Artefakte nur in registrierte Projektionsbereiche kopieren.

## UserForms

Status:

VBA-UserForms sind ab Feature 1 fuer Excel auf macOS deprecated und nicht mehr das primaere Eingabe-Pattern.

`frm_student_new` bleibt als experimenteller Artefaktstand erhalten, bis ein eigener Bereinigungssprint das Artefakt entfernt oder migriert.

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
