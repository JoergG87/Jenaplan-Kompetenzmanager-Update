# Data Registry

## P1-Paket 1 - persistente Ereignisse und kontrolliertes Attachment-Staging

| Datenquelle | Inhalt | Eigentümer / Regel |
|---|---|---|
| SQLite `persistence_events` | monotone technische Ereignisse für Observation-Create/-Edit/-Deaktivierung und Confirmation-Upsert | Append-only Core-Persistenz; keine fachliche Datumsumdeutung |
| `.observation-staging/.writer.lock` | persistente Lockdatei für einen kernelgebundenen FD-Lock | kein Existenz-/PID-Lock; Datei wird nicht gelöscht oder übernommen |
| `.observation-staging/<operation_token>/journal.json` | versionierter Vorher-/Sollzustand, reservierte IDs, Quellen- und Stagingidentität, Phase | außerhalb des Backupinventars; retained bis zu separat freigegebenem GC |
| `.observation-staging/<operation_token>/files/` | exklusiv erzeugte, vollständig gehashte Stagingbytes | keine fachliche Source of Truth; Publikation per exklusivem Hardlink |

```text
persistence_events(
  event_sequence INTEGER PRIMARY KEY,
  operation_token TEXT NOT NULL,
  operation_index INTEGER NOT NULL CHECK(operation_index >= 0),
  operation_payload_hash TEXT NOT NULL,
  event_kind TEXT NOT NULL,
  student_id TEXT NOT NULL,
  competency_id TEXT,
  observation_id TEXT,
  technical_timestamp TEXT NOT NULL,
  ordering_state TEXT NOT NULL,
  UNIQUE(operation_token, operation_index),
  FOREIGN KEY(student_id) REFERENCES students(student_id),
  FOREIGN KEY(observation_id) REFERENCES observations(observation_id)
)
```

Die Cross-Column-Constraints erzwingen: allgemeine Create-/Update-Anker haben
keine `competency_id`, aber eine `observation_id` und `not_applicable`;
kompetenzbezogene Observation-Ereignisse besitzen beide Fach-IDs;
Confirmation-Ereignisse besitzen eine Kompetenz, aber keine Observation.
Ein Foreign Key auf `competencies` ist absichtlich ausgeschlossen, weil
historische Observation-Snapshots auch nach Katalogentfernung auflösbar
bleiben müssen. Außer Primärschlüssel, notwendigem UNIQUE-Constraint, CHECKs
und Foreign Keys wird kein Index eingeführt.

## Security Sprint 12 - interne Build- und Testdaten

| Datenquelle / Rolle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| `requirements-macos-build.txt` | exakt gepinnte macOS-Buildabhängigkeiten einschließlich PyNaCl 1.6.2 und sqlcipher3 0.6.2 | Repository; keine Schlüssel oder Nutzerdaten | Build-Source-of-Truth |
| interner Gate-Off-Buildroot | Venv, PyInstaller-Zwischenstand, Frameworks und generierte Dokumente | ausschließlich freigegebener Build- oder System-Temporärroot; kein Nutzerroot | verwerfbares Buildartefakt |
| 0.3.0-App-Bundle / Build 303 | arm64-Code, Ressourcen, Updatekonfiguration und Lizenztexte | separates technisches Validierungsartefakt für den korrigierten Restore-Neustart; keine Datenbanken, Backups, Container, Schlüssel oder Exceldateien | Nachweis über Build-Inventar und Prüfsummen; keine Übergabe- oder Releasefreigabe |
| Paket-Integrationsroot | synthetische SQLite-Quelle, Safety Copy, SQLCipher-Ziel, Dokument-/Backupcontainer, Journal, Replay-Anker und Restore-Staging | privater doppelt markierter System-Temporärroot | interner Gate-On-Testbestand |
| Paket-Keychain-Root | ausschließlich künstlicher Security Store und DMK-Keysetmetadaten | privater markergebundener System-Temporärroot | interner Keychain-Testbestand |
| macOS-Keychain-Testeintrag | zufälliger 256-Bit-DMK unter dem getrennten DMK-Service und zufälligen Test-IDs | realer lokaler Keychain; am Testende explizit widerrufen und gelöscht | flüchtige Abnahmeevidenz |
| Security-Drittanbieterhinweise | Lizenztexte für PyNaCl, libsodium, sqlcipher3, cryptography und cffi plus Versionshinweis | nur App-Ressource `third_party_licenses` | Distributionshinweis |

Produkt-, Pilot-, Laura-, Excel-, Appcast-, Supportschlüssel- und bestehende
Runtime-Daten sind keine Sprint-12-Testquelle. Der Pakettest darf keinen
normalen `RuntimePaths`-Root akzeptieren.

## Security Sprint 11 - markergebundene Integrationsquellen

| Datenquelle / Rolle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| Integrations-Gate und Test-Root-Marker | exakter Gatewert, feste Markerbytes und private Rootidentität | nur unter System-Temporärwurzel; kein Produkt-`RuntimePaths` | interne Testautorität |
| markierte Klartext-Testinstallation | bestehende V1-Fachdatenbank und ausschließlich künstliche Dokumentquellen | read-only Quellrolle; nie automatisch verändert oder gelöscht | Testquelle |
| `MigrationSafetyCopy` | byte-identische Klartextkopie mit Größe, SHA-256 und SQLite-Integritätsbeleg | exklusiv erzeugt und gefsynct; Retained erst nach Abschluss | Test-Recoveryquelle |
| SQLCipher-Testbestand | vollständig übertragene Fachdaten plus `SecurityIntegrationSchemaV1` | fester Zielpfad, `user_version=1101`, kein Create-Fallback beim Reopen | inaktiver Integrationsbestand |
| `security_document_generations` | technische Generationen, opaque Storage-/Key-IDs, Versionen, Größe/hash, MIME, Lifecycle und Retained-/Quarantänegrund | ausschließlich SQLCipher; aktive Generation per partiellem Unique-Index | Test-Persistenz |
| verschlüsselte Dokumentcontainer | Secretstream-Container mit verschlüsseltem Manifest und zufälligem Document-Key-Envelope | nur opaque Dateinamen im verwalteten Storage; kein Klartext | inaktiver Integrationsbestand |
| `SecurityIntegrationJournalV1` | Crossbinding, Phasen, Dokumentplan, Artefakthashes, Revision und sanitierter Fehlercode | HMAC-authentisiert im Test-Root, atomar und gefsynct | Test-Control-Plane |
| `SecurityIntegrationReplayAnchorV1` | committed/pending Journalrevision und -digest | außerhalb des replaybaren Integrationsroots, aber innerhalb der temporären Testumgebung | Test-Control-Plane |
| verschlüsselter Sprint-11-Backupcontainer | SQLCipher-Testbestand und verifizierte Dokumentcontainer | fester privater Backup-Root; vollständig neu verifiziert | inaktiver Integrationsbestand |
| Restore-Staging | wiederhergestellte SQLCipher-Datei, Dokumentcontainer und Abschlussbeleg | immer neuer Root; keine automatische Live-Umschaltung | Test-Recoverybestand |
| Retained-Beleg | Hashbindung von Klartextquelle und Safety Copy nach vollständigem Abschluss | Marker; keine physische Löschung oder GC | Test-Evidenz |

Originalnamen, Titel, Notizen, fachliche Zuordnungen und MIME-Typen werden
nicht in Dateinamen, Journal, Replay-Anker oder Logs geschrieben. Sie bleiben
in SQLCipher beziehungsweise im verschlüsselten Dokumentmanifest. Produkt-,
Pilot-, RC-, Excel-, Appcast- und reale Nutzerdaten sind keine
Sprint-11-Datenquellen.

## Security Sprint 10 - isolierte synthetische Dokumentquellen

| Datenquelle / Rolle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| injizierter `DocumentContainerContextV1` | stabile Installation-ID, Datenbankkontext-ID, erwartete Dokument-ID/-Generation und technische App-/Formatversion | nur im Aufrufer und verschlüsselten Manifest; stabile Identitäten binden HKDF und Envelope-AAD | isolierte Testquelle |
| synthetischer Sprint-10-Test-Root | private feste Unterbereiche `sources`, `storage` und `exports` plus feste Marker | explizit injiziert; keine RuntimePaths, Produktroots oder frei adressierbaren Ziele | mechanische Testgrenze |
| synthetische Dokumentquelle | künstliche Bytes mit festem Sprint-10-Synthetikmarker | reguläre, einfach verlinkte no-follow-Datei ausschließlich unter `sources`; nie verändert | isolierte Testquelle |
| opaque Storage-Dateiname | zufällige UUIDv4-Storage-ID, Envelope-Revision und `.jkmedoc` | keine Dokument-, Schüler-, Fach-, Kurs- oder Originalnamen | bewusst sichtbar |
| öffentlicher Dokumentheader v1 | Magic, Format-/Header-/Framing-/Algorithmusversion, Chunkgröße, zufällige Container-/Document-Key-ID, Key-Generation, Secretstream-Header und integriertes Envelope samt DMK-ID/-Generation und Revision | kanonisch; Payload-Binding und Envelope-AAD sind getrennt, aber auf dieselben technischen Identitäten gebunden | bewusst sichtbar |
| verschlüsseltes Dokumentmanifest v1 | Dokument-ID/-Generation, Storage-ID, Document-Key-ID/-Generation, Installation-/Datenbankkontext, Originalname, MIME-Typ, Größe, Klartext-SHA-256, Chunkanzahl, Erstellungszeit und technische App-/Formatversion | erster authentisierter Secretstream-Record | ausschließlich verschlüsselt |
| verschlüsselte Dokumentrecords | genau die synthetischen Quelldaten in fester Chunkreihenfolge | Secretstream-Records mit eigener Dokument-AAD-Domain, Ordinal, Chunkindex und erwarteter Größe | ausschließlich verschlüsselt |
| versteckte Container-Retained-Datei | vollständig gefsyncter und kryptografisch verifizierter Container vor Veröffentlichung | bleibt als Retained-Evidenz; sichtbares Ziel entsteht per No-Clobber-Hardlink | isolierte Publikationsevidenz |
| bewusster synthetischer Export | vollständig verifizierter Klartext nur unter dem markergebundenen `exports`-Root | exklusiv, no-follow, nie automatisch geöffnet; atomarer No-Clobber-Rename ist der Commitpunkt, normale Fehler leeren den Inhalt nur über den offenen eigenen FD, harter Abbruch davor kann nur eine versteckte nicht erfolgreiche Retained-Datei hinterlassen | isolierter Prototyp |
| Storage-Inventar/GC-Plan | read-only Klassifikation bekannter Container als `ACTIVE`, `PREPARED`, `RETAINED`, `QUARANTINED` oder explizit `GC_ELIGIBLE` | Dry-Run; unbekannte oder ungebundene Dateien werden niemals automatisch gelöscht | isolierter Prototyp |

Produktive `documents`-Tabelle, heutige Klartextpfade, Produkt-Dokumentroot,
Backup-/Restore-Inventar, PDF-Artefakte, `security.sqlite`, RuntimePaths,
Pilot-, RC-, Release- und Excel-Artefakte sind keine Sprint-10-Datenquellen.


## Security Sprint 9 - isolierte synthetische Backupquellen

| Datenquelle / Rolle | Inhalt | Grenze |
|---|---|---|
| `BackupContainerContextV1` | stabile Installations- und Datenbankkontext-IDs | nur injizierter Testkontext; Bindung in HKDF und Envelope-AAD |
| synthetischer Test-Root | Marker, SQLCipher-Testquelle und künstliche Dokumente | privat, eigentümergeprüft, keine RuntimePaths oder Produktdaten |
| Containerheader und Key-Envelope | Format-/Algorithmuswerte, Key-ID, DMK-Generation und geschützter Backup-Key | technisch sichtbar, keine Schülerdaten oder Klartextschlüssel |
| verschlüsseltes Manifest und Eintragsrecords | Metadaten sowie SQLCipher-/Dokumentbytes | nur authentifizierter Secretstream-Recordstrom |
| Retained-Container und Restore-Root | Publikations- beziehungsweise Abschlussbeleg | ausschließlich synthetischer Prototyp, kein Produkt-Backup |

## Security Sprint 7B - Kontrollprojektionen ohne neue Produktdatenquelle

| Datenbestand / Projektion | Owner | Zweck | Persistenz |
|---|---|---|---|
| Locktransition-Einträge | Security Infrastructure | HMAC-authentisierte append-only Lockevidenz | Je Transition eine unveränderliche kanonische Datei im injizierten Security-Root |
| `MigrationCrossbindingContext` | Security Domain | Bindung von Installation, Migration, Schlüsseln, Security-Artefakten, Dateirollen und Versionen | Unveränderlicher In-Memory-Wert |
| Authentisierte Preflight-Projektionen | Security Domain / Adapter | Read-only Evidenz für Anchor, Registry, Journal, Lock und Artefakte | Unveränderliche In-Memory-Werte |
| `MigrationPreflightDecision` | Security Domain | Abgeleiteter Modus oder sanitisiertes Blockierungsergebnis | Keine Persistenz |

Es entsteht keine neue fachliche Datenquelle, Produktprojektion oder
Runtime-Pfad.

## Security Sprint 6 - isolierter Replay-Anker und Migrations-Lock

