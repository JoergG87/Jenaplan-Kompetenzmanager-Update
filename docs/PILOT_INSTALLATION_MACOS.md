# macOS-Installation und Buildvorbereitung 0.3.0 / Build 303

## Status

Diese Unterlage beschreibt den macOS-arm64-Vorbereitungsstand vor einem
kontrollierten GitHub-Pre-Release/Pilot. Clean-Build, DMG,
Prüfsummenmanifest und Signaturnachweis werden vor einer Übergabe als
Releaseartefakte nachgewiesen. Builds 300 bis 302 sind nicht verteilte
historische Vorstände; Build 303 ist noch kein Release Candidate.

| Punkt | Vorgabe |
|---|---|
| Produkt | Jenaplan-Kompetenzmanager 0.3.0 / Build 303 |
| Architektur | Apple Silicon (arm64) |
| Mindestplattform | macOS 13 |
| Übergabeform | GitHub-Pre-Release/Pilot mit Drag-and-drop-DMG |
| Signatur | ad-hoc signiert, nicht notarisiert |
| Datenmodus für eine Übergabe | `release`, ohne Schüler-, Pilot- oder Runtime-Daten |
| Freigabe | kein Windows, kein Stable-Release, kein Stable-Appcast |

## Erwarteter Installationsweg

Nach einer freigegebenen Übergabe wird das DMG im Finder geöffnet,
`Jenaplan-Kompetenzmanager.app` nach `Programme` gezogen, das DMG ausgeworfen
und die App regulär aus `Programme` gestartet. Bei Gatekeeper-Hinweis gilt nur
der kontrollierte Weg über Control-Klick `Öffnen` beziehungsweise
`Datenschutz & Sicherheit > Dennoch öffnen`. Gatekeeper wird niemals global
deaktiviert.

Die App benötigt auf dem Ziel-Mac weder Python, Terminal, Repository noch
Entwicklungsumgebung. Version und Build werden über `Über die App` geprüft.

## Lokale Daten und Sicherheit

Veränderliche Daten liegen getrennt vom App-Bundle in einem lokalen,
verwalteten App-Bereich. Dieser enthält die fachliche SQLite-Datenbank,
verwaltete Dokumente, erzeugte Ausgaben, lokale Backups, Einstellungen und
Security-Store. Absolute Entwicklerpfade gehören nicht in Übergabeunterlagen.

Der normale Produktpfad verwendet lokale SQLite-Daten, verwaltete Klartext-
Dokumente/PDFs sowie ZIP-v1-Backup und Restore. Ein Restore prüft die
Sicherung, zeigt eine Vorschau, verlangt Bestätigung, startet einen separaten
Worker und beendet die App vor dem kontrollierten Neustart vollständig.

Die App-Sperre, Keychain und optionales Touch ID schützen den Zugang zur App;
sie sind keine Behauptung einer aktiven Verschlüsselung der Fachdaten,
Dokumente oder ZIP-v1-Backups. Die Details stehen in
`SICHERHEIT_UND_VERSCHLUESSELUNG.md`.

## Reproduzierbarer späterer Build

Ein späterer Build läuft ausschließlich auf Apple Silicon und liest Version und
Build zentral aus `src/version.py`:

```bash
scripts/build_macos_pilot.sh --data-mode empty
scripts/build_macos_pilot.sh --data-mode release
```

`empty` ist nur ein technischer Smoke-Test ohne Fachdaten. `release` darf
keine SQLite-Datei, Dokumente, Backups, Schlüssel oder reale Nutzerdaten in das
Bundle übernehmen. Die optionale Variante `laura` ist eine streng synthetische
Entwicklungs-/Testvariante und kein Übergabeweg.

Der Build muss ein isoliertes Venv nutzen, Paketabhängigkeiten prüfen und
Bundle, Architektur, sichtbare Version/Build, Datenfreiheit, Lizenzhinweise,
Signatur, DMG-Inhalt sowie die vorgesehenen Paket-Smokes belegen. Der
Dokumentgenerator erhält Version und Build; der Artefakt-Commit darf erst nach
dem Clean-Build in erzeugten Unterlagen erscheinen.

## Nicht Teil dieses Dokuments

- keine Appcast-Aktualisierung oder automatische Updatefreigabe;
- keine Developer ID, Notarisierung oder Stapling;
- keine Produktmigration oder Verschlüsselungsaktivierung;
- keine Windows-/DPAPI-Abnahme;
- keine reale Touch-ID-, Sleep/Wake- oder Power-Loss-Abnahme;
- keine Testdaten, Pilotdatenbanken oder persönlichen Daten im Bundle.

Die Lehrkraftanleitung, der Schnellstart, das Benutzerhandbuch und die
Backup-Anleitung werden aus ihren wartbaren Quellen erzeugt. Erst nach allen
Build- und Realweltgates darf ein Artefakt, eine Prüfsumme oder ein
Produkt-Commit als Nachweis ergänzt werden.
