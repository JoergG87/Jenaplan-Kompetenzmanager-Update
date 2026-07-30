# Projektdokumentation: Jenaplan-Kompetenzmanager

## V3-only Produktschema und Architecture Cleanup

**Status:** Governance, technischer V3-only-Cleanup, zentrale Assignment-API,
SJ-2E-Leserumstellung, SJ-2F-Writerumstellung und die Final-V3-Runtime-
Aktivierung sind lokal implementiert. Die manuelle macOS-Abnahme bleibt offen.

V3 ist das erste und einzige Produktschema. Es enthält `school_years`,
datierte `student_school_year_assignments`, `courses.year_level`,
`students` ohne `group_id` und `course_id` sowie
`school_year_transitions` ausschließlich für echte spätere
Schuljahreswechsel. Aktuelle und historische Mitgliedschaften werden nur am
expliziten fachlichen Referenzdatum aus Assignments aufgelöst.

Es existieren keine produktiven V2-Daten. Vorhandene V2-Bestände sind
synthetische Entwicklungsdaten, werden nicht migriert und dürfen für Tests
durch frisch erzeugte deterministische V3-Bestände ersetzt werden. Echte
Nutzerdaten werden erst nach vollständiger V3-Implementierung, Prüfung und
Freigabe verwendet. Es gibt keinen V2-Cutover, keinen V2-Bootstrap-Assistenten,
keinen V2-Produktrestore und keine dauerhafte V2-Kompatibilitätszusage.

Der technische Cleanup hat das bisher in der isolierten Migrationsengine
enthaltene finale DDL in `FinalV3SchemaInitializer` überführt und Engine,
Klassifizierung, Cutover-Plan, Backup-Evidence, Failpoints und
V2-Startupzustände entfernt. Compatibility, Backup und Restore akzeptieren
ausschließlich das exakte finale Schema. Das unabhängige Backupformat-v1
bleibt bestehen.

Startup-Ziel ist: exaktes finales Schema erkennen, eine fehlende Datenbank nur
im autorisierten First-Run-/Testkontext direkt als V3 erzeugen und unbekannte
oder beschädigte Schemata fail-closed ablehnen. Exakt verifiziertes Final-V3
wird als `V3_SCHEMA_READY` für die normale Runtime zugelassen. Nach diesem
Gate öffnet die Composition Root die vorhandene Datenbank ausschließlich ohne
Create-Fallback; verschwindet sie, stoppt der Start fail-closed.

Ein autorisierter First Run erzeugt ausschließlich das vollständige
Final-V3-Schema und prüft es erneut. Er erzeugt kein Schuljahr. Fehlt ein
eindeutiges `current`-Schuljahr, startet die technische Runtime, während die
schülerbezogenen Bereiche fachlich gesperrt bleiben.

Implementiert sind die Qt-freien, Connection-gebundenen
`SchoolYearRepository`- und
`StudentSchoolYearAssignmentRepository`-Grenzen, der konsistente
`SchoolYearAssignmentQueryService`, das Membership-freie `V3Student`-Modell
und die isolierten Einzelkind-Lifecycles für Anlage, Stammdatenänderung,
Einschreibung, unterjährigen Wechsel, Austritt und Archivierung. Alle
Referenzdaten sind explizit; Batchreads sind set-basiert; Mehrdeutigkeit und
fehlende Zuordnung bleiben sichtbare Zustände.

SJ-2E stellt die produktiven Membership-Leser für Schülerlisten und -profil,
Gruppen, Kurse, Kursverbünde, Dashboard, Beobachtungsbearbeitung,
Berichtsvorbereitung und -finalisierung sowie LEG-Vorbereitung und -Abschluss
auf diese API um. Aktuelle Ansichten bestimmen genau ein explizites `as_of`
pro Read-Snapshot; historische Auflösung verwendet `observations.date`,
`period_end` beziehungsweise `conference_date`. Connection-gebundene
`SchoolYearAssignmentReadSession`-Komposition, zentrale Counts und
set-basierte Batchabfragen verhindern V2-Fallbacks und N+1-Reads. Report- und
LEG-Snapshotbildung einschließlich Assignmentauflösung und persistierendem
Revisionsschritt liegt jeweils in derselben Transaktion. Bestehende
Revisionen, Hashes und PDF-Artefakte werden nicht neu aufgelöst.

SJ-2F stellt die produktiven Schüler-, Kurs- und Stammgruppen-Writer auf
Final-V3 um. Schüleranlage schreibt V3-Stammdaten und initiales
`enrolled`-Assignment atomar. Stammdatenänderung, datierter Einzelwechsel,
Austritt und Archivierung bleiben getrennte Lifecycles; Austritt archiviert
nicht, Archivierung verändert keine Assignments und wird bei aktueller
Einschreibung blockiert. Der bisherige generische V2-Schülercommand und die
testlokale Legacy-Membershipfixture sind entfernt.

Kurse verlangen eine bewusst gewählte stabile `year_level` von 1, 2 oder 3;
mehrere Kurse derselben Stufe bleiben zulässig. Kurs oder Stammgruppe dürfen
an einem expliziten Stichtag nicht deaktiviert werden, solange aktuelle oder
zukünftige `enrolled`-Assignments darauf verweisen. Historische Assignments
bleiben unverändert lesbar; Stammdatenwrites buchen kein Kind um.

Der synthetische Entwicklungs-/Testdatenpfad erzeugt ausschließlich frische
deterministische Final-V3-Daten mit current-Schuljahr `2025/26`,
Kursstufen, V3-Schülerstammdaten und vollständigen Assignments. Er migriert
oder überschreibt keine vorhandene Datenbank und verwendet keine echten
Nutzerdaten.

SJ-3A implementiert ausschließlich die Qt-freie, rein lesende
Schuljahreswechsel-Vorschau. Sie prüft Zieljahresdaten, liest jedes V3-Kind
und dessen Assignmentkandidaten am Ende des eindeutigen current-Schuljahres,
übernimmt eine gültige aktive Stammgruppe unverändert und schlägt anhand
`courses.year_level` nur bei genau einem aktiven Zielkurs 1→2 oder 2→3 vor.
Alle ausgeschlossenen oder uneindeutigen Fälle bleiben sichtbar und
`UNRESOLVED`. SJ-3A selbst enthält keine UI, Persistenz, Aktivierung,
Authentifizierung, Backup- oder Mehrkindwechselfunktion.

SJ-3B.1 ergänzt einen isolierten rein lesenden PySide-Dialog. Er zeigt Kopf,
Zähler und jedes vorhandene Preview-Item unverändert, erlaubt nur Schließen
und besitzt weder Repository-/Write-Aufruf noch Ausführungsmöglichkeit. Eine
breite Settings-/Shell-Integration ist nicht erfolgt.

Weiterhin nicht umgesetzt oder freigegeben sind die editierbare
Schuljahreswechsel-UI SJ-3B.2, die spätere Ausführung des Wechsels,
unterjährige Mehrkind-/Sammelwechsel, Build, Packaging und Release. Die
manuelle Prüfung der Runtime sowie der neuen Schüler-, Wechsel-, Austritts-
und Kursstufenoberflächen auf macOS ist noch offen. Es wurden keine Migration
und keine echten Daten verwendet.

## Schuljahresmodell und echte Wechsel

Die Domainmodelle `SchoolYear` und
`StudentMembershipAssignment`, ihre Datums- und Intervallinvarianten sowie
die Datenhoheit aus ADR-095 bleiben verbindlich. Ein echter späterer
Schuljahreswechsel führt von einem vorhandenen current-Schuljahr zu einem
vorhandenen geplanten Schuljahr. Sein `school_year_transitions`-Beleg besitzt
immer ein vorhandenes Ausgangs- und Zielschuljahr; eine Bootstrap-Transition
mit leerer Ausgangs-ID ist ausgeschlossen.

Vorschau, verifiziertes Sicherheitsbackup, Maintenance-Gate, erneute
Quellenprüfung, Passwort-Step-up, atomare Transaktion, Rollback, Idempotenz,
Historie und unveränderliche finale Bericht-/LEG-Artefakte bleiben für diesen
späteren Produktprozess erforderlich. Diese Sicherheitsfunktionen sind durch
SJ-3A oder den Architecture Cleanup nicht als implementiert zu verstehen.

## Berichte-Übersicht - implementierte Phase 2

### Historische Basis: Paket 1 und Paket 1.1

Paket 1 stellt die getrennten vorhandenen Bericht- und LEG-Zustände, den
eindeutig gewählten RPD-Zeitraum, konkrete nächste Schritte, eine gemeinsame
read-only Anzeigehistorie und die Navigation in den vorhandenen
Berichtarbeitsraum bereit. Die fachlichen Aggregate und Schreibprozesse
bleiben getrennt.

Paket 1.1 verdichtet die vorhandene Übersicht visuell. Es zeigt auf Basis der
Paket-1-Projektionen eine platzbegrenzte Meilensteinleiste und kompakte
Fachkarten. Dieser historische Zwischenstand verwendete die
Paket-1-Semantik mit `documented_count/current_count`, Screen-eigener
Inhaltsbegrenzung und `orientation_changes`; Phase 2 hat diese Semantik im
Berichtsbereich vollständig ersetzt.

