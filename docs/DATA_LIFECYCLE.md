# Data Lifecycle

Dieses Dokument beschreibt freigegebene oder geplante Schreibprozesse fuer fachliche Daten.

Kein Schreibprozess darf implementiert werden, bevor sein Lebenszyklus hier dokumentiert ist.

## macOS-Pilotstart und lokale Datenordner

Start: Die installierte `.app` wird fuer einen macOS-Benutzer geoeffnet.

Technischer Pfad:

```text
PySide Entry Point
-> RuntimePaths / sichere Ordnerpruefung
-> vorhandene Benutzerdatenbank oder einmalige Initialisierung
-> bestehende Adapter-/Repository-/SQLite-Initialisierung
```

Die App legt bei Bedarf den Benutzerordner sowie `documents/`, `exports/`, `backups/` und `logs/` an. Eine vorhandene `kompetenzmanager.sqlite` wird nie durch Bundleinhalte ersetzt. Die technische Smoke-Test-Variante `empty` enthaelt keine Startdatenbank und laesst den vorhandenen produktiven Initialisierungspfad eine leere Schuelerdatenbasis mit Stammdaten- und Katalogdefaults anlegen.

Nur die explizite Buildvariante `laura` darf beim ersten Start eine als `Fiktive Pilotdaten` markierte Datenbank und ihre zugehoerigen Dokumente und Beispiel-PDFs kopieren. Dies geschieht ausschliesslich, wenn noch keine Benutzerdatenbank existiert; vorhandene Dokumente blockieren eine kollidierende Ersteinrichtung statt still ersetzt zu werden. Der Entwicklerstart bleibt bei `data/kompetenzmanager.sqlite`.

## Technisches macOS-Pilotbackup

Start: Die Lehrkraft hat die App vollstaendig geschlossen und startet bewusst `PILOT_BACKUP.sh`.

Schreibprozess:

```text
Prozesspruefung
-> SQLite Online-Backup der geschlossenen lokalen Datenbank
-> Kopie des verwalteten documents/-Baums
-> neuer backups/YYYYMMDD-HHMMSS/-Ordner
```

Eine vorhandene Sicherung wird nie ueberschrieben. Das Skript aendert weder Benutzerdatenbank noch Dokumente und fuehrt keine Wiederherstellung aus. Eine technische Wiederherstellung bleibt ein separater, manuell gepruefter Eingriff.

## Verifiziertes Anwendungsbackup erstellen und pruefen

Start: Ein expliziter Application-Command erhaelt Datenbankpfad, vollstaendige `RuntimePaths`, Zielordner, Buildinformationen und UTC-Zeitquelle. In Sprint 0.2A.2 existiert dafuer noch keine sichtbare UI und kein automatischer Ausloeser.

Technischer Prozess:

```text
CreateBackupCommand
-> BackupApplicationService
-> BackupService
-> SQLiteBackupEngine / sqlite3.Connection.backup()
-> Snapshot integrity_check + foreign_key_check
-> BackupInventoryService liest ausschliesslich den Snapshot
-> verwaltete Dateien stabil kopieren und SHA-256 bilden
-> kanonisches Manifest v1 und ZIP-Stagingdatei schreiben
-> BackupVerifier prueft das geschlossene Archiv isoliert erneut
-> flush / fsync / atomare exklusive Veroeffentlichung
```

Der Prozess liest die Live-Datenbank kontrolliert und schreibt niemals in sie. Er kopiert keine laufende SQLite-Datei, keine `-wal`- oder `-shm`-Datei und verwendet keinen externen SQLite-Prozess. Bei einer laenger blockierten Transaktion endet das begrenzte Warten mit `BackupBusyError`.

Das Inventar stammt aus dem Snapshot. Registrierte Dokumente innerhalb `RuntimePaths.documents` werden aktiv wie soft-deaktiviert aufgenommen. Finale Bericht- und LEG-PDF-Artefakte werden aufgenommen und ihre gespeicherten Groessen und SHA-256-Hashes gegen die tatsaechlichen Dateien geprueft. Fehlende, veraenderte, verlinkte oder besondere verwaltete Dateien, unbekannte Nutzdateien unter `documents/` sowie Hashabweichungen brechen den gesamten Prozess ab. Externe Dokumentreferenzen werden nur gezaehlt und nie kopiert.

Verwaltete Dateien werden relativ zu einem geoeffneten `documents`-Directory-FD gelesen. Jede Pfadkomponente wird ohne Symlink-Folgen geoeffnet; Geraet, Inode, Dateityp, Groesse und Aenderungszeit muessen vom Inventar bis nach dem Streaming identisch bleiben. Ein Parent-Verzeichnis-Austausch oder ein Endkomponenten-Symlink kann dadurch keine externe Datei in das Backup umlenken.

Bei jedem Fehler werden temporaeres Archiv und Staging entfernt; vorhandene Backups bleiben unveraendert und es entsteht kein Erfolgsergebnis. Bei der exklusiven Veroeffentlichung darf der finale Pfad nur entfernt werden, wenn genau dieser Aufruf den Hardlink zuvor selbst erfolgreich erzeugt hat. Der abschliessende Verifier prueft ZIP-Struktur und CRC, Pfadsicherheit und macOS-Namenskollisionen, Limits vor und waehrend der Extraktion, Manifestversion, Datenbank- und Dateihashes, SQLite-Integritaet, Fremdschluessel, Schema-Fingerprint, Counts und vollstaendiges Inventar in einem isolierten temporaeren Verzeichnis.

