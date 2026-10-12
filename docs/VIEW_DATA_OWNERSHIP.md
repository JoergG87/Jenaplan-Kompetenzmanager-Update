# View Data Ownership

TabletDialogPolicy besitzt Katalog-Mindesthöhe 420 Pixel und Bewertungsfläche bis 440 Pixel. Überhöhe bleibt über den jeweiligen Schritt erreichbar; vorhandene Dialogadapter bleiben fachliche Owner.

iPad-Startbildschirm-Symbol gehört zur nativen Paketpräsentation. Quelle assets/app_icon.png; keine neue fachliche Ansicht.

Beobachtungsdialog: TabletDialogPolicy/TabletAppShell besitzen finale Gestenbindung und Mindestgrößen der vorhandenen drei Schritte. Inhalt und Commands bleiben ursprünglicher Dialog.

TabletTapGuard besitzt nur die Unterscheidung Antippen/Wischen. Vorhandene Karten und Schaltflächen behalten ihre fachliche Action-/Signalownership; Desktop unverändert.

Tablet-Fehlerkorrektur 12.10.2026: Heute-Klassen-/Kompetenzmatrix bleibt bestehende kanonische Projektion, erhält bei Überhöhe vertikalen Zugriff. Tablet-Hintergrund/Lifecycle sind Präsentationsownership; keine Fachänderung.

Simulator-Verfeinerung: Einspaltige Bericht-/LEG-Seiten verwenden vorhandene Projektionen. Tablet-Auswahlfelder projizieren NavigationButtons; Suche/Filter werden lediglich neu angeordnet. Abschlussaktionen bleiben außerhalb des scrollbaren Inhalts. Keine persistierten Layoutzustände.

Tablet-Dialogseiten 12.10.2026: AppShell._exec_dialog / _exec_workspace / _open_dialog / _open_workspace sind Präsentationsports mit identischen Desktopdefaults. TabletAppShell zeigt vorhandene Qt-Dialoginhalte als fokussierte Seite im eigenen Stack; fachliche Accept-/Reject-/Finished-Verträge bleiben erhalten. Navigation ist während der Eingabe gesperrt, Zurück verwendet den vorhandenen Abbruch-/Entwurfschutz. Keine zweite Validierung oder Persistenz.

## iPad-UX-Präzisierung – PO-Auftrag 12.10.2026

Tablet-Bedienung folgt dem Arbeitsablauf: Kind → Kontext → Kompetenzen/Bewertungen → Notiz → Speichern. Beobachtungsdialog komponiert dieselben vorhandenen Felder in drei direkt wechselbare Bereiche; keine Daten-/Validierungsänderung; bestehende Bewertungsdefaults bleiben unverändert. Speichern und Abbrechen bleiben dauerhaft sichtbar. Bildschirmtastatur reserviert unteren Raum, Schrittfelder sind scrollbar; dynamische Bewertungsflächen mindestens 44 Pixel hoch. Hauptnavigation im Hochformat als Menü, kompakte zweizeilige Profilaktionen, Kompetenzlisten mit natürlicher Zeilenhöhe statt verteilter Vollbildfelder. Desktop bleibt unverändert. Breite Arbeitsschritte müssen innerhalb der Tabletbreite umbrechen; globales horizontales Scrollen ist kein fertiges Tablet-Design.

## Gesamte App für iPad – PO-Auftrag 11.10.2026

TabletAppShell komponiert die vorhandenen Heute-/Schüler-/Profil-/Stammdaten-/Einstellungen-Ansichten aus AppShell. Quellen, Aggregate, Projektionen und Schreibownership bleiben unverändert. Tablet-Layout besitzt nur Navigation, Scrollen, Dialoggröße und Touchflächen. Keine zweite Fachlogik oder eigene Schüler-/Kompetenztabellen. Fehlende iOS-Plattformfunktionen müssen sichtbar gesperrt sein, niemals als erfolgreich simuliert.

## iPad-Machbarkeitstest

iPad-Prototypfenster projiziert ausschließlich DemoRepository mit drei fest vorgegebenen Kompetenzen. Keine Verbindung zu Desktop-Adaptern oder Nutzerdaten. Keine neue Produktansicht.

Release-Signierung 11.10.2026: Sparkle signiert unveränderte Artefaktbytes über eine kurzlebige, zugriffsbeschränkte `payload.bin`-Kopie; die Kopie wird auch bei Fehlern entfernt. Keine Produktdaten oder neuen UI-Felder.

Releasepräzisierung 11.10.2026: Öffentliche Release-Notes erhalten Version und Build ausschließlich aus der geprüften Manifestidentität; Quellvorlagen behalten ihre Platzhalter. Keine Produktdaten, Datenmodell- oder UI-Änderung.


PO-Ergänzung 11.10.2026: Vier neu erzeugte PNG-Pflanzen mit echtem Alphakanal ersetzen die weißen JPEG-Flächen im Elternexport. Als separat nutzbare Dateien und ZIP bereitgestellt; Präsentationsressourcen ohne Änderung fachlicher Stufen oder Daten.

## Vorgelagerter Auswahl-Dialog – aktueller PO-Stand 11.10.2026

`CompetencyPdfCompletionDialog` projiziert ausschließlich die vom Application Layer gelieferten offenen Kompetenzzeilen, je Fach gruppiert. Qt sammelt Auswahl und zeigt Restanzahl; fachliche Vollständigkeit, Frische, Persistenz und Exportfreigabe liegen außerhalb der Widgets in Service/Adapter/Repository. Shell koordiniert Dialog, bewussten Speicherschritt, Profilrefresh und nativen Zieldialog. Renderer erhält nur vollständig bewertete Modelle.


## Ownership der Cipher-Produktkomposition

`CipherProductRuntimeCoordinator` besitzt die Qt-freie Startup-Komposition
nach bereits verifizierter Authentifizierung. Er klassifiziert den
Installationsstand, bindet die produktiven `RuntimePaths`, prüft die exakte
SQLCipher-Engine, lädt genau eine Database-Key-Runtime und öffnet damit
Final-V4, Companion und Managed Document Store. Kein Widget, keine Shell und
kein Desktop Adapter erzeugt im Cipher-Produktpfad eine eigene
`SQLiteDatabase` oder einen ungekeyten Connection Provider.

`main.py` besitzt ausschließlich die Reihenfolge aus Auth-/Sessionprüfung,
Cipher-Komposition und Injektion. `StudentDesktopAdapter` besitzt weiterhin
fachliche Projektionen und Writes, verwendet aber die injizierte keyed
`SQLiteDatabase` und denselben `ManagedDocumentStore`. `AppShell` komponiert
die vorhandene UI auf diesen Instanzen. Die Settings-View projiziert nur
Status, Vorschau und bewusste Bestätigung. Die injizierten Final-V4-
Application-Services besitzen `.jkmebackup`, Vollverifikation,
Restore-Staging, `RESTORE_READY` und Worker-Handoff; ZIP-v1 ist im Cipher-
Produktpfad nicht erreichbar. Klartexterkennung, Schlüssel-, Schema-,
Context- und Integritätsprüfung bleiben außerhalb der Widgets.

## Final-V4-Ownership für Startup, Schuljahre und Assignments

Der `DatabaseStartupResolver` besitzt ausschließlich die read-only
Schemaerkennung. Der `DatabaseStartupCoordinator` besitzt die
Runtime-Disposition vor Shell, Adaptern und fachlichen Writern. Die direkte
Final-V4-Schemaquelle besitzt nur die autorisierte Neuanlage und vollständige
Verifikation. Kein Widget und kein Adapter erkennt, migriert oder repariert
Datenbankschemata.

Der SJ-2E-Ownershipvertrag für produktive Membership-Reader und der
SJ-2F-Ownershipvertrag für produktive Writer sind lokal im Produktcode
umgesetzt. Produktive Views konsumieren die Assignment-API über
Application-, Repository- und Adaptergrenzen. Ein erkanntes und vollständig
verifiziertes finales Schema führt zu `V4_SCHEMA_READY` und darf die normale
Runtime erreichen. Nach dem Gate öffnet die Composition Root die vorhandene
Datenbank ohne Create-Fallback. Es gibt keine
V2-Bootstrap-View, keine V2-Migrationsvorschau und keine sichtbare
V2-Restoreauswahl.

| Projektion / Vorgang | Fachliche Quellen | Owner | Nicht erlaubt |
|---|---|---|---|
| Datenbank-Startupstatus | read-only Pfad-, Restore- und vollständige Schemaidentität | Core Startup | Widgetentscheidung, Teilfingerprint, automatische Migration |
| direkte V4-Neuanlage | autorisierter leerer Zielpfad und finales DDL | Core Schema Initializer | bestehende Datei ersetzen, V2-/V3-Zwischenschema, Transition-Beleg |
| zugelassene Runtime-Datenbank | zuvor vollständig verifizierte Final-V4-Datei | Desktop Composition Root mit `create=False` | stille Neuanlage nach dem Startup-Gate |
| Schuljahresliste/-status | `school_years` | `SchoolYearRepository` und aufrufender Application Service | Systemdatum oder Label als Statusquelle |
| Zuordnung an einem Datum | `student_school_year_assignments`, V3-`students`, `school_years`, Gruppen und Kurse plus `AssignmentReferenceRequest` mit explizitem Fachdatum | `SchoolYearAssignmentReadSession` über bestehende datierte Assignment-Projektionen | `students.group_id/course_id`, current- oder Last-known-Fallback, Widgetlogik |
| aktuelle Mitgliedschaft und Mitgliederlisten | current-Schuljahr plus einmalig gesetzter `as_of`-Tag; optionale Gruppe, Kurs oder Kursverbund als Schnittmenge seiner Gruppen und Kurse | `CurrentMembershipReadSnapshot` aus `SchoolYearAssignmentReadSession` | Systemdatum, N+1, Python-Nachzählung, Widgetfilterung von Intervallen |
| zusammengesetzter Bildschirm-Read | Assignment-, Stammdaten-, Dokumentations- und Beobachtungsprojektionen auf derselben aufrufereigenen Connection und im selben Read-Snapshot | aufrufender Application-/Desktop-Adapter plus `SchoolYearAssignmentReadSession` | zweite Connection, Session-eigene Transaktionssteuerung, Query je Unterwidget |
| historische Schuljahres-/Last-known-Abfrage | explizite Schuljahr-ID und Referenzdatum beziehungsweise expliziter Last-known-Aufruf | `SchoolYearAssignmentQueryService.membership_in_school_year` / `last_known_membership` | Jahresende als Ersatzdatum, Last-known als automatischer Fallback |
| Schüleranlage | bewusst eingegebene Stammdaten, eindeutiges current-Schuljahr, Gruppe, Kurs und explizites Gültigkeitsintervall | `StudentDesktopAdapter` und `CreateStudentWithInitialEnrollment` | Widget-SQL, Teilcommit, V2-Membershipfelder, implizites Schuljahr |
| Schülerstammdaten ändern | Vorname, Nachname und Notiz | `StudentDesktopAdapter` und `UpdateStudentMasterData` | Kurs, Stammgruppe, Schuljahr, Assignmentintervall oder -status |
| Einzelkind-Zuordnung ändern | aktuelle Assignmentprojektion, expliziter Stichtag, Zielkurs und optionale Zielgruppe | `StudentMembershipChangeDialog`, `StudentDesktopAdapter` und `ChangeStudentMembership` | generischer Studentupdate, Mehrkindwechsel, historische Korrektur |
| Austritt | expliziter Stichtag und eindeutiges aktuelles Assignment | `StudentExitDialog`, `StudentDesktopAdapter` und `ExitStudentFromSchoolYear` | Archivierung oder Änderung der Stammdaten |
| Archivierung | V3-Schülerstammdaten und aktive Einschreibungsprüfung am expliziten Stichtag | `StudentDesktopAdapter` und `ArchiveStudent` | `exited` erzeugen, Assignment verändern, aktive Einschreibung übergehen |
| Kurs-/Stammgruppendeaktivierung | Stammdaten plus aktuelle und zukünftige `enrolled`-Referenzen am expliziten Stichtag | `MasterDataDesktopAdapter` und `SQLiteMasterDataRepository` | versteckte Umbuchung, Ersatzgruppe/-kurs, historische Assignmentmutation |
| Kursfortschreibung | `courses.year_level` | späterer School-Year Transition Service | Kursname, Farbe, Sortierung |
| SJ-3A-Schuljahreswechsel-Vorschau | alle V3-Schüler, genau ein current-Schuljahr, Assignments an dessen Ende, vorhandene Schuljahre sowie Gruppen und Kurse mit `active`/`year_level` | `SchoolYearTransitionPreviewService` und `SchoolYearTransitionPreviewProjector` | Kindfilter, Systemdatum, Kursname/-sortierung, zweite Connection, Write, UI-Entscheidung oder stille Zielauswahl |
| Settings-Einstieg Schuljahre | eindeutiges aktuelles Schuljahr sowie bewusst eingegebene flüchtige Zieljahresdaten | `AppShell` als Composition Root und `SettingsScreen` als reine Eingabe-/Anzeigegrenze | Widget-Repositoryzugriff, zweite Connection für Planoptionen, Persistenz, Backup, Authentifizierung, Maintenance-Gate oder Ausführung |
| SJ-3B.1-Previewdialog | unveränderte Reihenfolge, Zähler, Zielstatus und Issues genau einer vorhandenen `SchoolYearTransitionPreview` | `SchoolYearTransitionPreviewViewModel` und `SchoolYearTransitionPreviewDialog` | Repository-/Serviceaufruf im Widget, Neuberechnung, Sortierung, Bearbeitung, Backup, Authentifizierung oder Ausführung |
| SJ-3B.2a-Planmodell | vorhandene Preview sowie explizite aktive Kurs- und Gruppenoptionen | `SchoolYearTransitionPlan` | Qt, Repositoryzugriff, Persistenz, automatische Entscheidung, Backup, Authentifizierung oder Ausführung |
| SJ-3B.2b-individuelle Planbearbeitung | aktueller flüchtiger `SchoolYearTransitionPlan` mit dessen kopierten Anzeige-Metadaten, aktiven Optionen, Validierung und Zählern | `SchoolYearTransitionPreviewViewModel` und `SchoolYearTransitionPreviewDialog` | Preview-Mutation, Widget-Fachlogik, Repository-/Servicezugriff, automatische Auswahl, Mehrfachauswahl, Sammeländerung, Write, Backup, Authentifizierung oder Ausführung |
| SJ-3B.3-Filter, UI-Schritte und Sammelbearbeitung | aktueller flüchtiger `SchoolYearTransitionPlan`, reine Präsentationsschritte, kombinierte ViewModel-Filter sowie explizite stabile Auswahl-IDs; Sammelziele ausschließlich aus den aktiven Planoptionen | `SchoolYearTransitionPreviewViewModel`, `SchoolYearTransitionPreviewDialog` und `SchoolYearTransitionPlan` | Wizard-Domainlogik, Preview-Mutation, automatische Auswahl, Änderung verdeckter ausgewählter Zeilen, Widget-Repositoryzugriff, Write, Backup, Authentifizierung oder Ausführung |
| isolierter SJ-3C.2-Wechselbeleg | vollständig gelöster source-gebundener Plan, Operation-Token und erwarteter Plan-Hash auf temporärer synthetischer Final-V4-Datenbank | `ExecuteSchoolYearTransition` und `SchoolYearTransitionExecutionRepository` | Widget-/Adapterwrite, Anzeigenamen im Beleg, Initialanlage, Bootstrap, Migration, reales Produktziel oder Freigabe ohne Backup |
| SJ-3C.6-Aktivierung | vollständig gelöster flüchtiger Plan, Prüfbestätigung, Passwort-Step-up und sanitisiertes Phasen-/Ergebnisprotokoll | `AppShell` als Composition Root, `SchoolYearTransitionActivationController` als Workergrenze und `ExecuteSchoolYearTransition` als fachlicher Owner | Widget-Aufruf einzelner Backendstufen, UI-Hashing, technische IDs/Pfade/Exceptions, Doppelausführung oder Fortsetzung bei `RECOVERY_REQUIRED` |

