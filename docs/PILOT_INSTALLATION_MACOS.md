# macOS-Installation und technische Pilotvorbereitung

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

Status: inhaltlich finaler Final-V4-Reviewstand vor der Versionsanhebung; noch
kein finales Pilot-, Build- oder Releaseartefakt.

| Punkt | Aktueller Vertrag |
|---|---|
| Architektur | Apple Silicon (arm64) |
| Mindestplattform | macOS 13 |
| Installation | Drag-and-drop-DMG nach gesondertem Freigabegate |
| Signatur | ad-hoc signiert, nicht notarisiert; Developer ID separat |
| Datenmodus | frische leere Final-V4-Pilotinstallation |
| Freigabe | kein Release, kein Stable-Appcast, kein Pilot-GO durch dieses Dokument |

## Installationsweg

DMG im Finder öffnen, `Jenaplan-Kompetenzmanager.app` nach `Programme` ziehen,
DMG auswerfen und die App aus `Programme` starten. Bei einem internen,
nicht notarisierten Artefakt nur den kontrollierten Weg über Control-Klick
`Öffnen` beziehungsweise `Datenschutz & Sicherheit > Dennoch öffnen` nutzen.
Gatekeeper niemals global deaktivieren.

Auf dem Ziel-Mac werden weder Python, Terminal, Repository noch
Entwicklungsumgebung benötigt. Version und Build unter `Über die App` prüfen.

## Final-V4-Produktdatenhaltung

Der normale Produktpfad verwendet nach erfolgreicher Anmeldung eine
verschlüsselte Final-V4-Fachdatenbank (`PRAGMA user_version = 4`) und einen
verschlüsselten Dokument-Companion. Verbindlich sind SQLCipher 4.17.0,
SQLite 3.53.3 und CommonCrypto; Standard-SQLite ist kein Fallback.

Das App-Passwort schützt den Zugang und ist nicht der Datenschlüssel. Der DMK
liegt getrennt im macOS-Schlüsselbund; ein separater Database-Key wird über den
geschützten Schlüsselkontext geöffnet. Fehlende oder widersprüchliche
Schlüssel-, Schema- oder Runtimezustände blockieren den Start.

Der First Run erzeugt den technischen Final-V4-Systembestand, Schuljahr
`2026/27` vom 01.08.2026 bis 31.07.2027 und den offiziellen Katalog mit 331
Kompetenzen. Schüler, Stammgruppen, Kurse, Kursverbünde, Beobachtungen,
Bestätigungen, Berichtsentwürfe, LEG-Entwürfe, Testdokumente, Beispielschüler,
Beispielbeobachtungen und Testbackups bleiben leer.

## Managed Documents und PDF-Viewer

Beobachtungsanhänge, Schülerdokumente sowie finale Bericht- und LEG-PDFs
werden als verschlüsselte Managed Documents gespeichert. Finale PDFs öffnen
read-only im sicheren In-App-Viewer. Dieser unterstützt mehrseitige Anzeige,
Scrollen, Zoom, Schließen und erneutes Öffnen. Export, Drucken und Teilen sind
nicht Teil dieses Produktvertrags. Qt ist der Pilotstandard; historische oder
interne HTML-Erprobungspfade sind keine Lehrkraftfunktion.

## Backup, Restore und Support Reset

Der Produktpfad veröffentlicht ausschließlich verschlüsselte `.jkmebackup`.
Restore verlangt vollständige Prüfung, Vorschau und Bestätigung, verifiziertes
Staging, Safety-Backup, separaten Worker, vollständige App-Beendigung,
kontrollierten Neustart und erneute Anmeldung.

Backup und Restore sind installationsgebunden und benötigen den passenden
vorhandenen lokalen Schlüsselkontext. Allgemeine Geräteportabilität,
DMK-Recovery und Cloud-Backup werden nicht behauptet.

Support Reset ist ein betreuter Ausnahmeweg bei verlorenem Passwort und
fehlenden Recovery-Codes. Voraussetzung sind die ursprüngliche aktive
Produktinstallation, ein intakter zugreifbarer DMK, vollständig prüfbares
Final V4 und ein erfolgreich erzeugtes und verifiziertes Safety-`.jkmebackup`.
Er verändert ausschließlich Authentifizierungs- und Recoveryzustände. Support
erhält weder Passwort, DMK, Database-Key, Schülerdaten, Dokumente noch
Backupinhalt. Ein verlorener DMK bleibt nicht recoverbar.

## Offene Freigaben

- finaler Pilotbuild und exakte Artefaktprüfung;
- reale macOS-, Keychain-, Touch-ID-, Restore- und Fresh-First-Run-Abnahme;
- Developer ID und Apple-Notarisierung;
- portable Backup-Recovery beziehungsweise DMK-Recovery;
- ausdrückliches Pilot-GO.
