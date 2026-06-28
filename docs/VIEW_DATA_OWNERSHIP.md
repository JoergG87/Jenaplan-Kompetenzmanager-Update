# View Data Ownership

Dieses Dokument definiert, welche Datenquellen eine Ansicht lesen oder schreiben darf.

Eine neue Ansicht darf nicht umgesetzt werden, bevor ihre Datenverantwortung hier dokumentiert ist.

Jede Ansicht besitzt genau definierte Datenquellen.

Eine Ansicht darf ausschliesslich auf die in diesem Dokument eingetragenen Datenquellen zugreifen.

Neue Datenquellen duerfen nur nach Erweiterung dieser Dokumentation in einer Ansicht verwendet werden.

Eine Ansicht darf nur fachlich erforderliche Datenquellen lesen.

Nicht erlaubt ist:

```text
alles lesen, weil es moeglich ist
```

Erlaubt ist nur:

```text
nur lesen, was fuer diese Ansicht fachlich begruendet ist
```

Dashboards duerfen mehrere Quellen lesen, muessen aber jede Quelle fachlich begruenden.

## Temporaerer UI-State

Temporaere UI-Zustaende gehoeren nicht zum fachlichen Datenmodell.

Sie werden beim Verlassen einer View verworfen.

Dazu gehoeren mindestens:

- Suchtext
- Suchergebnis
- Hervorhebungen
- temporaere Auswahl

Diese Informationen werden weder gespeichert noch zwischen Views uebernommen.

Beim erneuten Oeffnen einer View startet diese in ihrem definierten Standardzustand.

Fachliche Daten duerfen durch das Zuruecksetzen von temporaerem UI-State nicht veraendert werden.

## UI-Projektionssortierung

UI-Projektionen duerfen eigene Sortierregeln verwenden.

Diese Sortierung dient ausschliesslich der Darstellung.

Die Reihenfolge der Darstellung wird ausschliesslich durch den Projection Builder vorbereitet.

Sie veraendert niemals:

- `tbl_students`
- `tbl_groups`
- `tbl_courses`

Die Sortierung erfolgt ausschliesslich innerhalb der Projektion.

Die Datenhaltung, insbesondere `tbl_students`, bleibt unveraendert.

## Stammgruppenuebersicht

Liest:

- `data_students`
- `data_groups`
- `data_courses`

Schreibt:

- nichts

Navigation:

- `student_id`

UI-Projektionen:

- Schuelerkarten
- Kurs auf Schuelerkarte
- Kartenfarbe aus Kurs
- Suche
- Pfeilnavigation zum Schuelerprofil

Regel:

Die Stammgruppenuebersicht ist Auswahl- und Navigationsansicht. Sie verwaltet keine Schuelerdaten.

## Kursuebersicht

Liest:

- `data_students`
- `data_courses`
- `data_groups`

Schreibt:

- nichts

Navigation:

- `student_id`

UI-Projektionen:

- Schuelerkarten eines Kurses
- Stammgruppe auf Schuelerkarte
- Suche
- Pfeilnavigation zum Schuelerprofil

Regel:

Die Kursuebersicht ist eine Projektion derselben Schuelerdaten wie die Stammgruppenuebersicht.

## Schuelerprofil

Liest:

- `data_students`
- `data_groups`
- `data_courses`
- `data_observations`
- `data_observation_competencies`
- `data_competencies`
- `data_subjects`
- `data_media`

Schreibt:

- nichts

Navigation:

- `student_id`
- spaeter `observation_id`
- spaeter `competency_id`

UI-Projektionen:

- Profilkopf
- Stammgruppe
- Kurs
- Beobachtungsverlauf
- Kompetenzchips
- Medienhinweise

Regel:

Das Schuelerprofil zeigt Daten eines Schuelers und startet spaeter freigegebene Dialoge. Es schreibt selbst keine fachlichen Daten.

## Beobachtungsdialog

Liest:

- `data_students`
- `data_subjects`
- `data_competencies`
- `data_observations` bei Bearbeitung bestehender Beobachtungen
- `data_observation_competencies` bei Bearbeitung bestehender Zuordnungen

Schreibt:

- `data_observations`
- `data_observation_competencies`
- spaeter `data_media`

Navigation:

- `student_id`
- `observation_id` bei Bearbeitung
- `competency_id` fuer Zuordnungen

UI-Projektionen:

- ausgewaehlter Schueler
- Kompetenzauswahl
- Beobachtungsnotiz
- Kontext
- Bewertung/Zuordnung

Regel:

Der Beobachtungsdialog ist ein freizugebender Schreibprozess. Ohne Data-Lifecycle-Eintrag darf er nicht implementiert werden.

## Kompetenzansicht

Liest:

- `data_competencies`
- `data_subjects`
- `data_observation_competencies`
- `data_observations`
- `data_students`

Schreibt:

- nichts

Navigation:

- `competency_id`
- `student_id` bei schuelerbezogener Filterung
- `observation_id` fuer spaetere Beobachtungsdetails

UI-Projektionen:

- Kompetenzkopf
- Fach/Lernbereich
- Beobachtungen zur Kompetenz
- Kompetenzverlauf

Regel:

Die Kompetenzansicht ist Auswertung und Navigation. Sie schreibt keine fachlichen Daten.

## Dashboards

Liest:

- `data_students`: Schuelerkontext fuer Auswertung
- `data_groups`: Gruppierung nach Stammgruppe
- `data_courses`: Gruppierung nach Kurs
- `data_subjects`: fachliche Gruppierung
- `data_competencies`: Kompetenzstruktur
- `data_observations`: Beobachtungsbasis
- `data_observation_competencies`: Kompetenzzuordnung und Bewertung
- `data_media`: Hinweise auf Anlagen, falls fachlich relevant
- `data_settings`: Anzeige- und Zeitraumkontext

Schreibt:

- niemals

Navigation:

- `student_id`
- `group_id`
- `course_id`
- `competency_id`
- `observation_id`

UI-Projektionen:

- aggregierte Beobachtungsdaten
- Kompetenzuebersichten
- Hinweise auf Handlungsbedarf

Regel:

Dashboards duerfen keine eigenen Schatteninformationen speichern.

## Berichte

Liest:

- `data_students`
- `data_groups`
- `data_courses`
- `data_subjects`
- `data_competencies`
- `data_observations`
- `data_observation_competencies`
- `data_media`
- `data_settings`

Schreibt:

- nichts

Navigation:

- `student_id`
- `course_id`
- `group_id`
- `competency_id`

UI-Projektionen:

- Lernentwicklungsbericht
- Beobachtungszusammenfassung
- Kompetenzdarstellung

Regel:

Berichte sind Ausgabeprojektionen. Sie speichern keine fachlichen Ergebnisdaten.
