# Security Sprint 12 – Release- und Packaging-Abnahme 0.3.0

Stand: 2026-07-26  
Referenz: Branch `spike/python-gui`, HEAD
`f47e0a86926f0f349b9c2e2dc25d8b068a57df0a`  
Entscheidung: **GO ausschließlich für einen internen macOS-arm64-Security-RC**

## Release-Matrix

Legende: `grün` = in dieser Abnahme ausgeführt, `statisch` = Vertrag und
plattformisolierte Tests geprüft, `ungeprüft` = keine reale Plattformabnahme.

| Bereich | Quellbetrieb | gebaute App | macOS arm64 | Windows | Gate-Off | Gate-On-Test |
|---|---|---|---|---|---|---|
| Python | 3.14.6, grün | 3.14.6, grün | arm64 | ungeprüft | normaler Start | Testprozess |
| PySide6 / Shiboken | 6.11.1 / 6.11.1 | 6.11.1 / 6.11.1 | reine arm64-Slices | ungeprüft | produktive UI grün | Versionsbeleg |
| SQLCipher-Bindung | sqlcipher3 0.6.2 | explizit gebündelt | arm64 | ungeprüft | nicht importiert | grün |
| SQLCipher-Engine | 4.12.0 Community | 4.12.0 Community | eingebettet | ungeprüft | Standard-SQLite | Migration/Reopen grün |
| PyNaCl / libsodium | 1.6.2 | explizit gebündelt | arm64 | ungeprüft | nicht importiert | Secretstream grün |
| cryptography | 49.0.0 | gebündelt | arm64 | ungeprüft | Support/Auth | Envelope grün |
| cffi / `_cffi_backend` | 2.0.0 | gebündelt | arm64 | ungeprüft | Auth/Krypto | Import grün |
| PyInstaller | 6.21.0 gepinnt | vollständiger Build grün | `target_arch=arm64` | kein Spec | n/a | n/a |
| Keychain | Port/Fakes grün | realer Lifecycle grün | Keychain grün | n/a | Gerätecredential | DMK-Testprobe grün |
| DPAPI | unsupported/fail-closed | kein Windows-Build | n/a | ungeprüft | keine Freigabe | keine Freigabe |
| Sparkle | 2.9.4 + SHA-256-Pin | Framework gebündelt | arm64 | n/a | Pilotkanal unverändert | unabhängig |
| Launcher / Startup | Importisolation grün | Paketstart grün | grün | ungeprüft | Orchestrator nicht importiert | nur internes Argument |
| Support-Reset | Quell-E2E grün | bestehendes separates Werkzeug grün | grün | ungeprüft | bestehender Pfad | keine DMK-Produktkopplung |
| Backup / Restore | ZIP-v1 und Security-Fokus grün | Paket-Smokes grün | grün | ungeprüft | ZIP-v1 unverändert | verschlüsselt + Staging grün |
| Dokumentcontainer | Fokus grün | Paket-Tampertest grün | grün | ungeprüft | bestehender Pfad | Secretstream v1 grün |
| RuntimePaths | unverändert | normaler Temporärroot grün | grün | statisch | normaler Nutzerroot | Produktroot abgelehnt |
| Appcast / Version | 0.3.0 / 300 | Plist 0.3.0 / 300 | Pilot-URL unverändert | n/a | Pilot, manuell | unabhängig |
| About-Dialog | zentrale Version | 0.3.0 / 300 | grün | ungeprüft | sichtbar | unverändert |

## Packaging und Abhängigkeiten

- Frisches Build-Venv mit exakt gepinnten Security- und
  Packaging-Abhängigkeiten; `pip check` ist grün.
- `_cffi_backend`, `nacl._sodium`, `sqlcipher3._sqlite3`, PySide6, Shiboken
  und Sparkle werden explizit erfasst. Der Pakettest importiert und verwendet
  die Security-Laufzeit tatsächlich.
