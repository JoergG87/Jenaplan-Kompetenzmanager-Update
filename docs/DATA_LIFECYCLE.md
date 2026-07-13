# Data Lifecycle

Dieses Dokument beschreibt freigegebene oder geplante Schreibprozesse fuer fachliche Daten.

Kein Schreibprozess darf implementiert werden, bevor sein Lebenszyklus hier dokumentiert ist.

## Dokumentationsrelevante Faecher speichern

Start: Laura legt in den Einstellungen fest, welche Faecher fuer spaetere Dokumentations- und Auswertungslogik zaehlen sollen.

Schreibprozess: Dokumentationskonfiguration ueber Settings-UI, Desktop Adapter und SQLite-Repository. Ab Sprint 2C wird die Auswahl lesend in Dokumentationsauswertungen angewendet.

Freigegebener PySide-Pfad:

```text
PySide6 SettingsScreen
-> StudentDesktopAdapter
-> SQLiteDocumentationSubjectSettingsRepository
-> SQLite documentation_subject_settings
```

Betroffene Datenquellen:

- `documentation_subject_settings` in SQLite als Source of Truth fuer die Auswahl dokumentationsrelevanter Faecher
- `competencies` nur lesend fuer das Default-Verhalten und die vorhandenen Fachschluessel

Erforderliche IDs:

- bestehender `subject_id`

Automatisch profitierende Ansichten:

- Schuelerlisten-Dokumentationsstatus
- Schuelerprofil-Dokumentationsstand
- offene Kompetenzen / Beobachtungsanlaesse
- Beobachtungshinweise im Halbjahresblick
- Berichtsvorbereitung, falls sie Dokumentationsstatus oder offene Kompetenzen nutzt

Regel: Die Speicherung ersetzt die vollstaendige Auswahl in `documentation_subject_settings`. Wenn keine Settings-Zeilen vorhanden sind, bleibt das bisherige Verhalten erhalten: alle aktiven Katalogfaecher aus `competencies.active = 1` gelten als dokumentationsrelevant. Die Einstellung loescht keine Beobachtungen, veraendert keine Kompetenzdefinitionen und nutzt `competencies.active` nicht als Einstellungsfeld. Nicht dokumentationsrelevante Faecher bleiben in Beobachtungslisten, Kompetenzhistorien und bestaetigten Kompetenzstaenden sichtbar, zaehlen aber nicht als offen im Dokumentationsstand oder in offenen Beobachtungsanlaessen.

## Stundenplaneintrag pflegen

Start: Laura legt in den Einstellungen einen Stundenplaneintrag an, bearbeitet, aktiviert, deaktiviert oder loescht ihn.

Freigegebener PySide-Pfad:

```text
PySide6 SettingsScreen / TimetableEntryDialog
-> TimetableDesktopAdapter
-> TimetableApplicationService
-> TimetableService / TimetableValidator
-> SQLiteTimetableRepository
-> SQLite timetable_entries
```

Betroffene Datenquellen:

- SQLite `timetable_entries` schreibend
- SQLite `competencies` lesend zur Aufloesung und Validierung vorhandener `subject_id`
- SQLite `groups`, `courses` und `course_groups` lesend zur zielartgerechten Validierung von `target_id`

Erforderliche IDs:

- neue oder bestehende `timetable_entry_id`
- bestehende `subject_id`
- bestehende, zu `target_type` passende `target_id`

Regel: Anlegen und Aendern validieren Zeitbereich, Referenzen und aktive Ueberschneidungen vor dem Schreiben. Aktivieren durchlaeuft dieselben Regeln. Loeschen markiert nur den ausdruecklich gewaehlten Stundenplaneintrag mit `deleted_at` und deaktiviert ihn; bestehende Stammdaten und Stundenplan-IDs bleiben unveraendert und geloeschte IDs werden nicht wiederverwendet. Die Leseprojektion speichert nichts und berechnet aktuelle, naechste und heutige Stunden ausschliesslich aus aktiven, nicht geloeschten Eintraegen und einem explizit uebergebenen Zeitpunkt.

## Schueler anlegen

Start: Lehrkraft oder Verwaltung legt einen neuen Schueler an.

Schreibprozess: Schuelerverwaltung, spaeter freizugeben.

Primaerer UI-Einstieg: PySide-Dialog `Neuer Schüler`.