### Implementiert: Pakete 2A.1, 2A.2, 2B und 2C

Phase 2 ist als rein lesende Berichtsvorbereitung implementiert. Dauerhafte
Source of Truth sind die zuständigen Governance-Dokumente: Architektur in
`DECISIONS.md`, technische Begriffe in `docs/TECHNICAL_NAMES.md`,
Datenquellen in `docs/DATA_REGISTRY.md`, Projektionsablauf in
`docs/DATA_LIFECYCLE.md`, View-Verantwortung in
`docs/VIEW_DATA_OWNERSHIP.md`, sichtbare Felder in
`docs/UI_DATA_MAPPING.md` und UX in `docs/DESIGN_SYSTEM.md`.

Der Berichtsbereich beantwortet ausschließlich, welche vorhandenen
Beobachtungen und Belege Laura für den Bericht verwenden kann. Er ist
Berichtsvorbereitung und Dokumentationsübersicht im gewählten
Berichtszeitraum, keine zusätzliche Entwicklungsanalyse. Der Profilbereich
`Überblick` bleibt Eigentümer der kompakten Lernentwicklungsdarstellung;
`Kompetenzen` bleibt Eigentümer der detaillierten Kompetenz- und Belegansicht.
Phase 2 führt deshalb weder einen neuen Themenverlauf noch einen
Kompetenzentwicklungs-Drill-down, eine dritte Lernentwicklungsdarstellung,
eine automatische Entwicklungszusammenfassung oder eine automatische
Berichtsformulierung ein.

Die Phase-2-Berichte-Übersicht verwendet ausschließlich den inklusiven
Zeitraum des eindeutig gewählten RPD. Sie zeigt pro aktivem
`observation_id`, abgeschlossenem `report_draft_id`, abgeschlossenem
`learning_conference_draft_id` und aktuellem sicheren
`(student_id, competency_id)`-Bestätigungsstand höchstens ein neutrales
Timeline-Ereignis. Kompetenzzuordnungen bleiben Fachkarten- und
Beleggrundlage, erzeugen aber keine eigenen Timeline-Karten.
`persistence_events` und `orientation_changes` sind keine Timeline-Quellen.
Berichte verwenden `finalized_at` der neuesten gültigen, hashverifizierten
Revision; LEG verwendet `conference_date`, nicht `completed_at`.

Fachkarten zeigen absolute Dokumentationsmengen ohne Nenner, x/y-Semantik,
Prozentwert, Restspur oder Bewertung. Kleine fachbezogene Symbole unterstützen
die Orientierung, ohne eine fachliche Wertung oder ein Diagramm zu bilden.
Historische Kompetenzen bleiben aus aktuellen
Zählern ausgeschlossen. Bericht und LEG bleiben getrennte Aggregate und
werden nur displayseitig gemeinsam angezeigt. Die Timeline ist
ereignisorientiert und enthält weder Trend, Entwicklungsrichtung,
pädagogische Priorisierung noch Stärke-, Defizit- oder Förderlogik.

Die Implementierung ergänzt reine ViewModel-Projektionen, schülerbezogene
SQLite-Read-Snapshots, getrennte Batch-Lesepfade für Bericht- und
LEG-Revisionen, absolute Fachkarten und die horizontale
Dokumentations-Timeline. Sie ergänzt keine Tabelle, Migration, Schreiblogik
oder Persistenz. Automatisierte Offscreen-Tests prüfen die 2/4/5-Viewport-
Kapazitäten, Scrollsteuerung, Tastatur, Ankererhalt und ID-Navigation. Reale
macOS-Trackpad- und VoiceOver-Abnahme bleibt offen. Build, Packaging, Push,
Tag und Release wurden nicht ausgeführt.

## Berichte-Übersicht 0.3.1 / Build-304-Scope - Paket 1

Paket 1 ersetzt die bisherige vorbereitende Berichtsvorschau im Register
`Bericht` des Schülerprofils durch eine vertikal scrollbare, read-only
orchestrierte Übersicht. Sie zeigt Bericht-, LEG- und nächste Statusschritte,
den ausschließlich aus einem eindeutig gewählten RPD stammenden
Berichtszeitraum, eine gemeinsame Anzeigehistorie und Fachsprunganker.

Bericht und LEG bleiben technisch und fachlich getrennt. Ihre vorhandenen
Draft-, Revisions-, Abschluss- und Integritätsprojektionen werden erst im
Desktop-Adapter zu einer displayfertigen Übersicht zusammengesetzt. Bei
mehreren Berichtsentwürfen oder LEG-Arbeitsständen wird niemals automatisch
gewählt; `Zuletzt bearbeitet` beeinflusst nur die Reihenfolge der bestehenden
Auswahl.

Der bestehende `LearningReportDialog` bleibt in Paket 1 der einzige
Berichteditor. Die Übersicht öffnet ihn über eine kontrollierte
Navigationsgrenze und kann dort den vorhandenen Bereich
`Kompetenzen & Belege` sowie ein Fach fokussieren. Eine Einbettung als
gemeinsamer `LearningReportWorkspace` bleibt einem späteren Paket vorbehalten;
Editorzustand, Speichern, Revisionen, Vorschau und PDF-Funktionen werden nicht
dupliziert.

Zeitleiste, Stärken-/Watch-Kandidaten, neue Kompetenzlogik, neue Persistenz,
Migration und Schuljahresmodell gehören nicht zu Paket 1. Die entsprechenden
Flächen sind neutrale, klar bezeichnete Leerzustände.

## Pilot-Releaseautomation

Der mit Build 303 nachgewiesene lokale Pilot-Releaseprozess ist als
terminale, wiederaufnehmbare Automation umgesetzt. Build 303 ist seit
27. Juli 2026 die unveränderliche veröffentlichte Referenz: GitHub-Pre-Release
`v0.3.0-build303`, Quellcommit
`07c20a3764405bc1f535eb33efe809519dd8316b` und aktiver Pilot-Appcast. Stable
bleibt deaktiviert.

`scripts/release_pilot.py` trennt Inspect, Prepare, detached Clean-Build,
Paketprüfung, GitHub-Draft/Assetverifikation, Appcast-Publikation und
öffentliche Endverifikation. Das monotone Manifest ermöglicht sichere
Wiederaufnahme ohne Neubau nach späteren Netzwerk- oder
Authentifizierungsfehlern. Version und Build werden nie automatisch geändert;
Veröffentlichungen benötigen getrennte explizite Gates. Architektur,
Sicherheitsgrenzen und Betrieb stehen in `docs/RELEASE_AUTOMATION.md`.

Die Automation verändert weder Produktlogik noch SQLite-Datenmodell, UI,
Backup-/Restoreformat oder Verschlüsselungsstatus. Sie enthält keine Secrets,
liest keinen privaten Sparkle-Schlüssel und kann Stable weder erzeugen noch
aktivieren.

## Historischer Vorbereitungsstand 0.3.0 / Build 303

Der folgende Abschnitt hält den dokumentierten Stand vor der späteren
Veröffentlichung fest. Build 303 war zu diesem Zeitpunkt ein
macOS-arm64-Vorbereitungsstand, kein Release Candidate und kein verteiltetes
Artefakt. Der race-freie
Restore-Neustartfix ist committed. Die verbindliche Produktwahrheit, offene
Artefaktnachweise und Releasegrenzen stehen in
`docs/SECURITY_RELEASE_0_3_0.md`; die verständliche Schutzdarstellung in
`docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md`.

`src.version` führt `0.3.0` / Build `303` als gemeinsame Quelle für Bundle,
Über-Dialog, Buildkonfiguration und Dokumentgenerator. Der normale Gate-Off-
Pfad bleibt lokale SQLite-Datenbank, verwaltete Klartextdokumente und
ZIP-v1-Backup/Restore. Nur interne markergebundene Pakettests laden SQLCipher,
PyNaCl/libsodium und den Integrationsorchestrator. Es gibt keine automatische
Migration, keine UI-Aktivierung und keinen Zugriff auf Pilot- oder
Produktdaten.

Der macOS-arm64-Build verwendet ein neues Venv mit exakt gepinnten Versionen,
prüft native Laufzeiten vor PyInstaller, reduziert das fertige Bundle auf
arm64, signiert erst danach und führt Gate-Off-, Gate-On-, Keychain-, Bundle-,
Artefakt-, Pfad- und Klartextprüfungen vor DMG-Erzeugung aus. SQLCipher
Community 4.12.0 bleibt ausdrücklich nur die Sprint-11-Testengine; das
SQLCipher-4.17.0-Produktziel ist nicht freigegeben.