- Alle 141 geprüften Mach-O-Dateien des fertigen Bundles sind arm64. Fünf
  universelle Eingaben werden vor der abschließenden Signierung ausgedünnt.
- Keine Datenbank, kein Backup-/Dokumentcontainer, kein Pilot-Excel, kein
  privater Schlüssel und keine verbotene lokale Datenendung liegt im Bundle.
- Kein lokaler `/Users/lauragehrke/`-Pfad wurde gefunden. 28
  `/Users/runner/work/cryptography/`-Referenzen stammen ausschließlich aus der
  upstream CycloneDX-SBOM von cryptography und werden separat gezählt.
- Die Security-Lizenztexte und der Sprint-12-Drittanbieterhinweis sind
  gebündelt. PyInstaller meldet nicht benötigte `pycparser.lextab`- und
  `pycparser.yacctab`-Hidden-Imports; die realen cffi-, PyNaCl- und
  SQLCipher-Paketpfade sind dennoch vollständig grün.

## Gate-Off und Gate-On

Gate-Off startet die normale App mit leerem Release-Datenbestand, erzeugt nur
die bestehenden RuntimePaths, initialisiert Standard-SQLite, erstellt und
verifiziert ein ZIP-v1-Backup, bereitet und verifiziert Restore-Staging,
bestätigt Login, Dokumentzugriff und reguläres Beenden und erzeugt den
bestehenden PDF-Pfad. Der Security-Integrationsorchestrator wird dabei nicht
importiert. Es gibt keinen UI-Schalter, keine automatische Migration und
keinen SQLCipher-Fallback.

Gate-On akzeptiert nur den exakten Gatewert, den Paketmarker und einen
privaten, kanonischen System-Temporärroot mit beiden Sprint-11-Markern. Im
gebauten Artefakt sind 23 Schritte grün: SQLCipher-Migration, verschlüsselte
Dokumente, verschlüsseltes Backup, frischer Reopen, Restore-Staging, falscher
Schlüssel, Backup-/Dokumentmanipulation, Gate-Off bei vorhandenem Testbestand
und Recovery nach vier echten Prozessabbrüchen. Die Klartextquelle bleibt als
Safety Copy erhalten; im neuen Storage wurde kein Klartextpayload akzeptiert.

## macOS-Keychain und Support

Die gebaute App hat einen synthetischen DMK gespeichert und in einem neuen
Prozess sowie aus einer Bundle-Kopie wieder geladen. Ein Passwortwechsel
rotierte den DMK nicht. Fehlender und falscher Keychain-Inhalt blockierten
ohne stille Neuerzeugung; der Testeintrag wurde abschließend entfernt.

Das bestehende beaufsichtigte Support-Reset-Werkzeug bestand separat den
vollständigen synthetischen E2E-Lauf einschließlich Sicherheitsbackup,
Passwortwechsel, neuen Recovery-Codes, unveränderten Fachdaten und
abgewiesener Token-Wiederverwendung. Eine DMK-gekoppelte produktive
Support-Reset-Migration existiert absichtlich nicht. Ein real verweigerter
Keychain-Systemdialog ist noch nicht auf Zielhardware abgenommen.

Der Build ist ad-hoc signiert. Developer-ID-Signierung und Apple-Notarisierung
sind nicht ausgeführt und bleiben eigene Distributionsgates. Die
Keychain-Bridge verwendet funktionierende, aber von Apple als veraltet
markierte ACL-APIs; deren Ablösung ist ein Plattform-Härtungspunkt.

## Windows

Es gab keine echte Windows-Umgebung. Der Windows-DMK-Store bleibt
`unsupported` und fail-closed; ein produktiver DPAPI-Adapter und Windows-Spec
existieren nicht. Plattformisolierte Verträge und ACL-/No-Clobber-Tests sind
grün, ersetzen aber keinen DPAPI-, NTFS-, SQLCipher-, libsodium- oder
PyInstaller-E2E-Nachweis. Es gibt keine Windows-Freigabe.