Beobachtung, Bericht und LEG liefern ihren vorhandenen fachlichen
Referenzzeitpunkt als `AssignmentReferenceRequest`: `observations.date`,
`period_end` beziehungsweise `conference_date`. Ein freies Dokument ohne
fachliches Referenzdatum bleibt neutral und erzeugt keine
Zuordnungsbehauptung. Current, `last_known_membership`, Systemdatum und
V2-Schülerfelder sind keine Fallbacks. Diese produktive Leserumstellung ist
lokal erfolgt. Finalisierte Revisionen und PDFs werden nicht neu
aufgelöst. Widgets komponieren ausschließlich displayfertige ViewModels und
enthalten keine Repository- oder Intervalllogik.

SJ-3A besitzt ausschließlich die vollständige Domain-/Application-Projektion.
Der connection-gebundene Preview-Repository liest alle Quellen im selben
`query_only`-Snapshot; der SQLite-freie Projektor besitzt Kalenderprüfung,
Eindeutigkeitsauflösung, Stufenfortschreibung, Blockercodes, stabile Sortierung
und Gesamtzähler. Der Anzeigename stammt ausschließlich aus den über
`student_id` aufgelösten V3-Schülerstammdaten; ein fehlender Datensatz bleibt
als neutraler Blocker sichtbar. SJ-3B.1 stellt die Projektion ausschließlich
lesend dar. SJ-3B.2a besitzt nur das unveränderliche flüchtige Planmodell.
SJ-3B.2b bearbeitet diesen Plan ausschließlich über dessen vorhandene
Einzelmethoden. Das Widget hält nur die jeweils neue flüchtige Instanz;
Optionen, Validierung und Zähler stammen aus Plan und ViewModel, ohne
Vorschlags- oder Validierungslogik im Widget zu duplizieren.
SJ-3C.6 übergibt den vollständig gelösten Plan nach Checkbox und Passwort an
eine eigene Workergrenze. Diese konsumiert Step-up und ruft ausschließlich den
bestehenden Executor auf; Phasen-, Ergebnis- und Fehlerprojektion bleiben im
Dialog. Das Widget besitzt weiterhin weder Repository-, Backup-, Maintenance-
noch Transitionslogik.

Die minimale Settings-Integration übergibt Bezeichnung, Beginn und Ende an
den bestehenden `SchoolYearTransitionPreviewService`. Dieser erzeugt Preview
und `SchoolYearTransitionPlan` aus denselben bereits gelesenen Kurs- und
Gruppenquellen im einen `query_only`-Snapshot. Die Shell prüft ausschließlich
die vorhandenen globalen Zieljahres-Issues, zeigt dafür neutralen UI-Text und
öffnet sonst den vorhandenen Dialog. Das Schließen löst keinen Refresh und
keinen fachlichen oder technischen Write aus.

Die Writer-Dialoge besitzen ausschließlich Eingabe, Vorschau, bewusste
Bestätigung und Fehlerdarstellung. Atomizität, Intervallregeln,
Eindeutigkeitsprüfung, Deaktivierungsschutz und Rollback gehören den
Application-/Repositorygrenzen. `courses.year_level` ist Stammdatenquelle und
wird im Kursdialog bewusst gewählt; sie wird nicht durch Widgetreihenfolge
oder Kursname abgeleitet.

## Intern gegateter LEG-HTML-Host - View Ownership

`LearningConferenceHtmlDialog` besitzt ausschließlich WebEngine-Lifecycle,
Ressourcen-, Navigations- und Python-seitigen Close-Schutz. Der DOM besitzt
sichtbare Phase, Disclosure, Fokus und Eingabespiegel.
`LearningConferenceHtmlBridge` besitzt die Allowlist, den geöffneten Python-
Draft und dessen gespeicherte Baseline. Vorhandene Adapter, Application
Services und Domain Services bleiben alleinige Eigentümer von Reads,
vollständigem Draft-Write, Validierung, Completion, Revision und finalem LCA.
Die AppShell besitzt Gate-Auswahl und verhindert parallele LEG-Hosts desselben
Drafts. Der Bericht-HTML-Spike bleibt außerhalb der Shell-Navigation.

## Phase 2 Berichte-Übersicht - implementiert

`StudentDesktopAdapter.report_overview_for_student` bleibt die einzige
Desktop-Kompositionsgrenze. Er bestimmt das eindeutige aktuelle Schuljahr und
die effektiven Schülerfächer, hält Bericht und LEG beim Lesen getrennt und
übergibt ausschließlich vorhandene Schuljahr-, Bericht-, LEG-, Beobachtungs-
und kanonische Kompetenzstatuswerte an die reine Phase-2-ViewModel-Projektion.
Die RPD-Auswahl bleibt ausschließlich Navigationszustand der Berichtswerkstatt
und ist kein Gate der Entwicklungsübersicht. Repositories und Application
Services behalten ihre bestehenden fachlichen Zuständigkeiten.

Der Adapter friert den aktuellen Schuljahreszeitraum einmal ein, verifiziert die
neueste gültige Bericht- beziehungsweise LEG-Revision je Aggregat, reicht
stabile IDs unverändert weiter und klassifiziert Quellenfehler neutral.
Live-Dokumentation wird möglichst in einem SQLite-Read-Snapshot gelesen. Ein
Fehler einer Quelle darf weiterhin gültige getrennte Dokumentereignisse nicht
entfernen.

Die ViewModel-Projektion besitzt Schuljahreszeitraumfilter, Datumsnormalisierung,
Ereignisidentitäten, je Aggregat höchstens ein gültiges Bericht- und
LEG-Abschlussereignis, die rein zeitliche Ergänzung mit Beobachtungen und
aktuellen sicheren Bestätigungen bis zum Zielumfang 15,
die chronologische Gesamtordnung, Fach- und Globaldeduplizierung, aktuelle
Kompetenz- und Beobachtungsmengen, den Ausschluss historischer Kompetenzen
sowie displayfertige neutrale Texte, Accessible Names, Leer- und
Lesewarnzustände. Sie liefert dem Widget genau eine vollständige ausgewählte
Timeline-Liste. Sie erzeugt keine pädagogische Relevanz, Bewertung,
Priorisierung, Stärke, Defizit, Trend oder Entwicklungsrichtung.

`StudentProfileScreen` besitzt ausschließlich Rendering, Fokus,
horizontale Scrollposition, Responsive Layout und bewusstes Auf-/Zuklappen. Es
rendert die vollständige gelieferte Timeline-Liste in einer horizontal
scrollbaren Darstellung und positioniert sie beim Öffnen am neuesten Ende.
Abhängig von der verfügbaren Breite sind ungefähr `2`, `4` oder `5`
Ereigniskarten gleichzeitig sichtbar; diese Werte sind weder Inhaltsgrenze
noch ViewModel-Auswahlgröße oder Begrenzung der Ereignisprojektion. Das Widget
filtert, sortiert, entfernt, priorisiert, dedupliziert und zählt keine Inhalte,
greift nicht auf `orientation_changes` zu und verwendet keinen curricularen
Nenner. Es ermöglicht ausschließlich das bewusste Scrollen zu älteren
enthaltenen Ereignissen; automatisches Karussell und automatische Bewegung
sind unzulässig.

Die kleinen Fachsymbole sind eine rein darstellungsbezogene, neutrale
UI-Zuordnung aus der bereits vorhandenen `subject_id`. Sie ersetzen ein
Diagramm, erzeugen keine neue Fachzuordnung und transportieren weder Menge,
Status noch Bewertung. Für unbekannte Fach-IDs verwendet der Screen einen
neutralen Punkt.

Die horizontale Bedienung umfasst Trackpad, Scrollbar, sichtbare
Links-/Rechtssteuerung und Tastatur mit sichtbarem Fokus und Accessible Names.
Normales vertikales Scrollen bleibt Eigentum der äußeren Profilscrollfläche.
Bei Resize wird die Position möglichst erhalten; war die Timeline am neuesten
Ende, bleibt sie dort. Bei Refresh verwendet das Widget eine stabile
gelieferte Ereignisidentität als Anker und trifft keine neue Inhaltsauswahl.

Die Shell besitzt ausschließlich die Navigation mit vorhandenen Student-,
Draft-, Revisions-, Fach-, Beobachtungs- und Kompetenz-IDs. Sie berechnet
weder Zeitraum noch Ereignisse, Zähler, Bestätigungsstand oder historische
Zugehörigkeit.

Der Berichtsbereich ist eine neutrale Belegübersicht im gewählten
Berichtszeitraum und keine Entwicklungsanalyse. `Überblick` bleibt Eigentümer
der kompakten Lernentwicklungsdarstellung; `Kompetenzen` bleibt Eigentümer der
detaillierten Kompetenz- und Belegansicht. Eine gemeinsame Timeline ist keine
gemeinsame Bericht-/LEG-Domain. RPD/RPT/RPV
und LCD/LCF/LCV behalten getrennte Aggregate, Repositories, Application
Services, Integritätsprüfungen, Revisionen, Statusbegriffe und Lifecycle.
Die automatisierten Offscreen-Prüfungen decken Rendering, Navigation,
Tastatur- und Scrollvertrag ab; eine reale macOS-Trackpad- und
VoiceOver-Abnahme bleibt separat offen.

## Berichte-Übersicht 0.3.1 / Paket 1

Dieser Abschnitt ist die historische Eigentumsbasis von Paket 1. Seine
Meilenstein- und Nennerdarstellung ist im sichtbaren Berichtsbereich durch den
vorstehenden Phase-2-Vertrag ersetzt.

`StudentDesktopAdapter.report_overview_for_student` besitzt die
Kompositionsgrenze. Er fragt Berichtsdrafts und Berichtrevisionen sowie
LEG-Drafts und LEG-Revisionen über ihre jeweils vorhandenen getrennten
Application Services ab. `ReportOverviewViewModel` normalisiert diese
Ergebnisse ausschließlich für die Anzeige, markiert Integritätsfehler und
sortiert die gemeinsame Historienanzeige.

`StudentProfileScreen` besitzt nur Widget-, Scroll-, Fokus- und
Responsive-State. Es berechnet weder Draft-/Revisions-/Abschlussstatus noch
Zeitraumgültigkeit, Integrität, nächste Schritte oder fachliche Zählwerte. Ohne
eindeutigen RPD zeigt es keinen inhaltlichen Berichtstand. Für die
Meilensteinleiste darf es bereits displayfertige Bericht-/LEG-Historieneinträge
und reale Bestätigungsereignisse aus dem vorhandenen Profildashboard zeitlich
anordnen und rein nach verfügbarem Platz begrenzen. Es leitet daraus weder
Kompetenzabschluss noch Entwicklung, Stärke, Priorität oder Empfehlung ab.