Builds 300 bis 302 bleiben historische, nicht verteilte Ausgangsstände.
Build 303 bündelt die dokumentierte Produktbasis einschließlich
Performance-Batch, Kursverbundsnapshot, Ereignisordnung,
Attachment-Unit-of-Work, Entwurfsauswahl, Restore-Worker und UX-Hardening.
Der immutabel nachweisende App-, DMG- und Prüfsummenstand wird ausschließlich
aus dem noch ausstehenden finalen Clean-Build-Commit erzeugt und im Release-
Inventar festgehalten.

Windows, Developer ID, Notarisierung, physische Touch ID, vollständiger
Power-Loss-Nachweis, Produktmigration, Pilotaktivierung und Stable-Appcast
bleiben getrennte Gates. Der GitHub-Pre-Release/Pilot erfolgt erst nach
Clean-Build und vollständiger Paketabnahme; es gibt keinen Stable-Appcast und
keinen automatischen Pilotrollout.

## Security Sprint 11 - kontrollierte Integration hinter inaktivem Gate

Security Sprint 11 verbindet die isolierten Foundations aus Sprint 8 bis 10
ausschließlich in einer markergebundenen temporären Testinstallation. Das
interne Gate `JKM_SECURITY_INTEGRATION_TEST=1` ist standardmäßig aus, nicht
über die UI erreichbar und akzeptiert weder den normalen `RuntimePaths`-Root
noch Pilot-, RC- oder echte Nutzerdaten. Unbekannte Gatewerte und gemischte
Bestände blockieren ohne SQLite-/SQLCipher-Fallback.

### Verbindliche Integrationsmatrix

| Komponente | heutiger Klartextpfad | neuer verschlüsselter Testpfad | Gate | Fehler / Recovery | Schema | Testnachweis |
|---|---|---|---|---|---|---|
| Startup / `RuntimePaths` | normale Rootauflösung und `prepare_runtime_storage` | `SecurityIntegrationGate` plus feste temporäre `SecurityIntegrationPaths` | exakt `1` und zwei Marker | ungültiger Root blockiert vor Mutation | nein | Gate-/Import-/Startup-Isolation |
| Connection Factory | `SQLiteDatabase` über SQLite-Provider | explizite SQLCipher-Factory mit DMK-geöffnetem Database-Key | nur Integrationsruntime | falscher/fehlender Key, Format oder Integrität blockiert; kein Create-Fallback | `user_version=1101` | Open, falscher Key, Reopen |
| Auth / DMK | bestehende lokale Authentifizierung | injizierter DMK-Loader erst nach Auth-Erfolg | keine UI-Aktivierung | fehlender/beschädigter Plattformschlüssel blockiert | nein | Passwortwechsel-/Support-Reset-Semantik |
| Migration / Journal / Lock | keine automatische Produktmigration | geschlossene markierte Testquelle, byte-identische Safety Copy, SQLCipher-Ziel, HMAC-Journal, externer pending/committed Anchor und exklusiver Lock | nur Test-Root | neue Prozess-Recovery, idempotente Phasen, Widerspruch blockiert | Integrationsmetadaten v1 | Fokus- und echte Crash-Subprozesse |
| Dokumentrepository | `documents.file_path` auf Klartextdatei | unveränderliche `security_document_generations` plus opaque aktive Referenz | nur SQLCipher-Ziel | vorbereitete Generation bleibt inaktiv; alte aktive Generation retained | neue Tabellen / Index | Import, Austausch, Restart, gemischter Zustand |
| Import / Lesen / Export / Löschen | Kopie in `documents/`, direktes OS-Öffnen, Soft-Delete | Container vor Pointer, zweiphasiger Reader, bewusster No-Clobber-Klartextexport, konservatives Retained | nur Application Adapter | keine erfolgreiche Meldung bei Teilfehler; kein GC | Generation/Lifecycle | Container-, Export- und Crashtests |
| Backup / Restore | ZIP-v1 und bestehendes Restore-Handoff | Sprint-9-Container für SQLCipher plus verschlüsselte Dokumente; Restore nur in neuen Staging-Root | nur Integrationsadapter | Vollverifikation vor Erfolg; alter Bestand bleibt | nein | Tamper, Crash, Restore-Reopen |
| Application Services | normale Desktop-Adapter mit Klartext-DB | Qt-freie `SecurityIntegrationRuntime` gegen zentrale Factory | nur Testcode | sanitierte Fehlercodes; keine UI | nutzt v1 | Student-/Dokumentprojektion gegen SQLCipher |
| Support-Reset / Passwortwechsel | bestehende Auth-Schicht | unverändert; DMK-/Datenkeys bleiben identisch | unabhängig vom Gate | fehlender Plattform-DMK blockiert | nein | explizite Nicht-Rotations-Regression |
| Nutzerführung | bestehende Dialoge | keine neue UI; ausschließlich technischer Testreport | nicht sichtbar | fail-closed ohne Geheimnisse/Pfade in Logs | nein | UI-/Import-Isolation |
| Packaging | bestehende Abhängigkeiten | keine Sprint-11-Paketaktivierung | gesperrt | PyNaCl/SQLCipher-Packaging bleibt Release-Gate | nein | `pip check`; kein Build |

### Datenfluss Startup bis Restore

`Gate/Marker prüfen -> Auth bestätigt -> DMK laden -> Database-Key-Envelope
öffnen -> Locks erwerben -> Klartextquelle und Dokumentinventar binden ->
byte-identische Safety Copy verifizieren -> separate SQLCipher-Datei ohne
ATTACH übertragen und reopen -> Dokumentcontainer PREPARED erzeugen ->
SQLCipher-Referenzen atomar ACTIVE schalten -> verschlüsseltes Backup
verifizieren -> alle Handles schließen -> SQLCipher und Dokumente frisch
reopen -> Klartextbestand Retained markieren -> COMPLETED -> optional Backup in
neuen Restore-Staging-Root extrahieren und vollständig reopen-verifizieren`.

Der Klartextbestand wird nicht ersetzt oder gelöscht. Der Testpfad startet
seine Application Services direkt gegen den validierten SQLCipher-Bestand.
Das bestehende ZIP-v1-Backup, normale Dokumentpfade, Produktstartup, Pilot, RC,
Excel, Packaging und Release bleiben ohne Gate unverändert.

## Security Sprint 9 - isolierter verschlüsselter Backupcontainer

Der Sprint ergänzt ausschließlich für synthetische Testdaten einen
versionierten, authentifizierten und streamend verschlüsselten Backupcontainer.
Der bestehende `.jkmbackup`-Writer, dessen Restore-Staging, Startup, Login, UI
und RuntimePaths bleiben unverändert und importieren den neuen Pfad nicht.

Jeder Container verwendet einen zufälligen 256-Bit-Backup-Key. DMK,
HKDF-zweckgetrennter Backup-Wrapping-Key und AES-256-GCM-Envelope schützen den
Schlüssel; Manifest und Nutzdaten werden mit Secretstream XChaCha20-Poly1305
authentifiziert verschlüsselt.

Writer, Verifier und Restore-Prototyp prüfen und veröffentlichen ausschließlich
im privaten synthetischen Test-Root. Packaging, Windows, realer Power-Loss,
Same-User-ABA, Retained-GC, weitergehende Zeroization und Produktintegration
bleiben Folge-Gates; P0 = 0 und P1 = 0 im ADR-088-Bedrohungsmodell.

## Security Sprint 7B - Migration State Foundations

Security Sprint 7B ergänzt drei Qt-freie Security-Foundations: eine
HMAC-authentisierte append-only Lock-Transitionskette, einen vollständigen
kanonischen Migrations-Crossbinding-Kontext und eine deterministische
recovery-aware Preflight-Ableitung.

Crossbinding umfasst Installation, Datenbankkontext, Migration und Generation,
DMK und Database-Key, Registry, Journal, Replay-Anker, Lockkopf, Source,
Backup, Target, Capabilities, Dateiidentitäten und erwartete Engine- sowie
Schemaversionen. Der Preflight besitzt genau die Modi `NEW`, `RESUME`,
`RECOVERY`, `COMPLETED` und `BLOCKED`.

Die Foundations bleiben ohne Produkt-, Startup-, Login-, UI-, Backup/Restore-
oder Orchestratorintegration. Nachgelagerte Security-Sprints bleiben gesperrt.

## Security Sprint 6 - Replay-Schutz, exklusiver Lock und Prototype-Recovery

Security Sprint 6 ist als Erweiterung der nicht produktiv aktivierten
Foundations implementiert und nach dem P1-Fix vollständig gegatet: ein externer monotoner
Replay-Anker, ein exklusiver POSIX/macOS-Migrations-Lock und eine eng
allowlistete ausführende Recovery-Orchestrierung für den guarded synthetischen
Migrationsprototyp. Alle Abhängigkeiten werden
explizit injiziert; es gibt weiterhin keine `RuntimePaths`-, Startup-, UI-,
Login-, Backup/Restore- oder Produktkopplung.

