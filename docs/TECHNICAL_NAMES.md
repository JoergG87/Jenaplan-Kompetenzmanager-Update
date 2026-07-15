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
- `timetable_entries`
- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`
- `learning_reports`
- `learning_report_revisions`
- `learning_report_pdf_artifacts`
- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`
- `learning_conferences`
- `learning_conference_revisions`
- `learning_conference_pdf_artifacts`

`documentation_subject_settings` speichert ausschliesslich, welche `subject_id` fuer Dokumentations- und Auswertungslogik als dokumentationsrelevant gelten. Die Tabelle ersetzt nicht den Kompetenzkatalog und veraendert `competencies.active` nicht.

Die Tabellen mit Praefix `report_draft_` speichern ausschliesslich den bearbeitbaren Arbeitsentwurf eines Lernentwicklungsberichts. Sie sind keine finale Berichtsdomain, enthalten keine Kompetenzbewertung und frieren keine Kompetenz- oder Beobachtungsinhalte ein.

`learning_reports` speichert die stabile Identitaet eines aus genau einem `RPD` hervorgegangenen Lernentwicklungsberichts. `learning_report_revisions` speichert dessen unveraenderliche fachliche Revisionen als kanonischen JSON-Snapshot mit SHA-256-Hash. Beide Tabellen erweitern den Draft additiv; sie veraendern weder `RPD` noch dessen Statusvertrag.

Registrierte technische Felder fuer persistente Berichtsentwuerfe:

- `report_draft_id`
- `learning_report_id`
- `learning_report_revision_id`
- `learning_report_pdf_artifact_id`
- `source_report_draft_id`
- `revision_number`
- `snapshot_schema_version`
- `snapshot_json`
- `snapshot_sha256`
- `relative_file_path`
- `mime_type`
- `file_size_bytes`
- `pdf_sha256`
- `finalized_at`
- `finalized_by_display_name`
- `superseded_at`
- `report_type`
- `period_start`
- `period_end`
- `status`
- `teacher_name`
- `overall_text`
- `strengths_text`
- `development_text`
- `support_needs_text`
- `next_goals_text`
- `chart_type`

Zulaessiger Status in Sprint 7F.1: `draft`.

Zulaessiger Berichtstyp in Sprint 7F.1: `learning_development`.

Zulaessige Diagrammtypen:

- `documentation_coverage`
- `competency_timeline`
- `observation_timeline`

`report_draft_id` verwendet das Format `RPD-######`.

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

`is_quick_observation` ist ausschliesslich ein fluechtiger Command-/ViewModel-Name fuer die bewusste Eingabe und Anzeige einer Schnellbeobachtung. Er ist kein SQLite-Feld. Persistiert und rekonstruiert wird der Zustand als aktive Beobachtung mit nichtleerer Notiz und ohne Zeilen in `observation_competency_ratings`.

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
- `report_draft_id`
- `learning_report_id`
- `learning_report_revision_id`

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
| ReportDraft | `report_draft_id` | `RPD-######` | `RPD-000001` |
| LearningReport | `learning_report_id` | `RPT-######` | `RPT-000001` |
| LearningReportRevision | `learning_report_revision_id` | `RPV-######` | `RPV-000001` |
| TimetableEntry | `timetable_entry_id` | `TTE-######` | `TTE-000001` |

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
- `SeedResult.timetable_count`
- `_seed_timetable(database)`
- `_seed_all_subject_history(database, service, students)`

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
- `src/desktop_app/components.py`
- `src/desktop_app/icons.py`
- `src/desktop_app/screens/master_data_screen.py`
- `src/desktop_app/screens/overview_screen.py`
- `src/desktop_app/screens/students_screen.py`
- `src/desktop_app/screens/students_workspace.py`
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
- `set_button_role(button, role)`
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
- `StudentDesktopAdapter.competency_cockpit_for_student(student_id)`
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
- `StudentCompetencyStatusViewModel.documentation_state_label`
- `StudentCompetencyStatusViewModel.confirmed_status_label`
- `StudentCompetencyEvidenceViewModel`
- `StudentCompetencyCockpitViewModel`
- `StudentCompetencyCockpitSubjectViewModel`
- `StudentCompetencyCockpitLearningAreaViewModel`
- `StudentCompetencyCockpitTopicViewModel`
- `build_student_competency_cockpit(statuses)`
- `StudentProfileDashboardViewModel`
- `StudentProfileOrientationChangeViewModel`
- `StudentProfileOrientationEventViewModel`
- `StudentProfileUndocumentedSubjectViewModel`
- `build_student_profile_dashboard(statuses, documentation_statuses, as_of)`
- `StudentDesktopAdapter.student_profile_dashboard_for_student(student_id, as_of)`
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
- `StudentProfileScreen.set_competency_cockpit(cockpit)`
- `StudentProfileScreen.apply_competency_cockpit_filters()`
- `StudentProfileScreen.reset_competency_cockpit_filters()`
- `StudentProfileScreen._populate_competency_subject_filter(cockpit)`
- `StudentProfileScreen._filtered_cockpit_subject(subject, documentation_filter, learning_stage_filter, search_text)`
- `StudentProfileScreen._filtered_cockpit_learning_area(area, documentation_filter, learning_stage_filter, search_text)`
- `StudentProfileScreen._matches_competency_documentation_filter(competency, documentation_filter)`
- `StudentProfileScreen._cockpit_subject_card(subject, historical)`
- `StudentProfileScreen._cockpit_learning_area_card(subject_id, area, historical)`
- `StudentProfileScreen._cockpit_topic_card(subject_id, learning_area, topic, historical)`
- `StudentProfileScreen._cockpit_competency_row(competency)`
- `StudentProfileScreen._cockpit_competency_details(competency)`
- `StudentProfileScreen._make_clickable_card(card, action, tooltip)`
- `StudentProfileScreen._historical_competency_section(subjects)`
- `StudentProfileScreen._toggle_cockpit_section(key, details, button, collapsed_text, expanded_text)`
- `StudentProfileScreen._show_observations_tab()`
- `StudentProfileScreen._documentation_subject_details(status)`
- `StudentProfileScreen._toggle_documentation_status_details(details_container, details_button)`
- `StudentProfileScreen.set_documents(documents)`
- `StudentProfileScreen._documents_card()`
- `StudentProfileScreen._empty_documents_card()`
- `StudentProfileScreen._document_row(document)`
- `StudentProfileScreen.document_remove_requested(student_id, document_id)`
- `StudentProfileScreen._request_document_remove(document_id)`
- `StudentProfileScreen.open_document_file(file_path)`
- `StudentProfileScreen._observation_attachments_block(observation)`
- `StudentProfileScreen.set_report_preview(report_preview)`
- `StudentProfileScreen._report_subject_card(section)`
- `StudentProfileScreen._report_bucket(title, competencies)`
- `StudentProfileScreen._report_evidence_block(observations)`
- `StudentProfileScreen.report_text()`
- `StudentProfileScreen.copy_report_text_to_clipboard()`
- `StudentProfileScreen.export_report_text()`
- `StudentProfileScreen.export_report_text_to_path(target_path)`
- `StudentProfileScreen._default_report_export_filename()`
- `CompetencyCockpitSubjectCard`
- `CompetencyCockpitFilterBar`
- `CompetencyCockpitSubjectFilter`
- `CompetencyCockpitDocumentationFilter`
- `CompetencyCockpitFilterResetButton`
- `CompetencyCockpitEmptyFilterState`
- `CompetencyCockpitSubjectButton`
- `CompetencyCockpitSubjectDetails`
- `CompetencyCockpitLearningAreaCard`
- `CompetencyCockpitLearningAreaButton`
- `CompetencyCockpitLearningAreaDetails`
- `CompetencyCockpitTopicCard`
- `CompetencyCockpitTopicButton`
- `CompetencyCockpitTopicDetails`
- `CompetencyCockpitCompetencyRow`
- `CompetencyCockpitCompetencyButton`
- `CompetencyCockpitCompetencyDetails`
- `CompetencyCockpitObservationsButton`
- `CompetencyCockpitHistoricalCard`
- `CompetencyCockpitHistoricalButton`
- `CompetencyCockpitHistoricalDetails`
- `CompetencyCockpitProgressBar`
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
- `StudentDetailViewModel.course_color_name`
- `StudentDetailViewModel.course_color_hex`
- `DashboardSuggestedStudentViewModel.course_name`
- `DashboardSuggestedStudentViewModel.course_color_name`
- `DashboardSuggestedStudentViewModel.course_color_hex`
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
- `CourseBadge`
- `CourseBadge.set_course(course_name, color_hex)`
- `CourseBadgeIndicator`
- `CourseBadgeLabel`
- `semanticRole = courseContext`
- `courseColorHex`
- `usesNeutralColor`
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
- `ObservationCompetencyOptionViewModel.learning_stage`
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
- `configure_save_cancel_buttons(buttons)`
- `AppShell.refresh_overview()`
- `AppShell.show_students_for_course_group(course_group_id, course_id)`
- `AppShell.open_new_course_group_dialog()`
- `AppShell.open_edit_course_group_dialog(course_group_id)`
- `AppShell.remove_student_document(student_id, document_id)`
- `GroupOverviewScreen.set_master_data(view_model, group_summaries)`
- `OVERVIEW_GROUP_EMPTY_STATE`
- `OVERVIEW_COURSE_EMPTY_STATE`
- `MASTER_DATA_COURSE_GROUP_EMPTY_STATE`
- `MasterDataScreen.course_group_add_requested`
- `MasterDataScreen._activate_table_row(table, row)`
- `APP_INFO_TITLE`
- `APP_INFO_APP_NAME`
- `APP_INFO_MODE`
- `APP_INFO_VERSION`
- `APP_INFO_STORAGE_HINT`
- `APP_INFO_PURPOSE`
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
- `StudentsWorkspace`
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