Status: Produktiver Schreibpfad bis SQLite ist ueber den PySide-Adapter umgesetzt. Beim produktiven App-Start werden Schema, Stammdaten und Kursverbund-Defaults initialisiert, aber keine Demo-Schueler erzeugt. Excel-Projection-Refresh ist archivierter Legacy-Altstand und kein Zielpfad fuer neue UI-Funktionalitaet.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Legacy-Excel-Pfad:

Der fruehere Feature-1.4-Pfad ueber `dlg_neuer_schueler`, VBA Adapter und Python CLI/Bridge bleibt als historischer Architekturstand dokumentiert. Er wird nicht fuer neue Features, UI oder Smoke-Tests weiterverfolgt.

Nach erfolgreichem `student.create` wird die PySide-Ansicht aus SQLite aktualisiert. Ein spaeterer Datei- oder Excel-Export braucht einen separaten freigegebenen Exportprozess.

Die GUI sammelt Eingaben und erzeugt Commands, enthaelt aber keine Businesslogik und schreibt nicht direkt aus Widgets in SQLite.

Der Excel/VBA-Runtime-Adapter wird nicht weiter ausgebaut. Excel liegt nur noch als historischer Altstand unter `legacy/excel/`.

Betroffene Datenquellen:

- `students` in SQLite als fachliche Source of Truth
- `data_students` als historische Excel-/Exportprojektion
- spaeter optional `data_media` fuer Schuelerdokumente

Erforderliche IDs:

- neuer `student_id`
- bestehender `group_id`
- bestehender `course_id`
- optional neue `media_id` je Dokument

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Beobachtungsdialog
- Berichte

Regel: Neue Stammgruppen oder Kurse werden dabei nicht automatisch angelegt. `student_id`, `group_id` und `course_id` bleiben die technische Zuordnung; sichtbare Namen werden aus den persistenten Stammdaten aufgeloest. Optionale Dokumente werden erst nach erfolgreicher Erzeugung der `student_id` referenziert. Dateien werden nicht in Excel eingebettet. Bei Fehlern bleibt der PySide-Dialog geoeffnet und SQLite unveraendert. Demo-/Seed-Schueler duerfen nur ueber explizite Test- oder Legacy-Seed-Pfade erzeugt werden und ueberschreiben keine produktiven Nutzerdaten.

## Dokument oder Medium hinzufuegen

Start: Lehrkraft fuegt im Schuelerprofil oder Beobachtungsdialog eine Datei hinzu oder entfernt eine Datei aus dem Schuelerprofil.

Schreibprozess: Dokumenten- und Medien-MVP ueber PySide.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> StudentDesktopAdapter
-> Dateiablage data/documents/<student_id>/
-> SQLiteDocumentRepository
-> SQLite documents
```

Betroffene Datenquellen:

- SQLite `documents` als fachliche Source of Truth fuer Metadaten
- Dateisystem `data/documents/<student_id>/` fuer physische Dateien
- optional `observations`, wenn die Datei als Beobachtungsanhang verknuepft wird

Erforderliche IDs:

- bestehender `student_id`
- optional bestehender `observation_id`
- neuer `document_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Beobachtungsdetails
- spaeter Berichte und Exporte

Regel: SQLite speichert nur Metadaten und keine Datei-BLOBs. Die Datei wird in den App-Datenordner kopiert und studentenzentriert abgelegt. Ein Beobachtungsanhang gehoert weiterhin zum Schueler und traegt nur zusaetzlich den optionalen Beobachtungsbezug. Entfernen ist ein Soft Delete ueber `documents.active = 0`; die physische Datei wird in diesem MVP nicht automatisch geloescht.

## Schueler archivieren

Start: Schueler soll nicht mehr aktiv in Ansichten erscheinen.

Schreibprozess: Schuelerverwaltung, spaeter freizugeben.

Betroffene Datenquellen:

- `data_students`

Erforderliche IDs:

- `student_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Berichte
- Dashboards

Regel: Archivierung setzt `active = FALSE` und `archived_at` auf einen Zeitstempel. Historische Daten bleiben vollständig erhalten. Beobachtungen bleiben über `student_id` gültig.

## Schueler aendern

Start: Stammdaten oder Zuordnungen eines bestehenden Schuelers werden korrigiert.

Schreibprozess: Schuelerverwaltung, spaeter freizugeben.

Betroffene Datenquellen:

- `data_students`

Erforderliche IDs:

- bestehender `student_id`
- gueltiger `group_id`
- gueltiger `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte
- Dashboards

