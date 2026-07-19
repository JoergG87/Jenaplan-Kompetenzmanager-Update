# Pilot-Installation unter macOS

## Paketstand

- Produkt: `Jenaplan-Kompetenzmanager`
- Pilotversion: `0.2.2` / Build `202`
- Architektur: Apple Silicon (`arm64`)
- minimale unterstützte Version: macOS 13
- Auslieferungsvariante: `release` ohne Schüler-, Pilot- oder Runtime-Daten
- technische Prüfvariante: `empty` ohne Schüler und Dokumente
- Updatekanal: beaufsichtigter Sparkle-2-Pilotkanal; Stable deaktiviert
- Ausgangsversion `0.2.1`, erstes Pilotupdate `0.2.2`; keine automatische
  Prüfung, kein Hintergrunddownload und keine unbeaufsichtigte Installation

Das App-Bundle enthält Python 3.14, PySide6 6.11 und die benötigten Qt- und
PDF-Laufzeitbestandteile. Auf dem Ziel-Mac werden weder Python, Terminal,
Repository noch Entwicklungsumgebung benötigt.

Die kurze Lehrkraftfassung liegt in `docs/PILOT_INSTALLATION_LEHRKRAFT.md` und
wird beim Build als
`Jenaplan-Kompetenzmanager-Pilot-0.2.2-Installationsanleitung.pdf` erzeugt.

## Reproduzierbarer Build

Der Build läuft auf Apple Silicon mit Python 3.14.6 und den vollständig
versionierten Paketen aus `requirements-macos-build.txt`:

```bash
# Leer, nur für den technischen Paket-Smoke-Test
scripts/build_macos_pilot.sh --data-mode empty

# Leerer Release-Kandidat und Übergabepaket für Laura
scripts/build_macos_pilot.sh --data-mode release
```

Für das lokale Laura-Paket wird die führende Abnahmemappe bei Bedarf ohne
Speicherung eines Benutzerpfads im Repository über `LAURA_TEST_WORKBOOK`
übergeben. Ohne Variable verwendet der Build die versionierte Repository-Kopie.

Die Buildvarianten überschreiben einander nicht beim DMG:

```text
dist/macos/Jenaplan-Kompetenzmanager-SmokeTest-0.2.0-macOS-arm64.dmg
dist/macos/Jenaplan-Kompetenzmanager-0.2.0-macOS-arm64.dmg
```

Der zuletzt ausgeführte Build stellt außerdem
`dist/macos/Jenaplan-Kompetenzmanager.app` bereit. Beide Builds erzeugen die
versionierte Installationsanleitung, Erste Schritte, das PDF-Benutzerhandbuch,
den Schnellstart, die Backup-Anleitung, das technische Backup-Skript und
SHA-256-Prüfsummen. Die Variante `release` erzeugt zusätzlich ausschließlich
aus den aktuellen, freigegebenen Ausgaben das Übergabepaket
`dist/Jenaplan-Kompetenzmanager-0.2.0-Pilotpaket-Laura-macOS-arm64.zip`.

Das Skript erzeugt eine isolierte Build-Umgebung, entfernt nur seine bekannten
alten Zwischenausgaben und prüft die Datenvariante. `empty` und `release` dürfen
keine SQLite-Datei im Bundle enthalten. Die technische Versionsquelle
ist `src/version.py`; `pilot_build_info.json` nennt Version, Architektur,
Git-HEAD, Quellbaumzustand, Datenvariante und sichtbare Kennzeichnung. Die
Entwicklerdatenbank `data/kompetenzmanager.sqlite` wird nie übernommen.

Dateisystem-, Signatur- und DMG-Zeitstempel verhindern eine Zusage
bitidentischer Builds. Inhalt und Ablauf sind reproduzierbar.

## DMG-Layout und Inhalt

Das DMG verwendet ein 700 × 500 Pixel großes ruhiges Finder-Layout aus der
bestehenden blau-grauen Designsprache. App und Programme-Verknüpfung stehen als
gleichwertige große Ziele mit klarer Pfeilrichtung gegenüber. Die
Installationsanleitung liegt darunter. Das Hintergrundbild wird reproduzierbar
durch `scripts/create_macos_dmg_background.py` erzeugt.

Sichtbarer DMG-Inhalt:

- `Jenaplan-Kompetenzmanager.app`
- `Programme` als Verknüpfung nach `/Applications`
- `Installationsanleitung.pdf`

Schnellstart, Pilottestdatei, Release-Hinweise und Prüfsummen werden bewusst im
getrennten Laura-ZIP ausgeliefert, damit das Installationsfenster ruhig und
eindeutig bleibt.

## Installation und erster Start

1. Das DMG öffnen.
2. `Jenaplan-Kompetenzmanager.app` auf `Programme` ziehen.
3. Das DMG auswerfen.
4. Die App im Ordner `Programme` öffnen.

Beim ersten Start legt die App den lokalen Datenordner an. Der Release-Kandidat
enthält keine Startdatenbank, Pilotdaten oder Dokumente. Vorhandene Daten werden
nie ersetzt. Die Anwendung initialisiert die leere fachliche Datenbasis erst
nach erfolgreicher Authentifizierung; Stammdaten- und Katalogdefaults enthalten
keine Kinder.