## Sprint 7F - Produktiver Lernentwicklungsbericht

Registrierte Python-Module:

- `src/desktop_app/dialogs/learning_report_dialog.py`
- `src/desktop_app/view_models/learning_report_view_model.py`

Registrierte technische Namen:

- `PrepareLearningReportQuery`
- `LearningReportSourceData`
- `LearningReportApplicationService`
- `LearningReportPreparationViewModel`
- `LearningReportSubjectViewModel`
- `LearningReportCompetencyViewModel`
- `LearningReportEvidenceViewModel`
- `LearningReportDraft`
- `LearningReportDialog`
- `StudentDesktopAdapter.learning_report_preparation_for_student(student_id, retained_competency_ids=())`
- `build_learning_report_preparation(student, statuses, observations)`
- `build_report_output_model(preparation, draft)`
- `AppShell.open_learning_report_dialog(student_id)`
- `AppShell.export_learning_report_pdf(output_model)`

Regel: Diese Namen bezeichnen ausschliesslich die fluechtige Berichtsvorbereitung und das neutrale Ausgabemodell. Sie fuehren keine persistente Berichtsentitaet und keine zweite Kompetenzstatuslogik ein.

Registrierte Qt-Objektnamen fuer das Sprint-7F.1-UX-Alignment:

- `LearningReportWorkspace`
- `LearningReportTopBar`
- `LearningReportBrand`
- `LearningReportTopHint`
- `LearningReportEyebrow`
- `LearningReportStatusPill`
- `LearningReportInternalCard`
- `LearningReportResponsibilityNote`
- `LearningReportPreviewPanel`
- `LearningReportPreviewScroll`
- `LearningReportPreviewCanvas`
- `LearningReportPaperPage`
- `LearningReportDocumentBlock`

## Sprint 7F.1 - Persistenter Berichtsentwurf

Registrierte Python-Module:

- `src/core/report_draft.py`
- `tests/test_report_draft.py`

Registrierte Klassen und Application-Namen:

- `ReportDraftRecord`
- `ReportDraftSubjectRecord`
- `ReportDraftChartSelectionRecord`
- `ReportDraftRepository`
- `SQLiteReportDraftRepository`
- `ReportDraftService`
- `ReportDraftApplicationService`
- `CreateLearningReportDraftCommand`
- `UpdateLearningReportDraftCommand`
- `GetLearningReportDraftQuery`
- `ListLearningReportDraftsQuery`
- `LearningReportDraftViewModel`
- `LearningReportSubjectDraftViewModel`
- `LearningReportChartSelectionViewModel`
- `StudentDesktopAdapter.save_learning_report_draft(draft)`
- `StudentDesktopAdapter.load_learning_report_draft(report_draft_id)`
- `StudentDesktopAdapter.list_learning_report_drafts_for_student(student_id)`

Registrierte Konstanten:

- `REPORT_DRAFT_ID_PREFIX`
- `REPORT_DRAFT_STATUS`
- `LEARNING_DEVELOPMENT_REPORT_TYPE`
- `REPORT_DRAFT_CHART_TYPES`

