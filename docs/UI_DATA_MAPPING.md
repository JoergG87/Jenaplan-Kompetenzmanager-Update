# UI Data Mapping

Dieses Dokument beschreibt, aus welcher Datenquelle sichtbare UI-Informationen stammen.

UI-Felder duerfen nicht eingefuehrt werden, ohne ihre Datenherkunft hier zu dokumentieren.

Spalten:

- Projektionstyp: `Anzeige`, `Navigation`, `Filter`, `Eingabe`, `Auswertung`
- Schreibend: `Nein`, `Ja (ueber freigegebenen Prozess)`, `Geplant`, `Nie`
- Verantwortliche Datenquelle: Datenquelle, die fachlich fuer das Feld verantwortlich ist

## Stammgruppenuebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenueberschrift | `data_groups.group_name` | Anzeige | Nein | `data_groups` | aktuelle Stammgruppe nach `group_id` |
| Schuelername auf Karte | `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | Anzeige, keine technische Identitaet |
| Initialen auf Karte | `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | abgeleitete Anzeige |
| Kurs auf Schuelerkarte | `data_students.course_id` -> `data_courses.course_name` | Anzeige | Nein | `data_courses` | Stammgruppe wird auf Karten nicht erneut angezeigt |
| Kartenfarbe | `data_students.course_id` -> `data_courses.color_key` | Anzeige | Nein | `data_courses` | farbliche Projektion der Kurszuordnung |
| Suche | `data_students.first_name`, `data_students.last_name`, `display_name` | Filter | Nein | `data_students` | Namen dienen nur Suche und Anzeige |
| Navigations-ID | `data_students.student_id` | Navigation | Nein | `data_students` | einzige technische Identitaet fuer Schueler |
| Neuer Schueler | keine fachliche Datenquelle | Navigation | Nein | keine | oeffnet `dlg_neuer_schueler`; Speichern spaeter ueber Runtime Adapter |
| Neue Beobachtung | `data_students.student_id` | Navigation | Geplant | `data_students` | startet spaeter zentralen Beobachtungsdialog |

## Kursuebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Kursueberschrift | `data_courses.course_name` | Anzeige | Nein | `data_courses` | aktuelle Kursauswahl nach `course_id` |
| Schuelername auf Karte | `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | Anzeige |
| Stammgruppe auf Karte | `data_students.group_id` -> `data_groups.group_name` | Anzeige | Nein | `data_groups` | Kursuebersicht zeigt Stammgruppe je Schueler |
| Kartenfarbe | `data_students.course_id` -> `data_courses.color_key` | Anzeige | Nein | `data_courses` | konsistent zur Kurszuordnung |
| Suche | `data_students.first_name`, `data_students.last_name`, `display_name` | Filter | Nein | `data_students` | filtert Projektion |
| Navigations-ID | `data_students.student_id` | Navigation | Nein | `data_students` | oeffnet Schuelerprofil |

## Schuelerprofil

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Profilkopf | `data_students.student_id` | Navigation | Nein | `data_students` | Profil wird technisch ueber `student_id` geoeffnet |
| Schuelername | `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | Anzeige |
| Stammgruppe | `data_students.group_id` -> `data_groups.group_name` | Anzeige | Nein | `data_groups` | organisatorische Zugehoerigkeit |
| Kurs | `data_students.course_id` -> `data_courses.course_name` | Anzeige | Nein | `data_courses` | Jahrgang |
| Beobachtungsverlauf | `data_observations` + `data_observation_competencies` | Anzeige | Nein | `data_observations` | Beobachtungen sind fachliche Quelle |
| Kompetenzchips | `data_observation_competencies.competency_id` -> `data_competencies.name` | Anzeige | Nein | `data_competencies` | abgeleitete Anzeige |
| Neue Beobachtung | `data_students.student_id` | Navigation | Geplant | `data_students` | startet spaeter zentralen Beobachtungsdialog |

