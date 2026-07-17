# Jenaplan-Kompetenzmanager 0.2.0 – Pilot-Release-Kandidat

Version 0.2.0 bündelt den aktuellen technisch geprüften Stand der lokalen
PySide-Anwendung für den vereinbarten Pilottest. Alle Arbeitsdaten bleiben auf
dem verwendeten Mac; eine Cloudübertragung findet nicht statt.

## Sicherheit und Wiederherstellung

- Genau ein lokales Lehrkraftkonto je Installation mit Argon2id-geschütztem
  Passwort, Recovery-Codes und Fehlversuchsdrosselung.
- Sichere Startreihenfolge, flüchtige Sitzung sowie manuelle, Inaktivitäts- und
  Wake-Sperre.
- Auf unterstützten Macs ausdrücklich aktivierbare gespeicherte
  Geräteanmeldung und optionale Touch-ID-Entsperrung. Das App-Passwort wird
  nicht im Schlüsselbund gespeichert und bleibt immer als Fallback verfügbar.
- Technisch implementierter signierter Support-Reset mit verpflichtendem,
  verifiziertem Sicherheitsbackup und neuem Passwort beim Folgestart.

Der produktive Support-Reset ist in diesem Build noch nicht freigeschaltet,
weil kein freigegebener öffentlicher Produktivschlüssel eingebunden ist. Die
produktive Schlüsselregistry bleibt leer.

## Betrieb und Orientierung

- Backup erstellen und prüfen, Restore-Vorschau und bewusst bestätigter Restore.
- Geführte `Erste Schritte`, optionaler Anzeigename und persönliche
  Dashboard-Begrüßung.
- Sicherheitseinstellungen für Sperrintervall, Passwort, Recovery-Codes,
  gespeicherte Anmeldung, Touch ID und manuelles Sperren.
- Arbeitsfenster für Beobachtung, Bericht und LEG öffnen maximiert auf der
  verfügbaren Bildschirmfläche. Lange Bestätigungsaktionen bleiben vollständig
  lesbar; beim LEG-Seitenwechsel bleibt genau eine Phase sichtbar.

## Wichtige Grenzen

Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen. Lokale
Administratoren können grundsätzlich auf lokale Dateien zugreifen.

Der Kandidat ist ad hoc signiert und nicht notarisiert. Die reale Abnahme von
Sleep/Wake, physischer Touch-ID-Systemaufforderung und Fingerabdruck,
App-Switcher sowie der vollständigen Aktivierungs- und Widerrufsreise bleibt
offen. Developer-ID-Signierung, Apple-Notarisierung und produktiver
Support-Reset bleiben ebenfalls offen.

Es wurden keine neue fachliche Funktion, keine Datenverschlüsselung, kein
privater oder Testschlüssel und keine echten Schüler- oder Pilotdaten in den
Release-Kandidaten aufgenommen.
