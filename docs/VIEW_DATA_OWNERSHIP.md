# View Data Ownership

## Phase 2 Berichte-Übersicht - implementiert

`StudentDesktopAdapter.report_overview_for_student` bleibt die einzige
Desktop-Kompositionsgrenze. Er bestimmt den eindeutig gewählten RPD, hält
Bericht und LEG beim Lesen getrennt und übergibt ausschließlich vorhandene
RPD-, Bericht-, LEG-, Beobachtungs- und kanonische Kompetenzstatuswerte an die
reine Phase-2-ViewModel-Projektion. Repositories und Application Services
behalten ihre bestehenden fachlichen Zuständigkeiten.

Der Adapter friert den ausgewählten RPD-Zeitraum einmal ein, verifiziert die
neueste gültige Bericht- beziehungsweise LEG-Revision je Aggregat, reicht
stabile IDs unverändert weiter und klassifiziert Quellenfehler neutral.
Live-Dokumentation wird möglichst in einem SQLite-Read-Snapshot gelesen. Ein
Fehler einer Quelle darf weiterhin gültige getrennte Dokumentereignisse nicht
entfernen.

Die ViewModel-Projektion besitzt RPD-Zeitraumfilter, Datumsnormalisierung,
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

## Security Sprint 12 - bestehender Über-Dialog und technische Testreports

Der vorhandene `AppInfoDialog` projiziert zusätzlich ausschließlich
`APP_VERSION` und `APP_BUILD_VERSION` aus `src.version`. Er besitzt keine
Build-, Appcast-, Gate-, Keychain-, SQLCipher- oder Releaseentscheidung.

Gate-Off-, Gate-On-, Bundle- und Keychain-Smokes liefern nur sanitierte
technische JSON-Testreports an den aufrufenden internen Prüfprozess. Sie sind
keine Produkt-View, kein ViewModel und keine sichtbare Recoveryführung.
Widgets besitzen weiterhin keine Security-, Repository- oder Dateisystemlogik.

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
`SupportResetBackupFactory` baut aus RuntimePaths ausschließlich den vorhandenen
`VerifiedSecurityBackupAdapter`. Der Desktop-Controller besitzt Worker,
Dateidialoge, Zwischenablageaktion, Sperr-/Sitzungshandoff und App-Ende.

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
Dokumentationsstatusprojektion ueber einen refresh-lokalen
`StudentDocumentationProjectionBatch`. Der
`SQLiteStudentDocumentationProjectionRepository` besitzt nur den
transaktionskonsistenten Read-Snapshot; `StudentDesktopAdapter` bleibt Owner
der Gruppierung, kanonischen Dokumentationsabdeckung und Sortierprojektion.
Die vollstaendige Bestätigungsfrische bleibt im Batch fachlich gleich
projizierbar, beeinflusst aber nicht die Regel, ob eine konkrete Kompetenz
dokumentiert ist. Screens und Widgets lesen weder Repositories noch SQLite
direkt. Der Batch fuehrt keine DDL aus und wird nicht ueber den jeweiligen
Refresh hinaus gehalten.

`OnboardingScreen` besitzt nur sichtbaren Schritt-, Text-, Button- und lokalen
Fokuszustand. Persistenz gehoert `OnboardingController` und
`AppPreferencesFile`; Navigation gehoert `AppShell`. Kleine Statuszeilen werden
aus bestehenden Adapter-/ViewModel-Projektionen als aggregierte Ja/Nein-Werte
uebergeben. Die View liest keine SQLite-Daten direkt, zeigt keine Schuelernamen
und schreibt keine fachlichen Daten.

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
- passende Kinder mit textlich sichtbarer Kurszugehoerigkeit und bestehender Kursfarbe als reinem Kontextbadge
- neutrale Mini-Heatmap der Dokumentationsabdeckung je Stammgruppe und Fach; keine Bewertung, Leistung, Rangfolge oder Entwicklungsableitung

Regel:

`Heute` ist eine reine Lese- und Navigationsoberflaeche. Der technische Screen und Schluessel `dashboard` bleiben erhalten. Die Ansicht zeigt den aktuellen Stammdaten-Scope der PySide-App, verwaltet weder Stammdaten noch Stundenplan und schreibt nicht direkt in SQLite. Aktuell, naechste und heutige Stunde stammen ausschliesslich aus `TimetableDesktopAdapter.read_projection(at)`. Zeitstatus wird beim Oeffnen beziehungsweise Aktivieren und hoechstens minuetlich neu gelesen. Die Heatmap zaehlt je Stammgruppe und Fach nur Kinder, deren bestehende kanonische Fachprojektion mindestens eine dokumentierte Kompetenz ausweist; sie zeigt keine Ratings, Scores oder automatischen Entwicklungsurteile. Ihre neutralen Blau-Grau-Abstufungen codieren ausschliesslich Dokumentationsabdeckung und keine Ampelbewertung.