Der Anchor-Zustand liegt außerhalb von Envelope-Registry und Journal und bindet
Installation/Security-Context, Anchor-Version/-Revision, Database-Context,
DMK-/Keyset-ID/-Generation, Registry-High-Water-Mark,
Journal-/Migrationsgeneration sowie die exakten SHA-256-Digests beider
authentisierten Dateien. macOS verwendet
den eigenen Keychain-Service
`de.jenaplan.kompetenzmanager.monotonic-security-anchor` ohne Datei-Fallback.
Ein fehlender oder beschädigter Anker bei vorhandenem Security-Bestand,
Rollback, doppelte Revision, unplausibler Sprung, Kontextabweichung und
Parallelitätskonflikt blockieren ohne stille Neuerzeugung. Ein
`committed`/`pending`-Protokoll koppelt Plattformstore und Dateipublikation:
Prepare bindet alten und exakt geplanten neuen Snapshot, Publish schreibt die
Dateien und Commit akzeptiert ausschließlich exakt pending Digests. Nach Crash
darf exakt der alte Stand durch
`abort_pending(expected, observed_committed)` monoton verworfen oder exakt der
neue Stand durch Commit aufgelöst werden; jeder Mischstand blockiert. Der
exklusive Lock serialisiert diesen Advance prozessübergreifend. Windows bleibt
auf Port, Fake, Fehlervertrag und DPAPI-user-scope-Entwurf begrenzt.

Der Plattformvertrag `MigrationLockPort` besitzt den threadsicheren Test-Fake
`InMemoryMigrationLock`, den fail-closed Adapter
`UnsupportedMigrationLock` und den POSIX/macOS-Prototyp
`ExclusiveMigrationLock`. `database-migration-v1.lock` wird im injizierten
Test-Root exklusiv angelegt.
Eigentum bindet mehr als eine PID: Installation, Datenbankkontext,
Migration-ID, Prozessstartidentität, Nonce, Erstellungszeit und Dateiidentität
werden geprüft. Fremde, manipulierte, ausgetauschte oder uneindeutig stale
Locks werden nicht automatisch gelöscht oder überschrieben.

Die ausführende Recovery prüft vor jedem Schritt Lock, Journal-HMAC,
Replay-Anker, Rootgrenze und Dateiidentität. Sie darf nur eigene
identitätsgebundene Testziele zurückrollen, Backup-/Zielvalidierung fortsetzen,
das Testziel neu öffnen und bei authentisiertem `COMPLETED` ausschließlich das
evidence-gebundene Testziel und Backup per atomarem No-Clobber-Rename in retained Quarantine
verschieben und dort idempotent identitätsprüfen, aber niemals löschen.
Klartextquelle, Anchor, Registry, Journal, Lock, unbekannte Dateien, produktive
Pfade und reservierte Swap-Phasen bleiben unverändert. Auth-Recovery-Codes und
Support-Reset sind nicht Teil dieser Recovery.

Echte Subprozessabbrüche und kontrollierte Fehleradapter decken Crashfenster,
ENOSPC, Rechte, `fsync`, Rename/Replace und Dateiwechsel ab. Der Nachweis gilt nur
für synthetische temporäre Testdaten; vollständige Power-Loss-Sicherheit bleibt
ein offenes Plattformgate. Recovery verwendet für Ziel und Backup kein
pathname-basiertes `unlink` oder `remove`; das frühere finale Unlink-TOCTOU ist
beseitigt. Ein konkurrierend angelegter Quarantänepfad wird durch
`RENAME_EXCL`/`RENAME_NOREPLACE` niemals überschrieben; fehlt dieser
No-Clobber-Primitive, blockiert Recovery. Die bekannte P2-Grenze ist retained Quarantine ohne freigegebenen
handlebasierten Bereinigungsprozess.

Das Post-Fix-Gate ist vollständig grün: 215 fokussierte Sprint-6-Tests, 265
fokussierte Tests der Security Sprints 2 bis 6, 465
Security-/Support-Regressionstests, 130 Backup-/Restore-Regressionstests sowie
die Gesamtsuite mit 1148 Tests und 67 Subtests. `compileall`, `pip check`,
`git diff --check`, native Bridge-Checks mit ausschließlich erwarteten
Deprecated-Warnungen und die geschützten Hashprüfungen waren erfolgreich;
P0 = 0 und P1 = 0. Daraus folgt keine Produktfreigabe.

Für den kontrollierten Laura-Einzelpiloten bleibt der ad-hoc-signierte,
persönlich übergebene Pfad mit reproduzierbarem Clean Build, SHA-256-Manifest,
dokumentierter Gatekeeper-Freigabe und realer Keychain-/Bundle-ID-Prüfung
zulässig. Er ist nicht notarisiert und behauptet keine verifizierte
Entwickleridentität. Breite Verteilung bleibt an Developer ID und
Notarisierung oder eine gesonderte schulinterne MDM-Entscheidung gebunden.
Security Sprint 6 baut oder verändert kein RC- oder Pilotartefakt.

Security Sprint 7A ist nicht Bestandteil dieses Commits. Security Sprint 8A
wurde nicht begonnen und bleibt gesperrt; der historische fachliche
`Sprint 8A - Produktiver Stundenplan` ist davon verschieden.

## Security Sprint 5 - Product-Key-Envelope und Migrationsjournal-Foundation

Security Sprint 5 ergänzt zwei strikt isolierte, Qt-freie Bausteine. Ein
zufälliger 256-Bit-Database-Key wird unter einem per HKDF-SHA-256 eindeutig vom
DMK abgeleiteten Database-Wrapping-Key mit AES-256-GCM geschützt. Ein eigenes
versioniertes `DatabaseKeyEnvelope` authentifiziert sämtliche öffentlichen
Metadaten einschließlich einer monotonen Rewrap-Revision als AAD und wird atomar in
`database-key-envelopes-v1.json` gespeichert. Das generische Sprint-2-
`KeyEnvelope`, der DMK-Keychain-Lifecycle und `data-keysets.sqlite` bleiben
unverändert. Eine weitere getrennte HKDF-Domain authentifiziert die komplette
Registry samt Context, Generations-High-Water-Mark und Envelope-Mitgliedschaft
mit HMAC-SHA-256; auch die leere Registry bleibt dadurch manipulationsgeschützt.

Das Migrationsjournal `database-migration-journal-v1.json` speichert nur
technische Rollen, Dateibeweise, Phasen, Checks und sanitierte Fehlerklassen.
Ein separater HKDF-Zweck authentifiziert die vollständige kanonische Datei mit
HMAC-SHA-256. Journal und Envelope sind über Database-Context sowie
Database-Key-ID/-Generation kreuzgebunden. Die explizite State-Machine
verhindert illegale Sprünge; reservierte Pflichtchecks sind an ihre erreichte
Phase gebunden und Journalzeitpunkte monoton.
Recovery prüft Quelle, Backup und Ziel erneut und liefert ausschließlich eine
technische Entscheidung. Sie führt keine Dateioperation aus. Manipulation,
Korruption, unbekannte Version, Temp-Rest, fehlende oder ausgetauschte Datei
und widersprüchliche Historie blockieren.

Der vorhandene Sprint-4-Prototyp nutzt beide Bausteine ausschließlich mit neu
erzeugter guarded synthetischer SQLite in einem temporären Root. Er beweist
Envelope-Persistenz/-Entschlüsselung, SQLCipher-Erzeugung mit dem geladenen
Database-Key, phasenweises Journal sowie eindeutige Entscheidungen nach
Abbruch hinter Backup, während/nach Export, während Validierung und nach
Neuöffnung. Ein zweiter Lauf überschreibt vorhandene Sidecars oder Artefakte
nicht.

Threat Model und Grenzen: AEAD/HMAC schützen gegen Lesen des Database-Key und
gegen Manipulation ohne DMK. Sie schützen nicht gegen einen kompromittierten
Prozess mit DMK-Zugriff, vollständiges Replay eines älteren gültigen
Envelope/Journals, physische SSD-Restdaten oder ein kompromittiertes
Betriebssystem. Die Registry besitzt einen lokalen Generations-High-Water-Mark;
ein extern gegen Rollback geschützter monotoner Anker, produktive Database-Context-Bindung,
Windows-DPAPI/ACL/File-ID/Reparse-Point-Schutz, macOS-`F_FULLFSYNC`,
kontrollierter SQLCipher-4.17.0-Build, Packaging, Signierung, reale Crashtests,
exklusiver Prozess-Lock/handlegebundene Dateioperationen, Startup-Recovery,
Rotation und sichere Klartextentsorgung bleiben offen.

Es gibt keine RuntimePaths-, Startup-, Login-, Passwort-, UI-,
Backup/Restore-, Support-Reset-, Recovery-Code-, Produktdaten-, Dokument-,
Pilot-, RC-, Appcast- oder Releaseintegration. Normales SQLite bleibt der
Produktstandard. RC `0.2.2`, `security.sqlite`, Pilotdaten und bekannte
Exceldatei werden nicht geöffnet oder verändert.

## Security Sprint 4 - isolierter Datenbankmigrationsprototyp

