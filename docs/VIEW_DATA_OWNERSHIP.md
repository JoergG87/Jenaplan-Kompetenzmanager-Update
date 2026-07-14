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

Die Reihenfolge der Darstellung wird in der aktiven PySide-App durch Adapter/ViewModel-Projektionen vorbereitet. Historische Workbook-Projektionen nutzten frueher Projection Builder.

Sie veraendert niemals:

- `tbl_students`
- `tbl_groups`
- `tbl_courses`

Die Sortierung erfolgt ausschliesslich innerhalb der Projektion.

Die Datenhaltung, insbesondere `tbl_students`, bleibt unveraendert.

## Legacy: Worksheet-basierte Dialogseiten

Worksheet-basierte Dialogseiten waren in der Excel-Linie primaere Eingabedialoge. Sie sind nach ADR-046 Legacy und kein Zielpfad fuer neue UI-Entwicklung.

Sie sind eigene geschuetzte Arbeitsblaetter und keine fachlichen Datenquellen.

Sie sammeln Eingaben, fuehren spaeter nur einfache Oberflaechenvalidierung durch und rufen freigegebene Adapter auf.

Dialogseiten schreiben nicht direkt in `data_*`-Tabellen.

Nach erfolgreichem Speichern wird die Dialogseite verlassen und die betroffene Ansicht wird aus den registrierten Datenquellen aktualisiert.

VBA-UserForms sind deprecated und bleiben nur als experimenteller Artefaktstand erhalten.

## PySide6 Desktop-App

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Die Desktop-App ist keine fachliche Datenquelle.

Sie darf Daten anzeigen, Eingaben sammeln, Commands erzeugen und den `ApplicationCommandDispatcher` aufrufen.

Sie darf keine Businesslogik enthalten, keine fachlichen IDs erzeugen und nicht direkt aus Qt Widgets in SQLite schreiben.

Der validierte Schreibpfad lautet:

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Excel liegt nur noch als archivierter Legacy-Altstand unter `legacy/excel/`.

## PySide6 Einstellungen

Status: Sprint 8A ergaenzt den produktiven Wochenstundenplan neben der bestehenden Dokumentationskonfiguration.

Liest:

- `documentation_subject_settings`
- `data_competencies` / SQLite `competencies` fuer Fachschluessel und sichtbare Fachnamen
- `timetable_entries`
- `groups`, `courses` und `course_groups` fuer sichtbare Zielnamen

Schreibt:

- `documentation_subject_settings` ueber Repository-/Store-Methoden
- `timetable_entries` ueber `TimetableDesktopAdapter`, Application Service, Domain Service und Repository

UI-Projektionen:

- Auswahl dokumentationsrelevanter Faecher
- Wochentags-Tabs Montag bis Freitag mit einer breiten chronologischen Stundenliste fuer den ausgewaehlten Tag
- Anlegen, Bearbeiten, Loeschen und Aktivieren/Deaktivieren von Eintraegen

Regel:

Die Einstellungen duerfen keine Fachdefinitionen oder Stammdatenkopien speichern und den Kompetenzkatalog nicht veraendern. Stundenplanreferenzen werden im Adapter und Domain Service aufgeloest und validiert; Widgets greifen nicht direkt auf SQLite zu. Ohne gespeicherte Settings-Zeilen gelten alle aktiven Katalogfaecher als dokumentationsrelevant. Die Auswahl wirkt auf Dokumentationsstand, offene Beobachtungsanlaesse und Beobachtungshinweise; Beobachtungen und Kompetenzhistorien bleiben sichtbar.

## PySide6 Heute / technischer Screen `dashboard`

Liest:

- `timetable_entries` ueber die kanonische zeitpunktparametrisierte Stundenplanprojektion
- `data_groups`
- `data_courses`
- `data_students` fuer vorhandene Schuelerzahlen je Stammgruppe
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`
- `competencies`, `observations`, `observation_competency_ratings` und `student_competency_confirmations` ausschliesslich ueber die kanonische Dokumentationsstatusprojektion

Schreibt:

- nichts direkt
- startet `Beobachtung erfassen`, `Beobachtung aendern` und `Beobachtung loeschen` ueber freigegebene Adapter-/Service-/Repository-Prozesse

UI-Projektionen:

- zentrale Karte `Für diese Stunde` mit aktueller oder naechster aktiver Stunde und ruhigem Leerzustand
- heutige aktive Stunden als horizontale, zeitbezogen markierte Timeline
- fluechtige Stundenplanvorbelegung fuer den bestehenden Beobachtungsdialog nach bewusster Kindauswahl
- neutrale Mini-Heatmap der Dokumentationsabdeckung je Stammgruppe und Fach; keine Bewertung, Leistung, Rangfolge oder Entwicklungsableitung

Regel:

`Heute` ist eine reine Lese- und Navigationsoberflaeche. Der technische Screen und Schluessel `dashboard` bleiben erhalten. Die Ansicht zeigt den aktuellen Stammdaten-Scope der PySide-App, verwaltet weder Stammdaten noch Stundenplan und schreibt nicht direkt in SQLite. Aktuell, naechste und heutige Stunde stammen ausschliesslich aus `TimetableDesktopAdapter.read_projection(at)`. Zeitstatus wird beim Oeffnen beziehungsweise Aktivieren und hoechstens minuetlich neu gelesen. Die Heatmap zaehlt je Stammgruppe und Fach nur Kinder, deren bestehende kanonische Fachprojektion mindestens eine dokumentierte Kompetenz ausweist; sie zeigt keine Ratings, Scores oder automatischen Entwicklungsurteile. Ihre neutralen Blau-Grau-Abstufungen codieren ausschliesslich Dokumentationsabdeckung und keine Ampelbewertung.

Die direkte Kursansicht im Schueler-Arbeitsraum filtert appweit nach der ausgewaehlten `course_id`. Die getrennte Kursverbundansicht bleibt kursverbundbezogen und schraenkt ihren Kursfilter weiterhin zusaetzlich auf die Stammgruppen des ausgewaehlten Kursverbunds ein.

UX-Regel UI Sprint 1: `Heute` und `Schüler` sind die beiden globalen Arbeitsziele. Die Dashboard-Projektionen erscheinen ausschliesslich in einer grossen Hero-Karte, einer horizontalen Tages-Timeline, einer kompakten Stammgruppe-mal-Fach-Matrix und der Karte fuer passenden Unterrichtskontext. Allgemeine Stammgruppen- und Kursverbundkarten gehoeren lokal in den Schueler-Arbeitsraum.

Regel Sprint 8B.3: `Passende Kinder für diese Stunde` liest aktive Kinder aus der zur Stunde gehoerenden Stammgruppe, dem Kurs oder Kursverbund sowie deren aktive Beobachtungen. Es werden hoechstens fuenf Kinder als transparente Dokumentationshilfe projiziert. Reihenfolge und Hinweis beruhen ausschliesslich auf dem Vorhandensein und Datum einer aktiven Beobachtung mit eindeutigem Fachbezug; Ratings, Kompetenzstatus, Leistungswerte und paedagogische Urteile werden nicht gelesen oder berechnet. Der Screen rendert diese Projektion nur und startet `Beobachten` ueber den bestehenden Beobachtungsdialog.

## PySide6 Schueler-Arbeitsraum

Liest die bestehenden Projektionen aus `groups`, `courses`, `students`, `course_groups`, `course_group_student_groups` und `course_group_courses`. Schreibt nichts direkt. `StudentsWorkspace` komponiert die lokalen Segmente `Stammgruppen`, `Kurse`, `Kursverbünde` und `Alle Schüler`, ohne eine neue Datenquelle zu besitzen. Stammgruppenkarten, direkte Kurskarten, Schuelerzahlen, Kursverbuende, Kurszugriffe, Listenfilter und Profilnavigation verwenden ausschliesslich die bestehenden technischen IDs. Ein einfacher Klick auf eine Nicht-Aktionszelle, Enter oder die sekundäre Profilaktion navigiert per `student_id`; eingebettete Zeilenaktionen bleiben davon getrennt. Dashboard-Daten und Stundenplanprojektionen werden in diesem Arbeitsraum nicht gelesen.

Der Workspace darf nur lokale Segment-, Drill-down-, Such-, Fokus- und Auswahlzustaende halten. Beobachtung, Kompetenz, Bericht und LEG bleiben im vorhandenen Schuelerprofilkontext und verwenden ihre bereits dokumentierten Lese- und Schreibpfade. Der Workspace berechnet weder Mitgliedschaften noch Dokumentationsstatus und greift nicht direkt auf SQLite zu.

## PySide6 Stammdaten

Liest:

- `data_groups`
- `data_courses`
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`

Schreibt:

- `groups` ueber `MasterDataDesktopAdapter` und `SQLiteMasterDataRepository`
- `courses` ueber `MasterDataDesktopAdapter` und `SQLiteMasterDataRepository`
- `course_groups` ueber `MasterDataDesktopAdapter` und `SQLiteMasterDataRepository`
- `course_group_student_groups` ueber `MasterDataDesktopAdapter` und `SQLiteMasterDataRepository`
- `course_group_courses` ueber `MasterDataDesktopAdapter` und `SQLiteMasterDataRepository`

UI-Projektionen:

- Stammgruppenliste
- Kursliste
- Kursfarben
- Kursverbundliste
- Bearbeiten-Dialog fuer Kursverbund-Name, Stammgruppen-Auswahl und Kurs-Auswahl