Regel: Der persistente Entwurf ist ein bearbeitbarer Arbeitsstand. Er ist kein `ReportOutputModel`, keine finale Berichtsversion und keine Quelle fuer Kompetenzstatus oder Beobachtungsbewertung.

## Sprint 7F.2 - Prototypgetreue Berichtswerkstatt

Registrierte technische Namen:

- `LearningReportDialog.save_requested`
- `LearningReportDialog.report_draft_view_model()`
- `LearningReportDialog.apply_saved_draft(saved)`
- `CHART_OPTIONS`
- `LearningReportModeButton`
- `LearningReportSidebar`
- `LearningReportSubjectButton`
- `LearningReportInternalBadge`
- `LearningReportReportCard`

Regel: Diese Namen bilden ausschliesslich die aus `prototypes/learning_report_ux/` portierte PySide-Navigation, Kartenhierarchie, Draft-Anbindung und Auswahl der bereits registrierten Diagrammtypen ab. Sie fuehren keine neue Datenquelle, keine Kompetenzstatuslogik und keinen zusaetzlichen Schreibprozess ein.

## Sprint 5B.1 - Bestandssichere Berichtreferenzen

Registrierte Lese- und Projektionsnamen:

- `LearningReportDraftViewModel.unavailable_observation_ids`
- `LearningReportDraft.unavailable_observation_ids`
- `SQLiteReportDraftRepository.unavailable_observation_ids(draft)`
- `StudentDesktopAdapter._learning_report_draft_view_model(record)`
- `_unavailable_evidence_blocks(draft)`
- `LearningReportDialog._unavailable_evidence_card()`
- `LearningReportUnavailableEvidence`
- `LearningReportUnavailableEvidence_<observation_id>`

Regel: `retained_competency_ids` erweitert fuer einen geladenen Berichtsdraft ausschliesslich den Lesekontext der bestehenden kanonischen Kompetenzprojektion. `unavailable_observation_ids` ist eine abgeleitete Kennzeichnung bereits gespeicherter, nicht mehr aktiver `OBS`-Referenzen und kein persistiertes Fachfeld. Beide Pfade erhalten bestehende IDs, erlauben keine neue Auswahl inaktiver Quellen und erzeugen weder Snapshottexte noch eine zweite Kompetenzstatuslogik.

## Sprint 5B.2 - Unveraenderliche Berichtrevisionen

Registrierte Python-Module:

- `src/core/learning_report.py`
- `tests/test_report_finalization.py`

Registrierte Klassen, Protokolle und Funktionen:

- `LearningReportRecord`
- `LearningReportRevisionRecord`
- `LearningReportFinalizationSource`
- `LearningReportRepository`
- `LearningReportSnapshotBuilder`
- `LearningReportFinalizationValidator`
- `ReportFinalizationService`
- `ReportFinalizationError`
- `FinalizeLearningReportCommand`
- `ReportFinalizationApplicationService`
- `canonical_snapshot_json(snapshot)`
- `snapshot_sha256(canonical_json)`
- `SQLiteLearningReportRepository`

Registrierte Konstanten und Werte:

- `LEARNING_REPORT_ID_PREFIX` mit Wert `RPT`
- `LEARNING_REPORT_REVISION_ID_PREFIX` mit Wert `RPV`
- `LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION` mit Wert `1`
- Revisionsstatus `finalized`
- Revisionsstatus `superseded`

Regel: `RPD` bleibt der bearbeitbare Arbeitsentwurf. `RPT` ist das stabile, pro `source_report_draft_id` eindeutige Berichtaggregat. Nach Revision 1 bleiben `source_report_draft_id`, `student_id`, `report_type`, `period_start` und `period_end` des `RPT` unveraenderlich; ein anderer Berichtstyp oder Zeitraum braucht einen neuen `RPD` und damit ein neues `RPT`. `RPV` ist eine unveraenderliche Revision; ausschliesslich beim atomaren Erzeugen einer Folgerevision darf der Status der bisherigen aktuellen Revision von `finalized` auf `superseded` wechseln und `superseded_at` gesetzt werden. Der kanonische Snapshot wird als UTF-8-JSON mit sortierten Schluesseln, kompakten Trennern und ohne nicht endliche Zahlen serialisiert; `snapshot_sha256` ist der kleingeschriebene SHA-256-Hexdigest exakt dieser gespeicherten JSON-Bytes.

## Sprint 5B.3 - Produktive Berichtfinalisierung und Revisionsprojektion

Registrierte Klassen und Projektionen:

- `LearningReportFinalizationPreview`
- `LearningReportRevisionState`
- `LearningReportRevisionReadService`
- `ReportRevisionApplicationService`
- `LearningReportRevisionStatusViewModel`
- `LearningReportRevisionHistoryItemViewModel`
- `LearningReportFinalizationPreviewViewModel`
- `LearningReportRevisionViewModel`
- `LearningReportRevisionSubjectViewModel`
- `LearningReportRevisionCompetencyViewModel`
- `LearningReportRevisionObservationViewModel`
- `LearningReportRevisionChartViewModel`
- `LearningReportRevisionDialog`

Registrierte Funktionen und Adapteroperationen:

- `ReportFinalizationService.prepare(report_draft_id)`
- `LearningReportRevisionReadService.report_for_draft(report_draft_id)`
- `LearningReportRevisionReadService.current_revision_for_draft(report_draft_id)`
- `LearningReportRevisionReadService.revision_history_for_draft(report_draft_id)`
- `LearningReportRevisionReadService.revision_by_id(learning_report_revision_id)`
- `LearningReportRevisionReadService.snapshot_hash_valid(revision)`
- `LearningReportRevisionReadService.snapshot_payload(learning_report_revision_id)`
- `SQLiteLearningReportRepository.get_revision(learning_report_revision_id)`
- `StudentDesktopAdapter.learning_report_revision_status(report_draft_id)`
- `StudentDesktopAdapter.prepare_learning_report_finalization(report_draft_id)`
- `StudentDesktopAdapter.finalize_learning_report(report_draft_id, finalized_by_display_name)`
- `StudentDesktopAdapter.load_learning_report_revision(learning_report_revision_id)`
- `build_learning_report_revision_status(state)`
- `build_learning_report_finalization_preview(preview)`
- `build_learning_report_revision_view_model(revision, payload)`

Registrierte Qt-Objektnamen:

- `LearningReportFinalizeButton`
- `LearningReportOpenCurrentRevisionButton`
- `LearningReportOpenRevision_<learning_report_revision_id>`
- `LearningReportFinalizationConfirmation`
- `LearningReportFinalizedByInput`
- `LearningReportFinalizationAcknowledgement`
- `LearningReportFinalizationConfirmButton`
- `LearningReportRevisionDialog`