| Datenquelle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| macOS Keychain Service `de.jenaplan.kompetenzmanager.monotonic-security-anchor` | strikt versionierter Anchor-Zustand mit Installation/Security-Context, monotoner Revision, Database-Context, DMK-/Keyset-ID/-Generation sowie committed und optional pending Registry-/Journal-Snapshot; jeder Snapshot bindet High-Water-Mark, Journal-/Migrationsgeneration und exakte SHA-256-Digests der authentisierten Dateien | eigener nicht synchronisierender Keychain-Namespace; kein Datei-Fallback, kein Schlüsselmaterial, keine fachlichen IDs oder Inhalte | isolierte macOS-Foundation implementiert und getestet; keine Startup- oder Produktadressierung |
| `InMemoryMonotonicSecurityAnchorStore` | derselbe technische Anchor-Vertrag einschließlich atomarem Compare-and-Advance | ausschließlich Prozessspeicher in Tests; Neustart wird durch explizit injizierten Testzustand simuliert | Testquelle/Fake, keine Produktpersistenz |
| `database-migration-v1.lock` | Installation, Database-Context, Migration-ID, PID, Prozessstartidentität, Lock-Nonce, Erstellungs-/Aktualisierungszeit und SHA-256 der Rootbindung | exklusiv und atomar ausschließlich im injizierten synthetischen Test-Root; reguläre Datei, restriktive Rechte und geprüfte Dateiidentität | isolierter POSIX/macOS-Prototyp implementiert und getestet; kein RuntimePath |
| Sprint-6-Recovery-Testartefakte | guarded synthetische Quelle, verifiziertes Backup, separates SQLCipher-Ziel, authentisiertes Journal, geschützte Envelope-Registry und technische Fehlersimulationsreste | pro Test in neuem temporärem Root; ausschließlich bekannte Rollen und identitätsgebundene eigene Dateien | Testquellen/-artefakte, keine Produktdaten |

Bei authentisiertem `COMPLETED` mit
`synthetic_prototype_completed` darf der isolierte Recovery-Prototyp nur das
exakt evidence-gebundene Testziel und Backup per atomarem No-Clobber-Rename in
`.recovery-<role>-<migration_id>.quarantine` verschieben und dort erneut
identitätsgebunden verifizieren. Diese Quarantänebestände werden nicht durch
Recovery gelöscht. Quelle, Keychain-Anchor, Envelope-Registry, Journal, Lock
und unbekannte Dateien bleiben als Audit- beziehungsweise Blockierbeleg
erhalten.

Im Anker und Lock verboten sind DMK, Database-Key, Wrapping-/HMAC-Key,
Passwort, Auth-Recovery-Code, Gerätecredential, Support-Secret, Schülerdaten,
Dokumentinhalte, Klartext-SQL und frei übernommene externe Pfade. Ein fehlender
Anker bei bereits vorhandenem Registry-/Journalbestand ist kein leerer
Erstzustand, sondern ein blockierender Sicherheitsbefund.

`pending` ist keine zweite Source of Truth. Es bindet ausschließlich den alten
committed Snapshot und einen exakt geplanten neuen Snapshot für das
Cross-Store-Protokoll. Nach Dateipublikation darf nur der beobachtete exakt
pending Registry-/Journal-Digest committen. Nach Crash kann exakt der alte
Dateistand über eine monotone Abort-Transition oder exakt der neue Dateistand
über Commit aufgelöst werden; unbekannte oder gemischte Digests blockieren.
Die implementierte Portoperation `abort_pending(expected, observed_committed)`
behält den committed Registry-/Journal-Snapshot bei, entfernt ausschließlich
pending und übernimmt dessen höhere Anchor-Revision als monotonen
Abbruchnachweis.

## Security Sprint 5 - isolierte technische Sidecars

| Datenquelle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| `database-key-envelopes-v1.json` | Registry-Version, stabile Database-Context-UUID, monotoner Generations-High-Water-Mark, bereits AEAD-geschützte Envelopes und HMAC-SHA-256-Tag über die gesamte kanonische Registry | atomar im explizit injizierten synthetischen Test-Root; weder fachliche SQLite noch `security.sqlite`, Keychain oder Produkt-Runtime | implementierte Foundation, nicht produktiv adressiert |
| `database-migration-journal-v1.json` | Migration-/Database-Key-/DMK-Bindungs-IDs, Phasenhistorie, sichere relative Rollenpfade, Dateibeweise, Prüf- und sanitierte Fehlercodes, HMAC-Tag | atomar im selben isolierten Test-Root; getrennt von Envelope und Keyset-Metadaten | implementierte Foundation, nicht produktiv adressiert |
| Laufzeit-Database-Key | UUID, Generation und 32 zufällige Secret-Bytes | nur flüchtig; Secret ausschließlich als AES-GCM-Ciphertext im Envelope | implementiertes Testmittel |
| Laufzeit-Database-Wrapping-Key | 32 per HKDF-SHA-256 aus dem DMK abgeleitete Bytes | nur flüchtig; nicht in Registry, Journal, SQLite, Keychain, Log oder Report | implementiertes Testmittel |
| Laufzeit-Registry-HMAC-Key | 32 per eigener HKDF-Domain und Database-Context abgeleitete Bytes | nur flüchtig; authentifiziert Steuerdaten und Envelope-Mitgliedschaft | implementiertes Testmittel |
| Laufzeit-Journal-Key | 32 per getrennter HKDF-Domain abgeleitete Bytes | nur flüchtig; nur zur HMAC-SHA-256-Prüfung | implementiertes Testmittel |

Im Journal und in öffentlichen Envelope-Metadaten verboten sind DMK,
Database-Key, Wrapping-/Journal-Key, App-Passwort, Recovery-/Support-Secrets,
Schülerdaten, Dokumentinhalte und Klartext-SQL. Envelope-Ciphertext und
AEAD-/HMAC-Tags sind öffentlich speicherbar, enthalten aber kein
Klartextschlüsselmaterial. Beide Dateiquellen bleiben außerhalb aller
produktiven Pfadauflösungen.

## Security Sprint 4 - Quellen des isolierten Migrationsprototyps

| Datenquelle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| `synthetic-source.sqlite` | ausschließlich deterministische synthetische Schüler, Kurse, Kompetenzen, Beobachtungen, Berichte, Dokumentverweise und Binäranhänge | pro Lauf im temporären Prototyp-Root; dreifach durch Guard/Application-ID/User-Version markiert | implementierte Testquelle |
| `*-verified-backup.sqlite` | vollständiger SQLite-Backup-Snapshot derselben Fixture | separates Ziel im Prototyp-Root; Integrität und vollständiger Snapshotvergleich vor Export | implementiertes Testartefakt |
| `*-encrypted.sqlcipher` | vollständiges SQLCipher-Ziel derselben Fixture | separates Ziel im Prototyp-Root; wird bei Fehlern identitätsgebunden verworfen | implementiertes Testartefakt |
| Laufzeit-Database-Key | 32 zufällige Bytes | nur flüchtig; kein DMK, App-Passwort, Sidecar, Log, Report oder Repositoryinhalt | Testmittel |
| `MigrationReport` | Counts, Bool-Prüfungen, Schema-/Datenhash, Größen und Zeitdauern | nur Rückgabewert/optionale Konsolenausgabe; keine Pfade oder Secrets | technisches Testprotokoll |

Der Prototyp liest keine registrierte Produkt-, Pilot-, Security-, Dokument-,
Backup- oder Releasequelle. Die Guard ist eine zusätzliche Stopbedingung und
keine Berechtigung, beliebige gleichnamige Dateien zu migrieren. Der spätere
gewrappte Database-Key und seine Metadaten sind noch keine Datenquelle.

## Security Sprint 3 - Temporäre SQLCipher-Testquelle

| Datenquelle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| temporäre SQLCipher-Testdatenbank | ausschließlich synthetische Smoke-/Testzeilen | nur in pro Lauf neu erzeugtem temporärem Verzeichnis; nach Schließen entfernt; kein RuntimePath | implementierter Infrastrukturtest, nicht produktiv |
| Laufzeit-Testschlüssel | 32 zufällige Bytes aus `secrets.token_bytes` | ausschließlich flüchtig im Test-/Smoke-Prozess; weder Repository noch Datei, Log, Snapshot oder Sidecar | Testmittel, kein Produkt-Key |
| `sqlcipher3` 0.6.2 | DB-API-Binding mit statisch eingebetteter SQLCipher Community 4.12.0 im geprüften Wheel | optionale Entwicklungs-/Testabhängigkeit; nicht im RC und nicht im produktiven Startup importiert | isolierter Spike; Supply-Chain- und Produktbuild-Gate offen |

Die bestehende fachliche SQLite-Datenquelle und ihr Verhalten bleiben
unverändert; ihre normale Connection-Erzeugung delegiert nun an den expliziten
Standard-SQLite-Provider. SQLCipher ist dort nicht konfiguriert. Security
Sprint 3 registriert keine neue fachliche Datenquelle und speichert weder DMK
noch DB-Key-Metadaten.

## Security Sprint 2 - Isolierte Key-Foundation-Datenquellen

| Datenquelle | Inhalt | Persistenz / Grenze | Status |
|---|---|---|---|
| Development-Keyset-Sidecar `data-keysets.sqlite` | ausschließlich Key-ID, Generation, Status und SHA-256-Fingerprint | neuer isolierter Test-/Entwicklungsstore; nicht `security.sqlite`, nicht RuntimePaths, keine Migration | implementierte Foundation, nicht produktiv aktiviert |
| macOS Keychain Service `de.jenaplan.kompetenzmanager.data-master-key` | exakt 32 geheime DMK-Bytes je Installations-/Key-ID-Bindung | nicht synchronisierender Plattformstore hinter `DataMasterKeyStore` | macOS-Adapter implementiert, keine Startup-Aktivierung |
| `KeyEnvelope` | Version, Key-ID, Zweck, Algorithmus, technische Metadaten, bereits geschütztes Material | in diesem Sprint nicht persistiert | Format implementiert |
| Windows DPAPI / Credential Manager | zukünftige plattformgeschützte DMK-Ablage | nur Portvertrag, keine Datenquelle und keine Implementierung | offen |

In Security- und Keyset-SQLite-Stores unzulässig sind DMK, geschütztes
Envelope-Material sowie Schüler-, Dokument-, Berichts-, LEG- und Backupdaten.
Passwörter werden dort niemals im Klartext gespeichert. Der
bestehende Pilot-Security-Store und alle Pilotdaten werden weder geöffnet noch
verändert. Der Sidecar ist eine bewusste Entwicklungsisolation und keine
Entscheidung über eine spätere produktive Store-Topologie.

Der Development-Keyset-Sidecar ist noch nicht kryptografisch authentifiziert
oder rollbackgeschützt. Eine Metadatenabweichung blockiert den Lifecycle, darf
aber keinen möglicherweise korrekten Plattform-DMK automatisch löschen.
Authentisierung und monotoner Produktanker bleiben Aktivierungsgates.

## Sprint 0.2S.1 - Datenquellen des Support-Assistenten

| Quelle | Inhalt | Owner | Ausschlüsse |
|---|---|---|---|
| bewusst gewählte `.jkmresetrequest` | unveränderte kanonische technische Anfragebytes | betroffene Installation / `SupportResetTokenCodec` | keine automatische Suche, keine Schüler-, Dokument- oder Backupdaten |
| `PRODUCT_SUPPORT_KEY_REGISTRY` | ausschließlich öffentliche freigegebene Key-Metadaten | geprüfter App-Release | kein privater Schlüssel, keine Passphrase, kein Token |
| `SUPPORT_ASSISTANT_PRODUCT_KEY` | im getrennten Bundle eingebettete, strikt gleiche öffentliche Projektion des aktiven `support-2026-b` | Support-Packaging; Gleichheit zur Produktregistry wird getestet | kein privater Schlüssel, keine Passphrase, kein weiterer oder Testschlüssel |
| bewusst gewählte verschlüsselte PKCS#8-Datei | externer Ed25519-Privatschlüssel nur für den aktuellen Prozess | Support-Verantwortlicher | nie Paket, Repository, Audit oder Runtime-Datenquelle |
| `~/Library/Application Support/Jenaplan Support-Assistent/audit.jsonl` | UTC-Zeitpunkt, vollständige Request-ID, Key-ID und feste Aktion | `SupportAssistantAuditLog` | kein Token, Passwort, Passphrase, Private-Key-Inhalt, Nonce, Installationsname, Benutzername, Schüler- oder Fachdaten |
| separates Support-Assistent-Paket | App-Bundle, Betriebsanleitung, Version und Prüfsummen | Support-Packaging | keine Produkt-App, Datenbank, Dokumente, Backups, Runtime-Daten, Requests, Tokens, privaten Schlüssel oder Passphrase |

Installationsname und lesbare Anfragecode-Referenz sind ausschließlich
flüchtiger UI-State. Ein Benutzername ist im unveränderten Requestformat 1
nicht enthalten und wird nicht aus Konto-, OS- oder Fachdaten nachgeladen.

## Sprint 0.2U.2 - Öffentliche Pilot-Updatequellen

| Quelle | Inhalt | Owner | Ausschlüsse |
|---|---|---|---|
| `packaging/pilot_appcast_url.txt` | feste HTTPS-URL des Pilot-Appcasts | Release-Betrieb | keine Zugangsdaten, lokale Pfade oder Nutzerwahl |
| `packaging/sparkle_pilot_public_key.txt` | öffentlicher Sparkle-EdDSA-Schlüssel | Update-Vertrauensanker im App-Bundle | kein privater Update- oder Supportschlüssel |
| GitHub Pages `pilot/appcast.xml` | signierter Feed mit Version, Release-Hinweisen und Release-Asset-URL | Pilot-Release | keine Fach-, Konto-, Installations- oder Telemetriedaten |
| GitHub Release | EdDSA-signiertes ZIP des geschlossenen App-Bundles | Pilot-Release | kein DMG, Testdatenbackup, Pilotpaket, Secret oder Runtime-Bestand |

