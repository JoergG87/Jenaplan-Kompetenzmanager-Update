# Release- und Sicherheitsbasis 0.3.0 / Build 303

Stand: 27. Juli 2026  
Branch: `spike/python-gui`  
Buildreferenz: wird vor dem Clean-Build als vollständiger Commit im Release-
Inventar festgehalten.  
Entscheidung: **NO-GO für Übergabe und GitHub-Pre-Release, bis der Clean-Build
und alle Paket- und DMG-Gates nachgewiesen sind.**

## 1. Zweck und Geltung

Dieses Dokument trennt die dokumentierte Produktbasis von einem späteren
Buildnachweis. Es belegt weder ein erzeugtes DMG noch eine Signatur, Prüfsumme
oder den Buildcommit. Diese unveränderlichen Nachweise entstehen erst aus dem
Clean-Build und werden zusammen mit dem kontrollierten GitHub-Pre-Release/Pilot
veröffentlicht. Ein Updatefeed wird dabei nicht aktiviert.

Die verbindliche nutzerverständliche Beschreibung steht in
`SICHERHEIT_UND_VERSCHLUESSELUNG.md`; dieses Dokument ist die interne
Release- und Abnahmegrenze.

## 2. Dokumentierte Produktwahrheit

| Punkt | Stand für Build 303 |
|---|---|
| Version / Plattform | 0.3.0, macOS auf Apple Silicon (arm64), mindestens macOS 13 |
| Produktform | lokale Desktop-App, vorgesehene DMG-Installation |
| Signatur / Notarisierung | für einen internen Build ad-hoc signiert erwartet; nicht notarisiert |
| Freigabe | kein Windows, kein öffentlicher Stable-Release, kein Stable-Appcast |
| Datenübertragung | keine Cloud, keine KI-Einbindung |
| Normaler Datenpfad | frische Final-V4-SQLCipher-Fachdaten, verschlüsselte Managed Documents/PDFs sowie `.jkmebackup` und same-installation Restore |
| Bedienung | Authentifizierung, Keychain, optionales Touch ID, Sperre, Dashboard, Stundenplan, Schüler-/Kursverwaltung, Beobachtungen, Cockpit, Berichte, LEG und PDF-Ausgaben; Support-Reset im Cipher-Modus blockiert |
| Restore | Vorschau und ausdrückliche Bestätigung, separater Worker, vollständiges App-Ende, kontrollierter Neustart; fehlender Worker belässt den aktiven Bestand unverändert |

## 3. Aktive Schutzgrenzen

- Das lokale Passwort, Recovery-Codes und der lokale Security Store schützen
  den Zugang zur App. Eine gespeicherte Geräteanmeldung liegt im macOS-
  Schlüsselbund; Touch ID ist optional und das Passwort bleibt Fallback.
- Die App sperrt automatisch. Support-Reset bleibt im Cipher-Modus blockiert.
- `.jkmebackup` wird keyed geprüft und ist an Installation und DMK gebunden.
  Ein Restore wird erst nach Staging, Prüfung und expliziter Bestätigung wirksam.
- Lokale Datenroots und verwaltete Dateien bleiben getrennt vom App-Bundle.
  Freie Exportdateien und PDFs liegen außerhalb der App als Dateien vor und
  müssen organisatorisch geschützt weitergegeben werden.

Diese Grenzen sind keine Aussage „DSGVO-konform“ und keine Garantie gegen Malware,
Keylogger, Screenshots,
Speicheranalyse, hochprivilegierte lokale Angreifer oder sichere physische
SSD-Löschung.

## 4. Verschlüsselungsstatus

Der committed Produktpfad aktiviert nach Authentifizierung für eine frische
Installation SQLCipher 4.17/CommonCrypto, verschlüsselte Managed Documents,
`.jkmebackup` und same-installation Restore. Ein neuer Build-, Paket- und
Hardware-Nachweis bleibt davon getrennt.

Für Build 303 gilt daher ausdrücklich:

- keine automatische SQLCipher-Migration bestehender Fachdaten;
- verschlüsselte Produkt-Dokumentablage und `.jkmebackup`, aber keine
  Portabilität bei Gerätewechsel oder DMK-Verlust;
- keine automatische Produktmigration und kein physisches GC;
- keine stille Aktivierung, keine Windows-/DPAPI-Freigabe.

Passwortwechsel und Support-Reset ändern Authentifizierungs- und
Zugangsdaten, nicht den DMK oder die getrennten Datenbank-, Dokument- und
Backupschlüssel der nur vorbereiteten Verschlüsselungsarchitektur.

## 5. Referenzabnahme

Die vorliegende Referenzabnahme bestätigt alle Audit-P1 als geschlossen und
meldet für die letzte Gesamtsuite 1.617 bestandene Tests, 67 bestandene
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
   Prüfsummennachweis für Build 303.
2. Reale macOS-/Hardwareprüfung: Gatekeeper, Keychain, Touch ID,
   Sleep/Wake und Restore-Worker ohne Restfenster.
3. Developer ID, Apple-Notarisierung und eine getrennte Entscheidung über
   Update-/Appcast-Aktivierung.
4. Reale Bundle-/Keychain-/Cipher-Backup-/Restore-Abnahme sowie Entscheidung
   zu Gerätewechsel und DMK-Recovery; keine Klartextmigration.
5. Windows/DPAPI und reale Power-Loss-Abnahme.

Bis zu diesen Gates gilt: keine Übergabe, kein Tag, kein GitHub-Pre-Release,
kein Appcast und kein Pilotrollout. Der vorgesehene Veröffentlichungsweg ist
ein GitHub-Pre-Release/Pilot, niemals ein Stable-Release.
