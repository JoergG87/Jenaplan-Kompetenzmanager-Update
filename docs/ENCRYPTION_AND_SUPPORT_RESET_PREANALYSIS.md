# Technische Voranalyse: integrierte Verschlüsselung und registrierungsgebundener Support-Reset

Status: Historische Produktvoranalyse; Security Sprint 2 bis 5 sind inzwischen
als isolierte Foundations implementiert, weiterhin keine Produktaktivierung
Stand des Repositories: 2026-07-21
Untersuchter Branch: `spike/python-gui`
Untersuchter Commit: `e644f9d04b35ef8cbef0b8f21193d4e2a741f55c`
(`chore(release): harden 0.2.2 support packaging`)
Produktname im Zielbild: Kompentra; technische Bestandsnamen verwenden weiterhin
`jenaplan-kompetenzmanager` beziehungsweise `jkm`.

Hinweis zum Lesen: Die folgenden Sprint-4-Abschnitte beschreiben den damaligen
Entscheidungsstand vor Security Sprint 5. Aussagen, dass KDF, AEAD-Envelope,
persistentes Journal oder Recovery-Entscheidung noch nicht implementiert
seien, sind historisch. Der aktuelle verbindliche Stand steht in ADR-078 bis
ADR-080, `PROJECT.md`, `DATA_REGISTRY.md` und `DATA_LIFECYCLE.md`. Produktive
Migration, Startup-/Login-Integration und Verschlüsselungsaktivierung bleiben
unverändert gesperrt.

## Umsetzungsstand Security Sprint 4 - isolierter Migrationsprototyp

Security Sprint 4 hebt ausschließlich das technische Migrations-Prototypgate
an synthetischen Daten auf. Alle Produkt-Stopbedingungen bleiben bestehen:
keine produktive Datenbank, kein Startup, kein Login, keine UI, keine Recovery,
kein Support Reset, kein produktives Backup/Restore, kein Dateiaustausch, keine
Klartextentsorgung, keine Pilot- oder Releaseaktivierung.

### Architektur- und Risikoanalyse vor Implementierung

Der bestehende Sprint-3-Provider ist als Ziel- und Wiederöffnungsgrenze
geeignet: Er verlangt einen expliziten 32-Byte-Key, setzt ihn vor jedem
Schema-Read, prüft die exakte Spike-Version und führt Cipher-, SQLite- und
Fremdschlüsselintegrität aus. Nicht geeignet sind die produktiven
`SQLiteDatabase`-, Startup-, Backup-/Restore- oder RuntimePaths-Pfade, weil
deren Aktivierung den RC beziehungsweise die Pilot-Runtime berühren würde.
Deshalb liegt die neue Orchestrierung ausschließlich unter
`prototypes/database_encryption_migration/` und wird von keinem Produktmodul
importiert.

Das Hauptrisiko ist nicht der Exportaufruf selbst, sondern eine falsche Quelle,
ein unvollständig geprüfter Kandidat oder ein unklarer Zustand beim späteren
Dateiaustausch. Der Prototyp begrenzt dies wie folgt:

| Risiko | Prototypmaßnahme | Verbleibende Grenze |
|---|---|---|
| versehentlich produktive Quelle | eigener temporärer Root, reguläre Datei ohne Symlink, feste Application-ID, feste User-Version und Guard-Tabelle/-Wert | Guard ersetzt keine spätere signierte Produktidentität und keine Nutzerfreigabe |
| Quelle während Migration verändert | read-only/immutable Attach, SHA-256 vor/nach Lauf, kein Rename/Replace/Delete | produktiv werden exklusiver App-Lock und Prozesskoordination benötigt |
| unvollständiges Backup | Integrität plus vollständiger Struktur-/Datenvergleich vor Export | produktiv müssen verwaltete Dokumente und freier Speicher mitgesichert werden |
| stiller Datenverlust oder Wertänderung | Counts, PK/FK, Objekte, Schemahash, typkanonische Tabellen-/Datenhashes | fachliche Produktinvarianten brauchen ein eigenes freigegebenes Profil |
| falscher oder korrupter Cipher-Kandidat | fail-closed Provider, Cipher-/SQLite-/FK-Integrität, echtes Neuöffnen | Wrong Key und Headerkorruption bleiben an dieser Grenze absichtlich gemeinsam klassifiziert |
| Absturz beim Dateiaustausch | kein Austausch im Prototyp | dauerhaftes Journal und reale Crash-/Power-Loss-Matrix bleiben Pflicht |
| Secrets in Testartefakten | neuer Laufzeitkey, kein Key in Report, Pfad oder Fixture, bestmögliches Buffer-Erase | Python/C/OS garantieren keine sofortige vollständige Speicherlöschung |

### Key Hierarchy

```text
plattformgeschützter Data Master Key (DMK, zufällig, 256 Bit)
  -> domain-separierter Database-Wrapping-Key (flüchtiger KEK)
       -> authentisiertes, versioniertes Envelope
            -> zufälliger Database-Key pro fachlicher Datenbank (256 Bit)
                 -> SQLCipher raw key

  -> separater Document-Wrapping-Key / zufällige Document Keys
  -> separater Backup-Wrapping-Key / zufällige Backup Keys
  -> weitere strikt zweckgebundene Keys
```

Der DMK ist weder App-Passwort noch SQLCipher-Key. Der Database-Key wird
zufällig erzeugt und nicht deterministisch aus Passwort oder DMK abgeleitet.
Ein späterer DMK-/Wrapping-Key-Wechsel kann dadurch grundsätzlich den
Database-Key neu wrappen, ohne alle Datenbankseiten neu zu verschlüsseln. Eine
echte Database-Key-Rotation bleibt dagegen ein gesonderter SQLCipher-Rekey-
oder Exportvorgang. Security Sprint 4 implementiert weder KDF noch AEAD-
Envelope noch Store; der Laufzeitkey bildet nur die unterste Ebene ab.

Geprüfte Alternativen:

| Variante | Bewertung |
|---|---|
| `DMK == SQLCipher-Key` | verworfen: keine Zwecktrennung, gekoppelte Rotation und zu großer Kompromittierungsradius |
| Database-Key direkt deterministisch aus DMK | verworfen: koppelt Datenbankidentität, Wiederherstellung und Rotation; kein unabhängiges Re-Wrapping |
| Database-Key aus App-Passwort | verworfen: Passwortwechsel, Offline-Brute-Force und Auth-/Datenzweck würden vermischt |
| zufälliger Database-Key unter zweckgebundenem DMK-Wrapping | empfohlen: unabhängige Rotation, klare Domänentrennung und versionierbares Envelope |

### Isolierter Datenfluss und Migrationskonzept

```text
TemporaryDirectory
  -> guarded synthetic-source.sqlite erzeugen
  -> Pfad-/Guard-/Application-ID-/User-Version-Prüfung
  -> SQLite integrity_check + foreign_key_check
  -> Quell-SHA-256 + vollständigen Quellsnapshot bilden
  -> SQLite Backup API -> run-N-verified-backup.sqlite
  -> Backupintegrität + vollständigen Snapshotvergleich
  -> neues run-N-encrypted.sqlcipher über Sprint-3-Provider
  -> Quelle read-only/immutable mit leerem Attach-Key anbinden
  -> explizite Transaktion + sqlcipher_export('main', 'plaintext')
  -> application_id + user_version setzen -> Commit -> fsync
  -> Ziel schließen und mit richtigem Database-Key neu öffnen
  -> cipher_integrity_check + integrity_check + foreign_key_check
  -> vollständigen Zielsnapshot bilden und vergleichen
  -> Quell-SHA-256 erneut prüfen -> Messreport
  -> TemporaryDirectory nach Testende entfernen
```

Die offizielle SQLCipher-Dokumentation verlangt für Klartextverschlüsselung
eine neue leere verschlüsselte Datenbank und `sqlcipher_export`, nicht
`PRAGMA rekey`. `sqlcipher_export` überträgt Schema, Trigger, virtuelle Tabellen
und Daten, aber weder `user_version` noch `auto_vacuum`. Der Prototyp setzt
deshalb `auto_vacuum` am leeren Ziel vor dem Export und `application_id` sowie
`user_version` vor dem Commit explizit. Referenz:
https://www.zetetic.net/sqlcipher/sqlcipher-api/#sqlcipher_export

### Validierungskonzept

Eine Migration ist nur erfolgreich, wenn alle folgenden Dimensionen identisch
sind:

- Menge und Namen aller nicht internen Tabellen;
- Zeilenanzahl pro Tabelle und global;
- geordnete Primärschlüsselspalten einschließlich zusammengesetzter PKs;
- vollständige `foreign_key_list`-Definitionen und leeres
  `foreign_key_check`;
- Namen, Eigentabellen und normalisierte SQL-Definitionen aller Trigger,
  Views und expliziten Indizes;
- `application_id`, `user_version`, `auto_vacuum`, `encoding` und `page_size`;
- SHA-256 der normalisierten gesamten `sqlite_schema`-Projektion;
- SHA-256 pro Tabelle und global über alle Datensätze.

Für Datenhashes wird jeder SQLite-Wert mit einem Typmarker (`NULL`, Integer,
Float, Text, Blob) und einer 64-Bit-Längenrahmung kodiert. Zeilen werden als
kanonische Bytefolgen sortiert, sodass Tabellenreihenfolge und Row-ID-
Reihenfolge keinen falschen Unterschied erzeugen, Duplikate aber erhalten
bleiben. Counts verhindern, dass identische Hashinputs bei unterschiedlicher
Multiplizität übersehen werden. Dieser technische Gleichheitsbeweis umfasst
auch Binäranhänge und `NULL`-/Typunterschiede.

### Rollback-Konzept und Fehlerproben

Im Prototyp findet kein Live-Austausch statt. Rollback ist daher fail-closed:

1. Vor verifiziertem Backup bleibt ausschließlich die unveränderte Quelle.
   Ein eigenes Teilbackup wird entfernt.
2. Nach verifiziertem Backup bleibt die Quelle unverändert maßgeblich und das
   Backup erhalten.
3. Ein eigenes fehlgeschlagenes Cipher-Ziel wird nur entfernt, wenn Device- und
   Inode-Identität noch der von der Engine angelegten Datei entsprechen.
4. Quelle und gegebenenfalls Backup werden nach dem Fehler erneut auf
   Integrität und vollständige Snapshotgleichheit geprüft.
5. Der Key, der Fehler auslöste, wird nicht protokolliert; Fehlercodes enthalten
   weder SQL noch Pfad noch Roh-Exception.

Automatisch simuliert sind Fehler beim Backup, vor dem Export, vor dem Commit,
ein Fortschrittsabbruch mitten im Export, eine beschädigte Zieldatei und ein
falscher Wiederöffnungsschlüssel. Zusätzlich werden beschädigte Quelle und
inkompatible SQLCipher-Version fail-closed getestet.

### Späterer atomarer Dateiaustausch - nur Ablaufbeschreibung

Der Prototyp ruft weder `os.replace` noch `rename` noch `unlink` auf der Quelle
auf. Eine spätere Produktmigration benötigt mindestens:

1. exklusiven App-/Prozesslock und erneute Dateiidentitätsprüfung;
2. dauerhaftes, fsync-gesichertes Migrationsjournal mit eindeutigen Phasen;
3. fsync des vollständig validierten Cipher-Kandidaten;
4. Rename der Klartextquelle auf einen retained rollback name;
5. atomaren Rename des Cipher-Kandidaten auf den Live-Namen;
6. fsync des enthaltenden Verzeichnisses;
7. SQLCipher-Neuöffnen über den echten Startup-Key-Lifecycle;
8. Journalabschluss erst nach erfolgreichem Runtime-Smoke;
9. deterministische Start-Recovery, die nie zwei Kandidaten errät;
10. getrennte, bewusst freigegebene Behandlung der alten Klartextdatei.

`os.replace` allein beweist weder Stromausfallsicherheit über alle
Dateisystem-/Hardwarekombinationen noch sichere physische Löschung auf
APFS/NTFS/SSD. Reale Crash- und Power-Loss-Tests bleiben erforderlich.

### Fehleranalyse

| Fall | Erwartetes Verhalten | Risiko | Wiederherstellung / offenes Gate |
|---|---|---|---|
| Stromausfall | im Prototyp kein Live-Austausch; Quelle bleibt unberührt | temporäres Backup/Ziel kann unvollständig sein | Temp-Root verwerfen; produktiv Journal, fsync und reale Power-Loss-Tests |
| Prozessabbruch | Quelle bleibt read-only; kein Austausch | Teilziel/-backup im Temp-Root | nächsten Lauf mit neuem Root beginnen; produktiv Journal-Cleanup |
| beschädigte Quelle | `integrity_check`/Read schlägt vor Backupfreigabe fail-closed fehl | keine Migration möglich | vorhandenen geprüften Backup-/Restoreweg nutzen; keine automatische Reparatur |
| beschädigtes Ziel | Cipher-/SQLite-Integrität oder Reopen schlägt fehl; Ziel wird verworfen | Verfügbarkeit des Kandidaten | aus unveränderter Quelle und verifiziertem Backup neu migrieren |
| fehlende Rechte | Öffnen/Anlegen/fsync muss fehlschlagen, ohne Quelle umzubenennen | kein Kandidat/Backup | Rechte/Ort korrigieren und neuen Lauf starten; plattformspezifischer Test offen |
| fehlender Speicherplatz | Backup oder Export/Commit muss abbrechen; Quelle bleibt maßgeblich | Teilbackup/-ziel und Betriebsunterbrechung | Teilziel entfernen, Speicherreserve vorab prüfen; ENOSPC-/Quota-Harness offen |
| falscher Schlüssel | gemeinsame sanitisierte Key/Header-Ablehnung; kein Fallback | Ursache nicht von Headerfehler trennbar | korrekten Envelope/Key wiederherstellen; nie leere DB neu erzeugen |
| falsche SQLCipher-Version | exakte Versionsprüfung bricht vor Migration fail-closed ab | Migration nicht verfügbar | kontrollierten freigegebenen Build installieren; kein Downgrade/Fallback |