Der spätere Pfad `stable` bleibt ohne Appcast und damit deaktiviert. Private
Sparkle-Schlüssel verbleiben extern im macOS-Schlüsselbund des
Release-Verantwortlichen und sind strikt vom Support-Reset-Schlüssel getrennt.

## Sprint 0.2B.6 - Externe Support-Betriebsquellen

| Quelle | Inhalt | Owner | Ausschlüsse |
|---|---|---|---|
| `PRODUCT_SUPPORT_KEY_REGISTRY` | Formatversion 1; ab `0.2.2` ausschließlich `support-2026-b`, Ed25519-Public-Key, Status `active`, Aktivierung `2026-07-19T22:12:15Z`, technische Obergrenze und bestätigter SHA-256-Fingerprint | geprüfter App-Release | kein privater Schlüssel, keine Passphrase, Anfrage oder Token |
| externe öffentliche Schlüsselbeschreibung | `key_id`, Algorithmus, Public-Key, Erstellungszeit, vorgesehener Status und Fingerprint | Support-Verantwortlicher | darf getrennt zur Registry-Prüfung weitergegeben werden |
| externer verschlüsselter PKCS#8-Schlüssel | ausschließlich privater Ed25519-Schlüssel, verschlüsselt und Dateirechte `600` in Verzeichnis `700` | Support-Verantwortlicher | niemals App, Repository, Build, DMG, Pilot-/Laura- oder Supportpaket |
| separates Supportpaket | Finder-Starter, arm64-Laufzeiten, Anleitung, Strukturbeispiel, Version und Prüfsummen | Support-Packaging | keine App, DMG, Fachdatenbank, Backups, Schülerdaten, Secrets, Testkeys, Anfragen oder Tokens |

Der interaktive Supportprozess hält Anfrage, Passphrase, Private-Key-Objekt und
Token ausschließlich so kurz wie für Prüfung und Ausgabe nötig im Prozess. Nur
die bewusst gewählte `.jkmresettoken`-Datei wird mit Rechten `600` geschrieben;
es gibt keine automatische Suche, Ablage, Netzwerkquelle oder Protokollierung.

Der öffentliche Registry-Fingerprint von `support-2026-b` lautet
`76e619df93483de9313d5bf592fc852c88f1ba7ac5261018801c0fcd5e96be77`.
Registry-Format 1 verlangt `not_after`; `9999-12-31T23:59:59Z` bedeutet hier
kein bewusst terminiertes Ablaufdatum. Rotation oder Widerruf bleiben jederzeit
per geprüftem App-Release möglich.

## Historischer Sprint 0.2R - Release-Ausgaben

DMG, kanonisch gebaute PDFs, Release-Hinweise, Prüfsummen, Release-Inventar,
Laura-Testmappe, die beiden Pilot-ZIPs und das synthetische Laura-Testdatenbackup
sind unveränderliche Build-/Übergabeartefakte,
aber keine produktiven Datenquellen. Der Modus `release` enthält ausschließlich
nicht geheime Build-Info und niemals fachliche SQLite, Security Store,
AppPreferences, Enrollment-Marker, Backups, Recovery-Codes, Reset-Anfragen oder
Tokens, Schlüsselbundwerte, private oder Testschlüssel.

Beide Pilotpakete enthalten keine App zusätzlich zum identischen leeren DMG,
keinen Sourcecode, keine Tests oder Fixtures und keine Screenshots. Nur die
Laura-Testdatenvariante enthält zusätzlich
`Laura-Testdaten-0.2.1.jkmbackup`: das bereits an Laura ausgegebene, mit dem offiziellen Backup-Service aus
dem deterministischen Acht-Monats-Seed abgeleitete Sicherung mit ausschließlich
synthetischen Fachdaten. Sie enthält keinen Security Store, keine Kontodaten,
Passwörter, Recovery-Codes, Gerätecredentials, Support-Tokens oder Schlüssel.
Das Updateartefakt `0.2.2` enthält keine `.jkmbackup`; die produktive
Public-Key-Registry enthält ausschließlich `support-2026-b`. Die bestehende Testmappe bleibt
die einzige kanonische Ergebniserfassung; reale Ergebnisse werden nicht durch
den Build erzeugt oder überschrieben.

## Sprint 0.2B.5 - Support-Reset-UI-Datenquellen

| Quelle | Inhalt | Owner | Persistenz-/Datenschutzgrenze |
|---|---|---|---|
| bestehende `security.sqlite.support_reset_requests` | technische Installation, Nutzer, Anfrage-ID, Nonce, Aktion, Status und UTC-Zeiten | `SQLiteSecurityRepository` | kein Fachbezug; weiterhin Security Store v3 |
| bestehende `security.sqlite.support_reset_token_uses` | ausschließlich Token-Digest, `key_id`, Aktion, Status und Zeiten | `SQLiteSecurityRepository` | kein vollständiger Token |
| `.jkmresetrequest` | kanonische versionierte Anfragebytes | bewusster Nutzerexport | keine automatische Datei, keine Fach- oder Authgeheimnisse |
| `.jkmresettoken` | optionaler äußerer Tokenaustausch | externer Supportprozess / temporäre UI-Eingabe | nie AppPreferences, Security Store, Backup oder Log |
| `DEFAULT_SUPPORT_KEY_REGISTRY` | ausschließlich freigegebene öffentliche Ed25519-Schlüssel | paketierter Produktcode | ab `0.2.2` genau `support-2026-b`; kein Test-/Privatschlüssel |

Der Reset erzeugt ein bestehendes fachliches `.jkmbackup`; Format und Ausschlüsse
bleiben unverändert. Anfrageexport und Token sind keine Cloud-, Telemetrie- oder
fachlichen Datenquellen. Private Schlüssel und organisatorische Auditdaten wie
Supportbearbeiter bleiben vollständig außerhalb der App.

## Sprint 0.2B.4a - Gerätecredential-Datenquellen

| Datenquelle | Inhalt | Kanonischer Owner | Backup/Restore |
|---|---|---|---|
| `security.sqlite.device_credentials` | `credential_id`, Installation, Nutzer, technisches Label, individueller Salt, SHA-256-Verifikationswert, Formatversion, Epoch, Status und UTC-Zeitpunkte | `SQLiteSecurityRepository` über `DeviceCredentialRepository` | Nie Bestandteil von `.jkmbackup`; fachliches Restore verändert sie nicht |
| macOS-Schlüsselbund, Service `de.jenaplan.kompetenzmanager.device-credential` | Ausschließlich 32 zufällige Secret-Bytes, Account namespaced mit Installation und Credential-ID, nicht synchronisierender generischer Passwortdatensatz mit ACL für die erzeugende codesignierte Anwendung | `MacOSKeychainSecretStore` | Nie exportiert, gesichert, diagnostiziert oder wiederhergestellt |

`app-preferences.json`, fachliche SQLite, Dokumentordner, Exporte, Logs,
Screenshots und Diagnosepakete dürfen weder Secret, Salt, Hash,
`credential_id` noch Security-Epoch enthalten. Die Keychain-Quelle ist keine
Cloudquelle und speichert niemals das App-Passwort. Hardware-Seriennummern und
Fingerprints sind keine Datenquelle.

Dieses Dokument definiert die verbindlichen Datenquellen des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Source of Truth. Workbook-Tabellen sind historische Legacy-Projektionen unter `legacy/excel/`.

## Separater Security Store v2

Sprint 0.2B.4 behaelt Security-Schema v2 und alle vorhandenen Tabellen,
fachlichen Daten, IDs, Dokumentpfade sowie Backup-/Restore-Formate unveraendert.
Die produktive Startintegration fuehrt keine fachliche Migration ein.

Zusaetzliche rein technische Runtime-Quelle:

| Quelle | Owner | Inhalt | Ausschluesse |
| --- | --- | --- | --- |
| `<runtime-root>/app-preferences.json` | `AppPreferencesFile` | Formatversion 3, genau eines der Inaktivitaetsintervalle 5/10/15/30/60 Minuten, optionaler lokaler `display_name`, lokaler Onboarding-Status `not_started`/`in_progress`/`completed`/`dismissed`, aktueller Onboarding-Schritt, `onboarding_format_version` und boolesches `touch_id_preferred` | kein Authentifizierungskonto, keine IDs, Tokens, Passwoerter, Recovery-Codes, Hashes, Salts, Security-Epoch, Rollen, Schul-/E-Mail-/OS-Namen oder fachlichen Daten; ausgeschlossen aus `.jkmbackup`, Restore, Export, Security-Logs und Support-Reset |

`display_name` ist ein allgemeiner lokaler App-Profilwert und keine
Security-Identitaet. Er ist `null` oder ein nach Entfernen aeusserer Leerzeichen
hoechstens 80 Zeichen langer Unicode-Klartext. Interner Inhalt bleibt
unveraendert; HTML/Rich Text wird nicht interpretiert. Der Wert liegt weder in
`security.sqlite` noch in `kompetenzmanager.sqlite` und besitzt keine Kopplung
an `user_id`, Recovery, Passwort, Rolle oder Schuelerdaten.

Der Onboarding-Status ist eine lokale Bedienpraeferenz, keine fachliche
Einrichtung und keine Konto-Eigenschaft. `in_progress` speichert nur den
aktuellen Schritt. `completed` und `dismissed` verhindern automatische
Wiederoeffnung; manuelles Oeffnen aus den Einstellungen ist weiterhin moeglich.
Unbekannte neuere Preference-/Onboarding-Versionen werden konservativ gelesen,
ohne daraus fachliche Daten zu erzeugen.

`InMemorySession` ist ausdruecklich keine persistente Datenquelle. `user_id`,
`installation_id` und `security_epoch` existieren nur im Prozessspeicher und
werden beim App-Ende verworfen. Keychain, Geraete-Token und persistente
Sitzungsdaten entstehen nicht.

`<runtime-root>/security/security.sqlite` ist eine rein technische lokale
Security-Quelle und ausdruecklich keine fachliche Source of Truth. Sie liegt
ausserhalb von `documents/`, verwendet eine von `kompetenzmanager.sqlite`
unabhaengige Schema-/Formatversion und besitzt keine fachlichen Fremdschluessel.
Die fachliche `DATABASE_COMPATIBILITY_VERSION = 1` und das Backupformat v1
bleiben unveraendert.

Security-Schema v2 erweitert den vollstaendig erhaltenen v1-Bestand additiv.
Eine einzelne transaktionale Migration uebernimmt Accounts, Argon2id-Hashes,
Recovery-Codes, Markerbindung und Zeitpunkte unveraendert. Unbekannte neuere
Versionen werden fail-closed abgelehnt.

Tabellen des Security-Schemas v2:

| Tabelle | Primary Key | Foreign Keys / Eindeutigkeit | Inhalt |
| --- | --- | --- | --- |
| `security_metadata` | Singleton `metadata_id = 1` | keine | Schema-/Formatversion und technische Zeitpunkte |
| `installations` | `installation_id` | `marker_reference` eindeutig | zufaellige UUIDv4, nicht geheime Markerbindung, Status und Zeitpunkte |
| `local_accounts` | `user_id` | `installation_id -> installations`, genau ein Konto je Installation | Argon2id-PHC-String, Hashformatversion, Kontostatus, Login- und getrennte Recovery-Drosselung, Zeitpunkte |
| `recovery_code_sets` | `recovery_set_id` | `user_id -> local_accounts`; hoechstens ein aktiver und ein vorbereiteter Satz je Nutzer | zweiphasiger Satzstatus und Zeitpunkte |
| `recovery_codes` | `recovery_code_id` | `recovery_set_id -> recovery_code_sets`; Hash je Satz eindeutig | individueller Salt, SHA-256-Hash, Formatversion, benutzt/widerrufen und Zeitpunkte |
| `support_reset_requests` | `reset_request_id` | `user_id -> local_accounts`, `installation_id -> installations`; hoechstens eine aktive Anfrage | rein technische Bindung aus Installation, Nutzer, Nonce, Aktion, Status und Zeitpunkten; maximal 24 Stunden |
| `support_reset_token_uses` | `token_digest` | `reset_request_id -> support_reset_requests` | ausschliesslich SHA-256-Digest, `key_id`, Aktion, Status sowie Erzeugungs-, Ablauf- und Verbrauchszeitpunkt; kein vollstaendiges Token |
| `security_epochs` | `user_id` | `installation_id` eindeutig; beide an Account/Installation gebunden | monotone Generation und technischer Aenderungszeitpunkt fuer spaetere Widerrufsvertraege |

Unzulaessig sind E-Mail-Adresse, Schulname, Betriebssystem-Benutzername,
Klarname, Rolle, Passwort-Hinweis, Sicherheitsfrage sowie jeder Bezug auf
Schueler-, Beobachtungs-, Berichts-, LEG- oder Dokument-IDs. Klartextpasswoerter
und Klartext-Recovery-Codes sind keine Datenquelle und werden nie persistiert.
Vollstaendige Support-Reset-Tokens, private Schluessel und Passphrasen sind
ebenfalls keine Datenquelle. Oeffentliche Ed25519-Schluessel liegen
ausschliesslich in der paketierten Code-Registry; Rotation und Widerruf
erfordern ein App-Update und erzeugen keine Netzwerkquelle.

`<runtime-root>/security/enrollment.marker` ist ein streng versionierter,
nicht geheimer technischer Nachweis. Er enthaelt ausschliesslich Formatversion
und zufaellige Markerreferenz, ist kein kryptografischer Integritaetsnachweis
und keine zweite Authentifizierungsquelle.

Explizit ausgeschlossen aus `.jkmbackup`, Restore-Staging, Restore-Journal,
Restore-Recovery, Exporten und Diagnose-Allowlists sind das gesamte
`security/`-Verzeichnis, `security.sqlite`, alle SQLite-Sidecars und
`enrollment.marker`. Fachlicher Restore darf diese Quellen weder ersetzen noch
loeschen oder materialisieren.

