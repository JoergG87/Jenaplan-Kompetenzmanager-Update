# UI Data Mapping

Dieses Dokument beschreibt, aus welcher Datenquelle sichtbare UI-Informationen stammen.

UI-Felder duerfen nicht eingefuehrt werden, ohne ihre Datenherkunft hier zu dokumentieren.

Sprint 0.2A.2 fuehrt ausschliesslich ein injizierbares Backup-Backend ein. Sprint 0.2A.3a ergaenzt read-only Datenbank-Kompatibilitaet, Restore-Verifikation und eine rein technische, nicht sichtbare `RestorePreview`. Es entstehen keine sichtbare Ansicht, keine UI-Aktion und keine neuen UI-Felder; deshalb besitzen diese Betriebsfunktionen keine Feldzuordnung. Eine spaetere Settings-, Backup- oder Restore-UI benoetigt vor ihrer Implementierung eine eigene Product-Owner- und Mapping-Freigabe.

Spalten:

- Projektionstyp: `Anzeige`, `Navigation`, `Filter`, `Eingabe`, `Auswertung`
- Schreibend: `Nein`, `Ja (ueber freigegebenen Prozess)`, `Geplant`, `Nie`
- Verantwortliche Datenquelle: Datenquelle, die fachlich fuer das Feld verantwortlich ist

## App Shell

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| App-Info | statische Produkttexte | Anzeige | Nein | keine fachliche Datenquelle | benennt App-Name, Entwickler, lokale Desktop-App, Kurzbeschreibung und Copyright; zeigt keine technische Versions-, Build-, Pfad- oder Repositoryinformation ohne freigegebene aktuelle Produktquelle |
| App-Icon | versioniertes Asset `assets/app_icon.png` | Anzeige | Nein | keine fachliche Datenquelle | sichtbares Branding in Sidebar und Info-Dialog; keine Fachlogik |
| Globale Navigation | statische `NAVIGATION_ITEMS` | Navigation | Nein | keine fachliche Datenquelle | `ARBEIT`: `Heute`, `Schüler`; `VERWALTUNG`: `Stammdaten`, `Einstellungen`; keine leeren globalen Beobachtungs-, Kompetenz- oder Berichtsziele |
| Lokale Schuelernavigation | temporaerer `StudentsWorkspace`-State | Navigation / Filter | Nein | keine fachliche Datenquelle | Segmente `Stammgruppen`, `Kurse`, `Kursverbünde`, `Alle Schüler`; Drill-down behaelt den lokalen Ursprung, fachliche IDs und bestehende Filterprojektionen |
| Visuelles Theme | freigegebene Icon-Leitlinie und Tokens aus `docs/DESIGN_SYSTEM.md` | Anzeige | Nein | keine fachliche Datenquelle | native Systemschrift, semantische Farben/Typografie/Abstaende/Radien/Elevation/Motion, zentrale Buttonrollen und SVG-Shell-Icons; keine Fachlogik |
| Shell-Feedback | bestehende Shell-Ergebnisse und UI-Zustaende | Anzeige | Nein | keine fachliche Datenquelle | nicht blockierender `Toast` fuer kurze Rueckmeldung; `InlineMessage` fuer kontextgebundene Hinweise; keine Persistenz |

## PySide6 Einstellungen

