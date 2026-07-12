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
- `updated_at`

Beispiele fuer sichtbare Begriffe:

- Stammgruppe
- Kurs
- Schuelerprofil
- Kompetenz
- Lernentwicklungsbericht

## Workbook-CodeNames

Status: Archivierter Legacy-Pfad unter `legacy/excel/`. Bestehende Workbook-CodeNames bleiben fuer historische Arbeitsmappen und reproduzierbare Altstaende stabil. Neue Hauptanwendungsfeatures erzeugen keine neuen Workbook-CodeNames.

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

Status: Legacy-Workbook-Projektion unter `legacy/excel/`. Aktive PySide-Features nutzen SQLite, Adapter und ViewModels statt Hidden Sheets.

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

Status: Legacy-Workbook-Projektion unter `legacy/excel/`. Aktive PySide-Features nutzen SQLite-Tabellen und ViewModels.

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

## Aktive SQLite-Tabellen

Aktive SQLite-Tabellen verwenden englische, ASCII-kompatible technische Namen.

Registriert:

- `students`
- `groups`
- `courses`
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`
- `competencies`
- `observations`
- `observation_competency_ratings`
- `student_competency_confirmations`
- `documents`
- `documentation_subject_settings`

`documentation_subject_settings` speichert ausschliesslich, welche `subject_id` fuer Dokumentations- und Auswertungslogik als dokumentationsrelevant gelten. Die Tabelle ersetzt nicht den Kompetenzkatalog und veraendert `competencies.active` nicht.

## Sprint-3A-Mapping Kompetenzstruktur

Sprint 3A fuehrt keine neuen technischen Feldnamen und keine neuen SQLite-Spalten ein.

Die sichtbare Fachsprache fuer Kompetenzstruktur lautet:

```text
Fach -> Kompetenzbereich -> Thema -> Kompetenz
```

Mapping auf vorhandene technische Namen:

| Sichtbarer Begriff | Bestehender technischer Name |
| --- | --- |
| Fach | `subject_id` / `subject_name` |
| Kompetenzbereich | `learning_area` |
| Thema | `competency_group` |
| Kompetenz | `description` in `competencies`, `competency_text` in `observation_competency_ratings` |
| Kurzlabel fuer kompakte UI | `label` |

Regel: Keine neuen Feldnamen wie `competency_area` oder `topic` einfuehren, solange dieses Mapping fachlich ausreicht. Sichtbare UI- und Dokumentationsbegriffe duerfen deutsch sein; technische Namen bleiben stabil.

Sprint 3B ergaenzt im CSV-Katalog die optionale Spalte `competency_label`. Sie ist kein neues SQLite-Feld, sondern befuellt beim Katalogimport das bestehende Feld `competencies.label`. Ohne Wert bleibt die bisherige Fallback-Logik auf vorhandene Katalogfelder moeglich.

Bewertungen bleiben technisch in `observation_competency_ratings.rating` gespeichert. `observations` erhaelt keine globale Bewertung. Ein nicht bewerteter oder offener Kompetenzaspekt wird nicht als Ratingwert gespeichert, sondern erzeugt keine Zuordnungszeile in `observation_competency_ratings`.

## Sprint-4A Kompetenzkatalogmodell

Status: Verbindliche technische Namen fuer das produktive Kompetenzkatalogmodell. Sprint 4A speichert diese Felder im CSV-Katalog und in SQLite `competencies`.

Neue CSV-/SQLite-Felder:

| Technischer Name | Zweck |
| --- | --- |
| `learning_stage` | produktbezogene Filterstufe einer Kompetenz, getrennt vom quellenbezogenen `grade_band` |
| `catalog_status` | fachlicher Katalogstatus fuer Freigabe, Bestandsschutz und spaetere Archivierung |
| `activation_group_key` | stabiler, generischer Aktivierungsbereich fuer optionale Kompetenzgruppen |
| `catalog_default_active` | aus dem CSV uebernommene Default-Aktivitaet, getrennt von lokaler SQLite-Aktivitaet `active` |

Zulaessige Werte fuer `learning_stage`:

- `stage_1_3`
- `stage_4`
- `cross_stage`

Zulaessige Werte fuer `catalog_status`:

- `current`
- `legacy`

Optional empfohlene spaetere SQLite-Tabelle:

- `competency_activation_groups`

Regel: `grade_band` bleibt Quellenkontext. `learning_stage` ist die produktbezogene Filterstufe. `active` bleibt lokale SQLite-Aktivierung und wird beim erneuten Katalogimport fuer bestehende `competency_id`s nicht aus dem CSV ueberschrieben. `catalog_default_active` speichert nur den Katalogstandard. `catalog_status = current` ist der Standard; `catalog_status = legacy` ist ausschliesslich fuer historische Kompetenzen vorgesehen. Legacy-Kompetenzen sind standardmaessig keine neuen Dokumentationsziele.

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
| CourseGroup | `course_group_id` | stabiler technischer Key | `course-group-default` |
| Competency | `competency_id` | `CMP-######` | `CMP-000001` |
| Observation | `observation_id` | `OBS-######` | `OBS-000001` |
| Media | `media_id` | `MED-######` | `MED-000001` |

