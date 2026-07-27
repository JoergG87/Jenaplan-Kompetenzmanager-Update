# Release- und Sicherheitsbasis 0.3.0 / Build 302

Stand: 27. Juli 2026  
Branch: `spike/python-gui`  
Ausgangs-HEAD: `0a58dbee78742bc5fd134e28fa4516132293f0e4`  
Entscheidung: **NO-GO für Buildartefakt, Übergabe und Release; GO nur für die
Dokumentationsbasis und die zentrale Versionierung.**

## 1. Zweck und Geltung

Dieses Dokument trennt die dokumentierte Produktbasis von einem späteren
Buildnachweis. Es belegt weder ein erzeugtes DMG noch eine Signatur,
Prüfsumme, einen Produkt-Commit, eine Pilotübergabe oder einen veröffentlichten
Updatefeed. Diese Artefakte werden erst nach einem späteren Clean-Build
ergänzt.

Die verbindliche nutzerverständliche Beschreibung steht in
`SICHERHEIT_UND_VERSCHLUESSELUNG.md`; dieses Dokument ist die interne
Release- und Abnahmegrenze.

## 2. Dokumentierte Produktwahrheit

| Punkt | Stand für Build 302 |
|---|---|
| Version / Plattform | 0.3.0, macOS auf Apple Silicon (arm64), mindestens macOS 13 |
| Produktform | lokale Desktop-App, vorgesehene DMG-Installation |
| Signatur / Notarisierung | für einen internen Build ad-hoc signiert erwartet; nicht notarisiert |
| Freigabe | kein Windows, kein öffentlicher Stable-Release, kein Stable-Appcast |
| Datenübertragung | keine Cloud, keine KI-Einbindung |
| Normaler Datenpfad | lokale SQLite-Fachdaten, verwaltete Dokumente/PDFs, ZIP-v1-Backup und Restore |
| Bedienung | Authentifizierung, Keychain, optionales Touch ID, Sperre, Support-Reset, Dashboard, Stundenplan, Schüler-/Kursverwaltung, Beobachtungen, Cockpit, Berichte, LEG und PDF-Ausgaben |
| Restore | Vorschau und ausdrückliche Bestätigung, separater Worker, vollständiges App-Ende, kontrollierter Neustart; fehlender Worker belässt den aktiven Bestand unverändert |

## 3. Aktive Schutzgrenzen

- Das lokale Passwort, Recovery-Codes und der lokale Security Store schützen
  den Zugang zur App. Eine gespeicherte Geräteanmeldung liegt im macOS-
  Schlüsselbund; Touch ID ist optional und das Passwort bleibt Fallback.
- Die App sperrt automatisch. Support-Reset ist ein lokal gebundener,
  beaufsichtigter Ausnahmeweg und ersetzt weder den DMK noch Datenkeys.
- ZIP-v1-Backups und ihre Restore-Vorschau werden geprüft. Ein Restore wird
  erst nach erfolgreicher Prüfung und expliziter Bestätigung wirksam.
- Lokale Datenroots und verwaltete Dateien bleiben getrennt vom App-Bundle.
  Freie Exportdateien und PDFs liegen außerhalb der App als Dateien vor und
  müssen organisatorisch geschützt weitergegeben werden.

Diese Grenzen sind keine Aussage „DSGVO-konform“, keine Verschlüsselung aktiver
Fachdaten und keine Garantie gegen Malware, Keylogger, Screenshots,
Speicheranalyse, hochprivilegierte lokale Angreifer oder sichere physische
SSD-Löschung.

## 4. Verschlüsselungsstatus

Security- und Verschlüsselungsfoundations sind implementiert und getestet:
SQLCipher-Datenbankpfad, verschlüsselte Dokumentcontainer, verschlüsselter
Backupcontainer, DMK-/Keyset-Trennung sowie Migrations- und Recoverygrenzen.
Der Integrationspfad ist jedoch standardmäßig deaktiviert, nicht über die UI
zugänglich und auf markierte synthetische Testroots beschränkt.

Für Build 302 gilt daher ausdrücklich:

- keine automatische SQLCipher-Migration bestehender Fachdaten;
- keine verschlüsselte Produkt-Dokumentablage;
- kein verschlüsselter produktiver Backupcontainer;
- kein Security-Integrationsgate für normale Datenroots;
- keine automatische Produktmigration und kein physisches GC;
- keine stille Aktivierung, keine Windows-/DPAPI-Freigabe.

Passwortwechsel und Support-Reset ändern Authentifizierungs- und
Zugangsdaten, nicht den DMK oder die getrennten Datenbank-, Dokument- und
Backupschlüssel der nur vorbereiteten Verschlüsselungsarchitektur.

## 5. Referenzabnahme

Die vorliegende Referenzabnahme bestätigt alle Audit-P1 als geschlossen und
meldet für die letzte Gesamtsuite 1.603 bestandene Tests, 67 bestandene
Subtests und Exitcode 0. Diese Gesamtsuite wird in diesem reinen
Dokumentationsauftrag nicht erneut ausgeführt.

Für die vorliegende Dokumentationsbasis sind zu prüfen: zentrale
Versionsanzeige, Handbuchgenerator, PDF-Erzeugung und Sichtprüfung,
Datei-/Linkverweise, `compileall`, `pip check`, `git diff --check` sowie
Secret-, Pfad- und Artefaktscans. Die tatsächlich ausgeführten Resultate
gehören in den Abschlussbericht dieses Auftrags, nicht in einen vorgezogenen
Buildnachweis.

## 6. Noch offene Release-Gates

1. Clean-Build aus sauberem Worktree sowie Bundle-, DMG-, Architektur- und
   Prüfsummennachweis für Build 302.
2. Reale macOS-/Hardwareprüfung: Gatekeeper, Keychain, Touch ID,
   Sleep/Wake und Restore-Worker ohne Restfenster.
3. Developer ID, Apple-Notarisierung und eine getrennte Entscheidung über
   Update-/Appcast-Aktivierung.
4. Kontrollierte Produktmigration und Pilotaktivierung der Verschlüsselung mit
   verifizierbarem Backup, Rückfallweg und echter Nutzerführung.
5. Windows/DPAPI und reale Power-Loss-Abnahme.

Bis zu diesen Gates gilt: kein Build, keine Übergabe, kein Push, kein Tag, kein
Appcast, kein Pilotrollout und kein öffentlicher Release.