Regel: `student_id` bleibt erhalten. Historische Beobachtungen bleiben ueber `student_id` gueltig. UI-Projektionen aktualisieren sich aus `data_students`.

## Stammgruppe anlegen

Start: Neue organisatorische Stammgruppe wird benoetigt.

Schreibprozess: Stammgruppenverwaltung ueber PySide-Stammdaten.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> MasterDataDesktopAdapter
-> SQLiteMasterDataRepository
-> SQLite groups
```

Betroffene Datenquellen:

- `groups` in SQLite als fachliche Source of Truth
- `data_groups` als historische Excel-/Exportprojektion

Erforderliche IDs:

- neuer `group_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Schuelerverwaltung

Regel: Schueler werden erst durch `students.group_id` einer Stammgruppe zugeordnet. Neue Stammgruppen werden dem Default-Kursverbund hinzugefuegt, damit sie in der kursverbundbezogenen Uebersicht sichtbar bleiben.

## Stammgruppe aendern

Start: Name oder Status einer bestehenden Stammgruppe wird angepasst.

Schreibprozess: Stammgruppenverwaltung ueber PySide-Stammdaten.

Betroffene Datenquellen:

- `groups` in SQLite als fachliche Source of Truth
- `data_groups` als historische Excel-/Exportprojektion

Erforderliche IDs:

- bestehender `group_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `group_id` bleibt erhalten. Schuelerreferenzen bleiben gueltig. Umbenennen schreibt nur den Namen und loest keine Schueler-Umbuchung aus.

## Kurs anlegen

Start: Neuer Kurs/Jahrgang wird benoetigt.

Schreibprozess: Kursverwaltung ueber PySide-Stammdaten.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> MasterDataDesktopAdapter
-> SQLiteMasterDataRepository
-> SQLite courses
```

Betroffene Datenquellen:

- `courses` in SQLite als fachliche Source of Truth
- `data_courses` als historische Excel-/Exportprojektion

Erforderliche IDs:

- neuer `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: Kursfarbe wird mit Name und Hex-Wert am Kurs gespeichert und nicht an einzelnen Schuelern. Neue Kurse werden dem Default-Kursverbund hinzugefuegt, damit sie in der kursverbundbezogenen Uebersicht sichtbar bleiben.

## Kurs aendern

Start: Name, Farbe oder Status eines bestehenden Kurses wird angepasst.

Schreibprozess: Kursverwaltung ueber PySide-Stammdaten.

Betroffene Datenquellen:

- `courses` in SQLite als fachliche Source of Truth
- `data_courses` als historische Excel-/Exportprojektion

Erforderliche IDs:

- bestehender `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `course_id` bleibt erhalten. Schuelerkartenfarbe aktualisiert sich aus `course_id` und `courses.color_hex`.

## Kursverbund anlegen oder aendern

Start: Ein kursverbundbezogener Mathe-/Deutsch-Scope wird angelegt oder bearbeitet.

Schreibprozess: Kursverbundverwaltung ueber PySide-Stammdaten.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> MasterDataDesktopAdapter
-> SQLiteMasterDataRepository
-> SQLite course_groups
-> SQLite course_group_student_groups
-> SQLite course_group_courses
```

Betroffene Datenquellen:

- `course_groups`
- `course_group_student_groups`
- `course_group_courses`

Erforderliche IDs:

- bestehender oder neuer `course_group_id`
- mindestens ein bestehender `group_id`
- mindestens ein bestehender `course_id`

Automatisch profitierende Ansichten:

- PySide-Uebersicht `Stammgruppen und Schülerbestand`
- Schuelerliste mit Kursverbund-/Kursfilter
- Stammdaten-Seite

Regel: Name, Stammgruppen- und Kurszuordnung werden atomar gespeichert. Neue Kursverbuende erhalten eine stabile `course_group_id`. Doppelte Kursverbundnamen werden vor dem Speichern abgefangen. Die Relationstabellen werden beim Speichern vollstaendig fuer den Kursverbund ersetzt. Es werden keine Schueler umgebucht und keine Beobachtungsdaten veraendert.

## Stammdaten-Defaults initialisieren

Start: SQLite-Datenbank wird ohne vorhandene Stammgruppen oder Kurse geoeffnet.

Schreibprozess: Initialisierung ueber `SQLiteDatabase.ensure_master_data_defaults()`.

Betroffene Datenquellen:

- `groups`
- `courses`
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`