### Gemessene Performance

Referenzlauf am 2026-07-22 im lokalen Entwicklungsprozess, einmalig und ohne
Produkt-/Releaseaussage:

| Messwert | Ergebnis |
|---|---:|
| eigene synthetische Tabellen | 11 |
| validierte Tabellen einschließlich `sqlite_sequence` | 12 |
| Zeilen einschließlich Relationstabellen/Audit/`sqlite_sequence` | 50.062 |
| Klartextquelle | 4.739.072 Byte |
| verifiziertes Backup | 4.739.072 Byte |
| SQLCipher-Ziel | 4.583.424 Byte |
| Quellintegrität + Snapshot | 0,123 s |
| Backup + Prüfung | 0,143 s |
| Export + fsync | 0,057 s |
| vollständiger Zielvergleich | 0,169 s |
| SQLCipher-Neuöffnen + Integrität | 0,074 s |
| Gesamtdauer | 0,586 s |

Die Datenbankgröße kann durch Seitenbelegung, Auto-Vacuum, freie Seiten und
Cipher-Reserve kleiner oder größer als die Quelle sein; Größenähnlichkeit ist
kein Integritätskriterium. Zeiten variieren mit Hardware, Cache, Dateisystem,
SQLCipher-Build und Datenform. Es wurde nicht optimiert.

### Offene Risiken und Stopbedingungen

- Spike-Binding 0.6.2 / SQLCipher 4.12.0 ist keine Produktbasis; kontrollierter
  hash-gepinnter 4.17.0-Build, SBOM, Notices und CVE-Prozess fehlen.
- KDF-/AEAD-Algorithmus, Envelope-AAD, Nonceformat, Keyset-Generationen,
  Recovery und Rotation des produktiven Database-Key sind nicht implementiert.
- Der Prototyp besitzt kein Produkt-Schema-/Produktidentitätsprofil und keine
  freigegebenen fachlichen Invarianten für reale Daten.
- Exklusiver Lock, dauerhaftes Journal, Live-Austausch, Start-Recovery,
  Speicherplatzreserve und Klartext-Nachbehandlung fehlen absichtlich.
- Backup/Restore, Dokumente, PDF-Artefakte und externe Referenzen sind nicht
  engine- oder verschlüsselungsbewusst migriert.
- Fehlende Rechte und ENOSPC sind dokumentiert, aber nicht portabel
  automatisiert; Power-Loss braucht physische macOS-/Windows-Tests.
- Windows-x64, Produkt-PyInstaller, Developer ID, Notarisierung, Authenticode,
  Upgradepfad und Pilot-Rollback sind nicht geprüft.
- Die Messung ist kein Performance-SLO und keine Aussage zur Eignung für eine
  reale Nutzerinstallation.

Aus diesem Sprint folgt keine Aussage zur rechtlichen oder organisatorischen
Compliance. Freigegeben ist ausschließlich die technische Machbarkeit des
isolierten synthetischen Transfers und Vergleichs.

## Abgrenzung Security Sprint 2

Für Security Sprint 2 ist ausschließlich die isolierte Key-Foundation aus dem
späteren E2-Zielbild als Entwicklungsarbeit freigegeben: DMK/Keyset-Domain,
plattformneutraler Secret-Port, macOS-Keychain-Adapter und versioniertes
Envelope-Format. Alle Aussagen dieses Dokuments zu SQLCipher, fachlicher oder
dateibasierter Verschlüsselung, Backup v2, Migration, Startup, Supportprotokoll,
Windows-Implementierung und Rollout bleiben Voranalyse und gesperrt.

Release Candidate `0.2.2`, `security.sqlite` v3 und Pilotdaten bleiben
unverändert. Die Foundation nutzt einen neuen, nicht in RuntimePaths oder
Startup eingebundenen Development-Sidecar nur für technische Keyset-Metadaten.
DMK und geschütztes Envelope-Material werden dort nicht persistiert. Es gibt
keine v3-v4-Migration und keine Produktaktivierung.

## Umsetzungsstand Security Sprint 3 - isolierte SQLCipher-Infrastruktur

Security Sprint 3 hebt ausschließlich das E0-Infrastrukturgate teilweise auf.
Er führt eine kleine explizite Connection-Provider-Grenze und einen isolierten
SQLCipher-Testpfad ein. Alle produktiven Aussagen und Stopbedingungen dieses
Dokuments bleiben bestehen: keine Migration, kein Startup, kein Login, keine
UI, keine Dokument-/Backupverschlüsselung und kein Release.

### Architektur- und Bindingentscheidung

Der fachliche Repository-Pfad läuft zentral über `SQLiteDatabase.connect()`;
Backup, Restore, Kompatibilitätsprüfung, Runtime-Seed, `security.sqlite` und der
Development-Keyset-Sidecar besitzen jedoch weitere direkte `sqlite3`-Pfade.
Security Sprint 3 kapselt nur die normale Connection-Erzeugung und den
isolierten Cipher-Smoke. Er behauptet nicht, Backup oder Restore seien bereits
SQLCipher-fähig. Treibereigene `Row`- und Exception-Typen werden am Provider
verwendet; bestehende `sqlite3.Error`-Fänger werden nicht umgedeutet.

| Variante | Vorteile | Nachteile | Sicherheitsrisiko | Packaging-Risiko | Plattformrisiko | Wartung | Migrationsauswirkung | Testaufwand |
|---|---|---|---|---|---|---|---|---|
| PyPI-Wheel `sqlcipher3` 0.6.2 | DB-API-nah; kleinste Provider-Naht; CPython-3.14-Wheels | Engine-Metadaten unvollständig; tatsächlich 4.12.0; Lizenzangaben widersprüchlich | Drittanbieter-Binary und veralteter Core ohne eigene Buildkette | nicht Trusted Publishing; Notices/SBOM unvollständig; nur Spike-Signatur | Wheel-Indiz für macOS arm64/Windows x64, real nur macOS geprüft | geringer lokal, aber Upstream-/CVE-Abhängigkeit | API grundsätzlich geeignet; Version für produktiven Export/Migration nicht freigegeben | klein für Spike, hoch für Produkt-, Update- und Supply-Chain-Nachweis |
| kontrollierter `sqlcipher3`-Source-Build gegen SQLCipher 4.17.0 | gleiche API; aktuelle Engine; Quellen, Flags, Hashes und SBOM kontrollierbar | eigene Wheel- und Toolchain-Verantwortung | Fehlkonfiguration von Crypto-Provider/Flags; eigener Patch-/CVE-Prozess nötig | reproduzierbare arm64-/x64-Wheels, Signierung, Notices und PyInstaller-Sammlung selbst pflegen | macOS arm64 und Windows x64 getrennt bauen und physisch testen | hoher, aber kontrollierbarer Aufwand pro Python-/SQLCipher-/OpenSSL-Update | bevorzugte Grundlage für `sqlcipher_export`, Upgrade und Kompatibilitätsvertrag | vollständige Cipher-, Crash-, Performance-, Migration-, Packaging- und Upgrade-Matrix |
| APSW mit eigener SQLCipher-Amalgamation | aktiv gepflegt; flexible Low-Level-SQLite-Steuerung | nicht DB-API; andere Rows, Exceptions, Transaktionen und Backupsemantik | große neue Adapterfläche erhöht Fehlklassifikations- und Transaktionsrisiko | eigener SQLCipher-Build plus APSW-spezifische Hooks | je Plattform eigene Build-/ABI-Prüfung | sehr hoch wegen dauerhafter Abweichung vom stdlib-Modell | breite Repository-, Backup- und Restore-Refaktorierung vor Migration | höchste Regressionstiefe über gesamte Persistenzschicht |

`pysqlcipher3` wurde zusätzlich geprüft und ausgeschlossen: Das Projekt ist
nicht aktiv gepflegt, bindet einen alten SQLCipher-Stand, bietet keine modernen
Wheels und benötigt eine externe native Buildabhängigkeit. Es ist daher keine
ernsthafte Produktalternative.

Für den isolierten Spike gelten:

- Binding: `sqlcipher3` 0.6.2.
- Gemessene Engine: SQLCipher `4.12.0 community`, SQLite 3.51.1,
  OpenSSL 3.6.0.
- Produktziel: SQLCipher 4.17.0 aus reproduzierbaren, hash-gepinnten eigenen
  Wheels für macOS arm64 und Windows x64.
- SQLCipher Community: BSD-artige Attribution mit benutzerzugänglichen
  Copyright-, Lizenz- und Abhängigkeitshinweisen.
- Binding: PyPI nennt MIT, die im Wheel enthaltene Datei und das Repository
  verwenden einen zlib-artigen Text. Vor Distribution ist der genaue Notice-
  Satz anhand des kontrollierten Builds zu klären.

### Isolierter Daten- und Schlüsselfluss

```text
Test/Smoke
  -> TemporaryDirectory + secrets.token_bytes(32)
  -> SQLCipher-Verbindung explizit anfordern (nie über Startup/Environment)
  -> raw 32-byte key als erste SQLCipher-Operation
  -> vor Schema-Read exakte Engine-/Cipher-/Page-/KDF-/HMAC-Prüfung
  -> feste Memory-/Temp-/Journal-/Sync-/FK-Regeln
  -> synthetisches Schema und synthetische Zeilen
  -> close -> no-create reopen -> Cipher-/SQLite-/FK-Integrität
  -> normal sqlite3 und falschen Key ablehnen
  -> Testverzeichnis automatisch entfernen
```

App-Passwort und DMK werden nicht als DB-Key verwendet. Das Sprint-2-Envelope
wrappt ebenfalls keinen Datenbankschlüssel. Später wird ein eigener zufälliger
DB-Key benötigt, der unter einem zweckgebundenen DMK-KEK geschützt wird. Der
Security Store darf nur geschütztes Wrapping und technische Versionen tragen,
nie Klartext-DMK oder Klartext-DB-Key. Diese Hierarchie ist konzipiert, nicht
implementiert.

### Fail-closed-Verhalten und Threat Model

| Bedrohung / Fehler | Verhalten | Verbleibendes Risiko |
|---|---|---|
| Binding/native Engine fehlt oder Version weicht ab | sanitierter Fehler, kein `sqlite3`-Fallback | Verfügbarkeit bis korrekter Build bereitsteht |
| Key fehlt, ist leer oder nicht 32 Bytes | Ablehnung vor Dateierzeugung | Aufrufer muss sicheren Key-Lifecycle bereitstellen |
| falscher Key, Headerkorruption oder inkompatible Cipherparameter | gemeinsame sanitierte Authentisierungs-/Headerablehnung; keine Neuerstellung | Ursache ist ohne authentisierte externe Metadaten nicht eindeutig trennbar |
| Klartext-SQLite am Cipher-Provider | Headererkennung und Ablehnung ohne Änderung | Headerprüfung allein ist kein Verschlüsselungsbeweis |
| authentisierte Seite oder logische Struktur beschädigt | `cipher_integrity_check`, `integrity_check` und `foreign_key_check` schlagen fehl | Verfügbarkeitsverlust; Recovery/Migration fehlt absichtlich |
| Key in Fehlern/Artefakten | strukturierte Codes, keine Roh-Exception, Laufzeitschlüssel, deaktivierter Statement-Cache, Buffer bestmöglich überschrieben | unvermeidbare immutable Hex-/SQL-Zeichenkette; Python/C/OS garantieren keine vollständige sofortige Speicherlöschung |

Der Verschlüsselungsnachweis kombiniert exakte `cipher_version`,
`cipher_status=1`, `cipher_plaintext_header_size=0`, Cipherseitengröße,
KDF-/HMAC-Parameter, erfolgreiches Wiederöffnen, beide Integritätsprüfungen,
die Ablehnung durch Standard-`sqlite3`, einen vom Klartextheader abweichenden
Dateianfang und die Abwesenheit des synthetischen Markers in den Dateibytes.
Kein einzelnes Kriterium genügt allein.

### Packaging-, Plattform- und Releasebefund

Der isolierte macOS-Prototyp wurde mit Python 3.14.6 und PyInstaller 6.21.0 als
arm64-Onefile ausschließlich unter `/private/tmp` gebaut. Das etwa 13 MB große
Programm enthält sowohl die Standard-`sqlite3`-Extension für den Negativtest als
auch `sqlcipher3/_sqlite3`, ist lokal ad-hoc-signiert, besteht
`codesign --verify --deep --strict` und den vollständigen Cipher-Smoke.
Wegen des absichtlich späten Treiberimports erkennt ein generischer PyInstaller-
Lauf `sqlcipher3` nicht automatisch: Spec beziehungsweise Build müssen Binding,
native Extension und Lizenzdaten explizit sammeln. Ohne diese Aufnahme startet
der Prototyp fail-closed mit `sqlcipher_unavailable`.

Das ist kein Produkt- oder Releasebeleg. Nicht geprüft und daher offen sind:

- kontrollierter SQLCipher-4.17.0-Build und vollständige SBOM/Notices;
- Aufnahme in `requirements-macos-build.txt` und den Pilot-Spec;
- Developer-ID, Hardened Runtime, Notarisierung und Stapling;
- DMG und Sparkle-Update-ZIP aus demselben signierten App-Baum;
- saubere macOS-Upgradeprobe von 0.2.2;
- Windows-x64-Wheel, DLL-Inventar, PyInstaller-Spec, Authenticode und Update;
- Performance-, WAL-, Crash-, Parallelitäts- und große-Datenbanktests.

Das öffentliche Wheel bietet zwar Windows-x64/Python-3.14, dies ist nur ein
Verfügbarkeitsindiz und kein Windows-Kompatibilitätsnachweis. Der bestehende RC,
DMG, Update-ZIP und Appcast wurden nicht gebaut oder verändert.

### Backup, Restore und spätere Migration

Bestehende Backup-/Restorepfade verwenden weiterhin Standard-`sqlite3`,
Klartext-Snapshots und direkte Integritätsprüfungen. Sie dürfen eine produktive
SQLCipher-Datei später nicht ungekeyt öffnen und sind vor Aktivierung vollständig
engine-bewusst zu entwerfen. Security Sprint 3 ändert daran nichts.

Eine spätere Migration muss mindestens:

1. Klartextquelle über Header, Produktidentität und Schema eindeutig bestimmen;
2. die Anwendung exklusiv sperren und unverändertes verifiziertes Backup halten;
3. Quelle mit SQLite-/FK-Integrität prüfen;
4. separates verschlüsseltes Ziel mit eigenem zufälligem DB-Key erzeugen;
5. Schema und Daten mit `sqlcipher_export` oder gleichwertigem kontrolliertem
   Transfer übernehmen;
6. Tabellenzeilen, Schemafingerprint und fachliche Invarianten vergleichen;
7. Dokumente, PDF-Artefakte, externe Referenzen und Backups inventarisieren;
8. Cipher-, SQLite- und FK-Integrität am Ziel prüfen;
9. Ziel synchronisieren, atomaren Austausch und Neustarttest durchführen;
10. bei jedem Fehler ohne Teilfreigabe rollbacken oder eindeutig fortsetzen;
11. alte Klartextdatei und externe Klartextkopien transparent behandeln.

`os.replace`, Überschreiben oder Entlinken garantiert auf SSD/APFS/NTFS wegen
Copy-on-write, Wear-Leveling, Snapshots und Caches keine sichere physische
Löschung. Eine spätere Datenschutz- und Rolloutaussage darf daher nur
nachweisbare logische Entfernung und verbleibende forensische Grenzen benennen.

## 0. Ergebnis und Entscheidungsstatus

Das Zielbild ist technisch erreichbar, aber kein inkrementeller Austausch einer
einzelnen Bibliothek. Es betrifft die Datenbankverbindung, die gesamte verwaltete
Datei-I/O, Backup und Restore, die Startreihenfolge, zwei native Plattformadapter,
das Security-Schema, das Support-Tool, Packaging und die Migration bestehender
Installationen.

Empfohlen wird:

1. SQLCipher für die fachliche SQLite-Datenbank.
2. Ein zufälliger 256-Bit-Datenhauptschlüssel (`DMK`), der ausschließlich über
   einen neuen Plattformport aus macOS Keychain beziehungsweise Windows DPAPI
   verfügbar wird.
3. Zufällige Inhalts- beziehungsweise Objektschlüssel; zweck- und
   objektgebundene Wrapping-Schlüssel werden mit HKDF-SHA-256 aus dem DMK
   abgeleitet.
4. XChaCha20-Poly1305 `secretstream` aus libsodium für verwaltete Dokumente und
   große verschlüsselte Dateiströme. AES-256-GCM bleibt eine vertretbare
   Alternative, ist für das hier erforderliche chunkweise, absturzsichere
   Datei-I/O aber nicht die erste Empfehlung.
5. Ein Backupformat v2 mit zufälligem Backupschlüssel, verschlüsseltem Manifest,
   verschlüsselter SQLCipher-Kopie und bereits verschlüsselten Dokumenten.
6. Ein separates Ed25519-Installationssignaturschlüsselpaar und ein separates
   X25519-Support-Verschlüsselungsschlüsselpaar. Ed25519 darf nicht als
   Verschlüsselungsschlüssel verwendet werden.
7. Ein Support-Tool mit eigener verschlüsselter lokaler Datenbank, das weder
   Datenhauptschlüssel noch fachliche Daten erhält.

Die Einführung darf erst beginnen, wenn die Stopbedingungen in Abschnitt 20
aufgelöst und die Produktentscheidungen zu Dokumentöffnung, portablen Backups,
Bestands-Exports und Support-Datenaufbewahrung getroffen sind.

## 1. Bestätigter Ist-Zustand

### 1.1 Repository und Arbeitsstand

- HEAD ist der oben genannte Commit auf `spike/python-gui`.
- Der Arbeitsbaum enthielt vor dieser Analyse bereits die sachfremde Änderung
  `docs/Pilottest_Laura_Schuelerprofil_Variante_A.xlsx`. Sie gehört nicht zu
  diesem Auftrag.
- Die Hauptanwendung ist PySide6 mit fachlicher SQLite-Datenbank. Der
  Security Store ist eine zweite SQLite-Datenbank.
- Es existiert nur ein macOS-arm64-PyInstaller-Pilotbuild. Ein produktiver
  Windows-Buildpfad ist nicht vorhanden.

### 1.2 Fachliche SQLite-Datenbank

- `src/core/sqlite_store.py:210` definiert `SQLiteDatabase`;
  `src/core/sqlite_store.py:216` öffnet mit der Python-Standardbibliothek
  `sqlite3.connect(...)`.
- `src/desktop_app/adapters/student_desktop_adapter.py:1765` initialisiert die
  fachliche Datenbank und die Repositories nach dem Öffnen.
- Weitere direkte fachliche SQLite-Verbindungen bestehen in:
  `src/core/backup.py`, `src/core/database_compatibility.py`,
  `src/core/restore.py`, `src/core/restore_runtime.py` und
  `src/desktop_app/runtime.py` sowie in Pilot-/Smoke-Skripten.
- Die geprüfte Laufzeitdatenbank besitzt den Klartext-Header `SQLite format 3`.
  Es gibt keinen Cipher-Key, keine Verschlüsselungsprüfung und keinen
  fail-closed Cipher-Adapter.
- Repositories öffnen kurzlebige Verbindungen über `SQLiteDatabase.connect()`.
  Damit ist eine zentrale Connection Factory vorhanden, aber Backup, Restore,
  Kompatibilitätsprüfung und Runtime-Seedpfad umgehen sie teilweise.

Vollständiges Inventar der aktuellen Erzeugungs-/Verbindungsstellen:

| Datei | Zweck |
|---|---|
| `src/core/sqlite_store.py` | fachliche Hauptverbindung und alle darauf aufbauenden Repositories |
| `src/core/backup.py` | read-only Quelle, Klartext-Snapshotziel und Verifier |
| `src/core/database_compatibility.py` | read-only Schema-/Kompatibilitätsprüfung |
| `src/core/restore.py` | vorbereitete Restore-DB, Migrations- und Rebase-Schritte |
| `src/core/restore_runtime.py` | Checkpoint und read-only Prüfung von Live-/Rollback-DB |
| `src/desktop_app/runtime.py` | Rebase einer kopierten Pilot-Initialdatenbank |
| `src/security/infrastructure/sqlite_repository.py` | Erzeugung, Probe, Lesen und Schreiben des getrennten Security Store |
| `scripts/prepare_macos_pilot_payload.py` | Vorbereitung der Pilotdatenbank |
| `scripts/smoke_test_macos_app.py` | Smoke-Prüfung der fachlichen Laufzeitdatenbank |
| `scripts/smoke_test_support_reset_e2e.py` | E2E-Fixture und Prüfung für den aktuellen Support-Reset |

Das fachliche Schema wird derzeit in `sqlite_store.py` per `CREATE TABLE IF NOT
EXISTS`, `ALTER TABLE` und Default-/Kataloginitialisierung fortgeschrieben. Die
Kompatibilitätsprojektion liegt in `database_compatibility.py`; Restore besitzt
zusätzliche vorbereitende Migrationen und Pfad-Rebases. Es gibt somit keine
einzige externe Migration-Engine, sondern drei koordinierte Pfade. Für
SQLCipher muss deren Reihenfolge erhalten, aber jede Verbindung durch dieselbe
keyed Factory erzwungen werden. Der Security Store bleibt absichtlich ein
eigener Repository-/Migrationspfad.

### 1.3 Security Store, Authentifizierung und Schlüsselbund

- `src/security/infrastructure/sqlite_repository.py` verwaltet ein separates
  Security-Schema v3 mit Konten, Argon2id-Passworthash, Recovery-Codes,
  Support-Reset-Anfragen/-Verbrauch, Security-Epoch und Gerätecredentials.
- Passwortwechsel, Recovery und Support-Reset erhöhen bereits die
  `security_epoch` und widerrufen aktive Gerätecredentials.
- Der aktuelle Support-Reset ist ein Ed25519-signierter Token-Flow. Die Anfrage
  ist noch nicht installationssigniert, enthält kein Support-Geheimwort und das
  Support-Werkzeug besitzt keine Registrierungsdatenbank.
- `src/security/ports.py` enthält mit `DeviceSecretStore` bereits einen Port für
  ein 32-Byte-Gerätecredential.
- `src/security/infrastructure/platform_auth.py` und
  `src/security/infrastructure/macos_security_bridge.m` speichern dieses
  Credential unter dem Keychain-Service
  `de.jenaplan.kompetenzmanager.device-credential`. Dieser Port und Namespace
  dürfen nicht für den Datenhauptschlüssel wiederverwendet werden.
- Außerhalb von macOS liefert der Adapter derzeit `unsupported`; eine
  Windows-DPAPI-Implementierung existiert nicht.
- Der Security Store ist selbst nicht verschlüsselt. Er enthält bislang
  Passwort-/Recovery-Hashes und technische Metadaten, aber keine fachlichen
  Daten. Im Zielbild darf er nur verschlüsselte Key-Wrappings,
  Plattformreferenzen und Protokollstatus enthalten, niemals den DMK im
  Klartext.

### 1.4 Startreihenfolge

Die Reihenfolge ist heute grundsätzlich günstig:

1. Restore-Worker-Dispatch (`src/desktop_app/main.py:114`).
2. Runtime-Lock und unvollständige Restore-Recovery.
3. Security Store und Authentifizierung.
4. Erst danach `prepare_runtime_storage()` (`main.py:303`).
5. Erst danach Erzeugung der Anwendung und fachlicher Adapter (`main.py:309`).

Die fachliche Datenbank wird somit im normalen Start erst nach erfolgreicher
Authentifizierung geöffnet. Restore-Recovery darf bereits vor Login technische
Datenbankprüfungen ausführen. Im Zielbild muss sie dafür den Plattformschlüssel
abrufen können, ohne fachliche Ansichten oder Datenprojektionen zu öffnen.

### 1.5 Dokumente und PDF-Artefakte

Der Runtime-Root projiziert aktuell:

```text
<root>/kompetenzmanager.sqlite
<root>/documents/
<root>/exports/
<root>/backups/
<root>/logs/
<root>/security/security.sqlite
<root>/security/enrollment.marker
<root>/app-preferences.json
<root>/restore-staging/...
```

- `student_desktop_adapter.py:1642` kopiert jede importierte Datei mit
  `shutil.copy2` im Klartext nach `documents/<student_id>/...` und schreibt
  anschließend den Datensatz. Datei und DB-Eintrag bilden keine gemeinsame
  atomare Transaktion.
- Alle Dateitypen sind zugelassen (`Alle Dateien (*)`).
- `student_profile_screen.py:2345` übergibt den Klartextpfad über
  `QDesktopServices.openUrl` an ein externes Programm.
- `learning_report_pdf.py:335` und `learning_conference_pdf.py:477` erzeugen
  Klartextdateien mit der Endung `.pdf.tmp`, lesen sie anschließend und ersetzen
  das Ziel.
- `desktop_app/runtime.py:189` kopiert Pilot-DB und Pilotdokumente durch ein
  Klartext-`TemporaryDirectory`; `backup.py:590/879` und `restore.py:228`
  verwenden weitere temporäre Klartextextraktionen. `restore_runtime.py`
  kopiert Live-/Rollbackdateien und schreibt atomare `.tmp`-Statusdateien; die
  Statusdateien sind nicht fachlich, die kopierten DB-/Dokumentpayloads schon.
- Deaktivierte Dokumente werden fachlich ausgeblendet; die verwaltete Datei wird
  nicht automatisch physisch gelöscht.

Damit ist „keine unverschlüsselte temporäre Kopie“ mit der aktuellen externen
Dokumentöffnung nicht vereinbar. Ein beliebiges Fremdprogramm kann keinen
verschlüsselten Kompentra-Container lesen. Es ist eine Produktentscheidung
zwischen einem eingebauten Viewer und einem bewusst ausgelösten Klartext-Export
außerhalb des verwalteten Speichers erforderlich. Letzterer ist keine
temporäre App-Kopie, bleibt aber ausdrücklich ein vom Benutzer verantworteter
Klartextabzug.

### 1.6 Backup, Staging und Restore

