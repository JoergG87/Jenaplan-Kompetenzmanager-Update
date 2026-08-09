# Erste Schritte - Jenaplan-Kompetenzmanager

## Ruhig in der lokalen App ankommen

Diese Orientierung ergänzt das Benutzerhandbuch für Version
{{PILOT_VERSION}} / Build {{PILOT_BUILD}}. Sie legt keine Kinder,
Beobachtungen, Testdaten oder Backups automatisch an.

1. Die App aus dem Ordner `Programme` starten.
2. Beim ersten Start das lokale Passwort anlegen und Recovery-Codes getrennt
   sichern.
3. Die App mit dem Passwort entsperren.
4. Optional unter `Einstellungen > Sicherheit` Anzeigename, Sperrzeit,
   gespeicherte Geräteanmeldung und – bei erfüllten Voraussetzungen – Touch ID
   prüfen.
5. Unter `Stammdaten` mindestens eine Stammgruppe und einen Kurs anlegen.
6. Schüler anlegen und gegebenenfalls Kursverbünde pflegen.
7. Den Stundenplan unter `Einstellungen > Stundenplan` prüfen oder ergänzen.
8. Eine erste Beobachtung erfassen und die Rückmeldung zum Speichern abwarten.
9. Schülerprofil und Kompetenz-Cockpit öffnen; fehlende Dokumentation ist keine
   negative Bewertung.
10. Unter `Einstellungen > Datensicherung` ein lokales Backup erstellen und
    prüfen.

## Sicherheit im Alltag

> [!SICHERHEIT]
> - Die App sperrt nach der gewählten Inaktivitätszeit und nach dem Ruhezustand.
> - Touch ID ist optional; das Passwort bleibt der Fallback.
> - App-Sperre und Verschlüsselung sind getrennte Schutzschichten. Final-V4-
>   Datenbank, verwaltete Dokumente und `.jkmebackup` werden separat verschlüsselt;
>   ein geschütztes macOS-Benutzerkonto und FileVault bleiben erforderlich.
> - Support-Reset ist im Cipher-Modus kontrolliert blockiert.
> - `.jkmebackup` ist installationsgebunden. DMK-Verlust oder Gerätewechsel sind
>   damit nicht gelöst.
> - Ein späterer interner Build ist ohne abweichenden Artefaktnachweis höchstens
>   ad-hoc signiert und nicht notarisiert; es gibt
>   keine automatische Update- oder Appcast-Aktion.

Für den vollständigen Ablauf zu Bericht, LEG, Restore und Sicherheit das
Benutzerhandbuch verwenden.
