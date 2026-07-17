# Datensicherung im macOS-Pilottest

Die App erstellt unter `Einstellungen > Datensicherung` ein fachliches Backup
mit SQLite-sicherer Datenbankkopie und den von der App verwalteten Dokumenten.
Das Backup enthält weder das lokale Passwort noch Recovery-Codes, Security
Store, gespeicherte Geräteanmeldung oder `app-preferences.json`.

## Backup erstellen und prüfen

1. `Einstellungen > Datensicherung` öffnen.
2. `Backup erstellen` wählen und einen Zielort festlegen.
3. Warten, bis die App das Backup vollständig erstellt und geprüft hat.
4. Die Bestätigung und den Speicherort kontrollieren.

Ein Backup ist keine Verschlüsselung. Bewahren Sie es an einem schulisch
freigegebenen, geschützten Ort auf; FileVault beziehungsweise ein
verschlüsselter Datenträger wird empfohlen.

## Backup prüfen

Über `Backup prüfen` kann eine vorhandene `.jkmbackup`-Datei ohne Änderung der
laufenden Daten verifiziert werden. Eine positive Prüfung bestätigt Format und
Integrität, ersetzt aber keine organisatorische Kontrolle des Speicherorts.

## Wiederherstellung

1. Unter `Wiederherstellen` die gewünschte `.jkmbackup`-Datei auswählen.
2. Die datensparsame Vorschau mit Version, Kompatibilität und zusammengefassten
   Anzahlen lesen.
3. Den Restore nur nach bewusster Prüfung bestätigen.
4. Den nicht abbrechbaren Vorgang vollständig ausführen lassen.

Der fachliche Restore übernimmt keine Anmeldedaten. Security Store,
Geräteanmeldung, Anzeigename und Stand der geführten `Ersten Schritte` bleiben
zur Zielinstallation gehörig. Ein kompletter Umzug des Runtime-Ordners auf ein
anderes Gerät wird nicht unterstützt.

Während Backup oder Restore darf die App nicht beendet werden. Beim Sperren
wird eine offene Restore-Vorschau geschlossen; ein bereits gestarteter
kritischer Vorgang wird sicher zu Ende geführt.