Ebenso ausgeschlossen bleibt `<runtime-root>/app-preferences.json`, weil
allgemeine lokale App-Einstellungen nicht zum fachlichen Backupinventar
gehoeren. Der bestehende Backup- und Restore-Vertrag wird nicht erweitert.

## Sprint 0.2A.4 - Sichtbare allgemeine Betriebsprojektion

Die Datensicherungs-Unterseite liest ausschliesslich explizit gewaehlte `.jkmbackup`-Dateien und vollstaendig verifizierte Archive im bestehenden Runtime-Standardordner `backups/`. Die Quellen werden nur durch vorhandene Backup-/Restore-Services geprueft; Namen, IDs, Texte, Originaldateinamen und Pfade gelangen nicht in die UI-Projektion. Es entsteht keine persistente UI-Historie und keine neue Datenquelle.

UI-Ansichten sind Projektionen dieser Datenquellen. Sie duerfen selbst keine fachliche Datenquelle werden.

## Schreib- und Leseprinzip

Python schreibt fachliche Daten ausschliesslich ueber Application, Domain, Repository und SQLite.

PySide-Adapter und ViewModels lesen fachliche Daten ueber freigegebene Adapter, Repositories oder Query-Schichten.

Schuelerliste und Dashboard-Heatmap duerfen dieselben registrierten SQLite-
Quellen innerhalb eines Refreshs ueber
`SQLiteStudentDocumentationProjectionRepository` gebuendelt lesen. Der Batch
ist eine kurzlebige Projektion, keine Datenquelle und kein Cache. Er umfasst
nur aktive Schueler im angeforderten Gruppen-/Kursscope, aktive Beobachtungen,
deren Kompetenz-Snapshots, Bestaetigungen, Persistenzereignisse, den
Kompetenzkatalog, die Dokumentationsfachauswahl sowie aktive Gruppen und Kurse.
Die Abfragen laufen in einem gemeinsamen read-only Snapshot und fuehren keine
Schema- oder Stammdateninitialisierung aus.

Export-Builder duerfen nur nach ausdruecklicher Freigabe Projektionen aus SQLite erzeugen. Der alte Workbook-Builder ist archiviert.

VBA greift niemals direkt auf fachliche Tabellen oder SQLite zu.

VBA schreibt keine fachlichen Daten. Neue VBA-Schreibprozesse werden nicht mehr verfolgt.

Jede Datenquelle braucht einen registrierten Primary Key.

Alle Foreign Keys muessen in diesem Dokument explizit dokumentiert sein.

## Produktiver Benutzerpfad und SQLite-Datenbasis

SQLite ist die produktive lokale Datenbasis.

Installiertes macOS-Pilotpaket:

```text
~/Library/Application Support/Jenaplan-Kompetenzmanager/
├── kompetenzmanager.sqlite
├── documents/
├── exports/
├── backups/
└── logs/
```

Der Pfad liegt bewusst ausserhalb der `.app`. App-Austausch, Update und Loeschen der `.app` ersetzen oder loeschen keine Benutzerdaten. `JENAPLAN_APP_DATA_DIR` ist nur ein technischer Override fuer isolierte automatisierte Pakettests und keine zweite fachliche Datenquelle. Beim Modus `--packaged-smoke-test` genuegt dieser Override allein nicht: Zusaetzlich muss `JENAPLAN_PACKAGED_SMOKE_MARKER=isolated-v1` gesetzt sein und die Datenwurzel nachweislich unter einem eigens erzeugten temporaeren Smoke-Verzeichnis liegen. Die Pruefung erfolgt vor jeder Runtime-Initialisierung.

### Verifiziertes Anwendungsbackup v1

Ein `.jkmbackup` ist eine abgeleitete technische Sicherung und keine neue fachliche Source of Truth. Das ZIP enthaelt genau einen mit Pythons SQLite Backup API erzeugten und geprueften Datenbanksnapshot, ein kanonisches manifestiertes Inventar und die registrierten verwalteten Dateien.

Enthaltene Quellen:

- SQLite-Snapshot der produktiven `kompetenzmanager.sqlite` unter `database/kompetenzmanager.sqlite`
- alle registrierten `documents.file_path` innerhalb `RuntimePaths.documents`, unabhaengig von `documents.active`
- alle registrierten finalen Dateien aus `learning_report_pdf_artifacts.relative_file_path`
- alle registrierten finalen Dateien aus `learning_conference_pdf_artifacts.relative_file_path`

Nur zusammengefasst, nicht kopiert:

- registrierte `documents.file_path` ausserhalb `RuntimePaths.documents`; das Manifest speichert ausschliesslich `count`, `missing_count`, `included = false` und einen neutralen Hinweis

Ausgeschlossen:

- `exports/`, `logs/` und `backups/`
- frei gewaehlte Entwurfs-PDFs sowie freie Text- und Markdown-Exporte
- unregistrierte externe Dateien
- Originaldateinamen und absolute oder externe Pfade

Unregistrierte Nutzdateien unter `documents/` sind kein stiller Zusatzbestand und blockieren das Backup; `.DS_Store` wird ignoriert. Das Manifest ist eine technische Integritaetsprojektion und enthaelt keine personenbezogenen Klartexte. `sqlite_user_version`, `compatibility_version` und der strukturelle Schema-Fingerprint dokumentieren den Datenbankstand; der Fingerprint beruecksichtigt bei expliziten Indizes die normalisierte Definition samt Partial-Index-Praedikat. Diese Werte geben noch keine Restore-Kompatibilitaet frei.

Ab Sprint 0.2A.3a wird `compatibility_version = 1` beim Erstellen nicht mehr aus einer ungeprueften Konstante behauptet. Der read-only inspizierte Snapshot muss entweder exaktes Datenbankschema V1 mit `sqlite_user_version = 1` oder der registrierte bekannte unversionierte `c029aff`-Vorgaenger mit `sqlite_user_version = 0` sein. Unbekannte oder neuere Schemata blockieren die Backup-Erstellung. Der bestehende strukturelle Backup-Fingerprint und das Manifestformat v1 bleiben unveraendert.

### Datenbank-Kompatibilitaetsidentitaet V1

`PRAGMA user_version` ist SQLite-Metadatum und keine neue fachliche Datenquelle. Die registrierte V1-Identitaet besteht aus `DATABASE_COMPATIBILITY_VERSION = 1`, `sqlite_user_version` und einem vollstaendigen SHA-256-Kompatibilitaetsfingerprint ueber kanonisches JSON der nicht-internen Schemastruktur. Die App-Version ist kein Bestandteil dieser Identitaet.

Der vollstaendige Fingerprint bindet Tabellenname, normalisiertes Tabellen-SQL, Spaltenmetadaten, Primaer- und Fremdschluessel, explizite Indizes samt Partial-Praedikat, Trigger und Views. Damit sind auch `CHECK`-Constraints und Defaultwerte gebunden. Ausgeschlossen sind Dateninhalte, `sqlite_%`-Objekte, interne Indexnamen, Autoincrement-Zaehler und fluechtige SQLite-Werte.

Eine schemafreie neue Datenbank wird transaktional als V1 erzeugt. Eine vorhandene unversionierte Datenbank wird beim normalen Start nicht veraendert oder adoptiert. Nur der registrierte vollstaendige Fingerprint des bekannten unversionierten `c029aff`-Vorgaengers ist ein V1-Migrationskandidat; unbekannte Schemata sind keine registrierte Quelle und werden abgelehnt.

### Technische Restore-Vorschau ohne View

Die `RestorePreview` ist eine kurzlebige technische Projektion aus einem isoliert verifizierten Backup. Sie speichert nichts und enthaelt nur Erstellungszeit, App-, Backupformat-, Datenbank-Kompatibilitaets- und SQLite-Version, Kompatibilitaetsstatus sowie aggregierte Counts fuer Schueler, Beobachtungen, Berichtrevisionen, LEG-Revisionen, Managed Files und externe beziehungsweise fehlende externe Referenzen. Namen, Notizen, fachliche Texte, Dateinamen, absolute oder externe Pfade und Schueler-IDs sind ausgeschlossen.

### Persistentes Restore-Staging und Sicherheitsbackup

`restore-staging/<restore-id>/` ist eine abgeleitete technische Arbeitsablage innerhalb der Runtime-Datenwurzel und keine fachliche Source of Truth. `source/` enthaelt ausschliesslich die an Archivgroesse und SHA-256 gebunden extrahierten Backupbytes. `prepared/` enthaelt eine kontrollierte V1-Datenbankkopie und ausschliesslich verifizierte Managed Files. `staging-state.json` speichert nur technische Identitaet, Versionen, Phase, aggregierte Counts und Zeitpunkte; fachliche Inhalte, Namen, Originalpfade und externe Pfade sind ausgeschlossen.

Die vorbereitete Datenbank darf ausschliesslich aus exaktem V1 oder dem registrierten unversionierten V0-Vorgaenger entstehen. Eine V0-V1-Migration aendert nur SQLite-`user_version` und nur in `prepared/`. Managed Documents werden ueber `documents.document_id` aus dem Manifest zugeordnet und unter einem technischen Zielpfad materialisiert. Ihre `documents.file_path`-Werte werden nur in der vorbereiteten Datenbank auf die aktuelle Runtime-Documents-Wurzel rebased. Nicht im Manifest enthaltene externe Dokumentreferenzen bleiben unveraendert. `learning_report_pdf_artifacts.relative_file_path` und `learning_conference_pdf_artifacts.relative_file_path` bleiben runtime-relativ und unveraendert; ihre Bytes, Groessen und Hashes werden erneut geprueft.

`backups/restore-safety/<restore-id>/` enthaelt ein unveraendertes `.jkmbackup` der bestehenden Formatversion, das vor einem spaeteren Live-Austausch mit dem vorhandenen `BackupService` aus dem Live-Bestand erzeugt und vollstaendig verifiziert wird. Es ist eine technische Sicherung, keine neue Datenquelle. Restore-Staging, Sicherheitsbackup, produktive Datenbank und produktive `documents/` bleiben getrennte Pfadbereiche.

### Produktive Restore-Transaktion

Technische, nicht fachliche Runtime-Quellen:

| Quelle | Owner | Inhalt | Regel |
| --- | --- | --- | --- |
| `instance.lock` | Restore-Lock-Service | PID, Prozessstart-Identitaet, UTC-Zeit und Runtime-Root-Hash | keine fachlichen Daten; niemals nur wegen alter PID entfernen |
| `restore-handoffs/<restore-id>.json` | `CreateRestoreHandoffCommand` | Handoff-Version, Restore-ID, Nonce, kanonische Runtime-Wurzel, Archivgroesse/-hash, Staging-State-Hash, Prepared-DB-Groesse/-hash und UTC-Erstellungszeit | Modus `0600`, einmalige atomare Konsumierung, keine frei waehlbaren Zielpfade |
| `restore-transactions/<restore-id>/current-state.json` | Restore-Journal | kanonischer technischer Gesamtzustand, naechster Schritt, Hash-/Groessenbeweise, Rename-Intents, Teilzustaende, Fehlerklasse und Handshake | atomar ersetzt und vor kritischen Renames gefsynct |
| `restore-transactions/<restore-id>/events.jsonl` | Restore-Journal | append-only technische Zustandsereignisse | jede Zeile kanonisches JSON; Datei und Elternverzeichnis werden gefsynct |
| `restore-transactions/<restore-id>/source-backup.jkmbackup` | Restore-Handoff-Service | stabile Kopie der bereits verifizierten Archivbytes | Worker leitet den Pfad selbst ab; Groesse und SHA-256 muessen zur Handoff-Datei passen |
| `restore-transactions/<restore-id>/rollback/` | Restore-Executor | alter DB-, WAL-, SHM- und Documents-Zustand | nie automatisch loeschen; bis bestaetigtem Abschluss erhalten |
| `restore-transactions/<restore-id>/failed-new/` | Restore-Rollback | nach Fehler zurueckgenommener neuer Bestand | bei Fehler und manueller Recovery erhalten |
| `restore-transactions/<restore-id>/resume-token.json` | Restore-Executor | Restore-ID, zufaelliges Token, Erstellungs- und Ablaufzeit | Modus `0600`, einmalig, keine fachlichen Daten |

Diese Quellen enthalten keine Datenbankinhalte, Namen, Notizen, fachlichen Texte oder frei injizierten fachlichen Pfade. Sie sind technische Beweise und Steuerdaten; SQLite und `documents/` bleiben die fachliche Source of Truth.

Die kurzlebigen Prozesskanaele fuer `worker_started` und das Ende der
Haupt-App sind ausschliesslich geerbte Kernel-Deskriptoren. Sie werden nicht
persistiert und sind keine neue Datenquelle. `current-state.json` bleibt die
persistente Wahrheit: `handoff_created` bestaetigt nur die vollstaendig
geschriebene Uebergabedatei, `worker_started` erst die authentisierte
Lock-Uebernahme. Ein Startfehler wird vor jeder Live-Mutation als
`aborted_before_replacement` abgeschlossen.

Entwicklerpfad:

```text
data/kompetenzmanager.sqlite
```

Der Entwicklerstart behaelt damit die bestehende Projektkonvention. Die Datei wird nie in ein Pilotpaket uebernommen.

Statische Bundle-Ressourcen sind keine veraenderlichen Benutzerdaten:

- `data/curriculum_catalog_v1.csv` als eingebettete Kataloggrundlage;
- `assets/app_icon.png` und `assets/icons/*.svg` als eingebettete UI-Ressourcen;
- optional `pilot_initial/` nur fuer die explizit fiktive Buildvariante `laura`;
- `pilot_build_info.json` zur technischen Kennzeichnung des konkreten Pakets.