Regel: Defaults fuer Stammgruppen, Kurse und `Mathe/Deutsch Kursverbund A` werden nur erzeugt, wenn der jeweilige Stammdaten-Scope leer ist. Bestehende produktive Stammdaten werden nicht ueberschrieben.

## Beobachtung erfassen

Start: Lehrkraft dokumentiert eine Beobachtung zu einem Schueler.

Schreibprozess: PySide-Beobachtungsdialog ueber `StudentDesktopAdapter`, `observation.create`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`
- SQLite `documentation_subject_settings` nur lesend fuer die Fachauswahl
- Export-/Legacy-Projektionen `data_observations` und `data_observation_competencies`
- spaeter optional `data_media`

Erforderliche IDs:

- neuer `observation_id`
- bestehender `student_id`
- bestehender oder aus dem v1-Katalog abgeleiteter `competency_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzansicht
- Berichte
- Dashboards

Regel: Beobachtung ist Source of Truth. Auswertungen leiten sich daraus ab. Die Schnellauswahl im Beobachtungsdialog ist eine nicht schreibende Adapterprojektion aus bereits aktiven Beobachtungen und ihren Kompetenzbewertungen: nur aktive `current`-Kompetenzen, je Schueler und Fach maximal vier eindeutige Eintraege, neueste zuerst. Sie erzeugt keine Tabelle, keine Historie und keine zusaetzliche Persistenz und wird nach erfolgreichem Speichern neu abgeleitet.
Neue Beobachtungen koennen nur mit dokumentationsrelevanten aktiven Faechern aus der aktuellen Settings-Auswahl angelegt werden; ohne Settings-Zeilen gilt der aktive Katalog. Die Kompetenzauswahl bietet dabei ausschliesslich aktive `current`-Kompetenzen an. Beobachtung und Kompetenzbewertungen werden atomar gespeichert; eine Bewertung gehoert zur konkreten Kompetenz, nicht global zur Beobachtung. Die sichtbare Struktur lautet Fach -> Kompetenzbereich -> Thema -> Kompetenz und wird ueber vorhandene Felder abgebildet: `subject_id` / `subject_name`, `learning_area`, `competency_group`, `description` / `competency_text`. `offen` ist kein gespeicherter Ratingwert; eine nicht bewertete Kompetenz erzeugt keine Zeile in `observation_competency_ratings`. Eine bewusst aktivierte Schnellbeobachtung darf ohne Kompetenzbewertungen gespeichert werden, wenn `note` nach dem Trimmen nicht leer ist. Sie erzeugt keine Zeile in `observation_competency_ratings` und wirkt deshalb nicht auf kompetenzbezogene Projektionen. Medien/Anhaenge und Berichte bleiben im bestehenden separaten Prozess.

## Beobachtung aendern

Start: Lehrkraft korrigiert eine bestehende Beobachtung im Schuelerprofil.