- `src/core/backup.py:29-33` definiert `.jkmbackup` v1 als normales ZIP mit
  `manifest.json`, `database/kompetenzmanager.sqlite` und `files/...`.
- `SQLiteBackupEngine.create_snapshot()` (`backup.py:242`) erzeugt mit
  `sqlite3.Connection.backup()` eine temporäre Klartextdatenbank.
- `BackupService.create_backup()` (`backup.py:576`) hält Klartextsnapshot und
  Klartextdateien in temporärem Staging und schreibt sie in das ZIP.
- `BackupVerifier` (`backup.py:852`) extrahiert zur Prüfung erneut Klartext.
- `src/core/restore.py:45` nutzt dauerhaftes `restore-staging`; Quelle,
  vorbereitete DB und Dokumente liegen dort heute im Klartext.
- `src/core/restore_runtime.py` besitzt bereits Journal, Handoff,
  Ein-Datei-`os.replace`, Rollback und Start-Recovery. Diese Zustandsmaschine ist
  wiederverwendbar, ihre Payloads sind jedoch unverschlüsselt.
- Der Restore-Worker erhält die Handoff-Nonce als Prozessargument
  (`src/desktop_app/restore_worker.py:47`). Das ist für zukünftige Secrets oder
  Autorisierungstoken unzulässig.
- Ein Support-Reset erstellt vor dem Sicherheitszustandswechsel über
  `src/application/commands/security_backup.py` ein normales, derzeit
  unverschlüsseltes Backup.

### 1.7 Packaging und Abhängigkeiten

- `requirements-macos-build.txt` pinnt unter anderem PySide6, PyInstaller,
  `argon2-cffi` und `cryptography`; SQLCipher und libsodium/PyNaCl fehlen.
- `packaging/macos_pilot.spec` und `scripts/build_macos_pilot.sh` bauen nur
  macOS arm64. Bei fehlender Developer-ID wird ad hoc signiert und nicht
  notarisiert.
- `scripts/build_macos_support_assistant.sh` schließt `sqlite3` ausdrücklich aus;
  das widerspricht der geforderten Support-Datenbank.
- Es gibt weder Windows-Spec noch Windows-Build-/Signier-/Smoke-Pipeline.

## 2. Datenflussdiagramm in Textform

### 2.0 Isolierter Foundation-Datenfluss

```text
expliziter Entwicklungstest
  -> 32 zufaellige DMK-Bytes + Key-ID
  -> SHA-256-Fingerprint + pending Metadaten im Development-Sidecar
  -> DMK unter Installations-/Key-ID in macOS Keychain schreiben
  -> erst danach active
  -> bei erneutem Service-/Repository-Aufbau aus Keychain laden
  -> Laenge und Fingerprint pruefen
  -> DMK nur fluechtig im aufrufenden Prozess
```

Dieser Ablauf wird nicht beim App-Start ausgeführt und öffnet keine fachliche
SQLite-Datenbank, Dokumente, Backups oder Pilotdaten.

### 2.1 Normaler Betrieb

```text
App-Start
  -> Runtime-Lock
  -> technische Restore-/Migrations-Recovery
       -> PlatformKeyProtector.get(DMK)
       -> nur Cipher-/Integritaetspruefung, keine Fachprojektion
  -> Security Store oeffnen
  -> Passwort / Recovery / Geraeteanmeldung pruefen
  -> authentifizierte Sitzung
  -> DMK aus Keychain/DPAPI beziehen
  -> DB-KEK = HKDF(DMK, keyset_salt, "kompentra/db-wrap/v1")
  -> zufaelligen DB-Key aus Security Store entwrappen
  -> SQLCipher-Verbindung oeffnen und Cipher pruefen
  -> Repositories / ViewModels / UI-Projektionen

Dokumentimport
  -> Quelldatei bewusst gewaehlt
  -> zufaelliger Dokument-DEK
  -> Stream: Klartextquelle -> secretstream -> verschluesseltes Tempziel
  -> fsync -> Container vollstaendig verifizieren -> atomisches os.replace
  -> erst danach DB-Metadaten schreiben

Dokumentanzeige
  -> Container + Key-Wrapping verifizieren
  -> in kontrollierten App-Viewer streamen
  -> kein Klartextpfad und keine Klartexttempdatei
```

### 2.2 Backup und Restore

```text
Backup
  -> zufaelliger BDK
  -> explizit gekeyte SQLCipher-Zielverbindung oder sqlcipher_export
  -> verschluesselte DB-Kopie
  -> vorhandene verschluesselte Dokumentcontainer streamen
  -> Manifest in memory erzeugen und mit BDK verschluesseln
  -> BDK lokal unter DMK-abgeleitetem KEK wrappen
  -> optional: zweites Wrapping unter separatem portablem Backup-Geheimnis
  -> v2-Container in Tempziel -> verifizieren -> fsync -> os.replace

Restore gleiche Installation
  -> oeffentlichen Header strikt pruefen
  -> BDK mit lokalem DMK entwrappen
  -> Manifest authentifizieren
  -> nur Ciphertexte in restore-staging materialisieren
  -> SQLCipher-/Datei-Integritaet pruefen
  -> Journal + atomare Ersetzung + verschluesselter Rollback
  -> Neustart und Recovery bleiben fail-closed

Restore auf neue Installation (nur portable Variante)
  -> separates Backup-Geheimnis eingeben
  -> BDK entwrappen
  -> neue lokale Installation + neuer DMK/DB-Key
  -> Inhalte beim Import auf das neue Keyset umschluesseln
  -> niemals Hersteller- oder Supportschluessel verwenden
```

### 2.3 Support-Reset

```text
Registrierung nach normalem Login
  App: Installationssignatur + Support-Geheimwort-Hash
  -> signierte .jkmregistration
  -> Support-Tool prueft und importiert in eigene verschluesselte DB

Reset-Anfrage auf bestehender Installation
  lokales Geheimwort -> SealedBox(Support-X25519-Public-Key)
  + Request-ID + Nonce + Epoch + Ablauf
  -> Ed25519-Signatur der Installation
  -> .jkmresetrequest

Support-Tool
  -> kanonisch/signiert/registriert/aktuell/einmalig pruefen
  -> Geheimwort nur im Arbeitsspeicher entschluesseln
  -> Argon2id verify -> Speicher bestmoeglich loeschen
  -> registrierte E-Mail anzeigen -> manueller Absendervergleich
  -> Resetdatei mit getrenntem Support-Ed25519-Key signieren

App auf registrierter Installation
  -> offene Anfrage + Nonce + Epoch + Signatur + Ablauf + Einmaligkeit
  -> vorhandenen Installationsschluessel und DMK pruefen
  -> password_reset_pending; neues Passwort und Recovery-Codes erzwingen
  -> Epoch erhoehen; DMK/DB-Key/Dokument-DEKs unveraendert
```

## 3. Bedrohungsmodell

### 3.1 Sprint-2-spezifische Bedrohungen

| Bedrohung | Maßnahme | Verbleibendes Risiko |
|---|---|---|
| falsche Installations- oder Key-ID-Bindung | getrennter Keychain-Service und kanonisches Account-Schema; `not_found` statt Fallback | kopierter Sidecar bleibt als Verfügbarkeitsrisiko sichtbar |
| manipulierte Keyset-Metadaten | striktes Schema, UUID-/Statusprüfung, Fingerprintvergleich und keine automatische DMK-Löschung bei uneindeutiger Abweichung | Sidecar ist nicht vertraulich, nicht kryptografisch authentisiert und nicht rollbackgeschützt; produktive Authentisierung bleibt Pflicht |
| beschädigter oder zu kurzer Keychain-Eintrag | exakte 32-Byte-Prüfung, `failed`, kein stiller Ersatz | Datenzugriff wäre bei späterer Produktnutzung blockiert |
| Keychain verweigert oder temporär nicht verfügbar | getrennte retry-fähige Zustände für `access_denied` und `error` | OS-/Bridge-Ausfall bleibt verfügbarkeitskritisch |
| Plattformlöschung schlägt fehl | zuerst `revoked`, danach wiederholbare Bereinigung über terminale Metadaten | widerrufenes Secret kann bis zum Retry im Keychain verbleiben |
| Secret in Logs, Exceptions oder SQLite | keine Logger-/Printpfade, strukturierte Fehlercodes, `repr=False`, keine DMK-Repository-Parameter | Python garantiert keine vollständige sofortige Speicherlöschung |

| Bedrohung | Sicherheitsziel | Maßnahme | Verbleibendes Risiko |
|---|---|---|---|
| Gestohlener Datenträger oder kopiertes Datenverzeichnis | Keine fachlichen Klartexte | SQLCipher, Dokument-AEAD, DMK im OS-Schlüsselspeicher | Entsperrter Benutzerkontext oder kompromittiertes OS |
| Gestohlenes `.jkmbackup` | Vertraulichkeit und Manipulationsschutz | Zufälliger BDK, verschlüsseltes Manifest, AEAD/SQLCipher, optional portable Hülle | Metadaten des minimalen Außenheaders und Dateigröße |
| Manipulation, Trunkierung, Vertauschung | Fail-closed | AEAD-Tags, `TAG_FINAL`, kanonisches Manifest, IDs in AAD, SQLCipher-Integritätsprüfungen | Verfügbarkeitsverlust bleibt möglich |
| Rollback auf alte DB/Dateien/Epoch | Erkennen oder blockieren | Keyset-/Epoch-Bindung, Journal, Manifest-Digests, monotone Zustände | Vollständiger Offline-Rollback des gesamten App- und Keychain-Zustands ist OS-abhängig |
| Passwort und Recovery-Codes verloren | Reset nur auf registrierter Installation | signierte Anfrage, Support-Geheimwort, DMK-Präsenz, Einmaligkeit | Kein Zugriff ohne ursprünglichen OS-Schlüsselspeicher |
| Gefälschte oder wiederholte Support-Datei | Authentizität, Scope, Freshness | Ed25519, Request-/Nonce-/Token-Bindung, Ablauf, Epoch, Verbrauchstabellen | Kompromittierter Support-Signaturschlüssel |
| Böswilliger Support-Mitarbeiter | Kein Zugriff auf Nutzdaten | Support erhält nie DMK, DB oder Dokumente; Vier-Augen-Prozess möglich | Support kann bei kompromittiertem Signierschlüssel Resetdateien ausstellen, aber nicht Daten entschlüsseln |
| Gestohlene Registrierungsdatei | Begrenzte Offline-Angriffe | starkes separates Geheimwort, Argon2id, minimale Daten | E-Mail, IDs und Hash erlauben Wörterbuchangriffe; Richtlinie und Rate-Limit nötig |
| Support-Tool-Diebstahl | Schutz von E-Mail/Hashes/Schlüsseln | eigene SQLCipher-DB, tool-lokaler Plattformschlüssel, externer verschlüsselter Signier-/Entschlüsselungsschlüssel | Betreiberendpunkt bleibt Hochrisikosystem |
| Prozessargumente, Logs, Crashreports | Keine Secret-Leaks | keine Secrets in argv/env, strukturierte redigierte Fehler, Secret-Scanner | Python kann Speicher nicht garantiert sofort nullen |
| Crash oder Stromausfall | Kein gemischter Klar-/Cipherzustand | Write-verify-fsync-replace, Journal, idempotente Recovery | Mehr Speicherplatz und längere Wartungsfenster |
| Manipulierte native Abhängigkeit | Kein Supply-Chain-Schlüsselabfluss | reproduzierbare Builds, Hashes/SBOM, Signierung, Binärprüfung | Upstream-/Compiler-Risiko |
| Verlorenes/defektes Gerät | Klar definierte Grenze | optionales portables verschlüsseltes Backup | Ohne portables Geheimnis absichtlich keine Wiederherstellung |

Nicht geschützt werden Daten in einem laufenden, entsperrten und kompromittierten
Prozess, Bildschirminhalte, Druckausgaben oder bewusst exportierte Klartextdateien.
„Verschlüsselung im Ruhezustand“ ersetzt keine Endpoint-Sicherheit.

## 4. Empfohlene Kryptografie und Bibliotheken

### 4.1 Verschlüsseltes SQLite

