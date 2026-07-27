# Datensicherung im lokalen macOS-Stand 0.3.0 / Build 302

Die App erstellt unter `Einstellungen > Datensicherung` ein fachliches
ZIP-v1-Backup mit SQLite-sicherer Datenbankkopie und den von der App
verwalteten Dokumenten.
Das Backup enthält weder das lokale Passwort noch Recovery-Codes, Security
Store, gespeicherte Geräteanmeldung oder `app-preferences.json`.

## Backup erstellen und prüfen

1. `Einstellungen > Datensicherung` öffnen.
2. `Backup erstellen` wählen und einen Zielort festlegen.
3. Warten, bis die App das Backup vollständig erstellt und geprüft hat.
4. Die Bestätigung und den Speicherort kontrollieren.

> [!SICHERHEIT]
> Ein Backup ist keine Verschlüsselung. Bewahren Sie es an einem schulisch
> freigegebenen, geschützten Ort auf; FileVault beziehungsweise ein
> verschlüsselter Datenträger wird empfohlen.

## Backup prüfen

Über `Backup prüfen …` kann eine vorhandene `.jkmbackup`-Datei ohne Änderung der
laufenden Daten verifiziert werden. Eine positive Prüfung bestätigt Format und
Integrität, ersetzt aber keine organisatorische Kontrolle des Speicherorts.

## Wiederherstellung

1. Unter `Wiederherstellen …` die gewünschte `.jkmbackup`-Datei auswählen.
2. Die datensparsame Vorschau mit Version, Kompatibilität und zusammengefassten
   Anzahlen lesen.
3. Den Restore nur nach bewusster Prüfung bestätigen.
4. `Wiederherstellung starten` ausdrücklich bestätigen und den Vorgang
   vollständig ausführen lassen.

![Restore-Vorschau](user_manual/screenshots/21_restore_vorschau.png)

> [!KONTROLLE]
> Die App erstellt vor dem Wechsel ein Sicherheitsbackup, übergibt den Vorgang
> an einen separaten Restore-Worker, beendet sich vollständig und startet
> kontrolliert neu. Danach erneut anmelden und Schüler, Beobachtungen, Dokumente
> sowie Berichts- und LEG-Daten prüfen. Startet der Worker nicht, bleibt der
> bisherige aktive Bestand unverändert.

Der fachliche Restore übernimmt keine Anmeldedaten. Security Store,
Geräteanmeldung, Anzeigename und Stand der geführten `Ersten Schritte` bleiben
zur Zielinstallation gehörig. Ein kompletter Umzug des Runtime-Ordners auf ein
anderes Gerät wird nicht unterstützt.

> [!WARNUNG]
> Während Backup oder Restore darf die App nicht gewaltsam beendet werden. Beim
> Sperren wird eine offene Restore-Vorschau geschlossen; ein bereits gestarteter
> kritischer Vorgang wird sicher zu Ende geführt. Ein ZIP-v1-Backup ist nicht
> verschlüsselt; ein zusätzliches externes Backup bleibt vor Updates und
> Gerätewechseln sinnvoll.
