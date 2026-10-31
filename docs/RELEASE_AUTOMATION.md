# Pilot-Releaseautomation

## Build 405 vollständig zur Veröffentlichung vorbereitet – 31.10.2026

**GO für die lokale Veröffentlichungsvorbereitung.** Paketquelle `38f6e8c5c2d9bb149fdd166a09397d41462d0df6`, Dokumentationsquelle `d90011e20bb3373fb0a6b37bea29099c99f5f0fc`, abgeschlossene Paket-/Updatequalifikation `597eb287e91fe137dbf6a814804da6fcc78a3de4`. Vorgesehener Tag `v0.5.0-build405` zeigt gemäß bestehendem Releasevertrag später auf die Paketquelle, nicht auf diesen Dokumentationsabschluss. Kein Tag erstellt.

Einziger aktiver Satz: `release/output/0.5.0-build405-docrevision-20261031/release-manifest.local.json` und sanitisiertes `release-manifest.json`. DMG und Dokumentations-ZIP bytegleich zur endgültigen Qualifikation. Alle 58 im Manifest gebundenen bisherigen Nachweisdateien erneut hashgeprüft; Produkt-/Update-/Migrations-/Restoregates übernommen, keine erneute Gesamtsuite. Dokumentation vollständig: 8 PDFs, 61 Seiten, 25 synthetische Screenshots, 50 ZIP-Einträge.

Finale GitHub-Asset-Allowlist (SHA-256):

| Datei | SHA-256 |
| --- | --- |
| `Jenaplan-Kompetenzmanager-0.5.0-macOS-arm64.dmg` | `3ddc4a4ed40abdcefa181dacbd55587ed8d9f6004d956ecc8c7bfefa4276a4f7` |
| `Jenaplan-Kompetenzmanager-0.5.0-Dokumentation.zip` | `6a379800c13f64eae2cd1a891faddf94a63e394d04a9759645dfcb9b78bfa829` |
| `SHA256SUMS-0.5.0-Build-405.txt` | `4648acf48c35e295c640e736eaa46144884d17875480efc28019236f0730220f` |
| `RELEASE_INVENTORY-0.5.0-Build-405.txt` | `7a59a6c78e7c8dc17aa7c9a6f35a33ef521593743cba58ee99b98e2ed1f095c1` |

Gezielte Korrekturen: überholten Keychain-NO-GO-Satz im aktiven Textinventar durch den finalen Qualifikationsstand ersetzt; identische qualifizierte GitHub-Notes zusätzlich unter dem von `publish_appcast` erwarteten `artifacts/GITHUB_RELEASE_NOTES.md` bereitgestellt. Aktive Prüfsummenlisten konsistent erneuert; vorherige Listen als historische Nachweise unter `final-release-gates/historical/` erhalten. Historische STOP-Berichte sind keine aktiven Releaseinventare.

Bestehende Automation `_sign_update`, `_build_appcast`, `_verify_ed25519` und `_verify_feed_signature` verwendet, keine neue Releasepipeline. Sparkle 2.9.4, bestehendes Konto `de.jenaplan.kompetenzmanager.pilot`; kein Schlüsselexport/-wechsel. Signierung nur über kurzlebige private `payload.bin`-Kopie. DMG (235361769 Bytes), qualifizierte HTML-Notes und Appcastprefix mit unabhängigem öffentlichen Ed25519-Verifier bestätigt. Signaturen, signierte Längen und Hashes in `final-release-gates/sparkle-signatures.json`; Appcastdatei hat zusätzlich den unverändert von der bestehenden Pipeline erzeugten Signaturkommentar. Feedhash und signierte Prefixlänge sind ausdrücklich getrennt. Notes und Feed sind spätere Pages-Dateien, keine zusätzlichen GitHub-Assets.

Remotevorprüfung tatsächlich lesend ausgeführt: Ziel `JoergG87/Jenaplan-Kompetenzmanager-Update`; 405-Tag lokal/remote und 405-Release/Draft fehlen; 404 ist veröffentlichtes Pre-Release. Live-Pagesfeed bytegleich zum Repositoryfeed, dessen Signatur und lokale veröffentlichte 404-DMG-Signatur unter dem konfigurierten Pilotschlüssel unabhängig gültig. Maximaler Pilotbuild 404, keine doppelten Builds; vorbereiteter Feed ergänzt genau 405 und erhält alle bisherigen Einträge. Stable-Verzeichnis fehlt, Stable bleibt deaktiviert. Öffentliches Feedblob vor/nach Vorbereitung identisch. Nachweise: `final-release-gates/remote-preflight.json`, `local-gate-result.json`, `final-inventory-verification.json`, `SHA256SUMS-FINAL.txt`. Gezielte Prüfung: `rtk proxy python3 -m pytest tests/test_release_pilot.py tests/test_sparkle_feed.py -q --tb=short` → 47 bestanden, keine Skips.

Keine offenen technischen Blocker im beauftragten lokalen Signatur-/Manifestumfang. Öffentliche Phasen bleiben bewusst pending, `release_authorization=false`. Verbleibend: gesonderter Veröffentlichungsauftrag; Tag-/Releasefreiheit und unveränderten Feed unmittelbar erneut prüfen; bestehendes `publish-github` mit diesem Manifest ausführen (Pre-Release, Latest=false, exakt vier Assets, unabhängiger Download-/Hashvergleich); anschließend bestehendes `publish-appcast` und `verify`. Diese Phase erzeugt den Feed wegen seines Publikationsdatums neu und signiert ihn erneut; bei verzögerter Veröffentlichung dürfen vorbereitete und neu erzeugte Feedbytes niemals verwechselt werden. Bestehende Signaturen für identische DMG-/Notesbytes bleiben gültig. Kein Stable-Rollout.


## Endgültiger 405: Schlüsselbund-/Updategate geschlossen – 31.10.2026

Die folgende Sperre der Dokumentationsrevision ist historisch: Das endgültige DMG wurde ohne erneuten Neubau am ursprünglichen synthetischen 404-Schlüsselkontext qualifiziert. Ad-hoc-CDHash 404 `81a654aca76be93bf447e6078e1a6b79b348f516`, ursprünglicher 405 `0cbe3881fbae44c0c18ca88f0f82c5ad038fd858`, finale Revision `b02b1c9f3604051fa2d2c39d1f04e021bfb6f244`; Bundle-ID, Executable und Entitlements unverändert. Native Evidenz: vorhandene ACL vertraute den beiden früheren CDHashes; securityd versuchte den Dialog, hielt wegen `inDarkWake` mit -25337 an. Nutzer bestätigte nach Rückkehr persönlich den regulären Dialog. Danach vorhandene Anmeldung, unveränderte Schlüsselfingerprints und vollständige V7-Inhaltsgleichheit erfolgreich.

Zusätzlich ursprüngliche V4-Vollsicherung unabhängig verifiziert und als getrennte synthetische Kopie mit denselben vorhandenen Schlüsseln geprüft: tatsächlicher Original-404-Start, gewöhnlicher endgültiger 405-Start belässt V4, bewusste Wartungsmigration, vollständiger Datenerhalt und regulärer V7-Neustart/Login bestanden. Harness-Vorläufe und ausschließlich synthetische Fixturekorrekturen sind transparent im Abschlussbericht erfasst; keine Produktguardänderung. Bereits qualifizierte Backup-/Restore-Nachweise wegen unverändertem Code/native Komponenten übernommen. DMG und ZIP unverändert; alle 93 geschützten früheren Artefakte unverändert. Tatsächliches finales DMG und getestete App vollständig byte-/link-/modusgleich; Deep/strict-Codesign und DMG-Integrität gültig.

GO für das Paket-/Updategate. **Veröffentlichung weiterhin NO-GO** bis separatem ausdrücklichem Veröffentlichungsauftrag einschließlich neuer Sparkle-Signaturen der endgültigen DMG-/Notes-/Feedbytes und öffentlicher Rückprüfung. Kein Feedupdate und keine alten Sparkle-Signaturen für neue Dateien. Vollständiger Bericht: `release/output/0.5.0-build405-docrevision-20261031/KEYCHAIN_UPDATE_ABSCHLUSS_20261031.md`; Evidenz: dort `keychain-qualification-20261031/`. Beide Manifestfassungen schließen das Paketgate, `release_authorization` bleibt false. Keine Code-, Schema-, Versions-, Schlüssel- oder Assetänderung; kein Push/Tag/Release/Stable-Rollout.


## Dokumentationsrevision 405: abgeschlossen, Paketfreigabe gesperrt - 31.10.2026

Acht PDFs mit 61 Seiten vollständig erzeugt und final visuell geprüft; 25 Abbildungen pixelgenau und alle Textquellen vollständig in den PDFs nachgewiesen. Dokumentations-ZIP mit 50 Einträgen vollständig geöffnet und bytegeprüft. Quellencommit `d90011e`. Neues DMG aus kontrolliert geänderter Dokumentressourcenkopie des unveränderten Ursprungspakets neu versiegelt; ausführbarer Code ohne Signatur identisch. Elf konfigurierte Paketgates sowie isolierter Start/Restart und Restore-Worker-Smoke bestanden. Der finale DMG-Inhalt ist an die geprüfte Arbeitskopie gebunden.

**Keine Paket-/Veröffentlichungsfreigabe:** neue Signatur öffnet den bestehenden synthetischen 404-Ursprungskontext nicht (Exit 3, unklarer V7-Recoverykontext); Originalpaket öffnet denselben Bestand. Neue Bestands-/Schlüsselbundkontinuität und anschließend neue Sparkle-Signaturen bleiben verpflichtend. Keine ungeprüfte Übernahme alter Signatur- oder Updatebelege. Keine Codeänderung zur Umgehung, keine Reparatur und kein Schlüsselersatz.

Aktiver Releasezeiger verweist jetzt auf die neue ausdrücklich gesperrte Revision `release/output/0.5.0-build405-docrevision-20261031/release-manifest.local.json`. Der alte qualifizierte Kandidat bleibt byteunverändert. Dokumentation GO; Veröffentlichung NO-GO bis nachgeholtem Paketgate und erneuter ausdrücklicher PO-Bestätigung. Vollständiger Bericht: `DOKUMENTATIONSREVISION_ABSCHLUSS.md` im Revisionsordner. Kein Push, Tag, Release oder Appcastupdate.

## Dokumentationsrevision 405 - 31.10.2026

Bestands-HEAD `b19225b0a1fe51e1ac122d471a66b881307c0edb`, Produktquelle `38f6e8c5c2d9bb149fdd166a09397d41462d0df6`. GitHub-Releases und Repository-Appcast read-only geprüft: öffentlich weiterhin 404, kein405-Release. Dokumentation ist nicht nur ZIP-Inhalt: Erste-Schritte-PDF und zwei Drittanbieterhinweise sind App-Ressourcen, Installations-PDF zusätzlich DMG-Inhalt. Deshalb keine ZIP-only-Freigabe und kein stilles Überschreiben des gehashten Kandidaten.

Der ursprüngliche Kandidat bleibt unverändert unter `release/output/0.5.0-build405-38f6e8c5c2d9/`. Die getrennte Revision unter `release/output/0.5.0-build405-docrevision-20261031/` bindet acht PDFs, vollständige Dokumentations-ZIP, kontrolliert neu versiegeltes App-/DMG-Paket und geänderte Hashes. Produktcode und Abhängigkeiten bleiben unverändert; Bytevergleich und Signatur-/Ressourcenprüfung bestimmen die übertragbaren bisherigen Nachweise. Neue App-/DMG-Bytes benötigen eigene Paketgates; alte Sparkle-Signaturen gelten nur für alte Bytes. Es erfolgt keine Änderung des öffentlichen oder bisherigen lokal signierten Feeds. Ergebnis, offene neue Signatur-/Updategates und abschließende Empfehlung stehen im dortigen Revisionsbericht. Keine Veröffentlichung ohne erneuten PO-Auftrag zum endgültigen Artefaktstand.

## Updateabschluss 405 – 31.10.2026 – GO

Tatsächliche synthetische 404→405-Keychainkontinuität nach manueller OS-Freigabe, bestehende Anmeldung, ausdrückliche V4→V7-Migration, vollständige Datenerhaltung, V7-Neustart/Schreibvorgänge und vollständiger Worker-/Restart-/Restore bestanden. Build 404 verweigert V7 mit final_v4_sqlcipher_schema_incompatible, regulärer Exit 4; Screenshot gesichert. Testharness-bedingte leere Metadaten-Sidecars ausschließlich im synthetischen Root durch SQLite geschlossen, beide Metadaten-DBs bytegleich; Produktguard unverändert. Keine offenen bestätigten P0/P1. Releaseassets unverändert, keine neue Suite oder Paketbau notwendig. Maßgeblicher Bericht: `release/output/0.5.0-build405-38f6e8c5c2d9/UPDATE_REPORT_20261031.md`. GO für separate PO-Veröffentlichungsfreigabe; öffentliche Feed-/Auslieferungsprüfung verbleibt im Veröffentlichungsauftrag. Kein Push/Tag/Release/Appcastupdate.

## 0.5.0 / Build 405 – lokaler Kandidat, Updateabschluss offen – 30.10.2026

Sauberer Produktquellcommit `38f6e8c5c2d9`; separater Versionscommit `77f370f`. Bestehende Pipeline vollständig gebaut, finale Gesamtsuite **3544 bestanden / 104 bestehende Skips / 120 Unterprüfungen**, elf Originalpaketgates und Restore-Worker-Smoke bestanden. 209 Frozen-Module plus tatsächlicher Main stimmen mit Quelle überein; 6196 Bundleeinträge nach nativem Lauf unverändert und mit DMG verglichen. SQLCipher 4.17.0 / SQLite 3.53.3 / CommonCrypto, Produkt-Bundle-ID und vorhandener Pilotkanal qualifiziert.

Nativer Produktmigrationspfad V4→V7 mit realistisch befüllter synthetischer Quelle bestanden: Vollbackup unabhängig verifiziert, historische Inhalte und Dokumente erhalten, bestehende Anmeldung, V7-Schreibvorgänge und vollständiger tatsächlicher V7-Restore mit bestätigtem Worker-/Restart-Handschlag. Native Wartungsblockade durch wartenden Vorgänger behoben, ohne Live-owner-Veto oder Lockprüfung zu lockern: geschlossene Wartungsabbilder werden durch den bestehenden Abschluss-/Normalstart ersetzt.

Unveränderter veröffentlichter Build 404 selbst: synthetisch 24 Schüler, 3 Gruppen, 3 Kurse, 331 Kompetenzen, 71 Beobachtungen, 5 Dokumente / 7 Container, 2 Berichts- und 2 LEG-Entwürfe, Revisionen/PDFs, 10 Stundenplaneinträge; vorhandene Anmeldung und unabhängig geprüftes Backup/RESTORE_READY bestanden. Sparkles tatsächlicher Versionsvergleich erlaubt 405 > 404; Bundle-ID, Feed und Vertrauensschlüssel identisch. Beim realen Appaustausch am gleichen isolierten Pfad wartet der neue Zugriff auf den vorhandenen 404-DMK auf eine macOS-Keychainfreigabe. Computer-Use-Schutz sperrt SecurityAgent; Mac als gesperrt gemeldet. Daher gesamte 404→405-Migration/Anmeldung und nachfolgender paketierter 404-gegen-V7-Fall **offen**, nicht bestanden.

**NO-GO für die Veröffentlichungsfreigabe bis zum Abschluss dieses lokalen Updategates.** Keine neue bestätigte offene P0/P1 im qualifizierten Codeumfang. P2-/Funktionsgrenze: V7 besitzt keinen V4-Support-Resetadapter; Recovery-Codes und Pilotbetreuung bleiben vorgesehen. Bestehende Ad-hoc-Strategie beibehalten; Sparkle-Ed25519-Signaturen für alle vier Assets, Notes und lokalen Feed unabhängig verifiziert. Developer ID/Notarisierung nicht behauptet oder als neue Pflicht eingeführt. Öffentliche signierte Feed-/Download-/Sparkleinstallation bleibt ein Veröffentlichungsgate; keine Veröffentlichung ausgeführt.

Kandidat und ausführlicher Bericht: `release/output/0.5.0-build405-38f6e8c5c2d9/RELEASE_CANDIDATE_REPORT.md`; vollständiges lokales Inventar `SHA256SUMS-ALL-405.txt`. Nur `artifacts/` enthält die vier regulären Veröffentlichungassets; `staged-feed/` ist ausschließlich lokal. Historische Kandidaten bleiben getrennt; Build 404 und seine veröffentlichten Artefakte unverändert.

## Mac-Pilot 0.4.4 / Build 404 veröffentlicht – 13.10.2026

Veröffentlicht aus 79d59591344397fdc462f40e1c0335c75066463e im bestehenden Pilotkanal. GitHub-Pre-Release v0.4.4-build404 und signierter Pilot-Appcast öffentlich verifiziert; Feed-Commit 942087e0325b4b417738ba70b55a2148e011091b. Kein Stable-Wechsel, keine Developer-ID-/Notarisierungsbehauptung. Die installierte produktive Mac-App wurde weder gestartet noch aktualisiert; vorhandene Produktdaten und Produktschlüssel blieben unberührt.

Enthält bereichsgerechte Pflanzenbezeichnungen in App und Eltern-PDF, feste 32-Pixel-Bewertungsbuttons, an QObject-Owner gebundene verzögerte UI-Aktionen und begrenzte Wiederholung vorübergehender WAL-Initialisierungssperren. Native Tablet-Meldungsgrids behalten ihre Standardantworten und die bestehende Zurück-Aktion. Keine Datenmodelländerung oder Neubewertung.

Abnahme: vollständige Testsuite mit 2539 bestandenen Tests, 104 erwarteten umgebungs-/Gate-Skips und 100 bestandenen Unterprüfungen, Prozessende 0. Alle elf Paketgates und paketierter Restore-Worker-Smoke bestanden. Qualifizierte SQLCipher-4.17-/SDK-27-Basis zuvor mit 50 zusätzlichen exakten Runtimeprüfungen, darunter reale synthetische Keychain-/Crash-Grenzen, bestanden. Alle vier veröffentlichten Asset-Hashes, Ed25519-Signaturen und neuester Feed-Build 404 verifiziert. DMG-SHA256 d55c21c35509a034b3b249450478dc82514f7f296ab5e494799dae0fd93f311e.

Nachweise und Release-Manifeste: release/output/0.4.4-build404-79d595913443/. Exaktes qualifiziertes Wheel dauerhaft lokal unter build/macos-inputs/sqlcipher-4.17-sdk27/ gesichert, SHA256 9ce432941a45f28af3877192149ab2583ae22f466e3b22c2a7323c5a84c577f9. Lokale release_state.json zeigt auf das endgültige Manifest. Verschobene Pflanzen-ZIP bleibt unangetastet.

Release: https://github.com/JoergG87/Jenaplan-Kompetenzmanager-Update/releases/tag/v0.4.4-build404
Updatefeed: https://joergg87.github.io/Jenaplan-Kompetenzmanager-Update/pilot/appcast.xml


## Veröffentlicht: 0.4.3 / Build 403 – 11.10.2026

GitHub-Pre-Release `v0.4.3-build403` und Pilot-Appcast veröffentlicht; öffentliche Endprüfung erfolgreich. Paketquelle ist exakt `d531e11584e3cc7b7b2b79ca0ca807fc2efe3287`; nachfolgende Release-Werkzeugkorrekturen ändern keine Paketbytes. Vier öffentliche Assets wurden mit Größe und SHA256 zurückgeprüft; Ed25519-Signaturen für DMG, Release-Notes und Feed gültig. Alle elf Originalpaketgates bestanden. Restore-Worker-Smoke erreicht RESTORE_READY und bricht kontrolliert vor Datenaustausch ab; keine vollständige Restore-Abnahme. Stable bleibt deaktiviert, keine Developer-ID-/Notarisierungsfreigabe behauptet.

Nachweise: Gesamtsuite 2.472 Tests und 100 Untertests bestanden, 104 übersprungen; ein Test setzte einen Arbeitsordner außerhalb des Systemtemps voraus und scheiterte im temporären Release-Checkout. Alle 29 Runtime-Root-Tests mit identischem Quellstand im regulären Projektordner bestanden. Zusätzlich 94 Tests im exakten SQLCipher-4.17-Stack und sechs reale synthetische Keychain-Prozesstests bestanden. Release-Werkzeugkorrekturen: 43 gezielte Tests bestanden. Historische SQLCipher-4.12-Infrastrukturtests sind keine Tests des 4.17-Profils. Paketierter Elternexport unabhängig geprüft: zwölf Bereiche, 331 Kompetenzen, 29 Seiten, vier Alphamasken; unvollständiger Stand blockiert. Alle 35 Seiten der fünf Begleit-PDFs visuell geprüft. Finder-Installationsfenster mit drei lesbaren Zielen geprüft, keine App gestartet oder installiert.

Manifest und unveränderte Artefakte lokal unter `release/output/0.4.3-build403-d531e11584e3/`; DMG-SHA256 `c49aa8b227a8ec13abb9e5ae492089bf5f9f7f9d47aa3977c23d280327cf1bc5`. Öffentlicher Release: https://github.com/JoergG87/Jenaplan-Kompetenzmanager-Update/releases/tag/v0.4.3-build403. Die vom Nutzer verschobene Pflanzen-ZIP bleibt im Arbeitsordner unangetastet. Frühere Kandidaten 401/402 bleiben historisch und unverändert.


## Historischer Kandidat 402 – 11.10.2026

Die neue Implementierung wird als 0.4.2 / Build 402 vorbereitet. Das vorhandene Paket 401 bleibt unverändert; seine erneute isolierte Prüfung bestand elf Gates plus Restore-Worker-Smoke. Der Abbruch vor Datenaustausch ist keine vollständige Restore-Abnahme. Die Testkopie ist weiterhin kein Originalpaketnachweis. Der überarbeitete Launcher lehnt interne Links/Sonderdateien ab, übernimmt ausschließlich minimale OS-Umgebung und startet Python mit -I -B. Native Roundtripdiagnose schreibt `report.json` mit synthetischer Service-/Accountautorität vor SecItemAdd und `result.json` mit vollständigem Status danach; Cleanupfehler oder Inhaltsabweichung ergeben Exitcode 1. Vorhandene Reportziele werden nie überschrieben.


## Zweck und Grenze

`scripts/release_pilot.py` automatisiert ausschließlich den lokalen
macOS-arm64-Pilotkanal. Die Automation ändert keine Produktfunktion, keine
Fachdaten, keine Versionsquelle und keinen Stable-Kanal. Version und Build
müssen vor `prepare` in einem eigenen, sauberen Commit in `src/version.py`
stehen.

Build 303 (`0.3.0`, Quellcommit
`07c20a3764405bc1f535eb33efe809519dd8316b`) ist die veröffentlichte
read-only Referenz. Die Automation erkennt den vorhandenen Tag, das
GitHub-Pre-Release und den Pilot-Appcast und veröffentlicht Build 303 nicht
erneut.

## Voraussetzungen

- macOS auf arm64 mit Python 3.14.6;
- sauberer Branch `spike/python-gui`;
- exakt gepinnte Buildabhängigkeiten aus `requirements-macos-build.txt`;
- macOS-Buildwerkzeuge einschließlich `hdiutil`, `codesign`, `ditto` und
  PyInstaller-Buildvoraussetzungen;
- angemeldete `gh`-CLI für
  `JoergG87/Jenaplan-Kompetenzmanager-Update`;
- verifizierte Sparkle-Distribution; ihr Root wird ausschließlich lokal über
  `JENAPLAN_SPARKLE_ROOT` angegeben;
- vorhandener Sparkle-Keychain-Account
  `de.jenaplan.kompetenzmanager.pilot`.

Die kanonischen nicht geheimen Werte stehen in
`release/release_config.toml`. Tokens, Passwörter, private Schlüssel,
Keychain-Inhalte und private Pfade gehören weder in diese Datei noch in Git.

## Normaler Ablauf