## Schuelerverwaltung / `dlg_neuer_schueler`

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Vorname | zukuenftig `data_students.first_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | Pflichtfeld, keine technische Identitaet |
| Nachname | zukuenftig `data_students.last_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | Pflichtfeld |
| Stammgruppe | Auswahl aus `data_groups.group_name`, Speichern von `data_students.group_id` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_groups` | Pflichtauswahl, keine automatische Stammgruppenanlage |
| Kurs | Auswahl aus `data_courses.course_name`, Speichern von `data_students.course_id` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_courses` | Pflichtauswahl, keine automatische Kursanlage |
| Notiz | zukuenftig `data_students.student_notes` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | optional |
| Dokumentliste | zukuenftig `data_media.file_ref` nach `student_id` | Anzeige | Nein | `data_media` | zeigt referenzierte Dateien, keine Einbettung |
| Dokument hinzufuegen | zukuenftig Dateiauswahl -> `data_media` | Eingabe | Geplant | `data_media` | erzeugt spaeter `media_id` und `file_ref` nach freigegebenem Prozess |

Regel:

`dlg_neuer_schueler` ist eine worksheet-basierte Dialogseite. Die sichtbaren Eingabezellen sind temporaerer UI-State. Der freigegebene Runtime Adapter liest diesen UI-State und startet den Python-Schreibprozess bis SQLite.

Der VBA Adapter liest diese Werte ausschliesslich ueber die registrierten Named Ranges.

Der Adapter darf keine festen Zelladressen verwenden.

Nach erfolgreichem Python Command gibt Feature 1.4b nur ein Runtime-Ergebnis an Excel zurueck. Sichtbare Schuelerinformationen werden erst in einem spaeteren Schritt ueber ein Python-erzeugtes Projection-Refresh-Paket aktualisiert.

## Kompetenzansicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Kompetenzname | `data_competencies.name` | Anzeige | Nein | `data_competencies` | technische Identitaet ist `competency_id` |
| Fach/Lernbereich | `data_competencies.subject_id` -> `data_subjects.name` | Anzeige | Nein | `data_subjects` | fachliche Struktur |
| Beobachtungen zur Kompetenz | `data_observation_competencies` -> `data_observations` | Anzeige | Nein | `data_observations` | keine doppelte Beobachtungsdatenhaltung |
| Kompetenzverlauf | `data_observation_competencies.rating` + `data_observations.date` | Auswertung | Nein | `data_observation_competencies` | historisierte Projektion |
| Navigations-ID | `data_competencies.competency_id` | Navigation | Nein | `data_competencies` | oeffnet Kompetenzansicht |

## Beobachtungsdialog

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| ausgewaehlter Schueler | `student_id` aus Navigation -> `data_students` | Anzeige | Nein | `data_students` | Namen werden nicht als technische Identitaet verwendet |
| Fachauswahl | `data/curriculum_catalog_v1.csv` im PySide6-Prototyp, spaeter `data_subjects` | Eingabe | Nein | Kompetenzverwaltung / Lehrplanpflege | filtert die sichtbare Kompetenzauswahl; App-Anzeigename `EPU`, kein App-Fach `Sachunterricht` |
| Kompetenzauswahl | `data/curriculum_catalog_v1.csv` im PySide6-Prototyp, spaeter `data_competencies` + `data_subjects` | Eingabe | Nein | `data_competencies` | ausgewaehlte Kompetenzbewertungen koennen aus mehreren Faechern stammen; v1-Katalog noch nicht final ausdifferenziert |
| Beobachtungsnotiz | zukuenftig `data_observations.note` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | Schreiben nur nach freigegebenem Prozess |
| Beobachtungskontext | zukuenftig `data_observations.context` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | Kontext gehoert zur Beobachtung |
| Kompetenzzuordnung | zukuenftig `data_observation_competencies` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_observation_competencies` | n:m-Zuordnung; Bewertung liegt pro ausgewaehlter Kompetenz, Persistenz folgt spaeter |
| Dokumente und Medien | zukuenftig `data_media.file_ref` nach `student_id` und optional `observation_id` | Eingabe | Geplant | `data_media` | nur als Anlage, keine Einbettung, Beobachtung bleibt Source of Truth |

## Berichte und Dashboard

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Schuelerinformationen | `data_students` + `data_groups` + `data_courses` | Anzeige | Nein | `data_students` | gemeinsame Stammdaten |
| Beobachtungsbasis | `data_observations` | Auswertung | Nie | `data_observations` | Beobachtung ist Source of Truth |
| Kompetenzdaten | `data_observation_competencies` + `data_competencies` | Auswertung | Nie | `data_observation_competencies` | abgeleitete Auswertung |
| Medienhinweise | `data_media` | Anzeige | Nie | `data_media` | optionale Anlagen |