Regel: Die Revisionsprojektion entsteht ausschliesslich aus `snapshot_json`, `LearningReportRevisionRecord` und dem gespeicherten SHA-256. Sie darf keine aktuelle Schueler-, Gruppen-, Kurs-, Kompetenz-, Beobachtungs- oder Diagrammquelle lesen. Das Draft-Ausgabemodell und die finale snapshotbasierte Adapterprojektion bleiben getrennte Quellen fuer denselben renderer-neutralen `ReportOutputModel`-Vertrag.

## Sprint 9A - Finaler PDF-Druck aus Berichtrevisionen

Registrierte Python-Module:

- `src/core/learning_report_pdf.py`
- `tests/test_learning_report_pdf.py`

Registrierte Klassen, Protokolle und Commands:

- `LearningReportPdfArtifactRecord`
- `LearningReportPdfArtifactRepository`
- `LearningReportPdfSnapshotValidator`
- `LearningReportPdfService`
- `LearningReportPdfError`
- `GenerateLearningReportPdfCommand`
- `LearningReportPdfApplicationService`
- `SQLiteLearningReportPdfArtifactRepository`
- `LearningReportPdfArtifactViewModel`

Registrierte Konstanten und Werte:

- `LEARNING_REPORT_PDF_ARTIFACT_ID_PREFIX` mit Wert `RPA`
- MIME-Type `application/pdf`

Registrierte Adapteroperationen:

- `StudentDesktopAdapter.generate_learning_report_pdf(learning_report_revision_id)`
- `StudentDesktopAdapter.load_learning_report_pdf_artifact(learning_report_revision_id)`

Registrierte Qt-Objektnamen:

- `LearningReportGenerateFinalPdfButton`
- `LearningReportFinalPdfStatus`

Regel: `RPA` identifiziert genau eine unveraenderliche PDF-Artefaktreferenz fuer eine `RPV`. Pro `learning_report_revision_id` existiert hoechstens eine `RPA`. `relative_file_path` ist relativ zum Verzeichnis der produktiven SQLite-Datei und bleibt innerhalb `documents/<student_id>/reports/<RPT>/<RPV>/`. `pdf_sha256` ist der kleingeschriebene SHA-256-Hexdigest der unveraenderten PDF-Bytes. `snapshot_sha256` kopiert den bei der Erzeugung erfolgreich bestaetigten Hash der Quellrevision. Es werden keine Renderer- oder Template-Versionsfelder eingefuehrt.

## UI Sprint 5 - Berichtswerkstatt und Revisionen

Registrierte Dialogmethoden und UI-State-Namen:

- `LearningReportDialog._set_workspace(key)`
- `LearningReportDialog._evidence_screen()`
- `LearningReportDialog._subject_evidence_editor(subject)`
- `LearningReportDialog._action_bar()`
- `LearningReportDialog._refresh_workspace_context()`
- `LearningReportDialog.workspace_navigation`
- `LearningReportDialog.evidence_navigation_group`
- `LearningReportDialog.evidence_stack`

Registrierte Qt-Objektnamen:

- `LearningReportWorkspaceNavigation`
- `LearningReportWorkspaceStack`
- `LearningReportActionBar`
- `LearningReportSaveButton`
- `LearningReportIncludeSubject_<subject_id>`
- `LearningReportSubjectText_<subject_id>_<text_key>`
- `LearningReportRevisionCanvas`
- `LearningReportRevisionPaper`

Regel: Diese Namen strukturieren ausschliesslich lokalen UI-State, Fokus, Bereichswechsel, zentrale Aktionshierarchie und Dokumentdarstellung. Sie fuehren keine Datenquelle, fachliche Filterung, Persistenz, Validierung, Snapshotauswertung oder Revisionslogik ein. `Schreiben` und `Kompetenzen & Belege` verwenden getrennte Widget-Stapel, lesen und schreiben jedoch weiterhin denselben bestehenden `LearningReportDraftViewModel` ueber die vorhandenen Dialogsignale.

## Sprint 7G.1 - Persistenter LEG-Arbeitsentwurf

Registrierte SQLite-Tabellen:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Registrierte technische Felder und Werte:

- `learning_conference_draft_id`
- `conference_date`
- `responsible_teacher`
- `conversation_entry_text`
- `child_retrospective_text`
- `teacher_perspective_text`
- `strengths_text`
- `development_fields_text`
- `prepared_goals_text`
- `prepared_support_text`
- `prepared_agreements_text`
- `agreed_goals_text`
- `agreed_support_text`
- `agreed_agreements_text`
- `responsibilities_text`
- `next_review_date`
- `cross_topic_key`

Zulaessiger Status: `draft`.

Zulaessige `cross_topic_key`-Werte aus dem freigegebenen Prototyp:

- `work_habits`
- `social_behavior`
- `independence`
- `learning_organization`

Zulaessige Diagrammtypen:

- `documentation_coverage`
- `competency_timeline`
- `observation_timeline`

`learning_conference_draft_id` verwendet das Format `LCD-######`.

Registrierte Python-Module:

- `src/core/learning_conference_draft.py`
- `src/application/commands/learning_conference.py`
- `src/desktop_app/view_models/learning_conference_view_model.py`
- `tests/test_learning_conference_draft.py`

Registrierte Klassen und Application-Namen:

- `LearningConferenceDraftRecord`
- `LearningConferenceDraftRepository`
- `SQLiteLearningConferenceDraftRepository`
- `LearningConferenceDraftService`
- `LearningConferenceDraftApplicationService`
- `CreateLearningConferenceDraftCommand`
- `UpdateLearningConferenceDraftCommand`
- `GetLearningConferenceDraftQuery`
- `ListLearningConferenceDraftsQuery`
- `PrepareLearningConferenceQuery`
- `LearningConferenceApplicationService`
- `LearningConferenceDraftViewModel`
- `LearningConferencePreparationViewModel`
- `LearningConferenceCompetencyViewModel`
- `LearningConferenceEvidenceViewModel`
- `StudentDesktopAdapter.learning_conference_preparation_for_student(student_id)`
- `StudentDesktopAdapter.save_learning_conference_draft(draft)`
- `StudentDesktopAdapter.load_learning_conference_draft(learning_conference_draft_id)`
- `StudentDesktopAdapter.list_learning_conference_drafts_for_student(student_id)`

Registrierte Konstanten:

- `LEARNING_CONFERENCE_DRAFT_ID_PREFIX`
- `LEARNING_CONFERENCE_DRAFT_STATUS`
- `LEARNING_CONFERENCE_CROSS_TOPIC_KEYS`
- `LEARNING_CONFERENCE_CHART_TYPES`

Regel: Der LEG-Arbeitsentwurf ist keine Berichtsentitaet und kein `report_type`. Er speichert manuelle Inhalte und reine Referenzen, aber weder Kompetenztexte noch Beobachtungsfachdaten, Kompetenzstaende oder Diagrammdaten.

## Sprint 7G.2 - Produktiver LEG-Arbeitsbereich

Registrierte Python-Module und UI-Einstiege:

- `src/desktop_app/dialogs/learning_conference_dialog.py`
- `tests/test_learning_conference_ui.py`
- `LearningConferenceDialog`
- `LearningConferenceDialog.save_requested`
- `LearningConferenceDialog.draft_view_model()`
- `LearningConferenceDialog.apply_saved_draft(draft)`
- `StudentProfileScreen.learning_conference_requested`
- `AppShell.open_learning_conference_dialog(student_id)`
- `_documentation_state_label(value)`
- `_rating_label(value)`

Registrierte zentrale Objektrollen:

- `LearningConferenceProfileAction`
- `LearningConferenceWorkspace`
- `LearningConferencePreparationPanel`
- `LearningConferenceConversationPanel`
- `LearningConferenceCard`
- `LearningConferenceSoftBlock`
- `LearningConferenceChartCard`
- `LearningConferenceHero`
- `LearningConferenceSection`
- `LearningConferencePrepared`
- `LearningConferenceShared`
- `LearningConferenceWarning`
- `LearningConferenceSaveButton`
- `LearningConferenceCanonicalStatus`
- `LearningConferenceUnavailableEvidence`

Regel: Diese Namen portieren ausschliesslich die freigegebene UX und binden sie an den bestehenden 7G.1-Draft. Sie fuehren keine neue Datenquelle, kein technisches Fachfeld und keine zweite Kompetenz- oder Beobachtungsprojektion ein.

## Sprint 7G.3 - Dokumentationsfilter der LEG-Kompetenzauswahl

Registrierte fluechtige ViewModel-Felder und Funktionen:

- `LearningConferenceCompetencyViewModel.observation_dates`
- `LearningConferenceCompetencyViewModel.has_current_confirmation`
- `LearningConferenceCompetencyViewModel.is_documented_in_period(period_start, period_end)`
- `_parse_evidence_date(value)`

Registrierte Leseparameter und UI-Rollen:

- `retained_competency_ids`
- `LearningConferenceCompetencyFilterNote`
- `LearningConferenceCompetencyEmpty_<subject_id>`
- `LearningConferenceDialog._update_competency_visibility(selected_subjects)`
- `LearningConferenceDialog._competency_filter_period()`
- `LearningConferenceDialog._optional_date_edit(value, accessible_name)`
- `LearningConferenceDialog._optional_date_value(edit)`

Regel: `observation_dates` enthaelt ausschliesslich Datumsreferenzen bereits kanonisch beruecksichtigter aktiver Kompetenzbeobachtungen des Kindes. `has_current_confirmation` bildet nur das Vorhandensein der bestehenden aktuellen Bestaetigung ab. Beide Werte steuern ausschliesslich die sichtbare LEG-Auswahl und berechnen keinen Kompetenzstatus. `retained_competency_ids` darf historische Draft-Referenzen in derselben kanonischen Projektion aufloesbar halten, veraendert aber deren Statuslogik und die Standardprojektion ohne diesen Parameter nicht.

## UI Sprint 6B - Phasenorientierter LEG-Workspace

Registrierte lokale UI-Kompositionen:

- `LearningConferencePhaseNavigation`
- `LearningConferencePhaseButton_<phase_key>`
- `LearningConferencePhaseWorkspace`
- `LearningConferencePhaseScroll`
- `LearningConferenceEvidenceSummary`
- `LearningConferenceActionBar`
- `LearningConferenceDirtyBadge`
- `LearningConferenceValidationMessage`
- `LearningConferenceCloseDialog`
- `LearningConferenceDraftSelectionDialog`
- `LearningConferenceDraftChoice_<learning_conference_draft_id>`

Registrierte reine Leseprojektionserweiterung:

- `LearningConferencePreparationViewModel.course_name`

Registrierte fluechtige UI-Schluessel:

- `goal`
- `strengths`
- `development`
- `goals`
- `evidence`
- `agreements`

Regel: Die sechs Schluessel strukturieren ausschliesslich den lokalen aktiven Phasen-, Fokus-, Scroll- und Dirty-State des bestehenden `LearningConferenceDialog`. `LearningConferencePhaseNavigation` und `LearningConferenceDraftSelectionDialog` sind lokale Qt-Kompositionen aus registrierten Basiskomponenten. Sie fuehren keine Datenquelle, fachliche Phase, Abschlusslogik, Persistenz, Repository-Verantwortung oder neue Feldbedeutung ein. `LearningConferencePreparationViewModel.course_name` reicht nur den bereits vorhandenen Kursnamen aus der Schuelerprojektion in den Kontextkopf weiter. `agreed_goals_text` bleibt unveraendert persistiert und wird nur sichtbar der Phase `goals` zugeordnet.

## Sprint 8A - Produktiver Stundenplan

Registrierte technische Felder und Werte:

- `timetable_entry_id`
- `weekday`
- `start_time`
- `end_time`
- `target_type`
- `target_id`
- `room`
- `deleted_at`
- `group`
- `course`
- `course_group`

Registrierte Python-Komponenten:

- `src/core/timetable.py`
- `src/application/commands/timetable.py`
- `src/desktop_app/adapters/timetable_desktop_adapter.py`
- `src/desktop_app/view_models/timetable_view_model.py`
- `src/desktop_app/dialogs/timetable_entry_dialog.py`
- `TimetableEntry`
- `TimetableOccurrence`
- `TimetableService`
- `TimetableValidator`
- `TimetableValidationError`
- `TimetableProjection`
- `TimetableRepository`
- `SQLiteTimetableRepository`
- `SaveTimetableEntryCommand`
- `TimetableApplicationService`
- `TimetableDesktopAdapter`
- `TimetableOptionViewModel`
- `TimetableEntryViewModel`
- `TimetableDayViewModel`
- `TimetableWeekViewModel`
- `TimetableOccurrenceViewModel`
- `TimetableReadProjectionViewModel`
- `TimetableEntryDialog`
- `build_timetable_projection(entries, at)`