Status: Sprint 2C wendet die gespeicherte Auswahl in Dokumentationsauswertungen an.

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Dokumentationsrelevante Faecher | SQLite `documentation_subject_settings` + SQLite `competencies.subject_id` / `subject_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `documentation_subject_settings` | Auswahl der Faecher, die fuer Dokumentations- und Auswertungslogik zaehlen; ohne gespeicherte Settings-Zeilen gelten alle aktiven Katalogfaecher; sichtbare Fachnamen kommen aus `competencies`, nicht aus der Settings-Tabelle; Hilfetext: `Diese Auswahl steuert, welche Fächer im Dokumentationsstand berücksichtigt werden. Beobachtungen bleiben immer erhalten.` |
| Wochenstundenplan | SQLite `timetable_entries` + aufgeloeste Namen aus `competencies`, `groups`, `courses`, `course_groups` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | `timetable_entries` | Wochentags-Tabs Montag bis Freitag; darunter nur der gewaehlte Tag als breite chronologische Zeilenliste; leerer Tag `Für <Wochentag> sind noch keine Stunden eingetragen.`; deaktivierte Stunden bleiben ruhig sichtbar; IDs bleiben unsichtbare technische Referenzen |
| Beginn und Ende | `timetable_entries.start_time` / `end_time` | Eingabe | Ja (ueber freigegebenen Prozess) | `timetable_entries` | `HH:MM`, Beginn strikt vor Ende; aktive Ueberschneidungen werden abgelehnt |
| Fach | `timetable_entries.subject_id` -> `competencies.subject_name` | Eingabe / Anzeige | Ja (nur ID-Referenz) | `competencies` / `timetable_entries` | Auswahl nur aus vorhandenen Fach-IDs; kein kopierter Fachname |
| Zielart und Ziel | `timetable_entries.target_type` / `target_id` -> `groups`, `courses` oder `course_groups` | Eingabe / Anzeige | Ja (nur ID-Referenz) | Stammdaten / `timetable_entries` | Ziel-ID muss zur Zielart Stammgruppe, Kurs oder Kursverbund passen |
| Raum/Ort | `timetable_entries.room` | Eingabe / Anzeige | Ja (ueber freigegebenen Prozess) | `timetable_entries` | optionaler Freitext, keine neue Raum-Stammdatenquelle |

## PySide6 Heute / technischer Screen `dashboard`

UX-Status UI Sprint 1: sichtbarer Hauptnavigationspunkt `Heute`; der technische Schluessel `dashboard` und alle Datenherkuenfte bleiben unveraendert. Die fruehere `Übersicht` ist lokal in `Schüler` integriert.

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Für diese Stunde | `TimetableDesktopAdapter.read_projection(at).current` beziehungsweise `.next` | Anzeige / Navigation | Nein | SQLite `timetable_entries` | zeigt Uhrzeit, Fach, Zielart, Ziel und optional Raum; ohne aktive laufende Stunde wird die naechste kanonische Occurrence gezeigt |
| Kein Stundenplan | `TimetableWeekViewModel.is_empty` | Anzeige / Navigation | Nein | SQLite `timetable_entries` | neutraler Leerzustand `Noch kein Stundenplan eingerichtet` mit Navigation zu Einstellungen; keine erfundenen Unterrichtsdaten |
| Heutiger Stundenplan | `TimetableDesktopAdapter.read_projection(at).today` | Anzeige / Navigation | Nein | SQLite `timetable_entries` | horizontale Timeline aus aktiven Stundenkarten; aktuelle Stunde anhand `.current` mit `JETZT` markiert, vergangene anhand des expliziten Zeitpunkts dezent; deaktivierte und geloeschte Eintraege erscheinen nicht |
| Unterrichtsziel-Navigation | `TimetableEntryViewModel.target_type` + `target_id` | Navigation | Nein | `groups`, `courses`, `course_groups` | technische ID oeffnet den passenden bestehenden Schuelerkontext; Namen sind nur Anzeige |
| Stundenplanbasierte Beobachtung | `subject_id`, `subject_label`, `target_type`, `target_id`, `target_label` der kanonischen Stunde | Navigation / Eingabe | Ja (erst im bestehenden Beobachtungsprozess) | `timetable_entries` + bestehender Beobachtungspfad | Dashboard navigiert zur Kindauswahl; danach oeffnet derselbe `NewObservationDialog` mit Fach und Unterrichtskontext fluechtig vorbelegt; keine Speicherung im Dashboard |
| Dokumentations-Heatmap | kanonische `StudentDocumentationSubjectStatus.documented_count`, als Anzahl Kinder mit mindestens einer dokumentierten Kompetenz je aktiver Stammgruppe und Fach aggregiert | Auswertung | Nein | `competencies`, `observations`, `observation_competency_ratings`, `student_competency_confirmations`, `documentation_subject_settings` | reine Dokumentationsabdeckung `Kinder dokumentiert / Kinder der Stammgruppe`; neutrale Blauabstufung, keine Ratings, Leistungsscores, Rangliste oder Entwicklungsurteile |
| Passende Kinder fuer diese Stunde | aktive Zielmitgliedschaft aus `students.group_id` / `students.course_id` und bei Kursverbund dessen bestehende Gruppen-/Kursrelationen + `courses.course_name` / `courses.color_hex` + aktive `observations.date` mit eindeutigem Bezug zu `timetable_entries.subject_id` | Anzeige / Navigation | Nein | `students`, `courses`, `course_group_student_groups`, `course_group_courses`, `observations`, `observation_competency_ratings` | maximal fuenf; Kurszugehoerigkeit als dezentes `CourseBadge`; keine Fachbeobachtung zuerst, danach aelteste letzte Fachbeobachtung, kuerzlich dokumentiert und heute dokumentiert; Gleichstand alphabetisch; keine Ratings oder Kompetenzstatus |
| Beobachten beim vorgeschlagenen Kind | `DashboardSuggestedStudentViewModel.student_id` + Fach und Zielkontext der hervorgehobenen Stunde | Navigation / Eingabe | Ja (erst im bestehenden Beobachtungsprozess) | `students`, `timetable_entries`, `observations` | oeffnet direkt denselben `NewObservationDialog` fuer das Kind und belegt Fach sowie Unterrichtskontext fluechtig vor |

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
| Kurs | `data_students.course_id` -> `data_courses.course_name` + `data_courses.color_hex` | Anzeige | Nein | `data_courses` | organisatorische Zugehoerigkeit als `CourseBadge` im Profilkopf; Text bleibt sichtbar, Farbe ist weder Status noch Bewertung |
| Dokumentationsring im Profilkopf | `StudentDocumentationSubjectStatus.learning_area_statuses` aus der kanonischen Dokumentationsstatusprojektion | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | zeigt Lernbereiche mit mindestens einer dokumentierten konkreten Kompetenz im Verhältnis zu allen aktiven dokumentationsrelevanten Lernbereichen; keine Prozentzahl, Leistungs- oder Ampelsemantik |
| Orientierungskarte im Arbeitsprofil | `StudentProfileDashboardViewModel.orientation_changes` aus kanonischen `StudentCompetencyStatusViewModel.evidence` und vorhandener aktueller Bestätigung | Auswertung / Navigation | Nein | `data_observations` / `data_observation_competencies` / `student_competency_confirmations` / `data_competencies` | höchstens drei konkrete Kompetenzen mit mindestens zwei realen Ereignissen und mindestens einem tatsächlichen Statuswechsel bis zum Stichtag; neueste Änderung zuerst, bei Gleichstand curriculare Reihenfolge. Jede kompakte Karte zeigt Kompetenz, Fach/Thema, `Ausgangslage`, `Aktueller dokumentierter Stand` und genau den datierten auslösenden Beleg. Die Tokens `--`, `-`, `+`, `++` bleiben immer textlich benannte pädagogische Dokumentationsstände; Pastell-Badges und Pfeil dienen nur der Orientierung. Die gesamte Karte navigiert bei Beobachtungsbeleg zur bestehenden Beobachtung, sonst zur bestehenden Kompetenzansicht; historische Referenz nur als ruhiges Badge. Keine Scores, Prozentwerte, Noten, Rankings, Mittelwerte, Lerngeschwindigkeit, Interpolation oder automatische Trendinterpretation |
| Kompetenzkarte im Arbeitsprofil | `StudentProfileDashboardViewModel.documentation_summary`, `.confirmed_documented_count` und `.observed_only_count` | Auswertung / Navigation | Nein | kanonische Kompetenzstatus- und Dokumentationsstatusprojektion | zeigt Dokumentationsumfang und Herkunft; Bestätigung und Beobachtung bleiben getrennt, alle Counts sind Dokumentations- und keine Leistungswerte; öffnet nur das bestehende Kompetenz-Cockpit |
| Noch nicht dokumentiert im Arbeitsprofil | `StudentProfileDashboardViewModel.undocumented_count` und `.undocumented_subjects` | Auswertung / Navigation | Nein | kanonische Dokumentationsstatusprojektion | neutraler Umfangshinweis nach curricularer Fachreihenfolge; fehlende Dokumentation ist kein negativer Status und öffnet nur das bestehende Kompetenz-Cockpit |
| Profil-Reiter | bestehende Profil-ViewModels | Navigation / Struktur | Nein | keine neue Datenquelle | `Überblick` ist Startreiter; `Beobachtungen`, `Kompetenzen`, `Bericht` und `Dateien` enthalten die bestehenden Detailbereiche ohne neue Persistenz; ein zentrales `SegmentedControl` steuert den weiterhin zustands- und scrollsicher verantwortlichen `QTabWidget` |
| Beobachtungsverlauf | `data_observations` + `data_observation_competencies` | Anzeige | Nein | `data_observations` | kompakte aufklappbare Karten, neueste Beobachtungen oben; ohne aktive Filter werden drei neueste Beobachtungen gezeigt und bei Bedarf erweitert; Kompaktansicht zeigt Datum, Fachlabel, Kontext, Notizvorschau und Kompetenzanzahl; Detailansicht zeigt volle Notiz und Kompetenzbewertungen; Fachlabel aus Kompetenzfaechern, bei mehreren Faechern `Fächerübergreifend` |
| Beobachtungsfilter Fach | `ObservationListItem.subject_display_name` | Filter | Nein | `data_observations` | filtert nur den Beobachtungsverlauf; Optionen `Alle`, vorhandene Fachlabels und `Fächerübergreifend`, wenn vorhanden |
| Beobachtungsfilter Bewertung | `ObservationRatingViewModel.rating` | Filter | Nein | `data_observation_competencies` | filtert nur den Beobachtungsverlauf nach Beobachtungen mit mindestens einer passenden Kompetenzbewertung |
| Beobachtungssuche | `ObservationListItem.context`, `ObservationListItem.note`, `ObservationRatingViewModel.learning_area`, `competency_group`, `competency_text` | Filter | Nein | `data_observations` / `data_observation_competencies` | lokale Textsuche auf vorhandenen ViewModel-Daten; keine SQLite-Abfrage; Sprint-3A-Mapping: `learning_area` = Kompetenzbereich, `competency_group` = Thema, `competency_text` = Kompetenz |
| Dokumentationsstatus in Schuelerlisten | SQLite `competencies` + aktive `data_observations` + `student_competency_confirmations` + `documentation_subject_settings` | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | kompakte Summary je Schueler; kuenftige Sprint-3-Zielregel zaehlt konkrete aktive Kompetenzen, darf aber ruhig nach Fach, Kompetenzbereich und Thema aggregiert angezeigt werden; nicht dokumentationsrelevante Faecher zaehlen nicht als offen |
| Schnellbeobachtung in Schuelerlisten | `StudentListItem.student_id` -> `NewObservationDialog` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | kompakte Zeilenaktion `Beobachten`; oeffnet bestehenden Beobachtungsdialog fuer genau diesen Schueler; Speichern laeuft ueber Adapter/Service/Repository |
| Dokumentationsstand im Schuelerprofil | SQLite `competencies` + aktive `data_observations` + `student_competency_confirmations` + `documentation_subject_settings` | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | kuenftige Sprint-3-Zielregel: konkrete aktive Kompetenzen zaehlen, Anzeige darf nach Fach -> Kompetenzbereich -> Thema aggregiert bleiben, z. B. `Mathematik -> Groessen & Messen -> Zeit: 2/6 Kompetenzen beobachtet`; Standardansicht kompakt, Fachdetails per `Details anzeigen`; Soft Deletes ausgeschlossen; Bestaetigungen zaehlen als dokumentiert |
| Kompetenz-Cockpit | kanonische `StudentCompetencyStatusViewModel`-Zeilen aus `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` | Anzeige / Navigation | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` | rein lesende Hierarchie Fach -> Kompetenzbereich -> Thema -> Kompetenz; Fach-, Bereichs-, Themen- und Kompetenzkarten verwenden jeweils ihre gesamte sichtbare Flaeche sowie Enter/Leertaste fuer denselben lokalen Disclosure-State wie der vorhandene `Öffnen`-Button. Lokale Suche sowie Fach-, Dokumentations- und Klassenstufenfilter schraenken nur sichtbare aktive Karten und Zeilen ein. `Passende Kompetenzen` zeigt `stage_1_3` und `cross_stage`, `Klassenstufe 4` zeigt `stage_4` und `cross_stage`, `Alle Kompetenzen` den gesamten aktiven aktuellen Zielbestand. `Dokumentiert` umfasst aktive Beobachtung oder Bestaetigung, `Noch nicht dokumentiert` weder, `Beobachtet, noch nicht bestätigt` nutzt `observed_unconfirmed`, `Bestätigter Stand` umfasst `confirmed` und `newer_observations`, der letzte Filter nur `newer_observations`. Fach- und Kompetenzbereich zeigen weiterhin dokumentiert/gesamt und neutrale Fortschrittsbalken aus dem vollstaendigen aktiven Zielbestand; alle Ebenen starten geschlossen und behalten ihren Aufklappzustand lokal. Historische Zeilen bleiben separat unter `Historisch dokumentiert` und werden nicht gefiltert. Kompetenzdetails zeigen den kanonischen Dokumentationszustand, bei vorhandener Bestätigung deren Bewertung, Datum und Notiz, einen klar getrennten Vorschlag aus Beobachtungen sowie aktive eindeutige Nachweise neueste zuerst. Nachweise verwenden die bestehende `observation_id` zur Navigation in den vorhandenen Profilreiter und zum bestehenden Bearbeitungspfad; keine Statusberechnung oder zusätzliche Datenabfrage im Screen |
| Undokumentierte Kompetenzen im Cockpit | kanonische Sprint-6B-Zeilen mit `documentation_state = undocumented` | Anzeige | Nein | `data_competencies` | nicht als globale Liste; nur innerhalb eines manuell geöffneten Themas sichtbar; historisch referenzierte Kompetenzen werden nicht vermischt |
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
| Kursbadge | `StudentListItem.course_name` + `StudentListItem.course_color_hex` aus SQLite-Kursstammdaten | Anzeige | Nein | `data_courses` / SQLite `courses` | dezentes `CourseBadge` in eigener Kurs-Spalte; Kursname bleibt sichtbar, keine Zeilenfaerbung und keine Status-, Leistungs- oder Entwicklungssemantik |
| Sortierung | `StudentDesktopAdapter.list_students()` + `sort_student_list()` | Anzeige | Nein | `data_students`, `data_courses` | zuerst Kursreihenfolge aus Stammdaten, dann alphabetisch nach Schuelername; Schueler ohne bekannten aktiven Kurs stehen am Ende |
| aktiver Filterhinweis | Shell-Filterstate aus Stammgruppe, Kurs oder Kursverbund/Kurs | Anzeige | Nein | keine fachliche Datenquelle | `FilterBar` zeigt den aktiven Kontext als `FilterChip`; Reset erscheint nur bei gefilterter Liste und kehrt zur lokalen Auswahl zurueck; keine Speicherung |
| Zurueck zur Auswahl | temporaerer Shell- und `StudentsWorkspace`-State | Navigation | Nein | keine fachliche Datenquelle | erscheint in gefilterten Stammgruppen-/Kurs-/Kursverbund-Schuelerlisten, setzt den Filter zurueck und kehrt lokal zum ausloesenden Segment zurueck |
| Profil oeffnen | `StudentListItem.student_id` | Navigation | Nein | `data_students` | einfacher Klick auf eine Nicht-Aktionszelle, Enter oder die sekundäre Zeilenaktion `Profil öffnen` navigiert genau einmal; eingebettete Aktionen bleiben davon getrennt; Namen bleiben reine Anzeige |
| Schnellbeobachtung | `StudentListItem.student_id` -> `NewObservationDialog` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `observations` / `observation_competency_ratings` | kompakte Zeilenaktion; nutzt denselben Beobachtungsdialog wie das Schuelerprofil und aktualisiert Liste und Dokumentationsstatus nach Speichern |