Die Fachübersicht behält die Reihenfolge der vorhandenen
`LearningReportPreparationViewModel.subjects`. Der Screen zeigt zunächst
höchstens vier Fächer und erweitert nur nach bewusster lokaler Aktion; diese
Sichtbarkeit ist keine Auswahl und wird nicht persistiert. Dokumentierte und
aktuelle Kompetenzanzahl sowie Beobachtungsanzahl werden unverändert aus dieser
bereits kanonischen Berichtsvorbereitung übernommen. Das wiederverwendete
Kreisdiagramm aus dem Schülerprofil visualisiert
ausschließlich das neutrale Zahlenverhältnis; der Screen erzeugt daraus weder
Dokumentationsurteil noch Empfehlung.

Die Shell besitzt die technische Navigation über `student_id`,
`report_draft_id`, `learning_conference_draft_id`, Revisions-ID und
`subject_id`. Mehrdeutige Draftzustände führen zwingend in die vorhandene
Auswahl. Eine ausdrücklich gewählte Draft-ID bleibt nur als flüchtiger
Shell-Navigationszustand erhalten und wird weder persistiert noch aus
`updated_at` abgeleitet. Der `LearningReportDialog` bleibt der einzige Editor; seine neue
Fachfokusgrenze setzt nur vorhandene Navigation, Scrollziel und Tastaturfokus.

Die gemeinsame Historienkarte ist keine gemeinsame Domain. Bericht und LEG
behalten eigene Repositories, Aggregate, Statusverträge, Snapshots,
Revisionen, Abschlussbegriffe und PDF-Artefakte.

Die früheren unteren Karten `Kompetenzauswahl` und `Berichtarbeitsraum` sind
keine eigene View oder Ownership-Grenze und werden nicht mehr in der Übersicht
gerendert. `LearningReportDialog` bleibt unverändert der einzige Editor.

## Pilot-Releaseautomation - technischer Prozess ohne View

`ReleasePilot` besitzt ausschließlich die technische Orchestrierung und
sanitierte Terminalausgabe. Es entsteht keine View, kein ViewModel und kein
Desktop-Adapter. PySide-Widgets, Produktservices und SQLite-Repositories
besitzen keine Release-, GitHub-, Appcast-, Signatur-, Manifest- oder
Buildlogik.

## P1-Paket 1 - kanonische Frischeprojektion ohne Widget-Ownership

`SQLitePersistenceEventRepository` besitzt die technische Ereignislesesicht.
`StudentDesktopAdapter.list_competency_status_projection_for_student` bleibt
die einzige kanonische Live-Projektion für Profil, Kompetenz-Cockpit,
Berichtsvorbereitung und LEG. Sie trennt aktive Evidence von der technischen
Frischeordnung und projiziert zusätzlich `confirmation_unknown`.

Widgets und Dialoge zeigen nur den gelieferten Zustand und den verbindlichen
Text `Bestätigungsstand unklar – bitte erneut bestätigen`. Sie vergleichen
weder Datumsfelder noch Ereignisse und besitzen keine SQLite-, Journal-,
Lock-, Staging-, Hash-, Dateipublikations- oder Recoverylogik.

`ObservationPersistenceUnitOfWork` besitzt den gesamten schreibenden
Observation-/Attachment-Prozess. Der Dialog besitzt ausschließlich sein
flüchtiges, über Retry stabiles `operation_token`. Alte unveränderliche
Bericht- und LEG-Revisionen werden nicht live neu projiziert oder migriert.
Im internen Cipher-Modus besitzt derselbe UoW zusätzlich die journalgebundene
Reihenfolge zwischen Final-V4-Fachcommit und Companion-Pointer. Der
`EncryptedObservationAttachmentRuntime`-Port besitzt nur Containerprepare,
Verifikation, Aktivierung/Deaktivierung und Consumerstream; er entscheidet
weder fachliche Zuordnung noch MED-ID.

## Security Sprint 12 - bestehender Über-Dialog und technische Testreports

Der vorhandene `AppInfoDialog` projiziert zusätzlich ausschließlich
`APP_VERSION` und `APP_BUILD_VERSION` aus `src.version`. Er besitzt keine
Build-, Appcast-, Gate-, Keychain-, SQLCipher- oder Releaseentscheidung.

Gate-Off-, Gate-On-, Bundle- und Keychain-Smokes liefern nur sanitierte
technische JSON-Testreports an den aufrufenden internen Prüfprozess. Sie sind
keine Produkt-View, kein ViewModel und keine sichtbare Recoveryführung.
Widgets besitzen weiterhin keine Security-, Repository- oder Dateisystemlogik.

## DMK-Database-Key-Runtime - Foundation ohne View

`DatabaseKeyRuntime` besitzt ausschließlich die Qt-freie First-Run-, Restart-
und Publishgrenzen-Orchestrierung. `DataMasterKeyService` besitzt den DMK-
Lifecycle, `SQLiteDataKeysetRepository` die nicht geheimen Keyset-/Phasen-
Metadaten, `MacOSDataMasterKeyStore` den Keychain-Zugriff,
`DatabaseKeyEnvelopeService` HKDF/AES-GCM und
`FileDatabaseKeyEnvelopeRepository` die authentisierte Registry. Es gibt
keine View-, ViewModel-, Widget-, Startup- oder fachliche Adapter-Ownership.

## Final-V4-SQLCipher-Runtime - technische Composition ohne View

`FinalV4SQLCipherRuntimeGate` besitzt ausschließlich die zusätzliche
Marker-/Rootzulassung. `FinalV4SQLCipherRuntimeCoordinator` besitzt
First-Run-/Restart-Klassifikation und Providerkomposition.
`KeyedFinalV4CompatibilityInspector` besitzt nur die mutationsfreie Prüfung
der bereits geöffneten keyed Connection. Nach Erfolg besitzt die zurückgegebene
`SQLiteDatabase` dieselbe Provider-/Keybindung für vorhandene Repositories und
Desktop-Adapter; der Anwendungssmoke konsumiert daraus vorhandene ViewModels.

Kein Widget, ViewModel oder Adapter entscheidet über Gate, Schlüssel,
Neuanlage, Cipher- oder Schemakompatibilität. Es entsteht keine Produkt-
Composition-Root, Shellverdrahtung oder sichtbare Recoveryführung.

## Final-V3-Dokumentcontainer-Runtime - technische Ownership ohne View

`FinalV3DocumentConnectionFactory` besitzt ausschließlich den pfad- und
Database-Key-gebundenen Companion-DB-Open. `FinalV3DocumentSchemaV1` besitzt
Schema-, Context- und Pointerprüfung. `FinalV3DocumentRuntime` besitzt
Containerinventar sowie `prepare`, `activate`, `deactivate`, `read` und
`replace`; der
injizierte Consumer besitzt nur vorläufig empfangene Klartextchunks und muss
`abort` respektieren.

Der `StudentDesktopAdapter` reicht aktive fachliche Beobachtungsreferenzen und
aktive allgemeine Schülerdokumentreferenzen über MED-ID an denselben Reader
weiter. `ManagedStudentDocumentService` besitzt ausschließlich den
journalisierten fachlichen Create-/Replace-/Remove-/Retry-Lifecycle; die
Security-, Container- und Pointerlogik bleibt allein im gemeinsamen
`ManagedDocumentStore`. Widgets und ViewModels besitzen weiterhin keine
Runtime-Ownership. Die vorhandenen Bericht-/LEG-PDF-Services sind hinter dem
Gate ausschließlich binäre Quellen für `ManagedPdfArtifactLifecycle`; RPA und
LCA bleiben getrennte fachliche Artefakte und derselbe Store besitzt allein
Container, Generation und Reader. Es gibt keine Export-, Preview-, Backup-, Restore-,
Migrations-, GC- oder Produktstartup-Ownership.

`StudentDocumentViewModel.managed_encrypted` ist ausschließlich eine
Adapterprojektion für die Aktionswahl: verschlüsselte allgemeine Dokumente
zeigen `Ersetzen` und `Entfernen`, aber keine OS-Öffnung. `AppShell` übernimmt
im Cipher-Produktmodus verpflichtend den bereits vollständig keyed
`StudentDesktopAdapter`; die Shell entscheidet weder Gate noch Schlüssel und
erzeugt keinen zweiten Provider.

## Verschlüsseltes Final-V4-Pilotbackup - technische Ownership ohne View

`FinalV4EncryptedBackupService` besitzt Writer-Lock, Snapshotkoordination,
Inventar-/Crossbindingprüfung, verschlüsselten Container, Neuverifikation,
Restore-Staging und READY-Reverifikation. SQLCipher-Factories besitzen ausschließlich keyed Open und
Schema-/Engineprüfung; Document-Runtime und Companion-DB bleiben Owner von
Generationen und Containern. `SQLiteDataKeysetRepository` besitzt nur den
konsistenten Metadatensnapshot. Kein Widget oder ViewModel besitzt Schlüssel,
Manifest, Staging, `RESTORE_READY` oder Live-Austausch.

`FinalV4EncryptedRestoreHandoffService` besitzt nur den DMK-authentisierten
same-installation Handoff. Die Bootstrap-Recovery besitzt ausschließlich die
vor Product-Open ausgewertete Handoff-/Journal-/Rollen-Evidenz und den
read-only bestehenden DMK-/Envelope-Kontext. `FinalV4EncryptedLiveRestoreService` besitzt die
Cipher-Strategie des vorhandenen `ProductiveRestoreService`; der bestehende
Restore-Worker bleibt Owner von Instanz-Lock, Parent-EOF, Journalphasen,
Write-ahead-Renames, Rollback und Restart-Handshake. Backup-Service und der
technische Restore-Verifier besitzen die Safety-, READY-, Installed- und
Rollback-Reopen-Prüfungen. Nach Auth besitzt allein die Cipher-
Produktkomposition Fachdatenbank und Document Store. Security Store,
AppPreferences und Keychain bleiben
außerhalb der Restore-Ownership.

Die bestehende Backup-/Restore-Oberfläche bleibt im Cipher-Modus vollständig
gesperrt; ZIP-v1 ist dort nicht erreichbar. Eine spätere sichtbare Aktivierung
benötigt eine eigene UX-Entscheidung; dieses Paket verdrahtet keine View.

## Security Sprint 11 - Integration ohne neue View

`SecurityIntegrationGate` und `SecurityIntegrationOrchestrator` besitzen die
rein technische Gate-, Preflight-, Migrations- und Recoverykoordination.
`SecurityIntegrationConnectionFactory` besitzt Engine-/Key-Open und
Integritätsvalidierung. `SecurityDocumentApplicationAdapter` besitzt
Container-/Generationsoperationen und die transaktionale Pointer-Umschaltung.
`SecurityEncryptedBackupAdapter` besitzt Backupinventar, Containerverifikation
und Restore-Staging.

Es entsteht keine View, kein ViewModel, kein Dialog, kein sichtbarer Schalter
und keine normale Startup-Projektion. Die bestehenden Dokument-, Backup- und
Restoreansichten bleiben außerhalb des Gates unverändert. Widgets besitzen
keine Gate-, Key-, SQLCipher-, Journal-, Replay-, Container-, Repository-,
Migrations- oder Dateisystemlogik. Sanitierte technische Testreports sind
keine Produkt-View.

## Security Sprint 10 - Foundation ohne View

Core Security besitzt Document-Key-Domain-Separation, eigenes Envelope,
kanonisches Dokumentformat und fail-closed Parsing. Der isolierte
Security-Prototyp besitzt Synthetikquellbindung, Streaming, Retained-/
No-Clobber-Publikation, Verifikation, kontrollierten Reader, bewussten
Testexport, Rewrap, Austauschsimulation und GC-Dry-Run ausschließlich im
injizierten Sprint-10-Root.

Es gibt keine View, kein ViewModel, keinen Desktop-Adapter und keine Startup-,
Produktdokument-, Viewer-, Export-, Backup- oder Restore-Ownership. Widgets
besitzen keine Schlüssel-, Container-, Manifest-, Lifecycle-, Repository-
oder Dateisystemlogik. Eine spätere Produktintegration benötigt eine eigene
Product-Owner-, Datenmodell-, Lifecycle-, UX-, Ownership- und
Mapping-Freigabe.


## Security Sprint 7B - Foundation ohne View

Security Sprint 7B besitzt keine View, kein ViewModel, keinen Desktop-Adapter
und keine Shell- oder Startup-Projektion. `MigrationCrossbindingContext`, die
authentisierte Lock-Transitionskette und `derive_migration_preflight` gehören
ausschließlich zur Qt-freien Security-Domain beziehungsweise isolierten
Security-Infrastruktur.

Widgets, Dialoge, Shell, Login, Einstellungen und Backup/Restore besitzen
keine Ownership an Locktransitionen, Crossbinding oder Preflight-Modi.

## Security Sprint 6 - Foundation ohne View

Security Sprint 6 besitzt keine View, kein ViewModel, keinen Desktop-Adapter
und keine sichtbare Produktprojektion. `MonotonicSecurityAnchorStore` besitzt
den Anchor-Plattformvertrag, `MigrationLockPort` den Lockvertrag,
`ExclusiveMigrationLock` ausschließlich den technischen POSIX/macOS-Lock im
injizierten Test-Root und `PrototypeMigrationRecoveryOrchestrator` die
eng begrenzten ausführenden Testoperationen einschließlich retained Quarantine
ohne Löschownership. Ein späterer handlebasierter Bereinigungsprozess besitzt
in Security Sprint 6 ausdrücklich keinen Owner. Domain und Prototyp entscheiden;
Infrastruktur persistiert beziehungsweise operiert nur nach diesem Vertrag.