Security Sprint 4 weist ausschließlich mit neu erzeugten synthetischen Daten
nach, dass eine Klartext-SQLite-Datenbank kontrolliert in eine separate
SQLCipher-Datenbank übertragen und vollständig verglichen werden kann. Der
Prototyp liegt unter `prototypes/database_encryption_migration/`, besitzt keine
RuntimePaths-, Startup-, UI-, Login-, Recovery-, Support-Reset-, Backup/Restore-
oder Releaseintegration und akzeptiert nur eine technische Synthetic-Guard-
Fixture im eigenen temporären Arbeitsbereich.

Der Ablauf prüft die Quelle, erzeugt und prüft ein unverändertes SQLite-Backup,
exportiert Schema und Daten in ein separates Cipher-Ziel, stellt die von
`sqlcipher_export` nicht übertragenen persistenten PRAGMAs explizit wieder her
und vergleicht Tabellen, Zeilenzahlen, Primär-/Fremdschlüssel, Trigger, Views,
Indizes, `sqlite_sequence`, Schemahash, kanonische Datenhashes und PRAGMAs.
Danach folgen
SQLCipher-/SQLite-Integrität und ein echtes Neuöffnen. Backup-, Export-,
Commit-, Abbruch-, Korruptions-, Wrong-Key- und Versionsfehler lassen die
Quelle bytegleich und entfernen ein eigenes fehlgeschlagenes Ziel.

Der flüchtige 256-Bit-Testkey bildet nur den zukünftigen Database-Key ab. Das
Produktziel bleibt eine zufällige DB-Key-Instanz unter einem zweckgebundenen,
aus dem DMK abgeleiteten Wrapping-Key; der DMK selbst wird nie SQLCipher-Key.
Key-Wrapping, Live-Dateiaustausch, Startup-Recovery, Klartextentsorgung,
produktive Migration, Packaging und Rollout bleiben offen. RC `0.2.2`,
`security.sqlite`, Pilotdaten, Produktdaten, Backups, Dokumente und die bekannte
Excel-Datei bleiben außerhalb des Prototyps.

## Security Sprint 3 - SQLCipher Infrastructure

Eine kleine Qt-freie Engine-Grenze stellt Standard-SQLite und einen expliziten
SQLCipher-Provider bereit. Die bestehende Hauptanwendung verwendet weiterhin
ausschließlich normales SQLite; SQLCipher wird weder beim Start noch über
Login, UI, Recovery, Support-Reset, Backup oder Restore aktiviert.

Der isolierte Testpfad verwendet `sqlcipher3` 0.6.2 mit der nachgewiesenen
SQLCipher Community Engine 4.12.0, erzeugt ausschließlich temporäre
verschlüsselte Datenbanken mit synthetischen Daten und Laufzeitschlüsseln und
prüft richtiges/falsches Keying, Korruption, Integrität, Transaktionen und die
Ablehnung durch normales `sqlite3`. Ein eigenständiger macOS-arm64-
PyInstaller-Prototyp wurde außerhalb der Releasepfade erfolgreich ausgeführt.
Dieser lokale Nachweis besitzt im Repository noch keinen reproduzierbaren
SQLCipher-Packagingpfad mit eigener Spec und Manifestkette.

Für ein späteres Produkt bleibt SQLCipher 4.17.0 aus einem kontrollierten,
hash-gepinnten macOS-/Windows-Build das Ziel. Produktive Schlüsselhierarchie,
Migration, Startup, Backup/Restore, Signierung, Notarisierung, Windows und
Release sind ausdrücklich offen. RC `0.2.2`, Pilotdaten, `security.sqlite`,
fachliche SQLite, Dokumente, Backups, Appcast und UI bleiben unverändert.

## Security Sprint 2 - Key Foundation und DMK-Lifecycle

Als isolierter Entwicklungsstand besteht eine Qt-freie Grundlage für einen
zufälligen 256-Bit-Data-Master-Key (DMK), versionierte Keysets mit den Zuständen
`pending`, `active`, `revoked` und `failed`, ein kanonisches Key-Envelope-Format
sowie einen getrennten macOS-Keychain-Adapter. Der gemeinsame Plattformport ist
für eine spätere Windows-DPAPI-/Credential-Manager-Implementierung vorbereitet.

App-Passwort, Gerätecredential, Supportschlüssel und DMK bleiben getrennte
Konzepte. Ein Passwortwechsel verändert den DMK nicht. Der aktuelle Stand wird
nicht vom App-Start aufgerufen, verschlüsselt keine fachliche Datenbank, keine
Dokumente und keine Backups und verändert weder UI noch Pilotdaten.

Release Candidate `0.2.2`, `security.sqlite` und seine Schema-Version 3 bleiben
unverändert. Die Entwicklung verwendet ausschließlich einen neuen, nicht in
RuntimePaths registrierten Metadaten-Sidecar für technische Keyset-Daten. Es
gibt keine Migration, keine Startup- oder Releaseintegration und keine
Produktivfreigabe. Der Sidecar ist noch nicht kryptografisch authentifiziert;
bei uneindeutiger Längen-/Fingerprint-Korruption blockiert der Lifecycle, ohne
den möglicherweise korrekten Plattform-DMK automatisch zu löschen.

## Sprint 0.2S.1 - Support-Assistent UX

Der Betreiber erhält mit `Jenaplan Support-Assistent.app` eine vom
Kompetenzmanager, Pilotpaket und Updatepfad getrennte grafische macOS-arm64-
Anwendung. Sie macht den bereits geprüften Offline-Support-Reset verständlich,
ohne Protokoll, Kryptografie, Tokenformat, Schlüsselmodell, Backupvertrag,
Appfunktion oder Schülerdatenmodell zu verändern.

Der Assistent verarbeitet nur eine bewusst gewählte technische Anfrage, einen
bewusst gewählten externen verschlüsselten Privatschlüssel und flüchtigen
UI-State. Fachliche SQLite, Security Store, Dokumente, Backups und Runtime-
Daten liegen außerhalb seiner Architektur- und Paketgrenze.

## Sicherer macOS-Updatepfad ab Sprint 0.2U.1

Sprint 0.2U.1 entscheidet die Architektur, implementiert aber noch keinen
produktiven Updater. Der unveränderte Release-Kandidat `0.2.0` besitzt keinen
Updateclient und wurde Laura nicht installiert. Ihre erste Installation ist
deshalb direkt ein bewusst manuell geöffnetes Pilot-DMG `0.2.1`; erst diese
Version enthält den für den beaufsichtigten Pilotkanal konfigurierten
Sparkle-2-Client. `0.2.2` / Build `202` ist das erste beaufsichtigte
Sparkle-Folgeupdate. Ein gleichnamiger Neuaufbau von `0.2.0` wird wegen nicht
unterscheidbarer Installationen verworfen.

Der spätere Updatepfad ersetzt ausschließlich das unveränderliche App-Bundle.
Fachliche SQLite, verwaltete Dokumente, Exporte, Backups, Logs, Security Store,
AppPreferences und nicht synchronisierender macOS-Schlüsselbund bleiben
außerhalb des Bundles. `0.2.2` enthält deshalb weder Fach- noch
Securitymigration. Der ad-hoc-signierte Einzelpilot behauptet weder Developer ID noch
Notarisierung. Produktive Veröffentlichung bleibt gesperrt, bis Developer ID,
Hardened Runtime, Notarisierung/Stapling, signierter HTTPS-Appcast, externer
privater EdDSA-Schlüssel und der reale Schlüsselbund-/Touch-ID-Übergang von der
ad-hoc-signierten Pilotbasis nachgewiesen sind. Details regelt ADR-073.

## Historischer Ursprung des produktiven Supportbetriebs (Sprint 0.2B.6)

Der vorhandene App- und Security-Vertrag bleibt unverändert. Neu ist ein
vollständig getrenntes macOS-arm64-Supportpaket mit Finder-Startern für
Token-Signatur und bewusste externe Schlüsselbereitstellung. Es arbeitet
offline, liest keine fachliche Runtime und wird weder App-/DMG- noch Laura-
Paketbestandteil. Der private Schlüssel wird ausschließlich außerhalb des
Repositorys verschlüsselt als PKCS#8 mit restriktiven Rechten erzeugt.

Die produktive Public-Key-Registry besitzt einen strikt versionierten,
deterministisch validierten Einbindungsweg für mehrere aktive, rotierende,
retirierte und widerrufene öffentliche Schlüssel. Die erstmalige Aktivierung
von `support-2026-b` geschah historisch mit 0.2.2; der dokumentierte
0.3.0-Stand führt diesen lokalen Support-Reset weiter. Privater Schlüssel und
Passphrase bleiben extern. Rotation und Widerruf erfordern weiterhin einen
neuen geprüften App-Release.

## Historischer Pilot-Release-Kandidat 0.2.0

Version `0.2.0` fasst den implementierten lokalen Security-, Betriebs- und
Onboardingstand als technisch prüfbaren Pilot-Release-Kandidaten zusammen. Die
kanonische Version stammt aus `src/version.py`; App-Metadaten, Build-Info, DMG
und Dokumentbuild übernehmen sie ohne zweite Versionsquelle.

