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

## PySide6 Einstellungen

Status: Sprint 2C wendet die gespeicherte Auswahl in Dokumentationsauswertungen an.

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Dokumentationsrelevante Faecher | SQLite `documentation_subject_settings` + SQLite `competencies.subject_id` / `subject_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `documentation_subject_settings` | Auswahl der Faecher, die fuer Dokumentations- und Auswertungslogik zaehlen; ohne gespeicherte Settings-Zeilen gelten alle aktiven Katalogfaecher; sichtbare Fachnamen kommen aus `competencies`, nicht aus der Settings-Tabelle; Hilfetext: `Diese Auswahl steuert, welche Fächer im Dokumentationsstand berücksichtigt werden. Beobachtungen bleiben immer erhalten.` |

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
| Profil-Reiter | bestehende Profil-ViewModels | Navigation / Struktur | Nein | keine neue Datenquelle | `Überblick` ist Startreiter; `Beobachtungen`, `Kompetenzen`, `Bericht` und `Dateien` enthalten die bestehenden Detailbereiche ohne neue Persistenz |
| Halbjahresblick | aktive `ObservationListItem`, `StudentCompetencySubjectGroup`, `StudentDocumentationSubjectStatus` | Auswertung | Nein | bestehende Profilprojektionen + `documentation_subject_settings` | zeigt Beobachtungszahl, Dokumentationsstand, letzte aktive Beobachtung, abgeleitete Stärken, Beobachtungshinweise und sichtbare Entwicklung; Beobachtungshinweise nutzen nur dokumentationsrelevante Faecher; keine technischen IDs und keine erfundenen fachlichen Aussagen |
| Beobachtungsverlauf | `data_observations` + `data_observation_competencies` | Anzeige | Nein | `data_observations` | kompakte aufklappbare Karten, neueste Beobachtungen oben; ohne aktive Filter werden drei neueste Beobachtungen gezeigt und bei Bedarf erweitert; Kompaktansicht zeigt Datum, Fachlabel, Kontext, Notizvorschau und Kompetenzanzahl; Detailansicht zeigt volle Notiz und Kompetenzbewertungen; Fachlabel aus Kompetenzfaechern, bei mehreren Faechern `Fächerübergreifend` |
| Beobachtungsfilter Fach | `ObservationListItem.subject_display_name` | Filter | Nein | `data_observations` | filtert nur den Beobachtungsverlauf; Optionen `Alle`, vorhandene Fachlabels und `Fächerübergreifend`, wenn vorhanden |
| Beobachtungsfilter Bewertung | `ObservationRatingViewModel.rating` | Filter | Nein | `data_observation_competencies` | filtert nur den Beobachtungsverlauf nach Beobachtungen mit mindestens einer passenden Kompetenzbewertung |
| Beobachtungssuche | `ObservationListItem.context`, `ObservationListItem.note`, `ObservationRatingViewModel.learning_area`, `competency_group`, `competency_text` | Filter | Nein | `data_observations` / `data_observation_competencies` | lokale Textsuche auf vorhandenen ViewModel-Daten; keine SQLite-Abfrage |
| Dokumentationsstatus in Schuelerlisten | SQLite `competencies` + aktive `data_observations` + `student_competency_confirmations` + `documentation_subject_settings` | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | kompakte Summary je Schueler, z. B. `5/8 Bereiche`; nicht dokumentationsrelevante Faecher zaehlen nicht als offen; keine vollstaendige Fachaufschluesselung in Listen |
| Schnellbeobachtung in Schuelerlisten | `StudentListItem.student_id` -> `NewObservationDialog` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | kompakte Zeilenaktion `Beobachten`; oeffnet bestehenden Beobachtungsdialog fuer genau diesen Schueler; Speichern laeuft ueber Adapter/Service/Repository |
| Dokumentationsstand im Schuelerprofil | SQLite `competencies` + aktive `data_observations` + `student_competency_confirmations` + `documentation_subject_settings` | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | zeigt dokumentierte Lernbereiche im Verhaeltnis zu dokumentationsrelevanten aktiven Katalogfaechern; Standardansicht kompakt, Fachdetails per `Details anzeigen` im Reiter `Überblick` und im Reiter `Kompetenzen`; Details zeigen Fachname, Zaehler, Fortschrittstext und ruhige Hinweise wie `Für nächste Beobachtungen geeignet`; Soft Deletes ausgeschlossen; Bestaetigungen zaehlen als dokumentiert |
| Kompetenzuebersicht | `data_observation_competencies.competency_id` -> SQLite `competencies` + aktive `data_observations.date` oder `student_competency_confirmations.confirmed_rating` | Anzeige | Nein | `data_observation_competencies` / `student_competency_confirmations` | beobachtete oder bestaetigte Kompetenzen; Faecher kompakt aufklappbar; Vorschlag wird gewichtet aus allen aktiven Beobachtungen berechnet, Verlauf chronologisch angezeigt, Soft Deletes ausgeschlossen; bestaetigte Staende ohne aktive Beobachtungshistorie bleiben sichtbar; Vorschlag ist keine gespeicherte Lehrerentscheidung |
| Fehlende Kompetenzen | SQLite `competencies` minus aktive Beobachtungsbewertungen und bestaetigte Kompetenzstaende, begrenzt durch `documentation_subject_settings` | Auswertung | Nein | `data_competencies` / `documentation_subject_settings` | optional aufklappbare Liste pro Fachgruppe; dient Planung und Dokumentationsueberblick, keine Bewertung; nicht dokumentationsrelevante Faecher liefern keine offenen Beobachtungsanlaesse |
| Bestaetigter Kompetenzstand | `student_competency_confirmations.confirmed_rating` nach `student_id` + `competency_id` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `student_competency_confirmations` | paedagogische Entscheidung der Lehrkraft; ueberschreibt keine Beobachtungen und aendert den Vorschlag nicht automatisch |
| Berichtsvorschau | bestaetigter Kompetenzstand oder berechneter Vorschlag + aktive `data_observations` | Auswertung | Nein | `data_observation_competencies` / `student_competency_confirmations` / `data_observations` | strukturierte Berichtsvorbereitung nach Fach; zeigt den aktuellen Kompetenzstand je relevanter Kompetenz mit Quelle, bevorzugt bestaetigte Staende vor berechneten Vorschlaegen; Entwicklung wird getrennt aus chronologischen aktiven Beobachtungen abgeleitet und formuliert Einzelbeobachtung, stabile Verlaeufe, positive Entwicklung, Rueckschritt oder wechselnde Beobachtungslage; Soft Deletes ausgeschlossen; echte Beobachtungen und bestaetigte Kompetenzstaende bleiben sichtbar, auch wenn ein Fach nicht dokumentationsrelevant ist; kann als Text kopiert oder als einfache Textdatei exportiert werden; keine KI-Textgenerierung, keine finalen Zeugnisformulierungen, keine gespeicherte Berichtsdatenhaltung |
| Dokumente & Medien | SQLite `documents` nach `student_id` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `documents` + Dateisystem `data/documents/<student_id>/` | zeigt alle aktiven Schuelerdokumente neueste oben; Dateien werden geoeffnet, wenn `file_path` vorhanden ist; Entfernen setzt `documents.active = 0` und loescht keine physische Datei; SQLite speichert keine BLOBs |
| Neue Beobachtung | `data_students.student_id` | Navigation | Ja (ueber freigegebenen Prozess) | `data_observations` | startet zentralen Beobachtungsdialog und speichert ueber Adapter/Service/Repository |
| Beobachtung bearbeiten | `data_observations.observation_id` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | oeffnet bestehenden Beobachtungsdatensatz im Dialog; Speichern ersetzt die Kompetenzbewertungen atomar |
| Beobachtung loeschen | `data_observations.observation_id` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | Soft Delete ueber `observations.active = 0`; aktive Profil- und Kompetenzuebersichten blenden die Beobachtung aus |

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
| Sortierung | `StudentDesktopAdapter.list_students()` + `sort_student_list()` | Anzeige | Nein | `data_students`, `data_courses` | zuerst Kursreihenfolge aus Stammdaten, dann alphabetisch nach Schuelername; Schueler ohne bekannten aktiven Kurs stehen am Ende |
| aktiver Filterhinweis | Shell-Filterstate aus Stammgruppe oder Kursverbund/Kurs | Anzeige | Nein | keine fachliche Datenquelle | zeigt `Alle Schüler`, `Stammgruppe: ...` oder `Kursverbund · Kurs`; keine Speicherung |
| Zurueck zur Uebersicht | temporaerer Shell-Filterstate | Navigation | Nein | keine fachliche Datenquelle | erscheint in gefilterten Stammgruppen-/Kurs-/Kursverbund-Schuelerlisten und setzt den Filter zurueck zur Uebersicht |
| Schnellbeobachtung | `StudentListItem.student_id` -> `NewObservationDialog` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `observations` / `observation_competency_ratings` | kompakte Zeilenaktion; nutzt denselben Beobachtungsdialog wie das Schuelerprofil und aktualisiert Liste und Dokumentationsstatus nach Speichern |

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
| Neuer Kursverbund | `CourseGroupDialog` -> `MasterDataDesktopAdapter.add_course_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` + Relationen | nutzt Name, Stammgruppen-Checkboxen und Kurs-Checkboxen; doppelte Namen werden abgefangen |
| Kursverbund bearbeiten | `CourseGroupDialog` -> `MasterDataDesktopAdapter.update_course_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` + Relationen | Checkbox-Auswahl fuer Stammgruppen und Kurse; Kursfilter bleibt Kurs plus Stammgruppen des Kursverbunds |
| Neue Stammgruppe | `MasterDataDesktopAdapter.add_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `groups` / `data_groups` | erzeugt persistente Stammgruppe, keine automatische Schuelerzuordnung |
| Neuer Kurs | `MasterDataDesktopAdapter.add_course()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `courses` / `data_courses` | erzeugt persistenten Kurs inklusive Kursfarbe |
| Umbenennen | `MasterDataDesktopAdapter.rename_*()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `groups` / `courses` | `group_id` und `course_id` bleiben fachlich massgeblich; Schueler-Umbuchung folgt separat |

## Kompetenzansicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Kompetenzname | SQLite `competencies.label` | Anzeige | Nein | `data_competencies` | technische Identitaet ist `competency_id` |
| Fach/Lernbereich | `data_competencies.subject_id` -> `data_subjects.name` | Anzeige | Nein | `data_subjects` | fachliche Struktur |
| Beobachtungen zur Kompetenz | `data_observation_competencies` -> `data_observations` | Anzeige | Nein | `data_observations` | keine doppelte Beobachtungsdatenhaltung |
| Kompetenzverlauf | `data_observation_competencies.rating` + `data_observations.date` | Auswertung | Nein | `data_observation_competencies` | historisierte Projektion |
| Navigations-ID | `data_competencies.competency_id` | Navigation | Nein | `data_competencies` | oeffnet Kompetenzansicht |

## Beobachtungsdialog

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| ausgewaehlter Schueler | `student_id` aus Navigation -> `data_students` | Anzeige | Nein | `data_students` | Namen werden nicht als technische Identitaet verwendet |
| Fachauswahl | SQLite `competencies.subject_id` / `subject_name` + `documentation_subject_settings` | Eingabe | Nein | Kompetenzverwaltung / Lehrplanpflege + `documentation_subject_settings` | neue Beobachtungen bieten nur dokumentationsrelevante aktive Faecher an; App-Anzeigename `EPU`, kein App-Fach `Sachunterricht`; bei Bearbeitung bleibt das gespeicherte Fach sichtbar, auch wenn es inzwischen nicht dokumentationsrelevant ist |
| Kompetenzauswahl | SQLite `competencies` | Eingabe | Ja | `data_observation_competencies` | jede Kompetenz hat `competency_id`, Fach und lesbares Label; ausgewaehlte Kompetenzbewertungen koennen aus mehreren Faechern stammen |
| Beobachtungsdatum | SQLite `observations.date` | Eingabe | Ja | `observations` | Datum gehoert zur Beobachtung |
| Beobachtungsnotiz | SQLite `observations.note` | Eingabe | Ja | `observations` | Schreiben ueber Adapter, Command, Service und Repository |
| Beobachtungskontext | SQLite `observations.context` | Eingabe | Ja | `observations` | Kontext gehoert zur Beobachtung |
| Kompetenzzuordnung | SQLite `observation_competency_ratings` | Eingabe | Ja | `observation_competency_ratings` | n:m-Zuordnung; Bewertung liegt pro ausgewaehlter Kompetenz |
| Dokumente und Medien | Dateiauswahl -> `StudentDesktopAdapter` -> SQLite `documents` nach `student_id` und optional `observation_id` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `documents` + Dateisystem `data/documents/<student_id>/` | Datei wird in den App-Datenordner kopiert; Beobachtungsanhaenge tragen zusaetzlich `observation_id`; Entfernen setzt `documents.active = 0`; keine Datei-BLOBs |

## Berichte und Dashboard

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Schuelerinformationen | `data_students` + `data_groups` + `data_courses` | Anzeige | Nein | `data_students` | gemeinsame Stammdaten |
| Beobachtungsbasis | `data_observations` | Auswertung | Nie | `data_observations` | Beobachtung ist Source of Truth |
| Kompetenzdaten | `data_observation_competencies` + `data_competencies` | Auswertung | Nie | `data_observation_competencies` | abgeleitete Auswertung |
| Berichtsvorbereitung | `student_competency_confirmations`, berechnete Kompetenzvorschlaege und aktive Beobachtungen | Auswertung | Nie | SQLite / `data_observations` | vorbereitende Struktur, kein gespeicherter Bericht, kein Export und keine KI-Textgenerierung |
| Medienhinweise | SQLite `documents` | Anzeige | Nie | SQLite `documents` | optionale Anlagen; Berichte nutzen Medien in diesem Sprint nicht produktiv weiter |