Die direkte Kursansicht im Schueler-Arbeitsraum filtert appweit nach der ausgewaehlten `course_id`. Die getrennte Kursverbundansicht bleibt kursverbundbezogen und schraenkt ihren Kursfilter weiterhin zusaetzlich auf die Stammgruppen des ausgewaehlten Kursverbunds ein.

UX-Regel UI Sprint 1: `Heute` und `Schüler` sind die beiden globalen Arbeitsziele. Die Dashboard-Projektionen erscheinen ausschliesslich in einer grossen Hero-Karte, einer horizontalen Tages-Timeline, einer kompakten Stammgruppe-mal-Fach-Matrix und der Karte fuer passenden Unterrichtskontext. Allgemeine Stammgruppen- und Kursverbundkarten gehoeren lokal in den Schueler-Arbeitsraum.

Regel Sprint 8B.3: `Passende Kinder für diese Stunde` liest aktive Kinder aus der zur Stunde gehoerenden Stammgruppe, dem Kurs oder Kursverbund sowie deren aktive Beobachtungen. Es werden hoechstens fuenf Kinder als transparente Dokumentationshilfe projiziert. Reihenfolge und Hinweis beruhen ausschliesslich auf dem Vorhandensein und Datum einer aktiven Beobachtung mit eindeutigem Fachbezug; Ratings, Kompetenzstatus, Leistungswerte und paedagogische Urteile werden nicht gelesen oder berechnet. Der Screen rendert diese Projektion nur und startet `Beobachten` ueber den bestehenden Beobachtungsdialog.

## PySide6 Schueler-Arbeitsraum

Liest die bestehenden Projektionen aus `groups`, `courses`, `students`, `course_groups`, `course_group_student_groups` und `course_group_courses`. Schreibt nichts direkt. `StudentsWorkspace` komponiert die lokalen Segmente `Stammgruppen`, `Kurse`, `Kursverbünde` und `Alle Schüler`, ohne eine neue Datenquelle zu besitzen. Stammgruppenkarten, direkte Kurskarten, Schuelerzahlen, Kursverbuende, Kurszugriffe, Listenfilter und Profilnavigation verwenden ausschliesslich die bestehenden technischen IDs. Ein einfacher Klick auf eine Nicht-Aktionszelle, Enter oder die sekundäre Profilaktion navigiert per `student_id`; eingebettete Zeilenaktionen bleiben davon getrennt. Dashboard-Daten und Stundenplanprojektionen werden in diesem Arbeitsraum nicht gelesen.

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

Sprint 7F.2 portiert die freigegebene UX aus `prototypes/learning_report_ux/` auf diese bestehende Ownership. Die PySide-Berichtswerkstatt besitzt ausschliesslich lokalen Widgetzustand fuer die laufende Bearbeitung und delegiert Speichern ueber `LearningReportDraftViewModel` an den Desktop-Adapter. Bei mindestens einem vorhandenen Entwurf lässt die Shell bewusst einen gespeicherten RPD nach Zeitraum und Status öffnen, einen neuen noch ungespeicherten Arbeitsstand beginnen oder abbrechen; nur der gewählte RPD liefert seine gespeicherten Kompetenzreferenzen als Lesekontext. Die separate Vorschau baut ihr `ReportOutputModel` aus dem aktuellen Entwurf und den vorhandenen Leseprojektionen; sie ist keine Datenquelle. Fachseiten duerfen nur Kompetenzen des jeweiligen Fachs und nur dazu passende Beobachtungsbelege neu anbieten. Nicht verfuegbare gespeicherte Belege werden in Qt-Vorschau und Ausgabemodell getrennt von regulaeren Belegen neutral ausgewiesen. Diagramme werden nur als gespeicherte Auswahlreferenzen gehalten; ihre Daten werden bei Vorschau und PDF aus den vorhandenen Projektionen erzeugt.

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

