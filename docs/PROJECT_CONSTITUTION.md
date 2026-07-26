# Project Constitution

## Entwicklungsgrenze Security Sprint 10

Security Sprint 10 darf ausschließlich eine isolierte Foundation für
synthetische verschlüsselte Dokumente ergänzen. Der Pfad erhält Test-Root,
Quelle, DMK, Dokument-/Installationskontext, Storage-ID und erwartete
Generationen explizit per Dependency Injection. Er liest weder `RuntimePaths`
noch Produktdaten und wird von `src/core`, `src/desktop_app`, Startup, Login,
UI, produktiven Dokumentservices, Backup/Restore oder Releasecode nicht
importiert.

Jede Dokumentgeneration erhält einen zufälligen 256-Bit-Document-Key. Ein per
HKDF-SHA-256 zweckgetrennter Document-Wrapping-Key unter dem DMK schützt ihn in
einem eigenen AES-256-GCM-Envelope. Der Dokumentstrom verwendet libsodium
Secretstream XChaCha20-Poly1305 mit strikt versioniertem eigenem Format,
kanonischen AAD-Verträgen, genau einem Abschluss-Tag und physischem EOF.
Backup-Key-, Backup-Envelope-, Backup-Manifest- und Backupcontainerformate
werden nicht als Dokumentformat wiederverwendet.

Der Container ist eine Datei mit integriertem Envelope. Ein unveränderliches
Payload-Binding ist vom austauschbaren Envelope getrennt: Secretstream bindet
Format, Container-, Storage- und Document-Key-Identität, Key-Generation,
Streamheader und Chunkvertrag; Envelope-AAD bindet zusätzlich erwartete
Dokument-ID/-Generation, Installation, Datenbankkontext, DMK und
Envelope-Revision. Ein DMK-Schutzwechsel erzeugt immer einen neuen
No-Clobber-Container und darf den bestehenden Container niemals in-place
ändern. Datenrotation verwendet einen neuen zufälligen Document-Key und eine
vollständige Neuverschlüsselung; Dokumentaustausch erzeugt eine neue
Dokumentgeneration.

Dateinamen enthalten ausschließlich eine zufällige opaque Storage-ID,
Envelope-Revision und technische Erweiterung. Dokument-ID, Originalname,
MIME-Typ, Klartextgröße/-hash, fachliche Zuordnung, Installation,
Datenbankkontext, Erstellungszeit und App-/Formatversion liegen nur im
verschlüsselten Manifest beziehungsweise im späteren SQLCipher-Produktmodell.
Der sichtbare Header bleibt auf technisch notwendige Format-, Algorithmus-,
Framing-, Container-, Key-, Envelope- und Streamwerte beschränkt.

Writer, Verifier, Reader, bewusster Testexport, Rewrap,
Generationsaustausch-Simulation und Retained-/GC-Dry-Run arbeiten nur in einem
privaten, eigentümergeprüften, markergebundenen synthetischen Root. Quellen
liegen außerhalb des verwalteten Storagebereichs, tragen einen festen
Synthetikmarker und werden no-follow sowie identitätsgebunden gelesen.
Container werden zunächst als versteckte Retained-Datei vollständig
geschrieben, synchronisiert und neu verifiziert und erst danach per atomarem
No-Clobber-Hardlink veröffentlicht. Bestehende Ziele, Quellen, alte
Generationen, unbekannte Dateien und ausgetauschte Pfade werden weder
überschrieben noch automatisch gelöscht.

Secretstream v1 ist sequenziell und besitzt kein Random Access. Ein späterer
interner Viewer muss den Container vor Ausgabe vollständig verifizieren und
anschließend denselben gebundenen Inhalt erneut sequenziell lesen; echtes
Seek/Random-Access benötigt ein neues, separat freizugebendes Format. Ein
vollständig gültiger Altcontainer- oder Datenroot-Replay ist ohne produktiven
SQLCipher-Pointer beziehungsweise externen monotonen Zustand nicht erkennbar
und bleibt Integrations-Gate.

Produktimport, Produktviewer, Produktdownload/-export, bestehende
Dokumentpfade, Produktdatenmodell, Startup, Login, UI, Application Services,
Backup/Restore, Migration realer Daten, Identity-VFS, Packaging, RC, Pilot,
Appcast, Build, Release und die bekannte Exceldatei bleiben unverändert. Es
gibt keine Produktaktivierung, keine rechtliche Compliance-Aussage und keine
Garantie physischer sicherer Löschung auf SSD, APFS oder NTFS.


## Entwicklungsgrenze Security Sprint 9

Security Sprint 9 darf ausschließlich einen isolierten Writer, Verifier und
Restore-Prototyp für einen verschlüsselten Backupcontainer mit synthetischer
SQLCipher-Testdatenbank und synthetischen Dokumenten ergänzen.

Jeder Container benötigt einen zufälligen 256-Bit-Backup-Key, einen
DMK-gebundenen HKDF-SHA-256-Backup-Wrapping-Key und ein versioniertes
AES-256-GCM-Envelope. Der Nutzdatenstrom verwendet Secretstream
XChaCha20-Poly1305 und blockiert unbekannte oder inkonsistente Formate
fail-closed.

Produktintegration, Aktivierung des bestehenden `.jkmbackup`-Pfads, Startup,
Login, UI, RuntimePaths, Pilot, RC, Release und Excel bleiben ausgeschlossen.

## Entwicklungsgrenze Security Sprint 7B - Migration State Foundations

Security Sprint 7B darf isolierte, Qt-freie Foundations für eine
authentisierte Lock-Transitionskette, eine reine recovery-aware
Preflight-Ableitung und einen vollständigen Migrations-Crossbinding-Kontext
ergänzen. Produkt- und Orchestratorverkabelung sind nicht freigegeben.

Locktransitionen sind append-only, HMAC-authentisiert, lückenlos sequenziert
und über Vorgängerdigest, Replay-Anker und Kontext gebunden. Der Kontext bindet
Installation, Datenbankkontext, Migration, DMK und Database-Key samt
Generationen, Registry, Journal, Anchor, Lockkopf, Quelle, Backup, Ziel,
Capabilities, Dateiidentitäten sowie erwartete SQLite-, SQLCipher- und
Schemaversionen.

Der Preflight liefert ausschließlich `NEW`, `RESUME`, `RECOVERY`,
`COMPLETED` oder `BLOCKED`. Fehlende, zusätzliche, ausgetauschte,
phasenfremde oder widersprüchliche Evidenz blockiert. Adapter authentisieren
Quellen vor der Projektion; die Domain führt weder I/O noch Mutation aus.
Startup, Login, UI, RuntimePaths, Backup/Restore und Produktmigration bleiben
unverändert.