Regel: Die Schueleruebersicht liest persistente Schueler ueber `StudentDesktopAdapter` aus SQLite. Ein leerer produktiver Start zeigt die leere Liste und erzeugt keine Demo-Schueler.

## Lokale Schuelerprojektionen `Stammgruppen`, `Kurse` und `Kursverbünde`

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenliste | `MasterDataViewModel.groups` aus SQLite `groups` | Anzeige | Nein | `data_groups` / SQLite `groups` | zeigt alle persistent aktiven Stammgruppen |
| Schueleranzahl je Stammgruppe | `GroupSummaryViewModel.active_student_count` aus bestehendem Adapter | Anzeige | Nein | `data_students` | nur wenn fuer die Stammgruppe sauber verfuegbar |
| Direkte Kursliste | `MasterDataViewModel.courses` aus SQLite `courses` | Anzeige / Filter | Nein | `data_courses` / SQLite `courses` | zeigt persistente aktive Kurse in vorhandener Stammdatenreihenfolge und uebergibt `course_id` an die bestehende Schuelerprojektion |
| Kursverbund | `MasterDataViewModel.course_groups` aus SQLite `course_groups` + Relationen | Anzeige / Filter | Nein | SQLite `course_groups`, `course_group_student_groups`, `course_group_courses` | definiert, welche Stammgruppen gemeinsam Mathe-/Deutsch-Kurse bilden |
| Kursliste im Kursverbund | `CourseGroupViewModel.selected_course_ids` -> `MasterDataViewModel.courses` | Anzeige / Filter | Nein | `data_courses` | Kursuebersicht ist kursverbundbezogen, nicht global ueber alle Stammgruppen |
| Kursmarker | `MasterDataItemViewModel.color_hex` | Anzeige | Nein | `data_courses` | nur kleiner Marker, keine Zeilenfaerbung |
| Kursverbund-Kursfilter | `course_id` + `CourseGroupViewModel.selected_group_ids` | Filter | Nein | `data_students` | zeigt nur Schueler mit Kurs und Stammgruppe im ausgewaehlten Kursverbund |