Regel:

Kursverbuende werden persistent in SQLite bearbeitet. Ein Kursverbund definiert, welche Stammgruppen und Kurse in der kursverbundbezogenen Kursuebersicht erscheinen. Die Bearbeitung bucht keine Schueler um und veraendert keine Beobachtungsdaten.

## Legacy: Projection Refresh durch VBA

VBA-Projection-Refresh ist ein historischer Excel-Runtime-Pfad und kein Zielpfad fuer neue Features oder UI-Tests. Falls er in einem ausdruecklichen Legacy-/Export-Auftrag genutzt wird, gelten weiterhin alle folgenden Bedingungen:

- Python hat den fachlichen Command erfolgreich verarbeitet.
- SQLite ist aktualisiert.
- Python hat ein Projection-Refresh-Paket erzeugt.
- VBA kopiert ausschliesslich diesen Projection Output.
- VBA berechnet, sortiert, filtert oder validiert die Projektion nicht selbst.

Diese Aktualisierung ist keine fachliche Tabellenbearbeitung.

Die fachliche Source of Truth bleibt SQLite.

Der Projection Builder bleibt Eigentuemer der Projektion.

## Stammgruppenuebersicht

Liest:

- `data_students`
- `data_groups`
- `data_courses`

Schreibt:

- nichts direkt
- startet `Kompetenzstand bestaetigen` ueber `StudentDesktopAdapter` und `SQLiteStudentCompetencyConfirmationRepository`

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
- `student_competency_confirmations`
- `documentation_subject_settings`
- SQLite `documents` / `data_media`

Schreibt:

- nichts direkt
- startet Dokument-/Medienanlage ueber `StudentDesktopAdapter` und `SQLiteDocumentRepository`

Navigation:

- `student_id`
- `observation_id`
- spaeter `competency_id`

UI-Projektionen:

- Profilkopf
- Stammgruppe
- Kurs
- Beobachtungsverlauf
- lokale Beobachtungsfilter fuer Fach, Bewertung und Suche
- Dokumentationsstand aus aktivem Kompetenzkatalog, aktiven Beobachtungen, bestaetigten Kompetenzstaenden und dokumentationsrelevanten Faechern
- Variante-A-Arbeitsprofil als reine `StudentProfileDashboardViewModel`-Komposition aus der kanonischen Kompetenzstatus- und Dokumentationsstatusprojektion: Profilkopf mit Dokumentationsring, Orientierungskarte, Kompetenzkarte und neutraler Karte `Noch nicht dokumentiert`
- Kompetenz-Cockpit aus der kanonischen Sprint-6B-Statusprojektion mit lokalen Fach- und Dokumentationsfiltern fuer aktive Zeilen sowie separat historischen Kompetenzen
- Berichtsvorschau aus Kompetenzstaenden und Beobachtungsbelegen
- Dokumente und Medien aus aktiven Dokumentmetadaten
- Aktionen zum Bearbeiten und Loeschen einzelner Beobachtungen
- Aktion zum Entfernen einzelner Dokumente ueber Soft Delete
- Aktion zum Bestaetigen oder manuellen Anpassen eines Kompetenzstand-Vorschlags
- Medienhinweise

Regel:

Das Schuelerprofil zeigt Daten eines Schuelers und startet freigegebene Schreibprozesse. Es schreibt selbst keine fachlichen Daten und greift nicht direkt auf SQLite zu. Das Variante-A-Arbeitsprofil wird im Adapter ueber `build_student_profile_dashboard(...)` ausschließlich aus der kanonischen Kompetenzstatusprojektion und der bestehenden Dokumentationsstatusprojektion komponiert. Die Orientierungskarte beruecksichtigt nur reale Beobachtungen und die vorhandene aktuelle Bestaetigung bis zum uebergebenen Stichtag. Eine Kompetenz qualifiziert sich nur mit mindestens zwei realen Ereignissen und einem tatsaechlichen Wechsel zwischen zwei aufeinanderfolgenden dokumentierten Statuswerten. Sie zeigt hoechstens drei Treffer, sortiert nach juengster Statusaenderung und danach curricularer Reihenfolge; historische Snapshot-Texte bleiben lesbar, ohne historische Kompetenzen fuer neue Auswahl zu reaktivieren. Der Screen rendert diese fertige Projektion und berechnet weder Statuswechsel noch Counts. Ohne aktive Filter begrenzt die UI-Projektion den Beobachtungsverlauf auf drei neueste Karten; lokale Beobachtungsfilter wirken auf alle Beobachtungen, aber nur auf den Beobachtungsverlauf und nicht auf das Kompetenz-Cockpit. Die zentrale Leseprojektion `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` erzeugt genau eine Statuszeile je aktiver `current`-Kompetenz sowie je historisch referenzierter Kompetenz. Sie trennt Beobachtungsvorschlag, Bestaetigung und chronologische aktive Nachweise; Soft Deletes bleiben ausgeschlossen. Sprint 6C gruppiert ausschließlich diese kanonischen Zeilen als Fach -> Kompetenzbereich -> Thema -> Kompetenz und aggregiert dokumentiert/gesamt, ohne einen zweiten Kompetenzstatus zu berechnen. Die lokalen Cockpit-Filter beschraenken nur sichtbare aktive Zeilen; sie kombinieren Fach mit dem kanonischen Dokumentationszustand, mutieren keine Daten und behalten die Fortschrittswerte aus dem vollstaendigen aktiven Zielbestand. Alle Cockpit-Ebenen starten geschlossen; der Aufklappzustand bleibt lokal je geoeffnetem Schueler und wird beim Filtern fuer weiterhin sichtbare Ebenen erhalten. Historische Zeilen werden separat unter `Historisch dokumentiert` dargestellt und nicht mit aktiven Zielen gefiltert. Kompetenzstand-Vorschlaege werden aus aktiven Beobachtungen und SQLite `competencies` abgeleitet. Bestaetigte Kompetenzstaende sind paedagogische Entscheidungen und liegen separat in `student_competency_confirmations`. Der Dokumentationsstand ist eine abgeleitete Auswertung aus aktivem `current`-Kompetenzkatalog, aktiven Beobachtungen, bestaetigten Kompetenzstaenden und `documentation_subject_settings`; er zaehlt konkrete Kompetenz-IDs je Fach und Kompetenzbereich, speichert nichts und ist keine Bewertung. Nicht dokumentationsrelevante Faecher zaehlen nicht als offen, bleiben aber in Beobachtungsverlauf, Kompetenz-Cockpit und Berichtsvorschau sichtbar, wenn echte Beobachtungen oder bestaetigte Kompetenzstaende vorliegen. Dokumente und Medien werden aus SQLite `documents` gelesen; Dateien liegen im Dateisystem und werden bei vorhandener `file_path` ueber das Betriebssystem geoeffnet. Die Berichtsvorschau ist eine abgeleitete Struktur aus bestaetigten Staenden, Vorschlaegen und aktiven Beobachtungsbelegen; sie speichert keine Berichtsdaten und erzeugt keine finalen Zeugnisformulierungen. Kopieren und einfacher Textdatei-Export sind Ausgabeaktionen, keine fachliche Persistenz.

## Schuelerverwaltung / PySide-Dialog `Neuer Schüler`

Liest:

- `data_groups`
- `data_courses`

Schreibt:

- `students` in SQLite ueber Desktop Adapter, Dispatcher, Student-Service und Repository
- `data_students` nur als Python-erzeugten Export-/Legacy-Projection Output
- spaeter optional `data_media` ueber freigegebenen Dokumentenprozess

Navigation:

- neuer `student_id` nach erfolgreichem Speichern
- bestehende `group_id`
- bestehende `course_id`
- optional neue `media_id`

UI-Projektionen:

- Eingabefelder Vorname, Nachname, Stammgruppe, Kurs, Notiz
- Dokumentliste
- Dokument-hinzufuegen-Aktion

Regel:

Der PySide-Dialog `Neuer Schüler` ist der aktive Eingabepfad fuer fachliche Schueleranlage. Er schreibt nicht direkt in SQLite, sondern nutzt den Desktop Adapter und den freigegebenen Command-/Service-/Repository-Pfad. Nach App- oder Adapter-Neustart werden gespeicherte Schueler aus SQLite geladen; Demo-Schueler entstehen nur ueber explizite Test-/Seed-Pfade. Der historische `dlg_neuer_schueler`-Pfad bleibt Legacy.

## Beobachtungsdialog

Liest:

- `data_students`
- `data_subjects`
- `data_competencies`
- `documentation_subject_settings` fuer die Fachauswahl neuer Beobachtungen
- `data/curriculum_catalog_v1.csv` ueber den SQLite-Katalogimport als read-only Kataloggrundlage mit `competency_label`, Fach, Kompetenzbereich, Thema und konkreter Kompetenz
- `data_observations` bei Bearbeitung bestehender Beobachtungen
- `data_observation_competencies` bei Bearbeitung bestehender Zuordnungen
- SQLite `documents` / `data_media` fuer Dokumente und Medien

Schreibt:

- SQLite `observations`
- SQLite `observation_competency_ratings`
- SQLite `documents` fuer Beobachtungsanhaenge ueber `StudentDesktopAdapter` und `SQLiteDocumentRepository`
- Export-/Legacy-Projektionen `data_observations` und `data_observation_competencies` nur ueber spaetere Projection Refreshes
- Export-/Legacy-Projektion `data_media` nur ueber spaetere Projection Refreshes

Navigation:

- `student_id`
- `observation_id` bei Bearbeitung
- `competency_id` fuer Zuordnungen

UI-Projektionen:

- ausgewaehlter Schueler
- Fachauswahl
- Kompetenzauswahl mit Fach, Kompetenzbereich, Thema und Kompetenz
- Kurzlabel aus `competencies.label` fuer kompakte Kompetenzauswahl
- Hierarchische Kompetenzprojektion aus `StudentDesktopAdapter.list_observation_competency_subject_groups(initial_draft)` fuer die Dialogdarstellung
- `catalog_status` und `is_active` aus derselben Adapterprojektion fuer Angebot und dezente historische Kennzeichnung
- Lokaler Suchtext und Trefferanzeige über Kurzlabel, Kompetenztext, Thema und Kompetenzbereich aus derselben Adapterprojektion; nur aktive `current`-Kompetenzen sind neue Suchtreffer
- Fachbezogene Schnellauswahl aus `StudentDesktopAdapter.list_recent_observation_competencies(student_id, initial_draft)`: maximal vier eindeutige aktive `current`-Kompetenzen aus den neuesten aktiven Beobachtungen des Schuelers; bei Suchtext vollstaendig ausgeblendet und nach erfolgreichem Speichern erneut aus SQLite projiziert
- Beobachtungsnotiz
- Schnellbeobachtungsmodus als fluechtige Eingabe; beim Bearbeiten aus aktiver Beobachtung mit nichtleerer Notiz und ohne Kompetenzbewertungen rekonstruiert
- Kontext
- Bewertung/Zuordnung
- Dokumente und Medien

Regel:

Der Beobachtungsdialog ist der freigegebene Schreibprozess fuer Erfassung und Bearbeitung von Beobachtungen. Die produktive Drei-Zonen-Arbeitsflaeche rendert ausschliesslich die Adapterprojektion; der Dialog baut keine eigene Fallback-Hierarchie aus Katalogdaten. Neue Beobachtungen bieten in der Fachauswahl nur dokumentationsrelevante aktive Faecher und im Katalog nur aktive `current`-Kompetenzen an. Bei Bearbeitung wird eine bestehende `observation_id` geladen; ein inzwischen nicht dokumentationsrelevantes Bestandsfach sowie bereits bewertete `legacy`- oder inaktive Kompetenzen bleiben sichtbar und werden nicht automatisch ersetzt. Speichern ersetzt die Kompetenzbewertungen atomar. Kompetenzen muessen im Beobachtungsdialog zwingend mitgedacht werden. Die sichtbare Kompetenzstruktur lautet Fach -> Kompetenzbereich -> Thema -> Kompetenz und nutzt bestehende Felder: `subject_id` / `subject_name`, `learning_area`, `competency_group`, `description` / `competency_text`.

Sprint 3C stellt diese Struktur als additive ViewModel-/Adapterprojektion bereit. Sprint 3D rendert die Kompetenzauswahl hierarchisch. Sprint 5C uebernimmt die freigegebene Drei-Zonen-UX produktiv: Neu-Erfassung startet vollstaendig geschlossen, Bearbeitung oeffnet ausschliesslich Zweige mit bereits bewerteten Kompetenzen, und Auswahl sowie Einzelbewertungen bleiben bei Fachwechsel oder Einklappen erhalten. Sprint 5D filtert diese bestehende Projektion ausschließlich lokal im Dialog; Suche und Treffer-Öffnung verändern weder Auswahl noch Bewertung oder Persistenz und das Löschen der Suche stellt den Aufklappzustand vor der Suche wieder her. Sprint 5E ergänzt darunter eine reine Adapterprojektion der zuletzt verwendeten Kompetenzen; die Dialogauswahl ändert deren Reihenfolge oder Inhalt nicht.

Dokumente und Medien sind nur Anhaenge zur Beobachtung und ersetzen keine Beobachtungsdaten. Sie gehoeren immer zum Schueler und tragen optional die `observation_id`.
Der PySide-Dialog schreibt nicht direkt in SQLite, sondern ueber Adapter, Command, Service und Repository. Jede ausgewaehlte Kompetenz speichert ihre eigene Bewertung in `observation_competency_ratings.rating`. `offen` ist kein gespeicherter Ratingwert; wenn eine Kompetenz nicht bewertet wird, wird keine Zuordnungszeile gespeichert. Nur eine bewusst aktivierte Schnellbeobachtung darf ganz ohne Kompetenzbewertungen gespeichert werden; sie braucht eine nichtleere Notiz und bleibt fuer Kompetenzstatus- und Fortschrittsprojektionen ohne Wirkung.

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
- Fach, Kompetenzbereich und Thema
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
- `student_competency_confirmations`
- `data_media`
- `data_settings`

