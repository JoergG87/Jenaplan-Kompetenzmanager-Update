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

## PySide6 Uebersicht `Stammgruppen und Schülerbestand`

Liest:

- `data_groups`
- `data_courses`
- `data_students` fuer vorhandene Schuelerzahlen je Stammgruppe
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`

Schreibt:

- nichts direkt
- startet `Beobachtung erfassen`, `Beobachtung aendern` und `Beobachtung loeschen` ueber freigegebene Adapter-/Service-/Repository-Prozesse

UI-Projektionen:

- Stammgruppenliste
- optionale Schueleranzahl fuer persistent bekannte Stammgruppen
- Kursverbundliste
- Kursliste innerhalb eines persistenten Kursverbunds
- Kursmarker aus Kursfarbe
- Kursfilter aus `course_id` und den Stammgruppen des Kursverbunds

Regel:

Die Uebersicht zeigt den aktuellen Stammdaten-Scope der PySide-App. Sie verwaltet keine Stammdaten und schreibt nicht direkt in SQLite.

Eine Kursuebersicht ist kursverbundbezogen. Sie zeigt nicht automatisch alle Schueler mit demselben Kurslabel in der ganzen App, sondern filtert nach `course_id` und den Stammgruppen des ausgewaehlten Kursverbunds.

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
- Dokumentationsstand aus aktivem Kompetenzkatalog, aktiven Beobachtungen und bestaetigten Kompetenzstaenden
- Kompetenzuebersicht aus beobachteten Kompetenzen
- Berichtsvorschau aus Kompetenzstaenden und Beobachtungsbelegen
- Dokumente und Medien aus aktiven Dokumentmetadaten
- Aktionen zum Bearbeiten und Loeschen einzelner Beobachtungen
- Aktion zum Entfernen einzelner Dokumente ueber Soft Delete
- Aktion zum Bestaetigen oder manuellen Anpassen eines Kompetenzstand-Vorschlags
- Medienhinweise

Regel:

Das Schuelerprofil zeigt Daten eines Schuelers und startet freigegebene Schreibprozesse. Es schreibt selbst keine fachlichen Daten und greift nicht direkt auf SQLite zu. Ohne aktive Filter begrenzt die UI-Projektion den Beobachtungsverlauf auf drei neueste Karten; lokale Beobachtungsfilter wirken auf alle Beobachtungen, aber nur auf den Beobachtungsverlauf und nicht auf die Kompetenzuebersicht. Kompetenzstand-Vorschlaege werden aus aktiven Beobachtungen und SQLite `competencies` abgeleitet. Bestaetigte Kompetenzstaende sind paedagogische Entscheidungen und liegen separat in `student_competency_confirmations`. Der Dokumentationsstand ist eine abgeleitete Auswertung aus aktivem Kompetenzkatalog, aktiven Beobachtungen und bestaetigten Kompetenzstaenden; er speichert nichts und ist keine Bewertung. Dokumente und Medien werden aus SQLite `documents` gelesen; Dateien liegen im Dateisystem und werden bei vorhandener `file_path` ueber das Betriebssystem geoeffnet. Die Berichtsvorschau ist eine abgeleitete Struktur aus bestaetigten Staenden, Vorschlaegen und aktiven Beobachtungsbelegen; sie speichert keine Berichtsdaten und erzeugt keine finalen Zeugnisformulierungen. Kopieren und einfacher Textdatei-Export sind Ausgabeaktionen, keine fachliche Persistenz.

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
- `data/curriculum_catalog_v1.csv` im PySide6-Dialog als read-only Kataloggrundlage
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
- Kompetenzauswahl
- Beobachtungsnotiz
- Kontext
- Bewertung/Zuordnung
- Dokumente und Medien

Regel:

Der Beobachtungsdialog ist der freigegebene Schreibprozess fuer Erfassung und Bearbeitung von Beobachtungen. Bei Bearbeitung wird eine bestehende `observation_id` geladen; Speichern ersetzt die Kompetenzbewertungen atomar. Kompetenzen muessen im Beobachtungsdialog zwingend mitgedacht werden.

Dokumente und Medien sind nur Anhaenge zur Beobachtung und ersetzen keine Beobachtungsdaten. Sie gehoeren immer zum Schueler und tragen optional die `observation_id`.
Der PySide-Dialog schreibt nicht direkt in SQLite, sondern ueber Adapter, Command, Service und Repository. Jede ausgewaehlte Kompetenz speichert ihre eigene Bewertung.

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
- `student_competency_confirmations`
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
- strukturierte Berichtsvorbereitung

Regel:

Berichte sind Ausgabeprojektionen. Sie speichern keine fachlichen Ergebnisdaten. Eine Berichtsvorschau darf bestaetigte Kompetenzstaende, berechnete Vorschlaege und aktive Beobachtungen strukturieren sowie als einfacher Text kopiert oder exportiert werden. Sie erzeugt keine KI-Texte, keine finalen Zeugnisformulierungen und keinen PDF-/Word-Export.