Regel: Alle drei Projektionen werden innerhalb von `StudentsWorkspace` angezeigt und sind keine eigenen globalen Navigationsziele. Sie lesen und filtern unveraendert ueber vorhandene Adapter/ViewModels; der Workspace erzeugt keine fachliche Datenquelle und keinen Schreibprozess.

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
| Kompetenzname | SQLite `competencies.label` / `competencies.description`, Katalog `competency_label` / `competency_text` | Anzeige | Nein | `data_competencies` | technische Identitaet ist `competency_id`; `label` ist Kurzlabel aus `competency_label`, `description` die konkrete Kompetenz |
| Fach / Kompetenzbereich / Thema | `competencies.subject_id` / `subject_name`, `learning_area`, `competency_group` | Anzeige | Nein | `data_competencies` | fachliche Struktur: Fach -> Kompetenzbereich -> Thema -> Kompetenz |
| Beobachtungen zur Kompetenz | `data_observation_competencies` -> `data_observations` | Anzeige | Nein | `data_observations` | keine doppelte Beobachtungsdatenhaltung |
| Kompetenzverlauf | `data_observation_competencies.rating` + `data_observations.date` | Auswertung | Nein | `data_observation_competencies` | historisierte Projektion |
| Navigations-ID | `data_competencies.competency_id` | Navigation | Nein | `data_competencies` | oeffnet Kompetenzansicht |