## Entwicklungsgrenze Security Sprint 6

Security Sprint 6 darf ausschließlich die isolierten Security-Foundations und
den explizit injizierten synthetischen Migrations-Workspace erweitern. Der
offizielle Runner und sämtliche Recovery-, Crash- und Fault-Injection-Tests
verwenden einen pro Lauf neu erzeugten temporären Root. Produktive
`RuntimePaths`, fachliche SQLite, `security.sqlite`, Dokumente, Backups,
Pilotdaten, RC- und Releaseartefakte werden weder als Quelle akzeptiert noch
verändert.

Ein externer monotoner Security-Anker bindet Installation beziehungsweise
Security-Context, Formatversion, monotone Revision, Database-Context,
DMK-/Keyset-ID und -Generation, Registry-High-Water-Mark,
Journal-/Migrationsgeneration sowie die exakten SHA-256-Digests der
authentisierten Registry und des authentisierten Journals außerhalb dieser
replaybaren Dateien. Der Plattformport ist fail-closed. Ein fehlender,
beschädigter, rückläufiger, kontextfremder oder unplausibel vorspringender Anker darf bei
vorhandenen Security-Artefakten weder still zurückgesetzt noch neu erzeugt
werden. macOS verwendet einen eigenen Keychain-Namespace ohne Datei-Fallback;
Windows bleibt auf Port, Fake und dokumentierten DPAPI-Vertrag begrenzt.

Dateien und Plattformstore werden über ein explizites `committed`/`pending`-
Protokoll gekoppelt. Prepare bindet den alten committed Snapshot und exakt den
geplanten neuen Snapshot, danach werden die authentisierten Dateien publiziert;
Commit ist nur bei exakt den pending Digests zulässig. Nach Crash darf
`abort_pending(expected, observed_committed)` ausschließlich bei exakt dem
alten Dateistand pending entfernen und die vorbereitete höhere Anchor-Revision
übernehmen; exakt der neue Dateistand darf pending committen. Jeder andere
Mischstand blockiert. Abort ist kein Reset oder Revisionsrücklauf. Der
exklusive Migrations-Lock serialisiert dieses Protokoll prozessübergreifend.

Eine Migration oder technische Migrations-Recovery benötigt für denselben
Installations- und Datenbankkontext einen exklusiven, verifizierten Lock. PID
oder Pfad allein beweisen kein Eigentum. Lock-Nonce, Prozessstartidentität und
Dateiidentität sind mitzubeweisen; fremde, manipulierte oder uneindeutig stale
Locks werden nicht automatisch gelöscht oder überschrieben. Eine Stale-
Übernahme ist ohne erfolgreichen Recovery-Evidence-Validator unzulässig. Symlinks,
Pfade außerhalb des Test-Roots und Identitätswechsel blockieren.

Die ausführende Recovery-Orchestrierung ist ausschließlich für eigene,
identitätsgebundene Testartefakte freigegeben. Vor jeder Operation müssen Lock,
Journal-HMAC, Replay-Anker, Rootgrenze und unmittelbare Dateiidentität erneut
geprüft werden. Sie darf ein eindeutig unvollständiges eigenes Testziel
entfernen, Prüfungen fortsetzen, das Testziel neu öffnen und bei
authentisiertem `COMPLETED` ausschließlich evidence-gebundenes Testziel und
Backup in eine eindeutig benannte retained Quarantine verschieben. Recovery
darf dabei keinen vorhandenen Namen überschreiben und diese Quarantänebestände
nicht löschen. Klartextquelle, Anchor, Registry,
Journal, Lock und unbekannte Dateien bleiben erhalten. Sie darf niemals produktive
Pfade oder reservierte Swap-Phasen verändern. Unklare Zustände sind `blocked`
und führen zu keiner Dateioperation.

Crash-, ENOSPC-, Rechte-, `fsync`-, Rename-/Replace- und Austauschtests belegen nur
das Verhalten des isolierten Prototyps; vollständige Stromausfallsicherheit
wird nicht behauptet. Recovery verwendet für Ziel und Backup keinerlei
pathname-basiertes `unlink` oder `remove`; das frühere finale Unlink-TOCTOU ist
damit beseitigt. Als bekannte P2-Grenze bleiben evidence-gebundene retained
Quarantine-Artefakte ohne freigegebenen handlebasierten Bereinigungsprozess.
Startup,
Login, Passwortwechsel, Auth-Recovery-Codes, Touch ID, Support-Reset,
produktives Backup/Restore, Produktmigration, UI und Verschlüsselungsaktivierung
bleiben unverändert. `Recovery-Code` bezeichnet weiterhin ausschließlich den
bestehenden Authentifizierungsweg und ist nicht mit Migrations-Recovery
gleichzusetzen.

## Entwicklungsgrenze Security Sprint 5

Security Sprint 5 darf ausschließlich im explizit injizierten isolierten
Prototyp-Workspace arbeiten. Runner und Tests verwenden dafür jeweils einen
neu erzeugten temporären Root. Zulässig sind dort nur die guarded synthetische
Quelle, ihr verifiziertes Backup, das separate SQLCipher-Ziel, das bereits
geschützte Database-Key-Envelope und das authentisierte technische Journal.
Keiner dieser Pfade wird durch Startup, RuntimePaths, UI, Login,
Backup/Restore oder Support-Reset aufgerufen.

Die Schlüsselhierarchie ist verbindlich `DMK -> HKDF-SHA-256 Database-
Wrapping-Key -> zufälliger 256-Bit-Database-Key -> SQLCipher`. App-Passwort,
Recovery-Code, Support-Key und Gerätecredential sind ausgeschlossen.
Database-Wrapping-Key, Journal-HMAC-Key und Database-Key bleiben flüchtig und
zweckgetrennt. Kein Secret darf in SQLite, Sidecar-Metadaten, Journal, Log,
Exception, Konfiguration, Backup oder Bundle stehen.

Envelope, vollständige Envelope-Registry und Journal sind über getrennte
Domain-Keys strikt versioniert, kanonisch, authentifiziert und
fail-closed. Unbekannte Felder/Versionen/Algorithmen, Manipulation, Korruption,
Symlink, Temp-Rest oder geänderte Dateiidentität blockieren; vorhandene
unbekannte Bestände werden weder ersetzt noch neu erzeugt. Recovery liefert
nur eine Entscheidung und löscht, verschiebt oder ersetzt keine Datei.

