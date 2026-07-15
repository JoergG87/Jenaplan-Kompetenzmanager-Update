# Pilot-Installation unter macOS

## Paketstand

- Produkt: `Jenaplan-Kompetenzmanager`
- Pilotversion: `0.1.1`
- Architektur: Apple Silicon (`arm64`)
- minimale unterstützte Version: macOS 13
- Auslieferungsvariante: `laura` mit ausschließlich fiktiven Pilotdaten
- technische Prüfvariante: `empty` ohne Schüler und Dokumente
- Auto-Updater und App-Store-Verteilung: nicht vorhanden

Das App-Bundle enthält Python 3.14, PySide6 6.11 und die benötigten Qt- und
PDF-Laufzeitbestandteile. Auf dem Ziel-Mac werden weder Python, Terminal,
Repository noch Entwicklungsumgebung benötigt.

Die kurze Lehrkraftfassung liegt in `docs/PILOT_INSTALLATION_LEHRKRAFT.md` und
wird beim Build als
`Jenaplan-Kompetenzmanager-Pilot-0.1.1-Installationsanleitung.pdf` erzeugt.

## Reproduzierbarer Build

Der Build läuft auf Apple Silicon mit Python 3.14.6 und den vollständig
versionierten Paketen aus `requirements-macos-build.txt`:

```bash
# Leer, nur für den technischen Paket-Smoke-Test
scripts/build_macos_pilot.sh --data-mode empty

# Fiktive Übergabe für Laura
scripts/build_macos_pilot.sh --data-mode laura
```

Die Buildvarianten überschreiben einander nicht beim DMG:

```text
dist/macos/Jenaplan-Kompetenzmanager-SmokeTest-0.1.1-macOS-arm64.dmg
dist/macos/Jenaplan-Kompetenzmanager-Pilot-0.1.1-macOS-arm64.dmg
```

Der zuletzt ausgeführte Build stellt außerdem
`dist/macos/Jenaplan-Kompetenzmanager.app` bereit. Beide Builds erzeugen die
versionierte Installationsanleitung, Erste Schritte, das PDF-Benutzerhandbuch,
den Schnellstart, die Backup-Anleitung, das technische Backup-Skript und
SHA-256-Prüfsummen. Die Variante `laura` erzeugt zusätzlich ausschließlich aus
diesen aktuellen Ausgaben das Übergabepaket
`dist/Jenaplan-Kompetenzmanager_Pilot_0.1.1_Laura.zip`.

Das Skript erzeugt eine isolierte Build-Umgebung, entfernt nur seine bekannten
alten Zwischenausgaben und prüft die Datenvariante. `empty` darf keine
SQLite-Datei im Bundle enthalten. `laura` muss genau eine Startdatenbank und die
Kennzeichnung `FIKTIVE_PILOTDATEN.txt` enthalten. Die technische Versionsquelle
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

Schnellstart, Pilottestdatei, Backup-Skript und ergänzende Dokumentation werden
bewusst im getrennten Laura-ZIP ausgeliefert, damit das Installationsfenster
ruhig und eindeutig bleibt.

## Installation und erster Start

1. Das DMG öffnen.
2. `Jenaplan-Kompetenzmanager.app` auf `Programme` ziehen.
3. Das DMG auswerfen.
4. Die App im Ordner `Programme` öffnen.

Beim ersten Start legt die App den lokalen Datenordner an. Die Laura-Variante
kopiert ihre ausdrücklich fiktive Datenbank und die zugehörigen Dokumente nur,
wenn noch keine Benutzerdatenbank existiert. Vorhandene Daten werden nie ersetzt.
Die technische `empty`-Variante initialisiert eine leere Schülerdatenbasis mit
Stammdaten- und Katalogdefaults.

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

Für ein Update wird die vollständig geschlossene `.app` in `Programme` durch
die neue `.app` ersetzt. Die Daten bleiben erhalten, weil sie außerhalb der App
liegen. Es gibt bewusst keinen automatischen Updater.

Das Löschen der `.app` entfernt nur die Anwendung. Die Benutzerdaten bleiben
bewusst erhalten und dürfen nur nach gesonderter Entscheidung und Sicherung aus
dem lokalen Datenordner entfernt werden.

## Bekannte Pilotgrenzen

- nur Apple-Silicon-Macs, kein Intel-/Universal-Build;
- keine Windows-Version;
- keine automatische Aktualisierung;
- keine Cloud-Synchronisation oder Benutzerkonten;
- ohne Developer-ID keine Notarisierung und daher Gatekeeper-Hinweis beim Erststart.
