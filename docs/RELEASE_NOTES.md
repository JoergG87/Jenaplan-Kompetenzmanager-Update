# Jenaplan-Kompetenzmanager 0.3.0 / Build 303

## Status dieser Release Notes

Dies sind die Release Notes für den macOS-arm64-Vorbereitungsstand, nicht für
einen Release Candidate oder GitHub-Pre-Release. Clean-Build, DMG,
Prüfsummenmanifest und der vollständige Buildcommit werden vor einer Übergabe
als unveränderliche Releaseartefakte nachgewiesen. Builds 300 bis 302 sind
überholte, nicht verteilte Vorstände.

## Produktumfang

Der Jenaplan-Kompetenzmanager ist eine lokale macOS-Desktop-App ohne Cloud und
ohne KI-Funktion. Der dokumentierte Stand bietet:

- lokale Anmeldung, Passwortanlage und Passwortwechsel, Recovery-Codes,
  Keychain-gestützte Geräteanmeldung, optionales Touch ID mit sichtbaren
  Nichtverfügbarkeitsgründen, Passwort-Fallback, Sperre und Support-Reset;
- Dashboard, Stundenplan, Schüler, Stammgruppen, Kurse und Kursverbünde;
- Beobachtungen, verwaltete Anhänge, Kompetenz-Cockpit und
  Bestätigungsstände;
- Berichtsentwürfe mit Auswahl vorhandener Entwürfe, neuem eigenständigem
  Entwurf, Finalisierung, Revisionen und PDF-Ausgaben;
- LEG-Entwürfe mit Auswahl, neuem eigenständigem Gespräch, Abschluss,
  Revisionen und PDF-Ausgaben;
- lokales ZIP-v1-Backup mit Prüfung sowie Restore-Vorschau, ausdrücklicher
  Bestätigung, separatem Restore-Worker und kontrolliertem Neustart.

Die Schülerliste, das Dashboard und Kursverbünde lesen ihre Projektionen
gebündelt. Dadurch bleibt der Alltag auch bei größeren lokalen Beständen frei
von tausenden Einzelabfragen.

<!-- pagebreak -->

## Datenintegrität und Bedienung

- Beobachtung und Anhänge werden als kontrollierter Gesamtvorgang gespeichert:
  ein Fehler erzeugt keine zweite Beobachtung, und gültige Altanhänge bleiben
  bei fehlgeschlagener Bearbeitung erhalten.
- Die technische Ereignisreihenfolge ist für Bestätigungsfrische maßgeblich.
  Historisch nicht beweisbare Stände werden verständlich als unklar gezeigt und
  durch eine bewusste erneute Bestätigung aufgelöst.
- Abbrechen und Escape sind sichere Standardwege. Produktinterne
  Bestätigungen verwenden deutsche, kontextbezogene Aktionsbezeichnungen.
- Der Restore ersetzt den aktiven fachlichen Bestand erst nach erfolgreicher
  Prüfung. Startet der Worker nicht, bleibt der bisherige Bestand unverändert.

## Schutz- und Releasegrenzen

Ein späterer GitHub-Pre-Release/Pilot wird ad-hoc signiert und nicht
notarisiert sein. Windows ist nicht freigegeben; es gibt keinen Stable-Release
und keinen Stable-Appcast. Developer ID und Notarisierung bleiben offen.

Die App-Sperre ist keine Verschlüsselung der Fachdaten, verwalteten Dokumente
oder ZIP-v1-Backups. SQLCipher, verschlüsselte Dokumentcontainer und ein
verschlüsselter Backupcontainer sind implementierte, getestete Foundations,
aber im normalen Produktpfad standardmäßig deaktiviert. Bestehende Pilot- und
Produktdaten werden nicht automatisch migriert und es gibt keine stille
Aktivierung.

Details für Lehrkräfte, technische Betreuung und Releaseverantwortliche stehen
in `SICHERHEIT_UND_VERSCHLUESSELUNG.md`. Das Benutzerhandbuch beschreibt die
Bedienabläufe mit ausschließlich synthetischen Screenshots.

## Referenzabnahme und offene Gates

Laut der vorliegenden Referenzabnahme sind alle bestätigten Audit-P1 geschlossen
und die letzte Gesamtsuite mit 1.617 Tests sowie 67 Subtests bei Exitcode 0
bestanden. Sie wurde für diesen reinen Dokumentationsauftrag nicht erneut
ausgeführt.

Vor einer Übergabe bleiben insbesondere ein Clean-Build, reale macOS-/Hardware-
und Restore-Abnahme, Artefaktprüfung, Developer ID/Notarisierung, eine spätere
kontrollierte Verschlüsselungsmigration und eine reale Power-Loss-Abnahme offen.
