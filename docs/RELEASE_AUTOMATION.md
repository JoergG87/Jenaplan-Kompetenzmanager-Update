# Pilot-Releaseautomation

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
