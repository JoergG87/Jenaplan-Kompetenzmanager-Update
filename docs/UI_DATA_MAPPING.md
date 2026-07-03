# UI Data Mapping

Dieses Dokument beschreibt, aus welcher Datenquelle sichtbare UI-Informationen stammen.

UI-Felder duerfen nicht eingefuehrt werden, ohne ihre Datenherkunft hier zu dokumentieren.

Spalten:

- Projektionstyp: `Anzeige`, `Navigation`, `Filter`, `Eingabe`, `Auswertung`
- Schreibend: `Nein`, `Ja (ueber freigegebenen Prozess)`, `Geplant`, `Nie`
- Verantwortliche Datenquelle: Datenquelle, die fachlich fuer das Feld verantwortlich ist

## App Shell

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| App-Info | statische PySide6-Prototyp-Texte | Anzeige | Nein | keine fachliche Datenquelle | nicht-technische Orientierung, keine Fachlogik |
| App-Icon | versioniertes Asset `assets/app_icon.png` | Anzeige | Nein | keine fachliche Datenquelle | sichtbares Branding in Sidebar und Info-Dialog; keine Fachlogik |
| Visuelles Theme | freigegebene Icon-Leitlinie aus `docs/DESIGN_SYSTEM.md` | Anzeige | Nein | keine fachliche Datenquelle | app-weites PySide-Theme fuer Farben, Karten, Navigation, Tabellen, Eingaben und Dialoge; keine Fachlogik |

## Stammgruppenuebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenueberschrift | `data_groups.group_name` | Anzeige | Nein | `data_groups` | aktuelle Stammgruppe nach `group_id` |
| Schuelername auf Karte | `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | Anzeige, keine technische Identitaet |
| Initialen auf Karte | `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | abgeleitete Anzeige |
| Kurs auf Schuelerkarte | `data_students.course_id` -> `data_courses.course_name` | Anzeige | Nein | `data_courses` | Stammgruppe wird auf Karten nicht erneut angezeigt |
| Kartenfarbe | `data_students.course_id` -> `data_courses.color_key` / UI-Defaultfarbe im PySide6-Scope | Anzeige | Nein | `data_courses` | farbliche Projektion der Kurszuordnung, keine Schuelerfarbe |
| Suche | `data_students.first_name`, `data_students.last_name`, `display_name` | Filter | Nein | `data_students` | Namen dienen nur Suche und Anzeige |
| Navigations-ID | `data_students.student_id` | Navigation | Nein | `data_students` | einzige technische Identitaet fuer Schueler |
| Neuer Schueler | keine fachliche Datenquelle | Navigation | Nein | keine | oeffnet in der Hauptanwendung den PySide-Dialog `Neuer Schüler`; historischer `dlg_neuer_schueler`-Pfad bleibt Legacy |
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

## Legacy: Schuelerverwaltung / `dlg_neuer_schueler`

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

`dlg_neuer_schueler` ist ein historischer worksheet-basierter Dialogseiten-Stand der Excel-Linie. Er ist kein Zielpfad fuer neue UI-Entwicklung, Smoke-Tests oder produktive Workflows. Der aktive Hauptpfad ist der PySide-Schuelerdialog.

## PySide6 Schuelerdialog

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Vorname | `QLineEdit` -> `student.create.first_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | Pflichtfeld, keine technische Identitaet |
| Nachname | `QLineEdit` -> `student.create.last_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | Pflichtfeld |
| Stammgruppe | `MasterDataViewModel.groups` aus SQLite `groups` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_groups` / SQLite `groups` | Dropdown, kein Freitext; nur persistente Stammgruppen koennen fuer `student.create` gespeichert werden |
| Kurs | `MasterDataViewModel.courses` aus SQLite `courses` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_courses` / SQLite `courses` | Dropdown, kein Freitext; nur persistente Kurse koennen fuer `student.create` gespeichert werden |
| Notiz | `QTextEdit` -> `student.create.student_notes` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | optional |

Regel:

Der PySide-Schuelerdialog ist der aktive Eingabepfad fuer `student.create`. Er sammelt Eingaben, validiert UI-nah und nutzt den Desktop Adapter sowie Application-/Domain-/Repository-Schichten. Qt Widgets schreiben nicht direkt in SQLite.

