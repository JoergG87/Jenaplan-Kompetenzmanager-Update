# Jenaplan-Kompetenzmanager

Der Jenaplan-Kompetenzmanager ist eine PySide-Desktop-App zur strukturierten Verwaltung, Auswertung und zukuenftigen Ausgabe von Kompetenzdaten im Jenaplan-Kontext.

SQLite ist die lokale produktive Datenbasis. Excel-/VBA-Artefakte aus der fruehen Projektphase liegen nur noch im Legacy-Archiv `legacy/excel/`.

Die vollständige Projektdokumentation befindet sich in `PROJECT.md`. Dauerhafte Architekturentscheidungen befinden sich in `DECISIONS.md`.

## Aktueller Dokumentstand

Der dokumentierte Release-Vorbereitungsstand ist Version `0.3.0` / Build `303`
für macOS auf Apple Silicon. Der Restore-Neustartfix ist committed; ein finaler
Clean-Build 303 steht noch aus. Ein DMG, Prüfsummenmanifest, Push, Tag, Appcast,
Pilotübergabe und öffentlicher Release sind damit **nicht** behauptet oder
ausgelöst. Der normale Produktpfad ist lokal, ohne Cloud und ohne KI-Funktion;
der committed Produktpfad ist eine frische verschlüsselte Final-V4-Installation
mit SQLCipher 4.17, verschlüsselten Managed Documents und `.jkmebackup`.
Ein neuer Paket- und Realwelt-Nachweis steht weiterhin aus. Ein späterer
macOS-Build ist ohne Developer-ID-Nachweis höchstens ad-hoc signiert und nicht
notarisiert; Windows ist nicht freigegeben.

Für die Bedienung gelten das
`docs/user_manual/USER_MANUAL_SOURCE.md` und das daraus erzeugte
`docs/user_manual/Jenaplan-Kompetenzmanager-0.3.0-Build-302-Benutzerhandbuch.pdf`.
Dieses vorhandene Build-302-PDF bleibt ein historisches Artefakt und wird nicht
als Build 303 umbenannt. Die Schutzgrenzen beschreibt
`docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md`.

## Projektziel

Ziel des Projekts ist der Aufbau einer modernen, ruhigen und wartbaren Desktop-App fuer paedagogische Kompetenzdokumentation.

PySide ist die Hauptanwendung. Python verantwortet Datenmodell, Application Layer, Domain Layer, Persistenz, ViewModels, Adapter, PySide-Oberflaeche, Berichte und Exporte. Fachliche Logik verbleibt vollstaendig ausserhalb von UI-Widgets.

Excel ist nicht mehr Hauptanwendung und kein Zielpfad fuer neue Features. Bestehende Workbook-/openpyxl-/VBA-Artefakte sind historisch archiviert und gehoeren nicht mehr zum aktiven App-Pfad.

Die Stammgruppenübersicht ist der Einstieg in den Arbeitsablauf. Sie dient ausschließlich dazu, Schüler schnell zu finden, auszuwählen und anschließend in das Schülerprofil zu wechseln. Verwaltung, Analyse und Auswertung erfolgen nicht in dieser Ansicht.

## Architektur

Das Projekt ist modular aufgebaut:

- `src/desktop_app/` enthaelt die PySide-Hauptanwendung.
- `src/core/` enthaelt fachliche Modelle, Application-/Domain-/Infrastructure-Bausteine und SQLite-Zugriff ueber Repositories.
- `legacy/excel/` enthaelt den archivierten Excel-/openpyxl-/VBA-Altstand.
- `data/` enthaelt strukturierte Eingabedaten und Konfigurationen.
- `docs/` enthaelt fachliche und technische Dokumentation.
- `tests/` ist fuer automatisierte Tests vorgesehen.
- `assets/` ist fuer statische Ressourcen vorgesehen.

Die Hauptanwendung laeuft ueber PySide und SQLite. Excel-Erzeugung ist kein aktiver Standardpfad und wird nur bei ausdruecklichem Legacy- oder Exportauftrag betrachtet.

Jede Ansicht besitzt genau eine Hauptaufgabe. Neue Funktionen dürfen diese Hauptaufgabe nicht verwässern.

Das Datenmodell ist die fachliche Grundlage des Projekts. Neue UI-Elemente duerfen das Datenmodell niemals umgehen; alle Ansichten sind Projektionen des Datenmodells.

Das freigegebene Design-System ist die visuelle Grundlage des Projekts. Neue Ansichten orientieren sich am Design der Stammgruppenübersicht.

## Entwicklungsprozess

Jede Implementierung folgt kuenftig dieser Reihenfolge:

1. Vision
2. Product Discovery
3. Produktentscheidung
4. Datenmodell-Review
5. Architektur-Review
6. UX-Review
7. Prompt-Review
8. Implementierung
9. Technical Review
10. Test
11. Commit

## Dokumentation

- `PROJECT.md` enthält die zentrale Projektdokumentation.
- `AGENTS.md` enthält die verbindlichen Projektregeln.
- `DECISIONS.md` enthält endgültige Architekturentscheidungen.
- `ROADMAP.md` enthält die Versionsplanung.
- `CHANGELOG.md` dokumentiert Änderungen pro Version.
- `docs/DESIGN_SYSTEM.md` dokumentiert die verbindliche Designreferenz.

## Voraussetzungen

- Python 3.11 oder neuer
- Installation der Abhaengigkeiten aus `requirements.txt`

```bash
pip install -r requirements.txt
```