Die Variante `laura` wird ausschliesslich aus `scripts/seed_test_data.py`
erzeugt. Sie enthaelt 24 fiktive Kinder, Stammdaten, Stundenplan,
Beobachtungen, Dokumentplatzhalter, Bericht-/LEG-Drafts, je eine zweistufige
Revisionshistorie und finale Beispiel-PDFs. Die Variante `empty` bleibt fuer den
technischen Smoke-Test ohne Schueler und Dokumente. Beide Varianten verwenden
dieselben registrierten SQLite-Tabellen; es entsteht keine neue Datenquelle.

Gepruefte Tabellen:

| SQLite-Tabelle | Entity | Bisherige Workbook-Projektion |
| --- | --- | --- |
| `students` | Student | `data_students` / `tbl_students` |
| `groups` | Group | `data_groups` / `tbl_groups` |
| `courses` | Course | `data_courses` / `tbl_courses` |
| `course_groups` | CourseGroup | keine Workbook-Projektion |
| `course_group_student_groups` | CourseGroupStudentGroup | keine Workbook-Projektion |
| `course_group_courses` | CourseGroupCourse | keine Workbook-Projektion |
| `competencies` | Competency | `data_competencies` / `tbl_competencies` |
| `observations` | Observation | `data_observations` / `tbl_observations` |
| `observation_competency_ratings` | ObservationCompetencyRating | `data_observation_competencies` / `tbl_observation_competencies` |
| `student_competency_confirmations` | StudentCompetencyConfirmation | keine Workbook-Projektion |
| `documents` | Document / Media | `data_media` / `tbl_media` |
| `documentation_subject_settings` | DocumentationSubjectSetting | keine Workbook-Projektion |
| `timetable_entries` | TimetableEntry | keine Workbook-Projektion |
| `learning_conference_drafts` | LearningConferenceDraft | keine Workbook-Projektion |
| `learning_conference_draft_subjects` | LearningConferenceDraftSubject | keine Workbook-Projektion |
| `learning_conference_draft_cross_topics` | LearningConferenceDraftCrossTopic | keine Workbook-Projektion |
| `learning_conference_draft_competencies` | LearningConferenceDraftCompetency | keine Workbook-Projektion |
| `learning_conference_draft_observations` | LearningConferenceDraftObservation | keine Workbook-Projektion |
| `learning_conference_draft_charts` | LearningConferenceDraftChart | keine Workbook-Projektion |
| `learning_reports` | LearningReport | keine Workbook-Projektion |
| `learning_report_revisions` | LearningReportRevision | keine Workbook-Projektion |
| `learning_report_pdf_artifacts` | LearningReportPdfArtifact | keine Workbook-Projektion |
| `learning_conferences` | LearningConference | keine Workbook-Projektion |
| `learning_conference_revisions` | LearningConferenceRevision | keine Workbook-Projektion |
| `learning_conference_pdf_artifacts` | LearningConferencePdfArtifact | keine Workbook-Projektion |

Regel:

SQLite ist die fachliche Source of Truth. Es darf keine parallele fachliche Source of Truth neben SQLite geben. `data_*`-Sheets und `tbl_*`-Tabellen sind Excel-/Workbook-Projektionen aus SQLite oder historische Legacy-Artefakte.

Produktive PySide-Datenbanken initialisieren `students` leer. Stammdaten-Defaults fuer `groups`, `courses` und Kursverbuende duerfen angelegt werden, Demo-Schueler jedoch nur ueber explizite Seed-/Testpfade.

VBA schreibt nicht direkt in SQLite.

Python bleibt fachliche Schreibschicht.

PySide-Dialoge verwenden fuer produktive Schreibprozesse freigegebene Adapter, Commands, Services und Repositories.

Beobachtungen werden nicht hart geloescht. `observations.active = 0` blendet eine Beobachtung aus aktiven Profil- und Kompetenzuebersichten aus; die zugehoerigen `observation_competency_ratings` bleiben historisch erhalten.

Der Kompetenzkatalog wird aus `data/curriculum_catalog_v1.csv` idempotent in SQLite `competencies` importiert. `grade_band` bleibt Quellenkontext, `learning_stage` speichert die produktbezogene Filterstufe, `catalog_status` speichert den Katalogstatus, `catalog_default_active` speichert den Katalogstandard und `activation_group_key` bereitet optional aktivierbare Bereiche vor. `competencies.active` bleibt die lokale Aktivierung und darf bei bestehenden `competency_id`s durch den Katalogimport nicht ueberschrieben werden.

VBA-UserForms und worksheet-basierte Dialogseiten sind historische Artefakte der Excel-Linie und kein Zielpfad fuer neue Features.

Feature 1.4a gab historisch fuer `student.create` den Runtime Adapter und den Projection Refresh Contract frei. Dieser Pfad liegt inzwischen unter `legacy/excel/` und ist kein aktiver Standardpfad.

Fuer diesen Schreibprozess ist SQLite die fachliche Source of Truth.

`data_*`-Sheets und `tbl_*`-Tabellen in der geoeffneten Arbeitsmappe sind danach Projection Output aus SQLite und duerfen nur ueber Python-erzeugte Projection-Refresh-Pakete aktualisiert werden.

Minimales Spike-Schema:

```text
students(
  student_id TEXT PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  group_id TEXT NOT NULL,
  course_id TEXT NOT NULL,
  student_notes TEXT,
  active INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_at TEXT
)

groups(
  group_id TEXT PRIMARY KEY,
  group_name TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL
)

courses(
  course_id TEXT PRIMARY KEY,
  course_name TEXT NOT NULL,
  color_key TEXT,
  color_name TEXT NOT NULL,
  color_hex TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL
)

course_groups(
  course_group_id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL
)

course_group_student_groups(
  course_group_id TEXT NOT NULL,
  student_group_id TEXT NOT NULL,
  PRIMARY KEY(course_group_id, student_group_id),
  FOREIGN KEY(course_group_id) REFERENCES course_groups(course_group_id),
  FOREIGN KEY(student_group_id) REFERENCES groups(group_id)
)

course_group_courses(
  course_group_id TEXT NOT NULL,
  course_id TEXT NOT NULL,
  PRIMARY KEY(course_group_id, course_id),
  FOREIGN KEY(course_group_id) REFERENCES course_groups(course_group_id),
  FOREIGN KEY(course_id) REFERENCES courses(course_id)
)

competencies(
  competency_id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  subject_name TEXT NOT NULL,
  subject_full_name TEXT NOT NULL DEFAULT '',
  official_subject_name TEXT NOT NULL DEFAULT '',
  school_context_name TEXT NOT NULL DEFAULT '',
  grade_band TEXT NOT NULL DEFAULT '',
  label TEXT NOT NULL,
  description TEXT NOT NULL,
  learning_stage TEXT NOT NULL DEFAULT 'cross_stage',
  learning_area TEXT NOT NULL,
  competency_group TEXT,
  source_reference TEXT NOT NULL DEFAULT '',
  catalog_status TEXT NOT NULL DEFAULT 'current',
  activation_group_key TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL,
  catalog_default_active INTEGER NOT NULL DEFAULT 1,
  is_core_subject INTEGER NOT NULL
)

observations(
  observation_id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL,
  date TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  context TEXT,
  note TEXT,
  active INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(student_id) REFERENCES students(student_id)
)

observation_competency_ratings(
  observation_id TEXT NOT NULL,
  competency_id TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  subject_display_name TEXT NOT NULL,
  learning_area TEXT NOT NULL,
  competency_group TEXT,
  competency_text TEXT NOT NULL,
  rating TEXT NOT NULL,
  PRIMARY KEY(observation_id, competency_id),
  FOREIGN KEY(observation_id) REFERENCES observations(observation_id)
)

student_competency_confirmations(
  student_id TEXT NOT NULL,
  competency_id TEXT NOT NULL,
  confirmed_rating TEXT NOT NULL,
  confirmed_at TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(student_id, competency_id),
  FOREIGN KEY(student_id) REFERENCES students(student_id),
  FOREIGN KEY(competency_id) REFERENCES competencies(competency_id)
)

documentation_subject_settings(
  subject_id TEXT PRIMARY KEY,
  active INTEGER NOT NULL CHECK (active IN (0, 1)),
  updated_at TEXT NOT NULL
)

timetable_entries(
  timetable_entry_id TEXT PRIMARY KEY,
  weekday INTEGER NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  room TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT NOT NULL DEFAULT ''
)
```

## Sprint-3A-Mapping Kompetenzstruktur

Sprint 3A klaert die fachliche Sprache, ohne neue Datenquelle, neue Spalte oder Schema-Migration einzufuehren.

Sichtbare Struktur:

```text
Fach -> Kompetenzbereich -> Thema -> Kompetenz
```

Mapping auf bestehende Datenfelder:

| Sichtbarer Begriff | SQLite / Katalogfeld | Bemerkung |
| --- | --- | --- |
| Fach | `subject_id`, `subject_name`, Katalog `subject_key`, `subject_display_name` | Fachschluessel und sichtbarer Fachname |
| Kompetenzbereich | `learning_area` | bisher teilweise als Lernbereich bezeichnet; ab Sprint 3 fachlich als Kompetenzbereich zu verstehen |
| Thema | `competency_group` | fachliche Untergliederung innerhalb eines Kompetenzbereichs |
| Kompetenz | `competencies.description`, `observation_competency_ratings.competency_text`, Katalog `competency_text` | konkrete beobachtbare Kompetenz |
| Kurzlabel fuer kompakte UI | `competencies.label`, Katalog `competency_label` | kurze Anzeige, keine eigene fachliche Ebene; Sprint 3B fuehrt `competency_label` als optionale CSV-Spalte ein |

Bewertungen:

- `observations` enthaelt keine globale Bewertung.
- `observation_competency_ratings.rating` speichert die Bewertung fuer genau eine Kombination aus `observation_id` und `competency_id`.
- Eine Beobachtung kann mehrere Kompetenzbewertungen enthalten.
- Unterschiedliche Kompetenzen innerhalb derselben Beobachtung duerfen unterschiedliche Bewertungen tragen.
- `offen` ist kein gespeicherter Ratingwert. Wenn eine Kompetenz nicht bewertet werden soll, wird keine Zeile in `observation_competency_ratings` gespeichert.

Bestandsdaten:

- Alte grobe Kompetenzen bleiben ueber ihre `competency_id` historisch lesbar.
- Bestehende `observation_competency_ratings` bleiben gueltig.
- Alte Beobachtungen werden nicht automatisch auf spaetere konkrete Kompetenzen migriert.
- Neue konkrete Kompetenzen werden spaeter fuer neue Beobachtungen ergaenzt.
- Alte grobe Kompetenzen duerfen spaeter deaktiviert oder archiviert werden, aber nicht geloescht werden.
- Sprint 3 braucht fuer Bewertung pro Kompetenz keine Rating-Schema-Migration.

## Legacy: Physische Workbook-/Export-Projektion

Die `data_*`-Quellen konnten in der Excel-Linie als versteckte Tabellenblaetter in Workbooks angelegt werden. Der zugehoerige Code liegt unter `legacy/excel/` und ist kein aktiver Standardpfad.

Jedes `data_*`-Blatt enthaelt genau eine strukturierte Tabelle mit `tbl_*`-Namen.

Der archivierte Builder erzeugte diese Tabellen automatisch.

Historische UI-Builder lasen ausschliesslich aus registrierten Tabellen und erzeugten daraus UI-Projektionen.

Eine Projektion darf mehrere registrierte Tabellen lesen, wenn die fachliche Herkunft in `docs/UI_DATA_MAPPING.md` dokumentiert und die View Ownership freigegeben ist.

Fuer Schuelerprojektionen sind mindestens `tbl_students`, `tbl_groups` und `tbl_courses` als lesende Quellen zulaessig.

Der Builder veraendert keine fachlichen Entitaeten und erzeugt keine doppelte Datenhaltung.

VBA nutzt IDs und benannte Bereiche, aber keine direkten Zugriffe auf fachliche Tabellen.

Worksheet-basierte Dialogseiten sind historische UI-Projektionen und temporaere Eingabeflaechen aus der Excel-Linie.

Sie sind keine fachlichen Datenquellen, erzeugen keine Schattenhaltung und duerfen fachliche Daten erst ueber freigegebene Schreibprozesse veraendern.

VBA darf keine fachlichen Daten in `data_*`-Tabellen schreiben.

VBA darf nur Projection Output importieren, der zuvor durch Python aus SQLite erzeugt wurde.

Registrierte Zuordnung:

| Hidden Sheet | Tabelle |
| --- | --- |
| `data_students` | `tbl_students` |
| `data_groups` | `tbl_groups` |
| `data_courses` | `tbl_courses` |
| `data_subjects` | `tbl_subjects` |
| `data_competencies` | `tbl_competencies` |
| `data_observations` | `tbl_observations` |
| `data_observation_competencies` | `tbl_observation_competencies` |
| `data_media` | `tbl_media` |
| `data_settings` | `tbl_settings` |

## Curriculum-Katalog v1

Zweck: Read-only-Katalog fuer Fachauswahl und Kompetenzauswahl im PySide6-Beobachtungsdialog.

Die fachbezogene Schnellauswahl `Zuletzt verwendet` ist keine eigene Datenquelle: Sie ist eine fluechtige `StudentDesktopAdapter`-Projektion aus aktiven SQLite-`observations` mit deren `observation_competency_ratings`, auf vorhandene aktive `current`-Zeilen aus `competencies` begrenzt. Sie speichert weder Historie noch Auswahlzustand.

Datei: `data/curriculum_catalog_v1.csv`

