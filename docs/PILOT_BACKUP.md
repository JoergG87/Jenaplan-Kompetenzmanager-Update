# Datensicherung im lokalen macOS-Stand 0.3.0 / Build 303

Die App erstellt unter `Einstellungen > Datensicherung` ausschließlich ein
verschlüsseltes `.jkmebackup`. Der Container bindet die keyed Final-V4-
Fachdatenbank, den Dokument-Companion, verschlüsselte Managed Documents sowie
die notwendigen Keyset-/Envelope-Metadaten an dieselbe Installation.
Er enthält weder DMK, lokales Passwort, Recovery-Codes noch gespeicherte
Geräteanmeldung oder `app-preferences.json`.

## Backup erstellen und prüfen

1. `Einstellungen > Datensicherung` öffnen.
2. `Backup erstellen` wählen und einen Zielort festlegen.
3. Warten, bis die App das Backup vollständig erstellt und geprüft hat.
4. Die Bestätigung und den Speicherort kontrollieren.

> [!SICHERHEIT]
> `.jkmebackup` ist verschlüsselt und authentisiert. Bewahren Sie es trotzdem
> an einem schulisch freigegebenen, geschützten Ort auf.

## Backup prüfen

Über `Backup prüfen …` kann eine vorhandene `.jkmebackup`-Datei ohne Änderung
der laufenden Daten keyed verifiziert werden. Eine positive Prüfung bestätigt
Format, Integrität und Installationskontext, ersetzt aber keine organisatorische
Kontrolle des Speicherorts.

## Wiederherstellung

1. Unter `Wiederherstellen …` die gewünschte `.jkmebackup`-Datei auswählen.
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

Der same-installation Restore übernimmt keine Anmeldedaten. Security Store,
Geräteanmeldung, Anzeigename und Stand der geführten `Ersten Schritte` bleiben
zur Zielinstallation gehörig. Ein kompletter Umzug des Runtime-Ordners auf ein
anderes Gerät wird nicht unterstützt. DMK-Verlust und Gerätewechsel sind nicht
durch Passwort, Recovery-Code oder Backup gelöst.

> [!WARNUNG]
> Während Backup oder Restore darf die App nicht gewaltsam beendet werden. Beim
> Sperren wird eine offene Restore-Vorschau geschlossen; ein bereits gestarteter
> kritischer Vorgang wird sicher zu Ende geführt. ZIP-v1 ist im Cipher-Modus
> gesperrt. Vor Updates bleibt ein geprüftes zusätzliches Backup sinnvoll; für
> einen Gerätewechsel ist damit noch kein Recoverypfad freigegeben.