Der Packaged-App-Smoke validiert vor `prepare_runtime_storage()` einen expliziten Smoke-Marker und eine eigene temporaere Datenwurzel. Fehlt eine der beiden unabhaengigen Bedingungen, endet der Start ohne Anlegen von Runtime-Verzeichnissen, Datenbank, PDF oder Backup.

Dieser Lifecycle veraendert keine fachlichen Daten. Restore, Vorschau, Migration, automatische Sicherung, Aufbewahrung, Verschluesselung, Signierung, Passwortschutz, Nutzerkonto, Import, Onboarding und Cloud sind nicht freigegeben.

## Datenbankschema V1 initialisieren und Kompatibilitaet pruefen

Start: Die bestehende SQLite-Initialisierung oeffnet eine neue oder vorhandene lokale Datenbank.

Technischer Prozess fuer eine schemafreie Datenbank:

```text
SQLiteDatabase.initialize_schema()
-> vor Schemaerzeugung keine nicht-internen Schemaobjekte festgestellt
-> BEGIN IMMEDIATE
-> vollstaendiges V1-Schema erzeugen
-> PRAGMA user_version = 1
-> COMMIT
```

Eine vorhandene Datenbank mit nicht-internen Schemaobjekten und `user_version = 0` bleibt beim normalen Start unversioniert. Sie wird weder als V1 adoptiert noch in-place migriert. Der bestehende fachliche Betrieb bleibt davon getrennt. `DatabaseCompatibilityInspector` liest Version und vollstaendigen Schemafingerprint ausschliesslich read-only; `DatabaseCompatibilityPolicy` klassifiziert exaktes V1 als `EXACT`, den registrierten unversionierten `c029aff`-Vorgaenger als `MIGRATION_REQUIRED` und unbekannte oder neuere Staende als `INCOMPATIBLE`.

## Restore-Backup technisch verifizieren und Vorschau erzeugen

Start: Eine explizite `VerifyRestoreBackupQuery` uebergibt den Pfad eines bestehenden `.jkmbackup`. Es gibt keinen sichtbaren UI-Ausloeser.

```text
VerifyRestoreBackupQuery
-> RestoreApplicationService
-> RestoreVerifier
-> BackupVerifier
-> Archivgroesse und SHA-256 erneut binden
-> sichere isolierte temporaere Extraktion
-> Datenbank read-only oeffnen
-> Manifest- und Datenbankversion vergleichen
-> vollstaendigen Kompatibilitaetsfingerprint und Status bestimmen
-> integrity_check / foreign_key_check
-> Counts und Managed Files pruefen
-> datensparsame RestorePreview erzeugen
-> temporaeres Verzeichnis vollstaendig entfernen
```

Der Prozess veraendert weder die Kandidatendatenbank noch Live-Daten oder Managed Files und fuehrt keine Migration aus. Ein Widerspruch zwischen Manifest und tatsaechlicher Datenbankversion, ein unbekannter Fingerprint, eine neuere Datenbank, Integritaets- oder Fremdschluesselfehler, falsche Counts oder fehlende beziehungsweise veraenderte Managed Files fuehren zu einem typisierten Fehler ohne Ergebnis. Es bleiben keine Stagingdaten zurueck.

Nicht Bestandteil dieses Lifecycles sind persistentes Restore-Staging, Pfad-Rebasing, Sicherheitsbackup, Worker, Austausch, Rollback, Journal, Start-Recovery, Neustart oder UI.

## Dokumentationsrelevante Faecher speichern

Start: Laura legt in den Einstellungen fest, welche Faecher fuer spaetere Dokumentations- und Auswertungslogik zaehlen sollen.

Schreibprozess: Dokumentationskonfiguration ueber Settings-UI, Desktop Adapter und SQLite-Repository. Ab Sprint 2C wird die Auswahl lesend in Dokumentationsauswertungen angewendet.

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

- Schuelerlisten-Dokumentationsstatus
- Schuelerprofil-Dokumentationsstand
- offene Kompetenzen / Beobachtungsanlaesse
- Beobachtungshinweise im Halbjahresblick
- Berichtsvorbereitung, falls sie Dokumentationsstatus oder offene Kompetenzen nutzt

Regel: Die Speicherung ersetzt die vollstaendige Auswahl in `documentation_subject_settings`. Wenn keine Settings-Zeilen vorhanden sind, bleibt das bisherige Verhalten erhalten: alle aktiven Katalogfaecher aus `competencies.active = 1` gelten als dokumentationsrelevant. Die Einstellung loescht keine Beobachtungen, veraendert keine Kompetenzdefinitionen und nutzt `competencies.active` nicht als Einstellungsfeld. Nicht dokumentationsrelevante Faecher bleiben in Beobachtungslisten, Kompetenzhistorien und bestaetigten Kompetenzstaenden sichtbar, zaehlen aber nicht als offen im Dokumentationsstand oder in offenen Beobachtungsanlaessen.

## Stundenplaneintrag pflegen

Start: Laura legt in den Einstellungen einen Stundenplaneintrag an, bearbeitet, aktiviert, deaktiviert oder loescht ihn.

Freigegebener PySide-Pfad:

```text
PySide6 SettingsScreen / TimetableEntryDialog
-> TimetableDesktopAdapter
-> TimetableApplicationService
-> TimetableService / TimetableValidator
-> SQLiteTimetableRepository
-> SQLite timetable_entries
```

Betroffene Datenquellen:

- SQLite `timetable_entries` schreibend
- SQLite `competencies` lesend zur Aufloesung und Validierung vorhandener `subject_id`
- SQLite `groups`, `courses` und `course_groups` lesend zur zielartgerechten Validierung von `target_id`