```bash
python3 scripts/release_pilot.py inspect
python3 scripts/release_pilot.py prepare --version 0.3.1 --build 304
python3 scripts/release_pilot.py build
python3 scripts/release_pilot.py package-test
python3 scripts/release_pilot.py publish-github
python3 scripts/release_pilot.py publish-appcast
python3 scripts/release_pilot.py verify
```

`status` zeigt das sanitierte aktuelle Manifest. Mit `--manifest` kann ein
bestimmter lokaler Lauf fortgesetzt werden. `run` orchestriert lokale Phasen;
Veröffentlichung wird nur mit den getrennten Schaltern
`--approve-github-publish` und `--approve-appcast-publish` überschritten.
Ohne diese Schalter endet `run` vor der Veröffentlichung.

Der sichere Planlauf lautet:

```bash
python3 scripts/release_pilot.py run --dry-run
```

Er prüft Ist-Zustand und Plan, erstellt aber keinen Zustand, keinen Build,
keinen Tag, keinen Release und keinen Appcast-Commit. Auch der lokale
Sparkle-Keychain-Account wird dabei nicht angesprochen. Ein Build im Plan wird
nur mit `--build-artifacts` angezeigt; im Dry-run wird er nicht ausgeführt.

## Phasen und Wiederaufnahme

Die monotone Reihenfolge ist:

1. `inspected`
2. `prepared`
3. `built`
4. `package_verified`
5. `github_draft_created`
6. `github_assets_verified`
7. `github_published`
8. `appcast_prepared`
9. `appcast_published`
10. `remote_verified`

Eine spätere Phase ist ohne vollständig bestätigte Vorgängerphase gesperrt.
Fehler werden an der betroffenen Phase festgehalten. Bereits gebaute Assets
bleiben nach einem GitHub- oder Appcast-Ausfall unverändert verwendbar. Vor
jeder Wiederaufnahme werden Größe und SHA-256 erneut gegen das Manifest
geprüft.

Ein vorhandener Tag, Draft, Release oder ein vorhandenes Asset wird niemals
blind überschrieben. Exakt gleiche Zustände werden weiterverwendet;
Commit-, Größen-, Hash- oder Metadatenabweichungen führen zu NO-GO. Es gibt
keinen Force-Push und kein pauschales Staging.

## Manifest und lokale Ausgabe

Jeder Lauf erhält einen ignorierten Root unter `release/output/`. Das lokale
`release-manifest.local.json` enthält die für Wiederaufnahme notwendigen
Pfade. `release-manifest.json` ist die sanitierte Variante ohne private
absolute Pfade. `release/release_state.json` verweist lokal auf den aktuellen
Lauf; alle drei Laufzeitartefakte sind ignoriert.

Das Manifest bindet Version, Build, Quellcommit, Branch, Host und Architektur,
Buildlaufzeiten, Sparkle-Version, Assets, Größen, SHA-256, Paketgates,
Restore-Smoke, GitHub-Release, Tag, Appcast-Commit, Feed-URL, jede Phase und
den sanitisierten Fehlerzustand.

## Build und Paketgates

`build` erzeugt einen detached Worktree exakt am Manifest-Commit in einem
restriktiven temporären Root. Das bestehende Buildskript erstellt dort ein
frisches Venv aus den committed Pins, leere Release-Payloads, App-Bundle, DMG
und Dokumente. Die Automation übernimmt nur die erlaubten Assets:

- DMG;
- Dokumentations-ZIP;
- `SHA256SUMS`;
- Release-Inventar;
- GitHub-Release-Notes als lokales Eingabedokument.

`package-test` prüft das konkrete DMG:

- `hdiutil verify` und read-only Mount;
- Bundle-ID, Version, Build und Mindest-macOS;
- ausschließlich arm64-Mach-O-Dateien;
- tiefe strikte Codesign-Prüfung;
- benötigte native Bibliotheken und Sparkle-Version;
- App-Start-Smoke;
- keine Datenbanken, Backups, Schlüssel, Credentials, Exceldateien,
  Entwicklerpfade oder Produktdaten;
- Pilotfeed korrekt und Stable deaktiviert.

Der zusätzliche paketierte Restore-Smoke läuft nur mit `--restore-smoke`.
Wenn ein späteres Releaseprofil ihn in der Konfiguration verpflichtend macht,
blockiert die Veröffentlichung ohne grünen Restore-Smoke.

Die Gesamtsuite ist kein Teil von `package-test`. Sie muss den zu
veröffentlichenden Commit bereits fachlich freigegeben haben.

## GitHub-Veröffentlichung

`publish-github` benötigt `package_verified` und eine gültige `gh`-Anmeldung.
Die Automation:

1. pusht den freigegebenen Quellcommit ohne Force;
2. erzeugt oder verifiziert den annotierten Tag;
3. erzeugt ein Draft-Pre-Release;
4. lädt exakt die Manifest-Allowlist hoch;
5. lädt jedes Asset erneut herunter;
6. vergleicht Größe und SHA-256;
7. prüft Tagziel und Metadaten;
8. veröffentlicht erst danach als Pre-Release mit `Latest=false`.

Bei einer Abweichung bleibt ein vorhandener Draft zur manuellen Untersuchung
bestehen. Ein noch nicht veröffentlichter, eindeutig zu diesem Lauf gehörender
Draft kann in GitHub manuell gelöscht werden. Tag oder Assets dürfen dabei
nicht wiederverwendet oder überschrieben werden, bevor die Ursache geklärt
ist.

## Sparkle und Pilot-Appcast

`publish-appcast` läuft erst nach `github_published`. Das öffentliche DMG wird
erneut heruntergeladen und gegen Manifestgröße und SHA-256 geprüft.
`sign_update` greift über den bestehenden lokalen Keychain-Account auf das
Sparkle-Privatmaterial zu; die Automation liest, speichert oder protokolliert
den privaten Schlüssel nicht.

In einem frischen Checkout des Update-Repositorys werden ausschließlich
`pilot/appcast.xml` und die neue Pilot-Release-Notes-Seite einzeln gestaged.
Der neue Build steht vor älteren Builds. Gleicher oder höherer Pilotbuild
blockiert. Ein vorhandener `stable/`-Bestand wird byteweise unverändert
gehalten; in der aktuellen Konfiguration muss Stable fehlen.

Nach Commit und Push ruft `verify` ausschließlich öffentliche Ergebnisse ab:
Pre-Release-Status, Nicht-Latest-Status, Tagziel, Assets und Hashes,
Pilot-Appcast, Version, Build, arm64, Mindest-macOS, Release Notes, DMG-Größe
sowie Ed25519-Signaturen von DMG, Release Notes und Feed. Erst danach wird
`remote_verified` gesetzt.

## Fehlerbehandlung und Sicherheitsgrenzen

- TLS-Verifikation wird nie deaktiviert. Öffentliche Downloads verwenden den
  macOS-Systempfad mit HTTPS-only und TLS 1.2 oder neuer.
- GitHub-Tokens werden nicht als Argument übergeben.
- Secret-ähnliche Fehlerausgaben werden vor Speicherung redigiert.
- Temporäre Releasewurzeln besitzen restriktive Rechte.
- Keine Produktdatenbank, kein Backup und kein privater Schlüssel ist
  Releasequelle.
- `git add .`, `git add -A`, Dateiglobs, Force-Push und Stable-Rollout sind
  ausgeschlossen.
- Ein Netzwerk-, Authentifizierungs- oder Hashfehler ist NO-GO und invalidiert
  keinen bereits verifizierten lokalen Build.

Weiterhin manuell bestätigt werden müssen insbesondere: fachliche Freigabe und
Gesamtsuite vor dem Lauf, reale Hardware-/Touch-ID-/Keychain-Grenzen,
Developer-ID/Notarisierung sofern für den Zielrelease verlangt, Release-Notes-
Inhalt sowie die beiden bewussten Veröffentlichungsgates.

## Build-303-Referenzsmoke

```bash
python3 scripts/release_pilot.py inspect --reference-303
```

Der Befehl prüft read-only: veröffentlichtes Pre-Release, Tagziel,
Assetmetadaten, Pilot-Appcast Build 303, Updatefähigkeit eines niedrigeren
Builds, Sperre desselben Builds und deaktivierten Stable-Kanal. Er baut und
veröffentlicht nichts.

## Sichtbare DMG-Layoutprüfung

Mit `JENAPLAN_DMG_LAYOUT_MODE=computer-use` erfolgt die Gestaltung des neuen
Arbeitsvolumes ausdrücklich per Computer-Use statt durch den automatischen
Finder-Layoutblock. Der Build schreibt den Mountpunkt nach
`<Buildroot>/dmg-layout.request` und wartet höchstens 15 Minuten. Nach
sichtbarer Prüfung der Symboldarstellung, des Hintergrunds und der drei
Installationsziele wird `<Buildroot>/dmg-layout.ready` als neue reguläre
Datei angelegt. Bereits vorhandene oder symbolische Ready-Dateien sind
unzulässig; Finder muss seine `.DS_Store`-Metadaten geschrieben haben.
Danach laufen unverändert Konvertierung, Manifestbindung und Paketgates.
Dies ist eine technische Bedienübergabe, keine Veröffentlichung.

## Gebundene lokale Testkopie

Für Computer-Use eine eigene Testkopie erzeugen:

```bash
python3 scripts/create_isolated_macos_test_app.py /absoluter/pfad/zum/Testbuild.app
```

Der JSON-Bericht nennt die neue App, ihren privaten synthetischen Root und die
UUID-Bundle-ID. Ausschließlich diese App per Computer-Use öffnen. Ihr nativer
Einstieg setzt den gebundenen Testroot auch beim automatischen Neustart ohne
Startargumente; ein fehlender oder ungültiger Root sperrt vor Produktcode.
Die App kann mit leerem Testroot normal zur Kontoeinrichtung starten oder die
bestehenden `--packaged-smoke-test`-Modi ausführen. Fremde Pfadargumente sind
gesperrt. Der Guard liegt in der neu signierten Kopie, benötigt aber weiterhin
den beim Erzeugen gebundenen lokalen Python-Interpreter. Die Kopie ist nicht
portabel und ihre eigene Ad-hoc-Signatur ersetzt kein Gate am Originalpaket.
Originalpaket und installierte Produkt-App nicht über einen möglicherweise
neu startenden Computer-Use-App-Aufruf zur synthetischen Prüfung öffnen.

## Native Schlüsselbunddiagnose

`macos_keychain_diagnostic.m` prüft nur Standard-Keychain-Status,
Vertrauensreferenz und ACL-Erzeugung. Es liest oder ändert keine Einträge.
`macos_keychain_roundtrip_diagnostic.m` prüft anschließend einen ausschließlich
neu erzeugten UUID-Testeintrag. Keine Produkt-Accounts sind wählbar. Nur nach
erfolgreichem Anlegen werden Lesen, Vergleich und Löschen desselben Eintrags
versucht. Fehlgeschlagenes Löschen ist ein offener Diagnosebefund und darf nicht
als erfolgreicher Roundtrip gelten. Reports enthalten keine Schlüsselbytes.

```bash
xcrun clang -fobjc-arc -framework Foundation -framework Security scripts/macos_keychain_diagnostic.m -o /private/tmp/jkm-keychain-status
xcrun clang -fobjc-arc -framework AppKit -framework Security scripts/macos_keychain_roundtrip_diagnostic.m -o /private/tmp/jkm-keychain-roundtrip
```

Die Statusprobe erwartet den absoluten Pfad des zu prüfenden Executables.
Die Roundtrip-Probe erwartet `--report <root>` mit einem neuen leeren privaten
Verzeichnis direkt im kanonischen System-Temporärordner, dessen Name mit
`jkm-keychain-roundtrip-` beginnt. Der Report wird exklusiv neu angelegt.
Für eine separate GUI-Diagnose bindet `JKMDiagnosticReportDirectory` denselben
Root im Info.plist; darin darf zuvor ausschließlich die eigene
`JKM-Schluesselbund-Diagnose.app` liegen. Der Start ohne Argumente zeigt die
Ergebnisse in einem nativen Dialog. Exit 0 bestätigt nur den geschriebenen
Report; die einzelnen Statuscodes und `secret_matches` bestimmen das Ergebnis.

Am 08.09.2026 wurde der Fehler auch nach manuellem Entsperren und im separat
per Computer-Use geprüften Diagnosefenster reproduziert: Vertrauensreferenz
und ACL-Erzeugung Status 0, `SecItemAdd=-25293`. Lesen/Löschen nicht erreicht.
Die verbleibende Ursache ist offen; diese Diagnose ist keine Paketfreigabe.


## Paketnachweis 0.4.2 / Build 402 – 11.10.2026

Implementierung und Version sind lokal committed (`bfe7c5b`, danach Versionscommit `2ac4e28ca5ea1545445922f228ac941bd944e190`). Der Build entstand ausschließlich aus diesem sauberen Versionscommit im detached Release-Worktree. Die spätere Dokumentation verändert weder diesen Quellcommit noch Paketbytes. Keine Installation, kein Push, kein Tag und keine Veröffentlichung.

- Elf von elf Paketgates bestanden: DMG-Verifikation, Metadaten, arm64, tiefe strikte Signatur, native Bibliotheken, Sparkle-Version, Erststart/Restart, verbotene Inhalte, Entwicklerpfade, Pilotfeed und deaktivierter Stable-Kanal.
- Paketierter Restore-Worker-Smoke bestanden. Dieser kontrollierte Nachweis erreicht RESTORE_READY und Workerstart und bricht vor dem Datenaustausch ab; er ersetzt keine vollständige reale Restore-/PO-Abnahme.
- Paketierter Export-Bytecode aus PYZ und unveränderte Originalpflanzen am tatsächlichen Frameworks-/Resources-Pfad erfolgreich in Memory gerendert. Dies prüft Code-/Ressourcenlieferung, keine zusätzliche Anmeldung oder Bedienabnahme der installierten App.
- Qt-Exportaktion mit ausschließlich synthetischen Daten bei 1180×760, 1280×800 und 1400×900 sichtbar/aktiv; End-to-End-Interaktion inklusive Abbruch und Schreiben in der fokussierten Testsuite geprüft. Alle 31 Seiten des 331-Kompetenzen-Beispiels visuell und textlich vollständig geprüft.
- DMG: `Jenaplan-Kompetenzmanager-0.4.2-macOS-arm64.dmg`, 205.050.568 Bytes, SHA-256 `481f982711305e7ccb58da2d094f4b167f24562e0e7685450b8a7a427152a37d`.
- Alle vier Releaseartefakte erneut gegen Manifestgröße und SHA-256 geprüft. Lokales Manifest: `release/output/0.4.2-build402-2ac4e28ca5ea/release-manifest.json`, Phase `package_verified`, kein Fehler, Restore `passed`.

Technische Quell- und Paketvorbereitung ist abgeschlossen. Offen bleiben die letzte reale PO-Bedienabnahme und die getrennte bewusste Veröffentlichung im Pilotkanal. Vollständiger Restore, Developer ID, Notarisierung, Stable- und schulische Betriebsfreigabe werden durch diese technischen Prüfungen nicht erteilt. Der frühere Fehler von Build 401 trat weder in den erneuten Originalpaketprüfungen noch in der aktuellen nativen Prüfung außerhalb der Sandbox auf; seine ursprüngliche Ursache bleibt ungeklärt.

## A2 – native macOS-Paketabnahme angehalten – 14.10.2026

Status: NO-GO; unveröffentlicht nach 0.4.4 / Build 404. Geprüfter Entwicklungsstand: 3ad1c0ff7e83c13a6df87d53c713264bed760246, Branch spike/python-gui. Arbeitsbaum und Staging zu Beginn leer. Kein Paketbau, kein Appstart, keine Installation, kein Keychainzugriff und keine Produktcodeänderung in diesem Auftrag.

Phase-3-Stop-Blocker: packaging/macos_pilot.spec setzt BUNDLE_ID fest auf de.jenaplan.kompetenzmanager; scripts/build_macos_pilot.sh bietet getrennte Build-/Dist-Roots, aber keine getrennte Bundleidentität. scripts/audit_macos_app_bundle.py verlangt ebenfalls die Produkt-ID. scripts/create_isolated_macos_test_app.py akzeptiert ausschließlich eine bereits mit Produkt-ID erzeugte Quell-App und vergibt erst danach eine UUID-Bundle-ID. Der Auftrag untersagt ausdrücklich das Fortfahren, wenn die vorhandene Pipeline zwingend produktive Bundleidentitäten benötigt. Die nachgelagerte Testkopie genügt deshalb diesem Testvertrag nicht. Kein unsicherer Ersatz und keine zweite Paketpipeline entwickelt.

Durchgeführt: read-only Quellprüfung von Startupkomposition, A2-Guard, A1-Inventar, Existing-only-Keyport, Restore-/Worker-/Confirm-/Restartpfad und vorhandenen Paket-/Securitywerkzeugen; unabhängiges technisches Quellreview. Beobachtete Reihenfolge: Root-/Artefaktpreflight, Runtime-Lock, A2-Veto vor Rootpublikation/Restore, erneutes Inventar nach Recovery, danach First-Run-Kandidatur und Security/Auth/Cipher. Existing-only-Port verwendet direkte DMK-Lesung und authentisiertes Envelope, keinen Create-/Delete-Lifecycle. Diese Quellbefunde sind keine native ACL-/Paketnachweise.

Aktueller Testlauf: rtk proxy python3 -m pytest tests/test_isolated_macos_test_app.py tests/test_security_release_packaging_sprint12.py::test_044_release_versions_and_security_dependencies_are_pinned -q: 24 bestanden, 0 Skips, 0.35 s, Exit 0. Das sind synthetische Launcherprüfungen mit gemocktem execve und statische Paketkonfigurationsprüfungen; kein eingefrorener/native paketierter A2-Produktstart. Die vorher dokumentierten 93 gezielten Tests, 2897 Produkttests, 104 bestehenden Skips und 120 Unterprüfungen wurden in diesem Auftrag nicht erneut ausgeführt und bleiben historische A2-Nachweise.

Offen/nicht ausgeführt: alle 20 paketierten Startupfälle des Auftrags, native Existing-only-Keychain-/ACL-/Locked-Keychainprüfungen, paketierte SQLCipher-4.17/CommonCrypto-Provideridentität und Cipherparameter, Dateizugriffs-/Eigentümer-/Pfadgates am neuen Paket, Bundle-/Signaturintegrität, Restore-Koexistenz und Worker-/Restart-Handoff samt realen Parent-/Workerabbrüchen, parallelem Start und Recoveryneustart sowie manuelle sichere Fehlerdarstellung. Keine Testinstallation, keine synthetische Installations-/Keychainidentität und kein internes App-/DMG-Testartefakt erzeugt. Keine Stromausfallschutzbehauptung.

Bewertung: kein neuer P0-Produktfehler nachgewiesen; ein P1-Abnahmeblocker wegen fehlender auftragskonformer Paketidentität. Produkt-P0/P1 im nativen Kontext mangels Paket nicht abschließend bewertbar. Bestehende P2-Grenzen (konsistenter lokaler Rollback/Evidenzentfernung, alter Build-404-Code, gleichbenutzerprivilegierte TOCTOU-/ABA-Grenzen, externer Interpreter der Testkopie) bleiben offen. Keine Paketfreigabe, kein Staging und kein Commit bei diesem Blocker.

Unveränderlichkeit read-only verifiziert: assets/competency_plants/Pflanzenbilder-transparent.zip: 439602 Bytes, fünf Einträge, ZIP-Integritätsprüfung ohne Fehler, SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4. Vorhandene veröffentlichte Build-404-DMG: SHA256 d55c21c35509a034b3b249450478dc82514f7f296ab5e494799dae0fd93f311e. Beide stimmen mit den bisherigen Registern überein. Produktinstallation, Produktdaten und Produktschlüssel wurden nicht geöffnet oder verändert; src/version.py, Releaseartefakte und Pilotfeed wurden nicht verändert. Kein Push, Tag, Release, Build 405 oder Folgepaket.

## Isolierte macOS-Testpaketpipeline vorbereitet – 14.10.2026

PO-Auftrag: ausschließlich Voraussetzungen und automatisierte Vorabprüfung für ein internes Testpaket; keine App-/DMG-Erstellung oder native A2-Abnahme. Baseline 3ad1c0ff7e83c13a6df87d53c713264bed760246 / spike/python-gui; genau die vier vorhandenen NO-GO-Dokumentänderungen geprüft und als sachlich korrekter historischer Nachweis unverändert erhalten. Der vorstehende Paket-NO-GO beschreibt die damalige unparametrisierte Pipeline, nicht eine native Prüfung der neuen Implementierung.

Bestehender Builder und Spec besitzen jetzt das explizite Profil internal-test. Default product behält Bundle-ID, Appname, UUID4-Enrollment, drei Keychain-Services/Accountformat, Sparkle-Feed, Version 0.4.4/404, Securitybasis und Releasepfade. Testprofil bindet vor Buildwrites UUID4-Test-/Installations-ID, abgeleitete Bundle-/App-/Service-/Accountidentitäten, eigenen privaten synthetischen Root sowie neue Build-/Artefaktziele. Vollständiger Snapshotdigest und exakter versiegelter Hook/Config werden vor Analysis geprüft. Keine Auswahl zur Laufzeit durch Environment, keine Produktfallbacks, keine größeren Architekturänderungen.

Jeder eingefrorene Normal-/Worker-/Restartprozess prüft vor main den gleichen Root, Executablepfad, Bundle/Config/Digest und CLI-Kontext. Keychainadapter verwenden getrennte DMK-, Device-Credential- und Monotonic-Anchor-Services sowie test-v1:<TestUUID>:<InstallationUUID>:<ItemUUID>; eine fremde Installations-ID sperrt vor Keychainaufruf. Nur der Enrollment-Installations-ID-Fabrikport ist im Testkontext gebunden; weitere Schlüssel-/Database-Context-UUIDs, KDFs, Cipherparameter und Final-V4-Schema bleiben unverändert. Keine Auth-/Recovery-/Runtimefreigabe aus einem Paketprofil.

Im Testprofil keine Sparkle-Bridge/Framework oder SU*-Plisteinträge, kein nativer Updateadapter, keine Signierungsidentitätssuche, keine Developer-ID, Timestamp-/Notarisierung-/Entitlements-/Installations-/DMG-/Releasezweige. Ausschließlich spätere Ad-hoc-Testsignierung innerhalb des bestehenden Builders; kein neues Signingversprechen. Das vorhandene Bundleaudit erwartet explizit die versiegelte Testidentität, behält alle Security-/Provider-/Architekturprüfungen; nur die exakt gebundenen nicht geheimen Identitätspfade werden bei der Prüfung auf unerwartete Entwicklerpfade normalisiert.

Native A2-Abnahme bleibt offen: alle 20 Startupfälle, tatsächlich eingefrorene Hookreihenfolge, native Bundle-/Signatur-/ACL-/Keychain-/SQLCipher-Identität, Restore-/Worker-/Restart-/Crash- und manuelle Fehlerprüfungen. Profilprüfung ist keine native Paketfreigabe. Bekannte P2-Grenzen: kooperative Prozess-/Rootgrenzen statt OS-Sandbox, keine Abwehr beliebiger gleichbenutzerprivilegierter Code-/Loader-/TOCTOU-Manipulation, kein Stromausfallschutzbeweis; bestehende A2-Rollback-/Evidenzgrenzen bleiben. Das Testpaket wäre lokal root-/pfadgebunden und darf nicht als Build 404 verteilt werden.

Kein Produktdaten-/Produktschlüsselzugriff, kein App-/DMG-Bau, kein Push/Tag/Release/Feed-/Versionswechsel. Pflanzen-ZIP 439602 Bytes/fünf valide Einträge/SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4 und veröffentlichte 404-DMG SHA256 d55c21c35509a034b3b249450478dc82514f7f296ab5e494799dae0fd93f311e read-only bestätigt.

### Identitätsannahmen und Codebelege