Widgets, Shell, Login, Einstellungen, Backup-/Restore-Controller und
Support-Reset besitzen weder Anchor-, Lock-, Journal-, Migrationspfad- noch
Recovery-Ownership. Auth-Recovery-Codes und technische Migrations-Recovery sind
getrennte Domänen; keine Sprint-6-Komponente liest oder schreibt
`security.sqlite.recovery_codes`.

## Security Sprint 5 - Foundation ohne View

Security Sprint 5 besitzt keine View, kein ViewModel, keinen Desktop-Adapter
und keine sichtbare Produktprojektion. `DatabaseKeyEnvelopeService`,
`AuthenticatedMigrationJournalRepository` und `MigrationRecoveryEvaluator`
bleiben Qt-freie Security-Bausteine; `SecureMigrationPrototypeEngine` gehört
ausschließlich zum synthetischen Prototyp. Widgets und Shell besitzen weder
Schlüssel-, Envelope-, Journal-, Pfad- noch Recovery-Ownership.

## Security Sprint 4 - Prototyp ohne View

Security Sprint 4 besitzt keine View, kein ViewModel, keinen Desktop-Adapter
und keine sichtbare Produktprojektion. `MigrationPrototypeEngine`,
`DatabaseSnapshot`, `ValidationResult` und `MigrationReport` gehören nur zum
Qt-freien technischen Prototyp. Konsolen-JSON aus dem isolierten Runner ist ein
Testprotokoll und kein Produkt-View. Kein Widget erhält Engine-Auswahl,
Schlüssel, Pfade, Migrationsstatus oder Fehlerdetails.

## Security Sprint 3 - Infrastruktur ohne View

Security Sprint 3 besitzt keine View, kein ViewModel und keine sichtbare
Projektion. `SQLCipherConnectionProvider` gehört ausschließlich zur Qt-freien
technischen Infrastruktur. Widgets, Shell, Dialoge, Adapter und bestehende
Repositories erhalten weder Engine-Auswahl noch Schlüsselmaterial oder
SQLCipher-Fehlertexte. Der technische Smoke ist kein Produkt-View.

## Security Sprint 2 - Foundation ohne View

Es gibt keine View-Ownership. `DataMasterKeyService` besitzt die
Lifecycle-Orchestrierung, `DataKeysetRepository` ausschließlich technische
Metadaten und `DataMasterKeyStore` den Plattformzugriff auf Secret-Material.
Widgets, Shell, ViewModels und fachliche Adapter erhalten keinen DMK-,
Fingerprint-, Envelope- oder Storezugriff.

## Sprint 0.2S.1 - Eigenständige Support-Assistent-Ansicht

`SupportAssistantWindow` besitzt nur flüchtigen Schritt-, Fokus-, Datei-,
Installationsname-, Passphrase- und Ergebniszustand. Sie erhält geprüfte
`SupportRequestProjection`- und `SupportKeyProjection`-Werte vom
`SupportAssistantApplicationService`. Die View decodiert kein Protokoll,
entscheidet keine Schlüsselgültigkeit und implementiert keine Signatur.

Dateidialoge öffnen ausschließlich nach bewusster Aktion. Die View besitzt
keine Ownership auf fachliche SQLite, Security Store, AppPreferences,
Dokumente, Backups oder Produkt-Runtime. Der Auditadapter darf ausschließlich
die vier registrierten technischen Felder schreiben. Das Token bleibt bis zum
Schließen flüchtig und gelangt nur durch `Kopieren` oder `Datei speichern` nach
außen.

## Sprint 0.2U.2 - Updateansicht und Pilot-Onboarding

Die Unterseite `Updates` besitzt ausschließlich die read-only Projektion aus
`UpdateApplicationService`: sichtbare Version, Build, fester Kanal, letzter
Prüfzeitpunkt und lokalisierter Status. Sie lädt keinen Feed, prüft keine
Signatur, entpackt kein Archiv und ersetzt keine App. Diese Verantwortung liegt
bei Sparkle hinter `MacOSSparkleAdapter` und der nativen C-ABI-Bridge.

`OnboardingScreen` besitzt für den Pilot-Zusatzschritt nur Text und Aktionen.
`AppShell` navigiert zur vorhandenen Datensicherungsseite und startet deren
Dateiauswahl. Backupprüfung, Restore-Vorschau, Bestätigung, Worker und Recovery
bleiben vollständig bei den vorhandenen Controllern und Services. Es gibt keine
automatische Dateisuche und keine fachliche Ownership in der Onboarding-View.

## Sprint 0.2B.6 - Externe Support-Terminalansichten

`support_reset_cli` besitzt nur flüchtigen Promptzustand: gewählte Anfrage,
technische Anfrageprojektion, bewusste Bestätigung, Pfade, begrenzte Laufzeit und
optionale Tokenanzeige. Das Tool liest weder fachliche SQLite noch Backups oder
Dokumente. Anfrageprüfung und Tokenformat bleiben im vorhandenen Qt-freien
`SupportResetTokenCodec`; Kryptografie bleibt im vorhandenen Generator.

`keypair_cli` besitzt nur den bewussten externen Zielpfad, `key_id` und die
zweimalige verdeckte Passphraseeingabe. `generate_support_keypair` besitzt
Erzeugung und atomare Publikation. Weder Terminalansicht noch Generator besitzen
Registry-, App-, Build- oder Fachdatenownership.

## Sprint 0.2R - Dokumentation und Release-Screenshots

Der Release-Abschluss führt keine neue View und keinen UI-State ein. Handbuch,
Handouts und Screenshots bilden ausschließlich vorhandene Auth-, Onboarding-,
Shell-, Settings-, Lock-, Backup/Restore- und Support-Reset-Views ab.
Screenshots besitzen keine Datenhoheit und verwenden leere oder künstliche
neutrale Projektionen ohne Passwörter, Recovery-Codes, Tokens, Schülerdaten oder
lokale Pfade. Offscreen-Zustände ersetzen keine reale Hardwareabnahme.

## Sprint 0.2B.5 - Support-Reset-Ansicht

`SupportResetDialog` besitzt ausschließlich flüchtige Anzeige-, Eingabe- und
Schrittzustände: datensparsame Anfrageprojektion, bewusst angezeigten
kanonischen Exporttext, Token-Eingabe bis zur Prüfung, Bestätigung und
Workerstatus. Nach Fehler, Abschluss oder Schließen werden Tokenfeld und
geprüfter Token verworfen. Die View liest weder SQLite noch Key Registry,
verifiziert keine Signatur und erstellt kein Backup selbst.

`SupportResetService` besitzt Anfrage, Bindungsprüfung und atomaren Reset.
`FinalV4PreAuthRecoveryVerifier` besitzt ausschließlich die existing-only
DMK-/Key-/Final-V4-/Companion-/Managed-Document-Prüfung und den Aufruf des
vorhandenen verifizierten `.jkmebackup`-Service. Er liefert keine Fachprojektion
an die View. `FinalV4PreAuthRecoveryFactory` injiziert im Auth-Gate nur
RuntimePaths und Security-Store-Port; `FinalV4SupportResetBackupFactory`
verwendet in Settings die bereits geöffnete Runtime. Der Desktop-Controller
besitzt Worker, Dateidialoge, Zwischenablageaktion, Sperr-/Sitzungshandoff und
App-Ende.

Im Auth-Gate bleibt die Fach-UI nicht konstruiert. Im Settings-Einstieg ist der
Dialog modal; laufende fachliche Backup-/Restore-Operationen verhindern einen
parallelen Start. Während des Support-Backups kann die zentrale opake Sperre den
Dialog vollständig verdecken, ohne den Worker abzubrechen. Nach erfolgreichem
Commit gibt es keine Rückkehr in den verdeckten Widgetbaum.

## Sprint 0.2B.4a - Geräteanmeldung und lokale Entsperrung

Login- und Sperransicht besitzen ausschließlich temporäre Eingabe-, Anzeige-
und Busy-Zustände. Sie erhalten eine datensparsame Projektion aus dem
`DeviceCredentialService`: ob eine gültige gespeicherte Anmeldung vorliegt, ob
lokale Authentifizierung verfügbar ist und welches generische Ergebnis
vorliegt. Sie lesen weder Security SQLite noch Schlüsselbund und rufen keine
Frameworks direkt auf.

Die bestehende Unterseite `Sicherheit` besitzt lokalen Bedienzustand für
`Auf diesem Gerät angemeldet bleiben`, `Touch ID zum Entsperren verwenden` und
`Gespeicherte Anmeldung widerrufen`. Der Security Coordinator vermittelt alle
Schreibaktionen über Application-Ports, aktualisiert den Status aus dem
kanonischen Security Store und hält Plattformdetails aus Widgets fern.
`AppShell` bleibt reiner Signal-/Navigationsowner.

Bei fehlender eingerichteter Biometrie, fehlendem Credential oder nicht
lesbarem Secret projiziert die Unterseite nur einen verständlichen Grund und
eine deaktivierte Bedienaktion. Sie erzeugt oder repariert kein Credential und
liest weder Keychain noch Security SQLite direkt.

Der Security Application Service besitzt Credential-Lebenszyklus,
Epoch-Prüfung, Verifikation und Widerruf. `SQLiteSecurityRepository` besitzt
Metadaten, der Plattformadapter ausschließlich das Secret. Die Fach-UI, ihre
Adapter und Repositories erhalten keinerlei Lese- oder Schreibownership. Die
opake Sperre und der erhaltene unsichtbare In-Memory-Widgetzustand bleiben
unverändert.

## Sprint 0.2B.4 - Authentifizierung und Sicherheit

`AuthenticationDialog` besitzt ausschliesslich temporaere Eingabewerte,
sichtbaren Authzustand, generische Fehlermeldung, Sperrzeit und die einmalige
Anzeige neu erzeugter Recovery-Codes sowie bei Erstkonto/Legacy-Aufnahme den
optionalen Begruessungsnamen. Es liest weder fachliche SQLite-Daten
noch fachliche Adapter oder Projektionen. Secrets werden nicht in ViewModels,
Logs, Zwischenablage oder Dateien uebernommen.

Die Einstellungs-Unterseite `Sicherheit` liest eine datensparsame Projektion aus
dem Security Application Service und `AppPreferencesFile`: aktiver
Passwortschutz, aktuelles Inaktivitaetsintervall, lokale persoenliche
Begruessung und erlaubte Aktionen. Der Profilbereich schreibt ausschliesslich
ueber den injizierten Preferences-Adapter, Security-Aktionen ueber injizierte
Security-Services. `AppShell` leitet
`Jetzt sperren` weiter und besitzt weder Kryptologie noch Security-SQLite.

Das Dashboard besitzt read-only Ownership auf den injizierten lokalen
Zeitpunkt und `AppPreferences.display_name`. `dashboard_greeting` erzeugt nur
die Klartextbegruessung; Stundenplan-, Schueler- und Fachdaten werden dafuer
nicht gelesen. `AppShell` reicht den Wert weiter, besitzt aber keine
Profilpersistenz.

Die Dokumentations-Heatmap und die Schuelerliste beziehen ihre bestehende
Dokumentationsstatusprojektion für die Mitglieder eines refresh-lokalen
`CurrentMembershipReadSnapshot`. Globale Defaults sowie individuelle
schuljahresbezogene Profile und Auswahlen werden gebündelt im selben Batch
gelesen; der Adapter löst daraus je Kind die kanonische effektive Fachmenge
auf. Assignment- und Dokumentationsreads werden durch den aufrufenden Adapter
auf derselben Connection und im selben transaktionskonsistenten Read-Snapshot
komponiert; weder
`SQLiteStudentDocumentationProjectionRepository` noch
`SchoolYearAssignmentReadSession` besitzt die Transaktionssteuerung.
`StudentDesktopAdapter` bleibt Owner der Gruppierung, kanonischen
Dokumentationsabdeckung und Sortierprojektion, zählt Mitgliedschaften aber
nicht in Python nach. Die vollstaendige Bestätigungsfrische bleibt fachlich
gleich projizierbar, beeinflusst aber nicht die Regel, ob eine konkrete
Kompetenz dokumentiert ist. Screens und Widgets lesen weder Repositories noch
SQLite direkt. Die Projektionen führen keine DDL aus und werden nicht ueber
den jeweiligen Refresh hinaus gehalten.

`OnboardingScreen` besitzt nur sichtbaren Schritt-, Text-, Button- und lokalen
Fokuszustand. Persistenz gehoert `OnboardingController` und
`AppPreferencesFile`; Navigation gehoert `AppShell`. Kleine Statuszeilen für
Stammgruppe, Kurs, Stundenplan und Schüler werden aus bestehenden
Adapter-/ViewModel-Projektionen als aggregierte Ja/Nein-Werte übergeben. Der
Backuphinweis verwendet ausschließlich das Vorhandensein einer Datei mit der
vom aktiven Backupadapter vorgegebenen Endung im bestehenden Runtime-
Backupbereich und behauptet keine Verifikation. Die View liest keine SQLite-
Daten direkt, zeigt keine Schülernamen, Prozentwerte oder Bewertungen,
blockiert keinen Schritt und schreibt keine fachlichen Daten. Die globale
Dokumentationsfachauswahl ist kein Onboardingstatus.