**Empfehlung: SQLCipher Community Edition oder ein offizielles kommerzielles
SQLCipher-Paket, abhängig vom Packaging-Spike.** SQLCipher bietet vollständige
Datenbankverschlüsselung, Seiten-HMAC und dokumentierte Integritätsprüfung. Der
Key muss die erste Operation nach dem Öffnen sein; eine Klartextdatenbank wird
über `sqlcipher_export`, nicht über `rekey`, migriert. Siehe
[SQLCipher API](https://www.zetetic.net/sqlcipher/sqlcipher-api/) und
[SQLCipher Community](https://www.zetetic.net/sqlcipher/community/).

Bewertung:

| Lösung | Bewertung |
|---|---|
| SQLCipher | Bevorzugt: etabliert, cross-platform, Python/SQLite-Modell bleibt weitgehend erhalten. Risiko sind reproduzierbare Python-3.14-Wheels für macOS arm64 und Windows sowie die native Lieferkette. |
| SQLite SEE | Technisch möglich und vom SQLite-Projekt; proprietäre Source-Lizenz, Eigenbuild nötig. SEE unterstützt AES-256-GCM, der Betriebs- und Python-Integrationspfad wäre aber vollständig neu. Die offizielle Produktseite nennt derzeit eine einmalige SEE-Source-Lizenz und Eigenkompilierung: [SQLite Pro Support](https://www.sqlite.org/prosupport.html). |
| SQLite3 Multiple Ciphers | Open-Source-Alternative mit mehreren Ciphers, aber kleinerer Wartungs-/Auditbasis und zusätzlichem Kompatibilitätsrisiko. Nicht erste Wahl für die produktive Sicherheitsbasis. |
| Feldverschlüsselung oder Dateisystemverschlüsselung | Unzureichend: erfüllt weder vollständige DB-Verschlüsselung noch eigenständige Backup-Portabilität und lässt SQLite-Metadaten offen. |

SQLCipher Community ist BSD-artig und verlangt zugängliche Copyright- und
Lizenzhinweise einschließlich abhängiger Komponenten. Offizielle kommerzielle
Pakete enthalten Support und vorkompilierte Komponenten; Details und Kosten
müssen vor Beschaffung geprüft werden. Siehe
[SQLCipher License](https://www.zetetic.net/sqlcipher/license/).

Kein ungeprüftes Drittanbieter-Wheel wird unmittelbar produktiv übernommen.
Der Spike muss die verwendete SQLCipher-Source-Version, SQLite-Version,
Crypto-Provider, Compilerflags, Binärarchitektur und SBOM reproduzierbar
festlegen. Bevorzugt wird ein eigener gepinnter Build oder ein offizielles
Paket.

### 4.2 Dokument- und Streamverschlüsselung

**Empfehlung: libsodium `crypto_secretstream_xchacha20poly1305` über PyNaCl.**
Die API erkennt Änderung, Trunkierung, Entfernung, Duplikation und Umordnung von
Chunks, authentifiziert jeden Chunk, kennzeichnet das Streamende und verwaltet
Nonces/Rekeying intern. Das passt direkt zu großen Dateien und dem Verbot von
Klartexttempdateien. Siehe
[libsodium secretstream](https://doc.libsodium.org/secret-key_cryptography/secretstream).

| Kriterium | AES-256-GCM | XChaCha20-Poly1305 secretstream |
|---|---|---|
| Bibliothek | Bereits vorhandenes `cryptography`/OpenSSL | Neue native Abhängigkeit libsodium/PyNaCl |
| Nonce | 96 Bit, pro Key strikt eindeutig | 192-Bit-Header/Nonce, automatisch verwaltet |
| Große Dateien | Streaming möglich, aber Framing/Finalisierung muss selbst korrekt umgesetzt werden | High-Level-Dateistream-API mit Chunk- und Final-Tags |
| Manipulation | Tag erst nach Finalisierung verlässlich; kein selbst gebautes Chunkformat zulassen | Frühe Chunkprüfung plus Trunkierungs-/Reihenfolgeerkennung |
| Packaging | Geringere Änderung | macOS- und Windows-Wheels/native Bibliothek müssen gepinnt und geprüft werden |
| Empfehlung | Fallback, wenn libsodium-Spike scheitert | Bevorzugt für verwaltete Dateien und Backupströme |

PyNaCl liefert laut seiner
[Installationsdokumentation](https://pynacl.readthedocs.io/en/latest/install/)
Binärwheels für macOS und Windows; dies ist im echten Python-3.14-/PyInstaller-
Build trotzdem zu verifizieren. libsodium steht unter ISC-Lizenz, PyNaCl unter
Apache-2.0; beide Notice-Dateien müssen in die Distribution.

### 4.3 Signaturen, KDF, Passwort-Hashing und Wrapping

- Ed25519 aus `cryptography` bleibt für Installations-, Support- und
  Bestätigungssignaturen.
- HKDF-SHA-256 aus `cryptography` erzeugt ausschließlich zweckgebundene KEKs;
  der `info`-Wert ist feste Protokollsyntax, keine frei zusammengesetzte UI-
  Zeichenfolge. Siehe
  [cryptography HKDF](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#hkdf).
- Zufällige 256-Bit-Objektschlüssel werden mit AES-256 Key Wrap nach RFC 3394
  (`cryptography.hazmat.primitives.keywrap`) unter objektgebundenen KEKs
  verpackt. Dadurch gibt es für das Wrapping keine Nonce-Verwaltung. Die
  Inhalts-AEAD bindet zusätzlich den kanonischen Containerheader.
- Argon2id über das vorhandene `argon2-cffi` bleibt für App-Passwort und
  Support-Geheimwort. Beide erhalten getrennte Policies, Salts und
  Domain-/Formatversionen.
- Vergleiche von Digests, IDs und Nonces verwenden `hmac.compare_digest` oder
  die Verifikation der Kryptobibliothek.
- Das Support-Geheimwort wird mit libsodium Sealed Boxes an einen **separaten
  X25519-Support-Verschlüsselungsschlüssel** verschlüsselt. Sealed Boxes
  verwenden ein ephemeres Senderpaar und authentifizierte Verschlüsselung;
  siehe [libsodium Sealed Boxes](https://doc.libsodium.org/public-key_cryptography/sealed_boxes).
  Der bestehende Ed25519-Supportschlüssel kann und darf nicht dafür verwendet
  werden.

## 5. Schlüsselhierarchie

```text
DMK (32 zufaellige Bytes, pro Installation)
  gespeichert/geschuetzt durch PlatformKeyProtector
  |
  +-- HKDF-SHA256(info="kompentra/db-wrap/v1", keyset_salt)
  |     -> DB-KEK -> wrap(zufaelliger SQLCipher-DB-Key)
  |
  +-- HKDF-SHA256(info="kompentra/document-wrap/v1/<document-id>", keyset_salt)
  |     -> Dokument-KEK -> wrap(zufaelliger Dokument-DEK)
  |
  +-- HKDF-SHA256(info="kompentra/artifact-wrap/v1/<artifact-id>", keyset_salt)
  |     -> Artefakt-KEK -> wrap(zufaelliger PDF-DEK)
  |
  +-- HKDF-SHA256(info="kompentra/backup-wrap/v1/<backup-id>", keyset_salt)
        -> lokaler Backup-KEK -> wrap(zufaelliger BDK)

Getrennt vom DMK:
  Installations-Ed25519-Key -> Signatur Registration/Request/Update
  Support-Ed25519-Key       -> Signatur Reset/ACK
  Support-X25519-Key        -> Entschluesselung Support-Geheimwort
```

Diese hybride Lösung wird gegenüber „ein Schlüssel für alles“ und gegenüber
vollständig unverbundenen Zufallsschlüsseln empfohlen: Ein einziges
plattformgeschütztes Root-Secret vereinfacht Verfügbarkeit und Recovery;
Domain Separation verhindert Zweckvermischung; zufällige Objektkeys erlauben
Rotation und Neuverpackung ohne erneute Inhaltsverschlüsselung.

Regeln:

- DMK, DB-Key, Dokument-DEKs und BDKs werden nie protokolliert, exportiert oder
  an Support übertragen.
- Key-IDs sind nicht geheim, aber streng an Installation, Keyset und Version
  gebunden.
- Das App-Passwort verschlüsselt oder erzeugt den DMK nicht. Passwortwechsel
  verursachen deshalb keine Massenvollverschlüsselung.
- Ein DMK-Wechsel ist ein eigener, journalierter Key-Rotation-Prozess und nicht
  Bestandteil dieses ersten Zielbilds.
- Best-effort-Zeroization wird in nativen Puffern umgesetzt. Python-Objekte
  erlauben keine Garantie vollständiger sofortiger Speicherlöschung; diese
  Grenze ist zu dokumentieren.

## 6. Container- und Dateiformate

Alle Formate verwenden kanonisches UTF-8-JSON für kleine Header/Protokolldateien:
keine Floats, keine Duplikatschlüssel, feste Feldmengen, sortierte Schlüssel,
UTC-Zeit mit `Z`, begrenzte Größen und keine unbekannten Versionen.

### 6.1 Dokumentcontainer `KDOC1`

Empfohlene Binärstruktur:

```text
magic "KDOC1\0"
uint32 header_length
canonical_header_json
secretstream_header (24 bytes)
repeated: uint32 ciphertext_chunk_length + authenticated_chunk
final chunk muss TAG_FINAL tragen
```

Der Header enthält ausschließlich: Formatversion, Crypto-Suite,
Container-/Datensatz-ID, Schlüssel-/Keyset-ID, Wrapping-Algorithmus,
wrapped-DEK, ursprüngliche Größe, Chunkgröße und optional MIME-Klasse. Der
kanonische Headerhash wird als Additional Data an jeden Chunk gebunden.
Originaldateiname, Schüler-ID und Fachmetadaten verbleiben in der verschlüsselten
DB und werden nicht im Außenheader offengelegt.

Neue verwaltete Dateinamen enden auf `.jkmenc`; die Originalendung bleibt nur in
der verschlüsselten DB. Unbekannte Versionen, fehlendes Final-Tag, falsche ID,
unzulässige Chunkgröße oder AEAD-Fehler brechen vor Anzeige ab.

### 6.2 Backupcontainer `.jkmbackup` v2

Ein ZIP kann als reines, strikt begrenztes Transportverzeichnis weiterverwendet
werden, sofern sämtliche sensiblen Mitglieder verschlüsselt sind:

```text
header.json                 # minimal, kanonisch, keine Fachmetadaten
manifest.jkmenc             # unter BDK authentifiziert verschluesselt
database/primary.sqlcipher  # SQLCipher-Snapshot
objects/<opaque-id>.jkmenc  # bestehende verschluesselte Dokumentcontainer
```

`header.json` enthält Format-/Crypto-Version, Backup-ID, lokale BDK-Hülle,
optional portable BDK-Hülle und die für deren Entschlüsselung nötigen
nichtgeheimen KDF-Parameter. Dateinamen und IDs im Archiv sind zufällige
Backup-Objekt-IDs. Das verschlüsselte Manifest bindet vollständige
Memberliste, Reihenfolge-unabhängige Digests, Größen, DB-Schemafingerprint,
Kompatibilitätsversion und fachliche Zählwerte.

ZIP-Pfadtraversal, Kompressionsbomben, Duplikate und unbekannte Member bleiben
wie heute strikt verboten. Die Integrität beruht nicht auf ZIP-CRC, sondern auf
SQLCipher und AEAD/Manifestbindung.

### 6.3 Protokolldateien

Empfohlene Endungen:

- `.jkmregistration` – signierte Support-Registrierung
- `.jkmresetrequest` – signierte, einmalige Reset-Anfrage
- `.jkmreset` – signierte Reset-Datei
- `.jkmsupportupdate` – signierte Geheimwort-/Registrierungsaktualisierung
- `.jkmsupportack` – vom Support signierte Importbestätigung

Die Signatur liegt in einem versionierten Envelope über exakt den kanonischen
Payloadbytes. Parser akzeptieren keine zusätzlichen Felder oder alternativen
Kodierungen.

## 7. Datenbankverschlüsselungskonzept

Ein neuer fachlicher `EncryptedSQLiteConnectionFactory` ersetzt jede direkte
`sqlite3.connect`-Stelle im Produktpfad. Er:

1. fordert einen bereits freigegebenen `DataKeyContext` an;
2. öffnet ausschließlich den gepinnten SQLCipher-Treiber;
3. setzt den rohen 32-Byte-Key als erste DB-Operation;
4. setzt feste Cipher-Parameter, `foreign_keys=ON`, Busy-Timeout und definierte
   Journal-/Sync-Policy;
5. prüft `PRAGMA cipher_status`, `cipher_integrity_check`, den erwarteten
   `user_version` und die Produkt-Schemaidentität;
6. liefert bei fehlendem/falschem Key oder Standard-SQLite-Treiber einen
   spezifischen fail-closed Fehler; es gibt keinen Klartextfallback.

Der Adapter muss nicht nur `sqlite_store.py`, sondern Backup, Restore,
Kompatibilitätsprüfung und Runtime-Seedpfad abdecken. Der Security Store behält
eine getrennte Connection Factory; fachlicher DB-Key und DMK werden niemals in
dieser DB als Klartext gespeichert.

Für WAL/SHM gilt: Entweder SQLCipher-WAL mit gleicher Verschlüsselung und
gesicherter Löschung beim sauberen Shutdown oder zunächst `journal_mode=DELETE`
für den kleineren Migrationsraum. Die konkrete Wahl folgt aus Last-/Crash-Tests;
ein unverschlüsseltes WAL ist eine harte Stopbedingung.

## 8. Dokumentverschlüsselungskonzept

- Ein neuer `ManagedDocumentStore` sitzt im Application-/Infrastructure-Layer;
  Widgets und Dialoge erhalten nur Dokument-IDs und ViewModels, keine
  Repository- oder Cipherlogik.
- Import: Quelldatei lesen, zufälligen DEK erzeugen, `.jkmenc.tmp` im Zielordner
  streamend schreiben, Datei und Verzeichnis `fsync`, vollständige
  Containerprüfung, `os.replace`, anschließend DB-Metadaten. Bei DB-Fehler wird
  der neue Ciphertext als verwaistes Objekt sicher bereinigt oder im Journal
  für Recovery markiert.
- PDF-Renderer schreiben in einen kontrollierten Byte-/Stream-Sink, der direkt
  verschlüsselt. `.pdf.tmp` im Klartext entfällt.
- Anzeige: Unterstützte Typen werden in einem App-Viewer aus entschlüsselten
  Memory-/Streamingdaten dargestellt. Für beliebige Fremdformate ist eine
  bewusste Funktion „Entschlüsselte Kopie exportieren“ mit Warnung,
  Zielauswahl und anschließendem Benutzerbesitz nötig. Automatisches externes
  Öffnen ist unvereinbar mit dem Zielbild.
- Löschen: Fachliche Deaktivierung und physische Aufbewahrung müssen als
  separate Retention-Regel entschieden werden. Kryptografisches Löschen ist
  durch Entfernen des DEK-Wrappings möglich, ersetzt aber keine
  Aufbewahrungsentscheidung.
- Keine Dateivorschau, Thumbnail-Bibliothek, Spotlight-Indexierung oder
  Diagnosefunktion darf Klartext-Caches erzeugen.

## 9. Backup- und Restorekonzept

### 9.1 Lokales Backup

- Jeder Lauf erzeugt einen zufälligen 32-Byte-BDK.
- Eine verschlüsselte Kopie benötigt entweder eine ausdrücklich mit SQLCipher
  geöffnete und gekeyte Zielverbindung oder den dokumentierten
  `sqlcipher_export`-Pfad. Die normale ungekeyte SQLite-Backup-API erzeugt nicht
  automatisch einen verschlüsselten Snapshot und bleibt verboten.
- Bereits verschlüsselte Dokumentcontainer werden unverändert übernommen; das
  Backupmanifest bindet deren Ciphertextdigests.
- Alle neuen temporären/staged Dateien sind Ciphertexte. Entschlüsselte
  Manifeste existieren nur kurz im Speicher.
- Das fertige Archiv wird erneut über den veröffentlichten Pfad verifiziert,
  dann atomar publiziert.

### 9.2 Sichere Portabilität

Das Standardbackup bleibt installationsgebunden: Der BDK ist nur unter einem
DMK-abgeleiteten KEK gewrappt. Für Geräteverlust ist ein **separat
freizugebendes portables Backup-Profil** nötig. Es ergänzt eine zweite BDK-Hülle
unter einem aus einer eigenen Backup-Passphrase per Argon2id abgeleiteten KEK.
Das App-Passwort, Support-Geheimwort und Recovery-Codes werden nicht
wiederverwendet.

Ohne Backup-Passphrase und ohne ursprünglichen Plattformschlüsselspeicher ist
ein solches Backup absichtlich nicht wiederherstellbar. Support besitzt keinen
Ersatzschlüssel. Alternativ kann später ein hochentropischer, einmalig
ausgegebener Backup-Recovery-Key spezifiziert werden; das ist eine eigene
Produktentscheidung.

### 9.3 Restore und Crash-Recovery

- Preview liest nur authentifizierte, datenschutzminimierte Projektionen aus dem
  entschlüsselten Manifest im Speicher.
- Staging enthält SQLCipher-DB und `.jkmenc`-Objekte, nie Klartext.
- Die vorhandene Restore-Zustandsmaschine bleibt Grundlage: locken, preflight,
  safety backup, ersetzen, verifizieren, commit/rollback, Neustart.
- Safety Backup und Rollback sind ebenfalls v2-verschlüsselt.
- Handoff-/Journaldateien enthalten nur IDs, Zustände, Pfade und Ciphertext-
  Digests. Einmalige Autorisierung wird über geerbten File Descriptor oder eine
  mode-`0600`-Handoffdatei unter gehaltenem Lock übergeben, nicht über argv oder
  Environment.
- Restore auf einer neuen Installation ist nur über das portable Profil und
  einen eigenen Onboarding-/Rekey-Prozess erlaubt.

## 10. Migrationsplan für Klartextinstallationen

Die Migration ist eine verpflichtende, blockierende Wartungszustandsmaschine
nach normaler Authentifizierung. Kein Fachbetrieb läuft parallel.

1. **Inventur:** Klartext-DB anhand des SQLite-Headers erkennen, verwaltete
   Dateien/Artefakte, v1-Backups und freien Speicher erfassen; keine Suche
   außerhalb des Runtime-Roots.
2. **Provisionierung:** DMK, Keyset-Salt, zufälligen DB-Key und
   Installationssignaturschlüssel erzeugen; Plattformpersistenz und
   Read-after-write prüfen; nur Wrappings/Metadaten in Security Store schreiben.
3. **Verschlüsseltes Sicherheitsbackup:** Aus der bestehenden Klartextquelle
   direkt ein v2-Backup erzeugen. Es entsteht keine weitere Klartextkopie.
4. **DB-Migration:** Klartextquelle read-only öffnen und mit
   `sqlcipher_export` in eine SQLCipher-Tempzieldatei im selben Dateisystem
   übertragen. Cipher-/SQLite-/FK-Integrität, Schemafingerprint und Zählwerte
   prüfen; Datei und Verzeichnis synchronisieren; atomar ersetzen.
5. **Dokumentmigration:** Jede bestehende Klartextdatei in ein verschlüsseltes
   Tempziel streamen, vollständig verifizieren und atomar ersetzen. Journal
   markiert jedes Objekt unabhängig.
6. **Artefakt-/Pfadupdate:** DB-Pfade auf `.jkmenc` und Storageversion
   aktualisieren; fachliche Identitäten und fachliche Inhalte bleiben gleich.
7. **Verwaltete v1-Backups:** Streamend nach v2 konvertieren und erst nach
   erfolgreicher Verifikation atomar ersetzen. Externe Backups können nicht
   garantiert gefunden oder gelöscht werden.
8. **Abschlussprüfung:** Kein Klartext-SQLite-Header, keine verwaltete
   Klartextdatei, kein v1-Backup, keine `.pdf.tmp`, keine Klartext-Stagingdatei.
9. **Commit des Zustands:** Migration als abgeschlossen markieren; erst dann
   Fachanwendung öffnen.

Crashregeln:

- Vor dem ersten Ersatz ist die alte Installation vollständig nutzbar.
- Ab dem ersten Ersatz ist der App-Start bis zur Recovery blockiert.
- Wiederaufnahme ist idempotent; bereits verifizierte Ciphertexte werden nicht
  erneut erzeugt.
- Es gibt keinen stillen Rückfall auf Klartext. Ein Fehler führt in
  `encryption_migration_recovery_required`.
- Das ursprüngliche Klartextinode wird durch `os.replace` entlinkt. Sichere
  physische Löschung ist auf SSD/APFS/NTFS wegen Copy-on-write/Wear-Leveling
  nicht garantierbar; diese forensische Grenze muss in Datenschutz und Rollout
  dokumentiert werden.

**Offene Bestandsgrenze:** `exports/`, bewusst extern abgelegte PDFs und alte
externe Backups können fachliche Klartexte enthalten. Entweder werden auch
verwaltete Exporte verschlüsselt, oder sie werden ausdrücklich als
benutzerverwaltete Klartextausgaben außerhalb der Schutzgarantie definiert.
Ohne diese Entscheidung darf die Aussage „keine dauerhaften Klartextkopien“
nicht veröffentlicht werden.

## 11. Support-Registrierungsprotokoll

### 11.1 Schlüssel und Vertrauen

- Die Installation besitzt ein neues Ed25519-Schlüsselpaar. Der private Key
  bleibt über den Plattformport geschützt; der öffentliche Key ist
  exportierbar.
- Der Fingerabdruck ist SHA-256 über die kanonische Raw-Public-Key-Darstellung.
- Die erste Registrierung ist Trust-on-first-use im Support-Tool. Eine
  Selbstsignatur beweist Schlüsselbesitz, nicht die reale Identität; deshalb
  bleibt die manuelle E-Mail-/Prozessprüfung erforderlich.
- Support-Signatur- und Support-Verschlüsselungsschlüssel sind getrennt,
  versioniert, rotierbar und widerrufbar.

### 11.2 Datei `KREG-1`

Der signierte Payload enthält ausschließlich die vorgegebenen Inhalte:

- Formatversion
- Konto-ID (bestehende `user_id`, keine neue fachliche Identität)
- Installations-ID
- öffentlicher Ed25519-Installationsschlüssel
- SHA-256-Fingerabdruck
- registrierte E-Mail-Adresse
- Salt und Argon2id-Hash des Support-Geheimworts einschließlich formatgebundener
  Argon2-Parameter
- aktuelle Security-Epoch
- Erstellungszeitpunkt

Die Envelope-Signatur ist die Installationssignatur über die exakten
kanonischen Payloadbytes. Die Formatversion legt Signaturalgorithmus und
Kanonisierung fest, damit keine zusätzlichen persönlichen Felder nötig sind.

Erzeugung ist nur nach normaler Passwort-/Geräteauthentifizierung erlaubt. Das
Geheimwort wird zweimal verdeckt eingegeben, gegen eine eigene Mindestpolicy
geprüft, lokal gehasht und danach verworfen. Datei und Support-Datenbank
enthalten nur Salt/Hash.

### 11.3 Import im Support-Tool

Das Tool prüft Format, Kanonisierung, Fingerabdruck, Selbstsignatur,
ID-Konsistenz, Generation und Duplikate. Es legt eine aktive Registrierung an
oder verlangt einen expliziten, protokollierten Updatepfad. Eine Registrierung
kann `active`, `locked`, `revoked` oder `superseded` sein.

## 12. Reset-Anfrage- und Reset-Dateiprotokoll

### 12.1 Anfrage `KRESETREQ-2`

Payload:

- Format- und Protokollversion
- Konto-ID und Installations-ID
- UUIDv4-Reset-Anfrage-ID
- mindestens 256 Bit zufällige Nonce
- Erstellungs- und kurze Ablaufzeit
- aktuelle Security-Epoch
- Aktion `PASSWORD_RESET`
- `support_encryption_key_id`
- libsodium-Sealed-Box-Ciphertext des lokal eingegebenen Support-Geheimworts

Die Ed25519-Installationssignatur bindet den gesamten kanonischen Payload.
Das Geheimwort erscheint nie im UI nach der Eingabe, in Dateinamen, Logs,
Fehlern, Diagnosepaketen oder DB-Spalten. Die App speichert lokal nur Request-ID,
Nonce, Epoch, Ablauf, Dateidigest und Status.

### 12.2 Prüfung im Support-Tool

Reihenfolge, um Orakel und unnötige Secret-Verarbeitung zu minimieren:

1. Größenlimit, exakte Felder, Version, kanonische Bytes.
2. Aktive Registrierung und ID-/Public-Key-Bindung.
3. Installationssignatur.
4. Gültigkeitszeit mit definierter Uhrtoleranz.
5. Request-ID-/Nonce-Einmaligkeit und Sperr-/Widerrufsstatus.
6. Exakte Security-Epoch.
7. Sealed Box mit passendem X25519-Private-Key entschlüsseln.
8. Argon2id-Verifikation gegen registrierten Hash.
9. Klartextpuffer bestmöglich löschen; kein Persistieren, kein Anzeigen.
10. Registrierte E-Mail-Adresse anzeigen; Support vergleicht den tatsächlichen
    Mailabsender manuell und dokumentiert nur das Ergebnis.

Fehlerausgaben bleiben absichtlich grob (`Anfrage nicht freigegeben`) und
verraten weder Registrierungsexistenz noch Geheimworttreffer.

### 12.3 Resetdatei `KRESET-2`

Der Payload enthält:

- Format-/Protokollversion
- Konto-ID und Installations-ID
- ursprüngliche Anfrage-ID und Nonce
- Aktion `PASSWORD_RESET`
- Ausstellungs- und Ablaufzeit
- einmalige Token-ID
- erwartete alte Security-Epoch
- exakt alte Epoch + 1 als neue Epoch
- Support-`key_id`

Der Support-Ed25519-Key signiert die kanonischen Bytes. Das Support-Tool schreibt
Ausstellung und Token-ID atomar in seine DB, bevor die Datei veröffentlicht
wird.

Die App akzeptiert nur bei exakter Installation, aktiver passender Anfrage,
gültiger Supportsignatur/Key-Registry, Zeitfenster, unveränderter alter Epoch,
noch nie verbrauchter Token-ID sowie lesbarem DMK und lokalem
Installationsprivatekey. Vor dem Zustandswechsel wird ein verschlüsseltes,
verifiziertes v2-Sicherheitsbackup erstellt.

Eine einzige Security-Store-Transaktion:

- verbraucht Anfrage, Nonce und Token,
- widerruft alle anderen offenen Anfragen,
- widerruft Recovery-Codes und Gerätecredentials,
- setzt `password_reset_pending`,
- setzt die Epoch exakt auf die signierte neue Generation.

Danach sind neues App-Passwort und neue Recovery-Codes zwingend. DMK, DB-Key und
Objektkeys bleiben unverändert. Fehlt der Plattformschlüssel, ist der Reset
wirkungslos und die Datei bleibt fachlich unbrauchbar; Support kann die Daten
nicht wiederherstellen.

## 13. Geheimwort-Aktualisierungsprotokoll

### 13.1 Aktualisierung

Nur nach normaler erfolgreicher Authentifizierung erzeugt die App:

- Update-ID
- Konto-/Installations-ID
- alte und neue Security-Epoch
- neues Salt und neuen Argon2id-Hash
- Zeitpunkt
- Installationssignatur

Datei: `.jkmsupportupdate`, Format `KSUPPORTUPDATE-1`. Die App speichert lokal
den neuen Hash nur als **pending registration state**; das alte Geheimwort muss
nicht im Klartext oder als zusätzlicher App-Hash aufbewahrt werden. Das
Support-Tool hält den bisher registrierten Hash aktiv, bis es die Datei
erfolgreich und atomar importiert.

Währenddessen zeigt die App verbindlich:

> Die Support-Registrierung wurde noch nicht aktualisiert. Für einen
> Support-Reset gilt weiterhin das bisher registrierte Geheimwort.

Eine zweite Geheimwortänderung, ein neuer Registrierungsupdate und die Erzeugung
einer Reset-Anfrage sind während eines offenen Updates zu blockieren. Normale
Passwort-/Recovery-Änderungen erhöhen heute ebenfalls die Epoch. Deshalb muss
jeder solche Epochwechsel eine bestehende Support-Registrierung als `stale`
markieren und einen signierten Epoch-Synchronisationspfad verlangen; andernfalls
würde die Support-DB eine alte Generation akzeptieren.

### 13.2 Offline-Bestätigung

Nach erfolgreichem Import erzeugt das Support-Tool eine
`.jkmsupportack`-Datei mit:

- Format-/Protokollversion
- Aktion `SUPPORT_SECRET_UPDATE_ACK`
- Konto-/Installations-ID
- Update-ID und SHA-256-Digest der exakten Update-Datei
- alte und neue Security-Epoch
- Importzeitpunkt
- Support-Signatur-`key_id`
- Support-Ed25519-Signatur

Die App akzeptiert sie nur für den exakt offenen Update-Digest und die lokale
neue Epoch, verbraucht sie einmalig und setzt den lokalen Status auf
`support_registration_current`. Erst dann verschwindet der Warnhinweis.

Der Support-Import und die ACK-Erzeugung sind idempotent: Geht die ACK-Datei
verloren, darf das Tool dieselbe inhaltlich gebundene Bestätigung erneut
exportieren, ohne den Hash nochmals zu wechseln. Nach dem atomaren Import ist
im Support-Tool nur das neue Geheimwort gültig, auch wenn die App mangels ACK
noch warnt.

## 14. Sicherheits- und Fehlerzustände

| Zustand | Verhalten |
|---|---|
| `key_provisioning_required` | Nur geführte Erzeugung nach Authentifizierung; keine Fach-DB öffnen |
| `key_unavailable` | Fail-closed; Recovery/Supporthinweis, kein Klartextfallback |
| `key_access_denied` | Erneute OS-Freigabe möglich; fachliche Daten bleiben geschlossen |
| `encrypted_ready` | Normaler Betrieb nach Authentifizierung |
| `plaintext_migration_required` | Fachbetrieb blockiert; nur Migration oder Beenden |
| `plaintext_migration_in_progress` | Journalierte Wiederaufnahme, keine normale UI |
| `encryption_migration_recovery_required` | Technische Recovery; keine automatische Löschung |
| `ciphertext_tampered` | Quarantäne/Fehlermeldung, niemals Teilinhalt anzeigen |
| `unsupported_crypto_version` | Update erforderlich, kein Fallback |
| `restore_recovery_required` | Vor Login weiterführen oder kontrolliert rollbacken |
| `restore_manual_recovery_required` | Daten unverändert lassen; Supportdiagnose ohne Secrets |
| `password_reset_pending` | Nur neues Passwort + neue Recovery-Codes; DMK unverändert |
| `support_registration_missing` | Kein Support-Reset; lokale Recovery bleibt möglich |
| `support_registration_current` | Anfrage darf erzeugt werden |
| `support_registration_stale` | Epoch/Registrierung synchronisieren; keine Anfrage |
| `support_registration_update_pending` | Pflichtwarnung; keine weitere Änderung/Anfrage |
| `support_request_active` | Genau eine offene Anfrage; neue widerruft alte bewusst |
| `support_registration_revoked/locked` | Support-Tool lehnt neutral ab |

### 14.1 Wirkung zentraler Benutzer- und Recovery-Aktionen

| Aktion/Ereignis | Authentifizierungszustand | Datenschlüssel | Fachliche Ciphertexte | Support-Registrierung |
|---|---|---|---|---|
| normaler Passwortwechsel | neuer Argon2id-Hash, Epoch + 1, Gerätecredentials widerrufen | unverändert | unverändert | wegen Epochwechsel `stale`, signiert synchronisieren |
| Recovery-Code verbraucht | `password_reset_pending`, Epoch + 1; danach neues Passwort und neue Codes | unverändert, muss lokal lesbar sein | unverändert | `stale`; offene Requests widerrufen |
| Support-Reset | `password_reset_pending`, signierte alte/neue Epoch; neue Codes zwingend | unverändert, muss lokal lesbar sein | unverändert | alte Registrierungsgeneration verbraucht; anschließend aktualisieren |
| lokaler Restore v2 | bestehende lokale Authentifizierung bleibt maßgeblich | lokaler DMK; Backup-BDK nur kurz im Speicher | verschlüsselte DB/Objekte atomar ersetzt | Security Store wird nicht aus Fachbackup überschrieben |
| portabler Restore auf neuem Gerät | neues lokales Konto/Onboarding nach eigener Spezifikation | neuer DMK; BDK über Backup-Passphrase; Inhalte werden umgeschlüsselt | neues lokales Keyset | neue Installation muss neu registriert werden |
| OS-Keychain/DPAPI verloren oder ursprüngliches Gerät zerstört | Passwort/Recovery allein reichen nicht | nicht verfügbar | kryptografisch nicht wiederherstellbar | Support-Reset hilft nicht; nur separat portables Backup kann retten |
| App-Passwort und Recovery verloren, DMK lokal vorhanden | Anmeldung blockiert | weiterhin lokal vorhanden, aber nicht an Support übertragbar | unverändert | registrierungsgebundener Support-Reset kann Passwortreset freigeben |

## 15. Genaue Änderungsliste nach Modulen und Dateien

Dies ist eine Planliste, keine Freigabe zur Änderung.

### 15.1 Neue Module

- `src/security/data_keys.py`: Keyset-Domain, DMK-Lifecycle, Key-Wrapping,
  Rotationstatus.
- `src/security/installation_identity.py`: Ed25519-Installationsidentität.
- `src/security/support_registration.py`: Registration, Request, Update und ACK;
  kanonische Formate und Zustandsregeln.
- `src/security/infrastructure/platform_keys.py`: gemeinsamer
  `PlatformKeyProtector`, macOS-/Windows-Factory.
- `src/security/infrastructure/windows_dpapi.py`: user-scope DPAPI-Adapter.
- `src/core/encrypted_sqlite.py`: SQLCipher Connection Factory und
  Integritätschecks.
- `src/core/encrypted_files.py`: `KDOC1`, secretstream, Wrapping und atomare
  Dateioperationen.
- `src/core/encryption_migration.py`: Inventur, Journal und Klartextmigration.
- `src/support_assistant/sqlite_repository.py`: eigene verschlüsselte
  Support-Datenbank.
- `src/support_assistant/registration_protocol.py`: Import, Revocation,
  Requestprüfung, Update und ACK.

### 15.2 Zu ändernde Produktmodule

- `src/security/ports.py`, `domain.py`, `application.py`, `startup.py`,
  `session.py`: neue Ports, Zustände und Epoch-/Registration-Lifecycle.
- `src/security/infrastructure/sqlite_repository.py`: Security-Schema v4+,
  Keyset-/Registrierungs-/Migrationsmetadaten.
- `src/security/infrastructure/macos_security_bridge.m` und der isolierte
  `data_master_key_store.py`: eigener nicht synchronisierender Keychain-
  Namespace für den DMK; ein späterer Installationsprivatekey braucht eine
  eigene Entscheidung. `platform_auth.py` und Gerätecredential bleiben vom
  Foundation-Importpfad getrennt.
- `src/security/support_reset.py`: Protokoll v2, Epoch, Installationssignatur,
  Datei statt Tokenstring.
- `src/core/sqlite_store.py`: SQLCipher Factory; keine direkte
  Standard-SQLite-Verbindung.
- `src/core/database_compatibility.py`: keyed Kompatibilitätsprüfung.
- `src/desktop_app/runtime.py`: verschlüsselter Seed-/Pilotimport und
  Key-Kontext.
- `src/desktop_app/main.py`: Key-Provisionierung/Migrations-Recovery vor
  fachlichem Öffnen.
- `src/desktop_app/adapters/student_desktop_adapter.py`: ausschließlich
  `ManagedDocumentStore`, keine `copy2`-Dateilogik.
- `src/desktop_app/screens/student_profile_screen.py`: interner Viewer oder
  bewusster Export; kein `QDesktopServices` auf verwaltete Ciphertexte.
- `src/core/learning_report_pdf.py` und
  `src/core/learning_conference_pdf.py`: direkter verschlüsselnder Sink.
- `src/core/backup.py`: v2-Container, SQLCipher-Snapshot,
  Ciphertextverifikation.
- `src/core/restore.py`, `restore_runtime.py` und
  `src/desktop_app/restore_worker.py`: ausschließlich verschlüsseltes Staging,
  geheime Handoffwerte nicht in argv.
- `src/application/commands/security_backup.py`: verschlüsseltes v2-Backup als
  Reset-Voraussetzung.
- `src/desktop_app/security_controller.py`, `security_ui.py`: Registrierung,
  Requestdatei, Resetdatei, Geheimwortupdate und ACK-Status.
- `src/support_assistant/application.py`, `ui.py` und
  `support_tools/support_assistant_app.py`: Registrierungs-DB, automatische
  Prüfungen, E-Mail-Abgleich, Resetdatei, Update/ACK; Secret-redigierte UI.

### 15.3 Build, Skripte und Tests

- `requirements.txt`, `requirements-macos-build.txt`: gepinnter SQLCipher-
  Treiber und PyNaCl/libsodium nach Spike.
- `packaging/macos_pilot.spec`, `scripts/build_macos_pilot.sh`,
  `scripts/build_macos_security_bridge.sh`: native Binaries, SBOM, Signatur,
  Cipher-Smoke.
- `scripts/build_macos_support_assistant.sh`: `sqlite3`-Ausschluss entfernen,
  Support-DB/Key-Bridge einbetten und prüfen.
- Neue Windows-Specs, Buildskripte, Signierung und DPAPI-Smokes; nicht bloß ein
  Plattformbranch im Code.
- `scripts/prepare_macos_pilot_payload.py`, Pilot-/Backup-Builder und
  `scripts/smoke_test_macos_app.py`: nur verschlüsselte Seeds/Backups.
- Bestehende Backup-, Restore-, Security-, Support-, PDF-, Adapter- und Runtime-
  Tests sowie neue Kryptografie-/Migrations-/Leaktests.

## 16. Notwendige Schemamigrationen

**Security-Sprint-2-Grenze:** Dieser Sprint führt keine der nachfolgend
voranalysierten Migrationen aus. Insbesondere gibt es keine Änderung von
`security.sqlite` v3 auf v4 und keinen Zugriff auf bestehende oder Pilot-Stores.
Der neue Metadaten-Sidecar ist eine isolierte Entwicklungsquelle, keine
Entscheidung für die spätere Produktarchitektur.

### 16.1 Security Store v4+

Empfohlene neue Tabellen beziehungsweise Erweiterungen:

- `data_keysets`: Keyset-ID, Konto-/Installationsbindung, Version, Salt,
  Plattformreferenz oder DPAPI-Blob, gewrappter DB-Key, Status,
  created/activated/retired.
- `installation_signing_keys`: Public Key, Fingerabdruck, Plattformreferenz,
  Status und Zeiten; kein privater Klartextkey.
- `support_registrations`: E-Mail, aktuelle/pending Generation,
  Registration-/Update-Digests, Status und Zeiten.
- `encryption_migrations`: Migrations-ID, Phase, Objektcursor, Digests,
  Fehlerklasse, Zeiten; keine Secrets und keine Fachinhalte.
- Erweiterung `support_reset_requests`: Protokollversion, Epoch,
  `support_encryption_key_id`, Requestdateidigest und eindeutige Nonce.
- Erweiterung `support_reset_token_uses`: Token-ID, erwartete/neue Epoch,
  ursprüngliche Request-/Nonce-Bindung und Dateidigest.

Die heutige Registry-Regel „keine E-Mail im Security Store“ muss vor dieser
Migration ausdrücklich geändert werden. Alternativ bleibt die E-Mail nur in
der exportierten Registrierung und ein lokaler Digest/Status wird gespeichert;
für Update-UX und erneuten Export ist die lokale Speicherung nach Login jedoch
praktischer.

### 16.2 Fachliche DB

Keine pädagogische Tabelle oder fachliche Identität muss geändert werden.
Empfohlen sind nur Storage-Metadaten:

- `documents`: `storage_format_version`, `ciphertext_sha256`,
  `ciphertext_size_bytes`, optional `keyset_id`.
- `learning_report_pdf_artifacts` und `learning_conference_pdf_artifacts`:
  dieselben Storagefelder; bestehende fachliche PDF-Hashinvariante bleibt in
  der verschlüsselten DB erhalten.
- Pfadwerte zeigen auf `.jkmenc` statt Klartextdateien.

Eine Alternative ist eine zentrale `managed_file_storage`-Tabelle. Diese darf
aber nicht zur zweiten fachlichen Wahrheit werden. Die endgültige Variante ist
im Datenmodell-Review zu entscheiden.

### 16.3 Support-Tool-Datenbank

- `registrations`: IDs, Public Key/Fingerprint, E-Mail, Secret-Salt/-Hash,
  Generation, Status, Datei-Digest, Zeiten.
- `registration_events`: Import, Update, Lock, Revoke, Supersede.
- `reset_requests`: Request-ID, Nonce/Digest, Generation, Ergebnisstatus,
  Zeiten; kein entschlüsseltes Geheimwort und vorzugsweise kein Requestfile.
- `issued_reset_tokens`: Token-ID, Requestbindung, alte/neue Generation,
  Signatur-Key-ID, Status.
- `support_secret_updates`: Update-/ACK-Digest und idempotenter Importstatus.
- `audit_events`: minimale technische Events ohne E-Mail, Geheimwort,
  Ciphertext oder Dateipfade.

Diese DB wird selbst mit SQLCipher und einem **eigenen** tool-lokalen
Plattformschlüssel geschützt. Sie teilt keinen Key mit der Kompentra-App.

## 17. Testmatrix

| Ebene | Pflichtfälle |
|---|---|
| Kryptografie | Referenzvektoren, HKDF-Domain-Separation, Key-Wrap roundtrip/Fehler, secretstream Änderung/Trunkierung/Umordnung/Duplikat/fehlendes Final, Zufallsquellen |
| SQLCipher | korrekter/falscher/fehlender Key, Standard-SQLite versehentlich geladen, Cipherstatus, Integrity/FK, WAL/SHM, explizit gekeytes Ziel beziehungsweise `sqlcipher_export`, Concurrent Reads/Writes |
| Plattformkeys | Keychain Create/Read/Delete/ACL/gesperrt/gelöscht; DPAPI user scope, anderer Benutzer, anderes Gerät, beschädigter Blob; keine LocalMachine-Nutzung |
| Dokumente | Import aller Größen einschließlich 0 Byte, Crash vor/nach replace/DB-Write, falsche ID/AAD, Viewer, bewusster Export, Löschen/Retention, kein Klartexttemp |
| PDFs | Bericht/LEG deterministisch aus Revision, direkter Cipher-Sink, Hash-/Artefaktinvariante, kein `.pdf.tmp` |
| Backup v2 | deterministischer kanonischer Header, verschlüsseltes Manifest, manipulierte Member, Duplikate, Bombenlimits, lokale/portable Hülle, falsche Passphrase, veröffentlichtes Archiv erneut verifiziert |
| Restore | Preview, gleiche Installation, neue Installation portable, falscher DMK, Crash-/Kill-Injection in jeder Journalphase, Rollback, Safety Backup, freier Speicher, Neustart vor Login |
| Migration | echte v1-/Pilotdaten, leere/große DB, jedes Objekt Crashpunkt, idempotentes Resume, Pfade/Counts/Hashes, v1-Backup-Konvertierung, kein Klartextartefakt nach Abschluss |
| Registrierung | kanonisch, zusätzliche/fehlende Felder, falscher Fingerprint, falsche Signatur, TOFU-Duplikat, revoked/locked, E-Mail-Grenzen |
| Anfrage | Secret nicht sichtbar/persistiert, falscher X25519-Key, Ablauf/Uhrabweichung, Request-/Nonce-Replay, Epoch mismatch, Argon2 falsch, neutrale Fehler |
| Reset | falsche Installation/Request/Nonce/Token/Key-ID, abgelaufen, doppelt, DMK fehlt, Keychain verweigert, atomarer Epochwechsel, neues Passwort/Recovery zwingend |
| Update/ACK | altes Secret bis Import, neues ab Import, verlorene/idempotente ACK, falscher Digest/Epoch, zweites Update blockiert, Pflichtwarnung |
| Datenschutz | Log-/Crash-/Diagnose-/DB-/argv-/env-Scanner für Passwörter, Secret, Keys und Schülerdaten; Supportpaket enthält keine Appdaten |
| Packaging | macOS arm64 clean build, Codesign/Notarisierung, native Architekturen/RPATH, Lizenznotices/SBOM; Windows x64 clean build, Authenticode, DPAPI; Offlineinstallation |
| Pilot/Regression | vorhandene fachliche Tests gegen SQLCipher, leerer Erststart, Laura-Testdaten nur verschlüsselt, Backup-/Restore-E2E, Update von letzter freigegebener Version |

Zusätzlicher Freigabegate: Ein automatisierter Artefaktscan sucht in Runtime,
Build, DMG/Installer und Testausgaben nach `SQLite format 3`, bekannten
Pilot-Schülerstrings, Secret-Fixtures, `.pdf.tmp`, Klartextmanifesten und
unverschlüsselten v1-Backups. Erwartete Testfixtures müssen eng allowlisted sein.

## 18. Packaging-, Lizenz- und Distributionsrisiken

### 18.1 macOS arm64

- SQLCipher und libsodium müssen arm64 sein und korrekt in PyInstaller
  gesammelt werden; keine zweite Standard-SQLite-Bibliothek darf den
  Produktpfad bedienen.
- Keychain-ACLs hängen an stabiler App-Identität/Signatur. Ad-hoc-Signierung ist
  für eine belastbare Schlüsselverfügbarkeit über Updates nicht ausreichend.
  Developer-ID, Hardened Runtime und Notarisierung sind vor breitem Rollout
  Freigabegates.
- RPATH, dylib-Signaturen, Mindest-macOS und Upgrade von 0.2.2 müssen auf einem
  sauberen arm64-Rechner geprüft werden.

### 18.2 Windows

- Es gibt noch keinen Buildpfad. Erforderlich sind mindestens Windows x64,
  PyInstaller-Spec, gepinnte DLLs, Authenticode, Installer/Upgrade und reale
  DPAPI-Smokes.
- DPAPI wird mit aktuellem Benutzerkontext und optionaler Entropy verwendet;
  `CRYPTPROTECT_LOCAL_MACHINE` ist ausgeschlossen, weil dadurch andere Benutzer
  desselben Rechners entschlüsseln könnten. Siehe
  [Microsoft CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).
- Domänenprofile, Passwortreset des Windows-Kontos und roaming profiles müssen
  praktisch getestet werden; die Produktgarantie darf nicht über das getestete
  Verhalten hinausgehen.

### 18.3 Lizenzen und Supply Chain

- SQLCipher Community: BSD-artige Attribution und Notices für SQLite/OpenSSL;
  kommerzielles Paket: Vertrags-/Laufzeit-/Redistributionsprüfung.
- libsodium: ISC; PyNaCl: Apache-2.0; `cryptography`: Apache-2.0/BSD;
  sämtliche Notices in App und Support-Tool.
- Kryptografie kann Exportkontroll-/Store-Erklärungen auslösen; juristische
  Distributionsprüfung ist vor internationalem Vertrieb erforderlich.
- Native Wheels sind nicht allein wegen PyPI-Verfügbarkeit vertrauenswürdig.
  Hash-pinned Lockfile, Herkunft, CVE-Prozess, SBOM, reproduzierbarer Clean Build
  und Binärarchitekturprüfung sind Pflicht.

## 19. Umsetzungssprints, Abhängigkeiten und Aufwand

Security Sprint 2 bis 5 implementieren isolierte, nicht aktivierte Teilmengen
von E0 bis E3: DMK/Keyset, expliziten SQLCipher-Provider, synthetischen
Migrationsprototyp sowie Database-Key-Envelope und technisches Journal. Alle
produktiven Sprints, Startup-/Dateiaustausch- und Rolloutabhängigkeiten bleiben
unverändert Voranalyse.

Schätzung in Netto-Personenwochen einschließlich Implementierung, Reviews,
Tests und Dokumentation; Beschaffung, externe Kryptoprüfung und Wartezeiten
sind nicht enthalten.

| Sprint | Inhalt | Abhängigkeit | Aufwand |
|---|---|---|---:|
| E0 | SQLCipher-/PyNaCl-/Keychain-/DPAPI-/PyInstaller-Spikes, Lizenzentscheidung | keine | 3-5 |
| E1 | Protokoll-, Container-, Bedrohungsmodell- und Governance-Freeze | E0 | 2-3 |
| E2 | PlatformKeyProtector, DMK/Keyset, Installationsidentität | E1 | 4-6 |
| E3 | Zentrale SQLCipher Factory, Startup, Repositories, DB-Backup | E2 | 4-6 |
| E4 | ManagedDocumentStore, PDF-Sink, Viewer/Exportentscheidung | E2 | 5-8 |
| E5 | Backupformat v2 und Verifier | E3, E4 | 4-6 |
| E6 | Verschlüsseltes Restore/Staging/Journal/Worker | E5 | 5-8 |
| E7 | Klartextmigration einschließlich v1-Backups | E3-E6 | 5-7 |
| E8 | Registrierung und verschlüsselte Support-DB | E1, E2 | 4-6 |
| E9 | Request-/Resetprotokoll und App-/Support-UI | E8, E5 | 4-6 |
| E10 | Geheimwortupdate/ACK, Revocation und Datenschutzbetrieb | E8, E9 | 3-4 |
| E11 | macOS-/Windows-Packaging, Leak-/Crashmatrix, Pilotmigration | alle | 5-8 |

Gesamt: **48-73 Personenwochen**. Ein erfahrener Einzelentwickler benötigt bei
serieller Umsetzung grob 12-18 Kalendermonate. Zwei bis drei Personen können
nach E1/E2 DB/Datei/Support parallelisieren, aber Migration, Restore und Release
bleiben stark gekoppelt. Für einen sicherheitskritischen Produktpfad ist eine
unabhängige Kryptografie-/Protokollprüfung zusätzlich einzuplanen.

## 20. Stopbedingungen und notwendige Governance-Änderungen

Die Foundations heben keine Stopbedingung für Produktverschlüsselung oder
Rollout auf. Produktive SQLCipher-Aktivierung, Dateiverschlüsselung, Backup v2,
Migration, Startupintegration, Windows-DPAPI, Produkt-Packaging und
Pilotmigration bleiben gesperrt.

### 20.1 Harte Stopbedingungen

Keine Implementierung beziehungsweise kein produktiver Rollout, solange eine
der folgenden Bedingungen gilt:

1. Kein reproduzierbarer, gepinnter SQLCipher-Build für macOS arm64 und das
   definierte Windows-Ziel.
2. Nicht ausgeschlossen, dass Standard-`sqlite3`, WAL, Backup, Restore, PDF-
   Renderer oder Dokumentöffnung Klartextkopien erzeugen.
3. Keine belastbare Keychain-Verfügbarkeit über signierte App-Updates oder kein
   real getesteter DPAPI-user-scope-Pfad.
4. Keine Produktentscheidung für beliebige Fremddokumente und bewusste
   Klartextexporte.
5. Keine Produktentscheidung, ob und wie portable Backups Geräteverlust
   abdecken.
6. Keine inventarisierte Regel für vorhandene `exports/` und externe v1-
   Backups; daher keine ehrliche „kein Klartext“-Garantie.
7. Container- und Supportprotokolle nicht extern oder unabhängig fachlich
   geprüft.
8. Crash-Injection zeigt einen nicht idempotent recoverbaren Mischzustand.
9. Support-Datenbank ohne Retention-, Lösch-, Zugriffs-, Backup- und
   Incident-Regel.
10. Support-Signing- und X25519-Decryptionschlüssel nicht organisatorisch
    getrennt, rotierbar und außerhalb des App-Repositories geschützt.
11. Secrets gelangen in argv, Environment, Logs, Fehler, Diagnosepakete,
    Zwischenablage oder Support-DB-Felder.
12. Kein erfolgreicher Upgrade-/Migrationspilot mit einer Kopie der letzten
    freigegebenen realistischen Pilotdaten.

### 20.2 Vor Implementierung anzupassende Governance

Gemäß Projektregeln ist die folgende Reihenfolge verbindlich:

1. `docs/PROJECT_CONSTITUTION.md`: bisherige Grenze „App-Sperre, keine
   Verschlüsselung“ ersetzen; Schutz-/Nichtschutzgrenzen festlegen.
2. `docs/TECHNICAL_NAMES.md`: DMK, Keyset, Containerformate, Protokolldateien,
   Supportstatus, Plattformports und Migrationstechniken aufnehmen.
3. `docs/DATA_REGISTRY.md`: verschlüsselte DB/Dateien/Backups, Key-Wrappings,
   Support-E-Mail/-Hash, Support-DB und Retention registrieren.
4. `docs/DATA_LIFECYCLE.md`: Key-Provisionierung, Import/Anzeige/Export,
   Backup/Restore, Migration, Registration/Reset/Update/ACK und Geräteverlust.
5. `docs/VIEW_DATA_OWNERSHIP.md`: interner Dokumentviewer,
   Registrierungs-/Reset-/Updateflächen und Support-Tool-Ansichten.
6. `docs/UI_DATA_MAPPING.md`: neue sichtbare Zustände, Warntexte, Dateiaktionen
   und Fehlerprojektionen.
7. `docs/DESIGN_SYSTEM.md`: nur falls neue sicherheitskritische Status-/Dialog-
   Muster tatsächlich nötig werden.
8. `DECISIONS.md`: neue ADRs mindestens für Encryption-at-rest, Key-Hierarchie,
   SQLCipher, Dateicontainer, Backupportabilität, Supportprotokoll und
   Migrations-/Klartextgrenzen. ADR-059, -064, -065, -068 und -069 werden
   ausdrücklich abgelöst oder ergänzt, nicht still überschrieben.
9. `PROJECT.md`, `SPRINTS.md`, `ROADMAP.md`, `BACKLOG.md` und `CHANGELOG.md`:
   freigegebene Produktentscheidung, Reihenfolge, Risiken und Releasegrenzen.

Diese Voranalyse stellt ADR-075 bis ADR-080 und die isolierten Security-
Foundations der Sprints 2 bis 5 als umgesetzt dar. Keine der beschriebenen
Produktaktivierungen, Live-Migrationen oder Releaseentscheidungen ist
umgesetzt.