## Beobachtungsdialog

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| ausgewaehlter Schueler | `student_id` aus Navigation -> `data_students` | Anzeige | Nein | `data_students` | Namen werden nicht als technische Identitaet verwendet |
| Fachauswahl | SQLite `competencies.subject_id` / `subject_name` + `documentation_subject_settings` | Eingabe | Nein | Kompetenzverwaltung / Lehrplanpflege + `documentation_subject_settings` | neue Beobachtungen bieten nur dokumentationsrelevante aktive Faecher an; App-Anzeigename `EPU`, kein App-Fach `Sachunterricht`; bei Bearbeitung bleibt das gespeicherte Fach sichtbar, auch wenn es inzwischen nicht dokumentationsrelevant ist |
| Kompetenzauswahl | SQLite `competencies`, befuellt aus `data/curriculum_catalog_v1.csv` | Eingabe | Ja | `data_observation_competencies` | Drei-Zonen-Dialog mit separat scrollbarer Auswahl und separat scrollbarem Katalog; die Adapterprojektion traegt das vorhandene `learning_stage` fuer die lokalen Ansichten `Passende Kompetenzen`, `Klassenstufe 4` und `Alle Kompetenzen`. Neue Beobachtungen bieten nur `catalog_status = current` und `active = 1` an; jede Kompetenz hat `competency_id`, Fach, Kompetenzbereich, Thema, konkrete Kompetenz und lesbares Kurzlabel; ausgewaehlte Kompetenzbewertungen koennen aus mehreren Faechern stammen; beim Bearbeiten bleiben bereits bewertete `legacy`- oder inaktive Kompetenzen mit historischem Text sichtbar, bewertbar und entfernbar. Suche, Filter und Collapse veraendern weder Auswahl noch Einzelbewertung |
| Schnellauswahl | aktive SQLite `observations` + `observation_competency_ratings` -> aktive `current`-Zeilen aus `competencies` | Anzeige / Eingabe | Nein | `observations` / `observation_competency_ratings` / `competencies` | Adapterprojektion je Schueler und aktuell gewaehltem Fach: hoechstens vier eindeutige Kompetenzen, neueste zuerst; Legacy- und inaktive Kompetenzen ausgeschlossen; ohne Eintraege oder bei aktivem Suchtext ausgeblendet; Klick fuegt nur zur bestehenden Auswahl hinzu und speichert nichts eigenstaendig |
| Beobachtungsdatum | SQLite `observations.date` | Eingabe | Ja | `observations` | Datum gehoert zur Beobachtung |
| Beobachtungsnotiz | SQLite `observations.note` | Eingabe | Ja | `observations` | Schreiben ueber Adapter, Command, Service und Repository |
| Schnellbeobachtung | bewusste Dialogeingabe; beim Bearbeiten aktive SQLite-`observations`-Zeile mit nichtleerer `note` und ohne `observation_competency_ratings` | Eingabe / Anzeige | Ja (ueber bestehenden Beobachtungsprozess) | `observations` / `observation_competency_ratings` | erlaubt Speichern ohne Kompetenz nur bei aktivierter Checkbox und nichtleerer Notiz; deaktiviert den Kompetenzbereich ohne Auswahl zu loeschen; im Verlauf dezent gekennzeichnet |
| Beobachtungskontext | SQLite `observations.context` | Eingabe | Ja | `observations` | Kontext gehoert zur Beobachtung |
| Kompetenzzuordnung | SQLite `observation_competency_ratings` | Eingabe | Ja | `observation_competency_ratings` | n:m-Zuordnung; vier direkt anklickbare Bewertungs-Chips schreiben weiterhin genau einen `rating`-Wert je konkreter `competency_id`; `offen` wird nicht gespeichert, sondern bedeutet keine Zuordnungszeile |
| Dokumente und Medien | Dateiauswahl -> `StudentDesktopAdapter` -> SQLite `documents` nach `student_id` und optional `observation_id` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `documents` + Dateisystem `data/documents/<student_id>/` | Datei wird in den App-Datenordner kopiert; Beobachtungsanhaenge tragen zusaetzlich `observation_id`; die ruhige Dateizeile zeigt Dateiname, Typ und Entfernen-Aktion. Entfernen setzt `documents.active = 0`; keine Datei-BLOBs |