## Gatekeeper und Signierung

Ohne verfügbare Apple Developer-ID wird der lokale Pilotbuild ad-hoc signiert
und nicht notarisiert. macOS kann deshalb beim ersten Start warnen oder den
Doppelklick zunächst ablehnen.

In diesem Fall:

1. im Finder mit gedrückter Control-Taste auf die App klicken;
2. `Öffnen` wählen und den Start bestätigen;
3. falls macOS weiter blockiert, `Systemeinstellungen -> Datenschutz & Sicherheit`
   öffnen und dort für diese App `Dennoch öffnen` wählen.

Es werden keine Zertifikate, Notarisierungszugänge oder Kennwörter mitgeliefert.
Ist `MACOS_SIGN_IDENTITY` gesetzt oder eine lokale `Developer ID Application`
auffindbar, signiert das Build-Skript die App mit Hardened Runtime und
Zeitstempel, verifiziert alle verschachtelten Bestandteile und signiert danach
das DMG. Die Notarisierung bleibt ein gesonderter Schritt mit lokalem
Keychain-Profil:

```bash
xcrun notarytool submit <DMG> --keychain-profile <PROFIL> --wait
xcrun stapler staple <DMG>
```

Profilname und Apple-Zugangsdaten werden weder im Skript noch im Repository
gespeichert.

## Lokale Daten

Veränderliche Daten liegen immer außerhalb der App unter:

```text
~/Library/Application Support/Jenaplan-Kompetenzmanager/
├── kompetenzmanager.sqlite
├── documents/
├── exports/
├── backups/
└── logs/
```

- `documents/` enthält lokal verwaltete Anhänge sowie finale Bericht- und LEG-PDFs.
- `exports/` ist der vorgeschlagene Ablageort für frei gewählte Entwurfs-Exporte.
- `backups/` enthält Sicherungen des technischen Pilot-Backup-Skripts.
- `logs/` enthält kleine rotierende technische Start- und Fehlerprotokolle.

## Aktualisieren und Deinstallieren

`0.2.0` bleibt unverändert und wurde Laura nicht installiert. Ihre erste
tatsächliche Installation ist direkt das manuell geöffnete Pilot-DMG `0.2.1`.
Das erste Folgeupdate ist `0.2.2` / Build `202` über den bewusst ausgelösten
Sparkle-Pilotkanal.
Es ist ad hoc signiert und nicht notarisiert; ein inhaltlich neu gebautes
`0.2.0` wird nicht verteilt. Die Daten bleiben außerhalb der App.

Ab einer updaterfähigen, vollständig freigegebenen Basis sieht die Lehrkraft
unter `Einstellungen -> Updates` installierte Version/Build, den festen Kanal,
letzte Prüfung und `Nach Updates suchen`. Im Pilotkanal erfolgt die Prüfung nur
bewusst; automatische Prüfung, Download, Installation und erzwungener Neustart
bleiben deaktiviert. Installation wird bei laufendem Backup/Restore/Support-
Reset, anderem Schreibvorgang oder ungespeichertem Arbeitsstand verschoben.

Der Updater ersetzt nur das App-Bundle. Fachliche Datenbank, Dokumente,
Exporte, Backups, Logs, Security Store, Einstellungen und macOS-Schlüsselbund
bleiben unverändert. `0.2.2` enthält weder Fach- noch Securitymigration. Ein manueller
Rollback auf ein aufbewahrtes vorheriges DMG ist nur zwischen
schemaidentischen Versionen zulässig.

Ein produktiver Updatekanal bleibt deaktiviert, solange Developer-ID-Signierung,
Hardened Runtime, Apple-Notarisierung und Stapling, signierter HTTPS-Appcast,
externe Sparkle-EdDSA-Schlüsselverwaltung, Pilot-/Stable-Trennung und die reale
Keychain-/Touch-ID-Prüfung nicht vollständig bestanden sind. Bei Feed-,
Signatur-, Plattform-, Netzwerk- oder Installationsfehlern wird nicht
weiterinstalliert; die UI verweist ruhig auf den manuellen DMG-Pfad.

Das Löschen der `.app` entfernt nur die Anwendung. Die Benutzerdaten bleiben
bewusst erhalten und dürfen nur nach gesonderter Entscheidung und Sicherung aus
dem lokalen Datenordner entfernt werden.

## Bekannte Pilotgrenzen

- nur Apple-Silicon-Macs, kein Intel-/Universal-Build;
- keine Windows-Version;
- keine automatische Aktualisierung;
  der Sparkle-2-Folgepfad ist entschieden, aber bis zu allen Release-Gates
  nicht produktiv;
- keine Cloud-Synchronisation oder Benutzerkonten;
- ohne Developer-ID keine Notarisierung und daher möglicher Gatekeeper-Hinweis
  beim Erststart;
- produktiver Support-Reset ist ab `0.2.2` als betreuter Ausnahmeweg aktiviert;
  Recovery-Code bleibt der bevorzugte erste Weg;
- echte Sleep/Wake-, physische Touch-ID-, App-Switcher- und vollständige reale
  Aktivierungs-/Widerrufsprüfung noch offen.
