# Data Lifecycle

Dieses Dokument beschreibt freigegebene oder geplante Schreibprozesse fuer fachliche Daten.

Kein Schreibprozess darf implementiert werden, bevor sein Lebenszyklus hier dokumentiert ist.

## Dokumentationsrelevante Faecher speichern

Start: Laura legt in den Einstellungen fest, welche Faecher fuer spaetere Dokumentations- und Auswertungslogik zaehlen sollen.

Schreibprozess: Dokumentationskonfiguration ueber Settings-UI, Desktop Adapter und SQLite-Repository. Sprint 2B speichert die Auswahl; die Auswertungsfilterung folgt separat.

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

- spaeter Schuelerlisten-Dokumentationsstatus
- spaeter Schuelerprofil-Dokumentationsstand
- spaeter offene Kompetenzen
- spaeter Berichtsvorbereitung

Regel: Die Speicherung ersetzt die vollstaendige Auswahl in `documentation_subject_settings`. Wenn keine Settings-Zeilen vorhanden sind, bleibt das bisherige Verhalten erhalten: alle aktiven Katalogfaecher aus `competencies.active = 1` gelten als dokumentationsrelevant. Die Einstellung loescht keine Beobachtungen, veraendert keine Kompetenzdefinitionen und nutzt `competencies.active` nicht als Einstellungsfeld.

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

Regel: Beobachtung ist Source of Truth. Auswertungen leiten sich daraus ab.
Beobachtung und Kompetenzbewertungen werden atomar gespeichert; eine Bewertung gehoert zur Kompetenz, nicht global zur Beobachtung. Medien/Anhaenge und Berichte bleiben separate spaetere Prozesse.

## Beobachtung aendern

Start: Lehrkraft korrigiert eine bestehende Beobachtung im Schuelerprofil.

Schreibprozess: PySide-Schuelerprofil oeffnet den Beobachtungsdialog mit `observation_id`; Speichern laeuft ueber `StudentDesktopAdapter`, `observation.update`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`
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

Regel: `observation_id` bleibt erhalten. Beobachtungsfelder werden aktualisiert; Kompetenzbewertungen werden fuer die Beobachtung atomar ersetzt. Die Fachanzeige wird weiter aus den Kompetenzfaechern abgeleitet.

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

Regel: Kompetenzstruktur wird nicht aus Beobachtungstexten abgeleitet.

## Kompetenzkatalog initialisieren

Start: PySide-App oeffnet eine SQLite-Datenbank ohne vorhandene Kompetenzen.

Schreibprozess: Initialisierung ueber `StudentDesktopAdapter`, `CurriculumDesktopAdapter` und `SQLiteCompetencyRepository.ensure_catalog_defaults()`.

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

Regel: Der Seed laeuft nur bei leerem SQLite-Kompetenzkatalog. Bestehende Kompetenzen werden nicht ueberschrieben. Kompetenzstaende werden weiterhin aus Beobachtungen abgeleitet und nicht manuell doppelt gespeichert.

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

Regel: `competency_id` bleibt erhalten. Offene Entscheidung: historische Beobachtungen zeigen entweder das aktuelle Kompetenzlabel oder das zum Beobachtungszeitpunkt gueltige Label.

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