Produktive SQLite, `security.sqlite`, Development-Keyset-Sidecar, Keychain,
Runtime, Pilotdaten, Dokumente, Backups, RC `0.2.2`, Appcast, Release- und
Supportpakete sowie die bekannte Exceldatei bleiben unangetastet. Der
Dateiaustausch bleibt simuliert. Es gibt keine Freigabe für Produktmigration,
Rotation, Startup-Recovery, Klartextlöschung oder Windowsbetrieb.

## Entwicklungsgrenze Security Sprint 4

Security Sprint 4 darf nur neu erzeugte, eindeutig markierte synthetische
Klartextdatenbanken in einem eigenen temporären Arbeitsbereich lesen. Die
Migration erzeugt ausschließlich ein separates verifiziertes Backup und ein
separates SQLCipher-Ziel. Eine Quelle ohne Guard-Tabelle, feste Application-ID
und feste Prototyp-User-Version wird vor Backup und Cipher-Dateierzeugung
abgelehnt.

Der Database-Key ist zufällig, 32 Byte lang und nur im Testprozess vorhanden.
Er ist weder DMK noch App-Passwort. Das spätere Ziel ist `DMK ->
zweckgebundener Database-Wrapping-Key -> zufälliger Database-Key`; Wrapping,
Envelope-Persistenz und Rotation sind nicht Teil dieses Sprints.

Ein Lauf ist nur erfolgreich, wenn Quelle, Backup und Ziel strukturell und
inhaltlich gleich sind, alle SQLite-/SQLCipher-/Fremdschlüsselprüfungen
erfolgreich sind, das Ziel mit dem richtigen Key neu geöffnet wird und der
Quell-Dateihash unverändert bleibt. Bei Fehlern bleibt die Quelle maßgeblich;
ein eigenes Ziel wird verworfen. Der Dateiaustausch wird nicht implementiert.

Produktive SQLite, `security.sqlite`, RuntimePaths, Startup, Login, Recovery,
Touch ID, Support Reset, Backup/Restore, UI, RC `0.2.2`, Appcast, Releasepakete,
Pilotdaten, Dokumente, Backups und bekannte Excel-Datei werden nicht geöffnet,
migriert oder verändert. Es gibt keine Produkt- oder Pilotfreigabe.

## Entwicklungsgrenze Security Sprint 3

Security Sprint 3 stellt ausschließlich eine optionale, isolierte
SQLCipher-Infrastruktur bereit. Normales SQLite bleibt der unveränderte
Standard der Hauptanwendung. Es gibt keine Umschaltung über Startup,
Umgebungsvariablen, Login oder UI und keinen Rückfall von SQLCipher auf
unverschlüsseltes SQLite.

SQLCipher-Tests dürfen nur zur Laufzeit erzeugte 32-Byte-Testschlüssel,
synthetische Inhalte und automatisch entfernte temporäre Verzeichnisse
verwenden. Bestehende fachliche Datenbanken, `security.sqlite`, der
Development-Keyset-Sidecar, Pilotdaten, Release Candidate `0.2.2`, Appcast,
Backups und Dokumente werden nicht geöffnet, migriert oder verändert.

Der DMK ist weder App-Passwort noch unmittelbarer produktiver
Datenbankschlüssel. Eine spätere Produktarchitektur benötigt einen eigenen
zufälligen DB-Key, der unter einem zweckgebundenen Schlüssel des DMK geschützt
wird. Ableitung, Wrapping, Persistenz, Migration und Startup-Freigabe bleiben
außerhalb dieses Sprints.

Ein falscher Schlüssel und ein beschädigter verschlüsselter Header können an
der SQLCipher-Grenze denselben Fehler liefern. Der Provider weist beide
fail-closed und ohne Neuerstellung ab; er behauptet ohne zusätzliche
authentisierte Metadaten keine technisch nicht belegbare Unterscheidung.

## Entwicklungsgrenze Security Sprint 2

Security Sprint 2 ist ausschließlich eine isolierte Entwicklungsgrundlage.
Release Candidate `0.2.2`, Pilot- und Laura-Daten, bestehender Security Store,
Startup, RuntimePaths, UI und Releasepakete bleiben unverändert. Es gibt keine
Migration und keinen Zugriff auf Pilotdaten.

Der Data Master Key darf niemals in SQLite, Logs, Diagnosen, Backups, UI oder
Fehlermeldungen gelangen. Keyset-Metadaten enthalten keine fachlichen IDs und
keine Schüler-, Dokument-, Berichts- oder LEG-Inhalte. App-Passwort,
Recovery-Code, Support-Reset, Gerätecredential und DMK bleiben getrennt;
Passwortwechsel und Recovery-Aktionen verändern den DMK in diesem Sprint nicht.

Die bestehende Aussage, dass die App-Sperre keine Verschlüsselung von
Datenbank, Dokumenten oder Backups ist, bleibt vollständig gültig. Die
Foundation erzeugt noch keinen Schutz fachlicher Daten und wird nicht
automatisch ausgeführt.

## Sprint 0.2S.1 - Eigenständiger Support-Assistent

Der `Jenaplan Support-Assistent` ist eine eigenständige macOS-arm64-
Betreiberanwendung. Er ist weder Bestandteil von
`Jenaplan-Kompetenzmanager.app` noch von Pilot-, Laura- oder normalen
Updatepaketen. Er darf keine fachliche SQLite-Datenbank, Dokumente, Backups,
AppPreferences, Security Store oder produktive Runtime öffnen oder suchen.

Der Assistent ersetzt ausschließlich die Bedienoberfläche des vorhandenen
Offline-Signaturwegs. Requestformat, `JKM-SR1`-Tokenformat, Ed25519-
Kryptografie, Schlüsselmodell, UUID-Bindung, Backupvertrag und App-seitiger
Reset bleiben unverändert. Private Schlüssel und Passphrasen bleiben extern
und werden niemals gebündelt. Als Schlüsselmaterial enthält das Paket nur die
öffentliche Projektion der Produktregistry.

Ein menschlicher Installationsname und der daraus abgeleitete lesbare
Anfragecode sind flüchtige, nicht sicherheitsrelevante Zuordnungshilfen. Sie
werden weder in Request oder Token aufgenommen noch persistiert oder auditiert.
Die Sicherheitsbindung bleibt ausschließlich die vorhandene Installations-UUID.
Das lokale technische Audit enthält nur Zeitpunkt, Request-ID, Key-ID und
Aktion; niemals Token, Passphrase, privaten Schlüssel, Nonce, fachliche Daten
oder lokale Quellpfade.

