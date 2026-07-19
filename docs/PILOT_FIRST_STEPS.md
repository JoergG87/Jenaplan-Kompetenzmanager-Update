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
`Laura-Testdaten-0.2.1.jkmbackup` unter
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
6. Prüfe zunächst die leere Anwendung. In der Pilotversion erscheint danach
   der Schritt `Pilottest mit Beispieldaten fortsetzen`.
7. Wähle dort `Testdaten jetzt einspielen` oder öffne später
   `Einstellungen > Datensicherung`. Die App öffnet nur den bestehenden
   Restore-Weg: Du wählst die beiliegende `.jkmbackup`-Datei selbst, prüfst die
   Vorschau und bestätigst die Wiederherstellung bewusst.
8. Prüfe die dokumentationsrelevanten Fächer.
9. Prüfe den Stundenplan.
10. Prüfe Stammgruppen, Kurse und Kinder. In einer leeren Installation müssen
   zuerst mindestens eine Stammgruppe und ein Kurs angelegt werden.
11. Erfasse eine erste Beobachtung und öffne sie anschließend erneut.
12. Erstelle unter `Einstellungen > Datensicherung` ein Backup und lasse es
    durch die App prüfen.

`Erste Schritte` legt keine Beispiel-, Pilot- oder Demodaten an und sucht keine
Backupdatei automatisch.

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
  technische Support-Reset-Anfrage. Ab Version `0.2.2` ist der betreute
  Ausnahmeweg nach Kontakt mit dem Support freigeschaltet. Die Anfrage enthält
  keine Schülerdaten; das neue Passwort setzt die Lehrkraft selbst.
- Recovery-Code bleibt der bevorzugte erste Wiederherstellungsweg. Nach einem
  Support-Reset müssen gespeicherte Anmeldung und Touch ID erneut eingerichtet
  werden.
- Unter `Einstellungen > Updates` wird ausschließlich auf bewusste Aktion im
  festen Pilotkanal geprüft. `0.2.1` ist die Ausgangsversion; `0.2.2` / Build
  `202` ist das erste beaufsichtigte Update. Es ersetzt ausschließlich das
  App-Bundle und keine fachlichen Daten oder Kontodaten.

Für Rückmeldungen die mitgelieferte Test-Excel verwenden und nur künstliche
Testdaten einsetzen.