`SecurityUiCoordinator` besitzt den rein technischen sichtbaren Lock-State. Er
versteckt bei Sperre alle fachlichen Top-Level-Fenster und zeigt eine vollstaendig
undurchsichtige neutrale Authentifizierungsansicht. Die fachlichen Widgets
behalten ihren In-Memory-State, bleiben aber waehrend der Sperre ohne sichtbare
Ownership. Backup-Ergebnisse werden gepuffert; unbestaetigte Restore-Vorschauen
werden ueber die vorhandene Settings-View geleert.

Dieses Dokument definiert, welche Datenquellen eine Ansicht lesen oder schreiben darf.

Eine neue Ansicht darf nicht umgesetzt werden, bevor ihre Datenverantwortung hier dokumentiert ist.

Jede Ansicht besitzt genau definierte Datenquellen.

Eine Ansicht darf ausschliesslich auf die in diesem Dokument eingetragenen Datenquellen zugreifen.

Neue Datenquellen duerfen nur nach Erweiterung dieser Dokumentation in einer Ansicht verwendet werden.

Eine Ansicht darf nur fachlich erforderliche Datenquellen lesen.

Sprint 0.2A.3b fuehrt keine neue Ansicht ein. Restore-Pruefung, persistentes Staging, vorbereitete V1-Kopie, Pfad-Rebasing, Managed-File-Materialisierung, Prepared-Verifikation, Cleanup und Sicherheitsbackup bleiben reine Core-/Application-Betriebsfunktionen. Keine bestehende PySide-Ansicht erhaelt Lese- oder Schreibownership auf `restore-staging/`, `staging-state.json` oder `backups/restore-safety/`. Eine spaetere Restore-UI benoetigt eine eigene Product-Owner- und Ownership-Freigabe.

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

Die macOS-Laufzeitvorbereitung liegt vor dem Aufbau der Views. Sie projiziert keine fachlichen Inhalte, sondern stellt ausschliesslich den getrennten lokalen Benutzerpfad bereit. Pfadfehler werden vor dem Start der Arbeitsansichten verstaendlich gemeldet. Views kennen weder Bundlepfad, Startdatenvariante, Backupordner noch Signierungsstatus.

Die SJ-2F-Schreibpfade für Schüler lauten:

```text
PySide6 GUI
-> StudentDesktopAdapter
-> getrennter V3-Application-Lifecycle
-> V3StudentRepository und/oder StudentSchoolYearAssignmentRepository
-> SQLite students und/oder student_school_year_assignments
```

Excel liegt nur noch als archivierter Legacy-Altstand unter `legacy/excel/`.

## Allgemeine Backup-Betriebsfunktion ohne View

Sprint 0.2A.2 fuehrt keine Ansicht und keine sichtbare UI-Aktion ein. Der Application Service darf fuer eine ausdrueckliche technische Ausfuehrung die produktive SQLite-Datenbank, `RuntimePaths`, Buildinformationen und den Zielordner lesen. Der Core-Service liest aus dem erzeugten Snapshot Counts und das registrierte Dateiinventar; er schreibt ausschliesslich temporaere Stagingdaten und das neue `.jkmbackup` im explizit injizierten Zielordner.

Die Funktion darf keine Qt-Widgets, Desktop-Adapter, fachlichen Repositories oder UI-Projektionen als Datenquelle verwenden. Sie darf keine Live-Daten, Dokumente, PDF-Artefakte, Exporte, Logs oder vorhandenen Backups veraendern. Externe Referenzen werden nicht in das Archiv uebernommen. Weil keine View entsteht, besitzt das Backup keine UI-Felder, Navigation oder temporaeren UI-State.

## Datenbank-Kompatibilitaet und Restore-Verifikation ohne View

Sprint 0.2A.3a fuehrt weiterhin keine Ansicht und keine sichtbare UI-Aktion ein. `DatabaseCompatibilityInspector` darf eine explizit injizierte SQLite-Datenbank ausschliesslich read-only fuer `PRAGMA user_version` und die registrierte nicht-interne Schemastruktur lesen. `RestoreVerifier` darf ein explizit injiziertes `.jkmbackup` nach erfolgreichem `BackupVerifier` nur in einem isolierten kurzlebigen temporaeren Verzeichnis lesen.

Die technische `RestorePreview` ist kein Screen und kein persistenter UI-State. Sie darf ausschliesslich technische Versionen, Kompatibilitaetsstatus und aggregierte Counts enthalten. Namen, Notizen, Beobachtungs-, Bericht- oder LEG-Texte, Dateinamen, fachliche IDs und Pfade sind nicht freigegeben. Die Funktion darf keine Qt-Widgets, Desktop-Adapter, fachlichen Repositories oder Live-Daten lesen oder veraendern und kein persistentes Staging, keine Migration und keinen Austausch ausloesen.

## Produktiver Restore, Worker und Start-Recovery ohne View

Sprint 0.2A.3c fuehrt weiterhin keine Ansicht, sichtbare Aktion oder UI-Projektion ein. Owner der technischen Restore-Steuerung sind Application-Commands und Qt-freie Core-Services. Der Worker und die Start-Recovery lesen ausschliesslich Runtime-gebundene Handoff-, Lock-, Journal-, Staging-, Backup-, Rollback- und Resume-Daten sowie SQLite und Managed Files fuer technische Integritaetspruefungen.

Qt-Widgets, Screens, ViewModels, Desktop-Adapter und fachliche Repositories besitzen weder Lock-, Rename-, Journal-, Rollback- noch Recovery-Verantwortung. Die normale App darf bei offenem kritischem oder widerspruechlichem Restore-Zustand keine View erzeugen.

## PySide6 Einstellungen

Sprint 0.2A.4 erweitert die bestehende Einstellungen-Ansicht um Übersicht und die drei lokalen Unterseiten `timetable`, `documentation_subjects` und `backup_restore`. `SettingsScreen` besitzt nur lokalen Navigations-, Bedien- und Meldungszustand. Stundenplan und Fachauswahl behalten ihre bestehenden Datenquellen. Die Datensicherungs-Unterseite darf nur `BackupSummaryViewModel` und `RestorePreviewViewModel` aus `BackupRestoreDesktopAdapter` lesen und dessen explizite Commands ausloesen; sie besitzt keine SQLite-, Dateisystem-, Lock-, Journal-, Staging-, Rollback- oder Worker-Verantwortung. Der Desktop-Adapter besitzt die bundle-sichere Worker-Startplanung und die bestaetigte Prozessuebernahme. Die Shell projiziert nur Erfolg oder den generischen Startfehler und fordert die App-Beendigung erst nach `worker_started` an.

