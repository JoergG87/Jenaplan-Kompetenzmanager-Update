# Erste Schritte - Jenaplan-Kompetenzmanager

## Dein erster Test

Diese kompakte Orientierung ergänzt das Benutzerhandbuch.

Das Pilotpaket liegt in zwei klar getrennten Varianten vor:

- `Leer` für Erststart, Kontoerstellung, Recovery-Codes, Onboarding, Login,
  gespeicherte Anmeldung, Touch ID, Stammdaten, Backup/Restore und Leerzustände.
- `Laura-Testdaten` für den fachlichen Pilottest mit einem vorbereiteten,
  ausschließlich synthetischen Acht-Monats-Datenbestand.

Beide Varianten verwenden exakt dasselbe leere DMG. In der
Laura-Testdatenvariante wird zuerst das lokale Konto eingerichtet. Danach wird
`Laura-Testdaten-{{PILOT_VERSION}}.jkmbackup` unter
`Einstellungen > Datensicherung` über den normalen Restore-Weg ausgewählt,
geprüft und bewusst wiederhergestellt. Das Backup enthält keine Kontodaten,
Passwörter, Recovery-Codes, Gerätecredentials, Security Stores, Support-Tokens
oder Schlüssel.

1. Starte die App aus dem Ordner `Programme`.
2. Lege beim ersten Start das lokale Konto mit einem sicheren Passwort an.
3. Sichere alle einmalig angezeigten Recovery-Codes.
4. Lege auf Wunsch einen Anzeigenamen für die Begrüßung fest.
5. Nutze die geführten `Ersten Schritte` oder öffne sie später erneut unter
   `Einstellungen`.
6. Prüfe die dokumentationsrelevanten Fächer.
7. Prüfe den Stundenplan.
8. Prüfe Stammgruppen, Kurse und Kinder. In einer leeren Installation müssen
   zuerst mindestens eine Stammgruppe und ein Kurs angelegt werden.
9. Erfasse eine erste Beobachtung und öffne sie anschließend erneut.
10. Erstelle unter `Einstellungen > Datensicherung` ein Backup und lasse es
    durch die App prüfen.

`Erste Schritte` legt keine Beispiel-, Pilot- oder Demodaten an.

Blaue Primäraktionen helfen bei der Orientierung. Beobachtung, Bericht und LEG
sind zusätzlich durch unterschiedliche ruhige Arbeitsbereichsfarben erkennbar;
maßgeblich bleiben immer Überschrift und Beschriftung. Kurs- und
Bewertungsfarben behalten ihre eigene Bedeutung.

<!-- pagebreak -->

## Sicherheit im Alltag

- Die App sperrt sich weiterhin nach dem gewählten Inaktivitätsintervall und
  nach dem Ruhezustand. `Nie sperren` wird nicht angeboten.
- Auf einem unterstützten Mac kann Touch ID nach einer Passwortanmeldung
  optional aktiviert werden. Das Passwort bleibt immer verfügbar.
- `Auf diesem Gerät angemeldet bleiben` ersetzt nur die erneute
  Passworteingabe beim normalen Start; die automatische Sperre bleibt aktiv.
- Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
  FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen.
- Wenn weder Passwort noch Recovery-Codes verfügbar sind, zeigt die App eine
  technische Support-Reset-Anfrage. Der produktive Reset ist ohne freigegebenen
  öffentlichen Schlüssel in Version {{PILOT_VERSION}} noch nicht freigeschaltet.

Für Rückmeldungen die mitgelieferte Test-Excel verwenden und nur künstliche
Testdaten einsetzen.
