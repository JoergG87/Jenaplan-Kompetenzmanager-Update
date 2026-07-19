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

- Zwei klar getrennte Pilotvarianten: eine leere Variante für Erststart,
  Konto, Onboarding und Leerzustände sowie eine Laura-Testdatenvariante für den
  fachlichen Pilottest.
- Beide Varianten installieren exakt dasselbe leere App-/DMG-Artefakt. Die
  Laura-Variante enthält zusätzlich ein ausdrücklich synthetisches
  `Laura-Testdaten-0.2.0.jkmbackup`, das erst nach lokaler Kontoerstellung über
  `Einstellungen > Datensicherung` wiederhergestellt wird.
- Das Testdatenbackup enthält keine Passwörter, Recovery-Codes,
  Gerätecredentials, Security Stores, Support-Tokens oder Schlüssel.
- Backup erstellen und prüfen, Restore-Vorschau und bewusst bestätigter Restore.
- Geführte `Erste Schritte`, optionaler Anzeigename und persönliche
  Dashboard-Begrüßung.
- Sicherheitseinstellungen für Sperrintervall, Passwort, Recovery-Codes,
  gespeicherte Anmeldung, Touch ID und manuelles Sperren.
- Arbeitsfenster für Beobachtung, Bericht und LEG öffnen maximiert auf der
  verfügbaren Bildschirmfläche. Lange Bestätigungsaktionen bleiben vollständig
  lesbar; beim LEG-Seitenwechsel bleibt genau eine Phase sichtbar.
- Die Oberfläche verwendet nun eine konsistentere Markenpalette und klarer
  unterscheidbare Arbeitsbereichskontexte: Beobachtung, LEG und Bericht sind
  visuell ruhiger voneinander abgegrenzt, die Sidebar ist zurückhaltender und
  Primäraktionen sind konsistent hervorgehoben.
- Sichtbare Fokusrahmen unterstützen die Tastaturorientierung. Fachliche Kurs-,
  Bewertungs-, Dokumentations- und Feedbackfarben bleiben unverändert; es gibt
  keine Navigations- oder Funktionsänderung.

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