## Release-Grenze Version 0.2.2

Der technisch umgesetzte Stand darf als leerer macOS-arm64-Pilot-
Release-Kandidat `0.2.2` gebaut und ausschließlich als beaufsichtigtes
Sparkle-Pilotupdate von `0.2.1` installiert werden. `src/version.py` bleibt die kanonische
Produktversionsquelle. Release-Artefakte enthalten keine Pilot-, Fach-,
Runtime- oder Security-Daten und keine privaten oder Testschlüssel.

Diese Grenze gilt unverändert für App-Bundle und DMG. Für den fachlichen
Pilottest darf daneben ein eindeutig bezeichnetes, ausschließlich synthetisches
`.jkmbackup` als separates Restore-Artefakt übergeben werden. Es wird nicht in
die App eingebettet und enthält weder Security Store noch Konto, Passwort,
Recovery-Codes, Gerätecredentials, Support-Tokens oder Schlüssel. Leere
Erststartvariante und Laura-Testdatenvariante verwenden exakt dasselbe leere
Installationsartefakt.

Laura hat `0.2.0` nicht installiert und beginnt direkt mit `0.2.1`. Version
`0.2.2` ist das erste beaufsichtigte Folgeupdate über den festen,
EdDSA-authentisierten Sparkle-Pilotkanal. Prüfung, Download und Installation
erfolgen nur nach bewusster Nutzeraktion. Stable, automatische Hintergrundinstallation und
eine allgemeine Produktivfreigabe bleiben ohne Developer ID, Notarisierung und
die übrigen ADR-073-Gates verboten.

Der Pilot-Zusatzschritt in `Erste Schritte` darf ausschließlich den bestehenden
Restore-Dateidialog öffnen. Er darf kein Backup suchen, vorauswählen, importieren
oder bestätigen. Synthetische Fachdaten bleiben ein separates `.jkmbackup`.

Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
Die produktive Support-Key-Registry enthält ab `0.2.2` ausschließlich den vom
Product Owner bestätigten öffentlichen Schlüssel `support-2026-b` im Status
`active`. Privater Schlüssel und Passphrase bleiben extern. Echter Sleep/Wake,
physische Touch ID, App-Switcher, vollständige Aktivierungs-/Widerrufsreise,
Developer-ID-Signierung und Apple-Notarisierung bleiben offene reale
Release-Prüfungen und dürfen nicht als automatisiert bestanden gelten.

## Sicherheitsnachtrag Sprint 0.2B.5

- Support-Reset ist kein Masterkennwort, entschlüsselt keine Daten und darf
  ausschließlich Authentifizierungszustände verändern.
- Anfrage und Token enthalten nur technische Bindungsdaten. Support erhält
  keine Schüler-, Dokument-, Backup- oder sonstigen Fachinhalte.
- Ohne aktive Anfrage, gültigen kurzlebigen einmaligen Ed25519-Token und
  erfolgreich erzeugtes sowie verifiziertes `.jkmbackup` findet kein Reset statt.
- Der atomare Abschluss invalidiert Passwort, Recovery-Codes,
  Gerätecredentials und Sitzung, erhöht die Security-Epoch, setzt
  `password_reset_pending` und beendet die App.
- Private Schlüssel bleiben außerhalb von Repository, Build und App-Bundle.
  Die produktive Registry enthält ab `0.2.2` nur den bestätigten öffentlichen
  Schlüssel; Rotation und Widerruf benötigen weiterhin ein App-Update.
- Der nächste Start erzwingt neues Passwort, neuen Recovery-Satz und
  Sicherungsbestätigung, bevor die Fach-App geöffnet wird.
- Fachliche Daten, IDs, Dokumentpfade, Backup-/Restoreverträge, Anzeigename und
  Onboardingstatus bleiben unverändert. Offene reale Pilotprüfungen bleiben offen.

## Sicherheitsnachtrag Sprint 0.2B.4a

- Persistente Geräteanmeldung und aktive App-Sitzung sind getrennte Konzepte.
  Das Credential darf am Auth-Gate eine neue flüchtige Sitzung erzeugen, hebt
  aber manuelle, Inaktivitäts- oder Wake-Sperren niemals auf.
- Das App-Passwort darf weder im Schlüsselbund noch in Preferences, Dateien,
  Backups, Logs oder Diagnose landen. Nur ein zufälliges, widerrufbares
  256-Bit-Gerätegeheimnis darf im lokalen, nicht synchronisierenden
  Plattform-Secret-Store liegen.
- Security Store ist kanonisch für Hash, Bindung, Security-Epoch und Status.
  Passwortänderung, Recovery und Support-Reset widerrufen Gerätecredentials.
- Lokale Biometrie ist optional. Passwort bleibt immer verfügbar; OS-Abbruch,
  Nichtverfügbarkeit, Lockout oder Fehler dürfen keine Sitzung freigeben.
- Es entsteht keine Datenbank-, Dokument- oder Backupverschlüsselung. Die
  physische 0.2B.4-Pilot-Mac-Abnahme einschließlich echtem Sleep/Wake bleibt
  offen und darf nicht als bestanden dargestellt werden.

Dieses Dokument legt die verbindlichen Architekturregeln fuer den Jenaplan-Kompetenzmanager ab Sprint 4 fest.

## Source-of-Truth-Regeln

Das Datenmodell ist die einzige fachliche Wahrheit.

Das Design-System ist Source of Truth fuer alle Benutzeroberflaechen.

Die Technical Naming Registry in `docs/TECHNICAL_NAMES.md` ist Source of Truth fuer technische Namen.

Die Data Registry in `docs/DATA_REGISTRY.md` ist Source of Truth fuer SQLite-Datenquellen und historische Workbook-Projektionen.

Das UI Data Mapping in `docs/UI_DATA_MAPPING.md` ist Source of Truth fuer die Herkunft sichtbarer UI-Felder.

Die View Data Ownership in `docs/VIEW_DATA_OWNERSHIP.md` ist Source of Truth fuer Datenverantwortung je Ansicht.

Der Data Lifecycle in `docs/DATA_LIFECYCLE.md` ist Source of Truth fuer freigegebene Schreibprozesse.

## Security-Grenze ab Version 0.2