Schreibprozess: PySide-Schuelerprofil oeffnet den Beobachtungsdialog mit `observation_id`; Speichern laeuft ueber `StudentDesktopAdapter`, `observation.update`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`
- SQLite `documentation_subject_settings` nur lesend fuer die Fachauswahl
- Export-/Legacy-Projektionen `data_observations` und `data_observation_competencies`

Erforderliche IDs:

- bestehender `observation_id`
- bestehender `student_id`
- bestehende `competency_id` je Bewertung

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzuebersicht
- Kompetenzansicht
- Berichte

Regel: `observation_id` bleibt erhalten. Beobachtungsfelder werden aktualisiert; Kompetenzbewertungen werden fuer die Beobachtung atomar ersetzt. Die Fachanzeige wird weiter aus den Kompetenzfaechern abgeleitet. Wenn das gespeicherte Fach inzwischen nicht dokumentationsrelevant ist, bleibt es beim Bearbeiten sichtbar und wird nicht automatisch ersetzt oder entfernt. Bereits bewertete `legacy`- oder inaktive Kompetenzen bleiben mit ihrer gespeicherten `competency_id`, Hierarchie, ihrem Text und Rating sichtbar, bewertbar und entfernbar; es erfolgt keine Ersetzung oder Migration. Eine Bewertung wird nur gespeichert, wenn eine konkrete Kompetenz in dieser Beobachtung bewertet wird; `offen` wird nicht als eigener Ratingwert gespeichert. Eine gespeicherte Schnellbeobachtung wird beim Bearbeiten aus nichtleerer Notiz und fehlenden Kompetenzbewertungen erkannt. Kompetenzen koennen spaeter ergaenzt werden; dann wird der Schnellbeobachtungsmodus beendet und die normale Bewertungsvalidierung gilt. Werden alle Kompetenzen einer normalen Beobachtung entfernt, ist Speichern nur nach bewusster Aktivierung des Schnellbeobachtungsmodus und mit nichtleerer Notiz erlaubt.

## Beobachtung loeschen

Start: Lehrkraft blendet eine fehlerhafte Beobachtung aus dem Schuelerprofil aus.

Schreibprozess: PySide-Schuelerprofil sendet `observation_id`; Loeschen laeuft ueber `StudentDesktopAdapter`, `observation.delete`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`

Erforderliche IDs:

- bestehender `observation_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzuebersicht
- Kompetenzansicht
- Berichte

Regel: Loeschen ist ein Soft Delete und setzt `observations.active = 0`. Rating-Zuordnungen bleiben historisch erhalten, aktive Profil- und Kompetenzuebersichten lesen nur aktive Beobachtungen.

## Kompetenzstand bestaetigen

Start: Lehrkraft uebernimmt oder aendert im Schuelerprofil den berechneten Kompetenzstand-Vorschlag.

Schreibprozess: PySide-Schuelerprofil sendet `student_id`, `competency_id` und `confirmed_rating`; Speichern laeuft ueber `StudentDesktopAdapter`, `SQLiteStudentCompetencyConfirmationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `student_competency_confirmations`

Erforderliche IDs:

- bestehender `student_id`
- bestehender `competency_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzuebersicht
- Berichtsvorschau

Regel: Der bestaetigte Kompetenzstand ist eine paedagogische Entscheidung der Lehrkraft. Er ueberschreibt keine Beobachtungen und veraendert den berechneten Vorschlag nicht. Neue Beobachtungen aktualisieren den Vorschlag, aber nicht automatisch den bestaetigten Stand.

## Kompetenz ergaenzen

Start: Fachliche Kompetenzstruktur wird erweitert.

Schreibprozess: Fachliche Konfiguration, spaeter freizugeben.

Betroffene Datenquellen:

- `data_competencies`
- optional `data_subjects`

Erforderliche IDs:

- neuer `competency_id`
- bestehender oder neuer `subject_id`
- optional `parent_competency_id`

Automatisch profitierende Ansichten:

- Beobachtungsdialog
- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Regel: Kompetenzstruktur wird nicht aus Beobachtungstexten abgeleitet. Sprint 3A fuehrt keine neuen DB-Felder wie `competency_area` oder `topic` ein. Die vorhandenen Felder werden fachlich gemappt: Fach = `subject_id` / `subject_name`, Kompetenzbereich = `learning_area`, Thema = `competency_group`, konkrete Kompetenz = `description` / `competency_text`, Kurzlabel = `label`. Sprint 3B ergaenzt konkrete Arbeitskatalog-Kompetenzen ueber neue stabile `competency_id`s und nutzt die optionale CSV-Spalte `competency_label` zur Befuellung des bestehenden SQLite-Feldes `label`.

## Kompetenzkatalog importieren oder aktualisieren

Start: PySide-App oeffnet eine SQLite-Datenbank ohne vorhandene Kompetenzen oder mit einem aelteren lokalen Kompetenzkatalog.

Schreibprozess: Idempotenter Katalogimport ueber `StudentDesktopAdapter`, `CurriculumDesktopAdapter` und `SQLiteCompetencyRepository.ensure_catalog_defaults()`.

Freigegebener PySide-/SQLite-Pfad:

```text
data/curriculum_catalog_v1.csv
-> CurriculumDesktopAdapter
-> SQLiteCompetencyRepository
-> SQLite competencies
```

Betroffene Datenquellen:

- `data/curriculum_catalog_v1.csv` als Seed-Quelle
- SQLite `competencies`
- Export-/Legacy-Projektion `data_competencies`

Erforderliche IDs:

- bestehende `competency_id` aus dem Katalog
- bestehende `subject_id` / `subject_key` aus dem Katalog

Automatisch profitierende Ansichten:

- Beobachtungsdialog
- Schuelerprofil
- Kompetenzansicht
- Dokumentationsstand
- Berichte und Dashboard, sobald sie die neuen Katalogmetadaten nutzen

Regel: Der Import ist ab Sprint 3B ein idempotenter Upsert. Bei leerer Tabelle wird der vollstaendige CSV-Katalog importiert. Bei bestehenden lokalen Datenbanken werden neue CSV-IDs eingefuegt und vorhandene CSV-IDs aktualisiert, ohne lokale Nicht-CSV-Kompetenzen zu loeschen. Sprint 4A aktualisiert dabei auch `grade_band`, `learning_stage`, `catalog_status`, `catalog_default_active` und `activation_group_key`. `competencies.active` vorhandener IDs wird nicht aus dem CSV ueberschrieben, damit alte grobe oder lokal deaktivierte Kompetenzen nicht ungefragt reaktiviert oder deaktiviert werden. `catalog_default_active` speichert nur den Katalogstandard. Kompetenzstaende werden weiterhin aus Beobachtungen abgeleitet und nicht manuell doppelt gespeichert. Alte grobe Kompetenzen bleiben historisch lesbar und bestehende `observation_competency_ratings` werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Fehlen Sprint-4A-Spalten in alten CSV-Dateien, setzt der Parser sichere Defaults: `learning_stage = cross_stage`, `catalog_status = current`, `activation_group_key = ''` und `catalog_default_active` aus dem alten `is_active`. Die Sprint-4-Lehrplanuebernahmen fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz sind abgeschlossen; Religion blieb ausserhalb dieses Katalogabgleichs.

## Kompetenzkatalog qualitaetssichern

Start: Vor einer fachlichen Ueberarbeitung von `data/curriculum_catalog_v1.csv`.

Schreibprozess: Kein fachlicher Schreibprozess. Die internen QS-Skripte lesen CSV-Dateien und melden Struktur-, ID- und Bestandsschutzverletzungen.

Freigegebener Pruefpfad:

```text
data/curriculum_catalog_v1.csv
-> scripts/validate_curriculum_catalog.py
-> scripts/compare_curriculum_catalog.py
-> scripts/next_competency_ids.py
```

Betroffene Datenquellen:

- `data/curriculum_catalog_v1.csv` nur lesend
- Vergleichskopie eines frueheren oder freigegebenen CSV-Katalogs nur lesend

Regel: Vor CSV-Aenderungen wird der aktuelle Katalog validiert. Vor Uebernahme einer neuen Katalogversion wird sie gegen den freigegebenen Altstand verglichen. Bestehende `competency_id`s duerfen niemals fachlich umgedeutet oder wiederverwendet werden; Text-, Hierarchie-, Status- und Stufenaenderungen an bestehenden IDs muessen durch das Vergleichswerkzeug sichtbar werden. Neue Kompetenz-IDs werden mit `scripts/next_competency_ids.py` global fortlaufend vergeben; fachbezogene Nummernkreise und Wiederverwendung von Luecken sind ausgeschlossen. Die QS-Skripte schreiben nicht in SQLite, erzeugen keine Migration und veraendern keine UI-Projektionen.

## Testdaten fuer Laura-Pilottest erzeugen

Start: Fuer einen Pilottest soll die lokale SQLite-Datenbank mit kuenstlichen Daten befuellt werden.

Schreibprozess: Explizites CLI-Script `scripts/seed_test_data.py`.

Freigegebener Testpfad:

```text
python3 scripts/seed_test_data.py
```

Optionaler Reset-Pfad:

```text
python3 scripts/seed_test_data.py --reset
```

Betroffene Datenquellen:

- SQLite `data/kompetenzmanager.sqlite`
- Dateisystem `data/documents/<student_id>/`

Erforderliche IDs:

- kuenstliche `student_id`
- bestehende oder kuenstliche `group_id`, `course_id`, `course_group_id`
- kuenstliche `observation_id`
- kuenstliche `document_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Beobachtungsdialog
- Berichtsvorbereitung
- Dokumentationsstand
- Dokumente & Medien