Registrierte Adapter-, Repository- und UI-Einstiege:

- `SQLiteTimetableRepository.list_entries()`
- `SQLiteTimetableRepository.get_entry(timetable_entry_id)`
- `SQLiteTimetableRepository.create_entry(entry)`
- `SQLiteTimetableRepository.update_entry(entry)`
- `SQLiteTimetableRepository.next_timetable_entry_id()`
- `SQLiteTimetableRepository.next_sort_order(weekday)`
- `TimetableDesktopAdapter.week_view_model()`
- `TimetableDesktopAdapter.save_entry(command)`
- `TimetableDesktopAdapter.set_entry_active(timetable_entry_id, active)`
- `TimetableDesktopAdapter.delete_entry(timetable_entry_id)`
- `TimetableDesktopAdapter.read_projection(at)`
- `SettingsScreen.timetable_add_requested`
- `SettingsScreen.timetable_edit_requested`
- `SettingsScreen.timetable_delete_requested`
- `SettingsScreen.timetable_active_requested`
- `TimetableSettingsSection`
- `TimetableEmptyState`
- `TimetableDay_{weekday}`
- `TimetableEntry_{timetable_entry_id}`
- `TimetableAdd_{weekday}`
- `TimetableActive_{timetable_entry_id}`

Regel: `weekday` verwendet ISO-Wochentage 1 bis 5. Zeiten werden kanonisch als `HH:MM` gespeichert. `target_type` ist genau `group`, `course` oder `course_group`; `target_id` referenziert die dazu passende bestehende Stammdaten-ID. Die Projektion erhaelt den Auswertungszeitpunkt explizit und verwendet kein verborgenes `datetime.now()`.

## Sprint 8B - Stundenplanbasiertes Dashboard

Registrierte Python-Komponenten und ViewModels:

- `DashboardDocumentationCellViewModel`
- `DashboardDocumentationGroupViewModel`
- `DashboardDocumentationHeatmapViewModel`
- `DashboardLessonCard`
- `StudentDesktopAdapter.dashboard_documentation_heatmap()`
- `StudentDesktopAdapter.list_students(..., course_ids)`
- `OverviewScreen.set_dashboard(projection, heatmap, at, has_timetable_entries)`
- `OverviewScreen.timetable_target_selected`
- `OverviewScreen.timetable_observation_requested`
- `OverviewScreen.settings_timetable_requested`
- `AppShell.refresh_dashboard(at)`
- `AppShell.show_students_for_timetable_target(target_type, target_id)`
- `AppShell.prepare_timetable_observation(subject_id, subject_label, target_type, target_id, target_label)`
- `NewObservationDialog.prefill_subject_id`
- `NewObservationDialog.prefill_context`
- `AppShell.now_provider`
- `AppShell.dashboard_refresh_timer`

Registrierter temporaerer UI-State:

- `pending_observation_subject_id`
- `pending_observation_subject_label`
- `pending_observation_target_label`

Regel: Das Dashboard liest ausschliesslich kanonische Stundenplan-, Stammdaten- und Dokumentationsprojektionen. Der aktuelle Zeitpunkt wird am Shell-Rand explizit an `TimetableDesktopAdapter.read_projection(at)` und den Screen weitergereicht. Die Stundenplanaktion merkt Fach und sichtbaren Unterrichtskontext nur fluechtig bis zur Kindauswahl vor; sie erzeugt keine neue Beobachtungs- oder Stundenplandatenquelle.

## Sprint 8B.1 - Dashboard UX-Referenz

Registrierte UI-Komponenten und Navigation:

- `dashboard`
- `GroupOverviewScreen`
- `DashboardHeroIllustrationSpace`
- `DashboardTimeline`
- `DashboardHeatmapMatrix`
- `DashboardMatchingChildren`

Regel: `dashboard` ist ein eigener Hauptnavigationspunkt. Der bestehende technische Navigationsschluessel `overview` und seine Stammgruppen-/Kursverbunduebersicht bleiben getrennt erhalten. Sprint 8B.1 veraendert ausschliesslich Screen-Komposition, Groessenverhaeltnisse, Weissraum und Theme-Stile; Stundenplan-, Dokumentations-, Ziel- und Beobachtungsprojektionen bleiben unveraendert.

## Sprint 8B.2 - Dashboard ohne allgemeine Uebersichtsbereiche

Regel: Der Dashboard-Screen endet nach `DashboardMatchingChildren`. Allgemeine Stammgruppen-, Kursverbund- und sonstige Schnellzugriffskarten gehoeren ausschliesslich zu `GroupOverviewScreen` unter dem getrennten Navigationspunkt `overview`. Das Dashboard besitzt dafuer keine Layouts, Signale oder Stammdatenbefuellung.

## Sprint 8B.3 - Passende Kinder als Dokumentationshilfe

Registrierte Projektion und UI-Einstiege:

- `DashboardSuggestedStudentViewModel`
- `StudentDesktopAdapter.list_dashboard_suggested_students(target_type, target_id, subject_id, subject_label, at, limit)`
- `OverviewScreen.timetable_student_observation_requested`
- `AppShell.open_dashboard_observation(student_id, subject_id, subject_label, target_label)`
- `DashboardMatchingChildRow`

Regel: Die Projektion verwendet ausschliesslich aktive Zielmitglieder und aktive Beobachtungen mit eindeutigem Bezug zum Stundenfach. Sie erhaelt `at` explizit, begrenzt auf hoechstens fuenf Kinder und sortiert ohne Ratings, Kompetenzstatus oder Scores: keine Fachbeobachtung zuerst, danach letzte Fachbeobachtung aufsteigend, heutige Fachbeobachtung zuletzt und bei Gleichstand sichtbarer Name alphabetisch plus stabile `student_id`.

## UI Sprint 1 - Product Shell und Interaction Foundations

Registrierte Dateien und Assets:

- `src/desktop_app/components.py`
- `src/desktop_app/icons.py`
- `src/desktop_app/screens/students_workspace.py`
- `assets/icons/today.svg`
- `assets/icons/students.svg`
- `assets/icons/master-data.svg`
- `assets/icons/settings.svg`
- `assets/icons/info.svg`
- `assets/icons/search.svg`
- `assets/icons/close.svg`
- `assets/icons/chevron-down.svg`

Registrierte Komponenten und Helfer (Component Library V1 und V2):

