# macOS-Installation und technische Pilotvorbereitung 0.4.0 / Build 400

## Status

Diese Unterlage beschreibt den geplanten macOS-arm64-Pilotstand. Version 0.4.0
/ Build 400 ist vorbereitet, aber noch nicht als Release, Verteilung,
Notarisierung oder Pilot-GO freigegeben. Ein konkretes App-/DMG-Artefakt,
Prüfsummenmanifest und exakter Buildcommit müssen vor der Übergabe separat aus
einem sauberen Build nachgewiesen werden.

| Punkt | Vorbereiteter Stand |
|---|---|
| Produkt | Jenaplan-Kompetenzmanager 0.4.0 / Build 400 |
| Architektur | Apple Silicon (arm64) |
| Mindestplattform | macOS 13 |
| Übergabeform | kontrolliertes Drag-and-drop-DMG nach gesondertem Freigabegate |
| Signatur | Developer ID und Notarisierung nicht nachgewiesen |
| Datenmodus | frische leere Pilotinstallation; keine Schüler-, Pilot- oder Testdaten im Bundle |
| Freigabe | kein Pilot-GO, kein Windows, kein Stable-Release, kein Stable-Appcast |

## Erwarteter Installationsweg

Nach einer freigegebenen Übergabe wird das DMG im Finder geöffnet,
`Jenaplan-Kompetenzmanager.app` nach `Programme` gezogen, das DMG ausgeworfen
und die App regulär aus `Programme` gestartet. Bei einem internen, nicht
notarisierten Artefakt gilt nur der kontrollierte Weg über Control-Klick
`Öffnen` beziehungsweise `Datenschutz & Sicherheit > Dennoch öffnen`.
Gatekeeper wird niemals global deaktiviert.

Die App benötigt auf dem Ziel-Mac weder Python, Terminal, Repository noch
Entwicklungsumgebung. Version und Build werden über `Über die App` geprüft.

## Final-V4-Produktdatenhaltung

Der normale Pilotstart öffnet nach erfolgreicher Authentifizierung eine frisch
angelegte Final-V4-Fachdatenbank und den Dokument-Companion keyed mit exakt
SQLCipher 4.17/CommonCrypto. Standard-SQLite ist kein produktiver Fallback.

Das App-Passwort authentifiziert die Lehrkraft und ist nicht der
Datenbankschlüssel. Der Data Master Key (DMK) liegt geschützt im macOS-
Keychain-Kontext. Ein eigener Database-Key wird getrennt in einem
authentisierten Envelope verwaltet und öffnet Haupt- und Companion-Datenbank.
Fehlende oder widersprüchliche Schlüssel-, Schema- oder Runtimezustände
blockieren den Start fail-closed.

Der First Run legt ausschließlich das aktuelle Schuljahr `2026/27` vom
01.08.2026 bis 31.07.2027 an. Schüler, Gruppen, Kurse, Assignments,
Beobachtungen und Testdaten bleiben leer. Vorhandene Klartext-, V3- und alte
Testbestände werden weder automatisch geöffnet noch migriert, überschrieben
oder gelöscht. Für den kommenden Pilot existieren keine produktiven Altdaten,
die migriert werden müssten.

## Verschlüsselte verwaltete Dokumente

Beobachtungsanhänge, allgemeine Schülerdokumente und finale Bericht-/LEG-
Artefakte verwenden zentral den `ManagedDocumentStore`. Fachliche Dokument-ID
und physische Storage-Generation bleiben getrennt; der keyed Companion hält
die registrierten Generationen und ihre aktiven Pointer.

Finale verschlüsselte Bericht- und LEG-PDFs lassen sich über denselben sicheren
In-App-Viewer lesen. Die Anzeige erfolgt nach Python-seitiger Auflösung und
Vollverifikation ausschließlich im Speicher; sie erzeugt keine Klartextdatei
und verwendet weder Finder/Preview noch Download, Export, Drucken oder Teilen.
PDF-Export bleibt offen. Die technische Source-Prüfung und ein Cocoa-Smoke sind
erfolgt; reale PO-Abnahme im Qt-/HTML-Vergleichsbuild sowie Bundle-/Packaging-
Nachweis bleiben offen und sind kein Pilot- oder Release-GO.

## Verschlüsseltes Backup und Restore

Der Produktpfad veröffentlicht ausschließlich `.jkmebackup`. Der
authentisierte Container umfasst:

- die keyed Final-V4-Hauptdatenbank;
- den keyed Dokument-Companion;
- notwendige Keyset- und Database-Key-Envelope-Metadaten;
- alle registrierten verschlüsselten Dokumentgenerationen.

Das Backup enthält keinen DMK, kein App-Passwort, keine Recovery-Codes und
keine Touch-ID- oder Gerätecredentials. Es ist installationsgebunden: Restore
benötigt den passenden vorhandenen DMK derselben Installation. Ein
Gerätewechsel- oder DMK-Recoverypfad wird nicht behauptet.

Restore prüft Container, Manifest, Datenbanken, Metadaten, Dokumentinventar,
Hashes und Bindungen vollständig in einem neuen Staging-Bereich. Erst
`RESTORE_READY` erlaubt die bewusste Übernahme. Danach folgen verschlüsseltes
Sicherheitsbackup, separater Restore-Worker, kontrollierter Austausch,
Reopen/Neustart und Rollback bei Fehlern. ZIP-v1 und ein Klartextfallback sind
im Cipher-Produktmodus gesperrt.

## Support Reset und optionale Oberflächen

Support Reset verwendet im Final-V4-Cipher-Produktpfad dieselbe vorhandene
Verschlüsselungsidentität. Er ist nur auf der ursprünglichen intakten
Installation möglich und setzt einen vollständig geprüften lokalen Bestand
sowie ein erzeugtes und vollständig verifiziertes `.jkmebackup` voraus. Ein
alter ZIP-v1- oder Klartextpfad ist keine aktive Ausweichlösung; Gerätewechsel
und ein verlorener Installationsschlüssel bleiben nicht wiederherstellbar.

Bericht und LEG verwenden standardmäßig die Qt-Oberfläche. Die Variablen
`JKM_REPORT_UI=qt|html` und `JKM_LEG_UI=qt|html` schalten ausschließlich
interne Erprobungspfade. Die HTML-Hosts rendern lokal aus `qrc:` in
`QWebEngineView`/`QWebChannel`; Python bleibt Source of Truth. Netzwerk,
externe Navigation und Downloads sind blockiert, Qt bleibt Fallback. Daraus
folgt keine Pilotstandard-, Packaging-, Accessibility- oder Releasefreigabe.

## Offene Freigaben

- sauberer exakter Build von 0.4.0 / Build 400 und Artefaktprüfung;
- reale macOS-, Keychain-, Touch-ID-, Restore- und UX-Abnahme;
- gemeinsamer sicherer Produktviewer für finale verschlüsselte PDFs;
- Developer ID und Apple-Notarisierung;
- Gerätewechsel und DMK-Recovery;
- Windows, Stable-Release, Stable-Appcast und Pilot-GO.

Details stehen in `SICHERHEIT_UND_VERSCHLUESSELUNG.md`.