Sprint 0.2B.4 aktiviert diese Grenze im produktiven Start. Die verbindliche
Reihenfolge lautet: Restore-Worker-Dispatch, Runtime-Pfade, Instanz-Lock,
Restore-Recovery, ausschliesslich technische Runtime-/Security-Pfade,
Security-Store-Pruefung, minimale Authentifizierungsoberflaeche und erst nach
einer erfolgreichen Authentifizierung beziehungsweise vollstaendig
bestaetigten Kontoaufnahme Pilotdaten, Produktverzeichnisse, normales Logging,
fachliche SQLite-Datenbank, Adapter, `AppShell`, Projektionen und Hauptfenster.
Restore-Recovery bleibt damit ausnahmslos vor Login; fachliche Daten werden vor
Authentifizierung weder geoeffnet noch projiziert.

Die Start- und Sperrgrenze ist fail-closed. Marker ohne Store, Store ohne
Marker, korrupte oder neuere unbekannte Security-Daten sowie nicht eindeutig
klassifizierbare Sicherheitsfehler starten keine fachliche App und loesen
weder eine neue Kontoaufnahme noch eine stille Reparatur aus. Genau ein lokales
Konto, eine rein fluechtige In-Memory-Sitzung und eine monotone
`security_epoch` sind verbindlich. Passwortwechsel, Recovery und Support-Reset
invalidieren aeltere Sitzungen. Es gibt keinen allgemeinen Auth-Bypass.

Manuelle Sperre, Inaktivitaet und Wake verdecken nicht transparent, sondern
entfernen alle fachlichen Fenster aus der sichtbaren Oberflaeche. Ungespeicherte
Eingaben bleiben ausschliesslich im Arbeitsspeicher erhalten und werden nach
erfolgreichem Entsperren fortgesetzt. Laufende Backups duerfen im Hintergrund
sicher enden; eine unbestaetigte Restore-Vorschau wird beim Sperren verworfen,
ein bereits bestaetigter Worker-Handoff nicht abgebrochen. Eine Sitzung wird
niemals ueber einen Neustart oder Restore hinweg fortgesetzt.

Die lokale Anwendungssperre schuetzt ausschliesslich den normalen Zugang ueber
die Anwendung. Sie ist keine Verschluesselung der Datenbank, Dokumente oder
Backups. `kompetenzmanager.sqlite`, verwaltete Dokumente und `.jkmbackup`
bleiben unverschluesselt; FileVault, ein geschuetztes Betriebssystemkonto und
sichere Geraeteverwaltung bleiben notwendig.

Sprint 0.2C.1 darf nach erfolgreicher Authentifizierung und nach Aufbau der
fachlichen Shell einmalig `Erste Schritte` anzeigen. Diese Ansicht ist
ausschliesslich Orientierung und Navigation. Sie darf keine fachlichen Daten
anlegen, keinen Import starten, kein Backup automatisch erzeugen, keine
fachliche Entscheidung treffen und keine Security-/Restore-Reihenfolge
veraendern. Der lokale Fortschritt gehoert zu `app-preferences.json`, nicht zum
Security Store, nicht zur fachlichen SQLite-Datenbank und nicht zu
`.jkmbackup`.

Authentifizierungsdaten sind technisch und fachlich vollstaendig von allen
Schueler-, Beobachtungs-, Kompetenz-, Berichts-, LEG- und Dokumentdaten
getrennt. Der kanonische Security Store liegt unter
`<runtime-root>/security/security.sqlite`, besitzt eine eigene Versionierung
und ist niemals Bestandteil von Backup, Restore, Export oder Diagnose. Ein
Restore fachlicher Daten ersetzt, loescht oder initialisiert ihn nicht.

Version 0.2 erlaubt genau ein aktives lokales Lehrkraftkonto je Installation.
Es gibt kein Masterkennwort, keinen Pepper im App-Bundle, kein Cloudkonto,
keinen Cloud-Reset, keine Rollen und keinen Mehrbenutzerbetrieb. Passwortverlust
darf fachliche Daten weder loeschen noch unbrauchbar machen. Der Security Core
bleibt eine eigenstaendige Domain-/Application-/Infrastructure-Grenze; Qt,
fachliche Adapter und Widgets greifen nicht direkt auf den Store zu.

Sprint 0.2B.2 stellt ausschliesslich diesen Core bereit. Eine spaetere
Startintegration muss Neuinstallation und ungeschuetzte Bestandsinstallation
bewusst unterscheiden. Sie darf erst nach eigener Freigabe die App sperren;
der produktive Start bleibt in diesem Sprint unveraendert und unblocked.

Sprint 0.2B.3 erlaubt ausschliesslich einen Qt-freien Offline-Support-Reset mit
Ed25519. Es gibt weiterhin kein Masterkennwort. Private Schluessel duerfen
niemals im Repository, Build oder App-Bundle liegen; die App enthaelt nur eine
oeffentliche Key-Registry, deren Rotation und Widerruf ein App-Update erfordert.
Anfrage und Token muessen kurzlebig, einmalig und vollstaendig an Installation,
Nutzer, Anfrage, Nonce, Aktion und `key_id` gebunden sein. Das Offline-Verfahren
besitzt ein dokumentiertes Risiko durch eine falsch gesetzte lokale Uhr.

Vor jeder Reset-Transaktion ist ein mit dem vorhandenen Backupformat
erfolgreich erzeugtes und vollstaendig verifiziertes fachliches
Sicherheitsbackup zwingend. Der Security Store bleibt ausgeschlossen. Der
Reset darf ausschliesslich Authentifizierungszustaende auf
`password_reset_pending` setzen, Recovery-Zustaende widerrufen und die monotone
Security-Epoch erhoehen. Fachliche Daten, Dokumente, Backups, IDs und
Restore-Vertraege duerfen nicht veraendert werden. UI, Startintegration,
Sitzung, neues Passwort und neue Recovery-Codes bleiben ausserhalb von 0.2B.3.

## Architekturprinzipien

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Python verantwortet Datenmodell, Application Layer, Domain Layer, Persistenz, UI-nahe Adapter, ViewModels, PySide-Oberflaeche, UI-Projektionen, Berichte, Exporte und Fachlogik.

Excel/openpyxl ist aus dem aktiven Projektpfad entfernt und nur noch im archivierten Legacy-Bereich `legacy/excel/` zulaessig, wenn ein ausdruecklicher Legacy- oder Exportauftrag vorliegt.

VBA ist kein Zielpfad fuer neue Features, UI, Smoke-Tests, Automatisierung oder produktive Workflows.