Der Release-Kandidat startet ohne Schüler-, Pilot- oder Runtime-Daten. Die
App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
FileVault und ein geschütztes macOS-Benutzerkonto bleiben erforderlich. Der
produktive Support-Reset ist ab `0.2.2` für den beaufsichtigten Pilotbetrieb als
betreuter Ausnahmeweg freigeschaltet. Recovery-Code bleibt der erste Weg.

Technisch nicht durch reale Hardwareabnahme ersetzt sind echter Sleep/Wake, die
physische Touch-ID-Systemaufforderung mit Fingerabdruck, App-Switcher und die
vollständige Aktivierungs-/Widerrufsreise. Developer-ID-Signierung,
Apple-Notarisierung sowie die reale Keychain-/Touch-ID-Prüfung nach dem Update
auf Lauras Mac bleiben ebenfalls offen.

## Historischer Support-Reset-Ablauf ab Version 0.2B.5

Wenn Passwort und Recovery-Codes nicht mehr verfügbar sind, kann die App eine
rein technische Reset-Anfrage erzeugen. Sie wird nicht automatisch übertragen
und enthält keine Schüler-, Dokument-, Schul-, E-Mail- oder Betriebssystemdaten.
Support prüft die Identität organisatorisch außerhalb der App und signiert die
Anfrage mit einem extern verwahrten privaten Ed25519-Schlüssel.

Die App prüft Tokenformat, Signatur, öffentlichen Schlüssel, Installation,
Nutzer, Anfrage, Nonce, Aktion und Zeitfenster. Der Reset erfolgt erst nach einer
zweiten bewussten Bestätigung und einem erfolgreich erzeugten und erneut
verifizierten fachlichen Sicherheitsbackup. Danach sind altes Passwort,
Recovery-Codes, gespeicherte Geräteanmeldung, Touch ID und laufende Sitzung
unwirksam; die App endet in `password_reset_pending` und beendet sich.

Beim nächsten Start werden neues Passwort, neuer Recovery-Satz und bewusste
Sicherungsbestätigung verlangt. Fachliche Daten, IDs, Dokumentpfade,
Backupformat, Anzeigename und Onboardingstatus bleiben unverändert. Der Prozess
entschlüsselt nichts und ist kein Masterkennwort.

Ab Version `0.2.2` enthält die Default-Key-Registry genau den vom Product Owner
bestätigten öffentlichen Schlüssel `support-2026-b`. Die UI kann damit
signierte Codes produktiv prüfen. Private Schlüssel, Passphrase und zentrale
Audit-/Cloudsysteme sind nicht Bestandteil der App.

## Geräteanmeldung und Touch ID ab Version 0.2B.4a

`Auf diesem Gerät angemeldet bleiben` bezeichnet eine widerrufbare lokale
Geräteanmeldung, keine dauerhafte App-Sitzung. Nach ausdrücklich bestätigter,
erfolgreicher Passwortanmeldung speichert macOS ausschließlich ein zufälliges
256-Bit-Gerätegeheimnis im nicht synchronisierenden Schlüsselbund. Das Passwort
wird niemals gespeichert; Security Store v3 enthält nur Salt, versionierten
Hash und technische Bindungs-/Statusmetadaten. Eine neue Sitzung entsteht erst
am Auth-Gate und endet beim Schließen der App.

Manuelle, Inaktivitäts- und Wake-Sperre bleiben aktiv. Nach einer Sperre kann
auf unterstützten Macs optional echtes Touch ID verwendet werden; das Passwort
bleibt jederzeit sichtbar verfügbar. Abbruch, fehlende Einrichtung, Lockout,
Systemabbruch oder Credential-Inkonsistenz öffnen die App nicht, sondern führen
zum Passwortpfad. Passwortänderung, Recovery und Support-Reset widerrufen über
die Security-Epoch alle gespeicherten Geräteanmeldungen.

Die Funktion verschlüsselt keine fachliche SQLite-Datenbank, Dokumente oder
Backups. `.jkmbackup`, Restore, Diagnose und AppPreferences enthalten kein
Gerätegeheimnis und keine Credential-Metadaten. Nicht-macOS-Plattformen bleiben
ohne Dummy-Sicherheit vollständig passwortfähig. Die reale physische Abnahme
von Sprint 0.2B.4, insbesondere echter Sleep/Wake, bleibt offen.

## Security Core ab Version 0.2

Sprint 0.2B.4 integriert den Core produktiv. Restore-Recovery bleibt vor der
Authentifizierung; die fachliche Runtime samt Pilotdaten, Produktordnern,
SQLite-Adaptern und `AppShell` entsteht erst nach erfolgreichem Erstkonto,
Login oder abgeschlossenem Passwort-Reset. Neuinstallationen und vorhandene
ungeschuetzte Installationen erhalten genau ein lokales Konto mit zehn einmalig
angezeigten Recovery-Codes.

Die Sitzung existiert nur im Arbeitsspeicher und wird durch `user_id`,
`installation_id` und `security_epoch` gebunden. Manuelle Sperre, Inaktivitaet
und Wake zeigen eine opake neutrale Sperransicht und erhalten ungespeicherte
In-Memory-Eingaben. Die Sicherheitseinstellungen bieten feste Intervalle,
Passwortwechsel, Recovery-Code-Erneuerung und `Jetzt sperren`.

Ein optionaler lokaler Anzeigename gehoert zum allgemeinen App-Profil, nicht
zum Authentifizierungskonto. Er wird bei Erstkonto/Legacy-Aufnahme freiwillig
erfasst, spaeter im getrennten Bereich `Persönliche Begrüßung` geaendert und
fuer eine dezente tageszeitabhaengige Dashboard-Begruessung verwendet. Der
atomare Store `<runtime-root>/app-preferences.json` bleibt ausserhalb von
Security-SQLite, fachlicher SQLite, Support-Reset und `.jkmbackup`.

Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
FileVault und ein geschuetztes Betriebssystemkonto bleiben empfohlen. Die
gespeicherte Geräteanmeldung, macOS-Keychain, Touch ID und die
Support-Reset-Token-UI sind im Stand 0.2 umgesetzt. Windows Hello und eine
Verschluesselung der fachlichen Dateien sind nicht Bestandteil dieses Stands.

Die reale Pilot-Mac-Abnahme der 0.2B.4-Sicherheitsintegration bleibt trotz
automatisierter und Offscreen-Pruefungen weiterhin offen, solange die
physische Bedienungshilfen-basierte Abnahme nicht nachgeholt wurde.
Insbesondere ist echter Sleep/Wake auf dem Pilot-Mac noch nicht physisch
bestaetigt.

## Erste Schritte ab Version 0.2C.1

Nach erfolgreicher Authentifizierung und Aufbau der fachlichen Shell kann die
Lehrkraft einmalig eine kurze Orientierung `Erste Schritte` erhalten. Der Flow
ist kein fachlicher Assistent: Er erklaert Zweck und Reihenfolge, zeigt nur
vorhandene Bereiche und navigiert zu bestehenden Seiten. Er erzeugt keine
Stammgruppen, Kurse, Kinder, Beobachtungen, Backups, Beispiel- oder
Pilotdaten.

Der Status liegt rein lokal in
`<runtime-root>/app-preferences.json` und ist weder Security-Attribut noch
fachlicher Datenbestand. Fachliches Restore, Support-Reset, Passwortwechsel und
Recovery veraendern ihn nicht. Bestehende Installationen ohne Onboarding-Status
duerfen beim ersten Start dieser Produktversion einmal die Orientierung sehen;
`completed` und `dismissed` oeffnen nicht erneut automatisch. Unter
`Einstellungen` kann `Erste Schritte erneut öffnen` bewusst aufgerufen werden.

Die Architektur besitzt einen fachlich getrennten Security Core unter
`<runtime-root>/security/`. Die App-Sperre ist keine Verschluesselung der
Datenbank, Dokumente oder Backups. Der Security Store wird nicht gesichert,
restored, exportiert oder diagnostiziert und ist nicht mit fachlichen IDs oder
Inhalten verbunden.

Historisch lieferten Sprint 0.2B.2 zunächst nur den testbaren Core und Sprint
0.2B.3 den offline signierten Ed25519-Support-Reset. Die damals noch offenen
Start-, Sitzungs-, Login-, Recovery- und Reset-Oberflaechen wurden durch Sprint
0.2B.4 und 0.2B.5 umgesetzt. Version `0.2.2` schließt die betriebliche
Freischaltung mit einem freigegebenen öffentlichen Produktivschlüssel ab.

## Aktueller Produktstand

Der Jenaplan-Kompetenzmanager ist eine lokale Python-/PySide6-Desktop-Anwendung fuer Lehrkraefte. PySide ist die aktive Produktoberflaeche, SQLite die produktive lokale Datenhaltung.

