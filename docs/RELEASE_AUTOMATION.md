# Pilot-Releaseautomation

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