| Identität/Vertrag | Produktdefault und isolierte Projektion |
| --- | --- |
| Bundle, Appname, Executable, Info.plist | packaging/macos_pilot.spec vor Analysis; src/desktop_app/runtime.py APP_NAME/APP_BUNDLE_ID; Appinfo übernimmt Testnamen nur nach Bindung |
| Produktroot | runtime.application_data_root: produktiv Application Support/APP_NAME bzw. bestehender Override; Testprofil ausschließlich festes data unter eigenem privaten systemtemporären Container |
| Installations-ID | security.application Enrollment: normale UUID4-Fabrik; security.startup injiziert ausschließlich im Testprofil die vorgeprüfte Installations-ID |
| DMK-Service/Account | security.infrastructure.data_master_key_store: unveränderter Produktservice, keychain_service/keychain_account projizieren Testnamespace und verweigern fremde Installation |
| Gerätecredential | security.infrastructure.platform_auth: eigener Service und gleicher Accountbindungsvertrag, bestehende native ACL/LocalAuthentication unverändert |
| Sicherheitsanker | security.infrastructure.monotonic_anchor_store: eigener monotonic-security-anchor-Service; Installations-/Database-Context-Accountbindung bleibt |
| SQLCipher/DMK/DB-Context | bestehender qualifizierter Wheelhash, unveränderte Binding-/Engine-/CommonCrypto- und Cipherverträge; Schlüssel und DB-Context entstehen weiterhin im bestehenden First Run innerhalb gebundener Testinstallation |
| Worker/Restart | restore_worker.resolve_restore_worker_launch und final_v4_runtime_adapters.DesktopFinalV4RestartLauncher: dasselbe frozen sys.executable; jeder Prozess durch denselben versiegelten Hook, fremde Handoff-/Rootpfade gesperrt |
| Rechte/Signatur | bestehende PyInstaller EXE ohne zusätzliche Entitlements; Testzweig nur codesign --sign -, keine Security-Identitätssuche, Developer-ID oder Notarisierung |
| Updates | Produkt-Sparkle unverändert; Test-Spec ohne Bridge/Framework/SU*, nativer Adapter blockiert auch direkte Konstruktion |
| Releasepfade/Version | Testartefakte ausschließlich im eigenen artifacts-Root; Builder endet vor DMG/Release. src/version.py bleibt 0.4.4/404; kein Testpaket als neuer 404-Release |

### Reine Vorabprüfung – erzeugt keine App

Explizite Profilwahl und vollständig vorhandene private synthetische Rootautorität sind erforderlich. Eine vorhandene leere Testwurzel wird nicht still als Produktwurzel angelegt. JSON hat exakt diese Felder, keine weiteren: profile, test_id, installation_id, bundle_id, app_name, runtime_root, build_root, dist_root, keychain_services, account_prefix, worker_bundle_id, restart_bundle_id, updates, signing, entitlements. Doppelte JSON-Schlüssel sind unzulässig. UUID4-Test-ID und UUID4-Installations-ID müssen verschieden sein. Bundle: de.jenaplan.kompetenzmanager.internaltest.t<UUIDhex>; App: JKM-Interner-Test-<UUIDhex>. Drei Services sind Bundle + .data-master-key/.device-credential/.monotonic-security-anchor. Accountpräfix test-v1:<TestUUID>. Worker-/Restart-Bundle gleich Testbundle, updates=false, signing=ad-hoc, entitlements=null.

Container: <kanonischer Systemtemp>/jkm-internal-test-<UUIDhex>, privat 0700/eigener Owner/keine Pfadlinks. runtime_root=data mit bestehendem synthetic_test-Marker; vor Build keine weiteren Runtimeartefakte. build_root=build und dist_root=artifacts dürfen noch nicht existieren. Fehlende, beschädigte, produktive, unbekannte oder widersprüchliche Identitäten/Roots sowie fremde Signing-/Feed-/Outputoverrides führen vor Buildwrites zu test_profile_invalid. Die rein lesende Prüfung lautet:

```bash
rtk proxy bash scripts/build_macos_pilot.sh --package-profile internal-test --test-profile /absoluter/pfad/testprofil.json --validate-profile-only
```

Produktdefault read-only prüfen:

```bash
rtk proxy bash scripts/build_macos_pilot.sh --validate-profile-only
```

Die Profile werden ausschließlich für einen später ausdrücklich beauftragten nativen Paketlauf vorbereitet. Ein tatsächlicher Build würde dieselbe Pipeline mit denselben Eingaben verwenden, mit Snapshotdigest vor erster Artefakterzeugung, neu erzeugtem versiegeltem Hook, unverändertem qualifiziertem SQLCipher-Wheel und vollständigem Bundleaudit. Dieser Auftrag hat keinen solchen Lauf ausgeführt. Die historische create_isolated_macos_test_app-Kopie ersetzt weder dieses Profil noch dessen native Gates.

Abschlussprüfung dieses Vorbereitungsauftrags: 65 neue gezielte Tests ohne Skip bestanden (rtk proxy python3 -m pytest tests/test_macos_test_package_profile.py -q, 3.82 s, Exit 0). Erweiterter gezielter Zwischenstand: 201 bestanden / ein bestehender qualifizierter Runtime-Skip (25.88 s). Erster vollständiger Lauf: 2954 bestanden / ein Appinfo-Quellregressionstest fehlgeschlagen / 104 bestehende Skips / 120 bestandene Unterprüfungen (354.50 s, Exit 1); kein Abnahmenachweis. Explizite produktive Appinfo-Namenskonstante erhalten und nur im gebundenen Testprofil überlagert, bestehender Einzeltest grün. Ein folgender Zwischenlauf wurde vor Abnahme für die letzte Pfadhärtung beendet (Exit 130). Finaler regulärer Lauf am endgültigen Code: rtk proxy python3 -m pytest tests -q -rs → 2962 bestanden, 104 unveränderte bestehende Skips, 120 bestandene Unterprüfungen, 354.19 s, Exit 0. Keine neue Skipregel, Sicherheitsausnahme oder Lockerung bestehender Tests.

Testnachweise sind synthetische Unit-/Integrationstests, echte Builder-Prozesse ausschließlich mit Vorabprüfung oder ungültigem Profil vor Build sowie Spec-/Hookprüfungen mit inerten Konstruktoren/Bundle-Reads. Kein nativer eingefrorener App-/SQLCipher-/Keychain-/Signingnachweis aus diesem Auftrag. Unabhängiger Architektur-/Diff-/Technical-Review einschließlich letzter Pfadhärtung: P0 = 0, P1 = 0, keine neue offene P2-Implementierungslücke; dokumentierte Sicherheitsgrenzen bleiben. Historischer NO-GO in allen vier bisherigen Dokumenten identisch und unverändert erhalten. Shellsyntax- und Diffprüfung erfolgreich. Damit Commit-Gate für die vorbereitete Testpipeline erfüllt; native A2-Paketabnahme weiterhin offen. Kein Testpaket gebaut und keine Veröffentlichung erfolgt.


### Native A2-Paketabnahme – 14.10.2026 – NO-GO vor Buildwrites

Auftragsbaseline: HEAD `720c917dabbea9a2a0bfe7ab28c182b743e9564a`, Branch `spike/python-gui`; Release-Referenz `79d59591344397fdc462f40e1c0335c75066463e`, 0.4.4/404. Ausgangsarbeitsbaum sauber, Staging leer. Kein Code-/Profil-/Versionswechsel.

Explizit ausgewählter vollständiger Snapshot: Test-ID `cd4b344f-537b-48bd-9971-031427207b2e`, Installations-ID `e575817a-cbdf-4aa2-9dd5-4aaa9ed055a7`; App/Executable `JKM-Interner-Test-cd4b344f537b48bd9971031427207b2e`; Bundle/Worker/Restart `de.jenaplan.kompetenzmanager.internaltest.tcd4b344f537b48bd9971031427207b2e`. DMK-/Device-/Anker-Services verwenden diesen Bundlepräfix und die drei kanonischen Suffixe, Accountpräfix `test-v1:cd4b344f-537b-48bd-9971-031427207b2e`. Updates false, signing ad-hoc, entitlements null. Vollständiges JSON unter `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-cd4b344f537b48bd9971031427207b2e/profile.json`; SHA256 des kanonischen Snapshots `2a80826f673e07a1b80fa27ef923ecddc0131df7a86b90bee2f2d187daf410de`, separat mit festem Erwartungswert bestätigt. Container/Root privat, eigener Owner, synthetischer Marker, neue getrennte build/artifacts-Ziele. Diese flüchtigen Pfade sind keine dauerhafte Paketfreigabe.

Ausgeführt: `rtk proxy bash scripts/build_macos_pilot.sh --package-profile internal-test --test-profile <obiger absoluter Profilpfad> --validate-profile-only` → Exit 0. `rtk proxy python3 -m pytest tests/test_macos_test_package_profile.py -q` → 65 bestanden, 1.06 s, Exit 0, keine Skips. Qualifizierter Buildinput `/private/tmp/jkm-cipher404-build-a/wheel/sqlcipher3-0.6.2+jkm.sqlcipher4170.1-cp314-cp314-macosx_11_0_arm64.whl`: SHA256 `9ce432941a45f28af3877192149ab2583ae22f466e3b22c2a7323c5a84c577f9`, exakt Manifest. Dies ist nur ein Inputhashnachweis, kein neuer nativer CommonCrypto-/Provider-/keyed-Reopen-Nachweis.

Ein realer vorhandener Builder-Aufruf mit derselben expliziten Profilwahl und ausschließlich dem qualifizierten Wheel als `JENAPLAN_SQLCIPHER_417_WHEEL`-Buildinput endete Exit 2: `Abbruch: Build-Ziel liegt nicht in einer freigegebenen Build- oder Temporärwurzel.` Keine Sicherheitsumgehung oder Mockausführung.

Konkreter Blocker: `validate_test_profile` verlangt den kanonischen `Path(tempfile.gettempdir()).resolve()`-Container unter `/private/var/folders/.../T`; `validate_output_root` im Shellbuilder erlaubt dagegen den textuellen TMPDIR-Präfix `/var/folders/.../T/` sowie `/private/tmp/` und Repository-build/dist. Auf diesem Host stimmen kanonischer Profilpfad und textueller TMPDIR-Präfix nicht überein. Die validate-profile-only-Abkürzung endet vor dieser zusätzlichen Zielprüfung und ist daher kein vollständiges Pre-Build-GO. Die vorläufige positive Profilbewertung wurde durch den realen Builder widerlegt. Kein TMPDIR-Override, Symlink, alternativer Root oder manuelle Plistbearbeitung wurde versucht; keine Folgeimplementierung.

Nach dem Abbruch erneut bestätigt: build und artifacts existieren nicht; data enthält ausschließlich `.jkm-runtime-root-v1`; Snapshotdigest unverändert. Kein venv, Hook, Payload, App, DMG, Signierungs- oder Runtimeartefakt erzeugt. Profil-/Rootvorbereitung war die einzige synthetische Testanlage. Der tatsächliche Abbruch erfolgte vor dem ersten mkdir des Builders und vor jeder Securitybridge-/Keychain-/SQLCipher-Ausführung.

Native Startupfälle 1–20 sämtlich NICHT AUSGEFÜHRT. Reihenfolge Root/Inventar → Lock → erneute Prüfung → Guard → Restore → First Run/Security/Cipher nur im Quelltext geprüft, keine paketierte Prozessreihenfolge bewiesen. Bundle-ID/Executable/Digest/Ad-hoc/Entitlements/Services/Updatefreiheit/Worker/Restart/enthaltene Cipherbasis/Final-V4-Paketkompatibilität sämtlich offen. Native Keychainfälle einschließlich vorhandener/fehlender/verweigerter/widersprüchlicher Identität, CommonCrypto/Provider/keyed Reopen/Integrität, Restore READY/Handoff/Parent-/Workerende/Restart/Recovery/Konflikt/Crashgrenzen sämtlich offen. Keine manuelle UI-Prüfung ausgeführt. Kein Stromausfallversprechen.

Nach NO-GO keine erweiterte Regression oder reguläre Produktsuite ausgeführt; frühere Testergebnisse sind kein aktueller Nachweis. Keine neuen Skipregeln/Testausnahmen/Gatelockerungen. Keine Freigabe, kein Commit/Staging, kein Push/Tag/Release/Feed/Version/Notarisierung/Installation, keine Migration/Upgradeaktivierung. Produkt-App/-Daten/-Schlüssel wurden durch keinen ausgeführten Schritt geöffnet oder angesprochen. Build 404 und Pilotfeed wurden nicht geändert; lokales dist-Verzeichnis nicht vorhanden, daher kein frischer DMG-Hashnachweis. Pflanzen-ZIP weiterhin 439602 Bytes, fünf valide Einträge, SHA256 `ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4`.

Unabhängiges read-only Architektur-/Sicherheitsreview durch separaten Reviewer bestätigt denselben Pfadvertragwiderspruch und die Abbruchstelle vor mkdir. P0: kein Befund im ausgeführten Umfang; P1: ein blockierender verpflichtender Paketabnahmeweg; P2: bestehende dokumentierte kooperative Root-/Prozess-, TOCTOU- und Rollbackgrenzen bleiben, hier keine neue native Bewertung. Keine zulässige Alternative ohne verbotene Umgebungs-/Pfadumgehung oder Folgecodeänderung. Reviewumfang ist der Pre-Build-Blocker und die sichtbare Quellkomposition; kein vollständiges natives A2-Sicherheitsreview. Ergebnis: NO-GO für A2-Nativabnahme.

Review zur Testabdeckung: Der erfolgreiche Builder-Profiltest nutzt den validate-profile-only-Frühausstieg und erreicht mit gültigem Profil die nachgelagerte Outputprüfung nicht; das erklärt die unentdeckte Paketierungslücke. Kein Test wurde verändert. Abschließendes git diff --check bestanden; ausschließlich CHANGELOG.md und docs/RELEASE_AUTOMATION.md geändert, Staging leer.


### Korrektur der internen Buildpfadidentität – unveröffentlicht nach Build 404

Der vorstehende historische NO-GO bleibt erhalten. Im Folgeauftrag wird ausschließlich sein P1-Pfadblocker korrigiert, keine native A2-Abnahme durchgeführt. Bestand: HEAD 720c917, spike/python-gui; die beiden vorhandenen Nachweisänderungen wurden erhalten.

Read-only Ursachenreproduktion am Host: /var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T und /private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T haben beide Device 16777234/Inode 245943, Owner 501, Modus 0700; samefile ist wahr. Das alte textuelle Shellmuster ist falsch. Die Abweichung war hier ausschließlich die systemeigene /var-Aliasdarstellung, keine bloß ähnlich aussehende Zeichenkette.

Gemeinsamer Vertrag im bestehenden Profilmodul: Nur die OS-Tempautorität wird kanonisch aufgelöst. Abweichende Darstellung ist ausschließlich für root-eigene Systemlinks /var → /private/var und /tmp → /private/tmp zulässig, mit exaktem Linkziel, realer samefile-Identität und anschließender descriptorrelativer O_DIRECTORY/O_NOFOLLOW-Prüfung sämtlicher kanonischer Pfadkomponenten. Profilpfade werden nicht normalisiert oder umgeschrieben. Container/data bleiben vorhandene private Verzeichnisse des aktuellen Owners mit strengem Modus, synthetischem Marker und exakten UUID-/Rootgrenzen; build/artifacts müssen weiterhin fehlen. Der bestehende Schutz vor Produktroots bleibt aktiv. Das Produkt-Shellgate und seine Defaults bleiben unverändert.

Buildzielprüfung und Profilvalidator verwenden denselben Vertrag. Ein flüchtiger Snapshot der Device/Inode-Identitäten aller kanonischen Temp-/Container-/data-Ahnen wird zusätzlich mit dem CLI-Profildigest gebunden und beim Zielgate sowie direkt vor ersten Buildwrites erneut verglichen. Dieser Snapshot wird nicht Teil des versiegelten Profilformats. Beobachtete Pfadersetzungen sperren; kein Schutzversprechen gegen beliebige gleichbenutzerprivilegierte ABA-Manipulation oder Rennen nach dem letzten Check. Keine NOFOLLOW-/Descriptorprüfung wird durch realpath umgangen; untrusted Descendants erhalten keinerlei Symlinkfreigabe.

Digestvertrag unverändert: SHA256 von json.dumps(profile.as_dict(), sort_keys=True). Keine Felder-, Format- oder Pfadinterpretationsänderung für vorhandene kanonische Profile; keine neue Profilversion notwendig. Historischer Snapshot weiterhin Digest 2a80826f673e07a1b80fa27ef923ecddc0131df7a86b90bee2f2d187daf410de. Manipulierter Digest wird vor Writes abgewiesen. Keychain-Namespaces, Worker/Restart, Updates=false, Ad-hoc-only, Produktversion und Cipherbasis bleiben unverändert.

--validate-profile-only erreicht im internal-test-Zweig jetzt das gleiche vollständige read-only Pfad-/Produktroot-/Neuzielgate wie der Buildpfad, statt vor der Zielprüfung zu enden. Der zuvor fehlschlagende absolute historische Profilpfad ergibt Exit 0 mit unverändertem Snapshotdigest. build/artifacts fehlen danach; data enthält ausschließlich .jkm-runtime-root-v1. Keine App/DMG/Hook/venv/Keychain/First-Run-/Cipheranlage. Negative reale Pipelinevorprüfungen mit Produktartefaktpfad, relativer Root und manipuliertem Digest ergeben Exit 2 vor Buildwrites.

Gezielter Zwischenstand: 84 Profil-/Pfadtests bestanden, keine Skips, 1.49 s. Erweiterte bestehende Paket-/Runtime-/Root-/Releasepipeline-Regression: 196 bestanden, zwei bestehende explizite Runtime-/Live-Release-Skips, 6.72 s. Keine neue Skipregel, Ausnahme oder Abschwächung. Erster Zwischenlauf nach der Korrektur hatte 17 Fehler/48 bestandene Tests: Systemlinks verwenden relative Linkziele private/var; exakte Prüfung auf das parentrelative Ziel korrigiert, erneuter ursprünglicher Profiltestlauf 65 bestanden. Diese Fehlversuche sind keine Abnahme. Shellsyntaxprüfung bestanden. Reguläre Produktsuite und unabhängiges Review werden separat abschließend ergänzt.

Unabhängiges read-only Architektur-/Sicherheitsreview der konkreten Korrektur: P0=0, P1=0, keine neue offene P2-Implementierungslücke. Reviewer führte separat 84 Profil-/Pfadtests aus (1.54 s, keine Skips). Gemeinsamer NOFOLLOW-Vertrag, begrenzte OS-Aliasautorität, unveränderte Digest- und Produktidentitäten sowie read-only vollständiges Zielgate bestätigt; dokumentierte ABA-/TOCTOU-Grenzen bleiben. Keine native Abnahme aus diesem Review.

Finaler regulärer Lauf am endgültigen Code: rtk proxy python3 -m pytest tests -q -rs → 2981 bestanden, 104 unveränderte bestehende Skips, 120 bestandene Unterprüfungen, 356.18 s, Exit 0. Keine Tests ausgeblendet oder Skipregeln ergänzt. Abschließender Diffcheck bestanden. Commit-Gate der reinen P1-Korrektur erfüllt: positive vollständige read-only Vorprüfung, sichere negative Tests, gezielte/erweiterte/reguläre Suite und unabhängiges Review ohne P0/P1. Produktpipeline, Produktdaten/-schlüssel, Build 404 und Feed unverändert. Pflanzen-ZIP erneut 439602 Bytes/fünf valide Einträge/SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4. Kein Build, keine App/DMG, kein Push/Tag/Release. Pfadblocker behoben, Pre-Build-Pfadgate bestanden; native A2-Paket-/Keychain-/Restore-/UI-Abnahme weiterhin ausstehend.


### Erneute native A2-Paketabnahme – 14.10.2026 – NO-GO im Smoke-Einstieg

Baseline HEAD 8ad26848d867c6d2311b34bef968c0d3ab6f560a, Branch spike/python-gui, Arbeitsbaum/Staging zu Beginn sauber. Keine Folgecodeänderung. Der historische Pfad-NO-GO und dessen Korrektur bleiben erhalten.

Erster gestarteter Paketlauf mit historischem Testprofil cd4b344f blieb ohne verwertbares Abschlussprotokoll; nach Wiederaufnahme war dessen Prozesshandle nicht mehr vorhanden. Beobachtet: nur Hook/Profil/venv, venv nur pip, keine App. Weder Erfolg noch konkrete Abbruchursache daraus abgeleitet. Keine Fortsetzung in bereits belegten Artefaktzielen.

Neuer unabhängiger Container: /private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-67680b19b7294b7d8e6133a890c7d2e1. Test-ID 67680b19-b729-4b7d-8e61-33a890c7d2e1, Installation baf84ad7-5f41-4867-8a0d-acc41ad9159e. Vollständiges Profil profile.json, Snapshotdigest b8f9bbf24b6d2f4671763f8dcd1f6115b6af195e54ef40eb98a4a3fd8f5027dd. Pre-Build-Profil-/Zielgate Exit 0. Bundle/Worker/Restart de.jenaplan.kompetenzmanager.internaltest.t67680b19b7294b7d8e6133a890c7d2e1; App/Executable JKM-Interner-Test-67680b19b7294b7d8e6133a890c7d2e1. Drei Keychainservices mit genau diesem Testbundlepräfix; Account test-v1:67680b19-b729-4b7d-8e61-33a890c7d2e1. Keine Produktidentität als aktive Testidentität.

Bestehende Buildpipeline mit explizitem internal-test-Profil, qualifiziertem manifestgebundenem Build-404-Wheel und Netzwerkzugriff für bestehende exakt festgelegte Buildabhängigkeiten ausgeführt; kein Securityoverride. build-run.log und build-exit.txt im obigen Container: Exit 0. Tatsächlich erzeugte App: artifacts/JKM-Interner-Test-67680b19b7294b7d8e6133a890c7d2e1.app. Kein DMG, kein Produktinstallationspfad, keine Notarisierung/Release-Signatur/Veröffentlichung.

Bestandene native Paketgates: strikte Deep-Signatur vor und nach Appöffnung/Smoke Exit 0; Signature=adhoc, TeamIdentifier=not set, kein Entitlementpayload. Info.plist bestätigt Testbundle, App/Executable und exakten Snapshotdigest. Bestehendes vollständiges Bundleaudit status=ok, forbidden_artifacts=0, 373 reine arm64-Mach-O, 296 RPATHs, Updatekomponenten-/SU*-Ablehnung und eingefrorener Profilhook bestanden. Tatsächlich eingefrorener Runtimeaudit: Binding 0.6.2+jkm.sqlcipher4170.1, SQLCipher 4.17.0 community, SQLite 3.53.3, Provider commoncrypto, integrity=[]; enthaltene native Extension _sqlite3.cpython-314-darwin.so und Linkage durch bestehenden Auditor bestätigt. Dies ersetzt keine vollständige Final-V4-Daten-/FK-/keyed-Reopen-/Restoreabnahme. Upstream-Buildpfadreferenzen vom Auditor gemeldet: 684, kein verbotener Entwickler-/Buildpfadbefund.

UI-Werkzeugprüfung: ausschließlich die exakte neue Test-App per absolutem Pfad geöffnet. Sichtbar war AuthenticationDialog mit lokaler Kontoeinrichtung, optionalem Namen, zwei Passwortfeldern, Hinweis auf zehn Recovery-Codes und Fortsetzen. Kein Passwort eingegeben, kein Kontoenrollment abgeschlossen; Dialog mit Close geschlossen (Werkzeug meldet App quit). Dies ist eine werkzeuggestützte Sichtprüfung, keine menschliche manuelle Abnahme. UI-Auswahlaufruf blockierte ungewöhnlich lange; daraus keine Laufzeit-/Performancefreigabe abgeleitet.

