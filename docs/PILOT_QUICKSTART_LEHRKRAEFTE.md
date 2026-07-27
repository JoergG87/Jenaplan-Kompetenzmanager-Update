# Schnellstart für Lehrkräfte

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

1. DMG öffnen, die App nach `Programme` ziehen und von dort starten.
2. Beim ersten Start Passwort festlegen, bestätigen und Recovery-Codes sicher
   aufbewahren.
3. Mit Passwort anmelden; gespeicherte Anmeldung oder Touch ID nur optional
   aktivieren. Das Passwort bleibt verfügbar.
4. Unter `Stammdaten` Stammgruppen, Kurse und bei Bedarf Kursverbünde pflegen.
5. Schüler anlegen oder ein Schülerprofil öffnen.
6. Dashboard und Stundenplan für den Unterrichtstag prüfen.
7. Beobachtung erfassen, Kontext und Kompetenzen prüfen und bewusst speichern.
8. Kompetenz-Cockpit und Bestätigungsstände im Schülerprofil nutzen.
9. Für Bericht oder LEG vorhandenen Entwurf öffnen oder bewusst einen neuen
   eigenständigen Entwurf beginnen. Abbrechen erzeugt keine Daten.
10. Unter `Einstellungen > Datensicherung` ein geprüftes lokales Backup
    erstellen.

## Wichtige Grenzen

- Die App arbeitet lokal, ohne Cloud und ohne KI.
- Die App-Sperre ersetzt keine Fachdatenverschlüsselung.
- Backup und Restore verwenden im Produktpfad ZIP-v1; Restore wird erst nach
  Vorschau und ausdrücklicher Bestätigung über einen separaten Worker gestartet.
- Finale oder frei exportierte PDFs liegen außerhalb der App als Dateien vor
  und müssen sicher weitergegeben werden.
- Der interne macOS-Build ist ad-hoc signiert und nicht notarisiert. Es gibt
  keine Windows-Freigabe, keinen Stable-Appcast und keine automatische
  Updateinstallation.

Weitere Hinweise stehen im Benutzerhandbuch und in
`SICHERHEIT_UND_VERSCHLUESSELUNG.md`.
