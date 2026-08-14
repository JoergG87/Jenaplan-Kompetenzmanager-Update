# Jenaplan-Kompetenzmanager - Final-V4-Pilotstand

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

## Status dieser Release Notes

Diese Release Notes dokumentieren den inhaltlich finalen Final-V4-Reviewstand
vor der späteren Versionsanhebung. Sie belegen weder finales Pilotartefakt noch
Release, Pilot-GO, Developer-ID-Signierung oder Apple-Notarisierung.

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

## Fachliche Struktur

- Selbst- und Sozialkompetenz sowie Arbeits- und Lernkompetenz sind als überfachliche
  Entwicklung immer verfügbar. Sie sind keine Unterrichtsfächer und erscheinen
  nicht im Stundenplan oder allgemeinen Fachsetup.
- Zehn Unterrichtsfächer stehen zur Verfügung: EPU, Deutsch, Mathematik,
  Kreatives Gestalten, Sport, Ethik, Religion, Musik, Englisch und Schulgarten.
- Relevante Unterrichtsfächer werden pro Schüler und Schuljahr gepflegt; die
  überfachliche Entwicklung bleibt davon unabhängig.
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

- spätere Versionsanhebung und finale Regeneration derselben Quellen;
- finaler Pilotbuild und Fresh-First-Run-Abnahme;
- reales Keychain-/Codesign-/Restore-Bundlegate;
- portable Backup-Recovery beziehungsweise DMK-Recovery;
- Developer ID und Apple-Notarisierung;
- ausdrückliches Pilot-GO.

## Historische Dokumentation

Explizit ältere Release-, Sprint-, Foundation- und Builddokumente bleiben als
Historie erhalten. Ihre Aussagen beschreiben nicht den aktuellen
Final-V4-Produktpfad und werden nicht als aktuelle Pilotunterlagen erzeugt.