Konkreter neuer Blocker: Paket-Executable mit --packaged-smoke-test initialize nativ aufgerufen. Exit 2, stderr: Packaged-App-Smoke abgelehnt: Packaged-Smoke ohne eigenes temporaeres Smoke-Verzeichnis abgelehnt. Vollständiges Ergebnis in first-run-smoke.json im Container. main._validated_packaged_smoke_data_root verlangt weiterhin ein Pfadsegment jenaplan-packaged-smoke-, während der versiegelte Testhook nur den exakten jkm-internal-test-<UUID>/data-Root zulässt. Argument ist im Profilhook explizit erlaubt, aber die nachgelagerte Smoke-Rootprüfung ist inkompatibel. Kein Root-/Environment-/Plistoverride, Symlink, Mock oder Umbenennung zur Umgehung versucht. Kein nativer First-Run-/Keychain-/Restoreerfolg aus diesem gesperrten Einstieg.

Nach normaler UI-Öffnung enthält data den synthetischen Marker, instance.lock und security; diese isolierten Startupwrites sind kein abgeschlossenes Enrollment oder Final-V4-Fachdatenbanknachweis. Keine produktive Installation geöffnet oder produktiven Daten/Schlüssel gezielt angesprochen. Keine vollständige Keychaintracing-Aussage: native bestehende/fehlende/verweigerte/widersprüchliche DMK-Kontexte sowie Repair-/Rotation-/Ersatz-DMK-Abwesenheit bei vollständig eingerichteter Installation bleiben ungeprüft.

Abnahmematrix: Startupfall 2 nur Einrichtungsdialog sichtbar, kontrollierter vollständiger First Run blockiert. Fälle 1 und 3–20 nicht nativ ausgeführt. Vollständige gefrorene Reihenfolge Root/Inventar → Lock → erneute Prüfung → Guard → Restore → First Run/Security/Cipher nicht dynamisch bewiesen. Restore READY/Vorbereitung/Worker-Handoff/Parent-/Workerende/Restart/Recovery/Konflikte/Crashgrenzen nicht ausgeführt. Fehlermeldungs-/Reparaturdialogprüfungen bei Upgradeevidenz und menschliche manuelle UI-Abnahme offen. Keine Stromausfallgarantie. Nach NO-GO keine Folgeimplementierung oder neue erweiterte/reguläre Produktsuite; vorherige 2981 Tests sind historischer Fixnachweis, keine neue A2-Nativabnahme.

Nur Nachweise ergänzt, kein Staging/Commit/Push/Tag/Release, kein Versions-/Feedwechsel, keine Migration/Upgradeaktivierung. Pflanzen-ZIP unverändert SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4. Build 404/Produktprofil/Pilotfeed unverändert. Die interne App ist nicht als neuer Build 404 veröffentlicht oder zur Verteilung freigegeben.

Unabhängiges read-only Review bestätigt P0 im geprüften Umfang nicht nachgewiesen, P1=1: der Smoke-Rootvertrag widerspricht jedem gültigen internal-test-Profil. Abbruch vor Inventar/Lock/Guard; kein dynamischer A2-Reihenfolgenachweis. Bestehende App-/Restore-Smokeskripte erwarten Produkt-Executable und fremde Roots, App-Smoke zusätzlich Produktbundle; Keychain-Skript ebenso, dessen --packaged-keychain-smoke ist vom Testhook nicht erlaubt. Profiltests decken Hookargumentzulassung, nicht die nachgelagerte widersprechende main-Rootprüfung. Keine produktive Identitätskollision aus diesem Befund ableitbar. Bestehende P2-Grenzen bleiben, keine neue native Bewertung. Review prüfte Quellverträge und Skripte, nicht selbst das Bundle oder Keychain. Abschluss: NO-GO für A2, kein Freigabecommit. git diff --check bestanden, nur CHANGELOG.md und docs/RELEASE_AUTOMATION.md geändert, Staging leer.


### Bindung des nativen Smoke-Roots – unveröffentlicht nach Build 404

Korrekturauftrag am HEAD 8ad26848d867c6d2311b34bef968c0d3ab6f560a, Branch spike/python-gui. Ausschließlich die zwei vorhandenen uncommitteten Nachweisänderungen waren vorhanden und bleiben vollständig erhalten. Gitverlauf bestätigt: 720c917 bereitete Testprofil vor; 8ad2684 korrigierte und committete den kanonischen TMPDIR-/Buildzielvertrag. Keine unerwartete Codeänderung seitdem. Keine neue Paketierung beauftragt oder ausgeführt.

Fehler erneut nativ mit vorhandener isolierter App 67680b19 reproduziert: --packaged-smoke-test initialize → Exit 2, Packaged-Smoke ohne eigenes temporaeres Smoke-Verzeichnis abgelehnt. Der Builder bereitete den synthetischen Root vor, der Frozen-Hook aktivierte genau die vollständige versiegelte Profilidentität; main lehnte anschließend allein deren fehlendes historisches jenaplan-packaged-smoke-Präfix ab. Exakte Bundle-/Installations-/Serviceidentität und sichere Rootstruktur stimmen; kein Produktpfadkonflikt aus dieser Reproduktion. Die vorhandene App enthält weiter den alten Code und wird weder umgeschrieben noch neu signiert.

Kleinste gemeinsame Identitätsautorität: aktives MacOSTestPackageProfile plus unveränderter Frozen-Hook. verify_test_package übernimmt die bisherige Hookprüfung und wird von Hook, Smoke-Einstieg und read-only Runner-Vorprüfung gemeinsam verwendet: vollständiger aktueller Profilvertrag, erwarteter Executable-/Apppfad, Bundle, Snapshot, kanonischer SHA256-Digest und Updatefreiheit. Aktiver Smoke setzt frozen, vorhandene Hookidentität und deren flüchtigen Parent-/Root-Device/Inode-Snapshot voraus; Root aus Hookumgebung muss exakt dem Profil entsprechen. Fehlender oder widersprüchlicher Kontext führt niemals zurück in den historischen Modus. Der Profilvertrag prüft UUIDs, Installation, drei getrennte Keychainservices/Accountpräfix, Worker-/Restartbundle, Ad-hoc-only und private synthetische Rootautorität. Kanonische NOFOLLOW-/Parentprüfungen bleiben erhalten; ein zusätzlicher rekursiver Links-/Typ-/Owner-/Rechtescan prüft aktuelle Rootinhalte. Wiederprüfung nach Scan, keine Sandbox-/ABA-/TOCTOU- oder Signaturersatzgarantie.

Historischer Modus ohne aktive Profilidentität behält expliziten Smoke-Marker, eigenen jenaplan-packaged-smoke-Root und synthetische Autorität. Environment kann keine Testprofilidentität aktivieren. Der interne Runner wird nur explizit mit --test-profile gewählt und erzeugt keinen zweiten Root; vor jedem Appstart prüft er erneut das versiegelte Bundle und dieselbe Root-/Prozessidentität. Kein APP_DATA_DIR-/QT-Override im internen Zweig; geerbter Fremdroot wird vor Appzugriff abgewehrt. Historischer Runnerdefault und seine Final-V4-/Cipher-/CommonCrypto-/Integritäts-/Klartextablehnungschecks bleiben unverändert. --preflight-only ist ausschließlich mit explizitem Testprofil zulässig und startet keinen Prozess.

Read-only Vorprüfung mit scripts/smoke_test_macos_app.py, absolutem bestehendem Bundle, profile.json und --test-profile --preflight-only: Exit 0, status preflight_ok, app_started false; Rootmetadatenbestand vor/nach exakt gleich. Snapshotdigest weiterhin b8f9bbf24b6d2f4671763f8dcd1f6115b6af195e54ef40eb98a4a3fd8f5027dd. Aktueller Smoke-Quellpfad zusätzlich mit inerten Paketdateien und simuliertem Frozen-Systemkontext geprüft: kein historischer Exit-2-Präfixkonflikt. Diese Unitattestation ist kein nativer Start des neuen Codes; kein Mock wird als Keychain-/Cipherabnahme ausgegeben. Der bestehende Altbinary-Fehler bleibt bis zu einer später ausdrücklich beauftragten neuen Testpaketierung erwartbar.

Prozessgrenzen: Parent/Runner wählen exakt die vorhandene Profilwurzel; App, Worker und Restart verwenden weiterhin denselben Frozen-Executable mit unverändertem Hook und dessen Argumentsperren. Wiederholte Prozesse prüfen erneut Bundle/Snapshot/Digest/Root/Installation und Keychainprojektion; flüchtige Pfadidentität gilt jeweils im eigenen Prozess. Produktionshandoffs nicht verändert. Bestehende restore-worker-/keychain-Smokeskripte besitzen eigene historische Roots und Produkt-Executable-Annahmen; sie wurden nicht pauschal freigegeben oder auf dieses Profil umgebogen. Der getrennte jenaplan-keychain-smoke- und jkm-security-packaged-Pfad bleibt außerhalb des internal-test-Hookvertrags. Deren Verwendung für A2 erfordert weiterhin ausdrücklich profilgebundene Prüfeinstiege; dieser Auftrag behauptet keine vollständige Restore-/Keychain-Nativabnahme.

Negativabnahme mit realen synthetischen Dateisystemfixtures und verbotenen Prozesslaunch-Sentinels: fehlender/manipulierter/alter Snapshot, Digest, Installation, Bundle, Keychainservice, Worker/Restart, Produkt-/beliebiger Temp-/relativer Root, ungebundenes historisches Präfix, fehlende Parameter, Symlink, unsicherer Parent, fehlender Marker, gewechselte Rootidentität, unfrozen Kontext und Produkt-Executable sperren. Fremde Root-/Argumentparameter stoppen sogar vor Paketreads. Vorhandene Profiltests behalten weitere Test-UUID-, Pfad-, Produktdefault-, Update-/Signing- und Final-V4-Grenzen bei. Keine künstliche native Testfreigabe.

Gezielter finaler Lauf: 124 Smoke-/Profil-/Runtimeprüfungen bestanden, keine Skips, 8.43 s. Vorheriger enger Zwischenstand 122 bestanden, davor ursprüngliche Regression 96 bestanden. Erweiterter Zwischenlauf 366 bestanden/ein bestehender qualifizierter Runtime-Skip, 61.40 s; finale erweiterte Suite und reguläre Produktsuite werden abschließend ergänzt. Unabhängiges Review fand P2: preflight-only fehlte zunächst der geerbte Fremdrootcheck, obwohl der echte Start sicher sperrte. Korrigiert und negativ getestet; Nachreview P0=0/P1=0, keine weitere konkrete Implementierungslücke. Bestehende ABA-/TOCTOU-Grenzen bleiben. Keine Skipregel/Testausnahme/Gatelockerung.

Finale erweiterte Regression am endgültigen Code: 368 bestanden/ein unveränderter bestehender SQLCipher-Runtime-Skip, 63.93 s. Finale reguläre Produktsuite: rtk proxy python3 -m pytest tests -q -rs → 3009 bestanden, 104 unveränderte bestehende Skips, 120 bestandene Unterprüfungen, 383.06 s, Exit 0. Diffcheck bestanden. Commit-Gate erfüllt: P0=0/P1=0 im unabhängigen Nachreview, neuer P2 korrigiert, sichere negative Tests, positive read-only Smoke-Vorprüfung, gezielte/erweiterte/volle Suite und unveränderte Produktpipeline. Auftragsdateien einzeln stagen; kein Build/DMG/App-Neustart nach Korrektur, kein Push/Tag/Release. Pflanzen-ZIP 439602 Bytes/fünf valide Einträge, SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4 unverändert. Produktinstallation, Daten/Schlüssel, Build 404, Version und Pilotfeed unberührt. Empfehlung: nächste ausdrücklich beauftragte A2-Abnahme benötigt eine frisch paketierte isolierte Test-App aus dem korrigierten Stand; alte Test-App nicht patchen und nicht als korrigierten nativen Nachweis verwenden. Alle 20 Startup-/Existing-only-Keychain-/Restore-/Worker-/Restart-/Crash-/manuellen UI-Pflichtgates bleiben ausstehend.


### Konsolidierte A2-Nativabnahme – PO-Folgeauftrag 14.10.2026 (laufend)

Baseline `6fd005ddac9c60f7b5580b4a242e12adf489c14a`, `spike/python-gui`; anfänglich Arbeitsbaum/Staging sauber. Nach gemeinsamem Audit autorisiert PO ausdrücklich die Behebung bis zur nativen Prüfung. Beide historischen Korrekturen (`8ad2684` Temp-/Buildpfad, `6fd005d` versiegelter Smoke-Root) sind im aktuellen Code vorhanden und synthetisch erneut geprüft. Zusätzlich drei P1-Infrastrukturkonflikte gefunden: Keychainrunner mit Produkt-Executable/fremdem Root/Bundlekopie, Restore-/Workerrunner mit Produkt-Executable/fremdem Root, Security-/Crashrunner mit ausgeschlossenem Migrationsmodul/fremdem Root/4.12-Erwartung. Kein Produktfehler daraus abgeleitet.

Die drei bestehenden Runner erhalten ausdrückliches --test-profile. Im internen Zweig gilt ausschließlich dasselbe MacOSTestPackageProfile mit exaktem Paket-/Executable-/Root-/Snapshot-/Digestkontext. Der historische 4.12-Migrationspfad bleibt ausgeschlossen; native Final-V4-Abnahme enthält keine Kryptografie-/Keychainmocks. Das neue Nativmodul wird im Produkt-Spec ausdrücklich ausgeschlossen. Startup-Proben beobachten echte Aufrufe und prüfen Reihenfolge/Mutationsveto. Native ACL-Fixture betrifft nur den synthetischen DMK-Account und eine prozesslokale Interaktionssperre, keine globalen Keychainsettings. Automatische Gates und menschliche UI-Abnahme werden getrennt ausgewiesen; automatischer Erfolg ist keine Produktfreigabe.

| Konsolidierter Einstieg | Interner Identitäts- und Pfadvertrag |
| --- | --- |
| Builder | Profil vor erstem Write; eigene Bundle-/App-/Installationsidentität, neue build/artifacts-Ziele; Ad-hoc-only, keine Entitlements, Updates/DMG/Verteilung aus |
| Spec | Profilwerte für App/Bundle, eingefrorener Hook/JSON, Digest im Info.plist; native Testmodule nur intern |
| Profilvalidator | Exakte UUIDs, Installation, Services/Accounts, Worker/Restart; private kanonische synthetische Root; keine Signing-/Feedoverrides |
| Frozen-Snapshot / Digest | internal_test_hook.py + internal_test_profile.json; SHA256 von json.dumps(profile.as_dict(), sort_keys=True); genaue Paketbindung, kein Environmentfallback |
| Buildzielvalidator | Gleiche Tempautorität/NOFOLLOW/Device-Inode-Wahrheit; erneute Kontrolle direkt vor Writes |
| Paketauditor | Explizites Profil, App/Plist/Snapshot/Digest, arm64 und native Bibliotheken, keine SU-/Sparklekomponenten; Builder prüft strikte Deep-Signatur |
| Startup-/First-Run-Smoke | Nur profile.runtime_root und profilgebundener Executable; erneute Paket-/Prozessbindung; Final V4, 4.17/CommonCrypto und stabiler Kontext |
| Keychain-Smoke | Mit Profil Existing-only in bestehender Testinstallation; nur die drei eigenen Services, Account profile.account_prefix:profile.installation_id:item_id; keine Bundlekopie |
| Restore-/Worker-Smoke | Mit Profil bestehende Keys, echter Worker und Restartprobe unter derselben Root-/Frozen-Executableautorität |
| Restart | Bestehender Desktoplauncher, gleicher Frozen-Executable, Root, Restore-ID/Token/Lock-FD und gleicher Hook |
| Security-/Crash-Smoke | Mit Profil tatsächliche Final-V4-Matrix, reale Kinder/SIGKILL/Restore; keine historische Migrationszulassung |
| Native Matrix | Geschlossene Hookmodi, echte main-Starts, native Keychain/SQLCipher/Prozesslocks; flüchtige Bestandkopien nur im privaten Profilcontainer, keine Schlüsseldateien |

Unabhängiges Vorreview fand drei Harnesslücken (Sollwerte, Reihenfolge, Parent-/Restartnachweis), vor Build korrigiert. Nachreview P0=0/P1=0 im Implementierungsumfang. Auch Hold-lock-Timeout und explizite Prüfung des Restart-Prozessendes ergänzt. Gezielt 265 bestanden ohne Skips (37.85 s); weitere Paket-/Release-/Runtimechecks 110 bestanden/ein bestehender qualifizierter Runtime-Skip (1.83 s). Keine neue Skipregel/Testausnahme.

Paketversuch e142f7c6 bestand vollständiges read-only Pre-Build-Gate; danach fehlgeschlagener Dependencybezug wegen Sandbox-Netzwerksperre, Exit 1, keine App. Neues unbelegtes Profil 97d458b7 mit Netzwerkfreigabe: eigentliche PyInstaller-BUNDLE-Erstellung scheiterte beim Qt-Kopieren mit ENOSPC, Exit 1. Keine vollständige signierte App, keine App geöffnet, keine Keychain-/Startup-/Restoreabnahme. Quellstand Baseline plus PO-autorisierte Korrekturen, kein reiner HEAD-Binarynachweis. Relevante Quellhashes jeweils source-provenance.json. Logs/Exitbelege unter den privaten Systemtempcontainern jkm-internal-test-e142f7c673ab4948a73b9241678d4618 und jkm-internal-test-97d458b779784c38a2037eadd59d4be9.

Die parallel gestartete Produktsuite wurde durch ENOSPC ungültig und per SIGINT gestoppt: 2564 bestanden/56 fehlgeschlagen/278 Setupfehler/104 bestehende Skips/118 Unterprüfungen, Exit 2, 342.31 s. Kein positiver Abnahmenachweis. Ausschließlich eigene fehlgeschlagene Buildordner und eigene pytest-283/284/285-Zwischenbestände bereinigt; Profil-/Quell-/Fehlernachweise erhalten. Danach nur 1.1 GiB frei. Freigabe zur Entfernung des konkret benannten älteren 2.3-GiB-build-Zwischenordners der historischen isolierten Test-App 67680b19 angefragt; alte artifacts/data/Profile/Nachweise sollen erhalten bleiben. Noch keine alte Datei gelöscht.

Native Startupfälle 1–20, native Keychain-/Cipher-, Restore-/Worker-/Restart-/Crash- sowie UI-/Signatur-Pflichtgates bislang NICHT AUSGEFÜHRT. Keine Migration/Aktivierung/Veröffentlichung/Versionserhöhung. Abnahme offen, kein GO/Staging/Commit. Produktinstallation/-daten/-schlüssel durch keinen ausgeführten Appschritt angesprochen; Pflanzen-ZIP und Build-404-DMG-Hashes vorab bestätigt, Schlussvergleich folgt.


PO-Speicherbereinigung 14.10.2026: ausdrücklich autorisiert, nach Prozessinventar kein laufender Test/Build. 87 geprüfte regenerierbare Cache-/Zwischenordner entfernt; belegter Umfang 13418135552 Bytes, freier Speicher vor/nach 2913144832/16796962816 Bytes. Einschließlich alter internal-test-build-Ordner 67680b19/cd4b344f, pytest-Reste, entpackter iPad-Qt-Abhängigkeiten und Compilerzwischenprodukte, alter iPad-venv sowie pip-/PyInstaller-Caches. Alle neun fertigen iPad-App-Bundles, Quellen, Screenshots, Releaseartefakte, kanonische qualifizierte SQLCipherinputs, Daten, Profile und kleine Nachweise erhalten; 31 Schutzdatei-Hashes unverändert. Vollständige exakte Liste in cleanup-plan.json/cleanup-result.json unter dem bestehenden jkm-a2-prebuild-audit-27aibx24-Systemtempcontainer. Der beim Seitenwechsel unterbrochene Produktsuite-Wiederholungslauf hat keinen Abschluss-/Exitbeleg und zählt nicht als bestanden. Kein Produkt-/Keychainzugriff oder Release.


Native Erstpaketierung e3ff2cdd-c971-4857-a075-c9d1a75627b3: Pipeline Exit 0, exakte Testbundleidentität, Ad-hoc-Signatur, Bundleaudit status=ok, forbidden_artifacts=0, 373 arm64-Mach-O/296 RPATH, Binding 0.6.2+jkm.sqlcipher4170.1 / SQLCipher 4.17.0 community / SQLite 3.53.3 / commoncrypto, integrity=[]. Vollständige Hashinventur von 3386 Paketdateien vor Nativtests. Normales Öffnen zeigt tatsächlichen First-Run-Dialog; ohne Eingabe geschlossen und nur nicht eingerichteten synthetischen Bestand bei nachgewiesenem Prozessende zurückgesetzt. Automatisierte Werkzeugbeobachtung, keine menschliche Abnahme.

Tatsächlicher nativer Startupfall 2 am Erstpaket Exit 0: echter Test-Keychain-DMK create/read, echte SQLCipher-4.17-/CommonCrypto-Final-V4-Anlage, Schuljahr 2026/27, 331 Kompetenzen, null Schüler, reguläres Fensterende. Native Aufrufbeobachtung belegt Root/Inventarpreflight → RuntimeInstanceLock → erneutes Inventar/Guard → Restore-Recovery → erneuter Guard → First-Run-Kandidatur → Security/Authentifizierung → Cipher. Folgegate Existing-only blockierte mit SecurityStoreError vor weiteren Startupfällen: security.sqlite und data-keysets.sqlite hatten nach Prozessende WAL/SHM-Reste. Nachweise in native-matrix-result.json, native-matrix-progress.json und native-existing-keys.json des e3ff2cdd-Containers. Kein Gesamterfolg aus Fall 2.

Ursache auf sechs bestehenden SQLite-Verbindungslebenszyklen eingegrenzt: der Python-SQLite-Kontextmanager schließt Verbindungen nicht; Prüf-/Snapshot-/Initialisierungsverbindungen waren GC-abhängig. contextlib.closing ergänzt, vorhandene explizite Transaktionen bleiben unverändert. Kein neuer Checkpoint/Repair und keine Lockerung der Existing-only-Sidecarsperre. Unabhängiges enges Review P0=0/P1=0 im Korrekturumfang. 159 gezielte Security-/Keyset-/Startup-/Harnessprüfungen bestanden, ein bestehender expliziter Real-Keychain-Skip; echte SQLite-Regressionsprüfungen mit deaktivierter GC, Persistenz und Fehlerpfad. Snapshot-Readonly kann im eigenen neuen temporären Snapshot erwartbar leere WAL-Reader-Sidecars erzeugen; die Regression prüft die für A2 erforderlichen sidecarfreien Live-Metadaten und Snapshotinhalt getrennt.

Vor dieser letzten Lebenszykluskorrektur: vollständige Produktsuite 3063 bestanden, 104 bestehende Skips, 120 Unterprüfungen, 391.55 s, Exit 0. Am korrigierten Code erneuter finaler Gesamtlauf gestartet; alter grüner Lauf ersetzt ihn nicht. Nativer Cleanup des eigenen e3ff2cdd-Test-DMK über das unveränderte alte Paket erfolgreich, keychain_cleanup=ok/Exit 0. Alte App nicht gepatcht; nur deren regenerierbare build-Zwischenprodukte entfernt, App/Profil/Daten/Nachweise erhalten.

Frisches Folgeprofil 200fecf3-199f-4317-83f9-e249dd5446a2, Installation 375ca0d7-2b54-4a9d-b2c8-03898dc852af, Bundle/Worker/Restart de.jenaplan.kompetenzmanager.internaltest.t200fecf3199f431783f9e249dd5446a2, App/Executable JKM-Interner-Test-200fecf3199f431783f9e249dd5446a2. Eigener privater Systemtempcontainer jkm-internal-test-200fecf3199f431783f9e249dd5446a2, Root data, Build build, Ausgabe artifacts. Profil-SHA256 82a447c7a031c5cb0b099a4234935f76d380cd60223d178d48a990c4e01e0334. Drei eigene Testbundle-Services; Accountpräfix test-v1:200fecf3-199f-4317-83f9-e249dd5446a2; Ad-hoc-only, keine Entitlements/Updates. Quellprovenienz enthält zusätzlich exakte Hashes beider korrigierten Repositorydateien. Neubau über bestehende Pipeline; pip ohne persistenten Cache, PyInstaller-Cache im eigenen build. Keine Produktpfade oder Versionsänderung. Finale native Ergebnisse folgen; bislang keine A2-Freigabe.


