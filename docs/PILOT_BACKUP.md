# Backup und Wiederherstellung

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

> [!HINWEIS]
> Inhaltlich finaler Reviewstand vor der Versionsanhebung; noch kein finales
> Pilot- oder Releaseartefakt.

Die App erstellt unter `Einstellungen > Datensicherung` ausschließlich ein
verschlüsseltes `.jkmebackup`. Es umfasst die verschlüsselte Final-V4-
Fachdatenbank, die registrierten verschlüsselten Managed Documents und die
notwendigen Metadaten für eine Wiederherstellung in der ursprünglichen
geschützten Installation. App-Passwort, Recovery-Codes, Touch-ID- und
Geräteanmeldedaten sowie der lokale Datenschlüssel sind nicht enthalten.

## Backup erstellen und prüfen

1. `Einstellungen > Datensicherung` öffnen.
2. `Backup erstellen` wählen und einen schulisch freigegebenen Zielort
   festlegen.
3. Warten, bis die App das Backup vollständig erstellt und geprüft hat.
4. Bestätigung und Speicherort kontrollieren.

Mit `Backup prüfen ...` lässt sich eine vorhandene `.jkmebackup`-Datei ohne
Änderung der laufenden Daten prüfen.

> [!SICHERHEIT]
> `.jkmebackup` ist verschlüsselt und authentisiert. Bewahren Sie es trotzdem
> an einem schulisch freigegebenen, geschützten Ort auf. Recovery-Codes werden
> getrennt und außerhalb des Macs aufbewahrt.

## Wiederherstellung

1. `Wiederherstellen ...` wählen und die gewünschte `.jkmebackup`-Datei
   auswählen.
2. Die Vorschau mit Version, Kompatibilität und zusammengefassten Anzahlen
   prüfen.
3. Den Restore bewusst bestätigen.
4. Den Vorgang bis zur vollständigen App-Beendigung und zum kontrollierten
   Neustart laufen lassen.

![Restore-Vorschau](user_manual/screenshots/21_restore_vorschau.png)

Die App prüft das Backup vollständig in einem getrennten Staging-Bereich und
erstellt vor dem Austausch ein verschlüsseltes Safety-Backup. Ein separater
Worker übernimmt den kontrollierten Austausch. Danach die App erneut öffnen
beziehungsweise den kontrollierten Neustart abwarten, neu anmelden und Schüler,
Beobachtungen, Dokumente sowie Berichts- und LEG-Daten prüfen. Kann der Worker
nicht sicher starten, bleibt der aktive Bestand unverändert.

## Bindung und Recoverygrenze

Der Restore ist an die ursprüngliche geschützte Installation und deren
vorhandenen lokalen Schlüsselkontext gebunden. Das Backup ist nicht beliebig
auf jedem Mac wiederherstellbar, kein Cloud-Backup und kein allgemeiner
Gerätewechselweg.

Recovery-Codes sind der normale erste Weg bei verlorenem Passwort. Ein
betreuter Support-Reset kann nur auf der intakten ursprünglichen Installation
erfolgen, wenn der lokale Schlüssel verfügbar, Final V4 vollständig prüfbar
und ein neues Safety-`.jkmebackup` erfolgreich erstellt und verifiziert werden
kann. Er setzt ausschließlich Authentifizierungs- und Recoveryzustände zurück,
nicht Fachdaten oder Datenschlüssel. Bei verlorenem lokalem Schlüssel kann
Support die Daten nicht wiederherstellen.

> [!WARNUNG]
> Backup oder Restore nicht gewaltsam unterbrechen. Produktive Final-V4-
> Bestände niemals mit alten Klartext- oder historischen Backupwerkzeugen
> öffnen.