## PySide6 Schueleruebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Name | `StudentListItem.display_name` aus `data_students.first_name` + `data_students.last_name` | Anzeige | Nein | `data_students` | Anzeige, keine technische Identitaet |
| Kurs | `StudentListItem.course_name` aus `data_courses.course_name` | Anzeige | Nein | `data_courses` | neutrale Textanzeige in eigener Kurs-Spalte, keine Zeilenfaerbung |
| Kursmarker | `StudentListItem.course_color_hex` aus SQLite-Kursfarbe | Anzeige | Nein | `data_courses` / SQLite `courses` | kleiner farbiger Marker vor dem Kursnamen; Farbe markiert den Kurs, nicht die ganze Zeile |
| aktiver Filterhinweis | Shell-Filterstate aus Stammgruppe oder Kursverbund/Kurs | Anzeige | Nein | keine fachliche Datenquelle | zeigt `Alle Schüler`, `Stammgruppe: ...` oder `Kursverbund · Kurs`; keine Speicherung |

Regel: Die Schueleruebersicht liest persistente Schueler ueber `StudentDesktopAdapter` aus SQLite. Ein leerer produktiver Start zeigt die leere Liste und erzeugt keine Demo-Schueler.

## PySide6 Uebersicht `Stammgruppen und Schülerbestand`

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenliste | `MasterDataViewModel.groups` aus SQLite `groups` | Anzeige | Nein | `data_groups` / SQLite `groups` | zeigt alle persistent aktiven Stammgruppen |
| Schueleranzahl je Stammgruppe | `GroupSummaryViewModel.active_student_count` aus bestehendem Adapter | Anzeige | Nein | `data_students` | nur wenn fuer die Stammgruppe sauber verfuegbar |
| Kursverbund | `MasterDataViewModel.course_groups` aus SQLite `course_groups` + Relationen | Anzeige / Filter | Nein | SQLite `course_groups`, `course_group_student_groups`, `course_group_courses` | definiert, welche Stammgruppen gemeinsam Mathe-/Deutsch-Kurse bilden |
| Kursliste im Kursverbund | `CourseGroupViewModel.selected_course_ids` -> `MasterDataViewModel.courses` | Anzeige / Filter | Nein | `data_courses` | Kursuebersicht ist kursverbundbezogen, nicht global ueber alle Stammgruppen |
| Kursmarker | `MasterDataItemViewModel.color_hex` | Anzeige | Nein | `data_courses` | nur kleiner Marker, keine Zeilenfaerbung |
| Kursverbund-Kursfilter | `course_id` + `CourseGroupViewModel.selected_group_ids` | Filter | Nein | `data_students` | zeigt nur Schueler mit Kurs und Stammgruppe im ausgewaehlten Kursverbund |

## PySide6 Stammdaten

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenliste | SQLite `groups.group_name` ueber `MasterDataDesktopAdapter` | Anzeige | Nein | SQLite `groups` / `data_groups` | Stammgruppen sind eigenstaendige Stammdaten |
| Kursliste | SQLite `courses.course_name` ueber `MasterDataDesktopAdapter` | Anzeige | Nein | SQLite `courses` / `data_courses` | Kurse sind eigenstaendige Stammdaten |
| Kursfarbe | SQLite `courses.color_name` + `courses.color_hex` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `courses` / `data_courses` | persistenter Farbwert am Kurs; Schuelerfarbe wird daraus abgeleitet |
| Kursverbund | `MasterDataViewModel.course_groups` aus SQLite `course_groups` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` | definiert Name, ausgewaehlte Stammgruppen und ausgewaehlte Kurse |
| Kursverbund bearbeiten | `CourseGroupDialog` -> `MasterDataDesktopAdapter.update_course_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` + Relationen | Checkbox-Auswahl fuer Stammgruppen und Kurse; Kursfilter bleibt Kurs plus Stammgruppen des Kursverbunds |
| Neue Stammgruppe | `MasterDataDesktopAdapter.add_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `groups` / `data_groups` | erzeugt persistente Stammgruppe, keine automatische Schuelerzuordnung |
| Neuer Kurs | `MasterDataDesktopAdapter.add_course()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `courses` / `data_courses` | erzeugt persistenten Kurs inklusive Kursfarbe |
| Umbenennen | `MasterDataDesktopAdapter.rename_*()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `groups` / `courses` | `group_id` und `course_id` bleiben fachlich massgeblich; Schueler-Umbuchung folgt separat |

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