Status: v1-Kataloggrundlage mit abgeschlossenem Sprint-4-Lehrplanabgleich fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz. Die konkreten Kompetenzen folgen den freigegebenen Lehrplan-Mappings, der Katalog-Konsolidierung und den Product-Owner-Entscheidungen. Religion bleibt ausserhalb dieses Sprint-4-Katalogabgleichs.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Wichtige Felder:

- `competency_id`
- `subject_key`
- `subject_display_name`
- `subject_full_name`
- `official_subject_name`
- `school_context_name`
- `grade_band`
- `learning_stage`
- `learning_area`
- `competency_group`
- `competency_text`
- `competency_label`
- `source_reference`
- `catalog_status`
- `catalog_default_active`
- `activation_group_key`
- `is_core_subject`
- `is_active`

Regeln:

- Der Katalog wird nur lesend verwendet.
- `competency_id` ist eine stabile Katalog-ID im Format `CMP-######`.
- Neue konkrete Kompetenzen werden mit neuen global fortlaufenden IDs ergaenzt; bestehende IDs werden nicht fachlich umgedeutet oder wiederverwendet.
- `competency_label` befuellt beim Import das bestehende SQLite-Feld `competencies.label`; es ist keine neue SQLite-Spalte.
- Der SQLite-Katalogimport ist idempotent: neue CSV-IDs werden in bestehende lokale Datenbanken eingefuegt, vorhandene lokale Nicht-CSV-Kompetenzen bleiben erhalten und `competencies.active` vorhandener IDs wird nicht ungefragt aus dem CSV ueberschrieben.
- Vor fachlichen CSV-Aenderungen pruefen die internen Werkzeuge `scripts/validate_curriculum_catalog.py`, `scripts/compare_curriculum_catalog.py` und `scripts/next_competency_ids.py` Header, Pflichtfelder, Wertebereiche, ID-Stabilitaet, stille Text-/Hierarchieveraenderungen und die naechsten freien globalen IDs.
- `catalog_status = current` ist Standard. `catalog_status = legacy` dient ausschliesslich historischen Kompetenzen und macht diese nicht automatisch zu neuen Dokumentationszielen.
- `catalog_default_active = false` bedeutet, dass neue optionale Kompetenzen beim Erstimport standardmaessig deaktiviert werden.
- Alte grobe Kompetenzen bleiben historisch lesbar. Sie duerfen spaeter deaktiviert oder archiviert, aber nicht geloescht werden.
- Bestehende `observation_competency_ratings` bleiben gueltig und werden nicht automatisch auf neue konkrete Kompetenzen migriert.
- Er erzeugt selbst keine Beobachtung; der PySide-Adapter uebergibt die Katalog-IDs an `observation_competency_ratings`.
- `EPU` ist der App-Anzeigename fuer `Epochaler Projektunterricht`.
- Die offizielle Lehrplanquelle fuer `EPU` ist `Heimat- und Sachkunde`.
- `Sachunterricht` wird nicht als App-Fach gefuehrt.
- `Kunst` wird als App-Fach angezeigt; offizielle Quelle ist `Kunsterziehung`.
- `Ethik`, `Religion`, `Werken` und `Schulgarten` sind als erweiterte Faecher enthalten.

## documentation_subject_settings

Zweck: Auswahl der Faecher, die fuer spaetere Dokumentations- und Auswertungslogik als dokumentationsrelevant gelten.

Entity: DocumentationSubjectSetting.

Storage: SQLite `documentation_subject_settings`.

Projection: PySide6 Einstellungen und Dokumentations-/Auswertungsprojektionen.

Owner: Systemeinstellungen / Dokumentationskonfiguration.

Primary Key: `subject_id`.

Foreign Keys:

- keine, weil `competencies.subject_id` im Kompetenzkatalog mehrfach vorkommt

Wichtige Felder:

- `subject_id`
- `active`
- `updated_at`

Beziehungen:

- `subject_id` verweist fachlich auf die Fachschluessel im aktiven Kompetenzkatalog, speichert aber keine Fachdefinition und keine sichtbaren Fachnamen.

Schreibende Prozesse:

- Dokumentationsrelevante Faecher speichern

Lesende Prozesse:

- Dokumentations- und Auswertungsprojektionen
- PySide6 Einstellungen

Regeln:

- Wenn keine Zeilen vorhanden sind, gelten alle aktiven Katalogfaecher aus `competencies.active = 1` als dokumentationsrelevant.
- Wenn Zeilen vorhanden sind, gilt die gespeicherte Auswahl.
- Die Tabelle veraendert den Kompetenzkatalog nicht.
- `competencies.active` darf nicht fuer diese Dokumentationsauswahl missbraucht werden.
- Sichtbare Fachnamen werden weiterhin aus `competencies` bzw. dem Katalog abgeleitet.
- Nicht dokumentationsrelevante Faecher bleiben in Beobachtungslisten, Kompetenzhistorien und bestaetigten Kompetenzstaenden sichtbar, zaehlen aber nicht als offen im Dokumentationsstand oder in offenen Beobachtungsanlaessen.

## timetable_entries

Zweck: Persistenter Wochenstundenplan fuer Montag bis Freitag.

Entity: TimetableEntry.

Storage: SQLite `timetable_entries`.

Projection: PySide6 Einstellungen sowie kanonische Leseprojektion fuer aktuelle, naechste und heutige Stunden.

Owner: Stundenplankonfiguration.

Primary Key: `timetable_entry_id` im Format `TTE-######`.

Fachliche Referenzen:

- `subject_id` muss als bestehender Fachschluessel in SQLite `competencies` vorkommen; ein sichtbarer Fachname wird nicht gespeichert.
- `target_type = group` referenziert mit `target_id` genau SQLite `groups.group_id`.
- `target_type = course` referenziert mit `target_id` genau SQLite `courses.course_id`.
- `target_type = course_group` referenziert mit `target_id` genau SQLite `course_groups.course_group_id`.

Wichtige Felder:

- `weekday` als ISO-Wochentag 1 bis 5
- `start_time` und `end_time` als `HH:MM`
- `room` als optionaler Anzeigeort
- `active` fuer bewusste Aktivierung oder Deaktivierung
- `sort_order` fuer stabile Reihenfolge bei sonst gleichen Anzeigeattributen
- `created_at` und `updated_at` als technische Zeitstempel
- `deleted_at` fuer kontrolliertes Entfernen ohne Wiederverwendung der ID

Regeln:

- Beginn liegt strikt vor Ende; ein Eintrag kann daher nicht ueber Mitternacht reichen.
- Aktive Eintraege duerfen sich zeitlich nicht ueberschneiden.
- Inaktive Eintraege werden weder als aktuell noch als naechste Stunde projiziert.
- Die Leseprojektion erhaelt einen expliziten Zeitpunkt und liest hoechstens bis zum folgenden Wochenumlauf.
- Das Ende ist exklusiv: bei `end_time` ist die Stunde nicht mehr aktuell.
- Es werden keine Fach-, Stammgruppen-, Kurs- oder Kursverbundnamen kopiert.
- Loeschen blendet den Eintrag ueber `deleted_at` aus; die technische ID wird nicht wiederverwendet.

## data_students

Zweck: Stammdaten der Schueler.

Entity: Student.

Storage: `data_students` / `tbl_students`.

Projection: Schuelerkarten, Schuelerprofil, Auswahllisten, Berichtskopf.

Owner: Schuelerverwaltung.

Primary Key: `student_id`.

Foreign Keys:

- `group_id` -> `data_groups.group_id`
- `course_id` -> `data_courses.course_id`

Wichtige Felder:

- `student_id`
- `first_name`
- `last_name`
- `group_id`
- `course_id`
- `student_notes`
- `active`
- `created_at`
- `updated_at`
- `archived_at`

Pflichtfelder:

- `first_name`
- `last_name`
- `group_id`
- `course_id`

Optionale Felder:

- `student_notes`
- `archived_at`

Beziehungen:

- viele Schueler gehoeren zu einer Stammgruppe
- viele Schueler gehoeren zu einem Kurs
- ein Schueler kann viele Beobachtungen besitzen

Schreibende Prozesse:

- Schueler anlegen
- Schueler bearbeiten
- Schueler archivieren
- Python-Datenimport

Lesende Prozesse:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Beobachtungsdialog
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Schuelerkarten in Stammgruppenuebersicht
- Schuelerkarten in Kursuebersicht
- Kopfbereich im Schuelerprofil
- Schuelerauswahl im Beobachtungsdialog
- Berichtskopf

Erweiterungsregeln:

- keine fachlichen Schuelerdaten in UI-Projektionen speichern
- `display_name` ist eine UI-Projektion, kein gespeichertes Feld
- Archivierung setzt `active = FALSE` und `archived_at`
- keine physische Loeschung ohne eigenen Architekturentscheid
- produktiver App-Start erzeugt keine Demo-Schueler; explizite Seed-Daten dienen Tests, Legacy-Projektionen oder Demo-Szenarien

## data_groups

Zweck: Stammgruppen als organisatorische Zugehoerigkeit.

Entity: Group.

Storage: `data_groups` / `tbl_groups`.

Projection: Stammgruppenueberschrift, Stammgruppenanzeige, Gruppenauswahl.

Owner: Stammgruppenverwaltung.

Primary Key: `group_id`.

Foreign Keys:

- keine

Wichtige Felder:

- `group_id`
- `group_name`
- `sort_order`
- `active`

Beziehungen:

- eine Stammgruppe besitzt viele Schueler
- eine Stammgruppe kann in mehreren Kursverbuenden enthalten sein

Schreibende Prozesse:

- Stammgruppe anlegen
- Stammgruppe bearbeiten
- Stammgruppe archivieren
- Python-Datenimport

Lesende Prozesse:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Erlaubte UI-Projektionen:

- Ueberschrift der Stammgruppenuebersicht
- Stammgruppenanzeige in der Kursuebersicht
- Stammgruppenanzeige im Schuelerprofil

Erweiterungsregeln:

- neue Stammgruppen entstehen ueber Stammgruppenverwaltung
- keine automatische Stammgruppenanlage beim Anlegen eines Schuelers
- Archivierung statt physischer Loeschung

## data_courses

Zweck: Kurse als Jahrgangszuordnung.

Entity: Course.

Storage: `data_courses` / `tbl_courses`.

Projection: Kursanzeige, Kursuebersicht, Kartenfarbe.

Owner: Kursverwaltung.

Primary Key: `course_id`.

Foreign Keys:

- keine

Wichtige Felder:

- `course_id`
- `course_name`
- `color_key`
- `color_name`
- `color_hex`
- `sort_order`
- `active`

Beziehungen:

- ein Kurs besitzt viele Schueler
- ein Kurs kann in mehreren Kursverbuenden enthalten sein

Schreibende Prozesse:

- Kurs anlegen
- Kurs bearbeiten
- Kurs archivieren
- Python-Datenimport

Lesende Prozesse:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Erlaubte UI-Projektionen:

- Kursanzeige auf Schuelerkarten der Stammgruppenuebersicht
- Kartenfarbe aus Kurszuordnung
- Kursuebersicht
- Kursanzeige im Schuelerprofil

Erweiterungsregeln:

- Farben sind fachliche UI-Metadaten des Kurses
- Kartenfarben duerfen nicht manuell pro Schueler vergeben werden
- Archivierung statt physischer Loeschung

## course_groups

Zweck: Fachlicher Scope fuer kursverbundbezogene Mathe-/Deutsch-Kurse.

Entity: CourseGroup.

Storage: SQLite `course_groups`.

Projection: PySide-Uebersicht `Stammgruppen und Schülerbestand`, Stammdaten-Seite.

Owner: Stammdatenverwaltung.

Primary Key: `course_group_id`.

Foreign Keys:

- keine direkt in `course_groups`

Wichtige Felder:

- `course_group_id`
- `name`
- `sort_order`
- `active`

Beziehungen:

- ein Kursverbund enthaelt viele Stammgruppen ueber `course_group_student_groups`
- ein Kursverbund enthaelt viele Kurse ueber `course_group_courses`

Schreibende Prozesse:

- Kursverbund bearbeiten
- Stammdaten-Defaults initialisieren

Lesende Prozesse:

- PySide-Uebersicht `Stammgruppen und Schülerbestand`
- Stammdaten-Seite
- Schuelerliste mit Kursverbund-/Kursfilter

Erweiterungsregeln:

- Kursverbund definiert einen Filter-Scope, keine Schueler-Umbuchung
- Name, Stammgruppen- und Kurszuordnung werden atomar gespeichert
- Loeschen bleibt einem spaeteren Sprint vorbehalten

## course_group_student_groups

Zweck: Relation zwischen Kursverbund und Stammgruppen.

Entity: CourseGroupStudentGroup.

Storage: SQLite `course_group_student_groups`.

Owner: Stammdatenverwaltung.

Primary Key:

- `course_group_id`
- `student_group_id`

Foreign Keys:

- `course_group_id` -> `course_groups.course_group_id`
- `student_group_id` -> `groups.group_id`

Regel: Diese Relation filtert, welche Stammgruppen in einem Kursverbund ausgewertet werden. Sie erzeugt keine neue Stammgruppe und bucht keine Schueler um.

## course_group_courses

Zweck: Relation zwischen Kursverbund und Kursen.

Entity: CourseGroupCourse.

Storage: SQLite `course_group_courses`.

Owner: Stammdatenverwaltung.

Primary Key:

- `course_group_id`
- `course_id`

Foreign Keys:

- `course_group_id` -> `course_groups.course_group_id`
- `course_id` -> `courses.course_id`

Regel: Diese Relation filtert, welche Kurse innerhalb eines Kursverbunds angezeigt werden. Kursfarben bleiben Metadaten des Kurses.

## data_subjects