## PySide-App starten

### Installiertes macOS-Paket

Ein späterer eigenständiger Apple-Silicon-Build wird als
`Jenaplan-Kompetenzmanager.app` und Drag-and-drop-DMG erzeugt. Er benötigt auf
dem Ziel-Mac weder Python noch Terminal, Repository oder Entwicklungsumgebung.
Installation, Gatekeeper und Datenpfad sind in
`docs/PILOT_INSTALLATION_MACOS.md` beschrieben; das technische Backup in
`docs/PILOT_BACKUP.md`. Die kurze Lehrkraftanleitung liegt unter
`docs/PILOT_INSTALLATION_LEHRKRAFT.md`, das Benutzerhandbuch unter
`docs/user_manual/USER_MANUAL_SOURCE.md`.

Reproduzierbarer Build auf einem Apple-Silicon-Mac:

```bash
scripts/build_macos_pilot.sh --data-mode empty
scripts/build_macos_pilot.sh --data-mode release
```

`empty` erzeugt die leere technische Smoke-Test-Variante mit eigenem Dateinamen.
`release` bleibt datenfrei. Synthetische Final-V4-Testdaten werden ausschließlich
in einer getrennten, neuen Testinstallation erzeugt; sie werden weder in das
Bundle aufgenommen noch als portables Backup ausgegeben. Der Build schreibt
seine Variante in `pilot_build_info.json` und übernimmt niemals einen lokalen
Runtime-Bestand aus dem Entwicklerarbeitsstand.

Zusätzlich erzeugt der Build die gebrandete Lehrkraft-Installationsanleitung und
das Benutzerhandbuch als PDF. Das DMG verwendet ein ruhiges Finder-Layout mit
App, Programme-Verknüpfung und Installationsanleitung.

Die App verwendet im installierten Betrieb ausschließlich:

```text
~/Library/Application Support/Jenaplan-Kompetenzmanager/
```

Der Entwicklerstart verwendet weiterhin den bisherigen Projektpfad unter `data/`.
Er ist kein Installationsweg für Lehrkräfte oder technische Betreuung.

### Entwicklerstart

Primaerer Start per Doppelklick auf macOS:

```text
launcher/Jenaplan_Kompetenzmanager.command
```

Start per Terminal:

```bash
python3 -m src.desktop_app.main
```

Der Launcher nutzt `.venv/bin/python`, wenn eine virtuelle Umgebung vorhanden ist,
und faellt sonst auf `python3` zurueck.

Hinweis: Der `.command`-Launcher bleibt ausschließlich der Entwicklerstart und
benötigt Python sowie die Projektabhängigkeiten. Für den Piloteinsatz dient das
eigenständige App-/DMG-Paket.

## Standardchecks

Der aktive Standardcheck prueft die PySide-/SQLite-Linie:

```bash
git diff --check
python3 -m pytest
QT_QPA_PLATFORM=offscreen python3 -c 'from src.desktop_app.main import main; print("import ok")'
```

Der alte Excel-Workbook-Build ist archiviert und kein Pflichtcheck mehr. `python3 build.py` gehoert nur noch zu ausdruecklichen Legacy-/Exportauftraegen innerhalb von `legacy/excel/`.

## Synthetische Testdaten für Entwicklung und Dokumentation

Eine ausdrücklich lokale Entwicklungsdatenbank kann mit künstlichen Testdaten
befüllt werden:

```bash
python3 scripts/seed_test_data.py
```

Das Script schreibt standardmaessig nach `data/kompetenzmanager.sqlite`. Wenn dort bereits Schueler, Beobachtungen, Dokumente oder Stundenplaneintraege liegen, bricht es ohne Aenderung ab.

Ein bewusst frisches Testsystem wird so erzeugt:

```bash
python3 scripts/seed_test_data.py --reset
```

`--reset` loescht die lokale Testdatenbank und die Demo-Dateien unter `data/documents/` kontrolliert neu. Es werden nur kuenstliche Namen und harmlose Platzhalterdateien erzeugt.

Die Testdaten bilden einen rund achtmonatigen Nutzungsstand von September bis
Juli ab. Sie enthalten 24 künstliche Kinder in vier Stammgruppen, drei Kurse,
drei Kursverbünde, 25 Unterrichtsstunden einer vollständigen Woche und
Kompetenzdokumentationen in allen aktiven Katalogfächern. Sie dürfen niemals
gegen einen vorhandenen fachlichen Bestand oder für eine Übergabe an Lehrkräfte
verwendet werden.

Pilottest-Checkliste:

- Stammgruppen, Kurse und Kursverbuende
- Dashboard und Stundenplan mit Stammgruppen-, Kurs- und Kursverbundzielen
- Fachabdeckung, alte, aktuelle und heute erfasste Dokumentationen
- Schuelerlisten-Sortierung nach Kurs und Name
- Einzel- und Multi-Fach-Beobachtungen
- Kompetenzvorschlaege, Verlauf und bestaetigte Staende
- Berichtsvorbereitung mit Staerken, Entwicklung, Unterstuetzungsbedarf und Belegen
- Dokumentationsstand und offene Kompetenzen
- Dokumente & Medien am Schueler und an Beobachtungen

## Excel/VBA Legacy

Der fruehere Workbook-/VBA-Pfad ist unter `legacy/excel/` archiviert. Er dient nur der historischen Nachvollziehbarkeit und ist kein aktiver Entwicklungs-, Test- oder Startpfad der Hauptanwendung.
