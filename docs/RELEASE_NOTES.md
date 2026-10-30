# Jenaplan-Kompetenzmanager – V7-Pilotupdate

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

## Neu in diesem Update

- A-/B-Wochen mit bewusst gesetzten manuellen Ausnahmen für einzelne Wochen.
- Globale Unterrichtszeiten als Vorlagen; individuell gespeicherte Stundenzeiten bleiben erhalten.
- Stammgruppenstunden auch ohne Unterrichtsfach.
- Kombinierte Unterrichtsfächer in einer Stunde; Beobachtungen verlangen eine eindeutige Fachwahl.
- Fachpflanzen zeigen den vorhandenen Kompetenzstand im Schülerprofil.
- Verbesserte Kalender und Eingabefelder sowie eine übersichtlichere Kompetenzansicht.
- Deutlich schnellere Wochenumschaltung und weitere Darstellungs- und Stabilitätskorrekturen.
- Die Beobachtungssituation „Sitzkreis“ ergänzt die bestehende Auswahl.

## Bewusste Umstellung von Build 404

Das Ersetzen des App-Bundles führt keine automatische Datenmigration aus. Eine vorhandene Final-V4-Installation bleibt beim gewöhnlichen Start V4. V7 wird ausschließlich über den ausdrücklich gestarteten Wartungsweg aktiviert, nachdem die App vollständig beendet wurde:

`/Applications/Jenaplan-Kompetenzmanager.app/Contents/MacOS/Jenaplan-Kompetenzmanager --migrate-v4-to-v7 --runtime-root "<bestehender kanonischer Datenroot>"`

Dieser Wartungsweg prüft vorhandene Installation, Schlüssel und exaktes Quellschema, erstellt ein verschlüsseltes Vollbackup, verifiziert es unabhängig und führt die bestehende transaktionale V4→V7-Migration aus. Danach prüft ein neuer Prozess den vollständigen Bestand und startet die App erneut. Die Anmeldung verwendet das bestehende Passwort. Daten und Schlüssel werden nicht neu angelegt oder rotiert.

Die Wartung sollte mit Unterstützung der Pilotbetreuung ausgeführt werden. Platzhalter im Befehl müssen durch den tatsächlichen bestehenden Datenroot ersetzt werden. Keine Test-/Seed-/Resetbefehle für einen Produktbestand verwenden.

## Backup, Wiederherstellung und Fehlerfall

- Produktdatenbank und Dokumente bleiben lokal verschlüsselt: SQLCipher 4.17.0, SQLite 3.53.3, CommonCrypto. Standard-SQLite ist kein Fallback.
- V7 verwendet sein eigenes geprüftes verschlüsseltes `.jkmebackup` im vorhandenen Installations- und Schlüsselkontext. Restore erfolgt mit Safety-Backup, separatem Worker und kontrolliertem Neustart.
- Bei einem Wartungsfehler hält die App kontrolliert an. Vorhandenen Bestand, Fehlermeldung und Quellbackup erhalten und die Pilotbetreuung hinzuziehen. Kein Löschen von Wartungsbelegen, keine Schlüsselneuanlage und kein Austausch einzelner Datenbankdateien.
- Nach einer bereits erfolgreich committeten, aber noch nicht abgeschlossenen Migration ist die gesonderte erneute Abschlussprüfung `--complete-v7-migration` möglich; sie ist kein automatisches Fortsetzen und prüft den vollständigen Zielbestand erneut.
- Eine Rückkehr zu Build 404 erfordert die vollständige geprüfte V4-Sicherung im ursprünglichen Schlüsselkontext. Build 404 darf V7 nicht öffnen. Alle Änderungen nach dem V4-Sicherungszeitpunkt gingen bei dieser Rückkehr verloren; kein automatischer Downgrade.

## Pilotkanal und Installation

Dieses Update bleibt im bestehenden macOS-arm64-Pilotkanal ab macOS 13. Stable ist deaktiviert. Der vorhandene Pilotweg verwendet eine Ad-hoc-Codesignatur sowie signierte Sparkle-Artefakte und einen signierten Feed. Eine Developer-ID-Signatur, Notarisierung oder Gatekeeper-Freigabe wird damit nicht behauptet. Die manuelle Erstinstallation kann weiterhin die dokumentierte macOS-Freigabe erfordern.

Eine Neuinstallation beginnt weiterhin mit einem leeren Final-V4-Bestand, Schuljahr 2026/27 und dem offiziellen Katalog mit 331 Kompetenzen. Auch hier erfolgt die V7-Aktivierung bewusst über den Wartungsweg. Es werden keine Beispielkinder oder Testdaten angelegt.