Zweck: Faecher als fachliche Struktur. Kompetenzbereiche liegen im Kompetenzkatalog ueber `learning_area`.

Entity: Subject.

Storage: `data_subjects` / `tbl_subjects`.

Projection: Fachauswahl, Fachnavigation, Kompetenzstruktur.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Primary Key: `subject_id`.

Foreign Keys:

- keine

Wichtige Felder:

- `subject_id`
- `name`
- `sort_order`
- `status`

Beziehungen:

- ein Fach besitzt viele Kompetenzen

Schreibende Prozesse:

- Fach anlegen
- Fach bearbeiten
- Fach archivieren
- Python-Datenimport

Lesende Prozesse:

- Kompetenzansichten
- Beobachtungsdialog
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Fachauswahl
- Kompetenznavigation
- Kompetenzkarten

Erweiterungsregeln:

- Fachstruktur nur ueber fachlich freigegebene Konfiguration aendern
- Sortierung ueber `sort_order`, nicht ueber sichtbare Reihenfolge

## data_competencies

Zweck: Kompetenzen und Kompetenzstruktur.

Entity: Competency.

Storage: SQLite `competencies`, Export-/Legacy-Projektion `data_competencies` / `tbl_competencies`.

Projection: Kompetenzkarten, Kompetenzansicht, Kompetenzauswahl, Kompetenzchips.

Owner: Kompetenzverwaltung / Lehrplanpflege.

Primary Key: `competency_id`.

Foreign Keys:

- `subject_id` -> `data_subjects.subject_id` spaeter; aktuell mit `subject_name` aus dem Katalog denormalisiert
- `parent_competency_id` -> `data_competencies.competency_id`

Wichtige Felder:

- `competency_id`
- `subject_id`
- `subject_name`
- `label`
- `description`
- `learning_area`
- `competency_group`
- `parent_competency_id`
- `sort_order`
- `active`
- `is_core_subject`

Sprint-3A-Mapping:

- `subject_id` / `subject_name` = Fach
- `learning_area` = Kompetenzbereich
- `competency_group` = Thema
- `description` = konkrete Kompetenz
- `label` = Kurzlabel fuer kompakte UI

Beziehungen:

- eine Kompetenz gehoert zu einem Fach
- eine Kompetenz kann eine uebergeordnete Kompetenz besitzen
- eine Kompetenz kann vielen Beobachtungen zugeordnet werden

Schreibende Prozesse:

- Kompetenz ergaenzen
- Kompetenz bearbeiten
- Kompetenz archivieren
- Python-Datenimport

Lesende Prozesse:

- Beobachtungsdialog
- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Kompetenzkarten
- Kompetenzauswahl im Beobachtungsdialog
- Kompetenzverlauf
- Kompetenzchips an Beobachtungen

Erweiterungsregeln:

- Kompetenzstruktur wird aus dem freigegebenen Katalog geseedet und spaeter fachlich weiterentwickelt
- neue Kompetenzfelder duerfen keine Beobachtungsdaten duplizieren
- Bewertungen werden nicht als reine Farbwerte gespeichert

## data_observations

Zweck: Beobachtungen als fachliche Quelle der Lernentwicklung.

Entity: Observation.

Storage: SQLite `observations`, Export-/Legacy-Projektion `data_observations` / `tbl_observations`.

Projection: Beobachtungsverlauf, Kompetenzverlauf, Berichtsdaten, Dashboard-Auswertung.

Owner: Beobachtungserfassung.

Primary Key: `observation_id`.

Foreign Keys:

- `student_id` -> `data_students.student_id`

Wichtige Felder:

- `observation_id`
- `student_id`
- `date`
- `subject_id`
- `context`
- `note`
- `created_at`
- `updated_at`
- `active`

Beziehungen:

- eine Beobachtung gehoert zu einem Schueler
- eine Beobachtung kann vielen Kompetenzen zugeordnet werden
- eine Beobachtung kann Medien besitzen

Schreibende Prozesse:

- Beobachtung erfassen
- Beobachtung bearbeiten
- Beobachtung archivieren

Lesende Prozesse:

- Schuelerprofil
- Kompetenzansicht
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Beobachtungsverlauf im Schuelerprofil
- Kompetenzverlauf
- Berichtsdaten
- Dashboard-Auswertungen

Erweiterungsregeln:

- Beobachtungen bleiben Source of Truth fuer Lernentwicklung
- keine Auswertung darf Beobachtungsinhalte kopieren
- Archivierung statt physischer Loeschung

## data_observation_competencies

Zweck: Zuordnung von Beobachtungen zu Kompetenzen.

Entity: ObservationCompetency.

Storage: SQLite `observation_competency_ratings`, Export-/Legacy-Projektion `data_observation_competencies` / `tbl_observation_competencies`.

Projection: Kompetenzchips, Kompetenzverlauf, Bewertungsuebersicht.

Owner: Beobachtungserfassung.

Primary Key: zusammengesetzt aus `observation_id` und `competency_id`.

Foreign Keys:

- `observation_id` -> `data_observations.observation_id`
- `competency_id` -> SQLite `competencies.competency_id`

Wichtige Felder:

- `observation_id`
- `competency_id`
- `subject_id`
- `subject_display_name`
- `learning_area`
- `competency_group`
- `competency_text`
- `rating`

Sprint-3A-Mapping:

- `subject_id` / `subject_display_name` = Fach zum Zeitpunkt der Beobachtung
- `learning_area` = Kompetenzbereich zum Zeitpunkt der Beobachtung
- `competency_group` = Thema zum Zeitpunkt der Beobachtung
- `competency_text` = konkrete Kompetenz zum Zeitpunkt der Beobachtung
- `rating` = Bewertung dieser konkreten Kompetenz innerhalb dieser Beobachtung

Beziehungen:

- eine Beobachtung kann vielen Kompetenzen zugeordnet werden
- eine Kompetenz kann in vielen Beobachtungen vorkommen
- `rating` gehoert zur Zuordnung, nicht global zur Beobachtung

Schreibende Prozesse:

- Beobachtung erfassen
- Kompetenzzuordnung bearbeiten
- Beobachtung archivieren

Lesende Prozesse:

- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Erlaubte UI-Projektionen:

- Kompetenzchips an Beobachtungen
- Kompetenzverlauf
- Bewertungsuebersicht

Erweiterungsregeln:

- keine Kompetenzzuordnung ohne gueltige Beobachtung
- keine Kompetenzzuordnung ohne gueltige Kompetenz
- Bewertungswerte muessen aus der fachlich freigegebenen Skala stammen

## data_media

Zweck: Dokumente, Medien oder Anlagen zu Schuelern und Beobachtungen.

Entity: Media.

Storage: SQLite `documents`, optionale Export-/Legacy-Projektion `data_media` / `tbl_media`.

Projection: Dokumentliste, Medienhinweise, Anlagenliste, Beobachtungsdetails.

Owner: Dokumentenverwaltung / Medienanhang / Beobachtungserfassung.

Primary Key: `document_id`.

Foreign Keys:

- `student_id` -> SQLite `students.student_id`
- `observation_id` -> SQLite `observations.observation_id` optional fuer Beobachtungsanhaenge

Wichtige Felder:

- `document_id`
- `student_id`
- `observation_id`
- `title`
- `document_type`
- `file_path`
- `original_filename`
- `created_at`
- `note`
- `active`

Beziehungen:

- ein Dokument oder Medium gehoert immer zu einem Schueler
- ein Beobachtungsanhang kann zusaetzlich einer Beobachtung zugeordnet sein
- eine Beobachtung kann viele Anhaenge besitzen

Schreibende Prozesse:

- Schuelerdokument hinzufuegen
- Beobachtungsanhang hinzufuegen
- Dokument oder Medium bearbeiten
- Dokument oder Medium archivieren

Lesende Prozesse:

- Schuelerverwaltung
- Schuelerprofil
- Beobachtungsdetails
- Berichte

Erlaubte UI-Projektionen:

- Dokumentbereich in Schueler-UserForms
- Medienhinweise an Beobachtungen
- Anlagenliste

Erweiterungsregeln:

- Medien speichern keine Beobachtungsdaten doppelt
- SQLite speichert nur Metadaten, keine Datei-BLOBs
- Dateien werden nicht in Excel eingebettet
- Excel speichert hoechstens Referenzen und Metadaten
- physische Dateiablage erfolgt studentenzentriert im Dateisystem unter `data/documents/<student_id>/`
- Beobachtungsanhaenge liegen unter dem Schueler und tragen zusaetzlich den Beobachtungsbezug
- `document_type` nutzt die freigegebene MVP-Auswahl: Arbeitsprobe, Lernzielkontrolle, Gespraechsnotiz, Bericht, Foto, Audio, Sonstiges

Vorgesehene physische Dateiablage:

```text
data/
|-- kompetenzmanager.sqlite
`-- documents/
    |-- STU-000001/
    |   |-- MED-000001_Foerderplan.pdf
    |   `-- MED-000002_Arbeitsprobe.txt
    |-- STU-000002/
    `-- ...
```

## report_drafts und Berichtsentwurf-Relationen

Zweck: Persistenter, weiter bearbeitbarer Arbeitsentwurf fuer Lernentwicklungsberichte.

Entity: ReportDraft. Keine finale Berichtsentitaet.

Storage:

- SQLite `report_drafts` fuer Identitaet, Schuelerbezug, Berichtstyp, Zeitraum, Status, Lehrkraft, Gesamtblick und Zeitstempel
- SQLite `report_draft_subjects` fuer bewusste Fachauswahl und vier manuelle Fachtexte
- SQLite `report_draft_competencies` fuer reine `competency_id`-Referenzen
- SQLite `report_draft_observations` fuer reine `observation_id`-Referenzen
- SQLite `report_draft_charts` fuer Diagrammtyp je ausgewaehltem Fach

Owner: Lernentwicklungsbericht / Berichtsvorbereitung.

Primary Key: `report_draft_id`.

Foreign Keys:

- `student_id` -> `students.student_id`
- `competency_id` -> `competencies.competency_id`
- `observation_id` -> `observations.observation_id`
- alle Relationstabellen -> `report_drafts.report_draft_id` mit `ON DELETE CASCADE`

Wichtige Regeln:

- `status` ist in Sprint 7F.1 ausschliesslich `draft`.
- Kompetenztexte, Hierarchie, Bewertungen, Vorschlaege und Bestaetigungen werden nicht kopiert.
- Beobachtungsdatum, Kontext und Notiz werden nicht kopiert.
- Fachtexte stammen ausschliesslich aus manueller Eingabe durch Laura.
- Eine Zeile in `report_draft_subjects` repraesentiert ein bewusst ausgewaehltes Fach, auch wenn alle vier Texte noch leer sind.
- Der Berichtsentwurf liest Kompetenzstatus weiterhin ausschliesslich aus der kanonischen Sprint-6-Projektion.
- Neue Kompetenzreferenzen muessen aktiv und `current` sein sowie zu einem ausgewaehlten Fach gehoeren. Bereits gespeicherte, spaeter deaktivierte oder historische Kompetenz-IDs bleiben als nicht mehr regulaer verfuegbare Auswahl erhalten und werden nicht erneut zur Auswahl angeboten.
- Neue Beobachtungsreferenzen muessen aktiv sein, zum Kind gehoeren und mindestens einem ausgewaehlten Fach ueber Beobachtungsfach oder Kompetenzbewertung zugeordnet sein. Bereits gespeicherte, spaeter soft-geloeschte `OBS`-IDs bleiben als nicht verfuegbare Referenzen erhalten; Beobachtungsinhalte werden nicht rekonstruiert.
- Der Entwurf ist nicht freigegeben, versioniert, archiviert oder eingefroren.

Schreibende Prozesse:

- Berichtsentwurf anlegen
- Berichtsentwurf aktualisieren

Lesende Prozesse:

- Berichtsentwurf laden
- Berichtsentwuerfe eines Schuelers auflisten
- spaetere Sprint-7F.2-Berichtswerkstatt

## learning_reports und learning_report_revisions

Zweck: Stabile Lernentwicklungsbericht-Aggregate und unveraenderliche fachliche Revisionen aus einer bewussten Finalisierung eines weiterhin bearbeitbaren Berichtsentwurfs.

Entities: LearningReport und LearningReportRevision. Keine PDF-Artefakte und keine LEG-Entitaeten.

Storage:

```text
learning_reports(
  learning_report_id TEXT PRIMARY KEY,
  source_report_draft_id TEXT NOT NULL UNIQUE,
  student_id TEXT NOT NULL,
  report_type TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_report_draft_id) REFERENCES report_drafts(report_draft_id),
  FOREIGN KEY(student_id) REFERENCES students(student_id)
)

learning_report_revisions(
  learning_report_revision_id TEXT PRIMARY KEY,
  learning_report_id TEXT NOT NULL,
  revision_number INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('finalized', 'superseded')),
  snapshot_schema_version INTEGER NOT NULL,
  snapshot_json TEXT NOT NULL,
  snapshot_sha256 TEXT NOT NULL,
  finalized_at TEXT NOT NULL,
  finalized_by_display_name TEXT NOT NULL,
  superseded_at TEXT,
  UNIQUE(learning_report_id, revision_number),
  FOREIGN KEY(learning_report_id) REFERENCES learning_reports(learning_report_id)
)
```

Owner: Lernentwicklungsbericht / Finalisierung und Revisionshistorie.

Primary Keys:

- `learning_reports.learning_report_id` im Format `RPT-######`
- `learning_report_revisions.learning_report_revision_id` im Format `RPV-######`

Foreign Keys:

- `source_report_draft_id` -> `report_drafts.report_draft_id`
- `student_id` -> `students.student_id`
- `learning_report_id` -> `learning_reports.learning_report_id`