Regel: Der produktive App-Start erzeugt keine Demo-Schueler. Testdaten werden nur durch das explizite Script erzeugt. Ohne `--reset` bricht das Script ab, wenn bereits Schueler, Beobachtungen oder Dokumente vorhanden sind. Mit `--reset` wird bewusst ein frisches lokales Testsystem erzeugt. Der Pilottest-Seed bildet ein Halbjahr von September bis Januar ab und enthaelt unterschiedliche Beobachtungsdichten, Kompetenzverlaeufe, bestaetigte Kompetenzstaende, Abweichungen zwischen Vorschlag und Bestaetigung sowie Demo-Dokumente. Es werden keine echten Kindernamen und keine echten Dokumente verwendet; Demo-Dateien sind harmlose Platzhalter und werden nicht versioniert.

## Lernentwicklungsbericht-Entwurf speichern

Start: Laura legt aus einem Schuelerprofil einen Lernentwicklungsbericht-Entwurf an oder speichert einen bereits geladenen Entwurf erneut.

Freigegebener Pfad:

```text
PySide Berichtswerkstatt
-> LearningReportDraftViewModel
-> StudentDesktopAdapter
-> Application Command / ReportDraftService
-> SQLiteReportDraftRepository
-> SQLite report_drafts + Relationstabellen
```

Betroffene Datenquellen:

- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`

Erforderliche IDs:

- neuer oder bestehender `report_draft_id`
- bestehender `student_id`
- ausgewaehlte bestehende `subject_id`
- ausgewaehlte bestehende `competency_id`
- ausgewaehlte bestehende `observation_id`

Regel: Anlegen erzeugt genau einen Entwurf mit Status `draft` und unveraenderlichem `created_at`. Aktualisieren ersetzt Fachauswahl, Fachtexte, Kompetenz-, Beobachtungs- und Diagrammreferenzen atomar und setzt `updated_at`. Kompetenz- und Beobachtungsinhalte werden nicht kopiert. Der Prozess erzeugt keine Bewertung, Bestaetigung, Version, Freigabe, Archivierung oder finale Ausgabe. Das neutrale `ReportOutputModel` wird weiterhin erst fuer die Vorschau beziehungsweise PDF-Ausgabe aus dem geladenen Entwurf und den aktuellen freigegebenen Leseprojektionen gebaut.

## Lernentwicklungsbericht-Entwurf laden

Start: Laura oeffnet einen vorhandenen Entwurf zur Weiterbearbeitung.

Leseweg:

```text
SQLite report_drafts + Relationstabellen
-> SQLiteReportDraftRepository
-> Application Query
-> LearningReportDraftViewModel
-> PySide Berichtswerkstatt
```

Regel: Laden rekonstruiert ausschliesslich gespeicherte manuelle Texte und Referenzen. Kompetenzstatus, Kompetenztexte und Beobachtungsinhalte werden aus ihren bestehenden Sources of Truth neu projiziert. Historische Kompetenzreferenzen bleiben dadurch aufloesbar, ohne fuer neue Auswahl reaktiviert zu werden.

## LEG-Arbeitsentwurf speichern

Start: Laura legt fuer einen Schueler einen Lernentwicklungsgespraech-Arbeitsentwurf an oder speichert einen bereits geladenen Entwurf erneut.

Freigegebener Pfad:

```text
LEG ViewModel
-> StudentDesktopAdapter
-> LearningConferenceDraftApplicationService
-> LearningConferenceDraftService
-> SQLiteLearningConferenceDraftRepository
-> SQLite learning_conference_drafts + Relationstabellen
```

Betroffene Datenquellen:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Erforderliche IDs:

- neuer oder bestehender `learning_conference_draft_id`
- bestehender `student_id`
- ausgewaehlte bestehende `subject_id`
- ausgewaehlte bestehende `competency_id`
- ausgewaehlte bestehende `observation_id`

Regel: Anlegen erzeugt genau einen Entwurf mit Status `draft` und unveraenderlichem `created_at`. Aktualisieren ersetzt manuelle Inhalte sowie Fach-, Themen-, Kompetenz-, Beobachtungs- und Diagrammreferenzen atomar und setzt `updated_at`. `student_id` bleibt stabil. Neue Beobachtungsreferenzen muessen aktiv sein und zum Kind gehoeren. Bereits referenzierte, spaeter soft-geloeschte Belege bleiben erhalten und werden beim Laden als nicht verfuegbar gekennzeichnet. Der Prozess erzeugt keine Kompetenzbewertung, keinen Kompetenzstatus, keine automatischen Texte, keine finale Version, Freigabe oder Archivierung.

## LEG-Arbeitsentwurf laden

Start: Laura oeffnet einen vorhandenen Entwurf zur Weiterbearbeitung.

Leseweg:

```text
SQLite learning_conference_drafts + Relationstabellen
-> SQLiteLearningConferenceDraftRepository
-> Application Query
-> LearningConferenceDraftViewModel
-> produktiver Sprint-7G.2-LEG-Arbeitsbereich
```

Regel: Laden rekonstruiert manuelle Inhalte und stabile Referenzen. Kompetenzstatus, Kompetenztexte und Beobachtungsinhalte werden aus den bestehenden Live-Sources-of-Truth neu projiziert. Nicht mehr aktive Beobachtungsbelege werden weder verworfen noch ersetzt, sondern kontrolliert als nicht verfuegbar ausgewiesen. Der Draft ist kein eingefrorener Gespraechsstand.

Sprint 7G.2 startet diesen Prozess im Schuelerprofil ueber `Lernentwicklungsgespräch`. Bei genau einem vorhandenen Draft wird dieser geladen. Bei mehreren Drafts muss Laura einen vorhandenen Entwurf oder das explizite Anlegen eines neuen Entwurfs waehlen. Die Dialogaktion `Entwurf speichern` darf jederzeit ausgefuehrt werden; Schliessen allein erzeugt keine finale Dokumentation und fuehrt keine stillschweigende Speicherung aus.

## Kompetenz aendern

Start: Name, Beschreibung, Hierarchie oder Status einer bestehenden Kompetenz wird angepasst.

Schreibprozess: Kompetenzverwaltung / Lehrplanpflege, spaeter freizugeben.

Betroffene Datenquellen:

- `data_competencies`
- optional `data_subjects`

Erforderliche IDs:

- bestehender `competency_id`
- gueltiger `subject_id`
- optional gueltiger `parent_competency_id`

Automatisch profitierende Ansichten:

- Beobachtungsdialog
- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Regel: `competency_id` bleibt erhalten. Alte grobe Kompetenzen duerfen spaeter deaktiviert oder archiviert werden, aber nicht geloescht werden, solange historische Beobachtungen oder bestaetigte Kompetenzstaende darauf verweisen. Bestehende `observation_competency_ratings` bleiben gueltig und werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Offene Entscheidung fuer einen spaeteren Implementierungssprint: historische Beobachtungen zeigen entweder das aktuelle Kompetenzlabel oder das zum Beobachtungszeitpunkt gueltige Label.

## Schuelerdokument hinzufuegen

Start: Zu einem Schueler wird ein Hauptdokument referenziert.

Schreibprozess: Schuelerverwaltung / Dokumentenfunktion, spaeter freizugeben.

Betroffene Datenquellen:

- `data_media`

Erforderliche IDs:

- neuer `media_id`
- bestehender `student_id`

Automatisch profitierende Ansichten:

- Schuelerverwaltung
- Schuelerprofil
- Berichte

Regel: Das Dokument liegt im Dateisystem unter `Dokumente/<student_id>/Hauptdokumente/`. Excel speichert nur `file_ref` und Metadaten. Kein Dokument wird in Excel eingebettet.

## Beobachtungsanhang hinzufuegen

Start: Zu einer Beobachtung wird eine Anlage hinzugefuegt.

Schreibprozess: Medienfunktion, spaeter freizugeben.

Betroffene Datenquellen:

- `data_media`

Erforderliche IDs:

- neuer `media_id`
- bestehender `student_id`
- bestehender `observation_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Beobachtungsdetails
- Berichte

Regel: Beobachtungsanhaenge liegen im Dateisystem unter `Dokumente/<student_id>/Beobachtungsanhaenge/<observation_id>/`. Excel speichert nur `file_ref` und Metadaten. Medien referenzieren Beobachtungen und speichern keine Beobachtungsinhalte doppelt.