Sprint 0.2A.4a legt die Qt-Lebensdauer ausserhalb der Unterseite fest: `AppShell` besitzt genau einen `BackupRestoreOperationsController`; dieser besitzt waehrend einer Operation genau einen `QThread` und einen `BackupRestoreOperationWorker` bis `thread.finished`. Der Worker besitzt nur den unveraenderlichen technischen Auftrag und injizierte Application-Services. `SettingsScreen` besitzt ausschliesslich sichtbaren Busy-, Phasen-, Ergebnis- und Fehlerzustand. Seitenwechsel, Screen-Refresh und abgelehnte Close-Ereignisse zerstoeren den Controller nicht. Signale zu bereits zerstoerten Qt-Empfaengern werden durch Qt-Ownership getrennt; Worker und Thread werden per `deleteLater()` entsorgt.

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
- `groups` und `courses` als sichtbare Stammdaten
- `CurrentMembershipReadSnapshot` für aktuelle Zielmitgliedschaften und
  zentral berechnete Schülerzahlen je Stammgruppe, Kurs und Kursverbund
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`
- `competencies`, `documentation_subject_settings`, `student_documentation_subject_profiles`, `student_documentation_subject_selections`, `observations`, `observation_competency_ratings` und `student_competency_confirmations` ausschliesslich ueber die kanonische Dokumentationsstatusprojektion

Schreibt:

- nichts direkt
- startet `Beobachtung erfassen`, `Beobachtung aendern` und `Beobachtung loeschen` ueber freigegebene Adapter-/Service-/Repository-Prozesse

UI-Projektionen:

- zentrale Karte `Für diese Stunde` mit aktueller oder naechster aktiver Stunde und ruhigem Leerzustand
- heutige aktive Stunden als horizontale, zeitbezogen markierte Timeline
- fluechtige Stundenplanvorbelegung fuer den bestehenden Beobachtungsdialog nach bewusster Kindauswahl
- passende Kinder mit textlich sichtbarer Kurszugehoerigkeit und bestehender Kursfarbe als reinem Kontextbadge
- neutrale Mini-Heatmap der Dokumentationsabdeckung je Stammgruppe und Fach; keine Bewertung, Leistung, Rangfolge oder Entwicklungsableitung

Regel:

`Heute` ist eine reine Lese- und Navigationsoberflaeche. Der technische Screen und Schluessel `dashboard` bleiben erhalten. Die Ansicht zeigt den aktuellen Stammdaten-Scope der PySide-App, verwaltet weder Stammdaten noch Stundenplan und schreibt nicht direkt in SQLite. Aktuell, naechste und heutige Stunde stammen ausschliesslich aus `TimetableDesktopAdapter.read_projection(at)`. Derselbe einmalig injizierte Zeitpunkt liefert den `as_of`-Tag für die aktuelle Mitgliedschaft. Zeitstatus wird beim Oeffnen beziehungsweise Aktivieren und hoechstens minuetlich neu gelesen. Assignment-, Dokumentations- und Beobachtungsprojektionen eines Refreshs werden über genau eine `SchoolYearAssignmentReadSession` auf derselben aufrufereigenen Connection und im selben Read-Snapshot komponiert. Der Batch liest individuelle Fachprofile und deren optionale Auswahl mit genau einem konstanten Read; fehlendes Profil bleibt `inherit`, vorhandenes `custom` ohne Auswahl bleibt bewusst leer. Die Heatmap zaehlt je Stammgruppe und Fach nur aktuelle `ENROLLED`-Kinder, deren kanonisch effektive Fachmenge das Fach enthält; überfachliche Bereiche bleiben unabhängig von der Unterrichtsfachauswahl enthalten. Sie zeigt keine Ratings, Scores oder automatischen Entwicklungsurteile. Ihre neutralen Blau-Grau-Abstufungen codieren ausschliesslich Dokumentationsabdeckung und keine Ampelbewertung. Fehlendes current-Schuljahr oder mehrdeutige aktuelle Assignments blockieren die fachliche Projektion und werden nicht als leere Liste oder Nullzählung angezeigt.

Die direkte Kursansicht im Schueler-Arbeitsraum filtert den
`CurrentMembershipReadSnapshot` nach der ausgewaehlten `course_id`. Die
getrennte Kursverbundansicht bleibt kursverbundbezogen und verwendet die
zentrale Schnittmenge aus den registrierten Stammgruppen und Kursen des
Kursverbunds mit den aktuellen Assignments; der Screen expandiert oder
filtert diese Intervalle nicht selbst.

UX-Regel UI Sprint 1: `Heute` und `Schüler` sind die beiden globalen Arbeitsziele. Die Dashboard-Projektionen erscheinen ausschliesslich in einer grossen Hero-Karte, einer horizontalen Tages-Timeline, einer kompakten Stammgruppe-mal-Fach-Matrix und der Karte fuer passenden Unterrichtskontext. Allgemeine Stammgruppen- und Kursverbundkarten gehoeren lokal in den Schueler-Arbeitsraum.

Regel Sprint 8B.3: `Passende Kinder für diese Stunde` liest ausschließlich
aktuelle `ENROLLED`-Kinder aus dem `CurrentMembershipReadSnapshot` für die zur
Stunde gehörende Stammgruppe, den Kurs oder den Kursverbund sowie deren aktive
Beobachtungen und gebündelte individuelle Fachkonfigurationen aus demselben
Read-Snapshot. Vor der bestehenden Sortierung bleiben nur Kinder übrig, für
die das Stundenplan-Unterrichtsfach effektiv relevant ist. Es werden
hoechstens fuenf Kinder als transparente Dokumentationshilfe projiziert.
Reihenfolge und Hinweis
beruhen ausschliesslich auf dem Vorhandensein und Datum einer aktiven
Beobachtung mit eindeutigem Fachbezug; Ratings, Kompetenzstatus,
Leistungswerte und paedagogische Urteile werden nicht gelesen oder berechnet.
Der Screen rendert diese Projektion nur und startet `Beobachten` ueber den
bestehenden Beobachtungsdialog.

## PySide6 Schueler-Arbeitsraum

Liest V3-`students` ausschließlich für Schülerstammdaten, `groups`, `courses`,
`course_groups`, `course_group_student_groups` und `course_group_courses` für
Stammdatendefinitionen sowie genau einen `CurrentMembershipReadSnapshot` für
aktuelle Mitgliedermengen und zentral berechnete Zähler. Schreibt nichts
direkt. `StudentsWorkspace` komponiert die lokalen Segmente `Stammgruppen`,
`Kurse`, `Kursverbünde` und `Alle Schüler`, ohne eine neue Datenquelle zu
besitzen. Stammgruppenkarten, direkte Kurskarten, Schuelerzahlen,
Kursverbuende, Kurszugriffe, Listenfilter und Profilnavigation verwenden
ausschliesslich die bestehenden technischen IDs. Ein einfacher Klick auf eine
Nicht-Aktionszelle, Enter oder die sekundäre Profilaktion navigiert per
`student_id`; eingebettete Zeilenaktionen bleiben davon getrennt.
Dashboard-Daten und Stundenplanprojektionen werden in diesem Arbeitsraum nicht
gelesen.

Der Workspace darf nur lokale Segment-, Drill-down-, Such-, Fokus- und Auswahlzustaende halten. Kursname und Kursfarbe werden in Schuelerliste und Profilkopf ausschliesslich aus der bestehenden Kursprojektion als `CourseBadge` dargestellt. Beobachtung, Kompetenz, Bericht und LEG bleiben im vorhandenen Schuelerprofilkontext und verwenden ihre bereits dokumentierten Lese- und Schreibpfade. Der Workspace berechnet weder Mitgliedschaften noch Dokumentationsstatus und greift nicht direkt auf SQLite zu.

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
- bewusst gewählte Kursstufe 1, 2 oder 3
- Kursfarben
- Aktiv-/Inaktivstatus
- Kursverbundliste
- Bearbeiten-Dialog fuer Kursverbund-Name, Stammgruppen-Auswahl und Kurs-Auswahl

Regel:

Kursverbuende werden persistent in SQLite bearbeitet. Ein Kursverbund
definiert, welche Stammgruppen und Kurse in der kursverbundbezogenen
Kursuebersicht erscheinen. Kursstufe und Stammdatenstatus gehören dem
`SQLiteMasterDataRepository`; die View validiert oder verändert keine
Assignments. Deaktivierung wird bei aktuellen oder zukünftigen
Einschreibungsreferenzen blockiert, historische Referenzen bleiben
unverändert. Die Bearbeitung bucht keine Schueler um und veraendert keine
Beobachtungsdaten.

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

- V3-`students` für Name, Aktiv-/Archivstatus und `student_id`
- `groups` und `courses` für sichtbare Stammdaten
- `CurrentMembershipReadSnapshot` für aktuelle Stammgruppenmitglieder und
  zentral berechnete Schülerzahlen

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

Die Stammgruppenuebersicht ist Auswahl- und Navigationsansicht. Sie verwaltet
keine Schuelerdaten. Sie zeigt ausschließlich aktuelle `ENROLLED`-Mitglieder
am einmalig gesetzten `as_of`-Tag; `EXITED`, `NO_ASSIGNMENT` und archivierte
Schüler erscheinen nicht. Fehlendes current-Schuljahr oder `AMBIGUOUS`
blockiert die Projektion. Sie zählt nicht in Python und löst Assignments nicht
je Kind auf.

## Kursuebersicht

Liest:

- V3-`students` für Name, Aktiv-/Archivstatus und `student_id`
- `groups` und `courses` für sichtbare Stammdaten
- `CurrentMembershipReadSnapshot` für aktuelle Kursmitglieder

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

Die Kursuebersicht ist eine Projektion derselben aktuellen
`CurrentMembershipReadSnapshot`-Daten wie die Stammgruppenuebersicht. Ein
Kursverbundfilter wird zentral als Schnittmenge seiner registrierten
Stammgruppen und Kurse mit aktuellen Assignments aufgelöst; Widgets und
ViewModels filtern keine Assignmentintervalle.

## Schuelerprofil

Liest:

- V3-`students` für Name, Notiz, Aktiv-/Archivstatus und `student_id`
- `CurrentStudentMembershipProjection` aus der
  `SchoolYearAssignmentReadSession` für den einmalig gesetzten aktuellen
  `as_of`-Tag
- `groups` und `courses` ausschließlich als über die zentrale
  Assignmentprojektion aufgelöste sichtbare Stammdaten
- `data_observations`
- `data_observation_competencies`
- `data_competencies`
- `data_subjects`
- `student_competency_confirmations`
- `documentation_subject_settings`
- `student_documentation_subject_profiles`
- `student_documentation_subject_selections`
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
- schuljahresbezogene Fachkonfiguration mit `inherit` oder exakter
  individueller `custom`-Auswahl aus der
  `StudentDocumentationSubjectProjectionViewModel`
- Variante-A-Arbeitsprofil als reine `StudentProfileDashboardViewModel`-Komposition aus der kanonischen Kompetenzstatus- und Dokumentationsstatusprojektion: Profilkopf mit Dokumentationsring, Orientierungskarte, Kompetenzkarte und neutraler Karte `Noch nicht dokumentiert`
- Kompetenz-Cockpit aus der kanonischen Sprint-6B-Statusprojektion mit lokaler Suche sowie Fach- und Dokumentationsfiltern fuer aktive Zeilen und separat historischen Kompetenzen; keine Stage-Segmentierung des einheitlichen Entwicklungsbuch-Katalogs
- Berichtsvorschau aus Kompetenzstaenden und Beobachtungsbelegen
- Dokumente und Medien aus aktiven Dokumentmetadaten
- Aktionen zum Bearbeiten und Loeschen einzelner Beobachtungen
- Aktion zum Entfernen einzelner Dokumente ueber Soft Delete
- Aktion zum Bestaetigen oder manuellen Anpassen eines Kompetenzstand-Vorschlags
- Medienhinweise

Regel:

Das Schuelerprofil zeigt Daten eines Schuelers und startet freigegebene
Schreibprozesse. Es schreibt selbst keine fachlichen Daten und greift nicht
direkt auf SQLite zu. Die bewusste Fachauswahl läuft ausschließlich über
`StudentDesktopAdapter` und `StudentDocumentationSubjectService`; Abbrechen
verwirft nur den lokalen Draft. Der aktuelle Profilkopf zeigt bei `ENROLLED` die zentral
aufgelöste Stammgruppe und den Kurs, bei `EXITED` den neutralen Zustand
`Im aktuellen Schuljahr ausgeschieden`, bei `NO_ASSIGNMENT` `Keine aktuelle
Zuordnung` und bei `STUDENT_ARCHIVED` einen neutralen nicht aktuellen Zustand.
Fehlendes current-Schuljahr oder `AMBIGUOUS` blockiert die aktuelle
Zuordnungsanzeige. Technische Gruppen- oder Kurs-IDs und V2-Schülerfelder sind
keine sichtbaren Fallbacks.

Das Variante-A-Arbeitsprofil wird im Adapter ueber
`build_student_profile_dashboard(...)` ausschließlich aus der kanonischen
Kompetenzstatusprojektion und der bestehenden Dokumentationsstatusprojektion
komponiert. Die Orientierungskarte beruecksichtigt nur reale Beobachtungen und
die vorhandene aktuelle Bestaetigung bis zum uebergebenen Stichtag. Eine
Kompetenz qualifiziert sich nur mit mindestens zwei realen Ereignissen und
einem tatsaechlichen Wechsel zwischen zwei aufeinanderfolgenden dokumentierten
Statuswerten. Sie zeigt hoechstens drei Treffer, sortiert nach juengster
Statusaenderung und danach curricularer Reihenfolge; historische
Snapshot-Texte bleiben lesbar, ohne historische Kompetenzen fuer neue Auswahl
zu reaktivieren. Der Screen rendert diese fertige Projektion und berechnet
weder Statuswechsel noch Counts. Ohne aktive Filter begrenzt die
UI-Projektion den Beobachtungsverlauf auf drei neueste Karten; lokale
Beobachtungsfilter wirken auf alle Beobachtungen, aber nur auf den
Beobachtungsverlauf und nicht auf das Kompetenz-Cockpit. Die zentrale
Leseprojektion
`StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)`
erzeugt genau eine Statuszeile je aktiver `current`-Kompetenz sowie je
historisch referenzierter Kompetenz. Sie trennt Beobachtungsvorschlag,
Bestaetigung und chronologische aktive Nachweise; Soft Deletes bleiben
ausgeschlossen. Sprint 6C gruppiert ausschließlich diese kanonischen Zeilen
als Fach -> Kompetenzbereich -> Thema -> Kompetenz und aggregiert
dokumentiert/gesamt, ohne einen zweiten Kompetenzstatus zu berechnen. Die
lokalen Cockpit-Filter beschraenken nur sichtbare aktive Zeilen; sie
kombinieren Fach mit dem kanonischen Dokumentationszustand, mutieren keine
Daten und behalten die Fortschrittswerte aus dem vollstaendigen aktiven
Zielbestand innerhalb der effektiven Fachmenge. Der fachbezogene Eintrag
`Alle Kompetenzen` erweitert ausschließlich die sichtbare Fachmenge; eine
Stage-Segmentierung wird nicht angeboten. Alle Cockpit-Ebenen starten geschlossen; der Aufklappzustand
bleibt lokal je geoeffnetem Schueler und wird beim Filtern fuer weiterhin
sichtbare Ebenen erhalten. Historische Zeilen werden separat unter
`Historisch dokumentiert` dargestellt und nicht mit aktiven Zielen gefiltert.
Kompetenzstand-Vorschlaege werden aus aktiven Beobachtungen und SQLite
`competencies` abgeleitet. Bestaetigte Kompetenzstaende sind paedagogische
Entscheidungen und liegen separat in `student_competency_confirmations`. Der
Dokumentationsstand ist eine abgeleitete Auswertung aus aktivem
`current`-Kompetenzkatalog, aktiven Beobachtungen, bestaetigten
Kompetenzstaenden und der über `StudentDocumentationSubjectService`
aufgelösten Schüler-/Schuljahrfachmenge; er zaehlt konkrete
Kompetenz-IDs je Fach und Kompetenzbereich, speichert nichts und ist keine
Bewertung. Nicht dokumentationsrelevante Faecher zaehlen nicht als offen,
bleiben aber in Beobachtungsverlauf, Kompetenz-Cockpit und Berichtsvorschau
sichtbar, wenn echte Beobachtungen oder bestaetigte Kompetenzstaende
vorliegen. Dokumente und Medien werden aus SQLite `documents` gelesen; Dateien
liegen im Dateisystem und werden bei vorhandener `file_path` ueber das
Betriebssystem geoeffnet. Die Berichtsvorschau ist eine abgeleitete Struktur
aus bestaetigten Staenden, Vorschlaegen und aktiven Beobachtungsbelegen; sie
speichert keine Berichtsdaten und erzeugt keine finalen Zeugnisformulierungen.
Kopieren und einfacher Textdatei-Export sind Ausgabeaktionen, keine fachliche
Persistenz.

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

Der Dialog besitzt den flüchtigen Weitererfassungszustand und setzt ihn erst
nach bestätigtem Adapter-Erfolg zurück. Die Shell wertet ausschließlich den
Erfolgsbeleg `has_saved_observation` aus, um auch nach späterem Abbruch die
vorhandenen Ansichten neu zu lesen. Persistenz und Atomarität bleiben bei
Application-/Domain-Service, Repository und Managed-Document-Lifecycle.

Die Shell besitzt die fenstergebundene Aktion `⌘N` und die Auflösung des
sichtbaren Kindkontexts. `StudentsScreen` liefert nur die ID der selektierten
sichtbaren Zeile; der vorhandene Adapter prüft den aktuellen Kindkontext.
Andere Fenster und Dialoge erhalten keine globale Beobachtungsaktion.

Der Dialog besitzt den einmaligen Startfokus. Bei neuen Beobachtungen erhält
die Katalogsuche Fokus, bei Bearbeitung beziehungsweise Schnellbeobachtung die
Notiz. Spätere Fokuswechsel bleiben bei Qt und der Lehrkraft; der Dialog
erzwingt seinen Startfokus bei erneuter Aktivierung nicht nochmals.
Adapter-, Daten- und Speicherownership bleiben unverändert.

Liest:

- neue Beobachtung: V3-`students` und aktuelle `ENROLLED`-Mitgliedschaft aus
  `CurrentMembershipReadSnapshot`
- bestehende Beobachtung: V3-`students` über die gespeicherte `student_id` und
  datierte Zuordnung über
  `AssignmentReferenceRequest(observation_id, student_id, observations.date)`
- `data_subjects`
- `data_competencies`
- `documentation_subject_settings` fuer die Fachauswahl neuer Beobachtungen
- `student_documentation_subject_profiles` und
  `student_documentation_subject_selections` über den bestehenden
  `StudentDocumentationSubjectService`
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
- Schülerbezogene primäre und weitere Fachoptionen aus `StudentDesktopAdapter.list_observation_subject_options(student_id, initial_draft)`; `is_primary` ist ausschließlich Darstellungsmetadatum
- Hierarchische Kompetenzprojektion aus `StudentDesktopAdapter.list_observation_competency_subject_groups(student_id, initial_draft)` fuer die Dialogdarstellung
- `catalog_status` und `is_active` aus derselben Adapterprojektion fuer Angebot und dezente historische Kennzeichnung
- Ungefilterte aktuelle Kompetenzansicht je bewusst gewähltem Fach; das
  weiterhin projizierte `learning_stage` erzeugt im Beobachtungsdialog keine
  zusätzliche Stage-Steuerung
- Lokaler Suchtext und Trefferanzeige über Kurzlabel, Kompetenztext, Thema und Kompetenzbereich aus derselben Adapterprojektion; nur aktive `current`-Kompetenzen sind neue Suchtreffer
- Fachbezogene Schnellauswahl aus `StudentDesktopAdapter.list_recent_observation_competencies(student_id, initial_draft)`: maximal vier eindeutige aktive `current`-Kompetenzen aus den neuesten aktiven Beobachtungen des Schuelers; bei Suchtext vollstaendig ausgeblendet und nach erfolgreichem Speichern erneut aus SQLite projiziert
- Beobachtungsnotiz
- Schnellbeobachtungsmodus als fluechtige Eingabe; beim Bearbeiten aus aktiver Beobachtung mit nichtleerer Notiz und ohne Kompetenzbewertungen rekonstruiert
- Kontext
- Bewertung/Zuordnung
- Dokumente und Medien

Regel:

Der Beobachtungsdialog ist der freigegebene Schreibprozess fuer Erfassung und
Bearbeitung von Beobachtungen. Die produktive Drei-Zonen-Arbeitsflaeche
rendert ausschliesslich die Adapterprojektion; der Dialog baut keine eigene
Fallback-Hierarchie aus Katalogdaten. Eine neue Beobachtung bietet nur
aktuelle `ENROLLED`-Kinder aus dem einmalig gesetzten
`CurrentMembershipReadSnapshot` an. Bei Bearbeitung bleiben die gespeicherte
`student_id` und `observations.date` fachlicher Kontext; die historische
Zuordnung wird ausschließlich an diesem Datum aufgelöst und niemals durch
current, Last-known oder V2-Schülerfelder ersetzt. Die beiden überfachlichen
Domänen und die über `effective_documentation_subjects(student_id,
school_year_id)` aufgelösten Unterrichtsfächer bilden die primäre
Fachauswahl. Andere aktive Unterrichtsfächer bleiben bewusst unter `Weitere
Fächer` erreichbar; der Katalog bietet in allen Fällen nur aktive
`current`-Kompetenzen neu an. Der aktuelle Entwicklungsbuch-Katalog wird nach
dem Fach direkt als Kompetenzbereich -> Thema -> Kompetenz gerendert; die
einheitlichen `cross_stage`-Kompatibilitätswerte werden nicht als drei
bedeutungsgleiche UI-Filter projiziert. `Zuletzt verwendet` stammt aus derselben
schülerbezogenen Hierarchie und wird erst für das bewusst gewählte Fach
sichtbar. Bei Bearbeitung wird eine bestehende
`observation_id` geladen; ein inzwischen nicht dokumentationsrelevantes
Bestandsfach sowie bereits bewertete `legacy`- oder inaktive Kompetenzen
bleiben sichtbar und werden nicht automatisch ersetzt. Speichern ersetzt die
Kompetenzbewertungen atomar. Eine bewusst leere `custom`-Auswahl bleibt leer;
der Dialog erzeugt weder daraus noch aus vorhandenen Beobachtungen eine neue
individuelle Auswahl. Die Fachprojektion priorisiert die normale Dokumentation,
löscht aber keine fachlichen Bestände und bildet keine Berechtigungsgrenze.
Kompetenzen muessen im Beobachtungsdialog zwingend mitgedacht werden. Die
sichtbare Kompetenzstruktur lautet Fach ->
Kompetenzbereich -> Thema -> Kompetenz und nutzt bestehende Felder:
`subject_id` / `subject_name`, `learning_area`, `competency_group`,
`description` / `competency_text`.

Die zentrale ViewModel-Auflösung bestimmt aus dem kanonischen Fachschlüssel
genau `standard`, `social` oder `sport` und liefert die vier sichtbaren
Chiptexte. Dialog, Schüler-/Kompetenzprojektionen und sichtbare LEG-/Bericht-
Ratingtexte konsumieren dieselbe Auflösung. Widgets besitzen weder
Fachspezialfälle noch neue Ratingwerte; Auswahl und Farben bleiben an die
stabilen Tokens `--`, `-`, `+`, `++` gebunden.

Sprint 3C stellt diese Struktur als additive ViewModel-/Adapterprojektion bereit. Sprint 3D rendert die Kompetenzauswahl hierarchisch. Sprint 5C uebernimmt die freigegebene Drei-Zonen-UX produktiv: Neu-Erfassung startet vollstaendig geschlossen, Bearbeitung oeffnet ausschliesslich Zweige mit bereits bewerteten Kompetenzen, und Auswahl sowie Einzelbewertungen bleiben bei Fachwechsel oder Einklappen erhalten. Sprint 5D filtert diese bestehende Projektion ausschließlich lokal im Dialog; Suche und Treffer-Öffnung verändern weder Auswahl noch Bewertung oder Persistenz und das Löschen der Suche stellt den Aufklappzustand vor der Suche wieder her. Sprint 5E ergänzt darunter eine reine Adapterprojektion der zuletzt verwendeten Kompetenzen; die Dialogauswahl ändert deren Reihenfolge oder Inhalt nicht.

Dokumente und Medien sind nur Anhaenge zur Beobachtung und ersetzen keine Beobachtungsdaten. Sie gehoeren immer zum Schueler und tragen optional die `observation_id`.
Der PySide-Dialog schreibt nicht direkt in SQLite, sondern ueber Adapter, Command, Service und Repository. Jede ausgewaehlte Kompetenz speichert ihre eigene Bewertung in `observation_competency_ratings.rating`. `offen` ist kein gespeicherter Ratingwert; wenn eine Kompetenz nicht bewertet wird, wird keine Zuordnungszeile gespeichert. Nur eine bewusst aktivierte Schnellbeobachtung darf ganz ohne Kompetenzbewertungen gespeichert werden; sie braucht eine nichtleere Notiz und bleibt fuer Kompetenzstatus- und Fortschrittsprojektionen ohne Wirkung.

## Kompetenzansicht

Liest:

- `data_competencies`
- `data_subjects`
- `data_observation_competencies`
- `data_observations`
- V3-`students` für Namen und stabile `student_id`; gegebenenfalls datierte
  Assignmentprojektion zum fachlichen Beobachtungsdatum

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

- V3-`students`: Schuelerstammdaten fuer Auswertung
- `CurrentMembershipReadSnapshot`: aktuelle Zielmitgliedschaften und zentral
  berechnete Gruppen-, Kurs- und Kursverbundzähler
- `groups` und `courses`: sichtbare Stammdaten
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

Dashboards duerfen keine eigenen Schatteninformationen speichern. Aktuelle
Dashboardprojektionen verwenden einmalig gesetztes `as_of` und dieselbe
`SchoolYearAssignmentReadSession` wie ihre übrigen Daten. Historische
Belegkontexte verwenden ausschließlich ihr fachliches Referenzdatum. Python-
Nachzählung, Query je Kind, V2-Schülerfelder sowie current- oder
Last-known-Fallback sind unzulässig.

## Berichte

Liest:

- V3-`students`
- `groups` und `courses` über datierte Assignmentprojektionen aus
  `AssignmentReferenceRequest`
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

Der Berichtskontext löst Stammgruppe und Kurs ausschließlich am `period_end`
des fachlich maßgeblichen RPD auf. LEG verwendet ausschließlich
`conference_date`, Beobachtungsbelege ausschließlich `observations.date`.
Freie Dokumente ohne fachliches Referenzdatum bleiben neutral. Current,
`last_known_membership`, technische Zeitpunkte und V2-Schülerfelder sind
keine Fallbacks; finalisierte Revisionen und PDFs werden nicht live neu
aufgelöst.

Sprint 7F.1 ergaenzt einen persistenten, weiter bearbeitbaren Berichtsentwurf. Die Berichtswerkstatt liest und schreibt ihn ausschliesslich ueber ViewModel, Application Layer und `SQLiteReportDraftRepository`. Gespeichert werden Dokumentkontext, manuelle Gesamt- und Fachtexte sowie bewusste Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen. Kompetenzzustaende stammen weiterhin ausschliesslich aus der kanonischen Sprint-6-Projektion; Kompetenz- und Beobachtungsinhalte werden nicht in den Entwurf kopiert. Aktive `current`-Kompetenzen sind fuer neue Auswahl vorgesehen. Beim Wiedereroeffnen werden gespeicherte Kompetenz-IDs als `retained_competency_ids` an dieselbe Projektion uebergeben, sodass spaeter deaktivierte oder historische Referenzen gekennzeichnet ausgewaehlt bleiben, ohne erneut angeboten zu werden. Gespeicherte Beobachtungs-IDs werden zusätzlich als `retained_observation_ids` ausschließlich read-only aufgelöst. Eine vorhandene soft-gelöschte Beobachtung bleibt mit ihrem gespeicherten Fachbezug und ihren `observation_competency_ratings`-Snapshotfeldern fachlich lesbar; tatsächlich fehlende oder fremde Referenzen bleiben ohne erfundene Zuordnung neutral. Die bestehende Draftklassifikation `unavailable_observation_ids` und die strengere Finalisierungsvalidierung bleiben unverändert. Der Entwurf ist keine finale Berichtsdomain und besitzt weder Freigabe, Versionierung, Archivierung noch eingefrorene Ausgabe.

Sprint 7F.2 portiert die freigegebene UX aus `prototypes/learning_report_ux/` auf diese bestehende Ownership. Die PySide-Berichtswerkstatt besitzt ausschliesslich lokalen Widgetzustand fuer die laufende Bearbeitung und delegiert Speichern ueber `LearningReportDraftViewModel` an den Desktop-Adapter. Bei mindestens einem vorhandenen Entwurf lässt die Shell bewusst einen gespeicherten RPD nach Zeitraum und Status öffnen, einen neuen noch ungespeicherten Arbeitsstand beginnen oder abbrechen; nur der gewählte RPD liefert seine gespeicherten Kompetenzreferenzen als Lesekontext. Die separate Vorschau baut ihr `ReportOutputModel` aus dem aktuellen Entwurf und den vorhandenen Leseprojektionen; sie ist keine Datenquelle. Fachseiten duerfen nur Kompetenzen des jeweiligen Fachs und nur dazu passende Beobachtungsbelege neu anbieten. Nicht verfuegbare gespeicherte Belege werden in Qt-Vorschau und Ausgabemodell getrennt von regulaeren Belegen neutral ausgewiesen. Diagramme werden nur als gespeicherte Auswahlreferenzen gehalten; ihre Daten werden bei Vorschau und PDF aus den vorhandenen Projektionen erzeugt.

Der Qt-Pilot-Grundworkflow komponiert denselben Widgetzustand sichtbar als
`Auswählen`, `Schreiben` und `Prüfen & finalisieren`. Der Dialog besitzt nur
die Zuordnung dieser sichtbaren Rollen zu den vorhandenen internen Seiten und
den flüchtigen Fokus-/Scrollzustand. `Frühere Fassungen` ist eine sekundäre
Navigation zur bestehenden snapshotbasierten Revisionslesesicht. Der Dialog
besitzt weder Prüfreife-, Snapshot-, Hash-, Persistenz- noch
Finalisierungslogik. Beim Dirty-Close fordert er über das vorhandene
`save_requested`-Signal das vollständige Draftspeichern an und beendet sich
erst, wenn `apply_saved_draft` den Erfolg bestätigt und den lokalen Dirty-State
zurückgesetzt hat.

Für neue Qt-Entwürfe klassifiziert ausschließlich der Desktop-Adapter die
aktiven Unterrichtsfächer anhand der bestehenden individuellen
Fachprojektion in primäre und weitere Angebote. Beobachtungen sind keine
Quelle dieser Klassifikation. `LearningReportDialog` gruppiert und navigiert
nur diese Projektion, hält die bewusste Auswahl lokal und startet ohne
gespeicherte Fächer in `Kompetenzen & Belege`. Die gespeicherten
`report_draft_subjects` bleiben Source of Truth; explizite Bestandsfächer
werden beim Öffnen auch dann als eigener Bestandsabschnitt projiziert, wenn
keine aktuelle Kompetenzzeile mehr existiert. Vorschau und OutputBuilder
filtern ausschließlich nach der laufenden Draftauswahl. RPV-Snapshots werden
nicht neu projiziert oder verändert.

Die Priorisierung in `Kompetenzen & Belege` bleibt eine reine
ViewModel-/Widgetprojektion: `LearningReportSubjectViewModel` ermittelt aus
seinen bereits gelieferten aktiven Beobachtungsbelegen die deduplizierten
Kompetenz-IDs im inklusiven RPD-Zeitraum; das Dialog-Widget komponiert daraus
die sichtbaren Gruppen. `documentation_state`, Bestätigungen, Ratingwerte und
Schnellbeobachtungen ohne Kompetenzzuordnung sind keine Prioritätsquelle.
Zeitraumwechsel schreiben und selektieren nichts. Adapter, Draftpersistenz,
OutputModel und unveränderliche RPV-Snapshots bleiben unverändert.

Der Qt-Schreibbereich komponiert pro ausgewähltem Fach ausschließlich
`LearningReportWritingEvidenceViewModel` aus Preparation und laufender lokaler
Draftauswahl. Die Projektion ordnet eine ausgewählte Beobachtung nach dem
bestehenden Berichtvertrag höchstens einmal einem Fach zu und zählt je
ausgewählter Kompetenz nur ihre gespeicherten Bezüge. Nicht aufgelöste IDs
bleiben außerhalb aller Fachzähler. Widget, Navigation und Anzeige besitzen
keine Repository-, Katalogrekonstruktions-, Speicher- oder
Finalisierungslogik.

Die intern gegatete `LearningReportHtmlDialog` ist ein alternativer Host
desselben Editors und wird nie parallel für denselben Draft geöffnet. Sie
besitzt dieselben Lese- und Schreibquellen wie `LearningReportDialog`:
`LearningReportPreparationViewModel`, den bewusst gewählten vollständigen
`LearningReportDraftViewModel`, den bestehenden Report-Save-Service,
`LearningReportRevisionStatusViewModel`, ausschließlich snapshotbasierte
`LearningReportRevisionViewModel`-Lesen und opaque RPA-Referenzen. Der DOM ist
keine Datenquelle. Der HTML-Host verlangt eine zuvor bewusst gewählte konkrete
`report_draft_id`; er erzeugt weder Timeline noch Fachkarten der
schuljahresbezogenen Entwicklungsübersicht. Qt bleibt Standard und
unveränderter Fallback.

Aktueller produktiver Stand: Die PDF-Ausgabe liest ausschliesslich ein neutrales `ReportOutputModel`, das fuer die Vorschau aus dem Berichtsentwurf und den freigegebenen Leseprojektionen aufgebaut wird. Sie greift weder direkt auf SQLite zu noch berechnet oder interpretiert sie fachliche Inhalte. Dieses Modell ist im Draft-Prozess noch kein eingefrorener oder freigegebener Berichtstand.

Sprint 5B.2 ergaenzt ohne neue Ansicht einen reinen Backend-Schreib- und Lesepfad fuer finale Berichtrevisionen. `ReportFinalizationService` darf den vorhandenen `RPD`, dessen normalisierte Auswahlrelationen sowie die registrierten Schueler-, Kompetenz-, Beobachtungs- und bestaetigten Statusquellen lesen. `SQLiteLearningReportRepository` ist alleiniger Schreiber von `learning_reports` und `learning_report_revisions`. Der persistierte fachliche Snapshot ist historische Source of Truth; weder Berichtswerkstatt noch aktuelle Draft-Vorschau noch `ReportOutputModel` besitzen oder veraendern bestehende Revisionen. Es gibt in diesem Sprint keine UI-Aktion, keine neue UI-Projektion und keine PDF-Artefaktansicht.

Aktueller Revisionsstand: Ein finalisierter Bericht ist mit `RPT` und `RPV` als eigene fachliche Entitaet umgesetzt. Der fachliche Snapshot friert Schuelerbezug, Berichtszeitraum, verantwortlichen Anzeigenamen, manuelle Texte, ausgewaehlte Kompetenzinformationen, ausgewaehlte Beobachtungsbelege und Diagrammdaten ein. Eine finale Ausgabeversion beziehungsweise PDF-Artefaktverwaltung fehlt weiterhin; der bestehende reine Renderer erhaelt in diesem Sprint noch kein neues Eingangsmodell.

Sprint 5B.3 bindet den vorhandenen Revisionspfad produktiv an die Berichtswerkstatt an. Die Werkstatt liest Status, aktuelle Revision und neueste-zuerst sortierte Historie ausschliesslich ueber `StudentDesktopAdapter`, `ReportRevisionApplicationService`, `LearningReportRevisionReadService` und `SQLiteLearningReportRepository`. Der zentrale Leseservice erzeugt fuer die Aenderungserkennung einen vollstaendig validierten deterministischen Finalisierungskandidaten und vergleicht dessen SHA-256 mit der aktuellen Revision; Widgets besitzen keine Snapshot-, Hash- oder Repositorylogik. Finalisierung speichert ungespeicherte Draftaenderungen zuerst und verwendet danach den bestehenden transaktionalen Schreibpfad.

Die `LearningReportRevisionDialog` besitzt ausschliesslich die bereits snapshotbasierte `LearningReportRevisionViewModel`-Projektion. Deren einzige fachliche Inhaltsquelle sind `snapshot_json`, Revisionsmetadaten und gespeicherter Hash. Sie darf keine aktuellen Schueler-, Gruppen-, Kurs-, Kompetenz-, Beobachtungs- oder Diagrammdaten nachladen und bietet keine Schreib-, Loesch-, Entsperr- oder Wiederherstellungsaktion. Die Projektion adaptiert den Snapshot getrennt vom Live-Draft an den renderer-neutralen `ReportOutputModel`-Vertrag.

Sprint 9A erlaubt in dieser Ansicht fuer die aktuelle `finalized`-Revision ausschliesslich die Aktion `Finales PDF erstellen`. Das Widget uebergibt nur die `RPV`-ID. `StudentDesktopAdapter`, `LearningReportPdfApplicationService`, `LearningReportPdfService` und `SQLiteLearningReportPdfArtifactRepository` pruefen Status und Snapshot, erzeugen das PDF aus dem snapshotbasierten `ReportOutputModel` und speichern die unveraenderliche `RPA`-Referenz. Die UI kennt weder Pfadpolicy, Hashberechnung, Renderer noch SQLite. Supersedierte Revisionen koennen vorhandene historische Inhalte weiterhin anzeigen, aber kein neues finales Artefakt erzeugen.

Ein vorhandenes RPA wird für `Finales PDF anzeigen` ausschließlich als opaque
Artifact-ID an `StudentDesktopAdapter.read_final_pdf_artifact` übergeben. Der
Adapter verifiziert die fachliche Referenz und den vorhandenen
Managed-Document-Lesepfad vollständig. `PdfArtifactBufferConsumer` und
`PdfArtifactViewerDialog` besitzen nur die flüchtigen PDF-Bytes beziehungsweise
deren QtPdf-Darstellung; Shell, Qt-Dialog und HTML-DOM besitzen weder Pfad-,
Container-, Hash- noch Entschlüsselungsownership. Schließen verwirft den
Anzeigezustand deterministisch.

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

Bei mindestens einem vorhandenen LEG lässt die Shell bewusst einen gespeicherten LCD nach Gesprächsdatum, Zeitraum und Status öffnen, ein neues noch ungespeichertes eigenständiges Gespräch beginnen oder abbrechen. Nur der gewählte LCD bildet den Lesekontext; die Auswahl selbst schreibt nichts. Ein neuer LCD ist keine Revision eines vorhandenen LCF/LCV; Revisionen bleiben ausschliesslich der expliziten Abschlussownership vorbehalten.

Sprint 7G.3 schraenkt nur die sichtbare Kompetenzwahl ein. Die bestehende kanonische Projektion liefert aktive kindbezogene Kompetenznachweise und aktuelle Bestaetigungen; das LEG-ViewModel reicht deren Datums- und Vorhandenseinsreferenzen weiter. Der Dialog zeigt bei vollstaendigem Zeitraum Beobachtungsreferenzen innerhalb dieses Zeitraums, ohne vollstaendigen Zeitraum alle kanonisch beruecksichtigten Kompetenzbeobachtungen. Aktuelle Bestaetigungen bleiben zeitraumunabhaengig sichtbar. Bereits im Draft ausgewaehlte IDs werden nie automatisch entfernt und duerfen als expliziter Lesekontext auch historische Katalogzeilen in derselben Projektion aufloesbar halten. Schnellbeobachtungen, fremde oder soft-geloeschte Beobachtungen gelangen nicht in diese kanonischen Kompetenznachweise. Der lokale Filter ist keine Datenquelle und keine zweite Statuslogik.

UI Sprint 6B komponiert dieselbe Ownership als Workspace mit sechs Inhaltsankern neu. Der Qt-Pilotabschluss gruppiert sie rein sichtbar als `Vorbereitung` (`goal`, `evidence`), `Im Gespräch` (`strengths`, `development`) und `Vereinbarungen & Abschluss` (`goals`, `agreements`); die Gruppen sind keine eigene Seite oder Datenquelle. `LearningConferenceDialog` besitzt nur fluechtigen aktiven Anker-, Fokus-, Scroll- und Dirty-State. `goal` bearbeitet den bestehenden Gespraechsrahmen und die Schwerpunktreferenzen; `strengths`, `development` und `goals` ordnen vorhandene manuelle Texte nach Vorbereitung, gemeinsamem Gespraech und Draft-Vereinbarung; `evidence` bearbeitet die bestehenden Kompetenz-, Beobachtungs- und Diagrammreferenzen; `agreements` bearbeitet Unterstuetzung und Vereinbarungen. Ausserhalb von `evidence` ist die Belegzusammenfassung rein lesend. Kursname, Stammgruppe und Kindname bleiben Live-Projektionen der vorhandenen Schuelerquelle. Direkte Ankerwahl, Suche, Disclosure und Dirty-Ermittlung schreiben nichts; ausschliesslich `Entwurf speichern` delegiert weiterhin den vollstaendigen Draft ueber `StudentDesktopAdapter` an den bestehenden Schreibpfad.

Sprint 10A ergaenzt neben diesem Draftpfad eine eigene Abschlussownership. `LearningConferenceDialog` sendet fuer den expliziten Abschluss nur die gespeicherte LCD-ID. `StudentDesktopAdapter` delegiert an `LearningConferenceCompletionApplicationService`, LEG-Domainvalidierung und `SQLiteLearningConferenceRepository`. Snapshotbildung, kanonische Serialisierung, SHA-256 und atomare LCF-/LCV-Persistenz liegen vollstaendig ausserhalb von UI und ViewModel.

Die Revisionshistorie ist eine Lesesicht auf `learning_conference_revisions`. `LearningConferenceRevisionDialog` besitzt ausschliesslich `LearningConferenceRevisionViewModel`, das zuvor durch `LearningConferenceRevisionReadService` aus einem hashverifizierten Snapshot gebildet wurde. Die Ansicht darf weder aktuelle Stammdaten noch Kompetenz-/Beobachtungsprojektionen nachladen. Der LCD bleibt unabhaengig von vorhandenen LCVs bearbeitbar; seine Live-Projektionen und die historische Snapshotansicht sind bewusst getrennte Sources of Truth.

Sprint 10B erlaubt in dieser Ansicht fuer die aktuelle `completed`-Revision ausschliesslich die Artefaktaktion `Finales PDF erstellen`. Das Widget uebergibt nur die LCV-ID. Adapter, Application Service, LEG-PDF-Domain und Artefakt-Repository validieren Revision und Snapshot, bauen die Ausgabe ausschliesslich aus dem LCV-Snapshot und speichern die unveraenderliche `LCA`. Die UI kennt weder Renderer, Pfadpolicy, Hashberechnung noch SQLite. `superseded`-Revisionen bleiben lesbar, bieten aber keine neue PDF-Erzeugung.

Ein vorhandenes LCA nutzt für die Anzeige denselben
`StudentDesktopAdapter.read_final_pdf_artifact`-, Memory-Consumer- und
`PdfArtifactViewerDialog`-Vertrag wie ein RPA. Nur die fachliche Auflösung der
opaque LCA-ID bleibt im bestehenden LEG-Repository; es gibt keinen eigenen
LEG-Viewer und keinen zweiten Entschlüsselungspfad.

## UI-only Kompetenz-Darstellungsgruppen

Das Observation-ViewModel besitzt die alleinige Zuordnung vorhandener
kanonischer Domänenschlüssel zu `Überfachliche Entwicklung` oder `Fächer`.
Dialog und Schülerprofil komponieren daraus ruhige Überschriften und reichen
bei Auswahl weiterhin unverändert `subject_key`, `competency_id` und
Ratingtoken weiter. Widgets dürfen die Gruppe weder speichern noch als Fach,
Filterquelle oder Status interpretieren. Die individuelle Fachauswahlprojektion
entfernt die beiden Schlüssel ausschließlich aus ihren sichtbaren Optionen.
Die Entwicklungsübersicht ergänzt dieselben Schlüssel fest vor der weiterhin
über `effective_documentation_subjects` bestimmten Unterrichtsfachmenge und
verwendet für beide Abschnitte unverändert die bestehende neutrale
Dokumentationskartenprojektion.

## Einklappbare Berichtsvorschau (07.09.2026)

Der Berichtdialog besitzt ausschließlich den flüchtigen Klappzustand. Alle bewusst gewählten Fachseiten werden weiterhin vollständig erzeugt und nummeriert. Entwurf, PDF und finale Revision behalten ihre bestehende Projektion unabhängig von der Sichtbarkeit.

## Dezenter Sicherungshinweis (07.09.2026)

Das Backup-ViewModel besitzt Altersregel und Hinweistext. Settings rendert den Hinweis und den knappen Zustand in der bestehenden Datensicherungskarte. Die Shell liefert Ergebnisse und unterscheidet fehlgeschlagene von erfolgreicher leerer Discovery. Geprüfte Auswahl und Sicherungsdateien werden durch den Hinweis nicht verändert.

Die gebundene lokale macOS-Testkopie besitzt ausschließlich den technischen
Prozesseinstieg. Die fachlichen Views bleiben unverändert; die native
Schlüsselbunddiagnose liefert einen internen Statusreport ohne Produkt-View.

Die eigenständige native Roundtrip-Diagnose zeigt ihren eigenen Teststatus.
Sie besitzt weder Produktfenster noch Zugriff auf App-Datenordner.


## Kompetenzübersicht als PDF – PO-Freigabe 11.10.2026

Der vorhandene Shell-Toast besitzt die Export-Rückmeldung; der native Plattformdialog besitzt ausschließlich Zielauswahl. Kein neuer View-State.

Owner der neuen Ausgabe ist die Kompetenz-PDF-Projektion. Der Adapter liest ausschließlich das bestehende Schülerprofil-Bundle. Export enthält alle aktuellen Kompetenzen je effektivem Fach sowie die beiden überfachlichen Bereiche; ein Fachfilter verkürzt die Ausgabe niemals. Such-/Dokumentationsfilter und eingeklappte Themen verkürzen den Export nicht. Renderer kennt weder Repository noch SQLite, Widgets enthalten ausschließlich Interaktions-/Dialoglogik.