Wichtige Regeln:

- Pro `source_report_draft_id` existiert hoechstens ein stabiles `RPT`-Aggregat.
- Nach der Erstfinalisierung sind `source_report_draft_id`, `student_id`, `report_type`, `period_start` und `period_end` unveraenderliche Aggregateidentitaet. `learning_reports` besitzt keinen Update- oder Delete-Pfad. Weicht ein spaeter bearbeiteter `RPD` in Berichtstyp oder Zeitraum ab, wird die Folgerevision abgelehnt; der abweichende Bericht braucht einen neuen Draft und ein neues Aggregat.
- Revisionsnummern sind innerhalb eines `RPT` eindeutig, beginnen bei 1 und steigen ohne Luecke im normalen Finalisierungspfad.
- Pro `RPT` besitzt hoechstens eine Revision den Status `finalized`.
- Revisionszeilen werden weder geloescht noch fachlich aktualisiert. Nur beim Erzeugen einer Folgerevision darf die bisherige aktuelle Revision in derselben Transaktion von `finalized` auf `superseded` wechseln; dabei wird ausschliesslich `superseded_at` zusaetzlich gesetzt.
- Der fachliche Snapshot ist die historische Source of Truth. Er enthaelt Quell-`RPD`, eingefrorene sichtbare Schuelerdaten, Berichtskontext, verantwortlichen Anzeigenamen, manuelle Texte, Faecher, Kompetenzen mit Historienkennzeichnung, aktive ausgewaehlte Beobachtungsbelege, bewusst ausgewaehlte Diagrammdaten und Snapshot-Zeitpunkt.
- `snapshot_json` ist exakt die kanonische UTF-8-JSON-Darstellung. `snapshot_sha256` ist der SHA-256-Hexdigest genau dieser Bytes.
- `ReportOutputModel`, PDF-Dateien, Renderer-Versionen und Artefaktpfade sind keine Felder dieser Tabellen.
- Die bestehenden `report_drafts*`-Tabellen und ihr ausschliesslicher Status `draft` bleiben unveraendert.

Schreibender Prozess:

- Lernentwicklungsbericht-Draft finalisieren beziehungsweise als neue Revision erneut finalisieren

Lesende Prozesse:

- stabiles Berichtaggregat zum Quell-Draft lesen
- aktuelle oder historische Revisionen eines Berichtaggregats lesen

## learning_report_pdf_artifacts

Zweck: Unveraenderliche Dateireferenz fuer das genau aus einer verifizierten finalisierten Lernentwicklungsbericht-Revision erzeugte PDF.

Entity: LearningReportPdfArtifact. Kein fachlicher Berichtssnapshot, keine allgemeine Dokumententitaet und kein LEG-Artefakt.

Storage:

```text
learning_report_pdf_artifacts(
  learning_report_pdf_artifact_id TEXT PRIMARY KEY,
  learning_report_revision_id TEXT NOT NULL UNIQUE,
  relative_file_path TEXT NOT NULL UNIQUE,
  mime_type TEXT NOT NULL CHECK(mime_type = 'application/pdf'),
  file_size_bytes INTEGER NOT NULL CHECK(file_size_bytes > 0),
  snapshot_sha256 TEXT NOT NULL,
  pdf_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(learning_report_revision_id)
    REFERENCES learning_report_revisions(learning_report_revision_id)
)
```

Owner: Lernentwicklungsbericht / finaler PDF-Druck.

Primary Key:

- `learning_report_pdf_artifacts.learning_report_pdf_artifact_id` im Format `RPA-######`

Foreign Key:

- `learning_report_revision_id` -> `learning_report_revisions.learning_report_revision_id`

Wichtige Regeln:

- Pro `RPV` existiert hoechstens eine Artefaktreferenz. Die Zeile wird nach ihrer Erstellung weder aktualisiert noch geloescht.
- Ein neues Artefakt darf nur erzeugt werden, solange die Quellrevision den Status `finalized` besitzt und ihr kanonischer Snapshot sowie dessen interne Referenzen vollstaendig validiert sind.
- `relative_file_path` liegt relativ zum Verzeichnis der SQLite-Datei unter `documents/<student_id>/reports/<RPT>/<RPV>/`; der Dateiname enthaelt technische IDs und keinen Schuelerklarnamen.
- `snapshot_sha256` entspricht exakt dem bei der Erzeugung bestaetigten `learning_report_revisions.snapshot_sha256`.
- `pdf_sha256` ist der SHA-256-Hexdigest der gespeicherten PDF-Bytes; `file_size_bytes` ist deren exakte Bytegroesse.
- Der fachliche Snapshot bleibt Source of Truth. Das Artefakt ist ein abgeleitetes unveraenderliches Ausgabeobjekt und keine Quelle fuer neue Berichtsinhalte.
- Renderer-Versionierung, mehrere Artefakte pro Revision, Archivstatus, Retention und LEG-PDF sind nicht Teil dieser Tabelle.

Schreibender Prozess:

- finales PDF aus einer aktuellen `finalized`-Berichtrevision erzeugen

Lesende Prozesse:

- vorhandenes PDF-Artefakt fuer eine Revision laden und gegen Pfad, Groesse und Hash pruefen

## data_settings

Zweck: Workbook- und Anwendungseinstellungen.

Entity: Setting.

Storage: `data_settings` / `tbl_settings`.

Projection: Build-Kontext, Anzeigeeinstellungen, App-Bar-Kontext.

Owner: Systemeinstellungen.

Primary Key: `setting_key`.

Foreign Keys:

- keine

Wichtige Felder:

- `setting_key`
- `setting_value`
- `value_type`
- `description`

Beziehungen:

- keine fachlichen Beziehungen

Schreibende Prozesse:

- Python-Build
- Einstellungsverwaltung nach Freigabe

Lesende Prozesse:

- Python-Builder
- UI-Projektionen
- VBA nur fuer technische Interaktion bei Bedarf

Erlaubte UI-Projektionen:

- Schuljahr
- sichtbare Stammdaten im App-Bar-Kontext
- optionale Anzeigeeinstellungen

Erweiterungsregeln:

- Settings duerfen keine fachlichen Daten ersetzen
- fachliche Konfiguration gehoert in die passende Datenquelle, nicht pauschal in Settings

## learning_conference_drafts und LEG-Entwurfsrelationen

Zweck: Persistenter, weiter bearbeitbarer Arbeitsentwurf fuer Vorbereitung und Durchfuehrung eines Lernentwicklungsgespraechs.

Entity: LearningConferenceDraft. Kein Bericht und keine finale Gespraechsversion.

Storage:

- `learning_conference_drafts` fuer Identitaet, Schuelerbezug, Zeitraum, Gespraechsdatum, Status, verantwortliche Lehrkraft, manuell verantwortete Vorbereitungs- und Gespraechsinhalte sowie Zeitstempel
- `learning_conference_draft_subjects` fuer bewusste `subject_id`-Auswahl
- `learning_conference_draft_cross_topics` fuer die vier freigegebenen uebergreifenden Themen
- `learning_conference_draft_competencies` fuer reine `competency_id`-Referenzen
- `learning_conference_draft_observations` fuer reine `observation_id`-Referenzen
- `learning_conference_draft_charts` fuer die drei freigegebenen neutralen Darstellungsarten

Owner: Lernentwicklungsgespraech.

Primary Key: `learning_conference_draft_id`.

Foreign Keys:

- `student_id` -> `students.student_id`
- `competency_id` -> `competencies.competency_id`
- `observation_id` -> `observations.observation_id`
- alle Relationstabellen -> `learning_conference_drafts.learning_conference_draft_id` mit `ON DELETE CASCADE`

Wichtige Regeln:

- `status` ist in Sprint 7G.1 ausschliesslich `draft`.
- Der Entwurf referenziert Live-Daten und friert weder Kompetenz- noch Beobachtungsinhalte ein.
- Kompetenztexte, Hierarchie, Bewertungen, Bestaetigungen und berechnete Kompetenzstaende werden nicht kopiert.
- Beobachtungsdatum, Kontext, Notiz und Kompetenzbewertungen werden nicht kopiert.
- Ausgewaehlte Beobachtungen muessen zum betroffenen Kind gehoeren. Neue Auswahl ist nur fuer aktive Beobachtungen erlaubt; bereits referenzierte, spaeter soft-geloeschte Beobachtungen bleiben als nicht verfuegbarer Beleg identifizierbar.
- Schnellbeobachtungen duerfen als `observation_id` referenziert werden und bleiben ohne Wirkung auf Kompetenzstatus und Diagrammberechnungen.
- Ziele, Unterstuetzung, Vereinbarungen, Zustaendigkeiten und weitere Gespraechstexte sind ausschliesslich manuelle Inhalte. Vorbereitete und gemeinsam vereinbarte Inhalte bleiben getrennt.
- Diagrammzeilen speichern nur den Typ, keine berechneten Darstellungsdaten.
- Keine Freigabe, Versionierung, Archivierung, Signatur oder finale Dokumentation.

Schreibende Prozesse:

- LEG-Arbeitsentwurf anlegen
- LEG-Arbeitsentwurf aktualisieren

Lesende Prozesse:

- LEG-Arbeitsentwurf laden
- LEG-Arbeitsentwuerfe eines Schuelers auflisten
- Sprint-7G.2-LEG-Arbeitsbereich

## learning_conferences und learning_conference_revisions

Zweck: Stabiles fachliches LEG-Aggregat und unveraenderliche, reproduzierbare Abschlussrevisionen.

Entities:

- `LearningConferenceRecord` (`LCF`) als stabile Identitaet eines explizit abgeschlossenen LCD
- `LearningConferenceRevisionRecord` (`LCV`) als unveraenderlicher Abschlussstand

Storage:

- `learning_conferences` fuer `learning_conference_id`, Quell-LCD, Schuelerbezug und Erzeugungszeitpunkt
- `learning_conference_revisions` fuer Revisionsnummer, Status, Snapshotvertrag, Snapshot-JSON, SHA-256 und Abschluss-/Ersetzungsmetadaten

Owner: LEG-Abschlussdomain. Keine Berichtsdomain.

Primary Keys:

- `learning_conferences.learning_conference_id`
- `learning_conference_revisions.learning_conference_revision_id`

Foreign Keys:

- `learning_conferences.source_learning_conference_draft_id` -> `learning_conference_drafts.learning_conference_draft_id`
- `learning_conferences.student_id` -> `students.student_id`
- `learning_conference_revisions.learning_conference_id` -> `learning_conferences.learning_conference_id`

Wichtige Regeln:

- Pro LCD existiert hoechstens ein LCF; der LCD bleibt `draft` und bearbeitbar.
- Pro LCF existiert hoechstens eine aktuelle LCV mit Status `completed`.
- LCV-Snapshots sind unveraenderlich und nicht loeschbar; nur der Statuswechsel `completed` nach `superseded` mit `superseded_at` ist erlaubt.
- Ein identischer kanonischer Snapshot erzeugt keine neue LCV.
- Der Snapshot ist die historische Source of Truth und enthaelt keine interne Lehrkraftvorbereitung oder private Notizen.
- Ausgewaehlte historische Kompetenzen muessen vollstaendig aufloesbar und gekennzeichnet sein; fehlende Pflichtbelege blockieren den Schreibprozess.
- Diagramme bleiben in Sprint 10A Draftreferenzen und sind nicht Bestandteil des Abschluss-Snapshotvertrags.

Schreibender Prozess:

- expliziter LEG-Abschluss beziehungsweise korrigierender Folgeabschluss

Lesende Prozesse:

- LEG-Abschlussstatus zu einem LCD
- LCV-Historie eines LCF
- verifizierte snapshotbasierte LCV-Lesesicht

## learning_conference_pdf_artifacts

Zweck: Unveraenderliche Referenz auf genau ein verwaltetes finales PDF einer abgeschlossenen LEG-Revision.

Entity:

- `LearningConferencePdfArtifactRecord` (`LCA`)

Storage:

```text
learning_conference_pdf_artifacts(
  learning_conference_pdf_artifact_id TEXT PRIMARY KEY,
  learning_conference_revision_id TEXT NOT NULL UNIQUE,
  relative_file_path TEXT NOT NULL UNIQUE,
  mime_type TEXT NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  snapshot_sha256 TEXT NOT NULL,
  pdf_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
)
```

Owner: LEG-PDF-Domain. Keine Berichtsdomain und keine Workbook-Projektion.

Primary Key:

- `learning_conference_pdf_artifacts.learning_conference_pdf_artifact_id` im Format `LCA-######`

Foreign Key:

- `learning_conference_pdf_artifacts.learning_conference_revision_id` -> `learning_conference_revisions.learning_conference_revision_id`

Wichtige Regeln:

- Pro LCV existiert hoechstens eine Artefaktzeile; sie darf weder aktualisiert noch geloescht werden.
- Ein neues Artefakt darf nur fuer eine LCV mit Status `completed` entstehen.
- `snapshot_sha256` entspricht exakt dem vor dem Rendern bestaetigten Hash der LCV.
- `pdf_sha256` und `file_size_bytes` beschreiben exakt die unveraenderten gespeicherten PDF-Bytes.
- `relative_file_path` liegt unter `documents/<student_id>/learning_conferences/<LCF>/<LCV>/` relativ zum Verzeichnis der SQLite-Datei.
- Wiederaufrufe lesen und verifizieren die bestehende Zeile und Datei; es entsteht kein zweites Artefakt.

Schreibender Prozess:

- finales LEG-PDF aus einer verifizierten aktuellen LCV erzeugen

Lesender Prozess:

- vorhandenes LEG-PDF-Artefakt nach Pfad, Dateigroesse und SHA-256 verifizieren
