# Data Lifecycle

Dieses Dokument beschreibt freigegebene oder geplante Schreibprozesse fuer fachliche Daten.

Kein Schreibprozess darf implementiert werden, bevor sein Lebenszyklus hier dokumentiert ist.

## Schueler anlegen

Start: Lehrkraft oder Verwaltung legt einen neuen Schueler an.

Schreibprozess: Schuelerverwaltung, spaeter freizugeben.

Primaerer UI-Einstieg: PySide-Dialog `Neuer Schüler`.

Status: Produktiver Schreibpfad bis SQLite ist ueber den PySide-Adapter umgesetzt. Excel-Projection-Refresh ist Legacy/Export und kein Zielpfad fuer neue UI-Funktionalitaet.

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

Regel: Neue Stammgruppen oder Kurse werden dabei nicht automatisch angelegt. Optionale Dokumente werden erst nach erfolgreicher Erzeugung der `student_id` referenziert. Dateien werden nicht in Excel eingebettet. Bei Fehlern bleibt der PySide-Dialog geoeffnet und SQLite unveraendert.

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

Schreibprozess: Stammgruppenverwaltung, spaeter freizugeben.

Betroffene Datenquellen:

- `data_groups`

Erforderliche IDs:

- neuer `group_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Schuelerverwaltung

Regel: Schueler werden erst durch `data_students.group_id` einer Stammgruppe zugeordnet.

## Stammgruppe aendern

Start: Name oder Status einer bestehenden Stammgruppe wird angepasst.

Schreibprozess: Stammgruppenverwaltung, spaeter freizugeben.

Betroffene Datenquellen:

- `data_groups`

Erforderliche IDs:

- bestehender `group_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `group_id` bleibt erhalten. Schuelerreferenzen bleiben gueltig.

## Kurs anlegen

Start: Neuer Kurs/Jahrgang wird benoetigt.

Schreibprozess: Kursverwaltung, spaeter freizugeben.

Betroffene Datenquellen:

- `data_courses`

Erforderliche IDs:

- neuer `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: Kursfarbe wird am Kurs gespeichert und nicht an einzelnen Schuelern.

## Kurs aendern

Start: Name, Farbe oder Status eines bestehenden Kurses wird angepasst.

Schreibprozess: Kursverwaltung, spaeter freizugeben.

Betroffene Datenquellen:

- `data_courses`

Erforderliche IDs:

- bestehender `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `course_id` bleibt erhalten. Schuelerkartenfarbe aktualisiert sich aus `course_id` und `data_courses.color_key`.

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