Regeln:

- IDs sind technische Identitaeten und bleiben stabil.
- Sichtbare Namen duerfen sich aendern, IDs nicht.
- Neue IDs werden fortlaufend je Entity erzeugt.
- Neue `competency_id`s werden global fortlaufend als `CMP-######` erzeugt; es gibt keine fachbezogenen Nummernkreise und keine Wiederverwendung vorhandener oder uebersprungener IDs.
- Historische Seed-IDs wurden fuer Student in Sprint 4.2c kontrolliert migriert.
- VBA-Navigation verwendet weiterhin ausschliesslich das jeweilige ID-Feld, nicht das konkrete Praefix.

## Named Ranges

Status: Archivierter Legacy-Pfad unter `legacy/excel/`. Bestehende Named Ranges bleiben stabil, solange alte Workbook-Projektionen reproduzierbar sein muessen. Neue PySide-Features nutzen keine neuen Named Ranges.

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

## Aktive Core-Referenzdaten

| Name | Zweck | Status |
| --- | --- | --- |
| `src/core/records.py` | Aktive leichte Dataclasses und deterministische Referenzdaten ohne Excel-Abhaengigkeit | aktiv |
| `StudentRecord` | Dataclass fuer Schueler-Referenzdaten und SQLite-Seed-Pfade | aktiv |
| `GroupRecord` | Dataclass fuer Stammgruppen-Referenzdaten | aktiv |
| `CourseRecord` | Dataclass fuer Kurs-Referenzdaten | aktiv |
| `ReferenceData` | Container fuer aktive Referenzdaten ohne Workbook-Bezug | aktiv |
| `seed_reference_data()` | Erzeugt deterministische Referenz-Stammdaten und Demo-Schueler fuer explizite Seed-/Testpfade | aktiv |

Regel: Aktive Referenzdaten duerfen keine `openpyxl`- oder Workbook-Abhaengigkeit einfuehren.

## Verbotene technische Namen

Nicht erlaubt sind:

- technische Namen mit Umlauten
- technische Namen mit Leerzeichen
- sichtbare deutsche UI-Begriffe als technische Schluessel
- Namen, die mit Excel/VBA-Objekttypen kollidieren, zum Beispiel `shape`, `range`, `worksheet`, `name`, `index`
- neue kreative Praefixe ohne Registry-Erweiterung
- fachliche Anzeigenamen als technische Identitaet

## Navigationsprozeduren

Status: Legacy-/Export-Pfad. Bestehende VBA-Navigationsprozeduren bleiben dokumentiert, werden aber nicht fuer neue Features, UI, Smoke-Tests oder produktive Workflows erweitert.

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

