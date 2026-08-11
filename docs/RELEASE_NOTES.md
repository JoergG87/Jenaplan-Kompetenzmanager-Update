# Jenaplan-Kompetenzmanager 0.4.0 / Build 400 – geplanter Pilotstand

## Status dieser Release Notes

Diese Release Notes bereiten Version 0.4.0 / Build 400 fachlich vor. Sie
belegen weder ein erzeugtes oder verteiltes Artefakt noch Release, Pilot-GO,
Developer-ID-Signierung oder Apple-Notarisierung. Clean-Build, exakter
Buildcommit, DMG, Prüfsummen und manuelle Pilotabnahme bleiben getrennte Gates.

## Wesentliche Änderungen gegenüber 0.3.0 / Build 303

### Final V4 und aktive lokale Verschlüsselung

- Final V4 ist das aktuelle Pilot-/Produktschema.
- Die Produktdatenbank und der Dokument-Companion werden keyed mit SQLCipher
  4.17 geöffnet. Standard-SQLite ist kein produktiver Fallback.
- Das App-Passwort ist nicht der Datenbankschlüssel. Der DMK bleibt geschützt
  im macOS-Keychain-Kontext; der getrennte Database-Key wird über ein
  authentisiertes Envelope verwaltet.
- Vorhandene Klartext-, V3- und alte Testbestände werden nicht automatisch
  migriert. Für den kommenden Pilot gibt es keine produktiven Altdaten, die
  übernommen werden müssten.

### Verschlüsselte verwaltete Dokumente

- Beobachtungsanhänge, allgemeine Schülerdokumente sowie finale Bericht- und
  LEG-Artefakte verwenden zentral den `ManagedDocumentStore`.
- Dokumente werden als verschlüsselte Generationen verwaltet. Fachliche
  Dokument-ID und physische Storage-Generation bleiben getrennt.

### Verschlüsseltes Backup und Restore

- Der Produktpfad verwendet ausschließlich das verschlüsselte `.jkmebackup`.
- Es enthält Final-V4-Datenbank, keyed Companion, notwendige Keyset-/Envelope-
  Metadaten und registrierte verschlüsselte Dokumentgenerationen.
- Es enthält keinen DMK, keine Passwörter, Recovery-Codes, Touch-ID- oder
  Gerätecredentials.
- Restore prüft vollständig in einem neuen Staging-Bereich und verlangt
  `RESTORE_READY`, bewusste Bestätigung, verschlüsseltes Sicherheitsbackup,
  separaten Restore-Worker, kontrollierten Austausch, Reopen/Neustart und
  Rollback bei Fehlern.
- Restore ist installationsgebunden und benötigt den passenden bestehenden DMK.
  Geräteübertragbarkeit und DMK-Recovery werden nicht behauptet.

### Schuljahr und individuelle Fachprofile

- Der frische Pilot startet mit dem Schuljahr `2026/27` vom 01.08.2026 bis
  31.07.2027 und ohne automatisch angelegte Schüler- oder Testdaten.
- Schüler können pro Schuljahr die globalen Dokumentationsfächer übernehmen
  oder eine genaue individuelle Auswahl verwenden. Eine bewusst leere Auswahl
  ist zulässig.
- Historische Schuljahre sind nicht für normale nachträgliche Änderungen der
  Fachauswahl vorgesehen.

### Entwicklungsübersicht

- Timeline, Fachkarten und Dokumentationsumfang erscheinen unmittelbar für das
  aktuelle Schuljahr und berücksichtigen die individuellen Schülerfächer.
- Die Übersicht arbeitet unabhängig von einem Berichtsentwurf.
- Sie berechnet keine Stärke, Schwäche, Punktzahl, Tendenz oder Priorität.

### Bericht und LEG

- Bericht bleibt ein getrenntes Arbeitsprodukt mit dem RPD-Zeitraum des
  konkreten Entwurfs. Mehrere Entwürfe werden nicht unbemerkt automatisch
  ausgewählt.
- Der Qt-Bericht bleibt Pilot-Fallback und aktueller Produktdefault.
- Der Qt-LEG-Pfad bleibt verfügbar; sein nativer Window-/Fokus-Lifecycle ist
  als shell-owned, window-modaler Ablauf stabilisiert.
- Die optionalen lokalen HTML-Oberflächen hinter `JKM_REPORT_UI=html` und
  `JKM_LEG_UI=html` sind ausschließlich interne Erprobungspfade. Qt bleibt
  Default; HTML ist nicht als Pilotstandard freigegeben.

## Bekannte Pilotgrenzen und offene Gates

- Ein finales Bericht- oder LEG-Artefakt kann verschlüsselt vorhanden sein.
  Der gemeinsame sichere Produktviewer ist noch nicht final freigegeben;
  `Finales PDF anzeigen` kann kontrolliert blockiert bleiben.
- Support Reset bleibt im Final-V4-Cipher-Produktpfad kontrolliert blockiert.
- Keine automatische Migration älterer Datenbestände.
- Keine Geräteübertragbarkeit und kein DMK-Recoverypfad für `.jkmebackup`.
- Kein Developer-ID-/Notarisierungsnachweis, kein Stable Release, kein Windows
  und kein Pilot-GO.

## Einordnung historischer Dokumentation

Historische Sprint-, Foundation- und Build-303-Abschnitte bleiben als Historie
erhalten. Aussagen zu Klartext-SQLite, Klartextdokumenten, ZIP-v1 oder nur
deaktivierter Verschlüsselungsfoundation beschreiben nicht den heutigen
Final-V4-Produktpfad.