Der implementierte Stand nach Sprint 10B und den anschliessenden Schuelerprofil-UX-Korrekturen umfasst die zentralen Arbeitsbereiche fuer Stammdaten, Unterrichtsalltag, Beobachtung, Kompetenzdokumentation, Schuelerprofil, Lernentwicklungsbericht und Lernentwicklungsgespraech. Unveraenderliche Bericht- und LEG-Revisionen sowie daraus erzeugte PDF-Artefakte sind produktiv umgesetzt.

Das Projekt befindet sich in der **Produktreifephase**. Der dokumentierte
Stand ist Version `0.3.0` / Build `303` mit lokaler Anmeldung, Keychain,
optionalem Touch ID, Sperre, Support-Reset, ZIP-v1-Backup/Restore,
Restore-Worker, Bericht-/LEG-Entwurfsauswahl, Revisionen und PDF-Ausgaben.
Der Schwerpunkt liegt auf Konsistenz, Barrierearmut, Pilotierbarkeit,
Dokumentationsqualität, Betriebsentscheidungen und Release-Vorbereitung. Ein
Buildartefakt, eine reale Pilotabnahme oder App-Store-Entscheidung folgt daraus
nicht.

Excel/VBA ist eine historische Vorstufe. Die damalige Workbook-Linie wird unter `legacy/excel/` als Referenz erhalten, ist aber weder Zielplattform noch aktiver Produktpfad. Historische Workbook-Versionen wie `v0.4` und fruehere Ausgabedateien sind keine aktuellen Hauptartefakte.

## Nächste Phase nach Version 0.3.0

Die unmittelbar nächste Phase ist der beaufsichtigte Pilottest des
Release-Kandidaten 0.3.0 und die Behebung ausschließlich tatsächlich beobachteter
pilotkritischer Fehler. Pilottestpunkte sind Validierungen und noch keine
automatisch beschlossenen Funktionsänderungen.

Für den ersten alltagsrelevanten Funktionsschnitt nach dem Pilottest sind
Schülerlisten-Import, Schuljahreswechsel, Mehrkind-Schnellbeobachtung und
Klassen-/Kursmatrix Kandidaten. Keiner dieser Kandidaten ist derzeit als
Implementierungssprint freigegeben. Vor einer Freigabe folgen Product Discovery,
Produktentscheidung, Datenmodell-, Architektur-, Datenschutz- und UX-Review.
Der kleinste empfohlene nächste fachliche Planungsschritt ist ein
Discovery-/Architecture-Gate für den Schülerlisten-Import; ein
Implementierungssprint folgt daraus nicht automatisch.

## Projektziel

Der Kompetenzmanager unterstuetzt Lehrkraefte an Jenaplan-Grundschulen bei der strukturierten, nachvollziehbaren und alltagstauglichen Dokumentation von Lernentwicklung nach dem Thueringer Lehrplan.

Das Produkt soll den Dokumentationsaufwand reduzieren, ohne paedagogische Entscheidungen zu automatisieren. Beobachtungen, bestaetigte Kompetenzstaende, Berichte und Lernentwicklungsgespraeche bleiben fachlich unterscheidbare Arbeits- und Ausgabekontexte.

## Paedagogische Leitlinien

- Beobachtung steht vor Bewertung.
- Dokumentierte Ereignisse bleiben bis zum konkreten Beleg nachvollziehbar.
- Entwicklung wird aus realen Beobachtungen und Bestaetigungen sichtbar, nicht aus erfundenen Zwischenwerten.
- Fehlende Dokumentation ist kein negativer Leistungsstatus.
- Automatische Projektionen liefern Orientierung, aber keine fertigen paedagogischen Aussagen.
- Lehrkraefte verantworten manuelle Berichtstexte, Gespraechsinhalte und bewusste Evidenzauswahl.
- Status, Dokumentationsabdeckung und Entwicklung duerfen nicht allein durch Farbe vermittelt werden.

## Abgeschlossene Kernfunktionen

### Stammdaten und Unterrichtskontext

- persistente Schueler-, Stammgruppen-, Kurs- und Kursverbundverwaltung
- stabile technische IDs und kontrollierte Archivierungs- beziehungsweise Aktivitaetsregeln
- persistenter Wochenstundenplan mit Stammgruppen-, Kurs- und Kursverbundkontext
- read-only Dashboard `Heute` mit aktueller beziehungsweise naechster Stunde, Tagesverlauf, Dokumentationsorientierung und direkten Arbeitswegen

### Beobachtungen und Dokumente

- Beobachtungen mit Datum, Kontext, Notiz, Kompetenzzuordnung und Einzelbewertungen
- Schnellbeobachtungen ohne erzwungene Kompetenzzuordnung
- Bearbeiten und Soft Delete ueber den bestehenden Application-/Repository-Pfad
- studentenzentrierte Dokument- und Medienreferenzen ohne Datei-BLOBs in SQLite
- historisch sichere Darstellung nicht mehr aktiver oder nicht mehr verfuegbarer Referenzen

### Schuelerprofil und Kompetenzen

- kindbezogener Arbeitsraum mit dauerhaft sichtbarem Schuelerkontext
- Profilueberblick nach der produktiven Variante-A-UX
- dokumentationsbezogene Orientierungskarten, Kompetenzuebersicht, neueste Beobachtungen und neutrale Hinweise auf noch nicht dokumentierte Bereiche
- Kompetenz-Cockpit mit der Hierarchie `Fach -> Kompetenzbereich -> Thema -> Kompetenz`
- kanonische Trennung von bestaetigtem Stand, berechnetem Vorschlag und Beobachtungsevidenz
- Maus-, Tastatur-, Fokus- und Accessibility-Vertraege fuer zentrale Profilinteraktionen

### Lernentwicklungsbericht

- persistenter bearbeitbarer Berichtsentwurf `RPD`
- bewusst ausgewaehlte Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen
- manuell verantwortete Gesamt- und Fachtexte
- stabiles Berichtaggregat `RPT` mit unveraenderlichen Revisionen `RPV`
- snapshotbasierte historische Leseansicht mit Integritaetspruefung
- unveraenderliches finales PDF-Artefakt `RPA` genau einer aktuellen finalisierten Revision

### Lernentwicklungsgespraech

- persistenter, live-referenzierender LEG-Arbeitsentwurf `LCD`
- phasenorientierter Arbeitsraum fuer Vorbereitung, Gespraech und gemeinsam festgehaltene Ergebnisse
- bewusst ausgewaehlte Kompetenz- und Beobachtungsbelege
- stabiles LEG-Aggregat `LCF` mit unveraenderlichen Revisionen `LCV`
- snapshotbasierte historische Leseansicht mit Integritaetspruefung
- unveraenderliches finales PDF-Artefakt `LCA` genau einer aktuellen abgeschlossenen Revision

## Aktive Systemarchitektur

Die aktive Schichtenfolge lautet:

```text
PySide UI
-> ViewModels
-> Desktop Adapter
-> Application Commands und Queries
-> Domain Services und Validatoren
-> Repositories
-> SQLite
```

Fuer Ausgaben gilt zusaetzlich:

```text
verifizierter fachlicher Snapshot
-> renderer-neutrales Ausgabemodell
-> reiner PDF Renderer
-> unveraenderliche Datei und Artefaktreferenz
```

Fuer den lokalen macOS-Pilotbetrieb gilt:

```text
signiertes oder ad-hoc signiertes App-Bundle
-> unveraenderliche eingebettete Laufzeit und Ressourcen
-> getrennter Benutzerpfad unter ~/Library/Application Support/
-> SQLite, Dokumente, Exporte, Backups und Logs ausserhalb der App
```

Ein späterer Apple-Silicon-Build wird reproduzierbar mit PyInstaller erzeugt
und setzt macOS 13 voraus. Die Übergabevariante enthält keine Schülerdaten.
Version 0.3.0 / Build 303 ist ein Release-Vorbereitungsstand; der finale
Clean-Build vor einer kontrollierten GitHub-Pre-Release-/Pilot-Übergabe steht
noch aus. Stable bleibt deaktiviert; eine Update-/Appcast-Aktivierung ist kein
Bestandteil dieser Übergabe.

### Architekturprinzipien

- Widgets enthalten keine Businesslogik und greifen nicht direkt auf SQLite zu.
- SQLite und die dokumentierten Datenquellen bilden die fachliche Source of Truth.
- Repositories kapseln Persistenz; Application- und Domain-Schichten verantworten Schreibprozesse und Validierung.
- ViewModels und Adapter liefern displayfertige Projektionen, ohne fachliche Daten in der UI neu zu berechnen.
- Jede Funktion besitzt eine Implementierung, kann aber mehrere Einstiegspunkte haben.
- Schuelerprofil, Bericht und LEG verwenden dieselbe kanonische Kompetenz- und Evidenzprojektion, ohne eigene Statuslogik zu entwickeln.
- Historische Snapshots werden vor jeder Lese- oder PDF-Projektion gegen ihren gespeicherten SHA-256 geprueft.
- `PdfRenderer` kennt weder SQLite noch Repositories, Draftstatus oder fachliche Freigaberegeln.
- Bericht und LEG bleiben getrennte fachliche Domains mit getrennten Aggregaten, Revisionen und Artefakten.
- Schema- und Datenmodellveraenderungen erfolgen nur nach Product-Owner-, Datenmodell- und Architekturreview.