Status: Legacy. Worksheet-basierte Dialogseiten sind historische Artefakte der Excel-Linie. Neue Eingabedialoge werden fuer die PySide-Hauptanwendung dokumentiert und umgesetzt.

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
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`
- `observations`
- `observation_competency_ratings`
- `competencies`
- `documents`

Registrierte Python-Spike-Komponenten:

- `SQLiteDatabase`
- `SQLiteStudentRepository`
- `SQLiteGroupRepository`
- `SQLiteCourseRepository`
- `SQLiteCompetencyRepository`
- `SQLiteStudentCompetencyConfirmationRepository`
- `SQLiteMasterDataRepository`
- `SQLiteObservationRepository`
- `SQLiteDocumentRepository`
- `MasterDataGroupRecord`
- `MasterDataCourseRecord`
- `MasterDataCourseGroupRecord`
- `CompetencyRecord`
- `StudentCompetencyConfirmationRecord`
- `DocumentRecord`
- `ObservationCompetencyRatingRecord`
- `ObservationRecord`
- `ObservationService`
- `ObservationValidator`
- `ObservationValidationError`
- `ObservationRepositoryError`
- `create_sqlite_seed_database(path)`
- `SeedDataError`
- `SeedResult`
- `seed_test_data(database_path, reset)`

Regel: `create_sqlite_seed_database(path)` ist ein expliziter Seed-/Testpfad. Der produktive PySide-App-Start nutzt diesen Pfad nicht, damit keine Demo-Schueler erzeugt oder Nutzerdaten ueberschrieben werden.

Registrierte SQLite-/Stammdaten-Konstanten:

- `COLOR_NAME`
- `COLOR_HEX`
- `COURSE_GROUP_ID_PREFIX`
- `COURSE_COLOR_OPTIONS`
- `DEFAULT_COURSE_GROUP_ID`
- `DEFAULT_COURSE_GROUP_NAME`

Registrierte Stammdaten-Repository-Methoden:

- `SQLiteDatabase.ensure_master_data_defaults()`
- `SQLiteMasterDataRepository.list_student_groups()`
- `SQLiteMasterDataRepository.upsert_student_group(group)`
- `SQLiteMasterDataRepository.list_courses()`
- `SQLiteMasterDataRepository.upsert_course(course)`
- `SQLiteMasterDataRepository.list_course_groups()`
- `SQLiteMasterDataRepository.update_course_group(course_group)`
- `SQLiteMasterDataRepository.get_course_group_relations(course_group_id)`
- `SQLiteMasterDataRepository.replace_course_group_student_groups(course_group_id, group_ids)`
- `SQLiteMasterDataRepository.replace_course_group_courses(course_group_id, course_ids)`
- `SQLiteMasterDataRepository.next_student_group_id()`
- `SQLiteMasterDataRepository.next_course_id()`
- `SQLiteMasterDataRepository.next_course_group_id()`
- `SQLiteObservationRepository.create_observation(observation)`
- `SQLiteObservationRepository.update_observation(observation)`
- `SQLiteObservationRepository.deactivate_observation(observation_id, updated_at)`
- `SQLiteObservationRepository.list_observations()`
- `SQLiteObservationRepository.list_observations_for_student(student_id)`
- `SQLiteObservationRepository.get_observation(observation_id)`
- `SQLiteCompetencyRepository.ensure_catalog_defaults(entries)`
- `SQLiteCompetencyRepository.list_competencies()`
- `SQLiteCompetencyRepository.get_competency(competency_id)`
- `SQLiteStudentCompetencyConfirmationRepository.list_confirmations_for_student(student_id)`
- `SQLiteStudentCompetencyConfirmationRepository.get_confirmation(student_id, competency_id)`
- `SQLiteStudentCompetencyConfirmationRepository.upsert_confirmation(confirmation)`
- `SQLiteDocumentRepository.create_document(document)`
- `SQLiteDocumentRepository.list_documents_for_student(student_id)`
- `SQLiteDocumentRepository.list_documents_for_observation(observation_id)`
- `SQLiteDocumentRepository.deactivate_document(document_id)`
- `SQLiteDocumentRepository.next_document_id()`

Registrierte Spike-Skripte:

- `scripts/create_sqlite_spike.py`
- `scripts/seed_test_data.py`

Registrierte interne QS-Skripte fuer den Kompetenzkatalog:

- `scripts/validate_curriculum_catalog.py`
- `scripts/compare_curriculum_catalog.py`
- `scripts/next_competency_ids.py`
- `scripts/curriculum_catalog_tools.py`

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
- `CreateObservationCommand`
- `UpdateObservationCommand`
- `DeleteObservationCommand`
- `student_create_handler(service)`
- `observation_create_handler(service)`
- `observation_update_handler(service)`
- `observation_delete_handler(service)`

Registrierte Command-Namen:

- `student.create`
- `observation.create`
- `observation.update`
- `observation.delete`

## Desktop-App

Status:

PySide ist die Hauptanwendung. Der Desktop-App-Layer bleibt Adapter/UI-Schicht und greift nicht direkt aus Widgets auf SQLite zu.

Registrierte Katalogdateien:

- `data/curriculum_catalog_v1.csv`

Registrierte Python-Module:

- `assets/app_icon.png`
- `src/desktop_app/main.py`
- `src/desktop_app/app.py`
- `src/desktop_app/assets.py`
- `src/desktop_app/shell.py`
- `src/desktop_app/navigation.py`
- `src/desktop_app/theme.py`
- `src/desktop_app/student_adapter.py`
- `src/desktop_app/student_list_view.py`
- `src/desktop_app/new_student_dialog.py`
- `src/desktop_app/adapters/curriculum_desktop_adapter.py`
- `src/desktop_app/adapters/master_data_desktop_adapter.py`
- `src/desktop_app/adapters/student_desktop_adapter.py`
- `src/desktop_app/dialogs/app_info_dialog.py`
- `src/desktop_app/dialogs/dialog_buttons.py`
- `src/desktop_app/dialogs/master_data_dialog.py`
- `src/desktop_app/dialogs/new_observation_dialog.py`
- `src/desktop_app/dialogs/new_student_dialog.py`
- `src/desktop_app/screens/master_data_screen.py`
- `src/desktop_app/screens/overview_screen.py`
- `src/desktop_app/screens/students_screen.py`
- `src/desktop_app/screens/student_profile_screen.py`
- `src/desktop_app/screens/placeholder_screen.py`
- `src/desktop_app/view_models/master_data_view_model.py`
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
- `APP_ICON_RELATIVE_PATH`
- `project_root()`
- `app_icon_path()`
- `load_app_icon_pixmap(size)`
- `create_app_icon_label(size)`
- `apply_app_theme(app)`
- `APP_STYLESHEET`
- `PRIMARY_BUTTON_STYLESHEET`
- `create_card()`
- `set_label_style(label, role)`
- `ObservationFilterBar`
- `ObservationFilterInput`
- `ObservationTextActionButton`
- `ObservationResetButton`
- `NewObservationDialog.subject_options`
- `QDateEdit`
- `QDateTimeEdit`
- `QTimeEdit`
- `COLOR_NAVY`
- `COLOR_BLUE`
- `COLOR_TURQUOISE`
- `COLOR_GREEN`
- `COLOR_ORANGE`
- `StudentDesktopAdapter`
- `StudentDesktopAdapter.list_students(group_id, group_ids, course_id)`
- `StudentDesktopAdapter.create_update_observation_command(draft)`
- `StudentDesktopAdapter.update_observation(draft)`
- `StudentDesktopAdapter.delete_observation(observation_id)`
- `StudentDesktopAdapter.observation_draft_for_edit(observation_id)`
- `StudentDesktopAdapter.list_competency_overview_for_student(student_id)`
- `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)`
- `StudentDesktopAdapter.list_documentation_status_for_student(student_id)`
- `StudentDesktopAdapter.list_documents_for_student(student_id)`
- `StudentDesktopAdapter.add_student_document(student_id, source_path, document_type, title, note, observation_id)`
- `StudentDesktopAdapter.remove_document(document_id)`
- `StudentDesktopAdapter.get_report_preview_for_student(student_id)`
- `StudentDesktopAdapter.settings_view_model()`
- `StudentDesktopAdapter.list_documentation_subject_options()`
- `StudentDesktopAdapter.list_observation_subject_options(initial_draft)`
- `StudentDesktopAdapter.list_observation_competency_subject_groups(initial_draft)`
- `StudentDesktopAdapter.save_active_documentation_subjects(subject_ids)`
- `StudentDesktopAdapter._active_documentation_subject_ids()`
- `StudentDesktopAdapter._initial_observation_subject_key(initial_draft)`
- `StudentDesktopAdapter._initial_observation_subject_label(initial_draft)`
- `StudentDesktopAdapter._documentation_relevant_competencies()`
- `StudentDesktopAdapter._report_development_line(competency)`
- `StudentDesktopAdapter._report_development_label(rating_history)`
- `StudentDesktopAdapter._is_monotonic(scores, increasing)`
- `StudentDesktopAdapter.save_competency_confirmation(student_id, competency_id, confirmed_rating, note)`
- `StudentCompetencyStatusViewModel.documentation_state`
- `StudentCompetencyStatusViewModel.observed_proposal`
- `StudentCompetencyEvidenceViewModel`
- `StudentDocumentationLearningAreaStatus`
- `SettingsScreen`
- `SettingsScreen.documentation_subjects_save_requested`
- `SettingsScreen.set_settings(view_model)`
- `SettingsScreen.set_documentation_subjects(subjects)`
- `SettingsScreen.show_documentation_subjects_saved()`
- `DocumentationSubjectSettingsSection`
- `DocumentationSubjectCheckbox_{subject_id}`
- `DocumentationSubjectSaveButton`
- `SettingsStatusLabel`
- `DOCUMENTATION_SUBJECTS_HELP_TEXT`
- `DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE`
- `StudentProfileScreen.DEFAULT_OBSERVATION_LIMIT`
- `StudentProfileScreen.apply_observation_filters()`
- `StudentProfileScreen.reset_observation_filters()`
- `StudentProfileScreen.toggle_observation_limit()`
- `StudentProfileScreen._populate_observation_subject_filter(observations)`
- `StudentProfileScreen._filtered_observations()`
- `StudentProfileScreen._visible_observations(observations)`
- `StudentProfileScreen._update_observation_limit_action(observations)`
- `StudentProfileScreen._observation_filter_is_active()`
- `StudentProfileScreen._matches_observation_filters(observation, subject_filter, rating_filter, search_text)`
- `StudentProfileScreen._observation_search_text(observation)`
- `StudentProfileScreen._observation_summary(observation)`
- `StudentProfileScreen._toggle_observation_details(details_widget, details_button)`
- `StudentProfileScreen._observation_actions(observation)`
- `StudentProfileScreen._note_preview(note, max_length)`
- `StudentProfileScreen._competency_group_card(group)`
- `StudentProfileScreen._toggle_competency_group_details(details_container, details_button)`
- `StudentProfileScreen._competency_status_row(competency)`
- `StudentProfileScreen._competency_confirmation_actions(competency)`
- `StudentProfileScreen._request_competency_confirmation(competency, confirmed_rating)`
- `StudentProfileScreen.set_documents(documents)`
- `StudentProfileScreen._documents_card()`
- `StudentProfileScreen._empty_documents_card()`
- `StudentProfileScreen._document_row(document)`
- `StudentProfileScreen.document_remove_requested(student_id, document_id)`
- `StudentProfileScreen._request_document_remove(document_id)`
- `StudentProfileScreen.open_document_file(file_path)`
- `StudentProfileScreen._observation_attachments_block(observation)`
- `StudentProfileScreen.set_documentation_statuses(statuses)`
- `StudentProfileScreen._documentation_status_card()`
- `StudentProfileScreen._toggle_documentation_status_details(details_container, details_button)`
- `StudentProfileScreen._empty_documentation_status_card()`
- `StudentProfileScreen._missing_competencies_block(missing_competencies)`
- `StudentProfileScreen._toggle_missing_competencies(details_container, details_button, count)`
- `StudentProfileScreen.set_report_preview(report_preview)`
- `StudentProfileScreen._report_subject_card(section)`
- `StudentProfileScreen._report_bucket(title, competencies)`
- `StudentProfileScreen._report_evidence_block(observations)`
- `StudentProfileScreen.report_text()`
- `StudentProfileScreen.copy_report_text_to_clipboard()`
- `StudentProfileScreen.export_report_text()`
- `StudentProfileScreen.export_report_text_to_path(target_path)`
- `StudentProfileScreen._default_report_export_filename()`
- `CompetencyConfirmationRatingSelect`
- `CompetencyGroupDetailsButton`
- `CompetencyGroupDetails`
- `MissingCompetenciesDetailsButton`
- `MissingCompetenciesDetails`
- `MasterDataDesktopAdapter`
- `MasterDataDesktopAdapter.add_course_group(name, selected_group_ids, selected_course_ids)`
- `MasterDataDesktopAdapter.update_course_group(course_group_id, name, selected_group_ids, selected_course_ids)`
- `CurriculumDesktopAdapter`
- `CurriculumCatalogEntry`
- `CurriculumCompetencyGroup`
- `CurriculumSubjectOption`
- `CATALOG_REQUIRED_FIELDS`
- `CURRICULUM_CATALOG_V1_PATH`
- `CurriculumCatalogEntry.competency_id`
- `CurriculumCatalogEntry.subject_id`
- `CurriculumCatalogEntry.competency_display_name`
- `CurriculumCatalogEntry.competency_detail_label`
- `StudentListItem`
- `StudentListItem.documentation_status`
- `StudentDetailViewModel`
- `GroupSummaryViewModel`
- `StudentReportCompetencyViewModel`
- `StudentReportDevelopmentViewModel`
- `StudentReportEvidenceViewModel`
- `StudentReportSubjectSectionViewModel`
- `StudentReportSubjectSectionViewModel.current_statuses`
- `StudentReportPreviewViewModel`
- `StudentDocumentViewModel`
- `StudentDocumentViewModel.display_title`
- `StudentDocumentViewModel.created_date_label`
- `StudentDocumentViewModel.observation_link_label`
- `format_student_report_preview_text(student, report_preview, created_date)`
- `MasterDataItemViewModel`
- `MasterDataViewModel`
- `CourseGroupViewModel`
- `SettingsViewModel`
- `DocumentationSubjectOptionViewModel`
- `normalize_master_data_name(name)`
- `course_color_from_key(color_key, fallback_index)`
- `course_color_name(color_hex)`
- `COURSE_COLOR_OPTIONS`
- `COURSE_GROUP_EMPTY_GROUPS_MESSAGE`
- `COURSE_GROUP_EMPTY_COURSES_MESSAGE`
- `COURSE_GROUP_DUPLICATE_NAME_MESSAGE`
- `MASTER_DATA_EMPTY_NAME_MESSAGE`
- `MASTER_DATA_SAVE_PLACEHOLDER_MESSAGE`
- `filter_student_list(students, search_text)`
- `sort_student_list(students, course_order_by_id)`
- `PROFILE_ACTION_MESSAGES`
- `PROFILE_SECTION_PLACEHOLDERS`
- `ObservationCompetencyRatingDraft`
- `ObservationCompetencyRatingDraft.competency_id`
- `ObservationCompetencyRatingDraft.subject_display_name`
- `ObservationSubjectOptionViewModel`
- `ObservationCompetencySubjectGroupViewModel`
- `ObservationCompetencySubjectGroupViewModel.subject_key`
- `ObservationCompetencySubjectGroupViewModel.subject_display_name`
- `ObservationCompetencySubjectGroupViewModel.learning_area_groups`
- `ObservationLearningAreaGroupViewModel`
- `ObservationLearningAreaGroupViewModel.learning_area`
- `ObservationLearningAreaGroupViewModel.competency_groups`
- `ObservationCompetencyGroupViewModel`
- `ObservationCompetencyGroupViewModel.competency_group`
- `ObservationCompetencyGroupViewModel.competencies`
- `ObservationCompetencyOptionViewModel`
- `ObservationCompetencyOptionViewModel.competency_id`
- `ObservationCompetencyOptionViewModel.subject_key`
- `ObservationCompetencyOptionViewModel.subject_display_name`
- `ObservationCompetencyOptionViewModel.learning_area`
- `ObservationCompetencyOptionViewModel.competency_group`
- `ObservationCompetencyOptionViewModel.competency_text`
- `ObservationCompetencyOptionViewModel.competency_label`
- `ObservationCompetencyOptionViewModel.selected`
- `ObservationCompetencyOptionViewModel.rating`
- `ObservationCompetencyOptionViewModel.catalog_status`
- `ObservationCompetencyOptionViewModel.is_active`
- `StudentDesktopAdapter.list_recent_observation_competencies(student_id, initial_draft)`
- `NewObservationDialog.recent_competencies`
- `NewObservationDialog.recent_competency_chips`
- `ObservationRecentCompetencies`
- `ObservationRecentCompetencyChip`
- `ObservationRatingSelector`
- `ObservationCatalogCompetencyTile`
- `NewObservationDialog.competency_catalog_tiles`
- `ObservationThreeZoneWorkspace`
- `ObservationSelectedScroll`
- `ObservationCatalogScroll`
- `ObservationAttachmentsScroll`
- `ObservationPersistentActions`
- `ObservationAttachmentDraft`
- `ObservationAttachmentDraft.display_label`
- `ObservationDraftViewModel`
- `ObservationDraftViewModel.observation_id`
- `ObservationDraftViewModel.subject_id`
- `ObservationDraftViewModel.subject_display_name`
- `ObservationDraftViewModel.attachments`
- `ObservationListItem`
- `ObservationListItem.attachments`
- `ObservationRatingViewModel`
- `StudentCompetencyStatusViewModel`
- `StudentCompetencyStatusViewModel.rating_history`
- `StudentCompetencyStatusViewModel.observation_count`
- `StudentCompetencyStatusViewModel.weighted_score`
- `StudentCompetencyStatusViewModel.confirmed_rating`
- `StudentCompetencyStatusViewModel.confirmed_at`
- `StudentCompetencyStatusViewModel.confirmation_note`
- `StudentCompetencyStatusViewModel.rating_history_label`
- `StudentCompetencyStatusViewModel.observation_count_label`
- `StudentCompetencyStatusViewModel.confirmation_status_label`
- `StudentCompetencyStatusViewModel.confirmation_meta_label`
- `StudentCompetencySubjectGroup`
- `StudentCompetencySubjectGroup.missing_competencies`
- `StudentDocumentationSummaryViewModel`
- `StudentDocumentationSummaryViewModel.list_label`
- `StudentDocumentationSummaryViewModel.profile_summary_label`
- `StudentDocumentationSummaryViewModel.weak_subjects_label`
- `documentation_summary_from_subjects(statuses)`
- `empty_documentation_summary()`
- `REPORT_NO_OBSERVATIONS_MESSAGE`
- `StudentDocumentationSubjectStatus`
- `StudentDocumentationSubjectStatus.progress_label`
- `StudentDocumentationSubjectStatus.missing_count_label`
- `StudentMissingCompetencyViewModel`
- `OBSERVATION_CONTEXT_OPTIONS`
- `OBSERVATION_CROSS_SUBJECT_LABEL`
- `OBSERVATION_RATING_OPTIONS`
- `OBSERVATION_SAVE_SUCCESS_MESSAGE`
- `OBSERVATION_UPDATE_SUCCESS_MESSAGE`
- `OBSERVATION_SAVE_VALIDATION_MESSAGE`
- `OBSERVATION_ATTACHMENT_EMPTY_STATE`
- `DOCUMENT_TYPE_OPTIONS`
- `observation_rating_label(rating)`
- `calculated_rating_from_history(ratings_newest_first)`
- `rating_from_weighted_score(score)`
- `observation_rating_keys()`
- `DIALOG_CANCEL_TEXT`
- `DIALOG_SAVE_TEXT`
- `DIALOG_PRIMARY_BUTTON_STYLE`
- `configure_save_cancel_buttons(buttons)`
- `AppShell.refresh_overview()`
- `AppShell.show_students_for_course_group(course_group_id, course_id)`
- `AppShell.open_new_course_group_dialog()`
- `AppShell.open_edit_course_group_dialog(course_group_id)`
- `AppShell.remove_student_document(student_id, document_id)`
- `OverviewScreen.set_master_data(view_model, group_summaries)`
- `OVERVIEW_GROUP_EMPTY_STATE`
- `OVERVIEW_COURSE_EMPTY_STATE`
- `MASTER_DATA_COURSE_GROUP_EMPTY_STATE`
- `MasterDataScreen.course_group_add_requested`
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
- `StudentsScreen.observation_requested`
- `StudentsScreen.back_to_overview_requested`
- `StudentProfileScreen`
- `StudentProfileScreen.profile_tabs`
- `StudentProfileOverviewViewModel`
- `build_student_profile_overview(observations, competency_groups, documentation_statuses)`
- `MasterDataScreen`
- `PlaceholderScreen`
- `AppInfoDialog`
- `CourseGroupDialog`
- `MasterDataNameDialog`
- `NewObservationDialog`
- `NewStudentDialog`
- `AppShell.open_quick_observation_dialog(student_id)`
- `AppShell.return_to_overview()`
- `main()`

Regel:

Der Desktop-App-Layer ist Adapter/UI-Schicht. Er darf Daten anzeigen, Eingaben sammeln, Commands oder Repository-Aufrufe ueber freigegebene Adapter ausloesen. Er darf keine Businesslogik enthalten, keine Schueler-IDs erzeugen und nicht direkt aus Qt-Widgets in SQLite schreiben.

## Runtime Adapter und Projection Refresh

Status: Historischer Excel/VBA-Bridge-Pfad unter `legacy/excel/`. Nicht Teil aktiver PySide-Standardchecks.

Historisch umgesetzte VBA-Adapter-Prozeduren:

- `SaveNewStudentDialog()`

Vorgesehene VBA-Adapter-Prozeduren:

- `CancelNewStudentDialog()`
- `ImportProjectionRefresh()`

Historisch umgesetzte Python-CLI/Bridge:

- `legacy/excel/km.py`
- `student create`

Historisch umgesetzte Runtime-Artefakte:

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

Status: Legacy-Archiv unter `legacy/excel/vba/`.

Registrierte Standardmodule im historischen Seed:

- `Globals`
- `Navigation`
- `UI`
- `SeedImport`

`SeedImport` war das Bootstrap-Modul fuer den automatischen Import versionierter `.bas`-Quellen in die historische Seed-Arbeitsmappe unter `legacy/excel/seeds/`.
