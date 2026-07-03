# Data Lifecycle

Dieses Dokument beschreibt freigegebene oder geplante Schreibprozesse fuer fachliche Daten.

Kein Schreibprozess darf implementiert werden, bevor sein Lebenszyklus hier dokumentiert ist.

## Schueler anlegen

Start: Lehrkraft oder Verwaltung legt einen neuen Schueler an.

Schreibprozess: Schuelerverwaltung, spaeter freizugeben.

Primaerer UI-Einstieg: PySide-Dialog `Neuer Schüler`.

Status: Produktiver Schreibpfad bis SQLite ist ueber den PySide-Adapter umgesetzt. Beim produktiven App-Start werden Schema, Stammdaten und Kursverbund-Defaults initialisiert, aber keine Demo-Schueler erzeugt. Excel-Projection-Refresh ist Legacy/Export und kein Zielpfad fuer neue UI-Funktionalitaet.

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

Nach erfolgreichem `student.create` kann Python fuer Export-/Legacy-Zwecke eine Workbook-Projektion aus SQLite erzeugen.

Die GUI sammelt Eingaben und erzeugt Commands, enthaelt aber keine Businesslogik und schreibt nicht direkt aus Widgets in SQLite.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut. Excel bleibt als bestehende Projektion und moeglicher Export-/Berichtspfad erhalten.

Betroffene Datenquellen:

- `students` in SQLite als fachliche Source of Truth
- `data_students` als optionale Excel-/Exportprojektion aus SQLite
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
- `data_groups` als optionale Excel-/Exportprojektion aus SQLite

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
- `data_groups` als optionale Excel-/Exportprojektion aus SQLite

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
- `data_courses` als optionale Excel-/Exportprojektion aus SQLite

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
- `data_courses` als optionale Excel-/Exportprojektion aus SQLite

Erforderliche IDs:

- bestehender `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `course_id` bleibt erhalten. Schuelerkartenfarbe aktualisiert sich aus `course_id` und `courses.color_hex`.

## Kursverbund aendern

Start: Ein kursverbundbezogener Mathe-/Deutsch-Scope wird bearbeitet.

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

Regel: Name, Stammgruppen- und Kurszuordnung werden atomar gespeichert. Die Relationstabellen werden beim Speichern vollstaendig fuer den Kursverbund ersetzt. Es werden keine Schueler umgebucht und keine Beobachtungsdaten veraendert.

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

Schreibprozess: Zentraler Beobachtungsdialog, spaeter freizugeben.

Betroffene Datenquellen:

- `data_observations`
- `data_observation_competencies`
- optional `data_media`

Erforderliche IDs:

- neuer `observation_id`
- bestehender `student_id`
- mindestens ein bestehender `competency_id`, sobald Kompetenzzuordnung verpflichtend ist

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzansicht
- Berichte
- Dashboards

Regel: Beobachtung ist Source of Truth. Auswertungen leiten sich daraus ab.

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