## Berichte und Dashboard

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Schuelerinformationen | `data_students` + `data_groups` + `data_courses` | Anzeige | Nein | `data_students` | gemeinsame Stammdaten |
| Beobachtungsbasis | `data_observations` | Auswertung | Nie | `data_observations` | Beobachtung ist Source of Truth |
| Kompetenzdaten | `data_observation_competencies` + `data_competencies` | Auswertung | Nie | `data_observation_competencies` | abgeleitete Auswertung |
| bestehende Berichtsvorschau im Schuelerprofil | `student_competency_confirmations`, berechnete Kompetenzvorschlaege und aktive Beobachtungen | Auswertung | Nie | SQLite / `data_observations` | bestehende vorbereitende Struktur, kein gespeicherter Bericht und keine KI-Textgenerierung |
| Dokumentkontext Lernentwicklungsbericht | `LearningReportDraftViewModel` + `StudentDetailViewModel` | Anzeige / Eingabe | Ja, als Entwurf | SQLite `report_drafts`, `students`, `groups` | Berichtstyp, Zeitraum, Lehrkraft und Status werden als `draft` gespeichert; Schueler- und Gruppennamen bleiben Projektionen |
| Fach- und Kompetenzauswahl | gespeicherte Referenzen + `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` | Auswahl | Ja, als Referenzen | `report_draft_subjects`, `report_draft_competencies` + kanonische Sprint-6-Projektion | keine Kompetenztexte oder Bewertungen im Entwurf; nur aktive `current`-Kompetenzen neu auswählbar, historische Referenzen weiterhin aufloesbar |
| Beobachtungsbelege | gespeicherte `observation_id`-Referenzen + aktive Beobachtungsprojektion | Auswahl | Ja, als Referenzen | `report_draft_observations`, SQLite `observations` | Datum, Kontext und Notiz bleiben in `observations` und werden nicht in den Entwurf kopiert |
| Gesamtblick und Fachtexte | `LearningReportDraftViewModel` | Eingabe | Ja, als Entwurf | `report_drafts.overall_text`, `report_draft_subjects` | ausschliesslich manuelle Eingabe; keine KI-Formulierung, automatische Bewertung oder Zielerzeugung |
| Diagrammauswahl | `LearningReportDraftViewModel.chart_selections` | Auswahl | Ja, als Referenz | `report_draft_charts` | speichert nur Fach und Diagrammtyp; keine berechneten Diagrammdaten |
| Entwurfs-PDF-Ausgabe | vollstaendiges Draft-`ReportOutputModel` -> unveraenderter `PdfRenderer` | Ausgabe | Nein | fluechtiges Ausgabemodell | Renderer liest keine Datenbank und leitet keine Inhalte ab; kein finales Artefakt |
| Finalisierungsstatus | `LearningReportRevisionReadService.state_for_draft(report_draft_id)` -> `LearningReportRevisionStatusViewModel` | Anzeige | Nein | `learning_reports`, `learning_report_revisions` + aktueller validierter Finalisierungskandidat | zeigt `Entwurf`, `Finalisiert · Revision X` oder `Entwurf geändert`; Vergleich und Hashpruefung erfolgen zentral, nie im Widget |
| Finalisierungsbestaetigung | `ReportFinalizationService.prepare(report_draft_id)` -> `LearningReportFinalizationPreviewViewModel` | Anzeige / verpflichtender Anzeigename | Ja, ueber bestehenden Finalisierungsprozess | gespeicherter `RPD` + registrierte Finalisierungsquellen | zeigt Kind, Typ, Zeitraum, Faecher, Kompetenz-/Beobachtungsanzahl und neue Revisionsnummer; erzeugt keine Benutzer-ID |
| Revisionsprotokoll | `LearningReportRevisionStatusViewModel.history` | Anzeige | Nein | `learning_report_revisions` + unveraenderliche `learning_reports`-Identitaet | neueste Revision zuerst; Status `Aktuell` oder `Ersetzt`; ausschliesslich Aktion `Öffnen` |
| Finale Berichtrevision | `LearningReportRevisionReadService.snapshot_payload(RPV-ID)` -> `LearningReportRevisionViewModel` | schreibgeschuetzte Anzeige | Nein | ausschliesslich `learning_report_revisions.snapshot_json`, Revisionsmetadaten und `snapshot_sha256` | friert sichtbare Fachinformationen, manuelle Inhalte, Referenzprovenienz und Diagrammwerte ein; keine Live-Nachladung |
| Finales Berichts-PDF | `RPV-ID` -> `StudentDesktopAdapter.generate_learning_report_pdf` -> `GenerateLearningReportPdfCommand` -> `LearningReportPdfService` -> snapshotbasiertes `ReportOutputModel` -> `PdfRenderer` | Ausgabe / Artefaktaktion | Ja, nur Artefaktreferenz | `learning_report_revisions` + `learning_report_pdf_artifacts` + verwaltete PDF-Datei | nur Status `finalized`; keine Draft- oder Live-Daten; zeigt danach Dateiname, Erzeugungszeitpunkt und PDF-SHA-256 |
| Medienhinweise | SQLite `documents` | Anzeige | Nie | SQLite `documents` | optionale Anlagen; Berichte nutzen Medien in diesem Sprint nicht produktiv weiter |