Schreibt im aktuellen Produktstand:

- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`

Navigation:

- `student_id`
- `course_id`
- `group_id`
- `competency_id`

UI-Projektionen:

- Lernentwicklungsbericht
- Beobachtungszusammenfassung
- Kompetenzdarstellung
- strukturierte Berichtsvorbereitung

Regel:

Die bestehende Berichtsvorschau ist eine Live-Auswertungsprojektion. Sie speichert keine fachlichen Ergebnisdaten. Sie darf bestaetigte Kompetenzstaende, klar getrennte berechnete Vorschlaege und aktive Beobachtungen strukturieren sowie als einfachen Text kopieren oder exportieren. Sie erzeugt keine fertigen paedagogischen Aussagen, keine finalen Zeugnisformulierungen und keinen PDF-/Word-Export.

Sprint 7F.1 ergaenzt einen persistenten, weiter bearbeitbaren Berichtsentwurf. Die Berichtswerkstatt liest und schreibt ihn ausschliesslich ueber ViewModel, Application Layer und `SQLiteReportDraftRepository`. Gespeichert werden Dokumentkontext, manuelle Gesamt- und Fachtexte sowie bewusste Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen. Kompetenzzustaende stammen weiterhin ausschliesslich aus der kanonischen Sprint-6-Projektion; Kompetenz- und Beobachtungsinhalte werden nicht in den Entwurf kopiert. Aktive `current`-Kompetenzen sind fuer neue Auswahl vorgesehen. Beim Wiedereroeffnen werden gespeicherte Kompetenz-IDs als `retained_competency_ids` an dieselbe Projektion uebergeben, sodass spaeter deaktivierte oder historische Referenzen gekennzeichnet ausgewaehlt bleiben, ohne erneut angeboten zu werden. Gespeicherte, spaeter soft-geloeschte Beobachtungs-IDs bleiben als nicht verfuegbare Referenzen sichtbar und werden nur durch ausdrueckliche Abwahl entfernt; Inhalte werden nicht rekonstruiert. Der Entwurf ist keine finale Berichtsdomain und besitzt weder Freigabe, Versionierung, Archivierung noch eingefrorene Ausgabe.

Sprint 7F.2 portiert die freigegebene UX aus `prototypes/learning_report_ux/` auf diese bestehende Ownership. Die PySide-Berichtswerkstatt besitzt ausschliesslich lokalen Widgetzustand fuer die laufende Bearbeitung und delegiert Speichern ueber `LearningReportDraftViewModel` an den Desktop-Adapter. Beim Oeffnen laedt die Shell den zuletzt aktualisierten Entwurf des Schuelers vor der Berichtsvorbereitung, damit dessen gespeicherte Kompetenzreferenzen den Lesekontext bilden. Die separate Vorschau baut ihr `ReportOutputModel` aus dem aktuellen Entwurf und den vorhandenen Leseprojektionen; sie ist keine Datenquelle. Fachseiten duerfen nur Kompetenzen des jeweiligen Fachs und nur dazu passende Beobachtungsbelege neu anbieten. Nicht verfuegbare gespeicherte Belege werden in Qt-Vorschau und Ausgabemodell getrennt von regulaeren Belegen neutral ausgewiesen. Diagramme werden nur als gespeicherte Auswahlreferenzen gehalten; ihre Daten werden bei Vorschau und PDF aus den vorhandenen Projektionen erzeugt.

Aktueller produktiver Stand: Die PDF-Ausgabe liest ausschliesslich ein neutrales `ReportOutputModel`, das fuer die Vorschau aus dem Berichtsentwurf und den freigegebenen Leseprojektionen aufgebaut wird. Sie greift weder direkt auf SQLite zu noch berechnet oder interpretiert sie fachliche Inhalte. Dieses Modell ist im Draft-Prozess noch kein eingefrorener oder freigegebener Berichtstand.

Sprint 5B.2 ergaenzt ohne neue Ansicht einen reinen Backend-Schreib- und Lesepfad fuer finale Berichtrevisionen. `ReportFinalizationService` darf den vorhandenen `RPD`, dessen normalisierte Auswahlrelationen sowie die registrierten Schueler-, Kompetenz-, Beobachtungs- und bestaetigten Statusquellen lesen. `SQLiteLearningReportRepository` ist alleiniger Schreiber von `learning_reports` und `learning_report_revisions`. Der persistierte fachliche Snapshot ist historische Source of Truth; weder Berichtswerkstatt noch aktuelle Draft-Vorschau noch `ReportOutputModel` besitzen oder veraendern bestehende Revisionen. Es gibt in diesem Sprint keine UI-Aktion, keine neue UI-Projektion und keine PDF-Artefaktansicht.

Aktueller Revisionsstand: Ein finalisierter Bericht ist mit `RPT` und `RPV` als eigene fachliche Entitaet umgesetzt. Der fachliche Snapshot friert Schuelerbezug, Berichtszeitraum, verantwortlichen Anzeigenamen, manuelle Texte, ausgewaehlte Kompetenzinformationen, ausgewaehlte Beobachtungsbelege und Diagrammdaten ein. Eine finale Ausgabeversion beziehungsweise PDF-Artefaktverwaltung fehlt weiterhin; der bestehende reine Renderer erhaelt in diesem Sprint noch kein neues Eingangsmodell.

Sprint 5B.3 bindet den vorhandenen Revisionspfad produktiv an die Berichtswerkstatt an. Die Werkstatt liest Status, aktuelle Revision und neueste-zuerst sortierte Historie ausschliesslich ueber `StudentDesktopAdapter`, `ReportRevisionApplicationService`, `LearningReportRevisionReadService` und `SQLiteLearningReportRepository`. Der zentrale Leseservice erzeugt fuer die Aenderungserkennung einen vollstaendig validierten deterministischen Finalisierungskandidaten und vergleicht dessen SHA-256 mit der aktuellen Revision; Widgets besitzen keine Snapshot-, Hash- oder Repositorylogik. Finalisierung speichert ungespeicherte Draftaenderungen zuerst und verwendet danach den bestehenden transaktionalen Schreibpfad.

Die `LearningReportRevisionDialog` besitzt ausschliesslich die bereits snapshotbasierte `LearningReportRevisionViewModel`-Projektion. Deren einzige fachliche Inhaltsquelle sind `snapshot_json`, Revisionsmetadaten und gespeicherter Hash. Sie darf keine aktuellen Schueler-, Gruppen-, Kurs-, Kompetenz-, Beobachtungs- oder Diagrammdaten nachladen und bietet keine Schreib-, Loesch-, Entsperr- oder Wiederherstellungsaktion. Die Projektion adaptiert den Snapshot getrennt vom Live-Draft an den renderer-neutralen `ReportOutputModel`-Vertrag.

Sprint 9A erlaubt in dieser Ansicht fuer die aktuelle `finalized`-Revision ausschliesslich die Aktion `Finales PDF erstellen`. Das Widget uebergibt nur die `RPV`-ID. `StudentDesktopAdapter`, `LearningReportPdfApplicationService`, `LearningReportPdfService` und `SQLiteLearningReportPdfArtifactRepository` pruefen Status und Snapshot, erzeugen das PDF aus dem snapshotbasierten `ReportOutputModel` und speichern die unveraenderliche `RPA`-Referenz. Die UI kennt weder Pfadpolicy, Hashberechnung, Renderer noch SQLite. Supersedierte Revisionen koennen vorhandene historische Inhalte weiterhin anzeigen, aber kein neues finales Artefakt erzeugen.

## Lernentwicklungsgespraech

Liest in der spaeteren Zielarchitektur:

- kanonische Kompetenzprojektion
- zeitraumbezogene Evidenzprojektion
- Schueler-, Gruppen- und Kurskontext
- freigegebene historische Kompetenzinformationen

Schreibt ab Sprint 7G.1 ueber den freigegebenen Draft-Pfad:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Konzeptionelle Projektionen:

- Gespraechsvorbereitung
- Gespraechsschwerpunkte
- relevante Evidenz
- Ziele
- Vereinbarungen
- Gespraechsergebnis

Regel:

Ein Lernentwicklungsgespraech ist kein Bericht. Automatisch abgeleitete Uebersichten, Kompetenzstatus, moegliche Schwerpunkte und Evidenzhinweise bleiben Live-Projektionen. Sprint 7G.1 speichert ausschliesslich den eigenen bearbeitbaren LEG-Arbeitsentwurf: manuelle Inhalte, bewusste Fach-/Themenauswahl und stabile Kompetenz-/Beobachtungsreferenzen. Der Draft greift nur ueber ViewModel, `StudentDesktopAdapter`, Application Service, Domain Service und Repository auf SQLite zu. Er kopiert keine Kompetenz- oder Beobachtungsfachdaten und veraendert keine kanonische Projektion. Spaeter soft-geloeschte Beobachtungsreferenzen werden kontrolliert als nicht verfuegbar angezeigt und nicht ersetzt. Der Entwurf ist nicht final, nicht versioniert, nicht archiviert und nicht freigegeben.

Sprint 7G.2 portiert `prototypes/learning_conference_ux/` als produktive PySide-Ansicht. `LearningConferenceDialog` besitzt nur den Widgetzustand der laufenden Bearbeitung und baut daraus ein `LearningConferenceDraftViewModel`; die Shell delegiert Speichern an `StudentDesktopAdapter`. Vorbereitung und Gespraechsmappe lesen denselben aktuellen Draftzustand, bleiben visuell getrennt und sind keine eigenen Datenquellen. Kompetenzstatus ist eine nicht editierbare Anzeige der kanonischen Sprint-6-Projektion. Quick Observations bleiben reine Textbelege, nicht verfuegbare gespeicherte Beobachtungsreferenzen sichtbar und Diagramme speichern ausschliesslich ihren Typ.

Sprint 7G.3 schraenkt nur die sichtbare Kompetenzwahl ein. Die bestehende kanonische Projektion liefert aktive kindbezogene Kompetenznachweise und aktuelle Bestaetigungen; das LEG-ViewModel reicht deren Datums- und Vorhandenseinsreferenzen weiter. Der Dialog zeigt bei vollstaendigem Zeitraum Beobachtungsreferenzen innerhalb dieses Zeitraums, ohne vollstaendigen Zeitraum alle kanonisch beruecksichtigten Kompetenzbeobachtungen. Aktuelle Bestaetigungen bleiben zeitraumunabhaengig sichtbar. Bereits im Draft ausgewaehlte IDs werden nie automatisch entfernt und duerfen als expliziter Lesekontext auch historische Katalogzeilen in derselben Projektion aufloesbar halten. Schnellbeobachtungen, fremde oder soft-geloeschte Beobachtungen gelangen nicht in diese kanonischen Kompetenznachweise. Der lokale Filter ist keine Datenquelle und keine zweite Statuslogik.

UI Sprint 6B komponiert dieselbe Ownership als Sechs-Phasen-Workspace neu. `LearningConferenceDialog` besitzt nur fluechtigen aktiven Phasen-, Fokus-, Scroll- und Dirty-State. Phase 1 bearbeitet den bestehenden Gespraechsrahmen und die Schwerpunktreferenzen; Phase 2 bis 4 ordnen vorhandene manuelle Texte nach Vorbereitung, gemeinsamem Gespraech und Draft-Vereinbarung; Phase 5 bearbeitet die bestehenden Kompetenz-, Beobachtungs- und Diagrammreferenzen; Phase 6 bearbeitet Unterstuetzung und Vereinbarungen. Ausserhalb von Phase 5 ist die Belegzusammenfassung rein lesend. Kursname, Stammgruppe und Kindname bleiben Live-Projektionen der vorhandenen Schuelerquelle. Phasenwechsel, Suche, Disclosure und Dirty-Ermittlung schreiben nichts; ausschliesslich `Entwurf speichern` delegiert weiterhin den vollstaendigen Draft ueber `StudentDesktopAdapter` an den bestehenden Schreibpfad.

Sprint 10A ergaenzt neben diesem Draftpfad eine eigene Abschlussownership. `LearningConferenceDialog` sendet fuer den expliziten Abschluss nur die gespeicherte LCD-ID. `StudentDesktopAdapter` delegiert an `LearningConferenceCompletionApplicationService`, LEG-Domainvalidierung und `SQLiteLearningConferenceRepository`. Snapshotbildung, kanonische Serialisierung, SHA-256 und atomare LCF-/LCV-Persistenz liegen vollstaendig ausserhalb von UI und ViewModel.

Die Revisionshistorie ist eine Lesesicht auf `learning_conference_revisions`. `LearningConferenceRevisionDialog` besitzt ausschliesslich `LearningConferenceRevisionViewModel`, das zuvor durch `LearningConferenceRevisionReadService` aus einem hashverifizierten Snapshot gebildet wurde. Die Ansicht darf weder aktuelle Stammdaten noch Kompetenz-/Beobachtungsprojektionen nachladen. Der LCD bleibt unabhaengig von vorhandenen LCVs bearbeitbar; seine Live-Projektionen und die historische Snapshotansicht sind bewusst getrennte Sources of Truth.

Sprint 10B erlaubt in dieser Ansicht fuer die aktuelle `completed`-Revision ausschliesslich die Artefaktaktion `Finales PDF erstellen`. Das Widget uebergibt nur die LCV-ID. Adapter, Application Service, LEG-PDF-Domain und Artefakt-Repository validieren Revision und Snapshot, bauen die Ausgabe ausschliesslich aus dem LCV-Snapshot und speichern die unveraenderliche `LCA`. Die UI kennt weder Renderer, Pfadpolicy, Hashberechnung noch SQLite. `superseded`-Revisionen bleiben lesbar, bieten aber keine neue PDF-Erzeugung.