## Datenhaltung und Dateien

- Produktive lokale Datenbank: `data/kompetenzmanager.sqlite`
- Lehrplanbasierter Kompetenzkatalog: `data/curriculum_catalog_v1.csv`
- Konfiguration und Farbreferenzen: strukturierte Dateien unter `data/`
- Verwaltete Schuelerdokumente: `data/documents/<student_id>/`
- Finale Berichtartefakte: `data/documents/<student_id>/reports/<RPT>/<RPV>/`
- Finale LEG-Artefakte: `data/documents/<student_id>/learning_conferences/<LCF>/<LCV>/`

SQLite speichert fuer Dokumente und PDF-Ausgaben Metadaten und Referenzen. Dateien werden nicht als BLOB in der Datenbank gespeichert. Produktive Beziehungen verwenden stabile IDs und nicht sichtbare Namen oder UI-Positionen.

## Produkt- und Ausgabemodell

### Schuelerprofil

Das Schuelerprofil ist eine aktuelle Live-Arbeitsansicht. Es zeigt dokumentierte Staende, Evidenz, Dokumentationsabdeckung und Arbeitswege, ist aber kein offizielles oder eingefrorenes Dokument.

### Bericht

Der Berichtsentwurf bleibt bearbeitbar und live-referenzierend. Eine bewusste Finalisierung erzeugt beziehungsweise aktualisiert ein stabiles Berichtaggregat und schreibt eine neue unveraenderliche Revision. Korrekturen erfolgen als Folgerevision; fruehere Revisionen bleiben historisch lesbar.

### Lernentwicklungsgespraech

Der LEG-Entwurf bleibt ein eigener bearbeitbarer Gespraechsarbeitsstand. Ein expliziter Abschluss friert ausschliesslich den reproduzierbaren Gespraechskontext, gemeinsame Ergebnisse und bewusst ausgewaehlte Belege in einer unveraenderlichen LEG-Revision ein. Interne Vorbereitung wird nicht automatisch Teil des Abschlusses.

### PDF-Artefakte

PDF ist ein Ausgabeformat und keine Fachschicht. Finale Bericht- und LEG-PDFs werden ausschliesslich aus der jeweils aktuellen, hashverifizierten Revision erzeugt. Drafts, Widgets und spaetere operative Daten sind keine Quellen eines finalen PDF-Artefakts. Ein vorhandenes Artefakt wird bei erneutem Aufruf verifiziert und nicht ueberschrieben.

## Informationsarchitektur und Design-System

Die globale Navigation trennt `ARBEIT` mit `Heute` und `Schueler` von `VERWALTUNG` mit `Stammdaten` und `Einstellungen`. Beobachtungen, Kompetenzen, Berichte und LEG bleiben ueber den Kindkontext erreichbar.

Das verbindliche PySide-Design-System ist in `docs/DESIGN_SYSTEM.md` dokumentiert. Es definiert Tokens, Typografie, Flaechen, Karten, Tabellen, Dialoge, Fokus, Reduced Motion, Tastaturbedienung und Accessibility. Historische Workbook-Layouts, feste Zellpositionen und Excel-Zoomstufen sind keine Designreferenz der aktiven Produktlinie.

Zentrale UX-Prinzipien:

- ruhige, lehrkraftzentrierte Informationshierarchie
- genau eine dominante Aktion pro Arbeitskontext
- ganze sinnvolle Zeilen und Karten als ausreichend grosse Interaktionsflaechen
- progressive Disclosure fuer Evidenz und historische Details
- sichtbare Fokuszustaende und vollstaendige Tastaturwege
- Status nie ausschliesslich ueber Farbe
- responsive Desktop-Zielgroessen 1180 x 760, 1280 x 800 und 1400 x 900

## Prototypen und Product Discovery

In `prototypes/` abgelegte UX-Studien sind isolierte Entscheidungs- und Referenzartefakte. Sie verwenden fiktive Daten und werden erst nach ausdruecklicher Produktentscheidung in die produktive App uebertragen. Ein Prototyp ist weder Datenquelle noch produktive Nebenanwendung.

## Historische Excel-/VBA-Linie

Die fruehere Excel-/Workbook-Architektur, VBA-Interaktionsschicht, UserForm- und Worksheet-Dialogspikes sowie die historische Version `v0.4` bleiben als Projektgeschichte dokumentiert. Ausfuehrbare Altstaende und Quellen liegen unter `legacy/excel/`.

Fuer die aktive Produktlinie gilt:

- keine neuen Excel- oder VBA-Funktionen
- keine Workbook-Datei als aktuelles Hauptartefakt
- keine VBA-/AppleScript-Smoke-Tests als Standardpruefung
- Excel/openpyxl nur bei ausdruecklichem Legacy- oder Exportauftrag

Historische Sprint- und ADR-Texte bleiben als damaliger Entscheidungsstand lesbar, werden aber als historisch oder durch die PySide-/SQLite-Linie abgeloest gekennzeichnet.

## Dokumentationssystem

- `PROJECT.md`: aktueller Produktstand und dauerhafte Projektgrundlagen
- `SPRINTS.md`: operative Planung und historisch gekennzeichnete Sprintstaende
- `DECISIONS.md`: Architekturentscheidungen und ihr Umsetzungsstatus
- `CHANGELOG.md`: chronologische Aenderungen ohne Vorwegnahme einer Release-Version
- `docs/PROJECT_CONSTITUTION.md`: verbindliche Projektverfassung
- `docs/TECHNICAL_NAMES.md`: technische Namen und IDs
- `docs/DATA_REGISTRY.md`: Datenquellen und Persistenzobjekte
- `docs/DATA_LIFECYCLE.md`: Schreib-, Historien- und Loeschprozesse
- `docs/VIEW_DATA_OWNERSHIP.md`: Owner und Quellen der Ansichten
- `docs/UI_DATA_MAPPING.md`: sichtbare UI-Felder und ihre Datenquellen
- `docs/DESIGN_SYSTEM.md`: verbindliches PySide-Design-System

Neue Architektur-Dokumente werden nur eingefuehrt, wenn eine echte Luecke nicht in den bestehenden Governance-Dokumenten geschlossen werden kann.

## Rollen und Entwicklungsreihenfolge

- Product Owner: gibt neue Funktionen, fachliche Aenderungen und Datenmodellaenderungen frei.
- Fachliche Review: prueft paedagogische Verstaendlichkeit, Lehrplanbezug und nicht bewertende Darstellung.
- UX-/Accessibility-Review: prueft Informationshierarchie, Bedienbarkeit, Tastatur, Fokus und Kontrast.
- Technische Review: prueft Architekturgrenzen, Wartbarkeit, Integritaet und Lauffaehigkeit.

Jede Implementierung folgt dieser Reihenfolge:

1. Vision
2. Product Discovery
3. Produktentscheidung
4. Datenmodell-Review
5. Architektur-Review
6. UX-Review
7. Prompt-Review
8. Implementierung
9. Technical Review
10. Test
11. Commit

## Aktueller Entwicklungsstatus

Der Funktionsaufbau bis Sprint 10B sowie die anschliessenden
Schuelerprofil-UX-Korrekturen sind umgesetzt. Die aktive Phase ist der
beaufsichtigte Pilottest von Version 0.2 mit anschliessender, befundbasierter
Fehlerbehebung.

Aktuelle Arbeitsschwerpunkte sind:

- reale fachliche, ergonomische und betriebliche Pilotpruefung
- ausschliesslich befundbasierte P0-Fehlerbehebung
- Accessibility- und Tastaturqualitaet
- robuste Desktop-Darstellung in den festgelegten Zielgroessen
- Vorbereitung der noch nicht freigegebenen Planungskandidaten aus `BACKLOG.md`
- Betriebs- und Datenschutzentscheidungen ohne Vorwegnahme einer Auslieferung

Weiterhin offen bleiben insbesondere Product-Owner- beziehungsweise Betriebsentscheidungen zu Rollen und Berechtigungen, Aufbewahrung und Zugriffsschutz, Archivierung und Verschluesselung, Renderer-Versionierung, mehreren Artefakten pro Revision sowie einem moeglichen gemeinsamen, klar getrennten Bericht-/LEG-Ausgabepaket.

## Definition of Done

Eine Aenderung gilt als abgeschlossen, wenn:

- die freigegebene fachliche Anforderung umgesetzt oder dokumentiert ist,
- keine Projekt- oder Architekturregel verletzt wurde,
- Datenquellen, technische Namen, Lifecycle und UI-Mapping konsistent dokumentiert sind,
- das Changelog aktualisiert wurde,
- fokussierte und risikogerechte Pruefungen erfolgreich sind,
- die PySide-Anwendung weiterhin importierbar und offscreen startbar ist,
- keine nicht freigegebene Funktion oder Datenmodellentscheidung eingefuehrt wurde.