Fortsetzung 15.10.2026: closing-Korrektur allein genügte im nativen 200fec-Paket nicht: leere Live-WAL/SHM blieben bestehen; Existing-only blockierte weiter. Eigener synthetischer Test-DMK anschließend nativ entfernt (native-cleanup.json: Exit 0/keychain_cleanup=ok). App/Nachweise erhalten, nur private Buildzwischenprodukte entfernt. Produktsuite dieses Standes: 3065 bestanden, 104 bestehende Skips, 120 Unterprüfungen, 403.44 s.

Regulären erfolgreichen Metadatenabschluss unter bestehendem Prozesslock ergänzt; niemals auf Guard-/Fehlerpfaden. Versionsprüfung vor Schreibport, kein Schema-Repair/Keyzugriff. Unabhängiges Review fand zunächst zwei P1 bei der Restore-Reihenfolge; vor erneutem Build korrigiert: Composition-Callback vor Evidenzbindung, bestätigter Workertransfer als ausdrücklicher Zustand; danach kein Parentflush. Nachreview P0=0/P1=0 im Diff; native Bestätigung offen. 280 gezielte Tests bestanden/ein bestehender Skip (16.95 s), zusätzliche Qt-Offscreen-Gruppe 78 bestanden (4.43 s). Unkonfigurierter direkter Qt-Lauf zuvor an Cocoa-Initialisierung abgebrochen; kein positives Gate daraus.

Frisches Profil cc8faa9c-c799-49db-88f1-796142ece456, Profil-SHA256 7ae0cdebccad357a8e3f26bbd21fb79109d8a86dadc8929a22dda2801e4cd912; Bundle/Worker/Restart de.jenaplan.kompetenzmanager.internaltest.tcc8faa9cc79949db88f1796142ece456, App/Executable JKM-Interner-Test-cc8faa9cc79949db88f1796142ece456. Private Roots und neue Installation/Keychainidentitäten stehen in profile.json des gleichnamigen Systemtempcontainers. Vor Buildwrite validiert; Hashprovenienz Baseline plus autorisierter Korrekturen gespeichert. Frischer Pipelinebuild und abschließende Produktsuite gestartet. Keine A2-Freigabe.


Paket cc8faa: Pipeline Exit 0, Paketprüfung status=ok/373 arm64/296 RPATH/forbidden=0; 4.17.0 community/CommonCrypto/Binding 0.6.2+jkm.sqlcipher4170.1/SQLite 3.53.3. Normale First-Run-Oberfläche automatisiert gesehen, ohne Eingabe geschlossen. Native Fälle 1–15 liefern alle erwarteten Codes; Existing-only, fehlender DMK und echte Keychain-ACL-Verweigerung bestanden. Matrix danach NO-GO wegen Infrastrukturcleanup: absichtlich restriktiver Testitem lässt sich nicht löschen, nativer Status -25244 errSecInvalidOwnerEdit. Fälle 16–20/Restorecrashes daher nicht ausgeführt. Exakter eigener Service/Account und Bereinigungsrest in attempt-summary.json; Benutzer um getrennte manuelle Entfernung gebeten. SecurityAgent-Werkzeugzugriff gesperrt, keine Umgehung. Kein Produktservice/-schlüssel beteiligt. Bundlehashinventur 5087 Einträge nach Tests unverändert; nur private build-Zwischenprodukte entfernt. Produktsuite dieses Quellstandes 3070 bestanden/104 bestehende Skips/120 Unterprüfungen/385.42 s/Exit 0.

Fixturekorrektur vor erneutem Build: zusätzlicher itemlokaler Delete/KeychainItemDelete-Zugriff nur für aktuelle Frozen-App, kein Read/Any. Eigener Zufallsschlüssel-Vorabtest muss real deny→delete→same-material restore→read→delete→NOT_FOUND beweisen; Interaktionszustand wird nur pro Testprozess geändert und Rückkehrstatus geprüft, getrennte schlüsselfreie Fixturebelege je ID. Unabhängiges Diffreview P0=0/P1=0, drei P2-Nachschärfungen übernommen. Native Bestätigung bleibt Pflicht; keine pauschale Ausnahme. Frisches Profil f9399ad0-fb2b-42da-beb6-84d31b267332, Digest 98c85ee660ae740f8cdc91af7d6212d9b825002574b645795bfaad0e93041af5, eigene Installation und Bundle .internaltest.tf9399ad0fb2b42dabeb684d31b267332. Neubau über unveränderte Buildpipeline gestartet.


ACL-Folgeversuch f9399: Paketbau/Audit Exit 0, aber der vorgeschaltete native ACL-Vorabtest blieb NO-GO (data_master_key_delete_failed). Die große Matrix wurde bewusst nicht gestartet; keine Produktbefunde daraus. Zusätzliche Delete-ACL war damit kein hinreichender nativer Fix und wurde wieder entfernt. Sicherer nativer Fixturecleanup anschließend ohne Secretbytes/Interaktion nachgewiesen: SecKeychainFindGenericPassword mit NULL-Länge/NULL-Daten liefert ausschließlich die exakte Itemreferenz; SecKeychainItemDelete liefert 0. Beide temporären restriktiven Items (cc8faa und f9399) entfernt, exakte Nachsuche jeweils -25300 NOT_FOUND. Belege restricted-item-cleanup-final.json beziehungsweise native-item-delete-probe.json und native-acl-fixture-<ID>.json. Keine ACL-/Owneränderung, keine globalen Einstellungen, kein Produktservice. Die zwischenzeitliche manuelle Bitte ist zurückgezogen; kein Rest dieses Fehlversuchs.

Finale Fixturekorrektur ausschließlich im versiegelten internen Runner: _delete_restricted_key bindet aktives Profil, validierte UUID und exakten Service/Account; bestehender Produkt-Keychainport unverändert. Preflight prüft weiterhin native Verweigerung, Delete, identische Wiederherstellung, Read und endgültige Abwesenheit. Nachreview P0=0/P1=0, keine weitere konkrete P2-Lücke. 66 gezielte Tests bestanden (2.24 s).

Neues Profil 0df2983b-0dfd-4393-8e1c-9f133e5f4b9d, Digest 7a003f1a3f5cd14b96461a3c78ccca5ecd22987c0e7404f472b92ec2558db399, Bundle/Worker/Restart .internaltest.t0df2983b0dfd43938e1c9f133e5f4b9d, eigener Systemtempcontainer. Vor Buildwrite validiert, exakte Quellhashes in source-provenance.json. Frischer Pipelinebuild und finale Produktsuite laufen. Vier ausschließlich eigene überholte Fehlversuchs-Appbundles nach Prozess-/Cleanupnachweis entfernt (2.10 GiB); vollständige kleine Evidenz/Profile/Daten erhalten, exakte Liste cleanup-superseded-apps.json. Veröffentlichtes Build-404-Artefakt unangetastet.


Paket 0df2983b: native ACL-Vorabprüfung vollständig Exit 0 (echte Verweigerung, exakte Itemlöschung, identische Materialwiederherstellung, endgültiges NOT_FOUND). Alle 20 Startupfälle erwartungsgemäß; Existing-only und beide echten keyed Reopens mit Cipher-/SQLite-/FK-Integrität bestanden. Worker worker_started→aborted_before_replacement; vollständiger Parent-/Worker-/Restart-Handoff completed/confirmed, alle Enden identifiziert. Sechs echte SIGKILL-Grenzen jeweils Restart 0, stabile DMK-/Database-Key-/Kontextidentitäten. Ergänzender unveränderter-Paketlauf speichert tatsächliche Journalphasen in native-crash-journals.json: before_swap maintenance→aborted_before_replacement; die fünf späteren Grenzen replacement_started→rolled_back. Beide DB-Integritäten nach jedem Fall erneut echt geprüft. Der temporäre Zusatzcontroller erzeugte zunächst selbst einen lebenden freigegebenen Lockdatensatz; dessen Start wurde korrekt verweigert. Controller korrigiert (nur beendete historische Fixtureidentitäten, kein Gate umgangen), danach alle sechs Belege erfolgreich. Keine Stromausfallgarantie.

Bestehende profilgebundene Keychain-, Restore-/Worker-/Restart- und vollständige App-First-Run-Smokerunner ebenfalls bestanden. Matrix-DMK und neuer App-Smoke-DMK jeweils nativ bereinigt; alle ACL-Testitems entfernt. Produktsuite 3071 bestanden/104 unveränderte Skips/120 Unterprüfungen/397.98 s/Exit 0. Nach diesen Läufen Bundleinventur aller 5087 Datei-/Symlinkeinträge unverändert; strikte tiefe Signatur und erneuter Bundleaudit bestanden (373 arm64/296 RPATH, unverändert exakte 4.17/CommonCrypto-Runtime). Versionsdatei, Feedkonfiguration/-zustand, 404-DMG, qualifizierter Wheelhash und Pflanzen-ZIP abschließend unverändert bestätigt, soweit als Schutzdatei erfasst; autorisierte Quellkorrekturen sind ausdrücklich separat.

UI-Grenze des 0df-Pakets: normaler First-Run-Dialog per CUA gesehen, keine Zugangsdaten eingegeben. Frühe Fehlerfenster bei Upgradeevidenz und partieller Installation wiederholt timeoutReached; root jeweils nach Prozessende nachweislich unverändert, verschlüsselte Companion-Fixture zurückgelegt. sample belegt regulären QMessageBox/NSAlert/AppKit-Modalereignisloop, keinen Produktdeadlock. Sichtgate daher offen, Gesamt-NO-GO dieses Pakets. Menschliche Sichtantwort angefragt, bislang kein entsprechender Nachweis. Unabhängiges Review verlangt keine zusätzliche menschliche Freigabe als erfundenes Pflichtgate; alle konkret verlangten UI-Zustände müssen tatsächlich beobachtet werden, Werkzeug-/Menschennachweise getrennt.

Minimaler Renderer-Kompatibilitätskandidat: bestehender früher Fehlerport als explizite Qt-QMessageBox mit DontUseNativeDialog, Critical, unverändertem Titel/Text, nur OK und exec. Sicherheitsveto und Prozess-/Schreibreihenfolge unverändert, keine Ereignispumpe und kein OS-Sicherheitsdialog betroffen. Canonical UI-Verträge präzisiert. Unabhängiger Diffreview P0=0/P1=0, 126 gezielte Prüfungen bestanden (35.68 s). Neuer geschlossener Matrixbericht bezeichnet separate UI-Sichtgates statt einer nicht beauftragten zwingenden menschlichen Freigabe; menschliche Abnahme weiterhin ausdrücklich nicht behauptet.

Frisches Kandidatenprofil 5d58c6e0-b2c3-4aed-a37e-d04d65b8c1e8, Digest b5b150aa1fda9da68575e233619cb57600e6d11e2fe16bd244dec4cb443539a1, Bundle/Worker/Restart .internaltest.t5d58c6e0b2c34aeda37ed04d65b8c1e8; eigener privater Systemtempcontainer, neue Installation und Services vor Buildwrite versiegelt. Bestehender Pipelinebuild und finale Regression laufen. Native UI-Zugänglichkeit dieses Kandidaten noch nicht bestanden.


### A2 FINAL – Commitbindung und native Abschlussabnahme – 15.10.2026

**Status A2: NATIV ABGENOMMEN, UNVERÖFFENTLICHT. GO ausschließlich für A2; keine Produkt-/Releasefreigabe.** Historische NO-GO-Berichte oben bleiben unverändert gültige Zwischenstände. Der jüngste Kandidat 5d58c6e0 hat deren offene Sichtgates inzwischen erfüllt.

Basis des getesteten Pakets: `6fd005ddac9c60f7b5580b4a242e12adf489c14a`, Branch `spike/python-gui`, plus exakt die unten hashgebundenen 14 damaligen uncommitteten Implementierungs-/Testdateien. Codecommit: `b6e3a0e81c8b8dbe5785ffe3146ea32c91aa8e24` (`fix: finalize packaged A2 startup acceptance corrections`). Keine Codebytes in diesem Abschlussauftrag verändert. Alle 14 Dateien einzeln gestagt; keine Dokumentation im Codecommit. Danach Git-Blobbytes erneut per SHA256 gegen vor Build erfasste source-provenance.json geprüft: 14/14 identisch. Nur docs/RELEASE_AUTOMATION.md und docs/TECHNICAL_NAMES.md unterschieden sich bereits zu Auftragsbeginn vom Dokumentationssnapshot; kein ausführbarer Unterschied.

Paketidentität: Profil `5d58c6e0-b2c3-4aed-a37e-d04d65b8c1e8`, Installation `c57700d7-794e-4865-b67a-31130cd5776d`, Bundle/Worker/Restart `de.jenaplan.kompetenzmanager.internaltest.t5d58c6e0b2c34aeda37ed04d65b8c1e8`. Digest `b5b150aa1fda9da68575e233619cb57600e6d11e2fe16bd244dec4cb443539a1`. Originalcontainer `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-5d58c6e0b2c34aeda37ed04d65b8c1e8`, Paket dort `artifacts/JKM-Interner-Test-5d58c6e0b2c34aeda37ed04d65b8c1e8.app`. Build-Exit 0, vorhandenes build-run.log und build/payload/pilot_build_info.json bestätigen internal-test/dirty/Basiscommit, nicht irreführend den späteren Commit als ursprünglichen Build-HEAD.

Unabhängiger Inhaltsvergleich am echten vorhandenen Executable (kein Appstart/Neubau): alle 5087 Datei-/Symlinkeinträge inklusive Modi/Targets/Hashes exakt gegen bundle-before.json; keine zusätzlichen oder fehlenden Einträge. Eingefrorenen PYZ direkt gelesen, 176 Projektmodule mit Kompilierung der heutigen Quelldateien unter demselben Build-Python und optimize=1 verglichen; rekursiv nur co_filename normalisiert, sonst vollständige Codeobjektgleichheit. Zusätzlich CArchive-Einstieg main und Frozen-Profilhook ebenso geprüft. Alle 178 Vergleiche erfolgreich. Quellbytegleichheit wird separat durch Prebuild-SHA256 belegt; Bytecodevergleich allein wäre kein Quellbytebeweis. Paketprofil-JSON, Buildsnapshot und Info.plist-Digest stimmen unabhängig überein. Executable-SHA256 `c38d65c5d0dd2579ea9ebf2ad1e452edfb86a8323f3d904ed70998ccc9e6607d`. Erneute strikte tiefe codesign-Verifikation Exit 0. Der abweichende neue Commit-SHA ändert weder Paketbytes noch Buildmetadaten; Bindung erfolgt über nachgewiesenen Inhalt.

Abschlussablage: `output/a2-acceptance/2026-10-15-closure/` (lokale, nicht versionierte Rohbelege); Originalbelege im genannten Profilcontainer. Alle 21 Einträge in evidence-sha256.json unabhängig neu gehasht, vollständig identisch. Zusätzlicher Abschlussvergleich closure-bundle-verification.json. Die nachfolgenden SHA256 sichern die Nachweisreferenzen im Register, auch wenn temporäre Dateien später entfernt werden; die Rohbelege bleiben für Nachprüfung zu erhalten.

| A2-Gate | Übernommener Nachweis desselben jüngsten Pakets |
| --- | --- |
| Startup 1–20 | native-matrix-result.json: returncode 0, automated_gates_passed; alle 20 Sollcodes, echte Frozen-Prozesse und beobachtete Reihenfolge/Mutationsvetos |
| Existing-only / Keychain | native-acl-preflight.json und Matrix: echte Verweigerung, exakte Löschung, identische Materialwiederherstellung; fehlender DMK gesperrt, beide keyed Reopens samt Cipher-/SQLite-/FK-Integrität bestanden |
| Worker / Restart | restore-runner-result.json und Matrix: completed/confirmed, Parent/Worker/Restart identifiziert und beendet |
| SIGKILL | Sechs Grenzen mit -9 und Restart 0; native-crash-journals.json: before_swap maintenance→aborted_before_replacement, fünf spätere replacement_started→rolled_back; stabile Schlüssel-/Kontextidentitäten und echte Integritätsprüfungen |
| Native Runtime / Bundle | bundle-audit-final.json: 373 arm64, 296 RPATH, forbidden=0, Binding 0.6.2+jkm.sqlcipher4170.1, SQLCipher 4.17.0 community, SQLite 3.53.3, CommonCrypto |
| UI | ui-first-run.json, ui-normal-open.json, ui-partial-result.json, ui-upgrade-result.json, ui-upgrade-existing-result.json: bestanden; reale synthetische Anmeldung, Hauptfenster regulär geschlossen, sicherer Halt nur OK ohne First Run/Reparatur; Werkzeugsichtprüfung, keine menschliche manuelle Abnahme behauptet |
| Produktsuite | product-suite.log + Exitdatei: 3071 bestanden, 104 bestehende Skips, 120 Unterprüfungen, **371.61 s**, Exit 0; nicht mit älterem 0df-Lauf (397.98 s) vermischen |
| Gezielter Abschlusslauf | targeted-final.log + Exitdatei: 350 bestanden, 2 bestehende Skips, Exit 0 |
| Commitbindung | 14/14 Quell-/Test-/Spec-SHA256 im Codecommit identisch; 176 PYZ-Module plus main/hook und vollständige Bundleinventur unabhängig geprüft |

Unabhängiges read-only Abschlussreview durch separaten Reviewer: P0=0, P1=0, keine neue offene P2-Implementierungslücke (P2=0 im Korrekturumfang). Hauptprüfung ergänzt Commit-/Paketbindung und Schutzdateien. Keine Tests aufgeweicht, kein Securityoverride. Bestehende Grenzen bleiben: keine Stromausfallgarantie, kein Schutz gegen vollständigen konsistenten lokalen Rollback einschließlich Anker, keine absolute ABA-/TOCTOU-Garantie und keine Downgradesicherheitszusage gegenüber Build 404.

Produktdaten/-schlüssel in diesem Abschlussauftrag weder geöffnet noch verändert; nur Quellen, synthetische Nachweise und Paketdateien gelesen. Keine neue produktive Upgradekante, Migration, Aktivierung, Schemaänderung oder Writerfreigabe. Versionsdatei, Pilotfeedkonfiguration und Feedbuilder identisch zur Basis. Historisches 404-DMG SHA256 d55c21c35509a034b3b249450478dc82514f7f296ab5e494799dae0fd93f311e bestätigt. Pflanzenbilder-ZIP unverändert 439602 Bytes, SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4. Keine Feedmutation, kein neuer Build, Push, Tag, Appcastupdate oder Release; macOS 0.4.4 / Build 404 bleibt veröffentlicht unverändert. Offene Releasegates: gesonderter PO-Releaseauftrag und reguläre Qualifikation eines künftigen Produktpakets (Produktbuild, Signierung/Notarisierung, Releaseartefakt-/Feedgates); die interne A2-Abnahme erteilt keine Verteilungsfreigabe.

#### Getesteter und committeter SHA256-Quellbestand

| Datei | SHA256 |
| --- | --- |
| `packaging/macos_pilot.spec` | `dbb97248c64ccd38b6edb4eabbce821cd04614d7a21307dbe51100788ef6da87` |
| `scripts/smoke_test_macos_keychain.py` | `e2766b7dda3bd71abe8acc6a23345efa2a333e32aebbd2a30e6fa9864f9780df` |
| `scripts/smoke_test_macos_security_integration.py` | `5a9afdf6fa3c06d367bfdea779c723d4ae798a0a47203683e59e27b33ae08782` |
| `scripts/smoke_test_packaged_restore_worker.py` | `dbda656bd438fbd026dab57692c9adf3847ba200c6289d0978972c15411e89fd` |
| `src/application/commands/final_v4_backup_restore.py` | `5e06383f150c2697a44a826fbc3290f5aa8ed812495869920d37cbb4e30d005c` |
| `src/core/macos_test_package_profile.py` | `4a13ac026ebfa57e2a9161952e0f6eab5ce0144a80b270c4361a946fd0e16c08` |
| `src/desktop_app/main.py` | `0e7363b012ed4a56a57763b49d33271744502bf560871075ee7740c3f5481e53` |
| `src/security/infrastructure/data_keyset_repository.py` | `057f710da6b8141e3b89730f6213a648811a1ff2a4073045ccac5fc16a38d79c` |
| `src/security/infrastructure/sqlite_repository.py` | `078271f6f88c060e4589b09ecbf3e23aa7d1e754f15db478ff177577ce437d14` |
| `src/security/startup.py` | `eadb0cae8dda02a47ae3ffd471dd5fb5326c1bed7ea9607502d285a18ffe1320` |
| `tests/test_final_v4_backup_restore_activation.py` | `6c58a491c25a88c2d47fe4e4c861cee7980de497de1147f4af01dfe0390104f5` |
| `tests/test_product_upgrade_startup.py` | `68175c9dee81a3f4d6448cc61fa82705e1f4db71729069c082488b8b1bcc6c4a` |
| `scripts/macos_native_acceptance.py` | `a00d0275803ca4186f81c31a7393b504cf745ee1b1c357a6a84ccb701189bc5a` |
| `tests/test_macos_native_acceptance.py` | `3579761d87ea95dec9acde5d8698f6a715a25d2cecb523e098346ec45946338c` |

#### Hashgebundene Test- und Paketbelege