UX-Regel Sprint 7F.2: `prototypes/learning_report_ux/` ist die verbindliche Spezifikation fuer Layout, Navigation, Arbeitsweise, Kartenstruktur, Informationshierarchie, Abstaende, Auswahlmechanismen und Vorschaukonzept. Die produktive Ansicht wechselt oben zwischen `Bericht bearbeiten` und `Berichtsvorschau`; die Bearbeitung navigiert links zwischen Dokumentkontext, den fachbezogenen Arbeitsbereichen und Abschluss. Kompetenzstaende sind anders als im isolierten Demo-Prototyp nicht editierbar, weil der Entwurf ausschliesslich `competency_id`-Referenzen speichert und die kanonische Kompetenzstatusprojektion nicht veraendert. Globale Abschluss- und interne Notizfelder werden nicht angezeigt, weil sie im unveraenderten Entwurfsmodell keine verantwortliche Datenquelle besitzen.

## Lernentwicklungsgespraech

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Gespraechsrahmen | `LearningConferenceDraftViewModel` + `StudentDetailViewModel` | Anzeige / Eingabe | Ja, als Entwurf | `learning_conference_drafts`, `students`, `groups` | Zeitraum, Gespraechsdatum und verantwortliche Lehrkraft werden gespeichert; Kind- und Stammgruppenname bleiben Live-Projektionen |
| Fachliche Bereiche | gespeicherte `subject_id`-Referenzen + kanonische Kompetenzprojektion | Auswahl | Ja, als Referenzen | `learning_conference_draft_subjects`, `competencies` | keine Fachdefinition oder Kompetenzlogik im Entwurf |
| Uebergreifende Gespraechsthemen | vier registrierte `cross_topic_key`-Werte | Auswahl | Ja, als Entwurf | `learning_conference_draft_cross_topics` | entspricht exakt Arbeitsverhalten, Sozialverhalten, Selbststaendigkeit und Lernorganisation aus dem Prototyp |
| Kompetenzen | gespeicherte `competency_id`-Referenzen + `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` | Auswahl | Ja, als Referenzen | `learning_conference_draft_competencies` + kanonische Sprint-6-Projektion | Fach -> Kompetenzbereich -> Thema -> Kompetenz; sichtbar sind aktive kindbezogene Kompetenzbeobachtungen im vollstaendig gesetzten LEG-Zeitraum, aktuelle Bestaetigungen und bereits ausgewaehlte Draft-Referenzen; ohne vollstaendigen Zeitraum gelten alle aktiven Kompetenzbeobachtungen des Kindes; leere Zweige werden ausgeblendet; kein kopierter Text, Status oder eigene Bewertung |
| Beobachtungsbelege | gespeicherte `observation_id`-Referenzen + aktive Beobachtungsprojektion | Auswahl | Ja, als Referenzen | `learning_conference_draft_observations`, `observations` | nur Belege des Kindes neu auswaehlbar; Schnellbeobachtungen duerfen Textbeleg sein; nicht mehr aktive Referenzen bleiben kontrolliert sichtbar |
| Gespraechseinstieg, Rueckblick, Lehrkraftsicht, Staerken und Entwicklungsfelder | `LearningConferenceDraftViewModel` | Eingabe | Ja, als Entwurf | `learning_conference_drafts` | ausschliesslich manuelle Texte |
| Ziele, Unterstuetzung und Vereinbarungen | getrennte vorbereitete und gemeinsam vereinbarte Felder | Eingabe | Ja, als Entwurf | `learning_conference_drafts` | keine automatische Ziel-, Text- oder Bewertungsableitung |
| Zustaendigkeiten und naechster Ueberpruefungszeitpunkt | `LearningConferenceDraftViewModel` | Eingabe | Ja, als Entwurf | `learning_conference_drafts` | manuelle Verantwortungsangabe und optionales ISO-Datum |
| Optionale Gespraechsbilder | gespeicherter Diagrammtyp + bestehende Live-Projektionen | Auswahl / Auswertung | Ja, nur Typreferenz | `learning_conference_draft_charts` | keine gespeicherten Diagrammdaten, Scores oder Trends |
| LEG-Kontextkopf | `LearningConferencePreparationViewModel` + aktueller Widget-/Draftzustand | Anzeige | Nein | `students`, `groups`, `courses`, `learning_conference_drafts` | Kind, Stammgruppe und Kurs sind Live-Projektionen; Datum und Lehrkraft spiegeln bestehende Draftfelder; Phasen- und Speicherstatus sind fluechtiger UI-State |
| LEG-Phasenstatus | Vollstaendigkeit der bereits sichtbaren Draft-Widgets und Auswahlreferenzen | Anzeige | Nein | keine neue Datenquelle | ausschliesslich `Aktuell`, `Inhalt vorhanden` oder `Noch leer`; nicht persistiert und keine Abschlussaussage |
| LEG-Belegzusammenfassung ausserhalb Phase 5 | aktuelle lokale Kompetenz-, Beobachtungs- und Diagrammauswahl | Anzeige | Nein | bestehende Draftreferenzen + Live-Projektionen | rein lesend; `Belege ansehen` wechselt nur lokal zu Phase 5 |
| LEG-Speicherstatus und Dirty-State | Vergleich des aktuellen `LearningConferenceDraftViewModel` mit dem zuletzt geladenen beziehungsweise erfolgreich gespeicherten Widgetstand | Anzeige | Nein | keine neue Datenquelle | `Ungespeicherte Aenderungen` oder lokalisierter letzter Speicherstand; keine Autosave- oder Domainstatusbehauptung |