Bei mindestens einem vorhandenen LEG lässt die Shell bewusst einen gespeicherten LCD nach Gesprächsdatum, Zeitraum und Status öffnen, ein neues noch ungespeichertes eigenständiges Gespräch beginnen oder abbrechen. Nur der gewählte LCD bildet den Lesekontext; die Auswahl selbst schreibt nichts. Ein neuer LCD ist keine Revision eines vorhandenen LCF/LCV; Revisionen bleiben ausschliesslich der expliziten Abschlussownership vorbehalten.

Sprint 7G.3 schraenkt nur die sichtbare Kompetenzwahl ein. Die bestehende kanonische Projektion liefert aktive kindbezogene Kompetenznachweise und aktuelle Bestaetigungen; das LEG-ViewModel reicht deren Datums- und Vorhandenseinsreferenzen weiter. Der Dialog zeigt bei vollstaendigem Zeitraum Beobachtungsreferenzen innerhalb dieses Zeitraums, ohne vollstaendigen Zeitraum alle kanonisch beruecksichtigten Kompetenzbeobachtungen. Aktuelle Bestaetigungen bleiben zeitraumunabhaengig sichtbar. Bereits im Draft ausgewaehlte IDs werden nie automatisch entfernt und duerfen als expliziter Lesekontext auch historische Katalogzeilen in derselben Projektion aufloesbar halten. Schnellbeobachtungen, fremde oder soft-geloeschte Beobachtungen gelangen nicht in diese kanonischen Kompetenznachweise. Der lokale Filter ist keine Datenquelle und keine zweite Statuslogik.

UI Sprint 6B komponiert dieselbe Ownership als Sechs-Phasen-Workspace neu. `LearningConferenceDialog` besitzt nur fluechtigen aktiven Phasen-, Fokus-, Scroll- und Dirty-State. Phase 1 bearbeitet den bestehenden Gespraechsrahmen und die Schwerpunktreferenzen; Phase 2 bis 4 ordnen vorhandene manuelle Texte nach Vorbereitung, gemeinsamem Gespraech und Draft-Vereinbarung; Phase 5 bearbeitet die bestehenden Kompetenz-, Beobachtungs- und Diagrammreferenzen; Phase 6 bearbeitet Unterstuetzung und Vereinbarungen. Ausserhalb von Phase 5 ist die Belegzusammenfassung rein lesend. Kursname, Stammgruppe und Kindname bleiben Live-Projektionen der vorhandenen Schuelerquelle. Phasenwechsel, Suche, Disclosure und Dirty-Ermittlung schreiben nichts; ausschliesslich `Entwurf speichern` delegiert weiterhin den vollstaendigen Draft ueber `StudentDesktopAdapter` an den bestehenden Schreibpfad.

Sprint 10A ergaenzt neben diesem Draftpfad eine eigene Abschlussownership. `LearningConferenceDialog` sendet fuer den expliziten Abschluss nur die gespeicherte LCD-ID. `StudentDesktopAdapter` delegiert an `LearningConferenceCompletionApplicationService`, LEG-Domainvalidierung und `SQLiteLearningConferenceRepository`. Snapshotbildung, kanonische Serialisierung, SHA-256 und atomare LCF-/LCV-Persistenz liegen vollstaendig ausserhalb von UI und ViewModel.

Die Revisionshistorie ist eine Lesesicht auf `learning_conference_revisions`. `LearningConferenceRevisionDialog` besitzt ausschliesslich `LearningConferenceRevisionViewModel`, das zuvor durch `LearningConferenceRevisionReadService` aus einem hashverifizierten Snapshot gebildet wurde. Die Ansicht darf weder aktuelle Stammdaten noch Kompetenz-/Beobachtungsprojektionen nachladen. Der LCD bleibt unabhaengig von vorhandenen LCVs bearbeitbar; seine Live-Projektionen und die historische Snapshotansicht sind bewusst getrennte Sources of Truth.

Sprint 10B erlaubt in dieser Ansicht fuer die aktuelle `completed`-Revision ausschliesslich die Artefaktaktion `Finales PDF erstellen`. Das Widget uebergibt nur die LCV-ID. Adapter, Application Service, LEG-PDF-Domain und Artefakt-Repository validieren Revision und Snapshot, bauen die Ausgabe ausschliesslich aus dem LCV-Snapshot und speichern die unveraenderliche `LCA`. Die UI kennt weder Renderer, Pfadpolicy, Hashberechnung noch SQLite. `superseded`-Revisionen bleiben lesbar, bieten aber keine neue PDF-Erzeugung.