Alte VBA-Quellen, Seeds und Workbook-Generatoren bleiben unter `legacy/excel/` als Legacy-Altstand versioniert, werden aber nicht zur Hauptanwendung ausgebaut.

Fachliche Eingaben erfolgen nicht direkt in fachlichen Tabellen.

Primaeres Eingabe-Pattern sind PySide-Dialoge und PySide-Screens, die freigegebene Adapter, Commands, Services und Repositories nutzen.

VBA-UserForms und worksheet-basierte Dialogseiten sind historische Artefakte der Excel-Linie und werden fuer neue Entwicklung nicht weiterverfolgt.

Vor der technischen Umsetzung eines neuen Eingabedialogs muss ein UX-Prototyp als verbindliche visuelle Referenz erstellt, mit Laura bzw. dem Product Owner reviewed und freigegeben werden.

Der verbindliche Ablauf fuer neue Eingabedialoge lautet:

1. UX-Prototyp erstellen
2. UX-Review mit Laura bzw. Product Owner durchfuehren
3. UX-Freigabe dokumentieren
4. PySide-Dialog oder PySide-Screen moeglichst 1:1 nach dem freigegebenen UX-Prototyp umsetzen
5. Validierung, Adapter-Anbindung und fachliche Logik erst danach ergaenzen

Der UX-Prototyp ist keine technische Implementierung. Er ist die visuelle Referenz fuer den spaeteren PySide-Dialog oder Screen.

Designentscheidungen fuer Eingabedialoge werden im UX-Prototyp getroffen, nicht frei in Legacy-Excel-/VBA-Artefakten.

PySide-Dialoge duerfen:

- Eingaben sammeln
- einfache Pflichtfeld- und Formatpruefungen fuer unmittelbare Benutzerfuehrung durchfuehren
- technische IDs aus Auswahlfeldern uebergeben
- freigegebene Services aufrufen
- nach erfolgreichem Speichern die betroffene Ansicht aktualisieren

PySide-Dialoge duerfen nicht:

- fachliche Logik enthalten
- direkt in fachliche Tabellen oder SQLite schreiben
- Datenmodellentscheidungen treffen
- eigene Schattenhaltung erzeugen
- UI-Positionen als technische Identitaet verwenden

Nach erfolgreichem Speichern wird die Dialogseite verlassen und die aufrufende oder betroffene Ansicht wird aus dem Datenmodell aktualisiert.

## Legacy Runtime Adapter und Export Refresh

Der folgende Excel/VBA-Runtime-Adapter ist ein historischer, nicht weiter verfolgter Pfad der Excel-Linie.

Der damalige freigegebene Pfad lautete:

```text
Worksheet-Dialogseite
-> VBA Adapter
-> Python CLI/Bridge
-> ApplicationCommandDispatcher
-> Command
-> Service
-> Repository
-> SQLite
```

VBA las in diesem Legacy-Pfad Eingaben ausschliesslich ueber registrierte Named Ranges.

VBA enthaelt keine Fachlogik, erzeugt keine fachlichen IDs, validiert keine Fachregeln und schreibt nicht direkt in SQLite.

Nach erfolgreichem Python Command erzeugt Python ein Projection-Refresh-Paket.

VBA darf ausschliesslich diesen Projection Output in registrierte Projektionsbereiche der geoeffneten Arbeitsmappe kopieren.

VBA darf die Projektion nicht selbst berechnen, sortieren oder fachlich interpretieren.

SQLite bleibt fachliche Source of Truth.

Der Projection Builder bleibt Eigentuemer der Projektion.

UI ist immer Projektion und niemals fachliche Datenquelle.

UI darf anzeigen, filtern, sortieren und navigieren.

UI darf fachliche Daten nur ueber definierte Schreibprozesse veraendern.

Darstellungsregeln wie Sortierung, Gruppierung und Filterung gehoeren ausschliesslich zur UI-Projektion.

Sie veraendern niemals die zugrunde liegenden fachlichen Entitaeten.

Die Datenhaltung bleibt unabhaengig von der Darstellung.

Excel-/Workbook-Projektionen sind historisch archiviert. Neue Exportprojektionen brauchen eine eigene fachliche Freigabe und duerfen die PySide-/SQLite-Schichten nicht umgehen.

Excel darf diese Projektion anzeigen und technische Zellbezuege aufloesen, ist aber keine Haupt-UI.

Excel darf die fachliche Reihenfolge der Projektion nicht durch dynamische Sortier- oder Filtermechanismen veraendern.

Hilfstabellen, Formeln, Named Ranges, Shapes und sichtbare Zellen duerfen das Datenmodell nicht umgehen.

Auswertungen duerfen keine eigenen Schatteninformationen erzeugen.

## PySide-Hauptanwendung und Excel-Projektion

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Excel/VBA bleibt unter `legacy/excel/` als historischer Altstand erhalten, ist aber nicht mehr die Zielrichtung fuer die Haupt-App.

Der validierte Spike-Pfad lautet:

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Auch fuer PySide6 gilt:

- keine Businesslogik in der GUI
- keine fachliche ID-Erzeugung in der GUI
- keine direkten SQLite-Schreibzugriffe aus Widgets
- keine Umgehung von Dispatcher, Service, Validator oder Repository

Excel/VBA bleibt im Legacy-Archiv erhalten. Excel ist kein aktiver Standardpfad.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut. Der Ruecksprungpunkt fuer den Excel-/xlwings-Pfad ist `checkpoint-excel-adapter-before-python-gui`.

Offen bleiben produktiver Nutzer-Datenbankpfad, Backup/Restore, Packaging als macOS-App, Updates/Migrationen und spaetere Exportformate.

## Architecture Baseline v3.0

Architecture Baseline v3.0 ist die verbindliche Schichtenbaseline nach der PySide-Architekturentscheidung.

```text
Adapter Layer
-> Application Layer
-> Domain Layer
-> Infrastructure Layer
-> Projection Layer
-> PySide UI / freigegebene Exportprojektion
```

Verantwortlichkeiten:

- Adapter Layer: nimmt Interaktionen entgegen und baut Commands; keine Fachlogik.
- Application Layer: Commands, Dispatcher und Routing; keine Fachlogik, kein SQL, keine Excel-Logik.
- Domain Layer: Services, Validatoren und fachliche Regeln.
- Infrastructure Layer: Repositories, SQLite und Persistenz.
- Projection Layer: PySide ViewModels, UI-nahe Anzeigeprojektionen und explizit freigegebene Export Builder.
- PySide UI: Hauptanwendung fuer Anzeige, Navigation, Dialoge und Benutzerinteraktion.
- Excel UI: historischer Legacy-Altstand unter `legacy/excel/`.