## Crash, Power-Loss und Qt-Stabilität

Vier Orchestratorgrenzen wurden durch echte Prozessabbrüche mit Exitcode 91
geprüft: Journal-Publikation, Safety-Copy-Publikation,
Dokumentgeneration-PREPARED und bestätigtes verschlüsseltes Backup. Recovery,
Journal, Replay-Anker, Lock, fsync, No-Clobber und erneute Verifikation sind
grün. Ein Prozessabbruch ist kein physischer Stromausfall; Hardware-, Cache-
und Dateisystemverhalten bleibt ein reales Zielgerätegate.

Die beobachtete Qt-Flanke wurde in wechselnder Testreihenfolge reproduziert.
Der Responsivitätstest verglich einen 5-ms-Hauptthread-Timer mit einem festen
200-ms-Worker-Sleep und konnte bei ungünstigem Scheduling den bereits
beendeten Worker sehen. Der Test synchronisiert nun auf einen tatsächlich
verarbeiteten Timer-Tick, der den blockierten Testworker freigibt. Produktcode,
Timeout und Skips blieben unverändert. Die fehlerhafte Reihenfolge, ihre
Umkehr und die erneute fehlerhafte Reihenfolge bestanden anschließend jeweils
310 Tests und 48 Subtests.

## Version, Artefakt und Prüfsumme

- App-/Bundle-/About-Version: `0.3.0`; Build: `300`.
- Bundle-ID: `de.jenaplan.kompetenzmanager`; Mindest-macOS: 13.0.
- Updatekanal: bestehender Pilotkanal mit signiertem Feed; keine
  Stable-Aktivierung und keine Veröffentlichung.
- Datenbank-, Backup- und Dokumentformatversionen wurden nicht umgedeutet.
  SQLCipher 4.12.0 bleibt ausschließlich die Sprint-11-Testengine; das
  SQLCipher-4.17.0-Produktziel ist offen.
- Interner Build:
  `/private/tmp/jkm-security-s12-dist/Jenaplan-Kompetenzmanager-0.3.0-macOS-arm64.dmg`
- Größe: 58.423.724 Byte; SHA-256:
  `ca03fce2329fb7f540c3bc8959f0d6215c56b3232b13d84365983795f9468234`.

## Tests und Entscheidung

- Gesamtsuite zweimal im Auftrag grün; final nach allen Änderungen:
  1.625 bestanden, 20 bestehende plattformgebundene Skips.
- 576 Security-, Backup-, Restore-, Support- und Produktfokustests grün.
- Wiederholte Qt-Reihenfolgeläufe grün; keine Testdeaktivierung und keine
  Timeout-Erhöhung.
- Gate-Off-, Gate-On-, Keychain-, Codesign-, Bundle-, Architektur-, Lizenz-,
  Artefakt-, Entwicklerpfad-, Secret- und Klartextprüfungen grün.
- `compileall`, `pip check`, Build-Syntax und `git diff --check` grün.

Klassifikation: **P0 = 0, P1 = 0**. Offene **P2** sind Windows/DPAPI,
Developer ID/Notarisierung, reale Zielhardware- und Keychain-Denial-Prüfung,
vollständiger Power-Loss, Ablösung veralteter Keychain-ACL-APIs,
SQLCipher-4.17.0-Produktbasis sowie Nutzerführung für eine spätere produktive
Recovery.

Damit gilt **GO nur für den internen macOS-arm64-Security-RC 0.3.0**.
Produktmigration, Pilotaktivierung, Windows, Developer ID, Notarisierung,
Stable-Appcast und öffentlicher Release bleiben **NO-GO** bis zu ihren
jeweiligen bestätigten Gates. Es gibt keine Aussage „DSGVO-konform“ und kein
Versprechen sicherer SSD-Löschung.