- `AppCard`
- `AppCard.set_selected(selected)`
- `AppCard.set_pressed(pressed)`
- `SectionHeader`
- `SectionHeader.add_action(action)`
- `FilterBar`
- `FilterBar.reset_requested`
- `FilterBar.set_context_filter(label, active)`
- `FilterBar.add_filter_widget(widget)`
- `FilterChip`
- `FilterChip.remove_requested`
- `FilterChip.set_label(label)`
- `IconButton`
- `PageHeader`
- `SegmentedControl`
- `SegmentedControl.selection_changed`
- `SearchField`
- `SearchField.find_shortcut`
- `StatusBadge`
- `StatusBadge.setText(text)`
- `InlineMessage`
- `EmptyState`
- `EmptyState._update_accessibility()`
- `Toast`
- `Toast.show_message(text, tone, duration_ms)`
- `configure_button(button, role, accessible_name)`
- `set_button_role(button, role)`
- `StudentsWorkspace`
- `StudentsWorkspace.courses_screen`
- `StudentsWorkspace.new_student_requested`
- `StudentsWorkspace.all_students_requested`
- `StudentsWorkspace.course_selected`
- `StudentsWorkspace.set_master_data(view_model, group_summaries)`
- `StudentsWorkspace.show_section(key)`
- `StudentsWorkspace.show_student_list(source_key)`
- `StudentsWorkspace.show_source_selection()`
- `StudentsWorkspace.list_source_key()`
- `StudentsWorkspace.current_content_key()`
- `STUDENT_WORKSPACE_SEGMENTS`
- `AppShell.show_all_students()`
- `AppShell.show_students_for_course(course_id)`
- `GroupOverviewScreen.direct_course_selected`
- `ICON_NAMES`
- `ICON_SIZE_SMALL`
- `ICON_SIZE_MEDIUM`
- `ICON_SIZE_LARGE`
- `icon_path(name)`
- `load_icon(name)`

Registrierte Theme-Tokens:

- `SPACING_4`, `SPACING_8`, `SPACING_12`, `SPACING_16`, `SPACING_24`, `SPACING_32`, `SPACING_48`
- `RADIUS_SMALL`, `RADIUS_MEDIUM`, `RADIUS_LARGE`, `RADIUS_XLARGE`
- `ELEVATION_FLAT`, `ELEVATION_CARD`, `ELEVATION_OVERLAY`
- `MOTION_FAST_MS`, `MOTION_STANDARD_MS`, `MOTION_SLOW_MS`
- `TYPOGRAPHY_STYLES`
- `COLOR_SUCCESS`, `COLOR_WARNING`, `COLOR_INFO`, `COLOR_FOCUS`

Erweiterte Felder von `NavigationItem`:

- `section`
- `icon_name`

Regel: Der sichtbare Navigationsname des bestehenden technischen Schluessels `dashboard` lautet `Heute`. Globale produktive Ziele sind ausschliesslich `dashboard`, `students`, `master_data` und `settings`, gruppiert in `ARBEIT` und `VERWALTUNG`. Der fruehere Schluessel `overview` wird nicht mehr global aufgeloest; `GroupOverviewScreen` bleibt als bestehende reine Projektion innerhalb von `StudentsWorkspace` erhalten. `PlaceholderScreen` bleibt als registriertes Modul historisch verfuegbar, ist aber kein Product-Shell-Ziel.

Regel: `StudentsWorkspace` komponiert die lokalen Segmente `groups`, `courses`, `course_groups` und `all` nur aus vorhandenen Adapter-/ViewModel-Projektionen und lokalem UI-State. Es fuehrt weder eine Datenquelle noch Businesslogik, SQLite-Zugriff, Persistenz oder einen Schreibprozess ein. Die direkte Kursansicht uebergibt eine vorhandene `course_id` an `StudentDesktopAdapter.list_students(course_id=...)`. Beobachtungs-, Kompetenz-, Berichts- und LEG-Pfade bleiben ueber das bestehende Schuelerprofil erreichbar.

## Premium UI Sprint 2 - Dialog Experience und Workspace Polish

Registrierte UI-Komponenten und Objektrollen:

- `DialogHeader`
- `DialogHeader.add_action(action)`
- `DialogActionBar`
- `ObservationDialogZone.zoneRole`
- `zoneRole = context`
- `zoneRole = primary`
- `zoneRole = entry`
- `LearningReportDialog.reject()`

Registrierte Dialogicons:

- `assets/icons/student-record.svg`
- `assets/icons/master-data-dialog.svg`
- `assets/icons/timetable-dialog.svg`
- `assets/icons/observation.svg`
- `assets/icons/report.svg`
- `assets/icons/conference.svg`

Regel: `DialogHeader`, `DialogActionBar` und `zoneRole` strukturieren ausschliesslich visuelle Hierarchie, Kontext, Fokusreihenfolge und lokale Surface-Gewichtung vorhandener Dialoge. `LearningReportDialog.reject()` bestaetigt nur das Verwerfen eines bereits lokal erkannten Dirty-State. Diese Namen besitzen keine Datenquelle, erzeugen keine Fachlogik und veraendern weder Adapter-, ViewModel-, Repository-, SQLite-, Navigations- noch Speicherpfade.

## UI Sprint 3 - Motion System und Microinteractions

Registrierte Datei:

- `src/desktop_app/motion.py`

Registrierte Motion-Namen:

- `MotionPolicy`
- `motion_policy`
- `set_reduced_motion(enabled)`
- `reduced_motion_enabled()`
- `motion_duration(duration_ms)`
- `animate_value(owner, key, start_value, end_value, update, duration_ms, easing)`
- `animate_opacity(widget, visible, duration_ms, key)`
- `animate_feedback(widget, key, duration_ms)`
- `install_card_motion(card)`
- `stop_motion(owner, key)`

Regel: Motion ist ausschliesslich lokaler, fluechtiger UI-State. Animationen setzen keine fachlichen Zustaende, besitzen keine Datenquelle und duerfen Signale, Navigation, Filter oder Schreibprozesse nicht verzoegern. Pro Widget und semantischem Schluessel existiert hoechstens eine laufende Animation; Reduced Motion setzt denselben Endzustand ohne Bewegung.

## UI Sprint 4 - Schuelerprofil und Beobachtungs-Workspace

Registrierte Profilnamen:

- `StudentProfilePageHeader`
- `StudentProfileHeaderSurface`
- `StudentProfilePrimaryAction`
- `StudentProfileMoreActions`
- `StudentProfileNavigation`
- `StudentProfileTabs`
- `DocumentationRing`
- `StudentProfileAvatar`
- `StudentProfileContextBadge`
- `StudentProfileHeaderDocumentation`
- `StudentProfileDocumentationRing`
- `StudentProfileOverviewCards`
- `StudentProfileOrientationCard`
- `StudentProfileOrientationChange`
- `StudentProfileOrientationStatusChange`
- `StudentProfileOrientationEvidence`
- `StudentProfileDevelopmentStatusBadge`
- `StudentProfileDevelopmentArrow`
- `StudentProfileEvidenceBadge`
- `StudentProfileHistoricalBadge`
- `StudentProfileCompetencySummaryCard`
- `StudentProfileUndocumentedCard`
- `StudentProfileEyebrow`
- `StudentProfileDocumentationMetric`
- `StudentProfileDashboardSummaryRow`
- `StudentProfileOpenCompetencyCockpit`
- `StudentProfileOpenUndocumented`
- `CompetencyCockpitSearch`
- `CompetencyCockpitStageFilter`
- `StudentProfileScreen._select_profile_section(key)`
- `StudentProfileScreen._sync_profile_navigation(index)`
- `StudentProfileScreen._update_profile_header_context()`
- `StudentProfileScreen._apply_overview_card_layout(compact)`
- `StudentProfileScreen._orientation_change_row(change)`
- `StudentProfileScreen._orientation_status_row(label, rating, status_label)`
- `StudentProfileScreen._orientation_evidence_excerpt(event)`
- `StudentProfileScreen._open_undocumented_competencies()`
- `StudentProfileScreen._matches_competency_learning_stage(competency, learning_stage_filter)`
- `StudentProfileScreen._matches_competency_search(competency, learning_area, topic, search_text)`

Registrierte Dialognamen:

- `OBSERVATION_STAGE_FILTERS`
- `ObservationDialogPageHeader`
- `ObservationLearningStageFilter`
- `ObservationValidationMessage`
- `ObservationFileRow`
- `NewObservationDialog._catalog_stage_filter_key`
- `NewObservationDialog._change_catalog_stage_filter(filter_key)`
- `NewObservationDialog._matches_catalog_learning_stage(competency)`

Regel: Beide Klassenstufenfilter lesen ausschliesslich das bestehende Katalogfeld `learning_stage`. `matching` zeigt `stage_1_3` und `cross_stage`, `stage_4` zeigt `stage_4` und `cross_stage`, `all` zeigt alle aktiven aktuellen Katalogzeilen. Filterung bleibt lokaler UI-State und erzeugt keine neue Datenquelle, Berechnung oder Persistenz. Initial ausgewaehlte Edit-Kompetenzen bleiben unabhaengig vom Filter sichtbar und geoeffnet; historische beziehungsweise inaktive Kompetenzen werden nie als neue Auswahl reaktiviert.

## LEG-Abschluss und Revision

Registrierte Domainnamen:

- `LearningConferenceRecord` (`LCF`)
- `LearningConferenceRevisionRecord` (`LCV`)
- `LearningConferenceCompletionSource`
- `LearningConferenceCompletionResult`
- `LearningConferenceCompletionError`
- `LearningConferenceSnapshotBuilder`
- `LearningConferenceCompletionService`
- `LearningConferenceRevisionReadService`

Registrierte Application- und Persistenznamen:

- `LearningConferenceCompletionApplicationService`
- `LearningConferenceRevisionApplicationService`
- `SQLiteLearningConferenceRepository`
- `learning_conferences`
- `learning_conference_revisions`

Registrierte UI-/Projektionsnamen:

- `LearningConferenceRevisionStatusViewModel`
- `LearningConferenceRevisionListItemViewModel`
- `LearningConferenceRevisionViewModel`
- `LearningConferenceCompletionErrorViewModel`
- `LearningConferenceRevisionDialog`

Registrierte IDs und Statuswerte:

- `learning_conference_id` mit Praefix `LCF-`
- `learning_conference_revision_id` mit Praefix `LCV-`
- LCV-Status `completed`
- LCV-Status `superseded`
- `snapshot_schema_version`
- `snapshot_json`
- `snapshot_sha256`

Begriffsregel:

- `Abschluss` ist der explizite, validierte und atomare Schreibbefehl vom LCD zum LCF/LCV.
- `Revision` bezeichnet ausschliesslich eine unveraenderliche LCV; der LCD bleibt ein Draft.
- `Snapshotvertrag` bezeichnet die LEG-spezifische kanonische JSON-Struktur und ist keine gemeinsame Bericht-/LEG-Domain.

## Sprint 10B - Finales LEG-PDF aus abgeschlossener Revision

Registrierte Python-Module:

- `src/core/learning_conference_pdf.py`
- `tests/test_learning_conference_pdf.py`

Registrierte Klassen, Protokolle und Commands:

- `LearningConferencePdfArtifactRecord`
- `LearningConferencePdfArtifactRepository`
- `LearningConferencePdfSnapshotValidator`
- `LearningConferencePdfOutputModelBuilder`
- `LearningConferencePdfService`
- `LearningConferencePdfError`
- `GenerateLearningConferencePdfCommand`
- `LearningConferencePdfApplicationService`
- `SQLiteLearningConferencePdfArtifactRepository`
- `LearningConferencePdfArtifactViewModel`

Registrierte Konstanten und Werte:

- `LEARNING_CONFERENCE_PDF_ARTIFACT_ID_PREFIX` mit Wert `LCA`
- MIME-Type `application/pdf`

Registrierte technische Felder und Adapteroperationen:

- `learning_conference_pdf_artifact_id`
- `relative_file_path`
- `mime_type`
- `file_size_bytes`
- `pdf_sha256`
- `StudentDesktopAdapter.generate_learning_conference_pdf(learning_conference_revision_id)`
- `StudentDesktopAdapter.load_learning_conference_pdf_artifact(learning_conference_revision_id)`

Registrierte Qt-Objektnamen:

- `LearningConferenceGenerateFinalPdfButton`
- `LearningConferenceFinalPdfStatus`

Regel: `LCA` identifiziert genau eine unveraenderliche PDF-Artefaktreferenz fuer eine `LCV`. Pro `learning_conference_revision_id` existiert hoechstens eine `LCA`. Neue Erzeugung ist nur fuer Status `completed` erlaubt. `relative_file_path` liegt relativ zur produktiven SQLite-Datei innerhalb `documents/<student_id>/learning_conferences/<LCF>/<LCV>/`; der Dateiname enthaelt keinen Schuelerklartext. `pdf_sha256` ist der kleingeschriebene SHA-256-Hexdigest der PDF-Bytes. Die renderer-neutrale PDF-Projektion ist keine Berichtsdomain und liest ausschliesslich den verifizierten LCV-Snapshot.