UX-Regel UI Sprint 6B: `docs/LEG_UX_AUDIT_AND_TARGET.md` ersetzt fuer die produktive Dialogkomposition die fruehere Zwei-Seiten-Darstellung aus Sprint 7G.2. Genau eine der sechs vorhandenen Phasen ist aktiv. `strengths_text` und `teacher_perspective_text` erscheinen als interne Vorbereitung, `child_retrospective_text` und `development_fields_text` als gemeinsam bearbeitete Inhalte, `agreed_goals_text` sichtbar in Phase 4 und die Kompetenz-/Beleg-/Diagrammauswahl in Phase 5. Alle Feldbedeutungen, Referenzen und der vollstaendige `LearningConferenceDraftViewModel`-Speicherpfad bleiben unveraendert.

### LEG-Abschluss und Revisionen

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Abschlussaktion | gespeicherte LCD-ID | Befehl | Ja, explizit | `LearningConferenceCompletionApplicationService` | UI uebergibt ausschliesslich die ID; keine Snapshot-, Hash- oder Persistenzlogik im Widget oder ViewModel |
| Abschlussstatus | `LearningConferenceRevisionStatusViewModel` | Anzeige | Nein | `learning_conferences`, `learning_conference_revisions` + validierter Kandidat | unterscheidet noch nicht abgeschlossen, aktuell und Draft seit Abschluss geaendert |
| Abschlussfehler | `LearningConferenceCompletionErrorViewModel` aus typisiertem Domainfehler | Anzeige / Navigation | Nein | LEG-Domainvalidierung | Dialog wertet keine Fehlermeldungsstrings aus |
| Revisionshistorie | `LearningConferenceRevisionListItemViewModel` | Anzeige / Navigation | Nein | `learning_conference_revisions` | neueste zuerst; keine Bearbeiten-, Loeschen- oder Wiederherstellungsaktion |
| Finales LEG-PDF | `LearningConferencePdfArtifactViewModel` aus verifizierter `LCA` | Anzeige / Aktion | Ja, ueber freigegebenen Artefaktprozess | `learning_conference_revisions`, `learning_conference_pdf_artifacts` | Aktion nur fuer aktuelle `completed`-LCV; UI uebergibt ausschliesslich LCV-ID und besitzt keine Renderer-, Snapshot-, Hash-, Pfad- oder SQLite-Logik |
| Historische Revisionsansicht | `LearningConferenceRevisionViewModel` | schreibgeschuetzte Anzeige | Nein | verifiziertes `snapshot_json` der LCV | keine Live-Aufloesung fachlicher Werte; Integritaetspruefung vor Anzeige |

Der Abschlussbereich ist vom primaeren Draftspeichern getrennt. Solange der aktuelle Widgetstand ungespeichert ist, ist der Abschluss deaktiviert. Nach einer Korrektur bleibt der LCD bearbeitbar; erst ein erneuter expliziter Abschluss kann eine neue LCV erzeugen.