| Beleg | SHA256 |
| --- | --- |
| `app-first-run-smoke-result.json` | `1d007c62d0ae3ceb0c6b4214704203cc9473ea0aba374f576f677edfa6ec0927` |
| `build-exit.txt` | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` |
| `bundle-audit-final.json` | `7ac2d322b8d7fb8c217e005e86baf20085574f783ebed1a98c4780e0b009951c` |
| `bundle-before.json` | `ba8b0bc8a6cbcd38d98fcf6ef45d2d1981a89407bdd8017d8e0c2edaa0d24972` |
| `keychain-runner-result.json` | `211be5599cba3649f2e8701253507c5d5568ffa347e807e0b06316d7d3cea09e` |
| `matrix-key-cleanup.json` | `1f12af08f880a1d0bc24bc50c11277b74d66f2323c9c3de89f7e02d6d9523db8` |
| `native-acl-preflight.json` | `42625e3fcacff477c9899ac2f59d420269930a2182119ea70dc6ae8d5701bbad` |
| `native-crash-journals.json` | `dc17f50be4ce182932c761a7a41aa9dc0576169116e7a640cd2d6b2b1f97bb32` |
| `native-matrix-result.json` | `f64b232356c36eded7b8741db909f6c65f282288aec5a24a8d9d5284c3ed8d04` |
| `product-suite-exit.txt` | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` |
| `product-suite.log` | `8303d0e7842084dfe57d7e3545a2741fa4178e3141fd81a842cc415041000264` |
| `profile.json` | `586b83def8339cc5d8ca406fe0f2e4000cc08725f501d9a1df8acc98919e7778` |
| `restore-runner-result.json` | `b546d78fa6e19f185edf7f11ea35a219bcc493039a5c5c082c631855714181e0` |
| `source-provenance.json` | `3a44e6ff8224b082912f068ff5a94cc23cd08ec72e959db9346423bb9547cec2` |
| `targeted-final-exit.txt` | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` |
| `targeted-final.log` | `f2c96a322ea60848baef893f7b711b444076a525b3ce1088f55441bf75c721a0` |
| `ui-first-run.json` | `7c04048d71f13b038e31a1da4f428e1c999849b1cbe6d051b741ac70a2fe084b` |
| `ui-normal-open.json` | `0a8e56e5d127a5b5ce557f588135c4b443f945636f9e55accde98f9cdd4350da` |
| `ui-partial-result.json` | `2d2080a1713799d8b7539921d449c71d534b1266f4ec8563ae57820d7c9dd8bc` |
| `ui-upgrade-existing-result.json` | `11103bf91aebf7a7c7828f4d3364cb8523769aa1624d269806b6c1657eb2c391` |
| `ui-upgrade-result.json` | `ef2926bb7e97461429b68bf2ddfc3ed29b8821040c3d647aa015e02446422733` |
| `closure-bundle-verification.json` | `deb72755a88cc82db10e9598381c2bf1efecf2b62656667db7894fe2aaa17e1b` |


### V6-Gesamtabnahme – Vorprüfung 16.10.2026 – NO-GO / Auftrag nicht abgeschlossen

Auftrag: frische isolierte native V6-Abnahme und Vorbereitung eines späteren regulären Feature-Releases. Keine Veröffentlichung. Ausgangs-HEAD `e56a5287768aa5aeb7c0aeb455390dac46914ce1`, Branch `spike/python-gui`, erwartete Baseline exakt bestätigt. Fünf vorbestehende Dokumentänderungen in CHANGELOG, DECISIONS, PROJECT, DATA_LIFECYCLE und PROJECT_CONSTITUTION vollständig erhalten; insbesondere fremde Speicherbereinigungsnotiz nicht gestagt. Kein ausführbarer Code geändert.

**Abbruchgrund:** Eine bloße Paketierung dieses HEAD liefert keine normale V6-Testanwendung. Die synthetischen V6-Services und die gesondert komponierte AppShell sind implementiert, aber die eingefrorene Desktop-/Workerkomposition fehlt. Das ist eine grundlegende Integrationslücke für den Abnahmeauftrag; kein Anlass, die produktiven Guards oder Registry zu lockern. Zusätzlich zunächst nur 832 MiB verfügbar; spätere Messung 2.29 GiB. Historisches fertiges Testbundle allein 538 MiB, zusätzlich braucht die bestehende Pipeline neue venv, PyInstaller-Zwischenprodukte und Bundlekopien. Kein aussichtsloser Build und keine eigenmächtige Speicherbereinigung gestartet. Speicherfreigabe angefragt; keine Löschfreigabe angenommen.

#### Unabhängiges Architektur-/Security-Review

Separater read-only Reviewer, anschließend Quellprüfung durch Hauptagent; keine Reviewer-Testläufe. P0 im geprüften Quellumfang nicht gefunden. Keine neue P1-Sicherheitslücke im synthetischen Servicepfad bestätigt. **P1-Releaseblocker: V6-Desktopkomposition und V6-Workerintegration fehlen. Deshalb ist die geforderte gesamte P1=0-Abnahme nicht erreicht.** Kein neuer konkret bestätigter P2-Defekt; bestehende lokale Koordinations-/Stromausfall-/Rollbackgrenzen bleiben.

- `src/security/cipher_product_runtime.py:312` baut weiterhin ausschließlich FinalV4SQLCipherRuntimeCoordinator. Die exakte V4-Prüfung bleibt richtig und darf nicht global V6 zulassen.
- `src/desktop_app/main.py:760` komponiert V4-Backup/Restore. `src/desktop_app/restore_worker.py:374` akzeptiert nur ZIP/V4. `src/core/macos_test_package_profile.py:252` erlaubt Worker ebenfalls nur mit final_v4_encrypted. Vorhandene V6-Handoffservices ersetzen diese fehlende Prozessverdrahtung nicht.
- Normaler Appstart liefert keinen lesson_time_templates_adapter. `src/desktop_app/shell.py:280,500` lässt diesen optional und blendet Unterrichtszeiten ohne ihn aus. Die funktionalen AppShelltests injizieren ihn ausdrücklich.
- `src/core/schema_registry.py:165` bleibt Final-V4-only ohne Produktkante. UpgradeStartupGuard hält vorhandene Upgradeevidenz nach Prüfung weiterhin an. Eine neue Produktregistry allein würde weder Startup noch Recovery/Writeradmission freigeben.

#### Profilvorbereitung und tatsächlich ausgeführte Prüfungen

Neues Profil: `229d6f32-3846-4c33-bcfa-753f81f0f033`; Installation `82549014-cc02-4254-9feb-1dfc24652266`; Bundle/Worker/Restart `de.jenaplan.kompetenzmanager.internaltest.t229d6f3238464c33bcfa753f81f0f033`; Appname `JKM-Interner-Test-229d6f3238464c33bcfa753f81f0f033`. Snapshotdigest `b6655a7078732f56523853f8fd28e577a2a034d440b92c344e6d919439ea9173`. Drei getrennte Test-Keychainservices, eigener Accountpräfix, updates=false, ad-hoc, entitlements=null. Keine produktidentische Zwischenapp.

Privater Container im kanonischen Systemtemp: `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-229d6f3238464c33bcfa753f81f0f033/`. `data` ausschließlich mit synthetic_test-Marker; `build` und `artifacts` nicht erzeugt. Dort liegen profile.json, source-provenance.json (474 aktuelle Quell-/Test-/Builddateihashes), preflight-result.json und protection-check.json. Flüchtige Rohbelege sind keine Paketfreigabe.

Ausgeführt:

- Alle sechs geforderten Git-Baselineprüfungen; erwarteter HEAD/Branch, fünf Fremddokumente, Staging leer.
- Bestehende Pipeline `rtk proxy bash scripts/build_macos_pilot.sh --package-profile internal-test --test-profile <obiges profile.json> --validate-profile-only`: Exit 0, keine Buildwrites.
- `rtk proxy python3 -m pytest tests/test_macos_test_package_profile.py tests/test_schema_registry.py -q --tb=short`: **132 bestanden, 0 Skips, 1.96 s**.
- Schutz-/Quellhashprüfung: 474/474 unverändert; Versionsdatei, Builder, Spec und Pilotfeeddatei bytegleich HEAD. Fünf fremde Dokumentstände vor eigener Dokumentation hashgleich zum Eingang.

Die vorhandene finale Quellsuite ist laut PROJECT und vorhandenem `/private/tmp/jkm-d-full-suite-serial-final.log` 3395 bestanden / 104 bestehende Skips / 120 Untertests / 754.75 s. Der PO ordnet sie dem identischen erwarteten V6-HEAD zu; keine neue Codeänderung hier. Dies ist übernommene Quellprovenienz, keine neu unabhängig rekonstruierte damalige Hashattestation und keine native Paketprovenienz. Keine unnötige Wiederholung der bisherigen Migration-/SIGKILL-/AppShellkampagnen. Vor späterer Codeintegration betroffene Regressionen und vollständige Suite erneut bzw. mit eindeutiger identischer Provenienz. Alte A2-Paketabnahme gilt nicht für einen frischen V6-Build.

#### Abnahmestatus zu den 23 Berichtspunkten

| Punkt | Ergebnis dieses Auftrags |
| --- | --- |
| 1. HEAD vorher/nachher | Vorher e56a5287768aa5aeb7c0aeb455390dac46914ce1; nachher separater reiner Dokumentationscommit, siehe git log. Keine Codeänderung. |
| 2. Commits/Git | Nur eigener Abnahmebericht und eigene Changelogergänzung im Dokumentationscommit; fünf Fremdänderungen bleiben ungestagt. Kein Push/Tag. |
| 3. Testpaket/Profil | Neues Profil wie oben validiert; **keine neue App gebaut**. |
| 4. Bundle/Signatur/Provider | Am neuen Paket nicht ausgeführt; SQLCipher 4.17/CommonCrypto aus Quellnachweisen sind kein neuer Bundlebeleg. |
| 5. Startupmatrix A–O | Sämtliche Fälle am neuen V6-Paket offen; keine alte A2-Matrix als neues Ergebnis ausgegeben. |
| 6. V4→V6 End-to-End | Vorhandener synthetischer Servicenachweis; paketierter Wartungs-/Login-/Restartverlauf nicht ausgeführt. |
| 7. Datenvollständigkeit | Historische Quelltests prüfen vollständige Fachdaten/Dokumente; neuer Paketbestand und dessen vollständiger Vorher-/Nachhervergleich offen. |
| 8. V6 Backup/Restore | Synthetische Services geprüft im Vorauftrag; paketierter Worker/Restart fehlt, Abnahme offen. |
| 9. Unterrichtszeiten | In gesonderter AppShell geprüft; normaler Paketstart ohne Adapter, daher hier nicht vollständig bedienbar qualifiziert. |
| 10. Stammgruppenstunden | Quell-/AppShellnachweis vorhanden; native Paketbedienung offen. |
| 11. Kombinierte Fachstunden | Quell-/AppShellnachweis vorhanden; native Paketbedienung offen. |
| 12. Beobachtungszuordnung | Quellnachweise: bewusste Fachwahl, genau eine Beobachtung; paketierter Persistenznachweis offen. |
| 13. UI/Bediennachweise | Historischer automatisierter Cocoa-Quell-Smoke vorhanden; keine neue Frozen-UI und keine menschliche Abnahme. |
| 14. Neue Tests | 132 Tests und reines Pipeline-Profilgate bestanden, siehe oben. |
| 15. Befunde | P0 nicht gefunden; P1-Releaseblocker Desktop/Worker; kein neuer bestätigter P2. Keine Gesamtfreigabe P1=0. |
| 16. Menschliche Prüfung | Vollständig offen; reproduzierbare Liste unten. |
| 17. Native Paketgates | Build, Inhalts-/Signatur-/Entitlement-/Provider-/Modulinventur, Startup A–O, ACL/Keychain, Migration, Persistenz, Worker/Restart und Crashmatrix offen. |
| 18. Produktintegration vorbereitet | Readinessanalyse erstellt; vollständige technische Produktintegration **nein**, keine Aktivierungsimplementierung. |
| 19. Produktmigration gesperrt | Ja: Registry, Runtime und Startupguard unverändert. |
| 20. Feature-Releaseempfehlung | **NO-GO** bis Integrations-/Paket-/Migrations-/PO-Gates erfüllt sind. |
| 21. Produktdaten/Schlüssel | Nicht geöffnet oder verwendet; keine Keychainoperation in diesem Auftrag. |
| 22. Build 404/Pilotfeed | Keine Installations-/Artefakt-/Feedmutation, keine Versionsänderung. Historisches DMG in dieser Vorprüfung nicht erneut lokalisiert/gehasht; keine pauschale neue Artefaktattestation. |
| 23. Pflanzenbilder-ZIP | Unverändert: 439602 Bytes, SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4. |

#### Konkrete weitere Integrations- und Releasegates

1. Platz für den bestehenden Builder freigeben; Quellen, Produkt-/Pilotdaten, Schlüssel, Releaseartefakte und alte Evidenz erhalten.
2. Profilgebundene Frozen-V6-Testkomposition implementieren: bestehende synthetische Autorität, Existing-only-Keys, exakte Zielruntime, Templateadapter, V6-Backup/Restore, eigener authentisierter Worker/Restartkontext. Normaler Produktstart bleibt V4. Keine globale Umgebungsvariable oder Registryfreigabe als Ersatz.
3. Frischen Source-/Package-gebundenen Build mit vorhandener Pipeline durchführen; ausgehend davon alle im Auftrag geforderten nativen Gates abnehmen. SQL-/Commit-/SIGKILL-/ENOSPC-/Parallel-/Korruptionsfehler nur als echte geprüfte Fälle zählen; V4-READY darf V6 nie direkt ersetzen, DMK bleibt unverändert.
4. Produktiver Wartungsstart benötigt vor Freigabe einen expliziten, noch geschlossenen Vertrag: exakte bestehende V4-Quelle und vorhandene Schlüssel, geprüftes unabhängiges Vollbackup, Connection-Drain, registrierte V4→V6-Kante, transaktionaler Commit/Rollback, exakte Zielprüfung, terminaler Wartungsabschluss, neue V6-Runtime und authentisierte Recovery-/Writeradmission. Kein normaler Start darf still migrieren oder bei unbekanntem Zustand First Run erreichen.
5. Build 404 weist V6 zurück; daraus folgt kein automatischer Downgrade. Vor erster V6-Nutzung muss Wiederherstellung des vollständigen geprüften V4-Bestands dokumentiert sein; nach V6-Nutzung bedeutet Rückkehr zum V4-Backup Verlust späterer Änderungen. Keine Main-Einzeldateirückkopie oder Schlüsselrotation als Recovery. Fehlgeschlagener Upgradezustand bleibt sicher gesperrt bis eindeutiger geprüfter Wiederherstellung.
6. Regulärer Produktbuild separat gegen bestehende Build-404-Gates qualifizieren: Produkt-Keychain/Provider, vollständiger V6-Restore, Developer-ID/Hardened-Runtime/Entitlements, Notarisierung/Stapling/Gatekeeper, Sparkle-Framework/Bridge/Feed/Signatur und Update vom tatsächlich eingesetzten Pilotstand. Verteilung erst nach gesonderter PO-Freigabe. Profiltest mit ad-hoc/Updates aus qualifiziert diese Produktgates nicht.
7. Tatsächlich eingesetzte Pilotversionen und ihr Daten-/Backup-/Updatezustand im späteren autorisierten Releaseprozess erfassen; hier keine realen Installationen inventarisieren. Neue monoton höhere Buildnummer und Version erst im separaten Releaseauftrag festlegen. Keine neue Releaseinfrastruktur nötig.

#### Kompakte menschliche Prüfliste für Laura – erst nach bestandener Frozen-Testkomposition

Nur neue isolierte synthetische Test-App/angegebene Testdaten verwenden. Pro Schritt Soll-/Ist, Screenshot und Neustartresultat festhalten; alles derzeit **offen**.

- Mit bereitgestelltem synthetischem Konto anmelden; Dashboard, Stundenplanübersicht, vorhandene Bewertungen/Beobachtungen, Fachauswertung und Bericht öffnen. Fenster-/Dialogaktionen und Fehlermeldungen auf Lesbarkeit prüfen.
- Unterrichtszeit 08:00–08:45 anlegen, bearbeiten/speichern; ungültige bzw. umgekehrte Zeiten abweisen lassen; neu starten und laden. Zeitvorschlag ausdrücklich in Stunde übernehmen, individuell ändern, Vorlage erneut ändern; Bestandsstunde bleibt unverändert.
- Stammgruppenstunde ohne Fach anlegen; Anzeige, Bearbeiten, Deaktivieren/Reaktivieren, Neustart und Löschen prüfen. Keine künstliche Bewertung/Fachzuordnung.
- Deutsch+Mathematik als einen Eintrag speichern; beide Namen prüfen, bearbeiten und nach Neustart laden. Ein Parent, keine Verdoppelung. Dazu technische Persistenzkontrolle durch Runner.
- Aus kombinierter Stunde Beobachtung starten, Fachwahl zunächst abbrechen (keine Speicherung), erneut Mathematik bewusst wählen, passende Kompetenzliste prüfen und genau eine Beobachtung speichern. Organisatorische Stunde darf kein Fach erfinden.
- V6-Vollbackup/Restore mit kontrolliertem Worker-/Restart durchlaufen; nach Anmeldung alle vorgenannten Bestände und synthetisches Dokument wiederfinden. Technische Manifest-/READY-/Key-/Integritäts-/Vollständigkeitsbelege zusätzlich erforderlich.

Keine menschliche Bedienprüfung oder Gesamtfreigabe behauptet. Keine Produktmigration, kein Push/Tag/Release/Appcastupdate. A/B-Wochen bleiben zurückgestellt.


### V6-Codeabschluss und frische native Paketabnahme – 16.10.2026 – NO-GO

**Ergebnis: getesteter Code gesichert, zwei frische isolierte Testpakete gebaut, nativer P1-Startblocker an regulären erhaltenen Operationsbelegen bestätigt. Keine native V6-Gesamtfreigabe und keine Produktfreigabe. Keine Folgeimplementierung begonnen.** Die historischen NO-GO-Nachweise bleiben erhalten.

#### Baseline, Commit und Testprovenienz

Ausgangs-HEAD `18a00fcb8cae1eb1786d0396786c334ff028d119`, Branch spike/python-gui. Seit e56a528 bestand zunächst ausschließlich dieser Dokumentationscommit. Sämtliche uncommitteten Änderungen überprüft, fünf fremde Dokumentänderungen abgegrenzt und vollständig erhalten. Fremde CHANGELOG-Speicherbereinigungsnotiz nicht gestagt. Eigene Ergänzungen in gemischten Dokumenten als gezielte Indexpatches gesichert, alle anderen Dateien einzeln gestagt.

- `002123eb6e916535f35cbf3b0cc6c42576090a0b`: V6-Desktop-/Templateadapter-/Restore-Worker-/Restartintegration, zugehörige Tests, interne native Prüfeinstiege und eigene kanonische Vertragsänderungen.
- `767afb1a2ce92487f5c3f37a0a96f5a081d771f6`: eng begrenzte native Harnesskorrektur: Pflichtargument environ an bestehenden V4-Backupbuilder übergeben. Kein Produktcode geändert.
- Nachfolgender reiner Nachweiscommit dokumentiert diesen tatsächlich ausgeführten Paketlauf; genaue Identität in git log. Er ersetzt keinen Implementierungscommit.

Vor erstem Commit alle 478 Einträge aus suite-source-provenance.json mit aktuellen Quell-/Test-/Skript-/Paketbytes verglichen: 478/478 identisch; gestagte Bytes ebenfalls gegen diese Hashes geprüft. Übernommener vollständiger Lauf: **3424 bestanden, 104 unveränderte bestehende Skips, 120 bestandene Untertests, 756.18 s, Exit 0**. Log und Exitbeleg unter `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-v6-integration-evidence-20261016/`.

Nach Harnesskorrektur unterscheidet sich ausschließlich scripts/macos_native_v6_acceptance.py von dieser Suiteprovenienz; sämtliche src-, Test- und Packagingbytes sind unverändert. Tatsächlich neu ausgeführt: `rtk proxy python3 -m pytest tests/test_macos_native_acceptance.py tests/test_macos_test_package_profile.py -q --tb=short` → **179 bestanden, keine Skips, 3.51 s**. Die Vollsuite wird für unveränderten Produktcode übernommen; sie wird nicht als neuer Gesamtlauf des korrigierten Harness ausgegeben. Dessen tatsächlicher Paketlauf erreicht danach erfolgreich das vollständige Datenseeding. Keine neue Skipregel/Sicherheitsausnahme.

Unabhängige Reviews vor den Codecommits: keine neuen P0/P1 im geprüften Integrationsumfang; bekannte Restorehistoriengrenze bleibt. Nach dem nativen Befund erneutes unabhängiges read-only Review: **P1 bestätigt**, siehe unten. Die frühere Sourcebewertung ist keine Behauptung einer bestandenen nativen Gesamtprüfung.

#### Frische Pakete und Identitätsbindung

Erster Kandidat: Profil 8ae439ee-fcb1-4e22-a686-9f96198be9b7, Installation ef9ff306-7139-432d-bccd-3a119f719f55; Snapshotdigest `71f47a428aed95edf447b575a36b91e3d0eeb76c777eb9b6708812a8c3f49d08`; Commit 002123e. Pipelinebuild Exit 0, Paketaudit ok, First Run erfolgreich. Native Matrix stoppt danach bei v6-seed mit TypeError; fehlendes environ im Harness gefunden. Kandidat samt Fehlerbelegen unverändert erhalten.

Zweiter Kandidat: Profil `4777464c-5871-4ae4-abb2-e57da1aa2f13`, Installation `357ce340-5671-4ad1-ba54-56eb0c5defbb`; App/Executable `JKM-Interner-Test-4777464c58714ae4abb2e57da1aa2f13`; Bundle/Worker/Restart `de.jenaplan.kompetenzmanager.internaltest.t4777464c58714ae4abb2e57da1aa2f13`. Snapshotdigest `8161b13ef1c8dfd2cf6642c1ed2406d874be68888554d17c74f1209859b40ba5`. Codecommit 767afb1, Buildmetadaten korrekt dirty wegen ausschließlich fünf geschützter Fremddokumentänderungen. Vollständige Quellhashes separat gebunden.

Privater Container: `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-4777464c58714ae4abb2e57da1aa2f13/`. App darunter `artifacts/JKM-Interner-Test-4777464c58714ae4abb2e57da1aa2f13.app`. Runtime ausschließlich data mit bestehendem synthetic_test-Marker; eigene neue build/artifacts-Ziele. Drei Keychainservices exakt Testbundle + .data-master-key/.device-credential/.monotonic-security-anchor, Accountpräfix test-v1:4777464c-5871-4ae4-abb2-e57da1aa2f13. Updates false, Ad-hoc-only, keine Entitlements/Team-ID. Keine produktidentische Zwischenapp oder Produktfallbacks.

Beide Kandidaten über bestehende internal-test-Pipeline gebaut. Profilsnapshot/Digest/Pfade vor Build validiert; nach Build profilgebundener Smoke-Preflight Exit 0. Signatur strict/deep gültig. Paketaudit ok, forbidden_artifacts=0; echtes Binding 0.6.2+jkm.sqlcipher4170.1, SQLCipher 4.17.0 community, SQLite 3.53.3, CommonCrypto. Keine Developer-ID-/Notarisierungs-/Verteilungsfreigabe.

Unabhängig am echten Frozen-Executable jeweils 196 Vergleiche gegen die vorhandenen Quellcodeobjekte: PYZ-Projekt-/Nativeprüfmodule plus CArchive-main und Profilhook; nur co_filename rekursiv normalisiert, sonst vollständige Codeobjektgleichheit bei optimize=1. Kein Unterschied. Benötigte V6-Runtime-/Backup-/Restore-/Command-/Adaptermodule enthalten; historisches unsicheres Testarchiv und VFS-Probe ausgeschlossen. Zusätzlich Quellbytehashes an Commit gebunden. Abschließender vollständiger Bundlevergleich: **6030/6030 Datei-/Link-/Verzeichniseinträge inklusive Modi/Hashes/Linkziele unverändert**, beide Kandidaten. Zweiter Kandidat nach Tests erneut strict/deep codesign Exit 0.

Speicher vor Build rund 17 GiB; historischer vergleichbarer Build 2.7 GiB plus fertige App 538 MiB. Zwei vollständige neue Kandidaten konnten ohne ENOSPC gebaut werden. Keine Bereinigung vorgenommen, keine alten Nachweise/Backups/Keychainobjekte gelöscht.

#### Tatsächlich ausgeführte native Matrix und bestätigter P1

Beim zweiten Kandidaten:

1. Echte leere synthetische Installation, kontrollierter First Run, neue getrennte Testschlüssel, erfolgreich authentisierte synthetische Erstsitzung, Hauptfenster und reguläres Schließen: Exit 0. Schuljahr 2026/27, 331 Katalogkompetenzen, Main keyed Final V4. Dies ist ein automatisierter funktionaler UI-Smoke, keine menschliche Sicht-/Bedienabnahme.
2. Eigener Frozen-Prozess v6-seed: Exit 0, tatsächliche V4-Runtime und bestehender normaler Schreibpfad. Bestand vollständig gezählt: 24 Schüler, drei Stammgruppen, drei Kurse, ein Kursverbund, 331 Kompetenzen, 71 Beobachtungen, 71 Kompetenzratings, zehn Stundenplaneinträge, fünf Dokumente, ein Schuljahr; zusätzlich Berichts-/LEG-Entwürfe, Revisionen und PDF-Artefakte. Companion-/Dokumentprüfung bestanden. Vorhandene Installations-/DMK-/Datenbankschlüsselidentitäten im synthetischen Ausgangsnachweis festgehalten.
3. Neuer Frozen-Prozess v6-migrate: **gesperrt vor Migration**, native_existing_keys_installation_unknown. Native Matrix Exit 1. Kein V6-Commit, kein Migrationsbackup oder Teilupgrade aus diesem Lauf behauptet.
4. Danach tatsächlicher normaler Restart am selben Paket/root mit vorhandenen synthetischen Zugangsdaten: **Exit 3**, bereits bei before_lock/inspect sicher angehalten; keine Runtime-/Anmeldefreigabe. Befund unabhängig von der Migration reproduziert.

Konkreter P1: `src/security/infrastructure/installation_inventory.py:147` erkennt nur .observation-staging und .writer.lock, jedoch nicht die normalen aufbewahrten Operationsunterverzeichnisse/Journale. Außerdem ist .managed-document-staging unbekannt. Der echte Bestand enthält 154 unbekannt klassifizierte Artefaktpfade: 71 Beobachtungsoperationen samt Journalen plus zwölf Dokument-/PDF-Stagingpfade. Alle **71 Beobachtungsjournale und vier Dokument-/PDF-Journale stehen auf COMPLETE**. `src/core/observation_uow.py:433` überspringt COMPLETE absichtlich bei Recovery; die ID-Reservierung liest aufbewahrte Journale weiterhin. Auch die vorhandene ManagedDocument-Recovery behält COMPLETE-Belege bei. Der vollständige gültige Schreibbestand wird damit vom nachgelagerten Startup-/Existing-key-Inventar als UNKNOWN gesperrt.

Dies ist ein Verfügbarkeits-/Integrationsblocker an der bestehenden A2-Inventargrenze, kein nachgewiesenes V6-Schema-/Cipher-Transaktionsversagen. Der Konflikt bestand bereits in der Baseline und wurde durch die realistische native Fixture sichtbar. Ein fehlender regulärer Keymetadatenabschluss des Seed-Harness ist eine zusätzliche getrennte Nachweisgrenze: vorhandene Keyset-WAL/SHM bleiben in diesem Erzeugungsprozess zurück. Ein unterstützter Metadatenabschluss kann diese behandeln, beseitigt aber den reproduzierten Konflikt mit bewusst erhaltenen COMPLETE-Journalen nicht.

Keine Belege gelöscht, keine Statusfelder als Autorität akzeptiert, kein Glob-/Whitelist-Bypass eingeführt, kein Guard abgeschwächt. Weitere Implementierung hier gestoppt. Nötiger nächster eng begrenzter Auftrag: reguläre erhaltene Beobachtungs-/Dokumentbelege im bestehenden Startup-/Inventar-/Existing-key-Vertrag sicher und mit tatsächlicher Persistenzbindung behandeln; davor native Regression mit echter vollständiger Schreibinstallation. Keine neue Recoveryplattform erforderlich oder hier begonnen.

#### Abschluss zu den 24 Berichtspunkten

| Punkt | Tatsächliches Ergebnis |
| --- | --- |
| 1. HEAD vorher/nachher | Vorher 18a00fcb8cae1eb1786d0396786c334ff028d119; Implementierungs-/Paketstand 767afb1a2ce92487f5c3f37a0a96f5a081d771f6; anschließend dieser Nachweiscommit, siehe git log. |
| 2. Neue Commits | 002123e Implementierung; 767afb1 Harnesskorrektur; abschließender Nachweiscommit. |
| 3. Arbeitsbaum/Staging | Nach eigenen Commits ausschließlich die ursprünglichen fünf Fremddokumentänderungen ungestagt; Staging leer. |
| 4. Implementierungen | V6-Startupkomposition, LessonTimeTemplatesDesktopAdapter bis JenaplanDesktopApp/AppShell, exakter V6-Worker/Restart und authentisierter bestehender Recoverybootstrap committed. |
| 5. Paket/Commitbindung | Beide frischen Profile/Bundles wie oben, source hashes und jeweils 196 Codeobjektvergleiche; Paketstand ist 767afb1, kein späterer Dokumentationsstand als Build-HEAD behauptet. |
| 6. Native Paketgates | Profil, Build, Bundle, Signatur, Provider und nachträgliche Paketintegrität bestanden; keine Gesamtfreigabe. |
| 7. V6-Startup/Anmeldung | Nicht erreicht; reichhaltiger V4-Testbestand blockiert bereits vor Migration und beim normalen Restart. |
| 8. Unterrichtszeiten | Source-/AppShellnachweise übernommen; frische paketierte V6-Bedienung/Persistenz nicht erreicht. |
| 9. Stammgruppenstunden | Source-/AppShellnachweise vorhanden; native Bedienabnahme offen. |
| 10. Kombinierte Fachstunden | Source-/AppShellnachweise vorhanden; native Bedien-/Neustartprüfung offen. |
| 11. Beobachtungszuordnung | Sourceprüfung bewusste konkrete Fachwahl/eine Beobachtung vorhanden; native V6-Prüfung offen. Native V4-Schreibfixture legt reguläre Einzelbeobachtungen an und deckt Startblocker auf. |
| 12. V4→V6 | Nativer neuer Versuch vor Migration blockiert; keine erfolgreiche native E2E-Migration behauptet. Synthetische Transaktions-/Crashquelltests bleiben historische Nachweise. |
| 13. V6-Backup/Restore | Service-/Integrationstests übernommen; neuer Paketpfad nicht erreicht. |
| 14. Worker/Restart | Code und reale Quellenprozesse getestet; paketierter V6-Handoff/Crash-/Konkurrenznachweis nicht erreicht. Normaler vorhandener-V4-Restart bestätigt Exit 3. |
| 15. Neue Tests | 179 native/profile Quellregressionen; zwei vollständige native Builds/Audits, zwei leere Erstsitzungen, eine vollständige Native-V4-Schreibfixture, blockierte Migrations-/Restartprozesse, Frozen-Code-/Bundlevergleiche. |
| 16. Wiederverwendet | Exakt hashgebundene Suite 3424/104/120 für Produktstand 002123e; Vorauftrags-SQLCipher-/SIGKILL-/AppShellnachweise ausdrücklich Source-/Servicebelege, keine alten Paketergebnisse als neue V6-Abnahme. |
| 17. P0/P1/P2 | P0 nicht gefunden; P1=1 bestätigt (Inventar gegen reguläre aufbewahrte Operationsbelege). P2: bestehende enge historische/mehrfache Restorehistoriengrenze und separater Seed-Metadatenabschluss. Gesamtes P1=0-Gate verfehlt. |
| 18. Menschlich offen | Sämtliche praktische V6-Layout-/Bedienabnahme durch Laura offen. Bestehende kompakte Prüfliste oben bleibt gültig. Keine menschliche Prüfung behauptet. |
| 19. Produktgates offen | P1 beheben, Fixture sauber abschließen, gesamte native V6-Startup-/Fach-/Migration-/Restore-/Crash-/Konkurrenzmatrix und menschliche Prüfung; danach separate Produktmigrations-, Signing-/Notarisierungs-/Update-/PO-Freigabe. |
| 20. Produktmigration gesperrt | Ja: Produktregistry weiterhin ausschließlich Final V4 ohne Upgradekante; kein stilles Upgrade/First-Run-Fallback. |
| 21. Build 404 | Installation/Releaseartefakte unverändert; src/version.py bytegleich Baseline, keine Versions-/Feedmutation oder Updateverteilung. |
| 22. Produktdaten/Schlüssel | Nicht geöffnet oder verwendet. Nur neue synthetische Profile und deren isolierte Keychainservices. Keine produktive Migration oder Schlüsseländerung. |
| 23. Pflanzen-ZIP | Unverändert 439602 Bytes, SHA256 ef06e04c4bbc4803fb036f8dfa61151f8556a2a3f647c89b5fbe9d7dec9a31d4. |
| 24. Empfehlung | **NO-GO für produktive Freigabeprüfung**, bis der konkrete native Startblocker und die anschließend offenen Pflichtgates geschlossen sind. |

Rohbelege in beiden obigen privaten Profilcontainern: profile.json, source-provenance.json, preflight-result.json, build-run.log/build-exit.txt, smoke-preflight-result.json, bundle-before.json, bundle-code-binding.json, bundle-after-verification.json und native-v6-runner.log/native-v6-matrix.json. Zusätzlich im zweiten Kandidaten native-seed-inventory.json, native-seeded-restart-result.json, codesign-final.json und evidence-sha256.json. Temporäre Originalpfade sind keine Veröffentlichung und müssen für Nachprüfung erhalten werden. Keine Produktinstallation geöffnet, kein Push, Tag, Release, Appcastupdate oder Versionswechsel.


### V6-Reparaturabschluss – 21.10.2026 – native Gesamtfreigabe NO-GO

**Die Quellenkorrekturen sind vollständig committed und getestet. Die abschließende native Abnahme ist nicht bestanden: Der neue Paketbau wird vor dem Appbau durch den Qt-Download blockiert. Keine Produktfreigabe.** Frühere NO-GO-Nachweise bleiben unverändert erhalten.

#### Stand und gesicherte Reparaturen

Ausgangs-HEAD des Reparaturauftrags: `4e35e1cf8069f198857883d4d99835984e612c9b`. Aktueller Code-HEAD und Start dieses Abschlusslaufs: `61375c27ac508db9d65ee943cfc469a87eea1dec`, Branch `spike/python-gui`. Danach ausschließlich dieser Dokumentationsabschluss; genaue Nachweiscommit-SHA im Gitlog.

- `c83b8dc`: retained-operation-Startupfix. Regulär aufbewahrte COMPLETE-Beobachtungs-/Dokumentjournale werden strukturell und anschließend gegen keyed Persistenzereignisse bzw. Dokument-/Companionhistorie geprüft. Passender Dateiname oder unkeyed Journalhash allein erteilt keine Autorität. Offene, beschädigte, unbekannte oder unsichere Bestände bleiben gesperrt; keine automatische Reparatur, Löschung oder First-Run-Anlage.
- `5a8f1c4`: geordneter Metadatenabschluss zwischen nativen Prüfstufen.
- `65dde0f`: Parentabschluss vor authentisiertem Restorehandoff; neue Keyset-Snapshotziele nach SQLite-backup tatsächlich auf DELETE normalisieren. Quelle und historische Container bleiben unverändert.
- `e077436`: interner restore-ready-Smoke stoppt über das vorhandene Lifecycle-Signal UI-Timer; selektiver Profiler ohne bisherigen unnötigen Aufwand.
- `61375c2`: ausschließlich nach vollständig geprüftem Restore-Rollback dessen bestehenden Schlüsselkontext innerhalb desselben gelockten Starts bis zur authentisierten V6-Komposition erhalten. Installationsabgleich und aktuelle Keyset-/Envelope-/Schema-/Dokumentprüfungen bleiben aktiv. Kein Sidecarignorieren, Checkpoint-Fallback oder Produktbypass.

#### Test- und Paketprovenienz

Übernommener vollständiger Lauf des exakt committed Quellstands `61375c2`: **3466 bestanden, 104 bestehende Skips, 120 bestandene Untertests, 854.51 s, Exit 0**. Zuvor 62 gezielte Startup-/Worker-/Kompositions-/Dialogtests bestanden; realer SQLCipher-/SIGKILL-Gesamtstart nach Rollback und weiterer Neustart bestanden. Die Gegenprobe ohne Kontextübergabe reproduzierte Exit 1 / synthetic_v6_existing_keys_unavailable. Unabhängiges Review fand keine neuen konkreten P0/P1 im geprüften Quellumfang.

Diese Ergebnisse stammen aus dem bisherigen Chatlauf. Die damaligen temporären Rohlogs sind inzwischen nicht mehr vorhanden und werden nicht als aktuell nachprüfbare Dateien ausgegeben. Deshalb keine erneute Suite ohne Codeänderung; heutiger Abgleich bestätigt 481 unveränderte erfasste Quellen-/Test-/Paketdateien. Die neue source-provenance.json bindet sie an HEAD und Profil. Historische native Ergebnisse werden ausdrücklich nicht zu einer frischen Gesamtabnahme des letzten Commits erklärt.

Frisches Profil: `72072bea-9b9d-4020-a554-a81636dcfd88`; Appname `JKM-Interner-Test-72072bea9b9d4020a554a81636dcfd88`; Bundle/Worker/Restart `de.jenaplan.kompetenzmanager.internaltest.t72072bea9b9d4020a554a81636dcfd88`; Digest `5903989c2b46dcfe26ff734384dd24e108f4d1441618652cddb2ca5c41ca8c2d`. Eigene zufällige Installationsidentität, drei eigene Keychainservices, private synthetische Datenroots, eigene neue Build-/Artefaktziele, Updates false, Ad-hoc-only, keine Entitlements. Bestehende Profilvalidierung vor Build erfolgreich; keine Produktidentität als Zwischenprodukt.

**Konkreter Infrastrukturblocker:** Die unveränderte internal-test-Pipeline erreicht den Download von PySide6_Addons 6.11.1 und protokolliert Timeout/Resume bei rund 36 MB von 331.7 MB. Eigener Pipprozess nach bestätigter Profil-Elternkette beendet; Build Exit 143. Begrenzter alternativer Abruf derselben offiziellen Qt-Wheels lieferte auch nach mehr als elf Minuten keine vollständige SHA256-geprüfte Wheel und wurde beendet. Keine unvollständige Datei installiert, keine Versionsänderung, keine Signatur-/Providerprüfung umgangen. Schlechte Internetverbindung anschließend durch Nutzer bestätigt. Kein weiterer Netzwerkversuch und kein Downloadhelper im Hintergrund.

Dauerhafte lokale Nachweise: `output/v6-acceptance/2026-10-21-61375c2/` mit Profil, Commit-/Quellhashes, Buildlog/Exit, Netzwerkblocker und Schutzgrenzen. Dieser ignorierte Outputordner ist kein Produktrelease. Der Profilcontainer liegt separat im privaten Systemtemp; dessen Fortbestand ist keine dauerhafte Nachweisgarantie.

#### Abschlussmatrix

| Auftragspunkt | Tatsächlicher Stand |
| --- | --- |
| 1–3. HEAD, Ursache, Commit | Obige fünf fokussierte Reparaturcommits; letzter Code-HEAD 61375c2. Dieser Nachweiscommit enthält keinen Produktcode. |
| 4. Negative Inventartests | Im Quelllauf: offene Journale, Digest-/Schemafehler, unbekannte Felder/Fremddateien, Token-/Pfadmanipulation, Symlink/Rechte, fehlende Main/DMK, Upgrade/Replay/Restorekonflikt, ungebundene Persistenz und Read-only-Preflight geprüft. Keine neuen Skips/Ausnahmen. |
| 5. Gefüllter V4-Neustart | In früheren isolierten nativen Kandidaten nach retained-operation-Fix erfolgreich, mit regulären Beobachtungs-/Dokumentbelegen. Kein frischer Lauf am letzten Codepaket möglich. |
| 6. Paket/Signatur/Provider | Frühere Pakete qualifiziert; heutiges Profil validiert, aber Build vor Appbau abgebrochen. Kein frisches Bundle, keine neue Signatur-/SQLCipher-/CommonCryptoabnahme behauptet. |
| 7–8. V6-Startup/Migration | Historisch nativ erfolgreich: bestehendes synthetisches Konto, transaktionales V4→V6, exakter Fingerprint 4d8f4e056f5897114b3af8899947bce1f7362c52a3da96525f32baec3e9d2cc2, vollständige Originalzeilen-/Dokumentbindung und erhaltene Schlüssel. Abschlussregression des letzten Pakets offen. |
| 9. Unterrichtszeiten | Frühere native Dialog-/Persistenzprüfung erfolgreich: ungültige Zeiten abweisen, Vorlagen speichern/ändern, explizit kopieren, individuelle Zeiten und Bestandsstunden erhalten, neu laden. Menschliche Bedienabnahme offen. |
| 10. Stammgruppenstunden | Historisch nativ CRUD, Deaktivieren/Reaktivieren und Null-Fachzuordnung geprüft; menschliche Abnahme offen. |
| 11. Kombinierte Stunden | Historisch nativ genau ein Parent mit Deutsch/Mathematik und zwei Links, Persistenz nach Neustart geprüft. |
| 12. Beobachtungen | Historisch nativ bewusste Mathematikwahl, gefilterter Katalog, genau eine Beobachtung, keine Ratingverdoppelung; vorhandene 71 Ratings erhalten. Automatisierte Bedienung/Screenshotprüfung, keine menschliche Freigabe. |
| 13–14. Backup/Restore/Worker | Historisch V6-Vollbackup, unabhängige Verifikation und RESTORE_READY bestanden; V4-Container/READY gegen V6 abgewiesen. Echter paketierter SIGKILL erreicht; folgender Neustart war damals blockiert. Fix61375c2 besteht im Quell-Gesamtstart; frischer nativer Crash-/Recovery-/Worker-/Restartabschluss fehlt weiterhin. Keine vollständige Restoreabnahme. |
| 15. Produktsuite | 3466/104/120 wie oben übernommen; keine neue Suite und keine neuen nativen Laufzeittests im heutigen Abschlusslauf. Tatsächlich heute: Git-/Hash-/Registry-/Profilprüfung, Paketbauversuch, begrenzte Downloaddiagnose, unabhängiges Review. |
| 16. P0/P1/P2 | Quellreview: keine neuen konkreten P0/P1. Das native P1-Abnahmegate bleibt mangels korrigiertem Paketlauf offen. P2: historische WAL-Metadatencontainer/Restorehistorien nicht pauschal zugelassen; englische Cancel-Schaltfläche in historischer Fachwahl. |
| 17. Menschliche Abnahme | Weiterhin offen. Kompakte Prüfliste oben bleibt gültig: Anmeldung/Ansichten, Unterrichtszeiten, Stammgruppe, kombinierte Stunde, bewusste Fachwahl/Abbruch, Backup/Restore und Neustart. Nur die isolierte synthetische Test-App verwenden. |
| 18. Offene Releasegates | Frischer Build samt Codebindung/Signatur/Provider; vollständiger korrigierter Crash-/Recovery-/Worker-/Restartlauf; restliche native Startup- und Migrationsfehlerfälle; menschliche Bedienabnahme; danach separate Produktmigrations-/Releasegates. |
| 19–21. Schutzgrenzen | Produktdaten/-schlüssel/-backups nicht geöffnet oder migriert. Build404, src/version.py, Pilotfeed und Pflanzenbilder-ZIP unverändert; ursprüngliche fünf Fremddokumentänderungen erhalten. Kein Push/Tag/Release/Appcastupdate. |
| 22. Empfehlung | **NO-GO für native Gesamtfreigabe und produktiven Feature-Release.** Quellenreparaturen abgeschlossen; tatsächliche native Abnahme bis verfügbarer vollständiger Qt-Abhängigkeiten und bestandener Restgates offen. Keine automatische Folgeimplementierung. |

Produktive Final-V4-Registry bleibt unverändert und besitzt keine V4→V6-Kante. Spätere Aktivierung verlangt einen separat freigegebenen Wartungsstart mit bestehenden Schlüsseln, exakter Quelle, unabhängig geprüftem Vollbackup, Connection-Drain, transaktionaler Migration und passenden V6-Runtime-/Restoreverträgen. Kein stiller normaler Start und kein First-Run-Fallback. Build404 weist V6 zurück; kein automatischer Downgrade. Wiederherstellung muss vollständig auf ein geprüftes V4-Backup zurückgehen; spätere V6-Änderungen wären dabei verloren.

Für ein reguläres Release bleiben die bestehenden Build404-Gates maßgeblich: Developer-ID/Hardened Runtime/Entitlements, Notarisierung/Stapling/Gatekeeper, Sparkle-/Feed-/Updatesignatur und Updatekompatibilität mit tatsächlich eingesetzten Pilotständen. Kein Zugriff auf reale Pilotinstallationen in diesem Auftrag; keine neue Versions-/Buildnummer vergeben. A/B-Wochen bleiben zurückgestellt.


### Frische native V6-Abnahme – 22.10.2026 – automatisierte V6-Matrix bestanden

**Der Netzwerkblocker ist behoben. Das frische isolierte Paket besteht die vorhandene automatisierte V6-Matrix einschließlich des zuvor fehlgeschlagenen echten Crash-/Recovery- und Worker-/Restartpfads. Der P1-Reparaturnachweis ist damit nativ geschlossen. Dies ist keine vollständige Produkt-/Releasefreigabe; weitere negative Paketgates und menschliche Bedienabnahme bleiben ausdrücklich offen.** Historische NO-GO-Berichte werden nicht entfernt oder umgedeutet.

#### Herkunft und Paketidentität

Start-HEAD `f966414123bdd34927a93393a52e8e74cda567fc`, Branch spike/python-gui; ausführbarer Produktcode unverändert zum vollständig getesteten Reparaturcommit61375c2. Heute kein Produktcode geändert. Profil `58d28d02-6cba-49e7-91c8-a8af96420980`, Installation `02c0d617-d17c-4d3e-8c2d-b1f62c7d446a`, Bundle/Worker/Restart `de.jenaplan.kompetenzmanager.internaltest.t58d28d026cba49e791c8a8af96420980`, App `JKM-Interner-Test-58d28d026cba49e791c8a8af96420980.app`. Profildigest `c50a5cdfc08dd135fe011556bad6b3c513d13eeabb7656bf1bd61281eb451952`.

Die gestern gesicherten235929600 Bytes von QtAddons wurden fortgesetzt. Vollständige331714589 Bytes mit offiziellem SHA256 `54733c77f789bef5f03c6aff4ad3bec8b2eff021f0cfcbc53d5e6c250ded24f9` verifiziert. Alle gepinnten Buildabhängigkeiten erfolgreich geladen und lokal gehasht; bestehende Paketpipeline danach mit lokalem Wheelcache und ohne Indexzugriff ausgeführt. Keine Abhängigkeits-/Versionsänderung.

Vor Build bestehende Profilvalidierung: eigene private synthetische Roots und neue Build-/Artefaktpfade, getrennte drei Keychainservices, eigene Installationsidentität, identische isolierte Worker-/Restartidentität, Updates false, ausschließlich Ad-hoc, keine Entitlements. Build Exit0. Paketprüfung: SQLCipher4.17.0 community/CommonCrypto, SQLite3.53.3, Binding0.6.2+jkm.sqlcipher4170.1, forbidden_artifacts=0. Sealed-Profil/Plist/Digest stimmen; kein Produktbundle als Zwischenprodukt.

Unabhängiger Frozenvergleich: **200/200 Codeobjektvergleiche gleich**, einschließlich tatsächlichem CArchive-main und Profilhook, benötigte retained-operation-/V6-/Workerkomponenten enthalten. Nur co_filename normalisiert. Nach allen nativen Läufen **6030/6030 Bundleeinträge einschließlich Dateihashes, Modi und Linkziele unverändert**; strict/deep Ad-hoc-Signatur gültig, TeamIdentifier not set, keine Entitlements. Produktquellen stimmen weiterhin mit allen481 erfassten Byteshashes überein.

#### Tatsächlich ausgeführte native Nachweise

Die bestehende `v6-matrix` läuft im tatsächlichen neuen Frozen-Executable: **Exit0, native_v6_automated_gates_passed**. Keine Crypto-/Keychainmocks, keine neuen Skipregeln oder Sicherheitsausnahmen.

| Bereich | Ergebnis und Grenze |
| --- | --- |
| Startup/P1 | Leere synthetische Installation und kontrollierter First Run erfolgreich. Regulär befüllte Final-V4-Installation mit erhaltenen Beobachtungs-/Dokumentjournalen startet mit vorhandenem Konto erneut, kein First Run. V6-Anmeldung und Hauptfenster erfolgreich. |
| Negativer Startup | Unbekannte Datei, beschädigtes Journal, fehlende Main und realer konkurrierender Prozess gesperrt; Bestands-/Schlüsselersatz und unzulässige Mutation werden vom Runner geprüft. Bestehende paketierte Keychain-/SQLCipherbindung bestanden. |
| Zusätzliche Keychainprüfung | Sealed acl-preflight Exit0: tatsächliche item-lokale Zugriffssperre nachgewiesen, eigener temporärer Testeintrag gelöscht/wiederhergestellt/abschließend vollständig entfernt. Keine Produktkeys oder aktive DMK verändert. Dies ersetzt nicht den vollständigen Appstartfall mit verweigertem aktiven DMK. |
| V4→V6 | Synthetisch24 Schüler,3 Stammgruppen,3 Kurse,331 Kompetenzen,71 Beobachtungen/71 Ratings,10 Stundenplaneinträge,5 Dokumente sowie Schuljahr, Berichts-/LEG-Entwürfe/Revisionen/PDFs. Quelle keyed geprüft, verschlüsseltes Vollbackup unabhängig geprüft, Connection-Drain und transaktionale Migration bisCommit; exakter V6-Fingerprint unverändert. Vollständiger Originalzeilenvergleich, Dokument-/Companionbindung und vorhandene Schlüssel erhalten; neuer Prozess mit bestehendem Konto angemeldet. |
| Unterrichtszeiten | Echte Qt-Dialog-/Signalflüsse: ungültige Zeiten abweisen; Vorlage speichern/ändern; Zeiten explizit kopieren; individuell07:05–07:50 ändern; spätere Vorlage ändert Bestandsstunden nicht. Persistenz nach Neustart und Restore geprüft. |
| Stammgruppenstunden | Organisatorische Stunde ohne Fach, bearbeiten, deaktivieren/reaktivieren und temporären Eintrag löschen; keine künstlichen Fachlinks/Ratings. Endbestand TTE-000012 ohne Subjectlinks. |
| Kombinierte Stunden | Deutsch+Mathematik als genau ein Parent TTE-000011 mit zwei Links; beide Zuordnungen nach Neustart und Restore erhalten. |
| Beobachtung | Bewusste Mathematikwahl und gefilterter Kompetenzkatalog; genau eine synthetische Schnellbeobachtung, keine doppelte Bewertung, bestehende71 Ratings unverändert. Keine künstliche Fachzuordnung zur Stammgruppenstunde. |
| V6-Backup/READY | Vollbackup und unabhängige Verifikation bestanden, V6-RESTORE_READY gültig. Historischer V4-Backupcontainer und V4-READY gegen V6 gezielt abgewiesen; kein direkter Schemaersatz und keine DMK-Rotation. |
| Echter Crash/Wiederanlauf | SIGKILL Exit-9 zwischen Main- und Companionersatz. Anschließender regulärer Startup/Recovery erfolgreich; vollständige typisierte Main-/Companioninhalte gleich. Der in früheren Kandidaten bestätigte Restartblocker tritt im korrigierten Paket nicht mehr auf. |
| Regulärer Restore/Worker/Restart | Reales Parentende, paketierter Worker und echte Restart-App beendet; Transaktionsphase completed, Restart-Handschlag confirmed. Erneute Anmeldung erfolgreich. Vollständige typisierte Zeilengleichheit, fachlicher Bestand und Dokumentbindung mit unabhängigem Featurebackup verglichen; Unterrichtszeiten, Stammgruppen-/Mehrfachfachstunden und Beobachtung danach erneut geladen. |
| UI-Nachweis | Fünf aktuelle Cocoa-/Qt-Screenshots geprüft: Stundeneditor, Stammgruppenstunde, explizite Fachwahl, Mathematikbeobachtung und Hauptfenster. Automatisierte funktionale Bedienung plus toolgestützte Sichtprüfung; keine menschliche Bedienabnahme behauptet. |

#### Suite, Bewertung und verbleibende Freigabegrenzen

Vorhandene Suite **3466 bestanden,104 bestehende Skips,120 Untertests,854.51s** für denselben Produkt-/Testquellstand übernommen; kein neuer Gesamtlauf ohne Codeänderung. Die frühere Rohlogverlustgrenze bleibt wie oben dokumentiert. Heute tatsächlich neu: vollständiger frischer Build/Audit, Sealed-Preflight, native V6-Matrix, reale ACL-Verweigerungsprüfung, Frozen-/Bundlevergleich, Screenshotprüfung und unabhängiges Abschlussreview.

Im geprüften Reparatur-/V6-Matrixumfang keine offenen P0/P1. Das ist keine Aussage über noch nicht ausgeführte Paketfälle. P2 bleibt die englische Cancel-Schaltfläche in der expliziten Fachwahl; historische WAL-Metadatencontainer und Mehrfach-Restorehistorien erhalten keine pauschale zusätzliche Zulassung.

Noch offene Gates, ausdrücklich auch vom Runner ausgewiesen:

1. Restliche vollständige native Startupmatrix: insbesondere fehlender aktiver DMK bzw. dessen Zugriffssperre im ganzen Appstart, unbekannte Schemaidentität, beschädigte Cipherdatenbank und weitere unsichere/partielle Zustände am finalen Paket. Bestehende Quellregressionen gelten weiter; nicht als heute ausgeführte Frozenfälle ausgegeben.
2. Vollständige paketierte Migrationsfehlerkampagne (SQLfehler, Prozessabbruch vor/nachCommit, ENOSPC, beschädigte Quelle, fehlendes Backup und fehlerhafte Zielintegrität). Bestehende echte SQLCipher-/Crashquelltests bleiben zugeordnete Quellnachweise, keine pauschale neue Paketabnahme sämtlicher Fehlergrenzen.
3. Menschliche Bedienabnahme durch Laura: synthetisch anmelden, Dashboard/Übersichten/Bewertungen/Berichte ansehen; Zeitvorlagen samt individuellen Zeiten ändern; Stammgruppen-CRUD; kombinierte Stunde ändern; Fachwahl abbrechen und bewusst wählen; Restore/Neustart und Dokument öffnen. Lokale private Testanleitung mit ausschließlich synthetischem Anmeldepasswort liegt im Nachweisordner.
4. Separat autorisierte produktive V4→V6-Integration und die bestehenden Build404-Releasegates: bewusster Wartungsstart, registrierte exakte Produktkante, unabhängiges Vollbackup, Wiederherstellungs-/Rollbackgrenzen, Developer-ID/Hardened Runtime/Notarisierung, Sparkle-/Updateprüfung und Pilotkompatibilität. Keine neue Versions-/Buildnummer oder Produktaktivierung in diesem Auftrag.

**Empfehlung: P1-Reparatur und vorhandene native V6-Matrix erfolgreich abgenommen; NO-GO für vollständige native Gesamt-/Produktreleasefreigabe bis die ausdrücklich offenen Gates geschlossen sind.** Der Netzwerk- und bisherige Crash-/Restartblocker sind behoben. Keine neue Architekturphase oder automatische Folgeimplementierung.

#### Dauerhafte Nachweise und Schutzgrenzen

Nachweisordner `output/v6-acceptance/2026-10-22-f966414/`: source-provenance.json, profile.json, dependency-wheel-sha256.json, build-run.log/build-exit.txt, smoke-preflight.json, bundle-code-binding.json/bundle-after-verification.json, native-v6-matrix.json und alle Teilberichte, native-keychain-denial.json, native-v6-ui/, verifiziertes isolated-test-app.zip sowie privater manual-test-instructions.txt. App-ZIP dient der Nachweissicherung; das versiegelte Testprofil bleibt an seinen privaten Runtimepfad gebunden. Kein portabler Produktinstaller oder Releaseartefakt. Die App selbst liegt im Profilcontainer unter artifacts; keine Produktinstallation geändert.

Vorher HEADf966414, nachher ausschließlich nachfolgender fokussierter Nachweiscommit (siehe Gitlog); alle fünf vorbestehenden Fremddokumentänderungen erhalten, Staging nach Commit leer. Produktregistry weiterhin ausschließlich FinalV4 ohne Upgradekante, produktive Migration gesperrt. src/version.py, Build404/Pilotfeed und Pflanzenbilder-ZIP bytegleich; keine Produktdaten/-schlüssel/-backups geöffnet oder verändert. Kein Push, Tag, Release, Appcastupdate, Versionswechsel oder A/B-Wochen.


### Fachpflanzen: isolierte V6-Test-App – 22.10.2026

Quellstand `985ea8456e2c63df0d17a4c7c340dbf6b65dfa7c`; Produkt-UI zuletzt `566669b`, davor Pflanzenfunktion `0fbeacf`, abgegrenzte V6-Restkorrektur `ff77a98`. Frischer bestehender internal-test-Pipelinebuild Exit 0, ausschließlich synthetische Identität `a17a3d60-4f58-4694-ac0e-9f3726dab483`, eigene drei Keychainservices, Updates deaktiviert, Ad-hoc ohne Entitlements. Neue App: `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-a17a3d604f584694ac0e9f3726dab483/artifacts/JKM-Interner-Test-a17a3d604f584694ac0e9f3726dab483.app`. Alte Test-App und Produktinstallation nicht überschrieben.

Berechnung: vorhandene kanonische aktuelle Cockpitstände; sichere Bestätigung vor vorhandenem Beobachtungsvorschlag, jede gültige aktive aktuelle Kompetenz-ID einmal, keine Historienmehrfachzählung und keine Nullwerte für fehlende Bewertungen. Gleichgewichteter Token-Scoremittelwert, bestehende Schwellen und vorhandene Pflanzen. Keine gespeicherte Bewertung, Schulnote, neue Bilddatei oder Schemaänderung.

Gezielte Nachweise: 60 Startup-/Compositiontests bestanden; 112 Paketprofiltests bestanden. Nach der bei nativer Sichtprüfung gefundenen lokalen Höhenkorrektur erneut 353 UI-/Adaptertests und 74 Unterprüfungen bestanden (41,73 s). Zusätzlich kombinierter Profil-/Pflanzenlauf 121 bestanden (enthält die neun neuen Pflanzenfälle, keine zusätzlichen 121 unabhängigen Fälle). Unabhängige Reviews ohne offenen blockierenden Befund. Keine neue Gesamtsuite, Sicherheitsmatrix oder erneute Migrationsgrundsatzprüfung.

Finales Paket: Build/Sealed-Preflight erfolgreich; vorhandene synthetische Fixturevorbereitung, regulärer V6-Start, gezielter `v6-subject-plants` und anschließender regulärer Neustart jeweils Exit 0. Drei echte synthetische Profilbundles mit 2, 5 und 12 Chips; alle vier Pflanzenstufen und neutrale Fächer, keine Rechtecküberschneidung. Vollständige native Fachkartenbilder visuell geprüft, keine überlagerten Texte/Aktionen oder verlorenen Fächer. Bestehende Alle-anzeigen-Aktion und Fachnavigation erhalten. Cocoa verarbeitet verschachtelte Layoutanforderungen; nach unabhängiger Reproduktion verarbeitet der Smoke vor der unveränderten Geometrieprüfung begrenzt vier Ereignisdurchläufe. Kein menschlicher Bedienabnahmenachweis.

200/200 Frozen-Codevergleiche stimmen mit dem Quellstand überein. Nach allen Smokes 6030/6030 Bundleeinträge unverändert, strict/deep Signatur weiter gültig. Nachweise: `output/v6-acceptance/2026-10-22-subject-plants-delivery/`; Testpasswort und genaue Bedienfolge ausschließlich in privater `Anleitung-fuer-Laura.txt`, vollständige Bilder unter `native-subject-plants/`. Kein portabler Produktinstaller.

Zwischenbefunde erhalten: Sandbox-Iconfehler, ein korrigierter responsiver Smoke-Vergleich, vorzeitig geprüfte Cocoa-Geometrie und ein ENOSPC-Build. Ausschließlich fünf eigene regenerierbare Buildroots dieses Auftrags nach Profil-/Prozessprüfung entfernt; App-Bundles, Profile, synthetische Daten und Nachweise erhalten, kleine Buildinputs gesichert. Keine allgemeine Speicherbereinigung.

Offen bleiben die vollständige frühere native V6-Restabnahme und menschliche Bedienabnahme durch Laura. Deren alte erweiterte Runner-/Migrationskampagnennachweise werden nicht durch diese UI-Smokes ersetzt. Keine Produktfreigabe, Produktmigration, Änderung an Build 404/Pilotfeed/Pflanzen-ZIP oder Zugriff auf Produktdaten/-schlüssel; kein Push, Tag oder Release. Alle fünf vorbestehenden Fremddokumentänderungen bleiben unverändert außerhalb der Commits.


## Modernisierte Zeitfelder: isolierte Test-App – 22.10.2026

PO-Präzisierung betrifft die kräftige Markierung der Zeitziffern, nicht blaue Aktionsbuttons. Zentrale QAbstractSpinBox-Stile für Zeit-/Datums-/Zahlenfelder: kleine klare Outline-Pfeile, flache Hoverflächen, LIGHT_TEAL/COLOR_TEXT für ausgewählte Ziffern. Keine Fach-, Validierungs-, Schrittweiten- oder Speicheränderung.

Quellcommit `c881cf218863d6c853d98523caa3e80dfeef3215`. 15 gezielte Feld-/Vorlagenprüfungen und 11 Theme-/Dialogprüfungen grün; bestehende Adapterfälle im breiteren Lauf bestanden, ein neuer DateTime-Fokustest anschließend korrekt auf die zu bearbeitende Sektion gesetzt und im grünen 15-Fälle-Lauf erneut geprüft. Native Cocoa-Quellvorschauen Unterrichtszeiten und kompakter Stundenplan-Dialog visuell kontrolliert: klare Pfeile, dezente Ziffernauswahl, keine abgeschnittenen Felder oder Aktionen. Vorschauen unter output/ui-previews/2026-10-22-spin-controls/.

Frisches isoliertes V6-Paket über bestehende Pipeline: Build 0, Sealed-Preflight 0, bestehende synthetische Fixturevorbereitung und regulärer V6-Neustart 0. 200/200 Frozen-Codevergleiche gleich; beide Pfeil-SVGs bytegleich im Bundle. Nach den Smokes 6031/6031 Bundleeinträge unverändert, strict/deep Ad-hoc-Signatur gültig, keine Entitlements. Keine neue Sicherheitsmatrix oder Produktfreigabe.

App: `/private/var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-internal-test-c798eaa6651247e588056c34b3a47588/artifacts/JKM-Interner-Test-c798eaa6651247e588056c34b3a47588.app`. Private Testanleitung/-passwort und genaue Nachweise: `output/v6-acceptance/2026-10-22-time-controls/Anleitung-fuer-Laura.txt`. Die bisherige geöffnete Test-App samt Testeingaben bleibt unverändert erhalten; neue App besitzt eigenen synthetischen Bestand und isolierte Identitäten/Schlüsselservices. Produktdaten, Build 404, Pilotfeed und Pflanzen-ZIP unberührt; kein Push, Tag oder Release. Fünf fremde Dokumentänderungen weiterhin vollständig außerhalb des Commits.


## Migrationsassistent 406 – technischer Abschluss / NO-GO

Implementiert in 7c9f22d; vorläufige Version 0.5.1/406 in 912e902; Supportdiagnose c7cd1f0; Startup-/Versionsregression 969232c. Vorhandene V4→V7-Engine, Existing-only-Keys, verschlüsseltes unabhängig geprüftes Vollbackup, Connection-Drain, Transaktion und separater authentifizierter Abschluss unverändert verwendet. UI bestätigt bewusst, verwendet Runtimepfad automatisch, zeigt echte Phasen ohne Prozente und startet kontrolliert neu. Fehler erhalten Daten/Belege; Wiederaufnahme bietet ausschließlich bestehende Completion an. V7 wird nicht erneut migriert. Neue Installation bleibt im ersten Start V4 und bietet Migration beim Folgestart; direkte V7-Erstanlage würde zusätzlichen Lifecyclevertrag benötigen.

Nachweise: Gesamtsuite 3564 bestanden, 104 Skips, 120 Unterprüfungen, drei Fehler; zwei auftragsbezogene Fehler korrigiert, gezielte Regression danach 194 bestanden. Finale Produkt-/Startup-/Assistentenregression 107 bestanden. Ein unverändert vorbestehender Noticehashkonflikt bleibt: seit d90011e Produktnotice 04b50956… gegenüber reproduzierbarer Wheelnotice c72b6095…. Keine isolierte Hashanpassung, da dies die Wheelbindung widersprüchlich machen würde.

Native 405-V4→406 mit Paketquelle 912e902: bestehende Anmeldung, Zustimmung/Checkbox, reale Sicherungsphase, Wartung, Neustart, bisherige Anmeldung, Erfolgsmeldung und Dashboard tatsächlich bedient. Unabhängiger Paketsnapshot bestätigt Schema7, vollständig erhaltene unveränderte Tabellen, Dokumente und Schlüsselkontext. Wiederholter V7-Start bestanden. Das beweist nicht die vollständige native Bedienung des nachfolgenden finalen Pakets.

Finaler lokaler Paketbau aus sauberem 969232c77a42d4ef81d6870a5ffa17eb316b3f42 mit bestehender Pipeline erfolgreich; deep/strict Codesign gültig, ad-hoc/nicht notarisiert. DMG 206334364 Bytes, SHA256 440d5ed217a8cbb5f8d25ae33a559e729d68f1528bb3a177a5e066cb1b28fdfb. Pfad im lokalen Buildbericht unter /var/folders/61/nxlq0vm9311gvx30ztnpj63r0000gn/T/jkm-406-rebuild-jvxvjj4c/. Finaler 406 öffnet getrennte Original404-V4-Testkopie mit vorhandener Anmeldung. Vollständige native Migration dieses finalen Pakets bleibt wegen wiederholtem ScreenCaptureKit -3812 offen; keine UI-Bestätigung ersetzt oder automatisiert.

Testgrenzen/Vorfall: Testextraktionsmanifest außerhalb Runtime erhalten, ohne Datenbank-/Schlüsseländerung. Sandboxblockierte Vorläufe getrennt dokumentiert. Native Appauswahl startete unbeabsichtigt eine alte gleichnamige Test-App ohne Testrootargument; PID22158 hielt regulären instance.lock. Sofort beendet; lsof zeigte keine offene Fachdatenbank. Keine Anmeldung oder Migration darin bestätigt. Deshalb keine pauschale Aussage, der reguläre Produktroot sei vollständig unberührt. Keine Schlüsselrotation, kein Produktdatenimport/-migration beauftragt oder ausgeführt.

Offen: vollständiger finaler nativer 404/405→406-Assistentenpfad, vollständige paketierte Restoreabschlussabnahme und konsistenter zusätzlicher Packagingvertrag für Notice/Wheel. NO-GO für qualifizierten Releasekandidaten; keine Veröffentlichung, Push, Tags oder Feedänderungen. Originale 405-Assets und fremde Dokumentänderungen erhalten. Rohbelege: release/output/migration-assistant-406/.


Restore-Nachtrag 406: Synthetischer Harnessabschluss per bestehendem checkpoint_truncate unter RuntimeInstanceLock bestanden; Main, Companion und drei Metadaten-Dateihashes unverändert. Anschließend Restart und migration-snapshot Exit0. Vergleich main_content gleich, managed_document_hashes jedoch nicht gleich; vollständiger Dokumentvergleich daher offen/abweichend, kein vollständiger Restoreerfolg behauptet. Keine weiter laufenden Testprozesse.


## Build 406 – konkrete Gates abgeschlossen / 01.11.2026

Paketquelle `ddaee98594ec4d20bb092898ff282000260f1c9f` sauber gebaut; Notice-/Wheelbindung mit belegter historischer Notice getrennt, aktives Dokumentinventar nach Restorevorbereitung korrigiert. Reguläre Produktsuite: 3571 bestanden, 104 bestehende Skips, 120 Unterprüfungen bestanden. Finales Paket: deep/strict gültige Ad-hoc-Signatur, exakte 4.17/CommonCrypto-Runtime, alle Notices und Artefakthashes geprüft. Laura bediente und bestätigte native 404→406, 405→406, erneuten V7-Start ohne Assistent und vollständige leere Einrichtung/Onboarding. Unabhängige Endpaketprüfungen bestätigen Daten, Dokumente, bestehende Schlüssel/Passwort, vollständige verschlüsselte Quellbackups und echten vollständigen V7-Restore/Neustarthandshake. Die Agent-Bildschirmaufnahme blieb -3811-blockiert; die native UI-Abnahme ist ausdrücklich eine Benutzerabnahme mit unabhängiger technischer Verifikation.

Direkte V7-Erstanlage ist ohne neuen First-Run-/Restartvertrag nicht aus vorhandenem Initialisierer verfügbar; gemäß Auftragsausnahme bleibt die begründete UX-Einschränkung V4-Erstanlage mit geführtem Folgestartübergang. Kein neues Schema und keine Architekturausweitung. Frühere offene UI-Gates sind durch diese spätere Abnahme geschlossen. Vollständiger Bericht einschließlich separat protokolliertem fehlgeschlagenem historischen Binding-Zusatzlauf: `release/output/migration-assistant-406/FINAL406_GATE_REPORT.md`.

**BUILD 406 ALS RELEASEKANDIDAT QUALIFIZIERT**. Dauerhaftes DMG: `release/output/0.5.1-build406-ddaee98594ec/Jenaplan-Kompetenzmanager-0.5.1-macOS-arm64.dmg`, SHA256 `cf09b5550dfcd87ccffc19e4754c9b997101e3b1b749f00ecad76d393e65f387`; alle Hashes in `SHA256SUMS-ALL-406.txt`. Keine Veröffentlichung, Push, Tags oder Feedänderung; Build405 und fremde Änderungen erhalten. STOP.


## Build 406 – Veröffentlichungsvorbereitung 01.11.2026

PO-Auftrag: keine Veröffentlichung, keine Fachfunktionen. Drei historische
Sprint-11-Smokes gezielt reproduziert: historischer Defaultprovider erwartet
Binding 0.6.2 / SQLCipher 4.12, installiert ist das qualifizierte 4.17-Binding.
Alle drei scheitern vor den jeweiligen Manipulationsprüfungen mit
`sqlcipher_binding_version_incompatible`. Produktkomposition übergibt explizit
4.17; historische Module sind im Produktspec ausgeschlossen. Kein Produktfix,
keine neuen Skips oder gelockerten Prüfungen. Einzelbelege und Releaseabschluss
unter `release/output/406-publication-preparation/`.

Acht bestehende Dokumentprofile gezielt auf Assistent, V4-Erstanlage,
404/405→406, Passwortkontinuität, Backup/Restore und Rückkehrgrenze nachgeführt.
Synthetische Qt-Dialogabbildungen ergänzt. Eingebettete PDFs benötigen neuen
Pipelinekandidaten und erneute betroffene Paketgates. Build 405 und bisheriger
406-Kandidat bleiben unverändert. Remoteprüfung lesend: 405 veröffentlicht,
406-Tag/Release nicht vorhanden, Stable-Verzeichnis nicht vorhanden.


## Build 406 – finales Auslieferungsset / Schlüsselkontinuität noch offen

Finales Set: `release/output/0.5.1-build406-final-20261101/`.
Paketquelle `4f478de`, unveränderte qualifizierte Produktbasis `ddaee98`,
externe Dokumentationsquelle `1bfcfe3`. Acht PDFs / 63 Seiten und 27 aktuelle
synthetische Abbildungen in vollständiger geprüfter ZIP. Die Handbuchrevision
ändert nur externe Dokumentation; der neue Pipeline-DMG bleibt bytegleich.
Elf Paketgates und Restore-Worker-Smoke am neuen DMG bestanden. Alle 211
Frozen-Projektmodule plus Main sowie 775 Frameworkdateien entsprechen dem
qualifizierten 406; DMG-App und geprüftes Bundle stimmen in 6196 Einträgen
überein, eingebettete PDFs bytegleich mit Pipelineausgabe.

Alle vier Veröffentlichungsassets, Sparkle-Notes und ausschließlich lokal
bereitgestellter Feed sind Ed25519-signiert und unabhängig gegen den
bestehenden Pilot-Vertrauensschlüssel geprüft. Nativ mit Sparkle bestätigt:
406 > 404 und 406 > 405, gleiche Bundle-ID/Feed/Public Key. Öffentlicher
405-Feed kryptografisch geprüft; alte Einträge im lokalen Feed erhalten.

Zusätzliches Pflichtgate des neuen Ad-hoc-Codehashs bleibt offen: vorhandene
synthetische 404-/405-Schlüsselkontexte warten auf reguläre macOS-Freigabe.
Zwei enge Bestandsproben liefen in Timeout; neuer Prüfprozess hängt belegt in
SecItemCopyMatching, securityd protokolliert die angeforderte ACL-Rückfrage.
Keine Lock-/ACL-Umgehung, Schlüsselkopie oder Rotation. Benutzer um die
Systemfreigabe gebeten. Keine bestätigte neue P0/P1, aber NO-GO für vollständige
Veröffentlichungsvorbereitung bis dieses neue Paketgate nachgewiesen ist.
Die ursprünglichen nativen 404/405→406-Nachweise ersetzen es nicht.

Alle sechs fremden Dokumentänderungen erhalten, Index getrennt gehalten.
Keine Veröffentlichung, kein Push/Tag/Release/Appcastupdate/Stable-Rollout.
Bericht und Hashes im finalen Set. Gesonderte ausdrückliche PO-Freigabe und
öffentliche Auslieferungsprüfung bleiben spätere Veröffentlichungsschritte.