Standard-Datenfluss:

```text
User
-> PySide-Dialog oder freigegebener Adapter
-> Adapter
-> Dispatcher
-> Command
-> Service
-> Repository
-> SQLite
-> ViewModel / Query-Projektion
-> PySide-Ansicht oder freigegebene Exportprojektion
```

SQLite ist die produktive lokale Source of Truth fuer fachliche Daten.

Python ist die einzige fachliche Schreibschicht.

VBA enthaelt keine Businesslogik und schreibt nicht direkt in SQLite.

PySide ist Haupt-UI, aber nicht fachliche Datenquelle.

Excel bleibt historischer Altstand, nicht fachliche Datenquelle.

Neue Funktionen entstehen nach dem Standardablauf:

1. vorhandene Daten ergaenzen
2. Registry kennt die Datenquelle
3. PySide ViewModel oder freigegebene Exportprojektion aktualisieren
4. UI zeigt die Projektion
5. PySide navigiert ueber technische IDs; Export-/Legacy-Projektionen duerfen technische IDs abbilden

Neue Funktionen duerfen nur entstehen durch:

- bestehende Daten erweitern
- registrierte neue Datenquelle ergaenzen
- ViewModel oder freigegebenen Export Builder erweitern
- UI-Projektion ergaenzen
- PySide-Navigation ergaenzen; Legacy-/Export-Navigation nur bei ausdruecklichem Auftrag

Nicht erlaubt sind:

- eigene Schattenlogik
- lokale Zwischendatenhaltung
- doppelte Speicherung derselben Information

## Entity first

Neue Funktionen werden kuenftig nicht zuerst als Maske gedacht, sondern als fachliche Entitaet.

Nicht:

```text
Wir brauchen eine Kompetenzverwaltung.
```

Sondern:

```text
Welche Entitaet entsteht oder wird erweitert? Competency.
```

Die verbindliche Reihenfolge lautet:

```text
Entity
-> Validator
-> Repository
-> Service
-> Application Command Layer
-> Builder
-> UI
-> Navigation
```

Das Schema selbst wird nicht als Python-Klasse implementiert.

Die fachliche Definition einer Entity erfolgt ausschliesslich ueber die Architektur-Dokumentation und die Workbook Data Registry.

Validator pruefen fachliche Eingaben.

Repositories lesen und schreiben Datenquellen.

Services koordinieren fachliche Prozesse.

Der Application Command Layer nimmt technische Commands von Adaptern entgegen und delegiert an Services.

Command Adapter wie CLI oder spaeter VBA duerfen keine Fachlogik enthalten.

Builder erzeugen Projektionen.

UI zeigt Projektionen und ruft keine Repositories direkt auf.

Navigation erfolgt ausschliesslich ueber technische IDs.

## Entity / Storage / Projection

Entity ist das fachliche Objekt, zum Beispiel Student, Group, Course, Competency oder Observation.

Storage ist die physische Ablage im Workbook, zum Beispiel `data_students` mit `tbl_students`.

Projection ist die sichtbare oder auswertbare Darstellung, zum Beispiel Schuelerkarte, Schuelerprofil, Dashboard oder Bericht.

Regeln:

- Entities bleiben stabil.
- Storage kann sich technisch kontrolliert aendern.
- Projections koennen sich gestalterisch aendern.
- Projektionen duerfen keine fachliche Wahrheit speichern.

## Builder-Schicht

Der Builder ist eine eigene Architekturschicht zwischen Daten und Workbook/UI.

```text
Data
-> Builder
-> Workbook/UI
-> VBA-Interaktion
```

Der Builder erzeugt:

- Hidden Data Sheets
- Excel-Tabellen
- Named Ranges
- UI-Projektionen
- vorbereitete Navigationspunkte

Der Builder veraendert keine fachlichen Entitaeten.

Der Builder erzeugt ausschliesslich Workbook-Struktur und Projektionen.

Builder duerfen Projektionen aus mehreren registrierten Datenquellen erzeugen, sofern diese Datenquellen in `docs/DATA_REGISTRY.md`, `docs/VIEW_DATA_OWNERSHIP.md` und `docs/UI_DATA_MAPPING.md` fuer die jeweilige Projektion freigegeben sind.

Fuer Schuelerprojektionen duerfen mindestens gelesen werden:

- `tbl_students`
- `tbl_groups`
- `tbl_courses`

Diese Tabellen werden dabei ausschliesslich gelesen.

Gruppen- oder Kursinformationen duerfen nicht redundant in `tbl_students` uebernommen werden.

Der Builder enthaelt keine spontane Fachlogik ausserhalb der Data Registry.

Fachliche Ableitungen muessen aus registrierten Datenquellen und dokumentierten Regeln entstehen.

## Backlog-relevante Architekturanforderungen

Die Architektur muss folgende spaetere Anforderungen tragen, ohne erneut grundsaetzlich umgebaut zu werden:

- Schuelerverwaltung: anlegen, aendern, archivieren; keine Loeschung; `student_id` bleibt stabil.
- Stammgruppenverwaltung: anlegen, aendern, archivieren; `group_id` bleibt stabil.
- Kursverwaltung: Kurs 1/2/3, Farbe aus `data_courses`; `course_id` bleibt stabil.
- Kursuebersicht: liest Schueler aus mehreren Stammgruppen und zeigt Stammgruppe auf Schuelerkarten.
- Beobachtungserfassung: `observation_id`, Bezug zu `student_id`, Mehrfachbezug zu Kompetenzen.
- Kompetenz-/Lehrplanpflege: `competency_id`, Faecherbezug, Hierarchie, Historisierung offen.
- Dokumente und Medienanhaenge: Dateien werden referenziert, studentenzentriert abgelegt und nicht in Excel eingebettet.
- Automatisch zusammengestellte Vorbereitungsinformationen fuer Lernentwicklungsgespraeche und Berichte bleiben abgeleitete Auswertungsprojektionen. Sie schreiben keine Kompetenz-, Beobachtungs- oder Bewertungsdaten.
- Sprint 7G.1 fuehrt nach Product-Owner- und Datenmodellfreigabe einen eigenen persistenten LEG-Arbeitsentwurf fuer manuelle Vorbereitung, bewusste Referenzauswahl und gemeinsam festgehaltene Inhalte ein. Ein LEG bleibt fachlich von einem Bericht getrennt und ist weder finale Version noch Archiv.
- Dashboards bleiben reine Lese-/Auswertungsschicht. Ein freigegebener Bericht ist langfristig ein versionierter, eingefrorener fachlicher Ausgabestand; die laufende Berichtsvorbereitung bleibt davon getrennt.
- Historisierung: offene Entscheidung vor produktiver Beobachtungserfassung.

