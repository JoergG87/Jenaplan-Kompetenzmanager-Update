# Technisches Backup für den macOS-Pilottest

Das Backup-Skript sichert die lokale SQLite-Datenbank und alle von der App
verwalteten Dokumente. Es führt keine automatische Wiederherstellung durch.

## Backup erstellen

1. Den Jenaplan-Kompetenzmanager vollständig schließen.
2. Das getrennt mitgelieferte, versionierte Backup-Skript in einen gut
   auffindbaren Ordner kopieren. Es liegt neben dem DMG und bewusst nicht im
   aufgeräumten Installationsfenster.
3. Ein Terminal öffnen und das Skript ausführen:

```bash
bash /Pfad/zu/Jenaplan-Kompetenzmanager-Pilot-{{PILOT_VERSION}}-Backup.sh
```

Das Skript bricht ab, wenn die App noch läuft. Es verwendet die sichere
SQLite-Backup-Funktion, kopiert `documents/` und legt eine neue, nicht
überschriebene Sicherung mit Zeitstempel an:

```text
~/Library/Application Support/Jenaplan-Kompetenzmanager/backups/YYYYMMDD-HHMMSS/
├── kompetenzmanager.sqlite
├── documents/
└── BACKUP_INFO.txt
```

Der abschließend ausgegebene Pfad ist die vollständige Sicherung. Für Schutz vor
einem Defekt des Macs sollte dieser gesamte Ordner zusätzlich auf einen
verschlüsselten externen Datenträger kopiert werden.

## Technische Wiederherstellung

Es gibt bewusst keine automatische Restore-Funktion. Eine Wiederherstellung ist
ein kontrollierter technischer Eingriff:

1. App schließen und prüfen, dass sie nicht mehr läuft.
2. Vom aktuellen Datenordner zunächst eine zusätzliche Sicherung anlegen.
3. Den gewünschten Backup-Ordner vollständig prüfen; Datenbank und `documents/`
   gehören zusammen.
4. Die aktuelle `kompetenzmanager.sqlite` und `documents/` nicht löschen, sondern
   zunächst in einen eindeutig datierten Sicherheitsordner verschieben.
5. Datenbank und `documents/` aus genau derselben Sicherung in den App-Datenordner
   kopieren.
6. App starten und Schüler, Dokumente sowie letzte fachliche Änderungen prüfen.

Bei Unsicherheit keine Dateien ersetzen. Das Backup-Skript selbst verändert
keine aktuellen Nutzerdaten.