Erforderliche IDs:

- neue oder bestehende `timetable_entry_id`
- bestehende `subject_id`
- bestehende, zu `target_type` passende `target_id`

Regel: Anlegen und Aendern validieren Zeitbereich, Referenzen und aktive Ueberschneidungen vor dem Schreiben. Aktivieren durchlaeuft dieselben Regeln. Loeschen markiert nur den ausdruecklich gewaehlten Stundenplaneintrag mit `deleted_at` und deaktiviert ihn; bestehende Stammdaten und Stundenplan-IDs bleiben unveraendert und geloeschte IDs werden nicht wiederverwendet. Die Leseprojektion speichert nichts und berechnet aktuelle, naechste und heutige Stunden ausschliesslich aus aktiven, nicht geloeschten Eintraegen und einem explizit uebergebenen Zeitpunkt.

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
- SQLite `documentation_subject_settings` nur lesend fuer die Fachauswahl
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

Regel: Beobachtung ist Source of Truth. Auswertungen leiten sich daraus ab. Die Schnellauswahl im Beobachtungsdialog ist eine nicht schreibende Adapterprojektion aus bereits aktiven Beobachtungen und ihren Kompetenzbewertungen: nur aktive `current`-Kompetenzen, je Schueler und Fach maximal vier eindeutige Eintraege, neueste zuerst. Sie erzeugt keine Tabelle, keine Historie und keine zusaetzliche Persistenz und wird nach erfolgreichem Speichern neu abgeleitet.
Neue Beobachtungen koennen nur mit dokumentationsrelevanten aktiven Faechern aus der aktuellen Settings-Auswahl angelegt werden; ohne Settings-Zeilen gilt der aktive Katalog. Die Kompetenzauswahl bietet dabei ausschliesslich aktive `current`-Kompetenzen an. Beobachtung und Kompetenzbewertungen werden atomar gespeichert; eine Bewertung gehoert zur konkreten Kompetenz, nicht global zur Beobachtung. Die sichtbare Struktur lautet Fach -> Kompetenzbereich -> Thema -> Kompetenz und wird ueber vorhandene Felder abgebildet: `subject_id` / `subject_name`, `learning_area`, `competency_group`, `description` / `competency_text`. `offen` ist kein gespeicherter Ratingwert; eine nicht bewertete Kompetenz erzeugt keine Zeile in `observation_competency_ratings`. Eine bewusst aktivierte Schnellbeobachtung darf ohne Kompetenzbewertungen gespeichert werden, wenn `note` nach dem Trimmen nicht leer ist. Sie erzeugt keine Zeile in `observation_competency_ratings` und wirkt deshalb nicht auf kompetenzbezogene Projektionen. Medien/Anhaenge und Berichte bleiben im bestehenden separaten Prozess.

## Beobachtung aendern

Start: Lehrkraft korrigiert eine bestehende Beobachtung im Schuelerprofil.