## Identitaet

Sichtbare Namen sind niemals technische Identitaeten.

Technische Identitaet erfolgt ausschliesslich ueber IDs.

Namen, Ueberschriften, Zellpositionen, Blattpositionen und sichtbare Texte duerfen nicht als technische Identitaet verwendet werden.

Navigation erfolgt immer ueber technische IDs:

- `student_id`
- `group_id`
- `course_id`
- `competency_id`
- `observation_id`
- weitere registrierte IDs

## Datenhaltung

Es gibt keine doppelte Datenhaltung.

Workbook-Datenquellen werden ausschliesslich in der Workbook Data Registry definiert.

Neue Datenquellen duerfen nicht ohne Erweiterung von `docs/DATA_REGISTRY.md` eingefuehrt werden.

UI-Projektionen duerfen nur aus registrierten Datenquellen entstehen.

Neue Funktionen erweitern vorhandene Daten, statt eigene Dateninseln zu erzeugen.

Keine Funktion erzeugt Schattenlogik.

Erweiterbarkeit ist wichtiger als kurzfristige Implementierung.

Sichtbare Begriffe duerfen sich aendern. Technische Namen bleiben stabil.

## View Ownership

Jede Ansicht besitzt genau definierte Datenquellen.

Eine Ansicht darf nur Datenquellen lesen und schreiben, die in `docs/VIEW_DATA_OWNERSHIP.md` fuer diese Ansicht freigegeben sind.

Neue Ansichten duerfen nicht ohne View Data Ownership umgesetzt werden.

Neue Datenquellen duerfen in einer Ansicht erst verwendet werden, nachdem `docs/VIEW_DATA_OWNERSHIP.md` entsprechend erweitert wurde.

Dashboards und Live-Berichtsvorbereitungen lesen Daten, schreiben aber niemals fachliche Daten. Das spaetere Erstellen, Pruefen, Freigeben oder Korrigieren eines Berichtstands ist ein eigener fachlicher Schreibprozess und braucht vor der Umsetzung Datenmodell-, Lifecycle- und Product-Owner-Freigabe.

## Verbindliche Implementierungsreihenfolge

Eine neue Funktion wird kuenftig in dieser Reihenfolge entwickelt:

1. `docs/PROJECT_CONSTITUTION.md` pruefen
2. `docs/TECHNICAL_NAMES.md` pruefen
3. `docs/DATA_REGISTRY.md` erweitern
4. `docs/DATA_LIFECYCLE.md` ergaenzen
5. `docs/VIEW_DATA_OWNERSHIP.md` ergaenzen
6. `docs/UI_DATA_MAPPING.md` ergaenzen
7. erst danach implementieren

Diese Reihenfolge ist verbindlich.

## Schreibprozesse

Fachliche Daten duerfen nur ueber freigegebene Schreibprozesse veraendert werden.

Kein Schreibprozess darf ohne Eintrag in `docs/DATA_LIFECYCLE.md` umgesetzt werden.

Archivieren ist der Standard fuer fachliche Deaktivierung. Physische Loeschung ist nicht vorgesehen, solange kein eigener fachlicher Entscheid vorliegt.

Schreibprozesse muessen transaktional gedacht werden: Sie erfolgen vollstaendig oder gar nicht.

Keine halben Datensaetze sind erlaubt.

Beispiel Schueler anlegen:

1. `student_id` erzeugt
2. `data_students` geschrieben
3. `group_id` und `course_id` gueltig
4. Projektionen koennen daraus gelesen werden

Wenn ein Schritt fehlschlaegt, darf kein inkonsistenter Zwischenzustand entstehen.

Dateien werden nicht in Excel eingebettet.

Excel speichert fuer Dokumente und Medien ausschliesslich registrierte Referenzen.

Physische Dateien liegen im Dateisystem.

Dokumente gehoeren immer zu einem Schueler.

Beobachtungsanhaenge liegen ebenfalls unter dem Schueler, koennen aber zusaetzlich einen Beobachtungsbezug besitzen.

Beobachtungen duerfen nicht durch eingebettete Dateien oder unkontrollierte Anlagen belastet werden.

## Navigation

Navigation erfolgt immer ueber technische IDs.

Nicht erlaubt ist Navigation ueber:

- Namen
- Zellpositionen
- Blattpositionen
- sichtbare Texte

Ein oeffentlicher VBA-Einstiegspunkt darf keinen impliziten Zustand voraussetzen. Er muss benoetigte Objekte selbst sicher ermitteln oder eine verstaendliche Fehlermeldung ausgeben.

## Technische Namen

Technische Namen muessen in `docs/TECHNICAL_NAMES.md` registriert sein.

Neue technische Namen duerfen nicht kreativ lokal erfunden werden.

Technische Namen sind ASCII-kompatibel, ohne Umlaute und ohne Leerzeichen.

Sichtbare deutsche UI-Begriffe duerfen nicht als technische Schluessel verwendet werden.

Bestehende technische Namen werden nicht ohne eigenen Migrationssprint umbenannt.

## UI

Alle UI-Elemente folgen `docs/DESIGN_SYSTEM.md`.

Neue UI-Felder duerfen erst umgesetzt werden, wenn ihre Datenherkunft in `docs/UI_DATA_MAPPING.md` dokumentiert ist.

Normale Entwicklungssprints veraendern das freigegebene Design nicht.

## Verbotene Umgehungen

Nicht erlaubt sind:

- UI-Tabellen als fachliche Datenquelle
- UI-Zellen als technische Identitaet
- VBA als Ort fuer Fachlogik
- Auswertungen mit eigener Schattenlogik
- neue Datenquellen ohne `DATA_REGISTRY.md`
- neue technische Namen ohne `TECHNICAL_NAMES.md`
- neue Ansichten ohne `VIEW_DATA_OWNERSHIP.md`
- neue UI-Felder ohne `UI_DATA_MAPPING.md`
- Schreibprozesse ohne `DATA_LIFECYCLE.md`
- Navigation ueber Namen statt IDs
- doppelte Datenhaltung fuer dieselbe fachliche Information
- Designaenderungen ohne eigenen UX-Sprint
