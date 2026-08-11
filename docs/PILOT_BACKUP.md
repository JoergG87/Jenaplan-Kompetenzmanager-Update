# Datensicherung für den geplanten Pilotstand 0.4.0 / Build 400

Version 0.4.0 / Build 400 ist vorbereitet, aber noch nicht als Pilot-GO,
Verteilung oder Release freigegeben.

Die App erstellt unter `Einstellungen > Datensicherung` ausschließlich ein
verschlüsseltes `.jkmebackup`. Es umfasst die verschlüsselte Fachdatenbank,
die registrierten verwalteten Dokumente und die notwendigen Metadaten für eine
Wiederherstellung in derselben Installation. Es enthält weder den geschützten
Installationsschlüssel noch lokales Passwort, Recovery-Codes, Touch-ID- oder
gespeicherte Geräteanmeldedaten.

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
der laufenden Daten vollständig geprüft werden. Eine positive Prüfung bestätigt
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

Die Abbildung stammt aus dem bisherigen synthetischen Referenzstand und muss
vor einer 0.4.0-Pilotübergabe aktualisiert werden.

> [!KONTROLLE]
> Die App erstellt vor dem Wechsel ein Sicherheitsbackup, übergibt den Vorgang
> an einen separaten Restore-Worker, beendet sich vollständig und startet
> kontrolliert neu. Danach erneut anmelden und Schüler, Beobachtungen, Dokumente
> sowie Berichts- und LEG-Daten prüfen. Startet der Worker nicht, bleibt der
> bisherige aktive Bestand unverändert.

Der installationsgebundene Restore übernimmt keine Anmeldedaten. Security
Store, Geräteanmeldung, Anzeigename und Stand der geführten `Ersten Schritte`
bleiben zur Zielinstallation gehörig. Ein kompletter Umzug des Datenordners auf
ein anderes Gerät wird nicht unterstützt. Der Verlust des
Installationsschlüssels und ein Gerätewechsel sind nicht durch Passwort,
Recovery-Code oder Backup gelöst.

> [!WARNUNG]
> Während Backup oder Restore darf die App nicht gewaltsam beendet werden. Beim
> Sperren wird eine offene Restore-Vorschau geschlossen; ein bereits gestarteter
> kritischer Vorgang wird sicher zu Ende geführt. Alte ZIP-Backups sind im
> verschlüsselten Produktpfad gesperrt. Vor Updates bleibt ein geprüftes
> zusätzliches Backup sinnvoll; für einen Gerätewechsel ist damit noch kein
> Recoverypfad freigegeben.
