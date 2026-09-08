# Jenaplan-Kompetenzmanager - Final-V4-Pilotstand

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

## Status dieser Release Notes

Diese Release Notes dokumentieren den vorbereiteten Final-V4-Pilotstand
{{PILOT_VERSION}} / Build {{PILOT_BUILD}}. Sie belegen weder ein finales App-Bundle noch Release,
Pilot-GO, Developer-ID-Signierung oder Apple-Notarisierung.

## Neu im vorbereiteten Folgeupdate

Diese Ergänzungen gehören zum unveröffentlichten Quellstand nach dem bisherigen
Pilotpaket. Das neue Paket verwendet die oben ausgewiesene eigene Versions- und
Buildidentität; die Paketprüfung erfolgt am zugehörigen Manifest.

- Das Dashboard berücksichtigt die individuellen Dokumentationsfächer jedes
  Kindes auch in der Heatmap und bei passenden Kindern für die Unterrichtsstunde.
- `⌘N` öffnet eine Beobachtung für das aktuelle Kind. Ohne eindeutige Auswahl
  führt das Kürzel zur Schülersuche.
- `Speichern & weitere` speichert eine Beobachtung und öffnet eine leere
  Folgeeingabe für dasselbe Kind. Bereits gespeicherte Einträge bleiben auch
  beim Abbrechen der nächsten Eingabe erhalten.
- Neue Beobachtungen beginnen mit dem Fokus in der Kompetenzsuche; beim
  Bearbeiten steht der Fokus in der vorhandenen Notiz.
- Fachabschnitte der Berichtsvorschau lassen sich ein- und ausklappen.
  Berichtsinhalte und PDF bleiben dabei vollständig.
- In den Einstellungen erscheint ein ruhiger Hinweis auf fehlende oder
  mindestens sieben Tage alte geprüfte Sicherungen. Neue Sicherungen werden
  weiterhin bewusst gestartet.

## Fachliche Grundlage und Dokumentation

- Fachliche Grundlage ist das offizielle Jenaplan-Entwicklungsbuch mit 331
  Kompetenzen in zehn Unterrichtsfächern. Überfachliche Entwicklung bleibt
  davon getrennt; Unterrichtsfächer werden je Kind individuell priorisiert.
- Beobachtungen, Kompetenz-Cockpit, Bericht und LEG bilden den aktuellen
  Lehrkraftworkflow. Es werden keine Beispielkinder oder Testdaten angelegt.

## Final V4 und lokale Verschlüsselung

- Final V4 (`PRAGMA user_version = 4`) ist das aktuelle Produktschema.
- Produktdatenbank und Dokument-Companion werden mit SQLCipher 4.17.0,
  SQLite 3.53.3 und CommonCrypto geöffnet. Standard-SQLite ist kein Fallback.
- Das App-Passwort schützt den Zugang. Der davon getrennte DMK wird über den
  macOS-Schlüsselbund geschützt; ein separater Database-Key öffnet die
  Datenbanken.
- Der Pilot-Produktionsroot ist geschützt. Seed-, Reset-, Recreate- und
  Klartextfallbacks sind im Produktpfad gesperrt.

## Fresh First Run

- Eine frische Installation enthält den technischen Final-V4-Systembestand,
  Schuljahr `2026/27` vom 01.08.2026 bis 31.07.2027 sowie den offiziellen
  Entwicklungsbuchkatalog mit 331 Kompetenzen.
- Schüler, Stammgruppen, Kurse, Kursverbünde, Beobachtungen, Bestätigungen,
  Berichtsentwürfe, LEG-Entwürfe, Testdokumente, Beispielbestände und
  Testbackups werden nicht angelegt.
- Ein Beispielbestand oder Katalogimport ist für den Pilotstart nicht nötig.

<!-- pagebreak -->

## Fachliche Struktur

- Selbst- und Sozialkompetenz sowie Arbeits-/Lernkompetenz sind als überfachliche
  Entwicklung immer verfügbar. Sie sind keine Unterrichtsfächer, erscheinen
  nicht im Stundenplan und müssen für ein Kind auch dann nicht ausgewählt
  werden, wenn die vorhandene allgemeine Voreinstellung `Fächer für die
  Dokumentation` diese Dokumentationsbereiche aufführt.
- Zehn Unterrichtsfächer stehen zur Verfügung: EPU, Deutsch, Mathematik,
  Kreatives Gestalten, Sport, Ethik, Religion, Musik, Englisch und Schulgarten.
