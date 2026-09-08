# Pilot-Releaseautomation

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

Für die sichtbare App-Prüfung den Startprozess mit explizitem synthetischem
Datenroot in einer laufenden Terminalsession gebunden halten. Vor jedem
Computer-Use-App-Aufruf die laufende Prozessidentität und Testargumente
bestätigen: Der App-Aufruf kann eine bereits beendete App automatisch neu
starten und dabei den Testpfad-Override verlieren. Ein dann angezeigtes normales
Anmeldefenster ohne Eingabe schließen; es ist kein gültiger Testnachweis.