Schreibprozess: PySide-Schuelerprofil oeffnet den Beobachtungsdialog mit `observation_id`; Speichern laeuft ueber `StudentDesktopAdapter`, `observation.update`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`
- SQLite `documentation_subject_settings` nur lesend fuer die Fachauswahl
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

Regel: `observation_id` bleibt erhalten. Beobachtungsfelder werden aktualisiert; Kompetenzbewertungen werden fuer die Beobachtung atomar ersetzt. Die Fachanzeige wird weiter aus den Kompetenzfaechern abgeleitet. Wenn das gespeicherte Fach inzwischen nicht dokumentationsrelevant ist, bleibt es beim Bearbeiten sichtbar und wird nicht automatisch ersetzt oder entfernt. Bereits bewertete `legacy`- oder inaktive Kompetenzen bleiben mit ihrer gespeicherten `competency_id`, Hierarchie, ihrem Text und Rating sichtbar, bewertbar und entfernbar; es erfolgt keine Ersetzung oder Migration. Eine Bewertung wird nur gespeichert, wenn eine konkrete Kompetenz in dieser Beobachtung bewertet wird; `offen` wird nicht als eigener Ratingwert gespeichert. Eine gespeicherte Schnellbeobachtung wird beim Bearbeiten aus nichtleerer Notiz und fehlenden Kompetenzbewertungen erkannt. Kompetenzen koennen spaeter ergaenzt werden; dann wird der Schnellbeobachtungsmodus beendet und die normale Bewertungsvalidierung gilt. Werden alle Kompetenzen einer normalen Beobachtung entfernt, ist Speichern nur nach bewusster Aktivierung des Schnellbeobachtungsmodus und mit nichtleerer Notiz erlaubt.

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

Regel: Kompetenzstruktur wird nicht aus Beobachtungstexten abgeleitet. Sprint 3A fuehrt keine neuen DB-Felder wie `competency_area` oder `topic` ein. Die vorhandenen Felder werden fachlich gemappt: Fach = `subject_id` / `subject_name`, Kompetenzbereich = `learning_area`, Thema = `competency_group`, konkrete Kompetenz = `description` / `competency_text`, Kurzlabel = `label`. Sprint 3B ergaenzt konkrete Arbeitskatalog-Kompetenzen ueber neue stabile `competency_id`s und nutzt die optionale CSV-Spalte `competency_label` zur Befuellung des bestehenden SQLite-Feldes `label`.

## Kompetenzkatalog importieren oder aktualisieren

Start: PySide-App oeffnet eine SQLite-Datenbank ohne vorhandene Kompetenzen oder mit einem aelteren lokalen Kompetenzkatalog.

Schreibprozess: Idempotenter Katalogimport ueber `StudentDesktopAdapter`, `CurriculumDesktopAdapter` und `SQLiteCompetencyRepository.ensure_catalog_defaults()`.

Freigegebener PySide-/SQLite-Pfad:

```text
data/curriculum_catalog_v1.csv
-> CurriculumDesktopAdapter
-> SQLiteCompetencyRepository
-> SQLite competencies
```

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
- Dokumentationsstand
- Berichte und Dashboard, sobald sie die neuen Katalogmetadaten nutzen

Regel: Der Import ist ab Sprint 3B ein idempotenter Upsert. Bei leerer Tabelle wird der vollstaendige CSV-Katalog importiert. Bei bestehenden lokalen Datenbanken werden neue CSV-IDs eingefuegt und vorhandene CSV-IDs aktualisiert, ohne lokale Nicht-CSV-Kompetenzen zu loeschen. Sprint 4A aktualisiert dabei auch `grade_band`, `learning_stage`, `catalog_status`, `catalog_default_active` und `activation_group_key`. `competencies.active` vorhandener IDs wird nicht aus dem CSV ueberschrieben, damit alte grobe oder lokal deaktivierte Kompetenzen nicht ungefragt reaktiviert oder deaktiviert werden. `catalog_default_active` speichert nur den Katalogstandard. Kompetenzstaende werden weiterhin aus Beobachtungen abgeleitet und nicht manuell doppelt gespeichert. Alte grobe Kompetenzen bleiben historisch lesbar und bestehende `observation_competency_ratings` werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Fehlen Sprint-4A-Spalten in alten CSV-Dateien, setzt der Parser sichere Defaults: `learning_stage = cross_stage`, `catalog_status = current`, `activation_group_key = ''` und `catalog_default_active` aus dem alten `is_active`. Die Sprint-4-Lehrplanuebernahmen fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz sind abgeschlossen; Religion blieb ausserhalb dieses Katalogabgleichs.

## Kompetenzkatalog qualitaetssichern

Start: Vor einer fachlichen Ueberarbeitung von `data/curriculum_catalog_v1.csv`.

Schreibprozess: Kein fachlicher Schreibprozess. Die internen QS-Skripte lesen CSV-Dateien und melden Struktur-, ID- und Bestandsschutzverletzungen.

Freigegebener Pruefpfad:

```text
data/curriculum_catalog_v1.csv
-> scripts/validate_curriculum_catalog.py
-> scripts/compare_curriculum_catalog.py
-> scripts/next_competency_ids.py
```

Betroffene Datenquellen:

- `data/curriculum_catalog_v1.csv` nur lesend
- Vergleichskopie eines frueheren oder freigegebenen CSV-Katalogs nur lesend

Regel: Vor CSV-Aenderungen wird der aktuelle Katalog validiert. Vor Uebernahme einer neuen Katalogversion wird sie gegen den freigegebenen Altstand verglichen. Bestehende `competency_id`s duerfen niemals fachlich umgedeutet oder wiederverwendet werden; Text-, Hierarchie-, Status- und Stufenaenderungen an bestehenden IDs muessen durch das Vergleichswerkzeug sichtbar werden. Neue Kompetenz-IDs werden mit `scripts/next_competency_ids.py` global fortlaufend vergeben; fachbezogene Nummernkreise und Wiederverwendung von Luecken sind ausgeschlossen. Die QS-Skripte schreiben nicht in SQLite, erzeugen keine Migration und veraendern keine UI-Projektionen.

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
- SQLite `timetable_entries`

Erforderliche IDs:

- kuenstliche `student_id`
- bestehende oder kuenstliche `group_id`, `course_id`, `course_group_id`
- kuenstliche `observation_id`
- kuenstliche `document_id`
- kuenstliche `timetable_entry_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Beobachtungsdialog
- Berichtsvorbereitung
- Dokumentationsstand
- Dokumente & Medien
- Dashboard und Stundenplan

Regel: Der produktive App-Start erzeugt keine Demo-Schueler. Testdaten werden nur durch das explizite Script erzeugt. Ohne `--reset` bricht das Script ab, wenn bereits Schueler, Beobachtungen oder Dokumente vorhanden sind. Mit `--reset` wird bewusst ein frisches lokales Testsystem erzeugt. Der Pilottest-Seed bildet einen rund achtmonatigen Nutzungsstand bis zum aktuellen Pilotzeitraum ab und enthaelt vier Stammgruppen, mehrere Kurse und Kursverbuende, einen vollstaendigen Wochenstundenplan, fachbezogene Kompetenzbeobachtungen fuer alle aktiven Katalogfaecher, unterschiedliche Beobachtungsdichten, Kompetenzverlaeufe, eindeutige Schnellbeobachtungen, Soft Deletes, bestaetigte Kompetenzstaende sowie Demo-Dokumente. Es werden keine echten Kindernamen und keine echten Dokumente verwendet; Demo-Dateien sind harmlose Platzhalter und werden nicht versioniert.

## Lernentwicklungsbericht-Entwurf speichern

Start: Laura legt aus einem Schuelerprofil einen Lernentwicklungsbericht-Entwurf an oder speichert einen bereits geladenen Entwurf erneut.

Freigegebener Pfad:

```text
PySide Berichtswerkstatt
-> LearningReportDraftViewModel
-> StudentDesktopAdapter
-> Application Command / ReportDraftService
-> SQLiteReportDraftRepository
-> SQLite report_drafts + Relationstabellen
```

Betroffene Datenquellen:

- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`

Erforderliche IDs:

- neuer oder bestehender `report_draft_id`
- bestehender `student_id`
- ausgewaehlte bestehende `subject_id`
- ausgewaehlte bestehende `competency_id`
- ausgewaehlte bestehende `observation_id`

Regel: Anlegen erzeugt genau einen Entwurf mit Status `draft` und unveraenderlichem `created_at`. Aktualisieren ersetzt Fachauswahl, Fachtexte, Kompetenz-, Beobachtungs- und Diagrammreferenzen atomar und setzt `updated_at`. Neue Kompetenzreferenzen muessen aktiv und `current` sein; neue Beobachtungsreferenzen muessen aktiv sein. Beide Referenzarten muessen zum ausgewaehlten Fachkontext gehoeren, Beobachtungen zusaetzlich zum Kind. Bereits im Draft gespeicherte, spaeter deaktivierte Kompetenz- oder soft-geloeschte Beobachtungsreferenzen bleiben beim Speichern erhalten, solange sie nicht ausdruecklich abgewaehlt werden. Kompetenz- und Beobachtungsinhalte werden nicht kopiert. Der Prozess erzeugt keine Bewertung, Bestaetigung, Version, Freigabe, Archivierung oder finale Ausgabe. Das neutrale `ReportOutputModel` wird weiterhin erst fuer die Vorschau beziehungsweise PDF-Ausgabe aus dem geladenen Entwurf und den aktuellen freigegebenen Leseprojektionen gebaut.

## Lernentwicklungsbericht-Entwurf laden

Start: Laura oeffnet einen vorhandenen Entwurf zur Weiterbearbeitung.

Leseweg:

```text
SQLite report_drafts + Relationstabellen
-> SQLiteReportDraftRepository
-> Application Query
-> LearningReportDraftViewModel
-> PySide Berichtswerkstatt
```

Regel: Laden rekonstruiert ausschliesslich gespeicherte manuelle Texte und Referenzen. Kompetenzstatus und Kompetenztexte werden mit den gespeicherten `competency_id`-Werten als `retained_competency_ids` aus der kanonischen Projektion gelesen. Nicht mehr regulaer verfuegbare Kompetenzen bleiben gekennzeichnet ausgewaehlt, koennen nach Abwahl aber nicht neu ausgewaehlt werden. Aktive Beobachtungsinhalte werden aus der bestehenden Beobachtungsprojektion gelesen; gespeicherte, dort nicht mehr aktive `observation_id`-Werte bleiben ohne erfundene Inhalte als nicht verfuegbar sichtbar. Vorschau und `ReportOutputModel` weisen solche Ausfaelle neutral aus.

## Lernentwicklungsbericht finalisieren und revidieren

Start: Eine verantwortliche Lehrkraft finalisiert bewusst einen vorhandenen `RPD` und uebergibt ihren nichtleeren Anzeigenamen. Es wird keine Benutzer-ID erzeugt oder abgeleitet.

Freigegebener produktiver Pfad:

```text
PySide Berichtswerkstatt
-> LearningReportDraftViewModel speichern
-> StudentDesktopAdapter.prepare_learning_report_finalization
-> ReportFinalizationService.prepare
-> explizite Bestaetigung mit Lehrkraft-Anzeigename
-> StudentDesktopAdapter.finalize_learning_report
FinalizeLearningReportCommand
-> ReportFinalizationApplicationService
-> ReportFinalizationService
-> LearningReportFinalizationValidator
-> LearningReportSnapshotBuilder
-> SQLiteLearningReportRepository
-> SQLite learning_reports + learning_report_revisions
```

Gelesene Datenquellen:

- `report_drafts` und alle `report_draft_*`-Relationen
- `students`, `groups`, `courses`
- `competencies`
- `observations`, `observation_competency_ratings`
- `student_competency_confirmations` ausschliesslich fuer bewusst ausgewaehlte Diagrammwerte

Geschriebene Datenquellen:

- `learning_reports`
- `learning_report_revisions`

Erstfinalisierung:

1. `RPD` und alle referenzierten Quelldaten laden.
2. Zeitraum, Berichtstyp, Fachauswahl, verantwortete manuelle Inhalte sowie Kompetenz- und Beobachtungsreferenzen vollstaendig validieren.
3. Fachlichen Snapshot vollstaendig im Speicher erzeugen.
4. Snapshot kanonisch als UTF-8-JSON serialisieren und SHA-256 ueber exakt diese Bytes bilden.
5. Genau ein `RPT` fuer das Quell-`RPD` und Revision 1 als `RPV` in einer Transaktion schreiben.
6. Bei jedem Fehler die gesamte Transaktion zurueckrollen.

Folgerevision:

1. Dasselbe ueber `source_report_draft_id` gefundene `RPT` verwenden und dessen unveraenderliche Aggregateidentitaet gegen `student_id`, `report_type`, `period_start` und `period_end` des Drafts pruefen.
2. Bei einer Abweichung die Finalisierung als Domainfehler ablehnen; ein anderer Berichtstyp oder Zeitraum braucht einen neuen `RPD` und ein neues `RPT`.
3. Naechste Revisionsnummer und neue globale `RPV`-ID innerhalb der Schreibtransaktion bestimmen.
4. Bisher aktuelle Revision auf `superseded` setzen und `superseded_at` setzen.
5. Neue Revision mit Status `finalized` schreiben.
6. Bei jedem Fehler bleibt die bisherige Revision unveraendert aktuell.

Validierungsregeln:

- Draft, Student, unterstuetzter Berichtstyp und gueltiger Zeitraum muessen existieren beziehungsweise gueltig sein.
- Mindestens ein Fach und mindestens ein nichtleerer, manuell verantworteter Gesamt- oder Fachtext sind erforderlich.
- Alle Kompetenzreferenzen muessen vollstaendig aufloesbar und einem ausgewaehlten Fach zugeordnet sein. Bereits im Draft gespeicherte inaktive oder `legacy`-Kompetenzen duerfen mit Historienkennzeichnung eingefroren werden.
- Alle Beobachtungsreferenzen muessen aktiv, dem Kind zugeordnet und ueber Beobachtungsfach oder Kompetenzbewertung mindestens einem ausgewaehlten Fach fachlich zuordenbar sein. Fehlende oder inaktive `OBS`-IDs blockieren bis zur ausdruecklichen Abwahl im Draft.
- Bestaetigte Kompetenzstaende sind keine allgemeine Finalisierungspflicht.

Regel: Der `RPD` bleibt nach jeder Finalisierung im Status `draft` und normal bearbeitbar. Seine spaeteren Text- und Referenzaenderungen duerfen eine Folgerevision erzeugen, seine nach Revision 1 abweichenden Angaben zu Berichtstyp oder Zeitraum aber nicht dasselbe `RPT` umdeuten. `learning_reports` wird nach seiner Erstellung weder aktualisiert noch geloescht. Spaetere Aenderungen an Draft, Student, Kompetenz, Beobachtung oder Projektionen veraendern keine bestehende `RPV`. PDF-Artefakte, Renderer-Versionierung, Archivierung und LEG-Abschluss sind nicht Bestandteil dieses Schreibprozesses.

Produktive UI-Regel Sprint 5B.3: Vor jeder Bestaetigung wird der aktuelle Widgetstand ueber den bestehenden Draft-Lifecycle gespeichert. `ReportFinalizationService.prepare` validiert danach denselben gespeicherten Stand und erzeugt die Zusammenfassung fuer Kind, Berichtstyp, Zeitraum, Faecher, Kompetenz- und Beobachtungsanzahl sowie neue Revisionsnummer. Der Anzeigename wird sinnvoll aus `report_drafts.teacher_name` vorbelegt, bleibt aber eine verpflichtende freie Anzeigeeingabe ohne Benutzer- oder Rollen-ID. Erst eine ausdrueckliche Checkbox-Bestaetigung loest den bestehenden transaktionalen Finalisierungscommand aus. Bei fachlichen Fehlern bleibt die aktuelle Revision unveraendert und die Berichtswerkstatt zeigt eine handlungsorientierte `InlineMessage`; nur unerwartete technische Fehler sind modal. Es wird kein PDF automatisch erzeugt.

## Lernentwicklungsbericht-Revisionen und Snapshot lesen

Start: Laura oeffnet die Berichtswerkstatt oder waehlt eine konkrete `RPV`-Revision.

Status- und Historienweg:

```text
PySide Berichtswerkstatt
-> StudentDesktopAdapter.learning_report_revision_status(report_draft_id)
-> ReportRevisionApplicationService
-> LearningReportRevisionReadService
-> SQLiteLearningReportRepository
-> learning_reports + learning_report_revisions
```

Regel: Der Leseservice ermittelt das `RPT` zu einem `RPD`, die aktuelle `finalized`-Revision und alle Revisionen neueste zuerst. Fuer `Entwurf geändert` baut er den aktuellen Finalisierungskandidaten mit dem gespeicherten Anzeigenamen und Finalisierungszeitpunkt der aktuellen Revision deterministisch auf und vergleicht dessen SHA-256 mit `snapshot_sha256`. Fachliche Validierung und Vergleich finden zentral statt; die UI liest weder SQLite noch Repositorydetails.

Einzelrevisionsweg:

```text
RPV-ID
-> StudentDesktopAdapter.load_learning_report_revision
-> ReportRevisionApplicationService.snapshot_payload
-> LearningReportRevisionReadService
-> gespeicherten SHA-256 pruefen und snapshot_json lesen
-> LearningReportRevisionViewModel + snapshotbasiertes ReportOutputModel
-> LearningReportRevisionDialog
```

Regel: Nach der `RPV`-Abfrage werden keine operativen Datenquellen gelesen. Namen, Gruppen-/Kurskontext, Fachlabels, Kompetenztexte, Beobachtungsinhalte und Diagrammwerte stammen ausschliesslich aus dem Snapshot. Die Ansicht ist vollstaendig schreibgeschuetzt. Ein fehlgeschlagener Hash verhindert das Oeffnen; aktuelle Daten werden niemals als Ersatz rekonstruiert.

## Finales Lernentwicklungsbericht-PDF erzeugen

Start: Laura oeffnet eine konkrete aktuelle `RPV`-Revision und waehlt `Finales PDF erstellen`.

Freigegebener Pfad:

```text
LearningReportRevisionDialog (RPV-ID)
-> StudentDesktopAdapter.generate_learning_report_pdf
-> LearningReportPdfApplicationService
-> LearningReportPdfService
-> LearningReportRevisionReadService + SQLiteLearningReportRepository
-> gespeicherten RPV-Snapshot und SHA-256 validieren
-> snapshotbasiertes ReportOutputModel
-> reiner PdfRenderer
-> verwaltete PDF-Datei
-> SQLiteLearningReportPdfArtifactRepository
-> learning_report_pdf_artifacts
```

Gelesene Datenquellen:

- `learning_reports`
- `learning_report_revisions`
- eine bereits vorhandene `learning_report_pdf_artifacts`-Zeile fuer idempotente Wiederaufrufe

Geschriebene Ziele:

- PDF-Datei unter `data/documents/<student_id>/reports/<RPT>/<RPV>/`
- genau eine unveraenderliche Zeile in `learning_report_pdf_artifacts` pro `RPV`

Regeln:

1. Nur eine Revision mit aktuellem Status `finalized` darf ein neues Artefakt erzeugen. Draft und `superseded` sind unzulaessig.
2. Vor dem Rendern werden gespeicherter Snapshot-Hash, Schemaversion, Pflichtstruktur und interne Fach-, Kompetenz-, Beobachtungs- und Textreferenzen geprueft. Es werden keine operativen Quellen nachgeladen.
3. Der vorhandene `PdfRenderer` erhaelt ausschliesslich das aus diesem Snapshot gebaute `ReportOutputModel` und kennt keine Persistenz- oder Statuslogik.
4. Nach erfolgreichem Rendern werden PDF-SHA-256 und Dateigroesse berechnet. Erst danach wird die `RPA`-Referenz gespeichert.
5. Ein vorhandenes Artefakt wird nie ueberschrieben. Der Wiederaufruf bestaetigt relativen Pfad, Dateigroesse und PDF-Hash und gibt dieselbe Referenz zurueck.
6. Draftaenderungen, operative Datenaenderungen und spaetere Revisionen veraendern bestehende PDF-Dateien und Hashes nicht.
7. Bei Render-, Datei-, Hash- oder Persistenzfehlern entsteht keine gueltige neue Artefaktreferenz; eine in diesem Versuch erzeugte Datei wird entfernt.

Renderer-Versionierung, Mehrfachartefakte, komplexe Archivverwaltung, LEG-PDF und externe freie Exportpfade sind nicht Bestandteil dieses Lifecycles.

## LEG-Arbeitsentwurf speichern

Start: Laura legt fuer einen Schueler einen Lernentwicklungsgespraech-Arbeitsentwurf an oder speichert einen bereits geladenen Entwurf erneut.

Freigegebener Pfad:

```text
LEG ViewModel
-> StudentDesktopAdapter
-> LearningConferenceDraftApplicationService
-> LearningConferenceDraftService
-> SQLiteLearningConferenceDraftRepository
-> SQLite learning_conference_drafts + Relationstabellen
```

Betroffene Datenquellen:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Erforderliche IDs:

- neuer oder bestehender `learning_conference_draft_id`
- bestehender `student_id`
- ausgewaehlte bestehende `subject_id`
- ausgewaehlte bestehende `competency_id`
- ausgewaehlte bestehende `observation_id`

Regel: Anlegen erzeugt genau einen Entwurf mit Status `draft` und unveraenderlichem `created_at`. Aktualisieren ersetzt manuelle Inhalte sowie Fach-, Themen-, Kompetenz-, Beobachtungs- und Diagrammreferenzen atomar und setzt `updated_at`. `student_id` bleibt stabil. Neue Beobachtungsreferenzen muessen aktiv sein und zum Kind gehoeren. Bereits referenzierte, spaeter soft-geloeschte Belege bleiben erhalten und werden beim Laden als nicht verfuegbar gekennzeichnet. Der Prozess erzeugt keine Kompetenzbewertung, keinen Kompetenzstatus, keine automatischen Texte, keine finale Version, Freigabe oder Archivierung.

## LEG-Arbeitsentwurf laden

Start: Laura oeffnet einen vorhandenen Entwurf zur Weiterbearbeitung.

Leseweg:

```text
SQLite learning_conference_drafts + Relationstabellen
-> SQLiteLearningConferenceDraftRepository
-> Application Query
-> LearningConferenceDraftViewModel
-> produktiver Sprint-7G.2-LEG-Arbeitsbereich
```

Regel: Laden rekonstruiert manuelle Inhalte und stabile Referenzen. Kompetenzstatus, Kompetenztexte und Beobachtungsinhalte werden aus den bestehenden Live-Sources-of-Truth neu projiziert. Nicht mehr aktive Beobachtungsbelege werden weder verworfen noch ersetzt, sondern kontrolliert als nicht verfuegbar ausgewiesen. Der Draft ist kein eingefrorener Gespraechsstand.

Sprint 7G.2 startet diesen Prozess im Schuelerprofil ueber `Lernentwicklungsgespräch`. Bei genau einem vorhandenen Draft wird dieser geladen. Bei mehreren Drafts muss Laura einen vorhandenen Entwurf oder das explizite Anlegen eines neuen Entwurfs waehlen. Die Dialogaktion `Entwurf speichern` darf jederzeit ausgefuehrt werden; Schliessen allein erzeugt keine finale Dokumentation und fuehrt keine stillschweigende Speicherung aus.

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

Regel: `competency_id` bleibt erhalten. Alte grobe Kompetenzen duerfen spaeter deaktiviert oder archiviert werden, aber nicht geloescht werden, solange historische Beobachtungen oder bestaetigte Kompetenzstaende darauf verweisen. Bestehende `observation_competency_ratings` bleiben gueltig und werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Offene Entscheidung fuer einen spaeteren Implementierungssprint: historische Beobachtungen zeigen entweder das aktuelle Kompetenzlabel oder das zum Beobachtungszeitpunkt gueltige Label.

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

## Lernentwicklungsgespraech abschliessen

Start: Die verantwortliche Lehrkraft loest fuer einen gespeicherten `LCD` ausdruecklich `Gespraech abschliessen` aus. Die UI uebergibt nur die LCD-ID.

Schreibprozess:

1. `LearningConferenceCompletionApplicationService` laedt den aktuellen LCD und alle bewusst ausgewaehlten Referenzen ueber das LEG-Repository.
2. Die LEG-Domain validiert Schuelerbezug, Gespraechsdatum, verantwortliche Lehrkraft, mindestens einen gemeinsamen Ergebnisinhalt und die vollstaendige Aufloesbarkeit aller Abschlussreferenzen.
3. Der LEG-spezifische Snapshot Builder erzeugt ausschliesslich aus diesen validierten Daten die kanonische Snapshotstruktur. Interne Vorbereitung, private Notizen und Diagrammtypen werden nicht uebernommen.
4. Aus kanonischem UTF-8-JSON wird SHA-256 berechnet.
5. Das SQLite-Repository erzeugt beim ersten Abschluss LCF und LCV atomar. Bei einer Korrektur schreibt es zuerst die neue Revision und ersetzt den Status der bisherigen Revision innerhalb derselben Transaktion; bei einem Fehler wird alles zurueckgerollt.
6. Entspricht der Hash dem aktuellen Snapshot, wird die bestehende LCV zurueckgegeben und keine neue Revision erzeugt.

Betroffene Datenquellen:

- lesend: `learning_conference_drafts` und Relationen, `students`, `groups`, `courses`, `competencies`, `observations`, `observation_competency_ratings`
- schreibend: `learning_conferences`, `learning_conference_revisions`

Erforderliche IDs:

- bestehende `learning_conference_draft_id`
- neue `learning_conference_id` beim ersten Abschluss
- neue `learning_conference_revision_id` nur bei neuem Snapshot

Regeln:

- LCD bleibt nach jedem Abschluss bearbeitbar und wird nicht umgedeutet.
- Alte Revisionen werden erst nach einem vollstaendig erfolgreichen Folgeabschluss `superseded`.
- Abgeschlossene Revisionen werden weder geloescht noch inhaltlich aktualisiert.
- Fehlende ausgewaehlte Fach-, Kompetenz- oder Beobachtungsreferenzen werden nicht still entfernt.

## LEG-Abschlussrevision anzeigen

Start: Eine LCV wird aus der Abschluss- beziehungsweise Revisionshistorie geoeffnet.

Leseprozess:

1. Adapter und Application Service laden die LCV ueber das Repository.
2. Der LEG-Leseservice bildet aus dem gespeicherten Snapshot-JSON erneut die kanonischen Bytes und prueft SHA-256 sowie Snapshot-Schemaversion.
3. Das ViewModel projiziert ausschliesslich diese Snapshotdaten in die schreibgeschuetzte Ansicht.

Regel: Es werden keine aktuellen Schueler-, Gruppen-, Kurs-, Kompetenz- oder Beobachtungswerte nachgeladen. Ein Integritaetsfehler verhindert die Anzeige.

## Finales LEG-PDF erzeugen

Start: Laura oeffnet eine konkrete aktuelle LCV mit Status `completed` und waehlt `Finales PDF erstellen`.

Freigegebener Pfad:

```text
LearningConferenceRevisionDialog (LCV-ID)
-> StudentDesktopAdapter.generate_learning_conference_pdf
-> LearningConferencePdfApplicationService
-> LearningConferencePdfService
-> LearningConferenceRevisionReadService + SQLiteLearningConferenceRepository
-> gespeicherten LCV-Snapshot und SHA-256 validieren
-> LEG-spezifisches renderer-neutrales Ausgabemodell
-> reiner PdfRenderer
-> verwaltete PDF-Datei
-> SQLiteLearningConferencePdfArtifactRepository
-> learning_conference_pdf_artifacts
```

Gelesene Datenquellen:

- `learning_conference_revisions`
- `learning_conferences`
- eine vorhandene `learning_conference_pdf_artifacts`-Zeile fuer idempotente Wiederaufrufe

Geschriebene Ziele:

- PDF-Datei unter `data/documents/<student_id>/learning_conferences/<LCF>/<LCV>/`
- genau eine unveraenderliche Zeile in `learning_conference_pdf_artifacts` pro LCV

Regeln:

1. Nur eine LCV mit aktuellem Status `completed` darf ein neues Artefakt erzeugen. LCD und `superseded` sind unzulaessig.
2. Der LEG-Revisionsleseservice prueft kanonisches Snapshot-JSON, Schemaversion und SHA-256. Danach validiert die PDF-Domain alle fuer die Ausgabe erforderlichen Snapshotstrukturen und Referenzen.
3. Es werden weder LCD noch aktuelle Schueler-, Kompetenz-, Beobachtungs- oder sonstige Live-Projektionen gelesen.
4. Der reine `PdfRenderer` erhaelt nur das aus dem LCV-Snapshot gebaute Ausgabemodell und kennt weder Persistenz, Status noch Hashregeln.
5. Nach erfolgreichem Rendern werden Dateigroesse und PDF-SHA-256 berechnet; erst danach wird die `LCA`-Referenz gespeichert.
6. Ein vorhandenes Artefakt wird nie ueberschrieben. Der Wiederaufruf verifiziert Snapshot-Hash, Pfad, Dateigroesse und PDF-Hash und gibt dieselbe Referenz zurueck.
7. Bei Render-, Datei-, Hash- oder Persistenzfehlern entsteht keine gueltige neue Artefaktreferenz; eine in diesem Versuch erzeugte Datei wird entfernt.

Archivierung, Verschluesselung, Renderer-Versionierung, Mehrfachartefakte, Rollenmodell und Berichtsdomain sind nicht Bestandteil dieses Lifecycles.