- Relevante Unterrichtsfächer werden pro Schüler und Schuljahr gepflegt. Dazu
  `Schüler` öffnen, das Kind über `Profil öffnen` auswählen und unter
  `Überblick` die Karte `Fächer für die Dokumentation` mit `Aufklappen`
  öffnen. `Für dieses Kind individuell festlegen` erlaubt die bewusste Auswahl;
  `Globale Fachauswahl verwenden` übernimmt die vorhandene Voreinstellung.
- Die Auswahl priorisiert Unterrichtsfächer im normalen Dokumentationsworkflow;
  sie löscht nichts und ist keine harte Berechtigungsgrenze. Im
  Beobachtungsdialog stehen die wirksamen Fächer primär unter `Fächer`, andere
  aktive Unterrichtsfächer unter `Weitere Fächer`. Eine bewusst leere
  individuelle Auswahl bleibt leer.
- Die überfachliche Entwicklung bleibt davon unabhängig immer verfügbar und
  wird nicht als Unterrichtsfach ausgewählt.
- Kleine Fachmarker dienen nur der Orientierung. Fachnamen bleiben sichtbar;
  Kurs-, Rating- und Statusfarben bleiben getrennt. Für EPU und Kreatives
  Gestalten ist keine neue Farbe festgelegt.

## Managed Documents, Bericht und LEG

- Beobachtungsanhänge, Schülerdokumente sowie finale Bericht- und LEG-PDFs
  werden verschlüsselt als Managed Documents gespeichert.
- Finale PDFs öffnen read-only im sicheren In-App-Viewer mit mehrseitiger
  Anzeige, Scrollen, Zoom, Schließen und erneutem Öffnen. Export, Drucken und
  Teilen werden nicht versprochen.
- Der Qt-Bericht führt durch `Auswählen -> Schreiben -> Prüfen & finalisieren`.
  Texte bleiben manuell verantwortet, ausgewählte Belege sind beim Schreiben
  read-only sichtbar, mehrere Entwürfe sind möglich und Finalisierung erzeugt
  eine unveränderliche Revision.
- Der Qt-LEG-Arbeitsbereich ordnet sechs fachliche Anker in `Vorbereitung`,
  `Im Gespräch` und `Vereinbarungen & Abschluss`. Der kanonische Kompetenzstand
  bleibt read-only; Kompetenzen und Belege werden primär in der Vorbereitung
  gewählt und außerhalb dieses Ankers read-only zusammengefasst. Es gibt keine
  eigene LEG-Bewertung.
- Qt ist Pilotstandard. Historische oder interne HTML-Erprobungspfade sind
  keine Lehrkraftfunktion.

## Backup, Restore und Support Reset

- Das aktuelle Produktbackup ist ausschließlich das verschlüsselte
  `.jkmebackup`.
- Restore verlangt Prüfung, Vorschau und Bestätigung, verifiziertes Staging,
  Safety-Backup, separaten Worker, vollständige App-Beendigung, kontrollierten
  Neustart und erneute Anmeldung.
- Backup und Restore sind an die ursprüngliche geschützte Installation und
  deren vorhandenen lokalen Schlüsselkontext gebunden. Allgemeine
  Geräteportabilität und DMK-Recovery werden nicht behauptet.
- Recovery-Codes bleiben der erste Wiederherstellungsweg.
- Support Reset ist als betreute Auth-Recovery verfügbar, aber nur bei intakter
  ursprünglicher Installation, zugreifbarem DMK, vollständig prüfbarem Final V4
  und erfolgreich erzeugtem und verifiziertem Safety-`.jkmebackup`. Er ändert
  keine Fachdaten oder Datenschlüssel und gibt Support keinen Datenzugriff.

## Offene Gates

- finaler Pilotbuild nach bestandenem Source-/Dokument-/Fresh-First-Run-Gate;
- reales Keychain-/Codesign-/Restore-Bundlegate;
- Support Reset und Backup/Restore im real gebauten Bundle;
- finaler DMG-Smoke;
- portable Backup-Recovery beziehungsweise DMK-Recovery;
- Developer ID und Apple-Notarisierung;
- ausdrückliches Pilot-GO.

## Historische Dokumentation

Explizit ältere Release-, Sprint-, Foundation- und Builddokumente bleiben als
Historie erhalten. Ihre Aussagen beschreiben nicht den aktuellen
Final-V4-Produktpfad und werden nicht als aktuelle Pilotunterlagen erzeugt.
